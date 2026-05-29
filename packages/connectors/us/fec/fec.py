from typing import Iterable, Tuple, Dict, Any
import time
from .._common.base_us import USBaseConnector

class FECConnector(USBaseConnector):
    name = "fec"
    def fetch_records(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        samples = [
            {"external_id": "C12345678", "committee": "Citizens for Example", "filings": 42}
        ]
        for it in samples:
            yield it["external_id"], it
            time.sleep(0.05)
