from typing import Iterable, Tuple, Dict, Any
import time
from .._common.base_us import USBaseConnector

import os
import requests

class SAMGovConnector(USBaseConnector):
    name = "sam_gov"
    def fetch_records(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        sam_key = self.creds.get("api_key") or os.getenv("SAM_GOV_API_KEY")
        if sam_key:
            try:
                # SAM.gov Opportunities API endpoint
                url = f"https://api.sam.gov/prod/opportunities/v1/search?api_key={sam_key}&limit=5"
                resp = requests.get(url, timeout=15)
                resp.raise_for_status()
                records = resp.json().get("opportunitiesData", [])
                for r in records:
                    yield str(r.get("noticeId")), r
                return
            except Exception:
                pass

        # Fallback graceful mock samples
        samples = [{"external_id": "UEI-ABCD1234EFGH", "entity": "Acme, Inc.", "status": "Active"}]
        for it in samples:
            yield it["external_id"], it
            time.sleep(0.05)
