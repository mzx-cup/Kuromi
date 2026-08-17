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
    initTokenEditor();
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

// ============================================================
//   Token Editor — live theme primitive manipulation
// ============================================================
function initTokenEditor() {
    var tokenEditor = document.getElementById('token-editor');
    if (!tokenEditor) return;

    // ---- Element references ----
    var brandColorPicker = document.getElementById('brand-color-picker');
    var brandChroma      = document.getElementById('brand-chroma');
    var brandLightness    = document.getElementById('brand-lightness');
    var neutralLightness  = document.getElementById('neutral-lightness');
    var surfacePageL      = document.getElementById('surface-page-l');
    var surfaceCardL      = document.getElementById('surface-card-l');
    var shadowStrength    = document.getElementById('shadow-strength');
    var themeNameInput    = document.getElementById('custom-theme-name');
    var modeLight         = document.getElementById('mode-light');
    var modeDark          = document.getElementById('mode-dark');
    var saveBtn           = document.getElementById('save-custom-theme-btn');
    var resetBtn          = document.getElementById('reset-token-editor-btn');

    var brandChromaValEl     = document.getElementById('brand-chroma-val');
    var brandLightnessValEl  = document.getElementById('brand-lightness-val');
    var neutralLightnessValEl = document.getElementById('neutral-lightness-val');
    var surfacePageLValEl    = document.getElementById('surface-page-l-val');
    var surfaceCardLValEl    = document.getElementById('surface-card-l-val');
    var shadowStrengthValEl  = document.getElementById('shadow-strength-val');

    var accentAmber  = document.getElementById('accent-amber');
    var accentRose   = document.getElementById('accent-rose');
    var accentTeal   = document.getElementById('accent-teal');
    var accentViolet = document.getElementById('accent-violet');

    var neutralWarm  = document.getElementById('neutral-warm');
    var neutralCool  = document.getElementById('neutral-cool');
    var neutralPure  = document.getElementById('neutral-pure');
    var neutralBtns  = [neutralWarm, neutralCool, neutralPure].filter(Boolean);

    // ---- State ----
    var currentPrimitives = {};

    // ---- Color helpers (same approximate oklch↔hex as theme.js) ----
    function hexToApproxOklch(hex) {
        var r = parseInt(hex.slice(1,3), 16) / 255;
        var g = parseInt(hex.slice(3,5), 16) / 255;
        var b = parseInt(hex.slice(5,7), 16) / 255;
        var max = Math.max(r,g,b), min = Math.min(r,g,b);
        var L = Math.round((max + min) / 2 * 100);
        var delta = max - min;
        var H = 0, S = 0;
        if (delta !== 0) {
            S = delta / (1 - Math.abs(2 * L/100 - 1));
            if (max === r) H = ((g - b) / delta) % 6;
            else if (max === g) H = (b - r) / delta + 2;
            else H = (r - g) / delta + 4;
            H = Math.round(H * 60);
            if (H < 0) H += 360;
        }
        var C = Math.min(Math.round(S * 35) / 100, 0.32);
        return { h: H, c: C, l: L };
    }

    function oklchToApproxHex(h, c, l) {
        var s = Math.round(c / 0.32 * 100);
        var lNorm = l / 100;
        var hNorm = h / 360;
        var q = lNorm < 0.5 ? lNorm * (1 + s/100) : lNorm + s/100 - lNorm * s/100;
        var p = 2 * lNorm - q;
        var r = Math.round(hue2rgb(p, q, hNorm + 1/3) * 255);
        var g = Math.round(hue2rgb(p, q, hNorm) * 255);
        var b = Math.round(hue2rgb(p, q, hNorm - 1/3) * 255);
        return '#' + [r,g,b].map(function(v) {
            var hex = Math.max(0, Math.min(255, v)).toString(16);
            return hex.length === 1 ? '0' + hex : hex;
        }).join('');
    }

    function hue2rgb(p, q, t) {
        if (t < 0) t += 1;
        if (t > 1) t -= 1;
        if (t < 1/6) return p + (q - p) * 6 * t;
        if (t < 1/2) return q;
        if (t < 2/3) return p + (q - p) * (2/3 - t) * 6;
        return p;
    }

    // ---- Read a CSS primitive from :root ----
    function readPrimitive(name, fallback) {
        var val = getComputedStyle(document.documentElement).getPropertyValue('--' + name).trim();
        if (!val) return fallback;
        // Some values end with % — strip it for numeric parsing
        if (val.slice(-1) === '%') val = val.slice(0, -1);
        var n = parseFloat(val);
        return isNaN(n) ? fallback : n;
    }

    // ---- Write primitives to documentElement.style ----
    function setPrimitive(name, value) {
        document.documentElement.style.setProperty('--' + name, value);
    }

    function clearPrimitive(name) {
        document.documentElement.style.removeProperty('--' + name);
    }

    // ---- Update UI controls from currentPrimitives ----
    function syncControlsToState() {
        // Brand
        if (brandColorPicker) {
            brandColorPicker.value = oklchToApproxHex(
                currentPrimitives._brandH || 42,
                currentPrimitives._brandC || 0.18,
                currentPrimitives._brandL || 62
            );
        }
        if (brandChroma)      brandChroma.value      = currentPrimitives._brandC   !== undefined ? currentPrimitives._brandC   : 0.18;
        if (brandLightness)   brandLightness.value   = currentPrimitives._brandL   !== undefined ? currentPrimitives._brandL   : 62;

        // Neutral
        if (neutralLightness) neutralLightness.value = currentPrimitives._neutralL !== undefined ? currentPrimitives._neutralL : 48;
        highlightNeutralButton(currentPrimitives._neutralH, currentPrimitives._neutralC);

        // Surfaces
        if (surfacePageL)     surfacePageL.value     = currentPrimitives._surfacePageL !== undefined ? currentPrimitives._surfacePageL : 0.97;
        if (surfaceCardL)     surfaceCardL.value     = currentPrimitives._surfaceCardL !== undefined ? currentPrimitives._surfaceCardL : 1.00;
        if (shadowStrength)   shadowStrength.value   = currentPrimitives._shadowStrength  !== undefined ? currentPrimitives._shadowStrength  : 0.04;

        // Accent colors
        if (accentAmber)  accentAmber.value  = oklchToApproxHex(currentPrimitives._warningH||48, currentPrimitives._warningC||0.17, currentPrimitives._warningL||65);
        if (accentRose)   accentRose.value   = oklchToApproxHex(currentPrimitives._dangerH||15,  currentPrimitives._dangerC||0.22,  currentPrimitives._dangerL||52);
        if (accentTeal)   accentTeal.value   = oklchToApproxHex(currentPrimitives._successH||145, currentPrimitives._successC||0.16, currentPrimitives._successL||58);
        if (accentViolet) accentViolet.value = oklchToApproxHex(currentPrimitives._infoH||250,   currentPrimitives._infoC||0.15,    currentPrimitives._infoL||56);

        // Highlight active preset swatch
        highlightPresetSwatch(currentPrimitives._brandH, currentPrimitives._brandC, currentPrimitives._brandL);

        // Live value displays
        updateLiveValueDisplays();
    }

    function highlightPresetSwatch(brandH, brandC, brandL) {
        var swatches = document.querySelectorAll('.token-preset-swatch');
        swatches.forEach(function(sw) {
            var h = parseFloat(sw.getAttribute('data-brand-h'));
            var c = parseFloat(sw.getAttribute('data-brand-c'));
            var l = parseFloat(sw.getAttribute('data-brand-l'));
            var match = (Math.abs(h - (brandH||42)) < 0.5 && Math.abs(c - (brandC||0.18)) < 0.005 && l === (brandL||62));
            sw.classList.toggle('active', match);
        });
    }

    function highlightNeutralButton(nh, nc) {
        (neutralBtns).forEach(function(btn) {
            var h = parseFloat(btn.getAttribute('data-neutral-h'));
            var c = parseFloat(btn.getAttribute('data-neutral-c'));
            var match = (Math.abs(h - (nh||50)) < 0.5 && Math.abs(c - (nc||0.015)) < 0.005);
            btn.classList.toggle('active', match);
        });
    }

    // ---- Initialize from current theme ----
    function initFromCurrentTheme() {
        currentPrimitives = {};
        currentPrimitives._brandH   = readPrimitive('_brand-h', 42);
        currentPrimitives._brandC   = readPrimitive('_brand-c', 0.18);
        currentPrimitives._brandL   = readPrimitive('_brand-l', 62);
        currentPrimitives._neutralH = readPrimitive('_neutral-h', 50);
        currentPrimitives._neutralC = readPrimitive('_neutral-c', 0.015);
        currentPrimitives._neutralL = 48; // not a direct CSS primitive; default
        currentPrimitives._surfacePageL = 0.97;
        currentPrimitives._surfaceCardL = 1.00;
        currentPrimitives._shadowStrength = readPrimitive('_shadow-strength', 0.04);
        currentPrimitives._surfaceSaturation = readPrimitive('_surface-saturation', 0.02);

        // Semantic accent colors
        currentPrimitives._warningH = readPrimitive('_warning-h', 48);
        currentPrimitives._warningC = readPrimitive('_warning-c', 0.17);
        currentPrimitives._warningL = readPrimitive('_warning-l', 65);
        currentPrimitives._dangerH  = readPrimitive('_danger-h', 15);
        currentPrimitives._dangerC  = readPrimitive('_danger-c', 0.22);
        currentPrimitives._dangerL  = readPrimitive('_danger-l', 52);
        currentPrimitives._successH = readPrimitive('_success-h', 145);
        currentPrimitives._successC = readPrimitive('_success-c', 0.16);
        currentPrimitives._successL = readPrimitive('_success-l', 58);
        currentPrimitives._infoH    = readPrimitive('_info-h', 250);
        currentPrimitives._infoC    = readPrimitive('_info-c', 0.15);
        currentPrimitives._infoL    = readPrimitive('_info-l', 56);

        syncControlsToState();
    }

    // ---- Update live value displays ----
    function updateLiveValueDisplays() {
        if (brandChromaValEl)     brandChromaValEl.textContent     = (currentPrimitives._brandC   !== undefined ? currentPrimitives._brandC.toFixed(2)   : '0.18');
        if (brandLightnessValEl)  brandLightnessValEl.textContent  = (currentPrimitives._brandL   !== undefined ? currentPrimitives._brandL + '%'        : '62%');
        if (neutralLightnessValEl) neutralLightnessValEl.textContent = (currentPrimitives._neutralL !== undefined ? currentPrimitives._neutralL + '%'      : '48%');
        if (surfacePageLValEl)   surfacePageLValEl.textContent     = (currentPrimitives._surfacePageL !== undefined ? currentPrimitives._surfacePageL.toFixed(2) : '0.97');
        if (surfaceCardLValEl)   surfaceCardLValEl.textContent     = (currentPrimitives._surfaceCardL !== undefined ? currentPrimitives._surfaceCardL.toFixed(2) : '1.00');
        if (shadowStrengthValEl) shadowStrengthValEl.textContent   = (currentPrimitives._shadowStrength !== undefined ? currentPrimitives._shadowStrength.toFixed(2) : '0.04');
    }

    // ---- Push primitives to live CSS ----
    function applyLivePrimitives() {
        setPrimitive('_brand-h',   currentPrimitives._brandH);
        setPrimitive('_brand-c',   currentPrimitives._brandC);
        setPrimitive('_brand-l',   currentPrimitives._brandL + '%');
        setPrimitive('_neutral-h', currentPrimitives._neutralH);
        setPrimitive('_neutral-c', currentPrimitives._neutralC);
        setPrimitive('_shadow-strength', currentPrimitives._shadowStrength);
        setPrimitive('_surface-saturation', currentPrimitives._surfaceSaturation);
        // Semantic accent colors
        setPrimitive('_warning-h', currentPrimitives._warningH);
        setPrimitive('_warning-c', currentPrimitives._warningC);
        setPrimitive('_warning-l', currentPrimitives._warningL + '%');
        setPrimitive('_danger-h',  currentPrimitives._dangerH);
        setPrimitive('_danger-c',  currentPrimitives._dangerC);
        setPrimitive('_danger-l',  currentPrimitives._dangerL + '%');
        setPrimitive('_success-h', currentPrimitives._successH);
        setPrimitive('_success-c', currentPrimitives._successC);
        setPrimitive('_success-l', currentPrimitives._successL + '%');
        setPrimitive('_info-h',    currentPrimitives._infoH);
        setPrimitive('_info-c',    currentPrimitives._infoC);
        setPrimitive('_info-l',    currentPrimitives._infoL + '%');
        setPrimitive('_color-scheme', modeLight && modeLight.checked ? 'light' : 'dark');

        updateLiveValueDisplays();
    }

    function clearLivePrimitives() {
        var allKeys = [
            '_brand-h','_brand-c','_brand-l',
            '_neutral-h','_neutral-c',
            '_shadow-strength','_surface-saturation',
            '_warning-h','_warning-c','_warning-l',
            '_danger-h','_danger-c','_danger-l',
            '_success-h','_success-c','_success-l',
            '_info-h','_info-c','_info-l',
            '_color-scheme'
        ];
        allKeys.forEach(function(k) { clearPrimitive(k); });
    }

    // ---- Event: brand slider changes ----
    if (brandChroma) {
        brandChroma.addEventListener('input', function() {
            currentPrimitives._brandC = parseFloat(this.value);
            applyLivePrimitives();
            syncBrandPicker();
            highlightPresetSwatch(currentPrimitives._brandH, currentPrimitives._brandC, currentPrimitives._brandL);
        });
    }

    if (brandLightness) {
        brandLightness.addEventListener('input', function() {
            currentPrimitives._brandL = parseInt(this.value);
            applyLivePrimitives();
            syncBrandPicker();
            highlightPresetSwatch(currentPrimitives._brandH, currentPrimitives._brandC, currentPrimitives._brandL);
        });
    }

    function syncBrandPicker() {
        if (!brandColorPicker) return;
        brandColorPicker.value = oklchToApproxHex(
            currentPrimitives._brandH || 42,
            currentPrimitives._brandC || 0.18,
            currentPrimitives._brandL || 62
        );
    }

    // ---- Event: neutral lightness slider ----
    if (neutralLightness) {
        neutralLightness.addEventListener('input', function() {
            currentPrimitives._neutralL = parseInt(this.value);
            updateLiveValueDisplays();
        });
    }

    // ---- Event: surface / shadow sliders ----
    if (surfacePageL) {
        surfacePageL.addEventListener('input', function() {
            currentPrimitives._surfacePageL = parseFloat(this.value);
            updateLiveValueDisplays();
        });
    }
    if (surfaceCardL) {
        surfaceCardL.addEventListener('input', function() {
            currentPrimitives._surfaceCardL = parseFloat(this.value);
            updateLiveValueDisplays();
        });
    }
    if (shadowStrength) {
        shadowStrength.addEventListener('input', function() {
            currentPrimitives._shadowStrength = parseFloat(this.value);
            applyLivePrimitives();
        });
    }

    // ---- Event: brand color picker ----
    if (brandColorPicker) {
        brandColorPicker.addEventListener('input', function() {
            var approx = hexToApproxOklch(this.value);
            currentPrimitives._brandH = approx.h;
            currentPrimitives._brandC = approx.c;
            currentPrimitives._brandL = approx.l;

            if (brandChroma)    brandChroma.value    = approx.c;
            if (brandLightness) brandLightness.value = approx.l;

            applyLivePrimitives();
            updateLiveValueDisplays();
            highlightPresetSwatch(approx.h, approx.c, approx.l);
        });
    }

    // ---- Event: preset swatches ----
    var presetSwatches = document.querySelectorAll('.token-preset-swatch');
    presetSwatches.forEach(function(swatch) {
        swatch.addEventListener('click', function() {
            var h = parseFloat(this.getAttribute('data-brand-h'));
            var c = parseFloat(this.getAttribute('data-brand-c'));
            var l = parseInt(this.getAttribute('data-brand-l'));

            currentPrimitives._brandH = h;
            currentPrimitives._brandC = c;
            currentPrimitives._brandL = l;

            if (brandChroma)    brandChroma.value    = c;
            if (brandLightness) brandLightness.value = l;
            if (brandColorPicker) brandColorPicker.value = oklchToApproxHex(h, c, l);

            applyLivePrimitives();
            highlightPresetSwatch(h, c, l);
            updateLiveValueDisplays();
        });
    });

    // ---- Event: neutral tone buttons ----
    neutralBtns.forEach(function(btn) {
        btn.addEventListener('click', function() {
            var h = parseFloat(this.getAttribute('data-neutral-h'));
            var c = parseFloat(this.getAttribute('data-neutral-c'));

            currentPrimitives._neutralH = h;
            currentPrimitives._neutralC = c;

            applyLivePrimitives();
            highlightNeutralButton(h, c);
        });
    });

    // ---- Event: accent color pickers ----
    function bindAccent(accentEl, hKey, cKey, lKey) {
        if (!accentEl) return;
        accentEl.addEventListener('input', function() {
            var approx = hexToApproxOklch(this.value);
            currentPrimitives[hKey] = approx.h;
            currentPrimitives[cKey] = approx.c;
            currentPrimitives[lKey] = approx.l;
            applyLivePrimitives();
        });
    }

    bindAccent(accentAmber,  '_warningH', '_warningC', '_warningL');
    bindAccent(accentRose,   '_dangerH',  '_dangerC',  '_dangerL');
    bindAccent(accentTeal,   '_successH', '_successC', '_successL');
    bindAccent(accentViolet, '_infoH',    '_infoC',    '_infoL');

    // ---- Event: save ----
    if (saveBtn) {
        saveBtn.addEventListener('click', function() {
            var name = (themeNameInput && themeNameInput.value.trim()) ? themeNameInput.value.trim() : '自定义主题';
            var mode = (modeDark && modeDark.checked) ? 'dark' : 'light';

            // Build primitives object matching PRIMITIVE_KEYS format
            var primitives = {};
            primitives['_brand-h']   = currentPrimitives._brandH;
            primitives['_brand-c']   = currentPrimitives._brandC;
            primitives['_brand-l']   = currentPrimitives._brandL + '%';
            primitives['_neutral-h'] = currentPrimitives._neutralH;
            primitives['_neutral-c'] = currentPrimitives._neutralC;
            primitives['_shadow-strength'] = currentPrimitives._shadowStrength;
            primitives['_surface-saturation'] = currentPrimitives._surfaceSaturation;
            primitives['_color-scheme'] = mode === 'dark' ? 'dark' : 'light';

            // Semantic colors
            primitives['_warning-h'] = currentPrimitives._warningH;
            primitives['_warning-c'] = currentPrimitives._warningC;
            primitives['_warning-l'] = currentPrimitives._warningL + '%';
            primitives['_danger-h']  = currentPrimitives._dangerH;
            primitives['_danger-c']  = currentPrimitives._dangerC;
            primitives['_danger-l']  = currentPrimitives._dangerL + '%';
            primitives['_success-h'] = currentPrimitives._successH;
            primitives['_success-c'] = currentPrimitives._successC;
            primitives['_success-l'] = currentPrimitives._successL + '%';
            primitives['_info-h']    = currentPrimitives._infoH;
            primitives['_info-c']    = currentPrimitives._infoC;
            primitives['_info-l']    = currentPrimitives._infoL + '%';

            // Check for duplicate names
            var existingCustom = (window.StarTheme && window.StarTheme.getCustomThemes) ? window.StarTheme.getCustomThemes() : [];
            for (var i = 0; i < existingCustom.length; i++) {
                if (existingCustom[i].name === name) {
                    showToast('主题名称 "' + name + '" 已存在，请更换名称', 'error');
                    return;
                }
            }

            if (!window.StarTheme || !window.StarTheme.createCustomTheme) {
                showToast('主题系统未就绪，请刷新页面后重试', 'error');
                return;
            }

            var newId = window.StarTheme.createCustomTheme(name, mode, primitives);
            showToast('自定义主题 "' + name + '" 已保存并应用', 'success');
            window.StarTheme.setTheme(newId);

            // Update the current state with the new theme info
            currentPrimitives._colorScheme = mode;
        });
    }

    // ---- Event: reset ----
    if (resetBtn) {
        resetBtn.addEventListener('click', function() {
            clearLivePrimitives();
            if (window.StarTheme && window.StarTheme.applyAll) {
                window.StarTheme.applyAll();
            }
            initFromCurrentTheme();
            showToast('Token 编辑器已重置为当前预设主题默认值', 'info');
        });
    }

    // ---- Mode radios ----
    if (modeLight) {
        modeLight.addEventListener('change', function() {
            if (this.checked) {
                setPrimitive('_color-scheme', 'light');
                currentPrimitives._colorScheme = 'light';
            }
        });
    }
    if (modeDark) {
        modeDark.addEventListener('change', function() {
            if (this.checked) {
                setPrimitive('_color-scheme', 'dark');
                currentPrimitives._colorScheme = 'dark';
            }
        });
    }

    // ---- Contrast display (bonus) ----
    updateContrastDisplay();
    // Re-check contrast when primitives change
    var origApply = applyLivePrimitives;
    applyLivePrimitives = function() {
        origApply();
        updateContrastDisplay();
    };

    function updateContrastDisplay() {
        var contrastEl = document.getElementById('token-contrast-ratio');
        if (!contrastEl) return;

        var textLum, cardLum;
        // Approximate: read computed color of text-body and surface-card
        try {
            var textColor = getComputedStyle(document.documentElement).getPropertyValue('--text-body').trim();
            var cardColor = getComputedStyle(document.documentElement).getPropertyValue('--surface-card').trim();

            // Quick luminance estimate from hex or css color
            textLum = estimateLuminance(textColor);
            cardLum = estimateLuminance(cardColor);
        } catch(e) {
            textLum = 0.1; cardLum = 0.08;
        }

        var lighter = Math.max(textLum, cardLum);
        var darker   = Math.min(textLum, cardLum);
        var ratio = (lighter + 0.05) / (darker + 0.05);
        var ratioRounded = ratio.toFixed(1);

        var cls = 'good';
        if (ratio < 3) cls = 'bad';
        else if (ratio < 4.5) cls = 'warn';

        contrastEl.textContent = '对比度: ' + ratioRounded + ':1';
        contrastEl.style.color = cls === 'good' ? '#10b981' : (cls === 'warn' ? '#f59e0b' : '#ef4444');
    }

    function estimateLuminance(colorStr) {
        if (!colorStr) return 0.5;
        // Try to extract from rgb() or oklch() or hex
        var r = 128, g = 128, b = 128;

        var rgbMatch = colorStr.match(/rgb\(\s*(\d+)\s*[,\s]\s*(\d+)\s*[,\s]\s*(\d+)/);
        if (rgbMatch) {
            r = parseInt(rgbMatch[1]); g = parseInt(rgbMatch[2]); b = parseInt(rgbMatch[3]);
        } else {
            var hexMatch = colorStr.match(/#([0-9a-fA-F]{2})([0-9a-fA-F]{2})([0-9a-fA-F]{2})/);
            if (hexMatch) {
                r = parseInt(hexMatch[1], 16); g = parseInt(hexMatch[2], 16); b = parseInt(hexMatch[3], 16);
            }
        }

        // sRGB to relative luminance
        var rs = r/255, gs = g/255, bs = b/255;
        var rLin = rs <= 0.03928 ? rs/12.92 : Math.pow((rs+0.055)/1.055, 2.4);
        var gLin = gs <= 0.03928 ? gs/12.92 : Math.pow((gs+0.055)/1.055, 2.4);
        var bLin = bs <= 0.03928 ? bs/12.92 : Math.pow((bs+0.055)/1.055, 2.4);
        return 0.2126 * rLin + 0.7152 * gLin + 0.0722 * bLin;
    }

    // ---- Kickoff ----
    initFromCurrentTheme();
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