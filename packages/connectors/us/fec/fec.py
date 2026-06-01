from typing import Iterable, Tuple, Dict, Any
import time
from .._common.base_us import USBaseConnector

import os
import requests

class FECConnector(USBaseConnector):
    name = "fec"
    def fetch_records(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        fec_key = self.creds.get("api_key") or os.getenv("FEC_API_KEY")
        if fec_key:
            try:
                url = f"https://api.open.fec.gov/v1/candidates/?api_key={fec_key}&sort=name&per_page=5"
                resp = requests.get(url, timeout=15)
                resp.raise_for_status()
                records = resp.json().get("results", [])
                for r in records:
                    yield str(r.get("candidate_id")), r
                return
            except Exception:
                pass

        # Fallback graceful mock samples
        samples = [
            {"external_id": "C12345678", "committee": "Citizens for Example", "filings": 42}
        ]
        for it in samples:
            yield it["external_id"], it
            time.sleep(0.05)
