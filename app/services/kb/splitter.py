"""Chinese-aware recursive text splitter."""
from langchain_text_splitters import RecursiveCharacterTextSplitter

_FORMULA_SEPARATORS = ["\n\n", "。", "！", "？", "\n", "；", "，"]


class ChineseRecursiveTextSplitter:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self._impl = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap,
            separators=_FORMULA_SEPARATORS, keep_separator=True,
        )

    def split_text(self, text: str) -> list[str]:
        return self._impl.split_text(text)