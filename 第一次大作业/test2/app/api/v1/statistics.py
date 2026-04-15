from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.deps import get_current_user, get_db
from app.schemas.common import success
from app.services import statistic_service

router = APIRouter()


def _creator_id(user: Dict[str, Any]) -> str:
    return user["id"]


@router.get("/{survey_id}/statistics")
async def full_stats(
    survey_id: str,
    user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    data = await statistic_service.full_statistics(
        db, survey_id, _creator_id(user)
    )
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "message": "问卷不存在", "data": {}},
        )
    return success(data)


@router.get("/{survey_id}/statistics/{qid}")
async def question_stats(
    survey_id: str,
    qid: str,
    user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    data = await statistic_service.single_question_stats(
        db, survey_id, qid, _creator_id(user)
    )
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "message": "问卷或题目不存在", "data": {}},
        )
    return success(data)


@router.get("/{survey_id}/export")
async def export_stats(
    survey_id: str,
    format: str = Query("json", regex="^(json|csv)$"),
    user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    data = await statistic_service.full_statistics(
        db, survey_id, _creator_id(user)
    )
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "message": "问卷不存在", "data": {}},
        )
    if format == "csv":
        body = statistic_service.export_csv(data)
        return Response(
            content=body,
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="survey_{survey_id}.csv"'
            },
        )
    return Response(
        content=statistic_service.export_json_payload(data),
        media_type="application/json; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="survey_{survey_id}.json"'
        },
    )
