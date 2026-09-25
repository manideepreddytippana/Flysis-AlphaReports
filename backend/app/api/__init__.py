from fastapi import APIRouter
from app.api.upload import router as upload_router
from app.api.documents import router as documents_router
from app.api.chat import router as chat_router
from app.api.analytics import router as analytics_router
from app.core.config import get_settings

router = APIRouter()
settings = get_settings()

@router.get("/health", tags=["health"])
async def health_check():
    return {
        "status": "ok",
        "version": "1.0.0",
        "services": {
            "pdf_extraction": "ready",
            "pgvector": "ready",
            "sarvam_llm": "ready" if settings.sarvam_api_key else "no_api_key"
        }
    }

router.include_router(upload_router)
router.include_router(documents_router)
router.include_router(chat_router)
router.include_router(analytics_router)
