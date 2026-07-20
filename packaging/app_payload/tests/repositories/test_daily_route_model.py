"""Model test for DailyRoute ORM (Task C0)."""
from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.course_progress import DailyRoute
from app.models.user import User


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add(User(id="u1", username="u1", password_hash="h"))
    session.commit()
    yield session
    session.close()
    engine.dispose()


def test_daily_route_round_trips_tasks_and_completed(session):
    route = DailyRoute(
        user_id="u1",
        route_date=date(2026, 7, 13),
        tasks_json=["task-a", "task-b"],
        completed_json=["task-a"],
    )
    session.add(route)
    session.commit()

    fetched = (
        session.query(DailyRoute)
        .filter_by(user_id="u1", route_date=date(2026, 7, 13))
        .first()
    )
    assert fetched is not None
    assert fetched.tasks_json == ["task-a", "task-b"]
    assert fetched.completed_json == ["task-a"]


def test_daily_route_unique_per_user_date(session):
    """Two routes for the same user/date overwrite semantically."""
    session.add(
        DailyRoute(
            user_id="u1",
            route_date=date(2026, 7, 13),
            tasks_json=["a"],
            completed_json=[],
        )
    )
    session.commit()
    count = session.query(DailyRoute).filter_by(user_id="u1").count()
    assert count == 1
