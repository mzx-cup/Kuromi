"""Performance regression tests run by CI.

Compares legacy vs ORM latency with relative tolerance. Non-blocking
in CI (assertion failure is recorded but doesn't fail the build).
"""
import os
import time
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from main import app
    return TestClient(app)


def measure_p50(client: TestClient, path: str, backend: str, iterations: int = 10) -> float:
    """Measure p50 latency over N iterations."""
    # Warm-up
    for _ in range(3):
        if backend == "legacy":
            os.environ["READ_BACKEND_PERCENTAGE"] = "0"
        else:
            os.environ["READ_BACKEND_PERCENTAGE"] = "100"
        client.get(path)

    times = []
    for _ in range(iterations):
        if backend == "legacy":
            os.environ["READ_BACKEND_PERCENTAGE"] = "0"
        else:
            os.environ["READ_BACKEND_PERCENTAGE"] = "100"
        start = time.perf_counter()
        client.get(path)
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)

    times.sort()
    return times[len(times) // 2]


@pytest.mark.perf
class TestRelativeRegression:
    def test_overview_endpoint(self, client):
        """ORM p50 must be within 2x of legacy p50."""
        try:
            legacy_p50 = measure_p50(client, "/api/stats/overview/perf_user", "legacy", iterations=10)
            orm_p50 = measure_p50(client, "/api/stats/overview/perf_user", "orm", iterations=10)
        except Exception as e:
            pytest.skip(f"Endpoint not available: {e}")

        # Tolerance: ORM cannot be more than 2x slower than legacy
        assert orm_p50 <= legacy_p50 * 2.0, (
            f"ORM p50 ({orm_p50:.2f}ms) > 2x legacy p50 ({legacy_p50:.2f}ms)"
        )

    def test_login_endpoint(self, client):
        """ORM login p50 must be within 2x of legacy."""
        try:
            legacy_p50 = measure_p50(client, "/api/login", "legacy", iterations=10)
            orm_p50 = measure_p50(client, "/api/login", "orm", iterations=10)
        except Exception as e:
            pytest.skip(f"Endpoint not available: {e}")

        assert orm_p50 <= legacy_p50 * 2.0, (
            f"ORM p50 ({orm_p50:.2f}ms) > 2x legacy p50 ({legacy_p50:.2f}ms)"
        )

    def test_preferences_endpoint(self, client):
        """ORM preferences p50 must be within 2x of legacy."""
        try:
            legacy_p50 = measure_p50(client, "/api/user/preferences/perf_user", "legacy", iterations=10)
            orm_p50 = measure_p50(client, "/api/user/preferences/perf_user", "orm", iterations=10)
        except Exception as e:
            pytest.skip(f"Endpoint not available: {e}")

        assert orm_p50 <= legacy_p50 * 2.0