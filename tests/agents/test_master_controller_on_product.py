# -*- coding: utf-8 -*-
"""Tests for MasterController on_product callback (generator artifact push).

回归背景: _run_and_emit 之前读 state.metadata[f"{gen.name}_output"]
(如 document_generator_output), 但各 GeneratorAgent 实际写入的是
document_output / mindmap_output / exercise_output / video_output,
导致 on_product 永远拿不到 payload, 控制塔产物无法实时推到聊天框.

注: 用 asyncio.run 而非 pytest.mark.asyncio, 避免 pytest-asyncio 插件依赖.
"""
from __future__ import annotations

import asyncio

from agents import MasterController
from state import StudentState


class _FakeGenerator:
    """最小 generator: 往真实产物键写一份 payload."""

    def __init__(self, name: str, output_key: str):
        self.name = name
        self.role = name
        self._output_key = output_key

    async def run(self, state: StudentState) -> StudentState:
        state.metadata[self._output_key] = {"text_content": f"product of {self.name}"}
        return state


def test_on_product_receives_real_output_key():
    """generator 写 document_output, on_product 应回调收到同一份 payload."""
    controller = MasterController()
    controller.register_generator(
        "document_generator", _FakeGenerator("document_generator", "document_output")
    )
    state = StudentState(student_id="u1")

    products: list[tuple[str, dict]] = []

    async def on_product(name: str, payload: dict) -> None:
        products.append((name, payload))

    asyncio.run(_run(controller, state, on_product))

    assert products == [
        ("document_generator", {"text_content": "product of document_generator"})
    ]


async def _run(controller: MasterController, state: StudentState, on_product) -> None:
    await controller.execute(state, on_product=on_product)


def test_on_product_all_four_generator_keys():
    """planner 路由到 4 个 generator 时, 4 个真实产物键都要触发回调."""
    controller = MasterController()
    for name, key in [
        ("document_generator", "document_output"),
        ("mindmap_generator", "mindmap_output"),
        ("exercise_generator", "exercise_output"),
        ("video_content", "video_output"),
    ]:
        controller.register_generator(name, _FakeGenerator(name, key))
    # planner_output 让 route_generators 选中全部 4 类 content_type
    state = StudentState(student_id="u1")
    state.metadata["planner_output"] = {
        "learning_objective": "obj",
        "difficulty_level": "medium",
        "content_types": ["document", "mindmap", "exercise", "video"],
        "reasoning": "test",
    }

    seen: list[str] = []

    async def on_product(name: str, payload: dict) -> None:
        seen.append(name)

    asyncio.run(_run(controller, state, on_product))

    assert sorted(seen) == [
        "document_generator", "exercise_generator",
        "mindmap_generator", "video_content",
    ]


def test_on_product_without_callback_is_noop():
    """不传 on_product 时流水线照常跑, 不抛错."""
    controller = MasterController()
    controller.register_generator(
        "document_generator", _FakeGenerator("document_generator", "document_output")
    )
    state = StudentState(student_id="u1")
    asyncio.run(controller.execute(state))
    assert state.metadata["document_output"]["text_content"] == (
        "product of document_generator"
    )
