"""
Ordered, switchable pipeline steps for hybrid document retrieval.
Implements Reciprocal Rank Fusion (RRF), dual-layer role filtering, and evidence gating.
"""
from typing import Dict, List, Set, Tuple
from uuid import UUID

from app.domain.entities import DocumentChunk, Role, VersionStatus


def reciprocal_rank_fusion(
    vector_hits: List[Tuple[UUID, int, float]],
    keyword_hits: List[Tuple[UUID, int, float]],
    k: int = 60,
    top_n: int = 8,
) -> List[Tuple[UUID, float, Dict[str, int]]]:
    """
    Combines dense vector search results and sparse keyword search results
    using Reciprocal Rank Fusion (RRF):
    score = sum(1.0 / (k + rank)) across both ranked lists.
    Returns sorted list of (chunk_id, fused_score, {vector_rank, keyword_rank}).
    """
    scores: Dict[UUID, float] = {}
    ranks_meta: Dict[UUID, Dict[str, int]] = {}

    for cid, rank, _ in vector_hits:
        scores[cid] = scores.get(cid, 0.0) + (1.0 / (k + rank))
        if cid not in ranks_meta:
            ranks_meta[cid] = {}
        ranks_meta[cid]["vector_rank"] = rank

    for cid, rank, _ in keyword_hits:
        scores[cid] = scores.get(cid, 0.0) + (1.0 / (k + rank))
        if cid not in ranks_meta:
            ranks_meta[cid] = {}
        ranks_meta[cid]["keyword_rank"] = rank

    # Sort descending by fused score
    sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    fused_results = [
        (cid, score, ranks_meta.get(cid, {}))
        for cid, score in sorted_items[:top_n]
    ]
    return fused_results


def check_evidence_gate(
    fused_candidates: List[Tuple[UUID, float, Dict[str, int]]],
    min_evidence_score: float = 0.015,
) -> bool:
    """
    Evidence Gate: returns True if candidate evidence passes the quality threshold.
    If best fused score is below min_evidence_score or candidates are empty, returns False.
    """
    if not fused_candidates:
        return False
    best_score = fused_candidates[0][1]
    return best_score >= min_evidence_score
