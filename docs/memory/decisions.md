# Architecture Decision Records (ADRs)

| ID | Title | Status | Date | Decision & Rationale |
|---|---|---|---|---|
| ADR-001 | Clean / Hexagonal Architecture | Accepted | 2026-11-11 | Adopt ports and adapters so domain code has no framework/network dependencies; permits instant testing with fakes and clean swapping of LLMs and vector stores. |
| ADR-002 | Dual-Layer Access Control | Accepted | 2026-11-11 | Chroma metadata role flags provide fast search pre-filtering, while authoritative PostgreSQL join before generation guarantees zero permission leaks. |
| ADR-003 | PostgreSQL as Source of Truth | Accepted | 2026-11-11 | Chunks and metadata reside in PostgreSQL; ChromaDB holds only embeddings and IDs. Vector store can be completely reconstructed from database. |
| ADR-004 | Reciprocal Rank Fusion (RRF) | Accepted | 2026-11-11 | Merges dense vector results (semantic matches) with PostgreSQL full-text (exact terms and codes) without calibrating arbitrary score scales. |
| ADR-005 | Strict JSON Citation Contract | Accepted | 2026-11-11 | The LLM must output structured JSON with chunk citation indices. Answers lacking verifiable citations are replaced with standard neutral abstention. |

