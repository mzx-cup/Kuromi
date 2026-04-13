// ============================================
// Code Practice - JavaScript Logic
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    initProblemList();
    initFilters();
    initEditor();
    initLanguageSelect();
});

// ============================================
// Problem List
// ============================================
function initProblemList() {
    const problemItems = document.querySelectorAll('.problem-item');

    problemItems.forEach(item => {
        item.addEventListener('click', function() {
            // Update active state
            problemItems.forEach(p => p.classList.remove('active'));
            this.classList.add('active');

            // Update problem description (in real app, would load from data)
            const problemId = this.dataset.id;
            updateProblemDescription(problemId);
        });
    });
}

function updateProblemDescription(problemId) {
    const problemName = document.querySelector('.problem-name');
    const problemContent = document.querySelector('.problem-content');

    if (problemName) {
        const titles = {
            '1': '#001 两数之和',
            '2': '#002 回文数判定',
            '3': '#003 合并两个有序链表',
            '4': '#004 无重复字符的最长子串',
            '5': '#005 寻找两个有序数组的中位数',
            '6': '#006 盛水最多的容器',
            '7': '#007 三数之和',
            '8': '#008 括号生成'
        };
        problemName.textContent = titles[problemId] || `#${problemId} 题目`;
    }
}

// ============================================
// Filter Functionality
// ============================================
function initFilters() {
    const filterBtns = document.querySelectorAll('.filter-btn');

    filterBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            filterBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');

            const filter = this.dataset.filter;
            filterProblems(filter);
        });
    });
}

function filterProblems(filter) {
    const problemItems = document.querySelectorAll('.problem-item');

    problemItems.forEach(item => {
        const difficulty = item.querySelector('.problem-difficulty').textContent;
        const difficultyClass = difficulty === '简单' ? 'easy' : difficulty === '中等' ? 'medium' : 'hard';

        if (filter === 'all' || difficultyClass === filter) {
            item.style.display = 'flex';
        } else {
            item.style.display = 'none';
        }
    });
}

// ============================================
// Code Editor
// ============================================
function initEditor() {
    const runBtn = document.getElementById('run-btn');
    const submitBtn = document.getElementById('submit-btn');
    const resetBtn = document.getElementById('reset-btn');
    const clearBtn = document.getElementById('clear-output');
    const codeInput = document.getElementById('code-input');

    runBtn?.addEventListener('click', function() {
        runCode();
    });

    submitBtn?.addEventListener('click', function() {
        submitCode();
    });

    resetBtn?.addEventListener('click', function() {
        resetCode();
    });

    clearBtn?.addEventListener('click', function() {
        document.getElementById('output-content').textContent = '// 点击"运行代码"查看输出结果';
    });
}

function runCode() {
    const codeInput = document.getElementById('code-input');
    const outputContent = document.getElementById('output-content');
    const code = codeInput.value;

    // Simulate code execution
    outputContent.textContent = '正在运行代码...\n\n';

    setTimeout(() => {
        // Simulated output
        const output = `测试用例 1: [2,7,11,15], target = 9
输出: [0, 1]
状态: 通过 ✓

测试用例 2: [3,2,4], target = 6
输出: [1, 2]
状态: 通过 ✓

测试用例 3: [3,3], target = 6
输出: [0, 1]
状态: 通过 ✓

所有测试用例通过！`;

        outputContent.textContent = output;
        outputContent.style.color = '#10b981';
    }, 500);
}

function submitCode() {
    const outputContent = document.getElementById('output-content');

    outputContent.textContent = '正在提交...\n\n';

    setTimeout(() => {
        outputContent.textContent = `提交结果: 解答正确！✓

执行用时: 48 ms
内存消耗: 14.2 MB
击败: 95.23% 的用户`;

        outputContent.style.color = '#10b981';

        // Update problem status to solved
        const activeItem = document.querySelector('.problem-item.active');
        const status = activeItem?.querySelector('.problem-status');
        if (status) {
            status.classList.add('solved');
        }
    }, 1000);
}

function resetCode() {
    const codeInput = document.getElementById('code-input');
    codeInput.value = `def two_sum(nums, target):
    """
    :type nums: List[int]
    :type target: int
    :rtype: List[int]
    """
    # 在此编写你的代码
    pass

# 测试用例
print(two_sum([2, 7, 11, 15], 9))  # 输出: [0, 1]`;
}

// ============================================
// Language Select
// ============================================
function initLanguageSelect() {
    const languageSelect = document.getElementById('language-select');

    languageSelect?.addEventListener('change', function() {
        const language = this.value;
        const editorTitle = document.querySelector('.editor-title');

        const languageNames = {
            'python': 'Python 3',
            'java': 'Java 17',
            'cpp': 'C++17',
            'javascript': 'JavaScript (Node.js)'
        };

        if (editorTitle) {
            editorTitle.textContent = languageNames[language] || language;
        }

        // Reset code template based on language
        resetCode();
    });
}
