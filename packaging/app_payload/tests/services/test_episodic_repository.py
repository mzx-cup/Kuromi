"""EpisodicMemory service — record_event + recent_unconsolidated."""
from __future__ import annotations

from unittest.mock import patch


def test_record_event_calls_repository_insert():
    from app.services.memory import episodic_memory as svc
    with patch.object(svc, "OrmEpisodicMemoryRepository") as MockRepo:
        MockRepo.return_value.insert.return_value = 42
        result = svc.record_event(
            user_id="u1",
            event_type="conversation",
            summary="Socratic turn about photosynthesis",
        )
        assert result == 42
        MockRepo.return_value.insert.assert_called_once()
        entry = MockRepo.return_value.insert.call_args[0][0]
        assert entry.user_id == "u1"
        assert entry.event_type == "conversation"
        assert entry.summary == "Socratic turn about photosynthesis"
        # consolidated_into defaults to None (unconsolidated)
        assert entry.consolidated_into is None


def test_record_event_defaults_metadata_to_none():
    """event_metadata=None must propagate to the entry as None (not {})."""
    from app.services.memory import episodic_memory as svc
    with patch.object(svc, "OrmEpisodicMemoryRepository") as MockRepo:
        MockRepo.return_value.insert.return_value = 1
        svc.record_event(
            user_id="u1",
            event_type="session_start",
            summary="user opened a session",
        )
        entry = MockRepo.return_value.insert.call_args[0][0]
        assert entry.event_metadata is None


def test_recent_unconsolidated_calls_repository():
    from app.services.memory import episodic_memory as svc

    class FakeEpisode:
        def __init__(self, id, event_type, summary, event_metadata):
            self.id = id
            self.event_type = event_type
            self.summary = summary
            self.event_metadata = event_metadata
            self.consolidated_into = None

    fake_rows = [
        FakeEpisode(1, "conversation", "turn A", None),
        FakeEpisode(2, "quiz_attempt", "turn B", {"score": 0.7}),
    ]
    with patch.object(svc, "OrmEpisodicMemoryRepository") as MockRepo:
        MockRepo.return_value.recent_unconsolidated.return_value = fake_rows
        out = svc.recent_unconsolidated(user_id="u1", days=14)
        assert len(out) == 2
        assert out[0].summary == "turn A"
        assert out[1].event_metadata == {"score": 0.7}
        MockRepo.return_value.recent_unconsolidated.assert_called_once_with(
            user_id="u1", days=14,
        )


def test_recent_unconsolidated_uses_default_7d_window():
    from app.services.memory import episodic_memory as svc
    with patch.object(svc, "OrmEpisodicMemoryRepository") as MockRepo:
        MockRepo.return_value.recent_unconsolidated.return_value = []
        svc.recent_unconsolidated(user_id="u1")
        MockRepo.return_value.recent_unconsolidated.assert_called_once_with(
            user_id="u1", days=7,
        )


def test_recent_unconsolidated_returns_empty_list_when_none():
    from app.services.memory import episodic_memory as svc
    with patch.object(svc, "OrmEpisodicMemoryRepository") as MockRepo:
        MockRepo.return_value.recent_unconsolidated.return_value = []
        assert svc.recent_unconsolidated(user_id="u1", days=7) == []