"""CitationRetriever returns CitationHit dataclasses with must_cite=True."""
from app.services.kb.citation_retriever import CitationRetriever, CitationHit
from app.services.kb.qdrant_client import QdrantClientSingleton  # production vs injected; FakeVS used below


def test_citation_retriever_returns_tuples_with_must_cite_flag():
    class FakeVS:
        def similarity_search_with_score(self, q, k=5):
            return [
                ({"id": "KB-CON-0001", "title": "pythag", "content": "a²+b²=c²"}, 0.92),
                ({"id": "KB-CON-0002", "title": "trig", "content": "sin"}, 0.85),
            ]

    r = CitationRetriever(vector_store=FakeVS())
    hits = r.retrieve("勾股", top_k=2)
    assert len(hits) == 2
    assert all(isinstance(h, CitationHit) for h in hits)
    assert all(h.must_cite is True for h in hits)
    assert hits[0].node_id == "KB-CON-0001"


def test_citation_retriever_handles_document_shaped_hits():
    from app.services.kb.citation_retriever import CitationRetriever, CitationHit
    from langchain_core.documents import Document

    class FakeVS:
        def similarity_search_with_score(self, q, k=5):
            return [
                (Document(page_content="a²+b²=c²", metadata={"id": "KB-CON-0001", "title": "pythag"}), 0.91),
                (Document(page_content="sin²+cos²=1", metadata={"id": "KB-CON-0002", "title": "trig"}), 0.83),
            ]

    r = CitationRetriever(vector_store=FakeVS())
    hits = r.retrieve("勾股", top_k=2)
    assert len(hits) == 2
    assert all(isinstance(h, CitationHit) for h in hits)
    assert hits[0].node_id == "KB-CON-0001"
    assert hits[0].title == "pythag"
    assert "a²+b²=c²" in hits[0].content
    assert hits[0].score == 0.91
    assert hits[0].must_cite is True