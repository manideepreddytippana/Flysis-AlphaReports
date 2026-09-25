import json
import logging
import asyncio
from pathlib import Path

from celery import Celery

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.api.utils import _get_document_by_id, _build_extraction_dict
from app.api.deps import pdf_pipeline, vector_store, llm_client, extraction_cache

settings = get_settings()
logger = logging.getLogger(__name__)

celery_app = Celery(
    "flysis_tasks",
    broker=settings.redis_url,
    backend=settings.redis_url.replace("/0", "/1")
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

async def async_process_document(doc_id: int, python_doc_id: str, file_path: str):
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

@celery_app.task(name="process_document_task")
def process_document_task(doc_id: int, python_doc_id: str, file_path: str):
    """
    Celery task wrapper to run the async document processing logic.
    """
    asyncio.run(async_process_document(doc_id, python_doc_id, file_path))
