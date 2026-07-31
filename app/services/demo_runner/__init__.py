"""演示主链统一执行器 (Demo Runner).

P0 阶段: 仅暴露 trace_id + 步骤耗时 + fallback 标记的数据类与最小执行器.
P1 阶段: 接入 Tutor Engine (`app.services.tutor_engine.engine.process_chat_request`),
         把每步结果合并进 `LivePathResult.steps`.

公开 API:
    run_live_demo_path(user_id, scenario) -> LivePathResult
    LivePathResult  (dataclass; 含 trace_id / steps / fallback_used / elapsed_ms)
"""
from app.services.demo_runner.live_path import (  # noqa: F401
    LivePathResult,
    run_live_demo_path,
)

__all__ = ["LivePathResult", "run_live_demo_path"]
