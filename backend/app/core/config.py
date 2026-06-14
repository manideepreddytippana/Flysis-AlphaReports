from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List
import json


class Settings(BaseSettings):

  database_url: str = "postgresql://postgres:mani@localhost:5432/filysis"
  sarvam_api_key: str = ""
  embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
  uploads_dir: str = "./uploads"
  max_file_size_mb: int = 50
  ocr_enabled: bool = True
  host: str = "127.0.0.1"
  port: int = 8001
  debug: bool = True
  cors_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]
  app_secret: str = "filysis"
  class Config:
    env_file = ".env"
    env_file_encoding = "utf-8"
@lru_cache()


def get_settings() -> Settings:
  return Settings()
