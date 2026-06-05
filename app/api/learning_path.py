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


# ── 节点级增量刷新模型 ──

class NodeUpdateItem(BaseModel):
    node_id: str
    status: str | None = None
    mastery_score: float | None = None
    rule_verified: bool | None = None
    llm_verified: bool | None = None
    completion_source: str | None = None
    evidence_json: dict | None = None


class BatchUpdateNodesRequest(BaseModel):
    userId: int
    nodes: list[NodeUpdateItem]


class EvaluateNodesRequest(BaseModel):
    userId: int
    node_ids: list[str] | None = None  # None 表示评估所有节点


class NodeStateResponse(BaseModel):
    success: bool
    nodes: list[dict]
    evaluated_count: int = 0
    changed_count: int = 0


# ── LLM 调用 ──

def _call_llm(system_prompt: str, user_prompt: str, temperature: float = 0.4) -> str:
    """调用 MiniMax-Text-01 大模型生成内容（已完全切换自讯飞）"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.minimax_api_key}",
    }
    payload = {
        "model": settings.minimax_model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": 8192,
    }
    try:
        resp = requests.post(
            f"{settings.minimax_api_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=120,
        )
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


def _merge_node_states_into_path(user_id: int, path: list[dict]) -> list[dict]:
    """将节点追踪表中的状态融合到路径中（节点表优先）。"""
    nodes_map = {}
    try:
        nodes = database.get_learning_path_nodes(user_id)
        for n in nodes:
            nid = n.get('node_id')
            if nid:
                nodes_map[nid] = n
    except Exception as e:
        print(f"[_merge_node_states] 获取节点状态失败: {e}")

    def _merge_node(node, parent_id=None):
        topic = node.get('topic') or node.get('name') or node.get('title', '')
        node_id = node.get('id') or node.get('node_id')
        if not node_id and topic:
            import re
            slug = re.sub(r'[^\w一-鿿]+', '_', topic).strip('_').lower()
            node_id = f"topic:{slug}" if not parent_id else f"{parent_id}:{slug}"

        if node_id and node_id in nodes_map:
            ns = nodes_map[node_id]
            # 节点表状态优先（更精确）
            if ns.get('status'):
                node['status'] = ns['status']
            # 添加掌握度元数据
            if ns.get('mastery_score'):
                node['mastery_score'] = ns['mastery_score']
            if ns.get('completion_source'):
                node['completion_source'] = ns['completion_source']
            if ns.get('rule_verified'):
                node['rule_verified'] = bool(ns['rule_verified'])
            if ns.get('llm_verified'):
                node['llm_verified'] = bool(ns['llm_verified'])

        # 递归处理 children
        if node.get('children'):
            for child in node['children']:
                _merge_node(child, parent_id=node_id)

    for node in path:
        _merge_node(node)

    return path


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
                    # 融合节点状态（如果有更新的节点状态）
                    path = _merge_node_states_into_path(user_id, path)
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

    # 5. 融合节点状态（节点表的状态更精确，覆盖 LLM 生成的状态）
    path = _merge_node_states_into_path(user_id, path)

    # 6. 同步路径到节点追踪表（初始化缺失节点）
    database.sync_path_to_nodes(user_id, path)

    # 7. 保存到数据库
    data_sources = ["profile", "cockpit_analysis", "quiz_records", "classroom_sessions", "user_stats", "daily_route", "messages", "node_states"]
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
    返回的路径已融合节点追踪表中的最新状态。
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
    # 融合节点状态
    path = _merge_node_states_into_path(user_id, path)
    return GenerateLearningPathResponse(
        success=True,
        path=path,
        reasoning=existing.get("reasoning") or "",
        data_sources=existing.get("data_sources") or [],
        generated_at=existing.get("generated_at") or datetime.now().isoformat(),
        confidence=existing.get("confidence", 0.0) or 0.0,
    )


# ── 节点级增量刷新 API ──

@router.post("/nodes/update", response_model=NodeStateResponse)
async def update_learning_path_nodes(request: BatchUpdateNodesRequest):
    """批量更新知识点节点状态（前端或事件系统调用）。"""
    updated = []
    changed = 0
    for item in request.nodes:
        node_data = {
            'node_id': item.node_id,
            'status': item.status,
            'mastery_score': item.mastery_score,
            'rule_verified': 1 if item.rule_verified else 0,
            'llm_verified': 1 if item.llm_verified else 0,
            'completion_source': item.completion_source,
            'evidence_json': item.evidence_json,
        }
        # 过滤 None 值
        node_data = {k: v for k, v in node_data.items() if v is not None}
        existing = database.get_learning_path_node(request.userId, item.node_id)
        old_status = existing.get('status') if existing else None
        success = database.save_learning_path_node(request.userId, node_data)
        if success:
            updated.append(item.node_id)
            if item.status and item.status != old_status:
                changed += 1

    return NodeStateResponse(
        success=True,
        nodes=[{"node_id": nid} for nid in updated],
        evaluated_count=len(updated),
        changed_count=changed,
    )


@router.get("/nodes/{user_id}", response_model=NodeStateResponse)
async def get_learning_path_nodes(user_id: int):
    """获取学生的所有知识点节点状态。"""
    nodes = database.get_learning_path_nodes(user_id)
    return NodeStateResponse(
        success=True,
        nodes=nodes,
        evaluated_count=0,
        changed_count=0,
    )


@router.post("/nodes/evaluate", response_model=NodeStateResponse)
async def evaluate_learning_path_nodes(request: EvaluateNodesRequest):
    """触发规则引擎评估节点状态（事件系统调用）。"""
    from app.services.learning_path.rule_engine import (
        evaluate_node, reevaluate_all_nodes
    )

    results = []
    changed = 0

    if request.node_ids:
        # 评估指定节点
        for node_id in request.node_ids:
            try:
                result = evaluate_node(request.userId, node_id)
                results.append({
                    "node_id": result.node_id,
                    "status": result.status,
                    "mastery_score": result.mastery_score,
                    "rule_verified": result.rule_verified,
                    "completion_source": result.completion_source,
                })
                if result.rule_verified:
                    changed += 1
            except Exception as e:
                print(f"[evaluate_nodes] 节点 {node_id} 评估失败: {e}")
    else:
        # 评估所有节点
        all_results = reevaluate_all_nodes(request.userId)
        for result in all_results:
            results.append({
                "node_id": result.node_id,
                "status": result.status,
                "mastery_score": result.mastery_score,
                "rule_verified": result.rule_verified,
                "completion_source": result.completion_source,
            })
            if result.rule_verified:
                changed += 1

    return NodeStateResponse(
        success=True,
        nodes=results,
        evaluated_count=len(results),
        changed_count=changed,
    )
