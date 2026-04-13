/* personal.js - 个人中心页面的独立 JavaScript 逻辑 */

let currentUser = JSON.parse(localStorage.getItem('starlearn_user') || 'null') || {
    name: '同学',
    avatar: 'https://api.dicebear.com/7.x/adventurer/svg?seed=starlearn&backgroundColor=b6e3f4',
    currentTask: '大数据导论'
};

let userPreferences = JSON.parse(localStorage.getItem('starlearn_preferences') || 'null') || {
    cognitiveStyle: 'pragmatic',
    difficultyPref: 'basic',
    socraticEnabled: true,
    notificationEnabled: true,
    privacyMode: false,
    reminderEnabled: false,
    reminderTime: '14:00',
    learningGoals: ['应对考试'],
    dailyGoalMinutes: 60
};

let pendingAvatarData = null;

const tasks = [
    { id: 'bigdata', name: '大数据技术', icon: 'database', color: 'blue' },
    { id: 'clang', name: 'C语言', icon: 'file-code', color: 'emerald' },
    { id: 'cpp', name: 'C++', icon: 'code-2', color: 'purple' },
    { id: 'python', name: 'Python', icon: 'terminal', color: 'amber' },
    { id: 'algorithm', name: '算法', icon: 'git-branch', color: 'red' },
    { id: 'os', name: '操作系统', icon: 'cpu', color: 'cyan' }
];

const avatarStyles = [
    'adventurer', 'avataaars', 'bottts', 'fun-emoji', 'lorelei', 'micah',
    'miniavs', 'notionists', 'open-peeps', 'personas', 'pixel-art', 'thumbs'
];

const learningGoals = [
    { id: 'exam', label: '应对考试', icon: '📝', color: 'rgba(59,130,246,0.15)', textColor: '#60a5fa' },
    { id: 'career', label: '职业发展', icon: '💼', color: 'rgba(16,185,129,0.15)', textColor: '#34d399' },
    { id: 'project', label: '项目实战', icon: '🚀', color: 'rgba(245,158,11,0.15)', textColor: '#fbbf24' },
    { id: 'interest', label: '兴趣探索', icon: '🎯', color: 'rgba(139,92,246,0.15)', textColor: '#a78bfa' },
    { id: 'competition', label: '竞赛备战', icon: '🏆', color: 'rgba(239,68,68,0.15)', textColor: '#f87171' },
    { id: 'research', label: '科研学术', icon: '🔬', color: 'rgba(6,182,212,0.15)', textColor: '#22d3ee' }
];

function init() {
    const savedTheme = localStorage.getItem('starlearn_theme') || 'ocean';
    document.documentElement.setAttribute('data-theme', savedTheme);

    document.getElementById('current-avatar').src = currentUser.avatar;
    document.getElementById('display-name').textContent = currentUser.name;
    document.getElementById('edit-name').value = currentUser.name;

    const evaluation = JSON.parse(localStorage.getItem('starlearn_evaluation') || '{}');
    document.getElementById('stat-interactions').textContent = evaluation.interactionCount || 0;
    document.getElementById('stat-tasks').textContent = Math.floor((evaluation.interactionCount || 0) / 3);
    document.getElementById('stat-time').textContent = evaluation.codePracticeTime || 0;

    renderAvatarGrid();
    renderTaskGrid();
    renderGoalTags();
    loadPreferences();

    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
}

function renderAvatarGrid() {
    const grid = document.getElementById('avatar-grid');
    if (!grid) return;

    grid.innerHTML = avatarStyles.map(style => {
        const url = `https://api.dicebear.com/7.x/${style}/svg?seed=${encodeURIComponent(currentUser.name)}&backgroundColor=b6e3f4`;
        const isSelected = currentUser.avatar.includes(style);
        return `<img src="${url}" alt="${style}" class="avatar-option ${isSelected ? 'selected' : ''}" onclick="selectAvatar('${style}', this)">`;
    }).join('');
}

function renderTaskGrid() {
    const grid = document.getElementById('task-grid');
    if (!grid) return;

    grid.innerHTML = tasks.map(task => {
        const isActive = currentUser.currentTask === task.name || (currentUser.currentTask === '大数据导论' && task.id === 'bigdata');
        return `
        <div class="task-card ${isActive ? 'active' : ''}" onclick="switchTask('${task.name}', '${task.id}')">
            <div class="task-card-icon">
                <i data-lucide="${task.icon}" class="w-5 h-5" style="color: var(--primary-light);"></i>
            </div>
            <span class="task-card-name">${task.name}</span>
            ${isActive ? '<span class="task-card-badge">当前</span>' : ''}
        </div>`;
    }).join('');

    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
}

function renderGoalTags() {
    const container = document.getElementById('goal-tags');
    if (!container) return;

    container.innerHTML = learningGoals.map(goal => {
        const isActive = userPreferences.learningGoals.includes(goal.label);
        return `<span class="goal-tag ${isActive ? 'active' : ''}" style="background: ${goal.color}; color: ${goal.textColor};" onclick="toggleGoal('${goal.label}', this)">${goal.icon} ${goal.label}</span>`;
    }).join('');
}

function toggleGoal(goalLabel, el) {
    const idx = userPreferences.learningGoals.indexOf(goalLabel);
    if (idx >= 0) {
        userPreferences.learningGoals.splice(idx, 1);
    } else {
        userPreferences.learningGoals.push(goalLabel);
    }
    renderGoalTags();
    savePreferences();
}

function updateDailyGoal(val) {
    const display = document.getElementById('daily-goal-display');
    if (display) {
        display.textContent = val + '分钟';
    }
    userPreferences.dailyGoalMinutes = parseInt(val);
    savePreferences();
}

function loadPreferences() {
    const cognitiveStyle = document.getElementById('cognitive-style');
    const difficultyPref = document.getElementById('difficulty-pref');
    const dailyGoalSlider = document.getElementById('daily-goal-slider');
    const dailyGoalDisplay = document.getElementById('daily-goal-display');

    if (cognitiveStyle) cognitiveStyle.value = userPreferences.cognitiveStyle;
    if (difficultyPref) difficultyPref.value = userPreferences.difficultyPref;
    if (dailyGoalSlider) dailyGoalSlider.value = userPreferences.dailyGoalMinutes;
    if (dailyGoalDisplay) dailyGoalDisplay.textContent = userPreferences.dailyGoalMinutes + '分钟';

    setToggleState('socratic-toggle', userPreferences.socraticEnabled);
    setToggleState('notification-toggle', userPreferences.notificationEnabled);
    setToggleState('privacy-toggle', userPreferences.privacyMode);
    setToggleState('reminder-toggle', userPreferences.reminderEnabled);

    const reminderSettings = document.getElementById('reminder-settings');
    if (reminderSettings) {
        reminderSettings.classList.toggle('hidden', !userPreferences.reminderEnabled);
    }

    document.querySelectorAll('.time-btn').forEach(btn => {
        btn.classList.toggle('active', btn.textContent === userPreferences.reminderTime);
    });
}

function toggleSwitch(el, key) {
    if (!el) return;

    el.classList.toggle('active');
    const isActive = el.classList.contains('active');

    switch (key) {
        case 'socratic':
            userPreferences.socraticEnabled = isActive;
            break;
        case 'notification':
            userPreferences.notificationEnabled = isActive;
            break;
        case 'privacy':
            userPreferences.privacyMode = isActive;
            break;
        case 'reminder':
            userPreferences.reminderEnabled = isActive;
            const reminderSettings = document.getElementById('reminder-settings');
            if (reminderSettings) {
                reminderSettings.classList.toggle('hidden', !isActive);
            }
            if (isActive) requestNotificationPermission();
            break;
    }

    savePreferences();
}

function setToggleState(id, active) {
    const el = document.getElementById(id);
    if (el) {
        el.classList.toggle('active', active);
    }
}

function setReminderTime(btn, time) {
    if (!btn) return;

    userPreferences.reminderTime = time;
    document.querySelectorAll('.time-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    savePreferences();
}

function requestNotificationPermission() {
    if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
    }
}

function selectAvatar(style, el) {
    if (!el) return;

    const url = `https://api.dicebear.com/7.x/${style}/svg?seed=${encodeURIComponent(currentUser.name)}&backgroundColor=b6e3f4`;
    currentUser.avatar = url;

    const avatarImg = document.getElementById('current-avatar');
    if (avatarImg) {
        avatarImg.src = url;
    }

    document.querySelectorAll('.avatar-option').forEach(opt => opt.classList.remove('selected'));
    el.classList.add('selected');

    saveUser();
    showToast('头像已更新');
}

function handleAvatarUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
        showToast('请选择图片文件');
        return;
    }

    if (file.size > 5 * 1024 * 1024) {
        showToast('图片大小不能超过5MB');
        return;
    }

    const reader = new FileReader();
    reader.onload = function(e) {
        pendingAvatarData = e.target.result;
        const previewImg = document.getElementById('crop-preview-img');
        if (previewImg) {
            previewImg.src = pendingAvatarData;
        }

        const modal = document.getElementById('crop-modal');
        if (modal) {
            modal.classList.remove('hidden');
            requestAnimationFrame(() => {
                requestAnimationFrame(() => {
                    modal.classList.add('visible');
                });
            });
        }

        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    };
    reader.readAsDataURL(file);
    event.target.value = '';
}

function cancelCrop() {
    const modal = document.getElementById('crop-modal');
    if (modal) {
        modal.classList.remove('visible');
    }
    setTimeout(() => {
        const m = document.getElementById('crop-modal');
        if (m) m.classList.add('hidden');
    }, 300);
    pendingAvatarData = null;
}

function confirmCrop() {
    if (!pendingAvatarData) return;

    const canvas = document.createElement('canvas');
    canvas.width = 200;
    canvas.height = 200;
    const ctx = canvas.getContext('2d');
    const img = document.getElementById('crop-preview-img');

    if (!img) return;

    const size = Math.min(img.naturalWidth, img.naturalHeight);
    const sx = (img.naturalWidth - size) / 2;
    const sy = (img.naturalHeight - size) / 2;
    ctx.drawImage(img, sx, sy, size, size, 0, 0, 200, 200);

    const croppedData = canvas.toDataURL('image/png');
    currentUser.avatar = croppedData;

    const avatarImg = document.getElementById('current-avatar');
    if (avatarImg) {
        avatarImg.src = croppedData;
    }

    saveUser();

    const modal = document.getElementById('crop-modal');
    if (modal) {
        modal.classList.remove('visible');
    }
    setTimeout(() => {
        const m = document.getElementById('crop-modal');
        if (m) m.classList.add('hidden');
    }, 300);

    pendingAvatarData = null;
    document.querySelectorAll('.avatar-option').forEach(opt => opt.classList.remove('selected'));
    showToast('头像已更新');
}

function saveName() {
    const nameInput = document.getElementById('edit-name');
    if (!nameInput) return;

    const name = nameInput.value.trim();
    if (!name) return;

    currentUser.name = name;

    const displayName = document.getElementById('display-name');
    if (displayName) {
        displayName.textContent = name;
    }

    saveUser();
    showToast('昵称已保存');
}

function switchTask(taskName, taskId) {
    currentUser.currentTask = taskName;
    saveUser();
    renderTaskGrid();
    showToast(`已切换到「${taskName}」`);
}

function savePreferences() {
    const cognitiveStyle = document.getElementById('cognitive-style');
    const difficultyPref = document.getElementById('difficulty-pref');

    if (cognitiveStyle) userPreferences.cognitiveStyle = cognitiveStyle.value;
    if (difficultyPref) userPreferences.difficultyPref = difficultyPref.value;

    localStorage.setItem('starlearn_preferences', JSON.stringify(userPreferences));
}

function saveUser() {
    localStorage.setItem('starlearn_user', JSON.stringify(currentUser));
}

function goBack() {
    window.close();
    if (!window.closed) {
        window.location.href = '/index.html';
    }
}

function clearData() {
    if (confirm('确定要清除所有学习数据吗？此操作不可恢复。')) {
        localStorage.removeItem('starlearn_evaluation');

        const statInteractions = document.getElementById('stat-interactions');
        const statTasks = document.getElementById('stat-tasks');
        const statTime = document.getElementById('stat-time');

        if (statInteractions) statInteractions.textContent = '0';
        if (statTasks) statTasks.textContent = '0';
        if (statTime) statTime.textContent = '0';

        showToast('学习数据已清除');
    }
}

function showToast(msg) {
    const existingToasts = document.querySelectorAll('.toast-message');
    existingToasts.forEach(t => t.remove());

    const toast = document.createElement('div');
    toast.className = 'toast-message';
    toast.style.cssText = `
        position: fixed;
        top: 24px;
        left: 50%;
        transform: translateX(-50%);
        padding: 12px 24px;
        border-radius: 12px;
        font-size: 14px;
        font-weight: 600;
        z-index: 9999;
        background: rgba(30,41,59,0.95);
        color: white;
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        animation: toastIn 0.3s ease-out;
    `;
    toast.textContent = msg;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.transition = 'all 0.3s ease';
        toast.style.opacity = '0';
        toast.style.transform = 'translate(-50%, -12px)';
        setTimeout(() => toast.remove(), 300);
    }, 2200);
}

function startReminderCheck() {
    setInterval(() => {
        if (!userPreferences.reminderEnabled) return;

        const now = new Date();
        const currentTime = now.getHours().toString().padStart(2, '0') + ':' + now.getMinutes().toString().padStart(2, '0');

        if (currentTime === userPreferences.reminderTime && now.getSeconds() < 2) {
            if ('Notification' in window && Notification.permission === 'granted') {
                new Notification('星识 Star-Learn 学习提醒', {
                    body: `该学习啦！今日目标：${userPreferences.dailyGoalMinutes}分钟`,
                    icon: currentUser.avatar
                });
            }
            showToast('📚 学习提醒：该学习啦！');
        }
    }, 1000);
}

document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        const modal = document.getElementById('crop-modal');
        if (modal && !modal.classList.contains('hidden')) {
            cancelCrop();
        }
    }
});

document.addEventListener('DOMContentLoaded', function() {
    init();
    startReminderCheck();
});
