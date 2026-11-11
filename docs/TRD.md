# Technical Requirements Document (TRD): University Document Intelligence

## 1. System Parameters
- Chunk size: ~600 tokens with 80 tokens overlap.
- Embedding model: Sentence Transformers `BAAI/bge-small-en-v1.5` (384-dimensional).
- Vector store: ChromaDB persistent client with role flags (`role_student`, `role_faculty`, `role_staff`, `role_admin`).
- Sparse search: PostgreSQL `tsvector` with GIN index over headings and chunk text.
- Merge algorithm: Reciprocal Rank Fusion (RRF, k=60), score = sum of 1 / (60 + rank).
- Candidate limits: Top 20 vector hits, Top 20 keyword hits, Top 8 fused candidates, Top 5 prompt chunks.
- Minimum evidence score: 0.015 threshold.
- Upload limits: 25 MB max file size, PDF and DOCX only, magic byte validation.

## 2. Ingestion Pipeline
1. Magic byte check + SHA-256 duplicate validation.
2. Store file under UUID filename in `storage/original_documents/`.
3. Create document record (or version) + ingestion job in `queued` state.
4. Extract text per page (PyMuPDF) or per section (python-docx). Flag pages yielding < 30 characters as `needs_ocr`.
5. Section-aware chunking with token count and nearest section heading.
6. Write chunks to PostgreSQL `document_chunks` table (`tsv` populated automatically).
7. Compute embeddings in batch and upsert to ChromaDB with role metadata flags.
8. Update job state to `completed`.

## 3. Retrieval & Access Verification
1. Parse user query, perform regex PII redaction.
2. Determine user's active role from session/token verified against DB.
3. Fetch allowed version IDs from DB (`status == 'current'` and role permitted).
4. Run ChromaDB search filtered by `role_<role> == true` and `status == 'current'`.
5. Run PostgreSQL full-text search filtered by `version_id IN (allowed_versions)`.
6. Merge lists via RRF.
7. Post-merge authoritative verification: re-query DB to verify every chunk ID is strictly allowed.
8. Gate check: if best score < threshold or chunks < 1, abstain without calling LLM.

## 4. Generation & Citations
1. LLMPort invoked with grounded prompt contract and numbered context chunks.
2. Enforce JSON schema output: `{ "answer": str, "citations": [int], "sufficient": bool }`.
3. Citation validation: all cited numbers must map to supplied chunks. If no valid citation is present, replace with neutral abstain message.
4. Store retrieval trace and message citations in database.
