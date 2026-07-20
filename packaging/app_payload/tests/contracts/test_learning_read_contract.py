"""Contract tests for learning stats read endpoints (M3)."""
import pytest


@pytest.mark.contract
class TestLearningReadContract:
    def test_overview(self, contract_runner):
        contract_runner.assert_contract("GET", "/api/stats/overview/test_user_99")

    def test_trend(self, contract_runner):
        contract_runner.assert_contract("GET", "/api/stats/trend/test_user_99?days=7")

    def test_heatmap(self, contract_runner):
        contract_runner.assert_contract("GET", "/api/stats/heatmap/test_user_99?weeks=4")

    def test_mastery(self, contract_runner):
        contract_runner.assert_contract("GET", "/api/stats/mastery/test_user_99")

    def test_daily_route_status(self, contract_runner):
        contract_runner.assert_contract("GET", "/api/daily-route/status?userId=1")

    def test_study_sessions(self, contract_runner):
        contract_runner.assert_contract("GET", "/api/study/sessions/test_user_99")

    def test_study_total(self, contract_runner):
        contract_runner.assert_contract("GET", "/api/study/total/test_user_99")

    def test_goals(self, contract_runner):
        contract_runner.assert_contract("GET", "/api/goals/test_user_99")

    def test_stats_load(self, contract_runner):
        contract_runner.assert_contract("GET", "/api/stats/load/test_user_99")

    def test_user_state(self, contract_runner):
        contract_runner.assert_contract("GET", "/api/user/state/test_user_99")

    def test_notifications_load(self, contract_runner):
        contract_runner.assert_contract("GET", "/api/notifications/load/test_user_99")

    def test_calendar_events_load(self, contract_runner):
        contract_runner.assert_contract("GET", "/api/calendar-events/load/test_user_99")
