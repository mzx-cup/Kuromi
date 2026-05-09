import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from main import VIDEO_DIR, app


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

    def test_serves_existing_mp4_file(self):
        video_path = Path(VIDEO_DIR) / "test-route-sample.mp4"
        video_bytes = b"fake video bytes"
        client = TestClient(app)

        video_path.write_bytes(video_bytes)
        try:
            response = client.get("/video/test-route-sample.mp4")

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content, video_bytes)
            self.assertTrue(response.headers["content-type"].startswith("video/mp4"))
        finally:
            video_path.unlink(missing_ok=True)

    def test_missing_video_file_returns_404(self):
        client = TestClient(app)

        response = client.get("/video/missing-route-sample.mp4")

        self.assertEqual(response.status_code, 404)

    def test_non_video_file_returns_404(self):
        client = TestClient(app)

        response = client.get("/video/README.md")

        self.assertEqual(response.status_code, 404)

    def test_local_video_api_lists_real_video_files(self):
        video_path = Path(VIDEO_DIR) / "__test_本地 视频(Av123,P1).mp4"
        client = TestClient(app)

        video_path.write_bytes(b"fake video bytes")
        try:
            response = client.get("/api/local-videos")

            self.assertEqual(response.status_code, 200)
            videos = response.json()["videos"]
            sample = next((item for item in videos if item["filename"] == video_path.name), None)
            self.assertIsNotNone(sample)
            self.assertEqual(sample["title"], "__test_本地 视频")
            self.assertIn("%E6%9C%AC%E5%9C%B0", sample["src"])
            self.assertTrue(sample["src"].startswith("/video/"))
        finally:
            video_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
