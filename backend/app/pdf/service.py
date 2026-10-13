import os
import json
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from app.pdf.legacy_compat import ExtractionResult
from app.pdf.config import DoclingPipelineConfig, RouterConfig
from app.pdf.router import DocumentProfiler, DocumentProfile
from app.pdf.fast_engine import FastPyMuPDFEngine
from app.pdf.docling_engine import DoclingNeuralEngine
from app.pdf.chunker import FlysisHybridChunker
from app.pdf.adapter import UnifiedFlysisAdapter
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class HybridPDFExtractionService:

    def __init__(
        self,
        docling_config: Optional[DoclingPipelineConfig] = None,
        router_config: Optional[RouterConfig] = None,
    ):
        self.docling_config = docling_config or DoclingPipelineConfig.from_settings()
        self.router_config = router_config or RouterConfig()
        self.settings = get_settings()

        self.profiler = DocumentProfiler(self.router_config)
        self.fast_engine = FastPyMuPDFEngine()
        self.docling_engine = DoclingNeuralEngine(self.docling_config)
        self.chunker = FlysisHybridChunker(max_tokens=self.docling_config.max_tokens)
        self.adapter = UnifiedFlysisAdapter(self.chunker)

        self.artifacts_dir = Path(getattr(self.settings, "pdf_information_dir", "./pdf-information"))
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def pre_warm(self) -> None:
        logger.info("Pre-warming HybridPDFExtractionService neural models...")
        self.docling_engine.pre_warm()
        self.chunker.pre_warm()
        logger.info("HybridPDFExtractionService pre-warming completed.")

    def extract(

        self,
        file_path: str,
        doc_id: str,
        force_route: Optional[str] = None,
    ) -> ExtractionResult:
        start_time = time.time()
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF document not found: {file_path}")

        profile: Optional[DocumentProfile] = None
        route = force_route

        if not route:
            try:
                profile = self.profiler.profile(file_path)
                route = profile.recommended_route
            except Exception as e:
                logger.warning(f"[{doc_id}] Profiler failed ({e}); defaulting to docling")
                route = "docling"

        result: Optional[ExtractionResult] = None

        if route == "fast":
            logger.info(f"[{doc_id}] Executing Fast Track (PyMuPDF)...")
            extract_tabs = profile.has_tables if profile else False
            result = self.fast_engine.extract(file_path, doc_id, extract_tables=extract_tabs)
            result.methods_used.append("route_fast_track")

        else:
            logger.info(f"[{doc_id}] Executing Deep Neural Track (Docling + TableFormer)...")
            try:
                conv_result = self.docling_engine.extract(file_path)
                elapsed_ms = int((time.time() - start_time) * 1000)
                result = self.adapter.docling_to_extraction_result(
                    doc=conv_result.document,
                    doc_id=doc_id,
                    processing_time_ms=elapsed_ms,
                )
                result.methods_used.append("route_deep_track_docling")
            except Exception as exc:
                logger.error(
                    f"[{doc_id}] Docling conversion encountered error: {exc}. "
                    f"Activating Fail-Safe Circuit Breaker fallback to FastPyMuPDFEngine!",
                    exc_info=True,
                )
                result = self.fast_engine.extract(file_path, doc_id)
                result.methods_used.append("circuit_breaker_fallback_fast")

        result.processing_time_ms = int((time.time() - start_time) * 1000)

        try:
            canonical_data = self.adapter.to_canonical_dict(result, include_metadata=True)
            if profile:
                canonical_data["profile"] = {
                    "is_scanned": profile.is_scanned,
                    "has_tables": profile.has_tables,
                    "avg_chars": profile.avg_chars_per_page,
                    "route": route,
                    "reason": profile.routing_reason,
                }
            cache_file = self.artifacts_dir / f"{doc_id}_data.json"
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(canonical_data, f, indent=2, ensure_ascii=False)
            logger.info(f"[{doc_id}] Saved canonical extraction artifact to {cache_file}")
        except Exception as cache_err:
            logger.error(f"[{doc_id}] Failed to save extraction JSON artifact: {cache_err}")

        return result

    def extract_tables_only(self, file_path: str, doc_id: Optional[str] = None):
        temp_id = doc_id or Path(file_path).stem
        info_file = self.artifacts_dir / f"{temp_id}_data.json"
        if info_file.exists():
            try:
                with open(info_file, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
                from app.pdf.legacy_compat import ExtractedTable
                tables = []
                for t in cached_data.get("tables", []):
                    tables.append(
                        ExtractedTable(
                            page=t.get("page", 0),
                            rows=t.get("rows", 0),
                            cols=t.get("cols", 0),
                            data=t.get("data", []),
                            confidence=t.get("confidence", 1.0),
                            extraction_method=t.get("method", "cached"),
                        )
                    )
                return tables
            except Exception as e:
                logger.warning(f"Failed loading cached tables for {temp_id}: {e}")

        result = self.extract(file_path, doc_id=temp_id)
        return result.tables

