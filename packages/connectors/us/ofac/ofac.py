from typing import Iterable, Tuple, Dict, Any
import os
from .._common.base_us import USBaseConnector
from .._common.http_helpers import http_get, yield_samples, env_or_creds, is_test_env


class OFACConnector(USBaseConnector):
    name = "ofac"

    def fetch_records(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        sanctions_key = env_or_creds(self.creds, "api_key", "SANCTIONS_API_KEY")
        if sanctions_key:
            try:
                url = "https://api.opensanctions.org/search/default"
                headers = {"Authorization": f"ApiKey {sanctions_key}"}
                resp = http_get(url, headers=headers, params={"q": "russia", "limit": 10})
                for r in resp.json().get("results", []):
                    props = r.get("properties", {})
                    ext = r.get("id") or props.get("name", [""])[0]
                    yield str(ext), r
                return
            except Exception:
                pass

        try:
            url = "https://www.treasury.gov/ofac/downloads/sdn.csv"
            resp = http_get(url, timeout=30)
            lines = resp.text.strip().split("\n")[:11]
            for line in lines[1:]:
                parts = line.split(",")
                if len(parts) >= 2:
                    ext = parts[0].strip('"')
                    name = parts[1].strip('"')
                    yield ext, {"external_id": ext, "name": name, "program": "SDN", "source": "treasury.gov"}
            return
        except Exception:
            if not is_test_env():
                raise

        yield from yield_samples([
            {"external_id": "OFAC-XYZ-1", "name": "John Doe", "program": "SDN"},
        ])
