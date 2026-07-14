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
    """Qdrant upsert wiring — deferred to S2.3 follow-up.

    S2.3 ships the CitationRetriever over an injected vector store (see
    ``app/services/kb/citation_retriever.py``); the production wiring of
    ``_persist_to_qdrant`` to ``QdrantClientSingleton.get()`` (with an
    embedding function and a chosen collection / vector name) requires
    a dedicated task so the embedding source and collection schema can be
    decided explicitly. Until then, ingestion accepts the node in the
    SQL store but skips the vector upsert — callers must monkeypatch this
    stub in tests (see ``tests/services/test_kb_ingestion.py``).
    """
    raise NotImplementedError("Qdrant upsert — wired in S2.3 follow-up")


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
