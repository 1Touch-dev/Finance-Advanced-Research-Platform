from typing import Iterable, Tuple, Dict, Any
import time
from ...us._common.base_us import USBaseConnector

class RegulationsGovConnector(USBaseConnector):
    name = "regulations_gov"
    def fetch_records(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        samples = [{"external_id": "EPA-HQ-OAR-2024-0001", "title": "Proposed Emissions Rule", "comments": 12034}]
        for it in samples:
            yield it["external_id"], it
            time.sleep(0.05)
