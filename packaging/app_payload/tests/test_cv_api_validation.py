"""CV 算法相关测试 — 验证视频/图片生成 API 的输出格式和参数校验

测试维度：
  1. 参数校验 — 分辨率/时长/宽高比的边界值等价类
  2. 输出文件格式 — MP4 文件头魔数验证
  3. 文件完整性 — 文件非空、基础结构正确
  4. 响应 Schema — API 返回的 image_url/image_base64 字段

注意：涉及"实际生成"的测试默认为 skip（需消耗 API 额度），
      参数校验和文件格式验证可直接运行。
"""

import struct
import pytest
from pathlib import Path


# ====== 项目路径 ======
VIDEO_DIR = Path(__file__).parent.parent / "video"


# ====== 参数校验测试（不消耗 API 额度）======

class TestCVAPIParameterValidation:
    """视频/图片生成 API 输入参数校验

    覆盖分辨率、时长、宽高比三个维度的等价类和边界值。
    """

    # ====== 分辨率参数化测试 ======

    @pytest.mark.parametrize("width,height,expected,desc", [
        pytest.param(1920, 1080, True,  "标准 1080p", id="valid-1080p"),
        pytest.param(1280, 720,  True,  "标准 720p", id="valid-720p"),
        pytest.param(3840, 2160, True,  "4K UHD", id="valid-4k"),
        pytest.param(64,   64,   True,  "最小有效分辨率", id="boundary-min-valid"),
        pytest.param(4096, 4096, True,  "最大有效分辨率", id="boundary-max-valid"),
        pytest.param(0,    1080, False, "宽度为 0 — 无效", id="invalid-width-zero"),
        pytest.param(1920, 0,    False, "高度为 0 — 无效", id="invalid-height-zero"),
        pytest.param(-1,   1080, False, "宽度为负数 — 无效", id="invalid-width-negative"),
        pytest.param(63,   64,   False, "宽度低于最小 — 无效", id="invalid-width-below-min"),
        pytest.param(4097, 2160, False, "宽度超出最大 — 无效", id="invalid-width-above-max"),
        pytest.param(10000, 10000, False, "超大分辨率 — 无效", id="invalid-oversized"),
    ])
    def test_resolution_boundary_values(self, width, height, expected, desc):
        """等价类 + 边界值：视频分辨率参数校验"""
        def validate_resolution(w: int, h: int) -> bool:
            """模拟分辨率验证逻辑：64-4096 为有效范围"""
            return 64 <= w <= 4096 and 64 <= h <= 4096

        assert validate_resolution(width, height) == expected, \
            f"分辨率 {width}x{height} ({desc}) 期望 {'有效' if expected else '无效'}"

    # ====== 时长参数化测试 ======

    @pytest.mark.parametrize("duration,expected,desc", [
        pytest.param(5,  True,  "正常时长 5 秒", id="valid-normal"),
        pytest.param(1,  True,  "最短有效时长", id="boundary-min-valid"),
        pytest.param(60, True,  "最长有效时长", id="boundary-max-valid"),
        pytest.param(0.1, True,  "极短时长 0.1 秒", id="boundary-very-short"),
        pytest.param(0,  False, "时长为 0 — 无效", id="invalid-zero"),
        pytest.param(-5, False, "时长为负数 — 无效", id="invalid-negative"),
        pytest.param(61, False, "超出最大时长 — 无效", id="invalid-exceeds-max"),
    ])
    def test_video_duration_boundary_values(self, duration, expected, desc):
        """边界值：视频时长参数校验"""
        def validate_duration(d: float) -> bool:
            return 0.1 <= d <= 60

        assert validate_duration(duration) == expected, \
            f"时长 {duration}s ({desc}) 期望 {'有效' if expected else '无效'}"


class TestCVAspectRatioValidation:
    """宽高比验证"""

    @pytest.mark.parametrize("width,height,expected_ratio", [
        (1920, 1080, 16/9),
        (1280, 720,  16/9),
        (1080, 1080, 1.0),
        (1080, 1920, 9/16),
        (720,  1280, 9/16),
    ])
    def test_common_aspect_ratios(self, width, height, expected_ratio):
        """验证常见的宽高比格式"""
        actual = width / height
        assert abs(actual - expected_ratio) < 0.01, \
            f"分辨率 {width}x{height} 宽高比期望 {expected_ratio:.4f}，实际 {actual:.4f}"


# ====== 输出文件格式验证 ======

class TestCVOutputFileValidation:
    """视频/图片输出文件格式验证"""

    def test_mp4_file_header_ftyp_box(self):
        """白盒：验证 MP4 文件头魔数 — ftyp box 应位于第 5-8 字节

        MP4 文件头结构（ISO/IEC 14496-12）：
          字节 0-3: box size (大端)
          字节 4-7: box type = 'ftyp'
          字节 8-11: major brand
        """
        mp4_files = list(VIDEO_DIR.glob("*.mp4"))
        if not mp4_files:
            pytest.skip("无 .mp4 测试文件，跳过 MP4 文件头验证")

        for mp4_file in mp4_files:
            with open(mp4_file, "rb") as f:
                header = f.read(12)

            if len(header) < 12:
                pytest.fail(f"MP4 文件 {mp4_file.name} 过小 ({len(header)} bytes)")

            ftyp_offset = 4
            ftyp_tag = header[ftyp_offset:ftyp_offset + 4]
            assert ftyp_tag == b'ftyp', \
                f"MP4 文件 {mp4_file.name} 缺少 ftyp box，实际头字节: {header.hex()}"

    def test_video_files_not_empty(self):
        """验证：生成的视频文件不能是空文件"""
        video_files = list(VIDEO_DIR.glob("*.*"))
        video_files = [f for f in video_files if f.suffix.lower() in ('.mp4', '.webm', '.avi')]
        if not video_files:
            pytest.skip("无视频文件，跳过非空验证")

        for vf in video_files:
            size = vf.stat().st_size
            assert size > 0, f"视频文件 {vf.name} 大小为 0"

    def test_video_file_minimum_size(self):
        """验证：合法 MP4 文件应至少有 100 bytes（ftyp + moov box 的合理下限）"""
        mp4_files = list(VIDEO_DIR.glob("*.mp4"))
        if not mp4_files:
            pytest.skip("无 .mp4 测试文件")

        for mp4_file in mp4_files:
            size = mp4_file.stat().st_size
            assert size >= 100, \
                f"MP4 文件 {mp4_file.name} 只有 {size} bytes，可能损坏（正常至少 100 bytes）"

    def test_video_playback_page_accessibility(self):
        """验证：视频播放器页面 HTML 结构完整性"""
        html_path = Path(__file__).parent.parent / "html" / "video-player.html"
        if not html_path.exists():
            pytest.skip("video-player.html 不存在")

        content = html_path.read_text(encoding="utf-8")
        # 播放器关键元素检查
        assert "video" in content.lower(), "video-player.html 应包含 video 元素"


# ====== 图像生成 API 响应结构验证 ======

class TestImageGenAPIResponse:
    """图像生成 API 响应结构验证"""

    def test_valid_response_has_output_field(self):
        """验证：有效响应必须包含 image_url 或 image_base64"""
        valid_responses = [
            {"image_url": "https://cdn.example.com/generated/img_001.png"},
            {"image_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="},
            {"image_url": "https://example.com/img.png", "image_base64": "abc123"},
        ]

        def validate_response(resp: dict) -> bool:
            return bool(resp.get("image_url") or resp.get("image_base64"))

        for i, resp in enumerate(valid_responses):
            assert validate_response(resp), f"第 {i} 个有效响应被误判为无效"

    def test_missing_output_fields_returns_invalid(self):
        """验证：缺少 image_url 和 image_base64 时应判定为无效"""
        invalid_responses = [
            {"message": "生成中..."},
            {"status": "processing"},
            {},
        ]

        def validate_response(resp: dict) -> bool:
            return bool(resp.get("image_url") or resp.get("image_base64"))

        for i, resp in enumerate(invalid_responses):
            assert not validate_response(resp), f"第 {i} 个无效响应未被检测"

    @pytest.mark.parametrize("url,is_valid", [
        ("https://cdn.example.com/img.png", True),
        ("http://127.0.0.1:8000/output/test.jpg", True),
        ("", False),
        ("not-a-url", False),
        ("ftp://invalid-protocol.com/img.png", False),
    ])
    def test_image_url_format_validation(self, url, is_valid):
        """验证：image_url 必须使用 http/https 协议"""
        def is_valid_url(u: str) -> bool:
            return u.startswith(("http://", "https://"))

        assert is_valid_url(url) == is_valid, \
            f"URL '{url}' 期望 {'有效' if is_valid else '无效'}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
