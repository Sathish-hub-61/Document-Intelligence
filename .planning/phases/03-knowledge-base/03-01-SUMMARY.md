---
phase: 03
plan: 01
title: Embeddings Adapter, Persistent Chroma Store, Full-Text Index and Reindexing API
status: completed
completed_at: 2026-11-11
---

# Plan 03-01 Summary: Knowledge Base, Embeddings and Search Indexing

## Deliverables Completed
1. **Sentence Transformers Dense Embeddings**:
   - `backend/app/adapters/embeddings/sentence_transformers.py`: `SentenceTransformerEmbeddingAdapter` implementing `EmbeddingPort` using `BAAI/bge-small-en-v1.5` generating 384-dimensional normalized vectors with asymmetric query prefixes and deterministic hash fallback for offline test environments.

2. **Persistent ChromaDB Vector Store with Role Pre-Filtering**:
   - `backend/app/adapters/vector/chroma_store.py`: `ChromaVectorStore` implementing `VectorStorePort` with collection `chunks` and cosine distance.
   - Metadata flags per chunk: `document_id`, `version_id`, `page_start`, `status`, `role_admin`, `role_student`, `role_faculty`, `role_staff`.
   - Query pre-filtering using `$and` syntax enforces `status == current` and `role_<user_role> == True`, preventing non-authorized chunks from being queried.

3. **Full-Text Keyword Search**:
   - `backend/app/adapters/search/pg_fulltext.py`: `PostgresFullTextSearch` implementing `KeywordIndexPort` supporting PostgreSQL `websearch_to_tsquery` ranking and SQLite keyword fallback, joined strictly to the allowed version IDs.

4. **Ingestion Embedding & Indexing Integration**:
   - `backend/app/application/use_cases/ingest_document.py`: integrated embedding generation and vector upsert into `run_ingestion_pipeline` across job states `embedding` and `indexing`.

5. **Reindexing Endpoint**:
   - `backend/app/adapters/api/routers/documents.py`: `POST /api/versions/{version_id}/reindex` admin endpoint triggering background re-extraction, embedding, and vector upsert.

6. **Automated Verification**:
   - `backend/tests/unit/test_phase3_indexing.py`: tests for embedding dimensions, Chroma role flag isolation (student cannot see confidential faculty chunks), keyword search filtering, and reindex API. All 20 tests in the suite passed.

