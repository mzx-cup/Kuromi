"""db.py wrapper for user preferences, settings, and theme sync.

全量委托 db.py 正式函数（双引擎 + 真实 schema）。旧版本直接对
``user_preferences(user_id, key, value)`` / ``user_settings(setting_key,
setting_value)`` / ``user_themes`` 写 SQL —— 这些表结构只存在于测试
fixture 的想象 schema，两个真实引擎里 user_preferences 是
preferences_json blob、user_settings 是 settings_json blob + 专用列、
user_themes 表根本不存在（主题存在 user.theme_prefs 列）。
"""
from __future__ import annotations

import db
from app.repositories.legacy._conn import legacy_scope

# user_settings 的专用列（独立于 settings_json blob 存储）
_SETTINGS_COLUMNS = ("weather_city", "hub_theme")

_DEFAULT_THEME = {"theme": "dark", "accent_color": "#7c3aed"}


class DbPyPreferencesRepository:
    def __init__(self, db_path: str = None):
        # 保留参数兼容旧调用/测试；委托 db.py 后连接由生效后端决定
        # （legacy_scope 保证测试的 db_path 对委托调用同样生效）。
        self.db_path = db_path

    def get_preferences(self, user_id: str) -> dict:
        """Return {key: value} dict for the user."""
        with legacy_scope(self.db_path):
            prefs = db.get_user_preferences(user_id)
        return prefs if isinstance(prefs, dict) else {}

    def set_preference(self, user_id: str, key: str, value: dict) -> None:
        prefs = self.get_preferences(user_id)
        prefs[key] = value
        with legacy_scope(self.db_path):
            db.save_user_preferences(user_id, prefs)

    def get_settings(self, user_id: str) -> dict:
        with legacy_scope(self.db_path):
            row = db.get_user_settings(user_id) or {}
        settings = dict(row.get("settings") or {})
        for col in _SETTINGS_COLUMNS:
            val = row.get(col)
            if val:
                settings.setdefault(col, val)
        return settings

    def set_setting(self, user_id: str, key: str, value: str) -> None:
        # 读全量再回写：save_user_settings 的 MySQL 分支是全列 upsert，
        # 只传 settings_data 会把 weather_city 等专用列冲成 ''。
        with legacy_scope(self.db_path):
            row = db.get_user_settings(user_id) or {}
        settings = dict(row.get("settings") or {})
        col_kwargs = {}
        if key in _SETTINGS_COLUMNS:
            col_kwargs[key] = value
        else:
            settings[key] = value
        with legacy_scope(self.db_path):
            db.save_user_settings(
                user_id,
                settings_data=settings,
                weather_city=row.get("weather_city"),
                floating_alarm_x=row.get("floating_alarm_x"),
                floating_alarm_y=row.get("floating_alarm_y"),
                hub_theme=row.get("hub_theme"),
                **col_kwargs,
            )

    def get_theme(self, user_id: str) -> dict:
        with legacy_scope(self.db_path):
            prefs = db.get_user_theme_prefs(user_id)
        if isinstance(prefs, dict) and prefs:
            theme = dict(_DEFAULT_THEME)
            theme.update(prefs)
            return theme
        return dict(_DEFAULT_THEME)

    def set_theme(self, user_id: str, theme: str, accent_color: str = "#7c3aed") -> None:
        with legacy_scope(self.db_path):
            db.save_user_theme_prefs(user_id, {"theme": theme, "accent_color": accent_color})
