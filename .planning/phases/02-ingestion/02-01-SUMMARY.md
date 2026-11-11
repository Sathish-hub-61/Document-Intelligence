---
phase: 02
plan: 01
title: File Validation, Extractors, Section Chunker, Ingestion Runner and Document API
status: completed
completed_at: 2026-11-11
---

# Plan 02-01 Summary: Document Ingestion, Extraction and Chunking Pipeline

## Deliverables Completed
1. **File Validation & Secure Storage**:
   - `backend/app/adapters/storage/local_files.py`: `LocalFileStorage` validating magic bytes (`%PDF` for PDF, `PK\x03\x04` for DOCX), rejecting files exceeding 25 MB or spoofed files, computing SHA-256 hashes, and storing under UUID filenames in `storage/original_documents/`.

2. **Page-Aware Text Extractors**:
   - `backend/app/adapters/extraction/pymupdf_extractor.py`: `PyMuPDFExtractor` extracting page-by-page text, detecting font size and bold formatting for headings, preserving exact page numbers, and flagging pages with < 30 characters as `needs_ocr`.
   - `backend/app/adapters/extraction/docx_extractor.py`: `DocxExtractor` preserving paragraph and heading styles and estimating page boundaries.

3. **Section-Aware Chunking Engine**:
   - `backend/app/application/use_cases/chunker.py`: `DocumentChunker` splitting text into ~600-token chunks with 80-token overlap, retaining `version_id`, `chunk_index`, `page_start`, `page_end`, and `section_heading`.

4. **Document Repository Persistence**:
   - `backend/app/adapters/persistence/repositories.py`: expanded `SqlAlchemyDocumentRepo` supporting full CRUD for documents, versions, chunks, and ingestion jobs with idempotent chunk updates on re-ingestion.

5. **Ingestion Orchestrator**:
   - `backend/app/application/use_cases/ingest_document.py`: `run_ingestion_pipeline()` managing job transitions (`queued` -> `extracting` -> `chunking` -> `completed` / `failed`).

6. **Document API Endpoints**:
   - `backend/app/adapters/api/routers/documents.py`:
     - `POST /api/documents`: admin upload returning `202 Accepted` with background job processing.
     - `GET /api/documents`: lists documents accessible to the caller's role.
     - `GET /api/documents/{id}`: retrieves document metadata (returns 404 for unauthorized documents).
     - `GET /api/versions/{id}/jobs`: retrieves ingestion job status.
     - `GET /api/chunks/{id}`: fetches citation source chunk with permission check.
     - `GET /api/files/{version_id}`: streams original file with permission check.

7. **Verification Tests**:
   - `backend/tests/unit/test_phase2_ingestion.py`: tests for magic bytes validation, PDF/DOCX extraction, chunking, and API upload/job flow. All 16 tests in the test suite passed.

