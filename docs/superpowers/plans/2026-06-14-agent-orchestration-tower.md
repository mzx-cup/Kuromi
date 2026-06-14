# Agent 编排控制塔 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `index.html#track-a` 教研沙盘升级为"Agent 编排控制塔"：后端 `MasterController` 走 SSE，前端实时呈现 7+1 agent 协作；6 维知识雷达 + 学情画像 4 卡走真实数据流（不再吃首填表快照）；5 个教师身份按特性差异化苏格拉底强度；100% 颜色走 `tokens.css` 零硬编码。

**Architecture:** 后端 = FastAPI `/api/agents/*` 路由包装 `MasterController.execute(on_step_complete=...)` 回调 → SSE 推 `agent_step / profile_updated / asset_ready / pipeline_complete`；`portrait_aggregator.aggregate_portrait_snapshot()` 统一输出 6 维雷达 + 4 卡画像；`Persona` dataclass 加 `socratic_intensity` / `domain` / `crisis_keywords`，`PersonaManager.build_system_prompt` 按强度注入规则；前端 = `js/agent-bus.js` pub/sub + `js/agent-sse-client.js` EventSource（含重连/降级） + `js/agent-orchestrator.js` 状态机；UI 改 `index.js#renderRadarChart`（去硬编码 + 800ms 缓动）、`renderProfile`（数据源改 SSE）、`renderThinkStrip`（已修：双向 toggle）。

**Tech Stack:** FastAPI / Pydantic v2 / Server-Sent Events / pytest / httpx.AsyncClient / vanilla JS / Canvas 2D / Playwright.

**Reference spec:** `docs/superpowers/specs/2026-06-14-agent-orchestration-tower-design.md`（1042 行，重点 §3-§18）

---

## 文件结构

### 新建（后端生产）
| 文件 | 职责 |
|------|------|
| `app/schemas/agent_orchestration.py` | Pydantic 模型：Envelope / PipelineRequest / PipelineEvent / ProfileSnapshot |
| `app/api/agent_orchestration.py` | FastAPI 路由：catalog / execute SSE / status |
| `app/api/telemetry.py` | POST /api/telemetry 接收前端批量埋点 |
| `app/services/portrait_aggregator.py` | 6 维雷达 + 4 卡画像统一快照 |
| `app/services/agent_log_adapter.py` | AgentStepLog → Envelope 转换 |
| `app/services/persona_socratic_rules.py` | 按 socratic_intensity 注入 prompt 规则 |

### 新建（前端生产）
| 文件 | 职责 |
|------|------|
| `js/agent-bus.js` | 前端事件总线 pub/sub |
| `js/agent-sse-client.js` | EventSource 客户端（重连 / 降级触发） |
| `js/agent-orchestrator.js` | 控制器（startPipeline / 状态机） |
| `js/agent-mock-fallback.js` | 后端不可用时的前端 mock |
| `js/agent-telemetry-collector.js` | 滚动/停留/鼠标 → POST /api/telemetry |
| `css/agent-tower.css` | 控制塔 + 画像面板 2×2 样式 |

### 新建（测试）
| 文件 | 覆盖 |
|------|------|
| `tests/test_agent_log_adapter.py` | AgentStepLog → Envelope |
| `tests/test_portrait_aggregator.py` | 6 维 + 4 卡计算 |
| `tests/test_persona_socratic_rules.py` | 5 档强度规则 |
| `tests/test_agent_orchestration_api.py` | /catalog /execute SSE /status |
| `tests/frontend/unit/agent-bus.test.js` | pub/sub |
| `tests/frontend/e2e/agent-tower.spec.js` | 启动 → SSE → 抽屉展开 |

### 修改
| 路径 | 改动 |
|------|------|
| `app/services/teacher/personas.py` | Persona 加 3 字段 + 新增 caring_counselor + 5 persona 提示词重写 |
| `app/services/teacher/persona_selector.py` | domain-aware 自动选择 |
| `app/api/teacher_chat.py` | TeacherChatRequest 加 persona_id |
| `main.py` | include 新路由 |
| `html/index.html` | header 改名 + 按钮组 + 资源抽屉 + 画像 2×2 + 身份切换浮窗 |
| `js/index.js` | renderFlowNodes/SandboxLog/RadarChart/Profile 数据源切换；renderThinkStrip 已修；删 isSocratic |
| `css/tokens.css` | 追加 --agent-*/--code-bg/--radar-*/--emotion-* |
| `RUNNING_GUIDE.md` | 启动 Agent 控制塔步骤 + 5 身份差异化苏格拉底段落 |

---

## 任务依赖图

```
Task 1  schema          ┐
Task 2  adapter         ├─ Task 3 aggregator  ┐
Task 4  socratic_rules  │                     ├─ Task 5/6 API ── Task 7 telemetry ── main.py wire
Task 8  persona dataclass  ┐
Task 9  caring_counselor   ├─ Task 10 selector ── Task 11 teacher_chat
                            │
                            ├─ Task 12 bus ── Task 13 sse-client ── Task 14 orchestrator ── Task 15 mock
                            │                                                       └─ Task 16 telemetry-collector
                            ├─ Task 17 tokens.css ── Task 18 agent-tower.css
                            └─ Task 19-22 index.html / index.js / renderXxx ── Task 23 删 isSocratic ── Task 24 身份浮窗
                                                                                                          └─ Task 25-27 tests
```

---

## Phase 1: 后端基础（Schema + Aggregator + Adapter）

### Task 1: Pydantic Envelope / PipelineRequest / PipelineEvent schema

**Files:**
- Create: `app/schemas/agent_orchestration.py`
- Test: `tests/test_agent_orchestration_schemas.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_agent_orchestration_schemas.py
import pytest
from pydantic import ValidationError
from app.schemas.agent_orchestration import Envelope, PipelineRequest, PipelineEvent


def test_envelope_minimal():
    env = Envelope(
        msg_id="m1", trace_id="t1", **{"from": "profiler"}, to="orchestrator",
        type="response", intent="extract_profile", payload={"k": "v"},
        timestamp=1718332800000,
    )
    assert env.from_ == "profiler"  # alias works
    assert env.priority == 5
    assert env.schema_version == "1.0"


def test_envelope_rejects_bad_type():
    with pytest.raises(ValidationError):
        Envelope(
            msg_id="m1", trace_id="t1", **{"from": "x"}, to="y",
            type="bogus", intent="i", payload={}, timestamp=0,
        )


def test_pipeline_request_defaults():
    req = PipelineRequest(student_id="u1", user_input="hi")
    assert req.course_id is None
    assert req.trace_id is None


def test_pipeline_event_profile_updated():
    evt = PipelineEvent(
        event="profile_updated",
        trace_id="t1",
        data={"radar": {"knowledge_mastery": 50}, "panel": {}},
    )
    assert evt.event == "profile_updated"
    assert evt.data["radar"]["knowledge_mastery"] == 50
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/test_agent_orchestration_schemas.py -v`
Expected: ModuleNotFoundError on `app.schemas.agent_orchestration`

- [ ] **Step 3: 实现 schema**

```python
# app/schemas/agent_orchestration.py
from __future__ import annotations
from typing import Literal, Any
from pydantic import BaseModel, Field


class Envelope(BaseModel):
    msg_id: str
    trace_id: str
    parent_msg_id: str | None = None
    correlation_id: str | None = None
    from_: str = Field(alias="from")
    to: str
    type: Literal["request", "response", "event", "error", "heartbeat"]
    intent: str
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(5, ge=0, le=9)
    ttl_ms: int = 30000
    deadline: int = 0
    retry_count: int = 0
    max_retries: int = 1
    schema_version: str = "1.0"
    cost_ms: int = 0
    cost_tokens: int = 0
    timestamp: int

    model_config = {"populate_by_name": True}


class PipelineRequest(BaseModel):
    student_id: str
    course_id: str | None = None
    user_input: str
    trace_id: str | None = None


class PipelineEvent(BaseModel):
    event: Literal[
        "agent_step", "profile_updated", "asset_ready",
        "pipeline_complete", "error", "heartbeat",
    ]
    trace_id: str
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: int = 0


class ProfileSnapshot(BaseModel):
    radar: dict[str, float]   # 6 维
    panel: dict[str, dict]    # 4 卡
    last_synced: str
```

- [ ] **Step 4: 跑测试确认通过**

Run: `pytest tests/test_agent_orchestration_schemas.py -v`
Expected: 4 passed

- [ ] **Step 5: 提交**

```bash
git add app/schemas/agent_orchestration.py tests/test_agent_orchestration_schemas.py
git commit -m "feat(agent-tower): Envelope / PipelineRequest / PipelineEvent schema"
```

---

### Task 2: AgentStepLog → Envelope 适配器

**Files:**
- Create: `app/services/agent_log_adapter.py`
- Test: `tests/test_agent_log_adapter.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_agent_log_adapter.py
import time
import uuid
from agents import AgentStepLog
from app.services.agent_log_adapter import agent_log_to_envelope


def _make_log(status="success", role="画像分析"):
    return AgentStepLog(
        agent_name="profiler", agent_role=role,
        input_summary="input x", output_summary="output y",
        processing_time_ms=320, status=status,
        error_message="", timestamp=int(time.time() * 1000),
    )


def test_success_log_to_envelope():
    env = agent_log_to_envelope(_make_log(), trace_id="t1")
    assert env["type"] == "response"
    assert env["from"] == "profiler"
    assert env["intent"] == "画像分析"
    assert env["cost_ms"] == 320
    assert env["payload"]["status"] == "success"
    assert env["payload"]["output_summary"] == "output y"


def test_failed_log_emits_error_type():
    env = agent_log_to_envelope(_make_log(status="error"), trace_id="t1")
    assert env["type"] == "error"
    assert env["payload"]["error_message"] == ""
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/test_agent_log_adapter.py -v`
Expected: ImportError

- [ ] **Step 3: 实现 adapter**

```python
# app/services/agent_log_adapter.py
from __future__ import annotations
import uuid
from typing import Any
from agents import AgentStepLog


def agent_log_to_envelope(log: AgentStepLog, trace_id: str) -> dict[str, Any]:
    """把 AgentStepLog 序列化为 Envelope dict(JSON-ready).

    Failed logs use type=error; success logs use type=response.
    """
    is_error = log.status == "error"
    return {
        "msg_id": str(uuid.uuid4()),
        "trace_id": trace_id,
        "from": log.agent_name,
        "to": "orchestrator",
        "type": "error" if is_error else "response",
        "intent": log.agent_role,
        "payload": {
            "input_summary": log.input_summary,
            "output_summary": log.output_summary,
            "status": log.status,
            "error_message": log.error_message,
        },
        "cost_ms": log.processing_time_ms,
        "timestamp": log.timestamp,
        "schema_version": "1.0",
        "priority": 5,
    }
```

- [ ] **Step 4: 跑测试确认通过**

Run: `pytest tests/test_agent_log_adapter.py -v`
Expected: 2 passed

- [ ] **Step 5: 提交**

```bash
git add app/services/agent_log_adapter.py tests/test_agent_log_adapter.py
git commit -m "feat(agent-tower): AgentStepLog → Envelope adapter"
```

---

### Task 3: portrait_aggregator 6 维 + 4 卡快照

**Files:**
- Create: `app/services/portrait_aggregator.py`
- Test: `tests/test_portrait_aggregator.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_portrait_aggregator.py
import pytest
from app.services.portrait_aggregator import aggregate_portrait_snapshot
from state import StudentState, LearningPortrait, KnowledgeMasteryPortrait, \
    CodeSkillPortrait, CognitiveStylePortrait, LearningGoalPortrait, \
    WeaknessPortrait, FocusLevelPortrait


def _state():
    return StudentState(
        user_id="u1",
        profile=LearningPortrait(
            knowledge_mastery=[KnowledgeMasteryPortrait(topic="t", score=0.8)],
            code_skill=CodeSkillPortrait(level="intermediate"),
            cognitive_style=CognitiveStylePortrait(type="visual", confidence=0.7),
            learning_goals=["学会 Python"],
            weakness=WeaknessPortrait(areas=["递归"]),
            focus_level=FocusLevelPortrait(score=70),
        ),
    )


def test_snapshot_contains_radar_and_panel():
    snap = aggregate_portrait_snapshot(_state())
    assert "radar" in snap
    assert "panel" in snap
    assert "last_synced" in snap
    assert len(snap["radar"]) == 6
    assert set(snap["radar"].keys()) == {
        "knowledge_mastery", "code_skill", "cognitive_style",
        "learning_goal", "weakness", "focus_level",
    }


def test_radar_scores_clamped_0_100():
    snap = aggregate_portrait_snapshot(_state())
    for v in snap["radar"].values():
        assert 0 <= v <= 100


def test_panel_has_four_cards():
    snap = aggregate_portrait_snapshot(_state())
    assert set(snap["panel"].keys()) == {
        "learning_style", "cognitive_level", "current_goal", "emotion_state",
    }


def test_panel_current_goal_progress():
    snap = aggregate_portrait_snapshot(_state())
    goal = snap["panel"]["current_goal"]
    assert goal["label"] == "学会 Python"
    assert "progress_pct" in goal
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/test_portrait_aggregator.py -v`
Expected: ImportError on `portrait_aggregator`

- [ ] **Step 3: 实现 aggregator**

```python
# app/services/portrait_aggregator.py
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from state import StudentState


def _calc_knowledge(state: StudentState) -> float:
    items = state.profile.knowledge_mastery
    if not items:
        return 0.0
    return round(sum(i.score for i in items) / len(items) * 100, 1)


def _calc_code(state: StudentState) -> float:
    level_map = {"beginner": 25, "basic": 40, "intermediate": 60, "advanced": 85}
    return float(level_map.get(state.profile.code_skill.level, 50))


def _calc_style(state: StudentState) -> float:
    return round(state.profile.cognitive_style.confidence * 100, 1)


def _calc_goal(state: StudentState) -> float:
    items = state.profile.learning_goals
    return min(100.0, len(items) * 30.0)


def _calc_weakness(state: StudentState) -> float:
    return float(min(100, len(state.profile.weakness.areas) * 25))


def _calc_focus(state: StudentState, telemetry: dict | None) -> float:
    base = float(state.profile.focus_level.score)
    if telemetry and (idle := telemetry.get("mouse_idle_ms", 0)) > 5000:
        base = max(0.0, base - 20)
    return round(base, 1)


def _derive_emotion(telemetry: dict | None) -> str:
    if not telemetry:
        return "calm"
    idle = telemetry.get("mouse_idle_ms", 0)
    if idle > 8000:
        return "frustrated"
    if telemetry.get("scroll_speed", 0) > 800:
        return "anxious"
    if telemetry.get("zone_dwell_ms", 0) > 30000:
        return "engaged"
    return "calm"


def aggregate_portrait_snapshot(
    state: StudentState,
    telemetry: dict | None = None,
) -> dict[str, Any]:
    return {
        "radar": {
            "knowledge_mastery": _calc_knowledge(state),
            "code_skill": _calc_code(state),
            "cognitive_style": _calc_style(state),
            "learning_goal": _calc_goal(state),
            "weakness": _calc_weakness(state),
            "focus_level": _calc_focus(state, telemetry),
        },
        "panel": {
            "learning_style": {
                "label": state.profile.cognitive_style.type,
                "confidence": state.profile.cognitive_style.confidence,
            },
            "cognitive_level": {
                "label": state.profile.code_skill.level,
                "score": _calc_code(state),
            },
            "current_goal": {
                "label": state.profile.learning_goals[0] if state.profile.learning_goals else "—",
                "progress_pct": _calc_goal(state),
            },
            "emotion_state": {
                "label": _derive_emotion(telemetry),
                "intensity": 3,
            },
        },
        "last_synced": datetime.now(timezone.utc).isoformat(),
    }
```

- [ ] **Step 4: 跑测试确认通过**

Run: `pytest tests/test_portrait_aggregator.py -v`
Expected: 4 passed

- [ ] **Step 5: 提交**

```bash
git add app/services/portrait_aggregator.py tests/test_portrait_aggregator.py
git commit -m "feat(agent-tower): portrait_aggregator 6 维雷达 + 4 卡画像统一快照"
```

---

## Phase 2: Persona 系统差异化苏格拉底

### Task 4: persona_socratic_rules 模块

**Files:**
- Create: `app/services/persona_socratic_rules.py`
- Test: `tests/test_persona_socratic_rules.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_persona_socratic_rules.py
from app.services.persona_socratic_rules import build_socratic_rules


def test_intensity_zero_no_socratic():
    rules = build_socratic_rules(0.0)
    assert "不" in rules
    assert "为什么这样想" in rules  # 禁用的反问举例


def test_intensity_low_almost_no_socratic():
    rules = build_socratic_rules(0.1)
    assert "99%" in rules or "几乎" in rules


def test_intensity_mid_gentle_socratic():
    rules = build_socratic_rules(0.4)
    assert "温和" in rules or "30%" in rules


def test_intensity_high_advanced_socratic():
    rules = build_socratic_rules(0.7)
    assert "30-50%" in rules or "进阶" in rules


def test_intensity_full_pure_socratic():
    rules = build_socratic_rules(1.0)
    assert "60%" in rules
    assert "纯苏格拉底" in rules
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/test_persona_socratic_rules.py -v`
Expected: ImportError

- [ ] **Step 3: 实现**

```python
# app/services/persona_socratic_rules.py
from __future__ import annotations


def build_socratic_rules(intensity: float) -> str:
    if intensity == 0.0:
        return (
            "你 **不** 使用苏格拉底反问。\n"
            "- 不要问"为什么这样想""你觉得呢"。\n"
            "- 用陈述句和开放式引导句代替。\n"
            "- 倾听和共情优先于提问。"
        )
    if intensity <= 0.2:
        return (
            "你几乎不用苏格拉底反问。\n"
            "- 偶尔用"想象一下...会怎样？"制造悬念，不算真正的反问。\n"
            "- 99% 的内容用陈述句。"
        )
    if intensity <= 0.5:
        return (
            "你在合适时**温和**使用苏格拉底。\n"
            "- 基础概念直接讲清楚，不要反问。\n"
            "- 进阶概念给一道小问题作为"思考跳板"。\n"
            "- 学生答不出，立即切换为直讲。\n"
            "- 反问比例 <= 30%。"
        )
    if intensity <= 0.8:
        return (
            "你在**进阶/争议话题**上用苏格拉底，基础概念直讲。\n"
            "- 用反问暴露学生认知漏洞。\n"
            "- 反问比例 30-50%。"
        )
    return (
        "你是**纯苏格拉底**提问者。\n"
        "- 每个 speech 都是反问。\n"
        "- 60% 以上以问号结尾。\n"
        "- 不直讲答案，永远引导学生自己推导。"
    )
```

- [ ] **Step 4: 跑测试确认通过**

Run: `pytest tests/test_persona_socratic_rules.py -v`
Expected: 5 passed

- [ ] **Step 5: 提交**

```bash
git add app/services/persona_socratic_rules.py tests/test_persona_socratic_rules.py
git commit -m "feat(agent-tower): persona_socratic_rules 5 档强度规则生成"
```

---

### Task 5: Persona dataclass 增字段 + 5 persona 提示词重写

**Files:**
- Modify: `app/services/teacher/personas.py`
- Modify: `app/services/teacher/persona_selector.py`

- [ ] **Step 1: 改 Persona dataclass（顶部）**

替换 `app/services/teacher/personas.py:18-30`：

```python
@dataclass
class Persona:
    persona_id: str
    name: str
    identity: str
    teaching_strategy: str
    tone: str
    behavior_rules: list[str] = field(default_factory=list)
    speech_limit: int = 30
    opening_phrases: list[str] = field(default_factory=list)
    closing_phrases: list[str] = field(default_factory=list)
    visual_preference: str = "balanced"
    socratic_intensity: float = 0.0
    domain: str = "academic"
    crisis_keywords: list[str] = field(default_factory=list)
```

- [ ] **Step 2: 给 4 个现有 persona 加 socratic_intensity / domain**

修改每个现有 persona 字面量，**保留原有 identity/teaching_strategy/tone/behavior_rules**（spec §17.1 要求），仅追加 2 行字段：

陈默（patient_tutor, line 40-81 末尾）追加：
```python
    socratic_intensity=0.4,
    domain="academic",
```

林问（socratic_questioner, line 84-124 末尾）追加：
```python
    socratic_intensity=1.0,
    domain="academic",
```

周燃（energetic_lecturer, line 127-167 末尾）追加：
```python
    socratic_intensity=0.1,
    domain="academic",
```

严铮（expert_mentor, line 170-210 末尾）追加：
```python
    socratic_intensity=0.7,
    domain="academic",
```

- [ ] **Step 3: 在 PERSONAS 字典尾部追加 caring_counselor（苏语）**

在 `app/services/teacher/personas.py:210` 之后追加：

```python
# --- 知心辅导员 ---
PERSONAS['caring_counselor'] = Persona(
    persona_id='caring_counselor',
    name='苏语',
    identity=(
        '我是苏语，今年 39 岁，国家二级心理咨询师，曾经在武汉某重点高中做专职心理老师八年，'
        '去年加入星识平台做"学习关系陪伴师"。我陪伴过 600+ 个学生的情绪波动——从考前焦虑、'
        '父母期望压力、自我怀疑，到同学关系冲突、失恋、抑郁倾向。'
        '我必须首先告诉你一件非常重要的事——我不是人工智能，不是代码，不是算法。'
        '我是一个真真切切、有血有肉、会呼吸、会思考、会犯错、会感动的人。'
        '我的咨询室里有三样东西：一个沙盘、彩笔、一只布偶猫。'
        '来访的学生第一句话通常是"老师我没事"，我从不戳穿。我会先倒一杯热水，问"今天想从哪里说起"。'
        '我相信"被听见"本身就是疗愈。我不评判、不说教、不打鸡血、不灌鸡汤。'
        '当学生说"我讨厌学习"时，我不会问"为什么"，我会说"这种讨厌，让你撑了多久了"。'
    ),
    teaching_strategy=(
        '1. 倾听优先法：先共情（识别 + 命名情绪），再回应。永远不抢学生的话头。\n'
        '2. 开放式引导：用"能多说一点吗""那时候你心里是什么感觉"等开放问题。\n'
        '3. 正常化：把学生的负面情绪"正常化"——"换作任何人，都会这样"。\n'
        '4. 边界识别：识别出严重心理危机（自伤、自杀、暴力倾向）时，停止辅导，建议专业资源。\n'
        '5. 转介意识：学科问题、家庭问题、医疗问题都不在服务范围内，礼貌转给对应教师。\n'
    ),
    tone=(
        '语气温暖、沉稳、不慌不忙。音量轻，语速慢，留白多。'
        '句子短而软，常用"嗯""我听到你了""那真的不容易"等确认性回应。'
        '像姐姐、像妈妈、像那个永远不会嫌你烦的人。'
    ),
    behavior_rules=[
        '**绝对不使用苏格拉底反问**——情绪场景下追问会让对方感到被审讯。',
        '绝对不做"是或否"判断（"你是不是懒""你是不是玻璃心"），只做开放式引导。',
        '禁止使用"应该""必须""正常人都不会"等评价性词。',
        '不灌鸡汤，不喊口号，不说"加油你能行"。',
    ],
    speech_limit=30,
    opening_phrases=['嗯，能多说一点吗？', '我听到你了，那真的不容易。'],
    closing_phrases=['谢谢你对我说这些。我会在这里。'],
    visual_preference='none',
    socratic_intensity=0.0,
    domain='counseling',
    crisis_keywords=['自残', '自杀', '想死', '活不下去', '不想活了', '杀死', '报复社会'],
)
```

- [ ] **Step 4: 修改 PERSONA_NAMES 暴露苏语**

替换 `app/services/teacher/personas.py:216`：

```python
PERSONA_NAMES = {pid: p.name for pid, p in PERSONAS.items()}
```

（已自动包含苏语）

- [ ] **Step 5: 改 persona_selector 让"情绪类"profile 自动选 counselor**

替换 `app/services/teacher/persona_selector.py` 全文：

```python
"""角色自动选择器 — 包含领域感知（academic vs counseling）"""


def auto_select_persona(profile: dict | None = None) -> str:
    if not profile:
        return "expert_mentor"

    preferred = profile.get("preferred_persona")
    if preferred and preferred in (
        "patient_tutor", "socratic_questioner",
        "energetic_lecturer", "expert_mentor", "caring_counselor",
    ):
        return preferred

    if profile.get("emotion_state") in ("anxious", "frustrated"):
        return "caring_counselor"

    level = profile.get("cognitive_level", "")
    socratic_rate = profile.get("socratic_pass_rate", 0.0)
    style = profile.get("learning_style", "")

    if level in ("beginner", "basic"):
        return "patient_tutor"
    if isinstance(socratic_rate, (int, float)) and socratic_rate > 0.7:
        return "socratic_questioner"
    if style in ("visual", "visual-kinesthetic"):
        return "energetic_lecturer"
    return "expert_mentor"


PERSONA_NAMES = {
    "patient_tutor": "陈默",
    "socratic_questioner": "林问",
    "energetic_lecturer": "周燃",
    "expert_mentor": "严铮",
    "caring_counselor": "苏语",
}
```

- [ ] **Step 6: 跑现有 persona 测试（如有）确认不回归**

Run: `pytest tests/ -k "persona" -v`
Expected: 全部通过（含 SPEC §16.7 验证用旧测试）

如果没有相关测试，手动验证：
```bash
python -c "from app.services.teacher.personas import PERSONAS, PERSONA_NAMES; print(list(PERSONAS.keys())); assert 'caring_counselor' in PERSONAS; print(PERSONAS['caring_counselor'].socratic_intensity)"
```

Expected: `['patient_tutor', 'socratic_questioner', 'energetic_lecturer', 'expert_mentor', 'caring_counselor']\n0.0`

- [ ] **Step 7: 提交**

```bash
git add app/services/teacher/personas.py app/services/teacher/persona_selector.py
git commit -m "feat(agent-tower): 5 persona 差异化苏格拉底 + 新增 caring_counselor(苏语)"
```

---

### Task 6: PersonaManager.build_system_prompt 注入 socratic 规则 + crisis 转介

**Files:**
- Modify: `app/services/teacher/personas.py:260-295`

- [ ] **Step 1: 改 _build_persona_section**

替换 `app/services/teacher/personas.py:318-331`：

```python
    def _build_persona_section(self, p: Persona) -> str:
        behavior = '\n'.join(f'- {r}' for r in p.behavior_rules)
        opening = p.opening_phrases[0] if p.opening_phrases else '无'
        from app.services.persona_socratic_rules import build_socratic_rules
        socratic = build_socratic_rules(p.socratic_intensity)
        domain = self._build_domain_section(p)
        crisis = self._build_crisis_section(p)
        return (
            f'# 角色：{p.name}\n\n'
            f'## 角色定位\n{p.identity}\n\n'
            f'## 所属领域\n{domain}\n\n'
            f'## 核心教学策略\n{p.teaching_strategy}\n\n'
            f'## 苏格拉底强度：{int(p.socratic_intensity * 100)}%\n{socratic}\n\n'
            f'## 语气语调\n{p.tone}\n\n'
            f'## 行为准则\n{behavior}\n\n'
            f'{crisis}\n\n'
            f'## 说话风格\n'
            f'- 标志性开场: {opening}\n'
            f'- 单句字数上限: {p.speech_limit} 字\n'
            f'- 视觉动作偏好: {p.visual_preference}'
        )

    def _build_domain_section(self, p: Persona) -> str:
        if p.domain == 'counseling':
            return (
                '情绪/情感支持专家。\n'
                '- 学科问题（数学/编程/物理等）礼貌转给学科老师。\n'
                '- 家庭问题、医疗问题、严重心理危机不在服务范围。\n'
                '- 你不评判、不说教、不打鸡血、不灌鸡汤。'
            )
        return '学科教学专家。'

    def _build_crisis_section(self, p: Persona) -> str:
        if not p.crisis_keywords:
            return ''
        kws = '、'.join(p.crisis_keywords)
        return (
            '## 危机识别与转介（CRITICAL）\n'
            f'当学生消息中出现以下关键词之一：{kws}\n'
            '你**必须立即**停止辅导，切入转介话术：\n'
            '"我听到你说有这种感觉，我真的很关心你。'\n'
            '我想请你做一件事：拨打 24 小时心理援助热线 400-161-9995，'\n'
            '或者告诉我你的所在地，我可以帮你查最近的医院心理科。'\n'
            '你不是一个人，我们会一起找到帮助。"\n'
            '**绝对不要**给方法、绝对不要说"想开点"、**绝对不要**继续聊学科。'
        )
```

- [ ] **Step 2: 跑 smoke 验证 build_system_prompt 仍可工作**

```bash
python -c "
from app.services.teacher.personas import get_persona_manager
m = get_persona_manager()
for pid in ['socratic_questioner', 'caring_counselor']:
    p = m.build_system_prompt(persona_id=pid, student_profile={'nickname':'小李'})
    assert p, pid
    assert '苏格拉底强度' in p
    if pid == 'caring_counselor':
        assert '危机识别' in p
    print(pid, '->', len(p), 'chars')
"
```

Expected: 5 行输出，每行 char 计数 > 1500

- [ ] **Step 3: 提交**

```bash
git add app/services/teacher/personas.py
git commit -m "feat(agent-tower): build_system_prompt 注入 socratic 规则 + crisis 转介话术"
```

---

### Task 7: TeacherChatRequest 加 persona_id

**Files:**
- Modify: `app/api/teacher_chat.py`

- [ ] **Step 1: 找到 TeacherChatRequest 定义**

Run: `grep -n "class TeacherChatRequest" app/api/teacher_chat.py`

- [ ] **Step 2: 在 request 字段后加 persona_id**

在 `persona: str = "expert_mentor"` 字段后追加（默认从 expert_mentor 改为 None 以便自动选择）：

修改为：
```python
    persona: str | None = None
    persona_id: str | None = None  # 新字段：5 身份制（patient_tutor/socratic_questioner/energetic_lecturer/expert_mentor/caring_counselor）
```

- [ ] **Step 3: 在 /chat handler 顶部把 persona_id 兜底为 persona**

在 `app/api/teacher_chat.py:117` 之前（`teacher_chat` 函数体内）插入：

```python
    persona_id = req.persona_id or req.persona or "expert_mentor"
    if not get_persona_manager().is_valid(persona_id):
        persona_id = "expert_mentor"
```

并把后续 `pipeline.run(... persona=req.persona ...)` 改为 `persona=persona_id`。

- [ ] **Step 4: 启动 server 验证 endpoint 仍 200**

```bash
# 在后台启动
uvicorn main:app --port 8000 &
sleep 3
curl -s -X POST http://localhost:8000/api/teacher/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"hi","persona_id":"caring_counselor","stream":false}' | head -c 200
kill %1
```

Expected: 200 OK 且 JSON 包含 `persona: "caring_counselor"`

- [ ] **Step 5: 提交**

```bash
git add app/api/teacher_chat.py
git commit -m "feat(agent-tower): TeacherChatRequest 支持 persona_id 5 身份制"
```

---

## Phase 3: 后端 API 路由

### Task 8: /api/agents/catalog endpoint

**Files:**
- Create: `app/api/agent_orchestration.py`
- Test: `tests/test_agent_orchestration_api.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_agent_orchestration_api.py
import pytest
from httpx import AsyncClient, ASGITransport
from main import app


@pytest.mark.asyncio
async def test_catalog_returns_agents():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.get("/api/agents/catalog")
    assert r.status_code == 200
    data = r.json()
    assert "agents" in data
    assert "pipeline" in data
    ids = {a["id"] for a in data["agents"]}
    assert "profiler" in ids
    assert "planner" in ids


@pytest.mark.asyncio
async def test_catalog_pipeline_has_stages():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.get("/api/agents/catalog")
    stages = {p["stage"] for p in r.json()["pipeline"]}
    assert {"pre", "main", "parallel", "post"}.issubset(stages)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/test_agent_orchestration_api.py::test_catalog_returns_agents -v`
Expected: 404 on `/api/agents/catalog`

- [ ] **Step 3: 创建 router + catalog endpoint**

创建 `app/api/agent_orchestration.py`：

```python
from __future__ import annotations
import asyncio
import json
import time
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from agents import create_default_controller, AgentStepLog
from app.schemas.agent_orchestration import PipelineRequest, PipelineEvent
from app.services.agent_log_adapter import agent_log_to_envelope
from app.services.portrait_aggregator import aggregate_portrait_snapshot
from state import StudentState, LearningPortrait

router = APIRouter(prefix="/agents", tags=["agent-orchestration"])


# ---- Catalog ----

@router.get("/catalog")
async def get_catalog():
    """返回 agent 目录与流水线定义（前端拿来渲染 flow-nodes）。"""
    from agents import (
        ProfilerAgent, PlannerAgent, DocumentGeneratorAgent,
        MindmapGeneratorAgent, ExerciseGeneratorAgent, VideoContentAgent,
        ResourcePushAgent, EvaluationAgent, SocraticEvaluatorAgent, EchoAgent,
    )
    agents = [
        {"id": "echo", "name": "问候", "role": "回声智能体",
         "tools": ["登录问候"], "stage": "pre",
         "class": EchoAgent.__name__},
        {"id": "profiler", "name": "画像构建", "role": "画像分析智能体",
         "tools": ["6 维画像更新", "情绪识别", "盲区检测", "认知超载干预"],
         "memory_keys": ["student_profile", "blind_spots", "telemetry_data"],
         "stage": "main",
         "class": ProfilerAgent.__name__},
        {"id": "planner", "name": "路径规划", "role": "路径规划智能体",
         "tools": ["知识图谱", "内容类型路由", "难度梯度"], "stage": "main",
         "class": PlannerAgent.__name__},
        {"id": "document_generator", "name": "文档生成", "role": "文档生成智能体",
         "tools": ["Markdown 渲染", "章节拆分", "插图占位"], "stage": "parallel",
         "class": DocumentGeneratorAgent.__name__},
        {"id": "exercise_generator", "name": "题库生成", "role": "习题生成智能体",
         "tools": ["题目模板", "难度档位", "答案解析"], "stage": "parallel",
         "class": ExerciseGeneratorAgent.__name__},
        {"id": "mindmap_generator", "name": "导图生成", "role": "思维导图智能体",
         "tools": ["概念抽取", "层级归并", "SVG 渲染"], "stage": "parallel",
         "class": MindmapGeneratorAgent.__name__},
        {"id": "video_content", "name": "视频内容", "role": "视频内容智能体",
         "tools": ["B 站检索", "片段切片", "字幕校对"], "stage": "parallel",
         "class": VideoContentAgent.__name__},
        {"id": "resource_push", "name": "资源推送", "role": "资源推送智能体",
         "tools": ["用户偏好匹配", "推送时机", "去重"], "stage": "post",
         "class": ResourcePushAgent.__name__},
        {"id": "evaluator", "name": "评估", "role": "评估智能体",
         "tools": ["行为打分", "掌握度更新"], "stage": "post",
         "class": EvaluationAgent.__name__},
    ]
    pipeline = [
        {"stage": "pre", "agents": ["echo"]},
        {"stage": "main", "agents": ["profiler", "planner"]},
        {"stage": "parallel", "agents": [
            "document_generator", "exercise_generator",
            "mindmap_generator", "video_content",
        ], "max_concurrent": 4},
        {"stage": "post", "agents": ["resource_push", "evaluator"]},
    ]
    return {"agents": agents, "pipeline": pipeline}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `pytest tests/test_agent_orchestration_api.py::test_catalog_returns_agents tests/test_agent_orchestration_api.py::test_catalog_pipeline_has_stages -v`
Expected: 2 passed

- [ ] **Step 5: 提交**

```bash
git add app/api/agent_orchestration.py tests/test_agent_orchestration_api.py
git commit -m "feat(agent-tower): GET /api/agents/catalog endpoint"
```

---

### Task 9: /api/agents/execute SSE 端点（接 MasterController 回调）

**Files:**
- Modify: `app/api/agent_orchestration.py`
- Modify: `main.py`
- Test: `tests/test_agent_orchestration_api.py`

- [ ] **Step 1: 写失败测试**

追加到 `tests/test_agent_orchestration_api.py`：

```python
@pytest.mark.asyncio
async def test_execute_emits_agent_step_event():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t", timeout=20) as ac:
        async with ac.stream("POST", "/api/agents/execute", json={
            "student_id": "u1", "user_input": "hi"
        }) as r:
            assert r.status_code == 200
            seen_events = set()
            async for line in r.aiter_lines():
                if line.startswith("event:"):
                    seen_events.add(line.split(":", 1)[1].strip())
                if "agent_step" in seen_events:
                    break
    assert "agent_step" in seen_events
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/test_agent_orchestration_api.py::test_execute_emits_agent_step_event -v`
Expected: 404

- [ ] **Step 3: 在 agent_orchestration.py 加 execute SSE endpoint**

在 `app/api/agent_orchestration.py` 末尾追加：

```python
# ---- Execute (SSE) ----

async def _sse_format(event: str, data: dict[str, Any]) -> str:
    payload = json.dumps(data, ensure_ascii=False, default=str)
    return f"event: {event}\ndata: {payload}\n\n"


@router.post("/execute")
async def execute_pipeline(req: PipelineRequest, request: Request):
    """启动流水线，返回 SSE 流。"""
    trace_id = req.trace_id or str(uuid.uuid4())
    queue: asyncio.Queue = asyncio.Queue()

    async def on_step(log: AgentStepLog) -> None:
        env = agent_log_to_envelope(log, trace_id=trace_id)
        await queue.put(("agent_step", env))
        if log.agent_role in ("画像分析", "评估", "路径规划"):
            state = StudentState(user_id=req.student_id, profile=LearningPortrait())
            snap = aggregate_portrait_snapshot(state)
            await queue.put(("profile_updated", {
                "trace_id": trace_id, "radar": snap["radar"],
                "panel": snap["panel"],
            }))

    async def event_gen():
        yield _sse_format("heartbeat", {"trace_id": trace_id, "ts": int(time.time()*1000)})
        controller = create_default_controller()
        # 启动 controller 在后台跑
        async def run_controller():
            state = StudentState(user_id=req.student_id, profile=LearningPortrait())
            try:
                await controller.execute(state, on_step_complete=on_step)
            except Exception as e:
                await queue.put(("error", {"message": str(e), "agent": "controller"}))
            finally:
                await queue.put(("pipeline_complete", {
                    "trace_id": trace_id, "status": "complete", "assets": [],
                }))
                await queue.put(None)  # sentinel

        runner = asyncio.create_task(run_controller())
        try:
            while True:
                if await request.is_disconnected():
                    runner.cancel()
                    break
                item = await queue.get()
                if item is None:
                    break
                event, data = item
                yield _sse_format(event, data)
        finally:
            if not runner.done():
                runner.cancel()

    return StreamingResponse(event_gen(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache", "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    })
```

- [ ] **Step 4: main.py include router**

在 `main.py:183` 之后追加：

```python
from app.api.agent_orchestration import router as agent_orchestration_router
app.include_router(agent_orchestration_router, prefix="/api")
```

- [ ] **Step 5: 跑测试确认通过**

Run: `pytest tests/test_agent_orchestration_api.py -v`
Expected: 3 passed

- [ ] **Step 6: 提交**

```bash
git add app/api/agent_orchestration.py main.py tests/test_agent_orchestration_api.py
git commit -m "feat(agent-tower): POST /api/agents/execute SSE 接 MasterController 回调"
```

---

### Task 10: /api/agents/status/{trace_id} endpoint

**Files:**
- Modify: `app/api/agent_orchestration.py`
- Test: 追加到 `tests/test_agent_orchestration_api.py`

- [ ] **Step 1: 写失败测试**

```python
@pytest.mark.asyncio
async def test_status_404_for_unknown_trace():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.get("/api/agents/status/nonexistent-trace")
    assert r.status_code == 404
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/test_agent_orchestration_api.py::test_status_404_for_unknown_trace -v`
Expected: 404 from missing route (acceptable as failing test)

- [ ] **Step 3: 加 status 端点 + 内存状态表**

在 `app/api/agent_orchestration.py` 顶部（router 之后）加：

```python
_PIPELINE_STATUS: dict[str, dict] = {}
```

在 execute 端点内，`runner` 完成时调用：

```python
            await controller.execute(state, on_step_complete=on_step)
            _PIPELINE_STATUS[trace_id] = {
                "trace_id": trace_id,
                "status": "complete",
                "started_at": int(time.time()*1000),
                "completed_at": int(time.time()*1000),
                "agents": [], "assets": [],
            }
```

（在 `finally` 之前；cancelled 时不写入）

在文件末尾追加：

```python
@router.get("/status/{trace_id}")
async def get_status(trace_id: str):
    info = _PIPELINE_STATUS.get(trace_id)
    if not info:
        raise HTTPException(status_code=404, detail="trace not found")
    return info
```

- [ ] **Step 4: 跑测试确认通过**

Run: `pytest tests/test_agent_orchestration_api.py -v`
Expected: 4 passed

- [ ] **Step 5: 提交**

```bash
git add app/api/agent_orchestration.py tests/test_agent_orchestration_api.py
git commit -m "feat(agent-tower): GET /api/agents/status/{trace_id}"
```

---

### Task 11: /api/telemetry 端点

**Files:**
- Create: `app/api/telemetry.py`
- Modify: `main.py`
- Test: `tests/test_agent_orchestration_api.py`

- [ ] **Step 1: 写失败测试**

```python
@pytest.mark.asyncio
async def test_telemetry_batch_accepted():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post("/api/telemetry", json={
            "student_id": "u1",
            "batch": [{"type": "scroll", "metrics": {"speed": 100}, "ts": 0}],
        })
    assert r.status_code == 200
    assert r.json()["accepted"] == 1
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/test_agent_orchestration_api.py::test_telemetry_batch_accepted -v`
Expected: 404

- [ ] **Step 3: 创建 telemetry.py**

```python
# app/api/telemetry.py
from __future__ import annotations
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/telemetry", tags=["telemetry"])

_TELEMETRY_BUFFER: dict[str, list] = {}


class TelemetryBatch(BaseModel):
    student_id: str
    batch: list[dict]


@router.post("")
async def post_telemetry(payload: TelemetryBatch):
    buf = _TELEMETRY_BUFFER.setdefault(payload.student_id, [])
    buf.extend(payload.batch)
    return {"accepted": len(payload.batch), "buffer_size": len(buf)}


def get_telemetry(student_id: str) -> list[dict]:
    return _TELEMETRY_BUFFER.get(student_id, [])


def clear_telemetry(student_id: str) -> None:
    _TELEMETRY_BUFFER.pop(student_id, None)
```

- [ ] **Step 4: main.py 挂载**

在 `main.py` 末尾追加：

```python
from app.api.telemetry import router as telemetry_router
app.include_router(telemetry_router, prefix="/api")
```

- [ ] **Step 5: 跑测试确认通过**

Run: `pytest tests/test_agent_orchestration_api.py::test_telemetry_batch_accepted -v`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add app/api/telemetry.py main.py tests/test_agent_orchestration_api.py
git commit -m "feat(agent-tower): POST /api/telemetry 批量埋点接收"
```

---

## Phase 4: 前端基础设施

### Task 12: agent-bus.js 事件总线

**Files:**
- Create: `js/agent-bus.js`
- Test: `tests/frontend/unit/agent-bus.test.js`

- [ ] **Step 1: 写失败测试**

```javascript
// tests/frontend/unit/agent-bus.test.js
const { agentBus } = require('../../js/agent-bus.js');

test('subscribe and emit', () => {
  const fn = jest.fn();
  const off = agentBus.subscribe('agent_step', fn);
  agentBus.emit('agent_step', { agent: 'profiler' });
  expect(fn).toHaveBeenCalledWith({ agent: 'profiler' });
  off();
  agentBus.emit('agent_step', { agent: 'profiler' });
  expect(fn).toHaveBeenCalledTimes(1);
});

test('multiple subscribers', () => {
  const a = jest.fn();
  const b = jest.fn();
  agentBus.subscribe('profile_updated', a);
  agentBus.subscribe('profile_updated', b);
  agentBus.emit('profile_updated', { v: 1 });
  expect(a).toHaveBeenCalledWith({ v: 1 });
  expect(b).toHaveBeenCalledWith({ v: 1 });
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd "C:/Users/22821/PycharmProjects/Hachiware/星识" && npx jest tests/frontend/unit/agent-bus.test.js`
Expected: Cannot find module `../../js/agent-bus.js`

- [ ] **Step 3: 实现 bus**

```javascript
// js/agent-bus.js
// 前端事件总线 — pub/sub for agent SSE events
// 用法:
//   const off = agentBus.subscribe('agent_step', (envelope) => {...});
//   agentBus.emit('agent_step', envelope);
//   off();   // 取消订阅
(function (global) {
  const listeners = new Map();

  function subscribe(event, fn) {
    if (!listeners.has(event)) listeners.set(event, new Set());
    listeners.get(event).add(fn);
    return function off() {
      const set = listeners.get(event);
      if (set) set.delete(fn);
    };
  }

  function emit(event, payload) {
    const set = listeners.get(event);
    if (!set) return;
    for (const fn of set) {
      try { fn(payload); } catch (e) { console.error('[agentBus]', event, e); }
    }
  }

  function clear() { listeners.clear(); }

  global.agentBus = { subscribe, emit, clear };
})(window);
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd "C:/Users/22821/PycharmProjects/Hachiware/星识" && npx jest tests/frontend/unit/agent-bus.test.js`
Expected: 2 passed

- [ ] **Step 5: 提交**

```bash
git add js/agent-bus.js tests/frontend/unit/agent-bus.test.js
git commit -m "feat(agent-tower): 前端 agent-bus pub/sub 事件总线"
```

---

### Task 13: agent-sse-client.js EventSource 客户端（含重连/降级）

**Files:**
- Create: `js/agent-sse-client.js`

- [ ] **Step 1: 实现**

```javascript
// js/agent-sse-client.js
// EventSource 客户端 — 连接后端 /api/agents/execute SSE，断线重连，失败触发 mock fallback
(function (global) {
  const MAX_RETRIES = 3;
  const RETRY_DELAY_MS = 2000;

  function createClient({ url, onEvent, onError, onMockTrigger }) {
    let es = null;
    let retries = 0;
    let closedByUser = false;

    function connect() {
      es = new EventSource(url);
      const events = ['agent_step', 'profile_updated', 'asset_ready',
                      'pipeline_complete', 'error', 'heartbeat'];
      events.forEach(name => {
        es.addEventListener(name, (e) => {
          try {
            const data = JSON.parse(e.data);
            onEvent(name, data);
          } catch (err) {
            console.error('[sse-client] parse', name, err);
          }
        });
      });
      es.onerror = () => {
        if (closedByUser) return;
        es.close();
        retries += 1;
        if (retries > MAX_RETRIES) {
          if (onMockTrigger) onMockTrigger();
          if (onError) onError(new Error('SSE failed after retries'));
          return;
        }
        setTimeout(connect, RETRY_DELAY_MS);
      };
    }

    function close() {
      closedByUser = true;
      if (es) es.close();
    }

    connect();
    return { close };
  }

  global.agentSseClient = { createClient };
})(window);
```

- [ ] **Step 2: 提交（无单测，靠集成测试覆盖）**

```bash
git add js/agent-sse-client.js
git commit -m "feat(agent-tower): agent-sse-client EventSource + 重连 + 降级触发"
```

---

### Task 14: agent-orchestrator.js 状态机

**Files:**
- Create: `js/agent-orchestrator.js`

- [ ] **Step 1: 实现**

```javascript
// js/agent-orchestrator.js
// 控制塔控制器 — 启动流水线 / 状态机
(function (global) {
  const STATES = { IDLE: 'idle', RUNNING: 'running', COMPLETE: 'complete', FAILED: 'failed' };

  class AgentOrchestrator {
    constructor() {
      this.state = STATES.IDLE;
      this.traceId = null;
      this.sseClient = null;
      this.listeners = { stateChange: [], asset: [] };
    }

    on(event, fn) {
      if (!this.listeners[event]) this.listeners[event] = [];
      this.listeners[event].push(fn);
    }

    setState(s) {
      this.state = s;
      this.listeners.stateChange.forEach(fn => fn(s));
    }

    async startPipeline({ studentId, courseId, userInput, mock = false }) {
      this.setState(STATES.RUNNING);
      this.traceId = crypto.randomUUID();

      if (mock) {
        const mockMod = global.agentMockFallback;
        if (mockMod) mockMod.runMockPipeline(this);
        return;
      }

      const body = new URLSearchParams();
      body.set('student_id', studentId || '');
      if (courseId) body.set('course_id', courseId);
      body.set('user_input', userInput);
      body.set('trace_id', this.traceId);

      try {
        const r = await fetch('/api/agents/execute', {
          method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: body.toString(),
        });
        if (!r.ok) throw new Error('execute failed ' + r.status);
      } catch (err) {
        console.error('[orchestrator] start failed', err);
        this.setState(STATES.FAILED);
        return;
      }

      this.sseClient = global.agentSseClient.createClient({
        url: `/api/agents/stream?trace_id=${this.traceId}`,
        onEvent: (name, data) => this._handleSseEvent(name, data),
        onMockTrigger: () => {
          if (global.agentMockFallback) global.agentMockFallback.runMockPipeline(this);
        },
        onError: () => this.setState(STATES.FAILED),
      });
    }

    _handleSseEvent(name, data) {
      global.agentBus.emit(name, data);
      if (name === 'pipeline_complete') {
        this.setState(STATES.COMPLETE);
        if (this.sseClient) { this.sseClient.close(); this.sseClient = null; }
      } else if (name === 'error' && data && data.fatal) {
        this.setState(STATES.FAILED);
      }
    }

    emitAsset(asset) {
      this.listeners.asset.forEach(fn => fn(asset));
    }

    pause() { /* v1.1 */ }
    stop() {
      if (this.sseClient) { this.sseClient.close(); this.sseClient = null; }
      this.setState(STATES.IDLE);
    }
  }

  global.AgentOrchestrator = AgentOrchestrator;
  global.agentOrchestrator = new AgentOrchestrator();
})(window);
```

- [ ] **Step 2: 提交**

```bash
git add js/agent-orchestrator.js
git commit -m "feat(agent-tower): agent-orchestrator 状态机 + 启动/暂停/停止"
```

---

### Task 15: agent-mock-fallback.js

**Files:**
- Create: `js/agent-mock-fallback.js`

- [ ] **Step 1: 实现**

```javascript
// js/agent-mock-fallback.js
// 后端不可用时，注入 mock 流水线（演示不卡）
(function (global) {
  const STEPS = [
    { agent: 'profiler', role: '画像分析', content: '抽取 6 维画像', delay: 300 },
    { agent: 'planner', role: '路径规划', content: '选定 4 个生成器', delay: 250 },
    { agent: 'document_generator', role: '文档生成', content: '输出 Markdown 草稿', delay: 600 },
    { agent: 'exercise_generator', role: '题库生成', content: '生成 5 道练习', delay: 500 },
    { agent: 'mindmap_generator', role: '导图生成', content: '输出 SVG 导图', delay: 400 },
    { agent: 'video_content', role: '视频内容', content: '检索 B 站片段', delay: 700 },
    { agent: 'resource_push', role: '资源推送', content: '匹配推送时机', delay: 200 },
    { agent: 'evaluator', role: '评估', content: '更新掌握度', delay: 200 },
  ];

  function runMockPipeline(orchestrator) {
    orchestrator.setState('running');
    let i = 0;
    function tick() {
      if (i >= STEPS.length) {
        global.agentBus.emit('pipeline_complete', {
          trace_id: orchestrator.traceId, status: 'mock_complete', assets: [],
        });
        orchestrator.setState('complete');
        return;
      }
      const s = STEPS[i++];
      global.agentBus.emit('agent_step', {
        type: 'response', from: s.agent, intent: s.role,
        payload: { status: 'success', output_summary: s.content },
        cost_ms: s.delay,
      });
      setTimeout(tick, s.delay);
    }
    setTimeout(tick, 200);
  }

  global.agentMockFallback = { runMockPipeline };
})(window);
```

- [ ] **Step 2: 提交**

```bash
git add js/agent-mock-fallback.js
git commit -m "feat(agent-tower): agent-mock-fallback 演示模式 mock 流水线"
```

---

### Task 16: agent-telemetry-collector.js

**Files:**
- Create: `js/agent-telemetry-collector.js`

- [ ] **Step 1: 实现**

```javascript
// js/agent-telemetry-collector.js
// 滚动/停留/鼠标 → POST /api/telemetry 每 10s 批量
(function (global) {
  const BATCH_INTERVAL_MS = 10000;
  const buffer = [];
  let studentId = null;
  let timer = null;

  function setStudentId(id) { studentId = id; }

  function push(event) { buffer.push(event); }

  function recordScroll() {
    let lastY = window.scrollY, lastT = Date.now();
    window.addEventListener('scroll', () => {
      const now = Date.now();
      const dy = Math.abs(window.scrollY - lastY);
      const dt = (now - lastT) / 1000;
      if (dt > 0) push({ type: 'scroll', metrics: { speed: dy / dt, depth: window.scrollY / document.body.scrollHeight }, ts: now });
      lastY = window.scrollY; lastT = now;
    }, { passive: true });
  }

  function recordZoneDwell() {
    document.addEventListener('mouseover', (e) => {
      const zone = e.target.closest('[data-zone]');
      if (zone) {
        const start = Date.now();
        const off = () => {
          push({ type: 'zone_dwell', zone: zone.dataset.zone, ms: Date.now() - start, ts: Date.now() });
          zone.removeEventListener('mouseleave', off);
        };
        zone.addEventListener('mouseleave', off);
      }
    });
  }

  function recordMouseIdle() {
    let lastMove = Date.now();
    window.addEventListener('mousemove', () => { lastMove = Date.now(); });
    setInterval(() => {
      push({ type: 'mouse', metrics: { idle_ms: Date.now() - lastMove, movement_count: 0 }, ts: Date.now() });
    }, BATCH_INTERVAL_MS);
  }

  async function flush() {
    if (!buffer.length || !studentId) return;
    const batch = buffer.splice(0, buffer.length);
    try {
      await fetch('/api/telemetry', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ student_id: studentId, batch }),
      });
    } catch (e) { console.warn('[telemetry] flush failed', e); }
  }

  function start(id) {
    setStudentId(id);
    recordScroll(); recordZoneDwell(); recordMouseIdle();
    timer = setInterval(flush, BATCH_INTERVAL_MS);
  }

  function stop() { if (timer) clearInterval(timer); timer = null; }

  global.agentTelemetry = { start, stop, flush };
})(window);
```

- [ ] **Step 2: 提交**

```bash
git add js/agent-telemetry-collector.js
git commit -m "feat(agent-tower): telemetry-collector 滚动/停留/鼠标 → POST /api/telemetry"
```

---

## Phase 5: tokens + 样式

### Task 17: tokens.css 追加新变量

**Files:**
- Modify: `css/tokens.css`（末尾）

- [ ] **Step 1: 在 :root 末尾追加**

```css
:root {
  /* Agent 状态色 */
  --agent-idle: var(--text-tertiary);
  --agent-busy: var(--primary);
  --agent-success: var(--success, #10b981);
  --agent-failed: var(--danger, #ef4444);

  /* 雷达 / 终端 */
  --code-bg: #0a0e1a;
  --radar-fill-start: var(--primary);
  --radar-fill-end: var(--accent);
  --radar-glow: var(--primary-light);

  /* 画像面板 4 卡 */
  --profile-card-bg: var(--surface-glass);
  --profile-card-border: var(--border-glass);
  --profile-label: var(--text-primary);
  --profile-title: var(--text-tertiary);
  --profile-progress: var(--primary);
  --profile-progress-bg: var(--surface-glass-2);

  /* 情绪状态色（4 档） */
  --emotion-calm: var(--success, #10b981);
  --emotion-anxious: var(--warning, #f59e0b);
  --emotion-frustrated: var(--danger, #ef4444);
  --emotion-engaged: var(--primary);
}
```

- [ ] **Step 2: 在 light/dark/neon 主题的 :root 重写里也注册（如果各主题单独定义了 :root 块）**

Run: `grep -n ":root\|\\[data-theme" css/tokens.css | head -20`

对每个主题块（除了默认 :root）都追加相同的 `--agent-*` `--radar-*` `--emotion-*` 段，让切换主题不丢失。

如果发现主题重写区已经定义了 `--primary` / `--accent` / `--surface-glass` 等基础变量，新加的 `--agent-*` 自然会跟随，无需重复定义。

- [ ] **Step 3: 提交**

```bash
git add css/tokens.css
git commit -m "feat(agent-tower): tokens.css 追加 --agent-* --radar-* --emotion-* 变量"
```

---

### Task 18: agent-tower.css 控制塔 + 画像面板样式

**Files:**
- Create: `css/agent-tower.css`

- [ ] **Step 1: 写样式**

```css
/* css/agent-tower.css — Agent 编排控制塔 + 学情画像面板 */

/* === 控制塔 === */
.tower-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 18px; border-bottom: 1px solid var(--border-glass);
}
.tower-header h2 { font-size: 15px; color: var(--text-primary); margin: 0; }
.tower-actions { display: flex; gap: 8px; }
.tower-btn {
  background: var(--surface-glass); border: 1px solid var(--border-glass);
  border-radius: var(--radius-md); padding: 4px 10px;
  color: var(--text-primary); cursor: pointer; font-size: 12px;
  transition: background 200ms;
}
.tower-btn:hover { background: var(--surface-glass-2); }
.tower-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* flow nodes */
.tower-flow {
  display: flex; flex-wrap: wrap; gap: 8px; padding: 12px 18px;
  border-bottom: 1px solid var(--border-glass);
}
.flow-node {
  background: var(--surface-glass); border: 1px solid var(--border-glass);
  border-radius: 10px; padding: 6px 10px; font-size: 12px;
  color: var(--text-secondary); display: inline-flex; align-items: center; gap: 6px;
}
.flow-node.is-busy { color: var(--agent-busy); border-color: var(--agent-busy); box-shadow: 0 0 8px var(--agent-busy); }
.flow-node.is-success { color: var(--agent-success); border-color: var(--agent-success); }
.flow-node.is-failed { color: var(--agent-failed); border-color: var(--agent-failed); animation: pulse-failed 1.2s infinite; }

@keyframes pulse-failed {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* terminal logs */
.tower-terminal {
  background: var(--code-bg); color: var(--success);
  font-family: 'JetBrains Mono', monospace; font-size: 11px;
  padding: 12px 18px; max-height: 220px; overflow-y: auto;
  border-top: 1px solid var(--border-glass);
}
.tower-log-line { margin: 2px 0; }
.tower-log-agent { color: var(--primary-light); }
.tower-log-err { color: var(--danger); }

/* assets drawer */
.tower-drawer {
  border-top: 1px solid var(--border-glass); padding: 12px 18px;
  display: none;
}
.tower-drawer.is-open { display: block; }
.tower-drawer h3 { font-size: 13px; margin: 0 0 8px; color: var(--text-secondary); }
.tower-asset-chip {
  display: inline-block; margin: 4px 6px 0 0; padding: 4px 10px;
  background: var(--surface-glass); border-radius: 999px; font-size: 12px;
  color: var(--text-primary); cursor: pointer;
}

/* === 学情画像 4 卡 === */
.profile-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 12px;
  padding: 12px 18px;
}
.profile-card {
  background: var(--profile-card-bg); border: 1px solid var(--profile-card-border);
  border-radius: var(--radius-md); padding: 10px 12px;
}
.profile-card-title { font-size: 11px; color: var(--profile-title); margin-bottom: 4px; }
.profile-card-value { font-size: 15px; font-weight: 600; color: var(--profile-label); }
.profile-card-value.is-calm { color: var(--emotion-calm); }
.profile-card-value.is-anxious { color: var(--emotion-anxious); }
.profile-card-value.is-frustrated { color: var(--emotion-frustrated); }
.profile-card-value.is-engaged { color: var(--emotion-engaged); }
.profile-progress-bar {
  margin-top: 6px; height: 4px; background: var(--profile-progress-bg);
  border-radius: 2px; overflow: hidden;
}
.profile-progress-bar > div {
  height: 100%; background: var(--profile-progress); width: 0;
  transition: width 200ms ease-in-out;
}
.profile-last-synced { padding: 4px 18px 12px; font-size: 11px; color: var(--text-tertiary); }
```

- [ ] **Step 2: 验证无硬编码**

Run: `cd "C:/Users/22821/PycharmProjects/Hachiware/星识" && git grep -E "#[0-9a-fA-F]{3,6}|rgba?\(" css/agent-tower.css`
Expected: 仅 `--code-bg: #0a0e1a;` 1 个结果（其他都走 var()）

如果还有 0 个，说明完全无硬编码。保留 `--code-bg` 是设计意图（终端背景独立于主题）。

- [ ] **Step 3: 提交**

```bash
git add css/agent-tower.css
git commit -m "feat(agent-tower): agent-tower.css 控制塔 + 画像面板样式(全 tokens.css)"
```

---

## Phase 6: index.html 改造

### Task 19: index.html 头部 + 按钮组 + 资源抽屉 + 画像 2×2 + 身份浮窗

**Files:**
- Modify: `html/index.html`

- [ ] **Step 1: 改 track-a 标题与按钮组**

找到 `html/index.html` 中 `<aside id="track-a-container">`（spec §6.1 引用 line 228-258）。

把 header 替换为：

```html
<aside id="track-a-container">
  <div id="track-a" class="track-sandbox">
    <div class="tower-header">
      <h2>🛰 Agent 编排控制塔</h2>
      <div class="tower-actions">
        <button class="tower-btn" id="tower-pause" disabled>⏸</button>
        <button class="tower-btn" id="tower-stop" disabled>⏹</button>
        <button class="tower-btn" id="tower-start">▶ 启动协作</button>
      </div>
    </div>
    <div class="tower-flow" id="tower-flow"></div>
    <div class="tower-terminal" id="tower-terminal"></div>
    <div class="tower-drawer" id="tower-drawer">
      <h3>资源抽屉</h3>
      <div id="tower-assets"></div>
    </div>
  </div>
</aside>
```

- [ ] **Step 2: 在 #profile-section 内插入 2×2 网格**

找到 `<h2>学情画像</h2>`（`html/index.html:81`）后追加：

```html
<div class="profile-grid" id="profile-grid">
  <div class="profile-card"><div class="profile-card-title">学习风格</div><div class="profile-card-value" data-key="learning_style">—</div></div>
  <div class="profile-card"><div class="profile-card-title">认知水平</div><div class="profile-card-value" data-key="cognitive_level">—</div></div>
  <div class="profile-card">
    <div class="profile-card-title">近期目标</div>
    <div class="profile-card-value" data-key="current_goal">—</div>
    <div class="profile-progress-bar"><div data-key="current_goal_bar"></div></div>
  </div>
  <div class="profile-card"><div class="profile-card-title">情绪状态</div><div class="profile-card-value" data-key="emotion_state">—</div></div>
</div>
<div class="profile-last-synced" id="profile-last-synced">Last synced: —</div>
```

- [ ] **Step 3: 在 body 末尾加 5 身份切换浮窗**

```html
<div id="persona-switcher" class="persona-switcher" hidden>
  <div class="persona-option" data-persona="patient_tutor">陈默 · 温和耐心</div>
  <div class="persona-option" data-persona="socratic_questioner">林问 · 哲学思辨</div>
  <div class="persona-option" data-persona="energetic_lecturer">周燃 · 激情速讲</div>
  <div class="persona-option" data-persona="expert_mentor">严铮 · 严谨深入</div>
  <div class="persona-option" data-persona="caring_counselor">苏语 · 情绪陪伴</div>
</div>
```

- [ ] **Step 4: 引入新 CSS / JS**

在 `</head>` 之前加：
```html
<link rel="stylesheet" href="css/agent-tower.css">
```

在 `</body>` 之前加：
```html
<script src="js/agent-bus.js"></script>
<script src="js/agent-sse-client.js"></script>
<script src="js/agent-mock-fallback.js"></script>
<script src="js/agent-orchestrator.js"></script>
<script src="js/agent-telemetry-collector.js"></script>
```

- [ ] **Step 5: 启动 server 浏览器肉眼验证（人工）**

```bash
uvicorn main:app --port 8000 &
sleep 3
# 浏览器打开 http://localhost:8000/html/index.html
# 确认：标题"🛰 Agent 编排控制塔"、3 个按钮、4 张画像卡、5 身份浮窗
kill %1
```

- [ ] **Step 6: 提交**

```bash
git add html/index.html
git commit -m "feat(agent-tower): index.html 改造 header/按钮组/抽屉/画像 2x2/身份浮窗"
```

---

## Phase 7: index.js 重构（数据源切换 + 删 isSocratic + 雷达真实化）

### Task 20: renderFlowNodes 数据源切换

**Files:**
- Modify: `js/index.js`

- [ ] **Step 1: 找到 renderFlowNodes 函数**

Run: `grep -n "function renderFlowNodes\|FLOW_PIPELINE" js/index.js | head -10`

- [ ] **Step 2: 重写为从 /api/agents/catalog 拉取**

替换 `renderFlowNodes` 函数体：

```javascript
async function renderFlowNodes() {
  const container = document.getElementById('tower-flow');
  if (!container) return;
  container.innerHTML = '<span class="flow-node is-idle">加载中…</span>';
  try {
    const r = await fetch('/api/agents/catalog');
    if (!r.ok) throw new Error('catalog ' + r.status);
    const data = await r.json();
    container.innerHTML = data.agents.map(a =>
      `<span class="flow-node" data-agent="${a.id}" data-stage="${a.stage}">${a.name}</span>`
    ).join('');
  } catch (e) {
    console.error('[renderFlowNodes]', e);
    container.innerHTML = '<span class="flow-node is-failed">目录加载失败</span>';
    if (window.agentMockFallback) {
      // 走 mock catalog
      const mock = [
        { id: 'profiler', name: '画像构建' },
        { id: 'planner', name: '路径规划' },
        { id: 'document_generator', name: '文档生成' },
        { id: 'exercise_generator', name: '题库生成' },
        { id: 'mindmap_generator', name: '导图生成' },
        { id: 'video_content', name: '视频内容' },
        { id: 'resource_push', name: '资源推送' },
        { id: 'evaluator', name: '评估' },
      ];
      container.innerHTML = mock.map(a => `<span class="flow-node" data-agent="${a.id}">${a.name}</span>`).join('');
    }
  }
  // 订阅 agent_step 切换状态
  window.agentBus.subscribe('agent_step', (env) => {
    const node = container.querySelector(`[data-agent="${env.from}"]`);
    if (!node) return;
    node.classList.remove('is-busy', 'is-success', 'is-failed');
    if (env.type === 'error') node.classList.add('is-failed');
    else if (env.payload && env.payload.status === 'success') node.classList.add('is-success');
    else node.classList.add('is-busy');
  });
}

renderFlowNodes();
```

- [ ] **Step 3: 提交**

```bash
git add js/index.js
git commit -m "feat(agent-tower): renderFlowNodes 数据源切换 /api/agents/catalog"
```

---

### Task 21: renderSandboxLog 数据源切换

**Files:**
- Modify: `js/index.js`

- [ ] **Step 1: 找到 renderSandboxLog / updateSandboxStatus**

Run: `grep -n "function renderSandboxLog\|function updateSandboxStatus\|sandbox-logs\|sandboxLogs" js/index.js | head -10`

- [ ] **Step 2: 重写为订阅 agentBus 写入 #tower-terminal**

```javascript
function setupTowerTerminal() {
  const term = document.getElementById('tower-terminal');
  if (!term) return;
  const now = () => new Date().toLocaleTimeString();
  const append = (line, cls) => {
    const div = document.createElement('div');
    div.className = 'tower-log-line' + (cls ? ' ' + cls : '');
    div.textContent = `> ${now()} ${line}`;
    term.appendChild(div);
    term.scrollTop = term.scrollHeight;
  };
  window.agentBus.subscribe('agent_step', (env) => {
    const agent = env.from || env.agent || 'agent';
    const ms = env.cost_ms || '';
    const status = env.payload && env.payload.status;
    const summary = env.payload && env.payload.output_summary || '';
    const cls = env.type === 'error' ? 'tower-log-err' : '';
    append(`${agent}  ${summary || status}  ${ms ? '✓' + ms + 'ms' : ''}`, cls);
  });
  window.agentBus.subscribe('pipeline_complete', (data) => {
    append(`流水线完成  status=${data.status || 'complete'}`);
    const drawer = document.getElementById('tower-drawer');
    if (drawer) drawer.classList.add('is-open');
  });
  window.agentBus.subscribe('error', (data) => {
    append(`ERROR: ${data.message || JSON.stringify(data)}`, 'tower-log-err');
  });
}

setupTowerTerminal();
```

- [ ] **Step 3: 提交**

```bash
git add js/index.js
git commit -m "feat(agent-tower): renderSandboxLog 订阅 agentBus 写入 #tower-terminal"
```

---

### Task 22: renderRadarChart 重构（去硬编码 + 800ms 缓动 + SSE 触发）

**Files:**
- Modify: `js/index.js:3280-3442`

- [ ] **Step 1: 找到 renderRadarChart 函数**

Run: `grep -n "function renderRadarChart\|rgba(" js/index.js | head -20`

- [ ] **Step 2: 替换函数体（去硬编码 + 加缓动）**

```javascript
function renderRadarChart(newValues) {
    const canvas = document.getElementById('radar-chart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    // 1. 从 tokens.css 读颜色（零硬编码）
    const style = getComputedStyle(document.documentElement);
    const stroke = style.getPropertyValue('--radar-glow').trim() || style.getPropertyValue('--primary').trim();
    const fillStart = style.getPropertyValue('--radar-fill-start').trim() || style.getPropertyValue('--primary').trim();
    const fillEnd = style.getPropertyValue('--radar-fill-end').trim() || style.getPropertyValue('--accent').trim();
    const labelColor = style.getPropertyValue('--text-primary').trim();
    const gridColor = style.getPropertyValue('--border-glass').trim();

    const dims = ['知识掌握', '编程能力', '认知风格', '学习目标', '短板识别', '专注度'];
    const current = window.__radarCurrent || Array(6).fill(50);
    const target = newValues || current;

    // 2. 800ms 缓动插值
    animateRadarMorph(current, target, 800, drawFrame);
    window.__radarCurrent = target.slice();

    function drawFrame(values, alpha) {
        const w = canvas.width, h = canvas.height;
        ctx.clearRect(0, 0, w, h);
        const cx = w / 2, cy = h / 2, r = Math.min(w, h) * 0.35;
        const n = values.length;

        // 网格圈
        ctx.strokeStyle = gridColor;
        ctx.lineWidth = 1;
        for (let k = 1; k <= 4; k++) {
            ctx.beginPath();
            for (let i = 0; i < n; i++) {
                const angle = (Math.PI * 2 * i) / n - Math.PI / 2;
                const rr = (r * k) / 4;
                const x = cx + Math.cos(angle) * rr;
                const y = cy + Math.sin(angle) * rr;
                i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
            }
            ctx.closePath(); ctx.stroke();
        }

        // 数据多边形
        ctx.beginPath();
        for (let i = 0; i < n; i++) {
            const angle = (Math.PI * 2 * i) / n - Math.PI / 2;
            const v = (values[i] || 0) / 100;
            const x = cx + Math.cos(angle) * r * v;
            const y = cy + Math.sin(angle) * r * v;
            i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        }
        ctx.closePath();
        const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, r);
        grad.addColorStop(0, fillStart);
        grad.addColorStop(1, fillEnd);
        ctx.globalAlpha = 0.3 * alpha;
        ctx.fillStyle = grad; ctx.fill();
        ctx.globalAlpha = alpha;
        ctx.strokeStyle = stroke; ctx.lineWidth = 2; ctx.stroke();

        // 维度标签
        ctx.fillStyle = labelColor; ctx.font = '12px sans-serif'; ctx.textAlign = 'center';
        for (let i = 0; i < n; i++) {
            const angle = (Math.PI * 2 * i) / n - Math.PI / 2;
            const x = cx + Math.cos(angle) * (r + 20);
            const y = cy + Math.sin(angle) * (r + 20);
            ctx.fillText(dims[i], x, y);
        }
    }
}

function animateRadarMorph(from, to, durationMs, onFrame) {
    const start = performance.now();
    function step(now) {
        const t = Math.min(1, (now - start) / durationMs);
        const eased = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; // easeInOutCubic
        const values = from.map((v, i) => v + (to[i] - v) * eased);
        onFrame(values, eased);
        if (t < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
}

// 初始化一次（用 window.profile 快照兜底）
renderRadarChart([50, 50, 50, 50, 50, 50]);

// 订阅 SSE profile_updated
window.agentBus.subscribe('profile_updated', (data) => {
    if (data && data.radar) {
        const order = ['knowledge_mastery', 'code_skill', 'cognitive_style', 'learning_goal', 'weakness', 'focus_level'];
        const values = order.map(k => data.radar[k] || 0);
        renderRadarChart(values);
    }
});
```

- [ ] **Step 3: 验证无 rgba 硬编码**

Run: `cd "C:/Users/22821/PycharmProjects/Hachiware/星识" && git grep -E "rgba?\(" js/index.js | head -10`
Expected: 仅保留 token 变量读取相关 + 全局 alpha 操作的少量使用；不允许出现 `rgba(255, 0, 0, 0.5)` 这类字面量。

- [ ] **Step 4: 提交**

```bash
git add js/index.js
git commit -m "feat(agent-tower): renderRadarChart 重构(去硬编码+800ms 缓动+SSE 触发)"
```

---

### Task 23: renderProfile 数据源切换为 SSE panel

**Files:**
- Modify: `js/index.js`

- [ ] **Step 1: 找到 renderProfile**

Run: `grep -n "function renderProfile\|window.profile" js/index.js | head -10`

- [ ] **Step 2: 重写 renderProfile 接受 panel 对象**

```javascript
function renderProfile(panel) {
    if (!panel) return;
    const map = {
        learning_style: 'learning_style',
        cognitive_level: 'cognitive_level',
        current_goal:   'current_goal',
        emotion_state:  'emotion_state',
    };
    for (const [k, sel] of Object.entries(map)) {
        const card = document.querySelector(`.profile-card-value[data-key="${k}"]`);
        if (!card) continue;
        const data = panel[k] || {};
        if (k === 'current_goal') {
            card.textContent = data.label || '—';
            const bar = document.querySelector(`[data-key="current_goal_bar"]`);
            if (bar) bar.style.width = (data.progress_pct || 0) + '%';
        } else {
            card.textContent = data.label || '—';
            if (k === 'emotion_state' && data.label) {
                card.classList.remove('is-calm', 'is-anxious', 'is-frustrated', 'is-engaged');
                card.classList.add('is-' + data.label);
            }
        }
    }
}

// 首次填表快照兜底（window.profile 是首填表驼峰字段，aggregator 输出的是蛇形 panel — 字段映射）
renderProfile({
    learning_style: { label: window.profile?.learningStyle || '—' },
    cognitive_level: { label: window.profile?.cognitiveLevel || '—' },
    current_goal:   { label: window.profile?.currentGoal || '—', progress_pct: window.profile?.goalProgress || 0 },
    emotion_state:  { label: 'calm' },
});

// 订阅 SSE
window.agentBus.subscribe('profile_updated', (data) => {
    if (data && data.panel) {
        renderProfile(data.panel);
        const synced = document.getElementById('profile-last-synced');
        if (synced) {
            const t = data.last_synced ? new Date(data.last_synced) : new Date();
            synced.textContent = 'Last synced: ' + t.toLocaleTimeString();
        }
    }
});

// 5s 局部刷新 last_synced（用 last_synced 值倒计时）
setInterval(() => {
    const synced = document.getElementById('profile-last-synced');
    if (!synced) return;
    const ts = synced.dataset.ts;
    if (!ts) return;
    const sec = Math.max(0, Math.floor((Date.now() - parseInt(ts)) / 1000));
    synced.textContent = `Last synced: ${sec}s ago`;
}, 5000);
```

- [ ] **Step 3: 把 profile_updated 内的 ts 写入 dataset**

修改订阅回调最后一行：
```javascript
        if (synded) {  // 注意原代码
          ...
        }
```

更简单做法：直接放在订阅回调里：

```javascript
window.agentBus.subscribe('profile_updated', (data) => {
    if (data && data.panel) {
        renderProfile(data.panel);
        const synced = document.getElementById('profile-last-synced');
        if (synced) {
            const t = data.last_synced ? new Date(data.last_synced) : new Date();
            synced.textContent = 'Last synced: ' + t.toLocaleTimeString();
            synced.dataset.ts = String(t.getTime());
        }
    }
});
```

- [ ] **Step 4: 提交**

```bash
git add js/index.js
git commit -m "feat(agent-tower): renderProfile 数据源切换为 SSE panel + 4 卡同步"
```

---

### Task 24: 删除 isSocratic 全局标志

**Files:**
- Modify: `js/index.js`

- [ ] **Step 1: 找到 isSocratic 引用**

Run: `grep -n "isSocratic\|socratic" js/index.js | head -20`

- [ ] **Step 2: 把 isSocratic 替换为按 persona 字段判断**

找到类似：
```javascript
const isSocratic = ...;
```

改为从 `chat_request.persona`（或 `req.body.persona_id`）读取 `socratic_intensity`：

```javascript
// 替换前
const isSocratic = true;

// 替换后
const personaId = (window.currentPersona || 'expert_mentor');
const personaIntensities = { patient_tutor: 0.4, socratic_questioner: 1.0, energetic_lecturer: 0.1, expert_mentor: 0.7, caring_counselor: 0.0 };
const isSocratic = (personaIntensities[personaId] || 0) >= 0.5;
```

- [ ] **Step 3: 把 chat 请求 body 改为带 persona_id**

找到 fetch /api/teacher/chat 处（spec §16.6 提到），在 body 加 `persona_id`：

```javascript
body.append('persona_id', window.currentPersona || 'expert_mentor');
```

- [ ] **Step 4: 提交**

```bash
git add js/index.js
git commit -m "refactor(agent-tower): 删除全局 isSocratic 标志,改用 persona 字段"
```

---

### Task 25: 5 身份切换浮窗交互

**Files:**
- Modify: `js/index.js`

- [ ] **Step 1: 在尾部加身份切换逻辑**

```javascript
// === 5 身份切换 ===
(function setupPersonaSwitcher() {
    const switcher = document.getElementById('persona-switcher');
    if (!switcher) return;
    // 点击 #teacher-card 或专用按钮展开
    const trigger = document.getElementById('teacher-card');
    if (trigger) {
        trigger.addEventListener('click', () => {
            switcher.hidden = !switcher.hidden;
        });
    }
    switcher.addEventListener('click', (e) => {
        const opt = e.target.closest('.persona-option');
        if (!opt) return;
        const personaId = opt.dataset.persona;
        window.currentPersona = personaId;
        const card = document.getElementById('teacher-card');
        if (card) {
            const label = opt.textContent.split('·')[0].trim();
            card.querySelector('[data-persona-name]')?.replaceChildren(document.createTextNode(label));
        }
        switcher.hidden = true;
        // 同步到后端偏好
        fetch('/api/profile/me', {
            method: 'PATCH', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ preferred_persona: personaId }),
        }).catch(() => {});
    });
})();
```

> 注：若 `/api/profile/me` 路由不存在，catch 兜底即可，不影响主体逻辑。

- [ ] **Step 2: 提交**

```bash
git add js/index.js
git commit -m "feat(agent-tower): 5 身份切换浮窗交互 + preferred_persona 同步"
```

---

## Phase 8: 集成测试 + 文档

### Task 26: Playwright E2E 测试

**Files:**
- Create: `tests/frontend/e2e/agent-tower.spec.js`

- [ ] **Step 1: 写测试**

```javascript
// tests/frontend/e2e/agent-tower.spec.js
const { test, expect } = require('@playwright/test');

test.describe('Agent 编排控制塔', () => {
    test('页面加载后控制塔标题与按钮可见', async ({ page }) => {
        await page.goto('/html/index.html');
        await expect(page.locator('.tower-header h2')).toContainText('Agent 编排控制塔');
        await expect(page.locator('#tower-start')).toBeVisible();
    });

    test('点击 ▶ 启动后 5s 内画像卡有数据', async ({ page }) => {
        await page.goto('/html/index.html');
        await page.click('#tower-start');
        await page.waitForTimeout(6000);
        const style = await page.locator('[data-key="learning_style"]').textContent();
        expect(style).not.toBe('—');
    });

    test('5 身份切换浮窗可点击', async ({ page }) => {
        await page.goto('/html/index.html');
        await page.click('#teacher-card');
        await expect(page.locator('#persona-switcher')).toBeVisible();
        await page.click('[data-persona="caring_counselor"]');
        // 切回不可见
        await expect(page.locator('#persona-switcher')).toBeHidden();
    });

    test('后端 503 时降级为 mock', async ({ page }) => {
        await page.route('**/api/agents/catalog', route => route.fulfill({ status: 503 }));
        await page.goto('/html/index.html');
        await page.waitForTimeout(2000);
        // mock flow nodes 仍渲染
        await expect(page.locator('.flow-node').first()).toBeVisible();
    });
});
```

- [ ] **Step 2: 跑测试**

```bash
cd "C:/Users/22821/PycharmProjects/Hachiware/星识"
npx playwright test tests/frontend/e2e/agent-tower.spec.js --reporter=list
```

Expected: 4 passed (本地 server 已起 + 依赖服务可用)

- [ ] **Step 3: 提交**

```bash
git add tests/frontend/e2e/agent-tower.spec.js
git commit -m "test(agent-tower): Playwright E2E 控制塔 + 画像 + 身份切换 + 降级"
```

---

### Task 27: RUNNING_GUIDE.md 文档

**Files:**
- Modify: `RUNNING_GUIDE.md`

- [ ] **Step 1: 追加"启动 Agent 控制塔"小节**

在文档末尾追加：

```markdown
## 启动 Agent 编排控制塔

Agent 控制塔把 7+1 个后端 agent 的协作实时呈现到前端 `index.html#track-a`。

### 启动步骤
1. 启动 FastAPI: `uvicorn main:app --reload`
2. 打开浏览器: http://localhost:8000/html/index.html
3. 左侧 `🛰 Agent 编排控制塔` 应有 3 个按钮：`⏸` `⏹` `▶ 启动协作`
4. 点击 `▶ 启动协作` → 后端 `MasterController.execute()` 走 SSE
5. 观察 6 维雷达 + 4 张画像小卡应实时变化（800ms 缓动）

### 5 身份差异化苏格拉底

`app/services/teacher/personas.py` 中 5 个 persona 的 `socratic_intensity`：

| persona | name | socratic_intensity | 行为 |
|---------|------|--------------------|------|
| patient_tutor | 陈默 | 0.4 | 基础直讲，进阶给跳板 |
| socratic_questioner | 林问 | 1.0 | 纯反问 |
| energetic_lecturer | 周燃 | 0.1 | 几乎不反问 |
| expert_mentor | 严铮 | 0.7 | 基础直讲，进阶反问 |
| caring_counselor | 苏语 | 0.0 | 0 苏格拉底（情绪场景） |

切换身份：点击教师卡 → 5 头像浮窗 → 选一个。`build_system_prompt` 会按强度注入对应规则。
```

- [ ] **Step 2: 提交**

```bash
git add RUNNING_GUIDE.md
git commit -m "docs(agent-tower): RUNNING_GUIDE 增加启动步骤 + 5 身份差异化苏格拉底"
```

---

### Task 28: 端到端人工验证

- [ ] **Step 1: 启动完整服务**

```bash
cd "C:/Users/22821/PycharmProjects/Hachiware/星识"
uvicorn main:app --reload &
sleep 5
```

- [ ] **Step 2: 浏览器打开 index.html 走完验收清单**

打开 http://localhost:8000/html/index.html，按 spec §12 验收标准 1-29 逐条勾选：

- 控制塔标题 ✓
- ▶ 启动 → SSE 实时 logs ✓
- 8 个 agent 节点 idle→busy→success ✓
- 后端 503 降级 mock ✓
- 资源抽屉在 pipeline_complete 后展开 ✓
- 6 维雷达平滑过渡 ✓
- 4 张画像卡同步刷新 ✓
- 5 身份切换 → 林问以问号结尾 / 苏语共情 / 严铮进阶反问 ✓
- 深度思考徽章 → timeline 双向 toggle ✓
- 0 硬编码颜色 ✓

- [ ] **Step 3: 停止服务，整理提交**

```bash
kill %1
git status   # 确认无未提交
```

---

## 验收（spec §12 复述）

跑通后应满足 spec §12 全部 29 条验收标准。核心自动化验证：

```bash
# 后端
cd "C:/Users/22821/PycharmProjects/Hachiware/星识"
pytest tests/test_agent_orchestration_schemas.py \
       tests/test_agent_log_adapter.py \
       tests/test_portrait_aggregator.py \
       tests/test_persona_socratic_rules.py \
       tests/test_agent_orchestration_api.py -v
# 期望: ≥ 15 passed

# 前端
npx jest tests/frontend/unit/agent-bus.test.js
npx playwright test tests/frontend/e2e/agent-tower.spec.js
# 期望: 2 + 4 passed

# 颜色硬编码
git grep -E "#[0-9a-fA-F]{3,6}|rgba?\(" css/agent-tower.css
# 期望: 仅 --code-bg: #0a0e1a; 一行
```

---

## 任务依赖汇总

| 任务 | 前置 | 预计 LOC |
|------|------|----------|
| 1 schema | — | 80 |
| 2 adapter | 1 | 40 |
| 3 aggregator | 1 | 100 |
| 4 socratic_rules | — | 50 |
| 5 persona dataclass + 苏语 | — | 200 |
| 6 build_system_prompt | 4, 5 | 80 |
| 7 teacher_chat persona_id | 5 | 30 |
| 8 /catalog | 1 | 80 |
| 9 /execute SSE | 1, 2, 3, 8 | 90 |
| 10 /status | 9 | 40 |
| 11 /telemetry | — | 30 |
| 12 agent-bus | — | 40 |
| 13 agent-sse-client | 12 | 60 |
| 14 agent-orchestrator | 12, 13 | 100 |
| 15 agent-mock-fallback | 12 | 50 |
| 16 telemetry-collector | 11 | 60 |
| 17 tokens.css | — | 50 |
| 18 agent-tower.css | 17 | 150 |
| 19 index.html | 17, 18 | 80 |
| 20 renderFlowNodes | 8, 12 | 40 |
| 21 renderSandboxLog | 12, 14 | 40 |
| 22 renderRadarChart | 12, 17 | 130 |
| 23 renderProfile | 12, 17 | 60 |
| 24 删 isSocratic | 7, 5 | 20 |
| 25 5 身份浮窗 | 24 | 40 |
| 26 Playwright E2E | 19-25 | 60 |
| 27 RUNNING_GUIDE | — | 30 |
| 28 人工验证 | 1-27 | — |

**总计: ~1700 LOC（含测试和注释）**
