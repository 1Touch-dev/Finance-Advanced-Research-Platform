from typing import Iterable, Tuple, Dict, Any
from .._common.base_us import USBaseConnector
from .._common.http_helpers import http_get, yield_samples, env_or_creds, is_test_env


class FECConnector(USBaseConnector):
    name = "fec"

    def fetch_records(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        fec_key = env_or_creds(self.creds, "api_key", "FEC_API_KEY")
        if fec_key:
            try:
                url = "https://api.open.fec.gov/v1/candidates/"
                resp = http_get(url, params={"api_key": fec_key, "sort": "name", "per_page": 10})
                for r in resp.json().get("results", []):
                    yield str(r.get("candidate_id")), r
                return
            except Exception:
                if not is_test_env():
                    raise

        yield from yield_samples([
            {"external_id": "C12345678", "committee": "Citizens for Example", "filings": 42},
        ])
