"""BaseChatModel adapter wrapping existing llm_stream.py."""
from typing import AsyncIterator, Iterator, List, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class XunfeiChatModel(BaseChatModel):
    stream_fn: Optional[object] = None  # injected callable from llm_stream
    model_kwargs: dict = {}

    def _generate(self, messages: List[BaseMessage], stop=None, **kwargs) -> ChatResult:
        raise NotImplementedError("Streaming-only — call _stream directly")

    def _stream(self, messages: List[BaseMessage], stop=None, **kwargs) -> Iterator["ChatGenerationChunk"]:
        from langchain_core.messages import AIMessageChunk
        from langchain_core.outputs import ChatGenerationChunk
        if self.stream_fn is None:
            raise RuntimeError("XunfeiChatModel.stream_fn not injected")
        for token in self.stream_fn(messages):
            yield ChatGenerationChunk(message=AIMessageChunk(content=token))

    @property
    def _llm_type(self) -> str:
        return "xunfei"