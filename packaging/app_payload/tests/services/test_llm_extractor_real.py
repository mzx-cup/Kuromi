import json
import pytest
from unittest.mock import MagicMock

from app.services.memory.llm_extractor import extract_pattern


def _fake_llm(reply_json: str):
    llm = MagicMock()
    llm._stream.return_value = iter([MagicMock(message=MagicMock(content=reply_json))])
    return llm


@pytest.fixture
def cluster():
    return [
        {"id": f"e{i}", "summary": f"用户做了第 {i} 道题"}
        for i in range(3)
    ]


def test_real_extract_calls_llm(cluster):
    """真接 LLM 路径：LLM 返回 JSON"""
    reply = json.dumps({
        "statement": "用户高频练习同类题型",
        "confidence": 0.75,
        "evidence_ids": ["e0", "e1", "e2"],
    })
    out = extract_pattern(user_id="u-1", cluster=cluster, llm=_fake_llm(reply))
    assert out["statement"] == "用户高频练习同类题型"
    assert out["confidence"] == 0.75
    assert set(out["evidence_ids"]) == {"e0", "e1", "e2"}


def test_json_parse_failure_uses_fallback(cluster):
    """LLM 返回非 JSON → fallback dict"""
    llm = MagicMock()
    llm._stream.return_value = iter([
        MagicMock(message=MagicMock(content="这不是 JSON")),
    ])
    out = extract_pattern(user_id="u-1", cluster=cluster, llm=llm)
    assert out["statement"] == "无事件"
    assert out["confidence"] == 0.0


def test_llm_timeout_returns_fallback(cluster):
    """LLM 超时 → fallback（不抛异常）"""
    import time
    def slow(*_args, **_kw):
        time.sleep(35)  # > 30s timeout
        yield MagicMock(message=MagicMock(content="{}"))
    llm = MagicMock()
    llm._stream.side_effect = lambda msgs: slow()
    out = extract_pattern(user_id="u-1", cluster=cluster, llm=llm)
    assert out["statement"] == "无事件"


def test_empty_cluster_returns_fallback():
    out = extract_pattern(user_id="u-1", cluster=[], llm=MagicMock())
    assert out["statement"] == "无事件"
    assert out["confidence"] == 0.0


def test_missing_confidence_field_defaults_low(cluster):
    """JSON 缺 confidence 字段 → 默认 0.0（保守）"""
    reply = json.dumps({"statement": "X", "evidence_ids": ["e0"]})
    out = extract_pattern(user_id="u-1", cluster=cluster, llm=_fake_llm(reply))
    assert out["confidence"] == 0.0
