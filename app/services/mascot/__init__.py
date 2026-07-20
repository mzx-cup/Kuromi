"""小星 AI 学习助手的服务层。

- ``llm_service``: 直接调用 MiniMax (minimax-Text-01) 大模型 API 的接入层。
"""
from app.services.mascot.llm_service import (
    MASCOT_DEFAULT_TEMPERATURE,
    MascotLLMService,
    build_mascot_messages,
)

__all__ = [
    "MascotLLMService",
    "build_mascot_messages",
    "MASCOT_DEFAULT_TEMPERATURE",
]
