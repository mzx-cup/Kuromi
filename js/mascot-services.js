/**
 * 看板娘 AI 助手 — Services 层 (v2 全功能版)
 *
 * 纯 async 函数 + 工具函数，零 DOM 操作。被 Alpine 组件调用。
 * 包含：对话、语音、记忆、画像、统计、签到、历史、Markdown、页面感知
 */
window.MascotServices = (() => {
  'use strict';

  const BASE = '/api/mascot';
  const STORAGE_PREFIX = 'starlearn_mascot_';

  // ═══════════════════════════════════════════
  // 1. SSE 流式对话
  // ═══════════════════════════════════════════
  async function* streamChat(message, history, pageContext, opts = {}) {
    const { signal } = opts;
    const studentId = localStorage.getItem('starlearn_student_id') || 'default';

    const response = await fetch(`${BASE}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        student_id: studentId,
        page_context: pageContext || document.title || window.location.pathname,
        conversation_history: (history || []).slice(-20),
      }),
      signal,
    });

    if (!response.ok) {
      throw new Error(`Chat stream failed: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        try {
          const data = JSON.parse(line.slice(6));
          yield data;
        } catch (_) { /* skip */ }
      }
    }
  }

  // ═══════════════════════════════════════════
  // 2. 语音 — 统一使用 /api/v2/asr/transcribe 和 /api/v2/tts/generate
  // ═══════════════════════════════════════════
  async function speechToText(audioBlob) {
    // ASR 端点使用 multipart/form-data（UploadFile），不是 JSON
    const formData = new FormData();
    formData.append('file', audioBlob, 'recording.webm');
    formData.append('provider_id', 'baidu-asr');

    const res = await fetch('/api/v2/asr/transcribe', {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) throw new Error('STT failed');
    const data = await res.json();
    return data.success ? data.text : null;
  }

  async function textToSpeech(text) {
    // TTS 使用 /api/v2/tts/generate — 返回 { audio_base64, format, duration_ms }
    const res = await fetch('/api/v2/tts/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text,
        provider_id: 'minimax-tts',
        voice: 'female-shaonv',
        speed: 1.0,
        audio_format: 'mp3',
      }),
    });
    if (!res.ok) throw new Error('TTS failed');
    const data = await res.json();
    if (data.audio_base64) {
      const byteString = atob(data.audio_base64);
      const ab = new ArrayBuffer(byteString.length);
      const ia = new Uint8Array(ab);
      for (let i = 0; i < byteString.length; i++) ia[i] = byteString.charCodeAt(i);
      const blob = new Blob([ab], { type: `audio/${data.format || 'mp3'}` });
      return URL.createObjectURL(blob);
    }
    return null;
  }

  // ═══════════════════════════════════════════
  // 3. 语音录制
  // ═══════════════════════════════════════════
  let mediaRecorder = null;
  let audioChunks = [];

  async function startRecording() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream, {
      mimeType: MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/mp4',
    });
    audioChunks = [];
    return new Promise(resolve => {
      mediaRecorder.ondataavailable = e => { if (e.data.size > 0) audioChunks.push(e.data); };
      mediaRecorder.onstart = () => resolve();
      mediaRecorder.start();
    });
  }

  function stopRecording() {
    return new Promise(resolve => {
      if (!mediaRecorder || mediaRecorder.state === 'inactive') { resolve(null); return; }
      mediaRecorder.onstop = () => {
        if (mediaRecorder.stream) mediaRecorder.stream.getTracks().forEach(t => t.stop());
        if (audioChunks.length === 0) { resolve(null); return; }
        resolve(new Blob(audioChunks, { type: mediaRecorder.mimeType || 'audio/webm' }));
      };
      mediaRecorder.stop();
    });
  }

  // ═══════════════════════════════════════════
  // 4. 导航
  // ═══════════════════════════════════════════
  const ROUTE_MAP = {
    'AI问答':       '/html/index.html',
    '课程中心':     '/html/courses.html',
    '我的课程':     '/html/courses.html',
    '课程':         '/html/courses.html',
    '学习数据':     '/html/personal.html',
    '数据看板':     '/html/personal.html',
    '个人中心':     '/html/personal.html',
    '代码工坊':     '/html/code.html',
    '代码':         '/html/code.html',
    '苏格拉底教学': '/html/socratic-ai.html',
    '苏格拉底':     '/html/socratic-ai.html',
    '全息视界':     '/html/video-player.html',
    'AI编程':       '/html/ai-pair-programming.html',
    '日历':         '/html/calendar.html',
    '进度':         '/html/progress.html',
    '评测':         '/html/assessment.html',
  };

  function navigate(target) {
    const url = ROUTE_MAP[target];
    if (url) { window.location.href = url; return true; }
    // 模糊匹配
    for (const [key, val] of Object.entries(ROUTE_MAP)) {
      if (key.includes(target) || target.includes(key)) {
        window.location.href = val;
        return true;
      }
    }
    return false;
  }

  // ═══════════════════════════════════════════
  // 5. 记忆 API — 统一使用 /api/memories/ (app/api/memory.py)
  //    与 index.js AI 问答页共享同一套记忆管理端点。
  // ═══════════════════════════════════════════
  async function fetchMemories(userId) {
    const res = await fetch(`/api/memories/${encodeURIComponent(userId)}`);
    if (!res.ok) throw new Error('Failed to fetch memories');
    return res.json();
  }

  async function createMemory(userId, content, memoryType = 'fact') {
    const res = await fetch('/api/memories', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, content, memory_type: memoryType }),
    });
    return res.json();
  }

  async function confirmMemory(memoryId, confirmed) {
    const res = await fetch(`/api/memories/${memoryId}/confirm`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ confirmed }),
    });
    return res.json();
  }

  async function deleteMemory(memoryId) {
    const res = await fetch(`/api/memories/${memoryId}`, { method: 'DELETE' });
    return res.json();
  }

  // ═══════════════════════════════════════════
  // 6. 画像 + 统计 + 签到 — 各端点统一为单一数据源
  //
  //    用户画像:  /api/profile/{userId}      (app/api/profile.py)
  //    学习统计:  /api/mascot/stats/{userId}  (app/api/mascot.py — 直接查询 study_sessions)
  //    每日签到:  /api/mascot/checkin         (app/api/mascot.py — 唯一签到端点)
  // ═══════════════════════════════════════════
  async function fetchProfile(userId) {
    const res = await fetch(`/api/profile/${encodeURIComponent(userId)}`);
    if (!res.ok) throw new Error('Failed to fetch profile');
    return res.json();
  }

  async function fetchStats(userId) {
    const res = await fetch(`${BASE}/stats/${encodeURIComponent(userId)}`);
    if (!res.ok) return null;
    return res.json();
  }

  async function dailyCheckin(userId) {
    const res = await fetch(`${BASE}/checkin`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ student_id: userId }),
    });
    return res.json();
  }

  // ═══════════════════════════════════════════
  // 7. 聊天历史持久化 (localStorage)
  // ═══════════════════════════════════════════
  function saveChatHistory(messages, userId) {
    const key = STORAGE_PREFIX + 'history_' + (userId || 'default');
    const clean = messages.filter(m => !m.typing).slice(-200);
    try {
      localStorage.setItem(key, JSON.stringify(clean));
    } catch (_) { /* quota exceeded */ }
  }

  function loadChatHistory(userId) {
    const key = STORAGE_PREFIX + 'history_' + (userId || 'default');
    try {
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : [];
    } catch (_) { return []; }
  }

  function clearChatHistory(userId) {
    const key = STORAGE_PREFIX + 'history_' + (userId || 'default');
    localStorage.removeItem(key);
  }

  function exportChatHistory(messages, format = 'text') {
    const clean = messages.filter(m => !m.typing);
    if (format === 'json') {
      return JSON.stringify(clean, null, 2);
    }
    // text 格式
    return clean.map(m => {
      const role = m.role === 'user' ? '你' : m.role === 'assistant' ? '小星' : '系统';
      return `[${role}] ${m.content}`;
    }).join('\n\n');
  }

  function downloadChatHistory(messages) {
    const text = exportChatHistory(messages, 'text');
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `小星对话记录_${new Date().toISOString().slice(0, 10)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }

  // ═══════════════════════════════════════════
  // 8. 页面感知
  // ═══════════════════════════════════════════
  function getPageContext() {
    const path = window.location.pathname.toLowerCase();
    const title = document.title || '';

    if (path.includes('hub'))          return { type: 'hub',        label: '学习中枢' };
    if (path.includes('index'))         return { type: 'chat',       label: 'AI问答' };
    if (path.includes('course'))        return { type: 'course',     label: '课程中心' };
    if (path.includes('code'))          return { type: 'code',       label: '代码工坊' };
    if (path.includes('personal'))      return { type: 'personal',   label: '个人中心' };
    if (path.includes('socratic'))      return { type: 'socratic',   label: '苏格拉底教学' };
    if (path.includes('assessment'))    return { type: 'assessment', label: '评测练习' };
    if (path.includes('video'))         return { type: 'video',      label: '全息视界' };
    if (path.includes('calendar'))      return { type: 'calendar',   label: '学习日历' };
    if (path.includes('progress'))      return { type: 'progress',   label: '学习进度' };
    if (path.includes('login'))         return { type: 'login',      label: '登录' };
    if (path.includes('register'))      return { type: 'register',   label: '注册' };
    if (path.includes('classroom'))     return { type: 'classroom',  label: '教室' };
    if (path.includes('ai-pair'))       return { type: 'pair',       label: 'AI结对编程' };
    if (path.includes('settings'))      return { type: 'settings',   label: '设置' };

    return { type: 'unknown', label: title || '星学平台' };
  }

  function getQuickSuggestions(pageContext) {
    const ctx = pageContext || getPageContext();
    // 通用建议
    const common = [
      { text: '今天有什么学习建议？', icon: '💡', label: '学习建议' },
      { text: '帮我总结一下今天的收获', icon: '📝', label: '今日总结' },
    ];
    // 页面相关建议
    const pageSpecific = {
      hub:        [{ text: '解释一下学习中枢的功能', icon: '🏠', label: '中枢介绍' }],
      chat:       [{ text: '出一道Python练习题', icon: '🐍', label: 'Python练习' }],
      course:     [{ text: '推荐一门适合我的课程', icon: '📚', label: '推荐课程' }],
      code:       [{ text: '帮我调试这段代码', icon: '🐛', label: '调试代码' }],
      personal:   [{ text: '分析我的学习数据', icon: '📊', label: '数据分析' }],
      socratic:   [{ text: '苏格拉底教学是什么？', icon: '🏛️', label: '教学介绍' }],
      assessment: [{ text: '这道题我不太懂', icon: '❓', label: '帮我解题' }],
    };
    const specific = pageSpecific[ctx.type] || [];
    return [...specific, ...common].slice(0, 5);
  }

  // ═══════════════════════════════════════════
  // 9. 时间感知问候
  // ═══════════════════════════════════════════
  function getTimeGreeting() {
    const hour = new Date().getHours();
    if (hour < 5)  return { text: '夜深了', emoji: '🌙', sub: '注意休息哦~' };
    if (hour < 9)  return { text: '早上好', emoji: '🌅', sub: '一日之计在于晨！' };
    if (hour < 12) return { text: '上午好', emoji: '☀️', sub: '今天状态不错！' };
    if (hour < 14) return { text: '中午好', emoji: '🍜', sub: '午休后效率更高哦~' };
    if (hour < 18) return { text: '下午好', emoji: '🌤️', sub: '继续加油！' };
    if (hour < 22) return { text: '晚上好', emoji: '🌆', sub: '今天学得怎么样？' };
    return { text: '夜深了', emoji: '🌙', sub: '注意休息，明天继续~' };
  }

  // ═══════════════════════════════════════════
  // 10. Markdown 渲染（轻量版）
  // ═══════════════════════════════════════════
  function renderMarkdown(text) {
    if (!text) return '';

    let html = text;

    // 转义 HTML
    html = html.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

    // 代码块 ```...``` (含语法高亮)
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
      const langLabel = lang || '';
      const escaped = code.trim();
      const highlighted = highlightCode(escaped, langLabel);
      return `<pre class="md-code-block" data-lang="${langLabel}"><code class="md-code">${highlighted}</code><button class="md-copy-btn" onclick="navigator.clipboard.writeText(this.parentElement.querySelector('code').textContent)" title="复制代码">📋</button></pre>`;
    });

    // 行内代码 `...`
    html = html.replace(/`([^`]+)`/g, '<code class="md-inline-code">$1</code>');

    // 粗体 **...**
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

    // 斜体 *...*
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');

    // 链接 [text](url)
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener" class="md-link">$1</a>');

    // 无序列表 - item
    html = html.replace(/^- (.+)$/gm, '<li class="md-li">$1</li>');
    html = html.replace(/(<li class="md-li">.*<\/li>)/s, '<ul class="md-ul">$1</ul>');

    // 有序列表 1. item
    html = html.replace(/^\d+\. (.+)$/gm, '<li class="md-li">$1</li>');

    // 标题 ### ...
    html = html.replace(/^### (.+)$/gm, '<h4 class="md-h4">$1</h4>');
    html = html.replace(/^## (.+)$/gm, '<h3 class="md-h3">$1</h3>');

    // 水平线 ---
    html = html.replace(/^---$/gm, '<hr class="md-hr">');

    // 换行
    html = html.replace(/\n\n/g, '</p><p class="md-p">');
    html = html.replace(/\n/g, '<br>');

    // 包装
    return '<div class="md-content"><p class="md-p">' + html + '</p></div>';
  }

  // ═══════════════════════════════════════════
  // 11. 代码高亮（Python + JS + SQL 基础高亮）
  // ═══════════════════════════════════════════
  function highlightCode(code, lang) {
    const escaped = code
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

    let highlighted = escaped;

    // 字符串
    highlighted = highlighted.replace(/(["'`])(?:(?!\1|\\).|\\.)*\1/g, '<span class="hl-str">$&</span>');

    // 注释
    if (lang === 'python' || lang === 'py') {
      highlighted = highlighted.replace(/(#.*)$/gm, '<span class="hl-comment">$1</span>');
    } else if (lang === 'javascript' || lang === 'js' || lang === 'ts') {
      highlighted = highlighted.replace(/(\/\/.*)$/gm, '<span class="hl-comment">$1</span>');
    } else if (lang === 'sql') {
      highlighted = highlighted.replace(/(--.*)$/gm, '<span class="hl-comment">$1</span>');
    }

    // 关键字
    const kwMap = {
      python: /\b(def|class|import|from|return|if|else|elif|for|while|try|except|raise|with|as|in|not|and|or|True|False|None|lambda|yield|pass|break|continue|async|await|print|range|len|list|dict|set|tuple|str|int|float|bool)\b/g,
      javascript: /\b(function|const|let|var|return|if|else|for|while|try|catch|throw|new|class|extends|import|export|default|from|async|await|this|true|false|null|undefined|console|document|window)\b/g,
      sql: /\b(SELECT|FROM|WHERE|INSERT|UPDATE|DELETE|CREATE|TABLE|ALTER|DROP|INDEX|JOIN|LEFT|RIGHT|INNER|ON|AND|OR|NOT|IN|LIKE|ORDER|BY|GROUP|HAVING|LIMIT|OFFSET|COUNT|SUM|AVG|MAX|MIN|AS|DISTINCT|UNION|ALL|NULL|IS|EXISTS|BETWEEN|CASE|WHEN|THEN|ELSE|END)\b/gi,
    };

    const keywords = kwMap[lang] || kwMap.python;
    highlighted = highlighted.replace(keywords, '<span class="hl-kw">$1</span>');

    // 数字
    highlighted = highlighted.replace(/\b(\d+\.?\d*)\b/g, '<span class="hl-num">$1</span>');

    // 函数调用
    highlighted = highlighted.replace(/\b([a-zA-Z_]\w*)(?=\()/g, '<span class="hl-fn">$1</span>');

    return highlighted;
  }

  // ═══════════════════════════════════════════
  // 12. 表情映射 + 粒子表情
  // ═══════════════════════════════════════════
  const EMOJI_MAP = {
    happy:     '😊',
    thinking:  '🤔',
    surprised: '😮',
    encourage: '🌟',
    celebrate: '🎉',
    love:      '💜',
    cool:      '😎',
    sleepy:    '😴',
    neutral:   '😊',
  };

  function emojiFor(expression) {
    return EMOJI_MAP[expression] || '😊';
  }

  const PARTICLE_EMOJIS = ['⭐', '🌟', '✨', '💫', '🎉', '💜', '🔥', '💪'];

  function randomParticleEmoji() {
    return PARTICLE_EMOJIS[Math.floor(Math.random() * PARTICLE_EMOJIS.length)];
  }

  // ═══════════════════════════════════════════
  // Export
  // ═══════════════════════════════════════════
  return {
    // 对话
    streamChat,
    // 语音
    speechToText, textToSpeech, startRecording, stopRecording,
    // 导航
    navigate, ROUTE_MAP,
    // 记忆
    fetchMemories, createMemory, confirmMemory, deleteMemory,
    // 画像 + 统计 + 签到
    fetchProfile, fetchStats, dailyCheckin,
    // 历史
    saveChatHistory, loadChatHistory, clearChatHistory,
    exportChatHistory, downloadChatHistory,
    // 页面感知
    getPageContext, getQuickSuggestions,
    // 时间
    getTimeGreeting,
    // 渲染
    renderMarkdown, highlightCode,
    // 表情
    emojiFor, randomParticleEmoji,
  };
})();
