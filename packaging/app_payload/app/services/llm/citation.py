"""Citation extraction + position validation."""
import re
from dataclasses import dataclass
from typing import List


_CITE_RE = re.compile(r"\[KB:([A-Z0-9\-]+)\]")


@dataclass
class Citation:
    kb_node_id: str
    claim: str
    position: int
    confidence: float = 1.0


# Imported after Citation is defined to avoid a circular import
# (citation_position imports Citation from this module).
from app.services.llm.citation_position import CitationPositionChecker  # noqa: E402


def extract_citations(text: str) -> List[Citation]:
    citations = []
    for m in _CITE_RE.finditer(text):
        citations.append(Citation(
            kb_node_id=m.group(1),
            claim="",
            position=m.start(),
            confidence=1.0,
        ))
    return citations


def extract_claims(text: str) -> List[str]:
    """Split text into sentences (Chinese + English punctuation)."""
    parts = re.split(r"(?<=[。！？!?\.])\s*", text.strip())
    return [p.strip() for p in parts if p.strip()]


def has_citation(claim: str, citations: List["Citation"], checker=None) -> bool:
    """Position-aware check via CitationPositionChecker.

    A claim is backed when it carries at least one in-line KB marker that sits
    within the citation window of the claim. Citations are re-based to the
    claim's own coordinate space (markers physically present in the claim) so
    the check is correct regardless of whether the caller passes citations with
    positions relative to the full response or the claim. The ``citations``
    argument is retained for API compatibility with existing callers.
    """
    if not claim:
        return False
    if checker is None:
        checker = CitationPositionChecker()
    # Only markers physically present in this claim can back it; this both
    # matches the legacy marker-in-claim semantics and guards against
    # "cite A 配 claim B" tampering at the aggregate (checker) level.
    local_citations = extract_citations(claim)
    if not local_citations:
        return False
    _, mis = checker.check([claim], local_citations)
    return not mis


def compute_risk(unbacked_ratio: float, invalid_ratio: float) -> float:
    # Unbacked (no grounding) is weighted higher than invalid (partially grounded
    # but referencing a non-existent node) because unbacked is a worse failure mode.
    return round(unbacked_ratio * 0.6 + invalid_ratio * 0.4, 2)