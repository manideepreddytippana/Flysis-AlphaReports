from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from enum import Enum


class DocumentStatus(str, Enum):
    UPLOADING = "uploading"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"


class TaskType(str, Enum):
    FULL_TEXT = "full_text"
    TABLES = "tables"
    FIGURES = "figures"
    SUMMARY = "summary"
    QA = "qa"


class TaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class UploadResponse(BaseModel):
    doc_id: str
    filename: str
    page_count: int
    status: DocumentStatus
    message: str = "Upload successful"


class DocumentMetadata(BaseModel):
    doc_id: str
    filename: str
    page_count: int
    file_size: int
    status: DocumentStatus
    extracted_text_length: Optional[int] = None
    table_count: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TextBlock(BaseModel):
    text: str
    page: int
    bbox: Optional[List[float]] = None
    font_size: Optional[float] = None
    block_type: str = "text"


class TableCell(BaseModel):
    row: int
    col: int
    text: str
    bbox: Optional[List[float]] = None


class ExtractedTable(BaseModel):
    page: int
    rows: int
    cols: int
    data: List[List[str]]
    confidence: float = 1.0
    extraction_method: str = "unknown"


class ExtractionResult(BaseModel):
    doc_id: str
    text_blocks: List[TextBlock] = []
    tables: List[ExtractedTable] = []
    total_pages: int = 0
    processing_time_ms: int = 0
    methods_used: List[str] = []
    confidence: float = 0.0


class SearchResult(BaseModel):
    chunk: str
    score: float
    page: Optional[int] = None
    context: Optional[str] = None
    metadata: Dict[str, Any] = {}


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequest(BaseModel):
    doc_id: str
    messages: List[ChatMessage]
    use_rag: bool = True
    stream: bool = False


class ChatResponse(BaseModel):
    response: str
    sources: List[Dict[str, Any]] = []
    tokens_used: int = 0
    latency_ms: int = 0


class SummaryRequest(BaseModel):
    doc_id: str
    style: Literal["brief", "detailed", "executive"] = "detailed"
    focus_area: Optional[str] = None


class SummaryResponse(BaseModel):
    summary: str
    sections: List[Dict[str, str]] = []
    key_metrics: List[Dict[str, Any]] = []


class AnalysisRequest(BaseModel):
    doc_id: str
    analysis_type: str
    parameters: Dict[str, Any] = {}


class ChunkConfig(BaseModel):
    chunk_size: int = 512
    overlap: int = 128


class IndexResponse(BaseModel):
    indexed_chunks: int
    collection_name: str
    message: str = "Indexing complete"


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
