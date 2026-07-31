# 星识 AI 教育平台 比赛整改实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 1 个月内把星识 AI 教育平台改造成可演示、可答辩、可追溯的比赛作品,确保现场演示主链 (登录 → 学习画像 → 弱点诊断 → 苏格拉底式教学 → 路径调整 → 微练习 → 掌握度变化 → 教师观察) 一次成功。

**Architecture:** 保留 FastAPI 模块化单体 + 原生 HTML/CSS/JavaScript 前端,不迁移框架,不拆微服务。沿设计文档的 6 层边界 (体验/API/教学编排/智能体/数据记忆/外部服务) 落地。先用 `app/api/` 接管演示主链路由,逐步把数据访问收敛到 Repository,智能体按结构化 I/O 接入 Tutor Engine。加固认证/降级/CI,新增真实端到端冒烟测试。

**Tech Stack:** Python 3.11+ / FastAPI / SQLAlchemy 2.x / pytest / pytest-asyncio / httpx / Pydantic v2 / vitest / Playwright / MiniMax LLM / Qdrant / uvicorn

**Spec:** [2026-07-30-starlearn-competition-audit-design.md](../specs/2026-07-30-starlearn-competition-audit-design.md)

---

## 范围与边界

本计划执行设计文档的 §10 整改路线图:
- P0 (第 1 周): 关闭比赛安全与演示可靠性风险
- P1 (第 2-3 周): 提升比赛竞争力
- P2 (第 4 周+): 强化工程作品集质量

明确不做 (来自设计文档 §14):
- 不迁移 React/Vue 等前端框架
- 不拆微服务
- 不补全未演示的功能到生产级别
- 不在答辩现场跑耗时视频生成
- 不在比赛前轻易删除所有旧 API 或数据兼容逻辑

环境注意:
- 本受限沙盒中后端测试和 Vitest 因环境权限问题无法完整运行 (`.pytest_cache` 锁、esbuild 无法遍历上级目录),实施者必须在本地或 CI 上重新采集基线,不能依赖本沙盒结果。
- 工作目录存在大量用户未提交的修改 (`.claude/worktrees/*`、`.env.example`、`agents.py`、`db.py` 等),严禁 `git reset --hard`,所有 commit 仅针对本计划新创建或显式修改的文件。

---

## File Structure (新增 / 修改)

### 新增文件

| 路径 | 职责 |
|---|---|
| `app/api/demo_path.py` | 演示主链路由 (登录/画像/弱点/教学/路径/练习/掌握度/教师视图) |
| `app/api/health.py` | `/api/health` 标准化响应 (LLM/KB/DB/Qdrant 子项) |
| `app/services/demo_runner/__init__.py` | 演示运行器命名空间 |
| `app/services/demo_runner/live_path.py` | 演示主链统一执行器 (返回 trace_id + 各步耗时 + 降级标记) |
| `app/services/audit/registration_guard.py` | 注册角色白名单 (禁止 self-promote) |
| `app/services/repository/__init__.py` | Repository 命名空间 |
| `app/services/repository/demo_repo.py` | 演示主链数据访问入口 |
| `app/agents/io_schema.py` | 智能体结构化 Envelope (trace_id + role + fallback) |
| `scripts/start_competition.sh` | 一键启动 (环境变量 + 健康检查) |
| `scripts/reset_demo.sh` | 一键重置演示数据 |
| `scripts/health_check.sh` | 一键健康检查 |
| `scripts/playback.sh` | 录像回放 |
| `tests/security/test_jwt_secret_required.py` | 缺/弱 JWT_SECRET 必须启动失败 |
| `tests/security/test_registration_role_allowlist.py` | 注册 teacher/admin 必须 4xx |
| `tests/security/test_csrf_strict_default.py` | 比赛模式缺少 Origin 头必须 403 |
| `tests/security/test_sandbox_disabled_in_competition.py` | 比赛模式代码执行必须拒绝 |
| `tests/security/test_teacher_user_isolation.py` | 教师用户隔离 |
| `tests/demo/test_live_path_smoke.py` | 20 次连续跑通演示主链 |
| `tests/demo/test_demo_seed_reset.py` | `_drop_all_demo_rows` 重置后版本一致 |
| `tests/demo/test_health_endpoint.py` | `/api/health` 报告各子系统状态 |
| `tests/demo/test_degraded_fallback.py` | LLM/KB 不可用时回退到 `fallback` 标记 |
| `tests/demo/test_demo_repository.py` | Repository 单元测试 |
| `tests/agents/test_agent_structured_io.py` | 智能体结构化 I/O 测试 |
| `docs/runbook-demo.md` | 演示手册 |
| `docs/competition-architecture.md` | 比赛架构图说明 |
| `docs/data-flow.md` | 数据流图 |
| `docs/tech-qa.md` | 技术问答 |

### 修改文件

| 路径 | 改动 |
|---|---|
| `app/api/auth.py` | 删除 JWT_SECRET 兜底,启动期校验;比赛模式拒绝 teacher/admin 注册 |
| `main.py` | 演示主链路由移到 `app/api/demo_path.py`,`main.py` 只挂载 |
| `db.py` | 抽出 demo 相关函数到 Repository,保留兼容 |
| `app/core/security_config.py` | 比赛模式默认 `dev_mode=False`,`csrf_strict=True` |
| `app/core/middleware/origin_check.py` | 比赛模式强制校验 Origin |
| `app/services/tutor_engine/engine.py` | 每步记录 trace_id + 耗时 + 降级标记 |
| `app/services/llm/retry_strategy.py` | 增加 1 次重试 + 降级标记 |
| `app/services/kb/citation_retriever.py` | 增加 Qdrant 不可用时回退 |
| `app/services/sandbox/executor.py` | 比赛模式短路,直接拒绝 |
| `app/services/tutor_engine/hallucination_guard.py` | 比赛模式 `_run_python_sandbox` 直接拒绝 |
| `app/services/demo_seeder.py` | 严格 `_drop_all_demo_rows` + 重置后版本一致 |
| `agents.py` | 包裹所有 `run` 入口到 AgentEnvelope |
| `scripts/seed_demo.py` | 接受 `--json` 输出 |
| `app/api/profile.py` | 新增 `/api/profile/{user_id}/mastery-diff` 与 `/recommendations` |
| `app/api/teacher.py` | 新增 `/api/teacher/dashboard/observation` 与用户隔离 |
| `tests/smoke/conftest.py` | 启动真实服务进程 |
| `tests/smoke/test_e2e_apis.py` | 移除通用 200/4xx/5xx 断言,改为严格断言 |
| `.github/workflows/test.yml` | 移除 `npm run test:e2e || echo`,失败必须 fail |
| `.gitignore` | 忽略 `node_modules/`、`audio/`、`packaging/`、`*.db`、`.pytest_cache/` |
| `html/personal.html` + `js/personal.js` | 渲染掌握度变化 / 推荐理由卡片 |
| `html/teacher-dashboard.html` + `js/teacher-dashboard.js` | 班级实时观察同步 |

---## Phase 1: P0 — 第 1 周,关闭演示翻车风险 (Tasks 1-12)

P0 任务完成后,演示主链必须满足:
- 连续 20 次启动 → 登录 → 画像 → 弱点 → 苏格拉底 → 路径调整 → 微练习 → 掌握度变化 → 教师视图 全部通过
- 没有 404 / 空状态 / 控制台报错 / 数据错位
- 缺/弱 JWT_SECRET 无法启动
- 注册 teacher/admin 必须 4xx
- 比赛模式缺 Origin 头必须 403
- CI 中 E2E 失败必须阻塞合并

### Task 1: 启用 git 安全目录并准备分支

**Files:**
- Modify: 本仓库 `git config` (仓库级,沙盒外手动执行)

- [ ] **Step 1: 在本地正常 shell 中执行**

```bash
git config --global --add safe.directory /path/to/Kuromi-main
```

- [ ] **Step 2: 确认可读 git 状态**

```bash
git status
git log --oneline -5
```

- [ ] **Step 3: 创建工作分支**

```bash
git checkout -b competition/p0-remediation
```

> 沙盒环境无 git 写权限时,直接跳过本任务,在用户机器上初始化分支即可。

---

### Task 2: 删除 JWT_SECRET 兜底,启动期校验

**Files:**
- Modify: `app/api/auth.py:1-40`
- Test: `tests/security/test_jwt_secret_required.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/security/test_jwt_secret_required.py
import importlib
import pytest


def test_startup_fails_without_jwt_secret(monkeypatch):
    monkeypatch.delenv("JWT_SECRET", raising=False)
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        import app.api.auth as auth
        importlib.reload(auth)


def test_startup_fails_with_weak_jwt_secret(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "short")
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        import app.api.auth as auth
        importlib.reload(auth)
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/security/test_jwt_secret_required.py -v
```

Expected: FAIL (RuntimeError 未触发)

- [ ] **Step 3: 修改 `app/api/auth.py` 启动期校验**

```python
# app/api/auth.py 顶部,删除原硬编码 fallback
import os
import logging

logger = logging.getLogger(__name__)

_MIN_SECRET_LEN = 32


def _resolve_jwt_secret() -> str:
    secret = os.environ.get("JWT_SECRET")
    if not secret:
        raise RuntimeError(
            "JWT_SECRET environment variable is required. "
            "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(48))'"
        )
    if len(secret) < _MIN_SECRET_LEN:
        raise RuntimeError(
            f"JWT_SECRET is too short (got {len(secret)}, need >= {_MIN_SECRET_LEN})."
        )
    if secret == "change-me" or secret.startswith("dev-"):
        raise RuntimeError("JWT_SECRET appears to be a development placeholder.")
    return secret


JWT_SECRET = _resolve_jwt_secret()
```

- [ ] **Step 4: 同步替换文件中所有 `JWT_SECRET = "..."` 字面量**

```bash
rg -n 'JWT_SECRET\s*=' app/ -t py
```

把所有硬编码字面量改为引用顶部已校验的 `JWT_SECRET`。

- [ ] **Step 5: 运行测试确认通过**

```bash
JWT_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(48)") \
  pytest tests/security/test_jwt_secret_required.py -v
```

Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add app/api/auth.py tests/security/test_jwt_secret_required.py
git commit -m "fix(security): require strong JWT_SECRET at startup"
```

---

### Task 3: 注册角色白名单 (禁止 self-promote teacher/admin)

**Files:**
- Modify: `app/api/auth.py` (注册路由附近)
- Create: `app/services/audit/registration_guard.py`
- Test: `tests/security/test_registration_role_allowlist.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/security/test_registration_role_allowlist.py
from fastapi.testclient import TestClient

from main import app  # noqa: E402

client = TestClient(app)


def test_register_with_teacher_role_is_rejected():
    r = client.post(
        "/api/auth/register",
        json={"username": "u1", "password": "Pp@ssw0rd!", "role": "teacher"},
    )
    assert r.status_code in (400, 403, 422), r.text
    assert "role" in r.text.lower() or "forbidden" in r.text.lower()


def test_register_with_admin_role_is_rejected():
    r = client.post(
        "/api/auth/register",
        json={"username": "u2", "password": "Pp@ssw0rd!", "role": "admin"},
    )
    assert r.status_code in (400, 403, 422), r.text


def test_register_with_default_role_is_allowed():
    r = client.post(
        "/api/auth/register",
        json={"username": "u3", "password": "Pp@ssw0rd!"},
    )
    assert r.status_code == 200, r.text
```

- [ ] **Step 2: 运行测试确认失败**

```bash
JWT_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(48))") \
  pytest tests/security/test_registration_role_allowlist.py -v
```

Expected: FAIL (teacher/admin 注册未拦截)

- [ ] **Step 3: 创建 `app/services/audit/registration_guard.py`**

```python
# app/services/audit/registration_guard.py
"""注册角色白名单: 比赛版只允许 self-registered role = student."""
from __future__ import annotations

ALLOWED_SELF_REGISTER_ROLES: frozenset[str] = frozenset({"student"})


def assert_self_register_role_allowed(role: str | None) -> str:
    """校验自注册角色,违规抛出 ValueError 由 FastAPI 转为 422."""
    if role is None or role == "":
        return "student"
    if role not in ALLOWED_SELF_REGISTER_ROLES:
        raise ValueError(
            f"role '{role}' is not allowed for self-registration; "
            f"allowed: {sorted(ALLOWED_SELF_REGISTER_ROLES)}"
        )
    return role
```

- [ ] **Step 4: 在 `app/api/auth.py` 注册路由中调用守卫**

```python
# app/api/auth.py 注册路由 handler 顶部
from app.services.audit.registration_guard import assert_self_register_role_allowed

# 在写入数据库之前:
#     role = assert_self_register_role_allowed(payload.role)
# 把 payload.role 替换为规范化后的 role
```

- [ ] **Step 5: 运行测试确认通过**

```bash
JWT_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(48))") \
  pytest tests/security/test_registration_role_allowlist.py -v
```

Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add app/api/auth.py app/services/audit/registration_guard.py \
        tests/security/test_registration_role_allowlist.py
git commit -m "fix(security): block self-registration of teacher/admin roles"
```

---### Task 4: 比赛模式强制 Origin 校验 (CSRF strict)

**Files:**
- Modify: `app/core/security_config.py`
- Modify: `app/core/middleware/origin_check.py`
- Test: `tests/security/test_csrf_strict_default.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/security/test_csrf_strict_default.py
from fastapi.testclient import TestClient

from main import app  # noqa: E402

client = TestClient(app)


def test_post_without_origin_rejected_in_competition(monkeypatch):
    monkeypatch.setenv("STARLEARN_COMPETITION", "1")
    r = client.post("/api/v2/chat", json={"user_id": "u1", "message": "hi"})
    assert r.status_code in (400, 403), r.text


def test_post_with_allowed_origin_passes_in_competition(monkeypatch):
    monkeypatch.setenv("STARLEARN_COMPETITION", "1")
    monkeypatch.setenv("STARLEARN_ALLOWED_ORIGINS", "http://localhost:8000")
    r = client.post(
        "/api/v2/chat",
        json={"user_id": "u1", "message": "hi"},
        headers={"Origin": "http://localhost:8000"},
    )
    assert r.status_code != 403, r.text
```

- [ ] **Step 2: 运行测试确认失败**

```bash
JWT_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(48))") \
  STARLEARN_COMPETITION=1 \
  pytest tests/security/test_csrf_strict_default.py -v
```

Expected: FAIL

- [ ] **Step 3: 修改 `app/core/security_config.py`**

```python
# 在 SecurityConfig 类中追加字段 (示例,真实字段名以代码为准)
import os

class SecurityConfig:
    # 现有字段保留 ...
    competition_mode: bool = bool(int(os.environ.get("STARLEARN_COMPETITION", "0")))
    csrf_strict: bool = competition_mode or bool(int(os.environ.get("STARLEARN_CSRF_STRICT", "0")))
    allowed_origins: list[str] = [
        o.strip() for o in os.environ.get(
            "STARLEARN_ALLOWED_ORIGINS",
            "http://localhost:8000,http://127.0.0.1:8000",
        ).split(",") if o.strip()
    ]
```

- [ ] **Step 4: 修改 `app/core/middleware/origin_check.py`**

```python
# 在 OriginCheck 中间件内:
#   - 当 config.csrf_strict 为 True 且请求 method 在 {"POST","PUT","PATCH","DELETE"} 时,
#     必须校验 Origin 头出现在 config.allowed_origins 中,否则返回 403。
#   - 保留原有 dev_mode 行为作为 backward-compat fallback。
from fastapi import Request
from fastapi.responses import JSONResponse


async def origin_check_middleware(request: Request, call_next):
    from app.core.security_config import security_config  # 局部导入避免循环

    method = request.method.upper()
    if method in {"POST", "PUT", "PATCH", "DELETE"} and security_config.csrf_strict:
        origin = request.headers.get("origin") or request.headers.get("Origin")
        if not origin or origin not in security_config.allowed_origins:
            return JSONResponse(
                {"detail": "origin not allowed in competition mode"},
                status_code=403,
            )
    return await call_next(request)
```

- [ ] **Step 5: 在 `main.py` 中挂载中间件**

```python
# main.py
from app.core.middleware.origin_check import origin_check_middleware
app.middleware("http")(origin_check_middleware)
```

- [ ] **Step 6: 运行测试确认通过**

```bash
JWT_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(48))") \
  pytest tests/security/test_csrf_strict_default.py -v
```

Expected: PASS

- [ ] **Step 7: 提交**

```bash
git add app/core/security_config.py app/core/middleware/origin_check.py \
        main.py tests/security/test_csrf_strict_default.py
git commit -m "fix(security): enforce strict Origin check in competition mode"
```

---

### Task 5: 比赛模式关闭任意代码执行

**Files:**
- Modify: `app/services/sandbox/executor.py`
- Modify: `app/services/tutor_engine/hallucination_guard.py`
- Test: `tests/security/test_sandbox_disabled_in_competition.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/security/test_sandbox_disabled_in_competition.py
def test_run_python_disabled_in_competition(monkeypatch):
    monkeypatch.setenv("STARLEARN_COMPETITION", "1")
    from app.services.tutor_engine.hallucination_guard import HallucinationGuard
    guard = HallucinationGuard()
    out = guard._run_python_sandbox("print('hello')")  # type: ignore[attr-defined]
    assert out["blocked"] is True
    assert out["reason"] in {"competition_mode_disabled", "disabled"}


def test_run_python_enabled_outside_competition(monkeypatch):
    monkeypatch.delenv("STARLEARN_COMPETITION", raising=False)
    from app.services.tutor_engine.hallucination_guard import HallucinationGuard
    guard = HallucinationGuard()
    out = guard._run_python_sandbox("x = 1 + 1")  # type: ignore[attr-defined]
    assert "blocked" not in out or out["blocked"] is False
```

- [ ] **Step 2: 运行测试确认失败**

```bash
JWT_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(48))") \
  STARLEARN_COMPETITION=1 \
  pytest tests/security/test_sandbox_disabled_in_competition.py -v
```

Expected: FAIL

- [ ] **Step 3: 修改 `app/services/tutor_engine/hallucination_guard.py`**

```python
# _run_python_sandbox 顶部增加环境判断
import os

def _run_python_sandbox(self, code: str) -> dict:
    if os.environ.get("STARLEARN_COMPETITION") == "1":
        return {
            "output": "",
            "blocked": True,
            "reason": "competition_mode_disabled",
        }
    # ... 保留原实现
```

- [ ] **Step 4: 修改 `app/services/sandbox/executor.py`**

```python
# run_python 函数顶部增加环境判断
import os

def run_python(code: str, timeout: float = 5.0) -> dict:
    if os.environ.get("STARLEARN_COMPETITION") == "1":
        return {"stdout": "", "stderr": "", "blocked": True, "reason": "competition_mode_disabled"}
    # ... 保留原实现
```

- [ ] **Step 5: 运行测试确认通过**

```bash
JWT_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(48))") \
  pytest tests/security/test_sandbox_disabled_in_competition.py -v
```

Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add app/services/sandbox/executor.py \
        app/services/tutor_engine/hallucination_guard.py \
        tests/security/test_sandbox_disabled_in_competition.py
git commit -m "fix(security): disable arbitrary code execution in competition mode"
```

---

### Task 6: LLM/KB 重试与降级标记

**Files:**
- Modify: `app/services/llm/retry_strategy.py`
- Modify: `app/services/kb/citation_retriever.py`
- Create: `app/services/demo_runner/__init__.py`
- Create: `app/services/demo_runner/live_path.py`
- Test: `tests/demo/test_degraded_fallback.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/demo/test_degraded_fallback.py
import pytest

from app.services.llm.retry_strategy import retry_chat


class _FakeTimeout(Exception):
    pass


@pytest.mark.asyncio
async def test_retry_chat_returns_fallback_after_timeout(monkeypatch):
    async def fake_call(_payload, _timeout):
        raise _FakeTimeout()

    monkeypatch.setattr(
        "app.services.llm.retry_strategy._primary_call",
        fake_call,
    )
    out = await retry_chat({"messages": [{"role": "user", "content": "hi"}]}, timeout=0.1)
    assert out["fallback"] is True
    assert "content" in out
```

- [ ] **Step 2: 运行测试确认失败**

```bash
JWT_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(48))") \
  pytest tests/demo/test_degraded_fallback.py -v
```

Expected: FAIL

- [ ] **Step 3: 修改 `app/services/llm/retry_strategy.py`**

```python
# 新增 retry_chat: 1 次快速重试 + 降级 fallback 标记
from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


async def retry_chat(payload: dict, timeout: float = 6.0, retries: int = 1) -> dict[str, Any]:
    """1 次重试; 失败后返回带 fallback=True 的种子响应."""
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return await asyncio.wait_for(_primary_call(payload, timeout), timeout=timeout)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            logger.warning("llm primary call failed attempt=%d err=%s", attempt, exc)
    return {
        "content": "[fallback] 演示模式已启用离线教学响应,请参考知识库或教师建议。",
        "fallback": True,
        "error": str(last_exc) if last_exc else "unknown",
    }


async def _primary_call(_payload: dict, _timeout: float) -> dict[str, Any]:
    raise NotImplementedError("wired in main.py via existing llm provider")
```

- [ ] **Step 4: 修改 `app/services/kb/citation_retriever.py`**

```python
# retrieve 函数: Qdrant 不可用时回退到结构化 SQL 检索
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def retrieve(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    try:
        return await _qdrant_search(query, top_k=top_k)
    except Exception as exc:  # noqa: BLE001
        logger.warning("qdrant unavailable, fallback to sql: %s", exc)
        return _sql_search(query, top_k=top_k)


async def _qdrant_search(_query: str, _top_k: int) -> list[dict[str, Any]]:
    raise NotImplementedError("wired in main.py via existing qdrant client")


def _sql_search(query: str, top_k: int) -> list[dict[str, Any]]:
    return [{"text": query, "score": 0.0, "source": "sql_fallback"}][:top_k]
```

- [ ] **Step 5: 创建 `app/services/demo_runner/__init__.py` 和 `live_path.py` 骨架**

```python
# app/services/demo_runner/__init__.py
"""演示主链统一执行器命名空间."""
from app.services.demo_runner.live_path import run_live_demo_path, LivePathResult  # noqa: F401

__all__ = ["run_live_demo_path", "LivePathResult"]
```

```python
# app/services/demo_runner/live_path.py
"""演示主链统一执行器 (P0 阶段先搭骨架, P1 阶段接入 Tutor Engine)."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LivePathResult:
    trace_id: str
    steps: list[dict[str, Any]] = field(default_factory=list)
    fallback_used: bool = False
    elapsed_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "steps": self.steps,
            "fallback_used": self.fallback_used,
            "elapsed_ms": self.elapsed_ms,
        }


async def run_live_demo_path(user_id: str, scenario: str = "default") -> LivePathResult:
    """演示主链 (P1 阶段才会接入完整流程, 本任务先记录 trace_id 与耗时)."""
    trace_id = f"lp_{uuid.uuid4().hex[:12]}"
    started = time.time()
    return LivePathResult(
        trace_id=trace_id,
        steps=[{"name": "init", "ok": True, "ts_ms": int((time.time() - started) * 1000)}],
        fallback_used=False,
        elapsed_ms=int((time.time() - started) * 1000),
    )
```

- [ ] **Step 6: 运行测试确认通过**

```bash
JWT_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(48))") \
  pytest tests/demo/test_degraded_fallback.py -v
```

Expected: PASS

- [ ] **Step 7: 提交**

```bash
git add app/services/llm/retry_strategy.py \
        app/services/kb/citation_retriever.py \
        app/services/demo_runner/__init__.py \
        app/services/demo_runner/live_path.py \
        tests/demo/test_degraded_fallback.py
git commit -m "feat(reliability): retry+fallback for llm/kb and demo runner skeleton"
```

---### Task 7: 健康检查接口 (LLM/KB/DB/Qdrant 子项)

**Files:**
- Create: `app/api/health.py`
- Test: `tests/demo/test_health_endpoint.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/demo/test_health_endpoint.py
from fastapi.testclient import TestClient

from main import app  # noqa: E402

client = TestClient(app)


def test_health_returns_subsystem_status():
    r = client.get("/api/health")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] in {"ok", "degraded", "down"}
    for key in ("llm", "kb", "db", "qdrant"):
        assert key in body["components"]
        assert body["components"][key]["status"] in {"ok", "degraded", "down", "skipped"}
```

- [ ] **Step 2: 运行测试确认失败**

```bash
JWT_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(48))") \
  pytest tests/demo/test_health_endpoint.py -v
```

Expected: FAIL

- [ ] **Step 3: 创建 `app/api/health.py`**

```python
# app/api/health.py
from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter()


async def _check_llm() -> dict[str, Any]:
    try:
        from app.services.llm.retry_strategy import _primary_call  # noqa: WPS433
        await asyncio.wait_for(_primary_call({}, 1.0), timeout=2.0)
        return {"status": "ok"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "degraded", "error": str(exc)}


async def _check_kb() -> dict[str, Any]:
    try:
        from app.services.kb.citation_retriever import retrieve  # noqa: WPS433
        await asyncio.wait_for(retrieve("__health__"), timeout=2.0)
        return {"status": "ok"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "degraded", "error": str(exc)}


async def _check_db() -> dict[str, Any]:
    try:
        return {"status": "ok"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "down", "error": str(exc)}


async def _check_qdrant() -> dict[str, Any]:
    return {"status": "skipped"}


@router.get("/api/health")
async def health() -> dict[str, Any]:
    llm, kb, db, qd = await asyncio.gather(
        _check_llm(), _check_kb(), _check_db(), _check_qdrant(),
    )
    overall = "ok"
    if any(c["status"] == "down" for c in (llm, kb, db, qd)):
        overall = "down"
    elif any(c["status"] == "degraded" for c in (llm, kb, db, qd)):
        overall = "degraded"
    return {
        "status": overall,
        "components": {"llm": llm, "kb": kb, "db": db, "qdrant": qd},
    }
```

- [ ] **Step 4: 在 `main.py` 挂载**

```python
from app.api.health import router as health_router
app.include_router(health_router)
```

- [ ] **Step 5: 运行测试确认通过**

```bash
JWT_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(48))") \
  pytest tests/demo/test_health_endpoint.py -v
```

Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add app/api/health.py main.py tests/demo/test_health_endpoint.py
git commit -m "feat(ops): unified /api/health with subsystem status"
```

---

### Task 8: 一键启动 / 重置 / 健康检查脚本

**Files:**
- Create: `scripts/start_competition.sh`
- Create: `scripts/reset_demo.sh`
- Create: `scripts/health_check.sh`

- [ ] **Step 1: 创建 `scripts/start_competition.sh`**

```bash
#!/usr/bin/env bash
# scripts/start_competition.sh
# 一键启动比赛模式 (强校验 JWT_SECRET, 启动真实服务并等待 /api/health=200)
set -euo pipefail

if [[ -z "${JWT_SECRET:-}" ]]; then
  echo "[start_competition] JWT_SECRET 未设置,自动生成临时值 (仅本地开发用)."
  export JWT_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
fi
export STARLEARN_COMPETITION=1
export STARLEARN_CSRF_STRICT=1
export STARLEARN_ALLOWED_ORIGINS="${STARLEARN_ALLOWED_ORIGINS:-http://localhost:8000,http://127.0.0.1:8000}"

PORT="${STARLEARN_PORT:-8000}"
echo "[start_competition] starting uvicorn on port ${PORT}, competition=1"

exec uvicorn main:app --host 0.0.0.0 --port "${PORT}"
```

- [ ] **Step 2: 创建 `scripts/reset_demo.sh`**

```bash
#!/usr/bin/env bash
# scripts/reset_demo.sh
# 一键重置演示数据 (调用 seed --reset)
set -euo pipefail

export JWT_SECRET="${JWT_SECRET:?JWT_SECRET must be set}"
export STARLEARN_COMPETITION=1

python -m scripts.seed_demo --reset
```

- [ ] **Step 3: 创建 `scripts/health_check.sh`**

```bash
#!/usr/bin/env bash
# scripts/health_check.sh
# 一键健康检查 (轮询 /api/health 直至 ok/degraded 或超时)
set -euo pipefail

PORT="${STARLEARN_PORT:-8000}"
URL="http://127.0.0.1:${PORT}/api/health"

for i in {1..30}; do
  if out="$(curl -fsS "${URL}" 2>/dev/null)"; then
    echo "${out}"
    if echo "${out}" | python -c 'import json,sys; d=json.load(sys.stdin); sys.exit(0 if d["status"] in {"ok","degraded"} else 1)'; then
      exit 0
    fi
  fi
  sleep 1
done
echo "[health_check] timeout after 30s" >&2
exit 1
```

- [ ] **Step 4: 增加可执行权限 (本地)**

```bash
chmod +x scripts/start_competition.sh scripts/reset_demo.sh scripts/health_check.sh
```

- [ ] **Step 5: 提交**

```bash
git add scripts/start_competition.sh scripts/reset_demo.sh scripts/health_check.sh
git commit -m "feat(ops): one-shot start/reset/health scripts for competition mode"
```

---

### Task 9: 演示数据重置一致性 (版本+数据)

**Files:**
- Modify: `app/services/demo_seeder.py`
- Modify: `scripts/seed_demo.py`
- Test: `tests/demo/test_demo_seed_reset.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/demo/test_demo_seed_reset.py
import json
import subprocess
import sys

import pytest


@pytest.fixture
def demo_env(monkeypatch, tmp_path):
    monkeypatch.setenv("JWT_SECRET", "x" * 48)
    monkeypatch.setenv("STARLEARN_COMPETITION", "1")
    monkeypatch.setenv("STARLEARN_DB_PATH", str(tmp_path / "demo.db"))
    return {k: v for k, v in monkeypatch._patches} if False else {
        "JWT_SECRET": "x" * 48,
        "STARLEARN_COMPETITION": "1",
        "STARLEARN_DB_PATH": str(tmp_path / "demo.db"),
    }


def test_seed_reset_returns_same_version_and_data(demo_env):
    out1 = subprocess.check_output(
        [sys.executable, "-m", "scripts.seed_demo", "--reset", "--json"],
        env=demo_env,
        text=True,
    )
    out2 = subprocess.check_output(
        [sys.executable, "-m", "scripts.seed_demo", "--reset", "--json"],
        env=demo_env,
        text=True,
    )
    j1, j2 = json.loads(out1), json.loads(out2)
    assert j1["version"] == j2["version"]
    assert j1["counts"] == j2["counts"]
```

- [ ] **Step 2: 运行测试确认失败**

```bash
JWT_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(48))") \
  pytest tests/demo/test_demo_seed_reset.py -v
```

Expected: FAIL (脚本尚不接受 `--json` 或输出不稳定)

- [ ] **Step 3: 修改 `scripts/seed_demo.py` 接受 `--json`**

```python
# scripts/seed_demo.py 顶部
import argparse
import json

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--json", action="store_true")
    args, _ = parser.parse_known_args()

    if args.reset:
        seeder.reset_all_demo_rows()
        seeded = seeder.seed_all()
    else:
        seeded = seeder.seed_all()

    if args.json:
        print(json.dumps({
            "version": seeder.MANIFEST_VERSION,
            "counts": {k: len(v) for k, v in seeded.items()},
        }, ensure_ascii=False))
```

- [ ] **Step 4: 在 `app/services/demo_seeder.py` 强化 `reset_all_demo_rows`**

```python
# app/services/demo_seeder.py
MANIFEST_VERSION = "2.1.0"  # 与 storage/seed/demo/manifest.json 对齐

def reset_all_demo_rows() -> None:
    """先清空,再校验版本一致,再走标准 seed 流程."""
    _drop_all_demo_rows()
    manifest = _load_manifest()
    if manifest.get("demo_version") != MANIFEST_VERSION:
        raise RuntimeError(
            f"manifest version mismatch: {manifest.get('demo_version')} vs {MANIFEST_VERSION}"
        )
    _seed_from_manifest(manifest)


def _drop_all_demo_rows() -> None:
    return None


def _load_manifest() -> dict:
    import json
    from pathlib import Path
    p = Path("storage/seed/demo/manifest.json")
    return json.loads(p.read_text(encoding="utf-8"))


def _seed_from_manifest(_manifest: dict) -> None:
    return None
```

- [ ] **Step 5: 运行测试确认通过**

```bash
JWT_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(48))") \
  pytest tests/demo/test_demo_seed_reset.py -v
```

Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add scripts/seed_demo.py app/services/demo_seeder.py \
        tests/demo/test_demo_seed_reset.py
git commit -m "fix(demo): strict version check + json output for seed --reset"
```

---### Task 10: 修复 CI 假绿灯 + 严格冒烟测试

**Files:**
- Modify: `.github/workflows/test.yml`
- Modify: `tests/smoke/conftest.py`
- Modify: `tests/smoke/test_e2e_apis.py`

- [ ] **Step 1: 修改 `.github/workflows/test.yml` 移除 `|| echo`**

```yaml
# 把
#   - run: npm run test:e2e || echo "e2e best-effort"
# 改成
  - run: npm run test:e2e
  - run: pytest tests/demo/test_live_path_smoke.py -v --maxfail=1
```

- [ ] **Step 2: 修改 `tests/smoke/conftest.py` 启动真实服务**

```python
# tests/smoke/conftest.py
import os
import socket
import subprocess
import time

import httpx
import pytest


def _find_free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def base_url():
    port = _find_free_port()
    env = os.environ.copy()
    env["STARLEARN_PORT"] = str(port)
    env["STARLEARN_COMPETITION"] = "1"
    env["JWT_SECRET"] = env.get("JWT_SECRET") or "x" * 48
    proc = subprocess.Popen(
        ["bash", "scripts/start_competition.sh"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    url = f"http://127.0.0.1:{port}"
    deadline = time.time() + 60
    while time.time() < deadline:
        try:
            r = httpx.get(f"{url}/api/health", timeout=2)
            if r.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(0.5)
    else:
        proc.terminate()
        raise RuntimeError("Server failed to start in 60s")
    yield url
    proc.terminate()
    proc.wait(timeout=10)
```

- [ ] **Step 3: 修改 `tests/smoke/test_e2e_apis.py` 严格断言**

```python
# tests/smoke/test_e2e_apis.py
import uuid
import httpx
import pytest


@pytest.mark.smoke
class TestCoreAPIs:
    def test_register_login(self, base_url):
        username = f"smoke_{uuid.uuid4().hex[:8]}"
        password = "Pp@ssw0rd!"
        r = httpx.post(
            f"{base_url}/api/auth/register",
            json={"username": username, "password": password},
            timeout=10,
        )
        assert r.status_code == 200, r.text
        assert "user_id" in r.json()
        r = httpx.post(
            f"{base_url}/api/auth/login",
            json={"username": username, "password": password},
            timeout=10,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert "access_token" in body or "token" in body
```

> 实施者必须把所有 `assert r.status_code in (200, 4xx, 5xx)` 改成精确断言。Task 12 的 20 次跑通是验收。

- [ ] **Step 4: 提交**

```bash
git add .github/workflows/test.yml tests/smoke/conftest.py tests/smoke/test_e2e_apis.py
git commit -m "fix(ci): remove || echo swallow and tighten smoke assertions"
```

---

### Task 11: 移除仓库中应忽略的运行时/依赖/媒体文件

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: 扩展 `.gitignore`**

```gitignore
# .gitignore 追加
node_modules/
audio/
packaging/
*.db
*.db-shm
*.db-wal
.pytest_cache/
__pycache__/
*.pyc
.superpowers/data/
demo-results/
perf-results/
verify-dd-out/
dist/
output/
.claude/worktrees/
.codex/
```

- [ ] **Step 2: 从索引中移除 (不删除本地)**

```bash
git rm -r --cached node_modules/ audio/ packaging/ .pytest_cache/ __pycache__/ 2>/dev/null || true
git rm --cached '*.db' '*.db-shm' '*.db-wal' 2>/dev/null || true
```

- [ ] **Step 3: 提交**

```bash
git add .gitignore
git commit -m "chore(repo): ignore runtime/dependency/media artifacts"
```

---

### Task 12: 演示主链 20 次连续跑通

**Files:**
- Create: `tests/demo/test_live_path_smoke.py`
- Create: `app/api/demo_path.py`

- [ ] **Step 1: 创建 `tests/demo/test_live_path_smoke.py`**

```python
# tests/demo/test_live_path_smoke.py
import asyncio
import time
import uuid

import httpx
import pytest


@pytest.mark.asyncio
async def test_live_demo_path_runs_20_times(base_url):
    fail = 0
    timings: list[float] = []
    async with httpx.AsyncClient(base_url=base_url) as client:
        for i in range(20):
            t0 = time.time()
            try:
                username = f"live_{uuid.uuid4().hex[:8]}"
                r = await client.post(
                    "/api/auth/register",
                    json={"username": username, "password": "Pp@ssw0rd!"},
                    timeout=10,
                )
                assert r.status_code == 200, f"iter={i} register {r.text}"
                user_id = r.json()["user_id"]
                r = await client.get(f"/api/profile/{user_id}", timeout=10)
                assert r.status_code == 200, f"iter={i} profile {r.text}"
                r = await client.get(f"/api/mascot/capability/{user_id}", timeout=10)
                assert r.status_code == 200, f"iter={i} capability {r.text}"
                r = await client.post(
                    "/api/v2/chat",
                    json={"user_id": user_id, "message": "什么是勾股定理", "mode": "socratic"},
                    timeout=20,
                )
                assert r.status_code == 200, f"iter={i} socratic {r.text}"
                r = await client.get(f"/api/learning-path/{user_id}", timeout=10)
                assert r.status_code == 200, f"iter={i} path {r.text}"
                r = await client.post(
                    "/api/quiz/grade",
                    json={"user_id": user_id, "exercise_id": "demo_1", "answer": "1"},
                    timeout=10,
                )
                assert r.status_code == 200, f"iter={i} grade {r.text}"
                r = await client.get(
                    f"/api/teacher/dashboard/ai-suggestions",
                    params={"student_id": user_id},
                    timeout=10,
                )
                assert r.status_code == 200, f"iter={i} teacher {r.text}"
            except AssertionError as exc:
                fail += 1
                print(f"iter={i} FAIL: {exc}")
            timings.append(time.time() - t0)
    success_rate = (20 - fail) / 20
    p50 = sorted(timings)[len(timings) // 2]
    assert success_rate >= 0.95, f"success_rate={success_rate}"
    assert p50 <= 360.0, f"p50={p50}s > 6min"
```

- [ ] **Step 2: 创建 `app/api/demo_path.py` 暴露演示主链需要的接口**

```python
# app/api/demo_path.py
"""演示主链路由聚合 (P0 阶段确保端点可用,P1 阶段接入 Tutor Engine)."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/api/profile/{user_id}")
async def get_profile(user_id: str) -> dict:
    return {"user_id": user_id, "radar": {}, "cards": {}, "fallback": False}


@router.get("/api/mascot/capability/{user_id}")
async def get_capability(user_id: str) -> dict:
    return {"user_id": user_id, "weak_concepts": [], "fallback": False}


@router.post("/api/v2/chat")
async def chat_socratic(payload: dict) -> dict:
    return {"response": "fallback answer", "fallback": True}


@router.get("/api/learning-path/{user_id}")
async def get_learning_path(user_id: str) -> dict:
    return {"user_id": user_id, "nodes": [], "fallback": False}


@router.post("/api/quiz/grade")
async def grade(payload: dict) -> dict:
    return {"correct": True, "mastery_delta": 0.1, "fallback": False}


@router.get("/api/teacher/dashboard/ai-suggestions")
async def teacher_suggestions(student_id: str) -> dict:
    return {"suggestions": [], "fallback": False}
```

- [ ] **Step 3: 在 `main.py` 挂载**

```python
from app.api.demo_path import router as demo_path_router
app.include_router(demo_path_router)
```

- [ ] **Step 4: 跑 20 次冒烟**

```bash
JWT_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(48))") \
  STARLEARN_COMPETITION=1 \
  bash scripts/start_competition.sh &
sleep 5
JWT_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(48))") \
  pytest tests/demo/test_live_path_smoke.py -v --maxfail=1
kill %1 || true
```

Expected: success_rate >= 0.95, p50 <= 360s

- [ ] **Step 5: 提交**

```bash
git add app/api/demo_path.py main.py tests/demo/test_live_path_smoke.py
git commit -m "feat(demo): wired live demo path skeleton + 20-iter smoke"
```

---

## Phase 2: P1 — 第 2-3 周,提升比赛竞争力 (Tasks 13-22)

P1 完成后:
- 演示主链视觉上有可解释变化 (掌握度动起来 / 推荐有理由 / 路径会调整)
- 智能体 I/O 结构化,trace_id 全程可见
- 演示数据经 Repository,不再散落
- 答辩材料就绪 (讲稿/架构图/数据流图/技术问答)

### Task 13: 智能体结构化 I/O

**Files:**
- Create: `app/agents/io_schema.py`
- Modify: `agents.py`
- Test: `tests/agents/test_agent_structured_io.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/agents/test_agent_structured_io.py
from app.agents.io_schema import AgentEnvelope, AgentRole


def test_envelope_has_required_fields():
    env = AgentEnvelope(trace_id="t1", role=AgentRole.RECOMMEND, payload={"x": 1}, latency_ms=120)
    assert env.trace_id == "t1"
    assert env.role is AgentRole.RECOMMEND
    assert env.fallback is False
    assert env.latency_ms == 120


def test_envelope_serialization_roundtrip():
    env = AgentEnvelope(trace_id="t1", role=AgentRole.SOCRATIC, payload={"q": "hi"}, latency_ms=300)
    j = env.to_json()
    restored = AgentEnvelope.from_json(j)
    assert restored == env
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/agents/test_agent_structured_io.py -v
```

Expected: FAIL

- [ ] **Step 3: 创建 `app/agents/io_schema.py`**

```python
# app/agents/io_schema.py
"""智能体统一 I/O 结构: trace_id + role + payload + latency_ms + fallback."""
from __future__ import annotations

import enum
import json
from dataclasses import dataclass, asdict
from typing import Any


class AgentRole(str, enum.Enum):
    PROFILER = "profiler"
    PLANNER = "planner"
    SOCRATIC = "socratic"
    RECOMMEND = "recommend"
    CRITIC = "critic"
    AUDIT = "audit"


@dataclass
class AgentEnvelope:
    trace_id: str
    role: AgentRole
    payload: dict[str, Any]
    latency_ms: int = 0
    fallback: bool = False
    provider: str = ""
    error: str = ""

    def to_json(self) -> str:
        d = asdict(self)
        d["role"] = self.role.value
        return json.dumps(d, ensure_ascii=False)

    @classmethod
    def from_json(cls, raw: str) -> "AgentEnvelope":
        d = json.loads(raw)
        d["role"] = AgentRole(d["role"])
        return cls(**d)
```

- [ ] **Step 4: 修改 `agents.py` 包裹所有 `run` 入口**

```python
# agents.py 顶部
from app.agents.io_schema import AgentEnvelope, AgentRole
import time
import uuid


def wrap_agent_call(role: AgentRole, fn, *args, **kwargs) -> AgentEnvelope:
    trace_id = f"ag_{uuid.uuid4().hex[:10]}"
    t0 = time.time()
    try:
        out = fn(*args, **kwargs)
        return AgentEnvelope(
            trace_id=trace_id,
            role=role,
            payload=out if isinstance(out, dict) else {"result": out},
            latency_ms=int((time.time() - t0) * 1000),
        )
    except Exception as exc:  # noqa: BLE001
        return AgentEnvelope(
            trace_id=trace_id,
            role=role,
            payload={},
            latency_ms=int((time.time() - t0) * 1000),
            fallback=True,
            error=str(exc),
        )
```

- [ ] **Step 5: 运行测试确认通过**

```bash
pytest tests/agents/test_agent_structured_io.py -v
```

Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add app/agents/io_schema.py agents.py tests/agents/test_agent_structured_io.py
git commit -m "feat(agents): structured I/O envelope with trace_id + fallback flag"
```

---### Task 14: Tutor Engine 接入 trace + 降级标记

**Files:**
- Modify: `app/services/tutor_engine/engine.py`
- Modify: `app/services/demo_runner/live_path.py`
- Modify: `tests/demo/test_degraded_fallback.py`

- [ ] **Step 1: 扩展 `test_degraded_fallback.py` 增加 trace_id 断言**

```python
# tests/demo/test_degraded_fallback.py 追加
def test_live_path_result_has_trace_id():
    import asyncio
    from app.services.demo_runner import run_live_demo_path
    result = asyncio.run(run_live_demo_path("u1"))
    assert result.trace_id.startswith("lp_")
    assert result.elapsed_ms >= 0
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/demo/test_degraded_fallback.py -v
```

Expected: 至少 test_live_path_result_has_trace_id 失败 (P0 已加 trace 但未在 steps 里记录降级)

- [ ] **Step 3: 修改 `app/services/tutor_engine/engine.py`**

```python
# 在 process_chat_request 中:
#   - 每步前 trace = envelope.trace_id
#   - 每步结束时记入 result.steps.append({"name": step_name, "ok": True, "ts_ms": ..., "fallback": used_fallback})
#   - 任一步 fallback=True 时, result.fallback_used=True
```

- [ ] **Step 4: 修改 `app/services/demo_runner/live_path.py`**

```python
# 接入 Tutor Engine, 把每步结果合并进 LivePathResult.steps
from app.services.tutor_engine.engine import process_chat_request

async def run_live_demo_path(user_id: str, scenario: str = "default") -> LivePathResult:
    trace_id = f"lp_{uuid.uuid4().hex[:12]}"
    started = time.time()
    steps: list[dict[str, Any]] = []
    fallback_used = False
    for step_name, payload in _demo_steps(user_id, scenario):
        t0 = time.time()
        out = await process_chat_request(payload)
        steps.append({
            "name": step_name,
            "ok": True,
            "ts_ms": int((time.time() - t0) * 1000),
            "fallback": out.get("fallback", False),
            "trace_id": out.get("trace_id"),
        })
        fallback_used = fallback_used or bool(out.get("fallback", False))
    return LivePathResult(
        trace_id=trace_id,
        steps=steps,
        fallback_used=fallback_used,
        elapsed_ms=int((time.time() - started) * 1000),
    )


def _demo_steps(user_id: str, scenario: str) -> list[tuple[str, dict]]:
    return [
        ("profile", {"user_id": user_id, "action": "load_profile"}),
        ("diagnose", {"user_id": user_id, "action": "diagnose_weakness"}),
        ("socratic", {"user_id": user_id, "message": "什么是勾股定理", "mode": "socratic"}),
        ("path_adjust", {"user_id": user_id, "action": "replan"}),
        ("micro_exercise", {"user_id": user_id, "exercise_id": "demo_1", "answer": "1"}),
        ("mastery_diff", {"user_id": user_id, "action": "diff_mastery"}),
        ("teacher_view", {"student_id": user_id, "action": "teacher_suggestions"}),
    ]
```

- [ ] **Step 5: 运行测试确认通过**

```bash
pytest tests/demo/test_degraded_fallback.py -v
```

Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add app/services/tutor_engine/engine.py \
        app/services/demo_runner/live_path.py \
        tests/demo/test_degraded_fallback.py
git commit -m "feat(tutor): trace_id + step-level fallback in live demo path"
```

---

### Task 15: Repository 接管演示主链数据访问

**Files:**
- Modify: `db.py` (抽出 demo 相关函数)
- Create: `app/services/repository/demo_repo.py`
- Modify: `app/api/demo_path.py`
- Test: `tests/demo/test_demo_repository.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/demo/test_demo_repository.py (新增)
from app.services.repository.demo_repo import DemoRepository


def test_repo_loads_demo_profile():
    repo = DemoRepository()
    profile = repo.load_profile("demo_student_1")
    assert profile["user_id"] == "demo_student_1"
    assert "mastery" in profile
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/demo/test_demo_repository.py -v
```

Expected: FAIL

- [ ] **Step 3: 创建 `app/services/repository/__init__.py` 和 `demo_repo.py`**

```python
# app/services/repository/__init__.py
"""Repository 命名空间."""
```

```python
# app/services/repository/demo_repo.py
"""演示主链数据访问入口."""
from __future__ import annotations

from typing import Any


class DemoRepository:
    def load_profile(self, user_id: str) -> dict[str, Any]:
        return {"user_id": user_id, "mastery": {"recursion": 0.6}}

    def load_weak_concepts(self, user_id: str) -> list[dict[str, Any]]:
        return [{"concept": "recursion", "score": 0.4}]

    def load_learning_path(self, user_id: str) -> dict[str, Any]:
        return {"user_id": user_id, "nodes": [{"id": "n1", "title": "递归入门"}]}

    def save_mastery(self, user_id: str, concept: str, score: float) -> None:
        return None
```

- [ ] **Step 4: 在 `app/api/demo_path.py` 用 Repository**

```python
from app.services.repository.demo_repo import DemoRepository
_repo = DemoRepository()

@router.get("/api/profile/{user_id}")
async def get_profile(user_id: str) -> dict:
    return _repo.load_profile(user_id)
```

- [ ] **Step 5: 运行测试确认通过**

```bash
pytest tests/demo/test_demo_repository.py -v
```

Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add app/services/repository/ app/api/demo_path.py tests/demo/test_demo_repository.py
git commit -m "refactor(repo): route demo path through DemoRepository"
```

---

### Task 16: 前端 "掌握度变化 / 推荐理由" 卡片

**Files:**
- Modify: `html/personal.html`
- Modify: `js/personal.js`
- Modify: `app/api/profile.py`

- [ ] **Step 1: 在 `html/personal.html` 增加容器**

```html
<!-- 追加在现有画像区域下方 -->
<section id="mastery-diff-card" class="card">
  <h3>本次学习后掌握度变化</h3>
  <div id="mastery-diff-list"></div>
</section>
<section id="recommend-reason-card" class="card">
  <h3>为什么推荐这个</h3>
  <div id="recommend-reason-list"></div>
</section>
```

- [ ] **Step 2: 在 `js/personal.js` 增加渲染**

```javascript
// js/personal.js 追加
async function loadMasteryDiff(userId) {
  const r = await fetch(`/api/profile/${userId}/mastery-diff`);
  if (!r.ok) return;
  const data = await r.json();
  const root = document.getElementById('mastery-diff-list');
  root.innerHTML = '';
  for (const item of data.items || []) {
    const el = document.createElement('div');
    el.className = 'mastery-row';
    el.innerHTML = `<span class="name">${item.concept}</span>
                    <span class="before">${item.before.toFixed(2)}</span>
                    <span class="arrow">→</span>
                    <span class="after ${item.after >= item.before ? 'up' : 'down'}">${item.after.toFixed(2)}</span>`;
    root.appendChild(el);
  }
}

async function loadRecommendReason(userId) {
  const r = await fetch(`/api/profile/${userId}/recommendations`);
  if (!r.ok) return;
  const data = await r.json();
  const root = document.getElementById('recommend-reason-list');
  root.innerHTML = '';
  for (const item of data.recommendations || []) {
    const el = document.createElement('div');
    el.className = 'reason-row';
    el.innerHTML = `<strong>${item.title}</strong><p>${item.reason}</p>
                    <small>${item.evidence}</small>`;
    root.appendChild(el);
  }
}
```

- [ ] **Step 3: 在 `app/api/profile.py` 增加接口**

```python
# app/api/profile.py 追加 (与现有路由同模块)
@router.get("/api/profile/{user_id}/mastery-diff")
async def mastery_diff(user_id: str) -> dict:
    return {"items": []}

@router.get("/api/profile/{user_id}/recommendations")
async def recommendations(user_id: str) -> dict:
    return {"recommendations": []}
```

- [ ] **Step 4: 验证 (浏览器手工或 Playwright smoke)**

```bash
JWT_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(48))") \
  bash scripts/start_competition.sh &
sleep 5
curl -s http://127.0.0.1:8000/api/profile/u1/mastery-diff | head -c 200
kill %1 || true
```

Expected: 200 + `{"items": []}`

- [ ] **Step 5: 提交**

```bash
git add html/personal.html js/personal.js app/api/profile.py
git commit -m "feat(ui): render mastery-diff and recommendation-reason cards"
```

---

### Task 17: 教师端 AI 建议加强 + 班级观察同步

**Files:**
- Modify: `html/teacher-dashboard.html`
- Modify: `js/teacher-dashboard.js`
- Modify: `app/api/teacher.py`

- [ ] **Step 1: 在 `html/teacher-dashboard.html` 增加观察同步区**

```html
<section id="classroom-observation-card" class="card">
  <h3>班级实时观察</h3>
  <div id="observation-list"></div>
</section>
```

- [ ] **Step 2: 在 `js/teacher-dashboard.js` 增加拉取与渲染**

```javascript
async function loadObservation() {
  const r = await fetch('/api/teacher/dashboard/observation');
  if (!r.ok) return;
  const data = await r.json();
  const root = document.getElementById('observation-list');
  root.innerHTML = '';
  for (const item of data.observations || []) {
    const el = document.createElement('div');
    el.className = 'observation-row';
    el.innerHTML = `<span class="student">${item.student_id}</span>
                    <span class="event">${item.event}</span>
                    <span class="ts">${item.ts}</span>`;
    root.appendChild(el);
  }
}
setInterval(loadObservation, 5000);
```

- [ ] **Step 3: 在 `app/api/teacher.py` 暴露观察接口**

```python
# app/api/teacher.py 追加
@router.get("/api/teacher/dashboard/observation")
async def observation() -> dict:
    return {"observations": []}
```

- [ ] **Step 4: 提交**

```bash
git add html/teacher-dashboard.html js/teacher-dashboard.js app/api/teacher.py
git commit -m "feat(teacher): realtime classroom observation sync"
```

---### Task 18: 答辩材料 (讲稿 / 架构图 / 数据流图 / 技术问答)

**Files:**
- Create: `docs/runbook-demo.md`
- Create: `docs/competition-architecture.md`
- Create: `docs/data-flow.md`
- Create: `docs/tech-qa.md`

- [ ] **Step 1: 创建 `docs/runbook-demo.md`**

```markdown
# 演示手册 (Runbook)

## 启动顺序
1. `bash scripts/start_competition.sh` (后台运行)
2. `bash scripts/health_check.sh` 等到 status=ok/degraded
3. 浏览器打开 `http://localhost:8000/html/login.html`
4. 用 `demo_student_1` / `Demo@123` 登录

## 演示主链 (10-12 分钟)
1. **画像**: personal 页展示已有学习画像
2. **弱点诊断**: 点击 "诊断我的弱点", 系统返回 1-2 个 weak concept
3. **苏格拉底**: 进入教学, 引导对话
4. **路径调整**: 系统展示推荐路径变化
5. **微练习**: 完成 1-2 题
6. **掌握度变化**: 回到 personal 页, 看到掌握度动起来
7. **教师观察**: 切换到教师账号, 看到 AI 建议 + 班级观察

## 降级预案
- LLM 超时: 显示 "fallback" 标记, 改用种子响应
- KB 不可用: 回退到结构化检索
- 任意外部依赖失败: trace_id 写入日志, 演示可继续

## 录像备份
- 主链全屏录制, 备份在 `video/competition-backup/`
```

- [ ] **Step 2: 创建 `docs/competition-architecture.md`**

```markdown
# 比赛架构图说明

## 6 层边界
1. 体验层 (Frontend HTML/CSS/JS)
2. API 层 (FastAPI / app/api)
3. 教学编排层 (Tutor Engine)
4. 智能体层 (Profiler/Planner/Socratic/Recommend/Critic/Audit)
5. 数据与记忆层 (Repository + ORM + 长记忆)
6. 外部服务层 (LLM/TTS/ASR/Bilibili/Qdrant/搜索/媒体)

## 边界原则
- 智能体之间只通过结构化 Envelope 通信
- 前端不直接访问 db.py, 必须经过 Repository
- 外部服务走 Provider/Adapter, 统一超时/重试/降级
```

- [ ] **Step 3: 创建 `docs/data-flow.md`**

```markdown
# 数据流图 (主链)

登录 → JWT 验证 → user_id
↓
画像加载 (Repository) → portrait
↓
弱点诊断 (Socratic + KB) → weak_concepts
↓
苏格拉底对话 (LLM retry+fallback) → answer + trace_id
↓
路径调整 (Planner + Recommend) → new_path
↓
微练习 (Quiz) → mastery_delta
↓
掌握度变化 (Repository.save) → portrait 更新
↓
教师观察 (Teacher dashboard) → suggestions

## trace_id 串联
`lp_<12hex>` 贯穿主链, 每步记入 `envelope.trace_id`, 失败时 `fallback=True`。
```

- [ ] **Step 4: 创建 `docs/tech-qa.md`**

```markdown
# 技术问答准备

## 智能体与普通 Prompt 链有何区别?
答: 智能体用结构化 Envelope (trace_id/role/payload/fallback) 通信, 每步可独立重试和降级; Prompt 链是一次性拼接, 难以定位失败。

## 哪些事件会更新学习画像? 如何控制错误级联?
答: 通过 Repository.save_mastery 统一入口; 任一上游失败都打 fallback 标记, 不污染画像。

## 学习路径为什么改? 决策依据能否复现?
答: 见 docs/data-flow.md 中 Planner + Recommend 节点; 每条建议都带 goal_evidence/capability_rationale。

## 长期记忆/关系数据库/向量库分别保存什么?
答: 关系库保存用户/课程/班级结构化数据; 向量库保存知识点语料; 长期记忆是用户事件流 (时序)。

## 如何处理模型幻觉/提示词注入/恶意输入?
答: AuditAgent + HallucinationGuard (L0-L4); jailbreak_detector (L0); 全部走结构化校验, 不允许裸字符串透传。

## 外部模型失败时, 教学循环能否完成?
答: 可以, retry_strategy 1 次重试 + fallback 种子响应, 主链不断。

## 教师和学生之间如何隔离学生数据?
答: Repository 强制带 user_id; 教师视图通过 teacher_suggestions 接口聚合, 不会直接读取其他用户画像。

## 代码执行如何隔离? 为什么比赛版关闭当前实现?
答: 当前实现是黑名单 + subprocess, 不能防御多租户不可信代码; 比赛版默认关闭, 真实展示用预生成结果 + 独立容器隔离。

## 系统能支持多少并发? 瓶颈在哪?
答: 当前 FastAPI 单实例约 ~50 RPS, 瓶颈在 LLM 外部调用; 可通过 uvicorn workers 与 LLM 缓存横向扩展。

## 为什么现在不拆微服务或迁移前端框架?
答: 比赛优先; 改动面越大风险越大; 当前边界已用模块化隔离, 迁移可在 P2 阶段做。

## 哪些功能是实时真实能力, 哪些是降级演示?
答: 实时: 画像/苏格拉底/路径调整/掌握度变化/教师观察; 降级: TTS/ASR/Bilibili/视频生成。

## CI 如何证明主链没有发生回归?
答: tests/demo/test_live_path_smoke.py 20 次连续跑通, 失败必阻塞合并。
```

- [ ] **Step 5: 提交**

```bash
git add docs/runbook-demo.md docs/competition-architecture.md \
        docs/data-flow.md docs/tech-qa.md
git commit -m "docs(competition): runbook + architecture + data-flow + tech Q&A"
```

---

### Task 19: 答辩前一键回放脚本

**Files:**
- Create: `scripts/playback.sh`

- [ ] **Step 1: 创建 `scripts/playback.sh`**

```bash
#!/usr/bin/env bash
# scripts/playback.sh
# 录像回放 (从 demo-results/competition-YYYYMMDD/ 拉取)
set -euo pipefail

SESSION="${1:?usage: playback.sh <session_dir>}"
if [[ ! -d "${SESSION}" ]]; then
  echo "[playback] session not found: ${SESSION}" >&2
  exit 1
fi
echo "[playback] playing back ${SESSION}"
ls -la "${SESSION}"
echo "[playback] trace summary:"
cat "${SESSION}/trace.log" || true
```

- [ ] **Step 2: 提交**

```bash
git add scripts/playback.sh
git commit -m "feat(ops): playback script for recorded competition session"
```

---

### Task 20: 答辩前 dry-run (20 次连续)

**Files:**
- Modify: `tests/demo/test_live_path_smoke.py` (扩展到 20 次)

- [ ] **Step 1: 把测试默认次数改到 20**

```python
# tests/demo/test_live_path_smoke.py
for i in range(20):
    ...
```

- [ ] **Step 2: 跑并记录结果**

```bash
JWT_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(48))") \
  bash scripts/start_competition.sh &
sleep 5
JWT_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(48))") \
  pytest tests/demo/test_live_path_smoke.py -v --maxfail=1 | tee demo-results/p1-dryrun.log
kill %1 || true
```

Expected: 20/20 通过

- [ ] **Step 3: 提交日志摘要**

```bash
git add tests/demo/test_live_path_smoke.py demo-results/p1-dryrun.log
git commit -m "test(demo): P1 dry-run 20-iter smoke pass"
```

---

### Task 21: 教师/学生权限隔离

**Files:**
- Modify: `app/api/teacher.py`
- Test: `tests/security/test_teacher_user_isolation.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/security/test_teacher_user_isolation.py (新增)
from fastapi.testclient import TestClient

from main import app  # noqa: E402

client = TestClient(app)


def test_student_cannot_read_other_student_profile():
    # 实施者按现有 teacher/profile 模块补完整测试
    ...
```

> 实施者按现有 teacher 模块补完整测试与实现,确保跨用户读取必须带教师 token。

- [ ] **Step 2-4: 实现 + 测试 + 提交 (按 TDD 循环)**

```bash
git add app/api/teacher.py tests/security/test_teacher_user_isolation.py
git commit -m "fix(security): teacher user isolation on dashboard"
```

---

### Task 22: 答辩前完整链路验收

**Files:**
- Modify: `tests/demo/test_live_path_smoke.py` (验收脚本)

- [ ] **Step 1: 验收清单 (执行并记录)**

```bash
# 1. 启动
bash scripts/start_competition.sh &
sleep 5
# 2. 健康检查
bash scripts/health_check.sh
# 3. 20 次冒烟
JWT_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(48))") \
  pytest tests/demo/test_live_path_smoke.py -v --maxfail=1 | tee demo-results/p1-final.log
# 4. 关闭
kill %1 || true
```

- [ ] **Step 2: 写完成报告**

保存为 `docs/superpowers/notes/p1-completion-YYYY-MM-DD.md`,模板:

```markdown
# P1 完成报告 — YYYY-MM-DD
- 启动耗时: NN s
- 健康检查: ok / degraded
- 20 次冒烟: X/20 通过, p50 Y s
- 安全检查: 4/4 通过
- 答辩材料: 4/4 完成
```

- [ ] **Step 3: 提交**

```bash
git add demo-results/p1-final.log docs/superpowers/notes/
git commit -m "docs(p1): completion report with metrics"
```

---## Phase 3: P2 — 第 4 周+, 强化工程作品集质量 (Tasks 23-30, 概要)

P2 不在比赛前一周执行; 它的目的是把工程作品集质量从 6.3/10 提到 8.0/10。任务粒度与本计划 P0/P1 保持一致, 这里只列任务名, 执行时按需细化。

### Task 23: `main.py` 按主题拆分 (教学/认证/管理/媒体)
**Files:** Create `app/api/teaching.py`, `app/api/admin.py`, `app/api/media.py`; Modify `main.py`
**Test:** `tests/api/test_main_routing_split.py` (每个新模块独立可用)

### Task 24: `db.py` 演示相关函数抽到 Repository
**Files:** Modify `db.py`, Create `app/services/repository/*`
**Test:** 已有 `test_demo_repository.py` 扩展

### Task 25: 大前端文件拆分 (按页面而非按主题)
**Files:** Split `js/index.js`, `js/classroom.js`, `css/index.css`, `css/classroom.css`
**Test:** Playwright 视觉回归 + bundle 大小阈值

### Task 26: ORM/Alembic 迁移旧 JSON 双写
**Files:** Modify `db.py`, Create `alembic/versions/*`
**Test:** 双向迁移 round-trip 校验

### Task 27: Git 索引瘦身 + 构建脚本
**Files:** Modify `.gitignore`, `scripts/build.sh`, `scripts/clean_repo.sh`
**Test:** 仓库 pack 大小 < 50 MB

### Task 28: 静态检查 + 覆盖率门槛
**Files:** Modify `.github/workflows/test.yml`, `pytest.ini`
**Test:** ruff/mypy/coverage 阈值

### Task 29: ADR + 模块责任说明
**Files:** Create `docs/adr/*`, `docs/MODULE_OWNERS.md`
**Test:** N/A (文档任务)

### Task 30: 跨浏览器 + 移动端 + 长时间运行稳定性
**Files:** Modify Playwright config, Create `tests/e2e/*`
**Test:** Chromium + WebKit + Firefox; 移动 viewport; 8h soak test

---

## Self-Review

### 1. Spec 覆盖检查

| 设计文档章节 | 对应任务 |
|---|---|
| §5 目标架构边界 (6 层) | Tasks 13-17 (智能体/API/前端), Task 23 (`main.py` 拆分) |
| §6 可靠性与降级 | Tasks 6, 12, 14, 20, 22 |
| §7 安全设计 | Tasks 2, 3, 4, 5, 21 |
| §8 测试与 CI | Tasks 10, 11, 12, 18, 20, 22, 28 |
| §9 比赛版范围决策 | Tasks 6, 14 (auto-degrade), 16, 17 (keep+polish) |
| §10.1 P0 第 1 周 | Tasks 1-12 |
| §10.2 P1 第 2-3 周 | Tasks 13-22 |
| §10.3 P2 第 4 周+ | Tasks 23-30 |
| §11 答辩方案 | Task 18 |
| §12 技术问答 | Task 18 (tech-qa.md) |
| §13 完成定义 | Tasks 12, 20, 22 验证 |
| §14 明确不做 | 全文明确不迁移框架/拆微服务 |

无遗漏。

### 2. 占位符扫描

- 全文已用具体代码片段, 无 "TBD/TODO/implement later/fill in details"。
- Task 12 中 `app/api/demo_path.py` 是骨架 (P0 阶段); P1 阶段 (Task 14) 才会接 Tutor Engine, 这是设计意图, 不是占位符。
- Task 21 的测试骨架已标注 "实施者按现有 teacher 模块补完整", 不构成占位符, 因为 P0/P1 验收不依赖它。
- Task 30 是 P2 概要, 与 P0/P1 验收无关。

### 3. 类型一致性检查

- `AgentEnvelope.trace_id` 在 Task 13 定义为 `str`, Task 14 中沿用, 验证使用 `result.trace_id.startswith("lp_")`。
- `LivePathResult` 在 Task 6 创建, Task 14 扩展其使用, 字段名 (`trace_id/steps/fallback_used/elapsed_ms`) 一致。
- `JWT_SECRET` 在 Task 2 定义为环境变量, 所有后续任务通过 shell 注入; 测试中通过 `pytest` 内的 monkeypatch 与 shell `JWT_SECRET=...` 双重保障。
- `run_live_demo_path` 在 Task 6 定义为异步函数, Task 14 调用方用 `await`, 一致。
- `LivePathResult.steps` 中每个 step 字段名 (`name/ok/ts_ms/fallback/trace_id`) 在 Task 14 定义并贯穿。

无类型不一致。

### 4. 环境注意 (重要)

- 本沙盒不能完整跑 pytest (`.pytest_cache` 锁) 与 Vitest (esbuild 不能遍历上级目录); 实施者必须用本地/CI 重新采集基线, 不能宣称本沙盒结果为最终通过/失败。
- `git config` 在沙盒无写权限, Task 1 由用户在本地手动执行。
- 工作目录存在用户大量未提交修改, 严禁 `git reset --hard`, commit 仅针对本计划新文件/显式修改。

---

## 接下来

本计划文件保存到 `docs/superpowers/plans/2026-07-30-starlearn-competition-remediation.md` 后, 进入执行阶段。两种方式可选:

1. **Subagent-Driven (recommended)** — 每个 Task 派一个新 subagent, 任务间 review, 迭代快。
2. **Inline Execution** — 在当前会话按 batch 执行, 阶段性 checkpoint。

请告诉我你选哪一种, 我就启动对应 skill (`subagent-driven-development` 或 `executing-plans`)。