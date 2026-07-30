"""Tests for MasterController 5-role agent registration (M2.3)."""
from __future__ import annotations

from agents import create_default_controller


def test_create_default_controller_registers_five_named_agents():
    """五大角色命名空间必须注册完整：
    qa_agent / content_agent / recommend_agent / audit_agent / evaluate_agent
    """
    controller = create_default_controller()
    expected = {
        "qa_agent",
        "content_agent",
        "recommend_agent",
        "audit_agent",
        "evaluate_agent",
    }
    registered = set(controller._agents.keys())
    missing = expected - registered
    assert not missing, f"missing 5-role agents: {missing}"


def test_recommend_agent_alias_uses_correct_class():
    """recommend_agent 别名必须指向 RecommendAgent 实例。"""
    from app.agents.recommend import RecommendAgent

    controller = create_default_controller()
    agent = controller._agents.get("recommend_agent")
    assert isinstance(agent, RecommendAgent)


def test_audit_agent_alias_uses_correct_class():
    """audit_agent 别名必须指向 AuditAgent 实例。"""
    from app.agents.audit import AuditAgent

    controller = create_default_controller()
    agent = controller._agents.get("audit_agent")
    assert isinstance(agent, AuditAgent)


def test_qa_agent_alias_preserves_backward_compatibility():
    """qa_agent 别名必须保留对老代码（socratic_evaluator）的支持。"""
    controller = create_default_controller()
    # 至少有一个名字指向同一个实例
    qa = controller._agents.get("qa_agent")
    socratic = controller._agents.get("socratic_evaluator")
    assert qa is socratic, "qa_agent must alias to socratic_evaluator"