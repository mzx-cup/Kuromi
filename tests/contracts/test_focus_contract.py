"""Contract tests for focus endpoints (M7)."""
import pytest


@pytest.mark.contract
class TestFocusContract:
    def test_cockpit_analysis(self, contract_runner):
        contract_runner.assert_contract("GET", "/api/cockpit/analysis/test_user_99")

    def test_focus_load(self, contract_runner):
        contract_runner.assert_contract("GET", "/api/focus/load/test_user_99")