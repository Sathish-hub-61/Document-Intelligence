# University Document Intelligence

RAG assistant for university documents. Admins upload, users ask, answers cite sources.
Hard constraints: no student or faculty records; role checks in the backend; restricted
chunks never reach the LLM; answers need valid citations or the system abstains.

## Layout
backend/app/domain         entities and pure rules (no framework imports)
backend/app/application    use cases and port interfaces
backend/app/adapters       FastAPI routes, Postgres, Chroma, LLM, OCR, storage
backend/app/composition    dependency wiring
frontend/                  React + Vite + TypeScript
docs/                      PRD, TRD, ADRs, ai-log.md, memory notes

## Commands
make up        start Postgres (Docker Compose)
make test      pytest + frontend tests
make lint      ruff + mypy + eslint
make eval      run the gold question set

## Rules
- Dependencies point inward. Domain imports no framework.
- Routes call one use case. No SQL or business logic in routes.
- Every external service is behind a port with a fake for tests.
- Add a test with every change. Run make test and make lint before finishing.
- Schema changes through Alembic only. Never edit applied migrations.
- Never put secrets or real documents in git. Use .env and sample docs.
- Tunable numbers come from Settings, not literals.

## Workflow
1. Read docs/PRD.md and docs/TRD.md for the phase you are on.
2. Write a short plan, then wait for approval on anything touching auth or retrieval.
3. Implement one phase deliverable at a time. Keep diffs small.
4. Update docs/memory/progress.md and docs/memory/decisions.md when done.

## Do not
- Do not call an LLM or vector store directly from routes or domain code.
- Do not trust the frontend for authorization.
- Do not log raw user questions, tokens, or document text.

