"""
Citation validation rules for University Document Intelligence.
Pure domain logic verifying that generated answers are grounded in retrieved chunks.
"""
from typing import Dict, List, Optional, Set, Tuple
from uuid import UUID

from app.domain.entities import Citation, Document, DocumentChunk, DocumentVersion
from app.domain.access_policy import STANDARD_ABSTAIN_MESSAGE


def validate_citations(
    cited_numbers: List[int],
    prompt_chunks_map: Dict[int, DocumentChunk],
) -> Tuple[bool, List[DocumentChunk]]:
    """
    Validates that cited numbers map 1-to-1 with chunks supplied in the prompt.
    Returns (is_valid, list_of_matching_chunks).
    """
    if not cited_numbers:
        return False, []

    valid_chunks: List[DocumentChunk] = []
    for num in cited_numbers:
        if num not in prompt_chunks_map:
            return False, []
        valid_chunks.append(prompt_chunks_map[num])

    return True, valid_chunks


def build_citations(
    cited_numbers: List[int],
    prompt_chunks_map: Dict[int, DocumentChunk],
    versions_map: Dict[UUID, DocumentVersion],
    documents_map: Dict[UUID, Document],
    max_snippet_chars: int = 250,
) -> List[Citation]:
    """
    Resolves citation metadata into structured Citation domain objects.
    """
    citations: List[Citation] = []
    seen_numbers: Set[int] = set()

    for num in cited_numbers:
        if num in seen_numbers or num not in prompt_chunks_map:
            continue
        seen_numbers.add(num)
        chunk = prompt_chunks_map[num]
        version = versions_map.get(chunk.version_id)
        doc = documents_map.get(version.document_id) if version else None

        snippet = chunk.chunk_text[:max_snippet_chars].strip()
        if len(chunk.chunk_text) > max_snippet_chars:
            snippet += "..."

        citations.append(
            Citation(
                n=num,
                chunk_id=chunk.chunk_id,
                document_id=doc.document_id if doc else chunk.version_id,
                document_title=doc.title if doc else "University Document",
                version_number=version.version_number if version else 1,
                page_start=chunk.page_start,
                section_heading=chunk.section_heading,
                snippet=snippet,
            )
        )

    return sorted(citations, key=lambda c: c.n)
