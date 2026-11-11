"""
PyMuPDF extractor for PDF documents.
Extracts text page-by-page preserving exact page numbers, section headings,
and flags pages with < 30 characters as needs_ocr.
"""
from dataclasses import dataclass
from typing import List, Optional
import fitz  # PyMuPDF


@dataclass
class ExtractedBlock:
    page_number: int
    text: str
    section_heading: Optional[str] = None
    is_heading: bool = False
    needs_ocr: bool = False


@dataclass
class ExtractedDocument:
    total_pages: int
    blocks: List[ExtractedBlock]
    has_scanned_pages: bool = False


class PyMuPDFExtractor:
    def extract(self, file_path: str) -> ExtractedDocument:
        doc = fitz.open(file_path)
        total_pages = len(doc)
        blocks: List[ExtractedBlock] = []
        has_scanned = False
        current_heading: Optional[str] = None

        for page_idx in range(total_pages):
            page_num = page_idx + 1
            page = doc[page_idx]
            page_text = page.get_text().strip()

            # If page yields under 30 characters, mark needs_ocr
            if len(page_text) < 30:
                has_scanned = True
                blocks.append(
                    ExtractedBlock(
                        page_number=page_num,
                        text=page_text,
                        section_heading=current_heading,
                        needs_ocr=True,
                    )
                )
                continue

            # Analyze text blocks for headings and paragraphs
            page_dict = page.get_text("dict")
            for b in page_dict.get("blocks", []):
                if b.get("type") != 0:  # 0 is text block
                    continue

                block_lines = []
                is_heading = False
                max_font_size = 0.0

                for line in b.get("lines", []):
                    line_text = "".join(span.get("text", "") for span in line.get("spans", [])).strip()
                    if not line_text:
                        continue
                    block_lines.append(line_text)
                    for span in line.get("spans", []):
                        size = span.get("size", 10.0)
                        flags = span.get("flags", 0)  # flag 2 is bold
                        if size > max_font_size:
                            max_font_size = size
                        # Font size > 13 or bold title format marks a heading
                        if (size >= 13.0 or (flags & 2 and size >= 11.0)) and len(line_text) < 120:
                            is_heading = True

                block_content = "\n".join(block_lines).strip()
                if not block_content:
                    continue

                if is_heading and len(block_content) < 120:
                    current_heading = block_content
                    blocks.append(
                        ExtractedBlock(
                            page_number=page_num,
                            text=block_content,
                            section_heading=current_heading,
                            is_heading=True,
                        )
                    )
                else:
                    blocks.append(
                        ExtractedBlock(
                            page_number=page_num,
                            text=block_content,
                            section_heading=current_heading,
                            is_heading=False,
                        )
                    )

        doc.close()
        return ExtractedDocument(
            total_pages=total_pages,
            blocks=blocks,
            has_scanned_pages=has_scanned,
        )

