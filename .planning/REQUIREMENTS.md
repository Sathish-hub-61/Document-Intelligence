# Requirements: University Document Intelligence

**Defined:** 2026-11-11
**Core Value:** Correct, strictly grounded answers with verifiable page-level citations from official university documents, guaranteed by dual-layer role-based access filtering where unauthorized chunks never reach the LLM prompt.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Authentication & Authorization (AUTH)

- [ ] **AUTH-01**: Admin can register users with roles (`admin`, `student`, `faculty`, `staff`).
- [ ] **AUTH-02**: Users can log in using email and password, receiving a short-lived (30-minute) JWT access token with password verified via Argon2.
- [ ] **AUTH-03**: Protected endpoints verify user identity and check database role on every request via FastAPI dependency `require_role`.
- [ ] **AUTH-04**: Role-based document access permissions table maps documents to allowed roles (`admin`, `student`, `faculty`, `staff`).

### Document Ingestion & Storage (INGEST)

- [ ] **INGEST-01**: Admin can upload `.pdf` and `.docx` documents up to 25 MB with title, type, department, allowed roles, and effective dates.
- [ ] **INGEST-02**: System validates magic bytes (file signature) and checks SHA-256 hash to reject duplicate uploads for the same document.
- [ ] **INGEST-03**: System extracts text page-by-page from PDFs using PyMuPDF and paragraphs/headings from DOCX using python-docx.
- [ ] **INGEST-04**: System detects section headings and page boundaries, splitting content into ~600-token chunks with 80-token overlap without losing page references.
- [ ] **INGEST-05**: System records background ingestion jobs (`queued`, `extracting`, `chunking`, `embedding`, `indexing`, `completed`, `failed`) and stores chunks in PostgreSQL.

### Knowledge Base & Indexing (INDEX)

- [ ] **INDEX-01**: System generates 384-dimensional dense embeddings for chunks using Sentence Transformers (`BAAI/bge-small-en-v1.5`).
- [ ] **INDEX-02**: System upserts embeddings into a persistent ChromaDB collection with role flags (`role_student`, `role_faculty`, `role_staff`, `role_admin`) and status.
- [ ] **INDEX-03**: System maintains a PostgreSQL full-text search column (`tsv` `tsvector` with GIN index) combining section headings and chunk text.
- [ ] **INDEX-04**: Admin can trigger reindexing of any document version to rebuild vector and full-text indexes.

### Hybrid Retrieval & Access Control (RETRIEVE)

- [ ] **RETRIEVE-01**: System pre-filters allowed versions based on the querying user's active role and current status.
- [ ] **RETRIEVE-02**: System executes dense vector search in ChromaDB (top 20) with role flag filters.
- [ ] **RETRIEVE-03**: System executes sparse keyword search in PostgreSQL full-text (top 20) joined against the allowed versions set.
- [ ] **RETRIEVE-04**: System merges vector and keyword results using Reciprocal Rank Fusion (RRF with k=60) to yield top candidate chunks.
- [ ] **RETRIEVE-05**: System re-checks every fused candidate chunk against PostgreSQL permissions; unauthorized chunks are dropped immediately.
- [ ] **RETRIEVE-06**: System evaluates evidence threshold; if fused score is below threshold or candidate chunks are empty, retrieval gates out the LLM call.
- [ ] **RETRIEVE-07**: System logs complete retrieval traces (candidate IDs, scores, allowed-set size, prompt chunks) for auditability.

### Generation, Citations & Privacy (RAG)

- [ ] **GEN-01**: System sanitizes user question with PII regex redaction (registration numbers, student IDs, emails, phone numbers) before passing to the LLM.
- [ ] **GEN-02**: System prompts LLM via `LLMPort` with strict grounded prompt contract to answer solely from numbered context chunks.
- [ ] **GEN-03**: System requires LLM to output structured JSON containing answer, citation references, and sufficiency boolean.
- [ ] **GEN-04**: System validates citations against prompt chunk IDs; if citations are invalid or empty for an asserted fact, system abstains.
- [ ] **GEN-05**: System abstains with a neutral standard message when evidence is insufficient or when unauthorized documents are queried, revealing no document existence.
- [ ] **GEN-06**: Chat sessions maintain conversation history for follow-up questions, rewriting follow-ups into standalone queries while running independent permission checks on each turn.

### Version Management & Lifecycle (VER)

- [ ] **VER-01**: Admin can upload new revisions of existing documents as draft versions (n+1) without deleting old versions.
- [ ] **VER-02**: Admin can publish versions, atomically transitioning a draft to `current` and marking prior current versions as `superseded`.
- [ ] **VER-03**: Document versions record effective dates (`effective_from`, `effective_to`), and queries default to `current` versions.
- [ ] **VER-04**: Historical citations retain direct access to superseded chunks and original files without appearing in current search results.

### User Interface (UI)

- [ ] **UI-01**: Responsive web interface built with React 18, Vite, TypeScript, and Tailwind CSS.
- [ ] **UI-02**: Secure login screen with role-based navigation and token session management.
- [ ] **UI-03**: Chat workspace displaying message history, loading step indicators, answer cards with interactive citation chips, and collapsible Source Panel showing exact page and passage.
- [ ] **UI-04**: Document catalog view for browsing accessible documents by department, type, and current version.
- [ ] **UI-05**: Admin management console for uploading documents, monitoring ingestion job progress, managing version statuses, and assigning role permissions.
- [ ] **UI-06**: Diagnostic Trace Drawer (accessible in admin/demo mode) visualizing allowed-set count, vector/keyword ranks, fusion scores, and prompt chunks.

### Evaluation & Verification (EVAL)

- [ ] **EVAL-01**: Automated evaluation suite with a 60-question gold benchmark covering all document types, roles, and edge cases.
- [ ] **EVAL-02**: Automated scoring of retrieval hit rate @ 5, answer correctness, citation accuracy, and proper abstention on unanswerable questions.
- [ ] **EVAL-03**: Automated security leak test verifying that restricted documents and chunks never appear in retrieval traces or prompts for unauthorized roles.

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUTH-01 | Phase 1 | Pending |
| AUTH-02 | Phase 1 | Pending |
| AUTH-03 | Phase 1 | Pending |
| AUTH-04 | Phase 1 | Pending |
| INGEST-01 | Phase 2 | Pending |
| INGEST-02 | Phase 2 | Pending |
| INGEST-03 | Phase 2 | Pending |
| INGEST-04 | Phase 2 | Pending |
| INGEST-05 | Phase 2 | Pending |
| INDEX-01 | Phase 3 | Pending |
| INDEX-02 | Phase 3 | Pending |
| INDEX-03 | Phase 3 | Pending |
| INDEX-04 | Phase 3 | Pending |
| RETRIEVE-01 | Phase 4 | Pending |
| RETRIEVE-02 | Phase 4 | Pending |
| RETRIEVE-03 | Phase 4 | Pending |
| RETRIEVE-04 | Phase 4 | Pending |
| RETRIEVE-05 | Phase 4 | Pending |
| RETRIEVE-06 | Phase 4 | Pending |
| RETRIEVE-07 | Phase 4 | Pending |
| GEN-01 | Phase 5 | Pending |
| GEN-02 | Phase 5 | Pending |
| GEN-03 | Phase 5 | Pending |
| GEN-04 | Phase 5 | Pending |
| GEN-05 | Phase 5 | Pending |
| GEN-06 | Phase 5 | Pending |
| VER-01 | Phase 6 | Pending |
| VER-02 | Phase 6 | Pending |
| VER-03 | Phase 6 | Pending |
| VER-04 | Phase 6 | Pending |
| UI-01 | Phase 7 | Pending |
| UI-02 | Phase 7 | Pending |
| UI-03 | Phase 7 | Pending |
| UI-04 | Phase 7 | Pending |
| UI-05 | Phase 7 | Pending |
| UI-06 | Phase 7 | Pending |
| EVAL-01 | Phase 8 | Pending |
| EVAL-02 | Phase 8 | Pending |
| EVAL-03 | Phase 8 | Pending |
