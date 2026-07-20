"""
TTS Provider 注册表 — 字典路由分发

对应 OpenMAIC lib/audio/tts-providers.ts 的 generateTTS() switch 分发逻辑
"""

import logging
from app.services.tts.types import BaseTTSProvider

logger = logging.getLogger("starlearn.tts.registry")

TTS_PROVIDER_REGISTRY: dict[str, type[BaseTTSProvider]] = {}


def _register_builtin_providers():
    """注册内置 Provider"""
    from app.services.tts.providers.minimax import MiniMaxTTSProvider
    TTS_PROVIDER_REGISTRY["minimax-tts"] = MiniMaxTTSProvider


_register_builtin_providers()


def get_tts_provider(provider_id: str) -> BaseTTSProvider:
    """根据 provider_id 实例化对应的 TTS Provider"""
    if provider_id in TTS_PROVIDER_REGISTRY:
        return TTS_PROVIDER_REGISTRY[provider_id]()

    # 自定义 Provider: 'custom-tts-{name}' → 走 OpenAI 兼容 API
    if provider_id.startswith("custom-tts-"):
        from app.services.tts.providers.openai_compat import OpenAICompatTTSProvider
        return OpenAICompatTTSProvider(provider_id)

    raise ValueError(f"Unsupported TTS provider: {provider_id}")


def list_providers() -> list[str]:
    """列出所有已注册的 Provider ID"""
    return list(TTS_PROVIDER_REGISTRY.keys())
