# Spec 2.1: Trace Context 贯穿设计

**日期：** 2026-07-17
**状态：** 设计待 review
**作者：** Brainstorming 会话

---

## 1. 背景与目标

### 1.1 当前状态

`tutor_engine/` 是项目的核心决策管道（3500 行），但缺少可观测性基础设施：

| 缺口 | 影响 |
|------|------|
| ❌ 无 trace_id | 单次请求的多个子模块调用无法关联 |
| ❌ 无 root span | 不知道一次 `engine.decide()` 耗时多少 |
| ❌ 无结构化日志 | 排查问题时只能 grep 字符串 |
| ❌ 无并发隔离 | 多个请求的日志混在一起 |

### 1.2 目标

实现 W3C Trace Context 标准的 traceparent 贯穿：

- 每个 HTTP 请求自动获得 trace_id（接收或生成）
- `engine.decide()` 整个管道记录一个 root span
- 子模块通过 contextvar 自动写入 attributes
- 结构化日志输出（便于 grep / 后续接 OpenTelemetry）
- 零第三方依赖（仅 stdlib）

### 1.3 非目标

- 不引入 OpenTelemetry SDK（用 Python logging 输出就够了）
- 不做 span exporter（不接 Jaeger / Zipkin / OTLP）
- 不做 metrics / logs 收集（Spec 5 涉及）
- 不做 APM（应用性能监控产品集成）

---

## 2. 架构

```
HTTP Request (with optional traceparent header)
    ↓
┌─────────────────────────────────────────────┐
│  TraceMiddleware (NEW)                       │
│  - Parse or generate traceparent             │
│  - Set contextvars for downstream access     │
│  - Add traceparent to response header        │
└─────────────────────────────────────────────┘
    ↓
engine.decide(event)
    ↓
  ┌──────────────────────────────────────────┐
  │  SpanRecorder (root span)                  │
  │  - trace_id: from TraceMiddleware          │
  │  - span_id: generated                      │
  │  - name: "tutor.decide"                    │
  │  - attributes:                             │
  │    • user_id, event_type                   │
  │    • context_count                          │
  │    • llm_tokens, llm_latency_ms            │
  │    • guard_risk_score                      │
  │    • links_count, actions_count            │
  │    • total_latency_ms                      │
  │    • status (ok/error)                     │
  │    • error.type, error.message (on error)  │
  └──────────────────────────────────────────┘
    ↓
finish_span() → logger.info("span_end", extra={...})
    ↓
ResponseEnvelope (with traceparent in response header)
```

**关键决策：**
- 单一 root span（不嵌套 child span）——性能友好
- 子模块通过 `get_current_span()` 自动写入 attributes
- Trace ID 出现在响应 header（`traceparent`）+ 日志中
- 用 stdlib `contextvars` 实现请求隔离（线程/协程安全）

---

## 3. 核心模块

### 3.1 `app/core/trace.py` — TraceContext + contextvars

```python
"""W3C Trace Context (traceparent header) — lightweight implementation.

Reference: https://www.w3.org/TR/trace-context/
Format: 00-{32 hex trace_id}-{16 hex span_id}-{2 hex flags}

Uses stdlib contextvars (no opentelemetry-api dependency).
"""
from __future__ import annotations

import contextvars
import re
import secrets
import time
from dataclasses import dataclass, field
from typing import Optional


# W3C traceparent format: 00-{32 hex}-{16 hex}-{2 hex}
TRACEPARENT_RE = re.compile(
    r"^([0-9a-f]{2})-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$"
)
TRACEPARENT_VERSION = "00"
TRACEPARENT_FLAGS_SAMPLED = "01"


@dataclass(frozen=True)
class TraceContext:
    """Immutable trace context carried across the request."""
    trace_id: str  # 32 hex chars
    span_id: str   # 16 hex chars
    flags: str = TRACEPARENT_FLAGS_SAMPLED

    @property
    def traceparent(self) -> str:
        return f"{TRACEPARENT_VERSION}-{self.trace_id}-{self.span_id}-{self.flags}"


@dataclass
class SpanRecorder:
    """Records attributes for the current root span.

    Used by engine.decide() and its sub-modules to record timing,
    counts, and status without producing child spans (per design).
    """
    attributes: dict[str, str | int | float] = field(default_factory=dict)
    status: str = "ok"
    start_time: float = 0.0

    def set_attribute(self, key: str, value: str | int | float) -> None:
        self.attributes[key] = value

    def set_status(self, status: str) -> None:
        self.status = status


# ContextVars for downstream code to access current trace
_current_trace: contextvars.ContextVar[Optional[TraceContext]] = contextvars.ContextVar(
    "current_trace", default=None
)
_current_span: contextvars.ContextVar[Optional[SpanRecorder]] = contextvars.ContextVar(
    "current_span", default=None
)


def generate_trace_id() -> str:
    """Generate a 32-hex-char trace ID."""
    return secrets.token_hex(16)


def generate_span_id() -> str:
    """Generate a 16-hex-char span ID."""
    return secrets.token_hex(8)


def parse_traceparent(header: str | None) -> TraceContext:
    """Parse incoming traceparent header or generate new context.

    If header is malformed, generates a fresh context (W3C spec says invalid
    traceparent should be silently ignored).
    """
    if header:
        match = TRACEPARENT_RE.match(header.strip())
        if match:
            return TraceContext(
                trace_id=match.group(2),
                span_id=generate_span_id(),  # new span for this request
                flags=match.group(4),
            )
    # No header or invalid → fresh trace
    return TraceContext(
        trace_id=generate_trace_id(),
        span_id=generate_span_id(),
    )


def get_current_trace() -> TraceContext | None:
    """Return the current request's trace context, or None."""
    return _current_trace.get()


def set_current_trace(ctx: TraceContext) -> contextvars.Token:
    """Set current trace context (returns Token for restoration)."""
    return _current_trace.set(ctx)


def reset_current_trace(token: contextvars.Token) -> None:
    """Restore previous trace context."""
    _current_trace.reset(token)


def get_current_span() -> SpanRecorder | None:
    """Return the current span recorder, or None if no span active."""
    return _current_span.get()


def start_span(name: str) -> tuple[SpanRecorder, contextvars.Token]:
    """Start a new root span and bind to context.

    Returns (span, token). Caller is responsible for finish_span(token).
    """
    span = SpanRecorder(start_time=time.perf_counter())
    span.set_attribute("span.name", name)
    token = _current_span.set(span)
    return span, token


def finish_span(span: SpanRecorder, token) -> None:
    """Finish span — emit attributes to structured log."""
    elapsed_ms = (time.perf_counter() - span.start_time) * 1000
    span.set_attribute("span.duration_ms", elapsed_ms)
    trace = get_current_trace()
    logger = logging.getLogger("starlearn.trace")
    # Format attributes as key=value pairs
    attrs_str = " ".join(f"{k}={v}" for k, v in span.attributes.items())
    logger.info(
        f"span_end name={span.attributes.get('span.name', 'unknown')} "
        f"trace_id={trace.trace_id if trace else 'none'} "
        f"span_id={trace.span_id if trace else 'none'} "
        f"status={span.status} duration_ms={elapsed_ms:.1f} {attrs_str}"
    )
    _current_span.reset(token)
```

### 3.2 `app/core/middleware/trace.py` — TraceMiddleware

```python
"""TraceMiddleware — extracts/generates W3C traceparent for every request.

Adds the traceparent header to the response so clients can correlate.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.trace import (
    get_current_trace,
    parse_traceparent,
    set_current_trace,
    reset_current_trace,
)


class TraceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Extract or generate trace context
        incoming = request.headers.get("traceparent")
        ctx = parse_traceparent(incoming)
        token = set_current_trace(ctx)

        try:
            response: Response = await call_next(request)
            # Echo traceparent on response (W3C trace context convention)
            response.headers["traceparent"] = ctx.traceparent
            return response
        finally:
            reset_current_trace(token)
```

### 3.3 `app/core/middleware/__init__.py`

Add `TraceMiddleware` to exports.

---

## 4. 引擎集成

### 4.1 `app/services/tutor_engine/engine.py` 修改

```python
from app.core.trace import (
    SpanRecorder,
    start_span,
    finish_span,
    get_current_span,
)


class TutorDecisionEngine:
    async def decide(self, event: TutorEvent) -> ResponseEnvelope:
        span, token = start_span("tutor.decide")
        span.set_attribute("user_id", str(event.user_id))
        span.set_attribute("event_type", event.event_type.value)

        try:
            # Phase 1: Context aggregation
            context = await self.context_aggregator.aggregate(event)
            span.set_attribute("context_count", len(context.citations) + len(context.knowledge_nodes))

            # Phase 2: LLM generation
            llm_start = time.perf_counter()
            raw_response = await self.llm.generate(event, context)
            span.set_attribute("llm_latency_ms", (time.perf_counter() - llm_start) * 1000)

            # Phase 3: Hallucination guard
            confidence = await self.guard.check(raw_response, context)
            span.set_attribute("guard_risk_score", confidence.risk_score)
            if confidence.blocked:
                span.set_status("error")
                raise HallucinationBlocked(...)

            # Phase 4: Link recommender
            links = await self.link_recommender.recommend(event, context)
            span.set_attribute("links_count", len(links))

            # Phase 5: Proactive advisor
            actions = await self.proactive_advisor.evaluate(event, context, response)
            span.set_attribute("actions_count", len(actions))

            envelope = ResponseEnvelope(...)
            span.set_status("ok")
            return envelope

        except Exception as e:
            span.set_status("error")
            span.set_attribute("error.type", type(e).__name__)
            span.set_attribute("error.message", str(e)[:200])
            raise
        finally:
            finish_span(span, token)
```

### 4.2 子模块记录属性（示例）

子模块通过 `get_current_span()` 自动写入：

```python
# app/services/tutor_engine/hallucination_guard.py
from app.core.trace import get_current_span

async def check(self, response, context):
    span = get_current_span()
    claims = self.extract_claims(response)
    if span:
        span.set_attribute("guard.claims_total", len(claims))
        span.set_attribute("guard.citations_checked", len(self.find_citations(response)))
    # ... rest of guard logic
```

类似地：
- `context_aggregator.py` 写 `context.citations_count`, `context.knowledge_nodes_count`
- `link_recommender.py` 写 `links.score_distribution`
- `proactive_advisor.py` 写 `proactive.triggers_fired`

---

## 5. 测试策略

### 5.1 单元测试（`tests/trace/`）

#### `test_trace.py`

```python
import re
import pytest
from app.core.trace import (
    TraceContext, SpanRecorder,
    generate_trace_id, generate_span_id, parse_traceparent,
    get_current_trace, set_current_trace, reset_current_trace,
    get_current_span, start_span, finish_span,
)


class TestTraceIdGeneration:
    def test_trace_id_format(self):
        tid = generate_trace_id()
        assert len(tid) == 32
        assert re.match(r"^[0-9a-f]{32}$", tid)

    def test_trace_ids_unique(self):
        ids = {generate_trace_id() for _ in range(100)}
        assert len(ids) == 100

    def test_span_id_format(self):
        sid = generate_span_id()
        assert len(sid) == 16
        assert re.match(r"^[0-9a-f]{16}$", sid)


class TestParseTraceparent:
    def test_valid_traceparent(self):
        header = "00-abc12345678901234567890123456789-0123456789abcdef-01"
        ctx = parse_traceparent(header)
        assert ctx.trace_id == "abc12345678901234567890123456789"
        # span_id is NEW (not preserved from incoming — per W3C spec)
        assert ctx.span_id != "0123456789abcdef"
        assert len(ctx.span_id) == 16
        assert ctx.flags == "01"

    def test_invalid_traceparent_generates_new(self):
        ctx = parse_traceparent("invalid-format")
        assert len(ctx.trace_id) == 32
        assert len(ctx.span_id) == 16

    def test_none_traceparent_generates_new(self):
        ctx = parse_traceparent(None)
        assert len(ctx.trace_id) == 32
        assert len(ctx.span_id) == 16

    def test_empty_traceparent_generates_new(self):
        ctx = parse_traceparent("")
        assert len(ctx.trace_id) == 32

    def test_traceparent_roundtrip(self):
        ctx = parse_traceparent(None)
        assert ctx.traceparent.startswith("00-")
        assert f"-{ctx.trace_id}-{ctx.span_id}-" in ctx.traceparent


class TestContextVar:
    def test_get_returns_none_when_unset(self):
        assert get_current_trace() is None

    def test_set_and_get(self):
        ctx = TraceContext(trace_id="aaa", span_id="bbb")
        token = set_current_trace(ctx)
        try:
            assert get_current_trace() is ctx
        finally:
            reset_current_trace(token)

    def test_reset_restores_previous(self):
        ctx1 = TraceContext(trace_id="111", span_id="222")
        ctx2 = TraceContext(trace_id="333", span_id="444")
        token1 = set_current_trace(ctx1)
        token2 = set_current_trace(ctx2)
        reset_current_trace(token2)
        assert get_current_trace() is ctx1
        reset_current_trace(token1)


class TestSpanRecorder:
    def test_set_attribute(self):
        span = SpanRecorder()
        span.set_attribute("user_id", 42)
        span.set_attribute("latency_ms", 123.4)
        assert span.attributes["user_id"] == 42
        assert span.attributes["latency_ms"] == 123.4

    def test_default_status_is_ok(self):
        span = SpanRecorder()
        assert span.status == "ok"

    def test_set_status_error(self):
        span = SpanRecorder()
        span.set_status("error")
        assert span.status == "error"


class TestStartFinishSpan:
    def test_start_creates_span(self):
        span, token = start_span("test.span")
        try:
            assert get_current_span() is span
            assert span.attributes["span.name"] == "test.span"
        finally:
            finish_span(span, token)

    def test_finish_records_duration(self, caplog):
        span, token = start_span("test.timed")
        import time
        time.sleep(0.01)
        with caplog.at_level("INFO", logger="starlearn.trace"):
            finish_span(span, token)
        assert "span_end" in caplog.text
        assert "duration_ms=" in caplog.text
```

#### `test_trace_middleware.py`

```python
class TestTraceMiddleware:
    def test_incoming_traceparent_preserved(self, client):
        incoming = "00-11111111111111111111111111111111-aaaaaaaaaaaaaaaa-01"
        r = client.get("/login.html", headers={"traceparent": incoming})
        assert r.headers["traceparent"].startswith("00-11111111111111111111111111111111-")

    def test_no_incoming_generates_new(self, client):
        r = client.get("/login.html")
        assert "traceparent" in r.headers
        parts = r.headers["traceparent"].split("-")
        assert len(parts) == 4
        assert len(parts[1]) == 32  # trace_id
        assert len(parts[2]) == 16  # span_id

    def test_invalid_traceparent_replaced(self, client):
        r = client.get("/login.html", headers={"traceparent": "garbage"})
        parts = r.headers["traceparent"].split("-")
        assert len(parts[1]) == 32

    def test_traceparent_on_error_responses(self, client):
        r = client.get("/nonexistent-route-12345")
        assert r.status_code == 404
        assert "traceparent" in r.headers
```

### 5.2 引擎集成测试（`tests/services/test_engine_trace.py`）

```python
class TestEngineTraceIntegration:
    def test_engine_emits_span_attributes(self, mock_submodules):
        """engine.decide() should record span attributes via contextvar."""
        engine = TutorDecisionEngine(...)

        event = TutorEvent(user_id="42", event_type=...)
        with caplog.at_level("INFO", logger="starlearn.trace"):
            envelope = await engine.decide(event)

        # Verify span_end log emitted with expected attributes
        assert "span_end" in caplog.text
        assert "user_id=42" in caplog.text
        assert "event_type=" in caplog.text
        assert "context_count=" in caplog.text
        assert "llm_latency_ms=" in caplog.text
        assert "guard_risk_score=" in caplog.text
        assert "links_count=" in caplog.text
        assert "actions_count=" in caplog.text

    def test_engine_records_error_status(self, mock_submodules_failing):
        engine = TutorDecisionEngine(...)

        event = TutorEvent(...)
        with pytest.raises(HallucinationBlocked):
            with caplog.at_level("INFO", logger="starlearn.trace"):
                await engine.decide(event)

        assert "status=error" in caplog.text
        assert "error.type=" in caplog.text

    def test_child_module_writes_attributes(self, mock_submodules):
        """HallucinationGuard writes guard.* attrs via get_current_span()."""
        engine = TutorDecisionEngine(...)

        event = TutorEvent(...)
        with caplog.at_level("INFO", logger="starlearn.trace"):
            await engine.decide(event)

        # Guard should have set its own attributes
        assert "guard.claims_total=" in caplog.text
```

### 5.3 E2E 测试（`tests/trace/test_e2e.py`）

```python
class TestTraceE2E:
    def test_trace_id_consistent_across_engine(self, client, caplog):
        """Trace ID from request header reaches engine.decide() log."""
        incoming = "00-deadbeefdeadbeefdeadbeefdeadbeef-cafebabecafebabe-01"

        with caplog.at_level("INFO", logger="starlearn.trace"):
            r = client.post("/api/v2/chat/stream",
                           json={"message": "test"},
                           headers={"traceparent": incoming})
            # Even if endpoint errors, trace should be in logs
            for record in caplog.records:
                if "trace_id=deadbeef" in record.message:
                    return  # found
            pytest.fail("Trace ID not propagated to engine logs")

    def test_concurrent_requests_have_different_traces(self, client):
        """Two concurrent requests get distinct trace IDs."""
        r1 = client.get("/login.html")
        r2 = client.get("/login.html")
        trace1 = r1.headers["traceparent"].split("-")[1]
        trace2 = r2.headers["traceparent"].split("-")[1]
        assert trace1 != trace2

    def test_response_traceparent_matches_request(self, client):
        """Response traceparent echoes the incoming trace_id (new span_id)."""
        incoming = "00-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-1111111111111111-01"
        r = client.get("/login.html", headers={"traceparent": incoming})
        parts = r.headers["traceparent"].split("-")
        assert parts[1] == "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        assert parts[2] != "1111111111111111"  # new span_id
```

### 5.4 回归测试

确保不破坏现有功能：
- `tests/repositories/` 全部通过
- `tests/contracts/` 全部通过
- `tests/security/` 73 个测试全部通过
- `tests/test_feature_flags.py`, `test_repository_factory.py`, `test_dual_db_fixture.py` 全部通过

---

## 6. 验收标准

### 6.1 切片 2.1.1 验收（TraceContext + contextvars）

- [ ] 12 个单元测试通过（TestTraceIdGeneration, TestParseTraceparent, TestContextVar, TestSpanRecorder, TestStartFinishSpan）
- [ ] 无第三方依赖
- [ ] contextvars 在并发请求下隔离

### 6.2 切片 2.1.2 验收（TraceMiddleware）

- [ ] 3 个中间件测试通过
- [ ] 所有现有 303+ 测试无回归
- [ ] 手动 curl 验证：响应 header 含 `traceparent`

### 6.3 切片 2.1.3 验收（SpanRecorder 日志输出）

- [ ] SpanRecorder 测试通过
- [ ] finish_span 通过 `logger.info(...)` 输出
- [ ] 日志格式包含所有 attributes

### 6.4 切片 2.1.4 验收（engine.decide() 集成）

- [ ] engine.decide() 每次调用都输出 span_end 日志
- [ ] 日志包含 user_id, event_type, context_count, llm_latency_ms, guard_risk_score, links_count, actions_count
- [ ] 失败时 span.status = "error"
- [ ] 230+ 回归测试无破坏

### 6.5 切片 2.1.5 验收（E2E + 文档）

- [ ] 3 个 E2E 测试通过
- [ ] `docs/superpowers/trace-context-usage.md` 创建
- [ ] `docs/superpowers/spec-2.1-status.md` 创建

---

## 7. 风险与依赖

### 7.1 依赖

- 无（仅 stdlib: `contextvars`, `secrets`, `re`, `dataclasses`, `time`, `logging`）

### 7.2 风险

| 风险 | 等级 | 缓解 |
|------|------|------|
| 现有 `engine.decide()` 修改可能引入回归 | 🟡 中 | 4 个 mock-based 集成测试 + 完整回归 |
| `get_current_span()` 返回 None 时子模块崩溃 | 🟢 低 | 子模块代码用 `if span:` 守卫 |
| Trace ID 暴露给客户端可能泄露信息 | 🟢 低 | 仅 32 字符随机十六进制，无业务语义 |
| contextvars 在异步中的行为 | 🟢 低 | Python 3.7+ 标准库，asyncio 兼容 |

### 7.3 不在范围内（后续 Spec）

- Spec 2.2: Loop budget（成本控制）
- Spec 2.3: State machine（流程抽象）
- Spec 3: 防护栏（max-iter + 断路器）
- Spec 4: Prompt injection 防护
- Spec 5: PII 检测

---

## 8. 时间线

```
W1: 切片 2.1.1 + 2.1.2 + 2.1.3   (基础设施 + middleware + span recorder)
W2: 切片 2.1.4 + 2.1.5            (engine 集成 + E2E + 文档)
```

**总计：约 1.5 周（5-6 工作日）**

---

## 9. 待决问题

> 这些问题在实施前应明确或接受风险。

1. **是否需要后续接 OpenTelemetry SDK？** 目前 spec 决定只用 logging 输出，但未来可能需要 OTLP exporter。预留接口（`finish_span()` 可以替换成 exporter）即可。
2. **是否记录 LLM 的 prompt/response 内容？** 当前 spec 只记录 token 计数和延迟。如果需要审计 LLM 输入输出，需考虑隐私和存储成本。
3. **trace_id 在错误日志中的格式？** 当前用 `trace_id={value}` 格式。生产可能需要 JSON 格式便于 log aggregator 解析。

---

**文档版本：** 1.0
**下一步：** 用户 review → writing-plans skill → 实施