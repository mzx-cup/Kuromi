"""Sandbox: subprocess + timeout 执行 Python 代码（M4.5）

不引入 Docker 依赖；通过黑名单 + subprocess timeout 提供最低安全保障。

适用场景：
  - 学生提交代码 → 沙箱执行 → 验证输出
  - AI 生成代码片段 → 沙箱验证正确性
  - LLM 调用前的代码可执行性校验

不适用场景（需要 Docker / gVisor / Firecracker）：
  - 多租户不受信任的代码
  - 大量 CPU/内存密集任务
"""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass

logger = logging.getLogger("starlearn.sandbox")

# 高危模块黑名单
BLOCKED_MODULES: set[str] = {
    "os",
    "subprocess",
    "sys",
    "shutil",
    "socket",
    "ctypes",
    "multiprocessing",
    "importlib",
}


@dataclass
class ExecutionResult:
    success: bool
    stdout: str
    stderr: str
    error: str = ""  # 沙箱层错误（timeout / blocked）


class SandboxExecutor:
    """subprocess + timeout 的最小化 Python 沙箱。"""

    def __init__(self, timeout_seconds: int = 5) -> None:
        if timeout_seconds < 1:
            raise ValueError("timeout_seconds must be >= 1")
        self.timeout_seconds = timeout_seconds

    async def run_python(self, code: str) -> ExecutionResult:
        """在子进程中执行 Python 代码。

        安全检查顺序：
          1. 黑名单 import 检测（前置）
          2. subprocess 执行 + 超时
        """
        # L1: 黑名单 import 检测
        blocked, mod = self._detect_blocked_import(code)
        if blocked:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr="",
                error=f"blocked: import {mod} not allowed",
            )

        # L2: subprocess 执行
        try:
            proc = await asyncio.create_subprocess_exec(
                "python",
                "-c",
                code,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=self.timeout_seconds,
            )
            return ExecutionResult(
                success=proc.returncode == 0,
                stdout=stdout.decode("utf-8", errors="ignore"),
                stderr=stderr.decode("utf-8", errors="ignore"),
            )
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except Exception:  # noqa: BLE001
                pass
            return ExecutionResult(
                success=False,
                stdout="",
                stderr="",
                error=f"timeout after {self.timeout_seconds}s",
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception(f"[SandboxExecutor] run_python failed: {exc}")
            return ExecutionResult(
                success=False,
                stdout="",
                stderr="",
                error=str(exc),
            )

    @staticmethod
    def _detect_blocked_import(code: str) -> tuple[bool, str]:
        """检测代码里是否 import 黑名单中的模块。

        Returns:
            (blocked, module_name) — blocked=False 表示放行
        """
        # 匹配 import x / import x.y / from x import ...
        pattern = re.compile(
            r"^\s*(?:import\s+([\w.]+)|from\s+([\w.]+)\s+import)",
            re.MULTILINE,
        )
        for match in pattern.finditer(code):
            mod = match.group(1) or match.group(2)
            top = mod.split(".")[0]
            if top in BLOCKED_MODULES:
                return True, top
        return False, ""