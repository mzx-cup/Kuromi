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
        // 演示账号登录走 /api/auth/demo-login (需后端 ALLOW_DEMO_LOGIN=true)
        const res = await fetch(`${API_URL}/auth/demo-login?role=${encodeURIComponent(name)}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await res.json();

        if (res.status === 403) {
            alert('演示账号登录已禁用 (生产环境默认关闭)\n如需启用,设置环境变量 ALLOW_DEMO_LOGIN=true');
            return;
        }
        if (!res.ok) {
            alert(data.detail || '演示账号登录失败');
            return;
        }

        const user = {
            id: data.user.id || data.userId,
            name: data.user.display_name || data.user.username || name,
            username: data.user.username || name,
            avatar: data.user.avatar || '',
            role: data.user.role || name,
            currentTask: '大数据导论'
        };
        localStorage.setItem('starlearn_user', JSON.stringify(user));
        if (data.isDemo) {
            localStorage.setItem('starlearn_is_demo', 'true');
        }

        if (window.StarData) {
            StarData.init(user.id);
        }

        if (data.preferences && Object.keys(data.preferences).length > 0) {
            localStorage.setItem('starlearn_preferences', JSON.stringify(data.preferences));
        }
    } catch (e) {
        console.warn('演示账号登录服务端失败:', e);
        alert('无法连接服务器,请确认后端已启动且 ALLOW_DEMO_LOGIN=true');
        return;
    }
    window.location.href = '/index.html';
}

document.getElementById('login-password').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') handleLogin();
});

lucide.createIcons();
