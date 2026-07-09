"""Contract tests for preferences/settings/theme endpoints."""
import pytest


@pytest.mark.contract
class TestPreferencesContract:
    def test_get_user_preferences(self, contract_runner):
        contract_runner.assert_contract(
            "GET", "/api/user/preferences/test_user_99"
        )

    def test_get_settings(self, contract_runner):
        contract_runner.assert_contract(
            "GET", "/api/settings/load/test_user_99"
        )

    def test_get_theme_sync(self, contract_runner):
        contract_runner.assert_contract(
            "GET", "/api/user/theme/sync?user_id=test_user_99"
        )

    def test_get_user_state(self, contract_runner):
        contract_runner.assert_contract(
            "GET", "/api/user/state/test_user_99"
        )
