const API_URL = `${window.location.origin}/api`;

async function handleRegister() {
    const username = document.getElementById('reg-username').value.trim();
    const password = document.getElementById('reg-password').value;
    const confirm = document.getElementById('reg-confirm').value;
    const errorEl = document.getElementById('error-msg');
    const successEl = document.getElementById('success-msg');
    const btn = document.getElementById('reg-btn');

    errorEl.classList.add('hidden');
    successEl.classList.add('hidden');

    if (!username || !password) {
        errorEl.textContent = '用户名和密码不能为空';
        errorEl.classList.remove('hidden');
        return;
    }
    if (username.length < 2 || username.length > 20) {
        errorEl.textContent = '用户名长度需在2-20个字符之间';
        errorEl.classList.remove('hidden');
        return;
    }
    if (password.length < 4) {
        errorEl.textContent = '密码长度不能少于4个字符';
        errorEl.classList.remove('hidden');
        return;
    }
    if (password !== confirm) {
        errorEl.textContent = '两次输入的密码不一致';
        errorEl.classList.remove('hidden');
        return;
    }

    btn.disabled = true;
    btn.textContent = '注册中...';

    try {
        const res = await fetch(`${API_URL}/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        const data = await res.json();

        if (!res.ok) {
            errorEl.textContent = data.detail || '注册失败';
            errorEl.classList.remove('hidden');
            btn.disabled = false;
            btn.textContent = '注 册';
            return;
        }

        successEl.textContent = '注册成功！即将进入学习状态评估...';
        successEl.classList.remove('hidden');
        btn.textContent = '注册成功';

        const user = {
            id: data.userId,
            name: data.nickname || data.username,
            username: data.username,
            avatar: data.avatar,
            currentTask: '大数据导论',
            isNewUser: true
        };
        localStorage.setItem('starlearn_user', JSON.stringify(user));

        setTimeout(() => {
            window.location.href = '/assessment.html';
        }, 1500);
    } catch (error) {
        errorEl.textContent = '网络错误，请检查服务器是否启动';
        errorEl.classList.remove('hidden');
        btn.disabled = false;
        btn.textContent = '注 册';
    }
}

document.getElementById('reg-confirm').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') handleRegister();
});

lucide.createIcons();
