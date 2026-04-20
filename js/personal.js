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
    dailyGoalMinutes: 60,
    debateModeEnabled: false
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
    initPetSystem();
    loadPreferences();
    initFloatingAlarm();
    requestNotificationPermission();

    // 初始化云端林场同步
    initEcoPlantSync();

    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
}

// 云端林场数据同步
function initEcoPlantSync() {
    updateEcoPlantDisplay();
    // 每秒更新倒计时
    setInterval(() => {
        updateEcoPlantTimer();
    }, 1000);
    // 每5秒完整同步一次数据
    setInterval(() => {
        updateEcoPlantDisplay();
    }, 5000);
}

// 更新倒计时显示
function updateEcoPlantTimer() {
    const timerValue = document.getElementById('eco-timer-value');
    if (!timerValue) return;

    const rawPlant = JSON.parse(localStorage.getItem('starlearn_plants') || '{}');
    const slots = rawPlant.slots || [];
    const selected = slots[personalSelectedPlantSlot] || slots.find(s => s.plantId) || slots[0];

    if (!selected || !selected.plantId) {
        timerValue.textContent = '--:--:--';
        return;
    }

    if (selected.stage >= 3) {
        timerValue.textContent = '可收获!';
        timerValue.style.color = '#34d399';
        return;
    }

    const hours = Math.floor(selected.remainingTime / 3600);
    const mins = Math.floor((selected.remainingTime % 3600) / 60);
    const secs = Math.floor(selected.remainingTime % 60);
    timerValue.textContent = `${String(hours).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    timerValue.style.color = selected.remainingTime < 300 ? '#f87171' : '#10b981';
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
    emoji: '🐱',
    name: '星宝',
    satiety: 80,
    mood: 70,
    intimacy: 50,
    lastInteraction: Date.now(),
    pressureLevel: 'low'
};

// 个人中心当前选中的植物槽位（缩略视图）
let personalSelectedPlantSlot = 0;

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

const petTips = {
    normal: [
        'Tip: 星宝今天表现很棒！继续保持这份专注~',
        'Tip: 它的情绪指数很高，饱食度良好，继续保持！🍖',
        'Tip: 记得定时陪它玩耍，情绪会更稳定哦~ 🧶',
        'Tip: 建议每2小时起来活动一下，和星宝一起伸个懒腰~ 🐱',
        'Tip: 星宝喜欢你专注学习的样子，继续加油！💪'
    ],
    hungry: [
        'Tip: It seems your Star-Friend is getting a bit hungry. Consider a quick snack!',
        'Tip: 星宝的饱食度有点低啦，该给它喂食了~ 🍖',
        'Tip: 长时间学习后，记得也关心一下星宝的饱腹感哦~'
    ],
    stressed: [
        'Tip: 检测到学习压力较大，星宝也有点低落，陪它玩耍一下吧~ 🎾',
        'Tip: 休息一下吧，星宝看到你累了，它也会担心的~ 💖'
    ]
};

let selectedPetEmoji = null;

function initPetSystem() {
    const savedPet = localStorage.getItem('starlearn_pet');
    if (savedPet) {
        petState = JSON.parse(savedPet);
        applyPetDecay();
        updatePetUI();
        startPetDecayTimer();
    } else {
        showPetSelectionModal();
    }
}

function showPetSelectionModal() {
    const modal = document.getElementById('pet-selection-modal');
    if (modal) {
        modal.classList.remove('hidden');
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                modal.classList.add('visible');
            });
        });
    }
}

function hidePetSelectionModal() {
    const modal = document.getElementById('pet-selection-modal');
    if (modal) {
        modal.classList.remove('visible');
        setTimeout(() => {
            modal.classList.add('hidden');
        }, 300);
    }
}

function selectPetOption(el) {
    document.querySelectorAll('.pet-option').forEach(opt => opt.classList.remove('selected'));
    el.classList.add('selected');
    selectedPetEmoji = el.dataset.pet;
}

function confirmPetSelection() {
    if (!selectedPetEmoji) {
        showToast('请先选择一只星友~');
        return;
    }
    petState.emoji = selectedPetEmoji;
    petState.lastInteraction = Date.now();
    savePetState();
    hidePetSelectionModal();
    updatePetUI();
    startPetDecayTimer();
    showToast(`恭喜！你的星友 ${selectedPetEmoji} 已加入！`);
}

function savePetState() {
    localStorage.setItem('starlearn_pet', JSON.stringify(petState));
}

function applyPetDecay() {
    const now = Date.now();
    const elapsed = now - petState.lastInteraction;
    const hoursPassed = elapsed / (1000 * 60 * 60);

    if (hoursPassed >= 1) {
        const decayUnits = Math.floor(hoursPassed);
        petState.satiety = Math.max(0, petState.satiety - (decayUnits * 5));

        if (petState.satiety < 20) {
            petState.mood = Math.max(0, petState.mood - (decayUnits * 10));
            petState.intimacy = Math.max(0, petState.intimacy - (decayUnits * 5));
        }

        petState.lastInteraction = now;
        savePetState();
    }
}

function startPetDecayTimer() {
    setInterval(() => {
        applyPetDecay();
        updatePetUI();
    }, 60000);
}

function petAction(action) {
    const avatar = document.getElementById('eco-pet-avatar');
    const avatarWrapper = document.getElementById('eco-pet-avatar-wrapper');
    if (!avatar) return;

    avatar.classList.remove('feed-animation', 'play-animation', 'heartbeat-animation');
    void avatar.offsetWidth;

    let tipText = '';
    switch (action) {
        case 'feed':
            petState.satiety = Math.min(100, Math.max(0, petState.satiety + 10));
            avatar.classList.add('feed-animation');
            tipText = '+10 饱食度';
            break;
        case 'play':
            petState.mood = Math.min(100, Math.max(0, petState.mood + 15));
            avatar.classList.add('play-animation');
            tipText = '+15 情绪';
            break;
        case 'pet':
            petState.intimacy = Math.min(100, Math.max(0, petState.intimacy + 10));
            avatar.classList.add('heartbeat-animation');
            tipText = '+10 亲密度';
            break;
    }

    petState.lastInteraction = Date.now();
    savePetState();
    updatePetUI();
    showFloatTip('eco-pet-tip', tipText);

    setTimeout(() => {
        avatar.classList.remove('feed-animation', 'play-animation', 'heartbeat-animation');
    }, 1000);
}

function showFloatTip(tipId, text) {
    const tip = document.getElementById(tipId);
    if (!tip) return;
    tip.textContent = text;
    tip.classList.remove('show');
    void tip.offsetWidth;
    tip.classList.add('show');
    setTimeout(() => {
        tip.classList.remove('show');
    }, 2000);
}

function updatePetUI() {
    const avatar = document.getElementById('pet-avatar-display');
    const nameEl = document.getElementById('pet-name-display');
    const satietyValue = document.getElementById('pet-satiety-value');
    const satietyBar = document.getElementById('pet-satiety-bar');
    const moodValue = document.getElementById('pet-mood-value');
    const moodBar = document.getElementById('pet-mood-bar');
    const intimacyValue = document.getElementById('pet-intimacy-value');
    const intimacyBar = document.getElementById('pet-intimacy-bar');
    const statusText = document.getElementById('pet-status-text');
    const tipText = document.getElementById('pet-tip-text');

    if (avatar) avatar.textContent = petState.emoji;
    if (nameEl) nameEl.textContent = petState.name;

    if (satietyValue) satietyValue.textContent = petState.satiety + '%';
    if (satietyBar) satietyBar.style.width = petState.satiety + '%';
    if (moodValue) moodValue.textContent = petState.mood + '%';
    if (moodBar) moodBar.style.width = petState.mood + '%';
    if (intimacyValue) intimacyValue.textContent = petState.intimacy + '%';
    if (intimacyBar) intimacyBar.style.width = petState.intimacy + '%';

    const ecoAvatar = document.getElementById('eco-pet-avatar');
    const ecoName = document.getElementById('eco-pet-name');
    const ecoStatus = document.getElementById('eco-pet-status');
    const ecoSatietyValue = document.getElementById('eco-satiety-value');
    const ecoSatietyBar = document.getElementById('eco-satiety-bar');
    const ecoMoodValue = document.getElementById('eco-mood-value');
    const ecoMoodBar = document.getElementById('eco-mood-bar');
    const ecoIntimacyValue = document.getElementById('eco-intimacy-value');
    const ecoIntimacyBar = document.getElementById('eco-intimacy-bar');

    if (ecoAvatar) ecoAvatar.textContent = petState.emoji;
    if (ecoName) ecoName.textContent = petState.name;
    if (ecoSatietyValue) ecoSatietyValue.textContent = petState.satiety + '%';
    if (ecoSatietyBar) ecoSatietyBar.style.width = petState.satiety + '%';
    if (ecoMoodValue) ecoMoodValue.textContent = petState.mood + '%';
    if (ecoMoodBar) ecoMoodBar.style.width = petState.mood + '%';
    if (ecoIntimacyValue) ecoIntimacyValue.textContent = petState.intimacy + '%';
    if (ecoIntimacyBar) ecoIntimacyBar.style.width = petState.intimacy + '%';
    if (ecoStatus) ecoStatus.textContent = statusText ? statusText.textContent : '';

    const evaluation = JSON.parse(localStorage.getItem('starlearn_evaluation') || '{}');
    const interactions = evaluation.interactionCount || 0;
    const recentPressure = Math.min(100, Math.floor(interactions / 5));
    petState.pressureLevel = recentPressure < 30 ? 'low' : recentPressure < 70 ? 'medium' : 'high';

    if (statusText) {
        const messages = petStatusMessages[petState.pressureLevel];
        statusText.textContent = messages[Math.floor(Math.random() * messages.length)];
    }

    if (tipText) {
        let tips;
        if (petState.satiety < 20) {
            tips = petTips.hungry;
        } else if (petState.pressureLevel === 'high') {
            tips = petTips.stressed;
        } else {
            tips = petTips.normal;
        }
        tipText.textContent = tips[Math.floor(Math.random() * tips.length)];
    }

    updateEcoPlantDisplay();
}

function updatePetCompanion() {
    updatePetUI();
}

function updateEcoPlantDisplay() {
    const plantEmoji = document.getElementById('eco-plant-emoji');
    const plantName = document.getElementById('eco-plant-name');
    const plantStage = document.getElementById('eco-plant-stage');
    const timerValue = document.getElementById('eco-timer-value');
    const waterValue = document.getElementById('eco-water-value');
    const waterBar = document.getElementById('eco-water-bar');
    const nutrientValue = document.getElementById('eco-nutrient-value');
    const nutrientBar = document.getElementById('eco-nutrient-bar');
    const lightValue = document.getElementById('eco-light-value');
    const lightBar = document.getElementById('eco-light-bar');
    const growthValue = document.getElementById('eco-growth-value');
    const growthBar = document.getElementById('eco-growth-bar');
    const harvestCount = document.getElementById('eco-harvest-count');
    const slotsContainer = document.getElementById('eco-plant-slots');
    const plantDisplayWrapper = document.getElementById('eco-plant-display');

    const rawPlant = JSON.parse(localStorage.getItem('starlearn_plants') || '{}');
    const slots = rawPlant.slots || [];
    const seeds = parseInt(localStorage.getItem('starlearn_seeds') || '0');

    const PLANT_SLOTS = 3; // 保持与种植页面一致
    // 填充默认槽位
    while (slots.length < PLANT_SLOTS) slots.push({ plantId: null, stage: 0, remainingTime: 0, water: 0, nutrient: 0, lastUpdate: Date.now() });

    // 本地图鉴数据
    const PLANT_DATA = [
        { id: 'bamboo', name: '逻辑之竹', emoji: '🎋', stages: ['🌰', '🌱', '🎋', '🎍'] },
        { id: 'vine', name: '算法之藤', emoji: '🌿', stages: ['🌰', '🌱', '🌿', '🍃'] },
        { id: 'sunflower', name: '数据向日葵', emoji: '🌻', stages: ['🌰', '🌱', '🌻', '🌻'] },
        { id: 'cactus', name: '极客仙人掌', emoji: '🌵', stages: ['🌰', '🌱', '🌵', '🏜️'] },
        { id: 'rose', name: '星空玫瑰', emoji: '🌹', stages: ['🌹', '🌷', '🌹', '💐'] },
        { id: 'tree', name: '智慧之树', emoji: '🌳', stages: ['🌱', '🌿', '🌳', '🌲'] },
        { id: 'lotus', name: '架构莲花', emoji: '🪷', stages: ['🪷', '🪷', '🪷', '✨'] },
        { id: 'mushroom', name: '敏捷蘑菇', emoji: '🍄', stages: ['🍄', '🍄', '🍄', '🌟'] },
        { id: 'flower', name: '创新之花', emoji: '🌸', stages: ['🌸', '🌺', '🌸', '💮'] },
        { id: 'palm', name: '运维棕榈', emoji: '🌴', stages: ['🌴', '🌴', '🌴', '🏝️'] }
    ];
    const STAGE_NAMES = ['种子 Seed', '萌芽 Sprout', '成长期 Growth', '成熟 Harvest'];

    // 渲染槽位缩略图
    if (slotsContainer) {
        slotsContainer.innerHTML = '';
        slots.forEach((slot, i) => {
            const plant = slot.plantId ? PLANT_DATA.find(p => p.id === slot.plantId) : null;
            const emoji = plant ? plant.stages[slot.stage] : '🌱';
            const cls = slot.plantId ? 'occupied' : 'empty';
            const selectedClass = i === personalSelectedPlantSlot ? ' selected' : '';
            const html = `
                <div class="eco-plant-slot ${cls}${selectedClass}" data-slot="${i}" onclick="selectEcoSlot(${i})" title="槽位 ${i+1}">
                    <div class="slot-emoji">${emoji}</div>
                    ${slot.plantId && slot.stage >= 3 ? '<div class="slot-ready-badge">!</div>' : ''}
                </div>
            `;
            slotsContainer.insertAdjacentHTML('beforeend', html);
        });
    }

    // 选中的槽位显示详情（优先读取选中槽；若为空则显示占位）
    const selected = slots[personalSelectedPlantSlot] || slots.find(s => s.plantId) || slots[0];
    if (!selected || !selected.plantId) {
        if (plantEmoji) plantEmoji.textContent = '🌱';
        if (plantName) plantName.textContent = '选择你的植物';
        if (plantStage) plantStage.textContent = '待种植';
        if (timerValue) timerValue.textContent = '--:--:--';
        if (plantDisplayWrapper) plantDisplayWrapper.classList.add('empty');
    } else {
        const plant = PLANT_DATA.find(p => p.id === selected.plantId);
        if (plantDisplayWrapper) plantDisplayWrapper.classList.remove('empty');
        if (plant) {
            if (plantEmoji) plantEmoji.textContent = plant.stages[selected.stage];
            if (plantName) plantName.textContent = plant.name;
            if (plantStage) plantStage.textContent = STAGE_NAMES[selected.stage];
        }

        if (selected.stage >= 3) {
            if (timerValue) { timerValue.textContent = '可收获!'; timerValue.style.color = '#34d399'; }
        } else {
            const hours = Math.floor(selected.remainingTime / 3600);
            const mins = Math.floor((selected.remainingTime % 3600) / 60);
            const secs = Math.floor(selected.remainingTime % 60);
            if (timerValue) timerValue.textContent = `${String(hours).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
            if (timerValue) timerValue.style.color = selected.remainingTime < 300 ? '#f87171' : '#10b981';
        }

        if (waterValue) waterValue.textContent = Math.round(selected.water || 0) + '%';
        if (waterBar) waterBar.style.width = (selected.water || 0) + '%';
        if (nutrientValue) nutrientValue.textContent = Math.round(selected.nutrient || 0) + '%';
        if (nutrientBar) nutrientBar.style.width = (selected.nutrient || 0) + '%';
        if (lightValue) lightValue.textContent = Math.round(selected.light || 50) + '%';
        if (lightBar) lightBar.style.width = (selected.light || 50) + '%';
        if (growthValue) growthValue.textContent = Math.round(selected.growth || 0) + '%';
        if (growthBar) growthBar.style.width = (selected.growth || 0) + '%';
    }

    if (harvestCount) harvestCount.textContent = (rawPlant.ownedPlants && rawPlant.ownedPlants.length) || 0;
}

// 在个人页面点击槽位以切换查看
function selectEcoSlot(idx) {
    personalSelectedPlantSlot = idx;
    updateEcoPlantDisplay();
    showFloatTip('eco-plant-tip', `已切换到槽位 ${idx+1}`);
}

// 简单收集粒子效果（小规模）
function createMiniParticles(targetEl) {
    if (!targetEl) return;
    for (let i = 0; i < 10; i++) {
        const p = document.createElement('div');
        p.className = 'mini-particle';
        p.textContent = ['✨','🌟','💫','🍃'][Math.floor(Math.random()*4)];
        p.style.left = (30 + Math.random()*40) + '%';
        p.style.top = (10 + Math.random()*60) + '%';
        targetEl.appendChild(p);
        setTimeout(() => p.remove(), 1200);
    }
}

function ecoPlantAction(action) {
    const plantStateData = JSON.parse(localStorage.getItem('starlearn_plants') || '{}');
    const slots = plantStateData.slots || [];
    const PLANT_SLOTS = 3;

    // 确保 slots 数量
    while (slots.length < PLANT_SLOTS) slots.push({ plantId: null, stage: 0, remainingTime: 0, water: 0, nutrient: 0, lastUpdate: Date.now() });

    // 选中的槽位或第一个有植物的槽
    let idx = personalSelectedPlantSlot;
    if (!slots[idx] || !slots[idx].plantId) {
        idx = slots.findIndex(s => s && s.plantId);
        if (idx === -1) { showToast('请先在林场种植一株植物~'); return; }
    }

    const slot = slots[idx];
    const WATER_TIME_REDUCTION = 10 * 60;
    const NUTRIENT_TIME_REDUCTION = 30 * 60;

    let tipText = '';
    if (action === 'water') {
        slot.water = Math.min(100, Math.max(0, (slot.water || 0) + 20));
        slot.remainingTime = Math.max(0, (slot.remainingTime || 0) - WATER_TIME_REDUCTION);
        tipText = '+20💧';
        showToast('💧 浇水成功！生长时间缩短10分钟~');
        // 水波动效
        const slotEl = document.querySelector(`#eco-plant-slots .eco-plant-slot[data-slot='${idx}']`);
        if (slotEl) {
            slotEl.classList.remove('mini-water-ripple'); void slotEl.offsetWidth; slotEl.classList.add('mini-water-ripple');
            createMiniParticles(slotEl);
        }
    } else if (action === 'nutrient') {
        slot.nutrient = Math.min(100, Math.max(0, (slot.nutrient || 0) + 15));
        slot.remainingTime = Math.max(0, (slot.remainingTime || 0) - NUTRIENT_TIME_REDUCTION);
        tipText = '+15🧪';
        showToast('🧪 施肥成功！生长时间缩短30分钟~');
        const slotEl = document.querySelector(`#eco-plant-slots .eco-plant-slot[data-slot='${idx}']`);
        if (slotEl) { createMiniParticles(slotEl); }
    }

    slot.lastUpdate = Date.now();
    plantStateData.slots = slots;
    plantStateData.lastUpdate = Date.now();
    try { localStorage.setItem('starlearn_plants', JSON.stringify(plantStateData)); } catch (e) {}

    // 保存 eco_data 快照
    const ecoData = {
        lastWater: slot.water,
        lastNutrient: slot.nutrient,
        lastLight: slot.light || 50,
        lastGrowth: slot.growth || 0,
        lastUpdate: Date.now()
    };
    localStorage.setItem('eco_data', JSON.stringify(ecoData));

    // 广播自定义事件，通知植物页面（如有打开）
    window.dispatchEvent(new CustomEvent('plantStateUpdated', { detail: plantStateData }));

    updateEcoPlantDisplay();
    showFloatTip('eco-plant-tip', tipText);
}

function goToPlantFarm() {
    window.location.href = '/plant.html';
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
    setToggleState('debate-toggle', userPreferences.debateModeEnabled);

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

// 当其它页面（例如宠物游戏页）更新了 starlearn_pet，本页也同步显示头像/状态
window.addEventListener('storage', (e) => {
  try {
    if (e.key === 'starlearn_pet') {
      const newPet = JSON.parse(e.newValue);
      if (newPet) {
        petState = { ...petState, ...newPet };
        updatePetUI();
      }
    } else if (e.key === 'starlearn_plants') {
      // 当林场数据变化时，更新展示
      updateEcoPlantDisplay();
    }
  } catch (err) {
    // ignore parse errors
  }
});

// 监听植物页面自定义事件，实现跨页面即时同步
window.addEventListener('plantStateUpdated', (e) => {
  if (e.detail) {
    updateEcoPlantDisplay();
  }
});

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
        case 'debate':
            userPreferences.debateModeEnabled = isActive;
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
    if (window.history.length > 1) {
        window.history.back();
    } else {
        window.location.href = '/hub.html';
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