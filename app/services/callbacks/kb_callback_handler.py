"""KBCallbackHandler: persist ValidatedResponse into AgentBehaviorLog.

Wires the AntiHallucination parser output (S3.1) into the 3-layer
ResilientBehaviorLogger (DB -> Redis -> disk). Used by S3.3 e2e code
which calls ``on_validated_response`` directly after
``AntiHallucinationOutputParser.parse_with_retry`` returns.

This handler inherits from langchain's ``BaseCallbackHandler`` for
framework interop, but the canonical entry point is the domain hook
``on_validated_response`` — the framework's ``on_llm_end`` signature
in langchain 0.3.x does not match our custom kwargs, so we expose
a separate method that callers invoke explicitly.
"""
from __future__ import annotations

from typing import Optional

from langchain_core.callbacks.base import BaseCallbackHandler

from app.models.agent_behavior_log import AgentBehaviorLog
from app.services.agent_log.resilient_logger import ResilientBehaviorLogger


class KBCallbackHandler(BaseCallbackHandler):
    """Persist each ValidatedResponse into AgentBehaviorLog."""

    def __init__(self, agent_id: str, user_id: Optional[str] = None) -> None:
        super().__init__()
        self.agent_id = agent_id
        self.user_id = user_id
        # Resolved lazily inside ``on_validated_response`` so tests can
        # patch ``app.services.callbacks.kb_callback_handler.ResilientBehaviorLogger``
        # before the logger is instantiated.
        self._logger: Optional[ResilientBehaviorLogger] = None

    def on_validated_response(
        self,
        *,
        output_text: str,
        citations: Optional[list] = None,
        risk: float = 0.0,
        blocked: bool = False,
        block_reason: Optional[str] = None,
    ) -> None:
        """Domain hook: persist a ValidatedResponse from the parser.

        S3.3 calls this directly after ``parse_with_retry`` returns.
        """
        entry = AgentBehaviorLog(
            agent_id=self.agent_id,
            user_id=self.user_id or "",
            action_type="llm_response",
            input_summary="",
            output_text=output_text,
            citations=citations or [],
            hallucination_risk_score=risk,
            blocked=blocked,
            block_reason=block_reason,
        )
        if self._logger is None:
            self._logger = ResilientBehaviorLogger()
        self._logger.log(entry)

    # Langchain 0.3.x framework hook — do not pass our custom kwargs to it.
    # This is invoked by the framework during streaming; we ignore it and
    # let on_validated_response be the canonical entry point.
    def on_llm_end(self, response, *, run_manager=None) -> None:  # noqa: D401
        pass