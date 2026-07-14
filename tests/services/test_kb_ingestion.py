"""KnowledgeNode ingestion must reject entries with missing/empty SourceRef."""
import pytest
from app.services.kb.source_ref import SourceRef


def test_source_ref_required_textbook():
    ref = SourceRef(type="textbook", reference="ISBN-9787", confidence=0.95, verifier_id=None)
    assert ref.is_valid()


def test_source_ref_rejects_none():
    with pytest.raises(ValueError, match="must not be None"):
        SourceRef(type=None, reference="x", confidence=1.0, verifier_id=None)


def test_source_ref_rejects_empty_reference():
    with pytest.raises(ValueError, match="must not be empty"):
        SourceRef(type="textbook", reference="", confidence=1.0, verifier_id=None)


def test_source_ref_rejects_invalid_confidence():
    with pytest.raises(ValueError, match="between 0 and 1"):
        SourceRef(type="textbook", reference="ISBN-x", confidence=1.5, verifier_id=None)


def test_source_ref_rejects_low_confidence():
    with pytest.raises(ValueError, match="between 0 and 1"):
        SourceRef(type="textbook", reference="ISBN-x", confidence=-0.1, verifier_id=None)


def test_source_ref_accepts_boundary_zero():
    ref = SourceRef(type="manual", reference="x", confidence=0.0, verifier_id=None)
    assert ref.is_valid()


def test_source_ref_accepts_boundary_one():
    ref = SourceRef(type="codebase", reference="abc123", confidence=1.0, verifier_id="verifier-1")
    assert ref.is_valid()


def test_source_ref_accepts_all_valid_types():
    for t in ("textbook", "codebase", "agent_output", "manual", "external_parsed"):
        ref = SourceRef(type=t, reference="r", confidence=0.5, verifier_id=None)
        assert ref.is_valid()


def test_ingestion_rejects_node_without_source():
    from app.services.kb.ingestion import ingest_node, IngestionRejected
    with pytest.raises(IngestionRejected, match="source"):
        ingest_node(subject="math", title="x", content="y", source=None)


def test_ingestion_accepts_node_with_valid_source(monkeypatch):
    from app.services.kb.ingestion import ingest_node
    monkeypatch.setattr("app.services.kb.ingestion._persist_to_qdrant", lambda n: True)
    monkeypatch.setattr("app.services.kb.ingestion._persist_to_db", lambda n: True)
    nid = ingest_node(
        subject="math", title="勾股定理", content="a²+b²=c²",
        source={"type": "textbook", "reference": "ISBN-1234", "confidence": 0.95, "verifier_id": None}
    )
    assert nid.startswith("KB-CON-")
