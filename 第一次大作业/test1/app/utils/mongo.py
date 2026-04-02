from typing import Any, Dict

from bson import ObjectId


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
