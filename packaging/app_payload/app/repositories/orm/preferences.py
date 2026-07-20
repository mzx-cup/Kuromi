"""SQLAlchemy implementation for user preferences, settings, and theme sync."""
from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.preferences import UserPreference, UserSetting, UserTheme


class SqlAlchemyPreferencesRepository:
    def __init__(self, session: Session = None):
        self.session = session

    def get_preferences(self, user_id: str) -> dict:
        rows = self.session.query(UserPreference).filter_by(user_id=user_id).all()
        return {row.key: row.value for row in rows}

    def set_preference(self, user_id: str, key: str, value: dict) -> None:
        existing = self.session.query(UserPreference).filter_by(user_id=user_id, key=key).first()
        if existing:
            existing.value = value
            existing.updated_at = datetime.now(timezone.utc)
        else:
            self.session.add(UserPreference(
                user_id=user_id, key=key, value=value,
                updated_at=datetime.now(timezone.utc),
            ))
        self.session.flush()

    def get_settings(self, user_id: str) -> dict:
        rows = self.session.query(UserSetting).filter_by(user_id=user_id).all()
        return {row.setting_key: row.setting_value for row in rows}

    def set_setting(self, user_id: str, key: str, value: str) -> None:
        existing = self.session.query(UserSetting).filter_by(user_id=user_id, setting_key=key).first()
        if existing:
            existing.setting_value = value
            existing.updated_at = datetime.now(timezone.utc)
        else:
            self.session.add(UserSetting(
                user_id=user_id, setting_key=key, setting_value=value,
                updated_at=datetime.now(timezone.utc),
            ))
        self.session.flush()

    def get_theme(self, user_id: str) -> dict:
        theme = self.session.query(UserTheme).filter_by(user_id=user_id).first()
        if not theme:
            return {"theme": "dark", "accent_color": "#7c3aed"}
        return {"theme": theme.theme, "accent_color": theme.accent_color}

    def set_theme(self, user_id: str, theme: str, accent_color: str = "#7c3aed") -> None:
        existing = self.session.query(UserTheme).filter_by(user_id=user_id).first()
        if existing:
            existing.theme = theme
            existing.accent_color = accent_color
            existing.updated_at = datetime.now(timezone.utc)
        else:
            self.session.add(UserTheme(
                user_id=user_id, theme=theme, accent_color=accent_color,
                updated_at=datetime.now(timezone.utc),
            ))
        self.session.flush()
