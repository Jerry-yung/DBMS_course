from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.deps import get_current_user, get_db
from app.schemas.auth import LoginRequest, RegisterRequest
from app.schemas.common import success
from app.services import auth_service

router = APIRouter()


@router.post("/register")
async def register(body: RegisterRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    ok, msg, data = await auth_service.register_user(
        db, body.username, body.password
    )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 400, "message": msg, "data": {}},
        )
    return success(data)


@router.post("/login")
async def login(body: LoginRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    ok, msg, data = await auth_service.login_user(db, body.username, body.password)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 401, "message": msg, "data": {}},
        )
    return success(data)


@router.get("/me")
async def me(user=Depends(get_current_user)):
    return success(auth_service.user_public(user))
