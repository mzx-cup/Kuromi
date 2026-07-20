"""SQLAlchemy models for gamification (M8).

This slice introduces normalized gamification storage backing the
garden / pet / achievements / eco-data features. Four tables:

* ``user_garden``       – virtual garden state (plants + growth points)
* ``user_pet``          – virtual pet state (name, level, hunger, etc.)
* ``user_achievements`` – unlocked badges / milestones
* ``user_eco_data``     – eco-points / sustainability stats

The repositories expose get/save pairs that mirror the
``db.py`` wrappers so callers can swap implementations behind the
:class:`app.repositories.base.GamificationRepository` Protocol.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, DateTime, Float, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class UserGarden(Base):
    """Virtual garden state (replaces db.py user_garden)."""
    __tablename__ = "user_garden"

    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), primary_key=True)
    plants_json: Mapped[dict] = mapped_column(JSON, default=dict)
    last_watered: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    growth_points: Mapped[int] = mapped_column(Integer, default=0)


class UserPet(Base):
    """Virtual pet state (replaces db.py user_pet)."""
    __tablename__ = "user_pet"

    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), default="Pixel")
    level: Mapped[int] = mapped_column(Integer, default=1)
    happiness: Mapped[float] = mapped_column(Float, default=50.0)
    hunger: Mapped[float] = mapped_column(Float, default=50.0)
    energy: Mapped[float] = mapped_column(Float, default=100.0)
    last_fed: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class UserAchievement(Base):
    """A single unlocked achievement/badge for a user."""
    __tablename__ = "user_achievements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    achievement_id: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(256), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    unlocked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.utcnow())


class UserEcoData(Base):
    """Eco-points / sustainability stats (replaces db.py user_eco_data)."""
    __tablename__ = "user_eco_data"

    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), primary_key=True)
    eco_points: Mapped[int] = mapped_column(Integer, default=0)
    co2_saved_kg: Mapped[float] = mapped_column(Float, default=0.0)
    trees_planted: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[str] = mapped_column(String(32), default="Seedling")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.utcnow())