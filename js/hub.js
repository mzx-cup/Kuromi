// ============================================
// Data Particle Animation
// ============================================
function createDataParticles() {
    const bg = document.getElementById('hub-bg');
    if (!bg) return;

    const particleCount = 30;

    for (let i = 0; i < particleCount; i++) {
        const particle = document.createElement('div');
        particle.className = 'data-particle';

        const size = Math.random() * 4 + 2;
        const left = Math.random() * 100;
        const duration = Math.random() * 20 + 15;
        const delay = Math.random() * 20;

        const colors = [
            'rgba(168, 85, 247, 0.6)',
            'rgba(59, 130, 246, 0.6)',
            'rgba(16, 185, 129, 0.6)',
            'rgba(249, 115, 22, 0.6)',
            'rgba(236, 72, 153, 0.6)'
        ];

        particle.style.cssText = `
            width: ${size}px;
            height: ${size}px;
            left: ${left}%;
            background: ${colors[Math.floor(Math.random() * colors.length)]};
            animation-duration: ${duration}s;
            animation-delay: -${delay}s;
        `;

        bg.appendChild(particle);
    }
}

// ============================================
// Daily Adaptive Route (今日星际航线)
// ============================================
function initDailyRoute() {
    const launchBtn = document.getElementById('launch-btn');
    const pathNodes = document.querySelectorAll('.path-node');

    if (launchBtn) {
        launchBtn.addEventListener('click', handleLaunch);
    }

    pathNodes.forEach(node => {
        node.addEventListener('click', () => handleNodeClick(node));
    });
}

function handleLaunch() {
    const launchBtn = document.getElementById('launch-btn');
    const currentNode = document.querySelector('.path-node.current');

    launchBtn.style.transform = 'scale(0.95)';

    setTimeout(() => {
        launchBtn.style.transform = '';
        showLaunchAnimation();

        if (currentNode) {
            const taskName = currentNode.dataset.task;
            showToast(`🚀 启动 "${taskName}" 学习任务！`, 'success');
        }
    }, 150);
}

function showLaunchAnimation() {
    const card = document.querySelector('.mothership-card');
    if (!card) return;

    card.style.boxShadow = `
        0 25px 50px -12px rgba(0, 0, 0, 0.5),
        0 0 80px rgba(168, 85, 247, 0.4),
        inset 0 1px 0 rgba(255, 255, 255, 0.2)
    `;

    setTimeout(() => {
        card.style.boxShadow = `
            0 25px 50px -12px rgba(0, 0, 0, 0.5),
            0 0 40px rgba(99, 102, 241, 0.15),
            inset 0 1px 0 rgba(255, 255, 255, 0.1)
        `;
    }, 1000);
}

function handleNodeClick(node) {
    if (node.classList.contains('completed')) {
        showToast('⏪ 回顾已完成的任务', 'info');
        return;
    }

    if (node.classList.contains('current')) {
        const taskName = node.dataset.task;
        showToast(`⚡ 继续 "${taskName}"`, 'success');
        return;
    }

    if (node.classList.contains('pending')) {
        const taskName = node.dataset.task;
        showToast(`📋 已记录 "${taskName}" 任务待完成`, 'info');
    }
}

// ============================================
// 星际自习大厅 (Interstellar Study Hall)
// ============================================
function initStudyHall() {
    const joinBtn = document.getElementById('join-study-btn');
    const peerPods = document.querySelectorAll('.peer-pod');

    if (joinBtn) {
        joinBtn.addEventListener('click', handleJoinStudy);
        initMagneticEffect(joinBtn);
    }

    peerPods.forEach(pod => {
        pod.addEventListener('click', () => handlePeerClick(pod));
    });
}

function initMagneticEffect(btn) {
    btn.addEventListener('mousemove', (e) => {
        const rect = btn.getBoundingClientRect();
        const x = ((e.clientX - rect.left) / rect.width) * 100;
        const y = ((e.clientY - rect.top) / rect.height) * 100;
        btn.style.setProperty('--mouse-x', `${x}%`);
        btn.style.setProperty('--mouse-y', `${y}%`);
    });
}

function handleJoinStudy() {
    showToast('🔍 正在匹配学习伙伴...', 'info');
    setTimeout(() => {
        showToast('🎉 成功匹配到 3 位学习伙伴！', 'success');
    }, 2000);
}

function handlePeerClick(pod) {
    const name = pod.querySelector('.pod-name')?.textContent || '该用户';
    const time = pod.querySelector('.pod-focus-time')?.textContent || '';

    if (pod.classList.contains('current-user')) {
        showToast('📊 这是你的专注状态', 'info');
    } else {
        showToast(`👤 查看 ${name} 的专注数据 (${time})`, 'info');
    }
}

// ============================================
// Toast Notification System
// ============================================
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

// ============================================
// Radial Progress Animation
// ============================================
function animateRadialProgress() {
    const rings = document.querySelectorAll('.radial-ring .progress');
    rings.forEach((ring, index) => {
        const offset = ring.style.strokeDashoffset;
        setTimeout(() => {
            ring.style.strokeDashoffset = offset;
        }, 300 + (index * 150));
    });
}

// ============================================
// Bar Chart Animation
// ============================================
function animateBarCharts() {
    const bars = document.querySelectorAll('.bar, .focus-bar');
    bars.forEach((bar, index) => {
        const height = bar.style.height;
        bar.style.height = '0';
        setTimeout(() => {
            bar.style.height = height;
        }, 100 + (index * 80));
    });
}

// ============================================
// Line Chart Animation
// ============================================
function animateLineChart() {
    const path = document.querySelector('.chart-path');
    const area = document.querySelector('.chart-area');
    const dots = document.querySelectorAll('.chart-dot');

    if (path) {
        const length = path.getTotalLength();
        path.style.strokeDasharray = length;
        path.style.strokeDashoffset = length;

        setTimeout(() => {
            path.style.transition = 'stroke-dashoffset 2s ease-out';
            path.style.strokeDashoffset = '0';
        }, 500);
    }

    if (area) {
        area.style.opacity = '0';
        setTimeout(() => {
            area.style.transition = 'opacity 1s ease-out';
            area.style.opacity = '1';
        }, 1500);
    }

    dots.forEach((dot, index) => {
        dot.style.opacity = '0';
        dot.style.transform = 'scale(0)';
        setTimeout(() => {
            dot.style.transition = 'all 0.3s ease-out';
            dot.style.opacity = '1';
            dot.style.transform = 'scale(1)';
        }, 2000 + (index * 100));
    });
}

// ============================================
// Initialize
// ============================================
document.addEventListener('DOMContentLoaded', function() {
    createDataParticles();
    initDailyRoute();
    initStudyHall();
    animateRadialProgress();
    animateBarCharts();
    animateLineChart();
});

// Smooth scroll for navigation
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({ behavior: 'smooth' });
        }
    });
});