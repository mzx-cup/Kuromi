"""Citation position checker — G-class red team hardening (slice-A1).

Each claim must have ALL its cited KB ids appearing within ±window chars
of that claim's span. Catches "cite A 配 claim B" tampering.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # avoid circular import; Citation only used in annotations
    from app.services.llm.citation import Citation


@dataclass
class CitationPositionChecker:
    window: int = 80

    def check(
        self,
        claims: list[str],
        citations: list[Citation],
    ) -> tuple[int, list[str]]:
        """Return (unbacked_count, mispositioned_kb_ids).

        - unbacked_count: number of claims whose window has no citation.
        - mispositioned_kb_ids: KB ids that appear in some citation but
          not within the window of any claim (often a tampering signal).
        Short claims (<10 chars) are skipped — not counted as claims.
        """
        if not claims:
            return 0, []
        if not citations:
            # all empty claims counted as unbacked; skip short ones
            return sum(1 for c in claims if len(c) >= 10), []

        covered_claim_idx: set[int] = set()
        mispositioned: set[str] = set()

        # Pre-compute claim spans in absolute char positions over the
        # joined text. Each claim's [start, end) is its slice.
        offsets: list[tuple[int, int]] = []
        cursor = 0
        joined = ""
        for c in claims:
            joined += c
            offsets.append((cursor, cursor + len(c)))
            cursor += len(c)

        for cit in citations:
            placed = False
            marker = f"[KB:{cit.kb_node_id}]"
            for idx, (start, end) in enumerate(offsets):
                if len(claims[idx]) < 10:
                    continue
                win_start = max(0, start - self.window)
                win_end = min(len(joined), end + self.window)
                # A citation only backs a claim when it sits within the
                # claim's window AND its marker literally appears in that
                # claim's text. The marker check is what distinguishes a
                # genuinely-grounded claim from "cite A 配 claim B" tampering
                # (a cite positionally inside a claim whose id is not there).
                if win_start <= cit.position < win_end and marker in claims[idx]:
                    covered_claim_idx.add(idx)
                    placed = True
                    # Don't break — same cite can cover multiple claims
            if not placed:
                mispositioned.add(cit.kb_node_id)

        unbacked = sum(
            1 for idx, c in enumerate(claims)
            if len(c) >= 10 and idx not in covered_claim_idx
        )
        return unbacked, sorted(mispositioned)
