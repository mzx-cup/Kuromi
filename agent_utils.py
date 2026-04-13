from __future__ import annotations

import json
import os
import time
from datetime import datetime
from typing import Any, Optional

from state import (
    ChatMessage,
    ContentType,
    DifficultyLevel,
    DialogueRole,
    EmotionType,
    LearningProfile,
    PathNode,
    StudentState,
)

STATE_STORAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "storage", "state_storage")


def ensure_storage_dir() -> None:
    os.makedirs(STATE_STORAGE_DIR, exist_ok=True)


def save_state(state: StudentState) -> str:
    ensure_storage_dir()
    filename = f"{state.student_id}_{state.context_id}.json"
    filepath = os.path.join(STATE_STORAGE_DIR, filename)
    data = state.to_persist_dict()
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    return filepath


def load_state(student_id: str, context_id: str) -> Optional[StudentState]:
    ensure_storage_dir()
    filename = f"{student_id}_{context_id}.json"
    filepath = os.path.join(STATE_STORAGE_DIR, filename)
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return StudentState.from_persist_dict(data)


def list_student_contexts(student_id: str) -> list[str]:
    ensure_storage_dir()
    contexts = []
    for fname in os.listdir(STATE_STORAGE_DIR):
        if fname.startswith(f"{student_id}_") and fname.endswith(".json"):
            ctx = fname[len(student_id) + 1 : -5]
            contexts.append(ctx)
    return sorted(contexts, reverse=True)


def build_state_from_request(
    student_id: str,
    course_id: str,
    user_input: str,
    context_id: str,
    current_profile: dict[str, Any],
    current_path: list[dict[str, Any]],
    interaction_count: int,
    code_practice_time: int,
    socratic_pass_rate: float,
) -> StudentState:
    existing_state = None
    if context_id:
        existing_state = load_state(student_id, context_id)

    if existing_state:
        existing_state.add_message(DialogueRole.STUDENT, user_input)
        existing_state.updated_at = datetime.now()
        return existing_state

    profile = _build_profile(current_profile, interaction_count, code_practice_time, socratic_pass_rate)
    path = _build_path(current_path)

    state = StudentState(
        student_id=student_id,
        course_id=course_id,
        context_id=context_id or datetime.now().strftime("%Y%m%d%H%M%S%f"),
        profile=profile,
        current_path=path,
    )
    state.add_message(DialogueRole.STUDENT, user_input)
    return state


def _build_profile(
    raw: dict[str, Any],
    interaction_count: int,
    code_practice_time: int,
    socratic_pass_rate: float,
) -> LearningProfile:
    if not raw:
        return LearningProfile(
            interaction_count=interaction_count,
            code_practice_time=code_practice_time,
            socratic_pass_rate=socratic_pass_rate,
        )

    knowledge_mastery = []
    for item in raw.get("knowledgeMastery", []):
        if isinstance(item, dict):
            knowledge_mastery.append(item)

    cognitive = raw.get("cognitiveLevel", "basic")
    if isinstance(cognitive, str):
        try:
            cognitive = DifficultyLevel(cognitive)
        except ValueError:
            cognitive = DifficultyLevel.BASIC

    style = raw.get("learningStyle", "pragmatic")

    return LearningProfile(
        knowledge_mastery=knowledge_mastery,
        learning_style=style,
        learning_progress=raw.get("learningProgress", 0.0),
        learning_preference=raw.get("learningPreference", {}),
        cognitive_level=cognitive,
        learning_goals=raw.get("learningGoals", ["应对考试"]),
        interaction_count=interaction_count,
        socratic_pass_rate=socratic_pass_rate,
        code_practice_time=code_practice_time,
    )


def _build_path(raw: list[dict[str, Any]]) -> list[PathNode]:
    if not raw:
        return [PathNode(topic="大数据导论", status="current", course_id="bigdata", chapter_id="ch1", knowledge_point_id="kp1")]
    nodes = []
    for item in raw:
        if isinstance(item, dict):
            nodes.append(PathNode(
                course_id=item.get("courseId", item.get("course_id", "bigdata")),
                chapter_id=item.get("chapterId", item.get("chapter_id", "")),
                knowledge_point_id=item.get("knowledgePointId", item.get("knowledge_point_id", "")),
                topic=item.get("topic", ""),
                status=item.get("status", "locked"),
                difficulty=item.get("difficulty", "basic"),
            ))
    return nodes


def extract_final_content(state: StudentState) -> str:
    parts = state.metadata.get("final_content_parts", [])
    if parts:
        return "\n\n---\n\n".join(parts)

    for key in ["document_output", "mindmap_output", "exercise_output", "video_output"]:
        data = state.metadata.get(key)
        if data and isinstance(data, dict):
            text = data.get("text_content", "")
            if text:
                return text

    messages = state.get_recent_messages(5)
    for msg in reversed(messages):
        if msg.role == DialogueRole.STUDENT:
            continue
        if msg.content and len(msg.content) > 20:
            return msg.content

    return "系统正在处理你的请求，请稍候..."


def extract_resources(state: StudentState) -> list[dict[str, Any]]:
    resources = state.metadata.get("final_resources", [])
    return resources if isinstance(resources, list) else []


def extract_evaluation(state: StudentState) -> dict[str, Any]:
    return state.metadata.get("evaluation", {
        "interactionCount": state.profile.interaction_count,
        "socraticPassRate": state.profile.socratic_pass_rate,
        "difficultyLevel": state.profile.cognitive_level.value if isinstance(state.profile.cognitive_level, DifficultyLevel) else state.profile.cognitive_level,
        "codePracticeTime": state.profile.code_practice_time,
    })


def format_workflow_logs(logs: list[Any]) -> list[dict[str, Any]]:
    result = []
    for log in logs:
        if hasattr(log, "model_dump"):
            result.append(log.model_dump(mode="json"))
        elif isinstance(log, dict):
            result.append(log)
        else:
            result.append({"raw": str(log)})
    return result


class Timer:
    def __init__(self) -> None:
        self._start: float = 0.0

    def __enter__(self) -> Timer:
        self._start = time.time()
        return self

    def __exit__(self, *args: Any) -> None:
        pass

    @property
    def elapsed_ms(self) -> int:
        return int((time.time() - self._start) * 1000)
