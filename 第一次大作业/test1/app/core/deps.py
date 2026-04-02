from typing import Any, Dict, Optional

from bson import ObjectId
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.security import decode_token_subject
from app.db.mongo import get_database

security = HTTPBearer(auto_error=False)


async def get_db() -> AsyncIOMotorDatabase:
    return get_database()


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": 401, "message": "未认证或令牌无效", "data": {}},
    )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise _unauthorized()
    sub = decode_token_subject(credentials.credentials)
    if not sub:
        raise _unauthorized()
    try:
        oid = ObjectId(sub)
    except Exception:
        raise _unauthorized()
    user = await db["users"].find_one({"_id": oid})
    if not user or user.get("status") != "active":
        raise _unauthorized()
    user["id"] = str(user["_id"])
    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Optional[Dict[str, Any]]:
    if not credentials or credentials.scheme.lower() != "bearer":
        return None
    sub = decode_token_subject(credentials.credentials)
    if not sub:
        return None
    try:
        oid = ObjectId(sub)
    except Exception:
        return None
    user = await db["users"].find_one({"_id": oid})
    if not user or user.get("status") != "active":
        return None
    user["id"] = str(user["_id"])
    return user
