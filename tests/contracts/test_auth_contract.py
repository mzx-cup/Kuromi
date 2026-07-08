"""Contract tests for authentication endpoints.

Verifies that legacy db.py and new ORM backend produce equivalent responses
for the auth flow.
"""
import pytest


@pytest.mark.contract
class TestRegisterContract:
    def test_register_returns_user_object(self, contract_runner):
        contract_runner.assert_contract(
            "POST", "/api/register",
            json={
                "username": "contract_user_1",
                "password": "secure_pw_abc",
                "preferred_language": "zh-CN",
            },
        )


@pytest.mark.contract
class TestLoginContract:
    def test_login_with_valid_credentials(self, contract_runner, dual_db_environment):
        # First register via legacy path (db.py)
        from tests.fixtures.seed_data import populate_legacy
        populate_legacy(dual_db_environment.legacy_path, [{
            "id": 100, "username": "contract_login_user",
            "password": "test_pw_hash", "preferred_language": "zh-CN",
        }])

        contract_runner.assert_contract(
            "POST", "/api/login",
            json={"username": "contract_login_user", "password": "test_pw_hash"},
        )

    def test_login_with_invalid_credentials_returns_error(self, contract_runner):
        contract_runner.assert_contract(
            "POST", "/api/login",
            json={"username": "nonexistent", "password": "wrong"},
        )


@pytest.mark.contract
class TestGuestLoginContract:
    def test_guest_login_creates_temporary_session(self, contract_runner):
        contract_runner.assert_contract(
            "POST", "/api/login/guest", json={},
        )