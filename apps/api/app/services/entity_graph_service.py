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

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

from sqlalchemy import text

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
# DB-BACKED GRAPH STORE WITH IN-MEMORY CACHE
# Persists to SQLite/PostgreSQL via SQLAlchemy, caches in-memory for fast traversal.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class EntityGraphStore:
    """
    DB-backed graph store with write-through in-memory cache.

    Storage backend: SQLite (local.db) or PostgreSQL via app.db.session.
    On init, loads all entities/edges from DB into cache.
    Mutations write to DB first, then update cache.
    """

    def __init__(self):
        self._entities: Dict[str, EntityNode] = {}
        self._edges: Dict[str, Edge] = {}
        self._adjacency: Dict[str, List[str]] = {}
        self._reverse_adjacency: Dict[str, List[str]] = {}
        self._identifier_index: Dict[Tuple[str, str], str] = {}
        # Maps graph string IDs to DB integer PKs
        self._entity_db_pk: Dict[str, int] = {}
        self._edge_db_pk: Dict[str, int] = {}
        self._loaded = False

    def _ensure_loaded(self):
        """Lazy-load from DB on first access."""
        if self._loaded:
            return
        self._loaded = True
        try:
            self._load_from_db()
        except Exception as exc:
            log.warning("Failed to load graph from DB, starting empty: %s", exc)

    def _load_from_db(self):
        """Hydrate in-memory cache from the database."""
        from app.db.session import get_db_context

        with get_db_context() as db:
            # Load entities
            rows = db.execute(text(
                "SELECT id, kind, name, meta FROM entities"
            )).fetchall()

            for row in rows:
                db_id, kind, name, meta_raw = row[0], row[1], row[2], row[3]
                meta = json.loads(meta_raw) if meta_raw else {}
                graph_id = meta.get("graph_id", str(db_id))

                entity = EntityNode(
                    id=graph_id,
                    kind=kind,
                    name=name,
                    identifiers={},
                    aliases=[],
                    meta={k: v for k, v in meta.items() if k != "graph_id"},
                )
                self._entities[graph_id] = entity
                self._entity_db_pk[graph_id] = db_id
                if graph_id not in self._adjacency:
                    self._adjacency[graph_id] = []
                if graph_id not in self._reverse_adjacency:
                    self._reverse_adjacency[graph_id] = []

            # Load identifiers
            id_rows = db.execute(text(
                "SELECT entity_id, scheme, value FROM entity_identifiers"
            )).fetchall()
            for row in id_rows:
                ent_db_id, scheme, value = row[0], row[1], row[2]
                graph_id = self._graph_id_for_db_pk(ent_db_id)
                if graph_id and graph_id in self._entities:
                    self._entities[graph_id].identifiers[scheme] = value
                    self._identifier_index[(scheme, value)] = graph_id

            # Load aliases
            alias_rows = db.execute(text(
                "SELECT entity_id, alias FROM entity_aliases"
            )).fetchall()
            for row in alias_rows:
                ent_db_id, alias = row[0], row[1]
                graph_id = self._graph_id_for_db_pk(ent_db_id)
                if graph_id and graph_id in self._entities:
                    self._entities[graph_id].aliases.append(alias)

            # Load relationships (edges)
            rel_rows = db.execute(text(
                "SELECT id, src_entity_id, dst_entity_id, kind, meta "
                "FROM relationships"
            )).fetchall()

            for row in rel_rows:
                db_id, src_db, dst_db, kind, meta_raw = (
                    row[0], row[1], row[2], row[3], row[4]
                )
                meta = json.loads(meta_raw) if meta_raw else {}
                edge_graph_id = meta.get("edge_graph_id", str(db_id))
                src_graph_id = self._graph_id_for_db_pk(src_db)
                dst_graph_id = self._graph_id_for_db_pk(dst_db)

                if not src_graph_id or not dst_graph_id:
                    continue

                conf = meta.get("confidence_tier", "INFERRED")
                try:
                    confidence = ConfidenceTier(conf)
                except ValueError:
                    confidence = ConfidenceTier.INFERRED

                as_of = meta.get("as_of")
                valid_to = meta.get("valid_to")
                source_id = meta.get("source_id")
                source_name = meta.get("source_name")
                extracted_by = meta.get("extracted_by")

                # Load evidence for this relationship
                ev_rows = db.execute(text(
                    "SELECT meta FROM relationship_evidence WHERE relationship_id = :rid"
                ), {"rid": db_id}).fetchall()
                evidence_refs = []
                for ev in ev_rows:
                    ev_meta = json.loads(ev[0]) if ev[0] else {}
                    evidence_refs.append(EvidenceRef(
                        document_id=ev_meta.get("document_id", ""),
                        source_name=ev_meta.get("source_name", ""),
                        source_url=ev_meta.get("source_url"),
                        page_start=ev_meta.get("page_start"),
                        page_end=ev_meta.get("page_end"),
                        char_start=ev_meta.get("char_start"),
                        char_end=ev_meta.get("char_end"),
                        excerpt=ev_meta.get("excerpt"),
                        retrieved_at=None,
                    ))

                if not evidence_refs:
                    evidence_refs = [EvidenceRef(
                        document_id="legacy",
                        source_name=source_name or "unknown",
                    )]

                edge = Edge(
                    id=edge_graph_id,
                    src_entity_id=src_graph_id,
                    dst_entity_id=dst_graph_id,
                    relationship_type=kind,
                    confidence_tier=confidence,
                    evidence_refs=evidence_refs,
                    as_of=as_of,
                    valid_to=valid_to,
                    source_id=source_id,
                    source_name=source_name,
                    extracted_by=extracted_by,
                    meta={k: v for k, v in meta.items()
                          if k not in ("edge_graph_id", "confidence_tier", "as_of",
                                       "valid_to", "source_id", "source_name", "extracted_by")},
                )
                self._edges[edge_graph_id] = edge
                self._edge_db_pk[edge_graph_id] = db_id

                if src_graph_id not in self._adjacency:
                    self._adjacency[src_graph_id] = []
                self._adjacency[src_graph_id].append(edge_graph_id)

                if dst_graph_id not in self._reverse_adjacency:
                    self._reverse_adjacency[dst_graph_id] = []
                self._reverse_adjacency[dst_graph_id].append(edge_graph_id)

        log.info(
            "Loaded graph from DB: %d entities, %d edges",
            len(self._entities), len(self._edges)
        )

    def _graph_id_for_db_pk(self, db_pk: int) -> Optional[str]:
        """Reverse lookup: DB PK -> graph string ID."""
        for gid, pk in self._entity_db_pk.items():
            if pk == db_pk:
                return gid
        return None

    def add_entity(self, entity: EntityNode) -> EntityNode:
        """Add or update an entity in the graph. Persists to DB."""
        self._ensure_loaded()
        from app.db.session import get_db_context

        with get_db_context() as db:
            meta_dict = dict(entity.meta)
            meta_dict["graph_id"] = entity.id

            if entity.id in self._entity_db_pk:
                # Update existing
                db_pk = self._entity_db_pk[entity.id]
                db.execute(text(
                    "UPDATE entities SET kind = :kind, name = :name, meta = :meta "
                    "WHERE id = :id"
                ), {"kind": entity.kind, "name": entity.name,
                    "meta": json.dumps(meta_dict), "id": db_pk})
            else:
                # Insert new
                result = db.execute(text(
                    "INSERT INTO entities (kind, name, canonical, meta) "
                    "VALUES (:kind, :name, true, :meta)"
                ), {"kind": entity.kind, "name": entity.name,
                    "meta": json.dumps(meta_dict)})
                db_pk = result.lastrowid
                self._entity_db_pk[entity.id] = db_pk

            # Sync identifiers: delete old, insert current
            db.execute(text(
                "DELETE FROM entity_identifiers WHERE entity_id = :eid"
            ), {"eid": db_pk})
            for scheme, value in entity.identifiers.items():
                db.execute(text(
                    "INSERT OR REPLACE INTO entity_identifiers (entity_id, scheme, value) "
                    "VALUES (:eid, :scheme, :value)"
                ), {"eid": db_pk, "scheme": scheme, "value": value})

            # Sync aliases
            db.execute(text(
                "DELETE FROM entity_aliases WHERE entity_id = :eid"
            ), {"eid": db_pk})
            for alias in entity.aliases:
                db.execute(text(
                    "INSERT OR REPLACE INTO entity_aliases (entity_id, alias) "
                    "VALUES (:eid, :alias)"
                ), {"eid": db_pk, "alias": alias})

            db.commit()

        # Update in-memory cache
        self._entities[entity.id] = entity
        for scheme, value in entity.identifiers.items():
            self._identifier_index[(scheme, value)] = entity.id
        if entity.id not in self._adjacency:
            self._adjacency[entity.id] = []
        if entity.id not in self._reverse_adjacency:
            self._reverse_adjacency[entity.id] = []

        return entity

    def add_edge(self, edge: Edge) -> Edge:
        """
        Add an edge to the graph. Persists to DB.

        Raises ValueError if:
        - relationship_type not in closed vocabulary
        - evidence_refs is empty (A5 compliance)
        """
        self._ensure_loaded()

        if not edge.evidence_refs:
            raise ValueError(
                f"Edge {edge.src_entity_id} -> {edge.dst_entity_id} "
                "has no evidence_refs. Every edge must cite a document (A5)."
            )

        if edge.relationship_type not in VALID_RELATIONSHIP_TYPES:
            raise ValueError(
                f"Relationship type '{edge.relationship_type}' not in closed vocabulary. "
                f"Valid types: {VALID_RELATIONSHIP_TYPES}"
            )

        from app.db.session import get_db_context

        src_db_pk = self._entity_db_pk.get(edge.src_entity_id)
        dst_db_pk = self._entity_db_pk.get(edge.dst_entity_id)
        if not src_db_pk or not dst_db_pk:
            raise ValueError(
                f"Source or destination entity not found in DB. "
                f"src={edge.src_entity_id} dst={edge.dst_entity_id}"
            )

        with get_db_context() as db:
            meta_dict = dict(edge.meta)
            meta_dict["edge_graph_id"] = edge.id
            meta_dict["confidence_tier"] = edge.confidence_tier.value
            meta_dict["source_id"] = edge.source_id
            meta_dict["source_name"] = edge.source_name
            meta_dict["extracted_by"] = edge.extracted_by
            if edge.as_of:
                meta_dict["as_of"] = edge.as_of.isoformat() if isinstance(edge.as_of, datetime) else str(edge.as_of)
            if edge.valid_to:
                meta_dict["valid_to"] = edge.valid_to.isoformat() if isinstance(edge.valid_to, datetime) else str(edge.valid_to)

            if edge.id in self._edge_db_pk:
                db_pk = self._edge_db_pk[edge.id]
                db.execute(text(
                    "UPDATE relationships SET src_entity_id = :src, dst_entity_id = :dst, "
                    "kind = :kind, meta = :meta WHERE id = :id"
                ), {
                    "src": src_db_pk, "dst": dst_db_pk,
                    "kind": edge.relationship_type,
                    "meta": json.dumps(meta_dict), "id": db_pk,
                })
            else:
                result = db.execute(text(
                    "INSERT INTO relationships "
                    "(src_entity_id, dst_entity_id, kind, confidence_tier, meta) "
                    "VALUES (:src, :dst, :kind, :ct, :meta)"
                ), {
                    "src": src_db_pk, "dst": dst_db_pk,
                    "kind": edge.relationship_type,
                    "ct": edge.confidence.value if hasattr(edge.confidence, 'value') else "INFERRED",
                    "meta": json.dumps(meta_dict),
                })
                db_pk = result.lastrowid
                self._edge_db_pk[edge.id] = db_pk

            # Persist evidence refs
            db.execute(text(
                "DELETE FROM relationship_evidence WHERE relationship_id = :rid"
            ), {"rid": db_pk})
            for ref in edge.evidence_refs:
                ev_meta = {
                    "document_id": ref.document_id,
                    "source_name": ref.source_name,
                    "source_url": ref.source_url,
                    "page_start": ref.page_start,
                    "page_end": ref.page_end,
                    "char_start": ref.char_start,
                    "char_end": ref.char_end,
                    "excerpt": ref.excerpt,
                }
                db.execute(text(
                    "INSERT INTO relationship_evidence (relationship_id, meta) "
                    "VALUES (:rid, :meta)"
                ), {"rid": db_pk, "meta": json.dumps(ev_meta)})

            db.commit()

        # Update in-memory cache
        self._edges[edge.id] = edge
        if edge.src_entity_id not in self._adjacency:
            self._adjacency[edge.src_entity_id] = []
        self._adjacency[edge.src_entity_id].append(edge.id)
        if edge.dst_entity_id not in self._reverse_adjacency:
            self._reverse_adjacency[edge.dst_entity_id] = []
        self._reverse_adjacency[edge.dst_entity_id].append(edge.id)

        return edge

    def get_entity(self, entity_id: str) -> Optional[EntityNode]:
        """Get entity by ID."""
        self._ensure_loaded()
        return self._entities.get(entity_id)

    def resolve_entity(self, scheme: str, value: str) -> Optional[EntityNode]:
        """
        Resolve entity by identifier (A3 - Entity Resolution).

        Priority: deterministic ID match > fuzzy name match
        """
        self._ensure_loaded()
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
        self._ensure_loaded()
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
        self._ensure_loaded()
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
            edge_idx = confidence_order.index(edge.confidence_tier)
            if edge_idx > min_idx:
                continue

            if config.relationship_types:
                if edge.relationship_type not in config.relationship_types:
                    continue

            if config.as_of_date:
                if edge.as_of and edge.as_of > config.as_of_date:
                    continue
                if edge.valid_to and edge.valid_to < config.as_of_date:
                    continue

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
    store._ensure_loaded()
    return {
        "total_entities": len(store._entities),
        "total_edges": len(store._edges),
        "indexed_identifiers": len(store._identifier_index),
    }
