"""Tests for KnowledgeDepositionService (M5.5)."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_deposition_requires_teacher_approval():
    """submit_for_review 必须返回 pending_review + review_id。"""
    from app.services.kb.deposition import KnowledgeDepositionService

    svc = KnowledgeDepositionService()
    result = await svc.submit_for_review(
        teacher_id="t_1",
        content="教学心得：勾股定理用面积法讲解更直观",
        knowledge_point="勾股定理",
    )
    assert result["status"] == "pending_review"
    assert "review_id" in result


@pytest.mark.asyncio
async def test_deposition_enters_private_kb_after_approval():
    """approve_review 必须返回 approved + entered_kb=True。"""
    from app.services.kb.deposition import KnowledgeDepositionService

    svc = KnowledgeDepositionService()
    # 先提交
    submit = await svc.submit_for_review(
        teacher_id="t_2",
        content="test",
        knowledge_point="代数",
    )
    review_id = submit["review_id"]
    # 再审核
    result = await svc.approve_review(review_id=review_id, approver="admin_1")
    assert result["status"] == "approved"
    assert result["entered_kb"] is True


@pytest.mark.asyncio
async def test_deposition_rejects_unknown_review_id():
    """未知的 review_id 必须返回 not_found。"""
    from app.services.kb.deposition import KnowledgeDepositionService

    svc = KnowledgeDepositionService()
    result = await svc.approve_review(review_id="rv_nonexistent", approver="admin")
    assert result["status"] == "not_found"


@pytest.mark.asyncio
async def test_deposition_lists_pending_reviews():
    """list_pending 必须返回所有待审核的 review_id。"""
    from app.services.kb.deposition import KnowledgeDepositionService

    svc = KnowledgeDepositionService()
    await svc.submit_for_review("t_1", "content1", "topic1")
    await svc.submit_for_review("t_2", "content2", "topic2")
    pending = await svc.list_pending()
    assert len(pending) == 2