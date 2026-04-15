from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.question import OptionIn, ValidationIn


class LibraryQuestionCreate(BaseModel):
    title: str
    type: str
    required: bool = False
    options: List[OptionIn] = []
    validation: Optional[ValidationIn] = None
    bank_ids: List[str] = Field(..., min_items=1)


class LibraryQuestionNewVersion(BaseModel):
    title: str
    type: str
    required: bool = False
    options: List[OptionIn] = []
    validation: Optional[ValidationIn] = None
    bank_ids: List[str] = Field(..., min_items=1)


class LibraryQuestionUpdateBody(BaseModel):
    """原地更新当前库题版本（不新建 lineage 节点）。"""

    title: str
    type: str
    required: bool = False
    options: List[OptionIn] = []
    validation: Optional[ValidationIn] = None


class ShareLineageBody(BaseModel):
    grantee_username: str = Field(..., min_length=1)
    lineage_id: str = Field(..., min_length=1)


class QuestionBankCreate(BaseModel):
    title: str = Field(..., min_length=1)
    description: str = ""


class QuestionBankUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None


class BankItemAdd(BaseModel):
    library_question_id: str = Field(..., min_length=1)


class AddQuestionFromLibraryBody(BaseModel):
    library_question_id: str = Field(..., min_length=1)


class PromoteSurveyQuestionBody(BaseModel):
    survey_id: str = Field(..., min_length=1)
    question_id: str = Field(..., min_length=1)
    bank_ids: List[str] = Field(..., min_items=1)


class BankItemDisplayVersionBody(BaseModel):
    """钉选本题库详情中展示的版本；library_question_id 为空则跟随最新版。"""

    lineage_id: str = Field(..., min_length=1)
    library_question_id: Optional[str] = None


class ApplyLibraryVersionBody(BaseModel):
    library_question_id: str = Field(..., min_length=1)
