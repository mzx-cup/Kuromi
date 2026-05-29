const STORAGE_PREFIX = 'starlearn-video-progress:';
const NOTE_STORAGE_PREFIX = 'starlearn-video-notes:';
const SPEED_OPTIONS = [1, 1.25, 1.5, 2];

let currentSourceType = null;
let currentVideoId = null;
let currentCourseData = null;
let speedIndex = 0;

// ============ DOM refs ============
const $ = (id) => document.getElementById(id);
const videoLocal = $('course-video-local');
const iframeBilibili = $('course-video-bilibili');
const player = $('video-player');
const playBtn = $('play-btn');
const volumeBtn = $('volume-btn');
const speedBtn = $('speed-btn');
const speedText = $('speed-text');
const fullscreenBtn = $('fullscreen-btn');
const progressTrack = $('progress-track');
const progressFill = $('progress-fill');
const progressThumb = $('progress-thumb');
const currentTimeEl = $('current-time');
const totalTimeEl = $('total-time');
const progressPercent = $('progress-percent');
const danmakuForm = $('danmaku-form');
const danmakuInput = $('danmaku-input');
const danmakuStage = $('danmaku-stage');

// ============ BilibiliDriver ============
const BilibiliDriver = {
    _playing: false,

    get iframe() { return iframeBilibili; },

    postCommand(cmd, ...args) {
        try {
            this.iframe.contentWindow.postMessage(
                { cmd: 'callPlayer', args: [cmd, ...args], id: Date.now() },
                'https://player.bilibili.com'
            );
        } catch (e) {}
    },

    load(bvid, page = 1) {
        this._playing = false;
        this.iframe.src = 'https://player.bilibili.com/player.html?bvid=' + bvid + '&page=' + page + '&autoplay=0&danmaku=0';
    },

    play() { this.postCommand('play'); },
    pause() { this.postCommand('pause'); },
    seek(time) { this.postCommand('seek', time); },
    setPlaybackRate(rate) { this.postCommand('setPlaybackRate', rate); },
    setVolume(vol) { this.postCommand('setVolume', vol / 100); },

    show() {
        this.iframe.style.display = 'block';
        videoLocal.style.display = 'none';
    },

    hide() {
        this.iframe.style.display = 'none';
    }
};

// ============ LocalDriver ============
const LocalDriver = {
    get video() { return videoLocal; },

    load(src) {
        this.video.src = src;
        this.video.load();
    },

    play() { this.video.play().catch(() => {}); },
    pause() { this.video.pause(); },
    seek(time) { this.video.currentTime = time; },
    setPlaybackRate(rate) { this.video.playbackRate = rate; },
    setVolume(vol) { this.video.volume = vol / 100; },

    get currentTime() { return this.video.currentTime; },
    get duration() { return this.video.duration; },
    get paused() { return this.video.paused; },

    show() {
        this.video.style.display = 'block';
        iframeBilibili.style.display = 'none';
    },

    hide() {
        this.video.style.display = 'none';
    }
};

// ============ videoController ============
const videoController = {
    get driver() {
        return currentSourceType === 'bilibili' ? BilibiliDriver : LocalDriver;
    },

    load(courseData) {
        currentCourseData = courseData;
        currentSourceType = courseData.source_type || 'bilibili';
        currentVideoId = courseData.id;

        player.removeAttribute('data-empty-state');
        player.setAttribute('data-loading-state', '');

        if (currentSourceType === 'bilibili') {
            BilibiliDriver.show();
            BilibiliDriver.load(courseData.bvid, courseData.page || 1);
        } else {
            LocalDriver.show();
            LocalDriver.load(courseData.local_path);
        }

        $('video-title').textContent = courseData.title || '';
        $('video-subtitle').textContent = courseData.subtitle || '';
        $('info-title').textContent = courseData.title || '';
        $('info-description').textContent = courseData.subtitle || '';
        $('total-time').textContent = courseData.duration_label || '--:--';
        $('info-source-label').textContent =
            `来源: ${currentSourceType === 'bilibili' ? 'B站 · ' + (courseData.bvid || '') : '本地 · ' + (courseData.local_path || '')}`;

        updateProgress(0);
        currentTimeEl.textContent = '00:00';
        renderAiNotes(courseData);
        updateStudentNoteCount();
    },

    play() { this.driver.play(); },
    pause() { this.driver.pause(); },
    togglePlay() {
        if (currentSourceType === 'local') {
            if (LocalDriver.paused) LocalDriver.play();
            else LocalDriver.pause();
        } else {
            if (BilibiliDriver._playing) BilibiliDriver.pause();
            else BilibiliDriver.play();
        }
    },
    seek(time) { this.driver.seek(time); },
    setSpeed(rate) { this.driver.setPlaybackRate(rate); },
    setVolume(vol) { this.driver.setVolume(vol); }
};

// ============ postMessage 监听 ============
window.addEventListener('message', function(e) {
    if (e.origin !== 'https://player.bilibili.com') return;
    const data = e.data;
    if (!data || typeof data !== 'object') return;

    if (typeof data.currentTime === 'number' && currentSourceType === 'bilibili') {
        const duration = data.duration || 1;
        const pct = (data.currentTime / duration) * 100;
        updateProgress(pct);
        currentTimeEl.textContent = formatTime(data.currentTime);
        if (data.duration && totalTimeEl.textContent === '--:--') {
            totalTimeEl.textContent = formatTime(data.duration);
        }
    }

    if (data.state === 'playing') {
        BilibiliDriver._playing = true;
        updatePlayIcon(true);
    }
    if (data.state === 'paused') {
        BilibiliDriver._playing = false;
        updatePlayIcon(false);
    }

    if (data.state === 'ready' || data.state === 'playing') {
        player.removeAttribute('data-loading-state');
        player.removeAttribute('data-empty-state');
    }
});

// ============ 本地视频事件 ============
videoLocal.addEventListener('timeupdate', function() {
    if (currentSourceType !== 'local') return;
    if (!Number.isFinite(videoLocal.duration)) return;
    const pct = (videoLocal.currentTime / videoLocal.duration) * 100;
    updateProgress(pct);
    currentTimeEl.textContent = formatTime(videoLocal.currentTime);
    if (Number.isFinite(videoLocal.duration)) {
        totalTimeEl.textContent = formatTime(videoLocal.duration);
    }
    localStorage.setItem(STORAGE_PREFIX + currentVideoId, String(Math.floor(videoLocal.currentTime)));
});

videoLocal.addEventListener('loadedmetadata', function() {
    if (currentSourceType !== 'local') return;
    player.removeAttribute('data-loading-state');
    player.removeAttribute('data-empty-state');
    totalTimeEl.textContent = formatTime(videoLocal.duration);
    const saved = Number(localStorage.getItem(STORAGE_PREFIX + currentVideoId));
    if (Number.isFinite(saved) && saved > 0 && saved < videoLocal.duration) {
        videoLocal.currentTime = saved;
    }
});

videoLocal.addEventListener('play', () => updatePlayIcon(true));
videoLocal.addEventListener('pause', () => updatePlayIcon(false));
videoLocal.addEventListener('error', showEmptyState);

// ============ 控制栏事件 ============
playBtn.addEventListener('click', () => videoController.togglePlay());

volumeBtn.addEventListener('click', function() {
    if (currentSourceType === 'local') {
        videoLocal.muted = !videoLocal.muted;
        updateVolumeIcon();
        showToast(videoLocal.muted ? '已静音' : '已恢复声音', 'info');
    } else {
        showToast('B站视频请使用播放器内置音量控制', 'info');
    }
});

speedBtn.addEventListener('click', function() {
    speedIndex = (speedIndex + 1) % SPEED_OPTIONS.length;
    const rate = SPEED_OPTIONS[speedIndex];
    speedText.textContent = rate + 'x';
    videoController.setSpeed(rate);
});

fullscreenBtn.addEventListener('click', function() {
    if (!document.fullscreenElement) {
        player.requestFullscreen().catch(() => showToast('无法进入全屏', 'error'));
    } else {
        document.exitFullscreen();
    }
});

progressTrack.addEventListener('click', function(e) {
    if (currentSourceType === 'local') {
        if (!Number.isFinite(videoLocal.duration)) return;
        const rect = progressTrack.getBoundingClientRect();
        const pct = (e.clientX - rect.left) / rect.width;
        videoLocal.currentTime = pct * videoLocal.duration;
    } else if (currentSourceType === 'bilibili') {
        showToast('B站视频请拖动播放器内置进度条', 'info');
    }
});

document.addEventListener('keydown', function(e) {
    if (e.code === 'Space' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
        e.preventDefault();
        videoController.togglePlay();
    }
});

// ============ 课程库 ============
async function loadCourseLibrary() {
    try {
        const resp = await fetch('/api/video-courses');
        if (!resp.ok) return;
        const data = await resp.json();
        renderCourseList(data.courses || []);
    } catch (e) {
        console.warn('加载课程库失败', e);
    }
}

function renderCourseList(courses, filter) {
    if (filter === undefined) filter = '';
    const list = $('course-list');
    list.innerHTML = '';
    const filtered = filter
        ? courses.filter(function(c) { return c.title.toLowerCase().indexOf(filter.toLowerCase()) !== -1; })
        : courses;

    if (filtered.length === 0) {
        list.innerHTML = '<div class="empty-list-hint">没有匹配的课程</div>';
        return;
    }

    filtered.forEach(function(course, i) {
        const div = document.createElement('div');
        div.className = 'course-item';
        const sourceLabel = course.source_type === 'bilibili' ? 'B站' : '本地';
        div.innerHTML =
            '<span class="course-index">' + String(i + 1).padStart(2, '0') + '</span>' +
            '<span class="course-title">' + escapeHtml(course.title) + '</span>' +
            '<span class="source-tag ' + course.source_type + '">' + sourceLabel + '</span>' +
            '<button class="add-to-list-btn" data-course-id="' + course.id + '">+ 加入列表</button>';
        div.querySelector('.add-to-list-btn').addEventListener('click', function(e) {
            e.stopPropagation();
            addCourseToPlaylist(course.id);
        });
        list.appendChild(div);
    });
}

$('course-search').addEventListener('input', async function() {
    try {
        const resp = await fetch('/api/video-courses');
        if (!resp.ok) return;
        const data = await resp.json();
        renderCourseList(data.courses || [], this.value);
    } catch (e) {}
});

async function addCourseToPlaylist(courseId) {
    const playlistId = getCurrentPlaylistId();
    if (!playlistId) {
        showToast('请先创建播放列表', 'warning');
        return;
    }
    try {
        const resp = await fetch('/api/playlist-videos', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ playlist_id: playlistId, course_id: courseId })
        });
        if (resp.ok) {
            showToast('已添加到播放列表', 'success');
            loadPlaylist();
        } else {
            showToast('添加失败', 'error');
        }
    } catch (e) {
        showToast('网络错误', 'error');
    }
}

// ============ 播放列表 ============
async function loadPlaylist() {
    const userId = getCurrentUserId();
    if (!userId) return;
    try {
        const resp = await fetch('/api/video-playlists?user_id=' + encodeURIComponent(userId));
        if (!resp.ok) return;
        const data = await resp.json();
        const playlists = data.playlists || [];
        if (playlists.length > 0) {
            renderPlaylistVideos(playlists[0]);
            $('playlist-count').textContent = (playlists[0].videos ? playlists[0].videos.length : 0) + ' 个视频';
            $('playlist-name').textContent = playlists[0].name;
        } else {
            const pid = await createDefaultPlaylist(userId);
            if (pid) {
                renderPlaylistVideos({ id: pid, videos: [], name: '默认列表' });
                $('playlist-count').textContent = '0 个视频';
                $('playlist-name').textContent = '默认列表';
            }
        }
    } catch (e) {
        console.warn('加载播放列表失败', e);
    }
}

function getCurrentPlaylistId() {
    return parseInt(localStorage.getItem('starlearn-current-playlist-id') || '0') || null;
}

async function createDefaultPlaylist(userId) {
    try {
        const resp = await fetch('/api/video-playlists', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, name: '默认列表' })
        });
        if (resp.ok) {
            const data = await resp.json();
            localStorage.setItem('starlearn-current-playlist-id', String(data.id));
            return data.id;
        }
    } catch (e) {}
    return null;
}

function getCurrentUserId() {
    try {
        if (window.StarData && window.StarData.user && window.StarData.user.id) {
            return window.StarData.user.id;
        }
    } catch (e) {}
    return localStorage.getItem('starlearn-user-id') || 'anonymous';
}

function renderPlaylistVideos(playlist) {
    const list = $('playlist-episode-list');
    list.innerHTML = '';
    const videos = playlist.videos || [];
    if (videos.length === 0) {
        list.innerHTML = '<div class="empty-list-hint">添加你的第一个学习视频<br>支持 bilibili.com 的 BV 号或 av 号</div>';
        return;
    }
    localStorage.setItem('starlearn-current-playlist-id', String(playlist.id));
    $('playlist-count').textContent = videos.length + ' 个视频';

    videos.forEach(function(v, i) {
        const div = document.createElement('div');
        div.className = 'playlist-video-item';
        const sourceLabel = v.source_type === 'bilibili' ? 'B站' : '本地';
        div.innerHTML =
            '<span class="episode-index">' + String(i + 1).padStart(2, '0') + '</span>' +
            '<span>' +
                '<span class="episode-title">' + escapeHtml(v.title || '未命名') + '</span>' +
                '<span class="episode-desc">' + (v.duration_label || '--:--') + ' · <span class="source-tag ' + v.source_type + '">' + sourceLabel + '</span></span>' +
            '</span>' +
            '<button class="remove-from-list-btn" data-pv-id="' + v.id + '" title="从列表移除">&times;</button>';
        div.addEventListener('click', function(e) {
            if (e.target.classList.contains('remove-from-list-btn')) return;
            videoController.load(v);
            updatePlaylistActiveState(i);
        });
        div.querySelector('.remove-from-list-btn').addEventListener('click', async function(e) {
            e.stopPropagation();
            await removeFromPlaylist(v.id);
        });
        list.appendChild(div);
    });
}

function updatePlaylistActiveState(index) {
    document.querySelectorAll('.playlist-video-item').forEach(function(item, i) {
        if (i === index) item.classList.add('active');
        else item.classList.remove('active');
    });
}

async function removeFromPlaylist(pvId) {
    try {
        const resp = await fetch('/api/playlist-videos/' + pvId, { method: 'DELETE' });
        if (resp.ok) {
            showToast('已从列表移除', 'success');
            loadPlaylist();
        }
    } catch (e) {
        showToast('移除失败', 'error');
    }
}

// ============ 添加课程弹窗 ============
$('add-course-btn').addEventListener('click', function() {
    $('add-course-modal').classList.remove('hidden');
});

$('modal-close-btn').addEventListener('click', function() {
    $('add-course-modal').classList.add('hidden');
});

$('modal-cancel-btn').addEventListener('click', function() {
    $('add-course-modal').classList.add('hidden');
});

$('course-source-type').addEventListener('change', function() {
    if (this.value === 'bilibili') {
        $('bvid-group').classList.remove('hidden');
        $('local-path-group').classList.add('hidden');
    } else {
        $('bvid-group').classList.add('hidden');
        $('local-path-group').classList.remove('hidden');
    }
});

$('add-course-form').addEventListener('submit', async function(e) {
    e.preventDefault();
    const sourceType = $('course-source-type').value;
    const title = $('course-title-input').value.trim();
    if (!title) { showToast('请输入课程标题', 'warning'); return; }

    const body = {
        title: title,
        source_type: sourceType,
        subtitle: title,
        created_by: getCurrentUserId()
    };

    if (sourceType === 'bilibili') {
        body.bvid = $('course-bvid-input').value.trim();
        if (!body.bvid) { showToast('请输入 B站 BV 号', 'warning'); return; }
        try {
            const infoResp = await fetch('/api/bilibili/info?bvid=' + body.bvid);
            if (infoResp.ok) {
                const info = await infoResp.json();
                body.title = info.title || title;
                body.subtitle = info.owner ? 'UP主: ' + info.owner : title;
                body.duration_label = info.duration_label || '--:--';
            }
        } catch (e) {}
    } else {
        body.local_path = $('course-local-input').value.trim();
        if (!body.local_path) { showToast('请输入本地文件路径', 'warning'); return; }
    }

    try {
        const resp = await fetch('/api/video-courses', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if (resp.ok) {
            showToast('课程已添加', 'success');
            $('add-course-modal').classList.add('hidden');
            this.reset();
            loadCourseLibrary();
        } else {
            showToast('添加失败', 'error');
        }
    } catch (e) {
        showToast('网络错误', 'error');
    }
});

// ============ Tab 切换 ============
document.querySelectorAll('.side-tab').forEach(function(tab) {
    tab.addEventListener('click', function() {
        document.querySelectorAll('.side-tab').forEach(function(t) { t.classList.remove('active'); });
        document.querySelectorAll('.side-panel-section').forEach(function(s) { s.classList.remove('active'); });
        this.classList.add('active');
        const panelId = this.dataset.tab + '-panel';
        const panel = document.getElementById(panelId);
        if (panel) panel.classList.add('active');
        if (this.dataset.tab === 'courses') loadCourseLibrary();
        if (this.dataset.tab === 'playlist') loadPlaylist();
    });
});

// ============ 弹幕 ============
danmakuForm.addEventListener('submit', function(e) {
    e.preventDefault();
    const text = danmakuInput.value.trim();
    if (!text) return;
    addStudentNote(text);
    launchDanmaku(text);
    danmakuInput.value = '';
});

function getStudentNotes(videoId) {
    try {
        const raw = localStorage.getItem(NOTE_STORAGE_PREFIX + videoId);
        const notes = raw ? JSON.parse(raw) : [];
        return Array.isArray(notes) ? notes : [];
    } catch (e) { return []; }
}

function saveStudentNotes(videoId, notes) {
    localStorage.setItem(NOTE_STORAGE_PREFIX + videoId, JSON.stringify(notes));
}

function addStudentNote(text) {
    if (!currentVideoId) return;
    const notes = getStudentNotes(currentVideoId);
    notes.push({ text: text, time: Math.floor(Date.now() / 1000), createdAt: Date.now() });
    saveStudentNotes(currentVideoId, notes);
    updateStudentNoteCount();
    renderStudentNotes(currentCourseData);
}

function updateStudentNoteCount() {
    $('note-count').textContent = currentVideoId ? getStudentNotes(currentVideoId).length : 0;
}

function renderStudentNotes(item) {
    const list = $('student-note-list');
    if (!list) return;
    const itemId = item ? item.id : currentVideoId;
    const notes = getStudentNotes(itemId);
    list.innerHTML = '';
    if (notes.length === 0) {
        list.innerHTML = '<div class="student-note-empty">还没有学生笔记，发送一条本地弹幕后这里会自动记录。</div>';
        return;
    }
    notes.slice().reverse().forEach(function(note) {
        const div = document.createElement('div');
        div.className = 'student-note-item';
        const date = new Date(note.createdAt);
        div.innerHTML =
            '<span class="note-time">' + String(date.getHours()).padStart(2, '0') + ':' + String(date.getMinutes()).padStart(2, '0') + '</span>' +
            '<span class="student-note-text">' + escapeHtml(note.text) + '</span>';
        list.appendChild(div);
    });
}

function launchDanmaku(text) {
    const el = document.createElement('div');
    el.className = 'danmaku-item';
    el.textContent = text;
    el.style.setProperty('--lane-top', (18 + Math.floor(Math.random() * 48)) + '%');
    danmakuStage.appendChild(el);
    setTimeout(function() { el.remove(); }, 7200);
}

// ============ AI 笔记 ============
function renderAiNotes(item) {
    if (!item) return;
    $('ai-summary-text').textContent =
        (typeof item.ai_summary === 'string' ? item.ai_summary : '') || '暂无摘要';
    $('ai-suggestion-text').textContent =
        (typeof item.ai_suggestion === 'string' ? item.ai_suggestion : '') || '暂无建议';
    updateStudentNoteCount();

    const timeline = $('note-timeline');
    timeline.innerHTML = '';
    let timelineData = item.ai_timeline;
    if (typeof timelineData === 'string') {
        try { timelineData = JSON.parse(timelineData); } catch (e) { timelineData = []; }
    }
    if (Array.isArray(timelineData)) {
        timelineData.forEach(function(note) {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'note-item';
            btn.innerHTML =
                '<span class="note-time">' + formatTime(note.time) + '</span>' +
                '<span>' +
                    '<span class="note-title">' + escapeHtml(note.title) + '</span>' +
                    '<span class="note-desc">' + escapeHtml(note.desc) + '</span>' +
                '</span>';
            btn.addEventListener('click', function() {
                if (currentSourceType === 'bilibili') {
                    BilibiliDriver.seek(note.time);
                    showToast('已跳转到 ' + formatTime(note.time), 'success');
                } else {
                    videoLocal.currentTime = note.time;
                    showToast('已跳转到 ' + formatTime(note.time), 'success');
                }
            });
            timeline.appendChild(btn);
        });
    }

    const questions = $('question-list');
    questions.innerHTML = '';
    let qData = item.ai_questions;
    if (typeof qData === 'string') {
        try { qData = JSON.parse(qData); } catch (e) { qData = []; }
    }
    if (Array.isArray(qData)) {
        qData.forEach(function(q) {
            const div = document.createElement('div');
            div.className = 'question-item';
            div.textContent = q;
            questions.appendChild(div);
        });
    }

    renderStudentNotes(item);
}

// ============ 工具函数 ============
function updateProgress(pct) {
    const safe = Math.max(0, Math.min(100, pct));
    progressFill.style.width = safe + '%';
    progressThumb.style.left = safe + '%';
    if (progressPercent) progressPercent.textContent = Math.round(safe) + '%';
}

function updatePlayIcon(playing) {
    var playIcon = document.querySelector('.icon-play');
    var pauseIcon = document.querySelector('.icon-pause');
    if (playIcon) playIcon.classList.toggle('hidden', playing);
    if (pauseIcon) pauseIcon.classList.toggle('hidden', !playing);
}

function updateVolumeIcon() {
    if (!volumeBtn) return;
    if (currentSourceType === 'local' && videoLocal.muted) {
        volumeBtn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 5L6 9H2v6h4l5 4V5z"/><line x1="23" y1="9" x2="17" y2="15"/><line x1="17" y1="9" x2="23" y2="15"/></svg>';
    }
}

function showEmptyState() {
    player.setAttribute('data-empty-state', '');
    BilibiliDriver._playing = false;
}

function formatTime(value) {
    if (!Number.isFinite(value)) return '00:00';
    const total = Math.max(0, Math.floor(value));
    const m = Math.floor(total / 60);
    const s = total % 60;
    return String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showToast(message, type) {
    if (type === undefined) type = 'info';
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:9999;display:flex;flex-direction:column;gap:12px;';
        document.body.appendChild(container);
    }
    const colors = { success: 'rgba(16,185,129,0.4)', error: 'rgba(239,68,68,0.4)', warning: 'rgba(249,115,22,0.4)', info: 'rgba(59,130,246,0.4)' };
    const toast = document.createElement('div');
    toast.style.cssText = 'padding:14px 20px;background:rgba(20,20,40,0.95);border:1px solid ' + (colors[type] || colors.info) + ';border-radius:12px;box-shadow:0 8px 32px rgba(0,0,0,0.4);color:#fff;font-size:14px;animation:slideIn 0.3s ease;backdrop-filter:blur(20px);';
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(function() {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100px)';
        setTimeout(function() { toast.remove(); }, 300);
    }, 3000);
}

// ============ 初始化 ============
document.addEventListener('DOMContentLoaded', async function() {
    await loadPlaylist();
    try {
        const userId = getCurrentUserId();
        const playlistResp = await fetch('/api/video-playlists?user_id=' + encodeURIComponent(userId));
        if (playlistResp.ok) {
            const data = await playlistResp.json();
            const playlists = data.playlists || [];
            if (playlists.length > 0 && playlists[0].videos && playlists[0].videos.length > 0) {
                videoController.load(playlists[0].videos[0]);
                updatePlaylistActiveState(0);
            }
        }
    } catch (e) {
        console.warn('初始化加载播放列表失败', e);
    }
});
