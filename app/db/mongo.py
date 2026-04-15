from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings

_client: Optional[AsyncIOMotorClient] = None


async def connect_mongo() -> None:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.mongodb_url)


async def close_mongo() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


def get_database() -> AsyncIOMotorDatabase:
    if _client is None:
        raise RuntimeError("MongoDB client not initialized")
    return _client[settings.mongodb_db]
