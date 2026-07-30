"""Sandbox 服务命名空间（M4.5）。

当前导出：
  - SandboxExecutor  : subprocess + timeout Python 沙箱
  - ExecutionResult  : 执行结果 dataclass
"""
from __future__ import annotations

from app.services.sandbox.executor import ExecutionResult, SandboxExecutor

__all__ = ["SandboxExecutor", "ExecutionResult"]