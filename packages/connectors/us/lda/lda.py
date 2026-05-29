from typing import Iterable, Tuple, Dict, Any
import time
from .._common.base_us import USBaseConnector

class LDAConnector(USBaseConnector):
    name = "lda_gov"
    def fetch_records(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        samples = [{"external_id": "lda-2024-0001", "registrant": "Acme Strategies"}]
        for it in samples:
            yield it["external_id"], it
            time.sleep(0.05)
