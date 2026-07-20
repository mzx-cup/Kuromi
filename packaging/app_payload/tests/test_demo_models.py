"""Verify the demo columns exist on the ORM models."""
from sqlalchemy import inspect

from app.models.classroom import ClassroomSession
from app.models.course import Chapter, Course, Subject, SubChapter


def test_subject_has_demo_columns():
    cols = {c.name for c in inspect(Subject).columns}
    assert "is_demo" in cols
    assert "demo_version" in cols


def test_course_has_demo_columns():
    cols = {c.name for c in inspect(Course).columns}
    assert "is_demo" in cols
    assert "demo_version" in cols


def test_chapter_has_demo_columns_and_json():
    cols = {c.name for c in inspect(Chapter).columns}
    assert "is_demo" in cols
    assert "demo_version" in cols
    assert "lecture" in cols
    assert "mindmap" in cols


def test_subchapter_has_demo_columns():
    cols = {c.name for c in inspect(SubChapter).columns}
    assert "is_demo" in cols
    assert "demo_version" in cols


def test_classroom_session_has_demo_columns():
    cols = {c.name for c in inspect(ClassroomSession).columns}
    assert "is_demo" in cols
    assert "demo_version" in cols
    assert "slides" in cols
