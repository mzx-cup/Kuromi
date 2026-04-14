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
// URL Parameter Parser (课程中心跳转参数解析)
// ============================================
function parseCourseParams() {
    const params = new URLSearchParams(window.location.search);
    const courseId = params.get('course_id');
    const action = params.get('action');
    const courseName = params.get('course_name');
    const lastChapter = params.get('last_chapter');
    const progress = params.get('progress');
    const outline = params.get('outline');

    if (courseId) {
        console.log(`[Hub] 接收到课程参数: course_id=${courseId}, action=${action}`);
        console.log(`[Hub] 课程名称: ${courseName || '未知'}`);

        const header = document.querySelector('.hub-header');
        if (header && courseName) {
            const titleEl = header.querySelector('h1') || header.querySelector('.title');
            if (titleEl) {
                titleEl.textContent = `${courseName} - 学习中心`;
            }
        }

        if (action === 'continue' && lastChapter) {
            const decodedChapter = decodeURIComponent(lastChapter);
            console.log(`[Hub] 继续学习，上次章节: ${decodedChapter}`);
            showToast(`📚 继续学习: ${decodedChapter}`, 'info');
        }

        if (action === 'start' && outline) {
            try {
                const outlineItems = JSON.parse(decodeURIComponent(outline));
                console.log(`[Hub] 课程大纲:`, outlineItems);
            } catch (e) {
                console.warn('[Hub] 无法解析课程大纲参数');
            }
        }
    }
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
// 全息知识生态 - 树状金字塔布局
// ============================================
function initHoloEcosystem() {
    const container = document.getElementById('holoTree');
    const nodesContainer = document.getElementById('holoNodes');

    if (!container || !nodesContainer) return;

    const nodes = nodesContainer.querySelectorAll('.holo-node');
    nodes.forEach((node, index) => {
        node.style.animationDelay = (0.1 + index * 0.1) + 's';
    });

    drawTreeConnections();

    let resizeTimeout;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(drawTreeConnections, 100);
    });
}

// 绘制树状金字塔的 SVG 连线
function drawTreeConnections() {
    const svgContainer = document.getElementById('holoConnections');
    const nodesContainer = document.getElementById('holoNodes');

    if (!svgContainer || !nodesContainer) return;

    const rootNode = nodesContainer.querySelector('.node-root');
    const branchNodes = nodesContainer.querySelectorAll('.node-branch');
    const leafNodes = nodesContainer.querySelectorAll('.node-leaf');

    if (!rootNode) return;

    svgContainer.innerHTML = `
        <defs>
            <linearGradient id="lineGradientHealthy" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="rgba(52, 211, 153, 0.6)"/>
                <stop offset="100%" stop-color="rgba(52, 211, 153, 0.3)"/>
            </linearGradient>
            <linearGradient id="lineGradientWarning" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="rgba(251, 191, 36, 0.6)"/>
                <stop offset="100%" stop-color="rgba(251, 191, 36, 0.3)"/>
            </linearGradient>
            <linearGradient id="lineGradientDanger" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="rgba(248, 113, 113, 0.6)"/>
                <stop offset="100%" stop-color="rgba(248, 113, 113, 0.3)"/>
            </linearGradient>
            <filter id="glow">
                <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
                <feMerge>
                    <feMergeNode in="coloredBlur"/>
                    <feMergeNode in="SourceGraphic"/>
                </feMerge>
            </filter>
        </defs>
    `;

    svgContainer.setAttribute('viewBox', '0 0 100 100');
    svgContainer.setAttribute('preserveAspectRatio', 'xMidYMid meet');

    const containerRect = nodesContainer.getBoundingClientRect();
    const containerWidth = containerRect.width;
    const containerHeight = containerRect.height;

    function getNodeCenter(node) {
        const rect = node.getBoundingClientRect();
        const containerRect = nodesContainer.getBoundingClientRect();
        const x = ((rect.left + rect.width / 2) - containerRect.left) / containerWidth * 100;
        const y = ((rect.top + rect.height / 2) - containerRect.top) / containerHeight * 100;
        return { x, y };
    }

    function getNodeStatus(node) {
        return node.dataset.status || 'healthy';
    }

    branchNodes.forEach((branchNode) => {
        const rootCenter = getNodeCenter(rootNode);
        const branchCenter = getNodeCenter(branchNode);
        const status = getNodeStatus(branchNode);

        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        const midY = (rootCenter.y + branchCenter.y) / 2;
        const d = `M${rootCenter.x} ${rootCenter.y} Q${rootCenter.x} ${midY} ${branchCenter.x} ${branchCenter.y - 10}`;

        path.setAttribute('d', d);
        path.setAttribute('class', `connection-line ${status}`);
        path.setAttribute('filter', 'url(#glow)');
        path.style.opacity = '0';
        path.style.strokeWidth = '1';
        path.style.fill = 'none';

        svgContainer.appendChild(path);

        setTimeout(() => {
            path.style.transition = 'opacity 0.5s ease';
            path.style.opacity = '0.6';
        }, 300 + Math.random() * 300);
    });

    leafNodes.forEach((leafNode) => {
        const parentId = leafNode.dataset.parent;
        const parentNode = nodesContainer.querySelector(`[data-id="${parentId}"]`);
        if (!parentNode) return;

        const parentCenter = getNodeCenter(parentNode);
        const leafCenter = getNodeCenter(leafNode);
        const status = getNodeStatus(leafNode);

        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        const midY = (parentCenter.y + leafCenter.y) / 2;
        const d = `M${parentCenter.x} ${parentCenter.y} Q${parentCenter.x} ${midY} ${leafCenter.x} ${leafCenter.y - 10}`;

        path.setAttribute('d', d);
        path.setAttribute('class', `connection-line ${status}`);
        path.setAttribute('filter', 'url(#glow)');
        path.style.opacity = '0';
        path.style.strokeWidth = '0.8';
        path.style.fill = 'none';

        svgContainer.appendChild(path);

        setTimeout(() => {
            path.style.transition = 'opacity 0.5s ease';
            path.style.opacity = '0.5';
        }, 400 + Math.random() * 300);
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
    parseCourseParams();
    initHoloEcosystem();
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