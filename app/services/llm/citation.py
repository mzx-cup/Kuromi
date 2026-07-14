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


def has_citation(claim: str, citations: List[Citation]) -> bool:
    """Best-effort proximity check: citation marker appears anywhere in the claim."""
    for c in citations:
        marker = f"[KB:{c.kb_node_id}]"
        if marker in claim:
            return True
    return False


def compute_risk(unbacked_ratio: float, invalid_ratio: float) -> float:
    return round(unbacked_ratio * 0.6 + invalid_ratio * 0.4, 2)