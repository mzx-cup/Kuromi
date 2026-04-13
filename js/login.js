const API_URL = `${window.location.origin}/api`;

function togglePassword() {
    const input = document.getElementById('login-password');
    const icon = document.getElementById('eye-icon');
    if (input.type === 'password') {
        input.type = 'text';
        icon.setAttribute('data-lucide', 'eye-off');
    } else {
        input.type = 'password';
        icon.setAttribute('data-lucide', 'eye');
    }
    lucide.createIcons();
}

async function handleLogin() {
    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value;

    if (!username || !password) {
        alert('请输入用户名和密码');
        return;
    }

    try {
        const res = await fetch(`${API_URL}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        const data = await res.json();

        if (!res.ok) {
            alert(data.detail || '登录失败，用户名或密码错误');
            return;
        }

        const user = {
            id: data.userId,
            name: data.nickname || data.username,
            username: data.username,
            avatar: data.avatar,
            currentTask: data.currentTask || '大数据导论'
        };
        localStorage.setItem('starlearn_user', JSON.stringify(user));

        if (data.preferences && Object.keys(data.preferences).length > 0) {
            localStorage.setItem('starlearn_preferences', JSON.stringify(data.preferences));
        }

        // 检查用户是否已完成评估
        if (data.isNewUser || !data.hasCompletedAssessment) {
            window.location.href = '/assessment.html';
        } else {
            window.location.href = '/index.html';
        }
    } catch (error) {
        alert('网络错误，请检查服务器是否启动');
    }
}

function quickLogin(name) {
    const avatarSeed = name + Date.now();
    const user = {
        name: name,
        avatar: `https://api.dicebear.com/7.x/adventurer/svg?seed=${encodeURIComponent(avatarSeed)}&backgroundColor=b6e3f4`,
        currentTask: '大数据导论'
    };
    localStorage.setItem('starlearn_user', JSON.stringify(user));
    window.location.href = '/index.html';
}

document.getElementById('login-password').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') handleLogin();
});

lucide.createIcons();