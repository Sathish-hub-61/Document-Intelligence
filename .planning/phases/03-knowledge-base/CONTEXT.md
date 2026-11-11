# Phase 3: Knowledge Base, Embeddings and Full-Text Indexing - Context

## Objective
Implement dense vector embeddings using Sentence Transformers (`BAAI/bge-small-en-v1.5`), persistent ChromaDB indexing with role metadata flags (`role_student`, `role_faculty`, `role_staff`, `role_admin`), PostgreSQL full-text search indexing (`tsvector` + GIN), and version reindexing capability.

## Specifications (Blueprint Section 7.3 & 12.1)
- Model: `BAAI/bge-small-en-v1.5` yielding 384-dimensional dense vectors on CPU.
- ChromaDB collection `chunks` with cosine distance.
- Metadata flags on Chroma chunks: `document_id`, `version_id`, `page_start`, `status`, `role_student`, `role_faculty`, `role_staff`, `role_admin`.
- Keyword index: queries chunks using full-text search matching section headings and text, filtered by allowed version IDs.
- Ingestion step: batches embeddings and upserts to ChromaDB upon document chunking.
- Reindex endpoint: `POST /api/versions/{id}/reindex`.

