"""KBCallbackHandler: persist ValidatedResponse into AgentBehaviorLog via 3-layer logger."""
from unittest.mock import patch
from app.services.callbacks.kb_callback_handler import KBCallbackHandler
from app.models.agent_behavior_log import AgentBehaviorLog


def test_callback_handler_logs_validated_response():
    """on_validated_response builds AgentBehaviorLog with risk/block fields and calls logger.log once."""
    handler = KBCallbackHandler(agent_id="SocraticAgent", user_id="u1")
    with patch("app.services.callbacks.kb_callback_handler.ResilientBehaviorLogger") as MockL:
        MockL.return_value.log.return_value.status = "ok"
        handler.on_validated_response(
            output_text="hello [KB:KB-CON-0001]",
            citations=[{"kb_node_id": "KB-CON-0001", "claim": "x"}],
            risk=0.1,
            blocked=False,
            block_reason=None,
        )
        MockL.return_value.log.assert_called_once()
        entry = MockL.return_value.log.call_args[0][0]
        assert isinstance(entry, AgentBehaviorLog)
        assert entry.agent_id == "SocraticAgent"
        assert entry.user_id == "u1"
        assert entry.hallucination_risk_score == 0.1
        assert entry.blocked is False
        assert entry.block_reason is None
        assert entry.citations == [{"kb_node_id": "KB-CON-0001", "claim": "x"}]


def test_callback_handler_persists_blocked_response():
    """on_validated_response with blocked=True stores block_reason and risk=1.0."""
    handler = KBCallbackHandler(agent_id="SocraticAgent", user_id="u1")
    with patch("app.services.callbacks.kb_callback_handler.ResilientBehaviorLogger") as MockL:
        MockL.return_value.log.return_value.status = "ok"
        handler.on_validated_response(
            output_text="我需要核实一下再回答。",
            citations=[],
            risk=1.0,
            blocked=True,
            block_reason="unbacked_claims",
        )
        entry = MockL.return_value.log.call_args[0][0]
        assert entry.blocked is True
        assert entry.block_reason == "unbacked_claims"
        assert entry.hallucination_risk_score == 1.0


def test_callback_handler_handles_missing_user_id():
    """user_id=None must not crash; defaults to empty string in the log entry."""
    handler = KBCallbackHandler(agent_id="SocraticAgent", user_id=None)
    with patch("app.services.callbacks.kb_callback_handler.ResilientBehaviorLogger") as MockL:
        MockL.return_value.log.return_value.status = "ok"
        handler.on_validated_response(output_text="x")
        entry = MockL.return_value.log.call_args[0][0]
        assert entry.user_id == ""
        assert entry.blocked is False  # defaults
        assert entry.hallucination_risk_score == 0.0  # defaults


def test_callback_handler_accepts_none_citations():
    """citations=None (not just []) must propagate as empty list to the log entry."""
    handler = KBCallbackHandler(agent_id="SocraticAgent", user_id="u1")
    with patch("app.services.callbacks.kb_callback_handler.ResilientBehaviorLogger") as MockL:
        MockL.return_value.log.return_value.status = "ok"
        handler.on_validated_response(output_text="x", citations=None)
        entry = MockL.return_value.log.call_args[0][0]
        assert entry.citations == []


def test_callback_handler_lazy_logger_init():
    """_logger is None before first on_validated_response call; mock patch is honored.

    This guards against a regression to eager init in __init__, which would
    silently bypass the mock and create a real ResilientBehaviorLogger.
    """
    handler = KBCallbackHandler(agent_id="SocraticAgent", user_id="u1")
    assert handler._logger is None
    with patch("app.services.callbacks.kb_callback_handler.ResilientBehaviorLogger") as MockL:
        MockL.return_value.log.return_value.status = "ok"
        handler.on_validated_response(output_text="x")
        MockL.return_value.log.assert_called_once()
