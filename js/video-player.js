document.addEventListener('DOMContentLoaded', function() {
    initVideoPlayer();
    initChapterList();
    initAICompanion();
});

let isPlaying = false;
let currentProgress = 35;
let currentChapter = 3;

function initVideoPlayer() {
    const playBtn = document.getElementById('play-btn');
    const videoPlayer = document.getElementById('video-player');
    const progressTrack = document.querySelector('.progress-track');
    const markers = document.querySelectorAll('.marker');
    const fullscreenBtn = document.getElementById('fullscreen-btn');

    if (playBtn) {
        playBtn.addEventListener('click', togglePlay);
    }

    if (videoPlayer) {
        videoPlayer.addEventListener('click', function(e) {
            if (!e.target.closest('.player-controls') && !e.target.closest('.control-btn')) {
                togglePlay();
            }
        });
    }

    if (progressTrack) {
        progressTrack.addEventListener('click', function(e) {
            const rect = this.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const percent = (x / rect.width) * 100;
            updateProgress(percent);
        });
    }

    markers.forEach(marker => {
        marker.addEventListener('click', function(e) {
            e.stopPropagation();
            const position = this.dataset.position;
            const title = this.dataset.title;
            const time = this.dataset.time;
            updateProgress(parseFloat(position));
            showToast(`📍 跳转到：${title} (${time})`, 'info');
        });
    });

    if (fullscreenBtn) {
        fullscreenBtn.addEventListener('click', toggleFullscreen);
    }

    document.addEventListener('keydown', function(e) {
        if (e.code === 'Space' && e.target.tagName !== 'INPUT') {
            e.preventDefault();
            togglePlay();
        }
    });

    initProgressAnimation();
}

function togglePlay() {
    isPlaying = !isPlaying;
    const playIcon = document.querySelector('.icon-play');
    const pauseIcon = document.querySelector('.icon-pause');

    if (isPlaying) {
        playIcon.classList.add('hidden');
        pauseIcon.classList.remove('hidden');
        showToast('▶️ 播放中', 'success');
        startProgressSimulation();
    } else {
        playIcon.classList.remove('hidden');
        pauseIcon.classList.add('hidden');
        showToast('⏸️ 已暂停', 'info');
        stopProgressSimulation();
    }
}

let progressInterval = null;

function startProgressSimulation() {
    stopProgressSimulation();
    progressInterval = setInterval(() => {
        if (currentProgress < 100) {
            currentProgress += 0.5;
            updateProgress(currentProgress);
            updateTimeDisplay();
        } else {
            stopProgressSimulation();
            showToast('🎉 课程完成！', 'success');
        }
    }, 1000);
}

function stopProgressSimulation() {
    if (progressInterval) {
        clearInterval(progressInterval);
        progressInterval = null;
    }
}

function updateProgress(percent) {
    currentProgress = Math.min(100, Math.max(0, percent));

    const progressFill = document.getElementById('progress-fill');
    const progressThumb = document.getElementById('progress-thumb');

    if (progressFill) {
        progressFill.style.width = currentProgress + '%';
    }
    if (progressThumb) {
        progressThumb.style.left = currentProgress + '%';
    }

    updateActiveMarker();
}

function updateTimeDisplay() {
    const totalSeconds = 45 * 60 + 30;
    const currentSeconds = Math.floor((currentProgress / 100) * totalSeconds);
    const minutes = Math.floor(currentSeconds / 60);
    const seconds = currentSeconds % 60;

    const currentTimeEl = document.querySelector('.current-time');
    if (currentTimeEl) {
        currentTimeEl.textContent = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    }
}

function updateActiveMarker() {
    const markers = document.querySelectorAll('.marker');
    markers.forEach(marker => {
        const position = parseFloat(marker.dataset.position);
        if (currentProgress >= position) {
            marker.classList.add('active');
        } else {
            marker.classList.remove('active');
        }
    });
}

function toggleFullscreen() {
    const videoPlayer = document.getElementById('video-player');
    if (!document.fullscreenElement) {
        videoPlayer.requestFullscreen().then(() => {
            showToast('📺 全屏模式', 'info');
        }).catch(err => {
            showToast('无法进入全屏', 'error');
        });
    } else {
        document.exitFullscreen();
        showToast('📱 退出全屏', 'info');
    }
}

function initProgressAnimation() {
    updateActiveMarker();
}

function initChapterList() {
    const chapters = document.querySelectorAll('.chapter-item');

    chapters.forEach(chapter => {
        chapter.addEventListener('click', function() {
            if (this.classList.contains('locked')) {
                showToast('🔒 完成当前章节后解锁', 'warning');
                return;
            }

            const chapterNum = this.dataset.chapter;
            if (chapterNum != currentChapter) {
                showToast(`📖 切换到第 ${chapterNum} 章`, 'info');
            }
        });
    });
}

function initAICompanion() {
    const inputField = document.querySelector('.input-field');
    const sendBtn = document.querySelector('.send-btn');

    if (sendBtn) {
        sendBtn.addEventListener('click', sendMessage);
    }

    if (inputField) {
        inputField.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
    }
}

function sendMessage() {
    const inputField = document.querySelector('.input-field');
    const message = inputField.value.trim();

    if (!message) return;

    const messagesContainer = document.querySelector('.companion-messages');

    const userMessage = document.createElement('div');
    userMessage.className = 'message user';
    userMessage.innerHTML = `
        <p class="message-text">${escapeHtml(message)}</p>
        <span class="message-icon">👤</span>
    `;
    userMessage.style.cssText = `
        display: flex;
        gap: 10px;
        justify-content: flex-end;
        margin-bottom: 12px;
    `;
    userMessage.querySelector('.message-text').style.cssText = `
        background: rgba(168, 85, 247, 0.2);
        border-radius: 12px 12px 4px 12px;
    `;

    messagesContainer.appendChild(userMessage);

    inputField.value = '';

    showTypingIndicator();

    setTimeout(() => {
        removeTypingIndicator();
        const botMessage = document.createElement('div');
        botMessage.className = 'message bot';
        botMessage.innerHTML = `
            <span class="message-icon">🤖</span>
            <p class="message-text">这是关于算法复杂度的问题，核心知识点是时间复杂度 O(n) 和空间复杂度 O(1)。建议你先理解大 O 表示法的定义，再通过实际代码分析加深理解。</p>
        `;
        messagesContainer.appendChild(botMessage);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }, 1500);
}

function showTypingIndicator() {
    const messagesContainer = document.querySelector('.companion-messages');
    const typing = document.createElement('div');
    typing.className = 'message bot typing';
    typing.innerHTML = `
        <span class="message-icon">🤖</span>
        <p class="message-text">...</p>
    `;
    typing.style.cssText = `
        display: flex;
        gap: 10px;
        margin-bottom: 12px;
    `;
    messagesContainer.appendChild(typing);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function removeTypingIndicator() {
    const typing = document.querySelector('.message.typing');
    if (typing) typing.remove();
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
    toast.style.cssText = `
        padding: 14px 20px;
        background: rgba(20, 20, 40, 0.95);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
        color: #fff;
        font-size: 14px;
        animation: slideIn 0.3s ease;
        backdrop-filter: blur(20px);
    `;

    const colors = {
        success: 'rgba(16, 185, 129, 0.4)',
        error: 'rgba(239, 68, 68, 0.4)',
        warning: 'rgba(249, 115, 22, 0.4)',
        info: 'rgba(59, 130, 246, 0.4)'
    };
    toast.style.borderColor = colors[type] || colors.info;
    toast.textContent = message;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100px)';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}