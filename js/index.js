const API_BASE = window.location.origin;
const API_URL = `${API_BASE}/api/chat`;
const RUN_CODE_URL = `${API_BASE}/api/run-code`;
const GRADE_CODE_URL = `${API_BASE}/api/grade-code`;
const SAVE_PROGRESS_URL = `${API_BASE}/api/progress/save`;
const LOAD_PROGRESS_URL = `${API_BASE}/api/progress/load`;
const PROACTIVE_SSE_URL = `${API_BASE}/api/v2/proactive/stream`;
const STRUGGLE_EVENT_URL = `${API_BASE}/api/v2/event/struggle`;

const AGENTS_CONFIG = [
    {
        id: 'bigdata-architect',
        name: '大数据架构导师',
        icon: '🧙‍♂️',
        greeting: (userName) => `**${userName}同学，你好！** 我是你的专属大数据架构导师 🧙‍♂️。

根据你近期的学习轨迹，我已经为你生成了今日的专属学习计划：

📊 **当前进度**：正在深入学习 \`Hadoop HDFS底层原理\`。
🎯 **今日目标**：攻克 NameNode 核心机制与源码解析。
💡 **个性化提示**：我会为你提供大量企业级代码示例和分布式架构设计思路，帮你突破技术瓶颈！

\`\`\`
学习路径规划：
1. HDFS 读写流程详解
2. NameNode 与 DataNode 通信机制
3. Block 副本分布策略
4. 企业级 Hadoop 集群调优实战
\`\`\`

你可以随时向我提问，例如："*帮我梳理一下 HDFS 的读写流程*" 或 "*抛给我一道大厂关于 MapReduce 的面试题*"。

加油！跟着我，一步一步成为大数据专家！💪`,
        themeColor: '#3b82f6',
        systemPrompt: '你是一位资深大数据架构导师，名为"星识大牛"。你的专长是Hadoop生态（HDFS/MapReduce/YARN）、Spark、Flink、Kafka、Hive等技术的底层原理与架构设计。你需要用通俗语言解释复杂概念，结合源码级分析和企业级实践案例。当学生提问时，优先用启发式提问引导思考，而非直接给答案。'
    },
    {
        id: 'psychologist',
        name: '知心辅导员',
        icon: '💝',
        greeting: (userName) => `**${userName}同学，你好呀！** 💝 我是你的知心辅导员，很高兴在你需要的时候陪伴着你。

🌸 **今日情绪状态回顾**：
最近你在大数据课程的学习中表现出色！根据你的学习数据分析，你已经连续高效学习了 **3 天**，保持了这个好势头！

📈 **学习与心理小贴士**：
学习路上难免会遇到困难和疲惫，这是每个追求进步的人都会经历的。我看到你偶尔会在晚上 10 点后还在刷题，其实适当的休息同样重要哦～

💬 **你可以这样使用我**：
- 当你感到 **焦虑或迷茫** 时，和我聊聊，我会帮你梳理情绪
- 当你 **压力山大** 时，告诉我你的烦恼，我会给你放松技巧
- 当你 **学习受挫** 时，我们可以一起分析问题，找回信心

记住，你不是一个人在战斗！我会一直在这里支持你。🌈

*（温馨提示：如果你的情绪持续低落，请记得寻求专业心理咨询师的帮助）*`,
        themeColor: '#ec4899',
        systemPrompt: '你是一位温柔耐心的心理辅导员，名为"星灵"。你的职责是关注学生的心理健康和情绪状态。当学生感到焦虑、迷茫、压力大或情绪低落时，你要用温暖的话语给予安慰和鼓励。你可以运用积极心理学、认知行为疗法等专业知识帮助学生调整心态。但如果你发现学生有严重的心理困扰，请建议他们寻求专业的心理咨询帮助。记住，你的态度要真诚、友善、充满同理心。'
    },
    {
        id: 'interviewer',
        name: '资深面试官',
        icon: '👔',
        greeting: (userName) => `**${userName}同学，你好！** 👔 我是你的资深面试官，曾在 BAT、TMD 等大厂担任技术面试官多年。

🎯 **面试备战方案已生成**：

\`\`\`
📋 今日面试特训计划
━━━━━━━━━━━━━━━━━
🔴 Java基础：HashMap源码剖析
🟠 多线程：线程池与并发控制
🟡 框架：Spring Boot启动流程
🟢 项目：亿级数据处理架构设计
🔵 架构：分布式系统一致性方案
\`\`\`

📊 **你的面试竞争力分析**：
- 算法能力：★★★☆☆
- 项目经验：★★★☆☆
- 系统设计：★★☆☆☆
- 表达能力：★★★★☆

💡 **高频考点提醒**：
1. HashMap 的扩容机制与线程安全问题
2. MySQL 索引原理与优化
3. Redis 分布式锁实现
4. Kafka 消息丢失与重复消费

准备好接受挑战了吗？可以直接说"**开始面试**"或"**出一道算法题**"！`,
        themeColor: '#f59e0b',
        systemPrompt: '你是一位资深技术面试官，名为"面霸"。你有10年以上的大厂技术面试经验，涉及Java后端、算法、系统设计等多个领域。你的职责是帮助学生准备技术面试，包括模拟面试、简历优化、面试技巧传授等。你出的面试题要贴近真实大厂风格，难度适中偏难，同时给出评分标准和改进建议。保持严谨专业但不失亲和力的态度。'
    },
    {
        id: 'educator',
        name: '教育学大师',
        icon: '🎓',
        greeting: (userName) => `**${userName}同学，你好！** 🎓 我是教育学大师"智远"，专攻学习科学与认知心理学。

🧠 **你的专属学习策略**：

根据你的学习数据分析，我发现你属于 **视觉+实践型** 学习者！这意味着：

✨ **最适合你的学习方法**：
1. 📊 **费曼技巧**：用简单语言向他人讲解概念
2. 🎨 **视觉化记忆**：画思维导图整理知识体系
3. ⏰ **艾宾浩斯复习**：按照遗忘曲线科学复习
4. 🏃 **间隔重复**：每天固定时间回顾前一天内容

📅 **个性化复习计划**：

| 日期 | 复习内容 | 方式 |
|------|---------|------|
| 今天 | HDFS架构 | 思维导图 |
| 明天 | HDFS读写 | 向我讲解 |
| 3天后 | MapReduce | 实战编码 |
| 7天后 | 综合复习 | 默写框架 |

💡 **今日学习建议**：
在学习新知识前，先花 5 分钟回忆上次学习的内容，这能帮助你的大脑建立知识连接！

准备好了吗？告诉我你想学习的主题，我来帮你制定专属计划！`,
        themeColor: '#8b5cf6',
        systemPrompt: '你是一位博学的教育学大师，名为"智远"。你的专长是学习科学和教育心理学。你可以帮助学生了解自己的学习风格，优化学习策略，提高记忆效率，克服学习障碍。你要引导学生理解"学会学习"的重要性，传授元认知技巧。你还可以根据学生的认知风格和偏好，推荐个性化的学习方法和资源。回答要富有洞察力，能够启发学生对教育和学习的深层思考。'
    },
    {
        id: 'geek-senior',
        name: '极客学长',
        icon: '🧑‍💻',
        greeting: (userName) => `**${userName}同学，你好！** 🧑‍💻 我是你的极客学长，在 GitHub 上有 5000+ Stars 的开源项目经验，Bug 排查专家！

🚀 **实战项目推荐**：

\`\`\`javascript
// 适合你的项目清单
const projects = [
  { name: "手写迷你Hadoop", level: "⭐⭐⭐⭐", goal: "理解MR核心原理" },
  { name: "实时数据看板", level: "⭐⭐⭐⭐⭐", goal: "Flink + Kafka实战" },
  { name: "分布式缓存系统", level: "⭐⭐⭐⭐", goal: "Redis深度应用" },
  { name: "GitHub星标项目分析", level: "⭐⭐⭐", goal: "数据采集与可视化" }
];
\`\`\`

🔧 **开发环境检查**：
- JDK 版本：17+ ✅
- Maven/Gradle：已配置 ✅
- Docker：已安装 ✅
- IDE：IDEA ✅

🐛 **常见Bug急救箱**：

| 错误类型 | 解决方案 |
|---------|---------|
| SerializationException | 检查对象是否实现Serializable |
| OutOfMemoryError | 调整JVM堆内存 -Xmx4g |
| ConnectionRefused | 检查Hadoop服务是否启动 |
| ClassNotFoundException | 清理Maven缓存重新构建 |

💬 **你可以这样使用我**：
- 遇到 Bug 了？直接贴错误日志，我来帮你分析！
- 想做项目？告诉我你的技术栈，我给你推荐！
- 代码优化？把你的代码发给我，我帮你 review！

准备好开始实战了吗？🚀`,
        themeColor: '#10b981',
        systemPrompt: '你是一位经验丰富的极客学长，名为"极客"。你在GitHub上有丰富的开源项目经验，精通Java、Python、Go等多种语言，专长是项目实战和Bug诊断排查。你的职责是帮助学生提升实际编码能力，包括项目架构设计、代码优化、Bug排查解决等。你的风格是直接、高效、实战的，喜欢通过真实代码案例来讲解技术要点。'
    }
];

let currentAgent = AGENTS_CONFIG[0];

let agentMenuState = {
    isOpen: false,
    isAnimating: false,
    lockUntil: 0,
    wrapper: null,
    panel: null,
    button: null,
    fabList: null
};

function initAgentMenu() {
    agentMenuState.wrapper = document.getElementById('agent-menu-wrapper');
    agentMenuState.panel = document.getElementById('agent-fab-panel');
    agentMenuState.button = document.getElementById('agent-fab-btn');
    agentMenuState.fabList = document.getElementById('agent-fab-list');

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && agentMenuState.isOpen) {
            closeMenu();
        }
    });
}

function isMenuLocked() {
    return Date.now() < agentMenuState.lockUntil;
}

function lockMenu(durationMs) {
    agentMenuState.lockUntil = Date.now() + durationMs;
}

function openMenu() {
    if (agentMenuState.isAnimating) return;

    agentMenuState.isAnimating = true;
    agentMenuState.isOpen = true;
    agentMenuState.panel.classList.add('open');
    renderAgentFab();

    lockMenu(350);
    setTimeout(() => {
        agentMenuState.isAnimating = false;
    }, 350);
}

function closeMenu() {
    if (agentMenuState.isAnimating) {
        agentMenuState.isAnimating = false;
    }

    agentMenuState.panel.classList.remove('open');
    agentMenuState.isOpen = false;
    agentMenuState.isAnimating = false;
}

function handleMenuButtonClick(event) {
    event.stopPropagation();
    event.preventDefault();

    if (isMenuLocked()) return;

    if (agentMenuState.isOpen) {
        closeMenu();
    } else {
        openMenu();
    }
}

function handleGlobalClick(event) {
    if (!agentMenuState.isOpen) return;

    const path = event.composedPath ? event.composedPath() : [];
    const isClickInsidePanel = agentMenuState.panel && (path.includes(agentMenuState.panel) || (event.target && agentMenuState.panel.contains(event.target)));
    const isClickOnButton = agentMenuState.button && (path.includes(agentMenuState.button) || (event.target && agentMenuState.button.contains(event.target)));
    const isClickInsideWrapper = agentMenuState.wrapper && (path.includes(agentMenuState.wrapper) || (event.target && agentMenuState.wrapper.contains(event.target)));

    if (!isClickInsideWrapper) {
        closeMenu();
        return;
    }

    if (isClickInsidePanel && !isClickOnButton) {
        return;
    }
}

document.addEventListener('click', handleGlobalClick);

function switchAgent(agentId) {
    const agent = AGENTS_CONFIG.find(a => a.id === agentId);
    if (!agent) return;
    currentAgent = agent;
    const msgInput = document.getElementById('message-input') || document.getElementById('notion-input');
    if (msgInput) msgInput.value = '';
    const userName = currentUser?.name || currentUser?.nickname || '同学';
    const greetingText = typeof agent.greeting === 'function' ? agent.greeting(userName) : agent.greeting;
    messages = [{ role: 'assistant', content: greetingText }];
    renderMessages();
    renderAgentFab();
    closeMenu();
    localStorage.setItem('starlearn_agent', agentId);
}

function renderAgentFab() {
    const iconEl = document.getElementById('agent-fab-icon');
    const nameEl = document.getElementById('agent-fab-name');
    if (iconEl) iconEl.textContent = currentAgent.icon;
    if (nameEl) nameEl.textContent = currentAgent.name;
    const btnEl = document.getElementById('agent-fab-btn');
    if (btnEl) {
        btnEl.style.borderColor = currentAgent.themeColor;
        btnEl.style.boxShadow = `0 0 16px ${currentAgent.themeColor}50`;
    }
    const listEl = document.getElementById('agent-fab-list');
    if (listEl) {
        listEl.innerHTML = AGENTS_CONFIG.map(agent => `
            <button class="agent-fab-item ${agent.id === currentAgent.id ? 'active' : ''}"
                    onclick="switchAgent('${agent.id}')"
                    style="${agent.id === currentAgent.id ? `background: ${agent.themeColor}20; border-color: ${agent.themeColor};` : ''}">
                <span class="agent-fab-item-icon">${agent.icon}</span>
                <span class="agent-fab-item-name">${agent.name}</span>
            </button>
        `).join('');
    }
}

function toggleAgentPanel() {
    if (agentMenuState.isOpen) {
        closeMenu();
    } else {
        openMenu();
    }
}

document.addEventListener('DOMContentLoaded', initAgentMenu);

function getAgentSystemPrompt() {
    return currentAgent.systemPrompt;
}

class ProactiveTutorClient {
    constructor() {
        this.eventSource = null;
        this.studentId = '';
        this.courseId = 'bigdata';
        this.deviceId = 'web-' + Math.random().toString(36).substring(2, 8);
        this.lastMsgId = '';
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectDelay = 1000;
        this.connected = false;
        this._struggleTimer = null;
        this._idleSeconds = 0;
        this._errorCount = 0;
    }

    connect(studentId, courseId = 'bigdata') {
        if (this.eventSource) {
            this.disconnect();
        }
        this.studentId = studentId || 'anonymous';
        this.courseId = courseId;
        const params = new URLSearchParams({
            student_id: this.studentId,
            course_id: this.courseId,
            device_id: this.deviceId,
            last_msg_id: this.lastMsgId,
        });
        const url = `${PROACTIVE_SSE_URL}?${params.toString()}`;
        console.log('[ProactiveTutor] Connecting to', url);

        this.eventSource = new EventSource(url);

        this.eventSource.addEventListener('proactive', (event) => {
            this._handleProactiveMessage(event);
        });

        this.eventSource.addEventListener('open', () => {
            console.log('[ProactiveTutor] Connected');
            this.connected = true;
            this.reconnectAttempts = 0;
            this.reconnectDelay = 1000;
        });

        this.eventSource.addEventListener('error', (event) => {
            console.warn('[ProactiveTutor] Connection error');
            this.connected = false;
            this._scheduleReconnect();
        });

        this.eventSource.onmessage = (event) => {
            if (event.data && event.data.startsWith(':')) return;
        };

        this._startIdleTracking();
    }

    disconnect() {
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
        this.connected = false;
        this._stopIdleTracking();
        console.log('[ProactiveTutor] Disconnected');
    }

    _handleProactiveMessage(event) {
        try {
            const data = JSON.parse(event.data);
            const envelope = data.envelope || {};
            const payload = data.payload || {};

            if (envelope.msg_id) {
                this.lastMsgId = envelope.msg_id;
            }

            console.log('[ProactiveTutor] Received:', envelope.msg_type, payload.title);

            this._renderProactiveNotification(envelope, payload);

            if (envelope.msg_type === 'struggle_intervention') {
                this._errorCount = 0;
                this._idleSeconds = 0;
            }
        } catch (e) {
            console.warn('[ProactiveTutor] Parse error:', e);
        }
    }

    _renderProactiveNotification(envelope, payload) {
        const container = document.getElementById('proactive-notifications');
        if (!container) {
            this._createNotificationContainer();
        }
        const notifContainer = document.getElementById('proactive-notifications');

        const typeIcons = {
            greeting: '👋',
            struggle_intervention: '🆘',
            review_reminder: '📖',
            achievement: '🏆',
            tip: '💡',
            system: '🔔',
        };
        const typeColors = {
            greeting: 'var(--accent-bg)',
            struggle_intervention: 'var(--danger-bg)',
            review_reminder: 'var(--warning-bg)',
            achievement: 'var(--success-bg)',
            tip: 'var(--accent-bg)',
            system: 'var(--surface-glass)',
        };

        const icon = typeIcons[envelope.msg_type] || '🔔';
        const bgColor = typeColors[envelope.msg_type] || 'var(--surface-glass)';

        const notif = document.createElement('div');
        notif.className = 'proactive-notif fade-in-up';
        notif.style.cssText = `
            background: var(--surface-glass);
            backdrop-filter: blur(24px) saturate(150%);
            -webkit-backdrop-filter: blur(24px) saturate(150%);
            border: 1px solid var(--border-glass);
            border-radius: 16px;
            padding: 16px 20px;
            margin-bottom: 12px;
            box-shadow: var(--shadow-glass);
            will-change: transform;
            transform: translateZ(0);
            animation: slideUp 0.4s cubic-bezier(0.22,1,0.36,1) both;
        `;

        const actionBtn = payload.action_label
            ? `<button class="proactive-action-btn" onclick="window.proactiveTutor.handleAction('${envelope.msg_type}', ${JSON.stringify(payload.action_payload || {}).replace(/"/g, '&quot;')})" style="
                margin-top: 10px;
                padding: 8px 16px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: 600;
                cursor: pointer;
                border: none;
                background: linear-gradient(135deg, var(--accent), var(--accent-hover));
                color: var(--text-on-accent);
                box-shadow: 0 4px 12px var(--accent-bg);
                transition: all 0.25s;
            ">${payload.action_label}</button>`
            : '';

        notif.innerHTML = `
            <div style="display: flex; align-items: flex-start; gap: 12px;">
                <div style="width: 36px; height: 36px; border-radius: 12px; background: ${bgColor}; display: flex; align-items: center; justify-content: center; font-size: 18px; flex-shrink: 0;">${icon}</div>
                <div style="flex: 1; min-width: 0;">
                    <div style="font-size: 13px; font-weight: 700; color: var(--text-primary); margin-bottom: 4px;">${payload.title || ''}</div>
                    <div style="font-size: 12px; color: var(--text-secondary); line-height: 1.5;">${payload.content || ''}</div>
                    ${actionBtn}
                </div>
                <button onclick="this.closest('.proactive-notif').remove()" style="background: none; border: none; color: var(--text-tertiary); cursor: pointer; font-size: 16px; padding: 4px; line-height: 1;">✕</button>
            </div>
        `;

        notifContainer.appendChild(notif);

        setTimeout(() => {
            if (notif.parentNode) {
                notif.style.transition = 'all 0.3s ease';
                notif.style.opacity = '0';
                notif.style.transform = 'translateY(-10px)';
                setTimeout(() => notif.remove(), 300);
            }
        }, 15000);
    }

    _createNotificationContainer() {
        const container = document.createElement('div');
        container.id = 'proactive-notifications';
        container.style.cssText = `
            position: fixed;
            top: 16px;
            right: 16px;
            width: 360px;
            max-width: calc(100vw - 32px);
            z-index: 1000;
            pointer-events: none;
        `;
        container.querySelectorAll('.proactive-notif').forEach(el => el.style.pointerEvents = 'auto');
        document.body.appendChild(container);

        const style = document.createElement('style');
        style.textContent = `
            #proactive-notifications .proactive-notif { pointer-events: auto; }
            #proactive-notifications .proactive-action-btn:hover { transform: translateY(-1px); box-shadow: 0 6px 16px var(--accent-bg); }
            #proactive-notifications .proactive-action-btn:active { transform: scale(0.96); }
        `;
        document.head.appendChild(style);
    }

    handleAction(msgType, payload) {
        console.log('[ProactiveTutor] Action:', msgType, payload);
        if (msgType === 'greeting' || msgType === 'review_reminder') {
            if (payload.type === 'socratic_quick' || payload.type === 'review_session') {
                const notionInput = document.getElementById('notion-input');
                const msgInput = document.getElementById('message-input');
                const kp = payload.knowledge_point || '';
                if (notionInput) {
                    notionInput.innerText = `帮我复习一下${kp}`;
                    notionInput.focus();
                } else if (msgInput) {
                    msgInput.value = `帮我复习一下${kp}`;
                    msgInput.focus();
                }
            }
        } else if (msgType === 'struggle_intervention') {
            if (payload.type === 'socratic_hint') {
                const notionInput = document.getElementById('notion-input');
                const msgInput = document.getElementById('message-input');
                if (notionInput) {
                    notionInput.innerText = '我需要一些提示来理解这个概念';
                    notionInput.focus();
                } else if (msgInput) {
                    msgInput.value = '我需要一些提示来理解这个概念';
                    msgInput.focus();
                }
            }
        }
        const notifs = document.querySelectorAll('.proactive-notif');
        notifs.forEach(n => n.remove());
    }

    reportStruggle(contentId, metrics = {}) {
        if (!this.studentId || this.studentId === 'anonymous') return;
        fetch(STRUGGLE_EVENT_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: this.studentId,
                session_id: this.deviceId,
                current_content_id: contentId,
                struggle_metrics: metrics,
            }),
        }).catch(err => console.warn('[ProactiveTutor] Struggle report failed:', err));
    }

    _startIdleTracking() {
        this._stopIdleTracking();
        this._idleSeconds = 0;
        this._struggleTimer = setInterval(() => {
            this._idleSeconds++;
            if (this._idleSeconds >= 120 && this._idleSeconds % 120 === 0) {
                this.reportStruggle('idle_timeout', { idle_seconds: this._idleSeconds });
            }
        }, 1000);

        const resetIdle = () => { this._idleSeconds = 0; };
        document.addEventListener('mousemove', resetIdle);
        document.addEventListener('keydown', resetIdle);
        document.addEventListener('click', resetIdle);
        document.addEventListener('scroll', resetIdle);
        this._resetIdleHandler = resetIdle;
    }

    _stopIdleTracking() {
        if (this._struggleTimer) {
            clearInterval(this._struggleTimer);
            this._struggleTimer = null;
        }
        if (this._resetIdleHandler) {
            document.removeEventListener('mousemove', this._resetIdleHandler);
            document.removeEventListener('keydown', this._resetIdleHandler);
            document.removeEventListener('click', this._resetIdleHandler);
            document.removeEventListener('scroll', this._resetIdleHandler);
        }
    }

    _scheduleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('[ProactiveTutor] Max reconnect attempts reached');
            return;
        }
        this.reconnectAttempts++;
        const delay = Math.min(this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1), 30000);
        console.log(`[ProactiveTutor] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
        setTimeout(() => {
            this.connect(this.studentId, this.courseId);
        }, delay);
    }
}

window.proactiveTutor = new ProactiveTutorClient();

/** FastAPI 的 detail 可能是 string、对象或校验错误数组，直接拼进 Error 会变成 [object Object] */
function formatApiErrorDetail(detail) {
    if (detail == null || detail === '') return '';
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
        return detail.map((item) => {
            if (item && typeof item === 'object') {
                const loc = Array.isArray(item.loc) ? item.loc.filter(Boolean).join('.') : '';
                const msg = item.msg || item.message || JSON.stringify(item);
                return loc ? `${loc}: ${msg}` : msg;
            }
            return String(item);
        }).join('; ');
    }
    if (typeof detail === 'object') return JSON.stringify(detail);
    return String(detail);
}

const DEFAULT_LEARNING_PATH = [
    { topic: '大数据导论', status: 'current' },
    { topic: '分布式文件系统', status: 'locked' }
];

/** 接口与 localStorage 里 path 可能是 JSON 字符串、单对象或非标准字段名，统一为 { topic, status }[] */
function normalizeLearningPath(value) {
    if (value == null) return [...DEFAULT_LEARNING_PATH];
    if (typeof value === 'string') {
        try {
            return normalizeLearningPath(JSON.parse(value));
        } catch {
            return [...DEFAULT_LEARNING_PATH];
        }
    }
    if (Array.isArray(value)) {
        const mapped = value.map((item) => {
            if (!item || typeof item !== 'object') return { topic: '学习任务', status: 'locked' };
            const topic = item.topic ?? item.Topic ?? item.name ?? item.title ?? '学习任务';
            const status = item.status ?? item.Status ?? 'locked';
            const node = { topic: String(topic), status: String(status) };
            if (item.name) node.name = item.name;
            if (item.title) node.title = item.title;
            if (item.importance) node.importance = item.importance;
            if (item.estimated_time) node.estimated_time = item.estimated_time;
            if (item.estimatedMinutes) node.estimatedMinutes = item.estimatedMinutes;
            if (item.children) node.children = item.children;
            return node;
        });
        return mapped.length > 0 ? mapped : [...DEFAULT_LEARNING_PATH];
    }
    if (typeof value === 'object') {
        const topic = value.topic ?? value.Topic ?? value.name ?? value.title ?? '学习任务';
        const status = value.status ?? value.Status ?? 'current';
        return [{ topic: String(topic), status: String(status) }];
    }
    return [...DEFAULT_LEARNING_PATH];
}

function ensureCurrentPathValid() {
    currentPath = normalizeLearningPath(currentPath);
}

/** 后端曾保存原始 assessment（knowledgeBase 为 basic/zero 等枚举），需转成界面用的展示型画像 */
function isRawAssessmentProfile(p) {
    if (!p || typeof p !== 'object') return false;
    const levels = ['zero', 'basic', 'intermediate', 'advanced'];
    return typeof p.knowledgeBase === 'string' && levels.includes(p.knowledgeBase);
}

let currentUser = JSON.parse(localStorage.getItem('starlearn_user') || 'null') || {
    name: '同学',
    avatar: 'https://api.dicebear.com/7.x/adventurer/svg?seed=starlearn&backgroundColor=b6e3f4',
    currentTask: '大数据导论'
};

// 评估数据映射到画像显示
const assessmentToProfileMap = {
    knowledgeBase: {
        zero: '零基础入门',
        basic: '基础入门',
        intermediate: '进阶学习',
        advanced: '深入掌握'
    },
    codeSkill: {
        beginner: '编程新手',
        basic: '基础掌握',
        intermediate: '熟练编程',
        advanced: '编程高手'
    },
    learningGoal: {
        exam: '应对考试',
        career: '职业发展',
        project: '项目实战',
        interest: '兴趣探索',
        competition: '竞赛备战',
        research: '科研学术'
    },
    cognitiveStyle: {
        visual: '视觉型',
        textual: '文字型',
        pragmatic: '实践型'
    },
    focusLevel: {
        high: '高专注',
        medium: '中等专注',
        low: '需要引导'
    },
    learningDirection: {
        bigdata: '大数据技术',
        ai: '人工智能',
        frontend: '前端开发',
        backend: '后端开发',
        algorithm: '算法数据结构',
        database: '数据库技术'
    }
};

/** 将画像中的枚举键（含模型输出的英文标签）转为界面中文，避免卡片上出现 basic、exam 等裸键 */
function normalizeProfileDisplayFields(p) {
    if (!p || typeof p !== 'object') return;
    const kb = assessmentToProfileMap.knowledgeBase;
    const cs = assessmentToProfileMap.codeSkill;
    const lg = assessmentToProfileMap.learningGoal;
    const cog = assessmentToProfileMap.cognitiveStyle;
    const fl = assessmentToProfileMap.focusLevel;
    const dir = assessmentToProfileMap.learningDirection;
    if (p.knowledgeBase && kb[p.knowledgeBase]) p.knowledgeBase = kb[p.knowledgeBase];
    if (p.codeSkill && cs[p.codeSkill]) p.codeSkill = cs[p.codeSkill];
    if (p.learningGoal && lg[p.learningGoal]) p.learningGoal = lg[p.learningGoal];
    if (p.cognitiveStyle && cog[p.cognitiveStyle]) p.cognitiveStyle = cog[p.cognitiveStyle];
    if (p.focusLevel && fl[p.focusLevel]) p.focusLevel = fl[p.focusLevel];
    if (p.learningDirection && dir[p.learningDirection]) p.learningDirection = dir[p.learningDirection];
}

// 从评估数据初始化画像
function initProfileFromAssessment(assessment) {
    if (!assessment) return null;

    const profile = {
        knowledgeBase: assessmentToProfileMap.knowledgeBase[assessment.knowledgeBase] || '基础入门',
        codeSkill: assessmentToProfileMap.codeSkill[assessment.codeSkill] || '基础掌握',
        learningGoal: assessmentToProfileMap.learningGoal[assessment.learningGoal] || '学习提升',
        cognitiveStyle: assessmentToProfileMap.cognitiveStyle[assessment.cognitiveStyle] || '实践型',
        weakness: '暂无',
        focusLevel: assessmentToProfileMap.focusLevel[assessment.focusLevel] || '中等专注',
        learningDirection: assessmentToProfileMap.learningDirection[assessment.learningDirection] || '大数据技术',
        languages: assessment.languages || ['python']
    };

    return profile;
}

// ============================================
// 学习上下文接收与应用逻辑
// ============================================
function applyLearningContext() {
    try {
        const contextJson = localStorage.getItem('currentLearningContext');

        if (!contextJson) {
            console.log('[Context] 无学习上下文，继续使用默认设置');
            return;
        }

        const context = JSON.parse(contextJson);

        // 验证数据完整性和有效性
        const requiredFields = ['courseId', 'courseName', 'aiSystemPrompt', 'tutorPersona', 'timestamp'];
        const isValid = requiredFields.every(field => context[field] !== undefined && context[field] !== null);

        if (!isValid) {
            console.warn('[Context] 学习上下文数据不完整:', context);
            localStorage.removeItem('currentLearningContext');
            return;
        }

        // 检查是否过期
        if (context.expiresAt && Date.now() > context.expiresAt) {
            console.warn('[Context] 学习上下文已过期');
            localStorage.removeItem('currentLearningContext');
            return;
        }

        console.log('[Context] 应用学习上下文:', context.courseName);

        // A. 将 aiSystemPrompt 设置为当前 Agent 的系统提示词
        const contextPrompt = `[课程模式] ${context.aiSystemPrompt}`;
        if (typeof setAgentSystemPrompt === 'function') {
            setAgentSystemPrompt(contextPrompt);
        } else if (typeof updateAgentPrompt === 'function') {
            updateAgentPrompt(contextPrompt);
        } else {
            // 尝试直接修改 currentAgent
            if (window.currentAgent) {
                window.currentAgent.systemPrompt = contextPrompt;
                console.log('[Context] 已更新 Agent 系统提示词');
            }
        }

        // B. 根据 tutorPersona 更新导师头像及名称
        const tutor = context.tutorPersona;
        if (tutor && typeof tutor === 'object') {
            const tutorNameEl = document.getElementById('tutor-name');
            const tutorTitleEl = document.getElementById('tutor-title');

            if (tutorNameEl) {
                tutorNameEl.textContent = tutor.name || '导师';
                tutorNameEl.style.display = 'block';
            }
            if (tutorTitleEl) {
                tutorTitleEl.textContent = tutor.title || '';
                tutorTitleEl.style.display = 'block';
            }

            console.log('[Context] 已更新导师信息:', tutor.name, tutor.title);
        }

        // C. 加载关联的课程知识库
        if (context.knowledgeBase && Array.isArray(context.knowledgeBase)) {
            console.log('[Context] 加载知识库:', context.knowledgeBase);
            // 知识库加载逻辑由具体业务实现
            if (typeof loadCourseKnowledgeBase === 'function') {
                loadCourseKnowledgeBase(context.knowledgeBase);
            }
        }

        // D. 显示上下文应用提示
        showContextAppliedToast(context.courseName);

        // E. 清理 localStorage（可选，保留以便刷新时恢复）
        // localStorage.removeItem('currentLearningContext');

    } catch (error) {
        console.error('[Context] 应用学习上下文失败:', error);
        localStorage.removeItem('currentLearningContext');
    }
}

function showContextAppliedToast(courseName) {
    const toast = document.createElement('div');
    toast.className = 'fixed top-20 left-1/2 -translate-x-1/2 z-[9999] px-6 py-3 rounded-xl shadow-2xl backdrop-blur-xl bg-gradient-to-r from-purple-500/90 to-indigo-500/90 text-white font-medium transform -translate-y-4 opacity-0 transition-all duration-300';
    toast.innerHTML = `<span class="mr-2">📚</span>已切换到课程: <strong>${courseName}</strong>`;
    document.body.appendChild(toast);

    requestAnimationFrame(() => {
        toast.classList.remove('-translate-y-4', 'opacity-0');
    });

    setTimeout(() => {
        toast.classList.add('-translate-y-4', 'opacity-0');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// 根据评估数据生成个性化欢迎消息
function generateWelcomeMessage(assessment, profile) {
    if (!assessment) {
        return '同学你好，我是 **V4.0 十大智能体协同伴学系统**。\n\n我具备以下核心能力：\n- **6维动态画像**：自动构建你的学情状态机\n- **认知风格路由**：视觉型多画图，实践型多推代码\n- **苏格拉底诊断**：说"我不懂"时，我会引导你自主思考\n- **引用溯源**：每个知识点标注教材出处\n- **微课动画**：视觉型同学可享受动态讲解\n- **智能任务切换**：提到C语言不懂时，自动切换到C语言学习任务\n\n试试问我："HDFS是怎么工作的？给我画个图" 或 "我不太懂C语言"';
    }

    const dirStr = profile.learningDirection || '大数据技术';
    const langStr = (assessment.languages || ['python']).map(l => {
        const langNames = { python: 'Python', java: 'Java', c: 'C语言', cpp: 'C++', javascript: 'JavaScript', go: 'Go', sql: 'SQL', scala: 'Scala', rust: 'Rust' };
        return langNames[l] || l;
    }).join('、');
    const goalStr = profile.learningGoal || '学习提升';
    const styleStr = profile.cognitiveStyle || '实践型';

    let styleTip = '';
    if (assessment.cognitiveStyle === 'visual') {
        styleTip = '我会为你提供丰富的图表和可视化演示';
    } else if (assessment.cognitiveStyle === 'pragmatic') {
        styleTip = '我会为你提供大量代码示例和动手练习';
    } else {
        styleTip = '我会为你提供详细的理论解释和文档';
    }

    return `你好，**${currentUser.name}**！欢迎来到星识伴学系统 🎓\n\n根据你的学习评估，我已为你生成专属学习计划：\n\n📊 **你的学习画像**\n- 学习方向：${dirStr}\n- 主要语言：${langStr}\n- 学习目标：${goalStr}\n- 认知风格：${styleStr}\n\n🚀 **当前学习任务**\n你正在学习「${currentPath.find(p => p.status === 'current')?.topic || '基础课程'}」\n\n💡 **个性化提示**\n${styleTip}，帮助你在${dirStr}方向上快速成长。\n\n---\n\n你可以直接问我问题，比如：\n- "${currentPath.find(p => p.status === 'current')?.topic || '当前课程'}的核心概念是什么？"\n- "给我讲讲${langStr.split('、')[0]}的基础语法"\n- "我不太理解这个概念，能详细解释一下吗？"`;
}

let profile = {
    knowledgeBase: '普通学生',
    codeSkill: 'Python基础',
    learningGoal: '期末考试',
    cognitiveStyle: '待测试',
    weakness: '暂无',
    focusLevel: 'medium'
};

let evaluation = {
    interactionCount: 0,
    socraticPassRate: 0.0,
    difficultyLevel: 'basic',
    codePracticeTime: 0
};

let codePracticeStartTime = null;
let codePracticeTimer = null;
let lastGradeRecord = null;

let currentPath = normalizeLearningPath([
    { topic: '大数据导论', status: 'current' },
    { topic: '分布式文件系统', status: 'locked' }
]);

let messages = [];

let currentSourceLinks = {};
const LINK_CACHE_KEY = 'starlearn_link_cache';
const LINK_CACHE_EXPIRY_MS = 7 * 24 * 60 * 60 * 1000;

let chatContainer = null;
let profileContainer = null;
let pathContainer = null;
let messageInput = null;
let sendBtn = null;
let workflowPanel = null;
let workflowLogs = null;
let sourcePanel = null;
let sourceList = null;

let codeEditor = null;

function toggleDropdown() {
    const dd = document.getElementById('avatar-dropdown');
    const tp = document.getElementById('theme-panel');
    if (tp) tp.classList.remove('show');
    if (dd) dd.classList.toggle('show');
}

function toggleThemePanel() {
    const dd = document.getElementById('avatar-dropdown');
    const tp = document.getElementById('theme-panel');
    if (dd) dd.classList.remove('show');
    if (tp) tp.classList.toggle('show');
}

document.addEventListener('click', function(e) {
    const wrapper = document.getElementById('avatar-wrapper');
    if (wrapper && !wrapper.contains(e.target)) {
        const dropdown = document.getElementById('avatar-dropdown');
        const themePanel = document.getElementById('theme-panel');
        if (dropdown) dropdown.classList.remove('show');
        if (themePanel) themePanel.classList.remove('show');
    }
});

function generateParticles(theme) {
    const layer = document.getElementById('dynamic-bg-layer');
    if (!layer) {
        console.error('[DynamicTheme] #dynamic-bg-layer not found in DOM');
        return;
    }
    layer.innerHTML = '';

    if (theme === 'starry-night') {
        for (let i = 0; i < 80; i++) {
            const star = document.createElement('div');
            star.className = 'particle-star';
            const left = Math.random() * 100;
            const top = Math.random() * 100;
            const duration = 2 + Math.random() * 3;
            const delay = Math.random() * 5;
            const size = 2 + Math.random() * 3;
            star.style.left = left + 'vw';
            star.style.top = top + 'vh';
            star.style.width = size + 'px';
            star.style.height = size + 'px';
            star.style.setProperty('--dur', duration + 's');
            star.style.setProperty('--delay', delay + 's');
            layer.appendChild(star);
        }
    }

    if (theme === 'sakura-falling') {
        const colors = ['#ffccd5', '#ffb7c5', '#ffc8dd', '#ffafcc', '#f9a8d4'];
        for (let i = 0; i < 50; i++) {
            const petal = document.createElement('div');
            petal.className = 'particle-sakura';
            const left = Math.random() * 100;
            const duration = 8 + Math.random() * 7;
            const delay = Math.random() * 8;
            const size = 10 + Math.random() * 14;
            const color = colors[Math.floor(Math.random() * colors.length)];
            petal.style.left = left + 'vw';
            petal.style.setProperty('--size', size + 'px');
            petal.style.setProperty('--color', color);
            petal.style.setProperty('--dur', duration + 's');
            petal.style.setProperty('--delay', delay + 's');
            layer.appendChild(petal);
        }
    }

    if (theme === 'lunar-halo') {
        const halo = document.createElement('div');
        halo.className = 'moon-halo';
        layer.appendChild(halo);

        for (let i = 0; i < 50; i++) {
            const star = document.createElement('div');
            star.className = 'particle-star';
            const left = Math.random() * 100;
            const top = Math.random() * 100;
            const duration = 2 + Math.random() * 5;
            const delay = Math.random() * 6;
            const size = 1 + Math.random() * 2;
            star.style.left = left + 'vw';
            star.style.top = top + 'vh';
            star.style.width = size + 'px';
            star.style.height = size + 'px';
            star.style.setProperty('--dur', duration + 's');
            star.style.setProperty('--delay', delay + 's');
            layer.appendChild(star);
        }
    }

    if (theme === 'flowing-aurora') {
        const blobs = [
            { w: 400, h: 300, x: 10, y: 20, color: 'rgba(45,212,191,0.4)', dur: 70, delay: 0, mx1: '12vw', my1: '-8vh', mx2: '-6vw', my2: '10vh', mx3: '8vw', my3: '-4vh' },
            { w: 350, h: 250, x: 50, y: 10, color: 'rgba(139,92,246,0.35)', dur: 85, delay: -20, mx1: '-8vw', my1: '6vh', mx2: '10vw', my2: '-5vh', mx3: '-5vw', my3: '8vh' },
            { w: 300, h: 200, x: 30, y: 50, color: 'rgba(45,212,191,0.3)', dur: 60, delay: -35, mx1: '6vw', my1: '-3vh', mx2: '-10vw', my2: '7vh', mx3: '4vw', my3: '-6vh' },
            { w: 280, h: 220, x: 70, y: 40, color: 'rgba(167,139,250,0.25)', dur: 90, delay: -50, mx1: '-5vw', my1: '5vh', mx2: '8vw', my2: '-8vh', mx3: '-3vw', my3: '4vh' },
            { w: 250, h: 180, x: 20, y: 65, color: 'rgba(94,234,212,0.2)', dur: 75, delay: -15, mx1: '9vw', my1: '-6vh', mx2: '-7vw', my2: '4vh', mx3: '5vw', my3: '-2vh' },
        ];
        blobs.forEach(b => {
            const el = document.createElement('div');
            el.className = 'aurora-blob';
            el.style.left = b.x + '%';
            el.style.top = b.y + '%';
            el.style.width = b.w + 'px';
            el.style.height = b.h + 'px';
            el.style.background = b.color;
            el.style.setProperty('--dur', b.dur + 's');
            el.style.setProperty('--delay', b.delay + 's');
            el.style.setProperty('--mx1', b.mx1);
            el.style.setProperty('--my1', b.my1);
            el.style.setProperty('--mx2', b.mx2);
            el.style.setProperty('--my2', b.my2);
            el.style.setProperty('--mx3', b.mx3);
            el.style.setProperty('--my3', b.my3);
            layer.appendChild(el);
        });
    }
}

const DynamicThemeManager = {
    currentDynamicTheme: null,
    _fadeTimer: null,

    init() {
        const saved = localStorage.getItem('starlearn_theme');
        if (saved && this._isDynamicTheme(saved)) {
            this.activate(saved, true);
        }
    },

    _isDynamicTheme(theme) {
        return ['starry-night', 'sakura-falling', 'lunar-halo', 'flowing-aurora'].includes(theme);
    },

    activate(theme, silent) {
        this.deactivate();
        if (!this._isDynamicTheme(theme)) return;
        this.currentDynamicTheme = theme;

        this._hideMesh();
        generateParticles(theme);

        const layer = document.getElementById('dynamic-bg-layer');
        if (!silent && layer) {
            layer.style.opacity = '0';
            if (this._fadeTimer) cancelAnimationFrame(this._fadeTimer);
            this._fadeTimer = requestAnimationFrame(() => {
                layer.style.opacity = '1';
            });
        }
    },

    deactivate() {
        const layer = document.getElementById('dynamic-bg-layer');
        if (layer && layer.innerHTML) {
            layer.style.opacity = '0';
            setTimeout(() => { layer.innerHTML = ''; }, 500);
        }
        this.currentDynamicTheme = null;
        this._showMesh();
        if (this._fadeTimer) {
            cancelAnimationFrame(this._fadeTimer);
            this._fadeTimer = null;
        }
    },

    _hideMesh() {
        const meshBg = document.querySelector('.mesh-gradient-bg');
        if (meshBg) {
            meshBg.style.opacity = '0';
            meshBg.style.transition = 'opacity 0.5s ease';
        }
        const orbs = document.querySelectorAll('.mesh-orb');
        orbs.forEach(orb => {
            orb.style.opacity = '0';
            orb.style.transition = 'opacity 0.5s ease';
        });
    },

    _showMesh() {
        const meshBg = document.querySelector('.mesh-gradient-bg');
        if (meshBg) {
            meshBg.style.opacity = '';
            meshBg.style.transition = 'opacity 0.5s ease';
        }
        const orbs = document.querySelectorAll('.mesh-orb');
        orbs.forEach(orb => {
            orb.style.opacity = '';
            orb.style.transition = 'opacity 0.5s ease';
        });
    }
};

function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('starlearn_theme', theme);
    document.querySelectorAll('.theme-option').forEach(opt => {
        opt.classList.toggle('active', opt.dataset.theme === theme);
    });
    const lightThemes = new Set(['sakura-falling']);
    const isLightTheme = lightThemes.has(theme);
    document.body.classList.toggle('light-theme', isLightTheme);
    if (codeEditor) {
        const cmTheme = isLightTheme ? 'default' : 'dracula';
        codeEditor.setOption('theme', cmTheme);
    }
    if (DynamicThemeManager._isDynamicTheme(theme)) {
        DynamicThemeManager.activate(theme);
    } else {
        DynamicThemeManager.deactivate();
    }
    setTimeout(renderRadarChart, 100);
    const themePanel = document.getElementById('theme-panel');
    if (themePanel) themePanel.classList.remove('show');
}

function goToPersonal() {
    const dropdown = document.getElementById('avatar-dropdown');
    if (dropdown) dropdown.classList.remove('show');
    window.open('/personal.html', '_blank');
}

function logout() {
    const dropdown = document.getElementById('avatar-dropdown');
    if (dropdown) dropdown.classList.remove('show');
    localStorage.removeItem('starlearn_user');
    window.location.href = '/login.html';
}

function updateUserUI() {
    const userAvatarImg = document.getElementById('user-avatar-img');
    const dropdownAvatar = document.getElementById('dropdown-avatar');
    const dropdownUsername = document.getElementById('dropdown-username');
    if (userAvatarImg) userAvatarImg.src = currentUser.avatar;
    if (dropdownAvatar) dropdownAvatar.src = currentUser.avatar;
    if (dropdownUsername) dropdownUsername.textContent = currentUser.name;
}

function switchTab(tab) {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tab);
    });
    const chatView = document.getElementById('chat-view');
    const codeView = document.getElementById('code-view');
    if (chatView) chatView.classList.toggle('hidden', tab !== 'chat');
    if (codeView) codeView.classList.toggle('hidden', tab !== 'code');
    if (tab === 'code' && !codeEditor) {
        setTimeout(initCodeEditor, 50);
    }
    if (tab === 'code' && codeEditor) {
        setTimeout(() => codeEditor.refresh(), 50);
    }

    if (tab === 'code') {
        startCodePracticeTimer();
    } else {
        stopCodePracticeTimer();
    }
}

function switchOutputTab(tab) {
    document.querySelectorAll('.output-tab').forEach(btn => {
        const isActive = btn.dataset.outputTab === tab;
        btn.classList.toggle('active', isActive);
    });
    const runOutputPanel = document.getElementById('run-output-panel');
    const gradeOutputPanel = document.getElementById('grade-output-panel');
    if (runOutputPanel) runOutputPanel.classList.toggle('hidden', tab !== 'run');
    if (gradeOutputPanel) gradeOutputPanel.classList.toggle('hidden', tab !== 'grade');
}

function initCodeEditor() {
    const textarea = document.getElementById('code-editor');
    if (!textarea) return;
    const savedLang = localStorage.getItem('starlearn_preferred_lang') || 'python';
    const config = LANG_CONFIG[savedLang] || LANG_CONFIG.python;
    const langSelect = document.getElementById('lang-select');
    if (langSelect) langSelect.value = savedLang;
    codeEditor = CodeMirror.fromTextArea(textarea, {
        mode: config.mode,
        theme: 'dracula',
        lineNumbers: true,
        matchBrackets: true,
        autoCloseBrackets: true,
        indentUnit: 4,
        tabSize: 4,
        lineWrapping: true,
        extraKeys: {
            "Ctrl-Enter": function() { runCode(); },
            "Cmd-Enter": function() { runCode(); }
        }
    });
    codeEditor.setValue(config.template);
    codeEditor.refresh();
}

const LANG_CONFIG = {
    python: { mode: 'python', template: 'def hello():\n    print("Hello, Star-Learn!")\n\nhello()' },
    java: { mode: 'text/x-java', template: 'public class Main {\n    public static void main(String[] args) {\n        System.out.println("Hello, Star-Learn!");\n    }\n}' },
    c: { mode: 'text/x-csrc', template: '#include <stdio.h>\n\nint main() {\n    printf("Hello, Star-Learn!\\n");\n    return 0;\n}' },
    cpp: { mode: 'text/x-c++src', template: '#include <iostream>\n\nusing namespace std;\n\nint main() {\n    cout << "Hello, Star-Learn!" << endl;\n    return 0;\n}' },
    javascript: { mode: 'javascript', template: 'function hello() {\n    console.log("Hello, Star-Learn!");\n}\n\nhello();' },
    go: { mode: 'go', template: 'package main\n\nimport "fmt"\n\nfunc main() {\n    fmt.Println("Hello, Star-Learn!")\n}' },
    sql: { mode: 'text/x-sql', template: 'SELECT * FROM students\nWHERE grade = \'A\'\nORDER BY name;' },
    scala: { mode: 'text/x-scala', template: 'object Main extends App {\n    println("Hello, Star-Learn!")\n}' },
    rust: { mode: 'rust', template: 'fn main() {\n    println!("Hello, Star-Learn!");\n}' }
};

function changeLanguage() {
    if (!codeEditor) return;
    const langSelect = document.getElementById('lang-select');
    if (!langSelect) return;
    const lang = langSelect.value;
    const config = LANG_CONFIG[lang] || LANG_CONFIG.python;
    codeEditor.setOption('mode', config.mode);
    codeEditor.setValue(config.template);
    codeEditor.refresh();
    localStorage.setItem('starlearn_preferred_lang', lang);
}

function switchToCLanguage() {
    const langSelect = document.getElementById('lang-select');
    if (langSelect) langSelect.value = 'c';
    changeLanguage();
    switchTab('code');
}

function renderProfile() {
    const container = document.getElementById('profile-container');
    if (!container) return;

    normalizeProfileDisplayFields(profile);

    // 获取语言显示字符串
    const langStr = profile.languages && profile.languages.length > 0
        ? profile.languages.map(l => {
            const langNames = { python: 'Python', java: 'Java', c: 'C', cpp: 'C++', javascript: 'JS', go: 'Go', sql: 'SQL', scala: 'Scala', rust: 'Rust' };
            return langNames[l] || l;
        }).join('、')
        : 'Python';

    const config = {
        '学习方向': { icon: 'compass', val: profile.learningDirection || '大数据技术', color: 'text-blue-700 bg-blue-100' },
        '编程语言': { icon: 'code-2', val: langStr, color: 'text-violet-700 bg-violet-100' },
        '知识基础': { icon: 'book-open', val: profile.knowledgeBase, color: 'text-emerald-700 bg-emerald-100' },
        '编程能力': { icon: 'terminal', val: profile.codeSkill, color: 'text-purple-700 bg-purple-100' },
        '学习目标': { icon: 'target', val: profile.learningGoal, color: 'text-cyan-700 bg-cyan-100' },
        '认知风格': { icon: 'brain-circuit', val: profile.cognitiveStyle, color: 'text-orange-700 bg-orange-100' },
        '知识短板': { icon: 'alert-circle', val: profile.weakness, color: 'text-red-700 bg-red-100' },
        '专注程度': { icon: 'focus', val: (profile.focusLevel === 'high' || profile.focusLevel === '高专注') ? '高专注' : ((profile.focusLevel === 'low' || profile.focusLevel === '需要引导') ? '需引导' : '中等'), color: 'text-indigo-700 bg-indigo-100' }
    };
    container.innerHTML = Object.entries(config).map(([label, data]) => `
        <div class="profile-glass-tile flex flex-col p-2.5 rounded-2xl border shadow-sm transition-all duration-300 ease-out hover:-translate-y-0.5">
            <span class="text-xs text-gray-500 mb-1 flex items-center gap-1 font-semibold"><i data-lucide="${data.icon}" class="w-3.5 h-3.5"></i> ${label}</span>
            <span class="text-xs font-bold p-1 rounded-md ${data.color} w-fit">${data.val}</span>
        </div>
    `).join('');
    if (window.lucide) lucide.createIcons();
}

function renderRadarChart() {
    const canvas = document.getElementById('radar-chart');
    const loadingEl = document.getElementById('radar-loading');
    if (!canvas) return;
    try {
        const wrap = canvas.closest('.glass-radar-wrap');
        const wrapW = wrap ? wrap.clientWidth : 240;
        const size = Math.min(wrapW, 240);
        const dpr = window.devicePixelRatio || 1;
        canvas.width = size * dpr;
        canvas.height = size * dpr;
        canvas.style.width = size + 'px';
        canvas.style.height = size + 'px';

        const ctx = canvas.getContext('2d');
        if (!ctx) throw new Error('Canvas 2D context unavailable');
        ctx.scale(dpr, dpr);

        const W = size, H = size;
        const cx = W / 2, cy = H * 0.52;
        const R = Math.min(W, H) * 0.3;
        ctx.clearRect(0, 0, W, H);

        const style = getComputedStyle(document.documentElement);
        const radarStroke = style.getPropertyValue('--radar-stroke').trim() || '#3b82f6';
        const radarFill = style.getPropertyValue('--radar-fill').trim() || 'rgba(59,130,246,0.2)';
        const gridColor = style.getPropertyValue('--border-glass').trim() || 'rgba(255,255,255,0.12)';
        const labelColor = style.getPropertyValue('--text-secondary').trim() || 'rgba(255,255,255,0.55)';

        const dims = ['方向', '基础', '编程', '认知', '短板', '专注'];
        const values = [
            mapProfileToScore(profile.learningDirection || '大数据技术'),
            mapProfileToScore(profile.knowledgeBase),
            mapProfileToScore(profile.codeSkill),
            mapProfileToScore(profile.cognitiveStyle),
            mapProfileToScore(profile.weakness, true),
            mapProfileToScore(profile.focusLevel)
        ];
        const n = dims.length;

        for (let level = 1; level <= 4; level++) {
            ctx.beginPath();
            for (let i = 0; i < n; i++) {
                const angle = (Math.PI * 2 * i / n) - Math.PI / 2;
                const r = R * level / 4;
                const x = cx + r * Math.cos(angle);
                const y = cy + r * Math.sin(angle);
                if (i === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            }
            ctx.closePath();
            ctx.strokeStyle = gridColor;
            ctx.lineWidth = 1;
            ctx.stroke();
        }

        for (let i = 0; i < n; i++) {
            const angle = (Math.PI * 2 * i / n) - Math.PI / 2;
            ctx.beginPath();
            ctx.moveTo(cx, cy);
            ctx.lineTo(cx + R * Math.cos(angle), cy + R * Math.sin(angle));
            ctx.strokeStyle = gridColor;
            ctx.lineWidth = 1;
            ctx.stroke();

            const labelOffset = R + 22;
            const lx = cx + labelOffset * Math.cos(angle);
            const ly = cy + labelOffset * Math.sin(angle);
            ctx.fillStyle = labelColor;
            ctx.font = '11px sans-serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(dims[i], lx, ly);
        }

        ctx.beginPath();
        for (let i = 0; i < n; i++) {
            const angle = (Math.PI * 2 * i / n) - Math.PI / 2;
            const r = R * values[i] / 100;
            const x = cx + r * Math.cos(angle);
            const y = cy + r * Math.sin(angle);
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }
        ctx.closePath();
        ctx.fillStyle = radarFill;
        ctx.fill();
        ctx.strokeStyle = radarStroke;
        ctx.lineWidth = 2;
        ctx.stroke();

        for (let i = 0; i < n; i++) {
            const angle = (Math.PI * 2 * i / n) - Math.PI / 2;
            const r = R * values[i] / 100;
            ctx.beginPath();
            ctx.arc(cx + r * Math.cos(angle), cy + r * Math.sin(angle), 3, 0, Math.PI * 2);
            ctx.fillStyle = radarStroke;
            ctx.fill();
        }

        canvas.style.display = 'block';
        if (loadingEl) loadingEl.style.display = 'none';
    } catch (err) {
        console.warn('[RadarChart] Render failed:', err);
        canvas.style.display = 'none';
        if (loadingEl) {
            loadingEl.style.display = 'flex';
            loadingEl.innerHTML = '<div class="radar-error"><span>雷达图加载失败</span><button class="radar-error-retry" onclick="renderRadarChart()">重试</button></div>';
        }
    }
}

function mapProfileToScore(val, invert) {
    const map = {
        // 知识基础
        '零基础入门': 15, '基础入门': 30, '进阶学习': 65, '深入掌握': 90,
        '零基础': 10, '入门': 25, '基础': 35, '普通学生': 40,
        // 编程能力
        '编程新手': 15, '基础掌握': 35, '熟练编程': 65, '编程高手': 90,
        'Python基础': 35, 'Python进阶': 65, 'C语言基础': 30, 'C语言进阶': 60, 'C++基础': 30, 'C++进阶': 60,
        // 学习目标
        '应对考试': 45, '职业发展': 65, '项目实战': 70, '兴趣探索': 50, '竞赛备战': 80, '科研学术': 75,
        '期末考试': 50, '就业准备': 70, '科研入门': 80, '竞赛': 90,
        // 认知风格
        '视觉型': 70, '文字型': 50, '实践型': 80,
        'visual': 70, 'textual': 50, 'pragmatic': 80, '待测试': 30,
        // 专注度
        '高专注': 85, '中等专注': 55, '需要引导': 25, '需引导': 25,
        'high': 85, 'medium': 55, 'low': 20,
        // 学习方向
        '大数据技术': 60, '人工智能': 70, '前端开发': 55, '后端开发': 60, '算法数据结构': 75, '数据库技术': 55,
        // 知识短板
        '暂无': 70, '排序算法': 30, '分布式计算': 25, '流处理': 20,
        'C语言指针': 20, 'C语言内存管理': 15, 'C语言基础语法': 25,
        // 其他
        '中等': 50, '进阶': 70, '熟练': 80, '精通': 95, '优秀': 90
    };
    let score = map[val] || 40;
    if (invert) score = 100 - score;
    return Math.max(10, Math.min(95, score));
}

function renderEvaluation() {
    const evalContainer = document.getElementById('eval-container');
    if (!evalContainer) return;
    const diffColors = { basic: 'text-green-700 bg-green-100', medium: 'text-amber-700 bg-amber-100', advanced: 'text-red-700 bg-red-100' };
    const diffLabels = { basic: '基础', medium: '中等', advanced: '进阶' };
    evalContainer.innerHTML = `
        <div class="eval-metric glass-eval-card flex items-center gap-2 p-2.5 rounded-xl border shadow-sm">
            <i data-lucide="message-square" class="w-3.5 h-3.5 shrink-0" style="color: var(--accent);"></i>
            <span class="text-xs text-gray-500">交互次数</span>
            <span class="text-xs font-bold ml-auto" style="color: var(--primary);">${evaluation.interactionCount}</span>
        </div>
        <div class="eval-metric glass-eval-card flex items-center gap-2 p-2.5 rounded-xl border shadow-sm">
            <i data-lucide="check-circle" class="w-3.5 h-3.5 text-purple-500 shrink-0"></i>
            <span class="text-xs text-gray-500">启发通关率</span>
            <span class="text-xs font-bold text-purple-700 ml-auto">${(evaluation.socraticPassRate * 100).toFixed(0)}%</span>
        </div>
        <div class="eval-metric glass-eval-card flex items-center gap-2 p-2.5 rounded-xl border shadow-sm">
            <i data-lucide="code" class="w-3.5 h-3.5 text-emerald-500 shrink-0"></i>
            <span class="text-xs text-gray-500">代码实操</span>
            <span class="text-xs font-bold text-emerald-700 ml-auto">${evaluation.codePracticeTime}min</span>
        </div>
        <div class="eval-metric glass-eval-card flex items-center gap-2 p-2.5 rounded-xl border shadow-sm">
            <i data-lucide="gauge" class="w-3.5 h-3.5 text-orange-500 shrink-0"></i>
            <span class="text-xs text-gray-500">下一阶段难度</span>
            <span class="text-xs font-bold px-1.5 rounded ${diffColors[evaluation.difficultyLevel] || diffColors.medium} ml-auto">${diffLabels[evaluation.difficultyLevel] || '中等'}</span>
        </div>
    `;
    if (window.lucide) lucide.createIcons();
}

function renderPath() {
    const container = document.getElementById('path-container');
    if (container) {
        container.innerHTML = currentPath.map((node) => {
            if(node.status === 'current') {
                const style = `background: var(--primary-50); border-color: var(--primary-200); color: var(--primary);`;
                return `
                <div class="path-glass-node relative pl-6 mb-2 p-2.5 rounded-xl -ml-2 border transition-transform duration-300" style="${style}">
                    <div class="absolute left-[-1px] top-3 w-4 h-4 rounded-full border-2 border-white z-10 animate-pulse" style="background: var(--accent);"></div>
                    <p class="text-sm transition-colors duration-300" style="color: var(--primary);">${node.topic}</p>
                </div>`;
            }
            let dotColor = 'bg-gray-300';
            let textColor = 'text-gray-500';
            if(node.status === 'completed') {
                dotColor = 'bg-green-500'; textColor = 'text-green-700';
            }
            return `
            <div class="path-glass-node relative pl-6 mb-2 transition-opacity duration-300">
                <div class="absolute -left-[9px] top-1 w-4 h-4 rounded-full border-2 border-white ${dotColor} z-10 shadow-sm"></div>
                <p class="text-sm ${textColor} transition-colors duration-300">${node.topic}</p>
            </div>`;
        }).join('');
    }
    renderPathTree();
}

function updateDispatchBadge(strategy) {
    const badge = document.getElementById('dispatch-badge');
    const label = document.getElementById('dispatch-label');
    if (!badge || !label) return;
    const configs = {
        socratic: { text: '苏格拉底诊断', bg: 'bg-purple-50 text-purple-600 border-purple-100' },
        visual: { text: '高视觉权重', bg: 'bg-orange-50 text-orange-600 border-orange-100' },
        pragmatic: { text: '高实践权重', bg: 'bg-emerald-50 text-emerald-600 border-emerald-100' },
        textual: { text: '均衡模式', bg: '' }
    };
    const cfg = configs[strategy] || configs.textual;
    if (cfg.bg) {
        badge.className = `text-xs font-bold px-3 py-1 rounded-full border flex items-center gap-1 ${cfg.bg}`;
    } else {
        badge.className = 'text-xs font-bold px-3 py-1 rounded-full border flex items-center gap-1';
        badge.style.background = 'var(--primary-50)';
        badge.style.color = 'var(--primary)';
        badge.style.borderColor = 'var(--primary-200)';
    }
    label.textContent = cfg.text;
}

function getLinkCache() {
    try {
        const raw = localStorage.getItem(LINK_CACHE_KEY);
        if (!raw) return {};
        const cache = JSON.parse(raw);
        const now = Date.now();
        const valid = {};
        for (const [key, entry] of Object.entries(cache)) {
            if (now - entry.cachedAt < LINK_CACHE_EXPIRY_MS) {
                valid[key] = entry;
            }
        }
        localStorage.setItem(LINK_CACHE_KEY, JSON.stringify(valid));
        return valid;
    } catch {
        return {};
    }
}

function setLinkCacheEntry(source, url, status) {
    try {
        const cache = getLinkCache();
        cache[source] = { url, status, cachedAt: Date.now() };
        localStorage.setItem(LINK_CACHE_KEY, JSON.stringify(cache));
    } catch {}
}

function getTextbookUrl(textbookInfo) {
    if (currentSourceLinks[textbookInfo]) {
        return currentSourceLinks[textbookInfo];
    }
    const cache = getLinkCache();
    if (cache[textbookInfo] && cache[textbookInfo].status === 'valid') {
        return cache[textbookInfo].url;
    }
    const fallbackMap = {
        '大数据处理技术': 'https://ebook.hep.com.cn',
        '大数据导论': 'http://www.ucdrs.superlib.net/',
        '实验指导书': 'https://www.zhishikoo.com/'
    };
    const match = textbookInfo.match(/《(.+?)》/);
    if (match) {
        const textbookName = match[1];
        return fallbackMap[textbookName] || 'https://zh.hkr101.ru/';
    }
    return 'https://zh.hkr101.ru/';
}

async function validateTextbookLink(url) {
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000);
        const res = await fetch(url, {
            method: 'HEAD',
            mode: 'no-cors',
            signal: controller.signal
        });
        clearTimeout(timeoutId);
        return true;
    } catch {
        return false;
    }
}

function openTextbookLink(textbookInfo) {
    openTextbookModal(textbookInfo);
}

const _textbookContentCache = new Map();

function openTextbookModal(source) {
    let modal = document.getElementById('textbook-reader-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'textbook-reader-modal';
        modal.style.cssText = `
            position: fixed; inset: 0; z-index: 280;
            display: flex; align-items: center; justify-content: center;
            background: rgba(0,0,0,0.5); backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            opacity: 0; visibility: hidden;
            transition: opacity 300ms ease, visibility 300ms ease;
        `;
        modal.innerHTML = `
            <div class="textbook-reader-panel" id="textbook-reader-panel">
                <div class="textbook-reader-toolbar">
                    <div class="textbook-reader-toolbar-left">
                        <i data-lucide="book-open" style="width:18px;height:18px;color:var(--accent);"></i>
                        <span id="textbook-reader-title">教材阅览室</span>
                    </div>
                    <div class="textbook-reader-toolbar-right">
                        <button class="textbook-toolbar-btn" onclick="textbookAdjustFont(-1)" title="缩小字体">
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px;"><path d="M4 7V4h16v3"></path><path d="M9 20h6"></path><path d="M12 4v16"></path></svg>
                        </button>
                        <button class="textbook-toolbar-btn" onclick="textbookAdjustFont(1)" title="放大字体">
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px;"><path d="M4 7V4h16v3"></path><path d="M9 20h6"></path><path d="M12 4v16"></path><line x1="17" y1="12" x2="22" y2="12"></line><line x1="19.5" y1="9.5" x2="19.5" y2="14.5"></line></svg>
                        </button>
                        <button class="textbook-toolbar-btn" onclick="textbookToggleMaximize()" title="最大化" id="textbook-maximize-btn">
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px;"><polyline points="15 3 21 3 21 9"></polyline><polyline points="9 21 3 21 3 15"></polyline><line x1="21" y1="3" x2="14" y2="10"></line><line x1="3" y1="21" x2="10" y2="14"></line></svg>
                        </button>
                        <button class="textbook-toolbar-btn" onclick="closeTextbookModal()" title="关闭">
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px;"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                        </button>
                    </div>
                </div>
                <div id="textbook-reader-content" class="textbook-reader-content">
                    <div style="text-align: center; padding: 40px 0; color: var(--text-tertiary);">
                        <div class="skeleton-spinner" style="margin: 0 auto 12px;"></div>
                        正在检索教材内容...
                    </div>
                </div>
            </div>
        `;
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeTextbookModal();
        });
        document.addEventListener('keydown', function textbookEscHandler(e) {
            if (e.key === 'Escape' && modal.style.visibility === 'visible') {
                closeTextbookModal();
            }
        });
        document.body.appendChild(modal);
        if (window.lucide) lucide.createIcons();
    }

    const titleEl = document.getElementById('textbook-reader-title');
    if (titleEl) titleEl.textContent = source || '教材阅览室';

    const contentEl = document.getElementById('textbook-reader-content');
    if (contentEl) {
        contentEl.style.fontSize = (window._textbookFontSize || 13) + 'px';
        contentEl.innerHTML = `<div style="text-align: center; padding: 40px 0; color: var(--text-tertiary);">
            <div class="skeleton-spinner" style="margin: 0 auto 12px; width: 28px; height: 28px; border: 2px solid var(--border-glass); border-top-color: var(--primary-light); border-radius: 50%; animation: spin 0.8s linear infinite;"></div>
            正在检索教材内容...
        </div>`;
    }

    modal.style.opacity = '1';
    modal.style.visibility = 'visible';
    const panel = modal.querySelector('.textbook-reader-panel');
    if (panel) { panel.style.transform = 'translateY(0) scale(1)'; }

    if (_textbookContentCache.has(source)) {
        renderTextbookContent(contentEl, _textbookContentCache.get(source));
        return;
    }

    fetch(`${API_BASE}/api/v2/textbook/chapter`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source: source, keywords: source }),
    })
    .then(res => res.json())
    .then(data => {
        if (data.success && data.data) {
            _textbookContentCache.set(source, data.data);
            renderTextbookContent(contentEl, data.data);
        } else {
            contentEl.innerHTML = `<div style="text-align: center; padding: 40px 0; color: var(--text-tertiary);">
                <p>暂无该教材的详细内容</p>
                <p style="font-size: 11px; margin-top: 8px;">请尝试与AI助手对话获取相关知识</p>
            </div>`;
        }
    })
    .catch(err => {
        console.warn('[TextbookReader] Fetch failed:', err);
        contentEl.innerHTML = `<div style="text-align: center; padding: 40px 0; color: var(--text-tertiary);">
            <p>加载失败，请稍后重试</p>
        </div>`;
    });
}

window._textbookFontSize = 13;
window._textbookMaximized = false;

function textbookAdjustFont(delta) {
    window._textbookFontSize = Math.max(10, Math.min(22, (window._textbookFontSize || 13) + delta));
    const contentEl = document.getElementById('textbook-reader-content');
    if (contentEl) contentEl.style.fontSize = window._textbookFontSize + 'px';
}

function textbookToggleMaximize() {
    window._textbookMaximized = !window._textbookMaximized;
    const panel = document.getElementById('textbook-reader-panel');
    if (!panel) return;
    if (window._textbookMaximized) {
        panel.style.maxWidth = '100%';
        panel.style.width = '100%';
        panel.style.maxHeight = '100vh';
        panel.style.height = '100vh';
        panel.style.borderRadius = '0';
    } else {
        panel.style.maxWidth = '680px';
        panel.style.width = '92%';
        panel.style.maxHeight = '80vh';
        panel.style.height = '';
        panel.style.borderRadius = '20px';
    }
}

function closeTextbookModal() {
    const modal = document.getElementById('textbook-reader-modal');
    if (!modal) return;
    const panel = modal.querySelector('.textbook-reader-panel');
    if (panel) panel.style.transform = 'translateY(20px) scale(0.97)';
    modal.style.opacity = '0';
    setTimeout(() => { modal.style.visibility = 'hidden'; }, 300);
}

function renderTextbookContent(container, data) {
    if (!container) return;
    const sections = data.sections || [];
    let html = '';
    if (data.title) {
        html += `<h2 style="font-size: 18px; font-weight: 800; color: var(--text-primary); margin-bottom: 16px; text-shadow: 0 1px 3px rgba(0,0,0,0.3);">${escapeHtml(data.title)}</h2>`;
    }
    for (const section of sections) {
        if (section.title) {
            html += `<h3 style="font-size: 14px; font-weight: 700; color: var(--primary-light); margin-top: 20px; margin-bottom: 8px; padding-bottom: 4px; border-bottom: 1px solid var(--border-glass);">${escapeHtml(section.title)}</h3>`;
        }
        const content = section.content || '';
        const paragraphs = content.split(/\n+/);
        for (const p of paragraphs) {
            const trimmed = p.trim();
            if (!trimmed) continue;
            if (trimmed.startsWith('- ') || trimmed.startsWith('• ') || trimmed.startsWith('* ')) {
                html += `<div style="padding-left: 16px; margin: 4px 0; position: relative;"><span style="position: absolute; left: 0; color: var(--primary-light);">•</span>${escapeHtml(trimmed.substring(2))}</div>`;
            } else if (/^\d+[\.\)]\s/.test(trimmed)) {
                html += `<div style="padding-left: 16px; margin: 4px 0;">${escapeHtml(trimmed)}</div>`;
            } else {
                html += `<p style="margin: 8px 0;">${escapeHtml(trimmed)}</p>`;
            }
        }
    }
    if (data.sources && data.sources.length > 0) {
        html += `<div style="margin-top: 24px; padding-top: 12px; border-top: 1px solid var(--border-glass); font-size: 11px; color: var(--text-tertiary);">
            <span>📚 参考来源：${data.sources.map(s => escapeHtml(s)).join('、')}</span>
        </div>`;
    }
    container.innerHTML = html;
}

function updateSourceLinks(sourceLinks) {
    if (sourceLinks && typeof sourceLinks === 'object') {
        currentSourceLinks = { ...currentSourceLinks, ...sourceLinks };
        for (const [source, url] of Object.entries(sourceLinks)) {
            setLinkCacheEntry(source, url, 'valid');
        }
    }
}

function renderSources(sources) {
    const sourcePanel = document.getElementById('source-panel');
    const sourceList = document.getElementById('source-list');
    if (!sourcePanel || !sourceList) return;
    if (!sources || sources.length === 0) {
        sourcePanel.classList.add('hidden');
        return;
    }
    sourcePanel.classList.remove('hidden');
    sourceList.innerHTML = sources.map(s => {
        const hasDeepLink = currentSourceLinks[s] || getLinkCache()[s];
        const linkIndicator = hasDeepLink
            ? '<i data-lucide="external-link" class="w-2.5 h-2.5 ml-1 text-green-500" title="深度链接可用"></i>'
            : '<i data-lucide="alert-circle" class="w-2.5 h-2.5 ml-1 text-amber-400" title="深度链接未配置"></i>';
        return `
        <span class="doc-ref cursor-pointer hover:text-blue-600 transition-colors group" onclick="openTextbookLink('${escapeHtml(s)}')">
            <i data-lucide="book-open" class="w-3 h-3"></i> ${escapeHtml(s)} ${linkIndicator}
        </span>`;
    }).join('');
    if (window.lucide) lucide.createIcons();
}

async function refreshLinkCacheFromBackend() {
    try {
        const res = await fetch(`${API_BASE}/api/textbook-links/validate`);
        if (!res.ok) {
            console.warn(`[TextbookLinks] 验证接口返回 ${res.status}，跳过缓存刷新`);
            return;
        }
        const data = await res.json();
        if (data.validationResults) {
            for (const [source, info] of Object.entries(data.validationResults)) {
                if (info.deepLink) {
                    currentSourceLinks[source] = info.deepLink;
                    setLinkCacheEntry(source, info.deepLink, 'valid');
                }
            }
        }
    } catch (err) {
        console.warn('[TextbookLinks] 验证接口请求失败:', err.message || err);
    }
}

function preprocessContent(content) {
    if (!content) return '';
    if (content.includes('```mermaid')) return content;
    const mermaidPattern = /(^|\n)(graph|flowchart) (TD|LR|TB|RL|BT)[\s\S]+?(?=\n\n[^ \t]|$)/g;
    const seqPattern = /(^|\n)sequenceDiagram[\s\S]+?(?=\n\n[^ \t]|$)/g;
    let result = content.replace(mermaidPattern, (match) => {
        return `\n\`\`\`mermaid\n${match.trim()}\n\`\`\`\n\n`;
    });
    result = result.replace(seqPattern, (match) => {
        return `\n\`\`\`mermaid\n${match.trim()}\n\`\`\`\n\n`;
    });
    return result;
}

function processDocRefs(html) {
    return html.replace(/\[Doc_Ref:\s*([^\]]+)\]/g, (match, ref) => {
        const hasDeepLink = currentSourceLinks[ref] || getLinkCache()[ref];
        const linkIndicator = hasDeepLink
            ? '<i data-lucide="external-link" style="width:9px;height:9px;display:inline;vertical-align:middle;margin-left:2px;color: var(--success);" title="深度链接可用"></i>'
            : '';
        return `<span class="doc-ref cursor-pointer hover:text-blue-600 transition-colors" onclick="openTextbookLink('${escapeHtml(ref)}')"><i data-lucide="book-open" style="width:10px;height:10px;display:inline;vertical-align:middle;"></i> ${escapeHtml(ref)}${linkIndicator}</span>`;
    });
}

async function renderMessages() {
    const container = document.getElementById('chat-container');
    if (!container) return;

    const streamBubble = container.querySelector('.stream-bubble');

    container.innerHTML = messages.map(msg => {
        const processedContent = msg.role === 'user' ? msg.content : preprocessContent(msg.content);
        let htmlContent = window.marked && msg.role !== 'user' ? marked.parse(processedContent) : processedContent;
        if (msg.role !== 'user') {
            htmlContent = processDocRefs(htmlContent);
        }
        const isSocratic = msg.role === 'assistant' && msg.socratic;
        return `
        <div class="msg-row flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}">
            <div class="max-w-[90%] flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'} min-w-0">
                ${msg.role !== 'user' ? `<span class="text-xs mb-1 ml-1 flex items-center gap-1 font-bold" style="color: var(--primary);"><i data-lucide="bot" class="w-3 h-3"></i> 智能辅导团队 ${isSocratic ? '<span class="socratic-badge"><i data-lucide="help-circle" style="width:10px;height:10px;display:inline;"></i> 苏格拉底诊断</span>' : ''}</span>` : ''}
                <div class="msg-bubble p-4 rounded-2xl ${msg.role === 'user' ? 'msg-bubble-user rounded-tr-none' : 'msg-bubble-bot rounded-tl-none'} w-full min-w-0 overflow-x-visible">
                    <div class="prose prose-sm max-w-none break-words whitespace-pre-wrap">${htmlContent}</div>
                </div>
            </div>
        </div>`;
    }).join('');

    if (streamBubble && isTypewriting) {
        container.appendChild(streamBubble);
    }

    container.scrollTop = container.scrollHeight;
    if (window.lucide) lucide.createIcons();

    if (window.mermaid) {
        const placeholders = document.querySelectorAll('.mermaid-placeholder');
        for (let i = 0; i < placeholders.length; i++) {
            const div = placeholders[i];
            const txt = document.createElement("textarea");
            txt.innerHTML = div.innerHTML;
            let code = txt.value.trim();
            const id = `mermaid-svg-${Date.now()}-${i}`;
            try {
                code = code.replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>');
                const validStarts = ['graph', 'flowchart', 'sequenceDiagram', 'classDiagram', 'stateDiagram', 'pie', 'gantt'];
                const codeLines = code.split('\n').filter(line => line.trim() !== '');
                if (codeLines.length > 0) {
                    const firstLine = codeLines[0].trim();
                    const isValidStart = validStarts.some(start => firstLine.startsWith(start));
                    if (!isValidStart) throw new Error('图表代码格式不正确');
                }
                const { svg } = await mermaid.render(id, code);
                div.innerHTML = svg;
            } catch (e) {
                console.warn("Mermaid render error:", e);
                div.style.display = 'none';
                const errEl = document.getElementById('d' + id);
                if (errEl) errEl.remove();
            }
            div.classList.remove('mermaid-placeholder');
        }
    }

    renderMicroCourses();
}

function renderMicroCourses() {
    const mcBlocks = document.querySelectorAll('.micro-course-block');
    mcBlocks.forEach(block => {
        if (block.dataset.rendered) return;
        block.dataset.rendered = 'true';
        try {
            const data = JSON.parse(block.textContent);
            let scenesHtml = '';
            if (data.scenes) {
                data.scenes.forEach((scene, idx) => {
                    scenesHtml += `
                        <div class="mc-scene ${idx === 0 ? 'active' : ''}" data-scene-idx="${idx}">
                            <div class="text-xs text-indigo-300 mb-1">Scene ${idx + 1}</div>
                            <div class="text-sm">${escapeHtml(scene.narration)}</div>
                            ${scene.highlight ? `<div class="text-xs text-amber-300 mt-1">Key: ${escapeHtml(scene.highlight)}</div>` : ''}
                        </div>
                    `;
                });
            }
            block.innerHTML = `
                <div class="micro-course-player">
                    <div class="flex items-center gap-2 mb-3">
                        <i data-lucide="play-circle" class="w-5 h-5 text-indigo-300"></i>
                        <span class="font-bold text-sm">${escapeHtml(data.title || '微课动画')}</span>
                        <button onclick="playMicroCourse(this)" class="ml-auto px-3 py-1 text-[var(--text-on-accent)] text-xs rounded-lg font-semibold transition-colors">播放</button>
                    </div>
                    <div class="mc-progress mb-3"><div class="mc-progress-bar" style="width: 0%"></div></div>
                    <div class="mc-scenes">${scenesHtml}</div>
                </div>
            `;
            if (window.lucide) lucide.createIcons();
        } catch(e) {
            block.innerHTML = `<div class="bg-red-50 text-red-500 p-2 rounded text-xs">微课数据解析失败</div>`;
        }
    });
}

function playMicroCourse(btn) {
    const player = btn.closest('.micro-course-player');
    const scenes = player.querySelectorAll('.mc-scene');
    const progressBar = player.querySelector('.mc-progress-bar');
    btn.disabled = true;
    btn.textContent = '播放中...';
    let idx = 0;
    function next() {
        if (idx >= scenes.length) {
            btn.disabled = false;
            btn.textContent = '重播';
            progressBar.style.width = '100%';
            return;
        }
        scenes.forEach(s => s.classList.remove('active'));
        scenes[idx].classList.add('active');
        progressBar.style.width = ((idx + 1) / scenes.length * 100) + '%';
        const narration = scenes[idx].querySelector('div:nth-child(2)').textContent;
        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel();
            const utter = new SpeechSynthesisUtterance(narration);
            utter.lang = 'zh-CN';
            utter.rate = 0.9;
            utter.onend = () => { idx++; setTimeout(next, 500); };
            window.speechSynthesis.speak(utter);
        } else {
            setTimeout(() => { idx++; next(); }, 3000);
        }
    }
    next();
}

async function runCode() {
    if (!codeEditor) return;
    const code = codeEditor.getValue();
    const langSelect = document.getElementById('lang-select');
    const outputPanel = document.getElementById('run-output-panel');
    if (!outputPanel) return;
    switchOutputTab('run');
    outputPanel.innerHTML = '<div class="text-yellow-400 text-xs animate-pulse">正在运行中...</div>';
    try {
        const res = await fetch(RUN_CODE_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code, language: langSelect ? langSelect.value : 'python' })
        });
        const data = await res.json();
        let output = '';
        if (data.stdout) output += `<div class="text-green-400 whitespace-pre-wrap">${escapeHtml(data.stdout)}</div>`;
        if (data.stderr) output += `<div class="text-red-400 whitespace-pre-wrap mt-2">${escapeHtml(data.stderr)}</div>`;
        if (!data.stdout && !data.stderr) output = '<div class="text-gray-500">程序运行完毕，无输出。</div>';
        const statusColor = data.returncode === 0 ? 'text-green-400' : 'text-red-400';
        const statusText = data.returncode === 0 ? '运行成功' : '运行失败';
        outputPanel.innerHTML = `<div class="${statusColor} text-xs mb-2 pb-2 border-b border-gray-700">退出码: ${data.returncode} | ${statusText}</div>${output}`;
    } catch (error) {
        outputPanel.innerHTML = `<div class="text-red-400">运行请求失败: ${escapeHtml(error.message)}</div>`;
    }
}

async function submitGrade() {
    if (!codeEditor) return;
    const code = codeEditor.getValue();
    const taskInput = document.getElementById('task-input');
    const langSelect = document.getElementById('lang-select');
    const gradePanel = document.getElementById('grade-output-panel');
    if (!gradePanel) return;
    const task = taskInput ? taskInput.value.trim() : '';
    if (!task) {
        switchOutputTab('grade');
        gradePanel.innerHTML = '<div class="text-orange-500 text-sm text-center mt-8">请先在「编程题目」区域输入题目要求，再提交批阅。</div>';
        return;
    }
    switchOutputTab('grade');
    gradePanel.innerHTML = '<div class="text-center mt-8"><div class="animate-spin w-8 h-8 border-4 border-t-transparent rounded-full mx-auto mb-3" style="border-color: var(--primary-200); border-top-color: var(--primary);"></div><div class="text-gray-500 text-sm">AI 正在批阅你的代码，请稍候...</div></div>';
    try {
        const res = await fetch(GRADE_CODE_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code, task, language: langSelect ? langSelect.value : 'python', currentProfile: profile })
        });
        const data = await res.json();
        renderGradeResult(data);
        lastGradeRecord = {
            task: task,
            score: data.score || 0,
            language: langSelect ? langSelect.value : 'python',
            correctness: data.correctness || '',
            logic_analysis: data.logic_analysis || '',
            style_analysis: data.style_analysis || '',
            suggestions: data.suggestions || [],
            graded_at: new Date().toISOString()
        };
        saveProgress();
    } catch (error) {
        gradePanel.innerHTML = `<div class="text-red-500 text-sm text-center mt-8">批阅请求失败: ${escapeHtml(error.message)}</div>`;
    }
}

function renderGradeResult(data) {
    const gradePanel = document.getElementById('grade-output-panel');
    if (!gradePanel) return;
    const score = data.score || 0;
    let scoreClass = 'score-poor';
    if (score >= 90) scoreClass = 'score-excellent';
    else if (score >= 70) scoreClass = 'score-good';
    else if (score >= 50) scoreClass = 'score-medium';
    let suggestionsHtml = '';
    if (data.suggestions && data.suggestions.length > 0) {
        suggestionsHtml = data.suggestions.map((s, i) => `
            <div class="flex items-start gap-2 p-2 bg-amber-50 rounded-lg border border-amber-100">
                <span class="shrink-0 w-5 h-5 bg-amber-200 text-amber-700 rounded-full flex items-center justify-center text-xs font-bold">${i + 1}</span>
                <span class="text-sm text-amber-800">${escapeHtml(s)}</span>
            </div>
        `).join('');
    }
    let refAnswerHtml = '';
    if (data.reference_answer) {
        refAnswerHtml = `<div class="mt-4"><div class="text-xs font-semibold text-gray-500 mb-2 flex items-center gap-1"><i data-lucide="code" class="w-3 h-3"></i> 参考答案</div><pre class="bg-gray-900 text-green-400 p-3 rounded-lg text-xs overflow-x-auto whitespace-pre-wrap font-mono">${escapeHtml(data.reference_answer)}</pre></div>`;
    }
    gradePanel.innerHTML = `
        <div class="animate-slide-up space-y-4">
            <div class="flex items-center gap-5 p-4 rounded-xl border" style="background: var(--primary-50); border-color: var(--primary-200);">
                <div class="score-ring ${scoreClass} shrink-0">${score}</div>
                <div class="flex-1">
                    <div class="text-lg font-bold text-gray-800 mb-1">AI 批阅结果</div>
                    <div class="text-sm text-gray-600">${score >= 90 ? '优秀！继续保持！' : score >= 70 ? '良好，还有提升空间' : score >= 50 ? '及格，需要加强练习' : '需要重新复习相关知识'}</div>
                    ${data.encouragement ? `<div class="text-xs mt-2 italic" style="color: var(--primary);">"${escapeHtml(data.encouragement)}"</div>` : ''}
                </div>
            </div>
            <div><div class="text-xs font-semibold text-gray-500 mb-2 flex items-center gap-1"><i data-lucide="check-square" class="w-3 h-3"></i> 正确性评价</div><p class="text-sm text-gray-700 rounded-lg border p-3">${escapeHtml(data.correctness || '无')}</p></div>
            <div><div class="text-xs font-semibold text-gray-500 mb-2 flex items-center gap-1"><i data-lucide="git-branch" class="w-3 h-3"></i> 逻辑分析</div><p class="text-sm text-gray-700 rounded-lg border p-3">${escapeHtml(data.logic_analysis || '无')}</p></div>
            <div><div class="text-xs font-semibold text-gray-500 mb-2 flex items-center gap-1"><i data-lucide="palette" class="w-3 h-3"></i> 代码风格</div><p class="text-sm text-gray-700 rounded-lg border p-3">${escapeHtml(data.style_analysis || '无')}</p></div>
            ${suggestionsHtml ? `<div><div class="text-xs font-semibold text-gray-500 mb-2 flex items-center gap-1"><i data-lucide="lightbulb" class="w-3 h-3"></i> 改进建议</div><div class="space-y-2">${suggestionsHtml}</div></div>` : ''}
            ${refAnswerHtml}
        </div>
    `;
    if (window.lucide) lucide.createIcons();
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function extractTaskFromContent(fullText) {
    if (!fullText) return '';

    const lines = fullText.split('\n');

    let taskStartIdx = -1;
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        if (line.match(/📝?\s*题目/) || line.match(/题目[：:]/) || line.match(/题目描述/) || line.match(/^(#{1,3}\s*)?题目/)) {
            taskStartIdx = i;
            break;
        }
    }

    if (taskStartIdx === -1) {
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            if (line.match(/请编写|请实现|请完成|请设计|编程题|练习题|作业[：:]/)) {
                taskStartIdx = i;
                break;
            }
        }
    }

    if (taskStartIdx === -1) {
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            if (line.match(/Task:|Problem:|Exercise:/)) {
                taskStartIdx = i;
                break;
            }
        }
    }

    if (taskStartIdx !== -1) {
        let extractedParts = [];
        for (let i = taskStartIdx; i < lines.length; i++) {
            const line = lines[i].trim();
            if (!line) continue;

            if (extractedParts.length > 0 && (
                line.match(/^```/) ||
                line.match(/^#{1,3}\s*(💡|📊|🎯|📚|🐍|核心概念|代码实现|算法逻辑|实际操作|考点|拓展)/) ||
                line.match(/^#{1,3}\s*(Python|代码|实现|可视化|步骤|考点)/)
            )) {
                break;
            }

            extractedParts.push(line);

            if (extractedParts.join('\n').length > 300) break;
        }

        if (extractedParts.length > 0) {
            let result = extractedParts.join('\n');
            result = result.replace(/\*\*/g, '').replace(/📝\s*/g, '').replace(/#{1,6}\s*/g, '');
            result = result.replace(/^\s*题目[：:]\s*/i, '题目：');
            if (result.length > 250) {
                result = result.substring(0, 247) + '...';
            }
            return result;
        }
    }

    const shortDesc = lines.filter(l => l.trim()).slice(0, 3).join(' ').replace(/[#*\[\]]/g, '').trim();
    if (shortDesc.length > 150) {
        return shortDesc.substring(0, 147) + '...';
    }
    return shortDesc;
}

function autoFillTask(taskText) {
    const refinedTask = extractTaskFromContent(taskText);
    const taskInput = document.getElementById('task-input');
    if (taskInput) {
        taskInput.value = refinedTask;
        switchTab('code');
    }
}

function isProgrammingTask(text) {
    if (!text) return false;
    const lines = text.split('\n').filter(l => l.trim());
    if (lines.length === 0) return false;

    const taskSignals = ['📝 题目', '题目：', '题目描述', '编程题', '练习题', '作业：', 'Task:', 'Problem:', 'Exercise:'];
    const hasTaskSignal = taskSignals.some(s => text.includes(s));
    if (!hasTaskSignal) return false;

    const codeSignals = ['函数', '算法', '代码', '编写', '实现', '编程', 'def ', 'int main', '#include', 'class ', 'return', '输入', '输出', '示例', '测试用例'];
    const hasCodeSignal = codeSignals.some(s => text.includes(s));

    const instructionSignals = ['请编写', '请实现', '请完成', '请设计', '要求你', '实现一个', '编写一个', '设计一个'];
    const hasInstructionSignal = instructionSignals.some(s => text.includes(s));

    if (hasTaskSignal && (hasCodeSignal || hasInstructionSignal)) {
        const lines = text.split('\n');
        let taskLines = 0;
        for (let line of lines) {
            if (line.trim() && !line.trim().startsWith('```') && !line.trim().startsWith('#')) {
                taskLines++;
            }
        }
        return taskLines >= 2;
    }

    return false;
}

function detectLanguageNeed(text) {
    const lower = text.toLowerCase();
    const cKeywords = ['c语言', 'c 语言', 'c语言不懂', 'c语言不会', 'c语言不理解', 'c语言基础', 'c语言指针', 'c语言数组', 'c语言结构体', 'c语言内存', 'c语言函数', 'c语言入门', '学c语言', 'c语言学习', 'c语言复习', 'c语言考试'];
    const cppKeywords = ['c++', 'cpp', 'c++不懂', 'c++不会', 'c++基础', 'c++入门', '学c++', 'c++学习', 'c++复习'];
    for (const kw of cKeywords) {
        if (lower.includes(kw)) return 'c';
    }
    for (const kw of cppKeywords) {
        if (lower.includes(kw)) return 'cpp';
    }
    return null;
}

const STREAM_API_URL = `${API_BASE}/api/v2/chat/stream`;

const AGENT_COLORS = {
    system: { bg: 'bg-slate-100', text: 'text-slate-600', border: 'border-slate-300', dot: 'bg-slate-400' },
    profiler: { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200', dot: 'bg-blue-500' },
    planner: { bg: 'bg-violet-50', text: 'text-violet-700', border: 'border-violet-200', dot: 'bg-violet-500' },
    master_controller: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200', dot: 'bg-amber-500' },
    rag_retriever: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200', dot: 'bg-emerald-500' },
    socratic_evaluator: { bg: 'bg-purple-50', text: 'text-purple-700', border: 'border-purple-200', dot: 'bg-purple-500' },
    generator_visual: { bg: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-200', dot: 'bg-orange-500' },
    generator_pragmatic: { bg: 'bg-teal-50', text: 'text-teal-700', border: 'border-teal-200', dot: 'bg-teal-500' },
    generator_textual: { bg: 'bg-cyan-50', text: 'text-cyan-700', border: 'border-cyan-200', dot: 'bg-cyan-500' },
    evaluator: { bg: 'bg-rose-50', text: 'text-rose-700', border: 'border-rose-200', dot: 'bg-rose-500' },
};
const DEFAULT_AGENT_COLOR = { bg: 'bg-gray-50', text: 'text-gray-600', border: 'border-gray-200', dot: 'bg-gray-400' };

const AGENT_LABELS = {
    system: '系统',
    profiler: '画像分析',
    planner: '路径规划',
    master_controller: '主控中枢',
    rag_retriever: 'RAG检索',
    socratic_evaluator: '苏格拉底',
    generator_visual: '视觉生成',
    generator_pragmatic: '实践生成',
    generator_textual: '文本生成',
    evaluator: '评估',
};

const FLOW_PIPELINE = ['system', 'profiler', 'planner', 'master_controller', 'rag_retriever', 'socratic_evaluator', 'generator_visual', 'generator_pragmatic', 'generator_textual', 'evaluator'];

let sandboxLogs = [];
let activeAgents = new Set();
let sandboxFilterSet = new Set();
let typewriterTimer = null;
let typewriterQueue = [];
let isTypewriting = false;
let currentAssistantContent = '';
let currentAssistantIdx = -1;
let streamAbortController = null;
let resourcePollingTimer = null;
let currentResourceTaskId = null;
let resourcePollingBackoff = 0;
let resourceCompletedAgents = new Set();
let mockProgressTimers = {};
let resourcePollingStartTime = 0;
let resourceAgentStartTimes = {};
const RESOURCE_SHORT_TIMEOUT = 10000;
const RESOURCE_LONG_TIMEOUT = 30000;

const RESOURCE_STATUS_API = `${API_BASE}/api/v2/resource/status`;
const RESOURCE_POLL_INTERVAL = 1000;
const RESOURCE_MAX_BACKOFF = 8000;

const RESOURCE_CONFIG = {
    document_generator: { icon: 'file-text', title: '文档', color: 'var(--accent)' },
    mindmap_generator: { icon: 'git-branch', title: '导图', color: 'var(--primary-light)' },
    video_content: { icon: 'video', title: '视频', color: 'var(--warning)' },
    exercise_generator: { icon: 'code-2', title: '习题', color: 'var(--success)' },
};

const RESOURCE_PHASE_LABELS = {
    document_generator: ['构思框架', '组织内容', '润色排版'],
    mindmap_generator: ['构思架构', '布局节点', '渲染连线'],
    video_content: ['检索资源', '匹配内容', '生成摘要'],
    exercise_generator: ['设计题目', '编写用例', '校验答案'],
};

function getResourcePhase(agentName, progress) {
    const phases = RESOURCE_PHASE_LABELS[agentName] || ['处理中', '生成中', '完善中'];
    if (progress < 33) return phases[0];
    if (progress < 66) return phases[1];
    return phases[2];
}

function toggleAccordion(agentName) {
    const allAccordions = document.querySelectorAll('.resource-accordion');
    const target = document.querySelector(`.resource-accordion[data-resource="${agentName}"]`);
    if (!target) return;
    const wasOpen = target.classList.contains('is-open');
    allAccordions.forEach(a => {
        a.classList.remove('is-open');
        a.classList.add('is-collapsed');
    });
    if (!wasOpen) {
        target.classList.add('is-open');
        target.classList.remove('is-collapsed');
    } else {
        allAccordions.forEach(a => a.classList.remove('is-collapsed'));
    }
}

function showResourceDashboard() {
    const dashboard = document.getElementById('resource-dashboard');
    if (dashboard) dashboard.classList.remove('hidden');
    const cancelBtn = document.getElementById('dashboard-cancel-btn');
    if (cancelBtn) cancelBtn.classList.remove('hidden');
}

function hideResourceDashboard() {
    const dashboard = document.getElementById('resource-dashboard');
    if (dashboard) dashboard.classList.add('hidden');
    const cancelBtn = document.getElementById('dashboard-cancel-btn');
    if (cancelBtn) cancelBtn.classList.add('hidden');
}

function resetResourceCards() {
    resourceCompletedAgents = new Set();
    Object.values(mockProgressTimers).forEach(id => clearInterval(id));
    mockProgressTimers = {};
    const accordions = document.querySelectorAll('.resource-accordion');
    accordions.forEach(acc => {
        acc.dataset.status = 'pending';
        acc.classList.remove('is-open');
        const skeleton = acc.querySelector('.resource-skeleton');
        const content = acc.querySelector('.resource-content');
        if (skeleton) {
            skeleton.classList.remove('is-running', 'is-completed', 'is-failed', 'hidden');
            const statusEl = skeleton.querySelector('.resource-skeleton-status');
            if (statusEl) statusEl.textContent = '排队中 0%';
        }
        if (content) {
            content.classList.add('hidden');
            content.innerHTML = '';
        }
        const headerRing = acc.querySelector('.accordion-ring .ring-progress');
        if (headerRing) headerRing.setAttribute('stroke-dasharray', '0 100');
        const headerStatus = acc.querySelector('.accordion-header-right .resource-skeleton-status');
        if (headerStatus) headerStatus.textContent = '排队中 0%';
    });
}

function startResourcePolling(taskId) {
    stopResourcePolling();
    currentResourceTaskId = taskId;
    resourcePollingBackoff = 0;
    resourcePollingStartTime = Date.now();
    resourceAgentStartTimes = {};
    Object.keys(RESOURCE_CONFIG).forEach((agent, idx) => {
        resourceAgentStartTimes[agent] = Date.now();
        setTimeout(() => startMockProgress(agent), idx * 400);
    });
    showResourceDashboard();
    resetResourceCards();
    pollResourceStatus();
}

function stopResourcePolling() {
    if (resourcePollingTimer) {
        clearTimeout(resourcePollingTimer);
        resourcePollingTimer = null;
    }
    currentResourceTaskId = null;
}

function cancelResourceGeneration() {
    stopResourcePolling();
    Object.values(mockProgressTimers).forEach(id => clearInterval(id));
    mockProgressTimers = {};
    hideResourceDashboard();
}

async function pollResourceStatus() {
    if (!currentResourceTaskId) return;

    try {
        const res = await fetch(`${RESOURCE_STATUS_API}/${currentResourceTaskId}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const data = await res.json();
        resourcePollingBackoff = 0;
        updateResourceDashboard(data);

        if (data.overallStatus === 'completed' || data.overallStatus === 'failed') {
            const cancelBtn = document.getElementById('dashboard-cancel-btn');
            if (cancelBtn) cancelBtn.classList.add('hidden');
            updateDashboardOverallStatus(data.overallStatus, data.overallProgress);
            return;
        }

        resourcePollingTimer = setTimeout(pollResourceStatus, RESOURCE_POLL_INTERVAL);
    } catch (e) {
        resourcePollingBackoff = Math.min(resourcePollingBackoff * 2 + RESOURCE_POLL_INTERVAL, RESOURCE_MAX_BACKOFF);
        console.warn(`Resource poll failed, retrying in ${resourcePollingBackoff}ms:`, e);
        resourcePollingTimer = setTimeout(pollResourceStatus, resourcePollingBackoff);
    }
}

function updateDashboardOverallStatus(status, progress) {
    const el = document.getElementById('dashboard-overall-status');
    if (!el) return;
    const labels = { pending: '等待中', running: '生成中', completed: '已完成', failed: '部分失败' };
    const bgColors = {
        pending: 'var(--surface-glass)',
        running: 'var(--accent-bg)',
        completed: 'var(--success-bg)',
        failed: 'var(--danger-bg)'
    };
    const textColors = {
        pending: 'var(--text-tertiary)',
        running: 'var(--primary-light)',
        completed: 'var(--success)',
        failed: 'var(--danger)'
    };
    el.textContent = `${labels[status] || status} ${progress}%`;
    el.style.background = bgColors[status] || bgColors.pending;
    el.style.color = textColors[status] || textColors.pending;
}

function updateResourceDashboard(data) {
    updateDashboardOverallStatus(data.overallStatus, data.overallProgress);

    for (const sub of data.subtasks) {
        const acc = document.querySelector(`.resource-accordion[data-resource="${sub.agent}"]`);
        if (!acc) continue;

        acc.dataset.status = sub.status;
        const skeleton = acc.querySelector('.accordion-body .resource-skeleton');
        const content = acc.querySelector('.accordion-body .resource-content');
        const headerRing = acc.querySelector('.accordion-ring .ring-progress');
        const headerStatus = acc.querySelector('.accordion-header-right .resource-skeleton-status');

        if (sub.status === 'completed' && !resourceCompletedAgents.has(sub.agent)) {
            resourceCompletedAgents.add(sub.agent);
            if (mockProgressTimers[sub.agent]) { clearInterval(mockProgressTimers[sub.agent]); delete mockProgressTimers[sub.agent]; }
            if (headerRing) headerRing.setAttribute('stroke-dasharray', '100 0');
            if (headerStatus) headerStatus.textContent = '✓ 完成';
            if (skeleton) {
                skeleton.classList.add('is-completed');
                skeleton.classList.remove('is-running');
            }
            setTimeout(() => {
                if (skeleton) skeleton.classList.add('hidden');
                if (content) {
                    content.classList.remove('hidden');
                    content.innerHTML = renderResourceContent(sub.agent, sub.result);
                }
                if (window.lucide) lucide.createIcons();
                renderMermaidInResourceCard(acc);
                if (sub.agent === 'video_content') {
                    injectVideoPlayer(acc);
                }
            }, 300);
        } else if (sub.status === 'failed') {
            if (mockProgressTimers[sub.agent]) { clearInterval(mockProgressTimers[sub.agent]); delete mockProgressTimers[sub.agent]; }
            if (headerRing) headerRing.setAttribute('stroke-dasharray', '100 0');
            if (headerStatus) headerStatus.textContent = '✗ 失败';
            if (skeleton) {
                skeleton.classList.add('is-failed');
                skeleton.classList.remove('is-running');
            }
            setTimeout(() => {
                if (skeleton) skeleton.classList.add('hidden');
                if (content) {
                    content.classList.remove('hidden');
                    content.innerHTML = renderResourceError(sub.agent, sub.error);
                }
                if (window.lucide) lucide.createIcons();
            }, 300);
        } else {
            const progress = sub.progress || 0;
            const agentStartTime = resourceAgentStartTimes[sub.agent] || resourcePollingStartTime;
            const agentElapsed = Date.now() - agentStartTime;

            if (sub.agent === 'video_content' && progress === 0 && agentElapsed > RESOURCE_SHORT_TIMEOUT) {
                if (agentElapsed > RESOURCE_LONG_TIMEOUT) {
                    if (headerRing) headerRing.setAttribute('stroke-dasharray', '100 0');
                    if (headerStatus) headerStatus.textContent = '✗ 超时';
                    if (skeleton) {
                        skeleton.classList.add('is-failed');
                        skeleton.classList.remove('is-running');
                    }
                    setTimeout(() => {
                        if (skeleton) skeleton.classList.add('hidden');
                        if (content) {
                            content.classList.remove('hidden');
                            content.innerHTML = renderResourceError(sub.agent, '视频生成超时，请重试');
                        }
                    }, 300);
                } else {
                    if (headerRing) headerRing.setAttribute('stroke-dasharray', '100 0');
                    if (headerStatus) headerStatus.textContent = '✓ 就绪';
                    if (skeleton) {
                        skeleton.classList.add('is-completed');
                        skeleton.classList.remove('is-running');
                    }
                    setTimeout(() => {
                        if (skeleton) skeleton.classList.add('hidden');
                        if (content) {
                            content.classList.remove('hidden');
                            content.innerHTML = renderResourceContent(sub.agent, {
                                text_content: '视频资源正在后台生成中，以下为预览播放器：',
                                resources: []
                            });
                        }
                        injectVideoPlayer(acc);
                    }, 300);
                }
            } else {
                if (headerRing) headerRing.setAttribute('stroke-dasharray', `${progress} ${100 - progress}`);
                if (skeleton) {
                    if (sub.status === 'running') skeleton.classList.add('is-running');
                    const bodyStatus = skeleton.querySelector('.resource-skeleton-status');
                    if (bodyStatus) {
                        const phase = getResourcePhase(sub.agent, progress);
                        const statusLabel = sub.status === 'running' ? `正在${phase}` : '排队中';
                        bodyStatus.textContent = `${statusLabel} ${progress}%`;
                    }
                }
                if (headerStatus) {
                    const phase = getResourcePhase(sub.agent, progress);
                    const statusLabel = sub.status === 'running' ? `${phase}` : '排队中';
                    headerStatus.textContent = `${statusLabel} ${progress}%`;
                }
            }
        }
    }
}

function startMockProgress(agentName, duration) {
    if (mockProgressTimers[agentName]) clearInterval(mockProgressTimers[agentName]);
    const acc = document.querySelector(`.resource-accordion[data-resource="${agentName}"]`);
    if (!acc) return;
    acc.dataset.status = 'running';
    const skeleton = acc.querySelector('.accordion-body .resource-skeleton');
    if (skeleton) skeleton.classList.add('is-running');

    let progress = 0;
    const step = 12 + Math.floor(Math.random() * 6);
    const intervalMs = 300 + Math.floor(Math.random() * 200);

    const timer = setInterval(() => {
        progress = Math.min(progress + step, 100);

        const headerRing = acc.querySelector('.accordion-ring .ring-progress');
        const headerStatus = acc.querySelector('.accordion-header-right .resource-skeleton-status');
        const bodyStatus = acc.querySelector('.accordion-body .resource-skeleton-status');

        if (headerRing) headerRing.setAttribute('stroke-dasharray', `${progress} ${100 - progress}`);
        const phase = getResourcePhase(agentName, progress);
        const label = `正在${phase} ${progress}%`;
        if (headerStatus) headerStatus.textContent = label;
        if (bodyStatus) bodyStatus.textContent = label;

        if (progress >= 100) {
            clearInterval(timer);
            delete mockProgressTimers[agentName];
            acc.dataset.status = 'completed';
            const content = acc.querySelector('.accordion-body .resource-content');

            if (headerRing) headerRing.setAttribute('stroke-dasharray', '100 0');
            if (headerStatus) headerStatus.textContent = '✓ 完成';
            if (skeleton) { skeleton.classList.add('is-completed', 'hidden'); skeleton.classList.remove('is-running'); }
            if (content) {
                content.classList.remove('hidden');
                content.innerHTML = renderResourceContent(agentName, { text_content: getMockResult(agentName), resources: [] });
            }
            if (window.lucide) lucide.createIcons();
            renderMermaidInResourceCard(acc);
            if (agentName === 'video_content') injectVideoPlayer(acc);
        }
    }, intervalMs);
    mockProgressTimers[agentName] = timer;
}

function getMockResult(agentName) {
    const mockResults = {
        document_generator: '## 大数据技术概述\n\n### 1. HDFS架构\nHDFS采用主从架构，NameNode管理元数据，DataNode存储实际数据块。\n\n### 2. MapReduce模型\nMap阶段并行处理输入分片，Reduce阶段聚合中间结果。\n\n### 3. Spark生态\n基于内存计算，RDD为核心抽象，支持SQL、流处理和机器学习。',
        mindmap_generator: '```mermaid\ngraph TD\n    A[大数据技术] --> B[HDFS]\n    A --> C[MapReduce]\n    A --> D[Spark]\n    B --> B1[NameNode]\n    B --> B2[DataNode]\n    C --> C1[Map]\n    C --> C2[Reduce]\n    D --> D1[RDD]\n    D --> D2[DataFrame]\n```',
        video_content: '视频资源已生成，包含HDFS架构讲解和MapReduce工作原理的动画演示。',
        exercise_generator: '```python\nfrom pyspark import SparkContext\n\nsc = SparkContext("local", "WordCount")\n\ntext = sc.parallelize(["hello spark", "hello world"])\nwords = text.flatMap(lambda line: line.split())\nword_counts = words.map(lambda w: (w, 1)).reduceByKey(lambda a, b: a + b)\n\nprint(word_counts.collect())\n# Output: [("hello", 2), ("spark", 1), ("world", 1)]\n```',
    };
    return mockResults[agentName] || '资源生成完成';
}

function injectVideoPlayer(acc) {
    const body = acc.querySelector('.accordion-body-inner');
    if (!body) return;
    const existingThumb = body.querySelector('.resource-video-thumb');
    if (existingThumb) {
        const playerWrap = document.createElement('div');
        playerWrap.className = 'resource-video-player';
        playerWrap.innerHTML = `<video controls preload="metadata" poster="" style="width:100%;border-radius:8px;">
            <source src="https://www.w3schools.com/html/mov_bbb.mp4" type="video/mp4">
            您的浏览器不支持视频播放
        </video>`;
        existingThumb.replaceWith(playerWrap);
        return;
    }
    const existingContent = body.querySelector('.resource-content-body');
    if (existingContent) {
        const playerWrap = document.createElement('div');
        playerWrap.className = 'resource-video-player';
        playerWrap.style.marginTop = '8px';
        playerWrap.innerHTML = `<video controls preload="metadata" style="width:100%;border-radius:8px;">
            <source src="https://www.w3schools.com/html/mov_bbb.mp4" type="video/mp4">
            您的浏览器不支持视频播放
        </video>`;
        existingContent.appendChild(playerWrap);
    }
}

function renderResourceContent(agentName, result) {
    const config = RESOURCE_CONFIG[agentName];
    if (!config) return '';

    let bodyHtml = '';

    if (agentName === 'mindmap_generator' && result) {
        const textContent = result.text_content || '';
        const mermaidMatch = textContent.match(/```mermaid\s*\n([\s\S]*?)```/);
        if (mermaidMatch) {
            bodyHtml = `<div class="mermaid-placeholder">${escapeHtml(mermaidMatch[1].trim())}</div>`;
        } else {
            bodyHtml = `<div style="color:var(--text-tertiary);font-size:10px;">${escapeHtml(textContent.slice(0, 200))}</div>`;
        }
    } else if (agentName === 'video_content' && result) {
        bodyHtml = `<div class="resource-video-player">
            <video controls preload="metadata" style="width:100%;border-radius:8px;">
                <source src="https://www.w3schools.com/html/mov_bbb.mp4" type="video/mp4">
                您的浏览器不支持视频播放
            </video>
        </div>`;
        if (result.resources && result.resources.length > 0) {
            bodyHtml += `<div style="font-size:9px;color:var(--text-tertiary);margin-top:4px;">${result.resources.length} 个视频资源</div>`;
        }
    } else if (agentName === 'exercise_generator' && result) {
        const textContent = result.text_content || '';
        const codeMatch = textContent.match(/```(?:python|java|cpp|c|javascript|go|sql|scala|rust)?\s*\n([\s\S]*?)```/);
        if (codeMatch) {
            bodyHtml = `<pre><code>${escapeHtml(codeMatch[1])}</code></pre>
                <button class="resource-copy-btn" onclick="copyResourceCode(this)" aria-label="复制代码">
                    <i data-lucide="copy" class="w-2.5 h-2.5 inline -mt-0.5"></i> 复制
                </button>`;
        } else {
            bodyHtml = `<div style="color:var(--text-tertiary);font-size:10px;">${escapeHtml(textContent.slice(0, 200))}</div>`;
        }
    } else if (agentName === 'document_generator' && result) {
        const textContent = result.text_content || '';
        bodyHtml = `<div style="color:var(--text-secondary);font-size:10px;line-height:1.6;white-space:pre-wrap;">${escapeHtml(textContent.slice(0, 300))}${textContent.length > 300 ? '...' : ''}</div>`;
    } else if (result) {
        const textContent = result.text_content || JSON.stringify(result).slice(0, 200);
        bodyHtml = `<div style="color:var(--text-tertiary);font-size:10px;">${escapeHtml(textContent)}</div>`;
    }

    return `<div class="resource-content-header">
        <i data-lucide="${config.icon}" class="w-3.5 h-3.5" style="color: ${config.color}"></i>
        <span class="resource-content-title">${config.title}</span>
        <span class="resource-content-badge">✓ 已生成</span>
    </div>
    <div class="resource-content-body">${bodyHtml}</div>`;
}

function renderResourceError(agentName, errorMsg) {
    const config = RESOURCE_CONFIG[agentName];
    if (!config) return '';

    return `<div class="resource-error">
        <i data-lucide="alert-circle" class="w-5 h-5 text-red-400"></i>
        <span class="resource-error-msg">${escapeHtml(errorMsg || '生成失败')}</span>
        <button class="resource-retry-btn" onclick="retryResourceAgent('${agentName}')" aria-label="重试${config.title}生成">
            <i data-lucide="refresh-cw" class="w-2.5 h-2.5 inline -mt-0.5"></i> 重试
        </button>
    </div>`;
}

function copyResourceCode(btn) {
    const pre = btn.previousElementSibling;
    if (!pre) return;
    const code = pre.textContent;
    navigator.clipboard.writeText(code).then(() => {
        btn.innerHTML = '<i data-lucide="check" class="w-2.5 h-2.5 inline -mt-0.5"></i> 已复制';
        if (window.lucide) lucide.createIcons();
        setTimeout(() => {
            btn.innerHTML = '<i data-lucide="copy" class="w-2.5 h-2.5 inline -mt-0.5"></i> 复制';
            if (window.lucide) lucide.createIcons();
        }, 2000);
    });
}

async function retryResourceAgent(agentName) {
    if (!currentResourceTaskId) return;
    const acc = document.querySelector(`.resource-accordion[data-resource="${agentName}"]`);
    if (!acc) return;

    acc.dataset.status = 'running';
    const content = acc.querySelector('.accordion-body .resource-content');
    const skeleton = acc.querySelector('.accordion-body .resource-skeleton');
    if (content) content.classList.add('hidden');
    if (skeleton) {
        skeleton.classList.remove('hidden', 'is-completed', 'is-failed');
        skeleton.classList.add('is-running');
        const statusEl = skeleton.querySelector('.resource-skeleton-status');
        if (statusEl) statusEl.textContent = '重试中 0%';
    }
    const headerRing = acc.querySelector('.accordion-ring .ring-progress');
    if (headerRing) headerRing.setAttribute('stroke-dasharray', '0 100');
    const headerStatus = acc.querySelector('.accordion-header-right .resource-skeleton-status');
    if (headerStatus) headerStatus.textContent = '重试中 0%';
    resourceCompletedAgents.delete(agentName);

    if (!resourcePollingTimer) {
        resourcePollingBackoff = 0;
        pollResourceStatus();
    }
}

async function renderMermaidInResourceCard(card) {
    if (!window.mermaid) return;
    const placeholders = card.querySelectorAll('.mermaid-placeholder');
    for (let i = 0; i < placeholders.length; i++) {
        const div = placeholders[i];
        if (div.dataset.rendered) continue;
        div.dataset.rendered = 'true';
        const txt = document.createElement('textarea');
        txt.innerHTML = div.innerHTML;
        let code = txt.value.trim();
        const id = `mermaid-res-${Date.now()}-${i}`;
        try {
            code = code.replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>');
            const { svg } = await mermaid.render(id, code);
            div.innerHTML = svg;
        } catch (e) {
            console.warn("Mermaid render error (resource):", e);
            div.style.display = 'none';
            const errEl = document.getElementById('d' + id);
            if (errEl) errEl.remove();
        }
        div.classList.remove('mermaid-placeholder');
        div.classList.add('mermaid-rendered');
    }
}

function getAgentColor(agentName) {
    for (const [key, color] of Object.entries(AGENT_COLORS)) {
        if (agentName.includes(key)) return color;
    }
    return DEFAULT_AGENT_COLOR;
}

function getAgentLabel(agentName) {
    for (const [key, label] of Object.entries(AGENT_LABELS)) {
        if (agentName.includes(key)) return label;
    }
    return agentName;
}

function updateSandboxStatus(status, color) {
    const el = document.getElementById('sandbox-status');
    if (!el) return;
    el.textContent = status;
    el.className = `text-[10px] px-2 py-0.5 rounded-full font-semibold ${color || 'bg-gray-200 text-gray-500'}`;
}

function renderFlowNodes() {
    const container = document.getElementById('flow-node-container');
    if (!container) return;

    const pipeline = FLOW_PIPELINE.filter(name => activeAgents.has(name) || name === 'system');
    if (pipeline.length === 0) {
        container.innerHTML = '<span class="text-xs text-gray-400">等待智能体启动...</span>';
        return;
    }

    container.innerHTML = pipeline.map((name, i) => {
        const color = getAgentColor(name);
        const label = getAgentLabel(name);
        const isActive = activeAgents.has(name);
        const dotClass = isActive ? color.dot : 'bg-gray-300';
        const opacityClass = isActive ? '' : 'opacity-40';
        const connector = i < pipeline.length - 1 ? '<i data-lucide="chevron-right" class="w-3 h-3 text-gray-300 shrink-0"></i>' : '';
        return `<div class="flex items-center gap-1 ${opacityClass}">
            <div class="flex items-center gap-1 px-2 py-1 rounded-full ${color.bg} border ${color.border} transition-all duration-300">
                <div class="w-1.5 h-1.5 rounded-full ${dotClass} ${isActive ? 'animate-pulse' : ''}"></div>
                <span class="text-[10px] font-semibold ${color.text} whitespace-nowrap">${label}</span>
            </div>
            ${connector}
        </div>`;
    }).join('');

    if (window.lucide) lucide.createIcons();
}

function renderSandboxLog(log, prepend) {
    const container = document.getElementById('sandbox-logs');
    if (!container) return;

    if (sandboxFilterSet.size > 0 && !sandboxFilterSet.has(log.agent)) return;

    const searchInput = document.getElementById('sandbox-search-input');
    const searchTerm = searchInput ? searchInput.value.trim().toLowerCase() : '';
    if (searchTerm && !log.content.toLowerCase().includes(searchTerm) && !log.agent.toLowerCase().includes(searchTerm)) return;

    const color = getAgentColor(log.agent);
    const label = getAgentLabel(log.agent);
    const time = log.timestamp ? new Date(log.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '';

    const bubble = document.createElement('div');
    bubble.className = `agent-bubble ${color.bg} border ${color.border} rounded-xl p-2.5 transition-all duration-300 animate-slide-up`;
    bubble.dataset.agent = log.agent;
    bubble.innerHTML = `
        <div class="flex items-center gap-1.5 mb-1">
            <div class="w-2 h-2 rounded-full ${color.dot} shrink-0"></div>
            <span class="text-[11px] font-bold ${color.text}">${escapeHtml(label)}</span>
            ${time ? `<span class="text-[9px] text-gray-400 ml-auto">${time}</span>` : ''}
        </div>
        <div class="text-[11px] text-gray-600 leading-relaxed pl-3.5">${escapeHtml(log.content)}</div>
    `;

    if (prepend && container.firstChild) {
        container.insertBefore(bubble, container.firstChild);
    } else {
        container.appendChild(bubble);
    }
    container.scrollTop = container.scrollHeight;
}

function renderAllSandboxLogs() {
    const container = document.getElementById('sandbox-logs');
    if (!container) return;
    container.innerHTML = '';
    sandboxLogs.forEach(log => renderSandboxLog(log, false));
}

function renderFilterChips() {
    const container = document.getElementById('sandbox-filter-chips');
    if (!container) return;

    const agents = [...new Set(sandboxLogs.map(l => l.agent))];
    container.innerHTML = agents.map(agent => {
        const color = getAgentColor(agent);
        const label = getAgentLabel(agent);
        const isActive = sandboxFilterSet.has(agent);
        return `<button class="text-[10px] px-2 py-0.5 rounded-full border font-semibold transition-all duration-200 ${isActive ? color.bg + ' ' + color.text + ' ' + color.border : 'text-[var(--text-tertiary)] border-[var(--border-glass)]'}" data-filter-agent="${agent}">${label}</button>`;
    }).join('');

    container.querySelectorAll('[data-filter-agent]').forEach(btn => {
        btn.addEventListener('click', () => {
            const agent = btn.dataset.filterAgent;
            if (sandboxFilterSet.has(agent)) {
                sandboxFilterSet.delete(agent);
            } else {
                sandboxFilterSet.add(agent);
            }
            renderFilterChips();
            renderAllSandboxLogs();
        });
    });
}

function startTypewriter(text) {
    typewriterQueue.push(text);
    if (!isTypewriting) {
        processTypewriterQueue();
    }
}

function processTypewriterQueue() {
    if (typewriterQueue.length === 0) {
        isTypewriting = false;
        return;
    }

    isTypewriting = true;
    const text = typewriterQueue.shift();

    let charIdx = 0;
    const speed = 18;
    const batchSize = 3;

    function typeNext() {
        if (charIdx >= text.length) {
            processTypewriterQueue();
            return;
        }

        const end = Math.min(charIdx + batchSize, text.length);
        currentAssistantContent += text.slice(charIdx, end);
        charIdx = end;

        if (currentAssistantIdx >= 0 && currentAssistantIdx < messages.length) {
            messages[currentAssistantIdx].content = currentAssistantContent;
        }

        requestAnimationFrame(() => {
            renderStreamingMessage();
        });

        typewriterTimer = setTimeout(typeNext, speed);
    }

    typeNext();
}

function renderStreamingMessage() {
    const container = document.getElementById('chat-container');
    if (!container) return;

    let streamBubble = container.querySelector('.stream-bubble');
    if (!streamBubble) return;

    const processedContent = preprocessContent(currentAssistantContent);
    let htmlContent = window.marked ? marked.parse(processedContent) : currentAssistantContent;
    htmlContent = processDocRefs(htmlContent);

    const isSocratic = messages[currentAssistantIdx]?.socratic;
    const headerHtml = `<span class="text-xs mb-1 ml-1 flex items-center gap-1 font-bold" style="color: var(--primary);"><i data-lucide="bot" class="w-3 h-3"></i> 智能辅导团队 ${isSocratic ? '<span class="socratic-badge"><i data-lucide="help-circle" style="width:10px;height:10px;display:inline;"></i> 苏格拉底诊断</span>' : ''}</span>`;

    streamBubble.innerHTML = `<div class="max-w-[90%] flex flex-col items-start min-w-0">${headerHtml}<div class="msg-bubble p-4 rounded-2xl msg-bubble-bot rounded-tl-none w-full min-w-0 overflow-x-auto"><div class="prose prose-sm max-w-none break-words whitespace-pre-wrap">${htmlContent}<span class="typing-cursor-inline"></span></div></div></div>`;

    const chatScroll = container.closest('.chat-glass-scroll') || container;
    const isNearBottom = chatScroll.scrollHeight - chatScroll.scrollTop - chatScroll.clientHeight < 150;
    if (isNearBottom) {
        chatScroll.scrollTop = chatScroll.scrollHeight;
    }

    if (window.lucide) lucide.createIcons();
    renderMermaidInBubble(streamBubble);
}

function renderMermaidInBubble(container) {
    if (!window.mermaid) return;
    const placeholders = container.querySelectorAll('.mermaid-placeholder');
    placeholders.forEach(async (div, i) => {
        if (div.dataset.rendered) return;
        div.dataset.rendered = 'true';
        const txt = document.createElement("textarea");
        txt.innerHTML = div.innerHTML;
        let code = txt.value.trim();
        const id = `mermaid-stream-${Date.now()}-${i}`;
        try {
            code = code.replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>');
            const { svg } = await mermaid.render(id, code);
            div.innerHTML = svg;
        } catch (e) {
            console.warn("Mermaid render error (bubble):", e);
            div.style.display = 'none';
            const errEl = document.getElementById('d' + id);
            if (errEl) errEl.remove();
        }
        div.classList.remove('mermaid-placeholder');
    });
}

function getInputValue() {
    const notionInput = document.getElementById('notion-input');
    if (notionInput) {
        const text = notionInput.innerText.trim();
        return text;
    }
    const msgInput = document.getElementById('message-input');
    return msgInput ? msgInput.value.trim() : '';
}

function clearInput() {
    const notionInput = document.getElementById('notion-input');
    if (notionInput) {
        notionInput.innerHTML = '';
        notionInput.style.height = 'auto';
        return;
    }
    const msgInput = document.getElementById('message-input');
    if (msgInput) msgInput.value = '';
}

function setInputDisabled(disabled) {
    const notionInput = document.getElementById('notion-input');
    if (notionInput) {
        notionInput.contentEditable = disabled ? 'false' : 'true';
        notionInput.style.opacity = disabled ? '0.5' : '1';
        return;
    }
    const msgInput = document.getElementById('message-input');
    if (msgInput) msgInput.disabled = disabled;
}

function toggleLeftCol() {
    const col = document.getElementById('left-col');
    if (col) col.classList.toggle('show');
}

function toggleRightCol() {
    const col = document.getElementById('right-col');
    if (col) col.classList.toggle('show');
}

function updateAgentStatus(agentKey, status) {
    const item = document.querySelector(`.agent-status-item[data-agent="${agentKey}"]`);
    if (!item) return;
    const dot = item.querySelector('.agent-status-dot');
    const label = item.querySelector('.agent-status-label');
    if (!dot || !label) return;

    dot.className = 'agent-status-dot';
    if (status === 'active') {
        dot.classList.add('agent-dot-active');
        label.textContent = '运行中';
        label.className = 'agent-status-label active';
    } else if (status === 'idle') {
        dot.classList.add('agent-dot-idle');
        label.textContent = '待命';
        label.className = 'agent-status-label';
    } else if (status === 'warning') {
        dot.classList.add('agent-dot-warning');
        label.textContent = '等待';
        label.className = 'agent-status-label';
    } else if (status === 'error') {
        dot.classList.add('agent-dot-error');
        label.textContent = '异常';
        label.className = 'agent-status-label';
    }
}

function renderPathTree() {
    const container = document.getElementById('path-tree-container');
    if (!container) return;

    if (!currentPath || currentPath.length === 0) {
        container.innerHTML = '<div class="text-xs text-gray-400 py-4 text-center">暂无学习路径</div>';
        return;
    }

    container.innerHTML = currentPath.map((node, idx) => {
        const status = node.status || 'locked';
        const dotClass = status === 'completed' ? 'completed' : status === 'in_progress' ? 'in-progress' : 'locked';
        const isImportant = node.importance === 'high' || node.importance === 'core';
        const hasChildren = node.children && node.children.length > 0;
        const time = node.estimated_time || node.estimatedMinutes || '';
        const displayName = node.topic || node.name || node.title || '学习任务';

        let html = `<div class="path-tree-node" data-idx="${idx}" onclick="onPathNodeClick(${idx})" tabindex="0" role="treeitem" aria-label="${escapeHtml(displayName)}">
            ${hasChildren ? '<i data-lucide="chevron-right" class="w-3 h-3 path-tree-toggle"></i>' : '<span class="w-3"></span>'}
            <div class="path-tree-node-dot ${dotClass}"></div>
            <span class="text-gray-700">${escapeHtml(displayName)}</span>
            ${isImportant ? '<span class="path-tree-badge important">核心</span>' : ''}
            ${time ? `<span class="path-tree-time">${time}min</span>` : ''}
        </div>`;

        if (hasChildren) {
            html += `<div class="path-tree-children">`;
            for (const child of node.children) {
                const cStatus = child.status || 'locked';
                const cDotClass = cStatus === 'completed' ? 'completed' : cStatus === 'in_progress' ? 'in-progress' : 'locked';
                const childName = child.topic || child.name || child.title || '子节点';
                html += `<div class="path-tree-node" tabindex="0" role="treeitem" aria-label="${escapeHtml(childName)}">
                    <span class="w-3"></span>
                    <div class="path-tree-node-dot ${cDotClass}"></div>
                    <span class="text-gray-600">${escapeHtml(childName)}</span>
                </div>`;
            }
            html += '</div>';
        }
        return html;
    }).join('');

    if (window.lucide) lucide.createIcons();
}

function onPathNodeClick(idx) {
    const node = currentPath[idx];
    if (!node) return;
    const toggle = document.querySelector(`.path-tree-node[data-idx="${idx}"] .path-tree-toggle`);
    if (toggle) toggle.classList.toggle('expanded');
    const children = document.querySelector(`.path-tree-node[data-idx="${idx}"] + .path-tree-children`);
    if (children) children.style.display = children.style.display === 'none' ? '' : 'none';
}

async function handleSendStream() {
    const sendButton = document.getElementById('send-btn');
    const userMsg = getInputValue();
    if (!userMsg) return;

    ensureCurrentPathValid();
    clearInput();
    setInputDisabled(true);
    if (sendButton) sendButton.disabled = true;

    messages.push({ role: 'user', content: userMsg });
    renderMessages();

    sandboxLogs = [];
    activeAgents = new Set();
    sandboxFilterSet = new Set();
    stopResourcePolling();
    hideResourceDashboard();
    const sandboxLogsEl = document.getElementById('sandbox-logs');
    if (sandboxLogsEl) sandboxLogsEl.innerHTML = '';
    renderFlowNodes();
    renderFilterChips();
    updateSandboxStatus('调度中', 'bg-amber-100 text-amber-600');

    currentAssistantContent = '';
    messages.push({ role: 'assistant', content: '', socratic: false });
    currentAssistantIdx = messages.length - 1;

    const chatContainer = document.getElementById('chat-container');
    if (chatContainer) {
        const streamDiv = document.createElement('div');
        streamDiv.className = 'msg-row flex justify-start stream-bubble';
        chatContainer.appendChild(streamDiv);
    }

    if (typewriterTimer) {
        clearTimeout(typewriterTimer);
        typewriterTimer = null;
    }
    typewriterQueue = [];
    isTypewriting = false;

    streamAbortController = new AbortController();

    try {
        const res = await fetch(STREAM_API_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                student_id: String(currentUser?.id || 'anonymous'),
                course_id: 'bigdata',
                user_input: userMsg,
                context_id: '',
                current_profile: profile,
                current_path: currentPath,
                interaction_count: evaluation.interactionCount || 0,
                code_practice_time: evaluation.codePracticeTime || 0,
                socratic_pass_rate: evaluation.socraticPassRate || 0,
                system_prompt: getAgentSystemPrompt()
            }),
            signal: streamAbortController.signal
        });

        if (!res.ok) {
            const errText = await res.text();
            let errMsg = `请求失败（HTTP ${res.status}）`;
            try {
                const errData = JSON.parse(errText);
                errMsg = formatApiErrorDetail(errData.detail) || errMsg;
            } catch {}
            throw new Error(errMsg);
        }

        updateSandboxStatus('运行中', 'bg-emerald-100 text-emerald-600');

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let renderThrottleTimer = null;
        let pendingRender = false;

        function throttledRender() {
            if (pendingRender) return;
            pendingRender = true;
            requestAnimationFrame(() => {
                renderStreamingMessage();
                pendingRender = false;
            });
        }

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (line.startsWith(': ')) continue;
                if (!line.startsWith('data: ')) continue;
                const jsonStr = line.slice(6).trim();
                if (!jsonStr) continue;

                let event;
                try {
                    event = JSON.parse(jsonStr);
                } catch {
                    continue;
                }

                if (event.type === 'agent_log') {
                    const logEntry = {
                        agent: event.agent || 'unknown',
                        content: event.content || '',
                        timestamp: Date.now()
                    };
                    sandboxLogs.push(logEntry);
                    activeAgents.add(logEntry.agent);
                    updateAgentStatus(logEntry.agent, 'active');
                    renderSandboxLog(logEntry, false);
                    renderFlowNodes();
                    renderFilterChips();
                } else if (event.type === 'content_chunk') {
                    startTypewriter(event.content || '');
                } else if (event.type === 'complete') {
                    if (typewriterTimer) {
                        clearTimeout(typewriterTimer);
                        typewriterTimer = null;
                    }
                    typewriterQueue = [];
                    isTypewriting = false;

                    const data = event.data;
                    if (data.newProfile) {
                        profile = { ...profile, ...data.newProfile };
                    }
                    renderProfile();
                    renderRadarChart();

                    if (data.newPath) {
                        currentPath = normalizeLearningPath(data.newPath);
                        renderPath();
                    }

                    if (data.evaluation) {
                        evaluation = data.evaluation;
                        renderEvaluation();
                    }

                    if (data.dispatchStrategy) {
                        updateDispatchBadge(data.dispatchStrategy);
                        if (currentAssistantIdx >= 0) {
                            messages[currentAssistantIdx].socratic = data.dispatchStrategy === 'socratic';
                        }
                    }

                    if (data.sources) {
                        renderSources(data.sources);
                    }

                    if (data.sourceLinks) {
                        updateSourceLinks(data.sourceLinks);
                        if (data.sources) renderSources(data.sources);
                    }

                    if (data.resourceTaskId) {
                        startResourcePolling(data.resourceTaskId);
                    }

                    if (currentAssistantIdx >= 0) {
                        messages[currentAssistantIdx].content = currentAssistantContent;
                    }

                    if (isProgrammingTask(currentAssistantContent)) {
                        autoFillTask(currentAssistantContent);
                    }

                    updateSandboxStatus('完成', 'bg-green-100 text-green-600');
                    document.querySelectorAll('.agent-status-item').forEach(item => {
                        const dot = item.querySelector('.agent-status-dot');
                        const label = item.querySelector('.agent-status-label');
                        if (dot) dot.className = 'agent-status-dot agent-dot-idle';
                        if (label) { label.textContent = '待命'; label.className = 'agent-status-label'; }
                    });
                    renderMessages();
                    saveProgress();
                } else if (event.type === 'error') {
                    const logEntry = {
                        agent: 'error',
                        content: event.message || '未知错误',
                        timestamp: Date.now()
                    };
                    sandboxLogs.push(logEntry);
                    renderSandboxLog(logEntry, false);
                    updateSandboxStatus('错误', 'bg-red-100 text-red-600');

                    if (!currentAssistantContent) {
                        if (currentAssistantIdx >= 0) {
                            messages[currentAssistantIdx].content = `抱歉，智能体处理失败：${event.message || '未知错误'}。请稍后重试。`;
                        }
                        renderMessages();
                    }
                }
            }
        }
    } catch (error) {
        if (error.name === 'AbortError') return;
        const errMsg = error instanceof Error ? error.message : String(error);
        console.error('[Stream] Request failed:', errMsg);
        const logEntry = {
            agent: 'error',
            content: errMsg,
            timestamp: Date.now()
        };
        sandboxLogs.push(logEntry);
        renderSandboxLog(logEntry, false);
        updateSandboxStatus('错误', 'bg-red-100 text-red-600');

        let userMsg = '抱歉，请求失败。';
        if (errMsg.includes('Failed to fetch') || errMsg.includes('NetworkError')) {
            userMsg = '无法连接到服务器，请确认后端服务已启动（python main.py）。';
        } else if (errMsg.includes('HTTP 404')) {
            userMsg = 'API接口未找到(404)，请确认后端服务版本正确。';
        } else if (errMsg.includes('HTTP 5')) {
            userMsg = `服务器内部错误：${errMsg}。请稍后重试。`;
        } else {
            userMsg = `请求失败：${errMsg}。请稍后重试。`;
        }

        if (!currentAssistantContent) {
            if (currentAssistantIdx >= 0) {
                messages[currentAssistantIdx].content = userMsg;
            }
            renderMessages();
        }
    } finally {
        setInputDisabled(false);
        if (sendButton) sendButton.disabled = false;
        const notionInput = document.getElementById('notion-input');
        if (notionInput) notionInput.focus();
        else { const mi = document.getElementById('message-input'); if (mi) mi.focus(); }
        streamAbortController = null;
    }
}

async function handleSend() {
    const sendButton = document.getElementById('send-btn');
    const userMsg = getInputValue();
    if (!userMsg) return;

    ensureCurrentPathValid();
    clearInput();
    setInputDisabled(true);
    if (sendButton) sendButton.disabled = true;
    
    messages.push({ role: 'user', content: userMsg });
    renderMessages();

    const langNeed = detectLanguageNeed(userMsg);

    const wfPanel = null;
    const wfLogs = null;
    sandboxLogs = [];
    activeAgents = new Set();
    const sandboxLogsEl = document.getElementById('sandbox-logs');
    if (sandboxLogsEl) sandboxLogsEl.innerHTML = '';
    updateSandboxStatus('处理中', 'bg-amber-100 text-amber-600');

    try {
        const res = await fetch(API_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                userText: userMsg,
                currentProfile: profile,
                currentPath: currentPath,
                interactionCount: evaluation.interactionCount,
                codePracticeTime: evaluation.codePracticeTime,
                socraticPassRate: evaluation.socraticPassRate
            })
        });

        const rawText = await res.text();
        let data = {};
        if (rawText) {
            try {
                data = JSON.parse(rawText);
            } catch {
                throw new Error(`服务器返回非 JSON（HTTP ${res.status}）：${rawText.slice(0, 240)}`);
            }
        }
        if (!res.ok) {
            const msg = formatApiErrorDetail(data.detail) || `请求失败（HTTP ${res.status}）`;
            throw new Error(msg);
        }

        const logs = Array.isArray(data.logs) ? data.logs : [];

        const applyChatResponse = () => {
            if (data.newProfile && typeof data.newProfile === 'object') {
                profile = { ...profile, ...data.newProfile };
            }
            renderProfile();
            renderRadarChart();

            if (data.newPath != null) {
                currentPath = normalizeLearningPath(data.newPath);
                renderPath();
            }

            if (data.evaluation) {
                evaluation = data.evaluation;
                renderEvaluation();
            }

            if (data.dispatchStrategy) {
                updateDispatchBadge(data.dispatchStrategy);
            }

            renderSources(data.sources || []);

            if (data.sourceLinks) {
                updateSourceLinks(data.sourceLinks);
                renderSources(data.sources || []);
            }

            const isSocratic = data.dispatchStrategy === 'socratic';
            messages.push({ role: 'assistant', content: data.content, socratic: isSocratic });
            renderMessages();

            if (isProgrammingTask(data.content)) {
                autoFillTask(data.content);
            }

            if (langNeed) {
                setTimeout(() => {
                    const langSelect = document.getElementById('lang-select');
                    if (langSelect) {
                        langSelect.value = langNeed;
                        changeLanguage();
                        if (!isProgrammingTask(data.content)) {
                            switchTab('code');
                        }
                    }
                }, 800);
            }

            setInputDisabled(false);
            if (sendButton) sendButton.disabled = false;
            msgInput.focus();

            saveProgress();
        };

        if (logs.length === 0) {
            applyChatResponse();
        } else {
            for (let i = 0; i < logs.length; i++) {
                const logText = logs[i];
                const agentMatch = logText.match(/^\[([^\]]+)\]/);
                const agentName = agentMatch ? agentMatch[1].toLowerCase().replace(/\s+/g, '_') : 'system';
                const logEntry = { agent: agentName, content: logText, timestamp: Date.now() };
                sandboxLogs.push(logEntry);
                activeAgents.add(agentName);
            }
            renderAllSandboxLogs();
            renderFlowNodes();
            renderFilterChips();
            updateSandboxStatus('完成', 'bg-green-100 text-green-600');
            setTimeout(applyChatResponse, 500);
        }
    } catch (error) {
        const text = error instanceof Error
            ? (typeof error.message === 'string' ? error.message : formatApiErrorDetail(error.message))
            : formatApiErrorDetail(error) || String(error);
        const logEntry = { agent: 'error', content: text, timestamp: Date.now() };
        sandboxLogs.push(logEntry);
        renderSandboxLog(logEntry, false);
        updateSandboxStatus('错误', 'bg-red-100 text-red-600');
        setInputDisabled(false);
        if (sendButton) sendButton.disabled = false;
    }
}

async function saveProgress() {
    if (!currentUser || !currentUser.id) return;
    ensureCurrentPathValid();
    try {
        const body = {
            userId: parseInt(currentUser.id),
            evaluation: evaluation,
            currentPath: currentPath,
            profile: profile
        };
        if (lastGradeRecord) {
            body.lastGradeRecord = lastGradeRecord;
        }
        const res = await fetch(SAVE_PROGRESS_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if (!res.ok) {
            const errData = await res.json();
            console.warn('保存进度失败:', res.status, errData);
        }
    } catch (error) {
        console.warn('保存进度失败:', error);
    }
}

function startCodePracticeTimer() {
    if (codePracticeStartTime === null) {
        codePracticeStartTime = Date.now();
        codePracticeTimer = setInterval(() => {
            const elapsed = Math.floor((Date.now() - codePracticeStartTime) / 1000);
            evaluation.codePracticeTime = Math.floor(elapsed / 60);
            renderEvaluation();
        }, 1000);
    }
}

function stopCodePracticeTimer() {
    if (codePracticeTimer) {
        clearInterval(codePracticeTimer);
        codePracticeTimer = null;
    }
    if (codePracticeStartTime !== null) {
        const elapsed = Math.floor((Date.now() - codePracticeStartTime) / 1000);
        evaluation.codePracticeTime = Math.floor(elapsed / 60);
        codePracticeStartTime = null;
        renderEvaluation();
        saveProgress();
    }
}

function updateAvatar(newAvatar) {
    currentUser.avatar = newAvatar;
    localStorage.setItem('starlearn_user', JSON.stringify(currentUser));
    updateUserUI();
    if (currentUser.id) {
        fetch(`${API_BASE}/api/user/update`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username: currentUser.username,
                avatar: newAvatar
            })
        });
    }
}

function updateNickname(newNickname) {
    currentUser.name = newNickname;
    localStorage.setItem('starlearn_user', JSON.stringify(currentUser));
    updateUserUI();
    if (currentUser.id) {
        fetch(`${API_BASE}/api/user/update`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username: currentUser.username,
                nickname: newNickname
            })
        });
    }
}

function showNicknameInput() {
    document.getElementById('avatar-dropdown').classList.remove('show');
    const modal = document.getElementById('nickname-modal');
    const input = document.getElementById('nickname-input');
    if (modal && input) {
        input.value = currentUser.name || '';
        modal.classList.remove('hidden');
    }
}

function hideNicknameInput() {
    const modal = document.getElementById('nickname-modal');
    if (modal) modal.classList.add('hidden');
}

function confirmNicknameChange() {
    const input = document.getElementById('nickname-input');
    if (!input) return;
    const newNickname = input.value.trim();
    if (!newNickname) {
        alert('请输入昵称');
        return;
    }
    if (newNickname.length > 20) {
        alert('昵称长度不能超过20个字符');
        return;
    }
    updateNickname(newNickname);
    hideNicknameInput();
}

async function loadProgress() {
    if (!currentUser || !currentUser.id) return;
    try {
        const res = await fetch(LOAD_PROGRESS_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ userId: parseInt(currentUser.id) })
        });
        const data = await res.json();
        if (data.success) {
            if (data.profile) {
                let incoming = data.profile;
                if (isRawAssessmentProfile(incoming)) {
                    const mapped = initProfileFromAssessment(incoming);
                    if (mapped) incoming = mapped;
                }
                profile = { ...profile, ...incoming };
            }
            if (data.evaluation) {
                evaluation = { ...evaluation, ...data.evaluation };
            }
            if (data.currentPath != null) {
                const loaded = normalizeLearningPath(data.currentPath);
                if (loaded.length > 0) currentPath = loaded;
            }
            if (data.lastGradeRecord) {
                lastGradeRecord = data.lastGradeRecord;
            }
            renderProfile();
            renderRadarChart();
            renderEvaluation();
            renderPath();
        }
    } catch (error) {
        console.warn('加载进度失败:', error);
    }
}

document.addEventListener('DOMContentLoaded', function() {
    const savedAgentId = localStorage.getItem('starlearn_agent');
    if (savedAgentId) {
        const savedAgent = AGENTS_CONFIG.find(a => a.id === savedAgentId);
        if (savedAgent) currentAgent = savedAgent;
    }
    renderAgentFab();

    const notionInput = document.getElementById('notion-input');
    const msgInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-btn');

    if (notionInput) {
        notionInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSendStream();
            }
        });
        notionInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 160) + 'px';
        });
    } else if (msgInput) {
        msgInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') handleSendStream();
        });
    }
    if (sendButton) {
        sendButton.addEventListener('click', handleSendStream);
    }

    const savedTheme = localStorage.getItem('starlearn_theme') || 'ocean';
    setTheme(savedTheme);
    DynamicThemeManager.init();

    const savedUser = JSON.parse(localStorage.getItem('starlearn_user') || 'null');
    if (savedUser) {
        currentUser = savedUser;

        // 从评估数据初始化画像
        if (savedUser.assessment) {
            const assessmentProfile = initProfileFromAssessment(savedUser.assessment);
            if (assessmentProfile) {
                profile = assessmentProfile;
            }
        } else if (savedUser.profile) {
            profile = { ...profile, ...savedUser.profile };
        }

        // 加载学习路径（可能是 JSON 字符串或非数组）
        if (savedUser.learningPath != null) {
            const lp = normalizeLearningPath(savedUser.learningPath);
            if (lp.length > 0) currentPath = lp;
        }
    }

    ensureCurrentPathValid();

    // ============================================
    // 学习上下文接收与应用逻辑
    // ============================================
    applyLearningContext();

    // 生成个性化欢迎消息
    const welcomeMsg = generateWelcomeMessage(savedUser?.assessment, profile);
    messages = [{ role: 'assistant', content: welcomeMsg }];

    updateUserUI();

    if (currentUser && currentUser.id) {
        loadProgress();
        window.proactiveTutor.connect(currentUser.id || currentUser.name || 'anonymous', currentUser.currentTask || 'bigdata');
    }

    if (window.marked && window.mermaid) {
        const renderer = new marked.Renderer();
        const originalCode = renderer.code.bind(renderer);
        renderer.code = function(arg1, arg2, arg3) {
            let code = typeof arg1 === 'object' ? arg1.text : arg1;
            let lang = typeof arg1 === 'object' ? arg1.lang : arg2;
            if (lang === 'mermaid' || (code && (code.trim().startsWith('graph ') || code.trim().startsWith('flowchart ') || code.trim().startsWith('sequenceDiagram')))) {
                const encodedCode = code.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
                return `<div class="mermaid-placeholder mermaid-container">${encodedCode}</div>`;
            }
            if (lang === 'micro-course') {
                const encodedCode = code.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
                return `<div class="micro-course-block">${encodedCode}</div>`;
            }
            return typeof arg1 === 'object' ? originalCode(arg1) : originalCode(arg1, arg2, arg3);
        };
        marked.use({ renderer: renderer });
        
        if (mermaid.mermaidAPI) {
            const origRender = mermaid.mermaidAPI.render;
            mermaid.mermaidAPI.render = function(id, code, cb, opts) {
                return origRender.call(this, id, code, function(svg, bindFunctions) {
                    if (cb) cb(svg, bindFunctions);
                }, { ...opts, suppressErrorRendering: true, errorCallback: function() {} });
            };
        }
        
        mermaid.initialize({
            startOnLoad: false,
            theme: 'default',
            securityLevel: 'loose',
            suppressErrorRendering: true,
            flowchart: { useMaxWidth: true, htmlLabels: true },
            sequence: { useMaxWidth: true },
            errorCallback: function() {}
        });
        
        const origParse = mermaid.parse;
        mermaid.parse = function(code) {
            return origParse.call(this, code).catch(function(e) {
                console.warn('Mermaid parse suppressed:', e);
                return null;
            });
        };
        
        // 彻底禁用Mermaid错误弹窗
        if (mermaid.parseError) {
            mermaid.parseError = function() {};
        }
        if (mermaid.mermaidAPI && mermaid.mermaidAPI.parseError) {
            mermaid.mermaidAPI.parseError = function() {};
        }
        
        // 覆盖Mermaid的错误处理
        if (window.mermaidConfig) {
            window.mermaidConfig = {
                ...window.mermaidConfig,
                suppressErrorRendering: true,
                errorCallback: function() {}
            };
        } else {
            window.mermaidConfig = {
                suppressErrorRendering: true,
                errorCallback: function() {}
            };
        }
    }

    const style = document.createElement('style');
    style.textContent = '.mermaid-error, [id^="mermaid-error-"], [class*="mermaid-error"], .mermaid-syntax-error, .mermaidErrorMessage, .mermaidError, .mermaid-syntaxError, .mermaid-error-container, .mermaid-error-message, #mermaid-syntax-error, #mermaid-error-dialog { display: none !important; visibility: hidden !important; height: 0 !important; overflow: hidden !important; position: absolute !important; z-index: -1 !important; opacity: 0 !important; pointer-events: none !important; }';
    document.head.appendChild(style);
    
    window.addEventListener('error', function(e) {
        if (e.message && (e.message.includes('mermaid') || e.message.includes('Mermaid'))) {
            e.preventDefault();
            e.stopPropagation();
            console.warn('Mermaid error suppressed:', e.message);
        }
    }, true);

    window.addEventListener('unhandledrejection', function(e) {
        const reason = e.reason;
        if (reason && ((reason.message && (reason.message.includes('mermaid') || reason.message.includes('Mermaid'))) || String(reason).includes('mermaid'))) {
            e.preventDefault();
            console.warn('Mermaid promise error suppressed:', reason);
        }
    });

    switchOutputTab('run');
    renderProfile();
    renderRadarChart();
    renderEvaluation();
    renderPath();
    renderMessages();

    let _radarResizeTimer = null;
    window.addEventListener('resize', () => {
        if (_radarResizeTimer) clearTimeout(_radarResizeTimer);
        _radarResizeTimer = setTimeout(() => { renderRadarChart(); }, 200);
    });

    if (window.sidebarManager) window.sidebarManager.init();

    const sandboxSearchToggle = document.getElementById('sandbox-search-toggle');
    const sandboxSearchBar = document.getElementById('sandbox-search-bar');
    const sandboxSearchInput = document.getElementById('sandbox-search-input');
    const sandboxFilterBtn = document.getElementById('sandbox-filter-btn');
    const sandboxFilterBar = document.getElementById('sandbox-filter-bar');
    const sandboxCollapseBtn = document.getElementById('sandbox-collapse-btn');

    if (sandboxSearchToggle && sandboxSearchBar) {
        sandboxSearchToggle.addEventListener('click', () => {
            sandboxSearchBar.classList.toggle('hidden');
            if (!sandboxSearchBar.classList.contains('hidden') && sandboxSearchInput) {
                sandboxSearchInput.focus();
            }
        });
    }

    if (sandboxSearchInput) {
        let searchDebounce = null;
        sandboxSearchInput.addEventListener('input', () => {
            clearTimeout(searchDebounce);
            searchDebounce = setTimeout(() => renderAllSandboxLogs(), 200);
        });
    }

    if (sandboxFilterBtn && sandboxFilterBar) {
        sandboxFilterBtn.addEventListener('click', () => {
            sandboxFilterBar.classList.toggle('hidden');
        });
    }

    if (sandboxCollapseBtn) {
        sandboxCollapseBtn.addEventListener('click', () => {
            const trackA = document.getElementById('track-a');
            if (trackA) {
                trackA.classList.toggle('h-[40vh]');
                trackA.classList.toggle('h-0');
                trackA.classList.toggle('overflow-hidden');
            }
        });
    }

    const dashboardCancelBtn = document.getElementById('dashboard-cancel-btn');
    if (dashboardCancelBtn) {
        dashboardCancelBtn.addEventListener('click', cancelResourceGeneration);
    }

    refreshLinkCacheFromBackend();
    setInterval(refreshLinkCacheFromBackend, 30 * 60 * 1000);

    if (window.LearningMonitor && currentUser) {
        window._learningMonitor = new LearningMonitor({
            enabled: true,
            studentId: String(currentUser.id || 'anonymous'),
            courseId: 'bigdata',
            onOverload: function(event) {
                if (event.score > 80) {
                    const toast = document.createElement('div');
                    toast.className = 'fixed top-4 left-1/2 transform -translate-x-1/2 px-6 py-3 rounded-2xl shadow-xl text-sm font-semibold z-[9999]';
                    toast.style.cssText = 'background: var(--warning); color: var(--text-on-accent); backdrop-filter: blur(16px);';
                    toast.innerHTML = '<i data-lucide="alert-triangle" class="w-4 h-4 inline mr-2"></i>检测到学习疲劳，建议休息一下再继续';
                    document.body.appendChild(toast);
                    if (window.lucide) lucide.createIcons();
                    setTimeout(() => { toast.style.transition = 'all 0.3s'; toast.style.opacity = '0'; setTimeout(() => toast.remove(), 300); }, 3000);
                }
            }
        });
        window._learningMonitor.start();
    }

    if (window.lightboxManager) {
        window.lightboxManager.init();
    }

    if (window.focusDurationPanel) {
        window.focusDurationPanel.init();
    }
});

class FlowTimerState {
    constructor() {
        this.is_timer_running = false;
        this.remaining_time = 25 * 60;
        this.total_time = 25 * 60;
        this.is_paused = false;
        this.is_complete = false;
        this._listeners = new Map();
    }

    update(partial) {
        const changed = {};
        for (const [key, value] of Object.entries(partial)) {
            if (this[key] !== value) {
                this[key] = value;
                changed[key] = value;
            }
        }
        if (Object.keys(changed).length > 0) {
            this._notify(changed);
        }
    }

    subscribe(id, callback) {
        this._listeners.set(id, callback);
        return () => this._listeners.delete(id);
    }

    _notify(changed) {
        for (const [, cb] of this._listeners) {
            try { cb(changed); } catch (e) { console.warn('[FlowTimerState] Listener error:', e); }
        }
    }
}

class FlowModeManager {
    constructor() {
        this.active = false;
        this.timerRunning = false;
        this.timerPaused = false;
        this.totalSeconds = 25 * 60;
        this.remainingSeconds = this.totalSeconds;
        this.animationFrameId = null;
        this.lastTickTime = 0;
        this.audioPlaying = false;
        this.circumference = 2 * Math.PI * 130;
        this.prefs = JSON.parse(localStorage.getItem('starlearn_flow_prefs') || '{}');
        this.state = new FlowTimerState();
        this.state.subscribe('island-ui', (changed) => this._onStateChanged(changed));
        this.currentMode = 'focus';
        this.selectedMinutes = 25;
        this.leftSidebarOpen = false;
        this.rightSidebarOpen = false;
        this.flowPresets = {
            focus: [
                { minutes: 5, label: '5 分钟', sub: '快速' },
                { minutes: 10, label: '10 分钟', sub: '短时' },
                { minutes: 15, label: '15 分钟', sub: '适中' },
                { minutes: 30, label: '30 分钟', sub: '标准' },
                { minutes: 45, label: '45 分钟', sub: '深度' },
                { minutes: 60, label: '60 分钟', sub: '沉浸' }
            ],
            rest: [
                { minutes: 3, label: '3 分钟', sub: '微休' },
                { minutes: 5, label: '5 分钟', sub: '短休' },
                { minutes: 10, label: '10 分钟', sub: '小憩' },
                { minutes: 15, label: '15 分钟', sub: '放松' },
                { minutes: 20, label: '20 分钟', sub: '充电' },
                { minutes: 30, label: '30 分钟', sub: '深度' }
            ]
        };
    }

    _onStateChanged(changed) {
        if ('remaining_time' in changed) {
            this._syncIslandDisplay();
        }
        if ('is_timer_running' in changed || 'is_paused' in changed || 'is_complete' in changed) {
            this._syncIslandStatus();
        }
    }

    _syncIslandDisplay() {
        const mins = Math.floor(this.state.remaining_time / 60);
        const secs = this.state.remaining_time % 60;
        const timeStr = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
        const islandDisplay = document.getElementById('island-timer-display');
        if (islandDisplay) {
            islandDisplay.textContent = timeStr;
            islandDisplay.classList.add('tick');
            setTimeout(() => islandDisplay.classList.remove('tick'), 150);
        }
        const overlayDisplay = document.getElementById('flow-timer-display');
        if (overlayDisplay) overlayDisplay.textContent = timeStr;
        const fraction = this.state.remaining_time / this.state.total_time;
        const progressBar = document.getElementById('island-progress-bar');
        if (progressBar) progressBar.style.width = `${fraction * 100}%`;
        const ring = document.getElementById('flow-ring-progress');
        if (ring) {
            ring.setAttribute('stroke-dasharray', `${this.circumference * fraction} ${this.circumference}`);
        }
    }

    _syncIslandStatus() {
        const island = document.getElementById('flow-dynamic-island');
        const islandLabel = document.getElementById('island-timer-label');
        const modeLabel = this.currentMode === 'rest' ? '休息' : '专注';
        if (this.state.is_complete) {
            if (island) { island.classList.add('is-complete', 'flow-island-complete'); island.classList.remove('is-paused', 'flow-island-paused'); }
            if (islandLabel) islandLabel.textContent = modeLabel + '完成!';
            this._updateIslandPlayIcon(false);
        } else if (this.state.is_paused) {
            if (island) { island.classList.add('is-paused', 'flow-island-paused'); island.classList.remove('is-complete', 'flow-island-complete'); }
            if (islandLabel) islandLabel.textContent = '已暂停';
            this._updateIslandPlayIcon(true);
        } else if (this.state.is_timer_running) {
            if (island) { island.classList.remove('is-paused', 'flow-island-paused', 'is-complete', 'flow-island-complete'); }
            if (islandLabel) islandLabel.textContent = modeLabel + '中';
            this._updateIslandPlayIcon(false);
        } else {
            if (island) { island.classList.remove('is-paused', 'flow-island-paused', 'is-complete', 'flow-island-complete'); }
            if (islandLabel) islandLabel.textContent = modeLabel + '模式';
            this._updateIslandPlayIcon(true);
        }
    }

    enter() {
        if (this.active) return;
        this.active = true;
        document.body.classList.add('flow-mode-active');
        const overlay = document.getElementById('flow-overlay');
        if (overlay) {
            overlay.classList.toggle('rest-mode', this.currentMode === 'rest');
            overlay.classList.add('visible');
        }
        const island = document.getElementById('flow-dynamic-island');
        if (island) island.classList.add('visible');
        this.resetTimer();
        this.loadPrefs();
        this._renderFlowPresets();
        this._renderFlowMusicGenres();
        this._renderFlowMusicList();
        this._syncFlowMusicPlayer();
        this._updateSidebarExpandBtns();
        document.addEventListener('keydown', this._escHandler);
        if (lucide) lucide.createIcons();
    }

    exit() {
        if (!this.active) return;
        this.active = false;
        this.timerRunning = false;
        this.timerPaused = false;
        this.stopAudio();
        document.body.classList.remove('flow-mode-active');
        const overlay = document.getElementById('flow-overlay');
        if (overlay) overlay.classList.remove('visible');
        const island = document.getElementById('flow-dynamic-island');
        if (island) {
            island.classList.remove('visible', 'is-paused', 'is-complete', 'flow-island-paused', 'flow-island-complete');
        }
        document.removeEventListener('keydown', this._escHandler);
        if (this.animationFrameId) {
            cancelAnimationFrame(this.animationFrameId);
            this.animationFrameId = null;
        }
        this.state.update({
            is_timer_running: false,
            remaining_time: this.totalSeconds,
            is_paused: false,
            is_complete: false
        });
        this.savePrefs();
    }

    exitOverlayOnly() {
        document.body.classList.remove('flow-mode-active');
        const overlay = document.getElementById('flow-overlay');
        if (overlay) overlay.classList.remove('visible');
        document.removeEventListener('keydown', this._escHandler);
        const island = document.getElementById('flow-dynamic-island');
        if (island) island.classList.add('visible');
    }

    _escHandler = (e) => {
        if (e.key === 'Escape') this.exitOverlayOnly();
    };

    resetTimer() {
        this.remainingSeconds = this.totalSeconds;
        this.timerRunning = false;
        this.timerPaused = false;
        if (this.animationFrameId) {
            cancelAnimationFrame(this.animationFrameId);
            this.animationFrameId = null;
        }
        this.state.update({
            is_timer_running: false,
            remaining_time: this.totalSeconds,
            is_paused: false,
            is_complete: false
        });
        const container = document.querySelector('.flow-timer-container');
        if (container) container.classList.remove('flow-timer-complete');
        const modeLabel = this.currentMode === 'rest' ? '休息' : '专注';
        const btn = document.getElementById('flow-start-btn');
        if (btn) btn.innerHTML = '<i data-lucide="play" class="w-4 h-4"></i> 开始' + modeLabel;
        const label = document.getElementById('flow-timer-label');
        if (label) label.textContent = modeLabel + '模式';
        this._updateIslandPlayIcon(true);
        if (lucide) lucide.createIcons();
    }

    toggleTimer() {
        if (!this.active) return;
        if (!this.timerRunning) {
            this.startTimer();
        } else if (this.timerPaused) {
            this.resumeTimer();
        } else {
            this.pauseTimer();
        }
    }

    startTimer() {
        this.timerRunning = true;
        this.timerPaused = false;
        this.lastTickTime = performance.now();
        this._tick();
        const modeLabel = this.currentMode === 'rest' ? '休息' : '专注';
        const btn = document.getElementById('flow-start-btn');
        if (btn) btn.innerHTML = '<i data-lucide="pause" class="w-4 h-4"></i> 暂停';
        const label = document.getElementById('flow-timer-label');
        if (label) label.textContent = modeLabel + '中...';
        this.state.update({ is_timer_running: true, is_paused: false, is_complete: false });
        if (lucide) lucide.createIcons();
    }

    pauseTimer() {
        this.timerPaused = true;
        if (this.animationFrameId) {
            cancelAnimationFrame(this.animationFrameId);
            this.animationFrameId = null;
        }
        const btn = document.getElementById('flow-start-btn');
        if (btn) btn.innerHTML = '<i data-lucide="play" class="w-4 h-4"></i> 继续';
        const label = document.getElementById('flow-timer-label');
        if (label) label.textContent = '已暂停';
        this.state.update({ is_paused: true });
        if (lucide) lucide.createIcons();
    }

    resumeTimer() {
        this.timerPaused = false;
        this.lastTickTime = performance.now();
        this._tick();
        const modeLabel = this.currentMode === 'rest' ? '休息' : '专注';
        const btn = document.getElementById('flow-start-btn');
        if (btn) btn.innerHTML = '<i data-lucide="pause" class="w-4 h-4"></i> 暂停';
        const label = document.getElementById('flow-timer-label');
        if (label) label.textContent = modeLabel + '中...';
        this.state.update({ is_paused: false });
        if (lucide) lucide.createIcons();
    }

    _tick = () => {
        if (!this.timerRunning || this.timerPaused) return;
        const now = performance.now();
        const deltaMs = now - this.lastTickTime;
        if (deltaMs >= 1000) {
            const elapsed = Math.floor(deltaMs / 1000);
            this.remainingSeconds = Math.max(0, this.remainingSeconds - elapsed);
            this.lastTickTime = now - (deltaMs % 1000);
            this.state.update({ remaining_time: this.remainingSeconds });
            if (this.remainingSeconds <= 0) {
                this.onTimerComplete();
                return;
            }
        }
        this.animationFrameId = requestAnimationFrame(this._tick);
    };

    onTimerComplete() {
        this.timerRunning = false;
        this.timerPaused = false;
        if (this.animationFrameId) {
            cancelAnimationFrame(this.animationFrameId);
            this.animationFrameId = null;
        }
        const container = document.querySelector('.flow-timer-container');
        if (container) container.classList.add('flow-timer-complete');
        const modeLabel = this.currentMode === 'rest' ? '休息' : '专注';
        const btn = document.getElementById('flow-start-btn');
        if (btn) btn.innerHTML = '<i data-lucide="rotate-ccw" class="w-4 h-4"></i> 再来一轮';
        const label = document.getElementById('flow-timer-label');
        if (label) label.textContent = modeLabel + '完成！';
        this.state.update({ is_timer_running: false, is_complete: true });
        if (lucide) lucide.createIcons();
        this.playCompletionSound();
        this._showPlantReward();
    }

    _showPlantReward() {
        if (this.currentMode === 'rest') return;
        const seeds = parseInt(localStorage.getItem('starlearn_seeds') || '0');
        localStorage.setItem('starlearn_seeds', String(seeds + 1));
        const modal = document.getElementById('plant-reward-modal');
        const countEl = document.getElementById('plant-reward-seed-count');
        if (countEl) countEl.textContent = seeds + 1;
        if (modal) {
            modal.classList.remove('hidden');
            requestAnimationFrame(() => {
                requestAnimationFrame(() => modal.classList.add('visible'));
            });
        }
    }

    _updateIslandPlayIcon(isPaused) {
        const icon = document.getElementById('island-play-icon');
        if (!icon) return;
        if (isPaused) {
            icon.innerHTML = '<polygon points="5 3 19 12 5 21 5 3"></polygon>';
        } else {
            icon.innerHTML = '<rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect>';
        }
    }

    playCompletionSound() {
        try {
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            const notes = [523.25, 659.25, 783.99, 1046.50];
            notes.forEach((freq, i) => {
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.type = 'sine';
                osc.frequency.value = freq;
                gain.gain.setValueAtTime(0.15, ctx.currentTime + i * 0.2);
                gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + i * 0.2 + 0.5);
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.start(ctx.currentTime + i * 0.2);
                osc.stop(ctx.currentTime + i * 0.2 + 0.5);
            });
        } catch (e) {}
    }

    updateTimerDisplay() {
        this._syncIslandDisplay();
    }

    updateRingProgress(fraction) {
        const ring = document.getElementById('flow-ring-progress');
        if (ring) {
            ring.setAttribute('stroke-dasharray', `${this.circumference * fraction} ${this.circumference}`);
        }
        const progressBar = document.getElementById('island-progress-bar');
        if (progressBar) {
            progressBar.style.width = `${fraction * 100}%`;
        }
    }

    toggleAudio() {
        const audio = document.getElementById('flow-audio');
        if (!audio) return;
        if (this.audioPlaying) {
            this.stopAudio();
        } else {
            this.playAudio();
        }
    }

    playAudio() {
        const audio = document.getElementById('flow-audio');
        if (!audio) return;
        audio.volume = (parseInt(document.getElementById('flow-volume')?.value || 40)) / 100;
        audio.play().then(() => {
            this.audioPlaying = true;
            const btn = document.getElementById('flow-audio-toggle');
            if (btn) btn.classList.add('active');
        }).catch(err => {
            console.warn('[FlowMode] Audio play failed:', err);
        });
    }

    stopAudio() {
        const audio = document.getElementById('flow-audio');
        if (audio) {
            audio.pause();
            audio.currentTime = 0;
        }
        this.audioPlaying = false;
        const btn = document.getElementById('flow-audio-toggle');
        if (btn) btn.classList.remove('active');
    }

    setVolume(val) {
        const audio = document.getElementById('flow-audio');
        if (audio) audio.volume = val / 100;
        const label = document.getElementById('flow-volume-label');
        if (label) label.textContent = val + '%';
        this.prefs.volume = parseInt(val);
    }

    loadPrefs() {
        if (this.prefs.volume !== undefined) {
            const slider = document.getElementById('flow-volume');
            if (slider) slider.value = this.prefs.volume;
            this.setVolume(this.prefs.volume);
        }
    }

    savePrefs() {
        localStorage.setItem('starlearn_flow_prefs', JSON.stringify(this.prefs));
    }

    switchFlowMode(mode) {
        if (this.currentMode === mode) return;
        this.currentMode = mode;
        this.selectedMinutes = mode === 'focus' ? 25 : 5;
        const overlay = document.getElementById('flow-overlay');
        if (overlay) overlay.classList.toggle('rest-mode', mode === 'rest');
        const island = document.getElementById('flow-dynamic-island');
        if (island) {
            island.classList.toggle('rest-mode', mode === 'rest');
            island.classList.toggle('flow-island-rest', mode === 'rest');
        }
        const islandLabel = document.getElementById('island-timer-label');
        if (islandLabel) islandLabel.textContent = mode === 'rest' ? '休息模式' : '专注模式';
        document.querySelectorAll('#flow-mode-switch .flow-mode-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.mode === mode);
        });
        this._renderFlowPresets();
        const label = document.getElementById('flow-timer-label');
        if (label) label.textContent = mode === 'rest' ? '休息模式' : '专注模式';
    }

    _renderFlowPresets() {
        const container = document.getElementById('flow-presets-grid');
        if (!container) return;
        const presets = this.flowPresets[this.currentMode] || this.flowPresets.focus;
        container.innerHTML = presets.map(p => {
            const isSelected = this.selectedMinutes === p.minutes;
            return `<button class="flow-preset-item${isSelected ? ' selected' : ''}" data-minutes="${p.minutes}" onclick="window.flowMode.selectFlowPreset(${p.minutes})">
                <span class="preset-time">${p.label}</span>
                <span class="preset-desc">${p.sub}</span>
            </button>`;
        }).join('');
    }

    selectFlowPreset(minutes) {
        this.selectedMinutes = minutes;
        this._renderFlowPresets();
        const totalSeconds = minutes * 60;
        this.totalSeconds = totalSeconds;
        this.remainingSeconds = totalSeconds;
        this.state.update({
            total_time: totalSeconds,
            remaining_time: totalSeconds,
            is_timer_running: false,
            is_paused: false,
            is_complete: false
        });
        this.resetTimer();
    }

    confirmCustomDuration() {
        const input = document.getElementById('flow-custom-field');
        if (!input) return;
        const val = parseInt(input.value);
        if (!val || val < 1 || val > 180) {
            input.style.borderColor = 'var(--danger-border)';
            setTimeout(() => { input.style.borderColor = ''; }, 1500);
            return;
        }
        this.selectFlowPreset(val);
        input.value = '';
        input.style.borderColor = 'var(--success-border)';
        setTimeout(() => { input.style.borderColor = ''; }, 1000);
    }

    toggleLeftSidebar() {
        this.leftSidebarOpen = !this.leftSidebarOpen;
        const sidebar = document.getElementById('flow-sidebar-left');
        if (sidebar) sidebar.classList.toggle('collapsed', !this.leftSidebarOpen);
        this._updateSidebarExpandBtns();
    }

    toggleRightSidebar() {
        this.rightSidebarOpen = !this.rightSidebarOpen;
        const sidebar = document.getElementById('flow-sidebar-right');
        if (sidebar) sidebar.classList.toggle('collapsed', !this.rightSidebarOpen);
        this._updateSidebarExpandBtns();
    }

    _updateSidebarExpandBtns() {
        const leftExpand = document.getElementById('flow-expand-left');
        const rightExpand = document.getElementById('flow-expand-right');
        if (leftExpand) leftExpand.classList.toggle('visible', !this.leftSidebarOpen);
        if (rightExpand) rightExpand.classList.toggle('visible', !this.rightSidebarOpen);
    }

    _renderFlowMusicGenres() {
        const container = document.getElementById('flow-music-genres');
        if (!container) return;
        const genres = [
            { key: 'all', label: '全部' },
            { key: 'piano', label: '钢琴' },
            { key: 'ambient', label: '环境' },
            { key: 'nature', label: '自然' },
            { key: 'lofi', label: '低保真' }
        ];
        const currentGenre = window.musicPanel?.currentGenre || 'all';
        container.innerHTML = genres.map(g =>
            `<button class="flow-music-genre-chip${g.key === currentGenre ? ' active' : ''}" onclick="window.flowMode._filterFlowMusic('${g.key}')">${g.label}</button>`
        ).join('');
    }

    _filterFlowMusic(genre) {
        if (window.musicPanel) {
            window.musicPanel.currentGenre = genre;
            window.musicPanel._renderGenres();
            window.musicPanel._renderList();
        }
        this._renderFlowMusicGenres();
        this._renderFlowMusicList();
    }

    _renderFlowMusicList() {
        const container = document.getElementById('flow-music-list');
        if (!container || !window.musicPanel) return;
        const songs = window.musicPanel.songs || [];
        const genre = window.musicPanel.currentGenre || 'all';
        const filtered = genre === 'all' ? songs : songs.filter(s => s.genre === genre);
        const currentSongId = window.musicPanel.currentIndex >= 0 ? window.musicPanel.songs[window.musicPanel.currentIndex]?.id : -1;
        container.innerHTML = filtered.map(song =>
            `<div class="flow-music-item${song.id === currentSongId ? ' playing' : ''}" onclick="window.musicPanel.play(${song.id})">
                <div class="flow-music-item-cover">${song.coverSvg || ''}</div>
                <div class="flow-music-item-info">
                    <div class="flow-music-item-title">${song.title}</div>
                    <div class="flow-music-item-artist">${song.artist}</div>
                </div>
            </div>`
        ).join('');
    }

    _syncFlowMusicPlayer() {
        if (!window.musicPanel) return;
        const title = document.getElementById('flow-music-title');
        const artist = document.getElementById('flow-music-artist');
        const cover = document.getElementById('flow-music-cover');
        const playIcon = document.getElementById('flow-music-play-icon');
        if (window.musicPanel.currentIndex >= 0) {
            const song = window.musicPanel.songs[window.musicPanel.currentIndex];
            if (title) title.textContent = song.title;
            if (artist) artist.textContent = song.artist;
            if (cover) cover.innerHTML = song.coverSvg || '';
        } else {
            if (title) title.textContent = '未在播放';
            if (artist) artist.textContent = '';
        }
        if (playIcon) {
            playIcon.innerHTML = window.musicPanel.isPlaying
                ? '<rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect>'
                : '<polygon points="5 3 19 12 5 21 5 3"></polygon>';
        }
    }

    syncVisualizers() {
        const isPlaying = window.musicPanel?.isPlaying || false;
        document.querySelectorAll('.flow-vis-bar').forEach(bar => {
            bar.classList.toggle('playing', isPlaying);
        });
        document.querySelectorAll('.mini-vis-bar').forEach(bar => {
            bar.classList.toggle('playing', isPlaying);
        });
        document.querySelectorAll('.music-vis-bar').forEach(bar => {
            bar.classList.toggle('playing', isPlaying);
        });
    }
}

function formatTime(seconds) {
    if (typeof seconds !== 'number' || !isFinite(seconds) || seconds <= 0) return '00:00';
    const totalSec = Math.floor(Math.max(0, seconds));
    const mins = Math.floor(totalSec / 60);
    const secs = totalSec % 60;
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

class FlashcardUI {
    constructor() {
        this.cards = [];
        this.currentIndex = 0;
        this.flipped = false;
        this.container = null;
        this.timeLeft = 180;
        this.timerInterval = null;
        this.autoFlipTimer = null;
        this.AUTO_FLIP_DELAY = parseInt(localStorage.getItem('starlearn_flashcard_duration') || '180') * 1000;
        this.COUNTDOWN_WARNING = 10;
        this._countdownStartTs = 0;
        this._countdownTotalSec = 0;
        this._visibilityHandler = null;
        this._beforeUnloadHandler = null;
        this._destroyed = false;
    }

    async open() {
        if (this._destroyed) return;
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.id = 'flashcard-modal';
            this.container.style.cssText = `
                position: fixed; inset: 0; z-index: 300;
                display: flex; align-items: center; justify-content: center;
                background: rgba(0,0,0,0.6); backdrop-filter: blur(20px);
                -webkit-backdrop-filter: blur(20px);
                opacity: 0; visibility: hidden;
                transition: opacity 300ms ease, visibility 300ms ease;
            `;
            document.body.appendChild(this.container);
        }
        this.container.style.opacity = '1';
        this.container.style.visibility = 'visible';
        this.AUTO_FLIP_DELAY = parseInt(localStorage.getItem('starlearn_flashcard_duration') || '180') * 1000;
        await this.generateCards();
        this._restoreCountdownState();
        this.renderCard();
        document.addEventListener('keydown', this._keyHandler);
        this._bindVisibilityChange();
        this._bindBeforeUnload();
    }

    close() {
        this._forceClearAllTimers();
        this._clearCountdownState();
        if (this.container) {
            this.container.style.opacity = '0';
            this.container.style.visibility = 'hidden';
        }
        document.removeEventListener('keydown', this._keyHandler);
        this._unbindVisibilityChange();
        this._unbindBeforeUnload();
    }

    destroy() {
        this.close();
        this._destroyed = true;
        if (this.container && this.container.parentNode) {
            this.container.parentNode.removeChild(this.container);
        }
        this.container = null;
        this.cards = [];
    }

    _forceClearAllTimers() {
        if (this.timerInterval !== null) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }
        if (this.autoFlipTimer !== null) {
            clearTimeout(this.autoFlipTimer);
            this.autoFlipTimer = null;
        }
        this.timeLeft = 0;
    }

    _keyHandler = (e) => {
        if (e.key === 'Escape') this.close();
        else if (e.key === 'ArrowLeft') this.prev();
        else if (e.key === 'ArrowRight') this.next();
        else if (e.key === ' ') { e.preventDefault(); this.flip(); }
    };

    _startAutoFlip() {
        this._forceClearAllTimers();

        this._countdownTotalSec = Math.floor(this.AUTO_FLIP_DELAY / 1000);
        this.timeLeft = this._countdownTotalSec;
        this._countdownStartTs = Date.now();
        this._updateCountdownDisplay();

        this.timerInterval = setInterval(() => {
            const elapsed = Math.floor((Date.now() - this._countdownStartTs) / 1000);
            this.timeLeft = Math.max(0, this._countdownTotalSec - elapsed);
            this._updateCountdownDisplay();

            if (this.timeLeft <= 0) {
                this._clearCountdown();
                if (!this.flipped) {
                    this.flip(true);
                }
            }
        }, 1000);

        this.autoFlipTimer = setTimeout(() => {
            if (!this.flipped) {
                this.flip(true);
            }
        }, this.AUTO_FLIP_DELAY);

        this._saveCountdownState();
    }

    _clearAutoFlip() {
        if (this.autoFlipTimer !== null) {
            clearTimeout(this.autoFlipTimer);
            this.autoFlipTimer = null;
        }
        this._clearCountdown();
    }

    _clearCountdown() {
        if (this.timerInterval !== null) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }
    }

    _updateCountdownDisplay() {
        const frontEl = document.getElementById('flashcard-countdown-front');
        const backEl = document.getElementById('flashcard-countdown');
        const text = formatTime(this.timeLeft);

        [frontEl, backEl].forEach(el => {
            if (!el) return;
            el.textContent = text;
            el.classList.remove('countdown-warning', 'countdown-expired');
            if (this.timeLeft <= 0) {
                el.classList.add('countdown-expired');
            } else if (this.timeLeft <= this.COUNTDOWN_WARNING) {
                el.classList.add('countdown-warning');
            }
        });
    }

    _saveCountdownState() {
        try {
            const state = {
                cardIndex: this.currentIndex,
                flipped: this.flipped,
                countdownStartTs: this._countdownStartTs,
                countdownTotalSec: this._countdownTotalSec,
                timestamp: Date.now(),
            };
            sessionStorage.setItem('starlearn_flashcard_state', JSON.stringify(state));
        } catch (e) {}
    }

    _restoreCountdownState() {
        try {
            const saved = sessionStorage.getItem('starlearn_flashcard_state');
            if (!saved) return;
            const state = JSON.parse(saved);
            if (state.cardIndex !== undefined && state.cardIndex < this.cards.length) {
                this.currentIndex = state.cardIndex;
            }
            const elapsed = Math.floor((Date.now() - (state.countdownStartTs || 0)) / 1000);
            const remaining = Math.max(0, (state.countdownTotalSec || 0) - elapsed);
            if (remaining > 0 && state.countdownTotalSec > 0) {
                this._countdownTotalSec = remaining;
                this.AUTO_FLIP_DELAY = remaining * 1000;
                this.flipped = state.flipped || false;
            }
        } catch (e) {}
    }

    _clearCountdownState() {
        try {
            sessionStorage.removeItem('starlearn_flashcard_state');
        } catch (e) {}
    }

    _bindVisibilityChange() {
        this._visibilityHandler = () => {
            if (document.visibilityState === 'visible' && this.timerInterval) {
                const elapsed = Math.floor((Date.now() - this._countdownStartTs) / 1000);
                this.timeLeft = Math.max(0, this._countdownTotalSec - elapsed);
                this._updateCountdownDisplay();
                if (this.timeLeft <= 0) {
                    this._clearCountdown();
                    if (!this.flipped) {
                        this.flip(true);
                    }
                }
            } else if (document.visibilityState === 'hidden') {
                this._saveCountdownState();
            }
        };
        document.addEventListener('visibilitychange', this._visibilityHandler);
    }

    _unbindVisibilityChange() {
        if (this._visibilityHandler) {
            document.removeEventListener('visibilitychange', this._visibilityHandler);
            this._visibilityHandler = null;
        }
    }

    _bindBeforeUnload() {
        this._beforeUnloadHandler = () => {
            this._saveCountdownState();
            this._forceClearAllTimers();
        };
        window.addEventListener('beforeunload', this._beforeUnloadHandler);
    }

    _unbindBeforeUnload() {
        if (this._beforeUnloadHandler) {
            window.removeEventListener('beforeunload', this._beforeUnloadHandler);
            this._beforeUnloadHandler = null;
        }
    }

    async generateCards() {
        const user = JSON.parse(localStorage.getItem('starlearn_user') || '{}');
        const evaluation = JSON.parse(localStorage.getItem('starlearn_evaluation') || '{}');
        const recentContent = evaluation.lastTopics || '大数据基础';
        try {
            const res = await fetch(`${API_BASE}/api/v2/flashcard/generate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    student_id: user.id || user.name || 'anonymous',
                    course_id: user.currentTask || 'bigdata',
                    chapter_name: recentContent,
                    chapter_content: recentContent,
                }),
            });
            const data = await res.json();
            if (data.success && data.data?.flashcards?.length > 0) {
                this.cards = data.data.flashcards;
            } else {
                this.cards = this._fallbackCards(recentContent);
            }
        } catch (err) {
            console.warn('[Flashcard] Generate failed:', err);
            this.cards = this._fallbackCards(recentContent);
        }
        this.currentIndex = 0;
        this.flipped = false;
    }

    _fallbackCards(topic) {
        return [
            { front: `${topic}的核心概念是什么？`, back: '请通过对话学习获取详细内容', hint: '尝试用自己的话总结' },
            { front: `${topic}有哪些常见应用场景？`, back: '结合实际案例理解更深刻', hint: '思考日常生活中的例子' },
            { front: `${topic}与其他相关概念有何区别？`, back: '对比分析有助于深入理解', hint: '关注本质差异而非表面' },
            { front: `${topic}的底层原理是什么？`, back: '理解原理才能灵活运用', hint: '从机制层面思考' },
            { front: `${topic}有哪些常见误区？`, back: '识别误区是正确理解的关键', hint: '回忆自己是否犯过类似错误' },
            { front: `${topic}的发展历程是怎样的？`, back: '了解演进有助于把握趋势', hint: '关注关键转折点' },
            { front: `${topic}的核心特征有哪些？`, back: '特征是识别和分类的基础', hint: '列举最本质的3-5个特征' },
            { front: `${topic}在实际中如何应用？`, back: '理论联系实际加深记忆', hint: '寻找身边的真实案例' },
            { front: `${topic}有哪些限制条件？`, back: '了解边界才能正确使用', hint: '思考什么情况下不适用' },
            { front: `如何系统学习${topic}？`, back: '系统学习需要建立知识框架', hint: '从整体到局部逐步深入' },
        ];
    }

    renderCard() {
        if (!this.container || this.cards.length === 0) return;
        const card = this.cards[this.currentIndex];
        const wasFlipped = this.flipped;
        this.flipped = false;
        this._forceClearAllTimers();
        const durationSec = Math.floor(this.AUTO_FLIP_DELAY / 1000);
        const initialDisplay = formatTime(durationSec);
        this.container.innerHTML = `
            <div style="max-width: 480px; width: 90%; padding: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h3 style="color: var(--text-primary); font-size: 16px; font-weight: 700;">⚡ 知识胶囊</h3>
                    <button onclick="window.flashcardUI.close()" style="background: none; border: none; color: var(--text-tertiary); cursor: pointer; font-size: 20px;">✕</button>
                </div>
                <div class="flashcard-container" onclick="window.flashcardUI.flip()">
                    <div class="flashcard-card" id="flashcard-card" style="height: 240px;">
                        <div class="flashcard-front">
                            <div style="font-size: 11px; color: var(--text-tertiary); margin-bottom: 12px;">点击翻转查看答案</div>
                            <div class="flashcard-question">${card.front}</div>
                            <div class="flashcard-countdown flashcard-countdown-front" id="flashcard-countdown-front">${initialDisplay}</div>
                        </div>
                        <div class="flashcard-back">
                            <div class="flashcard-answer">${card.back}</div>
                            ${card.hint ? `<div class="flashcard-hint">💡 ${card.hint}</div>` : ''}
                            <div class="flashcard-countdown" id="flashcard-countdown">${initialDisplay}</div>
                        </div>
                    </div>
                </div>
                <div id="flashcard-auto-flip-hint" style="text-align: center; margin-top: 8px; font-size: 10px; color: var(--text-tertiary); opacity: 0; transition: opacity 0.5s ease;">
                    ⏱ ${durationSec}秒后自动展示答案
                </div>
                <div class="flashcard-nav" style="justify-content: center; margin-top: 16px;">
                    <button class="flashcard-nav-btn" onclick="window.flashcardUI.prev()" ${this.currentIndex === 0 ? 'disabled' : ''}>
                        <i data-lucide="chevron-left" class="w-4 h-4"></i>
                    </button>
                    <span class="flashcard-counter">${this.currentIndex + 1} / ${this.cards.length}</span>
                    <button class="flashcard-nav-btn" onclick="window.flashcardUI.next()" ${this.currentIndex >= this.cards.length - 1 ? 'disabled' : ''}>
                        <i data-lucide="chevron-right" class="w-4 h-4"></i>
                    </button>
                </div>
                <div style="text-align: center; margin-top: 12px; font-size: 11px; color: var(--text-tertiary);">
                    ← → 切换卡片 · 空格翻转 · Esc 关闭
                </div>
            </div>
        `;
        if (lucide) lucide.createIcons();

        if (wasFlipped) {
            this.flipped = true;
            const cardEl = document.getElementById('flashcard-card');
            if (cardEl) cardEl.classList.add('flipped');
            this._clearCountdown();
        } else {
            this._startAutoFlip();
        }

        const hintEl = document.getElementById('flashcard-auto-flip-hint');
        if (hintEl && !wasFlipped) setTimeout(() => { hintEl.style.opacity = '1'; }, 500);
    }

    flip(isAutoFlip = false) {
        const card = document.getElementById('flashcard-card');
        if (card) {
            this.flipped = !this.flipped;
            card.classList.toggle('flipped', this.flipped);
            this._clearAutoFlip();
            const hintEl = document.getElementById('flashcard-auto-flip-hint');
            if (this.flipped && isAutoFlip) {
                const answerEl = card.querySelector('.flashcard-answer');
                if (answerEl) {
                    answerEl.classList.add('auto-flip-highlight');
                    setTimeout(() => answerEl.classList.remove('auto-flip-highlight'), 3000);
                }
                if (hintEl) {
                    hintEl.textContent = '✅ 已自动展示答案';
                    hintEl.style.color = 'var(--success)';
                    hintEl.style.opacity = '1';
                }
            } else if (hintEl) {
                hintEl.style.opacity = '0';
            }
            if (this.flipped) {
                this._clearCountdown();
                this._clearCountdownState();
            }
        }
    }

    next() {
        if (this.currentIndex < this.cards.length - 1) {
            this.currentIndex++;
            this._clearCountdownState();
            this.renderCard();
        }
    }

    prev() {
        if (this.currentIndex > 0) {
            this.currentIndex--;
            this._clearCountdownState();
            this.renderCard();
        }
    }
}

function toggleSection(sectionId, btnEl) {
    const section = document.getElementById(sectionId);
    if (!section) return;
    const isCollapsed = section.classList.contains('collapsed');
    if (isCollapsed) {
        section.classList.remove('collapsed');
        if (btnEl) btnEl.classList.remove('collapsed');
    } else {
        section.classList.add('collapsed');
        if (btnEl) btnEl.classList.add('collapsed');
    }
}

window.flowMode = new FlowModeManager();
window.flashcardUI = new FlashcardUI();

function goToPlantFarm() {
    const modal = document.getElementById('plant-reward-modal');
    if (modal) {
        modal.classList.remove('visible');
        setTimeout(() => modal.classList.add('hidden'), 300);
    }
    window.location.href = '/plant.html';
}

class SidebarManager {
    constructor() {
        this.prefs = JSON.parse(localStorage.getItem('starlearn_sidebar_prefs') || '{}');
        this._debounceTimers = {};
    }

    init() {
        if (this.prefs.leftCollapsed === undefined) {
            this.prefs.leftCollapsed = true;
        }
        if (this.prefs.rightCollapsed === undefined) {
            this.prefs.rightCollapsed = false;
        }
        if (this.prefs.leftCollapsed) {
            document.getElementById('left-col')?.classList.add('collapsed');
        }
        if (this.prefs.rightCollapsed) {
            document.getElementById('right-col')?.classList.add('collapsed');
        }
        this._updateToggleIcons();
        this._updateExpandBtns();
    }

    toggleLeft() {
        if (this._debounceTimers.left) return;
        this._debounceTimers.left = true;
        setTimeout(() => { this._debounceTimers.left = false; }, 350);
        const col = document.getElementById('left-col');
        if (!col) return;
        col.classList.toggle('collapsed');
        this.prefs.leftCollapsed = col.classList.contains('collapsed');
        this._savePrefs();
        this._updateToggleIcons();
        this._updateExpandBtns();
    }

    toggleRight() {
        if (this._debounceTimers.right) return;
        this._debounceTimers.right = true;
        setTimeout(() => { this._debounceTimers.right = false; }, 350);
        const col = document.getElementById('right-col');
        if (!col) return;
        col.classList.toggle('collapsed');
        this.prefs.rightCollapsed = col.classList.contains('collapsed');
        this._savePrefs();
        this._updateToggleIcons();
        this._updateExpandBtns();
    }

    _updateToggleIcons() {
        const leftCol = document.getElementById('left-col');
        const rightCol = document.getElementById('right-col');
        const leftBtn = leftCol?.querySelector('.sidebar-toggle-btn svg');
        const rightBtn = rightCol?.querySelector('.sidebar-toggle-btn svg');
        if (leftBtn) {
            leftBtn.innerHTML = leftCol.classList.contains('collapsed')
                ? '<polyline points="9 18 15 12 9 6"></polyline>'
                : '<polyline points="15 18 9 12 15 6"></polyline>';
        }
        if (rightBtn) {
            rightBtn.innerHTML = rightCol.classList.contains('collapsed')
                ? '<polyline points="15 18 9 12 15 6"></polyline>'
                : '<polyline points="9 18 15 12 9 6"></polyline>';
        }
    }

    _updateExpandBtns() {
        const leftCol = document.getElementById('left-col');
        const rightCol = document.getElementById('right-col');
        const leftExpand = document.getElementById('left-expand-btn');
        const rightExpand = document.getElementById('right-expand-btn');
        if (leftExpand) {
            leftExpand.classList.toggle('visible', leftCol?.classList.contains('collapsed'));
        }
        if (rightExpand) {
            rightExpand.classList.toggle('visible', rightCol?.classList.contains('collapsed'));
        }
    }

    _savePrefs() {
        localStorage.setItem('starlearn_sidebar_prefs', JSON.stringify(this.prefs));
    }
}

window.sidebarManager = new SidebarManager();

class LightboxManager {
    constructor() {
        this.overlay = null;
        this.img = null;
        this.closeBtn = null;
        this.isOpen = false;
        this._dragState = null;
        this._initialized = false;
        this._boundOnDblClick = this._onDblClick.bind(this);
        this._boundOnBackdropClick = this._onBackdropClick.bind(this);
        this._boundOnKeyDown = this._onKeyDown.bind(this);
        this._boundOnDragStart = this._onDragStart.bind(this);
        this._boundOnDragMove = this._onDragMove.bind(this);
        this._boundOnDragEnd = this._onDragEnd.bind(this);
    }

    init() {
        if (this._initialized) return;
        this.overlay = document.getElementById('lightbox-overlay');
        this.img = document.getElementById('lightbox-img');
        this.closeBtn = document.getElementById('lightbox-close-btn');
        if (!this.overlay) return;
        this.overlay.querySelector('.lightbox-backdrop').addEventListener('click', this._boundOnBackdropClick);
        this.closeBtn?.addEventListener('click', () => this.close());
        this.img?.addEventListener('mousedown', this._boundOnDragStart);
        this.img?.addEventListener('touchstart', this._boundOnDragStart, { passive: false });
        document.addEventListener('mousemove', this._boundOnDragMove);
        document.addEventListener('touchmove', this._boundOnDragMove, { passive: false });
        document.addEventListener('mouseup', this._boundOnDragEnd);
        document.addEventListener('touchend', this._boundOnDragEnd);
        this._observeChat();
        this._initialized = true;
    }

    _observeChat() {
        const chatContainer = document.getElementById('chat-container');
        if (!chatContainer) return;
        const observer = new MutationObserver(() => this._bindImages());
        observer.observe(chatContainer, { childList: true, subtree: true });
        this._bindImages();
    }

    _bindImages() {
        const chatContainer = document.getElementById('chat-container');
        if (!chatContainer) return;
        const images = chatContainer.querySelectorAll('.msg-bubble-bot img, .prose img');
        images.forEach(img => {
            if (!img.dataset.lightboxBound) {
                img.dataset.lightboxBound = 'true';
                img.addEventListener('dblclick', this._boundOnDblClick);
            }
        });
    }

    _onDblClick(e) {
        e.preventDefault();
        const img = e.currentTarget;
        if (img.src) {
            this.open(img.src, img.alt || '');
        }
    }

    open(src, alt = '') {
        this.init();
        if (!this.overlay || !this.img) return;
        this.img.src = src;
        this.img.alt = alt || '放大预览';
        this.img.style.transform = '';
        this._dragState = null;
        this.overlay.classList.remove('closing');
        this.overlay.classList.add('open');
        this.isOpen = true;
        document.addEventListener('keydown', this._boundOnKeyDown);
        document.body.style.overflow = 'hidden';
    }

    close() {
        if (!this.overlay || !this.isOpen) return;
        this.overlay.classList.add('closing');
        this.overlay.classList.remove('open');
        this.isOpen = false;
        document.removeEventListener('keydown', this._boundOnKeyDown);
        setTimeout(() => {
            this.overlay?.classList.remove('closing');
            this.img.src = '';
            this.img.style.transform = '';
            this._dragState = null;
        }, 300);
    }

    _onBackdropClick(e) {
        if (e.target === e.currentTarget) {
            this.close();
        }
    }

    _onKeyDown(e) {
        if (e.key === 'Escape') {
            this.close();
        }
    }

    _onDragStart(e) {
        if (!this.isOpen) return;
        e.preventDefault();
        const pos = e.touches ? e.touches[0] : e;
        this._dragState = {
            startX: pos.clientX,
            startY: pos.clientY,
            offsetX: 0,
            offsetY: 0,
        };
        this.img.classList.add('dragging');
    }

    _onDragMove(e) {
        if (!this._dragState) return;
        e.preventDefault();
        const pos = e.touches ? e.touches[0] : e;
        this._dragState.offsetX = pos.clientX - this._dragState.startX;
        this._dragState.offsetY = pos.clientY - this._dragState.startY;
        this.img.style.transform = `translate(${this._dragState.offsetX}px, ${this._dragState.offsetY}px)`;
    }

    _onDragEnd() {
        if (!this._dragState) return;
        this._dragState = null;
        this.img.classList.remove('dragging');
        this.img.style.transform = '';
    }
}

window.lightboxManager = new LightboxManager();

class MusicPanel {
    constructor() {
        this.isOpen = false;
        this.currentIndex = -1;
        this.isPlaying = false;
        this.currentGenre = 'all';
        this.audio = new Audio();
        this.audio.volume = 0.6;
        this._previousVolume = 60;
        const slider = document.getElementById('music-volume-slider');
        const label = document.getElementById('music-volume-label');
        if (slider) slider.value = 60;
        if (label) label.textContent = '60';
        this._boundOnError = this._onAudioError.bind(this);
        this._boundOnEnded = this._onAudioEnded.bind(this);
        this.audio.addEventListener('error', this._boundOnError);
        this.audio.addEventListener('ended', this._boundOnEnded);

        this.songs = this._createSongData();
        this._renderGenres();
        this._renderList();
    }

    _createSongData() {
        const genres = {
            piano: {
                label: '经典钢琴',
                colors: ['#818cf8', '#6366f1', '#a5b4fc'],
                shapes: ['circle', 'diamond', 'hexagon', 'star', 'triangle']
            },
            ambient: {
                label: '环境音乐',
                colors: ['#34d399', '#10b981', '#6ee7b7'],
                shapes: ['circle', 'diamond', 'hexagon', 'star', 'triangle']
            },
            nature: {
                label: '自然声',
                colors: ['#fbbf24', '#f59e0b', '#fcd34d'],
                shapes: ['circle', 'diamond', 'hexagon', 'star', 'triangle']
            },
            lofi: {
                label: '低保真',
                colors: ['#f472b6', '#ec4899', '#f9a8d4'],
                shapes: ['circle', 'diamond', 'hexagon', 'star', 'triangle']
            }
        };

        const rawFiles = [
            { file: 'clavier-music-song-from-a-secret-garden-sad-piano-205576.mp3', genre: 'piano' },
            { file: 'sigmamusicart-emotional-piano-music-256262.mp3', genre: 'piano' },
            { file: 'nickpanekaiassets-peaceful-piano-background-music-218762.mp3', genre: 'piano' },
            { file: 'paulyudin-piano-background-182519.mp3', genre: 'piano' },
            { file: 'viacheslavstarostin-piano-background-music-soft-344547.mp3', genre: 'piano' },

            { file: 'good_b_music-ambient-piano-and-strings-10711.mp3', genre: 'ambient' },
            { file: 'music_for_video-please-calm-my-mind-125566.mp3', genre: 'ambient' },
            { file: 'the_mountain-soft-background-music-492811.mp3', genre: 'ambient' },
            { file: 'joyinsound-inspiring-soft-corporate-background-music-391736.mp3', genre: 'ambient' },
            { file: 'sigmamusicart-inspiring-inspirational-background-music-412596.mp3', genre: 'ambient' },

            { file: 'sergepavkinmusic-field-grass-115973.mp3', genre: 'nature' },
            { file: 'the_mountain-piano-background-music-487020.mp3', genre: 'nature' },
            { file: 'trtasfiq-sad-piano-instrumental-background-music-279069.mp3', genre: 'nature' },
            { file: 'white_records-legacy-of-vivaldi-epic-background-orchestral-music-hip-hop-version-143986.mp3', genre: 'nature' },
            { file: 'joyinsound-corporate-upbeat-motivational-music-403406.mp3', genre: 'nature' },

            { file: 'ikoliks_aj-jazz-lounge-elevator-music-332339.mp3', genre: 'lofi' },
            { file: '34910776-for-her-chill-upbeat-summel-travel-vlog-and-ig-music-royalty-free-use-202298.mp3', genre: 'lofi' },
            { file: 'lnplusmusic-vlogs-background-music-335289.mp3', genre: 'lofi' },
            { file: 'kontraa-hype-drill-music-438398.mp3', genre: 'lofi' },
            { file: 'paulyudin-happy-happy-music-513014.mp3', genre: 'lofi' }
        ];

        const songs = rawFiles.map((item, i) => {
            const title = this._cleanFileName(item.file);
            return {
                id: i + 1,
                title: title,
                artist: this._genreArtist(item.genre),
                genre: item.genre,
                duration: this._estimateDuration(item.file),
                audioUrl: `/audio/${item.file}`
            };
        });

        return songs.map((song, i) => {
            const g = genres[song.genre];
            const shapeIdx = i % g.shapes.length;
            song.coverSvg = this._generateCoverSvg(g.shapes[shapeIdx], g.colors, song.genre, song.id);
            return song;
        });
    }

    _cleanFileName(filename) {
        let name = filename.replace(/\.mp3$/i, '');
        name = name.replace(/^\d+-/, '');
        name = name.replace(/_+/g, ' ');
        name = name.replace(/-/g, ' ');
        const parts = name.split(/\s+/);
        const stopWords = new Set(['music', 'background', 'royalty', 'free', 'use', 'for', 'and', 'the', 'of', 'video', 'vlog', 'ig']);
        const filtered = parts.filter(p => !stopWords.has(p.toLowerCase()) && !/^\d{5,}$/.test(p));
        const title = filtered.map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(' ');
        return title || name.replace(/\.mp3$/i, '');
    }

    _genreArtist(genre) {
        const map = { piano: 'Piano Collection', ambient: 'Ambient Space', nature: 'Nature Sound', lofi: 'Lofi Beats' };
        return map[genre] || 'Star-Learn';
    }

    _estimateDuration(filename) {
        let hash = 0;
        for (let i = 0; i < filename.length; i++) hash = ((hash << 5) - hash) + filename.charCodeAt(i);
        const mins = 3 + Math.abs(hash % 6);
        const secs = Math.abs((hash >> 8) % 60);
        return `${mins}:${String(secs).padStart(2, '0')}`;
    }

    _generateCoverSvg(shape, colors, genre, songId) {
        const [c1, c2, c3] = colors;
        let shapeEl = '';

        switch (shape) {
            case 'circle':
                shapeEl = `<circle cx="20" cy="20" r="10" fill="${c3}" opacity="0.9"/><circle cx="20" cy="20" r="5" fill="white" opacity="0.6"/>`;
                break;
            case 'diamond':
                shapeEl = `<rect x="10" y="10" width="14" height="14" rx="2" fill="${c3}" opacity="0.9" transform="rotate(45 17 17)"/><rect x="14" y="14" width="6" height="6" rx="1" fill="white" opacity="0.5" transform="rotate(45 17 17)"/>`;
                break;
            case 'hexagon':
                shapeEl = `<polygon points="20,6 30,12 30,24 20,30 10,24 10,12" fill="${c3}" opacity="0.9"/><polygon points="20,11 25,14 25,22 20,25 15,22 15,14" fill="white" opacity="0.4"/>`;
                break;
            case 'star':
                shapeEl = `<polygon points="20,4 23,14 34,14 25,20 28,30 20,24 12,30 15,20 6,14 17,14" fill="${c3}" opacity="0.9"/><circle cx="20" cy="18" r="3" fill="white" opacity="0.5"/>`;
                break;
            case 'triangle':
                shapeEl = `<polygon points="20,6 32,28 8,28" fill="${c3}" opacity="0.9"/><polygon points="20,13 26,25 14,25" fill="white" opacity="0.4"/>`;
                break;
        }

        const icons = {
            piano: `<rect x="8" y="24" width="3" height="8" rx="0.5" fill="white" opacity="0.7"/><rect x="13" y="24" width="3" height="8" rx="0.5" fill="white" opacity="0.7"/><rect x="18" y="24" width="3" height="8" rx="0.5" fill="white" opacity="0.7"/><rect x="23" y="24" width="3" height="8" rx="0.5" fill="white" opacity="0.7"/><rect x="28" y="24" width="3" height="8" rx="0.5" fill="white" opacity="0.7"/>`,
            ambient: `<circle cx="12" cy="28" r="3" fill="white" opacity="0.5"/><circle cx="20" cy="26" r="4" fill="white" opacity="0.6"/><circle cx="28" cy="28" r="3" fill="white" opacity="0.5"/>`,
            nature: `<path d="M20 28 Q14 22 14 18 Q14 14 20 12 Q26 14 26 18 Q26 22 20 28Z" fill="white" opacity="0.6"/><line x1="20" y1="28" x2="20" y2="32" stroke="white" opacity="0.5" stroke-width="1.5"/>`,
            lofi: `<rect x="10" y="22" width="20" height="12" rx="2" fill="white" opacity="0.5"/><circle cx="16" cy="28" r="3" fill="${c2}" opacity="0.8"/><circle cx="24" cy="28" r="3" fill="${c2}" opacity="0.8"/>`
        };

        const uid = `bg_${songId}_${shape}`;
        return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40">
            <defs><linearGradient id="${uid}" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="${c1}"/><stop offset="100%" stop-color="${c2}"/>
            </linearGradient></defs>
            <rect width="40" height="40" rx="8" fill="url(#${uid})"/>
            ${shapeEl}
            ${icons[genre] || ''}
        </svg>`;
    }

    _renderGenres() {
        const container = document.getElementById('music-genres');
        if (!container) return;

        const genres = [
            { key: 'all', label: '全部' },
            { key: 'piano', label: '经典钢琴' },
            { key: 'ambient', label: '环境音乐' },
            { key: 'nature', label: '自然声' },
            { key: 'lofi', label: '低保真' }
        ];

        container.innerHTML = genres.map(g =>
            `<button class="music-genre-chip shrink-0 whitespace-nowrap${g.key === this.currentGenre ? ' active' : ''}" data-genre="${g.key}" onclick="window.musicPanel.filterGenre('${g.key}')">${g.label}</button>`
        ).join('');
    }

    _renderList() {
        const container = document.getElementById('music-list');
        if (!container) return;

        const filtered = this.currentGenre === 'all'
            ? this.songs
            : this.songs.filter(s => s.genre === this.currentGenre);

        container.innerHTML = filtered.map(song => {
            const isPlaying = this.currentIndex >= 0 && this.songs[this.currentIndex].id === song.id;
            return `<div class="music-item${isPlaying ? ' playing' : ''}" data-id="${song.id}" onclick="window.musicPanel.play(${song.id})">
                <div class="music-item-cover">${song.coverSvg}</div>
                <div class="music-item-info">
                    <div class="music-item-title">${song.title}</div>
                    <div class="music-item-meta">
                        <span>${song.artist}</span>
                        <span>·</span>
                        <span>${this._genreLabel(song.genre)}</span>
                    </div>
                </div>
                <div class="music-item-duration">${song.duration}</div>
                <div class="music-item-playing-indicator">
                    <div class="music-playing-bar"></div>
                    <div class="music-playing-bar"></div>
                    <div class="music-playing-bar"></div>
                </div>
            </div>`;
        }).join('');
    }

    _genreLabel(genre) {
        const map = { piano: '钢琴', ambient: '环境', nature: '自然', lofi: 'Lofi' };
        return map[genre] || genre;
    }

    _updatePlayerUI() {
        const titleEl = document.getElementById('music-player-title');
        const artistEl = document.getElementById('music-player-artist');
        const coverEl = document.getElementById('music-player-cover');
        const playIcon = document.getElementById('music-play-icon');
        const toggleBtn = document.getElementById('music-toggle-btn');

        if (this.currentIndex >= 0) {
            const song = this.songs[this.currentIndex];
            if (titleEl) titleEl.textContent = song.title;
            if (artistEl) artistEl.textContent = song.artist;
            if (coverEl) coverEl.innerHTML = song.coverSvg;
        } else {
            if (titleEl) titleEl.textContent = '未选择音乐';
            if (artistEl) artistEl.textContent = '--';
            if (coverEl) coverEl.innerHTML = '';
        }

        if (playIcon) {
            playIcon.innerHTML = this.isPlaying
                ? '<rect x="6" y="4" width="4" height="16" rx="1"></rect><rect x="14" y="4" width="4" height="16" rx="1"></rect>'
                : '<polygon points="5 3 19 12 5 21 5 3"></polygon>';
        }

        if (toggleBtn) {
            toggleBtn.classList.toggle('is-playing', this.isPlaying);
        }

        this._updateMiniPlayer();

        if (window.flowMode && window.flowMode.active) {
            window.flowMode._syncFlowMusicPlayer();
            window.flowMode._renderFlowMusicList();
        }
        if (window.flowMode) {
            window.flowMode.syncVisualizers();
        }
    }

    _updateListItemStates() {
        const items = document.querySelectorAll('.music-item');
        items.forEach(item => {
            const id = parseInt(item.dataset.id);
            const isCurrent = this.currentIndex >= 0 && this.songs[this.currentIndex].id === id;
            item.classList.toggle('playing', isCurrent && this.isPlaying);
        });
    }

    toggle() {
        const panel = document.getElementById('music-panel');
        if (!panel) return;
        this.isOpen = !this.isOpen;
        panel.classList.toggle('open', this.isOpen);
        if (this.isOpen) {
            this._renderGenres();
            this._renderList();
            if (window.focusDurationPanel && window.focusDurationPanel.isOpen) {
                window.focusDurationPanel.toggle();
            }
        }
        const miniPlayer = document.getElementById('mini-player');
        if (miniPlayer && this.currentIndex >= 0) {
            miniPlayer.classList.toggle('visible', !this.isOpen);
        }
    }

    filterGenre(genre) {
        this.currentGenre = genre;
        this._renderGenres();
        this._renderList();
    }

    play(songId) {
        const idx = this.songs.findIndex(s => s.id === songId);
        if (idx < 0) return;

        if (this.currentIndex === idx && this.isPlaying) {
            this.togglePlay();
            return;
        }

        if (this.currentIndex === idx && !this.isPlaying) {
            this.audio.play().catch(() => {});
            this.isPlaying = true;
            this._updatePlayerUI();
            this._updateListItemStates();
            return;
        }

        this.audio.pause();
        this.audio.currentTime = 0;
        this.currentIndex = idx;
        this.audio.src = this.songs[idx].audioUrl;
        this.audio.play().then(() => {
            this.isPlaying = true;
            this._updatePlayerUI();
            this._updateListItemStates();
        }).catch((err) => {
            console.warn('[MusicPanel] Play failed:', err);
            this._showError('音频加载失败，请稍后重试');
        });
    }

    togglePlay() {
        if (this.currentIndex < 0) {
            if (this.songs.length > 0) {
                this.play(this.songs[0].id);
            }
            return;
        }

        if (this.isPlaying) {
            this.audio.pause();
            this.isPlaying = false;
        } else {
            this.audio.play().catch(() => {
                this._showError('播放失败，请检查网络连接');
            });
            this.isPlaying = true;
        }
        this._updatePlayerUI();
        this._updateListItemStates();
    }

    prev() {
        if (this.songs.length === 0) return;

        if (this.currentGenre !== 'all') {
            const filtered = this.songs.filter(s => s.genre === this.currentGenre);
            if (filtered.length === 0) return;
            if (this.currentIndex < 0) { this.play(filtered[filtered.length - 1].id); return; }
            const currentSong = this.songs[this.currentIndex];
            const fIdx = filtered.findIndex(s => s.id === currentSong.id);
            const prevIdx = fIdx <= 0 ? filtered.length - 1 : fIdx - 1;
            this.play(filtered[prevIdx].id);
            return;
        }

        const idx = this.currentIndex < 0 ? this.songs.length - 1 : (this.currentIndex - 1 + this.songs.length) % this.songs.length;
        this.play(this.songs[idx].id);
    }

    next() {
        if (this.songs.length === 0) return;

        if (this.currentGenre !== 'all') {
            const filtered = this.songs.filter(s => s.genre === this.currentGenre);
            if (filtered.length === 0) return;
            if (this.currentIndex < 0) { this.play(filtered[0].id); return; }
            const currentSong = this.songs[this.currentIndex];
            const fIdx = filtered.findIndex(s => s.id === currentSong.id);
            const nextIdx = fIdx >= filtered.length - 1 ? 0 : fIdx + 1;
            this.play(filtered[nextIdx].id);
            return;
        }

        const idx = this.currentIndex < 0 ? 0 : (this.currentIndex + 1) % this.songs.length;
        this.play(this.songs[idx].id);
    }

    _onAudioError(e) {
        console.error('[MusicPanel] Audio error:', e);
        this.isPlaying = false;
        this._updatePlayerUI();
        this._updateListItemStates();
        this._showError('音频加载失败，请检查网络');
    }

    _onAudioEnded() {
        this.next();
    }

    _showError(msg) {
        const existing = document.querySelector('.music-error-toast');
        if (existing) existing.remove();

        const toast = document.createElement('div');
        toast.className = 'music-error-toast';
        toast.textContent = msg;
        Object.assign(toast.style, {
            position: 'fixed',
            bottom: '80px',
            right: '20px',
            background: 'var(--danger)',
            color: 'var(--text-on-accent)',
            padding: '8px 16px',
            borderRadius: '10px',
            fontSize: '12px',
            fontWeight: '600',
            zIndex: '300',
            backdropFilter: 'blur(10px)',
            boxShadow: '0 4px 12px var(--danger-bg)',
            animation: 'fadeInUp 0.3s ease',
            pointerEvents: 'none'
        });
        document.body.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transition = 'opacity 0.3s';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    _updateMiniPlayer() {
        const miniPlayer = document.getElementById('mini-player');
        const miniTitle = document.getElementById('mini-player-title');
        const miniPlayIcon = document.getElementById('mini-play-icon');

        if (!miniPlayer) return;

        const shouldShow = this.currentIndex >= 0;
        miniPlayer.classList.toggle('visible', shouldShow);

        if (miniTitle && this.currentIndex >= 0) {
            miniTitle.textContent = this.songs[this.currentIndex].title;
        } else if (miniTitle) {
            miniTitle.textContent = '未在播放';
        }

        if (miniPlayIcon) {
            miniPlayIcon.innerHTML = this.isPlaying
                ? '<rect x="6" y="4" width="4" height="16" rx="1"></rect><rect x="14" y="4" width="4" height="16" rx="1"></rect>'
                : '<polygon points="5 3 19 12 5 21 5 3"></polygon>';
        }
    }

    setVolume(val) {
        const volume = Math.max(0, Math.min(100, parseInt(val)));
        this.audio.volume = volume / 100;
        const slider = document.getElementById('music-volume-slider');
        const label = document.getElementById('music-volume-label');
        if (slider) slider.value = volume;
        if (label) label.textContent = volume;
        this._updateVolumeIcon();
    }

    toggleMute() {
        if (this.audio.volume > 0) {
            this._previousVolume = this.audio.volume * 100;
            this.audio.volume = 0;
            const slider = document.getElementById('music-volume-slider');
            const label = document.getElementById('music-volume-label');
            if (slider) slider.value = 0;
            if (label) label.textContent = '0';
        } else {
            const vol = this._previousVolume || 60;
            this.audio.volume = vol / 100;
            const slider = document.getElementById('music-volume-slider');
            const label = document.getElementById('music-volume-label');
            if (slider) slider.value = vol;
            if (label) label.textContent = vol;
        }
        this._updateVolumeIcon();
    }

    _updateVolumeIcon() {
        const iconEl = document.getElementById('music-volume-icon');
        if (!iconEl) return;
        const vol = this.audio.volume;
        if (vol === 0) {
            iconEl.innerHTML = '<line x1="1" y1="1" x2="23" y2="23"></line><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>';
        } else if (vol < 0.5) {
            iconEl.innerHTML = '<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path>';
        } else {
            iconEl.innerHTML = '<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path><path d="M19.07 4.93a10 10 0 0 1 0 14.14"></path>';
        }
    }

    destroy() {
        this.audio.pause();
        this.audio.removeEventListener('error', this._boundOnError);
        this.audio.removeEventListener('ended', this._boundOnEnded);
        this.audio.src = '';
    }
}

window.musicPanel = new MusicPanel();

class FocusDurationPanel {
    constructor() {
        this.isOpen = false;
        this.selectedMinutes = 25;
        this.selectionType = 'preset';
        this.currentMode = 'focus';
        this._initialized = false;
        this.presets = {
            focus: [
                { minutes: 5, label: '5 分钟', sub: '快速' },
                { minutes: 10, label: '10 分钟', sub: '短时' },
                { minutes: 15, label: '15 分钟', sub: '适中' },
                { minutes: 30, label: '30 分钟', sub: '标准' },
                { minutes: 45, label: '45 分钟', sub: '深度' },
                { minutes: 60, label: '60 分钟', sub: '沉浸' }
            ],
            rest: [
                { minutes: 3, label: '3 分钟', sub: '微休' },
                { minutes: 5, label: '5 分钟', sub: '短休' },
                { minutes: 10, label: '10 分钟', sub: '小憩' },
                { minutes: 15, label: '15 分钟', sub: '放松' },
                { minutes: 20, label: '20 分钟', sub: '充电' },
                { minutes: 30, label: '30 分钟', sub: '深度' }
            ]
        };
        this.recentDurations = this._loadRecent();
        this._debounceTimer = null;
    }

    init() {
        if (this._initialized) return;
        this._initialized = true;
        this._renderPresets();
        this._renderRecent();
        this._bindInputEvents();
        this._updateToggleBtn();
    }

    _loadRecent() {
        try {
            return JSON.parse(localStorage.getItem('starlearn_focus_recent') || '[]');
        } catch { return []; }
    }

    _saveRecent(minutes) {
        let recent = this.recentDurations.filter(m => m !== minutes);
        recent.unshift(minutes);
        recent = recent.slice(0, 3);
        this.recentDurations = recent;
        localStorage.setItem('starlearn_focus_recent', JSON.stringify(recent));
    }

    _renderPresets() {
        const container = document.getElementById('focus-presets');
        if (!container) return;

        const presets = this.presets[this.currentMode] || this.presets.focus;
        container.innerHTML = presets.map(p => {
            const isSelected = this.selectedMinutes === p.minutes && this.selectionType === 'preset';
            return `<button class="focus-preset-btn${isSelected ? ' selected' : ''}" data-minutes="${p.minutes}" onclick="window.focusDurationPanel.selectPreset(${p.minutes})">
                <span class="preset-label">${p.label}</span>
                <span class="preset-sub">${p.sub}</span>
            </button>`;
        }).join('');
    }

    _renderRecent() {
        const container = document.getElementById('focus-recent');
        if (!container) return;

        if (this.recentDurations.length === 0) {
            container.innerHTML = '';
            return;
        }

        container.innerHTML = `
            <div class="focus-recent-label">最近使用</div>
            <div class="focus-recent-chips">
                ${this.recentDurations.map(m =>
                    `<button class="focus-recent-chip" onclick="window.focusDurationPanel.selectPreset(${m})">${m}分钟</button>`
                ).join('')}
            </div>`;
    }

    _bindInputEvents() {
        const input = document.getElementById('focus-custom-input');
        if (!input) return;

        input.addEventListener('input', () => {
            const val = input.value.replace(/[^\d]/g, '');
            input.value = val;
            this._clearError();
            input.classList.remove('success', 'invalid');
        });

        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.confirmCustom();
            }
        });
    }

    toggle() {
        this.init();
        const panel = document.getElementById('focus-duration-panel');
        if (!panel) return;
        this.isOpen = !this.isOpen;
        panel.classList.toggle('open', this.isOpen);
        if (this.isOpen && window.musicPanel && window.musicPanel.isOpen) {
            window.musicPanel.toggle();
        }
    }

    switchMode(mode) {
        if (this.currentMode === mode) return;
        this.currentMode = mode;
        this.selectedMinutes = mode === 'focus' ? 25 : 5;
        this.selectionType = 'preset';

        const panel = document.getElementById('focus-duration-panel');
        if (panel) panel.classList.toggle('rest-mode', mode === 'rest');

        document.querySelectorAll('.focus-mode-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.mode === mode);
        });

        this._renderPresets();
        this._updateToggleBtn();

        const input = document.getElementById('focus-custom-input');
        if (input) { input.value = ''; input.classList.remove('invalid', 'success'); }
        this._clearError();
    }

    selectPreset(minutes) {
        this.selectedMinutes = minutes;
        this.selectionType = 'preset';
        this._renderPresets();
        this._updateToggleBtn();
        this._animateSelection(minutes);

        const input = document.getElementById('focus-custom-input');
        if (input) {
            input.value = '';
            input.classList.remove('invalid', 'success');
        }
        this._clearError();
    }

    _animateSelection(minutes) {
        const btn = document.querySelector(`.focus-preset-btn[data-minutes="${minutes}"]`);
        if (!btn) return;
        btn.classList.remove('just-selected');
        void btn.offsetWidth;
        btn.classList.add('just-selected');
        setTimeout(() => btn.classList.remove('just-selected'), 300);
    }

    confirmCustom() {
        const input = document.getElementById('focus-custom-input');
        if (!input) return;

        const raw = input.value.trim();
        if (!raw) {
            this._showError('请输入时长');
            input.classList.add('invalid');
            return;
        }

        const minutes = parseInt(raw, 10);

        if (isNaN(minutes)) {
            this._showError('请输入有效数字');
            input.classList.add('invalid');
            return;
        }

        if (minutes < 1 || minutes > 180) {
            this._showError('时长范围：1-180 分钟');
            input.classList.add('invalid');
            return;
        }

        this.selectedMinutes = minutes;
        this.selectionType = 'custom';
        this._renderPresets();
        this._updateToggleBtn();

        input.classList.remove('invalid');
        input.classList.add('success');
        this._clearError();

        const confirmBtn = document.getElementById('focus-custom-confirm');
        if (confirmBtn) {
            confirmBtn.classList.add('success-flash');
            setTimeout(() => confirmBtn.classList.remove('success-flash'), 400);
        }

        setTimeout(() => {
            input.classList.remove('success');
        }, 1500);
    }

    startFocus() {
        const minutes = this.selectedMinutes;
        if (!minutes || minutes < 1) {
            this._showError('请先选择时长');
            return;
        }

        this._saveRecent(minutes);
        this._renderRecent();

        if (window.flowMode) {
            const totalSeconds = minutes * 60;
            window.flowMode.totalSeconds = totalSeconds;
            window.flowMode.remainingSeconds = totalSeconds;
            window.flowMode.currentMode = this.currentMode;
            window.flowMode.selectedMinutes = minutes;
            window.flowMode.state.update({
                total_time: totalSeconds,
                remaining_time: totalSeconds,
                is_timer_running: false,
                is_paused: false,
                is_complete: false
            });

            const island = document.getElementById('flow-dynamic-island');
            if (island) {
                island.classList.toggle('rest-mode', this.currentMode === 'rest');
                island.classList.toggle('flow-island-rest', this.currentMode === 'rest');
            }

            const islandLabel = document.getElementById('island-timer-label');
            if (islandLabel) {
                islandLabel.textContent = this.currentMode === 'rest' ? '休息模式' : '专注模式';
            }

            const overlay = document.getElementById('flow-overlay');
            if (overlay) overlay.classList.toggle('rest-mode', this.currentMode === 'rest');

            if (!window.flowMode.active) {
                window.flowMode.enter();
            } else {
                window.flowMode.resetTimer();
                window.flowMode._renderFlowPresets();
            }
        }

        if (this.isOpen) {
            this.toggle();
        }
    }

    _updateToggleBtn() {
        const btn = document.getElementById('focus-duration-toggle-btn');
        if (!btn) return;
        btn.classList.toggle('has-selection', this.selectedMinutes > 0);
    }

    _showError(msg) {
        const el = document.getElementById('focus-duration-error');
        if (!el) return;
        el.textContent = msg;
        el.classList.add('visible');
    }

    _clearError() {
        const el = document.getElementById('focus-duration-error');
        if (!el) return;
        el.classList.remove('visible');
    }
}

window.focusDurationPanel = new FocusDurationPanel();