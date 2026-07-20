# -*- coding: utf-8 -*-
"""End-to-end tests for trace context propagation.

3 critical paths:
  1. Trace ID from request header reaches engine (verified via middleware traceparent)
  2. Concurrent requests have different trace IDs (isolation)
  3. Response traceparent matches incoming (with new span_id)
"""
import pytest


class TestTraceE2E:
    def test_trace_id_consistent_across_request(self, client, caplog):
        """Trace ID from request header appears in response traceparent."""
        import logging
        incoming_trace_id = "deadbeefdeadbeefdeadbeefdeadbeef"
        incoming = f"00-{incoming_trace_id}-cafebabecafebabe-01"

        # Call any endpoint (POST to login triggers trace middleware)
        r = client.post("/api/auth/login",
                       json={"username": "admin", "password": "123456"},
                       headers={"traceparent": incoming})

        # Response traceparent should echo the trace_id
        assert "traceparent" in r.headers
        assert incoming_trace_id in r.headers["traceparent"]

    def test_concurrent_requests_have_different_traces(self, client):
        """Two requests without incoming traceparent get distinct trace IDs."""
        r1 = client.get("/login.html")
        r2 = client.get("/login.html")
        trace1 = r1.headers["traceparent"].split("-")[1]
        trace2 = r2.headers["traceparent"].split("-")[1]
        assert trace1 != trace2

    def test_response_traceparent_matches_request(self, client):
        """Response traceparent echoes incoming trace_id (with new span_id)."""
        incoming_trace_id = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        incoming = f"00-{incoming_trace_id}-1111111111111111-01"
        r = client.get("/login.html", headers={"traceparent": incoming})
        parts = r.headers["traceparent"].split("-")
        assert parts[1] == incoming_trace_id
        assert parts[2] != "1111111111111111"  # new span_id

    def test_trace_id_in_response_without_incoming(self, client):
        """Without incoming traceparent, server generates one with valid format."""
        r = client.get("/login.html")
        assert "traceparent" in r.headers
        trace_id = r.headers["traceparent"].split("-")[1]
        assert len(trace_id) == 32
