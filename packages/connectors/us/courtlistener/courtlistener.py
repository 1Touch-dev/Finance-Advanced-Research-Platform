from typing import Iterable, Tuple, Dict, Any
import time
from ...us._common.base_us import USBaseConnector

import os
import requests

class CourtListenerConnector(USBaseConnector):
    name = "courtlistener"
    def fetch_records(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        cl_token = self.creds.get("api_token") or os.getenv("COURTLISTENER_API_TOKEN")
        if cl_token:
            try:
                url = "https://www.courtlistener.com/api/rest/v4/dockets/?limit=5"
                headers = {"Authorization": f"Token {cl_token}"}
                resp = requests.get(url, headers=headers, timeout=15)
                resp.raise_for_status()
                records = resp.json().get("results", [])
                for r in records:
                    yield str(r.get("id")), r
                return
            except Exception:
                pass

        # Fallback graceful mock samples
        samples = [{"external_id": "docket-2:23-cv-00001", "case_name": "Example v. Example", "court": "D. Mass."}]
        for it in samples:
            yield it["external_id"], it
            time.sleep(0.05)
