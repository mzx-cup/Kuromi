"""
ASR 统一抽象层 — 数据类型与基类

对应 OpenMAIC lib/audio/asr-providers.ts
"""

from abc import ABC, abstractmethod
from pydantic import BaseModel


class ASRResult(BaseModel):
    text: str
    language: str = "zh"
    confidence: float = 0.0


class BaseASRProvider(ABC):
    """ASR Provider 抽象基类"""

    provider_id: str

    @abstractmethod
    async def transcribe(self, audio: bytes, audio_format: str = "webm") -> ASRResult:
        """转写音频，返回文本"""
        ...
