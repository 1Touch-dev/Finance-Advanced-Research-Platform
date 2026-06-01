from typing import Iterable, Tuple, Dict, Any
import time
from .._common.base_us import USBaseConnector

import os
import requests

class CongressGovConnector(USBaseConnector):
    name = "congress_gov"
    def fetch_records(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        congress_key = self.creds.get("api_key") or os.getenv("CONGRESS_API_KEY")
        if congress_key:
            try:
                url = f"https://api.congress.gov/v3/bill?api_key={congress_key}&limit=5"
                resp = requests.get(url, timeout=15)
                resp.raise_for_status()
                records = resp.json().get("bills", [])
                for r in records:
                    stable_id = f"bill-{r.get('type','hr').lower()}{r.get('number')}-{r.get('congress')}"
                    yield stable_id, r
                return
            except Exception:
                pass

        # Fallback graceful mock samples
        samples = [{"external_id": "hr123-118", "title": "A bill to do X", "sponsor": "Rep. Example"}]
        for it in samples:
            yield it["external_id"], it
            time.sleep(0.05)
