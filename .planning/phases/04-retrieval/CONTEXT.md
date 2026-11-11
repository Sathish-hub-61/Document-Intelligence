# Phase 4: Hybrid Retrieval and Strict Permission Filtering - Context

## Objective
Implement the hybrid retrieval engine combining dense vector search (ChromaDB) and sparse keyword search (PostgreSQL), fused via Reciprocal Rank Fusion (RRF, k=60), backed by the dual-layer role-based permission verification model that guarantees zero restricted chunk leaks, with complete retrieval trace auditing.

## Specifications (Blueprint Section 4.2 & 6.1)
- Allowed Set: Computed first based on user role and version status (current).
- Vector Search: Top 20 from ChromaDB with role metadata pre-filter.
- Keyword Search: Top 20 from PostgreSQL full-text joined against allowed versions.
- RRF Fusion: `score = sum(1 / (60 + rank))` over vector and keyword rankings, keeping top 8 candidates.
- Authoritative Re-Check: Chunks verified against PostgreSQL permission join; non-permitted chunks dropped.
- Evidence Gate: If best fused score < 0.015 or candidates < 1, trigger abstention.
- Tracing: Record candidate IDs, ranks, scores, and prompt chunk IDs.

