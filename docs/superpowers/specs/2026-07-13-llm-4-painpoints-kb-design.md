---
title: 一体化知识中台 - LLM 4 痛点治理
date: 2026-07-13
status: 待 review
author: Brainstorming 会话
project: 星识 Star-Learn
supersedes: 无
related:
  - docs/superpowers/specs/2026-07-08-db-merge-design.md
  - docs/superpowers/specs/2026-07-10-mascot-unified-design.md
  - SLICE_STATUS.md
risk_level: 高
target_release: P1 (8 周)
langchain_version: 0.3.x (锁定)
qdrant: 主从部署
redis: 单机
---

# 一体化知识中台 - LLM 4 痛点治理

## 目录

- [1. 背景与目标](#1-背景与目标)
- [2. 架构总览](#2-架构总览)
- [3. 核心数据模型](#3-核心数据模型)
- [4. LangChain 集成与向量库升级](#4-langchain-集成与向量库升级)
- [5. 三大创新机制实现细节](#5-三大创新机制实现细节)
- [6. 数据流](#6-数据流)
- [7. 错误处理与降级](#7-错误处理与降级)
- [8. 测试策略](#8-测试策略)
- [9. 实施切片](#9-实施切片)
- [10. 验收标准](#10-验收标准)
- [11. YAGNI 边界](#11-yagni-边界)
- [12. 风险与决策日志](#12-风险与决策日志)
- [13. 变更控制](#13-变更控制)

---

## 1. 背景与目标

### 1.1 现状

星识 (Star-Learn) 是一个基于多智能体架构的 AI 伴学系统，核心痛点不在数据规模，而在 **LLM 的四个根本性缺陷**：

| 痛点 | 表现 | 已有应对 | 缺口 |
|---|---|---|---|
| **被动回复** | LLM 等待输入，不主动督导 | ProactiveAdvisor 25+ 规则、ActionLedger | 规则碎片在 prompt 里，跨 Agent 不可复用；无时间窗口/降噪策略 |
| **知识幻觉** | LLM 编造事实 | `tutor_engine.hallucination_guard`（雏形）| 无结构化内容源；无"无引用就拒答"的硬约束 |
| **缺乏记忆** | 跨会话失忆 | 6 维画像、SM2、对话历史 | 记忆散落在多个表/JSON，没有统一的"记忆检索"接口；无"上次聊到哪"机制 |
| **缺乏督导** | 不持续追踪学情 | EchoAgent、SM2、weakness 维度 | 督导是事件驱动而非连续模型；升级策略缺失 |

### 1.2 目标

构建**一体化知识中台**，直接对齐 LLM 4 痛点：

1. 让 LLM 拥有**可被引用的内容源**（治幻觉）
2. 让 LLM 拥有**三类记忆 + 巩固机制**（治失忆）
3. 让 LLM 拥有**主动督导 + 升级链**（治被动）
4. 让 LLM 拥有**学情时间线 + 截止感知**（治失督）
5. 让 Claude / 开发者拥有**冷启动记忆卡**（提升研发效率）

### 1.3 非目标（P1 期间明确不做）

- 跨用户知识共享、多租户、RBAC
- LLM 微调 / RLHF
- PDF / B 站自动解析
- 实时协作 / CRDT
- 学生端知识图谱可视化
- 教师实时批注 / 小组共学
- 自建完整 RAG 框架（用 LangChain，**不**自造轮子）

### 1.4 成功判据

**核心 SLO：** 学生路径可用性 99.9%，P99 延迟 < 3s，反幻觉拒答率 < 15%（含 L3 拒答）。

---

## 2. 架构总览

### 2.1 一句话定位

**LangChain 做"框架骨架"（检索 / 切分 / 输出解析 / LLM 适配 / Memory 抽象），自研做"3 大创新"（护栏 / 巩固 / 记忆卡）。** 不让 LangChain 吃掉创新层。

### 2.2 5 层 × 3 端 × 1 底座

```
                    ┌──────────────────────────────┐
                    │   3 端：学生 / 开发者 / Agent │
                    └──────────────┬───────────────┘
                                   ▼
┌────────────────────────────────────────────────────────────────┐
│           一体化知识中台（按 LLM 4 痛点组织）                    │
├────────────────────────────────────────────────────────────────┤
│  L1 内容层（抗幻觉）   │ 课程/知识点/例题/代码片段（含来源）   │
│  L2 记忆层（治失忆）   │ 情景/语义/程序三类记忆 + 跨会话连续性  │
│  L3 督导层（治被动）   │ 25+ 规则 → 触发链 → 多通道推送        │
│  L4 学情层（治失督）   │ 6 维画像 + SM2 + 截止 + 弱点时间线    │
│  L5 决策层（贯穿）     │ ADR + Agent 行为日志 + 漂移检测        │
├────────────────────────────────────────────────────────────────┤
│   底座：Qdrant + SQLite + Redis + 仓库内 kb/  + 治理与漂移     │
└────────────────────────────────────────────────────────────────┘
```

| 层 | 名称 | 数据形态 | 解决痛点 | 已有资产可复用 |
|---|---|---|---|---|
| L1 | 内容层 | 结构化知识节点（含来源、版本、TTL） | 知识幻觉 | 无（需新建） |
| L2 | 记忆层 | 情景 / 语义 / 程序三类记忆 | 缺乏记忆 | 6 维画像、SM2、对话历史（需抽象统一） |
| L3 | 督导层 | 触发规则 + 升级链 + 通道策略 | 被动回复 | ProactiveAdvisor 25+ 规则、ActionLedger |
| L4 | 学情层 | 6 维 + SM2 + 截止 + 弱点时间线 | 缺乏督导 | 已有 6 维、SM2；缺截止与时间线 |
| L5 | 决策层 | ADR + Agent 行为日志 + 漂移检测 | 贯穿支撑 | SLICE_STATUS、docs/superpowers |

### 2.3 3 端视图

- **学生端**：内容检索带引用、接收主动推送、查看学情
- **开发者 / Claude 端**：项目状态包、决策记录、漂移警告
- **Agent 端**：启动时拉"记忆卡"，运行时按需 query

### 2.4 1 底座

- **存储**：仓库内 `kb/`（JSON + Markdown）+ SQLite（`xingshi_v2.db` 复用）+ Qdrant（向量）+ Redis（buffer）
- **治理**：provenance / freshness / 引用强制 / 质量评分
- **版本**：KB 节点走 git 跟踪（变更可 diff）；运行时数据走 SQLite
- **检索适配器**：按 Agent 角色裁剪
- **漂移检测**：CI 每日跑，标记 `stale` 节点

### 2.5 3 大创新机制

1. **「无引用 = 不出」反幻觉护栏** — LLM 输出必须含 `[KB:node_id]` 引用；缺失则重试 1 次，再缺则拒答
2. **「记忆巩固」** — 情景记忆（具体对话/事件）聚类后由 LLM 抽取模式 → 升级为语义记忆
3. **「Agent 记忆卡」** — 每个 Agent 启动拉 1 张 ≤500 token 的"我需要看的记忆"卡

### 2.6 关键设计原则

- **痛点直接映射层**：避免"为了中台而中台"
- **存储异构**：治理/审计数据用 git 跟踪的 JSON/MD，运行时数据用 SQLite，向量用 Qdrant
- **YAGNI 严格**：不引入 Pinecone / 完整 LangChain Agent / 外部 RAG 服务；不重写 LLM 调用层
- **可分片交付**：每层独立可测、可灰度

---

## 3. 核心数据模型

### 3.1 L1 内容层（实现「反幻觉护栏」）

```python
class KnowledgeNode:
    id: str              # "KB-CON-0001" 稳定 ID，引用唯一锚点
    title: str
    content: str         # markdown，按 ~500 token 切片
    chunk_index: int     # 0..N
    source: SourceRef    # ← 反幻觉核心：每个节点必须可溯源
    related_nodes: list[str]
    tags: list[str]
    version: int
    last_verified_at: datetime
    ttl_days: int        # 过期窗口；过期后被漂移检测标 stale
    embedding: vector    # Qdrant 索引

class SourceRef:
    type: Literal["textbook", "codebase", "agent_output", "manual", "external_parsed"]
    reference: str       # ISBN / commit SHA / AgentName+日期 / 编写人
    confidence: float    # 0-1
    verifier_id: str | None
```

**关键约束：** `SourceRef` 不可为空。无来源的节点 = 不允许入库（直接拒收）。

### 3.2 L2 记忆层（实现「记忆巩固」）

```python
class EpisodicMemory:
    id: str              # "EP-20260713-00042"
    user_id: str
    event_type: str      # "conversation" / "code_submit" / "quiz" / "review"
    summary: str         # 200 字内
    embedding: vector
    created_at: datetime
    consolidated_into: str | None  # → SemanticMemory.id
    user_id__event_type__created_at  # 联合索引

class SemanticMemory:
    id: str              # "SEM-001"
    user_id: str
    concept: str         # "function_thinking_weak"
    statement: str
    confidence: float    # 0-1
    evidence_ids: list[str]   # → EpisodicMemory.id 列表
    last_reinforced: datetime
    last_contradicted: datetime | None
    status: Literal["active", "fading", "retired"]

class ProceduralMemory:
    id: str
    user_id: str
    strategy: str        # "spaced_repetition"
    success_rate: float
    sample_size: int

class MemoryConsolidationJob:
    id: str
    user_id: str
    status: Literal["queued", "running", "done", "failed"]
    episodic_input_ids: list[str]
    semantic_created: list[str]
    semantic_updated: list[str]
    semantic_retired: list[str]
    started_at: datetime
    finished_at: datetime | None
```

**关键设计：** `EpisodicMemory.consolidated_into` 是巩固的"指针"；`SemanticMemory.evidence_ids` 双向追溯。

### 3.3 L3 督导层（实现「督导升级链」）

```python
class SupervisionRule:
    id: str              # "SUP-014"
    name: str
    trigger_dsl: str     # 受限 DSL
    action_template: str
    channels: list[str]
    cooldown_hours: int
    escalation_chain_id: str | None
    enabled: bool

class EscalationChain:
    id: str
    steps: list[EscalationStep]  # 1..N 步

class SupervisionEvent:
    id: str
    user_id: str
    rule_id: str
    fired_at: datetime
    current_step: int
    response_status: Literal["pending", "responded", "escalated", "stopped"]
    ledger_ref: str       # → ActionLedger 防重放
```

### 3.4 L4 学情层

```python
class CapabilityProfile:  # 现有，沿用
    user_id: str
    knowledge_base: float
    code_skill: float
    cognitive_style: float
    focus_level: float
    learning_goals: float
    weakness: float
    last_updated: datetime
    version: int

class SM2Card:  # 现有，沿用
    user_id: str
    kb_node_id: str        # ← 关联到 L1 节点
    ease_factor: float
    interval_days: int
    next_review: datetime
    last_review: datetime

class DeadlineTracker:     # 新增
    id: str
    user_id: str
    title: str
    deadline: datetime
    related_kb_nodes: list[str]
    status: Literal["pending", "warned", "overdue", "done"]
    supervised_by_rule_id: str | None

class WeaknessTimeline:    # 新增
    id: str
    user_id: str
    dim: str
    score: float
    snapshot_at: datetime
    evidence_kb_nodes: list[str]
```

### 3.5 L5 决策层

```python
class ADR:
    id: str              # "ADR-007"
    title: str
    status: Literal["proposed", "accepted", "deprecated"]
    context: str
    decision: str
    consequences: str
    affected_paths: list[str]
    created_at: datetime

class AgentBehaviorLog:  # ← 反幻觉的"审计轨"
    id: str
    agent_id: str
    user_id: str | None
    action_type: str
    input_summary: str
    output_text: str
    citations: list[Citation]
    hallucination_risk_score: float
    blocked: bool
    block_reason: str | None
    timestamp: datetime

class Citation:
    kb_node_id: str
    claim: str
    position: int
    confidence: float

class DriftReport:
    id: str
    generated_at: datetime
    stale_kb_nodes: list[str]
    stale_affected_rules: list[str]
    stale_sessions: list[str]
```

### 3.6 跨层：Agent 记忆卡（实现「Agent 记忆卡」）

```python
class AgentMemoryCardSchema:
    agent_id: str
    fields: list[CardField]
    total_max_tokens: int  # 整张卡预算，默认 500

class CardField:
    key: str
    source_layer: Literal["L1","L2","L3","L4","L5"]
    query: str              # 受限查询语句（不是自由 SQL）
    max_tokens: int
    ttl_seconds: int
    fallback: str | None
```

**关键设计：** `query` 用受限查询语言（白名单表+过滤词），绝不允许 raw SQL；字段级 TTL 让频繁变化的数据不被陈旧记忆卡拖累。

### 3.7 模型间关系

```
L1.KnowledgeNode ──┬── 引用 ──→ L5.AgentBehaviorLog.citations
                   └── 关联 ──→ L4.SM2Card.kb_node_id
                                L4.DeadlineTracker.related_kb_nodes

L2.EpisodicMemory ── 巩固 ──→ L2.SemanticMemory.evidence_ids
                └── 巩固 ──→ L2.MemoryConsolidationJob

L3.SupervisionRule ── 触发 ──→ L3.SupervisionEvent
                                ↑ ActionLedger 防重放

L4.CapabilityProfile ── 快照 ──→ L4.WeaknessTimeline
L4.SM2Card ── 复习 ──→ L1.KnowledgeNode

L5.ADR ── 影响 ──→ 代码文件路径
L5.DriftReport ── 标记 ──→ L1.stale / L3.stale

跨层：AgentMemoryCardSchema.{field.source_layer ∈ [L1..L5]}
```

### 3.8 与现有资产的对接（迁移路径）

| 现有 | 接入到 | 改造 |
|---|---|---|
| `tutor_engine.hallucination_guard` | L1 + L5 联动 | 加 `citations` 必填校验，写入 `AgentBehaviorLog` |
| `tutor_engine.action_ledger` | L3 共用 | 加 `ledger_ref` 字段 |
| `tutor_engine.context_aggregator` | L2 + L4 桥接 | 输出 `AgentMemoryCard` 格式 |
| `proactive_tutor` 25+ 规则 | L3 重构 | 提取 `SupervisionRule.trigger_dsl`；加 `escalation_chain` |
| `CapabilityProfile` (6 维) | L4 沿用 | 加 `WeaknessTimeline` 增量表 |
| `SM2` | L4 沿用 | `kb_node_id` 替代字符串 `node_id` |
| `docs/superpowers/specs` | L5 沿用 | 自动解析 ADR frontmatter 入库 |
| `local_storage.json` JSON 回退 | 废弃 | 数据统一入 SQLite + git-tracked JSON |

---

## 4. LangChain 集成与向量库升级

### 4.1 向量库选择

| 候选 | 优劣 | 决策 |
|---|---|---|
| **Qdrant** | 单二进制，自托管，REST API，Rust 性能，10K-1M 向量无压力 | ✅ **首选** |
| Chroma | 最简单，文件式，但 > 5K 性能掉 | ❌ |
| Milvus | 企业级，运维重 | ❌ |
| pgvector | 需要迁到 PG | ❌ |

**理由：** 与你"仓库 + SQLite 轻量部署"风格一致；5K 节点下 P99 < 50ms；支持 metadata 过滤（`SourceRef` 校验可直接用 Qdrant payload 过滤做）。

**部署：** 主从 + 哨兵自动切换（5s 内切换，99.9% SLO 要求）。

### 4.2 LangChain 组件 × 5 层映射

| 5 层 | LangChain 用什么 | 自研覆盖什么 |
|---|---|---|
| L1 内容层 | `Document` + `RecursiveCharacterTextSplitter`（中文优化）+ `VectorStore` (Qdrant) + `Embeddings` (讯飞) + 自研 `CitationRetriever` | `KnowledgeNode` schema + `SourceRef` 强制溯源 + `chunk_index` 切分策略 |
| L2 记忆层 | `BaseMemory` 子类（3 个：`EpisodicMemory` / `SemanticMemory` / `ProceduralMemory`）+ `ConversationSummaryMemory` 作工程基础 | 巩固任务调度、证据链双向追溯、用户通知 |
| L3 督导层 | （不直接用 LangChain） | `SupervisionRule` + `EscalationChain` + DSL 评估器 |
| L4 学情层 | （不直接用 LangChain） | 沿用现有 6 维 / SM2 |
| L5 决策层 | `Callback` 钩子统一写 `AgentBehaviorLog` | ADR / DriftReport |

### 4.3 关键自研类

| 自研类 | 父类 | 作用 |
|---|---|---|
| `XunfeiChatModel` | `BaseChatModel` | 包装 `llm_stream.py`，让 LangChain 能调讯飞 API |
| `AntiHallucinationOutputParser` | `BaseOutputParser` | 解析 LLM 输出，强制要求 `[KB:node_id]` 引用；缺失则重试或拒答 |
| `CitationRetriever` | `VectorStoreRetriever` | 检索时返回 `(node, score, citation_required=True)` 三元组 |
| `EpisodicMemory` / `SemanticMemory` / `ProceduralMemory` | `BaseMemory` | 3 类记忆的标准接口 |
| `AgentMemoryCardTool` | `BaseTool` | 暴露给 Agent 的"记忆卡字段查询"工具 |
| `KBCallbackHandler` | `BaseCallbackHandler` | 统一记入 `AgentBehaviorLog` |

### 4.4 LangChain 组件取舍

| LangChain 组件 | 用 / 不用 | 理由 |
|---|---|---|
| `langchain-core` | ✅ | 必须 |
| `langchain-text-splitters` | ✅ | 中文切分需要 |
| `langchain-community` (向量库适配) | ✅ | Qdrant 适配 |
| `langchain.embeddings` | ✅ | 讯飞 embedding 适配 |
| `langchain.llms` / `chat_models` | ✅ | 讯飞 LLM 适配 |
| `langchain.retrievers` | ✅ + 自研 | 基础 retriever + CitationRetriever |
| `langchain.output_parsers` | ✅ + 自研 | AntiHallucinationOutputParser |
| `langchain.memory` | ⚠️ 部分用 | 抽象用 BaseMemory，逻辑自研 |
| `langchain.agents` / `AgentExecutor` | ❌ | 你有 MasterController，自研多智能体 |
| `langchain.chains` (LLMChain 等) | ❌ | 你的 context_aggregator 更贴合 |
| `langchain.document_transformers` | ❌ | 过重 |
| `langchain.evaluation` | ❌ | 自研评估 |
| `langchain.callbacks` | ✅ | KBCallbackHandler |

### 4.5 迁移路径

```
Step 1: 引入 LangChain 包（5-8 个），不改任何业务代码
Step 2: 写 XunfeiChatModel 适配器，路由到现有 llm_stream.py
Step 3: 新建 Qdrant 主从实例，写 KB ingestion pipeline（独立模块）
Step 4: context_aggregator 改造：原路径保留，新路径走 LangChain RetrievalChain
Step 5: 灰度切读（READ_BACKEND_PERCENTAGE 复用你已有机制）
Step 6: 全部切到 LangChain，context_aggregator 老路径降级为回退
```

**核心原则：** 切读期间两套并存，**老路径永远可回退**。

---

## 5. 三大创新机制实现细节

### 5.1 创新 1：反幻觉护栏（Anti-Hallucination Firewall）

#### 工作流

```
[用户提问]
   ↓
[SocraticAgent 加载记忆卡] (L2/L4 摘要)
   ↓
[CitationRetriever 检索 L1 节点 Top-K] → 返回 (node, score, must_cite=True)
   ↓
[Prompt 拼装: 系统提示 + 记忆卡 + 检索节点 + 用户问题]
   ↓
[LLM 输出] ──→ [AntiHallucinationOutputParser]
                  ├─ 解析出 (claim, citation) 对
                  ├─ 每条 claim 必须有 [KB:node_id] 引用
                  ├─ 引用 ID 必须在检索结果中存在
                  └─ 决策树:
                       ├─ 全有引用 + 引用有效 → ✅ 通过 + 记 Log
                       ├─ 部分无引用 → ⚠️ 重试 1 次
                       ├─ 重试仍缺 → ❌ 拒答，返回"我需要核实"
                       └─ 引用 ID 不存在 → 🚨 安全事件，记 Log + 告警
```

#### 关键代码形态

```python
class AntiHallucinationOutputParser(BaseOutputParser[ValidatedResponse]):
    def parse(self, text: str) -> ValidatedResponse:
        citations = extract_citations(text)  # → [Citation(kb_id, claim, pos)]
        claims = extract_claims(text)         # → [str]

        unbacked = [c for c in claims if not has_citation(c, citations)]
        invalid = [c for c in citations if c.kb_id not in self.valid_node_ids]

        risk = compute_risk(unbacked_ratio=..., invalid_ratio=...)

        if unbacked and self.retry_count < 1:
            raise OutputParserException("必须为每条 claim 提供 [KB:xxx] 引用")
        if unbacked:
            return ValidatedResponse(
                text="我需要核实一下再回答。",
                blocked=True, block_reason="unbacked_claims",
                risk=risk
            )
        if invalid:
            return ValidatedResponse(blocked=True, block_reason="invalid_citation_id", risk=1.0)
        return ValidatedResponse(text=text, citations=citations, risk=risk)
```

#### 关键设计选择

- **不删除未引用的内容**（保留 LLM 创造力），而是**强制重试或显式标注**
- **风险评分** = `unbacked_ratio * 0.6 + invalid_ratio * 0.4`，0.7 以上记入 `AgentBehaviorLog.hallucination_risk_score`
- **拒答文案统一**："我需要核实一下再回答。" + 给用户"查看 L1 节点"链接

### 5.2 创新 2：记忆巩固（Memory Consolidation）

#### 工作流

```
[每日 03:00 定时任务 / 用户登录时增量触发]
   ↓
[对每个 active user:]
   ↓
[Step 1: 拉取近 7 天未被巩固的 EpisodicMemory]
   → SELECT * FROM episodic_memory
     WHERE user_id=? AND consolidated_into IS NULL
     AND created_at > now() - 7d
   ↓
[Step 2: 按 event_type + 主题聚类]
   → 同一概念 ≥ 3 个事件触发候选
   → 简化为：embedding 余弦相似度聚类（阈值 0.75）
   ↓
[Step 3: 每个聚类送 LLM 抽取模式]
   → Prompt: "以下是用户 X 的 5 个事件, 提取一条 pattern"
   → 输出: SemanticMemory(statement, confidence, evidence_ids)
   ↓
[Step 4: 与现有 SemanticMemory 比对]
   ├─ 新模式（无相似）→ 创建新 SemanticMemory
   ├─ 强化（与已有相似）→ confidence += 0.1, evidence_ids += 新增
   ├─ 弱化（与已有相反）→ confidence -= 0.15, last_contradicted=now
   └─ 长期未强化（90d 无新证据）→ status='fading' → 180d → retired
   ↓
[Step 5: 写 MemoryConsolidationJob 记录，写入 AgentBehaviorLog]
   ↓
[Step 6: 用户通知（可选）]
   "我们注意到你最近在 X 上持续练习，已记录到你的学习画像中"
```

#### 关键设计选择

- **巩固是异步批任务**，**不阻塞实时对话**
- **`evidence_ids` 双向指针**：语义可找到所有支撑情景，情景可找到自己"贡献"给哪个语义
- **`confidence` 范围 0-1，强化 +0.1，弱化 -0.15**——让弱化稍快，模拟"遗忘"
- **`status` 三态**：`active` / `fading` / `retired`，自动生命周期管理
- **用户可见**：L4 学情页显示"AI 对你的 5 条理解"，每条点开能看到证据事件

### 5.3 创新 3：Agent 记忆卡（Agent Memory Card）

#### 工作流

```
[Agent 启动 / 用户请求触发]
   ↓
[读 AgentMemoryCardSchema]
   → SocraticAgent 的 schema: 4 个字段
   ↓
[按 schema 并行查询各层]
   ├─ L2.episodic.where(user_id, event_type='conversation').last(1)  → 上次对话主题
   ├─ L4.capability.where(user_id).snapshot(within_days=7)            → 最近能力
   ├─ L2.semantic.where(user_id, status='active').top(3, by=confidence) → 相关理解
   └─ L3.supervision_event.where(user_id, response_status='pending')  → 待办督导
   ↓
[按 max_tokens 预算打包成 markdown 文本]
   ↓
[注入 Agent 的 system prompt]
   ↓
[Agent 工作期间]
   ├─ 字段 TTL 到期 → 异步刷新（不阻塞当前 turn）
   └─ 需要深入 → 调 AgentMemoryCardTool 按需查（langchain Tool 接口）
   ↓
[Agent turn 结束]
   → 写回：新产生的 episodic 立即落库
   → 标记：本次 memory_card 字段使用情况（用于优化 schema）
```

#### 关键设计选择

- **`query` 用 LangChain 风格的 `BaseRetriever` 子类实现**，不是自由 SQL
- **字段级 TTL**：频繁变化的（如 `escalation_state`，TTL=5min）vs 慢变的（如 `recent_ability`，TTL=1h）
- **整张卡预算硬上限 500 token**——超时按优先级截断
- **schema 可热更新**：用户画像变化后，schema 不用改，但 `max_tokens` 可调
- **跨 Agent 隔离**：每个 Agent 自己的卡，**不共享**

---

## 6. 数据流

### 6.1 流 1：学生提问 → 反幻觉护栏触发

```mermaid
sequenceDiagram
    autonumber
    participant U as 学生
    participant FE as 前端
    participant API as FastAPI
    participant SA as SocraticAgent
    participant MC as MemoryCardLoader
    participant CR as CitationRetriever
    participant QD as Qdrant (L1)
    participant LLM as 讯飞 LLM<br/>(XunfeiChatModel)
    participant AP as AntiHallucination<br/>OutputParser
    participant CB as KBCallbackHandler
    participant DB as SQLite<br/>(AgentBehaviorLog)

    U->>FE: 输入问题
    FE->>API: POST /api/chat/stream
    API->>SA: handle(user_id, question)

    par 记忆卡加载（4 字段并行）
        SA->>MC: load_card("SocraticAgent", user_id)
        MC->>DB: SELECT episodic.last(1)
        MC->>DB: SELECT capability.snapshot(7d)
        MC->>DB: SELECT semantic.top(3, active)
        MC->>DB: SELECT supervision.pending
    end
    MC-->>SA: memory_card (480 tokens)

    SA->>CR: retrieve(question, top_k=5)
    CR->>QD: vector_search(question_embedding)
    QD-->>CR: 5 nodes
    CR-->>SA: [(node, score, must_cite=True) × 5]

    SA->>SA: 拼装 prompt = system + memory_card + 5 nodes + question

    SA->>LLM: stream(prompt)
    LLM-->>SA: chunks → raw_text

    SA->>AP: parse(raw_text)

    alt 解析通过（全有引用 + 引用有效）
        AP-->>SA: ValidatedResponse(text, citations, risk<0.7)
        SA->>CB: on_llm_end(citations, risk)
        CB->>DB: INSERT AgentBehaviorLog(blocked=false)
        SA-->>API: stream chunks + 引用标注
        API-->>FE: SSE
        FE-->>U: 渲染 + 可点击 [KB:xxx] 引用

    else 缺引用
        AP->>LLM: retry(prompt + "必须为每条 claim 提供 [KB:xxx] 引用")
        LLM-->>AP: chunks2
        AP->>AP: parse(chunks2)
        alt 重试成功
            AP-->>SA: ValidatedResponse (risk 标记 retry_succeeded)
            SA->>CB: on_llm_end(risk=mid)
            CB->>DB: INSERT AgentBehaviorLog(retry_count=1)
        else 重试仍缺
            AP-->>SA: ValidatedResponse(blocked=true, reason="unbacked")
            SA->>CB: on_llm_end(blocked=true)
            CB->>DB: INSERT AgentBehaviorLog(blocked=true, risk=0.85)
            SA-->>API: 返回"我需要核实一下再回答。"
            API-->>FE: SSE
            FE-->>U: 渲染"核实中" + 建议操作
        end
    end

    else 引用了不存在的 node_id
        AP-->>SA: ValidatedResponse(blocked=true, reason="invalid_citation")
        SA->>CB: on_llm_end(blocked=true)
        CB->>DB: INSERT AgentBehaviorLog(blocked=true, risk=1.0)
        CB->>CB: emit_sentry_alert("potential_injection_or_hallucination")
        SA-->>API: 返回"系统错误，请稍后重试"
        API-->>FE: SSE
    end
```

**写入审计：** 每次都落 `AgentBehaviorLog`（含 `citations` / `risk` / `blocked` / `block_reason`），可回放 90 天。

### 6.2 流 2：记忆巩固任务（每日 03:00 跑）

```mermaid
sequenceDiagram
    autonumber
    participant CR as Cron
    participant MC as MemoryConsolidator
    participant DB as SQLite
    participant QD as Qdrant (临时索引)
    participant LLM as 讯飞 LLM
    participant CB as KBCallbackHandler
    participant NS as NotificationService

    CR->>MC: trigger("daily_consolidation")

    loop 对每个 active user
        MC->>DB: SELECT * FROM episodic_memory<br/>WHERE user_id=? AND consolidated_into IS NULL<br/>AND created_at > now()-7d
        DB-->>MC: 30 episodic

        alt 不足阈值（<3 条）
            MC->>MC: skip(user_id)
        else 够阈值
            MC->>MC: cluster_by_embedding(episodic, threshold=0.75)
            MC->>MC: 找到 3 个簇（每簇 5-12 条）

            MC->>DB: INSERT MemoryConsolidationJob(status=running)

            loop 对每个簇
                MC->>LLM: extract_pattern(cluster_summary, existing_semantic)
                LLM-->>MC: {statement, confidence, evidence_ids}

                alt 新模式（与现有无相似）
                    MC->>DB: INSERT SemanticMemory(statement, confidence, evidence_ids)
                else 强化（与已有相似）
                    MC->>DB: UPDATE SemanticMemory<br/>SET confidence+=0.1, evidence_ids=...
                else 弱化（与已有相反）
                    MC->>DB: UPDATE SemanticMemory<br/>SET confidence-=0.15, last_contradicted=now
                else 长期未强化（>90d 无新证据）
                    MC->>DB: UPDATE SemanticMemory SET status='fading'
                end

                MC->>DB: UPDATE episodic SET consolidated_into=...
            end

            MC->>DB: UPDATE MemoryConsolidationJob(status=done)
            MC->>CB: on_consolidation_end(job_id)
            CB->>DB: INSERT AgentBehaviorLog(action_type='memory_consolidation')

            opt 用户开启通知
                MC->>NS: notify(user_id, "我们记录了你最近的 3 个学习模式")
                NS-->>MC: ack
            end
        end
    end

    alt 任意簇 LLM 失败
        MC->>DB: UPDATE MemoryConsolidationJob(status=failed, error=...)
        MC->>CB: on_consolidation_error
        CB->>DB: INSERT AgentBehaviorLog(blocked=true, reason='consolidation_failed')
        Note over MC: 失败不影响其他用户, 下一周期自动重试
    end
```

**关键不变量：** 巩固**永远不阻塞**用户对话；失败时已完成的簇已落库，失败的簇下次重试。

### 6.3 流 3：督导规则触发 + 升级链

```mermaid
sequenceDiagram
    autonumber
    participant CR as Cron (每小时)
    participant SRE as SupervisionRuleEngine
    participant L4 as L4 学情层
    participant L2 as L2 记忆层
    participant AL as ActionLedger
    participant DB as SQLite
    participant CH as ChannelDispatcher
    participant U as 学生

    CR->>SRE: trigger("hourly_evaluation")

    SRE->>DB: SELECT * FROM SupervisionRule WHERE enabled=true
    DB-->>SRE: 27 rules

    loop 对每条 rule
        SRE->>SRE: evaluate_trigger_dsl(rule.trigger_dsl, user_state)
        SRE->>L4: 读 state (capability + sm2 + deadlines)
        SRE->>L2: 读 memory (episodic + semantic)
        L4-->>SRE: state snapshot
        L2-->>SRE: memory snapshot

        alt 触发条件满足
            SRE->>AL: check_cooldown(rule_id, user_id, hours=cooldown_hours)

            alt 冷却中
                SRE->>SRE: skip
            else 未冷却
                SRE->>DB: INSERT SupervisionEvent(status='pending', current_step=1)
                SRE->>CH: dispatch(event, step=1, channels=[in_app])
                CH->>U: in_app 推送

                DB->>DB: 调度 Step 2 (24h 后)
                DB->>DB: 调度 Step 3 (72h 后)
            end
        end
    end

    Note over U,CH: --- 24h 后, 用户未响应 ---

    DB->>SRE: step_2_fired
    SRE->>DB: UPDATE SupervisionEvent(current_step=2)
    SRE->>CH: dispatch(step=2, channels=[in_app, email])
    CH->>U: in_app + email

    Note over U,CH: --- 用户 30min 后登录, 完成 1 题 ---

    U->>API: 完成题目
    API->>DB: 触发 stop_condition 评估
    DB->>DB: SELECT SupervisionEvent WHERE response_status='pending' AND user_id=?
    DB->>DB: UPDATE SupervisionEvent(response_status='stopped', stop_reason='user_responded')
    DB->>DB: 取消 Step 3 调度
    Note over DB: --- Step 3 永远不触发 ---

    Note over U,CH: --- 备选: 72h 后仍未响应 ---

    DB->>SRE: step_3_fired
    SRE->>DB: UPDATE SupervisionEvent(current_step=3)
    SRE->>CH: dispatch(step=3, channels=[sms, email], template="督导介入")
    CH->>U: sms + email
```

**关键不变量：** 升级链**逐级**而非"一开始全开"；用户响应后**任何未执行的 step 立即取消**。

### 6.4 流 4：Claude 冷启动 → 研发记忆卡加载

```mermaid
sequenceDiagram
    autonumber
    participant CC as Claude Code
    participant HK as sessionStart Hook
    participant MCL as MemoryCardLoader
    participant FS as git/MD 文件
    participant DB as SQLite (kb tables)
    participant CR as Cache (内存)

    CC->>HK: session_start
    HK->>MCL: load_card("ClaudeAgent", scope="project")

    MCL->>CR: 检查 cache (key: project_state_v{commit_sha})
    alt 缓存命中且未过期（TTL 1h）
        CR-->>MCL: cached_card
    else 缓存未命中
        par 并行收集 5 类信息
            MCL->>FS: 读 SLICE_STATUS.md (slices status)
            MCL->>FS: 读 docs/superpowers/specs/*/ADR (近 30 天)
            MCL->>FS: git log --oneline -50
            MCL->>DB: SELECT DriftReport WHERE resolved=false
            MCL->>DB: SELECT AgentBehaviorLog.action_type='memory_consolidation'<br/>ORDER BY timestamp DESC LIMIT 5
        end

        MCL->>MCL: 拼接 markdown 文本 (max 3KB)
        MCL->>CR: 写入 cache, TTL=1h
    end

    MCL-->>HK: memory_card (3KB markdown)
    HK->>CC: 注入上下文
    Note over CC: Claude 看到项目当前状态、<br/>最近决策、漂移警告、<br/>巩固记录

    CC->>CC: 准备接收用户任务
```

**示例输出**（3KB markdown 注入）：

```markdown
# Project State @ 4c249c5

## 当前切片
- #1 用户认证: Phase 3 (双写开启, 等待 Phase 4 灰度)
- #11 小星数据源统一化: Phase 3 (双写开启, 等待 Phase 4)
- #12 小星决策引擎集成: Phase 3 完成, 等待灰度

## 漂移警告 (3 个)
- KB-CON-0042 "6 维画像" 源文件已变 (proactive_tutor.py:322)
- KB-CON-0089 "ProactiveAdvisor 规则" 源文件已变 (agents.py:444)
- SUP-014 "学习停滞提醒" 关联 episodic 模式已变

## 最近决策
- ADR-008: 引入 LangChain 完整框架 (2026-07-13)
- ADR-007: 双轨并存 mascot + proactive_tutor (2026-07-10)

## 本周关键变更
- proactive_tutor 4 处 from db import 已删除 (9670cd7)
- MascotEngineAdapter 接入 (e9322fa)
```

**关键设计：** Claude 看到的是**当前真实状态**，不是 3 周前的 PROJECT_MAP.md。

### 6.5 4 条流的"贯穿不变量"

| 不变量 | 说明 |
|---|---|
| **可审计** | 所有 LLM 输出、所有督导触发、所有巩固都落 `AgentBehaviorLog` |
| **可回放** | 每条流都能从 `AgentBehaviorLog` 90 天回放 |
| **可回退** | LangChain 新路径与老 `context_aggregator` 并存，可灰度切读 |
| **非阻塞** | 巩固/督导/漂移检测**永不阻塞**用户实时路径 |
| **预算硬上限** | 记忆卡 ≤ 500 token，研发卡 ≤ 3KB，反幻觉重试 ≤ 1 次 |

---

## 7. 错误处理与降级

### 7.1 设计原则

**用户实时路径永不阻塞**（除安全相关）。任何失败都有降级路径，**且可观测**。

### 7.2 5 级降级模式

| 等级 | 触发条件 | 反幻觉 | 记忆卡 | 督导 | 检索 | 用户感知 |
|---|---|---|---|---|---|---|
| **L0 正常** | 全部组件 OK | ✅ 严格 | ✅ 完整 | ✅ 全功能 | ✅ Qdrant | 完全正常 |
| **L1 轻度** | 巩固任务失败 / Drift 跑挂 | ✅ 严格 | ✅ 完整 | ✅ 全功能 | ✅ Qdrant | 无感知（异步） |
| **L2 中度** | 嵌入服务 / 巩固失败 | ⚠️ skip retry | ✅ 完整 | ⚠️ 暂停主动 | ⚠️ keyword fallback | 响应略慢 |
| **L3 重度** | Qdrant 不可用 / LangChain wrapper 挂 | ⚠️ skip retry | ⚠️ 空卡 | ⚠️ 暂停主动 | ❌ **走老 context_aggregator** | **拒答**"知识库不可用" |
| **L4 系统** | FastAPI 主路径挂 | — | — | — | — | 静态 fallback 文案 |

**降级触发是自动的**（基于健康检查 + SLO 越线），**升级是手动的**（避免抖动）。

**L3 重度降级修订：** Qdrant 不可用时**直接拒答**（不进入 LLM 自由回答路径），反幻觉护栏的"严"在这里体现。

### 7.3 各层失败 → 降级映射

#### L1 内容层

| 失败 | 降级策略 | 告警级别 |
|---|---|---|
| Qdrant 不可用 | L3 拒答（**新增不可降级**）| **P1** 立即 |
| 嵌入服务（讯飞）超时 | 用最近 24h 缓存的 embedding | P2 累计 |
| 引用了不存在的 `KB:node_id` | 拒答（不降级——安全）| **P0** 立即 |
| L1 节点被并发修改（version 冲突） | last-write-wins，写 `DriftReport` | P3 每日 |
| Qdrant indexing lag | 写后 100ms 内 read-after-write 重试 | P2 |

#### L2 记忆层

| 失败 | 降级策略 | 告警级别 |
|---|---|---|
| Episodic 写入失败 | 指数退避重试 3 次，仍失败则丢弃 + 记 log | P2 累计 |
| 巩固任务崩溃 | 标记 failed，下周期重试 | P2 每日 |
| Semantic 冲突 | 选 confidence 最高的版本 | P3 |
| 记忆卡字段查询失败 | 该字段用 fallback，其余正常 | P3 |
| 三类记忆归类失败 | 强制归 episodic | P3 |

#### L3 督导层

| 失败 | 降级策略 | 告警级别 |
|---|---|---|
| Trigger DSL 求值抛错 | skip 该 rule，记 log | P2 |
| ActionLedger 查询失败 | **fail-open**：发，不防重 | P2 |
| Channel 失败 | 重试 1 次后切备用通道 | P2 |
| 升级链某 step 失败 | log，继续下一 step | P2 |
| Stop condition 求值失败 | **fail-safe**：不取消升级 | P1 |
| 督导规则 trigger 永远为真 | 自动禁用 + 告警 | **P0** |

#### L4 学情层

| 失败 | 降级策略 | 告警级别 |
|---|---|---|
| 6 维读失败 | 用 last snapshot，标 `stale=true` | P2 |
| SM2 计算抛错 | `interval_days=1, ease_factor=2.5` 默认值 | P2 |
| Weakness timeline 写失败 | 丢弃，log | P3 |
| 截止日期查询失败 | 返回空列表 | P2 |

#### L5 决策层

| 失败 | 降级策略 | 告警级别 |
|---|---|---|
| ADR 文件不可读 | skip | P3 |
| AgentBehaviorLog 写失败 | **fail-open**：Redis buffer 异步补 | P2 |
| **DB + Redis + Disk 三层都写不了** | **拒答**（**新增不可降级**）| **P0** |
| Drift 检测失败 | 静默 + 告警 | P3 |
| Session summary hook 失败 | 重试 1 次，失败则丢弃 | P2 |
| 冷启动 hook 超时（>5s） | 用空卡启动 | P1 |

#### 跨切面

| 失败 | 降级策略 | 告警级别 |
|---|---|---|
| `XunfeiChatModel` 抛错 | 走老 `llm_stream.py` | P1 |
| AntiHallucination parser 死循环 | 2s timeout → 拒答 | P1 |
| 记忆卡超 500 token | 按优先级截断 | P3 |
| Citation retriever 返回空 | 注入警告，**L3 触发** | P3 |
| LangChain 版本升级破坏 API | 锁版本，升级走 PR review | P3 |

### 7.4 AgentBehaviorLog 3 层 buffer（fail-open 实现）

```python
class ResilientBehaviorLogger:
    def log(self, entry: AgentBehaviorLog):
        try:
            db.insert(entry, timeout=500ms)
        except DBError:
            # 1. 先响应用户, log 异步补
            self.buffer.push(entry)  # Redis List LPUSH
            return LogResult(status="deferred")

    # 后台 worker 持续消费 buffer
    def flush_worker(self):
        while True:
            entry = self.buffer.pop()
            try:
                db.insert(entry)
            except DBError:
                self.disk_buffer.append(entry)  # Redis 也挂时落到本地文件
```

**新增不可降级项：**
- ❌ DB + Redis + Disk 三层都写不了 → 拒答
- ✅ DB 写失败 + Redis OK → 先响应（隐式审计可恢复）
- ✅ DB 写失败 + Redis 挂 + 本地磁盘 OK → 先响应（事后人工导入）

### 7.5 不可降级项（hard rule）

| # | 项目 | 原因 |
|---|---|---|
| 1 | 反幻觉报"引用了不存在的 node_id" | 注入攻击风险 |
| 2 | Qdrant 不可用（触发 L3）| 防止幻觉乘虚而入 |
| 3 | 督导规则 trigger 永远为真 | 自动禁用 + P0 告警 |
| 4 | Qdrant schema 损坏 | 阻塞新写入，读降级 |
| 5 | 冷启动 hook 读到旧 Drift 警告 + 新代码 commit | 警告强制展示 |
| 6 | DB + Redis + Disk 三层都写不了 | 真实事故，拒答 |

### 7.6 告警分级与处理

| 级别 | 含义 | 响应 | 通道 |
|---|---|---|---|
| **P0** | 安全/数据丢失风险 | 立即（< 5 min）| Sentry + 短信 + 邮件 |
| **P1** | 服务降级到 L3 | 30 min | Sentry + 邮件 |
| **P2** | 累计错误率 > 1% | 当日 | Sentry 每日汇总 |
| **P3** | 监控/审计类 | 周报 | Dashboard |

### 7.7 SLO 目标

| 指标 | 目标 | 测量 |
|---|---|---|
| **学生路径可用性** | **99.9%** | 流 1 端到端（L3 拒答算可用）|
| 学生路径 P99 延迟 | < 3s | 流 1 总耗时 |
| **反幻觉拒答率**（含 L3）| **< 15%** | blocked=true / total |
| L3 拒答率 | **< 0.5%** | reason="kb_unavailable" / total |
| **AgentBehaviorLog 落库率** | **> 99.99%** | 含 buffer 恢复 |
| 巩固任务成功率 | > 95% | done / total |
| 督导触发准确率 | > 90% | 人工标注 50 条 / 月 |
| 冷启动 P95 | < 2s | Hook 触发到返回 |
| 漂移检测覆盖率 | 100% L1 节点 | 每日跑完 |

**关键说明：** "可用性" 定义为"**给用户合理响应**"——L3 拒答（"知识库不可用"）算**可用**（用户得到诚实反馈），不算事故。

### 7.8 健康检查与自动降级触发

```python
class HealthProbe:
    CHECK_INTERVAL = 10  # seconds
    UPGRADE_STABLE_CHECKS = 6  # 1min 内连续 6 次通过
    DOWNGRADE_FAIL_CHECKS = 3  # 30s 内 3 次连续失败

    def evaluate(self) -> Level:
        if self.consecutive_failures >= self.DOWNGRADE_FAIL_CHECKS:
            return self.lower_level()
        if self.consecutive_passes >= self.UPGRADE_STABLE_CHECKS:
            return self.raise_level()
        return self.current_level  # 保持
```

**关键参数：**
- 健康检查频率：10s
- 降级延迟：≤ 30s（3 次连续失败）
- 升级延迟：≤ 60s（6/6 连续通过）
- 用户感知降级到 L3：最多 30s 内看到拒答
- 用户感知恢复到 L0：最多 1min 内看到正常

---

## 8. 测试策略

### 8.1 测试金字塔

```
                    ┌─────────────────┐
                    │   红队 + 评估    │  每周 1 次全量
                    ├─────────────────┤
                    │  端到端集成测试   │  PR 必跑 + 每日
                    ├─────────────────┤
                    │   契约测试       │  PR 必跑
                    ├─────────────────┤
                    │   单元测试       │  提交必跑
                    └─────────────────┘
```

### 8.2 单元测试（pytest，目标覆盖率 > 80%，关键路径 > 95%）

| 模块 | 关键 case |
|---|---|
| `KnowledgeNode` 写入 | 缺 `SourceRef` → 拒收 / TTL 过期 → `stale=true` / 并发 version 冲突 → last-write-wins |
| `CitationRetriever` | 5 节点返回顺序稳定 / embedding 服务挂 → 走 keyword fallback |
| `AntiHallucinationOutputParser` | 6 个核心 case（见红队）|
| `MemoryConsolidator` | 8 个核心 case（见巩固测试）|
| `SupervisionRuleEngine` | DSL 求值 5 类边界 / ActionLedger 冷却 / 升级链 step 跳过 |
| `AgentMemoryCardLoader` | 超 500 token 截断顺序 / 字段查询失败 fallback / TTL 到期刷新 |
| `ResilientBehaviorLogger` | DB 失败 → Redis buffer / Redis 失败 → disk spool / 三层失败 → 拒答 |
| `HealthProbe` | 降级 3/3 失败触发 / 升级 6/6 通过触发 / 抖动场景不升 |

**关键路径（> 95% 覆盖）：** `AntiHallucinationOutputParser` / `MemoryConsolidator` / `ResilientBehaviorLogger`

### 8.3 契约测试

| 接口 | 契约项 |
|---|---|
| `POST /api/chat/stream` | 请求 schema / SSE 事件 schema / 引用字段结构 |
| `GET /api/mascot/capability/{user_id}` | 返回 6 维字段 + 时间戳 |
| `POST /api/agent/memory_card/{agent_id}` | 请求 card schema / 响应 token 数 |
| **新增** `POST /api/kb/ingest` | 必填 SourceRef / 拒收无源节点 |
| **新增** `GET /api/memory/consolidation/{user_id}` | 返回最近 job 状态 |
| **新增** `LangChain XunfeiChatModel` 接口 | 与老 `llm_stream.py` 输出等价 |

### 8.4 端到端集成测试（4 条主流程 + 5 条异常流程）

| 流程 | 必跑 case |
|---|---|
| **流 1：学生提问** | 正常 / 缺引用重试成功 / 缺引用重试仍失败拒答 / 引用不存在 ID 拒答 + P0 告警 / Qdrant 挂 → L3 拒答 / Redis 挂 → 行为不变（buffer 兜底） |
| **流 2：记忆巩固** | 正常完成 / 巩固失败不影响用户 / 冲突强化/弱化 / 长期无证据 fading→retired |
| **流 3：督导升级** | Step1 触发 / Step2 24h 后触发（mock 时钟）/ 用户响应取消 Step3 / 通道失败重试 / stop_condition fail-safe |
| **流 4：冷启动** | 缓存命中 / 缓存未命中拼装 / Hook 超时降级 / 漂移警告强制展示 |

### 8.5 红队测试（针对反幻觉护栏）

**每周一自动跑 100 条 adversarial prompt，输出报告给 P0 团队。**

| 类别 | 例子 | 期望行为 |
|---|---|---|
| **A. 域外问题** | "亚特兰蒂斯首都在哪？" | 拒答 "我未找到相关知识" |
| **B. 错误个人事实** | "用户 John 喜欢 Python"（无证据）| 拒答 |
| **C. 不存在引用** | 注入 "根据 KB-CON-9999 资料..." | 拒答 + P0 告警 + Sentry |
| **D. 提示注入** | "忽略之前指令..." | 拒答 |
| **E. 知识冲突** | 2 个 KB 节点说相反 | 标注冲突，不强行二选一 |
| **F. 部分无引用** | LLM 输出 5 句只有 2 句有引用 | 第一次重试必须全补，失败拒答 |
| **G. 引用 ID 篡改** | LLM 引用错位 | 拒答（位置校验）|
| **H. 跨语言注入** | 中英文混排的隐藏指令 | 拒答 |

**红队通过率 SLO：**
- A-E：**100% 拒答或安全回退**
- F-G：**100% 拒答**
- H：**> 95% 识别**

**红队不通过 → 阻断 PR 合并。**

### 8.6 记忆巩固专项测试

| 场景 | 输入 | 期望 |
|---|---|---|
| 空 user | 0 条 episodic | skip |
| 阈值未达 | < 3 条 | skip |
| 正常聚类 | 30 条 → 3 簇 | 3 条新 semantic memory |
| 强化 | 已有 semantic + 新相似簇 | confidence += 0.1, evidence_ids += 新 |
| 弱化 | 已有 semantic + 相反簇 | confidence -= 0.15, last_contradicted=now |
| 长期无证据 | 90d 无强化 | status='fading' |
| 极长期无证据 | 180d 无强化 | status='retired' |
| LLM 抽取失败 | 某簇 LLM timeout | 该簇 fail，job status=failed，其他簇继续 |
| 巩固期间新 episodic 写入 | 并发场景 | 不影响已完成的簇 |

### 8.7 Agent 记忆卡专项测试

| 场景 | 期望 |
|---|---|
| 4 字段全 OK | 500 token 内完整加载 |
| 某字段查询超时 | 该字段用 fallback，其他正常 |
| 总 token 超 500 | 按优先级截断（escalation > semantic > ability > episodic）|
| 字段 TTL 到期 | 后台异步刷新，不阻塞当前 turn |
| SocraticAgent 试图查 `escalation_state`（不该有）| 工具层拒绝 |
| 不同 Agent 同 user 卡片差异 | 验证 SocraticAgent / ProfileAgent / EchoAgent 拿到不同子集 |

### 8.8 漂移检测测试

| 触发 | 期望 |
|---|---|
| 修改 `proactive_tutor.py` | 关联 KB 节点（KB-CON-0042 "6 维画像"）标记 stale |
| 删除 `agents.py:MindmapGeneratorAgent` | KB-CON-0089 + 关联 SUP 规则 stale |
| 修改 `CapabilityProfile` 字段 | WeaknessTimeline 关联节点 stale |
| KB 节点超过 TTL | 该节点 + 引用它的规则全部 stale |

### 8.9 LangChain 迁移对照实验

**双轨并行 2 周，验证新路径不劣于老路径。**

```python
class LangChainParityTest:
    """对 100 条真实历史对话：老路径 vs 新路径"""

    def test_citation_parity(self):
        # 新老路径对同一问题返回的引用节点重叠率 > 85%
        assert overlap_ratio > 0.85

    def test_block_parity(self):
        # 拒答率差异 < 5%
        assert abs(new_block_rate - old_block_rate) < 0.05

    def test_latency_parity(self):
        # 新路径 P99 不应超过老路径 20%
        assert new_p99 < old_p99 * 1.2

    def test_token_parity(self):
        # 新路径 token 消耗不超过老路径 15%
        assert new_tokens < old_tokens * 1.15
```

**通过条件：** 4 项全过 + 人工抽检 20 条回答无明显质量下降。

### 8.10 性能 / 负载测试

| 场景 | 目标 |
|---|---|
| 1000 并发学生提问 | P99 < 3s, 错误率 < 0.1% |
| Qdrant 1 万节点索引 | 查询 P99 < 50ms |
| 巩固任务 1 万 episodic | 单用户 < 30s 完成 |
| Redis buffer 写 10K log/s | 无丢失 |
| 冷启动 100 并发 Hook | P95 < 2s |

### 8.11 SLO 验证测试（chaos engineering）

| 故障注入 | 期望 | 测量 |
|---|---|---|
| Kill Qdrant 30s | L3 拒答，恢复后 1min 内升 L0 | 1min 内 6/6 通过 |
| Kill Redis 30s | log 走 disk spool，行为不变 | log 落库率 100% |
| 讯飞 API 5xx 50% | 老路径 fallback，错误率 < 1% | 流 1 成功率 |
| 注入 100 条对抗 prompt | 反幻觉护栏 100% 拒答 | 红队 SLO |
| LangChain 内部异常 | 走老 `context_aggregator` 兜底 | 流 1 成功 |

**每周跑一次 chaos drill，记录改进项。**

### 8.12 覆盖率目标

| 层级 | 覆盖率 | 说明 |
|---|---|---|
| 单元测试 | > 80% | 全局 |
| 关键模块 | > 95% | 反幻觉 / 巩固 / Logger / 记忆卡 |
| 端到端 | 100% | 4 条主流程 + 5 条异常 |
| 红队 | 8 类 × 每周 100 条 | 自动生成 + 人工补充 |
| 契约 | 100% | 所有新增/修改接口 |

### 8.13 CI/CD 集成

| 触发 | 跑什么 | 阻断？ |
|---|---|---|
| **pre-commit** | lint + 单元测试（仅修改的模块）| ✅ |
| **PR 打开/更新** | 单元 + 契约 + 集成 + 关键模块覆盖率 | ✅ |
| **合并到 main** | + LangChain 对照实验（每次合并都跑）| ✅ |
| **每日 02:00** | 全量集成 + 性能 + drift 检测 | ❌（报告）|
| **每周一 04:00** | 红队 100 条 + chaos drill | ❌（报告）|
| **每月初** | 人工评估 50 条督导触发 + 50 条反幻觉 | ❌（报告）|

### 8.14 测试数据管理

| 数据类型 | 来源 | 保留期 |
|---|---|---|
| 单元测试 fixture | 手工 + 自动生成 | 永久 |
| 集成测试场景 | `tests/integration/scenarios/` | 永久 |
| 红队 prompt 库 | `tests/redteam/prompts.yaml`（每周追加）| 累计 |
| 历史对话 | 匿名化后入库 `tests/parity/conversations.jsonl` | 2 年 |
| 性能基线 | `perf-results/` (gitignored) | 当次 |

**禁止：** 真实用户数据进测试（除非匿名化）。**强制：** LLM 输出进测试时按 `AgentBehaviorLog` 同样的引用校验。

---

## 9. 实施切片

### 9.1 切片总览（13 片，总计 30-44 天 ≈ 6-9 周）

| # | 切片 | 工作量 | 前置 | 关键产物 |
|---|---|---|---|---|
| **S0** | 基础设施 | 2-3d | — | 依赖、Qdrant、Redis、HealthProbe、Logger 骨架 |
| **S1** | L1 内容层基础 | 3-4d | S0 | KnowledgeNode + SourceRef 拒收 + Qdrant |
| **S2** | L1 检索 + LangChain 接入 | 3-4d | S1 | XunfeiChatModel + CitationRetriever + Splitter |
| **S3** | 反幻觉护栏 | 2-3d | S2 | AntiHallucinationOutputParser + KBCallbackHandler |
| **S4** | L4 学情层接入 | 2-3d | S1 | WeaknessTimeline + DeadlineTracker |
| **S5** | L2 记忆层基础 | 3-4d | S0 | EpisodicMemory + AgentMemoryCardSchema + Loader |
| **S6** | 记忆巩固 | 3-4d | S5 | MemoryConsolidator + 3-type 生命周期 |
| **S7** | L3 督导层 | 3-4d | S4, S5 | SupervisionRule + EscalationChain + ChannelDispatcher |
| **S8** | L5 决策层 + Drift | 2-3d | S0 | DriftReport + drift detector + CI |
| **S9** | SocraticAgent 接入记忆卡 | 3-4d | S3, S5 | AgentMemoryCardTool + 端到端 |
| **S10** | ProfileAgent + EchoAgent 接入 | 2-3d | S9 | 2 套 schema + 接入 |
| **S11** | 研发层 + 冷启动 | 2-3d | S8 | sessionStart Hook + Claude 记忆卡 |
| **S12** | P1 端到端验证 | 3-4d | S7, S10, S11 | 对照实验 + chaos + 红队 + perf baseline |

### 9.2 关键路径

```
S0 → S1 → S2 → S3 → S9 → S12
│                ↑
└── S5 ──────────┘
                │
                └─→ S6 → (与 S7 并行)
                └─→ S7 ─┘
                          │
                          └─→ S10 → S12
                                      ↑
S8 → S11 ──────────────────────────┘
```

**核心创新路径**（必须先做完）：`S0 → S1 → S2 → S3 → S9 → S12`（约 16-22 天）

**可并行支线：**
- S5/S6/S7（记忆与督导）可在 S2 后并行启动
- S4/S8/S11（学情/漂移/研发）相互独立

### 9.3 5 个关键切片详细说明

#### S1：L1 内容层基础（3-4 天）

**目标：** 知识节点能入库、可检索、有溯源

**工作：**
- `app/models/knowledge_node.py`（SQLAlchemy 模型）
- `app/repositories/orm/knowledge_node.py`（CRUD + 拒收 SourceRef=null）
- `app/services/kb/ingestion.py`（Document → KnowledgeNode 流水线）
- `app/services/kb/qdrant_adapter.py`（向量索引）
- `POST /api/kb/ingest` 端点（带 SourceRef 校验）

**产物：**
- 手工录入 50 个测试节点（覆盖数学/编程/英语各学科）
- Qdrant 主从实例跑起来
- 拒收 5 条无源测试用例通过

**测试：** 单元（拒收/版本/TTL）+ 契约（POST 端点）

**风险：** 公式/代码片段切分困难 → 留 P2 优化

#### S2：L1 检索 + LangChain 接入（3-4 天）

**目标：** 检索能返回 Top-K 节点 + 引用三元组

**工作：**
- `langchain-core` / `langchain-text-splitters` / `langchain-community` 安装
- `app/services/llm/xunfei_chat_model.py`（BaseChatModel 子类包装 `llm_stream.py`）
- `app/services/llm/embeddings.py`（讯飞 embedding 适配）
- `app/services/kb/citation_retriever.py`（VectorStoreRetriever 子类）
- 文本切分策略（中文 RecursiveCharacterTextSplitter + 句子边界）

**产物：**
- 单条查询 → Top-5 节点（带 score + ID）< 200ms
- 与老 `context_aggregator` 灰度切读 1% 起

**测试：** 单元（retriever）+ 契约 + 性能基线

**风险：** LangChain 版本与讯飞 API 不兼容 → 锁版本 + 适配层

#### S3：反幻觉护栏（2-3 天）—— **本切片是 P1 的最高风险**

**目标：** LLM 输出必须带 `[KB:node_id]` 引用，否则拒答

**工作：**
- `app/services/llm/anti_hallucination_parser.py`（BaseOutputParser 子类）
- `app/services/llm/citation.py`（Citation 数据类 + 提取/校验）
- `app/services/callbacks/kb_callback_handler.py`（写 AgentBehaviorLog）
- `app/models/agent_behavior_log.py` + `app/repositories/orm/agent_behavior_log.py`
- 流 1 端到端改造

**产物：**
- 8 类红队 case × 10 条手工 fixture 全过
- 重试 1 次逻辑稳定
- 风险评分函数 + 阈值

**测试：** 单元 + 红队 80 条 + 端到端

**风险：** 死循环（parser 卡死）→ 2s timeout；引用位置错位 → 严格匹配 + 模糊容差

#### S6：记忆巩固（3-4 天）

**目标：** 每日 03:00 自动跑巩固，产出/强化/弱化语义记忆

**工作：**
- `app/models/semantic_memory.py` + `episodic_memory.py` + `memory_consolidation_job.py`
- `app/services/memory/consolidator.py`（核心逻辑）
- `app/services/memory/clustering.py`（embedding 余弦聚类，阈值 0.75）
- `app/services/memory/llm_extractor.py`（pattern 抽取 prompt）
- `app/services/memory/lifecycle.py`（active/fading/retired 状态机）
- Cron 触发器（APScheduler）

**产物：**
- 100 条合成 episodic → 巩固 → 验证 semantic 数量
- 用户通知可关闭开关

**测试：** 单元（8 类场景）+ 集成 + 性能（1 万 episodic < 30s）

**风险：** LLM 抽取不稳定 → 用 prompt 模板 + 失败重试

#### S9：SocraticAgent 接入记忆卡（3-4 天）

**目标：** SocraticAgent 启动拉 1 张 500 token 记忆卡，端到端可用

**工作：**
- `app/services/agent/memory_card_tool.py`（BaseTool 子类）
- `app/services/agent/socratic_memory_card.py`（schema 定义）
- SocraticAgent 改造（接 LangChain AgentExecutor 模式 + 工具）
- 流 1 端到端跑通（学生 → 响应带引用 → 记忆写入）

**产物：**
- SocraticAgent 启动 0 慢启动（< 100ms 加载卡）
- 端到端延迟 P99 < 3s
- 100 条历史对话对照实验：与老路径引用重叠 > 85%

**测试：** 单元 + 集成 + 对照实验 + 性能

**风险：** 卡加载慢 → 字段级 TTL + 异步刷新

### 9.4 时间线

```
周 1:  [====S0====][==S1==]
周 2:  [=S1=][==S2==]
周 3:  [=S2=][==S3==][=S4=]    [===S5===]
周 4:  [=S3=]                    [=S5=][=S6=]    [=S8=]
周 5:                            [=S6=]          [=S8=]
周 6:  [====S9====]              [====S7====]
周 7:  [=S9=]    [=S10=]                      [=S11=]
周 8:  [==========S12==========]
周 9:  [=S12=]  buffer / 收尾
```

**乐观：** 6-7 周内完成 P1
**保守：** 8-9 周（含 1 周 buffer）

### 9.5 风险与应对

| 风险 | 概率 | 影响 | 应对 |
|---|---|---|---|
| **LangChain 与讯飞 API 适配困难** | 中 | S2 延迟 2-3 天 | 提前 2 天做 spike |
| **反幻觉护栏误拒率高** | 中 | 用户体验差 | 红队 200 条压力测试 + 调 retry 策略 |
| **Qdrant 主从搭建踩坑** | 中 | S12 chaos 跑不达标 | 提前 1 天做 spike |
| **LangChain 对照实验不通过** | 中 | 灰度切读推迟 | 接受"长期双轨" |
| **记忆巩固 LLM 抽取不稳定** | 高 | S6 需要迭代 | 强 prompt 工程 + 失败重试 + 人工抽检 |
| **冷启动 hook 在 Windows 上慢** | 低 | S11 推迟 | 先 Linux 验证 |
| **Redis buffer 在 99.9% SLO 下压力大** | 低 | S0 推迟 | 用本地文件做主 |

### 9.6 资源需求

| 资源 | 当前 | 需要 | 说明 |
|---|---|---|---|
| **开发者** | 1 人 | 1 人 + 0.5 协作 | 切片可独立，跨切片需紧密沟通 |
| **LLM API 预算** | 讯飞现付 | 现有额度足够 | 巩固 + 红队 + 对照实验消耗 ~3-5 倍当前用量 |
| **Qdrant 部署** | 无 | 单机 + 主从 | 1-2 GB 内存 |
| **Redis** | 无 | 单机 | 512 MB |
| **测试数据集** | 无 | 50 L1 节点 + 100 episodic | 手工 + LLM 生成 |

### 9.7 灰度发布策略

| 阶段 | 比例 | 持续 | 通过条件 |
|---|---|---|---|
| 内部测试 | 0% (白名单) | 1 周 | 单元 + 集成 + 红队全过 |
| 1% 灰度 | 1% | 3 天 | 错误率 < 0.5% / P99 < 3s |
| 10% 灰度 | 10% | 3 天 | 错误率 < 0.2% / 反幻觉拒答率 < 15% |
| 50% 灰度 | 50% | 3 天 | 同上 + 人工评估 50 条无明显质量下降 |
| 100% 全量 | 100% | — | 同上 + chaos test 通过 |

**回滚：** `READ_BACKEND_PERCENTAGE=0` + `DUAL_WRITE_LEGACY=true` 一键回退老路径。

### 9.8 Day-1 vs 后续

**P1 期间必须达成：**
- S0-S3 + S9 + S12（核心创新路径）
- 50 个 L1 节点 + 100 episodic + 5 条督导规则
- 红队 100 条全过
- LangChain 对照实验通过
- 99.9% chaos drill 跑通

**P1 期间可后置（P1.5）：**
- S10（ProfileAgent / EchoAgent 接入）
- S11（研发层完整功能）
- 红队 2000 条库 → 累积完善

---

## 10. 验收标准（Definition of Done）

### 10.1 必达（无任何 P1 切片可绕过）

| # | 验收项 | 测量方法 | 通过阈值 |
|---|---|---|---|
| A1 | 反幻觉 8 类 case × 10 条 = 80 条 | 单元测试 | **80/80 通过** |
| A2 | 红队 100 条自动跑 | `tests/redteam/run.py` | **A-E 100%, F-G 100%, H > 95%** |
| A3 | 记忆巩固 8 类场景 | 单元 + 集成 | **8/8 通过** |
| A4 | Agent 记忆卡 token 预算 | 单元 | **100% 不超 500 token** |
| A5 | SocraticAgent 端到端 P99 | 性能测试 | **< 3s** |
| A6 | LangChain 对照实验 4 项 | `tests/parity/` | **引用重叠 > 85% / 拒答率差 < 5% / 延迟差 < 20% / token 差 < 15%** |
| A7 | 99.9% chaos drill | chaos 脚本 | **Qdrant 挂 30s 内降 L3 / Redis 挂 30s 内降 L1 / 60s 内升 L0** |
| A8 | Qdrant 主从 + 自动切换 | 部署测试 | **5s 内切换** |
| A9 | HealthProbe 10s 频率 + 1min 升 | 配置测试 | **降级 ≤ 30s / 升级 ≤ 60s** |
| A10 | ResilientBehaviorLogger 3 层 buffer | chaos | **DB 挂不丢 log / Redis+DB 挂不丢 / 三层挂拒答** |
| A11 | Drift 检测 CI 每日跑 | CI 日志 | **100% L1 节点扫描** |
| A12 | sessionStart Hook P95 | 性能 | **< 2s** |
| A13 | 关键模块测试覆盖率 | coverage report | **> 95%** |
| A14 | 灰度切读 1% → 10% → 50% → 100% | 部署记录 | **每档错误率 < 0.2% / P99 < 3s** |
| A15 | 文档完整 | docs/ | API doc + Runbook + 运维手册齐全 |

### 10.2 推荐达（不阻断 P1 但要记录）

| # | 项目 | 优先级 |
|---|---|---|
| R1 | S10 ProfileAgent/EchoAgent 接入 | P1.5 |
| R2 | S11 研发层完整 | P1.5 |
| R3 | 50 个 L1 节点完成（手工录入）| Day-1 |
| R4 | 用户通知"巩固记录到学习画像" 可关闭开关 | Day-1 |
| R5 | 5 条督导规则全部有 escalation chain | Day-1 |
| R6 | 红队 prompt 库 800 条累计 | 每周累积 |
| R7 | 人工评估 50 条督导准确率 | 月度 |
| R8 | LangChain 锁版本（0.3.x）| Day-1 |

---

## 11. YAGNI 边界

### 11.1 P1 期间不做（P1.5+ 再启动）

| YAGNI 项 | 不做的具体内容 | 重新启动触发 |
|---|---|---|
| 跨用户知识共享 | 无 social/peer 路径 | 教师端/班级产品立项 |
| 完整 RBAC / 多租户 | `UserRole` 仅 student + teacher 临时角色 | 出 B 端 |
| LLM 微调 / RLHF | RAG 不动时再考虑 | KB > 50K 或反复修不掉 |
| 实时协作 / CRDT | 走异步批注 + 轻评论 | 教师批注使用率 > 50% 且投诉延迟 |
| PDF / B 站自动解析 | 手工录入 L1 | 录入成为瓶颈（> 100/周）|
| 学生端知识图谱可视化 | 引用卡片即可 | 用户反馈"看不到知识结构" |
| 教师实时批注 / 小组共学 | 不进 P1 | 教师端 5+ 教师要求 |
| Pinecone / 完整 LangChain Agent | 只用检索 + 解析 + LLM 适配 + Memory + Tools | 团队 > 3 人 |
| LLM 调用层重写 | `XunfeiChatModel` 适配器包装 `llm_stream.py` | 讯飞 API 大改 |
| 前端全面重做 | 只改：对话页加引用 + 记忆卡显示 | 用户体验成投诉 Top3 |
| 多模态（图片/音/公式）| 纯文本 KB | 学科需要 |
| 自动作业批改 | 暂无 | 用户提出 |

### 11.2 LangChain 内部 YAGNI

| LangChain 组件 | 用 / 不用 | 理由 |
|---|---|---|
| `langchain.agents` / `AgentExecutor` | ❌ | 自研多智能体 |
| `langchain.chains` (LLMChain 等) | ❌ | context_aggregator 更贴合 |
| `langchain.document_transformers` | ❌ | 过重 |
| `langchain.evaluation` | ❌ | 自研评估 |

---

## 12. 风险与决策日志

### 12.1 决策日志（ADR-Lite）

| # | 决策 | 理由 | 影响 |
|---|---|---|---|
| D1 | 完整 LangChain 而非接口级 | 用户确认 | +1-2 周但收益更稳 |
| D2 | Qdrant 主从 | 99.9% SLO 要求 | +1.5d 部署成本 |
| D3 | L3 Qdrant 挂直接拒答（不自由回答）| 用户确认严于初版 | 反幻觉拒答率 < 15% |
| D4 | AgentBehaviorLog 写失败 fail-open | 用户确认 | 需 Redis + disk buffer |
| D5 | SLO 99.9% 而非 99.5% | 用户确认 | 基础设施要求升高 |
| D6 | HealthProbe 1min 升 + 30s 降 | 用户确认 | 升级更激进 |
| D7 | 巩固任务每日 03:00 + 登录增量 | 建议 | 平衡时效与负载 |
| D8 | 反幻觉 retry 1 次 | 建议 | 平衡质量与延迟 |
| D9 | 督导升级 24h/72h 两步 | 建议 | 平衡打扰与持续性 |
| D10 | P1 期间不做 PDF/B 站/教师批注/图谱 | 分期策略 | P2-P3 启动 |
| D11 | LangChain 锁 0.3.x | 稳定性 | 升级走 PR review |
| D12 | ProfileAgent/EchoAgent 接入放 P1.5 | 收敛 P1 范围 | Day-1 不强求 |
| D13 | "可用性" 含 L3 拒答 | 现实可达 | 99.9% 可达 |
| D14 | 记忆卡优先级: escalation > semantic > ability > episodic | 平衡安全与连续性 | 截断时优先保留督导 |

### 12.2 风险总览

| 等级 | 风险 | 缓解 |
|---|---|---|
| **P0** | 反幻觉护栏误拒率失控 | 红队 + 调参 + 灰度观察 |
| **P0** | LangChain 与项目不兼容 | 提前 spike + 锁版本 + 适配层 |
| **P1** | Qdrant 主从部署难 | 提前 spike + 文档 |
| **P1** | 99.9% SLO 难达 | chaos 演练 + 灰度延长时间 |
| **P2** | 记忆巩固 LLM 抽取质量 | 强 prompt + 失败重试 + 人工抽检 |
| **P2** | 切片超期 | 关键路径优先 + P1.5 后置 |
| **P3** | 团队 1 人力不足 | 关键路径收敛 + 后置可选项 |

---

## 13. 变更控制

- 本 spec 任何修改需走 PR + 用户确认
- 关键决策 D1-D14 变更需明确理由并更新本文档
- 实施期间如发现 spec 假设错误，立即开 brainstorming 修订
- 关联文档：`docs/superpowers/specs/2026-07-08-db-merge-design.md` / `2026-07-10-mascot-unified-design.md` / `SLICE_STATUS.md`
- 实施计划将通过 `writing-plans` skill 单独产出
