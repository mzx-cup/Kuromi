from fastapi import APIRouter

from app.api.tts import router as tts_router
from app.api.asr import router as asr_router
from app.api.grading import router as grading_router
from app.api.teacher_chat import router as teacher_chat_router

router = APIRouter(prefix="/api/v2")

router.include_router(tts_router)
router.include_router(asr_router)
router.include_router(grading_router)
router.include_router(teacher_chat_router)
