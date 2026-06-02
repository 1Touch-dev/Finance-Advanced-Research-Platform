from typing import Iterable, Tuple, Dict, Any
import time
from .._common.base_us import USBaseConnector

class GovInfoConnector(USBaseConnector):
    name = "govinfo"
    def fetch_records(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        samples = [{"external_id": "govinfo-PL-117-58", "title": "Infrastructure Investment and Jobs Act"}]
        for it in samples:
            yield it["external_id"], it
            time.sleep(0.05)
