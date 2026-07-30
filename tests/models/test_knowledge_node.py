"""Tests for the L1 KnowledgeNode ID generator + DB-backed init."""
from unittest.mock import MagicMock

from app.models import knowledge_node as kn_mod
from app.models.knowledge_node import (
    _COUNTER,
    _COUNTER_INITIALIZED,
    init_counter_from_db,
    make_node_id,
)


def _reset_counter_to(value: int) -> None:
    """Test helper: reset both the counter and the init flag."""
    _COUNTER["v"] = value
    _COUNTER_INITIALIZED["done"] = False


def test_make_node_id_increments():
    _reset_counter_to(0)
    before = _COUNTER["v"]
    id1 = make_node_id("math", "T1")
    id2 = make_node_id("math", "T2")
    assert id1 != id2
    assert id1.startswith("KB-CON-")
    assert id2.startswith("KB-CON-")
    assert _COUNTER["v"] >= before + 2


def test_make_node_id_format_4_digits():
    _reset_counter_to(0)
    nid = make_node_id("math", "T")
    # Format is KB-CON-XXXX with 4-digit zero-pad.
    assert len(nid) == len("KB-CON-") + 4
    suffix = nid.split("-")[-1]
    assert len(suffix) == 4
    assert suffix.isdigit()


def test_init_counter_resets_from_db_max():
    """Simulate DB returning max_v=42 → _COUNTER must be >= 42 after init."""
    _reset_counter_to(0)

    fake_session = MagicMock()
    fake_session.execute.return_value.fetchone.return_value = (42,)

    fake_factory = MagicMock()
    fake_factory.return_value.__enter__ = MagicMock(return_value=fake_session)
    fake_factory.return_value.__exit__ = MagicMock(return_value=False)

    init_counter_from_db(fake_factory)
    assert _COUNTER["v"] >= 42
    # Next make_node_id call must be >= 43.
    nid = make_node_id("math", "T")
    assert int(nid.split("-")[-1]) >= 43


def test_init_counter_handles_empty_db():
    """If DB has no KB-CON- rows, max_v should be 0 and counter stays 0."""
    _reset_counter_to(0)

    fake_session = MagicMock()
    fake_session.execute.return_value.fetchone.return_value = (None,)

    fake_factory = MagicMock()
    fake_factory.return_value.__enter__ = MagicMock(return_value=fake_session)
    fake_factory.return_value.__exit__ = MagicMock(return_value=False)

    init_counter_from_db(fake_factory)
    assert _COUNTER["v"] == 0


def test_init_counter_idempotent():
    """Calling init twice must not double-jump the counter."""
    _reset_counter_to(0)

    fake_session = MagicMock()
    fake_session.execute.return_value.fetchone.return_value = (10,)

    fake_factory = MagicMock()
    fake_factory.return_value.__enter__ = MagicMock(return_value=fake_session)
    fake_factory.return_value.__exit__ = MagicMock(return_value=False)

    init_counter_from_db(fake_factory)
    first = _COUNTER["v"]
    # Second call must be a no-op even if we swap the factory.
    other_factory = MagicMock()
    other_factory.return_value.__enter__ = MagicMock(
        return_value=MagicMock(execute=MagicMock(return_value=MagicMock(fetchone=MagicMock(return_value=(999,))))
    ))
    other_factory.return_value.__exit__ = MagicMock(return_value=False)
    init_counter_from_db(other_factory)
    assert _COUNTER["v"] == first
