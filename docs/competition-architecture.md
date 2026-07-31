# 比赛架构图说明

> 给答辩评委看的"系统长什么样"一页纸.

## 1. 6 层架构

```
┌──────────────────────────────────────────────────────────┐
│ L1  体验层      html/*.html  +  js/*.js  +  css/*.css   │
│     (原生 HTML/JS, 不引前端框架)                          │
├──────────────────────────────────────────────────────────┤
│ L2  API 层      app/api/*.py  (FastAPI routers)          │
│     /api/auth  /api/profile  /api/teacher  /api/health   │
├──────────────────────────────────────────────────────────┤
│ L3  教学编排层  app/services/tutor_engine/*              │
│     ContextAggregator → LLM → HallucinationGuard          │
│                       → LinkRecommender → ResponseComposer│
├──────────────────────────────────────────────────────────┤
│ L4  智能体层    app/agents/*  +  app/agents/io_schema.py  │
│     Profiler / Planner / Socratic / Recommend / Audit    │
│     通信协议: AgentEnvelope (trace_id + role + payload)  │
├──────────────────────────────────────────────────────────┤
│ L5  数据与记忆层 app/services/repository/* + db.py       │
│     + agents.py (长记忆) + Qdrant (向量)                 │
├──────────────────────────────────────────────────────────┤
│ L6  外部服务层  app/services/llm/*  +  app/services/kb/* │
│     + app/services/tts/* + app/services/asr/* + 视频生成  │
└──────────────────────────────────────────────────────────┘
```

## 2. 边界原则

- **L1 ↔ L2**: 前端只调 REST/JSON, 不直接 import 后端模块.
- **L2 ↔ L3**: API 路由只编排"输入→引擎→输出", 不含业务规则.
- **L3 ↔ L4**: 引擎只调 AgentEnvelope, 不调 LLM 直连.
- **L4 ↔ L4**: 同层智能体之间只能通过 Envelope 通信, 禁止共享可变状态.
- **L4 ↔ L5**: 智能体不直连 ORM, 走 Repository.
- **L5 ↔ L6**: 外部服务走 Provider/Adapter, 统一超时/重试/降级.

## 3. 为什么这样划

- **可演示性**: 任一层独立降级 (LLM 超时 → fallback 种子响应, 不阻断主链).
- **可答辩性**: 每层有清晰职责, 评委能逐层追问.
- **可追溯性**: trace_id 贯穿 L2→L3→L4→L5→L6, 出问题能秒级定位.
- **可扩展性**: 改 LLM 厂商只动 L6, 加新智能体只动 L4, 不影响其他层.

## 4. 不做什么 (来自设计文档 §14)

- 不迁移 React/Vue 等前端框架 (L1 保持原生)
- 不拆微服务 (L1-L6 仍在同一进程)
- 不补全未演示的功能到生产级别
- 不在答辩现场跑耗时视频生成
- 不在比赛前轻易删除所有旧 API 或数据兼容逻辑
