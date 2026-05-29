from typing import Iterable, Tuple, Dict, Any
import time
from connectors.sdk import BaseConnector
from .._common.base_us import USBaseConnector

class OFACConnector(USBaseConnector):
    name = "ofac"
    def fetch_records(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        samples = [
            {"external_id": "OFAC-XYZ-1", "name": "John Doe", "program": "SDN"},
            {"external_id": "OFAC-XYZ-2", "name": "Acme Ltd.", "program": "SSI"},
        ]
        for it in samples:
            yield it["external_id"], it
            time.sleep(0.05)
