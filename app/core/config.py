from pydantic_settings import BaseSettings
from functools import lru_cache
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "")
    MAX_FRAMES: int = 8
    MIN_DURATION: float = 5.0
    MIN_WORDS: int = 5
    MAX_IMAGE_SIZE: int = 512
    JPEG_QUALITY: int = 70
    SHORT_VIDEO_THRESHOLD: int = 30
    MEDIUM_VIDEO_THRESHOLD: int = 60
    SHORT_VIDEO_INTERVAL: int = 5
    MEDIUM_VIDEO_INTERVAL: int = 10
    LONG_VIDEO_INTERVAL: int = 20
    # Cache settings
    CACHE_EXPIRE_TIME: int = 3600 * 24  # 24 hours
    CACHE_ENABLED: bool = True
    # Celery settings
    CELERY_TASK_TIME_LIMIT: int = 120  # 2 minutes
    CELERY_TASK_SOFT_TIME_LIMIT: int = 110  # 1.8 minutes
    CELERY_MAX_TASKS_PER_CHILD: int = 50  # Restart worker after 50 tasks
    CELERY_WORKER_CONCURRENCY: int = 2  # Number of concurrent tasks
    CELERY_WORKER_PREFETCH_MULTIPLIER: int = 1  # Process one task at a time per worker
    # Network settings
    MAX_VIDEO_SIZE: int = 50 * 1024 * 1024  # 50MB in bytes
    ALLOWED_VIDEO_FORMATS: list = ["video/mp4", "video/quicktime", "video/x-msvideo"]
    REQUEST_TIMEOUT: int = 30  # seconds
    ENABLE_GZIP: bool = True

@lru_cache()
def get_settings():
    return Settings()
