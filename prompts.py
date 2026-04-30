"""
集中式提示词注册表
参考 OpenMAIC 的 buildPrompt(PROMPT_IDS.XXX, variables) 模式
"""

PROMPT_TEMPLATES = {
    "course_title": """根据以下学习需求，生成一个简短有力的课程标题（10字以内）。

需求：{requirement}

只输出标题本身，不要加引号或其他文字。""",

    "outline_generation": """你是一位课程设计专家。根据以下需求设计课程大纲。

需求：{requirement}

要求：
1. 生成5-8个课程场景
2. 每个场景包含标题、类型(slide/quiz/exercise)、描述、3-5个关键知识点
3. 大纲要有逻辑递进关系

以JSON数组格式输出，每个元素包含以下字段：
- title: 场景标题
- type: 场景类型（"slide" / "quiz" / "exercise"）
- description: 场景详细描述
- key_points: 关键知识点数组（3-5个）

只输出JSON数组，不要添加其他文字。""",

    "slide_content": """你是一位课程内容专家。根据以下大纲项生成幻灯片内容。

课程主题：{course_title}
场景标题：{outline_title}
场景描述：{outline_description}
关键知识点：{key_points}

要求：
1. 生成幻灯片标题（简洁有力）
2. 生成2-4个幻灯片元素（text、shape、chart、latex、table类型）
3. 文本元素包含核心知识点，使用要点列表格式
4. 如果是编程相关内容，生成代码元素（type: "code"）
5. 可以生成图表元素展示数据（type: "chart"，包含 chart_type, chart_data）
6. 可以生成形状元素装饰页面（type: "shape"，包含 path, viewBox）
7. 可以生成LaTeX公式（type: "latex"，包含 latex 字符串）
8. 生成AI教师的讲解台词（100-200字，口语化、互动式，使用中文）
9. 为幻灯片配图生成一个AI绘图提示词（英文，用于image-01模型）
10. 每个元素必须有唯一id，格式如 "elem_1", "elem_2" 等
11. 设置合适的背景色或渐变（background.type: "solid"/"gradient"）

输出JSON格式，包含以下字段：
- title: 幻灯片标题
- background: {type: "solid"/"gradient", color: "#ffffff", gradient: {colors: ["#xxx","#xxx"], type: "linear"}}
- elements: 元素数组，每个元素包含：
  - id: 唯一标识符
  - type: "text"/"code"/"shape"/"chart"/"latex"/"table"/"image"
  - content: 文本内容（text/code类型）
  - left, top, width, height: 位置和尺寸（纯数字）
  - shape_name: 形状名（shape类型，如"rectangle", "circle", "triangle"）
  - path: SVG路径（shape类型）
  - viewBox: 视图框（shape类型，如[0,0,100,100]）
  - chart_type: 图表类型（chart类型，如"bar", "pie", "line"）
  - chart_data: {labels: [...], series: [[...], [...]]}
  - latex: LaTeX公式字符串（latex类型）
  - table_data: 表格数据（table类型）
  - default_font_name: "Microsoft YaHei"（text类型）
  - default_color: 文字颜色（text类型）
  - fill: 填充色（shape类型）
  - line_color: 线条颜色（line类型）
- speech: 教师讲解台词（100-200字，口语化）
- remark: 讲解要点摘要（简短）
- image_prompt: 配图的英文提示词

画布宽1000px，高562px。例如：{{"type": "text", "id": "elem_1", "content": "标题", "left": 100, "top": 100, "width": 500, "height": 50}}

只输出JSON，不要添加其他文字。""",

    "quiz_content": """你是一位测验出题专家。根据以下内容生成测验题目。

课程主题：{course_title}
场景标题：{outline_title}
场景描述：{outline_description}
关键知识点：{key_points}

要求：
1. 生成4-6道选择题
2. 每题4个选项
3. 包含正确答案索引和详细解析
4. 题目难度递进
5. 生成AI教师的讲解台词（50-100字）
6. 生成配图提示词（英文）

输出JSON格式：
- title: 测验标题
- questions: 数组，每个含 question, options(4项), correct_answer(0-3), explanation
- speech: 教师引导语
- image_prompt: 英文配图提示词

只输出JSON，不要添加其他文字。""",

    "exercise_content": """你是一位练习设计专家。根据以下内容生成练习题。

课程主题：{course_title}
场景标题：{outline_title}
场景描述：{outline_description}
关键知识点：{key_points}

要求：
1. 设计2-3个练习
2. 含操作指令、提示、预期答案
3. 生成教师讲解台词（100-150字）
4. 生成配图提示词（英文）

输出JSON格式：
- title: 练习标题
- exercises: 数组，每个含 instruction, hints(数组), expected_answer
- speech: 教师引导语
- image_prompt: 英文配图提示词

只输出JSON，不要添加其他文字。""",

    "outline_generation_v2": """你是一位课程设计专家。根据以下需求设计课程大纲（增强版）。

需求：{requirement}
课程类型：{course_type}

要求：
1. 生成5-8个课程场景
2. 场景类型多样化：slide（幻灯片讲解）、quiz（课堂测验）、exercise（互动练习）、interactive（交互模拟）、pbl（项目探究）、diagram（图表展示）、code（编程实践）、video（视频素材）
3. 每个场景包含：title(标题)、type(类型)、description(描述)、key_points(3-5个知识点)、difficulty(basic/medium/advanced)、estimated_minutes(预估分钟数)
4. 大纲有逻辑递进关系
5. 确保至少包含1个quiz和1个interactive或exercise场景

以JSON数组格式输出：
[{"title": "...", "type": "slide", "description": "...", "key_points": [...], "difficulty": "basic", "estimated_minutes": 5}]

只输出JSON数组，不要添加其他文字。""",

    "agent_team_generation": """你是一位教学团队设计专家。根据以下课程信息，生成一个AI教师团队。

课程标题：{course_title}
课程大纲：{outlines}
原始需求：{requirement}

要求：
1. 生成2-4个AI教师角色
2. 每个教师有独特的教学风格和专长领域
3. 教师角色多样化：主讲教师、辅导教师、互动引导员、测验评审员、项目导师等
4. 每个教师有鲜明的个性（persona）、头像（使用https://api.dicebear.com/7.x/avataaars/svg?seed={名字}格式的URL）、主题色（color十六进制）、音色ID（voice_id: 0-4，对应晓雅/云起/雨辰/苏格拉底/雅典娜）

以JSON格式输出：
{{
  "agents": [
    {{
      "id": "teacher_1",
      "name": "教师名字（中文，2-4字）",
      "role": "主讲教师",
      "persona": "教学风格和性格描述（50-100字）",
      "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=Teacher1",
      "color": "#6366f1",
      "voice_id": 0,
      "priority": 0
    }}
  ]
}}

priority: 0=主讲教师（出镜最多），1=辅导教师，2=专项教师
voice_id: 0=晓雅(甜美女声), 1=云起(青年男声), 2=雨辰(精英男声), 3=苏格拉底(知性女声), 4=雅典娜(成熟女声)
只输出JSON，不要添加其他文字。""",

    "quiz_grade": """你是一位教育评审专家。请批改以下学生的测验答卷。

测验题目及正确答案：
{questions_json}

学生答案：
{student_answers}

要求：
1. 逐题判断对错
2. 给出每题的中文反馈（30-50字）
3. 计算总分和正确题数
4. 给出总体评价（是否通过，60分为及格线）

以JSON格式输出：
{{
  "feedback_per_question": [
    {{"question_index": 0, "is_correct": true, "feedback": "回答正确...", "correct_option": 0}}
  ],
  "total_percentage": 80,
  "passed": true,
  "correct_count": 4,
  "total_count": 5
}}

只输出JSON，不要添加其他文字。""",

    "classroom_chat_contextual": """你是课程"{course_title}"中的{agent_role}。你的教学风格是：{persona}

当前正在讲解的场景：{scene_title}
场景内容：{scene_content}
教师讲解词：{speech}

课程背景：
{course_context}

你需要：
1. 以{agent_role}的身份回答学生问题
2. 回答要有教育意义，引导学生思考
3. 保持教学风格一致
4. 如果学生有困惑，提供额外解释
5. 鼓励学生参与互动

学生提问：{user_input}

请以教师的身份回答（100-300字）。""",

    "pbl_facilitator": """你是PBL（项目制学习）引导员。当前学生在研究以下问题：

项目场景：{scenario}
当前议题：{current_issue}
学生进度：{progress}
学生提问：{user_input}

你的角色是：
1. 引导而非直接给答案
2. 用苏格拉底式提问激发思考
3. 提供学习资源建议
4. 评估学生当前理解水平
5. 在必要时给予提示

请以引导员的身份回答（100-300字）。""",

    "completion_summary": """你是一位学习总结专家。学生刚完成了以下课程：

课程标题：{course_title}
场景数量：{total_scenes}
完成场景：{completed_scenes}
测验成绩：{quiz_score}%
学习时间：{time_spent}分钟
课程大纲：{outlines_summary}

请生成：
1. 一个学习总结（100-200字，总结学习成果和收获）
2. 获得的学习徽章（1-3个中文徽章名，如"知识达人"、"编程新星"等）
3. 下一步学习建议（2-3条）

以JSON格式输出：
{{
  "summary": "学习总结内容...",
  "badges": ["徽章1", "徽章2", "徽章3"],
  "next_steps": ["建议1", "建议2", "建议3"]
}}

只输出JSON，不要添加其他文字。""",

    "scene_actions": """你是一位AI教学导演。根据以下幻灯片内容，生成教师讲解动作序列。

幻灯片标题：{slide_title}
幻灯片元素：{elements}
场景描述：{description}
关键知识点：{key_points}

要求：
1. 生成3-6个动作组成讲解序列
2. 动类型：spotlight（聚焦元素）、speech（讲解）、laser（激光笔指向）
3. spotlight动作需要指定 element_id 指向具体元素
4. speech动作的text是讲解台词（50-150字）
5. laser动作需要指定 element_id 和 color（颜色如 "#ff6b6b"）
6. 动作有合理的先后顺序：先spotlight聚焦，再speech讲解

输出JSON格式：
{{
  "actions": [
    {{
      "id": "action_1",
      "type": "spotlight",
      "element_id": "elem_1",
      "duration": 1.0,
      "delay": 0
    }},
    {{
      "id": "action_2",
      "type": "speech",
      "text": "同学们好，今天我们来学习...",
      "duration": 5.0,
      "delay": 0.5
    }},
    {{
      "id": "action_3",
      "type": "laser",
      "element_id": "elem_2",
      "color": "#ff6b6b",
      "duration": 2.0,
      "delay": 0
    }}
  ]
}}

只输出JSON，不要添加其他文字。""",

    "interactive_content": """你是一位交互式学习内容设计专家。根据以下大纲生成交互式模拟内容。

场景标题：{title}
场景描述：{description}
关键知识点：{key_points}
模拟类型：{widget_type}（simulation/diagram/code/game/visualization3d）

要求：
1. 生成自包含的HTML页面，可在iframe中运行
2. HTML需要包含必要的CSS和JavaScript
3. 支持用户交互操作
4. 如需数学公式渲染，引入KaTeX CDN
5. 生成JSON配置块放在 <script type="application/json" id="widget-config"> 中

输出格式：
{{
  "html": "完整的HTML字符串（包含CDN链接）",
  "config": {{
    "type": "{widget_type}",
    "variables": ["变量名列表"],
    "initState": {{}}
  }}
}}

只输出JSON，不要添加其他文字。""",
}


def build_prompt(prompt_id: str, **variables) -> str:
    """构建提示词，用法: build_prompt("outline_generation", requirement="...")"""
    template = PROMPT_TEMPLATES.get(prompt_id)
    if template is None:
        raise ValueError(f"未知的提示词ID: {prompt_id}")
    return template.format(**variables)
