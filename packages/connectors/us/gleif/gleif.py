from typing import Iterable, Tuple, Dict, Any
import time
from .._common.base_us import USBaseConnector

class GLEIFConnector(USBaseConnector):
    name = "gleif"
    def fetch_records(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        samples = [
            {"external_id": "5493001KJTIIGC8Y1R12", "lei": "5493001KJTIIGC8Y1R12", "entity": "Alphabet Inc."},
        ]
        for it in samples:
            yield it["external_id"], it
            time.sleep(0.05)
