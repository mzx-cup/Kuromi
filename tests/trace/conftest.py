# -*- coding: utf-8 -*-
"""Shared fixtures for trace tests."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """FastAPI TestClient wrapping the real main app."""
    from main import app
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_trace_context():
    """Ensure no contextvar leakage between tests."""
    from app.core import trace
    import contextvars
    token_trace = trace._current_trace.set(None)
    token_span = trace._current_span.set(None)
    try:
        yield
    finally:
        trace._current_trace.reset(token_trace)
        trace._current_span.reset(token_span)