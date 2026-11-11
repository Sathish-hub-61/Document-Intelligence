"""
Documents API endpoints matching Blueprint Section 8.1.
"""
from datetime import date
import json
from typing import List, Optional
from uuid import UUID, uuid4
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.adapters.api.dependencies import get_current_user, require_role
from app.adapters.api.schemas.common import DocumentOut, UploadMeta, VersionOut
from app.adapters.persistence.database import get_db, SessionLocal
from app.adapters.persistence.repositories import SqlAlchemyDocumentRepo
from app.adapters.storage.local_files import LocalFileStorage
from app.application.use_cases.ingest_document import run_ingestion_pipeline
from app.domain.entities import Document, DocumentVersion, IngestionJob, JobStatus, Role, User, VersionStatus
from app.domain.errors import DuplicateFileError, EntityNotFoundError, ForbiddenError

router = APIRouter(prefix="/api", tags=["Documents"])


def _bg_ingest_worker(version_id: UUID, job_id: UUID, file_path: str):
    db = SessionLocal()
    try:
        repo = SqlAlchemyDocumentRepo(db)
        run_ingestion_pipeline(version_id, job_id, file_path, repo)
    finally:
        db.close()


@router.post("/documents", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    document_type: str = Form(...),
    department: Optional[str] = Form(None),
    allowed_roles: str = Form(...),  # JSON list string e.g. ["student", "faculty"] or comma-separated
    effective_from: Optional[date] = Form(None),
    effective_to: Optional[date] = Form(None),
    current_admin: User = Depends(require_role(Role.ADMIN)),
    db: Session = Depends(get_db),
):
    storage = LocalFileStorage()
    content = await file.read()
    rel_path, sha256_hash, mime_type = storage.save_file(content, file.filename or "upload.pdf")

    # Parse allowed roles
    parsed_roles: List[Role] = []
    try:
        raw = json.loads(allowed_roles)
        if isinstance(raw, list):
            parsed_roles = [Role(r) for r in raw]
    except Exception:
        parsed_roles = [Role(r.strip()) for r in allowed_roles.split(",") if r.strip()]

    if not parsed_roles:
        parsed_roles = [Role.ADMIN, Role.STUDENT, Role.FACULTY, Role.STAFF]

    repo = SqlAlchemyDocumentRepo(db)

    # Create Document entity
    document = Document(
        title=title,
        document_type=document_type,
        department=department,
        created_by=current_admin.user_id,
        allowed_roles=parsed_roles,
    )
    saved_doc = repo.create_document(document, parsed_roles)

    # Create Initial Version in DRAFT
    version = DocumentVersion(
        document_id=saved_doc.document_id,
        version_number=1,
        file_path=rel_path,
        file_sha256=sha256_hash,
        mime_type=mime_type,
        status=VersionStatus.DRAFT,
        effective_from=effective_from,
        effective_to=effective_to,
        uploaded_by=current_admin.user_id,
    )
    saved_ver = repo.create_version(version)

    # Create Ingestion Job in QUEUED
    job = IngestionJob(
        version_id=saved_ver.version_id,
        status=JobStatus.QUEUED,
    )
    saved_job = repo.create_job(job)

    # Launch background extraction and chunking
    background_tasks.add_task(
        _bg_ingest_worker,
        saved_ver.version_id,
        saved_job.job_id,
        rel_path,
    )

    return {
        "document_id": str(saved_doc.document_id),
        "version_id": str(saved_ver.version_id),
        "job_id": str(saved_job.job_id),
        "status": "queued",
    }


@router.get("/documents", response_model=List[DocumentOut])
def list_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = SqlAlchemyDocumentRepo(db)
    docs = repo.list_documents(current_user.role)
    out = []
    for d in docs:
        curr_ver = repo.get_current_version(d.document_id)
        out.append(
            DocumentOut(
                document_id=d.document_id,
                title=d.title,
                document_type=d.document_type,
                department=d.department,
                created_by=d.created_by,
                created_at=d.created_at,
                allowed_roles=d.allowed_roles,
                current_version={"version_id": curr_ver.version_id, "version_number": curr_ver.version_number} if curr_ver else None,
            )
        )
    return out


@router.get("/documents/{document_id}", response_model=DocumentOut)
def get_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = SqlAlchemyDocumentRepo(db)
    doc = repo.get_document(document_id)
    if not doc:
        raise EntityNotFoundError("Document not found")

    # Role check: Return 404 rather than 403 so restricted documents are not confirmed to exist
    if current_user.role != Role.ADMIN and current_user.role not in doc.allowed_roles:
        raise EntityNotFoundError("Document not found")

    curr_ver = repo.get_current_version(doc.document_id)
    return DocumentOut(
        document_id=doc.document_id,
        title=doc.title,
        document_type=doc.document_type,
        department=doc.department,
        created_by=doc.created_by,
        created_at=doc.created_at,
        allowed_roles=doc.allowed_roles,
        current_version={"version_id": curr_ver.version_id, "version_number": curr_ver.version_number} if curr_ver else None,
    )


@router.get("/versions/{version_id}/jobs")
def get_version_job(
    version_id: UUID,
    current_admin: User = Depends(require_role(Role.ADMIN)),
    db: Session = Depends(get_db),
):
    repo = SqlAlchemyDocumentRepo(db)
    job = repo.get_job_by_version(version_id)
    if not job:
        raise EntityNotFoundError("No ingestion job found for this version")
    return {
        "job_id": str(job.job_id),
        "version_id": str(job.version_id),
        "status": job.status.value,
        "error": job.error,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
    }


@router.get("/chunks/{chunk_id}")
def get_chunk(
    chunk_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = SqlAlchemyDocumentRepo(db)
    chunk = repo.get_chunk(chunk_id)
    if not chunk:
        raise EntityNotFoundError("Chunk not found")

    version = repo.get_version(chunk.version_id)
    if not version:
        raise EntityNotFoundError("Version not found")

    doc = repo.get_document(version.document_id)
    if not doc:
        raise EntityNotFoundError("Document not found")

    # Authoritative permission verification
    if current_user.role != Role.ADMIN and current_user.role not in doc.allowed_roles:
        raise EntityNotFoundError("Chunk not found")

    return {
        "chunk_id": str(chunk.chunk_id),
        "document_title": doc.title,
        "version_number": version.version_number,
        "page_start": chunk.page_start,
        "page_end": chunk.page_end,
        "section_heading": chunk.section_heading,
        "chunk_text": chunk.chunk_text,
    }


@router.get("/files/{version_id}")
def download_file(
    version_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = SqlAlchemyDocumentRepo(db)
    version = repo.get_version(version_id)
    if not version:
        raise EntityNotFoundError("Version not found")

    doc = repo.get_document(version.document_id)
    if not doc or (current_user.role != Role.ADMIN and current_user.role not in doc.allowed_roles):
        raise EntityNotFoundError("File not found")

    storage = LocalFileStorage()
    if not storage.file_exists(version.file_path):
        raise EntityNotFoundError("File missing on disk")

    return FileResponse(version.file_path, media_type=version.mime_type)
