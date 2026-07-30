# -*- coding: utf-8 -*-
"""Tests for reflection agent."""
from app.services.agent.reflection_agent import (
    ReflectionAgent,
    ReflectionTrigger,
    get_reflection_agent,
)


def test_build_prompt_default_three_questions():
    agent = ReflectionAgent()
    p = agent.build_prompt("u1", ReflectionTrigger.CHAPTER_COMPLETE)
    assert len(p.questions) == 3
    assert all("?" in q or "?" in q for q in p.questions)


def test_build_prompt_with_subject_adds_fourth():
    agent = ReflectionAgent()
    p = agent.build_prompt(
        "u1", ReflectionTrigger.CHAPTER_COMPLETE, subject="math"
    )
    assert len(p.questions) == 4


def test_build_prompt_unknown_subject_no_extra():
    agent = ReflectionAgent()
    p = agent.build_prompt(
        "u1", ReflectionTrigger.CHAPTER_COMPLETE, subject="unknown_subject"
    )
    assert len(p.questions) == 3


def test_build_prompt_contains_context():
    agent = ReflectionAgent()
    p = agent.build_prompt(
        "u1",
        ReflectionTrigger.SESSION_END,
        context={"chapter": "递归基础"},
        subject="coding",
    )
    assert p.context["chapter"] == "递归基础"
    assert p.context["subject"] == "coding"


def test_record_returns_entry_with_depth():
    agent = ReflectionAgent()
    entry = agent.record(
        student_id="u1",
        trigger=ReflectionTrigger.CHAPTER_COMPLETE,
        answers={
            "Q1": "我在理解递归出口条件时卡住了。",
            "Q2": "如果先处理边界,递归就会很快收敛。",
            "Q3": "今天学到了递归的 2 个关键点:出口和自调用。",
        },
    )
    assert entry.student_id == "u1"
    assert entry.trigger == ReflectionTrigger.CHAPTER_COMPLETE
    assert entry.depth_score() > 0.5  # 三个都答了 + 平均 > 20 字


def test_depth_score_empty_is_zero():
    agent = ReflectionAgent()
    entry = agent.record("u1", ReflectionTrigger.CHAPTER_COMPLETE, answers={})
    assert entry.depth_score() == 0.0


def test_depth_score_one_short_answer():
    agent = ReflectionAgent()
    entry = agent.record(
        "u1",
        ReflectionTrigger.CHAPTER_COMPLETE,
        answers={"Q1": "不会"},  # 1 道,太短
    )
    # n_score=1/3=0.33, len_score=2/20=0.1, 总分 0.33*0.5+0.1*0.5=0.215
    score = entry.depth_score()
    assert 0.0 < score < 0.5


def test_record_cleans_inputs():
    agent = ReflectionAgent()
    entry = agent.record(
        "u1",
        ReflectionTrigger.CHAPTER_COMPLETE,
        answers={"Q1": "  答案带前后空格  "},
    )
    assert entry.answers["Q1"] == "答案带前后空格"


def test_record_truncates_long_answers():
    agent = ReflectionAgent()
    entry = agent.record(
        "u1",
        ReflectionTrigger.CHAPTER_COMPLETE,
        answers={"Q1": "x" * 5000},
    )
    assert len(entry.answers["Q1"]) == 1000  # 截断到 1000


def test_weekly_summary_empty():
    agent = ReflectionAgent()
    summary = agent.weekly_summary("u1", [])
    assert summary["entry_count"] == 0
    assert summary["avg_depth_score"] == 0.0


def test_weekly_summary_with_entries():
    agent = ReflectionAgent()
    e1 = agent.record(
        "u1", ReflectionTrigger.CHAPTER_COMPLETE,
        answers={"Q1": "卡在X", "Q3": "学到了Y"},
    )
    e2 = agent.record(
        "u1", ReflectionTrigger.CHAPTER_COMPLETE,
        answers={"Q1": "卡在Z", "Q3": "学到了W"},
    )
    summary = agent.weekly_summary("u1", [e1, e2])
    assert summary["entry_count"] == 2
    assert 0 < summary["avg_depth_score"] < 1
    assert "卡在X" in summary["common_stuck_points"]


def test_singleton():
    a = get_reflection_agent()
    b = get_reflection_agent()
    assert a is b


def test_to_dict_round_trip():
    agent = ReflectionAgent()
    p = agent.build_prompt(
        "u1", ReflectionTrigger.WEEKLY_DIGEST, context={"week": 7}
    )
    d = p.to_dict()
    assert d["trigger"] == "weekly_digest"
    assert d["context"]["week"] == 7
