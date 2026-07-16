
import os
import uuid
import logging
import time
from typing import List, Optional
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db, AsyncSessionLocal
from app.core.models import (
    UploadResponse, DocumentStatus, ExtractionResult as ExtractionResultModel,
    ChatRequest, ChatResponse, SummaryRequest, SummaryResponse,
    AnalysisRequest, ChunkConfig, IndexResponse, ErrorResponse
)
from app.db.models import Document, DocumentChunk, User
from app.api.auth import get_current_user
from app.pdf.extractor import PDFExtractionPipeline
from app.vector.pgvector_store import PgVectorStore
from app.llm.sarvam_client import SarvamAIClient, RAGPipeline

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()

pdf_pipeline = PDFExtractionPipeline(enable_ocr=settings.ocr_enabled)
vector_store = PgVectorStore()
llm_client = SarvamAIClient()
rag_pipeline = RAGPipeline(vector_store, llm_client)

extraction_cache: dict = {}


async def _get_document_by_id(db: AsyncSession, doc_id: int) -> Document | None:
    result = await db.execute(select(Document).where(Document.id == doc_id))
    return result.scalar_one_or_none()


async def _get_document_by_python_doc_id(
    db: AsyncSession,
    python_doc_id: str,
) -> Document | None:
    result = await db.execute(
        select(Document).where(Document.python_doc_id == python_doc_id)
    )
    return result.scalar_one_or_none()


async def process_document_bg(doc_id: int, python_doc_id: str, file_path: str):

    async with AsyncSessionLocal() as db:
        doc = await _get_document_by_id(db, doc_id)
        if not doc:
            return
            
        doc.status = "processing"
        await db.commit()
        
        try:
            logger.info(f"Starting extraction for {python_doc_id}")
            result = pdf_pipeline.extract(file_path, python_doc_id)
            extraction_cache[python_doc_id] = {
                "text_blocks": [
                    {
                        "text": b.text,
                        "page": b.page,
                        "type": b.block_type,
                        "section": b.section,
                        "heading_path": b.heading_path or [],
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
            
            try:
                import json as _json
                info_dir = Path("pdf-information")
                info_dir.mkdir(exist_ok=True)
                info_file = info_dir / f"{python_doc_id}_data.json"
                with open(info_file, "w", encoding="utf-8") as f:
                    _json.dump(extraction_cache[python_doc_id], f, indent=2, ensure_ascii=False)
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
                        import json as _json
                        doc.extracted_summary = _json.dumps(summary_result, ensure_ascii=False)
                except Exception as sum_e:
                    logger.warning(f"Summary generation failed: {sum_e}")
            
            # 4. Update Status
            doc.status = "ready"
            await db.commit()
            logger.info(f"Background processing completed for doc {python_doc_id}")
            
        except Exception as e:
            doc.status = "error"
            doc.error_message = str(e)
            await db.commit()
            logger.error(f"Background processing failed for doc {python_doc_id}: {e}")


def get_upload_path() -> Path:
    path = Path(settings.uploads_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "version": "1.0.0",
        "services": {
            "pdf_extraction": "ready",
            "pgvector": "ready",
            "sarvam_llm": "ready" if settings.sarvam_api_key else "no_api_key"
        }
    }

@router.get("/documents")
async def list_documents(
    page: int = 1,
    limit: int = 20,
    status: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Document).where(Document.user_id == user.id)
    if status:
        query = query.where(Document.status == status)

    count_query = select(Document.id).where(Document.user_id == user.id)
    if status:
        count_query = count_query.where(Document.status == status)

    total = len((await db.execute(count_query)).scalars().all())
    items = (
        await db.execute(
            query.order_by(Document.uploaded_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
    ).scalars().all()
    
    return {
        "items": [
            {
                "id": doc.id,
                "filename": doc.filename,
                "original_name": doc.original_name,
                "file_size": doc.file_size,
                "file_type": doc.file_type,
                "page_count": doc.page_count,
                "python_doc_id": doc.python_doc_id,
                "status": doc.status,
                "extracted_summary": doc.extracted_summary,
                "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
            }
            for doc in items
        ],
        "total": total,
        "page": page,
        "limit": limit,
    }


@router.get("/documents/{doc_id}")
async def get_document(
    doc_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get document metadata."""
    result = await db.execute(
        select(Document).where(
            Document.id == doc_id,
            Document.user_id == user.id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {
        "id": doc.id,
        "filename": doc.filename,
        "original_name": doc.original_name,
        "page_count": doc.page_count,
        "file_size": doc.file_size,
        "status": doc.status,
        "python_doc_id": doc.python_doc_id,
        "extracted_summary": doc.extracted_summary,
        "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
    }


@router.get("/documents/{python_doc_id}/download")
async def download_document(
    python_doc_id: str,
    db: AsyncSession = Depends(get_db)
):
    doc = await _get_document_by_python_doc_id(db, python_doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    file_path = Path(settings.uploads_dir) / doc.filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
        
    return FileResponse(
        path=file_path, 
        media_type='application/pdf', 
        filename=doc.original_name,
        content_disposition_type="inline"
    )


@router.get("/documents/stats/overview")
async def get_document_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    docs = (await db.execute(select(Document).where(Document.user_id == user.id))).scalars().all()
    return {
        "total": len(docs),
        "ready": sum(1 for d in docs if d.status == "ready"),
        "processing": sum(1 for d in docs if d.status == "processing"),
        "error": sum(1 for d in docs if d.status == "error"),
        "totalPages": sum(d.page_count or 0 for d in docs),
    }


@router.post("/documents/upload", response_model=UploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
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
    
    try:
        import fitz
        pdf_doc = fitz.open(str(file_path))
        page_count = len(pdf_doc)
        pdf_doc.close()
    except Exception:
        page_count = 0
    
    db_doc = Document(
        user_id=user.id,
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


@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    result = await db.execute(
        select(Document).where(
            Document.id == doc_id,
            Document.user_id == user.id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    try:
        file_path = Path(settings.uploads_dir) / doc.filename
        if file_path.exists():
            os.remove(str(file_path))
    except Exception as e:
        logger.warning(f"Failed to delete file: {e}")
    
    await vector_store.delete_document_chunks(db, doc.id)
    
    if doc.python_doc_id:
        extraction_cache.pop(doc.python_doc_id, None)
    
    await db.delete(doc)
    await db.commit()
    
    return {"message": "Document deleted successfully"}




@router.post("/documents/{python_doc_id}/extract/full")
async def extract_full(python_doc_id: str, db: AsyncSession = Depends(get_db)):

    doc = await _get_document_by_python_doc_id(db, python_doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    file_path = Path(settings.uploads_dir) / doc.filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found on disk")
    
    doc.status = "processing"
    await db.commit()
    
    try:
        result = pdf_pipeline.extract(str(file_path), python_doc_id)
        
        extraction_result = {
            "text_blocks": [
                {
                    "text": b.text,
                    "page": b.page,
                    "type": b.block_type,
                    "confidence": b.confidence,
                    "section": b.section,
                    "heading_path": b.heading_path or [],
                }
                for b in result.text_blocks
            ],
            "tables": [
                {
                    "page": t.page,
                    "rows": t.rows,
                    "cols": t.cols,
                    "data": t.data,
                    "confidence": t.confidence,
                    "method": t.extraction_method
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
            "total_pages": result.total_pages,
            "processing_time_ms": result.processing_time_ms,
            "methods_used": result.methods_used,
            "confidence": result.confidence,
        }
        
        extraction_cache[python_doc_id] = extraction_result
        doc.status = "ready"
        await db.commit()
        
        return extraction_result
    
    except Exception as e:
        doc.status = "error"
        doc.error_message = str(e)
        await db.commit()
        logger.error(f"Extraction failed for {python_doc_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


@router.post("/documents/{python_doc_id}/extract/tables")
async def extract_tables(python_doc_id: str, db: AsyncSession = Depends(get_db)):

    doc = await _get_document_by_python_doc_id(db, python_doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    file_path = Path(settings.uploads_dir) / doc.filename
    try:
        tables = pdf_pipeline.extract_tables_only(str(file_path))
        return {
            "tables": [
                {
                    "page": t.page,
                    "rows": t.rows,
                    "cols": t.cols,
                    "data": t.data,
                    "confidence": t.confidence,
                    "method": t.extraction_method
                }
                for t in tables
            ],
            "total_tables": len(tables)
        }
    except Exception as e:
        logger.error(f"Table extraction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Table extraction failed: {str(e)}")


@router.get("/documents/{python_doc_id}/text")
async def get_text(python_doc_id: str, page: Optional[int] = None, db: AsyncSession = Depends(get_db)):

    doc = await _get_document_by_python_doc_id(db, python_doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Extract if not cached
    if python_doc_id not in extraction_cache:
        file_path = Path(settings.uploads_dir) / doc.filename
        result = pdf_pipeline.extract(str(file_path), python_doc_id)
        extraction_cache[python_doc_id] = {
            "text_blocks": [
                {
                    "text": b.text,
                    "page": b.page,
                    "type": b.block_type,
                    "section": b.section,
                    "heading_path": b.heading_path or [],
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
    
    blocks = extraction_cache[python_doc_id]["text_blocks"]
    if page is not None:
        blocks = [b for b in blocks if b["page"] == page]
    
    pages_dict = {}
    for block in blocks:
        p = block["page"]
        if p not in pages_dict:
            pages_dict[p] = []
        pages_dict[p].append(block)
    
    tables = extraction_cache[python_doc_id].get("tables", [])
    if page is not None:
        tables = [t for t in tables if t["page"] == page]
    
    return {
        "pages": [
            {"page_num": p, "blocks": page_blocks}
            for p, page_blocks in sorted(pages_dict.items())
        ],
        "tables": tables,
        "outline": extraction_cache[python_doc_id].get("outline", []),
        "total_blocks": len(blocks)
    }


@router.get("/documents/{python_doc_id}/data.json")
async def get_document_data_json(python_doc_id: str, db: AsyncSession = Depends(get_db)):
    """Return the exact raw extracted data JSON (chunks, tables, outline, etc)"""
    doc = await _get_document_by_python_doc_id(db, python_doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    info_file = Path("pdf-information") / f"{python_doc_id}_data.json"
    if info_file.exists():
        try:
            import json as _json
            with open(info_file, "r", encoding="utf-8") as f:
                return _json.load(f)
        except Exception as e:
            logger.error(f"Failed to read data JSON file: {e}")
            pass
            
    if python_doc_id in extraction_cache:
        return extraction_cache[python_doc_id]
        
    raise HTTPException(status_code=404, detail="Data JSON not found or document not yet processed")


@router.post("/documents/{python_doc_id}/index")
async def index_document(python_doc_id: str, config: ChunkConfig, db: AsyncSession = Depends(get_db)):
    """Index document chunks into PostgreSQL+pgvector for semantic search."""
    doc = await _get_document_by_python_doc_id(db, python_doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if python_doc_id not in extraction_cache:
        file_path = Path(settings.uploads_dir) / doc.filename
        result = pdf_pipeline.extract(str(file_path), python_doc_id)
        extraction_cache[python_doc_id] = {
            "text_blocks": [
                {
                    "text": b.text,
                    "page": b.page,
                    "type": b.block_type,
                    "section": b.section,
                    "heading_path": b.heading_path or [],
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
    
    chunks = [
        {
            "text": b["text"],
            "page": b["page"],
            "type": b.get("type", "text"),
            "section": b.get("section", "")
        }
        for b in extraction_cache[python_doc_id]["text_blocks"]
    ]
    
    result = await vector_store.index_document(
        db=db,
        doc_id=doc.id,
        chunks=chunks,
        chunk_size=config.chunk_size,
        overlap=config.overlap
    )
    
    return IndexResponse(**result)


@router.post("/documents/{python_doc_id}/search")
async def search_document(python_doc_id: str, query: dict, db: AsyncSession = Depends(get_db)):

    doc = await _get_document_by_python_doc_id(db, python_doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    search_query = query.get("query", "")
    top_k = query.get("top_k", 5)
    
    if not search_query:
        raise HTTPException(status_code=400, detail="Query is required")
    
    results = await vector_store.search(db, doc.id, search_query, top_k=top_k)
    
    return {
        "results": results,
        "total": len(results),
        "query": search_query
    }




@router.post("/llm/chat")
async def llm_chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):

    import httpx
    try:
        if request.use_rag:
            doc = await _get_document_by_python_doc_id(db, request.doc_id)
            if not doc:
                raise HTTPException(status_code=404, detail="Document not found")
            
            last_message = request.messages[-1] if request.messages else None
            if last_message and last_message.role == "user":
                result = await rag_pipeline.query(
                    db=db,
                    doc_id=doc.id,
                    question=last_message.content,
                    top_k=5
                )
                
                return ChatResponse(
                    response=result["answer"],
                    sources=result["sources"],
                    tokens_used=result["tokens_used"],
                    latency_ms=result["latency_ms"]
                )
        
        # Calling LLM directly without RAG
        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        
        start_time = time.time()
        response = await llm_client.chat(messages)
        latency_ms = int((time.time() - start_time) * 1000)
        
        return ChatResponse(
            response=response.content,
            tokens_used=response.tokens_used,
            latency_ms=latency_ms
        )
    except httpx.HTTPStatusError as e:
        error_msg = e.response.text
        if e.response.status_code in (401, 403):
            error_msg = "Invalid or missing Sarvam AI API Key. Please update SARVAM_API_KEY in the .env file."
        raise HTTPException(status_code=502, detail=f"LLM API Error: {error_msg}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/{python_doc_id}/extract/summary")
async def extract_summary(python_doc_id: str, request: SummaryRequest, db: AsyncSession = Depends(get_db)):

    doc = await _get_document_by_python_doc_id(db, python_doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if python_doc_id not in extraction_cache:
        file_path = Path(settings.uploads_dir) / doc.filename
        result = pdf_pipeline.extract(str(file_path), python_doc_id)
        extraction_cache[python_doc_id] = {
            "text_blocks": [
                {
                    "text": b.text,
                    "page": b.page,
                    "type": b.block_type,
                    "section": b.section,
                    "heading_path": b.heading_path or [],
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
    
    all_text = "\n".join(
        b["text"] for b in extraction_cache[python_doc_id]["text_blocks"]
    )
    
    if len(all_text) < 100:
        raise HTTPException(status_code=400, detail="Document has insufficient text for summary")
    
    summary_result = await llm_client.summarize(
        text=all_text,
        style=request.style,
        focus_area=request.focus_area
    )
    
   
    import json as _json
    doc.extracted_summary = _json.dumps(summary_result, ensure_ascii=False)
    await db.commit()
    
    return summary_result


@router.post("/llm/analyze")
async def llm_analyze(request: AnalysisRequest, db: AsyncSession = Depends(get_db)):

    doc = await _get_document_by_python_doc_id(db, request.doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if request.doc_id not in extraction_cache:
        file_path = Path(settings.uploads_dir) / doc.filename
        result = pdf_pipeline.extract(str(file_path), request.doc_id)
        extraction_cache[request.doc_id] = {
            "text_blocks": [
                {
                    "text": b.text,
                    "page": b.page,
                    "type": b.block_type,
                    "section": b.section,
                    "heading_path": b.heading_path or [],
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
    
    all_text = "\n".join(
        b["text"] for b in extraction_cache[request.doc_id]["text_blocks"]
    )
    table_data = extraction_cache[request.doc_id].get("tables", [])
    
    analysis = await llm_client.analyze_quantitative(
        text=all_text,
        table_data=table_data
    )
    
    return analysis
