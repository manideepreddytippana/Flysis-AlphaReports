import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import engine, Base, AsyncSessionLocal

from app.api.routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("filysis")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):

    logger.info("=" * 60)
    logger.info("Filysis Python Backend Starting")
    logger.info("=" * 60)

    async with engine.begin() as conn:
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            logger.info("pgvector extension ready")
        except Exception as e:
            logger.warning(f"Could not create pgvector extension: {e}")
            logger.warning(
                "Make sure pgvector is installed in your PostgreSQL instance"
            )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified")

    logger.info("Database: PostgreSQL")
    logger.info(f"Uploads Dir: {settings.uploads_dir}")
    logger.info(f"Embedding Model: {settings.embedding_model}")
    logger.info(f"OCR Enabled: {settings.ocr_enabled}")
    logger.info(
        f"Sarvam API Key: {'✓ Configured' if settings.sarvam_api_key else '✗ Not configured'}"
    )
    logger.info("=" * 60)

    yield

    logger.info("Filysis Python Backend shutting down")


app = FastAPI(
    title="Filysis API",
    description="AI-powered document analysis backend with PostgreSQL + pgvector",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info",
    )