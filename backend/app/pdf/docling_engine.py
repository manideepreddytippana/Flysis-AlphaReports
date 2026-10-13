import logging
import time
from typing import Optional
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    TableStructureOptions,
    TableFormerMode,
    RapidOcrOptions,
)
from docling.datamodel.document import ConversionResult

from app.pdf.config import DoclingPipelineConfig

logger = logging.getLogger(__name__)


class DoclingNeuralEngine:

    def __init__(self, config: Optional[DoclingPipelineConfig] = None):
        self.config = config or DoclingPipelineConfig.from_settings()
        self._converter: Optional[DocumentConverter] = None

    def _get_converter(self) -> DocumentConverter:
        if self._converter is None:
            logger.info("Initializing Docling DocumentConverter with neural pipeline options...")
            pipeline_options = PdfPipelineOptions(
                do_table_structure=True,
                do_ocr=self.config.ocr_enabled,
                generate_picture_images=self.config.generate_picture_images,
            )
            # TableFormer Configuration
            pipeline_options.table_structure_options.mode = self.config.table_mode
            pipeline_options.table_structure_options.do_cell_matching = self.config.do_cell_matching

            # OCR Configuration (RapidOCR)
            if self.config.ocr_enabled and self.config.ocr_engine == "rapidocr":
                try:
                    pipeline_options.ocr_options = RapidOcrOptions(lang=["latin"])
                except Exception as e:
                    logger.warning(f"Could not initialize RapidOcrOptions with lang=['latin'], using default: {e}")
                    pipeline_options.ocr_options = RapidOcrOptions()

            format_options = {
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
            self._converter = DocumentConverter(format_options=format_options)
            logger.info("Docling DocumentConverter initialized successfully.")
        return self._converter

    def pre_warm(self) -> None:
        try:
            logger.info("Pre-warming Docling DocumentConverter neural models...")
            _ = self._get_converter()
            logger.info("Docling DocumentConverter pre-warmed successfully.")
        except Exception as e:
            logger.warning(f"Docling pre-warming encountered an issue (will load on demand): {e}")

    def extract(self, file_path: str) -> ConversionResult:
        start = time.time()
        converter = self._get_converter()
        logger.info(f"[DoclingNeuralEngine] Starting conversion of {file_path}...")
        conv_res = converter.convert(file_path)
        elapsed = time.time() - start
        logger.info(
            f"[DoclingNeuralEngine] Conversion completed in {elapsed:.2f}s for {file_path}"
        )
        return conv_res

