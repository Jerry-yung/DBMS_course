from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services import survey_service
from app.utils.mongo import oid_str, parse_oid


async def _load_questions(db: AsyncIOMotorDatabase, survey_id: str) -> List[Dict[str, Any]]:
    cur = db["questions"].find({"survey_id": survey_id}).sort("order", 1)
    out = []
    async for q in cur:
        q["id"] = oid_str(q["_id"])
        out.append(q)
    return out


async def full_statistics(
    db: AsyncIOMotorDatabase, survey_id: str, creator_id: str
) -> Optional[Dict[str, Any]]:
    survey = await survey_service.get_survey(db, survey_id, creator_id)
    if not survey:
        return None
    questions = await _load_questions(db, survey_id)
    qstats = []
    for q in questions:
        block = await _per_question_stats(db, survey_id, q)
        qstats.append(block)
    return {
        "survey_id": survey_id,
        "total_responses": survey.get("total_responses", 0),
        "questions": qstats,
    }


async def single_question_stats(
    db: AsyncIOMotorDatabase, survey_id: str, qid: str, creator_id: str
) -> Optional[Dict[str, Any]]:
    survey = await survey_service.get_survey(db, survey_id, creator_id)
    if not survey:
        return None
    try:
        oid = parse_oid(qid)
    except Exception:
        return None
    q = await db["questions"].find_one({"_id": oid, "survey_id": survey_id})
    if not q:
        return None
    q["id"] = oid_str(q["_id"])
    return await _per_question_stats(db, survey_id, q)


async def _per_question_stats(
    db: AsyncIOMotorDatabase, survey_id: str, q: Dict[str, Any]
) -> Dict[str, Any]:
    qid = q["id"]
    qtype = q.get("type", "")
    pipeline = [
        {"$match": {"survey_id": survey_id, "status": "completed"}},
        {"$unwind": "$answers"},
        {"$match": {"answers.question_id": qid}},
    ]
    stats: Dict[str, Any] = {}

    if qtype == "single_choice":
        pipeline.append({"$group": {"_id": "$answers.value", "count": {"$sum": 1}}})
        cur = db["responses"].aggregate(pipeline)
        counts: Dict[str, int] = {}
        async for row in cur:
            key = str(row["_id"]) if row["_id"] is not None else ""
            counts[key] = int(row["count"])
        stats = counts

    elif qtype == "multiple_choice":
        pipeline.append({"$unwind": "$answers.value"})
        pipeline.append({"$group": {"_id": "$answers.value", "count": {"$sum": 1}}})
        cur = db["responses"].aggregate(pipeline)
        counts = {}
        async for row in cur:
            key = str(row["_id"]) if row["_id"] is not None else ""
            counts[key] = int(row["count"])
        stats = counts

    elif qtype == "text":
        pipeline.append({"$project": {"v": "$answers.value"}})
        cur = db["responses"].aggregate(pipeline)
        texts = []
        async for row in cur:
            texts.append(row.get("v"))
        stats = {"values": texts}

    elif qtype == "number":
        pipeline.append(
            {
                "$group": {
                    "_id": None,
                    "count": {"$sum": 1},
                    "avg": {"$avg": "$answers.value"},
                    "min": {"$min": "$answers.value"},
                    "max": {"$max": "$answers.value"},
                    "values": {"$push": "$answers.value"},
                }
            }
        )
        cur = db["responses"].aggregate(pipeline)
        async for row in cur:
            stats = {
                "count": int(row.get("count") or 0),
                "avg": float(row["avg"]) if row.get("avg") is not None else None,
                "min": row.get("min"),
                "max": row.get("max"),
                "values": row.get("values") or [],
            }
            break
        if not stats:
            stats = {"count": 0, "avg": None, "min": None, "max": None, "values": []}
    else:
        stats = {}

    return {
        "question_id": qid,
        "title": q.get("title", ""),
        "type": qtype,
        "options": q.get("options") or [],
        "statistics": stats,
    }


def export_json_payload(data: Dict[str, Any]) -> str:
    import json

    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


def _question_type_cn(qtype: str) -> str:
    return {
        "single_choice": "单选题",
        "multiple_choice": "多选题",
        "text": "文本题",
        "number": "数字题",
    }.get(qtype, qtype or "其它")


def _option_label_for_value(options: List[Dict[str, Any]], value: Any) -> str:
    sv = str(value) if value is not None else ""
    for opt in options:
        if str(opt.get("value", "")) == sv:
            lab = opt.get("label")
            if lab is not None and str(lab).strip() != "":
                return str(lab)
            return f"选项 {sv}" if sv else "（空选项）"
    return f"选项 {sv}" if sv else "（未归类）"


def _join_cell_values(values: List[Any]) -> str:
    parts = [str(x) for x in values if x is not None]
    return ";".join(parts)


def export_csv(data: Dict[str, Any]) -> str:
    import csv
    import io

    buf = io.StringIO()
    buf.write("\ufeff")
    w = csv.writer(buf)
    w.writerow(["题目", "题型", "统计项", "统计值"])
    total_resp = data.get("total_responses")
    if total_resp is None:
        total_resp = 0
    w.writerow(
        [
            "（整卷汇总）",
            "—",
            "总人数（total_responses）",
            int(total_resp),
        ]
    )

    for q in data.get("questions", []):
        title = q.get("title", "")
        qt_raw = q.get("type", "")
        type_label = _question_type_cn(qt_raw)
        options = q.get("options") or []
        st = q.get("statistics") or {}
        if not isinstance(st, dict):
            continue

        if qt_raw in ("single_choice", "multiple_choice"):
            keys = [k for k in st.keys() if k != "values"]
            if not keys:
                w.writerow([title, type_label, "（暂无数据）", ""])
            else:
                for k in sorted(keys, key=str):
                    label = _option_label_for_value(options, k)
                    w.writerow([title, type_label, label, st[k]])
        elif qt_raw == "text":
            vals = st.get("values") if isinstance(st.get("values"), list) else []
            w.writerow([title, type_label, "全部文本答案", _join_cell_values(vals)])
        elif qt_raw == "number":
            count = int(st.get("count") or 0)
            avg = st.get("avg")
            min_v = st.get("min")
            max_v = st.get("max")
            vals = st.get("values") if isinstance(st.get("values"), list) else []
            w.writerow([title, type_label, "作答人数", count])
            w.writerow(
                [
                    title,
                    type_label,
                    "平均值",
                    "" if avg is None else avg,
                ]
            )
            w.writerow(
                [
                    title,
                    type_label,
                    "最小值",
                    "" if min_v is None else min_v,
                ]
            )
            w.writerow(
                [
                    title,
                    type_label,
                    "最大值",
                    "" if max_v is None else max_v,
                ]
            )
            w.writerow([title, type_label, "全部数值", _join_cell_values(vals)])
        else:
            if not st:
                w.writerow([title, type_label, "（暂无数据）", ""])
            else:
                for k, v in st.items():
                    if k == "values" and isinstance(v, list):
                        w.writerow([title, type_label, "汇总", _join_cell_values(v)])
                    else:
                        w.writerow([title, type_label, str(k), v])

    return buf.getvalue()
