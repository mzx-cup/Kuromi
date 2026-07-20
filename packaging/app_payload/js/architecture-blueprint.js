// ============================================
// 创世·架构蓝图引擎 - JavaScript
// ============================================

// 项目模板库
const projectTemplates = {
    '校园二手交易平台': {
        projectName: '校园二手交易平台',
        projectDesc: '面向校园的C2C闲置物品交易平台，支持实名认证、在线支付、校园配送',
        techStack: {
            frontend: { name: '前端技术栈', icon: '🎨', items: [
                { name: 'Vue 3', desc: '渐进式响应式框架', level: 90 },
                { name: 'Vite', desc: '下一代前端构建工具', level: 85 },
                { name: 'TailwindCSS', desc: '原子化 CSS 框架', level: 88 },
                { name: 'Pinia', desc: 'Vue 状态管理方案', level: 82 },
                { name: 'Vue Router', desc: 'SPA 路由管理', level: 90 }
            ]},
            backend: { name: '后端技术栈', icon: '⚙️', items: [
                { name: 'Spring Boot 3', desc: '企业级 Java 框架', level: 90 },
                { name: 'Spring Cloud', desc: '微服务架构套件', level: 85 },
                { name: 'MySQL 8', desc: '关系型数据库', level: 88 },
                { name: 'Redis', desc: '分布式缓存与Session共享', level: 85 },
                { name: 'RabbitMQ', desc: '异步消息队列', level: 80 }
            ]},
            devops: { name: 'DevOps 工具链', icon: '🚀', items: [
                { name: 'Docker', desc: '容器化部署', level: 90 },
                { name: 'K8s', desc: '容器编排平台', level: 75 },
                { name: 'Jenkins', desc: 'CI/CD 持续集成', level: 85 },
                { name: 'GitLab', desc: '代码仓库与协作', level: 88 },
                { name: 'Prometheus', desc: '监控与告警', level: 78 }
            ]}
        },
        dataModels: [
            { name: 'User', alias: '用户表', icon: '👤', fields: [
                { name: 'user_id', type: 'BIGINT', key: 'PK', desc: '用户唯一标识' },
                { name: 'username', type: 'VARCHAR(50)', key: null, desc: '用户名' },
                { name: 'email', type: 'VARCHAR(100)', key: null, desc: '邮箱' },
                { name: 'phone', type: 'VARCHAR(20)', key: null, desc: '手机号' },
                { name: 'password_hash', type: 'VARCHAR(255)', key: null, desc: '密码哈希' },
                { name: 'school_id', type: 'INT', key: 'FK', desc: '所属学校' },
                { name: 'created_at', type: 'TIMESTAMP', key: null, desc: '注册时间' },
                { name: 'is_verified', type: 'BOOLEAN', key: null, desc: '是否实名认证' }
            ]},
            { name: 'Product', alias: '商品表', icon: '📦', fields: [
                { name: 'product_id', type: 'BIGINT', key: 'PK', desc: '商品唯一标识' },
                { name: 'seller_id', type: 'BIGINT', key: 'FK', desc: '卖家ID' },
                { name: 'title', type: 'VARCHAR(200)', key: null, desc: '商品标题' },
                { name: 'description', type: 'TEXT', key: null, desc: '商品描述' },
                { name: 'category_id', type: 'INT', key: 'FK', desc: '分类ID' },
                { name: 'price', type: 'DECIMAL(10,2)', key: null, desc: '标价' },
                { name: 'status', type: 'ENUM', key: null, desc: '在售/已售/下架' },
                { name: 'created_at', type: 'TIMESTAMP', key: null, desc: '发布时间' }
            ]},
            { name: 'Order', alias: '订单表', icon: '📋', fields: [
                { name: 'order_id', type: 'BIGINT', key: 'PK', desc: '订单唯一标识' },
                { name: 'product_id', type: 'BIGINT', key: 'FK', desc: '商品ID' },
                { name: 'buyer_id', type: 'BIGINT', key: 'FK', desc: '买家ID' },
                { name: 'seller_id', type: 'BIGINT', key: 'FK', desc: '卖家ID' },
                { name: 'amount', type: 'DECIMAL(10,2)', key: null, desc: '成交金额' },
                { name: 'status', type: 'ENUM', key: null, desc: '待支付/已支付/已完成/已取消' },
                { name: 'created_at', type: 'TIMESTAMP', key: null, desc: '下单时间' }
            ]}
        ],
        milestones: [
            { week: 'Week 1', theme: '需求分析与架构设计', tasks: [
                { text: '完成用户调研与需求文档', done: false },
                { text: '系统架构设计与评审', done: false },
                { text: '数据库表结构设计', done: false },
                { text: 'API 接口文档编写', done: false }
            ]},
            { week: 'Week 2', theme: '核心功能开发', tasks: [
                { text: '用户认证模块开发', done: false },
                { text: '商品发布与搜索功能', done: false },
                { text: '分类与标签系统', done: false },
                { text: '图片上传与CDN集成', done: false }
            ]},
            { week: 'Week 3', theme: '交易与支付流程', tasks: [
                { text: '订单模块开发', done: false },
                { text: '支付宝/微信支付集成', done: false },
                { text: '消息通知系统', done: false },
                { text: '用户评价体系', done: false }
            ]},
            { week: 'Week 4', theme: '测试与部署上线', tasks: [
                { text: '功能测试与Bug修复', done: false },
                { text: '性能压力测试', done: false },
                { text: '安全审计与加固', done: false },
                { text: '生产环境部署上线', done: false }
            ]}
        ]
    },
    '在线教育平台': {
        projectName: '在线教育平台',
        projectDesc: 'K12在线教育平台，支持直播上课、作业批改、学习数据分析',
        techStack: {
            frontend: { name: '前端技术栈', icon: '🎨', items: [
                { name: 'React 18', desc: 'UI 组件库', level: 92 },
                { name: 'Next.js', desc: 'SSR 框架', level: 88 },
                { name: 'TypeScript', desc: '类型安全', level: 90 },
                { name: 'Zustand', desc: '状态管理', level: 85 },
                { name: 'TailwindCSS', desc: '样式框架', level: 88 }
            ]},
            backend: { name: '后端技术栈', icon: '⚙️', items: [
                { name: 'Node.js', desc: 'Runtime', level: 88 },
                { name: 'NestJS', desc: '企业级框架', level: 85 },
                { name: 'PostgreSQL', desc: '主数据库', level: 90 },
                { name: 'MongoDB', desc: '日志存储', level: 82 },
                { name: 'Elasticsearch', desc: '搜索服务', level: 80 }
            ]},
            devops: { name: 'DevOps 工具链', icon: '🚀', items: [
                { name: 'Docker', desc: '容器化', level: 92 },
                { name: 'AWS', desc: '云服务', level: 85 },
                { name: 'GitHub Actions', desc: 'CI/CD', level: 88 },
                { name: 'Terraform', desc: 'IaC', level: 78 },
                { name: 'Datadog', desc: '监控', level: 80 }
            ]}
        },
        dataModels: [
            { name: 'Course', alias: '课程表', icon: '📚', fields: [
                { name: 'course_id', type: 'BIGINT', key: 'PK', desc: '课程ID' },
                { name: 'teacher_id', type: 'BIGINT', key: 'FK', desc: '教师ID' },
                { name: 'title', type: 'VARCHAR(200)', key: null, desc: '课程名' },
                { name: 'description', type: 'TEXT', key: null, desc: '课程描述' },
                { name: 'price', type: 'DECIMAL(10,2)', key: null, desc: '价格' },
                { name: 'created_at', type: 'TIMESTAMP', key: null, desc: '创建时间' }
            ]},
            { name: 'Student', alias: '学生表', icon: '👨‍🎓', fields: [
                { name: 'student_id', type: 'BIGINT', key: 'PK', desc: '学生ID' },
                { name: 'name', type: 'VARCHAR(100)', key: null, desc: '姓名' },
                { name: 'email', type: 'VARCHAR(100)', key: null, desc: '邮箱' },
                { name: 'grade', type: 'INT', key: null, desc: '年级' },
                { name: 'created_at', type: 'TIMESTAMP', key: null, desc: '注册时间' }
            ]},
            { name: 'Enrollment', alias: '选课表', icon: '📝', fields: [
                { name: 'enroll_id', type: 'BIGINT', key: 'PK', desc: '选课ID' },
                { name: 'course_id', type: 'BIGINT', key: 'FK', desc: '课程ID' },
                { name: 'student_id', type: 'BIGINT', key: 'FK', desc: '学生ID' },
                { name: 'progress', type: 'FLOAT', key: null, desc: '学习进度' },
                { name: 'enrolled_at', type: 'TIMESTAMP', key: null, desc: '选课时间' }
            ]}
        ],
        milestones: [
            { week: 'Week 1-2', theme: '基础架构搭建', tasks: [
                { text: '项目脚手架与规范', done: false },
                { text: '数据库设计与实现', done: false },
                { text: '用户认证模块', done: false },
                { text: '课程管理CRUD', done: false }
            ]},
            { week: 'Week 3-4', theme: '核心功能开发', tasks: [
                { text: '直播上课功能', done: false },
                { text: '作业系统开发', done: false },
                { text: '在线支付集成', done: false },
                { text: '消息通知系统', done: false }
            ]},
            { week: 'Week 5-6', theme: '高级功能', tasks: [
                { text: '学习数据分析', done: false },
                { text: '智能推荐算法', done: false },
                { text: '在线评测系统', done: false },
                { text: '移动端适配', done: false }
            ]},
            { week: 'Week 7-8', theme: '测试与上线', tasks: [
                { text: '全链路测试', done: false },
                { text: '性能优化', done: false },
                { text: '安全加固', done: false },
                { text: '灰度发布', done: false }
            ]}
        ]
    }
};

// Loading 消息
const loadingMessages = [
    '🔍 正在分析需求关键词...',
    '🏗️ 正在规划微服务架构边界...',
    '⚡ 正在推演高并发瓶颈场景...',
    '💾 正在设计数据持久化方案...',
    '📊 正在生成开发里程碑...',
    '✨ 架构蓝图生成完成！'
];

// 全局状态
let state = {
    currentProjectId: null,
    projects: [],
    currentTab: 'tech-stack',
    isLoading: false,
    hasGenerated: false,
    generatingStep: 0
};

// DOM 缓存
let domCache = {};

// ============================================
// 初始化
// ============================================
function initDOMCache() {
    domCache = {
        promptInput: document.getElementById('prompt-input'),
        generateBtn: document.getElementById('generate-btn'),
        loadingArea: document.getElementById('loading-area'),
        loadingText: document.getElementById('loading-text'),
        blueprintContent: document.getElementById('blueprint-content'),
        projectTitle: document.getElementById('project-title'),
        projectDesc: document.getElementById('project-desc'),
        contentArea: document.getElementById('content-area'),
        projectsList: document.getElementById('projects-list'),
        projectsPanel: document.getElementById('projects-panel'),
        newProjectBtn: document.getElementById('new-project-btn'),
        tabTech: document.getElementById('tab-tech'),
        tabData: document.getElementById('tab-data'),
        tabTimeline: document.getElementById('tab-timeline')
    };
}

function init() {
    initDOMCache();
    loadProjectsFromStorage();
    initEventListeners();
    renderProjectsList();

    // 检查 URL 参数
    const params = new URLSearchParams(window.location.search);
    const projectId = params.get('project');
    if (projectId && state.projects.find(p => p.id === projectId)) {
        loadProject(projectId);
    }
}

function initEventListeners() {
    // 输入框回车生成
    domCache.promptInput?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            generateBlueprint();
        }
    });

    // 生成按钮
    domCache.generateBtn?.addEventListener('click', generateBlueprint);

    // 新建项目按钮
    domCache.newProjectBtn?.addEventListener('click', () => {
        showInputMode();
    });

    // Tab 切换
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });

    // 导出按钮
    document.getElementById('btn-export-md')?.addEventListener('click', exportMarkdown);
    document.getElementById('btn-sync-calendar')?.addEventListener('click', syncToCalendar);

    // 模板快捷按钮
    document.querySelectorAll('.template-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            domCache.promptInput.value = btn.dataset.template;
        });
    });

    // 键盘快捷键
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            domCache.projectsPanel?.classList.add('hidden');
        }
    });
}

// ============================================
// 项目管理
// ============================================
function loadProjectsFromStorage() {
    try {
        const stored = localStorage.getItem('architecture_projects');
        if (stored) {
            state.projects = JSON.parse(stored);
        }
    } catch (e) {
        console.warn('Failed to load projects:', e);
    }
}

function saveProjectsToStorage() {
    try {
        localStorage.setItem('architecture_projects', JSON.stringify(state.projects));
    } catch (e) {
        console.warn('Failed to save projects:', e);
    }
}

function renderProjectsList() {
    if (!domCache.projectsList) return;

    if (state.projects.length === 0) {
        domCache.projectsList.innerHTML = `
            <div class="text-center text-gray-500 py-8">
                <div class="text-4xl mb-3">📁</div>
                <p class="text-sm">暂无项目</p>
                <p class="text-xs text-gray-600 mt-1">输入需求生成架构蓝图</p>
            </div>
        `;
        return;
    }

    domCache.projectsList.innerHTML = state.projects.map(project => `
        <div class="project-item ${project.id === state.currentProjectId ? 'active' : ''}" data-id="${project.id}">
            <div class="flex items-center justify-between">
                <div class="flex-1 min-w-0 cursor-pointer" onclick="loadProject('${project.id}')">
                    <div class="font-medium truncate">${project.data.projectName}</div>
                    <div class="text-xs text-gray-500 truncate">${project.data.projectDesc}</div>
                    <div class="text-xs text-indigo-400 mt-1">${new Date(project.updatedAt).toLocaleDateString()}</div>
                </div>
                <button class="delete-btn ml-2 p-1 hover:bg-red-500/20 rounded" onclick="deleteProject('${project.id}', event)">
                    <svg class="w-4 h-4 text-gray-500 hover:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                    </svg>
                </button>
            </div>
        </div>
    `).join('');
}

function loadProject(projectId) {
    const project = state.projects.find(p => p.id === projectId);
    if (!project) return;

    state.currentProjectId = projectId;
    state.hasGenerated = true;

    // 更新 URL
    const url = new URL(window.location);
    url.searchParams.set('project', projectId);
    window.history.pushState({}, '', url);

    // 显示项目内容
    domCache.blueprintContent.classList.remove('hidden');
    domCache.loadingArea.classList.add('hidden');

    // 更新标题
    domCache.projectTitle.textContent = `"${project.data.projectName}" 架构蓝图`;
    domCache.projectDesc.textContent = project.data.projectDesc;

    // 渲染当前 Tab
    renderCurrentTab();

    // 更新列表选中状态
    renderProjectsList();

    // 关闭侧边栏
    domCache.projectsPanel?.classList.add('hidden');
}

function deleteProject(projectId, event) {
    event.stopPropagation();

    if (!confirm('确定要删除该项目吗？')) return;

    state.projects = state.projects.filter(p => p.id !== projectId);
    saveProjectsToStorage();

    if (state.currentProjectId === projectId) {
        state.currentProjectId = null;
        state.hasGenerated = false;
        domCache.blueprintContent.classList.add('hidden');
    }

    renderProjectsList();
}

function showInputMode() {
    state.currentProjectId = null;
    state.hasGenerated = false;
    domCache.blueprintContent.classList.add('hidden');
    domCache.loadingArea.classList.add('hidden');
    domCache.promptInput.value = '';
    domCache.promptInput.focus();

    // 更新 URL
    const url = new URL(window.location);
    url.searchParams.delete('project');
    window.history.pushState({}, '', url);
}

// ============================================
// Tab 切换
// ============================================
function switchTab(tab) {
    state.currentTab = tab;

    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tab);
    });

    if (state.hasGenerated) {
        renderCurrentTab();
    }
}

function renderCurrentTab() {
    const project = state.projects.find(p => p.id === state.currentProjectId);
    if (!project) return;

    switch (state.currentTab) {
        case 'tech-stack':
            renderTechStack(project.data);
            break;
        case 'data-model':
            renderDataModel(project.data);
            break;
        case 'timeline':
            renderTimeline(project.data, project.id);
            break;
    }
}

// ============================================
// 生成架构蓝图
// ============================================
async function generateBlueprint() {
    const prompt = domCache.promptInput?.value.trim();
    if (!prompt) {
        domCache.promptInput?.focus();
        return;
    }

    state.isLoading = true;
    state.generatingStep = 0;
    state.hasGenerated = true;

    domCache.blueprintContent.classList.add('hidden');
    domCache.loadingArea.classList.remove('hidden');

    // 启动加载动画
    const messageInterval = setInterval(() => {
        if (state.generatingStep < loadingMessages.length) {
            domCache.loadingText.innerHTML = `<span class="loading-text">${loadingMessages[state.generatingStep]}</span>`;
            state.generatingStep++;
        }
    }, 700);

    // 模拟生成延迟
    await new Promise(resolve => setTimeout(resolve, 4500));

    clearInterval(messageInterval);

    // 选择模板或生成
    let blueprintData;
    if (projectTemplates[prompt]) {
        blueprintData = JSON.parse(JSON.stringify(projectTemplates[prompt]));
    } else {
        // 使用默认模板但修改名称
        blueprintData = JSON.parse(JSON.stringify(projectTemplates['校园二手交易平台']));
        blueprintData.projectName = prompt;
        blueprintData.projectDesc = `基于 "${prompt}" 的完整技术架构方案`;
    }

    // 保存项目
    const projectId = 'project_' + Date.now();
    const project = {
        id: projectId,
        prompt: prompt,
        data: blueprintData,
        createdAt: Date.now(),
        updatedAt: Date.now()
    };

    state.projects.unshift(project);
    state.currentProjectId = projectId;
    saveProjectsToStorage();

    state.isLoading = false;
    state.hasGenerated = true;

    // 更新 URL
    const url = new URL(window.location);
    url.searchParams.set('project', projectId);
    window.history.pushState({}, '', url);

    // 显示内容
    domCache.loadingArea.classList.add('hidden');
    domCache.blueprintContent.classList.remove('hidden');

    domCache.projectTitle.textContent = `"${blueprintData.projectName}" 架构蓝图`;
    domCache.projectDesc.textContent = blueprintData.projectDesc;

    renderCurrentTab();
    renderProjectsList();
}

// ============================================
// 渲染技术栈
// ============================================
function renderTechStack(data) {
    const { techStack } = data;
    const container = domCache.contentArea;

    container.innerHTML = `
        <div class="space-y-10">
            ${Object.entries(techStack).map(([key, stack]) => `
                <div class="tech-section">
                    <h3 class="text-lg font-semibold mb-5 flex items-center gap-3">
                        <span class="text-3xl">${stack.icon}</span>
                        <span class="text-gradient">${stack.name}</span>
                    </h3>
                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
                        ${stack.items.map((item, i) => `
                            <div class="tech-card" style="animation-delay: ${i * 100}ms">
                                <div class="tech-card-header">
                                    <span class="tech-name">${item.name}</span>
                                    <span class="tech-level">${item.level}%</span>
                                </div>
                                <div class="tech-desc">${item.desc}</div>
                                <div class="tech-progress">
                                    <div class="tech-progress-fill" style="width: ${item.level}%"></div>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}

// ============================================
// 渲染数据模型
// ============================================
function renderDataModel(data) {
    const { dataModels } = data;
    const container = domCache.contentArea;

    container.innerHTML = `
        <div class="er-diagram-container">
            <div class="er-legend">
                <span class="legend-item"><span class="legend-dot pk"></span>PK 主键</span>
                <span class="legend-item"><span class="legend-dot fk"></span>FK 外键</span>
                <span class="legend-item"><span class="legend-dot normal"></span>普通字段</span>
            </div>
            <div class="er-tables">
                ${dataModels.map((model, index) => `
                    <div class="er-table-wrapper">
                        ${renderERTable(model)}
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

function renderERTable(model) {
    const fieldIcons = { 'PK': '🔑', 'FK': '🔗', null: '○' };

    return `
        <div class="er-table">
            <div class="er-table-header">
                <span class="er-icon">${model.icon}</span>
                <span class="er-name">${model.name}</span>
                <span class="er-alias">${model.alias}</span>
            </div>
            <div class="er-table-body">
                ${model.fields.map(field => `
                    <div class="er-field">
                        <span class="er-field-icon ${field.key ? (field.key === 'PK' ? 'pk' : 'fk') : 'normal'}">${fieldIcons[field.key]}</span>
                        <span class="er-field-name">${field.name}</span>
                        <span class="er-field-type">${field.type}</span>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

// ============================================
// 渲染时间轴
// ============================================
function renderTimeline(data, projectId) {
    const { milestones } = data;
    const container = domCache.contentArea;

    // 找到当前周（第一个未完成的或最后一个）
    let currentWeekIndex = 0;
    for (let i = 0; i < milestones.length; i++) {
        if (milestones[i].tasks.some(t => !t.done)) {
            currentWeekIndex = i;
            break;
        }
        if (i === milestones.length - 1) currentWeekIndex = i;
    }

    container.innerHTML = `
        <div class="timeline-container">
            <div class="timeline-progress-bar">
                <div class="timeline-progress-fill" style="width: ${calculateProgress(milestones)}%"></div>
            </div>
            <div class="timeline">
                ${milestones.map((milestone, index) => {
                    const allDone = milestone.tasks.every(t => t.done);
                    const someDone = milestone.tasks.some(t => t.done);
                    let status = allDone ? 'completed' : (index === currentWeekIndex ? 'current' : 'pending');

                    return `
                        <div class="timeline-item ${status}">
                            <div class="timeline-marker">
                                ${allDone ? '✓' : index + 1}
                            </div>
                            <div class="timeline-content">
                                <div class="timeline-header">
                                    <span class="timeline-week">${milestone.week}</span>
                                    <span class="timeline-theme">${milestone.theme}</span>
                                </div>
                                <div class="timeline-tasks">
                                    ${milestone.tasks.map(task => `
                                        <label class="timeline-task ${task.done ? 'done' : ''}">
                                            <input type="checkbox" ${task.done ? 'checked' : ''}
                                                onchange="toggleTask('${projectId}', ${index}, '${task.text}')">
                                            <span class="task-text">${task.text}</span>
                                        </label>
                                    `).join('')}
                                </div>
                            </div>
                        </div>
                    `;
                }).join('')}
            </div>
            <div class="timeline-summary">
                <span>总进度: ${calculateProgress(milestones)}%</span>
                <span>已完成 ${countDoneTasks(milestones)} / ${countAllTasks(milestones)} 个任务</span>
            </div>
        </div>
    `;
}

function calculateProgress(milestones) {
    const total = milestones.reduce((sum, m) => sum + m.tasks.length, 0);
    const done = milestones.reduce((sum, m) => sum + m.tasks.filter(t => t.done).length, 0);
    return total > 0 ? Math.round((done / total) * 100) : 0;
}

function countDoneTasks(milestones) {
    return milestones.reduce((sum, m) => sum + m.tasks.filter(t => t.done).length, 0);
}

function countAllTasks(milestones) {
    return milestones.reduce((sum, m) => sum + m.tasks.length, 0);
}

function toggleTask(projectId, milestoneIndex, taskText) {
    const project = state.projects.find(p => p.id === projectId);
    if (!project) return;

    const milestone = project.data.milestones[milestoneIndex];
    const task = milestone.tasks.find(t => t.text === taskText);
    if (task) {
        task.done = !task.done;
        project.updatedAt = Date.now();
        saveProjectsToStorage();
        renderCurrentTab();
    }
}

// ============================================
// 导出功能
// ============================================
function exportMarkdown() {
    const project = state.projects.find(p => p.id === state.currentProjectId);
    if (!project) return;

    const markdown = generateMarkdown(project.data);
    const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${project.data.projectName}-架构蓝图.md`;
    a.click();
    URL.revokeObjectURL(url);

    showToast('已导出 Markdown 文件');
}

function generateMarkdown(data) {
    const { techStack, dataModels, milestones } = data;

    let md = `# ${data.projectName}\n\n`;
    md += `${data.projectDesc}\n\n`;
    md += `> 生成时间: ${new Date().toLocaleString()}\n\n`;
    md += `---\n\n`;

    md += `## 🛠️ 技术栈选型\n\n`;

    for (const [, stack] of Object.entries(techStack)) {
        md += `### ${stack.icon} ${stack.name}\n\n`;
        stack.items.forEach(item => {
            md += `- **${item.name}**: ${item.desc} (熟练度: ${item.level}%)\n`;
        });
        md += '\n';
    }

    md += `## 🗃️ 数据模型设计\n\n`;
    dataModels.forEach(model => {
        md += `### ${model.icon} ${model.name} (${model.alias})\n\n`;
        md += '| 字段名 | 类型 | 键 | 说明 |\n';
        md += '|--------|------|----|------|\n';
        model.fields.forEach(field => {
            md += `| ${field.name} | ${field.type} | ${field.key || '-'} | ${field.desc} |\n`;
        });
        md += '\n';
    });

    md += `## 📅 开发里程碑\n\n`;
    const totalTasks = countAllTasks(milestones);
    const doneTasks = countDoneTasks(milestones);
    md += `**总进度**: ${doneTasks}/${totalTasks} 任务完成\n\n`;

    milestones.forEach(milestone => {
        md += `### ${milestone.week}: ${milestone.theme}\n\n`;
        milestone.tasks.forEach(task => {
            md += `- [${task.done ? 'x' : ' '}] ${task.text}\n`;
        });
        md += '\n';
    });

    md += `---\n\n`;
    md += `*由 创世·架构蓝图引擎 生成*\n`;

    return md;
}

// ============================================
// 日历同步
// ============================================
function syncToCalendar() {
    const project = state.projects.find(p => p.id === state.currentProjectId);
    if (!project) return;

    // 保存到本地日历存储
    const calendarEvents = JSON.parse(localStorage.getItem('blueprint_calendar_events') || '{}');
    calendarEvents[project.id] = {
        projectName: project.data.projectName,
        milestones: project.data.milestones.map(m => ({
            week: m.week,
            theme: m.theme,
            tasks: m.tasks.map(t => ({
                text: t.text,
                done: t.done
            }))
        })),
        createdAt: Date.now()
    };
    localStorage.setItem('blueprint_calendar_events', JSON.stringify(calendarEvents));

    showToast('已同步到学习日历');
}

// ============================================
// 工具函数
// ============================================
function showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'toast-notification';
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', init);
