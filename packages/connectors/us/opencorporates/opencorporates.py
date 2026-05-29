from typing import Iterable, Tuple, Dict, Any
import time
from .._common.base_us import USBaseConnector

class OpenCorporatesConnector(USBaseConnector):
    name = "opencorporates"
    def fetch_records(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        samples = [
            {"external_id": "us_ca-1234567", "company": "Example LLC", "jurisdiction_code": "us_ca"}
        ]
        for it in samples:
            yield it["external_id"], it
            time.sleep(0.05)
