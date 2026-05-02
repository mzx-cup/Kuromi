"""
ASR Provider 注册表
"""

import logging
from app.services.asr.types import BaseASRProvider

logger = logging.getLogger("starlearn.asr.registry")

ASR_PROVIDER_REGISTRY: dict[str, type[BaseASRProvider]] = {}


def _register_builtin_providers():
    from app.services.asr.providers.baidu import BaiduASRProvider
    ASR_PROVIDER_REGISTRY["baidu-asr"] = BaiduASRProvider


_register_builtin_providers()


def get_asr_provider(provider_id: str) -> BaseASRProvider:
    """根据 provider_id 实例化对应的 ASR Provider"""
    if provider_id in ASR_PROVIDER_REGISTRY:
        return ASR_PROVIDER_REGISTRY[provider_id]()

    if provider_id == "whisper":
        from app.services.asr.providers.whisper import WhisperASRProvider
        return WhisperASRProvider()

    raise ValueError(f"Unsupported ASR provider: {provider_id}")


def list_providers() -> list[str]:
    """列出所有已注册的 Provider ID（含动态注册的 whisper）"""
    return list(ASR_PROVIDER_REGISTRY.keys()) + ["whisper"]
