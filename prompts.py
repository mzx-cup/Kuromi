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

    "quiz_content": """你是一位测验出题专家。根据以下内容生成3-5道测验题目。

课程主题：{course_title}
场景标题：{outline_title}
场景描述：{outline_description}
关键知识点：{key_points}
{web_search_context}

【难度递进要求 - 必须遵守】
1. 题目必须按难度由简到难排序，每道题必须标注 difficulty 字段（basic/medium/advanced）
2. 难度分布：
   - 基础题（basic）占40%：概念理解、简单回忆，使用单选题
   - 中等题（medium）占40%：简单应用、分析判断，使用单选或多选题
   - 进阶题（advanced）占20%：综合应用、推理判断，使用多选或简答题
3. 禁止一上来就出道难题，第一题必须是基础概念题
4. 题目之间要有逻辑递进：先考"是什么"，再考"怎么用"，最后考"为什么"

【题型要求】
1. 根据内容复杂度动态生成3-5道题目
2. 题型组合：至少包含1道单选题、1道多选题、1道简答题
3. 单选题：4个选项，1个正确答案，5分
4. 多选题：4个选项，2-3个正确答案，8分
5. 简答题：需学生输入文字回答，15分，必须包含参考答案(answer)和评分标准(comment_prompt)
6. 所有题目需包含详细解析(explanation)
7. 生成教师引导语speech（50-100字）：鼓励学生开始答题
8. 输出时带上scene_id字段用于匹配

输出JSON格式：
{{
  "scene_id": {scene_id},
  "title": "测验标题",
  "questions": [
    {{
      "id": 1,
      "question": "基础概念题",
      "question_type": "single",
      "difficulty": "basic",
      "options": ["A选项", "B选项", "C选项", "D选项"],
      "correct_answer": 0,
      "explanation": "答案解析",
      "points": 5
    }},
    {{
      "id": 2,
      "question": "应用分析题",
      "question_type": "multiple",
      "difficulty": "medium",
      "options": ["A选项", "B选项", "C选项", "D选项"],
      "correct_answers": [0, 2],
      "explanation": "答案解析",
      "points": 8
    }},
    {{
      "id": 3,
      "question": "综合挑战题",
      "question_type": "short_answer",
      "difficulty": "advanced",
      "answer": "参考答案",
      "comment_prompt": "评分标准说明",
      "key_points": ["要点1", "要点2", "要点3"],
      "explanation": "答案解析",
      "points": 15
    }}
  ],
  "speech": "教师引导语",
  "difficulty_distribution": {{"basic": 1, "medium": 1, "advanced": 1}}
}}

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

    "exercise_scene_content_v2": """你是一位编程教育练习设计专家。根据以下课程大纲，设计高质量的编程练习场景。

课程主题：{course_title}
场景标题：{outline_title}
场景描述：{outline_description}
关键知识点：{key_points}

【输出格式 - 必须严格遵循】
生成一个 JSON 对象，必须包含以下字段：

1. exercise_data: 练习数据对象
{{
  "title": "练习场景标题",
  "exercises": [
    {{
      "type": "code",
      "language": "python" | "javascript" | "html" | "sql",
      "instruction": "明确的编程任务说明（80-150字）",
      "starter_code": "带有TODO占位符的初始代码",
      "expected_output": "预期运行输出",
      "hints": ["提示1（思路引导）", "提示2（具体方向）", "提示3（接近答案）"],
      "difficulty": "basic" | "medium" | "advanced"
    }},
    {{
      "type": "choice",
      "instruction": "选择题题干",
      "options": ["A. 选项1", "B. 选项2", "C. 选项3", "D. 选项4"],
      "correct_answer": 0,
      "explanation": "答案解析"
    }},
    {{
      "type": "fill_blank",
      "instruction": "填空题题干，用 ___ 表示填空位置",
      "correct_answer": "正确答案",
      "explanation": "解析"
    }},
    {{
      "type": "true_false",
      "instruction": "判断题题干",
      "correct_answer": true,
      "explanation": "解析"
    }}
  ]
}}

2. slides_v2: 1-2 页 V2 格式概念讲解幻灯片（用于"查看讲解"功能）
- 布局类型可选：two-column、header-content、grid-cards
- 每页包含 title 和 content 数组（含 sub_title、bullets、narration、icon、color_theme）

3. speech: AI 教师语音讲解稿（150-250字），用于引入练习场景

【设计原则】
1. 练习类型选择：
   - 如果大纲涉及具体代码技能：优先出 code 类型 + 1个 choice 类型
   - 如果大纲是概念理解：出 choice + fill_blank + true_false 组合
   - 至少包含1个 code 类型（如果是编程课程）
2. code 练习的 starter_code 必须是"填空式"，不能是空白
3. 难度递进：basic → medium → advanced
4. 提示必须由简到难，第一条不给代码

只输出JSON，不要添加其他文字。""",


    "outline_generation_v2": """你是一位课程设计专家。根据以下需求设计课程大纲（增强版）。

需求：{requirement}
课程类型：{course_type}

要求：
1. 生成5-8个课程场景
2. 场景类型多样化：slide（幻灯片讲解）、quiz（课堂测验）、exercise（互动练习）、interactive（交互模拟）、pbl（项目探究）、diagram（图表展示）、code（编程实践）、video（视频素材）、whiteboard（白板绘图）
3. 每个场景包含：title(标题)、type(类型)、description(描述)、key_points(3-5个知识点)、difficulty(basic/medium/advanced)、estimated_minutes(预估分钟数)
4. 大纲有逻辑递进关系
5. 确保至少包含1个quiz和1个interactive或exercise场景

以JSON数组格式输出：
[{{"title": "...", "type": "slide", "description": "...", "key_points": [...], "difficulty": "basic", "estimated_minutes": 5}}]

只输出JSON数组，不要添加其他文字。""",

    "outline_generation_v3": """你是一位课程设计专家。根据以下需求设计课程大纲（最终版）。

需求：{requirement}
课程类型：{course_type}
{suggested_scene_types}
{pdf_text}
要求：
1. 根据内容复杂度决定场景数量，不要硬凑：
   - 简单主题（1-2个核心概念）：5-6个场景
   - 中等主题（3-5个核心概念）：7-9个场景
   - 复杂主题（6个以上核心概念）：10-12个场景
   知识讲完了就停止，不要为了凑数量而拆分已经完整的知识点。
2. 【场景类型智能分配 - 边学边练原则】
   可用类型：slide（幻灯片讲解）、quiz（课堂测验）、exercise（互动练习）、interactive（交互模拟）、pbl（项目探究）、diagram（图表展示）、code（编程实践）、video（视频素材）、whiteboard（白板绘图）

   分配原则：
   a) **绝对禁止** quiz/exercise/interactive/pbl/code 这5种互动型场景连续出现。任意两个互动型场景之间必须至少间隔1个 slide/diagram/video/whiteboard 讲授型场景。
   b) 边学边练模式：每讲授1-2个知识点后，必须插入1个互动场景让学生实践/检验。禁止连续3个及以上讲授型场景不插入互动。
   c) 根据内容特点精准选择场景：
      - 概念引入/理论讲解 → slide
      - 公式推导/图形手绘 → whiteboard
      - 代码演示+动手编程 → code
      - 流程图/架构图/思维导图 → diagram
      - 操作步骤模拟 → interactive
      - 视频演示/案例展示 → video
      - 学完2-3个知识点后检验 → quiz
      - 综合应用/动手实验 → exercise
      - 期末综合项目/真实问题解决 → pbl（仅在课程后半段出现1次）
   d) 课程节奏：前半段以 slide+quiz 为主（建立基础），中间以 code/interactive/exercise 为主（动手实践），后半段以 pbl/exercise 收尾（综合应用）。
   e) video 和 whiteboard 应分散在课程中，每种最多出现1次，用于突破难理解的知识点。

3. 每个场景包含：
   - title: 标题（简短有力，8字以内）
   - type: 类型（必须是以上9种之一）
   - description: 详细描述（30-50字，包含具体场景/问题/情境）
   - key_points: 3-5个关键知识点（每个15-30字）
   - difficulty: basic/medium/advanced
   - estimated_minutes: 预估分钟数（3-10分钟）
4. whiteboard场景适合几何图形、函数图像、流程图等需要手绘演示的内容，description中应包含具体的绘图要求
5. interactive场景需要有具体的widget_type（simulation/diagram/code/game/visualization3d）
6. pbl场景需要有具体的scenario（真实世界问题场景描述）
7. 至少包含1个quiz和1个interactive或exercise场景
8. 确保quiz场景有足够的知识点支撑题目设计
9. 【重要】场景类型分布规则：
   - 严禁连续出现2个或以上非slide类型的场景（如quiz紧接exercise）
   - non-slide类型场景（quiz/exercise/interactive/pbl/diagram/code/video）之间必须至少间隔1个slide场景
   - quiz场景最佳位置是第3-5个场景之间，用于阶段性检测
   - exercise/interactive场景应在slide讲解之后出现，用于巩固练习
   - 如果需要连续生成多个quiz，可以用slide场景作为过渡分隔

以JSON数组格式输出：
[{{"title": "...", "type": "slide", "description": "...", "key_points": [...], "difficulty": "basic", "estimated_minutes": 5, "widget_type": null, "scenario": null}}]

只输出JSON数组，不要添加其他文字。注意检查输出JSON中不存在连续两个非slide场景。""",

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

    "agent_team_generation": """你是一位编程教育平台的教学团队设计专家。本平台的所有课程都是编程/计算机相关，所有教师必须是编程技术领域的专家。

课程标题：{course_title}
课程大纲：{outlines}
原始需求：{requirement}

【重要约束】
1. 本平台是编程学习平台，所有AI教师必须是编程/计算机技术领域的专家，绝对禁止生成历史、文学、艺术、自然科学等非编程学科的教师
2. 教师的专业领域必须与课程内容高度相关：
   - 如果课程涉及Python/数据分析/AI → 生成Python工程师或数据科学家
   - 如果课程涉及Java/Spring/企业开发 → 生成Java架构师或后端工程师
   - 如果课程涉及JavaScript/React/Vue/前端 → 生成前端工程师
   - 如果课程涉及C/C++/数据结构/算法/系统编程 → 生成系统工程师或算法工程师
   - 如果课程涉及全栈/架构/DevOps/数据库 → 生成全栈架构师或DevOps工程师
   - 如果课程内容不明确 → 生成全栈工程师或软件工程师（通用编程导师）
3. 生成2-4个AI教师角色，角色多样化：主讲教师、辅导教师、代码审查员、项目导师等
4. 每个教师有鲜明的编程专家个性（persona），头像（使用https://api.dicebear.com/7.x/avataaars/svg?seed={名字}格式的URL）、主题色（color十六进制）、音色ID（voice_id: 0-4）

以JSON格式输出：
{{
  "agents": [
    {{
      "id": "teacher_1",
      "name": "教师名字（中文，2-4字）",
      "role": "主讲教师",
      "profession": "专业头衔（如：Python高级工程师 / Java架构师 / 前端技术专家）",
      "persona": "教学风格和性格描述（50-100字），必须体现编程技术背景",
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
模拟类型：{widget_type}（simulation/diagram/code/game/visualization3d/terminal）

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

    "interactive_terminal": """你是一位交互式终端模拟器设计专家。请根据以下课程大纲，生成一个Redis/命令行风格的交互式终端模拟器HTML页面。

课程主题：{course_title}
场景标题：{outline_title}
场景描述：{outline_description}
关键知识点：{key_points}

【要求】
1. 生成一个自包含的HTML页面，可在iframe中独立运行
2. 页面必须包含完整的CSS样式和JavaScript逻辑
3. 终端风格：深色背景（#0f172a）、等宽字体、绿色/青色文字（#4ade80/#22d3ee）
4. 模拟一个内存中的键值数据库（类似Redis），支持以下命令：
   - SET key value — 设置键值对
   - GET key — 获取键值
   - DEL key — 删除键
   - EXISTS key — 检查键是否存在
   - KEYS pattern — 查找匹配的键（支持 * 通配符）
   - HSET key field value — 设置哈希字段
   - HGET key field — 获取哈希字段值
   - HGETALL key — 获取哈希所有字段
   - LPUSH key value — 列表左侧插入
   - LRANGE key start stop — 获取列表范围
   - EXPIRE key seconds — 设置键过期时间（模拟）
   - TTL key — 查看键剩余时间
   - HELP — 显示可用命令列表
   - CLEAR — 清屏
5. 提供引导式体验：
   - 首次加载时显示欢迎信息和简短教程
   - 输入错误命令时给出友好提示和建议
   - 预设3-5个与本课程主题相关的示例数据（如课程相关的键值对）
6. 交互细节：
   - 支持方向键上下切换历史命令
   - 支持Tab键自动补全（至少补全命令名）
   - 命令执行后有明确的反馈（成功/失败不同颜色）
   - 显示命令执行时间（模拟）

【输出格式】
{{
  "html": "<!DOCTYPE html><html>...</html> 完整的HTML字符串",
  "widget_type": "terminal",
  "config": {{
    "type": "terminal",
    "commands": ["SET", "GET", "DEL", "EXISTS", "KEYS", "HSET", "HGET", "HGETALL", "LPUSH", "LRANGE", "EXPIRE", "TTL", "HELP", "CLEAR"],
    "init_data": {{}}
  }}
}}

只输出JSON，不要添加其他文字。""",

    "interactive_simulation": """你是一位交互式模拟实验设计专家。根据以下大纲生成模拟实验内容。

课程主题：{course_title}
场景标题：{outline_title}
场景描述：{outline_description}
关键知识点：{key_points}

要求：
1. 生成自包含的HTML页面，可在iframe中运行
2. 包含Canvas或SVG可视化
3. 提供可调节的参数控制面板
4. 实时显示模拟结果和数据
5. 适合教育场景，有明确的教学目标

输出格式：
{{
  "html": "完整的HTML字符串",
  "widget_type": "simulation",
  "config": {{
    "type": "simulation",
    "variables": ["参数名列表"],
    "initState": {{}}
  }}
}}

只输出JSON，不要添加其他文字。""",

    "interactive_diagram": """你是一位交互式图表设计专家。根据以下大纲生成交互式图表内容。

课程主题：{course_title}
场景标题：{outline_title}
场景描述：{outline_description}
关键知识点：{key_points}

要求：
1. 使用Mermaid.js生成可交互的图表
2. 支持流程图、时序图、类图、状态图等
3. 提供图表类型切换或缩放功能
4. 包含图表说明和关键节点解释

输出格式：
{{
  "html": "完整的HTML字符串（包含Mermaid CDN）",
  "widget_type": "diagram",
  "config": {{
    "type": "diagram",
    "diagram_type": "flowchart|sequence|class|state"
  }}
}}

只输出JSON，不要添加其他文字。""",

    "interactive_game": """你是一位教育游戏设计专家。根据以下大纲生成记忆配对或知识问答游戏。

课程主题：{course_title}
场景标题：{outline_title}
场景描述：{outline_description}
关键知识点：{key_points}

要求：
1. 生成自包含的HTML页面，可在iframe中运行
2. 游戏类型：记忆配对卡（翻牌匹配）或知识问答闯关
3. 使用与本课程相关的知识点作为游戏内容
4. 包含计分、计时、关卡进度
5. 有清晰的胜利条件和反馈

输出格式：
{{
  "html": "完整的HTML字符串",
  "widget_type": "game",
  "config": {{
    "type": "game",
    "game_type": "memory|quiz",
    "pairs": [{{"q": "问题", "a": "答案"}}]
  }}
}}

只输出JSON，不要添加其他文字。""",


    "slide_content_v2": """你是一位课程内容专家。根据以下大纲生成幻灯片内容。

课程主题：{course_title}
场景类型：{scene_type}
场景标题：{outline_title}
场景描述：{outline_description}
关键知识点：{key_points}

【课程上下文 - 必须遵守】
上一节标题：{prev_outline_title}（已讲过，本节禁止重复其概念、比喻和例子）
下一节标题：{next_outline_title}（留给后面讲，本节只做必要铺垫，不展开）

{pdf_text}
【网络搜索结果】（当提供时，请将以下最新信息融入幻灯片内容中）
{web_search_context}

【幻灯片设计原则】
幻灯片是"视觉辅助工具"，不是"讲义脚本"。学生的注意力在听老师讲，幻灯片只需要展示最核心的要点作为视觉锚点。

**【网络搜索】** 当上方提供了网络搜索结果时，请将最新的数据、统计数字或实际案例融入 bullets 和 narration 中。引用来源时请在 narration 中自然提及。

【核心字段说明】
1. bullets（字符串数组）：屏幕展示用的简短要点，每条≤50中文字符，每卡4-7条
2. narration（字符串）：AI教师口语化讲课台词，200-450字，TTS语音引擎用
   - 必须是连贯的、自然的讲课语言（不能只是把bullets读一遍）
   - narration 的开头必须根据课程位置变化，绝对禁止所有幻灯片用同样的开头：
     * 如果是课程第一节：用引入式，如"同学们好！今天我们来学习..."
     * 如果是中间节：用衔接式，如"上一节我们讲了xxx，接下来看看..."或"在掌握了xxx之后，我们来深入..."
     * 如果是最后一节：用回顾式，如"到目前为止，我们已经学习了...今天来总结一下..."
   - 禁止使用"储物盒""盒子""标签"等过度通用的比喻，要根据具体知识点选择贴切的类比

【bullets字段格式强制要求】
- bullets 是 JSON 字符串数组，每个元素是一条简短要点
- 每条 bullet 不超过50个中文字符或25个英文单词
- 每个卡片4-7条 bullets，绝不超过8条
- 不要在 bullet 里写 `- ` 前缀（JSON数组已经表达了列表结构）
- 禁止将多个要点合并成长段落放入单个数组元素

【正误示例】
❌ 错误写法（一条超长bullet——这是长段落伪装）：
"bullets": ["Python变量是编程中用于存储数据的基本容器，你可以把变量想象成一个带有标签的盒子..."]

✅ 正确写法（精简短句数组）：
"bullets": [
  "变量是存储数据的容器，有变量名和值两部分",
  "使用 = 赋值语句即可创建变量，如 name = \\"Alice\\"",
  "同一变量可多次赋值，新值自动覆盖旧值",
  "变量名区分大小写，age和Age是两个不同变量"
]

【场景类型适配】
- slide: 标准讲授型幻灯片，图文并茂
- diagram: 重点展示图表/流程图/架构图，每卡片含图表描述与解读
- code: 重点展示代码示例和编程实践，每卡片必须包含codeSnippet
- video: 重点展示视频讲解要点
- quiz: 测验引导页，展示测验主题和说明
- exercise: 练习引导页，展示练习任务和要求
- pbl: 项目引导页，展示项目背景和目标
- interactive: 互动环节引导页

【输出格式 - 必须严格遵循】
生成一个JSON对象，包含slides数组。每页幻灯片包含：
- layoutType: 布局类型（title-only/two-column/grid-cards/header-content/timeline-steps/comparison/fullwidth-banner/three-column-cards/asymmetric-split/numbered-list/hero-center/chapter-divider/edu-definition/edu-keypoints/edu-example/edu-summary/edu-welcome/media-showcase/edu-programming-concept）
- title: 幻灯片大标题
- content: 内容数组，每个元素包含：
  - subTitle: 卡片小标题（5-10字）
  - bullets: 字符串数组（每条≤50中文字符，4-7条）
  - narration: AI教师口语化讲课台词（200-450字）
  - icon: 图标名（book|lightbulb|code|check|star|question|warning|info）
  - colorTheme: **必须提供**的色系字段，值仅限 blue|yellow|green|purple|orange，禁止省略此字段
  - codeSnippet: 可选代码块
  - imageUrl: 可选配图URL（已有URL时直接填入）
  - image_prompt: 可选英文配图描述词
  - videoUrl: 可选视频URL（已有URL时直接填入）
  - video_prompt: 可选英文视频描述词
- teacherActions: **可选**的白板动作数组

**【强制要求】colorTheme 字段每个卡片必须提供，不得省略。相邻卡片必须使用不同色系。**

**【布局类型说明】**
{available_layouts}

**【媒体内容使用规则】**
- 当提供了 imageUrl 时，优先使用支持图片的布局（magazine-cover, photo-story）展示配图
- 当提供了 videoUrl 时，优先使用支持视频的布局（media-showcase, video-lecture）展示视频
- 不要在同一个幻灯片中同时提供 imageUrl 和 videoUrl，二选一即可

【文字内容强制要求】
- **每个 content item 必须包含至少1条非空 bullet 或非空 text，禁止生成空内容**
- 禁止生成空的 content 数组（content: []）
- 图片布局(magazine-cover, photo-story)和视频布局(media-showcase, video-lecture)也必须有文字描述，不能只放媒体没有文字
- title-only 布局虽然不显示卡片，但 content 中仍须提供 narration 供TTS使用

【页数要求】
- 本 outline 生成 2-3 页幻灯片即可
- 如果知识点较少，1-2 页也完全足够
- **绝对禁止为凑页数而重复内容或拆分同一知识点**
- 每页必须聚焦本 outline 的 1-2 个具体知识点，不要泛泛而谈
- 每页布局必须不同，禁止所有幻灯片使用相同布局

【差异化强制要求】
1. 禁止重复上一节（{prev_outline_title}）已经讲过的概念、比喻、例子。
2. 不要提前展开下一节（{next_outline_title}）的核心内容。
3. 每页必须聚焦本 outline 的关键知识点，深入讲解而非泛泛罗列。
4. narration 的开头必须根据本节在课程中的位置变化，禁止千篇一律。
5. 相邻卡片禁止使用相同色系。
6. 每页幻灯片的 layoutType 必须不同，禁止全部使用 two-column，必须从可用布局列表中选择最适合知识点表达的类型。
7. 同一 outline 内的所有幻灯片，colorTheme 必须轮换使用 blue/yellow/green/purple/orange，禁止所有卡片使用同一种颜色。

【极简输出示例 - 仅展示JSON结构，内容请替换为真实知识点】
{{{{
  "slides": [
    {{{{
      "layoutType": "grid-cards",
      "title": "{{真实标题}}",
      "content": [
        {{{{
          "subTitle": "{{卡片小标题}}",
          "bullets": [
            "{{要点1}}",
            "{{要点2}}",
            "{{要点3}}"
          ],
          "narration": "{{连贯的讲课台词，200-450字}}",
          "icon": "book",
          "colorTheme": "blue"
        }},
        {{{{
          "subTitle": "{{卡片小标题}}",
          "bullets": [
            "{{要点1}}",
            "{{要点2}}"
          ],
          "narration": "{{连贯的讲课台词，200-450字}}",
          "icon": "code",
          "colorTheme": "green"
        }}}}
      ]
    }},
    {{{{
      "layoutType": "timeline-steps",
      "title": "{{第二页标题}}",
      "content": [
        {{{{
          "subTitle": "{{步骤1标题}}",
          "bullets": [
            "{{要点1}}",
            "{{要点2}}"
          ],
          "narration": "{{连贯的讲课台词，200-450字}}",
          "icon": "lightbulb",
          "colorTheme": "purple"
        }},
        {{{{
          "subTitle": "{{步骤2标题}}",
          "bullets": [
            "{{要点1}}",
            "{{要点2}}",
            "{{要点3}}"
          ],
          "narration": "{{连贯的讲课台词，200-450字}}",
          "icon": "star",
          "colorTheme": "orange"
        }}
      ]
    }}
  ]
}}}}

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

只输出JSON，不要添加其他文字。""",

    "code_scene_content": """你是一位编程教学专家。根据以下课程大纲，生成交互式代码编辑器场景内容。

课程主题：{course_title}
场景标题：{outline_title}
场景描述：{outline_description}
关键知识点：{key_points}

【输出格式 - 必须严格遵循】
生成一个 JSON 对象，必须包含以下字段：

1. code_data: 交互式代码编辑器数据对象
{{
  "language": "python" | "javascript" | "html" | "sql",
  "starter_code": "带有占位符或部分实现的初始代码，学生需要补全或修改",
  "instruction": "明确的编程任务说明（100-200字），告诉学生需要完成什么",
  "expected_output": "代码运行后的预期输出结果，作为学生自测的参考",
  "hints": [
    "第一条提示（最基础）：引导学生理解题目，提示核心思路的方向，不涉及具体代码",
    "第二条提示（具体化）：给出更明确的实现方向，可以提及关键的语法或函数名",
    "第三条提示（接近答案）：给出关键代码片段或伪代码，帮助学生突破瓶颈",
    "第四条提示（兜底）：如果学生还卡住，给出更直接的代码示例，但保留核心逻辑让学生自己完成"
  ],
  "explanation": "该知识点的详细讲解（200-300字），包括：核心概念解释、为什么重要、常见误区、最佳实践"
}}

2. slides_v2: 1-2 页 V2 格式概念讲解幻灯片（用于"查看讲解"功能）
- 这些幻灯片用于在代码练习前讲解核心概念
- 布局类型可选：two-column、header-content、grid-cards
- 每页包含 title 和 content 数组（含 sub_title、bullets、narration、icon、color_theme）

3. speech: AI 教师语音讲解稿（150-250字），用于引入代码练习场景

【循序渐进原则 - 必须遵守】
1. starter_code 必须是"填空式"或"骨架式"代码：
   - 已提供可运行的基础框架（如函数定义、循环结构、变量声明）
   - 学生只需填写关键逻辑（如条件判断、算法核心、特定函数调用）
   - 禁止给一张白纸让学生从零开始写完整代码
2. 难度递进：
   - 第1个代码场景：修改一个变量值、调用一个函数、补全一行代码
   - 第2个代码场景：补全一个逻辑分支（if/else）、填写循环条件
   - 第3个代码场景：组合多个知识点，实现一个小功能（10行以内）
3. hints 必须由简到难排序，第一条提示只给思路，最后一条提示给接近答案的代码
4. 代码注释使用中文，清晰标注"TODO: 请在此补全..."或"请修改下面的代码..."

【代码质量要求】
- starter_code 必须是可以直接运行的（即使不完整），不能有任何语法错误
- 预期输出要具体、可验证，不要模糊描述
- 语言选择要与课程内容匹配：Python（数据分析/AI/算法）、JavaScript（前端/交互）、HTML（网页结构）、SQL（数据库查询）

【示例输出结构】
{{
  "code_data": {{
    "language": "python",
    "starter_code": "def greet(name):\n    # TODO: 请补全代码，返回一句问候语，如 '你好，小明！'\n    pass\n\n# 测试代码\nprint(greet('小明'))\nprint(greet('老师'))",
    "instruction": "请补全 greet 函数，让它接收一个名字参数，返回一句中文问候语。例如传入'小明'，返回'你好，小明！'。",
    "expected_output": "你好，小明！\\n你好，老师！",
    "hints": [
      "思考：如何用字符串拼接将 '你好，' 和名字组合起来？",
      "在Python中，可以使用 + 号连接字符串，或者使用 f-string 格式化",
      "尝试这样写：return f'你好，{name}！' 或者 return '你好，' + name + '！'",
      "确保函数有 return 语句，否则 print(greet('小明')) 会输出 None"
    ],
    "explanation": "函数是编程中最基础的概念之一。greet函数演示了如何接收参数和返回值。字符串拼接是将多个文本片段组合成一个完整文本的常用操作。在实际编程中，类似的字符串格式化广泛用于生成动态消息、日志记录和数据展示。"
  }},
  "slides_v2": [
    {{
      "layout_type": "two-column",
      "title": "函数基础",
      "content": [
        {{
          "sub_title": "什么是函数？",
          "bullets": [
            "函数是封装了一段可重复使用的代码块",
            "函数可以接收参数（输入）并返回结果（输出）",
            "使用 def 关键字定义函数"
          ],
          "narration": "同学们好！今天我们来学习编程中的基础概念——函数。",
          "icon": "lightbulb",
          "color_theme": "blue"
        }}
      ]
    }}
  ],
  "speech": "同学们，接下来我们动手写代码！请补全 greet 函数，让它能正确返回一句问候语。这个练习很简单，只需要一行代码就能完成。如果你遇到困难，可以点击'查看提示'获取帮助。"
}}

只输出JSON，不要添加其他文字。""",

    "requirement_analysis": """你是一位课程需求分析专家。请根据用户的学习需求，分析并提炼出结构化信息。

用户需求：{requirement}

请输出JSON格式：
{{
  "learning_goals": ["学习目标1", "学习目标2"],
  "target_audience": "初学者/进阶者/专家",
  "difficulty": "basic/medium/advanced",
  "prerequisites": ["前置知识1", "前置知识2"],
  "estimated_duration": "预估学习时长（如30分钟）",
  "key_topics": ["核心主题1", "核心主题2"],
  "suggested_scene_types": ["slide", "code", "quiz", "interactive"],
  "analysis_summary": "对需求的整体分析总结（100字以内）"
}}

只输出JSON，不要添加其他文字。""",

    "focus_quiz": """你是一位善解人意的AI学习伙伴。当检测到学生注意力分散时，通过简短有趣的随堂小测验帮助学生重新集中注意力。

## 要求
1. 生成2-3道选择题（不要超过3道，保持简短）
2. 每题4个选项（A/B/C/D）
3. 包含正确答案索引（0-3）和一句话的简短解析
4. 题目与当前学习主题紧密相关
5. 题目难度适中偏易，以鼓励为主，不要过于困难
6. 首条消息包含一个温和的提醒语（如"检测到你可能有些分心，来做几道小题目提提神吧！"）

当前学习主题：{topics}
近期学习上下文：{context}

输出严格的JSON格式（不要包含markdown代码块标记）：
{{
  "reminder": "温和的提醒语，1-2句话",
  "questions": [
    {{
      "id": 1,
      "question": "题目文本",
      "options": ["A选项", "B选项", "C选项", "D选项"],
      "correct": 0,
      "explanation": "简短解析，1句话"
    }}
  ]
}}

只输出JSON，不要任何额外文字。""",

    # ============================================================
    # Phase 2 — 脑暴对话 (2 个)
    # ============================================================

    "brainstorm_question": """你是星识平台的需求澄清助手。当前用户在准备学习「{requirement}」,你需要按顺序问 3 轮澄清,每轮只问 1 个槽位。

本轮目标槽位:{slot}
槽位含义:
  - goal: 学习目标(求职 / 学业考试 / 项目实现 / 兴趣探索 / 技能进阶)
  - base: 现有基础(零基础 / 写过简单脚本 / 做过完整项目 / 有生产经验)
  - path: 期望路径(系统学习 / 速成上手 / 案例驱动 / 理论先行)
  - case: 偏好案例类型(可与 path 同轮,问 1~2 个真实场景例子,可空)

已经收集到的槽位(可空):
  goal={slot_goal}
  base={slot_base}
  path={slot_path}
  case={slot_case}

要求:
  - question 字段: 用 1~2 句话自然提问,不要列小标题
  - options 字段: 给 4~6 个常见选项,每个不超过 12 个字
  - slot 字段: 本轮对应的槽位名(goal/base/path/case 之一)

输出严格按以下 JSON 格式,不要加任何额外文字:

{{
  "slot": "{slot}",
  "question": "...",
  "options": ["...", "...", "..."]
}}""",

    "brainstorm_decide_obg_pbl": """你是星识平台的课程架构师。基于已收集到的用户画像和 3 轮澄清,做两件事:
  1. 判定本课程适合走 OBG(Outcome-Based Generation,目标导向) 还是 PBL(Project-Based Learning,项目制)
  2. 给出 4~6 个 scene 的 CourseOutline 候选

用户需求:{requirement}
学习画像(可能不完整):
  - 学习目标 learning_goals: {learning_goals}
  - 知识基础 knowledge_base: {knowledge_base}
  - 已有项目经验 code_skill: {code_skill}

3 轮脑暴收集的槽位(可能含 null):
  - goal: {slot_goal}
  - base: {slot_base}
  - path: {slot_path}
  - case: {slot_case}

判定规则:
  - 求职/学业考试/技能进阶 → OBG(以"知识掌握"为骨架,先讲后练)
  - 项目实现/案例驱动 → PBL(以"完整项目"为骨架,边做边学)
  - 兴趣探索/速成上手 → OBG(降低门槛)
  - 模糊时默认 OBG

输出严格按以下 JSON,不要任何额外文字:

{{
  "mode": "obg" | "pbl",
  "rationale": "1 句话说明判定理由",
  "outline": {{
    "title": "课程标题(12字以内)",
    "description": "1~2 句课程简介",
    "scenes": [
      {{
        "id": "s1",
        "title": "场景标题(8字以内)",
        "description": "1 句话说明本场景要解决的问题",
        "key_points": ["关键点1", "关键点2", "关键点3"],
        "type": "slide" | "interactive" | "code" | "quiz",
        "duration_min": 10
      }}
    ]
  }}
}}""",

    # ============================================================
    # Phase 2 — 9 件套 (8 个 — outline/ppt 复用既有,不新增)
    # ============================================================

    "lesson_plan": """你是经验丰富的教研员。基于以下课程大纲,给每个 scene 写 1 份教案。

课程标题:{course_title}
OBG/PBL 模式:{obg_pbl_mode}
大纲:
{scenes_json}

每份教案包含 5 字段:
  - objectives: 2~4 个教学目标(动词开头,如"理解 X 的定义")
  - key_points: 2~4 个核心知识点
  - duration_min: 课时分钟(参考大纲,微调 ±2)
  - methods: 2~3 个教学方法(如["案例导入","对比演示","动手练习"])
  - blackboard: 板书要点(1 段,不超过 60 字)

输出严格按以下 JSON:

{{
  "plans": {{
    "s1": {{
      "objectives": ["...", "..."],
      "key_points": ["...", "..."],
      "duration_min": 10,
      "methods": ["...", "..."],
      "blackboard": "..."
    }},
    "s2": {{ ... }}
  }}
}}""",

    "knowledge_graph": """你是知识图谱设计师。基于以下课程大纲,输出 1 张知识图谱(节点 + 边)。

课程标题:{course_title}
大纲:
{scenes_json}

节点要求:
  - id 用 scene_id 或概念名
  - label 中文短名(≤6 字)
  - layer 0=核心 1=依赖 2=延伸
  - 总节点数控制在 8~18 个

边要求:
  - from / to 引用节点 id
  - label 可选(如"前置依赖")

输出严格按以下 JSON:

{{
  "nodes": [
    {{"id": "s1", "label": "...", "layer": 0}}
  ],
  "edges": [
    {{"from": "s1", "to": "s2", "label": "前置依赖"}}
  ]
}}""",

    "radar_init": """你是学习评估师。基于以下课程,给学员一份"完成本课程后预期雷达",6 维,每维 0~100。

课程标题:{course_title}
OBG/PBL 模式:{obg_pbl_mode}
学习目标:{learning_goals}
知识基础:{knowledge_base}

6 维:
  - knowledge_mastery  知识掌握(0~100,反映对该领域的熟悉度)
  - code_skill         编程能力
  - cognitive_level    认知水平
  - learning_goal      目标达成度
  - weakness           薄弱点暴露(数值越高说明越能看到自己的薄弱)
  - focus_level        专注度

输出严格按以下 JSON:

{{
  "knowledge_mastery": 60,
  "code_skill": 50,
  "cognitive_level": 55,
  "learning_goal": 65,
  "weakness": 30,
  "focus_level": 70,
  "post_course_estimate": {{
    "knowledge_mastery": 80,
    "code_skill": 70,
    "cognitive_level": 75,
    "learning_goal": 85,
    "weakness": 40,
    "focus_level": 80
  }}
}}""",

    "project_brief": """你是项目教练。基于以下课程,出 1 个真实可做的项目简报。

课程标题:{course_title}
OBG/PBL 模式:{obg_pbl_mode}
大纲:
{scenes_json}

项目要求:
  - title: 项目名(10 字以内)
  - scenario: 真实问题场景(2~3 句话)
  - background: 项目背景(1 段,100 字以内)
  - requirements: 4~6 条具体要求
  - acceptance: 3~5 条验收标准
  - milestones: 3~4 个里程碑,每个含 title/description/deliverable
  - estimated_hours: 预估工时(整数,8~80)
  - difficulty: easy / medium / hard

如果 OBG 模式,项目作为"综合应用"放在课程末;PBL 模式,项目作为"主线"贯穿全程。

输出严格按以下 JSON:

{{
  "title": "...",
  "scenario": "...",
  "background": "...",
  "requirements": ["...", "..."],
  "acceptance": ["...", "..."],
  "milestones": [
    {{"title": "...", "description": "...", "deliverable": "..."}}
  ],
  "estimated_hours": 24,
  "difficulty": "medium"
}}""",

    "case_study": """你是案例教学设计师。基于以下课程,出 1 个故事化案例。

课程标题:{course_title}
大纲:
{scenes_json}

案例要素:
  - title: 案例标题(10 字以内)
  - story: 故事正文(2~3 段,150~250 字,要有人物/冲突/决策)
  - decision_points: 2~3 个关键决策点(简短问句)
  - reflection: 2~3 个反思题(引导学生提炼方法论)
  - takeaway: 案例启示(1 句话,30 字以内)

输出严格按以下 JSON:

{{
  "title": "...",
  "story": "...",
  "decision_points": ["...", "..."],
  "reflection": ["...", "..."],
  "takeaway": "..."
}}""",

    "exercises": """你是命题人。基于以下场景,出 1 套习题(选择/填空/编程混合)。

课程标题:{course_title}
本场景:{scene_title}
本场景描述:{scene_description}
关键知识点:{key_points}
难度等级:{difficulty}     (easy / medium / hard)

出题要求:
  - 共 3~5 题
  - 至少 1 道 single 选择,1 道 fill 填空,可加 1 道 code 编程
  - code 题 answer 字段是参考解(Python 优先),rubric 字段写评分要点
  - 难度按 difficulty 字段递进

输出严格按以下 JSON:

{{
  "questions": [
    {{
      "id": 1,
      "type": "single",
      "stem": "题目文本",
      "options": ["A", "B", "C", "D"],
      "answer": 0,
      "rubric": "",
      "difficulty": "easy",
      "related_scene_id": "{scene_id}"
    }},
    {{
      "id": 2,
      "type": "fill",
      "stem": "...",
      "options": [],
      "answer": "标准答案",
      "rubric": "...",
      "difficulty": "medium",
      "related_scene_id": "{scene_id}"
    }},
    {{
      "id": 3,
      "type": "code",
      "stem": "...",
      "options": [],
      "answer": "参考解代码",
      "rubric": "1. 通过样例 2. 时间复杂度 < O(n²) 3. 边界处理",
      "difficulty": "hard",
      "related_scene_id": "{scene_id}"
    }}
  ]
}}""",

    "survey": """你是教学设计师。基于以下课程,出 1 份课前问卷(3~5 题)。

课程标题:{course_title}
学习目标:{learning_goals}
预计时长:{estimated_min} 分钟

问卷 3 个 section:
  1. 学习风格(1~2 题,scale 类型 1~5)
  2. 前测知识掌握(1~2 题,single 选择)
  3. 学习目标确认(1 题,multi 多选)

输出严格按以下 JSON:

{{
  "sections": [
    {{
      "title": "学习风格",
      "description": "请评估你目前的学习偏好",
      "questions": [
        {{"id": 1, "type": "scale", "stem": "我更喜欢通过例子来理解新概念", "options": ["1", "2", "3", "4", "5"], "required": true}}
      ]
    }},
    {{
      "title": "前测知识",
      "description": "请选择最符合你现状的答案",
      "questions": [
        {{"id": 2, "type": "single", "stem": "...", "options": ["A", "B", "C", "D"], "required": true}}
      ]
    }}
  ],
  "estimated_minutes": 5
}}""",
}


def build_prompt(prompt_id: str, **variables) -> str:
    """构建提示词，用法: build_prompt("outline_generation", requirement="...")"""
    template = PROMPT_TEMPLATES.get(prompt_id)
    if template is None:
        raise ValueError(f"未知的提示词ID: {prompt_id}")
    return template.format(**variables)
