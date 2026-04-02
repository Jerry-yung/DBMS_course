from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services import jump_engine, validation_service
from app.utils.mongo import oid_str, parse_oid


def _answers_list_to_dict(answers: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {a["question_id"]: a.get("value") for a in answers}


async def get_published_by_code(
    db: AsyncIOMotorDatabase, code: str
) -> Optional[Dict[str, Any]]:
    doc = await db["surveys"].find_one({"short_code": code, "status": "published"})
    if not doc:
        return None
    return doc


async def _serialize_public_question(db: AsyncIOMotorDatabase, qid: str) -> Optional[Dict[str, Any]]:
    try:
        oid = parse_oid(qid)
    except Exception:
        return None
    q = await db["questions"].find_one({"_id": oid})
    if not q:
        return None
    return {
        "id": oid_str(q["_id"]),
        "title": q.get("title", ""),
        "type": q.get("type", ""),
        "required": q.get("required", False),
        "options": q.get("options") or [],
        "validation": q.get("validation") or {},
    }


async def public_survey_payload(
    db: AsyncIOMotorDatabase, code: str
) -> Tuple[bool, str, Dict[str, Any]]:
    doc = await get_published_by_code(db, code)
    if not doc:
        return False, "问卷不存在或未发布", {}
    sid = oid_str(doc["_id"])
    order = doc.get("question_order") or []
    first = None
    if order:
        first = await _serialize_public_question(db, order[0])
    settings = doc.get("settings") or {}
    data = {
        "survey_id": sid,
        "title": doc.get("title", ""),
        "description": doc.get("description", ""),
        "short_code": doc.get("short_code", ""),
        "settings": {
            "allow_anonymous": settings.get("allow_anonymous", False),
            "allow_multiple": settings.get("allow_multiple", True),
            "thank_you_message": settings.get(
                "thank_you_message", "感谢您的参与！"
            ),
        },
        "question_order": order,
        "first_question": first,
    }
    return True, "ok", data


async def get_or_create_response(
    db: AsyncIOMotorDatabase,
    survey_id: str,
    session_id: str,
    user_id: Optional[str],
) -> Dict[str, Any]:
    coll = db["responses"]
    doc = await coll.find_one(
        {
            "survey_id": survey_id,
            "session_id": session_id,
            "status": "in_progress",
        }
    )
    if doc:
        if user_id and not doc.get("user_id"):
            await coll.update_one(
                {"_id": doc["_id"]}, {"$set": {"user_id": user_id}}
            )
            doc = await coll.find_one({"_id": doc["_id"]})
        return doc

    now = datetime.utcnow()
    new_doc = {
        "survey_id": survey_id,
        "user_id": user_id,
        "session_id": session_id,
        "answers": [],
        "status": "in_progress",
        "completed_at": None,
        "ip_address": None,
        "user_agent": None,
        "fill_duration": None,
        "created_at": now,
        "updated_at": now,
    }
    res = await coll.insert_one(new_doc)
    new_doc["_id"] = res.inserted_id
    return new_doc


async def compute_next(
    db: AsyncIOMotorDatabase,
    survey_id: str,
    session_id: str,
    user_id: Optional[str],
) -> Tuple[bool, str, Dict[str, Any]]:
    survey = await db["surveys"].find_one(
        {"_id": parse_oid(survey_id), "status": "published"}
    )
    if not survey:
        return False, "问卷不可用", {}

    order = survey.get("question_order") or []
    rules = await db["jump_rules"].find({"survey_id": survey_id}).to_list(length=500)
    rules = [r for r in rules]

    resp = await get_or_create_response(db, survey_id, session_id, user_id)
    answers = resp.get("answers") or []
    ad = _answers_list_to_dict(answers)
    last_qid: Optional[str] = answers[-1]["question_id"] if answers else None
    next_id = jump_engine.get_next_question(order, rules, last_qid, ad)
    next_q = await _serialize_public_question(db, next_id) if next_id else None
    data = {
        "response_id": oid_str(resp["_id"]),
        "next_question_id": next_id,
        "next_question": next_q,
        "is_done": next_id is None and bool(answers),
    }
    return True, "ok", data


async def save_answer(
    db: AsyncIOMotorDatabase,
    code: str,
    session_id: str,
    user_id: Optional[str],
    question_id: str,
    value: Any,
) -> Tuple[bool, str, Dict[str, Any]]:
    doc = await get_published_by_code(db, code)
    if not doc:
        return False, "问卷不存在或未发布", {}
    survey_id = oid_str(doc["_id"])

    try:
        q_oid = parse_oid(question_id)
    except Exception:
        return False, "题目无效", {}

    qdoc = await db["questions"].find_one({"_id": q_oid, "survey_id": survey_id})
    if not qdoc:
        return False, "题目无效", {}

    q_public = await _serialize_public_question(db, question_id)
    ok, err = validation_service.validate_answer(q_public or {}, value)
    if not ok:
        return False, err, {}

    resp = await get_or_create_response(db, survey_id, session_id, user_id)
    if resp.get("status") == "completed":
        return False, "问卷已提交", {}

    answers: List[Dict[str, Any]] = list(resp.get("answers") or [])
    replaced = False
    for i, a in enumerate(answers):
        if a.get("question_id") == question_id:
            answers[i] = {"question_id": question_id, "value": value}
            replaced = True
            break
    if not replaced:
        answers.append({"question_id": question_id, "value": value})

    now = datetime.utcnow()
    await db["responses"].update_one(
        {"_id": resp["_id"]},
        {"$set": {"answers": answers, "updated_at": now}},
    )

    order = doc.get("question_order") or []
    rules = await db["jump_rules"].find({"survey_id": survey_id}).to_list(length=500)
    ad = _answers_list_to_dict(answers)
    next_id = jump_engine.get_next_question(order, rules, question_id, ad)
    next_q = await _serialize_public_question(db, next_id) if next_id else None

    return True, "ok", {
        "response_id": oid_str(resp["_id"]),
        "next_question_id": next_id,
        "next_question": next_q,
        "is_done": next_id is None,
    }


async def submit_survey(
    db: AsyncIOMotorDatabase,
    code: str,
    session_id: str,
    user_id: Optional[str],
) -> Tuple[bool, str, Dict[str, Any]]:
    doc = await get_published_by_code(db, code)
    if not doc:
        return False, "问卷不存在或未发布", {}
    survey_id = oid_str(doc["_id"])
    settings = doc.get("settings") or {}
    allow_multiple = settings.get("allow_multiple", True)

    coll = db["responses"]
    flt_completed: Dict[str, Any] = {"survey_id": survey_id, "status": "completed"}
    if user_id:
        flt_completed["user_id"] = user_id
    elif session_id:
        flt_completed["session_id"] = session_id
    if not allow_multiple:
        if await coll.find_one(flt_completed):
            return False, "您已提交过该问卷", {}

    resp = await get_or_create_response(db, survey_id, session_id, user_id)
    if resp.get("status") == "completed":
        return False, "问卷已提交", {}

    answers: List[Dict[str, Any]] = list(resp.get("answers") or [])
    ad = _answers_list_to_dict(answers)

    cur = db["questions"].find({"survey_id": survey_id}).sort("order", 1)
    async for q in cur:
        qid = oid_str(q["_id"])
        q_public = await _serialize_public_question(db, qid)
        if not q_public:
            continue
        if q_public.get("required"):
            val = ad.get(qid)
            ok, err = validation_service.validate_answer(q_public, val)
            if not ok:
                return False, f"{q_public.get('title', qid)}: {err}", {}

    now = datetime.utcnow()
    try:
        await coll.update_one(
            {"_id": resp["_id"]},
            {
                "$set": {
                    "status": "completed",
                    "completed_at": now,
                    "updated_at": now,
                }
            },
        )
    except Exception as e:
        if "duplicate key" in str(e).lower() or "E11000" in str(e):
            return False, "您已提交过该问卷", {}
        raise

    await db["surveys"].update_one(
        {"_id": doc["_id"]}, {"$inc": {"total_responses": 1}}
    )

    msg = settings.get("thank_you_message", "感谢您的参与！")
    return True, "ok", {"thank_you_message": msg}
