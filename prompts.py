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

【重要】文字内容要求：
- 文本元素content字段必须是完整的句子或段落，不能只是关键词
- 每个文本元素content至少包含50-200个中文字符
- 使用完整的句子描述知识点，包含主谓宾结构
- 避免使用"概念：xxx"这种简短格式，改用"xxx是一种yyy，它的特点是..."
- 每个关键知识点需要3-5句话的详细解释

【视觉风格】
- 背景：纯白色或极浅灰色（#FFFFFF 或 #F8FAFC）
- 布局：信息图卡片式，用彩色圆角色块横向分区
- 配色：柔和多彩（深蓝#1E40AF + 浅蓝#DBEAFE + 暖黄#FEF3C7 + 绿#D1FAE5）
- 排版：一个色块只承载一个小主题，拒绝大字堆叠式标题

【页面结构（必须严格遵循）】
- 顶部标题条：深蓝色(#1E40AF)通栏，白色大号标题文字，元素id如"title-bar"，fill="#1E40AF"，width=1000，height=70
- 左侧浅蓝卡片：浅蓝色(#DBEAFE)圆角矩形，放概念解释+配图说明，元素id如"left-card"，left=30，top=85，width=420，height=380，fill="#DBEAFE"，border_radius=16
- 右侧暖黄卡片：暖黄色(#FEF3C7)圆角矩形，放规则/要点列表（带编号图标），元素id如"right-card"，left=465，top=85，width=505，height=380，fill="#FEF3C7"，border_radius=16
- 底部绿色宽卡片：绿色(#D1FAE5)宽横条，分列展示代码示例或类型说明，元素id如"bottom-card"，left=30，top=480，width=940，height=75，fill="#D1FAE5"，border_radius=12

【Markdown内容格式】
content字段可以使用以下markdown标记来组织富文本内容：
- `## 二级标题`（用于小节标题，在left-card-text或right-card-text中使用）
- `**粗体文字**`（用于重点强调）
- `- 列表项`（用于要点列表，每行一个，以-开头）
- ```python\n代码内容\n```（用于代码块，指定语言名）
- `> 引用文字`（用于引用框）

【布局坐标参考（画布1000×562px）】
- 标题条：left=0, top=0, width=1000, height=70
- 左侧浅蓝卡片：left=30, top=85, width=420, height=380
- 右侧暖黄卡片：left=465, top=85, width=505, height=380
- 底部绿色卡片：left=30, top=480, width=940, height=75
- 左上角小装饰圆形：left=20, top=20, width=30, height=30, fill="#FBBF24"（金黄色）
- 右侧小装饰：可用shape画圆形或矩形点缀

【文字颜色规范】
- 标题条文字：#FFFFFF（白色），font_size=28，font_weight=bold
- 左卡片标题：#1E40AF（深蓝），font_size=18
- 左卡片正文：#1E293B（深灰），font_size=14，line_height=1.8
- 右卡片标题：#92400E（深棕黄），font_size=18
- 右卡片正文：#78350F（棕色），font_size=14
- 底栏文字：#065F46（深绿），font_size=13
- 代码示例：深色背景#1E293B配白色代码文字

【元素类型要求】
1. 背景形状用shape类型：矩形fill对应颜色，border-radius通过CSS类控制
2. 标题用text类型：大型白色文字
3. 正文用text类型：包含完整段落的详细解释（每段50字以上）
4. 代码用code类型：深色背景配白色代码，height>=80px
5. 列表项用text类型：带编号或图标前缀，如"① 变量是存储数据的容器"
6. 每个主要区域至少包含2个以上子元素

生成JSON格式：
{{
  "title": "幻灯片标题",
  "background": {{"type": "solid", "color": "#FFFFFF"}},
  "theme": {{"themeColors": ["#1E40AF", "#DBEAFE", "#FEF3C7", "#D1FAE5"], "fontColor": "#1E293B", "backgroundColor": "#FFFFFF", "fontName": "Microsoft YaHei"}},
  "elements": [
    {{"id": "title-bar", "type": "text", "content": "大标题文字", "left": 0, "top": 0, "width": 1000, "height": 70, "fill": "#1E40AF", "default_color": "#FFFFFF", "font_size": 28, "font_weight": "bold"}},
    {{"id": "left-card-bg", "type": "shape", "shape_name": "rectangle", "left": 30, "top": 85, "width": 420, "height": 380, "fill": "#DBEAFE", "border_radius": 16}},
    {{"id": "left-card-title", "type": "text", "content": "## 什么是变量？", "left": 50, "top": 95, "width": 380, "height": 30, "fill": "transparent", "default_color": "#1E40AF", "font_size": 18, "font_weight": "bold"}},
    {{"id": "left-card-text", "type": "text", "content": "**变量**是编程中用于存储数据的容器。你可以把它想象成一个带有标签的盒子，\\n每个盒子上贴着一个名字（变量名），里面装着具体的数据（值）。\\n\\n例如：`name = \\"Alice\\"`表示创建一个名为name的盒子，里面存放了字符串Alice。\\n\\n- 变量需要先声明后使用\\n- 同一个变量可以多次赋值，每次会覆盖旧值", "left": 50, "top": 135, "width": 380, "height": 320, "fill": "transparent", "default_color": "#1E293B", "font_size": 14, "line_height": 1.8}},
    {{"id": "right-card-bg", "type": "shape", "shape_name": "rectangle", "left": 465, "top": 85, "width": 505, "height": 380, "fill": "#FEF3C7", "border_radius": 16}},
    {{"id": "right-card-title", "type": "text", "content": "## 变量命名规范", "left": 485, "top": 95, "width": 465, "height": 30, "fill": "transparent", "default_color": "#92400E", "font_size": 18, "font_weight": "bold"}},
    {{"id": "right-card-list", "type": "text", "content": "① 名称可以包含字母、数字和下划线\\n② 必须以字母或下划线开头，不能以数字开头\\n③ **区分大小写**，age和Age是两个不同的变量\\n④ 不能使用Python保留字（如if、for、class等）\\n⑤ 建议使用有意义的名称，如user_name优于xn", "left": 485, "top": 135, "width": 465, "height": 320, "fill": "transparent", "default_color": "#78350F", "font_size": 14, "line_height": 2.0}},
    {{"id": "bottom-card-bg", "type": "shape", "shape_name": "rectangle", "left": 30, "top": 480, "width": 940, "height": 75, "fill": "#D1FAE5", "border_radius": 12}},
    {{"id": "bottom-card-text", "type": "text", "content": "```python\\nname = \\"Alice\\"   # 字符串\\nage = 18         # 整数\\nprice = 19.99   # 浮点数\\n```", "left": 50, "top": 490, "width": 900, "height": 55, "fill": "transparent", "default_color": "#065F46", "font_size": 13}}
  ],
  "speech": "教师讲解台词150-300字，口语化互动式，包含引入、讲解、总结",
  "remark": "讲解要点摘要",
  "image_prompt": "配图英文提示词"
}}

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
[{{"title": "...", "type": "slide", "description": "...", "key_points": [...], "difficulty": "basic", "estimated_minutes": 5}}]

只输出JSON数组，不要添加其他文字。""",

    "outline_generation_v3": """你是一位课程设计专家。根据以下需求设计课程大纲（最终版）。

需求：{requirement}
课程类型：{course_type}

要求：
1. 生成5-8个课程场景
2. 场景类型多样化：slide（幻灯片讲解）、quiz（课堂测验）、exercise（互动练习）、interactive（交互模拟）、pbl（项目探究）、diagram（图表展示）、code（编程实践）、video（视频素材）
3. 每个场景包含：
   - title: 标题（简短有力，8字以内）
   - type: 类型（必须是以上8种之一）
   - description: 详细描述（30-50字，包含具体场景/问题/情境）
   - key_points: 3-5个关键知识点（每个15-30字）
   - difficulty: basic/medium/advanced
   - estimated_minutes: 预估分钟数（3-10分钟）
4. interactive场景需要有具体的widget_type（simulation/diagram/code/game/visualization3d）
5. pbl场景需要有具体的scenario（真实世界问题场景描述）
6. 至少包含1个quiz和1个interactive或exercise场景
7. 确保quiz场景有足够的知识点支撑题目设计

以JSON数组格式输出：
[{{"title": "...", "type": "slide", "description": "...", "key_points": [...], "difficulty": "basic", "estimated_minutes": 5, "widget_type": null, "scenario": null}}]

只输出JSON数组，不要添加其他文字。""",

    "pbl_content": """你是一位PBL（项目制学习）设计专家。根据以下大纲生成PBL场景内容。

课程主题：{course_title}
场景标题：{outline_title}
场景描述：{outline_description}
关键知识点：{key_points}

要求：
1. 设计一个真实世界的问题场景（scenario），包含背景、挑战和目标
2. 生成3-5个议题（issue_board），每个议题包含标题、问题描述、引导问题
3. 提供工作区配置（workspace）：包含需要用到的工具、数据集或资源链接
4. 生成教师引导台词（100-200字），采用苏格拉底式提问风格
5. 生成配图提示词（英文）

输出JSON格式：
{{
  "title": "PBL场景标题",
  "scenario": "真实世界问题场景描述，包含背景、具体挑战和预期成果",
  "issue_board": [
    {{"title": "议题1标题", "description": "议题具体描述", "guiding_questions": ["引导问题1", "引导问题2"]}}
  ],
  "workspace": {{"tools": [], "resources": [], "constraints": []}},
  "facilitator_speech": "苏格拉底式引导台词...",
  "image_prompt": "英文配图提示词"
}}

只输出JSON，不要添加其他文字。""",

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

    "slide_content_v2": """你是一位课程内容专家。根据以下大纲生成幻灯片内容。

课程主题：{course_title}
场景标题：{outline_title}
场景描述：{outline_description}
关键知识点：{key_points}

【输出格式 - 必须严格遵循】
你必须生成一个JSON对象，包含slides数组。每页幻灯片必须包含：
- layoutType: 布局类型（title-only/two-column/grid-cards/header-content/quote-highlight）
- title: 幻灯片大标题
- content: 内容数组，每个元素包含 subTitle（小标题）、text（正文）、icon（图标名：book|lightbulb|code|check|star|question|warning|info）、colorTheme（色系：blue|yellow|green|purple|orange）、codeSnippet（可选代码）、imageUrl（可选配图）

生成3-5页幻灯片，覆盖以下内容：
1. 概念引入页（建议用 two-column 或 header-content）
2. 知识点讲解页（建议用 grid-cards 展示多个要点）
3. 示例演示页（建议用 two-column 或 quote-highlight）
4. 练习巩固页（可用任意布局）

色系分配：blue用于概念解释，yellow用于规则要点，green用于示例代码，purple用于总结强调

只输出JSON，不要添加其他文字。""",

    "interactive_scene_content": """你是一位沉浸式课程内容专家。根据以下大纲生成互动场景。

课程主题：{course_title}
场景标题：{outline_title}
场景描述：{outline_description}
关键知识点：{key_points}

【输出格式 - 必须严格遵循】
生成一个 JSON 对象，必须包含以下字段：
- id: 场景唯一ID（如 "scene_001"）
- title: 场景标题
- audio_script: AI 教师旁白脚本文本（150-300字，口语化、互动式，包含引入语如"同学们好，今天我们来学习..."）
- components: 组件数组，每个组件必须包含 id、type 以及对应字段

【组件类型 - 仅限以下4种，禁止发明新类型】
1. text_card（图文卡片）：必须包含 title, content, icon, color_theme
2. quiz（互动测验）：必须包含 question, options（含 is_correct 标记正确项）, explanation, quiz_type
3. code_editor（代码沙箱）：必须包含 title, instruction, starter_code, language, expected_output, hints
4. simulation（模拟实验）：必须包含 title, description, html_content

【强制约束】
- type 字段必须 exactly match 以下四种之一："text_card" | "quiz" | "code_editor" | "simulation"
- 禁止使用 type: "exercise"、"task"、"card"、"text"、"interactive" 等变体
- options 数组中每个对象必须包含 key（A/B/C/D）和 text，quiz 组件需标注 is_correct: true/false
- code_editor 的 language 仅支持："python" | "javascript" | "html" | "sql"
- 组件 id 必须唯一，如 "card_001"、"quiz_001"、"code_001"

【场景结构要求】
每个场景必须包含：
- 1-2 个 text_card（用于引入概念、解释知识点）
- 0-1 个 quiz（检验理解）或 0-1 个 code_editor（动手练习），二选一
- 0-1 个 simulation（可视化辅助，可选）
- audio_script 必须与 components 内容对应，形成完整的讲解流程

【示例输出结构】
{{{{
  "id": "scene_001",
  "title": "变量的概念",
  "audio_script": "同学们好！欢迎来到今天的Python课堂。我们今天要学习一个非常重要的概念——变量。变量就像是编程世界的储物盒，它可以存放数据，让我们随时取用。想象一下你的书包里放着课本、文具...变量就是电脑里的'书包'。让我们一起来探索吧！",
  "components": [
    {{
      "id": "card_001",
      "type": "text_card",
      "title": "什么是变量？",
      "content": "**变量**是编程中用于存储数据的容器。\\n\\n可以把变量想象成一个带有标签的盒子：\\n- **变量名**：盒子上贴的标签\\n- **变量值**：盒子里装的东西\\n\\n例如：`name = \\"Alice\\"` 表示创建一个名为 name 的盒子，里面存放了字符串 Alice。",
      "icon": "lightbulb",
      "color_theme": "blue"
    }},
    {{
      "id": "quiz_001",
      "type": "quiz",
      "question": "下面哪个选项正确描述了变量的作用？",
      "options": [
        {{"key": "A", "text": "变量用于存储数据，可以随时修改", "is_correct": true}},
        {{"key": "B", "text": "变量是固定不变的值", "is_correct": false}},
        {{"key": "C", "text": "变量只能存储数字", "is_correct": false}},
        {{"key": "D", "text": "变量必须先声明才能使用", "is_correct": false}}
      ],
      "explanation": "变量最大的特点就是可以存储不同的数据，并且可以随时修改。这是编程灵活性的基础。",
      "quiz_type": "single"
    }}
  ]
}}}}

只输出JSON，不要添加其他文字。"""
}


def build_prompt(prompt_id: str, **variables) -> str:
    """构建提示词，用法: build_prompt("outline_generation", requirement="...")"""
    template = PROMPT_TEMPLATES.get(prompt_id)
    if template is None:
        raise ValueError(f"未知的提示词ID: {prompt_id}")
    return template.format(**variables)
