import unittest
from pathlib import Path


PYTHON_INTRO_VIDEO_URL = "https://www.bilibili.com/video/BV1hxQBYcE5C/"


class VideoPlayerLinksTest(unittest.TestCase):
    def test_python_intro_video_link_is_available_in_curriculum(self):
        hub_html = Path("html/video-player.html").read_text(encoding="utf-8")

        self.assertIn("Python 基础入门", hub_html)
        self.assertIn(PYTHON_INTRO_VIDEO_URL, hub_html)
        self.assertIn("data-video-url", hub_html)

    def test_video_player_opens_external_video_links(self):
        video_player_js = Path("js/video-player.js").read_text(encoding="utf-8")

        self.assertIn("dataset.videoUrl", video_player_js)
        self.assertIn("window.open(videoUrl, '_blank', 'noopener,noreferrer')", video_player_js)

    def test_holographic_video_page_uses_learning_theater_layout(self):
        video_html = Path("html/video-player.html").read_text(encoding="utf-8")

        self.assertIn("learning-theater", video_html)
        self.assertIn("stage-panel", video_html)
        self.assertIn("learning-rail", video_html)
        self.assertIn("本节重点", video_html)
        self.assertIn("学习轨道", video_html)
        self.assertIn("继续学习", video_html)

    def test_left_stage_is_labeled_as_preview_not_real_video(self):
        video_html = Path("html/video-player.html").read_text(encoding="utf-8")

        self.assertIn("学习进度预览", video_html)
        self.assertIn("点击预览当前章节", video_html)
        self.assertIn("右侧推荐入口可打开完整视频", video_html)
        self.assertNotIn("点击播放课程视频", video_html)


if __name__ == "__main__":
    unittest.main()
