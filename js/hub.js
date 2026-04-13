// ============================================
// Data Particle Animation
// ============================================
function createDataParticles() {
    const bg = document.getElementById('hub-bg');
    if (!bg) return;

    const particleCount = 30;

    for (let i = 0; i < particleCount; i++) {
        const particle = document.createElement('div');
        particle.className = 'data-particle';

        const size = Math.random() * 4 + 2;
        const left = Math.random() * 100;
        const duration = Math.random() * 20 + 15;
        const delay = Math.random() * 20;

        const colors = [
            'rgba(168, 85, 247, 0.6)',
            'rgba(59, 130, 246, 0.6)',
            'rgba(16, 185, 129, 0.6)',
            'rgba(249, 115, 22, 0.6)',
            'rgba(236, 72, 153, 0.6)'
        ];

        particle.style.cssText = `
            width: ${size}px;
            height: ${size}px;
            left: ${left}%;
            background: ${colors[Math.floor(Math.random() * colors.length)]};
            animation-duration: ${duration}s;
            animation-delay: -${delay}s;
        `;

        bg.appendChild(particle);
    }
}

// ============================================
// Radial Progress Animation
// ============================================
function animateRadialProgress() {
    const rings = document.querySelectorAll('.radial-ring .progress');
    rings.forEach((ring, index) => {
        const offset = ring.style.strokeDashoffset;
        setTimeout(() => {
            ring.style.strokeDashoffset = offset;
        }, 300 + (index * 150));
    });
}

// ============================================
// Bar Chart Animation
// ============================================
function animateBarCharts() {
    const bars = document.querySelectorAll('.bar, .focus-bar');
    bars.forEach((bar, index) => {
        const height = bar.style.height;
        bar.style.height = '0';
        setTimeout(() => {
            bar.style.height = height;
        }, 100 + (index * 80));
    });
}

// ============================================
// Line Chart Animation
// ============================================
function animateLineChart() {
    const path = document.querySelector('.chart-path');
    const area = document.querySelector('.chart-area');
    const dots = document.querySelectorAll('.chart-dot');

    if (path) {
        const length = path.getTotalLength();
        path.style.strokeDasharray = length;
        path.style.strokeDashoffset = length;

        setTimeout(() => {
            path.style.transition = 'stroke-dashoffset 2s ease-out';
            path.style.strokeDashoffset = '0';
        }, 500);
    }

    if (area) {
        area.style.opacity = '0';
        setTimeout(() => {
            area.style.transition = 'opacity 1s ease-out';
            area.style.opacity = '1';
        }, 1500);
    }

    dots.forEach((dot, index) => {
        dot.style.opacity = '0';
        dot.style.transform = 'scale(0)';
        setTimeout(() => {
            dot.style.transition = 'all 0.3s ease-out';
            dot.style.opacity = '1';
            dot.style.transform = 'scale(1)';
        }, 2000 + (index * 100));
    });
}

// ============================================
// Initialize
// ============================================
document.addEventListener('DOMContentLoaded', function() {
    createDataParticles();
    animateRadialProgress();
    animateBarCharts();
    animateLineChart();
});

// Smooth scroll for navigation
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({ behavior: 'smooth' });
        }
    });
});