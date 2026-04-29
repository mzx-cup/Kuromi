const APP_RUNTIME = 'Python 3.11';
const STORAGE_KEY = 'starlearn_unified_coding_state';
const LEGACY_STORAGE_KEY = 'starlearn_coding_state';
const DEFAULT_STUDENT_ID = 'guest';
const DEFAULT_COURSE_ID = 'python-adaptive-lab';

const DEFAULT_MASTERY_MAP = {
    '变量与数据类型': 74,
    '列表List': 68,
    '字典Dict': 61,
    '函数': 65,
    '类与对象': 63,
    '异常处理': 58,
    '排序算法': 53
};

const TOPIC_CHAPTER_MAP = {
    '变量与数据类型': 'ch1',
    '列表List': 'ch2',
    '字典Dict': 'ch2',
    '函数': 'ch3',
    '类与对象': 'ch4',
    '异常处理': 'ch5',
    '排序算法': 'ch7'
};

const CHAPTER_LABELS = {
    ch1: '第 1 章 · 基础语法',
    ch2: '第 2 章 · 容器结构',
    ch3: '第 3 章 · 函数设计',
    ch4: '第 4 章 · 面向对象',
    ch5: '第 5 章 · 异常处理',
    ch6: '第 6 章 · 模块导入',
    ch7: '第 7 章 · 算法训练',
    ch8: '第 8 章 · 数据库基础'
};

const DIFFICULTY_META = {
    easy: { label: '简单' },
    medium: { label: '中等' },
    hard: { label: '挑战' }
};

const MODE_META = {
    fix: {
        label: '代码修改',
        heroStatus: 'AI 诊断开启',
        summary: '系统会根据你的薄弱点推送带错误的 Python 代码。建议先运行观察报错，再逐步修复，最后交给 AI 批阅收口。',
        assistantSubtitle: '逐行诊断 + 修复引导',
        guideLabel: '修复清单',
        quickHintLabel: '修复提示',
        submitLabel: 'AI 批阅'
    },
    complete: {
        label: '补全代码',
        heroStatus: '学习反馈开启',
        summary: '系统会根据你最近的学习表现推送需要补全的模板代码，用来检验知识点是否真正掌握。',
        assistantSubtitle: '思路引导 + TODO 补全',
        guideLabel: '补全建议',
        quickHintLabel: '补全提示',
        submitLabel: '学习评估'
    }
};

const DEFAULT_OUTPUTS = {
    fix: '终端已就绪',
    complete: '终端已就绪'
};

const QUICK_ACTIONS = {
    fix: [
        '先帮我定位最值得检查的 1-2 处代码',
        '给我一个修复方向，但不要直接给完整答案',
        '我改了一版，接下来重点验证什么？'
    ],
    complete: [
        '先提示我应该补哪一段逻辑',
        '帮我梳理这题的边界条件',
        '不要直接给答案，先检查我的思路'
    ]
};

const COMPLETE_TASK_BANK = [
    {
        id: 'complete-two-sum',
        number: 'C01',
        title: '两数之和',
        topic: '列表List',
        chapter: 'ch2',
        difficulty: 'easy',
        tags: ['数组', '哈希表'],
        description: [
            '给定一个整数数组 nums 和一个目标值 target，请在数组中找到和为目标值的两个元素，并返回它们的下标。',
            '这道题主要检验你是否理解“边遍历边记录”的思路，以及如何使用字典保存已经看过的元素。'
        ],
        examples: [
            {
                title: '示例 1',
                input: 'nums = [2, 7, 11, 15], target = 9',
                output: '[0, 1]',
                explanation: '因为 nums[0] + nums[1] = 9，所以返回 [0, 1]。'
            },
            {
                title: '示例 2',
                input: 'nums = [3, 2, 4], target = 6',
                output: '[1, 2]',
                explanation: '遍历到 4 时，字典中已经记录了 2 的下标。'
            }
        ],
        hints: [
            '先计算 current 对应的差值 remain，再看字典里是否已经存过它。',
            '如果差值已出现，直接返回之前记录的下标和当前下标。',
            '遍历完成后如果还没找到，返回空列表即可。'
        ],
        starterCode: `def two_sum(nums, target):
    seen = {}
    for index, num in enumerate(nums):
        remain = target - num
        if __TODO__:
            return [seen[remain], index]
        __TODO__
    return []


print(two_sum([2, 7, 11, 15], 9))`
    },
    {
        id: 'complete-top-word',
        number: 'C02',
        title: '最高频单词统计',
        topic: '字典Dict',
        chapter: 'ch2',
        difficulty: 'medium',
        tags: ['字典', '字符串处理'],
        description: [
            '请补全函数 top_word，统计列表中出现频率最高的单词，并返回 (单词, 次数)。',
            '这道题重点考查字典计数、大小写统一以及如何维护当前最佳结果。'
        ],
        examples: [
            {
                title: '示例 1',
                input: `words = ["Data", "python", "data", "AI", "", "python", "data"]`,
                output: `('data', 3)`,
                explanation: '空字符串需要跳过，统计前要统一成小写。'
            }
        ],
        hints: [
            '字典里已有这个词时加一，否则初始化为 1。',
            'best_word 和 best_count 用来记录当前最优答案。',
            '比较频次时，只需要判断当前 count 是否大于 best_count。'
        ],
        starterCode: `def top_word(words):
    counts = {}
    for word in words:
        normalized = word.strip().lower()
        if not normalized:
            continue
        if __TODO__:
            counts[normalized] += 1
        else:
            __TODO__

    best_word = ""
    best_count = -1
    for word, count in counts.items():
        if __TODO__:
            best_word = word
            best_count = count
    return best_word, best_count


sample = ["Data", "python", "data", "AI", "", "python", "data"]
print(top_word(sample))`
    },
    {
        id: 'complete-score-summary',
        number: 'C03',
        title: '学生成绩汇总',
        topic: '函数',
        chapter: 'ch3',
        difficulty: 'medium',
        tags: ['函数', '聚合统计'],
        description: [
            '给定若干条 (学生名, 分数) 记录，请返回按平均分从高到低排序的结果。',
            '你需要补全平均值计算和最终排序逻辑，检验自己是否掌握了函数拆分与结果组织。'
        ],
        examples: [
            {
                title: '示例 1',
                input: `records = [("Alice", 88), ("Bob", 75), ("Alice", 94), ("Bob", 82)]`,
                output: `[('Alice', 91.0), ('Bob', 78.5)]`,
                explanation: '先把每个学生的成绩聚合到同一个列表，再计算平均值。'
            }
        ],
        hints: [
            'average 应该等于分数和除以数量。',
            '排序时让平均分高的排在前面。',
            '可以直接在 result 上调用 sort。'
        ],
        starterCode: `def summarize_scores(records):
    grouped = {}
    for name, score in records:
        grouped.setdefault(name, []).append(score)

    result = []
    for name, scores in grouped.items():
        average = __TODO__
        result.append((name, round(average, 2)))

    __TODO__
    return result


records = [("Alice", 88), ("Bob", 75), ("Alice", 94), ("Bob", 82)]
print(summarize_scores(records))`
    },
    {
        id: 'complete-merge-intervals',
        number: 'C04',
        title: '区间合并',
        topic: '排序算法',
        chapter: 'ch7',
        difficulty: 'medium',
        tags: ['排序', '区间'],
        description: [
            '请补全 merge_intervals：先按区间起点排序，再把重叠区间合并成一个结果列表。',
            '这道题用来检测你是否真正理解了“排序 + 扫描”的典型算法套路。'
        ],
        examples: [
            {
                title: '示例 1',
                input: '[(1, 3), (2, 4), (8, 10), (9, 12)]',
                output: '[(1, 4), (8, 12)]',
                explanation: '前两个区间重叠，后两个区间也重叠。'
            }
        ],
        hints: [
            '先按照每个区间的 start 进行排序。',
            '若当前区间的 start 小于等于上一个合并区间的 end，则说明重叠。',
            '不重叠时，直接把新区间追加到 merged 中。'
        ],
        starterCode: `def merge_intervals(intervals):
    if not intervals:
        return []

    __TODO__
    merged = [intervals[0]]

    for start, end in intervals[1:]:
        last_start, last_end = merged[-1]
        if __TODO__:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


print(merge_intervals([(1, 3), (2, 4), (8, 10), (9, 12)]))`
    }
];

const FIX_FALLBACK_BANK = [
    {
        id: 'fix-cart-summary',
        number: 'F01',
        title: '购物车汇总修复',
        topic: '字典Dict',
        chapter: 'ch2',
        difficulty: 'easy',
        tags: ['字典', '列表', '函数'],
        errorCount: 5,
        errorType: 'TypeError',
        errorLine: 6,
        description: [
            '这段购物车统计代码包含多处常见错误，覆盖了字段访问、返回值设计和空值判断等问题。',
            '请先运行一次观察第一个报错，再顺着调用链逐步修复。'
        ],
        examples: [
            {
                title: '已知现象',
                content: '第一次运行会很快触发 TypeError，建议优先检查累计变量和循环中的字段访问。'
            },
            {
                title: '调试目标',
                content: '修复后程序应能输出商品名称和最终总价，并通过 AI 批阅。'
            }
        ],
        hints: [
            'total 应该从数字开始累计，而不是字符串。',
            '商品名字段应和样例数据中的键保持一致。',
            'apply_coupon 里要先处理 coupon 为 None 的情况。'
        ],
        starterCode: `def summarize_cart(items):
    total = ""
    names = []

    for item in items:
        total += item["price"] * item["count"]
        names.append(item["title"])

    return total


def apply_coupon(total, coupon):
    if coupon["amount"] > 0:
        return total - coupon["amount"]
    return total


def main():
    cart = [
        {"name": "Keyboard", "price": 199, "count": 2},
        {"name": "Mouse", "price": 89, "count": 1},
    ]
    total, names = summarize_cart(cart)
    coupon = None
    final_total = apply_coupon(total, coupon)
    print("items:", " | ".join(names))
    print("final total:", final_total)


if __name__ == "__main__":
    main()`
    },
    {
        id: 'fix-merge-sort',
        number: 'F02',
        title: '归并排序修复',
        topic: '排序算法',
        chapter: 'ch7',
        difficulty: 'medium',
        tags: ['排序', '递归', '边界'],
        errorCount: 5,
        errorType: 'TypeError',
        errorLine: 7,
        description: [
            '这是一道典型的算法调试题，问题集中在切分边界、指针初始值和循环条件上。',
            '先修掉最早暴露的运行错误，再回头排查后续的逻辑问题。'
        ],
        examples: [
            {
                title: '已知现象',
                content: '第一次运行会在切片阶段报错，说明递归拆分的边界值存在问题。'
            },
            {
                title: '调试目标',
                content: '修复完成后，输出结果应是一个升序数组。'
            }
        ],
        hints: [
            'mid 应该是整数，适合使用整除。',
            '归并双指针通常从 0 开始。',
            'while 条件不要让 i 或 j 越过合法下标。'
        ],
        starterCode: `from typing import List


def merge_sort(arr: List[int]) -> List[int]:
    if len(arr) <= 1:
        return arr

    mid = len(arr) / 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])

    return merge(left, right)


def merge(left: List[int], right: List[int]) -> List[int]:
    result = []
    i = j = 1

    while i <= len(left) and j <= len(right):
        if left[i] < right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1

    result.extend(left[i:])
    result.extend(right[j:])
    return result


print(merge_sort([5, 2, 7, 1, 3]))`
    },
    {
        id: 'fix-attendance-summary',
        number: 'F03',
        title: '签到统计修复',
        topic: '函数',
        chapter: 'ch3',
        difficulty: 'medium',
        tags: ['函数', '统计', '排序'],
        errorCount: 5,
        errorType: 'TypeError',
        errorLine: 8,
        description: [
            '这道题考察函数返回值与数据结构设计是否稳定，问题集中在计数方式和输出结构上。',
            '建议先修复最早出现的类型错误，再检查统计逻辑是否符合题意。'
        ],
        examples: [
            {
                title: '已知现象',
                content: '第一次运行会在签到次数累加时出错，说明计数值的类型设计不正确。'
            },
            {
                title: '调试目标',
                content: '最终程序应能正确打印签到次数最多的学生。'
            }
        ],
        hints: [
            '签到次数应该是整数累计，而不是拼接字符串。',
            '返回值最好保持为稳定、可排序的数据结构。',
            '排序和打印阶段依赖上游返回结构正确。'
        ],
        starterCode: `def build_summary(records):
    summary = {}

    for name, status in records:
        if name not in summary:
            summary[name] = 0
        if status == "present":
            summary[name] = summary[name] + "1"
        else:
            summary[name] -= 1

    return summary.items()


def main():
    records = [("Alice", "present"), ("Bob", "late"), ("Alice", "present")]
    summary = build_summary(records)
    top_name = sorted(summary, key=lambda item: item[1], reverse=True)[0][0]
    print("top student:", top_name)
    print("summary:", dict(summary))


if __name__ == "__main__":
    main()`
    }
];

const state = {
    mode: 'complete',
    studentId: DEFAULT_STUDENT_ID,
    courseId: DEFAULT_COURSE_ID,
    courseName: '代码工坊',
    contextId: '',
    currentTask: null,
    tokenUsage: 0,
    sessionStartedAt: Date.now(),
    taskRequestId: 0,
    assistantRequestId: 0,
    typingTicket: 0,
    progressTimer: null,
    suggestedTaskIds: {
        fix: [],
        complete: []
    },
    busy: {
        task: false,
        run: false,
        submit: false,
        assistant: false
    },
    reviewReports: {},
    gradeReports: {},
    learningState: createDefaultLearningState()
};

const elements = {};

document.addEventListener('DOMContentLoaded', () => {
    cacheElements();
    if (!elements.codeInput) {
        return;
    }

    hydrateSession();
    loadLearningState();
    hydrateModeFromUrl();
    bindEvents();
    renderStaticFrame();
    requestPersonalizedTask({ initial: true });
});

function cacheElements() {
    elements.windowCourseTitle = document.getElementById('window-course-title');
    elements.runtimeChip = document.getElementById('runtime-chip');
    elements.modeButtons = Array.from(document.querySelectorAll('.mode-btn'));
    elements.currentTaskBadge = document.getElementById('current-task-badge');
    elements.modeSummaryText = document.getElementById('mode-summary-text');
    elements.recommendReason = document.getElementById('recommend-reason');
    elements.learningFocus = document.getElementById('learning-focus');
    elements.masteryRate = document.getElementById('mastery-rate');
    elements.masteryProgress = document.getElementById('mastery-progress');
    elements.recommendBtn = document.getElementById('recommend-btn');
    elements.heroModeLabel = document.getElementById('hero-mode-label');
    elements.heroStatus = document.getElementById('hero-status');
    elements.problemName = document.getElementById('problem-name');
    elements.problemSubtitle = document.getElementById('problem-subtitle');
    elements.problemTags = document.getElementById('problem-tags');
    elements.descriptionModeTag = document.getElementById('description-mode-tag');
    elements.problemDescriptionText = document.getElementById('problem-description-text');
    elements.guideLabel = document.getElementById('guide-label');
    elements.problemExamples = document.getElementById('problem-examples');
    elements.problemHints = document.getElementById('problem-hints');
    elements.editorTitle = document.getElementById('editor-title');
    elements.editorContext = document.getElementById('editor-context');
    elements.issueBadge = document.getElementById('issue-badge');
    elements.quickHintBtn = document.getElementById('quick-hint-btn');
    elements.resetBtn = document.getElementById('reset-btn');
    elements.runBtn = document.getElementById('run-btn');
    elements.submitBtn = document.getElementById('submit-btn');
    elements.generationPanel = document.getElementById('generation-panel');
    elements.generationTitle = document.getElementById('generation-title');
    elements.generationCopy = document.getElementById('generation-copy');
    elements.generationProgress = document.getElementById('generation-progress');
    elements.lineNumbers = document.getElementById('line-numbers');
    elements.codeInput = document.getElementById('code-input');
    elements.outputContent = document.getElementById('output-content');
    elements.clearOutput = document.getElementById('clear-output');
    elements.assistantSubtitle = document.getElementById('assistant-subtitle');
    elements.statusBadge = document.getElementById('status-badge');
    elements.statusText = document.getElementById('status-text');
    elements.assistantQuickActions = document.getElementById('assistant-quick-actions');
    elements.messageContainer = document.getElementById('message-container');
    elements.assistantInput = document.getElementById('assistant-input');
    elements.sendBtn = document.getElementById('send-btn');
    elements.terminalState = document.getElementById('terminal-state');
    elements.terminalStateText = elements.terminalState?.querySelector('span:last-child');
    elements.terminalRuntime = document.getElementById('terminal-runtime');
    elements.terminalMode = document.getElementById('terminal-mode');
    elements.terminalToken = document.getElementById('terminal-token');
    elements.terminalCpu = document.getElementById('terminal-cpu');
}

function bindEvents() {
    elements.modeButtons.forEach((button) => {
        button.addEventListener('click', () => {
            const mode = button.dataset.mode === 'complete' ? 'complete' : 'fix';
            switchMode(mode);
        });
    });

    elements.recommendBtn?.addEventListener('click', () => {
        requestPersonalizedTask({ manual: true });
    });

    elements.quickHintBtn?.addEventListener('click', () => {
        requestQuickHint();
    });

    elements.resetBtn?.addEventListener('click', () => {
        resetCurrentCode();
    });

    elements.runBtn?.addEventListener('click', () => {
        handleRun();
    });

    elements.submitBtn?.addEventListener('click', () => {
        handleSubmit();
    });

    elements.clearOutput?.addEventListener('click', () => {
        resetOutput();
    });

    elements.sendBtn?.addEventListener('click', () => {
        handleSend();
    });

    elements.assistantInput?.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' && event.ctrlKey) {
            event.preventDefault();
            handleSend();
        }
    });

    elements.codeInput?.addEventListener('input', () => {
        updateLineNumbers();
        updateIssueBadge();
    });

    elements.codeInput?.addEventListener('scroll', () => {
        syncLineNumberScroll();
    });
}

function hydrateSession() {
    state.contextId = `code-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;

    try {
        const user = JSON.parse(localStorage.getItem('starlearn_user') || 'null');
        state.studentId = user?.username || user?.id || user?.nickname || DEFAULT_STUDENT_ID;
        if (user?.currentTask) {
            state.courseName = user.currentTask;
        }
    } catch (error) {
        state.studentId = DEFAULT_STUDENT_ID;
    }

    const params = new URLSearchParams(window.location.search);
    const courseId = params.get('course_id');
    const courseName = params.get('course_name');

    if (courseId) {
        state.courseId = courseId;
    }

    if (courseName) {
        state.courseName = courseName;
    }
}

function hydrateModeFromUrl() {
    const params = new URLSearchParams(window.location.search);
    const mode = params.get('mode');
    const action = params.get('action');
    const source = params.get('source');

    if (mode === 'complete') {
        state.mode = 'complete';
        return;
    }

    if (mode === 'review' || mode === 'mistake-book' || mode === 'fix' || action === 'review' || source === 'pair') {
        state.mode = 'fix';
    }
}

function renderStaticFrame() {
    renderModeChrome();
    updateLineNumbers();
    setOutput('idle', DEFAULT_OUTPUTS[state.mode]);
    updateAssistantStatus('就绪', 'ready');
    updateTerminalState('idle', '等待推题');
    updateCpuMeter(false);
    updateTokenMeter();

    if (elements.editorTitle) {
        elements.editorTitle.textContent = '当前练习脚本';
    }

    if (elements.editorContext) {
        elements.editorContext.textContent = '系统会根据学习情况推送练习，不再展示固定题库。';
    }

    if (elements.problemName) {
        elements.problemName.textContent = '系统正在准备你的个性化练习';
    }

    if (elements.problemSubtitle) {
        elements.problemSubtitle.textContent = '加载完成后会自动以打字机效果写入代码，再进入运行与诊断流程。';
    }

    if (elements.masteryProgress) {
        elements.masteryProgress.style.width = '0%';
    }

    renderQuickActions();
}

function renderModeChrome() {
    const meta = MODE_META[state.mode];

    elements.modeButtons.forEach((button) => {
        const active = button.dataset.mode === state.mode;
        button.classList.toggle('active', active);
    });

    if (elements.currentTaskBadge) {
        elements.currentTaskBadge.textContent = meta.label;
    }

    if (elements.modeSummaryText) {
        elements.modeSummaryText.textContent = meta.summary;
    }

    if (elements.heroModeLabel) {
        elements.heroModeLabel.textContent = meta.label;
    }

    if (elements.heroStatus) {
        elements.heroStatus.textContent = meta.heroStatus;
    }

    if (elements.descriptionModeTag) {
        elements.descriptionModeTag.textContent = meta.label;
    }

    if (elements.guideLabel) {
        elements.guideLabel.textContent = meta.guideLabel;
    }

    if (elements.assistantSubtitle) {
        elements.assistantSubtitle.textContent = meta.assistantSubtitle;
    }

    if (elements.quickHintBtn) {
        elements.quickHintBtn.textContent = meta.quickHintLabel;
    }

    if (elements.submitBtn) {
        elements.submitBtn.textContent = meta.submitLabel;
    }

    if (elements.terminalMode) {
        elements.terminalMode.textContent = `模式: ${meta.label}`;
    }

    if (elements.runtimeChip) {
        elements.runtimeChip.textContent = APP_RUNTIME;
    }

    if (elements.terminalRuntime) {
        elements.terminalRuntime.textContent = APP_RUNTIME;
    }
}

async function switchMode(mode) {
    if (mode === state.mode) {
        return;
    }

    state.mode = mode === 'complete' ? 'complete' : 'fix';
    syncModeToUrl();
    renderModeChrome();
    renderQuickActions();
    await requestPersonalizedTask({ manual: true });
}

async function requestPersonalizedTask(options = {}) {
    const requestId = ++state.taskRequestId;
    state.assistantRequestId += 1;
    cancelTypingAnimation();
    stopGenerationProgress();
    updateGenerationStreamPreview.buffer = '';
    appendStreamingCodeToEditor.started = false;
    setBusy('assistant', false);
    setBusy('task', true);
    showGenerationOverlay();
    clearMessages();
    updateAssistantStatus('生成中...', 'busy');
    updateTerminalState('loading', '任务准备中');
    updateCpuMeter(true);
    setOutput('loading', state.mode === 'fix' ? '正在根据你的学情生成调试题...' : '正在根据你的学情推送补全题...');

    const finishProgress = startGenerationProgress();
    showTypingOverlay();
    const streamsCodeDirectly = state.mode === 'fix';
    if (streamsCodeDirectly && elements.codeInput) {
        elements.codeInput.value = '';
        updateLineNumbers();
        syncLineNumberScroll();
    }
    const warmupTyping = streamsCodeDirectly
        ? Promise.resolve(false)
        : typeCodeToEditor(buildGenerationWarmupCode(), { live: true }).catch(() => false);

    try {
        const task = await buildPersonalizedTask(state.mode);
        if (requestId !== state.taskRequestId) {
            return;
        }

        state.currentTask = task;
        renderTask(task);
        void warmupTyping;
        showTypingOverlay();

        let typed = true;
        if (task.streamedToEditor) {
            const finalCode = task.starterCode || task.originalCode || '';
            if (elements.codeInput && finalCode && elements.codeInput.value !== finalCode) {
                elements.codeInput.value = finalCode;
                updateLineNumbers();
                elements.codeInput.scrollTop = elements.codeInput.scrollHeight;
                syncLineNumberScroll();
            }
        } else {
            typed = await typeCodeToEditor(task.starterCode || task.originalCode || '', { live: true });
        }
        if (!typed || requestId !== state.taskRequestId) {
            return;
        }

        await finishProgress();
        hideGenerationOverlay();
        resetOutput();
        seedAssistantConversation(task, options.initial === true);
        updateIssueBadge();
        updateAssistantStatus('就绪', 'ready');
        updateTerminalState('success', '任务已就绪');
        updateCpuMeter(false);
    } catch (error) {
        if (requestId !== state.taskRequestId) {
            return;
        }

        stopGenerationProgress();
        cancelTypingAnimation();
        hideGenerationOverlay();
        setOutput('error', `练习任务准备失败：${error.message}`);
        updateAssistantStatus('服务异常', 'error');
        updateTerminalState('error', '任务加载失败');
        addMessage('ai', `抱歉，这次推题没有成功：${error.message}`, { label: '系统提示' });
    } finally {
        if (requestId === state.taskRequestId) {
            setBusy('task', false);
        }
    }
}

async function buildPersonalizedTask(mode) {
    const context = buildLearningContext(mode);

    if (mode === 'fix') {
        const task = await generateFixTask(context);
        pushSuggestedTaskId('fix', task.id);
        return task;
    }

    const task = buildCompletionTask(context);
    pushSuggestedTaskId('complete', task.id);
    return task;
}

function buildLearningContext(mode) {
    const weakTopics = deriveWeakTopics(state.learningState.masteryByTopic);
    const supportedWeakTopics = weakTopics.filter((topic) => {
        if (mode === 'fix') {
            return Boolean(TOPIC_CHAPTER_MAP[topic]);
        }
        return COMPLETE_TASK_BANK.some((task) => task.topic === topic);
    });

    const fallbackTopic = mode === 'fix' ? '函数' : '列表List';
    const focusTopic = supportedWeakTopics[0] || fallbackTopic;
    const mastery = getTopicMastery(focusTopic);
    const chapter = TOPIC_CHAPTER_MAP[focusTopic] || 'ch2';
    const difficulty = chooseDifficulty(mastery, mode);
    const recentHistory = state.learningState.learningHistory.slice(-10);
    const recentFailures = recentHistory.filter((item) => item.topic === focusTopic && item.passed === false).length;

    return {
        mode,
        focusTopic,
        mastery,
        chapter,
        difficulty,
        weakTopics,
        recentHistory,
        recentFailures
    };
}

async function generateFixTask(context) {
    const payload = buildProblemGenerationPayload(context);
    try {
        const streamResult = await fetchSseStream('/api/v2/coding-problem/generate/stream', payload, {
            onStatus: (data) => {
                appendTerminalLine(`[System] ${data.msg} _`, 'system');
                scrollOutputToBottom();
            },
            onCodeStart: () => {
                appendStreamingCodeToEditor('', { reset: true });
                updateGenerationStreamPreview.buffer = '';
            },
            onCodeChunk: (data) => {
                appendStreamingCodeToEditor(data.chunk || '');
                updateGenerationStreamPreview(data.chunk || '');
            },
            onCodeComplete: (data) => {
                appendTerminalLine(`[System] ${data.msg || '初始代码生成完成'} _`, 'success');
                scrollOutputToBottom();
            }
        });

        if (!streamResult?.success || !extractProblemStarterCode(streamResult.problem)) {
            throw new Error(streamResult?.error || '流式接口没有返回有效代码');
        }

        const task = normalizeGeneratedFixProblem(streamResult.problem, context);
        task.streamedToEditor = Boolean(appendStreamingCodeToEditor.started);
        return task;
    } catch (error) {
        return buildFallbackFixTask(context, error);
    }
}

function buildProblemGenerationPayload(context) {
    return {
        student_id: state.studentId,
        course_id: state.courseId,
        chapter: context.chapter,
        topic: context.focusTopic,
        difficulty: context.difficulty,
        weak_topics: context.weakTopics,
        learning_history: context.recentHistory.map((item) => ({
            problem_id: item.id,
            topic: item.topic,
            chapter: item.chapter,
            passed: item.passed,
            timestamp: item.timestamp
        })),
        current_mastery: context.mastery
    };
}

function normalizeGeneratedFixProblem(problem, context) {
    const taskInfo = problem.task_info || {};
    const uiHints = problem.ui_hints || {};
    const code = removeSpoilerComments(stripCodeFences(extractProblemStarterCode(problem)));
    const solutionCode = stripCodeFences(problem.solution_code || problem.solutionCode || '');
    const difficulty = problem.difficulty || context.difficulty;
    const focusTopic = problem.topic || context.focusTopic;
    const mastery = getTopicMastery(focusTopic);
    const errorCount = Array.isArray(problem.allErrors) && problem.allErrors.length
        ? problem.allErrors.length
        : estimateIssueCountFromHints(uiHints, problem);
    const reason = buildRecommendationReason({
        ...context,
        focusTopic,
        mastery
    }, 'fix');

    return {
        mode: 'fix',
        source: 'ai',
        id: `fix-${String(problem.id || Date.now())}`,
        number: formatNumber(problem.id, 'F'),
        title: taskInfo.title || problem.title || '个性化调试任务',
        topic: focusTopic,
        chapter: problem.chapter || context.chapter,
        chapterLabel: CHAPTER_LABELS[problem.chapter || context.chapter] || '学情推送',
        difficulty,
        difficultyLabel: DIFFICULTY_META[difficulty]?.label || '中等',
        tags: uniqueStrings([focusTopic, problem.errorType, 'Python']),
        subtitle: `系统根据你在「${focusTopic}」上的表现即时生成了一道调试题。先运行观察报错，再逐步修复。`,
        description: [
            taskInfo.description || `这道题聚焦「${focusTopic}」，代码中预计包含 ${errorCount} 处隐蔽错误。请先运行代码，结合终端报错逐步排查。`,
            '初始代码不会在注释中标出错误位置，真实定位需要依赖运行结果、调用链和变量状态。',
            '当代码能跑通后，再点击「AI 批阅」确认是否已经全部修复。'
        ],
        examples: [
            {
                title: '已知现象',
                content: uiHints.known_issue || `第一次运行通常会在第 ${problem.errorLine || '?'} 行附近触发 ${problem.errorType || '运行错误'}。`
            },
            {
                title: '报错线索',
                content: uiHints.error_clue || (problem.errorMsg ? `接口预估的报错信息：${problem.errorMsg}` : '请先以真实运行结果为准，从堆栈最靠近你代码的位置开始排查。')
            }
        ],
        hints: [
            '优先看 traceback 最靠下、最贴近你代码文件的那一行。',
            '每修完一处就重新运行一次，避免多个问题叠加在一起。',
            '能跑通不代表全部正确，最后一定要再过一遍 AI 批阅。'
        ],
        starterCode: code,
        originalCode: code,
        solutionCode,
        learningFocus: focusTopic,
        recommendationReason: reason,
        mastery,
        errorCount
    };
}

function buildFallbackFixTask(context, originalError) {
    const preferred = FIX_FALLBACK_BANK.find((item) => item.topic === context.focusTopic);
    const fallback = preferred || FIX_FALLBACK_BANK[0];
    const mastery = getTopicMastery(fallback.topic);
    const reason = buildRecommendationReason({
        ...context,
        focusTopic: fallback.topic,
        mastery
    }, 'fix');

    return {
        ...fallback,
        mode: 'fix',
        source: 'fallback',
        chapterLabel: CHAPTER_LABELS[fallback.chapter] || fallback.chapter,
        difficultyLabel: DIFFICULTY_META[fallback.difficulty]?.label || '中等',
        subtitle: originalError
            ? `实时生成暂时不可用，已为你切换到同知识点的回退调试题。当前仍聚焦「${fallback.topic}」。`
            : `这是一道围绕「${fallback.topic}」的代码修改题，请先运行再修复。`,
        starterCode: removeSpoilerComments(fallback.starterCode),
        originalCode: removeSpoilerComments(fallback.starterCode),
        learningFocus: fallback.topic,
        recommendationReason: `${reason} 实时生成未成功，因此先用一题同主题调试题保持训练连续性。`,
        mastery
    };
}

function buildCompletionTask(context) {
    const template = chooseCompletionTemplate(context);
    const mastery = getTopicMastery(template.topic);
    const reason = buildRecommendationReason({
        ...context,
        focusTopic: template.topic,
        mastery
    }, 'complete');

    return {
        mode: 'complete',
        source: 'bank',
        id: template.id,
        baseId: template.id,
        number: template.number,
        title: template.title,
        topic: template.topic,
        chapter: template.chapter,
        chapterLabel: CHAPTER_LABELS[template.chapter] || template.chapter,
        difficulty: template.difficulty,
        difficultyLabel: DIFFICULTY_META[template.difficulty]?.label || '中等',
        tags: uniqueStrings(template.tags),
        subtitle: `系统根据你在「${template.topic}」上的学习表现推送了这道补全题，用来检验是否真正掌握。`,
        description: [
            `当前聚焦「${template.topic}」，掌握度约 ${mastery}% 。这道题不会再展示固定题库，而是根据你的学习情况动态推送。`,
            ...template.description,
            '请补完代码中的 __TODO__ 占位，再运行样例验证，最后提交学习评估。'
        ],
        examples: template.examples.map((item) => ({ ...item })),
        hints: template.hints.slice(),
        starterCode: template.starterCode,
        originalCode: template.starterCode,
        learningFocus: template.topic,
        recommendationReason: reason,
        mastery,
        todoCount: countTodoSlots(template.starterCode)
    };
}

function chooseCompletionTemplate(context) {
    const recentSuggestions = state.suggestedTaskIds.complete.slice(-3);

    return COMPLETE_TASK_BANK
        .map((task) => ({
            task,
            score: scoreCompletionTemplate(task, context, recentSuggestions)
        }))
        .sort((left, right) => right.score - left.score)[0]
        .task;
}

function scoreCompletionTemplate(task, context, recentSuggestions) {
    let score = 0;

    if (task.topic === context.focusTopic) {
        score += 40;
    }

    score += 100 - getTopicMastery(task.topic);

    if (task.chapter === context.chapter) {
        score += 10;
    }

    if (recentSuggestions.includes(task.id)) {
        score -= 20;
    }

    if (state.currentTask?.id === task.id) {
        score -= 12;
    }

    score += Math.random() * 8;
    return score;
}

function buildRecommendationReason(context, kind) {
    if (context.recentFailures >= 2) {
        return `你在「${context.focusTopic}」上最近连续 ${context.recentFailures} 次还有卡点，因此系统继续安排同主题训练。`;
    }

    if (context.mastery < 60) {
        return `「${context.focusTopic}」当前掌握度约 ${context.mastery}% ，系统优先安排巩固。`;
    }

    if (kind === 'fix') {
        return `「${context.focusTopic}」已经进入“能写出雏形但容易漏错”的阶段，适合通过调试题查缺补漏。`;
    }

    return `基于最近完成情况，系统安排一道「${context.focusTopic}」补全题来检验学习效果。`;
}

function renderTask(task) {
    renderModeChrome();

    if (elements.windowCourseTitle) {
        elements.windowCourseTitle.textContent = buildWindowTitle(task);
    }

    if (elements.recommendReason) {
        elements.recommendReason.textContent = task.recommendationReason;
    }

    if (elements.learningFocus) {
        elements.learningFocus.textContent = task.learningFocus;
    }

    if (elements.masteryRate) {
        elements.masteryRate.textContent = `${task.mastery}%`;
    }

    if (elements.masteryProgress) {
        elements.masteryProgress.style.width = `${task.mastery}%`;
    }

    if (elements.heroStatus) {
        elements.heroStatus.textContent = task.source === 'fallback' ? '回退题已启用' : MODE_META[state.mode].heroStatus;
    }

    if (elements.problemName) {
        elements.problemName.textContent = `#${task.number} ${task.title}`;
    }

    if (elements.problemSubtitle) {
        elements.problemSubtitle.textContent = task.subtitle;
    }

    if (elements.problemTags) {
        elements.problemTags.innerHTML = renderTagList(task);
    }

    if (elements.problemDescriptionText) {
        elements.problemDescriptionText.innerHTML = task.description
            .map((paragraph) => `<p>${escapeHtml(paragraph)}</p>`)
            .join('');
    }

    if (elements.problemExamples) {
        elements.problemExamples.innerHTML = task.examples
            .map((example, index) => renderExampleCard(example, index === 0))
            .join('');
    }

    if (elements.problemHints) {
        elements.problemHints.innerHTML = task.hints
            .map((hint) => `<li>${escapeHtml(hint)}</li>`)
            .join('');
    }

    if (elements.editorTitle) {
        elements.editorTitle.textContent = '当前练习脚本';
    }

    if (elements.editorContext) {
        elements.editorContext.textContent = `${buildSourceLabel(task)} · ${task.chapterLabel} · ${task.learningFocus}`;
    }

    document.title = `${task.title} - 代码工坊`;
    updateIssueBadge();
}

function buildWindowTitle(task) {
    if (state.courseName && state.courseName !== '代码工坊') {
        return `${state.courseName} · ${task.learningFocus}`;
    }
    return `学情推送 · ${task.learningFocus}`;
}

function renderTagList(task) {
    const tags = [
        { text: MODE_META[task.mode].label, className: '' },
        { text: task.difficultyLabel, className: task.difficulty },
        ...task.tags.map((tag) => ({ text: tag, className: '' })),
        { text: task.source === 'ai' ? 'AI 推题' : (task.source === 'fallback' ? '回退题' : '学情模板'), className: '' }
    ];

    const uniqueTags = [];
    const seen = new Set();

    tags.forEach((tag) => {
        if (!tag.text || seen.has(tag.text)) {
            return;
        }
        seen.add(tag.text);
        uniqueTags.push(tag);
    });

    return uniqueTags
        .map((tag) => `<span class="tag ${escapeHtml(tag.className || '')}">${escapeHtml(tag.text)}</span>`)
        .join('');
}

function renderExampleCard(example, highlight) {
    const lines = [];

    if (example.content) {
        lines.push(example.content);
    }
    if (example.input) {
        lines.push(`输入: ${example.input}`);
    }
    if (example.output) {
        lines.push(`输出: ${example.output}`);
    }
    if (example.explanation) {
        lines.push(`说明: ${example.explanation}`);
    }

    return `
        <article class="example-card ${highlight ? 'highlight' : ''}">
            <span class="example-title">${escapeHtml(example.title || '示例')}</span>
            <pre><code>${escapeHtml(lines.join('\n'))}</code></pre>
        </article>
    `;
}

function showGenerationOverlay() {
    if (!elements.generationPanel) {
        return;
    }

    const meta = MODE_META[state.mode];
    elements.generationPanel.classList.remove('compact');
    elements.generationPanel.hidden = false;
    elements.generationTitle.textContent = state.mode === 'fix'
        ? '正在生成个性化代码修改任务'
        : '正在推送个性化补全代码任务';
    elements.generationCopy.textContent = state.mode === 'fix'
        ? '系统会结合你的薄弱知识点生成带错误的代码，并在写入编辑器时展示打字机效果。'
        : '系统会根据你最近的学习表现推送补全模板，并在写入编辑器时展示打字机效果。';
    elements.generationProgress.style.width = '8%';
    if (elements.statusText) {
        elements.statusText.textContent = '生成中...';
    }
    if (elements.assistantSubtitle) {
        elements.assistantSubtitle.textContent = meta.assistantSubtitle;
    }
}

function showTypingOverlay() {
    if (!elements.generationPanel) {
        return;
    }

    if (state.mode === 'fix') {
        elements.generationPanel.classList.remove('compact');
        elements.generationPanel.hidden = true;
        return;
    }

    elements.generationPanel.hidden = false;
    elements.generationPanel.classList.add('compact');
    elements.generationTitle.textContent = state.mode === 'fix'
        ? 'AI 正在边想边写入修改代码'
        : 'AI 正在边想边写入补全代码';
    elements.generationCopy.textContent = '代码会像打字一样逐步出现在编辑器里，你可以先观察结构，不用等待整段生成完成。';
}

function buildGenerationWarmupCode() {
    const focusTopic = state.learningState.weakTopics?.[0] || (state.mode === 'fix' ? '函数' : '列表List');
    const modeLabel = MODE_META[state.mode]?.label || '代码练习';

    return [
        '# AI 正在根据你的学情生成代码任务...',
        `# 练习模式: ${modeLabel}`,
        `# 重点知识点: ${focusTopic}`,
        '# 代码会逐行写入编辑器，请先观察整体结构和 TODO/错误标记。',
        ''
    ].join('\n');
}

function hideGenerationOverlay() {
    if (!elements.generationPanel) {
        return;
    }
    elements.generationPanel.classList.remove('compact');
    elements.generationPanel.hidden = true;
}

function startGenerationProgress() {
    stopGenerationProgress();

    let progress = 8;
    if (elements.generationProgress) {
        elements.generationProgress.style.width = `${progress}%`;
    }

    state.progressTimer = window.setInterval(() => {
        progress = Math.min(progress + 7 + Math.random() * 10, 90);
        if (elements.generationProgress) {
            elements.generationProgress.style.width = `${progress}%`;
        }
    }, 160);

    return async function finishProgress() {
        stopGenerationProgress();
        if (elements.generationProgress) {
            elements.generationProgress.style.width = '100%';
        }
        await sleep(180);
    };
}

function stopGenerationProgress() {
    if (state.progressTimer) {
        window.clearInterval(state.progressTimer);
        state.progressTimer = null;
    }
}

function cancelTypingAnimation() {
    state.typingTicket += 1;
}

async function typeCodeToEditor(code, options = {}) {
    const ticket = ++state.typingTicket;
    const editor = elements.codeInput;
    if (!editor) {
        return false;
    }

    editor.value = '';
    updateLineNumbers();
    syncLineNumberScroll();

    if (!code) {
        return true;
    }

    const chunkSize = options.live ? 3 : code.length > 1800 ? 18 : code.length > 900 ? 12 : 8;

    for (let index = 0; index < code.length; ) {
        if (ticket !== state.typingTicket) {
            return false;
        }

        const currentChar = code[index];
        const size = currentChar === '\n' ? 1 : chunkSize + Math.floor(Math.random() * 3);
        const nextIndex = Math.min(code.length, index + size);
        editor.value += code.slice(index, nextIndex);
        index = nextIndex;
        updateLineNumbers();
        editor.scrollTop = editor.scrollHeight;
        syncLineNumberScroll();

        const delay = editor.value.endsWith('\n') ? 18 : (options.live ? 0 : 4);
        if (delay > 0) {
            await sleep(delay);
        } else {
            await new Promise((resolve) => window.requestAnimationFrame(resolve));
        }
    }

    return ticket === state.typingTicket;
}

function updateLineNumbers() {
    if (!elements.lineNumbers || !elements.codeInput) {
        return;
    }

    const lineCount = Math.max(1, elements.codeInput.value.split('\n').length);
    const numbers = Array.from({ length: lineCount }, (_, index) => `<span>${index + 1}</span>`).join('');
    elements.lineNumbers.innerHTML = numbers;
}

function syncLineNumberScroll() {
    if (!elements.lineNumbers || !elements.codeInput) {
        return;
    }
    elements.lineNumbers.style.transform = `translateY(${-elements.codeInput.scrollTop}px)`;
}

function setBusy(key, value) {
    state.busy[key] = value;
    syncBusyState();
}

function syncBusyState() {
    const taskBusy = state.busy.task;
    const runBusy = state.busy.run;
    const submitBusy = state.busy.submit;
    const assistantBusy = state.busy.assistant;

    if (elements.recommendBtn) {
        elements.recommendBtn.disabled = taskBusy;
    }

    if (elements.quickHintBtn) {
        elements.quickHintBtn.disabled = taskBusy || assistantBusy;
    }

    if (elements.resetBtn) {
        elements.resetBtn.disabled = taskBusy || runBusy || submitBusy;
    }

    if (elements.runBtn) {
        elements.runBtn.disabled = taskBusy || runBusy || submitBusy;
    }

    if (elements.submitBtn) {
        elements.submitBtn.disabled = taskBusy || runBusy || submitBusy;
    }

    if (elements.sendBtn) {
        elements.sendBtn.disabled = taskBusy || assistantBusy;
    }

    if (elements.assistantInput) {
        elements.assistantInput.disabled = taskBusy || assistantBusy;
    }
}

async function handleRun() {
    if (!state.currentTask || state.busy.task || state.busy.run || state.busy.submit) {
        return;
    }

    const code = elements.codeInput?.value || '';
    if (!code.trim()) {
        setOutput('error', '编辑器为空，无法运行。');
        return;
    }

    const remainingTodo = state.mode === 'complete' ? countTodoSlots(code) : 0;
    if (remainingTodo > 0) {
        setOutput('error', `当前还有 ${remainingTodo} 处 __TODO__ 未补全，请先完成后再运行。`);
        updateTerminalState('error', 'TODO 未完成');
        return;
    }

    setBusy('run', true);
    updateAssistantStatus('运行中...', 'busy');
    updateTerminalState('loading', '运行中');
    updateCpuMeter(true);
    setOutput('loading', '正在运行代码...');

    try {
        const result = await runPythonCode(code);
        const success = Number(result.returncode) === 0;
        renderExecutionOutput(result);
        updateTerminalState(success ? 'success' : 'error', success ? '运行完成' : '运行报错');
        addRunGuidance(result, state.currentTask);
    } catch (error) {
        setOutput('error', `运行失败：${error.message}`);
        updateTerminalState('error', '运行失败');
        addMessage('ai', `运行服务暂时不可用：${error.message}`, { label: '系统提示' });
    } finally {
        setBusy('run', false);
        updateAssistantStatus('就绪', 'ready');
        updateCpuMeter(false);
    }
}

async function handleSubmit() {
    if (!state.currentTask || state.busy.task || state.busy.run || state.busy.submit) {
        return;
    }

    if (state.mode === 'fix') {
        await submitFixReview();
        return;
    }

    await submitCompletionEvaluation();
}

async function submitFixReview() {
    const task = state.currentTask;
    const code = elements.codeInput?.value || '';

    if (!code.trim()) {
        setOutput('error', '请先修改代码后再提交 AI 批阅。');
        return;
    }

    setBusy('submit', true);
    updateAssistantStatus('批阅中...', 'busy');
    updateTerminalState('loading', 'AI 批阅中');
    updateCpuMeter(true);
    setOutput('loading', '[System] 正在提交 AI 批阅 _');

    try {
        const result = await fetchSseStream('/api/v2/code/review/stream', {
            student_id: state.studentId,
            original_code: task.originalCode || '',
            solution_code: task.solutionCode || '',
            user_code: code,
            problem_id: task.id,
            topic: task.topic || task.learningFocus,
            difficulty: task.difficulty || 'medium'
        }, {
            onStatus: (data) => {
                appendTerminalLine(`[System] ${data.msg} _`, 'system');
                scrollOutputToBottom();
            }
        });

        if (!result?.success || !result.report) {
            throw new Error(result?.error || '流式批阅没有返回有效报告');
        }

        const report = result.report;
        const passed = Boolean(report.summary?.passed);
        state.reviewReports[task.id] = report;
        recordPracticeResult(task, passed, { report });
        renderReviewReport(report, task);
        setOutput(passed ? 'success' : 'error', buildReviewSummaryText(report, task));
        updateIssueBadge();
        refreshMasteryCard(task.learningFocus);
        updateTerminalState(passed ? 'success' : 'error', passed ? '修复完成' : '仍有遗漏');
        accumulateTokenUsage(JSON.stringify(report).length);

        // 更新学生画像
        StarData.updatePortrait('code', {
            task_id: task.id,
            topic: task.learningFocus || task.topic,
            mode: 'fix',
            passed: passed,
            score: report.summary?.score || 0,
            wrong_count: report.summary?.wrong_count || 0
        });
    } catch (error) {
        setOutput('error', `AI 批阅失败：${error.message}`);
        updateTerminalState('error', '批阅失败');
        updateAssistantStatus('服务异常', 'error');
        addMessage('ai', `这次批阅没有成功：${error.message}`, { label: 'AI 批阅' });
    } finally {
        setBusy('submit', false);
        updateAssistantStatus('就绪', 'ready');
        updateCpuMeter(false);
    }
}

async function submitCompletionEvaluation() {
    const task = state.currentTask;
    const code = elements.codeInput?.value || '';
    const remainingTodo = countTodoSlots(code);

    if (!code.trim()) {
        setOutput('error', '请先补全代码后再提交学习评估。');
        return;
    }

    if (remainingTodo > 0) {
        setOutput('error', `当前还有 ${remainingTodo} 处 __TODO__ 未补全，请先完成后再提交。`);
        updateTerminalState('error', 'TODO 未完成');
        return;
    }

    setBusy('submit', true);
    updateAssistantStatus('评估中...', 'busy');
    updateTerminalState('loading', '学习评估中');
    updateCpuMeter(true);
    setOutput('loading', '正在校验代码并提交学习评估...');

    try {
        const runResult = await runPythonCode(code);
        if (Number(runResult.returncode) !== 0) {
            renderExecutionOutput(runResult);
            updateTerminalState('error', '代码未通过运行');
            addMessage('ai', '我先帮你跑了一次，这份代码还有运行错误。先把报错处理掉，再做学习评估。', { label: 'AI 导师' });
            return;
        }

        const response = await fetch('/api/grade-code', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                code,
                task: buildCompletionTaskPrompt(task),
                language: 'python',
                currentProfile: buildProfilePayload()
            })
        });

        const report = await response.json();
        if (!response.ok) {
            throw new Error(`接口返回 ${response.status}`);
        }

        const score = Number(report.score) || 0;
        const passed = score >= 75;
        state.gradeReports[task.id] = report;
        recordPracticeResult(task, passed, { score });
        renderCompletionReport(report, task);
        setOutput(passed ? 'success' : 'error', buildCompletionSummaryText(report, task));
        updateIssueBadge();
        refreshMasteryCard(task.learningFocus);
        updateTerminalState(passed ? 'success' : 'error', passed ? '评估达标' : '建议继续巩固');
        accumulateTokenUsage(JSON.stringify(report).length);

        // 更新学生画像
        StarData.updatePortrait('code', {
            task_id: task.id,
            topic: task.learningFocus || task.topic,
            mode: 'complete',
            passed: passed,
            score: score
        });
    } catch (error) {
        setOutput('error', `学习评估失败：${error.message}`);
        updateTerminalState('error', '评估失败');
        updateAssistantStatus('服务异常', 'error');
        addMessage('ai', `这次学习评估没有成功：${error.message}`, { label: '学习评估' });
    } finally {
        setBusy('submit', false);
        updateAssistantStatus('就绪', 'ready');
        updateCpuMeter(false);
    }
}

async function resetCurrentCode() {
    if (!state.currentTask || state.busy.task || state.busy.run || state.busy.submit) {
        return;
    }

    const code = state.currentTask.originalCode || state.currentTask.starterCode || '';
    updateTerminalState('idle', '重置代码');
    setOutput('idle', '已恢复为系统推送的起始代码。');
    await typeCodeToEditor(code);
    updateIssueBadge();
}

function requestQuickHint() {
    if (!state.currentTask || state.busy.task || state.busy.assistant) {
        return;
    }

    const prompt = state.mode === 'fix'
        ? '请先帮我定位这份代码里最值得优先检查的 1-2 处位置，不要直接给完整修正版。'
        : '请先告诉我这题应该优先补哪一段逻辑，不要直接给完整答案。';

    sendAssistantMessage(prompt);
}

function seedAssistantConversation(task, isInitial) {
    clearMessages();
    renderQuickActions();

    const intro = state.mode === 'fix'
        ? [
            `你好，我会陪你一起排查这道「${task.title}」。`,
            `这次推题聚焦「${task.learningFocus}」，原因是：${task.recommendationReason}`,
            `建议顺序：先运行看报错，再修复，再点「AI 批阅」确认是否还有遗漏。`
        ].join('\n\n')
        : [
            `你好，这次我们一起完成「${task.title}」的代码补全。`,
            `这次推题聚焦「${task.learningFocus}」，原因是：${task.recommendationReason}`,
            '建议顺序：先补完 __TODO__，再运行验证，最后点「学习评估」查看效果。'
        ].join('\n\n');

    addMessage('ai', intro, { label: isInitial ? 'AI 导师' : '系统提示' });

    if (state.mode === 'fix' && state.reviewReports[task.id]) {
        renderReviewReport(state.reviewReports[task.id], task, '上次批阅记录');
    }

    if (state.mode === 'complete' && state.gradeReports[task.id]) {
        renderCompletionReport(state.gradeReports[task.id], task, '上次学习评估');
    }
}

function renderQuickActions() {
    if (!elements.assistantQuickActions) {
        return;
    }

    elements.assistantQuickActions.innerHTML = QUICK_ACTIONS[state.mode]
        .map((text) => `<button class="assistant-chip" type="button">${escapeHtml(text)}</button>`)
        .join('');

    Array.from(elements.assistantQuickActions.querySelectorAll('.assistant-chip')).forEach((button) => {
        button.addEventListener('click', () => {
            if (state.busy.task || state.busy.assistant) {
                return;
            }
            sendAssistantMessage(button.textContent?.trim() || '');
        });
    });
}

async function handleSend() {
    if (!elements.assistantInput || state.busy.task || state.busy.assistant) {
        return;
    }

    const message = elements.assistantInput.value.trim();
    if (!message) {
        return;
    }

    await sendAssistantMessage(message);
}

async function sendAssistantMessage(message) {
    if (!state.currentTask || !message.trim()) {
        return;
    }

    addMessage('user', message, { label: '我' });
    if (elements.assistantInput) {
        elements.assistantInput.value = '';
    }

    try {
        await callAI(message);
    } catch (error) {
        updateAssistantStatus('服务异常', 'error');
        addMessage('ai', `抱歉，AI 助手暂时不可用：${error.message}`, { label: 'AI 导师' });
    }
}

async function callAI(userMessage) {
    const task = state.currentTask;
    if (!task) {
        return;
    }

    const requestId = ++state.assistantRequestId;
    setBusy('assistant', true);
    updateAssistantStatus('思考中...', 'busy');
    updateTerminalState('loading', 'AI 思考中');
    updateCpuMeter(true);

    const payload = {
        student_id: state.studentId,
        course_id: state.courseId,
        user_input: buildAssistantPrompt(userMessage),
        context_id: state.contextId,
        current_profile: buildProfilePayload(),
        current_path: buildLearningPath(),
        interaction_count: Number(state.learningState.interactionCount) || 0,
        code_practice_time: getPracticeMinutes(),
        socratic_pass_rate: Number(state.learningState.socraticPassRate) || 0.72
    };
    let reader = null;

    try {
        const response = await fetch('/api/v2/chat/stream', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error(`接口返回 ${response.status}`);
        }

        if (!response.body) {
            throw new Error('未获取到流式响应');
        }

        const streaming = createStreamingMessage('AI 导师');
        reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let fullText = '';

        while (true) {
            if (requestId !== state.assistantRequestId) {
                return;
            }

            const { done, value } = await reader.read();
            if (done) {
                break;
            }

            buffer += decoder.decode(value, { stream: true });
            const chunks = buffer.split('\n\n');
            buffer = chunks.pop() || '';

            for (const chunk of chunks) {
                const lines = chunk.split('\n').map((line) => line.trim()).filter(Boolean);
                for (const line of lines) {
                    if (!line.startsWith('data:')) {
                        continue;
                    }

                    const raw = line.slice(5).trim();
                    if (!raw) {
                        continue;
                    }

                    let event;
                    try {
                        event = JSON.parse(raw);
                    } catch (error) {
                        continue;
                    }

                    if (event.type === 'content_chunk' || event.type === 'text') {
                        fullText += event.content || '';
                        streaming.content.innerHTML = `${formatPlainText(fullText)}<span class="typing-cursor"></span>`;
                        scrollMessagesToBottom();
                    } else if (event.type === 'complete') {
                        state.contextId = event.data?.contextId || state.contextId;
                    } else if (event.type === 'error') {
                        throw new Error(event.message || 'AI 返回异常');
                    }
                }
            }
        }

        if (requestId !== state.assistantRequestId) {
            return;
        }

        const finalText = fullText.trim() || 'AI 已收到你的问题，但这次没有返回有效内容。';
        streaming.content.innerHTML = formatPlainText(finalText);
        accumulateTokenUsage(finalText.length);
        state.learningState.interactionCount = (Number(state.learningState.interactionCount) || 0) + 1;
        saveLearningState();
        updateTerminalState('success', 'AI 已回复');
        scrollMessagesToBottom();
    } finally {
        reader?.releaseLock?.();
        if (requestId === state.assistantRequestId) {
            setBusy('assistant', false);
            updateAssistantStatus('就绪', 'ready');
            updateCpuMeter(false);
        }
    }
}

function buildAssistantPrompt(userMessage) {
    const task = state.currentTask;
    const code = elements.codeInput?.value || '';
    const reviewSummary = state.mode === 'fix' && state.reviewReports[task.id]?.summary
        ? `最近一次批阅：已改正 ${state.reviewReports[task.id].summary.correct_count || 0} 处，仍有 ${state.reviewReports[task.id].summary.wrong_count || 0} 处问题。`
        : '';
    const gradeSummary = state.mode === 'complete' && state.gradeReports[task.id]
        ? `最近一次评估分数：${Number(state.gradeReports[task.id].score) || 0} 分。`
        : '';
    const modeInstruction = state.mode === 'fix'
        ? '你当前服务于“代码修改”模式。请优先帮助学生定位 bug、解释报错、缩小排查范围，不要直接给出完整修正版代码。'
        : '你当前服务于“补全代码”模式。请优先帮助学生理解 TODO 应补什么逻辑、边界条件和测试思路，不要直接给完整答案。';

    return [
        modeInstruction,
        `推荐依据：${task.recommendationReason}`,
        `当前知识点：${task.learningFocus}，掌握度约 ${task.mastery}%`,
        `题目标题：${task.title}`,
        `题目说明：${task.description.join(' ')}`,
        `示例：${task.examples.map((item) => buildExampleSummary(item)).join('；')}`,
        `提示：${task.hints.join('；')}`,
        reviewSummary,
        gradeSummary,
        '当前编辑器代码：',
        '```python',
        code,
        '```',
        `学生消息：${userMessage}`
    ].filter(Boolean).join('\n');
}

function buildExampleSummary(item) {
    if (item.content) {
        return item.content;
    }
    return [
        item.input ? `输入 ${item.input}` : '',
        item.output ? `输出 ${item.output}` : '',
        item.explanation ? `说明 ${item.explanation}` : ''
    ].filter(Boolean).join('，');
}

function createStreamingMessage(label) {
    const row = document.createElement('div');
    row.className = 'message-row ai';
    row.innerHTML = `
        <div class="message-avatar">AI</div>
        <div class="message-card">
            <div class="message-meta">${escapeHtml(label)} · ${getTimeString()}</div>
            <div class="message-content"></div>
        </div>
    `;

    elements.messageContainer?.appendChild(row);
    scrollMessagesToBottom();

    return {
        row,
        content: row.querySelector('.message-content')
    };
}

function addMessage(role, content, options = {}) {
    const row = document.createElement('div');
    row.className = `message-row ${role === 'user' ? 'user' : 'ai'}`;
    row.innerHTML = `
        <div class="message-avatar">${role === 'user' ? '我' : 'AI'}</div>
        <div class="message-card">
            <div class="message-meta">${escapeHtml(options.label || (role === 'user' ? '我' : 'AI 导师'))} · ${getTimeString()}</div>
            <div class="message-content">${options.html ? content : formatPlainText(content)}</div>
        </div>
    `;

    elements.messageContainer?.appendChild(row);
    scrollMessagesToBottom();
    return row;
}

function renderReviewReport(report, task, title = 'AI 批阅报告') {
    const correctItems = Array.isArray(report.correct_items) ? report.correct_items : [];
    const wrongItems = Array.isArray(report.wrong_items) ? report.wrong_items : [];
    const summary = report.summary || {};

    const html = `
        <div class="review-report">
            <div class="review-report-title">${escapeHtml(title)}</div>
            <div class="review-section-title">题目</div>
            <div class="review-item">
                <div class="review-item-content">#${escapeHtml(task.number)} ${escapeHtml(task.title)}</div>
            </div>
            ${correctItems.length ? `
                <div class="review-section-title">已改正</div>
                ${correctItems.map((item) => `
                    <div class="review-item correct">
                        <div class="review-item-line">第 ${escapeHtml(item.line ?? '?')} 行</div>
                        <div class="review-item-content">${escapeHtml(item.description || '')}</div>
                    </div>
                `).join('')}
            ` : ''}
            ${wrongItems.length ? `
                <div class="review-section-title">还需处理</div>
                ${wrongItems.map((item) => `
                    <div class="review-item wrong">
                        <div class="review-item-line">第 ${escapeHtml(item.line ?? '?')} 行</div>
                        <div class="review-item-content">${escapeHtml(item.description || '')}</div>
                        ${item.suggestion ? `<div class="review-item-suggestion">建议：${escapeHtml(item.suggestion)}</div>` : ''}
                    </div>
                `).join('')}
            ` : ''}
            <div class="review-summary">
                <div class="review-summary-stats">
                    <span>✓ ${escapeHtml(summary.correct_count ?? 0)} 已改正</span>
                    <span>✗ ${escapeHtml(summary.wrong_count ?? 0)} 待处理</span>
                </div>
                <div class="review-summary-status ${summary.passed ? 'passed' : 'pending'}">
                    ${summary.passed ? '已全部修复' : '继续修正'}
                </div>
            </div>
        </div>
    `;

    addMessage('ai', html, { label: 'AI 批阅', html: true });
}

function renderCompletionReport(report, task, title = '学习评估') {
    const score = Number(report.score) || 0;
    const suggestions = Array.isArray(report.suggestions) ? report.suggestions : [];

    const html = `
        <div class="review-report">
            <div class="review-report-title">${escapeHtml(title)}</div>
            <div class="review-section-title">题目</div>
            <div class="review-item">
                <div class="review-item-content">#${escapeHtml(task.number)} ${escapeHtml(task.title)}</div>
            </div>
            <div class="review-section-title">综合得分</div>
            <div class="review-item ${score >= 75 ? 'correct' : 'wrong'}">
                <div class="review-item-content">${escapeHtml(score)} / 100</div>
            </div>
            <div class="review-section-title">正确性分析</div>
            <div class="review-item ${score >= 75 ? 'correct' : 'wrong'}">
                <div class="review-item-content">${escapeHtml(report.correctness || '暂无')}</div>
            </div>
            <div class="review-section-title">逻辑分析</div>
            <div class="review-item">
                <div class="review-item-content">${escapeHtml(report.logic_analysis || '暂无')}</div>
            </div>
            <div class="review-section-title">代码风格</div>
            <div class="review-item">
                <div class="review-item-content">${escapeHtml(report.style_analysis || '暂无')}</div>
            </div>
            ${suggestions.length ? `
                <div class="review-section-title">改进建议</div>
                ${suggestions.map((item) => `
                    <div class="review-item wrong">
                        <div class="review-item-content">${escapeHtml(item)}</div>
                    </div>
                `).join('')}
            ` : ''}
            ${report.encouragement ? `
                <div class="review-section-title">鼓励反馈</div>
                <div class="review-item correct">
                    <div class="review-item-content">${escapeHtml(report.encouragement)}</div>
                </div>
            ` : ''}
            <div class="review-summary">
                <div class="review-summary-stats">
                    <span>掌握点：${escapeHtml(task.learningFocus)}</span>
                </div>
                <div class="review-summary-status ${score >= 75 ? 'passed' : 'pending'}">
                    ${score >= 75 ? '当前学习效果达标' : '建议继续巩固'}
                </div>
            </div>
        </div>
    `;

    addMessage('ai', html, { label: '学习评估', html: true });
}

function addRunGuidance(result, task) {
    const success = Number(result.returncode) === 0;

    if (success) {
        const text = state.mode === 'fix'
            ? '代码已经能够运行了。下一步建议点「AI 批阅」，确认是否还有遗漏的逻辑或边界问题。'
            : '代码运行通过了。现在可以点「学习评估」看看完成质量。';
        addMessage('ai', text, { label: 'AI 导师' });
        return;
    }

    const lastErrorLine = extractLastErrorLine(result.stderr || '');
    const text = state.mode === 'fix'
        ? `这次运行暴露出新的线索：${lastErrorLine || '请先阅读 traceback。'} 先从报错最靠近你代码的位置开始修。`
        : `运行还没有通过：${lastErrorLine || '请先根据报错定位 TODO 附近的逻辑。'} 先让代码跑通，再做学习评估。`;
    addMessage('ai', text, { label: 'AI 导师' });
}

function updateIssueBadge() {
    if (!elements.issueBadge || !state.currentTask) {
        return;
    }

    if (state.mode === 'fix') {
        const report = state.reviewReports[state.currentTask.id];
        if (report?.summary) {
            elements.issueBadge.textContent = report.summary.passed
                ? '已全部修复'
                : `剩余 ${report.summary.wrong_count || 0} 处问题`;
            return;
        }

        elements.issueBadge.textContent = `${state.currentTask.errorCount || 0} 处待修复`;
        return;
    }

    const todoCount = countTodoSlots(elements.codeInput?.value || state.currentTask.starterCode || '');
    const report = state.gradeReports[state.currentTask.id];

    if (todoCount > 0) {
        elements.issueBadge.textContent = `${todoCount} 处 TODO 待补全`;
        return;
    }

    if (report) {
        elements.issueBadge.textContent = `最近得分 ${Number(report.score) || 0} 分`;
        return;
    }

    elements.issueBadge.textContent = '可运行验证';
}

function updateAssistantStatus(text, stateName) {
    if (elements.statusText) {
        elements.statusText.textContent = text;
    }

    if (elements.statusBadge) {
        if (stateName === 'busy') {
            elements.statusBadge.dataset.state = 'busy';
        } else if (stateName === 'error') {
            elements.statusBadge.dataset.state = 'error';
        } else {
            elements.statusBadge.dataset.state = 'ready';
        }
    }
}

function updateTerminalState(kind, text) {
    if (elements.terminalStateText) {
        elements.terminalStateText.textContent = text;
    }

    if (elements.terminalState) {
        elements.terminalState.dataset.state = kind;
    }
}

function updateCpuMeter(active) {
    if (!elements.terminalCpu) {
        return;
    }

    const value = active
        ? 24 + Math.floor(Math.random() * 16)
        : 8 + Math.floor(Math.random() * 8);
    elements.terminalCpu.textContent = `CPU: ${value}%`;
}

function updateTokenMeter() {
    if (elements.terminalToken) {
        elements.terminalToken.textContent = `AI: ${state.tokenUsage}`;
    }
}

function setOutput(outputState, text) {
    if (!elements.outputContent) {
        return;
    }

    elements.outputContent.dataset.state = outputState;
    elements.outputContent.innerHTML = '';
    const lineType = outputState === 'idle'
        ? 'muted'
        : outputState === 'loading'
            ? 'system'
            : outputState === 'success'
                ? 'success'
                : outputState === 'error'
                    ? 'error'
                    : 'stdout';
    appendTerminalLine(text, lineType);
    scrollOutputToBottom();
}

function resetOutput() {
    setOutput('idle', DEFAULT_OUTPUTS[state.mode]);
}

async function fetchSseStream(url, payload, handlers = {}) {
    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
    });

    if (!response.ok) {
        throw new Error(`流式接口返回 ${response.status}`);
    }
    if (!response.body) {
        throw new Error('浏览器未获取到流式响应体');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let finalResult = null;

    try {
        while (true) {
            const { done, value } = await reader.read();
            if (done) {
                break;
            }

            buffer += decoder.decode(value, { stream: true });
            const events = buffer.split('\n\n');
            buffer = events.pop() || '';

            for (const rawEvent of events) {
                const parsed = parseSseEvent(rawEvent);
                if (!parsed) {
                    continue;
                }

                const { event, data } = parsed;
                if (event === 'status') {
                    handlers.onStatus?.(data);
                } else if (event === 'content') {
                    handlers.onContent?.(data);
                } else if (event === 'code_start') {
                    handlers.onCodeStart?.(data);
                } else if (event === 'code_chunk') {
                    handlers.onCodeChunk?.(data);
                } else if (event === 'code_complete') {
                    handlers.onCodeComplete?.(data);
                } else if (event === 'result') {
                    finalResult = data;
                    handlers.onResult?.(data);
                } else if (event === 'error') {
                    throw new Error(data?.message || '流式接口返回错误');
                } else {
                    handlers.onMessage?.(data);
                }
            }
        }
    } finally {
        reader.releaseLock();
    }

    if (!finalResult) {
        throw new Error('流式接口未返回最终结果');
    }
    return finalResult;
}

function parseSseEvent(rawEvent) {
    const lines = rawEvent.split('\n').map((line) => line.trimEnd());
    let event = 'message';
    const dataLines = [];

    lines.forEach((line) => {
        if (!line || line.startsWith(':')) {
            return;
        }
        if (line.startsWith('event:')) {
            event = line.slice(6).trim();
        } else if (line.startsWith('data:')) {
            dataLines.push(line.slice(5).trim());
        }
    });

    if (!dataLines.length) {
        return null;
    }

    const rawData = dataLines.join('\n');
    try {
        return { event, data: JSON.parse(rawData) };
    } catch (error) {
        return { event, data: rawData };
    }
}

function updateGenerationStreamPreview(chunk) {
    if (!chunk) {
        return;
    }

    updateGenerationStreamPreview.buffer = `${updateGenerationStreamPreview.buffer || ''}${chunk}`;
    const draft = updateGenerationStreamPreview.buffer;
    if (elements.generationCopy) {
        elements.generationCopy.textContent = `AI 正在流式写入代码... 已接收 ${draft.length} 字`;
    }
}

function appendStreamingCodeToEditor(chunk, options = {}) {
    const editor = elements.codeInput;
    if (!editor) {
        return;
    }

    if (options.reset || !appendStreamingCodeToEditor.started) {
        cancelTypingAnimation();
        editor.value = '';
        appendStreamingCodeToEditor.started = true;
    }

    if (chunk) {
        editor.value += chunk;
    }

    updateLineNumbers();
    editor.scrollTop = editor.scrollHeight;
    syncLineNumberScroll();
}

function appendTerminalLine(text, type = 'stdout') {
    if (!elements.outputContent) {
        return;
    }

    const line = document.createElement('div');
    line.className = `terminal-line ${type}`;
    line.textContent = text || '';
    elements.outputContent.appendChild(line);
}

function renderExecutionOutput(result) {
    if (!elements.outputContent) {
        return;
    }

    const returnCode = Number(result.returncode);
    const success = returnCode === 0;
    elements.outputContent.dataset.state = success ? 'success' : 'error';
    elements.outputContent.innerHTML = '';

    appendTerminalLine('正在编译运行...', 'system');

    const stdout = String(result.stdout || '').trimEnd();
    const stderr = String(result.stderr || '').trimEnd();

    if (stdout) {
        appendTerminalLine(stdout, 'stdout');
    }

    if (stderr) {
        appendTerminalLine(stderr, 'stderr');
    }

    if (!stdout && !stderr) {
        appendTerminalLine('// 程序没有产生输出', 'muted');
    }

    appendTerminalLine(`进程已结束，退出代码 ${Number.isFinite(returnCode) ? returnCode : '未知'}`, success ? 'success' : 'error');
    scrollOutputToBottom();
}

function scrollOutputToBottom() {
    if (elements.outputContent) {
        elements.outputContent.scrollTop = elements.outputContent.scrollHeight;
    }
}

async function runPythonCode(code) {
    const response = await fetch('/api/run-code', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            code,
            language: 'python'
        })
    });

    if (!response.ok) {
        throw new Error(`运行接口返回 ${response.status}`);
    }

    return response.json();
}

function buildRunOutput(task, result) {
    const parts = [];

    if ((result.stdout || '').trim()) {
        parts.push(result.stdout.trim());
    }

    if ((result.stderr || '').trim()) {
        parts.push(result.stderr.trim());
    }

    parts.push(`进程已结束，退出代码 ${result.returncode}`);
    return parts.join('\n\n');
}

function buildReviewSummaryText(report, task) {
    const summary = report.summary || {};

    return [
        `已改正：${summary.correct_count || 0} 处`,
        `待处理：${summary.wrong_count || 0} 处`,
        summary.passed ? '状态：已全部修复' : '状态：仍有遗漏'
    ].join('\n');
}

function buildCompletionSummaryText(report, task) {
    const score = Number(report.score) || 0;
    return [
        `综合得分：${score} / 100`,
        `正确性：${report.correctness || '暂无'}`,
        score >= 75 ? '状态：当前学习效果达标' : '状态：建议继续巩固'
    ].join('\n');
}

function buildCompletionTaskPrompt(task) {
    return [
        `题目名称：${task.title}`,
        `知识点：${task.learningFocus}`,
        `题目说明：${task.description.join(' ')}`,
        `示例：${task.examples.map((item) => buildExampleSummary(item)).join('；')}`,
        `要求：请根据题意补全代码中的 TODO，并保证程序可以运行。`
    ].join('\n');
}

function recordPracticeResult(task, passed, extra = {}) {
    const topic = task.learningFocus || task.topic || '函数';
    const current = getTopicMastery(topic);
    let delta = passed ? 6 : -3;

    if (task.mode === 'complete' && typeof extra.score === 'number') {
        if (extra.score >= 90) {
            delta = 8;
        } else if (extra.score >= 75) {
            delta = 5;
        } else if (extra.score >= 60) {
            delta = -1;
        } else {
            delta = -4;
        }
    }

    if (task.mode === 'fix' && extra.report?.summary) {
        const wrongCount = Number(extra.report.summary.wrong_count) || 0;
        delta = passed ? 5 : Math.max(-4, -1 - wrongCount);
    }

    state.learningState.masteryByTopic[topic] = clamp(current + delta, 25, 96);
    state.learningState.lastMode = task.mode;
    state.learningState.correctCount += passed ? 1 : 0;
    state.learningState.wrongCount += passed ? 0 : 1;
    state.learningState.weakTopics = deriveWeakTopics(state.learningState.masteryByTopic);
    state.learningState.learningHistory.push({
        id: task.id,
        baseId: task.baseId || task.id,
        mode: task.mode,
        topic,
        chapter: task.chapter,
        passed: Boolean(passed),
        score: typeof extra.score === 'number' ? extra.score : null,
        timestamp: Date.now()
    });

    if (state.learningState.learningHistory.length > 30) {
        state.learningState.learningHistory = state.learningState.learningHistory.slice(-30);
    }

    saveLearningState();
}

function refreshMasteryCard(topic) {
    if (!state.currentTask || state.currentTask.learningFocus !== topic) {
        return;
    }

    state.currentTask.mastery = getTopicMastery(topic);
    if (elements.masteryRate) {
        elements.masteryRate.textContent = `${state.currentTask.mastery}%`;
    }
    if (elements.masteryProgress) {
        elements.masteryProgress.style.width = `${state.currentTask.mastery}%`;
    }
}

function createDefaultLearningState() {
    return {
        correctCount: 0,
        wrongCount: 0,
        interactionCount: 0,
        socraticPassRate: 0.72,
        practiceMinutes: 18,
        lastMode: 'complete',
        masteryByTopic: { ...DEFAULT_MASTERY_MAP },
        weakTopics: deriveWeakTopics(DEFAULT_MASTERY_MAP),
        learningHistory: []
    };
}

function loadLearningState() {
    const base = createDefaultLearningState();
    let merged = base;

    try {
        const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null');
        if (saved && typeof saved === 'object') {
            merged = normalizeLearningState(saved);
        }
    } catch (error) {
        merged = base;
    }

    try {
        const legacy = JSON.parse(localStorage.getItem(LEGACY_STORAGE_KEY) || 'null');
        if (legacy && typeof legacy === 'object') {
            merged = normalizeLearningState({
                ...merged,
                ...legacy
            });
        }
    } catch (error) {
        // ignore legacy read errors
    }

    state.learningState = merged;
}

function normalizeLearningState(raw) {
    const base = createDefaultLearningState();
    const masteryByTopic = sanitizeMasteryMap(raw.masteryByTopic);
    const topicStats = raw.topicStats && typeof raw.topicStats === 'object' ? raw.topicStats : {};

    Object.entries(topicStats).forEach(([topic, stats]) => {
        const total = Number(stats?.total) || 0;
        const correct = Number(stats?.correct) || 0;
        if (total > 0) {
            masteryByTopic[topic] = clamp(Math.round((correct / total) * 100), 25, 96);
        }
    });

    const history = [];

    const pushHistory = (item) => {
        if (!item || typeof item !== 'object') {
            return;
        }
        history.push({
            id: item.id || item.problemId || item.problem_id || `history-${history.length}`,
            mode: item.mode === 'complete' ? 'complete' : 'fix',
            topic: item.topic || '函数',
            chapter: item.chapter || TOPIC_CHAPTER_MAP[item.topic] || 'ch3',
            passed: typeof item.passed === 'boolean' ? item.passed : Boolean(item.isCorrect),
            score: typeof item.score === 'number' ? item.score : null,
            timestamp: item.timestamp || Date.now()
        });
    };

    (Array.isArray(raw.learningHistory) ? raw.learningHistory : []).forEach(pushHistory);
    (Array.isArray(raw.history) ? raw.history : []).forEach(pushHistory);
    (Array.isArray(raw.problemHistory) ? raw.problemHistory : []).forEach((item) => {
        pushHistory({
            id: item.problemId || item.id,
            mode: 'fix',
            topic: item.topic || '函数',
            chapter: item.chapter || TOPIC_CHAPTER_MAP[item.topic] || 'ch3',
            passed: Boolean(item.isCorrect),
            timestamp: item.timestamp
        });
    });

    const weakTopics = Array.isArray(raw.weakTopics) && raw.weakTopics.length
        ? raw.weakTopics.filter((item) => typeof item === 'string' && item.trim())
        : deriveWeakTopics(masteryByTopic);

    return {
        ...base,
        correctCount: Number(raw.correctCount) || 0,
        wrongCount: Number(raw.wrongCount) || 0,
        interactionCount: Number(raw.interactionCount || raw.totalInteractions) || 0,
        socraticPassRate: clamp(Number(raw.socraticPassRate ?? base.socraticPassRate), 0, 1),
        practiceMinutes: Number(raw.practiceMinutes ?? base.practiceMinutes) || base.practiceMinutes,
        lastMode: raw.lastMode === 'complete' ? 'complete' : 'fix',
        masteryByTopic,
        weakTopics,
        learningHistory: history.slice(-30)
    };
}

function sanitizeMasteryMap(input) {
    const mastery = { ...DEFAULT_MASTERY_MAP };
    if (!input || typeof input !== 'object') {
        return mastery;
    }

    Object.entries(input).forEach(([topic, value]) => {
        const numeric = Number(value);
        if (Number.isFinite(numeric)) {
            mastery[topic] = clamp(Math.round(numeric), 25, 96);
        }
    });

    return mastery;
}

function saveLearningState() {
    flushPracticeMinutes();
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(state.learningState));
    } catch (error) {
        // ignore write errors
    }
}

function flushPracticeMinutes() {
    state.learningState.practiceMinutes = getPracticeMinutes();
    state.sessionStartedAt = Date.now();
}

function getPracticeMinutes() {
    const currentSessionMinutes = Math.floor((Date.now() - state.sessionStartedAt) / 60000);
    return (Number(state.learningState.practiceMinutes) || 0) + Math.max(0, currentSessionMinutes);
}

function buildProfilePayload() {
    return {
        current_mode: state.mode,
        weak_topics: state.learningState.weakTopics,
        mastery_by_topic: state.learningState.masteryByTopic,
        correct_count: state.learningState.correctCount,
        wrong_count: state.learningState.wrongCount,
        current_focus: state.currentTask?.learningFocus || ''
    };
}

function buildLearningPath() {
    return state.learningState.learningHistory.slice(-5).map((item) => ({
        chapter: item.chapter,
        topic: item.topic,
        passed: item.passed,
        timestamp: item.timestamp
    }));
}

function deriveWeakTopics(masteryMap) {
    return Object.entries({ ...DEFAULT_MASTERY_MAP, ...(masteryMap || {}) })
        .sort((left, right) => left[1] - right[1])
        .slice(0, 3)
        .map(([topic]) => topic);
}

function getTopicMastery(topic) {
    return clamp(Number(state.learningState.masteryByTopic?.[topic] ?? DEFAULT_MASTERY_MAP[topic] ?? 65), 25, 96);
}

function chooseDifficulty(mastery, mode) {
    if (mastery < 55) {
        return 'easy';
    }
    if (mastery < 75) {
        return 'medium';
    }
    return mode === 'fix' ? 'medium' : 'hard';
}

function buildSourceLabel(task) {
    if (task.source === 'ai') {
        return 'AI 即时生成';
    }
    if (task.source === 'fallback') {
        return '回退调试题';
    }
    return '学情模板推送';
}

function accumulateTokenUsage(charCount) {
    state.tokenUsage += Math.max(1, Math.round(charCount / 4));
    updateTokenMeter();
}

function pushSuggestedTaskId(mode, id) {
    state.suggestedTaskIds[mode].push(id);
    if (state.suggestedTaskIds[mode].length > 6) {
        state.suggestedTaskIds[mode] = state.suggestedTaskIds[mode].slice(-6);
    }
}

function clearMessages() {
    if (elements.messageContainer) {
        elements.messageContainer.innerHTML = '';
    }
}

function scrollMessagesToBottom() {
    if (elements.messageContainer) {
        elements.messageContainer.scrollTop = elements.messageContainer.scrollHeight;
    }
}

function syncModeToUrl() {
    const url = new URL(window.location.href);
    url.searchParams.set('mode', state.mode);
    window.history.replaceState({}, '', url.toString());
}

function countTodoSlots(code) {
    return (code.match(/__TODO__/g) || []).length;
}

function extractProblemStarterCode(problem) {
    return problem?.starter_code || problem?.starterCode || problem?.code || '';
}

function estimateIssueCountFromHints(uiHints = {}, problem = {}) {
    const description = [
        problem.task_info?.description,
        uiHints.known_issue,
        uiHints.error_clue
    ].filter(Boolean).join(' ');
    const rangeMatch = description.match(/(\d+)\s*[-~至到]\s*(\d+)/);
    if (rangeMatch) {
        return Number(rangeMatch[2]) || 3;
    }
    const countMatch = description.match(/(\d+)\s*处/);
    return Number(countMatch?.[1]) || 3;
}

function countAnnotatedErrors(code) {
    return (code.match(/#\s*错误\d+/g) || []).length;
}

function extractLastErrorLine(stderr) {
    const lines = stderr.split('\n').map((line) => line.trim()).filter(Boolean);
    return lines.length ? lines[lines.length - 1] : '';
}

function formatNumber(value, prefix) {
    const digits = String(value || '')
        .replace(/\D/g, '')
        .slice(-3)
        .padStart(3, '0');
    return digits === '000' ? `${prefix}00` : `${prefix}${digits}`;
}

function stripCodeFences(text) {
    return String(text || '')
        .replace(/^```[a-zA-Z]*\s*/, '')
        .replace(/\s*```$/, '')
        .trim();
}

function removeSpoilerComments(code) {
    return String(code || '')
        .split('\n')
        .map((line) => line.replace(/\s+#\s*(错误|錯誤|閿欒|error|bug|这里写错|此处写错|写错了)\d*[:：]?.*$/i, ''))
        .join('\n')
        .trim();
}

function uniqueStrings(items) {
    return Array.from(new Set(items.filter(Boolean)));
}

function formatPlainText(text) {
    return escapeHtml(text).replace(/\n/g, '<br>');
}

function getTimeString() {
    return new Date().toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit'
    });
}

function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
}

function sleep(ms) {
    return new Promise((resolve) => {
        window.setTimeout(resolve, ms);
    });
}

window.switchPracticeMode = switchMode;
window.requestNewCodingTask = function requestNewCodingTask() {
    return requestPersonalizedTask({ manual: true });
};
