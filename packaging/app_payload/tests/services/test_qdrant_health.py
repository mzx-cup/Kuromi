"""Verify Qdrant master is reachable at startup and singleton failover."""
import os
from unittest import mock

import pytest

from app.services.kb.qdrant_client import QdrantClientSingleton


def test_qdrant_singleton_connect():
    """Singleton must reach Qdrant master and report a healthy node."""
    health = QdrantClientSingleton.health()
    if health["status"] == "down":
        pytest.skip("Qdrant not reachable (env without Docker access)")
    assert health["status"] in {"ok", "degraded"}
    assert health["node"] in {"master", "replica"}


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
    """get() returns replica when master construction raises."""
    QdrantClientSingleton._master = None
    QdrantClientSingleton._replica = _fake_client()
    with mock.patch.object(
        QdrantClientSingleton,
        "_master_client",
        side_effect=ConnectionError("master down"),
    ):
        assert QdrantClientSingleton.get() is QdrantClientSingleton._replica
