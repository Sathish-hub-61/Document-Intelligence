"""
Document ingestion use case.
Orchestrates text extraction, chunking, embedding generation, and vector indexing with job state tracking.
"""
from datetime import datetime
import os
from typing import Optional
from uuid import UUID

from app.adapters.embeddings.sentence_transformers import SentenceTransformerEmbeddingAdapter
from app.adapters.extraction.docx_extractor import DocxExtractor
from app.adapters.extraction.pymupdf_extractor import PyMuPDFExtractor
from app.adapters.vector.chroma_store import ChromaVectorStore
from app.application.ports import DocumentRepoPort, EmbeddingPort, VectorStorePort
from app.application.use_cases.chunker import DocumentChunker
from app.domain.entities import IngestionJob, JobStatus


def run_ingestion_pipeline(
    version_id: UUID,
    job_id: UUID,
    file_path: str,
    doc_repo: DocumentRepoPort,
    embedding_adapter: Optional[EmbeddingPort] = None,
    vector_store: Optional[VectorStorePort] = None,
) -> None:
    job = doc_repo.get_job_by_version(version_id)
    if not job:
        job = IngestionJob(job_id=job_id, version_id=version_id)

    job.status = JobStatus.EXTRACTING
    job.started_at = datetime.utcnow()
    doc_repo.update_job(job)

    try:
        # 1. Extraction
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            extractor = PyMuPDFExtractor()
            extracted = extractor.extract(file_path)
        elif ext == ".docx":
            extractor = DocxExtractor()
            extracted = extractor.extract(file_path)
        else:
            raise ValueError(f"Unsupported format: {ext}")

        version = doc_repo.get_version(version_id)
        if version:
            version.page_count = extracted.total_pages

        # 2. Chunking
        job.status = JobStatus.CHUNKING
        doc_repo.update_job(job)

        chunker = DocumentChunker()
        chunks = chunker.chunk_document(extracted, version_id)
        doc_repo.save_chunks(chunks)

        # 3. Embedding & Indexing
        if chunks:
            job.status = JobStatus.EMBEDDING
            doc_repo.update_job(job)

            embedder = embedding_adapter or SentenceTransformerEmbeddingAdapter()
            texts = [f"{c.section_heading or ''}\n{c.chunk_text}".strip() for c in chunks]
            embeddings = embedder.embed_documents(texts)

            job.status = JobStatus.INDEXING
            doc_repo.update_job(job)

            vstore = vector_store or ChromaVectorStore()
            doc = doc_repo.get_document(version.document_id) if version else None
            allowed_roles = doc.allowed_roles if doc else []
            roles_per_chunk = [allowed_roles for _ in chunks]

            vstore.upsert_chunks(
                chunks=chunks,
                embeddings=embeddings,
                allowed_roles_per_chunk=roles_per_chunk,
                status=version.status if version else JobStatus.COMPLETED,
                document_id=version.document_id if version else None,
            )

        # 4. Completed
        job.status = JobStatus.COMPLETED
        job.finished_at = datetime.utcnow()
        doc_repo.update_job(job)

    except Exception as e:
        job.status = JobStatus.FAILED
        job.error = str(e)
        job.finished_at = datetime.utcnow()
        doc_repo.update_job(job)
        raise e
