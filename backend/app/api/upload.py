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

async def process_document_bg(doc_id: int, python_doc_id: str, file_path: str):
    async with AsyncSessionLocal() as db:
        doc = await _get_document_by_id(db, doc_id)
        if not doc:
            return
            
        doc.status = "processing"
        await db.commit()
        
        try:
            logger.info(f"Starting extraction for {python_doc_id}")
            result = await asyncio.to_thread(pdf_pipeline.extract, file_path, python_doc_id)
            extraction_cache[python_doc_id] = _build_extraction_dict(result)
            
            try:
                info_dir = Path("pdf-information")
                info_dir.mkdir(exist_ok=True)
                info_file = info_dir / f"{python_doc_id}_data.json"
                with open(info_file, "w", encoding="utf-8") as f:
                    json.dump(extraction_cache[python_doc_id], f, indent=2, ensure_ascii=False)
                logger.info(f"Saved exact extraction data to {info_file}")
            except Exception as e:
                logger.error(f"Failed to save extraction data JSON: {e}")
            
            logger.info(f"Starting vector indexing for {python_doc_id}")
            chunks = [
                {
                    "text": b["text"],
                    "page": b["page"],
                    "type": b.get("type", "text"),
                    "section": b.get("section", "")
                }
                for b in extraction_cache[python_doc_id]["text_blocks"]
            ]
            
            await vector_store.index_document(
                db=db,
                doc_id=doc.id,
                chunks=chunks,
                chunk_size=512,
                overlap=128
            )
            
            logger.info(f"Generating summary for {python_doc_id}")
            full_text = "\n".join(b["text"] for b in chunks)
            if len(full_text.strip()) > 50:
                try:
                    summary_result = await llm_client.summarize(full_text, style="executive")
                    if summary_result and summary_result.get("summary"):
                        doc.extracted_summary = json.dumps(summary_result, ensure_ascii=False)
                except Exception as sum_e:
                    logger.warning(f"Summary generation failed: {sum_e}")
            
            doc.status = "ready"
            await db.commit()
            logger.info(f"Background processing completed for doc {python_doc_id}")
            
        except Exception as e:
            doc.status = "error"
            doc.error_message = str(e)
            await db.commit()
            logger.error(f"Background processing failed for doc {python_doc_id}: {e}")

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
    
    background_tasks.add_task(process_document_bg, db_doc.id, doc_uuid, str(file_path))
    
    logger.info(f"Document uploaded and queued: {doc_uuid} - {file.filename}")
    
    return UploadResponse(
        doc_id=doc_uuid,
        filename=file.filename,
        page_count=page_count,
        status=DocumentStatus.PROCESSING
    )
