/**
 * SmartLinkRenderer - 智能链接渲染组件
 * 统一处理站内/站外链接，自动选择最佳渲染形式
 */

class SmartLinkRenderer {
    constructor() {
        this.trustedDomains = [
            'github.com', 'leetcode.cn', 'leetcode.com',
            'docs.python.org', 'developer.mozilla.org',
            'www.bilibili.com', 'bilibili.com', 'zhihu.com',
            'www.zhihu.com', 'juejin.cn', 'csdn.net',
            'stackoverflow.com', 'www.w3schools.com',
            'www.runoob.com', 'www.liaoxuefeng.com',
            'www.python.org', 'go.dev', 'kotlinlang.org',
            'docs.oracle.com', 'learn.microsoft.com',
            'cloud.tencent.com', 'developer.aliyun.com',
            'www.kaggle.com', 'huggingface.co',
            'pytorch.org', 'tensorflow.org',
            'openai.com', 'platform.openai.com'
        ];
    }

    /**
     * 主入口：根据链接数据和上下文，自动选择最佳渲染方式
     */
    render(links, context = {}) {
        if (!links || links.length === 0) return null;

        const container = document.createElement('div');
        container.className = 'smart-links-container';

        if (links.length === 1) {
            container.appendChild(this._renderRichCard(links[0], context));
        } else if (links.every(l => l.type === 'internal')) {
            container.appendChild(this._renderCardGrid(links, context));
        } else if (links.every(l => l.type === 'external')) {
            container.appendChild(this._renderExternalBar(links, context));
        } else {
            container.appendChild(this._renderMixedLayout(links, context));
        }

        return container;
    }

    /**
     * 渲染链接到消息气泡中（替换 [[link:...]] 标记）
     */
    renderInMessage(content) {
        if (!content) return content;

        // 解析 [[link:...]] 标记
        return content.replace(/\[\[link:(\w+)\]\]/g, (match, linkId) => {
            return `<span data-smart-link="${linkId}"></span>`;
        });
    }

    /**
     * 为消息中的占位符注入实际链接
     */
    injectLinksIntoMessage(messageEl, links) {
        if (!messageEl || !links) return;

        const placeholders = messageEl.querySelectorAll('[data-smart-link]');
        placeholders.forEach(ph => {
            const linkId = ph.getAttribute('data-smart-link');
            const link = links.find(l => l.id === linkId);
            if (link) {
                const rendered = this._renderInlineLink(link);
                ph.replaceWith(rendered);
            }
        });

        // 同时渲染消息底部的链接区域
        const linksContainer = messageEl.querySelector('.message-links');
        if (linksContainer) {
            linksContainer.innerHTML = '';
            const rendered = this.render(links);
            if (rendered) {
                linksContainer.appendChild(rendered);
            }
        }
    }

    // ============ 丰富渲染形式 ============

    /** 富媒体卡片 - 单条链接的主打形式 */
    _renderRichCard(link, context) {
        const card = document.createElement('div');
        card.className = `link-card link-card--${link.type}`;

        // 封面/图标区域
        const media = document.createElement('div');
        media.className = 'link-card__media';
        if (link.thumbnail) {
            media.innerHTML = `<img src="${this._escapeHtml(link.thumbnail)}" loading="lazy" alt="${this._escapeHtml(link.title)}">`;
        } else {
            const emoji = link.icon || (link.type === 'internal' ? '📚' : '🔗');
            media.innerHTML = `<span class="link-card__emoji">${emoji}</span>`;
        }

        // 内容区域
        const body = document.createElement('div');
        body.className = 'link-card__body';

        let progressHtml = '';
        if (link.metadata?.progress !== undefined) {
            const pct = Math.min(100, Math.max(0, link.metadata.progress));
            progressHtml = `<div class="link-card__progress"><div class="link-card__progress-bar" style="width:${pct}%"></div><span class="link-card__progress-text">${pct}%</span></div>`;
        }

        let sourceHtml = '';
        if (link.type === 'external') {
            const source = link.metadata?.source || new URL(link.url).hostname.replace(/^www\./, '');
            const trusted = this._isTrustedDomain(link.url);
            sourceHtml = `<span class="link-card__source ${trusted ? 'link-card__source--trusted' : ''}">${trusted ? '✓ ' : '🌐 '}${this._escapeHtml(source)}${trusted ? ' · 可信来源' : ''}</span>`;
        }

        body.innerHTML = `
            <h4 class="link-card__title">${this._escapeHtml(link.title)}</h4>
            ${link.description ? `<p class="link-card__desc">${this._escapeHtml(link.description)}</p>` : ''}
            ${sourceHtml}
            ${progressHtml}
        `;

        // 点击处理
        card.addEventListener('click', (e) => this._handleClick(e, link));

        // 悬停效果由 CSS 处理
        card.appendChild(media);
        card.appendChild(body);
        return card;
    }

    /** 紧凑卡片 - 用于网格布局 */
    _renderCompactCard(link, context) {
        const card = document.createElement('div');
        card.className = `link-card link-card--compact link-card--${link.type}`;

        const emoji = link.icon || (link.type === 'internal' ? '📚' : '🔗');
        card.innerHTML = `
            <div class="link-card__compact-icon">${emoji}</div>
            <div class="link-card__compact-body">
                <h5 class="link-card__compact-title">${this._escapeHtml(link.title)}</h5>
                ${link.description ? `<p class="link-card__compact-desc">${this._escapeHtml(link.description)}</p>` : ''}
            </div>
            <div class="link-card__compact-arrow">→</div>
        `;

        card.addEventListener('click', (e) => this._handleClick(e, link));
        return card;
    }

    /** 卡片网格 - 多条站内链接 */
    _renderCardGrid(links, context) {
        const grid = document.createElement('div');
        grid.className = 'link-grid';
        links.forEach(link => {
            grid.appendChild(this._renderCompactCard(link, context));
        });
        return grid;
    }

    /** 外部链接条 - 多条站外链接 */
    _renderExternalBar(links, context) {
        const bar = document.createElement('div');
        bar.className = 'link-external-bar';

        const label = document.createElement('div');
        label.className = 'link-external-label';
        label.textContent = '🔗 相关学习资源';
        bar.appendChild(label);

        const pills = document.createElement('div');
        pills.className = 'link-pills';

        links.forEach(link => {
            const btn = document.createElement('a');
            btn.className = 'link-pill';
            btn.href = link.url;
            btn.target = '_blank';
            btn.rel = 'noopener noreferrer';
            const icon = link.icon || '🔗';
            btn.innerHTML = `<span class="link-pill__icon">${icon}</span><span class="link-pill__text">${this._escapeHtml(link.title)}</span>`;

            // 安全提示
            if (!this._isTrustedDomain(link.url)) {
                btn.classList.add('link-pill--untrusted');
                btn.addEventListener('click', (e) => {
                    e.preventDefault();
                    this._confirmExternalNavigation(link.url);
                });
            }

            pills.appendChild(btn);
        });

        bar.appendChild(pills);
        return bar;
    }

    /** 混合布局 - 站内+站外 */
    _renderMixedLayout(links, context) {
        const wrapper = document.createElement('div');
        wrapper.className = 'link-mixed-layout';

        const internal = links.filter(l => l.type === 'internal');
        const external = links.filter(l => l.type === 'external');

        if (internal.length > 0) {
            const internalSection = document.createElement('div');
            internalSection.className = 'link-section link-section--internal';
            const internalLabel = document.createElement('div');
            internalLabel.className = 'link-section__label';
            internalLabel.textContent = '📚 站内学习';
            internalSection.appendChild(internalLabel);

            if (internal.length === 1) {
                internalSection.appendChild(this._renderRichCard(internal[0], context));
            } else {
                internalSection.appendChild(this._renderCardGrid(internal, context));
            }
            wrapper.appendChild(internalSection);
        }

        if (external.length > 0) {
            const externalSection = document.createElement('div');
            externalSection.className = 'link-section link-section--external';
            const externalLabel = document.createElement('div');
            externalLabel.className = 'link-section__label';
            externalLabel.textContent = '🌐 外部资源';
            externalSection.appendChild(externalLabel);
            externalSection.appendChild(this._renderExternalBar(external, context));
            wrapper.appendChild(externalSection);
        }

        return wrapper;
    }

    /** 行内链接 - 嵌在句子中 */
    _renderInlineLink(link) {
        const a = document.createElement('a');
        a.className = `inline-link inline-link--${link.type}`;
        a.href = link.url;
        a.textContent = link.title;

        if (link.type === 'external') {
            a.target = '_blank';
            a.rel = 'noopener noreferrer';
            if (!this._isTrustedDomain(link.url)) {
                a.addEventListener('click', (e) => {
                    e.preventDefault();
                    this._confirmExternalNavigation(link.url);
                });
            }
        } else {
            a.addEventListener('click', (e) => {
                e.preventDefault();
                this._navigateInternal(link.url);
            });
        }

        return a;
    }

    /** 渲染快捷操作按钮 */
    renderActions(actions, links) {
        if (!actions || actions.length === 0) return null;

        const container = document.createElement('div');
        container.className = 'link-actions';

        // 特殊页面映射（用于模板中的简写 target）
        const specialPages = {
            'hub': '/hub.html',
            'progress': '/progress.html',
            'courses': '/courses.html',
            'plant': '/plant.html',
            'showcase': '/stellar-showcase.html',
            'settings': '/settings.html',
            'index': '/index.html'
        };

        actions.forEach(action => {
            const btn = document.createElement('button');
            btn.className = `link-action-btn link-action-btn--${action.action}`;
            btn.textContent = action.label;

            btn.addEventListener('click', () => {
                if (action.action === 'navigate' && action.target) {
                    // 先检查是否是 link id
                    const link = links && links.find(l => l.id === action.target);
                    if (link) {
                        this._navigate(link);
                        return;
                    }
                    // 再检查是否是特殊页面简写
                    const specialUrl = specialPages[action.target];
                    if (specialUrl) {
                        this._navigateInternal(specialUrl);
                        return;
                    }
                    // 否则当作直接 URL
                    if (action.target.startsWith('/')) {
                        this._navigateInternal(action.target);
                    }
                } else if (action.action === 'dismiss') {
                    const msgEl = container.closest('.msg-row');
                    if (msgEl) {
                        msgEl.style.transition = 'all 0.3s ease';
                        msgEl.style.opacity = '0';
                        msgEl.style.transform = 'translateX(-20px)';
                        setTimeout(() => msgEl.remove(), 300);
                    }
                    if (action.delay) {
                        const key = `dismissed_${action.target || Date.now()}`;
                        localStorage.setItem(key, String(Date.now()));
                    }
                }
            });

            container.appendChild(btn);
        });

        return container;
    }

    // ============ 跳转处理 ============

    _handleClick(event, link) {
        // 记录点击偏好
        this._recordClickPreference(link.style || 'card');

        if (link.type === 'external') {
            if (!this._isTrustedDomain(link.url)) {
                event.preventDefault();
                this._confirmExternalNavigation(link.url);
                return;
            }
            window.open(link.url, '_blank', 'noopener,noreferrer');
        } else {
            event.preventDefault();
            this._navigateInternal(link.url, link.metadata);
        }
    }

    _navigate(link) {
        if (link.type === 'external') {
            if (!this._isTrustedDomain(link.url)) {
                this._confirmExternalNavigation(link.url);
                return;
            }
            window.open(link.url, '_blank', 'noopener,noreferrer');
        } else {
            this._navigateInternal(link.url, link.metadata);
        }
    }

    _navigateInternal(url, metadata) {
        // 保存当前对话上下文
        try {
            sessionStorage.setItem('ai_context_snapshot', JSON.stringify({
                timestamp: Date.now(),
                agent_id: window.currentAgent?.id || 'default',
                last_topics: this._getRecentTopics(),
                scroll_position: document.getElementById('chat-container')?.scrollTop || 0
            }));
        } catch (e) {
            console.warn('[SmartLinkRenderer] Failed to save context:', e);
        }

        // 解析 URL
        const fullUrl = new URL(url, window.location.origin);

        // 附加元数据到 URL
        if (metadata) {
            Object.entries(metadata).forEach(([key, value]) => {
                if (value !== undefined && value !== null) {
                    fullUrl.searchParams.set(key, String(value));
                }
            });
        }

        // 平滑跳转动画
        document.body.style.transition = 'opacity 0.2s ease';
        document.body.style.opacity = '0';

        setTimeout(() => {
            window.location.href = fullUrl.toString();
        }, 200);
    }

    _confirmExternalNavigation(url) {
        let hostname;
        try {
            hostname = new URL(url).hostname;
        } catch {
            hostname = url;
        }

        const confirmed = confirm(
            `即将跳转至外部网站：${hostname}\n\n` +
            `⚠️ 安全提示：星识无法保证外部内容的安全性。\n` +
            `请谨慎访问不明来源的链接。\n\n` +
            `是否继续？`
        );

        if (confirmed) {
            window.open(url, '_blank', 'noopener,noreferrer');
        }
    }

    // ============ 工具方法 ============

    _isTrustedDomain(url) {
        try {
            const hostname = new URL(url).hostname.toLowerCase();
            return this.trustedDomains.some(t => {
                return hostname === t || hostname.endsWith('.' + t);
            });
        } catch {
            return false;
        }
    }

    _escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    _recordClickPreference(style) {
        try {
            const prefs = JSON.parse(localStorage.getItem('link_style_prefs') || '{}');
            prefs[style] = (prefs[style] || 0) + 1;
            localStorage.setItem('link_style_prefs', JSON.stringify(prefs));
        } catch (e) {
            // silent
        }
    }

    _getRecentTopics() {
        try {
            const messages = window.messages || [];
            return messages
                .filter(m => m.role === 'user')
                .slice(-3)
                .map(m => m.content?.substring(0, 50) || '');
        } catch {
            return [];
        }
    }
}

// 全局实例
window.smartLinkRenderer = new SmartLinkRenderer();
