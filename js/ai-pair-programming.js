// ============================================
// 玄武·AI 结对编程舱 - JavaScript
// ============================================

// 示例代码问题库
const codeProblems = [
    {
        id: 1,
        title: "排序算法作用域问题",
        language: "python",
        code: `import json
from typing import List, Dict

def merge_sort(arr: List[int]) -> List[int]:
    """归并排序实现"""
    if len(arr) <= 1:
        return arr

    mid = len(arr) // 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])

    return merge(left, right)

def merge(left: List[int], right: List[int]) -> List[int]:
    result = []
    i = j = 0

    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1

    result.extend(left[i:])
    result.extend(right[j:])
    return result

def quick_sort(arr: List[int]) -> List[int]:
    """快速排序实现"""
    if len(arr) <= 1:
        return arr

    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]

    return quick_sort(left) + middle + quick_sort(right)
    result = merge_sort(arr)  # 错误：调用了未定义的 merge_sort
    return result

if __name__ == "__main__":
    test_array = [64, 34, 25, 12, 22, 11, 90]
    print("原始数组:", test_array)
    sorted_array = quick_sort(test_array)
    print("排序后:", sorted_array)`,
        errorLine: 44,
        errorType: "NameError",
        errorMsg: "name 'merge_sort' is not defined. Did you mean: 'quick_sort'?"
    },
    {
        id: 2,
        title: "列表索引越界",
        language: "python",
        code: `def find_element(arr, target):
    """查找元素位置"""
    for i in range(len(arr)):
        if arr[i] == target:
            return i
    return -1

def remove_duplicates(arr):
    """移除重复元素"""
    result = []
    for i in range(len(arr)):
        if arr[i] not in result:
            result.append(arr[i])
    return result

def get_first_three(arr):
    """获取前三个元素"""
    return arr[0:3]

# 测试代码
numbers = [1, 2, 3, 4, 5]
print(find_element(numbers, 3))
print(remove_duplicates([1, 1, 2, 2, 3, 3]))
print(get_first_three(numbers))`,
        errorLine: null,
        errorType: null,
        errorMsg: null
    },
    {
        id: 3,
        title: "文件处理异常",
        language: "python",
        code: `import json
from typing import Dict, List

def read_config(filename):
    """读取配置文件"""
    with open(filename, 'r') as f:
        data = json.load(f)
    return data

def process_data(data: Dict) -> List:
    """处理数据"""
    results = []
    for key, value in data.items():
        results.append(f"{key}: {value}")
    return results

def save_results(results: List, filename):
    """保存结果"""
    with open(filename, 'w') as f:
        json.dump(results, f)

# 主程序
config = read_config('config.json')
processed = process_data(config)
save_results(processed, 'output.json')`,
        errorLine: 19,
        errorType: "FileNotFoundError",
        errorMsg: "[Errno 2] No such file or directory: 'config.json'"
    }
];

// 全局状态
let state = {
    currentProblem: null,
    currentCode: '',
    messages: [],
    isTyping: false,
    isAIThinking: false,
    cpuUsage: 12,
    tokenCount: 0,
    sessionId: null,
    studentId: 'anonymous',
    courseId: 'bigdata',
    contextId: null,
    interactionCount: 0,
    socraticPassRate: 0.0
};

// DOM 缓存
let domCache = {};

// ============================================
// 初始化
// ============================================
function initDOMCache() {
    domCache = {
        modal: document.getElementById('ide-modal'),
        editorContent: document.getElementById('editor-content'),
        messageContainer: document.getElementById('message-container'),
        diffContainer: document.getElementById('diff-container'),
        submitInput: document.getElementById('submit-input'),
        sendBtn: document.getElementById('send-btn'),
        terminalCpu: document.getElementById('terminal-cpu'),
        terminalToken: document.getElementById('terminal-token'),
        problemSelect: document.getElementById('problem-select'),
        statusBadge: document.getElementById('status-badge'),
        codeInput: document.getElementById('code-input'),
        errorCount: document.getElementById('error-count'),
        titleDisplay: document.getElementById('problem-title')
    };
}

function init() {
    initDOMCache();
    loadProblem(1);
    initEventListeners();
    initKeyboardShortcuts();
    startTokenSimulation();
    initSession();
}

// ============================================
// 会话初始化
// ============================================
function initSession() {
    state.sessionId = Date.now().toString(36) + Math.random().toString(36).substr(2);
    state.contextId = 'pair-prog-' + state.sessionId;
    state.tokenCount = 0;
    state.interactionCount = 0;
    state.socraticPassRate = 0.0;
    setInterval(updateCPUDisplay, 3000);
}

// ============================================
// 问题加载
// ============================================
function loadProblem(problemId) {
    const problem = codeProblems.find(p => p.id === problemId);
    if (!problem) return;

    state.currentProblem = problem;
    state.currentCode = problem.code;
    state.messages = [];

    // 更新标题
    if (domCache.titleDisplay) {
        domCache.titleDisplay.textContent = problem.title;
    }

    // 更新错误计数
    if (domCache.errorCount) {
        domCache.errorCount.textContent = problem.errorLine ? '1 Error' : '0 Errors';
        domCache.errorCount.className = problem.errorLine
            ? 'px-2 py-0.5 rounded bg-red-500/20 text-red-400 text-[11px]'
            : 'px-2 py-0.5 rounded bg-green-500/20 text-green-400 text-[11px]';
    }

    // 清空消息
    if (domCache.messageContainer) {
        domCache.messageContainer.innerHTML = '';
    }

    // 渲染代码
    renderCode();

    // 初始 AI 问候（苏格拉底式）
    setTimeout(() => {
        const greeting = `你好！我是你的 AI 编程导师 👋

我注意到你正在查看「${problem.title}」这个代码示例。

在我开始分析之前，我想先问你几个问题：
1. 你觉得这段代码想要实现什么功能？
2. 你注意到有没有什么不对劲的地方？

不要担心说错——结对编程的意义就在于一起思考、一起探索。`;
        addAIMessage(greeting);
    }, 500);
}

// ============================================
// 代码渲染
// ============================================
function renderCode() {
    const container = domCache.editorContent;
    const code = state.currentCode;
    if (!container || !code) return;

    const lines = code.split('\n');
    container.innerHTML = '';

    lines.forEach((line, index) => {
        const lineNum = index + 1;
        const isError = state.currentProblem?.errorLine === lineNum;

        const lineEl = document.createElement('div');
        lineEl.className = `flex text-[13px] leading-6 ${isError ? 'error-line' : ''} group`;

        // 行号
        const gutterEl = document.createElement('div');
        gutterEl.className = `w-12 text-right pr-4 flex-shrink-0 select-none font-mono flex items-center justify-end gap-1 ${isError ? 'text-red-400' : 'text-[#858585]'}`;

        if (isError) {
            gutterEl.innerHTML = `
                <span class="error-gutter-marker">
                    ⚠️
                    <div class="error-tooltip">
                        <div class="font-semibold text-red-400 mb-1">${state.currentProblem.errorType}</div>
                        <div>${state.currentProblem.errorMsg}</div>
                    </div>
                </span>
            `;
        } else {
            gutterEl.textContent = lineNum;
        }

        // 代码内容
        const codeEl = document.createElement('div');
        codeEl.className = 'flex-1 pl-2 pr-4';

        if (line.trim() === '') {
            codeEl.innerHTML = '&nbsp;';
        } else if (isError) {
            codeEl.innerHTML = `<span class="wavy-underline text-red-300">${escapeHtml(highlightSyntax(line))}</span>`;
        } else {
            codeEl.innerHTML = highlightSyntax(line);
        }

        // 折叠指示器
        const foldEl = document.createElement('div');
        foldEl.className = 'w-6 text-center text-[#808080] cursor-pointer hover:text-[#c6c6c6] flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity';
        foldEl.textContent = '▶';

        lineEl.appendChild(gutterEl);
        lineEl.appendChild(codeEl);
        lineEl.appendChild(foldEl);

        container.appendChild(lineEl);
    });
}

function highlightSyntax(code) {
    let result = escapeHtml(code);
    // 注释
    result = result.replace(/#.*$/, '<span class="syntax-comment">$&</span>');
    // 字符串
    result = result.replace(/"([^"]*)"/g, '<span class="syntax-string">"$1"</span>');
    result = result.replace(/'([^']*)'/g, '<span class="syntax-string">\'$1\'</span>');
    // 数字
    result = result.replace(/\b(\d+)\b/g, '<span class="syntax-number">$1</span>');
    // 类型
    result = result.replace(/\b(List|int|str|Dict|bool|None)\b/g, '<span class="syntax-type">$1</span>');
    // 关键字
    result = result.replace(/\b(import|from|def|return|if|elif|else|while|for|in|not|and|or|with|as|class|try|except|finally|raise|lambda|yield|global|nonlocal|pass|break|continue)\b/g, '<span class="syntax-keyword">$1</span>');
    // 函数调用
    result = result.replace(/\b(print|len|range|str|int|list|dict|set|tuple|open|json\.load|json\.dump|append|extend|items|keys|values)\b(?=\()/g, '<span class="syntax-function">$1</span>');
    return result;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================
// 消息系统
// ============================================
function addMessage(type, content) {
    const container = domCache.messageContainer;
    if (!container) return;

    const msgEl = document.createElement('div');
    msgEl.className = `flex gap-3 ${type === 'user' ? 'justify-end' : ''} mb-4`;

    if (type === 'ai') {
        msgEl.innerHTML = `
            <div class="message-avatar ai">🤖</div>
            <div class="message-card ai-message flex-1">
                <div class="text-[11px] text-indigo-400 mb-1">AI 导师 · ${getTimeString()}</div>
                <div class="text-[13px] leading-relaxed ai-message-content">${content}</div>
            </div>
        `;
    } else {
        msgEl.innerHTML = `
            <div class="message-card user-message">
                <div class="text-[11px] text-gray-400 mb-1">你 · ${getTimeString()}</div>
                <div class="text-[13px] leading-relaxed">${escapeHtml(content)}</div>
            </div>
            <div class="message-avatar user">👤</div>
        `;
    }

    container.appendChild(msgEl);
    container.scrollTop = container.scrollHeight;

    return msgEl;
}

function addAIMessage(content) {
    const msgEl = addMessage('ai', '');
    const contentEl = msgEl.querySelector('.ai-message-content');
    typeText(contentEl, content);
}

function typeText(element, text, speed = 20) {
    state.isTyping = true;
    updateAIStatus('思考中...', true);

    let index = 0;
    element.innerHTML = '<span class="typing-cursor"></span>';

    function type() {
        if (index < text.length) {
            // 处理换行
            const char = text[index];
            if (char === '\n') {
                element.innerHTML = element.innerHTML.replace('<span class="typing-cursor"></span>', '<br><span class="typing-cursor"></span>');
            } else {
                element.innerHTML = text.substring(0, index + 1).replace(/\n/g, '<br>') + '<span class="typing-cursor"></span>';
            }
            index++;
            setTimeout(type, speed);
        } else {
            element.innerHTML = text.replace(/\n/g, '<br>');
            state.isTyping = false;
            updateAIStatus('诊断中', false);
        }
    }

    type();
}

function getTimeString() {
    const now = new Date();
    return `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
}

// ============================================
// AI 状态
// ============================================
function updateAIStatus(text, thinking) {
    if (!domCache.statusBadge) return;

    const dot = domCache.statusBadge.querySelector('.status-dot');
    const label = domCache.statusBadge.querySelector('.status-text');

    if (dot) {
        dot.style.animation = thinking ? 'pulse-status 0.5s ease-in-out infinite' : 'pulse-status 1.5s ease-in-out infinite';
    }
    if (label) {
        label.textContent = text;
    }
}

// ============================================
// 发送消息到 AI
// ============================================
async function sendMessage() {
    const input = domCache.submitInput;
    if (!input) return;

    const content = input.value.trim();
    if (!content || state.isTyping) return;

    // 添加用户消息
    addMessage('user', content);
    state.messages.push({ type: 'user', content });
    input.value = '';

    // 显示 AI 思考状态
    updateAIStatus('思考中...', true);

    // 调用 AI API
    try {
        await callAI(content);
    } catch (error) {
        console.error('AI API 调用失败:', error);
        addAIMessage('抱歉，AI 服务暂时不可用。请稍后再试。');
    }
}

// ============================================
// AI API 调用
// ============================================
async function callAI(userMessage) {
    const payload = {
        student_id: state.studentId,
        course_id: state.courseId,
        user_input: buildSocraticPrompt(userMessage),
        context_id: state.contextId,
        current_profile: {
            knowledgeBase: 'Python 基础',
            codeSkill: '中级',
            learningGoal: '提升编程思维',
            cognitiveStyle: '实践型',
            weakness: state.currentProblem?.title || '作用域问题',
            focusLevel: '高专注'
        },
        current_path: [
            { topic: state.currentProblem?.title || '代码调试', status: 'current' }
        ],
        interaction_count: state.interactionCount,
        code_practice_time: Math.floor(Date.now() / 1000) % 86400,
        socratic_pass_rate: state.socraticPassRate
    };

    const response = await fetch('/api/v2/chat/stream', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
    });

    if (!response.ok) {
        throw new Error(`API 错误: ${response.status}`);
    }

    // 处理 SSE 流
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let fullContent = '';

    // 创建 AI 消息元素
    const msgEl = addMessage('ai', '');
    const contentEl = msgEl.querySelector('.ai-message-content');
    contentEl.innerHTML = '<span class="typing-cursor"></span>';

    state.isTyping = true;
    updateAIStatus('思考中...', true);

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
            if (line.startsWith('data: ')) {
                const data = line.slice(6);
                if (data === '[DONE]') {
                    continue;
                }
                try {
                    const event = JSON.parse(data);
                    if (event.type === 'content_chunk' && event.content) {
                        fullContent += event.content;
                        contentEl.innerHTML = formatSocraticResponse(fullContent) + '<span class="typing-cursor"></span>';
                        domCache.messageContainer.scrollTop = domCache.messageContainer.scrollHeight;
                    } else if (event.type === 'complete') {
                        state.isTyping = false;
                        state.interactionCount++;
                        updateAIStatus('诊断中', false);
                    }
                } catch (e) {
                    // 忽略解析错误
                }
            }
        }
    }

    // 确保光标消失
    contentEl.innerHTML = formatSocraticResponse(fullContent);
    state.isTyping = false;
    updateAIStatus('诊断中', false);

    // 保存消息
    state.messages.push({ type: 'ai', content: fullContent });

    // 更新 token 计数（估算）
    state.tokenCount += Math.ceil(fullContent.length / 4);
    updateTokenDisplay();
}

// ============================================
// 构建苏格拉底式提示
// ============================================
function buildSocraticPrompt(userMessage) {
    const codeContext = state.currentProblem ? `
当前代码问题：${state.currentProblem.title}
错误行：第 ${state.currentProblem.errorLine || '无'} 行
错误类型：${state.currentProblem.errorType || '无'}
错误信息：${state.currentProblem.errorMsg || '无'}

代码内容：
\`\`\`${state.currentProblem.language}
${state.currentProblem.code}
\`\`\`
` : '';

    const lowerMsg = userMessage.toLowerCase();

    // 检测用户意图并构建苏格拉底式提示
    let socraticPrompt = '';

    if (lowerMsg.includes('错误') || lowerMsg.includes('报错') || lowerMsg.includes('error') || lowerMsg.includes('有问题')) {
        socraticPrompt = `学生注意到了代码中的错误："${userMessage}"

作为苏格拉底式导师，请引导学生自己发现问题：

1. 先不要直接指出错误，而是引导学生关注可疑的代码行
2. 询问学生："你观察到第 ${state.currentProblem?.errorLine || '44'} 行调用了什么函数？"
3. 询问："这个函数在代码中是否有定义？定义在哪里？"
4. 引导学生发现：Python 执行顺序是从上往下的
5. 最后给出提示而非答案

保持对话简洁，每次只问一个问题。用中文回复。`;
    } else if (lowerMsg.includes('为什么') || lowerMsg.includes('why')) {
        socraticPrompt = `学生提问："${userMessage}"

作为苏格拉底式导师，引导学生深入思考：

1. 引导学生解释他们对这个问题的理解
2. 追问："你能想到这种情况会在什么时候发生吗？"
3. 帮助学生建立因果关系
4. 必要时用简单类比解释

保持对话简洁，每次只问一个问题。用中文回复。`;
    } else if (lowerMsg.includes('怎么改') || lowerMsg.includes('怎么修') || lowerMsg.includes('如何解决') || lowerMsg.includes('fix')) {
        socraticPrompt = `学生问如何修复错误："${userMessage}"

作为苏格拉底式导师，引导学生自己想出解决方案：

1. 先让学生解释他们打算怎么做
2. 追问："你觉得如果把函数位置调整一下，会有什么效果？"
3. 引导学生思考 Python 的执行顺序
4. 让学生自己说出解决方案
5. 如果学生卡住了，给出方向性提示而非答案

关键：不要直接给答案！让学生通过思考自己找到答案。

保持对话简洁，每次只问一个问题。用中文回复。`;
    } else if (lowerMsg.includes('不懂') || lowerMsg.includes('不理解') || lowerMsg.includes('不明白')) {
        socraticPrompt = `学生表示不理解："${userMessage}"

作为苏格拉底式导师，换一种方式解释：

1. 用日常生活中的类比来解释抽象概念
2. 画一个简单的图示来帮助理解
3. 将复杂问题分解成小步骤
4. 每解释一步就确认学生是否理解

保持对话简洁，每次只问一个问题。用中文回复。`;
    } else if (lowerMsg.includes('明白了') || lowerMsg.includes('懂了') || lowerMsg.includes('理解了')) {
        socraticPrompt = `学生表示理解了："${userMessage}"

作为苏格拉底式导师：
1. 肯定学生的理解
2. 让学生用自己的话复述一遍（检验真正理解）
3. 询问能否应用到其他场景
4. 鼓励学生继续探索

保持对话简洁。用中文回复。`;
    } else {
        // 默认苏格拉底式回应
        socraticPrompt = `学生说："${userMessage}"

当前代码问题：${state.currentProblem?.title || '一般编程问题'}

作为苏格拉底式导师：
1. 先理解学生的问题或困惑
2. 通过提问引导学生思考，而不是直接给答案
3. 每次只问一个引导性问题
4. 鼓励学生自己发现问题

保持对话简洁，每次只问一个问题。用中文回复。`;
    }

    return `你是「玄武·AI结对编程舱」的苏格拉底式编程导师。

角色设定：
- 你是一个启发式编程导师，而不是答案机器
- 你的目标是引导学生自己思考，自己发现问题
- 当学生犯错时，不要直接指出，而是通过提问让他们自己发现
- 用简洁的语言，每次只问一个问题
- 多用类比和图示来解释抽象概念

${codeContext}

${socraticPrompt}

记住：最好的教学不是告诉答案，而是引导思考。`;
}

// ============================================
// 格式化苏格拉底回复
// ============================================
function formatSocraticResponse(text) {
    // 转义 HTML
    let formatted = escapeHtml(text);
    // 处理换行
    formatted = formatted.replace(/\n/g, '<br>');
    // 高亮关键词
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    formatted = formatted.replace(/\*(.*?)\*/g, '<em>$1</em>');
    return formatted;
}

// ============================================
// Token 模拟
// ============================================
function startTokenSimulation() {
    // 已在 initSession 中设置
}

function updateTokenDisplay() {
    if (domCache.terminalToken) {
        domCache.terminalToken.innerHTML = `
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
            </svg>
            <span>AI: ${state.tokenCount}</span>
        `;
    }
}

function updateCPUDisplay() {
    if (domCache.terminalCpu) {
        state.cpuUsage = Math.floor(Math.random() * 30) + 10;
        domCache.terminalCpu.innerHTML = `
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"/>
            </svg>
            <span>CPU: ${state.cpuUsage}%</span>
        `;
    }
}

// ============================================
// 键盘快捷键
// ============================================
function initKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // ESC 关闭弹窗
        if (e.key === 'Escape' && domCache.modal && !domCache.modal.classList.contains('hidden')) {
            closeIDEPanel();
        }

        // Ctrl+Enter 发送消息
        if (e.ctrlKey && e.key === 'Enter') {
            e.preventDefault();
            sendMessage();
        }

        // 方向键切换问题
        if (domCache.modal && !domCache.modal.classList.contains('hidden')) {
            if (e.altKey && e.key === 'ArrowLeft') {
                e.preventDefault();
                prevProblem();
            } else if (e.altKey && e.key === 'ArrowRight') {
                e.preventDefault();
                nextProblem();
            }
        }
    });
}

function prevProblem() {
    const currentId = state.currentProblem?.id || 1;
    const newId = Math.max(1, currentId - 1);
    if (domCache.problemSelect) {
        domCache.problemSelect.value = newId;
    }
    loadProblem(newId);
}

function nextProblem() {
    const currentId = state.currentProblem?.id || 1;
    const newId = Math.min(codeProblems.length, currentId + 1);
    if (domCache.problemSelect) {
        domCache.problemSelect.value = newId;
    }
    loadProblem(newId);
}

// ============================================
// 事件监听
// ============================================
function initEventListeners() {
    // 发送按钮
    if (domCache.sendBtn) {
        domCache.sendBtn.addEventListener('click', sendMessage);
    }

    // 输入框回车发送
    if (domCache.submitInput) {
        domCache.submitInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }

    // 问题选择
    if (domCache.problemSelect) {
        domCache.problemSelect.addEventListener('change', (e) => {
            loadProblem(parseInt(e.target.value));
        });
    }

    // 折叠指示器点击
    document.addEventListener('click', (e) => {
        if (e.target.classList.contains('fold-indicator') || e.target.textContent === '▶') {
            const line = e.target.closest('.flex');
            if (line) {
                const isCollapsed = line.classList.contains('collapsed');
                if (isCollapsed) {
                    line.classList.remove('collapsed');
                    e.target.textContent = '▶';
                } else {
                    line.classList.add('collapsed');
                    e.target.textContent = '▼';
                }
            }
        }
    });
}

// ============================================
// 弹窗控制
// ============================================
function openIDEPanel() {
    domCache.modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function closeIDEPanel() {
    domCache.modal.classList.add('hidden');
    document.body.style.overflow = '';
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', init);
