from typing import Iterable, Tuple, Dict, Any
import time
from ...us._common.base_us import USBaseConnector

class ECFRConnector(USBaseConnector):
    name = "ecfr"
    def fetch_records(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        samples = [{"external_id": "eCFR-Title40-Part60", "title": "Standards of Performance for New Stationary Sources"}]
        for it in samples:
            yield it["external_id"], it
            time.sleep(0.05)
