"""LLM-backed pattern extractor for episodic → semantic consolidation (S6.2).

This is the second step of Core Innovation 2: 记忆巩固 (Memory Consolidation).
After ``clustering.py`` groups similar episodic events into clusters, this
module asks an LLM to summarise each cluster into a single declarative
``statement`` (the candidate ``SemanticMemory``), together with a confidence
score and the list of episode ids that ground it. The downstream
``consolidator`` (S6.3) feeds this output into ``reinforce`` / ``weaken``.

The real implementation will call ``XunfeiChatModel`` with ``PROMPT`` and
parse the JSON reply. In S6.2 we ship a deterministic stub so the consolidator
and tests can be built and reviewed before live LLM wiring lands.
"""
from __future__ import annotations

PROMPT = """以下是用户 X 的 {n} 条学习事件。请提取 1 条 pattern，JSON 格式：
{{"statement": "<一句陈述>", "confidence": <0-1>, "evidence_ids": [...]}}
"""

PROMPT_VERSION = "v1"

# Validate the format string at import time so a placeholder typo surfaces
# here rather than in the consolidator (S6.3) or the live LLM call.
_ = PROMPT.format(n=1)


def extract_pattern(user_id: str, cluster: list[dict]) -> dict:
    """Extract one declarative pattern from a cluster of episodic events.

    Stub implementation (S6.2): does not call any LLM. Returns a fixed-shape
    response based on the cluster contents so the rest of the consolidator
    pipeline can be exercised deterministically. The real implementation
    will format ``PROMPT`` with ``len(cluster)`` and the event summaries,
    call ``XunfeiChatModel``, and parse the JSON reply.

    Args:
        user_id: Owner of the cluster. Currently unused by the stub (the
            real LLM call will inject it into the prompt for traceability).
        cluster: List of episodic event dicts. Each must have at least
            an ``id`` (str). May be empty.

    Returns:
        A dict with keys ``statement`` (str), ``confidence`` (float in
        ``[0.0, 1.0]``), and ``evidence_ids`` (list of the cluster's
        ids). On an empty cluster the confidence collapses to ``0.0`` and
        the statement is a graceful fallback string.
    """
    # 真实实现：调 XunfeiChatModel + parse JSON
    # 这里 stub 返回一个最小可用结果
    n = len(cluster)
    if n == 0:
        return {
            "statement": "无事件",
            "confidence": 0.0,
            "evidence_ids": [],
        }
    return {
        "statement": f"用户在 {n} 个事件中重复练习相关内容",
        "confidence": 0.7,
        "evidence_ids": [c["id"] for c in cluster],
    }