"""3-layer fail-open logger: DB -> Redis -> Disk."""
import pytest
from unittest.mock import MagicMock, patch
from app.services.agent_log.resilient_logger import ResilientBehaviorLogger, LogResult
from app.models.agent_behavior_log import AgentBehaviorLog


@pytest.fixture
def sample_log():
    return AgentBehaviorLog(agent_id="SocraticAgent", user_id="u1", action_type="chat", input_summary="q", output_text="a")


def test_logger_writes_to_db_when_ok(sample_log):
    with patch("app.services.agent_log.resilient_logger.db_insert") as mock_db:
        mock_db.return_value = True
        logger = ResilientBehaviorLogger()
        result = logger.log(sample_log)
        assert result.status == "ok"
        mock_db.assert_called_once()


def test_logger_defers_to_redis_when_db_fails(sample_log):
    with patch("app.services.agent_log.resilient_logger.db_insert", return_value=False), \
         patch("app.services.agent_log.resilient_logger.redis_push") as mock_redis:
        mock_redis.return_value = True
        logger = ResilientBehaviorLogger()
        result = logger.log(sample_log)
        assert result.status == "deferred"
        mock_redis.assert_called_once()


def test_logger_defers_to_redis_when_db_raises(sample_log):
    """When db_insert raises, fail-open: defer to redis."""
    with patch("app.services.agent_log.resilient_logger.db_insert", side_effect=RuntimeError("db down")), \
         patch("app.services.agent_log.resilient_logger.redis_push", return_value=True) as mock_redis:
        logger = ResilientBehaviorLogger()
        result = logger.log(sample_log)
        assert result.status == "deferred"
        mock_redis.assert_called_once()


def test_logger_deferred_to_disk_when_both_fail(sample_log):
    with patch("app.services.agent_log.resilient_logger.db_insert", return_value=False), \
         patch("app.services.agent_log.resilient_logger.redis_push", return_value=False), \
         patch("app.services.agent_log.resilient_logger.disk_append") as mock_disk:
        mock_disk.return_value = True
        logger = ResilientBehaviorLogger()
        result = logger.log(sample_log)
        assert result.status == "deferred_disk"


def test_logger_rejects_when_all_three_layers_fail(sample_log):
    with patch("app.services.agent_log.resilient_logger.db_insert", return_value=False), \
         patch("app.services.agent_log.resilient_logger.redis_push", return_value=False), \
         patch("app.services.agent_log.resilient_logger.disk_append", return_value=False):
        logger = ResilientBehaviorLogger()
        result = logger.log(sample_log)
        assert result.status == "rejected"