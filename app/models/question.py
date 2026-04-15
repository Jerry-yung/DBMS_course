from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field
from bson import ObjectId
from enum import Enum

class QuestionType(str, Enum):
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"
    TEXT = "text"
    NUMBER = "number"

class Option(BaseModel):
    """选项"""
    value: str
    label: str
    order: int

class ValidationRules(BaseModel):
    """校验规则"""
    # 多选题专用
    min_select: Optional[int] = None
    max_select: Optional[int] = None
    exact_select: Optional[int] = None
    # 文本题专用
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    # 数字题专用
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    integer_only: bool = False
    # 通用
    pattern: Optional[str] = None

class Question(BaseModel):
    """questions 集合 - 题目模型"""
    id: Optional[str] = Field(None, alias="_id")
    survey_id: str
    title: str
    type: QuestionType
    required: bool = False
    order: int
    options: List[Option] = []
    validation: ValidationRules = Field(default_factory=ValidationRules)
    has_jump_rules: bool = False
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}