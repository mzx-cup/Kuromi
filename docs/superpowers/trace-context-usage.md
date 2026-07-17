# Trace Context Usage Guide

**Date:** 2026-07-17
**Audience:** Developers extending the tutor_engine pipeline

## What is Trace Context?

Every HTTP request gets a W3C-standard `traceparent` header (format: `00-{32 hex}-{16 hex}-{2 hex}`).
This trace_id is:
- Carried in HTTP headers (request and response)
- Set as a Python contextvar (accessible from anywhere)
- Attached to log output via Python's logging module
- Used to correlate logs from a single request across multiple components

## Reading the Current Trace

Anywhere in your code:

```python
from app.core.trace import get_current_trace

trace = get_current_trace()
if trace:
    print(f"trace_id={trace.trace_id} span_id={trace.span_id}")
```

The trace is **None** outside of a request context (e.g., in startup code, cron jobs).

## Recording Span Attributes

When you're inside `engine.decide()` (or any code wrapped by `start_span`):

```python
from app.core.trace import get_current_span

span = get_current_span()
if span:
    span.set_attribute("my_module.key", "value")
    span.set_attribute("my_module.count", 42)
    span.set_attribute("my_module.latency_ms", elapsed_ms)
```

These attributes are automatically attached to the active span's `span_end` log line.

## Adding New Span Points

If you need to trace a new phase of work:

```python
from app.core.trace import start_span, finish_span

async def my_new_phase(data):
    span, token = start_span("my.new_phase")
    try:
        # ... do work, record attributes ...
        span.set_attribute("items_processed", len(data))
        return result
    except Exception as e:
        span.set_status("error")
        span.set_attribute("error.type", type(e).__name__)
        raise
    finally:
        finish_span(span, token)
```

## Log Format

When a span ends, this line is logged:

```
INFO  starlearn.trace  span_end name=tutor.decide trace_id=abc... span_id=def... status=ok duration_ms=234.5 span.name=tutor.decide user_id=42 event_type=chat_message context_count=5 llm_latency_ms=189.3 guard_final_confidence=0.92 links_count=3 actions_count=1 span.duration_ms=234.5
```

Use `grep "trace_id=abc"` to filter logs for a single request.

## Troubleshooting

### "I'm not seeing trace_id in my logs"

Check that:
1. You're inside a request handler (TraceMiddleware ran)
2. You called `get_current_trace()` inside the same async context
3. You're looking at the right log file/stream

### "Span attributes are missing"

Check that:
1. You called `start_span()` before `set_attribute()`
2. You're in the same async context (contextvars are per-task)
3. You called `finish_span()` (which logs the attributes)

## References

- W3C Trace Context spec: https://www.w3.org/TR/trace-context/
- Spec doc: `docs/superpowers/specs/2026-07-17-trace-context-design.md`
- Test examples: `tests/trace/`, `tests/services/test_engine_trace.py`
