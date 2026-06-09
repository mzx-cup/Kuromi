document.addEventListener('DOMContentLoaded', function() {
    initCalendar();
    initModal();
    initDaySelection();
});

let currentDate = new Date();
let currentMonth = currentDate.getMonth();
let currentYear = currentDate.getFullYear();
let selectedDate = null;
let calendarData = { days: {}, month_summary: {}, upcoming: [] };
let eventsData = {};

function getCurrentUserId() {
    try {
        const user = JSON.parse(localStorage.getItem('starlearn_user') || '{}');
        return user.id || 1;
    } catch (error) {
        return 1;
    }
}

async function initCalendar() {
    setupMonthNavigation();
    updateMonthTitle();
    await loadCalendarData();
    renderCalendar(currentMonth, currentYear);
}

async function loadCalendarData() {
    try {
        const response = await fetch(`/api/calendar-events/load/${getCurrentUserId()}`);
        const data = await response.json();
        if (!response.ok || !data.success) throw new Error(data.detail || 'load calendar failed');
        eventsData = data.eventsData || {};
        calendarData = data.calendarData || { days: {}, month_summary: {}, upcoming: [] };
    } catch (error) {
        console.error('加载学习日历失败:', error);
        eventsData = {};
        calendarData = { days: {}, month_summary: {}, upcoming: [] };
    }
    updateSummary();
    renderUpcomingEvents();
}

function renderCalendar(month, year) {
    const grid = document.getElementById('calendar-grid');
    if (!grid) return;
    const weekdays = Array.from(grid.querySelectorAll('.calendar-weekday'));
    grid.innerHTML = '';
    weekdays.forEach(day => grid.appendChild(day));

    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const today = new Date();

    for (let i = 0; i < firstDay; i++) {
        const empty = document.createElement('div');
        empty.className = 'calendar-day empty';
        grid.appendChild(empty);
    }

    for (let day = 1; day <= daysInMonth; day++) {
        const dayEl = document.createElement('div');
        dayEl.className = 'calendar-day';
        dayEl.textContent = day;
        dayEl.dataset.day = day;

        const dateStr = formatDate(year, month, day);
        dayEl.dataset.date = dateStr;

        if (year === today.getFullYear() && month === today.getMonth() && day === today.getDate()) {
            dayEl.classList.add('today');
        }

        const dayData = calendarData.days?.[dateStr];
        if (dayData && dayData.status && dayData.status !== 'empty') {
            dayEl.classList.add(dayData.status);
        }

        dayEl.addEventListener('click', () => selectDay(dayEl, day, month, year));
        grid.appendChild(dayEl);
    }
}

function setupMonthNavigation() {
    document.getElementById('prev-month')?.addEventListener('click', () => {
        currentMonth--;
        if (currentMonth < 0) {
            currentMonth = 11;
            currentYear--;
        }
        updateMonthTitle();
        updateSummary();
        renderCalendar(currentMonth, currentYear);
    });

    document.getElementById('next-month')?.addEventListener('click', () => {
        currentMonth++;
        if (currentMonth > 11) {
            currentMonth = 0;
            currentYear++;
        }
        updateMonthTitle();
        updateSummary();
        renderCalendar(currentMonth, currentYear);
    });
}

function updateMonthTitle() {
    const title = document.getElementById('month-title');
    if (title) title.textContent = `${currentYear}年${currentMonth + 1}月`;
}

function initDaySelection() {
    const dayDetail = document.getElementById('day-detail');
    dayDetail?.addEventListener('click', (e) => {
        const checkbox = e.target.closest('.task-checkbox');
        if (checkbox) {
            checkbox.classList.toggle('checked');
            checkbox.closest('.task-item')?.classList.toggle('completed');
        }
    });
}

function selectDay(dayEl, day, month, year) {
    document.querySelectorAll('.calendar-day.selected').forEach(el => el.classList.remove('selected'));
    dayEl.classList.add('selected');

    selectedDate = { day, month, year };
    const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
    const dateObj = new Date(year, month, day);
    const dateStr = formatDate(year, month, day);
    const dayData = calendarData.days?.[dateStr];

    setText('detail-date', `${month + 1}月${day}日`);
    setText('detail-day', weekdays[dateObj.getDay()]);
    renderDayTasks(dayData);
}

function renderDayTasks(dayData) {
    const content = document.getElementById('detail-content');
    if (!content) return;

    const tasks = dayData?.tasks || [];
    if (!tasks.length) {
        content.innerHTML = `
            <div class="empty-state">
                <p>暂无学习记录或计划<br>点击右上角添加学习计划</p>
            </div>
        `;
        return;
    }

    content.innerHTML = `
        <div class="task-list">
            ${tasks.map(task => `
                <div class="task-item ${task.done ? 'completed' : ''}">
                    <div class="task-checkbox ${task.done ? 'checked' : ''}"></div>
                    <div class="task-info">
                        <div class="task-name">${escapeHtml(task.name || '学习计划')}</div>
                        <div class="task-meta">${escapeHtml(task.duration || '')}</div>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}

function initModal() {
    const modal = document.getElementById('event-modal');
    const addBtn = document.getElementById('add-event-btn');
    const closeBtn = document.getElementById('close-modal');
    const cancelBtn = document.getElementById('cancel-btn');
    const form = document.getElementById('event-form');

    addBtn?.addEventListener('click', () => {
        modal?.classList.remove('hidden');
        const date = selectedDate ? formatDate(selectedDate.year, selectedDate.month, selectedDate.day) : new Date().toISOString().split('T')[0];
        document.getElementById('event-date').value = date;
    });

    closeBtn?.addEventListener('click', () => modal?.classList.add('hidden'));
    cancelBtn?.addEventListener('click', () => modal?.classList.add('hidden'));

    modal?.addEventListener('click', (e) => {
        if (e.target === modal) modal.classList.add('hidden');
    });

    form?.addEventListener('submit', async (e) => {
        e.preventDefault();
        await saveEvent(form, modal);
    });
}

async function saveEvent(form, modal) {
    const title = document.getElementById('event-title').value.trim();
    const date = document.getElementById('event-date').value;
    const duration = document.getElementById('event-duration').value;
    const category = document.querySelector('input[name="event-category"]:checked')?.value || 'study';
    const desc = document.getElementById('event-desc')?.value.trim() || '';

    if (!title || !date) return;

    if (!Array.isArray(eventsData[date])) eventsData[date] = [];
    eventsData[date].push({
        name: title,
        duration: `${duration}h`,
        category,
        desc,
        done: false
    });

    try {
        const response = await fetch('/api/calendar-events/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ userId: getCurrentUserId(), eventsData })
        });
        const data = await response.json();
        if (!response.ok || !data.success) throw new Error(data.detail || 'save calendar failed');
        await loadCalendarData();
        renderCalendar(currentMonth, currentYear);
        form.reset();
        modal?.classList.add('hidden');
    } catch (error) {
        console.error('保存学习计划失败:', error);
    }
}

function updateSummary() {
    const prefix = `${currentYear}-${String(currentMonth + 1).padStart(2, '0')}`;
    const days = Object.entries(calendarData.days || {})
        .filter(([date]) => date.startsWith(prefix))
        .map(([, day]) => day);
    const studyDays = days.filter(day => (Number(day.study_minutes) || 0) > 0).length;
    const totalMinutes = days.reduce((sum, day) => sum + (Number(day.study_minutes) || 0), 0);
    const completedTasks = days.reduce((sum, day) => {
        return sum + (day.tasks || []).filter(task => task.done).length;
    }, 0);
    setText('study-days', studyDays);
    setText('total-hours-month', (totalMinutes / 60).toFixed(1));
    setText('completed-tasks', completedTasks);
}

const CATEGORY_LABELS = {
    python: '🐍 Python',
    algorithm: '🧮 算法',
    database: '🗄️ 数据库',
    web: '🌐 Web',
    ai: '🤖 AI',
    study: '📘 学习'
};

function renderUpcomingEvents() {
    const list = document.getElementById('events-list');
    if (!list) return;

    const upcoming = calendarData.upcoming || [];
    if (!upcoming.length) {
        list.innerHTML = `<div class="empty-state">暂无近期学习计划<br>点击右上角 + 添加</div>`;
        return;
    }

    list.innerHTML = upcoming.map(event => {
        const date = parseDate(event.date);
        const category = event.category || 'study';
        const categoryLabel = CATEGORY_LABELS[category] || category;
        return `
            <div class="event-item">
                <div class="event-date">
                    <span class="event-day">${date.day}</span>
                    <span class="event-month">${date.month}月</span>
                </div>
                <div class="event-content">
                    <h4 class="event-title">${escapeHtml(event.name || '学习计划')}</h4>
                    ${event.desc ? `<p class="event-desc">${escapeHtml(event.desc)}</p>` : ''}
                    <div class="event-meta">
                        <span class="event-tag ${escapeHtml(category)}">${escapeHtml(categoryLabel)}</span>
                        ${event.duration ? `<span class="event-duration">${escapeHtml(event.duration)}</span>` : ''}
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function formatDate(year, month, day) {
    return `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
}

function parseDate(value) {
    const [, month = '1', day = '1'] = String(value || '').split('-');
    return { month: Number(month), day: Number(day) };
}

function setText(elementId, value) {
    const element = document.getElementById(elementId);
    if (element) element.textContent = value;
}

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}
