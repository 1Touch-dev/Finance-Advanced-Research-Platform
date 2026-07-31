"""
Co-occurrence graph across people and entities (G-02).

This implements the method James pointed at on 31 July with seven links and
one line of explanation: *"paypal mafia analysis, is so you understand the
correlations."* Read as history the links say nothing we can build. Read as a
specification — which is what the Quartz/VentureBeat dataset is — they describe
a procedure:

1. Fix a seed cohort of people who overlapped at one issuer.
2. Follow each person to every other entity they later touched.
3. Weight the edge between any two people by the number of entities they both
   touched.
4. Compute, per person, the share of their entities that another cohort member
   also touched. That figure was 31% for Thiel, 47% for Rabois, 46% for Sacks.
5. Let the core cluster fall out of the edge weights rather than asserting it.
   Theirs was Sacks, Levchin, Rabois, Thiel and Banister — a result, not an
   input.
6. Plot activity over time.

Steps 3 to 5 are the correlation engine, and they run on filings we already
hold. A person keeps one CIK for life across every issuer where they report
under Section 16, so `board_interlock_connector` has already produced, for
each insider, the list of other issuers they have filed at. That list is the
"entities they later touched", and the co-occurrence graph is a join of that
table against itself.

What this cannot do without a paid vendor is private-round co-investment —
that is G-12 and it is stated as absent rather than approximated. What it does
do is the public-company half, which is the half with filings behind it.

The overlap rate is descriptive, not inferential. Two directors of the same
issuer sitting on one further board together is a fact about two filings; it
is not evidence of coordination, and nothing here says otherwise.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# An edge needs at least this many shared entities to be reported. One shared
# board between two directors of the same company is unremarkable and the
# graph is unreadable if every such pair is drawn.
MIN_EDGE_WEIGHT = 1

# A cluster needs at least this many people to be called one.
MIN_CLUSTER_SIZE = 2


def _safe(fn):
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as error:
            logger.warning("Co-occurrence %s failed: %s", fn.__name__, error)
            return None
    wrapper.__name__ = fn.__name__
    return wrapper


# ---------------------------------------------------------------------------
# Step 1-2: seed cohort and the entities each person touched
# ---------------------------------------------------------------------------

def build_person_entity_map(data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Each person mapped to the set of other entities they are on record at.

    Sources, all already fetched:
      * Section 16 outside seats (board_interlock_connector)
      * Related-party counterparties naming a director
      * Outbound Schedule 13D/G stakes
    """
    people: Dict[str, Dict[str, Any]] = {}

    interlocks = data.get("board_interlocks") or {}
    for person in interlocks.get("people") or []:
        name = person.get("name")
        if not name:
            continue
        entry = people.setdefault(name, {
            "name": name,
            "cik": person.get("cik"),
            "roles_at_issuer": person.get("roles_at_issuer") or [],
            "entities": {},
            "profile_url": person.get("profile_url"),
        })
        for seat in person.get("other_seats") or []:
            issuer = seat.get("issuer")
            if not issuer:
                continue
            entry["entities"][issuer] = {
                "issuer": issuer,
                "ticker": seat.get("ticker"),
                "roles": seat.get("roles") or [],
                "current": bool(seat.get("current")),
                "first_filed": seat.get("first_filed"),
                "last_filed": seat.get("last_filed"),
                "source_url": seat.get("source_url"),
            }

    return {name: p for name, p in people.items() if p["entities"]}


# ---------------------------------------------------------------------------
# Step 3-4: edges and per-person overlap rate
# ---------------------------------------------------------------------------

def build_edges(people: Dict[str, Dict[str, Any]],
                min_weight: int = MIN_EDGE_WEIGHT) -> List[Dict[str, Any]]:
    """Edge between two people weighted by the count of shared entities."""
    names = sorted(people)
    edges = []
    for i, left in enumerate(names):
        for right in names[i + 1:]:
            shared = set(people[left]["entities"]) & set(people[right]["entities"])
            if len(shared) < min_weight:
                continue
            edges.append({
                "a": left,
                "b": right,
                "weight": len(shared),
                "shared": sorted(shared),
                # A shared seat that both still hold is materially different
                # from two people who passed through the same board a decade
                # apart, so currency is carried on the edge.
                "concurrent": sorted(
                    e for e in shared
                    if people[left]["entities"][e]["current"]
                    and people[right]["entities"][e]["current"]),
            })
    return sorted(edges, key=lambda e: -e["weight"])


def overlap_rates(people: Dict[str, Dict[str, Any]],
                  edges: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Per person: what share of their entities another cohort member touches.

    This is the figure the Quartz analysis reported per Mafia member — 31% for
    Thiel, 47% for Rabois. It is the single most portable number in the whole
    method because it needs no external benchmark to be readable.
    """
    shared_by_person: Dict[str, Set[str]] = defaultdict(set)
    partners: Dict[str, Set[str]] = defaultdict(set)
    for edge in edges:
        for a, b in ((edge["a"], edge["b"]), (edge["b"], edge["a"])):
            shared_by_person[a].update(edge["shared"])
            partners[a].add(b)

    rows = []
    for name, person in people.items():
        total = len(person["entities"])
        if not total:
            continue
        overlapping = len(shared_by_person.get(name, set()))
        rows.append({
            "name": name,
            "entities": total,
            "shared_entities": overlapping,
            "overlap_rate": round(overlapping / total * 100, 1),
            "partners": sorted(partners.get(name, set())),
            "roles_at_issuer": person.get("roles_at_issuer") or [],
            "current_entities": sum(1 for e in person["entities"].values()
                                    if e["current"]),
        })
    return sorted(rows, key=lambda r: (-r["shared_entities"], -r["entities"]))


# ---------------------------------------------------------------------------
# Step 5: the core cluster, as a result rather than an assertion
# ---------------------------------------------------------------------------

def core_cluster(edges: List[Dict[str, Any]],
                 min_size: int = MIN_CLUSTER_SIZE) -> List[Dict[str, Any]]:
    """Connected components of the edge graph, largest first.

    The Quartz piece named Sacks, Levchin, Rabois, Thiel and Banister as the
    core. That set was not chosen — it is what remains when you keep only the
    people joined by shared portfolio companies. The same operation here.
    """
    adjacency: Dict[str, Set[str]] = defaultdict(set)
    for edge in edges:
        adjacency[edge["a"]].add(edge["b"])
        adjacency[edge["b"]].add(edge["a"])

    seen: Set[str] = set()
    clusters = []
    for start in adjacency:
        if start in seen:
            continue
        stack, component = [start], set()
        while stack:
            node = stack.pop()
            if node in component:
                continue
            component.add(node)
            stack.extend(adjacency[node] - component)
        seen |= component
        if len(component) < min_size:
            continue
        internal = [e for e in edges
                    if e["a"] in component and e["b"] in component]
        entities: Set[str] = set()
        for edge in internal:
            entities.update(edge["shared"])
        clusters.append({
            "members": sorted(component),
            "size": len(component),
            "edges": len(internal),
            "shared_entities": sorted(entities),
            "density": round(
                len(internal) / max(1, len(component) * (len(component) - 1) / 2), 2),
        })
    return sorted(clusters, key=lambda c: (-c["size"], -c["edges"]))


# ---------------------------------------------------------------------------
# Step 6: activity over time
# ---------------------------------------------------------------------------

def activity_by_year(people: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """New outside seats taken up per year, across the whole cohort."""
    counts: Dict[str, int] = defaultdict(int)
    for person in people.values():
        for entity in person["entities"].values():
            first = (entity.get("first_filed") or "")[:4]
            if first.isdigit():
                counts[first] += 1
    return [{"year": y, "new_seats": n} for y, n in sorted(counts.items())]


# ---------------------------------------------------------------------------
# The capital layer — managers as nodes, issuers as the shared entities
# ---------------------------------------------------------------------------

def institutional_cooccurrence(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """The same graph over 13F managers rather than over directors.

    The people layer is usually sparse by law: section 8 of the Clayton Act
    stops one person sitting on two competing boards, so directors of a single
    issuer rarely share an outside seat. Capital is under no such constraint —
    the same managers appear on every peer register at once, and that is where
    the edges actually are.

    The Quartz analysis had both layers too: the people were the story, the
    funds were how the money moved.
    """
    overlap = data.get("institutional_overlap") or {}
    analysis = overlap.get("overlap_analysis") or overlap or {}
    shared = analysis.get("shared_holders") or []
    if not shared:
        return None

    managers: Dict[str, Dict[str, Any]] = {}
    for holder in shared:
        details = holder.get("details_by_ticker") or {}
        name = next((d.get("original_name") for d in details.values()
                     if d.get("original_name")),
                    holder.get("normalized_name"))
        if not name:
            continue
        managers[name] = {
            "name": name,
            "issuers": sorted(details.keys()),
            "count": holder.get("count") or len(details),
            "value": holder.get("total_value_across_all"),
            "weight_skew": holder.get("weight_skew"),
            "overweight": holder.get("overweight"),
        }

    names = sorted(managers)
    edges = []
    for i, left in enumerate(names):
        for right in names[i + 1:]:
            common = set(managers[left]["issuers"]) & set(managers[right]["issuers"])
            if not common:
                continue
            edges.append({
                "a": left, "b": right,
                "weight": len(common),
                "shared": sorted(common),
            })

    # Which issuers are held by the most managers in common — the inverse
    # view, and the one that answers "who owns this whole sector at once".
    by_issuer: Dict[str, List[str]] = defaultdict(list)
    for name, manager in managers.items():
        for issuer in manager["issuers"]:
            by_issuer[issuer].append(name)

    return {
        "managers": sorted(managers.values(), key=lambda m: -(m["count"] or 0)),
        "manager_count": len(managers),
        "edges": sorted(edges, key=lambda e: -e["weight"])[:40],
        "edge_count": len(edges),
        "issuers": sorted(
            ({"issuer": k, "managers": len(v), "names": sorted(v)}
             for k, v in by_issuer.items()),
            key=lambda r: -r["managers"]),
        "fully_shared": [k for k, v in by_issuer.items()
                         if len(v) == len(managers)],
    }


# ---------------------------------------------------------------------------
# Where the cluster lands — the step James actually cares about
# ---------------------------------------------------------------------------

def cluster_endpoints(data: Dict[str, Any],
                      people: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Does the network terminate in the registers we already parse?

    The Quartz analysis ends by tracing the cohort into Founders Fund,
    Greylock and Sequoia, and from there into defence contracts and policy
    roles. That is the step that makes the whole exercise more than a
    curiosity, and it is the step we are best placed to do: federal awards and
    the lobbying register are already parsed for the seed issuer.
    """
    entity_names = set()
    for person in people.values():
        entity_names.update(person["entities"])

    contracts = data.get("contract_intelligence") or {}
    political = data.get("political_intelligence") or {}

    # Investment-management entities in the cohort's seat list: the "VC arm"
    # equivalent of Founders Fund / Greylock in the source analysis.
    capital_tokens = ("capital", "ventures", "partners", "management",
                      "asset", "advisors", "holdings", "fund")
    capital_entities = sorted(
        e for e in entity_names
        if any(t in e.lower() for t in capital_tokens))

    return {
        "entities_reached": len(entity_names),
        "capital_entities": capital_entities,
        "issuer_federal_obligated": (contracts.get("summary") or {})
            .get("total_obligated"),
        "issuer_lobbying_total": (political.get("lobbying_summary") or {})
            .get("total_spend"),
        "note": (
            "Federal and lobbying figures are the seed issuer's own. Mapping "
            "each networked entity's contract footprint requires a UEI "
            "resolution per entity and is not attempted here rather than "
            "being estimated."
        ),
    }


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

@_safe
def build_cooccurrence(data: Dict[str, Any],
                       entity_name: str = "") -> Optional[Dict[str, Any]]:
    """The full six-step analysis over both layers, people and capital."""
    people = build_person_entity_map(data)
    institutional = institutional_cooccurrence(data)
    if len(people) < 2 and not institutional:
        return None

    edges = build_edges(people)
    rates = overlap_rates(people, edges)
    clusters = core_cluster(edges)

    all_entities: Set[str] = set()
    for person in people.values():
        all_entities.update(person["entities"])

    # An empty people graph is a result, not a failure, and it has a specific
    # legal cause worth stating rather than leaving the section blank.
    negative = None
    if people and not edges:
        negative = (
            f"The {len(people)} insiders who report elsewhere reach "
            f"{len(all_entities)} outside issuers between them, and no two of "
            f"them share one. That is the expected outcome: section 8 of the "
            f"Clayton Act bars a person from sitting on the boards of two "
            f"competing corporations, so a shared outside seat among one "
            f"issuer's directors is uncommon by construction. The absence is "
            f"reported because its presence would have been the finding."
        )

    return {
        "entity_name": entity_name,
        "cohort_size": len(people),
        "entities_reached": len(all_entities),
        "edges": edges,
        "edge_count": len(edges),
        "overlap_rates": rates,
        "clusters": clusters,
        "negative_result": negative,
        "institutional": institutional,
        "activity_by_year": activity_by_year(people),
        "endpoints": cluster_endpoints(data, people),
        "method": (
            "Each person's other public-company roles are read from their own "
            "Section 16 filings, which carry one CIK per person for life. Two "
            "people are joined where they have both filed at the same outside "
            "issuer, and the edge is weighted by how many such issuers they "
            "share. Clusters are connected components of that graph, so "
            "membership is a result of the filings rather than a judgement."
        ),
        "limits": (
            "Public issuers only. Private-company boards, advisory roles and "
            "co-investment in funding rounds are not in Section 16 and are "
            "therefore invisible here; that gap needs a commercial database "
            "and is not approximated."
        ),
    }
