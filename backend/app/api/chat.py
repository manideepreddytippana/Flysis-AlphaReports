import time
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.core.database import get_db
from app.core.models import ChatRequest, ChatResponse
from app.api.deps import rag_pipeline, llm_client
from app.api.utils import _get_document_by_python_doc_id

router = APIRouter(tags=["chat"])

@router.post("/llm/chat")
async def llm_chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
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
