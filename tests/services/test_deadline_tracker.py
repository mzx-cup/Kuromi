"""DeadlineTracker service — add_deadline + list_active + mark_done."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import patch


def test_add_deadline_calls_repository_insert():
    from app.services.learning_state import deadline_tracker as svc
    due = datetime(2026, 7, 20, 12, 0, 0)
    with patch.object(svc, "OrmDeadlineRepository") as MockRepo:
        MockRepo.return_value.insert.return_value = 7
        result = svc.add_deadline(
            user_id="u1", title="复习 Chapter 3", due_at=due,
        )
        assert result == 7
        MockRepo.return_value.insert.assert_called_once()
        entry = MockRepo.return_value.insert.call_args[0][0]
        assert entry.user_id == "u1"
        assert entry.title == "复习 Chapter 3"
        assert entry.due_at == due


def test_add_deadline_stores_supervised_by_rule_id():
    from app.services.learning_state import deadline_tracker as svc
    due = datetime(2026, 7, 20, 12, 0, 0)
    with patch.object(svc, "OrmDeadlineRepository") as MockRepo:
        MockRepo.return_value.insert.return_value = 9
        svc.add_deadline(
            user_id="u1", title="停滞提醒触发", due_at=due,
            supervised_by_rule_id="SUP-014",
        )
        entry = MockRepo.return_value.insert.call_args[0][0]
        assert entry.supervised_by_rule_id == "SUP-014"


def test_add_deadline_defaults_supervised_by_rule_id_to_none():
    from app.services.learning_state import deadline_tracker as svc
    due = datetime(2026, 7, 20, 12, 0, 0)
    with patch.object(svc, "OrmDeadlineRepository") as MockRepo:
        MockRepo.return_value.insert.return_value = 3
        svc.add_deadline(user_id="u1", title="普通 deadline", due_at=due)
        entry = MockRepo.return_value.insert.call_args[0][0]
        assert entry.supervised_by_rule_id is None


def test_list_active_returns_repository_results():
    from app.services.learning_state import deadline_tracker as svc
    fake_rows = [
        {"id": 1, "title": "task A", "due_at": datetime(2026, 7, 15, 0, 0, 0),
         "status": "pending", "supervised_by_rule_id": None},
        {"id": 2, "title": "task B", "due_at": datetime(2026, 7, 18, 0, 0, 0),
         "status": "pending", "supervised_by_rule_id": "SUP-014"},
    ]
    with patch.object(svc, "OrmDeadlineRepository") as MockRepo:
        MockRepo.return_value.list_active.return_value = fake_rows
        out = svc.list_active(user_id="u1")
        assert len(out) == 2
        assert out[0]["title"] == "task A"
        MockRepo.return_value.list_active.assert_called_once_with(user_id="u1")


def test_mark_done_proxies_to_repository():
    from app.services.learning_state import deadline_tracker as svc
    with patch.object(svc, "OrmDeadlineRepository") as MockRepo:
        MockRepo.return_value.mark_done.return_value = True
        assert svc.mark_done(deadline_id=42) is True
        MockRepo.return_value.mark_done.assert_called_once_with(deadline_id=42)