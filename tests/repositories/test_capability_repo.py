"""Unit tests for CapabilityRepository (ORM + Legacy)."""
import pytest
from app.repositories.base import CapabilityRepository


@pytest.fixture
def sample_user_id() -> str:
    return "test_user_capability_001"


class TestCapabilityRepositoryProtocol:
    def test_protocol_lists_required_methods(self):
        """The CapabilityRepository Protocol must define all 6 dimensions + util methods."""
        from app.repositories.base import CapabilityRepository
        assert hasattr(CapabilityRepository, "__call__")  # Protocol is callable
        from app.repositories.legacy.capability import DbPyCapabilityRepository
        from app.repositories.orm.capability import SqlAlchemyCapabilityRepository
        repo_orm = SqlAlchemyCapabilityRepository(db_path="xingshi_v2.db")
        repo_legacy = DbPyCapabilityRepository(db_path="xingshi.db")
        assert isinstance(repo_orm, CapabilityRepository)
        assert isinstance(repo_legacy, CapabilityRepository)
