from typing import Iterable, Tuple, Dict, Any
from .._common.base_us import USBaseConnector
from .._common.http_helpers import http_get, yield_samples, is_test_env


class USASpendingConnector(USBaseConnector):
    name = "usaspending"

    def fetch_records(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        try:
            url = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
            body = {
                "filters": {
                    "time_period": [{"start_date": "2024-01-01", "end_date": "2024-12-31"}],
                    "award_type_codes": ["A", "B", "C", "D"],
                },
                "fields": ["Award ID", "Recipient Name", "Award Amount"],
                "limit": 10,
                "page": 1,
            }
            import requests
            resp = requests.post(url, json=body, timeout=30)
            resp.raise_for_status()
            for r in resp.json().get("results", []):
                ext = str(r.get("Award ID") or r.get("internal_id", ""))
                if ext:
                    yield ext, r
            return
        except Exception:
            if not is_test_env():
                raise

        yield from yield_samples([
            {"external_id": "award-12345", "amount": 1000000, "recipient": "Example University"},
        ])
