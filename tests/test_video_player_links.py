import unittest
from pathlib import Path


class VideoPlayerShellTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = Path("html/video-player.html").read_text(encoding="utf-8")

    def test_uses_local_course_video_instead_of_bilibili_embed(self):
        self.assertIn('id="course-video"', self.page)
        self.assertIn("<video", self.page)
        self.assertIn("data-empty-state", self.page)
        self.assertIn("video/", self.page)
        self.assertNotIn("www.bilibili.com", self.page)

    def test_contains_bilibili_style_theater_layout(self):
        for token in (
            "bili-theater",
            "player-column",
            "player-side-panel",
            "episode-list",
            "danmaku-form",
        ):
            self.assertIn(token, self.page)

    def test_contains_episode_and_ai_notes_tabs(self):
        for token in (
            'data-tab="episodes"',
            'data-tab="ai-notes"',
            "AI伴学笔记",
            "note-timeline",
            "重点问题",
        ):
            self.assertIn(token, self.page)

    def test_contains_local_video_empty_state_guidance(self):
        self.assertIn("请将视频放入 Kuromi 根目录的 video/ 文件夹", self.page)
        self.assertIn(".mp4 / .webm / .mov", self.page)


    def test_video_player_script_wires_local_video_features(self):
        video_js = Path("js/video-player.js").read_text(encoding="utf-8")

        self.assertIn("const videoCatalog", video_js)
        self.assertIn("src: '/video/python-algorithm-03.mp4'", video_js)
        self.assertIn("localStorage.setItem(STORAGE_PREFIX", video_js)
        self.assertIn("function seekToNote(time)", video_js)
        self.assertIn("function launchDanmaku(text)", video_js)
        self.assertIn("SPEED_OPTIONS", video_js)


if __name__ == "__main__":
    unittest.main()
