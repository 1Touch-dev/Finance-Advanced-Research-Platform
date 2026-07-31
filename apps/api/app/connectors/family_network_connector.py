"""
Family, trust and vehicle networks (G-04).

James's correction, 31 July: *"family members might not be on payroll. They
might be other shareholders or investors, with other companies or financial
investment vehicles. They might be advisors, or similar. Analyze what
positions family vs other members have."*

The existing Item 404 parser finds a relative only when the proxy puts them on
the payroll. That is the least interesting position and the easiest one to
avoid. The positions that carry weight are held through a vehicle: a trust, a
family limited partnership, an LLC or a foundation. Those are visible for free
and we were not reading them.

Three sources, none of them paid:

* **Section 16 reporting owners.** A Form 3/4 is filed by whoever holds the
  security, and that is frequently not a natural person. "Huang Jen-Hsun 2016
  Trust" files in its own right, under its own CIK, against the same issuer.
  The vehicle is already in data we fetch — we were treating its name as a
  person's and printing it as one.
* **Proxy beneficial ownership.** The 5% table and the director/officer table
  list vehicles alongside people.
* **IRS Form 990** via ProPublica's Nonprofit Explorer, which is free and
  unauthenticated. A private foundation files the names of its trustees, and a
  family foundation names the family.

Surname matching is the join. It is a weak signal on its own, which is why a
match is reported as *"shares a surname with"* and never as *"is the spouse
of"*. The filing establishes the vehicle; the surname suggests the link; the
report states exactly that much and no more.
"""

from __future__ import annotations

import logging
import os
import re
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set

import requests

logger = logging.getLogger(__name__)

_TIMEOUT = 20
_UA = os.getenv(
    "SEC_USER_AGENT",
    "Finance Research Platform research@example.com")

PROPUBLICA_SEARCH = "https://projects.propublica.org/nonprofits/api/v2/search.json"
PROPUBLICA_ORG = "https://projects.propublica.org/nonprofits/api/v2/organizations/{ein}.json"

# Tokens that mark a filer as a legal vehicle rather than a natural person.
# Ordered longest-first at use so "family limited partnership" wins over "lp".
_VEHICLE_KINDS = {
    "trust": ("trust", "revocable trust", "irrevocable trust", "living trust",
              "grat", "annuity trust", "remainder trust"),
    "foundation": ("foundation", "charitable", "endowment"),
    "partnership": ("family limited partnership", "limited partnership",
                    " lp", " l.p.", "partners", "partnership"),
    "llc": (" llc", " l.l.c.", "limited liability"),
    "fund": ("fund", "capital", "ventures", "management", "holdings",
             "investments", "advisors", "asset"),
    "corporation": (" inc", " inc.", " corp", " corporation", " co.", " plc"),
}

# Suffixes and honorifics stripped before a surname is taken.
_NAME_NOISE = re.compile(
    r"\b(jr|sr|ii|iii|iv|v|md|phd|mba|esq|mr|mrs|ms|dr)\b\.?",
    re.IGNORECASE)

# Vehicles that are plainly institutions rather than anyone's family office.
# BlackRock filing a 13G is not a Huang family trust, and a section headed
# "family vehicles" that lists BlackRock is worse than one that lists nothing.
_INSTITUTIONS = (
    "blackrock", "vanguard", "state street", "fidelity", "fmr ",
    "geode", "t. rowe", "t rowe", "capital research", "capital world",
    "wellington", "northern trust", "bank of new york", "bny mellon",
    "jpmorgan", "j.p. morgan", "morgan stanley", "goldman sachs",
    "ubs ", "credit suisse", "deutsche bank", "invesco", "schwab",
    "amundi", "legal & general", "nomura", "mizuho", "sumitomo",
    "franklin resources", "dimensional fund", "aqr ", "citadel",
    "renaissance techn", "two sigma", "millennium", "point72",
    "berkshire hathaway", "soros fund", "bridgewater",
)


def is_institution(name: str) -> bool:
    lowered = f" {(name or '').lower()} "
    return any(token in lowered for token in _INSTITUTIONS)


def _http_get(url: str, params: Optional[dict] = None) -> Optional[dict]:
    try:
        response = requests.get(url, params=params, timeout=_TIMEOUT,
                                headers={"User-Agent": _UA})
        if response.status_code == 200:
            return response.json()
        logger.debug("GET %s returned %s", url, response.status_code)
    except Exception as error:
        logger.debug("GET %s failed: %s", url, error)
    return None


# ---------------------------------------------------------------------------
# Name handling
# ---------------------------------------------------------------------------

def classify_holder(name: str) -> Optional[str]:
    """Vehicle kind for a holder name, or None where it reads as a person."""
    if not name:
        return None
    lowered = f" {name.lower().strip()} "
    for kind, tokens in _VEHICLE_KINDS.items():
        for token in tokens:
            if token in lowered:
                return kind
    return None


def surname_of(name: str, edgar_order: Optional[bool] = None) -> str:
    """Best-effort surname from either 'SMITH JOHN A' or 'John A. Smith'.

    EDGAR stores every Section 16 name surname-first; a proxy writes them the
    way a person would. Callers that know which convention they hold should
    say so via `edgar_order`, because the guess is genuinely ambiguous for a
    two-token name — "Ochoa Ellen" and "Ellen Ochoa" are the same person and
    only the source tells them apart.
    """
    raw = name or ""
    if "," in raw:                      # "Smith, John A."
        return surname_of(raw.split(",")[0], edgar_order=False)

    cleaned = _NAME_NOISE.sub("", raw)
    cleaned = re.sub(r"[^A-Za-z\s'\-]", " ", cleaned)
    tokens = cleaned.split()
    if not tokens:
        return ""

    if edgar_order is None:
        edgar_order = (
            raw.isupper()                                # EDGAR upper-cases
            or (len(tokens) >= 3 and len(tokens[-1]) == 1)   # trailing initial
        )
    parts = [t for t in tokens if len(t) > 1]
    if not parts:
        return ""
    return (parts[0] if edgar_order else parts[-1]).lower()


def _surnames_in(text: str) -> Set[str]:
    return {w.lower() for w in re.findall(r"[A-Z][a-z]{2,}|[A-Z]{3,}", text or "")}


# ---------------------------------------------------------------------------
# Vehicles from filings we already hold
# ---------------------------------------------------------------------------

def vehicles_from_insiders(insider: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Section 16 filers that are legal vehicles rather than natural persons."""
    seen: Dict[str, Dict[str, Any]] = {}
    for row in (insider or {}).get("transactions") or []:
        name = (row.get("insider") or "").strip()
        kind = classify_holder(name)
        if not kind:
            continue
        entry = seen.setdefault(name.lower(), {
            "name": name,
            "kind": kind,
            "cik": row.get("insider_cik") or "",
            "roles": set(),
            "transactions": 0,
            "value": 0.0,
            "first_seen": row.get("date"),
            "last_seen": row.get("date"),
            "source_url": row.get("source_url"),
        })
        entry["transactions"] += 1
        entry["value"] += float(row.get("value") or 0)
        for role in row.get("roles") or []:
            entry["roles"].add(role)
        date = row.get("date")
        if date:
            entry["first_seen"] = min(entry["first_seen"] or date, date)
            entry["last_seen"] = max(entry["last_seen"] or date, date)

    out = []
    for entry in seen.values():
        entry["roles"] = sorted(entry["roles"])
        out.append(entry)
    return sorted(out, key=lambda e: -e["value"])


def vehicles_from_proxy(proxy: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Holders in the proxy ownership table that are vehicles."""
    out = []
    for row in (proxy or {}).get("beneficial_ownership") or []:
        name = (row.get("owner") or "").strip()
        kind = classify_holder(name)
        if not kind:
            continue
        out.append({
            "name": name,
            "kind": kind,
            "shares": row.get("shares"),
            "percent": row.get("percent"),
        })
    return out


def _insider_people(insider: Dict[str, Any],
                    proxy: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Natural persons attached to the issuer, indexed by surname."""
    people: Dict[str, Dict[str, Any]] = {}

    for row in (insider or {}).get("transactions") or []:
        name = (row.get("insider") or "").strip()
        if not name or classify_holder(name):
            continue
        # Form 4 reporting-owner names are always surname-first.
        key = surname_of(name, edgar_order=True)
        if not key:
            continue
        entry = people.setdefault(key, {"names": set(), "roles": set(),
                                        "source": "Section 16"})
        entry["names"].add(name)
        for role in row.get("roles") or []:
            entry["roles"].add(role)

    board = (proxy or {}).get("board_composition") or {}
    for director in board.get("directors") or []:
        name = (director.get("name") or "").strip()
        if not name:
            continue
        # A proxy prints names the way the person writes them.
        key = surname_of(name, edgar_order=False)
        if not key:
            continue
        entry = people.setdefault(key, {"names": set(), "roles": set(),
                                        "source": "DEF 14A"})
        entry["names"].add(name)
        entry["roles"].add("Director")

    return people


# ---------------------------------------------------------------------------
# Foundations — IRS Form 990 via ProPublica
# ---------------------------------------------------------------------------

def foundations_for(surnames: List[str], entity_name: str = "",
                    limit_per_name: int = 3) -> List[Dict[str, Any]]:
    """Private foundations whose name carries an insider's surname.

    A family foundation is a disclosure surface most readers never check: the
    990 is public, names its trustees, and states the assets under their
    control. ProPublica's index is free and needs no key.
    """
    found: List[Dict[str, Any]] = []
    seen_eins: Set[str] = set()

    queries = [f"{s} foundation" for s in surnames[:8] if len(s) > 3]
    if entity_name:
        queries.insert(0, f"{entity_name.split()[0]} foundation")

    for query in queries:
        payload = _http_get(PROPUBLICA_SEARCH, {"q": query})
        time.sleep(0.2)
        if not payload:
            continue
        for org in (payload.get("organizations") or [])[:limit_per_name]:
            ein = str(org.get("ein") or "")
            name = org.get("name") or ""
            if not ein or ein in seen_eins:
                continue
            # The query is a substring search, so confirm the surname is
            # actually in the returned name before keeping it.
            token = query.split()[0].lower()
            if token not in name.lower():
                continue
            seen_eins.add(ein)
            found.append({
                "ein": ein,
                "name": name,
                "state": org.get("state"),
                "city": org.get("city"),
                "subsection": org.get("subseccd"),
                "matched_on": token,
                "source_url": f"https://projects.propublica.org/nonprofits/organizations/{ein}",
            })
    return found


def foundation_detail(ein: str) -> Dict[str, Any]:
    """Latest filing summary for one EIN."""
    payload = _http_get(PROPUBLICA_ORG.format(ein=ein))
    if not payload:
        return {}
    org = payload.get("organization") or {}
    filings = payload.get("filings_with_data") or []
    latest = filings[0] if filings else {}
    return {
        "ein": ein,
        "name": org.get("name"),
        "assets": latest.get("totassetsend") or latest.get("totassetsevoy"),
        "revenue": latest.get("totrevenue"),
        "tax_year": latest.get("tax_prd_yr"),
        "pdf_url": latest.get("pdf_url"),
    }


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

def get_family_network(entity_name: str,
                       proxy: Dict[str, Any] = None,
                       insider: Dict[str, Any] = None,
                       include_foundations: bool = True) -> Dict[str, Any]:
    """Vehicles attached to this issuer's insiders, and who they point at.

    Returns empty structures rather than inventing links. A run against an
    issuer whose insiders hold directly and fund no foundation should produce
    nothing here, and that is the correct answer for that issuer.
    """
    proxy = proxy or {}
    insider = insider or {}

    result: Dict[str, Any] = {
        "entity_name": entity_name,
        "vehicles": [],
        "surname_links": [],
        "foundations": [],
        "position_profile": {},
        "sources": ["SEC Form 3/4 reporting owners", "DEF 14A ownership table"],
    }

    people = _insider_people(insider, proxy)
    vehicles = vehicles_from_insiders(insider)
    proxy_vehicles = vehicles_from_proxy(proxy)

    known = {v["name"].lower() for v in vehicles}
    for entry in proxy_vehicles:
        if entry["name"].lower() not in known:
            vehicles.append(entry)

    for vehicle in vehicles:
        vehicle["institutional"] = is_institution(vehicle["name"])

    # Only the non-institutional ones are candidates for a family link.
    candidates = [v for v in vehicles if not v["institutional"]]
    result["vehicles"] = candidates
    result["institutional_vehicles"] = [v for v in vehicles if v["institutional"]]

    # Where a vehicle's name carries an insider's surname, record the link and
    # say precisely what evidences it.
    for vehicle in candidates:
        tokens = {t.lower() for t in re.findall(r"[A-Za-z]{3,}", vehicle["name"])}
        for surname, person in people.items():
            if surname not in tokens:
                continue
            result["surname_links"].append({
                "vehicle": vehicle["name"],
                "kind": vehicle["kind"],
                "surname": surname,
                "insider_names": sorted(person["names"]),
                "insider_roles": sorted(person["roles"]),
                "basis": (
                    f"The vehicle name contains '{surname}', which is also the "
                    f"surname of a {', '.join(sorted(person['roles'])) or 'reporting insider'} "
                    f"at {entity_name}. The filing establishes the vehicle; the "
                    f"shared surname is what suggests the connection and is not "
                    f"itself proof of a family relationship."
                ),
                "value": vehicle.get("value"),
                "source_url": vehicle.get("source_url"),
            })

    if include_foundations and people:
        try:
            result["foundations"] = foundations_for(
                sorted(people.keys()), entity_name)
        except Exception as error:
            logger.warning("Foundation lookup failed: %s", error)
            result["foundations"] = []
        if result["foundations"]:
            result["sources"].append("IRS Form 990 via ProPublica Nonprofit Explorer")

    # Position profile: what kind of position is held, and by how many.
    by_kind: Dict[str, int] = defaultdict(int)
    for vehicle in candidates:
        by_kind[vehicle["kind"]] += 1
    result["position_profile"] = {
        "people_identified": len(people),
        "vehicles_identified": len(candidates),
        "institutional_vehicles": len(result["institutional_vehicles"]),
        "vehicles_by_kind": dict(by_kind),
        "surname_linked": len(result["surname_links"]),
        "foundations": len(result["foundations"]),
        "direct_holders": max(0, len(people) - len(result["surname_links"])),
    }
    # James's point is about which positions family occupy, so the answer is
    # framed as a position census rather than a headcount. Each row is a place
    # a relative could hold something and whether we can see it here.
    result["position_census"] = [
        {"position": "Named on the payroll",
         "visible_in": "DEF 14A Item 404",
         "found": len((proxy.get("related_party_transactions") or []))},
        {"position": "Holder through a trust, LLC or partnership",
         "visible_in": "Form 3/4 reporting owner, proxy ownership table",
         "found": len(candidates)},
        {"position": "Holder sharing an insider's surname",
         "visible_in": "Vehicle name against Section 16 surnames",
         "found": len(result["surname_links"])},
        {"position": "Foundation trustee",
         "visible_in": "IRS Form 990 via ProPublica",
         "found": len(result["foundations"])},
        {"position": "Advisor",
         "visible_in": "No filing exists — prose sources only",
         "found": None},
    ]
    return result
