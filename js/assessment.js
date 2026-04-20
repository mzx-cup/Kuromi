const API_URL = `${window.location.origin}/api`;

let currentStep = 1;
const totalSteps = 10;
const assessmentData = {
    learningDirection: null,  // 学习方向
    languages: [],            // 编程语言（多选）
    knowledgeBase: null,      // 知识基础
    codeSkill: null,          // 编程能力
    learningGoal: null,       // 学习目标
    cognitiveStyle: null,     // 认知风格
    studyTime: null,          // 学习时间
    learningPace: null,       // 学习节奏
    focusLevel: null,         // 专注度
    quizResults: []           // 测验结果
};

// Quiz state
let quizState = {
    currentQuestion: 0,
    hearts: 3,
    answers: [],
    questions: []
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

// Quiz questions generator based on learning direction and knowledge level
function generateQuizQuestions() {
    const direction = assessmentData.learningDirection || 'bigdata';
    const level = assessmentData.codeSkill || 'beginner';
    const languages = assessmentData.languages || ['python'];

    const quizBank = {
        bigdata: [
            {
                question: 'HDFS 中，NameNode 存储的是什么信息？',
                options: ['文件内容数据', '文件元数据（MetaData）', 'DataNode 心跳信息', '数据块副本'],
                correct: 1,
                explanation: 'NameNode 是 HDFS 的核心节点，存储文件系统的命名空间、文件到块的映射、以及块的副本位置信息（元数据），不存储实际文件内容。'
            },
            {
                question: 'MapReduce 中的 Combiner 函数的作用是？',
                options: ['对数据进行排序', '在 Map 端进行本地聚合，减少网络传输', '将结果写入 HDFS', '监控任务进度'],
                correct: 1,
                explanation: 'Combiner 是 MapReduce 的优化组件，在每个 Map 节点上对输出进行局部聚合，减少 shuffle 阶段的网络数据传输量。'
            },
            {
                question: 'Spark RDD 的 transformation 操作是？',
                options: ['立即执行并返回结果', '惰性求值，延迟执行', '立即写入磁盘', '同步阻塞操作'],
                correct: 1,
                explanation: 'Spark RDD 的 transformation 操作（如 map, filter）采用惰性求值策略，只有遇到 action 操作时才会真正执行计算。'
            },
            {
                question: 'Kafka 消息的 offset 作用是？',
                options: ['消息优先级', '消息在分区中的唯一序号', '消息时间戳', '消息大小'],
                correct: 1,
                explanation: 'offset 是 Kafka 中消息在分区内的顺序标识，每个消费者通过 offset 来追踪已消费的消息位置，实现精确的消息消费控制。'
            },
            {
                question: 'Flink 的 watermark 机制用于解决什么问题？',
                options: ['网络延迟', '处理乱序事件和事件时间', '内存溢出', '任务失败恢复'],
                correct: 1,
                explanation: 'Watermark 是 Flink 事件时间处理的核心机制，用于告诉窗口等待多长时间来处理乱序到达的事件，平衡延迟和完整性。'
            },
            {
                question: 'Hive 与 HBase 的主要区别是？',
                options: ['Hive 支持 SQL，HBase 是 NoSQL', 'HBase 支持 SQL，Hive 是 NoSQL', '两者完全相同', '都只能存储结构化数据'],
                correct: 0,
                explanation: 'Hive 提供了 SQL 查询接口（HiveQL），适合批量数据分析；HBase 是面向列的 NoSQL 数据库，适合实时读写场景。'
            },
            {
                question: 'Zookeeper 在 Hadoop 集群中的作用是？',
                options: ['数据存储', '分布式协调服务', '任务调度', '文件压缩'],
                correct: 1,
                explanation: 'Zookeeper 提供分布式协调服务，用于 Hadoop 集群中的 leader 选举、分布式锁、配置管理等核心协调功能。'
            }
        ],
        ai: [
            {
                question: '监督学习与无监督学习的主要区别是？',
                options: ['监督学习需要标签数据', '无监督学习需要标签数据', '两者都需要标签', '两者都不需要标签'],
                correct: 0,
                explanation: '监督学习使用带标签的训练数据学习输入到输出的映射关系；无监督学习则从无标签数据中发现隐藏模式（如聚类、降维）。'
            },
            {
                question: '梯度下降算法中学习率（learning rate）的作用是？',
                options: ['控制模型的复杂度', '控制参数更新的步长', '加速模型收敛', '防止过拟合'],
                correct: 1,
                explanation: '学习率决定了梯度下降过程中参数更新的幅度。过大的学习率可能导致震荡，过小则收敛缓慢，需要合理调节。'
            },
            {
                question: '卷积神经网络（CNN）中 Pooling 层的作用是？',
                options: ['增加特征图尺寸', '减少特征图尺寸，降低计算量，增强平移不变性', '增加网络深度', '防止梯度消失'],
                correct: 1,
                explanation: 'Pooling（池化）层通过下采样减少特征图尺寸，降低计算复杂度，同时增强模型对特征平移的鲁棒性。'
            },
            {
                question: 'Transformer 模型中的 Self-Attention 机制计算的是？',
                options: ['卷积核权重', '序列内各位置之间的相关性', '梯度值', '损失函数'],
                correct: 1,
                explanation: 'Self-Attention 通过计算序列中每个位置与所有其他位置的关联程度（Query-Key 相似度），捕捉长距离依赖关系。'
            },
            {
                question: '过拟合（Overfitting）是指？',
                options: ['模型在训练和测试上表现都差', '模型在训练上差，测试上好', '模型在训练上好，测试上差', '模型在训练和测试上表现都好'],
                correct: 2,
                explanation: '过拟合指模型过度学习了训练数据的细节和噪声，导致在未见过的测试数据上表现下降，是机器学习中的常见问题。'
            },
            {
                question: 'LSTM 通过什么机制解决梯度消失问题？',
                options: ['ReLU 激活', '门控机制（遗忘门、输入门、输出门）', '残差连接', '批量归一化'],
                correct: 1,
                explanation: 'LSTM 通过门控机制选择性地保留或遗忘信息，保持梯度在长时间序列中有效传播，从而缓解梯度消失问题。'
            },
            {
                question: '反向传播（Backpropagation）算法的核心是？',
                options: ['前向传播输入数据', '链式法则计算梯度', '随机初始化权重', '批量处理数据'],
                correct: 1,
                explanation: '反向传播利用链式法则从输出层向输入层逐层计算损失函数对每个参数的梯度，是训练神经网络的核心算法。'
            }
        ],
        frontend: [
            {
                question: 'JavaScript 中 let、const 和 var 的主要区别是？',
                options: ['没有区别', 'const 不可变，let 块级作用域，var 函数作用域', '都是全局变量', '只影响性能'],
                correct: 1,
                explanation: 'let 和 const 是 ES6 引入的块级作用域声明，const 声明常量不可重新赋值，而 var 是函数作用域，存在变量提升问题。'
            },
            {
                question: 'React 中 useEffect 的第二个参数空数组 [] 表示？',
                options: ['每次渲染都执行', '从不执行', '只在首次渲染后执行（类似 componentDidMount）', '组件卸载时执行'],
                correct: 2,
                explanation: 'useEffect 的第二个参数为空数组时，effect 只在组件首次渲染后执行一次，用于处理副作用如数据获取、订阅等。'
            },
            {
                question: 'CSS Flexbox 中 justify-content 和 align-items 的区别是？',
                options: ['没有区别', 'justify-content 主轴对齐，align-items 交叉轴对齐', '两者都是主轴对齐', '两者都是交叉轴对齐'],
                correct: 1,
                explanation: 'justify-content 沿主轴（main axis）对齐 flex 项目，align-items 沿交叉轴（cross axis）对齐，是 Flexbox 布局的核心属性。'
            },
            {
                question: 'Vue 响应式原理中，当修改数组元素时，视图是否会更新？',
                options: ['会更新（Vue 2/3 都支持）', 'Vue 2 不支持直接索引修改，Vue 3 支持', '不会更新', '需要手动调用 $forceUpdate'],
                correct: 1,
                explanation: 'Vue 2 中通过数组索引直接赋值不会触发响应式更新，需要使用 Vue.set 或 splice；Vue 3 则基于 Proxy 实现，完全支持。'
            },
            {
                question: '浏览器事件冒泡（Event Bubbling）是指？',
                options: ['事件从子元素向父元素传播', '事件从父元素向子元素传播', '事件只发生在当前元素', '事件立即被执行'],
                correct: 0,
                explanation: '事件冒泡是 DOM 事件传播机制之一，当事件发生在子元素上时，会向上层父元素传播直到根节点，可通过 event.stopPropagation() 阻止。'
            },
            {
                question: 'TypeScript 中 interface 和 type 的主要区别是？',
                options: ['没有区别', 'interface 可被合并（声明合并），type 更灵活支持联合/交叉类型', 'type 可以继承，interface 不行', 'interface 性能更高'],
                correct: 1,
                explanation: 'interface 支持声明合并，适合定义对象结构；type 更灵活，可定义联合类型、交叉类型、元组等，功能更全面。'
            },
            {
                question: 'Webpack 的 tree shaking 作用是？',
                options: ['压缩代码', '移除未使用的模块/代码', '混淆代码', '合并文件'],
                correct: 1,
                explanation: 'Tree shaking 是基于 ES Module 的静态分析，移除未使用的导出代码，减小打包体积，是构建优化的重要手段。'
            }
        ],
        backend: [
            {
                question: 'RESTful API 中 GET、POST、PUT、DELETE 方法的区别是？',
                options: ['没有区别', 'GET 查询、POST 创建、PUT 更新、DELETE 删除', '都用于查询', '都用于创建'],
                correct: 1,
                explanation: 'RESTful 设计规范中，GET 用于资源查询，POST 用于创建资源，PUT 用于完整更新资源，DELETE 用于删除资源。'
            },
            {
                question: '数据库索引（Index）的主要作用是？',
                options: ['存储数据', '加速数据检索', '保证数据安全', '压缩数据'],
                correct: 1,
                explanation: '索引是数据库的优化结构，通过维护额外的数据指针（通常是 B+ 树），大幅提升数据查询速度，代价是额外的存储空间和写入开销。'
            },
            {
                question: 'Redis 与 Memcached 的主要区别是？',
                options: ['没有区别', 'Redis 支持更多数据类型和持久化，Memcached 仅支持字符串', 'Memcached 支持复杂数据类型', '两者都是关系型'],
                correct: 1,
                explanation: 'Redis 支持字符串、哈希、列表、集合、有序集合等多种数据类型，支持 RDB 和 AOF 持久化；Memcached 仅支持简单的键值存储。'
            },
            {
                question: '微服务架构中服务发现（Service Discovery）的作用是？',
                options: ['加密通信', '动态管理和定位服务实例', '负载均衡', '数据分片'],
                correct: 1,
                explanation: '服务发现让微服务能够动态地注册和查找其他服务实例的地址，实现服务间的松耦合通信，是微服务基础设施的核心组件。'
            },
            {
                question: 'SQL 中 JOIN 和 LEFT JOIN 的区别是？',
                options: ['没有区别', 'JOIN 只返回匹配行，LEFT JOIN 返回左表所有行及匹配行', 'JOIN 返回所有行', 'LEFT JOIN 只返回左表'],
                correct: 1,
                explanation: 'INNER JOIN 只返回两表连接条件匹配的行；LEFT JOIN 返回左表全部记录及右表匹配记录，右表无匹配时以 NULL 填充。'
            },
            {
                question: 'Kafka 与 RabbitMQ 相比，在高吞吐量场景下的优势是？',
                options: ['支持消息事务', '顺序写入 + 批量传输实现高吞吐', '支持更多协议', '更易部署'],
                correct: 1,
                explanation: 'Kafka 采用顺序写入磁盘和批量压缩传输机制，在高吞吐量场景下性能优异，适合日志采集、大数据实时处理等场景。'
            },
            {
                question: 'OAuth 2.0 的授权码模式流程是？',
                options: ['直接传递密码', '通过授权码中转，保护敏感信息在浏览器端不暴露', '不需要重定向', '不需要客户端密钥'],
                correct: 1,
                explanation: '授权码模式通过浏览器获取授权码，后端服务使用授权码换取 access_token，敏感信息不在浏览器暴露，是最安全的 OAuth 流程。'
            }
        ],
        algorithm: [
            {
                question: '时间复杂度 O(n log n) 的排序算法是？',
                options: ['冒泡排序 O(n²)', '归并排序 / 快速排序 O(n log n)', '计数排序 O(n+k)', '选择排序 O(n²)'],
                correct: 1,
                explanation: '归并排序和快速排序（平均情况）的时间复杂度是 O(n log n)；冒泡、选择排序是 O(n²)；计数排序是 O(n+k)。'
            },
            {
                question: '堆（Heap）数据结构的主要应用场景是？',
                options: ['图的广度优先搜索', '实现优先队列和求 Top K 问题', '字符串匹配', '排序'],
                correct: 1,
                explanation: '堆是一种完全二叉树结构，根节点总是最大/最小，适合实现优先队列和在海量数据中求 Top K、K 个最小/最大元素。'
            },
            {
                question: '动态规划（DP）解决问题的关键步骤是？',
                options: ['递归搜索所有解', '定义状态、状态转移方程、计算顺序', '分治治乱', '回溯剪枝'],
                correct: 1,
                explanation: '动态规划的核心是：定义重叠子问题的状态、找出状态转移方程、确定计算顺序（自底向上或自顶向下 + 记忆化）。'
            },
            {
                question: '布隆过滤器（Bloom Filter）可以实现？',
                options: ['精确计数', '确定存在判断（可能有假阳性，不可判断确定不存在）', '精确去重', '排序'],
                correct: 1,
                explanation: '布隆过滤器使用多个哈希函数映射到位数组，可以快速判断元素可能存在（可能误判），但无法判断确定不存在，适合大规模去重场景。'
            },
            {
                question: 'B+ 树相比 B 树更适合做数据库索引的原因是？',
                options: ['B+ 树更矮', 'B+ 树所有数据在叶子节点且叶子节点链表连接，区间查询高效', 'B+ 树节点存储更多指针', 'B+ 树更平衡'],
                correct: 1,
                explanation: 'B+ 树非叶子节点只存储索引，叶子节点包含所有数据并用链表连接，适合范围查询和顺序访问，是 MySQL InnoDB 索引的数据结构。'
            },
            {
                question: '图论中 Dijkstra 算法用于解决什么问题？',
                options: ['检测环路', '单源最短路径（边权非负）', '最大流', '二分图匹配'],
                correct: 1,
                explanation: 'Dijkstra 算法在边权非负的情况下，计算从单个源点到所有其他节点的最短路径，使用贪心策略和最小堆优化。'
            },
            {
                question: '一致性哈希（Consistent Hashing）的主要优点是？',
                options: ['数据绝对均衡分布', '节点增减时只需重新分配部分数据，减少迁移', '查找速度最快', '不需要哈希函数'],
                correct: 1,
                explanation: '一致性哈希通过环形空间和虚拟节点，使节点增减时只影响相邻区间的数据，大幅减少缓存/数据迁移量，用于分布式缓存系统。'
            }
        ],
        database: [
            {
                question: 'MySQL InnoDB 的 MVCC（多版本并发控制）是为了解决？',
                options: ['数据安全问题', '读写冲突，提高并发性能', '存储空间问题', '网络延迟问题'],
                correct: 1,
                explanation: 'MVCC 通过保存数据的多个版本，使读操作不加锁、写操作不阻塞读，实现读写不冲突，显著提升数据库并发性能。'
            },
            {
                question: '数据库事务的 ACID 特性中，"I" 代表什么？',
                options: ['独立性', '隔离性', '完整性', '原子性'],
                correct: 1,
                explanation: 'ACID 中的 I 是 Isolation（隔离性），指多个事务并发执行时相互隔离，不互相干扰，通过锁和 MVCC 机制实现。'
            },
            {
                question: 'Redis 的 AOF 持久化模式是？',
                options: ['定时全量快照', '记录每次写命令到日志文件', '定期压缩内存', '写入数据库后备份'],
                correct: 1,
                explanation: 'AOF（Append Only File）通过记录每个写操作命令到日志文件实现持久化，数据恢复时重放命令，比 RDB 持久化更完整但文件更大。'
            },
            {
                question: 'MongoDB 的文档型存储与关系型数据库的主要区别是？',
                options: ['不支持查询', 'Schema 灵活，JSON 格式存储', '性能一定更差', '只能存储字符串'],
                correct: 1,
                explanation: 'MongoDB 是文档型 NoSQL 数据库，数据以 JSON/BSON 格式存储，Schema 灵活（无固定表结构），适合快速迭代和半结构化数据存储。'
            },
            {
                question: '数据库连接池（Connection Pool）的作用是？',
                options: ['存储数据', '复用数据库连接，减少连接创建开销，提高性能', '加密连接', '监控查询'],
                correct: 1,
                explanation: '数据库连接池预创建并复用一组连接，避免每次请求都创建/销毁连接的开销，大幅提升高并发场景下的数据库访问性能。'
            },
            {
                question: 'SQL 中 COUNT(*)、COUNT(1)、COUNT(列名) 的区别是？',
                options: ['没有区别', 'COUNT(*) 包含 NULL，COUNT(列) 不含 NULL', 'COUNT(列) 更快', 'COUNT(1) 包含 NULL'],
                correct: 1,
                explanation: 'COUNT(*) 统计所有行包括 NULL 值，COUNT(column) 只统计非 NULL 值，COUNT(1) 等价于 COUNT(*)（InnoDB 优化）。'
            },
            {
                question: '数据库读写分离的主要目的是？',
                options: ['数据备份', '提高并发读取性能', '降低存储成本', '简化编程'],
                correct: 1,
                explanation: '读写分离将读操作分流到从库，写操作在主库执行，提升数据库整体并发读取能力，是应对高读取负载的常见架构方案。'
            }
        ]
    };

    const directionQuestions = quizBank[direction] || quizBank.bigdata;
    const skillLevel = assessmentData.codeSkill || 'beginner';

    // Adjust difficulty based on skill level
    let startIndex = 0;
    let endIndex = 5;
    if (skillLevel === 'advanced' || skillLevel === 'intermediate') {
        startIndex = 2;
        endIndex = 7;
    }

    // Select 5 questions based on direction and skill
    const selectedQuestions = [];
    const indices = new Set();

    while (indices.size < 5 && indices.size < directionQuestions.length) {
        const idx = Math.floor(Math.random() * (endIndex - startIndex)) + startIndex;
        if (!indices.has(idx)) {
            indices.add(idx);
            selectedQuestions.push(directionQuestions[idx]);
        }
    }

    // Fill with other direction questions if needed
    if (selectedQuestions.length < 5) {
        for (const d in quizBank) {
            if (d !== direction && selectedQuestions.length < 5) {
                const otherQuestions = quizBank[d];
                let idx = Math.floor(Math.random() * Math.min(3, otherQuestions.length));
                if (!indices.has(idx)) {
                    indices.add(idx);
                    selectedQuestions.push(otherQuestions[idx]);
                }
            }
        }
    }

    return selectedQuestions;
}

// Render quiz question
function renderQuizQuestion() {
    const container = document.getElementById('quiz-question-container');
    const question = quizState.questions[quizState.currentQuestion];

    if (!question) {
        // Move to result step after quiz
        goToStep(11);
        return;
    }

    document.getElementById('quiz-current-num').textContent = quizState.currentQuestion + 1;
    document.getElementById('quiz-total-num').textContent = quizState.questions.length;

    // Update hearts display
    const heartsContainer = document.getElementById('quiz-hearts');
    heartsContainer.innerHTML = Array(3).fill(0).map((_, i) =>
        `<span class="quiz-heart ${i >= quizState.hearts ? 'lost' : ''}">❤️</span>`
    ).join('');

    // Update progress dots
    const progressDots = document.querySelector('.quiz-progress-dots') || createProgressDots();
    updateProgressDots();

    // Render question
    container.innerHTML = `
        <div class="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-2xl p-6 mb-4 fade-in">
            <p class="text-lg font-semibold text-gray-800 mb-4">${question.question}</p>
            <div class="space-y-3">
                ${question.options.map((opt, idx) => `
                    <div class="quiz-option-btn p-4 border-2 border-gray-200 rounded-xl flex items-center gap-3"
                         data-index="${idx}" onclick="selectQuizOption(${idx})">
                        <div class="w-8 h-8 rounded-full border-2 border-gray-300 flex items-center justify-center font-bold text-sm flex-shrink-0 option-letter">
                            ${String.fromCharCode(65 + idx)}
                        </div>
                        <span class="option-text">${opt}</span>
                    </div>
                `).join('')}
            </div>
        </div>
    `;

    // Hide feedback
    document.getElementById('quiz-feedback').classList.add('hidden');
}

function createProgressDots() {
    const container = document.createElement('div');
    container.className = 'quiz-progress-dots mb-4';
    document.getElementById('quiz-question-container').before(container);
    return container;
}

function updateProgressDots() {
    const container = document.querySelector('.quiz-progress-dots');
    if (!container) return;

    container.innerHTML = quizState.questions.map((_, i) => {
        let cls = 'quiz-dot';
        if (i < quizState.currentQuestion) {
            cls += quizState.answers[i] ? ' completed' : ' wrong';
        } else if (i === quizState.currentQuestion) {
            cls += ' current';
        }
        return `<div class="${cls}"></div>`;
    }).join('');
}

function selectQuizOption(index) {
    const question = quizState.questions[quizState.currentQuestion];
    const isCorrect = index === question.correct;

    // Disable all options
    document.querySelectorAll('.quiz-option-btn').forEach(btn => {
        btn.style.pointerEvents = 'none';
        const optIndex = parseInt(btn.dataset.index);
        if (optIndex === question.correct) {
            btn.classList.add('correct');
            btn.querySelector('.option-letter').style.background = 'rgba(255,255,255,0.3)';
        } else if (optIndex === index && !isCorrect) {
            btn.classList.add('wrong');
            btn.querySelector('.option-letter').style.background = 'rgba(255,255,255,0.3)';
        }
    });

    // Record answer
    quizState.answers.push(isCorrect);

    // Show feedback
    const feedback = document.getElementById('quiz-feedback');
    feedback.classList.remove('hidden');
    feedback.className = `p-4 rounded-xl mb-4 fade-in ${isCorrect ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`;

    document.getElementById('feedback-icon').innerHTML = isCorrect
        ? '<div class="w-10 h-10 rounded-full bg-green-500 flex items-center justify-center"><svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg></div>'
        : '<div class="w-10 h-10 rounded-full bg-red-500 flex items-center justify-center"><svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg></div>';

    document.getElementById('feedback-title').textContent = isCorrect ? '回答正确！' : '回答错误';
    document.getElementById('feedback-title').className = `font-semibold ${isCorrect ? 'text-green-700' : 'text-red-700'}`;
    document.getElementById('feedback-detail').textContent = isCorrect ? question.explanation : question.explanation;

    if (!isCorrect) {
        quizState.hearts--;
        const heartsContainer = document.getElementById('quiz-hearts');
        heartsContainer.innerHTML = Array(3).fill(0).map((_, i) =>
            `<span class="quiz-heart ${i >= quizState.hearts ? 'lost' : ''}">❤️</span>`
        ).join('');

        if (quizState.hearts <= 0) {
            // Game over - show results
            setTimeout(() => {
                goToStep(11);
            }, 1500);
            return;
        }
    }

    // Auto advance after delay
    setTimeout(() => {
        quizState.currentQuestion++;
        if (quizState.currentQuestion < quizState.questions.length) {
            renderQuizQuestion();
        } else {
            // Quiz completed
            goToStep(11);
        }
    }, 2000);
}

function goToStep(step) {
    currentStep = step;
    updateStepUI();
    if (step === 10) {
        // Initialize quiz
        quizState = {
            currentQuestion: 0,
            hearts: 3,
            answers: [],
            questions: generateQuizQuestions()
        };
        renderQuizQuestion();
    } else if (step === 11) {
        // Quiz finished, generate learning plan
        generateLearningPlan();
    }
}

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

    // Update step indicators (only 9 indicators shown, step 10 is quiz)
    const indicatorsToShow = 9;
    for (let i = 1; i <= indicatorsToShow; i++) {
        const stepEl = document.getElementById(`step-${i}`);
        if (stepEl) {
            stepEl.classList.remove('active', 'completed');

            if (i < currentStep) {
                stepEl.classList.add('completed');
                stepEl.innerHTML = '<svg class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"></polyline></svg>';
            } else if (i === currentStep || (currentStep === 10 && i === 9)) {
                stepEl.classList.add('active');
                stepEl.textContent = i;
            } else {
                stepEl.textContent = i;
            }
        }
    }

    // Update progress lines
    for (let i = 1; i < indicatorsToShow; i++) {
        const lineEl = document.getElementById(`line-${i}`);
        if (lineEl) {
            if (i < currentStep || (currentStep === 10 && i >= 9)) {
                lineEl.style.background = '#10b981';
            } else {
                lineEl.style.background = 'rgba(255,255,255,0.2)';
            }
        }
    }

    // Show/hide step content (steps 1-9 are regular, step 10 is quiz, step 11 is loading/result)
    for (let i = 1; i <= 9; i++) {
        const content = document.getElementById(`step-content-${i}`);
        if (content) {
            content.classList.toggle('hidden', i !== currentStep);
        }
    }

    // Step 10 is quiz, step 11 is loading/result
    document.getElementById('step-content-10')?.classList.toggle('hidden', currentStep !== 10);

    // Handle special steps (quiz results flow through loading then result)
    if (currentStep === 10) {
        // Quiz step - handled separately
    }

    // Update navigation buttons
    const prevBtn = document.getElementById('prev-btn');
    const nextBtn = document.getElementById('next-btn');

    // Show/hide based on current step
    if (currentStep >= 10) {
        // After quiz, no prev/next buttons (goes through loading/result)
        prevBtn.style.visibility = 'hidden';
        nextBtn.style.visibility = 'hidden';
    } else {
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
    }

    // Update next button text for quiz step
    if (currentStep === 10) {
        // Quiz step - handled by quiz logic
    }

    lucide.createIcons();
}

function nextStep() {
    if (currentStep < 9) {
        currentStep++;
        updateStepUI();
    } else if (currentStep === 9) {
        // Go to quiz step (step 10) and initialize quiz
        currentStep = 10;
        quizState = {
            currentQuestion: 0,
            hearts: 3,
            answers: [],
            questions: generateQuizQuestions()
        };
        updateStepUI();
        renderQuizQuestion();
    } else {
        // All steps completed, generate plan
        generateLearningPlan();
    }
}

function prevStep() {
    if (currentStep > 1 && currentStep <= 9) {
        currentStep--;
        updateStepUI();
    }
}

async function generateLearningPlan() {
    // Show loading
    document.querySelectorAll('.assessment-step').forEach(el => el.classList.add('hidden'));
    document.getElementById('step-loading').classList.remove('hidden');
    document.getElementById('nav-buttons').classList.add('hidden');

    // Calculate radar scores and weakness analysis for AI
    const radarScores = calculateRadarScores();
    const weaknessAnalysis = analyzeWeakness();
    const quizScore = quizState.answers.filter(a => a).length;
    const quizTotal = quizState.questions.length;
    const quizResults = quizState.answers;

    // Prepare enhanced assessment data for AI
    const enhancedAssessment = {
        ...assessmentData,
        quizResults,
        quizScore,
        quizTotal,
        radarScores,
        radarLabels: ['知识掌握', '实战能力', '学习效率', '内容记忆', '问题解决', '技术深度'],
        weaknessAnalysis
    };

    try {
        // Call API to generate learning plan
        const res = await fetch(`${API_URL}/assessment/submit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                assessment: enhancedAssessment
            })
        });

        const data = await res.json();

        if (!res.ok) {
            throw new Error(data.detail || '生成学习计划失败');
        }

        // Add quiz data to response for display
        data.quizResults = quizResults;
        data.quizScore = quizScore;
        data.quizTotal = quizTotal;
        data.radarScores = radarScores;

        // Display result
        displayResult(data);

    } catch (error) {
        console.error('Error:', error);
        // Fallback: generate local plan with enhanced data
        const localPlan = generateLocalPlan(enhancedAssessment);
        displayResult(localPlan);
    }
}

function generateLocalPlan(enhancedAssessment) {
    const assessment = enhancedAssessment || assessmentData;
    const { learningDirection, languages, knowledgeBase, codeSkill, learningGoal, cognitiveStyle, studyTime, learningPace, focusLevel } = assessment;

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

    // Add personalized suggestions based on radar scores and weakness analysis
    const radarScores = assessment.radarScores || [];
    const weaknessAnalysis = assessment.weaknessAnalysis || '';
    const quizScore = assessment.quizScore || 0;
    const quizTotal = assessment.quizTotal || 5;
    const scorePercent = Math.round((quizScore / quizTotal) * 100);

    if (radarScores.length === 6) {
        const radarLabels = ['知识掌握', '实战能力', '学习效率', '内容记忆', '问题解决', '技术深度'];
        const minScore = Math.min(...radarScores);
        const minIndex = radarScores.indexOf(minScore);
        const maxScore = Math.max(...radarScores);
        const maxIndex = radarScores.indexOf(maxScore);

        // Add radar-based suggestions
        if (minScore < 50) {
            suggestion += `诊断测验显示你在${radarLabels[minIndex]}方面需要加强，我们会在后续学习中重点补充这部分内容。`;
        }

        // Add quiz result based suggestion
        if (scorePercent >= 80) {
            suggestion += `诊断测验表现优异！你的${radarLabels[maxIndex]}能力突出，继续保持！`;
        } else if (scorePercent >= 60) {
            suggestion += `测验显示你有一定基础，但${radarLabels[minIndex]}还需要持续练习。`;
        } else if (scorePercent < 40) {
            suggestion += `别担心！你的薄弱点(${radarLabels[minIndex]})正是我们教学的重点，会从基础开始帮你建立知识体系。`;
        }
    }

    // Add weakness analysis if available
    if (weaknessAnalysis) {
        suggestion += `根据答题分析，你的知识薄弱点在${weaknessAnalysis}，这是我们后续学习的重点突破方向。`;
    }

    return {
        profile: assessment,
        path: path,
        suggestion: suggestion,
        radarScores: radarScores,
        radarLabels: ['知识掌握', '实战能力', '学习效率', '内容记忆', '问题解决', '技术深度']
    };
}

function calculateRadarScores() {
    const direction = assessmentData.learningDirection || 'bigdata';
    const level = assessmentData.codeSkill || 'beginner';
    const quizScore = assessmentData.quizScore || 0;
    const quizTotal = assessmentData.quizTotal || 5;

    // Base scores from assessment data
    const levelScores = {
        zero: 20,
        basic: 40,
        intermediate: 65,
        advanced: 85
    };

    const skillScores = {
        beginner: 15,
        basic: 35,
        intermediate: 60,
        advanced: 80
    };

    // Calculate radar dimensions (0-100 scale)
    const knowledgeMastery = levelScores[assessmentData.knowledgeBase] || 30;
    const practicalAbility = skillScores[assessmentData.codeSkill] || 20;

    // Quiz performance affects practical ability (up to 20% boost/penalty)
    const quizRatio = quizScore / quizTotal;
    const quizBonus = Math.round((quizRatio - 0.5) * 30); // -15 to +15 adjustment

    // Learning efficiency based on focus and pace
    const focusScores = { high: 90, medium: 70, low: 50 };
    const paceScores = { slow: 75, normal: 80, fast: 85 };
    const learningEfficiency = (focusScores[assessmentData.focusLevel] || 70) * 0.6 +
                               (paceScores[assessmentData.learningPace] || 80) * 0.4;

    // Content retention based on cognitive style and study time
    const cognitiveScores = { visual: 75, textual: 80, pragmatic: 70 };
    const timeScores = { light: 60, moderate: 75, intensive: 85, immersive: 90 };
    const contentRetention = (cognitiveScores[assessmentData.cognitiveStyle] || 75) * 0.5 +
                              (timeScores[assessmentData.studyTime] || 70) * 0.5;

    // Problem solving based on quiz performance
    const problemSolving = Math.min(95, Math.max(25, quizRatio * 70 + 20 + (skillScores[assessmentData.codeSkill] || 20) * 0.3));

    // Technical depth based on direction and knowledge level
    const depthBase = levelScores[assessmentData.knowledgeBase] || 30;
    const directionBonus = {
        bigdata: 10, ai: 12, frontend: 8, backend: 10,
        algorithm: 15, database: 10
    };
    const technicalDepth = Math.min(95, depthBase + (directionBonus[direction] || 5));

    return [
        Math.round(knowledgeMastery),
        Math.round(practicalAbility + quizBonus),
        Math.round(learningEfficiency),
        Math.round(contentRetention),
        Math.round(problemSolving),
        Math.round(technicalDepth)
    ];
}

// Analyze weakness based on quiz results and assessment data
function analyzeWeakness() {
    const quizAnswers = quizState.answers;
    const questions = quizState.questions || [];

    if (quizAnswers.length === 0 || questions.length === 0) {
        // Fallback weakness analysis based on assessment
        if (assessmentData.knowledgeBase === 'zero') return '需要从基础概念开始补足';
        if (assessmentData.codeSkill === 'beginner') return '编程基础需要加强';
        if (assessmentData.focusLevel === 'low') return '学习专注度和持续性需提升';
        return '综合基础需要巩固';
    }

    // Analyze wrong answers
    const wrongIndices = quizAnswers.map((correct, idx) => !correct ? idx : -1).filter(idx => idx >= 0);

    if (wrongIndices.length === 0) {
        return '暂无明显短板';
    }

    // Map question topics to weakness categories
    const topicCategories = {
        'HDFS': '分布式存储原理',
        'MapReduce': '分布式计算框架',
        'Spark': '内存计算框架',
        'Kafka': '消息队列与流处理',
        'Hive': '数据仓库',
        'Flink': '流处理引擎',
        '监督学习': '机器学习算法',
        '梯度下降': '深度学习优化',
        '卷积': '计算机视觉',
        'Transformer': '大模型架构',
        'JavaScript': '前端编程',
        'React': '前端框架',
        'CSS': '样式布局',
        'REST': 'API设计',
        '数据库': '数据库原理',
        'Redis': '缓存技术',
        '微服务': '分布式架构',
        '排序': '基础算法',
        '动态规划': '算法思想',
        '堆': '数据结构',
        'MySQL': '关系型数据库',
        '索引': '数据库优化'
    };

    const weaknesses = [];
    wrongIndices.forEach(idx => {
        const question = questions[idx];
        if (question) {
            // Try to extract topic from question
            for (const [key, value] of Object.entries(topicCategories)) {
                if (question.question.includes(key)) {
                    weaknesses.push(value);
                    break;
                }
            }
        }
    });

    if (weaknesses.length === 0) {
        return '综合基础需要加强';
    }

    // Return unique weaknesses, limited to 3
    const uniqueWeaknesses = [...new Set(weaknesses)].slice(0, 3);
    return uniqueWeaknesses.join('、') || '综合基础需要加强';
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

    // Display quiz results summary
    if (data.quizResults) {
        const quizScore = data.quizScore || assessmentData.quizScore || 0;
        const quizTotal = data.quizTotal || assessmentData.quizTotal || 5;
        const scorePercent = Math.round((quizScore / quizTotal) * 100);

        // Add quiz summary to profile summary
        const quizSummaryDiv = document.createElement('div');
        quizSummaryDiv.className = 'bg-gradient-to-r from-amber-50 to-orange-50 rounded-lg p-3 shadow-sm mb-4 fade-in';
        quizSummaryDiv.innerHTML = `
            <div class="flex items-center justify-between mb-2">
                <div class="flex items-center gap-2">
                    <span class="text-lg">🎯</span>
                    <span class="font-semibold text-gray-800">诊断测验结果</span>
                </div>
                <div class="text-xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-amber-500 to-orange-500">
                    ${quizScore}/${quizTotal}
                </div>
            </div>
            <div class="w-full bg-gray-200 rounded-full h-2 mb-2">
                <div class="h-2 rounded-full bg-gradient-to-r from-amber-400 to-orange-500" style="width: ${scorePercent}%"></div>
            </div>
            <p class="text-xs text-gray-600">${scorePercent >= 80 ? '太棒了！你对核心概念掌握得很扎实' :
              scorePercent >= 60 ? '不错！有一定基础，继续保持' :
              scorePercent >= 40 ? '还有提升空间，建议加强基础知识' :
              '没关系，我们会从基础开始帮你夯实根基'}</p>
        `;
        profileSummary.parentNode.insertBefore(quizSummaryDiv, profileSummary);
    }

    // Calculate and save radar scores for six-dimensional knowledge radar
    const radarScores = calculateRadarScores();
    const radarLabels = ['知识掌握', '实战能力', '学习效率', '内容记忆', '问题解决', '技术深度'];

    // Save radar scores to localStorage
    const user = JSON.parse(localStorage.getItem('starlearn_user') || '{}');
    user.assessment = assessmentData;
    user.learningPath = data.path;
    user.hasCompletedAssessment = true;
    user.radarScores = radarScores;
    user.radarLabels = radarLabels;
    user.quizResults = assessmentData.quizResults;
    user.quizScore = assessmentData.quizScore;
    user.quizTotal = assessmentData.quizTotal;
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
        weakness: analyzeWeakness(),
        focusLevel: profileMap.focusLevel[assessmentData.focusLevel] || '中等专注',
        learningDirection: directionMap[assessmentData.learningDirection] || '大数据技术',
        languages: assessmentData.languages || ['python']
    };

    // Calculate radar scores for profile
    const radarScores = calculateRadarScores();
    profile.radarScores = radarScores;

    user.profile = profile;
    user.learningPath = user.learningPath || [];
    user.hasCompletedAssessment = true;
    user.radarScores = radarScores;
    user.radarLabels = ['知识掌握', '实战能力', '学习效率', '内容记忆', '问题解决', '技术深度'];
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

    // Navigate to hub page
    window.location.href = '/hub.html';
}

// Check if user has already completed assessment
window.addEventListener('load', function() {
    const user = JSON.parse(localStorage.getItem('starlearn_user') || '{}');
    if (user.hasCompletedAssessment) {
        // User already completed assessment, go to main page
        window.location.href = '/index.html';
    }
});
