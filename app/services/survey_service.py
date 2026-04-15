import secrets
import string
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services import jump_engine
from app.utils.mongo import doc_with_id, oid_str, parse_oid


async def _unique_short_code(db: AsyncIOMotorDatabase) -> str:
    coll = db["surveys"]
    alphabet = string.ascii_letters + string.digits
    for _ in range(50):
        code = "".join(secrets.choice(alphabet) for _ in range(8))
        if not await coll.find_one({"short_code": code}):
            return code
    raise RuntimeError("无法生成唯一短码")


async def create_survey(
    db: AsyncIOMotorDatabase, creator_id: str, title: str, description: str, settings: Dict[str, Any]
) -> Dict[str, Any]:
    short_code = await _unique_short_code(db)
    now = datetime.utcnow()
    doc = {
        "title": title,
        "description": description or "",
        "creator_id": creator_id,
        "short_code": short_code,
        "status": "draft",
        "settings": settings,
        "question_order": [],
        "total_responses": 0,
        "created_at": now,
        "published_at": None,
        "closed_at": None,
    }
    res = await db["surveys"].insert_one(doc)
    doc["_id"] = res.inserted_id
    return _serialize_survey(doc)


def _default_settings() -> Dict[str, Any]:
    return {
        "allow_anonymous": False,
        "allow_multiple": True,
        "deadline": None,
        "thank_you_message": "感谢您的参与！",
    }


def _serialize_survey(doc: Dict[str, Any]) -> Dict[str, Any]:
    d = doc_with_id(doc)
    d["creator_id"] = str(doc.get("creator_id", ""))
    if "settings" not in doc or doc["settings"] is None:
        d["settings"] = _default_settings()
    return d


async def list_surveys(db: AsyncIOMotorDatabase, creator_id: str) -> List[Dict[str, Any]]:
    cur = db["surveys"].find({"creator_id": creator_id}).sort("created_at", -1)
    out = []
    async for doc in cur:
        out.append(_serialize_survey(doc))
    return out


async def get_survey(
    db: AsyncIOMotorDatabase, survey_id: str, creator_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    try:
        oid = parse_oid(survey_id)
    except Exception:
        return None
    doc = await db["surveys"].find_one({"_id": oid})
    if not doc:
        return None
    if creator_id is not None and doc.get("creator_id") != creator_id:
        return None
    return _serialize_survey(doc)


async def update_survey(
    db: AsyncIOMotorDatabase,
    survey_id: str,
    creator_id: str,
    patch: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    doc = await get_survey(db, survey_id, creator_id)
    if not doc:
        return None
    oid = parse_oid(survey_id)
    allowed: Dict[str, Any] = {}
    if patch.get("title") is not None:
        allowed["title"] = patch["title"]
    if patch.get("description") is not None:
        allowed["description"] = patch["description"]
    if patch.get("settings") is not None:
        raw = await db["surveys"].find_one({"_id": oid})
        base = _default_settings()
        if raw and raw.get("settings"):
            base.update(raw["settings"])
        base.update(patch["settings"])
        allowed["settings"] = base
    if not allowed:
        return doc
    await db["surveys"].update_one({"_id": oid}, {"$set": allowed})
    fresh = await db["surveys"].find_one({"_id": oid})
    return _serialize_survey(fresh)


async def duplicate_survey(
    db: AsyncIOMotorDatabase, survey_id: str, creator_id: str
) -> Optional[Dict[str, Any]]:
    """复制问卷为新的草稿（含题目与跳转规则），标题为「原标题-副本」。"""
    if not await get_survey(db, survey_id, creator_id):
        return None
    try:
        oid = parse_oid(survey_id)
    except Exception:
        return None
    full = await db["surveys"].find_one({"_id": oid})
    if not full:
        return None
    base_title = str(full.get("title") or "").strip() or "未命名问卷"
    new_title = base_title + "-副本"
    settings = _default_settings()
    if full.get("settings"):
        settings.update(dict(full["settings"]))
    new_survey = await create_survey(
        db, creator_id, new_title, str(full.get("description") or ""), settings
    )
    new_id = new_survey["id"]

    from app.services import question_service

    qcur = db["questions"].find({"survey_id": survey_id}).sort([("order", 1), ("_id", 1)])
    id_map: Dict[str, str] = {}
    now = datetime.utcnow()
    async for q in qcur:
        old_id = oid_str(q["_id"])
        new_doc = {k: v for k, v in q.items() if k != "_id"}
        new_doc["survey_id"] = new_id
        new_doc["created_at"] = now
        new_doc["updated_at"] = now
        ins = await db["questions"].insert_one(new_doc)
        id_map[old_id] = oid_str(ins.inserted_id)

    rules = await db["jump_rules"].find({"survey_id": survey_id}).to_list(length=500)
    for r in rules:
        src = id_map.get(str(r.get("source_question_id") or ""))
        tgt = id_map.get(str(r.get("target_question_id") or ""))
        if not src or not tgt:
            continue
        nr = {
            "survey_id": new_id,
            "source_question_id": src,
            "target_question_id": tgt,
            "condition": r.get("condition") or {},
            "priority": int(r.get("priority", 0)),
            "enabled": bool(r.get("enabled", True)),
            "created_at": now,
            "updated_at": now,
        }
        await db["jump_rules"].insert_one(nr)

    await refresh_question_order(db, new_id)
    await question_service._sync_has_jump_flags(db, new_id)
    return await get_survey(db, new_id, creator_id)


async def delete_survey(db: AsyncIOMotorDatabase, survey_id: str, creator_id: str) -> bool:
    doc = await get_survey(db, survey_id, creator_id)
    if not doc:
        return False
    oid = parse_oid(survey_id)
    await db["questions"].delete_many({"survey_id": survey_id})
    await db["jump_rules"].delete_many({"survey_id": survey_id})
    await db["responses"].delete_many({"survey_id": survey_id})
    await db["surveys"].delete_one({"_id": oid})
    return True


async def publish_survey(
    db: AsyncIOMotorDatabase, survey_id: str, creator_id: str
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    doc = await get_survey(db, survey_id, creator_id)
    if not doc:
        return False, "问卷不存在", None
    if doc["status"] == "published":
        return True, "ok", doc
    rules = await db["jump_rules"].find({"survey_id": survey_id}).to_list(length=500)
    cycles = jump_engine.detect_cycle(rules)
    if cycles:
        return False, "跳转规则存在循环，无法发布", None
    oid = parse_oid(survey_id)
    now = datetime.utcnow()
    await db["surveys"].update_one(
        {"_id": oid},
        {"$set": {"status": "published", "published_at": now}},
    )
    fresh = await db["surveys"].find_one({"_id": oid})
    return True, "ok", _serialize_survey(fresh)


async def close_survey(
    db: AsyncIOMotorDatabase, survey_id: str, creator_id: str
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    doc = await get_survey(db, survey_id, creator_id)
    if not doc:
        return False, "问卷不存在", None
    oid = parse_oid(survey_id)
    now = datetime.utcnow()
    await db["surveys"].update_one(
        {"_id": oid},
        {"$set": {"status": "closed", "closed_at": now}},
    )
    fresh = await db["surveys"].find_one({"_id": oid})
    return True, "ok", _serialize_survey(fresh)


async def refresh_question_order(db: AsyncIOMotorDatabase, survey_id: str) -> None:
    cur = (
        db["questions"]
        .find({"survey_id": survey_id})
        .sort([("order", 1), ("_id", 1)])
    )
    ids = []
    async for q in cur:
        ids.append(oid_str(q["_id"]))
    await db["surveys"].update_one(
        {"_id": parse_oid(survey_id)},
        {"$set": {"question_order": ids}},
    )
