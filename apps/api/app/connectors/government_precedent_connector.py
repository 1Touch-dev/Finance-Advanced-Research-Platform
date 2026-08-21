"""
Government Action Precedent Library Connector
────────────────────────────────────────────────────────────────────────────────
Industry-keyed enforcement precedents from SEC, DOJ, and FTC. Unlike the
litigation connector's company-name search (which returns unrelated matters),
this connector maps the issuer's SIC code to relevant regulatory categories
and fetches industry-level enforcement trends and notable precedents.

The "Government Action Precedent Library" section answers:
  - What enforcement actions affect companies in this industry?
  - What are the regulatory trends for this sector?
  - What precedents should investors consider?

Sources:
  - SEC Litigation Releases (sec.gov/litigation/litreleases)
  - SEC Administrative Proceedings (sec.gov/litigation/admin)
  - SEC Press Releases (sec.gov/news/pressreleases)
  - DOJ Antitrust Press (justice.gov/atr/press-releases)
  - FTC Actions (ftc.gov/enforcement/cases-proceedings)

Usage:
    from app.connectors.government_precedent_connector import (
        get_industry_precedents,
        get_precedent_library,
    )
    precedents = get_precedent_library("NVIDIA Corporation", "3674")
"""
import os
import re
import logging
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

_HEADERS = {"User-Agent": os.getenv("SEC_USER_AGENT", "FinanceIntelPlatform/1.0 research@example.com")}
_TIMEOUT = 25

# ── SIC Code to Regulatory Category Mapping ──────────────────────────────────
# Maps SIC code ranges to enforcement-relevant categories.
# This lets us fetch industry-level precedents rather than company-name searches.

SIC_REGULATORY_MAP = {
    # Technology / Semiconductors (SIC 3570-3579, 3670-3679)
    "technology": {
        "sic_ranges": [(3570, 3579), (3670, 3679), (3571, 3575), (7370, 7379)],
        "keywords": ["semiconductor", "chip", "software", "technology", "AI", "artificial intelligence",
                     "data center", "export control", "entity list", "CHIPS Act", "BIS"],
        "agencies": ["SEC", "DOJ", "BIS", "CFIUS"],
        "enforcement_types": ["export_control", "entity_list", "cfius", "antitrust", "securities_fraud"],
    },
    # Pharmaceuticals / Biotech (SIC 2830-2836)
    "pharma_biotech": {
        "sic_ranges": [(2830, 2836), (8731, 8731)],
        "keywords": ["pharmaceutical", "biotech", "drug", "FDA", "clinical trial", "off-label",
                     "kickback", "False Claims Act", "pricing"],
        "agencies": ["SEC", "DOJ", "FDA", "FTC"],
        "enforcement_types": ["fcpa", "false_claims", "securities_fraud", "antitrust"],
    },
    # Financial Services (SIC 6000-6299, 6700-6799)
    "financial_services": {
        "sic_ranges": [(6000, 6299), (6700, 6799)],
        "keywords": ["bank", "broker", "investment", "trading", "market manipulation",
                     "insider trading", "FINRA", "wire fraud", "money laundering"],
        "agencies": ["SEC", "DOJ", "FINRA", "CFTC", "OCC", "Fed"],
        "enforcement_types": ["insider_trading", "market_manipulation", "fraud", "aml"],
    },
    # Defense / Aerospace (SIC 3720-3769, 3812)
    "defense_aerospace": {
        "sic_ranges": [(3720, 3769), (3812, 3812)],
        "keywords": ["defense", "contractor", "procurement", "False Claims", "ITAR",
                     "export control", "debarment", "bid rigging"],
        "agencies": ["DOJ", "SEC", "GAO", "BIS"],
        "enforcement_types": ["false_claims", "procurement_fraud", "export_control", "fcpa"],
    },
    # Energy / Oil & Gas (SIC 1300-1389, 2910-2911, 4911-4939)
    "energy": {
        "sic_ranges": [(1300, 1389), (2910, 2911), (4911, 4939)],
        "keywords": ["oil", "gas", "energy", "FERC", "NERC", "environmental", "EPA",
                     "Clean Air Act", "spill", "FCPA"],
        "agencies": ["SEC", "DOJ", "EPA", "FERC"],
        "enforcement_types": ["environmental", "fcpa", "securities_fraud", "manipulation"],
    },
    # Automotive (SIC 3711-3716)
    "automotive": {
        "sic_ranges": [(3711, 3716)],
        "keywords": ["auto", "vehicle", "emission", "NHTSA", "recall", "safety defect",
                     "Clean Air Act", "diesel"],
        "agencies": ["DOJ", "EPA", "NHTSA", "FTC", "SEC"],
        "enforcement_types": ["environmental", "consumer_fraud", "securities_fraud"],
    },
    # Retail / Consumer Products (SIC 5200-5999)
    "retail_consumer": {
        "sic_ranges": [(5200, 5999), (5000, 5199)],
        "keywords": ["consumer", "retail", "FTC", "advertising", "privacy", "data breach",
                     "deceptive practices", "antitrust"],
        "agencies": ["FTC", "DOJ", "SEC", "State AG"],
        "enforcement_types": ["consumer_protection", "privacy", "antitrust", "advertising"],
    },
    # Healthcare (SIC 8000-8099)
    "healthcare": {
        "sic_ranges": [(8000, 8099)],
        "keywords": ["healthcare", "hospital", "Medicare", "Medicaid", "kickback",
                     "False Claims", "Stark Law", "Anti-Kickback"],
        "agencies": ["DOJ", "HHS-OIG", "SEC", "State AG"],
        "enforcement_types": ["false_claims", "kickback", "securities_fraud"],
    },
    # Telecom (SIC 4810-4899)
    "telecom": {
        "sic_ranges": [(4810, 4899)],
        "keywords": ["telecom", "FCC", "spectrum", "merger", "antitrust", "privacy",
                     "consumer protection", "TCPA"],
        "agencies": ["FCC", "DOJ", "FTC", "SEC"],
        "enforcement_types": ["antitrust", "consumer_protection", "privacy"],
    },
}

# ── Notable Industry Precedents (Curated Case Studies) ───────────────────────
# These are landmark cases that inform regulatory risk for each industry.
# Updated manually as major precedents emerge.

CURATED_PRECEDENTS = {
    "technology": [
        {
            "case": "ARM/NVIDIA Merger Block (FTC 2022)",
            "summary": "FTC sued to block NVIDIA's $40B acquisition of ARM, citing anticompetitive concerns. Deal abandoned.",
            "relevance": "Semiconductor M&A faces heightened antitrust scrutiny",
            "url": "https://www.ftc.gov/news-events/news/press-releases/2021/12/ftc-sues-block-40-billion-semiconductor-chip-merger",
            "year": 2022,
            "agency": "FTC",
        },
        {
            "case": "Entity List Export Controls (BIS 2019-present)",
            "summary": "BIS added Huawei, SMIC, and other Chinese tech firms to Entity List, restricting US technology exports.",
            "relevance": "Export control compliance critical for companies with China exposure",
            "url": "https://www.bis.doc.gov/index.php/policy-guidance/lists-of-parties-of-concern/entity-list",
            "year": 2019,
            "agency": "BIS",
        },
        {
            "case": "CHIPS Act Clawback Provisions (2022)",
            "summary": "CHIPS Act includes guardrails: 10-year ban on expanding chip capacity in China, clawback of subsidies if violated.",
            "relevance": "Companies receiving CHIPS funds face strict compliance obligations",
            "url": "https://www.commerce.gov/chips",
            "year": 2022,
            "agency": "Commerce",
        },
        {
            "case": "Qualcomm Antitrust (FTC 2019)",
            "summary": "FTC sued Qualcomm for anticompetitive licensing practices. District court ruled for FTC; reversed on appeal.",
            "relevance": "Licensing practices under continued scrutiny despite appeal victory",
            "url": "https://www.ftc.gov/news-events/news/press-releases/2017/01/ftc-charges-qualcomm-monopolizing-key-semiconductor-device-used",
            "year": 2019,
            "agency": "FTC",
        },
        {
            "case": "Google Antitrust (DOJ 2020-present)",
            "summary": "DOJ sued Google for monopolizing search and search advertising. Landmark big tech antitrust case.",
            "relevance": "Sets precedent for platform monopoly enforcement",
            "url": "https://www.justice.gov/opa/pr/justice-department-sues-monopolist-google-violating-antitrust-laws",
            "year": 2020,
            "agency": "DOJ",
        },
    ],
    "pharma_biotech": [
        {
            "case": "Theranos Securities Fraud (SEC/DOJ 2018)",
            "summary": "Elizabeth Holmes and Theranos charged with massive securities fraud. Holmes convicted, sentenced to prison.",
            "relevance": "False claims about technology capabilities face criminal prosecution",
            "url": "https://www.sec.gov/news/press-release/2018-41",
            "year": 2018,
            "agency": "SEC/DOJ",
        },
        {
            "case": "Novartis Kickback Settlement ($729M, 2020)",
            "summary": "Novartis paid $729M to settle False Claims Act allegations involving kickbacks to doctors.",
            "relevance": "Pharmaceutical speaker programs and HCP payments face intense scrutiny",
            "url": "https://www.justice.gov/opa/pr/novartis-pays-over-729-million-settle-allegations-improper-payments-doctors",
            "year": 2020,
            "agency": "DOJ",
        },
        {
            "case": "Biogen FCPA Settlement ($22M, 2022)",
            "summary": "Biogen settled FCPA charges for bribing foreign officials to approve drugs.",
            "relevance": "Pharma companies face FCPA risk in international markets",
            "url": "https://www.sec.gov/news/press-release/2022-167",
            "year": 2022,
            "agency": "SEC/DOJ",
        },
    ],
    "financial_services": [
        {
            "case": "Wells Fargo Account Fraud ($3B, 2020)",
            "summary": "Wells Fargo paid $3B to settle criminal and civil charges for creating millions of fake accounts.",
            "relevance": "Sales practice misconduct can lead to criminal prosecution",
            "url": "https://www.justice.gov/opa/pr/wells-fargo-agrees-pay-3-billion-resolve-criminal-and-civil-investigations",
            "year": 2020,
            "agency": "DOJ/SEC",
        },
        {
            "case": "Goldman Sachs 1MDB ($2.9B, 2020)",
            "summary": "Goldman Sachs paid $2.9B to settle 1MDB scandal charges across multiple jurisdictions.",
            "relevance": "FCPA and money laundering exposure from sovereign wealth fund dealings",
            "url": "https://www.justice.gov/opa/pr/goldman-sachs-charged-foreign-bribery-case-and-agrees-pay-over-29-billion",
            "year": 2020,
            "agency": "DOJ",
        },
        {
            "case": "Archegos Capital Collapse (SEC 2021)",
            "summary": "SEC charged Archegos founder with fraud causing $36B in losses. Banks face scrutiny over prime brokerage.",
            "relevance": "Total return swap exposure and risk management failures under regulatory focus",
            "url": "https://www.sec.gov/news/press-release/2022-70",
            "year": 2022,
            "agency": "SEC",
        },
    ],
    "defense_aerospace": [
        {
            "case": "Boeing 737 MAX Criminal Settlement ($2.5B, 2021)",
            "summary": "Boeing entered deferred prosecution agreement for fraud related to 737 MAX safety certification.",
            "relevance": "Misleading regulators on safety can lead to criminal charges",
            "url": "https://www.justice.gov/opa/pr/boeing-charged-737-max-fraud-conspiracy-and-agrees-pay-over-25-billion",
            "year": 2021,
            "agency": "DOJ",
        },
        {
            "case": "L3Harris FCPA Settlement ($33M, 2023)",
            "summary": "L3Harris subsidiary settled FCPA charges for bribing Saudi officials.",
            "relevance": "Defense contractors face FCPA risk in foreign military sales",
            "url": "https://www.sec.gov/news/press-release/2023-129",
            "year": 2023,
            "agency": "SEC/DOJ",
        },
    ],
    "energy": [
        {
            "case": "BP Deepwater Horizon ($20.8B, 2015)",
            "summary": "BP paid $20.8B to settle Deepwater Horizon disaster claims, including $5.5B in Clean Water Act penalties.",
            "relevance": "Environmental disasters can result in existential-scale penalties",
            "url": "https://www.justice.gov/opa/pr/united-states-and-five-gulf-states-reach-historic-settlement-bp-resolve-civil-claims",
            "year": 2015,
            "agency": "DOJ/EPA",
        },
        {
            "case": "Ericsson FCPA ($1.06B, 2019)",
            "summary": "Ericsson paid $1.06B to settle FCPA charges for bribes in multiple countries.",
            "relevance": "Infrastructure/energy projects in emerging markets face high FCPA risk",
            "url": "https://www.justice.gov/opa/pr/ericsson-agrees-pay-over-1-billion-resolve-fcpa-case",
            "year": 2019,
            "agency": "DOJ/SEC",
        },
    ],
    "automotive": [
        {
            "case": "Volkswagen Dieselgate ($30B+, 2016)",
            "summary": "VW paid $30B+ to settle emissions cheating scandal, including criminal guilty plea.",
            "relevance": "Emissions fraud leads to criminal prosecution and massive penalties",
            "url": "https://www.epa.gov/enforcement/volkswagen-clean-air-act-civil-settlement",
            "year": 2016,
            "agency": "DOJ/EPA",
        },
        {
            "case": "GM Ignition Switch ($900M, 2015)",
            "summary": "GM paid $900M for ignition switch defect that caused deaths. Company faced deferred prosecution.",
            "relevance": "Safety defect concealment can result in criminal charges",
            "url": "https://www.justice.gov/opa/pr/general-motors-agrees-deferred-prosecution-agreement-and-9-million-penalty-concealing-safety",
            "year": 2015,
            "agency": "DOJ",
        },
    ],
    "retail_consumer": [
        {
            "case": "Amazon FTC Settlement ($25M, 2023)",
            "summary": "Amazon settled FTC charges over children's privacy violations (Alexa/Ring).",
            "relevance": "Data privacy enforcement intensifying, especially for children's data",
            "url": "https://www.ftc.gov/news-events/news/press-releases/2023/05/ftc-doj-charge-amazon-violating-childrens-privacy-law-keeping-kids-alexa-voice-recordings-forever",
            "year": 2023,
            "agency": "FTC",
        },
        {
            "case": "Epic Games FTC Settlement ($520M, 2022)",
            "summary": "Epic Games paid $520M to settle FTC charges over dark patterns and children's privacy.",
            "relevance": "Dark patterns and COPPA violations face substantial penalties",
            "url": "https://www.ftc.gov/news-events/news/press-releases/2022/12/fortnite-video-game-maker-epic-games-pay-more-half-billion-dollars-over-ftc-allegations",
            "year": 2022,
            "agency": "FTC",
        },
    ],
    "healthcare": [
        {
            "case": "Purdue Pharma Opioid Settlement ($6B, 2022)",
            "summary": "Purdue and Sackler family agreed to $6B settlement for role in opioid crisis.",
            "relevance": "Opioid-related liability remains existential risk for pharma/healthcare",
            "url": "https://www.justice.gov/opa/pr/purdue-pharma-and-members-sackler-family-reach-resolution-over-6-billion-resolve-civil",
            "year": 2022,
            "agency": "DOJ",
        },
        {
            "case": "HCA False Claims Settlement ($1.7B, 2003)",
            "summary": "HCA Healthcare paid $1.7B in largest healthcare fraud settlement at the time.",
            "relevance": "Healthcare billing practices face ongoing False Claims Act scrutiny",
            "url": "https://www.justice.gov/archive/opa/pr/2003/June/03_civ_386.htm",
            "year": 2003,
            "agency": "DOJ",
        },
    ],
    "telecom": [
        {
            "case": "AT&T/Time Warner Merger (DOJ 2018)",
            "summary": "DOJ sued to block AT&T's acquisition of Time Warner; lost at trial and on appeal.",
            "relevance": "Vertical mergers still face DOJ scrutiny despite AT&T win",
            "url": "https://www.justice.gov/opa/pr/justice-department-challenges-att-directv-s-acquisition-time-warner",
            "year": 2018,
            "agency": "DOJ",
        },
        {
            "case": "T-Mobile Data Breach FCC Settlement ($80M, 2024)",
            "summary": "T-Mobile agreed to $80M+ in FCC penalties for data breaches affecting millions.",
            "relevance": "Telecom carriers face regulatory action for data security failures",
            "url": "https://www.fcc.gov/document/fcc-enters-settlement-t-mobile-strengthen-data-breach-protections",
            "year": 2024,
            "agency": "FCC",
        },
    ],
}


def _sic_to_category(sic: str) -> Optional[str]:
    """Map a SIC code to a regulatory category."""
    try:
        sic_int = int(sic)
    except (ValueError, TypeError):
        return None

    for category, config in SIC_REGULATORY_MAP.items():
        for start, end in config["sic_ranges"]:
            if start <= sic_int <= end:
                return category
    return None


def _fetch_sec_rss(feed_type: str = "litreleases", limit: int = 25) -> List[Dict[str, Any]]:
    """
    Fetch recent SEC enforcement releases from RSS feeds.

    feed_type: "litreleases" | "admin" | "press"
    """
    feeds = {
        "litreleases": "https://www.sec.gov/cgi-bin/browse-edgar?action=getlatest&type=LR&owner=include&count=40&start=0&output=atom",
        "admin": "https://www.sec.gov/cgi-bin/browse-edgar?action=getlatest&type=AP&owner=include&count=40&start=0&output=atom",
        "press": "https://www.sec.gov/news/pressreleases.rss",
    }

    url = feeds.get(feed_type)
    if not url:
        return []

    results = []
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
        if resp.ok:
            # SEC feeds are Atom format
            root = ET.fromstring(resp.content)
            ns = {"atom": "http://www.w3.org/2005/Atom"}

            for entry in root.findall(".//atom:entry", ns)[:limit]:
                title_elem = entry.find("atom:title", ns)
                link_elem = entry.find("atom:link", ns)
                updated_elem = entry.find("atom:updated", ns)
                summary_elem = entry.find("atom:summary", ns)

                if title_elem is not None:
                    results.append({
                        "title": title_elem.text or "",
                        "url": link_elem.get("href", "") if link_elem is not None else "",
                        "date": updated_elem.text[:10] if updated_elem is not None else "",
                        "summary": summary_elem.text[:500] if summary_elem is not None and summary_elem.text else "",
                        "agency": "SEC",
                        "type": feed_type,
                    })
    except Exception as e:
        logger.warning("SEC RSS fetch failed (%s): %s", feed_type, e)

    return results


def _fetch_sec_litigation_page(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Fetch SEC litigation releases from the HTML page (more complete than RSS).
    """
    results = []
    try:
        resp = requests.get(
            "https://www.sec.gov/litigation/litreleases.htm",
            headers=_HEADERS,
            timeout=_TIMEOUT,
        )
        if resp.ok:
            soup = BeautifulSoup(resp.text, "html.parser")

            # SEC litigation page has table rows with case info
            for row in soup.select("table tr")[:limit]:
                cells = row.find_all("td")
                if len(cells) >= 2:
                    link = row.find("a")
                    if link:
                        text = row.get_text(" ", strip=True)
                        results.append({
                            "title": link.get_text(strip=True),
                            "url": f"https://www.sec.gov{link.get('href', '')}",
                            "date": "",  # Would need to parse from text
                            "summary": text[:300],
                            "agency": "SEC",
                            "type": "litigation_release",
                        })
    except Exception as e:
        logger.warning("SEC litigation page fetch failed: %s", e)

    return results


def _filter_by_keywords(items: List[Dict], keywords: List[str]) -> List[Dict]:
    """Filter enforcement items by industry-relevant keywords."""
    if not keywords:
        return items

    filtered = []
    keyword_pattern = re.compile("|".join(re.escape(k) for k in keywords), re.IGNORECASE)

    for item in items:
        text = f"{item.get('title', '')} {item.get('summary', '')}"
        if keyword_pattern.search(text):
            filtered.append(item)

    return filtered


def get_industry_precedents(sic: str, limit: int = 20) -> Dict[str, Any]:
    """
    Get industry-level enforcement precedents based on SIC code.

    Args:
        sic: Standard Industrial Classification code
        limit: Maximum number of recent actions to return

    Returns:
        Industry enforcement summary with recent actions and curated precedents.
    """
    category = _sic_to_category(sic)

    result = {
        "sic": sic,
        "industry_category": category or "general",
        "recent_actions": [],
        "curated_precedents": [],
        "regulatory_focus_areas": [],
        "primary_agencies": [],
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }

    if category and category in SIC_REGULATORY_MAP:
        config = SIC_REGULATORY_MAP[category]
        result["regulatory_focus_areas"] = config["enforcement_types"]
        result["primary_agencies"] = config["agencies"]
        keywords = config["keywords"]
    else:
        keywords = []

    # Fetch recent SEC actions
    sec_actions = _fetch_sec_litigation_page(limit * 2)
    if keywords:
        sec_actions = _filter_by_keywords(sec_actions, keywords)
    result["recent_actions"] = sec_actions[:limit]

    # Add curated precedents for the industry
    if category and category in CURATED_PRECEDENTS:
        result["curated_precedents"] = CURATED_PRECEDENTS[category]

    return result


def get_precedent_library(
    entity_name: str,
    sic: str = "",
    ticker: str = "",
) -> Dict[str, Any]:
    """
    Generate the Government Action Precedent Library section.

    Args:
        entity_name: Company name
        sic: SIC code (will be looked up if not provided)
        ticker: Stock ticker

    Returns:
        Complete precedent library payload for the report section.
    """
    result = {
        "entity": entity_name,
        "ticker": ticker,
        "sic": sic,
        "industry_category": "",
        "section_title": "Government Action Precedent Library",
        "methodology_note": (
            "This section presents regulatory enforcement precedents relevant to the issuer's "
            "industry sector, based on SIC code mapping. Precedents are drawn from SEC litigation "
            "releases, DOJ press releases, and FTC enforcement actions. Curated case studies "
            "highlight landmark enforcement actions that inform regulatory risk assessment."
        ),
        "curated_precedents": [],
        "recent_industry_actions": [],
        "enforcement_trends": [],
        "risk_factors": [],
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }

    # Get SIC if not provided
    if not sic and ticker:
        try:
            from app.connectors.sec_edgar_connector import get_company_submissions
            submissions = get_company_submissions(ticker)
            sic = submissions.get("sic", "")
        except Exception as e:
            logger.warning("Could not fetch SIC for %s: %s", ticker, e)

    result["sic"] = sic
    category = _sic_to_category(sic)
    result["industry_category"] = category or "general"

    # Get industry precedents
    industry_data = get_industry_precedents(sic, limit=15)
    result["curated_precedents"] = industry_data.get("curated_precedents", [])
    result["recent_industry_actions"] = industry_data.get("recent_actions", [])

    # Add enforcement trends summary
    if category and category in SIC_REGULATORY_MAP:
        config = SIC_REGULATORY_MAP[category]
        result["enforcement_trends"] = [
            {
                "focus_area": area.replace("_", " ").title(),
                "primary_agencies": config["agencies"],
            }
            for area in config["enforcement_types"]
        ]

        # Generate risk factors from precedents
        for precedent in result["curated_precedents"][:3]:
            result["risk_factors"].append({
                "risk": precedent.get("relevance", ""),
                "precedent": precedent.get("case", ""),
                "year": precedent.get("year", ""),
            })

    return result


def format_precedent_section(library: Dict[str, Any]) -> str:
    """
    Format the precedent library as markdown for report inclusion.
    """
    lines = []
    lines.append("## 12. Government Action Precedent Library\n")
    lines.append(f"**Industry Classification:** {library.get('industry_category', 'General').title()}")
    lines.append(f"**SIC Code:** {library.get('sic', 'N/A')}\n")

    lines.append("### Methodology\n")
    lines.append(library.get("methodology_note", ""))
    lines.append("")

    # Curated Precedents
    if library.get("curated_precedents"):
        lines.append("### Landmark Precedents Relevant to This Industry\n")
        for p in library["curated_precedents"]:
            lines.append(f"**{p.get('case', '')}**")
            lines.append(f"- **Summary:** {p.get('summary', '')}")
            lines.append(f"- **Relevance:** {p.get('relevance', '')}")
            lines.append(f"- **Agency:** {p.get('agency', '')} | **Year:** {p.get('year', '')}")
            if p.get("url"):
                lines.append(f"- [Source]({p.get('url')})")
            lines.append("")

    # Enforcement Trends
    if library.get("enforcement_trends"):
        lines.append("### Enforcement Focus Areas\n")
        lines.append("| Focus Area | Primary Agencies |")
        lines.append("|------------|------------------|")
        for trend in library["enforcement_trends"]:
            agencies = ", ".join(trend.get("primary_agencies", []))
            lines.append(f"| {trend.get('focus_area', '')} | {agencies} |")
        lines.append("")

    # Risk Factors
    if library.get("risk_factors"):
        lines.append("### Key Regulatory Risk Factors\n")
        for rf in library["risk_factors"]:
            lines.append(f"- **{rf.get('risk', '')}** (per *{rf.get('precedent', '')}*, {rf.get('year', '')})")
        lines.append("")

    # Recent Industry Actions
    if library.get("recent_industry_actions"):
        lines.append("### Recent Enforcement Actions in This Industry\n")
        for action in library["recent_industry_actions"][:10]:
            lines.append(f"- [{action.get('title', '')}]({action.get('url', '')}) — {action.get('agency', '')}")
        lines.append("")

    return "\n".join(lines)


# ─── BEA (Bureau of Economic Analysis) ────────────────────────────────────────
# GDP, regional income, industry data
# Signup: https://apps.bea.gov/API/signup/ (FREE)

BEA_BASE = "https://apps.bea.gov/api/data"
BEA_USER_ID = os.getenv("BEA_API_USER_ID", "")


def bea_get_data(dataset: str = "NIPA", table: str = "T10101", frequency: str = "A",
                 year: str = "2020,2021,2022,2023,2024") -> Dict[str, Any]:
    """
    Fetch data from BEA API.

    Args:
        dataset: BEA dataset (NIPA, Regional, etc.)
        table: Table name (T10101 for GDP, SAINC1 for state income, etc.)
        frequency: A=Annual, Q=Quarterly
        year: Years to fetch (comma-separated or LAST5)
    """
    if not BEA_USER_ID:
        return {"error": "BEA_API_USER_ID not set. Signup: https://apps.bea.gov/API/signup/"}

    try:
        params = {
            "UserID": BEA_USER_ID,
            "method": "GetData",
            "datasetname": dataset,
            "TableName": table,
            "Frequency": frequency,
            "Year": year,
            "ResultFormat": "JSON",
        }
        r = requests.get(BEA_BASE, params=params, timeout=30)
        data = r.json()

        results = data.get("BEAAPI", {}).get("Results", {})
        if "Error" in results:
            return {"error": results["Error"]}

        return {
            "dataset": dataset,
            "table": table,
            "data": results.get("Data", []),
            "statistic": results.get("Statistic", ""),
            "source": "BEA (Bureau of Economic Analysis)",
        }
    except Exception as e:
        logger.warning("BEA fetch error: %s", e)
        return {"error": str(e)}


def bea_gdp(years: str = "2020,2021,2022,2023,2024") -> Dict[str, Any]:
    """Fetch GDP data from BEA."""
    return bea_get_data("NIPA", "T10101", "A", years)


def bea_state_income(year: str = "LAST5") -> Dict[str, Any]:
    """Fetch state personal income from BEA."""
    if not BEA_USER_ID:
        return {"error": "BEA_API_USER_ID not set"}

    try:
        params = {
            "UserID": BEA_USER_ID,
            "method": "GetData",
            "datasetname": "Regional",
            "TableName": "SAINC1",
            "LineCode": "1",
            "GeoFips": "STATE",
            "Year": year,
            "ResultFormat": "JSON",
        }
        r = requests.get(BEA_BASE, params=params, timeout=30)
        data = r.json()
        results = data.get("BEAAPI", {}).get("Results", {})
        return {
            "table": "SAINC1",
            "description": "State Personal Income",
            "data": results.get("Data", []),
            "source": "BEA",
        }
    except Exception as e:
        return {"error": str(e)}


# ─── SAM.gov (System for Award Management) ────────────────────────────────────
# Federal contract opportunities and entity data
# API key: https://open.gsa.gov/api/sam-entity-extracts-api/

SAM_API_KEY = os.getenv("SAM_GOV_API_KEY", "") or os.getenv("SAM_API_KEY", "")


def sam_search_opportunities(keywords: str = "", limit: int = 20,
                              days_back: int = 30) -> Dict[str, Any]:
    """
    Search SAM.gov for federal contract opportunities.

    Args:
        keywords: Search keywords
        limit: Max results
        days_back: Look back this many days
    """
    if not SAM_API_KEY:
        return {"error": "SAM_GOV_API_KEY not set"}

    try:
        from datetime import datetime, timedelta
        end = datetime.now().date()
        start = end - timedelta(days=days_back)

        url = "https://api.sam.gov/opportunities/v2/search"
        params = {
            "api_key": SAM_API_KEY,
            "limit": limit,
            "postedFrom": start.strftime("%m/%d/%Y"),
            "postedTo": end.strftime("%m/%d/%Y"),
        }
        if keywords:
            params["keywords"] = keywords

        r = requests.get(url, params=params, timeout=30)
        data = r.json()

        opportunities = data.get("opportunitiesData", [])
        return {
            "count": len(opportunities),
            "opportunities": [{
                "notice_id": o.get("noticeId"),
                "title": o.get("title"),
                "type": o.get("type"),
                "posted_date": o.get("postedDate"),
                "response_deadline": o.get("responseDeadLine"),
                "agency": o.get("fullParentPathName"),
                "naics_code": o.get("naicsCode"),
                "set_aside": o.get("typeOfSetAsideDescription"),
                "place_of_performance": o.get("placeOfPerformance", {}).get("city", {}).get("name"),
            } for o in opportunities],
            "source": "SAM.gov",
        }
    except Exception as e:
        logger.warning("SAM.gov search error: %s", e)
        return {"error": str(e)}


def sam_entity_search(entity_name: str, limit: int = 10) -> Dict[str, Any]:
    """
    Search for registered entities in SAM.gov.
    """
    if not SAM_API_KEY:
        return {"error": "SAM_GOV_API_KEY not set"}

    try:
        url = "https://api.sam.gov/entity-information/v3/entities"
        params = {
            "api_key": SAM_API_KEY,
            "legalBusinessName": entity_name,
            "includeSections": "entityRegistration",
            "registrationStatus": "A",
        }
        r = requests.get(url, params=params, timeout=30)
        data = r.json()

        entities = data.get("entityData", [])[:limit]
        return {
            "count": len(entities),
            "entities": [{
                "uei": e.get("entityRegistration", {}).get("ueiSAM"),
                "legal_name": e.get("entityRegistration", {}).get("legalBusinessName"),
                "dba_name": e.get("entityRegistration", {}).get("dbaName"),
                "cage_code": e.get("entityRegistration", {}).get("cageCode"),
                "registration_status": e.get("entityRegistration", {}).get("registrationStatus"),
                "expiration_date": e.get("entityRegistration", {}).get("registrationExpirationDate"),
                "physical_address": e.get("entityRegistration", {}).get("physicalAddress", {}),
            } for e in entities],
            "source": "SAM.gov",
        }
    except Exception as e:
        logger.warning("SAM.gov entity search error: %s", e)
        return {"error": str(e)}


# ─── Regulations.gov ──────────────────────────────────────────────────────────
# Federal regulations, proposed rules, public comments
# API key: https://open.gsa.gov/api/regulationsgov/

REGULATIONS_GOV_KEY = os.getenv("REGULATIONS_GOV_API_KEY", "")


def regulations_search(query: str = "", agency: str = "", limit: int = 20) -> Dict[str, Any]:
    """
    Search Regulations.gov for federal regulations and proposed rules.

    Args:
        query: Search keywords
        agency: Filter by agency (e.g., "EPA", "SEC", "FDA")
        limit: Max results
    """
    if not REGULATIONS_GOV_KEY:
        return {"error": "REGULATIONS_GOV_API_KEY not set"}

    try:
        url = "https://api.regulations.gov/v4/documents"
        headers = {"X-Api-Key": REGULATIONS_GOV_KEY}
        params = {"page[size]": limit, "sort": "-postedDate"}
        if query:
            params["filter[searchTerm]"] = query
        if agency:
            params["filter[agencyId]"] = agency

        r = requests.get(url, headers=headers, params=params, timeout=30)
        data = r.json()

        documents = data.get("data", [])
        return {
            "count": len(documents),
            "documents": [{
                "id": d.get("id"),
                "title": d.get("attributes", {}).get("title"),
                "document_type": d.get("attributes", {}).get("documentType"),
                "agency_id": d.get("attributes", {}).get("agencyId"),
                "posted_date": d.get("attributes", {}).get("postedDate"),
                "comment_end_date": d.get("attributes", {}).get("commentEndDate"),
                "docket_id": d.get("attributes", {}).get("docketId"),
                "highlights": d.get("attributes", {}).get("highlightedContent"),
            } for d in documents],
            "source": "Regulations.gov",
        }
    except Exception as e:
        logger.warning("Regulations.gov search error: %s", e)
        return {"error": str(e)}


def regulations_docket(docket_id: str) -> Dict[str, Any]:
    """
    Get details about a specific regulatory docket.
    """
    if not REGULATIONS_GOV_KEY:
        return {"error": "REGULATIONS_GOV_API_KEY not set"}

    try:
        url = f"https://api.regulations.gov/v4/dockets/{docket_id}"
        headers = {"X-Api-Key": REGULATIONS_GOV_KEY}

        r = requests.get(url, headers=headers, timeout=30)
        data = r.json()

        attrs = data.get("data", {}).get("attributes", {})
        return {
            "docket_id": docket_id,
            "title": attrs.get("title"),
            "agency_id": attrs.get("agencyId"),
            "docket_type": attrs.get("docketType"),
            "rin": attrs.get("rin"),
            "abstract": attrs.get("dkAbstract"),
            "effective_date": attrs.get("effectiveDate"),
            "source": "Regulations.gov",
        }
    except Exception as e:
        logger.warning("Regulations.gov docket error: %s", e)
        return {"error": str(e)}


# ─── GovInfo (Government Publishing Office) ───────────────────────────────────
# Federal government documents, bills, CFR, Federal Register

GOVINFO_KEY = os.getenv("GOVINFO_API_KEY", "")


def govinfo_search(query: str, collection: str = "FR", limit: int = 20) -> Dict[str, Any]:
    """
    Search GovInfo for federal government documents.

    Args:
        query: Search keywords
        collection: Document collection (FR=Federal Register, CFR, BILLS, etc.)
        limit: Max results
    """
    if not GOVINFO_KEY:
        return {"error": "GOVINFO_API_KEY not set"}

    try:
        url = "https://api.govinfo.gov/search"
        params = {
            "api_key": GOVINFO_KEY,
            "query": query,
            "collection": collection,
            "pageSize": limit,
        }

        r = requests.get(url, params=params, timeout=30)
        data = r.json()

        results = data.get("results", [])
        return {
            "count": data.get("count", len(results)),
            "documents": [{
                "package_id": d.get("packageId"),
                "title": d.get("title"),
                "date_issued": d.get("dateIssued"),
                "collection": d.get("collectionCode"),
                "government_author": d.get("governmentAuthor1"),
                "doc_class": d.get("docClass"),
                "pages": d.get("pages"),
            } for d in results],
            "source": "GovInfo",
        }
    except Exception as e:
        logger.warning("GovInfo search error: %s", e)
        return {"error": str(e)}
