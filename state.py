from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

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
