"""KB API endpoints — POST /api/kb/ingest (slice-s1).

Wire the L1 ingestion pipeline behind a thin HTTP wrapper so the
frontend (and any test harness) can hand a SourceRef-bearing payload
to ``app.services.kb.ingestion.ingest_node``.

Validation layering:
  * pydantic enforces types / bounds (returns 422 on bad input).
  * ``ingest_node`` enforces business rules (returns 400 / raises
    ``IngestionRejected`` / ``ValueError`` for source-shape issues).
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.kb.ingestion import IngestionRejected, ingest_node

router = APIRouter(prefix="/api/kb", tags=["kb"])


class SourceRefIn(BaseModel):
    type: str = Field(..., pattern="^(textbook|codebase|agent_output|manual|external_parsed)$")
    reference: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0, le=1)
    verifier_id: str | None = None


class IngestIn(BaseModel):
    subject: str
    title: str
    content: str
    source: SourceRefIn
    tags: list[str] = Field(default_factory=list)
    ttl_days: int = 180


class IngestOut(BaseModel):
    id: str


@router.post("/ingest", response_model=IngestOut)
def ingest(payload: IngestIn):
    try:
        nid = ingest_node(
            subject=payload.subject,
            title=payload.title,
            content=payload.content,
            source=payload.source.model_dump(),
            tags=payload.tags,
            ttl_days=payload.ttl_days,
        )
        return IngestOut(id=nid)
    except IngestionRejected as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
