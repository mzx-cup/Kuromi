// 临时验证脚本：检查课程生成页面在 token 迁移后是否能正常渲染
// 截图保存到 tests/frontend/screenshots/openmaic-token-verify-*.png

const { test, expect } = require('@playwright/test');

test('openmaic token refactor renders correctly', async ({ page }) => {
    // 监听 console 错误
    const errors = [];
    page.on('pageerror', e => errors.push(`pageerror: ${e.message}\n${e.stack || ''}`));
    page.on('console', msg => {
        if (msg.type() === 'error') errors.push(`console.error: ${msg.text()}`);
    });

    // 加载 index.html
    await page.goto('http://localhost:8765/html/index.html');
    await page.waitForLoadState('networkidle');

    // 切到课程生成 tab
    await page.click('text=课程生成').catch(() => {});
    await page.waitForTimeout(500);

    // dark 模式截图
    await page.screenshot({ path: 'tests/frontend/screenshots/openmaic-token-verify-dark.png', fullPage: false });

    // 验证关键 token 计算值（通过 evaluate）
    const computedValues = await page.evaluate(() => {
        const overlay = document.querySelector('#openmaic-overlay');
        if (!overlay) return { error: 'overlay not found' };
        const s = getComputedStyle(overlay);
        const hero = document.querySelector('.openmaic-hero .openmaic-logo');
        const heroStyle = hero ? getComputedStyle(hero) : null;
        const inputCard = document.querySelector('.openmaic-input-card');
        const inputStyle = inputCard ? getComputedStyle(inputCard) : null;
        return {
            overlayBg: s.background.substring(0, 100),
            heroBg: heroStyle ? heroStyle.backgroundImage.substring(0, 100) : null,
            heroColor: heroStyle ? heroStyle.color : null,
            inputBorder: inputStyle ? inputStyle.borderColor : null,
        };
    });
    console.log('Computed values (dark):', JSON.stringify(computedValues, null, 2));

    // 切到 light 模式（点击主题切换按钮）
    const themeBtn = await page.$('.theme-toggle-btn');
    if (themeBtn) {
        await themeBtn.click();
        await page.waitForTimeout(500);
    }
    await page.screenshot({ path: 'tests/frontend/screenshots/openmaic-token-verify-light.png', fullPage: false });

    // 切回 dark
    if (themeBtn) {
        await themeBtn.click();
        await page.waitForTimeout(500);
    }

    // 切到 6 主题之一（测试 amber 不会被主题污染）
    await page.evaluate(() => {
        document.documentElement.setAttribute('data-theme', 'sakura-falling');
    });
    await page.waitForTimeout(300);
    await page.screenshot({ path: 'tests/frontend/screenshots/openmaic-token-verify-sakura.png', fullPage: false });

    // 还原主题
    await page.evaluate(() => {
        document.documentElement.removeAttribute('data-theme');
    });

    // 断言无 JS 错误
    // 过滤掉与 token 重构无关的预存在环境问题：
    // - favicon 404
    // - 通用资源 404（无 http server 提供 /api 端点等）
    // - Whisper WASM 解析失败（需要打包器，纯静态服务器无法满足）
    // - Live2D WebGL 不可用（headless Chromium 默认无 WebGL）
    const realErrors = errors.filter(e =>
        !e.includes('favicon') &&
        !e.includes('Failed to load resource') &&
        !e.includes('Whisper') &&
        !e.includes('Live2D') &&
        !e.includes('WebGL')
    );
    if (realErrors.length > 0) {
        console.log('\n=== UNEXPECTED CONSOLE ERRORS ===');
        realErrors.forEach((e, i) => console.log(`[${i + 1}] ${e}`));
        console.log('=== END ===\n');
    }
    expect(realErrors.length).toBe(0);
});
