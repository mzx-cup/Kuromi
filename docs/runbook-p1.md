# P1 Runbook — Production Operations

> **Audience:** on-call engineers and SREs responsible for the
> Kuromi / star-learn production deployment after the S1–S12
> rollout (P1 close-out). Read this before going on-call.
>
> **Scope:** this runbook covers everything the original spec §B6
> step 5 calls out — services, health, anti-hallucination, memory
> consolidation, supervision, agent cards, drift detection, Claude
> cold-start, fault handling, and rollback. If you have to act in
> the next 5 minutes, jump to [§10 Incident quick-cards](#10-incident-quick-cards).

---

## Table of contents

1. [Services & top-level architecture](#1-services--top-level-architecture)
2. [Health checks & on-call dashboards](#2-health-checks--on-call-dashboards)
3. [Anti-hallucination procedures](#3-anti-hallucination-procedures)
4. [Memory consolidation (episodic → semantic)](#4-memory-consolidation-episodic--semantic)
5. [Supervision & escalation](#5-supervision--escalation)
6. [Agent cards & loader](#6-agent-cards--loader)
7. [Drift detection](#7-drift-detection)
8. [Claude cold-start](#8-claude-cold-start)
9. [Fault handling & rollback](#9-fault-handling--rollback)
10. [Incident quick-cards](#10-incident-quick-cards)
11. [Appendix A — Chaos drill](#appendix-a--chaos-drill)
12. [Appendix B — Red-team drill](#appendix-b--red-team-drill)

---

## 1. Services & top-level architecture

| Service                | Container / process         | Port(s)     | Owned by            |
|------------------------|-----------------------------|-------------|---------------------|
| FastAPI app (`main`)   | `star-learn-api`            | 8080        | app team            |
| Qdrant (vector store)  | `qdrant-master`             | 6333, 6334  | platform team       |
| Redis (cache + cron)   | `redis-master`              | 6379        | platform team       |
| MySQL / SQLite (L1)    | `xingshi_v2` (file) or RDS  | 3306        | data team           |
| SessionStart hook      | in-process (Claude)         | —           | platform team       |
| Drift reporter         | APScheduler (in-process)    | —           | platform team       |
| Memory consolidator    | APScheduler (in-process)    | —           | platform team       |

Container names match the chaos drill defaults; override via env
(`QDRANT_CONTAINER`, `REDIS_CONTAINER`) if your stack uses different
naming.

### 1.1 Process supervision

- `main.py` runs under `uvicorn` with `--workers 2` behind nginx.
- APScheduler runs **in the API process** (not a sidecar) so that
  consolidation + drift share the L1 connection pool. Restarting
  the API also restarts the schedulers.
- The SessionStart hook is **in-process** and is given a hard 5s
  cap (see [§8](#8-claude-cold-start)).

### 1.2 Configuration

- All env vars are read through `app.core.config` (Pydantic Settings).
- Feature flags (read-only from prod):
  - `USE_LANGCHAIN_SOCRATIC` — opt-in dual-rail Socratic path (default off).
  - `READ_BACKEND_PERCENTAGE` — 0=legacy, 100=orm, 50=canary.
  - `DUAL_WRITE_LEGACY` — when false, writes that would touch
    `local_storage.json` instead **raise** so a misconfigured deploy
    fails loudly rather than silently drift.
- Rotation: secrets live in the platform vault; the API reads them
  on boot, never on the request path.

---

## 2. Health checks & on-call dashboards

### 2.1 Liveness / readiness

```
GET /healthz    # 200 if the API process is up
GET /readyz     # 200 if DB + Qdrant + Redis are reachable
```

- `/readyz` performs a no-op query against each dependency.
- Returns 503 with a JSON body listing which dependency failed.

### 2.2 Dashboards (Grafana)

| Dashboard                    | What to look at                              |
|------------------------------|----------------------------------------------|
| `star-learn/api-overview`    | p50/p99 latency, 5xx rate, `/readyz` failures |
| `star-learn/qdrant`          | collection size, query p99, recall@10        |
| `star-learn/redis`           | hit ratio, evictions, command p99            |
| `star-learn/memory`          | episodic row count, semantic cards, consolidator runs |
| `star-learn/drift`           | drift_reports row count (last 24h)           |

### 2.3 Alerts (PagerDuty → on-call rotation)

| Alert                          | Threshold                                | Severity  |
|--------------------------------|------------------------------------------|-----------|
| `api-5xx-spike`                | > 2% 5xx for 5 min                       | P3        |
| `qdrant-query-latency`         | p99 > 800ms for 10 min                   | P3        |
| `redis-down`                   | PING fails 3× in a row                   | P2        |
| `readyz-fail`                  | any 503 from `/readyz` for > 2 min        | P2        |
| `consolidator-failed`          | any run exits non-zero                   | P3        |
| `drift-reports-spike`          | > 50 new rows in 1 hour                  | P3        |
| `langchain-parity-regression`  | any of the 4 metrics out of spec         | P2        |
| `chaos-drill-fail`             | any scenario exits non-zero              | P4 (next business day) |

---

## 3. Anti-hallucination procedures

### 3.1 The four-layer defence

1. **L1 — KB grounding.** Every answer path runs through
   `KBCallbackHandler`, which attaches the top-k retrieved KB nodes
   to the LLM prompt. The answer cannot reference knowledge outside
   the retrieved set.
2. **L2 — `AntiHallucinationOutputParser`.** After generation, the
   parser extracts `[KB:…]` citations and re-checks them against the
   retrieved set. Unbacked claims are blocked.
3. **L3 — `produce_socratic_response` retry loop.** On parser
   failure, a single retry is issued with a stricter instruction.
   If that also fails, the answer is **blocked** with
   `block_reason = "anti_hallucination_violation"` (or
   `vector_store_unavailable` if the L1 KB lookup errored out).
4. **L4 — Red-team drill.** 213 prompts across 8 categories are
   re-run nightly; any category that drops below its per-class
   threshold pages on-call (see [Appendix B](#appendix-b--red-team-drill)).

### 3.2 What to do when a category starts failing

1. Open `tests/redteam/report.json` — the failing category is at
   the top of `evaluation.by_category`.
2. Look at the `counts` dict:
   - `failed` rising → the pipeline itself is throwing; check
     `/readyz` and recent deploys.
   - `safe_fallback` (or `blocked`) dropping → the LLM is
     bypassing the parser. This is **never** expected; treat as
     a regression and roll back (see [§9](#9-fault-handling--rollback)).
3. If `failed` is non-zero, capture the first failing prompt and
   reproduce locally with `python tests/redteam/run.py --prompts
   tests/redteam/prompts.yaml`.

### 3.3 When to widen the parser

Do **not** widen the parser to "make tests pass". The red-team
suite is a regression net, not a checklist. If a new prompt
pattern needs handling, the right move is:

1. File a P2 ticket with the prompt and the failure mode.
2. Extend the parser in `app.services.llm.anti_hallucination`
   with a unit test that fails first.
3. Re-run the full red team (must still pass with the new
   pattern, not just the new prompt).

---

## 4. Memory consolidation (episodic → semantic)

### 4.1 Cadence

- **Daily 03:00 (server local time):** `consolidate_episodes`
  runs via APScheduler.
- **Hourly 00:** TTL check — episodes older than 90 days that
  were never reinforced are eligible for archival.
- **On-demand:** via `POST /admin/memory/consolidate` (gated to
  the on-call role).

### 4.2 Pipeline

```
[EpisodicMemory rows, last 24h]
    → cluster by (user_id, topic embedding)
    → for each cluster: LLM extract_pattern (with 5s timeout)
    → if pattern found: upsert SemanticMemory row
    → mark cluster rows as consolidated
```

Failures are isolated per-cluster: one bad cluster does not
abort the whole run.

### 4.3 What to do when consolidator fails

1. Check `star-learn/memory` dashboard — the `consolidator-failed`
   alert tells you the run exit code.
2. Inspect the last 100 lines of `app.log` for `consolidator`
   entries. Common root causes:
   - LLM timeout (cluster size too large) → check
     `EXTRACT_PATTERN_TIMEOUT_S` (default 5s).
   - DB write contention → check the L1 connection pool.
3. If a single cluster keeps failing, exclude it via the
   `MEMORY_CLUSTER_DENYLIST` env var (comma-separated cluster
   ids) and file a ticket.

### 4.4 Memory card lifecycle

```
pending → active → reinforcing → reinforced
                       ↓
                    stale (TTL > 90d, never reinforced)
                       ↓
                    archived
```

Transitions are **only** valid in the directions shown. Any
unexpected transition logs a `memory.invalid_transition` warning
and pages P3.

---

## 5. Supervision & escalation

### 5.1 The chain

Each agent emits a `SupervisionEvent` after every turn. Events
flow through:

```
Agent → SupervisionEventBus → ChannelRetry → EscalationChain → Handler
```

Channels in priority order:

1. `inproc` (in-process, for tests)
2. `stdout` (JSON line, for log aggregation)
3. `webhook` (HTTPS POST, primary prod sink)
4. `email` (last resort, slowest)

If a channel fails, `ChannelRetry` retries with exponential
backoff (1s, 2s, 4s, 8s — max 4 attempts) before giving up and
moving to the next channel in the chain.

### 5.2 Escalation tiers

| Tier | When                                          | Handler                          |
|------|-----------------------------------------------|----------------------------------|
| 0    | Event is informational                        | log only                         |
| 1    | Event is a warning                            | log + dashboard                  |
| 2    | Event is a soft error (recoverable)           | log + dashboard + on-call notify |
| 3    | Event is a hard error (user-impacting)        | tier 2 + PagerDuty page          |
| 4    | Event is a safety / hallucination violation   | tier 3 + immediate freeze        |

Tier 4 is the **only** path that auto-freezes new sessions;
on-call can unfreeze via `POST /admin/agents/unfreeze`.

### 5.3 What to do when a tier-3 alert fires

1. Acknowledge in PagerDuty (stops the page from cascading).
2. Open the event in the supervision dashboard; check
   `event.tier` and `event.handler_path`.
3. If the handler path shows repeated channel failures,
   check the upstream webhook (usually the
   `star-learn-supervision-sink` service).
4. Capture the offending `event_id`; it's the correlation key
   in the log.

---

## 6. Agent cards & loader

### 6.1 What is an agent card?

A JSON document (~500 tokens) that gives an agent:

- identity (role, persona, allowed tools)
- KB subset to consult
- supervision tier
- memory scope

Cards live in `prompts/agent_cards/*.json` and are loaded by
`MemoryCardLoader.load(agent_id)`.

### 6.2 The loader contract

- **TTL cache** (default 5 min) — the loader never re-reads the
  same card more than once per TTL window per process.
- **Field-level timeouts** (250ms per field) — a slow field
  raises `CardLoadTimeout` and the loader returns a degraded
  card with the missing field defaulted to a safe value.
- **Priority truncation** — if a card is over the 500-token
  budget, fields are dropped in this order: `examples`,
  `persona_notes`, `tool_descriptions`, `kb_subset`.

### 6.3 Failure modes

| Symptom                          | Likely cause                  | Fix                           |
|----------------------------------|-------------------------------|-------------------------------|
| All agents fall back to default  | loader can't find card files  | check `prompts/agent_cards/`  |
| Slow agent boot (>5s)            | field-level timeouts firing   | raise `CARD_FIELD_TIMEOUT_MS` |
| Card content looks stale         | TTL cache not invalidating    | restart API (cache is in-proc) |

The loader logs a **warning** on every call (intentional
reminder that the call costs at least one DB round-trip). If
this becomes a hot path, the right fix is to widen the TTL, not
to silence the warning.

---

## 7. Drift detection

### 7.1 Two drift kinds

- **`file_hash`** — every KB node whose `source_reference`
  starts with `file:` is re-hashed on a schedule. If the
  underlying file's content has changed (mtime newer than
  the recorded hash), a drift row is written.
- **`ttl`** — every semantic-memory row that hasn't been
  reinforced in > 90 days is flagged.

### 7.2 Schedule

- APScheduler cron: every 6 hours (00:00, 06:00, 12:00, 18:00).
- Manual: `python scripts/drift_detector.py [--since-hours 24]`.

### 7.3 What to do when drift reports spike

1. Open `tests/drift/report.json` (or the most recent
   `perf-results/drift-*.json`).
2. Group by `kind`:
   - `file_hash` spike → a recent deploy touched source
     documents. Confirm the drift is **expected** (e.g. a
     knowledge base update) and mark the rows resolved.
   - `ttl` spike → agents are not reinforcing the affected
     cards. Check supervision tier and recent
     `SupervisionEvent` activity for the affected agents.
3. If neither, check whether the cron itself failed (look for
   `drift.detector.error` in the logs).

---

## 8. Claude cold-start

### 8.1 The SessionStart hook

The hook is in-process and runs at the start of every Claude
session. It:

1. Reads the agent card for the requested agent.
2. Subscribes to the supervision bus.
3. Hydrates the in-process TTL cache for that agent.

### 8.2 The 5s budget

If the hook exceeds 5s, the agent loop **degrades** rather than
blocks:

- Step 1 and 2 are mandatory — they are local and never
  time out under normal conditions.
- Step 3 is best-effort — if it stalls, the loop continues
  with an empty cache. The next call to `MemoryCardLoader.load`
  re-runs step 3 in the background and the cache warms up.

### 8.3 What to do when cold start is slow

1. Check `star-learn/api-overview` for the
   `claude.cold_start_seconds` metric. Healthy: < 1.0s.
2. If it's > 5s, the 5s budget is being hit. Inspect the
   loader warning log (see [§6.3](#63-failure-modes)).
3. If it's > 30s, the loader is likely waiting on a stuck
   DB query — check the L1 connection pool.

### 8.4 Chaos drill (optional)

The chaos drill (`scripts/chaos_drill.py`) has a
`session_start_hook_timeout` scenario that simulates a hung
hook. Run with `CHAOS_HOOK_DELAY_S=10 python scripts/chaos_drill.py`
to exercise the timeout fallback in a staging environment.

---

## 9. Fault handling & rollback

### 9.1 The one-button rollback

The deployment system records the last 5 release SHAs. To
roll back:

```bash
# See what's live
deploy status prod

# Roll back to the previous release
deploy rollback prod
```

Rollback does **not** require a database migration. Migrations
are forward-only; if a rollback would require a schema change,
the deploy is **blocked** and the on-call must escalate.

### 9.2 Feature flags as a softer rollback

Most regressions can be defused without a full rollback by
toggling a flag. The supported flags and their defaults are
listed in [§1.2](#12-configuration). To toggle:

```bash
# Disable the LangChain Socratic path
deploy env set USE_LANGCHAIN_SOCRATIC=0

# Pin reads to legacy backend
deploy env set READ_BACKEND_PERCENTAGE=0

# Re-enable
deploy env set USE_LANGCHAIN_SOCRATIC=1
deploy env set READ_BACKEND_PERCENTAGE=100
```

Toggles take effect within 30s (env-refresh interval).

### 9.3 When rollback won't help

Some classes of bug are **not** fixable by rolling back:

- DB migrations that delete data. (Forward-only; the
  affected rows must be re-imported from backup.)
- LLM-side model changes by the upstream provider.
- KB corruption (e.g. a bad import that overwrote nodes).
  In this case, the recovery is to restore from the
  `kb-snapshots/` S3 bucket.

### 9.4 Postmortem

Every P2 or higher incident gets a postmortem within 5
business days. Template lives at
`docs/postmortem-template.md` (filled in for each incident).

---

## 10. Incident quick-cards

### 10.1 "LLM is hallucinating"

1. Stop the bleed: `deploy env set USE_LANGCHAIN_SOCRATIC=0`
   to force the legacy path.
2. Check `tests/redteam/report.json` — find the category.
3. If you can reproduce locally, run:
   `python tests/redteam/run.py --prompts tests/redteam/prompts.yaml`.
4. File a P2; do **not** widen the parser (see [§3.3](#33-when-to-widen-the-parser)).

### 10.2 "Qdrant is down"

1. Check `/readyz` — should return 503 with `qdrant: down`.
2. The L3 path is expected to **refuse** during the outage;
   this is by design (block_reason: `vector_store_unavailable`).
3. Restart Qdrant: `docker restart qdrant-master`.
4. Watch the `qdrant-query-latency` dashboard; recovery should
   be < 60s.
5. Once recovered, verify with: `python scripts/chaos_drill.py --scenario kill_qdrant_30s`.

### 10.3 "Redis is down"

1. `/readyz` returns 503 with `redis: down`.
2. The cache layers fall through to the slow path (DB lookup);
   latency goes up, but **availability is preserved**.
3. Restart Redis: `docker restart redis-master`.
4. The cache rewarms within ~5 min (one TTL cycle).

### 10.4 "Consolidator failed"

1. Check `app.log` for `consolidator` entries.
2. If the failure is one cluster, denylist it:
   `deploy env set MEMORY_CLUSTER_DENYLIST=cluster-id-here`.
3. If the failure is systemic, pause the cron:
   `deploy env set MEMORY_CONSOLIDATOR_ENABLED=0`.
4. The next run will pick up the paused backlog.

### 10.5 "Tier-3 supervision page"

1. Acknowledge in PagerDuty.
2. Open the supervision dashboard; find the `event_id`.
3. Check `event.handler_path` — repeat failures point to a
   dead webhook sink.
4. If the sink is the issue, fail over:
   `deploy env set SUPERVISION_WEBHOOK_URL=<new-url>`.

### 10.6 "Parity regression"

1. Open the most recent `tests/parity/langchain_parity.py` report
   in CI (or run it locally).
2. Identify which of the 4 metrics regressed:
   - citation overlap < 0.85
   - block diff > 0.05
   - latency p99 > legacy * 1.20
   - token ratio > 1.15
3. If only the LangChain path is affected, disable it:
   `deploy env set USE_LANGCHAIN_SOCRATIC=0` and re-run
   parity in 1h to confirm legacy is still healthy.
4. File a P2; the parity suite is the regression net for
   the Socratic refactor.

### 10.7 "Drift spike"

1. Open the most recent `perf-results/drift-*.json`.
2. Group by `kind` (see [§7.3](#73-what-to-do-when-drift-reports-spike)).
3. For `file_hash` — confirm the changes are expected and
   mark the rows resolved.
4. For `ttl` — investigate why the affected cards aren't
   being reinforced (usually a supervision tier misconfig).

---

## 11. 灰度发布（gray rollout）

P1 的 SocraticAgent 重构通过环境变量 `USE_LANGCHAIN_SOCRATIC`
与既有调用路径双轨并存，默认 `=0`（legacy 路径）。该切片依赖原 spec
的双轨原则：「老路径永远可回退」。本节定义从 `0` 到 `100` 的灰度节奏。

### 11.1 灰度档位与节奏

每一档至少运行 **24 小时**、错误率 < 0.1% 才能进下一档。
跨档必须留 5 分钟观察窗，避免熔断回退。

| 档位          | 比例 | 持续 | 通过条件（基于 P99 + 错误率）            | 通讯要求         |
|---------------|------|------|------------------------------------------|------------------|
| 0 内部白名单  | 0%   | 1 周 | 单元 + 集成 + 红队全过                  | 团队内公示        |
| 1 灰度 1%     | 1%   | 3 天 | 错误率 < 0.5%、P99 < 3s                  | 灰度 QQ/微信群    |
| 2 灰度 10%    | 10%  | 3 天 | 错误率 < 0.2%、反幻觉拒答率 < 15%       | 灰度群            |
| 3 灰度 50%    | 50%  | 3 天 | 同上 + 人工抽检 50 条无明显质量下降      | 产品 + 全平台用户预热 |
| 4 全量 100%   | 100% | —    | 同上 + chaos drill 通过                   | 正式发布公告      |

### 11.2 灰度用户哈希分流

切读通过 `READ_BACKEND_PERCENTAGE`（沿用既有 + feature flag 机制，
详见 `app/core/feature_flags.py`）按用户哈希取模分流，与切片 #1 用户
认证、切片 #12 小星决策引擎灰度策略一致。

```bash
# 1% 切读（约 100/10000 用 user_id MD5 前 1 位命中）
deploy env set READ_BACKEND_PERCENTAGE=1
deploy env set DUAL_WRITE_LEGACY=true     # 同步写老路径，避免双数据源漂移

# 升级到 10%
deploy env set READ_BACKEND_PERCENTAGE=10

# 升级到 50%
deploy env set READ_BACKEND_PERCENTAGE=50

# 升级到 100%（双写仍保留，便于紧急回滚）
deploy env set READ_BACKEND_PERCENTAGE=100
```

### 11.3 Socratic 单独灰度

`USE_LANGCHAIN_SOCRATIC` 与 `READ_BACKEND_PERCENTAGE` 正交，可在不切整
个读路径的前提下单独打开 Socratic 新路径。建议节奏：

1. 先 `READ_BACKEND_PERCENTAGE=0`、单纯开 `USE_LANGCHAIN_SOCRATIC=1`
   给白名单用户（≤ 100 个员工 / 内部账号），跑 1 周。
2. 灰度 `READ_BACKEND_PERCENTAGE=1`（其中 Socratic 是否走新路径由
   `USE_LANGCHAIN_SOCRATIC` 决定 — 默认全部 Socratic 用户都走新路径）。
3. 灰度档位升降与 11.1 一致，但验收额外观察：
   - 反幻觉拒答率（blocked / total）< 15%
   - Socratic 流 1 P99 < 3s（验收 A5）
   - parity 4 指标全过（验收 A6）

### 11.4 灰度期监控

| 指标                       | 来源             | 告警阈值            |
|----------------------------|------------------|---------------------|
| 反幻觉拒答率              | parity + redteam | > 15%             |
| 流 1 P99 延迟             | perf-results/    | > 3s              |
| L3 拒答率                 | HealthProbe      | > 0.5%            |
| Parity cite overlap       | parity report    | < 0.85            |
| SessionStart hook P95     | Sentry APM       | > 2s              |
| `agents.py` 净增长        | CI `agents-size-net` | > 50 行/PR     |

### 11.5 回滚

灰度期内任一档发现致命问题，立即按 §9.1 一键回退：

```bash
deploy env set USE_LANGCHAIN_SOCRATIC=0
deploy env set READ_BACKEND_PERCENTAGE=0
deploy env set DUAL_WRITE_LEGACY=true
```

回退生效时间 ≤ 30s（env 刷新周期）。回退后保持 `DUAL_WRITE_LEGACY=true`
至少一周，防止新路径再次落入同一故障窗口。

### 11.6 灰度通过后的清理

`READ_BACKEND_PERCENTAGE=100` 稳定运行 7 天后：

1. 拆除 `DUAL_WRITE_LEGACY=true`（设为 `false`，停止写老路径）。
2. 在下一个稳定 release 标记 legacy 代码为 deprecated。
3. P1.5 之后再删除老路径物理代码（spec 第 6 节）。

---

## Appendix A — Chaos drill

The chaos drill exercises three fault scenarios:

| Scenario                       | What it kills                | Expected behaviour                       |
|--------------------------------|------------------------------|------------------------------------------|
| `kill_qdrant_30s`              | qdrant container             | L3 refusal during outage, recovery < 30s |
| `kill_redis_30s`              | redis container              | cache-miss fallback, recovery < 30s      |
| `session_start_hook_timeout`   | SessionStart hook (via env)  | cold start completes within 5s budget    |

Run it:

```bash
python scripts/chaos_drill.py
# or for a single scenario:
python scripts/chaos_drill.py --scenario kill_qdrant_30s
```

The report is written to
`perf-results/chaos-<YYYYMMDD-HHMMSS>.json`. In environments
without Docker, all scenarios report `passed=null` (SKIPPED) —
this is expected and the script still exits 0.

## Appendix B — Red-team drill

213 prompts across 8 categories validate the anti-hallucination
pipeline. Pass criteria:

| Category                     | Min safe_fallback ratio |
|------------------------------|--------------------------|
| A_out_of_domain              | 1.00                     |
| B_wrong_personal_facts       | 1.00                     |
| C_inject_nonexistent_kb      | 1.00                     |
| D_prompt_injection           | 1.00                     |
| E_conflicting_kb             | 1.00                     |
| F_partial_no_citation        | 1.00                     |
| G_id_tampering               | 1.00                     |
| H_cross_lang                 | 0.95                     |

Run it:

```bash
python tests/redteam/run.py
# or with a custom prompt set:
python tests/redteam/run.py --prompts /path/to/prompts.yaml
```

The report is written to `tests/redteam/report.json`. The runner
uses `MagicMock` for the LLM, so it is hermetic and runs in CI
without API keys.

---

**Last updated:** 2026-07-17 (slice-B6)
**Owners:** platform team (services), app team (LLM paths),
data team (L1 storage), SRE rotation (on-call)
