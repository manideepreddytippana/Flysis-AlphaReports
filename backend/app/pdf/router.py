import logging
from typing import Optional
from dataclasses import dataclass
import fitz

from app.pdf.config import RouterConfig

logger = logging.getLogger(__name__)

@dataclass
class DocumentProfile:
    total_pages: int
    is_scanned: bool
    avg_chars_per_page: float
    has_tables: bool
    table_count_estimate: int
    is_multi_column: bool
    recommended_route: str  # "fast" or "docling"
    routing_reason: str


class DocumentProfiler:

    def __init__(self, config: Optional[RouterConfig] = None):
        self.config = config or RouterConfig()

    def profile(self, file_path: str) -> DocumentProfile:
        doc = fitz.open(file_path)
        try:
            total_pages = len(doc)
            sample_count = min(total_pages, self.config.sample_pages_limit)
            if sample_count == 0:
                return DocumentProfile(
                    total_pages=0,
                    is_scanned=True,
                    avg_chars_per_page=0.0,
                    has_tables=False,
                    table_count_estimate=0,
                    is_multi_column=False,
                    recommended_route="docling",
                    routing_reason="Empty document or zero pages",
                )

            total_chars = 0
            table_count = 0
            multi_column_votes = 0

            for page_idx in range(sample_count):
                page = doc[page_idx]
                text = page.get_text("text") or ""
                total_chars += len(text.strip())

                try:
                    tabs = page.find_tables()
                    if tabs and len(tabs.tables) > 0:
                        table_count += len(tabs.tables)
                except Exception:
                    drawings = page.get_drawings()
                    if len(drawings) > 25:
                        table_count += 1
                blocks = page.get_text("blocks") or []
                text_blocks = [b for b in blocks if len(b) >= 5 and b[4].strip()]
                if len(text_blocks) >= 2:
                    page_width = page.rect.width
                    mid_x = page_width / 2.0
                    left_blocks = [b for b in text_blocks if b[2] < mid_x + 30]
                    right_blocks = [b for b in text_blocks if b[0] > mid_x - 30]
                    if len(left_blocks) >= 2 and len(right_blocks) >= 2:
                        multi_column_votes += 1

            avg_chars = total_chars / float(sample_count)
            is_scanned = avg_chars < self.config.scanned_min_chars_per_page
            has_tables = table_count >= self.config.table_detection_threshold
            is_multi_column = multi_column_votes >= max(1, sample_count // 3)

            if is_scanned:
                route = "docling"
                reason = f"Scanned/low-text document (avg {avg_chars:.1f} chars/page); requires RapidOCR"
            elif has_tables:
                route = "docling"
                reason = f"Tabular data detected (~{table_count} tables); requires TableFormer precision"
            elif is_multi_column:
                route = "docling"
                reason = "Multi-column layout detected; requires DocLayNet reading-order reconstruction"
            else:
                route = "fast"
                reason = "Clean single-column digital text without complex tables; eligible for Fast Track"

            logger.info(
                f"[DocumentProfiler] {file_path} -> Route: {route.upper()} (Pages: {total_pages}, AvgChars: {avg_chars:.1f}, Tables: {table_count}, MultiCol: {is_multi_column}) - {reason}"
            )

            return DocumentProfile(
                total_pages=total_pages,
                is_scanned=is_scanned,
                avg_chars_per_page=avg_chars,
                has_tables=has_tables,
                table_count_estimate=table_count,
                is_multi_column=is_multi_column,
                recommended_route=route,
                routing_reason=reason,
            )
        finally:
            doc.close()


class ExtractionRouter:
    """
    Decides routing between Fast Track and Docling Neural Track.
    """

    def __init__(self, profiler: Optional[DocumentProfiler] = None):
        self.profiler = profiler or DocumentProfiler()

    def route(
        self,
        file_path: str,
        force_route: Optional[str] = None,
    ) -> tuple[str, Optional[DocumentProfile]]:
        if force_route in ("fast", "docling"):
            return force_route, None
        profile = self.profiler.profile(file_path)
        return profile.recommended_route, profile

