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
        // 使用增强版 login-v2，一次性获取全部用户数据
        const res = await fetch(`${API_URL}/login-v2`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        const data = await res.json();

        if (!res.ok) {
            alert(data.detail || '登录失败，用户名或密码错误');
            return;
        }

        // 保存用户基本信息
        const user = {
            id: data.userId,
            name: data.nickname || data.username,
            username: data.username,
            avatar: data.avatar,
            currentTask: data.currentTask || '大数据导论'
        };
        localStorage.setItem('starlearn_user', JSON.stringify(user));

        // 使用 StarData 加载全部服务端数据到 localStorage 缓存
        if (window.StarData) {
            await StarData.loadAllFromServer(data);
        } else {
            // Fallback: 手动写入关键数据
            if (data.preferences && Object.keys(data.preferences).length > 0) {
                localStorage.setItem('starlearn_preferences', JSON.stringify(data.preferences));
            }
        }

        // 检查用户是否已完成评估
        if (!data.hasCompletedAssessment) {
            window.location.href = '/assessment.html';
        } else {
            window.location.href = '/index.html';
        }
    } catch (error) {
        alert('网络错误，请检查服务器是否启动');
    }
}

async function quickLogin(name) {
    try {
        // 游客登录走服务端，生成持久化账号
        const res = await fetch(`${API_URL}/login/guest`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await res.json();

        if (data.success) {
            const user = {
                id: data.userId,
                name: data.nickname || name,
                username: data.username,
                avatar: data.avatar,
                currentTask: data.currentTask || '大数据导论'
            };
            localStorage.setItem('starlearn_user', JSON.stringify(user));

            if (window.StarData) {
                StarData.init(data.userId);
            }

            if (data.preferences && Object.keys(data.preferences).length > 0) {
                localStorage.setItem('starlearn_preferences', JSON.stringify(data.preferences));
            }
        }
    } catch (e) {
        console.warn('游客登录服务端失败，使用纯本地模式');
        // Fallback: 纯本地游客模式
        const avatarSeed = name + Date.now();
        const user = {
            name: name,
            avatar: `https://api.dicebear.com/7.x/adventurer/svg?seed=${encodeURIComponent(avatarSeed)}&backgroundColor=b6e3f4`,
            currentTask: '大数据导论'
        };
        localStorage.setItem('starlearn_user', JSON.stringify(user));
    }
    window.location.href = '/index.html';
}

document.getElementById('login-password').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') handleLogin();
});

lucide.createIcons();
