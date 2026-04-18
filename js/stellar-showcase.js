document.addEventListener('DOMContentLoaded', function() {
    createStarfield();
    renderBadges();
    initCategoryFilter();
    init3DMouseEffect();
    initModal();
    updateStats();
});

function createStarfield() {
    const bg = document.getElementById('stellar-bg');
    const starCount = 120;

    for (let i = 0; i < starCount; i++) {
        const star = document.createElement('div');
        star.className = 'star';
        star.style.left = Math.random() * 100 + '%';
        star.style.top = Math.random() * 100 + '%';
        star.style.setProperty('--duration', (2 + Math.random() * 4) + 's');
        star.style.setProperty('--delay', Math.random() * 5 + 's');
        star.style.opacity = 0.1 + Math.random() * 0.5;
        bg.appendChild(star);
    }
}

function renderBadges() {
    const container = document.getElementById('badge-showcase');
    if (!window.ACHIEVEMENTS || !window.ACHIEVEMENT_ICONS) {
        console.error('Achievements data not loaded');
        return;
    }

    container.innerHTML = '';

    window.ACHIEVEMENTS.forEach(achievement => {
        const isUnlocked = window.AchievementManager?.isUnlocked(achievement.id) || false;
        const unlockTime = window.AchievementManager?.getUnlockTime(achievement.id);
        const progress = window.AchievementManager?.getProgress(achievement.id) || { current: 0, target: 0, percent: 0 };

        const card = document.createElement('div');
        card.className = `badge-card ${isUnlocked ? '' : 'locked'}`;
        card.dataset.category = achievement.category;
        card.dataset.tier = achievement.tier;
        card.dataset.id = achievement.id;
        card.style.setProperty('--neon-color', achievement.color);

        const iconSvg = window.ACHIEVEMENT_ICONS[achievement.icon] || window.ACHIEVEMENT_ICONS['compass'];

        card.innerHTML = `
            <div class="badge-base">
                <div class="badge-icon">
                    <svg viewBox="0 0 64 64" fill="none">${iconSvg}</svg>
                </div>
                <div class="badge-glare"></div>
                <div class="badge-glow"></div>
            </div>
            <div class="badge-info">
                <h3 class="badge-name">${achievement.name}</h3>
                <p class="badge-desc">${achievement.desc}</p>
                <span class="badge-tier ${achievement.tier}">${getTierLabel(achievement.tier)}</span>
                ${isUnlocked && unlockTime ? `<div class="badge-unlock-time">${formatDate(unlockTime)}</div>` : ''}
                ${!isUnlocked ? `
                    <div class="badge-progress">
                        <div class="progress-mini-bar">
                            <div class="progress-mini-fill" style="width: ${progress.percent}%"></div>
                        </div>
                    </div>
                ` : ''}
            </div>
            ${!isUnlocked ? `
                <div class="locked-overlay">
                    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>
                    </svg>
                    <span>${progress.current}/${progress.target}</span>
                </div>
            ` : ''}
        `;

        container.appendChild(card);
    });

    updateBadgeCount();
}

function getTierLabel(tier) {
    const labels = {
        legendary: '传奇',
        epic: '史诗',
        rare: '稀有',
        common: '普通'
    };
    return labels[tier] || tier;
}

function getCategoryLabel(category) {
    const labels = {
        skill: '技能',
        course: '课程',
        master: '大师'
    };
    return labels[category] || category;
}

function formatDate(timestamp) {
    const date = new Date(timestamp);
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

function formatTime(timestamp) {
    const date = new Date(timestamp);
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
}

function initCategoryFilter() {
    const tabs = document.querySelectorAll('.category-tab');
    const cards = document.querySelectorAll('.badge-card');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            const category = tab.dataset.category;

            cards.forEach(card => {
                if (category === 'all' || card.dataset.category === category) {
                    card.classList.remove('hidden');
                    card.style.animation = 'fadeIn 0.4s ease forwards';
                } else {
                    card.classList.add('hidden');
                }
            });
        });
    });
}

function init3DMouseEffect() {
    const cards = document.querySelectorAll('.badge-card:not(.locked)');

    cards.forEach(card => {
        const base = card.querySelector('.badge-base');

        card.addEventListener('mousemove', (e) => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            const centerX = rect.width / 2;
            const centerY = rect.height / 2;

            const rotateX = (y - centerY) / centerY * -6;
            const rotateY = (x - centerX) / centerX * 6;

            base.style.transform = `translateY(-4px) scale(1.03) rotateX(${rotateX}deg) rotateY(${rotateY}deg)`;
        });

        card.addEventListener('mouseleave', () => {
            base.style.transform = '';
        });
    });
}

function initModal() {
    const modal = document.getElementById('badge-modal');
    const closeBtn = document.getElementById('modal-close');
    const backdrop = modal.querySelector('.modal-backdrop');

    document.querySelectorAll('.badge-card').forEach(card => {
        card.addEventListener('click', () => {
            const achievementId = card.dataset.id;
            const achievement = window.ACHIEVEMENTS.find(a => a.id === achievementId);
            if (!achievement) return;

            const isUnlocked = window.AchievementManager?.isUnlocked(achievementId) || false;
            const unlockTime = window.AchievementManager?.getUnlockTime(achievementId);
            const progress = window.AchievementManager?.getProgress(achievementId) || { current: 0, target: 0, percent: 0 };

            // 设置模态框内容
            document.getElementById('modal-title').textContent = achievement.name;
            document.getElementById('modal-desc').textContent = achievement.desc;

            const tierEl = document.getElementById('modal-tier');
            tierEl.textContent = getTierLabel(achievement.tier);
            tierEl.className = `modal-tier badge-tier ${achievement.tier}`;

            // 设置日期
            const dateEl = document.getElementById('modal-date');
            if (isUnlocked && unlockTime) {
                dateEl.textContent = `获得于 ${formatDate(unlockTime)}`;
            } else {
                dateEl.textContent = '未解锁';
            }

            // 设置图标
            const iconContainer = document.getElementById('modal-icon-container');
            const iconSvg = window.ACHIEVEMENT_ICONS[achievement.icon] || window.ACHIEVEMENT_ICONS['compass'];
            iconContainer.innerHTML = `<svg viewBox="0 0 64 64" fill="none">${iconSvg}</svg>`;

            // 设置徽章基础样式
            const badgeBase = document.getElementById('modal-badge-base');
            badgeBase.style.setProperty('--neon-color', achievement.color);

            // 设置进度
            const progressFill = document.getElementById('progress-fill');
            const progressText = document.getElementById('progress-text');
            const progressContainer = document.getElementById('modal-progress');

            if (isUnlocked) {
                progressContainer.style.display = 'none';
            } else {
                progressContainer.style.display = 'block';
                progressFill.style.width = `${progress.percent}%`;
                progressFill.style.setProperty('--neon-color', achievement.color);
                progressText.textContent = `${progress.current} / ${progress.target}`;
            }

            // 设置统计
            document.getElementById('stat-unlocked-time').textContent = isUnlocked && unlockTime ? formatTime(unlockTime) : '-';
            document.getElementById('stat-category').textContent = getCategoryLabel(achievement.category);
            document.getElementById('stat-rarity').textContent = getTierLabel(achievement.tier);

            modal.classList.add('active');
            document.body.style.overflow = 'hidden';
        });
    });

    closeBtn.addEventListener('click', closeModal);
    backdrop.addEventListener('click', closeModal);

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal.classList.contains('active')) {
            closeModal();
        }
    });

    function closeModal() {
        modal.classList.remove('active');
        document.body.style.overflow = '';
    }
}

function updateBadgeCount() {
    const unlockedCount = window.AchievementManager?.getUnlockedCount() || 0;
    const totalCount = window.ACHIEVEMENTS?.length || 0;

    document.getElementById('badge-count').textContent = unlockedCount;
    document.getElementById('badge-total').textContent = totalCount;
}

function updateStats() {
    if (!window.ACHIEVEMENTS || !window.AchievementManager) return;

    const stats = { legendary: 0, epic: 0, rare: 0, common: 0 };

    window.ACHIEVEMENTS.forEach(achievement => {
        if (window.AchievementManager.isUnlocked(achievement.id)) {
            stats[achievement.tier]++;
        }
    });

    document.getElementById('legendary-count').textContent = stats.legendary;
    document.getElementById('epic-count').textContent = stats.epic;
    document.getElementById('rare-count').textContent = stats.rare;
    document.getElementById('common-count').textContent = stats.common;
}

// 添加动画样式
const style = document.createElement('style');
style.textContent = `
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(15px); }
        to { opacity: 1; transform: translateY(0); }
    }
`;
document.head.appendChild(style);
