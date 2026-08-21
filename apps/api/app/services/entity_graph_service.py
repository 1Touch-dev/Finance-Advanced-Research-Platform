"""
Entity Graph Store Service
══════════════════════════════════════════════════════════════════════════════

The core intelligence architecture for the Finance Research Platform.
Implements a recursive, evidence-backed graph over money, people, and entities.

Per James's vision: "go further and further in always" - this service provides:
1. Entity resolution and storage
2. Edge (relationship) management with evidence refs
3. Recursion engine with depth/cost caps
4. Point-in-time queries (A4 compliance)
5. Confidence tier tracking (A7 compliance)

Audit Compliance:
- A1: Source tracking on every edge
- A3: Entity resolution with deterministic IDs
- A4: Point-in-time queries via as_of/valid_to
- A5: Evidence requirement enforced (every edge cites a document)
- A6: No causal assertions - only correlational findings
- A7: Confidence tiers with accuracy targets
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

log = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONFIDENCE TIERS (A7 - Calibration Audit)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ConfidenceTier(str, Enum):
    """
    Calibrated confidence tiers with accuracy targets.

    Per A7 Audit Playbook:
    - CONFIRMED: Primary source document, directly asserted (≥99% accuracy)
    - REPORTED: ≥2 credible secondary sources agreeing (≥90% accuracy)
    - INFERRED: Derived from ≥2 confirmed facts, method stated (≥70% accuracy)
    - SPECULATIVE: Single weak source or pattern-based (≥40% accuracy)
    """
    CONFIRMED = "CONFIRMED"      # ≥99% target
    REPORTED = "REPORTED"        # ≥90% target
    INFERRED = "INFERRED"        # ≥70% target
    SPECULATIVE = "SPECULATIVE"  # ≥40% target


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RELATIONSHIP TYPES (Closed Vocabulary - A5 compliance)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class RelationshipType(str, Enum):
    """Closed vocabulary of edge types - no free text allowed."""
    # Ownership & Control
    OWNS = "owns"                      # Company A owns Company B
    CONTROLS = "controls"              # Person controls Company
    SUBSIDIARY_OF = "subsidiary_of"    # Company is subsidiary of Parent

    # Investment
    INVESTED_IN = "invested_in"        # VC/PE invested in Company
    CO_INVESTED = "co_invested"        # Two investors co-invested in same company
    LP_OF = "lp_of"                    # LP in a fund

    # Employment & Board
    EMPLOYED_AT = "employed_at"        # Person employed at Company
    BOARD_MEMBER = "board_member"      # Person on board of Company
    ADVISOR_TO = "advisor_to"          # Person advises Company
    FOUNDER_OF = "founder_of"          # Person founded Company

    # Political
    DONATES_TO = "donates_to"          # Person/PAC donates to Candidate/PAC
    LOBBIED_FOR = "lobbied_for"        # Lobbyist worked for Client
    REPRESENTED_BY = "represented_by"  # Entity represented by Lobbyist

    # Government
    AWARDED_TO = "awarded_to"          # Contract awarded to Company
    FILED_BY = "filed_by"              # Filing made by Entity
    REGULATES = "regulates"            # Agency regulates Entity

    # Legal
    PARTY_TO = "party_to"              # Entity is party to Case
    RELATED_TO = "related_to"          # Related-party transaction

    # Social/Network
    AFFILIATED = "affiliated"          # General affiliation


VALID_RELATIONSHIP_TYPES = set(rt.value for rt in RelationshipType)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DATA CLASSES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class EntityNode:
    """Canonical entity in the graph."""
    id: str                          # Internal ID
    kind: str                        # person|org|fund|agency|pac|case
    name: str                        # Display name
    identifiers: Dict[str, str] = field(default_factory=dict)  # CIK, LEI, EIN, FEC, etc.
    aliases: List[str] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvidenceRef:
    """Reference to source document proving a claim."""
    document_id: str                 # SHA256 or source native ID
    source_name: str                 # e.g., "SEC EDGAR", "FEC", "OpenSecrets"
    source_url: Optional[str] = None
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    excerpt: Optional[str] = None    # Quoted text supporting the claim
    retrieved_at: Optional[datetime] = None


@dataclass
class Edge:
    """
    Relationship between two entities with full provenance.

    Per A5 Audit: Every edge MUST have an evidence_ref.
    This is the atomic unit of the intelligence graph.
    """
    id: str
    src_entity_id: str
    dst_entity_id: str
    relationship_type: str           # From closed vocabulary
    confidence_tier: ConfidenceTier
    evidence_refs: List[EvidenceRef]  # REQUIRED - must be non-empty

    # Temporal validity (A4 - Point-in-Time)
    as_of: Optional[datetime] = None      # When relationship started
    valid_to: Optional[datetime] = None   # When it ended (null = active)

    # Provenance
    source_id: Optional[int] = None
    source_name: Optional[str] = None
    extracted_by: Optional[str] = None    # Parser version

    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphPath:
    """A path through the graph from source to destination."""
    nodes: List[EntityNode]
    edges: List[Edge]
    total_depth: int
    confidence_floor: ConfidenceTier  # Lowest confidence in the path

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": [{"id": n.id, "name": n.name, "kind": n.kind} for n in self.nodes],
            "edges": [{
                "src": e.src_entity_id,
                "dst": e.dst_entity_id,
                "type": e.relationship_type,
                "confidence": e.confidence_tier.value,
            } for e in self.edges],
            "depth": self.total_depth,
            "confidence_floor": self.confidence_floor.value,
        }


@dataclass
class RecursionConfig:
    """Configuration for recursive graph exploration."""
    max_depth: int = 3                # Maximum BFS depth
    max_nodes: int = 500              # Maximum nodes to explore
    max_cost: float = 100.0           # Cost budget (API calls, compute)
    min_confidence: ConfidenceTier = ConfidenceTier.INFERRED
    relationship_types: Optional[Set[str]] = None  # Filter by type
    as_of_date: Optional[datetime] = None  # Point-in-time query


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# IN-MEMORY GRAPH STORE
# (Production would use SQLAlchemy/PostgreSQL)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class EntityGraphStore:
    """
    In-memory graph store for development/testing.

    In production, this would be backed by:
    - PostgreSQL with entities/relationships tables
    - Optional: Neo4j for graph traversal
    - Optional: Redis for caching
    """

    def __init__(self):
        self._entities: Dict[str, EntityNode] = {}
        self._edges: Dict[str, Edge] = {}
        self._adjacency: Dict[str, List[str]] = {}  # entity_id -> edge_ids
        self._reverse_adjacency: Dict[str, List[str]] = {}  # entity_id -> incoming edge_ids
        self._identifier_index: Dict[Tuple[str, str], str] = {}  # (scheme, value) -> entity_id

    def add_entity(self, entity: EntityNode) -> EntityNode:
        """Add or update an entity in the graph."""
        self._entities[entity.id] = entity

        # Index identifiers for resolution
        for scheme, value in entity.identifiers.items():
            self._identifier_index[(scheme, value)] = entity.id

        # Initialize adjacency
        if entity.id not in self._adjacency:
            self._adjacency[entity.id] = []
        if entity.id not in self._reverse_adjacency:
            self._reverse_adjacency[entity.id] = []

        return entity

    def add_edge(self, edge: Edge) -> Edge:
        """
        Add an edge to the graph.

        Raises ValueError if:
        - relationship_type not in closed vocabulary
        - evidence_refs is empty (A5 compliance)
        """
        # A5 Compliance: Every edge MUST have evidence
        if not edge.evidence_refs:
            raise ValueError(
                f"Edge {edge.src_entity_id} -> {edge.dst_entity_id} "
                "has no evidence_refs. Every edge must cite a document (A5)."
            )

        # Closed vocabulary check
        if edge.relationship_type not in VALID_RELATIONSHIP_TYPES:
            raise ValueError(
                f"Relationship type '{edge.relationship_type}' not in closed vocabulary. "
                f"Valid types: {VALID_RELATIONSHIP_TYPES}"
            )

        self._edges[edge.id] = edge

        # Update adjacency
        if edge.src_entity_id not in self._adjacency:
            self._adjacency[edge.src_entity_id] = []
        self._adjacency[edge.src_entity_id].append(edge.id)

        if edge.dst_entity_id not in self._reverse_adjacency:
            self._reverse_adjacency[edge.dst_entity_id] = []
        self._reverse_adjacency[edge.dst_entity_id].append(edge.id)

        return edge

    def get_entity(self, entity_id: str) -> Optional[EntityNode]:
        """Get entity by ID."""
        return self._entities.get(entity_id)

    def resolve_entity(self, scheme: str, value: str) -> Optional[EntityNode]:
        """
        Resolve entity by identifier (A3 - Entity Resolution).

        Priority: deterministic ID match > fuzzy name match
        """
        entity_id = self._identifier_index.get((scheme, value))
        if entity_id:
            return self._entities.get(entity_id)
        return None

    def get_outgoing_edges(
        self,
        entity_id: str,
        config: Optional[RecursionConfig] = None,
    ) -> List[Edge]:
        """Get edges originating from an entity."""
        edge_ids = self._adjacency.get(entity_id, [])
        edges = [self._edges[eid] for eid in edge_ids if eid in self._edges]

        if config:
            edges = self._filter_edges(edges, config)

        return edges

    def get_incoming_edges(
        self,
        entity_id: str,
        config: Optional[RecursionConfig] = None,
    ) -> List[Edge]:
        """Get edges pointing to an entity."""
        edge_ids = self._reverse_adjacency.get(entity_id, [])
        edges = [self._edges[eid] for eid in edge_ids if eid in self._edges]

        if config:
            edges = self._filter_edges(edges, config)

        return edges

    def _filter_edges(
        self,
        edges: List[Edge],
        config: RecursionConfig,
    ) -> List[Edge]:
        """Filter edges based on recursion config."""
        result = []
        confidence_order = [
            ConfidenceTier.CONFIRMED,
            ConfidenceTier.REPORTED,
            ConfidenceTier.INFERRED,
            ConfidenceTier.SPECULATIVE,
        ]
        min_idx = confidence_order.index(config.min_confidence)

        for edge in edges:
            # Filter by confidence
            edge_idx = confidence_order.index(edge.confidence_tier)
            if edge_idx > min_idx:
                continue

            # Filter by relationship type
            if config.relationship_types:
                if edge.relationship_type not in config.relationship_types:
                    continue

            # Filter by point-in-time (A4)
            if config.as_of_date:
                if edge.as_of and edge.as_of > config.as_of_date:
                    continue  # Relationship didn't exist yet
                if edge.valid_to and edge.valid_to < config.as_of_date:
                    continue  # Relationship had ended

            result.append(edge)

        return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RECURSION ENGINE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class RecursionEngine:
    """
    BFS-based graph exploration with depth and cost caps.

    Implements James's "go further and further in" vision while
    maintaining computational bounds and confidence tracking.
    """

    def __init__(self, store: EntityGraphStore):
        self.store = store
        self._cost_tracker = 0.0

    def explore(
        self,
        seed_entity_id: str,
        config: RecursionConfig,
    ) -> Dict[str, Any]:
        """
        Explore the graph from a seed entity using bidirectional BFS.

        Traverses both outgoing and incoming edges to discover the full
        network around an entity.

        Returns:
            {
                "seed": EntityNode,
                "nodes": List[EntityNode],
                "edges": List[Edge],
                "depth_reached": int,
                "nodes_explored": int,
                "cost_spent": float,
            }
        """
        seed = self.store.get_entity(seed_entity_id)
        if not seed:
            return {"error": f"Seed entity {seed_entity_id} not found"}

        visited: Set[str] = {seed_entity_id}
        visited_edges: Set[str] = set()
        queue: deque = deque([(seed_entity_id, 0)])  # (entity_id, depth)
        explored_nodes: List[EntityNode] = [seed]
        explored_edges: List[Edge] = []
        max_depth_reached = 0
        self._cost_tracker = 0.0

        while queue and len(visited) < config.max_nodes:
            current_id, depth = queue.popleft()

            if depth >= config.max_depth:
                continue

            if self._cost_tracker >= config.max_cost:
                log.info("Cost budget exhausted at %.2f", self._cost_tracker)
                break

            # Get both outgoing and incoming edges (costs 2 units per lookup)
            self._cost_tracker += 2.0
            outgoing = self.store.get_outgoing_edges(current_id, config)
            incoming = self.store.get_incoming_edges(current_id, config)

            # Process outgoing edges
            for edge in outgoing:
                if edge.id not in visited_edges:
                    visited_edges.add(edge.id)
                    explored_edges.append(edge)

                if edge.dst_entity_id not in visited:
                    visited.add(edge.dst_entity_id)
                    dst_entity = self.store.get_entity(edge.dst_entity_id)
                    if dst_entity:
                        explored_nodes.append(dst_entity)
                        queue.append((edge.dst_entity_id, depth + 1))
                        max_depth_reached = max(max_depth_reached, depth + 1)

            # Process incoming edges (reverse traversal)
            for edge in incoming:
                if edge.id not in visited_edges:
                    visited_edges.add(edge.id)
                    explored_edges.append(edge)

                if edge.src_entity_id not in visited:
                    visited.add(edge.src_entity_id)
                    src_entity = self.store.get_entity(edge.src_entity_id)
                    if src_entity:
                        explored_nodes.append(src_entity)
                        queue.append((edge.src_entity_id, depth + 1))
                        max_depth_reached = max(max_depth_reached, depth + 1)

        return {
            "seed": {
                "id": seed.id,
                "name": seed.name,
                "kind": seed.kind,
            },
            "nodes": [
                {"id": n.id, "name": n.name, "kind": n.kind}
                for n in explored_nodes
            ],
            "edges": [
                {
                    "id": e.id,
                    "src": e.src_entity_id,
                    "dst": e.dst_entity_id,
                    "type": e.relationship_type,
                    "confidence": e.confidence_tier.value,
                    "evidence_count": len(e.evidence_refs),
                }
                for e in explored_edges
            ],
            "depth_reached": max_depth_reached,
            "nodes_explored": len(explored_nodes),
            "cost_spent": self._cost_tracker,
            "config": {
                "max_depth": config.max_depth,
                "max_nodes": config.max_nodes,
                "max_cost": config.max_cost,
                "min_confidence": config.min_confidence.value,
            },
        }

    def find_paths(
        self,
        src_entity_id: str,
        dst_entity_id: str,
        config: RecursionConfig,
    ) -> List[GraphPath]:
        """
        Find all paths between two entities.

        Uses bidirectional BFS to find shortest paths first.
        Traverses both outgoing and incoming edges to find connections
        through shared nodes (e.g., Thiel -> PayPal <- Chen).
        """
        src = self.store.get_entity(src_entity_id)
        dst = self.store.get_entity(dst_entity_id)

        if not src or not dst:
            return []

        paths: List[GraphPath] = []
        visited_paths: Set[str] = set()  # Track unique paths
        queue: deque = deque([(src_entity_id, [src], [], 0)])  # (id, nodes, edges, depth)

        confidence_order = [
            ConfidenceTier.CONFIRMED,
            ConfidenceTier.REPORTED,
            ConfidenceTier.INFERRED,
            ConfidenceTier.SPECULATIVE,
        ]

        def add_path(final_nodes: List[EntityNode], final_edges: List[Edge]):
            path_key = "->".join(n.id for n in final_nodes)
            if path_key in visited_paths:
                return
            visited_paths.add(path_key)

            min_conf = min(
                final_edges,
                key=lambda e: confidence_order.index(e.confidence_tier)
            ).confidence_tier

            paths.append(GraphPath(
                nodes=final_nodes,
                edges=final_edges,
                total_depth=len(final_edges),
                confidence_floor=min_conf,
            ))

        while queue:
            current_id, path_nodes, path_edges, depth = queue.popleft()

            if depth >= config.max_depth:
                continue

            visited_ids = {n.id for n in path_nodes}

            # Get all connected edges (both directions)
            outgoing = self.store.get_outgoing_edges(current_id, config)
            incoming = self.store.get_incoming_edges(current_id, config)

            # Process outgoing edges (normal direction)
            for edge in outgoing:
                next_id = edge.dst_entity_id
                if next_id == dst_entity_id:
                    add_path(path_nodes + [dst], path_edges + [edge])
                elif next_id not in visited_ids:
                    next_entity = self.store.get_entity(next_id)
                    if next_entity:
                        queue.append((
                            next_id,
                            path_nodes + [next_entity],
                            path_edges + [edge],
                            depth + 1,
                        ))

            # Process incoming edges (reverse direction)
            for edge in incoming:
                next_id = edge.src_entity_id
                if next_id == dst_entity_id:
                    add_path(path_nodes + [dst], path_edges + [edge])
                elif next_id not in visited_ids:
                    next_entity = self.store.get_entity(next_id)
                    if next_entity:
                        queue.append((
                            next_id,
                            path_nodes + [next_entity],
                            path_edges + [edge],
                            depth + 1,
                        ))

        return paths


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SERVICE SINGLETON
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_graph_store: Optional[EntityGraphStore] = None
_recursion_engine: Optional[RecursionEngine] = None


def get_graph_store() -> EntityGraphStore:
    """Get or create the global graph store."""
    global _graph_store
    if _graph_store is None:
        _graph_store = EntityGraphStore()
    return _graph_store


def get_recursion_engine() -> RecursionEngine:
    """Get or create the global recursion engine."""
    global _recursion_engine
    if _recursion_engine is None:
        _recursion_engine = RecursionEngine(get_graph_store())
    return _recursion_engine


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PUBLIC API
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def add_entity(
    entity_id: str,
    kind: str,
    name: str,
    identifiers: Optional[Dict[str, str]] = None,
    aliases: Optional[List[str]] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> EntityNode:
    """Add an entity to the graph."""
    entity = EntityNode(
        id=entity_id,
        kind=kind,
        name=name,
        identifiers=identifiers or {},
        aliases=aliases or [],
        meta=meta or {},
    )
    return get_graph_store().add_entity(entity)


def add_edge(
    edge_id: str,
    src_entity_id: str,
    dst_entity_id: str,
    relationship_type: str,
    confidence_tier: str,
    evidence_refs: List[Dict[str, Any]],
    as_of: Optional[datetime] = None,
    valid_to: Optional[datetime] = None,
    source_name: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> Edge:
    """
    Add an edge to the graph.

    Raises ValueError if evidence_refs is empty (A5 compliance).
    """
    refs = [
        EvidenceRef(
            document_id=ref.get("document_id", ""),
            source_name=ref.get("source_name", ""),
            source_url=ref.get("source_url"),
            page_start=ref.get("page_start"),
            page_end=ref.get("page_end"),
            char_start=ref.get("char_start"),
            char_end=ref.get("char_end"),
            excerpt=ref.get("excerpt"),
            retrieved_at=ref.get("retrieved_at"),
        )
        for ref in evidence_refs
    ]

    edge = Edge(
        id=edge_id,
        src_entity_id=src_entity_id,
        dst_entity_id=dst_entity_id,
        relationship_type=relationship_type,
        confidence_tier=ConfidenceTier(confidence_tier),
        evidence_refs=refs,
        as_of=as_of,
        valid_to=valid_to,
        source_name=source_name,
        meta=meta or {},
    )
    return get_graph_store().add_edge(edge)


def get_entity(entity_id: str) -> Optional[Dict[str, Any]]:
    """Get an entity by ID."""
    entity = get_graph_store().get_entity(entity_id)
    if entity:
        return {
            "id": entity.id,
            "kind": entity.kind,
            "name": entity.name,
            "identifiers": entity.identifiers,
            "aliases": entity.aliases,
        }
    return None


def explore_network(
    seed_entity_id: str,
    max_depth: int = 3,
    max_nodes: int = 500,
    min_confidence: str = "INFERRED",
    relationship_types: Optional[List[str]] = None,
    as_of_date: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Explore the network from a seed entity.

    This is the main entry point for James's "Follow the Money" use case.
    """
    config = RecursionConfig(
        max_depth=max_depth,
        max_nodes=max_nodes,
        min_confidence=ConfidenceTier(min_confidence),
        relationship_types=set(relationship_types) if relationship_types else None,
        as_of_date=as_of_date,
    )
    return get_recursion_engine().explore(seed_entity_id, config)


def find_connection(
    src_entity_id: str,
    dst_entity_id: str,
    max_depth: int = 3,
    min_confidence: str = "INFERRED",
) -> List[Dict[str, Any]]:
    """
    Find paths connecting two entities.

    Returns all paths up to max_depth.
    """
    config = RecursionConfig(
        max_depth=max_depth,
        min_confidence=ConfidenceTier(min_confidence),
    )
    paths = get_recursion_engine().find_paths(src_entity_id, dst_entity_id, config)
    return [p.to_dict() for p in paths]


def resolve_entity(scheme: str, value: str) -> Optional[Dict[str, Any]]:
    """
    Resolve an entity by identifier.

    Example: resolve_entity("CIK", "0001067983") -> Peter Thiel's entity
    """
    entity = get_graph_store().resolve_entity(scheme, value)
    if entity:
        return {
            "id": entity.id,
            "kind": entity.kind,
            "name": entity.name,
            "identifiers": entity.identifiers,
            "aliases": entity.aliases,
        }
    return None


def get_graph_stats() -> Dict[str, Any]:
    """Get statistics about the graph."""
    store = get_graph_store()
    return {
        "total_entities": len(store._entities),
        "total_edges": len(store._edges),
        "indexed_identifiers": len(store._identifier_index),
    }
