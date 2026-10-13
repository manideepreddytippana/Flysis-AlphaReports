import time
import logging
from typing import List, Dict, Any, Tuple
import fitz

from app.pdf.legacy_compat import (
    ExtractionResult,
    TextBlock,
    ExtractedTable,
    AdvancedChunk,
)

logger = logging.getLogger(__name__)


class FastPyMuPDFEngine:

    def extract(self, file_path: str, doc_id: str, extract_tables: bool = False) -> ExtractionResult:
        start_time = time.time()
        doc = fitz.open(file_path)
        result = ExtractionResult(doc_id=doc_id)
        result.total_pages = len(doc)
        result.methods_used.append("fast_pymupdf_engine")

        result.metadata = {
            "title": doc.metadata.get("title", "") if doc.metadata else "",
            "author": doc.metadata.get("author", "") if doc.metadata else "",
            "subject": doc.metadata.get("subject", "") if doc.metadata else "",
            "creator": doc.metadata.get("creator", "") if doc.metadata else "",
            "producer": doc.metadata.get("producer", "") if doc.metadata else "",
            "engine": "fast_pymupdf",
        }

        try:
            toc = doc.get_toc()
            result.outline = [
                {"level": item[0], "title": item[1], "page": item[2]}
                for item in toc
            ]
        except Exception as e:
            logger.debug(f"Failed to read TOC: {e}")
            result.outline = []

        all_blocks: List[TextBlock] = []
        all_tables: List[ExtractedTable] = []
        markdown_parts: List[str] = []

        current_section = "Document Overview"
        current_heading_path: List[str] = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            page_one_based = page_num + 1

            if extract_tables:
                try:
                    tabs = page.find_tables()
                    if tabs and len(tabs.tables) > 0:
                        for tab in tabs:
                            df_data = tab.extract()
                            if df_data and len(df_data) > 0:
                                headers = [str(c) if c is not None else "" for c in df_data[0]]
                                rows = [
                                    [str(c) if c is not None else "" for c in row]
                                    for row in df_data[1:]
                                ]
                                all_data = [headers] + rows
                                md_lines = [
                                    "| " + " | ".join(headers) + " |",
                                    "| " + " | ".join(["---"] * len(headers)) + " |",
                                ]
                                for r in rows:
                                    md_lines.append("| " + " | ".join(r) + " |")
                                tab_md = "\n".join(md_lines)

                                all_tables.append(
                                    ExtractedTable(
                                        page=page_one_based,
                                        rows=len(all_data),
                                        cols=len(headers),
                                        data=all_data,
                                        confidence=0.90,
                                        extraction_method="pymupdf_find_tables",
                                        bbox=list(tab.bbox) if hasattr(tab, "bbox") else None,
                                        markdown=tab_md,
                                    )
                                )
                except Exception as e:
                    logger.debug(f"Fast table check skipped on page {page_one_based}: {e}")

            try:
                raw_blocks = page.get_text("blocks")
                for b in raw_blocks:
                    if len(b) >= 5:
                        b_text = b[4].strip()
                        if not b_text:
                            continue

                        is_heading = (
                            len(b_text) < 100
                            and not b_text.endswith((".", ",", ";"))
                            and "\n" not in b_text
                            and (b_text.isupper() or b_text.istitle())
                        )

                        block_type = "heading" if is_heading else "text"
                        if is_heading:
                            current_section = b_text
                            current_heading_path = [b_text]

                        all_blocks.append(
                            TextBlock(
                                text=b_text,
                                page=page_one_based,
                                bbox=[float(b[0]), float(b[1]), float(b[2]), float(b[3])],
                                block_type=block_type,
                                confidence=0.95,
                                heading_path=list(current_heading_path),
                                section=current_section,
                            )
                        )
                        markdown_parts.append(f"\n\n### {b_text}" if is_heading else f"\n{b_text}")
            except Exception as e:
                logger.warning(f"Fast text extraction error on page {page_one_based}: {e}")

        doc.close()

        result.text_blocks = all_blocks
        result.tables = all_tables
        result.markdown = "".join(markdown_parts).strip()
        result.confidence = 0.95 if all_blocks else 0.0
        result.processing_time_ms = int((time.time() - start_time) * 1000)

        result.chunks_advanced = self._build_fast_chunks(all_blocks)

        return result

    def _build_fast_chunks(self, blocks: List[TextBlock], max_tokens: int = 250) -> List[AdvancedChunk]:
        chunks: List[AdvancedChunk] = []
        cur_parts: List[str] = []
        cur_pages: set = set()
        cur_headings: List[str] = []
        cur_token_total = 0
        chunk_id = 1

        for b in blocks:
            estimated_tokens = len(b.text.split())

            if cur_parts and (cur_token_total + estimated_tokens > max_tokens or (b.block_type == "heading" and len(cur_parts) > 2)):
                chunk_text = "\n\n".join(cur_parts).strip()
                if chunk_text:
                    chunks.append(
                        AdvancedChunk(
                            chunk_id=chunk_id,
                            text=chunk_text,
                            page_start=min(cur_pages) if cur_pages else 1,
                            page_end=max(cur_pages) if cur_pages else 1,
                            heading_path=list(cur_headings),
                            chunk_type="text",
                            token_estimate=cur_token_total,
                            boundary_reason="size_or_heading",
                        )
                    )
                    chunk_id += 1
                cur_parts = []
                cur_pages = set()
                cur_token_total = 0

            cur_parts.append(b.text)
            cur_token_total += estimated_tokens
            cur_pages.add(b.page)
            if b.heading_path:
                cur_headings = b.heading_path

        if cur_parts:
            chunk_text = "\n\n".join(cur_parts).strip()
            if chunk_text:
                chunks.append(
                    AdvancedChunk(
                        chunk_id=chunk_id,
                        text=chunk_text,
                        page_start=min(cur_pages) if cur_pages else 1,
                        page_end=max(cur_pages) if cur_pages else 1,
                        heading_path=list(cur_headings),
                        chunk_type="text",
                        token_estimate=len(chunk_text.split()),
                        boundary_reason="final",
                    )
                )

        return chunks
