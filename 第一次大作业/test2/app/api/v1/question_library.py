from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.deps import get_current_user, get_db
from app.schemas.common import success
from app.schemas.library import (
    BankItemAdd,
    BankItemDisplayVersionBody,
    LibraryQuestionCreate,
    LibraryQuestionNewVersion,
    LibraryQuestionUpdateBody,
    QuestionBankCreate,
    QuestionBankUpdate,
    ShareLineageBody,
    PromoteSurveyQuestionBody,
)
from app.services import (
    library_question_service,
    question_bank_service,
    statistic_service,
)

router = APIRouter()


def _uid(user: Dict[str, Any]) -> str:
    return user["id"]


# --- library questions ---


@router.post("/items")
async def create_library_item(
    body: LibraryQuestionCreate,
    user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    bank_ids = list(body.bank_ids)
    payload = body.dict(exclude={"bank_ids"})
    if body.validation is not None:
        payload["validation"] = body.validation.dict(exclude_unset=True)
    data = await library_question_service.create_library_question(
        db, _uid(user), payload
    )
    ok, msg = await question_bank_service.attach_library_question_to_banks(
        db, _uid(user), data["id"], bank_ids
    )
    if not ok:
        await library_question_service.delete_library_question_owned(
            db, data["id"], _uid(user)
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 400, "message": msg, "data": {}},
        )
    return success(data)


@router.get("/items")
async def list_library_items(
    user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    data = await library_question_service.list_visible_library_questions(
        db, _uid(user)
    )
    return success(data)


@router.get("/items/{library_question_id}")
async def get_library_item(
    library_question_id: str,
    user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    data = await library_question_service.get_library_question(
        db, library_question_id, _uid(user)
    )
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "message": "库题不存在或无权访问", "data": {}},
        )
    return success(data)


@router.put("/items/{library_question_id}")
async def update_library_item_inplace(
    library_question_id: str,
    body: LibraryQuestionUpdateBody,
    user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    payload = body.dict()
    if body.validation is not None:
        payload["validation"] = body.validation.dict(exclude_unset=True)
    data = await library_question_service.update_library_question_owned(
        db, _uid(user), library_question_id, payload
    )
    if not data:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": 403, "message": "无权修改或题目不存在", "data": {}},
        )
    return success(data)


@router.post("/items/{library_question_id}/versions")
async def new_library_version(
    library_question_id: str,
    body: LibraryQuestionNewVersion,
    user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    bank_ids = list(body.bank_ids)
    payload = body.dict(exclude={"bank_ids"})
    if body.validation is not None:
        payload["validation"] = body.validation.dict(exclude_unset=True)
    data = await library_question_service.create_new_version(
        db, _uid(user), library_question_id, payload
    )
    if not data:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": 403, "message": "无权基于该版本创建新题或题目不存在", "data": {}},
        )
    ok, msg = await question_bank_service.attach_library_question_to_banks(
        db, _uid(user), data["id"], bank_ids
    )
    if not ok:
        await library_question_service.delete_library_question_owned(
            db, data["id"], _uid(user)
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 400, "message": msg, "data": {}},
        )
    await question_bank_service.unset_display_for_lineage_in_banks(
        db, bank_ids, str(data.get("lineage_id", ""))
    )
    return success(data)


@router.delete("/items/{library_question_id}/version")
async def delete_one_library_version(
    library_question_id: str,
    user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    ok, err = await library_question_service.delete_library_version_owned(
        db, _uid(user), library_question_id
    )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 400, "message": err, "data": {}},
        )
    return success({})


@router.post("/items/{library_question_id}/restore-as-new")
async def restore_library_as_new(
    library_question_id: str,
    user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    data = await library_question_service.restore_version_as_new(
        db, _uid(user), library_question_id
    )
    if not data:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": 403, "message": "无权恢复或题目不存在", "data": {}},
        )
    return success(data)


@router.post("/items/from-survey-question")
async def promote_from_survey(
    body: PromoteSurveyQuestionBody,
    user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    data, did_create = await library_question_service.promote_survey_question(
        db, _uid(user), body.survey_id, body.question_id
    )
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "message": "问卷或题目不存在", "data": {}},
        )
    ok, msg = await question_bank_service.attach_library_question_to_banks(
        db, _uid(user), data["id"], list(body.bank_ids)
    )
    if not ok:
        if did_create:
            await library_question_service.delete_library_question_owned(
                db, data["id"], _uid(user)
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 400, "message": msg, "data": {}},
        )
    return success(data)


@router.get("/lineages/{lineage_id}/versions")
async def list_lineage_versions(
    lineage_id: str,
    user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    data = await library_question_service.list_versions(db, _uid(user), lineage_id)
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "message": "无权查看该题目家族", "data": {}},
        )
    return success(data)


@router.get("/lineages/{lineage_id}/usage")
async def lineage_usage(
    lineage_id: str,
    user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    data = await library_question_service.lineage_usage_for_user(
        db, _uid(user), lineage_id
    )
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "message": "无权查看使用情况", "data": {}},
        )
    return success(data)


@router.get("/lineages/{lineage_id}/cross-statistics")
async def lineage_cross_stats(
    lineage_id: str,
    user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    data = await statistic_service.cross_survey_lineage_statistics(
        db, lineage_id, _uid(user)
    )
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "message": "无权查看统计", "data": {}},
        )
    return success(data)


# --- shares ---


@router.post("/shares")
async def create_share(
    body: ShareLineageBody,
    user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    ok, msg = await library_question_service.share_lineage(
        db, _uid(user), body.grantee_username, body.lineage_id
    )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 400, "message": msg, "data": {}},
        )
    return success({})


@router.get("/shares/outgoing")
async def list_outgoing_shares(
    user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    data = await library_question_service.list_shares_outgoing(db, _uid(user))
    return success(data)


@router.get("/shares/incoming")
async def list_incoming_shares(
    user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    data = await library_question_service.list_shares_incoming(db, _uid(user))
    return success(data)


@router.delete("/shares/{share_id}")
async def delete_share(
    share_id: str,
    user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    ok = await library_question_service.revoke_share(db, _uid(user), share_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "message": "共享记录不存在", "data": {}},
        )
    return success({})


# --- banks ---


@router.post("/banks")
async def create_bank(
    body: QuestionBankCreate,
    user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    ok, msg, data = await question_bank_service.create_bank(
        db, _uid(user), body.title, body.description or ""
    )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 400, "message": msg, "data": {}},
        )
    return success(data)


@router.get("/banks")
async def list_banks(
    user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    data = await question_bank_service.list_banks(db, _uid(user))
    return success(data)


@router.get("/banks/{bank_id}")
async def get_bank(
    bank_id: str,
    user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    data = await question_bank_service.get_bank(db, bank_id, _uid(user))
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "message": "题库不存在", "data": {}},
        )
    return success(data)


@router.put("/banks/{bank_id}")
async def update_bank(
    bank_id: str,
    body: QuestionBankUpdate,
    user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    patch = body.dict(exclude_unset=True)
    ok, msg, data = await question_bank_service.update_bank(db, bank_id, _uid(user), patch)
    if not ok and msg == "题库不存在":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "message": "题库不存在", "data": {}},
        )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 400, "message": msg, "data": {}},
        )
    return success(data)


@router.delete("/banks/{bank_id}")
async def delete_bank(
    bank_id: str,
    user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    ok, err = await question_bank_service.delete_bank(db, bank_id, _uid(user))
    if not ok:
        if err == "共享库不可删除":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": 400, "message": err, "data": {}},
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "message": "题库不存在", "data": {}},
        )
    return success({})


@router.post("/banks/{bank_id}/items")
async def add_bank_item(
    bank_id: str,
    body: BankItemAdd,
    user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    ok, msg, data = await question_bank_service.add_bank_item(
        db, bank_id, _uid(user), body.library_question_id
    )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 400, "message": msg, "data": {}},
        )
    return success(data)


@router.delete("/banks/{bank_id}/items/{library_question_id}")
async def remove_bank_item(
    bank_id: str,
    library_question_id: str,
    user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    ok = await question_bank_service.remove_bank_item(
        db, bank_id, _uid(user), library_question_id
    )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "message": "移除失败", "data": {}},
        )
    return success({})


@router.patch("/banks/{bank_id}/items/display")
async def set_bank_item_display_version(
    bank_id: str,
    body: BankItemDisplayVersionBody,
    user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    lqid = str(body.library_question_id or "").strip() or None
    ok, msg = await question_bank_service.set_bank_item_display_version(
        db, bank_id, _uid(user), body.lineage_id, lqid
    )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 400, "message": msg, "data": {}},
        )
    return success({})


@router.get("/banks/{bank_id}/items")
async def list_bank_items(
    bank_id: str,
    user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    data = await question_bank_service.list_bank_items(db, bank_id, _uid(user))
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "message": "题库不存在", "data": {}},
        )
    return success(data)
