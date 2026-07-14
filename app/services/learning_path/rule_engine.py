# -*- coding: utf-8 -*-
"""
学习路径节点状态规则引擎

基于客观学习数据即时判定知识点节点的掌握状态。
双轨制中的"硬规则"侧：达到明确阈值即判定完成，不依赖 LLM。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import db as database
from app.core.repository_factory import get_repository_for_user


def _course_progress_repo(user_id):
    """CourseProgressRepository instance routed for this user."""
    return get_repository_for_user(str(user_id), repository_type="course_progress")


# ── 规则配置 ──

@dataclass
class MasteryRuleConfig:
    """节点掌握判定规则配置"""
    # 测验规则
    quiz_avg_threshold: float = 80.0          # 最近 N 次测验平均分阈值
    quiz_min_threshold: float = 60.0           # 单次最低分阈值
    quiz_recent_count: int = 3                 # 最近几次测验
    quiz_weight: float = 0.35                  # 测验在综合分中的权重

    # 代码评测规则
    code_task_required: bool = True            # 是否必须通过代码任务
    code_task_weight: float = 0.30             # 代码任务在综合分中的权重

    # 课堂规则
    classroom_min_progress: float = 90.0       # 课堂最小进度 %
    classroom_quiz_required: bool = True       # 是否要求课堂测验通过
    classroom_weight: float = 0.20             # 课堂在综合分中的权重

    # 学习时长规则
    min_interaction_count: int = 3             # 最少交互次数
    min_study_minutes: int = 15                # 最少学习时长（分钟）
    study_time_weight: float = 0.15            # 学习时长在综合分中的权重

    # 综合判定阈值
    mastery_score_threshold: float = 75.0      # 综合掌握度 >= 此值即完成

    # 双轨制宽松策略：规则完成即算完成
    rule_completes_node: bool = True


DEFAULT_RULE_CONFIG = MasteryRuleConfig()


# ── 规则评估结果 ──

@dataclass
class RuleEvaluationResult:
    node_id: str
    status: str                          # completed | in_progress | locked
    mastery_score: float                 # 0-100
    rule_verified: bool                  # 规则是否判定完成
    completion_source: str | None        # 完成来源
    evidence: dict = field(default_factory=dict)


# ── 数据查询 ──

def _get_quiz_records_for_node(user_id: str | int, node_id: str) -> list[dict]:
    """获取与某知识点节点关联的最近测验记录"""
    # TODO: 当 quiz_records 表增加 node_id 关联后，直接按 node_id 查询
    # 当前阶段：通过 quiz_id 中的知识点名称做模糊匹配
    all_quizzes = database.get_recent_quizzes(user_id, limit=50)
    matched = []
    node_topic = node_id.split(':')[-1].replace('_', '').lower()
    for q in all_quizzes:
        quiz_id = str(q.get('quiz_id', '')).lower().replace('_', '').replace('-', '')
        if node_topic in quiz_id or _topic_similarity(node_topic, quiz_id) > 0.6:
            matched.append(q)
    return matched[:10]


def _get_code_task_for_node(user_id: str | int, node_id: str) -> dict | None:
    """获取与某知识点节点关联的代码任务记录"""
    # TODO: 当代码评测记录表增加 node_id 关联后，直接按 node_id 查询
    # 当前阶段：从 user_stats 的 recent_topics 和 completed_tasks 中推断
    stats = database.get_user_stats(user_id) or {}
    recent_topics = stats.get('recentTopics', [])
    completed_tasks = stats.get('completedTasks', 0)
    node_topic = node_id.split(':')[-1]
    # 简单匹配：如果近期主题包含该知识点，则认为有关联
    for topic in recent_topics:
        if _topic_similarity(node_topic.lower(), topic.lower()) > 0.5:
            return {
                'has_task': True,
                'passed': completed_tasks > 0,  # 简化为有完成任务即算通过
            }
    return None


def _get_classroom_for_node(user_id: str | int, node_id: str) -> dict | None:
    """获取与某知识点节点关联的课堂记录"""
    classrooms = database.get_recent_classrooms(user_id, limit=20)
    node_topic = node_id.split(':')[-1].replace('_', '').lower()
    for c in classrooms:
        course_id = str(c.get('course_id', '')).lower().replace('_', '').replace('-', '')
        if node_topic in course_id or _topic_similarity(node_topic, course_id) > 0.6:
            return c
    return None


def _topic_similarity(a: str, b: str) -> float:
    """简单文本相似度（基于字符交集）"""
    if not a or not b:
        return 0.0
    set_a, set_b = set(a), set(b)
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union else 0.0


def _get_node_study_stats(user_id: str | int, node_id: str) -> dict:
    """获取某知识点的学习统计"""
    course_progress_repo = _course_progress_repo(user_id)
    node = course_progress_repo.get_learning_path_node(user_id, node_id)
    if node:
        return {
            'interaction_count': node.get('interaction_count', 0),
            'study_minutes': 0,  # TODO: 从专注时长记录中统计
        }
    return {'interaction_count': 0, 'study_minutes': 0}


# ── 核心评估 ──

def evaluate_node(
    user_id: str | int,
    node_id: str,
    config: MasteryRuleConfig | None = None,
) -> RuleEvaluationResult:
    """
    基于规则引擎评估单个知识点节点的掌握状态。

    返回 RuleEvaluationResult，包含状态判定和综合掌握度分数。
    """
    config = config or DEFAULT_RULE_CONFIG
    evidence = {}
    course_progress_repo = _course_progress_repo(user_id)

    # 1. 获取现有节点状态
    existing = course_progress_repo.get_learning_path_node(user_id, node_id)
    current_status = existing.get('status', 'locked') if existing else 'locked'

    # 2. 评估各维度
    quiz_score, quiz_evidence = _evaluate_quiz(user_id, node_id, config)
    code_score, code_evidence = _evaluate_code(user_id, node_id, config)
    classroom_score, classroom_evidence = _evaluate_classroom(user_id, node_id, config)
    study_score, study_evidence = _evaluate_study_time(user_id, node_id, config)

    evidence['quiz'] = quiz_evidence
    evidence['code'] = code_evidence
    evidence['classroom'] = classroom_evidence
    evidence['study'] = study_evidence

    # 3. 计算综合掌握度
    mastery_score = (
        quiz_score * config.quiz_weight +
        code_score * config.code_task_weight +
        classroom_score * config.classroom_weight +
        study_score * config.study_time_weight
    )
    mastery_score = round(min(100.0, max(0.0, mastery_score)), 1)

    # 4. 判定状态
    rule_verified = mastery_score >= config.mastery_score_threshold
    completion_source = None

    if rule_verified:
        # 找出主要完成来源
        scores = {
            'quiz_passed': quiz_score,
            'code_graded': code_score,
            'classroom_done': classroom_score,
            'study_time': study_score,
        }
        completion_source = max(scores, key=scores.get)
        status = 'completed'
    elif quiz_score > 30 or code_score > 30 or classroom_score > 30 or study_score > 30:
        status = 'in_progress'
    else:
        status = current_status if current_status != 'completed' else 'in_progress'

    return RuleEvaluationResult(
        node_id=node_id,
        status=status,
        mastery_score=mastery_score,
        rule_verified=rule_verified,
        completion_source=completion_source if rule_verified else None,
        evidence=evidence,
    )


def _evaluate_quiz(user_id, node_id, config) -> tuple[float, dict]:
    """评估测验维度，返回 (分数, 证据)"""
    quizzes = _get_quiz_records_for_node(user_id, node_id)
    if not quizzes:
        return 0.0, {'has_quiz': False, 'reason': '无关联测验记录'}

    recent = quizzes[:config.quiz_recent_count]
    scores = []
    for q in recent:
        total = int(q.get('total', 1))
        score = float(q.get('score', 0))
        pct = (score / total * 100) if total else 0
        scores.append(pct)

    avg = sum(scores) / len(scores) if scores else 0
    min_score = min(scores) if scores else 0

    # 分数计算：平均分占 70%，最低分占 30%
    score = avg * 0.7 + min_score * 0.3

    passed = avg >= config.quiz_avg_threshold and min_score >= config.quiz_min_threshold

    return score, {
        'has_quiz': True,
        'recent_count': len(recent),
        'avg_score': round(avg, 1),
        'min_score': round(min_score, 1),
        'passed': passed,
        'threshold_avg': config.quiz_avg_threshold,
        'threshold_min': config.quiz_min_threshold,
    }


def _evaluate_code(user_id, node_id, config) -> tuple[float, dict]:
    """评估代码任务维度"""
    task = _get_code_task_for_node(user_id, node_id)
    if not task:
        return 0.0, {'has_task': False, 'reason': '无关联代码任务'}

    passed = task.get('passed', False)
    score = 100.0 if passed else 0.0

    return score, {
        'has_task': True,
        'passed': passed,
    }


def _evaluate_classroom(user_id, node_id, config) -> tuple[float, dict]:
    """评估课堂进度维度"""
    classroom = _get_classroom_for_node(user_id, node_id)
    if not classroom:
        return 0.0, {'has_classroom': False, 'reason': '无关联课堂记录'}

    progress = float(classroom.get('progress', 0)) if 'progress' in classroom else 100.0
    status = classroom.get('status', '')
    completed = status == 'completed' or progress >= config.classroom_min_progress

    score = min(100.0, progress * 1.1)  # 进度 90% 以上即满分

    return score, {
        'has_classroom': True,
        'progress': progress,
        'status': status,
        'completed': completed,
        'threshold': config.classroom_min_progress,
    }


def _evaluate_study_time(user_id, node_id, config) -> tuple[float, dict]:
    """评估学习时长维度"""
    stats = _get_node_study_stats(user_id, node_id)
    interaction_count = stats.get('interaction_count', 0)
    study_minutes = stats.get('study_minutes', 0)

    # 交互次数达标给 50 分，学习时长达标给 50 分
    interaction_ok = interaction_count >= config.min_interaction_count
    time_ok = study_minutes >= config.min_study_minutes

    score = 0.0
    if interaction_ok:
        score += 50.0
        # 超额加分
        score += min(30.0, (interaction_count - config.min_interaction_count) * 3)
    else:
        score += (interaction_count / max(1, config.min_interaction_count)) * 50.0

    if time_ok:
        score += 50.0
    else:
        score += (study_minutes / max(1, config.min_study_minutes)) * 50.0

    score = min(100.0, score)

    return score, {
        'interaction_count': interaction_count,
        'study_minutes': study_minutes,
        'interaction_ok': interaction_ok,
        'time_ok': time_ok,
        'threshold_interaction': config.min_interaction_count,
        'threshold_minutes': config.min_study_minutes,
    }


# ── 事件触发即时评估 ──

def on_quiz_submitted(user_id: str | int, quiz_id: str, score: float, total: float) -> RuleEvaluationResult | None:
    """
    学生提交测验后触发节点评估。
    返回评估结果（如果有匹配的节点），否则返回 None。
    """
    # 找到可能关联的节点
    node_id = _infer_node_id_from_quiz(quiz_id)
    if not node_id:
        return None

    result = evaluate_node(user_id, node_id)
    _apply_result(user_id, node_id, result)
    return result


def on_code_graded(user_id: str | int, task_id: str, passed: bool) -> RuleEvaluationResult | None:
    """代码评测通过后触发节点评估"""
    node_id = _infer_node_id_from_task(task_id)
    if not node_id:
        return None

    result = evaluate_node(user_id, node_id)
    _apply_result(user_id, node_id, result)
    return result


def on_classroom_progress(user_id: str | int, course_id: str, progress_pct: float) -> RuleEvaluationResult | None:
    """课堂进度更新后触发节点评估"""
    node_id = _infer_node_id_from_course(course_id)
    if not node_id:
        return None

    result = evaluate_node(user_id, node_id)
    _apply_result(user_id, node_id, result)
    return result


def on_interaction(user_id: str | int, node_id: str | None = None) -> RuleEvaluationResult | None:
    """
    学生与某知识点发生交互后触发评估。
    如果 node_id 明确，直接评估；否则不评估（等更明确的事件）。
    """
    if not node_id:
        return None

    result = evaluate_node(user_id, node_id)
    _apply_result(user_id, node_id, result)
    return result


# ── 应用评估结果到数据库 ──

def _apply_result(user_id, node_id, result: RuleEvaluationResult) -> bool:
    """将规则评估结果保存到数据库"""
    course_progress_repo = _course_progress_repo(user_id)
    existing = course_progress_repo.get_learning_path_node(user_id, node_id)

    # 构建节点数据
    node_data = {
        'node_id': node_id,
        'status': result.status,
        'mastery_score': result.mastery_score,
        'rule_verified': result.rule_verified,
        'completion_source': result.completion_source,
        'evidence_json': result.evidence,
    }

    # 如果节点已存在，保留某些字段
    if existing:
        node_data['node_topic'] = existing.get('node_topic')
        node_data['llm_verified'] = existing.get('llm_verified', 0)
        node_data['interaction_count'] = (existing.get('interaction_count', 0) or 0) + 1
        node_data['last_quiz_score'] = existing.get('last_quiz_score')
        node_data['code_task_passed'] = existing.get('code_task_passed', 0)
        node_data['classroom_progress_pct'] = existing.get('classroom_progress_pct', 0.0)

    success = course_progress_repo.save_learning_path_node(user_id, node_data)
    if success:
        print(f"[RuleEngine] 节点 {node_id} 评估完成: status={result.status}, mastery={result.mastery_score}")
    return success


# ── ID 推断（临时方案，待数据关联完善后替换） ──

def _infer_node_id_from_quiz(quiz_id: str) -> str | None:
    """从测验 ID 推断关联的节点 ID"""
    # TODO: 当 quiz_records 表增加 node_id 字段后，直接查询
    import re
    quiz_clean = quiz_id.lower().replace('_', '').replace('-', '')
    # 简单规则：quiz_id 中包含知识点名称
    return f"topic:{quiz_clean}"


def _infer_node_id_from_task(task_id: str) -> str | None:
    """从任务 ID 推断关联的节点 ID"""
    import re
    task_clean = task_id.lower().replace('_', '').replace('-', '')
    return f"topic:{task_clean}"


def _infer_node_id_from_course(course_id: str) -> str | None:
    """从课程 ID 推断关联的节点 ID"""
    import re
    course_clean = course_id.lower().replace('_', '').replace('-', '')
    return f"topic:{course_clean}"


# ── 全量重新评估（定时任务用） ──

def reevaluate_all_nodes(user_id: str | int) -> list[RuleEvaluationResult]:
    """重新评估该学生的所有节点（用于定时刷新或路径重生成前）"""
    course_progress_repo = _course_progress_repo(user_id)
    nodes = course_progress_repo.get_learning_path_nodes(user_id)
    results = []
    for node in nodes:
        node_id = node.get('node_id')
        if not node_id:
            continue
        result = evaluate_node(user_id, node_id)
        _apply_result(user_id, node_id, result)
        results.append(result)
    return results
