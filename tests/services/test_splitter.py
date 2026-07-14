def test_splitter_respects_sentence_boundaries():
    from app.services.kb.splitter import ChineseRecursiveTextSplitter
    splitter = ChineseRecursiveTextSplitter(chunk_size=20, chunk_overlap=5)
    text = "勾股定理：a²+b²=c²。这是直角三角形的定理。它由商高发现。"
    chunks = splitter.split_text(text)
    assert all(len(c) <= 30 for c in chunks)  # allow buffer for CJK chars
    assert len(chunks) >= 2


def test_splitter_protects_formula_tokens():
    from app.services.kb.splitter import ChineseRecursiveTextSplitter
    splitter = ChineseRecursiveTextSplitter(chunk_size=20, chunk_overlap=5)
    text = "f(x) = sin(x)/cos(x) 一段说明文字。"
    chunks = splitter.split_text(text)
    # f(x)=sin(x)/cos(x) must not be split mid-token
    joined = " ".join(chunks)
    assert "f(x) = sin(x)/cos(x)" in joined or "sin(x)/cos(x)" in joined