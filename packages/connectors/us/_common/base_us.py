from typing import Any, Dict, Iterable, Tuple
from connectors.sdk import BaseConnector

class USBaseConnector(BaseConnector):
    jurisdiction: str = "US"
    def normalize(self, external_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        # minimal normalization stub; real mapping per-source
        return {"external_id": external_id, "jurisdiction": self.jurisdiction, "raw": payload}

    def evidence_excerpt(self, payload: Dict[str, Any]) -> str:
        return str(payload)[:500]
