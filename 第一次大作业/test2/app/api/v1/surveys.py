from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.deps import get_current_user, get_db
from app.schemas.common import success
from app.schemas.library import AddQuestionFromLibraryBody, ApplyLibraryVersionBody
from app.schemas.question import QuestionCreate, QuestionReorder, QuestionUpdate
from app.schemas.survey import SurveyCreate, SurveyUpdate
from app.services import question_service, survey_service

router = APIRouter()


def _creator_id(user: Dict[str, Any]) -> str:
    return user["id"]


@router.post("")
async def create_survey(
    body: SurveyCreate,
    user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    settings = survey_service._default_settings()
    if body.settings is not None:
        settings.update(body.settings.dict(exclude_unset=True))
    data = await survey_service.create_survey(
        db, _creator_id(user), body.title, body.description, settings
    )
    return success(data)


@router.get("")
async def list_surveys(
    user=Depends(get_current_user), db: AsyncIOMotorDatabase = Depends(get_db)
):
    data = await survey_service.list_surveys(db, _creator_id(user))
    return success(data)


@router.get("/{survey_id}")
async def get_survey_detail(
    survey_id: str,
    user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    doc = await survey_service.get_survey(db, survey_id, _creator_id(user))
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "message": "问卷不存在", "data": {}},
        )
    return success(doc)


@router.put("/{survey_id}")
async def update_survey(
    survey_id: str,
    body: SurveyUpdate,
    user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    patch = body.dict(exclude_unset=True)
    if body.settings is not None:
        patch["settings"] = body.settings.dict(exclude_unset=True)
    doc = await survey_service.update_survey(db, survey_id, _creator_id(user), patch)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "message": "问卷不存在", "data": {}},
        )
    return success(doc)


@router.delete("/{survey_id}")
async def delete_survey(
    survey_id: str,
    user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    ok = await survey_service.delete_survey(db, survey_id, _creator_id(user))
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "message": "问卷不存在", "data": {}},
        )
    return success({})


@router.post("/{survey_id}/duplicate")
async def duplicate_survey(
    survey_id: str,
    user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    data = await survey_service.duplicate_survey(db, survey_id, _creator_id(user))
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "message": "问卷不存在", "data": {}},
        )
    return success(data)


@router.post("/{survey_id}/publish")
async def publish_survey(
    survey_id: str,
    user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    ok, msg, data = await survey_service.publish_survey(
        db, survey_id, _creator_id(user)
    )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 400, "message": msg, "data": {}},
        )
    return success(data)


@router.post("/{survey_id}/close")
async def close_survey(
    survey_id: str,
    user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    ok, msg, data = await survey_service.close_survey(db, survey_id, _creator_id(user))
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "message": msg, "data": {}},
        )
    return success(data)


# --- questions ---


@router.get("/{survey_id}/questions")
async def list_questions(
    survey_id: str,
    user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    docs = await question_service.list_questions(db, survey_id, _creator_id(user))
    if docs is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "message": "问卷不存在", "data": {}},
        )
    return success(docs)


@router.post("/{survey_id}/questions/reorder")
async def reorder_questions(
    survey_id: str,
    body: QuestionReorder,
    user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    docs = await question_service.reorder_questions(
        db, survey_id, _creator_id(user), body.question_ids
    )
    if docs is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 400, "message": "题目列表与问卷不一致", "data": {}},
        )
    return success(docs)


@router.post("/{survey_id}/questions")
async def add_question(
    survey_id: str,
    body: QuestionCreate,
    user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    sur = await survey_service.get_survey(db, survey_id, _creator_id(user))
    if not sur:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "message": "问卷不存在", "data": {}},
        )
    if sur.get("status", "draft") != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": 400,
                "message": "仅草稿问卷可添加题目",
                "data": {},
            },
        )
    payload = body.dict()
    if body.validation is not None:
        payload["validation"] = body.validation.dict(exclude_unset=True)
    doc = await question_service.add_question(
        db, survey_id, _creator_id(user), payload
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "message": "问卷不存在", "data": {}},
        )
    return success(doc)


@router.put("/{survey_id}/questions/{qid}")
async def update_question(
    survey_id: str,
    qid: str,
    body: QuestionUpdate,
    user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    sur = await survey_service.get_survey(db, survey_id, _creator_id(user))
    if not sur:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "message": "问卷不存在", "data": {}},
        )
    if sur.get("status") in ("published", "closed"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": 400,
                "message": "已发布或已关闭的问卷不可修改题目内容",
                "data": {},
            },
        )
    patch = body.dict(exclude_unset=True)
    if body.validation is not None:
        patch["validation"] = body.validation.dict(exclude_unset=True)
    doc = await question_service.update_question(
        db, survey_id, qid, _creator_id(user), patch
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "message": "题目不存在", "data": {}},
        )
    return success(doc)


@router.post("/{survey_id}/questions/{qid}/apply-library-version")
async def apply_library_version_to_survey_question(
    survey_id: str,
    qid: str,
    body: ApplyLibraryVersionBody,
    user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    doc = await question_service.apply_library_version_to_survey_question(
        db, survey_id, qid, _creator_id(user), body.library_question_id
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": 400,
                "message": "无法覆盖：请确认问卷为草稿、题目已关联题库家族且所选版本属于同一家族",
                "data": {},
            },
        )
    return success(doc)


@router.delete("/{survey_id}/questions/{qid}")
async def delete_question(
    survey_id: str,
    qid: str,
    user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    sur = await survey_service.get_survey(db, survey_id, _creator_id(user))
    if not sur:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "message": "问卷不存在", "data": {}},
        )
    if sur.get("status") in ("published", "closed"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": 400,
                "message": "已发布或已关闭的问卷不可删除题目",
                "data": {},
            },
        )
    ok = await question_service.delete_question(
        db, survey_id, qid, _creator_id(user)
    )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "message": "题目不存在", "data": {}},
        )
    return success({})


@router.post("/{survey_id}/questions/from-library")
async def add_question_from_library(
    survey_id: str,
    body: AddQuestionFromLibraryBody,
    user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    sur = await survey_service.get_survey(db, survey_id, _creator_id(user))
    if not sur:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "message": "问卷不存在", "data": {}},
        )
    if sur.get("status", "draft") != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": 400,
                "message": "仅草稿问卷可从题库添加题目",
                "data": {},
            },
        )
    doc = await question_service.add_question_from_library(
        db, survey_id, _creator_id(user), body.library_question_id
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": 400,
                "message": "库题不存在或无权使用",
                "data": {},
            },
        )
    return success(doc)
