"""db.py wrapper for gamification (garden/pet/achievements/eco).

全量委托 db.py 正式函数（双引擎 + 真实 schema：user_garden.seeds +
garden_json、user_pet.pet_json/pet_game_json、user_achievements.
achievements_json、user_eco_data.eco_data_json）。旧版本对这些表写的
归一化列（plants/last_watered/growth_points、name/level/happiness...、
eco_points/co2_saved_kg/...）只存在于测试 fixture 的想象 schema，
真实库全是 JSON blob。
"""
from __future__ import annotations

import json
from datetime import datetime

import db
from app.repositories.legacy._conn import legacy_scope

_GARDEN_DEFAULTS = {"plants": {}, "last_watered": None, "growth_points": 0}

_PET_DEFAULTS = {
    "name": "Pixel",
    "level": 1,
    "happiness": 50.0,
    "hunger": 50.0,
    "energy": 100.0,
    "last_fed": None,
}

_ECO_DEFAULTS = {
    "eco_points": 0,
    "co2_saved_kg": 0.0,
    "trees_planted": 0,
    "level": "Seedling",
}


def _as_dict(value) -> dict:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return dict(parsed) if isinstance(parsed, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}


class DbPyGamificationRepository:
    def __init__(self, db_path: str = None):
        # 保留参数兼容旧调用/测试；委托 db.py 后连接由生效后端决定
        # （legacy_scope 保证测试的 db_path 对委托调用同样生效）。
        self.db_path = db_path

    # ── user_garden ──

    def get_garden(self, user_id) -> dict:
        with legacy_scope(self.db_path):
            result = db.get_user_garden(user_id) or {}
        garden_data = _as_dict(result.get("garden_data"))
        out = dict(_GARDEN_DEFAULTS)
        out.update(garden_data)
        return out

    def save_garden(self, user_id, garden_data: dict) -> None:
        # 保留现有 seeds（契约形状里没有它，不能写丢）
        with legacy_scope(self.db_path):
            current = db.get_user_garden(user_id) or {}
        seeds = current.get("seeds") or 0
        out = dict(_GARDEN_DEFAULTS)
        out.update(garden_data or {})
        with legacy_scope(self.db_path):
            db.save_user_garden(user_id, seeds, out)

    # ── user_pet ──

    def get_pet(self, user_id) -> dict:
        with legacy_scope(self.db_path):
            result = db.get_user_pet(user_id) or {}
        out = dict(_PET_DEFAULTS)
        out.update(_as_dict(result.get("pet")))
        return out

    def save_pet(self, user_id, pet_data: dict) -> None:
        # save_user_pet 无条件写两个 json 列（None → '{}'），先读回
        # pet_game 再一并传回，避免把游戏进度清空。
        with legacy_scope(self.db_path):
            current = db.get_user_pet(user_id) or {}
        pet_game = _as_dict(current.get("pet_game"))
        out = dict(_PET_DEFAULTS)
        out.update(pet_data or {})
        with legacy_scope(self.db_path):
            db.save_user_pet(user_id, out, pet_game)

    # ── user_achievements ──

    @staticmethod
    def _achievements_list(raw) -> list:
        """achievements_json 兼容映射：list 直取，dict 取常见键。"""
        if isinstance(raw, list):
            return raw
        if isinstance(raw, dict):
            for key in ("achievements", "unlocked", "list", "items"):
                val = raw.get(key)
                if isinstance(val, list):
                    return val
            if raw:
                # 单个成就对象的形状 → 包成列表
                if "achievement_id" in raw or "title" in raw:
                    return [raw]
        return []

    def get_achievements(self, user_id) -> list:
        with legacy_scope(self.db_path):
            raw = db.get_user_achievements(user_id)
        achievements = self._achievements_list(raw)
        out = []
        for i, item in enumerate(achievements):
            if isinstance(item, str):
                item = {"achievement_id": item}
            if not isinstance(item, dict):
                continue
            out.append({
                "id": item.get("id", i + 1),
                "achievement_id": item.get("achievement_id", item.get("id", "")),
                "title": item.get("title", ""),
                "description": item.get("description", ""),
                "unlocked_at": item.get("unlocked_at"),
            })
        return out

    def save_achievement(self, user_id, achievement: dict) -> int:
        with legacy_scope(self.db_path):
            raw = db.get_user_achievements(user_id)
        achievements = self._achievements_list(raw)
        achievements.append({
            "achievement_id": achievement.get("achievement_id", ""),
            "title": achievement.get("title", ""),
            "description": achievement.get("description", ""),
            "unlocked_at": achievement.get("unlocked_at") or datetime.now().isoformat(),
        })
        with legacy_scope(self.db_path):
            db.save_user_achievements(user_id, achievements)
        return len(achievements)

    # ── user_eco_data ──

    def get_eco(self, user_id) -> dict:
        out = dict(_ECO_DEFAULTS)
        with legacy_scope(self.db_path):
            out.update(_as_dict(db.get_user_eco_data(user_id)))
        return out

    def save_eco(self, user_id, eco_data: dict) -> None:
        current = dict(_ECO_DEFAULTS)
        with legacy_scope(self.db_path):
            current.update(_as_dict(db.get_user_eco_data(user_id)))
        current.update(eco_data or {})
        with legacy_scope(self.db_path):
            db.save_user_eco_data(user_id, current)
