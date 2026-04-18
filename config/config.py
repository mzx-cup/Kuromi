from __future__ import annotations

import os
import logging
from pathlib import Path

from pydantic_settings import BaseSettings

logger = logging.getLogger("starlearn.config")

_dotenv_path = Path(__file__).resolve().parent / ".env"


class Settings(BaseSettings):
    xunfei_api_url: str = "https://maas-coding-api.cn-huabei-1.xf-yun.com/v2/chat/completions"
    xunfei_api_key: str = "590f183a4564ff3c628ad0d6b692768f:YjdkMDdlODI3ODBiMGYxYzI4NDFmODc0"
    model_name: str = "astron-code-latest"

    minimax_api_url: str = "https://api.minimax.chat/v1"
    minimax_api_key: str = "sk-cp-NVJBfQDPdzQCtzIJoXOXamJ1L-hNMTDyweOV_1KsePGk9FnSLBvRejIDDpbjMe67O0aiZEIkMd267a2zNutthLjnUF5rxOU65dzMsYNXeWMcGOoQ7WCGX4I"
    minimax_model_name: str = "MiniMax-M2.7"

    debug: bool = False

    model_config = {
        "env_file": str(_dotenv_path),
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


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
