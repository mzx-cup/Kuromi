from __future__ import annotations

import logging
from typing import Any
from pathlib import Path

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger("starlearn.config")

_dotenv_path = Path(__file__).resolve().parent / ".env"


class Settings(BaseSettings):
    xunfei_api_url: str = "https://maas-coding-api.cn-huabei-1.xf-yun.com/v2/chat/completions"
    xunfei_api_key: str = "590f183a4564ff3c628ad0d6b692768f:YjdkMDdlODI3ODBiMGYxYzI4NDFmODc0"
    model_name: str = "astron-code-latest"

    minimax_api_url: str = "https://api.minimax.chat/v1"
    minimax_api_key: str = "sk-cp-NVJBfQDPdzQCtzIJoXOXamJ1L-hNMTDyweOV_1KsePGk9FnSLBvRejIDDpbjMe67O0aiZEIkMd267a2zNutthLjnUF5rxOU65dzMsYNXeWMcGOoQ7WCGX4I"
    minimax_group_id: str = Field(default="2041507423801320239", description="MiniMax API Group ID for TTS")
    minimax_model_name: str = "MiniMax-M2.7"

    # MiniMax 媒体生成模型
    minimax_image_model: str = Field(default="image-01", description="MiniMax image generation model")
    minimax_video_model: str = Field(default="video-01", description="MiniMax video generation model")
    minimax_tts_model: str = Field(default="speech-02", description="MiniMax TTS model for voice generation")

    # 百度语音识别 API（用于语音转文字）
    baidu_asr_app_id: str = Field(default="", description="百度语音识别 App ID")
    baidu_asr_api_key: str = Field(default="eymy6AqdEbhI676lonzRF9ux", description="百度语音识别 API Key")
    baidu_asr_secret_key: str = Field(default="qcSs7d5xEKJyPIxK9fXJqeEel95XFi8F", description="百度语音识别 Secret Key")

    # Use app-specific env names so a global DEBUG variable does not override us.
    debug: bool = Field(
        default=False,
        validation_alias=AliasChoices("KUROMI_DEBUG", "APP_DEBUG"),
    )

    model_config = {
        "env_file": str(_dotenv_path),
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug_value(cls, value: Any) -> Any:
        if isinstance(value, str):
            normalized = value.strip().lower()
            truthy = {"1", "true", "yes", "on", "debug", "dev", "development", "local"}
            falsy = {"0", "false", "no", "off", "release", "prod", "production"}

            if normalized in truthy:
                return True
            if normalized in falsy:
                return False

        return value


def _load_settings() -> Settings:
    try:
        s = Settings()
        logger.info(
            "配置加载成功 | xunfei_api_url=%s | model=%s | key=***%s | minimax_api_url=%s | minimax_model=%s",
            s.xunfei_api_url,
            s.model_name,
            s.xunfei_api_key[-6:] if len(s.xunfei_api_key) > 6 else "******",
            s.minimax_api_url,
            s.minimax_model_name,
        )
        return s
    except Exception as exc:
        logger.error("配置加载失败: %s", exc)
        raise


settings = _load_settings()
