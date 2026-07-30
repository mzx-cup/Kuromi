"""Star-Learn 五大 Agent 命名空间。

5 角色命名空间（M2）：
  - QA Agent       (SocraticEvaluatorAgent, 已有) — 苏格拉底式问答
  - Content Agent  (DocumentGeneratorAgent, 已有) — 内容生成
  - Recommend Agent (本模块新增, M2.1) — 可解释推荐
  - Audit Agent    (本模块新增, M2.2) — 防幻觉 + 越狱审核
  - Evaluate Agent (EvaluationAgent, 已有) — 评估

导出建议：新代码请按 5 角色命名空间使用这些符号。
"""
from __future__ import annotations

from app.agents.audit import AuditAgent, AuditResult
from app.agents.critic import CriticAgent, CritiqueResult
from app.agents.recommend import RecommendationResult, RecommendAgent

__all__ = [
    "RecommendAgent",
    "RecommendationResult",
    "AuditAgent",
    "AuditResult",
    "CriticAgent",
    "CritiqueResult",
]