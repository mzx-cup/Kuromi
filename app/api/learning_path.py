"""
学习路径实时生成 API

基于学生全量学情数据，聚合后通过 LLM 生成个性化学习路径。
端点：POST /api/learning-path/generate
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Optional

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import db as database
from app.services.analytics_builder import build_student_analytics
from config import settings

router = APIRouter()


# ── Pydantic Models ──

class GenerateLearningPathRequest(BaseModel):
    userId: int
    forceRefresh: bool = False  # 强制刷新，忽略缓存


class LearningPathNode(BaseModel):
    topic: str
    status: str  # completed | in_progress | locked
    importance: Optional[str] = "normal"  # core | high | normal
    estimated_time: Optional[int] = None  # 分钟
    prerequisites: Optional[list[str]] = []
    description: Optional[str] = ""
    children: Optional[list[dict]] = []


class GenerateLearningPathResponse(BaseModel):
    success: bool
    path: list[dict]
    reasoning: str
    data_sources: list[str]
    generated_at: str
    confidence: float


# ── LLM 调用 ──

def _call_llm(system_prompt: str, user_prompt: str, temperature: float = 0.4) -> str:
    """调用讯飞大模型生成内容。"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.xunfei_api_key}",
    }
    payload = {
        "model": settings.model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
    }
    try:
        resp = requests.post(settings.xunfei_api_url, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        body = resp.json()
        return body["choices"][0]["message"]["content"]
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"大模型调用失败: {e}")


def _extract_json(text: str, is_array: bool = False) -> Any:
    """从 LLM 响应中提取 JSON。"""
    try:
        pattern = r"\[.*\]" if is_array else r"\{.*\}"
        match = re.search(pattern, text.replace("\n", ""), re.DOTALL)
        if match:
            return json.loads(match.group())
        return json.loads(text)
    except Exception:
        # 尝试从 markdown code block 中提取
        cleaned = text.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```")[1].split("```")[0].strip()
        try:
            return json.loads(cleaned)
        except Exception:
            return None


def _normalize_path(value: Any) -> list[dict]:
    """统一路径格式为 list[dict]。"""
    if value is None:
        return []
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []
    if isinstance(value, list):
        return [node if isinstance(node, dict) else {"topic": str(node), "status": "locked"} for node in value]
    return []


# ── Prompt 构建 ──

LEARNING_PATH_SYSTEM_PROMPT = """你是一位资深大学教研规划智能体，专精于根据学生学情数据生成个性化学习路径。

## 任务
根据提供的完整学情报告，生成或调整学生的学习路径树。

## 输出格式
必须输出**纯 JSON 数组**，格式如下：
[
  {
    "topic": "节点标题（中文，简短）",
    "status": "completed | in_progress | locked",
    "importance": "core | high | normal",
    "estimated_time": 30,
    "prerequisites": ["前置知识1", "前置知识2"],
    "description": "该节点学习内容的一句话描述",
    "children": [
      {"topic": "子节点标题", "status": "locked", "importance": "normal"}
    ]
  }
]

## 规则
1. **学情驱动**：必须根据学生的掌握率、薄弱点、学习风格、认知等级来调整路径。
2. **优先级**：
   - 学生薄弱且重要的知识点 → 前置、标为 core/high
   - 学生已掌握的知识点 → 标为 completed，可跳过或快速复习
   - 学生正在学习的知识点 → 标为 in_progress
   - 尚未接触但属于进阶的内容 → 标为 locked
3. **层级结构**：最多支持一级 children，不要嵌套过深。
4. **estimated_time**：根据认知风格调整。视觉型学生给更多图示时间，实践型给更多编码时间。
5. **禁止输出**任何 JSON 之外的文本、解释、markdown 标记。
6. **路径节点数量**：一般 5-12 个主节点，每个主节点可有 0-4 个子节点。
"""


def _build_user_prompt(analytics: dict) -> str:
    """将学情报告构建为 LLM user prompt。"""
    profile = analytics.get("profile", {})
    cockpit = analytics.get("cockpit", {})
    quizzes = analytics.get("quizzes", {})
    classrooms = analytics.get("classrooms", {})
    stats = analytics.get("study_stats", {})
    current_path = analytics.get("current_path", {})
    conversations = analytics.get("conversations", {})
    daily_route = analytics.get("daily_route", {})

    lines = []
    lines.append("## 学生学情报告")
    lines.append("")
    lines.append("### 基础画像")
    lines.append(f"- 学习风格: {profile.get('learning_style', '未知')}")
    lines.append(f"- 认知等级: {profile.get('cognitive_level', '未知')}")
    lines.append(f"- 认知风格: {profile.get('cognitive_style', '未知')}")
    lines.append(f"- 专注度: {profile.get('focus_level', '未知')}")
    lines.append(f"- 学习目标: {profile.get('learning_goals', [])}")
    lines.append(f"- 知识基础: {profile.get('knowledge_base', '未知')}")
    lines.append(f"- 代码能力: {profile.get('code_skill', '未知')}")
    lines.append(f"- 知识短板: {profile.get('weakness', '暂无')}")
    lines.append("")
    lines.append("### 驾驶舱指标")
    lines.append(f"- 思维深度: {cockpit.get('thinking_depth', 0)}/95")
    lines.append(f"- 概念掌握率: {cockpit.get('concept_mastery', 0)}/95")
    lines.append(f"- 学习动能: {cockpit.get('learning_momentum', 0)}/98")
    lines.append(f"- 专注休息比: {cockpit.get('focus_ratio', 0)}%")
    lines.append(f"- 交互次数: {cockpit.get('interaction_count', 0)}")
    lines.append(f"- 学习时长: {cockpit.get('learning_minutes', 0)} 分钟")
    lines.append(f"- 完成任务: {cockpit.get('completed_tasks', 0)}")
    lines.append("")
    lines.append("### 测验表现")
    q_summary = quizzes.get("summary", {})
    lines.append(f"- 平均分: {q_summary.get('avg_score', 0)}")
    lines.append(f"- 通过率: {q_summary.get('pass_rate', 0)}%")
    lines.append(f"- 薄弱领域: {q_summary.get('weak_areas', [])}")
    lines.append(f"- 优势领域: {q_summary.get('strong_areas', [])}")
    if quizzes.get("records"):
        lines.append("- 近期测验详情:")
        for q in quizzes["records"][:3]:
            lines.append(f"  - {q.get('quiz_id', '未知')}: {q.get('score', 0)}/{q.get('total', 0)} (通过: {q.get('passed', False)})")
    lines.append("")
    lines.append("### 课堂进度")
    c_summary = classrooms.get("summary", {})
    lines.append(f"- 累计学习时长: {c_summary.get('total_time_spent', 0)} 秒")
    lines.append(f"- 已完成课堂: {c_summary.get('completed_count', 0)}")
    lines.append(f"- 进行中课堂: {c_summary.get('active_count', 0)}")
    lines.append(f"- 近期课程: {c_summary.get('recent_courses', [])}")
    lines.append("")
    lines.append("### 学习统计")
    lines.append(f"- 连续学习天数: {stats.get('streak_days', 0)}")
    lines.append(f"- 闪卡复习: {stats.get('flashcards_studied', 0)}")
    lines.append(f"- 近期主题: {stats.get('recent_topics', [])}")
    lines.append("")
    lines.append("### 今日航线")
    lines.append(f"- 今日任务数: {daily_route.get('tasks_count', 0)}")
    lines.append(f"- 已完成: {daily_route.get('completed_count', 0)}")
    lines.append("")
    lines.append("### 当前路径预览")
    preview = current_path.get("preview", [])
    for p in preview[:5]:
        lines.append(f"- [{p.get('status', 'locked')}] {p.get('topic', '')}")
    lines.append("")
    lines.append("### 近期对话主题")
    lines.append(f"{conversations.get('recent_topics', [])}")
    lines.append("")
    lines.append("请基于以上学情，生成该学生的个性化学习路径。")

    return "\n".join(lines)


# ── 核心生成逻辑（可被外部调用） ──

async def generate_path_for_user(user_id: int, force_refresh: bool = False) -> GenerateLearningPathResponse:
    """
    基于学生完整学情数据，实时生成/更新个性化学习路径。
    可被 main.py 或其他模块直接调用，避免循环导入和 HTTP 开销。
    """
    # 1. 聚合学情
    try:
        analytics = build_student_analytics(user_id)
    except Exception as e:
        print(f"[LearningPath] 学情聚合失败: {e}")
        existing = database.get_learning_path(user_id)
        path = _normalize_path(existing.get("path_json")) if existing else []
        return GenerateLearningPathResponse(
            success=True,
            path=path,
            reasoning="学情数据聚合异常，返回已保存路径",
            data_sources=["local_cache"],
            generated_at=datetime.now().isoformat(),
            confidence=0.0,
        )

    # 2. 检查缓存（5分钟防抖）
    if not force_refresh:
        existing = database.get_learning_path(user_id)
        if existing and existing.get("generated_at"):
            try:
                last_gen = datetime.fromisoformat(existing["generated_at"])
                if (datetime.now() - last_gen).total_seconds() < 300:
                    path = _normalize_path(existing.get("path_json"))
                    return GenerateLearningPathResponse(
                        success=True,
                        path=path,
                        reasoning=existing.get("reasoning", "缓存路径"),
                        data_sources=existing.get("data_sources", []),
                        generated_at=existing["generated_at"],
                        confidence=existing.get("confidence", 0.0),
                    )
            except Exception:
                pass

    # 3. 构建 prompt 并调用 LLM
    user_prompt = _build_user_prompt(analytics)
    try:
        llm_response = _call_llm(LEARNING_PATH_SYSTEM_PROMPT, user_prompt, temperature=0.4)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"路径生成失败: {e}")

    # 4. 解析路径
    raw_path = _extract_json(llm_response, is_array=True)
    if not raw_path or not isinstance(raw_path, list):
        raw_path = _extract_json(llm_response, is_array=True)
    path = _normalize_path(raw_path)

    if not path:
        existing = database.get_learning_path(user_id)
        path = _normalize_path(existing.get("path_json")) if existing else []
        return GenerateLearningPathResponse(
            success=True,
            path=path,
            reasoning="LLM 返回格式异常，返回已保存路径",
            data_sources=["fallback"],
            generated_at=datetime.now().isoformat(),
            confidence=0.0,
        )

    # 5. 保存到数据库
    data_sources = ["profile", "cockpit_analysis", "quiz_records", "classroom_sessions", "user_stats", "daily_route", "messages"]
    reasoning = f"基于学生最新学情生成：认知等级 {analytics['cockpit']['cognitive_level']}，概念掌握率 {analytics['cockpit']['concept_mastery']}%，近期测验通过率 {analytics['quizzes']['summary']['pass_rate']}%"
    confidence = min(0.99, 0.7 + len(path) * 0.02)

    database.save_learning_path(
        user_id=user_id,
        path_json=path,
        reasoning=reasoning,
        data_sources=data_sources,
        confidence=confidence,
    )

    return GenerateLearningPathResponse(
        success=True,
        path=path,
        reasoning=reasoning,
        data_sources=data_sources,
        generated_at=datetime.now().isoformat(),
        confidence=confidence,
    )


# ── 路由 ──

@router.post("/generate", response_model=GenerateLearningPathResponse)
async def generate_learning_path(request: GenerateLearningPathRequest):
    """基于学生完整学情数据，实时生成/更新个性化学习路径。"""
    return await generate_path_for_user(request.userId, force_refresh=request.forceRefresh)


@router.get("/current/{user_id}", response_model=GenerateLearningPathResponse)
async def get_current_learning_path(user_id: int):
    """
    获取学生当前保存的学习路径（不触发 LLM 生成）。
    """
    existing = database.get_learning_path(user_id)
    if not existing:
        return GenerateLearningPathResponse(
            success=True,
            path=[],
            reasoning="暂无学习路径",
            data_sources=[],
            generated_at=datetime.now().isoformat(),
            confidence=0.0,
        )

    path = _normalize_path(existing.get("path_json"))
    return GenerateLearningPathResponse(
        success=True,
        path=path,
        reasoning=existing.get("reasoning", ""),
        data_sources=existing.get("data_sources", []),
        generated_at=existing.get("generated_at", datetime.now().isoformat()),
        confidence=existing.get("confidence", 0.0),
    )
