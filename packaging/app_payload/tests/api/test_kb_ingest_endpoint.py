"""POST /api/kb/ingest contract test (slice-s1).

We exercise two paths:
  1. Happy path: valid payload -> 200, id starts with ``KB-CON-``.
  2. Validation failure: out-of-range ``confidence`` -> 422 from pydantic.

The qdrant side is intentionally a stub (``_persist_to_qdrant`` still
raises ``NotImplementedError``); we monkey-patch it so the success
path can complete without standing up a vector store.

DB isolation: the L1 repo's sync engine is rebuilt per-test to point
at a fresh tmp SQLite file. This keeps the run hermetic even when the
project's default DB has accumulated rows from earlier test runs.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app.services.kb.ingestion as ingestion_module
from app.models import knowledge_node as kn_model
from app.models.base import Base
from app.repositories.orm import knowledge_node as kn_repo
from main import app


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    """Point the L1 sync engine at a fresh tmp SQLite file per-test."""
    db_path = str(tmp_path / "kb_l1.db")
    monkeypatch.setenv("KB_L1_SYNC_DB_URL", f"sqlite:///{db_path}")
    kn_repo.reset_session_factory(f"sqlite:///{db_path}")
    # Recreate the L1 schema on the fresh DB.
    Base.metadata.create_all(kn_repo._engine)
    # Reset the monotonic id counter so ``make_node_id`` starts at 1.
    kn_model._COUNTER["v"] = 0
    yield db_path


@pytest.fixture
def _stub_qdrant(monkeypatch):
    """Bypass the S2 qdrant wiring — it is still NotImplementedError."""
    monkeypatch.setattr(ingestion_module, "_persist_to_qdrant", lambda n: True)


def test_ingest_endpoint_ingests_valid_node(isolated_db, _stub_qdrant):
    with TestClient(app) as client:
        r = client.post(
            "/api/kb/ingest",
            json={
                "subject": "math",
                "title": "勾股定理",
                "content": "a^2 + b^2 = c^2",
                "source": {
                    "type": "textbook",
                    "reference": "ISBN-9787",
                    "confidence": 0.9,
                },
            },
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"].startswith("KB-CON-")


def test_ingest_endpoint_rejects_invalid_confidence(isolated_db):
    with TestClient(app) as client:
        r = client.post(
            "/api/kb/ingest",
            json={
                "subject": "math",
                "title": "x",
                "content": "y",
                "source": {
                    "type": "textbook",
                    "reference": "ISBN-1",
                    "confidence": 1.5,
                },
            },
        )
    # pydantic Field(ge=0, le=1) rejects 1.5 -> 422
    assert r.status_code == 422
