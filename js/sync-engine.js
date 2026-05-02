/**
 * SyncEngine — 通用音画同步引擎
 *
 * 移植自 OpenMAIC lib/playback/engine.ts 的 PlaybackEngine 核心逻辑。
 *
 * 核心机制：
 * - 动作级同步：audio.onended 推进到下一个 Action
 * - 字级动画：StreamingTTSPlayer 的 timeupdate 驱动逐字高亮（星识增强）
 * - 视觉动作 fire-and-forget (queueMicrotask)，白板动作 await 动画延迟
 * - TTS 不可用时自动回退到阅读计时器
 *
 * 状态机: idle → playing → paused → playing → completed
 *
 * 星识增强（OpenMAIC 无）:
 * - StreamingTTSPlayer: 流式 TTS + 字级时间戳 → 实时字级高亮
 * - _playAudioStream: SSE 流式接收音频块 + 词时间戳
 */

class SyncEngine {
  /**
   * @param {Array<Object>} actions - 初始 Action 数组
   * @param {Object} options - 回调配置
   * @param {Function} options.onActionStart - 每个 Action 开始时回调
   * @param {Function} options.onSpeechStart - Speech Action 开始播放时回调
   * @param {Function} options.onWordHighlight - 字级高亮回调(word, startMs, endMs) — 星识增强
   * @param {Function} options.onVisualFire - 视觉 Action 触发时回调 (spotlight/laser/wb_*)
   * @param {Function} options.onComplete - 所有 Action 消费完毕后回调
   * @param {Function} options.onError - 错误回调
   * @param {boolean} options.useStreamingTTS - 是否启用流式 TTS + 字级时间戳（默认 true）
   */
  constructor(actions, options = {}) {
    /** @type {Array<Object>} */
    this.actions = actions || [];
    this.currentIndex = 0;
    this.state = 'idle'; // idle | playing | paused | completed

    this.onActionStart = options.onActionStart || (() => {});
    this.onSpeechStart = options.onSpeechStart || (() => {});
    this.onWordHighlight = options.onWordHighlight || (() => {}); // 星识增强
    this.onVisualFire = options.onVisualFire || (() => {});
    this.onComplete = options.onComplete || (() => {});
    this.onError = options.onError || (() => {});

    /** @type {HTMLAudioElement} */
    this.audioElement = new Audio();

    // TTS API endpoint
    this.ttsEndpoint = options.ttsEndpoint || '/api/v2/tts/generate';
    this.ttsStreamEndpoint = options.ttsStreamEndpoint || '/api/v2/tts/stream';

    // TTS 配置
    this.ttsConfig = options.ttsConfig || this._loadTTSConfig();

    // 流式 TTS 开关（默认启用）
    this.useStreamingTTS = options.useStreamingTTS !== false;

    // 字级时间戳积累
    /** @type {Array<{word: string, start_ms: number, end_ms: number}>} */
    this._wordTimestamps = [];
    this._wordHighlightTimer = null;
  }

  // ---- Actions 管理 ----

  /** 追加 Action 到队列末尾（用于 SSE 流持续推送） */
  appendActions(newActions) {
    if (Array.isArray(newActions)) {
      this.actions.push(...newActions);
      // 如果引擎空闲且未开始，自动启动
      if (this.state === 'idle' && this.actions.length > 0) {
        this.start();
      }
    }
  }

  /** 清空 Actions 队列 */
  clearActions() {
    this.actions = [];
    this.currentIndex = 0;
  }

  // ---- 状态控制 ----

  start() {
    if (this.state === 'playing') return;
    this.state = 'playing';
    this.processNext();
  }

  pause() {
    this.state = 'paused';
    this.audioElement.pause();
  }

  resume() {
    if (this.state !== 'paused') return;
    this.state = 'playing';
    this.audioElement.play()
      .then(() => this.processNext())
      .catch(() => this.processNext());
  }

  stop() {
    this.state = 'completed';
    this.audioElement.pause();
    this.audioElement.src = '';
  }

  /** 跳转到指定 Action 索引 */
  skipTo(index) {
    this.currentIndex = Math.max(0, Math.min(index, this.actions.length));
    this.audioElement.pause();
    this.audioElement.src = '';
    if (this.state === 'playing') {
      this.processNext();
    }
  }

  // ---- 核心循环 ----

  async processNext() {
    if (this.state !== 'playing') return;

    if (this.currentIndex >= this.actions.length) {
      this.state = 'completed';
      this.onComplete();
      return;
    }

    const action = this.actions[this.currentIndex];
    this.currentIndex++;
    this.onActionStart(action);

    try {
      switch (action.type) {
        // ---- Speech ----
        case 'speech':
          await this._handleSpeech(action);
          break;

        // ---- Fire-and-forget visual actions ----
        case 'spotlight':
        case 'laser':
          this.onVisualFire(action);
          queueMicrotask(() => this.processNext());
          break;

        // ---- Text-only (no speech) ----
        case 'text':
          this.onVisualFire(action);
          queueMicrotask(() => this.processNext());
          break;

        // ---- Whiteboard actions (with animation delay) ----
        default:
          if (action.type && action.type.startsWith('wb_')) {
            await this._handleWhiteboard(action);
          } else if (action.type === 'play_media') {
            this.onVisualFire(action);
            await this._delay(1000); // 等待媒体加载
          } else if (action.type === 'function_call') {
            // Function Calling 结果已被后端预处理，前端只需展示
            this.onVisualFire(action);
            queueMicrotask(() => this.processNext());
          } else {
            // 未知类型，跳过
            queueMicrotask(() => this.processNext());
          }
          break;
      }
    } catch (err) {
      console.error('[SyncEngine] Error processing action:', action, err);
      this.onError(err, action);
      // 错误不阻塞，继续下一个
      queueMicrotask(() => this.processNext());
    }
  }

  // ---- Speech 处理 ----

  async _handleSpeech(action) {
    this.onSpeechStart(action);
    const text = (action.content || action.params?.content || '').trim();

    if (!text) {
      queueMicrotask(() => this.processNext());
      return;
    }

    // 优先使用 action 中预生成的 audioUrl
    if (action.audioUrl) {
      return this._playAudioUrl(action.audioUrl);
    }

    // 星识增强：流式 TTS + 字级时间戳
    if (this.useStreamingTTS) {
      try {
        return await this._playAudioStream(text, action);
      } catch (err) {
        console.warn('[SyncEngine] Streaming TTS failed, falling back:', err.message);
        this.onError(err, { type: 'speech', content: text });
      }
    }

    // 非流式回退：请求后端 TTS
    try {
      const response = await fetch(this.ttsEndpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: text,
          provider_id: this.ttsConfig.providerId || 'minimax-tts',
          voice: this.ttsConfig.voice || 'female-shaonv',
          speed: this.ttsConfig.speed || 1.0,
        }),
      });

      if (!response.ok) throw new Error(`TTS API error: ${response.status}`);

      const data = await response.json();
      if (data.audio_base64) {
        const audioUrl = 'data:audio/' + (data.format || 'mp3') + ';base64,' + data.audio_base64;
        return this._playAudioUrl(audioUrl);
      }
    } catch (err) {
      console.warn('[SyncEngine] TTS request failed, using reading timer fallback:', err.message);
      this.onError(err, { type: 'speech', content: text });
    }

    // 阅读计时器兜底
    this._fallbackReadingTimer(text);
  }

  /**
   * 流式 TTS 播放 + 字级时间戳动画
   *
   * 调用 POST /api/v2/tts/stream（SSE），接收：
   *   event: audio  → 累积音频数据
   *   event: word   → 字级时间戳
   *   event: done   → 播放完毕
   */
  async _playAudioStream(text, action) {
    const response = await fetch(this.ttsStreamEndpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: text,
        provider_id: this.ttsConfig.providerId || 'minimax-tts',
        voice: this.ttsConfig.voice || 'female-shaonv',
        speed: this.ttsConfig.speed || 1.0,
      }),
    });

    if (!response.ok) throw new Error(`TTS stream error: ${response.status}`);

    // 累积音频数据 + 词时间戳
    const audioChunks = [];
    this._wordTimestamps = [];

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split('\n\n');
      buffer = parts.pop() || '';

      for (const part of parts) {
        const lines = part.split('\n');
        let eventType = '';
        let eventData = '';

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith('data: ')) {
            eventData += line.slice(6);
          }
        }

        if (!eventData) continue;

        try {
          const data = JSON.parse(eventData);
          if (eventType === 'audio' && data.hex) {
            // 将 hex 转为字节数组
            const hexStr = data.hex;
            const bytes = new Uint8Array(hexStr.length / 2);
            for (let i = 0; i < hexStr.length; i += 2) {
              bytes[i / 2] = parseInt(hexStr.substr(i, 2), 16);
            }
            audioChunks.push(bytes);
          } else if (eventType === 'word') {
            this._wordTimestamps.push({
              word: data.word,
              start_ms: data.start_ms,
              end_ms: data.end_ms,
            });
          } else if (eventType === 'done') {
            // 流结束
          } else if (eventType === 'error') {
            throw new Error(data.message || 'TTS stream error');
          }
        } catch (e) {
          if (e.message && !e.message.includes('JSON')) throw e;
        }
      }
    }

    // 合并所有音频块
    if (audioChunks.length === 0) {
      return this._fallbackReadingTimer(text);
    }

    const totalLength = audioChunks.reduce((sum, c) => sum + c.length, 0);
    const combined = new Uint8Array(totalLength);
    let offset = 0;
    for (const chunk of audioChunks) {
      combined.set(chunk, offset);
      offset += chunk.length;
    }

    const mimeType = 'audio/' + (this.ttsConfig.audioFormat || 'mp3');
    const blob = new Blob([combined], { type: mimeType });
    const audioUrl = URL.createObjectURL(blob);

    return this._playAudioWithWordTimestamps(audioUrl, text);
  }

  /**
   * 播放音频 + 启动字级时间戳监听
   *
   * 使用 audio.timeupdate 事件（仅当有词时间戳时），
   * 根据 currentTime 查找当前应高亮的词，触发 onWordHighlight。
   */
  _playAudioWithWordTimestamps(audioUrl, fallbackText) {
    return new Promise((resolve) => {
      this.audioElement.src = audioUrl;

      // 如果有字级时间戳，启动 timeupdate 监听
      if (this._wordTimestamps.length > 0) {
        this._startWordTimer();
      }

      this.audioElement.onended = () => {
        this._stopWordTimer();
        URL.revokeObjectURL(audioUrl);
        this.processNext();
        resolve();
      };

      this.audioElement.play().catch(() => {
        this._stopWordTimer();
        URL.revokeObjectURL(audioUrl);
        this._fallbackReadingTimer(fallbackText);
        resolve();
      });
    });
  }

  /** 启动 timeupdate 轮询，驱动字级高亮 */
  _startWordTimer() {
    this._stopWordTimer();
    const checkInterval = 30; // 每 30ms 检查一次

    this._wordHighlightTimer = setInterval(() => {
      const currentTimeMs = this.audioElement.currentTime * 1000;
      const timestamps = this._wordTimestamps;

      // 找到当前应高亮的词
      let found = null;
      for (let i = timestamps.length - 1; i >= 0; i--) {
        const t = timestamps[i];
        if (currentTimeMs >= t.start_ms && currentTimeMs <= t.end_ms) {
          found = t;
          break;
        }
        // 在词与词之间：使用最近的已结束词
        if (!found && currentTimeMs > t.end_ms) {
          found = t;
          break;
        }
      }

      if (found) {
        this.onWordHighlight(found.word, found.start_ms, found.end_ms);
      }
    }, checkInterval);
  }

  /** 停止 timeupdate 轮询 */
  _stopWordTimer() {
    if (this._wordHighlightTimer) {
      clearInterval(this._wordHighlightTimer);
      this._wordHighlightTimer = null;
    }
  }

  _playAudioUrl(audioUrl) {
    return new Promise((resolve) => {
      this.audioElement.src = audioUrl;
      this.audioElement.onended = () => {
        this.processNext();
        resolve();
      };
      this.audioElement.play().catch(() => {
        console.warn('[SyncEngine] Audio play failed, advancing');
        this.processNext();
        resolve();
      });
    });
  }

  _fallbackReadingTimer(text) {
    const cjkChars = (text.match(/[一-鿿]/g) || []).length;
    const words = text.split(/\s+/).filter(w => /[a-zA-Z]/.test(w)).length;
    const cjkTime = cjkChars * 150;   // 中文 150ms/字
    const wordTime = words * 240;      // 英文 240ms/词
    const duration = Math.max(2000, cjkTime + wordTime);
    setTimeout(() => this.processNext(), duration);
  }

  // ---- Whiteboard 处理 ----

  async _handleWhiteboard(action) {
    const delays = {
      'wb_open': 2000,
      'wb_draw_text': 500,
      'wb_draw_shape': 800,
      'wb_draw_chart': 1000,
      'wb_draw_latex': 600,
      'wb_draw_table': 800,
      'wb_draw_line': 400,
      'wb_draw_code': 800,
      'wb_draw_svg': 600,
      'wb_edit_code': 300,
      'wb_clear': 300,
      'wb_delete': 200,
      'wb_close': 300,
    };

    this.onVisualFire(action);
    const delay = delays[action.type] || 500;
    await this._delay(delay);
    this.processNext();
  }

  // ---- 工具方法 ----

  _delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  _loadTTSConfig() {
    try {
      const stored = localStorage.getItem('ttsConfig');
      return stored ? JSON.parse(stored) : { providerId: 'minimax-tts', voice: 'female-shaonv', speed: 1.0 };
    } catch {
      return { providerId: 'minimax-tts', voice: 'female-shaonv', speed: 1.0 };
    }
  }

  /** 保存 TTS 配置到 localStorage */
  saveTTSConfig(config) {
    this.ttsConfig = { ...this.ttsConfig, ...config };
    try {
      localStorage.setItem('ttsConfig', JSON.stringify(this.ttsConfig));
    } catch {}
  }

  /** 获取当前播放进度 */
  getProgress() {
    return {
      currentIndex: this.currentIndex,
      totalActions: this.actions.length,
      state: this.state,
      remaining: this.actions.length - this.currentIndex,
    };
  }
}

// Browser-compatible global export
if (typeof window !== 'undefined') {
  window.SyncEngine = SyncEngine;
}
