"""pytest parametrize 改造 — Flashcard JSON 解析等价类测试

将原先 8 个独立测试函数压缩为一个 @pytest.mark.parametrize 驱动，
展示 pytest 参数化测试的核心能力：
  - 数据驱动：新等价类只需在数据列表里加一行
  - 失败定位：pytest 精确报告哪组数据失败
  - verbose 输出：-v 模式显示每组数据的描述

对比文件: tests/test_flashcard_flow.py (unittest 风格, 8 个独立方法)
"""

import json
import pytest
from agents import FlashcardAgent


# ====== 8 个等价类测试数据 ======

FLASH_CARD_TEST_CASES = [
    # (描述, 输入JSON字符串, 期望卡片数量, 第一张front内容(可选), 额外检查)
    pytest.param(
        "标准JSON数组",
        json.dumps({"flashcards": [
            {"front": "What is HDFS?", "back": "HDFS is a distributed file system.", "hint": "Not a single node FS"},
            {"front": "What is NameNode?", "back": "NameNode manages metadata.", "hint": "Doesn't store data"},
        ]}),
        2, "What is HDFS?",
        id="valid-standard-json",
    ),
    pytest.param(
        "Markdown代码块包裹",
        '```json\n{"flashcards": [{"front": "Q1", "back": "A1", "hint": "H1"}]}\n```',
        1, "Q1",
        id="valid-markdown-code-block",
    ),
    pytest.param(
        "普通代码块包裹",
        '```\n{"flashcards": [{"front": "Q2", "back": "A2", "hint": "H2"}]}\n```',
        1, "Q2",
        id="valid-plain-code-block",
    ),
    pytest.param(
        "JSON嵌在文本中",
        'Some text before {"flashcards": [{"front": "Q", "back": "A", "hint": "H"}]} trailing text',
        1, "Q",
        id="valid-json-embedded-in-text",
    ),
    pytest.param(
        "纯文本非JSON",
        "This is not JSON at all",
        0, None,
        id="invalid-plain-text",
    ),
    pytest.param(
        "数组含非dict元素",
        json.dumps({"flashcards": ["not a dict", 123, {"front": "Q", "back": "A", "hint": "H"}]}),
        1, "Q",
        id="invalid-non-dict-elements",
    ),
    pytest.param(
        "front为空被过滤",
        json.dumps({"flashcards": [
            {"front": "", "back": "A", "hint": "H"},
            {"front": "Q", "back": "A", "hint": "H"},
        ]}),
        1, "Q",
        id="invalid-empty-front-filtered",
    ),
    pytest.param(
        "back为空被过滤",
        json.dumps({"flashcards": [
            {"front": "Q", "back": "", "hint": "H"},
        ]}),
        0, None,
        id="invalid-empty-back-filtered",
    ),
]


@pytest.mark.parametrize("desc,response,expected_count,first_front", FLASH_CARD_TEST_CASES)
def test_parse_flashcard_format(desc, response, expected_count, first_front):
    """等价类测试：验证 FlashcardAgent 对各种输入格式的解析结果

    8 个等价类覆盖：
      - 有效类：标准JSON / Markdown包裹 / 普通代码块 / 嵌入文本
      - 无效类：纯文本 / 非dict元素 / front为空 / back为空
    """
    agent = FlashcardAgent()
    result = agent._parse_flashcard_response(response)

    assert "flashcards" in result, f"场景'{desc}'：返回结果应包含 flashcards 字段"
    assert len(result["flashcards"]) == expected_count, \
        f"场景'{desc}'：期望 {expected_count} 张卡片，实际 {len(result['flashcards'])} 张"

    if first_front:
        assert result["flashcards"][0]["front"] == first_front, \
            f"场景'{desc}'：第一张卡片 front 期望 '{first_front}'，实际 '{result['flashcards'][0]['front']}'"


# ====== 边界值测试也参数化 ======

@pytest.mark.parametrize("field,long_content,expected_max,description", [
    pytest.param("back", "A" * 250, 200, "back字段超出200字符截断", id="boundary-back-truncation"),
    pytest.param("hint", "H" * 80, 50, "hint字段超出50字符截断", id="boundary-hint-truncation"),
])
def test_field_truncation_boundary(field, long_content, expected_max, description):
    """边界值分析：字段长度截断"""
    agent = FlashcardAgent()
    card_data = {"front": "Q", "back": "A", "hint": "H"}
    card_data[field] = long_content
    response = json.dumps({"flashcards": [card_data]})
    result = agent._parse_flashcard_response(response)

    assert len(result["flashcards"]) == 1, f"应该成功解析 1 张卡片"
    assert len(result["flashcards"][0][field]) <= expected_max, \
        f"{description}：实际长度 {len(result['flashcards'][0][field])} > {expected_max}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
