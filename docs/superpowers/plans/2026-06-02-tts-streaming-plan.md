# TTS 音频流式播放 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 index 和 classroom 页面的 TTS 音频从"下载到磁盘再播放"改为后端直返音频数据、前端即时播放，零落盘。

**Architecture:** index 页面使用 `/api/v2/tts/generate` 的 base64 响应直接播放；classroom 页面使用 `/api/v2/tts/stream` 的 SSE 流收集音频块合成 Blob 播放，同时收集逐字时间戳以备后续同步高亮。后端零改动，完全复用已有的 v2 TTS 服务。

**Tech Stack:** Vanilla JS, Fetch API, SSE (text/event-stream), Blob/URL.createObjectURL, sessionStorage

---

## 文件结构

| 文件 | 职责 | 改动类型 |
|------|------|----------|
| `js/socratic-ai.js` | index 页面的 TTS 播放（苏格拉底问答） | 修改 `playQuestionVoice()` |
| `js/classroom.js` | classroom 页面的 TTS 生成与播放 | 修改 `generateTTS()`, `_playAudioUrl()`, `stopAudio()`, 缓存逻辑；新增 `_collectSSEStream()` |

---

### Task 1: socratic-ai.js — playQuestionVoice() 改用 v2 base64 端点

**Files:**
- Modify: `js/socratic-ai.js:170-216`

**背景：** 当前 `playQuestionVoice()` 调用 `/api/socratic/tts`，后端把音频存到 `./audio/` 目录再返回 URL，前端用 `new Audio(url)` 播放。改为调用 `/api/v2/tts/generate`，后端直接返回 base64，前端用 data URI 播放。

**关键变更：**
- 端点：`/api/socratic/tts` → `/api/v2/tts/generate`
- 请求体：`voice` 从整数索引改为字符串 ID
- 响应：从 `audio_url` 改为 `audio_base64` + `format`
- 播放：Data URI 替代文件 URL
- 新增音色整数→字符串映射表

- [ ] **Step 1: 在 socratic-ai.js 顶部添加音色映射表**

在 `let autoPlayEnabled = true;`（第 26 行）之后添加：

```javascript
// v2 TTS 音色映射：整数选中的 voiceId → MiniMax 字符串 voice ID
const SOCRATIC_VOICE_MAP = {
    0: 'female-shaonv',
    1: 'male-qn-qingse',
    2: 'female-yujie',
    3: 'male-qingshu',
    4: 'female-danyun'
};
```

- [ ] **Step 2: 重写 playQuestionVoice() 函数**

将第 170-216 行替换为：

```javascript
async function playQuestionVoice() {
    if (isPlayingAudio || !currentQuestion) return;

    const voiceBtn = document.getElementById('voice-btn');
    voiceBtn.classList.add('playing');
    isPlayingAudio = true;
    updateOrbStatus('AI 播声中...');

    try {
        const voiceId = SOCRATIC_VOICE_MAP[selectedVoiceId] || 'female-shaonv';
        const response = await fetch('/api/v2/tts/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: currentQuestion.text,
                voice: voiceId
            })
        });

        const data = await response.json();
        if (data.audio_base64) {
            const mimeType = 'audio/' + (data.format || 'mp3');
            const audio = new Audio('data:' + mimeType + ';base64,' + data.audio_base64);
            audio.onended = () => {
                voiceBtn.classList.remove('playing');
                isPlayingAudio = false;
                updateOrbStatus('倾听中');
            };
            audio.onerror = () => {
                voiceBtn.classList.remove('playing');
                isPlayingAudio = false;
                updateOrbStatus('倾听中');
                showToast('语音播放失败', 'error');
            };
            await audio.play();
        } else {
            showToast(data.detail || '语音合成失败', 'error');
            voiceBtn.classList.remove('playing');
            isPlayingAudio = false;
        }
    } catch (error) {
        console.error('TTS 播放失败:', error);
        showToast('语音播放失败', 'error');
        voiceBtn.classList.remove('playing');
        isPlayingAudio = false;
    }

    updateOrbStatus('倾听中');
}
```

- [ ] **Step 3: 验证并提交**

```bash
git add js/socratic-ai.js
git commit -m "refactor(socratic): TTS 改用 v2 base64 端点，不再落盘

- 端点从 /api/socratic/tts 改为 /api/v2/tts/generate
- 使用 data URI 直接播放 base64 音频
- 添加音色整数到字符串 ID 的映射表

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: classroom.js — 新增 SSE 流收集方法 _collectSSEStream()

**Files:**
- Modify: `js/classroom.js`（在 `generateTTS()` 方法附近插入新方法）

**背景：** v2 `/api/v2/tts/stream` 端点返回 SSE 流，每个 `event: audio` 携带 hex 编码的音频块，`event: word` 携带逐字时间戳。需要一个方法消费这个 SSE 流，收集所有音频块合成 Blob，同时收集时间戳。

- [ ] **Step 1: 在 generateTTS() 之后添加 _collectSSEStream() 方法**

在 `generateTTS()` 方法结束的 `}` 之后（约第 4240 行）、`showSpeechSyncIndicator()` 之前插入：

```javascript
        /**
         * 从 v2 SSE 流式 TTS 端点收集音频数据。
         * 消费 SSE text/event-stream，提取所有 audio chunk (hex) 和 word timestamp。
         * 返回 Blob 和逐字时间戳数组，供后续播放和同步高亮使用。
         *
         * @param {string} text - 要合成语音的文本
         * @param {string} voiceId - MiniMax 音色字符串 ID (如 'female-yujie')
         * @param {number} speed - 语速 (0.5 ~ 2.0)
         * @returns {Promise<{success: boolean, audioBlob?: Blob, blobUrl?: string, wordTimestamps?: Array, error?: string}>}
         */
        async _collectSSEStream(text, voiceId, speed = 1.0) {
            const controller = new AbortController();
            // 保存到实例，stopAudio() 时可以通过它中断流
            this._activeStreamController = controller;

            try {
                const response = await fetch('/api/v2/tts/stream', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        text: text,
                        voice: voiceId,
                        speed: speed
                    }),
                    signal: controller.signal
                });

                if (!response.ok) {
                    const errData = await response.json().catch(() => ({}));
                    return { success: false, error: errData.detail || 'TTS stream request failed' };
                }

                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                const audioChunks = [];      // Uint8Array[]
                const wordTimestamps = [];   // {word, start_ms, end_ms}[]
                let buffer = '';

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n');
                    // 最后一行可能不完整，保留到下次循环
                    buffer = lines.pop() || '';

                    let currentEvent = '';
                    for (const line of lines) {
                        if (line.startsWith('event: ')) {
                            currentEvent = line.slice(7).trim();
                        } else if (line.startsWith('data: ') && currentEvent) {
                            const dataStr = line.slice(6);
                            try {
                                const data = JSON.parse(dataStr);
                                if (currentEvent === 'audio' && data.hex) {
                                    const bytes = new Uint8Array(data.hex.length / 2);
                                    for (let i = 0; i < data.hex.length; i += 2) {
                                        bytes[i / 2] = parseInt(data.hex.substring(i, i + 2), 16);
                                    }
                                    audioChunks.push(bytes);
                                } else if (currentEvent === 'word') {
                                    wordTimestamps.push({
                                        word: data.word,
                                        start_ms: data.start_ms,
                                        end_ms: data.end_ms,
                                        sentence_index: data.sentence_index
                                    });
                                }
                                // 'done' event: stream finished, nothing extra to extract
                                // 'error' event: stream error
                                if (currentEvent === 'error') {
                                    return { success: false, error: data.message || 'TTS stream error' };
                                }
                            } catch (e) {
                                // skip unparseable lines
                            }
                            currentEvent = '';
                        }
                    }
                }

                if (audioChunks.length === 0) {
                    return { success: false, error: 'No audio data received from stream' };
                }

                // 拼接所有音频块为完整 Blob
                const totalLength = audioChunks.reduce((sum, chunk) => sum + chunk.length, 0);
                const combined = new Uint8Array(totalLength);
                let offset = 0;
                for (const chunk of audioChunks) {
                    combined.set(chunk, offset);
                    offset += chunk.length;
                }
                const audioBlob = new Blob([combined], { type: 'audio/mp3' });

                // 创建 blob URL（stopAudio 时通过 revokeObjectURL 释放）
                const blobUrl = URL.createObjectURL(audioBlob);
                // 保存引用以便后续清理
                this._activeBlobUrl = blobUrl;

                console.log('[Classroom] SSE stream collected:',
                    audioChunks.length, 'chunks,',
                    totalLength, 'bytes,',
                    wordTimestamps.length, 'word timestamps');
                return {
                    success: true,
                    audioBlob: audioBlob,
                    blobUrl: blobUrl,
                    wordTimestamps: wordTimestamps
                };
            } catch (e) {
                if (e.name === 'AbortError') {
                    return { success: false, error: 'Stream aborted' };
                }
                console.error('[Classroom] SSE stream error:', e);
                return { success: false, error: e.message };
            } finally {
                this._activeStreamController = null;
            }
        }
```

- [ ] **Step 2: 提交**

```bash
git add js/classroom.js
git commit -m "feat(classroom): 新增 _collectSSEStream() SSE 流收集方法

消费 /api/v2/tts/stream 的 SSE 流，收集 hex 音频块合成 Blob，
同时提取逐字时间戳。支持 AbortController 中断。

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: classroom.js — 重写 generateTTS() 使用 v2 流式端点

**Files:**
- Modify: `js/classroom.js:4210-4240`

**背景：** `generateTTS()` 当前调用 `/api/socratic/tts` 返回 `{audioUrl}`。需要改为调用新的 `_collectSSEStream()`。v2 不需要整数 voice index，直接用字符串 voice ID。

- [ ] **Step 1: 重写 generateTTS()**

将第 4210-4240 行替换为：

```javascript
        async generateTTS(text, voiceId = null, speed = 1.0) {
            // v2 端点使用字符串音色 ID，不再需要整数索引映射
            const voice = voiceId || TTS_CONFIG.voice;
            // MINIMAX_VOICES 的 key 就是字符串 ID，验证其存在
            const validVoice = MINIMAX_VOICES[voice] ? voice : 'female-yujie';

            try {
                // 尝试流式 SSE 端点
                const result = await this._collectSSEStream(text, validVoice, speed);
                if (result.success && result.blobUrl) {
                    console.log('[Classroom] TTS stream success:', result.blobUrl, result.wordTimestamps?.length, 'word timestamps');
                    return {
                        success: true,
                        audioUrl: result.blobUrl,
                        wordTimestamps: result.wordTimestamps || []
                    };
                }
                console.warn('[Classroom] SSE stream failed, falling back to base64:', result.error);
            } catch (e) {
                console.warn('[Classroom] SSE stream exception, falling back to base64:', e);
            }

            // 降级：v2 base64 端点
            try {
                const response = await fetch('/api/v2/tts/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        text: text,
                        voice: validVoice,
                        speed: speed
                    })
                });
                const data = await response.json();
                if (data.audio_base64) {
                    const mimeType = 'audio/' + (data.format || 'mp3');
                    const dataUri = 'data:' + mimeType + ';base64,' + data.audio_base64;
                    console.log('[Classroom] TTS base64 fallback success');
                    return {
                        success: true,
                        audioUrl: dataUri,
                        wordTimestamps: data.word_timestamps || []
                    };
                }
                return { success: false, error: data.detail || 'TTS generation failed' };
            } catch (e) {
                console.error('[Classroom] TTS base64 fallback error:', e);
                return { success: false, error: e.message };
            }
        }
```

- [ ] **Step 2: 提交**

```bash
git add js/classroom.js
git commit -m "refactor(classroom): generateTTS() 改用 v2 流式/降级 base64 端点

主路径：SSE 流式 → Blob → blob URL
降级路径：/generate → base64 → data URI
不再使用 /api/socratic/tts，不再依赖整数 voice index。

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: classroom.js — 更新 _playAudioUrl() 支持 blob URL 生命周期管理

**Files:**
- Modify: `js/classroom.js:6354-6378`

**背景：** `_playAudioUrl()` 现在接收的 URL 可能是 `blob:` URL 或 `data:` URI。需要在这些情况下正确处理，确保 `stopAudio()` 时能清理 blob URL。

- [ ] **Step 1: 更新 _playAudioUrl()**

将第 6354-6378 行替换为：

```javascript
        _playAudioUrl(url, scene) {
            if (!this.audioPlayer) return;
            // 如果用户已暂停，不要开始播放
            if (!this.isPlaying) {
                this.speechSync.style.display = 'none';
                return;
            }
            this.speechSync.style.display = 'flex';
            this.audioPlayer.load();
            this.audioPlayer.src = url;
            this.audioPlayer.play().catch(() => this.fallbackTTS(scene));
            this.audioPlayer.onended = () => {
                this.speechSync.style.display = 'none';
                const playBtn = document.getElementById('playback-play-btn');
                const playIcon = playBtn?.querySelector('i');
                if (playBtn) {
                    playBtn.classList.remove('playing');
                    playBtn.title = '播放';
                }
                if (playIcon) playIcon.className = 'fas fa-play';
                // Clean up blob URL after playback completes
                if (url && url.startsWith('blob:')) {
                    URL.revokeObjectURL(url);
                }
                if (this.isPlaying && this.currentIndex < this.scenes.length - 1) {
                    setTimeout(() => this.nextScene(), 800);
                }
            };
        }
```

- [ ] **Step 2: 提交**

```bash
git add js/classroom.js
git commit -m "fix(classroom): _playAudioUrl() 支持 blob URL 清理

播放结束后自动 revokeObjectURL 释放内存。

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: classroom.js — 更新 stopAudio() 中断流并清理 blob URL

**Files:**
- Modify: `js/classroom.js:6471-6500`

**背景：** `stopAudio()` 需要中断正在进行的 SSE 流（通过 AbortController），并清理未播放完的 blob URL，防止内存泄漏。

- [ ] **Step 1: 更新 stopAudio()**

将第 6471-6500 行替换为：

```javascript
        stopAudio() {
            // Abort any in-flight SSE stream
            if (this._activeStreamController) {
                try { this._activeStreamController.abort(); } catch (e) {}
                this._activeStreamController = null;
            }
            // Clean up blob URL from current/last stream
            if (this._activeBlobUrl) {
                try { URL.revokeObjectURL(this._activeBlobUrl); } catch (e) {}
                this._activeBlobUrl = null;
            }
            if (this.audioPlayer) {
                // Remove event listeners first to prevent fallback TTS from firing when we clear src
                this.audioPlayer.onloadedmetadata = null;
                this.audioPlayer.onplay = null;
                this.audioPlayer.onended = null;
                this.audioPlayer.onerror = null;
                this.audioPlayer.pause();
                // Do NOT set src to empty string — it triggers MEDIA_ERR_SRC_NOT_SUPPORTED
            }
            if (window.speechSynthesis) window.speechSynthesis.cancel();
            if (this.openmaicPlayer) this.openmaicPlayer.stop({ keepSlide: true });
            if (this.speechSync) this.speechSync.style.display = 'none';
            // Clear spotlight when audio stops
            this.clearSpotlight();
            // Reset pause state
            this.audioPausedBefore = false;
            // Deactivate slide mode when audio stops
            if (this.teacherArea) this.teacherArea.classList.remove('slide-mode');
            // Reset play button state
            const playBtn = document.getElementById('playback-play-btn');
            const playIcon = playBtn?.querySelector('i');
            if (playBtn) {
                playBtn.classList.remove('playing');
                playBtn.title = '播放';
            }
            if (playIcon) playIcon.className = 'fas fa-play';
        }
```

- [ ] **Step 2: 提交**

```bash
git add js/classroom.js
git commit -m "fix(classroom): stopAudio() 增加 SSE 流中断和 blob URL 清理

- AbortController 中断进行中的 SSE 流
- revokeObjectURL 释放未播放完的 blob URL

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: classroom.js — 更新缓存逻辑适配 base64 数据

**Files:**
- Modify: `js/classroom.js:4286-4381`
  - `_scheduleNextScenePreload()`
  - `_preloadSceneTTS()`
  - `_ensureSceneTTSCached()`

**背景：** 旧缓存逻辑假设 `audioUrl` 是服务器文件 URL（如 `/audio/xxx.mp3`），可以直接存到 sessionStorage 并跨会话复用。新逻辑下 `audioUrl` 可能是 `blob:` URL（不可跨会话复用）或 `data:` URI（可以）。需要调整：
- 缓存时保存 base64 原始数据而非 blob URL
- `_ensureSceneTTSCached()` 从 base64 缓存重建 blob URL
- 预加载条件检查需适配

- [ ] **Step 1: 更新 _scheduleNextScenePreload() 的缓存检查**

将第 4300-4301 行替换为：

```javascript
            // 如果已经缓存，不需要再预加载（检查 scene.audioBase64 而非 audioUrl）
            if (scene.audioBase64 || this.courseData.tts_audio_base64?.[String(nextScene.id)]) return;
```

- [ ] **Step 2: 更新 _preloadSceneTTS() 缓存 base64 而非 URL**

将第 4310-4345 行替换为：

```javascript
        async _preloadSceneTTS(scene) {
            const text = this.getSceneSpeechText(scene);
            if (!text) return;
            const sceneId = String(scene.id);

            // 如果已经在缓存中，跳过（检查 scene.audioBase64 而非 audioUrl）
            if (scene.audioBase64 || this.courseData.tts_audio_base64?.[sceneId]) return;

            // 如果该场景正在预加载中，复用 Promise
            if (this._ttsPreloadPromises.has(sceneId)) {
                return this._ttsPreloadPromises.get(sceneId);
            }

            const voiceId = this.ttsConfig?.voice || TTS_CONFIG.voice;
            const speed = this.ttsConfig?.speed || TTS_CONFIG.speed;

            const preloadPromise = (async () => {
                try {
                    const result = await this.generateTTS(text, voiceId, speed);
                    if (result.success && result.audioUrl) {
                        // 提取 base64 数据用于持久化缓存（blob URL 不可跨会话复用）
                        let base64Data = null;
                        if (result.audioUrl.startsWith('data:')) {
                            // data URI: data:audio/mp3;base64,<data>
                            const commaIdx = result.audioUrl.indexOf(',');
                            if (commaIdx >= 0) base64Data = result.audioUrl.substring(commaIdx + 1);
                        }
                        // 内存中保留 blob URL（本次会话可用）
                        scene.audioUrl = result.audioUrl;
                        scene.audioBase64 = base64Data;
                        if (!this.courseData.tts_audio_urls) this.courseData.tts_audio_urls = {};
                        this.courseData.tts_audio_urls[sceneId] = result.audioUrl;
                        // 持久化 base64 数据到 sessionStorage
                        if (base64Data) {
                            if (!this.courseData.tts_audio_base64) this.courseData.tts_audio_base64 = {};
                            this.courseData.tts_audio_base64[sceneId] = base64Data;
                        }
                        try {
                            sessionStorage.setItem('classroomData', JSON.stringify(this.courseData));
                        } catch (e) {
                            // sessionStorage 可能满了，清除旧的 blob URL 条目再试
                            if (this.courseData.tts_audio_urls) {
                                const oldUrls = this.courseData.tts_audio_urls;
                                this.courseData.tts_audio_urls = {};
                                try { sessionStorage.setItem('classroomData', JSON.stringify(this.courseData)); } catch (e2) {}
                                this.courseData.tts_audio_urls = oldUrls;
                            }
                        }
                        console.log('[Classroom] TTS preloaded for scene', scene.id, ':', result.audioUrl?.substring(0, 50) + '...');
                    }
                } catch (e) {
                    console.warn('[Classroom] TTS preload failed for scene', scene.id, e);
                }
            })();

            this._ttsPreloadPromises.set(sceneId, preloadPromise);
            return preloadPromise;
        }
```

- [ ] **Step 3: 更新 _ensureSceneTTSCached() 从 base64 重建 blob URL**

将第 4348-4381 行替换为：

```javascript
        async _ensureSceneTTSCached(scene) {
            const sceneId = String(scene.id);
            // 1. 检查内存缓存（blob URL 或 data URI）
            if (scene.audioUrl) return scene.audioUrl;
            if (this.courseData.tts_audio_urls?.[sceneId]) {
                scene.audioUrl = this.courseData.tts_audio_urls[sceneId];
                return scene.audioUrl;
            }

            // 2. 从持久化 base64 缓存恢复（转换回 data URI，因为 blob URL 已过期）
            if (scene.audioBase64 || this.courseData.tts_audio_base64?.[sceneId]) {
                const b64 = scene.audioBase64 || this.courseData.tts_audio_base64[sceneId];
                if (b64) {
                    const dataUri = 'data:audio/mp3;base64,' + b64;
                    scene.audioUrl = dataUri;
                    return dataUri;
                }
            }

            const text = this.getSceneSpeechText(scene);
            if (!text) return null;

            // 3. 如果该场景正在后台预加载中，等待它完成
            if (this._ttsPreloadPromises.has(sceneId)) {
                await this._ttsPreloadPromises.get(sceneId);
                return scene.audioUrl || this.courseData.tts_audio_urls?.[sceneId] || null;
            }

            // 4. 否则立即生成（插队）
            this.updateTeacherStatus('正在合成语音...', false);
            const voiceId = this.ttsConfig?.voice || TTS_CONFIG.voice;
            const speed = this.ttsConfig?.speed || TTS_CONFIG.speed;
            const result = await this.generateTTS(text, voiceId, speed);
            if (result.success && result.audioUrl) {
                scene.audioUrl = result.audioUrl;
                let base64Data = null;
                if (result.audioUrl.startsWith('data:')) {
                    const commaIdx = result.audioUrl.indexOf(',');
                    if (commaIdx >= 0) base64Data = result.audioUrl.substring(commaIdx + 1);
                }
                scene.audioBase64 = base64Data;
                if (!this.courseData.tts_audio_urls) this.courseData.tts_audio_urls = {};
                this.courseData.tts_audio_urls[sceneId] = result.audioUrl;
                if (base64Data) {
                    if (!this.courseData.tts_audio_base64) this.courseData.tts_audio_base64 = {};
                    this.courseData.tts_audio_base64[sceneId] = base64Data;
                }
                try {
                    sessionStorage.setItem('classroomData', JSON.stringify(this.courseData));
                } catch (e) {}
                return result.audioUrl;
            }
            return null;
        }
```

- [ ] **Step 4: 提交**

```bash
git add js/classroom.js
git commit -m "refactor(classroom): 缓存逻辑适配 base64 数据存储

- 缓存保存 base64 原始数据（非 blob URL，跨会话可复用）
- _ensureSceneTTSCached() 从 base64 缓存重建 data URI
- sessionStorage 超限时优雅降级

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: 端到端验证

**Files:** 无修改，仅验证

- [ ] **Step 1: 验证后端 v2 端点可用**

```bash
curl -s -X POST http://localhost:8000/api/v2/tts/generate \
  -H "Content-Type: application/json" \
  -d '{"text":"你好，测试一下","voice":"female-shaonv","speed":1.0}' \
  | python -c "import sys,json; d=json.load(sys.stdin); print('OK, base64 len:', len(d.get('audio_base64','')))"
```
Expected: `OK, base64 len: <large number>`

- [ ] **Step 2: 验证 SSE 流式端点可用**

```bash
curl -s -X POST http://localhost:8000/api/v2/tts/stream \
  -H "Content-Type: application/json" \
  -d '{"text":"测试流式","voice":"female-shaonv","speed":1.0}' \
  | head -20
```
Expected: 看到 `event: audio\ndata: {"hex":"...` 格式的 SSE 事件

- [ ] **Step 3: 浏览器手动测试**

1. 打开 index 页面，点击语音播放按钮 → 确认音频正常播放
2. 打开 classroom 页面，开始一个课程 → 确认 TTS 语音正常播放
3. 在 classroom 中快速切换场景 → 确认前一个音频停止，新音频正常播放
4. 查看浏览器 Network 标签 → 确认没有对 `/audio/` 路径的请求（说明不再落盘）

- [ ] **Step 4: 提交最终验证结果**

```bash
git add -A
git commit -m "test: 端到端验证 TTS 流式播放通过

- index 页面 base64 播放正常
- classroom 页面 SSE 流式播放正常
- 场景切换时音频正确中断
- 不再对 /audio/ 路径发起请求

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## 任务依赖图

```
Task 1 (socratic-ai.js base64)  ──┐
                                   ├── 无依赖，可并行
Task 2 (classroom SSE collect) ──┘
                                   │
Task 3 (classroom generateTTS) ────┤ 依赖 Task 2
                                   │
Task 4 (classroom _playAudioUrl) ──┤ 依赖 Task 3
Task 5 (classroom stopAudio) ──────┤ 依赖 Task 3
Task 6 (classroom 缓存适配) ───────┤ 依赖 Task 3
                                   │
Task 7 (端到端验证) ───────────────┘ 依赖 Task 1-6
```

---

## 风险与缓解

| 风险 | 缓解 |
|------|------|
| SSE 流解析在浏览器兼容性问题 | ReadableStream + TextDecoder 在现代浏览器中广泛支持；降级到 base64 端点 |
| blob URL 在 sessionStorage 缓存恢复时失效 | 缓存 base64 数据而非 blob URL，恢复时重建 data URI |
| 大段文本导致 sessionStorage 超限 | 单个场景音频 < 500KB；超限时 catch 静默跳过缓存 |
| `_playTTSWithVoice()` 也调用了 `generateTTS()` | 该方法在第 6380 行，同样受益于新的 `generateTTS()` 返回值，返回的 `audioUrl` 可能是 blob URL 或 data URI，都兼容现有 `audioPlayer.src = url` |
