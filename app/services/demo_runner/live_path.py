"""演示主链统一执行器 (P0 骨架 + P1 接入 Tutor Engine).

设计原则:
- 步骤定义与执行分离: `_demo_steps` 工厂返回 (name, payload) 元组序列,
  ``run_live_demo_path`` 顺序执行, 每步结果合并进 `LivePathResult.steps`.
- 步骤分发: ``_run_step`` 根据 step_name 选择调用源:
    - ``socratic``      → TutorDecisionEngine.process_chat_request
    - ``profile``       → DemoRepository.load_profile
    - ``diagnose``      → DemoRepository.load_weak_concepts (wrap 成 list[dict])
    - ``path_adjust``   → DemoRepository.load_learning_path
    - ``mastery_diff``  → DemoRepository.diff_mastery
    - ``recommendations`` → DemoRepository.load_recommendations
    - ``teacher_view``  → DemoRepository + teacher 静态 seed
    - 其它/未知         → 仅占位, 标 ok=True
- 降级透明: 任一步抛异常 → step["fallback"]=True + step["error"] 非空,
  ``LivePathResult.fallback_used`` 也会被置 True, 演示主链不断.
- trace_id 贯穿: 顶层 lp_<12hex> 串联 7 步, 引擎内 step 生成 ag_<10hex>,
  都在 step 字典里保留, 便于回放.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Iterator


@dataclass
class LivePathResult:
    """演示主链执行结果.

    字段:
        trace_id: 全链路唯一 ID, 格式 ``lp_<12hex>``
        steps: 每一步的执行快照, 每条至少含 {name, ok, ts_ms, fallback, trace_id, error}
        fallback_used: 是否有任一步降级
        elapsed_ms: 全链路总耗时
    """

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


def _demo_steps(
    user_id: str, scenario: str = "default"
) -> Iterator[tuple[str, dict[str, Any]]]:
    """生成演示主链的步骤序列.

    每个步骤 (name, payload) 是声明式定义; ``_run_step`` 负责选择调用源.
    """
    yield (
        "profile",
        {"user_id": user_id, "action": "load_profile", "scenario": scenario},
    )
    yield (
        "diagnose",
        {"user_id": user_id, "action": "diagnose_weakness", "scenario": scenario},
    )
    yield (
        "socratic",
        {
            "user_id": user_id,
            "message": "什么是勾股定理",
            "mode": "socratic",
            "scenario": scenario,
        },
    )
    yield (
        "path_adjust",
        {"user_id": user_id, "action": "replan", "scenario": scenario},
    )
    yield (
        "micro_exercise",
        {
            "user_id": user_id,
            "exercise_id": "demo_1",
            "answer": "1",
            "scenario": scenario,
        },
    )
    yield (
        "mastery_diff",
        {"user_id": user_id, "action": "diff_mastery", "scenario": scenario},
    )
    yield (
        "recommendations",
        {"user_id": user_id, "action": "load_recommendations", "scenario": scenario},
    )
    yield (
        "teacher_view",
        {"student_id": user_id, "action": "teacher_suggestions", "scenario": scenario},
    )


async def run_live_demo_path(
    user_id: str, scenario: str = "default"
) -> LivePathResult:
    """执行演示主链并返回结构化结果.

    P1 Task 14: 接入真实 TutorDecisionEngine + DemoRepository,
    每步记 trace_id + 耗时 + fallback 标记.
    """
    trace_id = f"lp_{uuid.uuid4().hex[:12]}"
    started = time.time()
    steps: list[dict[str, Any]] = []
    fallback_used = False

    for step_name, payload in _demo_steps(user_id, scenario):
        t0 = time.time()
        try:
            result = await _run_step(step_name, payload, trace_id=trace_id)
            ok = result.get("ok", True)
            error = result.get("error", "")
            step_fallback = result.get("fallback", not ok)
            inner_trace_id = result.get("trace_id", trace_id)
            inner_data = result.get("data")
        except Exception as exc:  # noqa: BLE001
            ok = False
            error = str(exc)[:200]
            step_fallback = True
            inner_trace_id = trace_id
            inner_data = None
        step_ms = int((time.time() - t0) * 1000)
        steps.append(
            {
                "name": step_name,
                "ok": ok,
                "ts_ms": step_ms,
                "fallback": step_fallback,
                "trace_id": inner_trace_id,
                "error": error,
                "data": inner_data,
            }
        )
        if step_fallback:
            fallback_used = True

    return LivePathResult(
        trace_id=trace_id,
        steps=steps,
        fallback_used=fallback_used,
        elapsed_ms=int((time.time() - started) * 1000),
    )


async def _run_step(
    step_name: str, payload: dict[str, Any], trace_id: str
) -> dict[str, Any]:
    """执行单步, 返回 ``{ok, error, fallback, trace_id, data}`` 字典.

    任一异常都会被 ``run_live_demo_path`` 捕获, 包装为 fallback=True 的 step.
    """
    # 局部 import 避免启动期把 Repository / Engine 拉入 (演示骨架可独立运行).
    if step_name == "socratic":
        from app.services.tutor_engine.engine import TutorDecisionEngine

        engine = TutorDecisionEngine()
        # 透传 trace_id, 让 engine 返回 dict 里也有, 串联整条链路.
        decision = await engine.process_chat_request(
            user_id=str(payload.get("user_id", "")),
            message=str(payload.get("message", "")),
            mode=str(payload.get("mode", "socratic")),
            trace_id=trace_id,
        )
        return {
            "ok": True,
            "fallback": bool(decision.get("blocked", False)),
            "trace_id": decision.get("trace_id", trace_id),
            "data": {
                "agent": decision.get("agent"),
                "next_step": decision.get("next_step"),
                "blocked": decision.get("blocked", False),
                "reason": decision.get("reason"),
            },
        }

    if step_name in ("profile", "path_adjust", "diagnose",
                     "mastery_diff", "recommendations", "teacher_view"):
        from app.services.repository import DemoRepository

        repo = DemoRepository()
        user_id = payload.get("user_id") or payload.get("student_id")
        if not user_id:
            return {"ok": False, "fallback": True, "error": "missing user_id"}
        try:
            if step_name == "profile":
                data = repo.load_profile(user_id)
            elif step_name == "diagnose":
                data = repo.load_weak_concepts(user_id)
            elif step_name == "path_adjust":
                data = repo.load_learning_path(user_id)
            elif step_name == "mastery_diff":
                data = repo.diff_mastery(user_id)
            elif step_name == "recommendations":
                data = repo.load_recommendations(user_id)
            else:  # teacher_view
                # 复用 path + recommendations 给教师视图, 简化数据.
                data = {
                    "student_id": user_id,
                    "suggestions": [
                        f"建议关注 {user_id} 的薄弱点 (来自 demo seed)",
                    ],
                    "fallback": False,
                }
            return {
                "ok": True,
                "fallback": bool(data.get("fallback", False)) if isinstance(data, dict) else False,
                "trace_id": trace_id,
                "data": data,
            }
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "fallback": True, "error": str(exc)[:200], "trace_id": trace_id}

    if step_name == "micro_exercise":
        # 演示用占位: 真实链路里这里接 /api/quiz/grade, 演示主链仅打点.
        return {
            "ok": True,
            "fallback": False,
            "trace_id": trace_id,
            "data": {
                "exercise_id": payload.get("exercise_id"),
                "answer": payload.get("answer"),
                "graded": True,
                "note": "demo placeholder; real grading via /api/quiz/grade",
            },
        }

    # 未知 step_name: 仅占位, 标 ok=True 不阻断主链.
    return {
        "ok": True,
        "fallback": False,
        "trace_id": trace_id,
        "data": {"unknown_step": step_name},
    }
