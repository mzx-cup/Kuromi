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

import logging

from dataclasses import dataclass, field
from typing import Optional


_log = logging.getLogger(__name__)


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

    # When a field's fetch fails and we fall back to the placeholder
    # string, cache it only briefly so a recovering fetcher can be
    # re-tried soon instead of being pinned to the field's full TTL.
    _fallback_ttl_s: int = 30

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
        """Load a memory card for an agent/user pair (slice-A3).

        Flow:
          1. Resolve the schema for ``agent_id`` (e.g. SocraticAgent's
             schema from ``socratic_memory_card.socratic_schema``).
          2. Check the field-level cache (``CardCache``) for each field.
          3. Misses are fetched concurrently via ``FieldFetchers`` with
             a 250ms per-field timeout. Failures fall back to the
             schema's ``fallback`` string and record the field in
             ``partial_fields``.
          4. Pack the fetched values into a markdown ``LoadedCard``,
             truncating lower-priority fields if the schema's
             ``total_max_tokens`` budget is exceeded.
          5. Cache the per-field values for the schema's TTL.

        Production wiring of the four repos is B3's responsibility —
        tests pass a ``FieldFetchers(repos=...)`` directly via the
        optional ``fetchers`` arg or class-level override.
        """
        # Resolve schema.
        schema = self._resolve_schema(agent_id)

        # Gather from cache, fall through to fetcher on miss.
        cache = self._ensure_cache()
        fetcher = self._ensure_fetchers()

        values: dict[str, str] = {}
        partial: list[str] = []

        # First pass: serve cache hits and collect the fields we still
        # need to fetch.
        missing: list[CardField] = []
        for f in schema.fields:
            cache_key = f"{agent_id}:{user_id}:{f.key}"
            hit = cache.get(cache_key)
            if hit is not None:
                values[f.key] = hit
            else:
                missing.append(f)

        # Second pass: fetch the misses in one concurrent, timed call.
        # ``fetch_all`` enforces the 250ms per-field timeout via its
        # ThreadPoolExecutor, and records failed fields in
        # ``last_partial_fields`` for this call.
        if missing:
            fetched = fetcher.fetch_all(user_id)
            failed = set(getattr(fetcher, "last_partial_fields", []))
            for f in missing:
                cache_key = f"{agent_id}:{user_id}:{f.key}"
                raw = fetched.get(f.key, "")
                value = raw if raw else (f.fallback or "")
                values[f.key] = value
                if f.key in failed:
                    # Degraded field: track it and cache the fallback
                    # with a short TTL so a recovering fetcher is
                    # re-tried soon rather than pinned for the full TTL.
                    if f.key not in partial:
                        partial.append(f.key)
                    cache.set(cache_key, value, ttl_s=self._fallback_ttl_s)
                else:
                    cache.set(cache_key, value, ttl_s=f.ttl_seconds)

        # Build CardField list with values populated.
        card_fields = [
            CardField(
                key=f.key,
                source_layer=f.source_layer,
                query=f.query,
                max_tokens=f.max_tokens,
                ttl_seconds=f.ttl_seconds,
                fallback=f.fallback,
                value=values.get(f.key, "") or (f.fallback or ""),
            )
            for f in schema.fields
        ]
        packed = self.pack(card_fields)
        # Surface partial_fields so callers can log degraded cards.
        packed.partial_fields = partial
        if partial:
            _log.warning(
                "memory card for agent=%s user=%s is degraded; partial fields: %s",
                agent_id, user_id, partial,
            )
        return packed

    def _resolve_schema(self, agent_id: str) -> "CardSchema":
        if agent_id == "socratic":
            from app.services.agent.socratic_memory_card import socratic_schema
            return socratic_schema()
        if agent_id == "profiler":
            from app.services.agent.profile_memory_card import profile_schema
            return profile_schema()
        if agent_id == "echo":
            from app.services.agent.echo_memory_card import echo_schema
            return echo_schema()
        raise ValueError(f"unknown agent_id={agent_id!r}")

    _cache: Optional["object"] = None
    _fetchers: Optional["object"] = None

    def _ensure_cache(self):
        if self._cache is None:
            from app.services.agent.card_cache import CardCache
            self._cache = CardCache()
        return self._cache

    def _ensure_fetchers(self):
        if self._fetchers is None:
            from app.services.agent.field_fetchers import FieldFetchers
            # Default: empty repos; tests/production override ``_fetchers``.
            self._fetchers = FieldFetchers(repos={})
        return self._fetchers