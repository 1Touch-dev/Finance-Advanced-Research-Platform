import time
import json
from typing import Any, Dict, Iterable, Optional, Tuple

class RateLimiter:
    def __init__(self, rate_per_sec: float = 5.0):
        self.rate = rate_per_sec
        self._min_interval = 1.0 / rate_per_sec if rate_per_sec > 0 else 0
        self._last = 0.0
    def wait(self):
        now = time.time()
        delta = now - self._last
        if delta < self._min_interval:
            time.sleep(self._min_interval - delta)
        self._last = time.time()

class Retry:
    def __init__(self, retries: int = 3, base_backoff: float = 0.5):
        self.retries = retries
        self.base = base_backoff
    def run(self, fn, *args, **kwargs):
        attempt = 0
        while True:
            try:
                return fn(*args, **kwargs)
            except Exception as e:  # noqa
                if attempt >= self.retries:
                    raise
                time.sleep(self.base * (2 ** attempt))
                attempt += 1

class Checkpointer:
    def __init__(self, state: Optional[Dict[str, Any]] = None):
        self.state = state or {}
    def get(self, key: str, default=None):
        return self.state.get(key, default)
    def set(self, key: str, value: Any):
        self.state[key] = value
    def dump(self) -> str:
        return json.dumps(self.state)

class BaseConnector:
    """Base class for connectors.
    Implement fetch_records to yield (external_id, payload_dict) tuples.
    """
    name: str = "base"
    def __init__(self, creds: Dict[str, Any], rate_limit: float = 5.0, retries: int = 3):
        self.creds = creds
        self.rate_limiter = RateLimiter(rate_limit)
        self.retry = Retry(retries)
        self.checkpointer = Checkpointer()
    def fetch_records(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        raise NotImplementedError
    def run(self) -> Dict[str, Any]:
        """Idempotent ingestion skeleton; returns metrics."""
        seen = 0
        errors = 0
        for external_id, payload in self.fetch_records():
            self.rate_limiter.wait()
            def _process():
                # override to persist; here we only simulate serialization
                return True
            try:
                self.retry.run(_process)
                seen += 1
            except Exception:
                errors += 1
        return {"seen": seen, "errors": errors}
