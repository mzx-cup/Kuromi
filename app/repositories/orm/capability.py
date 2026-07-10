"""SQLAlchemy implementation for capability profile (filled in Task 11.2)."""
from app.repositories.base import CapabilityRepository


class SqlAlchemyCapabilityRepository:
    """Stub. Real implementation in Task 11.2."""

    def __init__(self, db_path: str = "xingshi_v2.db"):
        self.db_path = db_path

    async def get_knowledge_base(self, user_id: str) -> dict:
        raise NotImplementedError("Filled in Task 11.2")

    async def get_code_skill(self, user_id: str) -> dict:
        raise NotImplementedError("Filled in Task 11.2")

    async def get_cognitive_style(self, user_id: str) -> dict:
        raise NotImplementedError("Filled in Task 11.2")

    async def get_focus_level(self, user_id: str) -> dict:
        raise NotImplementedError("Filled in Task 11.2")

    async def get_learning_goals(self, user_id: str) -> list:
        raise NotImplementedError("Filled in Task 11.2")

    async def get_weakness(self, user_id: str) -> list:
        raise NotImplementedError("Filled in Task 11.2")

    async def aggregate_profile(self, user_id: str) -> dict:
        raise NotImplementedError("Filled in Task 11.2")
