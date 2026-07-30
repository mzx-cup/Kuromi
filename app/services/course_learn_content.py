"""
为课程学习页 (`course-learn.html`) 提供的子章节学习内容生成器.

前端 GET /api/courses/courses/{id}/subchapters/{sid}/content 会拿到四件套:
    - transcript  : 讲解文本 (HTML 片段, 含标题/段落/要点列表)
    - concepts    : 关键概念列表 [{term, level, definition, example}]
    - mindMap     : 思维导图根节点 {name, children: [...]}
    - exercises   : 选择/判断/填空题 [{type, question, options?, answer, explanation}]

数据源策略:
    1. 子章节自带 transcript (seeder / 手工录入)
    2. B 站字幕 (player/v2 → HTML scrape → 视频元信息) — 见 app.services.bilibili.fetch_subtitles
    3. 实在没原文: 允许 LLM 基于"课程标题 + 章节标题 + 课程简介"猜一份骨架,
       标记 `is_skeleton=True` 让前端 UI 可以提示"待字幕就绪后自动完善".

为了让结果对前端持久可见、且减少重复 token 消耗,
本服务会对生成结果做 in-process 缓存 (key = course_id|subchapter_id|source_hash).
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from typing import Any

from llm_stream import call_llm_async
from app.services.bilibili import fetch_subtitles

logger = logging.getLogger("starlearn.course_learn_content")


# ── 进程内缓存 ──
# key: "course|sub|source_hash" -> {transcript, concepts, mindMap, exercises, is_skeleton, ...}
_CACHE: dict[str, dict[str, Any]] = {}

_TTL_SECONDS = 6 * 3600


def _cache_key(course_id: str, subchapter_id: str, subtitle_hash: str) -> str:
    return f"{course_id}|{subchapter_id}|{subtitle_hash}"


def _source_hash(subs: list[dict[str, Any]], existing_transcript: str) -> str:
    if subs:
        h = hashlib.md5()
        for s in subs:
            h.update(str(s.get("from", 0)).encode())
            h.update(b"|")
            h.update((s.get("content") or "").encode())
            h.update(b";")
        return "subs:" + h.hexdigest()[:10]
    if existing_transcript:
        return "tx:" + hashlib.md5(existing_transcript.encode()).hexdigest()[:10]
    return "skeleton:0"


def _subtitle_hash(subs: list[dict[str, Any]]) -> str:
    if not subs:
        return "no-subs"
    h = hashlib.md5()
    for s in subs:
        h.update(str(s.get("from", 0)).encode())
        h.update(b"|")
        h.update((s.get("content") or "").encode())
        h.update(b";")
    return h.hexdigest()[:10]


def _plain_text(subtitles: list[dict[str, Any]], max_lines: int = 80) -> str:
    """把 B 站字幕数组转成紧凑文本, 最多 max_lines 行."""
    out = []
    for s in subtitles[:max_lines]:
        c = (s.get("content") or "").strip()
        if c:
            out.append(c)
    return "\n".join(out)


# ── 主入口 ──

async def get_subchapter_content(
    course: dict[str, Any],
    chapter: dict[str, Any] | None,
    subchapter: dict[str, Any],
    *,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """返回前端需要的四件套.

    任何一步失败都返回空骨架 (前端兜底) 而不是抛 500.
    """
    if not subchapter:
        return _empty()

    course_id = _get_attr(course, "id") or ""
    sub_id = _get_attr(subchapter, "id") or ""
    bvid = (_get_attr(subchapter, "bvid") or "") or (_get_attr(course, "bvid") or "")

    # 0. 如果父章节的 lecture/mindmap 已由 demo seeder 写入, 直接使用 — 不调 LLM
    lecture_obj = _get_attr(chapter, "lecture") if chapter else None
    mindmap_obj = _get_attr(chapter, "mindmap") if chapter else None

    # 1. 优先使用已存在的 transcript (手工录入 / demo seeder)
    existing_transcript = (_get_attr(subchapter, "transcript") or "").strip()

    # 1a. 如果没有手工 transcript 但父章节有 seeded lecture blocks, 渲染成 HTML
    if not existing_transcript and isinstance(lecture_obj, dict):
        existing_transcript = _render_lecture_html(lecture_obj)

    # 2. 拉 B 站字幕 (按 player/v2 → HTML scrape → 视频元信息 → yt-dlp+Whisper 顺序)
    subtitles: list[dict[str, Any]] = []
    subtitle_source = ""
    if not existing_transcript and bvid:
        try:
            raw_subs = fetch_subtitles(bvid) or []
            for raw in raw_subs:
                if raw.get("content"):
                    subtitles = raw["content"]
                    subtitle_source = raw.get("source", "cc")
                    break
        except Exception as exc:
            logger.warning("拉取 B 站字幕失败 bvid=%s: %s", bvid, exc)

        # 兜底: 真没有字幕时, 走 yt-dlp+Whisper ASR
        if not subtitles and bvid:
            try:
                from app.services.bilibili_audio_asr import (
                    _is_enabled as _asr_enabled, transcribe_bilibili_video,
                )
                if _asr_enabled():
                    cid = _get_attr(subchapter, "cid", 0) or 0
                    if not cid:
                        # 用公开接口自动建 cookie-injected client + 跑校验
                        try:
                            from app.services.bilibili import resolve_aid_cid
                            v = resolve_aid_cid(bvid)
                            cid = v[1] if v else 0
                        except Exception:
                            cid = 0
                    if cid:
                        asr_result = await transcribe_bilibili_video(bvid, cid)
                        for raw in asr_result:
                            if raw.get("content"):
                                subtitles = raw["content"]
                                subtitle_source = "asr"
                                break
            except Exception as exc:
                logger.warning("yt-dlp+Whisper 兜底失败 bvid=%s: %s", bvid, exc)

    cache_key = _cache_key(course_id, sub_id,
                           _source_hash(subtitles, existing_transcript))

    if not force_refresh and cache_key in _CACHE:
        cached = dict(_CACHE[cache_key])
        cached["_cache_hit"] = True
        return cached

    sub_title = _get_attr(subchapter, "title") or ""
    course_title = _get_attr(course, "title") or ""
    chapter_title = (_get_attr(chapter, "title") if chapter else "") or ""
    course_desc = _get_attr(course, "description") or ""

    # ── 快速通道: 父章节已经由 demo seeder 写好 lecture + mindmap ──
    # 直接用 seeder 内容拼四件套, 不调 LLM
    if isinstance(lecture_obj, dict) or isinstance(mindmap_obj, dict):
        seeded_content = _build_from_seeded(lecture_obj, mindmap_obj, sub_title)
        if seeded_content.get("transcript") or seeded_content.get("mindMap"):
            seeded_content["is_skeleton"] = False
            seeded_content["source"] = "demo_seeder"
            seeded_content["_cache_hit"] = False
            # 缓存以便后续重复请求秒回
            _CACHE[cache_key] = seeded_content
            return seeded_content

    # 3. 让 LLM 生成 — 即使没有字幕, 也基于课程标题 + 章节标题 + 简介
    #    生成"骨架"内容 (is_skeleton=True), 避免空骨架
    base_text = existing_transcript or _plain_text(subtitles)
    is_skeleton = not bool(base_text.strip())

    try:
        content = await _generate_all(
            course_title=course_title,
            chapter_title=chapter_title,
            subchapter_title=sub_title,
            course_desc=course_desc,
            base_text=base_text,
            is_skeleton=is_skeleton,
            subtitle_source=subtitle_source,
        )
    except Exception as exc:
        logger.warning("子章节内容生成失败 sub=%s: %s", sub_id, exc)
        return _empty(note=f"AI 生成失败: {exc}")

    content["is_skeleton"] = is_skeleton
    content["source"] = (
        "transcript" if existing_transcript
        else ("bilibili:" + subtitle_source if subtitle_source else "skeleton")
    )
    _CACHE[cache_key] = content
    return dict(content, _cache_hit=False)


def _empty(note: str = "") -> dict[str, Any]:
    return {
        "transcript": "",
        "concepts": [],
        "mindMap": None,
        "exercises": [],
        "note": note,
        "is_skeleton": True,
        "source": "none",
        "_cache_hit": False,
    }


# ── LLM 调用 ──

_GEN_SYSTEM = (
    "你是一名严谨的 K12 教师助手, 你必须只基于【参考资料】提炼内容."
    "参考资料为空时, 请根据课程标题/章节标题/课程简介**合理推测**该小节可能涵盖的结构, "
    "并在 transcript 顶部添加提示【本节为 AI 基于标题生成的骨架讲义, 待字幕就绪后会自动完善】。"
    "所有数据点的题目 answer / concept definition 必须能由参考资料或合理推断支撑."
    "输出必须是合法 JSON, 顶层为一个对象, 不要任何解释或 markdown 代码块。"
)

_GEN_USER_TEMPLATE = """【参考资料】(字幕/讲义/视频元信息, 可能为空):
\"\"\"
{base}
\"\"\"

【课程信息】
- 课程: {course_title}
- 章节: {chapter_title}
- 小节: {sub_title}
- 课程简介: {course_desc}
- 资料状态: {source_state}

请返回如下 JSON 结构的合法对象 (无 markdown, 无前后缀):
{{
  "transcript": "<教学讲义 HTML 片段, 用 <h4> 表示小标题, <p> 表示段落, <ol>/<ul> 表示要点, 长度 200-500 字, 只基于参考资料>",
  "concepts": [
    {{ "term": "概念名", "level": "core|basic|advanced", "definition": "一句话定义", "example": "可选, 一个例子" }}
  ],
  "mindMap": {{
    "name": "本节核心: {sub_title}",
    "children": [
      {{ "name": "分支1", "children": [{{"name": "细节"}}] }}
    ]
  }},
  "exercises": [
    {{ "type": "choice|bool|fill", "question": "题干",
       "options": ["A...","B...","C...","D..."],
       "answer": "choice=index(int)/bool=true或false/fill=字符串",
       "explanation": "解析一句话" }}
  ]
}}

约束:
1. concepts 3-6 条, 至少 1 条 core, 用词贴近资料/标题
2. mindMap 必须有; 2-4 个一级节点, 每个一级节点 2-3 个细节; 根节点 name ≤ 12 字
3. exercises 3-5 道, 必须包含 1 道 choice + 1 道 bool + 1 道 fill
4. 即便参考资料为空, 也按课程标题/章节标题给出**粗略但合理**的结构 (标记为 skeleton)
"""


async def _generate_all(
    course_title: str,
    chapter_title: str,
    subchapter_title: str,
    course_desc: str,
    base_text: str,
    *,
    is_skeleton: bool = False,
    subtitle_source: str = "",
) -> dict[str, Any]:
    # 截断避免超过 LLM 上限, 8k tokens ~ 12-15k 字符
    if len(base_text) > 9000:
        base_text = base_text[:9000] + "\n...(已截断)"

    source_state = (
        "骨架生成(无字幕/讲义)" if is_skeleton
        else f"基于字幕({subtitle_source or 'cc'})"
    )

    user_prompt = _GEN_USER_TEMPLATE.format(
        base=base_text or "(无参考资料)",
        course_title=course_title or "(未命名课程)",
        chapter_title=chapter_title or "(未分类章节)",
        sub_title=subchapter_title or "(本节)",
        course_desc=course_desc or "(无)",
        source_state=source_state,
    )

    raw = await call_llm_async(
        system_prompt=_GEN_SYSTEM,
        user_prompt=user_prompt,
        temperature=0.4,
    )

    data = _safe_json(raw)
    if not isinstance(data, dict):
        logger.warning("LLM 返回非 dict: %r", raw[:200])
        return _empty(note="AI 返回格式异常, 已重试请稍后再来。")

    transcript = data.get("transcript") or ""
    transcript = _strip_md(transcript)

    # 骨架场景下, 在 transcript 头部插入可识别提示
    if is_skeleton and transcript:
        skeleton_banner = (
            '<div class="cl-transcript-skeleton" '
            'style="background:rgba(251,191,36,.08);border-left:3px solid #fbbf24;'
            'padding:10px 14px;border-radius:6px;margin:0 0 14px;font-size:12.5px;'
            'color:#fbbf24">⚠ 本节为 AI 基于标题生成的骨架讲义, '
            '待字幕/讲义就绪后将自动完善</div>'
        )
        transcript = skeleton_banner + transcript

    concepts = data.get("concepts") or []
    concepts = [c for c in concepts if isinstance(c, dict) and c.get("term")]
    for c in concepts:
        c.setdefault("definition", "")
        c.setdefault("level", "basic")
        if c["level"] not in ("core", "basic", "advanced"):
            c["level"] = "basic"

    mindmap = data.get("mindMap")
    if not isinstance(mindmap, dict) or not mindmap.get("name"):
        # 骨架兜底: 用章节名 + 几个通用分支
        mindmap = {
            "name": (subchapter_title or "本节核心")[:12],
            "children": [
                {"name": "核心概念", "children": []},
                {"name": "关键步骤", "children": []},
                {"name": "常见误区", "children": []},
            ],
        }

    exercises = data.get("exercises") or []
    exercises = [e for e in exercises if isinstance(e, dict) and e.get("question")]
    for e in exercises:
        e.setdefault("type", "choice")
        if e["type"] not in ("choice", "bool", "fill"):
            e["type"] = "choice"
        if e["type"] == "choice":
            opts = e.get("options") or []
            if not isinstance(opts, list) or len(opts) < 2:
                continue
            e["options"] = [str(o) for o in opts]
            try:
                e["answer"] = int(e.get("answer", 0))
            except Exception:
                e["answer"] = 0
        elif e["type"] == "bool":
            e["answer"] = bool(e.get("answer", False))
        else:
            e["answer"] = str(e.get("answer", ""))
        e.setdefault("explanation", "")

    # 骨架兜底: 至少保证 1 道题, 不让练习面板完全空
    if is_skeleton and not exercises:
        exercises = [{
            "type": "fill",
            "question": f"请用一句话描述本节(《{subchapter_title or '本节'}》)最核心的知识点",
            "answer": "(自由作答, 由系统/教师点评)",
            "explanation": "本节目前缺少字幕/讲义, 题目为开放题;字幕就绪后将自动替换为标准练习。",
        }]

    return {
        "transcript": transcript,
        "concepts": concepts,
        "mindMap": mindmap,
        "exercises": exercises,
    }


def _strip_md(text: str) -> str:
    """去掉包裹的 ```html ...``` 等 markdown 代码块."""
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


# ── 演示课 seeder 适配 ──
#
# demo_seeder 在 chapter.lecture / chapter.mindmap 字段里塞了"ready"的数据.
# 本模块把这两份 JSON 转成前端期望的 transcript / mindMap / concepts / exercises.

_KIND_TAG = {
    "h1": "h4",
    "h2": "h4",
    "h3": "h4",
    "p": "p",
    "code": "pre",
    "list": "ul",
    "callout": "blockquote",
    "quote": "blockquote",
    "summary": "p",
    "image": "img",
    "table": "pre",
}


def _render_lecture_html(lecture: dict[str, Any]) -> str:
    """把 demo_seeder 写入的 lecture.blocks 渲染成 transcript HTML."""
    blocks = lecture.get("blocks") or []
    if not blocks:
        return ""

    parts: list[str] = []
    for blk in blocks:
        kind = blk.get("kind")
        if kind == "list":
            ordered = bool(blk.get("ordered"))
            tag = "ol" if ordered else "ul"
            items = blk.get("items") or []
            if items:
                li_html = "".join(f"<li>{_escape(str(x))}</li>" for x in items)
                parts.append(f"<{tag}>{li_html}</{tag}>")
        elif kind in ("h1", "h2", "h3"):
            text = blk.get("text") or ""
            parts.append(f"<h4>{_escape(text)}</h4>")
        elif kind == "p":
            text = blk.get("text") or ""
            parts.append(f"<p>{_escape(text)}</p>")
        elif kind == "code":
            lang = blk.get("lang") or ""
            code = blk.get("text") or ""
            parts.append(
                f"<pre><code class=\"lang-{_escape(lang)}\">"
                f"{_escape(code)}</code></pre>"
            )
        elif kind == "callout":
            text = blk.get("text") or ""
            tone = blk.get("tone") or "info"
            parts.append(
                f"<blockquote class=\"callout callout-{_escape(tone)}\">"
                f"<p>{_escape(text)}</p></blockquote>"
            )
        elif kind == "summary":
            text = blk.get("text") or ""
            parts.append(f"<p><strong>小结：</strong>{_escape(text)}</p>")
        elif kind == "quote":
            text = blk.get("text") or ""
            parts.append(f"<blockquote><p>{_escape(text)}</p></blockquote>")
        # 其他类型(callout, image, table)按情况忽略,避免渲染错误

    return "\n".join(parts)


def _convert_nodes_to_tree(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> dict[str, Any]:
    """把 demo_seeder 的 nodes/edges 转成前端 mindmap {name, children} 结构.
    数据源格式:
        nodes: [{id, label, level, x, y}, ...]
        edges: [{from, to}, ...]
    """
    if not nodes:
        return {}

    by_id = {n["id"]: n for n in nodes}
    children_map: dict[str, list[str]] = {n["id"]: [] for n in nodes}
    roots: list[str] = []
    for e in edges or []:
        src, dst = e.get("from"), e.get("to")
        if src in children_map and dst in by_id:
            children_map[src].append(dst)

    # 找根节点 (没有入边的节点, 或者 level=0)
    incoming = set()
    for e in edges or []:
        if e.get("to") in by_id:
            incoming.add(e["to"])
    for n in nodes:
        if n["id"] not in incoming or n.get("level", 0) == 0:
            roots.append(n["id"])

    if not roots:
        roots = [nodes[0]["id"]]

    def build(nid: str) -> dict[str, Any]:
        node = by_id[nid]
        kids = []
        for cid in children_map.get(nid, []):
            kids.append(build(cid))
        return {"name": node.get("label") or node.get("title") or "节点",
                "children": kids}

    # 单根: 直接返回; 多根: 包装成虚拟根
    if len(roots) == 1:
        return build(roots[0])
    return {
        "name": "本章概览",
        "children": [build(rid) for rid in roots],
    }


def _concepts_from_lecture(lecture: dict[str, Any]) -> list[dict[str, Any]]:
    """把 lecture.blocks 里的 h2 标题抽成 concepts (核心 = 第 1 个, 其余 = 基础)."""
    blocks = lecture.get("blocks") or []
    heads = [b.get("text", "").strip() for b in blocks
             if b.get("kind") in ("h1", "h2", "h3") and b.get("text")]
    out: list[dict[str, Any]] = []
    for i, term in enumerate(heads[:6]):
        clean = term.lstrip("1234567890. 　、 ").strip()
        if not clean:
            continue
        out.append({
            "term": clean[:30],
            "level": "core" if i == 0 else "basic",
            "definition": f"本节核心要点：{clean}",
            "example": None,
        })
    return out


def _exercises_from_lecture(lecture: dict[str, Any],
                            sub_title: str = "") -> list[dict[str, Any]]:
    """根据 lecture 标题合成几道练习题 (无 LLM, 走 heuristic)."""
    blocks = lecture.get("blocks") or []
    heads = [b.get("text", "").strip() for b in blocks
             if b.get("kind") in ("h1", "h2", "h3") and b.get("text")]
    if not heads:
        return []

    exercises: list[dict[str, Any]] = []

    # 一道记忆题 — 问本节小标题数量
    exercises.append({
        "type": "fill",
        "question": f"本节《{sub_title or '本节'}》共有多少个子主题？(输入阿拉伯数字)",
        "answer": str(len(heads)),
        "explanation": f"本节包含 {len(heads)} 个核心要点：" + " / ".join(heads[:5]),
    })

    # 一道选择题 — 第一个小标题是不是核心要点
    if len(heads) >= 2:
        choices = [heads[0].lstrip("1234567890. 　、 ").strip()[:40]] + \
                  [h.lstrip("1234567890. 　、 ").strip()[:40] for h in heads[1:4]]
        exercises.append({
            "type": "choice",
            "question": f"下列关于《{sub_title or '本节'}》的要点，哪一个是排在第一位的核心要点？",
            "options": choices,
            "answer": 0,
            "explanation": f"第一个要点 {heads[0].strip()} 是本节的核心。",
        })

    # 一道判断题 — 是否所有内容都讲完
    exercises.append({
        "type": "bool",
        "question": "学习完本节所有要点后再做练习，能显著提高记忆效果。",
        "answer": True,
        "explanation": "间隔复习与即时测验能强化长期记忆。",
    })

    return exercises


def _build_from_seeded(
    lecture_obj: dict[str, Any] | None,
    mindmap_obj: dict[str, Any] | None,
    sub_title: str = "",
) -> dict[str, Any]:
    """根据父章节的 seeded lecture + mindmap 直接构造四件套."""
    transcript = _render_lecture_html(lecture_obj) if isinstance(lecture_obj, dict) else ""
    mindmap_root: dict[str, Any] | None = None
    if isinstance(mindmap_obj, dict):
        mindmap_root = _convert_nodes_to_tree(
            mindmap_obj.get("nodes") or [],
            mindmap_obj.get("edges") or [],
        )

    concepts: list[dict[str, Any]] = []
    if isinstance(lecture_obj, dict):
        concepts = _concepts_from_lecture(lecture_obj)

    exercises: list[dict[str, Any]] = []
    if isinstance(lecture_obj, dict):
        exercises = _exercises_from_lecture(lecture_obj, sub_title)
    elif isinstance(mindmap_obj, dict):
        # 仅有 mindmap 的兜底
        exercises.append({
            "type": "bool",
            "question": f"本节包含思维导图，建议先看导图再学细节。",
            "answer": True,
            "explanation": "先建立全局视图，再深入细节，符合认知规律。",
        })

    return {
        "transcript": transcript,
        "concepts": concepts,
        "mindMap": mindmap_root,
        "exercises": exercises,
    }


def _escape(s: Any) -> str:
    """HTML escape (raw string 用不了 markupsafe.escape, 简单实现)."""
    if s is None:
        return ""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _safe_json(raw: str) -> Any:
    """允许 LLM 输出带前后缀; 先尝试直接 json.loads, 再尝试截取 { ... }."""
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        pass
    m = re.search(r"\{[\s\S]*\}", raw)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None


# ── 工具 ──

def _get_attr(obj: Any, key: str, default: Any = "") -> Any:
    """兼容 ORM row / dict, 安全取值."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)
