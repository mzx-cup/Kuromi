"""Contract tests for chat endpoints (M9)."""
import pytest


@pytest.mark.contract
class TestChatContract:
    def test_chat_history(self, contract_runner):
        contract_runner.assert_contract("GET", "/api/chat/history?user_id=test_user_99")