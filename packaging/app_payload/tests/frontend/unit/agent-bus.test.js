/**
 * agent-bus.js — 前端事件总线 (pub/sub) 单元测试
 *
 * 测试范围:
 *   1. subscribe / emit 基础流程
 *   2. unsubscribe 函数能正确移除订阅
 *   3. 多订阅者全部触发
 *   4. 单个订阅者抛错不影响其他订阅者
 *   5. clear() 清空所有订阅
 *   6. emit 无订阅者时是 no-op
 *   7. subscribe 非函数时抛 TypeError
 *   8. 重复订阅同一 handler 是幂等的 (Set 语义)
 *
 * 运行: npx vitest run tests/frontend/unit/agent-bus.test.js
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

describe('agentBus — 事件总线', () => {
  beforeEach(async () => {
    // 清理上一个测试可能挂载的全局 (IIFE 模式)
    delete window.agentBus;
    vi.resetModules();
    // 重新加载,获取干净的 module 级 listeners 状态
    await import('../../../js/agent-bus.js');
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('应挂载到 window.agentBus', () => {
    expect(window.agentBus).toBeDefined();
    expect(typeof window.agentBus.subscribe).toBe('function');
    expect(typeof window.agentBus.emit).toBe('function');
    expect(typeof window.agentBus.clear).toBe('function');
  });

  it('subscribe + emit 应调用回调并把 payload 传过去', () => {
    const fn = vi.fn();
    window.agentBus.subscribe('agent_step', fn);

    window.agentBus.emit('agent_step', { agent: 'profiler', step: 1 });

    expect(fn).toHaveBeenCalledTimes(1);
    expect(fn).toHaveBeenCalledWith({ agent: 'profiler', step: 1 });
  });

  it('返回的 off() 取消订阅', () => {
    const fn = vi.fn();
    const off = window.agentBus.subscribe('agent_step', fn);

    window.agentBus.emit('agent_step', { v: 1 });
    expect(fn).toHaveBeenCalledTimes(1);

    off();

    window.agentBus.emit('agent_step', { v: 2 });
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it('多个订阅者应都被调用', () => {
    const a = vi.fn();
    const b = vi.fn();
    window.agentBus.subscribe('profile_updated', a);
    window.agentBus.subscribe('profile_updated', b);

    window.agentBus.emit('profile_updated', { v: 1 });

    expect(a).toHaveBeenCalledWith({ v: 1 });
    expect(b).toHaveBeenCalledWith({ v: 1 });
  });

  it('不同事件互不干扰', () => {
    const step = vi.fn();
    const done = vi.fn();
    window.agentBus.subscribe('agent_step', step);
    window.agentBus.subscribe('agent_done', done);

    window.agentBus.emit('agent_step', { x: 1 });

    expect(step).toHaveBeenCalledWith({ x: 1 });
    expect(done).not.toHaveBeenCalled();
  });

  it('单个订阅者抛错不应影响其他订阅者', () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    const bad = vi.fn(() => { throw new Error('boom'); });
    const good = vi.fn();

    window.agentBus.subscribe('test_evt', bad);
    window.agentBus.subscribe('test_evt', good);

    // 不应该向上抛出
    expect(() => window.agentBus.emit('test_evt', { x: 1 })).not.toThrow();

    expect(bad).toHaveBeenCalledWith({ x: 1 });
    expect(good).toHaveBeenCalledWith({ x: 1 });
    expect(consoleSpy).toHaveBeenCalled();
    consoleSpy.mockRestore();
  });

  it('clear() 应移除所有订阅', () => {
    const fn = vi.fn();
    window.agentBus.subscribe('foo', fn);
    window.agentBus.subscribe('bar', fn);

    window.agentBus.clear();

    window.agentBus.emit('foo', { x: 1 });
    window.agentBus.emit('bar', { x: 2 });
    expect(fn).not.toHaveBeenCalled();
  });

  it('emit 一个没有任何订阅者的事件应为 no-op', () => {
    expect(() => window.agentBus.emit('nobody_home', { x: 1 })).not.toThrow();
  });

  it('subscribe 非函数应抛 TypeError', () => {
    expect(() => window.agentBus.subscribe('e', null)).toThrow(TypeError);
    expect(() => window.agentBus.subscribe('e', 'not-a-fn')).toThrow(TypeError);
  });

  it('同一 handler 重复订阅应保持单条 (Set 语义)', () => {
    const fn = vi.fn();
    window.agentBus.subscribe('dup', fn);
    window.agentBus.subscribe('dup', fn);

    window.agentBus.emit('dup', { v: 1 });

    expect(fn).toHaveBeenCalledTimes(1);
  });

  it('off() 后再 subscribe 应能重新工作', () => {
    const fn = vi.fn();
    const off = window.agentBus.subscribe('re', fn);
    off();
    window.agentBus.subscribe('re', fn);

    window.agentBus.emit('re', { v: 1 });

    expect(fn).toHaveBeenCalledTimes(1);
  });
});