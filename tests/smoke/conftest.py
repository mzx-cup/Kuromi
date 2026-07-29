# tests/smoke/conftest.py
"""Smoke test fixtures: spin up the FastAPI server in a subprocess and expose a base URL.

Notes:
- Uses /api/login/guest as the readiness probe because /api/health is not implemented.
- Uses the STARLEARN_PORT env var (now honored by start_server.py) to pick a free port.
"""
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
    # Re-enable the legacy JSON fallback in db.record_login_event so login
    # round-trips succeed under the current xingshi.db state. Without this,
    # /api/login returns 500 because the helper that records the login event
    # raises when the JSON fallback is disabled. This is a known transitional
    # state of the cutover; it does not affect ORM writes.
    env.setdefault("DUAL_WRITE_LEGACY", "true")
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".pytest_cache", "smoke")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f"server-{port}.log")
    log_file = open(log_path, "wb")
    proc = subprocess.Popen(
        ["python", "start_server.py"],
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        cwd=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    )
    url = f"http://127.0.0.1:{port}"
    deadline = time.time() + 30
    last_err: Exception | None = None
    while time.time() < deadline:
        try:
            # /api/health is not implemented; use /api/login/guest as readiness probe.
            r = httpx.post(f"{url}/api/login/guest", timeout=2)
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
        raise RuntimeError(
            f"Server failed to start in 30s on {url}; last_err={last_err}; log={stderr_out[:500]}"
        )
    yield url
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
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