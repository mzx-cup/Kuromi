/**
 * 深度思考 UI 回归 — 验证两个路径:
 * A. 点击 "✨ 已深度思考" 徽标 → timeline 容器+内部内容都可见
 *    (修复: .think-done-timeline 没有 CSS 规则, 内部 .think-log-timeline 永远 max-height:0)
 * B. 点击 "深度思考" 按钮 → think-block-body 内容可见
 */
const { test, expect } = require('@playwright/test');

const BASE = 'http://127.0.0.1:8765';

async function injectAndWait(page) {
    await page.addInitScript(() => {
        localStorage.setItem('starlearn_user', JSON.stringify({
            id: 'test_user', name: '测试', avatar: 'x',
        }));
        localStorage.setItem('starlearn_persona', 'patient_tutor');
    });
    await page.goto(`${BASE}/html/index.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1500);

    const ok = await page.evaluate(() => {
        if (typeof messages === 'undefined') return 'messages undefined';
        messages.length = 0;
        messages.push({ role: 'user', content: '什么是分布式系统?', _timestamp: 'u1' });
        messages.push({
            role: 'assistant',
            content: '<think>关键步骤 1：分析问题。\n关键步骤 2：拆解子任务。\n关键步骤 3：给出结论。</think>这是我的最终回答。',
            _timestamp: 'a1',
            _thinkingLogs: [
                { agent: 'planner', content: '正在拆解问题' },
                { agent: 'coder', content: '正在执行计划' },
            ],
        });
        renderMessages();
        return 'ok';
    });
    if (ok !== 'ok') throw new Error(`注入失败: ${ok}`);
    await page.waitForSelector('.think-block-header', { timeout: 5000 });
    await page.waitForSelector('.think-collapsed-badge', { timeout: 5000 });
    await page.waitForTimeout(300);
}

async function readBox(el) {
    return el.evaluate((node) => {
        const style = getComputedStyle(node);
        const rect = node.getBoundingClientRect();
        return {
            maxHeight: parseFloat(style.maxHeight),
            opacity: parseFloat(style.opacity),
            height: rect.height,
            display: style.display,
        };
    });
}

test.describe('深度思考 UI 回归', () => {
    test('路径 A: 点击 "✨ 已深度思考" 徽标后 timeline 内部内容可见', async ({ page }) => {
        await injectAndWait(page);
        const badge = page.locator('.think-collapsed-badge');
        const timeline = page.locator('.think-done-timeline');
        const thinkLog = page.locator('.think-log-timeline');

        // 初始: badge 可见, timeline hidden
        await expect(badge).toBeVisible();
        await expect(timeline).toBeHidden();
        const before = await readBox(thinkLog);
        expect(before.maxHeight, '初始 think-log-timeline 应该 max-height 0').toBe(0);
        expect(before.opacity, '初始 opacity 0').toBe(0);

        await badge.click();
        // 等动画完成: maxHeight 260 且 opacity 1
        await page.waitForFunction(() => {
            const el = document.querySelector('.think-log-timeline');
            if (!el) return false;
            const s = getComputedStyle(el);
            return parseFloat(s.maxHeight) >= 259 && parseFloat(s.opacity) >= 0.99;
        }, { timeout: 3000 });

        await expect(badge).toBeHidden();
        await expect(timeline).toBeVisible();

        const info = await readBox(thinkLog);
        console.log('  ✅ 路径 A — think-log-timeline 展开后样式:', info);
        expect(info.height, 'think-log-timeline 实际高度').toBeGreaterThan(10);
        expect(info.maxHeight, 'max-height 展开到 260px').toBeGreaterThanOrEqual(259);
        expect(info.opacity, 'opacity = 1').toBeGreaterThanOrEqual(0.99);
    });

    test('路径 B: 点击 "深度思考" 按钮后 think-block-body 可见', async ({ page }) => {
        await injectAndWait(page);
        const header = page.locator('.think-block-header');
        const body = page.locator('.think-block-body');

        const before = await readBox(body);
        expect(before.maxHeight, '初始 think-block-body 应该 max-height 0').toBe(0);

        await header.click();
        await page.waitForFunction(() => {
            const el = document.querySelector('.think-block-body');
            if (!el) return false;
            const s = getComputedStyle(el);
            return parseFloat(s.maxHeight) >= 590 && parseFloat(s.opacity) >= 0.99;
        }, { timeout: 3000 });

        const info = await readBox(body);
        console.log('  ✅ 路径 B — think-block-body 展开后样式:', info);
        expect(info.height, 'think-block-body 实际高度').toBeGreaterThan(10);
        expect(info.maxHeight, 'max-height 展开到 600px').toBeGreaterThanOrEqual(590);
        expect(info.opacity, 'opacity = 1').toBeGreaterThanOrEqual(0.99);
    });
});
