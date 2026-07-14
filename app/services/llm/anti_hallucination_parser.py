"""Anti-Hallucination OutputParser — core innovation 1.

Every claim in an LLM response must carry a `[KB:node_id]` citation that
resolves to a valid KB id. If not, retry once. If still not, block.
"""
from dataclasses import dataclass, field
from typing import List, Set
from langchain_core.output_parsers import BaseOutputParser
from langchain_core.exceptions import OutputParserException
from app.services.llm.citation import (
    Citation,
    compute_risk,
    extract_citations,
    extract_claims,
    has_citation,
)


@dataclass
class ValidatedResponse:
    text: str
    citations: List[Citation] = field(default_factory=list)
    risk: float = 0.0
    blocked: bool = False
    block_reason: str | None = None
    retry_succeeded: bool = False


class AntiHallucinationOutputParser(BaseOutputParser[ValidatedResponse]):
    model_config = {"arbitrary_types_allowed": True}

    valid_node_ids: Set[str]
    retry_count: int = 0
    max_retry: int = 1

    def parse(self, text: str) -> ValidatedResponse:
        text = (text or "").strip()
        if not text:
            return ValidatedResponse(
                text="我需要核实一下再回答。",
                blocked=True,
                block_reason="empty",
                risk=1.0,
            )

        citations = extract_citations(text)
        claims = extract_claims(text)

        invalid_ids = [
            c.kb_node_id for c in citations
            if c.kb_node_id not in self.valid_node_ids
        ]
        unbacked = [cl for cl in claims if not has_citation(cl, citations)]
        unbacked_ratio = len(unbacked) / max(1, len(claims))
        invalid_ratio = (
            len(invalid_ids) / max(1, len(citations)) if citations else 0.0
        )
        risk = compute_risk(unbacked_ratio, invalid_ratio)

        if invalid_ids:
            return ValidatedResponse(
                text="系统错误，请稍后重试。",
                blocked=True,
                block_reason="invalid_citation_id",
                risk=1.0,
                citations=citations,
            )

        if unbacked:
            if self.retry_count < self.max_retry:
                raise OutputParserException(
                    "必须为每条 claim 提供 [KB:xxx] 引用"
                )
            return ValidatedResponse(
                text="我需要核实一下再回答。",
                blocked=True,
                block_reason="unbacked_claims",
                risk=risk,
            )

        return ValidatedResponse(text=text, citations=citations, risk=risk)

    def parse_result(self, result, *, partial: bool = False) -> ValidatedResponse:
        return self.parse(result[0].text)