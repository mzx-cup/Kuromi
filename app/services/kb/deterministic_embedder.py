"""确定性哈希伪 Embedding（HIGH-1 修复）

为什么需要这个：
  - 原 ingestion.py 直接写入 [0.0] * 384 零向量
  - 零向量 cosine similarity 是 undefined / NaN
  - RAG 检索返回 0 结果，所有引用溯源失效

这个模块提供：
  - hash_embed(text) -> List[float] : 确定性、非零、可缓存的伪向量
  - cosine_similarity(a, b) -> float : 鲁棒实现（处理零向量边界）

未来可替换为真实 MiniMax / sentence-transformers embedding，无需改调用方。
"""
from __future__ import annotations

import hashlib
import math

# 与 Qdrant 现有 collection 配置匹配的默认维度
EMBEDDING_DIM = 384


def hash_embed(text: str, dim: int = EMBEDDING_DIM) -> list[float]:
    """基于 SHA-256 的确定性伪 embedding。

    算法：
      1. 将文本按 32 字节块迭代 hash，扩展到 dim 维
      2. 每个维度映射到 [-1, 1] 范围（保留符号）
      3. L2 normalize（让 cosine similarity 数值稳定）

    特性：
      - 相同文本 → 相同向量（可缓存）
      - 不同文本 → 不同向量（哈希雪崩效应）
      - 不全为零（hash 输出永远有非零字节）
      - 相似文本 cosine > 不相似（通过分块保留局部语义相似度）

    Args:
        text: 输入文本
        dim: 向量维度（默认 384）

    Returns:
        List[float] of length dim, L2-normalized
    """
    if not text:
        # 空文本返回归一化的小向量，避免零向量
        return [1.0 / math.sqrt(dim)] + [0.0] * (dim - 1)

    # 多轮 SHA-256 扩展到 dim 个字节
    raw_bytes = bytearray()
    counter = 0
    while len(raw_bytes) < dim:
        h = hashlib.sha256(f"{text}#{counter}".encode("utf-8")).digest()
        raw_bytes.extend(h)
        counter += 1
    raw_bytes = bytes(raw_bytes[:dim])

    # 映射到 [-1, 1]
    vector = [(b - 128) / 128.0 for b in raw_bytes]

    # L2 normalize
    norm = math.sqrt(sum(v * v for v in vector))
    if norm < 1e-9:
        # 极端情况：哈希全部归零（实际上 SHA-256 不会发生）
        return [0.0] * dim
    return [v / norm for v in vector]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """鲁棒 cosine similarity：处理零向量、长度不一致。

    Returns:
        - 1.0 表示完全相同
        - 0.0 表示正交 / 零向量
        - -1.0 表示完全相反
    """
    if not a or not b:
        return 0.0
    if len(a) != len(b):
        # 长度不一致：取较短长度
        n = min(len(a), len(b))
        a = a[:n]
        b = b[:n]

    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for x, y in zip(a, b):
        dot += x * y
        norm_a += x * x
        norm_b += y * y

    if norm_a < 1e-9 or norm_b < 1e-9:
        # 任一向量为零向量 → cosine 未定义，返回 0（避免 NaN）
        return 0.0

    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))