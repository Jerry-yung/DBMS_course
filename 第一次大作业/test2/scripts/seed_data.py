"""可选演示数据：注册用户并创建草稿问卷。运行前确保 MongoDB 可用且已执行 init_db。"""
import asyncio
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings
from app.core.security import hash_password
from app.services import survey_service


async def main():
    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client[settings.mongodb_db]
    username = "demo_user"
    password = "demo123456"
    coll = db["users"]
    if not await coll.find_one({"username": username}):
        await coll.insert_one(
            {
                "username": username,
                "password": hash_password(password),
                "email": None,
                "role": "user",
                "status": "active",
                "created_at": datetime.utcnow(),
                "last_login": None,
            }
        )
        print("Created user:", username, "/", password)
    else:
        print("User exists:", username)

    user = await coll.find_one({"username": username})
    uid = str(user["_id"])
    surveys = db["surveys"]
    existing = await surveys.find_one({"creator_id": uid, "title": "演示问卷"})
    if existing:
        print("Demo survey already exists, short_code:", existing.get("short_code"))
    else:
        data = await survey_service.create_survey(
            db, uid, "演示问卷", "由 seed_data 脚本创建", survey_service._default_settings()
        )
        print("Created draft survey id:", data["id"], "short_code:", data["short_code"])

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
