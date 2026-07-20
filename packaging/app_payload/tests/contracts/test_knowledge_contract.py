"""Contract tests for knowledge endpoints (M6)."""
import pytest


@pytest.mark.contract
class TestKnowledgeContract:
    def test_get_nodes(self, contract_runner):
        contract_runner.assert_contract(
            "GET", "/api/knowledge/nodes/test_user_99?active=false"
        )

    def test_get_pending(self, contract_runner):
        contract_runner.assert_contract(
            "GET", "/api/knowledge/pending/test_user_99"
        )

    def test_get_records(self, contract_runner):
        contract_runner.assert_contract(
            "GET", "/api/knowledge/records/test_user_99"
        )