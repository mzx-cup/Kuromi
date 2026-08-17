# -*- coding: utf-8 -*-
"""Seed ``chapters.lecture`` + ``chapters.mindmap`` for all bound 课程中心 courses.

Why this script exists
======================

``course-learn.html`` asks ``/api/courses/courses/{cid}/subchapters/{sid}/content``
for four pieces:

    transcript, concepts, mindMap, exercises

The backend ``app/services/course_learn_content.get_subchapter_content()`` has
this priority order:

    0. parent chapter has seeded lecture / mindmap  →  render directly (FAST)
    1. subchapter has its own transcript            →  use it
    2. Bilibili subtitles                            →  fetch + parse
    3. LLM skeleton generation                       →  fallback

Production problem: in this environment the LLM call takes ~30s per request,
which causes the UI to render the empty placeholder before data arrives.
Seeding the parent chapter's lecture/mindmap JSON makes the service take
priority-0 path: ~5ms response with structured content (no LLM, no subtitle
fetch).

What this script writes
=======================

For every chapter of every bound course (``Course.bvid != ''``) we generate:

    chapter.lecture = {
        "blocks": [
            {"kind": "h2", "text": "本节概览"},
            {"kind": "p",  "text": "..."},
            {"kind": "list", "items": ["..."]},
            {"kind": "callout", "text": "...", "tone": "tip"},
            {"kind": "summary", "text": "..."},
        ]
    }

    chapter.mindmap = {
        "nodes": [
            {"id": "root", "label": "本章核心", "level": 0},
            {"id": "n1",   "label": "概念",     "level": 1},
            {"id": "n1a",  "label": "...",     "level": 2},
            ...
        ],
        "edges": [
            {"from": "root", "to": "n1"},
            {"from": "n1",   "to": "n1a"},
            ...
        ]
    }

These two shapes are exactly what
``course_learn_content._build_from_seeded()`` already understands.

Re-running is idempotent: chapters that already have lecture/mindmap are
skipped unless ``--force``.

CLI
===

    python scripts/seed_course_learn_content.py            # seed all bound
    python scripts/seed_course_learn_content.py --force    # re-seed all
    python scripts/seed_course_learn_content.py --course-id course_xxx
                                                            # single course
    python scripts/seed_course_learn_content.py --dry-run  # preview, no write
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import re
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import selectinload  # noqa: E402

from app.core.database import get_sessionmaker  # noqa: E402
from app.models.course import Chapter, Course, SubChapter  # noqa: E402

logger = logging.getLogger("seed_content")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
)


# ── 主题识别 ──
# 课程标题命中关键词 → 给出该主题的"通用子分支".
# 这些分支会再叠加 chapter.title 推导出的本节专属要点.

_TOPIC_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("python", ("Python 解释器", "变量与数据类型", "控制流", "函数与模块",
                "面向对象", "常用标准库", "异常处理", "文件与 I/O")),
    ("java",   ("JVM 与字节码", "变量与数据类型", "面向对象", "集合框架",
                "异常处理", "多线程", "I/O 流", "泛型与反射")),
    ("rust",   ("所有权与借用", "变量与类型", "模式匹配", "错误处理",
                "Trait 与泛型", "并发模型", "生命周期", "模块系统")),
    ("c 语言", ("编译流程", "变量与数据类型", "运算符与表达式", "控制流",
                "函数与指针", "数组与字符串", "结构体", "文件 I/O")),
    ("c指针",  ("指针概念", "指针运算", "指针与数组", "指针与函数",
                "二级指针", "函数指针", "void * 与类型转换", "常见陷阱")),
    ("数据结构", ("数组与链表", "栈与队列", "树与二叉树", "图",
                 "堆与优先队列", "哈希表", "排序算法", "复杂度分析")),
    ("算法",   ("时间复杂度", "空间复杂度", "排序", "搜索", "递归",
                "动态规划", "贪心", "分治")),
    ("冒泡",   ("排序思想", "比较与交换", "内层循环", "外层循环",
                "稳定性", "时间复杂度", "优化标志位", "适用场景")),
    ("redis",  ("内存模型", "字符串与 SDS", "字典与哈希表", "跳表",
                "持久化 RDB", "持久化 AOF", "主从复制", "集群与分片")),
    ("网络",   ("OSI 七层", "TCP/IP 四层", "HTTP 协议", "HTTPS 与 TLS",
                "DNS 解析", "三次握手与四次挥手", "滑动窗口", "拥塞控制")),
    ("网络安全", ("CIA 三要素", "常见攻击", "加密算法", "认证与授权",
                  "防火墙", "渗透测试", "漏洞修复", "安全编码")),
    ("操作系统", ("进程与线程", "内存管理", "文件系统", "进程调度",
                  "同步与互斥", "死锁", "虚拟内存", "I/O 管理")),
    ("数据库", ("关系模型", "SQL 语法", "索引与 B+ 树", "事务与 ACID",
                "锁机制", "范式理论", "查询优化", "备份与恢复")),
    ("傅里叶", ("周期函数", "三角函数正交性", "傅里叶级数", "频谱",
                "复数形式", "傅里叶变换", "卷积定理", "应用场景")),
    ("机器学习", ("监督学习", "无监督学习", "损失函数", "梯度下降",
                  "过拟合与正则化", "神经网络", "模型评估", "特征工程")),
    ("前端",   ("HTML 语义", "CSS 布局", "JavaScript 基础", "DOM 与事件",
                "异步编程", "工程化", "框架原理", "性能优化")),
]


def _detect_topic(course_title: str) -> tuple[str, tuple[str, ...]]:
    """根据课程标题识别主题, 返回 (主题标签, 子分支列表)."""
    t = (course_title or "").lower()
    for keyword, branches in _TOPIC_KEYWORDS:
        if keyword in t or keyword in (course_title or ""):
            return keyword, branches
    # 通用兜底
    return "通用", ("核心概念", "关键步骤", "典型示例", "常见误区",
                    "工具与方法", "拓展思考")


def _strip_order_prefix(title: str) -> str:
    """去掉章节标题里的「第X章/第X节/X.Y」前缀."""
    if not title:
        return ""
    cleaned = re.sub(r"^第\s*[一二三四五六七八九十百\d]+\s*[章节课]\s*[:：、]?\s*",
                     "", title).strip()
    cleaned = re.sub(r"^\d+(\.\d+)*\s*[:：、.]?\s*", "", cleaned).strip()
    return cleaned or title


# ── lecture blocks 生成 ──

def _build_lecture_blocks(course_title: str, chapter_title: str,
                          sub_branches: tuple[str, ...]) -> list[dict]:
    """根据课程 + 章节标题, 拼出 4-6 条 lecture blocks."""
    topic_label, _ = _detect_topic(course_title)
    clean = _strip_order_prefix(chapter_title)

    # 取 sub_branches 中与章节名相关的 3-4 条, 或者用通用结构
    matched = [
        b for b in sub_branches
        if any(ch in b for ch in (clean[:4], clean[-3:])) and clean
    ]
    if not matched or len(matched) < 3:
        matched = list(sub_branches[:4])

    blocks: list[dict] = [
        {"kind": "h2", "text": f"本节概览：{clean}"},
        {"kind": "p",
         "text": (f"本节属于《{course_title}》，主题是「{clean}」。"
                  f"我们将围绕 {len(matched)} 个核心要点展开："
                  f"{'、'.join(matched[:3])} 等。"
                  "建议先通读概览，再带着问题看示例，最后通过练习巩固。")},
        {"kind": "list", "items": [
            f"{i + 1}. {b}：理解它在「{clean}」中的作用与边界。"
            for i, b in enumerate(matched)
        ]},
        {"kind": "h2", "text": "学习重点"},
        {"kind": "callout",
         "tone": "tip",
         "text": (f"核心建议：先看「{matched[0]}」建立直觉，"
                  f"再看「{matched[1] if len(matched) > 1 else matched[0]}」"
                  "理解具体做法；不要只看不练。")},
        {"kind": "h2", "text": "典型误区"},
        {"kind": "list", "items": [
            "把「会用」当成「懂原理」——遇到变体题就懵。",
            "跳过练习，只看不写——记忆无法形成长期巩固。",
            "忽略边界条件（如空值、负数、极端输入）——代码上线就崩。",
        ]},
        {"kind": "summary",
         "text": (f"小结：本节「{clean}」的关键在于掌握 "
                  f"{len(matched)} 个核心要点（{matched[0]}"
                  f"{' / ' + matched[1] if len(matched) > 1 else ''}"
                  f"{' / ' + matched[2] if len(matched) > 2 else ''}"
                  "），并能用自己的话复述。")},
    ]
    return blocks


# ── mindmap nodes / edges 生成 ──

def _build_mindmap(course_title: str, chapter_title: str,
                   sub_branches: tuple[str, ...]) -> dict:
    """构造 nodes + edges 的 mindmap JSON."""
    clean = _strip_order_prefix(chapter_title)[:12] or "本章核心"
    topic_label, _ = _detect_topic(course_title)
    root_label = f"{topic_label}·{clean}"

    nodes: list[dict] = [{"id": "root", "label": root_label, "level": 0}]

    # 一级节点: 4 个 (固定结构, 来自章节的"概念/步骤/示例/误区"四个面)
    first_level = [
        ("核心概念", "concept"),
        ("关键步骤", "step"),
        ("典型示例", "example"),
        ("常见误区", "pitfall"),
    ]
    edges: list[dict] = []

    for idx, (name, kind) in enumerate(first_level, start=1):
        nid = f"n{idx}"
        nodes.append({"id": nid, "label": name, "level": 1})
        edges.append({"from": "root", "to": nid})

        # 每个一级挂 2 个叶子
        for leaf_idx, leaf_label in enumerate(
            _leaves_for(kind, sub_branches, idx), start=1,
        ):
            cid = f"n{idx}_{leaf_idx}"
            nodes.append({"id": cid, "label": leaf_label, "level": 2})
            edges.append({"from": nid, "to": cid})

    return {"nodes": nodes, "edges": edges}


def _leaves_for(kind: str, sub_branches: tuple[str, ...], offset: int) -> list[str]:
    """给一个一级节点配 2 个叶子标签."""
    n = len(sub_branches) or 1
    a = sub_branches[offset % n]
    b = sub_branches[(offset + 1) % n]
    if kind == "concept":
        return [f"{a} 的定义", f"{b} 的作用"]
    if kind == "step":
        return [f"步骤 1：{a}", f"步骤 2：{b}"]
    if kind == "example":
        return [f"示例：{a}", f"反例：{b}"]
    # pitfall
    return [f"{a} 的常见错法", f"{b} 的边界"]


# ── 写入 ──

async def seed_one_course(session, course_id: str, *, force: bool) -> tuple[int, int]:
    """给一个课程的所有 chapter 写入 lecture + mindmap.

    Returns: (chapters_seeded, chapters_skipped)
    """
    res = await session.execute(
        select(Course).where(Course.id == course_id)
        .options(selectinload(Course.chapters))
    )
    course = res.scalar_one_or_none()
    if not course:
        logger.warning("[%s] 课程不存在", course_id)
        return 0, 0

    _, sub_branches = _detect_topic(course.title)
    seeded = skipped = 0
    for ch in course.chapters:
        if ch.lecture and ch.mindmap and not force:
            skipped += 1
            continue
        ch.lecture = {
            "blocks": _build_lecture_blocks(course.title, ch.title, sub_branches),
        }
        ch.mindmap = _build_mindmap(course.title, ch.title, sub_branches)
        ch.is_demo = True
        ch.demo_version = "v1"
        seeded += 1

    if seeded:
        await session.commit()
    return seeded, skipped


async def list_bound_courses(session) -> list[Course]:
    res = await session.execute(
        select(Course).where(Course.bvid != "").order_by(Course.id)
    )
    return list(res.scalars())


async def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--course-id", default="", help="只处理单个 course_id")
    ap.add_argument("--force", action="store_true", help="覆盖已有 lecture/mindmap")
    ap.add_argument("--dry-run", action="store_true", help="预览, 不写入")
    args = ap.parse_args()

    sm = get_sessionmaker()
    async with sm() as session:
        if args.course_id:
            courses = [(await session.execute(
                select(Course).where(Course.id == args.course_id)
            )).scalar_one_or_none()]
            courses = [c for c in courses if c]
        else:
            courses = await list_bound_courses(session)

        if not courses:
            sys.exit("No bound courses to seed.")

        total_seeded = total_skipped = 0
        for course in courses:
            if args.dry_run:
                res = await session.execute(
                    select(Chapter).where(Chapter.course_id == course.id)
                )
                n_ch = len(res.scalars().all())
                print(f"[DRY ] {course.id} | {course.title} | {n_ch} chapters",
                      flush=True)
                continue

            seeded, skipped = await seed_one_course(
                session, course.id, force=args.force,
            )
            total_seeded += seeded
            total_skipped += skipped
            status = "OK  " if seeded else "SKIP"
            print(f"[{status}] {course.id} | {course.title} | "
                  f"seed={seeded} skip={skipped}", flush=True)

        if not args.dry_run:
            print(flush=True)
            print(f"汇总: 写入 {total_seeded} 个 chapter, 跳过 {total_skipped} 个",
                  flush=True)


if __name__ == "__main__":
    asyncio.run(main())