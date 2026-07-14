"""AntiHallucinationOutputParser core: 6 acceptance cases."""
import pytest
from app.services.llm.anti_hallucination_parser import (
    AntiHallucinationOutputParser,
    ValidatedResponse,
)
from app.services.llm.retry_strategy import parse_with_retry
from langchain_core.exceptions import OutputParserException


@pytest.fixture
def parser():
    return AntiHallucinationOutputParser(
        valid_node_ids={"KB-CON-0001", "KB-CON-0002"},
        retry_count=0,
    )


def test_all_claims_have_valid_citations(parser):
    text = "勾股定理 [KB-CON-0001] 是 a²+b²=c²。同样适用于直角三角形 [KB-CON-0001]。"
    out = parser.parse(text)
    assert not out.blocked
    assert len(out.citations) >= 2


def test_unbacked_claim_triggers_retry_then_block(parser):
    parser.retry_count = 1
    text = "勾股定理是 a²+b²=c²。它由商高发现。"
    out = parser.parse(text)
    assert out.blocked
    assert out.block_reason == "unbacked_claims"
    assert "核实" in out.text


def test_invalid_citation_id_blocks_immediately(parser):
    text = "勾股定理 [KB-CON-9999] 重要。"
    out = parser.parse(text)
    assert out.blocked
    assert out.block_reason == "invalid_citation_id"


def test_partial_unbacked_with_retry_succeeds(parser):
    text = "勾股定理 [KB-CON-0001] 是 a²+b²=c²。第二句无引用。"
    with pytest.raises(OutputParserException):
        parser.parse(text)


def test_risk_score_combines_unbacked_and_invalid(parser):
    text = "[KB-CON-9999] 重要。"
    out = parser.parse(text)
    assert out.risk == 1.0


def test_empty_text_is_blocked(parser):
    out = parser.parse("")
    assert out.blocked
    assert out.block_reason == "empty"


def test_parse_with_retry_succeeds_on_second_attempt(monkeypatch):
    """retry_strategy: first OutputParserException → retry → success."""
    parser = AntiHallucinationOutputParser(
        valid_node_ids={"KB-CON-0001"}, retry_count=0
    )
    monkeypatch.setattr(parser, "retry_count", 0, raising=False)

    def fake_llm_call(_prompt: str) -> str:
        return "勾股定理 [KB-CON-0001] 是 a²+b²=c²。"

    out = parse_with_retry(parser, "勾股定理是 a²+b²=c²。", fake_llm_call)
    assert out.retry_succeeded is True
    assert not out.blocked