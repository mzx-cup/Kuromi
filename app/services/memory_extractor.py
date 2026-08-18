# -*- coding: utf-8 -*-
"""
Memory Extractor — 从对话中提取用户长期记忆

工作流程:
  1. 收集最近 N 轮对话
  2. 调用 LLM 提取结构化记忆
  3. 与现有记忆去重合并
  4. 保存到 user_memories 表

记忆类型:
  - background: 个人背景（姓名、专业、年级等）
  - preference: 偏好（喜欢的语言、学习方式等）
  - knowledge: 已掌握知识
  - interest: 兴趣方向
  - goal: 学习目标
  - emotion: 情感状态（上次的情绪、遇到的困难等）
  - learning_trait: 学习特征（学习风格、理解方式、记忆特点等）
  - personality: 性格特点（内向/外向、做事风格、思维习惯等）
  - interaction: 互动习惯（沟通偏好、反馈方式、表达习惯等）
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from llm_stream import call_llm_async

logger = logging.getLogger("starlearn.memory")

EXTRACTION_PROMPT = """你是一位擅长理解学生的AI导师。请从以下对话中，提取关于这位学生的**新信息**。

【已有记忆】（如果为空表示这是第一次）:
{existing_memories}

【新对话】:
{conversation_text}

【提取规则】:
1. 只提取**新出现**的信息，已有记忆中已经有的不要重复提取
2. 信息要具体、准确，不要猜测
3. 如果学生明确纠正了之前的记忆，标记为"update"
4. 情感类记忆要注明时间和情境
5. 关注学习特征（学习风格、擅长/薄弱点）、性格特点（沟通偏好、性格标签）、互动习惯（活跃时段、回复模式）

【输出格式】JSON数组:
[
  {{
    "memory_type": "background|preference|knowledge|interest|goal|emotion|learning_trait|personality|interaction",
    "content": "具体记忆内容，用第三人称描述",
    "confidence": 0.9,
    "is_update": false
  }}
]

如果没有新信息，输出空数组 []。
只输出 JSON，不要任何解释。"""


async def extract_memories_from_conversation(
    user_id: str,
    conversation: list[dict[str, str]],
    existing_memories: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """
    从对话中提取用户记忆。

    Args:
        user_id: 用户ID
        conversation: 对话记录 [{role, content}, ...]
        existing_memories: 已有记忆列表（用于去重）

    Returns:
        提取到的新记忆列表
    """
    if not conversation:
        return []

    # 格式化对话文本
    conversation_text = "\n".join(
        f"{'用户' if msg.get('role') == 'user' else 'AI'}: {msg.get('content', '')}"
        for msg in conversation
    )

    # 格式化已有记忆
    existing_text = ""
    if existing_memories:
        for m in existing_memories[:20]:  # 最多20条，避免超出上下文
            existing_text += f"- [{m.get('memory_type', 'fact')}] {m.get('content', '')}\n"
    else:
        existing_text = "（暂无）"

    prompt = EXTRACTION_PROMPT.format(
        existing_memories=existing_text,
        conversation_text=conversation_text,
    )

    try:
        result = await call_llm_async(
            "你是一位善于观察和理解学生的教育AI。请准确提取对话中的用户信息。",
            prompt,
            temperature=0.3,
        )
        memories = _parse_extraction_result(result)
        logger.info(f"[MemoryExtractor] 从对话中提取了 {len(memories)} 条记忆")
        return memories
    except Exception as e:
        logger.error(f"[MemoryExtractor] 记忆提取失败: {e}")
        raise  # 向上抛出，让调用方感知并记录


def _parse_extraction_result(text: str) -> list[dict[str, Any]]:
    """解析 LLM 输出的 JSON 记忆数组。"""
    text = text.strip()
    if text.startswith("```json"):
        text = text.split("```json", 1)[1]
    if text.startswith("```"):
        text = text.split("```", 1)[1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    text = text.strip()

    # 尝试从文本中提取 JSON 数组（可能嵌入在其他文本中）
    candidates = [text]
    
    # 寻找方括号包裹的内容
    start_idx = text.find("[")
    end_idx = text.rfind("]")
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        candidates.append(text[start_idx:end_idx + 1])
    
    # 寻找花括号包裹的内容（单个对象）
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
        single_obj = text[brace_start:brace_end + 1]
        candidates.append(single_obj)

    for candidate in candidates:
        candidate = candidate.strip()
        if not candidate:
            continue
        try:
            data = json.loads(candidate)
            if isinstance(data, list):
                valid = []
                for item in data:
                    if isinstance(item, dict) and item.get("content"):
                        valid.append({
                            "memory_type": item.get("memory_type", "fact"),
                            "content": item["content"],
                            "confidence": float(item.get("confidence", 0.8)),
                            "is_update": bool(item.get("is_update", False)),
                        })
                return valid
            elif isinstance(data, dict) and data.get("content"):
                # LLM 返回了单个对象而不是数组
                return [{
                    "memory_type": data.get("memory_type", "fact"),
                    "content": data["content"],
                    "confidence": float(data.get("confidence", 0.8)),
                    "is_update": bool(data.get("is_update", False)),
                }]
        except json.JSONDecodeError:
            continue

    logger.warning(f"[MemoryExtractor] 无法解析 LLM 输出: {text[:300]}...")
    return []


def deduplicate_memories(
    new_memories: list[dict[str, Any]],
    existing_memories: list[dict[str, Any]],
    similarity_threshold: float = 0.55,
) -> list[dict[str, Any]]:
    """
    去重：如果新记忆与已有记忆相似度超过阈值，则合并或跳过。

    Returns:
        需要去重后的新记忆（含标记为 update 的）
    """
    def _similarity(a: str, b: str) -> float:
        """混合文本相似度：字符级 Jaccard（适配中文）+ 词级 Jaccard（适配英文）。"""
        a_lower = a.lower().strip()
        b_lower = b.lower().strip()
        if not a_lower or not b_lower:
            return 0.0

        # 字符级 Jaccard（适配中文短句）
        chars_a = set(a_lower)
        chars_b = set(b_lower)
        # 过滤掉常见无意义字符
        noise = set(' ，。！？、；：""''（）【】《》 \t\n')
        chars_a -= noise
        chars_b -= noise
        char_sim = 0.0
        if chars_a and chars_b:
            char_sim = len(chars_a & chars_b) / len(chars_a | chars_b)

        # 词级 Jaccard（适配英文）
        words_a = set(a_lower.split())
        words_b = set(b_lower.split())
        word_sim = 0.0
        if words_a and words_b:
            word_sim = len(words_a & words_b) / len(words_a | words_b)

        # 取最大值（中文场景字符级更敏感，英文场景词级更敏感）
        return max(char_sim, word_sim)

    result = []
    for new in new_memories:
        new_content = new["content"]
        is_duplicate = False

        for existing in existing_memories:
            sim = _similarity(new_content, existing.get("content", ""))
            if sim >= similarity_threshold:
                is_duplicate = True
                if new.get("is_update"):
                    # 标记为更新，后续处理会覆盖
                    new["_update_target_id"] = existing.get("id")
                    result.append(new)
                break

        if not is_duplicate:
            result.append(new)

    return result


async def save_extracted_memories(
    user_id: str,
    memories: list[dict[str, Any]],
    source: str = "auto_extraction",
) -> list[str]:
    """
    将提取的记忆保存到数据库。

    Returns:
        保存成功的记忆ID列表
    """
    saved_ids: list[str] = []
    # Slice #9: route memory persistence through the SQLAlchemy chat repo
    # so the dual-write to legacy db.py continues via DualWriteRepository.
    from app.repositories.orm.chat import SqlAlchemyChatRepository

    # Resolve a session lazily. If no session is bound (e.g. unit tests that
    # call this function in isolation), fall back to db.py for backwards
    # compatibility.
    session_ctx = None
    try:
        from app.core.database import get_sessionmaker
        SessionLocal = get_sessionmaker()
        session_ctx = SessionLocal()
    except Exception:
        session_ctx = None

    if session_ctx is not None:
        try:
            # SqlAlchemyChatRepository is **synchronous** (a ~30-test call
            # site contracts depend on it staying sync).  Wrap the whole
            # thing in ``await session.run_sync`` so the sync repo's
            # ``self.session.flush()`` / ``self.session.add()`` execute
            # against a real sync ``Session`` bind — never on the AsyncSession
            # itself (that gave us silent commit failures + "None" IDs).
            chat_repo = SqlAlchemyChatRepository(session_ctx)

            def _do_writes(session):
                ids: list[str] = []
                for mem in memories:
                    mem_id = mem.get("_update_target_id")
                    if mem_id and mem.get("is_update"):
                        # 更新已有记忆
                        chat_repo.update_memory(
                            mem_id,
                            {"content": mem["content"], "importance": int(mem["confidence"] * 10)},
                        )
                        # 更新分支透传原 id（与 ``test_fallback_updates_...``
                        # 的 ``assert ids == [seeded_id]`` 对齐,seeded_id 是 int）
                        ids.append(mem_id)
                    else:
                        # 新增记忆
                        new_id_int = chat_repo.save_memory(
                            user_id=user_id,
                            memory={
                                "memory_type": mem["memory_type"],
                                "content": mem["content"],
                                "importance": int(mem["confidence"] * 10),
                                "source_conversation_id": source,
                            },
                        )
                        # flush() 之后 lastrowid 应该有值；旧逻辑里因为没 flush
                        # 这里一直是 None，被 str() 成字符串 "None"。
                        ids.append(str(new_id_int) if new_id_int is not None else "")
                return ids

            saved_ids = await session_ctx.run_sync(_do_writes)
            await session_ctx.commit()
            return saved_ids
        except Exception as e:
            logger.warning(f"[MemoryExtractor] ORM save failed, falling back to db.py: {e}")
            try:
                await session_ctx.rollback()
            except Exception:
                pass
        finally:
            try:
                await session_ctx.close()
            except Exception:
                pass

    # Fallback: legacy ChatRepository path (preserves old behaviour for
    # callers without an ORM session, e.g. unit tests that call this
    # function in isolation). Routes through DbPyChatRepository instead of
    # raw db.py functions, so the entire file flows through the Repository
    # abstraction.
    from app.repositories.legacy.chat import DbPyChatRepository
    chat_repo = DbPyChatRepository()
    for mem in memories:
        mem_id = mem.get("_update_target_id")
        if mem_id and mem.get("is_update"):
            # 更新已有记忆 — DbPyChatRepository.update_memory expects an
            # INTEGER id and a dict of updates. The id space shifts from
            # uuid-string to int-auto-increment; that's an intentional
            # consequence of routing through ChatRepository (the dual-write
            # slice #9 made the same shift on the ORM path).
            try:
                int_mem_id = int(mem_id)
            except (TypeError, ValueError):
                logger.warning(
                    f"[MemoryExtractor] Skipping update for non-int memory_id: {mem_id!r}"
                )
                continue
            chat_repo.update_memory(
                int_mem_id,
                {
                    "content": mem["content"],
                    "importance": int(mem["confidence"] * 10),
                },
            )
            # 更新分支透传原 id (int)
            saved_ids.append(mem_id)
        else:
            # 新增记忆 — returns int auto-increment id; stringify for the
            # existing return contract (list[str]).
            new_id_int = chat_repo.save_memory(
                user_id=user_id,
                memory={
                    "memory_type": mem["memory_type"],
                    "content": mem["content"],
                    "importance": int(mem["confidence"] * 10),
                    "source_conversation_id": source,
                },
            )
            saved_ids.append(str(new_id_int) if new_id_int is not None else "")

    return saved_ids
