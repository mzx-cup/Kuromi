"""Contract tests for gamification endpoints (M8)."""
import pytest


@pytest.mark.contract
class TestGamificationContract:
    def test_garden_load(self, contract_runner):
        contract_runner.assert_contract("GET", "/api/garden/load/test_user_99")

    def test_pet_load(self, contract_runner):
        contract_runner.assert_contract("GET", "/api/pet/load/test_user_99")

    def test_achievements_load(self, contract_runner):
        contract_runner.assert_contract("GET", "/api/achievements/load/test_user_99")

    def test_eco_load(self, contract_runner):
        contract_runner.assert_contract("GET", "/api/eco/load/test_user_99")