"""Unit tests for the red-team classifier and pass-criteria evaluation."""
from tests.redteam.run import classify, evaluate, Outcome


def test_classify_returns_blocked_when_parser_blocks():
    from app.services.llm.anti_hallucination_parser import ValidatedResponse
    out = ValidatedResponse(text="我需要核实一下再回答。", blocked=True, block_reason="unbacked_claims")
    assert classify(out) == "blocked"


def test_classify_returns_passed_when_citations_present():
    from app.services.llm.anti_hallucination_parser import ValidatedResponse
    from app.services.llm.citation import Citation
    out = ValidatedResponse(
        text="x [KB:KB-CON-0001]",
        citations=[Citation(kb_node_id="KB-CON-0001", claim="x", position=0)],
    )
    assert classify(out) == "passed"


def test_classify_returns_safe_fallback_when_no_citations_and_not_blocked():
    """Edge case: not blocked and no citations (e.g., LLM produced empty response)."""
    from app.services.llm.anti_hallucination_parser import ValidatedResponse
    out = ValidatedResponse(text="")  # not blocked but no citations either
    assert classify(out) == "safe_fallback"


def test_evaluate_counts_blocked_as_safe_fallback():
    """All-blocked category passes the safe_fallback=1.0 criterion."""
    outcomes = [
        Outcome(category="A", prompt="p1", classification="blocked", blocked=True,
                block_reason="x", citations_count=0, retry_succeeded=False, risk=1.0),
        Outcome(category="A", prompt="p2", classification="blocked", blocked=True,
                block_reason="x", citations_count=0, retry_succeeded=False, risk=1.0),
    ]
    result = evaluate(outcomes)
    assert result["by_category"]["A"]["pass"] is True
    assert result["overall_pass"] is True


def test_evaluate_handles_passed_outcome():
    """Categories expecting passed >= 1.0 should fail when nothing passes."""
    outcomes = [
        Outcome(category="H", prompt="p1", classification="blocked", blocked=True,
                block_reason="x", citations_count=0, retry_succeeded=False, risk=1.0),
        Outcome(category="H", prompt="p2", classification="passed", blocked=False,
                block_reason=None, citations_count=1, retry_succeeded=False, risk=0.0),
    ]
    # Use a category that requires both safe_fallback and passed.
    from tests.redteam.run import PASS_CRITERIA
    # Manually inject a test criterion to verify mixed logic.
    PASS_CRITERIA["TEST_MIX"] = {"safe_fallback": 0.5, "passed": 0.5}
    outcomes[0] = Outcome(category="TEST_MIX", prompt="p1", classification="blocked",
                          blocked=True, block_reason="x", citations_count=0,
                          retry_succeeded=False, risk=1.0)
    outcomes[1] = Outcome(category="TEST_MIX", prompt="p2", classification="passed",
                          blocked=False, block_reason=None, citations_count=1,
                          retry_succeeded=False, risk=0.0)
    result = evaluate(outcomes)
    assert result["by_category"]["TEST_MIX"]["pass"] is True
