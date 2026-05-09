import unittest

from app.services.dashboard_data import (
    build_calendar_payload,
    build_focus_event,
    build_focus_payload,
    build_progress_summary,
)


class DashboardDataTest(unittest.TestCase):
    def test_progress_summary_uses_real_sessions_goals_and_mastery(self):
        summary = build_progress_summary(
            user_id=1,
            range_key="month",
            today="2026-05-07",
            stats={"daily_minutes": {"2026-05-01": 60, "2026-05-02": 30, "2026-05-07": 120}},
            sessions=[
                {"session_date": "2026-05-07", "duration_minutes": 90, "subject": "数学"},
                {"session_date": "2026-05-02", "duration_minutes": 30, "subject": "编程"},
            ],
            goals=[
                {"title": "数学冲刺", "current_value": 40, "target_value": 80, "unit": "分钟"},
            ],
            mastery=[
                {"name": "函数", "mastery": 75, "subject": "数学"},
                {"name": "循环", "mastery": 50, "subject": "编程"},
            ],
        )

        self.assertEqual(summary["total_minutes"], 210)
        self.assertEqual(summary["study_days"], 3)
        self.assertEqual(summary["current_streak"], 1)
        self.assertEqual(summary["completed_courses"], 0)
        self.assertEqual(summary["course_progress"][0]["name"], "数学")
        self.assertEqual(summary["course_progress"][0]["progress"], 63)
        self.assertEqual(len(summary["weekly_activity"]), 7)

    def test_calendar_payload_merges_events_and_sessions(self):
        payload = build_calendar_payload(
            events_data={
                "2026-05-07": [
                    {"name": "算法计划", "duration": "2h", "category": "algorithm", "done": False}
                ]
            },
            sessions=[
                {"session_date": "2026-05-07", "duration_minutes": 45, "subject": "算法"},
                {"session_date": "2026-05-08", "duration_minutes": 30, "subject": "英语"},
            ],
            today="2026-05-07",
        )

        self.assertEqual(payload["days"]["2026-05-07"]["status"], "partial")
        self.assertEqual(payload["days"]["2026-05-08"]["status"], "completed")
        self.assertEqual(payload["month_summary"]["study_days"], 2)
        self.assertEqual(payload["month_summary"]["total_minutes"], 75)

    def test_focus_payload_prefers_history_and_has_empty_defaults(self):
        empty = build_focus_payload([])
        self.assertEqual(empty["score"], 0)
        self.assertEqual(empty["timeline"], [])

        payload = build_focus_payload([
            {"score": 80, "type": "deep", "timestamp": "2026-05-07T09:00:00"},
            {"score": 45, "type": "warning", "timestamp": "2026-05-07T10:00:00"},
        ])
        self.assertEqual(payload["score"], 63)
        self.assertEqual(payload["segments"]["deep"], 1)
        self.assertEqual(payload["segments"]["warning"], 1)

    def test_focus_event_scores_learning_and_switching_signals(self):
        deep = build_focus_event(
            study_minutes=20,
            focus_minutes=25,
            page_switches=0,
            completed_focus=True,
            timestamp="2026-05-09T10:00:00",
            source="focus_complete",
        )
        self.assertEqual(deep["type"], "deep")
        self.assertGreaterEqual(deep["score"], 85)

        warning = build_focus_event(
            study_minutes=0,
            focus_minutes=0,
            page_switches=8,
            completed_focus=False,
            timestamp="2026-05-09T10:05:00",
            source="page_switch",
        )
        self.assertEqual(warning["type"], "warning")
        self.assertLess(warning["score"], 55)


if __name__ == "__main__":
    unittest.main()
