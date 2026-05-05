#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
课程幻灯片重新生成工具

使用 MiniMax API 重新生成课程的 slides_v2 数据，提升PPT质量。

用法:
    python -m app.services.ppt.regenerate_course <course_id>
    python -m app.services.ppt.regenerate_course --all
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.services.ppt import get_ppt_provider, PPTGenerationRequest

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ppt.regenerate")


STORAGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "storage" / "courses"

DESIGN_STYLES = ["modern", "elegant", "minimal", "bold", "classic"]


async def regenerate_slide(
    provider,
    course_title: str,
    scene: dict,
    scene_idx: int,
) -> dict | None:
    """为一个场景生成幻灯片"""
    content = scene.get("content", [])
    if not content:
        # 从 content_items 或其他字段获取
        content = scene.get("content_items", [])

    # 构造请求
    request = PPTGenerationRequest(
        course_title=course_title,
        scene_title=scene.get("title", f"场景 {scene_idx + 1}"),
        scene_type=scene.get("type", "slide"),
        content=content,
        design_style=DESIGN_STYLES[scene_idx % len(DESIGN_STYLES)],
    )

    result = await provider.generate(request)

    if result.success:
        return result.slide
    else:
        logger.error(f"场景 {scene_idx + 1} 生成失败: {result.error}")
        return None


async def regenerate_course(course_path: Path) -> bool:
    """重新生成单个课程的幻灯片"""
    logger.info(f"处理课程: {course_path.name}")

    try:
        with open(course_path, "r", encoding="utf-8") as f:
            course = json.load(f)
    except Exception as e:
        logger.error(f"读取课程失败 {course_path.name}: {e}")
        return False

    course_title = course.get("title", "未知课程")
    outlines = course.get("outlines", [])

    provider = get_ppt_provider()

    # 为每个 outline 生成幻灯片
    new_slides_v2 = []
    for idx, outline in enumerate(outlines):
        logger.info(f"  生成场景 {idx + 1}/{len(outlines)}: {outline.get('title', '未命名')}")

        # 从 quiz_data 或 exercise_data 获取关联内容
        content = []

        # 查找关联的 quiz 或 exercise
        scene_id = outline.get("id")
        scene_type = outline.get("type", "slide")

        # 从 quiz_data 查找
        if scene_type == "quiz":
            quiz_data = course.get("quiz_data", [])
            for quiz in quiz_data:
                if quiz.get("scene_id") == scene_id or quiz.get("id") == scene_id:
                    questions = quiz.get("questions", [])
                    content = [
                        {
                            "sub_title": f"题目 {i + 1}",
                            "text": q.get("question", "")[:200],  # 截断过长题目
                            "icon": "question",
                            "color_theme": ["blue", "purple", "green", "orange", "yellow"][i % 5],
                        }
                        for i, q in enumerate(questions)
                    ]
                    break

        # 从 exercise_data 查找
        elif scene_type == "exercise":
            exercise_data = course.get("exercise_data", [])
            for ex in exercise_data:
                if ex.get("scene_id") == scene_id or ex.get("id") == scene_id:
                    content = [
                        {
                            "sub_title": ex.get("title", ""),
                            "text": ex.get("description", ""),
                            "icon": "book",
                            "color_theme": "blue",
                        }
                    ]
                    break

        # 普通幻灯片场景 - 使用 key_points 或 description
        if not content:
            key_points = outline.get("key_points", [])
            description = outline.get("description", "")

            if key_points:
                content = [
                    {
                        "sub_title": f"要点 {i + 1}",
                        "text": point,
                        "icon": "star",
                        "color_theme": ["blue", "yellow", "green", "purple", "orange"][i % 5],
                    }
                    for i, point in enumerate(key_points)
                ]
            elif description:
                content = [
                    {
                        "sub_title": outline.get("title", ""),
                        "text": description,
                        "icon": "book",
                        "color_theme": "blue",
                    }
                ]

        # 生成幻灯片
        request = PPTGenerationRequest(
            course_title=course_title,
            scene_title=outline.get("title", f"场景 {idx + 1}"),
            scene_id=str(outline.get("id", idx + 1)),
            scene_type=scene_type,
            content=content,
            design_style=DESIGN_STYLES[idx % len(DESIGN_STYLES)],
        )

        result = await provider.generate(request)

        if result.success and result.slide:
            # 只保留 elements，包装成 slides_v2 格式
            new_slides_v2.append(result.slide)
            logger.info(f"    ✓ 生成成功 ({len(result.slide.get('elements', []))} 元素)")
        else:
            logger.warning(f"    ✗ 生成失败: {result.error if result else 'unknown'}")
            # 添加空幻灯片占位
            new_slides_v2.append(
                {
                    "id": f"slide-{idx}",
                    "viewportSize": {"width": 1000, "height": 562.5},
                    "elements": [],
                }
            )

        # 避免请求过快
        await asyncio.sleep(0.5)

    # 更新课程数据
    course["slides_v2"] = new_slides_v2

    # 保存回原文件
    backup_path = course_path.with_suffix(".json.bak")
    course_path.rename(backup_path)

    try:
        with open(course_path, "w", encoding="utf-8") as f:
            json.dump(course, f, ensure_ascii=False, indent=2)
        logger.info(f"✓ 课程已更新: {course_path.name}")
        backup_path.unlink()  # 删除备份
        return True
    except Exception as e:
        logger.error(f"保存课程失败: {e}")
        backup_path.rename(course_path)  # 恢复备份
        return False


async def main():
    if len(sys.argv) < 2:
        print("用法: python -m app.services.ppt.regenerate_course <course_id> | --all")
        return

    arg = sys.argv[1]

    if arg == "--all":
        # 处理所有课程
        courses = list(STORAGE_DIR.glob("*.json"))
        logger.info(f"找到 {len(courses)} 个课程文件")

        for course_path in courses:
            await regenerate_course(course_path)
            await asyncio.sleep(1)  # 避免请求过快

    else:
        # 处理指定课程
        course_path = STORAGE_DIR / f"{arg}.json"
        if not course_path.exists():
            course_path = STORAGE_DIR / f"course_{arg}.json"

        if not course_path.exists():
            logger.error(f"课程文件不存在: {arg}")
            return

        await regenerate_course(course_path)


if __name__ == "__main__":
    asyncio.run(main())
