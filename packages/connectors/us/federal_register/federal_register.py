from typing import Iterable, Tuple, Dict, Any
import time
from .._common.base_us import USBaseConnector

class FederalRegisterConnector(USBaseConnector):
    name = "federal_register"
    def fetch_records(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        samples = [{"external_id": "fr-2024-00001", "title": "Proposed Rule", "agency": "DOE"}]
        for it in samples:
            yield it["external_id"], it
            time.sleep(0.05)
