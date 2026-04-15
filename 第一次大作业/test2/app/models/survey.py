from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from bson import ObjectId

class SurveySettings(BaseModel):
    """问卷设置"""
    allow_anonymous: bool = False
    allow_multiple: bool = True
    deadline: Optional[datetime] = None
    thank_you_message: str = "感谢您的参与！"

class Survey(BaseModel):
    """surveys 集合 - 问卷模型"""
    id: Optional[str] = Field(None, alias="_id")
    title: str = Field(..., max_length=200)
    description: str = ""
    creator_id: str
    short_code: str
    status: str = "draft"  # draft | published | closed
    settings: SurveySettings = Field(default_factory=SurveySettings)
    question_order: List[str] = []
    total_responses: int = 0
    created_at: datetime = Field(default_factory=datetime.now)
    published_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    
    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}