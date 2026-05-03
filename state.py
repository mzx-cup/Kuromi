from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional, Union

from pydantic import BaseModel, Field, field_validator


class EmotionType(str, Enum):
    CONFIDENT = "confident"
    CONFUSED = "confused"
    FRUSTRATED = "frustrated"
    CURIOUS = "curious"
    BORED = "bored"
    ANXIOUS = "anxious"
    NEUTRAL = "neutral"


class DialogueRole(str, Enum):
    STUDENT = "student"
    SYSTEM = "system"
    PROFILER = "profiler"
    PLANNER = "planner"
    GENERATOR = "generator"
    EVALUATOR = "evaluator"
    RESOURCE = "resource"


class ContentType(str, Enum):
    TEXT = "text"
    DOCUMENT = "document"
    MINDMAP = "mindmap"
    EXERCISE = "exercise"
    VIDEO = "video"
    CODE = "code"
    MERMAID = "mermaid"


class DifficultyLevel(str, Enum):
    BASIC = "basic"
    MEDIUM = "medium"
    ADVANCED = "advanced"


class CognitiveStyle(str, Enum):
    VISUAL = "visual"
    PRAGMATIC = "pragmatic"
    TEXTUAL = "textual"


class DialogueType(str, Enum):
    QUESTION = "question"
    CONFUSION = "confusion"
    PRACTICE = "practice"
    REVIEW = "review"
    CHITCHAT = "chitchat"
    GOAL_SETTING = "goal_setting"


class ChatMessage(BaseModel):
    role: DialogueRole = DialogueRole.STUDENT
    content: str = ""
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EmotionState(BaseModel):
    emotion_type: EmotionType = EmotionType.NEUTRAL
    intensity: float = Field(default=0.5, ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=datetime.now)
    trigger: str = ""


class KnowledgeMastery(BaseModel):
    topic: str = ""
    mastery_level: float = Field(default=0.0, ge=0.0, le=1.0)
    last_updated: datetime = Field(default_factory=datetime.now)
    evidence_count: int = 0


class LearningProfile(BaseModel):
    knowledge_mastery: list[KnowledgeMastery] = Field(default_factory=list)
    learning_style: CognitiveStyle = CognitiveStyle.PRAGMATIC
    learning_progress: float = Field(default=0.0, ge=0.0, le=1.0)
    learning_preference: dict[str, Any] = Field(default_factory=dict)
    cognitive_level: DifficultyLevel = DifficultyLevel.BASIC
    learning_goals: list[str] = Field(default_factory=lambda: ["应对考试"])
    interaction_count: int = 0
    socratic_pass_rate: float = 0.0
    code_practice_time: int = 0


class PathNode(BaseModel):
    course_id: str = ""
    chapter_id: str = ""
    knowledge_point_id: str = ""
    topic: str = ""
    status: str = "locked"
    difficulty: DifficultyLevel = DifficultyLevel.BASIC
    importance: str = ""
    estimated_time: int = 0
    name: str = ""
    title: str = ""
    children: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResourceLink(BaseModel):
    url: str = ""
    title: str = ""
    resource_type: ContentType = ContentType.TEXT
    description: str = ""


class AgentStepLog(BaseModel):
    agent_name: str = ""
    agent_role: str = ""
    input_summary: str = ""
    output_summary: str = ""
    processing_time_ms: int = 0
    status: str = "success"
    error_message: str = ""
    timestamp: datetime = Field(default_factory=datetime.now)


class PlannerOutput(BaseModel):
    learning_objective: str = ""
    difficulty_level: DifficultyLevel = DifficultyLevel.BASIC
    content_types: list[ContentType] = Field(default_factory=lambda: [ContentType.TEXT])
    next_path_node: Optional[PathNode] = None
    reasoning: str = ""


class GeneratorOutput(BaseModel):
    text_content: str = ""
    content_type: ContentType = ContentType.TEXT
    resources: list[ResourceLink] = Field(default_factory=list)
    suggested_path: list[PathNode] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class StudentState(BaseModel):
    student_id: str = ""
    course_id: str = ""
    context_id: str = Field(default_factory=lambda: datetime.now().strftime("%Y%m%d%H%M%S%f"))
    dialogue_history: list[ChatMessage] = Field(default_factory=list)
    profile: LearningProfile = Field(default_factory=LearningProfile)
    current_path: list[PathNode] = Field(default_factory=list)
    emotion: EmotionState = Field(default_factory=EmotionState)
    workflow_logs: list[AgentStepLog] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    source_links: dict[str, str] = Field(default_factory=dict)
    dispatch_strategy: str = "textual"
    is_timer_running: bool = False
    remaining_time: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
    telemetry_data: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def add_message(self, role: DialogueRole, content: str, metadata: dict[str, Any] | None = None) -> None:
        self.dialogue_history.append(
            ChatMessage(role=role, content=content, metadata=metadata or {})
        )
        self.updated_at = datetime.now()

    def add_workflow_log(self, log: AgentStepLog) -> None:
        self.workflow_logs.append(log)
        self.updated_at = datetime.now()

    def update_emotion(self, emotion_type: EmotionType, intensity: float, trigger: str = "") -> None:
        self.emotion = EmotionState(
            emotion_type=emotion_type,
            intensity=intensity,
            trigger=trigger,
            timestamp=datetime.now()
        )
        self.updated_at = datetime.now()

    def update_telemetry(self, data: dict[str, Any]) -> None:
        self.telemetry_data = {**self.telemetry_data, **data}
        self.updated_at = datetime.now()

    def get_recent_messages(self, n: int = 10) -> list[ChatMessage]:
        return self.dialogue_history[-n:]

    def to_persist_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_persist_dict(cls, data: dict[str, Any]) -> StudentState:
        # Fix legacy data where source_links might be a list instead of dict
        if "source_links" in data and not isinstance(data["source_links"], dict):
            data["source_links"] = {}
        if "sources" in data and not isinstance(data["sources"], list):
            data["sources"] = []
        return cls.model_validate(data)


class ChatRequestV2(BaseModel):
    student_id: str = ""
    course_id: str = "bigdata"
    user_input: str = ""
    context_id: str = ""
    current_profile: dict[str, Any] = Field(default_factory=dict)
    current_path: list[dict[str, Any]] = Field(default_factory=list)
    interaction_count: int = 0
    code_practice_time: int = 0
    socratic_pass_rate: float = 0.0


class ChatResponseV2(BaseModel):
    success: bool = True
    content: str = ""
    content_type: ContentType = ContentType.TEXT
    resources: list[ResourceLink] = Field(default_factory=list)
    suggested_path: list[PathNode] = Field(default_factory=list)
    new_profile: dict[str, Any] = Field(default_factory=dict)
    new_path: list[dict[str, Any]] = Field(default_factory=list)
    workflow_logs: list[AgentStepLog] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    source_links: dict[str, str] = Field(default_factory=dict)
    dispatch_strategy: str = "textual"
    emotion: EmotionState = Field(default_factory=EmotionState)
    evaluation: dict[str, Any] = Field(default_factory=dict)
    context_id: str = ""


class StreamChatRequest(BaseModel):
    student_id: str = ""
    course_id: str = "bigdata"
    user_input: str = Field(..., min_length=1)
    context_id: str = ""
    current_profile: dict[str, Any] = Field(default_factory=dict)
    current_path: list[dict[str, Any]] = Field(default_factory=list)
    interaction_count: int = Field(default=0, ge=0)
    code_practice_time: int = Field(default=0, ge=0)
    socratic_pass_rate: float = Field(default=0.0, ge=0.0, le=1.0)

    @field_validator("user_input", mode="after")
    @classmethod
    def _validate_user_input(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("用户输入不能为空白")
        return v.strip()


class DebateAgentConfig(BaseModel):
    """辩论身份配置"""
    id: str
    name: str
    systemPrompt: str
    themeColor: str = "#6366f1"


class DebateRequest(BaseModel):
    """辩论模式请求"""
    student_id: str = ""
    course_id: str = "bigdata"
    user_input: str = Field(..., min_length=1)
    context_id: str = ""
    current_profile: dict[str, Any] = Field(default_factory=dict)
    agents: list[DebateAgentConfig] = Field(default_factory=list)

    @field_validator("user_input", mode="after")
    @classmethod
    def _validate_user_input(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("用户输入不能为空白")
        return v.strip()


# ============================================================
# 学生画像（6维度）
# ============================================================

class TopicMastery(BaseModel):
    """知识点掌握情况"""
    name: str = ""
    level: float = Field(default=0.0, ge=0.0, le=1.0)
    last_updated: str = ""


class KnowledgeMasteryPortrait(BaseModel):
    """知识掌握画像"""
    topics: list[TopicMastery] = Field(default_factory=list)
    overall: float = Field(default=0.0, ge=0.0, le=1.0)


class CodeSkillPortrait(BaseModel):
    """编程能力画像"""
    level: str = "beginner"  # beginner, intermediate, advanced
    strong_areas: list[str] = Field(default_factory=list)
    weak_areas: list[str] = Field(default_factory=list)
    last_updated: str = ""


class CognitiveStylePortrait(BaseModel):
    """认知风格画像"""
    type: str = "实践型"  # 视觉型, 文字型, 实践型
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    last_updated: str = ""


class LearningGoalPortrait(BaseModel):
    """学习目标画像"""
    current: str = ""
    target_positions: list[str] = Field(default_factory=list)
    timeframe: str = ""
    last_updated: str = ""


class WeaknessPortrait(BaseModel):
    """知识短板画像"""
    areas: list[str] = Field(default_factory=list)
    last_detected: str = ""
    last_updated: str = ""


class FocusLevelPortrait(BaseModel):
    """专注度画像"""
    current: str = "中等专注"  # 高专注, 中等专注, 需要引导
    trend: str = "stable"  # stable, improving, declining
    last_updated: str = ""


class LearningPortrait(BaseModel):
    """6维学生画像"""
    knowledge_mastery: KnowledgeMasteryPortrait = Field(default_factory=KnowledgeMasteryPortrait)
    code_skill: CodeSkillPortrait = Field(default_factory=CodeSkillPortrait)
    cognitive_style: CognitiveStylePortrait = Field(default_factory=CognitiveStylePortrait)
    learning_goal: LearningGoalPortrait = Field(default_factory=LearningGoalPortrait)
    weakness: WeaknessPortrait = Field(default_factory=WeaknessPortrait)
    focus_level: FocusLevelPortrait = Field(default_factory=FocusLevelPortrait)
    last_synced: str = ""  # 最后同步时间


# ============================================================
# 课程生成数据模型
# ============================================================

class SlideElement(BaseModel):
    """幻灯片元素（增强版：支持多种类型）"""
    type: str = "text"  # text, code, image, shape, line, chart, latex, table, audio, video
    content: str = ""
    left: float = 0
    top: float = 0
    width: float = 0
    height: float = 0
    style: dict[str, Any] = Field(default_factory=dict)  # 字体、颜色等样式
    image_url: str = ""  # 图片元素URL
    audio_url: str = ""  # TTS音频URL
    # 样式增强
    default_font_name: str = "Microsoft YaHei"
    default_color: str = "#333333"
    fill: str = ""  # 背景填充色
    opacity: float = 1.0
    rotate: float = 0
    word_space: float = 0  # 字间距
    line_height: float = 0  # 行高
    # Shape专用
    shape_name: str = ""  # rectangle, circle, triangle, etc.
    path: str = ""  # SVG路径数据
    view_box: list[float] = [0, 0, 100, 100]
    gradient: dict[str, Any] = Field(default_factory=dict)  # 渐变填充
    pattern: str = ""  # 图案填充
    # Line专用
    line_color: str = "#333333"
    line_style: str = "solid"  # solid, dashed, dotted
    points: list[list[float]] = Field(default_factory=list)  # 线条端点 [[x1,y1],[x2,y2]]
    # Chart专用
    chart_type: str = ""  # bar, column, line, pie, ring, area, radar, scatter
    chart_data: dict[str, Any] = Field(default_factory=dict)  # {labels:[], series:[[val1,val2]]}
    theme_colors: list[str] = Field(default_factory=list)
    # LaTeX专用
    latex: str = ""  # LaTeX公式字符串
    # Table专用
    table_data: list[list[dict[str, Any]]] = Field(default_factory=list)  # 表格数据
    col_widths: list[float] = Field(default_factory=list)  # 列宽比例
    # Video专用
    video_url: str = ""
    poster: str = ""  # 视频封面
    # 链接
    link: dict[str, Any] = Field(default_factory=dict)  # {type:"web"/"slide", target:"url"/"slide_id"}
    # 阴影/边框
    shadow: dict[str, Any] = Field(default_factory=dict)  # {h, v, blur, color}
    outline: dict[str, Any] = Field(default_factory=dict)  # {color, width, style}
    id: str = ""  # 元素唯一ID（用于spotlight引用）


class SlideBackground(BaseModel):
    """幻灯片背景"""
    type: str = "solid"  # solid, gradient, image
    color: str = "#ffffff"
    gradient: dict[str, Any] = Field(default_factory=dict)  # {colors:[...], type:"linear"/"radial"}
    image: dict[str, Any] = Field(default_factory=dict)  # {src:"url", ...}


class SlideContent(BaseModel):
    """幻灯片内容"""
    elements: list[SlideElement] = Field(default_factory=list)


class Slide(BaseModel):
    """单个幻灯片"""
    id: int = 0
    title: str = ""
    content: SlideContent = Field(default_factory=SlideContent)
    speech: str = ""  # AI老师讲解文本
    image_prompt: str = ""  # 配图生成提示词(用于image-01模型)
    background: SlideBackground = Field(default_factory=SlideBackground)  # 背景设置
    remark: str = ""  # 教师备注/讲解要点摘要
    scene_id: Optional[int] = None  # strict FK → SceneOutline.id


class SlideContentItemV2(BaseModel):
    """幻灯片内容项 V2（结构化布局）"""
    sub_title: str = ""
    text: str = ""
    icon: str = "book"  # book, lightbulb, code, check, star, question, warning, info
    color_theme: str = "blue"  # blue, yellow, green, purple, orange
    code_snippet: str = ""  # 可选代码块
    image_url: str = ""  # 可选配图

    @field_validator('icon')
    @classmethod
    def validate_icon(cls, v):
        allowed = {'book', 'lightbulb', 'code', 'check', 'star', 'question', 'warning', 'info'}
        return v if v in allowed else 'book'

    @field_validator('color_theme')
    @classmethod
    def validate_color_theme(cls, v):
        allowed = {'blue', 'yellow', 'green', 'purple', 'orange'}
        return v if v in allowed else 'blue'


class SlideV2(BaseModel):
    """幻灯片 V2 版本（结构化布局）"""
    layout_type: str = "two-column"  # title-only, two-column, grid-cards, header-content, quote-highlight
    title: str = ""
    content: list[SlideContentItemV2] = Field(default_factory=list)
    scene_id: Optional[int] = None  # strict FK → SceneOutline.id

    @field_validator('layout_type')
    @classmethod
    def validate_layout_type(cls, v):
        allowed = {'title-only', 'two-column', 'grid-cards', 'header-content', 'quote-highlight'}
        return v if v in allowed else 'two-column'


class SceneOutline(BaseModel):
    """场景大纲"""
    id: int = 0
    title: str = ""
    type: str = "slide"  # slide, quiz, exercise
    points: int = 0  # 包含的要点数
    key_points: list[str] = Field(default_factory=list)  # LLM生成的关键知识点列表
    description: str = ""  # 场景详细描述


class TeacherInfo(BaseModel):
    """AI教师信息"""
    name: str = "星识教师"
    avatar: str = ""  # 头像URL或emoji
    role: str = "课程导师"
    voice_id: int = 0  # 音色ID 0-4


class TeacherAction(BaseModel):
    """AI教师动作（用于课堂演示）"""
    id: str = ""
    type: str = ""  # spotlight, laser, speech, wb_open, wb_close, wb_draw_text, wb_draw_shape
    element_id: str = ""  # spotlight/laser指向的元素ID
    text: str = ""  # speech动作的讲解文本
    # Whiteboard动作
    wb_content: str = ""  # 白板绘制的HTML内容
    wb_shape: str = ""  # 白板绘制的形状类型
    # Widget动作
    widget_target: str = ""
    widget_state: dict[str, Any] = Field(default_factory=dict)
    # 动画参数
    duration: float = 0  # 动作持续时间（秒）
    delay: float = 0  # 动作延迟时间（秒）
    color: str = "#ff6b6b"  # laser颜色


class SceneActions(BaseModel):
    """场景动作集合"""
    scene_id: int = 0
    actions: list[TeacherAction] = Field(default_factory=list)


# ============================================================
# Quiz / 交互数据模型
# ============================================================

class QuizQuestion(BaseModel):
    """测验题目"""
    id: int = 0
    question: str = ""
    options: list[str] = Field(default_factory=list)
    correct_answer: int = 0  # 正确答案索引
    explanation: str = ""  # 答案解析


class QuizData(BaseModel):
    """测验数据"""
    title: str = ""
    questions: list[QuizQuestion] = Field(default_factory=list)
    passing_score: int = 60  # 及格分数


class InteractiveData(BaseModel):
    """交互式内容数据"""
    instruction: str = ""
    hints: list[str] = Field(default_factory=list)
    expected_answer: str = ""


# ============================================================
# 课堂聊天 API 模型
# ============================================================

class CourseChatRequest(BaseModel):
    """课堂聊天请求"""
    student_id: str = ""
    course_id: str = ""
    slide_index: int = 0
    slide_title: str = ""
    slide_content: str = ""
    speech: str = ""
    user_input: str = Field(..., min_length=1)
    history: list[dict[str, str]] = Field(default_factory=list)


class CourseData(BaseModel):
    """生成的课程数据"""
    courseId: str = ""
    title: str = ""
    outlines: list[SceneOutline] = Field(default_factory=list)
    slides: list[Slide] = Field(default_factory=list)
    slides_v2: list[SlideV2] = Field(default_factory=list)  # V2 结构化布局格式
    teacher: TeacherInfo = Field(default_factory=TeacherInfo)
    agent_team: list[dict[str, Any]] = Field(default_factory=list)
    quiz_data: list[dict[str, Any]] = Field(default_factory=list)
    exercise_data: list[dict[str, Any]] = Field(default_factory=list)
    interactive_data: list[dict[str, Any]] = Field(default_factory=list)
    tts_audio_urls: dict[str, str] = Field(default_factory=dict)  # scene_id -> audio_url
    scene_actions: list[SceneActions] = Field(default_factory=list)  # 每场景的动作列表
    metadata: dict[str, Any] = Field(default_factory=dict)


class CourseGenerationRequest(BaseModel):
    """课程生成请求"""
    student_id: str = ""
    requirement: str = Field(..., min_length=1)
    enable_web_search: bool = True
    enable_image: bool = True
    enable_tts: bool = True
    enable_video: bool = False
    voice_id: str = "female-shaonv"
    agent_mode: str = "preset"  # preset / auto
    interactive_mode: bool = False
    enable_pdf_upload: bool = False


class CourseGenerationSession(BaseModel):
    """课程生成会话"""
    session_id: str = ""
    student_id: str = ""
    requirement: str = ""
    status: str = "pending"  # pending, generating, completed, failed
    progress: float = 0.0
    course_data: Optional[CourseData] = None
    error_message: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# ============================================================
# 媒体生成 API 模型
# ============================================================

class GenerateImageRequest(BaseModel):
    """图片生成请求"""
    prompt: str = Field(..., min_length=1)
    aspect_ratio: str = "16:9"


class GenerateImageResponse(BaseModel):
    """图片生成响应"""
    success: bool = True
    url: str = ""
    error: str = ""


class GenerateTTSRequest(BaseModel):
    """TTS生成请求"""
    text: str = Field(..., min_length=1)
    voice_id: str = "female-shaonv"
    speed: float = 1.0


class GenerateTTSResponse(BaseModel):
    """TTS生成响应"""
    success: bool = True
    url: str = ""
    error: str = ""


# ============================================================
# 课程持久化 API 模型
# ============================================================

class CourseSaveRequest(BaseModel):
    """课程保存请求"""
    course_data: CourseData
    student_id: str = ""


class CourseListResponse(BaseModel):
    """课程列表响应"""
    courses: list[CourseData] = Field(default_factory=list)


# ============================================================
# 提供者配置 API 模型
# ============================================================

class ProviderConfig(BaseModel):
    """提供者配置"""
    provider_type: str = ""  # llm, tts, image, video, asr
    provider_id: str = ""  # xunfei, minimax, baidu
    config: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class ProviderConfigRequest(BaseModel):
    """提供者配置请求"""
    provider_type: str = Field(..., min_length=1)
    provider_id: str = Field(..., min_length=1)
    config: dict[str, Any] = Field(default_factory=dict)


class ProviderVerifyRequest(BaseModel):
    """提供者验证请求"""
    provider_type: str = Field(..., min_length=1)
    provider_id: str = Field(..., min_length=1)
    config: dict[str, Any] = Field(default_factory=dict)


# ============================================================
# AI 教师团队数据模型
# ============================================================

class GeneratedAgent(BaseModel):
    """AI教师角色（LLM自动生成）"""
    id: str = ""
    name: str = ""
    role: str = ""
    persona: str = ""  # 教学风格/性格描述
    avatar: str = ""  # emoji头像
    color: str = "#6366f1"  # 主题色
    voice_id: str = "female-shaonv"  # TTS声音ID
    priority: int = 0  # 出场优先级（0=主讲）


class AgentTeam(BaseModel):
    """AI教师团队"""
    agents: list[GeneratedAgent] = Field(default_factory=list)
    voice_assignments: dict[str, str] = Field(default_factory=dict)  # agent_id -> voice_id


class GenerateAgentTeamRequest(BaseModel):
    """教师团队生成请求"""
    course_title: str = ""
    outlines: list[dict[str, Any]] = Field(default_factory=list)
    requirement: str = ""
    available_voices: list[str] = Field(default_factory=lambda: [
        "female-shaonv", "female-yujie", "female-danyun",
        "male-qingshu", "male-shaoshuai"
    ])


# ============================================================
# Quiz 评分 API 模型
# ============================================================

class QuizAnswer(BaseModel):
    """学生单个答案"""
    question_index: int = 0
    selected_option: int = -1  # -1 表示未作答


class QuizGradeRequest(BaseModel):
    """Quiz评分请求"""
    questions: list[dict[str, Any]] = Field(default_factory=list)
    student_answers: list[QuizAnswer] = Field(default_factory=list)


class QuizFeedback(BaseModel):
    """单题反馈"""
    question_index: int = 0
    is_correct: bool = False
    feedback: str = ""
    correct_option: int = 0


class QuizGradeResponse(BaseModel):
    """Quiz评分响应"""
    scores: list[int] = Field(default_factory=list)  # 每题得分（0/1）
    total: float = 0.0  # 总分百分比
    passed: bool = False
    correct_count: int = 0
    total_count: int = 0
    feedback_per_question: list[QuizFeedback] = Field(default_factory=list)


# ============================================================
# 课程完成 / 庆祝数据模型
# ============================================================

class CompletionData(BaseModel):
    """课程完成庆祝数据"""
    total_scenes: int = 0
    completed_scenes: int = 0
    quiz_score: float = 0.0
    time_spent_seconds: int = 0
    badges: list[str] = Field(default_factory=list)  # 获得徽章
    next_steps: list[str] = Field(default_factory=list)  # 学习建议
    summary: str = ""  # AI生成的学习总结


class CourseCompleteRequest(BaseModel):
    """课程完成请求"""
    course_id: str = ""
    student_id: str = ""
    quiz_scores: dict[str, Any] = Field(default_factory=dict)
    time_spent: int = 0
    scenes_visited: list[int] = Field(default_factory=list)


# ============================================================
# 增强场景类型数据模型
# ============================================================

class SceneType(str, Enum):
    """场景类型扩展"""
    SLIDE = "slide"
    QUIZ = "quiz"
    EXERCISE = "exercise"
    INTERACTIVE = "interactive"
    PBL = "pbl"
    DIAGRAM = "diagram"
    CODE_EDITOR = "code"
    VIDEO = "video"


class PBLData(BaseModel):
    """PBL（项目制学习）场景数据"""
    scenario: str = ""  # 问题场景描述
    issue_board: list[dict[str, Any]] = Field(default_factory=list)  # 议题列表
    workspace: dict[str, Any] = Field(default_factory=dict)  # 工作区配置
    resources: list[dict[str, Any]] = Field(default_factory=list)  # 学习资源
    facilitator_prompt: str = ""  # 引导员提示词


class InteractiveSceneData(BaseModel):
    """交互场景数据"""
    widget_type: str = "simulation"  # simulation, diagram, code, game, visualization3d
    html_content: str = ""  # iframe渲染的HTML内容
    config: dict[str, Any] = Field(default_factory=dict)
    teacher_actions: list[dict[str, Any]] = Field(default_factory=list)


class ExerciseData(BaseModel):
    """练习场景数据"""
    title: str = ""
    exercises: list[dict[str, Any]] = Field(default_factory=list)
    speech: str = ""
    image_prompt: str = ""


class SceneOutlineV2(BaseModel):
    """增强版场景大纲（支持8种类型）"""
    id: int = 0
    title: str = ""
    type: str = "slide"  # slide/quiz/exercise/interactive/pbl/diagram/code/video
    description: str = ""
    key_points: list[str] = Field(default_factory=list)
    difficulty: str = "basic"  # basic/medium/advanced
    estimated_minutes: int = 5
    teacher_index: int = 0  # 负责该场景的教师索引
    media_required: list[str] = Field(default_factory=list)  # image/tts/video


# ============================================================
# 增强课堂聊天 API 模型
# ============================================================

class CourseChatRequestV2(BaseModel):
    """增强课堂聊天请求（支持多教师角色）"""
    student_id: str = ""
    course_id: str = ""
    scene_index: int = 0
    scene_title: str = ""
    scene_content: str = ""
    speech: str = ""
    user_input: str = Field(..., min_length=1)
    history: list[dict[str, str]] = Field(default_factory=list)
    agent_role: str = ""  # 回答教师的角色
    interactive_mode: bool = False


class ClassroomSessionState(BaseModel):
    """课堂会话状态（本地持久化）"""
    classroom_id: str = ""
    current_scene_index: int = 0
    visited_scenes: list[int] = Field(default_factory=list)
    quiz_answers: dict[str, list[QuizAnswer]] = Field(default_factory=dict)
    chat_history: list[dict[str, str]] = Field(default_factory=list)
    time_spent: int = 0


# ============================================================
# 沉浸式互动教学引擎 - 组件模型
# ============================================================

class TextCardComponent(BaseModel):
    """基础图文卡片组件"""
    type: Literal["text_card"] = "text_card"
    id: str = ""
    title: str = ""
    content: str = ""  # 支持 Markdown
    icon: str = "book"
    color_theme: str = "blue"

    @field_validator('icon')
    @classmethod
    def validate_icon(cls, v):
        allowed = {'book', 'lightbulb', 'code', 'check', 'star', 'question', 'warning', 'info'}
        return v if v in allowed else 'book'

    @field_validator('color_theme')
    @classmethod
    def validate_color_theme(cls, v):
        allowed = {'blue', 'yellow', 'green', 'purple', 'orange'}
        return v if v in allowed else 'blue'


class QuizOption(BaseModel):
    """测验选项（安全设计：不含 is_correct，前端不暴露）"""
    key: str = ""  # A/B/C/D
    text: str = ""


class QuizComponent(BaseModel):
    """互动测验组件"""
    type: Literal["quiz"] = "quiz"
    id: str = ""
    question: str = ""
    options: list[QuizOption] = Field(default_factory=list)
    explanation: str = ""  # 用户提交后从后端获取
    quiz_type: str = "single"  # single/multiple/short_answer


class CodeEditorComponent(BaseModel):
    """代码练习沙箱组件"""
    type: Literal["code_editor"] = "code_editor"
    id: str = ""
    title: str = ""
    instruction: str = ""
    starter_code: str = ""
    language: str = "python"  # python/javascript/html/sql
    expected_output: str = ""  # 仅在后端比对
    hints: list[str] = Field(default_factory=list)


class SimulationComponent(BaseModel):
    """HTML/JS 实验载体组件"""
    type: Literal["simulation"] = "simulation"
    id: str = ""
    title: str = ""
    description: str = ""
    html_content: str = ""  # 可运行的 HTML/JS 代码
    height: int = 400


# 允许的组件类型
ALLOWED_COMPONENT_TYPES = {"text_card", "quiz", "code_editor", "simulation"}


def parse_interactive_scene(data: dict) -> "InteractiveScene":
    """安全解析 InteractiveScene，拒绝未知组件类型"""
    if "components" in data:
        for i, comp in enumerate(data.get("components", [])):
            comp_type = comp.get("type", "")
            if comp_type not in ALLOWED_COMPONENT_TYPES:
                raise ValueError(
                    f"组件[{i}]类型 '{comp_type}' 不被支持，仅支持: {list(ALLOWED_COMPONENT_TYPES)}"
                )
    return InteractiveScene.model_validate(data)


class InteractiveScene(BaseModel):
    """互动场景（核心数据结构）"""
    id: str = ""
    title: str = ""
    audio_script: str = ""  # AI 语音旁白脚本文本
    components: list["InteractiveComponent"] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def text_cards(self) -> list[TextCardComponent]:
        return [c for c in self.components if c.type == "text_card"]

    @property
    def quiz_components(self) -> list[QuizComponent]:
        return [c for c in self.components if c.type == "quiz"]

    @property
    def code_components(self) -> list[CodeEditorComponent]:
        return [c for c in self.components if c.type == "code_editor"]

    @property
    def simulation_components(self) -> list[SimulationComponent]:
        return [c for c in self.components if c.type == "simulation"]


# 前向引用解决
InteractiveComponent = Union[
    TextCardComponent,
    QuizComponent,
    CodeEditorComponent,
    SimulationComponent
]


class QuizSubmission(BaseModel):
    """学生提交答案"""
    quiz_id: str = ""
    selected_key: str = ""  # A/B/C/D


class QuizGradeRequest(BaseModel):
    """Quiz 评分请求"""
    quiz_id: str = ""
    selected_key: str = ""
    question: str = ""
    options: list[QuizOption] = Field(default_factory=list)  # 完整选项（供后端比对）


class QuizGradeResponse(BaseModel):
    """Quiz 评分响应（安全设计）"""
    is_correct: bool = False
    explanation: str = ""  # 提交后才返回
    correct_key: str = ""  # 提交后才返回


class RunCodeRequest(BaseModel):
    """代码执行请求"""
    code: str = ""
    language: str = "python"
    expected_output: str = ""


class RunCodeResponse(BaseModel):
    """代码执行响应"""
    success: bool = True
    passed: bool = False
    actual_output: str = ""
    error: str = ""


class InteractiveCourseData(BaseModel):
    """支持互动场景的课程数据"""
    course_id: str = ""
    title: str = ""
    scenes: list[InteractiveScene] = Field(default_factory=list)
    teacher: TeacherInfo = Field(default_factory=TeacherInfo)
