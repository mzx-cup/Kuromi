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
| 后端 agent 协作**无前端可视化** | `MasterController.execute(state, on_step_complete)` 回调存在但未接 SSE | 前端不知道发生了什么 |
| 雷达渲染含**硬编码 RGBA** | `js/index.js:3304-3442` 至少 6 处 `rgba(...)` 直接写死 | 违反 tokens.css 统一主题规则，主题切换时颜色断裂 |

### 1.2 设计目标

1. **新建"Agent 编排控制塔"** 替换/升级 `index.html#track-a` 教研沙盘：实时呈现 7+1 个 agent 的协作状态
2. **后端 agent 接入 SSE**：包装 `MasterController.execute()`，把 `on_step_complete` 回调事件以 Server-Sent Events 推到前端
3. **6 维知识雷达真实化**：从多源数据（agent 工作流日志、telemetry、`aggregate_profile`）实时聚合，SSE 推送后平滑过渡
4. **100% 颜色统一**：控制塔 + 雷达所有颜色走 `tokens.css` 变量，零硬编码
5. **降级兜底**：后端不可用时切换前端 mock，保证演示不卡

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

**真实化方案**：新增 `app/services/portrait_aggregator.py`（不要改现有的 `profile_aggregator.py`，它用于"AI 眼中的你"页面）：

```python
def aggregate_six_dim_portrait(
    state: StudentState,
    telemetry: dict | None = None,
    workflow_logs: list[AgentStepLog] | None = None,
) -> dict:
    """输出 6 维标准化数据 (0-100) 给雷达消费"""
    return {
        "knowledge_mastery": _calc_knowledge_score(state),       # 来自 knowledge_mastery[].score 平均
        "code_skill":        _calc_code_score(state),            # level + strong_areas 计数
        "cognitive_style":   _calc_style_score(state),           # type 映射 + confidence
        "learning_goal":     _calc_goal_progress(state),          # current_path 完成度
        "weakness":          _calc_weakness_score(state),         # areas 数量 + 频次
        "focus_level":       _calc_focus_score(state, telemetry),# 含 overload_score
        "last_synced":       datetime.utcnow().isoformat() + "Z"
    }
```

**6 维数据来源矩阵**：

| 维度 | 主信号源 | 辅助信号源 | 实时触发 |
|------|----------|------------|----------|
| knowledge_mastery | `state.profile.knowledge_mastery[]` | `workflow_logs` 中 quiz 正确率 | 流水线完成 / 单题作答 |
| code_skill | `state.profile.code_skill.level` | `state.profile.code_practice_time` | 流水线完成 |
| cognitive_style | `state.profile.cognitive_style.type + confidence` | `workflow_logs` 中 blind_spots | 流水线完成 |
| learning_goal | `state.current_path` 完成比例 | `planner_output` 节点状态 | 路径节点状态变更 |
| weakness | `state.profile.weakness.areas` | `profiler.metadata["blind_spots"]` | profiler 运行后 |
| focus_level | `profiler.metadata["overload_score"]` | `telemetry.scroll_metrics / zone_dwell_times` | telemetry 上报时 |

**触发更新链**：

```
任意 agent.run() 完成
  └─ state.add_workflow_log()
       └─ MasterController 回调 on_step_complete(log)
            └─ SSE 转发器
                 ├─ emit "agent_step" → 前端控制塔日志
                 └─ if log.agent_role == "画像分析" or "评估":
                       重新调用 aggregate_six_dim_portrait()
                       └─ emit "profile_updated" → 前端雷达
                            └─ renderRadarChart(newValues) 平滑过渡
```

**Telemetry 上报通道**（新增 `app/api/telemetry.py`）：
- 前端 `js/telemetry-collector.js` 采集滚动/停留/鼠标 → `POST /api/telemetry` 每 10s 批量
- 后端写入 `state.telemetry_data`（in-memory），下次 `ProfilerAgent._analyze_telemetry` 时使用
- 这是雷达"focus_level"维度的实时数据源

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
| `profile_updated` | `{trace_id, portrait: {6 维分数}}` | profiler 或 evaluator 完成后 |
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
| `html/index.html` | header 文案 + 按钮组 + 资源抽屉 + 雷达位置 |
| `js/index.js` | `renderFlowNodes` / `renderSandboxLog` 数据源切换；新增 `startPipeline`；`renderRadarChart` 重构（去硬编码 + 加动画） |
| `css/tokens.css` | 追加 `--agent-*` `--code-bg` `--radar-*` 等变量 |
| `main.py` | `app.include_router(agent_orchestration.router, prefix="/api/agents")` |
| `RUNNING_GUIDE.md` | 增加"启动 Agent 控制塔"步骤 |

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
