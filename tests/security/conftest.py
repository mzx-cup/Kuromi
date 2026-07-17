# -*- coding: utf-8 -*-
"""Shared fixtures for security middleware tests.

Provides:
  - client: FastAPI TestClient bound to the actual main app
  - clean_security_env: reset all SECURITY_* env vars to defaults before each test
  - reset_rate_limiter: clear SlowAPI state between tests
  - security_config: fresh SecurityConfig instance
"""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """FastAPI TestClient wrapping the real main app."""
    from main import app
    return TestClient(app)


@pytest.fixture(autouse=True)
def clean_security_env(monkeypatch):
    """Reset all SECURITY_* env vars to defaults before each test.

    Ensures test isolation: no env var from the host leaks into a test.
    """
    # Remove all SECURITY_* env vars
    for key in list(os.environ.keys()):
        if key.startswith(("SECURITY_", "RATE_LIMIT_", "MAX_REQUEST_SIZE", "MAX_STREAMING_SIZE")):
            monkeypatch.delenv(key, raising=False)

    # Also force dev mode for most tests
    monkeypatch.setenv("SECURITY_DEV_MODE", "true")
    yield


@pytest.fixture
def production_mode(monkeypatch):
    """Force production mode (disable dev shortcuts)."""
    monkeypatch.setenv("SECURITY_DEV_MODE", "false")


@pytest.fixture
def reset_rate_limiter():
    """Reset SlowAPI state between tests.

    SlowAPI uses an in-memory storage. Without this, rate limits from one
    test bleed into the next.
    """
    from app.core.rate_limiter import limiter
    limiter.reset()
    yield
    limiter.reset()