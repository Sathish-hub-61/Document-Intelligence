# University Document Intelligence

## What This Is

A correct, permission-safe university document assistant and RAG platform. Administrators upload official documents (regulations, circulars, calendars, procedures in PDF/DOCX), the system ingests, extracts headings and pages, chunks, and indexes them in PostgreSQL and ChromaDB. Users (Students, Faculty, Staff, Admins) ask questions in natural language, and answers are generated strictly from authorized documents with verifiable citations (document, version, page, section heading) or the system abstains when evidence is insufficient.

## Core Value

Correct, strictly grounded answers with verifiable page-level citations from official university documents, guaranteed by dual-layer role-based access filtering where unauthorized chunks never reach the LLM prompt.

## Requirements

### Validated

(None yet — milestone greenfield)

### Active

- [ ] **SEC-01**: Dual-layer role-based access control (pre-retrieval allowed set filtering and post-merge authoritative database verification) ensuring restricted content never enters an LLM prompt.
- [ ] **ING-01**: Document upload (.pdf, .docx), signature validation, SHA-256 deduplication, page-aware text extraction (PyMuPDF, python-docx), section heading tracking, and chunking with metadata.
- [ ] **RET-01**: Hybrid search combining dense vector search (ChromaDB with `BAAI/bge-small-en-v1.5`) and sparse keyword search (PostgreSQL full-text `tsvector` with GIN index), fused via Reciprocal Rank Fusion (RRF).
- [ ] **GEN-01**: Grounded answer generation using LLMPort (Gemini/OpenAI/Fake), strict citation enforcement (valid citations required or abstain), evidence gate, and PII redaction on user queries.
- [ ] **VER-01**: Version lifecycle management (draft, current, superseded, archived), effective dates, and as-of retrieval preserving citations to historical versions.
- [ ] **UI-01**: React 18 + Vite + TypeScript web application with Chat interface, citation popover/source panel, and Admin document management console.
- [ ] **EVAL-01**: Automated evaluation suite with a 60-question gold benchmark testing retrieval hit rate, answer correctness, citation accuracy, abstention rate, and permission leak tests.

### Out of Scope

- Student and faculty personal records / grades / transcripts — explicitly excluded to prevent data privacy liabilities.
- University SSO integration in v1 — local JWT auth with Argon2 hashes used for the capstone/v1.
- Document editing by non-administrators — only admins can upload and manage documents.
- Mobile application — responsive web interface only.
- Multilingual translation / multilingual embedding models — English documents and queries for v1.
- Fine-tuned LLMs — prompt-grounded RAG with strict verification only.

## Context

- University rules and circulars sit scattered across complex PDFs and DOCX files with formatting, tables, and frequent revisions.
- Clean / Hexagonal architecture is required so that external components (LLM, vector DB, OCR, database) sit behind ports and adapters, allowing zero-cost testing with fake adapters and seamless model swapping.
- Automated leak tests are critical to prove to auditors and university administration that student roles cannot extract staff/faculty confidential policies.

## Constraints

- **Architecture**: Clean/Hexagonal architecture; dependencies point strictly inward toward domain; no framework or database imports in domain logic.
- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL 16.
- **Vector DB**: ChromaDB persistent client; embeddings generated with Sentence Transformers `BAAI/bge-small-en-v1.5`.
- **Frontend**: React 18, Vite, TypeScript, Tailwind CSS, TanStack Query.
- **Security**: Argon2 password hashing, short-lived JWT, server-side role resolution on every request, PII regex redaction.
- **Testing**: Pytest unit tests with fake ports achieving high domain coverage; integration tests; automated security leak test.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| PostgreSQL as authoritative source of truth | Prevents vector store metadata drift from leaking unauthorized content; permissions re-checked in DB | ✓ Good |
| Dual-layer role filtering | Pre-filter in Chroma for search speed + post-merge authoritative SQL join to guarantee zero leaks | ✓ Good |
| Strict JSON LLM citation contract | Prevents hallucinations; if an answer cannot be cited to retrieved chunks, system abstains | ✓ Good |
| Clean / Hexagonal ports | Enables rapid unit testing without network calls or API keys via FakeLLM and In-Memory Vector Store | ✓ Good |
