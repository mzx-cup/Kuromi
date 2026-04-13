(function() {
    const LIGHT_THEMES = new Set(['sakura-falling']);
    const STORAGE_KEY = 'starlearn_theme';
    const DEFAULT_THEME = 'ocean';

    function isLightTheme(theme) {
        return LIGHT_THEMES.has(theme);
    }

    function getCurrentTheme() {
        return localStorage.getItem(STORAGE_KEY) || DEFAULT_THEME;
    }

    function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        const isLight = isLightTheme(theme);
        document.body.classList.toggle('light-theme', isLight);
        document.documentElement.classList.toggle('dark', !isLight);
        if (theme === 'sakura-falling') {
            renderSakuraParticles();
        }
    }

    function initTheme() {
        const theme = getCurrentTheme();
        applyTheme(theme);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initTheme);
    } else {
        initTheme();
    }

    window.StarTheme = {
        LIGHT_THEMES: LIGHT_THEMES,
        isLightTheme: isLightTheme,
        getCurrentTheme: getCurrentTheme,
        applyTheme: applyTheme,
        initTheme: initTheme,
        renderSakuraParticles: renderSakuraParticles
    };
})();
