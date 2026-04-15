from typing import Any, Dict, List

from bson import ObjectId


def id_match_variants(ids: List[str]) -> List[Any]:
    """用于查询/聚合：字段可能存为 24 位十六进制字符串或 ObjectId，需同时匹配。"""
    out: List[Any] = []
    for raw in ids:
        s = str(raw).strip() if raw is not None else ""
        if not s:
            continue
        out.append(s)
        try:
            out.append(ObjectId(s))
        except Exception:
            pass
    return out


def oid_str(oid: Any) -> str:
    if oid is None:
        return ""
    if isinstance(oid, ObjectId):
        return str(oid)
    return str(oid)


def parse_oid(s: str) -> ObjectId:
    return ObjectId(s)


def doc_with_id(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return doc
    out = dict(doc)
    out["id"] = oid_str(out.pop("_id", None))
    return out
