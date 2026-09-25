import json
import logging
import asyncio
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.models import SummaryRequest, AnalysisRequest

from app.api.deps import pdf_pipeline, llm_client, extraction_cache
from app.api.utils import _get_document_by_python_doc_id, _ensure_extraction_cached, _build_extraction_dict

router = APIRouter(tags=["analytics"])
logger = logging.getLogger(__name__)
settings = get_settings()

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
        result = await asyncio.to_thread(pdf_pipeline.extract, str(file_path), python_doc_id)
        
        extraction_result = _build_extraction_dict(result, include_metadata=True)
        
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
        tables = await asyncio.to_thread(pdf_pipeline.extract_tables_only, str(file_path))
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


@router.post("/documents/{python_doc_id}/extract/summary")
async def extract_summary(python_doc_id: str, request: SummaryRequest, db: AsyncSession = Depends(get_db)):
    doc = await _get_document_by_python_doc_id(db, python_doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    await _ensure_extraction_cached(python_doc_id, doc)
    
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
    
    doc.extracted_summary = json.dumps(summary_result, ensure_ascii=False)
    await db.commit()
    
    return summary_result


@router.post("/llm/analyze")
async def llm_analyze(request: AnalysisRequest, db: AsyncSession = Depends(get_db)):
    doc = await _get_document_by_python_doc_id(db, request.doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    await _ensure_extraction_cached(request.doc_id, doc)
    
    all_text = "\n".join(
        b["text"] for b in extraction_cache[request.doc_id]["text_blocks"]
    )
    table_data = extraction_cache[request.doc_id].get("tables", [])
    
    analysis = await llm_client.analyze_quantitative(
        text=all_text,
        table_data=table_data
    )
    
    return analysis
