from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field
from bson import ObjectId

class Answer(BaseModel):
    """单题答案"""
    question_id: str
    value: Any  # 字符串、列表、数字等

class Response(BaseModel):
    """responses 集合 - 填写记录模型"""
    id: Optional[str] = Field(None, alias="_id")
    survey_id: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    answers: List[Answer] = []
    status: str = "in_progress"  # in_progress | completed
    completed_at: Optional[datetime] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    fill_duration: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}