/**
 * Auth — JWT 认证模块单元测试
 *
 * 测试范围：
 *   1. Token 存储和读取
 *   2. Token 过期验证
 *   3. 角色判断
 *   4. logout 清理
 *   5. fetchMe API 调用
 *   6. DOM 角色可见性控制
 *
 * 运行: npx vitest run tests/frontend/unit/auth.test.js
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

// auth.js 使用 const + IIFE 模式，需要 jsdom 环境

describe('Auth — Token 管理', () => {
  beforeEach(async () => {
    document.body.innerHTML = '';
    localStorage.clear();
    vi.resetModules();

    // Mock fetch
    global.fetch = vi.fn();

    // Mock window.location
    delete window.location;
    window.location = { href: '', replace: vi.fn() };

    await import('../../../js/auth.js');
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ========== Token 存储 ==========

  it('getToken() 应从 localStorage 读取 sp_token', () => {
    localStorage.setItem('sp_token', 'test.jwt.token');
    expect(window.Auth.getToken()).toBe('test.jwt.token');
  });

  it('getToken() 在无 token 时返回 null', () => {
    expect(window.Auth.getToken()).toBeNull();
  });

  it('setToken() 应保存 token 和可选的 user 信息', () => {
    window.Auth.setToken('new.token.value', { name: '测试', role: 'student' });

    expect(localStorage.getItem('sp_token')).toBe('new.token.value');
    expect(JSON.parse(localStorage.getItem('sp_user'))).toEqual({
      name: '测试',
      role: 'student',
    });
  });

  // ========== Token 过期验证 ==========

  it('isTokenValid() 应返回 false 当无 token', () => {
    expect(window.Auth.isTokenValid()).toBe(false);
  });

  it('isTokenValid() 应返回 true 当 token 未过期', () => {
    // 构造一个未来过期的 JWT
    const future = Math.floor(Date.now() / 1000) + 3600;
    const payload = btoa(JSON.stringify({ exp: future, sub: 'user1' }));
    const token = 'header.' + payload + '.signature';
    localStorage.setItem('sp_token', token);

    expect(window.Auth.isTokenValid()).toBe(true);
  });

  it('isTokenValid() 应返回 false 当 token 已过期', () => {
    const past = Math.floor(Date.now() / 1000) - 3600;
    const payload = btoa(JSON.stringify({ exp: past }));
    const token = 'header.' + payload + '.signature';
    localStorage.setItem('sp_token', token);

    expect(window.Auth.isTokenValid()).toBe(false);
  });

  it('isTokenValid() 应返回 true 当 token 无 exp 字段', () => {
    const payload = btoa(JSON.stringify({ sub: 'user1' }));
    const token = 'header.' + payload + '.signature';
    localStorage.setItem('sp_token', token);

    expect(window.Auth.isTokenValid()).toBe(true);
  });

  it('isTokenValid() 应处理损坏的 token', () => {
    localStorage.setItem('sp_token', 'not.a.valid.jwt');
    expect(window.Auth.isTokenValid()).toBe(false);
  });

  it('isTokenValid() 应兼容 PyJWT 输出的 base64url (无 padding, 字符 -_)', () => {
    // PyJWT / Go-jwt / js-jwt 默认 encode 是 base64url：
    //  - 用 `-` 替换 `+`
    //  - 用 `_` 替换 `/`
    //  - 去掉尾部 `=` padding
    const future = Math.floor(Date.now() / 1000) + 3600;
    const payload = btoa(JSON.stringify({ exp: future, sub: 'u1' }))
      .replace(/=+$/, '')
      .replace(/\+/g, '-')
      .replace(/\//g, '_');
    const token = 'h.' + payload + '.s';
    localStorage.setItem('sp_token', token);
    expect(window.Auth.isTokenValid()).toBe(true);
  });

  it('isTokenValid() 应兼容含 + / = 的标准 base64', () => {
    const future = Math.floor(Date.now() / 1000) + 3600;
    // 构造一个 base64 后会含 / + = 的 payload
    const raw = btoa(JSON.stringify({ exp: future, sub: 'a'.repeat(20) }));
    expect(/[+/=]/.test(raw)).toBe(true);  // 确认这个 payload 确实含特殊字符
    const token = 'h.' + raw + '.s';
    localStorage.setItem('sp_token', token);
    expect(window.Auth.isTokenValid()).toBe(true);
  });

  it('isTokenValid() 在 payload 段为空时返回 false', () => {
    localStorage.setItem('sp_token', 'header..signature');
    expect(window.Auth.isTokenValid()).toBe(false);
  });

  // ========== 角色判断 ==========

  it('isTeacher() 应在 role=teacher 时返回 true', async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ user: { role: 'teacher', name: '张老师' } }),
    });
    localStorage.setItem('sp_token', 'valid.token.test');
    await window.Auth.fetchMe();
    expect(window.Auth.isTeacher()).toBe(true);
    expect(window.Auth.isStudent()).toBe(false);
  });

  it('isStudent() 应在 role=student 时返回 true', async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ user: { role: 'student', name: '小明' } }),
    });
    localStorage.setItem('sp_token', 'valid.token.test');
    await window.Auth.fetchMe();
    expect(window.Auth.isStudent()).toBe(true);
    expect(window.Auth.isTeacher()).toBe(false);
  });

  // ========== logout ==========

  it('logout() 应清除所有认证状态并跳转', () => {
    localStorage.setItem('sp_token', 'some.token');
    localStorage.setItem('sp_user', JSON.stringify({ name: 'test' }));
    localStorage.setItem('starlearn_user', JSON.stringify({ name: 'legacy' }));

    window.Auth.logout();

    expect(localStorage.getItem('sp_token')).toBeNull();
    expect(localStorage.getItem('sp_user')).toBeNull();
    expect(localStorage.getItem('starlearn_user')).toBeNull();
    // 使用 replace 跳转，避免浏览器后退到已退出账号的页面
    expect(window.location.replace).toHaveBeenCalledWith('/login.html');
  });

  // ========== fetchMe ==========

  it('fetchMe() 应在无 token 时抛出错误', async () => {
    await expect(window.Auth.fetchMe()).rejects.toThrow('No token');
  });

  it('fetchMe() 应在 401 时清除 token 并抛出', async () => {
    fetch.mockResolvedValueOnce({
      ok: false,
      status: 401,
    });
    localStorage.setItem('sp_token', 'expired.token');
    localStorage.setItem('sp_user', JSON.stringify({ name: 'old' }));

    await expect(window.Auth.fetchMe()).rejects.toThrow('Auth check failed: 401');
    expect(localStorage.getItem('sp_token')).toBeNull();
    expect(localStorage.getItem('sp_user')).toBeNull();
  });

  it('fetchMe() 应缓存用户信息到 localStorage', async () => {
    const userData = { id: 1, name: '测试用户', role: 'student' };
    fetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ user: userData }),
    });
    localStorage.setItem('sp_token', 'valid.token');

    const result = await window.Auth.fetchMe();
    expect(result).toEqual(userData);
    expect(JSON.parse(localStorage.getItem('sp_user'))).toEqual(userData);
  });

  // ========== 角色可见性 ==========

  it('applyRoleVisibility() 应根据 data-auth-role 属性显示/隐藏元素', () => {
    document.body.innerHTML = `
      <div data-auth-role="teacher" id="teacher-only">教师内容</div>
      <div data-auth-role="student" id="student-only">学生内容</div>
      <div data-auth-role="user" id="user-content">用户内容</div>
      <div data-auth-role="guest" id="guest-content">访客内容</div>
    `;

    // 未登录状态 (guest)
    window.Auth.applyRoleVisibility();

    expect(document.getElementById('teacher-only').style.display).toBe('none');
    expect(document.getElementById('student-only').style.display).toBe('none');
    expect(document.getElementById('user-content').style.display).toBe('none');
    expect(document.getElementById('guest-content').style.display).toBe('');
  });
});
