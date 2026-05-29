from typing import Iterable, Tuple, Dict, Any
import time
from ...us._common.base_us import USBaseConnector

class CourtListenerConnector(USBaseConnector):
    name = "courtlistener"
    def fetch_records(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        samples = [{"external_id": "docket-2:23-cv-00001", "case_name": "Example v. Example", "court": "D. Mass."}]
        for it in samples:
            yield it["external_id"], it
            time.sleep(0.05)
