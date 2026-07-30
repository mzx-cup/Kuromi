"""家长月报生成器（M5.1 / #18）

聚合学生学习数据 → 人话 + 改进建议，定期通过 email/sms 推送给家长。

数据流：
  1. 收集学生当月学习数据（总时长 / 掌握 / 薄弱 / 连续打卡）
  2. 生成结构化 ParentReport（summary_text）
  3. send() 标记 delivered_at + 记录 channel/recipient

未来扩展：
  - LLM 生成更具针对性的家长建议
  - 实际接 SMTP / 微信推送
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("starlearn.report.parent")


@dataclass
class ParentReport:
    student_id: str
    period: str
    summary_text: str
    delivered_at: datetime | None = None
    metrics: dict = field(default_factory=dict)


class ParentReportGenerator:
    """家长月报生成器。"""

    async def generate(
        self,
        student_id: str,
        period: str,
        data: dict,
    ) -> ParentReport:
        """生成家长月报。"""
        topics_mastered = data.get("topics_mastered", [])
        topics_struggling = data.get("topics_struggling", [])
        total_minutes = int(data.get("total_minutes", 0))
        streak_days = int(data.get("streak_days", 0))

        hours = total_minutes // 60
        minutes = total_minutes % 60

        summary = (
            f"亲爱的家长，您的孩子在 {period} 期间：\n"
            f"- 总学习时长 {hours} 小时 {minutes} 分钟\n"
            f"- 掌握：{', '.join(topics_mastered) or '暂无'}\n"
            f"- 待加强：{', '.join(topics_struggling) or '无'}\n"
            f"- 连续打卡 {streak_days} 天\n"
            "建议：在家辅导时，多关注薄弱点，用生活场景举例。"
        )

        return ParentReport(
            student_id=student_id,
            period=period,
            summary_text=summary,
            metrics=dict(data),
        )

    async def send(
        self,
        report: ParentReport,
        channel: str,
        recipient: str,
    ) -> ParentReport:
        """标记报告已发送（占位实现，未来接真实通道）。"""
        report.delivered_at = datetime.utcnow()
        report.metrics["channel"] = channel
        report.metrics["recipient"] = recipient
        logger.info(
            f"[ParentReport] sent: student={report.student_id} "
            f"channel={channel} recipient={recipient}"
        )
        return report