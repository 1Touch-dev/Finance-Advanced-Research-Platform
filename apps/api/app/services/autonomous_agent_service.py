"""
Autonomous Agent Service (J6)
Auto-discover subsidiaries/family entities using the real Entity Graph Store
and SEC EDGAR connector.
"""
import logging
import threading
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

from app.services.entity_graph_service import (
    get_graph_store,
    get_recursion_engine,
    RecursionConfig,
    ConfidenceTier,
    RelationshipType,
)
from app.services import graph_ingestion_service
from app.connectors.sec_edgar_connector import (
    get_filer_cik,
    get_company_submissions,
    get_insider_transactions,
)

log = logging.getLogger(__name__)

_JOBS: Dict[str, Dict] = {}


def _resolve_entity_id_for_ticker(ticker: str) -> Optional[str]:
    """Resolve a ticker to its graph entity ID, checking multiple schemes."""
    store = get_graph_store()
    store._ensure_loaded()

    # Try resolving by ticker identifier
    entity = store.resolve_entity("ticker", ticker.upper())
    if entity:
        return entity.id

    # Try CIK-based ID (how graph_ingestion_service creates org entities)
    cik = get_filer_cik(ticker)
    if cik:
        entity = store.resolve_entity("CIK", cik)
        if entity:
            return entity.id
        # Convention used by graph_ingestion_service
        candidate = f"org:sec-{cik.zfill(10)}"
        if store.get_entity(candidate):
            return candidate

    # Scan entities for matching ticker in identifiers
    for eid, ent in store._entities.items():
        if ent.identifiers.get("ticker", "").upper() == ticker.upper():
            return eid

    return None


def _run_discovery(job_id: str, ticker: str, depth: int, entity_types: Optional[List[str]]):
    """Background worker that performs entity ingestion."""
    job = _JOBS[job_id]
    try:
        job["status"] = "running"

        cik = get_filer_cik(ticker)
        company_name = None
        if cik:
            subs = get_company_submissions(cik)
            company_name = subs.get("name") or ticker

        result = graph_ingestion_service.ingest_entity_full(
            entity_name=company_name or ticker,
            cik=cik,
            include_sec=True,
            include_fec=True,
            include_contracts=True,
        )

        # If depth > 1, run recursive expansion on discovered entities
        if depth > 1:
            store = get_graph_store()
            entity_id = _resolve_entity_id_for_ticker(ticker)
            if entity_id:
                config = RecursionConfig(
                    max_depth=min(depth, 5),
                    max_nodes=200,
                    min_confidence=ConfidenceTier.INFERRED,
                )
                get_recursion_engine().explore(entity_id, config)

        job["status"] = "completed"
        job["completed_at"] = datetime.utcnow().isoformat() + "Z"
        job["result"] = result
    except Exception as exc:
        log.error("Discovery job %s failed: %s", job_id, exc)
        job["status"] = "failed"
        job["error"] = str(exc)
        job["completed_at"] = datetime.utcnow().isoformat() + "Z"


def start_discovery_job(ticker: str, depth: int = 2, entity_types: List[str] = None) -> Dict[str, Any]:
    """Start an autonomous entity discovery job in a background thread."""
    job_id = str(uuid.uuid4())
    job = {
        "job_id": job_id,
        "ticker": ticker.upper(),
        "depth": depth,
        "entity_types": entity_types,
        "status": "queued",
        "started_at": datetime.utcnow().isoformat() + "Z",
        "completed_at": None,
        "result": None,
        "error": None,
    }
    _JOBS[job_id] = job

    thread = threading.Thread(
        target=_run_discovery,
        args=(job_id, ticker, depth, entity_types),
        daemon=True,
    )
    job["_thread"] = thread
    thread.start()

    return {
        "job_id": job_id,
        "status": "queued",
        "ticker": ticker.upper(),
        "depth": depth,
        "started_at": job["started_at"],
    }


def get_job_status(job_id: str) -> Dict[str, Any]:
    """Return actual status of a running background discovery job."""
    job = _JOBS.get(job_id)
    if not job:
        return {"status": "not_found", "job_id": job_id}

    response = {
        "job_id": job_id,
        "ticker": job["ticker"],
        "status": job["status"],
        "started_at": job["started_at"],
        "completed_at": job.get("completed_at"),
    }

    if job["status"] == "completed" and job.get("result"):
        response["result_summary"] = {
            "total_entities": job["result"].get("total_entities", 0),
            "total_edges": job["result"].get("total_edges", 0),
            "errors": job["result"].get("errors", []),
        }
    elif job["status"] == "failed":
        response["error"] = job.get("error")

    return response


def get_discovered_entities(ticker: str) -> Dict[str, Any]:
    """Query the EntityGraphStore for all entities connected to this ticker."""
    store = get_graph_store()
    entity_id = _resolve_entity_id_for_ticker(ticker)

    if not entity_id:
        return {
            "ticker": ticker,
            "status": "no_entity",
            "message": f"No entity found for ticker {ticker}. Run a discovery job first.",
            "entities": [],
        }

    # Gather all neighbors (1-hop outgoing + incoming)
    outgoing = store.get_outgoing_edges(entity_id)
    incoming = store.get_incoming_edges(entity_id)

    seen_ids = {entity_id}
    entities = []

    root = store.get_entity(entity_id)
    if root:
        entities.append({
            "id": root.id,
            "kind": root.kind,
            "name": root.name,
            "identifiers": root.identifiers,
            "relationship": "self",
        })

    for edge in outgoing:
        if edge.dst_entity_id not in seen_ids:
            seen_ids.add(edge.dst_entity_id)
            dst = store.get_entity(edge.dst_entity_id)
            if dst:
                entities.append({
                    "id": dst.id,
                    "kind": dst.kind,
                    "name": dst.name,
                    "identifiers": dst.identifiers,
                    "relationship": edge.relationship_type,
                    "direction": "outgoing",
                })

    for edge in incoming:
        if edge.src_entity_id not in seen_ids:
            seen_ids.add(edge.src_entity_id)
            src = store.get_entity(edge.src_entity_id)
            if src:
                entities.append({
                    "id": src.id,
                    "kind": src.kind,
                    "name": src.name,
                    "identifiers": src.identifiers,
                    "relationship": edge.relationship_type,
                    "direction": "incoming",
                })

    return {
        "ticker": ticker,
        "root_entity_id": entity_id,
        "count": len(entities),
        "entities": entities,
    }


def get_entity_graph(ticker: str, depth: int = 2) -> Dict[str, Any]:
    """Use EntityGraphStore BFS (RecursionEngine.explore) for real graph neighborhood."""
    entity_id = _resolve_entity_id_for_ticker(ticker)

    if not entity_id:
        return {
            "ticker": ticker,
            "status": "no_entity",
            "message": f"No entity found for ticker {ticker}. Run a discovery job first.",
            "nodes": [],
            "edges": [],
        }

    config = RecursionConfig(
        max_depth=min(depth, 5),
        max_nodes=500,
        min_confidence=ConfidenceTier.SPECULATIVE,
    )
    result = get_recursion_engine().explore(entity_id, config)

    if "error" in result:
        return {"ticker": ticker, "status": "error", "message": result["error"]}

    return {
        "ticker": ticker,
        "root_entity_id": entity_id,
        **result,
    }


def discover_subsidiaries(ticker: str) -> Dict[str, Any]:
    """
    Discover subsidiaries via SEC EDGAR (Exhibit 21 data) and graph edges.

    Queries the graph for subsidiary_of edges first, then supplements with
    SEC submission data if available.
    """
    store = get_graph_store()
    entity_id = _resolve_entity_id_for_ticker(ticker)
    subsidiaries = []

    if entity_id:
        # Look for subsidiary_of edges where this entity is the parent (incoming)
        incoming = store.get_incoming_edges(entity_id)
        for edge in incoming:
            if edge.relationship_type == RelationshipType.SUBSIDIARY_OF.value:
                sub = store.get_entity(edge.src_entity_id)
                if sub:
                    subsidiaries.append({
                        "id": sub.id,
                        "name": sub.name,
                        "kind": sub.kind,
                        "confidence": edge.confidence_tier.value,
                        "source": edge.source_name,
                        "as_of": str(edge.as_of) if edge.as_of else None,
                    })

        # Also check owns edges
        outgoing = store.get_outgoing_edges(entity_id)
        seen = {s["id"] for s in subsidiaries}
        for edge in outgoing:
            if edge.relationship_type == RelationshipType.OWNS.value:
                if edge.dst_entity_id not in seen:
                    owned = store.get_entity(edge.dst_entity_id)
                    if owned and owned.kind == "org":
                        subsidiaries.append({
                            "id": owned.id,
                            "name": owned.name,
                            "kind": owned.kind,
                            "confidence": edge.confidence_tier.value,
                            "source": edge.source_name,
                            "relationship": "owned",
                            "as_of": str(edge.as_of) if edge.as_of else None,
                        })

    # Supplement with SEC submission data for filing context
    sec_context = None
    cik = get_filer_cik(ticker)
    if cik:
        subs = get_company_submissions(cik, forms=["10-K", "EX-21"], limit=5)
        ex21_filings = [f for f in subs.get("filings", []) if "21" in f.get("form", "")]
        if ex21_filings:
            sec_context = {
                "exhibit_21_filings": len(ex21_filings),
                "latest_filing_date": ex21_filings[0].get("filing_date") if ex21_filings else None,
            }

    return {
        "ticker": ticker,
        "root_entity_id": entity_id,
        "count": len(subsidiaries),
        "subsidiaries": subsidiaries,
        "sec_exhibit_21": sec_context,
    }


def discover_investments(ticker: str) -> Dict[str, Any]:
    """Query graph for invested_in edges originating from this ticker's entity."""
    store = get_graph_store()
    entity_id = _resolve_entity_id_for_ticker(ticker)
    investments = []

    if entity_id:
        outgoing = store.get_outgoing_edges(entity_id)
        for edge in outgoing:
            if edge.relationship_type == RelationshipType.INVESTED_IN.value:
                target = store.get_entity(edge.dst_entity_id)
                if target:
                    investments.append({
                        "id": target.id,
                        "name": target.name,
                        "kind": target.kind,
                        "confidence": edge.confidence_tier.value,
                        "source": edge.source_name,
                        "as_of": str(edge.as_of) if edge.as_of else None,
                        "meta": edge.meta,
                    })

        # Also check LP relationships
        for edge in outgoing:
            if edge.relationship_type == RelationshipType.LP_OF.value:
                target = store.get_entity(edge.dst_entity_id)
                if target:
                    investments.append({
                        "id": target.id,
                        "name": target.name,
                        "kind": target.kind,
                        "relationship": "lp_of",
                        "confidence": edge.confidence_tier.value,
                        "source": edge.source_name,
                        "as_of": str(edge.as_of) if edge.as_of else None,
                        "meta": edge.meta,
                    })

    return {
        "ticker": ticker,
        "root_entity_id": entity_id,
        "count": len(investments),
        "investments": investments,
    }


def discover_board_connections(ticker: str) -> Dict[str, Any]:
    """Query graph for board_member edges pointing at this ticker's entity."""
    store = get_graph_store()
    entity_id = _resolve_entity_id_for_ticker(ticker)
    board_members = []

    if entity_id:
        incoming = store.get_incoming_edges(entity_id)
        for edge in incoming:
            if edge.relationship_type == RelationshipType.BOARD_MEMBER.value:
                person = store.get_entity(edge.src_entity_id)
                if person:
                    # Find other board seats for this person
                    other_seats = []
                    person_outgoing = store.get_outgoing_edges(person.id)
                    for pe in person_outgoing:
                        if (pe.relationship_type == RelationshipType.BOARD_MEMBER.value
                                and pe.dst_entity_id != entity_id):
                            other_org = store.get_entity(pe.dst_entity_id)
                            if other_org:
                                other_seats.append({
                                    "id": other_org.id,
                                    "name": other_org.name,
                                })

                    board_members.append({
                        "id": person.id,
                        "name": person.name,
                        "confidence": edge.confidence_tier.value,
                        "source": edge.source_name,
                        "as_of": str(edge.as_of) if edge.as_of else None,
                        "other_board_seats": other_seats,
                    })

    return {
        "ticker": ticker,
        "root_entity_id": entity_id,
        "count": len(board_members),
        "board_members": board_members,
    }


def get_family_tree(ticker: str) -> Dict[str, Any]:
    """
    Build corporate family tree from graph edges.

    Traverses subsidiary_of, owns, and controls edges to construct
    the parent-child hierarchy.
    """
    store = get_graph_store()
    entity_id = _resolve_entity_id_for_ticker(ticker)

    if not entity_id:
        return {
            "ticker": ticker,
            "status": "no_entity",
            "message": f"No entity found for ticker {ticker}. Run a discovery job first.",
            "tree": None,
        }

    root = store.get_entity(entity_id)

    # Find parent (if this entity is subsidiary_of something)
    parent_info = None
    outgoing = store.get_outgoing_edges(entity_id)
    for edge in outgoing:
        if edge.relationship_type == RelationshipType.SUBSIDIARY_OF.value:
            parent = store.get_entity(edge.dst_entity_id)
            if parent:
                parent_info = {"id": parent.id, "name": parent.name, "kind": parent.kind}
                break

    # Find children (entities that are subsidiary_of this entity, or that it owns)
    children = []
    incoming = store.get_incoming_edges(entity_id)
    seen_children = set()

    for edge in incoming:
        if edge.relationship_type in (
            RelationshipType.SUBSIDIARY_OF.value,
        ):
            if edge.src_entity_id not in seen_children:
                seen_children.add(edge.src_entity_id)
                child = store.get_entity(edge.src_entity_id)
                if child:
                    children.append({
                        "id": child.id,
                        "name": child.name,
                        "kind": child.kind,
                        "relationship": edge.relationship_type,
                    })

    for edge in outgoing:
        if edge.relationship_type in (
            RelationshipType.OWNS.value,
            RelationshipType.CONTROLS.value,
        ):
            if edge.dst_entity_id not in seen_children:
                seen_children.add(edge.dst_entity_id)
                child = store.get_entity(edge.dst_entity_id)
                if child and child.kind == "org":
                    children.append({
                        "id": child.id,
                        "name": child.name,
                        "kind": child.kind,
                        "relationship": edge.relationship_type,
                    })

    return {
        "ticker": ticker,
        "root_entity_id": entity_id,
        "tree": {
            "parent": parent_info,
            "entity": {
                "id": root.id,
                "name": root.name,
                "kind": root.kind,
                "identifiers": root.identifiers,
            } if root else None,
            "children": children,
            "children_count": len(children),
        },
    }
