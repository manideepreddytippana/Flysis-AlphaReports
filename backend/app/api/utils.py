import json
import logging
import asyncio
from typing import Dict, Any
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import Document
from app.api.deps import pdf_pipeline, vector_store, llm_client, extraction_cache

settings = get_settings()
logger = logging.getLogger(__name__)

def _build_extraction_dict(result, include_metadata: bool = False) -> Dict[str, Any]:
    data: Dict[str, Any] = {
        "text_blocks": [
            {
                "text": b.text,
                "page": b.page,
                "type": b.block_type,
                "section": b.section,
                "heading_path": b.heading_path or [],
                **({"confidence": b.confidence} if include_metadata else {}),
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
                **({"confidence": t.confidence} if include_metadata else {}),
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
        "analyzer_report": result.analyzer_report,
    }

    if include_metadata:
        data["total_pages"] = result.total_pages
        data["processing_time_ms"] = result.processing_time_ms
        data["methods_used"] = result.methods_used
        data["confidence"] = result.confidence

    return data


async def _ensure_extraction_cached(python_doc_id: str, doc) -> None:
    if python_doc_id in extraction_cache:
        return
    file_path = Path(settings.uploads_dir) / doc.filename
    result = await asyncio.to_thread(pdf_pipeline.extract, str(file_path), python_doc_id)
    extraction_cache[python_doc_id] = _build_extraction_dict(result)


async def _get_document_by_id(db: AsyncSession, doc_id: int) -> Document | None:
    result = await db.execute(select(Document).where(Document.id == doc_id))
    return result.scalar_one_or_none()


async def _get_document_by_python_doc_id(db: AsyncSession, python_doc_id: str) -> Document | None:
    result = await db.execute(select(Document).where(Document.python_doc_id == python_doc_id))
    return result.scalar_one_or_none()


def get_upload_path() -> Path:
    path = Path(settings.uploads_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path
