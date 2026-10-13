from app.pdf.legacy_compat import (
    ExtractionResult,
    TextBlock,
    ExtractedTable,
    AdvancedChunk,
)
from app.pdf.config import DoclingPipelineConfig, RouterConfig
from app.pdf.router import DocumentProfiler, DocumentProfile
from app.pdf.fast_engine import FastPyMuPDFEngine
from app.pdf.docling_engine import DoclingNeuralEngine
from app.pdf.chunker import FlysisHybridChunker
from app.pdf.adapter import UnifiedFlysisAdapter
from app.pdf.service import HybridPDFExtractionService

PDFExtractionPipeline = HybridPDFExtractionService

__all__ = [
    "ExtractionResult",
    "TextBlock",
    "ExtractedTable",
    "AdvancedChunk",
    "DoclingPipelineConfig",
    "RouterConfig",
    "DocumentProfiler",
    "DocumentProfile",
    "FastPyMuPDFEngine",
    "DoclingNeuralEngine",
    "FlysisHybridChunker",
    "UnifiedFlysisAdapter",
    "HybridPDFExtractionService",
    "PDFExtractionPipeline",
]
