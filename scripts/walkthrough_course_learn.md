# `course-learn.html` 实操手册

> 这页说明怎么在浏览器里手动验证 6 个学习步骤面板, 以及每个面板"应该长什么样"。
> 验证用课程: **`demo_python_101` / `sc_py_1`** — 该课程已由 demo seeder 写入 `lecture` + `mindmap`,
> 不依赖 B站字幕, 离线即可跑通。

## 启动

```bash
# 后端
python scripts/start_server.py   # 默认端口 (8000?), 详见 config/.env
# 前端直接打开 (已经是静态 HTML)
#   http://localhost:8000/course-learn.html?courseId=demo_python_101
```

---

## 步骤 1 — 观看视频 (`watch` 面板)

预期显示:
- 顶部进度条 0%
- 中央卡片: 🎬 图标 + "正在播放: Python 编程入门 · Python 初识与环境搭建"
- 右侧 CTA: "下一步:阅读字幕" 紫色按钮

DOM 校验:
```js
document.getElementById('cl-welcome-title-text').textContent
// 期望: "Python 编程入门 · Python 初识与环境搭建"
document.getElementById('cl-welcome-next')  // 存在
```

---

## 步骤 2 — 字幕与讲义

切到 **"字幕"** Tab:

预期显示 (`demo_python_101` 走 seeded 路径, **字幕面板可能为空** — 因为 seeder 只写了 lecture, 没写 srt 字幕) :
- 顶部子 tab: 字幕 (active) / AI 讲义
- 主区: `cl-subtitle-empty` "该视频暂无字幕" 或滚动字幕行

切到 **"AI 讲义"** Tab:
- 应该看到 5 段结构化 HTML: `<h4>1. Python 历史与特点</h4><p>...</p>`
- 每段都带 `<strong>小结：</strong>`
- 不应再是 "暂无 AI 讲义" 占位

DOM 校验:
```js
document.querySelector('#cl-transcript-content h4').textContent
// 期望: "1. Python 历史与特点"
document.querySelectorAll('#cl-transcript-content h4').length
// 期望: 4 (即 4 个子主题)
```

---

## 步骤 3 — 笔记

输入文字, 等 1 秒, 顶部应从 "保存中..." 跳回 "✓ 已自动保存"。
刷新页面, 笔记应保留 (来自 localStorage `starlearn_course_notes`)。

DOM 校验:
```js
document.getElementById('cl-notes-save-status').textContent
// 期望: "已自动保存"
```

---

## 步骤 4 — 关键概念

预期显示 4 张卡片:
- 🟥 Python 历史与特点 (core)
- 🟦 环境搭建 (basic)
- 🟦 第一个程序 (basic)
- 🟦 应用领域 (basic)

顶部有 "全部 / 核心 / 基础 / 进阶" 过滤器, 点 "核心" 应该只剩 1 张。

DOM 校验:
```js
document.getElementById('cl-concepts-count').textContent
// 期望: "4"
document.querySelectorAll('.cl-concept-card').length
// 期望: 4
document.querySelectorAll('.cl-concept-card[data-level="core"]').length
// 期望: 1
```

---

## 步骤 5 — 思维导图 (本次重点)

预期显示根节点 **"Python"** + 4 个一级分支 (Python 历史与特点 / 环境搭建 / 第一个程序 / 应用领域)。
拖动视口 / 滚轮缩放 / 点击工具栏缩放按钮都应工作。

**重点校验 (修复了显示 bug)**:
```js
const stage = document.getElementById('cl-mindmap-stage');
const nodes = stage.querySelectorAll('.cl-mindmap-node');
// 期望: >= 5 (1 root + 4 branches)
const rootNode = stage.querySelector('.cl-mindmap-node.root');
// 期望: 不为 null, textContent = "Python"
```

如果 `nodes.length === 0` 或 `rootNode === null`, 说明视口尺寸计算有问题, 节点被挤出了画布。打开 devtools 检查 `cl-mindmap-viewport` 的 `clientWidth/clientHeight`, 应该是非零。

---

## 步骤 6 — 课后练习

预期显示 3 道题:
1. 填空: "本节《Python 初识与环境搭建》共有多少个子主题？(输入阿拉伯数字)" — 答案 `4`
2. 选择: "下列关于《...》的要点，哪一个是排在第一位的核心要点？" — 答案 index 0
3. 判断: "学习完本节所有要点后再做练习，能显著提高记忆效果。" — 答案 `true`

答完所有题:
- 顶部应显示 "已答 3 / 3, 正确率 XX%"
- 标记步骤为已完成 (cl-step[data-step="exercises"] 应带 `completed` class)

DOM 校验:
```js
document.getElementById('cl-exercises-count').textContent  // "3"
document.querySelectorAll('.cl-exercise-item').length       // 3
```

---

## 用真实 B站 课程的额外步骤

把任一 B站 视频的 `bvid` 粘到 `localStorage.starlearn_courses_data.subjects[].courses[].id`,
然后打开 `course-learn.html?courseId=<那个 ID>`。

切到 **"字幕"** Tab, 应该看到滚动的中文字幕行。点击任一行会向 iframe 发送 `{type:"seek",time:<秒>}`,
如果浏览器 console 报错 "Failed to send postMessage", 说明 B站 iframe 还在加载。

---

## 端到端 API 校验 (替代浏览器)

如果不想打开浏览器, 跑这个:

```bash
python -c "
import asyncio, json
from app.services.course_learn_content import get_subchapter_content
from app.core.database import get_sessionmaker
from app.models.course import SubChapter
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.course import Chapter

async def main():
    async with get_sessionmaker()() as s:
        sc = (await s.execute(
            select(SubChapter)
            .where(SubChapter.id == 'sc_py_1')
            .options(selectinload(SubChapter.chapter).selectinload(Chapter.course))
        )).scalar_one()
        out = await get_subchapter_content(course=sc.chapter.course, chapter=sc.chapter, subchapter=sc)
        print(json.dumps({k: ('<html>' if k=='transcript' else v) for k, v in out.items()}, ensure_ascii=False, indent=2)[:800])

asyncio.run(main())
"
```

期望输出 `source: "demo_seeder"`, 4 条 concepts, 1 个 mindmap root, 3 道 exercises。