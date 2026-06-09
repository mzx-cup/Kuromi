// ============================================
// 专注日历组件 (v2 重构)
// ============================================
// 职责:
//   - 加载本月学习数据 (调用 /api/stats/heatmap/<uid>)
//   - 把"学习分钟数"映射为 5 档强度 (0-4)
//   - 渲染 7×6 网格, 标记今天/未来/空白
//   - 提供点击日期回调 (可扩展跳转到学习回顾页)
//
// 设计:
//   - 暴露 window.FocusCalendar 全局 API, 不污染其它模块
//   - 失败/无数据时优雅降级: 显示空白日历
//   - 表格语义: role=grid + 7 个 columnheader
//
// 依赖:
//   - HTML: .focus-calendar + #focus-calendar-grid + #focus-calendar-month
//   - CSS:  css/hub.css 的 .focus-calendar* 命名空间
// ============================================

(function (global) {
    'use strict';

    /** 强度档位阈值 (分钟) */
    const LEVEL_THRESHOLDS = [0, 5, 15, 45, 90];  // >=X 分钟 → 强度 N
    /** 本月最大查询天数 (含首尾空白, 最多 6 行 7 列 = 42 格) */
    const GRID_ROWS = 6;
    const GRID_COLS = 7;
    const TOTAL_CELLS = GRID_ROWS * GRID_COLS;
    /** 星期日(0) 到 星期六(6) */
    const WEEKDAY_NAMES = ['日', '一', '二', '三', '四', '五', '六'];

    /** 将分钟数映射到 0-4 档强度 */
    function minutesToLevel(minutes) {
        let level = 0;
        for (let i = LEVEL_THRESHOLDS.length - 1; i >= 0; i--) {
            if (minutes >= LEVEL_THRESHOLDS[i]) {
                level = i;
                break;
            }
        }
        return level;
    }

    /** 构造当月信息: firstDayOffset (本月 1 号是星期几) + daysInMonth + today */
    function getMonthInfo(today) {
        const year = today.getFullYear();
        const month = today.getMonth();
        const firstDay = new Date(year, month, 1);
        const nextMonth = new Date(year, month + 1, 1);
        return {
            year,
            month,                              // 0-11
            monthCN: month + 1,                 // 1-12 (显示用)
            firstDayWeekday: firstDay.getDay(), // 0-6 (0=周日)
            daysInMonth: Math.round((nextMonth - firstDay) / 86400000),
            todayDate: today.getDate(),
            todayMonth: month,
            todayYear: year
        };
    }

    /** 构建 42 格 (6×7) 数据模型 */
    function buildCells(info, heatmapMap) {
        const cells = [];
        // 1) 前置空白 (上月残留)
        for (let i = 0; i < info.firstDayWeekday; i++) {
            cells.push({ type: 'empty', key: `empty-${i}` });
        }
        // 2) 当月日期
        for (let d = 1; d <= info.daysInMonth; d++) {
            const minutes = heatmapMap.get(d) || 0;
            const level = minutesToLevel(minutes);
            const isToday =
                d === info.todayDate &&
                info.month === info.todayMonth &&
                info.year === info.todayYear;
            const isFuture = new Date(info.year, info.month, d) >
                              new Date(info.todayYear, info.todayMonth, info.todayDate);
            const weekday = (info.firstDayWeekday + d - 1) % 7;
            cells.push({
                type: 'day',
                key: `d-${d}`,
                day: d,
                level,
                minutes,
                isToday,
                isFuture,
                isWeekend: weekday === 0 || weekday === 6
            });
        }
        // 3) 尾部空白 (凑满 6 行, 视觉对齐)
        while (cells.length < TOTAL_CELLS) {
            cells.push({ type: 'empty', key: `tail-${cells.length}` });
        }
        return cells;
    }

    /** 渲染 42 格到 DOM */
    function renderGrid(gridEl, cells, onDayClick) {
        // 用 DocumentFragment 一次性写入, 避免 42 次回流
        const frag = document.createDocumentFragment();
        for (const cell of cells) {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'focus-calendar__cell';
            btn.setAttribute('data-key', cell.key);

            if (cell.type === 'empty') {
                btn.classList.add('focus-calendar__cell--empty');
                btn.setAttribute('aria-hidden', 'true');
                btn.tabIndex = -1;
                btn.disabled = true;
            } else {
                btn.dataset.level = String(cell.level);
                btn.dataset.day = String(cell.day);
                btn.textContent = String(cell.day);
                btn.setAttribute(
                    'aria-label',
                    `${cell.day}日, ${cell.minutes > 0 ? `学习${cell.minutes}分钟` : '无学习记录'}` +
                    (cell.isToday ? ', 今天' : '') +
                    (cell.isFuture ? ', 未来' : '')
                );
                if (cell.isToday) {
                    btn.classList.add('focus-calendar__cell--today');
                    btn.setAttribute('aria-current', 'date');
                }
                if (cell.isFuture) {
                    btn.classList.add('focus-calendar__cell--future');
                } else if (cell.level === 0 && !cell.isToday) {
                    btn.classList.add('focus-calendar__cell--past-no-study');
                }
                if (cell.isWeekend) {
                    btn.classList.add('focus-calendar__cell--weekend');
                }
                // 未来日期不允许点击
                if (!cell.isFuture) {
                    btn.addEventListener('click', () => {
                        if (typeof onDayClick === 'function') {
                            onDayClick(cell);
                        } else {
                            console.log('[focus-calendar] click day', cell.day, 'minutes', cell.minutes);
                        }
                    });
                }
            }
            frag.appendChild(btn);
        }
        // 清空 + 一次性写入
        gridEl.replaceChildren(frag);
    }

    /** 主入口: 加载 + 渲染 */
    async function load(userId) {
        const gridEl = document.getElementById('focus-calendar-grid');
        const monthEl = document.getElementById('focus-calendar-month');
        if (!gridEl) {
            console.warn('[focus-calendar] #focus-calendar-grid not found');
            return;
        }
        if (!userId) {
            renderFallback(gridEl, monthEl, '请先登录');
            return;
        }

        // 月份 badge 立即显示
        const info = getMonthInfo(new Date());
        if (monthEl) monthEl.textContent = `${info.monthCN}月`;

        // 拉数据
        let heatmapMap = new Map();
        try {
            const resp = await fetch(`/api/stats/heatmap/${userId}?weeks=6`, {
                headers: { 'Accept': 'application/json' }
            });
            if (resp.ok) {
                const json = await resp.json();
                if (json && json.success && Array.isArray(json.heatmap)) {
                    // 过滤当月, 转 Map<day, minutes>
                    for (const item of json.heatmap) {
                        const date = new Date(item.date);
                        if (
                            date.getFullYear() === info.year &&
                            date.getMonth() === info.month &&
                            typeof item.minutes === 'number'
                        ) {
                            heatmapMap.set(date.getDate(), item.minutes);
                        }
                    }
                }
            }
        } catch (e) {
            console.warn('[focus-calendar] heatmap fetch failed, 降级为空日历', e);
        }

        const cells = buildCells(info, heatmapMap);
        renderGrid(gridEl, cells);
    }

    /** 降级渲染: 无数据 / 未登录 */
    function renderFallback(gridEl, monthEl, hint) {
        if (!gridEl) return;
        const info = getMonthInfo(new Date());
        if (monthEl) {
            monthEl.textContent = hint ? `${info.monthCN}月 · ${hint}` : `${info.monthCN}月`;
        }
        const cells = buildCells(info, new Map());
        renderGrid(gridEl, cells);
    }

    // ============ 对外 API ============
    const FocusCalendar = {
        load,
        renderFallback,
        // 暴露工具方法便于测试
        _internal: {
            minutesToLevel,
            getMonthInfo,
            buildCells,
            LEVEL_THRESHOLDS,
            GRID_ROWS,
            GRID_COLS
        }
    };

    global.FocusCalendar = FocusCalendar;

    // ============ 页面加载入口 ============
    // 兼容两种触发方式: DOMContentLoaded 自动跑 / hub.js 显式调用
    document.addEventListener('DOMContentLoaded', () => {
        // 只在 hub 页面跑 (看是否真的有 #focus-calendar-grid)
        if (!document.getElementById('focus-calendar-grid')) return;
        try {
            const userStr = localStorage.getItem('starlearn_user');
            const user = userStr ? JSON.parse(userStr) : null;
            if (user && user.id) {
                FocusCalendar.load(user.id);
            } else {
                FocusCalendar.renderFallback(
                    document.getElementById('focus-calendar-grid'),
                    document.getElementById('focus-calendar-month'),
                    '请登录'
                );
            }
        } catch (e) {
            console.warn('[focus-calendar] init failed', e);
            FocusCalendar.renderFallback(
                document.getElementById('focus-calendar-grid'),
                document.getElementById('focus-calendar-month'),
                ''
            );
        }
    });
})(window);
