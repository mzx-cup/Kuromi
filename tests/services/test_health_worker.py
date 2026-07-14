"""Health worker probes Qdrant + Redis every 10s."""
import pytest
from unittest.mock import patch
from app.core.health_worker import HealthWorker


def test_health_worker_reports_current_levels():
    with patch("app.core.health_worker.probe_qdrant", return_value=True), \
         patch("app.core.health_worker.probe_redis", return_value=True):
        worker = HealthWorker(interval_seconds=0.1)
        worker.run_once()
        levels = worker.snapshot()
        assert levels["qdrant"] == "L0"
        assert levels["redis"] == "L0"