// 成就管理器 - 跟踪和解锁成就
(function() {
    const STORAGE_KEY = 'starlearn_achievements';

    // 获取已解锁的成就
    function getUnlockedAchievements() {
        try {
            const data = localStorage.getItem(STORAGE_KEY);
            return data ? JSON.parse(data) : {};
        } catch (e) {
            return {};
        }
    }

    // 保存成就
    function saveAchievement(achievementId, data = {}) {
        const achievements = getUnlockedAchievements();
        if (!achievements[achievementId]) {
            achievements[achievementId] = {
                unlockedAt: Date.now(),
                ...data
            };
            localStorage.setItem(STORAGE_KEY, JSON.stringify(achievements));

            // 同步到服务端数据库
            if (window.StarData) StarData.setAchievements(achievements);

            // 触发成就解锁事件
            const achievement = window.ACHIEVEMENTS?.find(a => a.id === achievementId);
            if (achievement) {
                showAchievementNotification(achievement);
                document.dispatchEvent(new CustomEvent('achievement-unlocked', {
                    detail: { achievement, data: achievements[achievementId] }
                }));
            }
            return true;
        }
        return false;
    }

    // 检查是否已解锁
    function isUnlocked(achievementId) {
        const achievements = getUnlockedAchievements();
        return !!achievements[achievementId];
    }

    // 获取成就解锁时间
    function getUnlockTime(achievementId) {
        const achievements = getUnlockedAchievements();
        return achievements[achievementId]?.unlockedAt || null;
    }

    // 显示成就解锁通知
    function showAchievementNotification(achievement) {
        if (window.starlearnNotifications?.showNotification) {
            window.starlearnNotifications.showNotification({
                title: '🏆 成就解锁！',
                content: `${achievement.name} - ${achievement.desc}`,
                actionLabel: '查看详情',
                actionUrl: '/html/stellar-showcase.html',
                type: 'achievement'
            });
        }
    }

    // 检查并解锁成就
    function checkAndUnlock(conditionType, value, extraData = {}) {
        if (!window.ACHIEVEMENTS) return [];

        const unlocked = [];
        window.ACHIEVEMENTS.forEach(achievement => {
            if (isUnlocked(achievement.id)) return;

            const cond = achievement.condition;
            if (cond.type !== conditionType) return;

            let shouldUnlock = false;

            switch (conditionType) {
                case 'study_count':
                case 'study_minutes':
                case 'streak_days':
                case 'algo_count':
                case 'algo_streak':
                case 'algo_perfect_hard':
                case 'algo_all_medium':
                case 'daily_goal_complete':
                case 'early_study_streak':
                case 'pet_feed':
                case 'pet_play':
                case 'pet_intimacy':
                case 'pet_unlock':
                case 'plant_count':
                case 'harvest_count':
                case 'game_play':
                case 'game_high_score':
                case 'game_max_combo':
                case 'code_lines':
                case 'knowledge_mastery':
                case 'legendary_badges':
                    shouldUnlock = value >= cond.value;
                    break;
                case 'course_complete':
                    shouldUnlock = extraData.course === cond.course;
                    break;
                case 'course_all':
                case 'explore_all':
                case 'plant_all_types':
                case 'all_badges':
                    shouldUnlock = value >= 1;
                    break;
                case 'pet_adopt':
                    shouldUnlock = value >= 1;
                    break;
            }

            if (shouldUnlock) {
                saveAchievement(achievement.id, extraData);
                unlocked.push(achievement);
            }
        });

        return unlocked;
    }

    // 更新统计并检查成就
    function updateStats(stats) {
        Object.entries(stats).forEach(([key, value]) => {
            const storageKey = `starlearn_stats_${key}`;
            let current = parseInt(localStorage.getItem(storageKey) || '0');

            if (typeof value === 'object' && value.set !== undefined) {
                current = value.set;
            } else {
                current = Math.max(current, value);
            }

            localStorage.setItem(storageKey, current.toString());

            // 检查成就
            checkAndUnlock(key, current);
        });
    }

    // 同步所有统计到服务端
    function syncStatsToServer() {
        if (!window.StarData) return;
        const stats = {};
        // 收集所有 starlearn_stats_* 键值
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && key.startsWith('starlearn_stats_')) {
                const statName = key.replace('starlearn_stats_', '');
                stats[statName] = parseInt(localStorage.getItem(key) || '0');
            }
        }
        StarData.setStats(stats);
    }

    // 增加统计
    function incrementStat(key, amount = 1) {
        const storageKey = `starlearn_stats_${key}`;
        const current = parseInt(localStorage.getItem(storageKey) || '0');
        const newValue = current + amount;
        localStorage.setItem(storageKey, newValue.toString());
        checkAndUnlock(key, newValue);
        // 延迟同步到服务端（避免频繁保存）
        if (window.StarData) {
            StarData.incrementStat(key, amount);
        }
        return newValue;
    }

    // 获取统计
    function getStat(key) {
        return parseInt(localStorage.getItem(`starlearn_stats_${key}`) || '0');
    }

    // 获取进度
    function getProgress(achievementId) {
        const achievement = window.ACHIEVEMENTS?.find(a => a.id === achievementId);
        if (!achievement) return { current: 0, target: 0, percent: 0 };

        const current = getStat(achievement.condition.type);
        const target = achievement.condition.value;
        return {
            current,
            target,
            percent: Math.min(100, Math.round((current / target) * 100))
        };
    }

    // 获取已解锁数量
    function getUnlockedCount() {
        const achievements = getUnlockedAchievements();
        return Object.keys(achievements).length;
    }

    // 获取总数量
    function getTotalCount() {
        return window.ACHIEVEMENTS?.length || 0;
    }

    // 导出API
    window.AchievementManager = {
        getUnlockedAchievements,
        saveAchievement,
        isUnlocked,
        getUnlockTime,
        checkAndUnlock,
        updateStats,
        incrementStat,
        getStat,
        getProgress,
        getUnlockedCount,
        getTotalCount
    };
})();
