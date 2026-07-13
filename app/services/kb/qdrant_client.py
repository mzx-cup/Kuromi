"""Qdrant singleton + master/replica failover."""
import os
from typing import Optional
from qdrant_client import QdrantClient


class QdrantClientSingleton:
    _master: Optional[QdrantClient] = None
    _replica: Optional[QdrantClient] = None

    @classmethod
    def _master_client(cls) -> QdrantClient:
        if cls._master is None:
            cls._master = QdrantClient(
                host=os.getenv("QDRANT_MASTER_HOST", "localhost"),
                port=int(os.getenv("QDRANT_MASTER_PORT", "6333")),
                timeout=2.0,
            )
        return cls._master

    @classmethod
    def _replica_client(cls) -> QdrantClient:
        if cls._replica is None:
            cls._replica = QdrantClient(
                host=os.getenv("QDRANT_REPLICA_HOST", "localhost"),
                port=int(os.getenv("QDRANT_REPLICA_PORT", "6334")),
                timeout=2.0,
            )
        return cls._replica

    @classmethod
    def get(cls) -> QdrantClient:
        master = cls._master_client()
        try:
            if master.get_collections() is not None:
                return master
        except Exception:
            return cls._replica_client()
        return master

    @classmethod
    def health(cls) -> dict:
        try:
            cls._master_client().get_collections()
            return {"status": "ok", "node": "master"}
        except Exception:
            try:
                cls._replica_client().get_collections()
                return {"status": "degraded", "node": "replica"}
            except Exception:
                return {"status": "down", "node": "none"}
