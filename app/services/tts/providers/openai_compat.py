"""
OpenAI 兼容 TTS Provider — 用于自定义 TTS 端点

支持任何兼容 OpenAI TTS API 的服务（如本地部署的 TTS 服务）
"""

import logging
import httpx
from app.services.tts.types import BaseTTSProvider, TTSConfig, TTSResult

logger = logging.getLogger("starlearn.tts.openai_compat")


class OpenAICompatTTSProvider(BaseTTSProvider):
    """OpenAI 兼容 TTS Provider，支持自定义 base_url"""

    provider_id: str

    def __init__(self, provider_id: str = "custom-tts-openai"):
        self.provider_id = provider_id

    async def generate(self, text: str, config: TTSConfig) -> TTSResult:
        base_url = config.base_url or "https://api.openai.com/v1"
        url = f"{base_url}/audio/speech"

        payload = {
            "model": config.model_id or "tts-1",
            "input": text.strip(),
            "voice": config.voice or "alloy",
            "response_format": config.audio_format or "mp3",
            "speed": config.speed,
        }

        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code != 200:
                raise RuntimeError(
                    f"OpenAI-compat TTS error HTTP {response.status_code}: {response.text[:200]}"
                )
            audio_bytes = response.content

        duration_ms = self.estimate_duration_ms(audio_bytes, config.audio_format)
        logger.info(
            "OpenAI-compat TTS (%s): text_len=%d, audio_bytes=%d",
            self.provider_id, len(text), len(audio_bytes),
        )
        return TTSResult(audio=audio_bytes, format=config.audio_format, duration_ms=duration_ms)
