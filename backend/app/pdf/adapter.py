import logging
from typing import List, Dict, Any, Optional
import pandas as pd
from docling_core.types.doc.document import (
    DoclingDocument,
    TextItem,
    TableItem,
    SectionHeaderItem,
)
from docling_core.types.doc.labels import DocItemLabel

from app.pdf.legacy_compat import (
    ExtractionResult,
    TextBlock,
    ExtractedTable,
    AdvancedChunk,
)
from app.pdf.chunker import FlysisHybridChunker

logger = logging.getLogger(__name__)


class UnifiedFlysisAdapter:

    def __init__(self, chunker: Optional[FlysisHybridChunker] = None):
        self.chunker = chunker or FlysisHybridChunker()

    def docling_to_extraction_result(
        self,
        doc: DoclingDocument,
        doc_id: str,
        processing_time_ms: int = 0,
    ) -> ExtractionResult:
        result = ExtractionResult(doc_id=doc_id)
        result.methods_used = ["docling_doclaynet", "docling_tableformer"]
        result.total_pages = len(doc.pages) if hasattr(doc, "pages") and doc.pages else 1
        result.processing_time_ms = processing_time_ms
        result.confidence = 0.98

        text_blocks: List[TextBlock] = []
        outline_items: List[Dict[str, Any]] = []
        current_section = "Document Overview"
        current_heading_path: List[str] = []

        try:
            for item, level in doc.iterate_items():
                if isinstance(item, TextItem):
                    t_text = item.text.strip() if item.text else ""
                    if not t_text:
                        continue

                    page_no = 1
                    bbox = None
                    if hasattr(item, "prov") and item.prov:
                        first_prov = item.prov[0]
                        page_no = getattr(first_prov, "page_no", 1)
                        if hasattr(first_prov, "bbox") and first_prov.bbox:
                            b = first_prov.bbox
                            bbox = [float(b.l), float(b.t), float(b.r), float(b.b)]

                    is_heading = (
                        isinstance(item, SectionHeaderItem)
                        or item.label in (DocItemLabel.SECTION_HEADER, DocItemLabel.TITLE)
                    )
                    block_type = "heading" if is_heading else "text"

                    if is_heading:
                        current_section = t_text
                        current_heading_path = [t_text]
                        outline_items.append(
                            {"level": level if level is not None else 1, "title": t_text, "page": page_no}
                        )

                    text_blocks.append(
                        TextBlock(
                            text=t_text,
                            page=page_no,
                            bbox=bbox,
                            block_type=block_type,
                            confidence=0.98,
                            heading_path=list(current_heading_path),
                            section=current_section,
                        )
                    )
        except Exception as e:
            logger.warning(f"[UnifiedFlysisAdapter] Error iterating text items: {e}")

        tables: List[ExtractedTable] = []
        try:
            for t_item in doc.tables:
                page_no = 1
                bbox = None
                if hasattr(t_item, "prov") and t_item.prov:
                    first_prov = t_item.prov[0]
                    page_no = getattr(first_prov, "page_no", 1)
                    if hasattr(first_prov, "bbox") and first_prov.bbox:
                        b = first_prov.bbox
                        bbox = [float(b.l), float(b.t), float(b.r), float(b.b)]

                try:
                    df: pd.DataFrame = t_item.export_to_dataframe(doc=doc)
                    headers = [str(c) for c in df.columns.tolist()]
                    rows = [[str(val) for val in row] for row in df.values.tolist()]
                    matrix_data = [headers] + rows
                except Exception as df_err:
                    logger.debug(f"DataFrame export failed, fallback: {df_err}")
                    matrix_data = [["Table Content"]]
                    headers = ["Table Content"]

                try:
                    md_text = t_item.export_to_markdown(doc=doc)
                except Exception:
                    md_text = ""

                tables.append(
                    ExtractedTable(
                        page=page_no,
                        rows=len(matrix_data),
                        cols=len(headers),
                        data=matrix_data,
                        confidence=0.98,
                        extraction_method="docling_tableformer",
                        bbox=bbox,
                        markdown=md_text,
                    )
                )
        except Exception as e:
            logger.warning(f"[UnifiedFlysisAdapter] Error iterating tables: {e}")

        try:
            advanced_chunks = self.chunker.chunk_docling_document(doc)
        except Exception as e:
            logger.error(f"[UnifiedFlysisAdapter] Chunker error: {e}")
            advanced_chunks = []

        try:
            full_markdown = doc.export_to_markdown()
        except Exception:
            full_markdown = "\n\n".join(b.text for b in text_blocks)

        result.text_blocks = text_blocks
        result.tables = tables
        result.outline = outline_items
        result.chunks_advanced = advanced_chunks
        result.markdown = full_markdown
        return result

    @staticmethod
    def to_canonical_dict(result: ExtractionResult, include_metadata: bool = True) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "text_blocks": [
                {
                    "text": b.text,
                    "page": b.page,
                    "type": b.block_type,
                    "section": b.section,
                    "heading_path": b.heading_path or [],
                    **({"confidence": b.confidence} if include_metadata else {}),
                    **({"bbox": b.bbox} if b.bbox else {}),
                }
                for b in result.text_blocks
            ],
            "tables": [
                {
                    "page": t.page,
                    "rows": t.rows,
                    "cols": t.cols,
                    "data": t.data,
                    "method": t.extraction_method,
                    "markdown": t.markdown,
                    **({"confidence": t.confidence} if include_metadata else {}),
                    **({"bbox": t.bbox} if t.bbox else {}),
                }
                for t in result.tables
            ],
            "chunks_advanced": [
                {
                    "chunk_id": c.chunk_id,
                    "text": c.text,
                    "page_start": c.page_start,
                    "page_end": c.page_end,
                    "heading_path": c.heading_path,
                    "chunk_type": c.chunk_type,
                    "token_estimate": c.token_estimate,
                    "boundary_reason": c.boundary_reason,
                }
                for c in result.chunks_advanced
            ],
            "outline": result.outline,
            "analyzer_report": result.analyzer_report or {},
            "markdown": result.markdown,
        }

        if include_metadata:
            data["document_id"] = result.doc_id
            data["total_pages"] = result.total_pages
            data["processing_time_ms"] = result.processing_time_ms
            data["methods_used"] = result.methods_used
            data["confidence"] = result.confidence
            data["metadata"] = result.metadata

        return data
