from typing import Iterable, Tuple, Dict, Any
import time
from .._common.base_us import USBaseConnector

class IRS990Connector(USBaseConnector):
    name = "irs_990"
    def fetch_records(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        samples = [{"external_id": "ein-12-3456789-2023", "org": "Example Foundation", "form": "990"}]
        for it in samples:
            yield it["external_id"], it
            time.sleep(0.05)
