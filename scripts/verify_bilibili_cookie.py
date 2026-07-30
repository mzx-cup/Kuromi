"""
verify_bilibili_cookie.py — 一键验证 .env 里的 BILI_COOKIE 能否拿到真实字幕.

用法:
    1. 把 SESSDATA / bili_jct / buvid3 拼成 BILI_COOKIE 写入 config/.env
    2. 重启后端进程 (Settings 在启动时一次性加载 .env)
    3. python scripts/verify_bilibili_cookie.py

退出码:
    0 = 至少一个 bvid 拿到了 cc/ai 字幕
    1 = 全部 bvid 都没拿到字幕 (cookie 失效 / 视频本身无字幕)
    2 = 配置读取失败
"""
from __future__ import annotations

import asyncio
import io
import json
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
# 把项目根加进 sys.path, 这样 `app.services.bilibili` 才能 import
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# 这些是公开课程, 通常带字幕 (用于冒烟)
DEFAULT_BVIDS = [
    "BV1GJ411x7h7",        # python 入门 (教学) — 有字幕元数据, 正文 URL 通常为空
    "BV1uv411q7MV",        # 西游记相关 (有 58 行 CC 字幕, 来自 player/v2)
    "BV1ZZZZZZZZZZ",       # 故意构造的不合法 bvid — 必须返回空
]


def _print_redacted_cookie_status() -> None:
    """打印 cookie 是否配置, 但绝不打印值."""
    try:
        from config import settings
        cookie = (settings.bili_cookie or "").strip()
        print(f"[env] BILI_COOKIE configured: {bool(cookie)}, length={len(cookie)}")
        if cookie:
            # 看看能否解析出 SESSDATA 字段, 提示用户 cookie 是否完整
            has_sessdata = "SESSDATA=" in cookie
            has_bili_jct = "bili_jct=" in cookie
            has_buvid3 = "buvid3=" in cookie
            print(
                f"[env] contains SESSDATA={has_sessdata} bili_jct={has_bili_jct} buvid3={has_buvid3}"
            )
    except Exception as exc:
        print(f"[env] FAILED to read settings: {exc}", file=sys.stderr)
        sys.exit(2)


def _probe_one(bvid: str) -> dict:
    """调 fetch_subtitles, 返回命中摘要."""
    from app.services.bilibili import fetch_subtitles
    try:
        results = fetch_subtitles(bvid)
    except Exception as exc:
        return {"bvid": bvid, "ok": False, "err": repr(exc), "sources": [], "lines": 0}

    sources = []
    total_lines = 0
    sample_lines: list[str] = []
    for r in results:
        src = r.get("source", "?")
        lang = r.get("lang", "")
        n_lines = len(r.get("content") or [])
        sources.append(f"{src}({lang})={n_lines}")
        total_lines += n_lines
        if n_lines and len(sample_lines) < 3:
            sample_lines.extend((it.get("content") or "")[:50] for it in r["content"][:3])

    return {
        "bvid": bvid,
        "ok": total_lines > 0,
        "sources": sources,
        "lines": total_lines,
        "sample": sample_lines,
    }


def main() -> int:
    _print_redacted_cookie_status()
    print()

    bvids = DEFAULT_BVIDS
    any_ok = False
    for bvid in bvids:
        info = _probe_one(bvid)
        status = "✓" if info["ok"] else "✗"
        print(f"[{status}] {bvid}  sources=[{', '.join(info['sources']) or 'empty'}]  lines={info['lines']}")
        if info.get("sample"):
            for line in info["sample"]:
                print(f"      > {line}")
        if info["ok"]:
            any_ok = True
        print()

    print("=" * 60)
    if any_ok:
        print("✅ Cookie 工作正常, B 站字幕已能获取")
        print("   课程学习页 (course-learn.html) 应该能正确显示字幕面板.")
        return 0
    else:
        print("❌ 所有测试 bvid 都未拿到字幕. 可能原因:")
        print("   1. Cookie 已过期或 SESSDATA 解码失败")
        print("   2. 后端进程用的是旧 .env (请重启)")
        print("   3. 这些 bvid 本身就不带 CC/AI 字幕 (开启 BILI_ASSISTANT_ENABLED 走 ASR 兜底)")
        return 1


if __name__ == "__main__":
    sys.exit(main())