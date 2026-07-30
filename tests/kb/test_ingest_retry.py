"""Tests for KB ingest_node: IntegrityError retry + happy path."""
import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.exc import IntegrityError


VALID_SOURCE = {
    "type": "textbook",
    "reference": "ISBN-1234",
    "confidence": 0.95,
    "verifier_id": None,
}


def _make_fake_repo():
    """Return a repo mock whose insert() raises the given exception sequence."""
    repo = MagicMock()

    def _side_effect(node):
        if repo._errors:
            raise repo._errors.pop(0)
        return None

    repo._errors = []
    repo.insert.side_effect = _side_effect
    return repo


def test_ingest_retries_on_integrity_error_then_succeeds():
    """First insert raises IntegrityError, second succeeds, returns valid id."""
    from app.services.kb import ingestion as ing_mod

    repo = _make_fake_repo()
    repo._errors.append(
        IntegrityError("mock statement", {}, Exception("UNIQUE constraint failed: knowledge_node.id"))
    )

    # Reset the counter for determinism.
    from app.models.knowledge_node import _COUNTER, _COUNTER_INITIALIZED

    _COUNTER["v"] = 0
    _COUNTER_INITIALIZED["done"] = False

    # OrmKnowledgeRepository is imported lazily inside _persist_to_db, so we
    # must patch the source module path.
    with patch.object(ing_mod, "_persist_to_qdrant", return_value=True), \
         patch("app.repositories.orm.knowledge_node.OrmKnowledgeRepository", return_value=repo):
        nid = ing_mod.ingest_node(
            subject="math", title="勾股定理", content="a²+b²=c²", source=VALID_SOURCE
        )

    assert nid.startswith("KB-CON-")
    # Two attempts: one failed IntegrityError, one success.
    assert repo.insert.call_count == 2


def test_ingest_raises_runtime_error_after_max_retries():
    """If every retry raises IntegrityError, ingest_node raises RuntimeError."""
    from app.services.kb import ingestion as ing_mod
    from app.models.knowledge_node import _COUNTER, _COUNTER_INITIALIZED

    _COUNTER["v"] = 0
    _COUNTER_INITIALIZED["done"] = False

    repo = MagicMock()
    repo.insert.side_effect = IntegrityError(
        "mock", {}, Exception("UNIQUE constraint failed: knowledge_node.id")
    )

    with patch.object(ing_mod, "_persist_to_qdrant", return_value=True), \
         patch("app.repositories.orm.knowledge_node.OrmKnowledgeRepository", return_value=repo):
        with pytest.raises(RuntimeError, match="KB ingest failed after"):
            ing_mod.ingest_node(
                subject="math", title="x", content="y", source=VALID_SOURCE
            )

    # 5 attempts.
    assert repo.insert.call_count == 5


def test_ingest_happy_path_single_attempt():
    """No IntegrityError → exactly one insert call."""
    from app.services.kb import ingestion as ing_mod
    from app.models.knowledge_node import _COUNTER, _COUNTER_INITIALIZED

    _COUNTER["v"] = 0
    _COUNTER_INITIALIZED["done"] = False

    repo = MagicMock()
    repo.insert.return_value = None

    with patch.object(ing_mod, "_persist_to_qdrant", return_value=True), \
         patch("app.repositories.orm.knowledge_node.OrmKnowledgeRepository", return_value=repo):
        nid = ing_mod.ingest_node(
            subject="math", title="happy", content="c", source=VALID_SOURCE
        )

    assert nid.startswith("KB-CON-")
    assert repo.insert.call_count == 1


def test_ingest_rejects_missing_source():
    from app.services.kb.ingestion import ingest_node, IngestionRejected

    with pytest.raises(IngestionRejected):
        ingest_node(subject="math", title="x", content="y", source=None)
