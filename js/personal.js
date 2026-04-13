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
    reminderRepeat: [0, 1, 2, 3, 4, 5, 6],
    reminderAmPm: 'PM',
    learningGoals: ['应对考试'],
    dailyGoalMinutes: 60
};

let pendingAvatarData = null;

let floatingAlarmState = {
    isOpen: false,
    isMinimized: false,
    isDragging: false,
    dragOffset: { x: 0, y: 0 },
    position: { x: window.innerWidth - 400, y: 100 }
};

let activeReminderTimeouts = [];

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
    syncCockpitStats();
    initWaveCanvas();
    initQuantumCockpit();
    updatePetCompanion();
    loadPreferences();
    initFloatingAlarm();
    requestNotificationPermission();

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

function syncCockpitStats() {
    const evaluation = JSON.parse(localStorage.getItem('starlearn_evaluation') || '{}');
    const interactions = evaluation.interactionCount || 0;
    const minutes = evaluation.codePracticeTime || 0;
    const completed = Math.floor(interactions / 3);

    const elInteractions = document.getElementById('cockpit-interactions');
    const elMinutes = document.getElementById('cockpit-minutes');
    const elCompleted = document.getElementById('cockpit-completed');

    if (elInteractions) elInteractions.textContent = interactions;
    if (elMinutes) elMinutes.textContent = minutes;
    if (elCompleted) elCompleted.textContent = completed;
}

let quantumState = {
    thinkingDepth: 78,
    conceptMastery: 85,
    focusRestRatio: '4:1',
    learningMomentum: 88,
    restMinutes: 0,
    focusMinutes: 0,
    knowledgeNodes: [],
    chatHistory: [],
    quizResults: [],
    lastUpdate: null
};

const knowledgeKeywords = [
    { name: 'HDFS', emoji: '🐘', category: 'storage' },
    { name: 'Spark', emoji: '⚡', category: 'processing' },
    { name: 'Flink', emoji: '🌊', category: 'streaming' },
    { name: 'Data Mining', emoji: '⛏️', category: 'analysis' },
    { name: 'Vector DB', emoji: '🔢', category: 'ai' },
    { name: 'ML Pipeline', emoji: '🤖', category: 'ml' },
    { name: 'Hadoop', emoji: '🐘', category: 'storage' },
    { name: 'Kafka', emoji: '📨', category: 'messaging' },
    { name: 'Hive', emoji: '🐝', category: 'query' },
    { name: 'Zookeeper', emoji: '🦍', category: 'coordination' }
];

const aiAnalysisTemplates = [
    '你今天在 {topic} 概念上专注了 {minutes} 分钟，答题正确率 {accuracy}%，掌握度大幅提升，已自动建立新连接。',
    '检测到你在 {topic} 领域的学习热情！连续 {minutes} 分钟深度学习，认知连接稳固度提升 23%。',
    '根据近期交互分析，你在 {topic} 的理解深度达到 L{level} 级别。建议适当休息以巩固记忆。',
    '星识认知引擎监测到：{topic} 知识点已形成强关联网络。推荐进一步探索相关领域。',
    '你的学习拓扑显示 {topic} 与其他概念形成了 {count} 条新连接。继续保持！'
];

const metricDescriptions = {
    thinking: [
        '实时分析你最近的5次提问，思维深度和逻辑清晰度达到L3级。',
        '近10次对话语义分析显示，你的抽象思维指数稳步提升。',
        '思维路径可视化分析：逻辑链路清晰度 92%，建议挑战更高难度问题。'
    ],
    mastery: [
        '今日数据挖掘概念答题全对。Hadoop基础略有下降，请注意复习。',
        '答题记录显示你对流处理概念掌握较好，建议加强批处理实践。',
        '近7日答题趋势：整体正确率上升12%，但SQL优化部分需强化。'
    ],
    focus: [
        '连续专注学习HDFS 90分钟，建议休息15分钟以恢复认知资源。',
        '当前专注节律良好，已进入深度学习状态。请注意用眼休息。',
        '番茄钟数据显示你的最佳专注时段为上午9-11点。'
    ],
    momentum: [
        '综合你今日全网交互情况和目标进度（CET-4/大数据考研)，当前动能良好。',
        '学习动能指数持续攀升！已超越85%的同期学习者。',
        '根据你的学习轨迹预测，3日内可完成当前模块。建议保持节奏。'
    ]
};

function updateQuantumCockpit() {
    const evaluation = JSON.parse(localStorage.getItem('starlearn_evaluation') || '{}');
    const interactions = evaluation.interactionCount || 0;
    const minutes = evaluation.codePracticeTime || 0;
    const completed = Math.floor(interactions / 3);

    quantumState.thinkingDepth = Math.min(95, Math.max(45, 78 + Math.floor(Math.random() * 15) - 7));
    quantumState.conceptMastery = Math.min(95, Math.max(50, 85 + Math.floor(Math.random() * 10) - 5));
    quantumState.learningMomentum = Math.min(98, Math.max(40, 88 + Math.floor(Math.random() * 12) - 6));
    quantumState.focusMinutes = Math.floor(minutes * 0.8);
    quantumState.restMinutes = Math.floor(minutes * 0.2);

    const total = quantumState.focusMinutes + quantumState.restMinutes;
    const focusPercent = total > 0 ? Math.round((quantumState.focusMinutes / total) * 100) : 80;
    const restPercent = 100 - focusPercent;
    const ratio = focusPercent >= 80 ? '4:1' : focusPercent >= 60 ? '3:1' : focusPercent >= 40 ? '2:1' : '1:1';

    quantumState.focusRestRatio = ratio;

    const thinkingEl = document.getElementById('metric-thinking');
    const masteryEl = document.getElementById('metric-mastery');
    const focusEl = document.getElementById('metric-focus');
    const momentumEl = document.getElementById('metric-momentum');

    const barThinking = document.getElementById('bar-thinking');
    const barMastery = document.getElementById('bar-mastery');
    const barMomentum = document.getElementById('bar-momentum');
    const focusPortion = document.getElementById('focus-portion');
    const restPortion = document.getElementById('rest-portion');

    const descThinking = document.getElementById('metric-thinking-desc');
    const descMastery = document.getElementById('metric-mastery-desc');
    const descFocus = document.getElementById('metric-focus-desc');
    const descMomentum = document.getElementById('metric-momentum-desc');

    if (thinkingEl) {
        thinkingEl.innerHTML = `${quantumState.thinkingDepth}<span class="metric-unit">%</span>`;
    }
    if (masteryEl) {
        masteryEl.innerHTML = `${quantumState.conceptMastery}<span class="metric-unit">%</span>`;
    }
    if (focusEl) {
        focusEl.textContent = quantumState.focusRestRatio;
    }
    if (momentumEl) {
        momentumEl.innerHTML = `${quantumState.learningMomentum}<span class="metric-unit">/100</span>`;
    }

    if (barThinking) barThinking.style.width = quantumState.thinkingDepth + '%';
    if (barMastery) barMastery.style.width = quantumState.conceptMastery + '%';
    if (barMomentum) barMomentum.style.width = quantumState.learningMomentum + '%';
    if (focusPortion) focusPortion.style.width = focusPercent + '%';
    if (restPortion) restPortion.style.width = restPercent + '%';

    if (descThinking) {
        const msgs = metricDescriptions.thinking;
        descThinking.textContent = msgs[Math.floor(Math.random() * msgs.length)];
    }
    if (descMastery) {
        const msgs = metricDescriptions.mastery;
        descMastery.textContent = msgs[Math.floor(Math.random() * msgs.length)];
    }
    if (descFocus) {
        const msgs = metricDescriptions.focus;
        descFocus.textContent = msgs[Math.floor(Math.random() * msgs.length)];
    }
    if (descMomentum) {
        const msgs = metricDescriptions.momentum;
        descMomentum.textContent = msgs[Math.floor(Math.random() * msgs.length)];
    }

    updateAIAnalysis();
}

function updateAIAnalysis() {
    const now = new Date();
    const timestamp = now.toLocaleString('zh-CN', {
        month: 'numeric',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });

    const topic = knowledgeKeywords[Math.floor(Math.random() * knowledgeKeywords.length)].name;
    const minutes = Math.floor(Math.random() * 60) + 30;
    const accuracy = Math.floor(Math.random() * 30) + 70;
    const level = Math.floor(Math.random() * 3) + 3;
    const count = Math.floor(Math.random() * 5) + 3;

    const template = aiAnalysisTemplates[Math.floor(Math.random() * aiAnalysisTemplates.length)];
    const analysisText = template
        .replace('{topic}', topic)
        .replace('{minutes}', minutes)
        .replace('{accuracy}', accuracy)
        .replace('{level}', level)
        .replace('{count}', count);

    const textEl = document.getElementById('ai-analysis-text');
    const timeEl = document.getElementById('ai-analysis-timestamp');

    if (textEl) {
        textEl.classList.remove('typewriter');
        void textEl.offsetWidth;
        textEl.classList.add('typewriter');
        textEl.textContent = 'AI 分析：' + analysisText;
    }
    if (timeEl) timeEl.textContent = '🕐 ' + timestamp;
}

function initQuantumCockpit() {
    updateQuantumCockpit();
    setInterval(updateQuantumCockpit, 30000);
    setInterval(updateAIAnalysis, 15000);
}

let petState = {
    mood: 78,
    satiety: 85,
    gutHealth: 92,
    emoji: '🐱',
    name: '星宝',
    pressureLevel: 'low'
};

const petStatusMessages = {
    low: [
        '它在静静地陪你学习...',
        '蜷缩在你脚边打盹中...',
        '眼神温柔地看着你敲代码...',
        '轻轻蹭着你的椅子腿...'
    ],
    medium: [
        '它似乎有点无聊，在抓沙发...',
        '趴在地上看着你，似乎在思考人生...',
        '它在玩自己的尾巴，等待你的关注...'
    ],
    high: [
        '它蜷缩起来求摸摸，压力有点大...',
        '躲在角落里，似乎需要安慰...',
        '毛发有点炸，需要你抱抱...'
    ]
};

const petTips = [
    'Tip: 星宝今天表现很棒！建议傍晚补充一点益生菌。',
    'Tip: 它的情绪指数很高，饱食度良好，继续保持！🍖',
    'Tip: 记得定时陪它玩耍，情绪会更稳定哦~ 🧶',
    'Tip: 蛋白质摄入充足，肠道活力维持在92%的高水平！',
    'Tip: 建议每2小时起来活动一下，和星宝一起伸个懒腰~ 🐱',
    'Tip: 星宝喜欢你专注学习的样子，继续加油！💪'
];

function updatePetCompanion() {
    const evaluation = JSON.parse(localStorage.getItem('starlearn_evaluation') || '{}');
    const interactions = evaluation.interactionCount || 0;

    const recentPressure = Math.min(100, Math.floor(interactions / 5));
    petState.pressureLevel = recentPressure < 30 ? 'low' : recentPressure < 70 ? 'medium' : 'high';

    petState.mood = Math.max(40, Math.min(95, 78 + Math.floor(Math.random() * 10) - 5));
    petState.satiety = Math.max(50, Math.min(95, 85 + Math.floor(Math.random() * 8) - 4));
    petState.gutHealth = Math.max(60, Math.min(98, 92 + Math.floor(Math.random() * 6) - 3));

    const moodEl = document.querySelector('.pet-nutrition-fill.mood');
    const satietyEl = document.querySelector('.pet-nutrition-fill.satiety');
    const gutEl = document.querySelector('.pet-nutrition-fill.gut');
    const moodValueEl = document.querySelector('.pet-nutrition-item:nth-child(3) .pet-nutrition-value');
    const satietyValueEl = document.querySelector('.pet-nutrition-item:nth-child(1) .pet-nutrition-value');
    const gutValueEl = document.querySelector('.pet-nutrition-item:nth-child(2) .pet-nutrition-value');
    const statusTextEl = document.getElementById('pet-status-text');
    const tipTextEl = document.getElementById('pet-tip-text');

    if (moodEl) moodEl.style.width = petState.mood + '%';
    if (satietyEl) satietyEl.style.width = petState.satiety + '%';
    if (gutEl) gutEl.style.width = petState.gutHealth + '%';

    if (moodValueEl) moodValueEl.textContent = petState.mood + '%';
    if (satietyValueEl) satietyValueEl.textContent = petState.satiety + '%';
    if (gutValueEl) gutValueEl.textContent = petState.gutHealth + '%';

    if (statusTextEl) {
        const messages = petStatusMessages[petState.pressureLevel];
        statusTextEl.textContent = messages[Math.floor(Math.random() * messages.length)];
    }

    if (tipTextEl) {
        tipTextEl.textContent = petTips[Math.floor(Math.random() * petTips.length)];
    }
}

function initWaveCanvas() {
    const canvas = document.getElementById('wave-canvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    let animationId;
    let offset = 0;

    function resize() {
        canvas.width = canvas.offsetWidth * window.devicePixelRatio;
        canvas.height = canvas.offsetHeight * window.devicePixelRatio;
        ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    }

    function draw() {
        const width = canvas.offsetWidth;
        const height = canvas.offsetHeight;

        ctx.clearRect(0, 0, width, height);

        ctx.beginPath();
        ctx.moveTo(0, height);

        for (let x = 0; x <= width; x++) {
            const y = height / 2 + Math.sin((x + offset) * 0.03) * 15 + Math.sin((x + offset) * 0.02) * 10;
            ctx.lineTo(x, y);
        }

        ctx.lineTo(width, height);
        ctx.closePath();

        const gradient = ctx.createLinearGradient(0, 0, width, 0);
        gradient.addColorStop(0, 'rgba(59, 130, 246, 0.6)');
        gradient.addColorStop(0.5, 'rgba(139, 92, 246, 0.6)');
        gradient.addColorStop(1, 'rgba(59, 130, 246, 0.6)');
        ctx.fillStyle = gradient;
        ctx.fill();

        offset += 1;
        animationId = requestAnimationFrame(draw);
    }

    resize();
    window.addEventListener('resize', resize);
    draw();

    return () => cancelAnimationFrame(animationId);
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

    document.querySelectorAll('.time-tag').forEach(tag => {
        const timeText = tag.textContent.trim();
        if (timeText.includes(userPreferences.reminderTime)) {
            tag.classList.add('active');
        } else {
            tag.classList.remove('active');
        }
    });

    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }

    updateFloatingAlarmTrigger();
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
            if (isActive) requestNotificationPermission();
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
            if (isActive) {
                requestNotificationPermission();
                scheduleReminder();
            } else {
                cancelAllReminders();
            }
            updateFloatingAlarmTrigger();
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
    document.querySelectorAll('.time-tag').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
    savePreferences();
    scheduleReminder();
    showToast(`提醒时间已设置为 ${time}`);
}

function requestNotificationPermission() {
    if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission().then(permission => {
            if (permission === 'granted') {
                showToast('已开启通知提醒');
            }
        });
    }
}

function scheduleReminder() {
    cancelAllReminders();

    if (!userPreferences.reminderEnabled) return;

    const now = new Date();
    const [hours, minutes] = userPreferences.reminderTime.split(':').map(Number);
    let targetTime = new Date();
    targetTime.setHours(hours, minutes, 0, 0);

    if (targetTime <= now) {
        targetTime.setDate(targetTime.getDate() + 1);
    }

    const delay = targetTime.getTime() - now.getTime();

    const timeoutId = setTimeout(() => {
        triggerReminder();
        scheduleReminder();
    }, delay);

    activeReminderTimeouts.push(timeoutId);
}

function cancelAllReminders() {
    activeReminderTimeouts.forEach(id => clearTimeout(id));
    activeReminderTimeouts = [];
}

function triggerReminder() {
    if ('Notification' in window && Notification.permission === 'granted') {
        new Notification('📚 星识 Star-Learn 学习提醒', {
            body: `该学习啦！今日目标：${userPreferences.dailyGoalMinutes}分钟\n加油！坚持就是胜利！`,
            icon: currentUser.avatar,
            badge: currentUser.avatar,
            tag: 'starlearn-reminder',
            requireInteraction: true,
            silent: false
        });
    }

    if (userPreferences.notificationEnabled) {
        showNotificationToast('学习提醒', `该学习啦！今日目标：${userPreferences.dailyGoalMinutes}分钟`);
    }

    showFloatingAlarmNotification();
}

function showFloatingAlarmNotification() {
    const trigger = document.getElementById('floating-alarm-trigger');
    if (trigger) {
        trigger.classList.add('visible', 'bounce');
        setTimeout(() => {
            trigger.classList.remove('visible', 'bounce');
        }, 5000);
    }
}

function toggleAlarmPopup() {
    const trigger = document.getElementById('floating-alarm-trigger');
    const modal = document.getElementById('time-picker-modal');

    if (!trigger || !modal) return;

    trigger.classList.add('bounce');
    setTimeout(() => trigger.classList.remove('bounce'), 600);

    if (modal.classList.contains('visible')) {
        closeTimePicker();
    } else {
        openTimePicker();
    }
}

function openTimePicker() {
    const modal = document.getElementById('time-picker-modal');
    if (!modal) return;

    const hourInput = document.getElementById('picker-hour');
    const minuteInput = document.getElementById('picker-minute');
    const amBtn = document.getElementById('picker-am-btn');
    const pmBtn = document.getElementById('picker-pm-btn');

    if (hourInput && minuteInput) {
        const [hours, minutes] = userPreferences.reminderTime.split(':').map(Number);
        const isPm = hours >= 12;
        const hours12 = hours % 12 || 12;
        hourInput.value = hours12;
        minuteInput.value = minutes.toString().padStart(2, '0');

        if (amBtn && pmBtn) {
            amBtn.classList.toggle('active', !isPm);
            pmBtn.classList.toggle('active', isPm);
        }
    }

    modal.classList.remove('hidden');
    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            modal.classList.add('visible');
        });
    });

    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
}

function closeTimePicker() {
    const modal = document.getElementById('time-picker-modal');
    if (modal) {
        modal.classList.remove('visible');
        setTimeout(() => {
            const m = document.getElementById('time-picker-modal');
            if (m) m.classList.add('hidden');
        }, 300);
    }
}

function updatePickerDisplay() {
    const hourInput = document.getElementById('picker-hour');
    const minuteInput = document.getElementById('picker-minute');

    if (hourInput && minuteInput) {
        let hour = parseInt(hourInput.value) || 14;
        let minute = parseInt(minuteInput.value) || 0;

        hour = Math.max(1, Math.min(12, hour));
        minute = Math.max(0, Math.min(59, minute));

        hourInput.value = hour;
        minuteInput.value = minute.toString().padStart(2, '0');
    }
}

function setPickerAmPm(ampm) {
    const amBtn = document.getElementById('picker-am-btn');
    const pmBtn = document.getElementById('picker-pm-btn');

    if (ampm === 'AM') {
        amBtn.classList.add('active');
        pmBtn.classList.remove('active');
    } else {
        pmBtn.classList.add('active');
        amBtn.classList.remove('active');
    }
}

function setPickerQuickTime(minutes) {
    const now = new Date();
    now.setMinutes(now.getMinutes() + minutes);

    let hours = now.getHours();
    let mins = now.getMinutes();
    const ampm = hours >= 12 ? 'PM' : 'AM';
    const hours12 = hours % 12 || 12;

    const hourInput = document.getElementById('picker-hour');
    const minuteInput = document.getElementById('picker-minute');
    const amBtn = document.getElementById('picker-am-btn');
    const pmBtn = document.getElementById('picker-pm-btn');

    if (hourInput) hourInput.value = hours12;
    if (minuteInput) minuteInput.value = mins.toString().padStart(2, '0');

    if (amBtn && pmBtn) {
        if (ampm === 'AM') {
            amBtn.classList.add('active');
            pmBtn.classList.remove('active');
        } else {
            pmBtn.classList.add('active');
            amBtn.classList.remove('active');
        }
    }
}

function saveTimePicker() {
    const hourInput = document.getElementById('picker-hour');
    const minuteInput = document.getElementById('picker-minute');
    const pmBtn = document.getElementById('picker-pm-btn');

    if (hourInput && minuteInput) {
        let hour = parseInt(hourInput.value) || 14;
        let minute = parseInt(minuteInput.value) || 0;

        hour = Math.max(1, Math.min(12, hour));
        minute = Math.max(0, Math.min(59, minute));

        const isPm = pmBtn && pmBtn.classList.contains('active');
        let hours24 = hour;
        if (isPm && hour !== 12) hours24 += 12;
        if (!isPm && hour === 12) hours24 = 0;

        const timeStr = hours24.toString().padStart(2, '0') + ':' + minute.toString().padStart(2, '0');
        userPreferences.reminderTime = timeStr;

        document.querySelectorAll('.time-tag').forEach(tag => {
            tag.classList.remove('active');
        });

        userPreferences.reminderEnabled = true;
        savePreferences();
        scheduleReminder();
        updateFloatingAlarmTrigger();
        updateTimeTagActiveState();

        closeTimePicker();
        showToast(`提醒已设置为 ${timeStr}`);
    }
}

function updateTimeTagActiveState() {
    document.querySelectorAll('.time-tag').forEach(tag => {
        const time = tag.getAttribute('data-time') || tag.textContent.trim();
        if (time.includes(userPreferences.reminderTime)) {
            tag.classList.add('active');
        } else {
            tag.classList.remove('active');
        }
    });
}

function showNotificationToast(title, message) {
    const existing = document.querySelector('.notification-toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = 'notification-toast';
    toast.innerHTML = `
        <div class="notification-toast-icon">
            <i data-lucide="bell-ring"></i>
        </div>
        <div class="notification-toast-content">
            <div class="notification-toast-title">${title}</div>
            <div class="notification-toast-message">${message}</div>
        </div>
        <button class="notification-toast-close" onclick="this.parentElement.remove()">
            <i data-lucide="x"></i>
        </button>
    `;
    document.body.appendChild(toast);

    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            toast.classList.add('visible');
        });
    });

    setTimeout(() => {
        toast.classList.remove('visible');
        setTimeout(() => toast.remove(), 400);
    }, 5000);
}

function initFloatingAlarm() {
    const header = document.getElementById('floating-alarm-header');
    if (!header) return;

    header.addEventListener('mousedown', startDrag);
    document.addEventListener('mousemove', drag);
    document.addEventListener('mouseup', stopDrag);

    header.addEventListener('touchstart', handleTouchStart, { passive: false });
    document.addEventListener('touchmove', handleTouchMove, { passive: false });
    document.addEventListener('touchend', stopDrag);

    loadFloatingAlarmPosition();
    updateFloatingAlarmDisplay();
    updateFloatingAlarmTrigger();
}

function startDrag(e) {
    if (e.target.closest('.floating-alarm-controls')) return;

    floatingAlarmState.isDragging = true;
    const alarm = document.getElementById('floating-alarm');
    const rect = alarm.getBoundingClientRect();
    floatingAlarmState.dragOffset = {
        x: e.clientX - rect.left,
        y: e.clientY - rect.top
    };
    alarm.classList.add('dragging');
}

function drag(e) {
    if (!floatingAlarmState.isDragging) return;

    const alarm = document.getElementById('floating-alarm');
    const x = e.clientX - floatingAlarmState.dragOffset.x;
    const y = e.clientY - floatingAlarmState.dragOffset.y;

    alarm.style.left = Math.max(0, Math.min(x, window.innerWidth - alarm.offsetWidth)) + 'px';
    alarm.style.top = Math.max(0, Math.min(y, window.innerHeight - alarm.offsetHeight)) + 'px';
    alarm.style.right = 'auto';
    alarm.style.bottom = 'auto';
}

function stopDrag() {
    if (!floatingAlarmState.isDragging) return;

    floatingAlarmState.isDragging = false;
    const alarm = document.getElementById('floating-alarm');
    if (alarm) {
        alarm.classList.remove('dragging');
        saveFloatingAlarmPosition();
    }
}

function handleTouchStart(e) {
    if (e.target.closest('.floating-alarm-controls')) return;

    e.preventDefault();
    const touch = e.touches[0];
    floatingAlarmState.isDragging = true;
    const alarm = document.getElementById('floating-alarm');
    const rect = alarm.getBoundingClientRect();
    floatingAlarmState.dragOffset = {
        x: touch.clientX - rect.left,
        y: touch.clientY - rect.top
    };
    alarm.classList.add('dragging');
}

function handleTouchMove(e) {
    if (!floatingAlarmState.isDragging) return;

    e.preventDefault();
    const touch = e.touches[0];
    const alarm = document.getElementById('floating-alarm');
    const x = touch.clientX - floatingAlarmState.dragOffset.x;
    const y = touch.clientY - floatingAlarmState.dragOffset.y;

    alarm.style.left = Math.max(0, Math.min(x, window.innerWidth - alarm.offsetWidth)) + 'px';
    alarm.style.top = Math.max(0, Math.min(y, window.innerHeight - alarm.offsetHeight)) + 'px';
    alarm.style.right = 'auto';
    alarm.style.bottom = 'auto';
}

function loadFloatingAlarmPosition() {
    const saved = localStorage.getItem('floatingAlarmPosition');
    if (saved) {
        const pos = JSON.parse(saved);
        floatingAlarmState.position = pos;
        const alarm = document.getElementById('floating-alarm');
        if (alarm) {
            alarm.style.left = pos.x + 'px';
            alarm.style.top = pos.y + 'px';
            alarm.style.right = 'auto';
            alarm.style.bottom = 'auto';
        }
    }
}

function saveFloatingAlarmPosition() {
    const alarm = document.getElementById('floating-alarm');
    if (alarm) {
        floatingAlarmState.position = {
            x: alarm.offsetLeft,
            y: alarm.offsetTop
        };
        localStorage.setItem('floatingAlarmPosition', JSON.stringify(floatingAlarmState.position));
    }
}

function openFloatingAlarm() {
    const alarm = document.getElementById('floating-alarm');
    if (!alarm) return;

    updateFloatingAlarmDisplay();
    alarm.classList.add('visible');
    alarm.classList.remove('minimized');
    floatingAlarmState.isOpen = true;

    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
}

function closeFloatingAlarm() {
    const alarm = document.getElementById('floating-alarm');
    if (alarm) {
        alarm.classList.remove('visible');
        floatingAlarmState.isOpen = false;
    }
}

function toggleMinimizeAlarm() {
    const alarm = document.getElementById('floating-alarm');
    if (!alarm) return;

    floatingAlarmState.isMinimized = !floatingAlarmState.isMinimized;
    alarm.classList.toggle('minimized', floatingAlarmState.isMinimized);

    const minimizeBtn = alarm.querySelector('.floating-alarm-btn.minimize');
    const maximizeBtn = alarm.querySelector('.floating-alarm-btn.maximize');
    if (minimizeBtn) minimizeBtn.classList.toggle('hidden', floatingAlarmState.isMinimized);
    if (maximizeBtn) maximizeBtn.classList.toggle('hidden', !floatingAlarmState.isMinimized);
}

function updateFloatingAlarmDisplay() {
    const hourInput = document.getElementById('alarm-hour');
    const minuteInput = document.getElementById('alarm-minute');
    const miniDisplay = document.getElementById('floating-alarm-time-mini-display');

    if (hourInput && minuteInput) {
        hourInput.value = userPreferences.reminderTime.split(':')[0];
        minuteInput.value = userPreferences.reminderTime.split(':')[1];
    }

    if (miniDisplay) {
        miniDisplay.textContent = userPreferences.reminderTime;
    }

    const amBtn = document.getElementById('alarm-am-btn');
    const pmBtn = document.getElementById('alarm-pm-btn');
    if (amBtn && pmBtn) {
        const isPm = userPreferences.reminderAmPm === 'PM';
        amBtn.classList.toggle('active', !isPm);
        pmBtn.classList.toggle('active', isPm);
    }

    document.querySelectorAll('.floating-alarm-repeat-btn').forEach(btn => {
        const day = parseInt(btn.dataset.day);
        btn.classList.toggle('active', userPreferences.reminderRepeat.includes(day));
    });
}

function updateAlarmDisplay() {
    const hourInput = document.getElementById('alarm-hour');
    const minuteInput = document.getElementById('alarm-minute');
    const miniDisplay = document.getElementById('floating-alarm-time-mini-display');

    if (hourInput && minuteInput) {
        let hour = parseInt(hourInput.value) || 14;
        let minute = parseInt(minuteInput.value) || 0;

        hour = Math.max(1, Math.min(12, hour));
        minute = Math.max(0, Math.min(59, minute));

        hourInput.value = hour;
        minuteInput.value = minute.toString().padStart(2, '0');

        const isPm = document.getElementById('alarm-pm-btn').classList.contains('active');
        let hours24 = hour;
        if (isPm && hour !== 12) hours24 += 12;
        if (!isPm && hour === 12) hours24 = 0;

        const timeStr = hours24.toString().padStart(2, '0') + ':' + minute.toString().padStart(2, '0');
        userPreferences.reminderTime = timeStr;

        if (miniDisplay) {
            miniDisplay.textContent = timeStr;
        }
    }
}

function setAlarmAmPm(ampm) {
    const amBtn = document.getElementById('alarm-am-btn');
    const pmBtn = document.getElementById('alarm-pm-btn');

    if (ampm === 'AM') {
        amBtn.classList.add('active');
        pmBtn.classList.remove('active');
    } else {
        pmBtn.classList.add('active');
        amBtn.classList.remove('active');
    }

    userPreferences.reminderAmPm = ampm;
    updateAlarmDisplay();
}

function setQuickTime(minutes) {
    const now = new Date();
    now.setMinutes(now.getMinutes() + minutes);

    let hours = now.getHours();
    let mins = now.getMinutes();
    const ampm = hours >= 12 ? 'PM' : 'AM';
    const hours12 = hours % 12 || 12;

    const hourInput = document.getElementById('alarm-hour');
    const minuteInput = document.getElementById('alarm-minute');
    const amBtn = document.getElementById('alarm-am-btn');
    const pmBtn = document.getElementById('alarm-pm-btn');

    if (hourInput) hourInput.value = hours12;
    if (minuteInput) minuteInput.value = mins.toString().padStart(2, '0');

    if (ampm === 'AM') {
        amBtn.classList.add('active');
        pmBtn.classList.remove('active');
    } else {
        pmBtn.classList.add('active');
        amBtn.classList.remove('active');
    }

    userPreferences.reminderAmPm = ampm;

    let hours24 = hours;
    if (ampm === 'PM' && hours12 !== 12) hours24 += 12;
    if (ampm === 'AM' && hours12 === 12) hours24 = 0;

    userPreferences.reminderTime = hours24.toString().padStart(2, '0') + ':' + mins.toString().padStart(2, '0');

    const miniDisplay = document.getElementById('floating-alarm-time-mini-display');
    if (miniDisplay) {
        miniDisplay.textContent = userPreferences.reminderTime;
    }
}

function toggleDay(btn, day) {
    btn.classList.toggle('active');

    if (userPreferences.reminderRepeat.includes(day)) {
        userPreferences.reminderRepeat = userPreferences.reminderRepeat.filter(d => d !== day);
    } else {
        userPreferences.reminderRepeat.push(day);
        userPreferences.reminderRepeat.sort((a, b) => a - b);
    }
}

function saveFloatingAlarm() {
    updateAlarmDisplay();
    userPreferences.reminderEnabled = true;
    userPreferences.reminderRepeat = userPreferences.reminderRepeat.length > 0 ? userPreferences.reminderRepeat : [0, 1, 2, 3, 4, 5, 6];

    savePreferences();
    scheduleReminder();
    updateFloatingAlarmTrigger();

    const reminderToggle = document.getElementById('reminder-toggle');
    if (reminderToggle) {
        reminderToggle.classList.add('active');
    }

    closeFloatingAlarm();
    showToast(`提醒已设置为 ${userPreferences.reminderTime}`);
}

function updateFloatingAlarmTrigger() {
    const trigger = document.getElementById('floating-alarm-trigger');
    if (!trigger) return;

    if (userPreferences.reminderEnabled) {
        trigger.classList.add('visible');
    } else {
        trigger.classList.remove('visible');
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

document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        const modal = document.getElementById('crop-modal');
        if (modal && !modal.classList.contains('hidden')) {
            cancelCrop();
        }
        if (floatingAlarmState.isOpen) {
            closeFloatingAlarm();
        }
    }
});

document.addEventListener('DOMContentLoaded', function() {
    init();
});

document.addEventListener('visibilitychange', function() {
    if (document.visibilityState === 'visible') {
        if (userPreferences.reminderEnabled) {
            scheduleReminder();
        }
    }
});