"""
B 站视频 → 音频 → 字幕的兜底管道.

数据流:
    yt-dlp 拉音轨 (m4a/aac)  →  按 60s 切片 (避免 Whisper 25 MB 上限)
    →  每片调 Whisper ASR 服务 (走 app.services.asr.providers.whisper)
    →  合并成 [{from, to, content}] 与 player/v2 字幕格式对齐

注意:
  1. 这一步会下载视频音频 (10 MB ~ 50 MB), 默认关闭 (settings.bili_assistant_enabled=False).
  2. 调用前会读 config/settings.bili_assistant_* 配置.
  3. 同一 bvid 的转写结果会缓存到磁盘, 避免重复下载.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("starlearn.bilibili_audio_asr")


# ── 缓存目录 ──
_CACHE_ROOT = Path(
    os.environ.get("STARLEARN_AUDIO_CACHE")
    or (Path(__file__).resolve().parents[2] / "storage" / "bilibili_audio")
)


def _is_enabled() -> bool:
    try:
        from config import settings
        # 主开关 + 必须至少配 Whisper 端点
        if not getattr(settings, "bili_assistant_enabled", False):
            return False
        return bool(getattr(settings, "bili_assistant_openai_base_url", "").strip())
    except Exception:
        return False


def _settings():
    from config import settings
    return settings


def _resolve_bin(name: str, override: str = "") -> str | None:
    """优先用 override, 再 PATH, 再常见 Windows 路径."""
    if override and Path(override).exists():
        return override
    found = shutil.which(name)
    if found:
        return found
    if os.name == "nt":
        # Windows: 看看安装器是不是写到 PATH 或者 AppData
        candidates = [
            Path.home() / "AppData" / "Local" / "Microsoft" / "WinGet" / "Links" / (name + ".exe"),
            Path("C:/ProgramData/chocolatey/bin") / (name + ".exe"),
        ]
        for c in candidates:
            if c.exists():
                return str(c)
    return None


def _cache_path(bvid: str, cid: int) -> Path:
    h = hashlib.md5(f"{bvid}|{cid}".encode()).hexdigest()[:12]
    d = _CACHE_ROOT / h
    d.mkdir(parents=True, exist_ok=True)
    return d


# ── 入口 ──

async def transcribe_bilibili_video(
    bvid: str,
    cid: int,
    *,
    force_redownload: bool = False,
    progress_cb=None,
) -> dict[str, Any]:
    """拉音轨 + ASR 转写. 返回与 fetch_subtitles 兼容的 list[dict] 结构.

    返回: [{lang, url, content: [{from, to, content}], source: 'asr'}]
    """
    if not _is_enabled():
        return []
    if not bvid or not cid:
        return []

    settings_ = _settings()
    cache_dir = _cache_path(bvid, cid)
    transcript_json = cache_dir / "transcript.json"

    # 命中缓存
    if not force_redownload and transcript_json.exists():
        try:
            data = json.loads(transcript_json.read_text(encoding="utf-8"))
            if data and data.get("content"):
                logger.info("ASR 命中缓存 bvid=%s cid=%s lines=%d", bvid, cid, len(data["content"]))
                return [data]
        except Exception as exc:
            logger.warning("ASR 缓存读取失败, 重做: %s", exc)

    # 1. yt-dlp 拉音轨
    audio_path = await _download_audio(bvid, cid, cache_dir, progress_cb)
    if not audio_path or not audio_path.exists():
        logger.warning("yt-dlp 未产出音频: bvid=%s", bvid)
        return []

    # 2. ffmpeg 切片 (60s)
    chunks = await _slice_audio(audio_path, cache_dir)
    if not chunks:
        logger.warning("ffmpeg 切片失败: %s", audio_path)
        return []

    # 3. 调 Whisper ASR 逐片识别
    from app.services.asr.providers.whisper import WhisperASRProvider
    from app.services.asr.types import TTSConfig  # noqa: F401  — 占位, 让导入顺序稳定

    provider = WhisperASRProvider(
        base_url=settings_.bili_assistant_openai_base_url.rstrip("/"),
        api_key=settings_.bili_assistant_openai_api_key or "no-key",
    )
    # Whisper-1 API 单文件上限 25 MB;
    # 60s m4a 大概 1-2 MB, 远低于上限; 不必再压.

    all_lines: list[dict[str, Any]] = []
    base_offset = 0.0
    for idx, chunk in enumerate(chunks):
        if progress_cb:
            try:
                progress_cb(idx, len(chunks))
            except Exception:
                pass
        text = await _transcribe_chunk(provider, chunk)
        if not text:
            base_offset += _duration(chunk)
            continue
        # chunk-level text 转成时间轴近似条目 (按句号/换行切)
        for piece in _split_text_into_segments(text):
            seg_dur = min(6.0, max(1.5, len(piece) * 0.18))  # 经验估算
            all_lines.append({
                "from": round(base_offset, 2),
                "to": round(base_offset + seg_dur, 2),
                "content": piece,
            })
            base_offset += seg_dur
        # 安全兜底: 避免 base_offset 漂移, 让它跟着切片走
        base_offset += max(0, _duration(chunk) - _approx_duration_of_lines(all_lines[-10:]))
        # 释放已识别切片
        try:
            chunk.unlink()
        except Exception:
            pass

    if not all_lines:
        logger.info("yt-dlp+Whisper 转写结果为空 bvid=%s", bvid)
        return []

    payload = {
        "lang": "zh-CN",
        "url": "",
        "content": all_lines,
        "source": "asr",
        "model": "whisper-1",
        "generated_at": time.time(),
        "asr_confidence": 0.85,
    }
    try:
        transcript_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.warning("缓存 ASR 结果失败: %s", exc)
    return [payload]


# ── 工具 ──

async def _download_audio(bvid: str, cid: int, out_dir: Path, progress_cb=None) -> Path | None:
    out_tpl = str(out_dir / "audio.%(ext)s")
    cookie = ""

    try:
        from config import settings
        cookie = (settings.bili_cookie or "").strip()
    except Exception:
        cookie = ""

    cmd = [
        _resolve_bin("yt-dlp", getattr(_settings(), "bili_assistant_ytdlp_path", "")) or "yt-dlp",
        "-x", "--audio-format", "m4a", "--audio-quality", "5",
        "-o", out_tpl,
        "--no-progress", "--no-warnings",
        "--no-playlist", "--no-part",
        "--postprocessor-args", "-ac 1 -ar 16000",  # 单声道 16kHz, 给 Whisper
        "--download-sections", f"*0-{min(900, _estimate_max_seconds(0))}",  # 默认截前 15 min 节流
        f"https://www.bilibili.com/video/{bvid}?p={_cid_to_page(cid)}",
    ]
    if cookie:
        cmd += ["--add-header", f"Cookie:{cookie}"]

    # 长 timeout: 视视频长度而定, 上限 8 分钟
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=480)
    except asyncio.TimeoutError:
        proc.kill()
        logger.warning("yt-dlp 下载超时 bvid=%s", bvid)
        return None

    if proc.returncode != 0:
        logger.warning("yt-dlp 失败 bvid=%s err=%s", bvid, stderr.decode("utf-8", errors="replace")[-400:])
        return None

    # 找实际产出
    candidates = sorted(out_dir.glob("audio.*"), key=lambda p: p.stat().st_mtime, reverse=True)
    for c in candidates:
        if c.is_file() and c.stat().st_size > 1024:
            return c
    return None


def _estimate_max_seconds(_x: int) -> int:
    # 沙箱保护: 仅下前 15 分钟音频, 避免巨大开销. 在生产环境可调整为全片.
    return 900


def _cid_to_page(cid: int) -> int:
    """B站 cid 是单 P 视频的内容标识; url 里 p=1 即可. 默认返回 1."""
    return 1


async def _slice_audio(audio: Path, out_dir: Path) -> list[Path]:
    """按 60s 切片. 返回切片文件路径列表."""
    ffmpeg = _resolve_bin("ffmpeg", getattr(_settings(), "bili_assistant_ffmpeg_path", "")) or "ffmpeg"
    chunks_dir = out_dir / "chunks"
    chunks_dir.mkdir(exist_ok=True)

    # 先列时长
    probe_cmd = [ffmpeg, "-i", str(audio), "-hide_banner"]
    proc = await asyncio.create_subprocess_exec(
        *probe_cmd,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    _, err = await proc.communicate()
    try:
        import re
        m = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", err.decode("utf-8", errors="replace"))
        total_s = 0.0
        if m:
            h, mn, s = m.groups()
            total_s = int(h) * 3600 + int(mn) * 60 + float(s)
    except Exception:
        total_s = 0.0

    if total_s <= 0:
        total_s = 900  # fallback

    seg = 60
    parts = []
    i = 0
    while i * seg < total_s:
        out = chunks_dir / f"chunk_{i:03d}.m4a"
        if out.exists():
            out.unlink()
        # 用 -c copy 太脆; 用 m4a 不行 (没 acodec), 强制成 adts (AAC)
        slice_cmd = [
            ffmpeg, "-y", "-ss", str(i * seg), "-i", str(audio), "-t", str(seg),
            "-ac", "1", "-ar", "16000",
            "-f", "adts", str(out),
        ]
        proc = await asyncio.create_subprocess_exec(
            *slice_cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.communicate()
        if out.exists() and out.stat().st_size > 100:
            parts.append(out)
        i += 1
        # 安全上限: 一次最多 15 片
        if i > 15:
            break
    return parts


async def _transcribe_chunk(provider, chunk_path: Path) -> str:
    try:
        data = chunk_path.read_bytes()
    except Exception as exc:
        logger.warning("读切片失败: %s", exc)
        return ""
    if not data:
        return ""
    try:
        result = await provider.transcribe(data, audio_format="m4a")
        return (result.text or "").strip()
    except Exception as exc:
        logger.warning("Whisper 识别失败 chunk=%s: %s", chunk_path.name, exc)
        return ""


def _split_text_into_segments(text: str) -> list[str]:
    """把一整段 ASR 输出切成短句, 便于前端时间轴展示."""
    text = (text or "").strip()
    if not text:
        return []
    parts = []
    # 按中文/英文常见断句符号切
    import re
    chunks = re.split(r"(?<=[。!?？!；;])\s*", text)
    cur = ""
    for c in chunks:
        cur += c
        if len(cur) >= 18:
            parts.append(cur.strip())
            cur = ""
    if cur.strip():
        parts.append(cur.strip())
    return [p for p in parts if p]


def _duration(chunk: Path) -> float:
    # 经验值: 每个切片 60s, 由 _slice_audio 控制
    return 60.0


def _approx_duration_of_lines(lines: list[dict]) -> float:
    if not lines:
        return 0.0
    last = lines[-1]
    return float(last.get("to", 0)) - float(last.get("from", 0))
