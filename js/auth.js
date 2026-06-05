/**
 * Auth — JWT 令牌管理
 * 从 localStorage 'sp_token' 读取 Bearer token，验证并缓存用户信息。
 * 所有 Alpine.js 页面通过 Auth 全局对象访问认证状态。
 *
 * Usage:
 *   await Auth.fetchMe();          // 验证 token 并加载用户信息到 Auth.me
 *   if (!Auth.isTeacher()) { ... } // 角色判断
 *   Auth.logout();                 // 清除 token 并跳转登录
 */
const Auth = (() => {
  const STORAGE_KEY = 'sp_token';
  const USER_KEY = 'sp_user';

  let me = null; // cached user object from /api/auth/me

  /** 从 localStorage 获取 JWT token */
  function getToken() {
    return localStorage.getItem(STORAGE_KEY);
  }

  /** 保存 token 和可选的用户信息 */
  function setToken(token, user) {
    localStorage.setItem(STORAGE_KEY, token);
    if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));
  }

  /** 清除全部认证状态 */
  function logout() {
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(USER_KEY);
    me = null;
    window.location.href = '/login.html';
  }

  /** 验证 token 并从服务端拉取最新用户信息 */
  async function fetchMe() {
    const token = getToken();
    if (!token) throw new Error('No token');

    const res = await fetch('/api/auth/me', {
      headers: { 'Authorization': `Bearer ${token}` },
    });

    if (!res.ok) {
      if (res.status === 401) {
        localStorage.removeItem(STORAGE_KEY);
        localStorage.removeItem(USER_KEY);
      }
      throw new Error(`Auth check failed: ${res.status}`);
    }

    const data = await res.json();
    me = data.user || data;
    // Also cache in localStorage for quick access
    if (me) localStorage.setItem(USER_KEY, JSON.stringify(me));
    return me;
  }

  /** 角色判断 */
  function isTeacher() {
    return me && me.role === 'teacher';
  }

  function isStudent() {
    return me && me.role === 'student';
  }

  function isAdmin() {
    return me && me.role === 'admin';
  }

  // ---- 公开 API ----
  window.Auth = {
    get me() { return me; },
    getToken,
    setToken,
    fetchMe,
    logout,
    isTeacher,
    isStudent,
    isAdmin,
  };

  return window.Auth;
})();
