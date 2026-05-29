from typing import Iterable, Tuple, Dict, Any
import time
from connectors.sdk import BaseConnector
from .._common.base_us import USBaseConnector

class SECEDGARConnector(USBaseConnector):
    name = "sec_edgar"
    def fetch_records(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        # Placeholder: In production, call SEC EDGAR APIs; use a simple fixture-like yield here
        samples = [
            {"external_id": "0000320193-23-000105", "company": "Apple Inc.", "form": "10-K", "year": 2023},
            {"external_id": "0000789019-23-000012", "company": "Microsoft Corp.", "form": "10-Q", "q": 2},
        ]
        for it in samples:
            yield it["external_id"], it
            time.sleep(0.05)
