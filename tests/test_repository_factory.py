import os
import pytest
from app.core.repository_factory import (
    get_repository_for_user,
    is_orm_read_path_active,
)
from app.repositories.base import LearningRepository


class TestGetRepositoryForUser:
    def test_returns_object_implementing_protocol(self):
        repo = get_repository_for_user("any_user", repository_type="learning")
        assert isinstance(repo, LearningRepository)

    def test_zero_percentage_returns_legacy(self, monkeypatch):
        monkeypatch.setenv("READ_BACKEND_PERCENTAGE", "0")
        repo = get_repository_for_user("user_a", repository_type="learning")
        from app.repositories.legacy.learning import DbPyLearningRepository
        assert isinstance(repo, DbPyLearningRepository)

    def test_hundred_percentage_returns_orm(self, monkeypatch):
        monkeypatch.setenv("READ_BACKEND_PERCENTAGE", "100")
        repo = get_repository_for_user("user_a", repository_type="learning")
        from app.repositories.orm.learning import SqlAlchemyLearningRepository
        assert isinstance(repo, SqlAlchemyLearningRepository)


class TestIsOrmReadPathActive:
    def test_zero_percentage_inactive(self, monkeypatch):
        monkeypatch.setenv("READ_BACKEND_PERCENTAGE", "0")
        assert is_orm_read_path_active("user_a") is False

    def test_hundred_percentage_active(self, monkeypatch):
        monkeypatch.setenv("READ_BACKEND_PERCENTAGE", "100")
        assert is_orm_read_path_active("user_a") is True


class TestCapabilityRepositoryFactory:
    def test_get_repository_for_user_capability_returns_capability(self, monkeypatch):
        monkeypatch.setenv("READ_BACKEND_PERCENTAGE", "0")
        from app.core.repository_factory import get_repository_for_user
        from app.repositories.base import CapabilityRepository
        repo = get_repository_for_user("u1", repository_type="capability")
        assert isinstance(repo, CapabilityRepository)

    def test_hundred_percentage_returns_orm_capability(self, monkeypatch):
        monkeypatch.setenv("READ_BACKEND_PERCENTAGE", "100")
        from app.core.repository_factory import get_repository_for_user
        repo = get_repository_for_user("u1", repository_type="capability")
        from app.repositories.orm.capability import SqlAlchemyCapabilityRepository
        assert isinstance(repo, SqlAlchemyCapabilityRepository)
