"""教研知识自动沉淀（M5.5 / #22）

教师编辑教学心得 → 提交审核 → admin 审核通过 → 进入私有 KB。

数据流：
  1. submit_for_review()  : 教师提交，状态=pending_review
  2. approve_review()     : admin 审核，状态=approved + 入私有 KB
  3. list_pending()       : admin 拉取所有待审核

存储：进程内 dict（M2 已用类似模式，生产应迁移到 DB）。
"""
from __future__ import annotations

import logging
import uuid

logger = logging.getLogger("starlearn.kb.deposition")


class KnowledgeDepositionService:
    """教研知识沉淀服务。"""

    def __init__(self) -> None:
        # review_id → review record
        self._reviews: dict[str, dict] = {}

    async def submit_for_review(
        self,
        teacher_id: str,
        content: str,
        knowledge_point: str,
    ) -> dict:
        """教师提交教学心得，等待审核。"""
        review_id = f"rv_{uuid.uuid4().hex[:8]}"
        self._reviews[review_id] = {
            "teacher_id": teacher_id,
            "content": content,
            "knowledge_point": knowledge_point,
            "status": "pending_review",
        }
        logger.info(f"KB deposition submitted: {review_id} (teacher={teacher_id})")
        return {"review_id": review_id, "status": "pending_review"}

    async def approve_review(
        self,
        review_id: str,
        approver: str,
    ) -> dict:
        """审核通过：进入私有 KB。"""
        review = self._reviews.get(review_id)
        if not review:
            return {"status": "not_found"}

        review["status"] = "approved"
        review["approver"] = approver
        review["entered_kb"] = True
        logger.info(
            f"KB deposition approved: {review_id} (approver={approver}, "
            f"topic={review['knowledge_point']})"
        )
        # 占位：实际写入私有 KB（app/services/kb/ingestion.py）
        return {"status": "approved", "entered_kb": True}

    async def list_pending(self) -> list[dict]:
        """返回所有待审核的 review（admin 视角）。"""
        return [
            {"review_id": rid, **record}
            for rid, record in self._reviews.items()
            if record.get("status") == "pending_review"
        ]