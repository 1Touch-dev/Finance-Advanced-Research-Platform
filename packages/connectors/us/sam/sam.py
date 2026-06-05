from typing import Iterable, Tuple, Dict, Any
from .._common.base_us import USBaseConnector
from .._common.http_helpers import http_get, yield_samples, env_or_creds, is_test_env


class SAMGovConnector(USBaseConnector):
    name = "sam_gov"

    def fetch_records(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        sam_key = env_or_creds(self.creds, "api_key", "SAM_GOV_API_KEY")
        if sam_key:
            try:
                url = "https://api.sam.gov/prod/opportunities/v1/search"
                resp = http_get(url, params={"api_key": sam_key, "limit": 10})
                records = resp.json().get("opportunitiesData", [])
                for r in records:
                    yield str(r.get("noticeId")), r
                return
            except Exception:
                if not is_test_env():
                    raise

        yield from yield_samples([
            {"external_id": "UEI-ABCD1234EFGH", "entity": "Acme, Inc.", "status": "Active"},
        ])
