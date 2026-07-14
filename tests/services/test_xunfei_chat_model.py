"""Tests for XunfeiChatModel BaseChatModel adapter."""
def test_xunfei_chat_model_calls_llm_stream():
    from app.services.llm.xunfei_chat_model import XunfeiChatModel
    from langchain_core.messages import HumanMessage
    captured = {}

    def fake_stream(messages, **kw):
        captured["messages"] = messages
        captured["kw"] = kw
        yield "ok"

    m = XunfeiChatModel(stream_fn=fake_stream)
    out = m._stream([HumanMessage(content="hi")])
    chunks = list(out)
    assert "".join(c.text for c in chunks) == "ok"
    assert captured["messages"][0].content == "hi"