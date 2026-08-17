"""Re-create extra_courses.json with all 5 courses, 27 chapters, 27 subchapters."""
import json
import os

BASE = r"c:/Users/ZWC/Downloads/Kuromi-main/Kuromi-main/storage/seed/demo"

# All 5 courses
courses = [
    # Python — kept in sync with course.json's single-course template
    {
        "id": "demo_python_101",
        "subject_id": "subj_demo_cs",
        "title": "Python 编程入门",
        "description": "从零开始学习 Python。涵盖变量、控制流、函数、OOP 等核心概念。",
        "author_name": "Star-Learn 演示教师",
        "total_lessons": 6,
        "total_duration": 3600,
        "cover_url": "/static/demo/python_101_cover.svg",
        "sort_order": 0,
        "outlines": [
            {"id": "ol_py_1", "title": "Python 初识与环境搭建", "type": "slide", "points": 3},
            {"id": "ol_py_2", "title": "变量与数据类型", "type": "interactive", "points": 3},
            {"id": "ol_py_3", "title": "运算符与表达式", "type": "interactive", "points": 3},
            {"id": "ol_py_4", "title": "控制流：条件与循环", "type": "code", "points": 4},
            {"id": "ol_py_5", "title": "函数与模块化", "type": "code", "points": 4},
            {"id": "ol_py_6", "title": "面向对象编程入门", "type": "slide", "points": 3},
        ],
    },
    {
        "id": "demo_web_frontend",
        "subject_id": "subj_demo_cs",
        "title": "Web 前端基础：HTML·CSS·JavaScript",
        "description": "学习网页前端三大核心技术：HTML+CSS+JS。",
        "author_name": "Star-Learn 演示教师",
        "total_lessons": 5,
        "total_duration": 4200,
        "cover_url": "/static/demo/web_frontend_cover.svg",
        "sort_order": 1,
        "outlines": [
            {"id": "ol_web_1", "title": "HTML 网页骨架", "type": "slide", "points": 4},
            {"id": "ol_web_2", "title": "CSS 网页样式", "type": "interactive", "points": 4},
            {"id": "ol_web_3", "title": "JavaScript 交互", "type": "code", "points": 5},
            {"id": "ol_web_4", "title": "前端工程化", "type": "slide", "points": 3},
            {"id": "ol_web_5", "title": "综合实战", "type": "code", "points": 4},
        ],
    },
    {
        "id": "demo_data_structures",
        "subject_id": "subj_demo_cs",
        "title": "数据结构与算法基础",
        "description": "系统学习核心数据结构与算法。",
        "author_name": "Star-Learn 演示教师",
        "total_lessons": 6,
        "total_duration": 5400,
        "cover_url": "/static/demo/ds_algo_cover.svg",
        "sort_order": 2,
        "outlines": [
            {"id": "ol_ds_1", "title": "算法复杂度", "type": "slide", "points": 3},
            {"id": "ol_ds_2", "title": "数组与链表", "type": "interactive", "points": 3},
            {"id": "ol_ds_3", "title": "栈与队列", "type": "interactive", "points": 3},
            {"id": "ol_ds_4", "title": "树与二叉树", "type": "slide", "points": 4},
            {"id": "ol_ds_5", "title": "排序算法", "type": "code", "points": 4},
            {"id": "ol_ds_6", "title": "搜索与动态规划", "type": "code", "points": 4},
        ],
    },
    {
        "id": "demo_ai_intro",
        "subject_id": "subj_demo_ai",
        "title": "人工智能导论",
        "description": "了解 AI 基础、发展、机器学习、深度学习与 LLM。",
        "author_name": "Star-Learn 演示教师",
        "total_lessons": 5,
        "total_duration": 4800,
        "cover_url": "/static/demo/ai_intro_cover.svg",
        "sort_order": 0,
        "outlines": [
            {"id": "ol_ai_1", "title": "什么是 AI", "type": "slide", "points": 3},
            {"id": "ol_ai_2", "title": "机器学习基础", "type": "slide", "points": 4},
            {"id": "ol_ai_3", "title": "深度学习与神经网络", "type": "interactive", "points": 4},
            {"id": "ol_ai_4", "title": "NLP 自然语言处理", "type": "interactive", "points": 3},
            {"id": "ol_ai_5", "title": "AI 伦理与未来", "type": "slide", "points": 3},
        ],
    },
    {
        "id": "demo_linear_algebra",
        "subject_id": "subj_demo_math",
        "title": "线性代数精讲",
        "description": "向量、矩阵、特征值与 SVD。",
        "author_name": "Star-Learn 演示教师",
        "total_lessons": 5,
        "total_duration": 4500,
        "cover_url": "/static/demo/linear_algebra_cover.svg",
        "sort_order": 0,
        "outlines": [
            {"id": "ol_la_1", "title": "向量与向量空间", "type": "slide", "points": 3},
            {"id": "ol_la_2", "title": "矩阵与线性变换", "type": "slide", "points": 4},
            {"id": "ol_la_3", "title": "线性方程组", "type": "interactive", "points": 3},
            {"id": "ol_la_4", "title": "行列式与特征值", "type": "interactive", "points": 4},
            {"id": "ol_la_5", "title": "SVD 应用", "type": "slide", "points": 3},
        ],
    },
]

# Chapters
chapter_titles = {
    "demo_python_101": [
        ("Python 初识与环境搭建", "了解 Python 诞生、特点与第一个程序"),
        ("变量与数据类型", "掌握变量命名与六大基本数据类型"),
        ("运算符与表达式", "算术、比较、逻辑运算符与优先级"),
        ("控制流：条件与循环", "if/elif/else 与 for/while"),
        ("函数与模块化", "def 函数、参数、lambda、模块导入"),
        ("面向对象编程入门", "类、继承、封装、多态"),
    ],
    "demo_web_frontend": [
        ("HTML 网页骨架", "文档结构、常用标签、语义化"),
        ("CSS 网页样式", "选择器、盒模型、Flexbox、响应式"),
        ("JavaScript 交互", "DOM 操作、事件处理、异步编程"),
        ("前端工程化", "npm、模块化、打包工具、Git"),
        ("综合实战：个人主页", "HTML/CSS/JS 综合运用"),
    ],
    "demo_data_structures": [
        ("算法复杂度", "大 O 表示法、时间与空间复杂度"),
        ("数组与链表", "连续 vs 分散存储"),
        ("栈与队列", "LIFO / FIFO 与典型应用"),
        ("树与二叉树", "二叉树遍历、BST、堆"),
        ("排序算法", "快速、归并排序与复杂度对比"),
        ("搜索与动态规划", "二分、DFS/BFS、DP 入门"),
    ],
    "demo_ai_intro": [
        ("什么是 AI", "AI 定义、图灵测试、三次浪潮"),
        ("机器学习基础", "监督/无监督/强化学习"),
        ("深度学习与神经网络", "CNN/RNN、反向传播"),
        ("NLP 自然语言处理", "Transformer、GPT 系列"),
        ("AI 伦理与未来", "AI 安全、可解释性、AGI"),
    ],
    "demo_linear_algebra": [
        ("向量与向量空间", "向量的几何意义、线性组合"),
        ("矩阵与线性变换", "矩阵乘法、转置、逆"),
        ("线性方程组", "高斯消元、解的结构"),
        ("行列式与特征值", "行列式几何意义、特征值分解"),
        ("SVD 应用", "奇异值分解与降维"),
    ],
}

prefix_map = {
    "demo_python_101": "py",
    "demo_web_frontend": "web",
    "demo_data_structures": "ds",
    "demo_ai_intro": "ai",
    "demo_linear_algebra": "la",
}

subject_id_map = {c["id"]: c["subject_id"] for c in courses}

chapters = []
subchapters = []
for course_id, chs in chapter_titles.items():
    pre = prefix_map[course_id]
    for i, (title, desc) in enumerate(chs, 1):
        ch_id = f"ch_{pre}_{i}"
        chapters.append({
            "id": ch_id,
            "course_id": course_id,
            "title": title,
            "description": desc,
            "sort_order": i - 1,
            "lecture_ref": f"lecture_{ch_id}",
            "mindmap_ref": f"mindmap_{ch_id}",
        })
        subchapters.append({
            "id": f"sc_{pre}_{i}",
            "chapter_id": ch_id,
            "title": title,
            "type": "slide",
            "duration": 600,
        })

extra_courses = {
    "subjects": [
        {"id": "subj_demo_cs", "name": "计算机科学 (演示)", "slug": "demo-cs",
         "icon": "demo-cs", "visible": True, "sort_order": 0},
        {"id": "subj_demo_ai", "name": "人工智能 (演示)", "slug": "demo-ai",
         "icon": "demo-ai", "visible": True, "sort_order": 10},
        {"id": "subj_demo_math", "name": "数学 (演示)", "slug": "demo-math",
         "icon": "demo-math", "visible": True, "sort_order": 20},
    ],
    "courses": courses,
    "chapters": chapters,
    "subchapters": subchapters,
}

p = os.path.join(BASE, "extra_courses.json")
with open(p, "w", encoding="utf-8") as f:
    json.dump(extra_courses, f, ensure_ascii=False, indent=2)
print(f"wrote {p}")
print(f"  subjects={len(extra_courses['subjects'])}, courses={len(courses)}, "
      f"chapters={len(chapters)}, subchapters={len(subchapters)}")
