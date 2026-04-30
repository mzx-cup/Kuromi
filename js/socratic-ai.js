document.addEventListener('DOMContentLoaded', function() {
    initRoleToggle();
    initVoiceControls();
    initMicConsole();
    initHistoryPanel();
    initScoreResult();
    initSpeechRecognition();
    initManualInput();

    // 初始化：加载角色并获取第一个问题
    loadInitialQuestion();
});

let currentRole = 'teacher';
let currentQuestion = null;
let currentQuestionNumber = 1;
let selectedVoiceId = 0;
let isPlayingAudio = false;
let isRecording = false;
let recordingTimer = null;
let speechRecognizer = null;
let conversationHistory = [];
let mediaRecorder = null;
let audioChunks = [];
let autoPlayEnabled = true;
let finalTranscript = '';

// ========== 角色切换 ==========

function initRoleToggle() {
    const teacherBtn = document.getElementById('role-teacher');
    const interviewerBtn = document.getElementById('role-interviewer');

    teacherBtn.addEventListener('click', () => switchRole('teacher'));
    interviewerBtn.addEventListener('click', () => switchRole('interviewer'));
}

async function switchRole(role) {
    if (role === currentRole) return;

    currentRole = role;
    currentQuestionNumber = 1;

    // 更新按钮状态
    document.querySelectorAll('.role-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.role === role);
    });

    // 更新 Orb 状态
    updateOrbStatus('切换角色中...');

    // 获取新角色的问题
    await fetchNewQuestion();

    // 更新提示
    showToast(`已切换到${role === 'teacher' ? '老师' : '面试'}模式`, 'info');
}

async function loadInitialQuestion() {
    updateOrbStatus('准备中...');

    try {
        const response = await fetch('/api/socratic/role', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ role: currentRole })
        });

        const data = await response.json();
        if (data.success) {
            updateQuestion(data.question);
            hideScoreResult();
            if (autoPlayEnabled) {
                setTimeout(() => playQuestionVoice(), 500);
            }
        }
    } catch (error) {
        console.error('获取问题失败:', error);
        showToast('获取问题失败，请刷新重试', 'error');
    }

    updateOrbStatus('倾听中');
}

async function fetchNewQuestion() {
    try {
        const response = await fetch('/api/socratic/question', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ role: currentRole })
        });

        const data = await response.json();
        if (data.success) {
            updateQuestion(data.question);
            hideScoreResult();
            if (autoPlayEnabled) {
                setTimeout(() => playQuestionVoice(), 500);
            }
        }
    } catch (error) {
        console.error('获取新问题失败:', error);
        showToast('获取新问题失败', 'error');
    }
}

function updateQuestion(question) {
    currentQuestion = question;

    const transcriptContainer = document.getElementById('transcript-container');
    const transcriptText = document.getElementById('transcript-text');
    const questionNumber = document.getElementById('question-number');
    const hintText = document.getElementById('hint-text');

    // 淡出
    transcriptContainer.style.animation = 'transcriptFadeOut 0.3s ease-out forwards';

    setTimeout(() => {
        if (questionNumber) questionNumber.textContent = question.number || `Q${currentQuestionNumber}`;
        if (transcriptText) transcriptText.textContent = question.text;
        if (hintText) {
            hintText.querySelector('p').textContent = '💡 提示：' + question.hint;
        }

        // 淡入
        transcriptContainer.style.animation = 'transcriptFadeIn 0.5s ease-out forwards';
    }, 300);
}

// ========== 语音控制 ==========

function initVoiceControls() {
    const voiceBtn = document.getElementById('voice-btn');
    const voiceDropdown = document.getElementById('voice-dropdown');
    const autoPlayToggle = document.getElementById('auto-play-toggle');

    voiceBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        voiceDropdown.classList.toggle('hidden');
    });

    document.addEventListener('click', () => {
        voiceDropdown.classList.add('hidden');
    });

    document.querySelectorAll('.voice-option').forEach(option => {
        option.addEventListener('click', (e) => {
            e.stopPropagation();
            const voiceId = parseInt(option.dataset.voice);
            selectVoice(voiceId);
            voiceDropdown.classList.add('hidden');
        });
    });

    if (autoPlayToggle) {
        autoPlayToggle.addEventListener('change', (e) => {
            autoPlayEnabled = e.target.checked;
        });
    }
}

function selectVoice(voiceId) {
    selectedVoiceId = voiceId;

    document.querySelectorAll('.voice-option').forEach(opt => {
        opt.classList.toggle('selected', parseInt(opt.dataset.voice) === voiceId);
    });
}

async function playQuestionVoice() {
    if (isPlayingAudio || !currentQuestion) return;

    const voiceBtn = document.getElementById('voice-btn');
    voiceBtn.classList.add('playing');
    isPlayingAudio = true;
    updateOrbStatus('AI 播声中...');

    try {
        const response = await fetch('/api/socratic/tts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: currentQuestion.text,
                voice_id: selectedVoiceId
            })
        });

        const data = await response.json();
        if (data.success && data.audio_url) {
            const audio = new Audio(data.audio_url);
            audio.onended = () => {
                voiceBtn.classList.remove('playing');
                isPlayingAudio = false;
                updateOrbStatus('倾听中');
            };
            audio.onerror = () => {
                voiceBtn.classList.remove('playing');
                isPlayingAudio = false;
                updateOrbStatus('倾听中');
                showToast('语音播放失败', 'error');
            };
            await audio.play();
        } else {
            showToast(data.error || '语音合成失败', 'error');
            voiceBtn.classList.remove('playing');
            isPlayingAudio = false;
        }
    } catch (error) {
        console.error('TTS 播放失败:', error);
        showToast('语音播放失败', 'error');
        voiceBtn.classList.remove('playing');
        isPlayingAudio = false;
    }

    updateOrbStatus('倾听中');
}

// ========== 麦克风控制 ==========

function initMicConsole() {
    const micBtn = document.getElementById('mic-btn');

    if (!micBtn) return;

    micBtn.addEventListener('mousedown', startRecording);
    micBtn.addEventListener('mouseup', stopRecording);
    micBtn.addEventListener('mouseleave', stopRecording);

    micBtn.addEventListener('touchstart', function(e) {
        e.preventDefault();
        startRecording();
    });

    micBtn.addEventListener('touchend', function(e) {
        e.preventDefault();
        stopRecording();
    });

    document.addEventListener('keydown', function(e) {
        if (e.code === 'Space' && e.target.tagName !== 'INPUT' && !isRecording) {
            e.preventDefault();
            startRecording();
        }
    });

    document.addEventListener('keyup', function(e) {
        if (e.code === 'Space' && isRecording) {
            e.preventDefault();
            stopRecording();
        }
    });
}

function startRecording() {
    if (isRecording) return;

    finalTranscript = '';
    isRecording = true;
    audioChunks = [];
    document.body.classList.add('recording');

    const micLabel = document.getElementById('mic-label');
    if (micLabel) {
        micLabel.innerHTML = '<span class="label-text" style="color: #ef4444;">正在录音...</span>';
    }

    updateOrbStatus('聆听中');

    // 开始 MediaRecorder 录音
    if (mediaRecorder && mediaRecorder.state === 'inactive') {
        mediaRecorder.start();
    }

    showToast('🎙️ 开始录音，请回答问题', 'info');

    recordingTimer = setTimeout(() => {
        stopRecording();
    }, 60000); // 60秒超时
}

async function stopRecording() {
    if (!isRecording) return;

    isRecording = false;
    document.body.classList.remove('recording');

    if (recordingTimer) {
        clearTimeout(recordingTimer);
        recordingTimer = null;
    }

    const micLabel = document.getElementById('mic-label');
    if (micLabel) {
        micLabel.innerHTML = '<span class="label-text">长按说话</span>';
    }

    // 停止 MediaRecorder 录音
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
    }

    // 等待录音数据合并后发送
    setTimeout(async () => {
        if (audioChunks.length === 0) {
            showToast('未检测到语音，请重试', 'warning');
            updateTranscriptionDisplay('（未识别到语音）');
            processAnswer('');
            return;
        }

        showResponseIndicator();
        updateOrbStatus('AI 评分中...');
        showToast('🎙️ 录音结束，AI 正在分析...', 'info');

        // 将音频发送给后端进行 ASR
        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
        try {
            const formData = new FormData();
            formData.append('audio', audioBlob, 'recording.webm');

            const response = await fetch('/api/socratic/asr', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            const recognizedText = data.text || '';
            updateTranscriptionDisplay(recognizedText);
            processAnswer(recognizedText);
        } catch (error) {
            console.error('ASR 请求失败:', error);
            showToast('语音识别失败，请手动输入', 'error');
            updateTranscriptionDisplay('（语音识别失败）');
            processAnswer('');
        }

        audioChunks = [];
    }, 500);
}

function showResponseIndicator() {
    const indicator = document.getElementById('response-indicator');
    const audioViz = document.getElementById('audio-visualizer');

    if (indicator) indicator.classList.remove('hidden');
    if (audioViz) audioViz.classList.remove('hidden');
}

function hideResponseIndicator() {
    const indicator = document.getElementById('response-indicator');
    const audioViz = document.getElementById('audio-visualizer');

    if (indicator) indicator.classList.add('hidden');
    if (audioViz) audioViz.classList.add('hidden');
}

// ========== 语音转文字状态面板 ==========

function updateTranscriptionDisplay(text) {
    const panel = document.getElementById('transcription-panel');
    if (!panel) return;

    const recognizedEl = document.getElementById('transcription-recognized');
    const toAIEI = document.getElementById('transcription-to-ai');

    if (recognizedEl) recognizedEl.textContent = text || '（未识别到文字）';
    if (toAIEI) toAIEI.textContent = text || '（未识别到文字）';

    panel.classList.remove('hidden');
    panel.style.animation = 'transcriptFadeIn 0.3s ease';

    // 3秒后自动隐藏
    setTimeout(() => {
        panel.classList.add('hidden');
    }, 5000);
}

// ========== 语音识别（使用 MediaRecorder + 后端 ASR） ==========

async function initSpeechRecognition() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        console.warn('浏览器不支持录音');
        return;
    }

    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

        // 尝试使用 wav 格式（Chrome 支持），否则回退到 webm
        let mimeType = 'audio/webm;codecs=opus';
        if (MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported('audio/wav')) {
            mimeType = 'audio/wav';
        } else if (MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
            mimeType = 'audio/webm;codecs=opus';
        }

        console.log('使用录音格式:', mimeType);
        mediaRecorder = new MediaRecorder(stream, { mimeType: mimeType });
        audioChunks = [];

        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        };

        mediaRecorder.onerror = (event) => {
            console.error('录音错误:', event);
            showToast('录音出错，请重试', 'error');
        };

    } catch (e) {
        console.error('获取麦克风权限失败:', e);
        showToast('无法访问麦克风，请检查权限设置', 'error');
    }
}

// ========== 手动输入降级 ==========

function initManualInput() {
    const manualInputRow = document.getElementById('manual-input-row');
    const manualInput = document.getElementById('manual-answer-input');
    const manualSubmitBtn = document.getElementById('manual-submit-btn');

    if (!manualInputRow || !manualInput || !manualSubmitBtn) return;

    manualSubmitBtn.addEventListener('click', () => {
        const text = manualInput.value.trim();
        if (text) {
            manualInput.value = '';
            showResponseIndicator();
            updateOrbStatus('AI 评分中...');
            updateTranscriptionDisplay(text);
            processAnswer(text);
        }
    });

    manualInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            manualSubmitBtn.click();
        }
    });
}

function showManualInput() {
    const manualInputRow = document.getElementById('manual-input-row');
    if (manualInputRow) {
        manualInputRow.style.display = 'flex';
    }
}

// ========== AI 评分 ==========

async function processAnswer(transcribedText = '') {
    hideResponseIndicator();

    if (!currentQuestion) {
        showToast('问题加载中，请稍后', 'error');
        return;
    }

    // 如果没有转写文本，使用模拟文本
    const answerText = transcribedText || '（用户未作答）';

    try {
        const response = await fetch('/api/socratic/score', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                role: currentRole,
                question: currentQuestion.text,
                answer: answerText
            })
        });

        const data = await response.json();
        if (data.success) {
            showScoreResult(data.score, data.feedback);

            // 添加到历史记录
            addToHistory({
                number: currentQuestion.number || `Q${currentQuestionNumber}`,
                question: currentQuestion.text,
                answer: answerText,
                score: data.score,
                feedback: data.feedback,
                role: currentRole
            });

            showToast(`📊 回答评估完成，得分：${data.score}分`, data.score >= 85 ? 'success' : 'info');

            // 更新学生画像
            StarData.updatePortrait('socratic', {
                question: currentQuestion.text,
                answer: answerText,
                score: data.score,
                feedback: data.feedback,
                role: currentRole
            });
        } else {
            showToast('评分失败', 'error');
        }
    } catch (error) {
        console.error('评分请求失败:', error);
        showToast('评分请求失败', 'error');
    }

    updateOrbStatus('倾听中');

    // 2秒后获取新问题
    setTimeout(() => {
        currentQuestionNumber++;
        fetchNewQuestion();
    }, 3000);
}

// ========== 评分结果 ==========

function initScoreResult() {
    // 评分结果区域初始隐藏
}

function showScoreResult(score, feedback) {
    const scoreResult = document.getElementById('score-result');
    const scoreNumber = document.getElementById('score-number');
    const scoreFeedback = document.getElementById('score-feedback');

    if (scoreNumber) scoreNumber.textContent = score;
    if (scoreFeedback) scoreFeedback.textContent = feedback;

    scoreResult.classList.remove('hidden');
    scoreResult.style.animation = 'none';
    scoreResult.offsetHeight; // 触发重排
    scoreResult.style.animation = 'scoreReveal 0.5s ease';
}

function hideScoreResult() {
    const scoreResult = document.getElementById('score-result');
    if (scoreResult) {
        scoreResult.classList.add('hidden');
    }
}

// ========== 历史记录 ==========

function initHistoryPanel() {
    const historyToggle = document.getElementById('history-toggle');
    const historyPanel = document.getElementById('history-panel');
    const closeBtn = document.getElementById('close-history');

    if (historyToggle) {
        historyToggle.addEventListener('click', () => {
            historyPanel.classList.toggle('hidden');
        });
    }

    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            historyPanel.classList.add('hidden');
        });
    }
}

function addToHistory(item) {
    conversationHistory.unshift(item);

    const historyList = document.getElementById('history-list');
    const historyItem = document.createElement('div');
    historyItem.className = 'history-item';
    historyItem.innerHTML = `
        <span class="history-q">${item.number}</span>
        <p class="history-question">${item.question.substring(0, 50)}${item.question.length > 50 ? '...' : ''}</p>
        <div class="history-score">
            <span class="score-label">得分</span>
            <span class="score-value">${item.score}</span>
        </div>
    `;

    historyList.insertBefore(historyItem, historyList.firstChild);
}

// ========== Orb 状态 ==========

function updateOrbStatus(status) {
    const orbStatus = document.getElementById('orb-status');
    if (orbStatus) {
        orbStatus.textContent = status;
    }
}

// ========== Toast 提示 ==========

function showToast(message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = `
            position: fixed;
            bottom: 160px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 9999;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 12px;
        `;
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.style.cssText = `
        padding: 14px 24px;
        background: rgba(20, 20, 40, 0.95);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
        color: #fff;
        font-size: 14px;
        font-weight: 500;
        animation: toastFadeIn 0.3s ease;
        backdrop-filter: blur(20px);
        white-space: nowrap;
    `;

    const colors = {
        success: 'rgba(16, 185, 129, 0.4)',
        error: 'rgba(239, 68, 68, 0.4)',
        warning: 'rgba(249, 115, 22, 0.4)',
        info: 'rgba(168, 85, 247, 0.4)'
    };
    toast.style.borderColor = colors[type] || colors.info;
    toast.textContent = message;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(20px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ========== 样式注入 ==========

const style = document.createElement('style');
style.textContent = `
    @keyframes toastFadeIn {
        from { opacity: 0; transform: translateY(-20px); }
        to { opacity: 1; transform: translateY(0); }
    }

    @keyframes transcriptFadeOut {
        from { opacity: 1; transform: translateY(0); }
        to { opacity: 0; transform: translateY(-10px); }
    }

    @keyframes transcriptFadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }

    @keyframes scoreReveal {
        from { opacity: 0; transform: scale(0.9); }
        to { opacity: 1; transform: scale(1); }
    }

    .hidden { display: none !important; }
`;
document.head.appendChild(style);
