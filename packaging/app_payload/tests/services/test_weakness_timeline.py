"""WeaknessTimeline service — record_snapshot + recent."""
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock


def test_record_snapshot_calls_repository_insert():
    from app.services.learning_state import weakness_timeline as svc
    with patch.object(svc, "OrmWeaknessTimelineRepository") as MockRepo:
        MockRepo.return_value.insert.return_value = 42
        result = svc.record_snapshot(
            user_id="u1", dim="knowledge_base", score=0.6,
            evidence_kb_nodes=["KB-CON-0001"],
        )
        assert result == 42
        MockRepo.return_value.insert.assert_called_once()
        entry = MockRepo.return_value.insert.call_args[0][0]
        assert entry.user_id == "u1"
        assert entry.dim == "knowledge_base"
        assert entry.score == 0.6
        assert entry.evidence_kb_nodes == ["KB-CON-0001"]


def test_record_snapshot_defaults_evidence_to_empty_list():
    """evidence_kb_nodes=None must default to []."""
    from app.services.learning_state import weakness_timeline as svc
    with patch.object(svc, "OrmWeaknessTimelineRepository") as MockRepo:
        MockRepo.return_value.insert.return_value = 1
        svc.record_snapshot(user_id="u1", dim="engagement", score=0.4)
        entry = MockRepo.return_value.insert.call_args[0][0]
        assert entry.evidence_kb_nodes == []


def test_recent_returns_repository_results():
    from app.services.learning_state import weakness_timeline as svc
    fake_rows = [
        {"id": 1, "dim": "knowledge_base", "score": 0.7,
         "evidence_kb_nodes": ["KB-CON-0001"], "snapshot_at": datetime.utcnow()},
    ]
    with patch.object(svc, "OrmWeaknessTimelineRepository") as MockRepo:
        MockRepo.return_value.recent.return_value = fake_rows
        out = svc.recent(user_id="u1", dim="knowledge_base", within_days=7)
        assert len(out) == 1
        assert out[0]["score"] == 0.7
        MockRepo.return_value.recent.assert_called_once_with(
            user_id="u1", dim="knowledge_base", within_days=7
        )


def test_recent_uses_default_window_of_7_days():
    from app.services.learning_state import weakness_timeline as svc
    with patch.object(svc, "OrmWeaknessTimelineRepository") as MockRepo:
        MockRepo.return_value.recent.return_value = []
        svc.recent(user_id="u1", dim="engagement")
        MockRepo.return_value.recent.assert_called_once_with(
            user_id="u1", dim="engagement", within_days=7
        )


def test_recent_returns_empty_list_when_no_snapshots():
    from app.services.learning_state import weakness_timeline as svc
    with patch.object(svc, "OrmWeaknessTimelineRepository") as MockRepo:
        MockRepo.return_value.recent.return_value = []
        assert svc.recent(user_id="u1", dim="knowledge_base", within_days=30) == []
