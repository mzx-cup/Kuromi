"""1% gray cutover: kb_settings.read_backend_percentage 路由 RAG 到 LangChain / legacy.

Acceptance:
  * percentage == 0 -> legacy _fetch_rag 永远被调用；_fetch_rag_langchain 不会执行
  * percentage == 100 -> legacy _fetch_rag 不会被调用；_fetch_rag_langchain 执行
  * LangChain 路径异常 -> gracefully 退化为空 rag_results，不阻塞 aggregate
  * random.randint 的 monkeypatch 单点控制切流决策
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.services.tutor_engine.context_aggregator import (
    ContextAggregator,
    ContextAggregatorConfig,
)
from app.services.tutor_engine.models import (
    EventContext,
    LearningState,
    RichContext,
    TutorEvent,
    TutorEventType,
)


# ------------------------------------------------------------------
# Fixtures / helpers
# ------------------------------------------------------------------


def _make_event(question: str = "勾股定理是什么？") -> TutorEvent:
    return TutorEvent(
        type=TutorEventType.QUESTION_ASKED,
        student_id="u-gray",
        context=EventContext(session_id="s-gray"),
        payload={"question": question},
    )


class _FakeVS:
    """Mimics langchain VectorStore.similarity_search_with_score()."""

    def __init__(self, hits: list | None = None) -> None:
        self._hits = hits if hits is not None else [
            ({"id": "KB-CON-1001", "title": "pythag", "content": "a^2+b^2=c^2"}, 0.93),
            ({"id": "KB-CON-1002", "title": "trig", "content": "sin^2+cos^2=1"}, 0.81),
        ]
        self.calls: list[tuple[str, int]] = []

    def similarity_search_with_score(self, query: str, k: int = 5):
        self.calls.append((query, k))
        return self._hits


@pytest.fixture
def stub_dependencies(monkeypatch):
    """桩化 aggregator 内的其他数据源，避免 db / network 依赖。"""

    async def _fake_history(session_id, n):
        return []

    async def _fake_sm2(student_id):
        return []

    async def _fake_deadlines(student_id, days=7):
        return []

    async def _fake_web(question):
        return None

    repo = MagicMock(
        get_sm2_due=lambda _uid: [],
        get_upcoming_deadlines=lambda _uid, days=7: [],
    )

    monkeypatch.setattr(
        "app.services.tutor_engine.context_aggregator.get_repository_for_user",
        lambda uid, **kwargs: repo,
    )
    monkeypatch.setattr(
        "app.services.tutor_engine.context_aggregator._default_web_search",
        _fake_web,
    )
    monkeypatch.setattr(
        "app.services.tutor_engine.context_aggregator._default_memory_retriever",
        lambda *args, **kwargs: [],
    )
    return _fake_history


@pytest.fixture
def patch_kb_percentage(monkeypatch):
    """返回 setter，覆盖 kb_settings.read_backend_percentage。"""

    def _set(percentage: int) -> None:
        from app.core import config as config_module
        monkeypatch.setattr(
            config_module.kb_settings,
            "read_backend_percentage",
            percentage,
        )

    return _set


def _make_aggregator(**overrides) -> ContextAggregator:
    """构造一个所有数据源都被 stub 化的 aggregator。"""

    rag_retriever = overrides.pop("rag_retriever", lambda kws: ("", [], {}))
    aggregator = ContextAggregator(
        config=ContextAggregatorConfig(enable_rag=True),
        rag_retriever=rag_retriever,
    )

    async def _history(session_id, n):
        return []
    aggregator._get_messages = _history

    # 桩化 _get_learning_state / SM2 / Deadlines
    aggregator._get_learning_state = MagicMock(
        wraps=_async_return(lambda *_: LearningState())
    )
    return aggregator


def _async_return(value):
    async def _coro(*args, **kwargs):
        return value
    return _coro


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_zero_percentage_always_uses_legacy(
    monkeypatch, stub_dependencies, patch_kb_percentage
):
    """percentage == 0 时无论 random 怎样都走 legacy。"""

    patch_kb_percentage(0)
    import random as _random
    monkeypatch.setattr(_random, "randint", lambda a, b: 1)

    rag_called = {"count": 0}
    langchain_called = {"count": 0}

    async def fake_legacy(event, rich):
        rag_called["count"] += 1
        rich.rag_context_text = "legacy-text"

    async def fake_langchain(event, rich):
        langchain_called["count"] += 1

    aggregator = _make_aggregator(
        rag_retriever=lambda kws: ("legacy-text", ["src-legacy"], {}),
    )
    monkeypatch.setattr(aggregator, "_fetch_rag", fake_legacy)
    monkeypatch.setattr(aggregator, "_fetch_rag_langchain", fake_langchain)

    rich = await aggregator.aggregate(_make_event())

    assert rag_called["count"] == 1
    assert langchain_called["count"] == 0
    assert rich.rag_context_text == "legacy-text"


@pytest.mark.asyncio
async def test_full_percentage_always_uses_langchain(
    monkeypatch, stub_dependencies, patch_kb_percentage
):
    """percentage == 100 时永远走 LangChain；不调用 legacy。"""

    patch_kb_percentage(100)
    import random as _random
    # 即使 random=1（最不利），percentage=100 仍然要求走 langchain
    monkeypatch.setattr(_random, "randint", lambda a, b: 1)

    rag_called = {"count": 0}
    langchain_called = {"count": 0}

    async def fake_legacy(event, rich):
        rag_called["count"] += 1

    async def fake_langchain(event, rich):
        langchain_called["count"] += 1
        rich.rag_context_text = "lc-text"

    aggregator = _make_aggregator(
        rag_retriever=lambda kws: ("legacy-text", ["src"], {}),
    )
    monkeypatch.setattr(aggregator, "_fetch_rag", fake_legacy)
    monkeypatch.setattr(aggregator, "_fetch_rag_langchain", fake_langchain)

    rich = await aggregator.aggregate(_make_event())

    assert rag_called["count"] == 0
    assert langchain_called["count"] == 1
    assert rich.rag_context_text == "lc-text"


@pytest.mark.asyncio
async def test_percent_threshold_split_by_random(
    monkeypatch, stub_dependencies, patch_kb_percentage
):
    """percentage=30 时，random=20 (≤30) 走 langchain；random=50 (>30) 走 legacy。"""

    patch_kb_percentage(30)
    import random as _random

    aggregator = _make_aggregator(
        rag_retriever=lambda kws: ("leg", [], {}),
    )

    # Case A: random=20 -> 走 langchain
    lc_a, leg_a = {"count": 0}, {"count": 0}

    async def fa_leg(event, rich):
        leg_a["count"] += 1
        rich.rag_context_text = "leg"
    async def fa_lc(event, rich):
        lc_a["count"] += 1
        rich.rag_context_text = "lc"

    monkeypatch.setattr(aggregator, "_fetch_rag", fa_leg)
    monkeypatch.setattr(aggregator, "_fetch_rag_langchain", fa_lc)
    monkeypatch.setattr(_random, "randint", lambda a, b: 20)
    rich_a = await aggregator.aggregate(_make_event())
    assert rich_a.rag_context_text == "lc"
    assert leg_a["count"] == 0

    # Case B: random=50 -> 走 legacy
    lc_b, leg_b = {"count": 0}, {"count": 0}

    async def fb_leg(event, rich):
        leg_b["count"] += 1
        rich.rag_context_text = "leg"
    async def fb_lc(event, rich):
        lc_b["count"] += 1
        rich.rag_context_text = "lc"

    monkeypatch.setattr(aggregator, "_fetch_rag", fb_leg)
    monkeypatch.setattr(aggregator, "_fetch_rag_langchain", fb_lc)
    monkeypatch.setattr(_random, "randint", lambda a, b: 50)
    rich_b = await aggregator.aggregate(_make_event())
    assert rich_b.rag_context_text == "leg"
    assert lc_b["count"] == 0


@pytest.mark.asyncio
async def test_fetch_rag_langchain_writes_rag_results(
    monkeypatch, stub_dependencies, patch_kb_percentage
):
    """_fetch_rag_langchain 绕过切流直接调用 -> 写入 rag_results / rag_context_text。"""

    patch_kb_percentage(0)
    aggregator = _make_aggregator(
        config=ContextAggregatorConfig(enable_rag=True, rag_top_k=5),
    )
    fake_vs = _FakeVS()
    monkeypatch.setattr(
        aggregator,
        "_build_langchain_vector_store",
        lambda: fake_vs,
    )

    rich = RichContext(event=_make_event())
    await aggregator._fetch_rag_langchain(_make_event(), rich)

    assert len(rich.rag_results) >= 1
    assert all(r.source_id for r in rich.rag_results)
    assert "a^2+b^2=c^2" in rich.rag_context_text
    assert fake_vs.calls, "FakeVS.similarity_search_with_score should have been called"


@pytest.mark.asyncio
async def test_fetch_rag_langchain_swallows_exceptions(
    monkeypatch, stub_dependencies, patch_kb_percentage
):
    """LangChain 路径异常 -> aggregate 不抛；rich.rag_results 留空。"""

    patch_kb_percentage(100)
    import random as _random
    monkeypatch.setattr(_random, "randint", lambda a, b: 1)

    aggregator = _make_aggregator()

    def _raise():
        raise RuntimeError("qdrant down")
    monkeypatch.setattr(aggregator, "_build_langchain_vector_store", _raise)

    rich = await aggregator.aggregate(_make_event())

    # 异常被吞，rag_results 留空
    assert rich.rag_results == []
