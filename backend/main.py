import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import engine, Base, SessionLocal
from app.db.models import User, Document, DocumentChunk, ChatSession, ChatMessage, ExtractionTask
from app.api.routes import router
from app.api.auth import router as auth_router, ensure_dev_user

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("filysis")

settings = get_settings()

app = FastAPI(
    title="Filysis API",
    description="AI-powered document analysis backend with PostgreSQL + pgvector",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")

@app.on_event("startup")
async def startup_event():
    """Initialize database and services on startup."""
    logger.info("=" * 60)
    logger.info("Filysis Python Backend Starting")
    logger.info("=" * 60)
    
    from sqlalchemy import text
    with engine.connect() as conn:
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
            logger.info("pgvector extension ready")
        except Exception as e:
            logger.warning(f"Could not create pgvector extension: {e}")
            logger.warning("Make sure pgvector is installed in your PostgreSQL instance")
    
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified")
    
    db = SessionLocal()
    try:
        dev_user = ensure_dev_user(db)
        logger.info(f"Dev user ready: {dev_user.name} (id={dev_user.id})")
    finally:
        db.close()
    
    logger.info(f"Database: PostgreSQL")
    logger.info(f"Uploads Dir: {settings.uploads_dir}")
    logger.info(f"Embedding Model: {settings.embedding_model}")
    logger.info(f"OCR Enabled: {settings.ocr_enabled}")
    logger.info(f"Sarvam API Key: {'✓ Configured' if settings.sarvam_api_key else '✗ Not configured'}")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Filysis Python Backend shutting down")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    )
