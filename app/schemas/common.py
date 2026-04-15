from typing import Any, Dict, Optional


def success(data: Optional[Any] = None, message: str = "success") -> Dict[str, Any]:
    return {"code": 200, "message": message, "data": data if data is not None else {}}
