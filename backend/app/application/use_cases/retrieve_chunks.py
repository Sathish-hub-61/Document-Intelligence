"""
Hybrid retrieval use case orchestrating dual-layer role filtering, dense/sparse search,
Reciprocal Rank Fusion, post-merge authoritative verification, and evidence gating.
"""
from typing import Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4

from app.application.pipeline.retrieval_steps import check_evidence_gate, reciprocal_rank_fusion
from app.application.ports import DocumentRepoPort, EmbeddingPort, KeywordIndexPort, VectorStorePort
from app.composition.settings import get_settings
from app.domain.access_policy import filter_authorized_chunks
from app.domain.entities import DocumentChunk, RetrievalTrace, Role, VersionStatus


class HybridRetrievalUseCase:
    def __init__(
        self,
        doc_repo: DocumentRepoPort,
        embedding_adapter: EmbeddingPort,
        vector_store: VectorStorePort,
        keyword_index: KeywordIndexPort,
    ):
        self.doc_repo = doc_repo
        self.embedding_adapter = embedding_adapter
        self.vector_store = vector_store
        self.keyword_index = keyword_index
        self.settings = get_settings()

    def execute(
        self,
        query: str,
        user_role: Role,
        message_id: Optional[UUID] = None,
    ) -> Tuple[List[DocumentChunk], RetrievalTrace, bool]:
        """
        Executes the hybrid retrieval pipeline.
        Returns:
            - List[DocumentChunk]: permitted context chunks to be sent to LLM.
            - RetrievalTrace: complete diagnostic trace of candidates and scores.
            - bool: True if evidence passed the gate, False if system must abstain.
        """
        msg_id = message_id or uuid4()

        # Step 1: Pre-filter - compute allowed version IDs for this user role
        allowed_version_ids: Set[UUID] = self.doc_repo.get_allowed_version_ids(user_role)
        if not allowed_version_ids:
            trace = RetrievalTrace(
                message_id=msg_id,
                allowed_versions=0,
                vector_hits=[],
                keyword_hits=[],
                fused=[],
                sent_to_llm=[],
            )
            return [], trace, False

        # Step 2: Dense Vector Search (ChromaDB with metadata role flag pre-filter)
        query_vector = self.embedding_adapter.embed_query(query)
        vector_hits = self.vector_store.search(
            query_vector=query_vector,
            user_role=user_role,
            top_k=self.settings.top_k_vector,
            status=VersionStatus.CURRENT,
        )

        # Step 3: Sparse Keyword Search (PostgreSQL full-text joined to allowed_versions)
        keyword_hits = self.keyword_index.search(
            query_text=query,
            allowed_version_ids=allowed_version_ids,
            top_k=self.settings.top_k_keyword,
        )

        # Step 4: Reciprocal Rank Fusion (RRF)
        fused = reciprocal_rank_fusion(
            vector_hits=vector_hits,
            keyword_hits=keyword_hits,
            k=60,
            top_n=self.settings.top_k_final,
        )

        # Step 5: Evidence Gate Check
        passed_gate = check_evidence_gate(
            fused_candidates=fused,
            min_evidence_score=self.settings.min_evidence_score,
        )
        if not passed_gate:
            trace = RetrievalTrace(
                message_id=msg_id,
                allowed_versions=len(allowed_version_ids),
                vector_hits=[{"chunk_id": str(cid), "rank": r, "score": sc} for cid, r, sc in vector_hits],
                keyword_hits=[{"chunk_id": str(cid), "rank": r, "score": sc} for cid, r, sc in keyword_hits],
                fused=[{"chunk_id": str(cid), "score": sc, "ranks": rm} for cid, sc, rm in fused],
                sent_to_llm=[],
            )
            return [], trace, False

        # Step 6: Post-Merge Authoritative Database Verification
        fused_chunk_ids = [cid for cid, _, _ in fused]
        candidate_chunks = self.doc_repo.get_chunks_by_ids(fused_chunk_ids)

        # Re-order chunks according to fused ranking
        chunk_map = {c.chunk_id: c for c in candidate_chunks}
        ordered_chunks = [chunk_map[cid] for cid in fused_chunk_ids if cid in chunk_map]

        # Authoritative filter: strictly drops any chunk outside allowed versions
        authorized_chunks = filter_authorized_chunks(user_role, allowed_version_ids, ordered_chunks)

        # Cap to top 5 prompt chunks
        final_chunks = authorized_chunks[:5]

        trace = RetrievalTrace(
            message_id=msg_id,
            allowed_versions=len(allowed_version_ids),
            vector_hits=[{"chunk_id": str(cid), "rank": r, "score": sc} for cid, r, sc in vector_hits],
            keyword_hits=[{"chunk_id": str(cid), "rank": r, "score": sc} for cid, r, sc in keyword_hits],
            fused=[{"chunk_id": str(cid), "score": sc, "ranks": rm} for cid, sc, rm in fused],
            sent_to_llm=[c.chunk_id for c in final_chunks],
        )

        if not final_chunks:
            return [], trace, False

        return final_chunks, trace, True
