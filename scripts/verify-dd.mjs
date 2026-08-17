import { chromium } from 'playwright';
import { mkdir } from 'fs/promises';

const URL = 'http://localhost:8765/data-dashboard.html';
const OUT = 'C:/Users/zwc/Downloads/Kuromi-main/Kuromi-main/verify-dd-out';

async function run() {
    await mkdir(OUT, { recursive: true });
    const browser = await chromium.launch();
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await ctx.newPage();

    const errs = [];
    page.on('pageerror', e => errs.push('pageerror: ' + e.message));
    page.on('console', m => { if (m.type() === 'error') errs.push('console: ' + m.text()); });

    await page.goto(URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);

    // Dismiss any overlay that intercepts pointer events (onboarding, modals)
    await page.evaluate(() => {
        document.querySelectorAll(
            '.onboard-overlay, .modal-overlay, .modal-backdrop, [class*="onboard"]'
        ).forEach(el => el.remove());
    });
    await page.waitForTimeout(500);

    // Overview
    await page.screenshot({ path: `${OUT}/01-overview.png`, fullPage: true });

    // Inject some real data so we can see the dashboard with values
    await page.evaluate(() => {
        const today = new Date();
        const pad = n => n < 10 ? '0' + n : '' + n;
        const iso = d => d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate());
        const daily = {};
        for (let i = 0; i < 14; i++) {
            const d = new Date(); d.setDate(d.getDate() - i);
            daily[iso(d)] = 20 + Math.round(Math.random() * 90);
        }
        localStorage.setItem('starlearn_study', JSON.stringify({
            daily_minutes: daily,
            hourly_minutes: {},
            streak_days: 9,
            last_study_date: iso(today)
        }));
        localStorage.setItem('starlearn_courses_data', JSON.stringify({
            subjects: [
                { id: 'cs', name: '计算机科学', courses: [
                    { id: 'p1', title: 'Python 基础', progress: 92 },
                    { id: 'p2', title: '数据结构与算法', progress: 64 },
                    { id: 'p3', title: '操作系统', progress: 30 }
                ]},
                { id: 'math', name: '数学', courses: [
                    { id: 'm1', title: '线性代数', progress: 100 },
                    { id: 'm2', title: '概率论', progress: 45 }
                ]},
                { id: 'ml', name: '机器学习', courses: [
                    { id: 'ml1', title: '机器学习导论', progress: 22 },
                    { id: 'ml2', title: '深度学习', progress: 8 }
                ]}
            ]
        }));
        localStorage.setItem('starlearn_stats_knowledge_mastery', '67');
        localStorage.setItem('starlearn_evaluation', JSON.stringify({
            masteryScore: 72, codeSkill: 65, studyTime: 42, focusLevel: 78,
            learningPace: 'fast', cognitiveStyle: 'analytical', streakDays: 9
        }));
        localStorage.setItem('courseHistory', JSON.stringify([
            { courseId: 'p1', chapterId: '数据清洗', lastVisited: new Date(Date.now() - 3600000).toISOString() },
            { courseId: 'p2', chapterId: '排序算法', lastVisited: new Date(Date.now() - 7200000).toISOString() },
            { courseId: 'ml1', chapterId: '线性回归', lastVisited: new Date(Date.now() - 86400000).toISOString() }
        ]));
        localStorage.setItem('starlearn_focus_pending', JSON.stringify({
            studyMinutes: 45, focusMinutes: 32, pageSwitches: 3, completedFocus: true
        }));
    });

    // Reload to pick up the data
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);
    await page.evaluate(() => {
        document.querySelectorAll(
            '.onboard-overlay, .modal-overlay, .modal-backdrop, [class*="onboard"]'
        ).forEach(el => el.remove());
    });
    await page.waitForTimeout(1800);
    await page.screenshot({ path: `${OUT}/02-overview-with-data.png`, fullPage: true });

    // Switch tabs and capture (use JS click to bypass any overlay that re-appears)
    async function clickTab(name) {
        await page.evaluate((n) => {
            // strip overlays first
            document.querySelectorAll(
                '.onboard-overlay, .modal-overlay, .modal-backdrop, [class*="onboard"]'
            ).forEach(el => el.remove());
            // also unlock body scroll if overlay set it
            document.body.style.overflow = '';
            const btn = document.querySelector('.dd-tab[data-tab="' + n + '"]');
            if (btn) btn.click();
        }, name);
    }

    await clickTab('radar');
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `${OUT}/03-radar.png`, fullPage: true });

    await clickTab('graph');
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `${OUT}/04-graph.png`, fullPage: true });

    await clickTab('flow');
    await page.waitForTimeout(2500);
    await page.screenshot({ path: `${OUT}/05-flow.png`, fullPage: true });

    // Mobile view
    await page.setViewportSize({ width: 375, height: 800 });
    await clickTab('overview');
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `${OUT}/06-mobile-overview.png`, fullPage: true });

    console.log('SCREENSHOTS_DONE');
    if (errs.length) {
        console.log('ERRORS:');
        errs.forEach(e => console.log('  - ' + e));
    } else {
        console.log('No JS errors');
    }

    await browser.close();
}

run().catch(e => { console.error(e); process.exit(1); });
