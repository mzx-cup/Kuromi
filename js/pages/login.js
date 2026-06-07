document.addEventListener('alpine:init', () => {
  Alpine.data('loginPage', () => ({
    form: { username: '', password: '' },
    error: '',
    success: '',
    loading: false,

    async init() {
      const token = Auth.getToken();
      if (token) {
        try {
          await Auth.fetchMe();
          if (Auth.isTeacher()) { window.location.href = '/teacher-dashboard.html'; return; }
          if (Auth.isStudent()) { window.location.href = '/hub.html'; return; }
        } catch (_) { /* token expired */ }
      }
    },

    async doLogin() {
      this.error = '';
      this.success = '';
      if (!this.form.username || !this.form.password) {
        this.error = '请输入用户名和密码';
        return;
      }
      this.loading = true;
      try {
        const res = await fetch('/api/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(this.form),
        });
        const data = await res.json();
        if (data.token) {
          localStorage.setItem('sp_token', data.token);
          if (data.user) localStorage.setItem('sp_user', JSON.stringify(data.user));
          if (data.user && data.user.role === 'teacher') {
            window.location.href = '/teacher-dashboard.html';
          } else {
            window.location.href = '/hub.html';
          }
        } else {
          this.error = data.detail || '登录失败';
        }
      } catch (e) {
        this.error = '网络错误，请稍后重试';
      } finally {
        this.loading = false;
      }
    },

    /** Quick login with preset demo accounts */
    async quickLogin(role) {
      this.error = '';
      this.loading = true;
      try {
        const res = await fetch('/api/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username: role, password: '123456' }),
        });
        const data = await res.json();
        if (data.token) {
          localStorage.setItem('sp_token', data.token);
          if (data.user) localStorage.setItem('sp_user', JSON.stringify(data.user));
          if (data.user && data.user.role === 'teacher') {
            window.location.href = '/teacher-dashboard.html';
          } else {
            window.location.href = '/hub.html';
          }
        } else {
          this.error = `演示账号不可用: ${data.detail || '请先注册'}`;
        }
      } catch (e) {
        this.error = '网络错误';
      } finally {
        this.loading = false;
      }
    },
  }));
});
