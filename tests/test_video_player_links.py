import unittest
from pathlib import Path


class VideoPlayerShellTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = Path("html/video-player.html").read_text(encoding="utf-8")

    def test_dual_player_elements_present(self):
        """Both local video and bilibili iframe elements exist."""
        self.assertIn('id="course-video-local"', self.page)
        self.assertIn('id="course-video-bilibili"', self.page)
        self.assertIn("<video", self.page)
        self.assertIn("data-empty-state", self.page)

    def test_contains_bilibili_style_theater_layout(self):
        for token in (
            "bili-theater",
            "player-column",
            "player-side-panel",
            "episode-list",
            "danmaku-form",
        ):
            self.assertIn(token, self.page)

    def test_three_tabs_courses_playlist_ai_notes(self):
        for token in (
            'data-tab="courses"',
            'data-tab="playlist"',
            'data-tab="ai-notes"',
            "课程库",
            "我的列表",
            "AI伴学笔记",
            "note-timeline",
            "重点问题",
        ):
            self.assertIn(token, self.page)

    def test_no_bilibili_branding(self):
        self.assertNotIn("B站视频学习驾驶舱", self.page)
        self.assertNotIn("B站 已接入", self.page)

    def test_contains_modal_and_course_playlist_elements(self):
        for token in (
            "add-course-modal",
            "add-course-btn",
            "course-search",
            "playlist-episode-list",
        ):
            self.assertIn(token, self.page)

    def test_contains_unified_control_bar(self):
        for token in (
            "speed-btn",
            "volume-btn",
            "fullscreen-btn",
            "progress-track",
        ):
            self.assertIn(token, self.page)

    def test_empty_state_guidance(self):
        self.assertIn("添加你的第一个学习视频", self.page)
        self.assertIn("bilibili.com", self.page)
        self.assertIn("BV 号", self.page)

    def test_video_player_script_wires_dual_drivers(self):
        video_js = Path("js/video-player.js").read_text(encoding="utf-8")

        # Dual driver pattern
        self.assertIn("BilibiliDriver", video_js)
        self.assertIn("LocalDriver", video_js)
        self.assertIn("videoController", video_js)

        # postMessage API for B站 control
        self.assertIn("postMessage", video_js)
        self.assertIn("callPlayer", video_js)
        self.assertIn("player.bilibili.com", video_js)

        # Course library and playlist API endpoints
        self.assertIn("/api/video-courses", video_js)
        self.assertIn("/api/video-playlists", video_js)
        self.assertIn("/api/playlist-videos", video_js)
        self.assertIn("/api/bilibili/info", video_js)

        # Control features
        self.assertIn("SPEED_OPTIONS", video_js)
        self.assertIn("function launchDanmaku(text)", video_js)
        self.assertIn("localStorage.setItem(STORAGE_PREFIX", video_js)
        self.assertIn("showToast", video_js)

        # No more hardcoded video catalog
        self.assertNotIn("const videoCatalog", video_js)
        self.assertNotIn("python-algorithm-03.mp4", video_js)


if __name__ == "__main__":
    unittest.main()
