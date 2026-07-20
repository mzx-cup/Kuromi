from fastapi import APIRouter

from app.api.tts import router as tts_router
from app.api.asr import router as asr_router
from app.api.grading import router as grading_router
from app.api.teacher_chat import router as teacher_chat_router
from app.api.ppt import router as ppt_router

# 注意: profile_router 已在 main.py 中注册为 /api/profile/{user_id}，
# 不再在 /api/v2 下重复暴露。所有页面统一通过 /api/profile/ 获取画像。

router = APIRouter(prefix="/api/v2")

router.include_router(tts_router)
router.include_router(asr_router)
router.include_router(grading_router)
router.include_router(teacher_chat_router)
router.include_router(ppt_router)
