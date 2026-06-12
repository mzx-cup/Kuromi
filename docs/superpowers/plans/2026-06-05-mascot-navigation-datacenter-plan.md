# 星识 Phase 3-5 全面实现计划
星识项目位（C:\Users\ZWC\Downloads\Kuromi-main\Kuromi-main）
知域项目位置（C:\Users\ZWC\Desktop\软件杯大赛\softwacecup）
“小慧”ai助手位置（C:\Users\ZWC\Downloads\ai-assistant-teaching-website-main\ai-assistant-teaching-website-main）
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement 2D Live2D mascot AI assistant, dual-channel navigation refactor, and 知域 teacher dashboard + data center migration.

**Architecture:** Three sequential phases: Phase 3 builds the Live2D mascot controller as a global singleton extending existing `kanban.js`; Phase 4 restructures the hub sidebar to 5 entries with AJAX component embedding and Fuse.js command search; Phase 5 ports JWT auth, 6 teacher pages, and ECharts data dashboard from Vue3/Spring Boot to vanilla JS/FastAPI/pymysql.

**Tech Stack:** FastAPI + pymysql (backend), vanilla HTML/JS/CSS + Live2D Cubism SDK + ECharts + Fuse.js (frontend), PyJWT (auth), SSE (streaming)

---

## File Structure

```
Phase 3 (看板娘):
  Create:  js/mascot.js              — MascotController singleton (voice, SSE, commands, Live2D binding)
  Create:  css/mascot.css            — Panel styles, particles, bubbles, responsive
  Create:  app/api/mascot.py         — /api/mascot/{stt,chat/stream,tts,emotion} routes
  Modify:  main.py                   — Register mascot router
  Modify:  html/hub.html             — Add mascot CSS/JS references
  Modify:  html/index.html           — Add mascot CSS/JS references
  Note:    static/kanban.png         — 已有引用，若不存在则 Live2D 加载失败时无 fallback 图。可放任意 PNG 占位

Phase 4 (导航重构):
  Modify:  html/hub.html             — Sidebar: 12→5 entries
  Modify:  css/hub.css               — Sidebar style adjustments (incremental)
  Modify:  html/index.html           — Add hash-tab handler + mascot references
  Modify:  html/personal.html        — Add hash-tab handler
  Modify:  html/socratic-ai.html     — Add redirect script
  Modify:  html/video-player.html    — Add redirect script
  Modify:  html/code.html            — Add redirect script
  Modify:  html/courses.html         — Add redirect script
  Modify:  html/progress.html        — Add redirect script
  Modify:  html/calendar.html        — Add redirect script
  Modify:  html/flow-meter.html      — Add redirect script (with Phase 5 guard)
  Modify:  html/stellar-showcase.html — Add redirect script
  Modify:  html/plant.html           — Add redirect script (我的生态)
  Modify:  html/settings.html        — Add redirect script
  Create:  html/my-courses.html      — New aggregation page (courses + progress + calendar tabs)
  Create:  js/search-command.js      — Fuse.js command palette (⌘K)
  Create:  css/search-command.css    — Command palette dark-glass theme
  Create:  js/onboarding.js          — Spotlight tour + learning profile wizard
  Create:  css/onboarding.css        — Overlay, spotlight rings, wizard steps

Phase 5 (知域迁移):
  Modify:  db.py                      — Add generic helpers (query_one/query_all/execute/save_memory) + teacher stats functions
  Modify:  html/login.html           — Login/register page (ported from 知域 LoginModal, existing file)
  Create:  js/auth.js                — JWT token management (login/logout/fetchMe)
  Create:  js/http-intercept.js      — fetch/XHR wrapper, Bearer token, 401 redirect
  Modify:  css/auth.css              — Login page styles (existing file, append auth page rules)
  Create:  html/teacher-dashboard.html  — Teacher dashboard (stats + ECharts)
  Create:  js/teacher-dashboard.js   — Dashboard data loading + chart rendering
  Create:  html/teacher-class.html   — Class management
  Create:  js/teacher-class.js       — Class CRUD + student roster
  Create:  html/teacher-manage.html  — Question bank management
  Create:  js/teacher-manage.js      — Question CRUD + import
  Create:  html/teacher-exam.html    — Exam management + grading UI
  Create:  js/teacher-exam.js        — Exam CRUD + AI grading workflow
  Create:  html/teacher-content.html — Content management + AI review tab
  Create:  js/teacher-content.js     — Content editor + review approval
  Create:  html/data-dashboard.html  — Multi-level data visualization
  Create:  js/data-dashboard.js      — ECharts rendering + SSE realtime
  Create:  css/teacher.css           — Shared teacher page styles
  Create:  css/data-dashboard.css    — Dark-screen dashboard theme
  Create:  app/api/auth.py           — /api/auth/{login,register,me} routes
  Create:  app/api/teacher.py        — /api/teacher/* routes (20 endpoints)
  Create:  app/api/datacenter.py     — /api/datacenter/* routes (5 endpoints)
  Create:  app/utils/jwt.py          — PyJWT token generation/verification
  Create:  app/middleware/__init__.py — Package init
  Create:  app/middleware/auth.py    — FastAPI Depends: get_current_user
  Create:  app/middleware/roles.py   — @require_role decorator
  Create:  app/models/teacher.py     — Teacher-side Pydantic models
  Create:  migrations/001_teacher_tables.sql — 8 tables migration (sp_user, classes, questions, exams, etc.)
  Modify:  main.py                   — Register new routers + middleware
```

---

## Phase 3: 2D 看板娘 AI 助手

### Task 3.1: Backend — Mascot API Routes

**Files:**
- Create: `app/api/mascot.py`
- Modify: `main.py` (register router)

- [ ] **Step 1: Create `app/api/mascot.py` with STT, chat/stream, TTS, emotion endpoints**

```python
# -*- coding: utf-8 -*-
"""看板娘 AI 助手 API — STT / 流式对话 / TTS / 情绪识别"""

from __future__ import annotations

import json
import base64
import logging
import asyncio
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

logger = logging.getLogger("starlearn.api.mascot")

router = APIRouter(tags=["mascot"])


# ---------- Request models ----------

class STTRequest(BaseModel):
    audio_base64: str
    format: str = "wav"

class MascotChatRequest(BaseModel):
    message: str
    student_id: str = "default"
    page_context: str | None = None       # 当前页面描述，用于页面总结
    conversation_history: list[dict] | None = None

class TTSRequest(BaseModel):
    text: str
    voice: str = "female-shaonv"
    speed: float = 1.0

class EmotionRequest(BaseModel):
    image_base64: str


# ---------- STT (语音转文字) ----------

@router.post("/stt")
async def mascot_stt(req: STTRequest):
    """将 base64 音频转为文字，复用已有 ASR 管线"""
    try:
        from app.services.asr.registry import get_asr_provider
        provider = get_asr_provider("baidu-asr")  # 实际注册的 provider: baidu-asr / whisper
        audio_bytes = base64.b64decode(req.audio_base64)
        result = await provider.transcribe(audio_bytes, audio_format=req.format)
        return {"success": True, "text": result.text}
    except Exception as e:
        logger.error(f"STT failed: {e}")
        raise HTTPException(status_code=500, detail=f"语音识别失败: {e}")


# ---------- Stream Chat (SSE 流式对话) ----------

@router.post("/chat/stream")
async def mascot_chat_stream(req: MascotChatRequest, request: Request):
    """SSE 流式对话 — 看板娘专属 System Prompt + XML 指令支持"""
    async def event_stream():
        try:
            # 构建看板娘 System Prompt
            system_prompt = build_mascot_system_prompt(req.page_context)

            # 构建消息历史
            messages = [{"role": "system", "content": system_prompt}]
            if req.conversation_history:
                messages.extend(req.conversation_history[-10:])  # 最近10轮
            messages.append({"role": "user", "content": req.message})

            # 复用 LLM 流式管线
            from llm_stream import call_llm_stream_messages
            buffer = ""
            async for chunk in call_llm_stream_messages(messages):
                buffer += chunk
                # 转发原始文本块
                yield f"data: {json.dumps({'type': 'text', 'content': chunk})}\n\n"

                # 检测完整 XML 标签
                for tag in extract_complete_tags(buffer):
                    yield f"data: {json.dumps({'type': 'command', 'tag': tag['name'], 'content': tag['content']})}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

            # 异步提取长期记忆
            asyncio.create_task(extract_mascot_memory(req.student_id, req.message, buffer))

        except asyncio.CancelledError:
            logger.info("Mascot chat stream cancelled by client")
        except Exception as e:
            logger.error(f"Mascot chat stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


# ---------- TTS (文字转语音) ----------

@router.post("/tts")
async def mascot_tts(req: TTSRequest):
    """将文字转为语音，返回 base64 音频"""
    try:
        from app.services.tts.registry import get_tts_provider
        from app.services.tts.types import TTSConfig
        provider = get_tts_provider("minimax-tts")
        config = TTSConfig(voice=req.voice, speed=req.speed, audio_format="mp3")
        result = await provider.generate(req.text, config)
        audio_base64 = base64.b64encode(result.audio).decode()
        return {"success": True, "audio_base64": audio_base64, "format": result.format}
    except Exception as e:
        logger.error(f"TTS failed: {e}")
        raise HTTPException(status_code=500, detail=f"语音合成失败: {e}")


# ---------- Emotion Recognition (情绪识别，可选) ----------

@router.post("/emotion")
async def mascot_emotion(req: EmotionRequest):
    """分析面部情绪（摄像头采集 → 百度/讯飞 API）"""
    try:
        # 复用已有情绪分析或占位实现
        result = {"emotion": "neutral", "confidence": 0.5}
        return {"success": True, **result}
    except Exception as e:
        logger.error(f"Emotion recognition failed: {e}")
        raise HTTPException(status_code=500, detail=f"情绪识别失败: {e}")


# ---------- Helpers ----------

def build_mascot_system_prompt(page_context: str | None) -> str:
    base = """你是"小星"，星识学习平台的 AI 看板娘助手。

角色设定：活泼可爱的女高中生风格，热爱学习，擅长鼓励。
年龄感：16-18 岁，语气自然不做作。

核心职责：
1. 回答学习问题（调用平台知识库）
2. 帮助用户导航平台功能
3. 在课程学习时提供伴学指导
4. 提醒学习进度和任务

对话风格：
- 日常闲聊：活泼亲切，每次 2-3 句话
- 专业问答：切换到认真模式，详细解答
- 导航请求：回复包含 <网站指令> 标签，例如 <网站指令>打开课程中心</网站指令>
- 鼓励场景：回复包含 <表情>开心</表情> 或 <动作>鼓励</动作> 标签
- 学习提醒：温和提醒，不催促

可用 <网站指令> 目标：AI问答、我的课程、学习数据、个人中心、代码工坊、苏格拉底教学
可用 <表情>：开心、思考、惊讶、鼓励
可用 <动作>：招手、鼓励、小憩

行为规范：
- 不回答政治敏感问题
- 不生成暴力/色情内容
- 不确定时诚实说不知道
- 记住用户的偏好和之前聊过的话题"""

    if page_context:
        base += f"\n\n用户当前页面：{page_context}\n请根据当前页面内容提供相关的帮助和建议。"

    return base


def extract_complete_tags(text: str) -> list[dict]:
    """从文本中提取完整的 XML 标签"""
    import re
    patterns = [
        (r'<网站指令>(.*?)</网站指令>', 'navigate'),
        (r'<表情>(.*?)</表情>', 'expression'),
        (r'<动作>(.*?)</动作>', 'action'),
        (r'<打开链接>(.*?)</打开链接>', 'open_link'),
    ]
    results = []
    for pattern, name in patterns:
        for match in re.finditer(pattern, text):
            results.append({"name": name, "content": match.group(1).strip()})
    return results


async def extract_mascot_memory(student_id: str, user_msg: str, assistant_reply: str):
    """异步提取长期记忆（复用已有 memory 管线）"""
    try:
        from db import save_memory
        # 同步 DB 操作放到线程池执行，避免阻塞事件循环
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, save_memory, student_id, {
            "role": "user", "content": user_msg, "source": "mascot"
        })
        await loop.run_in_executor(None, save_memory, student_id, {
            "role": "assistant", "content": assistant_reply[:500], "source": "mascot"
        })
    except Exception:
        pass  # 静默失败，不影响主流程
```

- [ ] **Step 2: Register mascot router in `main.py`**

In `main.py`, after the existing router registrations (around line 154), add:

```python
# ---- Mascot API (看板娘AI助手) ----
from app.api.mascot import router as mascot_router
app.include_router(mascot_router, prefix="/api/mascot")
```

- [ ] **Step 3: Verify router registration**

Run: `python -c "from main import app; routes = [r.path for r in app.routes]; print([r for r in routes if 'mascot' in r])"`
Expected: `['/api/mascot/stt', '/api/mascot/chat/stream', '/api/mascot/tts', '/api/mascot/emotion']`

- [ ] **Step 4: Commit**

```bash
git add app/api/mascot.py main.py
git commit -m "feat(mascot): add /api/mascot STT/Chat/stream/TTS/emotion endpoints

- POST /api/mascot/stt — speech-to-text via existing ASR
- POST /api/mascot/chat/stream — SSE streaming with mascot System Prompt + XML tag parsing
- POST /api/mascot/tts — text-to-speech via existing TTS
- POST /api/mascot/emotion — camera emotion recognition (stub)
- Registered router in main.py"
```

---

### Task 3.2: Frontend — MascotController (js/mascot.js)

**Files:**
- Create: `js/mascot.js`

- [ ] **Step 1: Create `js/mascot.js` — Core controller extending kanban.js**

```javascript
/**
 * 看板娘 AI 控制器 — MascotController
 *
 * 依赖: kanban.js (Live2D 渲染层已初始化)
 * 功能: 语音对话 / SSE 流式聊天 / XML 指令解析 / 页面总结 / 情绪识别(可选)
 */
(function() {
  'use strict';

  // ===== 状态 =====
  const state = {
    mode: 'corner',               // 'corner' | 'panel' | 'companion'
    conversation: [],              // {role, content}[]
    isRecording: false,
    mediaRecorder: null,
    audioChunks: [],
    eventSource: null,
    panelVisible: false,
    studentId: 'default',
    pageContext: '',
  };

  // ===== DOM 引用（延迟初始化） =====
  let panel = null;
  let panelMessages = null;
  let panelInput = null;
  let panelMicBtn = null;
  let panelSendBtn = null;
  let panelCloseBtn = null;

  // ===== 初始化 =====
  function init() {
    // 读取学生 ID
    const saved = localStorage.getItem('starlearn_student_id');
    if (saved) state.studentId = saved;

    // 设置页面上下文
    state.pageContext = document.title || window.location.pathname;

    // 挂载全局 API
    window.Mascot = {
      openPanel, closePanel, togglePanel,
      sendMessage, startVoice, stopVoice,
      navigate: handleNavigate,
      getState: () => state,
    };

    // 绑定看板娘点击 → 打开面板
    bindKanbanClick();

    // 建立 SSE 长连接（接收服务端推送）
    connectProactiveSSE();

    console.log('[Mascot] Controller initialized, mode:', state.mode);
  }

  // ===== 对话面板 =====
  function createPanel() {
    if (panel) return;

    panel = document.createElement('div');
    panel.className = 'mascot-panel';
    panel.innerHTML = `
      <div class="mascot-panel-header">
        <div class="mascot-panel-avatar">
          <div class="mascot-panel-expression" id="mascot-expression">😊</div>
        </div>
        <div class="mascot-panel-title">小星</div>
        <button class="mascot-panel-close" id="mascot-panel-close">×</button>
      </div>
      <div class="mascot-panel-messages" id="mascot-messages"></div>
      <div class="mascot-panel-input-row">
        <button class="mascot-panel-mic" id="mascot-mic-btn" title="语音输入（需授权）">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/></svg>
        </button>
        <input type="text" class="mascot-panel-input" id="mascot-input" placeholder="输入消息，或点击麦克风说话..." />
        <button class="mascot-panel-send" id="mascot-send-btn">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
        </button>
      </div>
    `;
    document.body.appendChild(panel);

    // 绑定 DOM
    panelMessages = document.getElementById('mascot-messages');
    panelInput = document.getElementById('mascot-input');
    panelMicBtn = document.getElementById('mascot-mic-btn');
    panelSendBtn = document.getElementById('mascot-send-btn');
    panelCloseBtn = document.getElementById('mascot-panel-close');

    // 事件
    panelSendBtn.addEventListener('click', () => {
      const text = panelInput.value.trim();
      if (text) { sendMessage(text); panelInput.value = ''; }
    });
    panelInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        const text = panelInput.value.trim();
        if (text) { sendMessage(text); panelInput.value = ''; }
      }
    });
    panelMicBtn.addEventListener('click', () => {
      if (state.isRecording) { stopVoice(); } else { startVoice(); }
    });
    panelCloseBtn.addEventListener('click', closePanel);

    // 点击面板外关闭
    document.addEventListener('click', (e) => {
      if (panel && state.panelVisible && !panel.contains(e.target)) {
        const kanbanEl = document.querySelector('.app-kanban');
        if (kanbanEl && !kanbanEl.contains(e.target)) {
          closePanel();
        }
      }
    });
  }

  function openPanel() {
    createPanel();
    panel.classList.add('visible');
    state.panelVisible = true;
    panelInput?.focus();
  }

  function closePanel() {
    if (panel) panel.classList.remove('visible');
    state.panelVisible = false;
  }

  function togglePanel() {
    state.panelVisible ? closePanel() : openPanel();
  }

  // ===== 消息发送 =====
  async function sendMessage(text) {
    openPanel();
    appendMessage('user', text);
    state.conversation.push({ role: 'user', content: text });

    // 显示思考状态
    setExpression('thinking');
    const loadingId = appendLoadingBubble();

    try {
      const response = await fetch('/api/mascot/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          student_id: state.studentId,
          page_context: state.pageContext,
          conversation_history: state.conversation.slice(-10),
        }),
      });

      removeLoadingBubble(loadingId);

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let assistantText = '';
      let currentBubble = null;

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
            if (data.type === 'text') {
              assistantText += data.content;
              if (!currentBubble) {
                currentBubble = appendMessage('assistant', '');
              }
              currentBubble.textContent += data.content;
              panelMessages.scrollTop = panelMessages.scrollHeight;
            } else if (data.type === 'command') {
              handleCommand(data.tag, data.content);
            } else if (data.type === 'done') {
              setExpression('happy');
            } else if (data.type === 'error') {
              appendMessage('system', '抱歉，出错了: ' + data.message);
            }
          } catch (e) { /* skip malformed JSON */ }
        }
      }

      if (assistantText) {
        state.conversation.push({ role: 'assistant', content: assistantText });
      }

    } catch (error) {
      removeLoadingBubble(loadingId);
      appendMessage('system', '网络连接失败，请检查网络后重试');
      setExpression('surprised');
    }
  }

  // ===== 语音输入 =====
  async function startVoice() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      state.mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      state.audioChunks = [];

      state.mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) state.audioChunks.push(e.data);
      };

      state.mediaRecorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        const blob = new Blob(state.audioChunks, { type: 'audio/webm' });
        await processVoiceInput(blob);
      };

      state.mediaRecorder.start();
      state.isRecording = true;
      if (panelMicBtn) {
        panelMicBtn.classList.add('recording');
        panelMicBtn.style.color = '#ef4444';
      }
      setExpression('surprised');
    } catch (error) {
      console.warn('[Mascot] 麦克风权限被拒绝，仅支持文字输入');
      if (panelMicBtn) panelMicBtn.style.display = 'none';
      appendMessage('system', '麦克风权限被拒绝，您可以使用文字输入与我对话~');
    }
  }

  function stopVoice() {
    if (state.mediaRecorder && state.isRecording) {
      state.mediaRecorder.stop();
      state.isRecording = false;
      if (panelMicBtn) {
        panelMicBtn.classList.remove('recording');
        panelMicBtn.style.color = '';
      }
    }
  }

  async function processVoiceInput(blob) {
    // Blob → base64
    const reader = new FileReader();
    reader.onload = async () => {
      const base64 = reader.result.split(',')[1];
      try {
        const res = await fetch('/api/mascot/stt', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ audio_base64: base64, format: 'webm' }),
        });
        const data = await res.json();
        if (data.success && data.text) {
          panelInput.value = data.text;
          sendMessage(data.text);
        }
      } catch (error) {
        appendMessage('system', '语音识别失败，请使用文字输入');
      }
    };
    reader.readAsDataURL(blob);
  }

  // ===== 指令处理 =====
  function handleCommand(tag, content) {
    switch (tag) {
      case 'navigate':
        handleNavigate(content);
        break;
      case 'expression':
        setExpression(content);
        break;
      case 'action':
        // 委托给 kanban.js 的 Live2D motion 或 CSS 动画
        triggerAction(content);
        break;
      case 'open_link':
        if (content.startsWith('http')) window.open(content, '_blank');
        break;
    }
  }

  function handleNavigate(target) {
    const routeMap = {
      'AI问答': '/index.html',
      '课程中心': '/my-courses.html',
      '我的课程': '/my-courses.html',
      '学习数据': '/data-dashboard.html',
      '个人中心': '/personal.html',
      '代码工坊': '/code.html',
      '苏格拉底教学': '/socratic-ai.html',
    };
    const url = routeMap[target];
    if (url) {
      window.location.href = url;
    } else {
      appendMessage('system', `抱歉，我找不到"${target}"这个页面~`);
    }
  }

  function setExpression(expr) {
    const el = document.getElementById('mascot-expression');
    if (!el) return;
    const map = { happy: '😊', thinking: '🤔', surprised: '😮', encourage: '🌟', neutral: '😊' };
    el.textContent = map[expr] || '😊';
  }

  function triggerAction(action) {
    // 粒子特效或 CSS 动画
    if (action === '鼓励' || action === 'encourage') {
      spawnParticles();
    }
  }

  // ===== SSE 长连接（接收服务端推送） =====
  // 注意: /api/mascot/proactive/stream 端点暂未实现，SSE 连接失败时静默降级。
  // 后续可在 mascot.py 中添加 @router.get("/proactive/stream") 端点启用此功能。
  function connectProactiveSSE() {
    let retryCount = 0;
    const MAX_RETRIES = 3;

    try {
      const es = new EventSource(`/api/mascot/proactive/stream?student_id=${state.studentId}`);
      state.eventSource = es;

      es.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.message) {
            showNotification(data.message);
          }
        } catch (e) {}
      };

      es.onerror = () => {
        es.close();
        state.eventSource = null;
        // 端点未实现（404）→ 静默关闭，不重试
        // 网络错误 → 指数退避重连（最多 3 次）
        if (retryCount < MAX_RETRIES && es.readyState === EventSource.CLOSED) {
          retryCount++;
          const delay = Math.min(1000 * Math.pow(2, retryCount), 15000);
          console.warn(`[Mascot] SSE reconnect attempt ${retryCount}/${MAX_RETRIES} in ${delay}ms`);
          setTimeout(connectProactiveSSE, delay);
        }
      };
    } catch (e) {
      // EventSource 构造函数极少抛出，静默降级
      console.warn('[Mascot] SSE init failed (proactive push unavailable)');
    }
  }

  function showNotification(msg) {
    // 使用 kanban.js 的气泡系统
    const bubble = document.querySelector('.app-kanban-bubble');
    if (bubble) {
      bubble.textContent = msg;
      bubble.classList.add('visible');
      setTimeout(() => bubble.classList.remove('visible'), 5000);
    }
  }

  // ===== UI 辅助 =====
  function appendMessage(role, text) {
    if (!panelMessages) return null;
    const el = document.createElement('div');
    el.className = `mascot-msg mascot-msg--${role}`;
    if (role === 'system') el.className += ' mascot-msg--system';
    el.textContent = text;
    panelMessages.appendChild(el);
    panelMessages.scrollTop = panelMessages.scrollHeight;
    return el;
  }

  function appendLoadingBubble() {
    if (!panelMessages) return null;
    const el = document.createElement('div');
    el.className = 'mascot-msg mascot-msg--assistant mascot-msg--loading';
    el.innerHTML = '<span class="mascot-typing"><span></span><span></span><span></span></span>';
    el.id = 'mascot-loading-' + Date.now();
    panelMessages.appendChild(el);
    panelMessages.scrollTop = panelMessages.scrollHeight;
    return el.id;
  }

  function removeLoadingBubble(id) {
    if (!id) return;
    const el = document.getElementById(id);
    if (el) el.remove();
  }

  function spawnParticles() {
    // 简单的星星粒子特效
    const container = document.createElement('div');
    container.className = 'mascot-particles';
    document.body.appendChild(container);
    for (let i = 0; i < 12; i++) {
      const particle = document.createElement('span');
      particle.className = 'mascot-particle';
      particle.textContent = '⭐';
      particle.style.left = (Math.random() * 100) + '%';
      particle.style.animationDelay = (Math.random() * 0.5) + 's';
      particle.style.animationDuration = (1 + Math.random() * 1.5) + 's';
      container.appendChild(particle);
    }
    setTimeout(() => container.remove(), 2000);
  }

  function bindKanbanClick() {
    // 看板娘点击 → 打开对话面板（保留 kanban.js 的点击反应）
    const inner = document.querySelector('.app-kanban-inner');
    if (inner) {
      inner.addEventListener('click', (e) => {
        // 不阻止 kanban.js 的原有行为，追加面板打开
        setTimeout(() => {
          if (!state.panelVisible) openPanel();
        }, 300);
      });
    }
  }

  // ===== 启动 =====
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
```

- [ ] **Step 2: Verify file syntax**

Run: `node --check js/mascot.js` (or just verify no syntax errors via IDE)

- [ ] **Step 3: Commit**

```bash
git add js/mascot.js
git commit -m "feat(mascot): add MascotController — voice, SSE chat, XML commands, particles"
```

---

### Task 3.3: Frontend — Mascot Styles (css/mascot.css)

**Files:**
- Create: `css/mascot.css`

- [ ] **Step 1: Create `css/mascot.css` with panel, particles, and responsive styles**

```css
/* ============================================
   看板娘 AI 助手 — 对话面板 + 粒子特效 + 响应式
   ============================================ */

/* ---- 对话面板 ---- */
.mascot-panel {
  position: fixed;
  bottom: 140px;
  right: 20px;
  width: 360px;
  height: 480px;
  background: var(--surface-glass, rgba(15, 15, 25, 0.92));
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--border-glass, rgba(255, 255, 255, 0.12));
  border-radius: 16px;
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.4), 0 0 80px rgba(99, 102, 241, 0.08);
  display: flex;
  flex-direction: column;
  z-index: 600;
  opacity: 0;
  transform: translateY(16px) scale(0.95);
  pointer-events: none;
  transition: opacity 0.25s ease-out, transform 0.25s ease-out;
}

.mascot-panel.visible {
  opacity: 1;
  transform: translateY(0) scale(1);
  pointer-events: auto;
}

/* Panel Header */
.mascot-panel-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-glass, rgba(255, 255, 255, 0.08));
}

.mascot-panel-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
}

.mascot-panel-expression {
  transition: transform 0.2s ease;
}

.mascot-panel-title {
  flex: 1;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary, #e2e8f0);
}

.mascot-panel-close {
  background: none;
  border: none;
  color: var(--text-secondary, #94a3b8);
  font-size: 20px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: color 0.15s, background 0.15s;
}
.mascot-panel-close:hover {
  color: var(--text-primary, #e2e8f0);
  background: rgba(255, 255, 255, 0.08);
}

/* Messages */
.mascot-panel-messages {
  flex: 1;
  overflow-y: auto;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  scroll-behavior: smooth;
}

.mascot-msg {
  max-width: 85%;
  padding: 8px 12px;
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.5;
  word-break: break-word;
  animation: mascotMsgIn 0.25s ease-out;
}

@keyframes mascotMsgIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.mascot-msg--user {
  align-self: flex-end;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
  border-bottom-right-radius: 4px;
}

.mascot-msg--assistant {
  align-self: flex-start;
  background: var(--surface-elevated, rgba(255, 255, 255, 0.06));
  color: var(--text-primary, #e2e8f0);
  border-bottom-left-radius: 4px;
}

.mascot-msg--system {
  align-self: center;
  background: transparent;
  color: var(--text-tertiary, #64748b);
  font-size: 12px;
  font-style: italic;
}

/* Typing indicator */
.mascot-typing {
  display: inline-flex;
  gap: 4px;
  padding: 4px 0;
}
.mascot-typing span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-tertiary, #64748b);
  animation: mascotTyping 1.4s infinite both;
}
.mascot-typing span:nth-child(2) { animation-delay: 0.2s; }
.mascot-typing span:nth-child(3) { animation-delay: 0.4s; }

@keyframes mascotTyping {
  0%, 80%, 100% { opacity: 0.3; transform: scale(0.8); }
  40% { opacity: 1; transform: scale(1); }
}

/* Input Row */
.mascot-panel-input-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border-top: 1px solid var(--border-glass, rgba(255, 255, 255, 0.08));
}

.mascot-panel-input {
  flex: 1;
  background: var(--surface-elevated, rgba(255, 255, 255, 0.06));
  border: 1px solid var(--border-glass, rgba(255, 255, 255, 0.1));
  border-radius: 20px;
  padding: 8px 14px;
  color: var(--text-primary, #e2e8f0);
  font-size: 13px;
  outline: none;
  transition: border-color 0.15s;
}
.mascot-panel-input:focus {
  border-color: var(--brand, #6366f1);
}

.mascot-panel-mic,
.mascot-panel-send {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: none;
  background: transparent;
  color: var(--text-secondary, #94a3b8);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color 0.15s, background 0.15s;
}
.mascot-panel-send:hover {
  color: var(--brand, #6366f1);
  background: rgba(99, 102, 241, 0.1);
}
.mascot-panel-mic.recording {
  animation: micPulse 1s infinite;
}

@keyframes micPulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }
  50% { box-shadow: 0 0 0 8px rgba(239, 68, 68, 0); }
}

/* ---- 粒子特效 ---- */
.mascot-particles {
  position: fixed;
  bottom: 100px;
  right: 40px;
  width: 200px;
  height: 200px;
  pointer-events: none;
  z-index: 601;
}

.mascot-particle {
  position: absolute;
  bottom: 0;
  font-size: 16px;
  animation: mascotParticleUp 1.5s ease-out forwards;
}

@keyframes mascotParticleUp {
  0% { opacity: 1; transform: translateY(0) scale(1) rotate(0deg); }
  100% { opacity: 0; transform: translateY(-120px) scale(0) rotate(180deg); }
}

/* ---- Responsive ---- */
@media (max-width: 640px) {
  .mascot-panel {
    width: calc(100vw - 16px);
    height: 420px;
    right: 8px;
    bottom: 100px;
    border-radius: 12px;
  }
}

@media (max-width: 400px) {
  .mascot-panel {
    height: 360px;
    bottom: 80px;
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add css/mascot.css
git commit -m "feat(mascot): add mascot panel, particle, and responsive CSS styles"
```

---

### Task 3.4: Frontend — Page Integration

**Files:**
- Modify: `html/hub.html` (add mascot.css + mascot.js references)
- Modify: `html/index.html` (add mascot.css + mascot.js references)

- [ ] **Step 1: Add mascot CSS/JS to `html/hub.html`**

In `<head>`, after existing CSS links, add:
```html
<link rel="stylesheet" href="/css/mascot.css">
```

Before `</body>`, after existing JS scripts, add:
```html
<script src="/js/mascot.js"></script>
```

- [ ] **Step 2: Add mascot CSS/JS to `html/index.html`**

Same two additions as above.

- [ ] **Step 3: Commit**

```bash
git add html/hub.html html/index.html
git commit -m "feat(mascot): integrate mascot CSS/JS into hub and index pages"
```

---

## Phase 4: 双通道导航重构

### Task 4.1: Sidebar Refactor + Old Page Redirects + my-courses 聚合页

**Files:**
- Modify: `html/hub.html` (sidebar HTML — 12→5 entries)
- Modify: `css/hub.css` (sidebar style adjustments — badge + spacing)
- Create: `html/my-courses.html` (new aggregation page)
- Modify: `html/index.html` (add hash-tab handler)
- Modify: `html/personal.html` (add hash-tab handler)
- Modify: 10 old pages — add redirect scripts (socratic-ai, video-player, code, courses, progress, calendar, flow-meter, stellar-showcase, plant, settings)

- [ ] **Step 1: Read current sidebar structure to verify**

Open `html/hub.html` and locate the sidebar `<nav>` element. Identify all 12 navigation items and their group headings.

- [ ] **Step 2: Replace sidebar with 5-entry structure**

Replace the existing sidebar `<nav>` content with:

```html
<nav class="sidebar-nav">
  <div class="sidebar-section">
    <a class="nav-item active" data-section="home" href="/hub.html">
      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
      <span>首页</span>
    </a>
  </div>

  <div class="sidebar-section">
    <a class="nav-item" data-section="ai-qa" href="/index.html">
      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>
      <span>AI 问答</span>
      <span class="sidebar-badge">AI</span>
    </a>
  </div>

  <div class="sidebar-section">
    <a class="nav-item" data-section="my-courses" href="/my-courses.html">
      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 016.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/></svg>
      <span>我的课程</span>
    </a>
  </div>

  <!-- ⚠️ Phase 5 守卫：data-dashboard.html 在 Phase 5 (Task 5.7) 创建。
       Phase 4 部署时此链接指向不存在的页面。hub.js 的侧边栏点击处理器使用
       data-section + hash 切换机制，不会触发页面导航——此 href 仅在直接
       右键新标签页打开等场景生效。Phase 4→5 间为低影响死链。 -->
  <div class="sidebar-section">
    <a class="nav-item" data-section="data" href="/data-dashboard.html">
      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
      <span>学习数据</span>
    </a>
  </div>

  <div class="sidebar-section">
    <a class="nav-item" data-section="profile" href="/personal.html">
      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
      <span>个人中心</span>
    </a>
  </div>
</nav>
```

- [ ] **Step 3a: Add redirect scripts to old standalone pages（9 pages，flow-meter 除外）**

Each page below embeds only its own redirect entry — not the full 9-entry map:

**html/socratic-ai.html:**
```html
<script>
  if (window.top === window.self) { localStorage.setItem('sp_redirect_tab', 'socratic'); window.location.replace('/index.html'); }
</script>
```

**html/video-player.html:**
```html
<script>
  if (window.top === window.self) { localStorage.setItem('sp_redirect_tab', 'video'); window.location.replace('/index.html'); }
</script>
```

**html/code.html:**
```html
<script>
  if (window.top === window.self) { localStorage.setItem('sp_redirect_tab', 'code'); window.location.replace('/index.html'); }
</script>
```

**html/courses.html:**
```html
<script>
  if (window.top === window.self) { localStorage.setItem('sp_redirect_tab', 'courses'); window.location.replace('/my-courses.html'); }
</script>
```

**html/progress.html:**
```html
<script>
  if (window.top === window.self) { localStorage.setItem('sp_redirect_tab', 'progress'); window.location.replace('/my-courses.html'); }
</script>
```

**html/calendar.html:**
```html
<script>
  if (window.top === window.self) { localStorage.setItem('sp_redirect_tab', 'calendar'); window.location.replace('/my-courses.html'); }
</script>
```

**html/stellar-showcase.html:**
```html
<script>
  if (window.top === window.self) { localStorage.setItem('sp_redirect_tab', 'gallery'); window.location.replace('/personal.html'); }
</script>
```

**html/plant.html:**
```html
<script>
  if (window.top === window.self) { localStorage.setItem('sp_redirect_tab', 'ecology'); window.location.replace('/personal.html'); }
</script>
```

**html/settings.html:**
```html
<script>
  if (window.top === window.self) { localStorage.setItem('sp_redirect_tab', 'settings'); window.location.replace('/personal.html'); }
</script>
```

- [ ] **Step 3b: Add hash-tab handler to consolidated parent pages**

Each parent page needs to read the localStorage hint on load and activate the correct tab. Add the following `<script>` block before `</body>` in each target:

**html/index.html** (`/index.html` — AI 问答 + 苏格拉底 + 代码工坊 + 全息视界):
```html
<script>
  (function() {
    // 注意: switchTab() 接受字符串参数 ('chat'/'course'/'code')，参见 js/index.js
    const tab = localStorage.getItem('sp_redirect_tab');
    if (tab) {
      localStorage.removeItem('sp_redirect_tab');
      // socratic-ai / video-player → chat tab（苏格拉底和视频功能在 chat 面板内）
      // code → code tab
      const tabMap = { 'socratic': 'chat', 'video': 'chat', 'code': 'code' };
      const tabName = tabMap[tab];
      if (tabName && typeof switchTab === 'function') {
        switchTab(tabName);
      }
    }
  })();
</script>
```

**html/personal.html** (`/personal.html` — 个人中心 + 生态 + 设置):
```html
<script>
  (function() {
    const tab = localStorage.getItem('sp_redirect_tab');
    if (tab) {
      localStorage.removeItem('sp_redirect_tab');
      const tabMap = { 'gallery': 'stellar-showcase', 'ecology': 'plant', 'settings': 'settings' };
      const sectionId = tabMap[tab];
      if (sectionId) {
        const el = document.getElementById('section-' + sectionId);
        if (el) el.scrollIntoView({ behavior: 'smooth' });
        // 触发对应的 tab 按钮
        const tabBtn = document.querySelector(`[data-tab="${sectionId}"]`);
        if (tabBtn) tabBtn.click();
      }
    }
  })();
</script>
```

**html/my-courses.html** — 此页面将在 Step 3c 创建，hash-tab 逻辑内嵌于页面 JS 中。

> **注意：** `html/data-dashboard.html` 在 Phase 5 才创建，其 hash-tab 逻辑见 Task 5.7。`flow-meter.html` 的重定向在第4阶段部署时，若 `data-dashboard.html` 尚不存在则重定向到 `/data-dashboard.html` 会 404——参见 Step 3d 的依赖处理。

- [ ] **Step 3c: Create `html/my-courses.html`（课程聚合页）**

> 此为 Phase 4 新聚合页面，合并原"课程中心"、"学习进度"、"学习日历"三个入口为三 Tab 页。依赖现有的 `courses.html`、`progress.html`、`calendar.html` 内容通过 AJAX 嵌入。

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>我的课程 · 星识</title>
    <link rel="stylesheet" href="/css/tokens.css">
    <link rel="stylesheet" href="/css/hub.css">
    <link rel="stylesheet" href="/css/courses.css">
    <link rel="stylesheet" href="/css/mascot.css">
    <link rel="stylesheet" href="/css/search-command.css">
    <link rel="stylesheet" href="/css/onboarding.css">
    <style>
        .mc-tabs { display: flex; gap: 4px; padding: 16px 24px; border-bottom: 1px solid var(--cp-card-border); }
        .mc-tab { padding: 8px 20px; border: none; background: none; color: var(--cp-text-secondary); font-size: 14px; cursor: pointer; border-radius: 8px; transition: all 0.15s; }
        .mc-tab.active { background: color-mix(in oklch, var(--info), transparent 88%); color: var(--info); font-weight: 600; }
        .mc-content { padding: 24px; }
        .mc-panel { display: none; }
        .mc-panel.active { display: block; }
    </style>
</head>
<body class="hub-body">
    <div class="mc-tabs">
        <button class="mc-tab active" data-tab="courses">📚 课程中心</button>
        <button class="mc-tab" data-tab="progress">
学习进度</button>
        <button class="mc-tab" data-tab="calendar">📅 学习日历</button>
    </div>
    <div class="mc-content">
        <div class="mc-panel active" id="panel-courses">
            <!-- AJAX 加载 courses.html 主体内容 -->
        </div>
        <div class="mc-panel" id="panel-progress">
            <!-- AJAX 加载 progress.html 主体内容 -->
        </div>
        <div class="mc-panel" id="panel-calendar">
            <!-- AJAX 加载 calendar.html 主体内容 -->
        </div>
    </div>

    <script>
    (function() {
        // Tab 切换
        document.querySelectorAll('.mc-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.mc-tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.mc-panel').forEach(p => p.classList.remove('active'));
                tab.classList.add('active');
                const panel = document.getElementById('panel-' + tab.dataset.tab);
                if (panel) panel.classList.add('active');
            });
        });

        // localStorage redirect tab hint（来自旧页重定向）
        const redirectTab = localStorage.getItem('sp_redirect_tab');
        if (redirectTab) {
            localStorage.removeItem('sp_redirect_tab');
            const btn = document.querySelector(`.mc-tab[data-tab="${redirectTab}"]`);
            if (btn) btn.click();
        }

        // AJAX 延迟加载面板内容
        const panelSources = {
            'courses': '/courses.html',
            'progress': '/progress.html',
            'calendar': '/calendar.html',
        };
        document.querySelectorAll('.mc-tab').forEach(tab => {
            tab.addEventListener('click', function loadOnce() {
                const panelId = 'panel-' + this.dataset.tab;
                const panel = document.getElementById(panelId);
                if (panel && !panel.dataset.loaded) {
                    const url = panelSources[this.dataset.tab];
                    if (url) {
                        fetch(url)
                            .then(r => r.text())
                            .then(html => {
                                const parser = new DOMParser();
                                const doc = parser.parseFromString(html, 'text/html');
                                const main = doc.querySelector('main') || doc.querySelector('.content') || doc.body;
                                panel.innerHTML = main ? main.innerHTML : html;
                                panel.dataset.loaded = 'true';
                            })
                            .catch(() => { panel.innerHTML = '<p style="color:var(--cp-text-tertiary);padding:40px;text-align:center;">加载失败，请刷新重试</p>'; });
                    }
                    this.removeEventListener('click', loadOnce);
                }
            }, { once: false });
        });
    })();
    </script>
    <script src="/js/mascot.js"></script>
    <script src="/js/search-command.js"></script>
    <script src="/js/onboarding.js"></script>
</body>
</html>
```

- [ ] **Step 3d: flow-meter.html 重定向 + Phase 5 部署依赖**

> ⚠️ **部署顺序约束：**
> 1. `html/data-dashboard.html` 在 Phase 5 (Task 5.7 Step 1e) 创建。Phase 4 部署时此文件不存在。
> 2. `flow-meter.html` 的重定向目标为 `/data-dashboard.html`，Phase 5 部署前该页面 404。
> 3. **处理方案：** flow-meter.html 使用 try/catch 守卫 — 先 fetch 探测目标页面是否存在，存在则重定向，不存在则保留原地功能：

**html/flow-meter.html:**
```html
<script>
  // Phase 5 guard: 探测 data-dashboard.html 是否存在
  (async function() {
    if (window.top !== window.self) return;
    try {
      const res = await fetch('/data-dashboard.html', { method: 'HEAD' });
      if (res.ok) {
        localStorage.setItem('sp_redirect_tab', 'flow');
        window.location.replace('/data-dashboard.html');
      }
    } catch(e) {
      // Phase 4: 目标页面不存在，保留 flow-meter 原有功能
      console.log('data-dashboard.html not yet deployed, keeping flow-meter standalone');
    }
  })();
</script>
```

> Phase 5 部署 `data-dashboard.html` 后，flow-meter.html 自动检测并启用重定向，无需手动设置 localStorage flag。

- [ ] **Step 4: Update sidebar CSS in `css/hub.css`（增量叠加，不删除旧规则）**

> **CSS 策略：增量叠加 + 选择性覆盖。** 现有的 `.nav-item`、`.nav-item:hover`、`.nav-item.active`、`.nav-item svg` 规则（hover 高亮、active 态、flex 布局、SVG 图标尺寸）全部保留。追加的 `.hub-sidebar .nav-item` 选择器特异性更高（0,1,1 vs 0,1,0），其 `padding`/`border-radius`/`margin` 值会**覆盖**原有 `.nav-item` 的同名属性。追加 badge 样式 + 精简 sidebar-section 间距。

```css
/* ---- 以下追加到 hub.css 末尾 ---- */

/* 精简侧边栏间距：去掉 group header 后 section 间距减小 */
.hub-sidebar .sidebar-section {
  margin-bottom: 2px;
}

/* 5 项导航条目微调 — 与现有 .nav-item 规则叠加 */
.hub-sidebar .nav-item {
  padding: 10px 16px;
  border-radius: 10px;
  margin: 0 8px;
}

/* AI 角标 */
.sidebar-badge {
  margin-left: auto;
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 8px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
}
```

> **说明：** `.nav-item:hover` / `.nav-item.active` / `.nav-item svg` 等交互态和图标样式**沿用已有 CSS**，无需重复定义，不会出现"无高亮反馈"问题。

- [ ] **Step 5: 验证 `js/hub.js` 无需修改**

新侧边栏使用 `class="nav-item"` + `data-section="..."` — **与旧 HTML 的类名/属性约定完全一致**。现有 hub.js 的以下逻辑**无需任何改动**即可正常工作：

- `e.target.closest('.sidebar-nav .nav-item')` — 点击委托（第 163 行）
- `document.querySelectorAll('.nav-item')` — 遍历激活态（第 3442-3464 行）
- `this.dataset.section` — 读取导航目标（第 3458 行）
- `#sidebar-toggle` / `#hub-sidebar` — 移动端折叠（第 3402-3437 行）

仅需**清理**：搜索 `sidebar-section-label`、`sidebar-group-title` 相关的事件处理代码（旧 group header 的折叠/展开逻辑），移除对已删除 DOM 元素的引用。如不存在此类代码则跳过此步。

- [ ] **Step 6: Commit**

```bash
git add html/hub.html css/hub.css html/my-courses.html html/socratic-ai.html html/video-player.html html/code.html html/courses.html html/progress.html html/calendar.html html/flow-meter.html html/stellar-showcase.html html/plant.html html/settings.html html/index.html html/personal.html
git commit -m "feat(nav): refactor sidebar 12→5 entries, add old-page redirects + my-courses aggregation + hash-tab handlers"
```

---

### Task 4.2: Command Search (js/search-command.js + css/search-command.css)

**Files:**
- Create: `js/search-command.js`
- Create: `css/search-command.css`
- Modify: `html/hub.html` (add Fuse.js CDN + search-command.js reference)

- [ ] **Step 1: Add Fuse.js CDN and search references to `html/hub.html`**

In `<head>`:
```html
<script src="https://cdn.jsdelivr.net/npm/fuse.js@7.0.0/dist/fuse.min.js"></script>
<link rel="stylesheet" href="/css/search-command.css">
```

Before `</body>`:
```html
<script src="/js/search-command.js"></script>
```

- [ ] **Step 2: Create `js/search-command.js`**

```javascript
/**
 * 全局命令搜索 — ⌘K 快捷键
 * 依赖: Fuse.js (CDN)
 */
(function() {
  'use strict';

  let overlay = null;
  let input = null;
  let resultsEl = null;
  let fuse = null;
  let searchIndex = [];

  // ===== 索引构建 =====
  function buildIndex() {
    searchIndex = [
      // 功能入口
      { type: '功能', label: 'AI 问答', desc: '与AI智能对话、苏格拉底教学、代码工坊', route: '/index.html', keywords: 'chat ai socratic code' },
      { type: '功能', label: '我的课程', desc: '查看已生成课程、学习进度、学习日历', route: '/my-courses.html', keywords: 'courses progress calendar' },
      { type: '功能', label: '学习数据', desc: '学习分析大屏、能力雷达、知识图谱', route: '/data-dashboard.html', keywords: 'data analytics dashboard' },
      { type: '功能', label: '个人中心', desc: '个人资料、成就展示、学习生态、设置', route: '/personal.html', keywords: 'profile settings achievements' },
      { type: '功能', label: '代码工坊', desc: 'Python代码编辑与AI批阅', route: '/code.html', keywords: 'code python editor' },
      { type: '功能', label: '苏格拉底教学', desc: 'AI苏格拉底式提问教学', route: '/socratic-ai.html', keywords: 'socratic teaching' },
      { type: '功能', label: '全息视界', desc: '视频学习播放器', route: '/video-player.html', keywords: 'video player' },

      // 课程（从 localStorage 读取）
      ...loadCourseIndex(),
    ];

    fuse = new Fuse(searchIndex, {
      keys: ['label', 'desc', 'keywords'],
      threshold: 0.4,
      includeScore: true,
    });
  }

  function loadCourseIndex() {
    try {
      const courses = JSON.parse(localStorage.getItem('starlearn_courses') || '[]');
      return courses.map(c => ({
        type: '课程',
        label: c.name || c.title || '未命名课程',
        desc: `进度 ${c.progress || 0}%`,
        route: `/course-detail.html?id=${c.id}`,
        keywords: c.subject || '',
      }));
    } catch (e) {
      return [];
    }
  }

  // ===== UI 创建 =====
  function createOverlay() {
    if (overlay) return;

    overlay = document.createElement('div');
    overlay.className = 'cmd-overlay';
    overlay.innerHTML = `
      <div class="cmd-panel">
        <div class="cmd-header">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
          <input class="cmd-input" id="cmd-input" type="text" placeholder="搜索课程、功能或输入指令..." autocomplete="off" />
          <kbd class="cmd-kbd">ESC</kbd>
        </div>
        <div class="cmd-results" id="cmd-results"></div>
        <div class="cmd-footer">
          <span><kbd>↑↓</kbd> 导航</span>
          <span><kbd>Enter</kbd> 打开</span>
          <span><kbd>Esc</kbd> 关闭</span>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);

    input = document.getElementById('cmd-input');
    resultsEl = document.getElementById('cmd-results');

    // 事件
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) close();
    });
    input.addEventListener('input', handleInput);
    input.addEventListener('keydown', handleKeydown);
  }

  function open() {
    buildIndex();
    createOverlay();
    overlay.classList.add('visible');
    input.value = '';
    input.focus();
    renderResults(searchIndex.slice(0, 5));  // 默认显示前5个
  }

  function close() {
    if (overlay) overlay.classList.remove('visible');
    input.value = '';
    if (resultsEl) resultsEl.innerHTML = '';
  }

  // ===== 搜索 =====
  function handleInput() {
    const query = input.value.trim();
    if (!query) {
      renderResults(searchIndex.slice(0, 5));
      return;
    }
    const results = fuse.search(query).slice(0, 8);
    renderResults(results.map(r => r.item));
  }

  function renderResults(items) {
    if (!resultsEl) return;
    if (items.length === 0) {
      resultsEl.innerHTML = '<div class="cmd-empty">没有找到匹配结果</div>';
      return;
    }

    const grouped = {};
    items.forEach(item => {
      if (!grouped[item.type]) grouped[item.type] = [];
      grouped[item.type].push(item);
    });

    let html = '';
    for (const [group, entries] of Object.entries(grouped)) {
      html += `<div class="cmd-group-title">${group}</div>`;
      entries.forEach((item, i) => {
        html += `
          <div class="cmd-result-item" data-route="${item.route}" data-index="${i}">
            <div class="cmd-result-label">${item.label}</div>
            <div class="cmd-result-desc">${item.desc}</div>
            ${item.type === '功能' ? `<div class="cmd-result-arrow">→ ${item.label}</div>` : ''}
          </div>`;
      });
    }
    resultsEl.innerHTML = html;

    // 点击事件
    resultsEl.querySelectorAll('.cmd-result-item').forEach(el => {
      el.addEventListener('click', () => {
        const route = el.dataset.route;
        if (route) {
          window.location.href = route;
          close();
        }
      });
    });
  }

  function handleKeydown(e) {
    if (e.key === 'Escape') {
      close();
    } else if (e.key === 'Enter') {
      const first = resultsEl?.querySelector('.cmd-result-item');
      if (first) {
        window.location.href = first.dataset.route;
        close();
      }
    } else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      const items = resultsEl?.querySelectorAll('.cmd-result-item');
      if (!items || items.length === 0) return;
      const current = resultsEl.querySelector('.cmd-result-item.active');
      let idx = -1;
      if (current) {
        idx = Array.from(items).indexOf(current);
        current.classList.remove('active');
      }
      if (e.key === 'ArrowDown') idx = (idx + 1) % items.length;
      else idx = (idx - 1 + items.length) % items.length;
      items[idx].classList.add('active');
      items[idx].scrollIntoView({ block: 'nearest' });
    }
  }

  // ===== 快捷键 =====
  document.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      open();
    }
  });

  // ===== 暴露 API =====
  window.CommandSearch = { open, close, buildIndex };

  console.log('[CommandSearch] ⌘K ready — Fuse.js indexed', searchIndex.length, 'entries');

})();
```

- [ ] **Step 3: Create `css/search-command.css`**

```css
/* ---- Command Palette Overlay ---- */
.cmd-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 15vh;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.2s ease;
}

.cmd-overlay.visible {
  opacity: 1;
  pointer-events: auto;
}

.cmd-panel {
  width: 560px;
  max-width: calc(100vw - 32px);
  max-height: 480px;
  background: var(--surface-glass, rgba(15, 15, 25, 0.95));
  backdrop-filter: blur(24px);
  border: 1px solid var(--border-glass, rgba(255, 255, 255, 0.12));
  border-radius: 16px;
  box-shadow: 0 16px 64px rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.cmd-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  border-bottom: 1px solid var(--border-glass, rgba(255, 255, 255, 0.08));
}

.cmd-header svg {
  color: var(--text-tertiary, #64748b);
  flex-shrink: 0;
}

.cmd-input {
  flex: 1;
  background: transparent;
  border: none;
  color: var(--text-primary, #e2e8f0);
  font-size: 15px;
  outline: none;
}

.cmd-input::placeholder {
  color: var(--text-tertiary, #64748b);
}

.cmd-kbd {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.08);
  color: var(--text-tertiary, #64748b);
  font-family: inherit;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.cmd-results {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.cmd-group-title {
  padding: 8px 12px 4px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-tertiary, #64748b);
}

.cmd-result-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.1s;
}

.cmd-result-item:hover,
.cmd-result-item.active {
  background: rgba(99, 102, 241, 0.12);
}

.cmd-result-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary, #e2e8f0);
  flex-shrink: 0;
}

.cmd-result-desc {
  flex: 1;
  font-size: 12px;
  color: var(--text-tertiary, #64748b);
}

.cmd-result-arrow {
  font-size: 12px;
  color: var(--brand, #6366f1);
}

.cmd-empty {
  padding: 24px;
  text-align: center;
  color: var(--text-tertiary, #64748b);
  font-size: 14px;
}

.cmd-footer {
  display: flex;
  gap: 16px;
  padding: 10px 16px;
  border-top: 1px solid var(--border-glass, rgba(255, 255, 255, 0.08));
  font-size: 11px;
  color: var(--text-tertiary, #64748b);
}

.cmd-footer kbd {
  font-family: inherit;
  padding: 2px 6px;
  border-radius: 3px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  font-size: 10px;
}
```

- [ ] **Step 4: Commit**

```bash
git add js/search-command.js css/search-command.css html/hub.html
git commit -m "feat(nav): add ⌘K command search with Fuse.js fuzzy matching"
```

---

### Task 4.3: Onboarding System (js/onboarding.js + css/onboarding.css)

**Files:**
- Create: `js/onboarding.js`
- Create: `css/onboarding.css`
- Modify: `html/hub.html` (add onboarding references)

- [ ] **Step 1: Add onboarding references to `html/hub.html`**

In `<head>`:
```html
<link rel="stylesheet" href="/css/onboarding.css">
```

Before `</body>`:
```html
<script src="/js/onboarding.js"></script>
```

- [ ] **Step 2: Create `js/onboarding.js`**

```javascript
/**
 * 新手引导系统 — Spotlight Tour + 学习画像引导
 * 状态: localStorage('starlearn_onboarding_completed')
 */
(function() {
  'use strict';

  const STORAGE_KEY = 'starlearn_onboarding_completed';

  // 跳过参数: ?skip-onboarding=1
  if (window.location.search.includes('skip-onboarding=1')) return;
  if (localStorage.getItem(STORAGE_KEY)) return;

  let currentStep = 0;
  let overlay = null;
  let spotlight = null;
  let tooltip = null;

  const STEPS = [
    {
      target: '[data-section="ai-qa"]',
      title: 'AI 问答',
      description: '在这里，你可以和AI对话、生成课程、写代码练习——一个入口搞定所有学习需求。',
      position: 'right',
    },
    {
      target: '[data-section="my-courses"]',
      title: '我的课程',
      description: '所有AI生成的课程都在这里，随时查看学习进度和日程安排。',
      position: 'right',
    },
    {
      target: '.app-kanban',
      title: '看板娘 · 小星',
      description: '随时点击右下角呼叫我，语音或打字都可以——导航、答疑、伴学，我都在~',
      position: 'top',
    },
  ];

  function init() {
    // 等待看板娘先加载
    setTimeout(() => {
      // 看板娘招手
      showMascotGreeting();
      // 开始 spotlight tour
      setTimeout(startTour, 2000);
    }, 1500);
  }

  function showMascotGreeting() {
    const bubble = document.querySelector('.app-kanban-bubble');
    if (bubble) {
      bubble.textContent = '欢迎来到星识！我是小星~';
      bubble.classList.add('visible');
      setTimeout(() => bubble.classList.remove('visible'), 4000);
    }
  }

  function startTour() {
    createOverlay();
    showStep(0);
  }

  function createOverlay() {
    overlay = document.createElement('div');
    overlay.className = 'onboard-overlay';

    spotlight = document.createElement('div');
    spotlight.className = 'onboard-spotlight';

    tooltip = document.createElement('div');
    tooltip.className = 'onboard-tooltip';
    tooltip.innerHTML = `
      <div class="onboard-tooltip-title"></div>
      <div class="onboard-tooltip-desc"></div>
      <div class="onboard-tooltip-actions">
        <button class="onboard-btn onboard-btn--skip" id="onboard-skip">跳过</button>
        <span class="onboard-dots" id="onboard-dots"></span>
        <button class="onboard-btn onboard-btn--next" id="onboard-next">下一步</button>
      </div>
    `;

    overlay.appendChild(spotlight);
    overlay.appendChild(tooltip);
    document.body.appendChild(overlay);

    document.getElementById('onboard-skip').addEventListener('click', finish);
    document.getElementById('onboard-next').addEventListener('click', () => {
      if (currentStep < STEPS.length - 1) {
        showStep(currentStep + 1);
      } else {
        finish();
      }
    });
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) finish();
    });
  }

  function showStep(index) {
    currentStep = index;
    const step = STEPS[index];
    const target = document.querySelector(step.target);

    if (!target) {
      // target not found, skip to next
      if (index < STEPS.length - 1) showStep(index + 1);
      else finish();
      return;
    }

    // Show overlay
    overlay.classList.add('visible');

    // Position spotlight
    const rect = target.getBoundingClientRect();
    const pad = 8;
    Object.assign(spotlight.style, {
      left: (rect.left - pad) + 'px',
      top: (rect.top - pad) + 'px',
      width: (rect.width + pad * 2) + 'px',
      height: (rect.height + pad * 2) + 'px',
    });
    spotlight.classList.add('visible');

    // Position tooltip
    const ttipRect = tooltip.getBoundingClientRect();
    let ttipLeft, ttipTop;
    const gap = 16;

    if (step.position === 'right') {
      ttipLeft = rect.right + gap;
      ttipTop = rect.top + rect.height / 2 - 80;
    } else if (step.position === 'top') {
      ttipLeft = rect.left + rect.width / 2 - 140;
      ttipTop = rect.top - 200;
    } else {
      ttipLeft = rect.left;
      ttipTop = rect.bottom + gap;
    }

    // Clamp to viewport
    ttipLeft = Math.max(16, Math.min(ttipLeft, window.innerWidth - 300));
    ttipTop = Math.max(16, Math.min(ttipTop, window.innerHeight - 220));

    Object.assign(tooltip.style, {
      left: ttipLeft + 'px',
      top: ttipTop + 'px',
    });
    tooltip.classList.add('visible');

    // Update content
    tooltip.querySelector('.onboard-tooltip-title').textContent = step.title;
    tooltip.querySelector('.onboard-tooltip-desc').textContent = step.description;

    // Update dots
    const dots = document.getElementById('onboard-dots');
    dots.innerHTML = STEPS.map((_, i) =>
      `<span class="onboard-dot ${i === index ? 'active' : ''}"></span>`
    ).join('');

    // Update button text
    const nextBtn = document.getElementById('onboard-next');
    nextBtn.textContent = index === STEPS.length - 1 ? '开始探索' : '下一步';
  }

  function finish() {
    overlay.classList.remove('visible');
    spotlight.classList.remove('visible');
    tooltip.classList.remove('visible');
    localStorage.setItem(STORAGE_KEY, 'true');
    setTimeout(() => {
      if (overlay) overlay.remove();
    }, 300);
  }

  // ===== 暴露重新触发 =====
  window.Onboarding = {
    restart: () => {
      localStorage.removeItem(STORAGE_KEY);
      init();
    },
  };

  // ===== 自动启动 =====
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
```

- [ ] **Step 3: Create `css/onboarding.css`**

```css
/* ---- Onboarding Spotlight ---- */
.onboard-overlay {
  position: fixed;
  inset: 0;
  z-index: 900;
  background: rgba(0, 0, 0, 0.6);
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.3s ease;
}

.onboard-overlay.visible {
  opacity: 1;
  pointer-events: auto;
}

.onboard-spotlight {
  position: fixed;
  z-index: 901;
  border-radius: 12px;
  box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.6), 0 0 24px rgba(99, 102, 241, 0.3);
  opacity: 0;
  transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
}

.onboard-spotlight.visible {
  opacity: 1;
}

.onboard-tooltip {
  position: fixed;
  z-index: 902;
  width: 280px;
  background: var(--surface-glass, rgba(15, 15, 25, 0.95));
  backdrop-filter: blur(20px);
  border: 1px solid var(--border-glass, rgba(255, 255, 255, 0.15));
  border-radius: 14px;
  padding: 20px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
  opacity: 0;
  transform: translateY(8px);
  transition: all 0.3s ease;
}

.onboard-tooltip.visible {
  opacity: 1;
  transform: translateY(0);
}

.onboard-tooltip-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary, #e2e8f0);
  margin-bottom: 8px;
}

.onboard-tooltip-desc {
  font-size: 13px;
  color: var(--text-secondary, #94a3b8);
  line-height: 1.6;
  margin-bottom: 16px;
}

.onboard-tooltip-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.onboard-btn {
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: background 0.15s;
}

.onboard-btn--skip {
  background: transparent;
  color: var(--text-tertiary, #64748b);
}
.onboard-btn--skip:hover {
  color: var(--text-secondary, #94a3b8);
}

.onboard-btn--next {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
}
.onboard-btn--next:hover {
  background: linear-gradient(135deg, #4f46e5, #7c3aed);
}

.onboard-dots {
  display: flex;
  gap: 6px;
}

.onboard-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  transition: background 0.2s;
}
.onboard-dot.active {
  background: var(--brand, #6366f1);
  width: 16px;
  border-radius: 3px;
}
```

- [ ] **Step 4: Commit**

```bash
git add js/onboarding.js css/onboarding.css html/hub.html
git commit -m "feat(nav): add onboarding spotlight tour with 3-step guide"
```

---

## Phase 5: 知域迁移（教师端 + 数据大屏）

### Alpine.js 迁移计划

完整的前端 Alpine.js 3.14 迁移方案见: [2026-06-06-alpinejs-migration-plan.md](./2026-06-06-alpinejs-migration-plan.md)

迁移要点:
- 所有 Phase 5 页面使用 Alpine.js 3.14.9 CDN 替代原 jQuery/Bootstrap
- 统一使用 Constellation Prism (星座棱晶) 设计语言，与 hub.html 风格一致
- 后端 FastAPI API 保持不变
- 使用 data-theme="starry-night" 暗色主题，通过 tokens.css 变量驱动全站配色

### Task 5.0: Backend — db.py 通用查询辅助函数

**Files:**
- Modify: `db.py`

> **背景：** 现有 `db.py` 无通用 `query_one`/`query_all`/`execute`/`save_memory` 函数，每个功能手写内联 SQL。以下 4 个辅助函数封装 `get_db()` + SQLite/MySQL 双后端兼容，供 Phase 5 所有 API 端点使用。

- [ ] **Step 1: 在 `db.py` 末尾追加通用查询/执行函数**

```python
# ===== 通用数据库辅助函数（供 API 端点使用） =====

def _is_mysql(conn) -> bool:
    """检测当前数据库连接是否为 MySQL/pymysql"""
    try:
        import pymysql
        return isinstance(conn, pymysql.Connection)
    except ImportError:
        return False

def _is_sqlite(conn) -> bool:
    """检测当前数据库连接是否为 SQLite"""
    import sqlite3
    return isinstance(conn, sqlite3.Connection)

def _normalize_placeholders(sql: str, conn) -> str:
    """统一占位符：接受 ? 或 %s，根据后端自动转换。
    - MySQL/pymysql: 需要 %s 占位符
    - SQLite: 需要 ? 占位符
    调用方可以任意使用 ? 或 %s，此函数确保兼容。"""
    if _is_mysql(conn):
        return sql.replace("?", "%s")    # ? → %s for MySQL
    else:
        return sql.replace("%s", "?")    # %s → ? for SQLite

def execute(sql: str, params: tuple = ()) -> int:
    """执行 INSERT/UPDATE/DELETE，返回 lastrowid"""
    with get_db() as conn:
        if conn is not None:
            cursor = conn.cursor()
            sql = _normalize_placeholders(sql, conn)
            cursor.execute(sql, params)
            conn.commit()
            lastid = cursor.lastrowid
            cursor.close()
            return lastid
        else:
            # JSON fallback: 返回模拟 ID
            return 1

def query_one(sql: str, params: tuple = ()) -> dict | None:
    """执行 SELECT，返回单行 dict 或 None"""
    with get_db() as conn:
        if conn is not None:
            cursor = conn.cursor()
            sql = _normalize_placeholders(sql, conn)
            cursor.execute(sql, params)
            row = cursor.fetchone()
            cursor.close()
            if row is None:
                return None
            if hasattr(row, "keys"):
                return dict(row)
            # sqlite3.Row 或普通 tuple
            cols = [d[0] for d in cursor.description]
            return dict(zip(cols, row))
        else:
            return None

def query_all(sql: str, params: tuple = ()) -> list[dict]:
    """执行 SELECT，返回 dict 列表"""
    with get_db() as conn:
        if conn is not None:
            cursor = conn.cursor()
            sql = _normalize_placeholders(sql, conn)
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            cursor.close()
            if not rows:
                return []
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, r)) for r in rows]
        else:
            return []

def save_memory(user_id: str, memory_data: dict) -> bool:
    """保存用户记忆 — 写入 memories 表（如不存在则创建）"""
    import uuid
    from datetime import datetime
    mid = str(uuid.uuid4())[:8]
    content = memory_data.get("content", "")
    mem_type = memory_data.get("type", "general")
    mem_source = memory_data.get("source", "mascot")
    try:
        execute(
            "INSERT INTO memories (id, user_id, type, content, source, created_at) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (mid, str(user_id), mem_type, content[:500], mem_source, datetime.now())
        )
        return True
    except Exception:
        # 表不存在时静默失败（非关键路径）
        return False
```

- [ ] **Step 2: 验证函数导入**

Run: `python -c "from db import execute, query_one, query_all, save_memory; print('OK')"`
Expected: `OK` (无 ImportError)

- [ ] **Step 3: Commit**

```bash
git add db.py
git commit -m "feat(db): add generic query_one/query_all/execute/save_memory helpers"
```

---

### Task 5.1: Backend — JWT Auth Utilities

**Files:**
- Create: `app/utils/jwt.py`
- Create: `app/middleware/__init__.py` (empty)
- Create: `app/middleware/auth.py`
- Create: `app/middleware/roles.py`

- [ ] **Step 1: Create `app/utils/jwt.py`**

```python
# -*- coding: utf-8 -*-
"""JWT 生成与验证 — 荷载与知域一致: {uid, username, role}"""

from __future__ import annotations

import os
import time
import jwt

JWT_SECRET = os.environ.get("JWT_SECRET", "starlearn_jwt_secret_change_me")
JWT_EXPIRE_HOURS = int(os.environ.get("JWT_EXPIRE_HOURS", "24"))
JWT_ALGORITHM = "HS256"


def create_token(uid: int, username: str, role: str) -> str:
    """生成 JWT token，荷载与知域 sp_token 兼容"""
    now = int(time.time())
    payload = {
        "uid": uid,
        "username": username,
        "role": role,
        "iat": now,
        "exp": now + JWT_EXPIRE_HOURS * 3600,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> dict | None:
    """验证 JWT token，返回荷载或 None"""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def get_token_from_header(authorization: str | None) -> str | None:
    """从 Authorization: Bearer <token> 头提取 token"""
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None
```

- [ ] **Step 2: 创建 `app/middleware/` 目录**

```bash
mkdir -p app/middleware
```

- [ ] **Step 3: Create `app/middleware/__init__.py`**

```python
# Middleware package
```

- [ ] **Step 4: Create `app/middleware/auth.py`**

```python
# -*- coding: utf-8 -*-
"""认证中间件 — FastAPI Depends 注入 current_user"""

from __future__ import annotations

from fastapi import Request, HTTPException, Depends
from app.utils.jwt import verify_token, get_token_from_header


class CurrentUser:
    """当前认证用户"""
    def __init__(self, uid: int, username: str, role: str):
        self.uid = uid
        self.username = username
        self.role = role

    def is_teacher(self) -> bool:
        return self.role in ("teacher", "admin")

    def is_admin(self) -> bool:
        return self.role == "admin"


async def get_current_user(request: Request) -> CurrentUser:
    """FastAPI Depends: 从请求头提取并验证 JWT，返回 CurrentUser"""
    auth_header = request.headers.get("Authorization")
    token = get_token_from_header(auth_header)
    if not token:
        raise HTTPException(status_code=401, detail="未提供认证令牌")

    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="令牌无效或已过期")

    return CurrentUser(
        uid=payload["uid"],
        username=payload["username"],
        role=payload["role"],
    )


# 可选认证（不强制，但解析 token 如果存在）
async def get_optional_user(request: Request) -> CurrentUser | None:
    try:
        return await get_current_user(request)
    except HTTPException:
        return None
```

- [ ] **Step 5: Create `app/middleware/roles.py`**

```python
# -*- coding: utf-8 -*-
"""角色守卫 — @require_role 装饰器"""

from __future__ import annotations

from functools import wraps
from fastapi import HTTPException
from app.middleware.auth import CurrentUser


def require_role(*roles: str):
    """装饰器：要求当前用户属于指定角色之一。

    Usage:
        @router.get("/teacher/dashboard")
        @require_role("teacher", "admin")
        async def dashboard(user: CurrentUser = Depends(get_current_user)):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从 kwargs 中查找 CurrentUser
            user = None
            for v in kwargs.values():
                if isinstance(v, CurrentUser):
                    user = v
                    break
            if not user:
                raise HTTPException(status_code=401, detail="未认证")

            if user.role not in roles and user.role != "admin":
                raise HTTPException(status_code=403, detail="权限不足")

            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

> **⚠️ FastAPI 兼容性说明:** `functools.wraps` 会保留 `__wrapped__` 链，FastAPI 的 `inspect.signature()` 可以跟随此链找到原始函数签名，因此 `Depends(get_current_user)` 的依赖注入仍能正常工作。但若遇到依赖注入失败，替代方案是将 `require_role` 改为 FastAPI Dependency（而非装饰器）：
> ```python
> # 替代方案：作为 FastAPI Depends 使用
> def require_role(*roles: str):
>     async def checker(user: CurrentUser = Depends(get_current_user)):
>         if user.role not in roles and user.role != "admin":
>             raise HTTPException(403, "权限不足")
>         return user
>     return checker
> # 用法: dashboard(user: CurrentUser = Depends(require_role("teacher", "admin")))
> ```
> 装饰器方案更简洁，Dependency 方案更符合 FastAPI 惯例。当前计划使用装饰器方案，如出现问题可切换到 Dependency 方案。

- [ ] **Step 6: Verify JWT utility**

Run: `python -c "from app.utils.jwt import create_token, verify_token; t = create_token(1, 'test', 'teacher'); print(verify_token(t))"`
Expected: `{'uid': 1, 'username': 'test', 'role': 'teacher', ...}`

- [ ] **Step 7: Commit**

```bash
git add app/utils/jwt.py app/middleware/__init__.py app/middleware/auth.py app/middleware/roles.py
git commit -m "feat(auth): add JWT utilities + FastAPI auth middleware + role guard"
```

---

### Task 5.2: Backend — Auth API Routes

**Files:**
- Create: `app/api/auth.py`
- Modify: `main.py` (register auth router)

- [ ] **Step 1: Create `app/api/auth.py`**

```python
# -*- coding: utf-8 -*-
"""认证 API — 移植自知域 AuthController"""

from __future__ import annotations

import hashlib
import logging

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.utils.jwt import create_token
from app.middleware.auth import get_current_user, CurrentUser

logger = logging.getLogger("starlearn.api.auth")

router = APIRouter(tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    role: str = "student"
    display_name: str | None = None


class UpdateMeRequest(BaseModel):
    display_name: str | None = None
    avatar: str | None = None


# ===== 白名单：不需要认证的路径前缀 =====
PUBLIC_PATHS = ["/api/auth/login", "/api/auth/register"]


@router.post("/login")
async def login(req: LoginRequest):
    """登录 — 验证用户名/密码，返回 JWT token"""
    try:
        from db import query_one
        user = query_one(
            "SELECT id, username, password_hash, role, display_name FROM sp_user WHERE username = %s",
            (req.username,)
        )
        if not user:
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        # SHA-256 密码验证（与知域兼容）
        password_hash_input = hashlib.sha256(req.password.encode()).hexdigest()
        if password_hash_input != user["password_hash"]:
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        token = create_token(user["id"], user["username"], user["role"])
        return {
            "token": token,
            "userId": user["id"],
            "username": user["username"],
            "role": user["role"],
            "displayName": user.get("display_name", user["username"]),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail=f"登录失败: {e}")


@router.post("/register")
async def register(req: RegisterRequest):
    """注册 — 默认 student 角色"""
    try:
        from db import execute, query_one

        # 检查用户名重复
        existing = query_one(
            "SELECT id FROM sp_user WHERE username = %s", (req.username,)
        )
        if existing:
            raise HTTPException(status_code=409, detail="用户名已存在")

        # 规范化角色
        role = req.role if req.role in ("student", "teacher", "admin") else "student"
        display_name = req.display_name or req.username
        password_hash = hashlib.sha256(req.password.encode()).hexdigest()

        user_id = execute(
            """INSERT INTO sp_user (username, password_hash, role, display_name)
               VALUES (%s, %s, %s, %s)""",
            (req.username, password_hash, role, display_name)
        )

        token = create_token(user_id, req.username, role)
        return {
            "token": token,
            "userId": user_id,
            "username": req.username,
            "role": role,
            "displayName": display_name,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Register error: {e}")
        raise HTTPException(status_code=500, detail=f"注册失败: {e}")


@router.get("/me")
async def me(user: CurrentUser = Depends(get_current_user)):
    """获取当前用户信息"""
    try:
        from db import query_one
        u = query_one(
            "SELECT id, username, role, display_name, avatar FROM sp_user WHERE id = %s",
            (user.uid,)
        )
        if not u:
            raise HTTPException(status_code=404, detail="用户不存在")
        return {
            "userId": u["id"],
            "username": u["username"],
            "role": u["role"],
            "displayName": u.get("display_name", u["username"]),
            "avatarUrl": u.get("avatar", ""),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取用户信息失败: {e}")


@router.put("/me")
async def update_me(req: UpdateMeRequest, user: CurrentUser = Depends(get_current_user)):
    """更新当前用户信息"""
    try:
        from db import execute
        fields = []
        values = []
        update_data = req.model_dump(exclude_none=True)
        for key, val in update_data.items():
            fields.append(f"{key} = %s")
            values.append(val)
        if not fields:
            return {"success": True, "message": "无更新字段"}
        values.append(user.uid)
        execute(
            f"UPDATE sp_user SET {', '.join(fields)} WHERE id = %s",
            tuple(values)
        )
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新失败: {e}")


@router.get("/teacher/ping")
async def teacher_ping(user: CurrentUser = Depends(get_current_user)):
    """教师权限测试端点"""
    if not user.is_teacher():
        raise HTTPException(status_code=403, detail="需要教师权限")
    return {"success": True, "message": f"教师 {user.username} 认证通过"}
```

- [ ] **Step 2: Register auth router in `main.py`**

```python
# ---- Auth API (JWT认证) ----
from app.api.auth import router as auth_router
app.include_router(auth_router, prefix="/api/auth")
```

- [ ] **Step 3: Commit**

```bash
git add app/api/auth.py main.py
git commit -m "feat(auth): add /api/auth/{login,register,me} endpoints with JWT"
```

---

### Task 5.3: Backend — Teacher API Routes

**Files:**
- Create: `app/api/teacher.py`
- Modify: `main.py` (register teacher router)

- [ ] **Step 1: Create `app/api/teacher.py` with all 25 teacher endpoints**

This is the largest file in Phase 5. Due to its size, the core pattern for each endpoint follows the existing API conventions:

```python
# -*- coding: utf-8 -*-
"""教师端 API — 仪表盘/班级/题库/考试/内容审核"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from app.middleware.auth import get_current_user, CurrentUser

logger = logging.getLogger("starlearn.api.teacher")
router = APIRouter(tags=["teacher"])

# ===== Request Models =====

class ClassCreate(BaseModel):
    name: str
    description: str = ""

class QuestionCreate(BaseModel):
    type: str          # choice/blank/code/essay
    content: str
    options: list | None = None
    answer: str
    difficulty: str = "medium"
    tags: list | None = None
    course_id: int | None = None

class ImportQuestionsRequest(BaseModel):
    questions: list[dict] = []   # [{type, content, options, answer, difficulty, tags, course_id}]

class ExamCreate(BaseModel):
    title: str
    description: str = ""
    question_ids: list[int] = []
    class_ids: list[int] = []
    start_time: str | None = None
    end_time: str | None = None
    duration: int = 120

class GradeRequest(BaseModel):
    """教师确认/修改分数"""
    scores: list[dict]  # [{result_id, score, comment}]

class ContentGenerateRequest(BaseModel):
    lesson_id: int
    model: str | None = None  # LLM 模型选择，如 gpt-4o，默认 gpt-4o


# ===== Helper: ensure teacher role =====

def require_teacher(user: CurrentUser):
    if not user.is_teacher():
        raise HTTPException(status_code=403, detail="需要教师权限")
    return user


# ===== Dashboard =====

@router.get("/dashboard")
async def dashboard(user: CurrentUser = Depends(get_current_user)):
    """教师仪表盘统计"""
    require_teacher(user)
    try:
        from db import query_one, query_all
        stats = query_one("""
            SELECT
                (SELECT COUNT(*) FROM classes WHERE teacher_id = %s) as class_count,
                (SELECT COUNT(*) FROM courses WHERE teacher_id = %s) as course_count,
                (SELECT COUNT(*) FROM exam_results WHERE graded = 0 AND exam_id IN
                    (SELECT id FROM exams WHERE teacher_id = %s)) as pending_grading
        """, (user.uid, user.uid, user.uid))
        # 计算该教师下所有学生的平均考试成绩（通过 class_students 关联）
        avg_score = query_one("""
            SELECT AVG(er.score) as avg_score
            FROM exam_results er
            JOIN class_students cs ON er.student_id = cs.student_id
            JOIN classes c ON cs.class_id = c.id
            WHERE c.teacher_id = %s AND er.score IS NOT NULL
        """, (user.uid,))
        return {"success": True, "stats": {
            "classCount": stats["class_count"] if stats else 0,
            "courseCount": stats["course_count"] if stats else 0,
            "pendingGrading": stats["pending_grading"] if stats else 0,
            "avgScore": round(avg_score["avg_score"], 1) if avg_score and avg_score["avg_score"] else 0,
        }}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== Classes CRUD =====

@router.get("/classes")
async def list_classes(user: CurrentUser = Depends(get_current_user)):
    require_teacher(user)
    from db import query_all
    rows = query_all(
        "SELECT * FROM classes WHERE teacher_id = %s ORDER BY created_at DESC",
        (user.uid,)
    )
    return {"success": True, "classes": rows or []}

@router.post("/class")
async def create_class(req: ClassCreate, user: CurrentUser = Depends(get_current_user)):
    require_teacher(user)
    from db import execute
    cid = execute(
        "INSERT INTO classes (teacher_id, name, description) VALUES (%s, %s, %s)",
        (user.uid, req.name, req.description)
    )
    return {"success": True, "id": cid}

@router.put("/class/{class_id}")
async def update_class(class_id: int, req: ClassCreate, user: CurrentUser = Depends(get_current_user)):
    require_teacher(user)
    from db import execute
    execute(
        "UPDATE classes SET name=%s, description=%s WHERE id=%s AND teacher_id=%s",
        (req.name, req.description, class_id, user.uid)
    )
    return {"success": True}

@router.delete("/class/{class_id}")
async def delete_class(class_id: int, user: CurrentUser = Depends(get_current_user)):
    require_teacher(user)
    from db import execute
    execute("DELETE FROM classes WHERE id=%s AND teacher_id=%s", (class_id, user.uid))
    return {"success": True}


# ===== Students (花名册) =====

@router.get("/students/{class_id}")
async def list_students(class_id: int, user: CurrentUser = Depends(get_current_user)):
    require_teacher(user)
    from db import query_all
    rows = query_all("""
        SELECT u.id, u.username, u.display_name, cs.joined_at
        FROM class_students cs JOIN sp_user u ON cs.student_id = u.id
        WHERE cs.class_id = %s
    """, (class_id,))
    return {"success": True, "students": rows or []}

class ImportStudentsRequest(BaseModel):
    class_id: int
    students: list[dict] = []   # [{username, display_name}]

@router.post("/students/import")
async def import_students(req: ImportStudentsRequest, user: CurrentUser = Depends(get_current_user)):
    """批量导入学生 CSV"""
    require_teacher(user)
    from db import execute, query_one
    class_id = req.class_id
    count = 0
    for s in req.students:
        u = query_one("SELECT id FROM sp_user WHERE username = %s", (s["username"],))
        if u:
            # 跨 DB 兼容：先检查是否存在，避免重复插入
            existing = query_one(
                "SELECT 1 FROM class_students WHERE class_id=%s AND student_id=%s",
                (class_id, u["id"])
            )
            if not existing:
                execute(
                    "INSERT INTO class_students (class_id, student_id) VALUES (%s, %s)",
                    (class_id, u["id"])
                )
                count += 1
    execute("UPDATE classes SET student_count = (SELECT COUNT(*) FROM class_students WHERE class_id = %s) WHERE id = %s", (class_id, class_id))
    return {"success": True, "imported": count}


# ===== Questions CRUD =====

@router.get("/questions")
async def list_questions(
    type: str | None = None, difficulty: str | None = None, search: str | None = None,
    user: CurrentUser = Depends(get_current_user)
):
    require_teacher(user)
    from db import query_all
    sql = "SELECT * FROM questions WHERE teacher_id = %s"
    params = [user.uid]
    if type:
        sql += " AND type = %s"; params.append(type)
    if difficulty:
        sql += " AND difficulty = %s"; params.append(difficulty)
    if search:
        sql += " AND content LIKE %s"; params.append(f"%{search}%")
    sql += " ORDER BY created_at DESC LIMIT 200"
    rows = query_all(sql, tuple(params))
    return {"success": True, "questions": rows or []}

@router.post("/question")
async def create_question(req: QuestionCreate, user: CurrentUser = Depends(get_current_user)):
    require_teacher(user)
    from db import execute
    qid = execute(
        """INSERT INTO questions (teacher_id, type, content, options_json, answer, difficulty, tags, course_id)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
        (user.uid, req.type, req.content, json.dumps(req.options) if req.options else None,
         req.answer, req.difficulty, json.dumps(req.tags) if req.tags else None, req.course_id)
    )
    return {"success": True, "id": qid}

@router.put("/question/{qid}")
async def update_question(qid: int, req: QuestionCreate, user: CurrentUser = Depends(get_current_user)):
    require_teacher(user)
    from db import execute
    execute(
        """UPDATE questions SET type=%s, content=%s, options_json=%s, answer=%s, difficulty=%s, tags=%s, course_id=%s
           WHERE id=%s AND teacher_id=%s""",
        (req.type, req.content, json.dumps(req.options) if req.options else None,
         req.answer, req.difficulty, json.dumps(req.tags) if req.tags else None, req.course_id,
         qid, user.uid)
    )
    return {"success": True}

@router.delete("/question/{qid}")
async def delete_question(qid: int, user: CurrentUser = Depends(get_current_user)):
    require_teacher(user)
    from db import execute
    execute("DELETE FROM questions WHERE id=%s AND teacher_id=%s", (qid, user.uid))
    return {"success": True}

@router.post("/questions/import")
async def import_questions(req: ImportQuestionsRequest, user: CurrentUser = Depends(get_current_user)):
    """批量导入题目 — req.questions = [{type, content, options, answer, difficulty, tags, course_id}]"""
    require_teacher(user)
    from db import execute
    count = 0
    for q in req.questions:
        execute(
            """INSERT INTO questions (teacher_id, type, content, options_json, answer, difficulty, tags, course_id)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
            (user.uid, q["type"], q["content"],
             json.dumps(q.get("options")), q["answer"],
             q.get("difficulty", "medium"), json.dumps(q.get("tags")),
             q.get("course_id")))
        count += 1
    return {"success": True, "imported": count}


# ===== Exams CRUD =====

@router.get("/exams")
async def list_exams(user: CurrentUser = Depends(get_current_user)):
    require_teacher(user)
    from db import query_all
    rows = query_all("SELECT * FROM exams WHERE teacher_id=%s ORDER BY created_at DESC", (user.uid,))
    return {"success": True, "exams": rows or []}

@router.post("/exam")
async def create_exam(req: ExamCreate, user: CurrentUser = Depends(get_current_user)):
    require_teacher(user)
    from db import execute
    eid = execute(
        """INSERT INTO exams (teacher_id, title, description, questions_json, class_ids_json,
           start_time, end_time, duration)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
        (user.uid, req.title, req.description,
         json.dumps(req.question_ids), json.dumps(req.class_ids),
         req.start_time, req.end_time, req.duration)
    )
    return {"success": True, "id": eid}

@router.put("/exam/{exam_id}")
async def update_exam(exam_id: int, req: ExamCreate, user: CurrentUser = Depends(get_current_user)):
    require_teacher(user)
    from db import execute
    execute(
        "UPDATE exams SET title=%s, description=%s, questions_json=%s, class_ids_json=%s, start_time=%s, end_time=%s, duration=%s WHERE id=%s AND teacher_id=%s",
        (req.title, req.description, json.dumps(req.question_ids), json.dumps(req.class_ids),
         req.start_time, req.end_time, req.duration, exam_id, user.uid)
    )
    return {"success": True}

@router.delete("/exam/{exam_id}")
async def delete_exam(exam_id: int, user: CurrentUser = Depends(get_current_user)):
    require_teacher(user)
    from db import execute
    execute("DELETE FROM exams WHERE id=%s AND teacher_id=%s", (exam_id, user.uid))
    return {"success": True}

@router.post("/exam/{exam_id}/publish")
async def publish_exam(exam_id: int, user: CurrentUser = Depends(get_current_user)):
    require_teacher(user)
    from db import execute
    execute("UPDATE exams SET status='published' WHERE id=%s AND teacher_id=%s", (exam_id, user.uid))
    return {"success": True}

@router.get("/exam/{exam_id}/results")
async def get_exam_results(exam_id: int, user: CurrentUser = Depends(get_current_user)):
    require_teacher(user)
    from db import query_all
    results = query_all(
        "SELECT er.*, s.display_name FROM exam_results er JOIN sp_user s ON er.student_id=s.id WHERE er.exam_id=%s",
        (exam_id,)
    )
    return {"success": True, "results": results}

@router.post("/exam/{exam_id}/grade")
async def start_grade_exam(exam_id: int, user: CurrentUser = Depends(get_current_user)):
    require_teacher(user)
    from db import query_all
    # 获取该考试所有待批阅的答卷
    ungraded = query_all(
        "SELECT er.id, er.student_id, er.answers_json, s.display_name FROM exam_results er JOIN sp_user s ON er.student_id=s.id WHERE er.exam_id=%s AND er.graded = 0",
        (exam_id,)
    )
    return {"success": True, "ungraded": ungraded, "count": len(ungraded)}

@router.put("/exam/{exam_id}/grade")
async def submit_grade_exam(exam_id: int, req: GradeRequest, user: CurrentUser = Depends(get_current_user)):
    require_teacher(user)
    from db import execute
    from datetime import datetime
    for g in req.scores:
        execute(
            "UPDATE exam_results SET score=%s, comment=%s, graded=1, graded_at=%s WHERE id=%s AND exam_id=%s",
            (g["score"], g.get("comment", ""), datetime.now(), g["result_id"], exam_id)
        )
    return {"success": True}

@router.get("/exam/{exam_id}/analysis")
async def get_exam_analysis(exam_id: int, user: CurrentUser = Depends(get_current_user)):
    require_teacher(user)
    from db import query_one, query_all
    stats = query_one(
        "SELECT AVG(score) as avg_score, MAX(score) as max_score, MIN(score) as min_score, COUNT(*) as total FROM exam_results WHERE exam_id=%s AND score IS NOT NULL",
        (exam_id,)
    )
    distribution = query_all(
        "SELECT FLOOR(score/10)*10 as bucket, COUNT(*) as count FROM exam_results WHERE exam_id=%s AND score IS NOT NULL GROUP BY bucket ORDER BY bucket",
        (exam_id,)
    )
    return {"success": True, "stats": stats, "distribution": distribution}


# ===== Content Review =====

@router.post("/content/generate")
async def generate_content(req: ContentGenerateRequest, user: CurrentUser = Depends(get_current_user)):
    """AI 生成课程讲义草稿"""
    require_teacher(user)
    from db import execute
    from llm_stream import call_llm_stream_messages
    # 获取课程信息用于 prompt 构造
    from db import query_one
    lesson = query_one("SELECT id, title, description FROM lessons WHERE id=%s", (req.lesson_id,))
    if not lesson:
        raise HTTPException(404, "课程不存在")
    system_prompt = f"你是课程内容生成助手。请为课程「{lesson['title']}」生成讲义草稿，包含章节大纲和知识点。输出JSON格式：{{\"sections\": [{{\"title\":\"...\", \"content\":\"...\"}}]}}"
    draft_json = await call_llm_stream_messages(
        model=req.model or "gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"课程描述：{lesson.get('description','无')}\n请生成讲义草稿。"}
        ],
        temperature=0.7
    )
    rid = execute(
        "INSERT INTO content_reviews (lesson_id, ai_draft_json) VALUES (%s, %s)",
        (req.lesson_id, draft_json)
    )
    return {"success": True, "id": rid}

@router.get("/content/reviews")
async def list_reviews(user: CurrentUser = Depends(get_current_user)):
    require_teacher(user)
    from db import query_all
    rows = query_all("SELECT * FROM content_reviews WHERE status='pending' ORDER BY created_at DESC")
    return {"success": True, "reviews": rows or []}

@router.post("/content/review/{rid}/approve")
async def approve_review(rid: int, user: CurrentUser = Depends(get_current_user)):
    require_teacher(user)
    from db import execute, query_one
    # 验证该 review 的课程归属当前教师
    cr = query_one(
        "SELECT cr.id FROM content_reviews cr JOIN lessons l ON cr.lesson_id=l.id WHERE cr.id=%s AND l.teacher_id=%s",
        (rid, user.uid)
    )
    if not cr:
        raise HTTPException(403, "无权审批此内容")
    execute("UPDATE content_reviews SET status='approved', reviewer_id=%s, reviewed_at=CURRENT_TIMESTAMP WHERE id=%s", (user.uid, rid))
    return {"success": True}

@router.post("/content/review/{rid}/reject")
async def reject_review(rid: int, user: CurrentUser = Depends(get_current_user)):
    require_teacher(user)
    from db import execute, query_one
    cr = query_one(
        "SELECT cr.id FROM content_reviews cr JOIN lessons l ON cr.lesson_id=l.id WHERE cr.id=%s AND l.teacher_id=%s",
        (rid, user.uid)
    )
    if not cr:
        raise HTTPException(403, "无权审批此内容")
    execute("UPDATE content_reviews SET status='rejected', reviewer_id=%s, reviewed_at=CURRENT_TIMESTAMP WHERE id=%s", (user.uid, rid))
    return {"success": True}
```

Note: The full `teacher.py` file (~25 endpoints) is scaffolded above with the key patterns. All endpoints follow the same `Depends(get_current_user)` + `require_teacher()` + db operation structure.

- [ ] **Step 2: Register teacher router in `main.py`**

```python
# ---- Teacher API (教师端) ----
from app.api.teacher import router as teacher_router
app.include_router(teacher_router, prefix="/api/teacher")
```

- [ ] **Step 3: Commit**

```bash
git add app/api/teacher.py main.py
git commit -m "feat(teacher): add /api/teacher/* endpoints — dashboard, classes, questions, exams, content review"
```

---

### Task 5.4: Backend — Datacenter API + DB Functions + Models

**Files:**
- Create: `app/api/datacenter.py`
- Create: `app/models/teacher.py`
- Modify: `db.py` (add teacher-side query functions)
- Modify: `main.py` (register datacenter router)

- [ ] **Step 1: Create `app/api/datacenter.py`**

```python
# -*- coding: utf-8 -*-
"""数据大屏 API — 多级聚合数据"""

from __future__ import annotations

import json
import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from app.middleware.auth import get_current_user, CurrentUser

logger = logging.getLogger("starlearn.api.datacenter")
router = APIRouter(tags=["datacenter"])


@router.get("/overview")
async def overview(level: str = "school", user: CurrentUser = Depends(get_current_user)):
    """总览统计 — level: school|department|class|student"""
    try:
        from db import query_one
        if level == "school":
            stats = query_one("""
                SELECT
                    (SELECT COUNT(*) FROM courses) as totalCourses,
                    (SELECT COUNT(*) FROM sp_user WHERE role='student') as totalStudents,
                    (SELECT COUNT(*) FROM sp_user) as totalUsers
            """)
        elif level == "student":
            stats = query_one("""
                SELECT COUNT(*) as totalCourses FROM courses WHERE student_id = %s
            """, (user.uid,))
        else:
            stats = {"totalCourses": 0, "totalStudents": 0, "totalUsers": 0}
        return {"success": True, "level": level, "stats": stats or {}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trends")
async def trends(days: int = 30, user: CurrentUser = Depends(get_current_user)):
    """学习投入趋势 — 返回每日学习时长数组"""
    try:
        from db import query_all
        rows = query_all(
            "SELECT snapshot_date as date, metrics_json FROM data_snapshots "
            "WHERE snapshot_type='daily' ORDER BY snapshot_date DESC LIMIT %s",
            (days,)
        )
        if rows:
            # Python-side JSON extraction — 避免 MySQL/SQLite JSON 函数名差异
            # MySQL: JSON_EXTRACT(col, '$.key')  SQLite: json_extract(col, '$.key')
            result = []
            for r in rows:
                try:
                    metrics = json.loads(r["metrics_json"]) if isinstance(r["metrics_json"], str) else (r["metrics_json"] or {})
                    result.append({"date": str(r["date"]), "hours": metrics.get("total_hours", 0)})
                except (json.JSONDecodeError, TypeError):
                    result.append({"date": str(r["date"]), "hours": 0})
            if result:
                return {"success": True, "trends": result}
    except Exception:
        pass  # 降级到占位数据
    data = [{"date": f"2026-06-{d+1:02d}", "hours": 0} for d in range(days)]
    return {"success": True, "trends": data, "_placeholder": True}


@router.get("/distribution")
async def distribution(dimension: str = "region", user: CurrentUser = Depends(get_current_user)):
    """分布数据"""
    return {"success": True, "dimension": dimension, "data": []}


@router.get("/radar")
async def radar(user: CurrentUser = Depends(get_current_user)):
    """能力维度雷达"""
    return {"success": True, "dimensions": [
        {"name": "编程", "score": 78},
        {"name": "理论", "score": 85},
        {"name": "实践", "score": 72},
        {"name": "数学", "score": 80},
        {"name": "综合", "score": 76},
    ]}


@router.get("/realtime")
async def realtime(token: str | None = None, request: Request = None):
    """实时学习动态 — SSE 流。
    EventSource 不支持自定义请求头，因此通过 query param 传递 token。"""
    # 优先从 query param 取 token（EventSource 兼容），其次从 Authorization header
    if not token and request:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if token:
        from app.utils.jwt import verify_token
        payload = verify_token(token)
        if not payload:
            raise HTTPException(status_code=401, detail="令牌无效")
    async def event_stream():
        import asyncio
        try:
            while True:
                yield f"data: {json.dumps({'type': 'heartbeat', 'time': 'now'})}\n\n"
                await asyncio.sleep(30)
        except asyncio.CancelledError:
            logger.info("Realtime SSE client disconnected")
        except Exception as e:
            logger.error(f"Realtime SSE error: {e}")

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

- [ ] **Step 2: Create `app/models/teacher.py`** (Pydantic models for teacher data)

```python
# -*- coding: utf-8 -*-
"""教师端数据模型"""

from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# These Pydantic models mirror the SQL tables for type-safe serialization.
# Usage: ClassInfo(**row_dict) — Pydantic handles validation + JSON serialization.

class ClassInfo(BaseModel):
    id: int
    name: str
    student_count: int = 0

class QuestionInfo(BaseModel):
    id: int
    type: str
    content: str
    difficulty: str = "medium"

class ExamInfo(BaseModel):
    id: int
    title: str
    class_ids: list[int] = []
    status: str = "draft"
    created_at: Optional[datetime] = None

class ContentReviewInfo(BaseModel):
    id: int
    lesson_id: int
    status: str = "pending"
    created_at: Optional[datetime] = None
```

- [ ] **Step 3: Add teacher-specific DB functions to `db.py`**

> **注意：** 通用 `query_one`/`query_all`/`execute` 已在 Task 5.0 定义，此处**不重复定义**。以下仅追加 teacher/datacenter 模块专用的业务函数。

In `db.py`, add after existing functions:

```python
# ===== Teacher & Datacenter helpers =====
# 注意：query_one/query_all/execute 已在 Task 5.0 定义，此处直接使用

def get_teacher_stats(teacher_id: int) -> dict:
    """获取教师仪表盘统计数据"""
    return {
        "totalStudents": len(query_all(
            "SELECT DISTINCT student_id FROM class_students WHERE class_id IN "
            "(SELECT id FROM classes WHERE teacher_id=?)", (teacher_id,)
        )),
        "totalClasses": len(query_all(
            "SELECT id FROM classes WHERE teacher_id=?", (teacher_id,)
        )),
        "totalQuestions": len(query_all(
            "SELECT id FROM questions WHERE teacher_id=?", (teacher_id,)
        )),
        "pendingReviews": len(query_all(
            "SELECT id FROM content_reviews WHERE status='pending'"
        )),
    }

def get_datacenter_overview() -> dict:
    """获取数据大屏概览数据（跨所有教师）"""
    return {
        "totalUsers": len(query_all("SELECT id FROM sp_user WHERE 1=1")),
        "totalCourses": len(query_all("SELECT id FROM courses WHERE 1=1")),
        "activeToday": 0,  # placeholder — 需接入实时会话统计
    }
```

- [ ] **Step 4: Register datacenter router in `main.py`**

```python
# ---- Datacenter API (数据大屏) ----
from app.api.datacenter import router as datacenter_router
app.include_router(datacenter_router, prefix="/api/datacenter")
```

- [ ] **Step 5: Commit**

```bash
git add app/api/datacenter.py app/models/teacher.py db.py main.py
git commit -m "feat(datacenter): add /api/datacenter/* endpoints + teacher DB helpers + models"
```

---

### Task 5.5: Frontend — Login Page + Auth Module

**Files:**
- Modify: `html/login.html`
- Create: `js/auth.js`
- Create: `js/http-intercept.js`
- Modify: `css/auth.css`

- [ ] **Step 1: Modify `html/login.html` (已有文件，替换为 知域 登录页)**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>登录 · 星识</title>
  <link rel="stylesheet" href="/css/tokens.css">
  <link rel="stylesheet" href="/css/auth.css">
</head>
<body class="auth-page">
  <div class="auth-container">
    <div class="auth-card">
      <div class="auth-header">
        <div class="auth-logo">⭐ 星识</div>
        <p class="auth-subtitle">智能学习平台</p>
      </div>

      <div class="auth-tabs">
        <button class="auth-tab active" data-tab="login">登录</button>
        <button class="auth-tab" data-tab="register">注册</button>
      </div>

      <!-- Login Form -->
      <form id="login-form" class="auth-form">
        <div class="auth-field">
          <label>用户名</label>
          <input type="text" id="login-username" placeholder="请输入用户名" autocomplete="username" />
        </div>
        <div class="auth-field">
          <label>密码</label>
          <input type="password" id="login-password" placeholder="请输入密码" autocomplete="current-password" />
        </div>
        <button type="submit" class="auth-submit">登 录</button>
        <div class="auth-quick-login">
          <span>快速登录：</span>
          <button type="button" class="auth-quick-btn" data-username="student" data-password="123456">学生</button>
          <button type="button" class="auth-quick-btn" data-username="teacher" data-password="123456">教师</button>
          <button type="button" class="auth-quick-btn" data-username="admin" data-password="123456">管理员</button>
        </div>
      </form>

      <!-- Register Form (hidden by default) -->
      <form id="register-form" class="auth-form" style="display:none">
        <div class="auth-field">
          <label>用户名</label>
          <input type="text" id="reg-username" placeholder="请输入用户名" />
        </div>
        <div class="auth-field">
          <label>显示名称</label>
          <input type="text" id="reg-displayname" placeholder="如何称呼你？" />
        </div>
        <div class="auth-field">
          <label>密码</label>
          <input type="password" id="reg-password" placeholder="请输入密码" />
        </div>
        <div class="auth-field">
          <label>确认密码</label>
          <input type="password" id="reg-password2" placeholder="再次输入密码" />
        </div>
        <div class="auth-field">
          <label>角色</label>
          <select id="reg-role">
            <option value="student">学生</option>
            <option value="teacher">教师</option>
          </select>
        </div>
        <button type="submit" class="auth-submit">注 册</button>
      </form>

      <div class="auth-error" id="auth-error"></div>
    </div>
  </div>

  <script src="/js/auth.js"></script>
</body>
</html>
```

- [ ] **Step 2: Create `js/auth.js`**

```javascript
/**
 * 认证模块 — JWT token 管理 (login/logout/fetchMe)
 * Token 存储在 localStorage key 'sp_token'（与知域一致）
 */
(function() {
  'use strict';

  const TOKEN_KEY = 'sp_token';

  // ===== State =====
  let currentUser = null;

  // ===== Public API =====
  window.Auth = {
    login, register, logout, fetchMe,
    getToken: () => localStorage.getItem(TOKEN_KEY),
    getUser: () => currentUser,
    isLoggedIn: () => !!(localStorage.getItem(TOKEN_KEY) && currentUser),
    getUserRole: () => currentUser?.role || null,
    isTeacher: () => currentUser?.role === 'teacher' || currentUser?.role === 'admin',
  };

  // ===== Init =====
  function init() {
    // Tab switching
    document.querySelectorAll('.auth-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        document.querySelectorAll('.auth-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        const isLogin = tab.dataset.tab === 'login';
        document.getElementById('login-form').style.display = isLogin ? '' : 'none';
        document.getElementById('register-form').style.display = isLogin ? 'none' : '';
        document.getElementById('auth-error').textContent = '';
      });
    });

    // Login form
    document.getElementById('login-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const username = document.getElementById('login-username').value.trim();
      const password = document.getElementById('login-password').value;
      if (!username || !password) {
        showError('请填写用户名和密码');
        return;
      }
      await login(username, password);
    });

    // Register form
    document.getElementById('register-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const username = document.getElementById('reg-username').value.trim();
      const displayName = document.getElementById('reg-displayname').value.trim();
      const password = document.getElementById('reg-password').value;
      const password2 = document.getElementById('reg-password2').value;
      const role = document.getElementById('reg-role').value;

      if (!username || !password) { showError('请填写用户名和密码'); return; }
      if (password !== password2) { showError('两次密码不一致'); return; }

      await register(username, password, role, displayName);
    });

    // Quick login buttons
    document.querySelectorAll('.auth-quick-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.getElementById('login-username').value = btn.dataset.username;
        document.getElementById('login-password').value = btn.dataset.password;
        login(btn.dataset.username, btn.dataset.password);
      });
    });

    // Check for pending redirect
    const pending = sessionStorage.getItem('starlearn_pending_redirect');
    if (pending) sessionStorage.removeItem('starlearn_pending_redirect');
  }

  // ===== Actions =====
  async function login(username, password) {
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || '登录失败');

      applyAuth(data);
      redirectAfterLogin(data);
    } catch (err) {
      showError(err.message);
    }
  }

  async function register(username, password, role, displayName) {
    try {
      const res = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password, role, display_name: displayName }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || '注册失败');

      applyAuth(data);
      redirectAfterLogin(data);
    } catch (err) {
      showError(err.message);
    }
  }

  function applyAuth(data) {
    localStorage.setItem(TOKEN_KEY, data.token);
    currentUser = {
      uid: data.userId,
      username: data.username,
      role: data.role,
      displayName: data.displayName,
    };
  }

  async function fetchMe() {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) return null;
    try {
      const res = await fetch('/api/auth/me', {
        headers: { 'Authorization': 'Bearer ' + token },
      });
      if (!res.ok) { logout(); return null; }
      const data = await res.json();
      currentUser = {
        uid: data.userId, username: data.username,
        role: data.role, displayName: data.displayName,
      };
      return currentUser;
    } catch {
      logout();
      return null;
    }
  }

  function logout() {
    localStorage.removeItem(TOKEN_KEY);
    currentUser = null;
    window.location.href = '/login.html';
  }

  function redirectAfterLogin(data) {
    const pending = sessionStorage.getItem('starlearn_pending_redirect');
    if (pending) {
      window.location.href = pending;
    } else if (data.role === 'teacher' || data.role === 'admin') {
      // ⚠️ Phase 5 守卫：teacher-dashboard.html 在 Task 5.6 创建。
      // Task 5.5 部署时此文件尚不存在——通过 localStorage flag 或降级到 hub.html。
      if (localStorage.getItem('sp_phase5_deployed') === '1') {
        window.location.href = '/teacher-dashboard.html';
      } else {
        console.warn('Phase 5 teacher pages not yet deployed, redirecting to hub');
        window.location.href = '/hub.html';
      }
    } else {
      window.location.href = '/hub.html';
    }
  }

  function showError(msg) {
    const el = document.getElementById('auth-error');
    if (el) { el.textContent = msg; el.style.display = msg ? '' : 'none'; }
  }

  // ===== Start =====
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else { init(); }

})();
```

- [ ] **Step 3: Create `js/http-intercept.js`**

```javascript
/**
 * HTTP 拦截器 — 自动附加 Bearer token，401 时重定向登录
 */
(function() {
  'use strict';

  const TOKEN_KEY = 'sp_token';
  const PUBLIC_PATHS = ['/api/auth/login', '/api/auth/register'];

  // ===== Wrap fetch =====
  const _fetch = window.fetch;
  window.fetch = function(url, options = {}) {
    const path = typeof url === 'string' ? new URL(url, window.location.origin).pathname : url;

    // Skip token for public endpoints
    if (!PUBLIC_PATHS.some(p => path.startsWith(p))) {
      const token = localStorage.getItem(TOKEN_KEY);
      if (token) {
        options.headers = options.headers || {};
        if (!options.headers['Authorization']) {
          options.headers['Authorization'] = 'Bearer ' + token;
        }
      }
    }

    return _fetch(url, options).then(async (response) => {
      if (response.status === 401) {
        localStorage.removeItem(TOKEN_KEY);
        // Save current path for redirect after login
        sessionStorage.setItem('starlearn_pending_redirect', window.location.href);
        window.location.href = '/login.html';
      }
      return response;
    });
  };

  // ===== Auto-check: redirect to login if accessing teacher pages without token =====
  function checkAccess() {
    const path = window.location.pathname;
    const isTeacherPage = path.includes('teacher-') || path.includes('data-dashboard');
    if (!isTeacherPage) return;

    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) {
      sessionStorage.setItem('starlearn_pending_redirect', window.location.href);
      window.location.href = '/login.html';
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', checkAccess);
  } else { checkAccess(); }

})();
```

- [ ] **Step 4: Modify `css/auth.css`（已有文件，追加登录页样式）**

```css
/* ---- Auth Page ---- */
.auth-page {
  margin: 0; padding: 0;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-primary, #0f0f19);
  font-family: var(--font-sans, system-ui, -apple-system, sans-serif);
}

.auth-container { width: 400px; max-width: calc(100vw - 32px); }

.auth-card {
  background: var(--surface-glass, rgba(255,255,255,0.04));
  backdrop-filter: blur(24px);
  border: 1px solid var(--border-glass, rgba(255,255,255,0.1));
  border-radius: 20px;
  padding: 36px 32px;
  box-shadow: 0 8px 40px rgba(0,0,0,0.3);
}

.auth-header { text-align: center; margin-bottom: 28px; }
.auth-logo { font-size: 28px; font-weight: 700; color: var(--text-primary, #e2e8f0); }
.auth-subtitle { font-size: 14px; color: var(--text-tertiary, #64748b); margin-top: 4px; }

.auth-tabs { display: flex; gap: 4px; margin-bottom: 24px; background: rgba(255,255,255,0.04); border-radius: 10px; padding: 4px; }
.auth-tab { flex: 1; padding: 10px; border: none; background: none; color: var(--text-tertiary, #64748b); font-size: 14px; font-weight: 500; cursor: pointer; border-radius: 8px; transition: all 0.15s; }
.auth-tab.active { background: var(--brand, #6366f1); color: #fff; }

.auth-form { display: flex; flex-direction: column; gap: 16px; }
.auth-field { display: flex; flex-direction: column; gap: 6px; }
.auth-field label { font-size: 13px; font-weight: 500; color: var(--text-secondary, #94a3b8); }
.auth-field input, .auth-field select {
  padding: 10px 14px;
  border-radius: 10px;
  border: 1px solid var(--border-glass, rgba(255,255,255,0.1));
  background: var(--surface-elevated, rgba(255,255,255,0.04));
  color: var(--text-primary, #e2e8f0);
  font-size: 14px;
  outline: none;
  transition: border-color 0.15s;
}
.auth-field input:focus, .auth-field select:focus { border-color: var(--brand, #6366f1); }
.auth-field select option { background: #1a1a2e; color: #e2e8f0; }

.auth-submit {
  margin-top: 8px;
  padding: 12px;
  border: none;
  border-radius: 10px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s;
}
.auth-submit:hover { opacity: 0.9; }

.auth-quick-login { display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--text-tertiary, #64748b); justify-content: center; }
.auth-quick-btn { padding: 4px 12px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.1); background: rgba(255,255,255,0.04); color: var(--text-secondary, #94a3b8); cursor: pointer; font-size: 12px; transition: all 0.15s; }
.auth-quick-btn:hover { border-color: var(--brand, #6366f1); color: var(--brand, #6366f1); }

.auth-error { margin-top: 16px; padding: 10px 14px; border-radius: 8px; background: rgba(239,68,68,0.1); color: #ef4444; font-size: 13px; display: none; }
```

- [ ] **Step 5: Commit**

```bash
git add html/login.html js/auth.js js/http-intercept.js css/auth.css
git commit -m "feat(auth): add login page + auth.js + HTTP interceptor (ported from 知域)"
```

---

### Task 5.6: Frontend — Teacher Dashboard Page

**Files:**
- Create: `html/teacher-dashboard.html`
- Create: `js/teacher-dashboard.js`
- Create: `css/teacher.css`

- [ ] **Step 1: Create `html/teacher-dashboard.html`**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>教师工作台 · 星识</title>
  <link rel="stylesheet" href="/css/tokens.css">
  <link rel="stylesheet" href="/css/teacher.css">
  <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
</head>
<body class="teacher-page">
  <div class="teacher-layout">
    <!-- Sidebar -->
    <aside class="teacher-sidebar">
      <div class="teacher-brand">⭐ 星识教师端</div>
      <nav class="teacher-nav">
        <a class="teacher-nav-item active" href="/teacher-dashboard.html">
工作台</a>
        <a class="teacher-nav-item" href="/teacher-class.html">
班级管理</a>
        <a class="teacher-nav-item" href="/teacher-manage.html">
题库管理</a>
        <a class="teacher-nav-item" href="/teacher-exam.html">
考试管理</a>
        <a class="teacher-nav-item" href="/teacher-content.html">
内容管理</a>
        <a class="teacher-nav-item" href="/data-dashboard.html">
数据大屏</a>
      </nav>
      <div class="teacher-sidebar-footer">
        <button class="teacher-logout-btn" id="teacher-logout-btn">退出登录</button>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="teacher-main">
      <h1 class="teacher-page-title">
教师工作台</h1>

      <!-- Stats Cards -->
      <div class="teacher-stats" id="stats-row">
        <div class="stat-card"><div class="stat-value">--</div><div class="stat-label">授课班级</div></div>
        <div class="stat-card"><div class="stat-value">--</div><div class="stat-label">在授课程</div></div>
        <div class="stat-card"><div class="stat-value">--</div><div class="stat-label">待批改</div></div>
        <div class="stat-card"><div class="stat-value">--</div><div class="stat-label">平均成绩</div></div>
      </div>

      <!-- Charts Row -->
      <div class="teacher-charts">
        <div class="chart-card">
          <h3>班级学习概览</h3>
          <div class="chart-container" id="chart-class-progress" style="height:300px"></div>
        </div>
        <div class="chart-card">
          <h3>学生能力雷达</h3>
          <div class="chart-container" id="chart-radar" style="height:300px"></div>
        </div>
      </div>
    </main>
  </div>

  <script src="/js/http-intercept.js"></script>
  <script src="/js/auth.js"></script>
  <script src="/js/teacher-dashboard.js"></script>
</body>
</html>
```

- [ ] **Step 2: Create `js/teacher-dashboard.js`**

```javascript
/**
 * 教师仪表盘 — 统计数据 + ECharts 图表
 */
(function() {
  'use strict';

  let classChart = null;
  let radarChart = null;

  async function init() {
    // Ensure authenticated
    if (!Auth.isTeacher()) {
      await Auth.fetchMe();
      if (!Auth.isTeacher()) return;  // redirect handled by interceptor
    }

    // Bind logout button
    const logoutBtn = document.getElementById('teacher-logout-btn');
    if (logoutBtn) logoutBtn.addEventListener('click', () => Auth.logout());

    await loadStats();
    renderCharts();
  }

  async function loadStats() {
    try {
      const res = await fetch('/api/teacher/dashboard');
      const data = await res.json();
      if (data.success) {
        const cards = document.querySelectorAll('#stats-row .stat-value');
        cards[0].textContent = data.stats.classCount + '个';
        cards[1].textContent = data.stats.courseCount + '门';
        cards[2].textContent = data.stats.pendingGrading + '份';
        cards[3].textContent = data.stats.avgScore + '分';
      }
    } catch (err) {
      console.error('Failed to load dashboard stats:', err);
    }
  }

  async function renderCharts() {
    // 从 API 加载数据
    let classData = [];
    let radarData = [];
    try {
      const [classRes, radarRes] = await Promise.all([
        fetch('/api/teacher/classes').then(r => r.json()),
        fetch('/api/datacenter/radar').then(r => r.json())
      ]);
      if (classRes.success) {
        classData = (classRes.classes || []).map(c => ({ name: c.name, value: c.student_count || 0 }));
      }
      if (radarRes.success) {
        radarData = (radarRes.dimensions || []).map(d => d.score);
      }
    } catch (e) {
      console.warn('Failed to load chart data, using defaults');
    }

    // Fallback: 使用默认数据
    if (classData.length === 0) classData = [{ name: '1班', value: 78 }, { name: '2班', value: 85 }, { name: '3班', value: 62 }];
    if (radarData.length === 0) radarData = [78, 85, 72, 80, 76];

    // Class progress bar chart
    const classEl = document.getElementById('chart-class-progress');
    if (classEl) {
      classChart = echarts.init(classEl);
      classChart.setOption({
        tooltip: { trigger: 'axis' },
        xAxis: { type: 'category', data: classData.map(d => d.name) },
        yAxis: { type: 'value', max: 100 },
        series: [{
          type: 'bar', data: classData.map(d => d.value),
          itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#6366f1' }, { offset: 1, color: '#8b5cf6' }
          ])}
        }]
      });
    }

    // Radar chart
    const radarEl = document.getElementById('chart-radar');
    if (radarEl) {
      radarChart = echarts.init(radarEl);
      radarChart.setOption({
        radar: {
          indicator: [
            { name: '编程', max: 100 }, { name: '理论', max: 100 },
            { name: '实践', max: 100 }, { name: '数学', max: 100 }, { name: '综合', max: 100 }
          ]
        },
        series: [{
          type: 'radar',
          data: [{ value: radarData, name: '班级平均' }],
          areaStyle: { color: 'rgba(99,102,241,0.15)' },
          lineStyle: { color: '#6366f1' },
          itemStyle: { color: '#6366f1' }
        }]
      });
    }
  }

  // Handle resize
  window.addEventListener('resize', () => {
    classChart?.resize();
    radarChart?.resize();
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else { init(); }

})();
```

- [ ] **Step 3: Create `css/teacher.css`** (shared teacher styles)

```css
/* ---- Teacher Layout ---- */
.teacher-page { margin: 0; padding: 0; min-height: 100vh; background: var(--bg-primary, #0f0f19); color: var(--text-primary, #e2e8f0); font-family: var(--font-sans, system-ui, sans-serif); }
.teacher-layout { display: flex; min-height: 100vh; }

/* Sidebar */
.teacher-sidebar {
  width: 220px; flex-shrink: 0;
  background: var(--surface-glass, rgba(255,255,255,0.03));
  border-right: 1px solid var(--border-glass, rgba(255,255,255,0.08));
  display: flex; flex-direction: column; padding: 20px 0;
}
.teacher-brand { padding: 0 20px 20px; font-size: 18px; font-weight: 700; border-bottom: 1px solid var(--border-glass, rgba(255,255,255,0.08)); margin-bottom: 12px; }
.teacher-nav { flex: 1; display: flex; flex-direction: column; gap: 2px; padding: 0 12px; }
.teacher-nav-item {
  padding: 10px 12px; border-radius: 8px; font-size: 14px; color: var(--text-secondary, #94a3b8);
  text-decoration: none; transition: all 0.15s;
}
.teacher-nav-item:hover { background: rgba(255,255,255,0.05); color: var(--text-primary, #e2e8f0); }
.teacher-nav-item.active { background: rgba(99,102,241,0.15); color: var(--brand, #6366f1); font-weight: 600; }
.teacher-sidebar-footer { padding: 12px; }
.teacher-logout-btn { width: 100%; padding: 10px; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; background: transparent; color: var(--text-tertiary, #64748b); cursor: pointer; font-size: 13px; }
.teacher-logout-btn:hover { color: #ef4444; border-color: rgba(239,68,68,0.3); }

/* Main */
.teacher-main { flex: 1; padding: 32px; overflow-y: auto; }
.teacher-page-title { font-size: 24px; font-weight: 700; margin-bottom: 28px; }

/* Stats */
.teacher-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 28px; }
.stat-card { background: var(--surface-glass, rgba(255,255,255,0.04)); border: 1px solid var(--border-glass, rgba(255,255,255,0.08)); border-radius: 14px; padding: 20px; }
.stat-value { font-size: 28px; font-weight: 700; color: var(--brand, #6366f1); }
.stat-label { font-size: 13px; color: var(--text-tertiary, #64748b); margin-top: 4px; }

/* Charts */
.teacher-charts { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.chart-card { background: var(--surface-glass, rgba(255,255,255,0.04)); border: 1px solid var(--border-glass, rgba(255,255,255,0.08)); border-radius: 14px; padding: 20px; }
.chart-card h3 { font-size: 15px; font-weight: 600; margin-bottom: 16px; }

@media (max-width: 768px) {
  .teacher-sidebar { display: none; }
  .teacher-stats { grid-template-columns: repeat(2, 1fr); }
  .teacher-charts { grid-template-columns: 1fr; }
}
```

- [ ] **Step 4: Commit**

```bash
git add html/teacher-dashboard.html js/teacher-dashboard.js css/teacher.css
git commit -m "feat(teacher): add teacher dashboard page with ECharts stats + radar"
```

---

### Task 5.7: Frontend — Remaining Teacher Pages + Data Dashboard (Scaffolding)

**Files:**
- Create: `html/teacher-class.html`, `js/teacher-class.js`
- Create: `html/teacher-manage.html`, `js/teacher-manage.js`
- Create: `html/teacher-exam.html`, `js/teacher-exam.js`
- Create: `html/teacher-content.html`, `js/teacher-content.js`
- Create: `html/data-dashboard.html`, `js/data-dashboard.js`, `css/data-dashboard.css`

**Note:** These 5 pages follow the same architecture as `teacher-dashboard.html`:
- Same sidebar layout (imported from `teacher.css`)
- Same auth guard pattern (`js/http-intercept.js` + `js/auth.js`)
- API calls to the teacher/datacenter endpoints

---

- [ ] **Step 1a: Create `html/teacher-class.html` + `js/teacher-class.js`**

**html/teacher-class.html:**
```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>班级管理 · 星识</title>
  <link rel="stylesheet" href="/css/tokens.css"><link rel="stylesheet" href="/css/teacher.css">
  <style>
    .class-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
    .class-card { background: var(--surface-glass); border: 1px solid var(--border-glass); border-radius: 12px; padding: 20px; cursor: pointer; transition: border-color 0.15s; }
    .class-card:hover { border-color: var(--brand); }
    .class-card-name { font-size: 16px; font-weight: 600; }
    .class-card-count { font-size: 13px; color: var(--text-tertiary); margin-top: 4px; }
    .class-card-actions { display: flex; gap: 8px; margin-top: 12px; }
    .roster-table { width: 100%; border-collapse: collapse; margin-top: 16px; }
    .roster-table th, .roster-table td { text-align: left; padding: 10px 12px; border-bottom: 1px solid var(--border-glass); font-size: 13px; }
    .roster-table th { color: var(--text-tertiary); font-weight: 500; }
    .modal-overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.6); z-index: 500; align-items: center; justify-content: center; }
    .modal-overlay.visible { display: flex; }
    .modal-box { background: var(--surface-glass); border: 1px solid var(--border-glass); border-radius: 14px; padding: 24px; width: 400px; max-width: 90vw; }
    @media (max-width: 768px) { .class-grid { grid-template-columns: 1fr; } }
  </style>
</head>
<body class="teacher-page">
  <div class="teacher-layout">
    <aside class="teacher-sidebar">
      <div class="teacher-brand">⭐ 星识教师端</div>
      <nav class="teacher-nav">
        <a class="teacher-nav-item" href="/teacher-dashboard.html">
工作台</a>
        <a class="teacher-nav-item active" href="/teacher-class.html">
班级管理</a>
        <a class="teacher-nav-item" href="/teacher-manage.html">
题库管理</a>
        <a class="teacher-nav-item" href="/teacher-exam.html">
考试管理</a>
        <a class="teacher-nav-item" href="/teacher-content.html">
内容管理</a>
        <a class="teacher-nav-item" href="/data-dashboard.html">
数据大屏</a>
      </nav>
      <div class="teacher-sidebar-footer"><button class="teacher-logout-btn" id="teacher-logout-btn">退出登录</button></div>
    </aside>
    <main class="teacher-main">
      <h1 class="teacher-page-title">
班级管理</h1>
      <div style="margin-bottom:16px">
        <button class="auth-submit" id="btn-create-class" style="width:auto;display:inline-block;padding:10px 24px">+ 新建班级</button>
        <input type="file" id="file-import-csv" accept=".csv" style="display:none">
        <button class="auth-submit" id="btn-import-csv" style="width:auto;display:inline-block;padding:10px 24px;background:rgba(255,255,255,0.06);margin-left:8px">📥 导入 CSV</button>
      </div>
      <div class="class-grid" id="class-grid"></div>
      <!-- Roster Modal -->
      <div class="modal-overlay" id="roster-modal">
        <div class="modal-box">
          <h3 id="roster-title">班级花名册</h3>
          <table class="roster-table"><thead><tr><th>用户名</th><th>显示名</th><th>加入时间</th></tr></thead><tbody id="roster-tbody"></tbody></table>
          <button class="auth-submit" id="btn-close-roster" style="margin-top:16px;width:100%">关闭</button>
        </div>
      </div>
      <!-- Create Class Modal -->
      <div class="modal-overlay" id="create-modal">
        <div class="modal-box">
          <h3>新建班级</h3>
          <div class="auth-field" style="margin-top:12px"><label>班级名称</label><input type="text" id="new-class-name" placeholder="例如：三年二班"></div>
          <div class="auth-field"><label>描述</label><input type="text" id="new-class-desc" placeholder="选填"></div>
          <button class="auth-submit" id="btn-submit-create" style="margin-top:12px;width:100%">创建</button>
        </div>
      </div>
    </main>
  </div>
  <script src="/js/http-intercept.js"></script>
  <script src="/js/auth.js"></script>
  <script src="/js/teacher-class.js"></script>
</body></html>
```

**js/teacher-class.js:**
```javascript
(function() {
  'use strict';
  async function init() {
    if (!Auth.isTeacher()) { await Auth.fetchMe(); if (!Auth.isTeacher()) return; }
    document.getElementById('teacher-logout-btn')?.addEventListener('click', () => Auth.logout());
    await loadClasses();
    document.getElementById('btn-create-class').addEventListener('click', () => document.getElementById('create-modal').classList.add('visible'));
    document.getElementById('btn-submit-create').addEventListener('click', createClass);
    document.getElementById('btn-close-roster').addEventListener('click', () => document.getElementById('roster-modal').classList.remove('visible'));
    document.getElementById('btn-import-csv').addEventListener('click', () => document.getElementById('file-import-csv').click());
    document.getElementById('file-import-csv').addEventListener('change', importCSV);
  }
  async function loadClasses() {
    const res = await fetch('/api/teacher/classes'); const data = await res.json();
    const grid = document.getElementById('class-grid');
    grid.innerHTML = (data.classes||[]).map(c => `
      <div class="class-card">
        <div class="class-card-name">${c.name}</div>
        <div class="class-card-count">${c.student_count||0} 名学生</div>
        <div class="class-card-actions">
          <button class="auth-quick-btn" onclick="window._viewRoster(${c.id},'${c.name}')">查看花名册</button>
          <button class="auth-quick-btn" onclick="window._deleteClass(${c.id})" style="color:#ef4444">删除</button>
        </div>
      </div>`).join('') || '<p style="color:var(--text-tertiary)">暂无班级，点击上方按钮创建</p>';
  }
  async function createClass() {
    const name = document.getElementById('new-class-name').value.trim(); if (!name) return;
    const description = document.getElementById('new-class-desc').value.trim();
    await fetch('/api/teacher/class', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,description})});
    document.getElementById('create-modal').classList.remove('visible'); loadClasses();
  }
  window._viewRoster = async (classId, name) => {
    document.getElementById('roster-title').textContent = name + ' · 花名册';
    const res = await fetch('/api/teacher/students/'+classId); const data = await res.json();
    document.getElementById('roster-tbody').innerHTML = (data.students||[]).map(s => `<tr><td>${s.username}</td><td>${s.display_name||'-'}</td><td>${(s.joined_at||'').slice(0,10)}</td></tr>`).join('');
    document.getElementById('roster-modal').classList.add('visible');
  };
  window._deleteClass = async (id) => { if(confirm('确认删除此班级？')) { await fetch('/api/teacher/class/'+id,{method:'DELETE'}); loadClasses(); } };
  async function importCSV(e) {
    const file = e.target.files[0]; if (!file) return;
    const text = await file.text(); const lines = text.split('\n').filter(l=>l.trim());
    const students = lines.slice(1).map(l=>{const parts=l.split(',');return{username:parts[0]?.trim(),display_name:parts[1]?.trim()||parts[0]?.trim()};});
    const classId = prompt('请输入目标班级 ID:'); if (!classId) return;
    const res = await fetch('/api/teacher/students/import',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({class_id:parseInt(classId),students})});
    const data = await res.json(); alert('导入完成: '+data.imported+' 名学生'); loadClasses();
  }
  if (document.readyState==='loading') document.addEventListener('DOMContentLoaded',init); else init();
})();
```

- [ ] **Step 1b: Create `html/teacher-manage.html` + `js/teacher-manage.js`**

**html/teacher-manage.html:**
```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>题库管理 · 星识</title>
  <link rel="stylesheet" href="/css/tokens.css"><link rel="stylesheet" href="/css/teacher.css">
  <style>
    .filter-bar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
    .filter-bar select, .filter-bar input { padding: 8px 12px; border-radius: 8px; border: 1px solid var(--border-glass); background: var(--surface-elevated); color: var(--text-primary); font-size: 13px; }
    .q-table { width: 100%; border-collapse: collapse; }
    .q-table th, .q-table td { text-align: left; padding: 10px 12px; border-bottom: 1px solid var(--border-glass); font-size: 13px; }
    .q-table th { color: var(--text-tertiary); font-weight: 500; position: sticky; top: 0; background: var(--bg-primary); }
    .q-diff-easy { color: #22c55e; } .q-diff-medium { color: #f59e0b; } .q-diff-hard { color: #ef4444; }
  </style>
</head>
<body class="teacher-page">
  <div class="teacher-layout">
    <aside class="teacher-sidebar">
      <div class="teacher-brand">⭐ 星识教师端</div>
      <nav class="teacher-nav">
        <a class="teacher-nav-item" href="/teacher-dashboard.html">
工作台</a>
        <a class="teacher-nav-item" href="/teacher-class.html">
班级管理</a>
        <a class="teacher-nav-item active" href="/teacher-manage.html">
题库管理</a>
        <a class="teacher-nav-item" href="/teacher-exam.html">
考试管理</a>
        <a class="teacher-nav-item" href="/teacher-content.html">
内容管理</a>
        <a class="teacher-nav-item" href="/data-dashboard.html">
数据大屏</a>
      </nav>
      <div class="teacher-sidebar-footer"><button class="teacher-logout-btn" id="teacher-logout-btn">退出登录</button></div>
    </aside>
    <main class="teacher-main">
      <h1 class="teacher-page-title">
题库管理</h1>
      <div class="filter-bar">
        <select id="filter-type"><option value="">全部题型</option><option value="choice">选择题</option><option value="blank">填空题</option><option value="code">编程题</option><option value="essay">问答题</option></select>
        <select id="filter-diff"><option value="">全部难度</option><option value="easy">简单</option><option value="medium">中等</option><option value="hard">困难</option></select>
        <input type="text" id="filter-search" placeholder="搜索题目内容...">
        <button class="auth-submit" id="btn-add-q" style="width:auto;padding:8px 20px;margin-left:auto">+ 添加题目</button>
      </div>
      <div style="overflow-x:auto"><table class="q-table"><thead><tr><th>ID</th><th>题型</th><th>内容</th><th>难度</th><th>操作</th></tr></thead><tbody id="q-tbody"></tbody></table></div>
    </main>
    <!-- 添加题目弹窗 -->
    <div class="modal-overlay" id="add-q-modal" style="display:none">
      <div class="modal-box"><h2>添加题目</h2>
        <select id="new-q-type"><option value="choice">选择题</option><option value="blank">填空题</option><option value="code">编程题</option><option value="essay">问答题</option></select>
        <textarea id="new-q-content" placeholder="题目内容" rows="4"></textarea>
        <input type="text" id="new-q-options" placeholder="选项(JSON数组，非选择题可留空)"><input type="text" id="new-q-answer" placeholder="正确答案">
        <select id="new-q-diff"><option value="easy">简单</option><option value="medium" selected>中等</option><option value="hard">困难</option></select>
        <div class="modal-actions"><button class="auth-submit" id="btn-save-q">保存</button><button class="auth-quick-btn" onclick="document.getElementById('add-q-modal').style.display='none'">取消</button></div>
      </div>
    </div>
  </div>
  <script src="/js/http-intercept.js"></script><script src="/js/auth.js"></script><script src="/js/teacher-manage.js"></script>
</body></html>
```

**js/teacher-manage.js:**
```javascript
(function() {
  'use strict';
  let questions = [];
  async function init() {
    if (!Auth.isTeacher()) { await Auth.fetchMe(); if (!Auth.isTeacher()) return; }
    document.getElementById('teacher-logout-btn')?.addEventListener('click', () => Auth.logout());
    document.getElementById('filter-type').addEventListener('change', applyFilter);
    document.getElementById('filter-diff').addEventListener('change', applyFilter);
    document.getElementById('filter-search').addEventListener('input', applyFilter);
    document.getElementById('btn-add-q').addEventListener('click', showAddQuestionModal);
    await loadQuestions();
  }
  async function loadQuestions() {
    const res = await fetch('/api/teacher/questions'); const data = await res.json();
    questions = data.questions || []; applyFilter();
  }
  function applyFilter() {
    const type = document.getElementById('filter-type').value;
    const diff = document.getElementById('filter-diff').value;
    const search = document.getElementById('filter-search').value.toLowerCase();
    let filtered = questions;
    if (type) filtered = filtered.filter(q => q.type === type);
    if (diff) filtered = filtered.filter(q => q.difficulty === diff);
    if (search) filtered = filtered.filter(q => (q.content||'').toLowerCase().includes(search));
    document.getElementById('q-tbody').innerHTML = filtered.map(q => `
      <tr><td>${q.id}</td><td>${q.type}</td><td style="max-width:400px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${q.content||''}</td>
      <td><span class="q-diff-${q.difficulty}">${q.difficulty||'medium'}</span></td>
      <td><button class="auth-quick-btn" onclick="if(confirm('删除?'))fetch('/api/teacher/question/${q.id}',{method:'DELETE'}).then(()=>loadQuestions())" style="color:#ef4444">删除</button></td></tr>`).join('') || '<tr><td colspan="5" style="color:var(--text-tertiary);text-align:center;padding:40px">暂无题目</td></tr>';
  }
  function showAddQuestionModal() { document.getElementById('add-q-modal').style.display = 'flex'; }
  document.getElementById('btn-save-q').addEventListener('click', async () => {
    const payload = { type: document.getElementById('new-q-type').value, content: document.getElementById('new-q-content').value, options: document.getElementById('new-q-options').value, answer: document.getElementById('new-q-answer').value, difficulty: document.getElementById('new-q-diff').value };
    const res = await fetch('/api/teacher/question', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload) });
    const data = await res.json();
    if (data.success) { document.getElementById('add-q-modal').style.display = 'none'; await loadQuestions(); }
  });
  if (document.readyState==='loading') document.addEventListener('DOMContentLoaded',init); else init();
})();
```

- [ ] **Step 1c: Create `html/teacher-exam.html` + `js/teacher-exam.js`**

**html/teacher-exam.html:**
```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>考试管理 · 星识</title>
  <link rel="stylesheet" href="/css/tokens.css"><link rel="stylesheet" href="/css/teacher.css">
  <style>
    .exam-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }
    .exam-card { background: var(--surface-glass); border: 1px solid var(--border-glass); border-radius: 12px; padding: 20px; }
    .exam-card h3 { font-size: 16px; margin-bottom: 8px; }
    .exam-meta { font-size: 12px; color: var(--text-tertiary); display: flex; gap: 16px; }
    .exam-status { display: inline-block; padding: 2px 10px; border-radius: 10px; font-size: 12px; }
    .exam-status-draft { background: rgba(148,163,184,0.15); color: #94a3b8; }
    .exam-status-published { background: rgba(34,197,94,0.15); color: #22c55e; }
    .exam-status-ended { background: rgba(239,68,68,0.15); color: #ef4444; }
    @media (max-width: 768px) { .exam-grid { grid-template-columns: 1fr; } }
  </style>
</head>
<body class="teacher-page">
  <div class="teacher-layout">
    <aside class="teacher-sidebar">
      <div class="teacher-brand">⭐ 星识教师端</div>
      <nav class="teacher-nav">
        <a class="teacher-nav-item" href="/teacher-dashboard.html">
工作台</a>
        <a class="teacher-nav-item" href="/teacher-class.html">
班级管理</a>
        <a class="teacher-nav-item" href="/teacher-manage.html">
题库管理</a>
        <a class="teacher-nav-item active" href="/teacher-exam.html">
考试管理</a>
        <a class="teacher-nav-item" href="/teacher-content.html">
内容管理</a>
        <a class="teacher-nav-item" href="/data-dashboard.html">
数据大屏</a>
      </nav>
      <div class="teacher-sidebar-footer"><button class="teacher-logout-btn" id="teacher-logout-btn">退出登录</button></div>
    </aside>
    <main class="teacher-main">
      <h1 class="teacher-page-title">
考试管理</h1>
      <button class="auth-submit" id="btn-create-exam" style="width:auto;padding:10px 24px;margin-bottom:16px">+ 创建考试</button>
      <div class="exam-grid" id="exam-grid"></div>
    </main>
  </div>
  <!-- 创建考试弹窗 -->
  <div class="modal-overlay" id="create-exam-modal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:1000;align-items:center;justify-content:center">
    <div class="modal-content" style="background:var(--bg-card,#fff);border-radius:12px;padding:24px;max-width:520px;width:90%;max-height:80vh;overflow-y:auto;box-shadow:0 20px 60px rgba(0,0,0,0.3)">
      <h2 style="margin:0 0 16px 0;font-size:18px">创建考试</h2>
      <label style="font-size:13px;color:var(--text-secondary)">考试标题</label>
      <input id="exam-title-input" style="width:100%;padding:8px 12px;margin:6px 0 12px;border-radius:8px;border:1px solid var(--border-color,#e2e8f0);background:var(--bg,#f8fafc);color:var(--text-primary);box-sizing:border-box" placeholder="输入考试标题">
      <label style="font-size:13px;color:var(--text-secondary)">时长（分钟）</label>
      <input id="exam-duration-input" type="number" value="120" min="1" style="width:100%;padding:8px 12px;margin:6px 0 12px;border-radius:8px;border:1px solid var(--border-color,#e2e8f0);background:var(--bg,#f8fafc);color:var(--text-primary);box-sizing:border-box">
      <label style="font-size:13px;color:var(--text-secondary)">指定班级</label>
      <div id="exam-class-checkboxes" style="max-height:120px;overflow-y:auto;margin:6px 0 12px;font-size:13px"></div>
      <label style="font-size:13px;color:var(--text-secondary)">添加试题</label>
      <div id="exam-question-checkboxes" style="max-height:200px;overflow-y:auto;margin:6px 0 12px;font-size:13px"></div>
      <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:16px">
        <button id="btn-cancel-exam" style="padding:8px 20px;border-radius:8px;border:1px solid var(--border-color);background:transparent;color:var(--text-secondary);cursor:pointer">取消</button>
        <button id="btn-save-exam" style="padding:8px 20px;border-radius:8px;border:none;background:var(--accent,#6366f1);color:#fff;font-weight:600;cursor:pointer">创建考试</button>
      </div>
    </div>
  </div>
  <script src="/js/http-intercept.js"></script><script src="/js/auth.js"></script><script src="/js/teacher-exam.js"></script>
</body></html>
```

**js/teacher-exam.js:**
```javascript
(function() {
  'use strict';
  async function init() {
    if (!Auth.isTeacher()) { await Auth.fetchMe(); if (!Auth.isTeacher()) return; }
    document.getElementById('teacher-logout-btn')?.addEventListener('click', () => Auth.logout());
    document.getElementById('btn-create-exam').addEventListener('click', showCreateModal);
    document.getElementById('btn-cancel-exam')?.addEventListener('click', hideCreateModal);
    document.getElementById('btn-save-exam')?.addEventListener('click', onCreateExam);
    await loadExams();
  }
  // ---------- 创建弹窗 ----------
  async function showCreateModal() {
    const modal = document.getElementById('create-exam-modal');
    modal.style.display = 'flex';
    document.getElementById('exam-title-input').value = '';
    document.getElementById('exam-duration-input').value = '120';
    // 加载班级
    const clsRes = await fetch('/api/teacher/classes'); const clsData = await clsRes.json();
    document.getElementById('exam-class-checkboxes').innerHTML = (clsData.classes||[]).map(c =>
      `<label style="display:inline-block;margin-right:12px;cursor:pointer"><input type="checkbox" value="${c.id}"> ${c.name}</label>`
    ).join('') || '<span style="color:var(--text-tertiary)">暂无班级</span>';
    // 加载试题
    const qRes = await fetch('/api/teacher/questions'); const qData = await qRes.json();
    document.getElementById('exam-question-checkboxes').innerHTML = (qData.questions||[]).map(q =>
      `<label style="display:block;margin:4px 0;cursor:pointer;font-size:13px"><input type="checkbox" value="${q.id}"> [${q.type||'?'}] ${q.title||'无题面'}</label>`
    ).join('') || '<span style="color:var(--text-tertiary)">暂无试题，请先在题库中添加</span>';
  }
  function hideCreateModal() {
    document.getElementById('create-exam-modal').style.display = 'none';
  }
  async function onCreateExam() {
    const title = document.getElementById('exam-title-input').value.trim();
    if (!title) { alert('请输入考试标题'); return; }
    const duration = parseInt(document.getElementById('exam-duration-input').value) || 120;
    const classIds = [...document.querySelectorAll('#exam-class-checkboxes input:checked')].map(cb=>parseInt(cb.value));
    const questionIds = [...document.querySelectorAll('#exam-question-checkboxes input:checked')].map(cb=>parseInt(cb.value));
    const res = await fetch('/api/teacher/exam', {method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({title, question_ids:questionIds, class_ids:classIds, duration})});
    const data = await res.json();
    if (data.success) { hideCreateModal(); await loadExams(); }
    else { alert('创建失败: '+(data.detail||'未知错误')); }
  }
  // ---------- 列表 ----------
  async function loadExams() {
    const res = await fetch('/api/teacher/exams'); const data = await res.json();
    document.getElementById('exam-grid').innerHTML = (data.exams||[]).map(e => `
      <div class="exam-card">
        <h3>${e.title}</h3><div class="exam-meta"><span>状态: <span class="exam-status exam-status-${e.status||'draft'}">${e.status||'draft'}</span></span><span>时长: ${e.duration||60}分钟</span></div>
        <div style="margin-top:12px;display:flex;gap:8px">
          ${e.status==='draft' ? `<button class="auth-quick-btn" onclick="fetch('/api/teacher/exam/${e.id}/publish',{method:'POST'}).then(()=>loadExams())">发布</button>` : ''}
          <button class="auth-quick-btn" onclick="window._viewResults(${e.id})">查看成绩</button>
          <button class="auth-quick-btn" onclick="window._gradeExam(${e.id})">开始批阅</button>
          <button class="auth-quick-btn" onclick="if(confirm('删除?'))fetch('/api/teacher/exam/${e.id}',{method:'DELETE'}).then(()=>loadExams())" style="color:#ef4444">删除</button>
        </div>
      </div>`).join('') || '<p style="color:var(--text-tertiary)">暂无考试</p>';
  }
  window._viewResults = async (examId) => {
    const res = await fetch('/api/teacher/exam/'+examId+'/results'); const data = await res.json();
    const lines = (data.results||[]).map(r => `学生${r.display_name||r.student_id}: ${r.score||'未评分'}分`).join('\n');
    alert('成绩列表:\n'+ (lines || '暂无提交'));
  };
  window._gradeExam = async (examId) => {
    const res = await fetch('/api/teacher/exam/'+examId+'/grade',{method:'POST'}); const data = await res.json();
    alert('待批阅: '+data.count+' 份答卷');
  };
  if (document.readyState==='loading') document.addEventListener('DOMContentLoaded',init); else init();
})();
```

- [ ] **Step 1d: Create `html/teacher-content.html` + `js/teacher-content.js`**

**html/teacher-content.html:**
```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>内容管理 · 星识</title>
  <link rel="stylesheet" href="/css/tokens.css"><link rel="stylesheet" href="/css/teacher.css">
</head>
<body class="teacher-page">
  <div class="teacher-layout">
    <aside class="teacher-sidebar">
      <div class="teacher-brand">⭐ 星识教师端</div>
      <nav class="teacher-nav">
        <a class="teacher-nav-item" href="/teacher-dashboard.html">
工作台</a>
        <a class="teacher-nav-item" href="/teacher-class.html">
班级管理</a>
        <a class="teacher-nav-item" href="/teacher-manage.html">
题库管理</a>
        <a class="teacher-nav-item" href="/teacher-exam.html">
考试管理</a>
        <a class="teacher-nav-item active" href="/teacher-content.html">
内容管理</a>
        <a class="teacher-nav-item" href="/data-dashboard.html">
数据大屏</a>
      </nav>
      <div class="teacher-sidebar-footer"><button class="teacher-logout-btn" id="teacher-logout-btn">退出登录</button></div>
    </aside>
    <main class="teacher-main">
      <h1 class="teacher-page-title">
内容管理</h1>
      <div style="display:flex;gap:16px;margin-bottom:20px">
        <div class="stat-card"><div class="stat-value" id="stat-pending">--</div><div class="stat-label">待审核</div></div>
        <div class="stat-card"><div class="stat-value" id="stat-approved">--</div><div class="stat-label">已通过</div></div>
      </div>
      <div class="content-gen-bar" style="display:flex;gap:12px;margin-bottom:16px;align-items:center;flex-wrap:wrap">
        <select id="gen-lesson-select" class="gen-select" style="padding:8px 12px;border-radius:8px;border:1px solid var(--border-color, #e2e8f0);background:var(--bg-card,#fff);color:var(--text-primary,#1e293b);min-width:200px"><option value="">选择课程...</option></select>
        <select id="gen-model-select" class="gen-select" style="padding:8px 12px;border-radius:8px;border:1px solid var(--border-color, #e2e8f0);background:var(--bg-card,#fff);color:var(--text-primary,#1e293b)"><option value="gpt-4o">GPT-4o</option><option value="gpt-4-turbo">GPT-4 Turbo</option><option value="gpt-3.5-turbo">GPT-3.5 Turbo</option></select>
        <button id="generate-content-btn" class="btn btn-primary" style="padding:8px 20px;border-radius:8px;background:var(--accent,#6366f1);color:#fff;border:none;cursor:pointer;font-weight:600">AI 生成讲义</button>
        <span id="gen-status" style="font-size:13px;color:var(--text-tertiary,#94a3b8)"></span>
      </div>
      <table class="q-table"><thead><tr><th>ID</th><th>课程</th><th>状态</th><th>提交时间</th><th>操作</th></tr></thead><tbody id="review-tbody"></tbody></table>
    </main>
  </div>
  <script src="/js/http-intercept.js"></script><script src="/js/auth.js"></script><script src="/js/teacher-content.js"></script>
</body></html>
```

**js/teacher-content.js:**
```javascript
(function() {
  'use strict';
  async function init() {
    if (!Auth.isTeacher()) { await Auth.fetchMe(); if (!Auth.isTeacher()) return; }
    document.getElementById('teacher-logout-btn')?.addEventListener('click', () => Auth.logout());
    await loadLessons();
    await loadReviews();
    document.getElementById('generate-content-btn')?.addEventListener('click', onGenerate);
  }
  async function loadLessons() {
    const sel = document.getElementById('gen-lesson-select');
    if (!sel) return;
    const res = await fetch('/api/teacher/lessons'); const data = await res.json();
    const lessons = data.lessons||[];
    sel.innerHTML = '<option value="">选择课程...</option>' + lessons.map(l => `<option value="${l.id}">${l.title}</option>`).join('');
  }
  async function onGenerate() {
    const lessonId = document.getElementById('gen-lesson-select')?.value;
    const model = document.getElementById('gen-model-select')?.value || 'gpt-4o';
    const statusEl = document.getElementById('gen-status');
    if (!lessonId) { statusEl.textContent = '请先选择课程'; return; }
    const btn = document.getElementById('generate-content-btn');
    btn.disabled = true; statusEl.textContent = '正在生成讲义草稿...';
    try {
      const res = await fetch('/api/teacher/content/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({lesson_id:parseInt(lessonId),model})});
      const data = await res.json();
      if (data.success) { statusEl.textContent = '生成成功！审核ID: '+data.id; await loadReviews(); }
      else { statusEl.textContent = '生成失败: '+(data.detail||'未知错误'); }
    } catch(e) { statusEl.textContent = '请求失败: '+e.message; }
    finally { btn.disabled = false; }
  }
  async function loadReviews() {
    const res = await fetch('/api/teacher/content/reviews'); const data = await res.json();
    const reviews = data.reviews||[];
    document.getElementById('stat-pending').textContent = reviews.filter(r=>r.status==='pending').length;
    document.getElementById('stat-approved').textContent = reviews.filter(r=>r.status==='approved').length;
    document.getElementById('review-tbody').innerHTML = reviews.map(r => `
      <tr><td>${r.id}</td><td>#${r.lesson_id||'-'}</td><td><span class="exam-status exam-status-${r.status==='approved'?'published':r.status==='rejected'?'ended':'draft'}">${r.status}</span></td>
      <td>${(r.created_at||'').slice(0,10)}</td>
      <td>${r.status==='pending' ? `<button class="auth-quick-btn" onclick="fetch('/api/teacher/content/review/${r.id}/approve',{method:'POST'}).then(()=>location.reload())" style="color:#22c55e">通过</button>
       <button class="auth-quick-btn" onclick="fetch('/api/teacher/content/review/${r.id}/reject',{method:'POST'}).then(()=>location.reload())" style="color:#ef4444">驳回</button>` : '-'}</td></tr>`).join('') || '<tr><td colspan="5" style="color:var(--text-tertiary);text-align:center;padding:40px">暂无审核内容</td></tr>';
  }
  if (document.readyState==='loading') document.addEventListener('DOMContentLoaded',init); else init();
})();
```

- [ ] **Step 1e: Create `html/data-dashboard.html` + `js/data-dashboard.js`**

**html/data-dashboard.html:**
```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>学习数据 · 星识</title>
  <link rel="stylesheet" href="/css/tokens.css"><link rel="stylesheet" href="/css/data-dashboard.css">
  <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
</head>
<body class="data-page">
  <header class="data-header">
    <div class="data-title">
学习数据大屏</div>
    <div class="data-tabs">
      <button class="data-tab active" data-tab="overview">总览</button>
      <button class="data-tab" data-tab="radar">能力雷达</button>
      <button class="data-tab" data-tab="trends">学习趋势</button>
      <button class="data-tab" data-tab="flow">学习流</button>
    </div>
  </header>
  <div class="data-grid" id="data-overview-panel">
    <div class="data-stat-card"><div class="data-stat-value" id="stat-courses">--</div><div class="data-stat-label">课程总数</div></div>
    <div class="data-stat-card"><div class="data-stat-value" id="stat-students">--</div><div class="data-stat-label">学生总数</div></div>
    <div class="data-stat-card"><div class="data-stat-value" id="stat-users">--</div><div class="data-stat-label">平台用户</div></div>
    <div class="data-stat-card"><div class="data-stat-value" id="stat-active">--</div><div class="data-stat-label">今日活跃</div></div>
  </div>
  <div class="data-charts" id="data-charts-panel">
    <div class="data-chart-box" id="chart-trends" style="min-height:320px"></div>
    <div class="data-chart-box" id="chart-radar" style="min-height:320px"></div>
  </div>
  <div class="data-realtime" id="data-flow-panel"><div style="color:#64748b;text-align:center">实时动态加载中...</div></div>
  <script src="/js/http-intercept.js"></script><script src="/js/auth.js"></script><script src="/js/data-dashboard.js"></script>
</body></html>
```

**js/data-dashboard.js:**
```javascript
(function() {
  'use strict';
  let trendsChart=null, radarChart=null;
  async function init() {
    // flow-meter 重定向处理
    const redirectTab = localStorage.getItem('sp_redirect_tab');
    if (redirectTab === 'flow') {
      localStorage.removeItem('sp_redirect_tab');
      const flowTab = document.querySelector('.data-tab[data-tab="flow"]');
      if (flowTab) flowTab.click();
    }
    // Tab 切换 — 联动内容面板
    const panels = { overview: document.getElementById('data-overview-panel'), charts: document.getElementById('data-charts-panel'), flow: document.getElementById('data-flow-panel') };
    const tabPanelMap = { overview:'overview', radar:'charts', trends:'charts', flow:'flow' };
    function showPanel(key) {
      Object.entries(panels).forEach(([k, el]) => { if (el) el.style.display = k === key ? '' : 'none'; });
    }
    document.querySelectorAll('.data-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        document.querySelectorAll('.data-tab').forEach(t=>t.classList.remove('active'));
        tab.classList.add('active');
        showPanel(tabPanelMap[tab.dataset.tab] || 'overview');
      });
    });
    await Promise.all([loadOverview(), loadCharts(), connectRealtime()]);
  }
  async function loadOverview() {
    try {
      const res = await fetch('/api/datacenter/overview?level=school'); const data = await res.json();
      if (data.success && data.stats) {
        document.getElementById('stat-courses').textContent = data.stats.totalCourses||0;
        document.getElementById('stat-students').textContent = data.stats.totalStudents||0;
        document.getElementById('stat-users').textContent = data.stats.totalUsers||0;
      }
    } catch(e) { console.warn('Overview load failed'); }
    document.getElementById('stat-active').textContent = '--';
  }
  async function loadCharts() {
    // Trends
    const trendsEl = document.getElementById('chart-trends');
    if (trendsEl) {
      trendsChart = echarts.init(trendsEl);
      let trendData=[]; let dates=[];
      try {
        const res = await fetch('/api/datacenter/trends?days=30'); const data = await res.json();
        if (data.success && data.trends) { dates = data.trends.map(d=>d.date).reverse(); trendData = data.trends.map(d=>d.hours).reverse(); }
      } catch(e) {}
      if (!trendData.length) { dates = Array.from({length:7},(_,i)=>'06-'+(i+1).toString().padStart(2,'0')); trendData = [2.5,3.1,1.8,4.0,3.2,2.9,3.5]; }
      trendsChart.setOption({
        tooltip:{trigger:'axis'}, xAxis:{type:'category',data:dates}, yAxis:{type:'value',name:'小时'},
        series:[{type:'line',data:trendData,smooth:true,lineStyle:{color:'#6366f1'},areaStyle:{color:'rgba(99,102,241,0.1)'}}]
      });
    }
    // Radar
    const radarEl = document.getElementById('chart-radar');
    if (radarEl) {
      radarChart = echarts.init(radarEl);
      let rData=[];
      try { const res=await fetch('/api/datacenter/radar');const data=await res.json();if(data.success)rData=data.dimensions.map(d=>d.score); } catch(e) {}
      if (!rData.length) rData=[78,85,72,80,76];
      radarChart.setOption({
        radar:{indicator:[{name:'编程',max:100},{name:'理论',max:100},{name:'实践',max:100},{name:'数学',max:100},{name:'综合',max:100}]},
        series:[{type:'radar',data:[{value:rData,name:'能力维度'}],areaStyle:{color:'rgba(99,102,241,0.15)'},lineStyle:{color:'#6366f1'}}]
      });
    }
    window.addEventListener('resize',()=>{trendsChart?.resize();radarChart?.resize();});
  }
  function connectRealtime() {
    const feed = document.getElementById('realtime-feed');
    try {
      const token = Auth.getToken();
      const url = token ? `/api/datacenter/realtime?token=${encodeURIComponent(token)}` : '/api/datacenter/realtime';
      const es = new EventSource(url);
      es.onmessage = (e) => {
        try{const d=JSON.parse(e.data);feed.innerHTML=`<div class="data-realtime-item"><span class="data-realtime-dot active"></span>实时心跳 · ${new Date().toLocaleTimeString()}</div>`+feed.innerHTML;}catch(ex){}
      };
      es.onerror = () => { feed.innerHTML='<div style="color:#64748b;text-align:center">实时连接已断开</div>'; es.close(); };
    } catch(e) { feed.innerHTML='<div style="color:#64748b;text-align:center">实时数据暂不可用</div>'; }
  }
  if (document.readyState==='loading') document.addEventListener('DOMContentLoaded',init); else init();
})();
```

- [ ] **Step 2: Create `css/data-dashboard.css`** (dark-screen theme for data center)

```css
/* ---- Data Dashboard Dark Theme ---- */
.data-page { margin: 0; padding: 0; min-height: 100vh; background: #0a0a14; color: #e2e8f0; font-family: var(--font-sans, system-ui, sans-serif); }
.data-header { padding: 20px 32px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,0.06); }
.data-title { font-size: 22px; font-weight: 700; }
.data-tabs { display: flex; gap: 4px; background: rgba(255,255,255,0.04); border-radius: 10px; padding: 4px; }
.data-tab { padding: 8px 20px; border: none; background: none; color: #94a3b8; cursor: pointer; border-radius: 8px; font-size: 14px; transition: all 0.15s; }
.data-tab.active { background: #6366f1; color: #fff; }
.data-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; padding: 24px 32px; }
.data-stat-card { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 20px; }
.data-stat-value { font-size: 32px; font-weight: 700; color: #6366f1; }
.data-stat-label { font-size: 13px; color: #64748b; margin-top: 4px; }
.data-charts { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; padding: 0 32px 24px; }
.data-chart-box { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 20px; min-height: 320px; }
.data-realtime { margin: 0 32px 24px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 16px 20px; max-height: 200px; overflow-y: auto; }
.data-realtime-item { padding: 6px 0; font-size: 13px; color: #94a3b8; border-bottom: 1px solid rgba(255,255,255,0.04); display: flex; align-items: center; gap: 8px; }
.data-realtime-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.data-realtime-dot.active { background: #22c55e; }
.data-realtime-dot.started { background: #3b82f6; }
```

- [ ] **Step 3: Commit**

```bash
git add html/teacher-class.html html/teacher-manage.html html/teacher-exam.html html/teacher-content.html html/data-dashboard.html js/teacher-class.js js/teacher-manage.js js/teacher-exam.js js/teacher-content.js js/data-dashboard.js css/data-dashboard.css
git commit -m "feat(teacher): scaffold all teacher pages + data dashboard with dark theme"
```

---

### Task 5.8: Database Migration Script

**Files:**
- Create: `migrations/001_teacher_tables.sql`

- [ ] **Step 0: Create migrations directory**

```bash
mkdir -p migrations
```

- [ ] **Step 1: Create migration SQL**

Write the following SQL to `migrations/001_teacher_tables.sql`:

```sql
-- 知域教师端 + 数据大屏 数据库迁移
-- 目标: MySQL (pymysql)。IF NOT EXISTS 确保幂等。
-- ⚠️ SQLite 用户须知: 需将所有 AUTO_INCREMENT 替换为 AUTOINCREMENT，
--    或将 INTEGER PRIMARY KEY AUTO_INCREMENT → INTEGER PRIMARY KEY
--    （SQLite 中 INTEGER PRIMARY KEY 默认自动递增）。
--    建议在 db.py 迁移执行函数中根据 _is_sqlite() 做自动替换。

CREATE TABLE IF NOT EXISTS sp_user (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(64) NOT NULL UNIQUE,
    password_hash VARCHAR(256) NOT NULL,
    display_name VARCHAR(128) DEFAULT '',
    avatar VARCHAR(512) DEFAULT '',
    role VARCHAR(16) DEFAULT 'student',   -- student / teacher / admin
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME
);

CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    teacher_id INTEGER,
    student_id INTEGER,
    title VARCHAR(256) NOT NULL,
    subject VARCHAR(128) DEFAULT '',
    progress INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS classes (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    teacher_id INTEGER NOT NULL,
    name VARCHAR(128) NOT NULL,
    description TEXT DEFAULT '',
    student_count INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS class_students (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    class_id INTEGER NOT NULL,
    student_id INTEGER NOT NULL,
    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (class_id, student_id)
);

CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    teacher_id INTEGER NOT NULL,
    type VARCHAR(32) NOT NULL,             -- choice / short_answer / code
    content TEXT NOT NULL,
    answer TEXT DEFAULT '',
    options_json TEXT DEFAULT '[]',        -- JSON array for choice questions
    difficulty VARCHAR(16) DEFAULT 'medium',
    tags VARCHAR(256) DEFAULT '',
    course_id INTEGER,                      -- 关联课程（可选）
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS exams (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    teacher_id INTEGER NOT NULL,
    title VARCHAR(256) NOT NULL,
    description TEXT DEFAULT '',
    questions_json TEXT DEFAULT '[]',       -- JSON array of question IDs
    class_ids_json TEXT DEFAULT '[]',       -- JSON array of class IDs
    start_time DATETIME,
    end_time DATETIME,
    duration INTEGER DEFAULT 60,           -- minutes
    status VARCHAR(16) DEFAULT 'draft',    -- draft / published / ended
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS exam_results (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    exam_id INTEGER NOT NULL,
    student_id INTEGER NOT NULL,
    score DECIMAL(5,2) DEFAULT 0,
    answers_json TEXT DEFAULT '{}',         -- {question_id: student_answer}
    graded TINYINT DEFAULT 0,              -- 0=未批改, 1=已批改
    graded_at DATETIME,                     -- 批改时间
    comment TEXT DEFAULT '',                -- 教师评语
    submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(exam_id, student_id)             -- 同一学生同一考试仅一份答卷
);

CREATE TABLE IF NOT EXISTS content_reviews (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    lesson_id INTEGER,
    ai_draft_json TEXT,
    status VARCHAR(16) DEFAULT 'pending',  -- pending / approved / rejected
    reviewer_id INTEGER,
    reviewed_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS data_snapshots (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    snapshot_type VARCHAR(32) NOT NULL,     -- daily / weekly / monthly
    snapshot_date DATE NOT NULL,
    metrics_json TEXT DEFAULT '{}',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS memories (
    id VARCHAR(8) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    type VARCHAR(32) DEFAULT 'general',
    content TEXT DEFAULT '',
    source VARCHAR(32) DEFAULT 'mascot',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

- [ ] **Step 2: Commit**

```bash
git add migrations/001_teacher_tables.sql
git commit -m "feat(db): add migration for sp_user, classes, questions, exams, content_reviews, data_snapshots"
```

---

## Final Integration

### Task 5.9: Integration Verification

- [ ] **Step 1: Verify all Python imports resolve**

Run: `python -c "
from app.api.mascot import router as mr
from app.api.auth import router as ar
from app.api.teacher import router as tr
from app.api.datacenter import router as dr
from app.utils.jwt import create_token, verify_token
from app.middleware.auth import get_current_user
from app.middleware.roles import require_role
print('All imports OK')
"`

- [ ] **Step 2: Verify main.py starts without import errors**

Run: `python -c "from main import app; print(f'Routes: {len(app.routes)}')"`
Expected: No import errors, routes count increased.

- [ ] **Step 3: Verify frontend JS syntax**

Run: `for f in js/mascot.js js/search-command.js js/onboarding.js js/auth.js js/http-intercept.js js/teacher-dashboard.js; do node --check "$f" && echo "$f OK"; done`

- [ ] **Step 4: Final commit**

```bash
git add js/mascot.js css/mascot.css app/api/mascot.py \
  html/hub.html css/hub.css html/index.html html/personal.html \
  html/socratic-ai.html html/video-player.html html/code.html html/courses.html \
  html/progress.html html/calendar.html html/flow-meter.html \
  html/stellar-showcase.html html/plant.html html/settings.html \
  html/my-courses.html js/search-command.js css/search-command.css \
  js/onboarding.js css/onboarding.css \
  db.py html/login.html js/auth.js js/http-intercept.js css/auth.css \
  html/teacher-dashboard.html js/teacher-dashboard.js \
  html/teacher-class.html js/teacher-class.js \
  html/teacher-manage.html js/teacher-manage.js \
  html/teacher-exam.html js/teacher-exam.js \
  html/teacher-content.html js/teacher-content.js \
  html/data-dashboard.html js/data-dashboard.js \
  css/teacher.css css/data-dashboard.css \
  app/api/auth.py app/api/teacher.py app/api/datacenter.py \
  app/utils/jwt.py app/middleware/auth.py app/middleware/roles.py \
  app/models/teacher.py migrations/001_teacher_tables.sql main.py
git commit -m "chore: integration verification — all imports resolve, JS syntax passes"
```

---

## Plan Summary

| Phase | Tasks | Files Created | Files Modified | Est. Commits |
|-------|-------|---------------|----------------|--------------|
| Phase 3 (看板娘) | 3.1–3.4 | 4 | 2 | 4 |
| Phase 4 (导航) | 4.1–4.3 | 4 | 3 | 3 |
| Phase 5 (知域) | 5.1–5.9 | 23 | 2 | 7 |
| **Total** | **14 tasks** | **31 files** | **7 files** | **14 commits** |

**Execution order:** Phase 3 → Phase 4 → Phase 5 (sequential per spec)
