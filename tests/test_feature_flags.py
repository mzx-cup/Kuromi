import os
import pytest
from app.core.feature_flags import (
    user_in_orm_read_path,
    get_read_percentage,
    is_dual_write_enabled,
)


class TestUserInOrmReadPath:
    def test_zero_percentage_always_legacy(self):
        for user_id in ["user_1", "user_2", "user_3"]:
            assert user_in_orm_read_path(user_id, 0) is False

    def test_hundred_percentage_always_orm(self):
        for user_id in ["user_1", "user_2", "user_3"]:
            assert user_in_orm_read_path(user_id, 100) is True

    def test_fifty_percentage_is_stable_for_same_user(self):
        user_id = "stable_user_42"
        result_1 = user_in_orm_read_path(user_id, 50)
        result_2 = user_in_orm_read_path(user_id, 50)
        result_3 = user_in_orm_read_path(user_id, 50)
        assert result_1 == result_2 == result_3

    def test_distribution_roughly_uniform(self):
        results = [user_in_orm_read_path(f"user_{i}", 50) for i in range(1000)]
        orm_count = sum(results)
        assert 400 <= orm_count <= 600


class TestGetReadPercentage:
    def test_default_zero(self, monkeypatch):
        monkeypatch.delenv("READ_BACKEND_PERCENTAGE", raising=False)
        assert get_read_percentage() == 0

    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("READ_BACKEND_PERCENTAGE", "25")
        assert get_read_percentage() == 25

    def test_invalid_value_defaults_zero(self, monkeypatch):
        monkeypatch.setenv("READ_BACKEND_PERCENTAGE", "abc")
        assert get_read_percentage() == 0


class TestIsDualWriteEnabled:
    def test_default_false(self, monkeypatch):
        monkeypatch.delenv("DUAL_WRITE_LEGACY", raising=False)
        assert is_dual_write_enabled() is False

    def test_true_string(self, monkeypatch):
        monkeypatch.setenv("DUAL_WRITE_LEGACY", "true")
        assert is_dual_write_enabled() is True