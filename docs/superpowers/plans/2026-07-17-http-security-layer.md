# HTTP Security Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement 5 HTTP security middlewares (security headers, CORS strict, rate limiting, CSRF/origin check, request size limit) for the FastAPI app, achieving 100% HTTP-layer security coverage.

**Architecture:** FastAPI BaseHTTPMiddleware stack + SlowAPI for rate limiting + centralized SecurityConfig dataclass. All middlewares read from a single config source, override via env vars. 5 progressive slices ship one middleware each.

**Tech Stack:** Python 3.11+, FastAPI, Starlette BaseHTTPMiddleware, SlowAPI, pytest, FastAPI TestClient

---

## File Structure

### New Files

| Path | Responsibility |
|------|---------------|
| `app/core/security_config.py` | Centralized SecurityConfig dataclass, env var loader, fixed header dict |
| `app/core/middleware/__init__.py` | Middleware package marker |
| `app/core/middleware/security_headers.py` | Adds CSP/X-Frame-Options/HSTS/etc. to every response |
| `app/core/middleware/origin_check.py` | CSRF protection via Origin/Referer header validation |
| `app/core/middleware/request_size.py` | Rejects oversized request bodies (10MB default, 50MB streaming) |
| `app/core/rate_limiter.py` | SlowAPI Limiter instance + named limit decorators |
| `app/core/auth_utils.py` | JWT decode helper (no signature verify) for extracting user_id |
| `tests/security/__init__.py` | Test package marker |
| `tests/security/conftest.py` | Shared fixtures: reset rate limiter, clean env, monkeypatch security_config |
| `tests/security/test_security_config.py` | Config dataclass tests |
| `tests/security/test_security_headers.py` | SecurityHeadersMiddleware tests |
| `tests/security/test_cors.py` | CORS strict configuration tests |
| `tests/security/test_rate_limit.py` | Rate limit decorator tests |
| `tests/security/test_csrf.py` | OriginCheckMiddleware tests |
| `tests/security/test_request_size.py` | RequestSizeLimitMiddleware tests |
| `tests/security/test_integration.py` | Full middleware stack integration tests |
| `tests/security/test_e2e.py` | E2E security flow tests (3 critical paths) |

### Modified Files

| Path | Changes |
|------|---------|
| `main.py` | Add 5 middlewares (replacing current CORS), add rate limit decorators on auth/AI endpoints, add RateLimitExceeded exception handler |
| `requirements.txt` | Add `slowapi>=0.1.9` |

---

## Dependency Graph

```
Slice 1.1: SecurityConfig + SecurityHeaders (independent)
    │
    ├─> Slice 1.2: CORS strict (uses SecurityConfig)
    │
    ├─> Slice 1.3: RateLimitMiddleware (uses SecurityConfig, independent of 1.2)
    │
    ├─> Slice 1.4: OriginCheckMiddleware (uses SecurityConfig, independent of 1.2/1.3)
    │
    └─> Slice 1.5: RequestSizeLimitMiddleware (uses SecurityConfig, independent)
                       +
                   Integration + E2E tests (depends on 1.1-1.5)
```

Slices 1.2-1.5 can be done in parallel order, but plan executes them sequentially to avoid merge conflicts on `main.py`.

---

# Slice 1.1: SecurityConfig + SecurityHeadersMiddleware

**Goal:** Establish centralized security configuration and ship the simplest middleware (security headers). Zero business-logic impact.

**Working directory:** `c:/Users/ZWC/Downloads/Kuromi-main/Kuromi-main/`

---

### Task 1.1.1: Create security test package structure

**Files:**
- Create: `tests/security/__init__.py`
- Create: `tests/security/conftest.py`

- [ ] **Step 1: Create `tests/security/__init__.py` (empty file)**

Create the file with no content.

- [ ] **Step 2: Create `tests/security/conftest.py` with shared fixtures**

```python
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
```

- [ ] **Step 3: Verify imports work**

Run: `python -c "from tests.security.conftest import clean_security_env"`
Expected: no output (success).

- [ ] **Step 4: Commit**

```bash
git add tests/security/__init__.py tests/security/conftest.py
git commit -m "test(security): scaffold test package and shared fixtures"
```

---

### Task 1.1.2: Write failing test for SecurityConfig

**Files:**
- Create: `tests/security/test_security_config.py`

- [ ] **Step 1: Create the test file**

```python
# -*- coding: utf-8 -*-
"""Tests for SecurityConfig dataclass.

Verifies defaults, env var override, and singleton behavior.
"""
import pytest

from app.core.security_config import (
    SECURITY_HEADERS,
    SecurityConfig,
    get_security_config,
)


class TestSecurityConfigDefaults:
    def test_default_allowed_origins(self):
        cfg = SecurityConfig()
        assert "http://localhost:3000" in cfg.allowed_origins
        assert "http://localhost:5173" in cfg.allowed_origins
        assert "http://127.0.0.1:8000" in cfg.allowed_origins

    def test_default_csp_includes_self(self):
        cfg = SecurityConfig()
        assert "'self'" in cfg.csp_policy
        assert "default-src" in cfg.csp_policy

    def test_hsts_disabled_by_default(self):
        cfg = SecurityConfig()
        assert cfg.enable_hsts is False

    def test_default_rate_limits(self):
        cfg = SecurityConfig()
        assert cfg.login_rate_per_minute == 5
        assert cfg.register_rate_per_hour == 3
        assert cfg.ai_chat_rate_per_minute == 30
        assert cfg.default_api_rate_per_minute == 60

    def test_default_size_limits(self):
        cfg = SecurityConfig()
        assert cfg.max_request_size_mb == 10
        assert cfg.max_streaming_size_mb == 50

    def test_dev_mode_enabled_by_default(self):
        cfg = SecurityConfig()
        assert cfg.dev_mode is True


class TestSecurityConfigEnvOverrides:
    def test_allowed_origins_override(self, monkeypatch):
        monkeypatch.setenv(
            "SECURITY_ALLOWED_ORIGINS",
            "https://app.example.com,https://admin.example.com"
        )
        cfg = SecurityConfig()
        assert cfg.allowed_origins == [
            "https://app.example.com", "https://admin.example.com"
        ]

    def test_csp_override(self, monkeypatch):
        monkeypatch.setenv(
            "SECURITY_CSP_POLICY",
            "default-src 'none'"
        )
        cfg = SecurityConfig()
        assert cfg.csp_policy == "default-src 'none'"

    def test_hsts_enable(self, monkeypatch):
        monkeypatch.setenv("SECURITY_ENABLE_HSTS", "true")
        cfg = SecurityConfig()
        assert cfg.enable_hsts is True

    def test_rate_limit_overrides(self, monkeypatch):
        monkeypatch.setenv("RATE_LIMIT_LOGIN", "10")
        monkeypatch.setenv("RATE_LIMIT_REGISTER", "5")
        cfg = SecurityConfig()
        assert cfg.login_rate_per_minute == 10
        assert cfg.register_rate_per_hour == 5

    def test_size_limit_overrides(self, monkeypatch):
        monkeypatch.setenv("MAX_REQUEST_SIZE_MB", "25")
        monkeypatch.setenv("MAX_STREAMING_SIZE_MB", "100")
        cfg = SecurityConfig()
        assert cfg.max_request_size_mb == 25
        assert cfg.max_streaming_size_mb == 100

    def test_dev_mode_override(self, monkeypatch):
        monkeypatch.setenv("SECURITY_DEV_MODE", "false")
        cfg = SecurityConfig()
        assert cfg.dev_mode is False

    def test_invalid_rate_limit_uses_zero(self, monkeypatch):
        monkeypatch.setenv("RATE_LIMIT_LOGIN", "not-a-number")
        cfg = SecurityConfig()
        # int("not-a-number") raises; SecurityConfig catches and uses 0
        assert cfg.login_rate_per_minute == 0


class TestSecurityHeadersConstant:
    def test_security_headers_present(self):
        assert "X-Content-Type-Options" in SECURITY_HEADERS
        assert "X-Frame-Options" in SECURITY_HEADERS
        assert "X-XSS-Protection" in SECURITY_HEADERS
        assert "Referrer-Policy" in SECURITY_HEADERS
        assert "Permissions-Policy" in SECURITY_HEADERS

    def test_security_header_values(self):
        assert SECURITY_HEADERS["X-Content-Type-Options"] == "nosniff"
        assert SECURITY_HEADERS["X-Frame-Options"] == "DENY"
        assert SECURITY_HEADERS["X-XSS-Protection"] == "1; mode=block"
        assert "strict-origin" in SECURITY_HEADERS["Referrer-Policy"]
        assert "geolocation=()" in SECURITY_HEADERS["Permissions-Policy"]


class TestGetSecurityConfig:
    def test_returns_singleton(self):
        cfg1 = get_security_config()
        cfg2 = get_security_config()
        assert cfg1 is cfg2
```

- [ ] **Step 2: Run test to confirm failure**

Run: `pytest tests/security/test_security_config.py -v 2>&1 | tail -10`
Expected: FAIL with "ModuleNotFoundError: No module named 'app.core.security_config'"

- [ ] **Step 3: Commit the failing test**

```bash
git add tests/security/test_security_config.py
git commit -m "test(security): add SecurityConfig tests (red phase)"
```

---

### Task 1.1.3: Implement SecurityConfig

**Files:**
- Create: `app/core/security_config.py`

- [ ] **Step 1: Create `app/core/security_config.py`**

```python
# -*- coding: utf-8 -*-
"""Centralized security configuration.

All security middleware read from this single source of truth.
Override defaults via environment variables.

Environment variables:
  SECURITY_ALLOWED_ORIGINS — comma-separated origin allowlist
  SECURITY_CSP_POLICY     — Content-Security-Policy value
  SECURITY_ENABLE_HSTS    — "true" to enable Strict-Transport-Security
  SECURITY_DEV_MODE       — "true" to skip CSRF Origin check (dev convenience)
  RATE_LIMIT_LOGIN        — login attempts per minute per IP (default: 5)
  RATE_LIMIT_REGISTER     — register attempts per hour per IP (default: 3)
  RATE_LIMIT_GUEST        — guest login attempts per hour per IP (default: 10)
  RATE_LIMIT_AI           — AI chat calls per minute per user (default: 30)
  RATE_LIMIT_DEFAULT      — default API calls per minute per IP (default: 60)
  MAX_REQUEST_SIZE_MB     — max request body size in MB (default: 10)
  MAX_STREAMING_SIZE_MB    — streaming endpoint max in MB (default: 50)
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

logger = logging.getLogger("starlearn.security.config")


def _env_list(name: str, default: str) -> list[str]:
    """Parse a comma-separated env var into a list of stripped strings."""
    raw = os.getenv(name, default)
    return [s.strip() for s in raw.split(",") if s.strip()]


def _env_int(name: str, default: int) -> int:
    """Parse an int env var; return default on parse error (logged)."""
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("[security_config] %s=%r is not an int, using default %d", name, raw, default)
        return default


def _env_bool(name: str, default: bool) -> bool:
    """Parse a bool env var ('true'/'false'/'1'/'0')."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.lower() in ("true", "1", "yes", "on")


# Fixed security headers — returned by SecurityHeadersMiddleware on every response
SECURITY_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}


@dataclass(frozen=True)
class SecurityConfig:
    """Immutable security configuration. Read env vars at construction."""

    # CORS / CSRF shared allowlist
    allowed_origins: list[str] = field(default_factory=lambda:
        _env_list(
            "SECURITY_ALLOWED_ORIGINS",
            "http://localhost:3000,http://localhost:5173,"
            "http://localhost:8080,http://127.0.0.1:8000"
        )
    )

    # Content Security Policy
    csp_policy: str = os.getenv(
        "SECURITY_CSP_POLICY",
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "connect-src 'self'"
    )

    # HSTS — only enable in HTTPS deployments
    enable_hsts: bool = field(default_factory=lambda: _env_bool("SECURITY_ENABLE_HSTS", False))
    hsts_value: str = "max-age=31536000; includeSubDomains"

    # Rate limits
    login_rate_per_minute: int = field(default_factory=lambda: _env_int("RATE_LIMIT_LOGIN", 5))
    register_rate_per_hour: int = field(default_factory=lambda: _env_int("RATE_LIMIT_REGISTER", 3))
    guest_login_rate_per_hour: int = field(default_factory=lambda: _env_int("RATE_LIMIT_GUEST", 10))
    ai_chat_rate_per_minute: int = field(default_factory=lambda: _env_int("RATE_LIMIT_AI", 30))
    default_api_rate_per_minute: int = field(default_factory=lambda: _env_int("RATE_LIMIT_DEFAULT", 60))

    # Request size limits (MB)
    max_request_size_mb: int = field(default_factory=lambda: _env_int("MAX_REQUEST_SIZE_MB", 10))
    max_streaming_size_mb: int = field(default_factory=lambda: _env_int("MAX_STREAMING_SIZE_MB", 50))

    # Dev mode — skip CSRF Origin check
    dev_mode: bool = field(default_factory=lambda: _env_bool("SECURITY_DEV_MODE", True))


# Singleton — initialized at first access
_security_config: SecurityConfig | None = None


def get_security_config() -> SecurityConfig:
    """Return the singleton SecurityConfig instance.

    A fresh instance is constructed at first access; env var changes after
    that point are NOT reflected (caller must restart process).
    """
    global _security_config
    if _security_config is None:
        _security_config = SecurityConfig()
    return _security_config


def reset_security_config() -> None:
    """Reset the singleton. For tests only."""
    global _security_config
    _security_config = None
```

- [ ] **Step 2: Run tests to confirm pass**

Run: `pytest tests/security/test_security_config.py -v 2>&1 | tail -30`
Expected: PASS for all ~20 tests.

- [ ] **Step 3: Commit**

```bash
git add app/core/security_config.py
git commit -m "feat(security): add SecurityConfig with env var overrides"
```

---

### Task 1.1.4: Write failing test for SecurityHeadersMiddleware

**Files:**
- Create: `tests/security/test_security_headers.py`

- [ ] **Step 1: Create the test file**

```python
# -*- coding: utf-8 -*-
"""Tests for SecurityHeadersMiddleware.

Verifies every response (including errors) gets the security headers.
"""
from app.core.security_config import SECURITY_HEADERS, get_security_config


class TestSecurityHeadersAdded:
    def test_fixed_headers_present(self, client):
        r = client.get("/login.html")
        for header in SECURITY_HEADERS.keys():
            assert header.lower() in [k.lower() for k in r.headers.keys()], (
                f"Missing header: {header}"
            )

    def test_x_content_type_options_value(self, client):
        r = client.get("/login.html")
        assert r.headers["X-Content-Type-Options"] == "nosniff"

    def test_x_frame_options_value(self, client):
        r = client.get("/login.html")
        assert r.headers["X-Frame-Options"] == "DENY"

    def test_xss_protection_value(self, client):
        r = client.get("/login.html")
        assert r.headers["X-XSS-Protection"] == "1; mode=block"

    def test_referrer_policy_value(self, client):
        r = client.get("/login.html")
        assert "strict-origin" in r.headers["Referrer-Policy"]

    def test_permissions_policy_disables_sensors(self, client):
        r = client.get("/login.html")
        policy = r.headers["Permissions-Policy"]
        assert "geolocation=()" in policy
        assert "microphone=()" in policy
        assert "camera=()" in policy


class TestCSP:
    def test_csp_present(self, client):
        r = client.get("/login.html")
        assert "content-security-policy" in [k.lower() for k in r.headers.keys()]

    def test_csp_includes_self(self, client):
        r = client.get("/login.html")
        csp = r.headers["Content-Security-Policy"]
        assert "'self'" in csp
        assert "default-src" in csp

    def test_csp_customizable_via_env(self, client, monkeypatch):
        monkeypatch.setenv("SECURITY_CSP_POLICY", "default-src 'none'")
        from app.core.security_config import reset_security_config, get_security_config
        reset_security_config()
        r = client.get("/login.html")
        assert r.headers["Content-Security-Policy"] == "default-src 'none'"
        # Cleanup: reset singleton after this test
        reset_security_config()


class TestHSTS:
    def test_hsts_disabled_by_default(self, client):
        r = client.get("/login.html")
        assert "strict-transport-security" not in [k.lower() for k in r.headers.keys()]

    def test_hsts_enabled_when_configured(self, client, monkeypatch):
        monkeypatch.setenv("SECURITY_ENABLE_HSTS", "true")
        from app.core.security_config import reset_security_config
        reset_security_config()
        r = client.get("/login.html")
        assert "max-age=31536000" in r.headers["Strict-Transport-Security"]
        # Cleanup
        reset_security_config()


class TestHeadersOnErrorResponses:
    def test_404_response_has_security_headers(self, client):
        r = client.get("/nonexistent-route-12345")
        assert r.status_code == 404
        assert "x-content-type-options" in [k.lower() for k in r.headers.keys()]
        assert "x-frame-options" in [k.lower() for k in r.headers.keys()]

    def test_500_response_has_security_headers(self, client):
        # Trigger a 500 by sending invalid JSON to /api/auth/login
        r = client.post("/api/auth/login", data="not-json-at-all",
                       headers={"Content-Type": "application/json"})
        # Even errors should have security headers
        assert "x-content-type-options" in [k.lower() for k in r.headers.keys()]
```

- [ ] **Step 2: Run test to confirm failure**

Run: `pytest tests/security/test_security_headers.py -v 2>&1 | tail -10`
Expected: FAIL — security headers won't be present yet (no middleware installed).

- [ ] **Step 3: Commit failing test**

```bash
git add tests/security/test_security_headers.py
git commit -m "test(security): add SecurityHeadersMiddleware tests (red phase)"
```

---

### Task 1.1.5: Implement SecurityHeadersMiddleware

**Files:**
- Create: `app/core/middleware/__init__.py`
- Create: `app/core/middleware/security_headers.py`

- [ ] **Step 1: Create `app/core/middleware/__init__.py` (empty)**

Create the file with no content.

- [ ] **Step 2: Create `app/core/middleware/security_headers.py`**

```python
# -*- coding: utf-8 -*-
"""SecurityHeadersMiddleware — adds browser-level security headers to every response.

Adds:
  - Fixed headers from SECURITY_HEADERS (X-Content-Type-Options, X-Frame-Options, etc.)
  - Content-Security-Policy from config
  - Strict-Transport-Security (only when enable_hsts is True, i.e., HTTPS deployments)
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.security_config import SECURITY_HEADERS, get_security_config


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to every HTTP response (success and error)."""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        config = get_security_config()

        # Fixed headers — every response
        for header, value in SECURITY_HEADERS.items():
            response.headers[header] = value

        # Content-Security-Policy
        response.headers["Content-Security-Policy"] = config.csp_policy

        # HSTS — only on HTTPS deployments
        if config.enable_hsts:
            response.headers["Strict-Transport-Security"] = config.hsts_value

        return response
```

- [ ] **Step 3: Run tests to confirm pass**

Run: `pytest tests/security/test_security_headers.py -v 2>&1 | tail -20`
Expected: PASS — but only if main.py installs the middleware (next task).

**NOTE:** Tests will fail at this point because middleware is not yet installed. That's expected; next task installs it.

- [ ] **Step 4: Commit the implementation**

```bash
git add app/core/middleware/__init__.py app/core/middleware/security_headers.py
git commit -m "feat(security): add SecurityHeadersMiddleware"
```

---

### Task 1.1.6: Install SecurityHeadersMiddleware in main.py

**Files:**
- Modify: `main.py:209-230` (add middleware after FastAPI app creation, before existing CORS)

- [ ] **Step 1: Read main.py around app definition**

Run: `grep -n "FastAPI\|add_middleware\|CORSMiddleware\|app = " main.py | head -10`

Expected output similar to:
```
45:app = FastAPI(...)
212:app.add_middleware(
213:    CORSMiddleware,
```

- [ ] **Step 2: Add SecurityHeadersMiddleware before CORSMiddleware**

Locate the line `app.add_middleware(CORSMiddleware,` in main.py. Add this line **before** it:

```python
# Security headers middleware (MUST be added before CORS so preflight responses also get headers)
from app.core.middleware.security_headers import SecurityHeadersMiddleware
app.add_middleware(SecurityHeadersMiddleware)
```

Verify visually that the new line is placed BEFORE the CORSMiddleware line.

- [ ] **Step 3: Run security headers tests to confirm pass**

Run: `pytest tests/security/test_security_headers.py -v 2>&1 | tail -20`
Expected: All 13 tests PASS.

- [ ] **Step 4: Run regression to ensure nothing broken**

Run: `pytest tests/repositories/ tests/test_feature_flags.py tests/test_repository_factory.py tests/test_dual_db_fixture.py --tb=no -q 2>&1 | tail -3`
Expected: 240+ tests pass, no regressions.

- [ ] **Step 5: Verify manually with running server**

Start server briefly:
```bash
timeout 5 python main.py 2>&1 | head -15
```

Then in another shell:
```bash
curl -I http://127.0.0.1:8000/login.html 2>&1 | grep -E "X-Content-Type|X-Frame|Content-Security|Referrer"
```

Expected: All security headers present.

- [ ] **Step 6: Commit**

```bash
git add main.py
git commit -m "feat(security): install SecurityHeadersMiddleware in main.py"
```

---

### Slice 1.1 Gate

- [ ] `pytest tests/security/ -v` — all SecurityConfig + SecurityHeaders tests pass
- [ ] `pytest tests/repositories/ tests/test_feature_flags.py tests/test_repository_factory.py tests/test_dual_db_fixture.py` — no regressions
- [ ] Manual curl test shows security headers in response
- [ ] 5 commits made (test scaffold, config test, config impl, middleware test, middleware impl, middleware install)

**Slice 1.1 complete. Proceed to Slice 1.2.**

---

# Slice 1.2: CORS Strict Configuration

**Goal:** Fix `allow_origins=["*"]` + `allow_credentials=True` anti-pattern. Use environment-driven allowlist.

**Working directory:** `c:/Users/ZWC/Downloads/Kuromi-main/Kuromi-main/`

---

### Task 1.2.1: Write failing test for CORS strict config

**Files:**
- Create: `tests/security/test_cors.py`

- [ ] **Step 1: Create the test file**

```python
# -*- coding: utf-8 -*-
"""Tests for CORS strict configuration.

Verifies:
  - No wildcard origin allowed (anti-pattern fix)
  - Localhost defaults present
  - Allowed origins return correct CORS headers
  - Disallowed origins do not echo back
"""
from app.core.security_config import get_security_config, reset_security_config


class TestCORSConfiguration:
    def test_wildcard_origin_not_in_defaults(self):
        reset_security_config()
        cfg = get_security_config()
        assert "*" not in cfg.allowed_origins

    def test_localhost_in_defaults(self):
        reset_security_config()
        cfg = get_security_config()
        localhost_origins = [o for o in cfg.allowed_origins if "localhost" in o]
        assert len(localhost_origins) >= 3

    def test_env_override_replaces_defaults(self, monkeypatch):
        monkeypatch.setenv(
            "SECURITY_ALLOWED_ORIGINS",
            "https://prod.example.com"
        )
        reset_security_config()
        cfg = get_security_config()
        assert cfg.allowed_origins == ["https://prod.example.com"]


class TestCORSPreflight:
    def test_preflight_allowed_origin_returns_acao(self, client):
        headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        }
        r = client.options("/api/auth/login", headers=headers)
        # CORS preflight should echo back the allowed origin
        acao = r.headers.get("access-control-allow-origin", "")
        assert acao == "http://localhost:3000"

    def test_preflight_disallowed_origin_no_acao(self, client):
        headers = {
            "Origin": "http://evil.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        }
        r = client.options("/api/auth/login", headers=headers)
        # Disallowed origin should NOT get CORS headers
        acao = r.headers.get("access-control-allow-origin", "")
        assert acao != "http://evil.com"

    def test_actual_request_allowed_origin(self, client):
        headers = {"Origin": "http://localhost:3000"}
        r = client.get("/login.html", headers=headers)
        assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"


class TestCORSCredentials:
    def test_credentials_still_allowed_for_explicit_origins(self, client):
        # Browser sends with credentials — CORS allows this when origin is in allowlist
        headers = {
            "Origin": "http://localhost:3000",
            "Cookie": "session=abc123",
        }
        r = client.get("/login.html", headers=headers)
        assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"
        assert r.headers.get("access-control-allow-credentials") == "true"
```

- [ ] **Step 2: Run test to confirm failure**

Run: `pytest tests/security/test_cors.py -v 2>&1 | tail -20`
Expected: Some tests fail (wildcard origin is currently in use, CORS not yet updated).

- [ ] **Step 3: Commit failing test**

```bash
git add tests/security/test_cors.py
git commit -m "test(security): add CORS strict tests (red phase)"
```

---

### Task 1.2.2: Update CORS config in main.py

**Files:**
- Modify: `main.py:212-220` (CORSMiddleware block)

- [ ] **Step 1: Read current CORS config**

Locate the `app.add_middleware(CORSMiddleware,` block in main.py. It currently looks like:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    ...
)
```

- [ ] **Step 2: Replace CORS config with env-driven allowlist**

Replace the CORSMiddleware block with:

```python
# CORS — strict mode (no wildcard; uses SecurityConfig allowlist)
from app.core.security_config import get_security_config
config = get_security_config()
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    max_age=600,
)
```

- [ ] **Step 3: Run CORS tests to confirm pass**

Run: `pytest tests/security/test_cors.py -v 2>&1 | tail -15`
Expected: All 7 tests PASS.

- [ ] **Step 4: Run regression to ensure nothing broken**

Run: `pytest tests/repositories/ tests/contracts/ tests/test_feature_flags.py tests/test_repository_factory.py tests/test_dual_db_fixture.py --tb=no -q 2>&1 | tail -3`
Expected: 240+ tests pass, no regressions.

- [ ] **Step 5: Verify manually with running server**

```bash
timeout 5 python main.py 2>&1 &
sleep 3
curl -I -H "Origin: http://localhost:3000" http://127.0.0.1:8000/login.html 2>&1 | grep -i "access-control"
curl -I -H "Origin: http://evil.com" http://127.0.0.1:8000/login.html 2>&1 | grep -i "access-control"
```

Expected: First curl returns `access-control-allow-origin: http://localhost:3000`. Second curl does NOT echo evil.com.

- [ ] **Step 6: Commit**

```bash
git add main.py
git commit -m "fix(security): replace wildcard CORS with env-driven allowlist"
```

---

### Slice 1.2 Gate

- [ ] `pytest tests/security/test_cors.py -v` — all 7 CORS tests pass
- [ ] `allow_origins=["*"]` removed from main.py
- [ ] Manual curl confirms localhost allowed, evil.com blocked
- [ ] 240+ regression tests pass

**Slice 1.2 complete. Proceed to Slice 1.3.**

---

# Slice 1.3: RateLimitMiddleware (SlowAPI)

**Goal:** Add SlowAPI-based rate limiting. Configure tiered limits per endpoint category.

**Working directory:** `c:/Users/ZWC/Downloads/Kuromi-main/Kuromi-main/`

---

### Task 1.3.1: Install SlowAPI dependency

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add slowapi to requirements**

Find the line `httpx==0.25.2` in requirements.txt. Add `slowapi>=0.1.9` on a new line below it:

```
httpx==0.25.2
slowapi>=0.1.9
```

- [ ] **Step 2: Install SlowAPI**

Run: `pip install slowapi>=0.1.9`
Expected: Successfully installed slowapi-X.X.X

- [ ] **Step 3: Verify import**

Run: `python -c "from slowapi import Limiter; print('ok')"`
Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "chore(deps): add slowapi for rate limiting"
```

---

### Task 1.3.2: Write failing test for rate limiter module

**Files:**
- Create: `tests/security/test_rate_limit.py`

- [ ] **Step 1: Create the test file**

```python
# -*- coding: utf-8 -*-
"""Tests for rate limit decorators and SlowAPI integration.

Tests verify:
  - Decorators are importable
  - SlowAPI limiter instance is configured
  - Decorators apply correct limits based on SecurityConfig
"""
import pytest


class TestRateLimiterModule:
    def test_limiter_instance_exists(self):
        from app.core.rate_limiter import limiter
        assert limiter is not None

    def test_login_rate_limit_decorator_exists(self):
        from app.core.rate_limiter import login_rate_limit
        assert callable(login_rate_limit)

    def test_register_rate_limit_decorator_exists(self):
        from app.core.rate_limiter import register_rate_limit
        assert callable(register_rate_limit)

    def test_guest_login_rate_limit_decorator_exists(self):
        from app.core.rate_limiter import guest_login_rate_limit
        assert callable(guest_login_rate_limit)

    def test_ai_chat_rate_limit_decorator_exists(self):
        from app.core.rate_limiter import ai_chat_rate_limit
        assert callable(ai_chat_rate_limit)

    def test_default_api_rate_limit_decorator_exists(self):
        from app.core.rate_limiter import default_api_rate_limit
        assert callable(default_api_rate_limit)


class TestRateLimiterConfig:
    def test_login_limit_reflects_config(self, monkeypatch):
        monkeypatch.setenv("RATE_LIMIT_LOGIN", "10")
        from app.core.rate_limiter import login_rate_limit
        decorator = login_rate_limit()
        # The decorator should produce a callable
        assert callable(decorator)
```

- [ ] **Step 2: Run test to confirm failure**

Run: `pytest tests/security/test_rate_limit.py -v 2>&1 | tail -10`
Expected: FAIL with "ModuleNotFoundError: No module named 'app.core.rate_limiter'"

- [ ] **Step 3: Commit failing test**

```bash
git add tests/security/test_rate_limit.py
git commit -m "test(security): add rate limiter tests (red phase)"
```

---

### Task 1.3.3: Implement rate_limiter module

**Files:**
- Create: `app/core/auth_utils.py`
- Create: `app/core/rate_limiter.py`

- [ ] **Step 1: Create `app/core/auth_utils.py`**

```python
# -*- coding: utf-8 -*-
"""Auth utility helpers.

Currently exposes JWT decode without signature verification, used by
rate_limiter for per-user key extraction.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("starlearn.auth_utils")


def decode_jwt_no_verify(token: str) -> dict[str, Any] | None:
    """Decode a JWT WITHOUT verifying signature. Returns claims or None.

    Used by rate limiter to extract user_id from Authorization header
    for per-user rate limit keys. NEVER use for auth decisions.
    """
    try:
        # Lazy import to avoid pulling JWT lib at module load
        import jwt
        # decode without verification — signature check is bypassed
        return jwt.decode(token, options={"verify_signature": False})
    except Exception as e:
        logger.debug("decode_jwt_no_verify failed: %s", e)
        return None
```

- [ ] **Step 2: Create `app/core/rate_limiter.py`**

```python
# -*- coding: utf-8 -*-
"""Rate limiter using SlowAPI.

Single-process in-memory backend. State lost on restart (acceptable for dev/demo).
For production multi-process deployments, configure SlowAPI to use Redis.
"""
from __future__ import annotations

import logging

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.auth_utils import decode_jwt_no_verify
from app.core.security_config import get_security_config

logger = logging.getLogger("starlearn.rate_limiter")


def _user_or_ip_key(request: Request) -> str:
    """Extract user_id from JWT if present, else fall back to IP.

    Returns: "user:<uid>" for authenticated requests, "ip:<addr>" otherwise.
    """
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
        claims = decode_jwt_no_verify(token)
        if claims and claims.get("uid"):
            return f"user:{claims['uid']}"
    return f"ip:{get_remote_address(request)}"


# Initialize with per-IP key (default for unauthenticated endpoints)
config = get_security_config()
limiter = Limiter(key_func=get_remote_address)


def login_rate_limit():
    """5/min/IP for login attempts."""
    return limiter.limit(f"{config.login_rate_per_minute}/minute")


def register_rate_limit():
    """3/hour/IP for register attempts."""
    return limiter.limit(f"{config.register_rate_per_hour}/hour")


def guest_login_rate_limit():
    """10/hour/IP for guest login attempts."""
    return limiter.limit(f"{config.guest_login_rate_per_hour}/hour")


def ai_chat_rate_limit():
    """30/min per-user for AI chat endpoints."""
    return limiter.limit(f"{config.ai_chat_rate_per_minute}/minute", key_func=_user_or_ip_key)


def default_api_rate_limit():
    """60/min/IP default rate limit."""
    return limiter.limit(f"{config.default_api_rate_per_minute}/minute")
```

- [ ] **Step 3: Run tests to confirm pass**

Run: `pytest tests/security/test_rate_limit.py -v 2>&1 | tail -15`
Expected: All 10 tests PASS.

- [ ] **Step 4: Commit**

```bash
git add app/core/auth_utils.py app/core/rate_limiter.py
git commit -m "feat(security): add rate limiter with per-endpoint decorators"
```

---

### Task 1.3.4: Install SlowAPI middleware and exception handler in main.py

**Files:**
- Modify: `main.py` (add SlowAPI middleware + RateLimitExceeded handler)

- [ ] **Step 1: Read existing exception handlers in main.py**

Run: `grep -n "@app.exception_handler\|app.add_middleware\|app = FastAPI" main.py | head -15`

Expected: find `app = FastAPI(...)` and several `@app.exception_handler` lines.

- [ ] **Step 2: Add SlowAPI middleware installation**

Find the CORSMiddleware `app.add_middleware(...)` block (added in Slice 1.2). Add SlowAPI middleware AFTER it:

```python
# Rate limiting (SlowAPI)
from app.core.rate_limiter import limiter
app.state.limiter = limiter
from slowapi.middleware import SlowAPIMiddleware
app.add_middleware(SlowAPIMiddleware)
```

- [ ] **Step 3: Add RateLimitExceeded exception handler**

Find any existing `@app.exception_handler` line in main.py. Add a new one nearby:

```python
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    """Return 429 with Retry-After header when rate limit exceeded."""
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please slow down."},
        headers={"Retry-After": "60"},
    )
```

- [ ] **Step 4: Run security + regression tests**

Run: `pytest tests/security/test_rate_limit.py -v 2>&1 | tail -15`
Expected: All tests still pass.

Run: `pytest tests/repositories/ tests/contracts/ tests/test_feature_flags.py tests/test_repository_factory.py tests/test_dual_db_fixture.py --tb=no -q 2>&1 | tail -3`
Expected: 240+ tests pass, no regressions.

- [ ] **Step 5: Commit**

```bash
git add main.py
git commit -m "feat(security): install SlowAPI middleware and 429 handler"
```

---

### Task 1.3.5: Apply rate limit decorators to auth endpoints

**Files:**
- Modify: `main.py` (add decorators to /api/auth/login, /api/register, /api/login/guest)

- [ ] **Step 1: Read current auth endpoints**

Run: `grep -n "@app.post.*/api/auth/login\|@app.post.*/api/register\|@app.post.*/api/login/guest" main.py | head -10`

Expected: 3 endpoint decorators found.

- [ ] **Step 2: Find the login endpoint and add decorator**

Locate the `@app.post("/api/auth/login")` decorator line. It should look like:

```python
@app.post("/api/auth/login")
async def login(...):
```

Add the rate limit decorator ABOVE it:

```python
from app.core.rate_limiter import login_rate_limit


@app.post("/api/auth/login")
@login_rate_limit()
async def login(...):
    ...
```

- [ ] **Step 3: Find the register endpoint and add decorator**

Locate `@app.post("/api/register")` (note: this is the user register, not the legacy /api/register). Add:

```python
from app.core.rate_limiter import register_rate_limit


@app.post("/api/register")
@register_rate_limit()
async def register(...):
    ...
```

- [ ] **Step 4: Find the guest login endpoint and add decorator**

Locate `@app.post("/api/login/guest")` (or `/api/auth/login/guest`). Add:

```python
from app.core.rate_limiter import guest_login_rate_limit


@app.post("/api/login/guest")  # or appropriate path
@guest_login_rate_limit()
async def login_guest(...):
    ...
```

- [ ] **Step 5: Run security + regression tests**

Run: `pytest tests/security/ -v 2>&1 | tail -10`
Expected: Tests pass.

Run: `pytest tests/repositories/ tests/contracts/ tests/test_feature_flags.py tests/test_repository_factory.py tests/test_dual_db_fixture.py --tb=no -q 2>&1 | tail -3`
Expected: 240+ tests pass, no regressions.

- [ ] **Step 6: Verify rate limit triggers 429 manually**

Start server:
```bash
timeout 15 python main.py 2>&1 &
sleep 3
```

In another shell, hit login 6 times:
```bash
for i in 1 2 3 4 5 6; do
  curl -s -o /dev/null -w "Try $i: HTTP %{http_code}\n" \
    -X POST http://127.0.0.1:8000/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"wrong"}'
done
```

Expected: First 5 attempts return 401 (or 200/422). 6th attempt returns 429.

Wait for server to stop:
```bash
wait
```

- [ ] **Step 7: Commit**

```bash
git add main.py
git commit -m "feat(security): apply rate limit decorators to auth endpoints"
```

---

### Task 1.3.6: Apply rate limit decorators to AI chat endpoints

**Files:**
- Modify: `main.py` (add `@ai_chat_rate_limit()` to AI endpoints)

- [ ] **Step 1: Find AI chat endpoints**

Run: `grep -n "@app.post.*/api/v2/chat\|@app.post.*/api/v2/code" main.py | head -10`

Expected: Multiple endpoints (chat, chat/stream, code/review, etc.).

- [ ] **Step 2: Add decorator to `/api/v2/chat/stream`**

Locate `@app.post("/api/v2/chat/stream")`. Add above it:

```python
from app.core.rate_limiter import ai_chat_rate_limit


@app.post("/api/v2/chat/stream")
@ai_chat_rate_limit()
async def chat_stream(...):
    ...
```

- [ ] **Step 3: Add decorator to `/api/v2/code/review/stream` (if exists)**

Locate `@app.post("/api/v2/code/review/stream")`. Add `@ai_chat_rate_limit()` above it.

- [ ] **Step 4: Add decorator to other AI endpoints (up to 5 total)**

For each of: `/api/v2/code/review`, `/api/v2/debate/stream`, `/api/v2/course/chat/stream`, add `@ai_chat_rate_limit()` above the decorator. If any endpoint doesn't exist, skip it.

- [ ] **Step 5: Run security + regression tests**

Run: `pytest tests/security/ -v 2>&1 | tail -10`
Expected: All tests pass.

Run: `pytest tests/repositories/ tests/contracts/ tests/test_feature_flags.py tests/test_repository_factory.py tests/test_dual_db_fixture.py --tb=no -q 2>&1 | tail -3`
Expected: 240+ tests pass, no regressions.

- [ ] **Step 6: Commit**

```bash
git add main.py
git commit -m "feat(security): apply AI chat rate limit decorators"
```

---

### Task 1.3.7: Write integration test for rate limit + 429 handler

**Files:**
- Modify: `tests/security/test_rate_limit.py` (add integration test class)

- [ ] **Step 1: Append integration test class**

Append this to `tests/security/test_rate_limit.py`:

```python
class TestRateLimitIntegration:
    def test_login_returns_429_after_5_attempts(self, client):
        """5 attempts pass (200/401), 6th returns 429."""
        for i in range(5):
            r = client.post("/api/auth/login", json={
                "username": "admin", "password": "wrong"
            })
            assert r.status_code in (200, 401, 422), (
                f"Attempt {i+1}: unexpected status {r.status_code}"
            )

        r = client.post("/api/auth/login", json={
            "username": "admin", "password": "wrong"
        })
        assert r.status_code == 429
        assert "retry-after" in r.headers

    def test_429_response_has_security_headers(self, client):
        """Even rate-limited responses carry security headers."""
        for _ in range(6):
            client.post("/api/auth/login", json={
                "username": "admin", "password": "wrong"
            })
        r = client.post("/api/auth/login", json={
            "username": "admin", "password": "wrong"
        })
        assert r.status_code == 429
        assert "x-content-type-options" in [k.lower() for k in r.headers.keys()]
        assert "content-security-policy" in [k.lower() for k in r.headers.keys()]

    def test_register_limited_3_per_hour(self, client):
        """Registration limited to 3 per hour per IP."""
        for i in range(3):
            r = client.post("/api/register", json={
                "username": f"newuser_{i}",
                "password": "test1234",
            })
            # First attempt may succeed (200), next 2 may 400 (duplicate) or 422
            assert r.status_code in (200, 400, 422)

        r = client.post("/api/register", json={
            "username": "newuser_final",
            "password": "test1234",
        })
        assert r.status_code == 429

    def test_static_assets_not_rate_limited(self, client):
        """Static CSS/JS/HTML files not subject to API rate limit."""
        for _ in range(50):
            r = client.get("/css/tokens.css")
        assert r.status_code != 429
```

- [ ] **Step 2: Run tests to confirm pass**

Run: `pytest tests/security/test_rate_limit.py::TestRateLimitIntegration -v 2>&1 | tail -15`
Expected: All 4 integration tests pass.

- [ ] **Step 3: Commit**

```bash
git add tests/security/test_rate_limit.py
git commit -m "test(security): add rate limit integration tests"
```

---

### Slice 1.3 Gate

- [ ] Login endpoint returns 429 after 5 failed attempts
- [ ] Register endpoint returns 429 after 3 attempts
- [ ] AI chat endpoints have rate limit (verified by decorator presence)
- [ ] 429 response includes `Retry-After` header
- [ ] 429 response includes security headers
- [ ] 240+ regression tests pass
- [ ] 5+ commits made for this slice

**Slice 1.3 complete. Proceed to Slice 1.4.**

---

# Slice 1.4: OriginCheckMiddleware (CSRF Protection)

**Goal:** Block state-changing requests from unauthorized origins.

**Working directory:** `c:/Users/ZWC/Downloads/Kuromi-main/Kuromi-main/`

---

### Task 1.4.1: Write failing test for OriginCheckMiddleware

**Files:**
- Create: `tests/security/test_csrf.py`

- [ ] **Step 1: Create the test file**

```python
# -*- coding: utf-8 -*-
"""Tests for OriginCheckMiddleware (CSRF protection).

Verifies:
  - GET/HEAD/OPTIONS skip Origin check
  - POST/PUT/DELETE/PATCH require valid Origin or Referer
  - dev_mode bypasses check entirely
  - production mode rejects unauthorized origins
"""
import pytest


class TestOriginCheckDevMode:
    def test_dev_mode_post_without_origin_allowed(self, client):
        """In dev mode (default), CSRF check is skipped."""
        r = client.post("/api/auth/login", json={
            "username": "admin", "password": "123456"
        })
        assert r.status_code != 403

    def test_dev_mode_post_with_any_origin_allowed(self, client):
        r = client.post("/api/auth/login",
                       json={"username": "admin", "password": "123456"},
                       headers={"Origin": "http://random.com"})
        assert r.status_code != 403


class TestOriginCheckProductionMode:
    def test_get_skips_check_in_production(self, client, production_mode):
        r = client.get("/login.html")
        assert r.status_code != 403

    def test_post_without_origin_rejected(self, client, production_mode):
        r = client.post("/api/auth/login", json={
            "username": "admin", "password": "123456"
        })
        assert r.status_code == 403
        assert "Cross-origin" in r.json()["detail"] or "Origin" in r.json()["detail"]

    def test_post_with_valid_origin_allowed(self, client, production_mode):
        headers = {"Origin": "http://localhost:3000"}
        r = client.post("/api/auth/login",
                       json={"username": "admin", "password": "123456"},
                       headers=headers)
        assert r.status_code != 403

    def test_post_with_invalid_origin_rejected(self, client, production_mode):
        headers = {"Origin": "http://evil.com"}
        r = client.post("/api/auth/login",
                       json={"username": "admin", "password": "123456"},
                       headers=headers)
        assert r.status_code == 403

    def test_post_with_referer_fallback(self, client, production_mode):
        """If Origin missing, Referer is checked."""
        headers = {"Referer": "http://localhost:3000/login.html"}
        r = client.post("/api/auth/login",
                       json={"username": "admin", "password": "123456"},
                       headers=headers)
        assert r.status_code != 403

    def test_post_with_invalid_referer_rejected(self, client, production_mode):
        headers = {"Referer": "http://evil.com/page"}
        r = client.post("/api/auth/login",
                       json={"username": "admin", "password": "123456"},
                       headers=headers)
        assert r.status_code == 403

    def test_put_requires_valid_origin(self, client, production_mode):
        """PUT is a state-changing method."""
        headers = {"Origin": "http://evil.com"}
        r = client.put("/api/user/state/3",
                      json={"preferred_language": "en-US"},
                      headers=headers)
        assert r.status_code == 403

    def test_delete_requires_valid_origin(self, client, production_mode):
        """DELETE is a state-changing method."""
        headers = {"Origin": "http://evil.com"}
        r = client.delete("/api/weather/clear/3", headers=headers)
        assert r.status_code == 403
```

- [ ] **Step 2: Run test to confirm failure**

Run: `pytest tests/security/test_csrf.py -v 2>&1 | tail -10`
Expected: FAIL — OriginCheckMiddleware not yet implemented.

- [ ] **Step 3: Commit failing test**

```bash
git add tests/security/test_csrf.py
git commit -m "test(security): add OriginCheckMiddleware tests (red phase)"
```

---

### Task 1.4.2: Implement OriginCheckMiddleware

**Files:**
- Create: `app/core/middleware/origin_check.py`

- [ ] **Step 1: Create the file**

```python
# -*- coding: utf-8 -*-
"""OriginCheckMiddleware — CSRF protection via Origin/Referer header validation.

Only enforced for state-changing methods (POST/PUT/DELETE/PATCH).
GET/HEAD/OPTIONS are exempt (safe methods per RFC 7231).
"""
from __future__ import annotations

from urllib.parse import urlparse

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.security_config import get_security_config

# Methods that change server state — require Origin/Referer check
STATE_CHANGING_METHODS = {"POST", "PUT", "DELETE", "PATCH"}


class OriginCheckMiddleware(BaseHTTPMiddleware):
    """Reject state-changing requests from unauthorized origins."""

    async def dispatch(self, request: Request, call_next):
        config = get_security_config()

        # Dev mode bypass (developer convenience)
        if config.dev_mode:
            return await call_next(request)

        # Only check state-changing methods
        if request.method not in STATE_CHANGING_METHODS:
            return await call_next(request)

        # Extract Origin (preferred) or Referer (fallback)
        origin = request.headers.get("origin") or request.headers.get("referer", "")

        if not origin:
            return JSONResponse(
                status_code=403,
                content={"detail": "Cross-origin request rejected (no Origin/Referer header)"},
            )

        # Parse origin URL
        try:
            parsed = urlparse(origin)
            origin_url = f"{parsed.scheme}://{parsed.netloc}"
        except Exception:
            return JSONResponse(
                status_code=403,
                content={"detail": "Invalid Origin/Referer header"},
            )

        # Check against allowlist
        if origin_url not in config.allowed_origins:
            return JSONResponse(
                status_code=403,
                content={"detail": "Cross-origin request rejected (origin not allowed)"},
            )

        return await call_next(request)
```

- [ ] **Step 2: Run tests to confirm pass**

Run: `pytest tests/security/test_csrf.py -v 2>&1 | tail -20`
Expected: Tests in dev_mode PASS (because middleware skips). Tests in production_mode FAIL because middleware not installed yet (next task).

- [ ] **Step 3: Commit implementation**

```bash
git add app/core/middleware/origin_check.py
git commit -m "feat(security): add OriginCheckMiddleware (CSRF protection)"
```

---

### Task 1.4.3: Install OriginCheckMiddleware in main.py

**Files:**
- Modify: `main.py` (add middleware after SlowAPI)

- [ ] **Step 1: Find SlowAPI middleware installation**

Run: `grep -n "SlowAPIMiddleware" main.py`

Expected: 1 line found.

- [ ] **Step 2: Add OriginCheckMiddleware after SlowAPI**

Find the line `app.add_middleware(SlowAPIMiddleware)`. Add after it:

```python
# CSRF / Origin check (after rate limit to avoid wasting quota on bad requests)
from app.core.middleware.origin_check import OriginCheckMiddleware
app.add_middleware(OriginCheckMiddleware)
```

- [ ] **Step 3: Run CSRF tests to confirm pass**

Run: `pytest tests/security/test_csrf.py -v 2>&1 | tail -20`
Expected: All 10 tests PASS.

- [ ] **Step 4: Run regression**

Run: `pytest tests/repositories/ tests/contracts/ tests/test_feature_flags.py tests/test_repository_factory.py tests/test_dual_db_fixture.py --tb=no -q 2>&1 | tail -3`
Expected: 240+ tests pass.

- [ ] **Step 5: Commit**

```bash
git add main.py
git commit -m "feat(security): install OriginCheckMiddleware in main.py"
```

---

### Slice 1.4 Gate

- [ ] GET requests pass Origin check
- [ ] POST without Origin rejected in production mode (403)
- [ ] POST with valid Origin allowed in production mode
- [ ] POST with invalid Origin rejected (403)
- [ ] dev_mode bypasses check entirely
- [ ] 240+ regression tests pass
- [ ] 3+ commits made for this slice

**Slice 1.4 complete. Proceed to Slice 1.5.**

---

# Slice 1.5: RequestSizeLimitMiddleware + Integration + E2E Tests

**Goal:** Prevent DoS via large request bodies. Ship integration and E2E test suites.

**Working directory:** `c:/Users/ZWC/Downloads/Kuromi-main/Kuromi-main/`

---

### Task 1.5.1: Write failing test for RequestSizeLimitMiddleware

**Files:**
- Create: `tests/security/test_request_size.py`

- [ ] **Step 1: Create the test file**

```python
# -*- coding: utf-8 -*-
"""Tests for RequestSizeLimitMiddleware.

Verifies:
  - Normal requests allowed
  - Oversized requests rejected (413)
  - Streaming endpoints get higher limit
"""
import pytest


class TestRequestSizeLimit:
    def test_normal_size_allowed(self, client):
        """Small request body should pass."""
        r = client.post("/api/auth/login",
                       json={"username": "admin", "password": "123456"})
        assert r.status_code != 413

    def test_missing_content_length_allowed(self, client):
        """GET requests have no Content-Length — should pass."""
        r = client.get("/login.html")
        assert r.status_code != 413

    def test_oversized_normal_request_rejected(self, client):
        """11 MB body to non-streaming endpoint → 413."""
        big = "x" * (11 * 1024 * 1024)
        r = client.post("/api/auth/login", content=big)
        assert r.status_code == 413
        assert "too large" in r.json()["detail"].lower()

    def test_streaming_endpoint_higher_limit(self, client):
        """30 MB body to streaming endpoint should pass (50 MB limit)."""
        big = "x" * (30 * 1024 * 1024)
        # Use a streaming endpoint path
        r = client.post("/api/v2/chat/stream", content=big)
        assert r.status_code != 413

    def test_streaming_endpoint_still_has_limit(self, client):
        """60 MB body to streaming endpoint should fail (50 MB limit)."""
        big = "x" * (60 * 1024 * 1024)
        r = client.post("/api/v2/chat/stream", content=big)
        assert r.status_code == 413

    def test_invalid_content_length_rejected(self, client):
        """Malformed Content-Length header → 400."""
        r = client.post("/api/auth/login",
                       content="hello",
                       headers={"Content-Length": "not-a-number"})
        assert r.status_code in (400, 413)

    def test_size_limit_configurable_via_env(self, client, monkeypatch):
        """Custom size limit honored via env var."""
        monkeypatch.setenv("MAX_REQUEST_SIZE_MB", "5")
        from app.core.security_config import reset_security_config
        reset_security_config()

        # 6 MB should now fail
        big = "x" * (6 * 1024 * 1024)
        r = client.post("/api/auth/login", content=big)
        assert r.status_code == 413

        # Cleanup
        reset_security_config()
```

- [ ] **Step 2: Run test to confirm failure**

Run: `pytest tests/security/test_request_size.py -v 2>&1 | tail -10`
Expected: FAIL — middleware not yet implemented.

- [ ] **Step 3: Commit failing test**

```bash
git add tests/security/test_request_size.py
git commit -m "test(security): add RequestSizeLimitMiddleware tests (red phase)"
```

---

### Task 1.5.2: Implement RequestSizeLimitMiddleware

**Files:**
- Create: `app/core/middleware/request_size.py`

- [ ] **Step 1: Create the file**

```python
# -*- coding: utf-8 -*-
"""RequestSizeLimitMiddleware — prevents DoS via large request bodies.

Rejects requests with Content-Length exceeding the configured limit.
Streaming endpoints (AI chat, SSE) get a higher limit.
"""
from __future__ import annotations

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.security_config import get_security_config

# Endpoints that legitimately handle large payloads (AI streaming, file upload, etc.)
STREAMING_ENDPOINTS = {
    "/api/v2/chat/stream",
    "/api/v2/chat/onboard/stream",
    "/api/v2/classroom/stream",
    "/api/v2/course/bundle/generate/stream",
    "/api/v2/debate/stream",
    "/api/v2/code/review/stream",
    "/api/v2/course/chat/stream",
    "/api/v2/course/discussion/stream",
}


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests with oversized bodies."""

    async def dispatch(self, request: Request, call_next):
        config = get_security_config()

        content_length = request.headers.get("content-length")
        if not content_length:
            # GET requests or chunked uploads — let them through
            return await call_next(request)

        # Parse Content-Length
        try:
            size = int(content_length)
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={"detail": "Invalid Content-Length header"},
            )

        # Determine limit based on endpoint
        if request.url.path in STREAMING_ENDPOINTS:
            limit_mb = config.max_streaming_size_mb
        else:
            limit_mb = config.max_request_size_mb

        limit_bytes = limit_mb * 1024 * 1024

        if size > limit_bytes:
            return JSONResponse(
                status_code=413,
                content={"detail": f"Request body too large (max {limit_mb}MB)"},
            )

        return await call_next(request)
```

- [ ] **Step 2: Run tests to confirm pass (after middleware installed)**

Tests will FAIL until middleware is installed in main.py. That's expected.

- [ ] **Step 3: Commit implementation**

```bash
git add app/core/middleware/request_size.py
git commit -m "feat(security): add RequestSizeLimitMiddleware"
```

---

### Task 1.5.3: Install RequestSizeLimitMiddleware in main.py

**Files:**
- Modify: `main.py` (add middleware after OriginCheckMiddleware)

- [ ] **Step 1: Find OriginCheckMiddleware installation**

Run: `grep -n "OriginCheckMiddleware" main.py`

- [ ] **Step 2: Add RequestSizeLimitMiddleware after OriginCheckMiddleware**

Add this code after the OriginCheckMiddleware installation:

```python
# Request size limit (innermost security middleware)
from app.core.middleware.request_size import RequestSizeLimitMiddleware
app.add_middleware(RequestSizeLimitMiddleware)
```

- [ ] **Step 3: Run request size tests to confirm pass**

Run: `pytest tests/security/test_request_size.py -v 2>&1 | tail -15`
Expected: All 7 tests PASS.

- [ ] **Step 4: Run regression**

Run: `pytest tests/repositories/ tests/contracts/ tests/test_feature_flags.py tests/test_repository_factory.py tests/test_dual_db_fixture.py --tb=no -q 2>&1 | tail -3`
Expected: 240+ tests pass.

- [ ] **Step 5: Commit**

```bash
git add main.py
git commit -m "feat(security): install RequestSizeLimitMiddleware in main.py"
```

---

### Task 1.5.4: Write integration tests for full middleware stack

**Files:**
- Create: `tests/security/test_integration.py`

- [ ] **Step 1: Create the test file**

```python
# -*- coding: utf-8 -*-
"""Integration tests for the full security middleware stack.

Verifies that all 5 middlewares work together correctly:
  - SecurityHeadersMiddleware
  - CORSStrictMiddleware (via FastAPI CORSMiddleware)
  - RateLimitMiddleware (SlowAPI)
  - OriginCheckMiddleware
  - RequestSizeLimitMiddleware
"""
import pytest


class TestMiddlewareStack:
    def test_legal_request_flows_through_all(self, client):
        """Valid request should reach the handler and get all responses."""
        r = client.post("/api/auth/login",
                       json={"username": "admin", "password": "123456"},
                       headers={"Origin": "http://localhost:3000"})
        # Should NOT be blocked by security layer
        assert r.status_code != 403
        assert r.status_code != 429
        assert r.status_code != 413

    def test_security_headers_on_every_response_type(self, client):
        """Security headers present on 200, 404, 500."""
        # 200
        r = client.get("/login.html")
        assert "x-content-type-options" in [k.lower() for k in r.headers.keys()]

        # 404
        r = client.get("/nonexistent-route-12345")
        assert r.status_code == 404
        assert "x-content-type-options" in [k.lower() for k in r.headers.keys()]

    def test_429_response_has_security_headers(self, client):
        """Rate limit response carries security headers."""
        for _ in range(6):
            client.post("/api/auth/login", json={
                "username": "admin", "password": "wrong"
            })
        r = client.post("/api/auth/login", json={
            "username": "admin", "password": "wrong"
        })
        assert r.status_code == 429
        assert "x-content-type-options" in [k.lower() for k in r.headers.keys()]
        assert "content-security-policy" in [k.lower() for k in r.headers.keys()]

    def test_403_response_has_security_headers(self, client, production_mode):
        """CSRF 403 response carries security headers."""
        r = client.post("/api/auth/login",
                       json={"username": "admin", "password": "123456"},
                       headers={"Origin": "http://evil.com"})
        assert r.status_code == 403
        assert "x-content-type-options" in [k.lower() for k in r.headers.keys()]

    def test_413_response_has_security_headers(self, client):
        """Request size 413 response carries security headers."""
        big = "x" * (11 * 1024 * 1024)
        r = client.post("/api/auth/login", content=big)
        assert r.status_code == 413
        assert "x-content-type-options" in [k.lower() for k in r.headers.keys()]

    def test_order_security_headers_first(self, client):
        """Security headers should be on the response even if later middleware errors."""
        # Test with a request that would trigger rate limit
        for _ in range(6):
            client.post("/api/auth/login", json={
                "username": "admin", "password": "wrong"
            })
        r = client.post("/api/auth/login", json={
            "username": "admin", "password": "wrong"
        })
        # Rate limit response
        assert r.status_code == 429
        # All security headers present
        for header in ["x-content-type-options", "x-frame-options",
                      "referrer-policy", "permissions-policy"]:
            assert header in [k.lower() for k in r.headers.keys()]
```

- [ ] **Step 2: Run tests to confirm pass**

Run: `pytest tests/security/test_integration.py -v 2>&1 | tail -15`
Expected: All 6 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/security/test_integration.py
git commit -m "test(security): add full middleware stack integration tests"
```

---

### Task 1.5.5: Write E2E tests for critical security flows

**Files:**
- Create: `tests/security/test_e2e.py`

- [ ] **Step 1: Create the test file**

```python
# -*- coding: utf-8 -*-
"""End-to-end tests for critical security flows.

3 critical paths:
  1. Complete login flow (UI → API → JWT → authenticated request)
  2. Cross-origin attack blocked
  3. Rate limit triggers 429 with Retry-After
"""
import pytest


class TestSecurityE2E:
    def test_complete_login_flow(self, client):
        """UI simulates: login → receive JWT → use JWT in Authorization header."""
        # Step 1: Login
        r1 = client.post("/api/auth/login",
                        json={"username": "admin", "password": "123456"},
                        headers={"Origin": "http://localhost:3000"})
        assert r1.status_code == 200
        body = r1.json()
        assert "token" in body
        token = body["token"]

        # Step 2: Use token in Authorization header
        r2 = client.get("/api/user/state/3",
                       headers={"Authorization": f"Bearer {token}"})
        # Endpoint may 500 due to existing bug, but security layer must not block
        assert r2.status_code != 403
        assert r2.status_code != 429
        assert r2.status_code != 413

    def test_cross_origin_attack_blocked(self, client, production_mode):
        """Attacker site cannot make state-changing requests."""
        r = client.post("/api/auth/login",
                       json={"username": "admin", "password": "123456"},
                       headers={"Origin": "http://attacker.com",
                               "Referer": "http://attacker.com/phishing.html"})
        assert r.status_code == 403

        # Verify same request from legitimate origin works
        r2 = client.post("/api/auth/login",
                        json={"username": "admin", "password": "123456"},
                        headers={"Origin": "http://localhost:3000"})
        assert r2.status_code != 403

    def test_rate_limit_triggers_429_with_retry_after(self, client):
        """Burst of requests triggers 429 with Retry-After header."""
        for i in range(5):
            client.post("/api/auth/login", json={
                "username": "admin", "password": "wrong"
            })

        r = client.post("/api/auth/login", json={
            "username": "admin", "password": "wrong"
        })
        assert r.status_code == 429
        assert "retry-after" in r.headers
        assert r.json()["detail"] == "Too many requests. Please slow down."
```

- [ ] **Step 2: Run tests to confirm pass**

Run: `pytest tests/security/test_e2e.py -v 2>&1 | tail -10`
Expected: All 3 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/security/test_e2e.py
git commit -m "test(security): add E2E tests for critical security flows"
```

---

### Task 1.5.6: Final regression check + commit security report

**Files:**
- Modify: `SLICE_STATUS.md` (or new `docs/superpowers/security-1.1-status.md`)

- [ ] **Step 1: Run full regression suite**

Run: `pytest tests/repositories/ tests/contracts/ tests/test_feature_flags.py tests/test_repository_factory.py tests/test_dual_db_fixture.py tests/security/ --tb=no -q 2>&1 | tail -5`
Expected: 240+ existing tests pass + 50+ new security tests pass. Total ~290 tests.

- [ ] **Step 2: Verify no security regressions in existing flow**

Start server briefly and verify login still works:
```bash
timeout 10 python main.py 2>&1 &
sleep 3
curl -s -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"123456"}' | head -c 200
echo ""
wait
```

Expected: Returns 200 with token.

- [ ] **Step 3: Create final status doc**

Create `docs/superpowers/security-1.1-status.md`:

```markdown
# Spec 1: HTTP Security Layer — Completion Status

**Date:** 2026-07-17
**Status:** COMPLETE

## Implemented

- SecurityConfig with env var overrides
- SecurityHeadersMiddleware (CSP, X-Frame-Options, HSTS, etc.)
- CORS strict (replaced wildcard with allowlist)
- Rate limiting (SlowAPI) with tiered limits:
  - Login: 5/min/IP
  - Register: 3/hour/IP
  - AI chat: 30/min/user
  - Default API: 60/min/IP
- OriginCheckMiddleware (CSRF protection, dev-mode bypassable)
- RequestSizeLimitMiddleware (10MB default, 50MB streaming)

## Test Results

- 50+ new security tests pass
- 240+ existing tests pass (no regressions)
- 3 E2E flows verified

## Known Limitations

- Single-process only (SlowAPI in-memory backend)
- dev_mode=true by default (must set false in production)
- CORS allowlist hardcoded for dev (must configure for prod)

## Next Spec

Spec 2: Control Plane (trace ID + loop budget + state machine)
```

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/security-1.1-status.md
git commit -m "docs(security): mark HTTP security layer complete"
```

---

### Slice 1.5 Gate

- [ ] All 5 middlewares installed in main.py
- [ ] Integration tests pass (6 tests)
- [ ] E2E tests pass (3 tests)
- [ ] 240+ regression tests pass
- [ ] Manual verification: login still works, rate limit triggers 429
- [ ] Status doc created

**Slice 1.5 complete. Spec 1 (HTTP Security Layer) is done.**

---

# Final Acceptance

## All Slices Complete

- [x] **Slice 1.1:** SecurityConfig + SecurityHeaders — 5 commits
- [x] **Slice 1.2:** CORS strict — 1 commit
- [x] **Slice 1.3:** RateLimitMiddleware — 7 commits
- [x] **Slice 1.4:** OriginCheckMiddleware — 3 commits
- [x] **Slice 1.5:** RequestSizeLimitMiddleware + Integration + E2E — 6 commits

**Total: ~22 commits across 3 weeks**

## Success Criteria

- [ ] All 290+ tests pass (240 existing + 50 security)
- [ ] Security headers on every response (success + error)
- [ ] Rate limit prevents password爆破 (5/min/IP)
- [ ] CSRF protection blocks evil.com Origin
- [ ] DoS prevention (10MB limit, 50MB streaming)
- [ ] CORS allowlist configurable via env var
- [ ] dev_mode skips CSRF for DX
- [ ] No regressions in existing functionality

## Next Steps (Spec 2-5)

After Spec 1 ships:
1. **Spec 2: Control Plane** — trace ID + loop budget + state machine (tutor_engine)
2. **Spec 3: Safeguards** — max-iter + circuit breaker + deadlock detection
3. **Spec 4: Prompt Injection** — input classifier + output sanitizer
4. **Spec 5: PII Detection** — PII regex + encryption + audit

Each spec follows the same 5-slice pattern established in Spec 1.