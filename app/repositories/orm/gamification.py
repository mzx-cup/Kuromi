"""SQLAlchemy implementation for gamification (M8).

This repository backs the gamification read path with SQLAlchemy. It
mirrors the methods on
:class:`app.repositories.legacy.gamification.DbPyGamificationRepository`
so callers can swap implementations behind the
:class:`app.repositories.base.GamificationRepository` Protocol.

Only storage operations are exposed here; the gamification formula
itself continues to live in higher-level services.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.gamification import (
    UserGarden,
    UserPet,
    UserAchievement,
    UserEcoData,
)


class SqlAlchemyGamificationRepository:
    def __init__(self, session: Session = None):
        self.session = session

    # ── user_garden ──

    def get_garden(self, user_id: str) -> dict:
        g = self.session.query(UserGarden).filter_by(user_id=user_id).first()
        if not g:
            return {"plants": {}, "last_watered": None, "growth_points": 0}
        return {
            "plants": g.plants_json or {},
            "last_watered": g.last_watered.isoformat() if g.last_watered else None,
            "growth_points": g.growth_points or 0,
        }

    def save_garden(self, user_id: str, garden_data: dict) -> None:
        existing = self.session.query(UserGarden).filter_by(user_id=user_id).first()
        if existing:
            existing.plants_json = garden_data.get("plants", {})
            existing.last_watered = garden_data.get("last_watered")
            existing.growth_points = garden_data.get("growth_points", 0)
        else:
            self.session.add(
                UserGarden(
                    user_id=user_id,
                    plants_json=garden_data.get("plants", {}),
                    last_watered=garden_data.get("last_watered"),
                    growth_points=garden_data.get("growth_points", 0),
                )
            )
        self.session.flush()

    # ── user_pet ──

    def get_pet(self, user_id: str) -> dict:
        p = self.session.query(UserPet).filter_by(user_id=user_id).first()
        if not p:
            return {
                "name": "Pixel",
                "level": 1,
                "happiness": 50.0,
                "hunger": 50.0,
                "energy": 100.0,
                "last_fed": None,
            }
        return {
            "name": p.name,
            "level": p.level,
            "happiness": p.happiness,
            "hunger": p.hunger,
            "energy": p.energy,
            "last_fed": p.last_fed.isoformat() if p.last_fed else None,
        }

    def save_pet(self, user_id: str, pet_data: dict) -> None:
        existing = self.session.query(UserPet).filter_by(user_id=user_id).first()
        if existing:
            existing.name = pet_data.get("name", "Pixel")
            existing.level = pet_data.get("level", 1)
            existing.happiness = pet_data.get("happiness", 50.0)
            existing.hunger = pet_data.get("hunger", 50.0)
            existing.energy = pet_data.get("energy", 100.0)
            existing.last_fed = pet_data.get("last_fed")
        else:
            self.session.add(
                UserPet(
                    user_id=user_id,
                    name=pet_data.get("name", "Pixel"),
                    level=pet_data.get("level", 1),
                    happiness=pet_data.get("happiness", 50.0),
                    hunger=pet_data.get("hunger", 50.0),
                    energy=pet_data.get("energy", 100.0),
                    last_fed=pet_data.get("last_fed"),
                )
            )
        self.session.flush()

    # ── user_achievements ──

    def get_achievements(self, user_id: str) -> list:
        rows = (
            self.session.query(UserAchievement)
            .filter_by(user_id=user_id)
            .order_by(UserAchievement.unlocked_at.desc())
            .all()
        )
        return [
            {
                "id": r.id,
                "achievement_id": r.achievement_id,
                "title": r.title or "",
                "description": r.description or "",
                "unlocked_at": r.unlocked_at.isoformat() if r.unlocked_at else None,
            }
            for r in rows
        ]

    def save_achievement(self, user_id: str, achievement: dict) -> int:
        a = UserAchievement(
            user_id=user_id,
            achievement_id=achievement.get("achievement_id", ""),
            title=achievement.get("title", ""),
            description=achievement.get("description", ""),
            unlocked_at=datetime.utcnow(),
        )
        self.session.add(a)
        self.session.flush()
        return a.id

    # ── user_eco_data ──

    def get_eco(self, user_id: str) -> dict:
        e = self.session.query(UserEcoData).filter_by(user_id=user_id).first()
        if not e:
            return {
                "eco_points": 0,
                "co2_saved_kg": 0.0,
                "trees_planted": 0,
                "level": "Seedling",
            }
        return {
            "eco_points": e.eco_points or 0,
            "co2_saved_kg": e.co2_saved_kg or 0.0,
            "trees_planted": e.trees_planted or 0,
            "level": e.level or "Seedling",
        }

    def save_eco(self, user_id: str, eco_data: dict) -> None:
        existing = self.session.query(UserEcoData).filter_by(user_id=user_id).first()
        if existing:
            existing.eco_points = eco_data.get("eco_points", 0)
            existing.co2_saved_kg = eco_data.get("co2_saved_kg", 0.0)
            existing.trees_planted = eco_data.get("trees_planted", 0)
            existing.level = eco_data.get("level", "Seedling")
            existing.updated_at = datetime.utcnow()
        else:
            self.session.add(
                UserEcoData(
                    user_id=user_id,
                    eco_points=eco_data.get("eco_points", 0),
                    co2_saved_kg=eco_data.get("co2_saved_kg", 0.0),
                    trees_planted=eco_data.get("trees_planted", 0),
                    level=eco_data.get("level", "Seedling"),
                    updated_at=datetime.utcnow(),
                )
            )
        self.session.flush()