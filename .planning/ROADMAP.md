# Roadmap: University Document Intelligence

## Overview

This roadmap implements the University Document Intelligence platform following Clean/Hexagonal architecture, strict role-based access filtering before LLM retrieval, and verifiable citations. Starting with core repository scaffolding, database schema, and domain ports, the workflow proceeds through authentication, document ingestion/extraction, vector & full-text indexing, hybrid retrieval with RRF, grounded RAG answering with zero-leak citation validation, document version lifecycle, a modern React/TypeScript frontend, comprehensive evaluation with a 60-question gold benchmark, and system demonstration tuning.

## Phases

- [x] **Phase 0: Project Setup and Hexagonal Scaffolding** - Establish repository layout, Docker Compose PostgreSQL 16, FastAPI backend skeleton, React Vite frontend skeleton, Alembic migrations, and core domain entities & ports.
- [x] **Phase 1: Authentication, Authorization and Roles** - Implement users table, Argon2 password hashing, JWT authentication, `require_role` FastAPI dependency, seeded users, and document permission enforcement.
- [x] **Phase 2: Document Ingestion, Extraction and Chunking** - Implement file validation, PyMuPDF and python-docx text extractors, section heading and page tracking, chunking pipeline, and background ingestion job tracking.
- [x] **Phase 3: Knowledge Base, Embeddings and Full-Text Indexing** - Implement Sentence Transformers `BAAI/bge-small-en-v1.5` embeddings, persistent ChromaDB indexing with role flags, and PostgreSQL full-text search (`tsvector` + GIN).
- [ ] **Phase 4: Hybrid Retrieval and Strict Permission Filtering** - Implement hybrid retrieval pipeline (dense vector + sparse full-text), Reciprocal Rank Fusion (RRF), dual-layer role filtering (pre-filter and post-merge authoritative SQL join), and retrieval traces.
- [ ] **Phase 5: Grounded RAG Generation, Citations and PII Redaction** - Implement `LLMPort` adapter (Gemini/OpenAI/Fake), strict grounded prompt contract, citation checker, abstain gate, PII query redaction, chat sessions with follow-ups, and automated leak tests.
- [ ] **Phase 6: Document Versioning, Lifecycle and As-Of Retrieval** - Implement version management (draft, current, superseded, archived), effective dates, atomic publishing, and versioned citation persistence.
- [ ] **Phase 7: Frontend Web Application** - Build React 18 + Vite + TypeScript interface with Tailwind CSS: Chat workspace, citation popover/source panel, document catalog, and Admin document management console.
- [ ] **Phase 8: Evaluation Framework and Benchmark** - Build 60-question gold benchmark, evaluation runner, and automated scoring for hit rate @ 5, answer correctness, citation accuracy, and security leak absence.
- [ ] **Phase 9: Tuning, Diagnostics Trace Drawer and Demonstration** - Optimize tunable parameters, implement admin trace drawer, complete documentation, architecture diagrams, and rehearsed demo scripts.

## Phase Details

### Phase 0: Project Setup and Hexagonal Scaffolding
**Goal**: Set up repository structure, development environment, Docker Compose for PostgreSQL, FastAPI skeleton, React Vite skeleton, Alembic migrations setup, and hexagonal domain entities and ports.
**Depends on**: Nothing (first phase)
**Requirements**: AUTH-01, INGEST-01
**Success Criteria**:
  1. Repository layout matches Clean Architecture specification (`backend/app/{domain,application,adapters,composition}`, `frontend/`, `docs/`).
  2. Docker Compose starts PostgreSQL 16 container, and Alembic migrations run cleanly.
  3. Domain entities (`User`, `Role`, `Document`, `Version`, `Chunk`) and application ports (`LLMPort`, `VectorStorePort`, `EmbeddingPort`, `DocumentRepoPort`, `AuthzPort`, `FileStoragePort`) defined with zero framework dependencies.
  4. Backend `/api/health` returns operational status for database and services; test suite runs with pytest.
**Plans**: 1 plan

Plans:
- [x] 00-01: Initialize repository layout, Docker Compose PostgreSQL, FastAPI skeleton, React skeleton, Alembic setup, domain entities and ports.

### Phase 1: Authentication, Authorization and Roles
**Goal**: Implement complete authentication, role-based access control, JWT issuance/validation, and document permission models.
**Depends on**: Phase 0
**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-04
**Success Criteria**:
  1. Users table created with Argon2 password hashing and user roles (`student`, `faculty`, `staff`, `admin`).
  2. Seed script populates four test users (one for each role) and an admin account.
  3. `POST /api/auth/login` verifies credentials and returns 30-minute JWT; `/api/auth/me` returns current user and role.
  4. `require_role` dependency protects routes, correctly returning 200, 403, or 404 based on caller permissions.
**Plans**: 1 plan

Plans:
- [x] 01-01: Implement user persistence, Argon2 hashing, JWT service, auth endpoints, role guard dependencies, and permission verification service.

### Phase 2: Document Ingestion, Extraction and Chunking
**Goal**: Build document upload, validation, page-aware text extraction from PDF and DOCX, section heading detection, and chunking pipeline.
**Depends on**: Phase 1
**Requirements**: INGEST-01, INGEST-02, INGEST-03, INGEST-04, INGEST-05
**Success Criteria**:
  1. `POST /api/documents` accepts PDF and DOCX files up to 25 MB, validates magic bytes, checks SHA-256 for duplicates, and creates draft version and ingestion job.
  2. PyMuPDF extracts text page-by-page preserving page numbers; python-docx extracts paragraphs and headings.
  3. Chunker splits text by sections into ~600-token chunks with 80-token overlap, tagging each chunk with `page_start`, `page_end`, and `section_heading`.
  4. Ingestion job state machine tracks progress (`queued` -> `extracting` -> `chunking` -> `completed`/`failed`) and writes chunks to PostgreSQL.
**Plans**: 1 plan

Plans:
- [x] 02-01: Implement upload validation, file storage adapter, PyMuPDF and DOCX extractors, section-aware chunker, and background ingestion job runner.

### Phase 3: Knowledge Base, Embeddings and Full-Text Indexing
**Goal**: Implement dense vector embeddings with Sentence Transformers, ChromaDB indexing with role metadata flags, and PostgreSQL full-text search indexing.
**Depends on**: Phase 2
**Requirements**: INDEX-01, INDEX-02, INDEX-03, INDEX-04
**Success Criteria**:
  1. Embedding adapter generates 384-dimensional embeddings using `BAAI/bge-small-en-v1.5` on CPU.
  2. Persistent ChromaDB collection stores chunk embeddings with role flags (`role_student`, `role_faculty`, `role_staff`, `role_admin`) and `status`.
  3. PostgreSQL `document_chunks` table maintains `tsv` full-text column with GIN index combining headings and chunk text.
  4. Admin can trigger reindex endpoint to regenerate vector and full-text indexes.
**Plans**: 1 plan

Plans:
- [x] 03-01: Implement Sentence Transformers embedding adapter, persistent ChromaDB adapter with role flags, PostgreSQL full-text search adapter, and reindexing use case.

### Phase 4: Hybrid Retrieval and Strict Permission Filtering
**Goal**: Implement hybrid search, Reciprocal Rank Fusion (RRF), and dual-layer role-based permission filtering guaranteeing zero leaks.
**Depends on**: Phase 3
**Requirements**: RETRIEVE-01, RETRIEVE-02, RETRIEVE-03, RETRIEVE-04, RETRIEVE-05, RETRIEVE-06, RETRIEVE-07
**Success Criteria**:
  1. Dense vector search in ChromaDB queries top 20 chunks with role flag metadata pre-filtering.
  2. Sparse keyword search in PostgreSQL queries top 20 chunks joined against allowed versions for the user's role.
  3. Reciprocal Rank Fusion (RRF, k=60) merges both candidate lists into top candidates.
  4. Authoritative post-merge SQL join checks every chunk against PostgreSQL permissions; non-permitted chunks are strictly eliminated.
  5. Evidence gate verifies score and chunk count; retrieval traces recorded in database for auditing.
**Plans**: 1 plan

Plans:
- [ ] 04-01: Implement hybrid retrieval service, RRF merging algorithm, dual-layer permission filter, evidence gate, and retrieval trace persistence.

### Phase 5: Grounded RAG Generation, Citations and PII Redaction
**Goal**: Implement LLM generation behind LLMPort with strict grounded prompt contract, citation checker, abstain gate, PII redaction, and automated leak test.
**Depends on**: Phase 4
**Requirements**: GEN-01, GEN-02, GEN-03, GEN-04, GEN-05, GEN-06, EVAL-03
**Success Criteria**:
  1. Regex PII redactor removes registration numbers, emails, and phone numbers from user queries prior to LLM submission.
  2. `LLMPort` supports Gemini, OpenAI, and FakeLLM adapters with structured JSON output contract.
  3. Citation validation confirms every citation number corresponds to a supplied context chunk; answers failing citation validation trigger abstention.
  4. Abstain gate returns standard neutral message when evidence is insufficient or when access is forbidden.
  5. Chat sessions and follow-up query rewriting functional.
  6. Automated security leak test proves zero restricted chunks reach prompts across student, faculty, staff roles.
**Plans**: 1 plan

Plans:
- [ ] 05-01: Implement PII redactor, LLM adapters, grounded prompt contract, citation validator, abstain gate, chat session management, and automated leak tests.

### Phase 6: Document Versioning, Lifecycle and As-Of Retrieval
**Goal**: Implement document version lifecycle (draft, current, superseded, archived), effective dates, and as-of retrieval.
**Depends on**: Phase 5
**Requirements**: VER-01, VER-02, VER-03, VER-04
**Success Criteria**:
  1. Admin can upload version n+1 to an existing document in draft status.
  2. Publishing a version atomically sets it to `current`, updates the superseded version to `superseded`, and updates ChromaDB status flags.
  3. Search queries retrieve only `current` versions by default, while historical citations retain access to superseded versions.
  4. Version audit trail records status transitions and publication history.
**Plans**: 1 plan

Plans:
- [ ] 06-01: Implement version publishing transaction, status updates, ChromaDB status synchronization, and historical citation access.

### Phase 7: Frontend Web Application
**Goal**: Build a responsive React + Vite + TypeScript frontend with Tailwind CSS featuring a Chat workspace, Citation Source Panel, and Admin Document Management.
**Depends on**: Phase 6
**Requirements**: UI-01, UI-02, UI-03, UI-04, UI-05, UI-06
**Success Criteria**:
  1. Login screen with role-based routing and session management.
  2. Chat workspace with message history, step indicators, answer cards, and clickable citation chips that open the source panel at the cited page.
  3. Document catalog for browsing accessible documents by department and status.
  4. Admin console with file upload form, ingestion progress tracking, version status toggles, and role permission editor.
  5. Diagnostic Trace Drawer for reviewing retrieval ranks, allowed sets, and prompt chunks in demo mode.
**Plans**: 1 plan

Plans:
- [ ] 07-01: Implement React frontend application with authentication, chat workspace, citation source viewer, document browser, and admin management console.

### Phase 8: Evaluation Framework and Benchmark
**Goal**: Build a 60-question gold benchmark and automated evaluation runner measuring retrieval hit rate, correctness, citations, and abstention.
**Depends on**: Phase 7
**Requirements**: EVAL-01, EVAL-02, EVAL-03
**Success Criteria**:
  1. 60-question gold benchmark covering regulations, circulars, calendars, procedures, role-restricted queries, and unanswerable questions.
  2. Evaluation runner executes the benchmark and computes metrics (Hit Rate @ 5, answer correctness, citation accuracy, abstention rate, zero leaks).
  3. Evaluation results persisted to `eval_runs` and `eval_results` tables with reporting CLI/API.
**Plans**: 1 plan

Plans:
- [ ] 08-01: Implement 60-question gold dataset, evaluation runner service, metric scoring algorithms, and evaluation reporting endpoints.

### Phase 9: Tuning, Diagnostics Trace Drawer and Demonstration
**Goal**: Optimize tunable parameters, finalize diagnostics trace drawer, comprehensive documentation, architecture diagrams, and rehearsed demo flow.
**Depends on**: Phase 8
**Requirements**: UI-06, RETRIEVE-07
**Success Criteria**:
  1. Tunable parameters (chunk size, overlap, top-K, evidence threshold) calibrated against gold evaluation results.
  2. Trace drawer fully integrated into UI with complete visibility into hybrid search stages.
  3. Complete README, architecture diagrams, API documentation, and step-by-step demo script.
  4. Complete system verified end-to-end with green tests across all layers.
**Plans**: 1 plan

Plans:
- [ ] 09-01: Calibrate parameters, finalize diagnostics drawer, document end-to-end demo flow, and run final system verification.
