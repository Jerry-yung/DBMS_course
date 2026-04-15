from fastapi import APIRouter

from app.api.v1 import auth, jump_rules, public_fill, question_library, statistics, surveys

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(surveys.router, prefix="/surveys", tags=["surveys"])
api_router.include_router(
    question_library.router,
    prefix="/question-library",
    tags=["question-library"],
)
api_router.include_router(
    jump_rules.router, prefix="/surveys", tags=["jump-rules"]
)
api_router.include_router(
    statistics.router, prefix="/surveys", tags=["statistics"]
)
api_router.include_router(public_fill.router, tags=["public"])
