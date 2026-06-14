"""Seedream 4.5 图片生成 — 同步生成, 返回本地路径"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

import httpx

from app.services.ark_client import get_ark_client

logger = logging.getLogger("starlearn.seedream")

STORAGE_ROOT = Path(os.environ.get("STORAGE_DIR", "storage")) / "images"


def _ensure_storage(sub_dir: str = "") -> Path:
    dst = STORAGE_ROOT / sub_dir
    dst.mkdir(parents=True, exist_ok=True)
    return dst


def _extract_ext(url: str) -> str:
    m = re.search(r"\.(png|jpg|jpeg|webp)(?:\?|$)", url, re.IGNORECASE)
    return f".{m.group(1).lower()}" if m else ".png"


def generate_image(
    prompt: str,
    *,
    size: str = "1024x1024",
    model: str | None = None,
    image: str | list[str] | None = None,
    sub_dir: str = "",
    watermark: bool = False,
) -> dict:
    """调用 Seedream 4.5 生成图片, 下载到本地 storage/images/, 返回结果。

    返回格式:
      {
        "status": "succeeded" | "failed",
        "local_path": "..." / None,
        "error": ... / None,
        "revised_prompt": "...",
      }

    Seedream 是同步接口 (不走 task_id 轮询), 几秒内返回。
    """
    client = get_ark_client()
    model_id = model or os.environ.get(
        "ARK_IMAGE_MODEL", "doubao-seedream-4-5-250911"
    )

    resp = client.images.generate(
        model=model_id,
        prompt=prompt,
        size=size,
        image=image,
        watermark=watermark,
    )
    data = resp.data

    if not data or not data[0].url:
        logger.warning("Seedream 返回空 data prompt=%s", prompt[:60])
        return {"status": "failed", "local_path": None, "error": "empty response"}

    url = data[0].url
    _ensure_storage(sub_dir)

    # 以 prompt 前 30 字取 hash 做文件名, 避免 URL 参数干扰
    safe_name = re.sub(r"[^a-zA-Z0-9一-鿿_-]", "_", prompt[:30])
    ext = _extract_ext(url)
    local_path = STORAGE_ROOT / sub_dir / f"{safe_name}{ext}"

    logger.info("下载图片 %s -> %s", url, local_path)
    r = httpx.get(url, follow_redirects=True, timeout=120)
    r.raise_for_status()
    local_path.write_bytes(r.content)

    return {
        "status": "succeeded",
        "local_path": str(local_path),
        "error": None,
        "revised_prompt": getattr(data[0], "revised_prompt", None) if hasattr(data[0], "revised_prompt") else None,
    }
