"""
Document ingestion use case.
Orchestrates text extraction, chunking, and persistence with job state tracking.
"""
from datetime import datetime
import os
from uuid import UUID

from app.adapters.extraction.docx_extractor import DocxExtractor
from app.adapters.extraction.pymupdf_extractor import PyMuPDFExtractor
from app.application.ports import DocumentRepoPort
from app.application.use_cases.chunker import DocumentChunker
from app.domain.entities import IngestionJob, JobStatus


def run_ingestion_pipeline(
    version_id: UUID,
    job_id: UUID,
    file_path: str,
    doc_repo: DocumentRepoPort,
) -> None:
    job = doc_repo.get_job_by_version(version_id)
    if not job:
        job = IngestionJob(job_id=job_id, version_id=version_id)

    job.status = JobStatus.EXTRACTING
    job.started_at = datetime.utcnow()
    doc_repo.update_job(job)

    try:
        # Extract text based on file format
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            extractor = PyMuPDFExtractor()
            extracted = extractor.extract(file_path)
        elif ext == ".docx":
            extractor = DocxExtractor()
            extracted = extractor.extract(file_path)
        else:
            raise ValueError(f"Unsupported format: {ext}")

        # Update version page count
        version = doc_repo.get_version(version_id)
        if version:
            version.page_count = extracted.total_pages

        # Transition to chunking
        job.status = JobStatus.CHUNKING
        doc_repo.update_job(job)

        chunker = DocumentChunker()
        chunks = chunker.chunk_document(extracted, version_id)

        # Save chunks in database
        doc_repo.save_chunks(chunks)

        # Mark completed
        job.status = JobStatus.COMPLETED
        job.finished_at = datetime.utcnow()
        doc_repo.update_job(job)

    except Exception as e:
        job.status = JobStatus.FAILED
        job.error = str(e)
        job.finished_at = datetime.utcnow()
        doc_repo.update_job(job)
        raise e
