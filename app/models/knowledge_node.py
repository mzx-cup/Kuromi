"""KnowledgeNode SQLAlchemy model — L1 content layer backbone.

A KnowledgeNode is one chunk of sourceable content (a paragraph, an
example, a code snippet). Each node must carry a SourceRef; the KB
ingestion pipeline rejects nodes whose source is missing or invalid
(app/services/kb/ingestion.py wires this in S1.3).

Note on file location: the plan calls for ``app/models/knowledge.py``,
but that file already holds the SM2 ``KnowledgeNode`` model (M6) used
by ``app/repositories/orm/knowledge.py`` and ``tests/repositories/
test_knowledge_repo.py``. Adding a second class named ``KnowledgeNode``
to the same module would shadow the SM2 export and break those tests.
The L1 content model therefore lives here under the same class name;
callers should import it directly (``from app.models.knowledge_node
import KnowledgeNode, make_node_id``) rather than from
``app.models.knowledge`` to avoid the SM2 collision.
"""
from datetime import datetime, timedelta

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Float, DateTime, JSON, Text

from app.models.base import Base
from app.services.kb.source_ref import SourceRef


_COUNTER = {"v": 0}


def make_node_id(subject: str, title: str, chunk_index: int = 0) -> str:
    """Stable monotonic ID per session, e.g. KB-CON-0001."""
    _COUNTER["v"] += 1
    return f"KB-CON-{_COUNTER['v']:04d}"


class KnowledgeNode(Base):
    __tablename__ = "knowledge_node"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    subject: Mapped[str] = mapped_column(String, index=True)
    title: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(Text)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    source_type: Mapped[str] = mapped_column(String)
    source_reference: Mapped[str] = mapped_column(String)
    source_confidence: Mapped[float] = mapped_column(Float, default=1.0)
    verifier_id: Mapped[str | None] = mapped_column(String, nullable=True)
    related_nodes: Mapped[list] = mapped_column(JSON, default=list)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    version: Mapped[int] = mapped_column(Integer, default=1)
    last_verified_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ttl_days: Mapped[int] = mapped_column(Integer, default=180)
    stale: Mapped[bool] = mapped_column(default=False)

    def source(self) -> SourceRef:
        return SourceRef(
            type=self.source_type,
            reference=self.source_reference,
            confidence=self.source_confidence,
            verifier_id=self.verifier_id,
        )

    def is_expired(self, now: datetime | None = None) -> bool:
        n = now or datetime.utcnow()
        return n > self.last_verified_at + timedelta(days=self.ttl_days)