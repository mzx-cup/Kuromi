# Spec 1: HTTP 安全层设计

**日期：** 2026-07-17
**状态：** 设计待 review
**作者：** Brainstorming 会话

---

## 1. 背景与目标

### 1.1 当前状态

项目存在以下安全缺口（按风险排序）：

| 缺口 | 严重度 | 影响 |
|------|-------|------|
| 无 Rate limiting | 🔴 高 | 登录端点可被密码爆破、AI 端点可被滥用 |
| `allow_origins=["*"]` + `allow_credentials=True` | 🔴 高 | CORS 规范禁止的组合，浏览器会拒绝带 cookie 跨域请求 |
| 无 CSRF 防护 | 🟡 中 | 跨站请求伪造可被利用 |
| 无 Security headers (CSP, HSTS, etc.) | 🟡 中 | 缺乏浏览器层防护 |
| 无 Request size limit | 🟡 中 | DoS 大包攻击 |

### 1.2 目标

实现 5 个安全中间件 + 集中化配置，覆盖 100% HTTP 层安全缺口：

- Rate limiting（防爆破 + 防滥用）
- CORS 严格化（修复反模式）
- CSRF 防护（防跨站请求伪造）
- Security headers（浏览器层防护）
- Request size limit（防 DoS）

### 1.3 非目标

- 不引入反向代理（nginx/Caddy）——纯 FastAPI 单进程
- 不引入 Redis 等分布式存储——单进程内存即可
- 不改变业务逻辑——纯中间件层
- 不修复 prompt injection / PII / 循环过程——这些是 Spec 2-5 的范围

---

## 2. 架构

### 2.1 中间件栈顺序

```
HTTP Request
    ↓
┌─────────────────────────────────────────┐
│  FastAPI Middleware Stack                │
│  ┌─────────────────────────────────┐    │
│  │ 1. SecurityHeadersMiddleware    │    │  CSP, X-Frame-Options, HSTS
│  ├─────────────────────────────────┤    │
│  │ 2. CORSStrictMiddleware         │    │  替换 allow_origins=["*"]
│  ├─────────────────────────────────┤    │
│  │ 3. RateLimitMiddleware          │    │  SlowAPI: IP + user 维度
│  ├─────────────────────────────────┤    │
│  │ 4. OriginCheckMiddleware        │    │  CSRF: Origin/Referer 白名单
│  ├─────────────────────────────────┤    │
│  │ 5. RequestSizeLimitMiddleware   │    │  防 DoS: body 大小限制
│  ├─────────────────────────────────┤    │
│  │ 6. (existing) log_requests      │    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
    ↓
Route Handler
```

**顺序理由：**
- Security headers 在最外层（所有响应都加）
- CORS 在 Security headers 后（避免 preflight 失败）
- Rate limit 在 CORS 后（避免恶意跨域请求消耗配额）
- Origin check 在 Rate limit 后（避免对非法请求消耗配额）
- Request size 在 Origin check 后（避免大包探测）

### 2.2 配置中心化（`app/core/security_config.py`）

```python
"""Centralized security configuration.

All security middleware read from this single source of truth.
Override defaults via environment variables.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env_list(name: str, default: str) -> list[str]:
    return [s.strip() for s in os.getenv(name, default).split(",") if s.strip()]


@dataclass(frozen=True)
class SecurityConfig:
    """Security middleware configuration. Loaded once at startup."""

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
    enable_hsts: bool = os.getenv("SECURITY_ENABLE_HSTS", "false").lower() == "true"
    hsts_value: str = "max-age=31536000; includeSubDomains"

    # Rate limits (per single-process instance)
    login_rate_per_minute: int = int(os.getenv("RATE_LIMIT_LOGIN", "5"))
    register_rate_per_hour: int = int(os.getenv("RATE_LIMIT_REGISTER", "3"))
    guest_login_rate_per_hour: int = int(os.getenv("RATE_LIMIT_GUEST", "10"))
    ai_chat_rate_per_minute: int = int(os.getenv("RATE_LIMIT_AI", "30"))
    default_api_rate_per_minute: int = int(os.getenv("RATE_LIMIT_DEFAULT", "60"))

    # Request size limits
    max_request_size_mb: int = int(os.getenv("MAX_REQUEST_SIZE_MB", "10"))
    max_streaming_size_mb: int = int(os.getenv("MAX_STREAMING_SIZE_MB", "50"))

    # Dev mode — skip Origin check (improve DX)
    dev_mode: bool = os.getenv("SECURITY_DEV_MODE", "true").lower() == "true"


# Singleton — initialized at module import
_security_config: SecurityConfig | None = None


def get_security_config() -> SecurityConfig:
    global _security_config
    if _security_config is None:
        _security_config = SecurityConfig()
    return _security_config


# Fixed security headers (returned by SecurityHeadersMiddleware)
SECURITY_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}
```

---

## 3. 组件详细规格

### 3.1 SecurityHeadersMiddleware

**位置：** `app/core/middleware/security_headers.py`

**职责：** 给每个 HTTP 响应添加安全 headers。

```python
"""SecurityHeadersMiddleware — adds browser-level security headers to every response."""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.security_config import SECURITY_HEADERS, get_security_config


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        config = get_security_config()

        # Fixed headers (every response)
        for header, value in SECURITY_HEADERS.items():
            response.headers[header] = value

        # CSP — configurable
        response.headers["Content-Security-Policy"] = config.csp_policy

        # HSTS — only on HTTPS (or when explicitly enabled)
        if config.enable_hsts:
            response.headers["Strict-Transport-Security"] = config.hsts_value

        return response
```

**关键决策：**
- 错误响应（4xx/5xx）也带 headers
- HSTS 仅 HTTPS 启用（dev 环境无 HSTS）
- CSP 初始严格（`unsafe-inline` 仅给内联脚本）

### 3.2 CORSStrictMiddleware

**位置：** 替换 `main.py` 当前 `CORSMiddleware` 配置

**职责：** 修复 `allow_origins=["*"]` + `allow_credentials=True` 的反模式。

```python
# main.py (修改)
from app.core.security_config import get_security_config

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_security_config().allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    max_age=600,
)
```

**关键修复：** 移除 `allow_origins=["*"]`，改用环境变量驱动的白名单。

### 3.3 RateLimitMiddleware（SlowAPI）

**位置：** `app/core/rate_limiter.py`

**职责：** 防爆破 + 防滥用。分级限速。

```python
"""Rate limiter using SlowAPI.

Single-process in-memory backend. State lost on restart (acceptable for dev/demo).
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.security_config import get_security_config


def _user_key(request):
    """Per-user rate limit key (if authenticated)."""
    # Try to extract user_id from JWT
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        # JWT decoded here (avoid circular import)
        from app.core.auth_utils import decode_jwt_no_verify
        try:
            payload = decode_jwt_no_verify(auth[7:])
            user_id = payload.get("uid")
            if user_id:
                return f"user:{user_id}"
        except Exception:
            pass
    return f"ip:{get_remote_address(request)}"


# Initialize with per-IP key (default for unauthenticated endpoints)
config = get_security_config()
limiter = Limiter(key_func=get_remote_address)


# Rate limit decorators — applied to specific endpoints
def login_rate_limit():
    return limiter.limit(f"{config.login_rate_per_minute}/minute")


def register_rate_limit():
    return limiter.limit(f"{config.register_rate_per_hour}/hour")


def guest_login_rate_limit():
    return limiter.limit(f"{config.guest_login_rate_per_hour}/hour")


def ai_chat_rate_limit():
    """Per-user rate limit for AI endpoints."""
    return limiter.limit(f"{config.ai_chat_rate_per_minute}/minute", key_func=_user_key)


def default_api_rate_limit():
    return limiter.limit(f"{config.default_api_rate_per_minute}/minute")
```

**main.py 挂载：**

```python
from app.core.rate_limiter import limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.responses import JSONResponse

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests", "retry_after": exc.detail},
        headers={"Retry-After": str(exc.detail)},
    )
```

**端点装饰器示例：**

```python
# main.py (修改)
from app.core.rate_limiter import login_rate_limit, register_rate_limit, default_api_rate_limit


@app.post("/api/auth/login")
@login_rate_limit()
async def login(...):
    ...


@app.post("/api/register")
@register_rate_limit()
async def register(...):
    ...


@app.post("/api/v2/chat/stream")
@ai_chat_rate_limit()
async def chat_stream(...):
    ...
```

**限速策略：**

| 端点 | 限制 | Key | 理由 |
|------|------|-----|------|
| `POST /api/auth/login` | 5/min | IP | 防密码爆破 |
| `POST /api/register` | 3/hour | IP | 防批量注册 |
| `POST /api/login/guest` | 10/hour | IP | 防访客滥用 |
| AI 聊天端点 | 30/min | user_id | 防滥用（按用户） |
| 其他 API | 60/min | IP | 默认 |
| 静态资源（CSS/JS/HTML） | 不限 | — | — |

### 3.4 OriginCheckMiddleware（CSRF 防护）

**位置：** `app/core/middleware/origin_check.py`

**职责：** state-changing 请求必须有合法 Origin/Referer。

```python
"""OriginCheckMiddleware — CSRF protection via Origin/Referer header validation.

Only enforced for state-changing methods (POST/PUT/DELETE/PATCH).
"""
from urllib.parse import urlparse

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from fastapi.responses import JSONResponse

from app.core.security_config import get_security_config


STATE_CHANGING_METHODS = {"POST", "PUT", "DELETE", "PATCH"}


class OriginCheckMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        config = get_security_config()

        # Dev mode — skip entirely
        if config.dev_mode:
            return await call_next(request)

        # Only check state-changing methods
        if request.method not in STATE_CHANGING_METHODS:
            return await call_next(request)

        # Extract Origin or Referer
        origin = request.headers.get("origin") or request.headers.get("referer", "")
        if not origin:
            return JSONResponse(
                status_code=403,
                content={"detail": "Cross-origin request rejected (no Origin/Referer)"},
            )

        # Parse and validate
        try:
            parsed = urlparse(origin)
            origin_url = f"{parsed.scheme}://{parsed.netloc}"
        except Exception:
            return JSONResponse(
                status_code=403,
                content={"detail": "Invalid Origin/Referer header"},
            )

        if origin_url not in config.allowed_origins:
            return JSONResponse(
                status_code=403,
                content={"detail": "Cross-origin request rejected"},
            )

        return await call_next(request)
```

**关键决策：**
- dev 模式完全跳过（开发体验优先）
- 仅 state-changing 方法强制检查
- API 直调（curl、Postman）通常无 Origin——这种情况下通过 `SECURITY_DEV_MODE=true` 跳过

### 3.5 RequestSizeLimitMiddleware

**位置：** `app/core/middleware/request_size.py`

**职责：** 防 DoS 大包攻击。

```python
"""RequestSizeLimitMiddleware — prevents DoS via large request bodies."""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from fastapi.responses import JSONResponse

from app.core.security_config import get_security_config


# Streaming endpoints get higher limits (AI chat streams large payloads)
STREAMING_ENDPOINTS = {
    "/api/v2/chat/stream",
    "/api/v2/chat/onboard/stream",
    "/api/v2/classroom/stream",
    "/api/v2/course/bundle/generate/stream",
}


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        config = get_security_config()

        content_length = request.headers.get("content-length")
        if not content_length:
            return await call_next(request)

        try:
            size = int(content_length)
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={"detail": "Invalid Content-Length header"},
            )

        # Determine limit based on endpoint
        if request.url.path in STREAMING_ENDPOINTS:
            limit_bytes = config.max_streaming_size_mb * 1024 * 1024
        else:
            limit_bytes = config.max_request_size_mb * 1024 * 1024

        if size > limit_bytes:
            return JSONResponse(
                status_code=413,
                content={"detail": f"Request body too large (max {limit_bytes // (1024*1024)}MB)"},
            )

        return await call_next(request)
```

---

## 4. main.py 集成

**修改 `main.py` 中间件挂载部分：**

```python
# main.py (现有 CORS 配置之后，添加新中间件)
from app.core.security_config import get_security_config
from app.core.middleware.security_headers import SecurityHeadersMiddleware
from app.core.middleware.origin_check import OriginCheckMiddleware
from app.core.middleware.request_size import RequestSizeLimitMiddleware
from app.core.rate_limiter import limiter
from slowapi.middleware import SlowAPIMiddleware

config = get_security_config()

# 1. Security headers (outermost)
app.add_middleware(SecurityHeadersMiddleware)

# 2. CORS (existing — config updated)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    max_age=600,
)

# 3. Rate limit (SlowAPI)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

# 4. CSRF / Origin check
app.add_middleware(OriginCheckMiddleware)

# 5. Request size limit
app.add_middleware(RequestSizeLimitMiddleware)

# 6. Existing log_requests (innermost)
# (already in main.py)
```

**Rate limit 异常处理器：**

```python
# main.py (在 app 定义后)
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests"},
        headers={"Retry-After": "60"},
    )
```

---

## 5. 测试策略

### 5.1 测试金字塔

```
        ┌─────────────────┐
        │  E2E (3 个流程)   │
        ├─────────────────┤
        │  集成 (10 测试)   │
        ├─────────────────┤
        │  单元 (30+ 测试)  │
        └─────────────────┘
```

### 5.2 单元测试（`tests/security/`）

#### `test_security_headers.py`

```python
class TestSecurityHeadersMiddleware:
    def test_adds_fixed_headers(self):
        r = client.get("/")
        for h in ["X-Content-Type-Options", "X-Frame-Options",
                  "Referrer-Policy", "Permissions-Policy"]:
            assert h.lower() in [k.lower() for k in r.headers.keys()]

    def test_csp_present_and_strict(self):
        r = client.get("/")
        csp = r.headers.get("content-security-policy", "")
        assert "'self'" in csp
        assert "default-src" in csp

    def test_hsts_disabled_by_default(self):
        r = client.get("/")
        assert "strict-transport-security" not in [k.lower() for k in r.headers.keys()]

    def test_hsts_enabled_via_config(self, monkeypatch):
        monkeypatch.setenv("SECURITY_ENABLE_HSTS", "true")
        from app.core.security_config import SecurityConfig
        cfg = SecurityConfig()
        assert cfg.enable_hsts is True

    def test_headers_on_error_response(self):
        r = client.get("/nonexistent-route-12345")
        assert r.status_code == 404
        assert "x-content-type-options" in r.headers
```

#### `test_cors.py`

```python
class TestCORSConfiguration:
    def test_wildcard_origin_removed(self):
        from app.core.security_config import get_security_config
        cfg = get_security_config()
        assert "*" not in cfg.allowed_origins

    def test_default_origins_include_localhost(self):
        from app.core.security_config import get_security_config
        cfg = get_security_config()
        localhost_origins = [o for o in cfg.allowed_origins if "localhost" in o]
        assert len(localhost_origins) >= 3

    def test_allowed_origin_in_response(self):
        headers = {"Origin": "http://localhost:3000"}
        r = client.get("/", headers=headers)
        assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"

    def test_disallowed_origin_no_cors_header(self):
        headers = {"Origin": "http://evil.com"}
        r = client.get("/", headers=headers)
        # CORS header should NOT echo evil.com
        assert r.headers.get("access-control-allow-origin") != "http://evil.com"
```

#### `test_rate_limit.py`

```python
class TestRateLimit:
    def test_login_limited_5_per_minute(self):
        for i in range(5):
            r = client.post("/api/auth/login", json={
                "username": "admin", "password": "wrong"
            })
            assert r.status_code in (200, 401)
        r = client.post("/api/auth/login", json={
            "username": "admin", "password": "wrong"
        })
        assert r.status_code == 429
        assert "retry-after" in r.headers

    def test_rate_limit_response_includes_headers(self):
        for _ in range(6):
            client.post("/api/auth/login", json={
                "username": "admin", "password": "wrong"
            })
        r = client.post("/api/auth/login", json={
            "username": "admin", "password": "wrong"
        })
        assert r.status_code == 429
        assert r.headers.get("x-ratelimit-limit") is not None
        assert r.headers.get("x-ratelimit-remaining") == "0"

    def test_register_stricter_than_login(self):
        for i in range(3):
            r = client.post("/api/register", json={
                "username": f"newuser_{i}", "password": "test1234"
            })
        r = client.post("/api/register", json={
            "username": "newuser_4", "password": "test1234"
        })
        assert r.status_code == 429

    def test_static_assets_not_rate_limited(self):
        for _ in range(100):
            r = client.get("/css/tokens.css")
        assert r.status_code != 429
```

#### `test_csrf.py`

```python
class TestOriginCheck:
    def test_get_request_skips_check(self, monkeypatch):
        monkeypatch.setenv("SECURITY_DEV_MODE", "false")
        r = client.get("/")
        assert r.status_code == 200

    def test_post_without_origin_rejected(self, monkeypatch):
        monkeypatch.setenv("SECURITY_DEV_MODE", "false")
        r = client.post("/api/auth/login", json={"username": "x", "password": "y"})
        assert r.status_code == 403

    def test_post_with_valid_origin_allowed(self, monkeypatch):
        monkeypatch.setenv("SECURITY_DEV_MODE", "false")
        headers = {"Origin": "http://localhost:3000"}
        r = client.post("/api/auth/login",
                       json={"username": "admin", "password": "123456"},
                       headers=headers)
        assert r.status_code != 403

    def test_post_with_invalid_origin_rejected(self, monkeypatch):
        monkeypatch.setenv("SECURITY_DEV_MODE", "false")
        headers = {"Origin": "http://evil.com"}
        r = client.post("/api/auth/login",
                       json={"username": "admin", "password": "123456"},
                       headers=headers)
        assert r.status_code == 403

    def test_dev_mode_skips_check(self):
        # 默认 SECURITY_DEV_MODE=true，POST 无 Origin 也通过
        r = client.post("/api/auth/login",
                       json={"username": "admin", "password": "123456"})
        assert r.status_code != 403
```

#### `test_request_size.py`

```python
class TestRequestSizeLimit:
    def test_oversized_request_rejected(self):
        big = "x" * (11 * 1024 * 1024)
        r = client.post("/api/foo", content=big)
        assert r.status_code == 413

    def test_streaming_endpoint_higher_limit(self):
        big = "x" * (30 * 1024 * 1024)
        r = client.post("/api/v2/chat/stream", content=big)
        assert r.status_code != 413

    def test_normal_request_allowed(self):
        small = "x" * (1024 * 1024)  # 1 MB
        r = client.post("/api/foo", content=small)
        assert r.status_code != 413
```

### 5.3 集成测试（`tests/security/test_integration.py`）

```python
class TestMiddlewareStack:
    def test_legal_request_flows_through_all(self):
        r = client.post("/api/auth/login",
                       json={"username": "admin", "password": "123456"},
                       headers={"Origin": "http://localhost:3000"})
        assert r.status_code != 403
        assert r.status_code != 429
        assert "x-content-type-options" in r.headers

    def test_429_response_has_security_headers(self):
        for _ in range(6):
            client.post("/api/auth/login", json={
                "username": "admin", "password": "wrong"
            })
        r = client.post("/api/auth/login", json={
            "username": "admin", "password": "wrong"
        })
        assert r.status_code == 429
        assert "x-content-type-options" in r.headers
        assert "content-security-policy" in r.headers

    def test_403_response_has_security_headers(self, monkeypatch):
        monkeypatch.setenv("SECURITY_DEV_MODE", "false")
        r = client.post("/api/auth/login",
                       json={"username": "admin", "password": "123456"},
                       headers={"Origin": "http://evil.com"})
        assert r.status_code == 403
        assert "x-content-type-options" in r.headers
```

### 5.4 E2E 测试（`tests/security/test_e2e.py`）

3 个关键流程：

```python
class TestSecurityE2E:
    def test_complete_login_flow(self):
        """UI → API → JWT → 后续请求带 token"""
        # 1. 登录
        r1 = client.post("/api/auth/login",
                        json={"username": "admin", "password": "123456"},
                        headers={"Origin": "http://localhost:3000"})
        assert r1.status_code == 200
        token = r1.json()["token"]

        # 2. 带 token 请求
        r2 = client.get("/api/user/state/3",
                       headers={"Authorization": f"Bearer {token}"})
        assert r2.status_code in (200, 500)  # 不被安全层拦截

    def test_cross_origin_attack_blocked(self, monkeypatch):
        """恶意 Origin 拦截"""
        monkeypatch.setenv("SECURITY_DEV_MODE", "false")
        r = client.post("/api/auth/login",
                       json={"username": "admin", "password": "123456"},
                       headers={"Origin": "http://attacker.com"})
        assert r.status_code == 403

    def test_rate_limit_triggers_429(self):
        """连续 6 次登录，第 6 次收到 429 + Retry-After"""
        for _ in range(5):
            client.post("/api/auth/login",
                       json={"username": "admin", "password": "wrong"})
        r = client.post("/api/auth/login",
                       json={"username": "admin", "password": "wrong"})
        assert r.status_code == 429
        assert "retry-after" in r.headers
        assert r.json()["detail"] == "Too many requests"
```

### 5.5 回归测试

确保不破坏现有功能：
- `tests/repositories/` 全部通过
- `tests/contracts/` 全部通过
- `tests/test_feature_flags.py` 全部通过
- `tests/test_repository_factory.py` 全部通过
- `tests/test_dual_db_fixture.py` 全部通过
- 现有的 240+ 测试一个不能少

---

## 6. 验收标准

### 6.1 Slice 1.1 验收（SecurityConfig + SecurityHeaders）

- [ ] 所有响应带 X-Content-Type-Options、X-Frame-Options、X-XSS-Protection
- [ ] 所有响应带 Content-Security-Policy
- [ ] dev 模式无 HSTS；可通过 `SECURITY_ENABLE_HSTS=true` 启用
- [ ] 配置通过环境变量覆盖
- [ ] 现有 240+ 测试无回归

### 6.2 Slice 1.2 验收（CORS 严格化）

- [ ] `allow_origins=["*"]` 移除
- [ ] 白名单生效（localhost:3000 通过、evil.com 拒绝）
- [ ] 现有登录/前端调用不破坏
- [ ] 配置可通过 `SECURITY_ALLOWED_ORIGINS` 覆盖

### 6.3 Slice 1.3 验收（RateLimitMiddleware）

- [ ] 登录端点 5/min/IP，第 6 次 429
- [ ] 注册端点 3/hour/IP
- [ ] AI 聊天 30/min/user
- [ ] 静态资源不限
- [ ] 响应带 X-RateLimit-* 和 Retry-After headers
- [ ] SlowAPI 重启后状态丢失（已接受，单进程）

### 6.4 Slice 1.4 验收（OriginCheckMiddleware）

- [ ] GET/HEAD/OPTIONS 不检查 Origin
- [ ] POST/PUT/DELETE/PATCH 必须有合法 Origin
- [ ] dev 模式完全跳过
- [ ] 跨域攻击（evil.com Origin）被 403

### 6.5 Slice 1.5 验收（RequestSizeLimitMiddleware + 集成）

- [ ] 普通请求 10 MB 限制
- [ ] 流式端点 50 MB 限制
- [ ] 超大请求返回 413
- [ ] 错误响应也带 security headers
- [ ] E2E 关键流程通过
- [ ] 现有 240+ 测试无回归

---

## 7. 风险与依赖

### 7.1 依赖

- `slowapi` (Python package) — FastAPI 生态的成熟 rate limiter
- 现有 `app.core.config.AppConfig` — 复用环境变量加载模式

### 7.2 风险

| 风险 | 等级 | 缓解 |
|------|------|------|
| Rate limit 误伤正常用户 | 🟡 中 | 分级限速，AI 端点用 per-user 而非 per-IP |
| CORS 白名单配置错误导致前端无法登录 | 🔴 高 | Slice 1.2 集成测试覆盖 |
| Security headers 影响 LLM SSE 流式响应 | 🟢 低 | BaseHTTPMiddleware 对流式透明 |
| dev 模式 Origin 检查关闭导致安全漏洞 | 🟡 中 | 生产部署必须设置 `SECURITY_DEV_MODE=false`，文档明确说明 |

### 7.3 不在范围内（后续 Spec 处理）

- Prompt injection 防护（Spec 4）
- PII 检测与脱敏（Spec 5）
- 循环过程控制平面（Spec 2）
- 循环过程防护栏（Spec 3）

---

## 8. 时间线

```
W1: Slice 1.1 (SecurityConfig + SecurityHeaders) + Slice 1.2 (CORS)
W2: Slice 1.3 (RateLimitMiddleware)
W3: Slice 1.4 (OriginCheck) + Slice 1.5 (RequestSize + 集成测试)
```

**总计：3 周 = 15 工作日**

---

## 9. 待决问题

> 这些问题在实施前应明确或接受风险。

1. **SlowAPI 在单进程下重启状态丢失** — 是否接受？（已选择接受）
2. **CORS 白名单默认值** — 是否包含项目实际的前端域名？（需用户提供）
3. **CSP 策略** — `unsafe-inline` 是否过松？（生产环境可收紧）
4. **Rate limit 数值** — 5/min/IP 是否合理？（需根据实际流量调整）

---

**文档版本：** 1.0
**下一步：** 用户 review → writing-plans skill → 实施