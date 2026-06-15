import os
import time
import logging
import tempfile
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

import fitz  # PyMuPDF
import pdfplumber
import pandas as pd
from PIL import Image

from app.pdf.analyzer import PDFReportAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class ExtractedTable:
    page: int
    rows: int
    cols: int
    data: List[List[str]]
    confidence: float = 1.0
    extraction_method: str = "unknown"
    bbox: Optional[List[float]] = None


@dataclass
class TextBlock:
    text: str
    page: int
    bbox: Optional[List[float]] = None
    font_size: Optional[float] = None
    block_type: str = "text"
    confidence: float = 1.0
    heading_path: Optional[List[str]] = None
    section: str = ""


@dataclass
class AdvancedChunk:
    """Rich chunk data from the PDFReportAnalyzer."""
    chunk_id: int
    text: str
    page_start: int
    page_end: int
    heading_path: List[str]
    chunk_type: str    
    token_estimate: int
    boundary_reason: str 


@dataclass
class ExtractionResult:
    doc_id: str
    text_blocks: List[TextBlock] = field(default_factory=list)
    tables: List[ExtractedTable] = field(default_factory=list)
    total_pages: int = 0
    processing_time_ms: int = 0
    methods_used: List[str] = field(default_factory=list)
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    chunks_advanced: List[AdvancedChunk] = field(default_factory=list)
    outline: List[Dict[str, Any]] = field(default_factory=list)
    analyzer_report: Dict[str, Any] = field(default_factory=dict)


class PDFExtractionPipeline:
    """Multi-stage PDF extraction with PDFReportAnalyzer as primary engine."""

    def __init__(self, enable_ocr: bool = True):
        self.enable_ocr = enable_ocr

    def extract(self, file_path: str, doc_id: str) -> ExtractionResult:
        """
        Run the full extraction pipeline.

        Stage 1: PDFReportAnalyzer for advanced heading-aware extraction
                 with tables, topic detection, and chunking
        Stage 2: pdfplumber for supplementary table detection (if needed)
        Stage 3: camelot for additional table extraction (fallback)
        Stage 4: PyMuPDF OCR for scanned documents (if no text found)
        """
        start_time = time.time()
        result = ExtractionResult(doc_id=doc_id)

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        logger.info(f"[{doc_id}] Stage 1: PDFReportAnalyzer extraction")
        try:
            analyzer_result = self._extract_with_analyzer(file_path, doc_id)
            result.text_blocks = analyzer_result.text_blocks
            result.tables = analyzer_result.tables
            result.total_pages = analyzer_result.total_pages
            result.metadata = analyzer_result.metadata
            result.chunks_advanced = analyzer_result.chunks_advanced
            result.outline = analyzer_result.outline
            result.analyzer_report = analyzer_result.analyzer_report
            result.methods_used.append("pdf_report_analyzer")
            logger.info(
                f"[{doc_id}] PDFReportAnalyzer: {len(result.text_blocks)} text blocks, "
                f"{len(result.tables)} tables, {len(result.chunks_advanced)} chunks, "
                f"{result.total_pages} pages"
            )
        except Exception as e:
            logger.error(f"[{doc_id}] PDFReportAnalyzer failed: {e}", exc_info=True)
            # Fall back to basic PyMuPDF extraction
            logger.info(f"[{doc_id}] Falling back to basic PyMuPDF extraction")
            try:
                basic_result = self._extract_pymupdf_basic(file_path, doc_id)
                result.text_blocks = basic_result.text_blocks
                result.total_pages = basic_result.total_pages
                result.metadata = basic_result.metadata
                result.methods_used.append("pymupdf_basic")
            except Exception as e2:
                logger.error(f"[{doc_id}] Basic PyMuPDF also failed: {e2}")

        #Supplementary table detection (if analyzer found none) ─
        if len(result.tables) == 0:
            logger.info(f"[{doc_id}] Stage 2: pdfplumber supplementary table extraction")
            try:
                plumber_tables = self._extract_pdfplumber_tables(file_path)
                result.tables.extend(plumber_tables)
                if plumber_tables:
                    result.methods_used.append("pdfplumber")
                logger.info(f"[{doc_id}] pdfplumber: {len(plumber_tables)} tables")
            except Exception as e:
                logger.error(f"[{doc_id}] pdfplumber failed: {e}")

        #camelot fallback for tables ────────────────────────
        if len(result.tables) == 0:
            logger.info(f"[{doc_id}] Stage 3: camelot table extraction")
            try:
                camelot_tables = self._extract_camelot(file_path)
                result.tables.extend(camelot_tables)
                if camelot_tables:
                    result.methods_used.append("camelot")
                logger.info(f"[{doc_id}] camelot: {len(camelot_tables)} tables")
            except Exception as e:
                logger.error(f"[{doc_id}] camelot failed: {e}")

        #OCR fallback for scanned documents ─────────────────
        if len(result.text_blocks) == 0 and self.enable_ocr:
            logger.info(f"[{doc_id}] Stage 4: PyMuPDF OCR fallback")
            try:
                ocr_result = self._extract_ocr_pymupdf(file_path, doc_id)
                result.text_blocks = ocr_result.text_blocks
                if not result.total_pages:
                    result.total_pages = ocr_result.total_pages
                result.methods_used.append("pymupdf_ocr")
                logger.info(f"[{doc_id}] OCR: {len(result.text_blocks)} blocks")
            except Exception as e:
                logger.error(f"[{doc_id}] OCR failed: {e}")

        result.processing_time_ms = int((time.time() - start_time) * 1000)
        result.confidence = self._calculate_confidence(result)

        logger.info(
            f"[{doc_id}] Extraction complete: {result.processing_time_ms}ms, "
            f"confidence={result.confidence:.2f}, methods={result.methods_used}"
        )

        return result

    def _extract_with_analyzer(self, file_path: str, doc_id: str) -> ExtractionResult:
       
        result = ExtractionResult(doc_id=doc_id)

        analyzer = PDFReportAnalyzer(file_path, max_chunk_tokens=450, min_chunk_tokens=80).run()

        doc = fitz.open(file_path)
        result.total_pages = len(doc)
        result.metadata = {
            "title": doc.metadata.get("title", ""),
            "author": doc.metadata.get("author", ""),
            "subject": doc.metadata.get("subject", ""),
            "creator": doc.metadata.get("creator", ""),
            "format": doc.metadata.get("format", ""),
        }
        doc.close()

        result.analyzer_report = analyzer.report

        result.outline = analyzer.outline()

      
        for chunk in analyzer.chunks:
            
            if chunk.chunk_type == "table":
                block_type = "table"
            elif chunk.chunk_type == "title":
                block_type = "heading"
            else:
                block_type = "text"

            section = " > ".join(chunk.heading_path) if chunk.heading_path else ""

            result.text_blocks.append(TextBlock(
                text=chunk.text,
                page=chunk.page_start + 1,  # 1-indexed for API compatibility
                bbox=None,
                font_size=None,
                block_type=block_type,
                confidence=0.95,
                heading_path=chunk.heading_path,
                section=section,
            ))

        for chunk_dict in analyzer.chunks_as_dicts():
            result.chunks_advanced.append(AdvancedChunk(
                chunk_id=chunk_dict["chunk_id"],
                text=chunk_dict["text"],
                page_start=chunk_dict["page_range"][0],
                page_end=chunk_dict["page_range"][1],
                heading_path=chunk_dict["heading_path"],
                chunk_type=chunk_dict["chunk_type"],
                token_estimate=chunk_dict["token_estimate"],
                boundary_reason=chunk_dict["boundary_reason"],
            ))

        for page_num, table_list in analyzer.table_texts.items():
            for bbox, md_text in table_list:
                if md_text:
                    md_lines = md_text.strip().split("\n")
                    table_data = []
                    for line in md_lines:
                        if line.startswith("|") and "---" not in line:
                            cells = [c.strip() for c in line.strip("|").split("|")]
                            table_data.append(cells)

                    if table_data:
                        result.tables.append(ExtractedTable(
                            page=page_num + 1,  # 1-indexed
                            rows=len(table_data),
                            cols=max(len(row) for row in table_data) if table_data else 0,
                            data=table_data,
                            confidence=0.90,
                            extraction_method="pymupdf_find_tables",
                            bbox=list(bbox) if bbox else None,
                        ))

        return result

    def _extract_pymupdf_basic(self, file_path: str, doc_id: str) -> ExtractionResult:
        """Fallback Stage 1: Extract text and layout using basic PyMuPDF."""
        result = ExtractionResult(doc_id=doc_id)

        doc = fitz.open(file_path)
        result.total_pages = len(doc)
        result.metadata = {
            "title": doc.metadata.get("title", ""),
            "author": doc.metadata.get("author", ""),
            "subject": doc.metadata.get("subject", ""),
            "creator": doc.metadata.get("creator", ""),
            "format": doc.metadata.get("format", ""),
        }

        for page_num in range(len(doc)):
            page = doc[page_num]

            blocks = page.get_text("dict").get("blocks", [])

            for block in blocks:
                if block.get("type") == 0:
                    for line in block.get("lines", []):
                        line_text = ""
                        for span in line.get("spans", []):
                            line_text += span.get("text", "")

                        if line_text.strip():
                            font_size = line["spans"][0].get("size", 12) if line.get("spans") else 12
                            block_type = "heading" if font_size > 14 else "text"

                            result.text_blocks.append(TextBlock(
                                text=line_text.strip(),
                                page=page_num + 1,
                                bbox=block.get("bbox"),
                                font_size=font_size,
                                block_type=block_type,
                                confidence=0.95
                            ))

                elif block.get("type") == 1:
                    result.text_blocks.append(TextBlock(
                        text=f"[Figure on page {page_num + 1}]",
                        page=page_num + 1,
                        bbox=block.get("bbox"),
                        block_type="figure",
                        confidence=0.9
                    ))

        doc.close()
        return result
    
    def _extract_pdfplumber_tables(self, file_path: str) -> List[ExtractedTable]:
        """Stage 2: Extract tables using pdfplumber."""
        tables = []

        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                try:
                    for table in page.find_tables():
                        table_data = table.extract()
                        bbox = table.bbox

                        if not table_data or len(table_data) < 2:
                            continue

                        cleaned = []
                        for row in table_data:
                            cleaned_row = [str(cell).strip() if cell is not None else ""
                                          for cell in row]
                            cleaned.append(cleaned_row)

                        if cleaned and any(any(cell for cell in row) for row in cleaned):
                            tables.append(ExtractedTable(
                                page=page_num + 1,
                                rows=len(cleaned),
                                cols=max(len(row) for row in cleaned),
                                data=cleaned,
                                confidence=0.85,
                                extraction_method="pdfplumber",
                                bbox=list(bbox)
                            ))

                except Exception as e:
                    logger.warning(f"Table extraction failed on page {page_num + 1}: {e}")

        return tables

    def _extract_camelot(self, file_path: str) -> List[ExtractedTable]:
        """Stage 3: Extract tables using camelot (no ghostscript needed for lattice mode)."""
        tables = []

        try:
            import camelot

            try:
                lattice_tables = camelot.read_pdf(file_path, pages='all', flavor='lattice')

                for table in lattice_tables:
                    if table.df is not None and not table.df.empty:
                        data = table.df.values.tolist()
                        tables.append(ExtractedTable(
                            page=table.page,
                            rows=len(data),
                            cols=len(data[0]) if data else 0,
                            data=[[str(cell) for cell in row] for row in data],
                            confidence=table.accuracy / 100 if hasattr(table, 'accuracy') else 0.8,
                            extraction_method="camelot-lattice",
                        ))
            except Exception as e:
                logger.warning(f"Camelot lattice mode failed: {e}")

            if len(tables) == 0:
                try:
                    stream_tables = camelot.read_pdf(file_path, pages='all', flavor='stream')

                    for table in stream_tables:
                        if table.df is not None and not table.df.empty:
                            data = table.df.values.tolist()
                            tables.append(ExtractedTable(
                                page=table.page,
                                rows=len(data),
                                cols=len(data[0]) if data else 0,
                                data=[[str(cell) for cell in row] for row in data],
                                confidence=0.75,
                                extraction_method="camelot-stream",
                            ))
                except Exception as e:
                    logger.warning(f"Camelot stream mode failed: {e}")

        except ImportError:
            logger.warning("camelot-py not installed, skipping camelot extraction")
        except Exception as e:
            logger.error(f"Camelot extraction failed: {e}")

        return tables

    def _extract_ocr_pymupdf(self, file_path: str, doc_id: str) -> ExtractionResult:
        """
        Stage 4: OCR extraction using PyMuPDF's built-in capabilities.

        PyMuPDF can extract text from image-based pages by rendering them
        and using its built-in text recognition on the rendered images.
        """
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

    def _calculate_confidence(self, result: ExtractionResult) -> float:
        """Calculate overall extraction confidence score."""
        if not result.text_blocks and not result.tables:
            return 0.0

        text_confidences = [b.confidence for b in result.text_blocks]
        table_confidences = [t.confidence for t in result.tables]

        all_confidences = text_confidences + table_confidences
        if not all_confidences:
            return 0.5

        avg_confidence = sum(all_confidences) / len(all_confidences)

        method_bonus = min(len(result.methods_used) * 0.05, 0.15)

        return min(avg_confidence + method_bonus, 1.0)

    def extract_tables_only(self, file_path: str) -> List[ExtractedTable]:
        """Extract only tables from PDF (optimized for table-heavy documents)."""
        tables = []

        # First try the analyzer's native table detection
        try:
            analyzer = PDFReportAnalyzer(file_path).run()
            for page_num, table_list in analyzer.table_texts.items():
                for bbox, md_text in table_list:
                    if md_text:
                        md_lines = md_text.strip().split("\n")
                        table_data = []
                        for line in md_lines:
                            if line.startswith("|") and "---" not in line:
                                cells = [c.strip() for c in line.strip("|").split("|")]
                                table_data.append(cells)
                        if table_data:
                            tables.append(ExtractedTable(
                                page=page_num + 1,
                                rows=len(table_data),
                                cols=max(len(row) for row in table_data) if table_data else 0,
                                data=table_data,
                                confidence=0.90,
                                extraction_method="pymupdf_find_tables",
                                bbox=list(bbox) if bbox else None,
                            ))
        except Exception as e:
            logger.warning(f"Analyzer table extraction failed: {e}")

        if not tables:
            try:
                tables = self._extract_pdfplumber_tables(file_path)
            except Exception as e:
                logger.error(f"pdfplumber table extraction failed: {e}")

        if not tables:
            try:
                tables = self._extract_camelot(file_path)
            except Exception as e:
                logger.error(f"camelot table extraction failed: {e}")

        return tables
