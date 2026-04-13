import unittest
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import requests

BASE = "http://127.0.0.1:8000"


class TestFlashcardAgentUnit(unittest.TestCase):

    def test_import_flashcard_agent(self):
        from agents import FlashcardAgent
        agent = FlashcardAgent()
        self.assertEqual(agent.name, "flashcard")
        self.assertEqual(agent.role, "知识胶囊智能体")
        self.assertIsNotNone(agent.SYSTEM_PROMPT)

    def test_system_prompt_contains_rules(self):
        from agents import FlashcardAgent
        prompt = FlashcardAgent.SYSTEM_PROMPT
        self.assertIn("压缩规则", prompt)
        self.assertIn("输出格式", prompt)
        self.assertIn("质量控制标准", prompt)
        self.assertIn("flashcards", prompt)
        self.assertIn("front", prompt)
        self.assertIn("back", prompt)
        self.assertIn("hint", prompt)

    def test_parse_flashcard_response_valid_json(self):
        from agents import FlashcardAgent
        agent = FlashcardAgent()
        response = json.dumps({
            "flashcards": [
                {"front": "What is HDFS?", "back": "HDFS is a distributed file system.", "hint": "Not a single node FS"},
                {"front": "What is NameNode?", "back": "NameNode manages metadata.", "hint": "Doesn't store data"},
            ]
        })
        result = agent._parse_flashcard_response(response)
        self.assertEqual(len(result["flashcards"]), 2)
        self.assertEqual(result["flashcards"][0]["front"], "What is HDFS?")
        self.assertEqual(result["flashcards"][1]["hint"], "Doesn't store data")

    def test_parse_flashcard_response_markdown_code_block(self):
        from agents import FlashcardAgent
        agent = FlashcardAgent()
        response = '```json\n{"flashcards": [{"front": "Q1", "back": "A1", "hint": "H1"}]}\n```'
        result = agent._parse_flashcard_response(response)
        self.assertEqual(len(result["flashcards"]), 1)
        self.assertEqual(result["flashcards"][0]["front"], "Q1")

    def test_parse_flashcard_response_plain_code_block(self):
        from agents import FlashcardAgent
        agent = FlashcardAgent()
        response = '```\n{"flashcards": [{"front": "Q2", "back": "A2", "hint": "H2"}]}\n```'
        result = agent._parse_flashcard_response(response)
        self.assertEqual(len(result["flashcards"]), 1)

    def test_parse_flashcard_response_back_truncation(self):
        from agents import FlashcardAgent
        agent = FlashcardAgent()
        long_back = "A" * 250
        response = json.dumps({"flashcards": [{"front": "Q", "back": long_back, "hint": "H"}]})
        result = agent._parse_flashcard_response(response)
        self.assertLessEqual(len(result["flashcards"][0]["back"]), 200)

    def test_parse_flashcard_response_hint_truncation(self):
        from agents import FlashcardAgent
        agent = FlashcardAgent()
        long_hint = "H" * 80
        response = json.dumps({"flashcards": [{"front": "Q", "back": "A", "hint": long_hint}]})
        result = agent._parse_flashcard_response(response)
        self.assertLessEqual(len(result["flashcards"][0]["hint"]), 50)

    def test_parse_flashcard_response_empty_front_skipped(self):
        from agents import FlashcardAgent
        agent = FlashcardAgent()
        response = json.dumps({"flashcards": [
            {"front": "", "back": "A", "hint": "H"},
            {"front": "Q", "back": "A", "hint": "H"},
        ]})
        result = agent._parse_flashcard_response(response)
        self.assertEqual(len(result["flashcards"]), 1)

    def test_parse_flashcard_response_empty_back_skipped(self):
        from agents import FlashcardAgent
        agent = FlashcardAgent()
        response = json.dumps({"flashcards": [
            {"front": "Q", "back": "", "hint": "H"},
        ]})
        result = agent._parse_flashcard_response(response)
        self.assertEqual(len(result["flashcards"]), 0)

    def test_parse_flashcard_response_invalid_json(self):
        from agents import FlashcardAgent
        agent = FlashcardAgent()
        response = "This is not JSON at all"
        result = agent._parse_flashcard_response(response)
        self.assertIn("flashcards", result)
        self.assertEqual(len(result["flashcards"]), 0)
        self.assertIn("message", result)

    def test_parse_flashcard_response_partial_json(self):
        from agents import FlashcardAgent
        agent = FlashcardAgent()
        response = 'Some text before {"flashcards": [{"front": "Q", "back": "A", "hint": "H"}]} some text after'
        result = agent._parse_flashcard_response(response)
        self.assertEqual(len(result["flashcards"]), 1)

    def test_parse_flashcard_response_non_dict_card(self):
        from agents import FlashcardAgent
        agent = FlashcardAgent()
        response = json.dumps({"flashcards": ["not a dict", 123, {"front": "Q", "back": "A", "hint": "H"}]})
        result = agent._parse_flashcard_response(response)
        self.assertEqual(len(result["flashcards"]), 1)

    def test_run_insufficient_content(self):
        from agents import FlashcardAgent
        from state import StudentState
        agent = FlashcardAgent()
        state = StudentState(student_id="test", course_id="bigdata", context_id="fc-test")
        result = asyncio.run(agent.run(state, chapter_content="hi", chapter_name="test"))
        cards = result.metadata.get("flashcards", {})
        self.assertEqual(len(cards.get("flashcards", [])), 0)
        self.assertIn("message", cards)

    def test_run_extracts_from_history(self):
        from agents import FlashcardAgent
        from state import StudentState, DialogueRole
        agent = FlashcardAgent()
        state = StudentState(student_id="test", course_id="bigdata", context_id="fc-test2")
        state.metadata["current_chapter"] = "Test Chapter"
        state.add_message(DialogueRole.STUDENT, "HDFS architecture content " * 10)
        with patch.object(agent, '_generate_flashcards', new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = {"flashcards": [{"front": "Q", "back": "A", "hint": "H"}]}
            result = asyncio.run(agent.run(state))
            self.assertEqual(len(result.metadata["flashcards"]["flashcards"]), 1)

    def test_run_llm_error_handled(self):
        from agents import FlashcardAgent
        from state import StudentState
        agent = FlashcardAgent()
        state = StudentState(student_id="test", course_id="bigdata", context_id="fc-err")
        with patch.object(agent, '_generate_flashcards', new_callable=AsyncMock) as mock_gen:
            mock_gen.side_effect = Exception("LLM service unavailable")
            result = asyncio.run(agent.run(state, chapter_content="x" * 100, chapter_name="test"))
            cards = result.metadata.get("flashcards", {})
            self.assertEqual(len(cards.get("flashcards", [])), 0)
            self.assertIn("闪卡生成失败", cards.get("message", ""))


class TestFlashcardAPIE2E(unittest.TestCase):

    def test_flashcard_generate_success(self):
        r = requests.post(f"{BASE}/api/v2/flashcard/generate", json={
            "student_id": "test_user",
            "course_id": "bigdata",
            "chapter_name": "MapReduce编程模型",
            "chapter_content": "MapReduce是一种编程模型，用于大规模数据集的并行运算。Map阶段将输入数据拆分为独立的分片，每个分片由一个Map任务处理，输出键值对。Reduce阶段接收Map输出的中间结果，按键分组后进行聚合计算。MapReduce框架自动处理任务调度、数据分发、容错恢复等底层细节。用户只需实现Map和Reduce两个函数即可完成分布式计算。",
        }, timeout=60)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data.get("success"))
        cards = data.get("data", {}).get("flashcards", [])
        self.assertGreater(len(cards), 0)
        for card in cards:
            self.assertIn("front", card)
            self.assertIn("back", card)
            self.assertTrue(len(card["front"]) > 0)
            self.assertTrue(len(card["back"]) > 0)
            self.assertLessEqual(len(card["back"]), 200)

    def test_flashcard_short_content_returns_empty(self):
        r = requests.post(f"{BASE}/api/v2/flashcard/generate", json={
            "student_id": "test_user",
            "course_id": "bigdata",
            "chapter_name": "test",
            "chapter_content": "hi",
        }, timeout=15)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        cards = data.get("data", {}).get("flashcards", [])
        self.assertEqual(len(cards), 0)

    def test_flashcard_missing_content_field(self):
        r = requests.post(f"{BASE}/api/v2/flashcard/generate", json={
            "student_id": "test_user",
            "course_id": "bigdata",
            "chapter_name": "test",
        }, timeout=10)
        self.assertIn(r.status_code, [200, 422])
        if r.status_code == 200:
            data = r.json()
            cards = data.get("data", {}).get("flashcards", [])
            self.assertEqual(len(cards), 0)

    def test_flashcard_empty_content_field(self):
        r = requests.post(f"{BASE}/api/v2/flashcard/generate", json={
            "student_id": "test_user",
            "course_id": "bigdata",
            "chapter_name": "test",
            "chapter_content": "",
        }, timeout=10)
        self.assertEqual(r.status_code, 422)

    def test_flashcard_default_course_id(self):
        r = requests.post(f"{BASE}/api/v2/flashcard/generate", json={
            "student_id": "test_user",
            "chapter_name": "test",
            "chapter_content": "Spark是基于内存的分布式计算框架，比MapReduce快100倍。RDD是其核心抽象，支持弹性分布式数据集操作。Spark SQL提供结构化数据处理，DataFrame是其主要API。Spark Streaming支持实时流处理，采用微批处理模型。",
        }, timeout=60)
        self.assertEqual(r.status_code, 200)


class TestFrontendIntegration(unittest.TestCase):

    def _fetch_html(self):
        return requests.get(f"{BASE}/", timeout=5).text

    def _fetch_css(self):
        return requests.get(f"{BASE}/css/index.css", timeout=5).text

    def test_html_flow_overlay(self):
        html = self._fetch_html()
        self.assertIn("flow-overlay", html)

    def test_html_flow_audio(self):
        html = self._fetch_html()
        self.assertIn("flow-audio", html)
        self.assertIn("loop", html)

    def test_html_flow_enter_button(self):
        html = self._fetch_html()
        self.assertIn("flow-enter-btn", html)
        self.assertIn("flowMode.enter()", html)

    def test_html_flashcard_button(self):
        html = self._fetch_html()
        self.assertIn("flashcard-btn", html)
        self.assertIn("flashcardUI.open()", html)

    def test_html_timer_display(self):
        html = self._fetch_html()
        self.assertIn("flow-timer-display", html)
        self.assertIn("25:00", html)

    def test_html_ring_progress(self):
        html = self._fetch_html()
        self.assertIn("flow-ring-progress", html)
        self.assertIn("stroke-dasharray", html)

    def test_html_audio_controls(self):
        html = self._fetch_html()
        self.assertIn("flow-audio-toggle", html)
        self.assertIn("flow-volume", html)

    def test_css_flow_mode_active(self):
        css = self._fetch_css()
        self.assertIn("flow-mode-active", css)

    def test_css_flow_timer_ring(self):
        css = self._fetch_css()
        self.assertIn("flow-timer-ring", css)

    def test_css_flashcard_flip(self):
        css = self._fetch_css()
        self.assertIn(".flipped", css)
        self.assertIn("rotateY(180deg)", css)
        self.assertIn("backface-visibility: hidden", css)

    def test_css_timer_pulse_animation(self):
        css = self._fetch_css()
        self.assertIn("timerPulse", css)

    def test_css_dark_mode_transitions(self):
        css = self._fetch_css()
        self.assertIn("translateX(-110%)", css)
        self.assertIn("400ms", css)

    def test_css_responsive_breakpoint(self):
        css = self._fetch_css()
        self.assertIn("768px", css)

    def test_css_perspective_3d(self):
        css = self._fetch_css()
        self.assertIn("perspective: 1000px", css)
        self.assertIn("preserve-3d", css)


class TestAPIEndpoints(unittest.TestCase):

    def test_proactive_status(self):
        r = requests.get(f"{BASE}/api/v2/proactive/status", timeout=5)
        self.assertEqual(r.status_code, 200)

    def test_struggle_event(self):
        r = requests.post(f"{BASE}/api/v2/event/struggle", json={"user_id": "test"}, timeout=5)
        self.assertIn(r.status_code, [200, 201])

    def test_agents_list(self):
        r = requests.get(f"{BASE}/api/v2/agents/list", timeout=5)
        self.assertEqual(r.status_code, 200)

    def test_courses_list(self):
        r = requests.get(f"{BASE}/api/v2/courses/list", timeout=5)
        self.assertEqual(r.status_code, 200)


if __name__ == "__main__":
    unittest.main(verbosity=2)
