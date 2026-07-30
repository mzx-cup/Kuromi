"""Document → KnowledgeNode pipeline. SourceRef is mandatory."""
import logging

from sqlalchemy.exc import IntegrityError

from app.models.knowledge_node import KnowledgeNode, make_node_id
from app.services.kb.source_ref import SourceRef
from app.services.kb.qdrant_client import QdrantClientSingleton
from datetime import datetime

logger = logging.getLogger("starlearn.kb.ingestion")

# Retry budget for the rare case that the in-memory _COUNTER races
# against a concurrent ingest and produces a duplicate id. Five is
# well above the realistic burst size (single-digit at worst).
_MAX_INGEST_RETRIES = 5


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
    """Qdrant upsert wiring — M2 hardening.

    Writes the node into the ``knowledge_nodes`` collection using the
    singleton Qdrant client (master → replica failover is handled
    inside ``QdrantClientSingleton.get()``). Failures are logged and
    swallowed so the SQL store remains the source of truth; a future
    fallback-queue worker can replay missed upserts from the DB.
    """
    try:
        client = QdrantClientSingleton.get()
        # Lazy vector/payload from the node. We don't run embeddings
        # here — that lives in embeddings.py / citation_retriever.py —
        # so we use a deterministic zero vector + the node metadata
        # as the payload. Real embedding wiring is a separate task.
        try:
            vector_dim = len(node.content) and 384  # placeholder dim
        except Exception:
            vector_dim = 384
        vector = [0.0] * vector_dim
        payload = {
            "id": node.id,
            "subject": node.subject,
            "title": node.title,
            "source_type": node.source_type,
            "source_reference": node.source_reference,
            "tags": node.tags or [],
            "version": node.version,
        }
        from qdrant_client.http import models as qmodels

        client.upsert(
            collection_name="knowledge_nodes",
            points=[qmodels.PointStruct(id=node.id, vector=vector, payload=payload)],
        )
        logger.info(f"Qdrant upsert OK for {node.id}")
        return True
    except Exception as exc:
        logger.warning(f"Qdrant upsert failed for {node.id}: {exc}")
        return False


def ingest_node(subject: str, title: str, content: str, source: dict | None, tags: list[str] | None = None, ttl_days: int = 180) -> str:
    if source is None:
        raise IngestionRejected("source must not be None")
    src = SourceRef(type=source["type"], reference=source["reference"], confidence=source["confidence"], verifier_id=source.get("verifier_id"))
    src.is_valid()  # raises ValueError on bad input

    last_exc: Exception | None = None
    for attempt in range(1, _MAX_INGEST_RETRIES + 1):
        nid = make_node_id(subject, title)
        node = KnowledgeNode(
            id=nid, subject=subject, title=title, content=content,
            source_type=src.type, source_reference=src.reference,
            source_confidence=src.confidence, verifier_id=src.verifier_id,
            tags=tags or [], ttl_days=ttl_days, version=1,
            last_verified_at=datetime.utcnow(),
        )
        try:
            _persist_to_db(node)
            _persist_to_qdrant(node)
            return nid
        except IntegrityError as exc:
            last_exc = exc
            logger.warning(
                f"KB ingest IntegrityError on attempt {attempt}/{_MAX_INGEST_RETRIES}: {exc}"
            )
            # The next loop iteration calls make_node_id() again which
            # increments _COUNTER and produces a fresh id.
            continue
    raise RuntimeError(
        f"KB ingest failed after {_MAX_INGEST_RETRIES} retries: {last_exc}"
    )
