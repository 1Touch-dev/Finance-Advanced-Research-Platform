"""
PayPal Mafia Graph Loader
══════════════════════════════════════════════════════════════════════════════

Loads the PayPal Mafia seed data into the Entity Graph Store.
This provides the initial dataset for James's "Follow the Money" demonstration.
"""

import logging
from datetime import datetime
from typing import Dict, Any

from app.services import entity_graph_service as graph
from app.data.paypal_mafia_seed import (
    get_all_entities,
    get_all_relationships,
    get_seed_stats,
)

log = logging.getLogger(__name__)


def load_paypal_mafia_graph() -> Dict[str, Any]:
    """
    Load all PayPal Mafia entities and relationships into the graph.

    Returns statistics about what was loaded.
    """
    stats = {
        "entities_loaded": 0,
        "entities_failed": 0,
        "edges_loaded": 0,
        "edges_failed": 0,
        "errors": [],
    }

    # Load entities first
    for entity_data in get_all_entities():
        try:
            graph.add_entity(
                entity_id=entity_data["id"],
                kind=entity_data["kind"],
                name=entity_data["name"],
                identifiers=entity_data.get("identifiers", {}),
                aliases=entity_data.get("aliases", []),
                meta=entity_data.get("meta", {}),
            )
            stats["entities_loaded"] += 1
        except Exception as e:
            stats["entities_failed"] += 1
            stats["errors"].append(f"Entity {entity_data['id']}: {str(e)}")
            log.warning("Failed to load entity %s: %s", entity_data["id"], e)

    # Load relationships
    for rel_data in get_all_relationships():
        try:
            # Parse dates if present
            as_of = None
            valid_to = None
            if rel_data.get("as_of"):
                try:
                    as_of = datetime.strptime(rel_data["as_of"], "%Y-%m-%d")
                except ValueError:
                    pass
            if rel_data.get("valid_to"):
                try:
                    valid_to = datetime.strptime(rel_data["valid_to"], "%Y-%m-%d")
                except ValueError:
                    pass

            # Format evidence
            evidence = rel_data.get("evidence", {})
            evidence_refs = [{
                "document_id": evidence.get("document_id", "unknown"),
                "source_name": evidence.get("source_name", "unknown"),
                "source_url": evidence.get("source_url"),
                "excerpt": evidence.get("excerpt"),
            }]

            graph.add_edge(
                edge_id=rel_data["id"],
                src_entity_id=rel_data["src"],
                dst_entity_id=rel_data["dst"],
                relationship_type=rel_data["type"],
                confidence_tier=rel_data["confidence"],
                evidence_refs=evidence_refs,
                as_of=as_of,
                valid_to=valid_to,
                source_name=evidence.get("source_name"),
                meta=rel_data.get("meta", {}),
            )
            stats["edges_loaded"] += 1
        except Exception as e:
            stats["edges_failed"] += 1
            stats["errors"].append(f"Edge {rel_data['id']}: {str(e)}")
            log.warning("Failed to load edge %s: %s", rel_data["id"], e)

    return stats


def get_paypal_mafia_stats() -> Dict[str, Any]:
    """Get statistics about the PayPal Mafia seed data."""
    seed_stats = get_seed_stats()
    graph_stats = graph.get_graph_stats()

    return {
        "seed_data": seed_stats,
        "graph_state": graph_stats,
        "loaded": graph_stats["total_entities"] > 0,
    }


def explore_paypal_mafia(
    seed_person: str = "person:peter-thiel",
    max_depth: int = 3,
    max_nodes: int = 500,
) -> Dict[str, Any]:
    """
    Explore the PayPal Mafia network from a seed person.

    Default seed is Peter Thiel as the most connected member.
    """
    return graph.explore_network(
        seed_entity_id=seed_person,
        max_depth=max_depth,
        max_nodes=max_nodes,
        min_confidence="INFERRED",
    )


def find_paypal_connection(
    person_a: str,
    person_b: str,
    max_depth: int = 4,
) -> Dict[str, Any]:
    """
    Find connections between two PayPal Mafia members.

    Example: find_paypal_connection("person:peter-thiel", "person:steve-chen")
    """
    paths = graph.find_connection(
        src_entity_id=person_a,
        dst_entity_id=person_b,
        max_depth=max_depth,
        min_confidence="INFERRED",
    )

    return {
        "src": person_a,
        "dst": person_b,
        "paths_found": len(paths),
        "paths": paths,
    }


# Pre-defined interesting queries
INTERESTING_QUERIES = [
    {
        "name": "Thiel to YouTube",
        "description": "How is Peter Thiel connected to YouTube founders?",
        "src": "person:peter-thiel",
        "dst": "org:youtube",
    },
    {
        "name": "Musk to Affirm",
        "description": "Connection between Elon Musk and Affirm",
        "src": "person:elon-musk",
        "dst": "org:affirm",
    },
    {
        "name": "Sequoia to PayPal",
        "description": "Sequoia's connection to PayPal network",
        "src": "fund:sequoia",
        "dst": "org:paypal",
    },
    {
        "name": "Hoffman to Palantir",
        "description": "Reid Hoffman's path to Palantir",
        "src": "person:reid-hoffman",
        "dst": "org:palantir",
    },
]


def get_interesting_queries() -> list:
    """Get pre-defined interesting network queries."""
    return INTERESTING_QUERIES
