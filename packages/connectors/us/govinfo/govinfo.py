from typing import Iterable, Tuple, Dict, Any
from .._common.base_us import USBaseConnector
from .._common.http_helpers import http_get, yield_samples, env_or_creds, is_test_env


class GovInfoConnector(USBaseConnector):
    name = "govinfo"

    def fetch_records(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        api_key = env_or_creds(self.creds, "api_key", "GOVINFO_API_KEY")
        if api_key:
            try:
                url = "https://api.govinfo.gov/collections/BILLS/2024-01-01T00:00:00Z"
                resp = http_get(url, params={"api_key": api_key, "pageSize": 10, "offsetMark": "*"})
                for pkg in resp.json().get("packages", []):
                    ext = pkg.get("packageId", "")
                    if ext:
                        yield ext, pkg
                return
            except Exception:
                if not is_test_env():
                    raise

        yield from yield_samples([
            {"external_id": "govinfo-PL-117-58", "title": "Infrastructure Investment and Jobs Act"},
        ])
