# TTS 音频流式播放 — 设计文档

**日期**: 2026-06-02
**状态**: 已确认

---

## 目标

将 index 页面和 classroom 页面的 TTS 音频播放从"先下载到服务器磁盘 → 前端再下载到本地 → 播放"的两步模式，改为"后端直接返回音频数据 → 前端即时播放"的零落盘模式。

## 当前问题

```
POST /api/socratic/tts → 后端调 MiniMax API → 保存 mp3 到 ./audio/ 磁盘
                       → 返回 { audio_url: "/audio/xxx.mp3" }
GET /audio/xxx.mp3     → 浏览器下载文件 → 播放
```

- 音频必须先写到服务器磁盘，产生文件堆积
- 前端需要两次 HTTP 往返才能开始播放
- 无字音同步能力

## 设计决策

| 决策项 | 选择 |
|--------|------|
| 方案 | C — 混合方案：index 用 base64，classroom 用流式 SSE |
| 后端 | 零改动，复用已有的 `/api/v2/tts/generate` 和 `/api/v2/tts/stream` |
| 旧端点 | `/api/socratic/tts` 保留不动，兼容其他可能的使用方 |
| 音频格式 | 统一 `audio/mpeg` (MP3)，MediaSource 兼容性最好 |
| 降级策略 | MediaSource 不支持时降级到 base64 Blob；最终回退到浏览器 SpeechSynthesis |

---

## 架构：改造后数据流

### index 页面 — base64 路径

```
POST /api/v2/tts/generate { text, voice_id: "female-tianmei" }
    ↓
{ audio_base64: "//u...", format: "mp3", duration_ms: 5000 }
    ↓
new Audio("data:audio/mp3;base64,...") → 即时播放
```

- 改动文件：`js/socratic-ai.js`
- 改动方法：`playQuestionVoice()`
- 预估改动量：~30 行

### classroom 页面 — 流式 SSE 路径

```
POST /api/v2/tts/stream { text, voice_id: "female-yujie", speed: 1.0 }
    ↓
SSE stream:
  event: audio  → data: base64_chunk → 追加到缓冲区
  event: word   → data: {word, start_ms, end_ms} → 记录时间戳
  event: done   → 组装 Blob → URL.createObjectURL → audioPlayer 播放
                  + 启动字音同步定时器
```

- 改动文件：`js/classroom.js`
- 改动方法：`generateTTS()`, `_playAudioUrl()`, 新增 `_streamingTTS()`
- 预估改动量：~150 行

### 降级链（classroom）

```
1. 尝试 SSE 流式 (fetch + ReadableStream 消费 SSE)
   ↓ 浏览器不支持 / 网络错误
2. 降级: fetch /api/v2/tts/generate → base64 → Blob → 播放
   ↓ 也失败
3. 回退: window.speechSynthesis (现有逻辑保留)
```

---

## 各部分改动详情

### 1. `js/socratic-ai.js` — playQuestionVoice()

| 项目 | 改前 | 改后 |
|------|------|------|
| 端点 | `POST /api/socratic/tts` | `POST /api/v2/tts/generate` |
| 请求体 | `{ text, voice_id: 0 }` (整数索引) | `{ text, voice_id: "female-tianmei" }` (字符串 ID) |
| 响应 | `data.audio_url` | `data.audio_base64` + `data.format` |
| 播放 | `new Audio(data.audio_url)` | `new Audio("data:audio/" + data.format + ";base64," + data.audio_base64)` |

音色映射表写在 JS 中（与现有 VOICE_CONFIGS 类似）：

```javascript
const VOICE_ID_MAP = {
    0: 'female-tianmei',    // 晓雅
    1: 'male-qn-qingse',    // 云起
    2: 'female-zhiyu',      // 知遇
    3: 'male-jieshuo',      // 解说
    4: 'female-yujie',      // 御姐
};
```

### 2. `js/classroom.js` — generateTTS() + _playAudioUrl()

#### generateTTS() 改造

- 调用改为 `POST /api/v2/tts/stream`
- 用 `fetch()` + `ReadableStream.getReader()` 消费 SSE 响应
- 解析 SSE 事件：`audio` 事件收集 base64 chunk；`word` 事件收集时间戳
- 所有 chunk 收完后组装 `Blob`，通过 `URL.createObjectURL()` 创建播放 URL
- 返回 `{ success, audioUrl: blobUrl, wordTimestamps }` 

#### _playAudioUrl() 改造

- 不再需要改动核心逻辑（仍然是设置 `audioPlayer.src = url`）
- 增加字音同步：播放开始后，用 `setInterval` 对比 `audioPlayer.currentTime` 和 word timestamps，触发高亮

#### 缓存适配

- 现有 `sessionStorage` 缓存存 URL 字符串，改为存 base64 数据
- 单个场景音频预估 < 500KB，sessionStorage 容量（通常 5-10MB）足够

#### 音色映射

classroom.js 已有的 `MINIMAX_VOICES` 映射表包含字符串 ID（如 `'female-yujie'`），与 v2 端点兼容，无需额外映射。

### 3. 后端 — 零改动

- `/api/v2/tts/generate` — 已存在，返回 `{ audio_base64, format, duration_ms }`
- `/api/v2/tts/stream` — 已存在，SSE 流返回 audio chunk + word timestamp
- `/api/socratic/tts` — 保留不删

---

## 改动清单

| 文件 | 改动类型 | 预估行数 | 风险 |
|------|----------|---------|------|
| `js/socratic-ai.js` | 修改 `playQuestionVoice()` | ~30 行 | 低 |
| `js/classroom.js` | 修改 `generateTTS()`, `_playAudioUrl()`，新增 `_streamingTTS()` | ~150 行 | 中（SSE 解析 + 缓存格式变更） |
| 后端 | 无改动 | 0 行 | 无 |

---

## 边界情况与约束

- **网络中断**：SSE 流中断时，已收到的 chunk 丢弃，触发放回退链
- **大文本分段**：classroom 场景文本通常 < 500 字，单个 SSE 连接足够；特殊长文本由后端分段
- **并发播放**：切换场景时 `stopAudio()` 中断当前 SSE 连接（`AbortController`），启动新的
- **浏览器兼容**：MediaSource 在 Chrome 23+ / Firefox 42+ / Safari 8+ / Edge 12+ 均支持
- **sessionStorage 超限**：如果 base64 数据超过 5MB，跳过缓存直接每次生成

---

## 不做的事情

- 不删除旧端点 `/api/socratic/tts`
- 不清理服务器上已有的 `./audio/` 历史文件
- 不改动其他页面的 TTS 调用（如 `courses.js`、`course-learn.js`）——后续可以按需迁移
