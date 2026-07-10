"""Local benchmark script for database merge cutover decisions.

Usage:
  python tests/perf/benchmark_local.py --endpoint /api/stats/overview/perf_user
"""
import argparse
import json
import os
import statistics
import subprocess
import time
from datetime import datetime
from pathlib import Path


def benchmark(endpoint: str, backend: str, iterations: int, warmup: int) -> dict:
    if backend == "legacy":
        os.environ["READ_BACKEND_PERCENTAGE"] = "0"
    else:
        os.environ["READ_BACKEND_PERCENTAGE"] = "100"

    from fastapi.testclient import TestClient
    from main import app
    client = TestClient(app)

    # Warm-up
    for _ in range(warmup):
        client.get(endpoint)

    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        client.get(endpoint)
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)

    times.sort()
    return {
        "endpoint": endpoint,
        "backend": backend,
        "iterations": iterations,
        "warmup": warmup,
        "p50_ms": round(times[len(times) // 2], 2),
        "p95_ms": round(times[int(len(times) * 0.95)], 2),
        "p99_ms": round(times[int(len(times) * 0.99)], 2),
        "max_ms": round(times[-1], 2),
        "min_ms": round(times[0], 2),
        "mean_ms": round(statistics.mean(times), 2),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="/api/stats/overview/perf_user")
    parser.add_argument("--iterations", type=int, default=1000)
    parser.add_argument("--warmup", type=int, default=50)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    legacy_result = benchmark(args.endpoint, "legacy", args.iterations, args.warmup)
    orm_result = benchmark(args.endpoint, "orm", args.iterations, args.warmup)

    # Get current branch
    try:
        branch = subprocess.check_output(["git", "branch", "--show-current"], text=True).strip()
    except Exception:
        branch = "unknown"

    report = {
        "date": datetime.now().isoformat(),
        "branch": branch,
        "results": {"legacy": legacy_result, "orm": orm_result},
        "decision_criteria": {
            "p95_threshold_ms": 50,
            "p95_pass": orm_result["p95_ms"] <= 50,
        },
    }

    print(json.dumps(report, indent=2))

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()