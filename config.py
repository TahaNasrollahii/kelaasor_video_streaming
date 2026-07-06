from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    FASTAPI_API_KEY: str = "default_secret_api_key_for_dev"
    DATABASE_URL: str = "sqlite:///path/to/kelaasor_back/db.sqlite3"
    REDIS_URL: str = "redis://localhost:6379/0"
    DJANGO_WEBHOOK_URL: str = "http://127.0.0.1:8000/api/webhooks/video-status/"
    MEDIA_DIR: str = "E:/path/to/kelaasor_back/media"
    
    class Config:
        env_file = ".env"

settings = Settings()
