import time
from typing import Dict, Any

class TTLCache:
    def __init__(self, ttl_s: int = 300):
        self.ttl = ttl_s
        self.store: Dict[str, Any] = {}
    def get(self, k: str):
        v = self.store.get(k)
        if not v: return None
        if time.time() > v[1]:
            del self.store[k]; return None
        return v[0]
    def set(self, k: str, val: Any):
        self.store[k] = (val, time.time()+self.ttl)

class RefreshCadence:
    def __init__(self, cadences: Dict[str,int] | None = None):
        self.cad = cadences or {}
        self.last: Dict[str,float] = {}
    def should_refresh(self, source: str) -> bool:
        now = time.time(); every = self.cad.get(source, 3600)
        if source not in self.last or now - self.last[source] > every:
            self.last[source] = now; return True
        return False
