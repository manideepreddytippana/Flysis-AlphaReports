import os
from typing import Optional
from pydantic import BaseModel, Field
from docling.datamodel.pipeline_options import TableFormerMode
from app.core.config import get_settings

class RouterConfig(BaseModel):
    scanned_min_chars_per_page: float = 40.0
    table_detection_threshold: int = 1
    sample_pages_limit: int = 10
    multi_column_overlap_threshold: float = 0.35


class DoclingPipelineConfig(BaseModel):
    table_mode: TableFormerMode = TableFormerMode.ACCURATE
    do_cell_matching: bool = True
    ocr_engine: str = "rapidocr"
    ocr_enabled: bool = True
    max_tokens: int = 250
    generate_picture_images: bool = False
    artifacts_dir: str = "./pdf-information"

    @classmethod
    def from_settings(cls) -> "DoclingPipelineConfig":
        settings = get_settings()
        mode_str = getattr(settings, "docling_table_mode", "accurate").lower()
        table_mode = (
            TableFormerMode.FAST if mode_str == "fast" else TableFormerMode.ACCURATE
        )
        return cls(
            table_mode=table_mode,
            ocr_engine=getattr(settings, "docling_ocr_engine", "rapidocr"),
            ocr_enabled=getattr(settings, "docling_ocr_enabled", True),
            max_tokens=getattr(settings, "docling_max_tokens", 250),
            artifacts_dir=getattr(settings, "pdf_information_dir", "./pdf-information"),
        )
