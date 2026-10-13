from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

@dataclass
class ExtractedTable:
    page: int
    rows: int
    cols: int
    data: List[List[str]]
    confidence: float = 1.0
    extraction_method: str = "docling_tableformer"
    bbox: Optional[List[float]] = None
    markdown: str = ""

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
    markdown: str = ""
