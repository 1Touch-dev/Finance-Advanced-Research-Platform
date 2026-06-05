from typing import Iterable, Tuple, Dict, Any
from .._common.base_us import USBaseConnector
from .._common.http_helpers import http_get, yield_samples, is_test_env


class RegInfoOIRAConnector(USBaseConnector):
    name = "reginfo_oira"

    def fetch_records(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        if is_test_env():
            yield from yield_samples([
                {"external_id": "OIRA-RIN-1234-AA00", "stage": "Proposed Rule Stage", "agency": "EPA"},
            ])
            return
        try:
            url = "https://www.reginfo.gov/public/do/eAgendaMain"
            resp = http_get(url, timeout=30)
            text = resp.text
            yield "oira-agenda-snapshot", {
                "external_id": "oira-agenda-snapshot",
                "source": "reginfo.gov",
                "size": len(text),
                "has_rin": "RIN" in text,
            }
        except Exception:
            raise
