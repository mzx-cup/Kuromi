"""Agent memory card loader (Core Innovation 3).

The loader packs up to ``total_max_tokens`` of cross-layer context
into a single markdown block that the agent prompt can prepend. When
fields collectively exceed the budget, lower-priority fields are
truncated (or dropped) first.

Token estimation: tiktoken is NOT installed in this repo (and we must
not add it as a dep). We use a conservative heuristic:
  - CJK characters count ~1 token each.
  - Latin text counts ~1 token per 4 characters (rounded up).
This biases toward over-estimation so we never overshoot the budget
even though the real LLM token count may be slightly lower.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# Priority order for inclusion when budget is tight. Items not in
# this list are appended after all listed items (priority index 99).
# Supervision first because it is the most actionable signal;
# episodic_last last because recent events are usually short.
PRIORITY_ORDER: list[str] = [
    "supervision_pending",
    "semantic_top3",
    "capability_recent",
    "episodic_last",
]


@dataclass
class CardField:
    """A single field to fetch and render in the agent memory card.

    ``value`` is populated by the loader's per-layer fetcher before
    ``pack`` is called (the fetcher wiring itself is S9). When
    ``value`` is empty, ``fallback`` is used so the prompt still has
    a placeholder for the slot.
    """

    key: str
    source_layer: str
    query: str
    max_tokens: int
    ttl_seconds: int
    fallback: Optional[str] = None
    value: str = ""


@dataclass
class CardSchema:
    """The full schema for an agent — its fields plus the card budget."""

    agent_id: str
    fields: list[CardField]
    total_max_tokens: int = 500


@dataclass
class LoadedCard:
    """The packed card ready to prepend to the agent prompt."""

    markdown: str
    token_count: int


class MemoryCardLoader:
    """Pack CardFields into a <= total_max_tokens markdown card.

    Priority order: supervision_pending > semantic_top3 >
    capability_recent > episodic_last. Lower-priority fields are
    truncated (or dropped) first when the budget is exhausted.
    """

    def __init__(self, total_max_tokens: int = 500) -> None:
        self._max = total_max_tokens

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Approximate token count without tiktoken.

        CJK chars: ~1 token per char; Latin: ~1 token per 4 chars.
        The repo estimates a conservative upper bound so we never
        overshoot the budget.
        """
        if not text:
            return 0
        cjk = sum(1 for c in text if "一" <= c <= "鿿")
        other = len(text) - cjk
        return cjk + (other + 3) // 4

    def _priority_index(self, key: str) -> int:
        try:
            return PRIORITY_ORDER.index(key)
        except ValueError:
            # Unknown keys are treated as lowest priority so they are
            # dropped/truncated before any of the canonical fields.
            return 99

    def pack(self, fields: list[CardField]) -> LoadedCard:
        """Pack fields into a LoadedCard respecting the token budget."""
        if not fields:
            return LoadedCard(markdown="", token_count=0)

        ordered = sorted(fields, key=lambda f: self._priority_index(f.key))
        parts: list[str] = []
        budget = 0
        for f in ordered:
            text = f.value if f.value else (f.fallback or "")
            if not text:
                # Nothing to render (no value and no fallback). Skip.
                continue
            tokens = self._estimate_tokens(text)
            if budget + tokens <= self._max:
                budget += tokens
                parts.append(f"### {f.key}\n{text}")
                continue

            remaining = self._max - budget
            if remaining <= 0:
                # No budget left; nothing more can be rendered.
                continue

            # If the field's per-field budget is larger than the
            # remaining budget, we cannot honour its minimum — drop
            # the field entirely (header included) so lower-priority
            # sections stay well-formed.
            if f.max_tokens > remaining:
                continue

            # Truncate the body so it fits within ``remaining`` tokens.
            # We slice by chars using a 3x safety factor (since each
            # Latin char uses ~1/4 token, 3 chars per token is a
            # conservative upper bound; CJK uses 1:1 so the same
            # factor is still safe).
            max_chars = max(1, remaining * 3)
            truncated = text[:max_chars].rstrip()
            if not truncated:
                truncated = "…"
            else:
                truncated = truncated + "…"
            budget += self._estimate_tokens(truncated)
            parts.append(f"### {f.key}\n{truncated}")

        return LoadedCard(markdown="\n\n".join(parts), token_count=budget)

    def load(self, *, agent_id: str, user_id: str) -> LoadedCard:
        """Load a memory card for an agent/user pair.

        P1: schema-loader only. S9 wires the per-field fetchers
        (episodic, capability, semantic, supervision).
        """
        import logging
        logging.getLogger(__name__).warning(
            "MemoryCardLoader.load() is a P1 stub for agent_id=%s user_id=%s; "
            "S9 will wire per-field fetchers.", agent_id, user_id,
        )
        return LoadedCard(markdown="", token_count=0)