import uuid
import json
import logging
import asyncio
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db, AsyncSessionLocal
from app.core.models import UploadResponse, DocumentStatus
from app.db.models import Document

from app.api.deps import pdf_pipeline, vector_store, llm_client, extraction_cache
from app.api.utils import _get_document_by_id, get_upload_path, _build_extraction_dict

router = APIRouter(tags=["upload"])
logger = logging.getLogger(__name__)
settings = get_settings()



@router.post("/documents/upload", response_model=UploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    contents = await file.read()
    max_size = settings.max_file_size_mb * 1024 * 1024
    if len(contents) > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size: {settings.max_file_size_mb}MB"
        )
    
    doc_uuid = str(uuid.uuid4())
    upload_dir = get_upload_path()
    file_path = upload_dir / f"{doc_uuid}.pdf"
    
    with open(file_path, "wb") as f:
        f.write(contents)
    
    def _read_page_count(path_str: str) -> int:
        try:
            import fitz
            pdf_doc = fitz.open(path_str)
            count = len(pdf_doc)
            pdf_doc.close()
            return count
        except Exception:
            return 0

    page_count = await asyncio.to_thread(_read_page_count, str(file_path))
    
    db_doc = Document(
        filename=doc_uuid + ".pdf",
        original_name=file.filename,
        file_size=len(contents),
        file_type="application/pdf",
        page_count=page_count,
        python_doc_id=doc_uuid,
        status="processing",
    )
    db.add(db_doc)
    await db.commit()
    await db.refresh(db_doc)
    
    from app.worker import process_document_task
    process_document_task.delay(db_doc.id, doc_uuid, str(file_path))
    
    logger.info(f"Document uploaded and queued: {doc_uuid} - {file.filename}")
    
    return UploadResponse(
        doc_id=doc_uuid,
        filename=file.filename,
        page_count=page_count,
        status=DocumentStatus.PROCESSING
    )
