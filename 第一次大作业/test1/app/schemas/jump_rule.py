from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class JumpRuleCreate(BaseModel):
    source_question_id: str
    target_question_id: str
    condition: Dict[str, Any]
    priority: int = 0
    enabled: bool = True


class JumpRuleUpdate(BaseModel):
    source_question_id: Optional[str] = None
    target_question_id: Optional[str] = None
    condition: Optional[Dict[str, Any]] = None
    priority: Optional[int] = None
    enabled: Optional[bool] = None
