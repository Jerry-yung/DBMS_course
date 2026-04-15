from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SurveySettingsIn(BaseModel):
    allow_anonymous: bool = False
    allow_multiple: bool = True
    deadline: Optional[datetime] = None
    thank_you_message: str = "感谢您的参与！"


class SurveyCreate(BaseModel):
    title: str = Field(..., max_length=200)
    description: str = ""
    settings: Optional[SurveySettingsIn] = None


class SurveyUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    settings: Optional[SurveySettingsIn] = None
