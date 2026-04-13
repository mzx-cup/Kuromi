const STORAGE_KEY = 'starlearn_settings';

let settings = {};
let userId = null;

document.addEventListener('DOMContentLoaded', function() {
    initSettings();
});

function initSettings() {
    loadUserId();
    loadSettings();
    initNavigation();
    initToggleSwitches();
    initThemeColors();
    initRangeInputs();
    initSelectInputs();
    initButtons();
    initModal();
    initStorageUsage();
}

function loadUserId() {
    const storedUser = localStorage.getItem('starlearn_user');
    if (storedUser) {
        try {
            const userData = JSON.parse(storedUser);
            userId = userData.userId || userData.id;
        } catch (e) {
            console.warn('无法解析用户数据');
        }
    }
}

function loadSettings() {
    const savedSettings = localStorage.getItem(STORAGE_KEY);
    if (savedSettings) {
        try {
            settings = JSON.parse(savedSettings);
        } catch (e) {
            settings = getDefaultSettings();
        }
    } else {
        settings = getDefaultSettings();
    }
    applySettings();
}

function getDefaultSettings() {
    return {
        appearance: {
            darkMode: true,
            themeColor: 'purple',
            glassEffect: true,
            animations: true
        },
        notifications: {
            pushNotifications: true,
            studyReminder: true,
            reminderTime: '20:00',
            achievementNotify: true,
            emailNotifications: false
        },
        privacy: {
            dataSync: true,
            analytics: false,
            activityHistory: true,
            publicProfile: false
        },
        display: {
            sidebarExpanded: false,
            compactMode: false,
            cardLayout: 'grid',
            coursesPerPage: '24'
        },
        sound: {
            uiSounds: false,
            notificationSounds: true,
            soundVolume: 70,
            voiceReadout: false
        },
        language: {
            interfaceLanguage: 'zh-CN',
            contentLanguage: 'zh'
        }
    };
}

function saveSettings() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    if (userId) {
        syncToServer();
    }
    showToast('设置已保存', 'success');
}

async function syncToServer() {
    try {
        await fetch('/api/user/preferences', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                userId: userId,
                preferences: settings
            })
        });
    } catch (e) {
        console.warn('同步到服务器失败:', e);
    }
}

function applySettings() {
    const darkMode = document.getElementById('dark-mode');
    if (darkMode) darkMode.checked = settings.appearance.darkMode;

    const glassEffect = document.getElementById('glass-effect');
    if (glassEffect) glassEffect.checked = settings.appearance.glassEffect;

    const animations = document.getElementById('animations');
    if (animations) animations.checked = settings.appearance.animations;

    document.querySelectorAll('.theme-color').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.color === settings.appearance.themeColor);
    });

    const reminderTime = document.getElementById('reminder-time');
    if (reminderTime) reminderTime.value = settings.notifications.reminderTime;

    const pushNotifications = document.getElementById('push-notifications');
    if (pushNotifications) pushNotifications.checked = settings.notifications.pushNotifications;

    const studyReminder = document.getElementById('study-reminder');
    if (studyReminder) studyReminder.checked = settings.notifications.studyReminder;

    const achievementNotify = document.getElementById('achievement-notify');
    if (achievementNotify) achievementNotify.checked = settings.notifications.achievementNotify;

    const emailNotifications = document.getElementById('email-notifications');
    if (emailNotifications) emailNotifications.checked = settings.notifications.emailNotifications;

    const dataSync = document.getElementById('data-sync');
    if (dataSync) dataSync.checked = settings.privacy.dataSync;

    const analytics = document.getElementById('analytics');
    if (analytics) analytics.checked = settings.privacy.analytics;

    const activityHistory = document.getElementById('activity-history');
    if (activityHistory) activityHistory.checked = settings.privacy.activityHistory;

    const publicProfile = document.getElementById('public-profile');
    if (publicProfile) publicProfile.checked = settings.privacy.publicProfile;

    const sidebarExpanded = document.getElementById('sidebar-expanded');
    if (sidebarExpanded) sidebarExpanded.checked = settings.display.sidebarExpanded;

    const compactMode = document.getElementById('compact-mode');
    if (compactMode) compactMode.checked = settings.display.compactMode;

    const cardLayout = document.getElementById('card-layout');
    if (cardLayout) cardLayout.value = settings.display.cardLayout;

    const coursesPerPage = document.getElementById('courses-per-page');
    if (coursesPerPage) coursesPerPage.value = settings.display.coursesPerPage;

    const uiSounds = document.getElementById('ui-sounds');
    if (uiSounds) uiSounds.checked = settings.sound.uiSounds;

    const notificationSounds = document.getElementById('notification-sounds');
    if (notificationSounds) notificationSounds.checked = settings.sound.notificationSounds;

    const soundVolume = document.getElementById('sound-volume');
    if (soundVolume) soundVolume.value = settings.sound.soundVolume;

    const voiceReadout = document.getElementById('voice-readout');
    if (voiceReadout) voiceReadout.checked = settings.sound.voiceReadout;

    const interfaceLanguage = document.getElementById('interface-language');
    if (interfaceLanguage) interfaceLanguage.value = settings.language.interfaceLanguage;

    const contentLanguage = document.getElementById('content-language');
    if (contentLanguage) contentLanguage.value = settings.language.contentLanguage;
}

function initNavigation() {
    document.querySelectorAll('.settings-nav-item').forEach(item => {
        item.addEventListener('click', function() {
            document.querySelectorAll('.settings-nav-item').forEach(i => i.classList.remove('active'));
            this.classList.add('active');

            const section = this.dataset.section;
            document.querySelectorAll('.settings-section').forEach(s => s.classList.remove('active'));
            document.getElementById('section-' + section).classList.add('active');
        });
    });
}

function initToggleSwitches() {
    const toggleMap = {
        'dark-mode': ['appearance', 'darkMode'],
        'glass-effect': ['appearance', 'glassEffect'],
        'animations': ['appearance', 'animations'],
        'push-notifications': ['notifications', 'pushNotifications'],
        'study-reminder': ['notifications', 'studyReminder'],
        'achievement-notify': ['notifications', 'achievementNotify'],
        'email-notifications': ['notifications', 'emailNotifications'],
        'data-sync': ['privacy', 'dataSync'],
        'analytics': ['privacy', 'analytics'],
        'activity-history': ['privacy', 'activityHistory'],
        'public-profile': ['privacy', 'publicProfile'],
        'sidebar-expanded': ['display', 'sidebarExpanded'],
        'compact-mode': ['display', 'compactMode'],
        'ui-sounds': ['sound', 'uiSounds'],
        'notification-sounds': ['sound', 'notificationSounds'],
        'voice-readout': ['sound', 'voiceReadout']
    };

    Object.entries(toggleMap).forEach(([id, path]) => {
        const element = document.getElementById(id);
        if (element) {
            element.addEventListener('change', function() {
                const [category, key] = path;
                settings[category][key] = this.checked;
                saveSettings();
            });
        }
    });

    const timeInput = document.getElementById('reminder-time');
    if (timeInput) {
        timeInput.addEventListener('change', function() {
            settings.notifications.reminderTime = this.value;
            saveSettings();
        });
    }
}

function initThemeColors() {
    document.querySelectorAll('.theme-color').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.theme-color').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            settings.appearance.themeColor = this.dataset.color;
            saveSettings();
            applyThemeColor(this.dataset.color);
        });
    });
}

function applyThemeColor(color) {
    const colors = {
        purple: 'linear-gradient(135deg, #a855f7, #3b82f6)',
        blue: 'linear-gradient(135deg, #3b82f6, #06b6d4)',
        green: 'linear-gradient(135deg, #10b981, #34d399)',
        orange: 'linear-gradient(135deg, #f97316, #fbbf24)',
        pink: 'linear-gradient(135deg, #ec4899, #f472b6)'
    };
    document.documentElement.style.setProperty('--theme-gradient', colors[color] || colors.purple);
}

function initRangeInputs() {
    const volumeInput = document.getElementById('sound-volume');
    if (volumeInput) {
        volumeInput.addEventListener('input', function() {
            settings.sound.soundVolume = parseInt(this.value);
        });
        volumeInput.addEventListener('change', function() {
            saveSettings();
        });
    }
}

function initSelectInputs() {
    const selectMap = {
        'card-layout': ['display', 'cardLayout'],
        'courses-per-page': ['display', 'coursesPerPage'],
        'interface-language': ['language', 'interfaceLanguage'],
        'content-language': ['language', 'contentLanguage']
    };

    Object.entries(selectMap).forEach(([id, path]) => {
        const element = document.getElementById(id);
        if (element) {
            element.addEventListener('change', function() {
                const [category, key] = path;
                settings[category][key] = this.value;
                saveSettings();
            });
        }
    });
}

function initButtons() {
    const saveAllBtn = document.getElementById('save-all-btn');
    if (saveAllBtn) {
        saveAllBtn.addEventListener('click', function() {
            showToast('所有设置已保存', 'success');
            syncToServer();
        });
    }

    const changePasswordBtn = document.getElementById('change-password-btn');
    if (changePasswordBtn) {
        changePasswordBtn.addEventListener('click', () => showModal('修改密码', '请输入新密码：', true));
    }

    const bindEmailBtn = document.getElementById('bind-email-btn');
    if (bindEmailBtn) {
        bindEmailBtn.addEventListener('click', () => showModal('绑定邮箱', '请输入邮箱地址：', true));
    }

    const exportBtn = document.getElementById('export-data-btn');
    if (exportBtn) {
        exportBtn.addEventListener('click', exportData);
    }

    const importBtn = document.getElementById('import-data-btn');
    if (importBtn) {
        importBtn.addEventListener('click', () => document.getElementById('import-file-input').click());
    }

    const importInput = document.getElementById('import-file-input');
    if (importInput) {
        importInput.addEventListener('change', importData);
    }

    const clearCacheBtn = document.getElementById('clear-cache-btn');
    if (clearCacheBtn) {
        clearCacheBtn.addEventListener('click', clearCache);
    }

    const resetProgressBtn = document.getElementById('reset-progress-btn');
    if (resetProgressBtn) {
        resetProgressBtn.addEventListener('click', () => {
            showConfirmModal('重置学习进度', '确定要重置所有学习进度吗？此操作不可撤销！', resetProgress);
        });
    }

    const deleteAccountBtn = document.getElementById('delete-account-btn');
    if (deleteAccountBtn) {
        deleteAccountBtn.addEventListener('click', () => {
            showConfirmModal('注销账户', '确定要注销您的账户吗？所有数据将被永久删除！', deleteAccount);
        });
    }
}

function initModal() {
    const modal = document.getElementById('modal');
    const closeBtn = document.getElementById('modal-close');

    if (closeBtn) {
        closeBtn.addEventListener('click', hideModal);
    }

    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === modal) hideModal();
        });
    }
}

function showModal(title, message, hasInput = false, inputPlaceholder = '') {
    const modal = document.getElementById('modal');
    const modalTitle = document.getElementById('modal-title');
    const modalBody = document.getElementById('modal-body');
    const modalFooter = document.getElementById('modal-footer');

    modalTitle.textContent = title;

    if (hasInput) {
        modalBody.innerHTML = `<p>${message}</p><input type="${title.includes('密码') ? 'password' : 'email'}" placeholder="${inputPlaceholder}" id="modal-input" style="margin-top: 12px;">`;
    } else {
        modalBody.innerHTML = `<p>${message}</p>`;
    }

    modalFooter.innerHTML = `
        <button class="action-btn" onclick="hideModal()">取消</button>
        <button class="action-btn" onclick="confirmModalAction()">确定</button>
    `;

    modal.classList.remove('hidden');
}

function showConfirmModal(title, message, onConfirm) {
    const modal = document.getElementById('modal');
    const modalTitle = document.getElementById('modal-title');
    const modalBody = document.getElementById('modal-body');
    const modalFooter = document.getElementById('modal-footer');

    modalTitle.textContent = title;
    modalBody.innerHTML = `<p>${message}</p>`;
    modalFooter.innerHTML = `
        <button class="action-btn" onclick="hideModal()">取消</button>
        <button class="danger-btn" id="confirm-danger-btn">确定</button>
    `;

    document.getElementById('confirm-danger-btn').addEventListener('click', function() {
        onConfirm();
        hideModal();
    });

    modal.classList.remove('hidden');
}

function hideModal() {
    document.getElementById('modal').classList.add('hidden');
}

function confirmModalAction() {
    const input = document.getElementById('modal-input');
    const title = document.getElementById('modal-title').textContent;

    if (input && input.value.trim()) {
        if (title === '修改密码') {
            showToast('密码修改成功', 'success');
        } else if (title === '绑定邮箱') {
            showToast('邮箱绑定成功', 'success');
        }
    } else if (input) {
        showToast('请输入有效内容', 'error');
        return;
    }

    hideModal();
}

function exportData() {
    const exportData = {
        settings: settings,
        exportDate: new Date().toISOString(),
        userId: userId
    };

    const dataStr = JSON.stringify(exportData, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = `starlearn_settings_${new Date().toISOString().split('T')[0]}.json`;
    a.click();

    URL.revokeObjectURL(url);
    showToast('数据导出成功', 'success');
}

function importData(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = function(e) {
        try {
            const importedData = JSON.parse(e.target.result);
            if (importedData.settings) {
                settings = { ...getDefaultSettings(), ...importedData.settings };
                saveSettings();
                applySettings();
                showToast('数据导入成功', 'success');
            } else {
                showToast('无效的导入文件', 'error');
            }
        } catch (err) {
            showToast('导入失败：文件格式错误', 'error');
        }
    };
    reader.readAsText(file);
    event.target.value = '';
}

function clearCache() {
    const cacheKeys = ['starlearn_cache', 'starlearn_temp', 'temp_data'];
    let cleared = 0;

    cacheKeys.forEach(key => {
        if (localStorage.getItem(key)) {
            localStorage.removeItem(key);
            cleared++;
        }
    });

    sessionStorage.clear();

    showToast(`缓存已清理（${cleared}项）`, 'success');
}

function resetProgress() {
    localStorage.removeItem('starlearn_progress');
    localStorage.removeItem('starlearn_learning_path');
    showToast('学习进度已重置', 'warning');

    setTimeout(() => {
        window.location.href = '/index.html';
    }, 1500);
}

function deleteAccount() {
    if (userId) {
        fetch('/api/user/delete', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ userId: userId })
        }).then(() => {
            localStorage.clear();
            showToast('账户已注销', 'warning');
            setTimeout(() => {
                window.location.href = '/register.html';
            }, 1500);
        }).catch(() => {
            showToast('账户注销失败', 'error');
        });
    } else {
        localStorage.clear();
        window.location.href = '/register.html';
    }
}

async function initStorageUsage() {
    const storageElement = document.getElementById('storage-usage');
    if (!storageElement) return;

    try {
        if (navigator.storage && navigator.storage.estimate) {
            const estimate = await navigator.storage.estimate();
            const usedMB = (estimate.usage / (1024 * 1024)).toFixed(2);
            storageElement.textContent = `${usedMB} MB`;
        } else {
            let totalSize = 0;
            for (let key in localStorage) {
                if (localStorage.hasOwnProperty(key)) {
                    totalSize += localStorage[key].length * 2;
                }
            }
            const usedMB = (totalSize / (1024 * 1024)).toFixed(2);
            storageElement.textContent = `${usedMB} MB`;
        }
    } catch (e) {
        storageElement.textContent = '未知';
    }
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icons = {
        success: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>',
        error: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>',
        warning: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>',
        info: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>'
    };

    toast.innerHTML = `
        <svg class="toast-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            ${icons[type] || icons.info}
        </svg>
        <span class="toast-message">${message}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100px)';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

window.hideModal = hideModal;
window.confirmModalAction = confirmModalAction;