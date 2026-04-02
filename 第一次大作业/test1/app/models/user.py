from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from bson import ObjectId

class User(BaseModel):
    """users 集合 - 用户模型"""
    id: Optional[str] = Field(None, alias="_id")
    username: str = Field(..., min_length=3, max_length=50)
    password: str  # bcrypt 加密后的密码
    email: Optional[str] = None
    role: str = "user"  # user | admin
    status: str = "active"  # active | disabled
    created_at: datetime = Field(default_factory=datetime.now)
    last_login: Optional[datetime] = None
    
    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}