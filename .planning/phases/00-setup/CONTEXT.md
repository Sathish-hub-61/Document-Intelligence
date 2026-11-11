# Phase 0: Project Setup and Hexagonal Scaffolding - Context

## Objective
Establish the foundational infrastructure, directory layout, Docker Compose configuration, FastAPI backend skeleton, React Vite frontend skeleton, database migration configuration (Alembic), domain models, and port interfaces following Clean / Hexagonal architecture.

## Architecture Blueprint Reference
- Backend: Clean/Hexagonal architecture where domain contains pure entities and access policies without framework dependencies.
- Application layer defines ports (interfaces) for all external boundaries (LLM, vector DB, persistence, storage, PII redaction, embeddings).
- Adapters implement ports with both concrete adapters and test fakes (FakeLLM, InMemoryVectorStore, MockStorage).
- Composition layer wires settings and dependencies.
- Docker Compose configures PostgreSQL 16 on port 5432.
- Testing infrastructure setup with pytest.
