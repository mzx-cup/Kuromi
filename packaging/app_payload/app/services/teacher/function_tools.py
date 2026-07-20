"""
Function Calling Tool 定义 — 标准 OpenAI tools 格式

这些工具通过 API 请求的 tools 参数绑定，由 LLM 自主决定调用时机。
用于后台重量级任务：网页搜索、评分、大纲生成、知识库检索、代码执行。
"""

BACKEND_TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "搜索互联网获取最新信息。当需要补充背景知识或回答超出教材范围的问题时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词或问题",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "grade_quiz",
            "description": "对学生的答案进行智能评分。根据题目要求和评分标准给出分数和评语。",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "题目内容"},
                    "user_answer": {"type": "string", "description": "学生的答案"},
                    "total_points": {"type": "integer", "description": "满分值"},
                    "grading_criteria": {"type": "string", "description": "评分要点(可选)"},
                },
                "required": ["question", "user_answer", "total_points"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_course_outline",
            "description": "根据主题生成课程大纲，包含章节结构和知识点。",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "课程主题"},
                    "student_level": {
                        "type": "string",
                        "enum": ["beginner", "intermediate", "advanced"],
                        "description": "学生水平",
                    },
                    "chapter_count": {"type": "integer", "description": "章节数量(默认5)"},
                },
                "required": ["topic"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "在本地教材知识库中检索相关知识点。用于引用权威教材内容。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "检索关键词"},
                    "top_k": {"type": "integer", "description": "返回结果数量(默认3)"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_code",
            "description": "在沙盒中执行代码并返回结果。用于演示编程概念或验证学生代码。",
            "parameters": {
                "type": "object",
                "properties": {
                    "language": {
                        "type": "string",
                        "enum": ["python", "javascript", "java"],
                        "description": "编程语言",
                    },
                    "code": {"type": "string", "description": "要执行的代码"},
                },
                "required": ["language", "code"],
            },
        },
    },
]
