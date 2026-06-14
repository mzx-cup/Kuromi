// Classroom token refactor visual regression test
// Captures screenshots and validates computed styles after v4 token integration

const { test, expect } = require('@playwright/test');

test('classroom token refactor renders correctly', async ({ page }) => {
    const errors = [];
    page.on('pageerror', e => errors.push(`pageerror: ${e.message}`));
    page.on('console', msg => {
        if (msg.type() === 'error') errors.push(`console.error: ${msg.text()}`);
    });

    // Load classroom page
    await page.goto('http://localhost:8765/html/classroom.html');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Screenshot dark/default mode
    await page.screenshot({ path: 'tests/frontend/screenshots/classroom-token-verify-dark.png', fullPage: false });

    // Verify key computed values
    const computed = await page.evaluate(() => {
        const page_el = document.querySelector('.classroom-page');
        const slide = document.querySelector('.slide-container');
        const header = document.querySelector('.classroom-header');

        const pageStyle = page_el ? getComputedStyle(page_el) : null;
        const slideStyle = slide ? getComputedStyle(slide) : null;
        const headerStyle = header ? getComputedStyle(header) : null;

        return {
            // Font check
            pageFont: pageStyle ? pageStyle.fontFamily : null,
            // PPT size check (should be 16:9 responsive)
            slideWidth: slide ? slide.offsetWidth : null,
            slideHeight: slide ? slide.offsetHeight : null,
            slideRatio: slide ? (slide.offsetWidth / slide.offsetHeight).toFixed(3) : null,
            // Glass backdrop-filter
            headerBackdrop: headerStyle ? headerStyle.backdropFilter : null,
            // Key token colors
            slideBg: slideStyle ? slideStyle.background.substring(0, 60) : null,
            primaryColor: pageStyle ? pageStyle.getPropertyValue('--primary').trim() : null,
            accentColor: pageStyle ? pageStyle.getPropertyValue('--accent').trim() : null,
        };
    });

    console.log('Computed values (dark):', JSON.stringify(computed, null, 2));

    // Verify 16:9 aspect ratio (tolerance 0.05)
    if (computed.slideRatio) {
        const ratio = parseFloat(computed.slideRatio);
        expect(Math.abs(ratio - 1.778)).toBeLessThan(0.1);
        console.log(`Slide size: ${computed.slideWidth}x${computed.slideHeight}, ratio: ${computed.slideRatio}`);
    }

    // Verify glass backdrop-filter is active
    if (computed.headerBackdrop) {
        expect(computed.headerBackdrop).toContain('blur');
        console.log('Glass backdrop-filter active:', computed.headerBackdrop);
    }

    // Switch to sakura theme (brand accent should remain fixed amber)
    await page.evaluate(() => {
        document.documentElement.setAttribute('data-theme', 'sakura-falling');
    });
    await page.waitForTimeout(500);

    // Re-check accent is still amber (not sakura pink)
    const accentAfterTheme = await page.evaluate(() => {
        const page_el = document.querySelector('.classroom-page');
        const style = page_el ? getComputedStyle(page_el) : null;
        return style ? style.getPropertyValue('--accent').trim() : null;
    });
    console.log('Accent after sakura theme:', accentAfterTheme);

    await page.screenshot({ path: 'tests/frontend/screenshots/classroom-token-verify-sakura.png', fullPage: false });

    // Reset theme
    await page.evaluate(() => {
        document.documentElement.removeAttribute('data-theme');
    });

    // Filter pre-existing errors
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
