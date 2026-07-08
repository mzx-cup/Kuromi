"""SQLAlchemy implementation for preferences. Stub during M0."""


class SqlAlchemyPreferencesRepository:
    async def get_preferences(self, user_id: str) -> dict:
        raise NotImplementedError("Filled in M2")

    async def set_preference(self, user_id: str, key: str, value: dict) -> None:
        raise NotImplementedError("Filled in M2")
