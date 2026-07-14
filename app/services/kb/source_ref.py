"""SourceRef value object — provenance anchor for anti-hallucination.

Every KnowledgeNode must carry a SourceRef that points to a verifiable
source (textbook ISBN / codebase commit / agent name / manual editor /
external parsed doc). The anti-hallucination guard in S3 will refuse any
LLM output that cites a KB node whose SourceRef is missing or invalid.
"""
from dataclasses import dataclass
from typing import Literal


_ALLOWED_TYPES = frozenset({"textbook", "codebase", "agent_output", "manual", "external_parsed"})


def _validate(type_, reference, confidence) -> None:
    """Shared validation. Raises ``ValueError`` on any bad field."""
    if type_ is None:
        raise ValueError("SourceRef.type must not be None")
    if not isinstance(type_, str):
        raise ValueError(f"SourceRef.type must be a string, got {type(type_).__name__}")
    if type_ not in _ALLOWED_TYPES:
        raise ValueError(f"SourceRef.type must be one of {sorted(_ALLOWED_TYPES)}, got {type_!r}")
    if not reference or not isinstance(reference, str):
        raise ValueError("SourceRef.reference must not be empty")
    if not isinstance(confidence, (int, float)):
        raise ValueError(f"SourceRef.confidence must be a number, got {type(confidence).__name__}")
    if not (0.0 <= float(confidence) <= 1.0):
        raise ValueError(f"SourceRef.confidence must be between 0 and 1, got {confidence}")
    return None


@dataclass(frozen=True)
class SourceRef:
    type: Literal["textbook", "codebase", "agent_output", "manual", "external_parsed"]
    reference: str
    confidence: float
    verifier_id: str | None

    def __post_init__(self) -> None:
        _validate(self.type, self.reference, self.confidence)

    def is_valid(self) -> bool:
        # __post_init__ already enforced; this method is the public
        # re-check used by ingestion pipelines that want an explicit
        # boolean pass without try/except.
        _validate(self.type, self.reference, self.confidence)
        return True