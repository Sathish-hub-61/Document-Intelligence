"""
python-docx extractor for Word documents.
Extracts paragraphs and headings while preserving document section hierarchy.
"""
from typing import List, Optional
import docx

from app.adapters.extraction.pymupdf_extractor import ExtractedBlock, ExtractedDocument


class DocxExtractor:
    def extract(self, file_path: str) -> ExtractedDocument:
        doc = docx.Document(file_path)
        blocks: List[ExtractedBlock] = []
        current_heading: Optional[str] = None

        # DOCX doesn't have fixed pagination; we estimate page boundaries based on ~300 words/page
        word_count = 0
        current_page = 1

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue

            words = len(text.split())
            word_count += words
            if word_count > 300:
                current_page += 1
                word_count = words

            # Check heading style
            style_name = para.style.name if para.style else ""
            is_heading = style_name.startswith("Heading") or (len(text) < 100 and any(run.bold for run in para.runs))

            if is_heading:
                current_heading = text
                blocks.append(
                    ExtractedBlock(
                        page_number=current_page,
                        text=text,
                        section_heading=current_heading,
                        is_heading=True,
                    )
                )
            else:
                blocks.append(
                    ExtractedBlock(
                        page_number=current_page,
                        text=text,
                        section_heading=current_heading,
                        is_heading=False,
                    )
                )

        return ExtractedDocument(
            total_pages=max(1, current_page),
            blocks=blocks,
            has_scanned_pages=False,
        )

