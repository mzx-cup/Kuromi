# tests/smoke/conftest.py
"""Smoke test fixtures: spin up the FastAPI server in a subprocess and expose a base URL.

Notes:
- P0 Task 10: 改用 /api/health 作为 readiness probe (P0 Task 7 实现).
  /api/health 不依赖 DB, 启动判定更稳定, 也不会因双写状态影响 smoke 测试.
- Uses the STARLEARN_PORT env var (now honored by scripts/start_server.py) to pick a free port.
"""
import os
import socket
import subprocess
import time

import httpx
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _find_free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def base_url():
    port = _find_free_port()
    env = os.environ.copy()
    env["STARLEARN_PORT"] = str(port)
    # 保留 DUAL_WRITE_LEGACY 设置, 部分旧路由 (/api/login 等) 仍依赖.
    env.setdefault("DUAL_WRITE_LEGACY", "true")
    log_dir = os.path.join(PROJECT_ROOT, ".pytest_cache", "smoke")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f"server-{port}.log")
    log_file = open(log_path, "wb")
    proc: subprocess.Popen | None = None
    try:
        proc = subprocess.Popen(
            ["python", "scripts/start_server.py"],
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            cwd=PROJECT_ROOT,
        )
    except Exception:
        log_file.close()
        raise
    url = f"http://127.0.0.1:{port}"
    deadline = time.time() + 30
    last_err: Exception | None = None
    while time.time() < deadline:
        try:
            # P0 Task 10: 用 /api/health 替代 /api/login/guest 作为 readiness 探针.
            # /api/health 由 P0 Task 7 新增, 不依赖 DB / 业务路由.
            r = httpx.get(f"{url}/api/health", timeout=2)
            if r.status_code == 200:
                break
            last_err = RuntimeError(f"status={r.status_code}")
        except Exception as e:
            last_err = e
        time.sleep(0.5)
    else:
        proc.terminate()
        stderr_out = ""
        try:
            log_file.flush()
            with open(log_path, "rb") as f:
                stderr_out = f.read(2000).decode("utf-8", errors="replace")
        except Exception:
            pass
        # Chain the underlying error when available, otherwise suppress context.
        msg = (
            f"Server failed to start in 30s on {url}; "
            f"last_err={last_err}; log={stderr_out[:500]}"
        )
        if last_err is not None:
            raise RuntimeError(msg) from last_err
        raise RuntimeError(msg) from None
    yield url
    try:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
    finally:
        log_file.close()


@pytest.fixture
def guest_user(base_url):
    # /api/login/guest sometimes takes a few seconds because it dual-writes
    # to the ORM. Use a generous timeout to avoid ReadTimeout flakes.
    r = httpx.post(f"{base_url}/api/login/guest", timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    # The API returns camelCase keys ("userId"); accept both for forward-compat.
    return body.get("userId") or body["user_id"]