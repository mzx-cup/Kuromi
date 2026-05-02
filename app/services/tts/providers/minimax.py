# -*- coding: utf-8 -*-
"""
MiniMax TTS Provider — 完整封装

支持：
  - 非流式合成（generate） — 兼容现有 media_generation.py
  - 流式合成（generate_stream） — 字级时间戳 + SSE 兼容
  - 字级时间戳提取 — MiniMax speech-2.8-hd stream 模式原生支持

OpenMAIC 未启用的能力（stream: false），星识在此全部激活。
"""

from __future__ import annotations

import json
import logging
from typing import AsyncIterator

import httpx

from config import settings
from app.services.tts.types import (
    BaseTTSProvider, TTSConfig, TTSResult,
    TTSStreamChunk, WordTimestamp, SentenceTimestamp,
)

logger = logging.getLogger("starlearn.tts.minimax")


class MiniMaxTTSProvider(BaseTTSProvider):
    provider_id = "minimax-tts"

    VOICES = [
        {"id": "female-shaonv", "name": "青春少女", "desc": "活泼明亮的少女声音"},
        {"id": "female-yujie", "name": "温柔御姐", "desc": "温柔成熟的女性声音"},
        {"id": "female-danyun", "name": "知性女声", "desc": "沉稳知性的女声"},
        {"id": "male-qingshu", "name": "青涩少年", "desc": "年轻活力的男声"},
        {"id": "male-shaoshuai", "name": "磁性男声", "desc": "低沉磁性的男声"},
    ]

    # ---- 非流式合成（兼容现有接口） ----

    async def generate(self, text: str, config: TTSConfig) -> TTSResult:
        """
        非流式 TTS 合成。
        复用现有 media_generation.py 的 generate_tts() 逻辑，
        并从 extra_info 提取 word_count/audio_length 生成估计的字级时间戳。
        """
        from media_generation import generate_tts

        # 调用 MiniMax API 并获取 extra_info
        audio_bytes, extra_info = await self._generate_with_extra(text, config)

        duration_ms = extra_info.get("audio_length", 0)
        if not duration_ms:
            duration_ms = self.estimate_duration_ms(audio_bytes, config.audio_format)

        word_count = extra_info.get("word_count", 0)

        # 生成估计的字级时间戳
        word_timestamps = []
        sentences = []
        if word_count > 0 and duration_ms > 0:
            word_timestamps = self._estimate_word_timestamps(text, word_count, duration_ms)
            sentences = self._estimate_sentence_timestamps(text, duration_ms)

        logger.info(
            "MiniMax TTS (non-streaming): text_len=%d, audio_bytes=%d, "
            "duration_ms=%d, word_count=%d, estimated_timestamps=%d",
            len(text), len(audio_bytes), duration_ms, word_count, len(word_timestamps),
        )
        return TTSResult(
            audio=audio_bytes,
            format=config.audio_format,
            duration_ms=duration_ms,
            word_timestamps=[
                {"word": w.word, "start_ms": w.start_ms, "end_ms": w.end_ms}
                for w in word_timestamps
            ],
            sentences=[
                {"sentence": s.sentence, "start_ms": s.start_ms, "end_ms": s.end_ms}
                for s in sentences
            ],
        )

    async def _generate_with_extra(
        self, text: str, config: TTSConfig
    ) -> tuple[bytes, dict]:
        """调用 MiniMax API 并返回 (audio_bytes, extra_info)"""
        import httpx
        from config import settings

        key = config.api_key or settings.minimax_api_key
        gid = settings.minimax_group_id
        model_name = config.model_id or settings.minimax_tts_model or "speech-2.8-hd"

        url = f"{settings.minimax_api_url}/t2a_v2?GroupId={gid}"
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model_name,
            "text": text.strip(),
            "stream": False,
            "voice_setting": {
                "voice_id": config.voice or "female-shaonv",
                "speed": config.speed,
                "vol": 1.0,
                "pitch": 0,
            },
            "audio_setting": {
                "sample_rate": 32000,
                "bitrate": 128000,
                "format": "mp3",
                "channel": 1,
            },
            "output_format": "hex",
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code != 200:
                raise RuntimeError(
                    f"MiniMax TTS API error HTTP {response.status_code}: {response.text[:200]}"
                )
            data = response.json()

        base_resp = data.get("base_resp", {})
        if base_resp.get("status_code", 0) != 0:
            raise RuntimeError(
                f"MiniMax TTS API error {base_resp.get('status_code')}: "
                f"{base_resp.get('status_msg', 'unknown')}"
            )

        audio_hex = data.get("data", {}).get("audio")
        if not audio_hex:
            raise RuntimeError("MiniMax TTS: no audio data returned")

        audio_bytes = bytes.fromhex(audio_hex)
        extra_info = data.get("extra_info", {})
        return audio_bytes, extra_info

    # ---- 字级时间戳估算 ----

    @staticmethod
    def _estimate_word_timestamps(
        text: str, word_count: int, duration_ms: int
    ) -> list[WordTimestamp]:
        """
        当 MiniMax 不返回原生字级时间戳时，基于字数均分估算。

        中文字符按字均分，英文按词均分。
        """
        timestamps = []
        chars = list(text.replace("\n", "").replace(" ", ""))
        if not chars:
            return timestamps

        char_duration = duration_ms / max(len(chars), 1)

        for i, ch in enumerate(chars):
            if ch in "，。！？、；：""''（）…—《》":
                continue  # 标点不单独计时
            timestamps.append(WordTimestamp(
                word=ch,
                start_ms=int(i * char_duration),
                end_ms=int((i + 1) * char_duration),
            ))

        return timestamps

    @staticmethod
    def _estimate_sentence_timestamps(
        text: str, duration_ms: int
    ) -> list[SentenceTimestamp]:
        """按标点符号分割句子并估算时间"""
        sentences = []
        import re
        parts = re.split(r"([。！？\n])", text)

        current = ""
        for part in parts:
            current += part
            if part in "。！？\n" and current.strip():
                sentences.append(current.strip())
                current = ""

        if current.strip():
            sentences.append(current.strip())

        if not sentences:
            return []

        sent_duration = duration_ms / len(sentences)
        result = []
        for i, sent in enumerate(sentences):
            result.append(SentenceTimestamp(
                sentence=sent,
                start_ms=int(i * sent_duration),
                end_ms=int((i + 1) * sent_duration),
            ))
        return result

    # ---- 流式合成（字级时间戳 + 音频流） ----

    async def generate_stream(
        self, text: str, config: TTSConfig
    ) -> AsyncIterator[TTSStreamChunk]:
        """
        流式 TTS 合成 — 启用 MiniMax speech-2.8-hd 的 stream + subtitle 模式。

        产出的 TTSStreamChunk 包含：
          - audio: 增量 MP3 音频数据
          - word: 当前字的 WordTimestamp（start_ms/end_ms）
          - sentence_index: 句子序号

        前端可据此实现：音频流播放 + 同步字级高亮动画。
        """
        key = config.api_key or settings.minimax_api_key
        gid = settings.minimax_group_id
        model_name = config.model_id or settings.minimax_tts_model or "speech-2.8-hd"

        url = f"{settings.minimax_api_url}/t2a_v2?GroupId={gid}"
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model_name,
            "text": text.strip(),
            "stream": True,              # ← 关键：启用流式
            "voice_setting": {
                "voice_id": config.voice or "female-shaonv",
                "speed": config.speed,
                "vol": 1.0,
                "pitch": 0,
            },
            "audio_setting": {
                "sample_rate": 32000,
                "bitrate": 128000,
                "format": config.audio_format or "mp3",
                "channel": 1,
            },
            "subtitle_enable": True,      # ← 关键：启用字幕/时间戳
            "output_format": "hex",       # 流式模式需要 hex
        }

        logger.info(
            "MiniMax TTS (streaming): text_len=%d, model=%s, voice=%s",
            len(text), model_name, config.voice,
        )

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    raise RuntimeError(
                        f"MiniMax TTS stream error HTTP {response.status_code}: {body[:300]}"
                    )

                sentence_idx = 0
                accumulated_audio = bytearray()
                _had_word_events = False  # 跟踪是否有原生字级时间戳

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue

                    json_str = line[5:].strip()
                    if json_str == "[DONE]":
                        break

                    try:
                        event = json.loads(json_str)
                    except json.JSONDecodeError:
                        logger.warning("MiniMax TTS stream: unparseable line: %s", line[:100])
                        continue

                    # 检查错误
                    base_resp = event.get("base_resp", {})
                    if base_resp.get("status_code", 0) != 0:
                        raise RuntimeError(
                            f"MiniMax TTS stream error {base_resp.get('status_code')}: "
                            f"{base_resp.get('status_msg', 'unknown')}"
                        )

                    chunk = self._parse_stream_event(event, sentence_idx)
                    if chunk.audio:
                        accumulated_audio.extend(chunk.audio)
                    if chunk.word:
                        _had_word_events = True
                        logger.debug(
                            "Word timestamp: '%s' [%d-%dms]",
                            chunk.word.word, chunk.word.start_ms, chunk.word.end_ms,
                        )
                    yield chunk

                    # 句子边界检测
                    if chunk.word and chunk.word.word and chunk.word.word[-1] in "。！？.!?\n":
                        sentence_idx += 1

                # 如果没有原生字级时间戳，用估算值生成
                if accumulated_audio and not _had_word_events:
                    duration_ms = self.estimate_duration_ms(
                        bytes(accumulated_audio), config.audio_format
                    )
                    word_count = len(text.replace("\n", "").replace(" ", ""))
                    if word_count > 0:
                        char_duration = duration_ms / max(word_count, 1)
                        chars = list(text.replace("\n", "").replace(" ", ""))
                        for i, ch in enumerate(chars):
                            if ch not in "，。！？、；：""''（）…—《》":
                                yield TTSStreamChunk(
                                    word=WordTimestamp(
                                        word=ch,
                                        start_ms=int(i * char_duration),
                                        end_ms=int((i + 1) * char_duration),
                                    ),
                                    sentence_index=0,
                                )

                # 最终块
                yield TTSStreamChunk(
                    audio=bytes(accumulated_audio) if accumulated_audio else None,
                    is_final=True,
                )

                logger.info(
                    "MiniMax TTS stream complete: total_audio=%d bytes, sentences=%d",
                    len(accumulated_audio), sentence_idx + 1,
                )

    def _parse_stream_event(self, event: dict, sentence_idx: int) -> TTSStreamChunk:
        """解析 MiniMax 流式 SSE 事件，提取音频 + 字级时间戳"""
        chunk = TTSStreamChunk(sentence_index=sentence_idx)

        # 1. 提取音频（hex 编码）
        audio_hex = event.get("data", {}).get("audio")
        if audio_hex:
            try:
                chunk.audio = bytes.fromhex(audio_hex)
            except ValueError:
                logger.warning("MiniMax TTS: invalid hex audio, skipping")

        # 2. 提取字幕/时间戳
        subtitle = event.get("subtitle", {})
        if subtitle:
            sentences = subtitle.get("sentences", [])
            for sent in sentences:
                words = sent.get("words", [])
                for w in words:
                    # MiniMax 返回: { "word": "你", "start_time": 0.12, "end_time": 0.34 }
                    word_text = w.get("word", "")
                    start_sec = w.get("start_time", 0)
                    end_sec = w.get("end_time", 0)

                    chunk.word = WordTimestamp(
                        word=word_text,
                        start_ms=int(start_sec * 1000),
                        end_ms=int(end_sec * 1000),
                    )

                    # 只返回第一个字的时间戳（调用方循环获取）
                    # 后续字会在下一个 SSE 事件中到达
                    break
                if chunk.word:
                    break

        # 3. 提取 extra_info（音频元数据）
        extra = event.get("extra_info", {})
        if extra:
            if extra.get("audio_format"):
                pass  # 已在配置中指定
            if extra.get("word_count"):
                logger.debug("Word count so far: %s", extra["word_count"])

        return chunk

    async def get_voices(self) -> list[dict]:
        return self.VOICES
