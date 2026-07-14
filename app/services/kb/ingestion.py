"""Document → KnowledgeNode pipeline. SourceRef is mandatory."""
from app.models.knowledge_node import KnowledgeNode, make_node_id
from app.services.kb.source_ref import SourceRef
from datetime import datetime


class IngestionRejected(ValueError):
    pass


def _persist_to_db(node: KnowledgeNode) -> bool:
    """ORM insert — wired to the L1 OrmKnowledgeRepository in S1.4.

    The repository builds its own sync sessionmaker from ``DATABASE_URL``
    at module import, so this call site stays a one-liner.
    """
    from app.repositories.orm.knowledge_node import OrmKnowledgeRepository
    OrmKnowledgeRepository().insert(node)
    return True


def _persist_to_qdrant(node: KnowledgeNode) -> bool:
    """Qdrant upsert — wired in S2."""
    raise NotImplementedError


def ingest_node(subject: str, title: str, content: str, source: dict | None, tags: list[str] | None = None, ttl_days: int = 180) -> str:
    if source is None:
        raise IngestionRejected("source must not be None")
    src = SourceRef(type=source["type"], reference=source["reference"], confidence=source["confidence"], verifier_id=source.get("verifier_id"))
    src.is_valid()  # raises ValueError on bad input

    nid = make_node_id(subject, title)
    node = KnowledgeNode(
        id=nid, subject=subject, title=title, content=content,
        source_type=src.type, source_reference=src.reference,
        source_confidence=src.confidence, verifier_id=src.verifier_id,
        tags=tags or [], ttl_days=ttl_days, version=1,
        last_verified_at=datetime.utcnow(),
    )
    _persist_to_db(node)
    _persist_to_qdrant(node)
    return nid
