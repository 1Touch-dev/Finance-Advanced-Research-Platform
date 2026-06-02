from typing import Iterable, Tuple, Dict, Any
import time
from .._common.base_us import USBaseConnector

class RegInfoOIRAConnector(USBaseConnector):
    name = "reginfo_oira"
    def fetch_records(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        samples = [{"external_id": "OIRA-RIN-1234-AA00", "stage": "Proposed Rule Stage", "agency": "EPA"}]
        for it in samples:
            yield it["external_id"], it
            time.sleep(0.05)
