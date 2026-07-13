"""Verify Qdrant master is reachable at startup and singleton failover."""
import os
from unittest import mock

import pytest

from app.services.kb.qdrant_client import QdrantClientSingleton


def test_qdrant_singleton_connect():
    """Singleton must reach Qdrant master and return OK.

    Note: ``health()`` is a classmethod on the singleton wrapper; the
    raw ``QdrantClient`` instance returned by ``.get()`` does not expose
    it. The spec snippet in Step 1 of S0.1 calls ``client.health()`` on
    the returned QdrantClient which does not exist on that type --
    corrected here to call ``QdrantClientSingleton.health()`` so the
    test exercises the singleton path the same way the rest of the
    codebase will.

    Skipped when no Qdrant is reachable on the configured host/port --
    this test is meant to run against the docker-compose.dev.yml stack
    brought up via ``docker compose -f docker-compose.dev.yml up -d``.
    """
    # Reset cached clients so each run re-resolves host/port.
    QdrantClientSingleton._master = None
    QdrantClientSingleton._replica = None
    # Exercise the singleton lookup path (master first, replica on fail).
    QdrantClientSingleton.get()
    info = QdrantClientSingleton.health()
    if info["status"] == "down":
        pytest.skip(
            "Qdrant not reachable on "
            f"{os.getenv('QDRANT_MASTER_HOST', 'localhost')}:"
            f"{os.getenv('QDRANT_MASTER_PORT', '6333')} -- "
            "start docker-compose.dev.yml to run this test."
        )
    assert info["status"] == "ok"


def _fake_client():
    return mock.MagicMock(spec=["get_collections"])


def test_health_reports_master_when_master_alive():
    """Master up -> status 'ok', node 'master'."""
    QdrantClientSingleton._master = _fake_client()
    QdrantClientSingleton._replica = _fake_client()
    info = QdrantClientSingleton.health()
    assert info == {"status": "ok", "node": "master"}


def test_health_reports_degraded_when_master_down_replica_up():
    """Master down, replica up -> 'degraded' / 'replica'."""
    master = _fake_client()
    master.get_collections.side_effect = ConnectionError("master down")
    replica = _fake_client()
    QdrantClientSingleton._master = master
    QdrantClientSingleton._replica = replica
    info = QdrantClientSingleton.health()
    assert info == {"status": "degraded", "node": "replica"}


def test_health_reports_down_when_both_down():
    """Both down -> 'down' / 'none'."""
    master = _fake_client()
    master.get_collections.side_effect = ConnectionError("master down")
    replica = _fake_client()
    replica.get_collections.side_effect = ConnectionError("replica down")
    QdrantClientSingleton._master = master
    QdrantClientSingleton._replica = replica
    info = QdrantClientSingleton.health()
    assert info == {"status": "down", "node": "none"}


def test_get_falls_back_to_replica_when_master_raises():
    """get() returns replica when master's get_collections raises."""
    master = _fake_client()
    master.get_collections.side_effect = ConnectionError("master down")
    replica = _fake_client()
    QdrantClientSingleton._master = master
    QdrantClientSingleton._replica = replica
    assert QdrantClientSingleton.get() is replica
