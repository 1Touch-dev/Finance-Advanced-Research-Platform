from typing import Iterable, Tuple, Dict, Any
from .._common.base_us import USBaseConnector
from .._common.http_helpers import http_get, yield_samples, env_or_creds, is_test_env


class CourtListenerConnector(USBaseConnector):
    name = "courtlistener"

    def fetch_records(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        cl_token = env_or_creds(self.creds, "api_token", "COURTLISTENER_API_TOKEN")
        if cl_token:
            try:
                url = "https://www.courtlistener.com/api/rest/v4/dockets/"
                headers = {"Authorization": f"Token {cl_token}"}
                resp = http_get(url, headers=headers, params={"limit": 10})
                for r in resp.json().get("results", []):
                    yield str(r.get("id")), r
                return
            except Exception:
                if not is_test_env():
                    raise

        yield from yield_samples([
            {"external_id": "docket-2:23-cv-00001", "case_name": "Example v. Example", "court": "D. Mass."},
        ])
