from typing import Iterable, Tuple, Dict, Any
import time
from .._common.base_us import USBaseConnector

class USASpendingConnector(USBaseConnector):
    name = "usaspending"
    def fetch_records(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        samples = [{"external_id": "award-12345", "amount": 1000000, "recipient": "Example University"}]
        for it in samples:
            yield it["external_id"], it
            time.sleep(0.05)
