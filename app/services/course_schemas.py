# -*- coding: utf-8 -*-
"""Phase 2 — 9 件套课程包 Pydantic 模型.

每件 = 1 个 Artifact(LLM 输出) + 公共元数据(status / note / generated_at).
顶层 CourseBundle 汇总 9 件 + OBG/PBL 判定 + 大纲摘要,持久化到
`classroom_sessions.course_data.bundle` 顶层键,与现有 `slides_v2` / `outlines`
共存(向后兼容老课程).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional, Union

from pydantic import BaseModel, Field, field_validator


# ============================================================
# 通用基类
# ============================================================

class ArtifactBase(BaseModel):
    """每个组件产物的基类."""
    status: str = "ok"           # ok / fallback / empty
    note: str = ""               # fallback 时的提示文案
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ============================================================
# 1. 大纲 (outline) — 复用现有 SceneOutline 字段,但精简为组件视图
# ============================================================

class OutlineScene(BaseModel):
    id: str = ""
    title: str = ""
    description: str = ""
    key_points: list[str] = Field(default_factory=list)
    type: str = "slide"          # slide / quiz / interactive / code
    duration_min: int = 10


class OutlineArtifact(ArtifactBase):
    scenes: list[OutlineScene] = Field(default_factory=list)
    total_scenes: int = 0
    estimated_total_min: int = 0


# ============================================================
# 2. 教案 (lesson plan)
# ============================================================

class LessonPlanArtifact(ArtifactBase):
    """单场景的教案,9 件套生成时为每个 scene 各出一份,合并为 1 个 dict[scene_id, plan]."""
    plans: dict[str, dict[str, Any]] = Field(default_factory=dict)
    """    plans[scene_id] = {
              "objectives": ["理解 X 的定义", ...],
              "key_points": ["X 的核心是 Y", ...],
              "duration_min": 10,
              "methods": ["案例导入", "对比演示"],
              "blackboard": "X = Y + Z"
            }
    """


# ============================================================
# 3. PPT — 复用现有 CourseData.slides_v2,这里只声明 schema 不实现
# ============================================================

class PPTArtifact(ArtifactBase):
    """PPT 组件 — 本轮由 _gen_ppt 每场景调用 LLM 生成 slide_v2 数据.

    slides 字段暂存每场景产出的 slides_v2 列表,
    前端 _buildCourseData 合并进 CourseData.slides_v2.
    """
    slide_count: int = 0
    slide_titles: list[str] = Field(default_factory=list)
    slides: list[dict[str, Any]] = Field(default_factory=list)


# ============================================================
# 4. 知识图谱 (knowledge graph)
# ============================================================

class GraphNode(BaseModel):
    id: str
    label: str
    layer: int = 0               # 0=核心 1=依赖 2=延伸


class GraphEdge(BaseModel):
    from_id: str = Field(alias="from")
    to_id: str = Field(alias="to")
    label: str = ""

    model_config = {"populate_by_name": True}


class KnowledgeGraphArtifact(ArtifactBase):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)


# ============================================================
# 4b. 能力图谱 (ability_graph) — 区别于"知识地图"的能力维度
# 缺口1:PRD §4.2.2 要求"知识图谱 + 能力图谱"双图,这里补充独立结构。
# 注:不进 COMPONENT_NAMES,仅在 _component_dispatcher 中挂载,
#    不破坏现有 is_complete/ready_components 的 len==9 断言。
# ============================================================

class Competency(BaseModel):
    """单个能力节点。"""
    id: str = Field(..., min_length=1, description="kebab-case id,如 problem-decomposition")
    name: str = Field(..., min_length=1, description="如'问题分解能力'")
    category: str = "认知"                    # 认知 / 技能 / 素养
    bloom_level: int = Field(default=1, ge=1, le=6)  # Bloom 1~6
    target_level: float = Field(default=0.8, ge=0.0, le=1.0)
    description: str = ""
    related_scene_ids: list[str] = Field(default_factory=list)


class CompetencyEdge(BaseModel):
    """能力间关系(与 GraphEdge 同形,relation 语义不同)。"""
    from_id: str = Field(alias="from", description="源能力 id")
    to_id: str = Field(alias="to", description="目标能力 id")
    relation: str = "prerequisite"           # prerequisite / reinforce / transfer

    model_config = {"populate_by_name": True}


class AbilityGraphArtifact(ArtifactBase):
    """能力图谱(节点=能力,边=依赖/强化/迁移)。"""
    competencies: list[Competency] = Field(default_factory=list)
    edges: list[CompetencyEdge] = Field(default_factory=list)
    blooms_distribution: dict[str, int] = Field(default_factory=dict)
    """    {"bloom1": n1, "bloom2": n2, ..., "bloom6": n6} 各 Bloom 层能力数 """
    graph_view: dict[str, list] = Field(default_factory=dict)
    """    同 KnowledgeGraphArtifact 的 {nodes, edges},前端零成本复用
            由 _gen_ability_graph 从 competencies/edges 自动衍生 """

    def graph_view_for_frontend(self) -> dict[str, list]:
        """生成与 KnowledgeGraphArtifact 同形的 graph_view,便于前端直接渲染。"""
        return {
            "nodes": [
                {"id": c.id, "label": c.name, "layer": c.bloom_level}
                for c in self.competencies
            ],
            "edges": [
                {"from": e.from_id, "to": e.to_id, "label": e.relation}
                for e in self.edges
            ],
        }


# ============================================================
# 5. 雷达 (radar) — 课前 6 维初始值(扩展为 8 维)
# ============================================================

class RadarArtifact(ArtifactBase):
    """课前雷达,数值 0~100. 复用 LearningPortrait 字段名.

    缺口2:在原 6 维基础上扩展 2 维 — `process`(学习过程投入度) +
    `innovation`(创新思维表现),对齐 PRD §4.2.6 评分四维。
    老代码读 6 维仍可工作(新字段有默认值)。
    """
    knowledge_mastery: float = 0.0
    code_skill: float = 0.0
    cognitive_level: float = 0.0
    learning_goal: float = 0.0
    weakness: float = 0.0
    focus_level: float = 0.0
    # ---- 新增 2 维(向后兼容,老读取只读 6 维)----
    process: float = 0.0                     # 学习过程投入度
    innovation: float = 0.0                  # 创新思维表现
    # 若有画像,会从 LearningPortrait 聚合,本字段是 LLM 估的"完成本课程后预期值"
    post_course_estimate: dict[str, float] = Field(default_factory=dict)


# ============================================================
# 6. 项目 (project)
# ============================================================

class ProjectMilestone(BaseModel):
    title: str = ""
    description: str = ""
    deliverable: str = ""


class ProjectArtifact(ArtifactBase):
    title: str = ""
    scenario: str = ""           # 真实问题场景
    background: str = ""         # 项目背景
    requirements: list[str] = Field(default_factory=list)
    acceptance: list[str] = Field(default_factory=list)  # 验收标准
    milestones: list[ProjectMilestone] = Field(default_factory=list)
    estimated_hours: int = 0
    difficulty: str = "medium"   # easy / medium / hard


# ============================================================
# 7. 案例 (case study)
# ============================================================

class CaseStudyArtifact(ArtifactBase):
    title: str = ""
    story: str = ""              # 故事正文
    decision_points: list[str] = Field(default_factory=list)   # 关键决策点
    reflection: list[str] = Field(default_factory=list)        # 反思题
    takeaway: str = ""           # 案例启示


# ============================================================
# 8. 习题 (exercises)
# ============================================================

class ExerciseQuestion(BaseModel):
    id: int = 0
    type: str = "single"         # single / multi / fill / code
    stem: str = ""
    options: list[str] = Field(default_factory=list)   # 单选/多选
    answer: Any = None           # 单选=index(int) / 多选=list[int] / 填空=str / 编程=str(参考解)
    rubric: str = ""             # 评分规则
    difficulty: str = "medium"
    related_scene_id: str = ""


class ExerciseArtifact(ArtifactBase):
    questions: list[ExerciseQuestion] = Field(default_factory=list)
    by_scene: dict[str, list[int]] = Field(default_factory=dict)  # scene_id -> [question_id]


# ============================================================
# 9. 问卷 (survey) — 课前自测
# ============================================================

class SurveyQuestion(BaseModel):
    id: int = 0
    type: str = "single"         # single / multi / scale / text
    stem: str = ""
    options: list[str] = Field(default_factory=list)
    required: bool = True


class SurveySection(BaseModel):
    title: str = ""
    description: str = ""
    questions: list[SurveyQuestion] = Field(default_factory=list)


class SurveyArtifact(ArtifactBase):
    sections: list[SurveySection] = Field(default_factory=list)
    estimated_minutes: int = 5


# ============================================================
# 顶层 CourseBundle
# ============================================================

COMPONENT_NAMES = (
    "outline", "plan", "ppt", "graph", "radar",
    "project", "case", "exercises", "survey",
)


class CourseBundle(BaseModel):
    """9 件套课程包,持久化到 classroom_sessions.course_data.bundle 顶层键."""
    components: dict[str, dict] = Field(default_factory=dict)
    """    components["outline"] = OutlineArtifact.model_dump()
            components["plan"]    = LessonPlanArtifact.model_dump()
            ... 共 9 件
    """
    obg_pbl_mode: str = "obg"          # obg / pbl
    obg_pbl_rationale: str = ""        # LLM 判定理由(展示给用户)
    outline_summary: dict[str, Any] = Field(default_factory=dict)
    """    {title, total_scenes, scene_titles[], estimated_min}
    """
    brainstorm: dict[str, Any] = Field(default_factory=dict)
    """    {slots:{goal,base,path,case}, turns:[{q,a}], mode}
    """
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def is_complete(self) -> bool:
        """是否 9 件全部 status==ok (不含 fallback)."""
        return all(
            self.components.get(name, {}).get("status") == "ok"
            for name in COMPONENT_NAMES
        )

    def ready_components(self) -> list[str]:
        return [n for n in COMPONENT_NAMES if self.components.get(n, {}).get("status") == "ok"]

    def fallback_components(self) -> list[str]:
        return [n for n in COMPONENT_NAMES if self.components.get(n, {}).get("status") == "fallback"]


# ============================================================
# 脑暴端点的请求/响应模型
# ============================================================

class BrainstormStartRequest(BaseModel):
    requirement: str = Field(..., min_length=1)
    student_id: Union[int, str] = ""

    @field_validator("student_id", mode="before")
    @classmethod
    def _coerce_student_id(cls, v: Any) -> Any:
        # /api/login/guest returns an int userId; accept it and normalise to str.
        return str(v) if v is not None else v


class BrainstormStartResponse(BaseModel):
    brainstorm_id: str
    turn: int                       # 1
    total_turns: int = 3
    slot: str                       # goal / base / path
    question: str
    options: list[str] = Field(default_factory=list)
    allow_custom: bool = True
    allow_skip: bool = True


class BrainstormTurnRequest(BaseModel):
    brainstorm_id: str
    user_choice: Optional[str] = None    # 选了某个选项
    user_text: Optional[str] = None      # 或自定义文本
    skip: bool = False


class BrainstormTurnResponse(BaseModel):
    brainstorm_id: str
    turn: int                       # 推进后的轮次
    total_turns: int = 3
    done: bool = False              # 3 轮收齐,转交大纲生成
    # 若 done=True
    obg_pbl_mode: str = ""
    obg_pbl_rationale: str = ""
    outline: dict[str, Any] = Field(default_factory=dict)
    # 若 done=False
    slot: str = ""
    question: str = ""
    options: list[str] = Field(default_factory=list)


class BrainstormConfirmRequest(BaseModel):
    brainstorm_id: str
    outline_edit: dict[str, Any] = Field(default_factory=dict)
    obg_pbl_override: str = ""      # 用户可手动覆盖 LLM 判定


class BrainstormConfirmResponse(BaseModel):
    brainstorm_id: str
    locked: bool = True
    obg_pbl_mode: str
    outline: dict[str, Any]
    # 给 bundle 用的最小上下文
    outline_summary: dict[str, Any]
