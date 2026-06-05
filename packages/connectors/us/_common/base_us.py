from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, Optional, Tuple

from connectors.sdk import BaseConnector


class USBaseConnector(BaseConnector):
    jurisdiction: str = "US"

    def normalize(self, external_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "external_id": external_id,
            "jurisdiction": self.jurisdiction,
            "source": self.name,
            "ingested_at": datetime.now(timezone.utc).isoformat(),
            "raw": payload,
        }

    def evidence_excerpt(self, payload: Dict[str, Any]) -> str:
        for key in ("title", "name", "company", "entity", "case_name", "committee"):
            if payload.get(key):
                return str(payload[key])[:500]
        return str(payload)[:500]

    def timeline_event(self, external_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return {
            "source": self.name,
            "external_id": external_id,
            "event_type": "ingestion",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "summary": self.evidence_excerpt(payload),
        }

    def graph_edges(self, external_id: str, payload: Dict[str, Any]) -> list:
        return []

    def run(self, persist_fn: Optional[Callable] = None) -> Dict[str, Any]:
        seen = 0
        errors = 0
        persisted = 0
        for external_id, payload in self.fetch_records():
            self.rate_limiter.wait()

            def _process():
                normalized = self.normalize(external_id, payload)
                if persist_fn:
                    persist_fn(
                        external_id=external_id,
                        raw=payload,
                        normalized=normalized,
                        excerpt=self.evidence_excerpt(payload),
                        timeline=self.timeline_event(external_id, payload),
                        edges=self.graph_edges(external_id, payload),
                    )
                return True

            try:
                self.retry.run(_process)
                seen += 1
                if persist_fn:
                    persisted += 1
            except Exception:
                errors += 1
        self.checkpointer.set("last_run", datetime.now(timezone.utc).isoformat())
        return {
            "seen": seen,
            "errors": errors,
            "persisted": persisted,
            "checkpoint": self.checkpointer.dump(),
        }
