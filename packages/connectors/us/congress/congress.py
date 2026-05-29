from typing import Iterable, Tuple, Dict, Any
import time
from .._common.base_us import USBaseConnector

class CongressGovConnector(USBaseConnector):
    name = "congress_gov"
    def fetch_records(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        samples = [{"external_id": "hr123-118", "title": "A bill to do X", "sponsor": "Rep. Example"}]
        for it in samples:
            yield it["external_id"], it
            time.sleep(0.05)
