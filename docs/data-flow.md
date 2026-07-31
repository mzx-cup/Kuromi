# 数据流图 (演示主链)

> 一图说明"用户点一下鼠标, 哪些模块被调用, 数据如何流过".

## 1. 主链时序

```
用户浏览器           L1 体验层         L2 API 层           L3 编排层        L4 智能体层       L5 数据层        L6 外部服务
    │                  │                  │                  │                 │                │                │
    │ 1. 点击登录       │                  │                  │                 │                │                │
    ├─────────────────►│ POST /api/auth   │                  │                 │                │                │
    │                  │  /login          │                  │                 │                │                │
    │                  ├─────────────────►│ auth.login()     │                 │                │                │
    │                  │                  ├──────────────────► UserRepo       │                │                │
    │                  │                  │ ◄─────────────── {user,role}     │                │                │
    │                  │ ◄─────────────── {access_token}    │                 │                │                │
    │ ◄─────────────── {token, user}      │                  │                 │                │                │
    │                  │                  │                  │                 │                │                │
    │ 2. 进入 personal  │                  │                  │                 │                │                │
    │ GET /api/profile/123                │                  │                 │                │                │
    │                  ├─────────────────►│ profile.get()    │                 │                │                │
    │                  │                  ├──────────────────► DemoRepository  │                │                │
    │                  │                  │ ◄──────────────── {radar, cards} │                │                │
    │ ◄─────────────── JSON              │                  │                 │                │                │
    │                  │                  │                  │                 │                │                │
    │ 3. 弱点诊断       │                  │                  │                 │                │                │
    │ GET /api/mascot/capability/123      │                  │                 │                │                │
    │                  ├─────────────────►│ mascot.get()     │                 │                │                │
    │                  │                  ├─────────────────►│ engine.decide()│                │                │
    │                  │                  │                  ├────────────────► Profiler.env   │                │
    │                  │                  │                  │ ◄─────────────── AgentEnvelope   │                │
    │                  │                  │                  │                 │                │                │
    │                  │                  │                  │                 │                │                │
    │ 4. 苏格拉底对话   │                  │                  │                 │                │                │
    │ POST /api/v2/chat│                  │                  │                 │                │                │
    │ {msg:"勾股定理"} │                  │                  │                 │                │                │
    │                  ├─────────────────►│ chat.handler()   │                 │                │                │
    │                  │                  ├─────────────────►│ engine.decide()│                │                │
    │                  │                  │                  ├────────────────► Socratic.env   │                │
    │                  │                  │                  │                 ├──────────────►│ LLM (ark/qwen)│
    │                  │                  │                  │                 │ ◄────────────── {answer}        │
    │                  │                  │                  │                 ├──────────────►│ KB (Qdrant)   │
    │                  │                  │                  │                 │ ◄────────────── {citations}     │
    │                  │                  │                  │ ◄─────────────── AgentEnvelope   │                │
    │                  │                  │ ◄─────────────── {answer, trace}  │                │                │
    │ ◄─────────────── JSON              │                  │                 │                │                │
    │                  │                  │                  │                 │                │                │
    │ 5. 路径调整       │                  │                  │                 │                │                │
    │ GET /api/learning-path/123          │                  │                 │                │                │
    │                  ├─────────────────►│ path.get()       │                 │                │                │
    │                  │                  ├─────────────────►│ engine.decide()│                │                │
    │                  │                  │                  ├────────────────► Planner.env    │                │
    │                  │                  │                  │ ◄─────────────── {nodes}        │                │
    │                  │                  │ ◄─────────────── {nodes, trace}  │                │                │
    │ ◄─────────────── JSON              │                  │                 │                │                │
    │                  │                  │                  │                 │                │                │
    │ 6. 微练习         │                  │                  │                 │                │                │
    │ POST /api/quiz/grade               │                  │                 │                │                │
    │                  ├─────────────────►│ quiz.grade()     │                 │                │                │
    │                  │                  ├─────────────────►│ engine.decide()│                │                │
    │                  │                  │                  │                 ├──────────────►│ Mastery.save()│
    │                  │                  │                  │ ◄─────────────── {delta}         │                │
    │ ◄─────────────── {correct, delta}  │                  │                 │                │                │
    │                  │                  │                  │                 │                │                │
    │ 7. 掌握度变化     │                  │                  │                 │                │                │
    │ GET /api/profile/123/mastery-diff  │                  │                 │                │                │
    │                  ├─────────────────►│ profile.diff()   │                 │                │                │
    │                  │                  ├─────────────────►│ DemoRepository  │                │                │
    │                  │                  │ ◄──────────────── {items, before, after}        │                │
    │ ◄─────────────── JSON              │                  │                 │                │                │
    │                  │                  │                  │                 │                │                │
    │ 8. 教师观察       │                  │                  │                 │                │                │
    │ GET /api/teacher/dashboard/observation (教师 token)  │                │                │                │
    │                  ├─────────────────►│ teacher.obs()    │                 │                │                │
    │                  │                  ├─────────────────►│ Recommend.env   │                │                │
    │                  │                  │ ◄─────────────── {suggestions}   │                │                │
    │ ◄─────────────── JSON              │                  │                 │                │                │
    ▼                  ▼                  ▼                  ▼                 ▼                ▼                ▼
```

## 2. trace_id 串联

`lp_<12hex>` 在第 1 步 (登录) 时生成, 贯穿主链, 每步记入 `AgentEnvelope.trace_id` 与
`LivePathResult.steps[].trace_id`. 失败时 `fallback=True`, 现场可调出 trace 回放.

## 3. 失败回退位置

| 失败点 | 回退 | 主链是否中断 |
|---|---|---|
| LLM (L6) | 种子响应 + `fallback=True` | 不中断 |
| KB (L6) | 结构化 SQL 检索, 引用列表空 | 不中断 |
| Sandbox (L6) | 比赛模式下 `competition_mode_disabled` | 不中断 |
| DB (L5) | 静态种子数据 + `fallback=True` | 不中断 |
| 智能体 (L4) | 空 payload + `fallback=True` | 不中断 |
| API (L2) | 4xx/5xx 错误码 + trace_id | 主链中断, 提示用户 |
