"""
Orchestrator for all 51 U.S. state registry connectors.

Runs every jurisdiction and aggregates metrics.
"""
import importlib
import os
import sys
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .registry import JURISDICTIONS


def _load_connector(meta: Dict) -> Any:
    """Dynamically load the connector class from registry metadata."""
    module_path = meta["adapter_module"]
    class_name = meta["adapter_class"]

    if class_name == "GenericScrapedStateConnector":
        from us.state_registry.states.scrape_generic import GenericScrapedStateConnector
        return GenericScrapedStateConnector(jurisdiction_code=meta["jurisdiction_code"], creds={})

    mod = importlib.import_module(module_path)
    cls = getattr(mod, class_name)
    return cls(creds={})


def run_all_jurisdictions(
    persist_fn=None,
    jurisdictions: Optional[List[str]] = None,
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    Run all (or specified) jurisdiction connectors.

    Returns aggregated metrics dict.
    """
    target = jurisdictions or list(JURISDICTIONS.keys())
    results = {}
    total_seen = 0
    total_errors = 0
    success_count = 0
    partial_count = 0
    failed_count = 0

    for jcode in target:
        meta = JURISDICTIONS.get(jcode)
        if not meta:
            results[jcode] = {"status": "unknown", "seen": 0, "error": "Not in registry"}
            continue

        try:
            connector = _load_connector(meta)
            metrics = connector.run(persist_fn=persist_fn)
            seen = metrics.get("seen", 0)
            errs = metrics.get("errors", 0)
            total_seen += seen
            total_errors += errs

            if seen > 0 and errs == 0:
                status = "success"
                success_count += 1
            elif seen > 0:
                status = "partial"
                partial_count += 1
            else:
                status = "no_records"
                partial_count += 1

            results[jcode] = {
                "status": status,
                "seen": seen,
                "errors": errs,
                "tier": meta["tier"],
                "name": meta["name"],
                "last_run": datetime.now(timezone.utc).isoformat(),
            }
            if verbose:
                print(f"  [{jcode}] {status} seen={seen} errors={errs}", flush=True)

        except Exception as exc:
            failed_count += 1
            err_msg = str(exc)
            results[jcode] = {
                "status": "error",
                "seen": 0,
                "errors": 1,
                "tier": meta.get("tier", "unknown"),
                "name": meta.get("name", jcode),
                "error": err_msg,
                "last_run": datetime.now(timezone.utc).isoformat(),
            }
            if verbose:
                print(f"  [{jcode}] ERROR: {err_msg}", flush=True)

    return {
        "total_jurisdictions": len(target),
        "success": success_count,
        "partial": partial_count,
        "failed": failed_count,
        "total_records_seen": total_seen,
        "total_errors": total_errors,
        "jurisdictions": results,
        "ran_at": datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
    summary = run_all_jurisdictions(verbose=True)
    print(f"\n=== Registry Orchestrator Summary ===")
    print(f"Total: {summary['total_jurisdictions']} | Success: {summary['success']} | Partial: {summary['partial']} | Failed: {summary['failed']}")
    print(f"Records seen: {summary['total_records_seen']}")
