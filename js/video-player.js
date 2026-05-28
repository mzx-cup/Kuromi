const SPEED_OPTIONS = [1, 1.25, 1.5, 2];
const STORAGE_PREFIX = 'starlearn-video-progress:';
const NOTE_STORAGE_PREFIX = 'starlearn-video-notes:';

const videoCatalog = [
    {
        id: 'python-algorithm-03',
        title: '算法复杂度分析',
        subtitle: '从时间复杂度、空间复杂度到代码层级分析，建立算法效率判断框架。',
        description: '掌握 O(1)、O(n)、O(log n) 的判断方法，并能用 Python 代码解释时间与空间消耗。',
        src: '/video/python-algorithm-03.mp4',
        durationLabel: '45:30',
        notes: {
            summary: '本节聚焦算法复杂度的判断方法：先识别输入规模，再观察循环层级、递归拆分和额外空间使用。',
            timeline: [
                { time: 90, title: '大 O 表示法', desc: '理解复杂度描述的是增长趋势，而不是精确运行秒数。' },
                { time: 645, title: '单层循环', desc: '用列表遍历解释 O(n) 的来源。' },
                { time: 945, title: '嵌套循环', desc: '对照二维遍历理解 O(n²)。' },
                { time: 1575, title: '空间复杂度', desc: '区分原地计算和额外数组带来的空间消耗。' }
            ],
            questions: [
                '为什么常数项通常会被复杂度表示法省略？',
                '两层循环一定是 O(n²) 吗？',
                '如何判断一个 Python 函数是否使用了额外空间？'
            ],
            suggestion: '看完本节后，建议用三段不同循环结构的 Python 代码手动标注时间复杂度。'
        }
    },
    {
        id: 'python-sort-04',
        title: '排序算法详解',
        subtitle: '比较冒泡、选择、快速和归并排序的核心思想。',
        description: '通过可视化步骤理解常见排序算法，并比较稳定性、时间复杂度和空间复杂度。',
        src: '/video/python-sort-04.mp4',
        durationLabel: '38:20',
        notes: {
            summary: '本节把排序算法拆成比较、交换、分治和合并四类动作，帮助你理解不同算法的效率差异。',
            timeline: [
                { time: 120, title: '排序问题建模', desc: '明确输入、输出和比较规则。' },
                { time: 520, title: '冒泡与选择', desc: '观察简单排序为何通常效率较低。' },
                { time: 1100, title: '快速排序', desc: '理解基准值和分区过程。' },
                { time: 1680, title: '归并排序', desc: '通过合并有序子数组理解分治。' }
            ],
            questions: [
                '快速排序为什么平均表现好但最坏情况差？',
                '稳定排序在什么场景下重要？',
                '归并排序为什么需要额外空间？'
            ],
            suggestion: '建议把快速排序和归并排序各写一遍，再对照调用栈画出递归过程。'
        }
    },
    {
        id: 'python-binary-search-05',
        title: '二分查找实战',
        subtitle: '从有序数组查找到边界条件处理。',
        description: '掌握二分查找模板，并理解左右边界、循环条件和答案区间的关系。',
        src: '/video/python-binary-search-05.mp4',
        durationLabel: '29:10',
        notes: {
            summary: '本节用搜索区间的收缩过程解释二分查找，重点避免边界条件和死循环。',
            timeline: [
                { time: 80, title: '有序性前提', desc: '二分查找依赖单调性或可判定区间。' },
                { time: 410, title: '左右指针', desc: '用 left/right 描述仍可能包含答案的范围。' },
                { time: 860, title: '边界模板', desc: '比较闭区间与半开区间写法。' },
                { time: 1280, title: '实战题型', desc: '把查找值扩展到查找第一个满足条件的位置。' }
            ],
            questions: [
                '为什么 mid 推荐写成 left + (right - left) // 2？',
                '什么时候循环条件用 left <= right？',
                '如何查找第一个大于等于目标值的位置？'
            ],
            suggestion: '建议用纸笔模拟 left、right、mid 的变化，至少跑三组边界输入。'
        }
    }
];

let currentVideoIndex = 0;
let speedIndex = 0;

document.addEventListener('DOMContentLoaded', async function() {
    await loadLocalVideoCatalog();
    renderEpisodeList();
    bindPlayerEvents();
    bindTabs();
    bindDanmaku();
    loadVideo(0);
});

function getCurrentItem() {
    return videoCatalog[currentVideoIndex];
}

async function loadLocalVideoCatalog() {
    try {
        const response = await fetch('/api/local-videos');
        if (!response.ok) return;
        const payload = await response.json();
        const localVideos = Array.isArray(payload.videos) ? payload.videos : [];
        if (localVideos.length === 0) return;
        videoCatalog.splice(0, videoCatalog.length, ...localVideos.map(localVideoToCatalogItem));
    } catch (error) {
        console.warn('Local video catalog unavailable, using fallback catalog.', error);
    }
}

function localVideoToCatalogItem(video, index) {
    const title = cleanCourseTitle(video.title || video.filename || `本地视频 ${index + 1}`);
    const lessonNumber = index + 1;
    return {
        id: video.id || `local-video-${index + 1}`,
        title,
        lessonNumber,
        subtitle: `第 ${lessonNumber} 课`,
        description: title,
        src: video.src,
        durationLabel: '--:--',
        notes: buildDefaultNotes(title, 0)
    };
}

function cleanCourseTitle(value) {
    return String(value || '')
        .replace(/\.[^.]+$/, '')
        .replace(/\(Av[^)]*\)/gi, '')
        .replace(/^\d+(?:\.\d+)*\.?/, '')
        .trim() || '本地课程视频';
}

function buildDefaultNotes(title, duration = 0) {
    const safeDuration = Number.isFinite(duration) && duration > 0 ? duration : 600;
    const points = safeDuration < 360
        ? [0.08, 0.36, 0.72]
        : [0.06, 0.25, 0.48, 0.72, 0.9];
    const names = ['课程导入', '概念建立', '核心讲解', '跟练巩固', '回顾总结'];
    const descs = [
        '快速确认本节课的学习目标和上下文。',
        '记录新概念、关键词和容易混淆的说法。',
        '暂停整理关键步骤、代码片段或操作路径。',
        '跟着视频复现一遍，把卡住的点写成问题。',
        '用自己的话复盘本节课的结论和下一步练习。'
    ];
    return {
        summary: `AI 已根据《${title}》的当前视频时长生成伴学时间线。观看时可以点击时间戳跳转，并把自己的理解写进下方笔记。`,
        timeline: points.map((point, index) => ({
            time: Math.max(0, Math.min(safeDuration - 2, Math.floor(safeDuration * point))),
            title: names[index],
            desc: descs[index]
        })),
        questions: [
            `《${title}》这一节最关键的新知识是什么？`,
            '哪一个步骤需要暂停并自己复现一遍？',
            '看完后能否用一句话讲清本节课的结论？'
        ],
        suggestion: '建议每看完一个关键片段就写一条本地弹幕笔记，AI笔记计数会只统计你实际写下的笔记。'
    };
}

function bindPlayerEvents() {
    const video = document.getElementById('course-video');
    const playBtn = document.getElementById('play-btn');
    const continueBtn = document.getElementById('continue-learning-btn');
    const progressTrack = document.getElementById('progress-track');
    const volumeBtn = document.getElementById('volume-btn');
    const speedBtn = document.getElementById('speed-btn');
    const fullscreenBtn = document.getElementById('fullscreen-btn');
    const player = document.getElementById('video-player');

    playBtn.addEventListener('click', togglePlay);
    if (continueBtn) continueBtn.addEventListener('click', togglePlay);
    video.addEventListener('click', togglePlay);
    video.addEventListener('play', updatePlayIcon);
    video.addEventListener('pause', updatePlayIcon);
    video.addEventListener('timeupdate', handleTimeUpdate);
    video.addEventListener('loadedmetadata', handleLoadedMetadata);
    video.addEventListener('error', showEmptyState);

    progressTrack.addEventListener('click', function(event) {
        if (!Number.isFinite(video.duration) || video.duration === 0) return;
        const rect = progressTrack.getBoundingClientRect();
        const percent = (event.clientX - rect.left) / rect.width;
        video.currentTime = Math.max(0, Math.min(video.duration, percent * video.duration));
    });

    volumeBtn.addEventListener('click', function() {
        const video = document.getElementById('course-video');
        video.muted = !video.muted;
        updateVolumeIcon();
        showToast(video.muted ? '已静音' : '已恢复声音', 'info');
    });

    speedBtn.addEventListener('click', function() {
        speedIndex = (speedIndex + 1) % SPEED_OPTIONS.length;
        video.playbackRate = SPEED_OPTIONS[speedIndex];
        document.getElementById('speed-text').textContent = `${SPEED_OPTIONS[speedIndex]}x`;
    });

    fullscreenBtn.addEventListener('click', function() {
        if (!document.fullscreenElement) {
            player.requestFullscreen().catch(() => showToast('无法进入全屏', 'error'));
        } else {
            document.exitFullscreen();
        }
    });

    document.addEventListener('keydown', function(event) {
        if (event.code === 'Space' && event.target.tagName !== 'INPUT') {
            event.preventDefault();
            togglePlay();
        }
    });
}

function loadVideo(index) {
    currentVideoIndex = index;
    const item = getCurrentItem();
    const video = document.getElementById('course-video');
    const player = document.getElementById('video-player');

    video.pause();
    video.src = item.src;
    video.load();

    document.getElementById('video-title').textContent = item.title;
    document.getElementById('video-subtitle').textContent = item.subtitle;
    document.getElementById('info-title').textContent = item.title;
    document.getElementById('info-description').textContent = item.description;
    document.getElementById('total-time').textContent = item.durationLabel;
    updateStudentNoteCount();
    updateProgress(0);
    renderAiNotes(item);
    updateEpisodeActiveState();

    player.setAttribute('data-loading-state', '');
    player.removeAttribute('data-empty-state');
    const emptyText = document.querySelector('.placeholder-text');
    const emptySubtext = document.querySelector('.placeholder-subtext');
    if (emptyText) emptyText.textContent = '视频加载中...';
    if (emptySubtext) emptySubtext.textContent = '正在读取视频文件，请稍候';
    updatePlayIcon();

    function onMetadata() {
        player.removeAttribute('data-loading-state');
        player.removeAttribute('data-empty-state');
        if (emptyText) emptyText.textContent = '请将视频放入 星识 根目录的 video/ 文件夹';
        if (emptySubtext) emptySubtext.textContent = '支持 .mp4 / .webm / .mov，播放器会使用 /video/ 路径读取本地视频。';
        const saved = Number(localStorage.getItem(STORAGE_PREFIX + item.id));
        if (Number.isFinite(saved) && saved > 0 && saved < video.duration) {
            video.currentTime = saved;
        }
        item.durationLabel = formatTime(video.duration);
        item.notes = buildDefaultNotes(item.title, video.duration);
        document.getElementById('total-time').textContent = item.durationLabel;
        renderAiNotes(item);
        renderEpisodeList();
        updateEpisodeActiveState();
        handleTimeUpdate();
        video.removeEventListener('loadedmetadata', onMetadata);
    }
    video.addEventListener('loadedmetadata', onMetadata);

    function onError() {
        player.removeAttribute('data-loading-state');
        player.setAttribute('data-empty-state', '');
        video.removeEventListener('error', onError);
    }
    video.addEventListener('error', onError);
    updateVolumeIcon();
}

function renderEpisodeList() {
    const list = document.getElementById('episode-list');
    list.innerHTML = '';
    document.getElementById('episode-count').textContent = `${videoCatalog.length} 个视频`;

    videoCatalog.forEach((item, index) => {
        const saved = Number(localStorage.getItem(STORAGE_PREFIX + item.id)) || 0;
        const progress = saved > 0 ? 12 : 0;
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'episode-item';
        button.dataset.index = index;
        button.innerHTML = `
            <span class="episode-index">${String(index + 1).padStart(2, '0')}</span>
            <span>
                <span class="episode-title">${escapeHtml(item.title)}</span>
                <span class="episode-desc">${escapeHtml(item.durationLabel)} · ${getStudentNotes(item.id).length} 条笔记</span>
                <span class="episode-progress" style="--progress-width: ${progress}%"><span></span></span>
            </span>
        `;
        button.addEventListener('click', () => loadVideo(index));
        list.appendChild(button);
    });
}

function updateEpisodeActiveState() {
    document.querySelectorAll('.episode-item').forEach((item) => {
        item.classList.toggle('active', Number(item.dataset.index) === currentVideoIndex);
    });
}

function renderAiNotes(item) {
    document.getElementById('ai-summary-text').textContent = item.notes.summary;
    document.getElementById('ai-suggestion-text').textContent = item.notes.suggestion;
    updateStudentNoteCount();

    const timeline = document.getElementById('note-timeline');
    timeline.innerHTML = '';
    item.notes.timeline.forEach((note) => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'note-item';
        button.innerHTML = `
            <span class="note-time">${formatTime(note.time)}</span>
            <span>
                <span class="note-title">${escapeHtml(note.title)}</span>
                <span class="note-desc">${escapeHtml(note.desc)}</span>
            </span>
        `;
        button.addEventListener('click', () => seekToNote(note.time));
        timeline.appendChild(button);
    });

    const questions = document.getElementById('question-list');
    questions.innerHTML = '';
    item.notes.questions.forEach((question) => {
        const div = document.createElement('div');
        div.className = 'question-item';
        div.textContent = question;
        questions.appendChild(div);
    });

    renderStudentNotes(item);
}

function seekToNote(time) {
    const video = document.getElementById('course-video');
    video.currentTime = time;
    video.focus();
    showToast(`已跳转到 ${formatTime(time)}`, 'success');
}

function bindTabs() {
    document.querySelectorAll('.side-tab').forEach((tab) => {
        tab.addEventListener('click', function() {
            document.querySelectorAll('.side-tab').forEach((item) => item.classList.remove('active'));
            document.querySelectorAll('.side-panel-section').forEach((item) => item.classList.remove('active'));
            tab.classList.add('active');
            document.getElementById(`${tab.dataset.tab}-panel`).classList.add('active');
        });
    });
}

function bindDanmaku() {
    document.getElementById('danmaku-form').addEventListener('submit', function(event) {
        event.preventDefault();
        const input = document.getElementById('danmaku-input');
        const text = input.value.trim();
        if (!text) return;
        addStudentNote(text);
        launchDanmaku(text);
        input.value = '';
    });
}

function getStudentNotes(videoId) {
    try {
        const raw = localStorage.getItem(NOTE_STORAGE_PREFIX + videoId);
        const notes = raw ? JSON.parse(raw) : [];
        return Array.isArray(notes) ? notes : [];
    } catch (error) {
        return [];
    }
}

function saveStudentNotes(videoId, notes) {
    localStorage.setItem(NOTE_STORAGE_PREFIX + videoId, JSON.stringify(notes));
}

function addStudentNote(text) {
    const video = document.getElementById('course-video');
    const item = getCurrentItem();
    const notes = getStudentNotes(item.id);
    notes.push({
        text,
        time: Number.isFinite(video.currentTime) ? Math.floor(video.currentTime) : 0,
        createdAt: Date.now()
    });
    saveStudentNotes(item.id, notes);
    updateStudentNoteCount();
    renderStudentNotes(item);
    renderEpisodeList();
    updateEpisodeActiveState();
}

function updateStudentNoteCount() {
    const item = getCurrentItem();
    document.getElementById('note-count').textContent = getStudentNotes(item.id).length;
}

function renderStudentNotes(item) {
    const list = document.getElementById('student-note-list');
    if (!list) return;
    const notes = getStudentNotes(item.id);
    list.innerHTML = '';
    if (notes.length === 0) {
        const empty = document.createElement('div');
        empty.className = 'student-note-empty';
        empty.textContent = '还没有学生笔记，发送一条本地弹幕后这里会自动记录。';
        list.appendChild(empty);
        return;
    }

    notes.slice().reverse().forEach((note) => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'student-note-item';
        button.innerHTML = `
            <span class="note-time">${formatTime(note.time)}</span>
            <span class="student-note-text">${escapeHtml(note.text)}</span>
        `;
        button.addEventListener('click', () => seekToNote(note.time));
        list.appendChild(button);
    });
}

function launchDanmaku(text) {
    const stage = document.getElementById('danmaku-stage');
    const item = document.createElement('div');
    item.className = 'danmaku-item';
    item.textContent = text;
    item.style.setProperty('--lane-top', `${18 + Math.floor(Math.random() * 48)}%`);
    stage.appendChild(item);
    setTimeout(() => item.remove(), 7200);
}

function togglePlay() {
    const video = document.getElementById('course-video');
    if (!video.src) return;
    if (video.paused) {
        video.muted = false;
        updateVolumeIcon();
        video.play().catch(() => showToast('视频暂不可播放，请确认 video/ 中存在对应文件', 'warning'));
    } else {
        video.pause();
    }
}

function updatePlayIcon() {
    const video = document.getElementById('course-video');
    document.querySelector('.icon-play').classList.toggle('hidden', !video.paused);
    document.querySelector('.icon-pause').classList.toggle('hidden', video.paused);
}

function updateVolumeIcon() {
    const video = document.getElementById('course-video');
    const btn = document.getElementById('volume-btn');
    if (!btn) return;
    if (video.muted || video.volume === 0) {
        btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M11 5L6 9H2v6h4l5 4V5z"/>
            <line x1="23" y1="9" x2="17" y2="15"/><line x1="17" y1="9" x2="23" y2="15"/>
        </svg>`;
    } else {
        btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M11 5L6 9H2v6h4l5 4V5z"/>
            <path d="M19.07 4.93a10 10 0 010 14.14M15.54 8.46a5 5 0 010 7.07"/>
        </svg>`;
    }
}

function handleLoadedMetadata() {
    const video = document.getElementById('course-video');
    const item = getCurrentItem();
    document.getElementById('video-player').removeAttribute('data-empty-state');
    item.durationLabel = formatTime(video.duration);
    item.notes = buildDefaultNotes(item.title, video.duration);
    document.getElementById('total-time').textContent = item.durationLabel;
    renderAiNotes(item);
    renderEpisodeList();
    updateEpisodeActiveState();
    handleTimeUpdate();
}

function handleTimeUpdate() {
    const video = document.getElementById('course-video');
    if (!Number.isFinite(video.duration) || video.duration === 0) return;
    const percent = (video.currentTime / video.duration) * 100;
    updateProgress(percent);
    document.getElementById('current-time').textContent = formatTime(video.currentTime);
    document.getElementById('progress-percent').textContent = `${Math.round(percent)}%`;
    localStorage.setItem(STORAGE_PREFIX + getCurrentItem().id, String(Math.floor(video.currentTime)));
}

function updateProgress(percent) {
    const safePercent = Math.max(0, Math.min(100, percent));
    document.getElementById('progress-fill').style.width = `${safePercent}%`;
    document.getElementById('progress-thumb').style.left = `${safePercent}%`;
    document.getElementById('progress-percent').textContent = `${Math.round(safePercent)}%`;
}

function showEmptyState() {
    const player = document.getElementById('video-player');
    player.removeAttribute('data-loading-state');
    player.setAttribute('data-empty-state', '');
    const emptyText = document.querySelector('.placeholder-text');
    const emptySubtext = document.querySelector('.placeholder-subtext');
    if (emptyText) emptyText.textContent = '请将视频放入 星识 根目录的 video/ 文件夹';
    if (emptySubtext) emptySubtext.textContent = '支持 .mp4 / .webm / .mov，播放器会使用 /video/ 路径读取本地视频。';
    updatePlayIcon();
}

function formatTime(value) {
    if (!Number.isFinite(value)) return '00:00';
    const total = Math.max(0, Math.floor(value));
    const minutes = Math.floor(total / 60);
    const seconds = total % 60;
    return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showToast(message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = `
            position: fixed;
            bottom: 24px;
            right: 24px;
            z-index: 9999;
            display: flex;
            flex-direction: column;
            gap: 12px;
        `;
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    const colors = {
        success: 'rgba(16, 185, 129, 0.4)',
        error: 'rgba(239, 68, 68, 0.4)',
        warning: 'rgba(249, 115, 22, 0.4)',
        info: 'rgba(59, 130, 246, 0.4)'
    };
    toast.style.cssText = `
        padding: 14px 20px;
        background: rgba(20, 20, 40, 0.95);
        border: 1px solid ${colors[type] || colors.info};
        border-radius: 12px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
        color: #fff;
        font-size: 14px;
        animation: slideIn 0.3s ease;
        backdrop-filter: blur(20px);
    `;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100px)';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}
