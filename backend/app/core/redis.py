
import redis.asyncio as aioredis

from app.core.config import settings

# Global Redis client instance
_redis_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """Get or create the Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            protocol=2,
        )
    try:
        await _redis_client.ping()
    except Exception as e:
        _redis_client = None
        raise ConnectionError(f"Failed to connect to Redis: {e}")
    return _redis_client


async def close_redis() -> None:
    """Close the Redis connection."""
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None


async def redis_publish(channel: str, message: str) -> None:
    """Publish a message to a Redis channel (for WebSocket pub/sub)."""
    client = await get_redis()
    await client.publish(channel, message)


async def redis_set(key: str, value: str, expire: int = 3600) -> None:
    """Set a value in Redis with an optional TTL in seconds."""
    client = await get_redis()
    await client.setex(key, expire, value)


async def redis_get(key: str) -> str | None:
    """Get a value from Redis."""
    client = await get_redis()
    return await client.get(key)


async def redis_delete(key: str) -> None:
    """Delete a key from Redis."""
    client = await get_redis()
    await client.delete(key)
