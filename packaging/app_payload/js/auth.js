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

  /** 清除全部认证状态（与 index.js logout 保持完全一致） */
  function logout() {
    // 1) 清空内存中的 me
    me = null;
    // 2) 清除 localStorage 中所有可能残留的认证键
    const KEYS_TO_CLEAR = [
      STORAGE_KEY,     // sp_token
      USER_KEY,        // sp_user
      'starlearn_user', // index.js 用的旧键
      'auth_token',    // 旧版兼容
      'auth_user',
    ];
    KEYS_TO_CLEAR.forEach((k) => {
      try { localStorage.removeItem(k); } catch (_) {}
    });
    // 3) 清除 sessionStorage 中残留的用户态
    try {
      const sessionKeys = [];
      for (let i = 0; i < sessionStorage.length; i++) {
        const k = sessionStorage.key(i);
        if (k && (k.includes('user') || k.includes('profile') || k.includes('personal'))) {
          sessionKeys.push(k);
        }
      }
      sessionKeys.forEach((k) => sessionStorage.removeItem(k));
    } catch (_) {}
    // 4) 广播登出事件，通知仍在内存中的其他模块
    try { window.dispatchEvent(new CustomEvent('auth:logout')); } catch (_) {}
    // 5) 使用 replace 跳转，让用户无法通过「后退」回到已退出账号的页面
    window.location.replace('/login.html');
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

  /**
   * Decode a base64url / base64 string. PyJWT、Go-jwt、js-jwt 等不同实现的
   * 输出略有差异：base64url 用 `-` `_`，无 `=` padding；标准 base64
   * 可能有 `+` `/` `=`。统一做归一化，避免 atob 在部分 token 上抛错。
   */
  function decodeBase64(str) {
    if (!str) return '';
    let s = str.replace(/-/g, '+').replace(/_/g, '/');
    // 补齐 padding
    const pad = s.length % 4;
    if (pad) s += '='.repeat(4 - pad);
    try { return atob(s); } catch (_) { return ''; }
  }

  /** Decode JWT payload to check expiration. 兼容 base64 / base64url / 无 padding */
  function isTokenValid() {
    const token = getToken();
    if (!token) return false;
    try {
      const seg = token.split('.')[1];
      if (!seg) return false;
      const payload = JSON.parse(decodeBase64(seg));
      if (!payload.exp) return true;
      return Date.now() < payload.exp * 1000;
    } catch (e) {
      return false;
    }
  }

  /** Check token on load — if expiring soon, try refresh */
  function checkTokenOnLoad() {
    const token = getToken();
    if (!token) return;
    try {
      const seg = token.split('.')[1];
      if (!seg) return;
      const payload = JSON.parse(decodeBase64(seg));
      if (payload.exp && (payload.exp * 1000 - Date.now()) < 5 * 60 * 1000) {
        fetchMe().catch(function() {});
      }
    } catch (e) {}
  }

  /** Scan DOM for data-auth-role and show/hide elements */
  function applyRoleVisibility() {
    const role = me ? me.role : 'guest';
    document.querySelectorAll('[data-auth-role]').forEach(function(el) {
      const required = el.getAttribute('data-auth-role');
      if (required === 'user') {
        el.style.display = role !== 'guest' ? '' : 'none';
      } else if (required === 'guest') {
        el.style.display = role === 'guest' ? '' : 'none';
      } else {
        el.style.display = role === required ? '' : 'none';
      }
    });
  }

  // Apply role visibility after fetchMe completes
  const _originalFetchMe = fetchMe;
  fetchMe = async function() {
    const result = await _originalFetchMe();
    applyRoleVisibility();
    return result;
  };

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
    isTokenValid,
    applyRoleVisibility,
  };

  // Run on page load
  checkTokenOnLoad();
  applyRoleVisibility();

  return window.Auth;
})();
