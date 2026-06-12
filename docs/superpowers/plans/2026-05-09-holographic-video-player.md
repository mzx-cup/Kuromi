# Holographic Video Player Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local `video/` powered Bilibili-style player for Star-Learn's 全息视界 page, with an integrated AI companion notes tab.

**Architecture:** Keep the existing standalone `video-player.html`, `video-player.css`, and `video-player.js` module boundary. Add a small backend static route for `/video/{filename}` and let the frontend use a static video catalog with local `/video/...` sources, AI note metadata, progress persistence, and first-version local danmaku display.

**Tech Stack:** FastAPI, plain HTML/CSS/JavaScript, Python `unittest`, browser `<video>` API, Fullscreen API, `localStorage`.

---

## File Structure

- Create `video/.gitkeep`: keeps the local video warehouse directory in git.
- Create `video/README.md`: explains where users should place local video files.
- Modify `main.py`: add `VIDEO_DIR` and a `/video/{filename}` route near the existing `/audio/{filename}` route.
- Modify `html/video-player.html`: replace the preview-first external-link page with a real Bilibili-style player shell and right-side `选集` / `AI笔记` tabs.
- Modify `css/video-player.css`: style the main player layout, local-video empty state, episode list, AI notes, danmaku lane, and responsive behavior.
- Modify `js/video-player.js`: replace simulated playback with real `<video>` wiring, catalog switching, progress persistence, AI timestamp seeking, tab switching, speed cycling, fullscreen, and local danmaku.
- Modify `tests/test_video_player_links.py`: update old external-link expectations and add local-video structure checks.
- Create `tests/test_video_static_route.py`: verify the backend exposes `/video/{filename}` and has the expected video directory constant.

---

### Task 1: Backend Local Video Route

**Files:**
- Create: `video/.gitkeep`
- Create: `video/README.md`
- Modify: `main.py`
- Create: `tests/test_video_static_route.py`

- [ ] **Step 1: Write the failing route/constant test**

Create `tests/test_video_static_route.py`:

```python
import unittest
from pathlib import Path


class VideoStaticRouteTest(unittest.TestCase):
    def test_main_exposes_local_video_directory(self):
        main_py = Path("main.py").read_text(encoding="utf-8")

        self.assertIn('VIDEO_DIR = os.path.join(BASE_DIR, "video")', main_py)
        self.assertIn('@app.get("/video/{filename}")', main_py)
        self.assertIn('FileResponse(file_path, media_type=media_type)', main_py)

    def test_video_directory_has_usage_note(self):
        readme = Path("video/README.md").read_text(encoding="utf-8")

        self.assertIn("全息视界", readme)
        self.assertIn("/video/", readme)
        self.assertIn(".mp4", readme)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
python -m unittest tests.test_video_static_route -v
```

Expected: FAIL because `video/README.md`, `VIDEO_DIR`, and `/video/{filename}` do not exist yet.

- [ ] **Step 3: Add the video directory docs**

Create `video/.gitkeep` as an empty file.

Create `video/README.md`:

```markdown
# 全息视界本地视频仓库

把需要在全息视界播放的本地视频放在这个目录下。

支持第一版播放器清单中使用的常见格式：

- `.mp4`
- `.webm`
- `.mov`

浏览器访问路径使用 `/video/<文件名>`，例如 `/video/python-algorithm-03.mp4`。
```

- [ ] **Step 4: Add the backend route**

In `main.py`, add this constant next to the existing directory constants:

```python
VIDEO_DIR = os.path.join(BASE_DIR, "video")
```

Add this route immediately after `serve_audio`:

```python
@app.get("/video/{filename}")
def serve_video(filename: str):
    video_ext = os.path.splitext(filename)[1].lower()
    media_types = {
        ".mp4": "video/mp4",
        ".webm": "video/webm",
        ".mov": "video/quicktime",
        ".m4v": "video/mp4",
    }
    media_type = media_types.get(video_ext, "application/octet-stream")
    file_path = os.path.join(VIDEO_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type=media_type)
    raise HTTPException(status_code=404, detail="视频文件未找到")
```

- [ ] **Step 5: Run the route test**

Run:

```bash
python -m unittest tests.test_video_static_route -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```bash
git add main.py video/.gitkeep video/README.md tests/test_video_static_route.py
git commit -m "Add local video static route"
```

---

### Task 2: Player HTML Structure

**Files:**
- Modify: `html/video-player.html`
- Modify: `tests/test_video_player_links.py`

- [ ] **Step 1: Replace old external-link tests with local player structure tests**

Edit `tests/test_video_player_links.py` so its content is:

```python
import unittest
from pathlib import Path


class VideoPlayerLinksTest(unittest.TestCase):
    def test_holographic_video_page_uses_local_video_player(self):
        video_html = Path("html/video-player.html").read_text(encoding="utf-8")

        self.assertIn('id="course-video"', video_html)
        self.assertIn("<video", video_html)
        self.assertIn('data-empty-state', video_html)
        self.assertIn("video/", video_html)
        self.assertNotIn("www.bilibili.com", video_html)

    def test_page_uses_bilibili_style_learning_layout(self):
        video_html = Path("html/video-player.html").read_text(encoding="utf-8")

        self.assertIn("bili-theater", video_html)
        self.assertIn("player-column", video_html)
        self.assertIn("player-side-panel", video_html)
        self.assertIn("episode-list", video_html)
        self.assertIn("danmaku-form", video_html)

    def test_ai_notes_tab_is_present(self):
        video_html = Path("html/video-player.html").read_text(encoding="utf-8")

        self.assertIn('data-tab="episodes"', video_html)
        self.assertIn('data-tab="ai-notes"', video_html)
        self.assertIn("AI伴学笔记", video_html)
        self.assertIn("note-timeline", video_html)
        self.assertIn("重点问题", video_html)

    def test_local_video_empty_state_copy_is_present(self):
        video_html = Path("html/video-player.html").read_text(encoding="utf-8")

        self.assertIn("请将视频放入 Kuromi 根目录的 video/ 文件夹", video_html)
        self.assertIn(".mp4 / .webm / .mov", video_html)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the failing HTML tests**

Run:

```bash
python -m unittest tests.test_video_player_links -v
```

Expected: FAIL because the current page still uses preview/external-link structure.

- [ ] **Step 3: Replace `html/video-player.html` with the new shell**

Use this complete HTML:

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>星识 Star-Learn - 全息视界</title>
    <link rel="stylesheet" href="/css/video-player.css">
</head>
<body class="video-player-body">
    <div class="video-bg"></div>

    <nav class="video-nav">
        <div class="nav-container">
            <a href="/hub.html" class="nav-back" aria-label="返回中枢">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M15 19l-7-7 7-7"/>
                </svg>
                <span>返回中枢</span>
            </a>
            <div class="nav-brand">
                <span class="brand-mark">SL</span>
                <div>
                    <h1 class="nav-title">全息视界</h1>
                    <p class="nav-subtitle">本地视频学习驾驶舱</p>
                </div>
            </div>
            <div class="nav-status">
                <span class="status-dot"></span>
                <span>video/ 已接入</span>
            </div>
        </div>
    </nav>

    <main class="video-main">
        <section class="bili-theater">
            <div class="player-column">
                <section class="player-shell">
                    <div class="player-heading">
                        <div>
                            <p class="section-kicker">本地视频播放</p>
                            <h2 id="video-title">算法复杂度分析</h2>
                            <p id="video-subtitle" class="stage-copy">从时间复杂度、空间复杂度到代码层级分析，建立算法效率判断框架。</p>
                        </div>
                        <div class="stage-actions">
                            <button class="primary-action" type="button" id="continue-learning-btn">继续学习</button>
                            <button class="ghost-action" type="button" id="favorite-btn">收藏</button>
                        </div>
                    </div>

                    <div class="video-player" id="video-player" data-empty-state>
                        <video id="course-video" preload="metadata" playsinline></video>
                        <div class="video-empty-state" id="video-empty-state">
                            <div class="play-circle">
                                <svg class="play-icon" viewBox="0 0 24 24" fill="currentColor">
                                    <path d="M8 5v14l11-7z"/>
                                </svg>
                            </div>
                            <p class="placeholder-text">请将视频放入 Kuromi 根目录的 video/ 文件夹</p>
                            <p class="placeholder-subtext">支持 .mp4 / .webm / .mov，播放器会使用 /video/ 路径读取本地视频。</p>
                        </div>
                        <div class="danmaku-stage" id="danmaku-stage" aria-live="polite"></div>

                        <div class="player-controls" id="player-controls">
                            <div class="progress-container">
                                <div class="progress-track" id="progress-track">
                                    <div class="progress-fill" id="progress-fill">
                                        <div class="progress-glow"></div>
                                    </div>
                                    <div class="progress-thumb" id="progress-thumb"></div>
                                </div>
                            </div>

                            <div class="control-bar">
                                <div class="control-left">
                                    <button class="control-btn play-btn" id="play-btn" type="button" aria-label="播放或暂停">
                                        <svg class="icon-play" viewBox="0 0 24 24" fill="currentColor">
                                            <path d="M8 5v14l11-7z"/>
                                        </svg>
                                        <svg class="icon-pause hidden" viewBox="0 0 24 24" fill="currentColor">
                                            <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
                                        </svg>
                                    </button>
                                    <button class="control-btn volume-btn" id="volume-btn" type="button" aria-label="静音">
                                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                            <path d="M11 5L6 9H2v6h4l5 4V5zM19.07 4.93a10 10 0 010 14.14M15.54 8.46a5 5 0 010 7.07"/>
                                        </svg>
                                    </button>
                                    <div class="time-display">
                                        <span id="current-time">00:00</span>
                                        <span class="time-separator">/</span>
                                        <span id="total-time">00:00</span>
                                    </div>
                                </div>
                                <div class="control-right">
                                    <button class="control-btn speed-btn" id="speed-btn" type="button"><span id="speed-text">1x</span></button>
                                    <button class="control-btn quality-btn" id="quality-btn" type="button"><span>本地</span></button>
                                    <button class="control-btn fullscreen-btn" id="fullscreen-btn" type="button" aria-label="全屏">
                                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                            <path d="M8 3H5a2 2 0 00-2 2v3m18 0V5a2 2 0 00-2-2h-3m0 18h3a2 2 0 002-2v-3M3 16v3a2 2 0 002 2h3"/>
                                        </svg>
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>

                    <form class="danmaku-form" id="danmaku-form">
                        <input class="danmaku-input" id="danmaku-input" type="text" maxlength="40" placeholder="发一条本地弹幕笔记">
                        <button class="danmaku-send" type="submit">发送</button>
                    </form>
                </section>

                <section class="video-info-panel">
                    <div>
                        <span class="panel-label">当前视频</span>
                        <h3 id="info-title">算法复杂度分析</h3>
                        <p id="info-description">掌握 O(1)、O(n)、O(log n) 的判断方法，并能用 Python 代码解释时间与空间消耗。</p>
                    </div>
                    <div class="info-metrics">
                        <article class="metric-panel">
                            <span class="metric-value" id="progress-percent">0%</span>
                            <span class="metric-label">当前进度</span>
                        </article>
                        <article class="metric-panel">
                            <span class="metric-value" id="note-count">0</span>
                            <span class="metric-label">AI笔记</span>
                        </article>
                    </div>
                </section>
            </div>

            <aside class="player-side-panel">
                <div class="side-tabs" role="tablist" aria-label="全息视界侧栏">
                    <button class="side-tab active" type="button" data-tab="episodes">选集</button>
                    <button class="side-tab" type="button" data-tab="ai-notes">AI伴学笔记</button>
                </div>

                <section class="side-panel-section active" id="episodes-panel">
                    <div class="side-section-header">
                        <div>
                            <span class="section-kicker">video/ 本地仓库</span>
                            <h3>课程选集</h3>
                        </div>
                        <span class="rail-pill" id="episode-count">0 个视频</span>
                    </div>
                    <div class="episode-list" id="episode-list"></div>
                </section>

                <section class="side-panel-section" id="ai-notes-panel">
                    <div class="side-section-header">
                        <div>
                            <span class="section-kicker">AI Companion</span>
                            <h3>AI伴学笔记</h3>
                        </div>
                        <span class="rail-pill">可跳转</span>
                    </div>
                    <article class="ai-summary">
                        <span class="panel-label">本节摘要</span>
                        <p id="ai-summary-text"></p>
                    </article>
                    <div>
                        <span class="panel-label">时间戳笔记</span>
                        <div class="note-timeline" id="note-timeline"></div>
                    </div>
                    <div>
                        <span class="panel-label">重点问题</span>
                        <div class="question-list" id="question-list"></div>
                    </div>
                    <article class="ai-suggestion">
                        <span class="panel-label">学习建议</span>
                        <p id="ai-suggestion-text"></p>
                    </article>
                </section>
            </aside>
        </section>
    </main>

    <script src="/js/data-layer.js"></script>
    <script src="/js/video-player.js"></script>
</body>
</html>
```

- [ ] **Step 4: Run the HTML tests**

Run:

```bash
python -m unittest tests.test_video_player_links -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add html/video-player.html tests/test_video_player_links.py
git commit -m "Redesign holographic video player shell"
```

---

### Task 3: Player CSS Layout

**Files:**
- Modify: `css/video-player.css`

- [ ] **Step 1: Replace CSS with the Bilibili-style local video layout**

Replace `css/video-player.css` with a focused stylesheet that preserves the existing palette and includes these selectors exactly:

```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
    --bg: #071014;
    --panel: rgba(13, 25, 32, 0.82);
    --panel-strong: rgba(16, 31, 39, 0.94);
    --line: rgba(178, 224, 225, 0.16);
    --line-strong: rgba(114, 220, 209, 0.34);
    --text: #f2fbfa;
    --muted: rgba(228, 246, 244, 0.68);
    --faint: rgba(228, 246, 244, 0.46);
    --cyan: #5eead4;
    --blue: #60a5fa;
    --green: #34d399;
    --amber: #fbbf24;
    --danger: #fb7185;
    --radius: 8px;
}

* { box-sizing: border-box; }
body {
    margin: 0;
    min-height: 100vh;
    color: var(--text);
    font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    background: var(--bg);
}
button, input { font: inherit; }
button { border: 0; }
.video-player-body { overflow-x: hidden; }
.video-bg {
    position: fixed;
    inset: 0;
    z-index: 0;
    pointer-events: none;
    background:
        radial-gradient(circle at 18% 8%, rgba(94, 234, 212, 0.18), transparent 32%),
        radial-gradient(circle at 82% 18%, rgba(96, 165, 250, 0.16), transparent 30%),
        linear-gradient(135deg, #071014 0%, #0a1b20 48%, #101821 100%);
}
.video-bg::after {
    content: "";
    position: absolute;
    inset: 0;
    opacity: 0.16;
    background-image:
        linear-gradient(rgba(255,255,255,.08) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,.08) 1px, transparent 1px);
    background-size: 72px 72px;
    mask-image: linear-gradient(to bottom, black, transparent 82%);
}
.video-nav {
    position: sticky;
    top: 0;
    z-index: 20;
    border-bottom: 1px solid var(--line);
    background: rgba(7,16,20,.78);
    backdrop-filter: blur(18px);
}
.nav-container {
    min-height: 72px;
    width: min(1540px, calc(100vw - 48px));
    margin: 0 auto;
    display: grid;
    grid-template-columns: minmax(130px, 1fr) auto minmax(130px, 1fr);
    align-items: center;
    gap: 18px;
}
.nav-back, .nav-status, .nav-brand, .stage-actions, .control-left, .control-right, .side-section-header, .danmaku-form {
    display: flex;
    align-items: center;
}
.nav-back {
    width: fit-content;
    gap: 8px;
    color: var(--muted);
    text-decoration: none;
    font-size: 14px;
    font-weight: 600;
    padding: 9px 12px;
    border: 1px solid transparent;
    border-radius: var(--radius);
    transition: 160ms ease;
}
.nav-back:hover { color: var(--text); border-color: var(--line); background: rgba(255,255,255,.05); }
.nav-back svg { width: 18px; height: 18px; }
.nav-brand { justify-self: center; gap: 12px; }
.brand-mark {
    width: 38px;
    height: 38px;
    display: grid;
    place-items: center;
    border: 1px solid var(--line-strong);
    border-radius: 10px;
    background: linear-gradient(135deg, rgba(94,234,212,.18), rgba(96,165,250,.16));
    color: var(--cyan);
    font-size: 12px;
    font-weight: 800;
}
.nav-title { margin: 0; font-size: 18px; line-height: 1.1; letter-spacing: 0; }
.nav-subtitle { margin: 3px 0 0; color: var(--faint); font-size: 12px; }
.nav-status {
    justify-self: end;
    gap: 8px;
    color: var(--muted);
    font-size: 13px;
    padding: 8px 11px;
    border: 1px solid var(--line);
    border-radius: 999px;
    background: rgba(255,255,255,.04);
}
.status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--green);
    box-shadow: 0 0 14px rgba(52,211,153,.72);
}
.video-main {
    position: relative;
    z-index: 1;
    width: min(1540px, calc(100vw - 48px));
    margin: 0 auto;
    padding: 28px 0 42px;
}
.bili-theater {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 390px;
    gap: 22px;
    align-items: start;
}
.player-column { min-width: 0; display: grid; gap: 14px; }
.player-shell, .player-side-panel, .video-info-panel {
    border: 1px solid var(--line);
    border-radius: var(--radius);
    background: var(--panel);
    box-shadow: 0 24px 70px rgba(0,0,0,.28);
    backdrop-filter: blur(18px);
}
.player-shell { padding: 20px; }
.player-heading {
    display: flex;
    justify-content: space-between;
    gap: 18px;
    margin-bottom: 18px;
}
.section-kicker {
    display: block;
    margin: 0 0 7px;
    color: var(--cyan);
    font-size: 12px;
    font-weight: 800;
}
.player-heading h2, .side-section-header h3, .video-info-panel h3 {
    margin: 0;
    letter-spacing: 0;
}
.player-heading h2 {
    font-size: clamp(26px, 3vw, 42px);
    line-height: 1.04;
}
.stage-copy {
    max-width: 760px;
    margin: 10px 0 0;
    color: var(--muted);
    line-height: 1.7;
    font-size: 15px;
}
.stage-actions {
    align-self: flex-start;
    gap: 10px;
    flex-shrink: 0;
}
.primary-action, .ghost-action, .danmaku-send {
    min-height: 42px;
    padding: 0 16px;
    border-radius: var(--radius);
    color: var(--text);
    font-weight: 700;
    cursor: pointer;
}
.primary-action, .danmaku-send {
    background: linear-gradient(135deg, #0f766e, #2563eb);
    box-shadow: 0 14px 34px rgba(37,99,235,.22);
}
.ghost-action { border: 1px solid var(--line); background: rgba(255,255,255,.05); }
.video-player {
    position: relative;
    overflow: hidden;
    aspect-ratio: 16 / 9;
    border: 1px solid rgba(94,234,212,.22);
    border-radius: var(--radius);
    background: #03090d;
    box-shadow: inset 0 0 0 1px rgba(255,255,255,.04);
}
.video-player video {
    width: 100%;
    height: 100%;
    display: block;
    object-fit: contain;
    background: #03090d;
}
.video-empty-state {
    position: absolute;
    inset: 0;
    display: none;
    place-items: center;
    padding: 24px;
    text-align: center;
    background:
        linear-gradient(135deg, rgba(13,148,136,.16), rgba(37,99,235,.14)),
        radial-gradient(circle at 50% 40%, rgba(94,234,212,.18), transparent 34%),
        #03090d;
}
.video-player[data-empty-state] .video-empty-state { display: grid; }
.play-circle {
    width: 82px;
    height: 82px;
    display: grid;
    place-items: center;
    margin: 0 auto 14px;
    border: 1px solid rgba(94,234,212,.52);
    border-radius: 50%;
    background: rgba(94,234,212,.13);
    color: var(--cyan);
}
.play-icon { width: 34px; height: 34px; margin-left: 4px; }
.placeholder-text { margin: 0; font-size: 18px; font-weight: 800; }
.placeholder-subtext { max-width: 520px; margin: 8px auto 0; color: var(--muted); font-size: 14px; line-height: 1.6; }
.danmaku-stage {
    position: absolute;
    inset: 0;
    pointer-events: none;
    overflow: hidden;
}
.danmaku-item {
    position: absolute;
    left: 100%;
    top: var(--lane-top);
    white-space: nowrap;
    color: #fff;
    font-weight: 700;
    text-shadow: 0 2px 8px rgba(0,0,0,.75);
    animation: danmakuFly 7s linear forwards;
}
@keyframes danmakuFly {
    to { transform: translateX(calc(-100vw - 100%)); }
}
.player-controls {
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    padding: 18px;
    background: linear-gradient(to top, rgba(3,9,13,.96), transparent);
    opacity: 0;
    transition: opacity 180ms ease;
}
.video-player:hover .player-controls, .video-player[data-empty-state] .player-controls { opacity: 1; }
.progress-container { margin-bottom: 12px; }
.progress-track {
    position: relative;
    height: 7px;
    border-radius: 999px;
    background: rgba(255,255,255,.16);
    cursor: pointer;
}
.progress-fill {
    position: relative;
    width: 0;
    height: 100%;
    border-radius: 999px;
    background: linear-gradient(90deg, var(--cyan), var(--blue));
}
.progress-glow, .progress-thumb { position: absolute; top: 50%; border-radius: 50%; }
.progress-glow {
    right: 0;
    width: 12px;
    height: 12px;
    transform: translateY(-50%);
    background: var(--cyan);
    box-shadow: 0 0 16px rgba(94,234,212,.8);
}
.progress-thumb {
    left: 0;
    width: 15px;
    height: 15px;
    transform: translate(-50%, -50%);
    background: #fff;
}
.control-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
}
.control-left, .control-right { gap: 8px; }
.control-btn {
    min-width: 40px;
    height: 40px;
    display: grid;
    place-items: center;
    border-radius: var(--radius);
    background: rgba(255,255,255,.08);
    color: var(--text);
    cursor: pointer;
}
.control-btn svg { width: 20px; height: 20px; }
.play-btn { background: rgba(94,234,212,.18); color: var(--cyan); }
.hidden { display: none !important; }
.time-display {
    display: flex;
    align-items: center;
    gap: 4px;
    color: var(--muted);
    font-size: 13px;
    font-weight: 700;
}
.danmaku-form {
    gap: 10px;
    margin-top: 12px;
}
.danmaku-input {
    min-width: 0;
    flex: 1;
    height: 42px;
    padding: 0 12px;
    border: 1px solid var(--line);
    border-radius: var(--radius);
    outline: none;
    background: rgba(255,255,255,.05);
    color: var(--text);
}
.video-info-panel {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 330px;
    gap: 14px;
    padding: 16px;
}
.panel-label, .metric-label, .episode-meta {
    color: var(--faint);
    font-size: 12px;
    font-weight: 700;
}
.video-info-panel p, .ai-summary p, .ai-suggestion p {
    margin: 8px 0 0;
    color: var(--muted);
    line-height: 1.55;
    font-size: 14px;
}
.info-metrics {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
}
.metric-panel {
    min-height: 96px;
    padding: 14px;
    border: 1px solid var(--line);
    border-radius: var(--radius);
    background: rgba(255,255,255,.045);
}
.metric-value {
    display: block;
    color: var(--cyan);
    font-size: 30px;
    font-weight: 800;
}
.player-side-panel {
    position: sticky;
    top: 94px;
    overflow: hidden;
}
.side-tabs {
    display: grid;
    grid-template-columns: 1fr 1fr;
    border-bottom: 1px solid var(--line);
}
.side-tab {
    height: 48px;
    background: rgba(255,255,255,.035);
    color: var(--muted);
    cursor: pointer;
    font-weight: 800;
}
.side-tab.active {
    color: var(--cyan);
    background: rgba(94,234,212,.1);
}
.side-panel-section {
    display: none;
    padding: 16px;
    max-height: calc(100vh - 150px);
    overflow-y: auto;
}
.side-panel-section.active { display: block; }
.side-section-header {
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 14px;
}
.rail-pill {
    padding: 5px 9px;
    border: 1px solid var(--line);
    border-radius: 999px;
    background: rgba(0,0,0,.32);
    color: var(--muted);
    font-size: 12px;
}
.episode-list { display: grid; gap: 10px; }
.episode-item, .note-item, .question-item {
    width: 100%;
    text-align: left;
    border: 1px solid var(--line);
    border-radius: var(--radius);
    background: rgba(255,255,255,.045);
    color: var(--text);
}
.episode-item {
    display: grid;
    grid-template-columns: 42px minmax(0, 1fr);
    gap: 10px;
    padding: 12px;
    cursor: pointer;
}
.episode-item.active {
    border-color: var(--line-strong);
    background: rgba(94,234,212,.1);
}
.episode-index {
    width: 42px;
    height: 42px;
    display: grid;
    place-items: center;
    border: 1px solid var(--line);
    border-radius: var(--radius);
    color: var(--cyan);
    font-weight: 800;
}
.episode-title { margin: 0 0 5px; font-size: 14px; font-weight: 800; }
.episode-desc { margin: 0; color: var(--faint); font-size: 12px; line-height: 1.45; }
.episode-progress {
    height: 5px;
    margin-top: 9px;
    overflow: hidden;
    border-radius: 999px;
    background: rgba(255,255,255,.12);
}
.episode-progress span {
    display: block;
    height: 100%;
    width: var(--progress-width);
    background: linear-gradient(90deg, var(--cyan), var(--blue));
}
.ai-summary, .ai-suggestion {
    padding: 12px;
    margin-bottom: 14px;
    border: 1px solid var(--line);
    border-radius: var(--radius);
    background: rgba(255,255,255,.045);
}
.note-timeline, .question-list {
    display: grid;
    gap: 9px;
    margin: 9px 0 14px;
}
.note-item {
    display: grid;
    grid-template-columns: 58px minmax(0, 1fr);
    gap: 10px;
    padding: 11px;
    cursor: pointer;
}
.note-time { color: var(--amber); font-size: 12px; font-weight: 800; }
.note-title { margin: 0 0 4px; font-size: 14px; font-weight: 800; }
.note-desc { margin: 0; color: var(--faint); font-size: 12px; line-height: 1.45; }
.question-item {
    padding: 10px 12px;
    color: var(--muted);
    font-size: 13px;
    line-height: 1.5;
}
#toast-container { max-width: min(360px, calc(100vw - 32px)); }
@keyframes slideIn {
    from { opacity: 0; transform: translateX(32px); }
    to { opacity: 1; transform: translateX(0); }
}
@media (max-width: 1180px) {
    .bili-theater, .video-info-panel { grid-template-columns: 1fr; }
    .player-side-panel { position: static; }
    .side-panel-section { max-height: none; }
}
@media (max-width: 820px) {
    .nav-container, .video-main { width: min(100vw - 28px, 1540px); }
    .nav-container { grid-template-columns: 1fr auto; }
    .nav-brand { justify-self: end; }
    .nav-status { display: none; }
    .player-shell { padding: 14px; }
    .player-heading, .control-bar {
        flex-direction: column;
        align-items: stretch;
    }
    .stage-actions, .control-left, .control-right { flex-wrap: wrap; }
}
@media (max-width: 560px) {
    .video-main { padding-top: 16px; }
    .nav-container { min-height: 62px; }
    .nav-back span, .nav-subtitle, .ghost-action, .control-right { display: none; }
    .brand-mark { width: 34px; height: 34px; }
    .nav-title { font-size: 16px; }
    .player-heading h2 { font-size: 26px; }
    .play-circle { width: 64px; height: 64px; }
    .play-icon { width: 28px; height: 28px; }
    .placeholder-text { font-size: 15px; }
    .placeholder-subtext { font-size: 12px; }
    .player-controls { padding: 12px; opacity: 1; }
    .danmaku-form { grid-template-columns: 1fr; }
    .danmaku-send { width: 100%; }
}
```

- [ ] **Step 2: Run the HTML structure tests as a regression check**

Run:

```bash
python -m unittest tests.test_video_player_links -v
```

Expected: PASS.

- [ ] **Step 3: Commit**

Run:

```bash
git add css/video-player.css
git commit -m "Style local holographic video player"
```

---

### Task 4: Player JavaScript Behavior

**Files:**
- Modify: `js/video-player.js`

- [ ] **Step 1: Replace simulated JS with real video behavior**

Replace `js/video-player.js` with this complete script:

```javascript
const SPEED_OPTIONS = [1, 1.25, 1.5, 2];
const STORAGE_PREFIX = 'starlearn-video-progress:';

const videoCatalog = [
    {
        id: 'python-algorithm-03',
        title: '算法复杂度分析',
        subtitle: '从时间复杂度、空间复杂度到代码层级分析，建立算法效率判断框架。',
        description: '掌握 O(1)、O(n)、O(log n) 的判断方法，并能用 Python 代码解释时间与空间消耗。',
        src: '/video/python-algorithm-03.mp4',
        durationLabel: '45:30',
        notes: {
            summary: '本节聚焦算法复杂度的判断方法：先识别输入规模，再观察循环层级、递归拆分和额外空间使用。',
            timeline: [
                { time: 90, title: '大 O 表示法', desc: '理解复杂度描述的是增长趋势，而不是精确运行秒数。' },
                { time: 645, title: '单层循环', desc: '用列表遍历解释 O(n) 的来源。' },
                { time: 945, title: '嵌套循环', desc: '对照二维遍历理解 O(n²)。' },
                { time: 1575, title: '空间复杂度', desc: '区分原地计算和额外数组带来的空间消耗。' }
            ],
            questions: [
                '为什么常数项通常会被复杂度表示法省略？',
                '两层循环一定是 O(n²) 吗？',
                '如何判断一个 Python 函数是否使用了额外空间？'
            ],
            suggestion: '看完本节后，建议用三段不同循环结构的 Python 代码手动标注时间复杂度。'
        }
    },
    {
        id: 'python-sort-04',
        title: '排序算法详解',
        subtitle: '比较冒泡、选择、快速和归并排序的核心思想。',
        description: '通过可视化步骤理解常见排序算法，并比较稳定性、时间复杂度和空间复杂度。',
        src: '/video/python-sort-04.mp4',
        durationLabel: '38:20',
        notes: {
            summary: '本节把排序算法拆成比较、交换、分治和合并四类动作，帮助你理解不同算法的效率差异。',
            timeline: [
                { time: 120, title: '排序问题建模', desc: '明确输入、输出和比较规则。' },
                { time: 520, title: '冒泡与选择', desc: '观察简单排序为何通常效率较低。' },
                { time: 1100, title: '快速排序', desc: '理解基准值和分区过程。' },
                { time: 1680, title: '归并排序', desc: '通过合并有序子数组理解分治。' }
            ],
            questions: [
                '快速排序为什么平均表现好但最坏情况差？',
                '稳定排序在什么场景下重要？',
                '归并排序为什么需要额外空间？'
            ],
            suggestion: '建议把快速排序和归并排序各写一遍，再对照调用栈画出递归过程。'
        }
    },
    {
        id: 'python-binary-search-05',
        title: '二分查找实战',
        subtitle: '从有序数组查找到边界条件处理。',
        description: '掌握二分查找模板，并理解左右边界、循环条件和答案区间的关系。',
        src: '/video/python-binary-search-05.mp4',
        durationLabel: '29:10',
        notes: {
            summary: '本节用搜索区间的收缩过程解释二分查找，重点避免边界条件和死循环。',
            timeline: [
                { time: 80, title: '有序性前提', desc: '二分查找依赖单调性或可判定区间。' },
                { time: 410, title: '左右指针', desc: '用 left/right 描述仍可能包含答案的范围。' },
                { time: 860, title: '边界模板', desc: '比较闭区间与半开区间写法。' },
                { time: 1280, title: '实战题型', desc: '把查找值扩展到查找第一个满足条件的位置。' }
            ],
            questions: [
                '为什么 mid 推荐写成 left + (right - left) // 2？',
                '什么时候循环条件用 left <= right？',
                '如何查找第一个大于等于目标值的位置？'
            ],
            suggestion: '建议用纸笔模拟 left、right、mid 的变化，至少跑三组边界输入。'
        }
    }
];

let currentVideoIndex = 0;
let speedIndex = 0;

document.addEventListener('DOMContentLoaded', function() {
    renderEpisodeList();
    bindPlayerEvents();
    bindTabs();
    bindDanmaku();
    loadVideo(0);
});

function getCurrentItem() {
    return videoCatalog[currentVideoIndex];
}

function bindPlayerEvents() {
    const video = document.getElementById('course-video');
    const playBtn = document.getElementById('play-btn');
    const continueBtn = document.getElementById('continue-learning-btn');
    const progressTrack = document.getElementById('progress-track');
    const volumeBtn = document.getElementById('volume-btn');
    const speedBtn = document.getElementById('speed-btn');
    const fullscreenBtn = document.getElementById('fullscreen-btn');
    const player = document.getElementById('video-player');

    playBtn.addEventListener('click', togglePlay);
    continueBtn.addEventListener('click', togglePlay);
    video.addEventListener('click', togglePlay);
    video.addEventListener('play', updatePlayIcon);
    video.addEventListener('pause', updatePlayIcon);
    video.addEventListener('timeupdate', handleTimeUpdate);
    video.addEventListener('loadedmetadata', handleLoadedMetadata);
    video.addEventListener('error', showEmptyState);

    progressTrack.addEventListener('click', function(event) {
        if (!Number.isFinite(video.duration) || video.duration === 0) return;
        const rect = progressTrack.getBoundingClientRect();
        const percent = (event.clientX - rect.left) / rect.width;
        video.currentTime = Math.max(0, Math.min(video.duration, percent * video.duration));
    });

    volumeBtn.addEventListener('click', function() {
        video.muted = !video.muted;
        showToast(video.muted ? '已静音' : '已恢复声音', 'info');
    });

    speedBtn.addEventListener('click', function() {
        speedIndex = (speedIndex + 1) % SPEED_OPTIONS.length;
        video.playbackRate = SPEED_OPTIONS[speedIndex];
        document.getElementById('speed-text').textContent = `${SPEED_OPTIONS[speedIndex]}x`;
    });

    fullscreenBtn.addEventListener('click', function() {
        if (!document.fullscreenElement) {
            player.requestFullscreen().catch(() => showToast('无法进入全屏', 'error'));
        } else {
            document.exitFullscreen();
        }
    });

    document.addEventListener('keydown', function(event) {
        if (event.code === 'Space' && event.target.tagName !== 'INPUT') {
            event.preventDefault();
            togglePlay();
        }
    });
}

function loadVideo(index) {
    currentVideoIndex = index;
    const item = getCurrentItem();
    const video = document.getElementById('course-video');

    video.pause();
    video.src = item.src;
    video.load();

    document.getElementById('video-title').textContent = item.title;
    document.getElementById('video-subtitle').textContent = item.subtitle;
    document.getElementById('info-title').textContent = item.title;
    document.getElementById('info-description').textContent = item.description;
    document.getElementById('total-time').textContent = item.durationLabel;
    document.getElementById('note-count').textContent = item.notes.timeline.length;
    updateProgress(0);
    renderAiNotes(item);
    updateEpisodeActiveState();
    showEmptyState();

    video.addEventListener('loadedmetadata', function restoreProgressOnce() {
        const saved = Number(localStorage.getItem(STORAGE_PREFIX + item.id));
        if (Number.isFinite(saved) && saved > 0 && saved < video.duration) {
            video.currentTime = saved;
        }
        video.removeEventListener('loadedmetadata', restoreProgressOnce);
    });
}

function renderEpisodeList() {
    const list = document.getElementById('episode-list');
    list.innerHTML = '';
    document.getElementById('episode-count').textContent = `${videoCatalog.length} 个视频`;

    videoCatalog.forEach((item, index) => {
        const saved = Number(localStorage.getItem(STORAGE_PREFIX + item.id)) || 0;
        const progress = saved > 0 ? 12 : 0;
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'episode-item';
        button.dataset.index = index;
        button.innerHTML = `
            <span class="episode-index">${String(index + 1).padStart(2, '0')}</span>
            <span>
                <span class="episode-meta">${item.durationLabel}</span>
                <span class="episode-title">${escapeHtml(item.title)}</span>
                <span class="episode-desc">${escapeHtml(item.subtitle)}</span>
                <span class="episode-progress" style="--progress-width: ${progress}%"><span></span></span>
            </span>
        `;
        button.addEventListener('click', () => loadVideo(index));
        list.appendChild(button);
    });
}

function updateEpisodeActiveState() {
    document.querySelectorAll('.episode-item').forEach((item) => {
        item.classList.toggle('active', Number(item.dataset.index) === currentVideoIndex);
    });
}

function renderAiNotes(item) {
    document.getElementById('ai-summary-text').textContent = item.notes.summary;
    document.getElementById('ai-suggestion-text').textContent = item.notes.suggestion;

    const timeline = document.getElementById('note-timeline');
    timeline.innerHTML = '';
    item.notes.timeline.forEach((note) => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'note-item';
        button.innerHTML = `
            <span class="note-time">${formatTime(note.time)}</span>
            <span>
                <span class="note-title">${escapeHtml(note.title)}</span>
                <span class="note-desc">${escapeHtml(note.desc)}</span>
            </span>
        `;
        button.addEventListener('click', () => seekToNote(note.time));
        timeline.appendChild(button);
    });

    const questions = document.getElementById('question-list');
    questions.innerHTML = '';
    item.notes.questions.forEach((question) => {
        const div = document.createElement('div');
        div.className = 'question-item';
        div.textContent = question;
        questions.appendChild(div);
    });
}

function seekToNote(time) {
    const video = document.getElementById('course-video');
    video.currentTime = time;
    video.focus();
    showToast(`已跳转到 ${formatTime(time)}`, 'success');
}

function bindTabs() {
    document.querySelectorAll('.side-tab').forEach((tab) => {
        tab.addEventListener('click', function() {
            document.querySelectorAll('.side-tab').forEach((item) => item.classList.remove('active'));
            document.querySelectorAll('.side-panel-section').forEach((item) => item.classList.remove('active'));
            tab.classList.add('active');
            document.getElementById(`${tab.dataset.tab}-panel`).classList.add('active');
        });
    });
}

function bindDanmaku() {
    document.getElementById('danmaku-form').addEventListener('submit', function(event) {
        event.preventDefault();
        const input = document.getElementById('danmaku-input');
        const text = input.value.trim();
        if (!text) return;
        launchDanmaku(text);
        input.value = '';
    });
}

function launchDanmaku(text) {
    const stage = document.getElementById('danmaku-stage');
    const item = document.createElement('div');
    item.className = 'danmaku-item';
    item.textContent = text;
    item.style.setProperty('--lane-top', `${18 + Math.floor(Math.random() * 48)}%`);
    stage.appendChild(item);
    setTimeout(() => item.remove(), 7200);
}

function togglePlay() {
    const video = document.getElementById('course-video');
    if (!video.src) return;
    if (video.paused) {
        video.play().catch(() => showToast('视频暂不可播放，请确认 video/ 中存在对应文件', 'warning'));
    } else {
        video.pause();
    }
}

function updatePlayIcon() {
    const video = document.getElementById('course-video');
    document.querySelector('.icon-play').classList.toggle('hidden', !video.paused);
    document.querySelector('.icon-pause').classList.toggle('hidden', video.paused);
}

function handleLoadedMetadata() {
    const video = document.getElementById('course-video');
    document.getElementById('video-player').removeAttribute('data-empty-state');
    document.getElementById('total-time').textContent = formatTime(video.duration);
    handleTimeUpdate();
}

function handleTimeUpdate() {
    const video = document.getElementById('course-video');
    if (!Number.isFinite(video.duration) || video.duration === 0) return;
    const percent = (video.currentTime / video.duration) * 100;
    updateProgress(percent);
    document.getElementById('current-time').textContent = formatTime(video.currentTime);
    document.getElementById('progress-percent').textContent = `${Math.round(percent)}%`;
    localStorage.setItem(STORAGE_PREFIX + getCurrentItem().id, String(Math.floor(video.currentTime)));
}

function updateProgress(percent) {
    const safePercent = Math.max(0, Math.min(100, percent));
    document.getElementById('progress-fill').style.width = `${safePercent}%`;
    document.getElementById('progress-thumb').style.left = `${safePercent}%`;
    document.getElementById('progress-percent').textContent = `${Math.round(safePercent)}%`;
}

function showEmptyState() {
    document.getElementById('video-player').setAttribute('data-empty-state', '');
    updatePlayIcon();
}

function formatTime(value) {
    if (!Number.isFinite(value)) return '00:00';
    const total = Math.max(0, Math.floor(value));
    const minutes = Math.floor(total / 60);
    const seconds = total % 60;
    return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showToast(message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = `
            position: fixed;
            bottom: 24px;
            right: 24px;
            z-index: 9999;
            display: flex;
            flex-direction: column;
            gap: 12px;
        `;
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    const colors = {
        success: 'rgba(16, 185, 129, 0.4)',
        error: 'rgba(239, 68, 68, 0.4)',
        warning: 'rgba(249, 115, 22, 0.4)',
        info: 'rgba(59, 130, 246, 0.4)'
    };
    toast.style.cssText = `
        padding: 14px 20px;
        background: rgba(20, 20, 40, 0.95);
        border: 1px solid ${colors[type] || colors.info};
        border-radius: 12px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
        color: #fff;
        font-size: 14px;
        animation: slideIn 0.3s ease;
        backdrop-filter: blur(20px);
    `;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100px)';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}
```

- [ ] **Step 2: Add JS expectation checks to `tests/test_video_player_links.py`**

Append this test method inside `VideoPlayerLinksTest`:

```python
    def test_video_player_script_wires_local_video_features(self):
        video_js = Path("js/video-player.js").read_text(encoding="utf-8")

        self.assertIn("const videoCatalog", video_js)
        self.assertIn("src: '/video/python-algorithm-03.mp4'", video_js)
        self.assertIn("localStorage.setItem(STORAGE_PREFIX", video_js)
        self.assertIn("function seekToNote(time)", video_js)
        self.assertIn("function launchDanmaku(text)", video_js)
        self.assertIn("SPEED_OPTIONS", video_js)
```

- [ ] **Step 3: Run the JS structure tests**

Run:

```bash
python -m unittest tests.test_video_player_links -v
```

Expected: PASS.

- [ ] **Step 4: Commit**

Run:

```bash
git add js/video-player.js tests/test_video_player_links.py
git commit -m "Wire local video player interactions"
```

---

### Task 5: Verification and Browser Check

**Files:**
- No source files expected unless verification exposes a defect.

- [ ] **Step 1: Run focused unit tests**

Run:

```bash
python -m unittest tests.test_video_static_route tests.test_video_player_links -v
```

Expected: PASS for all tests.

- [ ] **Step 2: Run hub navigation regression**

Run:

```bash
python -m unittest tests.test_hub_navigation -v
```

Expected: PASS. This confirms the existing hub entry still points to registered routes.

- [ ] **Step 3: Start the local FastAPI server**

Run:

```bash
python main.py
```

Expected: the app starts and logs a local URL such as `http://localhost:8000/hub.html`.

- [ ] **Step 4: Open the player page in a browser**

Visit:

```text
http://localhost:8000/video-player.html
```

Expected visual result:

- The page shows a large 16:9 player on the left.
- The right side has `选集` and `AI伴学笔记` tabs.
- Empty state text mentions placing files in `video/`.
- Clicking `AI伴学笔记` shows summary, timestamp notes, questions, and suggestion.
- Mobile width stacks the side panel below the player without overlapping controls.

- [ ] **Step 5: Optional real-video smoke check**

If a real file is available, place it at:

```text
video/python-algorithm-03.mp4
```

Refresh `/video-player.html`.

Expected: the empty state disappears after metadata loads, the play button starts playback, progress updates, and AI timestamp buttons jump the video time.

- [ ] **Step 6: Final commit if verification fixes were needed**

If no fixes were needed, skip this step. If fixes were made:

```bash
git add html/video-player.html css/video-player.css js/video-player.js main.py tests/test_video_player_links.py tests/test_video_static_route.py video/.gitkeep video/README.md
git commit -m "Verify holographic local video player"
```

---

## Self-Review

- Spec coverage: backend `/video/` route is covered by Task 1; Bilibili-style layout is covered by Tasks 2 and 3; AI companion notes are covered by Tasks 2 and 4; real `<video>` behavior, progress, speed, fullscreen, timestamp seek, and local danmaku are covered by Task 4; verification is covered by Task 5.
- Placeholder scan: this plan contains no `TBD`, `TODO`, or vague implementation steps. Each implementation step includes concrete code or an exact command.
- Type consistency: IDs and function names are consistent across HTML, CSS, JS, and tests: `course-video`, `episode-list`, `ai-notes-panel`, `note-timeline`, `seekToNote`, `launchDanmaku`, and `videoCatalog`.
