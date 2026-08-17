document.addEventListener('alpine:init', () => {
  Alpine.data('loginPage', () => ({
    form: { username: '', password: '' },
    showPassword: false,
    error: '',
    success: '',
    loading: false,

    async init() {
      // 1) 先用本地 exp 解析 token：过期则直接清理，绝不去打后端
      if (Auth.isTokenValid && Auth.isTokenValid()) {
        try {
          await Auth.fetchMe();
          if (Auth.isTeacher()) {
            window.location.replace('/teacher-dashboard.html');
            return;
          }
          if (Auth.isStudent() || Auth.isAdmin()) {
            window.location.replace('/hub.html');
            return;
          }
        } catch (_) {
          // token 不可用 → Auth.fetchMe 内部已清理 storage，继续展示登录页
        }
      } else if (Auth.getToken()) {
        // 有 token 但本地判定已过期，立即清掉，避免后续请求带着坏 token
        Auth.logout();
      }
    },

    /** 显示/隐藏密码 */
    togglePassword() {
      this.showPassword = !this.showPassword;
    },

    async doLogin() {
      this.error = '';
      this.success = '';
      const username = (this.form.username || '').trim();
      const password = this.form.password || '';
      if (!username || !password) {
        this.error = '请输入用户名和密码';
        window.Toast && Toast.error(this.error);
        return;
      }
      this.loading = true;
      try {
        // 任何旧 token 都不应残留
        try { localStorage.removeItem('sp_token'); localStorage.removeItem('sp_user'); } catch (_) {}
        const res = await fetch('/api/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username, password }),
        });
        // 后端 404 / 500 / 代理错误等场景下，res.json() 可能因响应体不是 JSON 而抛错
        let data = null;
        try { data = await res.json(); } catch (_) { data = null; }
        if (res.ok && data && data.token) {
          Auth.setToken(data.token, data.user);
          // 注意：window.Toast 没有 success 方法，用 show(..., 'success') 或 ok()
          const greet = data.user?.display_name || data.user?.username || username;
          window.Toast && (Toast.show(`欢迎回来，${greet}`, 'success') || Toast.ok && Toast.ok(`欢迎回来，${greet}`));
          this.success = '登录成功，正在跳转...';
          // 用 replace 避免回退到登录页
          const dest = data.user?.role === 'teacher' ? '/teacher-dashboard.html' : '/hub.html';
          setTimeout(() => window.location.replace(dest), 250);
        } else {
          // 401 / 404 / 5xx 等场景：把 HTTP 状态码也带上，错误更可读
          const detail = (data && (data.detail || data.message)) || null;
          this.error = detail
            ? `${detail} (HTTP ${res.status})`
            : `登录失败 (HTTP ${res.status})`;
          window.Toast && Toast.error(this.error);
        }
      } catch (e) {
        this.error = '网络错误，请稍后重试';
        window.Toast && Toast.error(this.error);
      } finally {
        this.loading = false;
      }
    },

    /** Quick login with preset demo accounts */
    async quickLogin(role) {
      this.error = '';
      this.loading = true;
      try {
        // 同样的清理：先清掉旧 token，避免上一个用户态残留
        try { localStorage.removeItem('sp_token'); localStorage.removeItem('sp_user'); } catch (_) {}
        const res = await fetch('/api/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username: role, password: '123456' }),
        });
        let data = null;
        try { data = await res.json(); } catch (_) { data = null; }
        if (res.ok && data && data.token) {
          Auth.setToken(data.token, data.user);
          const greet = data.user?.display_name || role;
          window.Toast && (Toast.show(`已切换为「${greet}」`, 'success') || Toast.ok && Toast.ok(`已切换为「${greet}」`));
          this.success = '登录成功，正在跳转...';
          const dest = data.user?.role === 'teacher' ? '/teacher-dashboard.html' : '/hub.html';
          setTimeout(() => window.location.replace(dest), 250);
        } else {
          const detail = (data && (data.detail || data.message)) || null;
          this.error = detail
            ? `演示账号不可用：${detail} (HTTP ${res.status})`
            : `演示账号不可用 (HTTP ${res.status})`;
          window.Toast && Toast.error(this.error);
        }
      } catch (e) {
        this.error = '网络错误';
        window.Toast && Toast.error(this.error);
      } finally {
        this.loading = false;
      }
    },
  }));
});
