from typing import Iterable, Tuple, Dict, Any
import time
from ...us._common.base_us import USBaseConnector

class SAMGovConnector(USBaseConnector):
    name = "sam_gov"
    def fetch_records(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        samples = [{"external_id": "UEI-ABCD1234EFGH", "entity": "Acme, Inc.", "status": "Active"}]
        for it in samples:
            yield it["external_id"], it
            time.sleep(0.05)
