# 小星 AI 助手统一化设计

最后更新：2026-07-10

## 背景

项目小星 AI 助手由两套并行的子系统组成，存在数据源、AI 模型、决策逻辑三方面的割裂：

1. **数据源割裂**：`app/api/mascot.py` 和 `proactive_tutor.py` 都直接 `from db import get_db`，绕过项目统一的 Repository 抽象层。期间 11 个里程碑（M0-M11）完成的部分迁移未覆盖小星模块。
2. **AI 模型**：`mascot.py` 使用 `call_llm_stream_with_log_messages`（基于 `settings.minimax_api_key` + `settings.minimax_model_name`），模型调用是统一的，但决策逻辑不是。
3. **决策逻辑割裂**：`proactive_tutor.py` 仅有 3 类事件 + 硬编码模板；`mascot.py._get_proactive_actions()` 仅有 4 条关键词规则。两者都没接入 `app/services/tutor_engine/` 下已实现但未集成的子系统（25+ ProactiveAdvisor 规则、6 维能力画像、SM2 遗忘曲线、ActionLedger 防重放）。
4. **能力画像缺失**：`learning_path.py` 定义了 6 维能力（knowledge_base / code_skill / cognitive_style / focus_level / learning_goals / weakness），但小星模块从未读取，导致无法基于用户学习进度与能力做主动推送。

## 目标

- 小星 API 与 SSE 流的数据访问全部走 Repository 抽象层（与 M0-M11 切片一致）
- 决策逻辑接入 `tutor_engine` 子系统，复用 25+ 规则、6 维画像、SM2、ActionLedger
- 不删除 `proactive_tutor.py`（独立 SSE 流用户已上线），改为并存架构
- 渐进式迁移：复用 `READ_BACKEND_PERCENTAGE` 灰度开关

## 非目标

- 不重写 LLM 调用层（`llm_stream.py` 已经是项目统一入口）
- 不删除 `db.py`（M11 收尾切片负责）
- 不重做前端 UI 组件（仅同步数据契约变化）

## 架构总览

```
┌──────────────────────────────────────────────────────────────┐
│                    Frontend (js/mascot-*.js)                 │
└──────────────┬───────────────────────────────┬───────────────┘
               │ /api/mascot/* (HTTP+SSE)      │ /api/proactive/stream (SSE)
               ▼                               ▼
┌──────────────────────────┐    ┌──────────────────────────────┐
│  app/api/mascot.py       │    │  proactive_tutor.py          │
│  (重构)                  │    │  (保留, 仅改数据源)          │
│                          │    │                              │
│  - /api/mascot/chat      │    │  - login greeting            │
│  - /api/mascot/profile   │    │  - struggle alert            │
│  - /api/mascot/stats     │    │  - review reminder           │
│  - /api/mascot/capability│    │                              │
│      (新增)              │    │                              │
└────────┬─────────────────┘    └──────────┬───────────────────┘
         │                                │
         ▼                                ▼
┌──────────────────────────┐    ┌──────────────────────────────┐
│  app/services/           │    │  Repository 抽象层 (新接入)  │
│  tutor_engine/           │    │  - LearningRepository        │
│  - engine.decide()       │    │  - KnowledgeRepository       │
│  - context_aggregator    │    │  - CourseProgressRepository  │
│  - proactive_advisor     │    │  - PreferencesRepository     │
│  - hallucination_guard   │    └──────────┬───────────────────┘
│  - action_ledger         │               │
│  - models (6-dim)        │               │
└────────┬─────────────────┘               │
         │                                │
         ▼                                ▼
┌──────────────────────────────────────────────────────────────┐
│  app/repositories/                                          │
│    - orm/  (SQLAlchemy, xingshi_v2.db)                       │
│    - legacy/ (db.py wrapper, xingshi.db)                    │
│    - dual_write.py 装饰器 (主 ORM + 影子 legacy)            │
│    - base.py Protocols (8 个)                                │
└──────────────────────────────────────────────────────────────┘
```

**关键决策**：
- **双轨并存**：mascot API → ORM 主库（新迁移）；独立 SSE → legacy 主库（保留）。M11 收尾时统一切到 ORM。
- **共享决策引擎**：两轨都消费 `tutor_engine` 产出的 `ResponseEnvelope`（含 ActionType、priority、payload），但推送通道独立。

## 组件与职责

### 新增/扩展组件

| 组件 | 文件 | 职责 |
|------|------|------|
| `SqlAlchemyCapabilityRepository` | `app/repositories/orm/capability.py` (新) | 6 维能力画像读写（基于 learning_records + learning_goals 聚合） |
| `DbPyCapabilityRepository` | `app/repositories/legacy/capability.py` (新) | legacy 版本 |
| `CapabilityAggregator` | `app/services/tutor_engine/capability_aggregator.py` (新) | 把 6 维原始数据规整为 `CapabilityProfile` 数据类（已有 `models.py` 雏形） |
| `MascotEngineAdapter` | `app/services/tutor_engine/mascot_adapter.py` (新) | 包装 `TutorDecisionEngine.decide()`，对接 mascot.py 的 streamChat 调用 |
| `BaseRepository` (扩展) | `app/repositories/base.py` | 新增 `CapabilityRepository` Protocol |

### 修改组件

| 组件 | 改动 |
|------|------|
| `app/api/mascot.py` | 删除 4 处 `from db import get_db`；新增 `/api/mascot/capability/{user_id}`；`_get_proactive_actions()` 改用 `MascotEngineAdapter.decide()`；streamChat 改用 engine 的 `decide()` 返回的 `ResponseEnvelope` |
| `proactive_tutor.py` | 删除第 322 行 `from db import get_db`；改用 `get_repository_for_user(user_id, kind="learning")`；保留 SSE 协议不变 |
| `app/services/tutor_engine/context_aggregator.py` | 完成 2 个 TODO stub（`_fetch_goals()` / `_fetch_capability()`）；新增 `_fetch_capability_from_repo()` 走 Repository |
| `app/services/tutor_engine/proactive_advisor.py` | 不动（25+ 规则已完整） |
| `app/services/tutor_engine/action_ledger.py` | 不动（独立实例策略已就绪） |
| `app/repositories/dual_write.py` | 不动（已支持任意 Repository） |
| `js/mascot-services.js` | 新增 `fetchCapability(userId)` 调用 `/api/mascot/capability/{user_id}`；streamChat 解析新增的 `proactive_action` SSE 事件 |
| `js/mascot-core.js` | 不动 |

## 数据流

### 流 1：用户提问 → 小星回复（含主动推送）

```
前端 streamChat(question)
  → POST /api/mascot/chat {user_id, question}
  → mascot.py 解析 user_id, 调 MascotEngineAdapter.decide(user_id, question)
  → engine.decide() 内部:
      1. context_aggregator._fetch_*() 8 路并行 (走 Repository)
      2. capability_aggregator.aggregate() → CapabilityProfile
      3. proactive_advisor.evaluate() → [Action] 列表 (基于 6 维 + SM2 + Deadlines)
      4. action_ledger.filter() 去除 7 天内已推送
      5. pipeline_gate.process() L0→L1→L2→L3 (含 hallucination_guard)
      6. 返回 ResponseEnvelope {text, actions[], capability_delta}
  → mascot.py 把 ResponseEnvelope 序列化为 SSE 事件:
      - "delta" 事件: 流式文本片段
      - "proactive_action" 事件 (新): {type, priority, payload}
      - "done" 事件: {used_tokens, capability_snapshot}
  → 前端 mascot-services.js 解析事件，更新 UI + 触发 ActionType 对应的 toast
```

### 流 2：登录问候（SSE 独立流）

```
用户登录
  → main.py 触发 /api/proactive/stream (SSE)
  → proactive_tutor.py ProactiveTutor 启动
  → 数据从 get_repository_for_user(user_id, kind="learning").get_overview() 读
  → 模板渲染 (login greeting / struggle alert / review reminder)
  → SSE 推送 3 类硬编码事件
  → 7 天内同类型事件由 proactive_tutor 自己的 ActionLedger 抑制 (与 mascot 实例独立)
```

**流 2 决策**：不接入 engine（避免 25+ 规则冲击登录问候），仅改数据源。`proactive_tutor.py` 保留 3 类事件，独立 ActionLedger 独立计数。

### 流 3：能力画像查询

```
前端 fetchCapability(userId) (新)
  → GET /api/mascot/capability/{user_id}
  → mascot.py 调 capability_aggregator.aggregate(user_id)
  → capability_aggregator 走 CapabilityRepository 读 6 维
  → 返回 {knowledge_base, code_skill, cognitive_style, focus_level, learning_goals, weakness}
  → 前端 mascot-core.js 在 idle 检测时调用，结果用于调整 LLM 系统 prompt
```

## API 契约变更

### 新增端点

#### `GET /api/mascot/capability/{user_id}`

**请求**：
- Path: `user_id` (str)
- Headers: `Authorization: Bearer <jwt>`

**响应 200**：
```json
{
  "user_id": "u_123",
  "knowledge_base": {"math": 0.72, "physics": 0.45, "history": 0.61},
  "code_skill": {"python": 0.55, "javascript": 0.30},
  "cognitive_style": {"preferred_modality": "visual", "depth": "deep"},
  "focus_level": {"avg_session_minutes": 35, "streak_days": 7},
  "learning_goals": [{"id": 1, "title": "高考数学", "progress": 0.42}],
  "weakness": [{"subject": "physics", "topic": "kinematics", "mastery": 0.30}],
  "computed_at": "2026-07-10T08:30:00Z"
}
```

**错误**：
- 401: 未认证
- 404: 用户不存在
- 503: 能力聚合失败（fallback 到空画像）

### 修改端点

#### `POST /api/mascot/chat` (SSE)

**变更**：
- 旧：返回 `delta` + `done` 事件
- 新：返回 `delta` + `proactive_action` (新) + `done` (扩展)

**新增 SSE 事件 `proactive_action`**：
```json
{
  "type": "review_due",
  "priority": "high",
  "payload": {
    "subject": "math",
    "topic": "quadratic_equations",
    "due_at": "2026-07-10T12:00:00Z",
    "sm2_interval_days": 3
  },
  "ttl_seconds": 86400
}
```

**ActionType 枚举（25+ 个）**：
- `review_due` (SM2 触发)
- `goal_deadline_near` (7 天内到期)
- `streak_at_risk` (连续学习保护)
- `weakness_drill_suggest` (掌握度 < 0.4)
- `course_resume` (学习路径中断)
- `...` 其余 20+ 规则

**前端兼容性**：旧客户端忽略未知事件名 `proactive_action` 即可，不破坏现有功能。

### 保持不变

- `GET /api/mascot/profile/{user_id}`
- `GET /api/mascot/stats/{user_id}`
- `POST /api/mascot/checkin`
- `GET /api/proactive/stream` (SSE, 3 类事件保留)

## 错误处理

### 7 类错误与降级策略

| 错误类型 | 触发条件 | 降级行为 |
|----------|----------|----------|
| `repository_unavailable` | ORM + legacy DB 都不可用 | 返回 503，前端降级到静态问候 |
| `capability_aggregation_failed` | 6 维任一维度查询失败 | 返回空画像，engine 跳过依赖画像的规则 |
| `llm_timeout` | engine.decide() 超过 30s | 调用 `fallback_simple_chat()` (mascot.py 保留原 LLM 调用路径) |
| `action_ledger_unavailable` | 内存字典损坏 | 跳过去重，可能重复推送 (低优先级) |
| `sse_write_failed` | 客户端断连 | 优雅关闭，ActionLedger 不记录 |
| `context_fetch_partial` | 8 路 context 1-2 路失败 | 降级到 6 路 context，engine 标记 degraded=true |
| `hallucination_guard_rejected` | LLM 输出含超纲内容 | 重试 1 次，失败则 fallback_simple_chat |

### 降级代码骨架

```python
# app/api/mascot.py
async def stream_chat(user_id, question):
    try:
        envelope = await MascotEngineAdapter.decide(user_id, question)
    except (RepositoryError, LLMTimeout) as e:
        logger.warning("engine.decide failed, fallback", extra={"user_id": user_id, "err": str(e)})
        envelope = await fallback_simple_chat(user_id, question)
    
    async for event in envelope.stream_events():
        yield event
```

### 监控

- `audit_log` 表新增 `mascot_engine_decide` 事件类型，记录 (user_id, duration_ms, used_repository, fallback_used, action_count)
- 错误率阈值：`<0.1%` 触发告警
- P95 latency: `<2s`

## 测试策略

### 单元测试 (≥30 个)

| 模块 | 测试数 | 覆盖点 |
|------|--------|--------|
| `CapabilityRepository` (orm + legacy) | 8 | CRUD 各 2 + 错误路径 + 边界 |
| `CapabilityAggregator` | 6 | 6 维各 1 + 空数据 |
| `MascotEngineAdapter` | 4 | 成功 / 降级 / 超时 / repository 失败 |
| `mascot.py` 路由 | 8 | 4 端点 × 2 (正常 + 错误) |
| `proactive_tutor.py` 改 Repository | 4 | login / struggle / review / error |

### 集成测试 (≥15 个)

- `test_engine_to_mascot_e2e.py` (5): 真实 ORM + 真实 LLM (mock)，验证 25+ 规则至少 1 个触发
- `test_capability_to_proactive.py` (5): 验证 SM2 到期 → proactive_action 事件
- `test_dual_write_consistency.py` (5): ORM 写入后 legacy 是否同步

### 契约测试 (≥8 个)

- `test_mascot_capability_contract.py` (4): GET /api/mascot/capability 4 个用例
- `test_mascot_chat_sse_contract.py` (4): SSE 事件 schema 验证（含 proactive_action）

### 回归测试

- `test_existing_mascot_smoke.py`: 保留原 mascot.py 的 4 端点 smoke 测试，确保不破坏登录用户
- `test_proactive_tutor_independence.py`: 验证 proactive_tutor 与 mascot 的 ActionLedger 互不影响

## 迁移切片与时间表

### 切片 #11：小星数据源统一化 (4 工作日)

**Day 1**: 创建 `CapabilityRepository` (orm + legacy) + Protocol
**Day 2**: 创建 `CapabilityAggregator` + 单测 (8 个)
**Day 3**: 修改 `proactive_tutor.py` 第 322 行 + `context_aggregator.py` 2 TODO stub
**Day 4**: 删除 `mascot.py` 4 处 `from db import get_db` + 集成测试

**完成标志**：
- `from db import` 在 mascot/ + proactive_tutor 出现次数 = 0
- dual_write 测试 100% 通过
- Repository 单测 100% 通过

### 切片 #12：小星决策引擎集成 (6 工作日)

**Day 5**: 创建 `MascotEngineAdapter` + 单元测试 (4 个)
**Day 6**: 重构 `mascot.py.stream_chat` 走 engine.decide()，保留 `fallback_simple_chat`
**Day 7**: 新增 `GET /api/mascot/capability/{user_id}` 端点
**Day 8**: SSE 协议扩展（新增 `proactive_action` 事件）
**Day 9**: 前端 `mascot-services.js` 同步（fetchCapability + 事件解析）
**Day 10**: 灰度切读 + 监控 + 文档

**完成标志**：
- 6 维画像在 mascot /proactive 中至少 1 处使用
- 25+ ProactiveAdvisor 规则至少 5 个在测试中触发
- ActionLedger 实例独立 (2 个)
- 灰度：1% → 10% → 50% → 100% (各 ≥24h 监控)

**总计 10 工作日**

## 灰度与回滚

### 灰度切读（使用项目原有 feature flag）

```bash
# 1% 切读
READ_BACKEND_PERCENTAGE=1 DUAL_WRITE_LEGACY=true

# 10% 切读
READ_BACKEND_PERCENTAGE=10 DUAL_WRITE_LEGACY=true

# 50% 切读
READ_BACKEND_PERCENTAGE=50 DUAL_WRITE_LEGACY=true

# 100% 切读
READ_BACKEND_PERCENTAGE=100 DUAL_WRITE_LEGACY=true
```

每档运行 ≥24h 观察：错误率 `<0.1%`，双写差异数 `=0`，P95 latency `<2s`。

### 回滚预案

```bash
# 立即回滚
READ_BACKEND_PERCENTAGE=0
DUAL_WRITE_LEGACY=true
# mascot 与 proactive_tutor 都回退到 legacy DB + 原决策逻辑
```

## 已知遗留问题

1. **action_ledger 持久化**：当前是内存字典，进程重启后重置。生产环境需迁移到 Redis（不在本设计范围）。
2. **6 维画像数据稀疏**：新用户 learning_records 为空时返回空画像，proactive_advisor 会自动跳过依赖画像的规则。
3. **LLM 成本**：engine.decide() 8 路 context 聚合会增加 token 消耗（每次约 500-1500 token），监控成本曲线。
4. **前端 ActionType 覆盖**：25+ 规则中前端只实现 5 个 toast 模板（review_due / goal_deadline / streak / weakness / course_resume），其余 20+ 在前端静默丢弃（不显示但不报错）。

## 负责人

- 切片 #11: `<待填>`
- 切片 #12: `<待填>`

## 附录

### A. 与既有切片的关系

| 切片 | 状态 | 关系 |
|------|------|------|
| M0 基础设施 | 已完成 (2026-07-08) | 提供 Repository 协议 + DualWrite，本设计复用 |
| M1 认证 | 已完成 (2026-07-09) | user_id 来源已切到 ORM，本设计消费 |
| M2-M10 | 已完成 (2026-07-10) | 11 张表 ORM 化完成，本设计的 Repository 接入有底层 |
| M11 收尾 | 待启动 | 删除 db.py 前必须先完成切片 #11 + #12 |

### B. 关键文件清单

| 路径 | 行数 | 状态 |
|------|------|------|
| `app/api/mascot.py` | 683 | 修改 (4 处 from db + 路由重构) |
| `proactive_tutor.py` | 418 | 修改 (1 处 from db) |
| `app/services/tutor_engine/engine.py` | 137 | 不动 |
| `app/services/tutor_engine/proactive_advisor.py` | 286 | 不动 |
| `app/services/tutor_engine/context_aggregator.py` | 312 | 修改 (2 TODO stub) |
| `app/repositories/orm/capability.py` | 0 | 新建 (~120 行) |
| `app/repositories/legacy/capability.py` | 0 | 新建 (~120 行) |
| `app/services/tutor_engine/capability_aggregator.py` | 0 | 新建 (~180 行) |
| `app/services/tutor_engine/mascot_adapter.py` | 0 | 新建 (~80 行) |
| `js/mascot-services.js` | 511 | 修改 (新增 fetchCapability + 事件解析) |

### C. 设计决策记录

1. **不删除 proactive_tutor.py**：用户已上线独立 SSE 流，删除成本高；并存架构更安全。
2. **渐进迁移 vs 一次性重写**：选渐进（切片 #11 + #12），保留可回滚路径。
3. **ActionLedger 独立 vs 共享**：选独立。mascot 与 proactive_tutor 推送通道不同，共享会导致一方故障影响另一方。
4. **复用项目原有 feature flag**：READ_BACKEND_PERCENTAGE 已是灰度标准，避免新增 flag 增加运维负担。
5. **fallback_simple_chat 保留**：engine.decide() 失败时回退到原 mascot.py 的 LLM 调用路径，保证可用性。
6. **6 维画像完整集成**：knowledge_base / code_skill / cognitive_style / focus_level / learning_goals / weakness 全部接入 proactive_advisor（25+ 规则中至少 10 个依赖画像）。
