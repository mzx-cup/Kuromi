---
title: S1–S6 缺口收口 + S7→S12 推进方案 (P1 闭环)
date: 2026-07-16
status: 待 review
author: Brainstorming 会话
project: 星识 Star-Learn
supersedes:
  - 无
related:
  - docs/superpowers/specs/2026-07-13-llm-4-painpoints-kb-design.md
  - docs/superpowers/plans/2026-07-13-llm-4-painpoints-kb.md
risk_level: 高
target_release: P1 (8 周)
langchain_version: 0.3.x (锁定)
qdrant: 主从部署
redis: 单机
testing_runtime: docker-compose.dev.yml
---

# S1–S6 缺口收口 + S7→S12 推进方案

> Spec 范围：**先补 S1–S6 的 4 个真实缺口，再按 critical path 推进 S7→S12**。单 spec 串 10 个切片；不改原 spec 的设计原则、acceptance、ADR。

## 1. 背景与目标

`docs/superpowers/specs/2026-07-13-llm-4-painpoints-kb-design.md` (下称 "原 spec") 把 P1 切成 S0–S12 共 13 片。2026-07-15 复审发现：

- 8 片代码 + 测试已 OK
- 4 个 S1–S6 的真实缺口未补完
- S8–S12 仍未启动

本 spec 把"P1 闭环"拆成两个阶段、10 个有序切片，目标：让 P1 的 Day-1 验收（A1–A15）全部通过，或在 S1–S6 缺口上做出明确的工程妥协并记录在案。

## 2. 范围与非范围

### 在范围内

- A 阶段 4 切片（A1–A4）：S1–S6 缺口收口
- B 阶段 6 切片（B1–B6）：spec critical path 推进 S7→S12

### 不在范围内（沿用原 spec §10 YAGNI）

- 不重写 agents.py / 不重写 context_aggregator / 不重写 llm_stream.py
- 不引入新的 LLM 框架 / 不引入 Pinecone / 不重写 supervisor
- 不改 LangChain 锁版本（仍 0.3.x）
- PDF / B 站自动解析、教师批注、学生端图谱可视化（仍是 P2）

## 3. 架构

### 3.1 总体结构

**不动**原 spec 的 5 层 + 3 大创新拓扑。本 spec 仅：

- 把 agents.py 上的 LangChain 接入点缩到 1 个单点（feature flag）
- 把 S1–S6 缺口分成 4 个 PR-PR 大小
- 把 S7+ 严格顺序串到一个回归测试链

### 3.2 Phase A（4 切片：A1–A4）

| 切片 | 修的缺口 | 工作量 | 文件改动 |
|---|---|---|---|
| **A1** S3 引用位置校验 | [citation.py:36](app/services/llm/citation.py#L36) `has_citation` 现在只看 marker 在 claim 字符串里，**G 类（cite A 配 claim B）实际上没拦住** | 1d | 新建 `app/services/llm/citation_position.py` (30 行)；改 `citation.py`；扩 `tests/redteam/prompts.yaml` G 类 12→25 |
| **A2** S2 接通 SocraticAgent | `agents.py` 中 grep "XunfeiChatModel\|MemoryCardLoader" 0 命中 | 1.5d | `agents.py:handle_user_message` 顶部加 5 行 env-flag 分流；新文件 0；测试文件 1 |
| **A3** S5 `load()` 拆 stub | `app/services/agent/memory_card_loader.py:149` load() 返回空卡 | 2d | 新建 `app/services/agent/field_fetchers.py` (80 行) + `card_cache.py` (40 行)；改 loader.py |
| **A4** S6 `extract_pattern` 真接 LLM | `app/services/memory/llm_extractor.py:27` 是 stub 返回 `{confidence: 0.7}` | 1d | 改 `llm_extractor.py` (单文件)；`consolidator.py` 1 行参数 |

**Phase A 退出标准：**
- `git tag slice-A1` / `slice-A2` / `slice-A3` / `slice-A4` 都已落
- A1 红队 G 类 100/100
- A2 老路径 e2e 6/6 不回归 + 新路径 e2e 6/6 仍 100%
- A3 端到端 SocraticAgent 启动 P95 < 100ms（环境：本地 + 单 user）
- A4 consolidator 22/22 测试不回归 + 100 合成 episodic 跑出 ≥ 1 簇

### 3.3 Phase B（6 切片：B1–B6）

| 切片 | spec critical path | 工作量 | 关键改动 |
|---|---|---|---|
| **B1** S7 督导层 | `rule_engine.py:241` + `dsl.py:136` + `channel_dispatcher.py:107`；现在 6 测试失败 | 3-4d | fixture 缺 `supervision_rules` 表先修；补 ActionLedger.cooldown / EscalationChain / hourly cron + step2/3 调度 |
| **B2** S8 Drift 检测 | 全未启动；目录、模型、scheduler 都不存在 | 2-3d | 新建 `app/services/drift/` 4 文件 + `app/models/drift_report.py` + `scripts/drift_detector.py` + 04:00 cron |
| **B3** S9 SocraticAgent 端到端 | A3 的 loader + A2 的路径都不在 SocraticAgent 工作流里 | 3-4d | agents.py 加 2 行 import + 装饰器；100 条历史对话对照实验 |
| **B4** S10 ProfileAgent/EchoAgent | agents.py 中两 Agent 走老画像 / 主流程 | 2-3d | 新建 `profile_memory_card.py` + `echo_memory_card.py` |
| **B5** S11 研发层冷启动 | `.claude/settings.json` 只有 PreCompact hook | 2-3d | 加 SessionStart hook；新建 `app/services/claude_card/loader.py`；3KB markdown |
| **B6** S12 P1 端到端验证 | 全部未启动 | 3-4d | `scripts/chaos_drill.py` + `tests/parity/{langchain_parity.py,conversations.jsonl}` + 200 条红队扩 |

**Phase B 退出标准：原 spec §9 验收 A1–A15 全部通过（含 A5 SocraticAgent P99 < 3s、A6 对照实验 4/4、A7 chaos drill、A11 Drift 100% 扫描、A14 灰度切读）**

### 3.4 双轨接入点（A2 单点）

仅在 [agents.py](agents.py) `SocraticEvaluatorAgent.handle_user_message` 顶部加：

```python
async def handle_user_message(self, user_id, message, ...):
    if os.getenv("USE_LANGCHAIN_SOCRATIC", "0") == "1":
        return await produce_socratic_response(
            user_id=user_id, message=message,
            llm=self._llm, vector_store=self._vector_store,
            callback_handler=KBCallbackHandler(agent_id="socratic", user_id=user_id),
        )
    # ... 原有 legacy 代码
```

**老调用者完全不受影响**（env `=0` 默认）。这是 P1 推进期"老路径永远可回退"的核心单点。

### 3.5 测试环境升级

CI / PR 流程加 docker-compose 服务依赖：

```yaml
services:
  qdrant-master:
    image: qdrant/qdrant:v1.9.0
    ports: ["6333:6333"]
  qdrant-replica:
    image: qdrant/qdrant:v1.9.0
    ports: ["6334:6333"]
  redis:
    image: redis:7.2-alpine
    ports: ["6379:6379"]
```

集成测试 `tests/integration/test_*` 不再 SKIPPED（`test_qdrant_health.py:14` 现在能跑）。

## 4. 组件责任

### 4.1 A 阶段 4 组件

| ID | 文件路径 | 入接口 | 出接口 | 单一职责 |
|---|---|---|---|---|
| **A1** `CitationPositionChecker` | `app/services/llm/citation_position.py` (新建 30 行) | `claims: list[str]`, `citations: list[Citation]` | `(unbacked, mispositioned): tuple` | 校验每个 `[KB:id]` 标记在对应 claim ±80 字符窗内 |
| **A1** 改 `has_citation` | `app/services/llm/citation.py:36` | — | — | 字符串包含 → 改用 A1 的 checker |
| **A2** `produce_socratic_response`（已有）| `app/services/llm/socratic_response.py` | `user_id, message, llm, vector_store, callback_handler` | `ValidatedResponse` | **不变**，只是被 SocraticAgent 引入 |
| **A2** agents.py 5 行（不改 method body）| env `USE_LANGCHAIN_SOCRATIC` | `await legacy` | **不变** | feature-flag 分流，不影响老调用者 |
| **A3** `FieldFetchers` | `app/services/agent/field_fetchers.py` (新建 80 行) | `user_id, field_key` | `str` | 4 个 fetcher 各一方法；超 250ms 用 `fallback` 字段；总计 < 100ms |
| **A3** `CardCache` | `app/services/agent/card_cache.py` (新建 40 行) | `agent_id, user_id, ttl_s=300` | `LoadedCard \| None` | 字段级 TTL；key=`<agent_id>:<user_id>:<field_key>` |
| **A3** 拆 stub `MemoryCardLoader.load()` | `app/services/agent/memory_card_loader.py:149` | `agent_id, user_id` | `LoadedCard` | 串 4 fetcher → pack → cache.set |
| **A4** 改 `extract_pattern` | `app/services/memory/llm_extractor.py:27` | `user_id, cluster, llm: XunfeiChatModel` | `dict` | 真接 LLM + JSON 解析；parse 失败 → fallback；30s timeout |

### 4.2 B 阶段 6 组件

| ID | 新增 | 责任 |
|---|---|---|
| **B1** `app/services/supervision/escalation_chain.py`（新建）| ActionLedger.cooldown 收紧；EscalationChain 调度 step2/3；channel dispatcher 重试 3 次 |
| **B2** `app/services/drift/{detector,adr_parser,reporter,scheduler}.py`（新建） + `app/models/drift_report.py` + `scripts/drift_detector.py` | 检测 KB node 的 source file hash 变化、ADR frontmatter 变化、未引用 90d 节点 |
| **B3** agents.py 2 行 import + 装饰器 | SocraticAgent 启动 / 每次 turn 头注入 1 张 ≤ 500 token 卡 |
| **B4** `app/services/agent/{profile_memory_card,echo_memory_card}.py` | 2 个新 schema |
| **B5** `app/services/claude_card/loader.py` + `.claude/settings.json` SessionStart hook | 3KB markdown 注入 |
| **B6** `scripts/chaos_drill.py` + `tests/parity/{langchain_parity.py,conversations.jsonl}` | chaos + 对照实验脚本 |

### 4.3 不变性

- `agents.py` 在 A2 处加 5 行（feature flag 分流），B3 处加 2 行（import + 装饰），其余全不动
- A1/A2/A3/A4 各 PR **互不冲突**（改的文件不重叠）：A1→`citation*.py`；A2→`agents.py:5行+测试`；A3→`agent/*.py`；A4→`memory/llm_extractor.py+consolidator.py:1行`
- B 阶段切到 `agents.py` 的两个 PR 之间用 git tag + merge commit，避免叠合

## 5. 数据流

### 5.1 流 1：A1 — S3 引用位置校验

```
LLM 输出 raw_text
  ↓
extract_citations(text)  →  [(KB:id_3, pos_120), (KB:id_7, pos_280)]
extract_claims(text)      →  ["A 是 X...", "B 是 Y...", "C 是 Z..."]
  ↓
NEW CitationPositionChecker
  for each claim:
    window = claim_text[start-80 : end+80]
    covered = [c for c in citations if c.kb_node_id in window_or_origin]
    if covered_ratio < 0.6 (未引用)        → unbacked += 1
  ↓
risk = unbacked_ratio * 0.6 + invalid_ratio * 0.4
  ↓
unbacked → retry (max 1) → 仍缺 → block(unbacked_claims)
引用 ID 不在检索 valid_node_ids → block(invalid_citation_id, risk=1.0)
all back + valid → pass
```

**边界：** claim < 10 字符视为非 claim，跳过位置校验；窗口超出文本范围不补。

### 5.2 流 2：A3 + B3 — Agent 记忆卡加载

```
SocraticAgent.handle_user_message(user_id, msg)            (B3 装饰)
  ↓
card = MemoryCardLoader.load(agent_id="socratic", user_id=user_id)   (A3)
  ├─ CardCache.get(agent_id, user_id, ttl_s=300) → hit / miss
  └─ miss: parallel (4 fetchers, total ≤ 100ms)
      ├─ episodic_last    ← OrmEpisodicMemoryRepository.recent_unconsolidated(1)
      ├─ capability_recent ← WeaknessTimeline.recent(7d)
      ├─ semantic_top3     ← OrmSemanticMemoryRepository.top_by_confidence(3, status=active)
      └─ supervision_pending ← OrmSupervisionEventRepository.list_pending(user_id)
  └─ pack(4 fields, priority truncation, total ≤ 500 token)
system_prompt = base + "\n\n" + card.markdown
  ↓                                                            (A2)
if USE_LANGCHAIN_SOCRATIC: → produce_socratic_response(...)      (新)
else:                       → legacy code path                    (老)
```

**失败兜底：**
- 任一 fetcher 超时（> 250ms）→ 用 `fallback` 字段；其他字段继续
- 总 token 超 500 → 按 spec 优先级 `supervision_pending > semantic_top3 > capability_recent > episodic_last` 截断
- Cache 命中 → 跳过 4 fetcher
- 4 fetcher 全失败 → markdown 为空，**不阻断 turn**

### 5.3 流 3：B1 — 督导规则触发

```
每小时 cron (APScheduler)
  ↓
SupervisionRuleEngine.evaluate_all_rules()
  ├─ SELECT * FROM supervision_rules WHERE enabled=1 ORDER BY priority
  └─ for rule in rules:
        context = _build_context(user_id)
        ├─ L4 读: capability + sm2 + deadlines (WeaknessTimeline / DeadlineTracker)
        └─ L2 读: episodic_last_7d + semantic_active_count
        ↓
        safe_eval(rule.trigger_dsl, context)
        ├─ False → skip
        ├─ Exception → skip + log (若 24h 内 5 次 → P0 告警 + default disable)
        └─ True + cooldown OK
              ↓
              INSERT SupervisionEvent(status='pending', current_step=1)
              ChannelDispatcher.dispatch(step=1, channels=rule.step1.channels)
              ActionLedger.record_exposure(rule.id, user.id)
              scheduler.schedule_step(event.id, step=2, +24h)
              scheduler.schedule_step(event.id, step=3, +72h)

用户响应后:
  └─ UPDATE SupervisionEvent(response_status='stopped')
     scheduler.cancel_step(event.id, step=3)        ← step 3 永远不触发
```

### 5.4 流 4：B5 — Claude 冷启动记忆卡

```
Claude Code 启动会话
  ↓
SessionStart Hook (.claude/settings.json)
  ↓
python -m app.services.claude_card.loader --commit $(git rev-parse HEAD)
  ↓
Cache: project_state_v{commit_sha} (内存, TTL=1h)
  ├─ hit → return cached markdown
  └─ miss → parallel (5 类):
        ├─ SLICE_STATUS.md → grep 活跃切片
        ├─ docs/superpowers/specs/* ADR → 近 30 天 frontmatter
        ├─ git log --oneline -50
        ├─ SELECT DriftReport WHERE resolved=false      ← B2 输出
        └─ SELECT AgentBehaviorLog WHERE action_type='memory_consolidation' ORDER BY ts DESC LIMIT 5
  pack into markdown (max 3KB)
  ↓
stdout → Claude 上下文
```

## 6. 错误处理与降级（沿用原 spec §5 三策略）

### 6.1 三策略（不引入第 4 种）

- **fail-loud**：检索失败 / AntiHallucinationParser 报 invalid_citation_id → 异常向上传播
- **fail-closed**：督导 trigger 永远为真 → disable + P0 告警
- **fail-open**：AgentBehaviorLog 写失败 → DB→Redis→Disk 三层顺序

### 6.2 各组件失败矩阵

| 组件 | 失败 | 策略 | 兜底 |
|---|---|---|---|
| **A1** CitationPositionChecker | claim < 10 | skip（非 claim）| 不进 unbacked 计数 |
| **A1** | 检测超时 > 50ms | fail-open | 退回字符串包含；risk 标 `position_check_skipped=true` |
| **A2** produce_socratic_response | Retriever 抛异常 | fail-loud | 异常向上传播；HealthProbe 记 fail；L3 拒答 |
| **A2** | env `USE_LANGCHAIN_SOCRATIC` 未设置 | fail-safe 老路径 | 不动 |
| **A3** 字段 fetcher 超时 (> 250ms) | fail-open | 用 `fallback` 字段；其他继续；记 partial_fields 到 Log |
| **A3** CardCache 写失败 | fail-open | 跳过 cache；下次重拉 |
| **A3** 4 fetcher 全失败 | fail-closed (但 0 总 token) | card markdown 为空；不阻断 turn；记 WARN |
| **A4** LLM JSON 解析失败 | fail-open (per cluster) | 该簇 fallback；其他簇继续；`MemoryConsolidationJob.error_clusters.append(id)` |
| **A4** LLM 超时 (> 30s) | 同上 | 同上 |
| **B1** safe_eval 抛异常 | fail-closed | skip + log；同 rule 24h 内 5 次 → P0 + disable |
| **B1** ChannelDispatcher 通道失败 | retry 3 × exponential | 仍失败 → 写 `DispatchAttempt.error` |
| **B2** drift_detector 主流程异常 | fail-open | 当次 cron 标 failed；下周期重试 |
| **B3** `MemoryCardLoader.load()` 抛异常 | fail-open | 回落到空卡；启动不阻 |
| **B5** SessionStart Hook 超时 (> 1.5s) | fail-open | 截断 markdown；记 WARN；让 Claude 用空上下文开始 |
| **B5** Drift 全挂 / Qdrant 全挂 / Git 不可达 | fail-open (per item) | 渲染 `(no drift reports / qdrant unreachable / no recent ADRs)` 占位 |

### 6.3 HealthProbe 监控对象

| 监控项 | 当前阶段 | 阈值 |
|---|---|---|
| qdrant_health | 已存在 | 10s / 3 失败降 L3 |
| redis_health | B 阶段新增 | 10s / 3 失败降 L2 |
| claude_card_hook | B 阶段新增 | 超 1.5s 警告 |

### 6.4 不新增不可降级项（原 spec §5 清单不变）

- A / B 阶段的所有"失败"都被收敛到 fail-loud / fail-closed / fail-open 之一
- 不可降级项清单维持原 spec 6 条

## 7. 测试策略

### 7.1 测试金字塔

```
        红队 + chaos + parity  每周 / 每日
       ┌───────────────────────┐
       │  E2E + 集成 (docker)   │ PR + 每日
       │  ┌──────────────────┐  │
       │  │   契约 API/MCP    │  │ PR
       │  │ ┌──────────────┐ │  │
       │  │ │   单元 + 集成  │ │  │ 提交必跑
       │  │ └──────────────┘ │  │
       │  └──────────────────┘  │
       └───────────────────────┘
```

### 7.2 A1–A4 单元 / 集成测试矩阵

| 模块 | case | 目标 |
|---|---|---|
| **A1** CitationPositionChecker | 8 case | 95% 覆盖 |
| **A2** SocraticAgent 分流 | 4 case | 100% |
| **A3** FieldFetchers + CardCache + Loader | 7+4 case | 老路径不回归 |
| **A4** extract_pattern + consolidator | 5+2 case | consolidator 不回归 |

### 7.3 B1–B6 测试矩阵

| 模块 | case | 目标 |
|---|---|---|
| **B1** 督导测试 22/22 (含 step2 cancel-on-respond) | 28 case | 100% pass |
| **B1** E2E 流 3 | 6 case | 100% |
| **B2** drift detector | 4 case | CI 不报错 |
| **B3** 流 1 E2E | 8 case | 全过 |
| **B3** LangChain 对照实验 | 4 case（引用重叠 > 85% / 拒答率差 < 5% / 延迟差 < 20% / token 差 < 15%）| 全过 |
| **B4** 跨 Agent schema 隔离 | 3 case | 全过 |
| **B5** SessionStart Hook | 4 case | hook P95 < 2s |
| **B6** chaos + 红队 200 + perf | 8 case | 全过 |

### 7.4 验收门槛（每切片退出）

| 切片 | 通过阈值 |
|---|---|
| A1 | 8/8 单元 + 红队 G 100% |
| A2 | 4/4 单元 + e2e 现有 6/6 不回归 + 新路径 6/6 |
| A3 | 7+4 单元；端到端启动 P95 < 100ms |
| A4 | 5+2 单元 + 集成；consolidator 22/22 不回归 |
| B1 | 28/28 督导 + 流 3 E2E 6/6 |
| B2 | 4/4 + CI 集成 |
| B3 | 流 1 E2E 8/8 + 对照实验 4/4 |
| B4 | 3/3 schema 隔离 |
| B5 | 4/4 + manual hook P95 < 2s |
| B6 | chaos 3/3 + 红队 200/200 + perf 2/2 + 对照实验 4/4 |

### 7.5 CI/CD 集成

| 触发 | 跑什么 | 阻断？ |
|---|---|---|
| pre-commit | lint + 仅修改模块单测 | ✅ |
| PR | 单元 + 契约 + 集成（docker）+ 关键模块覆盖 | ✅ |
| 合并 main | + LangChain 对照实验（B3 起生效）| ✅ |
| 每日 02:00 | 全量集成 + perf + drift 报告 | ❌（报告）|
| 每周一 04:00 | 红队 200 条 + chaos drill | ❌（报告）|
| 每月初 | 人工评估 50 条督导 | ❌（报告）|

**CI 变更 1 处：** PR 流程加 docker-compose 服务（+25s）。

### 7.6 测试数据管理

| 数据 | 来源 | 保留期 |
|---|---|---|
| 单元 fixture | 手工 + 自动 | 永久 |
| 集成 | `tests/integration/scenarios/` | 永久 |
| 红队 | `tests/redteam/prompts.yaml` 累计 200 | 累计 |
| 历史对话 | `tests/parity/conversations.jsonl` 匿化 | 2 年 |
| chaos report | `perf-results/chaos-{date}.json` (gitignore) | 当次 |

## 8. 切片细节

### 8.1 A1 — S3 引用位置校验（1d）

**目标：** [citation.py:36](app/services/llm/citation.py#L36) `has_citation` 由字符串包含 → 改为调用 `CitationPositionChecker`；红队 G 类从 12 条扩到 25 条；G 类 100/100 通过。

**工作：**
- 新建 `app/services/llm/citation_position.py` (30 行)
- 改 `app/services/llm/citation.py` 1 个函数
- 新建 `tests/services/test_citation_position.py` (8 case)
- 扩 `tests/redteam/prompts.yaml` G 类 12 → 25 条
- 跑 `tests/redteam/run.py` → 仍 overall_pass=True

**风险：** 误判（claim 太长时窗口要扩）→ 可配阈值，默认 ±80 字。

### 8.2 A2 — S2 接通（1.5d）

**目标：** SocraticAgent 走 `produce_socratic_response`（env 控制），老路径不破坏。

**工作：**
- 改 `agents.py:SocraticEvaluatorAgent.handle_user_message` 顶部加 5 行 env flag
- 新建 `tests/services/test_socratic_dispatch.py` (4 case)
- local 跑 `USE_LANGCHAIN_SOCRATIC=1 python main.py` → e2e 流 1 通过

**风险：** 老路径仍需同样的引用校验 → 老路径与新路径用同一个 AntiHallucinationParser。

### 8.3 A3 — S5 load() 真接（2d）

**目标：** `MemoryCardLoader.load()` 拆 stub → 串 4 fetcher + cache。

**工作：**
- 新建 `app/services/agent/field_fetchers.py` (80 行, 4 个 fetcher 方法)
- 新建 `app/services/agent/card_cache.py` (40 行)
- 改 `app/services/agent/memory_card_loader.py` 拆掉 stub
- 新建 `tests/services/test_field_fetchers.py` (7 case)
- 新建 `tests/services/test_card_cache.py` (4 case)
- 性能测试：本地 fetch 全 4 字段 < 100ms

**风险：** fetcher 并发跑 → 用 `concurrent.futures.ThreadPoolExecutor(max_workers=4)`；DB 慢 → 250ms timeout。

### 8.4 A4 — S6 真接 LLM（1d）

**目标：** `extract_pattern` 从 stub → 真调 LLM + JSON 解析。

**工作：**
- 改 `app/services/memory/llm_extractor.py` 单一函数
- 改 `app/services/memory/consolidator.py:171` 调用点 1 行参数（加 `llm=XunfeiChatModel()`）
- 新建 `tests/services/test_llm_extractor_real.py` (5 case)
- 跑 100 合成 episodic → 应出 ≥ 1 簇

**风险：** LLM 抽取不稳定 → 30s timeout + per-cluster 失败隔离；JSON 解析失败 → fallback。

### 8.5 B1 — S7 督导层（3-4d）

（见 [原 spec §7 三、S7 详细](2026-07-13-llm-4-painpoints-kb-design.md#s7-l3-督导层)）

**新增差异：**
- 当前 6 测试失败先修（fixture 缺 `supervision_rules` 表 → 在 conftest.py 加 `Base.metadata.create_all` 或 alembic upgrade）
- scheduler 用现有 `apscheduler` 依赖

**工作：**
- 改 `tests/conftest.py` 加 metadata create_all (0.5d)
- 新建 `app/services/supervision/escalation_chain.py` (80 行) (1d)
- 改 `app/services/supervision/channel_dispatcher.py` + retry (1d)
- `tests/services/test_supervision_rule_engine.py` 补 6 case + 修复 (1d)
- `tests/integration/test_supervision_e2e.py` 新建流 3 (1d)

### 8.6 B2 — S8 Drift 检测（2-3d）

**工作：**
- 新建 `app/models/drift_report.py` (50 行)
- 新建 `app/repositories/orm/drift_report.py` (40 行)
- 新建 `app/services/drift/detector.py` (100 行, KB file hash 变更检测)
- 新建 `app/services/drift/adr_parser.py` (60 行, ADR frontmatter 解析)
- 新建 `app/services/drift/reporter.py` (50 行)
- 新建 `app/services/drift/scheduler.py` (40 行, 04:00 cron)
- 新建 `scripts/drift_detector.py` (CLI wrapper)
- 新建 `tests/services/test_drift_*.py` 4 文件 + `tests/integration/test_drift_ci.py`
- 改 `.github/workflows/ci.yml` 加 daily 02:00 drift job

### 8.7 B3 — S9 SocraticAgent 接卡（3-4d）

**工作：**
- 改 `agents.py` 加 2 行 import + `_with_memory_card` 装饰器
- 改 `app/api/agent_orchestration.py` SSE 流注入 memory card metadata
- `tests/services/test_socratic_dispatch.py` 加端到端 8 case
- `tests/parity/langchain_parity.py` 新建 100 条历史对话对照实验
- `tests/parity/conversations.jsonl` 准备 100 条匿化对话
- perf 测：1000 并发 P99 < 3s

### 8.8 B4 — S10 Profile/Echo（2-3d）

**工作：**
- 新建 `app/services/agent/profile_memory_card.py` (50 行)
- 新建 `app/services/agent/echo_memory_card.py` (30 行)
- 改 `agents.py:ProfilerAgent.handle_user_message` + `EchoAgent` 各 1 行
- 测试 3 case：跨 Agent 卡片隔离

### 8.9 B5 — S11 冷启动（2-3d）

**工作：**
- 改 `.claude/settings.json` 加 SessionStart hook (1 个新 hook entry)
- 新建 `app/services/claude_card/loader.py` (100 行, 5 类并行收集)
- 新建 `app/services/claude_card/cache.py` (30 行, TTL 1h)
- 新建 `app/services/claude_card/packer.py` (60 行, markdown 拼装 ≤ 3KB)
- 测试 4 case：cache hit / 5 类并行 / Drift 全挂 fallback / Markdown byte ≤ 3KB

### 8.10 B6 — S12 P1 端到端验证（3-4d）

**工作：**
- 新建 `scripts/chaos_drill.py` (200 行, Qdrant kill / Redis kill / 讯飞 5xx / hook 超时 4 类)
- 新建 `tests/parity/{langchain_parity.py,conversations.jsonl}` (4 case)
- 扩 `tests/redteam/prompts.yaml` 100 → 200 条
- 改 `perf-results/` 加 baseline json (Locust script)
- 改 `.github/workflows/ci.yml` 加 weekly chaos + redteam cron
- 更新 `docs/runbook-p1.md` (新文件, 运维手册)

## 9. 验收标准

### 9.1 必达（每切片退出门槛）

详见 §7.4。

### 9.2 P1 完整验收（原 spec §9 A1–A15）

P1 在最后一个切片 B6 完成后，必须达到：

- **A1** 反幻觉 8 类 80 条 unit + 200 条红队 = **280/280**
- **A2** 红队 200 条 100% safe_fallback ratio
- **A3** consolidator 8 类场景 + 100 合成 episodic
- **A4** Agent 记忆卡 token 100% ≤ 500
- **A5** SocraticAgent 端到端 P99 < 3s（perf baseline）
- **A6** LangChain 对照实验 4 项（重叠 > 85% / 拒答率差 < 5% / 延迟差 < 20% / token 差 < 15%）
- **A7** chaos drill（Qdrant 挂 30s → L3 / Redis 挂 30s → L1 / 60s 升 L0）
- **A8** Qdrant 主从 + 5s 内切换
- **A9** HealthProbe 10s / 1min 升 / 3 失败降
- **A10** ResilientBehaviorLogger 3 层 buffer
- **A11** Drift 检测 CI 每日 100% L1 扫描
- **A12** SessionStart Hook P95 < 2s
- **A13** 关键模块覆盖率 > 95%
- **A14** 灰度 1% → 10% → 50% → 100%
- **A15** API doc + Runbook + 运维手册齐全

## 10. YAGNI 边界（沿用原 spec §10）

- 不重写 context_aggregator / agents.py 任何已有方法
- 不引入新 LLM 框架
- 不重写 supervisor / drift 老的 deliverable
- 不改 LangChain 锁版本（仍 0.3.x）
- 不做 PDF / B 站自动解析
- 不做教师批注
- 不做学生端图谱可视化

## 11. 风险与决策日志

### 11.1 风险总览

| 等级 | 风险 | 缓解 |
|---|---|---|
| **P0** | S1–S6 缺口漏修 → A2 接通路径仍有 G 类 hallucination | A1 红队 200/200 阻断合并 |
| **P0** | A2 双轨接入破坏现有 SocraticAgent | env `=0` 默认走老路径；e2e 6/6 不回归 |
| **P1** | Redis buffer 在 99.9% SLO 下压力大 | 用本地文件做主，Redis 做加速（spec 原话）|
| **P1** | B1 测试修复引入 alembic 升级 → 可能破坏其他测试 | 用 `Base.metadata.create_all` 在 conftest 而非生产代码 |
| **P2** | Drift 检测触发误报 → Daily 告警炸 | 阈值默认 90d，可配；首次扫只报告"自上次 commit 以来" |
| **P2** | 红队 prompt 库累积过慢 | 每周跑红队时人工补 10 条 |

### 11.2 关键决策（ADR-Lite）

| # | 决策 | 理由 | 影响 |
|---|---|---|---|
| **D1** | 4 个 S1–S6 缺口作为 4 个独立 PR | 每个 PR diff < 200 行，便于 review + 回滚 | +1 周 |
| **D2** | `USE_LANGCHAIN_SOCRATIC` env flag 默认 `0` | 与原 spec "老路径永远可回退" 一致 | spec 已承诺 |
| **D3** | SessionStart Hook 不动原 PreCompact hook | 原 hook 已用于 compaction 摘要；不互相覆盖 | spec 不变 |
| **D4** | B1 用 `Base.metadata.create_all` 在 conftest 而非 alembic upgrade | 单 test 用，不用动迁移脚本 | 不影响生产 |
| **D5** | B6 perf baseline 用 Locust 而非 k6 | 项目已有 k6 依赖？不，引入 Locust 增加依赖；用现有 pytest-benchmark 替代 | +0d |

### 11.3 变更控制

- 本 spec 任何修改走 PR + 用户确认（沿用原 spec 第 8 节 七）
- 关键决策 D1–D5 变更需明确理由并更新本文档
- 实施期间如发现假设错误，立即开 brainstorming 修订

### 11.4 切片依赖与执行顺序

**用户决策：** 严格 critical path 顺序（B1→B2→B3→B4→B5→B6，串行执行）。

**逻辑依赖图（仅"可以做"的依赖，不反映执行顺序）：**

```
A1 → A2 ─┬→ A3 ──────────────────────────────┐
         │                                     ↓
         └→ A4 ─┬──────────────────────────┐    │
              ↓                            ↓    ↓
              B1 (S7) → B3 (S9) → B4 (S10) ──→ B6 (S12)
              
A4 ────────────────────→ B2 (S8) ─┐
                                 ↓
                              B5 (S11) ─→ B6
```

**关键依赖（必须满足）：**
- A2 必须先：A3 和 A4 都依赖 `produce_socratic_response` 已经是 `agents.py` 的可选入口
- A3 必须先于 B3：流 1 端到端接卡的代码路径要先通
- B1 + A3 必须先于 B3：`supervision_pending` 字段 fetcher 在 B1 才能取到
- B2 必须先于 B5：冷启动卡里的漂移警告数据来自 B2
- B3 + B4 + B5 都必须先于 B6：S12 是 P1 验收总收口

**执行顺序（用户确认的 critical path）：**

```
A1 → A2 → A3 → A4 → B1 → B2 → B3 → B4 → B5 → B6
```

每片结束 → `git tag slice-{A1|A2|A3|A4|B1|B2|B3|B4|B5|B6}`。违反此顺序视为变更控制事件（§11.3）。

**核心创新路径：** A1 → A2 → A3 → B3 → B6（P1 Day-1 验收最小依赖）
**最后收口：** B6（P1 A1–A15 全过）
