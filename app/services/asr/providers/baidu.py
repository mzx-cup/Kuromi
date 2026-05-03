"""
百度 ASR Provider

封装现有 main.py 中 /api/socratic/asr 的百度语音识别逻辑。
"""

import logging
import os
import tempfile
import uuid
import subprocess

import httpx

from config import settings
from app.services.asr.types import BaseASRProvider, ASRResult

logger = logging.getLogger("starlearn.asr.baidu")


class BaiduASRProvider(BaseASRProvider):
    provider_id = "baidu-asr"

    async def transcribe(self, audio: bytes, audio_format: str = "webm") -> ASRResult:
        """使用百度语音识别转写音频"""
        if not settings.baidu_asr_api_key or not settings.baidu_asr_secret_key:
            raise RuntimeError("百度 ASR API 密钥未配置")

        temp_dir = tempfile.gettempdir()
        input_file = os.path.join(temp_dir, f"asr_input_{uuid.uuid4().hex}")

        # 根据文件头判断格式
        is_wav = b'RIFF' in audio[:12] and b'WAVE' in audio[:12]
        ext = '.wav' if is_wav else '.webm'
        input_file = input_file + ext

        try:
            with open(input_file, "wb") as f:
                f.write(audio)

            # 获取百度 access token
            token_url = "https://aip.baidubce.com/oauth/2.0/token"
            token_params = {
                "grant_type": "client_credentials",
                "client_id": settings.baidu_asr_api_key,
                "client_secret": settings.baidu_asr_secret_key,
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                token_response = await client.post(token_url, data=token_params)
                token_result = token_response.json()
                access_token = token_result.get("access_token")

                if not access_token:
                    raise RuntimeError(f"获取百度 access token 失败: {token_result}")

                # 转换音频为 PCM 16kHz
                pcm_data = await self._convert_to_pcm(input_file, is_wav)
                if not pcm_data:
                    raise RuntimeError("音频转换失败")

                # 调用百度 ASR
                asr_url = f"https://vop.baidu.com/server_api?dev_pid=1537&token={access_token}"
                asr_response = await client.post(
                    asr_url,
                    data=pcm_data,
                    params={"dev_pid": 1537},
                    headers={"Content-Type": "audio/pcm; rate=16000"},
                )

                asr_result = asr_response.json()
                logger.info("百度 ASR 响应: %s", asr_result)

                if asr_result.get("err_no") == 0:
                    result_list = asr_result.get("result", [])
                    text = result_list[0] if result_list else ""
                    return ASRResult(text=text, language="zh", confidence=1.0)
                else:
                    err_msg = asr_result.get("err_msg", "语音识别失败")
                    raise RuntimeError(f"百度 ASR 错误: {err_msg}")

        finally:
            if os.path.exists(input_file):
                os.remove(input_file)

    async def _convert_to_pcm(self, input_file: str, is_wav: bool) -> bytes | None:
        """将音频转换为 16kHz 单声道 16bit PCM"""
        pcm_data = None

        if is_wav:
            try:
                from scipy.io import wavfile
                from scipy import signal
                import numpy as np
                sample_rate, wav_data = wavfile.read(input_file)
                if sample_rate != 16000:
                    num_samples = int(len(wav_data) * 16000 / sample_rate)
                    wav_data = signal.resample(wav_data, num_samples)
                if len(wav_data.shape) > 1:
                    wav_data = wav_data[:, 0]
                wav_data = wav_data.astype(np.int16)
                pcm_data = wav_data.tobytes()
                return pcm_data
            except Exception as e:
                logger.warning("WAV scipy 处理失败: %s", e)

        # ffmpeg 兜底
        ffmpeg_paths = [
            'ffmpeg', 'ffmpeg.exe',
            r"C:\Apps\Anaconda3\Library\bin\ffmpeg.exe",
            r"C:\Apps\ffmpeg\bin\ffmpeg.exe",
        ]
        ffmpeg_cmd = None
        for fp in ffmpeg_paths:
            if os.path.exists(fp) or fp in ('ffmpeg', 'ffmpeg.exe'):
                try:
                    result = subprocess.run([fp, '-version'], capture_output=True, timeout=5)
                    if result.returncode == 0:
                        ffmpeg_cmd = fp
                        break
                except Exception:
                    continue

        if ffmpeg_cmd:
            cmd = [ffmpeg_cmd, "-y", "-i", input_file,
                   "-ar", "16000", "-ac", "1", "-acodec", "pcm_s16le",
                   "-f", "s16le", "pipe:1"]
            result = subprocess.run(cmd, capture_output=True, timeout=60)
            if result.returncode == 0:
                return result.stdout
            logger.error("ffmpeg 转换失败: %s", result.stderr.decode())

        return None
