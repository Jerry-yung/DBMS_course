from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

from app.services import library_question_service
from app.utils.mongo import doc_with_id, oid_str, parse_oid

# 系统预置「共享库」：每人一个，仅通过他人共享写入条目，不可删除、不可改名
SHARED_INBOX_TITLE = "共享库"
SHARED_INBOX_DESCRIPTION = "来自其他人的共享，本库不可删除"
PRESET_SHARED_INBOX = "shared_inbox"


def _normalize_bank_title(title: str) -> str:
    return str(title or "").strip()


def _serialize_bank(doc: Dict[str, Any]) -> Dict[str, Any]:
    d = doc_with_id(doc)
    d["owner_id"] = str(doc.get("owner_id", ""))
    pk = doc.get("preset_kind")
    d["preset_kind"] = pk if pk else None
    d["is_shared_inbox"] = pk == PRESET_SHARED_INBOX
    return d


def _is_shared_inbox_doc(doc: Optional[Dict[str, Any]]) -> bool:
    return bool(doc and doc.get("preset_kind") == PRESET_SHARED_INBOX)


async def _get_bank_doc(
    db: AsyncIOMotorDatabase, bank_id: str, owner_id: str
) -> Optional[Dict[str, Any]]:
    try:
        oid = parse_oid(bank_id)
    except Exception:
        return None
    return await db["question_banks"].find_one({"_id": oid, "owner_id": owner_id})


async def ensure_shared_inbox_bank(
    db: AsyncIOMotorDatabase, owner_id: str
) -> Dict[str, Any]:
    doc = await db["question_banks"].find_one(
        {"owner_id": owner_id, "preset_kind": PRESET_SHARED_INBOX}
    )
    if doc:
        return _serialize_bank(doc)
    legacy = await db["question_banks"].find_one(
        {"owner_id": owner_id, "title": SHARED_INBOX_TITLE}
    )
    now = datetime.utcnow()
    if legacy:
        await db["question_banks"].update_one(
            {"_id": legacy["_id"]},
            {
                "$set": {
                    "preset_kind": PRESET_SHARED_INBOX,
                    "description": SHARED_INBOX_DESCRIPTION,
                }
            },
        )
        fresh = await db["question_banks"].find_one({"_id": legacy["_id"]})
        return _serialize_bank(fresh or legacy)
    insert_doc = {
        "owner_id": owner_id,
        "title": SHARED_INBOX_TITLE,
        "description": SHARED_INBOX_DESCRIPTION,
        "preset_kind": PRESET_SHARED_INBOX,
        "created_at": now,
    }
    try:
        res = await db["question_banks"].insert_one(insert_doc)
    except DuplicateKeyError:
        doc = await db["question_banks"].find_one(
            {"owner_id": owner_id, "title": SHARED_INBOX_TITLE}
        )
        if doc:
            return _serialize_bank(doc)
        raise
    insert_doc["_id"] = res.inserted_id
    return _serialize_bank(insert_doc)


async def remove_lineage_from_shared_inbox(
    db: AsyncIOMotorDatabase, grantee_id: str, lineage_id: str
) -> None:
    doc = await db["question_banks"].find_one(
        {"owner_id": grantee_id, "preset_kind": PRESET_SHARED_INBOX}
    )
    if not doc:
        return
    bid = oid_str(doc["_id"])
    await db["question_bank_items"].delete_many(
        {"bank_id": bid, "lineage_id": str(lineage_id or "").strip()}
    )


async def _bank_title_exists(
    db: AsyncIOMotorDatabase, owner_id: str, title: str, exclude_id: Optional[str] = None
) -> bool:
    q: Dict[str, Any] = {"owner_id": owner_id, "title": title}
    if exclude_id:
        try:
            q["_id"] = {"$ne": parse_oid(exclude_id)}
        except Exception:
            pass
    doc = await db["question_banks"].find_one(q)
    return doc is not None


async def ensure_banks_owned(
    db: AsyncIOMotorDatabase, owner_id: str, bank_ids: List[str]
) -> Tuple[bool, str]:
    if not bank_ids:
        return False, "请至少选择一个题库"
    for bid in dict.fromkeys(bank_ids):
        if not bid or not str(bid).strip():
            return False, "题库 ID 无效"
        if not await get_bank(db, str(bid).strip(), owner_id):
            return False, "题库不存在或无权限"
    return True, "ok"


async def create_bank(
    db: AsyncIOMotorDatabase, owner_id: str, title: str, description: str
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    normalized = _normalize_bank_title(title)
    if not normalized:
        return False, "题库名称不能为空", None
    if normalized == SHARED_INBOX_TITLE:
        return False, "该名称为系统保留（共享库由系统自动创建）", None
    if await _bank_title_exists(db, owner_id, normalized):
        return False, "题库名称已存在", None
    now = datetime.utcnow()
    doc = {
        "owner_id": owner_id,
        "title": normalized,
        "description": (description or "").strip(),
        "created_at": now,
    }
    try:
        res = await db["question_banks"].insert_one(doc)
    except DuplicateKeyError:
        return False, "题库名称已存在", None
    doc["_id"] = res.inserted_id
    return True, "ok", _serialize_bank(doc)


async def list_banks(
    db: AsyncIOMotorDatabase, owner_id: str
) -> List[Dict[str, Any]]:
    await ensure_shared_inbox_bank(db, owner_id)
    await sync_shared_inbox_from_shares(db, owner_id)
    cur = db["question_banks"].find({"owner_id": owner_id})
    inbox_ser: Optional[Dict[str, Any]] = None
    rest: List[Dict[str, Any]] = []
    async for doc in cur:
        s = _serialize_bank(doc)
        if s.get("is_shared_inbox"):
            inbox_ser = s
        else:
            rest.append(s)
    rest.sort(
        key=lambda x: x.get("created_at") or datetime.min,
        reverse=True,
    )
    return ([inbox_ser] if inbox_ser else []) + rest


async def get_bank(
    db: AsyncIOMotorDatabase, bank_id: str, owner_id: str
) -> Optional[Dict[str, Any]]:
    try:
        oid = parse_oid(bank_id)
    except Exception:
        return None
    doc = await db["question_banks"].find_one({"_id": oid, "owner_id": owner_id})
    if not doc:
        return None
    return _serialize_bank(doc)


async def update_bank(
    db: AsyncIOMotorDatabase,
    bank_id: str,
    owner_id: str,
    patch: Dict[str, Any],
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    doc = await get_bank(db, bank_id, owner_id)
    if not doc:
        return False, "题库不存在", None
    if doc.get("is_shared_inbox"):
        if patch.get("title") is not None or patch.get("description") is not None:
            return False, "共享库不可修改名称或描述", None
    allowed: Dict[str, Any] = {}
    if patch.get("title") is not None:
        new_title = _normalize_bank_title(patch["title"])
        if not new_title:
            return False, "题库名称不能为空", None
        if await _bank_title_exists(db, owner_id, new_title, exclude_id=bank_id):
            return False, "题库名称已存在", None
        allowed["title"] = new_title
    if patch.get("description") is not None:
        allowed["description"] = str(patch["description"] or "").strip()
    if not allowed:
        return True, "ok", doc
    oid = parse_oid(bank_id)
    try:
        await db["question_banks"].update_one({"_id": oid}, {"$set": allowed})
    except DuplicateKeyError:
        return False, "题库名称已存在", None
    fresh = await db["question_banks"].find_one({"_id": oid})
    return True, "ok", _serialize_bank(fresh)


async def delete_bank(
    db: AsyncIOMotorDatabase, bank_id: str, owner_id: str
) -> Tuple[bool, Optional[str]]:
    raw = await _get_bank_doc(db, bank_id, owner_id)
    if not raw:
        return False, None
    if _is_shared_inbox_doc(raw):
        return False, "共享库不可删除"
    oid = raw["_id"]
    await db["question_bank_items"].delete_many({"bank_id": bank_id})
    await db["question_banks"].delete_one({"_id": oid})
    return True, None


async def add_bank_item(
    db: AsyncIOMotorDatabase,
    bank_id: str,
    owner_id: str,
    library_question_id: str,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    bdoc = await _get_bank_doc(db, bank_id, owner_id)
    if not bdoc:
        return False, "题库不存在", None
    if _is_shared_inbox_doc(bdoc):
        return False, "共享库仅通过他人共享自动加入题目", None
    lib = await library_question_service.get_library_question(
        db, library_question_id, owner_id
    )
    if not lib:
        return False, "库题不存在或无权访问", None
    lineage_id = str(lib.get("lineage_id") or "").strip()
    if not lineage_id:
        return False, "库题 lineage_id 异常", None
    existed = await db["question_bank_items"].find_one(
        {"bank_id": bank_id, "lineage_id": lineage_id}
    )
    if existed:
        return False, "该题目已在题库中", None
    now = datetime.utcnow()
    doc = {
        "bank_id": bank_id,
        "lineage_id": lineage_id,
        "added_at": now,
    }
    try:
        res = await db["question_bank_items"].insert_one(doc)
    except DuplicateKeyError:
        return False, "该题目已在题库中", None
    doc["_id"] = res.inserted_id
    return True, "ok", {
        "id": oid_str(doc["_id"]),
        "bank_id": bank_id,
        "lineage_id": lineage_id,
        "added_at": now,
    }


async def add_bank_item_by_lineage(
    db: AsyncIOMotorDatabase,
    bank_id: str,
    owner_id: str,
    lineage_id: str,
    *,
    allow_shared_inbox: bool = False,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    lineage_id = str(lineage_id or "").strip()
    if not lineage_id:
        return False, "lineage_id 无效", None
    bdoc = await _get_bank_doc(db, bank_id, owner_id)
    if not bdoc:
        return False, "题库不存在", None
    if _is_shared_inbox_doc(bdoc) and not allow_shared_inbox:
        return False, "共享库仅通过他人共享自动加入题目", None
    latest = await library_question_service.get_latest_visible_library_by_lineage(
        db, owner_id, lineage_id
    )
    if not latest:
        return False, "库题不存在或无权访问", None
    existed = await db["question_bank_items"].find_one(
        {"bank_id": bank_id, "lineage_id": lineage_id}
    )
    if existed:
        return True, "ok", None
    now = datetime.utcnow()
    doc = {
        "bank_id": bank_id,
        "lineage_id": lineage_id,
        "added_at": now,
    }
    try:
        res = await db["question_bank_items"].insert_one(doc)
    except DuplicateKeyError:
        return True, "ok", None
    doc["_id"] = res.inserted_id
    return True, "ok", {
        "id": oid_str(doc["_id"]),
        "bank_id": bank_id,
        "lineage_id": lineage_id,
        "added_at": now,
    }


async def sync_shared_inbox_from_shares(
    db: AsyncIOMotorDatabase, grantee_id: str
) -> None:
    inbox = await ensure_shared_inbox_bank(db, grantee_id)
    bid = inbox["id"]
    cur = db["question_shares"].find({"grantee_id": grantee_id})
    async for row in cur:
        lid = str(row.get("lineage_id") or "").strip()
        if not lid:
            continue
        await add_bank_item_by_lineage(
            db, bid, grantee_id, lid, allow_shared_inbox=True
        )


async def attach_library_question_to_banks(
    db: AsyncIOMotorDatabase,
    owner_id: str,
    library_question_id: str,
    bank_ids: List[str],
) -> Tuple[bool, str]:
    uniq = [str(b).strip() for b in dict.fromkeys(bank_ids) if str(b).strip()]
    if not uniq:
        return False, "请至少选择一个题库"
    ok_own, msg_own = await ensure_banks_owned(db, owner_id, uniq)
    if not ok_own:
        return False, msg_own
    added_banks: List[str] = []
    for bid in uniq:
        ok, msg, _ = await add_bank_item(db, bid, owner_id, library_question_id)
        if ok:
            added_banks.append(bid)
            continue
        if msg == "该题目已在题库中":
            continue
        for b in added_banks:
            await remove_bank_item(db, b, owner_id, library_question_id)
        return False, msg
    return True, "ok"


async def remove_bank_item(
    db: AsyncIOMotorDatabase,
    bank_id: str,
    owner_id: str,
    library_question_or_lineage_id: str,
) -> bool:
    if not await get_bank(db, bank_id, owner_id):
        return False
    lid = str(library_question_or_lineage_id or "").strip()
    if not lid:
        return False
    # 兼容传入 library_question_id（旧调用）或 lineage_id（新调用）
    try:
        lib = await library_question_service.get_library_question(db, lid, owner_id)
        if lib and lib.get("lineage_id"):
            lid = str(lib["lineage_id"])
    except Exception:
        pass
    res = await db["question_bank_items"].delete_many({"bank_id": bank_id, "lineage_id": lid})
    return res.deleted_count > 0


async def list_bank_items(
    db: AsyncIOMotorDatabase, bank_id: str, owner_id: str
) -> Optional[List[Dict[str, Any]]]:
    if not await get_bank(db, bank_id, owner_id):
        return None
    cur = db["question_bank_items"].find({"bank_id": bank_id}).sort("added_at", -1)
    out = []
    async for row in cur:
        lineage_id = str(row.get("lineage_id", ""))
        display_id = str(row.get("display_library_question_id") or "").strip()
        shown = None
        if display_id:
            shown = await library_question_service.get_library_question(
                db, display_id, owner_id
            )
            if shown and str(shown.get("lineage_id", "")) != lineage_id:
                shown = None
        if not shown:
            shown = await library_question_service.get_latest_visible_library_by_lineage(
                db, owner_id, lineage_id
            )
        out.append(
            {
                "id": oid_str(row["_id"]),
                "bank_id": bank_id,
                "lineage_id": lineage_id,
                "added_at": row.get("added_at"),
                "display_library_question_id": display_id or None,
                "library_question_id": (shown or {}).get("id", ""),
                "library_question": shown,
            }
        )
    return out


async def set_bank_item_display_version(
    db: AsyncIOMotorDatabase,
    bank_id: str,
    owner_id: str,
    lineage_id: str,
    library_question_id: Optional[str],
) -> Tuple[bool, str]:
    if not await get_bank(db, bank_id, owner_id):
        return False, "题库不存在"
    lid = str(lineage_id or "").strip()
    item = await db["question_bank_items"].find_one(
        {"bank_id": bank_id, "lineage_id": lid}
    )
    if not item:
        return False, "该题目不在此题库中"
    if not library_question_id or not str(library_question_id).strip():
        await db["question_bank_items"].update_one(
            {"_id": item["_id"]},
            {"$unset": {"display_library_question_id": ""}},
        )
        return True, "ok"
    lqid = str(library_question_id).strip()
    lib = await library_question_service.get_library_question(db, lqid, owner_id)
    if not lib or str(lib.get("lineage_id", "")) != lid:
        return False, "版本不存在或不在该题目家族内"
    await db["question_bank_items"].update_one(
        {"_id": item["_id"]},
        {"$set": {"display_library_question_id": lqid}},
    )
    return True, "ok"


async def unset_display_for_lineage_in_banks(
    db: AsyncIOMotorDatabase, bank_ids: List[str], lineage_id: str
) -> None:
    lid = str(lineage_id or "").strip()
    if not lid or not bank_ids:
        return
    bids = [str(b).strip() for b in bank_ids if str(b).strip()]
    if not bids:
        return
    await db["question_bank_items"].update_many(
        {"bank_id": {"$in": bids}, "lineage_id": lid},
        {"$unset": {"display_library_question_id": ""}},
    )
