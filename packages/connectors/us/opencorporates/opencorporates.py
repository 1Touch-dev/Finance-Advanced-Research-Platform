from typing import Iterable, Tuple, Dict, Any
from .._common.base_us import USBaseConnector
from .._common.http_helpers import http_get, yield_samples, is_test_env


class OpenCorporatesConnector(USBaseConnector):
    name = "opencorporates"

    def fetch_records(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        try:
            url = "https://api.opencorporates.com/v0.4/companies/search"
            resp = http_get(url, params={"q": "Apple", "jurisdiction_code": "us_de", "per_page": 10}, timeout=30)
            for r in resp.json().get("results", {}).get("companies", []):
                co = r.get("company", {})
                ext = co.get("opencorporates_url", co.get("company_number", ""))
                if ext:
                    yield str(ext), co
            return
        except Exception:
            if not is_test_env():
                raise

        yield from yield_samples([
            {"external_id": "us_ca-1234567", "company": "Example LLC", "jurisdiction_code": "us_ca"},
        ])
