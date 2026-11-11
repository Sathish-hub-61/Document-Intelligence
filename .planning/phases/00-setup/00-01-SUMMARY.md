---
phase: 00
plan: 01
title: Scaffolding, Domain Entities, Application Ports and Settings
status: completed
completed_at: 2026-11-11
---

# Plan 00-01 Summary: Project Setup and Hexagonal Architecture Scaffolding

## Deliverables Completed
1. **Environment and Build Scaffolding**:
   - `CLAUDE.md`: rules, folder layout, commands, and constraints from Blueprint Section 10.
   - `.env.example` and `.env`: tunable parameters per Section 4.5.
   - `docker-compose.yml`: PostgreSQL 16 container definition.
   - `Makefile`: `up`, `down`, `backend`, `frontend`, `test`, `lint`, `eval`.
   - `.gitignore`: complete ignore rules for python, node, storage, and secrets.
   - `docs/PRD.md` and `docs/TRD.md`: generated from the Blueprint.

2. **Clean / Hexagonal Backend Scaffolding**:
   - `backend/app/domain/entities.py`: pure domain models (`User`, `Document`, `DocumentVersion`, `DocumentChunk`, `Role`, `VersionStatus`, `IngestionJob`, `JobStatus`, `ChatMessage`, `Citation`, `RetrievalTrace`, `AuditLog`).
   - `backend/app/domain/access_policy.py`: allowed-set computation, role authorization rules, and post-merge authoritative chunk filtering.
   - `backend/app/domain/citation_rules.py`: verification that all cited indices map to prompt chunks.
   - `backend/app/domain/errors.py`: domain exceptions mapped to system error types.
   - `backend/app/application/ports.py`: interfaces for `LLMPort`, `EmbeddingPort`, `VectorStorePort`, `KeywordIndexPort`, `DocumentRepoPort`, `UserRepoPort`, `ChatRepoPort`, `FileStoragePort`, `PiiRedactorPort`.
   - `backend/app/composition/settings.py` & `container.py`: Pydantic settings loading all tunable parameters and dependency injection container.
   - `backend/app/adapters/persistence/`: database connection and SQLAlchemy ORM models matching Blueprint Section 7.2.
   - `backend/app/adapters/llm/fake_llm.py`: FakeLLM implementing `LLMPort` for deterministic unit testing.
   - `backend/app/adapters/api/`: FastAPI entrypoint with `/api/health`, Pydantic schemas, and error handlers.

3. **Frontend Scaffolding**:
   - `frontend/package.json`: React 18, Vite, TypeScript, Tailwind CSS, TanStack Query.
   - `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/tailwind.config.js`.
   - `frontend/src/App.tsx`, `frontend/src/main.tsx`, `frontend/src/index.css`.

4. **Testing & Verification**:
   - `backend/tests/unit/test_phase0_setup.py`: 6 tests covering entities, access policy, post-merge authoritative chunk filtering, citation rules, FakeLLM, and `/api/health`. All 6 passed.
