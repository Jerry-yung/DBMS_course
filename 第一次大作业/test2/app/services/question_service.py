from datetime import datetime
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services import library_question_service, survey_service
from app.utils.mongo import doc_with_id, oid_str, parse_oid


def _serialize_question(doc: Dict[str, Any]) -> Dict[str, Any]:
    d = doc_with_id(doc)
    d["survey_id"] = str(doc.get("survey_id", ""))
    opts = doc.get("options") or []
    for i, o in enumerate(opts):
        if "order" not in o:
            o["order"] = i
    d["options"] = opts
    d["validation"] = doc.get("validation") or {}
    d["type"] = doc.get("type", "")
    if doc.get("lineage_id"):
        d["lineage_id"] = str(doc["lineage_id"])
    else:
        d["lineage_id"] = None
    sv = doc.get("source_library_version_id")
    d["source_library_version_id"] = str(sv) if sv else None
    return d


async def _survey_questions_locked(
    db: AsyncIOMotorDatabase, survey_id: str
) -> bool:
    try:
        oid = parse_oid(survey_id)
    except Exception:
        return True
    raw = await db["surveys"].find_one({"_id": oid})
    if not raw:
        return True
    st = raw.get("status", "draft")
    return st in ("published", "closed")


async def add_question(
    db: AsyncIOMotorDatabase,
    survey_id: str,
    creator_id: str,
    payload: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    s = await survey_service.get_survey(db, survey_id, creator_id)
    if not s:
        return None
    if await _survey_questions_locked(db, survey_id):
        return None

    max_order = 0
    cur = db["questions"].find({"survey_id": survey_id}).sort("order", -1).limit(1)
    async for q in cur:
        max_order = int(q.get("order", 0))

    options = []
    for i, o in enumerate(payload.get("options") or []):
        options.append(
            {
                "value": o["value"],
                "label": o["label"],
                "order": o.get("order", i),
            }
        )

    now = datetime.utcnow()
    doc = {
        "survey_id": survey_id,
        "title": payload["title"],
        "type": payload["type"],
        "required": bool(payload.get("required", False)),
        "order": max_order + 1,
        "options": options,
        "validation": payload.get("validation") or {},
        "has_jump_rules": False,
        "created_at": now,
        "updated_at": now,
    }
    res = await db["questions"].insert_one(doc)
    doc["_id"] = res.inserted_id
    await survey_service.refresh_question_order(db, survey_id)
    return _serialize_question(doc)


async def add_question_from_library(
    db: AsyncIOMotorDatabase,
    survey_id: str,
    creator_id: str,
    library_question_id: str,
) -> Optional[Dict[str, Any]]:
    s = await survey_service.get_survey(db, survey_id, creator_id)
    if not s:
        return None
    if s.get("status", "draft") != "draft":
        return None
    lib = await library_question_service.get_library_question_raw(
        db, library_question_id
    )
    if not lib:
        return None
    if not await library_question_service.can_use_library_version(
        db, creator_id, lib
    ):
        return None

    max_order = 0
    cur = db["questions"].find({"survey_id": survey_id}).sort("order", -1).limit(1)
    async for q in cur:
        max_order = int(q.get("order", 0))

    now = datetime.utcnow()
    options = []
    for i, o in enumerate(lib.get("options") or []):
        options.append(
            {
                "value": o["value"],
                "label": o["label"],
                "order": o.get("order", i),
            }
        )
    doc = {
        "survey_id": survey_id,
        "title": lib.get("title", ""),
        "type": lib.get("type", ""),
        "required": bool(lib.get("required", False)),
        "order": max_order + 1,
        "options": options,
        "validation": lib.get("validation") or {},
        "has_jump_rules": False,
        "lineage_id": str(lib.get("lineage_id", "")),
        "source_library_version_id": oid_str(lib["_id"]),
        "created_at": now,
        "updated_at": now,
    }
    res = await db["questions"].insert_one(doc)
    doc["_id"] = res.inserted_id
    await survey_service.refresh_question_order(db, survey_id)
    return _serialize_question(doc)


async def list_questions(
    db: AsyncIOMotorDatabase, survey_id: str, creator_id: str
) -> Optional[List[Dict[str, Any]]]:
    if not await survey_service.get_survey(db, survey_id, creator_id):
        return None
    cur = db["questions"].find({"survey_id": survey_id}).sort("order", 1)
    out = []
    async for doc in cur:
        out.append(_serialize_question(doc))
    return out


async def get_question(
    db: AsyncIOMotorDatabase, survey_id: str, qid: str, creator_id: str
) -> Optional[Dict[str, Any]]:
    if not await survey_service.get_survey(db, survey_id, creator_id):
        return None
    try:
        oid = parse_oid(qid)
    except Exception:
        return None
    doc = await db["questions"].find_one({"_id": oid, "survey_id": survey_id})
    if not doc:
        return None
    return _serialize_question(doc)


async def update_question(
    db: AsyncIOMotorDatabase,
    survey_id: str,
    qid: str,
    creator_id: str,
    patch: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    if not await get_question(db, survey_id, qid, creator_id):
        return None
    if await _survey_questions_locked(db, survey_id):
        return None
    oid = parse_oid(qid)
    allowed: Dict[str, Any] = {"updated_at": datetime.utcnow()}
    if patch.get("title") is not None:
        allowed["title"] = patch["title"]
    if patch.get("type") is not None:
        allowed["type"] = patch["type"]
    if patch.get("required") is not None:
        allowed["required"] = patch["required"]
    if patch.get("options") is not None:
        opts = []
        for i, o in enumerate(patch["options"]):
            opts.append(
                {
                    "value": o["value"],
                    "label": o["label"],
                    "order": o.get("order", i),
                }
            )
        allowed["options"] = opts
    if patch.get("validation") is not None:
        allowed["validation"] = patch["validation"]
    await db["questions"].update_one({"_id": oid}, {"$set": allowed})
    doc = await db["questions"].find_one({"_id": oid})
    return _serialize_question(doc)


async def apply_library_version_to_survey_question(
    db: AsyncIOMotorDatabase,
    survey_id: str,
    qid: str,
    creator_id: str,
    library_question_id: str,
) -> Optional[Dict[str, Any]]:
    """用某一库题版本覆盖草稿问卷中的题目（须同一 lineage 且用户可查看该库题）。"""
    if await _survey_questions_locked(db, survey_id):
        return None
    q = await get_question(db, survey_id, qid, creator_id)
    if not q:
        return None
    q_lineage = q.get("lineage_id")
    if not q_lineage:
        return None
    lib = await library_question_service.get_library_question_raw(
        db, library_question_id
    )
    if not lib:
        return None
    if not await library_question_service.can_use_library_version(
        db, creator_id, lib
    ):
        return None
    lib_lineage = str(lib.get("lineage_id", ""))
    if str(q_lineage) != lib_lineage:
        return None
    options = []
    for i, o in enumerate(lib.get("options") or []):
        options.append(
            {
                "value": o["value"],
                "label": o["label"],
                "order": o.get("order", i),
            }
        )
    now = datetime.utcnow()
    oid = parse_oid(qid)
    await db["questions"].update_one(
        {"_id": oid},
        {
            "$set": {
                "title": lib.get("title", ""),
                "type": lib.get("type", ""),
                "required": bool(lib.get("required", False)),
                "options": options,
                "validation": lib.get("validation") or {},
                "lineage_id": lib_lineage,
                "source_library_version_id": oid_str(lib["_id"]),
                "updated_at": now,
            }
        },
    )
    doc = await db["questions"].find_one({"_id": oid})
    return _serialize_question(doc) if doc else None


async def delete_question(
    db: AsyncIOMotorDatabase, survey_id: str, qid: str, creator_id: str
) -> bool:
    if not await get_question(db, survey_id, qid, creator_id):
        return False
    if await _survey_questions_locked(db, survey_id):
        return False
    oid = parse_oid(qid)
    await db["questions"].delete_one({"_id": oid})
    await db["jump_rules"].delete_many(
        {
            "survey_id": survey_id,
            "$or": [
                {"source_question_id": qid},
                {"target_question_id": qid},
            ],
        }
    )
    await survey_service.refresh_question_order(db, survey_id)
    await _sync_has_jump_flags(db, survey_id)
    return True


async def reorder_questions(
    db: AsyncIOMotorDatabase,
    survey_id: str,
    creator_id: str,
    question_ids: List[str],
) -> Optional[List[Dict[str, Any]]]:
    if not await survey_service.get_survey(db, survey_id, creator_id):
        return None
    existing = set()
    cur = db["questions"].find({"survey_id": survey_id})
    async for q in cur:
        existing.add(oid_str(q["_id"]))
    if set(question_ids) != existing:
        return None
    for i, qid in enumerate(question_ids):
        await db["questions"].update_one(
            {"survey_id": survey_id, "_id": parse_oid(qid)},
            {"$set": {"order": i + 1, "updated_at": datetime.utcnow()}},
        )
    await survey_service.refresh_question_order(db, survey_id)
    return await list_questions(db, survey_id, creator_id)


async def _sync_has_jump_flags(db: AsyncIOMotorDatabase, survey_id: str) -> None:
    cur = db["questions"].find({"survey_id": survey_id})
    async for q in cur:
        qid = oid_str(q["_id"])
        cnt = await db["jump_rules"].count_documents(
            {"survey_id": survey_id, "source_question_id": qid, "enabled": True}
        )
        await db["questions"].update_one(
            {"_id": q["_id"]},
            {"$set": {"has_jump_rules": cnt > 0}},
        )


async def set_has_jump_rules(
    db: AsyncIOMotorDatabase, survey_id: str, source_qid: str, flag: bool
) -> None:
    await db["questions"].update_one(
        {"survey_id": survey_id, "_id": parse_oid(source_qid)},
        {"$set": {"has_jump_rules": flag}},
    )
