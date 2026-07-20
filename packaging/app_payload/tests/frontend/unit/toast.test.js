/**
 * Toast 通知系统 — 单元测试
 *
 * 测试范围：
 *   1. 核心 API 存在性
 *   2. Toast 创建和 DOM 挂载
 *   3. 五种类型 (info/success/error/warning/mascot)
 *   4. 自动关闭计时器
 *   5. 手动关闭
 *   6. XSS 防护 (escapeHTML)
 *   7. 操作按钮回调
 *   8. 容器复用
 *
 * 运行: npx vitest run tests/frontend/unit/toast.test.js
 */

// 注意：toast.js 使用 IIFE 模式且依赖 document 对象
// 需要在 jsdom 环境中运行

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

// 模拟 DOM 环境由 vitest 的 jsdom 环境提供

describe('Toast — 核心 API', () => {
  beforeEach(async () => {
    // 清理 DOM
    document.body.innerHTML = '';
    // 重置 timer mock
    vi.useFakeTimers();
    // 加载 toast.js（每次测试前重新加载以重置状态）
    // toast.js 通过 IIFE 挂载 window.Toast
    vi.resetModules();
    await import('../../../js/toast.js');
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('应该暴露全局 Toast API', () => {
    expect(window.Toast).toBeDefined();
    expect(typeof window.Toast.show).toBe('function');
    expect(typeof window.Toast.info).toBe('function');
    expect(typeof window.Toast.ok).toBe('function');
    expect(typeof window.Toast.error).toBe('function');
    expect(typeof window.Toast.warning).toBe('function');
    expect(typeof window.Toast.mascot).toBe('function');
    expect(typeof window.Toast.dismiss).toBe('function');
  });

  it('show() 应该创建 toast 元素并挂载到 DOM', () => {
    window.Toast.show('测试消息', 'info');

    const container = document.querySelector('.app-toast-container');
    expect(container).not.toBeNull();
    expect(container.children.length).toBe(1);

    const toast = container.querySelector('.app-toast');
    expect(toast).not.toBeNull();
    expect(toast.classList.contains('app-toast--info')).toBe(true);
    expect(toast.querySelector('.app-toast-title').textContent).toBe('测试消息');
  });

  it('每种类型应设置正确的 CSS 类', () => {
    const types = ['info', 'success', 'error', 'warning'];
    const classMap = {
      info: 'app-toast--info',
      success: 'app-toast--success',
      error: 'app-toast--error',
      warning: 'app-toast--warning',
    };

    types.forEach((type) => {
      window.Toast.show(type, type);
      const toast = document.querySelector('.app-toast--' + type);
      expect(toast).not.toBeNull();
      // 清理以便下个迭代
      document.body.innerHTML = '';
    });
  });

  it('快捷方法应创建正确类型的 toast', () => {
    window.Toast.info('info 消息');
    expect(document.querySelector('.app-toast--info')).not.toBeNull();
    document.body.innerHTML = '';

    window.Toast.ok('成功消息');
    expect(document.querySelector('.app-toast--success')).not.toBeNull();
    document.body.innerHTML = '';

    window.Toast.error('错误消息');
    expect(document.querySelector('.app-toast--error')).not.toBeNull();
    document.body.innerHTML = '';

    window.Toast.warning('警告消息');
    expect(document.querySelector('.app-toast--warning')).not.toBeNull();
  });

  it('mascot() 应创建带 mascot 变体的 toast', () => {
    window.Toast.mascot('小星提醒', '该休息啦~');

    const toast = document.querySelector('.app-toast--mascot');
    expect(toast).not.toBeNull();
    expect(toast.querySelector('.app-toast-title').textContent).toBe('小星提醒');
    expect(toast.querySelector('.app-toast-content').textContent).toBe('该休息啦~');
  });

  it('默认 3 秒后自动关闭', () => {
    window.Toast.show('自动关闭', 'info');
    expect(document.querySelector('.app-toast')).not.toBeNull();

    // 快进 3 秒
    vi.advanceTimersByTime(3100);

    // toast 应该被标记为 removing
    const toast = document.querySelector('.app-toast');
    if (toast) {
      expect(toast.classList.contains('app-toast--removing')).toBe(true);
    }
  });

  it('duration:0 应该不自动关闭', () => {
    window.Toast.show('不关闭', 'info', { duration: 0 });
    vi.advanceTimersByTime(10000);

    const toast = document.querySelector('.app-toast');
    expect(toast).not.toBeNull();
    expect(toast.classList.contains('app-toast--removing')).toBe(false);
  });

  it('dismiss() 应手动关闭指定 toast', () => {
    const toast = window.Toast.show('手动关闭', 'info');
    expect(document.querySelector('.app-toast')).not.toBeNull();

    window.Toast.dismiss(toast);
    expect(toast.classList.contains('app-toast--removing')).toBe(true);
  });

  it('关闭按钮点击应触发 dismiss', () => {
    window.Toast.show('点击关闭', 'info');

    const closeBtn = document.querySelector('.app-toast-close');
    expect(closeBtn).not.toBeNull();

    closeBtn.click();
    const toast = document.querySelector('.app-toast');
    expect(toast.classList.contains('app-toast--removing')).toBe(true);
  });

  it('应转义 HTML 防止 XSS', () => {
    window.Toast.show('<script>alert("xss")</script>', 'info');

    const title = document.querySelector('.app-toast-title');
    // textContent 应该是字面量，不是 HTML
    expect(title.textContent).toBe('<script>alert("xss")</script>');
    expect(title.innerHTML).not.toContain('<script>');
  });

  it('操作按钮应该触发回调并关闭 toast', () => {
    let called = false;

    window.Toast.show('确认删除？', 'warning', {
      actionLabel: '确认',
      actionCallback: function () {
        called = true;
      },
    });

    const actionBtn = document.querySelector('.app-toast-action');
    expect(actionBtn).not.toBeNull();
    expect(actionBtn.textContent).toBe('确认');

    actionBtn.click();
    expect(called).toBe(true);

    const toast = document.querySelector('.app-toast');
    expect(toast.classList.contains('app-toast--removing')).toBe(true);
  });

  it('多个 toast 应复用同一个容器', () => {
    window.Toast.show('消息 1', 'info');
    window.Toast.show('消息 2', 'info');

    const containers = document.querySelectorAll('.app-toast-container');
    expect(containers.length).toBe(1);
    expect(containers[0].children.length).toBe(2);
  });

  it('transitionend 后应从 DOM 移除', () => {
    window.Toast.show('移除测试', 'info');
    const toast = document.querySelector('.app-toast');

    window.Toast.dismiss(toast);

    // 模拟 transitionend 事件
    toast.dispatchEvent(new Event('transitionend'));

    // toast 应该被移除
    expect(document.querySelector('.app-toast')).toBeNull();
  });

  it('若 transitionend 未触发，400ms fallback 应移除 toast', () => {
    window.Toast.show('fallback 测试', 'info');
    const toast = document.querySelector('.app-toast');

    window.Toast.dismiss(toast);
    // 不触发 transitionend，等 fallback
    vi.advanceTimersByTime(500);

    expect(document.querySelector('.app-toast')).toBeNull();
  });
});
