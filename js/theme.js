(function() {
    const LIGHT_THEMES = new Set(['sakura-falling']);
    const STORAGE_KEY = 'starlearn_theme';
    const DEFAULT_THEME = 'ocean';
    let sakuraCanvas = null;
    let sakuraAnimationId = null;

    function isLightTheme(theme) {
        return LIGHT_THEMES.has(theme);
    }

    function getCurrentTheme() {
        return localStorage.getItem(STORAGE_KEY) || DEFAULT_THEME;
    }

    function renderSakuraParticles() {
        const existingCanvas = document.getElementById('sakura-canvas');
        if (existingCanvas) {
            existingCanvas.remove();
            sakuraCanvas = null;
        }

        sakuraCanvas = document.createElement('canvas');
        sakuraCanvas.id = 'sakura-canvas';
        sakuraCanvas.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:0;opacity:0.6;';
        document.body.appendChild(sakuraCanvas);

        const canvas = sakuraCanvas;
        const ctx = canvas.getContext('2d');
        const particles = [];
        const particleCount = 50;

        function resize() {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        }
        resize();
        window.addEventListener('resize', resize);

        class SakuraParticle {
            constructor() {
                this.reset();
            }
            reset() {
                this.x = Math.random() * canvas.width;
                this.y = Math.random() * canvas.height - canvas.height;
                this.size = Math.random() * 8 + 4;
                this.speedY = Math.random() * 1 + 0.5;
                this.speedX = Math.random() * 0.5 - 0.25;
                this.rotation = Math.random() * 360;
                this.rotationSpeed = Math.random() * 2 - 1;
                this.opacity = Math.random() * 0.5 + 0.3;
            }
            update() {
                this.y += this.speedY;
                this.x += this.speedX;
                this.rotation += this.rotationSpeed;
                if (this.y > canvas.height) {
                    this.reset();
                    this.y = -10;
                }
            }
            draw() {
                ctx.save();
                ctx.translate(this.x, this.y);
                ctx.rotate(this.rotation * Math.PI / 180);
                ctx.globalAlpha = this.opacity;
                ctx.fillStyle = '#ffb7c5';
                ctx.beginPath();
                ctx.ellipse(0, 0, this.size, this.size / 2, 0, 0, Math.PI * 2);
                ctx.fill();
                ctx.restore();
            }
        }

        for (let i = 0; i < particleCount; i++) {
            particles.push(new SakuraParticle());
        }

        function animate() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            particles.forEach(p => {
                p.update();
                p.draw();
            });
            sakuraAnimationId = requestAnimationFrame(animate);
        }
        animate();
    }

    function stopSakuraParticles() {
        if (sakuraAnimationId) {
            cancelAnimationFrame(sakuraAnimationId);
            sakuraAnimationId = null;
        }
        if (sakuraCanvas) {
            sakuraCanvas.remove();
            sakuraCanvas = null;
        }
    }

    function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        const isLight = isLightTheme(theme);
        document.body.classList.toggle('light-theme', isLight);
        document.documentElement.classList.toggle('dark', !isLight);
        if (theme === 'sakura-falling') {
            renderSakuraParticles();
        } else {
            stopSakuraParticles();
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
        renderSakuraParticles: renderSakuraParticles,
        stopSakuraParticles: stopSakuraParticles
    };
})();
