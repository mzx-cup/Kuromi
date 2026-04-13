const API_URL = `${window.location.origin}/api`;

let currentStep = 1;
const totalSteps = 9;
const assessmentData = {
    learningDirection: null,  // 学习方向
    languages: [],            // 编程语言（多选）
    knowledgeBase: null,      // 知识基础
    codeSkill: null,          // 编程能力
    learningGoal: null,       // 学习目标
    cognitiveStyle: null,     // 认知风格
    studyTime: null,          // 学习时间
    learningPace: null,       // 学习节奏
    focusLevel: null          // 专注度
};

const dimensionLabels = {
    learningDirection: {
        label: '学习方向',
        options: {
            bigdata: '大数据技术',
            ai: '人工智能',
            frontend: '前端开发',
            backend: '后端开发',
            algorithm: '算法与数据结构',
            database: '数据库技术'
        }
    },
    languages: {
        label: '编程语言',
        options: {
            python: 'Python',
            java: 'Java',
            c: 'C语言',
            cpp: 'C++',
            javascript: 'JavaScript',
            go: 'Go',
            sql: 'SQL',
            scala: 'Scala',
            rust: 'Rust'
        }
    },
    knowledgeBase: {
        label: '知识基础',
        options: {
            zero: '零基础入门',
            basic: '有一定了解',
            intermediate: '有实践经验',
            advanced: '深入掌握'
        }
    },
    codeSkill: {
        label: '编程能力',
        options: {
            beginner: '编程新手',
            basic: '基础掌握',
            intermediate: '熟练编程',
            advanced: '编程高手'
        }
    },
    learningGoal: {
        label: '学习目标',
        options: {
            exam: '应对考试',
            career: '职业发展',
            project: '项目实战',
            interest: '兴趣探索',
            competition: '竞赛备战',
            research: '科研学术'
        }
    },
    cognitiveStyle: {
        label: '认知风格',
        options: {
            visual: '视觉型',
            textual: '文字型',
            pragmatic: '实践型'
        }
    },
    studyTime: {
        label: '学习时间',
        options: {
            light: '轻松模式',
            moderate: '均衡模式',
            intensive: '强化模式',
            immersive: '沉浸模式'
        }
    },
    learningPace: {
        label: '学习节奏',
        options: {
            slow: '稳扎稳打',
            normal: '适中节奏',
            fast: '快速迭代'
        }
    },
    focusLevel: {
        label: '专注度',
        options: {
            high: '高专注',
            medium: '中等专注',
            low: '需要引导'
        }
    }
};

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    lucide.createIcons();
    setupOptionListeners();
    updateStepUI();
});

function setupOptionListeners() {
    // Single select options
    document.querySelectorAll('.option-btn[data-dimension]:not(.multi-select-card)').forEach(btn => {
        btn.addEventListener('click', function() {
            const dimension = this.dataset.dimension;
            const value = this.dataset.value;

            // Remove selected from siblings
            document.querySelectorAll(`.option-btn[data-dimension="${dimension}"]`).forEach(b => {
                b.classList.remove('selected');
            });

            // Add selected to clicked
            this.classList.add('selected');

            // Store value
            assessmentData[dimension] = value;

            // Enable next button
            document.getElementById('next-btn').disabled = false;
        });
    });

    // Multi-select options (for languages)
    document.querySelectorAll('.multi-select-card').forEach(btn => {
        btn.addEventListener('click', function() {
            const dimension = this.dataset.dimension;
            const value = this.dataset.value;

            // Toggle selection
            this.classList.toggle('selected');

            // Update array
            if (!assessmentData[dimension]) {
                assessmentData[dimension] = [];
            }

            const index = assessmentData[dimension].indexOf(value);
            if (index > -1) {
                assessmentData[dimension].splice(index, 1);
            } else {
                assessmentData[dimension].push(value);
            }

            // Enable next button if at least one selected
            document.getElementById('next-btn').disabled = assessmentData[dimension].length === 0;
        });
    });
}

function updateStepUI() {
    // Update progress bar
    const progress = (currentStep / totalSteps) * 100;
    document.getElementById('progress-bar').style.width = `${progress}%`;

    // Update step indicators
    for (let i = 1; i <= totalSteps; i++) {
        const stepEl = document.getElementById(`step-${i}`);
        if (stepEl) {
            stepEl.classList.remove('active', 'completed');

            if (i < currentStep) {
                stepEl.classList.add('completed');
                stepEl.innerHTML = '<svg class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"></polyline></svg>';
            } else if (i === currentStep) {
                stepEl.classList.add('active');
                stepEl.textContent = i;
            } else {
                stepEl.textContent = i;
            }
        }
    }

    // Update progress lines
    for (let i = 1; i < totalSteps; i++) {
        const lineEl = document.getElementById(`line-${i}`);
        if (lineEl) {
            if (i < currentStep) {
                lineEl.style.background = '#10b981';
            } else {
                lineEl.style.background = 'rgba(255,255,255,0.2)';
            }
        }
    }

    // Show/hide step content
    for (let i = 1; i <= totalSteps; i++) {
        const content = document.getElementById(`step-content-${i}`);
        if (content) {
            content.classList.toggle('hidden', i !== currentStep);
        }
    }

    // Update navigation buttons
    const prevBtn = document.getElementById('prev-btn');
    const nextBtn = document.getElementById('next-btn');

    prevBtn.style.visibility = currentStep > 1 ? 'visible' : 'hidden';

    // Check if current step has selection
    const dimensions = ['learningDirection', 'languages', 'knowledgeBase', 'codeSkill', 'learningGoal', 'cognitiveStyle', 'studyTime', 'learningPace', 'focusLevel'];
    const currentDimension = dimensions[currentStep - 1];

    // For languages (multi-select), check array length
    if (currentDimension === 'languages') {
        nextBtn.disabled = !assessmentData[currentDimension] || assessmentData[currentDimension].length === 0;
    } else {
        nextBtn.disabled = !assessmentData[currentDimension];
    }

    lucide.createIcons();
}

function nextStep() {
    if (currentStep < totalSteps) {
        currentStep++;
        updateStepUI();
    } else {
        // All steps completed, generate plan
        generateLearningPlan();
    }
}

function prevStep() {
    if (currentStep > 1) {
        currentStep--;
        updateStepUI();
    }
}

async function generateLearningPlan() {
    // Show loading
    document.querySelectorAll('.assessment-step').forEach(el => el.classList.add('hidden'));
    document.getElementById('step-loading').classList.remove('hidden');
    document.getElementById('nav-buttons').classList.add('hidden');

    try {
        // Call API to generate learning plan
        const res = await fetch(`${API_URL}/assessment/submit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                assessment: assessmentData
            })
        });

        const data = await res.json();

        if (!res.ok) {
            throw new Error(data.detail || '生成学习计划失败');
        }

        // Display result
        displayResult(data);

    } catch (error) {
        console.error('Error:', error);
        // Fallback: generate local plan
        const localPlan = generateLocalPlan();
        displayResult(localPlan);
    }
}

function generateLocalPlan() {
    const { learningDirection, languages, knowledgeBase, codeSkill, learningGoal, cognitiveStyle, studyTime, learningPace, focusLevel } = assessmentData;

    // Generate learning path based on direction and knowledge base
    let path = [];
    let suggestion = '';

    // Direction-specific paths
    const directionPaths = {
        bigdata: {
            zero: [
                { topic: '计算机基础与Linux入门', status: 'current', desc: '操作系统基础、Linux命令行' },
                { topic: 'Python编程基础', status: 'locked', desc: 'Python语法、数据处理' },
                { topic: '大数据概论与环境搭建', status: 'locked', desc: 'Hadoop生态介绍、环境配置' },
                { topic: 'Hadoop HDFS分布式存储', status: 'locked', desc: 'HDFS原理、读写流程' },
                { topic: 'MapReduce分布式计算', status: 'locked', desc: 'MapReduce编程模型' },
                { topic: 'Spark内存计算框架', status: 'locked', desc: 'Spark Core、SQL、Streaming' }
            ],
            basic: [
                { topic: '编程基础巩固', status: 'completed', desc: '已掌握基础编程' },
                { topic: 'Hadoop HDFS深入', status: 'current', desc: 'HDFS架构、副本机制、读写优化' },
                { topic: 'MapReduce编程实战', status: 'locked', desc: 'MapReduce开发、调优' },
                { topic: 'Hive数据仓库', status: 'locked', desc: 'Hive SQL、分区、优化' },
                { topic: 'Spark核心编程', status: 'locked', desc: 'RDD、DataFrame、Dataset' },
                { topic: 'Flink流处理引擎', status: 'locked', desc: '流式计算、窗口、CEP' }
            ],
            intermediate: [
                { topic: 'Hadoop生态体系', status: 'completed', desc: '已掌握基础组件' },
                { topic: 'Spark高级编程与调优', status: 'current', desc: 'Spark调优、SQL优化' },
                { topic: 'Flink流处理引擎', status: 'locked', desc: '实时计算、状态管理' },
                { topic: 'NoSQL数据库', status: 'locked', desc: 'HBase、Redis、MongoDB' },
                { topic: '数据仓库建设', status: 'locked', desc: '数仓建模、ETL流程' },
                { topic: '大数据项目实战', status: 'locked', desc: '综合项目演练' }
            ],
            advanced: [
                { topic: '大数据核心技术栈', status: 'completed', desc: '已深入掌握' },
                { topic: '架构设计与优化', status: 'current', desc: '企业级架构设计' },
                { topic: '大数据平台运维', status: 'locked', desc: '集群监控、性能调优' },
                { topic: '实时数仓建设', status: 'locked', desc: 'Lambda/Kappa架构' },
                { topic: '机器学习平台', status: 'locked', desc: 'ML Pipeline构建' },
                { topic: '技术前沿探索', status: 'locked', desc: 'DataOps、Data Mesh' }
            ]
        },
        ai: {
            zero: [
                { topic: 'Python编程基础', status: 'current', desc: 'Python语法、数据结构' },
                { topic: '数学基础', status: 'locked', desc: '线性代数、概率统计、微积分' },
                { topic: '机器学习导论', status: 'locked', desc: 'ML基本概念、经典算法' },
                { topic: '深度学习基础', status: 'locked', desc: '神经网络、反向传播' },
                { topic: 'TensorFlow/PyTorch', status: 'locked', desc: '深度学习框架实战' },
                { topic: '计算机视觉/NLP', status: 'locked', desc: 'CV或NLP方向深入' }
            ],
            basic: [
                { topic: 'Python编程', status: 'completed', desc: '已掌握Python基础' },
                { topic: '机器学习算法', status: 'current', desc: '监督学习、无监督学习' },
                { topic: '深度学习原理', status: 'locked', desc: 'CNN、RNN、Transformer' },
                { topic: '框架实战', status: 'locked', desc: 'PyTorch/TensorFlow项目' },
                { topic: '领域深入', status: 'locked', desc: 'CV/NLP/推荐系统' },
                { topic: '模型部署与优化', status: 'locked', desc: '模型压缩、推理加速' }
            ],
            intermediate: [
                { topic: 'ML/DL基础', status: 'completed', desc: '已掌握核心算法' },
                { topic: '领域专项突破', status: 'current', desc: 'CV/NLP/推荐深入' },
                { topic: '大模型技术', status: 'locked', desc: 'LLM、Prompt Engineering' },
                { topic: 'MLOps实践', status: 'locked', desc: '模型生命周期管理' },
                { topic: '研究论文复现', status: 'locked', desc: '前沿论文阅读与实现' },
                { topic: 'AI项目实战', status: 'locked', desc: '端到端AI项目' }
            ],
            advanced: [
                { topic: 'AI核心技术', status: 'completed', desc: '已深入掌握' },
                { topic: '前沿技术探索', status: 'current', desc: '最新研究进展' },
                { topic: '系统架构设计', status: 'locked', desc: 'AI系统架构' },
                { topic: '团队技术管理', status: 'locked', desc: 'AI团队建设' },
                { topic: '论文发表', status: 'locked', desc: '学术研究' },
                { topic: '技术影响力建设', status: 'locked', desc: '开源、分享' }
            ]
        },
        frontend: {
            zero: [
                { topic: 'HTML/CSS基础', status: 'current', desc: '网页结构、样式设计' },
                { topic: 'JavaScript入门', status: 'locked', desc: 'JS语法、DOM操作' },
                { topic: 'ES6+与TypeScript', status: 'locked', desc: '现代JS、类型系统' },
                { topic: 'React/Vue框架', status: 'locked', desc: '组件化开发' },
                { topic: '前端工程化', status: 'locked', desc: 'Webpack、Vite、CI/CD' },
                { topic: '项目实战', status: 'locked', desc: '完整前端项目' }
            ],
            basic: [
                { topic: 'HTML/CSS/JS基础', status: 'completed', desc: '已掌握前端基础' },
                { topic: 'React/Vue深入', status: 'current', desc: '框架原理、最佳实践' },
                { topic: '状态管理', status: 'locked', desc: 'Redux、Pinia、Zustand' },
                { topic: '前端工程化', status: 'locked', desc: '构建工具、自动化' },
                { topic: '性能优化', status: 'locked', desc: '加载优化、渲染优化' },
                { topic: '跨端开发', status: 'locked', desc: '小程序、RN、Flutter' }
            ],
            intermediate: [
                { topic: '前端框架', status: 'completed', desc: '已熟练使用框架' },
                { topic: '架构设计', status: 'current', desc: '前端架构、微前端' },
                { topic: '性能优化深入', status: 'locked', desc: '极致性能优化' },
                { topic: '跨端技术', status: 'locked', desc: '多端统一方案' },
                { topic: '前端智能化', status: 'locked', desc: '低代码、AI辅助' },
                { topic: '技术团队管理', status: 'locked', desc: '前端团队建设' }
            ],
            advanced: [
                { topic: '前端全栈能力', status: 'completed', desc: '已具备全栈能力' },
                { topic: '技术规划', status: 'current', desc: '技术选型、架构演进' },
                { topic: '基础设施建设', status: 'locked', desc: '研发平台、工具链' },
                { topic: '技术影响力', status: 'locked', desc: '开源、技术分享' },
                { topic: '业务架构', status: 'locked', desc: '业务与技术结合' },
                { topic: '团队成长', status: 'locked', desc: '人才培养' }
            ]
        },
        backend: {
            zero: [
                { topic: '编程语言基础', status: 'current', desc: 'Java/Go/Python选一' },
                { topic: '数据结构与算法', status: 'locked', desc: '基础算法、数据结构' },
                { topic: '数据库基础', status: 'locked', desc: 'MySQL、Redis入门' },
                { topic: 'Web框架', status: 'locked', desc: 'Spring Boot/Gin/Django' },
                { topic: '微服务架构', status: 'locked', desc: '服务拆分、RPC' },
                { topic: '分布式系统', status: 'locked', desc: '分布式理论、实践' }
            ],
            basic: [
                { topic: '编程语言', status: 'completed', desc: '已掌握一门语言' },
                { topic: '数据库深入', status: 'current', desc: 'SQL优化、索引原理' },
                { topic: 'Web框架实战', status: 'locked', desc: '框架原理、最佳实践' },
                { topic: '微服务入门', status: 'locked', desc: 'Spring Cloud/微服务' },
                { topic: '消息队列', status: 'locked', desc: 'Kafka、RabbitMQ' },
                { topic: '分布式系统', status: 'locked', desc: 'CAP、分布式事务' }
            ],
            intermediate: [
                { topic: '后端基础', status: 'completed', desc: '已掌握后端开发' },
                { topic: '系统设计', status: 'current', desc: '高并发、高可用设计' },
                { topic: '性能优化', status: 'locked', desc: 'JVM、数据库、缓存优化' },
                { topic: '分布式深入', status: 'locked', desc: '分布式事务、一致性' },
                { topic: '容器化与云原生', status: 'locked', desc: 'Docker、K8s' },
                { topic: '架构演进', status: 'locked', desc: '系统架构设计' }
            ],
            advanced: [
                { topic: '后端核心技术', status: 'completed', desc: '已深入掌握' },
                { topic: '架构设计', status: 'current', desc: '大型系统架构' },
                { topic: '技术规划', status: 'locked', desc: '技术选型、演进' },
                { topic: '团队管理', status: 'locked', desc: '技术团队建设' },
                { topic: '技术影响力', status: 'locked', desc: '开源、分享' },
                { topic: '业务架构', status: 'locked', desc: '业务与技术融合' }
            ]
        },
        algorithm: {
            zero: [
                { topic: '编程语言基础', status: 'current', desc: 'C++/Python/Java' },
                { topic: '基础数据结构', status: 'locked', desc: '数组、链表、栈、队列' },
                { topic: '基础算法', status: 'locked', desc: '排序、二分、递归' },
                { topic: '进阶数据结构', status: 'locked', desc: '树、图、哈希表' },
                { topic: '动态规划', status: 'locked', desc: 'DP思想、经典问题' },
                { topic: '竞赛算法', status: 'locked', desc: '图论、数论、字符串' }
            ],
            basic: [
                { topic: '基础算法', status: 'completed', desc: '已掌握基础' },
                { topic: '数据结构深入', status: 'current', desc: '高级数据结构' },
                { topic: '动态规划', status: 'locked', desc: 'DP专题训练' },
                { topic: '图论算法', status: 'locked', desc: 'BFS、DFS、最短路' },
                { topic: '刷题训练', status: 'locked', desc: 'LeetCode专项' },
                { topic: '竞赛模拟', status: 'locked', desc: '模拟赛、真题' }
            ],
            intermediate: [
                { topic: '基础算法', status: 'completed', desc: '已熟练掌握' },
                { topic: '竞赛专题', status: 'current', desc: '专项突破' },
                { topic: '高级算法', status: 'locked', desc: '高级数据结构、算法' },
                { topic: '真题训练', status: 'locked', desc: '历年真题' },
                { topic: '模拟赛', status: 'locked', desc: '定期模拟' },
                { topic: '竞赛实战', status: 'locked', desc: '参加比赛' }
            ],
            advanced: [
                { topic: '算法能力', status: 'completed', desc: '已具备竞赛水平' },
                { topic: '难题突破', status: 'current', desc: '挑战难题' },
                { topic: '算法创新', status: 'locked', desc: '算法优化、创新' },
                { topic: '竞赛指导', status: 'locked', desc: '帮助他人提升' },
                { topic: '算法研究', status: 'locked', desc: '算法理论研究' },
                { topic: '技术影响力', status: 'locked', desc: '分享、开源' }
            ]
        },
        database: {
            zero: [
                { topic: 'SQL基础', status: 'current', desc: 'SQL语法、基本查询' },
                { topic: '数据库设计', status: 'locked', desc: 'ER图、范式设计' },
                { topic: 'MySQL深入', status: 'locked', desc: '索引、事务、锁' },
                { topic: 'Redis缓存', status: 'locked', desc: '缓存设计、数据结构' },
                { topic: 'MongoDB文档库', status: 'locked', desc: '文档数据库' },
                { topic: '分布式数据库', status: 'locked', desc: '分库分表、分布式事务' }
            ],
            basic: [
                { topic: 'SQL基础', status: 'completed', desc: '已掌握SQL' },
                { topic: 'MySQL深入', status: 'current', desc: '存储引擎、索引优化' },
                { topic: 'Redis实战', status: 'locked', desc: '缓存架构、分布式锁' },
                { topic: 'PostgreSQL', status: 'locked', desc: '高级特性' },
                { topic: 'NoSQL生态', status: 'locked', desc: 'MongoDB、ES' },
                { topic: '数据库运维', status: 'locked', desc: '监控、备份、高可用' }
            ],
            intermediate: [
                { topic: '数据库基础', status: 'completed', desc: '已熟练使用' },
                { topic: '性能优化', status: 'current', desc: 'SQL优化、架构优化' },
                { topic: '高可用架构', status: 'locked', desc: '主从、集群' },
                { topic: '分布式数据库', status: 'locked', desc: 'TiDB、OceanBase' },
                { topic: '数据架构', status: 'locked', desc: '数据中台、数仓' },
                { topic: '数据库内核', status: 'locked', desc: '源码分析' }
            ],
            advanced: [
                { topic: '数据库技术', status: 'completed', desc: '已深入掌握' },
                { topic: '架构设计', status: 'current', desc: '数据架构规划' },
                { topic: '内核研究', status: 'locked', desc: '数据库内核开发' },
                { topic: '技术规划', status: 'locked', desc: '技术选型' },
                { topic: '团队建设', status: 'locked', desc: 'DBA团队管理' },
                { topic: '技术影响力', status: 'locked', desc: '分享、开源' }
            ]
        }
    };

    // Get path based on direction and knowledge level
    const direction = learningDirection || 'bigdata';
    const level = knowledgeBase || 'zero';
    path = directionPaths[direction]?.[level] || directionPaths.bigdata.zero;

    // Generate suggestion based on profile
    const languageStr = languages && languages.length > 0
        ? languages.map(l => dimensionLabels.languages.options[l]).join('、')
        : 'Python';

    const directionStr = dimensionLabels.learningDirection.options[direction];
    const levelStr = dimensionLabels.knowledgeBase.options[level];
    const goalStr = dimensionLabels.learningGoal.options[learningGoal] || '学习提升';
    const styleStr = dimensionLabels.cognitiveStyle.options[cognitiveStyle] || '实践型';

    suggestion = `你选择了${directionStr}方向，主要使用${languageStr}语言。当前${levelStr}，目标是${goalStr}。`;

    // Add style-specific suggestions
    if (cognitiveStyle === 'visual') {
        suggestion += '根据你的视觉型学习偏好，我们会提供丰富的图表、流程图和可视化演示来帮助你理解抽象概念。';
    } else if (cognitiveStyle === 'pragmatic') {
        suggestion += '根据你的实践型学习偏好，我们会提供大量代码示例和动手练习，让你在实践中掌握知识。';
    } else {
        suggestion += '根据你的文字型学习偏好，我们会提供详细的理论解释和文档资料，帮助你系统性地理解知识。';
    }

    // Add time-based suggestions
    if (studyTime === 'light') {
        suggestion += '考虑到你的学习时间有限，建议每天专注1-2个核心概念，循序渐进。';
    } else if (studyTime === 'immersive') {
        suggestion += '你的学习时间充裕，建议结合理论学习和项目实战，快速提升技能水平。';
    }

    // Add pace suggestions
    if (learningPace === 'slow') {
        suggestion += '建议你稳扎稳打，每个知识点都要彻底理解后再继续，打好坚实基础。';
    } else if (learningPace === 'fast') {
        suggestion += '建议快速过一遍核心内容，遇到问题再回头深入，效率优先。';
    }

    // Add focus suggestions
    if (focusLevel === 'low') {
        suggestion += '我们会通过互动问答、苏格拉底式引导等方式，帮助你保持学习专注度。';
    }

    return {
        profile: assessmentData,
        path: path,
        suggestion: suggestion
    };
}

function displayResult(data) {
    // Hide loading, show result
    document.getElementById('step-loading').classList.add('hidden');
    document.getElementById('step-result').classList.remove('hidden');

    // Display profile summary
    const profileSummary = document.getElementById('profile-summary');
    profileSummary.innerHTML = '';

    for (const [key, value] of Object.entries(assessmentData)) {
        if (value && dimensionLabels[key]) {
            const div = document.createElement('div');
            div.className = 'bg-white rounded-lg p-2.5 shadow-sm slide-in';

            let displayValue;
            if (Array.isArray(value)) {
                displayValue = value.map(v => dimensionLabels[key].options[v]).join('、');
            } else {
                displayValue = dimensionLabels[key].options[value];
            }

            div.innerHTML = `
                <div class="text-xs text-gray-500 mb-0.5">${dimensionLabels[key].label}</div>
                <div class="font-semibold text-gray-800 text-sm">${displayValue}</div>
            `;
            profileSummary.appendChild(div);
        }
    }

    // Display learning path
    const pathContainer = document.getElementById('learning-path');
    pathContainer.innerHTML = '';

    data.path.forEach((item, index) => {
        const div = document.createElement('div');
        div.className = 'flex items-center gap-3 slide-in';
        div.style.animationDelay = `${index * 0.1}s`;

        let statusIcon, statusColor, statusBg;
        if (item.status === 'completed') {
            statusIcon = 'check-circle';
            statusColor = 'text-green-600';
            statusBg = 'bg-green-100';
        } else if (item.status === 'current') {
            statusIcon = 'play-circle';
            statusColor = 'text-blue-600';
            statusBg = 'bg-blue-100';
        } else {
            statusIcon = 'lock';
            statusColor = 'text-gray-400';
            statusBg = 'bg-gray-100';
        }

        div.innerHTML = `
            <div class="w-9 h-9 ${statusBg} rounded-full flex items-center justify-center shrink-0">
                <i data-lucide="${statusIcon}" class="w-4 h-4 ${statusColor}"></i>
            </div>
            <div class="flex-1">
                <div class="font-semibold text-gray-800 text-sm">${item.topic}</div>
                <div class="text-xs text-gray-500">${item.desc}</div>
            </div>
        `;
        pathContainer.appendChild(div);
    });

    // Display AI suggestion
    document.getElementById('ai-suggestion').textContent = data.suggestion;

    // Save assessment data to localStorage
    const user = JSON.parse(localStorage.getItem('starlearn_user') || '{}');
    user.assessment = assessmentData;
    user.learningPath = data.path;
    user.hasCompletedAssessment = true;
    localStorage.setItem('starlearn_user', JSON.stringify(user));

    lucide.createIcons();
}

function startLearning() {
    // Save to backend if user is logged in
    const user = JSON.parse(localStorage.getItem('starlearn_user') || '{}');

    // 与 index.js 中 initProfileFromAssessment 一致：保存「展示用画像」，避免后端/主界面出现 basic、exam 等裸枚举
    const profileMap = {
        knowledgeBase: { zero: '零基础入门', basic: '基础入门', intermediate: '进阶学习', advanced: '深入掌握' },
        codeSkill: { beginner: '编程新手', basic: '基础掌握', intermediate: '熟练编程', advanced: '编程高手' },
        learningGoal: { exam: '应对考试', career: '职业发展', project: '项目实战', interest: '兴趣探索', competition: '竞赛备战', research: '科研学术' },
        cognitiveStyle: { visual: '视觉型', textual: '文字型', pragmatic: '实践型' },
        focusLevel: { high: '高专注', medium: '中等专注', low: '需要引导' }
    };
    const directionMap = {
        bigdata: '大数据技术',
        ai: '人工智能',
        frontend: '前端开发',
        backend: '后端开发',
        algorithm: '算法数据结构',
        database: '数据库技术'
    };

    const profile = {
        knowledgeBase: profileMap.knowledgeBase[assessmentData.knowledgeBase] || '基础入门',
        codeSkill: profileMap.codeSkill[assessmentData.codeSkill] || '基础掌握',
        learningGoal: profileMap.learningGoal[assessmentData.learningGoal] || '学习提升',
        cognitiveStyle: profileMap.cognitiveStyle[assessmentData.cognitiveStyle] || '实践型',
        weakness: '暂无',
        focusLevel: profileMap.focusLevel[assessmentData.focusLevel] || '中等专注',
        learningDirection: directionMap[assessmentData.learningDirection] || '大数据技术',
        languages: assessmentData.languages || ['python']
    };

    user.profile = profile;
    user.learningPath = user.learningPath || [];
    user.hasCompletedAssessment = true;
    localStorage.setItem('starlearn_user', JSON.stringify(user));

    if (user.id) {
        // Save progress to backend
        fetch(`${API_URL}/progress/save`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                userId: user.id,
                profile: profile,
                evaluation: {},
                currentPath: user.learningPath || []
            })
        }).catch(err => console.log('Save progress error:', err));
    }

    // Navigate to main page
    window.location.href = '/index.html';
}

// Check if user has already completed assessment
window.addEventListener('load', function() {
    const user = JSON.parse(localStorage.getItem('starlearn_user') || '{}');
    if (user.hasCompletedAssessment) {
        // User already completed assessment, go to main page
        window.location.href = '/index.html';
    }
});
