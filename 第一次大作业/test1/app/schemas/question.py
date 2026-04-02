from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class OptionIn(BaseModel):
    value: str
    label: str
    order: Optional[int] = None


class ValidationIn(BaseModel):
    min_select: Optional[int] = None
    max_select: Optional[int] = None
    exact_select: Optional[int] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    integer_only: bool = False
    pattern: Optional[str] = None


class QuestionCreate(BaseModel):
    title: str
    type: str
    required: bool = False
    options: List[OptionIn] = []
    validation: Optional[ValidationIn] = None


class QuestionUpdate(BaseModel):
    title: Optional[str] = None
    type: Optional[str] = None
    required: Optional[bool] = None
    options: Optional[List[OptionIn]] = None
    validation: Optional[ValidationIn] = None


class QuestionReorder(BaseModel):
    question_ids: List[str] = Field(..., min_items=1)
