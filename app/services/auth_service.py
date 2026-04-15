from datetime import datetime
from typing import Any, Dict, Tuple

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.security import create_access_token, hash_password, verify_password


async def register_user(
    db: AsyncIOMotorDatabase, username: str, password: str
) -> Tuple[bool, str, Dict[str, Any]]:
    coll = db["users"]
    if await coll.find_one({"username": username}):
        return False, "用户名已存在", {}
    doc = {
        "username": username,
        "password": hash_password(password),
        "email": None,
        "role": "user",
        "status": "active",
        "created_at": datetime.utcnow(),
        "last_login": None,
    }
    res = await coll.insert_one(doc)
    uid = str(res.inserted_id)
    return True, "ok", {"user_id": uid, "username": username}


async def login_user(
    db: AsyncIOMotorDatabase, username: str, password: str
) -> Tuple[bool, str, Dict[str, Any]]:
    coll = db["users"]
    user = await coll.find_one({"username": username})
    if not user or not verify_password(password, user["password"]):
        return False, "用户名或密码错误", {}
    if user.get("status") != "active":
        return False, "账号已禁用", {}
    await coll.update_one(
        {"_id": user["_id"]}, {"$set": {"last_login": datetime.utcnow()}}
    )
    uid = str(user["_id"])
    token = create_access_token(uid)
    return True, "ok", {"access_token": token, "token_type": "bearer"}


def user_public(user: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "user_id": user.get("id") or str(user["_id"]),
        "username": user["username"],
        "email": user.get("email"),
        "role": user.get("role", "user"),
    }
