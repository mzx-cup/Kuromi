# tests/smoke/SMOKE_TEST_REPORT.md

## M1 Smoke Test Report — 2026-07-29

**pytest 结果**: `10 passed in 28.63s`（`pytest tests/smoke/test_e2e_apis.py -v -m smoke --timeout=180`）

前置条件：已释放 `xingshi.db` 上的 SQLite 锁（残留的 `python start_server.py`，PID 24028），
并启动 Qdrant v1.9.0（`docker compose -f docker-compose.dev.yml up -d qdrant-master`，`/healthz` 通过）。

> **重要**：10/10 "PASS" 指断言通过，不等于接口返回 200。M1 阶段的断言
> 有意容忍 4xx/5xx（见 `test_e2e_apis.py` 顶部注释）。下表的"实际状态码"
> 由独立探针单独采集，用于区分"真正成功"和"按 spec 容忍的失败"。

| #  | API                    | 状态 | 实际状态码 | 响应时间 |
|----|------------------------|------|-----------|---------|
| 01 | register/login         | ✅   | 200       | 687ms   |
| 02 | dashboard/summary      | ⚠️   | 404       | 419ms   |
| 03 | v2/chat socratic       | ⚠️   | 422       | 434ms   |
| 04 | course/brainstorm      | ⚠️   | 422       | 440ms   |
| 05 | course/bundle/stream   | ⚠️   | 422       | 450ms   |
| 06 | learning-path          | ⚠️   | 404       | 436ms   |
| 07 | teacher/ai-suggestions | ⚠️   | 404       | 487ms   |
| 08 | agents/catalog         | ✅   | 200       | 575ms   |
| 09 | kb/ingest qdrant       | ⚠️   | 500       | 454ms   |
| 10 | safety/jailbreak block | ⚠️   | 422       | 433ms   |

**结论**: 断言层面 10/10 通过，0/10 待修复（无 ERROR、无 17s 延迟）。
接口层面仅 2/10 返回 200，其余 8 项为 M1 阶段按 spec 容忍的 4xx/5xx。

### 值得跟进的两个具体问题

1. **`student_id` 类型不匹配导致 422（#03/#04/#05/#10）**
   `/api/login/guest` 返回的 `userId` 是整数（如 `84`），而 v2 系列接口的
   Pydantic 模型要求 `student_id` 为字符串：
   `{"type":"string_type","loc":["body","student_id"],"msg":"Input should be a valid string","input":84}`
   这 4 项全部因同一处类型契约不一致被挡在业务逻辑之外，并非引擎本身不稳定。

2. **`kb/ingest` 的 500 与 Qdrant 无关（#09）**
   Qdrant 已连通（`/healthz` 通过，`/collections` 返回 `ok`）。500 的真实原因是
   SQLite 写入冲突：`sqlite3.IntegrityError: UNIQUE constraint failed: knowledge_node.id`
   （rid `af47fd35b2e2`）。Task 9 排查 Qdrant 时不应被这个 500 误导。

### 环境备注

- Qdrant 容器在 `docker ps` 中显示 `unhealthy`，但这是 compose healthcheck 的缺陷：
  探针用 `wget`，而 `qdrant/qdrant:v1.9.0` 镜像里没有该二进制
  （`exec: "wget": executable file not found in $PATH`）。HTTP API 本身正常。
- `qdrant-client` 1.18.0 与 server 1.9.0 存在版本告警（major 不匹配），目前仅告警。
