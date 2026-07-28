from pydantic_settings import BaseSettings
from pydantic import field_validator
from functools import lru_cache
from typing import List


class Settings(BaseSettings):

    database_url: str
    sarvam_api_key: str = ""
    embedding_model: str = "all-MiniLM-L6-v2"
    uploads_dir: str = "./uploads"
    max_file_size_mb: int = 50
    ocr_enabled: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Accept both a JSON string and an actual list from the env."""
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v

    model_config = {
        "env_file": "../.env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()
