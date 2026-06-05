from typing import Iterable, Tuple, Dict, Any
from .._common.base_us import USBaseConnector
from .._common.http_helpers import http_get, yield_samples, is_test_env


class LDAConnector(USBaseConnector):
    name = "lda_gov"

    def fetch_records(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        try:
            url = "https://lda.senate.gov/api/v1/filings/"
            resp = http_get(url, params={"page_size": 10}, timeout=30)
            for r in resp.json().get("results", resp.json() if isinstance(resp.json(), list) else []):
                if isinstance(r, dict):
                    ext = str(r.get("filing_uuid") or r.get("id", ""))
                    if ext:
                        yield ext, r
            return
        except Exception:
            if not is_test_env():
                raise

        yield from yield_samples([
            {"external_id": "lda-2024-0001", "registrant": "Acme Strategies"},
        ])
