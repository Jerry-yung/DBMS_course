from datetime import datetime
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services import question_service, survey_service
from app.utils.mongo import doc_with_id, parse_oid


def _serialize_rule(doc: Dict[str, Any]) -> Dict[str, Any]:
    d = doc_with_id(doc)
    d["survey_id"] = str(doc.get("survey_id", ""))
    return d


async def _question_in_survey(
    db: AsyncIOMotorDatabase, survey_id: str, qid: str
) -> bool:
    try:
        oid = parse_oid(qid)
    except Exception:
        return False
    doc = await db["questions"].find_one({"_id": oid, "survey_id": survey_id})
    return doc is not None


async def add_rule(
    db: AsyncIOMotorDatabase,
    survey_id: str,
    creator_id: str,
    payload: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    if not await survey_service.get_survey(db, survey_id, creator_id):
        return None
    src, tgt = payload["source_question_id"], payload["target_question_id"]
    if not await _question_in_survey(db, survey_id, src):
        return None
    if not await _question_in_survey(db, survey_id, tgt):
        return None
    now = datetime.utcnow()
    doc = {
        "survey_id": survey_id,
        "source_question_id": src,
        "target_question_id": tgt,
        "condition": payload["condition"],
        "priority": int(payload.get("priority", 0)),
        "enabled": bool(payload.get("enabled", True)),
        "created_at": now,
        "updated_at": now,
    }
    res = await db["jump_rules"].insert_one(doc)
    doc["_id"] = res.inserted_id
    await question_service.set_has_jump_rules(db, survey_id, src, True)
    return _serialize_rule(doc)


async def list_rules(
    db: AsyncIOMotorDatabase, survey_id: str, creator_id: str
) -> Optional[List[Dict[str, Any]]]:
    if not await survey_service.get_survey(db, survey_id, creator_id):
        return None
    cur = db["jump_rules"].find({"survey_id": survey_id}).sort("priority", -1)
    out = []
    async for doc in cur:
        out.append(_serialize_rule(doc))
    return out


async def get_rule(
    db: AsyncIOMotorDatabase, survey_id: str, rule_id: str, creator_id: str
) -> Optional[Dict[str, Any]]:
    if not await survey_service.get_survey(db, survey_id, creator_id):
        return None
    try:
        oid = parse_oid(rule_id)
    except Exception:
        return None
    doc = await db["jump_rules"].find_one({"_id": oid, "survey_id": survey_id})
    if not doc:
        return None
    return _serialize_rule(doc)


async def update_rule(
    db: AsyncIOMotorDatabase,
    survey_id: str,
    rule_id: str,
    creator_id: str,
    patch: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    existing = await get_rule(db, survey_id, rule_id, creator_id)
    if not existing:
        return None
    oid = parse_oid(rule_id)
    old_src = existing["source_question_id"]
    allowed: Dict[str, Any] = {"updated_at": datetime.utcnow()}
    if patch.get("source_question_id") is not None:
        if not await _question_in_survey(db, survey_id, patch["source_question_id"]):
            return None
        allowed["source_question_id"] = patch["source_question_id"]
    if patch.get("target_question_id") is not None:
        if not await _question_in_survey(db, survey_id, patch["target_question_id"]):
            return None
        allowed["target_question_id"] = patch["target_question_id"]
    if patch.get("condition") is not None:
        allowed["condition"] = patch["condition"]
    if patch.get("priority") is not None:
        allowed["priority"] = patch["priority"]
    if patch.get("enabled") is not None:
        allowed["enabled"] = patch["enabled"]
    await db["jump_rules"].update_one({"_id": oid}, {"$set": allowed})
    doc = await db["jump_rules"].find_one({"_id": oid})
    await _refresh_source_flags(db, survey_id, old_src)
    new_src = doc.get("source_question_id", old_src)
    await _refresh_source_flags(db, survey_id, new_src)
    return _serialize_rule(doc)


async def delete_rule(
    db: AsyncIOMotorDatabase, survey_id: str, rule_id: str, creator_id: str
) -> bool:
    existing = await get_rule(db, survey_id, rule_id, creator_id)
    if not existing:
        return False
    src = existing["source_question_id"]
    oid = parse_oid(rule_id)
    await db["jump_rules"].delete_one({"_id": oid})
    await _refresh_source_flags(db, survey_id, src)
    return True


async def _refresh_source_flags(db: AsyncIOMotorDatabase, survey_id: str, src: str) -> None:
    cnt = await db["jump_rules"].count_documents(
        {
            "survey_id": survey_id,
            "source_question_id": src,
            "enabled": True,
        }
    )
    await question_service.set_has_jump_rules(db, survey_id, src, cnt > 0)
