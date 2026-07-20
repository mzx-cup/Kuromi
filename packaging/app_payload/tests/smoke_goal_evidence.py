"""端到端冒烟测试：goal_evidence 校验 + evidence_signals 聚合"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# ── 1) evidence_signals 单元测试 ──
from app.services.analytics_builder import _extract_evidence_signals

analytics = {
    "profile": {
        "knowledge_base": "零基础入门",
        "code_skill": "编程新手",
        "cognitive_style": "实践型",
        "focus_level": "中等专注",
        "learning_goals": ["exam"],
        "weakness": "递归",
        "learning_style": "pragmatic",
        "cognitive_level": "L1·入门级",
    },
    "cockpit": {
        "concept_mastery": 45,
        "thinking_depth": 50,
        "learning_momentum": 60,
        "cognitive_level": "L1·入门级",
    },
    "quizzes": [
        {"quiz_id": "recursion_q1", "score": 4, "total": 10, "passed": False},
        {"quiz_id": "loop_q3", "score": 9, "total": 10, "passed": True},
    ],
    "classrooms": [{"course_id": "intro_2"}],
    "study_stats": {"interactionCount": 12, "codePracticeTime": 60, "completedTasks": 3},
}

es = _extract_evidence_signals(
    analytics["profile"],
    analytics["quizzes"],
    analytics["classrooms"],
    analytics["study_stats"],
    analytics["cockpit"],
)
print("evidence_signals keys:", list(es.keys()))
print("  quiz_ids:", es["quiz_ids"])
print("  classroom_ids:", es["classroom_ids"])
print("  profile_signals:", es["profile_signals"])
print("  interaction_stats.weak_areas:", es["interaction_stats"]["weak_areas"])
print("  interaction_stats.strong_areas:", es["interaction_stats"]["strong_areas"])

assert es["quiz_ids"] == ["recursion_q1", "loop_q3"], f"quiz_ids 错: {es['quiz_ids']}"
assert es["classroom_ids"] == ["intro_2"], f"classroom_ids 错: {es['classroom_ids']}"
assert "knowledge_base=零基础入门" in es["profile_signals"]
assert "recursion_q1" in es["interaction_stats"]["weak_areas"]
assert "loop_q3" in es["interaction_stats"]["strong_areas"]
print("✅ _extract_evidence_signals 单元测试通过")

# 把 evidence_signals 注入 analytics，模拟 build_student_analytics 的完整输出
analytics["evidence_signals"] = es

# ── 2) 校验器 6 个场景 ──
from app.api.learning_path import _validate_and_ground_learning_goals

# 场景 A: 真实证据路径
path_a = [{
    "topic": "递归", "status": "in_progress",
    "learning_goal": "要培养 code_skill 维度的递归实现能力，达到能独立编写递归函数且无语法错误",
    "capability_rationale": "因学生基础为零基础，需要从基础概念开始",
    "targeted_dimensions": ["code_skill", "knowledge_base"],
    "goal_evidence": {
        "quiz_ids": ["recursion_q1"],
        "classroom_ids": ["intro_2"],
        "profile_signals": ["knowledge_base=零基础入门", "code_skill=编程新手"],
        "interaction_stats_refs": {"concept_mastery": 45},
        "rationale_excerpt": "因最近 5 次测验中 3 次未通过递归相关题目"
    }
}]
r_a = _validate_and_ground_learning_goals(path_a, analytics)
print("场景A (真实证据):", r_a)
assert r_a["valid_count"] == 1 and r_a["invalid_count"] == 0, f"场景A 失败: {r_a}"
print("✅ 场景A 通过")

# 场景 B: 假 quiz_id
path_b = [{
    "topic": "X", "status": "in_progress",
    "learning_goal": "要培养 code_skill 维度的 X 能力，达到能... 通过测验",
    "capability_rationale": "因学生基础为零基础",
    "targeted_dimensions": ["code_skill"],
    "goal_evidence": {
        "quiz_ids": ["FAKE_QUIZ_ID_999"],
        "classroom_ids": [],
        "profile_signals": ["knowledge_base=零基础入门"],
        "interaction_stats_refs": {},
        "rationale_excerpt": "..."
    }
}]
r_b = _validate_and_ground_learning_goals(path_b, analytics)
print("场景B (假 ID):", r_b)
assert r_b["valid_count"] == 0 and r_b["invalid_count"] == 1, f"场景B 失败: {r_b}"
assert "FAKE_QUIZ_ID_999" in str(r_b["reason_map"])
print("✅ 场景B 通过")

# 场景 C: 零基础 + 自夸"已掌握基础"矛盾
path_c = [{
    "topic": "Y", "status": "in_progress",
    "learning_goal": "要培养 code_skill 维度的 Y 能力，达到能写代码",
    "capability_rationale": "因学生已掌握基础，基础扎实",
    "targeted_dimensions": ["code_skill"],
    "goal_evidence": {
        "quiz_ids": [], "classroom_ids": [],
        "profile_signals": ["knowledge_base=零基础入门"],
        "interaction_stats_refs": {}, "rationale_excerpt": "..."
    }
}]
r_c = _validate_and_ground_learning_goals(path_c, analytics)
print("场景C (矛盾 rationale):", r_c)
assert r_c["invalid_count"] == 1, f"场景C 失败: {r_c}"
assert any("矛盾" in r for r in r_c["reason_map"]["Y"]), f"场景C 未检出矛盾: {r_c}"
print("✅ 场景C 通过")

# 场景 D: 违规词 "已掌握"
path_d = [{
    "topic": "Z", "status": "in_progress",
    "learning_goal": "要培养 code_skill 维度的 Z 能力",
    "capability_rationale": "因学生基础为零基础",
    "description": "本节点已掌握基础知识",
    "targeted_dimensions": ["code_skill"],
    "goal_evidence": {
        "quiz_ids": [], "classroom_ids": [],
        "profile_signals": ["code_skill=编程新手"],
        "interaction_stats_refs": {}, "rationale_excerpt": "..."
    }
}]
r_d = _validate_and_ground_learning_goals(path_d, analytics)
print("场景D (违规词):", r_d)
assert r_d["invalid_count"] == 1, f"场景D 失败: {r_d}"
reasons_d = r_d["reason_map"]["Z"]
assert any("已掌握" in r for r in reasons_d), f"场景D 未检出违禁词: {reasons_d}"
print("✅ 场景D 通过")

# 场景 E: 缺 goal_evidence
path_e = [{
    "topic": "W", "status": "in_progress",
    "learning_goal": "要培养 code_skill 维度的 W 能力",
    "capability_rationale": "因学生基础为零基础",
    "targeted_dimensions": ["code_skill"],
}]
r_e = _validate_and_ground_learning_goals(path_e, analytics)
print("场景E (缺 evidence):", r_e)
assert r_e["invalid_count"] == 1, f"场景E 失败: {r_e}"
assert any("goal_evidence" in r for r in r_e["reason_map"]["W"]), f"场景E 未检出缺字段: {r_e}"
print("✅ 场景E 通过")

# 场景 F: targeted_dimensions 白名单
path_f = [{
    "topic": "V", "status": "in_progress",
    "learning_goal": "要培养 V 能力",
    "capability_rationale": "因学生基础为零基础",
    "targeted_dimensions": ["math_ability", "code_skill"],
    "goal_evidence": {
        "quiz_ids": [], "classroom_ids": [],
        "profile_signals": ["knowledge_base=零基础入门"],
        "interaction_stats_refs": {}, "rationale_excerpt": "..."
    }
}]
r_f = _validate_and_ground_learning_goals(path_f, analytics)
print("场景F (非白名单维度):", r_f)
assert r_f["invalid_count"] == 1, f"场景F 失败: {r_f}"
assert any("非白名单" in r for r in r_f["reason_map"]["V"]), f"场景F 未检出白名单违规: {r_f}"
print("✅ 场景F 通过")

# 场景 G: 子节点递归
path_g = [{
    "topic": "G", "status": "in_progress",
    "learning_goal": "要培养 code_skill 维度的 G 能力",
    "capability_rationale": "因学生基础为零基础",
    "targeted_dimensions": ["code_skill"],
    "goal_evidence": {
        "quiz_ids": ["recursion_q1"], "classroom_ids": [],
        "profile_signals": ["code_skill=编程新手"],
        "interaction_stats_refs": {}, "rationale_excerpt": "..."
    },
    "children": [
        {
            "topic": "G.1 子节点", "status": "locked",
            "learning_goal": "要培养 code_skill 维度的 G.1 能力",
            "capability_rationale": "因学生基础为零基础",
            "targeted_dimensions": ["code_skill"],
            "goal_evidence": {
                "quiz_ids": ["FAKE_SUB"], "classroom_ids": [],
                "profile_signals": ["code_skill=编程新手"],
                "interaction_stats_refs": {}, "rationale_excerpt": "..."
            },
        }
    ]
}]
r_g = _validate_and_ground_learning_goals(path_g, analytics)
print("场景G (子节点递归):", r_g)
assert r_g["valid_count"] == 1 and r_g["invalid_count"] == 1, f"场景G 失败: {r_g}"
print("✅ 场景G 通过")

print()
print("=== 所有 7 个场景验证通过 ===")
