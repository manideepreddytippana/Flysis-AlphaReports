import json
import logging
import asyncio
from pathlib import Path

from celery import Celery
from celery.signals import worker_process_init

from app.core.config import get_settings
from app.core.database import WorkerAsyncSessionLocal as AsyncSessionLocal
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

@worker_process_init.connect
def init_worker(**kwargs):
    logger.info("Pre-warming ML models into Celery RAM...")
    from app.vector.pgvector_store import get_embedding_model
    get_embedding_model()
    try:
        pdf_pipeline.pre_warm()
    except Exception as exc:
        logger.warning(f"Celery pre-warming pdf_pipeline encountered issue: {exc}")

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
            extraction_dict = _build_extraction_dict(result, include_metadata=True)
            extraction_cache[python_doc_id] = extraction_dict
            
            if not doc.page_count and getattr(result, "total_pages", None):
                doc.page_count = result.total_pages
            
            info_dir = Path(getattr(settings, "pdf_information_dir", "./pdf-information"))
            info_dir.mkdir(parents=True, exist_ok=True)
            info_file = info_dir / f"{python_doc_id}_data.json"
            if not info_file.exists():
                try:
                    with open(info_file, "w", encoding="utf-8") as f:
                        json.dump(extraction_dict, f, indent=2, ensure_ascii=False)
                    logger.info(f"Saved exact extraction data to {info_file}")
                except Exception as e:
                    logger.error(f"Failed to save extraction data JSON: {e}")
            
            logger.info(f"Starting vector indexing for {python_doc_id}")
            advanced_chunks = extraction_dict.get("chunks_advanced", [])
            valid_types = {"text", "table", "figure", "heading"}
            if advanced_chunks:
                chunks = [
                    {
                        "text": c["text"],
                        "page": c.get("page_start", 1),
                        "type": c.get("chunk_type", "text") if c.get("chunk_type") in valid_types else "text",
                        "section": " > ".join(c.get("heading_path", [])) if c.get("heading_path") else "",
                    }
                    for c in advanced_chunks
                ]
                already_chunked = True
            else:
                chunks = [
                    {
                        "text": b["text"],
                        "page": b["page"],
                        "type": b.get("type", "text") if b.get("type") in valid_types else "text",
                        "section": b.get("section", ""),
                    }
                    for b in extraction_dict.get("text_blocks", [])
                ]
                already_chunked = False
            
            await vector_store.index_document(
                db=db,
                doc_id=doc.id,
                chunks=chunks,
                chunk_size=512,
                overlap=128,
                already_chunked=already_chunked,
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
            logger.error(f"Background processing failed for doc {python_doc_id}: {e}")
            try:
                await db.rollback()
                err_doc = await _get_document_by_id(db, doc_id)
                if err_doc:
                    err_doc.status = "error"
                    err_doc.error_message = str(e)
                    await db.commit()
            except Exception as rollback_err:
                logger.error(f"Failed to record error state for doc {python_doc_id}: {rollback_err}")


@celery_app.task(name="process_document_task")
def process_document_task(doc_id: int, python_doc_id: str, file_path: str):
    asyncio.run(async_process_document(doc_id, python_doc_id, file_path))
