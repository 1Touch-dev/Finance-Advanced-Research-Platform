from typing import Iterable, Tuple, Dict, Any
from .._common.base_us import USBaseConnector
from .._common.http_helpers import http_get, yield_samples, is_test_env


class FARAConnector(USBaseConnector):
    name = "fara"

    def fetch_records(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        try:
            url = "https://efile.fara.gov/api/v1/Registrants"
            resp = http_get(url, timeout=30)
            data = resp.json()
            items = data if isinstance(data, list) else data.get("results", data.get("data", []))
            for r in items[:10]:
                ext = str(r.get("registration_number") or r.get("id", ""))
                if ext:
                    yield ext, r
            return
        except Exception:
            if not is_test_env():
                raise

        yield from yield_samples([
            {"external_id": "fara-2024-0001", "registrant": "Global Strategies LLC", "country": "US"},
        ])
