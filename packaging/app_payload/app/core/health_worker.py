"""Background worker probing Qdrant / Redis / LangChain wrapper."""
import threading
import time
from typing import Callable, Optional, Dict
from app.services.health.health_probe import HealthProbe


def probe_qdrant() -> bool:
    try:
        from app.services.kb.qdrant_client import QdrantClientSingleton
        status = QdrantClientSingleton.health()["status"]
        return status in ("ok", "degraded")
    except Exception:
        return False


def probe_redis() -> bool:
    try:
        import redis
        from app.core.config import kb_settings
        r = redis.Redis(host=kb_settings.redis_host, port=kb_settings.redis_port, socket_timeout=0.5)
        return bool(r.ping())
    except Exception:
        return False


class HealthWorker:
    def __init__(self, interval_seconds: float = 10.0, callback: Optional[Callable[[Dict[str, str]], None]] = None):
        self.interval = interval_seconds
        self.probes = {"qdrant": HealthProbe("qdrant"), "redis": HealthProbe("redis")}
        self.callback = callback

    def run_once(self) -> None:
        results = {name: probe() for name, probe in [("qdrant", probe_qdrant), ("redis", probe_redis)]}
        for name, ok in results.items():
            self.probes[name].record(ok)
        if self.callback is not None:
            self.callback(self.snapshot())

    def snapshot(self) -> Dict[str, str]:
        return {name: probe.current_level.name for name, probe in self.probes.items()}

    def start_background(self) -> threading.Thread:
        def loop():
            while True:
                self.run_once()
                time.sleep(self.interval)
        t = threading.Thread(target=loop, daemon=True, name="kb-health-worker")
        t.start()
        return t