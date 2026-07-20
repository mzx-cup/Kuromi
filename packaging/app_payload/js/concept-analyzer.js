// ============================================
// 灵犀·动态概念拆解仪 - JavaScript
// ============================================

// ============================================
// 概念数据库
// ============================================
const conceptDatabase = {
    networking: {
        name: "计算机网络",
        icon: "🌐",
        concepts: [
            {
                id: "tcp-handshake",
                name: "TCP 三次握手",
                description: "理解 TCP 连接的建立过程",
                steps: [
                    {
                        title: "第一次握手：SYN",
                        description: "客户端发送一个 <span class='keyword'>SYN</span>（同步）包给服务器，请求建立连接。此时客户端进入 <span class='keyword blue'>SYN_SENT</span> 状态，等待服务器确认。",
                        visualState: { highlight: "client", activeNodes: ["client"], packet: null }
                    },
                    {
                        title: "第二次握手：SYN+ACK",
                        description: "服务器收到 SYN 包后，返回一个 <span class='keyword blue'>SYN+ACK</span>（同步确认）包，表示同意建立连接。服务器进入 <span class='keyword'>SYN_RCVD</span> 状态。",
                        visualState: { highlight: "server", activeNodes: ["client", "server"], packet: "synack" }
                    },
                    {
                        title: "第三次握手：ACK",
                        description: "客户端发送 <span class='keyword green'>ACK</span>（确认）包，握手完成。双方进入 <span class='keyword green'>ESTABLISHED</span> 状态，可以开始传输数据。",
                        visualState: { highlight: "established", activeNodes: ["client", "server", "established"], packet: "ack" }
                    }
                ]
            },
            {
                id: "tcp-four-wave",
                name: "TCP 四次挥手",
                description: "理解 TCP 连接的关闭过程",
                steps: [
                    {
                        title: "第一次挥手：FIN",
                        description: "客户端发送 <span class='keyword'>FIN</span>（结束）包，请求关闭连接。客户端进入 <span class='keyword blue'>FIN_WAIT_1</span> 状态。",
                        visualState: { highlight: "client", activeNodes: ["client", "server"], packet: null }
                    },
                    {
                        title: "第二次挥手：ACK",
                        description: "服务器收到 FIN 后，发送 <span class='keyword green'>ACK</span> 确认包。服务器进入 <span class='keyword'>CLOSE_WAIT</span> 状态，客户端收到后进入 <span class='keyword blue'>FIN_WAIT_2</span> 状态。",
                        visualState: { highlight: "server", activeNodes: ["client", "server"], packet: "ack" }
                    },
                    {
                        title: "第三次挥手：FIN",
                        description: "服务器处理完数据后，发送 <span class='keyword'>FIN</span> 包给客户端，请求关闭连接。服务器进入 <span class='keyword'>LAST_ACK</span> 状态。",
                        visualState: { highlight: "server", activeNodes: ["client", "server"], packet: "fin" }
                    },
                    {
                        title: "第四次挥手：ACK",
                        description: "客户端收到 FIN 后，发送 <span class='keyword green'>ACK</span> 确认包。客户端进入 <span class='keyword blue'>TIME_WAIT</span> 状态，等待 2MSL 后关闭。服务器收到后立即关闭连接。",
                        visualState: { highlight: "established", activeNodes: ["client", "server"], packet: "ack" }
                    }
                ]
            },
            {
                id: "dns-resolution",
                name: "DNS 解析流程",
                description: "域名到 IP 地址的转换过程",
                steps: [
                    {
                        title: "浏览器缓存检查",
                        description: "首先检查浏览器 DNS 缓存。如果没有，浏览器调用 <span class='keyword'>gethostname</span> 库检查本地 hosts 文件和缓存 DNS 服务器。",
                        visualState: { highlight: "client", activeNodes: ["client"], packet: null }
                    },
                    {
                        title: "递归查询请求",
                        description: "如果本地缓存都没有，客户端向配置的 <span class='keyword blue'>递归 DNS 服务器</span>（通常是 ISP 提供）发送查询请求。",
                        visualState: { highlight: "dns-server", activeNodes: ["client", "dns-server"], packet: "query" }
                    },
                    {
                        title: "根域名服务器查询",
                        description: "DNS 服务器首先查询 <span class='keyword'>根域名服务器</span>（全球 13 组），获取顶级域（.com, .cn 等）的权威服务器地址。",
                        visualState: { highlight: "root-server", activeNodes: ["client", "dns-server", "root-server"], packet: "root" }
                    },
                    {
                        title: "TLD 服务器查询",
                        description: "DNS 服务器向 <span class='keyword blue'>TLD 服务器</span>（如 .com）查询，得到目标域名的权威 DNS 服务器地址。",
                        visualState: { highlight: "tld-server", activeNodes: ["dns-server", "tld-server"], packet: "tld" }
                    },
                    {
                        title: "权威服务器查询",
                        description: "DNS 服务器向 <span class='keyword'>权威 DNS 服务器</span>查询，获取域名对应的具体 IP 地址。",
                        visualState: { highlight: "auth-server", activeNodes: ["dns-server", "auth-server"], packet: "auth" }
                    },
                    {
                        title: "返回结果",
                        description: "递归 DNS 服务器将查询结果返回给客户端，并<span class='keyword green'>缓存</span>一段时间（由 TTL 决定）。",
                        visualState: { highlight: "client", activeNodes: ["client", "dns-server"], packet: "result" }
                    }
                ]
            },
            {
                id: "http-request",
                name: "HTTP 请求流程",
                description: "从 URL 到完整请求的过程",
                steps: [
                    {
                        title: "URL 解析",
                        description: "浏览器解析 URL：<span class='keyword'>协议</span>（http/https）、<span class='keyword blue'>域名</span>、<span class='keyword'>端口</span>（默认 80/443）、<span class='keyword green'>路径</span>。",
                        visualState: { highlight: "client", activeNodes: ["client"], packet: null }
                    },
                    {
                        title: "DNS 解析",
                        description: "如果域名不在缓存中，需要进行 <span class='keyword'>DNS 解析</span>，获取服务器的 IP 地址。",
                        visualState: { highlight: "dns-server", activeNodes: ["client", "dns-server"], packet: "dns" }
                    },
                    {
                        title: "建立 TCP 连接",
                        description: "根据是否使用 HTTPS，先进行 <span class='keyword blue'>TCP 三次握手</span>（或 TLS 握手）。",
                        visualState: { highlight: "server", activeNodes: ["client", "server"], packet: "syn" }
                    },
                    {
                        title: "发送 HTTP 请求",
                        description: "客户端构建 <span class='keyword'>请求行</span>（GET/POST + 路径 + 版本），添加<span class='keyword blue'>请求头</span>（Host, User-Agent, Cookie 等）。",
                        visualState: { highlight: "client", activeNodes: ["client", "server"], packet: "request" }
                    },
                    {
                        title: "服务器处理",
                        description: "服务器接收请求，路由到对应的<span class='keyword'>处理器</span>，执行业务逻辑，可能查询数据库。",
                        visualState: { highlight: "server", activeNodes: ["server"], packet: null }
                    },
                    {
                        title: "返回响应",
                        description: "服务器返回<span class='keyword green'>状态码</span>（200/404/500）、<span class='keyword'>响应头</span>和<span class='keyword blue'>响应体</span>（HTML/JSON 等）。",
                        visualState: { highlight: "client", activeNodes: ["client", "server"], packet: "response" }
                    }
                ]
            }
        ]
    },
    algorithms: {
        name: "算法与数据结构",
        icon: "🧮",
        concepts: [
            {
                id: "binary-search",
                name: "二分查找",
                description: "有序数组的高效搜索算法",
                steps: [
                    {
                        title: "初始化",
                        description: "设定 <span class='keyword'>left</span> 和 <span class='keyword blue'>right</span> 指针，分别指向数组的起始和结束位置。",
                        visualState: { highlight: "client", activeNodes: ["client"], packet: null }
                    },
                    {
                        title: "计算中点",
                        description: "计算中间位置：<span class='keyword'>mid = (left + right) / 2</span>。比较 arr[mid] 与目标值的大小。",
                        visualState: { highlight: "server", activeNodes: ["client", "server"], packet: "compare" }
                    },
                    {
                        title: "缩小范围",
                        description: "如果 <span class='keyword green'>arr[mid] == target</span>，查找成功。如果 <span class='keyword'>arr[mid] < target</span>，左半部分可以排除。",
                        visualState: { highlight: "client", activeNodes: ["client", "server"], packet: "narrow" }
                    },
                    {
                        title: "继续查找",
                        description: "根据比较结果调整 <span class='keyword blue'>left</span> 或 <span class='keyword'>right</span> 指针，重复上述过程直到找到目标或范围为空。",
                        visualState: { highlight: "server", activeNodes: ["server"], packet: "search" }
                    }
                ]
            },
            {
                id: "quick-sort",
                name: "快速排序",
                description: "分治策略的经典排序算法",
                steps: [
                    {
                        title: "选择基准",
                        description: "从数组中选择一个<span class='keyword'>基准元素</span>（pivot），常用策略是选择首个元素、中间元素或随机元素。",
                        visualState: { highlight: "client", activeNodes: ["client"], packet: null }
                    },
                    {
                        title: "分区操作",
                        description: "遍历数组，将元素分为两部分：<span class='keyword blue'>小于 pivot</span> 的放左边，<span class='keyword'>大于 pivot</span> 的放右边。",
                        visualState: { highlight: "server", activeNodes: ["client", "server"], packet: "partition" }
                    },
                    {
                        title: "递归排序",
                        description: "对<span class='keyword'>左半部分</span>和<span class='keyword green'>右半部分</span>分别递归执行快速排序。",
                        visualState: { highlight: "client", activeNodes: ["client", "server"], packet: "recurse" }
                    },
                    {
                        title: "合并结果",
                        description: "当子数组大小为 0 或 1 时，递归结束。合并所有子数组，得到完整<span class='keyword'>有序数组</span>。",
                        visualState: { highlight: "established", activeNodes: ["client", "server", "established"], packet: "merge" }
                    }
                ]
            },
            {
                id: "hash-collision",
                name: "哈希冲突解决",
                description: "哈希表中冲突的处理方法",
                steps: [
                    {
                        title: "冲突发生",
                        description: "当两个不同的键<span class='keyword'>hash(key1) == hash(key2)</span>时，发生哈希冲突。这是不可避免的，但有好的解决方法。",
                        visualState: { highlight: "client", activeNodes: ["client"], packet: null }
                    },
                    {
                        title: "链地址法",
                        description: "每个桶（bucket）存储一个<span class='keyword blue'>链表</span>或<span class='keyword'>红黑树</span>，冲突的元素直接追加到链表尾部。",
                        visualState: { highlight: "server", activeNodes: ["client", "server"], packet: "chain" }
                    },
                    {
                        title: "开放寻址",
                        description: "当发生冲突时，探测<span class='keyword'>下一个空桶</span>：线性探测（+1）、二次探测（+i²）或<span class='keyword green'>双重哈希</span>。",
                        visualState: { highlight: "client", activeNodes: ["client", "server"], packet: "probe" }
                    },
                    {
                        title: "再哈希法",
                        description: "使用<span class='keyword'>第二个哈希函数</span>计算探测序列，直到找到空桶。优点是探测更均匀。",
                        visualState: { highlight: "established", activeNodes: ["client", "server", "established"], packet: "rehash" }
                    }
                ]
            }
        ]
    },
    databases: {
        name: "数据库原理",
        icon: "🗄️",
        concepts: [
            {
                id: "transaction-acid",
                name: "事务 ACID 特性",
                description: "数据库事务的核心保证",
                steps: [
                    {
                        title: "原子性（Atomicity）",
                        description: "事务是最小执行单位，<span class='keyword'>要么全部成功</span>，要么<span class='keyword blue'>全部失败回滚</span>。不会停留在中间状态。",
                        visualState: { highlight: "client", activeNodes: ["client"], packet: null }
                    },
                    {
                        title: "一致性（Consistency）",
                        description: "事务执行前后，数据库始终保持<span class='keyword green'>正确的状态</span>。所有约束、触发器、级联操作都被正确执行。",
                        visualState: { highlight: "server", activeNodes: ["client", "server"], packet: "check" }
                    },
                    {
                        title: "隔离性（Isolation）",
                        description: "并发执行的事务相互<span class='keyword'>隔离</span>，一个事务的中间状态对其他事务不可见。",
                        visualState: { highlight: "client", activeNodes: ["client", "server"], packet: "isolate" }
                    },
                    {
                        title: "持久性（Durability）",
                        description: "事务提交后，其结果<span class='keyword blue'>永久保存</span>在数据库中，即使系统崩溃也不会丢失。",
                        visualState: { highlight: "established", activeNodes: ["client", "server", "established"], packet: "commit" }
                    }
                ]
            },
            {
                id: "index-btree",
                name: "B+ 树索引",
                description: "数据库索引的核心数据结构",
                steps: [
                    {
                        title: "B+ 树结构",
                        description: "B+ 树是一种<span class='keyword'>多叉平衡树</span>，所有数据都存储在叶子节点，叶子节点之间<span class='keyword blue'>用链表连接</span>。",
                        visualState: { highlight: "client", activeNodes: ["client"], packet: null }
                    },
                    {
                        title: "根节点分裂",
                        description: "当根节点<span class='keyword'>满了</span>（超过最大子节点数），中间关键字上浮，节点<span class='keyword green'>分裂</span>为两个节点。",
                        visualState: { highlight: "server", activeNodes: ["client", "server"], packet: "split" }
                    },
                    {
                        title: "非叶子节点分裂",
                        description: "非叶子节点分裂时，中间关键字<span class='keyword blue'>上浮</span>到父节点，左右数据<span class='keyword'>分别</span>成为左右子节点。",
                        visualState: { highlight: "client", activeNodes: ["client", "server"], packet: "divide" }
                    },
                    {
                        title: "范围查询优化",
                        description: "由于叶子节点链表连接，<span class='keyword'>范围查询</span>只需定位起点，然后<span class='keyword green'>顺序遍历</span>链表即可。",
                        visualState: { highlight: "established", activeNodes: ["client", "server", "established"], packet: "range" }
                    }
                ]
            }
        ]
    },
    os: {
        name: "操作系统",
        icon: "⚙️",
        concepts: [
            {
                id: "process-thread",
                name: "进程与线程",
                description: "理解进程和线程的区别",
                steps: [
                    {
                        title: "进程定义",
                        description: "进程是<span class='keyword'>资源分配</span>的基本单位，拥有独立的<span class='keyword blue'>地址空间</span>、文件描述符、堆内存等资源。",
                        visualState: { highlight: "client", activeNodes: ["client"], packet: null }
                    },
                    {
                        title: "线程定义",
                        description: "线程是<span class='keyword'>CPU 调度</span>的基本单位，同一进程内的线程<span class='keyword green'>共享</span>进程的地址空间和资源。",
                        visualState: { highlight: "server", activeNodes: ["client", "server"], packet: "share" }
                    },
                    {
                        title: "资源对比",
                        description: "进程切换需要<span class='keyword'>切换页表</span>和内核态资源；线程切换只保存<span class='keyword blue'>寄存器</span>和栈，开销小得多。",
                        visualState: { highlight: "client", activeNodes: ["client", "server"], packet: "context" }
                    },
                    {
                        title: "通信方式",
                        description: "进程间通信（IPC）：管道、消息队列、<span class='keyword'>共享内存</span>、socket 等。线程间直接通过<span class='keyword green'>共享变量</span>通信。",
                        visualState: { highlight: "established", activeNodes: ["client", "server", "established"], packet: "comm" }
                    }
                ]
            },
            {
                id: "virtual-memory",
                name: "虚拟内存",
                description: "操作系统内存管理核心概念",
                steps: [
                    {
                        title: "虚拟地址空间",
                        description: "每个进程看到的是<span class='keyword'>独立的虚拟地址空间</span>（32位系统 4GB），与物理内存大小无关。",
                        visualState: { highlight: "client", activeNodes: ["client"], packet: null }
                    },
                    {
                        title: "页表映射",
                        description: "虚拟地址通过<span class='keyword blue'>页表</span>映射到物理地址。页表条目（PTE）包含<span class='keyword'>物理页框号</span>和访问权限。",
                        visualState: { highlight: "server", activeNodes: ["client", "server"], packet: "map" }
                    },
                    {
                        title: "页面置换",
                        description: "当物理内存不足时，操作系统将不常用的<span class='keyword'>页面置换</span>到磁盘（swap），需要时再换回来。",
                        visualState: { highlight: "client", activeNodes: ["client", "server"], packet: "swap" }
                    },
                    {
                        title: "TLB 加速",
                        description: "<span class='keyword green'>TLB</span>（Translation Lookaside Buffer）是页表的硬件缓存，加速虚拟地址到物理地址的转换。",
                        visualState: { highlight: "established", activeNodes: ["client", "server", "established"], packet: "tlb" }
                    }
                ]
            }
        ]
    }
};

// 全局状态
let state = {
    currentCategory: 'networking',
    currentConcept: null,
    currentConceptData: null,
    currentStep: 0,
    isPlaying: false,
    playInterval: null,
    typewriterTimeout: null,
    isLoading: true,
    completedConcepts: new Set(JSON.parse(localStorage.getItem('completedConcepts') || '[]')),
    quizAnswers: {},
    isQuizMode: false
};

// DOM 缓存
let domCache = {};

// ============================================
// 初始化
// ============================================
function initDOMCache() {
    domCache = {
        modal: document.getElementById('concept-analyzer-modal'),
        sandboxSkeleton: document.getElementById('sandbox-skeleton'),
        sandboxStage: document.getElementById('sandbox-stage'),
        stepTitle: document.getElementById('step-title'),
        typewriterText: document.getElementById('typewriter-text'),
        scrubberFill: document.getElementById('scrubber-fill'),
        scrubberThumb: document.getElementById('scrubber-thumb'),
        currentStep: document.getElementById('current-step'),
        stepCounter: document.getElementById('step-counter'),
        stepIndicators: document.getElementById('step-indicators'),
        activeNodes: document.getElementById('active-nodes'),
        playIcon: document.getElementById('play-icon'),
        pauseIcon: document.getElementById('pause-icon'),
        btnPlay: document.getElementById('btn-play'),
        btnPrev: document.getElementById('btn-prev'),
        btnNext: document.getElementById('btn-next'),
        regenerateIcon: document.getElementById('regenerate-icon'),
        conceptSubtitle: document.getElementById('concept-subtitle'),
        conceptSelector: document.getElementById('concept-selector'),
        categoryTabs: document.getElementById('category-tabs'),
        quizSection: document.getElementById('quiz-section'),
        conceptProgress: document.getElementById('concept-progress')
    };
}

function init() {
    initDOMCache();
    renderCategoryTabs();
    renderConceptSelector();
    initKeyboardControls();
}

function initEventListeners() {
    if (domCache.conceptSelector) {
        domCache.conceptSelector.addEventListener('change', (e) => {
            loadConcept(e.target.value);
        });
    }
}

// ============================================
// 分类和概念选择
// ============================================
function renderCategoryTabs() {
    const container = domCache.categoryTabs;
    if (!container) return;

    container.innerHTML = '';

    Object.entries(conceptDatabase).forEach(([key, category], index) => {
        const btn = document.createElement('button');
        btn.className = `category-tab px-4 py-2 rounded-lg text-sm font-medium transition-all ${index === 0 ? 'active' : ''}`;
        btn.innerHTML = `<span>${category.icon}</span><span>${category.name}</span>`;
        btn.onclick = () => selectCategory(key);
        container.appendChild(btn);
    });
}

function selectCategory(categoryKey) {
    state.currentCategory = categoryKey;

    // 更新标签样式
    document.querySelectorAll('.category-tab').forEach((tab, index) => {
        const key = Object.keys(conceptDatabase)[index];
        tab.classList.toggle('active', key === categoryKey);
    });

    renderConceptSelector();
}

function renderConceptSelector() {
    const container = domCache.conceptSelector;
    if (!container) return;

    const category = conceptDatabase[state.currentCategory];
    container.innerHTML = '';

    category.concepts.forEach(concept => {
        const option = document.createElement('option');
        option.value = concept.id;
        option.textContent = concept.name;
        if (state.completedConcepts.has(concept.id)) {
            option.textContent += ' ✓';
        }
        container.appendChild(option);
    });

    // 加载第一个概念
    if (category.concepts.length > 0) {
        loadConcept(category.concepts[0].id);
    }
}

function loadConcept(conceptId) {
    const category = conceptDatabase[state.currentCategory];
    const concept = category.concepts.find(c => c.id === conceptId);

    if (!concept) return;

    state.currentConcept = conceptId;
    state.currentConceptData = concept;
    state.currentStep = 0;
    state.isQuizMode = false;
    state.quizAnswers = {};

    // 更新选择器
    if (domCache.conceptSelector) {
        domCache.conceptSelector.value = conceptId;
    }

    // 关闭重新加载
    stopPlay();
    startLoading();
}

// ============================================
// 弹窗控制
// ============================================
function openConceptAnalyzer() {
    initDOMCache();
    initEventListeners();
    domCache.modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
    loadConcept(state.currentConcept || 'tcp-handshake');
}

function closeConceptAnalyzer() {
    domCache.modal.classList.add('hidden');
    document.body.style.overflow = '';
    stopPlay();
    saveProgress();
}

// ============================================
// 加载状态
// ============================================
function startLoading() {
    isLoading = true;
    domCache.sandboxSkeleton.classList.remove('hidden');
    domCache.sandboxStage.style.opacity = '0.3';

    setTimeout(() => {
        isLoading = false;
        domCache.sandboxSkeleton.classList.add('hidden');
        domCache.sandboxStage.style.opacity = '1';
        renderStep(0);
        renderStepIndicators();
        updateProgressDisplay();
    }, 1500);
}

// ============================================
// 步骤渲染
// ============================================
function renderStep(stepIndex) {
    if (isLoading || !state.currentConceptData || stepIndex < 0 || stepIndex >= state.currentConceptData.steps.length) return;

    currentStep = stepIndex;
    const step = state.currentConceptData.steps[stepIndex];

    // 更新标题
    domCache.stepTitle.textContent = step.title;
    if (domCache.conceptSubtitle) {
        domCache.conceptSubtitle.textContent = state.currentConceptData.name;
    }

    // 更新步骤指示器
    updateStepIndicators(stepIndex);

    // 更新进度条
    updateScrubber(stepIndex);

    // 更新控制按钮状态
    updateControlButtons(stepIndex);

    // 打字机效果
    typewriterEffect(step.description);

    // 更新可视化
    updateVisualState(step.visualState);

    // 标记完成
    if (stepIndex === state.currentConceptData.steps.length - 1) {
        markConceptComplete();
    }
}

function renderStepIndicators() {
    const container = domCache.stepIndicators;
    if (!container || !state.currentConceptData) return;

    container.innerHTML = '';
    const steps = state.currentConceptData.steps;

    steps.forEach((_, index) => {
        const dot = document.createElement('div');
        dot.className = 'step-dot' + (index === currentStep ? ' active' : index < currentStep ? ' completed' : '');
        dot.onclick = () => goToStep(index);
        dot.title = `步骤 ${index + 1}`;
        container.appendChild(dot);
    });
}

function updateStepIndicators(activeIndex) {
    if (!state.currentConceptData) return;

    const dots = document.querySelectorAll('.step-dot');
    dots.forEach((dot, index) => {
        dot.classList.remove('active', 'completed');
        if (index === activeIndex) {
            dot.classList.add('active');
        } else if (index < activeIndex) {
            dot.classList.add('completed');
        }
    });
}

function updateScrubber(stepIndex) {
    if (!state.currentConceptData) return;

    const total = state.currentConceptData.steps.length;
    const progress = ((stepIndex + 1) / total) * 100;

    domCache.scrubberFill.style.width = progress + '%';
    domCache.scrubberThumb.style.left = progress + '%';
    domCache.currentStep.textContent = `${stepIndex + 1}/${total}`;
    domCache.stepCounter.textContent = stepIndex + 1;
    if (document.getElementById('step-total')) {
        document.getElementById('step-total').textContent = total;
    }
}

function updateControlButtons(stepIndex) {
    if (!state.currentConceptData) return;

    const total = state.currentConceptData.steps.length;
    domCache.btnPrev.style.opacity = stepIndex === 0 ? '0.3' : '1';
    domCache.btnNext.style.opacity = stepIndex === total - 1 ? '0.3' : '1';
}

// ============================================
// 打字机效果
// ============================================
function typewriterEffect(html) {
    const container = domCache.typewriterText;
    if (!container) return;

    if (typewriterTimeout) clearTimeout(typewriterTimeout);

    container.innerHTML = '';

    const temp = document.createElement('div');
    temp.innerHTML = html;
    const plainText = temp.textContent;

    let charIndex = 0;
    const speed = 25;

    function typeChar() {
        if (charIndex < plainText.length) {
            container.innerHTML = html.substring(0, findHtmlIndex(html, charIndex + 1));
            charIndex++;
            typewriterTimeout = setTimeout(typeChar, speed);
        } else {
            container.innerHTML = html;
        }
    }

    function findHtmlIndex(htmlText, textIndex) {
        let textCount = 0;
        let inTag = false;
        let i = 0;
        for (i = 0; i < htmlText.length && textCount < textIndex; i++) {
            if (htmlText[i] === '<') inTag = true;
            else if (htmlText[i] === '>') inTag = false;
            else if (!inTag) textCount++;
        }
        return i;
    }

    typeChar();
}

// ============================================
// 可视化状态更新
// ============================================
function updateVisualState(visualState) {
    // 重置所有节点
    document.querySelectorAll('.node-glow').forEach(node => {
        node.classList.remove('active', 'synced');
    });

    // 隐藏所有脉冲
    document.querySelectorAll('.pulse-ring').forEach(ring => {
        ring.classList.add('hidden');
    });

    // 隐藏所有数据包
    ['packet-syn', 'packet-synack', 'packet-ack', 'packet-fin', 'packet-query', 'packet-result', 'packet-compare', 'packet-narrow', 'packet-search', 'packet-partition', 'packet-recurse', 'packet-merge', 'packet-chain', 'packet-probe', 'packet-rehash', 'packet-check', 'packet-isolate', 'packet-commit', 'packet-split', 'packet-divide', 'packet-range', 'packet-share', 'packet-context', 'packet-comm', 'packet-map', 'packet-swap', 'packet-tlb', 'packet-dns', 'packet-request', 'packet-response', 'packet-syn', 'packet-root', 'packet-tld', 'packet-auth'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.opacity = '0';
    });

    // 隐藏所有连线
    ['line-client-server', 'line-server-established', 'line-client-established', 'line-dns-root', 'line-dns-tld', 'line-dns-auth', 'line-partition'].forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.classList.remove('active');
            el.style.display = '';
        }
    });

    // 激活对应节点
    visualState.activeNodes.forEach(nodeId => {
        const node = document.getElementById(`node-${nodeId}`);
        if (node) {
            if (nodeId === visualState.highlight) {
                node.classList.add('active');
                const pulse = document.getElementById(`pulse-${nodeId}`);
                if (pulse) pulse.classList.remove('hidden');
            } else {
                node.classList.add('synced');
            }
        }
    });

    // 激活连线
    activateConnections(visualState);

    // 播放数据包动画
    if (visualState.packet) {
        animatePacket(visualState.packet);
    }

    // 更新活跃节点显示
    updateActiveNodesDisplay(visualState.activeNodes);
}

function activateConnections(visualState) {
    // 通用网络连接
    if (visualState.highlight === 'client' || visualState.highlight === 'server') {
        const line = document.getElementById('line-client-server');
        if (line) line.classList.add('active');
    }

    if (visualState.activeNodes.includes('dns-server') && visualState.activeNodes.includes('root-server')) {
        const line = document.getElementById('line-dns-root');
        if (line) line.style.display = 'block';
    }
}

function animatePacket(packetType) {
    const packetMap = {
        'synack': { id: 'packet-synack', start: '50%', top: '20%', color: 'blue' },
        'ack': { id: 'packet-ack', start: '20%', top: '45%', color: 'green' },
        'fin': { id: 'packet-fin', start: '50%', top: '45%', color: 'red' },
        'query': { id: 'packet-query', start: '50%', top: '50%', color: 'purple' },
        'result': { id: 'packet-result', start: '50%', top: '50%', color: 'green' },
        'compare': { id: 'packet-compare', start: '50%', top: '50%', color: 'blue' },
        'narrow': { id: 'packet-narrow', start: '50%', top: '50%', color: 'purple' },
        'search': { id: 'packet-search', start: '50%', top: '50%', color: 'green' },
        'partition': { id: 'packet-partition', start: '50%', top: '50%', color: 'blue' },
        'recurse': { id: 'packet-recurse', start: '50%', top: '50%', color: 'purple' },
        'merge': { id: 'packet-merge', start: '50%', top: '50%', color: 'green' },
        'chain': { id: 'packet-chain', start: '50%', top: '50%', color: 'blue' },
        'probe': { id: 'packet-probe', start: '50%', top: '50%', color: 'purple' },
        'rehash': { id: 'packet-rehash', start: '50%', top: '50%', color: 'green' },
        'check': { id: 'packet-check', start: '50%', top: '50%', color: 'blue' },
        'isolate': { id: 'packet-isolate', start: '50%', top: '50%', color: 'purple' },
        'commit': { id: 'packet-commit', start: '50%', top: '50%', color: 'green' },
        'split': { id: 'packet-split', start: '50%', top: '50%', color: 'blue' },
        'divide': { id: 'packet-divide', start: '50%', top: '50%', color: 'purple' },
        'range': { id: 'packet-range', start: '50%', top: '50%', color: 'green' },
        'share': { id: 'packet-share', start: '50%', top: '50%', color: 'blue' },
        'context': { id: 'packet-context', start: '50%', top: '50%', color: 'purple' },
        'comm': { id: 'packet-comm', start: '50%', top: '50%', color: 'green' },
        'map': { id: 'packet-map', start: '50%', top: '50%', color: 'blue' },
        'swap': { id: 'packet-swap', start: '50%', top: '50%', color: 'purple' },
        'tlb': { id: 'packet-tlb', start: '50%', top: '50%', color: 'green' },
        'dns': { id: 'packet-dns', start: '50%', top: '50%', color: 'blue' },
        'request': { id: 'packet-request', start: '50%', top: '50%', color: 'purple' },
        'response': { id: 'packet-response', start: '50%', top: '50%', color: 'green' },
        'syn': { id: 'packet-syn', start: '50%', top: '20%', color: 'purple' },
        'root': { id: 'packet-root', start: '50%', top: '50%', color: 'blue' },
        'tld': { id: 'packet-tld', start: '50%', top: '50%', color: 'purple' },
        'auth': { id: 'packet-auth', start: '50%', top: '50%', color: 'green' }
    };

    const packet = packetMap[packetType];
    if (!packet) return;

    const el = document.getElementById(packet.id);
    if (!el) return;

    el.style.left = packet.start;
    el.style.top = packet.top;
    el.style.opacity = '1';
    el.style.transform = 'translate(-50%, -50%)';
}

function updateActiveNodesDisplay(activeNodes) {
    const container = domCache.activeNodes;
    if (!container) return;

    container.innerHTML = '';

    const nodeLabels = {
        'client': 'Client',
        'server': 'Server',
        'established': '已连接',
        'dns-server': 'DNS服务器',
        'root-server': '根服务器',
        'tld-server': 'TLD服务器',
        'auth-server': '权威DNS'
    };

    activeNodes.forEach(nodeId => {
        const tag = document.createElement('span');
        tag.className = 'px-3 py-1 rounded-full bg-purple-500/20 text-purple-300 text-sm border border-purple-500/30';
        tag.textContent = nodeLabels[nodeId] || nodeId;
        container.appendChild(tag);
    });
}

// ============================================
// 播放控制
// ============================================
function togglePlay() {
    if (isPlaying) {
        stopPlay();
    } else {
        startPlay();
    }
}

function startPlay() {
    if (!state.currentConceptData) return;

    if (currentStep >= state.currentConceptData.steps.length - 1) {
        currentStep = -1;
    }

    isPlaying = true;
    domCache.playIcon.classList.add('hidden');
    domCache.pauseIcon.classList.remove('hidden');
    domCache.btnPlay.classList.add('playing');

    playInterval = setInterval(() => {
        if (currentStep < state.currentConceptData.steps.length - 1) {
            nextStep();
        } else {
            stopPlay();
        }
    }, 3500);
}

function stopPlay() {
    isPlaying = false;
    domCache.playIcon.classList.remove('hidden');
    domCache.pauseIcon.classList.add('hidden');
    domCache.btnPlay.classList.remove('playing');

    if (playInterval) {
        clearInterval(playInterval);
        playInterval = null;
    }
}

function prevStep() {
    if (currentStep > 0) {
        stopPlay();
        renderStep(currentStep - 1);
    }
}

function nextStep() {
    if (!state.currentConceptData) return;

    stopPlay();
    if (currentStep < state.currentConceptData.steps.length - 1) {
        renderStep(currentStep + 1);
    }
}

function goToStep(index) {
    stopPlay();
    renderStep(index);
}

function scrubToStep(event) {
    if (!state.currentConceptData) return;

    const scrubber = document.getElementById('scrubber');
    if (!scrubber) return;

    const rect = scrubber.getBoundingClientRect();
    const percent = (event.clientX - rect.left) / rect.width;
    const stepIndex = Math.round(percent * (state.currentConceptData.steps.length - 1));
    stopPlay();
    renderStep(Math.max(0, Math.min(stepIndex, state.currentConceptData.steps.length - 1)));
}

function regenerateConcept() {
    domCache.regenerateIcon.classList.add('spin-once');
    stopPlay();
    currentStep = 0;

    setTimeout(() => {
        domCache.regenerateIcon.classList.remove('spin-once');
        startLoading();
    }, 1000);
}

// ============================================
// 进度管理
// ============================================
function markConceptComplete() {
    if (state.currentConcept) {
        state.completedConcepts.add(state.currentConcept);
        saveProgress();
        updateProgressDisplay();
    }
}

function saveProgress() {
    localStorage.setItem('completedConcepts', JSON.stringify([...state.completedConcepts]));
}

function updateProgressDisplay() {
    const container = domCache.conceptProgress;
    if (!container) return;

    const total = Object.values(conceptDatabase).reduce((sum, cat) => sum + cat.concepts.length, 0);
    const completed = state.completedConcepts.size;
    const percent = total > 0 ? Math.round((completed / total) * 100) : 0;

    container.innerHTML = `
        <div class="flex items-center gap-2">
            <div class="flex-1 h-2 bg-white/10 rounded-full overflow-hidden">
                <div class="h-full bg-gradient-to-r from-purple-500 to-blue-500 transition-all duration-500" style="width: ${percent}%"></div>
            </div>
            <span class="text-xs text-white/60">${completed}/${total}</span>
        </div>
    `;
}

// ============================================
// 键盘控制
// ============================================
function initKeyboardControls() {
    document.addEventListener('keydown', (e) => {
        if (!domCache.modal || domCache.modal.classList.contains('hidden')) return;

        if (e.key === 'ArrowLeft') {
            prevStep();
        } else if (e.key === 'ArrowRight') {
            nextStep();
        } else if (e.key === ' ') {
            e.preventDefault();
            togglePlay();
        } else if (e.key === 'Escape') {
            closeConceptAnalyzer();
        }
    });
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', init);
