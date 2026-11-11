# Phase 2: Document Ingestion, Extraction and Chunking - Context

## Objective
Build the document ingestion pipeline: file signature and size validation, SHA-256 deduplication, local secure file storage, page-aware text extraction for PDF (PyMuPDF) and DOCX (python-docx), section heading tracking, section-aware chunking (~600 tokens, 80 overlap), background ingestion job state machine, and document management endpoints.

## Specifications (Blueprint Section 4.1 & 6.2)
- Allowed formats: PDF and DOCX only. Check magic bytes (`%PDF` and `PK\x03\x04`), 25 MB limit.
- Deduplication: SHA-256 of file content; reject duplicate file for the same document (409 conflict).
- Secure storage: Stored under `<uuid>.ext` in `storage/original_documents/`.
- Text extraction: PyMuPDF page-by-page preserving exact page number; flag pages with < 30 chars as `needs_ocr`. Python-docx preserves headings and paragraphs.
- Chunking: Section-aware chunking, ~600 tokens, 80 tokens overlap, preserving `page_start`, `page_end`, and `section_heading`.
- Job tracking: `queued` -> `extracting` -> `chunking` -> `completed` (or `failed`).
- Endpoints: `POST /api/documents` (admin, 202 Accepted), `GET /api/documents`, `GET /api/documents/{id}`, `GET /api/versions/{id}/jobs`, `GET /api/chunks/{id}`.
