import pytest
from app.services.llm.citation_position import CitationPositionChecker
from app.services.llm.citation import Citation


def test_citation_within_claim_passes():
    ck = CitationPositionChecker(window=80)
    claims = ["霍夫曼编码 [KB:HUFF] 是无损压缩 [KB:HUFF]。"]
    cits = [Citation(kb_node_id="HUFF", claim="", position=10)]
    unbacked, mis = ck.check(claims, cits)
    assert unbacked == 0
    assert mis == []


def test_citation_outside_window_unbacked():
    ck = CitationPositionChecker(window=10)
    claims = ["A" * 200 + "。" + "B" * 200 + "。"]
    cits = [Citation(kb_node_id="X", claim="", position=410)]
    unbacked, mis = ck.check(claims, cits)
    assert unbacked >= 1


def test_short_claim_skipped():
    ck = CitationPositionChecker(window=80)
    claims = ["是。"]
    unbacked, mis = ck.check(claims, [])
    assert unbacked == 0  # 非 claim，跳过


def test_window_does_not_exceed_text():
    ck = CitationPositionChecker(window=80)
    claims = ["短 [KB:X]。" * 5]
    cits = [Citation(kb_node_id="X", claim="", position=2)]
    unbacked, mis = ck.check(claims, cits)
    assert unbacked == 0


def test_multiple_citations_one_misplaced():
    ck = CitationPositionChecker(window=80)
    claims = ["A" * 100 + "。"
              + "B" * 100 + "。"
              + "C" * 100 + "[KB:Z]。" + " " * 300]
    cits = [Citation(kb_node_id="Z", claim="", position=900),
            Citation(kb_node_id="W", claim="", position=10)]
    unbacked, mis = ck.check(claims, cits)
    # W 在 claim 0 紧邻 → covered；Z 远离所有 → unbacked
    assert unbacked >= 1


def test_mispositioned_id_detected():
    """G 类核心：cite A 配错 claim B"""
    ck = CitationPositionChecker(window=30)
    claims = ["先说 A 是 X。" + " " * 200 + "后说 B 是 Y。"]
    # cite 在 claim A 字符串内，但 kb_node_id 引的是 Z（无关）
    cits = [Citation(kb_node_id="Z", claim="", position=5)]
    unbacked, mis = ck.check(claims, cits)
    assert "Z" in mis


def test_zero_claims_zero_unbacked():
    ck = CitationPositionChecker(window=80)
    unbacked, mis = ck.check([], [])
    assert unbacked == 0
    assert mis == []


def test_duplicate_id_one_coverage_sufficient():
    """同 ID 出现 2 次，1 处 claim 内 → pass"""
    ck = CitationPositionChecker(window=80)
    claims = ["这是 [KB:HUFF] 解释。"]
    cits = [Citation(kb_node_id="HUFF", claim="", position=2),
            Citation(kb_node_id="HUFF", claim="", position=40)]
    unbacked, mis = ck.check(claims, cits)
    assert unbacked == 0
