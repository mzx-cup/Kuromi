"""
5-Level Course Hierarchy:
  Subject -> Course -> Chapter -> SubChapter -> KnowledgePoint

Used for both AI-generated courses and B站-imported video courses.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Subject(Base):
    """Top-level subject category (e.g., 计算机科学, 数学)."""
    __tablename__ = "subjects"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    icon: Mapped[str] = mapped_column(String(32), default="default")
    visible: Mapped[bool] = mapped_column(default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    courses: Mapped[list["Course"]] = relationship(back_populates="subject", order_by="Course.sort_order")


class Course(Base):
    """Course belongs to a Subject (e.g., 计算机基础入门 under 计算机科学)."""
    __tablename__ = "courses"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    subject_id: Mapped[str] = mapped_column(String(64), ForeignKey("subjects.id"), nullable=False, default="")
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    bvid: Mapped[str] = mapped_column(String(32), default="")
    playlist_url: Mapped[str] = mapped_column(String(512), default="")
    cover_url: Mapped[str] = mapped_column(String(512), default="")
    author_name: Mapped[str] = mapped_column(String(128), default="")
    total_lessons: Mapped[int] = mapped_column(Integer, default=0)
    total_duration: Mapped[int] = mapped_column(Integer, default=0)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    visible: Mapped[bool] = mapped_column(default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    student_id: Mapped[str] = mapped_column(String(64), default="")
    outlines: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    scenes: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    data_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    subject: Mapped["Subject"] = relationship(back_populates="courses")
    chapters: Mapped[list["Chapter"]] = relationship(back_populates="course", order_by="Chapter.sort_order")


class Chapter(Base):
    """Chapter groups SubChapters (e.g., 第一章：计算机组成原理)."""
    __tablename__ = "chapters"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    course_id: Mapped[str] = mapped_column(String(64), ForeignKey("courses.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    course: Mapped["Course"] = relationship(back_populates="chapters")
    subchapters: Mapped[list["SubChapter"]] = relationship(back_populates="chapter", order_by="SubChapter.sort_order")


class SubChapter(Base):
    """SubChapter is a single learning unit (e.g., one B站 video page)."""
    __tablename__ = "subchapters"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    chapter_id: Mapped[str] = mapped_column(String(64), ForeignKey("chapters.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    bvid: Mapped[str] = mapped_column(String(32), default="")
    cid: Mapped[int] = mapped_column(Integer, default=0)
    page: Mapped[int] = mapped_column(Integer, default=1)
    duration: Mapped[int] = mapped_column(Integer, default=0)
    type: Mapped[str] = mapped_column(String(32), default="video")
    completed: Mapped[bool] = mapped_column(default=False)
    transcript: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    chapter: Mapped["Chapter"] = relationship(back_populates="subchapters")
    knowledge_points: Mapped[list["KnowledgePoint"]] = relationship(back_populates="subchapter")


class KnowledgePoint(Base):
    """Knowledge point extracted from a SubChapter for review/reinforcement."""
    __tablename__ = "knowledge_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subchapter_id: Mapped[str] = mapped_column(String(64), ForeignKey("subchapters.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    content: Mapped[str] = mapped_column(Text, default="")
    difficulty: Mapped[str] = mapped_column(String(16), default="medium")
    mastered: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    subchapter: Mapped["SubChapter"] = relationship(back_populates="knowledge_points")


class SceneOutline(Base):
    __tablename__ = "scene_outlines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_id: Mapped[str] = mapped_column(String(64), nullable=False)
    scene_index: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(256), default="")
    scene_type: Mapped[str] = mapped_column(String(32), default="slide")
    key_points: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Slide(Base):
    __tablename__ = "slides"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_id: Mapped[str] = mapped_column(String(64), nullable=False)
    scene_index: Mapped[int] = mapped_column(Integer, nullable=False)
    slide_index: Mapped[int] = mapped_column(Integer, default=0)
    layout: Mapped[str] = mapped_column(String(32), default="blank")
    elements: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
