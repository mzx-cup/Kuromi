"""One-shot helper: re-create the per-course classroom PPT files under
storage/seed/demo/classrooms/ and run the seeder.

Linters in this project keep deleting the classrooms/ directory after each
conversation, so we re-create it whenever we need it.
"""
import json
import os
import sys

BASE = r"c:/Users/ZWC/Downloads/Kuromi-main/Kuromi-main/storage/seed/demo"
CR = os.path.join(BASE, "classrooms")
os.makedirs(CR, exist_ok=True)


def cr(course_id, classroom_id, title, persona, voice, scenes, quiz_pool):
    return {
        "classroom_id": classroom_id,
        "course_id": course_id,
        "title": title,
        "teacher_persona": persona,
        "voice_id": voice,
        "scenes": scenes,
        "quiz_pool": quiz_pool,
    }


# ---------- 5 per-course PPTs ----------
PYTHON_CR = cr(
    "demo_python_101",
    "demo_classroom_python_101",
    "Python 编程入门 · 演示课堂",
    "patient_tutor",
    "female-yujie",
    scenes=[
        {"index": 0, "title": "开场：今天我们学什么？", "type": "intro", "duration_sec": 30,
         "slides": [
             {"id": "py_s1", "layout": "title", "title": "Python 编程入门", "subtitle": "演示课堂 · Star-Learn"},
             {"id": "py_s2", "layout": "agenda", "title": "本节内容", "items": ["Python 历史与特点", "环境搭建", "应用领域", "第一个程序"]}
         ],
         "speech": "同学们好，今天我们来认识 Python。它是当前最受欢迎的编程语言之一，让我们先了解它的诞生与特点。",
         "actions": []},
        {"index": 1, "title": "Python 的三大特点", "type": "concept", "duration_sec": 180,
         "slides": [
             {"id": "py_s3", "layout": "list", "title": "三大特点",
              "items": ["解释型：无需编译", "动态类型：自动推断", "跨平台：三大系统通吃"]},
             {"id": "py_s4", "layout": "callout", "title": "Python 之禅",
              "text": "优美胜于丑陋，明了胜于隐晦。", "tone": "info"},
             {"id": "py_s5", "layout": "code", "title": "Hello World",
              "code": "print('Hello, Star-Learn!')", "lang": "python"}
         ],
         "speech": "Python 有三大显著特点：解释型、动态类型、跨平台。",
         "actions": ["spotlight:py_s4"]},
        {"index": 2, "title": "变量与数据类型", "type": "concept", "duration_sec": 200,
         "slides": [
             {"id": "py_s6", "layout": "code", "title": "创建变量",
              "code": "name = 'xiaoming'\nage = 18\nprint(name, age)", "lang": "python"},
             {"id": "py_s7", "layout": "list", "title": "命名规则",
              "items": ["只能字母数字下划线", "不能以数字开头", "区分大小写", "snake_case"]}
         ],
         "speech": "变量是数据的标签。Python 不需要声明类型。", "actions": []},
        {"index": 3, "title": "互动：判断合法变量名", "type": "interactive", "duration_sec": 180,
         "slides": [
             {"id": "py_s8", "layout": "question", "title": "下列哪个合法？",
              "options": ["2var", "_name", "class", "my-var"], "quiz_id": "q_py_var"}
         ],
         "quiz": [{"id": "q_py_var", "question": "合法变量名？",
                   "options": ["2var", "_name", "class", "my-var"], "answer": 1}],
         "speech": "想一想哪个选项合法。", "actions": []},
        {"index": 4, "title": "控制流 if/else", "type": "code", "duration_sec": 200,
         "slides": [
             {"id": "py_s9", "layout": "code", "title": "if/elif/else",
              "code": "score = 85\nif score >= 90:\n    print('A')\nelif score >= 60:\n    print('C')\nelelse:\n    print('F')",
              "lang": "python"}
         ],
         "speech": "条件分支让程序做决策，Python 用缩进定义代码块。", "actions": []},
        {"index": 5, "title": "函数与 OOP", "type": "code", "duration_sec": 200,
         "slides": [
             {"id": "py_s10", "layout": "code", "title": "函数定义",
              "code": "def greet(name):\n    return f'Hi, {name}!'\n\nprint(greet('Star'))",
              "lang": "python"}
         ],
         "speech": "def 定义函数，return 返回值。", "actions": []},
        {"index": 6, "title": "本节小结", "type": "summary", "duration_sec": 60,
         "slides": [
             {"id": "py_s11", "layout": "summary", "title": "本节小结",
              "bullets": ["Python：解释+动态+跨平台", "第一个 print 程序",
                          "变量、命名、数据类型", "下一节：控制流与函数"]}
         ],
         "speech": "今天我们认识了 Python，运行了第一个程序。", "actions": []}
    ],
    quiz_pool=[
        {"id": "q_py_1", "question": "Python 是一门 ___ 语言",
         "options": ["编译型", "解释型", "汇编型"], "answer": 1},
        {"id": "q_py_2", "question": "合法变量名？",
         "options": ["2var", "_name", "class"], "answer": 1},
        {"id": "q_py_3", "question": "Python 之禅第一句？",
         "options": ["简单胜于复杂", "优美胜于丑陋"], "answer": 1}
    ]
)

WEB_CR = cr(
    "demo_web_frontend",
    "demo_classroom_web_frontend",
    "Web 前端基础 · 演示课堂",
    "energetic_lecturer",
    "female-yujie",
    scenes=[
        {"index": 0, "title": "开篇：前端是什么？", "type": "intro", "duration_sec": 40,
         "slides": [
             {"id": "web_s1", "layout": "title", "title": "Web 前端基础", "subtitle": "HTML CSS JavaScript"},
             {"id": "web_s2", "layout": "agenda", "title": "本节内容",
              "items": ["HTML 结构化", "CSS 美化", "JavaScript 交互", "实战"]}
         ],
         "speech": "网页由 HTML、CSS、JavaScript 三件套构成。", "actions": []},
        {"index": 1, "title": "HTML 骨架", "type": "concept", "duration_sec": 200,
         "slides": [
             {"id": "web_s3", "layout": "code", "title": "HTML 结构",
              "code": "<!DOCTYPE html>\n<html>\n<head><title>Page</title></head>\n<body><h1>Hello</h1></body>\n</html>",
              "lang": "html"}
         ],
         "speech": "HTML 是网页骨架。", "actions": []},
        {"index": 2, "title": "CSS 美化", "type": "concept", "duration_sec": 200,
         "slides": [
             {"id": "web_s4", "layout": "code", "title": "Flexbox",
              "code": ".container {\n  display: flex;\n  justify-content: center;\n  align-items: center;\n}",
              "lang": "css"}
         ],
         "speech": "CSS 控制样式，Flexbox 是最常用的布局。", "actions": []},
        {"index": 3, "title": "JavaScript 交互", "type": "code", "duration_sec": 200,
         "slides": [
             {"id": "web_s5", "layout": "code", "title": "点击事件",
              "code": "btn.addEventListener('click', (e) => {\n  console.log('clicked');\n});",
              "lang": "javascript"}
         ],
         "speech": "JS 让网页有生命，事件监听实现交互。", "actions": []},
        {"index": 4, "title": "互动", "type": "interactive", "duration_sec": 120,
         "slides": [
             {"id": "web_s6", "layout": "question", "title": "HTML5 新增标签？",
              "options": ["<div>", "<span>", "<article>"], "quiz_id": "q_web_art"}
         ],
         "quiz": [{"id": "q_web_art", "question": "HTML5 新增标签",
                   "options": ["<div>", "<span>", "<article>"], "answer": 2}],
         "speech": "测验。", "actions": []},
        {"index": 5, "title": "小结", "type": "summary", "duration_sec": 60,
         "slides": [
             {"id": "web_s7", "layout": "summary", "title": "本节小结",
              "bullets": ["HTML 结构", "CSS 样式", "JS 交互", "下一节：综合实战"]}
         ],
         "speech": "今天我们入门了三件套。", "actions": []}
    ],
    quiz_pool=[
        {"id": "q_web_1", "question": "垂直居中方法？",
         "options": ["margin: auto", "flex: center", "padding: 100"], "answer": 1},
        {"id": "q_web_2", "question": "事件方法？",
         "options": ["onclick", "addEventListener", "bind"], "answer": 1}
    ]
)

DS_CR = cr(
    "demo_data_structures",
    "demo_classroom_data_structures",
    "数据结构与算法 · 演示课堂",
    "expert_mentor",
    "male-yin",
    scenes=[
        {"index": 0, "title": "开场", "type": "intro", "duration_sec": 40,
         "slides": [
             {"id": "ds_s1", "layout": "title", "title": "数据结构与算法", "subtitle": "从理论到实践"},
             {"id": "ds_s2", "layout": "agenda", "title": "本节内容",
              "items": ["大 O 表示法", "数组 vs 链表", "栈与队列", "排序算法"]}
         ],
         "speech": "数据结构是程序的骨架，算法是程序的灵魂。", "actions": []},
        {"index": 1, "title": "大 O 复杂度", "type": "concept", "duration_sec": 200,
         "slides": [
             {"id": "ds_s3", "layout": "table", "title": "常见复杂度",
              "headers": ["复杂度", "n=1000"],
              "rows": [["O(1)", "1"], ["O(log n)", "10"],
                       ["O(n)", "1000"], ["O(n^2)", "1000000"]],
              "icon": "chart"}
         ],
         "speech": "大 O 描述算法随输入规模增长的趋势。", "actions": []},
        {"index": 2, "title": "数组 vs 链表", "type": "concept", "duration_sec": 180,
         "slides": [
             {"id": "ds_s4", "layout": "table", "title": "对比",
              "headers": ["操作", "数组", "链表"],
              "rows": [["随机访问", "O(1)", "O(n)"], ["头部插入", "O(n)", "O(1)"]]}
         ],
         "speech": "数组访问快，链表增删快。", "actions": []},
        {"index": 3, "title": "快速排序", "type": "code", "duration_sec": 240,
         "slides": [
             {"id": "ds_s5", "layout": "code", "title": "快速排序",
              "code": "def qsort(a):\n    if len(a)<=1: return a\n    p = a[len(a)//2]\n    return qsort([x for x in a if x<p]) + [x for x in a if x==p] + qsort([x for x in a if x>p])",
              "lang": "python"}
         ],
         "speech": "快速排序，平均 O(n log n)。", "actions": []},
        {"index": 4, "title": "互动", "type": "interactive", "duration_sec": 120,
         "slides": [
             {"id": "ds_s6", "layout": "question", "title": "二分搜索前提？",
              "options": ["数组无序", "数组已排序", "数组很大"], "quiz_id": "q_ds_bin"}
         ],
         "quiz": [{"id": "q_ds_bin", "question": "二分搜索前提？",
                   "options": ["数组无序", "数组已排序", "数组很大"], "answer": 1}],
         "speech": "想一想。", "actions": []},
        {"index": 5, "title": "小结", "type": "summary", "duration_sec": 60,
         "slides": [
             {"id": "ds_s7", "layout": "summary", "title": "本节小结",
              "bullets": ["大 O 表示法", "数组 vs 链表", "栈 LIFO / 队列 FIFO", "快速排序"]}
         ],
         "speech": "今天入门了 DS&A。", "actions": []}
    ],
    quiz_pool=[
        {"id": "q_ds_1", "question": "链表头部插入复杂度？",
         "options": ["O(1)", "O(n)", "O(log n)"], "answer": 0},
        {"id": "q_ds_2", "question": "栈的应用？",
         "options": ["排队", "括号匹配", "排序"], "answer": 1}
    ]
)

AI_CR = cr(
    "demo_ai_intro",
    "demo_classroom_ai_intro",
    "人工智能导论 · 演示课堂",
    "expert_mentor",
    "female-yujie",
    scenes=[
        {"index": 0, "title": "开场", "type": "intro", "duration_sec": 40,
         "slides": [
             {"id": "ai_s1", "layout": "title", "title": "人工智能导论", "subtitle": "从图灵测试到 GPT"},
             {"id": "ai_s2", "layout": "agenda", "title": "本节内容",
              "items": ["AI 定义", "机器学习", "深度学习", "LLM"]}
         ],
         "speech": "今天走进 AI 世界。", "actions": []},
        {"index": 1, "title": "AI 三次浪潮", "type": "concept", "duration_sec": 200,
         "slides": [
             {"id": "ai_s3", "layout": "list", "title": "发展历程",
              "items": ["1950s 符号主义", "1990s 机器学习", "2010s 深度学习", "2022 ChatGPT"]}
         ],
         "speech": "AI 经历了三次浪潮。", "actions": []},
        {"index": 2, "title": "机器学习", "type": "concept", "duration_sec": 200,
         "slides": [
             {"id": "ai_s4", "layout": "table", "title": "三类学习",
              "headers": ["类型", "数据", "任务"],
              "rows": [["监督", "(x,y)", "分类/回归"], ["无监督", "仅x", "聚类"], ["强化", "交互", "游戏"]]}
         ],
         "speech": "机器学习三大范式。", "actions": []},
        {"index": 3, "title": "深度学习", "type": "concept", "duration_sec": 200,
         "slides": [
             {"id": "ai_s5", "layout": "code", "title": "PyTorch",
              "code": "import torch\nmodel = torch.nn.Sequential(\n  torch.nn.Linear(784, 128),\n  torch.nn.ReLU(),\n  torch.nn.Linear(128, 10)\n)",
              "lang": "python"}
         ],
         "speech": "深度学习是神经网络的堆叠。", "actions": []},
        {"index": 4, "title": "LLM 演进", "type": "concept", "duration_sec": 180,
         "slides": [
             {"id": "ai_s6", "layout": "list", "title": "关键里程碑",
              "items": ["2017 Transformer", "2020 GPT-3 175B", "2022 ChatGPT", "2023 GPT-4"]}
         ],
         "speech": "LLM 改变行业。", "actions": []},
        {"index": 5, "title": "小结", "type": "summary", "duration_sec": 60,
         "slides": [
             {"id": "ai_s7", "layout": "summary", "title": "本节小结",
              "bullets": ["AI 三次浪潮", "三大范式", "深度学习", "LLM"]}
         ],
         "speech": "恭喜入门 AI！", "actions": []}
    ],
    quiz_pool=[
        {"id": "q_ai_1", "question": "图灵测试哪一年？",
         "options": ["1940", "1950", "1960"], "answer": 1},
        {"id": "q_ai_2", "question": "Transformer 核心？",
         "options": ["卷积", "自注意力", "循环"], "answer": 1}
    ]
)

LA_CR = cr(
    "demo_linear_algebra",
    "demo_classroom_linear_algebra",
    "线性代数精讲 · 演示课堂",
    "socratic_questioner",
    "male-yin",
    scenes=[
        {"index": 0, "title": "开场", "type": "intro", "duration_sec": 40,
         "slides": [
             {"id": "la_s1", "layout": "title", "title": "线性代数精讲", "subtitle": "机器学习的数学基石"},
             {"id": "la_s2", "layout": "agenda", "title": "本节内容",
              "items": ["向量", "矩阵", "行列式", "SVD"]}
         ],
         "speech": "今天开启线性代数学习。", "actions": []},
        {"index": 1, "title": "向量", "type": "concept", "duration_sec": 180,
         "slides": [
             {"id": "la_s3", "layout": "diagram", "title": "向量可视化",
              "text": "v=(3,4) 是从原点到(3,4)的箭头"},
             {"id": "la_s4", "layout": "list", "title": "运算",
              "items": ["加法", "数乘", "点积", "模长"]}
         ],
         "speech": "向量既有大小又有方向。", "actions": []},
        {"index": 2, "title": "矩阵", "type": "concept", "duration_sec": 200,
         "slides": [
             {"id": "la_s5", "layout": "code", "title": "NumPy",
              "code": "import numpy as np\nA = np.array([[1,2],[3,4]])\nB = np.array([[5,6],[7,8]])\nC = A @ B",
              "lang": "python"}
         ],
         "speech": "矩阵的本质是线性变换。", "actions": []},
        {"index": 3, "title": "特征值与 SVD", "type": "concept", "duration_sec": 180,
         "slides": [
             {"id": "la_s6", "layout": "code", "title": "特征值",
              "code": "import numpy as np\nw, v = np.linalg.eig(np.array([[4,1],[2,3]]))",
              "lang": "python"}
         ],
         "speech": "特征值描述主方向缩放，SVD 更一般。", "actions": []},
        {"index": 4, "title": "互动", "type": "interactive", "duration_sec": 120,
         "slides": [
             {"id": "la_s7", "layout": "question", "title": "何时矩阵可逆？",
              "options": ["det=0", "det≠0", "非方阵"], "quiz_id": "q_la_inv"}
         ],
         "quiz": [{"id": "q_la_inv", "question": "何时矩阵可逆？",
                   "options": ["det=0", "det≠0", "非方阵"], "answer": 1}],
         "speech": "想一想。", "actions": []},
        {"index": 5, "title": "小结", "type": "summary", "duration_sec": 60,
         "slides": [
             {"id": "la_s8", "layout": "summary", "title": "本节小结",
              "bullets": ["向量", "矩阵", "特征值", "SVD"]}
         ],
         "speech": "今天我们入门了线性代数。", "actions": []}
    ],
    quiz_pool=[
        {"id": "q_la_1", "question": "正交点积？",
         "options": ["1", "0", "-1"], "answer": 1},
        {"id": "q_la_2", "question": "SVD 适用？",
         "options": ["仅方阵", "任意矩阵", "对称矩阵"], "answer": 1}
    ]
)

# Write all 5 files
for name, data in [
    ("python_101.json", PYTHON_CR),
    ("web_frontend.json", WEB_CR),
    ("data_structures.json", DS_CR),
    ("ai_intro.json", AI_CR),
    ("linear_algebra.json", LA_CR),
]:
    p = os.path.join(CR, name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"wrote {p} ({len(data['scenes'])} scenes, "
          f"{len(data['quiz_pool'])} quizzes)")
