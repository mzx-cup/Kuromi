"""Legacy db.py wrapper for learning data. Stub during M0."""


class DbPyLearningRepository:
    async def get_overview(self, user_id: str) -> dict:
        raise NotImplementedError("Filled in M3")

    async def get_trend(self, user_id: str, days: int) -> list:
        raise NotImplementedError("Filled in M3")

    async def get_heatmap(self, user_id: str) -> dict:
        raise NotImplementedError("Filled in M3")

    async def record_session(self, user_id: str, session_data: dict) -> None:
        raise NotImplementedError("Filled in M4")
