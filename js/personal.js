const API_URL = `${window.location.origin}/api`;

let currentUser = JSON.parse(localStorage.getItem('starlearn_user') || 'null') || {
    name: '同学',
    avatar: 'https://api.dicebear.com/7.x/adventurer/svg?seed=starlearn&backgroundColor=b6e3f4',
    currentTask: '大数据导论'
};

const tasks = [
    { id: 'bigdata', name: '大数据技术', icon: 'database', desc: 'Hadoop/Spark/Flink分布式计算', color: 'blue' },
    { id: 'clang', name: 'C语言程序设计', icon: 'file-code', desc: '指针/内存管理/数据结构', color: 'emerald' },
    { id: 'cpp', name: 'C++面向对象', icon: 'code-2', desc: '类与对象/模板/STL', color: 'purple' },
    { id: 'python', name: 'Python编程', icon: 'terminal', desc: '基础语法/数据分析/AI入门', color: 'amber' },
    { id: 'algorithm', name: '算法与数据结构', icon: 'git-branch', desc: '排序/查找/图论/动态规划', color: 'red' },
    { id: 'os', name: '操作系统', icon: 'cpu', desc: '进程管理/内存管理/文件系统', color: 'cyan' }
];

const avatarStyles = [
    'adventurer', 'avataaars', 'bottts', 'fun-emoji', 'lorelei', 'micah',
    'miniavs', 'notionists', 'open-peeps', 'personas', 'pixel-art', 'thumbs'
];

function init() {
    document.getElementById('current-avatar').src = currentUser.avatar;
    document.getElementById('display-name').textContent = currentUser.name;
    document.getElementById('edit-name').value = currentUser.name;

    const evaluation = JSON.parse(localStorage.getItem('starlearn_evaluation') || '{}');
    document.getElementById('stat-interactions').textContent = evaluation.interactionCount || 0;
    document.getElementById('stat-tasks').textContent = Math.floor((evaluation.interactionCount || 0) / 3);
    document.getElementById('stat-time').textContent = evaluation.codePracticeTime || 0;

    renderAvatarGrid();
    renderTaskGrid();
    lucide.createIcons();
}

function renderAvatarGrid() {
    const grid = document.getElementById('avatar-grid');
    grid.innerHTML = avatarStyles.map(style => {
        const url = `https://api.dicebear.com/7.x/${style}/svg?seed=${encodeURIComponent(currentUser.name)}&backgroundColor=b6e3f4`;
        const isSelected = currentUser.avatar.includes(style);
        return `<img src="${url}" alt="${style}" class="avatar-option w-14 h-14 ${isSelected ? 'selected' : ''}" onclick="selectAvatar('${style}', this)"/>`;
    }).join('');
}

function renderTaskGrid() {
    const grid = document.getElementById('task-grid');
    const colorMap = { blue: 'bg-blue-50 text-blue-600 border-blue-200', emerald: 'bg-emerald-50 text-emerald-600 border-emerald-200', purple: 'bg-purple-50 text-purple-600 border-purple-200', amber: 'bg-amber-50 text-amber-600 border-amber-200', red: 'bg-red-50 text-red-600 border-red-200', cyan: 'bg-cyan-50 text-cyan-600 border-cyan-200' };
    grid.innerHTML = tasks.map(task => {
        const isActive = currentUser.currentTask === task.name || (currentUser.currentTask === '大数据导论' && task.id === 'bigdata');
        return `
        <div class="task-card p-5 rounded-xl border-2 ${isActive ? 'active border-blue-500' : 'border-gray-100'} cursor-pointer" onclick="switchTask('${task.name}', '${task.id}')">
            <div class="flex items-center gap-3 mb-2">
                <div class="w-10 h-10 rounded-lg ${colorMap[task.color]} flex items-center justify-center">
                    <i data-lucide="${task.icon}" class="w-5 h-5"></i>
                </div>
                <div>
                    <div class="text-sm font-bold text-gray-800">${task.name}</div>
                    <div class="text-xs text-gray-400">${task.desc}</div>
                </div>
                ${isActive ? '<span class="ml-auto px-2 py-0.5 bg-blue-600 text-white text-xs rounded-full font-semibold">当前</span>' : ''}
            </div>
        </div>`;
    }).join('');
    lucide.createIcons();
}

function selectAvatar(style, el) {
    const url = `https://api.dicebear.com/7.x/${style}/svg?seed=${encodeURIComponent(currentUser.name)}&backgroundColor=b6e3f4`;
    currentUser.avatar = url;
    document.getElementById('current-avatar').src = url;
    document.querySelectorAll('.avatar-option').forEach(opt => opt.classList.remove('selected'));
    el.classList.add('selected');
    saveUser();
    syncToServer();
}

function handleAvatarUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = function(e) {
        currentUser.avatar = e.target.result;
        document.getElementById('current-avatar').src = e.target.result;
        saveUser();
        syncToServer();
    };
    reader.readAsDataURL(file);
}

async function saveName() {
    const name = document.getElementById('edit-name').value.trim();
    if (!name) return;
    currentUser.name = name;
    document.getElementById('display-name').textContent = name;
    saveUser();
    await syncToServer();
    showToast('用户名已更新');
}

function switchTask(taskName, taskId) {
    currentUser.currentTask = taskName;
    saveUser();
    renderTaskGrid();
    syncToServer();
    showToast(`已切换到「${taskName}」学习任务`);
}

function saveUser() {
    localStorage.setItem('starlearn_user', JSON.stringify(currentUser));
}

async function syncToServer() {
    try {
        await fetch(`${API_URL}/user/update`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username: currentUser.name,
                avatar: currentUser.avatar,
                currentTask: currentUser.currentTask
            })
        });
    } catch (e) {
        console.warn('同步到服务器失败:', e);
    }
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
        document.getElementById('stat-interactions').textContent = '0';
        document.getElementById('stat-tasks').textContent = '0';
        document.getElementById('stat-time').textContent = '0';
        showToast('学习数据已清除');
    }
}

function showToast(msg) {
    const toast = document.createElement('div');
    toast.className = 'fixed top-6 right-6 bg-gray-800 text-white px-6 py-3 rounded-xl shadow-lg text-sm font-semibold z-50 fade-in';
    toast.textContent = msg;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 2500);
}

init();
