"""火山方舟 Ark 客户端 — 共享初始化, 从 .env 读 API Key"""

from __future__ import annotations

import os
from functools import lru_cache

try:
    from volcenginesdkarkruntime import Ark
except ImportError:
    Ark = None  # type: ignore


@lru_cache(maxsize=1)
def get_ark_client() -> Ark:
    """全局单例 Ark 客户端, 懒加载。

    鉴权优先级:
      1. ARK_API_KEY — 方舟 API Key (推荐, 所有方法都支持)
      2. VOLC_ACCESS_KEY / VOLC_SECRET_KEY — IAM AK/SK (部分方法不支持)

    环境变量:
      ARK_API_KEY — 方舟 API Key (https://console.volcengine.com/ark/region:ark+cn-beijing/apiKey)
      VOLC_ACCESS_KEY / VOLC_SECRET_KEY — 访问控制 IAM 密钥 (兜底)
      VOLC_REGION — 区域 (默认 cn-beijing)
    """
    api_key = os.environ.get("ARK_API_KEY")
    if api_key:
        if Ark is None:
            raise RuntimeError("volcenginesdkarkruntime 未安装，无法使用 Seed Media 功能")
        return Ark(api_key=api_key)

    ak = os.environ.get("VOLC_ACCESS_KEY")
    sk = os.environ.get("VOLC_SECRET_KEY")
    region = os.environ.get("VOLC_REGION", "cn-beijing")
    if ak and sk:
        if Ark is None:
            raise RuntimeError("volcenginesdkarkruntime 未安装，无法使用 Seed Media 功能")
        return Ark(ak=ak, sk=sk, region=region)

    raise RuntimeError(
        "请配置 ARK_API_KEY (推荐) 或 VOLC_ACCESS_KEY + VOLC_SECRET_KEY 到 .env\n"
        "ARK API Key 创建地址: https://console.volcengine.com/ark/region:ark+cn-beijing/apiKey"
    )
