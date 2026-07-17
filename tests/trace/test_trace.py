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