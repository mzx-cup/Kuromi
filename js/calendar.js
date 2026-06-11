/* ============================================================
   Calendar Page — 学习日历 (v2 重构)
   功能：日程事件、任务计划、学习打卡、每日提醒
   依赖：data-layer.js (可选)
   ============================================================ */

(function () {
    'use strict';

    // ---------- 状态 ----------
    const today = new Date();
    let currentMonth = today.getMonth();
    let currentYear = today.getFullYear();
    let selectedDate = null;
    let calendarData = { days: {}, month_summary: {}, upcoming: [] };
    let eventsData = {};
    let currentFilter = 'all';
    let checkedInToday = false;
    let reminderIndex = 0;
    let isLoading = false;

    // ---------- 工具 ----------
    const WEEKDAY_LABELS = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
    const WEEKDAY_SHORT = ['日', '一', '二', '三', '四', '五', '六'];
    const TIME_SLOT_LABELS = {
        'morning':   '上午',
        'afternoon': '下午',
        'evening':   '晚上',
        'all-day':   '全天'
    };
    const CATEGORY_LABELS = {
        study:  '📘 学习',
        review: '🔁 复习',
        exam:   '📝 考试',
        python: '🐍 Python',
        algorithm: '🧮 算法',
        database:  '🗄️ 数据库',
        web:    '🌐 Web',
        ai:     '🤖 AI'
    };

    const REMINDERS = [
        { quote: '不积跬步，无以至千里；不积小流，无以成江海。', source: '— 荀子《劝学》' },
        { quote: '学而时习之，不亦说乎？', source: '— 孔子《论语》' },
        { quote: '千里之行，始于足下。', source: '— 老子《道德经》' },
        { quote: '天才是 1% 的灵感加上 99% 的汗水。', source: '— 爱迪生' },
        { quote: '保持专注，时间会给你答案。', source: '— 学习寄语' },
        { quote: '今日事，今日毕。', source: '— 朱子家训' },
        { quote: '书山有路勤为径，学海无涯苦作舟。', source: '— 韩愈' },
        { quote: '慢慢来，比较快。', source: '— 学习寄语' }
    ];

    function pad2(n) { return String(n).padStart(2, '0'); }
    function formatDate(year, month, day) {
        return `${year}-${pad2(month + 1)}-${pad2(day)}`;
    }
    function parseDate(value) {
        const [, m = '1', d = '1'] = String(value || '').split('-');
        return { month: Number(m), day: Number(d) };
    }
    function getCurrentUserId() {
        try {
            const user = JSON.parse(localStorage.getItem('starlearn_user') || '{}');
            return user.id || null;
        } catch (e) { return null; }
    }
    function setText(id, value) {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    }
    function escapeHtml(value) {
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
    function minutesToLevel(minutes) {
        const thresholds = [0, 5, 15, 45, 90];
        let level = 0;
        for (let i = thresholds.length - 1; i >= 0; i--) {
            if (minutes >= thresholds[i]) { level = i; break; }
        }
        return level;
    }

    // ---------- Toast ----------
    function showToast(message, type = 'success') {
        const container = document.getElementById('toast-container');
        if (!container) return;
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        const icon = type === 'success'
            ? '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/></svg>'
            : '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>';
        toast.innerHTML = `<span class="toast-icon">${icon}</span><span>${escapeHtml(message)}</span>`;
        container.appendChild(toast);
        setTimeout(() => {
            toast.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(20px)';
            setTimeout(() => toast.remove(), 300);
        }, 2400);
    }

    // ---------- 数据加载 ----------
    async function loadCalendarData() {
        if (isLoading) return;
        isLoading = true;
        const userId = getCurrentUserId();
        if (!userId) {
            isLoading = false;
            renderLoginRequired();
            return;
        }
        try {
            const response = await fetch(`/api/calendar-events/load/${userId}`);
            const data = await response.json();
            if (!response.ok || !data.success) throw new Error(data.detail || 'load failed');
            eventsData = data.eventsData || {};
            calendarData = data.calendarData || { days: {}, month_summary: {}, upcoming: [] };
        } catch (err) {
            console.warn('[calendar] 加载后端数据失败，使用空数据:', err.message);
            eventsData = {};
            calendarData = { days: {}, month_summary: {}, upcoming: [] };
        } finally {
            isLoading = false;
        }
        // 兜底：把 eventsData 扁平化为 days 数据，便于 heatmap
        enrichCalendarFromEvents();
        refreshAll();
    }

    function renderLoginRequired() {
        const root = document.querySelector('.calendar-root') || document.body;
        root.innerHTML = '' +
            '<div class="calendar-empty">' +
                '<div class="calendar-empty-icon">✦</div>' +
                '<h3 class="calendar-empty-title">请先登录</h3>' +
                '<p class="calendar-empty-desc">登录后即可查看你的学习日历</p>' +
                '<a href="/login.html" class="calendar-empty-btn">前往登录</a>' +
            '</div>';
    }

    function enrichCalendarFromEvents() {
        // 1) 为空：直接从 eventsData 推断 upcoming
        if (!Array.isArray(calendarData.upcoming) || calendarData.upcoming.length === 0) {
            const todayStr = formatDate(today.getFullYear(), today.getMonth(), today.getDate());
            const list = [];
            Object.entries(eventsData || {}).forEach(([date, items]) => {
                if (date < todayStr) return;
                (items || []).forEach(it => {
                    list.push({
                        date, name: it.name || '学习计划',
                        duration: it.duration || '1h',
                        category: it.category || 'study',
                        desc: it.desc || '',
                        timeSlot: it.timeSlot || 'afternoon',
                        priority: it.priority || 'medium',
                        done: !!it.done
                    });
                });
            });
            list.sort((a, b) => a.date.localeCompare(b.date));
            calendarData.upcoming = list.slice(0, 20);
        }
        // 2) 计算每日 tasks
        Object.entries(eventsData || {}).forEach(([date, items]) => {
            if (!calendarData.days[date]) {
                calendarData.days[date] = { status: 'empty', study_minutes: 0, tasks: [] };
            }
            const day = calendarData.days[date];
            if (!Array.isArray(day.tasks)) day.tasks = [];
            (items || []).forEach(it => {
                day.tasks.push({
                    name: it.name || '学习计划',
                    duration: it.duration || '1h',
                    category: it.category || 'study',
                    done: !!it.done,
                    priority: it.priority || 'medium'
                });
            });
            // 推断 status
            const total = day.tasks.length;
            const done = day.tasks.filter(t => t.done).length;
            const isToday = date === formatDate(today.getFullYear(), today.getMonth(), today.getDate());
            if (isToday) {
                day.status = total > 0 ? (done === total ? 'completed' : done > 0 ? 'partial' : 'today') : 'today';
            } else if (total > 0) {
                day.status = done === total ? 'completed' : done > 0 ? 'partial' : 'scheduled';
            } else if (new Date(date) > today) {
                day.status = 'scheduled';
            } else {
                day.status = 'empty';
            }
        });
    }

    // ---------- 渲染：日历 ----------
    function renderCalendar(month, year) {
        const grid = document.getElementById('calendar-grid');
        if (!grid) return;

        // 保留 weekday header
        const weekdays = Array.from(grid.querySelectorAll('.calendar-weekday'));
        grid.innerHTML = '';
        weekdays.forEach((d, i) => {
            d.textContent = WEEKDAY_SHORT[i];
            d.classList.toggle('weekend', i === 0 || i === 6);
            grid.appendChild(d);
        });

        const firstDay = new Date(year, month, 1).getDay();
        const daysInMonth = new Date(year, month + 1, 0).getDate();
        const todayStr = formatDate(today.getFullYear(), today.getMonth(), today.getDate());
        const isCurrentMonth = (year === today.getFullYear() && month === today.getMonth());

        for (let i = 0; i < firstDay; i++) {
            const empty = document.createElement('div');
            empty.className = 'calendar-day empty';
            grid.appendChild(empty);
        }

        for (let day = 1; day <= daysInMonth; day++) {
            const dateStr = formatDate(year, month, day);
            const weekday = (firstDay + day - 1) % 7;
            const isWeekend = weekday === 0 || weekday === 6;
            const dayData = calendarData.days?.[dateStr] || {};
            const minutes = Number(dayData.study_minutes) || 0;
            const level = minutesToLevel(minutes);
            const dayEvents = (eventsData && eventsData[dateStr]) || [];
            const tasks = dayData.tasks || [];

            const dayEl = document.createElement('div');
            dayEl.className = 'calendar-day';
            if (isWeekend) dayEl.classList.add('weekend');
            dayEl.dataset.day = day;
            dayEl.dataset.date = dateStr;
            dayEl.dataset.level = String(level);

            // 状态样式
            const isToday = isCurrentMonth && day === today.getDate();
            if (isToday) dayEl.classList.add('today');
            if (dayData.status && dayData.status !== 'empty') {
                dayEl.classList.add(dayData.status);
            }
            if (selectedDate && selectedDate.dateStr === dateStr) {
                dayEl.classList.add('selected');
            }

            // 找出最高优先级事件
            const topPriority = dayEvents.reduce((acc, e) => {
                const order = { high: 3, medium: 2, low: 1 };
                return (order[e.priority] || 0) > (order[acc] || 0) ? (e.priority || acc) : acc;
            }, '');

            // 渲染事件小点（最多 3 个）
            const maxDots = 3;
            const dotsHtml = dayEvents.slice(0, maxDots).map(e =>
                `<span class="day-event-dot ${escapeHtml(e.category || 'study')}"></span>`
            ).join('');
            const moreHtml = dayEvents.length > maxDots
                ? `<span class="day-event-more">+${dayEvents.length - maxDots}</span>` : '';

            // 进度条：任务完成比例
            const totalTasks = tasks.length;
            const doneTasks = tasks.filter(t => t.done).length;
            const progressPct = totalTasks > 0 ? Math.round(doneTasks / totalTasks * 100) : 0;
            const showProgress = totalTasks > 0;

            dayEl.innerHTML = `
                <div class="day-number">${day}</div>
                ${topPriority && topPriority !== 'low' ? `<span class="day-priority ${topPriority}" title="优先级: ${topPriority}"></span>` : ''}
                <div class="day-events">${dotsHtml}${moreHtml}</div>
                ${showProgress ? `<div class="day-progress"><div class="day-progress-bar" style="width:${progressPct}%"></div></div>` : ''}
            `;

            dayEl.addEventListener('click', () => selectDay(dateStr, day, month, year));
            grid.appendChild(dayEl);
        }
    }

    // ---------- 渲染：KPI 与打卡环 ----------
    function updateKPIs() {
        const prefix = `${currentYear}-${pad2(currentMonth + 1)}`;
        const monthDays = Object.entries(calendarData.days || {})
            .filter(([d]) => d.startsWith(prefix))
            .map(([, day]) => day);

        const studyDays = monthDays.filter(d => (Number(d.study_minutes) || 0) > 0).length;
        const totalMinutes = monthDays.reduce((s, d) => s + (Number(d.study_minutes) || 0), 0);

        const todayStr = formatDate(today.getFullYear(), today.getMonth(), today.getDate());
        const todayEvents = (eventsData[todayStr]) || [];
        const todoToday = todayEvents.length;

        // 本周完成率：周一至周日
        const weekly = computeWeekStats();
        const weekRate = weekly.total > 0 ? Math.round(weekly.done / weekly.total * 100) : 0;

        // 连续打卡：基于 eventsData 中 done=true 的最近连续天数
        const streak = computeStreak();

        setText('kpi-streak', streak);
        setText('kpi-todo-today', todoToday);
        setText('kpi-month-hours', (totalMinutes / 60).toFixed(1));
        setText('kpi-week-rate', weekRate);
        const rateBar = document.getElementById('kpi-week-rate-bar');
        if (rateBar) rateBar.style.width = `${weekRate}%`;

        // 打卡环
        const done = todayEvents.filter(e => e.done).length;
        const percent = todoToday > 0 ? Math.round(done / todoToday * 100) : 0;
        updateCheckinRing(percent, done, todoToday);
    }

    function updateCheckinRing(percent, done, total) {
        const fg = document.getElementById('checkin-ring-fg');
        if (fg) {
            const C = 2 * Math.PI * 52;
            const offset = C * (1 - percent / 100);
            fg.setAttribute('stroke-dasharray', String(C.toFixed(2)));
            fg.setAttribute('stroke-dashoffset', String(offset.toFixed(2)));
        }
        setText('checkin-percent', `${percent}%`);

        const status = document.getElementById('checkin-status');
        const desc = document.getElementById('checkin-desc');
        const btn = document.getElementById('checkin-btn');
        const btnText = document.getElementById('checkin-btn-text');

        if (total === 0) {
            if (status) { status.textContent = '待规划'; status.style.background = 'var(--cal-surface)'; status.style.color = 'var(--cal-text-muted)'; }
            if (desc) desc.textContent = '今日还没有计划，添加一个吧';
            if (btn) { btn.disabled = true; btn.style.opacity = '0.5'; }
            if (btnText) btnText.textContent = '暂无任务';
        } else if (percent === 100) {
            if (status) { status.textContent = '已完成'; status.style.background = 'var(--cal-success-soft)'; status.style.color = 'var(--cal-success)'; }
            if (desc) desc.textContent = '🎉 今日任务全部完成，太棒了！';
            if (btn) { btn.classList.add('done'); btn.disabled = true; }
            if (btnText) btnText.textContent = '已完成打卡';
        } else if (percent > 0) {
            if (status) { status.textContent = '进行中'; status.style.background = 'var(--cal-info-soft)'; status.style.color = 'var(--cal-info)'; }
            if (desc) desc.textContent = `已完成 ${done}/${total}，继续加油`;
            if (btn) { btn.classList.remove('done'); btn.disabled = false; }
            if (btnText) btnText.textContent = '继续打卡';
        } else {
            if (status) { status.textContent = '未开始'; status.style.background = 'var(--cal-warning-soft)'; status.style.color = 'var(--cal-warning)'; }
            if (desc) desc.textContent = '完成今日计划，开启高效一天';
            if (btn) { btn.classList.remove('done'); btn.disabled = false; }
            if (btnText) btnText.textContent = '立即打卡';
        }
    }

    function computeStreak() {
        const dates = Object.keys(eventsData || {}).sort().reverse();
        let streak = 0;
        const cursor = new Date(today);
        // 如果今天没完成，从昨天开始
        const todayStr = formatDate(cursor.getFullYear(), cursor.getMonth(), cursor.getDate());
        const todayDone = (eventsData[todayStr] || []).some(e => e.done);
        if (!todayDone) cursor.setDate(cursor.getDate() - 1);
        while (true) {
            const s = formatDate(cursor.getFullYear(), cursor.getMonth(), cursor.getDate());
            const items = eventsData[s] || [];
            if (items.length > 0 && items.some(e => e.done)) {
                streak++;
                cursor.setDate(cursor.getDate() - 1);
            } else {
                break;
            }
            if (streak > 365) break;
        }
        return streak;
    }

    function computeWeekStats() {
        // 找出本周一
        const d = new Date(today);
        const wd = d.getDay() || 7; // 周一为 1
        const monday = new Date(d);
        monday.setDate(d.getDate() - (wd - 1));
        let total = 0, done = 0;
        for (let i = 0; i < 7; i++) {
            const day = new Date(monday);
            day.setDate(monday.getDate() + i);
            const s = formatDate(day.getFullYear(), day.getMonth(), day.getDate());
            const items = eventsData[s] || [];
            total += items.length;
            done += items.filter(e => e.done).length;
        }
        return { total, done };
    }

    // ---------- 渲染：标题 / 提醒 ----------
    function updateHeader() {
        setText('month-title', `${currentYear}年${currentMonth + 1}月`);
        // 本周范围
        const d = new Date(currentYear, currentMonth, 1);
        const wd = d.getDay() || 7;
        const monday = new Date(d);
        monday.setDate(d.getDate() - (wd - 1));
        const sunday = new Date(monday);
        sunday.setDate(monday.getDate() + 6);
        setText('month-subtitle',
            `本周 · ${monday.getMonth() + 1}月${monday.getDate()}日 - ${sunday.getMonth() + 1}月${sunday.getDate()}日`);

        // 今日日期
        const weekday = WEEKDAY_LABELS[today.getDay()];
        setText('checkin-date', `${today.getMonth() + 1}月${today.getDate()}日 ${weekday}`);
    }

    function updateReminder() {
        const r = REMINDERS[reminderIndex % REMINDERS.length];
        setText('reminder-quote', r.quote);
        setText('reminder-source', r.source);
    }

    // ---------- 渲染：今日任务 ----------
    function renderTodayTasks() {
        const list = document.getElementById('today-tasks-list');
        if (!list) return;
        const todayStr = formatDate(today.getFullYear(), today.getMonth(), today.getDate());
        const items = eventsData[todayStr] || [];
        const total = items.length;
        const done = items.filter(e => e.done).length;
        setText('today-tasks-count', `${done}/${total}`);

        if (total === 0) {
            list.innerHTML = `<div class="empty-state small"><p>暂无任务，点击右上角 + 添加</p></div>`;
            return;
        }
        // 按优先级排序
        const order = { high: 0, medium: 1, low: 2 };
        const sorted = [...items].sort((a, b) => (order[a.priority] ?? 1) - (order[b.priority] ?? 1));
        list.innerHTML = sorted.map((t, i) => `
            <div class="task-item ${t.done ? 'completed' : ''}" data-idx="${i}">
                <div class="task-checkbox ${t.done ? 'checked' : ''}" data-action="toggle"></div>
                <div class="task-info">
                    <div class="task-name">${escapeHtml(t.name || '学习计划')}</div>
                    <div class="task-meta">
                        <span class="task-meta-dot" style="background: var(--cal-${t.priority === 'high' ? 'danger' : t.priority === 'medium' ? 'warning' : 'text-faint'})"></span>
                        <span>${escapeHtml(TIME_SLOT_LABELS[t.timeSlot] || '')}</span>
                        <span>·</span>
                        <span>${escapeHtml(t.duration || '1h')}</span>
                    </div>
                </div>
            </div>
        `).join('');
    }

    // ---------- 渲染：7 日热力图 ----------
    function renderHeatmap() {
        const grid = document.getElementById('heatmap-grid');
        if (!grid) return;
        const cells = [];
        let totalMinutes = 0;
        for (let i = 6; i >= 0; i--) {
            const d = new Date(today);
            d.setDate(today.getDate() - i);
            const s = formatDate(d.getFullYear(), d.getMonth(), d.getDate());
            const dayData = calendarData.days?.[s] || {};
            const minutes = Number(dayData.study_minutes) || 0;
            totalMinutes += minutes;
            const level = minutesToLevel(minutes);
            cells.push(`
                <div class="heatmap-cell" data-level="${level}">
                    <span class="hm-day">${WEEKDAY_SHORT[d.getDay()]}</span>
                    <span class="hm-value">${(minutes / 60).toFixed(1)}h</span>
                </div>
            `);
        }
        grid.innerHTML = cells.join('');
        setText('heatmap-total', `${(totalMinutes / 60).toFixed(1)} h`);
    }

    // ---------- 渲染：近期计划 ----------
    function renderUpcoming() {
        const list = document.getElementById('events-list');
        if (!list) return;
        const todayStr = formatDate(today.getFullYear(), today.getMonth(), today.getDate());
        const all = (calendarData.upcoming || []).filter(e => e.date >= todayStr);
        const items = currentFilter === 'all'
            ? all
            : all.filter(e => e.category === currentFilter);

        if (items.length === 0) {
            list.innerHTML = `<div class="empty-state">暂无近期${currentFilter === 'all' ? '' : '（' + (CATEGORY_LABELS[currentFilter] || '') + '）'}学习计划<br>点击右上角 + 添加</div>`;
            return;
        }
        list.innerHTML = items.map(e => {
            const pd = parseDate(e.date);
            const cat = e.category || 'study';
            const catLabel = CATEGORY_LABELS[cat] || cat;
            const time = TIME_SLOT_LABELS[e.timeSlot] || '';
            return `
                <div class="event-item">
                    <div class="event-date">
                        <span class="event-day">${pd.day}</span>
                        <span class="event-month">${pd.month}月</span>
                    </div>
                    <div class="event-content">
                        <h4 class="event-title">${escapeHtml(e.name || '学习计划')}</h4>
                        ${e.desc ? `<p class="event-desc">${escapeHtml(e.desc)}</p>` : ''}
                        <div class="event-meta">
                            <span class="event-tag ${escapeHtml(cat)}">${escapeHtml(catLabel)}</span>
                            ${e.duration ? `<span class="event-duration">${escapeHtml(e.duration)}</span>` : ''}
                        </div>
                    </div>
                    <span class="event-time-slot">${time}</span>
                </div>
            `;
        }).join('');
    }

    // ---------- 选中日期 ----------
    function selectDay(dateStr, day, month, year) {
        selectedDate = { dateStr, day, month, year };
        // 重新渲染以显示 selected 样式
        renderCalendar(month, year);
        // 弹窗提示选中信息
        const items = eventsData[dateStr] || [];
        const weekday = WEEKDAY_LABELS[new Date(year, month, day).getDay()];
        if (items.length === 0) {
            showToast(`已选中 ${month + 1}月${day}日 ${weekday}（无计划）`, 'success');
        } else {
            showToast(`已选中 ${month + 1}月${day}日 · ${items.length} 项任务`, 'success');
        }
    }

    // ---------- 模态框 ----------
    function initModal() {
        const modal = document.getElementById('event-modal');
        const addBtn = document.getElementById('add-event-btn');
        const closeBtn = document.getElementById('close-modal');
        const cancelBtn = document.getElementById('cancel-btn');
        const form = document.getElementById('event-form');

        function openModal() {
            modal?.classList.remove('hidden');
            const date = selectedDate
                ? formatDate(selectedDate.year, selectedDate.month, selectedDate.day)
                : formatDate(today.getFullYear(), today.getMonth(), today.getDate());
            const dateInput = document.getElementById('event-date');
            if (dateInput) dateInput.value = date;
            setTimeout(() => document.getElementById('event-title')?.focus(), 50);
        }
        function closeModal() {
            modal?.classList.add('hidden');
            form?.reset();
        }

        addBtn?.addEventListener('click', openModal);
        closeBtn?.addEventListener('click', closeModal);
        cancelBtn?.addEventListener('click', closeModal);
        modal?.addEventListener('click', (e) => { if (e.target === modal) closeModal(); });
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && !modal?.classList.contains('hidden')) closeModal();
        });

        form?.addEventListener('submit', async (e) => {
            e.preventDefault();
            await saveEvent(form, closeModal);
        });
    }

    async function saveEvent(form, closeFn) {
        const title = document.getElementById('event-title').value.trim();
        const date = document.getElementById('event-date').value;
        const timeSlot = document.getElementById('event-time').value;
        const duration = document.getElementById('event-duration').value;
        const priority = document.getElementById('event-priority').value;
        const category = document.querySelector('input[name="event-category"]:checked')?.value || 'study';
        const remind = document.getElementById('event-remind')?.checked ?? true;
        const desc = document.getElementById('event-desc')?.value.trim() || '';

        if (!title || !date) {
            showToast('请填写学习内容和日期', 'error');
            return;
        }

        if (!Array.isArray(eventsData[date])) eventsData[date] = [];
        const event = {
            name: title,
            duration: `${duration}h`,
            category,
            desc,
            timeSlot,
            priority,
            remind,
            done: false,
            createdAt: new Date().toISOString()
        };
        eventsData[date].push(event);

        try {
            const response = await fetch('/api/calendar-events/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ userId: getCurrentUserId(), eventsData })
            });
            const data = await response.json();
            if (!response.ok || !data.success) throw new Error(data.detail || 'save failed');
            showToast('计划已添加 ✨', 'success');
            enrichCalendarFromEvents();
            refreshAll();
            form.reset();
            closeFn();
        } catch (err) {
            console.error('保存失败:', err);
            showToast('保存失败，请重试', 'error');
        }
    }

    // ---------- 任务勾选 ----------
    async function toggleTask(dateStr, idx) {
        const arr = eventsData[dateStr];
        if (!arr || !arr[idx]) return;
        arr[idx].done = !arr[idx].done;
        try {
            await fetch('/api/calendar-events/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ userId: getCurrentUserId(), eventsData })
            });
        } catch (e) { console.warn('同步失败:', e); }
        enrichCalendarFromEvents();
        refreshAll();
        const wasDone = arr[idx].done;
        showToast(wasDone ? '已完成 ✓' : '已取消勾选', 'success');
    }

    // ---------- 打卡 ----------
    async function checkinToday() {
        const todayStr = formatDate(today.getFullYear(), today.getMonth(), today.getDate());
        const items = eventsData[todayStr] || [];
        if (items.length === 0) {
            showToast('请先添加今日计划', 'error');
            return;
        }
        // 全部标记为 done
        items.forEach(it => { it.done = true; });
        try {
            await fetch('/api/calendar-events/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ userId: getCurrentUserId(), eventsData })
            });
        } catch (e) { console.warn('打卡同步失败:', e); }
        checkedInToday = true;
        enrichCalendarFromEvents();
        refreshAll();
        showToast('今日打卡成功 🎉', 'success');
    }

    // ---------- 月份导航 ----------
    function initNav() {
        document.getElementById('prev-month')?.addEventListener('click', () => {
            currentMonth--;
            if (currentMonth < 0) { currentMonth = 11; currentYear--; }
            updateHeader();
            renderCalendar(currentMonth, currentYear);
            updateKPIs();
        });
        document.getElementById('next-month')?.addEventListener('click', () => {
            currentMonth++;
            if (currentMonth > 11) { currentMonth = 0; currentYear++; }
            updateHeader();
            renderCalendar(currentMonth, currentYear);
            updateKPIs();
        });
        document.getElementById('today-btn')?.addEventListener('click', () => {
            currentMonth = today.getMonth();
            currentYear = today.getFullYear();
            updateHeader();
            renderCalendar(currentMonth, currentYear);
            updateKPIs();
            showToast(`已回到 ${currentMonth + 1}月${today.getDate()}日`, 'success');
        });

        // 视图切换（仅月视图有效）
        document.querySelectorAll('.view-toggle-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.view-toggle-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                if (btn.dataset.view === 'list') {
                    showToast('列表视图敬请期待', 'success');
                } else if (btn.dataset.view === 'week') {
                    showToast('周视图开发中', 'success');
                }
            });
        });

        // 筛选
        document.querySelectorAll('.filter-chip').forEach(chip => {
            chip.addEventListener('click', () => {
                document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
                chip.classList.add('active');
                currentFilter = chip.dataset.filter;
                renderUpcoming();
            });
        });

        // 提醒换一句
        document.getElementById('reminder-refresh')?.addEventListener('click', () => {
            reminderIndex++;
            updateReminder();
        });

        // 打卡按钮
        document.getElementById('checkin-btn')?.addEventListener('click', checkinToday);

        // 任务勾选（事件委托）
        document.getElementById('today-tasks-list')?.addEventListener('click', (e) => {
            const cb = e.target.closest('.task-checkbox');
            if (!cb) return;
            const item = cb.closest('.task-item');
            if (!item) return;
            const todayStr = formatDate(today.getFullYear(), today.getMonth(), today.getDate());
            const items = eventsData[todayStr] || [];
            // 找到对应 idx
            const name = item.querySelector('.task-name')?.textContent || '';
            const idx = items.findIndex(it => (it.name || '') === name);
            if (idx >= 0) toggleTask(todayStr, idx);
        });
    }

    // ---------- 刷新全部 ----------
    function refreshAll() {
        updateHeader();
        renderCalendar(currentMonth, currentYear);
        updateKPIs();
        renderTodayTasks();
        renderHeatmap();
        renderUpcoming();
    }

    // ---------- 启动 ----------
    document.addEventListener('DOMContentLoaded', () => {
        initNav();
        initModal();
        updateHeader();
        updateReminder();
        // 默认选中今天
        selectedDate = {
            dateStr: formatDate(today.getFullYear(), today.getMonth(), today.getDate()),
            day: today.getDate(),
            month: today.getMonth(),
            year: today.getFullYear()
        };
        loadCalendarData();
    });
})();
