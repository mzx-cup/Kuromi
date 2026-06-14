/**
 * agent-sse-client.js — EventSource 客户端
 *
 * 连接后端 /api/agents/execute SSE 端点，断线自动重连，失败触发 mock fallback。
 * 主要用于解耦 SSE 传输层与 orchestrator / agentBus：
 *   - SSE 收到事件 -> onEvent(name, data) -> 由调用者决定是否 emit 到 agentBus
 *   - 失败触发     -> onMockTrigger()   -> orchestrator 接驳到 mock pipeline
 *
 * 用法:
 *   const client = agentSseClient.createClient({
 *     url: '/api/agents/execute?student_id=u1&user_input=hi',
 *     onEvent: (name, data) => agentBus.emit(name, data),
 *     onError: (err) => console.error(err),
 *     onMockTrigger: () => agentMockFallback.runMockPipeline(orchestrator),
 *   });
 *   // ...later
 *   client.close();
 *
 * 设计要点:
 *   - 监听 6 种后端事件类型：agent_step, profile_updated, asset_ready,
 *                            pipeline_complete, error, heartbeat
 *   - 自动重连 MAX_RETRIES 次，每次间隔 RETRY_DELAY_MS
 *   - 重连耗尽后调用 onMockTrigger 触发 mock fallback
 *   - close() 是幂等的：用户主动断开后不再触发 mock fallback / 重连
 *   - EventSource 构造使用 try/catch，避免 SSR / 不支持环境直接抛 ReferenceError
 */
(function (global) {
  'use strict';

  const MAX_RETRIES = 3;
  const RETRY_DELAY_MS = 2000;

  const SSE_EVENTS = [
    'agent_step',
    'profile_updated',
    'asset_ready',
    'pipeline_complete',
    'error',
    'heartbeat',
  ];

  /**
   * 创建一个 SSE 客户端。
   * @param {Object} options
   * @param {string} options.url SSE 端点 URL（含 query string）
   * @param {Function} [options.onEvent] (name, data) => void
   * @param {Function} [options.onError] (err) => void
   * @param {Function} [options.onMockTrigger] () => void
   * @returns {{ close: Function }} 客户端句柄
   */
  function createClient({ url, onEvent, onError, onMockTrigger }) {
    let es = null;
    let retries = 0;
    let closedByUser = false;

    function connect() {
      try {
        es = new EventSource(url);
      } catch (err) {
        if (onError) onError(err);
        if (onMockTrigger) onMockTrigger();
        return;
      }

      SSE_EVENTS.forEach((name) => {
        es.addEventListener(name, (e) => {
          try {
            const data = JSON.parse(e.data);
            if (onEvent) onEvent(name, data);
          } catch (err) {
            // eslint-disable-next-line no-console
            console.error('[sse-client] parse', name, err);
          }
        });
      });

      es.onerror = () => {
        if (closedByUser) return;
        if (es) es.close();
        retries += 1;
        if (retries > MAX_RETRIES) {
          if (onMockTrigger) onMockTrigger();
          if (onError) onError(new Error('SSE failed after retries'));
          return;
        }
        setTimeout(connect, RETRY_DELAY_MS);
      };
    }

    function close() {
      closedByUser = true;
      if (es) es.close();
    }

    connect();
    return { close };
  }

  const api = { createClient };

  // 浏览器: 挂到 window
  if (typeof window !== 'undefined') {
    global.agentSseClient = api;
  }

  // Node/Vitest (CommonJS): 暴露给 require
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
    module.exports.agentSseClient = api;
    module.exports.default = api;
  }
})(typeof window !== 'undefined' ? window : globalThis);