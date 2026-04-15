from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from app.core.deps import get_db, get_optional_user
from app.schemas.common import success
from app.services import fill_service

router = APIRouter(prefix="/public/surveys", tags=["public"])


class SessionBody(BaseModel):
    session_id: str = Field(..., min_length=8)


class AnswerBody(SessionBody):
    question_id: str
    value: Any = None


class AnyBody(SessionBody):
    pass


@router.get("/{code}")
async def get_public_survey(
    code: str, db: AsyncIOMotorDatabase = Depends(get_db)
):
    ok, msg, data = await fill_service.public_survey_payload(db, code)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "message": msg, "data": {}},
        )
    return success(data)


@router.get("/{code}/next")
async def get_next_question(
    code: str,
    session_id: str = Query(..., min_length=8),
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: Optional[Dict[str, Any]] = Depends(get_optional_user),
):
    doc = await fill_service.get_published_by_code(db, code)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "message": "问卷不存在或未发布", "data": {}},
        )
    survey_id = str(doc["_id"])
    uid = user["id"] if user else None
    ok, msg, data = await fill_service.compute_next(db, survey_id, session_id, uid)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 400, "message": msg, "data": {}},
        )
    return success(data)


@router.post("/{code}/answer")
async def post_answer(
    code: str,
    body: AnswerBody,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: Optional[Dict[str, Any]] = Depends(get_optional_user),
):
    uid = user["id"] if user else None
    ok, msg, data = await fill_service.save_answer(
        db, code, body.session_id, uid, body.question_id, body.value
    )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 400, "message": msg, "data": {}},
        )
    return success(data)


@router.post("/{code}/submit")
async def submit_survey(
    code: str,
    body: SessionBody,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: Optional[Dict[str, Any]] = Depends(get_optional_user),
):
    uid = user["id"] if user else None
    ok, msg, data = await fill_service.submit_survey(
        db, code, body.session_id, uid
    )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 400, "message": msg, "data": {}},
        )
    return success(data)
