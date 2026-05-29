# -*- coding: utf-8 -*-
"""
LinkRecommender — 结构化学习链接生成器

从 RichContext 中的结构化数据确定性生成学习链接，
不再依赖 LLM 在 prompt 里"猜"链接和 `<links>` 标记。

设计原则：
  - 来源明确：每个链接都知道来自 RAG / Web Search / SM2 / Deadline
  - URL 可靠：由后端确定性生成，100% 有效
  - 前端兼容：输出格式与现有 SmartLinkRenderer (js/link-renderer.js) 完全一致
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from app.services.tutor_engine.action_ledger import ActionLedger
from app.services.tutor_engine.models import (
    Link,
    RichContext,
    TutorEvent,
)

logger = logging.getLogger("starlearn.tutor_engine")


# 可信外部域名列表（与 hallucination_guard.py 共享）
TRUSTED_DOMAINS = {
    "github.com", "docs.python.org", "developer.mozilla.org",
    "docs.oracle.com", "learn.microsoft.com", "leetcode.cn",
    "leetcode.com", "www.w3schools.com", "www.runoob.com",
    "docs.djangoproject.com", "flask.palletsprojects.com",
    "docs.sqlalchemy.org", "numpy.org", "pandas.pydata.org",
    "matplotlib.org", "scikit-learn.org", "pytorch.org",
    "tensorflow.org", "docs.opencv.org", "redis.io",
    "docs.docker.com", "kubernetes.io", "docs.github.com",
    "stackoverflow.com", "segmentfault.com", "juejin.cn",
    "zhihu.com", "csdn.net", "cnblogs.com",
    "www.bilibili.com", "www.youtube.com",
}


class LinkRecommender:
    """
    学习链接推荐器。

    使用示例:
        recommender = LinkRecommender()
        links = await recommender.recommend(event, rich_context, action_ledger)
    """

    def __init__(self, max_links: int = 5):
        self.max_links = max_links

    async def recommend(
        self,
        event: TutorEvent,
        rich: RichContext,
        ledger: Optional[ActionLedger] = None,
    ) -> list[Link]:
        """
        基于 RichContext 生成学习链接。

        返回排序后的链接列表（去重，最多 max_links 条）。
        """
        links: list[Link] = []
        student_id = event.student_id

        # 策略1: RAG 教材结果 -> 内部课程链接
        rag_links = self._from_rag(rich, student_id, ledger)
        links.extend(rag_links)

        # 策略2: Web Search -> 外部可信链接
        web_links = self._from_web_search(rich, student_id, ledger)
        links.extend(web_links)

        # 策略3: SM2 待复习项 -> 复习链接
        sm2_links = self._from_sm2(rich, student_id, ledger)
        links.extend(sm2_links)

        # 策略4: 截止日期 -> 任务直达链接
        deadline_links = self._from_deadlines(rich, student_id, ledger)
        links.extend(deadline_links)

        # 去重、排序、截断
        return self._deduplicate_and_rank(links)

    # ------------------------------------------------------------------
    # 各策略实现
    # ------------------------------------------------------------------

    def _from_rag(
        self,
        rich: RichContext,
        student_id: str,
        ledger: Optional[ActionLedger],
    ) -> list[Link]:
        """从 RAG 结果生成内部课程链接"""
        links = []
        course_id = rich.learning_state.current_course_id

        for rag in rich.rag_results[:3]:
            # 检查冷却期
            topic = rag.source_id
            if ledger and ledger.recently_exposed(student_id, topic, minutes=30):
                continue

            # 生成 URL
            if rag.node_id:
                url = f"/classroom.html?course={course_id or 'default'}&node={rag.node_id}"
            elif rag.chapter_id:
                url = f"/classroom.html?course={course_id or 'default'}&chapter={rag.chapter_id}"
            else:
                url = f"/classroom.html?course={course_id or 'default'}"

            if rag.deep_link:
                url = rag.deep_link

            links.append(Link(
                type="internal",
                title=rag.source_title or "相关知识点",
                url=url,
                description=rag.summary[:60] + "..." if len(rag.summary) > 60 else rag.summary,
                icon="📚",
                source="rag",
                relevance=rag.relevance_score,
                metadata={"topic": topic, "source_id": rag.source_id},
            ))

        return links

    def _from_web_search(
        self,
        rich: RichContext,
        student_id: str,
        ledger: Optional[ActionLedger],
    ) -> list[Link]:
        """从 Web Search 结果生成外部链接（过滤可信域名）"""
        links = []

        for web in rich.web_results[:3]:
            domain = web.domain or self._extract_domain(web.url)

            # 只推荐可信域名
            if not self._is_trusted_domain(domain):
                continue

            # 检查冷却期
            topic = f"web:{domain}:{web.title}"
            if ledger and ledger.recently_exposed(student_id, topic, minutes=60):
                continue

            links.append(Link(
                type="external",
                title=web.title or "相关资源",
                url=web.url,
                description=web.snippet[:80] + "..." if len(web.snippet) > 80 else web.snippet,
                icon="🌐",
                source="web_search",
                relevance=web.score,
                metadata={"topic": topic, "domain": domain},
            ))

        return links

    def _from_sm2(
        self,
        rich: RichContext,
        student_id: str,
        ledger: Optional[ActionLedger],
    ) -> list[Link]:
        """从 SM2 待复习项生成复习链接"""
        links = []

        for item in rich.sm2_due_items[:2]:
            topic = f"sm2:{item.knowledge_point}"
            if ledger and ledger.recently_exposed(student_id, topic, minutes=30):
                continue

            url = f"/review.html?item={item.id}"
            if item.course_id and item.node_id:
                url = f"/classroom.html?course={item.course_id}&node={item.node_id}&mode=review"

            links.append(Link(
                type="internal",
                title=f"复习：{item.knowledge_point}",
                url=url,
                description="根据你的记忆曲线，现在复习效果最好",
                icon="🔥",
                badge="今日待复习",
                source="sm2",
                metadata={"topic": topic, "item_id": item.id},
            ))

        return links

    def _from_deadlines(
        self,
        rich: RichContext,
        student_id: str,
        ledger: Optional[ActionLedger],
    ) -> list[Link]:
        """从截止日期生成任务直达链接"""
        links = []

        for dl in rich.upcoming_deadlines[:2]:
            topic = f"deadline:{dl.task_id}"
            if ledger and ledger.recently_exposed(student_id, topic, minutes=60):
                continue

            badge = "即将截止"
            if dl.days_left <= 1:
                badge = "明天截止"
            elif dl.days_left <= 3:
                badge = f"{dl.days_left}天后截止"

            url = f"/classroom.html?task={dl.task_id}"
            if dl.course_id:
                url = f"/classroom.html?course={dl.course_id}&task={dl.task_id}"

            links.append(Link(
                type="internal",
                title=f"任务：{dl.task_name}",
                url=url,
                description=f"还剩 {dl.days_left} 天截止",
                icon="⏰",
                badge=badge,
                source="deadline",
                metadata={"topic": topic, "task_id": dl.task_id, "days_left": dl.days_left},
            ))

        return links

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    @staticmethod
    def _is_trusted_domain(domain: str) -> bool:
        """检查域名是否在可信列表中"""
        if not domain:
            return False
        domain_lower = domain.lower()
        # 直接匹配或子域名匹配
        for trusted in TRUSTED_DOMAINS:
            if domain_lower == trusted or domain_lower.endswith("." + trusted):
                return True
        return False

    @staticmethod
    def _extract_domain(url: str) -> str:
        """从 URL 提取域名"""
        from urllib.parse import urlparse
        try:
            return urlparse(url).netloc
        except Exception:
            return ""

    def _deduplicate_and_rank(self, links: list[Link]) -> list[Link]:
        """去重、按相关度排序、截断"""
        seen_urls = set()
        unique = []

        for link in links:
            url = link.url
            if url in seen_urls:
                continue
            seen_urls.add(url)
            unique.append(link)

        # 按相关度降序
        unique.sort(key=lambda l: l.relevance, reverse=True)

        # 截断
        return unique[:self.max_links]
