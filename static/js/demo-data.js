/* ============================================================
   演示假数据 — 学习进度页 (progress.html) / 学习日历页 (calendar.html)
             / 学习数据大屏 (data-dashboard.html) 共用
   ------------------------------------------------------------
   触发条件（满足任一即渲染假数据）：
     1. 未登录（localStorage 无 starlearn_user）
     2. 后端接口请求失败
     3. 真实数据为空
   强制开启：URL 加 ?demo=1，或 localStorage.starlearn_demo_mode='1'
   渲染假数据时页面左下角会出现「演示数据」角标。
   ============================================================ */
(function () {
    'use strict';

    const DAY_MS = 24 * 60 * 60 * 1000;

    function pad2(n) { return String(n).padStart(2, '0'); }

    /** 相对今天的 ISO 日期，如 isoAt(-1) = 昨天 */
    function isoAt(offsetDays) {
        const d = new Date(Date.now() + offsetDays * DAY_MS);
        return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
    }

    function isForced() {
        try {
            if (new URLSearchParams(window.location.search).get('demo') === '1') return true;
            return localStorage.getItem('starlearn_demo_mode') === '1';
        } catch (e) { return false; }
    }

    function showBadge() {
        if (document.getElementById('demo-data-badge')) return;
        const badge = document.createElement('div');
        badge.id = 'demo-data-badge';
        badge.textContent = '🧪 演示数据';
        badge.style.cssText = [
            'position:fixed', 'left:16px', 'bottom:16px', 'z-index:9999',
            'padding:6px 14px', 'border-radius:999px',
            'background:rgba(0,0,0,.35)', 'backdrop-filter:blur(8px)',
            'border:1px solid rgba(255,255,255,.25)', 'color:#fff',
            'font-size:12px', 'letter-spacing:.5px', 'pointer-events:none'
        ].join(';');
        document.body.appendChild(badge);
    }

    /* ============================================================
       1. 学习进度页 (progress.js)
       ============================================================ */

    // 不同时间范围给出不同体量，成就解锁数随范围递进（3→4→5→6）
    const RANGE_SUMMARY = {
        week:  { total_hours: 11.5,  avg_daily_hours: 1.6 },
        month: { total_hours: 52.5,  avg_daily_hours: 1.8 },
        year:  { total_hours: 268.5, avg_daily_hours: 0.9 },
        all:   { total_hours: 512.5, avg_daily_hours: 0.7 },
    };

    // 近 7 天每日学习时长（索引 0 = 6 天前）
    const WEEKLY_HOURS = [2.1, 1.5, 0.4, 3.2, 2.8, 1.2, 0.8];

    const COURSE_PROGRESS = [
        { name: 'Python 基础',     progress: 86, icon: '🐍' },
        { name: '算法与数据结构', progress: 64, icon: '🧮' },
        { name: 'Web 开发',        progress: 41, icon: '🌐' },
        { name: '数据库原理',      progress: 23, icon: '🗄️' },
        { name: '系统设计',        progress: 12, icon: '🏗️' },
    ];

    const RADAR_VALUES = [78, 65, 52, 70, 84];

    const TIMELINE = [
        { title: '完成《Python 基础》第七章', time: '今天 14:32', desc: '耗时 38 分钟，测试通过率 100%', status: 'completed' },
        { title: '算法练习：二叉树遍历',       time: '今天 10:15', desc: '中等难度，已通过 5/5 测试用例',   status: 'completed' },
        { title: '正在学习：Web 框架入门',     time: '昨天 21:08', desc: '已完成 41%，预计还需 3.2 小时',   status: 'in-progress' },
        { title: '提交项目：TODO 应用',         time: '昨天 16:40', desc: '代码已合并至 main 分支',          status: 'completed' },
        { title: '复习：高阶函数与闭包',        time: '前天 20:12', desc: '已添加 8 个知识卡片到复习计划',   status: 'completed' },
    ];

    function getProgressSummary(range) {
        const base = RANGE_SUMMARY[range] || RANGE_SUMMARY.month;
        return {
            total_hours: base.total_hours,
            completed_courses: 11,
            current_streak: 12,
            avg_daily_hours: base.avg_daily_hours,
            weekly_activity: WEEKLY_HOURS.map((hours, i) => ({ date: isoAt(i - 6), hours })),
            course_progress: COURSE_PROGRESS,
            timeline: TIMELINE,
            radar: RADAR_VALUES,
        };
    }

    /* ============================================================
       2. 学习日历页 (calendar.js)
       ============================================================ */

    function makeEvent(name, category, opts) {
        const o = opts || {};
        return {
            name,
            category,
            done: !!o.done,
            priority: o.priority || 'medium',
            timeSlot: o.timeSlot || 'afternoon',
            duration: o.duration || '1h',
            desc: o.desc || '',
            remind: true,
        };
    }

    function getCalendarPayload() {
        const eventsData = {};
        const days = {};

        // 过去几天的学习时长（驱动热力图与日历格颜色）
        const pastStudy = [
            { off: -12, minutes: 95 },  { off: -10, minutes: 140 }, { off: -8, minutes: 40 },
            { off: -6, minutes: 85 },   { off: -4, minutes: 120 },  { off: -3, minutes: 60 },
            { off: -2, minutes: 105 },  { off: -1, minutes: 45 },
        ];
        pastStudy.forEach(({ off, minutes }) => {
            days[isoAt(off)] = { status: 'completed', study_minutes: minutes, tasks: [] };
        });

        // 过去的任务（已完成 / 部分完成）
        const pastEvents = [
            { off: -12, name: '完成《Python 基础》第七章练习', category: 'python',    done: true,  priority: 'medium', timeSlot: 'evening',   duration: '1.5h' },
            { off: -10, name: '算法练习：二叉树遍历',          category: 'algorithm', done: true,  priority: 'medium', timeSlot: 'morning',   duration: '2h' },
            { off: -8,  name: '数据库 ER 图建模作业',           category: 'database',  done: true,  priority: 'high',   timeSlot: 'afternoon', duration: '1h' },
            { off: -6,  name: 'Web 框架入门教程',              category: 'web',       done: true,  priority: 'medium', timeSlot: 'evening',   duration: '1.5h' },
            { off: -6,  name: '复习：高阶函数与闭包',           category: 'review',    done: false, priority: 'low',    timeSlot: 'evening',   duration: '0.5h' },
            { off: -4,  name: '线性代数第三章作业',             category: 'study',     done: true,  priority: 'high',   timeSlot: 'morning',   duration: '1h' },
            { off: -3,  name: 'AI 概览读书笔记',               category: 'ai',        done: true,  priority: 'low',    timeSlot: 'afternoon', duration: '1h' },
            { off: -2,  name: '算法周赛复盘',                  category: 'algorithm', done: true,  priority: 'medium', timeSlot: 'evening',   duration: '1.5h' },
            { off: -1,  name: 'Python 装饰器实战练习',          category: 'python',    done: false, priority: 'high',   timeSlot: 'morning',   duration: '1h' },
            { off: -1,  name: '英语词汇打卡',                  category: 'study',     done: true,  priority: 'low',    timeSlot: 'morning',   duration: '0.5h' },
        ];
        pastEvents.forEach(ev => {
            const s = isoAt(ev.off);
            if (!eventsData[s]) eventsData[s] = [];
            eventsData[s].push(makeEvent(ev.name, ev.category, {
                done: ev.done, priority: ev.priority, timeSlot: ev.timeSlot, duration: ev.duration,
            }));
        });

        // 今天：3 项任务，已完成 1 项 → 打卡环 33%
        const todayStr = isoAt(0);
        eventsData[todayStr] = [
            makeEvent('Python 装饰器实战练习', 'python', { done: true, priority: 'high', timeSlot: 'morning', duration: '1h', desc: '重点：闭包与 @wraps' }),
            makeEvent('算法：动态规划入门', 'algorithm', { priority: 'medium', timeSlot: 'afternoon', duration: '2h', desc: '刷完 LeetCode 70 / 198 / 322' }),
            makeEvent('英语词汇打卡 30 分钟', 'study', { priority: 'low', timeSlot: 'evening', duration: '0.5h' }),
        ];
        days[todayStr] = { status: 'partial', study_minutes: 65, tasks: [] };

        // 未来几天的计划（近期学习计划列表）
        const futureEvents = [
            { off: 1,  name: '复习高数第三章：导数应用',     category: 'review',    priority: 'medium', timeSlot: 'evening',   duration: '1.5h', desc: '重点看例题 3.2' },
            { off: 2,  name: '算法周赛模拟训练',            category: 'algorithm', priority: 'high',   timeSlot: 'afternoon', duration: '3h',   desc: '模拟 ACM 90 分钟' },
            { off: 4,  name: 'Python 爬虫实战项目',         category: 'python',    priority: 'medium', timeSlot: 'morning',   duration: '2h',   desc: 'requests + BeautifulSoup' },
            { off: 6,  name: '数据结构：图论与最短路径',     category: 'study',     priority: 'low',    timeSlot: 'afternoon', duration: '2h' },
            { off: 9,  name: '线性代数期中测验',            category: 'exam',      priority: 'high',   timeSlot: 'morning',   duration: '2h',   desc: '闭卷，含证明题' },
            { off: 13, name: 'AI 入门：机器学习基础',       category: 'ai',        priority: 'medium', timeSlot: 'evening',   duration: '1.5h' },
        ];
        futureEvents.forEach(ev => {
            const s = isoAt(ev.off);
            if (!eventsData[s]) eventsData[s] = [];
            eventsData[s].push(makeEvent(ev.name, ev.category, {
                priority: ev.priority, timeSlot: ev.timeSlot, duration: ev.duration, desc: ev.desc,
            }));
        });

        return {
            eventsData,
            calendarData: { days, month_summary: {}, upcoming: [] },
        };
    }

    /* ============================================================
       3. 学习数据大屏 (data-dashboard.html)
       ------------------------------------------------------------
       返回 data-dashboard 内联脚本消费的 legacy learningData 结构:
       { totalMinutes, totalHours, coursesCompleted, coursesTotal,
         courses, streak, exercises, dailyMinutes, hourlyMinutes,
         evaluation, focus, history, radar, goalRings, heatmap }
       时间范围 7d / 30d / 90d 给出不同体量（累计时长与练习数递进）。
       ============================================================ */

    const DASH_RANGE = {
        '7d':  { totalHours: 11.5,  exercises: 46 },
        '30d': { totalHours: 52.5,  exercises: 78 },
        '90d': { totalHours: 268.5, exercises: 95 },
    };

    // 知识图谱节点（按 progress 分档：>=80 已掌握 / >=30 学习中 / 其余待探索）
    const DASH_COURSES = [
        { title: 'Python 基础',     progress: 100, icon: '🐍' },
        { title: 'SQL 实战',        progress: 92,  icon: '🗄️' },
        { title: '算法与数据结构', progress: 86,  icon: '🧮' },
        { title: 'Web 开发',        progress: 64,  icon: '🌐' },
        { title: '数据可视化',      progress: 58,  icon: '📊' },
        { title: '机器学习导论',    progress: 41,  icon: '🤖' },
        { title: '数据库原理',      progress: 35,  icon: '💾' },
        { title: '深度学习',        progress: 18,  icon: '🧠' },
        { title: 'NLP 入门',        progress: 12,  icon: '💬' },
        { title: '系统设计',        progress: 8,   icon: '🏗️' },
    ];

    const DASH_DIMENSIONS = [
        { name: '知识掌握', icon: '🧠', value: 82 },
        { name: '应用能力', icon: '💡', value: 76 },
        { name: '分析思维', icon: '🔍', value: 68 },
        { name: '创造力',   icon: '🎨', value: 61 },
        { name: '表达沟通', icon: '📝', value: 72 },
        { name: '学习效率', icon: '⏱️', value: 85 },
    ];

    function isoAtTime(offsetDays, hour, minute) {
        const d = new Date(Date.now() + offsetDays * DAY_MS);
        d.setHours(hour, minute, 0, 0);
        return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}T${pad2(hour)}:${pad2(minute)}:00`;
    }

    const DASH_TIMELINE = [
        { chapterTitle: 'Python 数据清洗实战',  courseId: 'Python 基础',     updatedAt: isoAtTime(0, 14, 32) },
        { chapterTitle: '二叉树遍历与递归',     courseId: '算法与数据结构', updatedAt: isoAtTime(0, 10, 15) },
        { chapterTitle: 'Pandas GroupBy 练习',  courseId: '数据分析实战',   updatedAt: isoAtTime(-1, 21, 8) },
        { chapterTitle: 'Flask 路由与模板',     courseId: 'Web 开发',        updatedAt: isoAtTime(-1, 16, 40) },
        { chapterTitle: '索引与查询优化',       courseId: '数据库原理',      updatedAt: isoAtTime(-2, 20, 12) },
        { chapterTitle: '梯度下降推导',         courseId: '机器学习导论',    updatedAt: isoAtTime(-3, 19, 5) },
    ];

    /** 近 84 天每日学习分钟数（确定性伪随机 + 周末加成，驱动热力图/迷你图/日柱图） */
    function buildDailyMinutes() {
        const dailyMinutes = {};
        for (let off = -83; off <= 0; off++) {
            let minutes = 0;
            if (off === 0) {
                minutes = 65; // 今天已学 65 分钟
            } else {
                const wave = Math.sin(off * 12.9898) * 43758.5453;
                const r = wave - Math.floor(wave); // 0..1 确定性伪随机
                if (r >= 0.12) { // ~12% 的天没有学习
                    const dow = (new Date(Date.now() + off * DAY_MS).getDay() + 6) % 7;
                    minutes = Math.round(35 + r * 65 + (dow >= 5 ? 30 : 0));
                }
            }
            dailyMinutes[isoAt(off)] = minutes;
        }
        return dailyMinutes;
    }

    /**
     * 从 dailyMinutes 聚合出近 6 周的周数据。
     * 每周从周一开始（getDay()+6）%7===0 为周一。
     * 返回 { hours: number[6], exercises: number[6] }
     */
    function buildWeeklyData(dailyMinutes) {
        // 收集近 6×7=42 天的数据
        const weekHours = [0, 0, 0, 0, 0, 0];
        const weekExercises = [0, 0, 0, 0, 0, 0];
        for (let off = -41; off <= 0; off++) {
            const d = new Date(Date.now() + off * DAY_MS);
            const dow = (d.getDay() + 6) % 7; // Mon=0, Sun=6
            const weekIdx = Math.floor((41 + off) / 7); // 0=最老周, 5=最近周
            if (weekIdx >= 0 && weekIdx < 6) {
                const iso = isoAt(off);
                const mins = dailyMinutes[iso] || 0;
                weekHours[weekIdx] += mins / 60; // 转小时
                // 练习数：从 daily 分钟数推算（每 10 分钟约 1 题）
                weekExercises[weekIdx] += Math.round((mins / 10) * (0.8 + ((off * 9301 + 49297) % 233280) / 233280 * 0.4));
            }
        }
        // 保留 1 位小数
        return {
            hours: weekHours.map(v => Math.round(v * 10) / 10),
            exercises: weekExercises.map(v => Math.round(v)),
        };
    }

    function getDashboardData(range) {
        const base = DASH_RANGE[range] || DASH_RANGE['30d'];
        const dailyMinutes = buildDailyMinutes();
        const weeklyData = buildWeeklyData(dailyMinutes);
        let totalMinutes = 0;
        Object.keys(dailyMinutes).forEach(function (k) { totalMinutes += dailyMinutes[k]; });
        return {
            totalMinutes: totalMinutes,
            totalHours: base.totalHours,
            coursesCompleted: 11,
            coursesTotal: 15,
            courses: DASH_COURSES,
            streak: 12,
            exercises: base.exercises,
            dailyMinutes: dailyMinutes,
            hourlyMinutes: {},
            weeklyMinutes: weeklyData.hours,
            weeklyExercises: weeklyData.exercises,
            evaluation: { dimensions: DASH_DIMENSIONS },
            focus: { score: 87, summary: { focusMinutes: 42, studyMinutes: 65, pageSwitches: 3 } },
            history: DASH_TIMELINE,
            radar: { dimensions: DASH_DIMENSIONS, thisMonth: [], lastMonth: [] },
            goalRings: {},
            heatmap: null,
        };
    }

    /* ============================================================
       4. 心流共振仪 (flow-meter.html)
       ------------------------------------------------------------
       返回 FocusAnalysis 模块消费的 analysis 数据结构：
       { score, today, deepRatio, trend, timeline, timeOfDay, tips }
       以及 getRealtimeState() 返回的实时状态对象。
       ============================================================ */

    function isoAtTime(offsetDays, hour, minute, second) {
        var d = new Date(Date.now() + offsetDays * DAY_MS);
        d.setHours(hour, minute, second || 0, 0);
        return d.toISOString();
    }

    /** 生成 timeline 数据（最近 N 条记录，每隔 ~2 分钟一条） */
    function buildTimeline(count) {
        var entries = [];
        var types = ['deep', 'deep', 'deep', 'shallow', 'shallow', 'warning'];
        for (var i = count - 1; i >= 0; i--) {
            var offMin = i * 2.3;
            var d = new Date(Date.now() - offMin * 60000);
            var h = d.getHours();
            // 夜间分数偏低
            var base = (h >= 22 || h < 6) ? 55 : 75;
            var score = Math.round(base + Math.sin(i * 1.7) * 18 + Math.cos(i * 0.9) * 12);
            score = Math.max(20, Math.min(98, score));
            var r = (i * 9301 + 49297) % 233280 / 233280;
            var type = types[Math.floor(r * types.length)];
            entries.push({
                timestamp: d.toISOString(),
                score: score,
                type: type
            });
        }
        return entries;
    }

    /** 时段分布数据 */
    function buildTimeOfDay() {
        return {
            morning:    { sessions: 3, score: 78 },
            afternoon:  { sessions: 5, score: 85 },
            evening:    { sessions: 4, score: 72 },
            night:      { sessions: 2, score: 58 }
        };
    }

    /** 专注建议 */
    function buildTips() {
        return [
            { type: 'good', text: '下午 14:00–16:00 是你的黄金专注时段，建议安排高难度任务' },
            { type: 'info', text: '本周深度专注率比上周提升了 12%，继续保持 ✨' },
            { type: 'warn', text: '近 3 次会话平均分心次数偏高，尝试使用「勿扰模式」' }
        ];
    }

    /** 构造近期 7 天历史样本（驱动「本周均值」KPI 计算） */
    function buildRecentHistory() {
        var entries = [];
        var types = ['deep', 'deep', 'shallow', 'warning'];
        for (var off = 6; off >= 0; off--) {
            // 每天约 8 条样本，覆盖上午/下午/傍晚
            var hours = [9, 11, 14, 16, 19, 21, 22, 23];
            for (var k = 0; k < hours.length; k++) {
                var d = new Date(Date.now() - off * DAY_MS);
                d.setHours(hours[k], Math.floor(((off * 31 + hours[k]) % 60)), 0, 0);
                var hour = d.getHours();
                var base = (hour >= 22 || hour < 6) ? 55
                         : (hour >= 10 && hour <= 12) ? 85
                         : (hour >= 14 && hour <= 17) ? 82
                         : (hour >= 19 && hour <= 21) ? 74 : 68;
                var seed = (off * 9301 + hours[k] * 49297) % 233280;
                var r = seed / 233280;
                var score = Math.round(base + Math.sin(off + k) * 12 + (r - 0.5) * 18);
                score = Math.max(20, Math.min(98, score));
                var type = types[Math.floor(r * types.length)];
                entries.push({
                    timestamp: d.toISOString(),
                    score: score,
                    type: type
                });
            }
        }
        return entries;
    }

    function getFlowMeterData() {
        var now = new Date();
        var h = now.getHours();

        // 今日数据
        var todayFirst = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 9, 12, 0);

        // 心流指数根据时间段浮动
        var scoreBase = (h >= 10 && h <= 12) ? 86 : (h >= 14 && h <= 17) ? 82 : (h >= 19 && h <= 22) ? 74 : 65;

        return {
            success: true,
            score: scoreBase,
            today: {
                firstSessionTime: todayFirst.toISOString(),
                focusRatio: 72,
                studyMinutes: 65,
                focusMinutes: 47
            },
            deepRatio: 68,
            trend: {
                direction: 'up',
                change: 8,
                previousPeriodScore: 74,
                currentPeriodScore: 82
            },
            timeline: buildTimeline(30),
            timeOfDay: buildTimeOfDay(),
            tips: buildTips(),
            recentHistory: buildRecentHistory()
        };
    }

    function getFlowMeterRealtimeState() {
        var now = new Date();
        var h = now.getHours();
        // 模拟不同时间段处于不同状态
        var state;
        var confidence;
        if (h >= 10 && h <= 12) {
            state = 'focused';
            confidence = 0.94;
        } else if (h >= 14 && h <= 16) {
            state = 'lightly';
            confidence = 0.78;
        } else if (h >= 19 && h <= 22) {
            state = 'focused';
            confidence = 0.86;
        } else if (h >= 22 || h < 6) {
            state = 'distracted';
            confidence = 0.92;
        } else {
            state = 'focused';
            confidence = 0.82;
        }
        // 每秒调用时微调置信度，让指示器有轻微「呼吸」
        var phase = (Date.now() / 4000) % 1;
        var jitter = (phase - 0.5) * 0.08;
        return {
            state: state,
            switchFrequency: state === 'focused' ? 0 : (state === 'lightly' ? 2 : 5),
            lastActivitySec: state === 'focused' ? 18 : (state === 'lightly' ? 42 : 95),
            confidence: Math.round((confidence + jitter) * 100) / 100,
            isHidden: false,
            timestamp: Date.now()
        };
    }

    /* ============================================================
       5. 学习生态页 — 林场 / 植物图鉴 (plant.html)
       ------------------------------------------------------------
       返回 plant.js 消费的 plantState 结构：
       { seeds, ownedPlants, slots, lastUpdate }
       以及一个演示天气对象用于温度/天气 tip。
       已解锁图鉴比例约 24/80，让右上角角标 / 收集页有内容可看。
       ============================================================ */

    // 已解锁的 24 个植物 ID（含若干稀有/精良变体，传说保留 1 个提升惊喜）
    const PLANT_OWNED_IDS = [
        'carrot', 'tomato', 'corn', 'cabbage', 'cucumber', 'pepper',
        'broccoli', 'pumpkin', 'strawberry', 'apple', 'pear', 'peach',
        'cherry', 'grape', 'orange', 'mango',
        'coffee', 'tea', 'lavender', 'tulip', 'sakura', 'relic_flower',
        'rainbow_rose', 'origin_flower'
    ];

    // 槽位 1：已成熟，等待收获（揭晓稀有度）
    // 槽位 2：成长期
    // 槽位 3：空槽位
    function getPlantEcosystemData() {
        const now = Date.now();

        // 槽位 1 — 已成熟（stage=3，剩余时间 0），神秘阶段已揭晓
        const slot1 = {
            plantId: 'sakura',
            plantName: '🌸 樱花树',
            plantEmoji: '🌸',
            plantRarity: 'rare',
            stage: 3,
            remainingTime: 0,
            water: 78,
            nutrient: 65,
            lastUpdate: now
        };

        // 槽位 2 — 处于成长期（stage=2），剩余约 38 分钟
        const slot2GrowMinutes = 38;
        const slot2 = {
            plantId: 'rainbow_rose',
            plantName: '🌈 彩虹玫瑰',
            plantEmoji: '🌈',
            plantRarity: 'fine',
            stage: 2,
            remainingTime: slot2GrowMinutes * 60,
            water: 84,
            nutrient: 72,
            lastUpdate: now
        };

        // 槽位 3 — 空槽位
        const slot3 = { plantId: null, stage: 0, remainingTime: 0, water: 0, nutrient: 0, lastUpdate: now };

        // 已拥有植物（去重，按解锁顺序构造若干时间戳与变体）
        const ownedPlants = PLANT_OWNED_IDS.map((id, idx) => {
            // 已拥有越多越早解锁
            const obtainedAt = now - (PLANT_OWNED_IDS.length - idx) * 2 * DAY_MS;
            // 解锁次数与变体
            const variants = { normal: { count: 1 + (idx % 4), firstObtained: obtainedAt } };
            if (idx % 7 === 0) {
                variants['异色'] = { count: 1, firstObtained: obtainedAt + DAY_MS };
            }
            if (idx % 11 === 0) {
                variants['炫彩'] = { count: 1, firstObtained: obtainedAt + 2 * DAY_MS };
            }
            if (id === 'origin_flower') {
                variants['异色炫彩'] = { count: 1, firstObtained: obtainedAt };
            }
            // 仅存 id 与元数据：渲染时由 plant.js 从 PLANT_DATA 查表补齐 name/emoji/rarity
            return {
                id: id,
                obtainedAt: obtainedAt,
                harvestCount: variants.normal.count,
                variants: variants
            };
        });

        return {
            seeds: 18,
            ownedPlants: ownedPlants,
            slots: [slot1, slot2, slot3],
            lastUpdate: now,
            weather: {
                currentWeather: 'cloudy',
                temperature: 22,
                city: '演示城市 · 上海',
                lastUpdate: now,
                '保温罩': false
            }
        };
    }

    /* ============================================================
       导出
       ============================================================ */
    window.StarDemoData = {
        isForced,
        showBadge,
        getProgressSummary,
        getCalendarPayload,
        getDashboardData,
        getFlowMeterData,
        getFlowMeterRealtimeState,
        getPlantEcosystemData,
    };
})();
