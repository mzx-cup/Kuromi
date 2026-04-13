document.addEventListener('DOMContentLoaded', function() {
    initMicConsole();
    initHistoryPanel();
});

let isRecording = false;
let recordingTimer = null;
let currentQuestionIndex = 0;

const questions = [
    {
        number: 'Q1',
        text: '请解释一下 Apache Flink 中 Checkpoint 的对齐机制，当发生故障恢复时，系统如何确保状态一致性？',
        hint: '建议从 Checkpoint 的必要性、Chandy-Lamport 算法、对齐过程三个角度回答'
    },
    {
        number: 'Q2',
        text: '在分布式系统中，如何解决消息传递的幂等性问题？请举例说明',
        hint: '考虑消息重复发送、网络故障等场景'
    },
    {
        number: 'Q3',
        text: '解释一下 CAP 理论中的分区容错性，为什么在分布式系统中必须保证 P？',
        hint: '结合实际分布式系统（如 Kafka、HBase）分析'
    }
];

function initMicConsole() {
    const micBtn = document.getElementById('mic-btn');
    const body = document.body;

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

    isRecording = true;
    const body = document.body;
    body.classList.add('recording');

    const micLabel = document.getElementById('mic-label');
    if (micLabel) {
        micLabel.innerHTML = '<span class="label-text" style="color: #ef4444;">正在录音...</span>';
    }

    const orbStatus = document.getElementById('orb-status');
    if (orbStatus) {
        orbStatus.textContent = '聆听中';
    }

    showToast('🎙️ 开始录音，请回答问题', 'info');

    recordingTimer = setTimeout(function() {
        stopRecording();
    }, 30000);
}

function stopRecording() {
    if (!isRecording) return;

    isRecording = false;
    const body = document.body;
    body.classList.remove('recording');

    if (recordingTimer) {
        clearTimeout(recordingTimer);
        recordingTimer = null;
    }

    const micLabel = document.getElementById('mic-label');
    if (micLabel) {
        micLabel.innerHTML = '<span class="label-text">长按说话</span>';
    }

    showResponseIndicator();

    showToast('🎙️ 录音结束，AI 正在分析...', 'info');

    setTimeout(function() {
        processAnswer();
    }, 3000);
}

function showResponseIndicator() {
    const indicator = document.getElementById('response-indicator');
    const audioViz = document.getElementById('audio-visualizer');

    if (indicator) {
        indicator.classList.remove('hidden');
    }

    if (audioViz) {
        audioViz.classList.remove('hidden');
    }
}

function hideResponseIndicator() {
    const indicator = document.getElementById('response-indicator');
    const audioViz = document.getElementById('audio-visualizer');

    if (indicator) {
        indicator.classList.add('hidden');
    }

    if (audioViz) {
        audioViz.classList.add('hidden');
    }
}

function processAnswer() {
    hideResponseIndicator();

    const score = Math.floor(Math.random() * 20) + 80;
    showToast(`📊 回答评估完成，得分：${score}分`, score >= 90 ? 'success' : 'info');

    setTimeout(function() {
        moveToNextQuestion();
    }, 2000);
}

function moveToNextQuestion() {
    currentQuestionIndex++;

    if (currentQuestionIndex >= questions.length) {
        showToast('🎉 所有问题已完成！', 'success');
        currentQuestionIndex = 0;
        return;
    }

    const question = questions[currentQuestionIndex];

    const transcriptContainer = document.getElementById('transcript-container');
    const transcriptText = document.getElementById('transcript-text');
    const questionNumber = document.querySelector('.question-number');
    const hintText = document.getElementById('hint-text');

    transcriptContainer.style.animation = 'transcriptFadeOut 0.3s ease-out forwards';

    setTimeout(function() {
        if (questionNumber) questionNumber.textContent = question.number;
        if (transcriptText) transcriptText.textContent = question.text;

        if (hintText) {
            hintText.querySelector('p').textContent = '💡 提示：' + question.hint;
        }

        transcriptContainer.style.animation = 'transcriptFadeIn 0.5s ease-out forwards';
    }, 300);

    const orbStatus = document.getElementById('orb-status');
    if (orbStatus) {
        orbStatus.textContent = '倾听中';
    }
}

function initHistoryPanel() {
    const historyToggle = document.getElementById('history-toggle');
    const historyPanel = document.getElementById('history-panel');
    const closeBtn = document.getElementById('close-history');

    if (historyToggle) {
        historyToggle.addEventListener('click', function() {
            historyPanel.classList.toggle('hidden');
        });
    }

    if (closeBtn) {
        closeBtn.addEventListener('click', function() {
            historyPanel.classList.add('hidden');
        });
    }
}

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

const style = document.createElement('style');
style.textContent = `
    @keyframes toastFadeIn {
        from {
            opacity: 0;
            transform: translateY(-20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    @keyframes transcriptFadeOut {
        from {
            opacity: 1;
            transform: translateY(0);
        }
        to {
            opacity: 0;
            transform: translateY(-10px);
        }
    }
`;
document.head.appendChild(style);