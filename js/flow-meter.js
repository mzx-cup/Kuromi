class FlowWaveform {
    constructor(canvas) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.isRunning = true;
        this.init();
    }

    init() {
        this.resize();
        window.addEventListener('resize', () => this.resize());
        this.setupPageSwitchTracking();
        this.animate(0);
    }

    resize() {
        const rect = this.canvas.parentElement.getBoundingClientRect();
        this.canvas.width = rect.width * window.devicePixelRatio;
        this.canvas.height = rect.height * window.devicePixelRatio;
        this.ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
        this.width = rect.width;
        this.height = rect.height;
    }

    setupPageSwitchTracking() {
        this.pageSwitches = [];
        this.currentState = 'focused';
        this.stateProgress = 0;
        this.targetState = 'focused';
        this.transitionDuration = 2000;
        this.transitionStart = 0;
        this.lastStateChange = Date.now();

        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.recordPageSwitch();
            }
        });

        window.addEventListener('blur', () => {
            this.recordPageSwitch();
        });
    }

    recordPageSwitch() {
        const now = Date.now();
        this.pageSwitches.push(now);
        this.pageSwitches = this.pageSwitches.filter(t => now - t < 60000);

        if (this.currentState !== 'distracted') {
            this.startTransition('distracted');
        }
    }

    getSwitchFrequency() {
        const now = Date.now();
        const recent = this.pageSwitches.filter(t => now - t < 60000);
        return recent.length;
    }

    getDistractedAmplitude() {
        const frequency = this.getSwitchFrequency();
        const baseAmplitude = this.height * 0.06;
        const freqBonus = Math.min(frequency * 0.02, this.height * 0.08);
        return baseAmplitude + freqBonus + this.height * 0.03;
    }

    startTransition(newState) {
        if (this.targetState === newState) return;
        this.targetState = newState;
        this.transitionStart = Date.now();
    }

    lerpColor(color1, color2, t) {
        const c1 = this.hexToRgb(color1);
        const c2 = this.hexToRgb(color2);
        const r = Math.round(c1.r + (c2.r - c1.r) * t);
        const g = Math.round(c1.g + (c2.g - c1.g) * t);
        const b = Math.round(c1.b + (c2.b - c1.b) * t);
        return `rgb(${r},${g},${b})`;
    }

    hexToRgb(hex) {
        const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        return result ? {
            r: parseInt(result[1], 16),
            g: parseInt(result[2], 16),
            b: parseInt(result[3], 16)
        } : { r: 0, g: 188, b: 129 };
    }

    getStateColors() {
        return {
            focused: '#00C853',
            lightly: '#9E9E9E',
            distracted: '#F44336'
        };
    }

    updateState(t) {
        const now = Date.now();
        const timeSinceChange = now - this.lastStateChange;

        if (this.currentState !== this.targetState) {
            const elapsed = now - this.transitionStart;
            const progress = Math.min(elapsed / this.transitionDuration, 1);

            if (progress >= 1) {
                this.currentState = this.targetState;
                this.lastStateChange = now;
            }
        }

        if (timeSinceChange > 5000 && this.currentState === 'distracted') {
            this.targetState = 'lightly';
        }

        if (timeSinceChange > 30000 && this.currentState === 'lightly') {
            this.targetState = 'focused';
        }

        return {
            state: this.currentState,
            progress: this.getTransitionProgress()
        };
    }

    getTransitionProgress() {
        if (this.currentState === this.targetState) return 1;
        const elapsed = Date.now() - this.transitionStart;
        return Math.min(elapsed / this.transitionDuration, 1);
    }

    getCurrentColor(state, progress) {
        const colors = this.getStateColors();
        let fromColor, toColor;

        if (progress >= 1 || this.currentState === this.targetState) {
            return colors[this.targetState];
        }

        if (state === this.targetState) {
            fromColor = colors[this.currentState];
            toColor = colors[this.targetState];
        } else {
            fromColor = colors[this.targetState];
            toColor = colors[this.currentState];
        }

        return this.lerpColor(fromColor, toColor, progress);
    }

    generateECGWave(t, baseY, amplitude, frequency) {
        const phase = t * frequency;

        const breathWave = Math.sin(phase * 0.3) * amplitude * 0.4;

        const cardiacWave =
            Math.sin(phase) * amplitude * 0.3 +
            Math.sin(phase * 2) * amplitude * 0.15 +
            Math.sin(phase * 3) * amplitude * 0.08;

        const microNoise = (Math.random() - 0.5) * amplitude * 0.1;

        return baseY + breathWave + cardiacWave + microNoise;
    }

    drawWave(time) {
        const t = time / 1000;
        const stateInfo = this.updateState(t);

        this.ctx.clearRect(0, 0, this.width, this.height);

        let baseY, amplitude, frequency;

        switch (stateInfo.state) {
            case 'focused':
                baseY = this.height * 0.35;
                amplitude = this.height * 0.04;
                frequency = 1.5;
                break;
            case 'lightly':
                baseY = this.height * 0.5;
                amplitude = this.height * 0.07;
                frequency = 2.0;
                break;
            case 'distracted':
                baseY = this.height * 0.6;
                amplitude = this.getDistractedAmplitude();
                frequency = 2.5;
                break;
            default:
                baseY = this.height * 0.4;
                amplitude = this.height * 0.05;
                frequency = 1.5;
        }

        const currentColor = this.getCurrentColor(stateInfo.state, stateInfo.progress);

        const gradient = this.ctx.createLinearGradient(0, 0, 0, this.height);
        const rgb = this.hexToRgb(currentColor);
        gradient.addColorStop(0, `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.25)`);
        gradient.addColorStop(0.5, `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.08)`);
        gradient.addColorStop(1, `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.02)`);

        this.ctx.beginPath();
        this.ctx.moveTo(0, this.height);

        const points = 300;
        for (let i = 0; i <= points; i++) {
            const x = (i / points) * this.width;
            const localT = t + (i / points) * 2;
            const y = this.generateECGWave(localT, baseY, amplitude, frequency);
            this.ctx.lineTo(x, y);
        }

        this.ctx.lineTo(this.width, this.height);
        this.ctx.closePath();
        this.ctx.fillStyle = gradient;
        this.ctx.fill();

        this.ctx.strokeStyle = currentColor;
        this.ctx.lineWidth = 2.5;
        this.ctx.lineCap = 'round';
        this.ctx.lineJoin = 'round';
        this.ctx.shadowColor = currentColor;
        this.ctx.shadowBlur = 12;

        this.ctx.beginPath();
        for (let i = 0; i <= points; i++) {
            const x = (i / points) * this.width;
            const localT = t + (i / points) * 2;
            const y = this.generateECGWave(localT, baseY, amplitude, frequency);

            if (i === 0) {
                this.ctx.moveTo(x, y);
            } else {
                this.ctx.lineTo(x, y);
            }
        }
        this.ctx.stroke();
        this.ctx.shadowBlur = 0;

        this.drawGrid();
        this.drawLabels(stateInfo.state, currentColor);
    }

    drawGrid() {
        this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
        this.ctx.lineWidth = 1;

        for (let i = 1; i < 4; i++) {
            const y = (this.height / 4) * i;
            this.ctx.beginPath();
            this.ctx.moveTo(0, y);
            this.ctx.lineTo(this.width, y);
            this.ctx.stroke();
        }

        for (let i = 1; i < 6; i++) {
            const x = (this.width / 6) * i;
            this.ctx.beginPath();
            this.ctx.moveTo(x, 0);
            this.ctx.lineTo(x, this.height);
            this.ctx.stroke();
        }
    }

    drawLabels(state, color) {
        this.ctx.font = '11px Inter, sans-serif';

        this.ctx.fillStyle = color;
        this.ctx.fillRect(10, 10, 8, 8);

        const stateText = {
            focused: '专注',
            lightly: '轻度专注',
            distracted: '走神'
        };

        this.ctx.fillText(stateText[state] || '专注', 24, 18);

        this.ctx.fillStyle = 'rgba(255, 255, 255, 0.4)';
        this.ctx.textAlign = 'right';
        this.ctx.fillText('-60s', 50, this.height - 10);
        this.ctx.fillText('现在', this.width - 10, this.height - 10);
        this.ctx.textAlign = 'left';
    }

    animate(time) {
        if (!this.isRunning) return;
        this.drawWave(time);
        requestAnimationFrame((t) => this.animate(t));
    }

    stop() {
        this.isRunning = false;
    }
}

class FlowMeter {
    constructor() {
        this.focusTime = 45 * 60;
        this.switchCount = 0;
        this.flowScore = 78;
        this.deepRatio = 82;
        this.sessionStart = Date.now();
        this.isRunning = true;
        this.init();
    }

    init() {
        this.waveform = new FlowWaveform(document.getElementById('waveform-canvas'));
        this.updateStats();
        this.startTimer();
        this.initEventListeners();
    }

    initEventListeners() {
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
            });
        });
    }

    updateStats() {
        document.getElementById('deep-value').textContent = this.deepRatio;
        document.getElementById('deep-ring').style.setProperty('--percent', this.deepRatio);

        const ring = document.getElementById('deep-ring');
        const circumference = 2 * Math.PI * 42;
        const offset = circumference - (this.deepRatio / 100) * circumference;
        ring.style.strokeDasharray = `${circumference}`;
        ring.style.strokeDashoffset = offset;

        document.getElementById('focus-time').textContent = this.formatTime(this.focusTime);
        document.getElementById('switch-count').textContent = this.switchCount;
        document.getElementById('flow-score').textContent = this.flowScore;
        document.getElementById('state-fill').style.width = `${this.deepRatio}%`;

        const stateText = document.getElementById('state-text');
        const stateDesc = document.getElementById('state-desc');
        const stateOrb = document.querySelector('.orb-inner');

        if (this.deepRatio >= 70) {
            stateText.textContent = '深度专注中';
            stateText.style.color = '#00C853';
            stateDesc.textContent = '继续保持，学习效率很高';
            stateOrb.style.background = 'radial-gradient(circle, #00C853 0%, #00a844 100%)';
            stateOrb.style.boxShadow = '0 0 30px rgba(0, 200, 83, 0.6)';
        } else if (this.deepRatio >= 40) {
            stateText.textContent = '轻度专注';
            stateText.style.color = '#9E9E9E';
            stateDesc.textContent = '注意力有所分散，建议集中精神';
            stateOrb.style.background = 'radial-gradient(circle, #9E9E9E 0%, #757575 100%)';
            stateOrb.style.boxShadow = '0 0 30px rgba(158, 158, 158, 0.6)';
        } else {
            stateText.textContent = '注意力分散';
            stateText.style.color = '#F44336';
            stateDesc.textContent = '建议休息片刻，恢复精力';
            stateOrb.style.background = 'radial-gradient(circle, #F44336 0%, #c62828 100%)';
            stateOrb.style.boxShadow = '0 0 30px rgba(244, 67, 54, 0.6)';
        }
    }

    startTimer() {
        setInterval(() => {
            if (!this.isRunning) return;

            this.focusTime--;
            if (this.focusTime < 0) this.focusTime = 0;

            const elapsed = Math.floor((Date.now() - this.sessionStart) / 1000);
            const totalSeconds = 60 * 60;
            const progress = Math.min(100, (elapsed / totalSeconds) * 100);

            document.getElementById('session-progress').style.width = `${progress}%`;
            document.querySelector('.progress-text').textContent = `${Math.round(progress)}% 完成`;

            const remaining = this.getRemainingTime();
            document.getElementById('remaining-time').textContent = remaining;

            if (Math.random() < 0.01) {
                this.deepRatio = Math.max(20, Math.min(95, this.deepRatio + (Math.random() - 0.5) * 10));
                this.flowScore = Math.round(this.deepRatio * 0.95);
                this.updateStats();
            }
        }, 1000);
    }

    formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }

    getRemainingTime() {
        const remaining = Math.max(0, this.focusTime);
        return this.formatTime(remaining);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const flowMeter = new FlowMeter();
});
