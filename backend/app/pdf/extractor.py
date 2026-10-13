import logging
from typing import List, Dict, Any, Optional

from app.pdf.legacy_compat import (
    ExtractionResult,
    TextBlock,
    ExtractedTable,
    AdvancedChunk,
)
from app.pdf.service import HybridPDFExtractionService

logger = logging.getLogger(__name__)


class PDFExtractionPipeline:
    def __init__(self, enable_ocr: bool = True):
        self.service = HybridPDFExtractionService()

    def extract(self, file_path: str, doc_id: str) -> ExtractionResult:
        return self.service.extract(file_path=file_path, doc_id=doc_id)

    def extract_tables_only(self, file_path: str, doc_id: Optional[str] = None) -> List[ExtractedTable]:
        return self.service.extract_tables_only(file_path=file_path, doc_id=doc_id)

