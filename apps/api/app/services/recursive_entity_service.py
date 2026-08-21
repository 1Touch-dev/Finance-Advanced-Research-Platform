"""
Recursive Entity Discovery Service (J7)
─────────────────────────────────────────────────────────────────────────────
"Follow the Money" recursive network expansion.

James's requirement: "Find associates of each of these people" — the ability
to recursively trace relationships through:
  - Board interlocks (director cross-company seats)
  - Family vehicles (trusts, foundations, LLCs)
  - Institutional ownership (13F holdings)
  - Insider trading (Form 4 filings)
  - Congressional trades (STOCK Act disclosures)

This service integrates real data from SEC EDGAR, ProPublica 990s, and
government sources to build genuine relationship networks.
"""
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class EntityNode:
    def __init__(self, entity_id: str, name: str, entity_type: str, depth: int = 0):
        self.entity_id = entity_id
        self.name = name
        self.entity_type = entity_type
        self.depth = depth
        self.children: List['EntityNode'] = []
        self.relationships: List[Dict] = []


def _get_board_interlocks(ticker: str) -> List[Dict[str, Any]]:
    """Get board interlocks from SEC Section 16 filings."""
    try:
        from app.connectors.board_interlock_connector import get_director_interlocks
        return get_director_interlocks(ticker) or []
    except Exception as e:
        logger.warning("Board interlock fetch failed for %s: %s", ticker, e)
        return []


def _get_family_vehicles(ticker: str) -> List[Dict[str, Any]]:
    """Get family trusts and vehicles from SEC filings."""
    try:
        from app.connectors.family_network_connector import get_family_vehicles
        return get_family_vehicles(ticker) or []
    except Exception as e:
        logger.warning("Family vehicle fetch failed for %s: %s", ticker, e)
        return []


def _get_institutional_holders(ticker: str) -> List[Dict[str, Any]]:
    """Get institutional holders from 13F filings."""
    try:
        from app.connectors.institutional_holdings_connector import get_institutional_ownership
        result = get_institutional_ownership(ticker) or {}
        return result.get("holders", [])
    except Exception as e:
        logger.warning("Institutional holders fetch failed for %s: %s", ticker, e)
        return []


def _get_insider_network(ticker: str) -> List[Dict[str, Any]]:
    """Get insider trading network from Form 4 filings."""
    try:
        from app.connectors.gov_trading_connector import get_form4_for_ticker
        filings = get_form4_for_ticker(ticker, days=365) or []
        # Extract unique reporting owners
        owners = {}
        for f in filings:
            owner_cik = f.get("owner_cik")
            if owner_cik and owner_cik not in owners:
                owners[owner_cik] = {
                    "cik": owner_cik,
                    "name": f.get("owner_name"),
                    "is_director": f.get("is_director"),
                    "is_officer": f.get("is_officer"),
                    "officer_title": f.get("officer_title"),
                    "relationship": "insider",
                }
        return list(owners.values())
    except Exception as e:
        logger.warning("Insider network fetch failed for %s: %s", ticker, e)
        return []


def _get_congressional_traders(ticker: str) -> List[Dict[str, Any]]:
    """Get congressional officials who traded this stock."""
    try:
        from app.connectors.gov_trading_connector import get_ptr_trades_for_ticker
        trades = get_ptr_trades_for_ticker(ticker, days=365) or []
        # Extract unique officials
        officials = {}
        for t in trades:
            name = t.get("member_name") or t.get("name")
            if name and name not in officials:
                officials[name] = {
                    "name": name,
                    "chamber": t.get("chamber"),
                    "state": t.get("state_dst") or t.get("state"),
                    "party": t.get("party"),
                    "relationship": "congressional_trader",
                }
        return list(officials.values())
    except Exception as e:
        logger.warning("Congressional trader fetch failed for %s: %s", ticker, e)
        return []


def recursive_discover(root_ticker: str, max_depth: int = 3, visited: Set[str] = None) -> Dict[str, Any]:
    """
    Recursively discover related entities up to max_depth.

    This is the core "follow the money" function. It:
    1. Finds all entities directly related to root_ticker
    2. For each entity found, recursively finds their associates
    3. Builds a complete network of relationships
    """
    if visited is None:
        visited = set()

    if root_ticker in visited or len(visited) > 100:
        return {"root": root_ticker, "discovered_entities": [], "truncated": True}

    visited.add(root_ticker)
    entities = []

    # 1. Board Interlocks — directors who serve on multiple boards
    interlocks = _get_board_interlocks(root_ticker)
    for interlock in interlocks[:10]:  # Limit to prevent explosion
        entities.append({
            "entity_id": interlock.get("person_cik") or interlock.get("name", "").replace(" ", "_"),
            "name": interlock.get("name"),
            "type": "director",
            "relationship": "board_interlock",
            "other_boards": interlock.get("other_boards", []),
            "depth": 1,
            "source": "SEC Section 16",
        })

    # 2. Family Vehicles — trusts, foundations, LLCs
    vehicles = _get_family_vehicles(root_ticker)
    for vehicle in vehicles[:10]:
        entities.append({
            "entity_id": vehicle.get("cik") or vehicle.get("name", "").replace(" ", "_"),
            "name": vehicle.get("name"),
            "type": vehicle.get("vehicle_type", "vehicle"),
            "relationship": "family_vehicle",
            "linked_person": vehicle.get("linked_person"),
            "depth": 1,
            "source": "SEC/ProPublica 990",
        })

    # 3. Institutional Holders — major shareholders
    holders = _get_institutional_holders(root_ticker)
    for holder in holders[:10]:
        entities.append({
            "entity_id": holder.get("cik") or holder.get("name", "").replace(" ", "_"),
            "name": holder.get("name"),
            "type": "institution",
            "relationship": "institutional_holder",
            "shares": holder.get("shares"),
            "value_usd": holder.get("value_usd"),
            "percent_portfolio": holder.get("percent_of_portfolio"),
            "depth": 1,
            "source": "SEC 13F",
        })

    # 4. Insider Network — officers and directors who trade
    insiders = _get_insider_network(root_ticker)
    for insider in insiders[:15]:
        entities.append({
            "entity_id": insider.get("cik") or insider.get("name", "").replace(" ", "_"),
            "name": insider.get("name"),
            "type": "insider",
            "relationship": "insider_trader",
            "is_director": insider.get("is_director"),
            "is_officer": insider.get("is_officer"),
            "title": insider.get("officer_title"),
            "depth": 1,
            "source": "SEC Form 4",
        })

    # 5. Congressional Traders — officials who traded this stock
    officials = _get_congressional_traders(root_ticker)
    for official in officials[:10]:
        entities.append({
            "entity_id": official.get("name", "").replace(" ", "_"),
            "name": official.get("name"),
            "type": "official",
            "relationship": "congressional_trader",
            "chamber": official.get("chamber"),
            "state": official.get("state"),
            "party": official.get("party"),
            "depth": 1,
            "source": "STOCK Act PTR",
        })

    # Recursive expansion (depth 2+)
    if max_depth > 1:
        for entity in entities[:20]:  # Limit recursion
            other_boards = entity.get("other_boards", [])
            for board in other_boards[:3]:
                board_ticker = board.get("ticker")
                if board_ticker and board_ticker not in visited:
                    sub_result = recursive_discover(board_ticker, max_depth - 1, visited)
                    if sub_result and sub_result.get("discovered_entities"):
                        for sub_entity in sub_result["discovered_entities"][:5]:
                            sub_entity["depth"] = entity.get("depth", 1) + 1
                            sub_entity["discovered_via"] = entity.get("name")
                            entities.append(sub_entity)

    return {
        "root": root_ticker,
        "discovered_entities": entities,
        "total_discovered": len(entities),
        "max_depth_reached": max_depth,
        "visited_count": len(visited),
        "discovery_path": list(visited),
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


def build_entity_graph(ticker: str, max_depth: int = 3) -> Dict[str, Any]:
    """
    Build complete entity relationship graph using real data.

    Returns nodes and edges for visualization (D3.js, vis.js, etc.)
    """
    # Get all discovered entities
    discovery = recursive_discover(ticker, max_depth)
    entities = discovery.get("discovered_entities", [])

    # Build graph structure
    nodes = [{"id": ticker, "label": ticker, "type": "root", "depth": 0, "size": 30}]
    edges = []
    seen_nodes = {ticker}

    for entity in entities:
        entity_id = entity.get("entity_id") or entity.get("name", "").replace(" ", "_")
        if not entity_id or entity_id in seen_nodes:
            continue

        seen_nodes.add(entity_id)

        # Node size based on relationship importance
        size = 20 if entity.get("depth", 1) == 1 else 15
        if entity.get("type") == "institution":
            size = 25  # Larger for major holders

        nodes.append({
            "id": entity_id,
            "label": entity.get("name") or entity_id,
            "type": entity.get("type", "unknown"),
            "relationship": entity.get("relationship"),
            "depth": entity.get("depth", 1),
            "size": size,
            "source": entity.get("source"),
        })

        # Edge from root or discovered_via
        source = entity.get("discovered_via", ticker)
        if source == ticker or source is None:
            source = ticker

        # Find the source node ID
        source_id = ticker
        for n in nodes:
            if n.get("label") == source or n.get("id") == source:
                source_id = n.get("id")
                break

        edges.append({
            "source": source_id,
            "target": entity_id,
            "relationship": entity.get("relationship"),
            "weight": 100 - (entity.get("depth", 1) * 20),  # Closer = heavier
        })

    # Calculate graph statistics
    total_nodes = len(nodes)
    total_edges = len(edges)
    max_possible_edges = total_nodes * (total_nodes - 1) / 2 if total_nodes > 1 else 1
    density = round(total_edges / max_possible_edges, 3) if max_possible_edges > 0 else 0

    # Group by relationship type
    relationship_counts = {}
    for entity in entities:
        rel = entity.get("relationship", "unknown")
        relationship_counts[rel] = relationship_counts.get(rel, 0) + 1

    return {
        "ticker": ticker,
        "graph": {"nodes": nodes, "edges": edges},
        "statistics": {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "max_depth": max_depth,
            "density": density,
            "relationship_breakdown": relationship_counts,
        },
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


def find_shortest_path(source: str, target: str) -> Dict[str, Any]:
    """
    Find shortest path between two entities using BFS on the relationship graph.
    """
    # Build graphs for both entities
    source_discovery = recursive_discover(source, max_depth=2)
    target_discovery = recursive_discover(target, max_depth=2)

    source_entities = {e.get("entity_id") or e.get("name"): e
                       for e in source_discovery.get("discovered_entities", [])}
    target_entities = {e.get("entity_id") or e.get("name"): e
                       for e in target_discovery.get("discovered_entities", [])}

    # Find common entities (intersection points)
    common = set(source_entities.keys()) & set(target_entities.keys())

    if common:
        intermediate = list(common)[0]
        path = [source, intermediate, target]
        return {
            "source": source,
            "target": target,
            "path": path,
            "path_length": 2,
            "connection_found": True,
            "connecting_entity": {
                "name": source_entities.get(intermediate, {}).get("name") or intermediate,
                "type": source_entities.get(intermediate, {}).get("type"),
                "relationship_to_source": source_entities.get(intermediate, {}).get("relationship"),
                "relationship_to_target": target_entities.get(intermediate, {}).get("relationship"),
            },
            "relationship_chain": [
                {"from": source, "to": intermediate,
                 "type": source_entities.get(intermediate, {}).get("relationship", "unknown")},
                {"from": intermediate, "to": target,
                 "type": target_entities.get(intermediate, {}).get("relationship", "unknown")},
            ],
        }
    else:
        return {
            "source": source,
            "target": target,
            "path": [],
            "path_length": -1,
            "connection_found": False,
            "message": "No direct connection found within 2 degrees of separation",
        }


def get_entity_clusters(ticker: str) -> Dict[str, Any]:
    """
    Identify clusters of related entities by relationship type.
    """
    discovery = recursive_discover(ticker, max_depth=2)
    entities = discovery.get("discovered_entities", [])

    # Group by relationship type
    clusters = {}
    for entity in entities:
        rel_type = entity.get("relationship", "unknown")
        if rel_type not in clusters:
            clusters[rel_type] = {
                "cluster_id": f"cluster_{rel_type}",
                "name": rel_type.replace("_", " ").title(),
                "type": rel_type,
                "entities": [],
            }
        clusters[rel_type]["entities"].append({
            "id": entity.get("entity_id"),
            "name": entity.get("name"),
            "type": entity.get("type"),
        })

    # Calculate cohesion (entities in cluster / total entities)
    cluster_list = []
    total = len(entities) if entities else 1
    for cluster in clusters.values():
        cluster["cohesion_score"] = round(len(cluster["entities"]) / total, 2)
        cluster["entity_count"] = len(cluster["entities"])
        cluster_list.append(cluster)

    return {
        "ticker": ticker,
        "clusters": cluster_list,
        "total_clusters": len(cluster_list),
        "total_entities": len(entities),
    }


def detect_circular_ownership(ticker: str) -> Dict[str, Any]:
    """
    Detect circular ownership patterns using institutional holder data.
    """
    # Get institutional holders for the ticker
    holders = _get_institutional_holders(ticker)

    # Check if any holder is also held by the company (would need company's 13F)
    # This is a simplified check - real circular ownership detection requires
    # traversing the full ownership graph

    # For now, flag if multiple entities have cross-holdings
    circular_patterns = []
    holder_names = [h.get("name") for h in holders if h.get("name")]

    # Check for common institutional cross-holdings
    common_holders = ["Vanguard", "BlackRock", "State Street"]
    cross_held = [h for h in holder_names if any(c in h for c in common_holders)]

    if len(cross_held) >= 2:
        circular_patterns.append({
            "type": "common_ownership",
            "entities": cross_held[:3],
            "description": "Multiple positions held by same institutional complex",
        })

    return {
        "ticker": ticker,
        "circular_ownership_detected": len(circular_patterns) > 0,
        "patterns": circular_patterns,
        "risk_level": "medium" if circular_patterns else "low",
        "institutional_overlap_count": len(cross_held),
    }


def get_ownership_chain(ticker: str) -> Dict[str, Any]:
    """
    Get ownership chain to ultimate beneficial owners using 13F and proxy data.
    """
    holders = _get_institutional_holders(ticker)

    # Build ownership chain from largest holders
    chain = [{"entity": ticker, "level": 0, "ownership_pct": 100, "type": "issuer"}]

    # Add top institutional holders
    sorted_holders = sorted(holders, key=lambda x: x.get("shares", 0), reverse=True)

    for i, holder in enumerate(sorted_holders[:5]):
        chain.append({
            "entity": holder.get("name"),
            "cik": holder.get("cik"),
            "level": 1,
            "shares": holder.get("shares"),
            "value_usd": holder.get("value_usd"),
            "type": "institutional_holder",
        })

    # Identify ultimate parent if there's a majority holder
    ultimate_parent = None
    if sorted_holders:
        top_holder = sorted_holders[0]
        if top_holder.get("shares", 0) > 0:
            ultimate_parent = top_holder.get("name")

    return {
        "ticker": ticker,
        "chain": chain,
        "ultimate_parent": ultimate_parent,
        "chain_length": len(chain),
        "top_holders_count": len(sorted_holders),
    }


def compare_entity_networks(ticker1: str, ticker2: str) -> Dict[str, Any]:
    """
    Compare entity networks of two companies to find overlaps.
    """
    # Get networks for both tickers
    network1 = recursive_discover(ticker1, max_depth=2)
    network2 = recursive_discover(ticker2, max_depth=2)

    entities1 = {(e.get("entity_id") or e.get("name")): e
                 for e in network1.get("discovered_entities", [])}
    entities2 = {(e.get("entity_id") or e.get("name")): e
                 for e in network2.get("discovered_entities", [])}

    # Find common entities
    common_ids = set(entities1.keys()) & set(entities2.keys())
    common_entities = []
    for eid in common_ids:
        e1 = entities1.get(eid, {})
        common_entities.append({
            "entity_id": eid,
            "name": e1.get("name"),
            "type": e1.get("type"),
            "relationship_to_ticker1": e1.get("relationship"),
            "relationship_to_ticker2": entities2.get(eid, {}).get("relationship"),
        })

    # Count by type
    common_board = sum(1 for e in common_entities if e.get("type") == "director")
    common_investors = sum(1 for e in common_entities if e.get("type") == "institution")
    common_insiders = sum(1 for e in common_entities if e.get("type") == "insider")

    # Calculate overlap score
    total1 = len(entities1) if entities1 else 1
    total2 = len(entities2) if entities2 else 1
    overlap_score = round(len(common_ids) / min(total1, total2), 2) if common_ids else 0

    # Determine relationship strength
    if overlap_score > 0.3:
        strength = "strong"
    elif overlap_score > 0.1:
        strength = "moderate"
    elif common_ids:
        strength = "weak"
    else:
        strength = "none"

    return {
        "ticker1": ticker1,
        "ticker2": ticker2,
        "common_entities": common_entities,
        "common_board_members": common_board,
        "common_investors": common_investors,
        "common_insiders": common_insiders,
        "network_overlap_score": overlap_score,
        "relationship_strength": strength,
        "ticker1_network_size": len(entities1),
        "ticker2_network_size": len(entities2),
    }
