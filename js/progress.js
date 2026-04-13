document.addEventListener('DOMContentLoaded', function() {
    initTimeRangeSelect();
    animateCharts();
    animateProgressBars();
});

function initTimeRangeSelect() {
    const select = document.getElementById('time-range');
    if (select) {
        select.addEventListener('change', function() {
            updateStatsForTimeRange(this.value);
        });
    }
}

function updateStatsForTimeRange(range) {
    const stats = {
        week: { hours: 18, courses: 2, streak: 5, daily: 2.5 },
        month: { hours: 156, courses: 12, streak: 15, daily: 2.5 },
        year: { hours: 480, courses: 24, streak: 45, daily: 1.8 },
        all: { hours: 1250, courses: 48, streak: 120, daily: 2.1 }
    };

    const data = stats[range] || stats.month;
    animateNumber('total-hours', data.hours);
    animateNumber('completed-courses', data.courses);
    animateNumber('current-streak', data.streak);
    animateNumber('avg-daily', data.daily, true);
}

function animateNumber(elementId, targetValue, isDecimal = false) {
    const element = document.getElementById(elementId);
    if (!element) return;

    const duration = 800;
    const startValue = 0;
    const startTime = performance.now();

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const easeProgress = 1 - Math.pow(1 - progress, 3);
        const currentValue = startValue + (targetValue - startValue) * easeProgress;

        if (isDecimal) {
            element.textContent = currentValue.toFixed(1);
        } else {
            element.textContent = Math.round(currentValue);
        }

        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }

    requestAnimationFrame(update);
}

function animateCharts() {
    const bars = document.querySelectorAll('.chart-bar');
    const maxHours = 4;

    bars.forEach((bar, index) => {
        const hours = parseFloat(bar.dataset.hours) || 0;
        const heightPercent = (hours / maxHours) * 100;

        setTimeout(() => {
            const fill = bar.querySelector('.bar-fill');
            if (fill) {
                fill.style.height = heightPercent + '%';
            }
        }, index * 100);
    });
}

function animateProgressBars() {
    const progressBars = document.querySelectorAll('.progress-bar-fill');

    progressBars.forEach((bar, index) => {
        const targetWidth = bar.style.width;
        bar.style.width = '0%';

        setTimeout(() => {
            bar.style.width = targetWidth;
        }, index * 150);
    });
}