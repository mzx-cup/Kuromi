"""
Phase 2: 旧 courseData 无 bundle 时, 从 outlines/slides_v2/quiz_data/exercise_data/code_data 现场合成 bundle.components
"""
from typing import Any


def synthesize_bundle_from_legacy(cd: dict) -> dict[str, Any]:
    components: dict[str, Any] = {}

    outlines = cd.get("outlines") or []
    if outlines:
        components["outline"] = {
            "scenes": [
                {
                    "title": o.get("title", ""),
                    "key_points": o.get("key_points") or o.get("points") or [],
                    "description": o.get("description", ""),
                }
                for o in outlines
            ],
            "obg_pbl_mode": (cd.get("metadata") or {}).get("obg_pbl_mode", "obg"),
        }

    slides_v2 = cd.get("slides_v2") or cd.get("slides") or []
    if slides_v2:
        components["ppt"] = {
            "slides": slides_v2,
            "title": (cd.get("title") or "课程") + " PPT",
        }

    questions = []
    if cd.get("quiz_data"):
        questions.extend(cd["quiz_data"])
    if cd.get("exercise_data"):
        questions.extend(cd["exercise_data"])
    if questions:
        components["exercises"] = {"questions": questions, "title": "习题"}

    if cd.get("code_data"):
        raw = cd["code_data"]
        brief = "\n".join(raw) if isinstance(raw, list) else str(raw)
        components["project"] = {"brief": brief, "title": "项目"}

    return {
        "components": components,
        "obg_pbl_mode": (cd.get("metadata") or {}).get("obg_pbl_mode", "obg"),
        "generated_at": (cd.get("metadata") or {}).get("generated_at"),
        "_synthesized": True,
    }
