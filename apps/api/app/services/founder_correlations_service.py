"""
Founder Correlations Service
────────────────────────────────────────────────────────────────────────────
Identifies correlations and connections between founders and executives:
  - Educational background (studied together)
  - Prior company overlaps (worked together)
  - Co-investment patterns
  - Board seat overlaps across companies
  - PayPal Mafia-style network analysis

Uses existing SEC filings and proxy statements - no external APIs required.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Set, Tuple
from collections import defaultdict
from datetime import datetime

from app.services.person_disambiguation import (
    ELITE_INSTITUTIONS,
    INSTITUTION_ALIASES,
    company_core_name,
    extract_bio_companies,
    extract_institutions,
    normalize_institution,
    same_person,
)

logger = logging.getLogger(__name__)

# Known "Mafia" networks - companies that spawned notable founder networks
NOTABLE_NETWORKS = {
    "PayPal": {
        # Company names, not tickers. Matching tickers against company names by
        # substring made "Square Wave Ventures" a PayPal-network company on the
        # strength of the two letters in "SQ".
        "company_names": ["PayPal", "Tesla", "Palantir", "LinkedIn", "Block",
                          "Square", "Yelp", "YouTube", "Affirm"],
        "companies": ["PYPL", "TSLA", "PLTR", "LNKD", "SQ", "YELP", "YTBE"],
        "key_people": ["Peter Thiel", "Elon Musk", "Reid Hoffman", "Max Levchin",
                       "David Sacks", "Keith Rabois", "Roelof Botha", "Steve Chen",
                       "Chad Hurley", "Jeremy Stoppelman", "Russel Simmons"],
        "description": "Founders and early employees of PayPal who went on to found or lead major tech companies",
    },
    "Fairchild Semiconductor": {
        "company_names": ["Fairchild Semiconductor", "Intel",
                          "Shockley Semiconductor", "Kleiner Perkins"],
        "companies": ["INTC", "AMD", "NVDA"],
        "key_people": ["Robert Noyce", "Gordon Moore", "Eugene Kleiner", "Arthur Rock"],
        "description": "The 'Traitorous Eight' who left Shockley Semiconductor and founded Fairchild, then Intel",
    },
    "Microsoft": {
        "company_names": ["Microsoft"],
        "companies": ["MSFT", "AMZN", "GOOGL"],
        "key_people": ["Bill Gates", "Paul Allen", "Steve Ballmer"],
        "description": "Microsoft alumni who founded or led major tech companies",
    },
}

# Institution resolution and the elite set live with the other entity-resolution
# logic, so the alumni test used here is the same one the track-record and
# self-dealing sections use.
ELITE_UNIVERSITIES = {
    canonical: list(fragments)
    for canonical, fragments in INSTITUTION_ALIASES.items()
    if canonical in ELITE_INSTITUTIONS
}


def extract_educational_background(biography: str) -> List[Dict[str, Any]]:
    """
    Extract educational credentials from a biography text.

    Returns list of education entries with:
    - institution: University/school name
    - degree: Degree type (MBA, PhD, BS, etc.)
    - field: Field of study
    - year: Graduation year (if found)
    - normalized_institution: Standardized institution name for matching

    The extraction runs institution-first — find the school, then attach the
    degree stated before it. Capturing outward from the degree instead ran the
    match past the school and into the next clause, so "a BA degree in Economics
    from Dartmouth College and an MBA degree from Harvard Business School"
    yielded "Economics from Dartmouth College and an MBA degree" as the name of
    an institution and normalised to nothing. Two Dartmouth graduates on one
    board were consequently reported as zero educational connections.
    """
    return [
        {
            "raw_text": entry["institution"],
            "institution": entry["institution"],
            "degree": entry["degree"],
            "field": entry["field"],
            "year": entry["year"],
            "normalized_institution": entry["normalized_institution"],
            "is_elite": entry["is_elite"],
        }
        for entry in extract_institutions(biography)
    ]


def extract_prior_companies(
    biography: str,
    current_company: str = "",
    known_people: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Extract prior company experience from a biography text.

    Returns list of prior company entries with:
    - company: Company name
    - role: Position held
    - year: Year (if found)
    - is_founder: Whether they founded the company

    ``known_people`` are the other people in the cohort; passing them lets a
    candidate that is really someone's name be rejected rather than published as
    an employer.
    """
    return [
        {
            "raw_text": entry["company"],
            "company": entry["company"],
            "role": entry["role"],
            "year": entry["year"],
            "is_founder": entry["is_founder"],
        }
        for entry in extract_bio_companies(biography, current_company, known_people)
    ]


def find_educational_overlaps(
    people: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Find people who attended the same universities.

    Args:
        people: List of dicts with 'name' and 'biography' or 'education' keys

    Returns:
        Analysis of educational overlaps including:
        - overlaps: List of (institution, [people]) pairs
        - network_density: Measure of how connected the group is
        - elite_concentration: % at elite universities
    """
    result = {
        "overlaps": [],
        "by_institution": {},
        "network_density": 0.0,
        "elite_concentration": 0.0,
        "stanford_connection": [],
        "harvard_connection": [],
        "mit_connection": [],
    }

    if not people:
        return result

    # Extract education for each person
    institution_people: Dict[str, List[str]] = defaultdict(list)
    people_with_education = 0
    elite_count = 0

    for person in people:
        name = person.get("name", "")
        if not name:
            continue

        # Get education - either pre-extracted or from biography
        education = person.get("education", [])
        if not education and person.get("biography"):
            education = extract_educational_background(person["biography"])

        if education:
            people_with_education += 1

        person_elite = False
        for edu in education:
            inst = (edu.get("normalized_institution")
                    or normalize_institution(edu.get("institution", "")))
            if inst:
                if name not in institution_people[inst]:
                    institution_people[inst].append(name)
                if inst in ELITE_INSTITUTIONS:
                    person_elite = True

        # Elite concentration counts people, not degrees. Counting degrees made
        # a director with a Harvard AB and a Stanford JD two elite executives.
        if person_elite:
            elite_count += 1

    # Find overlaps (2+ people at same institution)
    overlaps = []
    for inst, names in institution_people.items():
        if len(names) >= 2:
            overlaps.append({
                "institution": inst,
                "people": names,
                "count": len(names),
                "is_elite": inst in ELITE_INSTITUTIONS,
            })

    overlaps.sort(key=lambda x: (-x["count"], x["institution"]))
    result["overlaps"] = overlaps
    result["by_institution"] = dict(institution_people)

    # Calculate network density
    if people_with_education > 1:
        total_pairs = len(people) * (len(people) - 1) / 2
        connected_pairs = sum(
            len(names) * (len(names) - 1) / 2
            for names in institution_people.values()
            if len(names) >= 2
        )
        result["network_density"] = round(connected_pairs / total_pairs, 3) if total_pairs else 0

    # Elite concentration
    if people_with_education:
        result["elite_concentration"] = round(elite_count / people_with_education * 100, 1)

    # Named connections for specific universities
    for key, variations in [
        ("stanford_connection", ELITE_UNIVERSITIES.get("Stanford University", [])),
        ("harvard_connection", ELITE_UNIVERSITIES.get("Harvard University", [])),
        ("mit_connection", ELITE_UNIVERSITIES.get("MIT", [])),
    ]:
        for inst, names in institution_people.items():
            if any(var.lower() in inst.lower() for var in variations):
                result[key.replace("_connection", "_connection")] = names
                break

    return result


def _years_overlap(entries: List[Dict[str, Any]]) -> Optional[bool]:
    """Whether two stints at one employer were contemporaneous.

    Returns None where the biographies do not date the roles, which is the
    common case; a shared employer is still worth reporting, but "worked
    together" is a stronger claim than the filing supports and is not made
    without dates.
    """
    years = [e.get("year") for e in entries if e.get("year")]
    if len(years) < 2:
        return None
    return max(years) - min(years) <= 10


def find_company_overlaps(
    people: List[Dict[str, Any]],
    current_company: str = "",
) -> Dict[str, Any]:
    """
    Find people who worked at the same prior companies.

    Args:
        people: List of dicts with 'name' and 'biography' or 'prior_companies' keys
        current_company: Current company name to exclude

    Returns:
        Analysis of company overlaps including:
        - overlaps: List of (company, [people]) pairs
        - serial_founders: People who founded multiple companies
        - paypal_mafia: Any connections to PayPal network
    """
    result = {
        "overlaps": [],
        "by_company": {},
        "serial_founders": [],
        "paypal_mafia_connection": [],
        "notable_network_connections": [],
    }

    if not people:
        return result

    # Keyed by the distinctive core of the name so that a director who lists
    # "Synopsys, Inc." and one who lists "Synopsys" are recorded at the same
    # employer rather than at two.
    company_people: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    company_labels: Dict[str, str] = {}
    founder_companies: Dict[str, List[str]] = defaultdict(list)
    cohort_names = [p.get("name", "") for p in people if p.get("name")]

    for person in people:
        name = person.get("name", "")
        if not name:
            continue

        # Get prior companies - either pre-extracted or from biography
        prior = person.get("prior_companies", [])
        if not prior and person.get("biography"):
            prior = extract_prior_companies(
                person["biography"], current_company, cohort_names)

        for comp in prior:
            company = comp.get("company", "")
            if not company:
                continue
            key = company_core_name(company) or company.lower()
            if key not in company_labels or len(company) > len(company_labels[key]):
                company_labels[key] = company
            if any(e["name"] == name for e in company_people[key]):
                continue
            company_people[key].append({
                "name": name,
                "role": comp.get("role"),
                "year": comp.get("year"),
                "is_founder": comp.get("is_founder", False),
            })

            if comp.get("is_founder"):
                founder_companies[name].append(company)

    # Find overlaps
    overlaps = []
    for key, entries in company_people.items():
        if len(entries) >= 2:
            overlaps.append({
                "company": company_labels.get(key, key),
                "people": [e["name"] for e in entries],
                "count": len(entries),
                "details": entries,
                # Two people at one employer in overlapping years worked
                # together; the same employer decades apart did not.
                "overlapping_years": _years_overlap(entries),
            })

    overlaps.sort(key=lambda x: (-x["count"], x["company"]))
    result["overlaps"] = overlaps
    result["by_company"] = {
        company_labels.get(k, k): [e["name"] for e in v]
        for k, v in company_people.items()
    }

    # Serial founders
    serial = [
        {"name": name, "companies_founded": companies, "count": len(companies)}
        for name, companies in founder_companies.items()
        if len(companies) >= 2
    ]
    serial.sort(key=lambda x: -x["count"])
    result["serial_founders"] = serial

    # Check for PayPal Mafia connections
    paypal_people = NOTABLE_NETWORKS["PayPal"]["key_people"]
    for person in people:
        name = person.get("name", "")
        if any(same_person(pp, name) for pp in paypal_people):
            result["paypal_mafia_connection"].append(name)

    # Check for other notable network connections. The comparison is on the
    # distinctive core of the company name, so membership requires naming the
    # company rather than merely containing a ticker's letters.
    for network_name, network in NOTABLE_NETWORKS.items():
        network_cores = {
            company_core_name(n) for n in network.get("company_names", []) if n
        }
        for key, entries in company_people.items():
            if key in network_cores:
                result["notable_network_connections"].append({
                    "network": network_name,
                    "company": company_labels.get(key, key),
                    "people": [e["name"] for e in entries],
                })

    return result


def build_founder_correlation_graph(
    people: List[Dict[str, Any]],
    company_name: str = "",
) -> Dict[str, Any]:
    """
    Build a comprehensive correlation graph for founders/executives.

    Returns:
        Complete correlation analysis with:
        - nodes: List of people with their attributes
        - edges: Connections between people with type and strength
        - clusters: Identified groups of connected people
        - key_findings: Notable patterns detected
    """
    result = {
        "nodes": [],
        "edges": [],
        "clusters": [],
        "key_findings": [],
        "education_overlaps": {},
        "company_overlaps": {},
        "network_stats": {},
    }

    if not people:
        return result

    # Extract education and company history for each person
    enriched_people = []
    cohort_names = [p.get("name", "") for p in people if p.get("name")]
    for person in people:
        name = person.get("name", "")
        if not name:
            continue

        bio = person.get("biography", "")
        education = person.get("education") or extract_educational_background(bio)
        prior = person.get("prior_companies") or extract_prior_companies(
            bio, company_name, cohort_names)

        enriched_people.append({
            **person,
            "education": education,
            "prior_companies": prior,
        })

        result["nodes"].append({
            "id": name,
            "name": name,
            "title": person.get("title") or person.get("occupation"),
            "education_count": len(education),
            "prior_company_count": len(prior),
            "is_founder": any(p.get("is_founder") for p in prior),
        })

    # Find education overlaps
    edu_overlaps = find_educational_overlaps(enriched_people)
    result["education_overlaps"] = edu_overlaps

    # Find company overlaps
    comp_overlaps = find_company_overlaps(enriched_people, company_name)
    result["company_overlaps"] = comp_overlaps

    # Build edges from overlaps
    edges = []

    # Education edges
    for overlap in edu_overlaps.get("overlaps", []):
        people_list = overlap["people"]
        for i, p1 in enumerate(people_list):
            for p2 in people_list[i+1:]:
                edges.append({
                    "source": p1,
                    "target": p2,
                    "type": "education",
                    "label": f"Both attended {overlap['institution']}",
                    "weight": 2 if overlap.get("is_elite") else 1,
                })

    # Company edges
    for overlap in comp_overlaps.get("overlaps", []):
        people_list = overlap["people"]
        contemporaneous = overlap.get("overlapping_years")
        for i, p1 in enumerate(people_list):
            for p2 in people_list[i+1:]:
                edges.append({
                    "source": p1,
                    "target": p2,
                    "type": "company",
                    "label": (f"Both held roles at {overlap['company']}"
                              + ("" if contemporaneous is None
                                 else " in overlapping years"
                                 if contemporaneous
                                 else " at different times")),
                    "weight": 3,  # Company overlap weighted higher
                    "contemporaneous": contemporaneous,
                })

    result["edges"] = edges

    # People with no connection to anyone else in the cohort. Naming them is
    # what makes a sparse network a finding rather than a gap.
    connected = {e["source"] for e in edges} | {e["target"] for e in edges}
    result["unconnected"] = [
        n["name"] for n in result["nodes"] if n["name"] not in connected
    ]

    # Calculate network stats
    result["network_stats"] = {
        "node_count": len(result["nodes"]),
        "edge_count": len(edges),
        "education_connections": len([e for e in edges if e["type"] == "education"]),
        "company_connections": len([e for e in edges if e["type"] == "company"]),
        "network_density": edu_overlaps.get("network_density", 0),
        "elite_university_pct": edu_overlaps.get("elite_concentration", 0),
    }

    # Generate key findings
    findings = []

    for top_inst in edu_overlaps.get("overlaps", [])[:3]:
        findings.append(
            f"{top_inst['count']} of the cohort attended "
            f"{top_inst['institution']} — {', '.join(top_inst['people'])}"
        )

    for top_comp in comp_overlaps.get("overlaps", [])[:3]:
        # "Worked together" requires dates; a shared employer alone does not
        # establish that two people were ever there at the same time.
        verb = ("worked together at" if top_comp.get("overlapping_years")
                else "each held roles at")
        findings.append(
            f"{top_comp['count']} of the cohort {verb} {top_comp['company']} — "
            f"{', '.join(top_comp['people'])}"
        )

    if comp_overlaps.get("serial_founders"):
        sf = comp_overlaps["serial_founders"][0]
        findings.append(
            f"{sf['name']} is a serial founder with {sf['count']} prior companies"
        )

    if comp_overlaps.get("paypal_mafia_connection"):
        findings.append(
            f"PayPal Mafia connection: {', '.join(comp_overlaps['paypal_mafia_connection'])}"
        )

    if edu_overlaps.get("elite_concentration", 0) > 50:
        findings.append(
            f"{edu_overlaps['elite_concentration']:.0f}% of executives attended elite universities"
        )

    result["key_findings"] = findings

    return result


def render_founder_correlations_markdown(data: Dict[str, Any]) -> List[str]:
    """Render founder correlations section as markdown."""
    lines = ["## Founder & Executive Correlations", ""]

    if not data.get("nodes"):
        return []

    stats = data.get("network_stats", {})

    # Key findings first
    findings = data.get("key_findings", [])
    if findings:
        lines.append("### Key Findings")
        lines.append("")
        for finding in findings:
            lines.append(f"- {finding}")
        lines.append("")

    # Network overview
    lines.append("### Network Overview")
    lines.append("")
    lines.append(f"- **People Analyzed:** {stats.get('node_count', 0)}")
    lines.append(f"- **Total Connections:** {stats.get('edge_count', 0)}")
    lines.append(f"- **Education Links:** {stats.get('education_connections', 0)}")
    lines.append(f"- **Company Links:** {stats.get('company_connections', 0)}")
    lines.append(f"- **Elite University Rate:** {stats.get('elite_university_pct', 0):.1f}%")
    lines.append("")

    # Education overlaps
    edu = data.get("education_overlaps", {})
    if edu.get("overlaps"):
        lines.append("### Educational Connections")
        lines.append("")
        lines.append("| Institution | Executives | Type |")
        lines.append("|-------------|------------|------|")
        for overlap in edu["overlaps"][:10]:
            elite = "Elite" if overlap.get("is_elite") else "Standard"
            lines.append(f"| {overlap['institution']} | {', '.join(overlap['people'])} | {elite} |")
        lines.append("")

    # Company overlaps
    comp = data.get("company_overlaps", {})
    if comp.get("overlaps"):
        lines.append("### Prior Company Connections")
        lines.append("")
        lines.append("| Company | Executives | Context |")
        lines.append("|---------|------------|---------|")
        for overlap in comp["overlaps"][:10]:
            contemporaneous = overlap.get("overlapping_years")
            context = ("Overlapping tenures" if contemporaneous
                       else "Same employer, different periods"
                       if contemporaneous is False
                       else "Same employer, tenures undated in the proxy")
            lines.append(f"| {overlap['company']} | {', '.join(overlap['people'])} "
                         f"| {context} |")
        lines.append("")

    # Serial founders
    if comp.get("serial_founders"):
        lines.append("### Serial Founders")
        lines.append("")
        for sf in comp["serial_founders"][:5]:
            lines.append(f"- **{sf['name']}** — Founded: {', '.join(sf['companies_founded'])}")
        lines.append("")

    # Notable network connections
    if comp.get("notable_network_connections"):
        lines.append("### Notable Network Connections")
        lines.append("")
        for conn in comp["notable_network_connections"]:
            lines.append(f"- **{conn['network']}** via {conn['company']}: {', '.join(conn['people'])}")
        lines.append("")

    # A cohort with no shared schools or employers is itself a finding, and one
    # worth distinguishing from a section that failed to run.
    unconnected = data.get("unconnected") or []
    if unconnected and len(unconnected) < stats.get("node_count", 0):
        lines.append(
            f"No shared school or employer was found in the filed biographies of "
            f"{len(unconnected)} of the {stats.get('node_count', 0)} people "
            f"examined: {', '.join(unconnected[:12])}."
        )
        lines.append("")

    lines.append(
        "*Connections are read from the education and employment histories in "
        "the issuer's own proxy statement. A proxy biography states where a "
        "person studied and worked but rarely when, so a shared employer is "
        "reported as such and is only called an overlapping tenure where both "
        "roles are dated.*"
    )
    lines.append("")

    return lines
