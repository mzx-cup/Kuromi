// ============================================
// 星识通知系统 - macOS 风格通知
// ============================================
(function() {
    const CONTAINER_ID = 'sl-notifications';

    // macOS 风格颜色
    const STYLES = `
        @keyframes sl-slide-in {
            from { transform: translateX(110%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        @keyframes sl-slide-out {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(110%); opacity: 0; }
        }
        @keyframes sl-progress {
            from { width: 100%; }
            to { width: 0%; }
        }
        @keyframes sl-icon-bounce {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.15); }
        }

        #sl-notifications {
            position: fixed;
            top: 16px;
            right: 16px;
            width: 360px;
            max-width: calc(100vw - 32px);
            z-index: 99999;
            display: flex;
            flex-direction: column;
            gap: 10px;
            pointer-events: none;
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'PingFang SC', sans-serif;
        }

        .sl-notif {
            pointer-events: auto;
            position: relative;
            background: rgba(30, 30, 30, 0.85);
            backdrop-filter: blur(20px) saturate(180%);
            -webkit-backdrop-filter: blur(20px) saturate(180%);
            border: 0.5px solid rgba(255, 255, 255, 0.15);
            border-radius: 14px;
            padding: 14px 16px;
            display: flex;
            align-items: flex-start;
            gap: 12px;
            box-shadow:
                0 4px 24px rgba(0, 0, 0, 0.4),
                0 0 0 0.5px rgba(255, 255, 255, 0.05) inset,
                0 1px 0 rgba(255, 255, 255, 0.1) inset;
            overflow: hidden;
            cursor: default;
            animation: sl-slide-in 0.6s cubic-bezier(.22,1,.36,1) forwards;
        }

        .sl-notif.exiting {
            animation: sl-slide-out 0.5s cubic-bezier(.22,1,.36,1) forwards;
        }

        /* 进度条 */
        .sl-notif::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            height: 2.5px;
            background: rgba(255, 255, 255, 0.25);
            border-radius: 0 0 14px 14px;
            animation: sl-progress 12s linear forwards;
            width: 100%;
        }

        .sl-notif:hover::after {
            animation-play-state: paused;
        }

        /* 关闭按钮 */
        .sl-close {
            position: absolute;
            top: 8px;
            right: 8px;
            width: 20px;
            height: 20px;
            border: none;
            background: rgba(255, 255, 255, 0.08);
            border-radius: 50%;
            color: rgba(255, 255, 255, 0.5);
            font-size: 9px;
            line-height: 20px;
            text-align: center;
            cursor: pointer;
            transition: all 0.15s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }
        .sl-close:hover {
            background: rgba(255, 255, 255, 0.15);
            color: rgba(255, 255, 255, 0.9);
        }

        /* 左侧图标 */
        .sl-icon {
            width: 36px;
            height: 36px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
            flex-shrink: 0;
            animation: sl-icon-bounce 0.5s ease 0.2s;
        }

        .sl-icon.achievement {
            background: linear-gradient(135deg, rgba(251,191,36,0.3), rgba(245,158,11,0.2));
            border: 0.5px solid rgba(251,191,36,0.4);
        }
        .sl-icon.seed {
            background: linear-gradient(135deg, rgba(34,197,94,0.3), rgba(16,185,129,0.2));
            border: 0.5px solid rgba(34,197,94,0.4);
        }
        .sl-icon.system {
            background: linear-gradient(135deg, rgba(99,102,241,0.3), rgba(79,70,229,0.2));
            border: 0.5px solid rgba(99,102,241,0.4);
        }
        .sl-icon.reminder {
            background: linear-gradient(135deg, rgba(59,130,246,0.3), rgba(37,99,235,0.2));
            border: 0.5px solid rgba(59,130,246,0.4);
        }

        /* 右侧内容 */
        .sl-body {
            flex: 1;
            min-width: 0;
            padding-right: 20px;
        }

        .sl-title {
            font-size: 13px;
            font-weight: 600;
            color: #ffffff;
            margin-bottom: 3px;
            letter-spacing: -0.01em;
        }

        .sl-content {
            font-size: 12px;
            color: rgba(255, 255, 255, 0.65);
            line-height: 1.45;
            letter-spacing: -0.005em;
        }

        /* 操作按钮 */
        .sl-action {
            margin-top: 8px;
            padding: 4px 10px;
            background: rgba(255, 255, 255, 0.1);
            border: 0.5px solid rgba(255, 255, 255, 0.15);
            border-radius: 6px;
            color: rgba(255, 255, 255, 0.8);
            font-size: 11px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.15s ease;
            letter-spacing: -0.01em;
            pointer-events: auto;
        }
        .sl-action:hover {
            background: rgba(255, 255, 255, 0.18);
            color: #ffffff;
            border-color: rgba(255, 255, 255, 0.25);
        }
    `;

    // 注入样式
    function injectStyles() {
        if (document.getElementById('sl-notif-styles')) return;
        const style = document.createElement('style');
        style.id = 'sl-notif-styles';
        style.textContent = STYLES;
        document.head.appendChild(style);
    }

    function getContainer() {
        let container = document.getElementById(CONTAINER_ID);
        if (!container) {
            container = document.createElement('div');
            container.id = CONTAINER_ID;
            document.body.appendChild(container);
        }
        return container;
    }

    const ICONS = {
        achievement: '🏆',
        seed: '🌱',
        system: '🔔',
        reminder: '⏰'
    };

    function makeNotif(payload) {
        const { title = '', content = '', actionLabel = '', actionUrl = '', type = 'system' } = payload || {};
        const icon = ICONS[type] || ICONS.system;
        const iconClass = type === 'seed' ? 'seed' : type === 'achievement' ? 'achievement' : type === 'reminder' ? 'reminder' : 'system';

        const el = document.createElement('div');
        el.className = 'sl-notif';
        el.innerHTML = `
            <button class="sl-close" aria-label="关闭">✕</button>
            <div class="sl-icon ${iconClass}">${icon}</div>
            <div class="sl-body">
                <div class="sl-title">${escapeHtml(title)}</div>
                <div class="sl-content">${escapeHtml(content)}</div>
                ${actionLabel ? `<button class="sl-action">${escapeHtml(actionLabel)}</button>` : ''}
            </div>
        `;

        // 关闭
        el.querySelector('.sl-close').addEventListener('click', (e) => {
            e.stopPropagation();
            dismiss(el);
        });

        // 操作按钮
        const actionBtn = el.querySelector('.sl-action');
        if (actionBtn) {
            actionBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                if (actionUrl) window.location.href = actionUrl;
                dismiss(el);
            });
        }

        // 暂停进度条 hover
        el.addEventListener('mouseenter', () => el.style.setProperty('--paused', 'paused'));
        el.addEventListener('mouseleave', () => el.style.setProperty('--paused', 'running'));

        return el;
    }

    function dismiss(el) {
        if (el.classList.contains('exiting')) return;
        el.classList.add('exiting');
        setTimeout(() => { try { el.remove(); } catch(e){} }, 350);
    }

    function escapeHtml(str) {
        if (!str && str !== 0) return '';
        return String(str).replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":"&#39;"})[c]);
    }

    function showNotification(payload) {
        try {
            injectStyles();
            const node = makeNotif(payload);
            const container = getContainer();
            container.insertBefore(node, container.firstChild);

            // 12秒后自动消失
            setTimeout(() => dismiss(node), 12000);
        } catch (e) { console.warn('showNotification error', e); }
    }

    // 跨标签页通知（种子奖励）
    window.addEventListener('storage', (e) => {
        if (!e.key) return;
        if (e.key === 'starlearn_seeds') {
            const newCount = parseInt(e.newValue || '0');
            injectStyles();
            showNotification({
                title: '🌱 获得种子',
                content: `完成专注，获得 1 颗种子（当前：${newCount}）`,
                actionLabel: '前往林场',
                actionUrl: '/html/plant.html',
                type: 'seed'
            });
        }
    });

    // 暴露 API
    window.starlearnNotifications = { showNotification };
})();
