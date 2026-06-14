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
    goal: Optional[str] = None  # 用户自定义学习目标（Tab 3 任务编排输入）


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
    capability_analysis: dict = {}  # 多维能力分析（知识适配、目标对齐、认知适配、短板强化、节奏建议）


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

LEARNING_PATH_SYSTEM_PROMPT = """你是一位资深大学教研规划智能体，专精于根据学生多维度学情数据生成个性化学习路径。

## 任务
根据提供的完整学情报告，生成或调整学生的学习路径树。你需要综合考虑学生的**全部能力维度**来规划合理的学习目标，确保每个节点都有明确的培养意图。

## 输出格式
必须输出**纯 JSON 对象**，包含 capability_analysis 和 path 两个字段，格式如下：
{
  "capability_analysis": {
    "knowledge_base_assessment": "根据知识基础（xxx），路径起点选在xxx，跳过/强化xxx",
    "learning_goal_alignment": "根据学习目标（xxx），路径侧重xxx方向",
    "cognitive_style_adaptation": "根据认知风格（xxx），推荐以xxx方式学习各节点",
    "weakness_reinforcement": "针对知识短板（xxx），安排了xxx强化内容",
    "learning_pace": "根据专注程度（xxx），建议每天学习X个节点，每X分钟休息"
  },
  "path": [
    {
      "topic": "节点标题（中文，简短）",
      "status": "completed | in_progress | locked",
      "importance": "core | high | normal",
      "estimated_time": 30,
      "prerequisites": ["前置知识1", "前置知识2"],
      "description": "该节点学习内容的一句话描述",
      "learning_goal": "本节点的学习目标，明确说明要培养什么能力/掌握什么知识",
      "capability_rationale": "该节点为何适合该学生当前能力水平的简短说明（如：因学生基础为进阶，跳过基础概念直接讲原理）",
      "targeted_dimensions": ["knowledge_base", "code_skill"],
      "children": [
        {
          "topic": "子节点标题",
          "status": "locked",
          "importance": "normal",
          "learning_goal": "子节点的学习目标",
          "capability_rationale": "子节点的能力适配说明"
        }
      ]
    }
  ]
}

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

## 多维能力映射规则
7. **知识基础适配**：knowledge_base 决定路径起点深度（零基础→概念入门，基础→核心原理，进阶→实践应用，深入→研究拓展），在节点 capability_rationale 中标注。
8. **编程能力适配**：code_skill 决定编程内容深度（新手→语法示例，基础→逻辑项目，熟练→架构设计，高手→优化重构），learning_goal 中体现能力培养层次。
9. **学习目标对齐**：learning_goal 决定路径权重方向（考试→考点习题，职业→实战项目，项目→完整流程，兴趣→广度探索，竞赛→算法技巧，科研→前沿方法），路径整体应服务于该目标。
10. **认知风格适配**：cognitive_style 影响节点描述中的学习方式建议（视觉型→图示视频，文字型→文档笔记，实践型→编码实验），在 capability_rationale 里给出适配说明。
11. **知识短板强化**：weakness 中列出的薄弱领域应在路径中有对应强化节点，标注为 core 优先级。
12. **专注度调整**：focus_level 影响路径密度和 estimated_time（高专注→每天 2-3 节点，中等→每天 1-2 节点，低→每天 1 节点并增加复习节点），在 capability_analysis.learning_pace 中给出具体建议。
"""


def _build_user_prompt(analytics: dict, goal: Optional[str] = None) -> str:
    """将学情报告构建为 LLM user prompt，突出多维能力数据。
    goal: 用户自定义学习目标，注入 prompt 引导 LLM 生成针对性路径。
    """
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

    # ── 多维能力总览（结构化，便于 LLM 逐维度决策） ──
    lines.append("### 📊 多维能力总览")
    lines.append("")
    lines.append("【知识基础】" + (" " + profile.get('knowledge_base', '未知') if profile.get('knowledge_base') else "未知"))
    lines.append("【代码能力】" + (" " + profile.get('code_skill', '未知') if profile.get('code_skill') else "未知"))
    lines.append("【学习目标】" + (" " + str(profile.get('learning_goals', [])) if profile.get('learning_goals') else "未知"))
    lines.append("【认知风格】" + (" " + profile.get('cognitive_style', '未知') if profile.get('cognitive_style') else "未知"))
    lines.append("【专注程度】" + (" " + profile.get('focus_level', '未知') if profile.get('focus_level') else "未知"))
    lines.append("【知识短板】" + (" " + profile.get('weakness', '暂无') if profile.get('weakness') else "暂无"))
    lines.append("- 思维深度: {}/95".format(cockpit.get('thinking_depth', 0)))
    lines.append("- 概念掌握率: {}%".format(cockpit.get('concept_mastery', 0)))
    lines.append("- 学习动能: {}/98".format(cockpit.get('learning_momentum', 0)))
    lines.append("- 认知等级: {}".format(cockpit.get('cognitive_level', '未知')))
    lines.append("")

    # ── 维度说明（逐维度详细描述） ──
    lines.append("### 各维度详细分析")
    lines.append("")

    # 知识基础
    kb = profile.get('knowledge_base', '')
    kb_desc_map = {
        '零基础入门': '完全零基础，需要从最基本的概念和原理开始',
        '基础入门': '有一定了解，但尚未系统掌握核心概念',
        '进阶学习': '已经掌握基础，可以进入更深入的内容',
        '深入掌握': '基础扎实，适合进行高阶研究和拓展',
    }
    lines.append("【知识基础维度】" + kb_desc_map.get(kb, '') + ("（当前等级：" + kb + "）" if kb else "无评估数据"))
    lines.append("")

    # 代码能力
    cs = profile.get('code_skill', '')
    cs_desc_map = {
        '编程新手': '几乎没有编程经验，需要从基本语法和逻辑开始',
        '基础掌握': '能写简单代码，理解基本编程概念',
        '熟练编程': '能独立完成中等复杂度项目，理解常见设计模式',
        '编程高手': '能进行代码优化、系统设计，具备工程化能力',
    }
    lines.append("【编程能力维度】" + cs_desc_map.get(cs, '') + ("（当前等级：" + cs + "）" if cs else "无评估数据"))
    lines.append("")

    # 认知风格
    cog = profile.get('cognitive_style', '')
    cog_desc_map = {
        '视觉型': '偏好图示、视频、思维导图等可视化学习材料',
        '文字型': '偏好文档、书籍、文字笔记等阅读型学习',
        '实践型': '偏好动手编码、实验操作、项目实践',
    }
    lines.append("【认知风格维度】" + cog_desc_map.get(cog, '') + ("（当前风格：" + cog + "）" if cog else "无评估数据"))
    lines.append("")

    # 专注度
    fl = profile.get('focus_level', '')
    fl_desc_map = {
        '高专注': '能够长时间集中注意力，适合密集学习安排，每次可持续2小时以上',
        '中等专注': '注意力适中，需要45-60分钟分段学习',
        '需要引导': '容易分散注意力，需要更短的学习单元和更多互动',
    }
    lines.append("【专注度维度】" + fl_desc_map.get(fl, '') + ("（当前等级：" + fl + "）" if fl else "无评估数据"))
    lines.append("")

    # 学习目标
    lgs = profile.get('learning_goals', [])
    lg_desc = {
        'exam': '应对考试——需要系统覆盖考点、重点和典型习题',
        'career': '职业发展——需要实际项目经验和行业最佳实践',
        'project': '项目实战——需要完整的项目开发流程训练',
        'interest': '兴趣探索——需要广泛的知识面覆盖和趣味性内容',
        'competition': '竞赛备战——需要算法训练和解题技巧',
        'research': '科研学术——需要论文阅读和前沿方法探索',
    }
    lg_texts = [lg_desc.get(g, g) for g in lgs] if lgs else ['未设定']
    lines.append("【学习目标维度】" + "；".join(lg_texts))
    if lgs:
        lines.append("  → 路径整体应主要服务于：" + "、".join(lg_texts[:2]))
    lines.append("")

    # 测验薄弱点
    q_summary = quizzes.get("summary", {})
    weak = q_summary.get("weak_areas", [])
    strong = q_summary.get("strong_areas", [])
    if weak:
        lines.append("【测验薄弱领域】" + str(weak) + "——路径中应优先安排这些领域的强化学习")
    if strong:
        lines.append("【测验优势领域】" + str(strong) + "——可适当减少这些领域的重复学习")
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
    if goal:
        lines.append(f"### 用户自定义学习目标")
        lines.append(f"学生特别提出了以下学习目标，请以此为核心规划路径：")
        lines.append(f"「{goal}」")
        lines.append(f"路径中的所有节点都应围绕这个目标设计，确保每个节点都为目标服务。")
        lines.append("")

    lines.append("请基于以上全部多维能力数据，生成该学生的个性化学习路径。注意：")
    lines.append("1. 每个路径节点的 learning_goal 必须明确写出该节点要培养的能力")
    lines.append("2. capability_rationale 要解释该节点为何适合该生的当前能力水平")
    lines.append("3. targeted_dimensions 至少要标注该节点针对哪些能力维度")
    lines.append("4. capability_analysis 要综合所有维度给出整体学习策略")

    return "\n".join(lines)


# ── 核心生成逻辑（可被外部调用） ──

async def generate_path_for_user(user_id: int, force_refresh: bool = False, goal: Optional[str] = None) -> GenerateLearningPathResponse:
    """
    基于学生完整学情数据，实时生成/更新个性化学习路径。
    可被 main.py 或其他模块直接调用，避免循环导入和 HTTP 开销。
    goal: 用户自定义学习目标，用于指导 LLM 生成路径。
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
                    stored = existing.get("path_json")
                    capability_analysis = {}
                    if isinstance(stored, dict) and "path" in stored:
                        capability_analysis = stored.get("capability_analysis", {})
                        path = _normalize_path(stored["path"])
                    else:
                        path = _normalize_path(stored)
                    # 融合节点状态（如果有更新的节点状态）
                    path = _merge_node_states_into_path(user_id, path)
                    return GenerateLearningPathResponse(
                        success=True,
                        path=path,
                        capability_analysis=capability_analysis,
                        reasoning=existing.get("reasoning", "缓存路径"),
                        data_sources=existing.get("data_sources", []),
                        generated_at=existing["generated_at"],
                        confidence=existing.get("confidence", 0.0),
                    )
            except Exception:
                pass

    # 3. 构建 prompt 并调用 LLM
    user_prompt = _build_user_prompt(analytics, goal=goal)
    try:
        llm_response = _call_llm(LEARNING_PATH_SYSTEM_PROMPT, user_prompt, temperature=0.4)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"路径生成失败: {e}")

    # 4. 解析路径（兼容新格式 {path, capability_analysis} 和旧格式 [...]）
    raw = _extract_json(llm_response, is_array=False) or _extract_json(llm_response, is_array=True)
    capability_analysis = {}
    if isinstance(raw, dict) and "path" in raw:
        # 新格式：{ "capability_analysis": {...}, "path": [...] }
        capability_analysis = raw.get("capability_analysis", {})
        path = _normalize_path(raw["path"])
        stored_obj = raw  # 保存完整对象（path + capability_analysis）
    elif isinstance(raw, list):
        # 旧格式：纯数组
        path = _normalize_path(raw)
        stored_obj = path
    else:
        path = []
        stored_obj = path

    if not path:
        existing = database.get_learning_path(user_id)
        existing_path = existing.get("path_json") if existing else []
        if isinstance(existing_path, dict) and "path" in existing_path:
            path = _normalize_path(existing_path["path"])
            capability_analysis = existing_path.get("capability_analysis", {})
        else:
            path = _normalize_path(existing_path)
        return GenerateLearningPathResponse(
            success=True,
            path=path,
            capability_analysis=capability_analysis,
            reasoning="LLM 返回格式异常，返回已保存路径",
            data_sources=["fallback"],
            generated_at=datetime.now().isoformat(),
            confidence=0.0,
        )

    # 5. 融合节点状态（节点表的状态更精确，覆盖 LLM 生成的状态）
    path = _merge_node_states_into_path(user_id, path)

    # 6. 同步路径到节点追踪表（初始化缺失节点）
    database.sync_path_to_nodes(user_id, path)

    # 7. 保存到数据库（若为新格式，保存完整对象；旧格式仍保存数组）
    data_sources = ["profile", "cockpit_analysis", "quiz_records", "classroom_sessions", "user_stats", "daily_route", "messages", "node_states", "capability_analysis"]
    reasoning = f"基于学生最新学情生成：认知等级 {analytics['cockpit']['cognitive_level']}，概念掌握率 {analytics['cockpit']['concept_mastery']}%，近期测验通过率 {analytics['quizzes']['summary']['pass_rate']}%"
    confidence = min(0.99, 0.7 + len(path) * 0.02)

    # 更新 stored_obj 中的 path 为融合后的版本
    if isinstance(stored_obj, dict) and "path" in stored_obj:
        stored_obj["path"] = path

    database.save_learning_path(
        user_id=user_id,
        path_json=stored_obj,
        reasoning=reasoning,
        data_sources=data_sources,
        confidence=confidence,
    )

    return GenerateLearningPathResponse(
        success=True,
        path=path,
        capability_analysis=capability_analysis,
        reasoning=reasoning,
        data_sources=data_sources,
        generated_at=datetime.now().isoformat(),
        confidence=confidence,
    )


# ── 路由 ──

@router.post("/generate", response_model=GenerateLearningPathResponse)
async def generate_learning_path(request: GenerateLearningPathRequest):
    """基于学生完整学情数据，实时生成/更新个性化学习路径。"""
    return await generate_path_for_user(request.userId, force_refresh=request.forceRefresh, goal=request.goal)


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

    stored = existing.get("path_json")
    capability_analysis = {}
    if isinstance(stored, dict) and "path" in stored:
        # 新格式：{ path, capability_analysis }
        capability_analysis = stored.get("capability_analysis", {})
        path = _normalize_path(stored["path"])
    else:
        # 旧格式：纯数组
        path = _normalize_path(stored)
    # 融合节点状态
    path = _merge_node_states_into_path(user_id, path)
    return GenerateLearningPathResponse(
        success=True,
        path=path,
        capability_analysis=capability_analysis,
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
