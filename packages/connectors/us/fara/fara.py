from typing import Iterable, Tuple, Dict, Any
import time
from .._common.base_us import USBaseConnector

class FARAConnector(USBaseConnector):
    name = "fara"
    def fetch_records(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        samples = [
            {"external_id": "fara-2024-0001", "registrant": "Global Strategies LLC", "country": "US"}
        ]
        for it in samples:
            yield it["external_id"], it
            time.sleep(0.05)
