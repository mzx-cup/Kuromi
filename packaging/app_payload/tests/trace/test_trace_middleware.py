# -*- coding: utf-8 -*-
"""Tests for TraceMiddleware.

Verifies:
  - Incoming traceparent is preserved (only span_id regenerated)
  - Missing traceparent → new trace generated
  - Invalid traceparent → replaced with new trace
  - traceparent echoed on response
  - traceparent present on error responses (4xx/5xx)
"""
import pytest


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
        assert parts[3] == "01"     # flags

    def test_invalid_traceparent_replaced(self, client):
        r = client.get("/login.html", headers={"traceparent": "garbage"})
        parts = r.headers["traceparent"].split("-")
        assert len(parts[1]) == 32  # new trace_id generated
        assert len(parts[2]) == 16  # new span_id

    def test_traceparent_on_error_responses(self, client):
        r = client.get("/nonexistent-route-12345")
        assert r.status_code == 404
        assert "traceparent" in r.headers

    def test_traceparent_span_id_changes_per_request(self, client):
        # Two requests with same traceparent should get different span_ids
        incoming = "00-22222222222222222222222222222222-bbbbbbbbbbbbbbbb-01"
        r1 = client.get("/login.html", headers={"traceparent": incoming})
        r2 = client.get("/login.html", headers={"traceparent": incoming})
        # trace_id preserved, span_id regenerated
        assert r1.headers["traceparent"].split("-")[1] == r2.headers["traceparent"].split("-")[1]
        assert r1.headers["traceparent"].split("-")[2] != r2.headers["traceparent"].split("-")[2]
