// ============================================
// Data Particle Animation
// ============================================
function createDataParticles() {
    const bg = document.getElementById('hub-bg');
    if (!bg) return;

    const particleCount = 60;

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

// 今日航线状态
let dailyRouteState = {
    tasks: [],
    completed: [],
    currentIndex: 0,
    generated: false
};

// 任务类型对应的 emoji 和颜色
const TASK_TYPE_CONFIG = {
    study: { emoji: '📖', color: '#8b5cf6' },
    practice: { emoji: '⚡', color: '#f59e0b' },
    review: { emoji: '🔄', color: '#3b82f6' },
    relax: { emoji: '🌟', color: '#10b981' }
};

function initDailyRoute() {
    const launchBtn = document.getElementById('launch-btn');

    if (launchBtn) {
        launchBtn.addEventListener('click', handleLaunch);
    }

    // 页面加载时检查今日航线状态
    checkDailyRouteStatus();
}

async function checkDailyRouteStatus() {
    const user = JSON.parse(localStorage.getItem('starlearn_user') || '{}');
    if (!user.id) {
        return;
    }

    try {
        const response = await fetch(`/api/daily-route/status?userId=${user.id}`);
        const data = await response.json();

        if (data.success && data.generated) {
            dailyRouteState = {
                tasks: data.tasks || [],
                completed: data.completed || [],
                currentIndex: findCurrentIndex(data.tasks || [], data.completed || []),
                generated: true
            };
            renderDailyRoute();
        }
    } catch (e) {
        console.warn('[DailyRoute] Failed to check status:', e);
    }
}

function findCurrentIndex(tasks, completed) {
    for (let i = 0; i < tasks.length; i++) {
        if (!completed.includes(tasks[i].id)) {
            return i;
        }
    }
    return tasks.length > 0 ? tasks.length - 1 : 0;
}

async function handleLaunch() {
    const launchBtn = document.getElementById('launch-btn');
    const launchEngine = document.getElementById('launch-engine');
    const routeTip = document.getElementById('route-tip');
    const routeLoading = document.getElementById('route-loading');
    const launchBtnText = document.getElementById('launch-btn-text');

    // 如果已经生成过，直接跳转当前任务
    if (dailyRouteState.generated && dailyRouteState.tasks.length > 0) {
        const currentTask = dailyRouteState.tasks[dailyRouteState.currentIndex];
        if (currentTask) {
            showLaunchAnimation();
            showToast(`🚀 继续 "${currentTask.title}" 学习任务！`, 'success');
            navigateToTask(currentTask);
        }
        return;
    }

    // 获取用户信息
    const user = JSON.parse(localStorage.getItem('starlearn_user') || '{}');
    if (!user.id) {
        showToast('请先登录后再使用此功能', 'error');
        return;
    }

    // 显示加载状态
    if (launchBtn) launchBtn.style.transform = 'scale(0.95)';

    setTimeout(() => {
        if (launchBtn) launchBtn.style.transform = '';
    }, 150);

    // 显示加载动画
    showLaunchAnimation();

    if (routeTip) routeTip.style.display = 'none';
    if (routeLoading) routeLoading.style.display = 'flex';
    if (launchBtnText) launchBtnText.textContent = '生成中...';
    if (launchBtn) launchBtn.disabled = true;

    try {
        console.log('[DailyRoute] Starting generation for user:', user.id);
        const response = await fetch('/api/daily-route/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ userId: user.id })
        });

        console.log('[DailyRoute] Response status:', response.status);
        const data = await response.json();
        console.log('[DailyRoute] Response data:', data);

        if (data.success && data.tasks && data.tasks.length > 0) {
            dailyRouteState = {
                tasks: data.tasks || [],
                completed: [],
                currentIndex: 0,
                generated: true
            };

            // 显示通知
            showRouteGeneratedNotification(data.tasks, data.profile);

            // 渲染航线
            renderDailyRoute();

            showToast(`🎉 今日航线已生成！包含 ${data.tasks.length} 个学习任务`, 'success');
        } else {
            console.error('[DailyRoute] Invalid response:', data);
            throw new Error(data.error || '生成失败');
        }
    } catch (e) {
        console.error('[DailyRoute] Failed to generate:', e);
        showToast('航线生成失败，请重试: ' + e.message, 'error');
    } finally {
        if (routeLoading) routeLoading.style.display = 'none';
        if (routeTip) routeTip.style.display = 'block';
        if (launchBtnText) launchBtnText.textContent = '重新生成';
        if (launchBtn) launchBtn.disabled = false;
    }
}

function showRouteGeneratedNotification(tasks, profile) {
    // 使用通知系统显示
    if (window.starlearnNotifications && typeof window.starlearnNotifications.showNotification === 'function') {
        const totalTime = tasks.reduce((sum, t) => sum + (t.duration || 0), 0);
        window.starlearnNotifications.showNotification({
            title: '🚀 今日航线已生成',
            content: `根据你的学习画像，AI 为你规划了 ${tasks.length} 个任务，总计约 ${totalTime} 分钟`,
            type: 'achievement'
        });
    }
}

function renderDailyRoute() {
    const pathTimeline = document.getElementById('path-timeline');
    const progressIndicator = document.getElementById('route-progress-indicator');
    const launchEngine = document.getElementById('launch-engine');
    const launchBtnText = document.getElementById('launch-btn-text');
    const routeTip = document.getElementById('route-tip');

    if (!pathTimeline || !dailyRouteState.tasks.length) return;

    if (launchEngine) launchEngine.style.display = 'none';
    if (progressIndicator) progressIndicator.style.display = 'none';
    pathTimeline.classList.add('route-generated');

    const total = dailyRouteState.tasks.length;
    const completed = dailyRouteState.completed.length;
    const progress = total > 0 ? Math.round((completed / total) * 100) : 0;
    const totalMinutes = dailyRouteState.tasks.reduce((sum, task) => sum + (Number(task.duration) || 0), 0);
    const remainingTasks = Math.max(total - completed, 0);

    let html = `
        <div class="route-dashboard">
            <div class="daily-route-header">
                <div>
                    <span class="route-eyebrow">今日航线</span>
                    <div class="route-date">${new Date().toLocaleDateString('zh-CN', { month: 'long', day: 'numeric', weekday: 'long' })}</div>
                </div>
                <div class="route-summary">
                    <span class="route-progress-badge">${progress}%</span>
                    <span class="route-status-text">${completed}/${total} 任务完成</span>
                </div>
            </div>
            <div class="route-shell">
                <aside class="route-overview-card">
                    <span class="route-overview-label">学习流程</span>
                    <strong>${remainingTasks} 个待完成节点</strong>
                    <p>预计 ${totalMinutes} 分钟，按顺序推进，也可以左右滑动查看完整路线。</p>
                    <div class="route-progress-bar">
                        <div class="route-progress-fill" id="route-progress" style="width: ${progress}%"></div>
                    </div>
                    <div class="route-overview-stats">
                        <span><span id="completed-count">${completed}</span> 已完成</span>
                        <span><span id="total-count">${total}</span> 总任务</span>
                    </div>
                </aside>
                <div class="route-flow-panel">
                    <div class="route-flow-toolbar">
                        <div>
                            <span class="route-flow-kicker">今日学习流程</span>
                            <span class="route-flow-hint">拖动卡片或使用按钮横向浏览</span>
                        </div>
                        <div class="route-scroll-actions" aria-label="学习流程滑动控制">
                            <button class="route-scroll-btn" id="route-scroll-left" type="button" aria-label="向左查看">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M15 18l-6-6 6-6"/></svg>
                            </button>
                            <button class="route-scroll-btn" id="route-scroll-right" type="button" aria-label="向右查看">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18l6-6-6-6"/></svg>
                            </button>
                        </div>
                    </div>
                    <div class="route-viewport-frame">
                        <div class="route-edge route-edge-left"></div>
                        <div class="route-edge route-edge-right"></div>
                        <div class="route-tasks" id="route-task-scroll" tabindex="0" aria-label="今日学习流程">
    `;

    dailyRouteState.tasks.forEach((task, index) => {
        const isCompleted = dailyRouteState.completed.includes(task.id);
        const isCurrent = index === dailyRouteState.currentIndex && !isCompleted;
        const typeConfig = TASK_TYPE_CONFIG[task.type] || TASK_TYPE_CONFIG.study;

        const difficultyLabels = { easy: '简单', medium: '中等', hard: '困难' };
        const difficultyColors = { easy: '#10b981', medium: '#f59e0b', hard: '#ef4444' };
        const difficultyColor = difficultyColors[task.difficulty] || difficultyColors.medium;

        html += `
            <div class="route-task-card ${isCompleted ? 'completed' : ''} ${isCurrent ? 'current' : ''}"
                 data-task-id="${task.id}"
                 data-task-url="${task.taskUrl || 'courses.html'}"
                 onclick="handleNodeClick(${task.id})">
                <div class="task-card-header">
                    <span class="task-step">${String(index + 1).padStart(2, '0')}</span>
                    <div class="task-subject-icon" style="background: ${typeConfig.color}20; color: ${typeConfig.color}">
                        ${typeConfig.emoji}
                    </div>
                    <div class="task-header-info">
                        <span class="task-type-label">${task.type === 'study' ? '学习' : task.type === 'practice' ? '练习' : task.type === 'review' ? '复习' : '放松'}</span>
                        <span class="task-duration">⏱${task.duration}分钟</span>
                    </div>
                    ${isCompleted ? '<div class="task-completed-check"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg></div>' : ''}
                    ${isCurrent ? '<div class="task-current-badge">进行中</div>' : ''}
                </div>
                <div class="task-card-body">
                    <h4 class="task-title">${task.title}</h4>
                    <p class="task-description">${task.description}</p>
                </div>
                <div class="task-card-footer">
                    <span class="task-subject">${task.subject}</span>
                    <span class="task-difficulty" style="color: ${difficultyColor}">${difficultyLabels[task.difficulty] || '中等'}</span>
                </div>
            </div>
        `;
    });

    html += `
                        </div>
                    </div>
                    <div class="route-scrollbar" aria-hidden="true">
                        <span class="route-scroll-thumb" id="route-scroll-thumb"></span>
                    </div>
                </div>
            </div>
        </div>
    `;
    pathTimeline.innerHTML = html;

    setupRouteScroller();
    updateRouteProgress();
}

function setupRouteScroller() {
    const scroller = document.getElementById('route-task-scroll');
    const leftBtn = document.getElementById('route-scroll-left');
    const rightBtn = document.getElementById('route-scroll-right');
    const thumb = document.getElementById('route-scroll-thumb');

    if (!scroller) return;

    let isDragging = false;
    let startX = 0;
    let startScrollLeft = 0;
    let movedDuringDrag = false;

    const scrollAmount = () => Math.max(280, Math.floor(scroller.clientWidth * 0.82));

    const updateControls = () => {
        const maxScroll = Math.max(scroller.scrollWidth - scroller.clientWidth, 0);
        const atStart = scroller.scrollLeft <= 2;
        const atEnd = scroller.scrollLeft >= maxScroll - 2;

        if (leftBtn) leftBtn.disabled = atStart;
        if (rightBtn) rightBtn.disabled = atEnd || maxScroll === 0;

        if (thumb) {
            const visibleRatio = maxScroll > 0 ? scroller.clientWidth / scroller.scrollWidth : 1;
            const thumbWidth = Math.max(18, Math.min(100, visibleRatio * 100));
            const travel = 100 - thumbWidth;
            const left = maxScroll > 0 ? (scroller.scrollLeft / maxScroll) * travel : 0;
            thumb.style.width = `${thumbWidth}%`;
            thumb.style.left = `${left}%`;
        }
    };

    leftBtn?.addEventListener('click', () => {
        scroller.scrollBy({ left: -scrollAmount(), behavior: 'smooth' });
    });

    rightBtn?.addEventListener('click', () => {
        scroller.scrollBy({ left: scrollAmount(), behavior: 'smooth' });
    });

    scroller.addEventListener('scroll', () => {
        window.requestAnimationFrame(updateControls);
    }, { passive: true });

    scroller.addEventListener('wheel', (event) => {
        if (Math.abs(event.deltaY) <= Math.abs(event.deltaX)) return;
        event.preventDefault();
        scroller.scrollLeft += event.deltaY;
    }, { passive: false });

    scroller.addEventListener('pointerdown', (event) => {
        if (event.button !== 0) return;
        isDragging = true;
        movedDuringDrag = false;
        startX = event.clientX;
        startScrollLeft = scroller.scrollLeft;
        scroller.classList.add('is-dragging');
        scroller.setPointerCapture?.(event.pointerId);
    });

    scroller.addEventListener('pointermove', (event) => {
        if (!isDragging) return;
        const delta = event.clientX - startX;
        if (Math.abs(delta) > 4) movedDuringDrag = true;
        scroller.scrollLeft = startScrollLeft - delta;
    });

    const stopDrag = (event) => {
        if (!isDragging) return;
        isDragging = false;
        scroller.classList.remove('is-dragging');
        scroller.releasePointerCapture?.(event.pointerId);
    };

    scroller.addEventListener('pointerup', stopDrag);
    scroller.addEventListener('pointercancel', stopDrag);
    scroller.addEventListener('click', (event) => {
        if (!movedDuringDrag) return;
        event.preventDefault();
        event.stopPropagation();
        movedDuringDrag = false;
    }, true);

    setTimeout(updateControls, 0);
}

function updateRouteProgress() {
    const progressFill = document.getElementById('route-progress');
    const completedCount = document.getElementById('completed-count');
    const totalCount = document.getElementById('total-count');

    const total = dailyRouteState.tasks.length;
    const completed = dailyRouteState.completed.length;
    const progress = total > 0 ? (completed / total) * 100 : 0;

    if (progressFill) progressFill.style.width = `${progress}%`;
    if (completedCount) completedCount.textContent = completed;
    if (totalCount) totalCount.textContent = total;
}

async function handleNodeClick(taskId) {
    const task = dailyRouteState.tasks.find(t => t.id === taskId);
    if (!task) return;

    const isCompleted = dailyRouteState.completed.includes(taskId);

    if (isCompleted) {
        showToast('⏪ 这项任务已完成，可以做点别的~', 'info');
        return;
    }

    // 点击当前任务，开始执行
    showToast(`⚡ 开始 "${task.title}"，预计 ${task.duration} 分钟`, 'success');

    // 导航到任务页面
    navigateToTask(task);
}

function navigateToTask(task) {
    const taskUrl = task.taskUrl || 'courses.html';
    window.location.href = '/' + taskUrl.replace(/^\//, '');
}

async function completeTask(taskId) {
    const user = JSON.parse(localStorage.getItem('starlearn_user') || '{}');
    if (!user.id) return;

    try {
        const response = await fetch('/api/daily-route/complete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ userId: user.id, taskId: taskId })
        });

        const data = await response.json();

        if (data.success) {
            // 更新本地状态
            if (!dailyRouteState.completed.includes(taskId)) {
                dailyRouteState.completed.push(taskId);
            }
            dailyRouteState.currentIndex = findCurrentIndex(dailyRouteState.tasks, dailyRouteState.completed);

            // 重新渲染
            renderDailyRoute();

            // 显示通知
            const task = dailyRouteState.tasks.find(t => t.id === taskId);
            showTaskCompletedNotification(task, data.completedCount, data.totalCount);
        }
    } catch (e) {
        console.error('[DailyRoute] Failed to complete task:', e);
    }
}

function showTaskCompletedNotification(task, completedCount, totalCount) {
    const remaining = totalCount - completedCount;

    // 使用通知系统
    if (window.starlearnNotifications && typeof window.starlearnNotifications.showNotification === 'function') {
        if (remaining > 0) {
            window.starlearnNotifications.showNotification({
                title: '✅ 任务完成！',
                content: `"${task.title}" 已完成！还剩 ${remaining} 个任务，继续加油！`,
                type: 'achievement'
            });
        } else {
            window.starlearnNotifications.showNotification({
                title: '🎉 今日航线全部完成！',
                content: `太棒了！你已完成今日所有 ${totalCount} 个学习任务！`,
                type: 'achievement'
            });
        }
    }

    // 也显示 toast
    if (remaining > 0) {
        showToast(`✅ "${task.title}" 完成！还剩 ${remaining} 个任务`, 'success');
    } else {
        showToast('🎉 恭喜！今日航线全部完成！', 'success');
    }
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

// 暴露 completeTask 到全局，以便其他页面可以调用
window.completeDailyRouteTask = completeTask;

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
// 学习概览图表初始化
// ============================================

// 学习概览日期显示
function initOverviewDate() {
    const dateEl = document.getElementById('overview-date');
    if (!dateEl) return;

    const now = new Date();
    const options = { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' };
    dateEl.textContent = now.toLocaleDateString('zh-CN', options);
}

function formatStudyDuration(minutes) {
    const value = Number(minutes) || 0;
    if (value >= 60) {
        return {
            value: (value / 60).toFixed(1),
            unit: '小时',
            text: `${(value / 60).toFixed(1)} 小时`
        };
    }

    return {
        value: String(value),
        unit: '分钟',
        text: `${value} 分钟`
    };
}

function updateOverviewAction(type, value, desc) {
    const card = document.querySelector(`.overview-action-card[data-overview-action="${type}"]`);
    if (!card) return;

    const valueEl = card.querySelector('.overview-action-value');
    const descEl = card.querySelector('.overview-action-desc');
    if (valueEl) valueEl.textContent = value;
    if (descEl) descEl.textContent = desc;
}

// 加载学习概览数据 (从API)
async function loadStudyOverviewData() {
    const user = JSON.parse(localStorage.getItem('starlearn_user') || '{}');
    if (!user || !user.id) return;

    try {
        // 获取概览数据
        const overviewRes = await fetch(`/api/stats/overview/${user.id}`);
        const overviewData = await overviewRes.json();

        if (overviewData.success && overviewData.overview) {
            const o = overviewData.overview;

            // 更新 Hero 状态卡
            const heroTitle = document.querySelector('.hero-title');
            const heroSubtitle = document.querySelector('.hero-subtitle');
            const heroValue = document.querySelector('.hero-stat-value');
            const heroUnit = document.querySelector('.hero-stat-unit');
            const todayDuration = formatStudyDuration(o.today_minutes || 0);
            const weekDuration = formatStudyDuration(o.week_minutes || 0);

            if (heroTitle) {
                heroTitle.textContent = (o.today_minutes || 0) > 0 ? '今天的学习状态' : '今天还没开始';
            }
            if (heroSubtitle) {
                heroSubtitle.textContent = (o.today_minutes || 0) > 0
                    ? `本周累计 ${weekDuration.text}，继续保持当前节奏。`
                    : `本周累计 ${weekDuration.text}，先从一个小任务开始。`;
            }
            if (heroValue) {
                heroValue.textContent = todayDuration.value;
            }
            if (heroUnit) {
                heroUnit.textContent = todayDuration.unit;
            }

            // 更新趋势显示
            const trendEl = document.querySelector('.hero-stat-trend');
            const trendSpan = trendEl?.querySelector('span');
            if (trendEl && trendSpan) {
                const trend = o.week_trend || 0;
                const isUp = trend > 0;
                const isDown = trend < 0;
                trendEl.className = `hero-stat-trend ${isUp ? 'up' : isDown ? 'down' : 'neutral'}`;
                trendSpan.textContent = trend === 0 ? '持平' : `${isUp ? '+' : ''}${trend}%`;
                // 更新箭头方向
                const svg = trendEl.querySelector('svg');
                if (svg) {
                    svg.innerHTML = isUp
                        ? '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 10l7-7m0 0l7 7m-7-7v18"/>'
                        : isDown
                            ? '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3"/>'
                            : '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 12h16"/>';
                }
            }

            const goalCount = o.total_goals || 0;
            const mastery = o.avg_mastery || 0;
            const knowledgeCount = o.knowledge_count || 0;
            const trend = o.week_trend || 0;
            const trendText = trend > 0 ? `+${trend}%` : trend < 0 ? `${trend}%` : '持平';
            const trendDesc = trend > 0
                ? '比上周更投入'
                : trend < 0
                    ? '比上周少一些，适合补一个短时段'
                    : '和上周相比暂无变化';

            updateOverviewAction(
                'focus',
                `${goalCount} 个目标`,
                goalCount > 0 ? '从专注任务里挑一个继续' : '暂无目标，可以先去选课'
            );
            updateOverviewAction(
                'mastery',
                `${mastery}%`,
                knowledgeCount > 0 ? `已学 ${knowledgeCount} 个知识点` : '暂无已学知识点'
            );
            updateOverviewAction('rhythm', trendText, trendDesc);
        }
    } catch (e) {
        console.log('[StudyOverview] 加载失败，使用默认数据');
    }
}

// 同步学习时长到服务器（每分钟调用）
async function syncLearningMinute() {
    const user = JSON.parse(localStorage.getItem('starlearn_user') || '{}');
    if (!user || !user.id) return;

    const now = new Date();
    const today = now.toISOString().split('T')[0];
    const hour = now.getHours();

    // 从 localStorage 读取当前学习数据
    let studyData = JSON.parse(localStorage.getItem('starlearn_study') || '{}');
    if (!studyData.daily_minutes) {
        studyData.daily_minutes = {};
    }
    if (!studyData.hourly_minutes) {
        studyData.hourly_minutes = {};
    }
    if (!studyData.hourly_minutes[today]) {
        studyData.hourly_minutes[today] = {};
    }

    // 更新今日分钟数
    studyData.daily_minutes[today] = (studyData.daily_minutes[today] || 0) + 1;

    // 更新当前小时分钟数
    studyData.hourly_minutes[today][hour] = (studyData.hourly_minutes[today][hour] || 0) + 1;

    // 保存到 localStorage
    localStorage.setItem('starlearn_study', JSON.stringify(studyData));

    try {
        await fetch('/api/cockpit/learning-time', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ userId: user.id }),
        });
        localStorage.setItem('starlearn_learning_update', String(Date.now()));
    } catch (e) { /* silent */ }
}

// 加载专注任务列表（从每日航线或目标API）
async function loadFocusTasks() {
    const user = JSON.parse(localStorage.getItem('starlearn_user') || '{}');
    if (!user || !user.id) return;

    const container = document.querySelector('.task-items');
    const badge = document.querySelector('.task-list-card .compact-badge');
    if (!container) return;

    try {
        // 尝试从每日航线获取任务
        const routeRes = await fetch(`/api/daily-route/status?userId=${user.id}`);
        const routeData = await routeRes.json();

        if (routeData.success && routeData.tasks && routeData.tasks.length > 0) {
            // 使用每日航线任务
            renderTaskItems(container, badge, routeData.tasks, routeData.completed || []);
            return;
        }

        // 备用：从目标API获取
        const goalsRes = await fetch(`/api/goals/${user.id}?active_only=true`);
        const goalsData = await goalsRes.json();

        if (goalsData.success && goalsData.goals && goalsData.goals.length > 0) {
            renderTaskItemsFromGoals(container, badge, goalsData.goals);
            return;
        }

        // 无数据时显示提示
        container.innerHTML = '<div class="task-empty">暂无专注任务，<a href="/courses.html">去选课</a></div>';
        if (badge) badge.textContent = '0个';
    } catch (e) {
        console.log('[FocusTasks] 加载失败');
    }
}

// 渲染任务列表（从每日航线）
function renderTaskItems(container, badge, tasks, completed) {
    if (!tasks || tasks.length === 0) {
        container.innerHTML = '<div class="task-empty">暂无专注任务，<a href="/courses.html">去选课</a></div>';
        if (badge) badge.textContent = '0个';
        return;
    }

    if (badge) badge.textContent = tasks.length + '个';

    const statusMap = {};
    completed.forEach(id => statusMap[id] = 'completed');

    container.innerHTML = tasks.slice(0, 5).map(task => {
        const status = statusMap[task.id] || 'pending';
        const statusLabels = { completed: '已完成', in_progress: '进行中', pending: '待开始' };
        const duration = task.duration || 60;
        return `
            <div class="task-item ${status}" data-task-id="${task.id}">
                <div class="task-status ${status}">
                    ${status === 'completed' ? '<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"/></svg>' : ''}
                    ${status === 'in_progress' ? '<span class="status-pulse"></span>' : ''}
                </div>
                <div class="task-info">
                    <span class="task-name">${escapeHtml(task.title)}</span>
                    <span class="task-meta">${duration}分钟 · ${statusLabels[status]}</span>
                </div>
            </div>
        `;
    }).join('');
}

// 从目标渲染任务列表
function renderTaskItemsFromGoals(container, badge, goals) {
    if (!goals || goals.length === 0) {
        container.innerHTML = '<div class="task-empty">暂无目标，<a href="/courses.html">去设定</a></div>';
        if (badge) badge.textContent = '0个';
        return;
    }

    if (badge) badge.textContent = goals.length + '个';

    container.innerHTML = goals.slice(0, 5).map(goal => {
        const progress = goal.current_value && goal.target_value
            ? Math.round(goal.current_value / goal.target_value * 100)
            : 0;
        const status = progress >= 100 ? 'completed' : progress > 0 ? 'in_progress' : 'pending';
        const statusLabels = { completed: '已完成', in_progress: '进行中', pending: '待开始' };
        return `
            <div class="task-item ${status}">
                <div class="task-status ${status}">
                    ${status === 'completed' ? '<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"/></svg>' : ''}
                    ${status === 'in_progress' ? '<span class="status-pulse"></span>' : ''}
                </div>
                <div class="task-info">
                    <span class="task-name">${escapeHtml(goal.title)}</span>
                    <span class="task-meta">${progress}% · ${statusLabels[status]}</span>
                </div>
            </div>
        `;
    }).join('');
}

// 加载专注日历（动态渲染）
async function loadFocusCalendar() {
    const user = JSON.parse(localStorage.getItem('starlearn_user') || '{}');
    if (!user || !user.id) return;

    const grid = document.querySelector('.mini-calendar-grid');
    const badge = document.querySelector('.calendar-card .compact-badge');
    if (!grid) return;

    try {
        const response = await fetch(`/api/stats/heatmap/${user.id}?weeks=4`);
        const result = await response.json();

        if (result.success && result.heatmap && result.heatmap.length > 0) {
            renderCalendarGrid(grid, badge, result.heatmap);
        } else {
            // 无数据时显示空白日历
            renderEmptyCalendar(grid, badge);
        }
    } catch (e) {
        console.log('[Calendar] 加载失败');
        renderEmptyCalendar(grid, badge);
    }
}

// 渲染日历网格
function renderCalendarGrid(grid, badge, heatmapData) {
    const today = new Date();
    const currentMonth = today.getMonth() + 1;
    if (badge) badge.textContent = currentMonth + '月';

    // 获取本月数据
    const monthData = {};
    heatmapData.forEach(item => {
        const date = new Date(item.date);
        if (date.getMonth() + 1 === currentMonth) {
            monthData[date.getDate()] = item.minutes > 0;
        }
    });

    // 计算本月第一天是星期几
    const firstDay = new Date(today.getFullYear(), currentMonth - 1, 1).getDay();
    const daysInMonth = new Date(today.getFullYear(), currentMonth, 0).getDate();

    let html = '';

    // 填充空白
    const dayNames = ['日', '一', '二', '三', '四', '五', '六'];
    for (let i = 0; i < firstDay; i++) {
        html += '<span class="empty"></span>';
    }

    // 填充日期
    for (let day = 1; day <= daysInMonth; day++) {
        const isToday = day === today.getDate();
        const hasStudy = monthData[day];
        html += `<span class="day${hasStudy ? ' completed' : ''}${isToday ? ' today' : ''}">${day}</span>`;
    }

    grid.innerHTML = html;
}

// 渲染空白日历
function renderEmptyCalendar(grid, badge) {
    const today = new Date();
    const currentMonth = today.getMonth() + 1;
    if (badge) badge.textContent = currentMonth + '月';

    const firstDay = new Date(today.getFullYear(), currentMonth - 1, 1).getDay();
    const daysInMonth = new Date(today.getFullYear(), currentMonth, 0).getDate();

    let html = '';
    for (let i = 0; i < firstDay; i++) {
        html += '<span class="empty"></span>';
    }
    for (let day = 1; day <= daysInMonth; day++) {
        const isToday = day === today.getDate();
        html += `<span class="day${isToday ? ' today' : ''}">${day}</span>`;
    }
    grid.innerHTML = html;
}

// 加载学习领域标签（从知识节点或用户画像）
async function loadLearningDomains() {
    const user = JSON.parse(localStorage.getItem('starlearn_user') || '{}');
    if (!user || !user.id) return;

    const container = document.querySelector('.tags-cloud');
    const badge = document.querySelector('.tags-card .compact-badge');
    if (!container) return;

    try {
        // 从每日航线获取学习领域
        const routeRes = await fetch(`/api/daily-route/status?userId=${user.id}`);
        const routeData = await routeRes.json();

        if (routeData.success && routeData.tasks && routeData.tasks.length > 0) {
            // 收集所有subject
            const subjects = [...new Set(routeData.tasks.map(t => t.subject).filter(Boolean))];
            if (subjects.length > 0) {
                renderDomainTags(container, badge, subjects);
                return;
            }
        }

        // 备用：从知识节点获取
        const nodesRes = await fetch(`/api/knowledge/nodes/${user.id}?active=true`);
        const nodesData = await nodesRes.json();

        if (nodesData.success && nodesData.nodes && nodesData.nodes.length > 0) {
            const subjects = [...new Set(nodesData.nodes.map(n => n.subject).filter(Boolean))];
            if (subjects.length > 0) {
                renderDomainTags(container, badge, subjects);
                return;
            }
        }

        // 无数据时显示默认标签
        renderDefaultDomainTags(container, badge);
    } catch (e) {
        console.log('[Domains] 加载失败');
        renderDefaultDomainTags(container, badge);
    }
}

// 渲染领域标签
function renderDomainTags(container, badge, subjects) {
    if (badge) badge.textContent = subjects.length + '个';

    const emojis = { 'Python': '🐍', '数学': '📊', '机器学习': '🤖', '深度学习': '🧠', '算法': '🧮', '数据库': '🗄️', 'Web开发': '🌐', '英语': '📖', '数据结构': '📚' };
    const colors = ['python', 'ds', 'ml', 'dl', 'algo', 'sys'];

    container.innerHTML = subjects.slice(0, 8).map((subject, i) => {
        const emoji = emojis[subject] || '📚';
        const color = colors[i % colors.length];
        return `<span class="tag-item ${color}">${emoji} ${escapeHtml(subject)}</span>`;
    }).join('');
}

// 渲染默认领域标签
function renderDefaultDomainTags(container, badge) {
    if (badge) badge.textContent = '6个';
    const defaults = [
        { name: 'Python', emoji: '🐍', color: 'python' },
        { name: '数据结构', emoji: '📊', color: 'ds' },
        { name: '机器学习', emoji: '🤖', color: 'ml' },
        { name: '深度学习', emoji: '🧠', color: 'dl' },
        { name: '算法', emoji: '🧮', color: 'algo' },
        { name: '系统设计', emoji: '🏗️', color: 'sys' }
    ];
    container.innerHTML = defaults.map(d =>
        `<span class="tag-item ${d.color}">${d.emoji} ${d.name}</span>`
    ).join('');
}

// 渲染学习趋势图 (Canvas) - 异步加载数据
async function initTrendChart() {
    const canvas = document.getElementById('overviewTrendChart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const wrapper = canvas.parentElement;
    if (!wrapper) return;

    // 设置 Canvas 尺寸
    const dpr = window.devicePixelRatio || 1;
    const rect = wrapper.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    canvas.style.width = rect.width + 'px';
    canvas.style.height = rect.height + 'px';
    ctx.scale(dpr, dpr);

    // 获取近7天数据 (异步从API)
    const data = await getWeekStudyData();
    const labels = data.map(d => d.day);
    const values = data.map(d => d.hours);

    const maxValue = Math.max(...values, 8);
    const padding = { top: 20, right: 20, bottom: 30, left: 40 };
    const chartWidth = rect.width - padding.left - padding.right;
    const chartHeight = rect.height - padding.top - padding.bottom;

    // 绘制网格
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
        const y = padding.top + (chartHeight / 4) * i;
        ctx.beginPath();
        ctx.moveTo(padding.left, y);
        ctx.lineTo(padding.left + chartWidth, y);
        ctx.stroke();
    }

    // 绘制 Y 轴标签
    ctx.fillStyle = 'rgba(255, 255, 255, 0.4)';
    ctx.font = '10px sans-serif';
    ctx.textAlign = 'right';
    for (let i = 0; i <= 4; i++) {
        const value = maxValue - (maxValue / 4) * i;
        const y = padding.top + (chartHeight / 4) * i + 4;
        ctx.fillText(value.toFixed(0) + 'h', padding.left - 8, y);
    }

    // 计算点位置
    const points = values.map((v, i) => ({
        x: padding.left + (chartWidth / (labels.length - 1)) * i,
        y: padding.top + chartHeight - (v / maxValue) * chartHeight
    }));

    // 绘制渐变填充
    const gradient = ctx.createLinearGradient(0, padding.top, 0, padding.top + chartHeight);
    gradient.addColorStop(0, 'rgba(168, 85, 247, 0.4)');
    gradient.addColorStop(1, 'rgba(168, 85, 247, 0)');

    ctx.beginPath();
    ctx.moveTo(points[0].x, padding.top + chartHeight);
    points.forEach(p => ctx.lineTo(p.x, p.y));
    ctx.lineTo(points[points.length - 1].x, padding.top + chartHeight);
    ctx.closePath();
    ctx.fillStyle = gradient;
    ctx.fill();

    // 绘制曲线
    ctx.beginPath();
    ctx.moveTo(points[0].x, points[0].y);
    for (let i = 1; i < points.length; i++) {
        const cp = {
            x: (points[i - 1].x + points[i].x) / 2,
            y: points[i].y
        };
        ctx.bezierCurveTo(cp.x, points[i - 1].y, cp.x, points[i].y, points[i].x, points[i].y);
    }
    ctx.strokeStyle = '#a855f7';
    ctx.lineWidth = 2.5;
    ctx.stroke();

    // 绘制点和hover效果
    points.forEach((p, i) => {
        // 外圈
        ctx.beginPath();
        ctx.arc(p.x, p.y, 6, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(168, 85, 247, 0.3)';
        ctx.fill();

        // 内圈
        ctx.beginPath();
        ctx.arc(p.x, p.y, 3, 0, Math.PI * 2);
        ctx.fillStyle = '#a855f7';
        ctx.fill();
    });

    // 绘制 X 轴标签
    ctx.fillStyle = 'rgba(255, 255, 255, 0.4)';
    ctx.font = '10px sans-serif';
    ctx.textAlign = 'center';
    labels.forEach((label, i) => {
        const x = padding.left + (chartWidth / (labels.length - 1)) * i;
        ctx.fillText(label, x, rect.height - 8);
    });
}

// 获取近7天学习数据 (从API)
async function getWeekStudyData() {
    const dayMap = { 'Sun': '周日', 'Mon': '周一', 'Tue': '周二', 'Wed': '周三', 'Thu': '周四', 'Fri': '周五', 'Sat': '周六' };
    const daysOrder = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
    const data = [];
    const today = new Date();
    const user = JSON.parse(localStorage.getItem('starlearn_user') || '{}');

    // 尝试从API获取数据
    if (user && user.id) {
        try {
            const response = await fetch(`/api/stats/trend/${user.id}?days=7`);
            const result = await response.json();
            if (result.success && result.trend && result.trend.length > 0) {
                // API返回的是从最早到最近排序的7天数据
                return result.trend.map(t => ({
                    day: dayMap[t.weekday] || t.weekday || daysOrder[data.length],
                    hours: parseFloat((t.minutes / 60).toFixed(1))
                }));
            }
        } catch (e) {
            console.log('[Trend] API加载失败，使用本地数据');
        }
    }

    // 降级：使用本地存储（无假数据）
    for (let i = 6; i >= 0; i--) {
        const date = new Date(today);
        date.setDate(date.getDate() - i);
        const dateStr = date.toISOString().split('T')[0];

        let hours = 0;
        try {
            const studyData = JSON.parse(localStorage.getItem('starlearn_study') || '{}');
            const dayData = studyData[dateStr];
            if (dayData && dayData.duration) {
                hours = parseFloat((dayData.duration / 60).toFixed(1));
            }
        } catch (e) {}

        data.push({
            day: daysOrder[6 - i], // 从周一到周日
            hours: parseFloat(hours.toFixed(1))
        });
    }

    return data;
}

// 学习时段热力图当前周期
let heatmapCurrentPeriod = 'week';

// 渲染学习时段热力图 - 异步加载数据
async function initHeatmap(period = 'week') {
    const hoursContainer = document.getElementById('heatmapHours');
    const heatmapWrapper = document.getElementById('heatmapWrapper');
    if (!hoursContainer) {
        console.log('[Heatmap] 未找到heatmapHours元素');
        return;
    }

    console.log('[Heatmap] 开始渲染, period:', period);
    heatmapCurrentPeriod = period;
    hoursContainer.innerHTML = '';

    const user = JSON.parse(localStorage.getItem('starlearn_user') || '{}');
    if (!user || !user.id) {
        console.log('[Heatmap] 未登录用户');
        return;
    }

    // 合并 API 数据和 localStorage 数据
    let dailyMinutes = {};

    // 从 localStorage 获取数据（浏览器实时数据）
    try {
        const localStudy = JSON.parse(localStorage.getItem('starlearn_study') || '{}');
        if (localStudy.daily_minutes) {
            Object.assign(dailyMinutes, localStudy.daily_minutes);
        }
    } catch (e) {}

    // 从API获取学习数据（数据库数据）
    try {
        const response = await fetch(`/api/stats/heatmap/${user.id}?weeks=52`);
        const result = await response.json();
        if (result.success && result.heatmap) {
            result.heatmap.forEach(item => {
                // API 数据覆盖 localStorage 数据（以数据库为准）
                dailyMinutes[item.date] = item.minutes || 0;
            });
        }
    } catch (e) {
        console.log('[Heatmap] API加载失败，使用本地数据', e);
    }

    console.log('[Heatmap] 合并后的数据:', dailyMinutes);

    const today = new Date();
    const dayLabels = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
    const monthLabels = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'];

    if (period === 'day') {
        // 今日视图：显示24小时的学习数据
        const todayStr = today.toISOString().split('T')[0];
        const todayMinutes = dailyMinutes[todayStr] || 0;
        const hasStudy = todayMinutes > 0;

        // 获取今日小时数据
        let hourlyData = {};
        try {
            const localStudy = JSON.parse(localStorage.getItem('starlearn_study') || '{}');
            hourlyData = localStudy.hourly_minutes?.[todayStr] || {};
        } catch (e) {}

        // 时段标签
        const periods = [
            { label: '凌晨', hours: [0,1,2,3,4,5] },
            { label: '上午', hours: [6,7,8,9,10,11] },
            { label: '下午', hours: [12,13,14,15,16,17] },
            { label: '晚上', hours: [18,19,20,21,22,23] }
        ];

        // 添加时段标签行
        const labelRow = document.createElement('div');
        labelRow.className = 'heatmap-periods';
        periods.forEach(p => {
            const span = document.createElement('span');
            span.className = 'heat-period';
            span.textContent = p.label;
            labelRow.appendChild(span);
        });
        hoursContainer.appendChild(labelRow);

        // 找到今日最大小时分钟数
        let maxHourMinutes = 0;
        Object.values(hourlyData).forEach(m => maxHourMinutes = Math.max(maxHourMinutes, m));

        // 每个时段一行
        periods.forEach((p, pIdx) => {
            const row = document.createElement('div');
            row.className = 'heatmap-row';

            p.hours.forEach(hour => {
                const cell = document.createElement('div');
                cell.className = 'heatmap-hour';

                const hourMinutes = hourlyData[hour] || 0;
                const intensity = getIntensityLevel(hourMinutes, maxHourMinutes);

                if (intensity > 0) cell.classList.add(`level-${intensity}`);
                cell.title = `${hour}:00 - ${hourMinutes}分钟`;
                row.appendChild(cell);
            });
            hoursContainer.appendChild(row);
        });

    } else if (period === 'week') {
        // 本周7天 - 柱状图
        const weekStart = new Date(today);
        weekStart.setDate(today.getDate() - today.getDay() + 1); // 周一

        // 找到本周最大分钟数用于渐变计算
        let maxMinutes = 0;
        const weekMinutesArr = [];
        for (let i = 0; i < 7; i++) {
            const d = new Date(weekStart);
            d.setDate(weekStart.getDate() + i);
            const dateStr = d.toISOString().split('T')[0];
            const minutes = dailyMinutes[dateStr] || 0;
            weekMinutesArr.push(minutes);
            maxMinutes = Math.max(maxMinutes, minutes);
        }

        // 创建柱状图容器
        const chartContainer = document.createElement('div');
        chartContainer.className = 'heatmap-year-chart';

        // 每天一根柱
        for (let i = 0; i < 7; i++) {
            const intensity = getIntensityLevel(weekMinutesArr[i], maxMinutes);
            const heightPercent = maxMinutes > 0 ? (weekMinutesArr[i] / maxMinutes) * 100 : 0;

            const barWrapper = document.createElement('div');
            barWrapper.className = 'heatmap-year-bar';

            const barFill = document.createElement('div');
            barFill.className = 'heatmap-year-bar-fill';
            if (intensity > 0) {
                barFill.classList.add(`level-${intensity}`);
            } else {
                barFill.style.background = 'rgba(255, 255, 255, 0.05)';
            }
            barFill.style.height = `${Math.max(heightPercent, 4)}%`;
            barFill.title = `${dayLabels[i]} - ${weekMinutesArr[i]}分钟`;

            const label = document.createElement('div');
            label.className = 'heatmap-year-bar-label';
            label.textContent = dayLabels[i];

            barWrapper.appendChild(barFill);
            barWrapper.appendChild(label);
            chartContainer.appendChild(barWrapper);
        }
        hoursContainer.appendChild(chartContainer);

    } else if (period === 'month') {
        // 本月视图 - 柱状图（每周一根）
        const weekStart = new Date(today);
        weekStart.setDate(today.getDate() - today.getDay() + 1);

        // 计算本月有几周
        const daysInMonth = new Date(today.getFullYear(), today.getMonth() + 1, 0).getDate();
        const weeksInMonth = Math.ceil((today.getDate() + new Date(today.getFullYear(), today.getMonth(), 1).getDay()) / 7);

        // 找到本月最大周分钟数
        let maxWeekMinutes = 0;
        const weekMinutesArr = [];
        for (let w = 0; w < weeksInMonth; w++) {
            let weekMinutes = 0;
            for (let d = 0; d < 7; d++) {
                const dayDate = new Date(weekStart);
                dayDate.setDate(weekStart.getDate() + w * 7 + d);
                const dateStr = dayDate.toISOString().split('T')[0];
                weekMinutes += dailyMinutes[dateStr] || 0;
            }
            weekMinutesArr.push(weekMinutes);
            maxWeekMinutes = Math.max(maxWeekMinutes, weekMinutes);
        }

        // 创建柱状图容器
        const chartContainer = document.createElement('div');
        chartContainer.className = 'heatmap-year-chart';

        // 每周一根柱
        for (let w = 0; w < weeksInMonth; w++) {
            const intensity = getIntensityLevel(weekMinutesArr[w], maxWeekMinutes);
            const heightPercent = maxWeekMinutes > 0 ? (weekMinutesArr[w] / maxWeekMinutes) * 100 : 0;

            const barWrapper = document.createElement('div');
            barWrapper.className = 'heatmap-year-bar';

            const barFill = document.createElement('div');
            barFill.className = 'heatmap-year-bar-fill';
            if (intensity > 0) {
                barFill.classList.add(`level-${intensity}`);
            } else {
                barFill.style.background = 'rgba(255, 255, 255, 0.05)';
            }
            barFill.style.height = `${Math.max(heightPercent, 4)}%`;
            barFill.title = `第${w + 1}周 - ${weekMinutesArr[w]}分钟`;

            const label = document.createElement('div');
            label.className = 'heatmap-year-bar-label';
            label.textContent = `第${w + 1}周`;

            barWrapper.appendChild(barFill);
            barWrapper.appendChild(label);
            chartContainer.appendChild(barWrapper);
        }
        hoursContainer.appendChild(chartContainer);

    } else if (period === 'year') {
        // 全年12个月 - 柱状图
        const year = today.getFullYear();

        // 计算每月分钟数
        let maxMonthMinutes = 0;
        const monthMinutesArr = [];
        for (let m = 0; m < 12; m++) {
            const daysInMonth = new Date(year, m + 1, 0).getDate();
            let monthMinutes = 0;
            for (let d = 1; d <= daysInMonth; d++) {
                const dateStr = `${year}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
                monthMinutes += dailyMinutes[dateStr] || 0;
            }
            monthMinutesArr.push(monthMinutes);
            maxMonthMinutes = Math.max(maxMonthMinutes, monthMinutes);
        }

        // 创建柱状图容器
        const chartContainer = document.createElement('div');
        chartContainer.className = 'heatmap-year-chart';

        // 每月一个柱状条
        for (let m = 0; m < 12; m++) {
            const intensity = getIntensityLevel(monthMinutesArr[m], maxMonthMinutes);
            const heightPercent = maxMonthMinutes > 0 ? (monthMinutesArr[m] / maxMonthMinutes) * 100 : 0;

            const barWrapper = document.createElement('div');
            barWrapper.className = 'heatmap-year-bar';

            const barFill = document.createElement('div');
            barFill.className = 'heatmap-year-bar-fill';
            if (intensity > 0) {
                barFill.classList.add(`level-${intensity}`);
            } else {
                barFill.style.background = 'rgba(255, 255, 255, 0.05)';
            }
            barFill.style.height = `${Math.max(heightPercent, 4)}%`;
            barFill.title = `${monthLabels[m]} - ${monthMinutesArr[m]}分钟`;

            const label = document.createElement('div');
            label.className = 'heatmap-year-bar-label';
            label.textContent = monthLabels[m];

            barWrapper.appendChild(barFill);
            barWrapper.appendChild(label);
            chartContainer.appendChild(barWrapper);
        }

        hoursContainer.appendChild(chartContainer);
    }
}

// 获取热力图强度等级 - 根据相对值计算
function getIntensityLevel(minutes, maxMinutes = null) {
    // 如果传入了最大分钟数，则根据相对比例计算
    if (maxMinutes !== null && maxMinutes > 0) {
        const ratio = minutes / maxMinutes;
        if (ratio >= 0.8) return 4;
        if (ratio >= 0.5) return 3;
        if (ratio >= 0.2) return 2;
        if (ratio > 0) return 1;
        return 0;
    }
    // 默认阈值
    if (minutes >= 120) return 4;
    if (minutes >= 60) return 3;
    if (minutes >= 30) return 2;
    if (minutes > 0) return 1;
    return 0;
}

function getWeekHeatmapData() {
    const data = {};
    const today = new Date();

    for (let i = 0; i < 7; i++) {
        const date = new Date(today);
        date.setDate(date.getDate() - i);
        const dateStr = date.toISOString().split('T')[0];

        try {
            const studyData = JSON.parse(localStorage.getItem('starlearn_study') || '{}');
            data[dateStr] = studyData[dateStr] || {};
        } catch (e) {
            data[dateStr] = {};
        }
    }

    return data;
}

// 获取热力图强度等级
function getHeatmapIntensity(studyData, dayOffset, hour) {
    const date = new Date();
    date.setDate(date.getDate() - dayOffset);
    const dateStr = date.toISOString().split('T')[0];

    const dayData = studyData[dateStr];
    if (!dayData || !dayData.sessions) return 0;

    let count = 0;
    dayData.sessions.forEach(session => {
        const sessionHour = new Date(session.start).getHours();
        if (sessionHour === hour) count++;
    });

    if (count >= 3) return 4;
    if (count >= 2) return 3;
    if (count >= 1) return 2;
    return 1;
}

// ============================================
// 全息知识生态 - 树状金字塔布局
// ============================================

// 知识节点缓存
let knowledgeNodesCache = [];

// SM2 算法前端计算
function calculateSM2(quality, easinessFactor, interval, repetitions) {
    let newEF = easinessFactor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02));
    newEF = Math.max(1.3, newEF);

    let newInterval, newReps;
    if (quality < 3) {
        newReps = 0;
        newInterval = 1;
    } else {
        newReps = repetitions + 1;
        if (newReps === 1) newInterval = 1;
        else if (newReps === 2) newInterval = 6;
        else newInterval = Math.round(interval * newEF);
    }

    const nextReview = new Date(Date.now() + newInterval * 86400000);
    return {
        newInterval,
        newEF,
        newReps,
        nextReview: nextReview.toISOString()
    };
}

// 计算综合评分
function calculateComprehensiveScore(nodeData) {
    const sm2 = nodeData.sm2_data || {};
    const stats = nodeData.stats || {};

    // 1. 正确率分 (50%)
    const total = stats.total_reviews || 0;
    const correct = stats.correct_count || 0;
    const accuracyScore = total > 0 ? (correct / total) * 50 : 25;

    // 2. 遗忘曲线分 (30%)
    let forgettingCurveScore = 15;
    const nextReviewStr = sm2.next_review;
    if (nextReviewStr) {
        const nextReview = new Date(nextReviewStr);
        const now = new Date();
        const daysUntil = (nextReview - now) / 86400000;

        if (daysUntil < 0) {
            forgettingCurveScore = Math.max(0, 30 + daysUntil * 5);
        } else if (daysUntil < 1) {
            forgettingCurveScore = 15 + daysUntil * 15;
        } else if (daysUntil < 3) {
            forgettingCurveScore = 15 + (daysUntil - 1) * 7.5;
        } else {
            forgettingCurveScore = 30;
        }
    }

    // 3. 学习深度分 (20%)
    const reps = sm2.repetitions || 0;
    const ef = sm2.easiness_factor || 2.5;
    const depthScore = Math.min(20, reps * 2 + (ef - 1.3) * 5);

    return Math.round(Math.min(100, Math.max(0, accuracyScore + forgettingCurveScore + depthScore)));
}

// 获取节点状态（5种状态）
function getNodeDynamicStatus(nodeData) {
    const sm2 = nodeData.sm2_data || {};
    const stats = nodeData.stats || {};
    const isActive = nodeData.is_active;
    const firstStudied = nodeData.first_studied_at;
    const repetitions = sm2.repetitions || 0;

    // 未开始学习：没有首次学习时间且没有复习记录
    if (!firstStudied && repetitions === 0) {
        return 'not-started';
    }

    // 学习中：开始学习了但还没有SM2复习记录
    if (repetitions === 0 && firstStudied) {
        return 'in-progress';
    }

    // 检查是否过期
    const nextReviewStr = sm2.next_review;
    if (nextReviewStr) {
        const nextReview = new Date(nextReviewStr);
        if (nextReview < new Date()) {
            return 'danger';
        }
    }

    // 计算综合评分
    const score = calculateComprehensiveScore(nodeData);
    if (score >= 70) return 'healthy';
    if (score >= 40) return 'warning';
    return 'danger';
}

// 获取状态文本
function getStatusText(status) {
    switch(status) {
        case 'not-started': return '未开始';
        case 'in-progress': return '学习中';
        case 'healthy': return '掌握良好';
        case 'warning': return '需复习';
        case 'danger': return '濒临遗忘';
        default: return '未知';
    }
}

// 从API加载知识节点
async function loadKnowledgeNodes(activeOnly = false) {
    const user = JSON.parse(localStorage.getItem('starlearn_user') || '{}');
    if (!user.id) {
        console.warn('[Holo] No user ID found');
        return [];
    }

    try {
        const url = `/api/knowledge/nodes/${user.id}${activeOnly ? '?active=true' : ''}`;
        const response = await fetch(url);
        const data = await response.json();
        if (data.success) {
            knowledgeNodesCache = data.nodes || [];
            return knowledgeNodesCache;
        }
    } catch (e) {
        console.error('[Holo] Failed to load knowledge nodes:', e);
    }
    return [];
}

// 提交复习结果
async function submitReview(nodeId, quality, responseTime = 0) {
    const user = JSON.parse(localStorage.getItem('starlearn_user') || '{}');
    if (!user.id) return null;

    try {
        const response = await fetch('/api/knowledge/review', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: user.id,
                node_id: nodeId,
                quality: quality,
                response_time: responseTime
            })
        });
        const data = await response.json();
        if (data.success) {
            // 刷新节点数据
            await loadKnowledgeNodes();
            updateHoloEcosystemUI();
        }
        return data.result;
    } catch (e) {
        console.error('[Holo] Failed to submit review:', e);
        return null;
    }
}

// 获取待复习节点
async function getPendingReviews() {
    const user = JSON.parse(localStorage.getItem('starlearn_user') || '{}');
    if (!user.id) return [];

    try {
        const response = await fetch(`/api/knowledge/pending/${user.id}`);
        const data = await response.json();
        if (data.success) {
            return data.pending || [];
        }
    } catch (e) {
        console.error('[Holo] Failed to get pending reviews:', e);
    }
    return [];
}

// 根据节点学科/icon返回对应的SVG图标
function getNodeIcon(nodeData) {
    const svgMap = {
        '🐍': `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3.3C13.5 1.5 8 2 5 6c-2 3 0 7 4 7.5 1 .1 2.5-.2 3-1 .6-.9.4-2-1-2.5-2.5-.8-6 .5-7 4-.7 2.5.5 6 4 7s7-2 9-6c1.4-2.8 0-6-2-7"/><circle cx="16" cy="5" r="1.2" fill="currentColor" stroke="none"/></svg>`,
        '📐': `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 20L20 4"/><path d="M4 20h4l12-12-4-4L4 16v4z"/><circle cx="7" cy="17" r="0.5" fill="currentColor" stroke="none"/></svg>`,
        '🌐': `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z"/></svg>`,
        '🗄️': `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="6" rx="9" ry="3"/><path d="M3 6v6c0 1.7 4 3 9 3s9-1.3 9-3V6"/><path d="M3 12v6c0 1.7 4 3 9 3s9-1.3 9-3v-6"/></svg>`,
        '📚': `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 016.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/><path d="M8 7h8"/><path d="M8 11h6"/></svg>`,
        '🤖': `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6" rx="1"/><path d="M9 1v3M15 1v3M9 20v3M15 20v3M4 9H1M4 15H1M23 9h-3M23 15h-3"/></svg>`,
        '🧮': `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="5" cy="5" r="3"/><circle cx="5" cy="19" r="3"/><circle cx="19" cy="12" r="3"/><path d="M8 6.5l8 4M8 17.5l8-4"/></svg>`,
        '⚙️': `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 01-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/></svg>`,
        '🔤': `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/><path d="M8 9h8"/><path d="M8 13h5"/></svg>`
    };
    const icon = nodeData.icon || '📚';
    return svgMap[icon] || svgMap['📚'];
}

// 更新全息生态UI
function updateHoloEcosystemUI() {
    const nodesContainer = document.getElementById('holoNodes');
    if (!nodesContainer) return;

    const nodeElements = nodesContainer.querySelectorAll('.holo-node');
    nodeElements.forEach(nodeEl => {
        const nodeId = nodeEl.dataset.id;
        const nodeData = knowledgeNodesCache.find(n => n.node_id === nodeId);

        if (nodeData) {
            const status = getNodeDynamicStatus(nodeData);
            nodeEl.dataset.status = status;

            // 更新图标
            const iconEl = nodeEl.querySelector('.node-icon');
            if (iconEl) {
                iconEl.innerHTML = getNodeIcon(nodeData);
            }

            // 更新状态显示
            const statusEl = nodeEl.querySelector('.node-status');
            if (statusEl) {
                statusEl.textContent = getStatusText(status);
            }

            // 更新节点样式
            nodeEl.classList.remove('not-started', 'in-progress', 'healthy', 'warning', 'danger');
            nodeEl.classList.add(status);
        }
    });

    // 更新统计栏
    updateHoloStats();
    updateHoloPrioritySummary();
    drawTreeConnections();
}

// 更新统计栏
function updateHoloStats() {
    const healthyCount = knowledgeNodesCache.filter(n => getNodeDynamicStatus(n) === 'healthy').length;
    const warningCount = knowledgeNodesCache.filter(n => getNodeDynamicStatus(n) === 'warning').length;
    const dangerCount = knowledgeNodesCache.filter(n => getNodeDynamicStatus(n) === 'danger').length;

    const total = knowledgeNodesCache.length || 1;
    const healthPercent = Math.round((healthyCount / total) * 100);

    const statsBar = document.querySelector('.holo-stats-bar');
    if (statsBar) {
        const healthyEl = statsBar.querySelector('.stat-item:nth-child(1) .stat-value');
        const warningEl = statsBar.querySelector('.stat-item:nth-child(2) .stat-value');
        const dangerEl = statsBar.querySelector('.stat-item:nth-child(3) .stat-value');
        const percentEl = statsBar.querySelector('.stat-item:nth-child(4) .stat-value');

        if (healthyEl) healthyEl.textContent = healthyCount;
        if (warningEl) warningEl.textContent = warningCount;
        if (dangerEl) dangerEl.textContent = dangerCount;
        if (percentEl) percentEl.textContent = healthPercent + '%';
    }
}

function getNodeDisplayName(nodeData) {
    return nodeData?.name || nodeData?.title || nodeData?.node_name || nodeData?.node_id || '知识节点';
}

function updateHoloPrioritySummary() {
    const urgentChip = document.querySelector('.priority-chip.urgent');
    const reviewChip = document.querySelector('.priority-chip.review');
    const stableChip = document.querySelector('.priority-chip.stable');
    const briefTitle = document.querySelector('.brief-copy strong');
    const briefText = document.querySelector('.brief-copy span:last-child');
    const reviewLink = document.querySelector('.holo-review-link');

    if (!urgentChip || !reviewChip || !stableChip || !briefTitle || !briefText) return;

    let urgentName = '机器学习';
    let reviewName = '算法设计';
    let stableName = 'Python核心';
    let helperText = '记忆风险最高，建议先复习 12 分钟';

    if (knowledgeNodesCache.length > 0) {
        const enriched = knowledgeNodesCache.map(node => {
            const urgency = calculateNodeUrgency(node);
            return {
                node,
                urgency,
                status: getNodeDynamicStatus(node)
            };
        }).sort((a, b) => b.urgency.score - a.urgency.score);

        const urgent = enriched[0];
        const review = enriched.find(item => ['danger', 'warning', 'in-progress'].includes(item.status) && item !== urgent) || enriched[1] || urgent;
        const stable = enriched.find(item => item.status === 'healthy') || enriched[enriched.length - 1] || urgent;

        if (urgent) {
            urgentName = getNodeDisplayName(urgent.node);
            const timeText = urgent.urgency.timeStr && urgent.urgency.timeStr !== '未安排'
                ? `距复习点 ${urgent.urgency.timeStr}`
                : '建议安排一次短复习';
            helperText = `${getStatusText(urgent.status)}，${timeText}`;
        }
        if (review) reviewName = getNodeDisplayName(review.node);
        if (stable) stableName = getNodeDisplayName(stable.node);
    }

    urgentChip.textContent = urgentName;
    reviewChip.textContent = reviewName;
    stableChip.textContent = stableName;
    briefTitle.textContent = urgentName;
    briefText.textContent = helperText;

    if (reviewLink) {
        reviewLink.setAttribute('aria-label', `开始复习${urgentName}`);
    }
}

// 初始化全息知识生态
async function initHoloEcosystem() {
    const container = document.getElementById('holoTree');
    const nodesContainer = document.getElementById('holoNodes');

    if (!container || !nodesContainer) return;

    // 先从API加载节点数据
    await loadKnowledgeNodes();

    const nodes = nodesContainer.querySelectorAll('.holo-node');
    nodes.forEach((node, index) => {
        node.style.animationDelay = (0.1 + index * 0.1) + 's';

        // 为每个节点添加点击事件
        node.addEventListener('click', () => {
            const nodeId = node.dataset.id;
            showReviewModal(nodeId);
        });
    });

    // 根据加载的数据更新UI，使用遗忘曲线布局
    if (knowledgeNodesCache.length > 0) {
        updateHoloEcosystemUI();
        // 使用新的遗忘曲线布局代替原来的树状金字塔布局
        setTimeout(() => {
            drawEbbinghausLayout();
        }, 100);
    } else {
        drawTreeConnections();
    }
    updateHoloPrioritySummary();

    let resizeTimeout;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(drawEbbinghausLayout, 100);
    });
}

// 显示复习弹窗
function showReviewModal(nodeId) {
    const nodeData = knowledgeNodesCache.find(n => n.node_id === nodeId);
    if (!nodeData) return;

    // 创建或显示复习弹窗
    let modal = document.getElementById('review-modal');
    if (!modal) {
        modal = createReviewModal();
        document.body.appendChild(modal);
    }

    // 更新弹窗内容
    const titleEl = modal.querySelector('.review-modal-title');
    const infoEl = modal.querySelector('.review-modal-info');
    const statsEl = modal.querySelector('.review-modal-stats');

    if (titleEl) titleEl.textContent = nodeData.name;
    if (infoEl) {
        const sm2 = nodeData.sm2_data || {};
        const nextReview = sm2.next_review ? new Date(sm2.next_review).toLocaleDateString() : '未设置';
        infoEl.innerHTML = `
            <p>下次复习: ${nextReview}</p>
            <p>简易度: ${(sm2.easiness_factor || 2.5).toFixed(2)}</p>
            <p>间隔: ${sm2.interval || 1} 天</p>
        `;
    }
    if (statsEl) {
        const stats = nodeData.stats || {};
        const total = stats.total_reviews || 0;
        const correct = stats.correct_count || 0;
        const rate = total > 0 ? Math.round((correct / total) * 100) : 0;
        statsEl.innerHTML = `
            <p>复习次数: ${total}</p>
            <p>正确率: ${rate}%</p>
        `;
    }

    modal.dataset.nodeId = nodeId;
    modal.classList.add('active');
}

// 创建复习弹窗
function createReviewModal() {
    const modal = document.createElement('div');
    modal.id = 'review-modal';
    modal.className = 'review-modal';
    modal.innerHTML = `
        <div class="review-modal-content">
            <div class="review-modal-header">
                <h3 class="review-modal-title">复习</h3>
                <button class="review-modal-close">&times;</button>
            </div>
            <div class="review-modal-body">
                <div class="review-modal-info"></div>
                <div class="review-modal-stats"></div>
                <div class="review-quality-buttons">
                    <p>这次复习你记得多好?</p>
                    <button class="quality-btn" data-quality="0">忘记</button>
                    <button class="quality-btn" data-quality="2">困难</button>
                    <button class="quality-btn" data-quality="3">一般</button>
                    <button class="quality-btn" data-quality="4">良好</button>
                    <button class="quality-btn" data-quality="5">完美</button>
                </div>
            </div>
        </div>
    `;

    // 关闭按钮事件
    modal.querySelector('.review-modal-close').addEventListener('click', () => {
        modal.classList.remove('active');
    });

    // 质量按钮事件
    modal.querySelectorAll('.quality-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            const quality = parseInt(btn.dataset.quality);
            const nodeId = modal.dataset.nodeId;
            const result = await submitReview(nodeId, quality);

            if (result) {
                modal.classList.remove('active');
                // 更新通知徽章
                updateNotificationBadge();
            }
        });
    });

    // 点击外部关闭
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.classList.remove('active');
        }
    });

    return modal;
}

// 更新通知徽章
async function updateNotificationBadge() {
    const pending = await getPendingReviews();
    const badge = document.querySelector('.notification-badge');
    const pendingBadge = document.querySelector('.pending-review-badge');

    if (badge && pending.length > 0) {
        badge.textContent = pending.length;
        badge.style.display = 'flex';
    }

    if (pendingBadge) {
        pendingBadge.textContent = pending.length;
        pendingBadge.style.display = pending.length > 0 ? 'flex' : 'none';
    }
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
// 遗忘曲线时间轴布局 (Ebbinghaus Timeline Layout)
// ============================================

// 基于紧迫性的布局配置
const URGENCY_CONFIG = {
    // X轴: 复习优先级 (0=最紧迫在左边, 100=最稳定在右边)
    // Y轴: 知识层级 (10=root, 35=branch, 60=leaf)
    levelY: { 'root': 10, 'branch': 35, 'leaf': 60 },
    // 紧迫性颜色
    urgencyColors: {
        critical: { from: '#ef4444', to: '#f87171' },  // 0-30: 危险红
        warning: { from: '#f59e0b', to: '#fbbf24' },   // 30-70: 警告橙
        healthy: { from: '#10b981', to: '#34d399' }    // 70-100: 健康绿
    }
};

// 计算机器的紧迫性评分和时间
function calculateNodeUrgency(nodeData) {
    const sm2 = nodeData.sm2_data || {};
    const nextReview = sm2.next_review;

    if (!nextReview) {
        return { score: 50, timeStr: '未安排', hoursUntil: Infinity };
    }

    const now = new Date();
    const reviewDate = new Date(nextReview.replace('Z', '+00:00'));
    const hoursUntil = (reviewDate - now) / (1000 * 60 * 60);

    let score, timeStr;

    if (hoursUntil < 0) {
        // 已过期 - 最高紧迫
        score = 100;
        timeStr = '已过期';
    } else if (hoursUntil < 1) {
        score = 98;
        timeStr = '不到1小时';
    } else if (hoursUntil < 24) {
        score = 95 - (hoursUntil / 24) * 5;
        timeStr = `${Math.round(hoursUntil)}小时`;
    } else if (hoursUntil < 72) {
        score = 90 - ((hoursUntil - 24) / 48) * 20;
        timeStr = `${Math.round(hoursUntil / 24)}天`;
    } else if (hoursUntil < 168) {
        score = 70 - ((hoursUntil - 72) / 96) * 40;
        timeStr = `${Math.round(hoursUntil / 24)}天`;
    } else {
        score = Math.max(0, 30 - ((hoursUntil - 168) / 672) * 30);
        const days = hoursUntil / 24;
        if (days < 14) timeStr = `${Math.round(days)}天`;
        else if (days < 30) timeStr = `${Math.round(days / 7)}周`;
        else timeStr = `${Math.round(days / 30)}月`;
    }

    return { score: Math.round(score), timeStr, hoursUntil };
}

// 根据紧迫性计算节点位置
function calculateNodePosition(nodeData, totalNodes) {
    const levelY = URGENCY_CONFIG.levelY;
    const level = nodeData.level || 'leaf';
    const y = levelY[level] || 60;

    const { score: urgency } = calculateNodeUrgency(nodeData);
    const x = Math.min(92, Math.max(8, 100 - urgency));

    return {
        x,
        y: y,
        urgency: urgency
    };
}

// 根据紧迫性获取颜色
function getUrgencyColor(urgency, opacity = 1) {
    let color;
    if (urgency >= 70) {
        color = URGENCY_CONFIG.urgencyColors.critical;
    } else if (urgency >= 30) {
        color = URGENCY_CONFIG.urgencyColors.warning;
    } else {
        color = URGENCY_CONFIG.urgencyColors.healthy;
    }

    // 根据紧迫性在颜色范围内插值
    let r, g, b;
    if (urgency >= 70) {
        const t = (urgency - 70) / 30; // 0-1
        r = Math.round(parseInt(color.from.slice(1, 3), 16) + (parseInt(color.to.slice(1, 3), 16) - parseInt(color.from.slice(1, 3), 16)) * t);
        g = Math.round(parseInt(color.from.slice(3, 5), 16) + (parseInt(color.to.slice(3, 5), 16) - parseInt(color.from.slice(3, 5), 16)) * t);
        b = Math.round(parseInt(color.from.slice(5, 7), 16) + (parseInt(color.to.slice(5, 7), 16) - parseInt(color.from.slice(5, 7), 16)) * t);
    } else if (urgency >= 30) {
        const t = (urgency - 30) / 40;
        r = Math.round(parseInt(color.from.slice(1, 3), 16) + (parseInt(color.to.slice(1, 3), 16) - parseInt(color.from.slice(1, 3), 16)) * t);
        g = Math.round(parseInt(color.from.slice(3, 5), 16) + (parseInt(color.to.slice(3, 5), 16) - parseInt(color.from.slice(3, 5), 16)) * t);
        b = Math.round(parseInt(color.from.slice(5, 7), 16) + (parseInt(color.to.slice(5, 7), 16) - parseInt(color.from.slice(5, 7), 16)) * t);
    } else {
        const t = Math.max(0, urgency / 30);
        r = Math.round(parseInt(color.to.slice(1, 3), 16) + (parseInt(color.from.slice(1, 3), 16) - parseInt(color.to.slice(1, 3), 16)) * t);
        g = Math.round(parseInt(color.to.slice(3, 5), 16) + (parseInt(color.from.slice(3, 5), 16) - parseInt(color.to.slice(3, 5), 16)) * t);
        b = Math.round(parseInt(color.to.slice(5, 7), 16) + (parseInt(color.from.slice(5, 7), 16) - parseInt(color.to.slice(5, 7), 16)) * t);
    }

    return `rgba(${r}, ${g}, ${b}, ${opacity})`;
}

// 绘制遗忘曲线布局
function drawEbbinghausLayout() {
    const svgContainer = document.getElementById('holoConnections');
    const nodesContainer = document.getElementById('holoNodes');

    if (!svgContainer || !nodesContainer) return;

    // 清除现有内容
    svgContainer.innerHTML = '';

    // 添加 SVG 定义
    svgContainer.innerHTML = `
        <defs>
            <!-- 紧迫性渐变 - 危险红 -->
            <linearGradient id="urgencyGradientCritical" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="rgba(239, 68, 68, 0.8)"/>
                <stop offset="100%" stop-color="rgba(248, 113, 113, 0.4)"/>
            </linearGradient>
            <!-- 紧迫性渐变 - 警告橙 -->
            <linearGradient id="urgencyGradientWarning" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="rgba(245, 158, 11, 0.8)"/>
                <stop offset="100%" stop-color="rgba(251, 191, 36, 0.4)"/>
            </linearGradient>
            <!-- 紧迫性渐变 - 健康绿 -->
            <linearGradient id="urgencyGradientHealthy" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="rgba(16, 185, 129, 0.8)"/>
                <stop offset="100%" stop-color="rgba(52, 211, 153, 0.4)"/>
            </linearGradient>
            <!-- 前置知识虚线样式 -->
            <marker id="arrowPrerequisite" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
                <polygon points="0 0, 10 3.5, 0 7" fill="rgba(168, 85, 247, 0.7)"/>
            </marker>
            <!-- 相关知识标记 -->
            <marker id="arrowRelated" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
                <polygon points="0 0, 8 3, 0 6" fill="rgba(59, 130, 246, 0.6)"/>
            </marker>
            <filter id="connectionGlow" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="2" result="glow"/>
                <feMerge>
                    <feMergeNode in="glow"/>
                    <feMergeNode in="SourceGraphic"/>
                </feMerge>
            </filter>
        </defs>
    `;

    svgContainer.setAttribute('viewBox', '0 0 100 100');
    svgContainer.setAttribute('preserveAspectRatio', 'xMidYMid meet');

    // 绘制时间轴背景（可选）
    drawTimeAxisBackground(svgContainer);

    // 获取所有节点
    const allNodes = nodesContainer.querySelectorAll('.holo-node');
    const nodePositions = new Map();

    // 第一步：计算所有节点位置
    allNodes.forEach(node => {
        const nodeId = node.dataset.id;
        const nodeData = knowledgeNodesCache.find(n => n.node_id === nodeId);
        if (!nodeData) return;

        const pos = calculateNodePosition(nodeData, allNodes.length);
        nodePositions.set(nodeId, pos);

        // 应用位置到节点
        const nodeEl = node;
        nodeEl.style.left = `${pos.x}%`;
        nodeEl.style.top = `${pos.y}%`;
        nodeEl.style.transform = 'translate(-50%, -50%)';
        nodeEl.style.zIndex = Math.round(100 + pos.urgency);

        // 更新紧迫性颜色
        updateNodeUrgencyStyle(nodeEl, pos.urgency);
    });

    // 第二步：绘制连接线
    drawUrgencyConnections(svgContainer, nodesContainer, nodePositions);
}

// 绘制时间轴背景
function drawTimeAxisBackground(svgContainer) {
    // 绘制紧迫性区域背景
    const urgencyBg = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    urgencyBg.setAttribute('class', 'urgency-background');

    // 左侧紧迫区 (0-30)
    const criticalZone = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    criticalZone.setAttribute('x', '0');
    criticalZone.setAttribute('y', '0');
    criticalZone.setAttribute('width', '30');
    criticalZone.setAttribute('height', '100');
    criticalZone.setAttribute('fill', 'rgba(239, 68, 68, 0.05)');
    urgencyBg.appendChild(criticalZone);

    // 中间缓冲X区 (30-70)
    const warningZone = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    warningZone.setAttribute('x', '30');
    warningZone.setAttribute('y', '0');
    warningZone.setAttribute('width', '40');
    warningZone.setAttribute('height', '100');
    warningZone.setAttribute('fill', 'rgba(245, 158, 11, 0.03)');
    urgencyBg.appendChild(warningZone);

    // 右侧安全区 (70-100)
    const healthyZone = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    healthyZone.setAttribute('x', '70');
    healthyZone.setAttribute('y', '0');
    healthyZone.setAttribute('width', '30');
    healthyZone.setAttribute('height', '100');
    healthyZone.setAttribute('fill', 'rgba(16, 185, 129, 0.03)');
    urgencyBg.appendChild(healthyZone);

    svgContainer.appendChild(urgencyBg);
}

// 更新节点的紧迫性样式
function updateNodeUrgencyStyle(nodeEl, urgency) {
    const color = getUrgencyColor(urgency, 0.8);
    const glowColor = getUrgencyColor(urgency, 0.4);

    // 更新边框颜色
    nodeEl.style.borderColor = color;
    nodeEl.style.setProperty('--node-accent', getUrgencyColor(urgency, 1));
    nodeEl.style.setProperty('--node-soft', getUrgencyColor(urgency, 0.12));

    // 更新光晕
    const glowEl = nodeEl.querySelector('.node-glow');
    if (glowEl) {
        glowEl.style.background = `radial-gradient(circle, ${glowColor} 0%, transparent 70%)`;
    }
}

// 绘制基于紧迫性的连接线
function drawUrgencyConnections(svgContainer, nodesContainer, nodePositions) {
    const allNodes = nodesContainer.querySelectorAll('.holo-node');
    const connectionsDrawn = new Set(); // 避免重复绘制

    // 绘制父子连接（树形连接）
    allNodes.forEach(node => {
        const parentId = node.dataset.parent;
        if (!parentId) return;

        const childPos = nodePositions.get(node.dataset.id);
        const parentPos = nodePositions.get(parentId);
        if (!childPos || !parentPos) return;

        const connectionKey = `${parentId}-${node.dataset.id}`;
        if (connectionsDrawn.has(connectionKey)) return;
        connectionsDrawn.add(connectionKey);

        // 获取子节点状态决定连线颜色
        const nodeData = knowledgeNodesCache.find(n => n.node_id === node.dataset.id);
        const urgency = nodeData ? calculateNodeUrgency(nodeData).score : 50;

        drawConnectionLine(svgContainer, parentPos, childPos, 'tree', urgency);
    });

    // 绘制AI识别的相关连接
    knowledgeNodesCache.forEach(nodeData => {
        const relatedList = nodeData.related_node_ids || [];
        const sourcePos = nodePositions.get(nodeData.node_id);
        if (!sourcePos) return;

        relatedList.forEach(rel => {
            const targetPos = nodePositions.get(rel.node_id);
            if (!targetPos) return;

            const connectionKey = `${nodeData.node_id}-${rel.node_id}`;
            if (connectionsDrawn.has(connectionKey)) return;
            connectionsDrawn.add(connectionKey);

            drawConnectionLine(svgContainer, sourcePos, targetPos, rel.type, rel.strength || 0.5);
        });
    });
}

// 绘制单条连接线
function drawConnectionLine(svgContainer, fromPos, toPos, type, param = 0.5) {
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'path');

    // 转换为实际坐标
    const x1 = fromPos.x;
    const y1 = fromPos.y;
    const x2 = toPos.x;
    const y2 = toPos.y;

    // 创建贝塞尔曲线
    const midY = (y1 + y2) / 2;
    let d;

    if (type === 'tree') {
        // 树形连接 - 向上/向下的曲线
        d = `M${x1} ${y1} Q${x1} ${midY} ${x2} ${y2}`;
        line.setAttribute('stroke', getUrgencyColor(param, 0.6));
        line.setAttribute('stroke-width', '0.8');
        line.setAttribute('stroke-dasharray', 'none');
    } else if (type === 'prerequisite') {
        // 前置知识连接 - 虚线+箭头
        d = `M${x1} ${y1} L${x2} ${y2}`;
        line.setAttribute('stroke', 'rgba(168, 85, 247, 0.7)');
        line.setAttribute('stroke-width', '0.6');
        line.setAttribute('stroke-dasharray', '3,2');
        line.setAttribute('marker-end', 'url(#arrowPrerequisite)');
    } else if (type === 'related') {
        // 相关知识连接 - 点线
        d = `M${x1} ${y1} L${x2} ${y2}`;
        line.setAttribute('stroke', 'rgba(59, 130, 246, 0.5)');
        line.setAttribute('stroke-width', '0.4');
        line.setAttribute('stroke-dasharray', '1,2');
        line.setAttribute('marker-end', 'url(#arrowRelated)');
    } else {
        return;
    }

    line.setAttribute('d', d);
    line.setAttribute('fill', 'none');
    line.setAttribute('filter', 'url(#connectionGlow)');
    line.style.opacity = '0';
    line.style.transition = 'opacity 0.5s ease';

    svgContainer.appendChild(line);

    setTimeout(() => {
        line.style.opacity = type === 'tree' ? '0.6' : '0.4';
    }, 100);
}

// ============================================
// Theme Toggle System
// ============================================
const THEME_STORAGE_KEY = 'hub-theme';

function initThemeToggle() {
    const toggleBtn = document.getElementById('theme-toggle');
    if (!toggleBtn) {
        console.warn('Theme toggle button not found');
        return;
    }

    const savedTheme = localStorage.getItem(THEME_STORAGE_KEY);
    const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const initialTheme = savedTheme || (systemPrefersDark ? 'dark' : 'light');

    setTheme(initialTheme);

    toggleBtn.addEventListener('click', () => {
        const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        setTheme(newTheme);
        localStorage.setItem(THEME_STORAGE_KEY, newTheme);
    });

    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        if (!localStorage.getItem(THEME_STORAGE_KEY)) {
            setTheme(e.matches ? 'dark' : 'light');
        }
    });
}

function setTheme(theme) {
    if (theme !== 'light' && theme !== 'dark') {
        console.warn('Invalid theme:', theme, 'Defaulting to light');
        theme = 'light';
    }

    document.documentElement.setAttribute('data-theme', theme);

    const toggleBtn = document.getElementById('theme-toggle');
    if (toggleBtn) {
        if (theme === 'dark') {
            toggleBtn.setAttribute('aria-label', '切换到浅色模式');
        } else {
            toggleBtn.setAttribute('aria-label', '切换到深色模式');
        }
    }

    document.body.classList.remove('theme-light', 'theme-dark');
    document.body.classList.add(`theme-${theme}`);
}

// ============================================
// Personalized Content based on Assessment
// ============================================
function initPersonalizedContent() {
    const user = JSON.parse(localStorage.getItem('starlearn_user') || '{}');

    if (!user.hasCompletedAssessment) {
        // User hasn't completed assessment, redirect to assessment page
        console.log('[Hub] User has not completed assessment, redirecting...');
        // Don't redirect here, allow viewing hub but show default content
        return;
    }

    // Update welcome message with personalized info
    updateWelcomeMessage(user);

    // Update recommended learning path based on profile
    updateRecommendedPath(user);

    // Update study recommendations based on radar scores
    updateStudyRecommendations(user);

    // Update peer pods to show compatible study partners
    updatePeerRecommendations(user);

    console.log('[Hub] Personalized content initialized with profile:', user.profile);
}

function updateWelcomeMessage(user) {
    const welcomeEl = document.querySelector('.welcome-section h1');
    if (!welcomeEl) return;

    const profile = user.profile || {};
    const direction = profile.learningDirection || '大数据技术';
    const level = profile.knowledgeBase || '基础入门';

    welcomeEl.textContent = `欢迎回来，${direction}学习者`;
}

function updateRecommendedPath(user) {
    const pathNodes = document.querySelectorAll('.path-node');
    const profile = user.profile || {};
    const learningPath = user.learningPath || [];

    if (learningPath.length === 0) return;

    pathNodes.forEach((node, index) => {
        if (learningPath[index]) {
            node.dataset.task = learningPath[index].topic;
            const titleEl = node.querySelector('.node-title');
            if (titleEl) {
                titleEl.textContent = learningPath[index].topic;
            }
            const descEl = node.querySelector('.node-desc');
            if (descEl) {
                descEl.textContent = learningPath[index].desc;
            }

            // Update status based on path
            node.classList.remove('current', 'completed', 'pending');
            node.classList.add(learningPath[index].status || 'pending');
        }
    });
}

function updateStudyRecommendations(user) {
    const radarScores = user.radarScores || [];
    const radarLabels = user.radarLabels || ['知识掌握', '实战能力', '学习效率', '内容记忆', '问题解决', '技术深度'];

    if (radarScores.length !== 6) return;

    // Find weakest dimension
    const minScore = Math.min(...radarScores);
    const minIndex = radarScores.indexOf(minScore);
    const weakDimension = radarLabels[minIndex];

    // Update recommendation cards based on weak areas
    const recCards = document.querySelectorAll('.recommendation-card');
    recCards.forEach(card => {
        const titleEl = card.querySelector('.rec-title');
        if (titleEl && minScore < 50) {
            // Add emphasis on weak dimension
            const badge = card.querySelector('.weakness-badge');
            if (badge) {
                badge.textContent = `需加强: ${weakDimension}`;
                badge.style.display = 'inline-block';
            }
        }
    });

    // Update stream topics based on radar scores
    const streamTopics = document.querySelectorAll('.stream-topic');
    streamTopics.forEach((topic, index) => {
        // Prioritize content for weak dimensions
        if (index < 3 && minScore < 60) {
            topic.classList.add('priority-topic');
        }
    });
}

function updatePeerRecommendations(user) {
    const profile = user.profile || {};
    const peerPods = document.querySelectorAll('.peer-pod');

    peerPods.forEach(pod => {
        // Filter peers by compatible learning direction
        const podDirection = pod.dataset.direction;
        if (profile.learningDirection && podDirection !== profile.learningDirection) {
            pod.style.opacity = '0.5';
        }
    });
}

// ============================================
// User Avatar Initialization
// ============================================
function initUserAvatar() {
    const user = JSON.parse(localStorage.getItem('starlearn_user') || '{}');
    if (user && user.avatar) {
        const avatarImg = document.querySelector('#user-avatar img.user-avatar');
        if (avatarImg) {
            avatarImg.src = user.avatar;
        }
    }
}

// ============================================
// 今日要闻 (Daily News) Fetching with Caching
// ============================================
const NEWS_CACHE_KEY = 'starlearn_daily_news';
const NEWS_CACHE_DURATION = 12 * 60 * 60 * 1000; // 12小时缓存

function getCategoryClass(category) {
    const categoryMap = {
        'AI科技': 'ai',
        'AI': 'ai',
        '人工智能': 'ai',
        '民生': 'livelihood',
        '生活': 'life',
        '国际形势': 'international',
        '国际': 'international',
        'Web': 'web',
        '云原生': 'cloud',
        '数据': 'data'
    };
    return categoryMap[category] || 'ai';
}

function renderNewsCards(news) {
    const grid = document.getElementById('highlights-grid');
    if (!grid) return;

    grid.innerHTML = '';

    if (!news || news.length === 0) {
        grid.innerHTML = `
            <div class="highlight-error">
                <span class="error-icon">📭</span>
                <span>暂无新闻数据</span>
            </div>
        `;
        return;
    }

    // 只显示7条新闻，不重复
    const displayNews = news.slice(0, 7);

    displayNews.forEach((item, index) => {
        const isMain = index === 0;
        const categoryClass = getCategoryClass(item.category);

        const card = document.createElement('div');
        card.className = `highlight-card ${isMain ? 'highlight-main' : 'highlight-side'}`;

        card.innerHTML = `
            <div class="highlight-category ${categoryClass}">
                <span class="category-tag">${item.category}</span>
                <span class="category-time">${item.timestamp || '今日'}</span>
            </div>
            <div class="highlight-content">
                <h3 class="highlight-title">${item.title}</h3>
                <p class="highlight-desc">${item.description || item.summary || ''}</p>
            </div>
        `;

        grid.appendChild(card);
    });
}

// ============================================
// 更多资讯弹窗
// ============================================
let allNewsData = [];
let currentNewsCategory = 'all';

function initNewsModal() {
    const modal = document.getElementById('news-modal');
    const overlay = document.getElementById('news-modal-overlay');
    const closeBtn = document.getElementById('news-modal-close');
    const moreBtn = document.getElementById('more-news-btn');
    const tabs = document.querySelectorAll('.news-tab');

    if (!modal) return;

    // 点击"查看更多"按钮
    if (moreBtn) {
        moreBtn.addEventListener('click', openNewsModal);
    }

    // 点击遮罩关闭
    if (overlay) {
        overlay.addEventListener('click', closeNewsModal);
    }

    // 点击关闭按钮
    if (closeBtn) {
        closeBtn.addEventListener('click', closeNewsModal);
    }

    // Tab 切换
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const category = tab.dataset.category;
            currentNewsCategory = category;

            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            renderModalNews();
        });
    });

    // ESC 键关闭
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal.classList.contains('active')) {
            closeNewsModal();
        }
    });
}

async function openNewsModal() {
    const modal = document.getElementById('news-modal');
    const body = document.getElementById('news-modal-body');
    if (!modal || !body) return;

    modal.classList.add('active');
    document.body.style.overflow = 'hidden';

    // 如果没有数据，先加载
    if (allNewsData.length === 0) {
        body.innerHTML = `
            <div class="news-modal-loading">
                <div class="loading-spinner"></div>
                <span>正在加载资讯...</span>
            </div>
        `;

        try {
            const response = await fetch('/api/news/more');
            const data = await response.json();
            if (data.success && data.news) {
                allNewsData = data.news;
                renderModalNews();
            } else {
                throw new Error('Failed to fetch news');
            }
        } catch (e) {
            body.innerHTML = `
                <div class="news-modal-error">
                    <div class="news-modal-empty-icon">😵</div>
                    <p>资讯加载失败</p>
                    <button class="more-btn" onclick="reloadMoreNews()" style="margin-top:12px">重新加载</button>
                </div>
            `;
        }
    } else {
        renderModalNews();
    }
}

function closeNewsModal() {
    const modal = document.getElementById('news-modal');
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = '';
    }
}

function renderModalNews() {
    const body = document.getElementById('news-modal-body');
    if (!body) return;

    let filteredNews = allNewsData;
    if (currentNewsCategory !== 'all') {
        filteredNews = allNewsData.filter(n => n.category === currentNewsCategory);
    }

    if (filteredNews.length === 0) {
        body.innerHTML = `
            <div class="news-modal-empty">
                <div class="news-modal-empty-icon">📭</div>
                <p>暂无${currentNewsCategory === 'all' ? '' : currentNewsCategory}相关资讯</p>
            </div>
        `;
        return;
    }

    const getCategoryClass = (category) => {
        const map = { 'AI科技': 'ai', '民生': 'livelihood', '生活': 'life', '国际形势': 'international' };
        return map[category] || 'ai';
    };

    body.innerHTML = `
        <div class="news-modal-list">
            ${filteredNews.map(news => `
                <div class="news-modal-item" onclick="openNewsLink('${news.link || ''}')">
                    <div class="news-item-header">
                        <span class="news-item-category ${getCategoryClass(news.category)}">${news.category}</span>
                        <span class="news-item-time">${news.timestamp}</span>
                    </div>
                    <h4 class="news-item-title">${news.title}</h4>
                    <p class="news-item-desc">${news.description}</p>
                    <div class="news-item-footer">
                        <span class="news-item-source">${news.source}</span>
                        ${news.link ? '<span class="news-item-link">阅读原文 →</span>' : ''}
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}

function openNewsLink(link) {
    if (link && link.startsWith('http')) {
        window.open(link, '_blank');
    }
}

async function reloadMoreNews() {
    allNewsData = [];
    await openNewsModal();
}

function getCachedNews() {
    try {
        const cached = localStorage.getItem(NEWS_CACHE_KEY);
        if (!cached) return null;

        const { news, date, timestamp } = JSON.parse(cached);
        const now = Date.now();
        const cacheAge = now - timestamp;

        // 缓存超过12小时，视为过期
        if (cacheAge > NEWS_CACHE_DURATION) {
            return null;
        }

        return { news, date, isStale: cacheAge > 6 * 60 * 60 * 1000 }; // 超过6小时显示刷新提示
    } catch (e) {
        return null;
    }
}

function setCachedNews(news, date) {
    try {
        localStorage.setItem(NEWS_CACHE_KEY, JSON.stringify({
            news,
            date,
            timestamp: Date.now()
        }));
    } catch (e) {
        console.warn('[Hub] Failed to cache news:', e);
    }
}

async function fetchTodayNews(showLoading = false) {
    const grid = document.getElementById('highlights-grid');
    const dateEl = document.getElementById('news-date');

    // 先尝试从缓存读取
    const cached = getCachedNews();
    if (cached && cached.news) {
        if (dateEl && cached.date) {
            const dateParts = cached.date.match(/(\d+)年(\d+)月(\d+)日/);
            if (dateParts) {
                const weekday = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][new Date().getDay()];
                dateEl.textContent = `${dateParts[2]}月${dateParts[3]}日 · ${weekday}`;
            }
        }
        renderNewsCards(cached.news);

        // 缓存过期了，在后台静默更新
        if (cached.isStale) {
            silentRefreshNews();
        }
        return;
    }

    // 无缓存，显示加载状态（仅首次）
    if (showLoading && grid) {
        grid.innerHTML = `
            <div class="highlight-loading">
                <div class="loading-spinner"></div>
                <span>正在加载今日要闻...</span>
            </div>
        `;
    }

    try {
        const response = await fetch('/api/news/today');
        const data = await response.json();

        if (data.success && data.news) {
            if (dateEl && data.date) {
                const dateParts = data.date.match(/(\d+)年(\d+)月(\d+)日/);
                if (dateParts) {
                    const weekday = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][new Date().getDay()];
                    dateEl.textContent = `${dateParts[2]}月${dateParts[3]}日 · ${weekday}`;
                }
            }

            setCachedNews(data.news, data.date);
            renderNewsCards(data.news);
        } else {
            throw new Error('Failed to fetch news');
        }
    } catch (error) {
        console.error('[Hub] Failed to fetch today news:', error);

        if (grid) {
            grid.innerHTML = `
                <div class="highlight-error">
                    <span class="error-icon">😵</span>
                    <span>新闻加载失败</span>
                    <button class="retry-btn" onclick="fetchTodayNews(true)">重新加载</button>
                </div>
            `;
        }
    }
}

// ============================================
// 侧边栏与导航控制
// ============================================
function toggleSidebar() {
    const sidebar = document.getElementById('hub-sidebar');
    sidebar.classList.toggle('open');
}

function updateNotificationDot() {
    const notificationDot = document.getElementById('notification-dot');
    if (!notificationDot) return;
    const unreadCount = document.querySelectorAll('.notification-item.unread').length;
    if (unreadCount > 0) {
        notificationDot.classList.add('active');
    } else {
        notificationDot.classList.remove('active');
    }
}

function initSidebarAndNotifications() {
    // 侧边栏切换
    document.getElementById('sidebar-toggle')?.addEventListener('click', function(e) {
        e.stopPropagation();
        toggleSidebar();
    });

    // 点击其他区域关闭侧边栏
    document.addEventListener('click', function(e) {
        const sidebar = document.getElementById('hub-sidebar');
        const toggle = document.getElementById('sidebar-toggle');
        if (sidebar?.classList.contains('open') &&
            !sidebar.contains(e.target) &&
            !toggle?.contains(e.target)) {
            sidebar.classList.remove('open');
        }
    });

    // 导航高亮
    document.querySelectorAll('.nav-item').forEach(item => {
        const href = item.getAttribute('href');
        if (href && href !== '#' && window.location.pathname === href) {
            document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
            item.classList.add('active');
        }
    });

    // 导航点击处理
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            if (!href || href === '#') {
                e.preventDefault();
                document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
                this.classList.add('active');
                const section = this.dataset.section;
                const target = document.getElementById('section-' + section);
                if (target) {
                    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            } else {
                document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
                this.classList.add('active');
            }
        });
    });

    // 通知面板
    const notificationBtn = document.getElementById('notification-btn');
    const notificationPanel = document.getElementById('notification-panel');
    const notificationBackdrop = document.getElementById('notification-backdrop');
    const markAllRead = document.getElementById('mark-all-read');
    const notificationItems = document.querySelectorAll('.notification-item');

    notificationBtn?.addEventListener('click', function(e) {
        e.stopPropagation();
        notificationPanel?.classList.toggle('active');
        notificationBackdrop?.classList.toggle('active');
    });

    notificationBackdrop?.addEventListener('click', function() {
        notificationPanel?.classList.remove('active');
        notificationBackdrop?.classList.remove('active');
    });

    markAllRead?.addEventListener('click', function() {
        notificationItems.forEach(item => {
            item.classList.remove('unread');
        });
        notificationDot?.classList.remove('active');
    });

    notificationItems.forEach(item => {
        item.addEventListener('click', function() {
            this.classList.remove('unread');
            updateNotificationDot();
        });
    });

    updateNotificationDot();

    // 初始化更多资讯弹窗
    initNewsModal();
}

// 通知持久化存储
const NOTIF_STORAGE_KEY = 'starlearn_notifications';

function getStoredNotifications() {
    try {
        return JSON.parse(localStorage.getItem(NOTIF_STORAGE_KEY) || '[]');
    } catch (e) { return []; }
}

function saveNotificationToStorage(notif) {
    const list = getStoredNotifications();
    list.unshift({ ...notif, id: Date.now(), time: new Date().toLocaleString('zh-CN') });
    if (list.length > 50) list.splice(50);
    localStorage.setItem(NOTIF_STORAGE_KEY, JSON.stringify(list));
    // 同步到服务端数据库
    if (window.StarData) StarData.setNotifications(list);
}

// 添加通知到 hub 面板
function addNotificationToHubPanel(payload) {
    const { title = '', content = '', type = 'system', actionLabel = '', actionUrl = '' } = payload || {};
    const list = document.getElementById('notification-list');
    if (!list) return;

    const iconMap = {
        achievement: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"/></svg>`,
        seed: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"/></svg>`,
        system: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`,
        reminder: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`
    };

    const colorMap = {
        achievement: 'achievement',
        seed: 'business',
        system: 'system',
        reminder: 'activity'
    };

    const icon = iconMap[type] || iconMap.system;
    const colorClass = colorMap[type] || 'system';

    const item = document.createElement('div');
    item.className = 'notification-item unread';
    item.innerHTML = `
        <div class="notification-icon ${colorClass}">${icon}</div>
        <div class="notification-content">
            <p class="notification-title">${escapeHtml(title)}</p>
            <p class="notification-text">${escapeHtml(content)}</p>
            <span class="notification-time">刚刚</span>
            ${actionLabel ? `<button class="notif-action-btn">${escapeHtml(actionLabel)}</button>` : ''}
        </div>
    `;

    item.addEventListener('click', () => {
        item.classList.remove('unread');
        updateNotificationDot();
    });

    // 操作按钮点击 - 跳转到目标页面
    if (actionLabel && actionUrl) {
        const actionBtn = item.querySelector('.notif-action-btn');
        if (actionBtn) {
            actionBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                window.location.href = actionUrl;
            });
        }
    }

    // 插入到最前面
    list.insertBefore(item, list.firstChild);

    // 持久化
    saveNotificationToStorage({ title, content, type, actionLabel, actionUrl });

    // 更新红点
    updateNotificationDot();

    // 同步到所有打开的 hub 页面（跨标签页）
    localStorage.setItem('starlearn_notifications_last_update', String(Date.now()));
}

// 监听 achievement-unlocked 事件
document.addEventListener('achievement-unlocked', (e) => {
    const { achievement } = e.detail || {};
    if (achievement) {
        addNotificationToHubPanel({
            title: '🏆 成就解锁',
            content: `${achievement.name} - ${achievement.desc}`,
            type: 'achievement'
        });
    }
});

// 监听 starlearnNotifications 调用（统一拦截）
const _origShowNotif = window.starlearnNotifications?.showNotification;
window.starlearnNotifications = window.starlearnNotifications || { showNotification: () => {} };
const _origFn = window.starlearnNotifications.showNotification.bind(window.starlearnNotifications);
window.starlearnNotifications.showNotification = function(payload) {
    _origFn(payload);
    addNotificationToHubPanel(payload);
};

// 跨标签页同步通知
window.addEventListener('storage', (e) => {
    if (e.key === 'starlearn_notifications_last_update') {
        const list = document.getElementById('notification-list');
        if (!list) return;
        const stored = getStoredNotifications();
        // 去重后重新渲染
        const existingIds = new Set(
            Array.from(list.querySelectorAll('.notification-item')).map(el => el.dataset.tempId).filter(Boolean)
        );
        stored.forEach(n => {
            if (!existingIds.has(String(n.id))) {
                const item = document.createElement('div');
                item.className = 'notification-item';
                item.dataset.tempId = n.id;
                const iconMap = {
                    achievement: 'achievement', seed: 'business', system: 'system', reminder: 'activity'
                };
                const iconSvg = {
                    achievement: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"/></svg>`,
                    seed: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"/></svg>`,
                    system: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`,
                    reminder: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`
                };
                item.innerHTML = `
                    <div class="notification-icon ${iconMap[n.type] || 'system'}">${iconSvg[n.type] || iconSvg.system}</div>
                    <div class="notification-content">
                        <p class="notification-title">${escapeHtml(n.title)}</p>
                        <p class="notification-text">${escapeHtml(n.content)}</p>
                        <span class="notification-time">${n.time || '刚刚'}</span>
                        ${n.actionLabel ? `<button class="notif-action-btn">${escapeHtml(n.actionLabel)}</button>` : ''}
                    </div>
                `;
                item.addEventListener('click', () => {
                    item.classList.remove('unread');
                    updateNotificationDot();
                });
                // 操作按钮导航
                if (n.actionLabel && n.actionUrl) {
                    const btn = item.querySelector('.notif-action-btn');
                    if (btn) {
                        btn.addEventListener('click', (e) => {
                            e.stopPropagation();
                            window.location.href = n.actionUrl;
                        });
                    }
                }
                list.insertBefore(item, list.firstChild);
                updateNotificationDot();
            }
        });
    }
});

// 跨页面学习数据实时同步 - 其他页面更新学习时间时自动刷新概览
window.addEventListener('storage', (e) => {
    if (e.key === 'starlearn_learning_update') {
        loadStudyOverviewData();
        initTrendChart();
        initHeatmap(heatmapCurrentPeriod);
        loadFocusTasks();
        loadFocusCalendar();
        loadLearningDomains();
    }
});

function escapeHtml(str) {
    if (!str && str !== 0) return '';
    return String(str).replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":"&#39;"})[c]);
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', initSidebarAndNotifications);

// 后台静默刷新新闻（缓存超过6小时时触发）
async function silentRefreshNews() {
    try {
        const response = await fetch('/api/news/today');
        const data = await response.json();

        if (data.success && data.news) {
            setCachedNews(data.news, data.date);
            const cached = getCachedNews();
            if (cached && !cached.isStale) {
                renderNewsCards(data.news);
            }
        }
    } catch (e) {
        // 静默失败，不打扰用户
    }
}

// ============================================
// Initialize
// ============================================
document.addEventListener('DOMContentLoaded', function() {
    initThemeToggle();
    createDataParticles();
    initDailyRoute();
    initStudyHall();
    animateRadialProgress();
    animateBarCharts();
    animateLineChart();
    parseCourseParams();
    initHoloEcosystem();
    initPersonalizedContent();
    initUserAvatar();
    // 使用缓存，不显示加载状态
    fetchTodayNews(false);
    // 学习概览图表 (异步加载)
    initOverviewDate();
    loadStudyOverviewData();
    initTrendChart();
    initHeatmap('week');
    // 加载动态数据
    syncLearningMinute(); // 立即同步一次学习时长
    loadFocusTasks();     // 加载专注任务
    loadFocusCalendar();  // 加载专注日历
    loadLearningDomains(); // 加载学习领域

    // 热力图切换按钮事件
    document.querySelectorAll('.heatmap-toggle .toggle-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.heatmap-toggle .toggle-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            initHeatmap(btn.dataset.period);
        });
    });

    // 每分钟同步一次学习时长
    setInterval(syncLearningMinute, 60000);

    // 定时轮询学习数据（每2分钟）
    let studyPollInterval = setInterval(() => {
        loadStudyOverviewData();
        initTrendChart();
        initHeatmap(heatmapCurrentPeriod);
    }, 120000);

    // 页面隐藏时暂停轮询，显示时恢复并立即刷新
    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            clearInterval(studyPollInterval);
            studyPollInterval = null;
        } else {
            loadStudyOverviewData();
            initTrendChart();
            initHeatmap(heatmapCurrentPeriod);
            studyPollInterval = setInterval(() => {
                loadStudyOverviewData();
                initTrendChart();
                initHeatmap(heatmapCurrentPeriod);
            }, 120000);
        }
    });
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
