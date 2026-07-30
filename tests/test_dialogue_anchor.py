# -*- coding: utf-8 -*-
"""Tests for dialogue anchor mechanism."""
from app.services.llm.dialogue_anchor import (
    DialogueAnchorStore,
    extract_from_student_reply,
    render_for_prompt,
    get_anchor_store,
)


def test_extract_consensus_chinese():
    text = "我明白了,因为力的方向变了所以加速度也变了。"
    consensus, opens = extract_from_student_reply(text, turn=1)
    assert len(consensus) >= 1
    assert "明白了" in consensus[0]


def test_extract_open_question_chinese():
    text = "我还是不太懂为什么会有反作用力?"
    consensus, opens = extract_from_student_reply(text, turn=1)
    assert len(opens) >= 1


def test_extract_english_anchor():
    text = "Oh I see, that makes sense now."
    consensus, opens = extract_from_student_reply(text, turn=1)
    assert len(consensus) >= 1


def test_extract_empty_text():
    consensus, opens = extract_from_student_reply("", turn=1)
    assert consensus == []
    assert opens == []


def test_extract_long_sentence_skipped():
    text = "我明白了" + "啊" * 300  # > 200 字符,跳过
    consensus, opens = extract_from_student_reply(text, turn=1)
    assert consensus == []


def test_store_add_and_get():
    store = DialogueAnchorStore()
    store.add_consensus("u1", "s1", "力的方向影响加速度", turn=1)
    store.add_open_question("u1", "s1", "为什么反作用力等大反向?", turn=2)
    items = store.get_active("u1", "s1")
    assert len(items) == 2
    assert items[0].kind == "consensus"
    assert items[1].kind == "open_question"
    assert items[1].is_open()


def test_store_resolve_open_question():
    store = DialogueAnchorStore()
    anchor = store.add_open_question("u1", "s1", "为什么?", turn=1)
    assert anchor.is_open()
    store.resolve_open_question("u1", "s1", anchor)
    assert not anchor.is_open()
    assert anchor.kind == "consensus"
    assert anchor.resolved_at is not None


def test_store_isolation_per_session():
    store = DialogueAnchorStore()
    store.add_consensus("u1", "s1", "共识A", turn=1)
    store.add_consensus("u1", "s2", "共识B", turn=1)
    assert len(store.get_active("u1", "s1")) == 1
    assert len(store.get_active("u1", "s2")) == 1
    assert store.get_active("u1", "s1")[0].text == "共识A"


def test_store_clear():
    store = DialogueAnchorStore()
    store.add_consensus("u1", "s1", "X", turn=1)
    store.clear("u1", "s1")
    assert store.get_active("u1", "s1") == []


def test_snapshot_format():
    store = DialogueAnchorStore()
    store.add_consensus("u1", "s1", "共识", turn=1)
    store.add_open_question("u1", "s1", "问题", turn=2)
    snap = store.snapshot("u1", "s1")
    assert snap["user_id"] == "u1"
    assert snap["total"] == 2
    assert len(snap["consensus"]) == 1
    assert len(snap["open_questions"]) == 1


def test_render_for_prompt_includes_both():
    snap = {
        "total": 2,
        "consensus": [{"text": "力的方向影响加速度", "kind": "consensus", "turn": 1}],
        "open_questions": [{"text": "为什么反作用力等大反向?", "kind": "open_question", "turn": 2}],
    }
    rendered = render_for_prompt(snap)
    assert "已确认共识" in rendered
    assert "待解决问题" in rendered
    assert "力的方向" in rendered


def test_render_for_prompt_truncates():
    snap = {
        "total": 1,
        "consensus": [{"text": "X" * 1000, "kind": "consensus", "turn": 1}],
        "open_questions": [],
    }
    rendered = render_for_prompt(snap, max_chars=100)
    assert len(rendered) <= 100
    assert rendered.endswith("...")


def test_render_empty_returns_empty():
    assert render_for_prompt({"total": 0}) == ""


def test_get_anchor_store_singleton():
    a = get_anchor_store()
    b = get_anchor_store()
    assert a is b
