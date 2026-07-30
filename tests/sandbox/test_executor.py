"""Tests for SandboxExecutor (M4.5)."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_executor_runs_simple_python():
    """简单的 print(2+2) 必须能跑通，stdout 含 '4'。"""
    from app.services.sandbox.executor import SandboxExecutor

    executor = SandboxExecutor(timeout_seconds=10)
    result = await executor.run_python("print(2 + 2)")
    assert result.success is True
    assert "4" in result.stdout


@pytest.mark.asyncio
async def test_executor_timeout_kills_long_running_code():
    """长跑代码必须被 timeout 杀掉。"""
    import asyncio

    from app.services.sandbox.executor import SandboxExecutor

    executor = SandboxExecutor(timeout_seconds=2)
    result = await executor.run_python("import time; time.sleep(10)")
    assert result.success is False
    assert "timeout" in result.error.lower()


@pytest.mark.asyncio
async def test_executor_blocks_dangerous_imports():
    """危险 import (os / subprocess / sys) 必须被拦截。"""
    from app.services.sandbox.executor import SandboxExecutor

    executor = SandboxExecutor(timeout_seconds=5)
    result = await executor.run_python("import os; os.system('echo pwned')")
    assert result.success is False
    assert "blocked" in result.error.lower() or "not allowed" in result.error.lower()


@pytest.mark.asyncio
async def test_executor_blocks_subprocess_import():
    """subprocess 也必须在黑名单里。"""
    from app.services.sandbox.executor import SandboxExecutor

    executor = SandboxExecutor(timeout_seconds=5)
    result = await executor.run_python("from subprocess import run; run(['echo', 'x'])")
    assert result.success is False


@pytest.mark.asyncio
async def test_executor_captures_python_error():
    """Python 运行时错误必须被捕获到 stderr。"""
    from app.services.sandbox.executor import SandboxExecutor

    executor = SandboxExecutor(timeout_seconds=5)
    result = await executor.run_python("print(undefined_var)")
    assert result.success is False
    assert "NameError" in result.stderr or "NameError" in result.error