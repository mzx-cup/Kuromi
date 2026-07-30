# yt-dlp + Whisper 兜底字幕 — 配置手册

> 当 B站 CC/AI 字幕都拿不到时, 本服务会自动下载视频音频并调 Whisper 转写.
> 默认关闭 (`BILI_ASSISTANT_ENABLED=False`), 你需要明确开启才会下载视频.

## 1. 准备工具链

### 1.1 安装 yt-dlp

```bash
pip install yt-dlp
# 验证
yt-dlp --version  # 期望: 2025.x.x 或更新
```

### 1.2 安装 ffmpeg

- Windows: `winget install Gyan.FFmpeg` 或从 https://www.gyan.dev/ffmpeg/builds/ 下载
- macOS: `brew install ffmpeg`
- Linux: `sudo apt install ffmpeg`

验证:
```bash
ffmpeg -version
```

## 2. 启动 Whisper 服务 (OpenAI 兼容)

### 2.1 推荐: faster-whisper (本地免费)

```bash
pip install faster-whisper openai-whisper-asr

# 启 OpenAI 兼容 server (默认 0.0.0.0:8000)
python -m whisper_asr.server --model base --language zh
```

`--model` 选择:
- `tiny`   (39M,  速度最快, 中文精度一般)
- `base`   (74M,  推荐入门)
- `small`  (244M, 较好)
- `medium` (769M, 较好)
- `large-v3` (1550M, 最佳)

> **注意**: 首次启动会自动下载模型, 需联网 5-15 分钟.

### 2.2 备选: OpenAI Whisper API (付费)

不需要本地跑模型, 直接用 OpenAI 服务:

```bash
export BILI_ASSISTANT_OPENAI_BASE_URL=https://api.openai.com/v1
export BILI_ASSISTANT_OPENAI_API_KEY=sk-...
```

## 3. 配置 `.env`

在 `config/.env` 末尾添加:

```env
# 启用 ASR 兜底
BILI_ASSISTANT_ENABLED=True

# Whisper 端点 (本地 faster-whisper)
BILI_ASSISTANT_OPENAI_BASE_URL=http://localhost:8000/v1
BILI_ASSISTANT_OPENAI_API_KEY=any-non-empty-key

# 可选: yt-dlp / ffmpeg 绝对路径 (PATH 没找到时填)
# BILI_ASSISTANT_YTDLP_PATH=D:/tools/yt-dlp.exe
# BILI_ASSISTANT_FFMPEG_PATH=C:/Program Files/ffmpeg/bin/ffmpeg.exe
```

## 4. 验证

### 4.1 单元测试 (无需 yt-dlp)

```bash
python -m pytest tests/services/test_bilibili_audio_asr.py -v
```

### 4.2 端到端 (需要 Whisper + yt-dlp)

```bash
python -c "
import asyncio
from app.services.bilibili_audio_asr import transcribe_bilibili_video, _is_enabled
print('ASR enabled:', _is_enabled())
r = asyncio.run(transcribe_bilibili_video('BV1GJ411x7h7', cid=137649199))
print('transcripts:', len(r))
if r: print('first line:', r[0]['content'][0]['content'][:60])
"
```

> 第一次跑会下载视频 (前 15 分钟约 1-2 MB), 结果落到 `storage/bilibili_audio/<hash>/transcript.json`,
> 后续调用直接读缓存不再下载.

## 5. 关闭兜底

```env
BILI_ASSISTANT_ENABLED=False
```

设置后 `transcribe_bilibili_video()` 立即返回 `[]`, 不会发起任何下载.

## 6. 配额与费用

| 方案 | 单视频成本 | 速度 |
|---|---|---|
| faster-whisper base (本地, CPU) | 免费 | 0.3x 实时 |
| faster-whisper base (本地, GPU) | 免费 | 5-10x 实时 |
| OpenAI Whisper-1 (云) | $0.006/分钟 | 即时 |

> 本服务默认只下载前 15 分钟音频 (`_estimate_max_seconds(0) = 900`),
> 在 [app/services/bilibili_audio_asr.py](../../app/services/bilibili_audio_asr.py) 修改该值即可调到全片.