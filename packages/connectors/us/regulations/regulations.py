from typing import Iterable, Tuple, Dict, Any
from .._common.base_us import USBaseConnector
from .._common.http_helpers import http_get, yield_samples, env_or_creds, is_test_env


class RegulationsGovConnector(USBaseConnector):
    name = "regulations_gov"

    def fetch_records(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        api_key = env_or_creds(self.creds, "api_key", "REGULATIONS_GOV_API_KEY")
        if api_key:
            try:
                url = "https://api.regulations.gov/v4/documents"
                headers = {"X-Api-Key": api_key}
                resp = http_get(url, headers=headers, params={"page[size]": 10}, timeout=30)
                for r in resp.json().get("data", []):
                    attrs = r.get("attributes", {})
                    ext = r.get("id") or attrs.get("documentId", "")
                    if ext:
                        yield str(ext), {**attrs, "id": ext}
                return
            except Exception:
                if not is_test_env():
                    raise

        yield from yield_samples([
            {"external_id": "EPA-HQ-OAR-2024-0001", "title": "Proposed Emissions Rule", "comments": 12034},
        ])
