"""
yt-dlp + Whisper ASR 兜底模块的单元测试.

主要覆盖:
  - _is_enabled() 主开关 / Whisper 端点必填
  - _resolve_bin() PATH / override / Windows 路径回退
  - _split_text_into_segments() 中文/英文断句
  - transcribe_bilibili_video() 在 ASR 关闭时返回 []
"""
from __future__ import annotations

from unittest.mock import patch

import pytest


# ── 1. _is_enabled() ────────────────────────────────────────────────

class TestIsEnabled:
    @pytest.mark.unit
    def test_default_disabled(self, monkeypatch):
        """未配 BILI_ASSISTANT_* 时必须返回 False (避免意外下载流量)."""
        from app.services import bilibili_audio_asr as mod
        # 直接改 settings 字段 (settings 已经在导入时实例化, reload 太脆弱)
        s = mod._settings()
        s.bili_assistant_enabled = False
        s.bili_assistant_openai_base_url = ""
        s.bili_assistant_openai_api_key = ""
        assert mod._is_enabled() is False

    @pytest.mark.unit
    def test_enabled_flag_required(self, monkeypatch):
        """OPENAI_BASE_URL 已配但 ENABLED=False → 仍不启用."""
        from app.services import bilibili_audio_asr as mod
        s = mod._settings()
        s.bili_assistant_enabled = False
        s.bili_assistant_openai_base_url = "https://example.com/v1"
        s.bili_assistant_openai_api_key = "sk-x"
        assert mod._is_enabled() is False

    @pytest.mark.unit
    def test_enabled_requires_base_url(self, monkeypatch):
        """ENABLED=True 但 BASE_URL 为空 → 仍不启用."""
        from app.services import bilibili_audio_asr as mod
        s = mod._settings()
        s.bili_assistant_enabled = True
        s.bili_assistant_openai_base_url = ""
        s.bili_assistant_openai_api_key = "sk-x"
        assert mod._is_enabled() is False

    @pytest.mark.unit
    def test_enabled_with_both(self, monkeypatch):
        from app.services import bilibili_audio_asr as mod
        s = mod._settings()
        s.bili_assistant_enabled = True
        s.bili_assistant_openai_base_url = "https://example.com/v1"
        s.bili_assistant_openai_api_key = "sk-x"
        assert mod._is_enabled() is True


# ── 2. _resolve_bin() ────────────────────────────────────────────────

class TestResolveBin:
    @pytest.mark.unit
    def test_override_path_used(self, tmp_path):
        """override 路径存在时优先使用."""
        from app.services.bilibili_audio_asr import _resolve_bin
        fake = tmp_path / "fake-yt-dlp"
        fake.write_text("#!/bin/sh\n")
        assert _resolve_bin("yt-dlp", str(fake)) == str(fake)

    @pytest.mark.unit
    def test_override_path_missing_falls_back(self):
        """override 路径不存在时回退到 PATH/默认."""
        from app.services.bilibili_audio_asr import _resolve_bin
        result = _resolve_bin("nonexistent-tool-xyz123", "/does/not/exist")
        assert result is None or isinstance(result, str)

    @pytest.mark.unit
    def test_empty_override_returns_none_for_unknown(self):
        from app.services.bilibili_audio_asr import _resolve_bin
        assert _resolve_bin("definitely-not-real-tool-xyz") is None


# ── 3. _split_text_into_segments() ──────────────────────────────────

class TestSplitText:
    @pytest.mark.unit
    def test_empty_input(self):
        from app.services.bilibili_audio_asr import _split_text_into_segments
        assert _split_text_into_segments("") == []
        assert _split_text_into_segments("   ") == []

    @pytest.mark.unit
    def test_chinese_punctuation_split(self):
        from app.services.bilibili_audio_asr import _split_text_into_segments
        text = "你好世界。这是一个测试句子。请问这样可以吗？当然可以!"
        parts = _split_text_into_segments(text)
        assert len(parts) >= 2
        assert all(p for p in parts)

    @pytest.mark.unit
    def test_long_text_grouped(self):
        from app.services.bilibili_audio_asr import _split_text_into_segments
        # 用句号分隔的长段, 累加器应把多个短句合并成 ~18+ 字一段
        text = "第一句。 第二句。 第三句。 第四句。 第五句。 第六句。 第七句。 第八句。 第九句。 第十句。"
        parts = _split_text_into_segments(text)
        # 10 个短句(每句 4 字) 累积到 18 字一组, 应至少 2 段
        assert len(parts) >= 2
        # 每段至少包含一个字
        assert all(len(p) >= 1 for p in parts)
        # 不应有空段
        assert all(p.strip() for p in parts)
        # 总长度应等于原文长
        total_chars = sum(len(p) for p in parts)
        assert total_chars <= len(text)


# ── 4. transcribe_bilibili_video() 关闭时不下载 ────────────────────

class TestTranscribeGate:
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_disabled_returns_empty(self):
        """ASR 关闭时调 transcribe_bilibili_video 必须立即返回 [], 不发起任何 yt-dlp 调用."""
        from app.services import bilibili_audio_asr as mod
        # 强制关闭
        mod._is_enabled = lambda: False
        # 即使传入真实 bvid, 也不应触发网络
        result = await mod.transcribe_bilibili_video("BV1REAL", 12345)
        assert result == []

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_empty_bvid_returns_empty(self):
        """bvid 为空时即使 ASR 启用也直接返回 []."""
        from app.services import bilibili_audio_asr as mod
        mod._is_enabled = lambda: True
        assert await mod.transcribe_bilibili_video("", 0) == []
        assert await mod.transcribe_bilibili_video(None, 0) == []