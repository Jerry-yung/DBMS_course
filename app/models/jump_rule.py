from datetime import datetime
from typing import Optional, Any, Dict, List
from pydantic import BaseModel, Field
from bson import ObjectId
from enum import Enum

class ConditionType(str, Enum):
    OPTION_MATCH = "option_match"
    OPTION_CONTAINS = "option_contains"
    VALUE_EQUAL = "value_equal"
    VALUE_GREATER = "value_greater"
    VALUE_LESS = "value_less"
    VALUE_BETWEEN = "value_between"

class Condition(BaseModel):
    """跳转条件"""
    type: ConditionType
    params: Dict[str, Any]
    operator: Optional[str] = None  # AND | OR，用于多条件组合
    conditions: Optional[List['Condition']] = None  # 嵌套条件

class JumpRule(BaseModel):
    """jump_rules 集合 - 跳转规则模型"""
    id: Optional[str] = Field(None, alias="_id")
    survey_id: str
    source_question_id: str
    target_question_id: str
    condition: Condition
    priority: int = 0
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}