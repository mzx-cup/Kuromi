/**
 * agent-bus.js — 前端事件总线 (pub/sub)
 *
 * 给前端 Agent 编排控制塔用的轻量事件总线。
 * 主要用于解耦 SSE 客户端、orchestrator、UI 渲染层：
 *   - SSE 客户端收到事件 -> agentBus.emit('agent_step', envelope)
 *   - UI 渲染层订阅     -> agentBus.subscribe('agent_step', handler)
 *
 * 用法:
 *   const off = agentBus.subscribe('agent_step', (envelope) => {...});
 *   agentBus.emit('agent_step', envelope);
 *   off();   // 取消订阅
 *
 * 设计要点:
 *   - 每个事件一个 Set 持有订阅者，subscribe 返回 unsubscribe 函数
 *   - 单个 handler 抛错不影响其他订阅者
 *   - clear() 用于测试间隔离
 */
(function (global) {
  'use strict';

  /** @type {Map<string, Set<Function>>} */
  const listeners = new Map();

  /**
   * 订阅事件。
   * @param {string} event 事件名
   * @param {Function} fn 回调
   * @returns {Function} 取消订阅的函数
   */
  function subscribe(event, fn) {
    if (typeof fn !== 'function') {
      throw new TypeError('agentBus.subscribe: fn must be a function');
    }
    if (!listeners.has(event)) {
      listeners.set(event, new Set());
    }
    const set = listeners.get(event);
    set.add(fn);
    return function off() {
      const s = listeners.get(event);
      if (s) s.delete(fn);
    };
  }

  /**
   * 触发事件。所有订阅者会被同步调用；单个订阅者抛错不会中断其他订阅者。
   * @param {string} event 事件名
   * @param {*} payload 载荷
   */
  function emit(event, payload) {
    const set = listeners.get(event);
    if (!set || set.size === 0) return;
    // 拷贝一份快照，避免迭代过程中被 mutate 影响
    const snapshot = Array.from(set);
    for (const fn of snapshot) {
      try {
        fn(payload);
      } catch (err) {
        // eslint-disable-next-line no-console
        console.error('[agentBus] subscriber threw for event', event, err);
      }
    }
  }

  /** 清空所有订阅（主要用于测试）。 */
  function clear() {
    listeners.clear();
  }

  /** 当前事件名列表（调试用）。 */
  function events() {
    return Array.from(listeners.keys());
  }

  const api = { subscribe, emit, clear, events };

  // 浏览器: 挂到 window
  if (typeof window !== 'undefined') {
    global.agentBus = api;
  }

  // Node/Vitest (CommonJS): 暴露给 require
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
    module.exports.agentBus = api;
    module.exports.default = api;
  }
})(typeof window !== 'undefined' ? window : globalThis);