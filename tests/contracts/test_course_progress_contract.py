"""Contract tests for course progress endpoints (M5)."""
import pytest


@pytest.mark.contract
class TestCourseProgressContract:
    def test_progress_load(self, contract_runner):
        contract_runner.assert_contract(
            "GET", "/api/progress/load?userId=test_user_99&courseId=course_1"
        )

    def test_progress_summary(self, contract_runner):
        contract_runner.assert_contract("GET", "/api/progress/summary/test_user_99")

    def test_v2_course_list(self, contract_runner):
        contract_runner.assert_contract("GET", "/api/v2/course/list/test_user_99")

    def test_v2_course_list_all(self, contract_runner):
        contract_runner.assert_contract("GET", "/api/v2/course/list/all")
