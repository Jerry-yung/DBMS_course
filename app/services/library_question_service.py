import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.services import survey_service
from app.utils.mongo import doc_with_id, oid_str, parse_oid


def _norm_options(raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for i, o in enumerate(raw or []):
        out.append(
            {
                "value": o["value"],
                "label": o["label"],
                "order": o.get("order", i),
            }
        )
    return out


def _survey_to_library_payload(qdoc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "title": qdoc.get("title", ""),
        "type": qdoc.get("type", ""),
        "required": bool(qdoc.get("required", False)),
        "options": _norm_options(qdoc.get("options") or []),
        "validation": qdoc.get("validation") or {},
    }


def _library_payload_fingerprint(payload: Dict[str, Any]) -> str:
    """用于比较问卷草稿与库题内容是否一致（避免无改动时重复插入新版本）。"""
    norm = {
        "title": str(payload.get("title", "")),
        "type": str(payload.get("type", "")),
        "required": bool(payload.get("required", False)),
        "options": _norm_options(payload.get("options") or []),
        "validation": payload.get("validation") or {},
    }
    return json.dumps(norm, sort_keys=True, ensure_ascii=False)


def _serialized_library_fingerprint(ser: Dict[str, Any]) -> str:
    norm = {
        "title": str(ser.get("title", "")),
        "type": str(ser.get("type", "")),
        "required": bool(ser.get("required", False)),
        "options": _norm_options(ser.get("options") or []),
        "validation": ser.get("validation") or {},
    }
    return json.dumps(norm, sort_keys=True, ensure_ascii=False)


def _serialize_library_question(doc: Dict[str, Any]) -> Dict[str, Any]:
    d = doc_with_id(doc)
    d["owner_id"] = str(doc.get("owner_id", ""))
    d["lineage_id"] = str(doc.get("lineage_id", ""))
    pv = doc.get("parent_version_id")
    d["parent_version_id"] = str(pv) if pv else None
    opts = doc.get("options") or []
    for i, o in enumerate(opts):
        if "order" not in o:
            o["order"] = i
    d["options"] = opts
    d["validation"] = doc.get("validation") or {}
    d["type"] = doc.get("type", "")
    return d


async def _lineage_owner_id(
    db: AsyncIOMotorDatabase, lineage_id: str
) -> Optional[str]:
    doc = await db["library_questions"].find_one({"lineage_id": lineage_id})
    if not doc:
        return None
    return str(doc.get("owner_id", ""))


async def is_lineage_owner(
    db: AsyncIOMotorDatabase, user_id: str, lineage_id: str
) -> bool:
    oid = await _lineage_owner_id(db, lineage_id)
    return oid is not None and oid == user_id


async def can_view_lineage(
    db: AsyncIOMotorDatabase, user_id: str, lineage_id: str
) -> bool:
    if await is_lineage_owner(db, user_id, lineage_id):
        return True
    sh = await db["question_shares"].find_one(
        {"grantee_id": user_id, "lineage_id": lineage_id}
    )
    return sh is not None


async def can_use_library_version(
    db: AsyncIOMotorDatabase, user_id: str, doc: Dict[str, Any]
) -> bool:
    lineage_id = str(doc.get("lineage_id", ""))
    if not lineage_id:
        return False
    return await can_view_lineage(db, user_id, lineage_id)


async def get_library_question_raw(
    db: AsyncIOMotorDatabase, library_question_id: str
) -> Optional[Dict[str, Any]]:
    try:
        oid = parse_oid(library_question_id)
    except Exception:
        return None
    return await db["library_questions"].find_one({"_id": oid})


async def get_library_question(
    db: AsyncIOMotorDatabase, library_question_id: str, user_id: str
) -> Optional[Dict[str, Any]]:
    doc = await get_library_question_raw(db, library_question_id)
    if not doc:
        return None
    if not await can_use_library_version(db, user_id, doc):
        return None
    return _serialize_library_question(doc)


async def get_latest_visible_library_by_lineage(
    db: AsyncIOMotorDatabase, user_id: str, lineage_id: str
) -> Optional[Dict[str, Any]]:
    if not lineage_id:
        return None
    if not await can_view_lineage(db, user_id, lineage_id):
        return None
    doc = (
        await db["library_questions"]
        .find({"lineage_id": lineage_id})
        .sort("created_at", -1)
        .limit(1)
        .to_list(length=1)
    )
    if not doc:
        return None
    return _serialize_library_question(doc[0])


async def create_library_question(
    db: AsyncIOMotorDatabase, owner_id: str, payload: Dict[str, Any]
) -> Dict[str, Any]:
    now = datetime.utcnow()
    lineage_id = str(ObjectId())
    options = _norm_options(payload.get("options") or [])
    doc = {
        "owner_id": owner_id,
        "lineage_id": lineage_id,
        "parent_version_id": None,
        "title": payload["title"],
        "type": payload["type"],
        "required": bool(payload.get("required", False)),
        "options": options,
        "validation": payload.get("validation") or {},
        "created_at": now,
    }
    res = await db["library_questions"].insert_one(doc)
    doc["_id"] = res.inserted_id
    return _serialize_library_question(doc)


async def delete_library_question_owned(
    db: AsyncIOMotorDatabase, library_question_id: str, owner_id: str
) -> bool:
    doc = await get_library_question_raw(db, library_question_id)
    if not doc:
        return False
    if str(doc.get("owner_id", "")) != owner_id:
        return False
    try:
        oid = parse_oid(library_question_id)
    except Exception:
        return False
    res = await db["library_questions"].delete_one({"_id": oid})
    return res.deleted_count > 0


async def update_library_question_owned(
    db: AsyncIOMotorDatabase,
    owner_id: str,
    library_question_id: str,
    payload: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """在原文档上更新库题（仅 owner），不插入新版本。"""
    raw = await get_library_question_raw(db, library_question_id)
    if not raw:
        return None
    if str(raw.get("owner_id", "")) != str(owner_id):
        return None
    try:
        qoid = parse_oid(library_question_id)
    except Exception:
        return None
    options = _norm_options(payload.get("options") or [])
    now = datetime.utcnow()
    await db["library_questions"].update_one(
        {"_id": qoid},
        {
            "$set": {
                "title": payload["title"],
                "type": payload["type"],
                "required": bool(payload.get("required", False)),
                "options": options,
                "validation": payload.get("validation") or {},
                "updated_at": now,
            }
        },
    )
    fresh = await get_library_question_raw(db, library_question_id)
    if not fresh:
        return None
    return _serialize_library_question(fresh)


async def delete_library_version_owned(
    db: AsyncIOMotorDatabase, user_id: str, library_question_id: str
) -> Tuple[bool, str]:
    """删除某一库题版本（仅 owner）。子版本挂到被删版本的上一版；清理展示钉选与问卷 source 引用。"""
    raw = await get_library_question_raw(db, library_question_id)
    if not raw:
        return False, "题目不存在"
    if str(raw.get("owner_id", "")) != str(user_id):
        return False, "无权删除该版本"
    try:
        my_oid = parse_oid(library_question_id)
    except Exception:
        return False, "题目 id 无效"
    my_id_str = oid_str(my_oid)
    parent_pv = raw.get("parent_version_id")
    cur = db["library_questions"].find({"parent_version_id": my_id_str})
    async for ch in cur:
        await db["library_questions"].update_one(
            {"_id": ch["_id"]},
            {"$set": {"parent_version_id": parent_pv}},
        )
    await db["question_bank_items"].update_many(
        {"display_library_question_id": my_id_str},
        {"$unset": {"display_library_question_id": ""}},
    )
    await db["questions"].update_many(
        {"source_library_version_id": my_id_str},
        {"$unset": {"source_library_version_id": ""}},
    )
    res = await db["library_questions"].delete_one({"_id": my_oid})
    if res.deleted_count < 1:
        return False, "删除失败"
    return True, "ok"


async def create_new_version(
    db: AsyncIOMotorDatabase,
    owner_id: str,
    from_library_question_id: str,
    payload: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    old = await get_library_question_raw(db, from_library_question_id)
    if not old:
        return None
    if str(old.get("owner_id", "")) != owner_id:
        return None
    now = datetime.utcnow()
    options = _norm_options(payload.get("options") or [])
    doc = {
        "owner_id": owner_id,
        "lineage_id": str(old.get("lineage_id", "")),
        "parent_version_id": oid_str(old["_id"]),
        "title": payload["title"],
        "type": payload["type"],
        "required": bool(payload.get("required", False)),
        "options": options,
        "validation": payload.get("validation") or {},
        "created_at": now,
    }
    res = await db["library_questions"].insert_one(doc)
    doc["_id"] = res.inserted_id
    return _serialize_library_question(doc)


async def restore_version_as_new(
    db: AsyncIOMotorDatabase, owner_id: str, template_library_question_id: str
) -> Optional[Dict[str, Any]]:
    tpl = await get_library_question_raw(db, template_library_question_id)
    if not tpl:
        return None
    if str(tpl.get("owner_id", "")) != owner_id:
        return None
    payload = {
        "title": tpl.get("title", ""),
        "type": tpl.get("type", ""),
        "required": bool(tpl.get("required", False)),
        "options": tpl.get("options") or [],
        "validation": tpl.get("validation") or {},
    }
    return await create_new_version(db, owner_id, template_library_question_id, payload)


async def list_visible_library_questions(
    db: AsyncIOMotorDatabase, user_id: str
) -> List[Dict[str, Any]]:
    owned_cur = db["library_questions"].find({"owner_id": user_id}).sort(
        "created_at", -1
    )
    owned: List[Dict[str, Any]] = []
    async for doc in owned_cur:
        owned.append(_serialize_library_question(doc))

    shared_lineages: Set[str] = set()
    sc = db["question_shares"].find({"grantee_id": user_id})
    async for row in sc:
        shared_lineages.add(str(row.get("lineage_id", "")))

    extra: List[Dict[str, Any]] = []
    for lid in shared_lineages:
        if not lid:
            continue
        cur = db["library_questions"].find({"lineage_id": lid}).sort("created_at", -1)
        async for doc in cur:
            extra.append(_serialize_library_question(doc))

    seen = {d["id"] for d in owned}
    for d in extra:
        if d["id"] not in seen:
            owned.append(d)
            seen.add(d["id"])
    owned.sort(key=lambda x: x.get("created_at") or datetime.min, reverse=True)
    return owned


async def list_versions(
    db: AsyncIOMotorDatabase, user_id: str, lineage_id: str
) -> Optional[List[Dict[str, Any]]]:
    if not await can_view_lineage(db, user_id, lineage_id):
        return None
    cur = db["library_questions"].find({"lineage_id": lineage_id}).sort(
        "created_at", 1
    )
    out = []
    async for doc in cur:
        out.append(_serialize_library_question(doc))
    return out


async def lineage_usage_for_user(
    db: AsyncIOMotorDatabase, user_id: str, lineage_id: str
) -> Optional[List[Dict[str, Any]]]:
    if not await can_view_lineage(db, user_id, lineage_id):
        return None
    qcur = db["questions"].find({"lineage_id": lineage_id})
    survey_ids: Set[str] = set()
    async for q in qcur:
        survey_ids.add(str(q.get("survey_id", "")))

    out: List[Dict[str, Any]] = []
    for sid in survey_ids:
        sdoc = await db["surveys"].find_one({"_id": parse_oid(sid)})
        if not sdoc:
            continue
        if str(sdoc.get("creator_id", "")) != user_id:
            continue
        curq = db["questions"].find({"survey_id": sid, "lineage_id": lineage_id})
        async for q in curq:
            out.append(
                {
                    "survey_id": sid,
                    "survey_title": sdoc.get("title", ""),
                    "survey_status": sdoc.get("status", ""),
                    "question_id": oid_str(q["_id"]),
                }
            )
    return out


async def promote_survey_question(
    db: AsyncIOMotorDatabase,
    user_id: str,
    survey_id: str,
    question_id: str,
) -> Tuple[Optional[Dict[str, Any]], bool]:
    """将问卷题目写入题库。返回 (库题序列化结果, 是否本次新插入了文档)。

    若题目已关联某家族且当前用户为该家族 owner：在最新可见版本上链式插入新版本；
    若与最新版本内容指纹相同则复用该版本（不插入）。其它情况新建家族。
    did_create=False 时调用方不得在失败时 delete 该 id（可能为既有版本）。
    """
    sur = await survey_service.get_survey(db, survey_id, user_id)
    if not sur:
        return None, False
    try:
        qoid = parse_oid(question_id)
    except Exception:
        return None, False
    qdoc = await db["questions"].find_one(
        {"_id": qoid, "survey_id": survey_id}
    )
    if not qdoc:
        return None, False
    payload = _survey_to_library_payload(qdoc)
    survey_fp = _library_payload_fingerprint(payload)

    lid = str(qdoc.get("lineage_id") or "").strip()
    if lid and await is_lineage_owner(db, user_id, lid):
        latest = await get_latest_visible_library_by_lineage(db, user_id, lid)
        if not latest:
            return None, False
        if _serialized_library_fingerprint(latest) == survey_fp:
            return latest, False
        new_doc = await create_new_version(db, user_id, latest["id"], payload)
        if new_doc:
            return new_doc, True
        return None, False

    lib = await create_library_question(db, user_id, payload)
    return lib, True


async def share_lineage(
    db: AsyncIOMotorDatabase,
    grantor_id: str,
    grantee_username: str,
    lineage_id: str,
) -> Tuple[bool, str]:
    if not await is_lineage_owner(db, grantor_id, lineage_id):
        return False, "无权共享该题目家族"
    ge = await db["users"].find_one({"username": grantee_username})
    if not ge:
        return False, "用户不存在"
    gid = str(ge["_id"])
    if gid == grantor_id:
        return False, "不能共享给自己"
    now = datetime.utcnow()
    share_doc = {
        "grantor_id": grantor_id,
        "grantee_id": gid,
        "lineage_id": lineage_id,
        "created_at": now,
    }
    try:
        await db["question_shares"].insert_one(share_doc)
    except DuplicateKeyError:
        return False, "已共享过该用户"
    from app.services import question_bank_service

    inbox = await question_bank_service.ensure_shared_inbox_bank(db, gid)
    ok_item, msg_item, _ = await question_bank_service.add_bank_item_by_lineage(
        db, inbox["id"], gid, lineage_id, allow_shared_inbox=True
    )
    if not ok_item:
        await db["question_shares"].delete_one(
            {
                "grantor_id": grantor_id,
                "grantee_id": gid,
                "lineage_id": lineage_id,
            }
        )
        return False, msg_item or "共享失败"
    return True, "ok"


async def list_shares_outgoing(
    db: AsyncIOMotorDatabase, grantor_id: str
) -> List[Dict[str, Any]]:
    cur = db["question_shares"].find({"grantor_id": grantor_id}).sort(
        "created_at", -1
    )
    out = []
    async for row in cur:
        ge = None
        try:
            ge = await db["users"].find_one(
                {"_id": parse_oid(str(row.get("grantee_id", "")))}
            )
        except Exception:
            ge = None
        out.append(
            {
                "id": oid_str(row["_id"]),
                "lineage_id": row.get("lineage_id"),
                "grantee_id": row.get("grantee_id"),
                "grantee_username": ge.get("username") if ge else "",
                "created_at": row.get("created_at"),
            }
        )
    return out


async def list_shares_incoming(
    db: AsyncIOMotorDatabase, grantee_id: str
) -> List[Dict[str, Any]]:
    cur = db["question_shares"].find({"grantee_id": grantee_id}).sort(
        "created_at", -1
    )
    out = []
    async for row in cur:
        go = None
        try:
            go = await db["users"].find_one(
                {"_id": parse_oid(str(row.get("grantor_id", "")))}
            )
        except Exception:
            go = None
        out.append(
            {
                "id": oid_str(row["_id"]),
                "lineage_id": row.get("lineage_id"),
                "grantor_id": row.get("grantor_id"),
                "grantor_username": go.get("username") if go else "",
                "created_at": row.get("created_at"),
            }
        )
    return out


async def revoke_share(
    db: AsyncIOMotorDatabase, grantor_id: str, share_id: str
) -> bool:
    try:
        oid = parse_oid(share_id)
    except Exception:
        return False
    doc = await db["question_shares"].find_one({"_id": oid, "grantor_id": grantor_id})
    if not doc:
        return False
    grantee_id = str(doc.get("grantee_id", ""))
    lineage_id = str(doc.get("lineage_id", ""))
    res = await db["question_shares"].delete_one({"_id": oid, "grantor_id": grantor_id})
    if res.deleted_count < 1:
        return False
    from app.services import question_bank_service

    await question_bank_service.remove_lineage_from_shared_inbox(
        db, grantee_id, lineage_id
    )
    return True
