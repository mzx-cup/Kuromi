document.addEventListener('DOMContentLoaded', function() {
    initCalendar();
    initModal();
    initDaySelection();
});

let currentDate = new Date();
let currentMonth = currentDate.getMonth();
let currentYear = currentDate.getFullYear();
let selectedDate = null;

const learningData = {
    2026: {
        4: {
            1: { status: 'completed', tasks: [{ name: 'Python 基础', duration: '2h', done: true }, { name: '算法练习', duration: '1h', done: true }] },
            2: { status: 'completed', tasks: [{ name: '数据结构', duration: '2h', done: true }] },
            3: { status: 'completed', tasks: [{ name: 'MySQL 基础', duration: '1.5h', done: true }, { name: '数据库设计', duration: '1.5h', done: true }] },
            4: { status: 'completed', tasks: [{ name: 'Web 开发', duration: '2h', done: true }] },
            5: { status: 'completed', tasks: [{ name: 'JavaScript', duration: '1.5h', done: true }, { name: 'CSS 布局', duration: '1h', done: true }] },
            6: { status: 'completed', tasks: [{ name: '算法专项', duration: '3h', done: true }] },
            7: { status: 'completed', tasks: [{ name: '机器学习', duration: '2h', done: true }] },
            8: { status: 'completed', tasks: [{ name: '深度学习', duration: '2h', done: true }] },
            9: { status: 'completed', tasks: [{ name: '项目实战', duration: '3h', done: true }] },
            10: { status: 'completed', tasks: [{ name: '代码审查', duration: '1h', done: true }] },
            11: { status: 'completed', tasks: [{ name: '系统设计', duration: '2h', done: true }] },
            12: { status: 'completed', tasks: [{ name: '分布式系统', duration: '2h', done: true }] },
            13: { status: 'completed', tasks: [{ name: '微服务架构', duration: '2h', done: true }] },
            14: { status: 'partial', tasks: [{ name: 'Docker 基础', duration: '1h', done: true }, { name: 'Kubernetes', duration: '1h', done: false }] },
            15: { status: 'partial', tasks: [{ name: '算法练习', duration: '2h', done: false }] },
            16: { status: 'partial', tasks: [] },
            17: { status: 'partial', tasks: [] },
            18: { status: 'partial', tasks: [] }
        }
    }
};

function initCalendar() {
    renderCalendar(currentMonth, currentYear);
    setupMonthNavigation();
    updateMonthTitle();
}

function renderCalendar(month, year) {
    const grid = document.getElementById('calendar-grid');
    const weekdays = grid.querySelectorAll('.calendar-weekday');
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

        const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
        dayEl.dataset.date = dateStr;

        if (year === today.getFullYear() && month === today.getMonth() && day === today.getDate()) {
            dayEl.classList.add('today');
        }

        const monthData = learningData[year]?.[month + 1]?.[day];
        if (monthData) {
            if (monthData.status === 'completed') {
                dayEl.classList.add('completed');
            } else if (monthData.status === 'partial') {
                dayEl.classList.add('partial');
            } else if (monthData.status === 'scheduled') {
                dayEl.classList.add('scheduled');
            }
        }

        dayEl.addEventListener('click', () => selectDay(dayEl, day, month, year));
        grid.appendChild(dayEl);
    }
}

function setupMonthNavigation() {
    document.getElementById('prev-month').addEventListener('click', () => {
        currentMonth--;
        if (currentMonth < 0) {
            currentMonth = 11;
            currentYear--;
        }
        updateMonthTitle();
        renderCalendar(currentMonth, currentYear);
    });

    document.getElementById('next-month').addEventListener('click', () => {
        currentMonth++;
        if (currentMonth > 11) {
            currentMonth = 0;
            currentYear++;
        }
        updateMonthTitle();
        renderCalendar(currentMonth, currentYear);
    });
}

function updateMonthTitle() {
    const title = document.getElementById('month-title');
    const monthNames = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'];
    title.textContent = `${currentYear}年${monthNames[currentMonth]}`;
}

function initDaySelection() {
    const dayDetail = document.getElementById('day-detail');
    dayDetail.addEventListener('click', (e) => {
        const checkbox = e.target.closest('.task-checkbox');
        if (checkbox) {
            checkbox.classList.toggle('checked');
            const taskItem = checkbox.closest('.task-item');
            taskItem.classList.toggle('completed');
        }
    });
}

function selectDay(dayEl, day, month, year) {
    document.querySelectorAll('.calendar-day.selected').forEach(el => el.classList.remove('selected'));
    dayEl.classList.add('selected');

    selectedDate = { day, month, year };
    const monthNames = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'];
    const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
    const dateObj = new Date(year, month, day);

    document.getElementById('detail-date').textContent = `${monthNames[month]}${day}日`;
    document.getElementById('detail-day').textContent = weekdays[dateObj.getDay()];

    const monthData = learningData[year]?.[month + 1]?.[day];
    const content = document.getElementById('detail-content');

    if (monthData && monthData.tasks.length > 0) {
        content.innerHTML = `
            <div class="task-list">
                ${monthData.tasks.map(task => `
                    <div class="task-item ${task.done ? 'completed' : ''}">
                        <div class="task-checkbox ${task.done ? 'checked' : ''}"></div>
                        <div class="task-info">
                            <div class="task-name">${task.name}</div>
                            <div class="task-meta">${task.duration}</div>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    } else {
        content.innerHTML = `
            <div class="empty-state">
                <svg class="w-12 h-12 text-white/20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>
                </svg>
                <p>暂无学习记录<br>点击右上角添加学习计划</p>
            </div>
        `;
    }
}

function initModal() {
    const modal = document.getElementById('event-modal');
    const addBtn = document.getElementById('add-event-btn');
    const closeBtn = document.getElementById('close-modal');
    const cancelBtn = document.getElementById('cancel-btn');
    const form = document.getElementById('event-form');

    addBtn.addEventListener('click', () => {
        modal.classList.remove('hidden');
        const today = new Date();
        document.getElementById('event-date').value = today.toISOString().split('T')[0];
    });

    closeBtn.addEventListener('click', () => modal.classList.add('hidden'));
    cancelBtn.addEventListener('click', () => modal.classList.add('hidden'));

    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.classList.add('hidden');
    });

    form.addEventListener('submit', (e) => {
        e.preventDefault();
        const title = document.getElementById('event-title').value;
        const date = document.getElementById('event-date').value;
        const duration = document.getElementById('event-duration').value;
        const category = document.querySelector('input[name="event-category"]:checked').value;

        if (title && date) {
            const [year, month, day] = date.split('-').map(Number);
            const monthKey = month;

            if (!learningData[year]) learningData[year] = {};
            if (!learningData[year][monthKey]) learningData[year][monthKey] = {};
            if (!learningData[year][monthKey][day]) learningData[year][monthKey][day] = { status: 'scheduled', tasks: [] };

            learningData[year][monthKey][day].tasks.push({
                name: title,
                duration: `${duration}h`,
                done: false
            });

            renderCalendar(currentMonth, currentYear);

            form.reset();
            modal.classList.add('hidden');
        }
    });
}