/**
 * HTTP Intercept — fetch/XHR 拦截器
 * 自动为所有 API 请求附加 Bearer token，401 时跳转登录。
 * 必须在 auth.js 之后加载。
 *
 * 行为:
 *   - 对所有 /api/ 开头的请求自动注入 Authorization header
 *   - 401 响应自动清除 token 并重定向到 /login.html
 *   - 不拦截非 /api/ 的请求（CDN、静态资源等）
 */
(() => {
  const AUTH_ROUTES = ['/api/']; // 需要注入 token 的路径前缀
  const LOGIN_URL = '/login.html';
  const STORAGE_KEY = 'sp_token';

  const originalFetch = window.fetch;

  /**
   * 判断一个 URL 是否需要附加 Authorization header
   */
  function needsAuth(url) {
    if (typeof url === 'string' && AUTH_ROUTES.some(p => url.includes(p))) return true;
    if (url instanceof Request && AUTH_ROUTES.some(p => url.url.includes(p))) return true;
    return false;
  }

  /**
   * 获取当前 token
   */
  function getToken() {
    return localStorage.getItem(STORAGE_KEY);
  }

  /**
   * 401 处理: 清除 token 并重定向
   * 用 replace 跳转，避免「后退」按钮回到已退出的页面
   */
  function handle401() {
    try { localStorage.removeItem(STORAGE_KEY); } catch (_) {}
    try { localStorage.removeItem('sp_user'); } catch (_) {}
    try { localStorage.removeItem('starlearn_user'); } catch (_) {}
    try { localStorage.removeItem('auth_token'); } catch (_) {}
    try { localStorage.removeItem('auth_user'); } catch (_) {}
    try { window.dispatchEvent(new CustomEvent('auth:logout')); } catch (_) {}
    // 防止循环重定向
    if (!window.location.pathname.includes('login.html')) {
      window.location.replace(LOGIN_URL);
    }
  }

  /**
   * Monkey-patch fetch: 自动注入 Authorization header
   */
  window.fetch = async function patchedFetch(input, init = {}) {
    const token = getToken();

    if (needsAuth(input) && token) {
      init.headers = init.headers || {};
      // 如果 headers 是 Headers 对象，转成普通对象
      if (init.headers instanceof Headers) {
        const h = {};
        init.headers.forEach((v, k) => { h[k] = v; });
        init.headers = h;
      }
      // 不重复添加
      if (!init.headers['Authorization'] && !init.headers['authorization']) {
        init.headers['Authorization'] = `Bearer ${token}`;
      }
    }

    try {
      const response = await originalFetch.call(window, input, init);

      // 401 自动跳转登录
      if (response.status === 401 && needsAuth(input)) {
        handle401();
      }

      return response;
    } catch (err) {
      // 网络错误不做 401 处理，直接抛出
      throw err;
    }
  };

  /**
   * 同样拦截 XMLHttpRequest 用于 ECharts / SSE 等使用原生 XHR 的场景
   */
  const OriginalXHR = window.XMLHttpRequest;
  const OriginalOpen = OriginalXHR.prototype.open;
  const OriginalSetHeader = OriginalXHR.prototype.setRequestHeader;
  const OriginalSend = OriginalXHR.prototype.send;

  let pendingXHRToken = null;

  OriginalXHR.prototype.open = function patchedOpen(method, url, ...rest) {
    this._url = url;
    this._needsAuth = needsAuth(url);
    return OriginalOpen.call(this, method, url, ...rest);
  };

  OriginalXHR.prototype.setRequestHeader = function patchedSetHeader(name, value) {
    if (name.toLowerCase() === 'authorization') {
      pendingXHRToken = value; // already set, don't override
    }
    return OriginalSetHeader.call(this, name, value);
  };

  OriginalXHR.prototype.send = function patchedSend(...args) {
    const token = getToken();
    if (this._needsAuth && token && !pendingXHRToken) {
      try {
        OriginalSetHeader.call(this, 'Authorization', `Bearer ${token}`);
      } catch (_) {
        // XHR may be in a state where setRequestHeader is not allowed
      }
    }
    pendingXHRToken = null;

    // Listen for 401
    this.addEventListener('readystatechange', function onReady() {
      if (this.readyState === 4 && this.status === 401 && this._needsAuth) {
        handle401();
      }
    });

    return OriginalSend.apply(this, args);
  };

  console.log('[http-intercept] fetch & XHR interceptor registered');
})();
