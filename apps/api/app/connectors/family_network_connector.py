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


# Words that appear in proxy section headings the board parser sometimes
# returns as though they were directors — "Board Performance Assessment",
# "Frequently Requested Information". Left unfiltered these become surnames
# and then get searched for as family foundations, which is how a run against
# Lockheed produced the Society For Personality Assessment Foundation.
_NOT_A_SURNAME = {
    "assessment", "attendance", "biographies", "information", "structure",
    "leadership", "performance", "committee", "governance", "compensation",
    "nominee", "nominees", "director", "directors", "board", "officer",
    "officers", "executive", "summary", "overview", "meeting", "meetings",
    "independence", "qualifications", "skills", "matrix", "election",
    "proposal", "proposals", "voting", "audit", "report", "biography",
    "experience", "background", "highlights", "requested", "frequently",
    "continued", "table", "contents", "other", "name", "age", "since",
}


def looks_like_person(name: str) -> bool:
    """Whether a name plausibly belongs to a human being.

    A conservative test, because the cost of a false positive here is a wrong
    family link in the report and the cost of a false negative is one missing
    surname among several dozen.
    """
    text = (name or "").strip()
    if not text or classify_holder(text) or is_institution(text):
        return False
    tokens = [t for t in re.split(r"[\s,]+", text) if t]
    if not 2 <= len(tokens) <= 5:
        return False
    words = {re.sub(r"[^a-z]", "", t.lower()) for t in tokens}
    if words & _NOT_A_SURNAME:
        return False
    # A real name is letters, hyphens, apostrophes and initials only.
    return all(re.fullmatch(r"[A-Za-z][A-Za-z'\-\.]*", t) for t in tokens)


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
        if not name or classify_holder(name) or not looks_like_person(name):
            continue
        # Form 4 reporting-owner names are always surname-first.
        key = surname_of(name, edgar_order=True)
        if not key or key in _NOT_A_SURNAME:
            continue
        entry = people.setdefault(key, {"names": set(), "roles": set(),
                                        "source": "Section 16"})
        entry["names"].add(name)
        for role in row.get("roles") or []:
            entry["roles"].add(role)

    board = (proxy or {}).get("board_composition") or {}
    for director in board.get("directors") or []:
        name = (director.get("name") or "").strip()
        if not name or not looks_like_person(name):
            continue
        # A proxy prints names the way the person writes them.
        key = surname_of(name, edgar_order=False)
        if not key or key in _NOT_A_SURNAME:
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

    The issuer's own corporate foundation is returned too but flagged as such.
    A company foundation and a family foundation are different objects, and
    filing the first under the second would be the same mistake as calling
    BlackRock someone's family office.
    """
    found: List[Dict[str, Any]] = []
    seen_eins: Set[str] = set()

    corporate_token = ""
    queries: List[tuple] = []
    if entity_name:
        corporate_token = entity_name.split()[0].lower()
        queries.append((f"{entity_name.split()[0]} foundation", True))
    queries += [(f"{s} foundation", False) for s in surnames[:8]
                if len(s) > 3 and s not in _NOT_A_SURNAME]

    for query, is_corporate in queries:
        payload = _http_get(PROPUBLICA_SEARCH, {"q": query})
        time.sleep(0.2)
        if not payload:
            continue
        token = query.split()[0].lower()
        for org in (payload.get("organizations") or [])[:limit_per_name]:
            ein = str(org.get("ein") or "")
            name = org.get("name") or ""
            if not ein or ein in seen_eins:
                continue
            # ProPublica searches loosely, so confirm the token is actually a
            # whole word in the returned name. A substring test matched
            # "Assessment" inside three unrelated charities on the first run.
            if not re.search(rf"\b{re.escape(token)}\b", name.lower()):
                continue
            seen_eins.add(ein)
            found.append({
                "ein": ein,
                "name": name,
                "state": org.get("state"),
                "city": org.get("city"),
                "subsection": org.get("subseccd"),
                "matched_on": token,
                "strength": _foundation_strength(name, token),
                "corporate": bool(is_corporate)
                             or (corporate_token and corporate_token in name.lower()),
                "source_url": f"https://projects.propublica.org/nonprofits/organizations/{ein}",
            })
    return found


def _foundation_strength(name: str, surname: str) -> str:
    """How much weight a surname match on a foundation name can carry.

    A family foundation is named to a near-fixed convention: the surname,
    optionally "Family", then "Foundation". "Carlson Family Foundation" fits
    it. "Burritt Museum Foundation" and "The Montana Cahill Foundation" carry
    the surname but describe something else, and treating those as family
    links would fill the section with leads that go nowhere.
    """
    cleaned = re.sub(r"[^a-z\s]", " ", (name or "").lower())
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = re.sub(r"^the\s+", "", cleaned)
    cleaned = re.sub(r"\s+(inc|incorporated|trust|tr|ltd|corp)$", "", cleaned)
    if re.fullmatch(rf"{re.escape(surname)}( family| charitable| family charitable)?"
                    r"( foundation| fund)", cleaned):
        return "pattern match"
    if cleaned.startswith(f"{surname} "):
        return "surname leads the name"
    return "surname appears in the name"


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

    # The issuer files Section 16 against itself on a director's behalf, so it
    # appears in its own reporting-owner list. It is not a family vehicle.
    issuer_key = re.sub(r"[^a-z]", "", (entity_name or "").lower())
    for vehicle in vehicles:
        vehicle["institutional"] = is_institution(vehicle["name"])
        vehicle["is_issuer"] = bool(issuer_key) and re.sub(
            r"[^a-z]", "", vehicle["name"].lower()) == issuer_key

    vehicles = [v for v in vehicles if not v["is_issuer"]]

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


def research_family_network(entity_name: str, ticker: str = "") -> Dict[str, Any]:
    """
    High-level wrapper for family network research.

    This is the entry point for the deep_research_orchestrator.
    It fetches proxy and insider data, then calls get_family_network.
    """
    from app.connectors.proxy_statement_connector import get_proxy_intelligence
    from app.connectors.sec_edgar_connector import get_filer_cik, get_insider_transactions

    result = {
        "entity_name": entity_name,
        "ticker": ticker,
        "executives": [],
        "vehicles": [],
        "surname_links": [],
        "foundations": [],
        "position_profile": {},
    }

    try:
        # Get proxy data
        proxy = {}
        if ticker:
            proxy = get_proxy_intelligence(ticker, years=2) or {}

        # Get insider transactions
        insider = {}
        if ticker:
            cik = get_filer_cik(ticker)
            if cik:
                insider = get_insider_transactions(cik) or {}

        # Run family network analysis
        network = get_family_network(
            entity_name=entity_name,
            proxy=proxy,
            insider=insider,
            include_foundations=True,
        )

        result.update(network)

    except Exception as e:
        logger.warning("Family network research failed for %s: %s", entity_name, e)

    return result


def render_family_network_markdown(data: Dict[str, Any]) -> List[str]:
    """Render family network analysis as markdown."""
    lines = ["## Family Network Analysis", ""]

    entity_name = data.get("entity_name", "Company")
    profile = data.get("position_profile", {}) or {}
    vehicles = data.get("vehicles", []) or []
    surname_links = data.get("surname_links", []) or []
    foundations = data.get("foundations", []) or []
    census = data.get("position_census", []) or []

    # Overview
    people_count = profile.get("people_identified", 0)
    vehicle_count = profile.get("vehicles_identified", 0)
    linked_count = profile.get("surname_linked", 0)
    foundation_count = profile.get("foundations", 0)

    # Filter foundations to only count valid ones
    # Fields are "name" and "strength" from foundations_for()
    valid_foundations = [
        f for f in foundations
        if f.get("name") and
           f.get("name") != "Unknown Foundation" and
           f.get("strength", "surname appears in the name") in ("pattern match", "surname leads the name")
    ]
    valid_foundation_count = len(valid_foundations)

    if not any([vehicles, surname_links, valid_foundations]):
        # Don't show section if nothing meaningful found
        return []

    # Build summary showing only what was found
    findings = []
    if people_count > 0:
        findings.append(f"**{people_count} reporting insiders**")
    if vehicle_count > 0:
        findings.append(f"**{vehicle_count} vehicles** (trusts, LLCs, partnerships)")
    if linked_count > 0:
        findings.append(f"**{linked_count} surname-linked positions**")
    if valid_foundation_count > 0:
        findings.append(f"**{valid_foundation_count} foundations**")

    if findings:
        lines.append(
            f"Analysis of Section 16 filings and proxy statements for {entity_name} "
            f"identified {', '.join(findings[:-1])}"
            + (f", and {findings[-1]}" if len(findings) > 1 else findings[0] if findings else "") + "."
        )
        lines.append("")

    # Position Census Table
    if census:
        lines.append("### Position Census")
        lines.append("")
        lines.append("| Position Type | Visible In | Found |")
        lines.append("|--------------|------------|-------|")
        for row in census:
            found = row.get("found")
            found_str = str(found) if found is not None else "N/A"
            lines.append(
                f"| {row.get('position', 'Unknown')} "
                f"| {row.get('visible_in', 'Unknown')} "
                f"| {found_str} |"
            )
        lines.append("")

    # Surname-linked vehicles (key findings)
    if surname_links:
        lines.append("### Family-Linked Holdings")
        lines.append("")
        lines.append(
            "The following vehicles contain surnames matching known insiders, "
            "suggesting potential family connections:"
        )
        lines.append("")

        for link in surname_links[:10]:
            vehicle = link.get("vehicle", "Unknown")
            kind = link.get("kind", "vehicle")
            surname = link.get("surname", "")
            roles = ", ".join(link.get("insider_roles", []))

            lines.append(f"**{vehicle}** ({kind})")
            lines.append(
                f"- Surname match: *{surname.title()}*"
            )
            if roles:
                lines.append(f"- Insider role(s): {roles}")
            if link.get("value"):
                lines.append(f"- Reported value: ${link['value']:,.0f}")
            if link.get("basis"):
                lines.append(f"- > {link['basis']}")
            lines.append("")

    # All vehicles by type
    by_kind = profile.get("vehicles_by_kind", {}) or {}
    if by_kind:
        lines.append("### Vehicle Breakdown by Type")
        lines.append("")
        lines.append("| Vehicle Type | Count |")
        lines.append("|--------------|-------|")
        for kind, count in sorted(by_kind.items(), key=lambda x: -x[1]):
            lines.append(f"| {kind.title()} | {count} |")
        lines.append("")

    # Foundations
    if foundations:
        lines.append("### Foundations")
        # Filter to only show foundations with actual names and strong matches
        # Fields are "name" and "strength" from foundations_for()
        valid_foundations = [
            f for f in foundations
            if f.get("name") and
               f.get("name") != "Unknown Foundation" and
               f.get("strength", "surname appears in the name") in ("pattern match", "surname leads the name")
        ]

        if valid_foundations:
            lines.append("")
            lines.append(
                f"{len(valid_foundations)} private foundation(s) were identified with names "
                f"matching insider surnames:"
            )
            lines.append("")

            for f in valid_foundations[:8]:
                name = f.get("name")
                ein = f.get("ein", "")
                assets = f.get("assets")
                year = f.get("tax_year")
                surname = f.get("matched_on", "")  # Field is "matched_on" not "surname"
                strength = f.get("strength", "")

                lines.append(f"**{name}**")
                if ein:
                    lines.append(f"- EIN: {ein}")
                if assets:
                    lines.append(f"- Total assets: ${assets:,.0f}")
                if year:
                    lines.append(f"- Tax year: {year}")
                if surname:
                    lines.append(f"- Surname match: {surname.title()}")
                lines.append("")

    # Source note
    sources = data.get("sources", [])
    if sources:
        lines.append(f"*Sources: {', '.join(sources)}.*")
        lines.append("")

    return lines
