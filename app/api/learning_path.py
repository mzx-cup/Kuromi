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
from pydantic import BaseModel, Field

import db as database
from app.services.analytics_builder import build_student_analytics
from config import settings

router = APIRouter()


# ── Pydantic Models ──

class GenerateLearningPathRequest(BaseModel):
    userId: int
    forceRefresh: bool = False  # 强制刷新，忽略缓存
    goal: Optional[str] = None  # 用户自定义学习目标（Tab 3 任务编排输入）
    difficulty_pref: int = Field(default=3, ge=1, le=5, description="Agent 控制塔难度偏好 1-5")
    strategy: str = Field(default="auto", description="Agent 控制塔教学策略")
    injected_knowledge: list[str] = Field(default_factory=list, description="Agent 控制塔注入知识标签")


class GoalEvidence(BaseModel):
    """节点学习目标的证据追溯（real-time 真实 ID 引用）。"""
    quiz_ids: Optional[list[str]] = []
    classroom_ids: Optional[list[str]] = []
    profile_signals: Optional[list[str]] = []
    interaction_stats_refs: Optional[dict] = {}
    rationale_excerpt: Optional[str] = ""


class LearningPathNode(BaseModel):
    topic: str
    status: str  # completed | in_progress | locked
    importance: Optional[str] = "normal"  # core | high | normal
    estimated_time: Optional[int] = None  # 分钟
    prerequisites: Optional[list[str]] = []
    description: Optional[str] = ""
    learning_goal: Optional[str] = ""
    capability_rationale: Optional[str] = ""
    targeted_dimensions: Optional[list[str]] = []
    goal_evidence: Optional[GoalEvidence] = None
    goal_evidence_validated: Optional[bool] = False
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


def _downgrade_completed_to_inprogress(path: list[dict]) -> None:
    """递归把路径中所有 `completed` 节点降级为 `in_progress`。

    适用场景：用户尚未完成学情评估，路径中不应出现"已掌握"的节点。
    LLM 即使收到强指令仍可能误标，本函数作为最后一道防线，强制纠正。
    """
    for node in path:
        if isinstance(node, dict):
            if node.get('status') == 'completed':
                node['status'] = 'in_progress'
                # 清空可能误生成的"已掌握"描述
                desc = node.get('description', '')
                if desc:
                    node['description'] = desc.replace('已掌握', '待学习').replace('已学完', '待学习').replace('已学毕', '待学习')
            children = node.get('children')
            if isinstance(children, list):
                _downgrade_completed_to_inprogress(children)


# 学习目标 6 维白名单（与 system prompt 规则 16 保持一致）
_TARGETED_DIMENSIONS_WHITELIST = {
    "knowledge_base", "code_skill", "cognitive_style",
    "focus_level", "learning_goals", "weakness",
}
# 描述学习目标时禁止使用的模糊词（与 LLM 规则 14 保持一致）
_FUZZY_GOAL_WORDS = ("了解", "理解", "认识", "知道")
# 节点 description / learning_goal 中"已掌握"类违禁词（与 _downgrade_completed_to_inprogress 一致）
_FORBIDDEN_COMPLETION_WORDS = ("已掌握", "已学完", "已学毕", "掌握完毕", "熟练掌握")


def _validate_and_ground_learning_goals(path: list[dict], analytics: dict) -> dict:
    """校验路径节点的 learning_goal / goal_evidence 真实性、实时性、贴合性。

    校验项：
    1. targeted_dimensions ∈ 6 维白名单
    2. 违规词扫描（描述/目标中含"已掌握"等"虚假完成"表述）
    3. goal_evidence.quiz_ids / classroom_ids 必须在 evidence_signals 中真实存在
    4. capability_rationale 与 profile 一致性（避免"零基础→已掌握基础"自相矛盾）

    失败策略：标记但不剔除（在节点上写 `goal_evidence_validated=false`）。
    整路径不通过时仍返回完整 path，由前端按节点级红色角标提示。

    返回: {valid_count, invalid_count, invalid_node_ids, reason_map}
    """
    evidence = analytics.get("evidence_signals", {}) or {}
    valid_quiz_ids = set(evidence.get("quiz_ids", []) or [])
    valid_classroom_ids = set(evidence.get("classroom_ids", []) or [])
    valid_profile_signals = set(evidence.get("profile_signals", []) or [])
    profile = analytics.get("profile", {}) or {}
    cockpit = analytics.get("cockpit", {}) or {}

    kb = profile.get("knowledge_base", "")
    cs = profile.get("code_skill", "")

    valid_count = 0
    invalid_count = 0
    invalid_node_ids: list[str] = []
    reason_map: dict[str, list[str]] = {}

    def _check_node(node: dict) -> None:
        nonlocal valid_count, invalid_count
        if not isinstance(node, dict):
            return

        topic = node.get("topic", "") or node.get("name", "") or node.get("title", "")
        node_id = node.get("id") or node.get("node_id") or topic
        reasons: list[str] = []

        # 1) targeted_dimensions 白名单
        dims = node.get("targeted_dimensions") or []
        if dims and isinstance(dims, list):
            bad_dims = [d for d in dims if isinstance(d, str) and d not in _TARGETED_DIMENSIONS_WHITELIST]
            if bad_dims:
                reasons.append(f"targeted_dimensions 含非白名单维度: {bad_dims}")

        # 2) 违规词扫描（description / learning_goal / capability_rationale）
        text_fields = [str(node.get("description", "")), str(node.get("learning_goal", "")),
                       str(node.get("capability_rationale", ""))]
        for txt in text_fields:
            for bad in _FORBIDDEN_COMPLETION_WORDS:
                if bad in txt:
                    reasons.append(f"含违禁词「{bad}」")
                    break
        # 模糊词（仅在 learning_goal 里检查）
        lg = str(node.get("learning_goal", "") or "")
        for fuzzy in _FUZZY_GOAL_WORDS:
            # 模糊词必须出现且后面不是"要"或"，"才算 — 简单实现：含模糊词且目标 < 25 字
            if fuzzy in lg and len(lg) < 25 and not any(s in lg for s in ["能", "会", "达到", "通过"]):
                reasons.append(f"learning_goal 含模糊词「{fuzzy}」且无可验证标准")
                break

        # 3) goal_evidence 真实性
        ge = node.get("goal_evidence")
        if ge and isinstance(ge, dict):
            fake_quiz = [q for q in (ge.get("quiz_ids") or []) if q not in valid_quiz_ids]
            if fake_quiz:
                reasons.append(f"goal_evidence.quiz_ids 含不存在的 ID: {fake_quiz}")
            fake_cls = [c for c in (ge.get("classroom_ids") or []) if c not in valid_classroom_ids]
            if fake_cls:
                reasons.append(f"goal_evidence.classroom_ids 含不存在的 ID: {fake_cls}")
            fake_prof = [p for p in (ge.get("profile_signals") or []) if p not in valid_profile_signals]
            if fake_prof:
                reasons.append(f"goal_evidence.profile_signals 含不存在的画像字段: {fake_prof}")
            # rationale_excerpt 必填
            if not ge.get("rationale_excerpt"):
                reasons.append("goal_evidence.rationale_excerpt 缺失")
        else:
            # 没填 goal_evidence 也算未通过（system prompt 规则 15 强制要求）
            reasons.append("缺少 goal_evidence 字段")

        # 4) capability_rationale 一致性（避免零基础自夸"已掌握基础"）
        rationale = str(node.get("capability_rationale", "") or "")
        if kb in ("零基础入门", "基础入门") and any(w in rationale for w in ("已掌握基础", "基础扎实", "基础很好", "基础强")):
            reasons.append(f"capability_rationale 与 profile.knowledge_base={kb} 矛盾")
        if cs in ("编程新手",) and any(w in rationale for w in ("熟练编程", "编程高手", "代码能力强")):
            reasons.append(f"capability_rationale 与 profile.code_skill={cs} 矛盾")

        # 写入校验结果
        if reasons:
            node["goal_evidence_validated"] = False
            node["_validation_reasons"] = reasons[:5]  # 限制条数
            invalid_count += 1
            invalid_node_ids.append(node_id)
            reason_map[node_id] = reasons[:5]
        else:
            node["goal_evidence_validated"] = True
            valid_count += 1

        # 递归处理子节点
        children = node.get("children")
        if isinstance(children, list):
            for child in children:
                _check_node(child)

    if isinstance(path, list):
        for n in path:
            _check_node(n)

    return {
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "invalid_node_ids": invalid_node_ids,
        "reason_map": reason_map,
    }


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
      "learning_goal": "本节点的学习目标（结构化）",
      "capability_rationale": "该节点为何适合该学生当前能力水平的简短说明（如：因学生基础为进阶，跳过基础概念直接讲原理）",
      "targeted_dimensions": ["knowledge_base", "code_skill"],
      "goal_evidence": {
        "quiz_ids": ["python_basics_q1", "loop_q3"],
        "classroom_ids": ["intro_lesson_2"],
        "profile_signals": ["knowledge_base=零基础入门", "code_skill=编程新手", "learning_goals=exam"],
        "interaction_stats_refs": {
          "concept_mastery": 67,
          "weak_areas": ["递归"]
        },
        "rationale_excerpt": "因最近 5 次测验中 3 次未通过递归相关题目"
      },
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

13. **completed 状态的硬约束**：仅当该学生有**真实的学习证据**（测验通过、课堂完成、对话中明确表达掌握）时，才能把节点标为 completed。**禁止把"看起来很基础"的节点默认为 completed**。如果学情数据中没有"已掌握该节点"的证据，则该节点必须标为 `in_progress` 或 `locked`，不能标为 `completed`。

14. **结构化 learning_goal（强制）**：每个节点的 `learning_goal` 必须是以下结构（一句话）：

    `要培养 {维度} 维度的 {能力}，达到 {可验证标准}，基于证据 {evidence_id} 的 {指标} 数值 {value}`

    示例：
    - `要培养 code_skill 维度的 Python 循环控制能力，达到能独立编写嵌套 for 循环且无语法错误，基于证据 quiz_id=loop_q3 的 pass_rate 0.4`
    - `要培养 knowledge_base 维度的递归基础概念，达到能口述递归三要素并写简单递归函数，基于证据 profile.knowledge_base=零基础入门`

    - `{维度}` ∈ {knowledge_base, code_skill, cognitive_style, focus_level, learning_goals, weakness}（6 维白名单）
    - `{evidence_id}` 必须是下述"可引用证据池"中真实存在的 ID；找不到证据时写 `profile.knowledge_base=<等级>` 或 `cockpit.concept_mastery=<数值>`
    - `{可验证标准}` 必须是可量化或可观察的行为（"能写...","会解释...","通过某测验..."），禁止写"了解""理解"等模糊词

15. **goal_evidence（强制输出）**：每个 path 节点（包含 children）必须输出 `goal_evidence` 对象，引用下方"可引用证据池"中真实存在的 ID：

    {
      "quiz_ids": ["<来自 evidence_signals.quiz_ids 的真实 ID>"],
      "classroom_ids": ["<来自 evidence_signals.classroom_ids 的真实 ID>"],
      "profile_signals": ["<来自 evidence_signals.profile_signals 的真实条目>"],
      "interaction_stats_refs": { "<key>": <value> },  // 可选：引用 interaction_stats 中的字段
      "rationale_excerpt": "用一句话说明为什么这些证据支撑这个 learning_goal"
    }

    - 找不到对应证据时，**必须**留空数组，但 `rationale_excerpt` 不能省略
    - **禁止编造** evidence_signals 中不存在的 ID

16. **targeted_dimensions 白名单**：仅可从 {knowledge_base, code_skill, cognitive_style, focus_level, learning_goals, weakness} 中选择，**禁止**出现"逻辑思维""数学"等未在白名单内的维度。

17. **capability_rationale 一致性**：必须与 `profile.knowledge_base` / `profile.code_skill` / `profile.weakness` 等画像字段一致。例如：profile.knowledge_base=零基础入门，但 capability_rationale 写"因学生已掌握基础"——这种**自相矛盾**会被后端校验标记为"待复核"。
"""


def _build_user_prompt(analytics: dict, goal: Optional[str] = None,
                       difficulty_pref: int = 3, strategy: str = "auto",
                       injected_knowledge: Optional[list[str]] = None) -> tuple[str, bool]:
    """将学情报告构建为 LLM user prompt，突出多维能力数据。
    返回: (prompt, has_assessment_data)
    goal: 用户自定义学习目标，注入 prompt 引导 LLM 生成针对性路径。
    difficulty_pref: 教学难度偏好 1-5
    strategy: 教学策略
    injected_knowledge: 注入知识标签
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
    # 注意：空值场景必须明确归类为"零基础"，避免 LLM 推断"未知=已有基础"而误标 completed。
    kb_raw = profile.get('knowledge_base') or ''
    cs_raw = profile.get('code_skill') or ''
    kb_for_display = kb_raw if kb_raw else '零基础入门'
    cs_for_display = cs_raw if cs_raw else '编程新手'
    has_assessment_data = bool(kb_raw and cs_raw)

    lines.append("### 📊 多维能力总览")
    lines.append("")
    lines.append("【知识基础】" + kb_for_display + ("（用户已评估）" if kb_raw else "（⚠️ 尚未评估，按零基础处理）"))
    lines.append("【代码能力】" + cs_for_display + ("（用户已评估）" if cs_raw else "（⚠️ 尚未评估，按编程新手处理）"))
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

    # ── 可引用证据池：LLM 在 goal_evidence 中只能引用以下 ID ──
    evidence = analytics.get("evidence_signals", {}) or {}
    quiz_ids = evidence.get("quiz_ids", [])
    classroom_ids = evidence.get("classroom_ids", [])
    interaction_stats = evidence.get("interaction_stats", {}) or {}
    profile_signals = evidence.get("profile_signals", [])
    recent_topics_ev = evidence.get("recent_message_topics", [])
    lines.append("### 🧾 可引用证据池（goal_evidence 必须从下列 ID 中引用，禁止编造）")
    lines.append(f"- 真实测验 ID（quiz_ids）: {quiz_ids if quiz_ids else '（暂无）'}")
    lines.append(f"- 真实课堂 ID（classroom_ids）: {classroom_ids if classroom_ids else '（暂无）'}")
    lines.append(f"- 已评估画像字段（profile_signals）: {profile_signals if profile_signals else '（暂无）'}")
    lines.append("- 互动统计快照（interaction_stats）:")
    lines.append(f"  - interaction_count = {interaction_stats.get('interaction_count', 0)}")
    lines.append(f"  - learning_minutes = {interaction_stats.get('learning_minutes', 0)}")
    lines.append(f"  - completed_tasks = {interaction_stats.get('completed_tasks', 0)}")
    lines.append(f"  - concept_mastery = {interaction_stats.get('concept_mastery', 0)}")
    lines.append(f"  - thinking_depth = {interaction_stats.get('thinking_depth', 0)}")
    lines.append(f"  - learning_momentum = {interaction_stats.get('learning_momentum', 0)}")
    lines.append(f"  - weak_areas = {interaction_stats.get('weak_areas', [])}")
    lines.append(f"  - strong_areas = {interaction_stats.get('strong_areas', [])}")
    if recent_topics_ev:
        lines.append(f"- 近期对话主题: {recent_topics_ev}")
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
    # ── ⚠️ 关键防误判规则：避免 LLM 把"无评估=已有基础"导致错标 completed ──
    if not has_assessment_data:
        lines.append("### ⚠️ 起点强制规则（学生尚未完成评估）")
        lines.append("由于该学生尚未完成学情评估，**所有节点必须按以下规则生成，禁止凭空把基础节点标记为 completed**：")
        lines.append("- 任何编程/语法基础类节点（如「Python基础语法」「数据结构」「Linux入门」等）必须标记为 `in_progress`（表示「刚要开始」）或 `locked`，**绝不能标记为 `completed`**；")
        lines.append("- 节点 description 中**禁止**使用「已掌握」「已学完」「已学毕」等表述；")
        lines.append("- 路径中第一个节点的 `learning_goal` 应明确为：从零开始学习 xxx 基础；")
        lines.append("- 节点 `status` 字段以本次新规划为准，**不要继承**上方「当前路径预览」中可能存在的旧状态（旧的 completed 状态不代表真实掌握）。")
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

    # ── Agent 控制塔教学调控注入 ──
    _dl = {1:"极简",2:"简单",3:"适中",4:"困难",5:"极难"}
    _dt = _dl.get(difficulty_pref, "适中")
    _sl = {"auto":"自动","lecture":"讲解","practice":"练习","socratic":"苏格拉底"}
    _st = _sl.get(strategy, "自动")
    _ik = "、".join(injected_knowledge) if injected_knowledge else "暂无"
    lines.append("### Agent 控制塔教学调控")
    lines.append(f"- 难度偏好：{_dt}（{difficulty_pref}/5）")
    lines.append(f"- 教学策略：{_st}")
    lines.append(f"- 注入知识/兴趣标签：{_ik}")
    lines.append("路径节点的话题难度和教学方式应遵循以上设置。")
    lines.append("")
    lines.append("请基于以上全部多维能力数据，生成该学生的个性化学习路径。注意：")
    lines.append("1. 每个路径节点的 learning_goal 必须明确写出该节点要培养的能力")
    lines.append("2. capability_rationale 要解释该节点为何适合该生的当前能力水平")
    lines.append("3. targeted_dimensions 至少要标注该节点针对哪些能力维度")
    lines.append("4. capability_analysis 要综合所有维度给出整体学习策略")

    return "\n".join(lines), has_assessment_data


# ── 核心生成逻辑（可被外部调用） ──

async def generate_path_for_user(user_id: int, force_refresh: bool = False, goal: Optional[str] = None,
                                  difficulty_pref: int = 3, strategy: str = "auto",
                                  injected_knowledge: Optional[list[str]] = None) -> GenerateLearningPathResponse:
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
    user_prompt, has_assessment_data = _build_user_prompt(analytics, goal=goal, difficulty_pref=difficulty_pref,
                                                          strategy=strategy, injected_knowledge=injected_knowledge)
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

    # 4.5 ⚠️ 防御性后处理：未评估用户禁止任何节点为 completed（兜底，防止 LLM 违反规则）
    if not has_assessment_data:
        _downgrade_completed_to_inprogress(path)

    # 4.6 结构化校验：学习目标真实性、证据 ID 真实性、profile 一致性
    try:
        cfg = getattr(settings, "learning_goal_validation", {}) or {}
        if cfg.get("enabled", True):
            validation_result = _validate_and_ground_learning_goals(path, analytics)
            print(f"[LearningPath] goal_evidence 校验: valid={validation_result['valid_count']}, "
                  f"invalid={validation_result['invalid_count']}")
            if validation_result["invalid_count"] > 0:
                print(f"[LearningPath] 校验失败节点: {validation_result['invalid_node_ids'][:5]}")
    except Exception as e:
        print(f"[LearningPath] _validate_and_ground_learning_goals 异常（不阻断生成）: {e}")

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
    return await generate_path_for_user(request.userId, force_refresh=request.forceRefresh, goal=request.goal,
                                        difficulty_pref=request.difficulty_pref, strategy=request.strategy,
                                        injected_knowledge=request.injected_knowledge)


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
    # ⚠️ 防御性后处理：未评估用户不应有 completed 节点（即使 LLM 历史生成过错误数据）
    try:
        profile_raw = database.get_user_profile(user_id)
        profile_json_raw = profile_raw.get("profile_json") if profile_raw else {}
        if isinstance(profile_json_raw, str):
            import json
            try:
                profile_json_raw = json.loads(profile_json_raw)
            except Exception:
                profile_json_raw = {}
        kb_val = (profile_json_raw or {}).get("knowledgeBase", "")
        cs_val = (profile_json_raw or {}).get("codeSkill", "")
        if not (kb_val and cs_val):
            _downgrade_completed_to_inprogress(path)
    except Exception:
        pass
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
