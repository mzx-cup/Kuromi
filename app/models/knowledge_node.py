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
import logging
from datetime import datetime, timedelta

from sqlalchemy import Integer, Float, DateTime, JSON, String, Text, text
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.models.base import Base
from app.services.kb.source_ref import SourceRef

logger = logging.getLogger("starlearn.knowledge_node")

# In-memory counter for monotonic KB-CON-XXXX IDs.
# Initialised lazily from the DB at startup (init_counter_from_db)
# so service restarts don't collide with already-persisted rows.
_COUNTER = {"v": 0}
_COUNTER_INITIALIZED = {"done": False}


def make_node_id(subject: str, title: str, chunk_index: int = 0) -> str:
    """Stable monotonic ID per session, e.g. KB-CON-0001.

    NOTE: ``subject`` / ``title`` / ``chunk_index`` are accepted for
    forward-compatibility with hashed-id plans; today's ID is purely a
    monotonic counter that must be initialised from the DB at startup
    to avoid UNIQUE-constraint collisions on restart.
    """
    _COUNTER["v"] += 1
    return f"KB-CON-{_COUNTER['v']:04d}"


def init_counter_from_db(session_factory) -> int:
    """Initialise ``_COUNTER`` from the maximum persisted ``KB-CON-NNNN``.

    Call once at process startup (see ``main.py`` lifespan hook) so a
    freshly-started server does not regenerate IDs that already exist
    in the ``knowledge_node`` table.

    ``session_factory`` is any SQLAlchemy sessionmaker whose ``()``
    returns a ``Session`` (sync or async-context-manager-compatible).
    Idempotent: subsequent calls are no-ops.
    """
    if _COUNTER_INITIALIZED["done"]:
        return _COUNTER["v"]
    try:
        with session_factory() as session:
            row = session.execute(
                text(
                    "SELECT MAX(CAST(SUBSTR(id, 8) AS INTEGER)) "
                    "FROM knowledge_node WHERE id LIKE 'KB-CON-%'"
                )
            ).fetchone()
            max_v = row[0] if row and row[0] is not None else 0
            _COUNTER["v"] = int(max_v)
            _COUNTER_INITIALIZED["done"] = True
            logger.info(f"KB _COUNTER initialized from DB: max_v={_COUNTER['v']}")
            return _COUNTER["v"]
    except Exception as exc:
        logger.warning(f"Failed to init KB _COUNTER from DB: {exc}")
        return _COUNTER["v"]


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
