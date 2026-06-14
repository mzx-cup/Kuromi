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
    xunfei_api_key: str = Field(default="", description="讯飞大模型 API Key（请配置到 .env 文件）")
    model_name: str = "astron-code-latest"

    minimax_api_url: str = "https://api.minimax.chat/v1"
    minimax_api_key: str = Field(default="", description="MiniMax API Key（请配置到 .env 文件）")
    minimax_group_id: str = Field(default="", description="MiniMax API Group ID for TTS（请配置到 .env 文件）")
    minimax_model_name: str = "MiniMax-Text-01"

    # MiniMax 媒体生成模型
    minimax_image_model: str = Field(default="image-01", description="MiniMax image generation model")
    minimax_video_model: str = Field(default="video-01", description="MiniMax video generation model")
    minimax_tts_model: str = Field(default="speech-2.8-hd", description="MiniMax TTS model for voice generation")

    # MiniMax Coding Plan 搜索额度（走 coding-plan-search）
    minimax_search_api_url: str = "https://api.minimax.chat/v1"
    minimax_search_model: str = "MiniMax-Text-01"

    # 百度语音识别 API（用于语音转文字）
    baidu_asr_app_id: str = Field(default="", description="百度语音识别 App ID")
    baidu_asr_api_key: str = Field(default="", description="百度语音识别 API Key（请配置到 .env 文件）")
    baidu_asr_secret_key: str = Field(default="", description="百度语音识别 Secret Key（请配置到 .env 文件）")

    # 可灵Kling视频生成API
    kling_api_url: str = "https://api.kling.ai/v1"
    kling_access_key: str = Field(default="", description="可灵Kling Access Key")
    kling_secret_key: str = Field(default="", description="可灵Kling Secret Key")

    # Use app-specific env names so a global DEBUG variable does not override us.
    debug: bool = Field(
        default=False,
        validation_alias=AliasChoices("KUROMI_DEBUG", "APP_DEBUG"),
    )

    # ── 学习路径目标真实性校验（real-time 校验开关） ──
    learning_goal_validation: dict = Field(
        default_factory=lambda: {
            "enabled": True,    # 总开关：关闭后 _validate_and_ground_learning_goals 不执行
            "strict": False,    # 严格模式：校验失败的节点直接剔除（默认仅标红不剔除）
            "max_invalid_pct": 50.0,  # 严格模式阈值：超过此比例的节点失败才视为 LLM 输出异常
        },
        description="学习路径 learning_goal / goal_evidence 真实性校验配置",
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
