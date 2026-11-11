"""
SQLAlchemy repository implementations satisfying application ports.
"""
from typing import List, Optional, Set
from uuid import UUID
from sqlalchemy.orm import Session

from app.application.ports import DocumentRepoPort, UserRepoPort
from app.adapters.persistence.models import (
    DocumentChunkModel,
    DocumentModel,
    DocumentPermissionModel,
    DocumentVersionModel,
    IngestionJobModel,
    UserModel,
)
from app.domain.entities import (
    Document,
    DocumentChunk,
    DocumentVersion,
    IngestionJob,
    JobStatus,
    Role,
    User,
    VersionStatus,
)


class SqlAlchemyUserRepo(UserRepoPort):
    def __init__(self, db: Session):
        self.db = db

    def _to_domain(self, model: UserModel) -> User:
        return User(
            user_id=model.user_id,
            name=model.name,
            email=model.email,
            password_hash=model.password_hash,
            role=model.role if isinstance(model.role, Role) else Role(model.role),
            is_active=model.is_active,
            created_at=model.created_at,
        )

    def create_user(self, user: User) -> User:
        model = UserModel(
            user_id=user.user_id,
            name=user.name,
            email=user.email,
            password_hash=user.password_hash,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return self._to_domain(model)

    def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        model = self.db.query(UserModel).filter(UserModel.user_id == user_id).first()
        return self._to_domain(model) if model else None

    def get_user_by_email(self, email: str) -> Optional[User]:
        model = self.db.query(UserModel).filter(UserModel.email == email.lower().strip()).first()
        return self._to_domain(model) if model else None

    def list_users(self) -> List[User]:
        models = self.db.query(UserModel).all()
        return [self._to_domain(m) for m in models]


class SqlAlchemyDocumentRepo(DocumentRepoPort):
    def __init__(self, db: Session):
        self.db = db

    def _doc_to_domain(self, model: DocumentModel) -> Document:
        roles = [
            p.role if isinstance(p.role, Role) else Role(p.role)
            for p in model.permissions
        ]
        return Document(
            document_id=model.document_id,
            title=model.title,
            document_type=model.document_type,
            department=model.department,
            created_by=model.created_by,
            created_at=model.created_at,
            allowed_roles=roles,
        )

    def _ver_to_domain(self, model: DocumentVersionModel) -> DocumentVersion:
        return DocumentVersion(
            version_id=model.version_id,
            document_id=model.document_id,
            version_number=model.version_number,
            file_path=model.file_path,
            file_sha256=model.file_sha256,
            mime_type=model.mime_type,
            page_count=model.page_count,
            status=model.status if isinstance(model.status, VersionStatus) else VersionStatus(model.status),
            effective_from=model.effective_from,
            effective_to=model.effective_to,
            uploaded_at=model.uploaded_at,
            uploaded_by=model.uploaded_by,
            supersedes_id=model.supersedes_id,
            scope=model.scope,
        )

    def _chunk_to_domain(self, model: DocumentChunkModel) -> DocumentChunk:
        return DocumentChunk(
            chunk_id=model.chunk_id,
            version_id=model.version_id,
            chunk_index=model.chunk_index,
            page_start=model.page_start,
            page_end=model.page_end,
            section_heading=model.section_heading,
            chunk_text=model.chunk_text,
            token_count=model.token_count,
            attributes=model.attributes,
        )

    def _job_to_domain(self, model: IngestionJobModel) -> IngestionJob:
        return IngestionJob(
            job_id=model.job_id,
            version_id=model.version_id,
            status=model.status if isinstance(model.status, JobStatus) else JobStatus(model.status),
            error=model.error,
            started_at=model.started_at,
            finished_at=model.finished_at,
        )

    def create_document(self, document: Document, allowed_roles: List[Role]) -> Document:
        doc_model = DocumentModel(
            document_id=document.document_id,
            title=document.title,
            department=document.department,
            document_type=document.document_type,
            created_by=document.created_by,
            created_at=document.created_at,
        )
        self.db.add(doc_model)
        self.db.flush()

        for role in allowed_roles:
            perm = DocumentPermissionModel(document_id=document.document_id, role=role)
            self.db.add(perm)

        self.db.commit()
        self.db.refresh(doc_model)
        return self._doc_to_domain(doc_model)

    def get_document(self, document_id: UUID) -> Optional[Document]:
        model = self.db.query(DocumentModel).filter(DocumentModel.document_id == document_id).first()
        return self._doc_to_domain(model) if model else None

    def list_documents(self, user_role: Role) -> List[Document]:
        if user_role == Role.ADMIN:
            models = self.db.query(DocumentModel).all()
        else:
            models = (
                self.db.query(DocumentModel)
                .join(DocumentPermissionModel, DocumentModel.document_id == DocumentPermissionModel.document_id)
                .filter(DocumentPermissionModel.role == user_role)
                .all()
            )
        return [self._doc_to_domain(m) for m in models]

    def update_document_permissions(self, document_id: UUID, roles: List[Role]) -> None:
        self.db.query(DocumentPermissionModel).filter(DocumentPermissionModel.document_id == document_id).delete()
        for role in roles:
            self.db.add(DocumentPermissionModel(document_id=document_id, role=role))
        self.db.commit()

    def create_version(self, version: DocumentVersion) -> DocumentVersion:
        model = DocumentVersionModel(
            version_id=version.version_id,
            document_id=version.document_id,
            version_number=version.version_number,
            file_path=version.file_path,
            file_sha256=version.file_sha256,
            mime_type=version.mime_type,
            page_count=version.page_count,
            status=version.status,
            effective_from=version.effective_from,
            effective_to=version.effective_to,
            uploaded_at=version.uploaded_at,
            uploaded_by=version.uploaded_by,
            supersedes_id=version.supersedes_id,
            scope=version.scope,
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return self._ver_to_domain(model)

    def get_version(self, version_id: UUID) -> Optional[DocumentVersion]:
        model = self.db.query(DocumentVersionModel).filter(DocumentVersionModel.version_id == version_id).first()
        return self._ver_to_domain(model) if model else None

    def get_current_version(self, document_id: UUID) -> Optional[DocumentVersion]:
        model = (
            self.db.query(DocumentVersionModel)
            .filter(
                DocumentVersionModel.document_id == document_id,
                DocumentVersionModel.status == VersionStatus.CURRENT,
            )
            .first()
        )
        return self._ver_to_domain(model) if model else None

    def list_versions(self, document_id: UUID) -> List[DocumentVersion]:
        models = (
            self.db.query(DocumentVersionModel)
            .filter(DocumentVersionModel.document_id == document_id)
            .order_by(DocumentVersionModel.version_number.desc())
            .all()
        )
        return [self._ver_to_domain(m) for m in models]

    def update_version_status(
        self,
        version_id: UUID,
        new_status: VersionStatus,
        supersedes_id: Optional[UUID] = None,
    ) -> None:
        model = self.db.query(DocumentVersionModel).filter(DocumentVersionModel.version_id == version_id).first()
        if not model:
            return

        # If marking CURRENT, supersede any existing current version
        if new_status == VersionStatus.CURRENT:
            current_versions = (
                self.db.query(DocumentVersionModel)
                .filter(
                    DocumentVersionModel.document_id == model.document_id,
                    DocumentVersionModel.status == VersionStatus.CURRENT,
                    DocumentVersionModel.version_id != version_id,
                )
                .all()
            )
            for cv in current_versions:
                cv.status = VersionStatus.SUPERSEDED

        model.status = new_status
        if supersedes_id:
            model.supersedes_id = supersedes_id
        self.db.commit()

    def get_allowed_version_ids(self, user_role: Role) -> Set[UUID]:
        if user_role == Role.ADMIN:
            versions = (
                self.db.query(DocumentVersionModel.version_id)
                .filter(DocumentVersionModel.status == VersionStatus.CURRENT)
                .all()
            )
        else:
            versions = (
                self.db.query(DocumentVersionModel.version_id)
                .join(DocumentModel, DocumentVersionModel.document_id == DocumentModel.document_id)
                .join(DocumentPermissionModel, DocumentModel.document_id == DocumentPermissionModel.document_id)
                .filter(
                    DocumentVersionModel.status == VersionStatus.CURRENT,
                    DocumentPermissionModel.role == user_role,
                )
                .all()
            )
        return {v[0] for v in versions}

    def save_chunks(self, chunks: List[DocumentChunk]) -> None:
        if not chunks:
            return
        version_id = chunks[0].version_id
        # Delete prior chunks for this version to make retry idempotent
        self.db.query(DocumentChunkModel).filter(DocumentChunkModel.version_id == version_id).delete()

        models = [
            DocumentChunkModel(
                chunk_id=c.chunk_id,
                version_id=c.version_id,
                chunk_index=c.chunk_index,
                page_start=c.page_start,
                page_end=c.page_end,
                section_heading=c.section_heading,
                chunk_text=c.chunk_text,
                token_count=c.token_count,
                attributes=c.attributes,
            )
            for c in chunks
        ]
        self.db.bulk_save_objects(models)
        self.db.commit()

    def get_chunk(self, chunk_id: UUID) -> Optional[DocumentChunk]:
        model = self.db.query(DocumentChunkModel).filter(DocumentChunkModel.chunk_id == chunk_id).first()
        return self._chunk_to_domain(model) if model else None

    def get_chunks_by_ids(self, chunk_ids: List[UUID]) -> List[DocumentChunk]:
        models = self.db.query(DocumentChunkModel).filter(DocumentChunkModel.chunk_id.in_(chunk_ids)).all()
        return [self._chunk_to_domain(m) for m in models]

    def get_chunks_for_version(self, version_id: UUID) -> List[DocumentChunk]:
        models = (
            self.db.query(DocumentChunkModel)
            .filter(DocumentChunkModel.version_id == version_id)
            .order_by(DocumentChunkModel.chunk_index.asc())
            .all()
        )
        return [self._chunk_to_domain(m) for m in models]

    def create_job(self, job: IngestionJob) -> IngestionJob:
        model = IngestionJobModel(
            job_id=job.job_id,
            version_id=job.version_id,
            status=job.status,
            error=job.error,
            started_at=job.started_at,
            finished_at=job.finished_at,
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return self._job_to_domain(model)

    def update_job(self, job: IngestionJob) -> IngestionJob:
        model = self.db.query(IngestionJobModel).filter(IngestionJobModel.job_id == job.job_id).first()
        if model:
            model.status = job.status
            model.error = job.error
            model.started_at = job.started_at
            model.finished_at = job.finished_at
            self.db.commit()
            self.db.refresh(model)
            return self._job_to_domain(model)
        return job

    def get_job_by_version(self, version_id: UUID) -> Optional[IngestionJob]:
        model = (
            self.db.query(IngestionJobModel)
            .filter(IngestionJobModel.version_id == version_id)
            .order_by(IngestionJobModel.started_at.desc())
            .first()
        )
        return self._job_to_domain(model) if model else None
