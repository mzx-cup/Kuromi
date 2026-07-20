"""Contract tests for classroom endpoints (M10)."""
import pytest


@pytest.mark.contract
class TestClassroomContract:
    def test_v2_classroom_list(self, contract_runner):
        contract_runner.assert_contract(
            "GET", "/api/v2/classroom/list/test_user_99",
        )

    def test_v2_classroom_get(self, contract_runner):
        contract_runner.assert_contract(
            "GET", "/api/v2/classroom/course_1?user_id=test_user_99",
        )
