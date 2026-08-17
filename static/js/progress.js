/* ============================================================
   学习进度页 — 数据渲染与交互
   适配重构后的 HTML 结构
   ============================================================ */

const PROGRESS_CONFIG = {
    radar: {
        labels: ['编程能力', '算法思维', '系统设计', '工程实践', '理论知识'],
        // 五边形 (cx=160, cy=140, r=100) 的 5 个顶点
        center: { x: 160, y: 140 },
        radius: 100,
        rings: 4,
    },
    achievements: [
        { id: 'first-course',    icon: '🏆', name: '初露锋芒', desc: '完成第一门课程',     threshold: { completed_courses: 1 } },
        { id: 'streak-7',        icon: '🔥', name: '连续 7 天', desc: '坚持学习一周',     threshold: { current_streak: 7 } },
        { id: 'course-10',       icon: '📚', name: '学富五车',  desc: '完成 10 门课程',    threshold: { completed_courses: 10 } },
        { id: 'algorithm-100',   icon: '⚡', name: '刷题达人',  desc: '完成 100 道算法题', threshold: { total_hours: 50 } },
        { id: 'hours-100',       icon: '🌟', name: '学习之星',  desc: '累计学习 100 小时', threshold: { total_hours: 100 } },
        { id: 'year-goal',       icon: '🎯', name: '年度目标',  desc: '完成年度学习计划',   threshold: { total_hours: 500 } },
    ],
    progressClass: ['primary', 'success', 'warning', 'info', 'danger'],
};

document.addEventListener('DOMContentLoaded', function() {
    initTimeRange();
    initRadarSkeleton();
    loadProgressSummary();
});

/* ---------- 1. 工具函数 ---------- */

function getCurrentUserId() {
    try {
        const user = JSON.parse(localStorage.getItem('starlearn_user') || '{}');
        return user.id || null;
    } catch (e) {
        return null;
    }
}

function escapeHtml(value) {
    return String(value == null ? '' : value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function formatHours(value) {
    const num = Number(value) || 0;
    if (num < 10) return num.toFixed(1);
    return Math.round(num).toString();
}

function formatDelta(current, previous) {
    if (previous == null || isNaN(previous)) {
        return { text: '—', cls: 'neutral' };
    }
    const diff = current - previous;
    if (Math.abs(diff) < 0.05) {
        return { text: '与上次持平', cls: 'neutral' };
    }
    const sign = diff > 0 ? '+' : '';
    return {
        text: `${sign}${diff.toFixed(1)} 较上期`,
        cls: diff > 0 ? 'up' : 'down',
    };
}

/* ---------- 2. 时间段选择 ---------- */

function initTimeRange() {
    document.querySelectorAll('.time-range-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const range = this.dataset.range;
            if (!range) return;
            document.querySelectorAll('.time-range-btn').forEach(b => {
                b.classList.remove('active');
                b.setAttribute('aria-selected', 'false');
            });
            this.classList.add('active');
            this.setAttribute('aria-selected', 'true');
            loadProgressSummary(range);
        });
    });
}

function getCurrentRange() {
    const active = document.querySelector('.time-range-btn.active');
    return active?.dataset.range || 'month';
}

/* ---------- 3. 数据加载 ---------- */

async function loadProgressSummary(range) {
    const rangeKey = range || getCurrentRange();
    renderLoadingState();

    const userId = getCurrentUserId();
    if (!userId || window.StarDemoData?.isForced?.()) {
        renderDemoProgress(rangeKey);
        return;
    }

    try {
        const response = await fetch(`/api/progress/summary/${userId}?range=${encodeURIComponent(rangeKey)}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        if (!data.success) throw new Error(data.detail || 'load progress failed');

        // 真实数据为空时自动填充演示假数据，便于预览页面效果
        if (isEmptySummary(data.summary)) {
            renderDemoProgress(rangeKey);
            return;
        }

        // 保存上一期数据用于计算 delta
        window.__progressPrev = window.__progressCurrent || {};
        window.__progressCurrent = data.summary || {};
        renderProgressSummary(data.summary || {}, window.__progressPrev);
    } catch (error) {
        console.error('加载学习进度失败:', error);
        if (window.toast?.error) {
            window.toast.error('学习数据加载失败');
        }
        renderDemoProgress(rangeKey);
    }
}

/** 判断真实数据是否为空（四项核心指标全部无数据） */
function isEmptySummary(summary) {
    if (!summary) return true;
    const hasHours = Number(summary.total_hours) > 0;
    const hasCourses = Number(summary.completed_courses) > 0;
    const hasProgress = Array.isArray(summary.course_progress) && summary.course_progress.length > 0;
    const hasActivity = Array.isArray(summary.weekly_activity)
        && summary.weekly_activity.some(d => Number(d.hours) > 0);
    return !hasHours && !hasCourses && !hasProgress && !hasActivity;
}

/** 渲染演示假数据（见 demo-data.js） */
function renderDemoProgress(rangeKey) {
    const demo = window.StarDemoData?.getProgressSummary?.(rangeKey);
    if (!demo) {
        renderLoginRequired();
        return;
    }
    window.__progressPrev = {};
    window.__progressCurrent = demo;
    renderProgressSummary(demo, {});
    window.StarDemoData.showBadge();
    console.info('[progress] 当前展示演示数据（未登录 / 无真实数据 / ?demo=1）');
}

function renderLoginRequired() {
    const root = document.querySelector('.progress-root') || document.body;
    root.innerHTML = '' +
        '<div class="progress-empty">' +
            '<div class="progress-empty-icon">✦</div>' +
            '<h3 class="progress-empty-title">请先登录</h3>' +
            '<p class="progress-empty-desc">登录后即可查看你的学习进度</p>' +
            '<a href="/login.html" class="progress-empty-btn">前往登录</a>' +
        '</div>';
}

/* ---------- 4. 渲染总入口 ---------- */

function renderProgressSummary(summary, prev) {
    renderStat('total-hours', Number(summary.total_hours) || 0, formatHours, prev.total_hours);
    renderStat('completed-courses', Number(summary.completed_courses) || 0, v => Math.round(v).toString(), prev.completed_courses);
    renderStat('current-streak', Number(summary.current_streak) || 0, v => Math.round(v).toString(), prev.current_streak);
    renderStat('avg-daily', Number(summary.avg_daily_hours) || 0, formatHours, prev.avg_daily_hours);

    renderWeeklyChart(summary.weekly_activity || []);
    renderCourseProgress(summary.course_progress || []);
    renderRadar(summary.radar || getDefaultRadar());
    renderTimeline(summary.timeline || []);
    renderAchievements(summary);
}

/* ---------- 5. 加载态 / 空态 ---------- */

function renderLoadingState() {
    ['total-hours', 'completed-courses', 'current-streak', 'avg-daily'].forEach(key => {
        const card = document.querySelector(`[data-stat="${key}"]`);
        if (!card) return;
        const valEl = card.querySelector('[data-field="value"]');
        const deltaEl = card.querySelector('[data-field="delta"]');
        if (valEl) valEl.textContent = key === 'avg-daily' ? '0.0' : '0';
        if (deltaEl) {
            deltaEl.textContent = '加载中…';
            deltaEl.className = 'stat-card-delta neutral';
        }
    });

    renderWeeklyChartSkeleton();
    renderCourseProgressSkeleton();
    renderTimelineSkeleton();
}

function renderEmpty(container, title = '暂无数据', desc = '') {
    if (!container) return;
    container.innerHTML = `
        <div class="empty-state">
            <div class="empty-state-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="9"/>
                    <line x1="12" y1="8" x2="12" y2="12"/>
                    <line x1="12" y1="16" x2="12.01" y2="16"/>
                </svg>
            </div>
            <p class="empty-state-title">${escapeHtml(title)}</p>
            ${desc ? `<p class="empty-state-desc">${escapeHtml(desc)}</p>` : ''}
        </div>
    `;
}

function renderWeeklyChartSkeleton() {
    const container = document.getElementById('weekly-chart');
    if (!container) return;
    const dayNames = ['一', '二', '三', '四', '五', '六', '日'];
    container.classList.remove('bar-chart');
    container.innerHTML = `
        <div class="bar-chart">
            ${dayNames.map(d => `
                <div class="bar-col">
                    <div class="bar-fill" style="height: 4%; background: var(--surface-hover);"></div>
                    <div class="bar-label">${d}</div>
                </div>
            `).join('')}
        </div>
    `;
}

function renderCourseProgressSkeleton() {
    const container = document.getElementById('course-progress-list');
    if (!container) return;
    container.innerHTML = Array.from({ length: 4 }).map(() => `
        <div class="progress-item">
            <div class="progress-item-head">
                <div class="progress-item-name">
                    <span class="progress-item-icon">📚</span>
                    <span class="progress-item-name-text" style="width: 80px; height: 12px; background: var(--surface-hover); border-radius: 4px; display: inline-block;"></span>
                </div>
                <span class="progress-item-value" style="width: 32px; height: 12px; background: var(--surface-hover); border-radius: 4px; display: inline-block;"></span>
            </div>
            <div class="progress-bar-track">
                <div class="progress-bar-fill" style="width: 0; background: var(--surface-hover);"></div>
            </div>
        </div>
    `).join('');
}

function renderTimelineSkeleton() {
    const container = document.getElementById('learning-timeline');
    if (!container) return;
    container.innerHTML = Array.from({ length: 3 }).map(() => `
        <div class="timeline-item">
            <div class="timeline-dot pending"></div>
            <div class="timeline-content">
                <div class="timeline-head">
                    <span class="timeline-title" style="width: 120px; height: 12px; background: var(--surface-hover); border-radius: 4px; display: inline-block;"></span>
                    <span class="timeline-time" style="width: 48px; height: 10px; background: var(--surface-hover); border-radius: 4px; display: inline-block;"></span>
                </div>
                <p class="timeline-desc" style="width: 60%; height: 10px; background: var(--surface-hover); border-radius: 4px; display: inline-block;"></p>
            </div>
        </div>
    `).join('');
}

/* ---------- 6. 顶部统计卡 ---------- */

function renderStat(key, value, formatter, prevValue) {
    const card = document.querySelector(`[data-stat="${key}"]`);
    if (!card) return;
    const valEl = card.querySelector('[data-field="value"]');
    const deltaEl = card.querySelector('[data-field="delta"]');
    if (!valEl || !deltaEl) return;

    animateNumber(valEl, value, formatter);
    const delta = formatDelta(value, prevValue);
    deltaEl.textContent = delta.text;
    deltaEl.className = `stat-card-delta ${delta.cls}`;
}

function animateNumber(el, target, formatter) {
    const start = Number(el.textContent) || 0;
    const duration = 600;
    const startTime = performance.now();
    const easeOut = t => 1 - Math.pow(1 - t, 3);

    function update(now) {
        const progress = Math.min((now - startTime) / duration, 1);
        const v = start + (target - start) * easeOut(progress);
        el.textContent = formatter(v);
        if (progress < 1) requestAnimationFrame(update);
    }
    requestAnimationFrame(update);
}

/* ---------- 7. 周活动柱状图 ---------- */

function renderWeeklyChart(activity) {
    const container = document.getElementById('weekly-chart');
    if (!container) return;

    // 补齐 7 天数据
    const days = ensure7Days(activity);

    if (!days.length || days.every(d => (Number(d.hours) || 0) === 0)) {
        container.classList.add('bar-chart');
        renderEmpty(container, '暂无学习记录', '本时间段内还没有学习活动，开始学习吧 ✨');
        return;
    }

    const maxHours = Math.max(1, ...days.map(d => Number(d.hours) || 0));
    container.classList.add('bar-chart');
    container.innerHTML = days.map(day => {
        const hours = Number(day.hours) || 0;
        const height = Math.max(4, Math.round((hours / maxHours) * 100));
        return `
            <div class="bar-col">
                <div class="bar-fill"
                     style="height: 0%;"
                     data-tooltip="${escapeHtml(day.label || '')} · ${hours.toFixed(1)}h"
                     data-target-height="${height}"></div>
                <div class="bar-label">${escapeHtml(day.dayShort || '')}</div>
                <div class="bar-value">${hours > 0 ? hours.toFixed(1) + 'h' : ''}</div>
            </div>
        `;
    }).join('');

    // 触发动画
    requestAnimationFrame(() => {
        container.querySelectorAll('.bar-fill').forEach((fill, i) => {
            setTimeout(() => {
                fill.style.height = `${fill.dataset.targetHeight}%`;
            }, i * 60);
        });
    });
}

function ensure7Days(activity) {
    const map = {};
    (activity || []).forEach(d => {
        const key = d.date || d.day;
        if (key) map[key] = d;
    });

    // 优先按 ISO 日期补齐；缺数据则显示空
    const today = new Date();
    const labels = ['一', '二', '三', '四', '五', '六', '日'];
    const result = [];
    for (let i = 6; i >= 0; i--) {
        const d = new Date(today);
        d.setDate(today.getDate() - i);
        const iso = d.toISOString().slice(0, 10);
        const item = map[iso] || {};
        const hours = Number(item.hours) || 0;
        const dateObj = new Date(iso);
        const weekday = (dateObj.getDay() + 6) % 7; // 周一=0
        result.push({
            date: iso,
            dayShort: labels[weekday] || '',
            label: `${iso} 周${labels[weekday] || ''}`,
            hours,
            minutes: hours * 60,
        });
    }
    return result;
}

/* ---------- 8. 课程进度 ---------- */

function renderCourseProgress(items) {
    const container = document.getElementById('course-progress-list');
    if (!container) return;

    if (!items || !items.length) {
        renderEmpty(container, '暂无课程或知识点进度', '开始学习一门课程后将自动展示');
        return;
    }

    container.innerHTML = items.map((item, index) => {
        const progress = Math.max(0, Math.min(100, Number(item.progress) || 0));
        const cls = PROGRESS_CONFIG.progressClass[index % PROGRESS_CONFIG.progressClass.length];
        return `
            <div class="progress-item">
                <div class="progress-item-head">
                    <div class="progress-item-name">
                        <span class="progress-item-icon">${escapeHtml(item.icon || '📚')}</span>
                        <span class="progress-item-name-text">${escapeHtml(item.name || '未命名')}</span>
                    </div>
                    <span class="progress-item-value">${progress}%</span>
                </div>
                <div class="progress-bar-track">
                    <div class="progress-bar-fill ${cls}" data-target-width="${progress}"></div>
                </div>
            </div>
        `;
    }).join('');

    requestAnimationFrame(() => {
        container.querySelectorAll('.progress-bar-fill').forEach((bar, i) => {
            const w = bar.dataset.targetWidth;
            setTimeout(() => { bar.style.width = `${w}%`; }, i * 100);
        });
    });
}

/* ---------- 9. 能力雷达 ---------- */

function initRadarSkeleton() {
    const { center, radius, rings, labels } = PROGRESS_CONFIG.radar;
    const grid = document.getElementById('radar-grid');
    const axis = document.getElementById('radar-axis');
    const labelsEl = document.getElementById('radar-labels');

    if (grid) {
        grid.innerHTML = Array.from({ length: rings }).map((_, idx) => {
            const r = radius * ((idx + 1) / rings);
            const points = polygonPoints(center.x, center.y, r, labels.length);
            return `<polygon class="radar-grid-line" points="${points}"/>`;
        }).join('');
    }

    if (axis) {
        axis.innerHTML = labels.map((_, i) => {
            const angle = (Math.PI * 2 * i) / labels.length - Math.PI / 2;
            const x = center.x + Math.cos(angle) * radius;
            const y = center.y + Math.sin(angle) * radius;
            return `<line class="radar-axis-line" x1="${center.x}" y1="${center.y}" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}"/>`;
        }).join('');
    }

    if (labelsEl) {
        labelsEl.innerHTML = labels.map((label, i) => {
            const angle = (Math.PI * 2 * i) / labels.length - Math.PI / 2;
            const x = center.x + Math.cos(angle) * (radius + 18);
            const y = center.y + Math.sin(angle) * (radius + 18);
            const anchor = Math.abs(Math.cos(angle)) < 0.2 ? 'middle'
                : Math.cos(angle) > 0 ? 'start' : 'end';
            return `<text class="radar-label" x="${x.toFixed(1)}" y="${y.toFixed(1)}" text-anchor="${anchor}" dominant-baseline="middle">${escapeHtml(label)}</text>`;
        }).join('');
    }
}

function getDefaultRadar() {
    return PROGRESS_CONFIG.radar.labels.map((_, i) => 50 + (i % 3) * 10);
}

function renderRadar(values) {
    const shape = document.getElementById('radar-shape');
    const pointsEl = document.getElementById('radar-points');
    if (!shape || !pointsEl) return;

    const safeValues = (values || []).map(v => Math.max(0, Math.min(100, Number(v) || 0)));
    if (safeValues.length !== PROGRESS_CONFIG.radar.labels.length) {
        safeValues.length = PROGRESS_CONFIG.radar.labels.length;
        for (let i = 0; i < safeValues.length; i++) {
            if (safeValues[i] == null) safeValues[i] = 0;
        }
    }

    const { center, radius } = PROGRESS_CONFIG.radar;
    const points = safeValues.map((v, i) => {
        const angle = (Math.PI * 2 * i) / safeValues.length - Math.PI / 2;
        const r = (v / 100) * radius;
        const x = center.x + Math.cos(angle) * r;
        const y = center.y + Math.sin(angle) * r;
        return { x, y };
    });

    const pointsAttr = points.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');

    // 首次渲染：直接放置；后续：使用过渡
    if (!shape.getAttribute('points')) {
        shape.setAttribute('points', pointsAttr);
    } else {
        shape.style.transition = 'all 0.6s var(--ease-out)';
        shape.setAttribute('points', pointsAttr);
    }

    pointsEl.innerHTML = points.map((p, i) => {
        const val = safeValues[i];
        return `
            <circle class="radar-point"
                    cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="4"
                    data-tooltip="${escapeHtml(PROGRESS_CONFIG.radar.labels[i])} · ${val}">
            </circle>
        `;
    }).join('');
}

function polygonPoints(cx, cy, r, sides) {
    return Array.from({ length: sides }, (_, i) => {
        const angle = (Math.PI * 2 * i) / sides - Math.PI / 2;
        const x = cx + Math.cos(angle) * r;
        const y = cy + Math.sin(angle) * r;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(' ');
}

/* ---------- 10. 时间线 ---------- */

function renderTimeline(items) {
    const container = document.getElementById('learning-timeline');
    if (!container) return;

    if (!items || !items.length) {
        renderEmpty(container, '暂无学习记录', '开始学习后这里会显示你的近期动态');
        return;
    }

    container.innerHTML = items.map(item => `
        <div class="timeline-item">
            <div class="timeline-dot ${escapeHtml(item.status || 'completed')}"></div>
            <div class="timeline-content">
                <div class="timeline-head">
                    <span class="timeline-title">${escapeHtml(item.title || '学习记录')}</span>
                    <span class="timeline-time">${escapeHtml(item.time || '')}</span>
                </div>
                <p class="timeline-desc">${escapeHtml(item.desc || '')}</p>
            </div>
        </div>
    `).join('');
}

/* ---------- 11. 成就 ---------- */

function renderAchievements(summary) {
    const grid = document.getElementById('achievements-grid');
    const unlockedEl = document.getElementById('unlocked-count');
    const totalEl = document.getElementById('total-count');
    if (!grid) return;

    const list = PROGRESS_CONFIG.achievements;
    if (totalEl) totalEl.textContent = list.length;

    const totalHours = Number(summary.total_hours) || 0;
    const completedCourses = Number(summary.completed_courses) || 0;
    const streak = Number(summary.current_streak) || 0;

    let unlocked = 0;
    grid.innerHTML = list.map(badge => {
        const isUnlocked = checkBadge(badge, { totalHours, completedCourses, streak });
        if (isUnlocked) unlocked++;
        return `
            <div class="badge ${isUnlocked ? 'unlocked' : 'locked'}" title="${escapeHtml(badge.name)} — ${escapeHtml(badge.desc)}">
                <div class="badge-icon">${escapeHtml(badge.icon)}</div>
                <p class="badge-name">${escapeHtml(badge.name)}</p>
                <p class="badge-desc">${escapeHtml(badge.desc)}</p>
            </div>
        `;
    }).join('');

    if (unlockedEl) unlockedEl.textContent = unlocked;
}

function checkBadge(badge, stats) {
    const t = badge.threshold || {};
    if (t.total_hours != null && stats.totalHours < t.total_hours) return false;
    if (t.completed_courses != null && stats.completedCourses < t.completed_courses) return false;
    if (t.current_streak != null && stats.streak < t.current_streak) return false;
    return true;
}
