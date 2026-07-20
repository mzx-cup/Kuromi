"""
Whisper ASR Provider

支持 OpenAI Whisper API 格式（兼容本地 faster-whisper 服务）。
"""

import logging
import httpx
from app.services.asr.types import BaseASRProvider, ASRResult

logger = logging.getLogger("starlearn.asr.whisper")


class WhisperASRProvider(BaseASRProvider):
    provider_id = "whisper"

    def __init__(self, base_url: str = "https://api.openai.com/v1", api_key: str = ""):
        self.base_url = base_url
        self.api_key = api_key

    async def transcribe(self, audio: bytes, audio_format: str = "webm") -> ASRResult:
        """
        调用 OpenAI Whisper API 转写音频。
        兼容任何实现 /v1/audio/transcriptions 端点的服务。
        """
        url = f"{self.base_url}/audio/transcriptions"

        # 映射格式到 MIME 类型
        mime_map = {
            "webm": "audio/webm",
            "mp3": "audio/mpeg",
            "wav": "audio/wav",
            "ogg": "audio/ogg",
            "m4a": "audio/mp4",
        }
        content_type = mime_map.get(audio_format, "audio/webm")

        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url,
                headers=headers,
                data={
                    "model": "whisper-1",
                    "language": "zh",
                    "response_format": "json",
                },
                files={
                    "file": (f"audio.{audio_format}", audio, content_type),
                },
            )

            if response.status_code != 200:
                raise RuntimeError(
                    f"Whisper API error HTTP {response.status_code}: {response.text[:200]}"
                )

            data = response.json()
            text = data.get("text", "").strip()
            logger.info("Whisper transcribed: %d chars", len(text))
            return ASRResult(text=text, language="zh", confidence=0.95)
