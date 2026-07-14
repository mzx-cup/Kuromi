"""Retry-once-or-reject wrapper around AntiHallucinationOutputParser.

The parser signals "please retry" by raising OutputParserException when
unbacked claims remain and retry_count < max_retry. After one retry, the
parser is invoked again with retry_count = 1, which routes into the
blocking branch.
"""
from typing import Callable
from langchain_core.exceptions import OutputParserException
from app.services.llm.anti_hallucination_parser import (
    AntiHallucinationOutputParser,
    ValidatedResponse,
)


def parse_with_retry(
    parser: AntiHallucinationOutputParser,
    raw_text: str,
    llm_call: Callable[[str], str],
) -> ValidatedResponse:
    parser.retry_count = 0
    try:
        return parser.parse(raw_text)
    except OutputParserException:
        parser.retry_count = 1
        retried = llm_call(
            raw_text + "\n\n（必须为每条 claim 提供 [KB:node_id] 引用。）"
        )
        out = parser.parse(retried)
        out.retry_succeeded = True
        return out