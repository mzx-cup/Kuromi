"""SQLAlchemy models for user preferences, settings, and theme sync."""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class UserPreference(Base):
    """Per-user preference key-value store (replaces db.py user_preferences)."""
    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    value: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.utcnow())


class UserSetting(Base):
    """Per-user simple settings (replaces db.py user_settings)."""
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    setting_key: Mapped[str] = mapped_column(String(128), nullable=False)
    setting_value: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.utcnow())


class UserTheme(Base):
    """Per-user theme preference (replaces db.py theme sync data)."""
    __tablename__ = "user_themes"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    theme: Mapped[str] = mapped_column(String(32), default="dark")
    accent_color: Mapped[str] = mapped_column(String(16), default="#7c3aed")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.utcnow())
