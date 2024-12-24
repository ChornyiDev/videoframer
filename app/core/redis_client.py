import redis
import json
from .config import get_settings

settings = get_settings()

# Initialize Redis client
redis_client = redis.Redis.from_url(
    settings.REDIS_URL,
    decode_responses=True  # Automatically decode responses to strings
)

class Cache:
    @staticmethod
    def get(key: str) -> dict | None:
        """Get value from cache"""
        try:
            data = redis_client.get(key)
            return json.loads(data) if data else None
        except Exception:
            return None

    @staticmethod
    def set(key: str, value: dict, expire: int = 3600 * 24) -> bool:
        """Set value in cache with expiration"""
        try:
            return redis_client.setex(
                key,
                expire,
                json.dumps(value)
            )
        except Exception:
            return False

    @staticmethod
    def delete(key: str) -> bool:
        """Delete value from cache"""
        try:
            return redis_client.delete(key) > 0
        except Exception:
            return False
