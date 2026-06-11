"""Base class for all U.S. state registry connectors."""
from typing import Any, Dict, Iterable, Optional, Tuple

from us._common.base_us import USBaseConnector
from .schema import normalize as schema_normalize


class StateRegistryConnector(USBaseConnector):
    """Base for all 51 jurisdiction adapters."""

    jurisdiction_code: str = ""      # e.g. "us_ny"
    source_tier: str = "unknown"     # bulk | api | scrape | cobalt
    source_url: str = ""

    def normalize(self, external_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Override per-state to produce a StateEntity dict."""
        return schema_normalize(
            jurisdiction_code=self.jurisdiction_code,
            entity_id=external_id,
            legal_name=payload.get("legal_name", payload.get("name", "")),
            raw_status=payload.get("status"),
            raw_entity_type=payload.get("entity_type"),
            formation_date=payload.get("formation_date"),
            registered_agent_name=payload.get("registered_agent_name"),
            registered_agent_address=payload.get("registered_agent_address"),
            principal_address=payload.get("principal_address"),
            mailing_address=payload.get("mailing_address"),
            officers=payload.get("officers", []),
            source_tier=self.source_tier,
            source_url=self.source_url,
            extra=payload.get("extra", {}),
        )

    def evidence_excerpt(self, payload: Dict[str, Any]) -> str:
        name = payload.get("legal_name") or payload.get("name") or ""
        jur = self.jurisdiction_code
        status = payload.get("status", "")
        return f"{jur}: {name} ({status})"[:500]

    def fetch_records(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        raise NotImplementedError
