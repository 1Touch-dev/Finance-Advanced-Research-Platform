from typing import Iterable, Tuple, Dict, Any
from .._common.base_us import USBaseConnector
from .._common.http_helpers import http_get, yield_samples, env_or_creds, is_test_env


class CongressGovConnector(USBaseConnector):
    name = "congress_gov"

    def fetch_records(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        congress_key = env_or_creds(self.creds, "api_key", "CONGRESS_API_KEY")
        if congress_key:
            try:
                url = "https://api.congress.gov/v3/bill"
                resp = http_get(url, params={"api_key": congress_key, "limit": 10})
                records = resp.json().get("bills", [])
                for r in records:
                    stable_id = f"bill-{r.get('type', 'hr').lower()}{r.get('number')}-{r.get('congress')}"
                    yield stable_id, r
                return
            except Exception:
                if not is_test_env():
                    raise

        yield from yield_samples([
            {"external_id": "hr123-118", "title": "A bill to do X", "sponsor": "Rep. Example"},
        ])
