# -*- coding: utf-8 -*-
"""
TTS 统一抽象层 — 数据类型与基类

对应 OpenMAIC lib/audio/types.ts + lib/audio/tts-providers.ts
增强：支持流式合成 + 字级时间戳（超越 OpenMAIC）
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator

from pydantic import BaseModel


# =============================================================================
# 配置
# =============================================================================

class TTSConfig(BaseModel):
    """TTS 生成配置 — 对应 OpenMAIC 的 TTSModelConfig"""
    provider_id: str = "minimax-tts"
    model_id: str | None = None
    voice: str = "default"
    speed: float = 1.0
    audio_format: str = "mp3"
    api_key: str | None = None
    base_url: str | None = None


# =============================================================================
# 字级时间戳 — 星识增强（OpenMAIC 无此能力）
# =============================================================================

@dataclass
class WordTimestamp:
    """单个字/词的时间戳"""
    word: str                  # 字或词
    start_ms: int              # 起始时间(毫秒)
    end_ms: int                # 结束时间(毫秒)


@dataclass
class SentenceTimestamp:
    """句子级时间戳"""
    sentence: str              # 完整句子文本
    start_ms: int              # 句子起始时间(毫秒)
    end_ms: int                # 句子结束时间(毫秒)
    words: list[WordTimestamp] = field(default_factory=list)  # 字级细分（如果 Provider 支持）


# =============================================================================
# 统一结果 — 非流式 + 流式
# =============================================================================

class TTSResult(BaseModel):
    """
    非流式 TTS 统一返回契约。

    对应 OpenMAIC 的 TTSGenerationResult { audio: Uint8Array, format: string }
    星识增强：新增 duration_ms, word_timestamps, sentences
    """
    audio: bytes
    format: str                # 'mp3' | 'wav' | 'opus'
    duration_ms: int
    word_timestamps: list[dict] = []    # WordTimestamp 列表
    sentences: list[dict] = []          # SentenceTimestamp 列表


@dataclass
class TTSStreamChunk:
    """
    流式 TTS 块。

    使用示例:
        async for chunk in provider.generate_stream(text, config):
            if chunk.audio:
                yield sse_audio(chunk.audio)        # 推送到前端播放
            if chunk.word:
                yield sse_word_timestamp(chunk.word) # 触发动画/高亮
    """
    audio: bytes | None = None          # 音频增量数据
    word: WordTimestamp | None = None   # 当前字的级时间戳
    sentence_index: int = 0             # 当前句子序号
    is_final: bool = False              # 是否最后一个块


# =============================================================================
# Provider 抽象基类
# =============================================================================

class BaseTTSProvider(ABC):
    """TTS Provider 抽象基类"""

    provider_id: str

    # ---- 必须实现 ----

    @abstractmethod
    async def generate(self, text: str, config: TTSConfig) -> TTSResult:
        """非流式 TTS 生成"""
        ...

    # ---- 可选覆盖 ----

    async def generate_stream(
        self, text: str, config: TTSConfig
    ) -> AsyncIterator[TTSStreamChunk]:
        """
        流式 TTS 生成（支持字级时间戳）。

        默认回退到非流式 generate()，拆分为单个 chunk。
        子类可覆盖以提供真正的流式合成。
        """
        result = await self.generate(text, config)
        # 回退：将完整音频包装为单个 chunk
        yield TTSStreamChunk(
            audio=result.audio,
            is_final=True,
        )

    async def get_voices(self) -> list[dict]:
        """获取该 Provider 支持的音色列表"""
        return []

    @staticmethod
    def estimate_duration_ms(audio_bytes: bytes, fmt: str = "mp3") -> int:
        """根据音频字节数估算时长"""
        kbps_map = {"mp3": 128, "wav": 1411, "opus": 64}
        kbps = kbps_map.get(fmt, 128)
        return max(500, int(len(audio_bytes) * 8 / kbps))
