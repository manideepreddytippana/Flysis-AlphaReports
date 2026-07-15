from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List
import json
import os
# import dotenv
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

class Settings(BaseSettings):

  database_url: str = os.getenv("DATABASE_URL")
  sarvam_api_key: str = os.getenv("SARVAM_API_KEY", "")
  embedding_model: str = os.getenv("EMBEDDING_MODEL")
  uploads_dir: str = os.getenv("UPLOADS_DIR", "./uploads")
  max_file_size_mb: int = int(os.getenv("MAX_FILE_SIZE_MB"))
  ocr_enabled: bool = str(os.getenv("OCR_ENABLED", "true")).lower() in ("true", "1", "t")
  host: str = os.getenv("HOST", "127.0.0.1")
  port: int = int(os.getenv("PORT", "8001"))
  debug: bool = str(os.getenv("DEBUG", "true")).lower() in ("true", "1", "t")
  cors_origins: List[str] = json.loads(os.getenv("CORS_ORIGINS", '["http://localhost:3000", "http://localhost:5173"]'))

  class Config:
    env_file = ".env"
    env_file_encoding = "utf-8"
@lru_cache()


def get_settings() -> Settings:
  return Settings()
