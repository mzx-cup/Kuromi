document.addEventListener('alpine:init', () => {
  Alpine.data('registerPage', () => ({
    form: { username: '', password: '', confirmPassword: '', display_name: '', role: 'teacher' },
    error: '',
    success: '',
    loading: false,

    async doRegister() {
      this.error = '';
      this.success = '';
      if (!this.form.username || !this.form.password) {
        this.error = '用户名和密码不能为空';
        if (window.Toast) Toast.error('用户名和密码不能为空');
        return;
      }
      if (this.form.password.length < 6) {
        this.error = '密码至少6位';
        if (window.Toast) Toast.error('密码至少6位');
        return;
      }
      if (this.form.password !== this.form.confirmPassword) {
        this.error = '两次密码输入不一致';
        if (window.Toast) Toast.error('两次密码输入不一致');
        return;
      }
      this.loading = true;
      try {
        const res = await fetch('/api/auth/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            username: this.form.username,
            password: this.form.password,
            display_name: this.form.display_name || this.form.username,
            role: this.form.role,
          }),
        });
        const data = await res.json();
        if (data.success || data.id) {
          this.success = '注册成功！正在跳转登录...';
          setTimeout(() => { window.location.href = '/login.html'; }, 1200);
        } else {
          this.error = data.detail || '注册失败';
          if (window.Toast) Toast.error(data.detail || '注册失败');
        }
      } catch (e) {
        this.error = '网络错误，请稍后重试';
        if (window.Toast) Toast.error('网络错误，请稍后重试');
      } finally {
        this.loading = false;
      }
    },
  }));
});
