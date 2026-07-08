import pytest
from pathlib import Path


class TestDualDbFixture:
    def test_dual_db_environment_provides_both_paths(self, dual_db_environment):
        assert Path(dual_db_environment.legacy_path).exists()
        assert Path(dual_db_environment.orm_path).exists()

    def test_contract_runner_provides_assert_contract(self, dual_db_environment, contract_runner):
        assert hasattr(contract_runner, "assert_contract")

    def test_seed_users_creates_consistent_users(self, dual_db_environment):
        from tests.fixtures.seed_data import count_users_legacy, count_users_orm
        legacy_count = count_users_legacy(dual_db_environment.legacy_path)
        orm_count = count_users_orm(dual_db_environment.orm_path)
        assert legacy_count == orm_count > 0
