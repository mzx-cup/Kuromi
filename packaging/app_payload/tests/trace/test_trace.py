# -*- coding: utf-8 -*-
"""Tests for TraceContext, trace_id/span_id generation, and parse_traceparent."""
import re
import pytest

from app.core.trace import (
    TraceContext,
    generate_trace_id,
    generate_span_id,
    parse_traceparent,
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

    def test_span_ids_unique(self):
        ids = {generate_span_id() for _ in range(100)}
        assert len(ids) == 100


class TestParseTraceparent:
    def test_valid_traceparent_extracts_trace_id(self):
        header = "00-abc12345678901234567890123456789-0123456789abcdef-01"
        ctx = parse_traceparent(header)
        assert ctx.trace_id == "abc12345678901234567890123456789"
        # span_id should be NEW (not preserved from incoming — per W3C spec)
        assert ctx.span_id != "0123456789abcdef"
        assert len(ctx.span_id) == 16

    def test_valid_traceparent_preserves_flags(self):
        header = "00-abc12345678901234567890123456789-0123456789abcdef-01"
        ctx = parse_traceparent(header)
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

    def test_malformed_version_ignored(self):
        ctx = parse_traceparent("99-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-1111111111111111-01")
        assert re.match(r"^[0-9a-f]{32}$", ctx.trace_id)


class TestSpanRecorder:
    def test_set_attribute(self):
        from app.core.trace import SpanRecorder
        span = SpanRecorder()
        span.set_attribute("user_id", 42)
        span.set_attribute("latency_ms", 123.4)
        assert span.attributes["user_id"] == 42
        assert span.attributes["latency_ms"] == 123.4

    def test_default_status_is_ok(self):
        from app.core.trace import SpanRecorder
        span = SpanRecorder()
        assert span.status == "ok"

    def test_set_status_error(self):
        from app.core.trace import SpanRecorder
        span = SpanRecorder()
        span.set_status("error")
        assert span.status == "error"

    def test_attributes_default_to_empty_dict(self):
        from app.core.trace import SpanRecorder
        span = SpanRecorder()
        assert span.attributes == {}


class TestStartFinishSpan:
    def test_start_creates_span_in_context(self):
        from app.core.trace import start_span, get_current_span, finish_span
        span, token = start_span("test.span")
        try:
            assert get_current_span() is span
            assert span.attributes["span.name"] == "test.span"
        finally:
            finish_span(span, token)

    def test_start_resets_to_none_after_finish(self):
        from app.core.trace import start_span, get_current_span, finish_span
        span, token = start_span("test.span")
        finish_span(span, token)
        assert get_current_span() is None

    def test_finish_emits_span_end_log(self, caplog):
        import logging
        from app.core.trace import start_span, finish_span
        span, token = start_span("test.timed")
        with caplog.at_level(logging.INFO, logger="starlearn.trace"):
            finish_span(span, token)
        # Verify log contains span_end marker
        assert any("span_end" in record.message for record in caplog.records)

    def test_finish_includes_duration_in_log(self, caplog):
        import logging
        import time
        from app.core.trace import start_span, finish_span
        span, token = start_span("test.timed")
        time.sleep(0.01)  # ensure duration > 0
        with caplog.at_level(logging.INFO, logger="starlearn.trace"):
            finish_span(span, token)
        assert any("duration_ms=" in record.message for record in caplog.records)