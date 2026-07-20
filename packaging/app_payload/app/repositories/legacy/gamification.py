"""db.py wrapper for gamification (garden/pet/achievements/eco).

Provides read/write methods against the db.py tables
``user_garden``, ``user_pet``, ``user_achievements`` and
``user_eco_data`` while M8 gradually shifts the read path to
SQLAlchemy.

Only storage operations are exposed here; the gamification formula
itself continues to live in higher-level services.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime


class DbPyGamificationRepository:
    def __init__(self, db_path: str = None):
        # Use the absolute path from db.py so legacy reads open the same
        # SQLite file the rest of the project uses (CWD-agnostic).
        import db as _db
        self.db_path = db_path or _db.SQLITE_PATH

    def _conn(self):
        return sqlite3.connect(self.db_path)

    # ── user_garden ──

    def get_garden(self, user_id) -> dict:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT plants, last_watered, growth_points FROM user_garden WHERE user_id = ?",
                (user_id,),
            )
            row = cur.fetchone()
            if not row:
                return {"plants": {}, "last_watered": None, "growth_points": 0}
            try:
                plants = json.loads(row[0]) if row[0] else {}
            except (json.JSONDecodeError, TypeError):
                plants = {}
            return {
                "plants": plants,
                "last_watered": row[1],
                "growth_points": row[2] or 0,
            }
        finally:
            conn.close()

    def save_garden(self, user_id, garden_data: dict) -> None:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO user_garden (user_id, plants, last_watered, growth_points)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET
                       plants = excluded.plants,
                       last_watered = excluded.last_watered,
                       growth_points = excluded.growth_points""",
                (
                    user_id,
                    json.dumps(garden_data.get("plants", {}), ensure_ascii=False),
                    garden_data.get("last_watered"),
                    garden_data.get("growth_points", 0),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    # ── user_pet ──

    def get_pet(self, user_id) -> dict:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT name, level, happiness, hunger, energy, last_fed FROM user_pet WHERE user_id = ?",
                (user_id,),
            )
            row = cur.fetchone()
            if not row:
                return {
                    "name": "Pixel",
                    "level": 1,
                    "happiness": 50.0,
                    "hunger": 50.0,
                    "energy": 100.0,
                    "last_fed": None,
                }
            return {
                "name": row[0],
                "level": row[1],
                "happiness": row[2],
                "hunger": row[3],
                "energy": row[4],
                "last_fed": row[5],
            }
        finally:
            conn.close()

    def save_pet(self, user_id, pet_data: dict) -> None:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO user_pet (user_id, name, level, happiness, hunger, energy, last_fed)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET
                       name = excluded.name,
                       level = excluded.level,
                       happiness = excluded.happiness,
                       hunger = excluded.hunger,
                       energy = excluded.energy,
                       last_fed = excluded.last_fed""",
                (
                    user_id,
                    pet_data.get("name", "Pixel"),
                    pet_data.get("level", 1),
                    pet_data.get("happiness", 50.0),
                    pet_data.get("hunger", 50.0),
                    pet_data.get("energy", 100.0),
                    pet_data.get("last_fed"),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    # ── user_achievements ──

    def get_achievements(self, user_id) -> list:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """SELECT id, achievement_id, title, description, unlocked_at
                   FROM user_achievements
                   WHERE user_id = ?
                   ORDER BY unlocked_at DESC""",
                (user_id,),
            )
            return [
                {
                    "id": r[0],
                    "achievement_id": r[1],
                    "title": r[2],
                    "description": r[3],
                    "unlocked_at": r[4],
                }
                for r in cur.fetchall()
            ]
        finally:
            conn.close()

    def save_achievement(self, user_id, achievement: dict) -> int:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO user_achievements
                   (user_id, achievement_id, title, description, unlocked_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    user_id,
                    achievement.get("achievement_id", ""),
                    achievement.get("title", ""),
                    achievement.get("description", ""),
                    achievement.get("unlocked_at") or datetime.now().isoformat(),
                ),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    # ── user_eco_data ──

    def get_eco(self, user_id) -> dict:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """SELECT eco_points, co2_saved_kg, trees_planted, level
                   FROM user_eco_data WHERE user_id = ?""",
                (user_id,),
            )
            row = cur.fetchone()
            if not row:
                return {
                    "eco_points": 0,
                    "co2_saved_kg": 0.0,
                    "trees_planted": 0,
                    "level": "Seedling",
                }
            return {
                "eco_points": row[0] or 0,
                "co2_saved_kg": row[1] or 0.0,
                "trees_planted": row[2] or 0,
                "level": row[3] or "Seedling",
            }
        finally:
            conn.close()

    def save_eco(self, user_id, eco_data: dict) -> None:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO user_eco_data
                   (user_id, eco_points, co2_saved_kg, trees_planted, level, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET
                       eco_points = excluded.eco_points,
                       co2_saved_kg = excluded.co2_saved_kg,
                       trees_planted = excluded.trees_planted,
                       level = excluded.level,
                       updated_at = excluded.updated_at""",
                (
                    user_id,
                    eco_data.get("eco_points", 0),
                    eco_data.get("co2_saved_kg", 0.0),
                    eco_data.get("trees_planted", 0),
                    eco_data.get("level", "Seedling"),
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()