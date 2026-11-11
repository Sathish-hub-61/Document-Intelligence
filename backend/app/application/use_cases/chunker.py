"""
Section-aware chunking pipeline.
Splits extracted document blocks into ~600-token chunks with 80-token overlap,
preserving page ranges and nearest section headings.
"""
from typing import List, Optional
from uuid import UUID

from app.adapters.extraction.pymupdf_extractor import ExtractedDocument
from app.composition.settings import get_settings
from app.domain.entities import DocumentChunk


def estimate_token_count(text: str) -> int:
    """
    Approximates token count (avg 1.3 tokens per word).
    """
    words = len(text.split())
    return max(1, int(words * 1.3))


class DocumentChunker:
    def __init__(self, target_tokens: Optional[int] = None, overlap_tokens: Optional[int] = None):
        settings = get_settings()
        self.target_tokens = target_tokens or settings.chunk_tokens
        self.overlap_tokens = overlap_tokens or settings.chunk_overlap

    def chunk_document(
        self,
        extracted: ExtractedDocument,
        version_id: UUID,
    ) -> List[DocumentChunk]:
        chunks: List[DocumentChunk] = []
        chunk_index = 0

        current_heading: Optional[str] = None
        current_paragraphs: List[str] = []
        page_start: Optional[int] = None
        page_end: Optional[int] = None
        accumulated_tokens = 0

        for block in extracted.blocks:
            if block.needs_ocr:
                continue

            if block.is_heading:
                # Flush previous chunk before starting a new section if it has meaningful content
                if current_paragraphs and accumulated_tokens >= self.target_tokens * 0.5:
                    chunk_text = "\n\n".join(current_paragraphs).strip()
                    if chunk_text:
                        chunks.append(
                            DocumentChunk(
                                version_id=version_id,
                                chunk_index=chunk_index,
                                page_start=page_start or 1,
                                page_end=page_end or page_start or 1,
                                section_heading=current_heading,
                                chunk_text=chunk_text,
                                token_count=estimate_token_count(chunk_text),
                            )
                        )
                        chunk_index += 1
                        current_paragraphs = []
                        accumulated_tokens = 0
                        page_start = None
                        page_end = None

                current_heading = block.text
                continue

            block_tokens = estimate_token_count(block.text)

            if page_start is None:
                page_start = block.page_number
            page_end = block.page_number

            current_paragraphs.append(block.text)
            accumulated_tokens += block_tokens

            # If accumulated tokens exceed target, create chunk with overlap
            if accumulated_tokens >= self.target_tokens:
                chunk_text = "\n\n".join(current_paragraphs).strip()
                chunks.append(
                    DocumentChunk(
                        version_id=version_id,
                        chunk_index=chunk_index,
                        page_start=page_start,
                        page_end=page_end,
                        section_heading=current_heading,
                        chunk_text=chunk_text,
                        token_count=estimate_token_count(chunk_text),
                    )
                )
                chunk_index += 1

                # Keep trailing paragraph for overlap if available
                if len(current_paragraphs) > 1:
                    overlap_para = current_paragraphs[-1]
                    current_paragraphs = [overlap_para]
                    accumulated_tokens = estimate_token_count(overlap_para)
                    page_start = block.page_number
                else:
                    current_paragraphs = []
                    accumulated_tokens = 0
                    page_start = None
                    page_end = None

        # Flush final remaining chunk
        if current_paragraphs:
            chunk_text = "\n\n".join(current_paragraphs).strip()
            if chunk_text:
                chunks.append(
                    DocumentChunk(
                        version_id=version_id,
                        chunk_index=chunk_index,
                        page_start=page_start or 1,
                        page_end=page_end or page_start or 1,
                        section_heading=current_heading,
                        chunk_text=chunk_text,
                        token_count=estimate_token_count(chunk_text),
                    )
                )

        return chunks

