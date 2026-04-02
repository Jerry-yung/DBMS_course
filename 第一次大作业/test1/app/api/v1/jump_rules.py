from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.deps import get_current_user, get_db
from app.schemas.common import success
from app.schemas.jump_rule import JumpRuleCreate, JumpRuleUpdate
from app.services import jump_rule_service

router = APIRouter()


def _creator_id(user: Dict[str, Any]) -> str:
    return user["id"]


@router.post("/{survey_id}/jump-rules")
async def add_jump_rule(
    survey_id: str,
    body: JumpRuleCreate,
    user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    payload = body.dict()
    doc = await jump_rule_service.add_rule(
        db, survey_id, _creator_id(user), payload
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 400, "message": "问卷或题目无效", "data": {}},
        )
    return success(doc)


@router.get("/{survey_id}/jump-rules")
async def list_jump_rules(
    survey_id: str,
    user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    docs = await jump_rule_service.list_rules(db, survey_id, _creator_id(user))
    if docs is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "message": "问卷不存在", "data": {}},
        )
    return success(docs)


@router.put("/{survey_id}/jump-rules/{rule_id}")
async def update_jump_rule(
    survey_id: str,
    rule_id: str,
    body: JumpRuleUpdate,
    user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    patch = {k: v for k, v in body.dict(exclude_unset=True).items()}
    doc = await jump_rule_service.update_rule(
        db, survey_id, rule_id, _creator_id(user), patch
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "message": "规则或题目不存在", "data": {}},
        )
    return success(doc)


@router.delete("/{survey_id}/jump-rules/{rule_id}")
async def delete_jump_rule(
    survey_id: str,
    rule_id: str,
    user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    ok = await jump_rule_service.delete_rule(
        db, survey_id, rule_id, _creator_id(user)
    )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "message": "规则不存在", "data": {}},
        )
    return success({})
