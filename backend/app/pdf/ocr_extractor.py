import logging
import fitz
from typing import Any

logger = logging.getLogger(__name__)

class OCRExtractor:
    @staticmethod
    def extract_ocr_pymupdf(file_path: str, doc_id: str, ExtractionResult, TextBlock) -> Any:
        """OCR extraction using PyMuPDF's built-in capabilities."""
        result = ExtractionResult(doc_id=doc_id)
        doc = fitz.open(file_path)
        result.total_pages = len(doc)

        for page_num in range(len(doc)):
            page = doc[page_num]
            mat = fitz.Matrix(3, 3)
            pix = page.get_pixmap(matrix=mat)
            text = page.get_text("text", flags=fitz.TEXT_PRESERVE_WHITESPACE)

            if text.strip():
                for line in text.strip().split('\n'):
                    if line.strip():
                        result.text_blocks.append(TextBlock(
                            text=line.strip(),
                            page=page_num + 1,
                            block_type="text",
                            confidence=0.7
                        ))
            else:
                text_instances = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
                for block in text_instances.get("blocks", []):
                    if block.get("type") == 0:
                        for line in block.get("lines", []):
                            line_text = ""
                            for span in line.get("spans", []):
                                line_text += span.get("text", "")
                            if line_text.strip():
                                result.text_blocks.append(TextBlock(
                                    text=line_text.strip(),
                                    page=page_num + 1,
                                    bbox=block.get("bbox"),
                                    block_type="text",
                                    confidence=0.6
                                ))
        doc.close()
        return result
