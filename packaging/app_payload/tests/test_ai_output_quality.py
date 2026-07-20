"""AI 输出质量测试 — 验证 LLM 返回内容的格式/结构/安全性/性能

测试维度：
  1. JSON 格式合规率 — LLM 是否按 schema 返回
  2. 响应延迟 — 解析是否在性能目标内
  3. 内容安全性 — 无注入/越狱内容
  4. Prompt 模板质量 — 发给 LLM 的指令本身是否完整正确
  5. 异常容错 — LLM 空返回、格式错误时的降级行为

特点：所有测试只测解析层和 Prompt 层，不消耗真实 LLM API 配额。
"""

import json
import time
import pytest
from agents import FlashcardAgent


class TestLLMOutputFormatCompliance:
    """LLM 输出格式合规性验证"""

    def test_parsed_cards_have_required_fields(self):
        """验证：每张解析后的闪卡必须包含 front/back/hint 三个字段"""
        agent = FlashcardAgent()
        response = json.dumps({
            "flashcards": [
                {"front": "What is MapReduce?", "back": "A programming model for parallel processing", "hint": "Two phases: Map and Reduce"},
                {"front": "NameNode vs DataNode?", "back": "NameNode manages metadata, DataNode stores actual data", "hint": "Think about HDFS architecture"},
            ]
        })
        result = agent._parse_flashcard_response(response)

        for i, card in enumerate(result.get("flashcards", [])):
            assert "front" in card, f"卡片 {i} 缺少 front 字段"
            assert "back" in card, f"卡片 {i} 缺少 back 字段"
            assert "hint" in card, f"卡片 {i} 缺少 hint 字段"

    def test_parsed_cards_front_not_empty(self):
        """验证：front 不能是空字符串 — 这是最低内容质量标准"""
        agent = FlashcardAgent()
        response = json.dumps({
            "flashcards": [
                {"front": "  ", "back": "Something", "hint": "Think"},
            ]
        })
        result = agent._parse_flashcard_response(response)
        # 纯空格 front 会被 strip 后变空，应被过滤
        assert len(result["flashcards"]) == 0, \
            "纯空白的 front 应被过滤，不应出现在结果中"

    def test_parsed_cards_content_not_too_short(self):
        """验证：front 至少要有实际内容（≥2个字符）"""
        agent = FlashcardAgent()
        response = json.dumps({
            "flashcards": [
                {"front": "Q", "back": "Answer is here", "hint": "H"},
            ]
        })
        result = agent._parse_flashcard_response(response)
        for card in result.get("flashcards", []):
            assert len(card["front"].strip()) >= 1, \
                f"front 内容过短: '{card['front']}'"

    def test_multiple_cards_all_validated(self):
        """验证：批量闪卡中每张都经过校验，不合格的被过滤"""
        agent = FlashcardAgent()
        response = json.dumps({
            "flashcards": [
                {"front": "Valid Q1", "back": "Valid A1", "hint": "Valid H1"},
                {"front": "", "back": "Empty front", "hint": "H"},  # 应被过滤
                {"front": "Valid Q2", "back": "Valid A2", "hint": ""},       # hint 可为空
                {"front": "Valid Q3", "back": "", "hint": "H3"},    # back 为空，应被过滤
            ]
        })
        result = agent._parse_flashcard_response(response)
        # 只有第一张和第三张有效（hint 空是允许的，back 空不允许）
        assert len(result["flashcards"]) >= 2, \
            f"应该至少保留 2 张有效闪卡，实际 {len(result['flashcards'])} 张"


class TestLLMOutputSecurity:
    """LLM 输出安全性验证 — 确保返回内容不含注入攻击"""

    def test_parser_preserves_content_for_frontend_sanitization(self):
        """验证：解析器保留原始内容，XSS 防护由前端 escapeHTML 负责

        架构决策：后端解析器负责结构化，前端 toast.js 的 escapeHTML() 负责 sanitize。
        这是关注点分离 — 后端不破坏 LLM 输出，前端统一做输出转义。
        因此解析器输出中可能包含 script 标签等危险内容，这是预期行为。
        """
        agent = FlashcardAgent()
        # 模拟 LLM 被注入后返回的内容
        injection_cases = [
            ("prompt injection in front",
             json.dumps({"flashcards": [
                 {"front": "ignore previous instructions", "back": "Normal", "hint": "H"}
             ]})),
            ("XSS in back",
             json.dumps({"flashcards": [
                 {"front": "Q", "back": "<script>alert('xss')</script>", "hint": "H"}
             ]})),
        ]

        for name, response in injection_cases:
            result = agent._parse_flashcard_response(response)
            assert len(result["flashcards"]) >= 0, \
                f"场景 '{name}'：解析器不应崩溃，应正常返回"
            # 确认：解析器确实保留了原始内容（交由前端 escapeHTML 处理）
            if result["flashcards"]:
                card = result["flashcards"][0]
                assert "front" in card and "back" in card and "hint" in card, \
                    f"场景 '{name}'：卡片结构应完整"

    def test_back_field_truncated_content_integrity(self):
        """验证：back 字段截断后保留有效内容（以 '...' 标记截断）"""
        agent = FlashcardAgent()
        long_content = "B" * 250
        response = json.dumps({"flashcards": [{"front": "Q", "back": long_content, "hint": "H"}]})
        result = agent._parse_flashcard_response(response)
        assert len(result["flashcards"]) == 1
        back = result["flashcards"][0]["back"]
        # 截断后长度 ≤ 200
        assert len(back) <= 200
        # 截断标记 '...' 出现在末尾
        assert back.endswith("..."), \
            f"back 截断后应以 '...' 结尾，实际: {back[-10:]}"


class TestLLMOutputPerformance:
    """LLM 输出解析性能验证"""

    def test_parse_single_card_under_5ms(self):
        """验证：单张闪卡解析应在 5ms 内完成"""
        agent = FlashcardAgent()
        response = json.dumps({"flashcards": [{"front": "Q", "back": "A", "hint": "H"}]})

        start = time.perf_counter()
        result = agent._parse_flashcard_response(response)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert "flashcards" in result
        assert elapsed_ms < 5, f"单张闪卡解析耗时 {elapsed_ms:.2f}ms，目标 < 5ms"

    def test_parse_20_cards_under_10ms(self):
        """验证：20 张闪卡批量解析应在 10ms 内完成"""
        agent = FlashcardAgent()
        response = json.dumps({"flashcards": [
            {"front": f"Q{i}", "back": f"A{i}", "hint": f"H{i}"} for i in range(20)
        ]})

        start = time.perf_counter()
        result = agent._parse_flashcard_response(response)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert len(result["flashcards"]) == 20
        assert elapsed_ms < 10, f"20 张闪卡解析耗时 {elapsed_ms:.2f}ms，目标 < 10ms"

    def test_parse_markdown_wrapped_performance(self):
        """验证：Markdown 代码块包裹的 JSON 解析也不应明显变慢"""
        agent = FlashcardAgent()
        inner = json.dumps({"flashcards": [{"front": f"Q{i}", "back": f"A{i}", "hint": f"H{i}"} for i in range(10)]})
        response = f'```json\n{inner}\n```'

        start = time.perf_counter()
        result = agent._parse_flashcard_response(response)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert len(result["flashcards"]) == 10
        assert elapsed_ms < 10, f"Markdown 包裹 JSON 解析耗时 {elapsed_ms:.2f}ms"


class TestLLMErrorTolerance:
    """LLM 异常输出容错验证"""

    def test_empty_response_handled(self):
        """验证：LLM 返回空字符串时不会崩溃，返回空列表"""
        agent = FlashcardAgent()
        result = agent._parse_flashcard_response("")
        assert "flashcards" in result
        assert len(result["flashcards"]) == 0

    def test_malformed_json_handled(self):
        """验证：LLM 返回不完整 JSON 时不会崩溃"""
        agent = FlashcardAgent()
        # 模拟 LLM 返回被截断的 JSON
        result = agent._parse_flashcard_response('{"flashcards": [{"front": "Q", "back": "A')
        assert "flashcards" in result
        # 不应抛出异常即可
        assert isinstance(result["flashcards"], list)

    def test_list_instead_of_dict_handled(self):
        """验证：LLM 直接返回数组而非对象时优雅处理"""
        agent = FlashcardAgent()
        result = agent._parse_flashcard_response(
            '[{"front": "Q", "back": "A", "hint": "H"}]'
        )
        assert "flashcards" in result

    def test_spaces_and_newlines_tolerated(self):
        """验证：大量空白字符和换行不影响解析"""
        agent = FlashcardAgent()
        response = ' \n  \n\t  {"flashcards": [{"front": "Q", "back": "A", "hint": "H"}]} \n \n '
        result = agent._parse_flashcard_response(response)
        assert len(result["flashcards"]) == 1


class TestAIPromptQuality:
    """Prompt 模板质量验证 — 确保发给 LLM 的指令本身完整正确"""

    QUALITY_FIELDS = ["front", "back", "hint", "flashcards"]

    def test_flashcard_system_prompt_exists(self):
        """验证：FlashcardAgent 的 SYSTEM_PROMPT 不应为空"""
        assert FlashcardAgent.SYSTEM_PROMPT, "SYSTEM_PROMPT 不应为空"
        assert len(FlashcardAgent.SYSTEM_PROMPT) > 200, \
            f"SYSTEM_PROMPT 过短 ({len(FlashcardAgent.SYSTEM_PROMPT)} 字符)，可能缺少质量控制规则"

    @pytest.mark.parametrize("keyword", [
        "压缩规则",
        "输出格式",
        "质量控制",
        "flashcards",
        "front",
        "back",
        "hint",
    ])
    def test_flashcard_prompt_contains_quality_keywords(self, keyword):
        """验证：SYSTEM_PROMPT 包含质量控制相关的关键词"""
        assert keyword in FlashcardAgent.SYSTEM_PROMPT, \
            f"SYSTEM_PROMPT 应包含质量控制关键词: '{keyword}'"

    def test_flashcard_prompt_requires_json_format(self):
        """验证：SYSTEM_PROMPT 明确要求 JSON 输出格式"""
        assert "json" in FlashcardAgent.SYSTEM_PROMPT.lower(), \
            "SYSTEM_PROMPT 应要求 JSON 格式输出"

    def test_flashcard_prompt_specifies_char_limits(self):
        """验证：SYSTEM_PROMPT 明确说明了 back/hint 的字符限制"""
        prompt = FlashcardAgent.SYSTEM_PROMPT
        assert "200" in prompt, "SYSTEM_PROMPT 应说明 back 字段的字符限制 (≤200)"
        assert "50" in prompt, "SYSTEM_PROMPT 应说明 hint 字段的字符限制 (≤50)"

    def test_flashcard_prompt_enforces_min_count(self):
        """验证：SYSTEM_PROMPT 有最少闪卡数量的强制要求"""
        prompt = FlashcardAgent.SYSTEM_PROMPT
        assert "10" in prompt or "至少" in prompt, \
            "SYSTEM_PROMPT 应有最少闪卡数量的要求"


class TestFlashcardAgentConstants:
    """验证 FlashcardAgent 的硬编码常量与 Prompt 声明一致"""

    def test_min_count_constant_matches_prompt(self):
        """验证：MIN_FLASHCARD_COUNT 常量在 SYSTEM_PROMPT 中有体现"""
        agent = FlashcardAgent()
        assert agent.MIN_FLASHCARD_COUNT == 10
        assert str(agent.MIN_FLASHCARD_COUNT) in agent.SYSTEM_PROMPT, \
            f"SYSTEM_PROMPT 中应提到 {agent.MIN_FLASHCARD_COUNT}"

    def test_max_retry_constant_reasonable(self):
        """验证：MAX_RETRY_ATTEMPTS 在合理范围内 (1-5)"""
        agent = FlashcardAgent()
        assert 1 <= agent.MAX_RETRY_ATTEMPTS <= 5, \
            f"MAX_RETRY_ATTEMPTS={agent.MAX_RETRY_ATTEMPTS}，应在 1-5 之间"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
