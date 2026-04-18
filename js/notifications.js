(function(){
    // Lightweight notification system with iOS-like liquid glass style and drag-to-mark-read
    const containerId = 'sl-notifications';

    function getContainer() {
        let container = document.getElementById(containerId);
        if (!container) {
            container = document.createElement('div');
            container.id = containerId;
            container.style.cssText = 'position: fixed; top: 16px; right: 16px; width: 360px; max-width: calc(100vw - 32px); z-index: 2000; display:flex; flex-direction:column; gap:12px; pointer-events: none;';
            if (document.body) {
                document.body.appendChild(container);
            } else {
                document.addEventListener('DOMContentLoaded', () => document.body.appendChild(container));
            }
        }
        return container;
    }

    function makeNotif(payload) {
        const { title = '', content = '', actionLabel = '', actionUrl = '', type = 'system' } = payload || {};
        const el = document.createElement('div');
        el.className = 'sl-notif';
        el.style.pointerEvents = 'auto';
        el.style.willChange = 'transform, opacity';
        el.innerHTML = `
            <button class="sl-close" aria-label="close">✕</button>
            <div class="sl-left">${type === 'achievement' ? '🌾' : '🔔'}</div>
            <div class="sl-body">
                <div class="sl-title">${escapeHtml(title)}</div>
                <div class="sl-content">${escapeHtml(content)}</div>
            </div>
            ${actionLabel ? `<button class="sl-action">${escapeHtml(actionLabel)}</button>` : ''}
        `;

        // Interaction: close button
        const closeBtn = el.querySelector('.sl-close');
        closeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            dismiss(el, true);
        });

        // Action button
        const actionBtn = el.querySelector('.sl-action');
        if (actionBtn) {
            actionBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                if (actionUrl) window.open(actionUrl, '_blank');
                dismiss(el, true);
            });
        }

        // Drag-to-right-to-mark-read
        let startX = 0, curX = 0, dragging = false;
        const threshold = 100;
        function onPointerDown(e) {
            dragging = true;
            startX = e.clientX || (e.touches && e.touches[0] && e.touches[0].clientX) || 0;
            el.style.transition = 'none';
            document.addEventListener('pointermove', onPointerMove);
            document.addEventListener('pointerup', onPointerUp);
            document.addEventListener('pointercancel', onPointerUp);
        }
        function onPointerMove(e) {
            if (!dragging) return;
            curX = (e.clientX || (e.touches && e.touches[0] && e.touches[0].clientX) || 0) - startX;
            if (curX < 0) curX = 0;
            el.style.transform = `translateX(${curX}px)`;
            el.style.opacity = `${Math.max(0.25, 1 - curX / 300)}`;
        }
        function onPointerUp(e) {
            dragging = false;
            document.removeEventListener('pointermove', onPointerMove);
            document.removeEventListener('pointerup', onPointerUp);
            document.removeEventListener('pointercancel', onPointerUp);
            el.style.transition = 'transform 0.35s cubic-bezier(.22,1,.36,1), opacity 0.25s ease';
            if (curX > threshold) {
                // mark read & dismiss
                el.style.transform = `translateX(120%)`;
                el.style.opacity = '0';
                setTimeout(() => dismiss(el, true), 300);
            } else {
                el.style.transform = '';
                el.style.opacity = '1';
            }
            startX = curX = 0;
        }
        el.addEventListener('pointerdown', onPointerDown);

        // Auto-dismiss
        const auto = setTimeout(() => dismiss(el, false), 12000);
        el._autoTimer = auto;

        // initial animation
        el.style.opacity = '0';
        el.style.transform = 'translateY(-8px)';
        setTimeout(() => {
            el.style.transition = 'transform 0.45s cubic-bezier(.22,1,.36,1), opacity 0.25s ease';
            el.style.opacity = '1';
            el.style.transform = '';
        }, 20);

        return el;
    }

    function dismiss(el, manually) {
        if (!el) return;
        if (el._autoTimer) clearTimeout(el._autoTimer);
        el.style.transition = 'transform 0.35s ease, opacity 0.25s ease';
        el.style.transform = 'translateX(30px) scale(0.98)';
        el.style.opacity = '0';
        setTimeout(() => { try { el.remove(); } catch(e){} }, 320);
    }

    function escapeHtml(str) {
        if (!str && str !== 0) return '';
        return String(str).replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":"&#39;"})[c]);
    }

    function showNotification(payload) {
        try {
            const node = makeNotif(payload);
            const container = getContainer();
            container.insertBefore(node, container.firstChild);
        } catch (e) { console.warn('showNotification error', e); }
    }

    // Listen for seed awards via storage events (other tabs)
    window.addEventListener('storage', (e) => {
        if (!e.key) return;
        if (e.key === 'starlearn_seeds') {
            const newCount = parseInt(e.newValue || '0');
            showNotification({
                title: '🎁 获得种子',
                content: `完成专注，获得了 1 个种子（当前：${newCount}）`,
                actionLabel: '前往林场',
                actionUrl: '/html/plant.html',
                type: 'achievement'
            });
        }
    });

    // Expose API
    window.starlearnNotifications = { showNotification };
})();
