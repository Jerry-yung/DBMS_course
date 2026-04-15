import statistics
from typing import Any, Dict, List, Optional, Set

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services import library_question_service, survey_service
from app.utils.mongo import id_match_variants, oid_str, parse_oid


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


def _value_display_for_lineage(
    qtype: str, val: Any, options: List[Dict[str, Any]]
) -> str:
    if qtype == "single_choice":
        return _option_label_for_value(options, val)
    if qtype == "multiple_choice":
        vals = val if isinstance(val, list) else ([] if val is None else [val])
        return ";".join(_option_label_for_value(options, v) for v in vals)
    if val is None:
        return ""
    return str(val)


def _option_summary_from_stats(
    stats: Dict[str, Any], options: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    if not isinstance(stats, dict):
        return []
    total = sum(int(v) for v in stats.values() if isinstance(v, (int, float)))
    rows: List[Dict[str, Any]] = []
    for k in sorted(stats.keys(), key=str):
        cnt = int(stats[k]) if isinstance(stats[k], (int, float)) else 0
        rows.append(
            {
                "value": k,
                "label": _option_label_for_value(options, k),
                "count": cnt,
                "proportion": (cnt / total) if total else 0.0,
            }
        )
    return rows


def _numeric_summary_from_stats(stats: Dict[str, Any]) -> Dict[str, Any]:
    vals = stats.get("values") or []
    nums: List[float] = []
    for v in vals:
        if isinstance(v, bool):
            continue
        if isinstance(v, (int, float)):
            nums.append(float(v))
    n = len(nums)
    med = statistics.median(nums) if nums else None
    if n > 1:
        sd: Optional[float] = statistics.stdev(nums)
    elif n == 1:
        sd = 0.0
    else:
        sd = None
    return {
        "count": int(stats.get("count") or 0),
        "avg": stats.get("avg"),
        "min": stats.get("min"),
        "max": stats.get("max"),
        "median": med,
        "std": sd,
    }


async def _survey_title_map(
    db: AsyncIOMotorDatabase, survey_ids: Set[str]
) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for sid in survey_ids:
        if not sid:
            continue
        try:
            oid = parse_oid(sid)
        except Exception:
            continue
        doc = await db["surveys"].find_one({"_id": oid})
        out[sid] = str(doc.get("title", "") or "") if doc else ""
    return out


async def _respondent_answers_lineage(
    db: AsyncIOMotorDatabase,
    survey_set: Set[str],
    qid_set: Set[str],
    qtype: str,
    options: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    if not survey_set or not qid_set:
        return []
    titles = await _survey_title_map(db, survey_set)
    out: List[Dict[str, Any]] = []
    survey_match = id_match_variants(list(survey_set))
    cur = db["responses"].find(
        {"survey_id": {"$in": survey_match}, "status": "completed"}
    )
    async for doc in cur:
        rid = oid_str(doc["_id"])
        sid = oid_str(doc.get("survey_id", ""))
        for ans in doc.get("answers") or []:
            qid = oid_str(ans.get("question_id", ""))
            if not qid or qid not in qid_set:
                continue
            val = ans.get("value")
            out.append(
                {
                    "response_id": rid,
                    "survey_id": sid,
                    "survey_title": titles.get(sid, ""),
                    "user_id": doc.get("user_id"),
                    "session_id": str(doc.get("session_id") or ""),
                    "question_id": qid,
                    "value": val,
                    "value_display": _value_display_for_lineage(qtype, val, options),
                }
            )
    return out


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
    survey_variants = id_match_variants([survey_id])
    qid_variants = id_match_variants([qid])
    pipeline = [
        {"$match": {"survey_id": {"$in": survey_variants}, "status": "completed"}},
        {"$unwind": "$answers"},
        {"$match": {"answers.question_id": {"$in": qid_variants}}},
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


async def cross_survey_lineage_statistics(
    db: AsyncIOMotorDatabase, lineage_id: str, user_id: str
) -> Optional[Dict[str, Any]]:
    if not await library_question_service.can_view_lineage(db, user_id, lineage_id):
        return None

    sur_cur = db["surveys"].find({"creator_id": user_id})
    survey_ids: List[str] = []
    async for s in sur_cur:
        survey_ids.append(oid_str(s["_id"]))

    qcur = db["questions"].find(
        {"lineage_id": lineage_id, "survey_id": {"$in": survey_ids}}
    )
    instances: List[Dict[str, Any]] = []
    qtypes: Set[str] = set()
    async for q in qcur:
        instances.append(q)
        qtypes.add(str(q.get("type", "") or ""))

    if not instances:
        return {
            "lineage_id": lineage_id,
            "question_type": None,
            "title": "",
            "options": [],
            "survey_count": 0,
            "question_instances": 0,
            "statistics": {},
            "option_summary": [],
            "numeric_summary": None,
            "respondent_answers": [],
            "note": "当前账户下无问卷使用该题目家族",
        }

    if len(qtypes) > 1:
        return {
            "lineage_id": lineage_id,
            "error": "mixed_question_types",
            "types": sorted(qtypes),
            "message": "该家族在您名下的问卷中存在多种题型，无法合并统计",
            "option_summary": [],
            "numeric_summary": None,
            "respondent_answers": [],
        }

    qtype = next(iter(qtypes))
    qids = [oid_str(q["_id"]) for q in instances]

    lib = await db["library_questions"].find_one(
        {"lineage_id": lineage_id}, sort=[("created_at", 1)]
    )
    title = ""
    options: List[Dict[str, Any]] = []
    if lib:
        title = str(lib.get("title", "") or "")
        options = lib.get("options") or []
    if not title and instances:
        title = str(instances[0].get("title", "") or "")

    survey_set = {oid_str(q.get("survey_id", "")) for q in instances if q.get("survey_id")}

    survey_id_match = id_match_variants(survey_ids)
    qid_match = id_match_variants(qids)

    base_match: List[Dict[str, Any]] = [
        {"$match": {"survey_id": {"$in": survey_id_match}, "status": "completed"}},
        {"$unwind": "$answers"},
        {"$match": {"answers.question_id": {"$in": qid_match}}},
    ]

    stats: Dict[str, Any] = {}
    if qtype == "single_choice":
        pipeline = base_match + [
            {"$group": {"_id": "$answers.value", "count": {"$sum": 1}}}
        ]
        cur = db["responses"].aggregate(pipeline)
        counts: Dict[str, int] = {}
        async for row in cur:
            key = str(row["_id"]) if row["_id"] is not None else ""
            counts[key] = int(row["count"])
        stats = counts
    elif qtype == "multiple_choice":
        pipeline = base_match + [
            {"$unwind": "$answers.value"},
            {"$group": {"_id": "$answers.value", "count": {"$sum": 1}}},
        ]
        cur = db["responses"].aggregate(pipeline)
        counts = {}
        async for row in cur:
            key = str(row["_id"]) if row["_id"] is not None else ""
            counts[key] = int(row["count"])
        stats = counts
    elif qtype == "text":
        pipeline = base_match + [{"$project": {"v": "$answers.value"}}]
        cur = db["responses"].aggregate(pipeline)
        texts = []
        async for row in cur:
            texts.append(row.get("v"))
        stats = {"values": texts}
    elif qtype == "number":
        pipeline = base_match + [
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
        ]
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

    qid_set = set(qids)
    respondent_answers = await _respondent_answers_lineage(
        db, survey_set, qid_set, qtype, options
    )
    option_summary: List[Dict[str, Any]] = []
    numeric_summary: Optional[Dict[str, Any]] = None
    if qtype in ("single_choice", "multiple_choice"):
        option_summary = _option_summary_from_stats(stats, options)
    elif qtype == "number":
        numeric_summary = _numeric_summary_from_stats(stats)

    return {
        "lineage_id": lineage_id,
        "question_type": qtype,
        "title": title,
        "options": options,
        "survey_count": len(survey_set),
        "question_instances": len(qids),
        "statistics": stats,
        "option_summary": option_summary,
        "numeric_summary": numeric_summary,
        "respondent_answers": respondent_answers,
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
