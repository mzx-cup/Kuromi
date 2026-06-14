/**
 * agent-orchestrator.js — 控制塔控制器 (状态机)
 *
 * 启动 Agent 流水线, 通过 POST /api/agents/execute 启动并消费其 SSE 响应流。
 * 注意: 后端 /api/agents/execute 本身返回 StreamingResponse (SSE),
 *       没有独立的 /api/agents/stream 端点 —— 不可拆成 "fetch POST + EventSource" 两步。
 *       因此本模块直接用 fetch + ReadableStream 消费 POST 响应流。
 *
 * 用法:
 *   agentOrchestrator.on('stateChange', (s) => console.log('state:', s));
 *   await agentOrchestrator.startPipeline({ studentId: 'u1', userInput: 'hi' });
 *
 * 设计要点:
 *   - 状态机: IDLE / RUNNING / COMPLETE / FAILED
 *   - 收到 pipeline_complete -> COMPLETE + 终止流
 *   - 收到 fatal error      -> FAILED
 *   - POST 失败 (网络/后端 5xx) -> 触发 agentMockFallback.runMockPipeline()
 *   - Trace ID 由前端生成, 在 POST body 中传给后端, 后端会在事件里回显
 *   - 所有 listener 回调包在 try/catch 里, 单个订阅者抛错不影响其他订阅者
 */
(function (global) {
  'use strict';

  const STATES = Object.freeze({
    IDLE: 'idle',
    RUNNING: 'running',
    COMPLETE: 'complete',
    FAILED: 'failed',
  });

  const EXECUTE_URL = '/api/agents/execute';

  /**
   * POST JSON 到 url, 将响应当作 SSE 流解析.
   * 返回 async generator, 每次 yield 一个 { event, data } 对象.
   *
   * SSE 协议帧格式:
   *   event: <name>\n
   *   data: <json>\n
   *   \n
   *
   * 注意: 后端 FastAPI StreamingResponse 通常会先发一行注释 ":ok\n\n"
   *       (SSE 注释帧), 我们的解析器对没有 event/data 行的 raw 直接跳过, 不会出错.
   */
  async function* postSse(url, payload) {
    const r = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!r.ok) {
      throw new Error('SSE init failed: HTTP ' + r.status);
    }
    if (!r.body || typeof r.body.getReader !== 'function') {
      throw new Error('SSE init failed: response body is not a stream');
    }

    const reader = r.body.getReader();
    const decoder = new TextDecoder();
    let buf = '';

    try {
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });

        // 按 "\n\n" 切分完整事件帧
        let idx;
        while ((idx = buf.indexOf('\n\n')) !== -1) {
          const raw = buf.slice(0, idx);
          buf = buf.slice(idx + 2);
          yield* parseSseFrame(raw);
        }
      }
    } finally {
      try { reader.releaseLock(); } catch (_) { /* ignore */ }
    }
  }

  /**
   * 解析单个 SSE 事件帧. 若不是 event/data 形式 (e.g. 注释行, 多行 data),
   * 则不产出任何元素.
   * @param {string} raw
   * @returns {Generator<{event: string, data: any}>}
   */
  function* parseSseFrame(raw) {
    const eventMatch = raw.match(/^event:\s*(.+)$/m);
    const dataMatch = raw.match(/^data:\s*([\s\S]+)$/m);
    if (!eventMatch || !dataMatch) return;
    let parsed;
    try {
      parsed = JSON.parse(dataMatch[1]);
    } catch (e) {
      // eslint-disable-next-line no-console
      console.error('[orchestrator] SSE JSON parse error', e, dataMatch[1]);
      return;
    }
    yield { event: eventMatch[1].trim(), data: parsed };
  }

  class AgentOrchestrator {
    constructor() {
      this.state = STATES.IDLE;
      this.traceId = null;
      this._abortController = null;
      this._listeners = { stateChange: [], asset: [] };
    }

    /**
     * 订阅 orchestrator 事件. 返回取消订阅的函数.
     * @param {'stateChange'|'asset'} event
     * @param {Function} fn
     * @returns {Function}
     */
    on(event, fn) {
      if (!this._listeners[event]) this._listeners[event] = [];
      this._listeners[event].push(fn);
      return () => {
        const arr = this._listeners[event];
        if (!arr) return;
        const i = arr.indexOf(fn);
        if (i !== -1) arr.splice(i, 1);
      };
    }

    /**
     * 切换状态并广播 stateChange.
     * @param {string} s
     */
    setState(s) {
      this.state = s;
      const arr = this._listeners.stateChange || [];
      const snapshot = arr.slice();
      for (const fn of snapshot) {
        try { fn(s); } catch (e) {
          // eslint-disable-next-line no-console
          console.error('[orchestrator] stateChange listener threw', e);
        }
      }
    }

    /**
     * 启动流水线. 会自动:
     *   1. 把状态切到 RUNNING
     *   2. mock=true 时直接走 agentMockFallback
     *   3. 否则 POST /api/agents/execute 并消费 SSE
     *   4. 收到 pipeline_complete 终止
     *   5. 网络失败时降级到 mock
     */
    async startPipeline({ studentId, courseId, userInput, mock = false } = {}) {
      this.setState(STATES.RUNNING);
      this.traceId = (global.crypto && typeof crypto.randomUUID === 'function')
        ? crypto.randomUUID()
        : 't-' + Date.now() + '-' + Math.random().toString(36).slice(2, 10);

      if (mock) {
        if (global.agentMockFallback && typeof global.agentMockFallback.runMockPipeline === 'function') {
          global.agentMockFallback.runMockPipeline(this);
        } else {
          // eslint-disable-next-line no-console
          console.warn('[orchestrator] mock=true but agentMockFallback missing; marking FAILED');
          this.setState(STATES.FAILED);
        }
        return;
      }

      const payload = {
        student_id: studentId || '',
        course_id: courseId || null,
        user_input: userInput || '',
        trace_id: this.traceId,
      };

      this._abortController = (typeof AbortController !== 'undefined')
        ? new AbortController()
        : null;

      try {
        for await (const { event, data } of postSse(EXECUTE_URL, payload)) {
          if (this._abortController && this._abortController.signal.aborted) break;
          this._handleSseEvent(event, data);
        }
        // 正常流结束: 若未进入 COMPLETE/FAILED, 留在 RUNNING 让上层决定.
        // 这里不强制回 IDLE, 避免把"业务完成但客户端先断"误判.
      } catch (err) {
        // eslint-disable-next-line no-console
        console.error('[orchestrator] startPipeline failed', err);
        if (err && err.name === 'AbortError') {
          this.setState(STATES.IDLE);
          return;
        }
        // 网络/后端失败 -> 降级到 mock
        if (global.agentMockFallback && typeof global.agentMockFallback.runMockPipeline === 'function') {
          // eslint-disable-next-line no-console
          console.warn('[orchestrator] falling back to mock pipeline after SSE failure');
          global.agentMockFallback.runMockPipeline(this);
        } else {
          this.setState(STATES.FAILED);
        }
      }
    }

    /**
     * 处理单个 SSE 事件: 转发到 agentBus, 并根据事件类型更新状态.
     * @param {string} name
     * @param {any} data
     */
    _handleSseEvent(name, data) {
      if (global.agentBus && typeof global.agentBus.emit === 'function') {
        try { global.agentBus.emit(name, data); }
        catch (e) {
          // eslint-disable-next-line no-console
          console.error('[orchestrator] agentBus.emit threw', e);
        }
      }
      if (name === 'pipeline_complete') {
        this.setState(STATES.COMPLETE);
        if (this._abortController) this._abortController.abort();
      } else if (name === 'error' && data && data.fatal) {
        this.setState(STATES.FAILED);
        if (this._abortController) this._abortController.abort();
      }
    }

    /**
     * mock 流水线回调使用: 把一条 asset 记录广播给 asset 订阅者.
     * (真正的 agentMockFallback 通过 agentBus.emit('asset_ready', ...) 也行,
     * 这里保留一个直连通道方便 mock 模式下不走 agentBus.)
     * @param {any} asset
     */
    emitAsset(asset) {
      const arr = this._listeners.asset || [];
      const snapshot = arr.slice();
      for (const fn of snapshot) {
        try { fn(asset); }
        catch (e) {
          // eslint-disable-next-line no-console
          console.error('[orchestrator] asset listener threw', e);
        }
      }
    }

    /**
     * 主动停止流水线 (中断 SSE 读取, 状态回到 IDLE).
     */
    stop() {
      if (this._abortController) this._abortController.abort();
      this.setState(STATES.IDLE);
    }
  }

  const AgentOrchestratorApi = AgentOrchestrator;

  // 浏览器: 挂到 window
  if (typeof window !== 'undefined') {
    global.AgentOrchestrator = AgentOrchestratorApi;
    global.agentOrchestrator = new AgentOrchestratorApi();
  }

  // Node/Vitest (CommonJS): 暴露给 require
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = AgentOrchestratorApi;
    module.exports.AgentOrchestrator = AgentOrchestratorApi;
    module.exports.STATES = STATES;
    module.exports.default = AgentOrchestratorApi;
  }
})(typeof window !== 'undefined' ? window : globalThis);
