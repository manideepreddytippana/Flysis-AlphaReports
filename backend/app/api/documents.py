import os
import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.models import ChunkConfig, IndexResponse
from app.db.models import Document

from app.api.deps import vector_store, extraction_cache
from app.api.utils import _get_document_by_python_doc_id, _ensure_extraction_cached

router = APIRouter(tags=["documents"])
logger = logging.getLogger(__name__)
settings = get_settings()

@router.get("/documents")
async def list_documents(
    page: int = 1,
    limit: int = 20,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Document)
    if status:
        query = query.where(Document.status == status)

    count_query = select(Document.id)
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


@router.get("/documents/stats/overview")
async def get_document_stats(
    db: AsyncSession = Depends(get_db),
):
    docs = (await db.execute(select(Document))).scalars().all()
    return {
        "total": len(docs),
        "ready": sum(1 for d in docs if d.status == "ready"),
        "processing": sum(1 for d in docs if d.status == "processing"),
        "error": sum(1 for d in docs if d.status == "error"),
        "totalPages": sum(d.page_count or 0 for d in docs),
    }

@router.get("/documents/{doc_id}")
async def get_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get document metadata."""
    result = await db.execute(select(Document).where(Document.id == doc_id))
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

@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Document).where(Document.id == doc_id))
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

@router.get("/documents/{python_doc_id}/text")
async def get_text(python_doc_id: str, page: int | None = None, db: AsyncSession = Depends(get_db)):
    doc = await _get_document_by_python_doc_id(db, python_doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    await _ensure_extraction_cached(python_doc_id, doc)
    
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
    doc = await _get_document_by_python_doc_id(db, python_doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    info_file = Path("pdf-information") / f"{python_doc_id}_data.json"
    if info_file.exists():
        try:
            with open(info_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read data JSON file: {e}")
            pass
            
    if python_doc_id in extraction_cache:
        return extraction_cache[python_doc_id]
        
    raise HTTPException(status_code=404, detail="Data JSON not found or document not yet processed")

@router.post("/documents/{python_doc_id}/index")
async def index_document(python_doc_id: str, config: ChunkConfig, db: AsyncSession = Depends(get_db)):
    doc = await _get_document_by_python_doc_id(db, python_doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    await _ensure_extraction_cached(python_doc_id, doc)
    
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
