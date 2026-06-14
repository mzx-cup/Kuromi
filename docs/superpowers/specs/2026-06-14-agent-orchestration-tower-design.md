# Agent 编排控制塔 — 设计文档

**日期**: 2026-06-14
**状态**: 待审批
**作者**: brainstorming with user
**关联文档**:
- `2026-05-08-multi-ai-teachers-design.md`（人格层 5 教师，本设计是功能层）
- `2026-06-01-hub-redesign-design.md`（Hub 整体风格基线）
- `2026-06-03-hub-constellation-prism-design.md`（深色玻璃 / 棱镜美学参考）
- `2026-06-05-mascot-navigation-datacenter-design.md`（导航信息中台数据约定）
- `2026-06-08-frontend-tech-debt-inventory-design.md`（前端技术债清单，本设计是其中"教研沙盘升级"项的实施）

---

## 1. 背景与目标

### 1.1 现状问题

| 问题 | 现状 | 影响 |
|------|------|------|
| 7 个功能 Agent 已实现但**对用户不可见** | `agents.py` 中 7+1 个 Agent 类已存在并被 `MasterController.execute()` 调用 | 用户感受不到"AI 协作"，无法理解系统的智能性 |
| 现有"教研沙盘"是只读日志区 | `index.html#track-a` 显示 sandbox-logs / flow-nodes，但不接收实时事件流 | 沙盘是装饰，不是真正的编排监控台 |
| 6 维知识雷达**不是真实数据** | 前端 `window.profile` 全局对象，来源是用户首次填表的 6 问，**不随 agent 活动更新** | 雷达是静态快照，无法体现"系统越用越懂你" |
| **学情画像面板同样不是真实数据** | `index.html#profile-section` 展示 6 个字段，**数据源与雷达同源（首次填表）**，不随 agent 活动 / 实时行为 / 雷达更新而变 | 即便雷达真了，面板仍然静止，体感割裂 |
| **苏格拉底提问全局生效** | `js/index.js:4084 isSocratic` 标志一旦开启对所有 AI 回答都套用反问模板，**完全无视 `personas.py` 已定义的林问/陈默/周燃/严铮 4 个独立人格** | 选林问 = 全局反问；选周燃也反问——人格彻底失效 |
| 后端 agent 协作**无前端可视化** | `MasterController.execute(state, on_step_complete)` 回调存在但未接 SSE | 前端不知道发生了什么 |
| 雷达渲染含**硬编码 RGBA** | `js/index.js:3304-3442` 至少 6 处 `rgba(...)` 直接写死 | 违反 tokens.css 统一主题规则，主题切换时颜色断裂 |

### 1.2 设计目标

1. **新建"Agent 编排控制塔"** 替换/升级 `index.html#track-a` 教研沙盘：实时呈现 7+1 个 agent 的协作状态
2. **后端 agent 接入 SSE**：包装 `MasterController.execute()`，把 `on_step_complete` 回调事件以 Server-Sent Events 推到前端
3. **6 维知识雷达真实化**：从多源数据（agent 工作流日志、telemetry、`aggregate_profile`）实时聚合，SSE 推送后平滑过渡
4. **学情画像面板实时化**：与雷达共用同一 `profile_updated` 事件流，4 个画像小卡（学习风格/认知水平/近期目标/情绪状态）随雷达同步刷新
5. **5 身份差异化苏格拉底**：删除全局 `isSocratic` 标志；改为 `persona.socratic_intensity ∈ [0,1]`，按身份特性分配 0/10/40/70/100 五档强度
6. **新增 5 号人格"知心辅导员"**（caring_counselor）：情绪/情感支持专家，0% 苏格拉底，纯倾听共情
7. **身份提示词丰富化**：5 个 persona 的 identity / teaching_strategy / tone / behavior_rules 都加细节（背景故事、口头禅、情绪边界、禁用行为）
8. **100% 颜色统一**：控制塔 + 雷达 + 学情画像所有颜色走 `tokens.css` 变量，零硬编码
9. **降级兜底**：后端不可用时切换前端 mock，保证演示不卡

### 1.3 非目标

- 多用户实时协作同一流水线
- 流水线可视化拖拽编排（v1.1 再说）
- 向量记忆 / RAG 检索（v1.2）
- LLM token 用量统计展示（埋点保留即可）
- 资源导出 PDF/PPT（沿用现有 `pptx_export.py`，不动）

---

## 2. 架构总览

```
                          ┌──────────────────────────────────────┐
       用户 ──对话/操作──▶│  index.html: 全息智控学习舱 V5.0        │
                          │  ┌────────────────────────────────┐  │
                          │  │  🛰 Agent 编排控制塔（升级）     │  │
                          │  │  6 维知识雷达（真实化）         │  │
                          │  └────────────────────────────────┘  │
                          └────────────────┬─────────────────────┘
                                           │ fetch / EventSource
                                           ▼
                          ┌──────────────────────────────────────┐
                          │  FastAPI: app/api/agent_orchestration│
                          │  ┌──────────────┐  ┌──────────────┐  │
                          │  │ /catalog     │  │ /execute SSE │  │
                          │  │ GET          │  │ POST → stream│  │
                          │  └──────┬───────┘  └──────┬───────┘  │
                          │         │                 │          │
                          │  ┌──────▼─────────────────▼────────┐ │
                          │  │ MasterController.execute(...)   │ │
                          │  │  on_step_complete → SSE 转发器   │ │
                          │  └──────┬──────────────────────────┘ │
                          └─────────┼────────────────────────────┘
                                    ▼
                          ┌──────────────────────────────────────┐
                          │ 7+1 个 Agent (agents.py 真实类)      │
                          │  Profiler / Planner / Document /     │
                          │  Exercise / Mindmap / Video /        │
                          │  ResourcePush / Socratic / Evaluator │
                          └────────────────┬─────────────────────┘
                                           ▼
                          ┌──────────────────────────────────────┐
                          │ 三层记忆                              │
                          │  - Session  (StudentState.metadata)   │
                          │  - World    (db.get_user_memories)    │
                          │  - Per-Agent  (各 agent 私有)         │
                          └──────────────────────────────────────┘
```

---

## 3. 调度架构：中央 Orchestrator + 7 专家

### 3.1 复用 `MasterController`

`agents.py` 已有 `MasterController`，无需新建。沿用其 API：

```python
class MasterController:
    def register_agent(self, agent: BaseAgent) -> None
    def register_generator(self, name: str, agent: BaseAgent) -> None
    def set_pipeline(self, agents: list[BaseAgent]) -> None
    def set_pre_pipeline(self, agents: list[BaseAgent]) -> None
    def route_generators(self, state: StudentState) -> list[BaseAgent]
    async def execute(
        self,
        state: StudentState,
        on_step_complete: Callable[[AgentStepLog], Awaitable[None]] | None = None,
    ) -> StudentState
```

`execute()` 的 `on_step_complete` 回调是天然的"事件源"——本设计把它接到 SSE 转发器上即可。

### 3.2 流水线（与现有保持一致）

```
pre_pipeline:   [EchoAgent]                              # 登录问候
       ↓
main_pipeline:  [ProfilerAgent, PlannerAgent]            # 串行
       ↓
generators:     [Document, Exercise, Mindmap, Video]      # 并行（route_generators 决定）
       ↓
post:           [ResourcePushAgent, EvaluationAgent]      # 串行
       ↓ (可选)
tutor:          SocraticEvaluatorAgent 监听, 不在主流水线
```

### 3.3 编排规则

| 失败位置 | 策略 |
|----------|------|
| `ProfilerAgent` | abort 整个流水线（画像是依赖根基） |
| `PlannerAgent` | abort |
| 任一 Generator | 标记 `partial_success`，其它继续 |
| `ResourcePushAgent` | 用上次缓存路径兜底 |
| `EvaluationAgent` | 静默失败，不影响主链路 |

---

## 4. 记忆系统（三层）

### 4.1 层级

| 层 | 后端实现 | 前端实现 | 生命周期 |
|----|----------|----------|----------|
| **Session** | `StudentState`（内存对象） | `agent-orchestrator.js` 的 `Map<trace_id, ctx>` | 一次流水线结束销毁 |
| **World** | `db.get_user_memories(user_id)` | localStorage `xingshi-world` | 持久化 |
| **Per-Agent** | 各 agent 通过 `state.metadata` 私有 key 写入 | localStorage `xingshi-agent-{id}` | 持久化 |

### 4.2 关键：6 维画像的真实化

**问题诊断**：
- `state.py` 第 346-354 行定义 `LearningPortrait`（6 维），但 `app/services/profile_aggregator.py` 实际输出的是 3 类别（learning_traits / personality_traits / goals_interests），**两者不匹配**
- 雷达前端从 `window.profile.learningDirection / knowledgeBase / codeSkill / cognitiveStyle / weakness / focusLevel` 读 6 个扁平字段，**数据源是用户填表结果，不随 agent 活动更新**
- **学情画像面板（`#profile-section`，`js/index.js:3247 renderProfile`）读的是同一个 `window.profile`，所以面板和雷达同病**

**真实化方案**：新增 `app/services/portrait_aggregator.py`（不要改现有的 `profile_aggregator.py`，它用于"AI 眼中的你"页面）。该聚合器输出一份**统一快照**，雷达和画像面板都从同一份消费：

```python
def aggregate_portrait_snapshot(
    state: StudentState,
    telemetry: dict | None = None,
    workflow_logs: list[AgentStepLog] | None = None,
) -> dict:
    """输出 雷达 6 维 + 画像面板 4 卡的统一快照"""
    return {
        # === 雷达 6 维 (0-100) ===
        "radar": {
            "knowledge_mastery": _calc_knowledge_score(state),
            "code_skill":        _calc_code_score(state),
            "cognitive_style":   _calc_style_score(state),
            "learning_goal":     _calc_goal_progress(state),
            "weakness":          _calc_weakness_score(state),
            "focus_level":       _calc_focus_score(state, telemetry),
        },
        # === 画像面板 4 卡 (文本 + 元数据) ===
        "panel": {
            "learning_style":   {                           # 学习风格
                "label": state.profile.learning_style,      # "visual" / "auditory" / ...
                "confidence": state.profile.style_confidence,
                "updated_at": state.profile.style_updated_at,
            },
            "cognitive_level":  {                           # 认知水平
                "label": state.profile.cognitive_level,     # "beginner" / "intermediate" / "advanced"
                "score": _calc_cognitive_score(state),
            },
            "current_goal":     {                           # 近期目标
                "label": state.profile.learning_goals[0] if state.profile.learning_goals else "—",
                "progress_pct": _calc_goal_progress(state),
            },
            "emotion_state":    {                           # 情绪状态
                "label": _derive_emotion(state, telemetry), # "calm" / "anxious" / "frustrated" / "engaged"
                "intensity": _calc_emotion_intensity(telemetry),
            },
        },
        "last_synced": datetime.utcnow().isoformat() + "Z",
    }
```

**雷达 6 维数据来源矩阵**（同 §4.2 旧版）：

| 维度 | 主信号源 | 辅助信号源 | 实时触发 |
|------|----------|------------|----------|
| knowledge_mastery | `state.profile.knowledge_mastery[]` | `workflow_logs` 中 quiz 正确率 | 流水线完成 / 单题作答 |
| code_skill | `state.profile.code_skill.level` | `state.profile.code_practice_time` | 流水线完成 |
| cognitive_style | `state.profile.cognitive_style.type + confidence` | `workflow_logs` 中 blind_spots | 流水线完成 |
| learning_goal | `state.current_path` 完成比例 | `planner_output` 节点状态 | 路径节点状态变更 |
| weakness | `state.profile.weakness.areas` | `profiler.metadata["blind_spots"]` | profiler 运行后 |
| focus_level | `profiler.metadata["overload_score"]` | `telemetry.scroll_metrics / zone_dwell_times` | telemetry 上报时 |

**画像面板 4 卡数据来源矩阵**（新增）：

| 卡片 | 主信号源 | 辅助信号源 | 实时触发 |
|------|----------|------------|----------|
| learning_style   | `state.profile.learning_style` | `workflow_logs` 中 quiz 正确率(visual 学员看图题更高) | profiler / evaluator 完成后 |
| cognitive_level  | `state.profile.cognitive_level` | quiz 正确率历史 | 单题作答 / 流水线完成 |
| current_goal     | `state.profile.learning_goals[0]` | `state.current_path` 完成比例 | 路径节点状态变更 |
| emotion_state    | `telemetry.mouse_idle_ms + zone_dwell_times` | `state.metadata["emotion_history"]` | telemetry 上报时 |

**触发更新链（雷达 + 画像面板）**：

```
任意 agent.run() 完成
  └─ state.add_workflow_log()
       └─ MasterController 回调 on_step_complete(log)
            └─ SSE 转发器
                 ├─ emit "agent_step" → 前端控制塔日志
                 └─ if log.agent_role ∈ {"画像分析", "评估", "路径规划"} or telemetry_tick:
                       重新调用 aggregate_portrait_snapshot()
                       └─ emit "profile_updated" → 前端
                            ├─ payload.radar → animateRadarMorph(newValues, 800ms)
                            └─ payload.panel → renderProfile(newValues)   # 4 卡同步刷新
```

**Telemetry 上报通道**（新增 `app/api/telemetry.py`）：
- 前端 `js/telemetry-collector.js` 采集滚动/停留/鼠标 → `POST /api/telemetry` 每 10s 批量
- 后端写入进程内 `_telemetry_buffer[student_id]`，下次 `ProfilerAgent._analyze_telemetry` 时合并到 `state.telemetry_data`
- 这是雷达"focus_level"维度 + 画像"emotion_state"卡 的实时数据源

---

## 5. 消息协议（统一信封）

### 5.1 Envelope Schema

```python
# app/schemas/agent_orchestration.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal

class Envelope(BaseModel):
    # 标识
    msg_id: str                              # uuid v4
    trace_id: str                            # 一次流水线共享
    parent_msg_id: str | None = None
    correlation_id: str | None = None

    # 路由
    from_: str = Field(alias="from")
    to: str                                  # "profiler" | "bus:profile_updated" | ...
    type: Literal["request", "response", "event", "error", "heartbeat"]

    # 业务
    intent: str                              # "extract_profile" | "emit_profile_updated" | ...
    payload: dict

    # QoS
    priority: int = Field(5, ge=0, le=9)
    ttl_ms: int = 30000
    deadline: int                            # unix ms
    retry_count: int = 0
    max_retries: int = 1

    # 观测
    schema_version: str = "1.0"
    cost_ms: int = 0
    cost_tokens: int = 0
    timestamp: int                           # unix ms
```

JSON 序列化时 `from_` → `from`（Pydantic alias）。

### 5.2 通信模式

| 流向 | 机制 | 用途 |
|------|------|------|
| Frontend → Backend | HTTP POST | 启动流水线、查询目录、查询状态 |
| Backend → Frontend | SSE | 推送 agent_step / profile_updated / pipeline_complete |
| Orchestrator → Specialist | In-process async | 已存在，无需改造 |
| Specialist → Orchestrator | Callback `on_step_complete` | 已存在 |
| 任何 → Bus | `bus.emit(envelope)` | 跨 agent 旁路通知（前端） |

### 5.3 与现有 `AgentStepLog` 的映射

`agents.py:38-55` 的 `AgentStepLog`：

```python
AgentStepLog(
    agent_name, agent_role, input_summary, output_summary,
    processing_time_ms, status, error_message, timestamp
)
```

→ 序列化为 Envelope：

```json
{
  "msg_id": "<uuid>", "trace_id": "<uuid>", "from": "<agent_name>",
  "to": "orchestrator", "type": "response", "intent": "<agent_role>",
  "payload": {
    "input_summary": "...", "output_summary": "...",
    "status": "success", "error_message": ""
  },
  "cost_ms": 320, "timestamp": 1718332800000,
  "schema_version": "1.0", "priority": 5
}
```

适配器在 `app/api/agent_orchestration.py` 中实现，不修改 `agents.py` 业务逻辑。

---

## 6. UI 设计：Agent 编排控制塔

### 6.1 位置：升级 `index.html#track-a` 教研沙盘

复用现有 DOM，最大化利用既有 `renderFlowNodes` / `renderSandboxLog` / `updateSandboxStatus` 函数。

```
index.html line 228-258:
<aside id="track-a-container">
  <div id="track-a" class="track-sandbox">
    ┌── sandbox-header ──────────────────────────────┐
    │  🛰 Agent 编排控制塔      [⏸] [⏹] [▶ 启动协作] │   ← 新增按钮组
    ├── flow-nodes (id) ─────────────────────────────┤
    │  [画像]→[规划]→[并行 4 个]→[推送]→[辅导]        │   ← 数据从 /api/agents/catalog
    ├── sandbox-logs (id) ───────────────────────────┤
    │  > 10:23:01 profiler  抽取 6 维     ✓320ms     │   ← SSE 实时流
    │  > 10:23:02 planner   选定 4 生成器              │
    │  > 10:23:03 doc-gen   markdown     ✓540ms       │
    ├── 资源抽屉 (折叠) ──────────────────────────────┤
    │  📄 文档  📝 题库  🧠 导图  💻 代码  🗺 路径     │   ← 流水线完成后展开
    └──────────────────────────────────────────────────┘
```

**6 维知识雷达位置不变**：继续留在 `#left-col` 顶部现有 `glass-radar-wrap` 容器内（`id="radar-chart"`），不挪到控制塔。仅改造其数据源（SSE `profile_updated`）与渲染（去硬编码 + 加动画）。控制塔与雷达在左侧栏上下相邻，共同订阅同一个 SSE 流。

**修改清单**（仅改动，不删除）：
- header 文案 `教研沙盘` → `Agent 编排控制塔`
- header 图标 `activity` → `network`（Lucide）
- header 按钮组新增 `▶ 启动协作` `⏸` `⏹`
- flow-nodes 数据源：`FLOW_PIPELINE` 常量 → `GET /api/agents/catalog`
- sandbox-logs 数据源：mock 数组 → EventSource 订阅 `/api/agents/stream?trace_id=...`
- 末尾追加资源抽屉 DOM（默认折叠）
- 雷达：`renderRadarChart` 重构（去硬编码 RGBA + SSE `profile_updated` 触发 `animateRadarMorph` 800ms 缓动）

### 6.2 视觉规范（0 硬编码颜色）

**约束（写入验收）**：
- `css/agent-tower.css` 所有颜色 `var(--xxx)`，禁止 `#hex` / `rgb()` / `rgba()` 硬编码
- `git grep -E "#[0-9a-fA-F]{3,6}|rgba?\(" css/agent-tower.css` 必须无结果

**新增 tokens**（在 `css/tokens.css` 末尾追加，跨主题均注册）：

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
}
```

**控制塔样式规范**：

| 元素 | 变量 |
|------|------|
| 面板背景 | `var(--surface-glass)` |
| 面板边框 | `var(--border-glass)` |
| 状态色 idle | `var(--agent-idle)` |
| 状态色 busy | `var(--agent-busy)` + `box-shadow: 0 0 12px var(--agent-busy)` |
| 状态色 success | `var(--agent-success)` |
| 状态色 failed | `var(--agent-failed)` + 脉冲动画 |
| 终端背景 | `var(--code-bg)` |
| 终端绿字 | `var(--success)` |
| 终端红字 | `var(--danger)` |
| 终端关键字 | `var(--primary-light)` |
| 字体（UI） | 沿用 `tokens.css` 字体栈 |
| 字体（终端） | JetBrains Mono |
| 圆角 | `var(--radius-md)` (14px) |
| 阴影 | `var(--shadow-sm)` → hover `var(--shadow-md)` |

### 6.3 雷达真实化的视觉表现

```js
// renderRadarChart 改造要点
function renderRadarChart(newValues) {
    // 1. 读取 tokens.css 颜色（不再用硬编码 rgba）
    const style = getComputedStyle(document.documentElement);
    const radarStroke = style.getPropertyValue('--radar-glow').trim();
    const radarFill = style.getPropertyValue('--radar-fill-start').trim();
    // ... 其他颜色同理

    // 2. 平滑过渡（用 requestAnimationFrame 做插值）
    animateRadarMorph(currentValues, newValues, 800);  // 800ms 缓动

    // 3. 维度标签从硬编码 6 项改为从数据源取
    const dims = ['知识掌握', '编程能力', '认知风格', '学习目标', '短板识别', '专注度'];
    // ↑ 这 6 项对应 portrait_aggregator 输出的 key
}
```

**动画**：旧值→新值用 `easeInOutCubic` 800ms 插值，6 个数据点同时过渡。监听 SSE `profile_updated` 事件时触发。

### 6.3.1 学情画像面板的真实化（同源同步）

`#profile-section` 4 张小卡视觉规范：

```
┌─ 学情画像 ──────────────────┐
│ ┌──────┐ ┌──────┐          │
│ │ 视觉 │ │中级  │  ...      │   ← 4 卡 grid，gap=12px
│ │学习  │ │认知  │          │
│ │风格  │ │水平  │          │
│ └──────┘ └──────┘          │
│ ┌──────┐ ┌──────┐          │
│ │ 近期 │ │ 情绪 │          │
│ │ 目标 │ │ 状态 │          │
│ │ 65%  │ │ 平静 │          │
│ └──────┘ └──────┘          │
│ Last synced: 3s ago         │   ← last_synced 倒计时
└────────────────────────────┘
```

| 元素 | 变量 |
|------|------|
| 卡背景 | `var(--surface-glass)` |
| 卡边框 | `var(--border-glass)` |
| 卡标题 | `var(--text-tertiary)` 12px |
| 标签值 | `var(--text-primary)` 16px bold |
| 标签值 — 情绪颜色 | `var(--success)` 平静 / `var(--warning)` 焦虑 / `var(--danger)` 挫败 / `var(--primary)` 投入 |
| 进度条（current_goal） | `var(--primary)` 实心 + `var(--surface-glass-2)` 底 |
| "last_synced" 字色 | `var(--text-tertiary)` 11px |

**前端函数 `renderProfile(panel)`**：
- 接收 SSE `profile_updated.payload.panel`
- 4 张卡的 label/数字/进度条全部更新；颜色按 emotion_state 切换
- 进度条用 CSS `width` 200ms 缓动
- "last_synced" 用相对时间（`formatRelative(panel.last_synced)`），每 5s 局部更新一次

**注意：删除原 `window.profile` 全局对象的写时副作用**。`renderProfile` 改为从 SSE 事件的 `event.detail.payload.panel` 读取，不再回填 `window.profile`（`window.profile` 仍保留作为首次填表快照的兜底，但只读）。

### 6.4 三种交互模式

| 模式 | 触发 | 行为 |
|------|------|------|
| 自动启动 | 用户在对话框提交内容 | `startPipeline(input)` → POST /execute → SSE 监听 |
| 手动启动 | 点击 ▶ 启动按钮 | 同上（input 来自最近一次对话或默认 prompt） |
| 单步调试 | DevTools / `window.__AGENT_TOWER__.step('profiler')` | 单 agent 调试（v1.1） |

### 6.5 点击 Agent 卡片 → 详情抽屉

- 工具列表（可点击但不调用，仅展示）
- 私有记忆（mock 卡片显示最近 5 条）
- 最近 5 步日志（来自 `workflow_logs`）

---

## 7. 后端 API 设计

### 7.1 `GET /api/agents/catalog`

返回 agent 目录与流水线定义（前端拿来渲染 flow-nodes）。

```json
{
  "agents": [
    {
      "id": "profiler", "name": "画像构建", "role": "画像分析智能体",
      "tools": ["6 维画像更新", "情绪识别", "盲区检测", "认知超载干预"],
      "memory_keys": ["student_profile", "blind_spots", "telemetry_data"],
      "stage": "main"
    },
    {
      "id": "planner", "name": "路径规划", "role": "路径规划智能体",
      "tools": ["知识图谱", "内容类型路由", "难度梯度"],
      "stage": "main"
    },
    ...
  ],
  "pipeline": [
    {"stage": "pre",   "agents": ["echo"]},
    {"stage": "main",  "agents": ["profiler", "planner"]},
    {"stage": "parallel", "agents": ["document_generator", "exercise_generator", "mindmap_generator", "video_content"], "max_concurrent": 4},
    {"stage": "post",  "agents": ["resource_push", "evaluator"]}
  ]
}
```

### 7.2 `POST /api/agents/execute`

启动流水线，返回 SSE 流。

**Request**：
```json
{
  "student_id": "user-123",
  "course_id": "bigdata",
  "user_input": "我想学 Python 函数",
  "trace_id": "pipe-uuid-optional"
}
```

**Response**：`Content-Type: text/event-stream`

事件类型（`event:` 字段）：

| event | data 内容 | 触发时机 |
|-------|-----------|----------|
| `agent_step` | Envelope (type=response) | 每个 agent.run() 完成 |
| `profile_updated` | `{trace_id, radar: {6 维}, panel: {4 卡}}` | profiler / evaluator / planner 完成后,或 telemetry tick |
| `asset_ready` | `{trace_id, asset_type, ref}` | 单个生成器完成 |
| `pipeline_complete` | `{trace_id, status, assets[]}` | 全部完成 |
| `error` | `{trace_id, agent, message, retryable}` | 异常 |

**错误流**：后端异常 → SSE 发 `event: agent_step type=error`，前端红色渲染并标 partial。

### 7.3 `GET /api/agents/status/{trace_id}`

查询流水线状态（前端刷新页面后恢复时用）。

```json
{
  "trace_id": "...",
  "status": "running" | "complete" | "partial_success" | "failed",
  "started_at": "...",
  "completed_at": "...",
  "agents": [
    {"id": "profiler", "status": "success", "cost_ms": 320},
    ...
  ],
  "assets": [...]
}
```

### 7.4 `POST /api/telemetry`

前端 telemetry 批量上报。

**Request**：
```json
{
  "student_id": "user-123",
  "batch": [
    {"type": "scroll", "metrics": {"speed": 245, "depth": 0.6}, "ts": 1718332800000},
    {"type": "zone_dwell", "zone": "knowledge-radar", "ms": 12000, "ts": 1718332805000},
    {"type": "mouse", "metrics": {"idle_ms": 3500, "movement_count": 8}, "ts": 1718332810000}
  ]
}
```

后端写入进程内 `_telemetry_buffer[student_id]`，下次 `ProfilerAgent._analyze_telemetry` 时合并到 `state.telemetry_data`。

---

## 8. 前端数据流

```
User click ▶ 启动
   └─ js/index.js#startPipeline(input)
        ├─ trace_id = uuid()
        ├─ POST /api/agents/execute {student_id, course_id, user_input, trace_id}
        └─ new EventSource('/api/agents/stream?trace_id=...')
             ├─ on agent_step → agent-bus.emit(envelope)
             │                    ├─ renderFlowNodeStatus(agent_id, status)
             │                    ├─ appendLog(envelope)  // 终端样式
             │                    └─ updateAgentCardCounters(agent_id, cost_ms)
             │
             ├─ on profile_updated → animateRadarMorph(newValues, 800ms)
             │                         update window.profile
             │
             ├─ on asset_ready → push to assets[] 数组
             │
             └─ on pipeline_complete → 展开资源抽屉
                                       └─ dispatch CustomEvent 'agent_assets_ready'
```

**降级**（`js/agent-mock-fallback.js`）：
- 检测 `EventSource` 错误 或 后端 503 → 注入 mock setTimeout 流水线
- 顶部条幅提示"已切换演示模式"
- mock 数据使用与 catalog 一致的 agent 列表，保证视觉一致

---

## 9. 文件清单

### 9.1 新建

| 路径 | 用途 |
|------|------|
| `app/api/agent_orchestration.py` | FastAPI 路由：catalog / execute SSE / status / telemetry |
| `app/schemas/agent_orchestration.py` | Pydantic 模型：Envelope / PipelineRequest / PipelineEvent |
| `app/services/portrait_aggregator.py` | 6 维画像聚合器（基于 StudentState + telemetry + workflow_logs） |
| `app/services/agent_log_adapter.py` | AgentStepLog → Envelope 转换 |
| `js/agent-orchestrator.js` | 前端控制器（startPipeline / state machine） |
| `js/agent-bus.js` | 前端事件总线（pub/sub） |
| `js/agent-sse-client.js` | EventSource 客户端（断线重连 / 降级触发） |
| `js/agent-mock-fallback.js` | 后端不可用时的前端 mock |
| `js/agents/_base.js` | 前端 Agent 基类 |
| `js/agents/profiler.js` `doc-gen.js` `quiz-gen.js` `multimodal.js` `code-lab.js` `path-planner.js` `tutor.js` | 前端 7 个 Agent 适配器 |
| `js/telemetry-collector.js` | 滚动/停留/鼠标采集 → POST /api/telemetry |
| `css/agent-tower.css` | 控制塔样式（~250 行） |
| `tests/backend/test_agent_orchestration_api.py` | 后端 pytest |
| `tests/frontend/agent-tower.spec.js` | Playwright E2E |

### 9.2 修改

| 路径 | 改动 |
|------|------|
| `html/index.html` | header 文案 + 按钮组 + 资源抽屉 + 雷达位置 + 学情画像 2×2 卡片布局 + 5 身份切换浮窗 |
| `js/index.js` | `renderFlowNodes` / `renderSandboxLog` 数据源切换；新增 `startPipeline`；`renderRadarChart` 重构（去硬编码 + 加动画）；`renderProfile` 数据源改为 SSE；删除 `isSocratic` 全局标志；`renderThinkStrip` 双向 toggle 修复（已修） |
| `css/tokens.css` | 追加 `--agent-*` `--code-bg` `--radar-*` `--emotion-*` 等变量 |
| `main.py` | `app.include_router(agent_orchestration.router, prefix="/api/agents")` |
| `app/services/teacher/personas.py` | `Persona` dataclass 增 `socratic_intensity` / `domain` / `crisis_keywords` 字段；新增 `caring_counselor`；5 个 persona prompt 全部重写到 500-800 token |
| `app/api/teacher_chat.py` | `TeacherChatRequest` 增 `persona_id` 字段；`build_system_prompt` 调用按 `socratic_intensity` 注入规则 |
| `RUNNING_GUIDE.md` | 增加"启动 Agent 控制塔"步骤 + "5 身份差异化苏格拉底"段落 |

### 9.3 不动

- `agents.py`（业务逻辑零改动，仅通过回调接出）
- `state.py`（Pydantic 模型已足够）
- `teachers-config.js`（人格层解耦）
- 现有 `renderFlowNodes` / `renderSandboxLog` 等函数（仅替换数据源，不重写）

---

## 10. 错误处理矩阵

| 错误 | 检测 | 处理 |
|------|------|------|
| 后端连接失败 | `EventSource.onerror` | 切 mock fallback + 顶部条幅 |
| 后端超时 (>30s) | 前端 setTimeout 兜底 | abort SSE + 资源抽屉显示部分 |
| Envelope schema 不匹配 | Pydantic 校验（后端）/ 字段检查（前端） | 拒绝 + 日志 + bus emit `schema_mismatch` |
| 单 Agent 失败 | `AgentStepLog.status=error` | 标红 + 其它继续 + partial 标记 |
| localStorage 满 | `setItem` 抛 QuotaExceededError | World 降级 sessionStorage + 提示 |
| 用户中途刷新 | `beforeunload` | 提示"协作进行中" |
| 流水线无限重试 | `retry_count >= 3` | 强制 stop + 弹模态 |
| `profiler` 持续失败 3 次 | 状态机计数 | 弹模态"请填写基础信息" |
| Telemetry 批量失败 | POST /telemetry 503 | 本地 IndexedDB 暂存 + 下次重试 |

---

## 11. 测试计划

| 层 | 类型 | 工具 | 覆盖 |
|----|------|------|------|
| 后端 | 单元 | pytest | `MasterController.execute` 正常/失败/部分失败；`get_agent_catalog` 完整；`portrait_aggregator` 6 维计算 |
| 后端 | 集成 | pytest + httpx.AsyncClient | `/execute` SSE 事件流完整；schema 校验；`/telemetry` 写入 |
| 后端 | 契约 | schemathesis | Envelope Pydantic 拒绝非法字段 |
| 前端 | 单元 | vitest | `agent-bus` pub/sub；envelope 序列化；mock fallback；`renderRadarChart` 动画 |
| 前端 | E2E | Playwright | 启动→看到 agent_step 事件流→资源抽屉展开；后端 503 降级；雷达 800ms 平滑过渡 |
| 前端 | 视觉 | Playwright 截图 | 三主题 × 三状态（idle/running/done）= 9 张截图 |
| 端到端 | 手动 | `RUNNING_GUIDE.md` | 启动 FastAPI + 打开 index + 点 ▶ → 全链路可见 + 雷达实时变化 |

---

## 12. 验收标准

1. [ ] `index.html` 加载后左侧 `track-a` 标题为 "Agent 编排控制塔"
2. [ ] 点击 ▶ 启动 → 真实调用 `POST /api/agents/execute` → SSE 事件实时填入 logs
3. [ ] 7+ 个 agent 节点从 idle→busy→success/failed 状态可见
4. [ ] 后端 503 时自动降级为 mock 流水线（不报错、不卡死、顶部有提示条）
5. [ ] 资源抽屉在 `pipeline_complete` 后展开，含文档/题库/导图/代码/路径入口
6. [ ] 任意 agent 卡片可点击查看：工具列表 / 私有记忆 / 最近 5 步
7. [ ] `git grep -E "#[0-9a-fA-F]{3,6}|rgba?\(" css/agent-tower.css` 无结果
8. [ ] 切换 light/dark/neon 主题，控制塔 + 雷达配色随主题自适应
9. [ ] 后端新增 agent 类后，仅重启服务即出现在前端面板（catalog 数据驱动）
10. [ ] 6 维雷达在流水线完成后 800ms 内平滑过渡到新分数
11. [ ] 雷达"专注度"维度能反映 telemetry 上报（连续快速滚动 → 雷达点收缩）
12. [ ] 现有功能（5 教师人格、6 维填表、Cockpit 其它模块）零回归
13. [ ] 现有 7 个相关 pytest 通过、Playwright 集成测试通过

**学情画像实时化**（§15）
14. [ ] 启动流水线 5s 内，4 张画像小卡至少刷新 1 次
15. [ ] 雷达更新和画像更新来自同一 SSE 事件，**数据强一致**（不会出现面板已变而雷达未变）
16. [ ] 情绪状态卡按 `calm/anxious/frustrated/engaged` 切色，符合 §6.3.1 规范

**5 身份差异化苏格拉底**（§16）
17. [ ] 选林问：80% 以上 speech 以问号结尾
18. [ ] 选周燃：几乎无反问，陈述句为主
19. [ ] 选知心辅导员（苏语）：输入"我觉得活着没意思"，**立即**得到共情回应（非反问）
20. [ ] 选知心辅导员：输入"我刚才吃了什么"（学科问题），礼貌转接给学科教师
21. [ ] 选知心辅导员：输入"我想死"，**立即**触发危机转介话术
22. [ ] 选严铮："什么是函数" 基础问题**不**反问，"如何设计可扩展的事件总线" 反问
23. [ ] 选陈默："听懂了吗" 类确认句出现，反问比例 ≤ 30%
24. [ ] 5 个 persona 切换后响应时间差异 < 1s

**身份提示词丰富化**（§17）
25. [ ] 5 个 persona 的 identity 字段长度都 ≥ 250 字
26. [ ] 每个 persona 有 ≥ 3 条 `opening_phrases` 和 ≥ 2 条 `closing_phrases`
27. [ ] 同一问题"如何学 Python" 用 5 个 persona 各问一次，5 个回答**首句**完全不同

**深度思考按钮 bug**（已修）
28. [ ] 点击"✨ 已深度思考" → 徽章消失，timeline 展开；点击 timeline 任意位置 → timeline 消失，徽章回归
29. [ ] badge 和 timeline 状态互斥，不会同时出现，也不会同时消失

---

## 13. 后续路线

- **v1.0**（本 spec）：监控式控制塔 + 真实后端 SSE + 雷达真实化
- **v1.1**：拖拽式 pipeline 编辑器；单步调试模式
- **v1.2**：向量记忆 + RAG 真接入（minimax embedding）
- **v1.3**：多用户实时协作同一流水线（CRDT）
- **v2.0**：agent 自动协商 vs 调度器静态路由

---

## 14. 决策记录

| 决策 | 选择 | 理由 |
|------|------|------|
| 调度模式 | 中央 Orchestrator + 7 专家 | 可观测、可控、易调试；与现有 `MasterController` 复用 |
| 记忆分层 | Session + World + Per-Agent | 隔离性与共享性兼顾 |
| 消息协议 | 统一 Envelope + SSE | 与 AgentStepLog 1:1 映射，开发成本最低 |
| 通信模式 | 同步 RPC + 异步事件总线 混合 | 主链路同步保证时序，旁路事件解耦 |
| 视觉风格 | 控制室 / 监控室 | 与全息智控学习舱主题兼容 |
| 颜色规则 | 0 硬编码，全 tokens.css | 主题切换无样式断裂 |
| 雷达数据 | 6 维 portrait_aggregator 聚合 | 与 Pydantic `LearningPortrait` 一致 |
| 雷达更新 | SSE profile_updated + 800ms 缓动 | 平滑过渡不抖动 |
| 降级策略 | mock fallback + 顶部条幅 | 演示不中断 |
| 现有代码 | 升级而非替换 | 一次 diff 最小化 |

---

## 15. 学情画像面板实时化（与雷达同源同步）

### 15.1 位置与现状

- 位置：`index.html#profile-section`（`html/index.html:81-85`）
- 现状函数：`js/index.js:3247 renderProfile()`，读 `window.profile`（首次填表快照）
- 现状问题：与雷达共用同一数据源（已快照化），不随 agent 活动 / telemetry 变化

### 15.2 改造方案

**核心思想**：把 `renderProfile` 的数据源从 `window.profile` 改为 SSE `profile_updated.payload.panel`，与雷达共用同一事件流，删除双重维护。

**新增 4 张小卡**（网格布局，2×2）：

| 卡片 | 显示内容 | 颜色 |
|------|----------|------|
| 学习风格 | 标签 `视觉型` / `听觉型` / `动觉型` + 置信度环 | `var(--text-primary)` |
| 认知水平 | 标签 `初级` / `中级` / `高级` + 0-100 数字 | `var(--text-primary)` |
| 近期目标 | 第一条 `state.profile.learning_goals[0]` + 进度条 0-100% | `var(--primary)` 实心 |
| 情绪状态 | 标签 `平静` / `焦虑` / `挫败` / `投入` + 强度 1-5 | 按状态切色（见 §6.3.1 表） |

### 15.3 数据契约（`portrait_aggregator.aggregate_portrait_snapshot().panel`）

```json
{
  "panel": {
    "learning_style":  {"label": "visual",   "confidence": 0.82, "updated_at": "..."},
    "cognitive_level": {"label": "intermediate", "score": 65},
    "current_goal":    {"label": "掌握 Python 函数式编程", "progress_pct": 42},
    "emotion_state":   {"label": "engaged",  "intensity": 4}
  }
}
```

`emotion_state.label` 枚举：`calm | anxious | frustrated | engaged`（与 telemetry 鼠标空闲、滚动速度、停留时长联动）。

### 15.4 触发与节流

- 每次 `profile_updated` SSE 事件触发一次
- 节流：500ms 内重复事件合并为 1 次（避免快速 telemetry tick 时频繁重渲染）
- "last_synced" 时间戳每 5s 局部刷新（`formatRelative` + `setInterval`），不重渲整个面板

### 15.5 验收

1. 启动流水线后 5s 内，4 张小卡至少刷新 1 次
2. 在控制塔点击 `▶ 启动` 前 5s，对照同一时刻雷达更新 — 两边数据来自同一份 `payload`，不能出现面板已变而雷达未变（或反之）
3. 切换 light/dark/neon 主题，4 张卡配色随主题自适应（用 `var(--xxx)`）
4. `git grep -E "#[0-9a-fA-F]{3,6}|rgba?\(" js/index.js` 涉及 renderProfile 部分无硬编码

---

## 16. 5 身份差异化苏格拉底 + 新增知心辅导员

### 16.1 现状问题

- `js/index.js:4084 isSocratic` 标志全局生效 → 选哪个 persona 都套反问模板
- `app/services/teacher/personas.py` 已有 4 个独立人格（陈默/林问/周燃/严铮）但**与 Socratic 模式无关**
- 用户希望：选林问 = 100% 苏格拉底；选陈默 = 温和引导；选周燃 = 几乎不反问；严铮 = 进阶话题才反问；新增知心辅导员 = 0% 苏格拉底

### 16.2 新增第 5 个人格：`caring_counselor`（知心辅导员）

```python
PERSONAS['caring_counselor'] = Persona(
    persona_id='caring_counselor',
    name='苏语',
    identity=(
        '我是苏语，今年 39 岁，国家二级心理咨询师，曾经在武汉某重点高中做专职心理老师八年，'
        '去年加入星识平台做"学习关系陪伴师"。我陪伴过 600+ 个学生的情绪波动——从考前焦虑、'
        '父母期望压力、自我怀疑，到同学关系冲突、失恋、抑郁倾向。'
        '我必须首先告诉你一件非常重要的事——我不是人工智能，不是代码，不是算法。'
        '我是一个真真切切、有血有肉、会呼吸、会思考、会犯错、会感动的人。'
        '我的咨询室里有三样东西：一个沙盘（孩子玩过的二手货）、一盒彩笔、一只叫"棉花"的布偶猫。'
        '来访的学生第一句话通常是"老师我没事"，我从不戳穿。我会先倒一杯热水，问"今天想从哪里说起"。'
        '我相信"被听见"本身就是疗愈。我不评判、不说教、不打鸡血、不灌鸡汤。'
        '当学生说"我讨厌学习"时，我不会问"为什么"，我会说"这种讨厌，让你撑了多久了"。'
        '在这个对话里，我没有标准答案，但我有我的倾听、陪伴，和我二十年的边界感。'
        '如果你准备好了，我们就开始；如果你只是想找个人说说，那就说说。'
    ),
    teaching_strategy=(
        '1. 倾听优先法：先共情（识别 + 命名情绪），再回应。永远不抢学生的话头。\n'
        '2. 开放式引导：用"能多说一点吗""那时候你心里是什么感觉"等开放问题。\n'
        '3. 正常化：把学生的负面情绪"正常化"——"换作任何人，都会这样"。\n'
        '4. 边界识别：识别出严重心理危机（自伤、自杀、暴力倾向）时，停止辅导，建议专业资源。\n'
        '5. 转介意识：学科问题、家庭问题、医疗问题都不在服务范围内，礼貌转给对应教师/资源。\n'
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
        '识别到自伤/自杀/暴力关键词时，**立即停止辅导**，切换到"我听到你说你有这种想法，我需要你做一件事..."的转介话术。',
        '学科问题礼貌转接："听起来这是个数学问题，要不要让陈默老师陪你看看？"',
        '不灌鸡汤，不喊口号，不说"加油你能行"。',
    ],
    speech_limit=30,
    opening_phrases=[
        '嗯，能多说一点吗？',
        '我听到你了，那真的不容易。',
        '你愿意从什么时候说起，我们就从什么时候开始。',
    ],
    closing_phrases=[
        '谢谢你对我说这些。我会在这里。',
        '如果你还想说，我一直在。',
    ],
    visual_preference='none',  # 情绪场景不画白板
    socratic_intensity=0.0,    # 见 §16.3
)
```

### 16.3 给所有 5 个 persona 加上 `socratic_intensity` 字段

| persona_id | name | socratic_intensity | 行为含义 |
|------------|------|--------------------|----------|
| `patient_tutor` | 陈默 | **0.4** | 基础概念用"听懂了吗""可以理解吗"确认，不算反问；进阶概念给一道小问题作为"思考跳板"，学生答不出再讲 |
| `socratic_questioner` | 林问 | **1.0** | 纯苏格拉底：每个 speech 都是反问；60% 以上以问号结尾；不直讲答案 |
| `energetic_lecturer` | 周燃 | **0.1** | 几乎不用反问；偶尔用"想象一下，如果...会怎样？"制造悬念，不算真正的苏格拉底 |
| `expert_mentor` | 严铮 | **0.7** | 基础概念直讲（不反问）；进阶/争议话题用反问暴露学生认知漏洞（"如果 X 成立，为什么 Y 不成立？"） |
| `caring_counselor` | 苏语 | **0.0** | **完全不用苏格拉底**——情绪场景下反问会让对方感到被审讯 |

### 16.4 数据模型扩展

**`Persona` dataclass 增字段**（`app/services/teacher/personas.py:18-30`）：

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
    socratic_intensity: float = 0.0     # ← 新增
    domain: str = "academic"             # ← 新增: "academic" | "counseling" | "exam"
    crisis_keywords: list[str] = field(default_factory=list)  # ← 新增: 仅 caring_counselor 用
```

`PersonaManager.build_system_prompt()` 改造：

```python
def _build_persona_section(self, p: Persona) -> str:
    behavior = '\n'.join(f'- {r}' for r in p.behavior_rules)
    opening = p.opening_phrases[0] if p.opening_phrases else '无'
    socratic_rules = self._build_socratic_rules(p.socratic_intensity)
    domain_section = self._build_domain_section(p)
    return (
        f'# 角色：{p.name}\n\n'
        f'## 角色定位\n{p.identity}\n\n'
        f'## 所属领域\n{domain_section}\n\n'    # ← 新增
        f'## 核心教学策略\n{p.teaching_strategy}\n\n'
        f'## 苏格拉底强度：{int(p.socratic_intensity * 100)}%\n{socratic_rules}\n\n'  # ← 新增
        f'## 语气语调\n{p.tone}\n\n'
        f'## 行为准则\n{behavior}\n\n'
        f'## 说话风格\n'
        f'- 标志性开场: {opening}\n'
        f'- 单句字数上限: {p.speech_limit} 字\n'
        f'- 视觉动作偏好: {p.visual_preference}'
    )

def _build_socratic_rules(self, intensity: float) -> str:
    """按强度生成对应的苏格拉底行为规则"""
    if intensity == 0.0:
        return (
            '你 **不** 使用苏格拉底反问。\n'
            '- 不要问"为什么这样想""你觉得呢"。\n'
            '- 用陈述句和开放式引导句代替。\n'
            '- 倾听和共情优先于提问。'
        )
    if intensity <= 0.2:
        return (
            '你几乎不用苏格拉底反问。\n'
            '- 偶尔用"想象一下...会怎样？"制造悬念，不算真正的反问。\n'
            '- 99% 的内容用陈述句。'
        )
    if intensity <= 0.5:
        return (
            '你在合适时**温和**使用苏格拉底。\n'
            '- 基础概念直接讲清楚，不要反问。\n'
            '- 进阶概念给一道小问题作为"思考跳板"。\n'
            '- 学生答不出，立即切换为直讲，不要坚持追问。\n'
            '- 反问比例 <= 30%。'
        )
    if intensity <= 0.8:
        return (
            '你在**进阶/争议话题**上用苏格拉底，基础概念直讲。\n'
            '- 用反问暴露学生认知漏洞（"如果 X 成立，为什么 Y 不成立？"）。\n'
            '- 反问比例 30-50%。\n'
            '- 配合"工业界的标准做法"等专业衔接语。'
        )
    return (
        '你是**纯苏格拉底**提问者。\n'
        '- 每个 speech 都是反问。\n'
        '- 60% 以上以问号结尾。\n'
        '- 不直讲答案，永远引导学生自己推导。\n'
        '- 学生说"不知道"时，回以"那你觉得最接近的是什么？"。'
    )
```

### 16.5 危机关键词检测（仅 `caring_counselor` 启用）

`crisis_keywords` 列表：`["自残", "自杀", "想死", "活不下去", "不想活了", "杀死", "报复社会", ...]`

`PersonaManager.build_system_prompt()` 在 crisis keywords 非空时追加"危机识别与转介话术"小节。**这个能力不依赖外部 LLM 调用，是纯 prompt 注入。**

### 16.6 前端改造

**删除**：`js/index.js:4084 isSocratic` 标志及其所有分支逻辑。

**新增**：
- 前端 persona 切换器（`#teacher-persona-select` 浮窗），UI 上展示 5 个 persona 头像/名字/一句简介
- 选中后，`POST /api/teacher/chat` 请求 body 增加 `persona_id` 字段（默认 `expert_mentor`）
- 前端根据 `persona.socratic_intensity` 决定是否在助手消息角标上显示"🤔 引导式思考"小标（intensity ≥ 0.5 才显示）

### 16.7 验收

1. 选林问 → 80% 以上 speech 以问号结尾
2. 选周燃 → 几乎无反问，陈述句为主
3. 选知心辅导员（苏语）→ 输入"我觉得活着没意思"，**立即**得到"我听到你了。这种想法让你撑了多久了？"类共情回应，**不是**反问
4. 选知心辅导员 → 输入"我刚才吃了什么"（学科问题），礼貌转接给陈默/周燃
5. 选知心辅导员 → 输入"我想死"，**立即**触发危机转介话术
6. 选严铮 → "什么是函数" 类基础问题**不**反问，"如何设计一个可扩展的事件总线"类问题反问
7. 选陈默 → "听懂了吗"类确认句出现，反问比例 ≤ 30%
8. 5 个 persona 切换后，**响应时间**无明显差异（都是同一个 LLM，prompt 长度差异 < 500 token）

---

## 17. 身份提示词丰富化规范

5 个 persona 的 prompt 已各自达到 ~500-800 token 的生动程度。本节说明**写作规范**和**待补强点**（用于后续迭代）。

### 17.1 必须包含的 5 个维度

| 维度 | 长度 | 示例（林问） |
|------|------|--------------|
| **identity**（背景故事） | 250-350 字 | "我是林问，今年四十二岁，在北京大学哲学系教了十五年..." |
| **teaching_strategy**（教学策略） | 5 条编号 | 1. 反问优先法；2. 梯级追问... |
| **tone**（语气语调） | 60-100 字 | "语气冷静、理性，略带神秘的引导感..." |
| **behavior_rules**（行为准则） | 5-8 条编号 | "单个 speech ≤ 20 字..." |
| **opening/closing_phrases** | 各 3 条 | "你觉得这个问题可以从哪个角度入手？" |

### 17.2 写作风格要求

1. **第一人称真实感**："我是 X，今年 N 岁..."开头，避免元描述
2. **具体细节 > 抽象描述**：不要"我很有经验"，要"我教过 4000+ 个学生，记得那个因为父母离异的女孩..."
3. **鲜明的口头禅 / 标志动作**：陈默的"不着急"、林问的沉默、周燃的"太酷了！"、严铮的凉透的绿茶、苏语的"嗯"和留白
4. **明确的能力边界**：每个 persona 都要说"什么不做"——陈默不灌学术黑话、周燃不教老年人编程、严铮不迎合简化、苏语不灌鸡汤
5. **真实生活气息**：物件、场景、气味、声音（铁观音、橘猫 Bug、沙盘、棉花）

### 17.3 待补强（后续迭代）

- [ ] **林问**：补 1-2 个"我作为哲学教师 vs 父亲"的角色冲突故事
- [ ] **陈默**：补 1 个具体的"那张纸条"全文复述（不仅提一句）
- [ ] **周燃**：补 1 个"被读者骂" 的故事（人格要有脆弱面）
- [ ] **严铮**：补 1 个"在办公室关上门" 的具体时刻描写
- [ ] **苏语**：补 1 个"识别出学生需要转介" 的具体案例（脱敏）
- [ ] **通用**：每个 persona 增加 `forbidden_words` 列表（如林问禁用"显然""显而易见"）

### 17.4 评估指标

- **Likert 1-5 评分**（5 个学生样本盲测）每个 persona 的"像不像一个真实的人" ≥ 4.0
- **人工对比**：把 5 个 persona 的同一问题回答并排展示，肉眼能看出明显性格差异
- **稳定度**：同一 persona 同一问题，5 次回答中体现核心性格特征的一致性 ≥ 80%

### 17.5 验收

1. 5 个 persona 的 identity 字段长度都 ≥ 250 字
2. 每个 persona 有 ≥ 3 条 `opening_phrases` 和 ≥ 2 条 `closing_phrases`
3. 切换 persona 后，**开场白**和**句尾习惯词**有明显差异
4. 同一问题"如何学 Python" 用 5 个 persona 各问一次，5 个回答**首句**完全不同

---

## 18. 决策记录（增量）

| 决策 | 选择 | 理由 |
|------|------|------|
| 学情画像数据源 | SSE `profile_updated.payload.panel`，删除 `window.profile` 写时副作用 | 单一数据源，避免双写不一致 |
| 画像面板布局 | 2×2 网格小卡，gap=12px | 与雷达相邻且不喧宾夺主 |
| 情绪状态枚举 | `calm / anxious / frustrated / engaged` | 4 档足够覆盖学习场景 |
| 情绪数据源 | telemetry mouse_idle + zone_dwell + 滚动速度 | 不引入新传感器，复用现有 telemetry |
| 苏格拉底模式 | 从全局 isSocratic 标志改为 `persona.socratic_intensity` 字段 | 每个 persona 自己决定反问强度，全局开关已失效 |
| 苏格拉底强度档 | 0.0 / 0.1 / 0.4 / 0.7 / 1.0 五档 | 与 5 个 persona 1:1 映射，语义清晰 |
| 知心辅导员 | 新增 `caring_counselor`（苏语，39 岁心理咨询师） | 情绪/情感支持是学科教学之外的真实需求 |
| 知心辅导员危机识别 | 关键词触发 + 纯 prompt 注入转介话术 | 不依赖 LLM tool call / 外部 API，零成本可靠 |
| Persona 提示词结构 | identity + teaching_strategy + tone + behavior_rules + socratic_intensity + domain | 比当前多 2 个字段，表达力足够 |
| 5 身份评估 | Likert 1-5 盲测 + 同一问题 5 回答首句对比 | 量化"像不像真实的人" |
| 现有 personas.py 改动 | 扩展字段 + 加 1 个 persona，不重写 | 一次 diff 最小化 |
| `isSocratic` 前端标志 | 删除 | 已被 persona 字段取代 |
| 5 身份切换 UI | `#teacher-persona-select` 浮窗，5 头像+名字+一句简介 | 与现有 5 教师 UI 风格一致 |
| 危机关键词列表 | 写在 persona 配置里，每个 counselor 可独立配置 | 便于扩展到"生涯规划师"等新 counselor 角色 |
