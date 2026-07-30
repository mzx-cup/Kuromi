"""认知风格识别（M5.2 / #19）

视觉 / 听觉 / 动觉 三分法，基于页面停留时长聚类。

输入：behavior dict（各类型页面平均停留秒数）
输出：{
    primary: "visual" | "auditory" | "kinesthetic",
    confidence: 0.0~1.0,
    scores: {visual, auditory, kinesthetic}
}

简化实现：取停留时间最长的渠道作为 primary；confidence = max/total。
"""
from __future__ import annotations


class StyleRecognizer:
    """认知风格识别器（基于行为聚类的简化版）。"""

    CHANNELS = ("visual", "auditory", "kinesthetic")

    # behavior key → 风格映射
    KEY_MAP = {
        "visual": "image_page_avg_dwell_seconds",
        "auditory": "audio_page_avg_dwell_seconds",
        "kinesthetic": "code_editor_avg_dwell_seconds",
    }

    def classify(self, behavior: dict) -> dict:
        """根据行为数据判断主要风格。"""
        scores: dict[str, float] = {}
        for style in self.CHANNELS:
            key = self.KEY_MAP[style]
            scores[style] = float(behavior.get(key, 0))

        # 边界：所有分数都是 0
        total = sum(scores.values())
        if total <= 0:
            return {
                "primary": "visual",
                "confidence": 0.0,
                "scores": scores,
            }

        primary = max(scores, key=scores.get)
        confidence = round(scores[primary] / total, 2)
        return {
            "primary": primary,
            "confidence": confidence,
            "scores": scores,
        }