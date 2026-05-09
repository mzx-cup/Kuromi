document.addEventListener('DOMContentLoaded', function() {
    initTimeRangeSelect();
    loadProgressSummary();
});

function getCurrentUserId() {
    try {
        const user = JSON.parse(localStorage.getItem('starlearn_user') || '{}');
        return user.id || 1;
    } catch (error) {
        return 1;
    }
}

function initTimeRangeSelect() {
    const select = document.getElementById('time-range');
    if (select) {
        select.addEventListener('change', function() {
            loadProgressSummary(this.value);
        });
    }
}

async function loadProgressSummary(range) {
    const select = document.getElementById('time-range');
    const rangeKey = range || select?.value || 'month';
    renderLoadingState();

    try {
        const response = await fetch(`/api/progress/summary/${getCurrentUserId()}?range=${encodeURIComponent(rangeKey)}`);
        const data = await response.json();
        if (!response.ok || !data.success) throw new Error(data.detail || 'load progress failed');
        renderProgressSummary(data.summary || {});
    } catch (error) {
        console.error('加载学习进度失败:', error);
        renderProgressSummary({
            total_hours: 0,
            completed_courses: 0,
            current_streak: 0,
            avg_daily_hours: 0,
            weekly_activity: [],
            course_progress: [],
            timeline: []
        });
    }
}

function renderLoadingState() {
    setText('total-hours', '0');
    setText('completed-courses', '0');
    setText('current-streak', '0');
    setText('avg-daily', '0.0');
    renderEmpty(document.getElementById('weekly-chart'), '正在加载学习活动...');
    renderEmpty(document.getElementById('course-progress-list'), '正在加载课程进度...');
    renderEmpty(document.getElementById('learning-timeline'), '正在加载学习记录...');
}

function renderProgressSummary(summary) {
    animateNumber('total-hours', Number(summary.total_hours) || 0, true);
    animateNumber('completed-courses', Number(summary.completed_courses) || 0);
    animateNumber('current-streak', Number(summary.current_streak) || 0);
    animateNumber('avg-daily', Number(summary.avg_daily_hours) || 0, true);
    renderWeeklyChart(summary.weekly_activity || []);
    renderCourseProgress(summary.course_progress || []);
    renderTimeline(summary.timeline || []);
}

function setText(elementId, value) {
    const element = document.getElementById(elementId);
    if (element) element.textContent = value;
}

function renderEmpty(container, message) {
    if (!container) return;
    container.innerHTML = `<div class="empty-state">${escapeHtml(message)}</div>`;
}

function animateNumber(elementId, targetValue, isDecimal = false) {
    const element = document.getElementById(elementId);
    if (!element) return;

    const duration = 500;
    const startValue = Number(element.textContent) || 0;
    const startTime = performance.now();

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const currentValue = startValue + (targetValue - startValue) * (1 - Math.pow(1 - progress, 3));
        element.textContent = isDecimal ? currentValue.toFixed(1) : String(Math.round(currentValue));
        if (progress < 1) requestAnimationFrame(update);
    }

    requestAnimationFrame(update);
}

function renderWeeklyChart(activity) {
    const container = document.getElementById('weekly-chart');
    if (!container) return;

    if (!activity.length || activity.every(day => (Number(day.minutes) || 0) === 0)) {
        renderEmpty(container, '暂无学习记录');
        return;
    }

    const maxHours = Math.max(1, ...activity.map(day => Number(day.hours) || 0));
    container.innerHTML = `
        <div class="bar-chart">
            ${activity.map((day, index) => {
                const hours = Number(day.hours) || 0;
                const height = Math.max(4, Math.round(hours / maxHours * 100));
                return `
                    <div class="chart-bar" data-day="${escapeHtml(day.day || '')}" data-hours="${hours}">
                        <div class="bar-fill" style="height: 0%"></div>
                        <span class="bar-value">${hours.toFixed(1)}h</span>
                    </div>
                `;
            }).join('')}
        </div>
    `;

    container.querySelectorAll('.bar-fill').forEach((fill, index) => {
        const hours = Number(activity[index]?.hours) || 0;
        const height = Math.max(4, Math.round(hours / maxHours * 100));
        setTimeout(() => {
            fill.style.height = `${height}%`;
        }, index * 80);
    });
}

function renderCourseProgress(items) {
    const container = document.getElementById('course-progress-list');
    if (!container) return;

    if (!items.length) {
        renderEmpty(container, '暂无课程或知识点进度');
        return;
    }

    container.innerHTML = items.map((item, index) => {
        const progress = Math.max(0, Math.min(100, Number(item.progress) || 0));
        return `
            <div class="progress-item">
                <div class="progress-info">
                    <span class="progress-icon">${escapeHtml(item.icon || '📚')}</span>
                    <span class="progress-name">${escapeHtml(item.name || '未命名')}</span>
                </div>
                <div class="progress-bar-container">
                    <div class="progress-bar-track">
                        <div class="progress-bar-fill ${progressClass(index)}" style="width: 0%"></div>
                    </div>
                    <span class="progress-percent">${progress}%</span>
                </div>
            </div>
        `;
    }).join('');

    container.querySelectorAll('.progress-bar-fill').forEach((bar, index) => {
        const progress = Math.max(0, Math.min(100, Number(items[index]?.progress) || 0));
        setTimeout(() => {
            bar.style.width = `${progress}%`;
        }, index * 100);
    });
}

function renderTimeline(items) {
    const container = document.getElementById('learning-timeline');
    if (!container) return;

    if (!items.length) {
        renderEmpty(container, '暂无学习记录');
        return;
    }

    container.innerHTML = items.map(item => `
        <div class="timeline-item">
            <div class="timeline-dot ${escapeHtml(item.status || 'completed')}"></div>
            <div class="timeline-content">
                <div class="timeline-header">
                    <span class="timeline-title">${escapeHtml(item.title || '学习记录')}</span>
                    <span class="timeline-time">${escapeHtml(item.time || '')}</span>
                </div>
                <p class="timeline-desc">${escapeHtml(item.desc || '')}</p>
            </div>
        </div>
    `).join('');
}

function progressClass(index) {
    return ['python', 'algorithm', 'java', 'database', 'web'][index % 5];
}

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}
