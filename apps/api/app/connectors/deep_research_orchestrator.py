"""
Deep Research Orchestrator (Phase 2 - Enhanced)
────────────────────────────────────────────────────────────────────────────
Master coordinator for comprehensive deep intelligence gathering that orchestrates:

  Phase 1 Connectors:
  - LinkedIn Deep Research (personnel, board interlocks, family connections)
  - FPDS Full Contracts (complete federal portfolio, self-dealing analysis)
  - OpenSecrets Political Intelligence (PAC, donations, lobbying, revolving door)
  - 13F Institutional Overlap (competitor shared investors, concentration)

  Phase 2 Connectors:
  - SEC EDGAR Financial (XBRL financials, Form 4 insider transactions)
  - Entity Network/Swarm (family networks, cross-firm connections, holding cos)
  - Proxy Statement Parser (executive compensation, board composition, say-on-pay)
  - Litigation Tracker (federal cases, SEC enforcement, FTC, antitrust)
  - Timeline Generator (event chronology, price movements)
  - DCF Valuation Model (Bear/Base/Bull scenarios, sensitivity analysis)
  - Risk Register Generator (categorized risks, mitigation strategies)

This orchestrator:
  1. Resolves entity identifiers across data sources
  2. Runs all deep research connectors in parallel
  3. Cross-references findings for correlation detection
  4. Generates unified deep intelligence payload
  5. Builds comprehensive risk register
  6. Creates event timeline
  7. Runs valuation analysis
  8. Flags anomalies and red flags

Usage:
    from app.connectors.deep_research_orchestrator import run_deep_intelligence
    result = run_deep_intelligence("NVIDIA Corporation", ticker="NVDA", competitors=["AMD", "INTC"])

    # For full comprehensive report:
    result = run_comprehensive_intelligence("NVIDIA Corporation", ticker="NVDA")
"""
import os
import time
import logging
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

logger = logging.getLogger(__name__)

# Import all deep research connectors
try:
    from app.connectors.linkedin_deep_connector import (
        deep_personnel_research,
        fetch_executive_deep_profile,
        fetch_company_executives,
    )
    LINKEDIN_AVAILABLE = True
except ImportError:
    LINKEDIN_AVAILABLE = False
    def deep_personnel_research(*args, **kwargs): return {}
    def fetch_executive_deep_profile(*args): return {}
    def fetch_company_executives(*args, **kwargs): return {}

try:
    from app.connectors.fpds_connector import (
        get_full_contract_portfolio,
        detect_self_dealing,
    )
    FPDS_AVAILABLE = True
except ImportError:
    FPDS_AVAILABLE = False
    def get_full_contract_portfolio(*args, **kwargs): return {}
    def detect_self_dealing(*args, **kwargs): return {}

try:
    from app.connectors.opensecrets_connector import (
        get_political_intelligence,
        fetch_lobbying_summary,
        detect_revolving_door,
    )
    OPENSECRETS_AVAILABLE = True
except ImportError:
    OPENSECRETS_AVAILABLE = False
    def get_political_intelligence(*args, **kwargs): return {}
    def fetch_lobbying_summary(*args): return {}
    def detect_revolving_door(*args, **kwargs): return []

try:
    from app.connectors.institutional_overlap_connector import (
        get_institutional_overlap,
        compare_competitor_ownership,
        get_mega_holder_positions,
    )
    OVERLAP_AVAILABLE = True
except ImportError:
    OVERLAP_AVAILABLE = False
    def get_institutional_overlap(*args): return {}
    def compare_competitor_ownership(*args): return {}
    def get_mega_holder_positions(*args): return {}

# ── Phase 2 Connector Imports ────────────────────────────────────────────────

try:
    from app.connectors.sec_edgar_connector import (
        get_filer_cik,
        get_full_financial_profile,
        get_insider_transactions,
    )
    from app.connectors.institutional_holdings_connector import (
        get_institutional_holders,
    )
    from app.connectors.filing_notes_connector import get_filing_notes
    from app.connectors.board_interlock_connector import get_beneficial_owners
    SEC_EDGAR_AVAILABLE = True
except ImportError:
    SEC_EDGAR_AVAILABLE = False
    def get_filer_cik(*args, **kwargs): return None
    def get_full_financial_profile(*args, **kwargs): return {}
    def get_insider_transactions(*args, **kwargs): return {}
    def get_institutional_holders(*args, **kwargs): return {}
    def get_filing_notes(*args, **kwargs): return {}
    def get_beneficial_owners(*args, **kwargs): return {}

try:
    from app.connectors.board_interlock_connector import get_board_interlocks
    BOARD_INTERLOCK_AVAILABLE = True
except ImportError:
    BOARD_INTERLOCK_AVAILABLE = False
    def get_board_interlocks(*args, **kwargs): return {}

try:
    from app.connectors.entity_network_connector import (
        build_entity_network,
        discover_family_network,
        find_cross_firm_connections,
    )
    ENTITY_NETWORK_AVAILABLE = True
except ImportError:
    ENTITY_NETWORK_AVAILABLE = False
    def build_entity_network(*args, **kwargs): return {}
    def discover_family_network(*args, **kwargs): return {}
    def find_cross_firm_connections(*args, **kwargs): return {}

try:
    from app.connectors.proxy_statement_connector import (
        get_proxy_intelligence,
        extract_executive_compensation,
    )
    PROXY_AVAILABLE = True
except ImportError:
    PROXY_AVAILABLE = False
    def get_proxy_intelligence(*args, **kwargs): return {}
    def extract_executive_compensation(*args, **kwargs): return {}

try:
    from app.connectors.litigation_connector import (
        get_litigation_intelligence,
        generate_legal_timeline,
    )
    LITIGATION_AVAILABLE = True
except ImportError:
    LITIGATION_AVAILABLE = False
    def get_litigation_intelligence(*args, **kwargs): return {}
    def generate_legal_timeline(*args): return []

try:
    from app.connectors.timeline_connector import (
        generate_entity_timeline,
        generate_timeline_markdown,
    )
    TIMELINE_AVAILABLE = True
except ImportError:
    TIMELINE_AVAILABLE = False
    def generate_entity_timeline(*args, **kwargs): return {}
    def generate_timeline_markdown(*args): return ""

try:
    from app.connectors.valuation_connector import (
        generate_scenario_analysis,
        generate_sensitivity_analysis,
        full_valuation_report,
    )
    VALUATION_AVAILABLE = True
except ImportError:
    VALUATION_AVAILABLE = False
    def generate_scenario_analysis(*args): return {}
    def generate_sensitivity_analysis(*args, **kwargs): return {}
    def full_valuation_report(*args): return {}

try:
    from app.connectors.risk_register_connector import (
        generate_risk_register,
        generate_risk_register_markdown,
    )
    RISK_REGISTER_AVAILABLE = True
except ImportError:
    RISK_REGISTER_AVAILABLE = False
    def generate_risk_register(*args, **kwargs): return {}
    def generate_risk_register_markdown(*args): return ""

# ── Phase 3 Connector Imports (Deep Intelligence) ────────────────────────────

try:
    from app.connectors.founder_track_record_connector import (
        get_founder_track_record,
        render_founder_track_record_markdown,
    )
    FOUNDER_TRACK_RECORD_AVAILABLE = True
except ImportError:
    FOUNDER_TRACK_RECORD_AVAILABLE = False
    def get_founder_track_record(*args, **kwargs): return {}
    def render_founder_track_record_markdown(*args): return []

try:
    from app.connectors.rumors_analysis_connector import (
        analyze_rumors_and_next_steps,
        render_rumors_analysis_markdown,
    )
    RUMORS_ANALYSIS_AVAILABLE = True
except ImportError:
    RUMORS_ANALYSIS_AVAILABLE = False
    def analyze_rumors_and_next_steps(*args, **kwargs): return {}
    def render_rumors_analysis_markdown(*args): return []

try:
    from app.services.contract_probability_service import (
        analyze_contract_probability,
        render_contract_probability_markdown,
    )
    CONTRACT_PROBABILITY_AVAILABLE = True
except ImportError:
    CONTRACT_PROBABILITY_AVAILABLE = False
    def analyze_contract_probability(*args, **kwargs): return {}
    def render_contract_probability_markdown(*args): return []

try:
    from app.services.deep_comparative_service import (
        run_deep_comparative_analysis,
        render_deep_comparative_markdown,
    )
    DEEP_COMPARATIVE_AVAILABLE = True
except ImportError:
    DEEP_COMPARATIVE_AVAILABLE = False
    def run_deep_comparative_analysis(*args, **kwargs): return {}
    def render_deep_comparative_markdown(*args): return []

try:
    from app.connectors.family_network_connector import (
        research_family_network,
        render_family_network_markdown,
    )
    FAMILY_NETWORK_AVAILABLE = True
except ImportError:
    FAMILY_NETWORK_AVAILABLE = False
    def research_family_network(*args, **kwargs): return {}
    def render_family_network_markdown(*args): return []


def _run_with_timeout(func, args=(), kwargs=None, timeout: int = 120):
    """Run a function with timeout, return None on error."""
    kwargs = kwargs or {}
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(func, *args, **kwargs)
            return future.result(timeout=timeout)
    except Exception as e:
        logger.warning("Deep research task failed: %s - %s", func.__name__, e)
        return None


def run_deep_intelligence(
    entity_name: str,
    ticker: str = "",
    entity_type: str = "org",
    competitors: List[str] = None,
    known_executives: List[str] = None,
    related_entities: List[str] = None,
    skip_linkedin: bool = False,
    skip_contracts: bool = False,
    skip_political: bool = False,
    skip_overlap: bool = False,
) -> Dict[str, Any]:
    """
    Run comprehensive deep intelligence research on an entity.

    Args:
        entity_name: Company or person name
        ticker: Stock ticker (for public companies)
        entity_type: "org" or "person"
        competitors: List of competitor tickers for overlap analysis
        known_executives: List of executive names to research
        related_entities: List of related entities for self-dealing detection
        skip_*: Flags to skip specific research areas

    Returns:
        Comprehensive deep intelligence payload with all findings.
    """
    start_time = time.time()
    competitors = competitors or []
    known_executives = known_executives or []
    related_entities = related_entities or []

    result = {
        "entity_name": entity_name,
        "ticker": ticker,
        "entity_type": entity_type,
        "research_scope": {
            "linkedin": not skip_linkedin and LINKEDIN_AVAILABLE,
            "contracts": not skip_contracts and FPDS_AVAILABLE,
            "political": not skip_political and OPENSECRETS_AVAILABLE,
            "institutional_overlap": not skip_overlap and OVERLAP_AVAILABLE and bool(ticker),
        },
        "personnel_intelligence": {},
        "contract_intelligence": {},
        "political_intelligence": {},
        "institutional_overlap": {},
        "cross_reference_findings": [],
        "risk_flags": [],
        "data_quality": {
            "sources_successful": 0,
            "sources_failed": 0,
            "total_data_points": 0,
        },
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }

    futures = {}

    with ThreadPoolExecutor(max_workers=4) as executor:
        # 1. LinkedIn Deep Research
        if result["research_scope"]["linkedin"]:
            logger.info("Starting LinkedIn deep research for %s", entity_name)
            futures["linkedin"] = executor.submit(
                deep_personnel_research,
                entity_name,
                ticker,
                "",  # company_linkedin_url
                known_executives,
            )

        # 2. FPDS Contract Research
        if result["research_scope"]["contracts"]:
            logger.info("Starting FPDS contract research for %s", entity_name)
            futures["contracts"] = executor.submit(
                get_full_contract_portfolio,
                entity_name,
                known_executives,
                related_entities,
            )

        # 3. Political Intelligence
        if result["research_scope"]["political"]:
            logger.info("Starting political intelligence for %s", entity_name)
            # We need executives for revolving door detection
            # This will run after linkedin if available, otherwise with empty list
            futures["political"] = executor.submit(
                get_political_intelligence,
                entity_name,
                [],  # Will be populated from linkedin results
                [2024, 2022, 2020],
            )

        # 4. Institutional Overlap (requires ticker)
        if result["research_scope"]["institutional_overlap"] and ticker and competitors:
            logger.info("Starting institutional overlap analysis for %s", ticker)
            futures["overlap"] = executor.submit(
                compare_competitor_ownership,
                ticker,
                competitors,
            )
        elif result["research_scope"]["institutional_overlap"] and ticker:
            logger.info("Starting mega holder analysis for %s", ticker)
            futures["mega_holders"] = executor.submit(
                get_mega_holder_positions,
                ticker,
            )

        # Collect results
        for key, future in futures.items():
            try:
                data = future.result(timeout=180)  # 3 minute timeout per task
                if data:
                    if key == "linkedin":
                        result["personnel_intelligence"] = data
                        result["data_quality"]["sources_successful"] += 1
                        result["data_quality"]["total_data_points"] += len(data.get("executive_dossiers", []))
                    elif key == "contracts":
                        result["contract_intelligence"] = data
                        result["data_quality"]["sources_successful"] += 1
                        result["data_quality"]["total_data_points"] += len(data.get("contracts", []))
                    elif key == "political":
                        result["political_intelligence"] = data
                        result["data_quality"]["sources_successful"] += 1
                    elif key in ("overlap", "mega_holders"):
                        result["institutional_overlap"] = data
                        result["data_quality"]["sources_successful"] += 1
                else:
                    result["data_quality"]["sources_failed"] += 1
            except Exception as e:
                logger.warning("Deep research task %s failed: %s", key, e)
                result["data_quality"]["sources_failed"] += 1

    # Cross-reference findings
    result["cross_reference_findings"] = _cross_reference_data(result)

    # Aggregate risk flags
    result["risk_flags"] = _aggregate_risk_flags(result)

    # Calculate research duration
    result["research_duration_seconds"] = round(time.time() - start_time, 2)

    return result


def _cross_reference_data(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Cross-reference findings across data sources to detect:
    - Connections between personnel and contract recipients
    - Overlap between lobbying targets and contract-awarding agencies
    - Revolving door + contract correlation
    """
    findings = []

    # Get data
    personnel = data.get("personnel_intelligence", {})
    contracts = data.get("contract_intelligence", {})
    political = data.get("political_intelligence", {})

    # 1. Check for lobbying ↔ contract agency correlation
    lobbying_issues = political.get("lobbying_summary", {}).get("top_issues", [])
    contract_agencies = contracts.get("agency_breakdown", [])

    lobbying_agencies = set()
    for issue in lobbying_issues:
        if isinstance(issue, tuple):
            issue_name = issue[0].lower()
        else:
            issue_name = str(issue).lower()
        # Extract agency hints from lobbying issues
        for agency_kw in ["defense", "commerce", "health", "energy", "treasury"]:
            if agency_kw in issue_name:
                lobbying_agencies.add(agency_kw)

    for agency_data in contract_agencies[:5]:
        agency_name = agency_data.get("agency", "").lower()
        for kw in lobbying_agencies:
            if kw in agency_name:
                findings.append({
                    "type": "lobbying_contract_correlation",
                    "severity": "MEDIUM",
                    "detail": f"Active lobbying on {kw} issues correlates with contracts from {agency_data.get('agency')}",
                    "contract_value": agency_data.get("amount", 0),
                })
                break

    # 2. Check for revolving door ↔ contract correlation
    revolving_door = political.get("revolving_door", [])
    for person in revolving_door:
        gov_entity = str(person.get("government_entity", "")).lower()
        for agency_data in contract_agencies:
            agency_name = agency_data.get("agency", "").lower()
            # Check if ex-government person's agency matches a contract agency
            for word in gov_entity.split():
                if len(word) > 4 and word in agency_name:
                    findings.append({
                        "type": "revolving_door_contract_match",
                        "severity": "HIGH",
                        "detail": f"{person.get('person')} previously at {person.get('government_entity')} — company has ${agency_data.get('amount', 0):,.0f} in contracts from {agency_data.get('agency')}",
                        "person": person.get("person"),
                        "government_role": person.get("government_role"),
                    })
                    break

    # 3. Check for board interlocks with self-dealing implications
    board_interlocks = personnel.get("board_analysis", {}).get("interlocks", [])
    for interlock in board_interlocks:
        findings.append({
            "type": "board_interlock",
            "severity": "MEDIUM",
            "detail": f"Board interlock detected: {interlock.get('count', 0)} directors share positions at {interlock.get('company')}",
            "shared_members": interlock.get("shared_members", []),
        })

    # 4. Check for family connections among executives
    family_connections = personnel.get("family_connections", [])
    for conn in family_connections:
        findings.append({
            "type": "family_connection",
            "severity": conn.get("flag_level", "MEDIUM"),
            "detail": conn.get("note", "Potential family relationship detected"),
            "people": conn.get("people", []),
        })

    return findings


def _aggregate_risk_flags(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Aggregate all risk flags from all data sources into unified list.
    """
    flags = []

    # Contract self-dealing flags
    contract_flags = data.get("contract_intelligence", {}).get("self_dealing_analysis", {}).get("flags", [])
    for flag in contract_flags:
        flags.append({
            **flag,
            "source": "contracts",
        })

    # Political risk flags
    political_risk = data.get("political_intelligence", {}).get("political_risk_assessment", {})
    if political_risk.get("overall_risk") == "HIGH":
        flags.append({
            "type": "political_risk",
            "severity": "HIGH",
            "detail": f"High political risk: {political_risk.get('lobbying_intensity')} lobbying, {political_risk.get('revolving_door_count')} revolving door hires",
            "source": "political",
        })

    # Institutional overlap flags
    overlap_flags = data.get("institutional_overlap", {}).get("risk_flags", [])
    for flag in overlap_flags:
        flags.append({
            **flag,
            "source": "institutional_overlap",
        })

    # Cross-reference findings that are high severity
    for finding in data.get("cross_reference_findings", []):
        if finding.get("severity") == "HIGH":
            flags.append({
                "type": finding.get("type"),
                "severity": "HIGH",
                "detail": finding.get("detail"),
                "source": "cross_reference",
            })

    # Sort by severity
    severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    flags.sort(key=lambda x: severity_order.get(x.get("severity", "LOW"), 2))

    return flags


def get_deep_intelligence_summary(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate executive summary of deep intelligence findings.
    """
    personnel = data.get("personnel_intelligence", {})
    contracts = data.get("contract_intelligence", {})
    political = data.get("political_intelligence", {})
    overlap = data.get("institutional_overlap", {})

    return {
        "entity_name": data.get("entity_name"),
        "ticker": data.get("ticker"),
        "key_findings": {
            "executives_profiled": len(personnel.get("executive_dossiers", [])),
            "board_members_found": personnel.get("research_stats", {}).get("board_members_found", 0),
            "board_interlocks": len(personnel.get("board_analysis", {}).get("interlocks", [])),
            "family_connections_flagged": len(personnel.get("family_connections", [])),
            "federal_contracts_total": contracts.get("summary", {}).get("total_obligated", 0),
            "federal_contracts_count": contracts.get("summary", {}).get("total_contracts", 0),
            "self_dealing_risk": contracts.get("self_dealing_analysis", {}).get("risk_level", "UNKNOWN"),
            "pac_total_contributions": political.get("pac_activity", {}).get("total_all_cycles", 0),
            "lobbying_total_spend": political.get("lobbying_summary", {}).get("total_spend", 0),
            "revolving_door_count": len(political.get("revolving_door", [])),
            "institutional_overlap_pct": overlap.get("overlap_analysis", {}).get("summary", {}).get("avg_overlap_pct", 0),
            "mega_holders": len(overlap.get("mega_positions", [])),
        },
        "risk_flags_count": len(data.get("risk_flags", [])),
        "high_severity_flags": len([f for f in data.get("risk_flags", []) if f.get("severity") == "HIGH"]),
        "cross_reference_findings": len(data.get("cross_reference_findings", [])),
        "research_duration_seconds": data.get("research_duration_seconds", 0),
        "data_quality": data.get("data_quality", {}),
    }


# ── Convenience Exports ──────────────────────────────────────────────────────

def run_deep_research(entity_name: str, ticker: str = "", competitors: List[str] = None) -> Dict[str, Any]:
    """Convenience wrapper for deep intelligence."""
    return run_deep_intelligence(entity_name, ticker=ticker, competitors=competitors)


def get_summary(data: Dict[str, Any]) -> Dict[str, Any]:
    """Get executive summary of deep intelligence."""
    return get_deep_intelligence_summary(data)


# ── Comprehensive Intelligence (Phase 2) ─────────────────────────────────────

def run_comprehensive_intelligence(
    entity_name: str,
    ticker: str = "",
    entity_type: str = "org",
    competitors: List[str] = None,
    known_executives: List[str] = None,
    related_entities: List[str] = None,
    years: int = 5,
) -> Dict[str, Any]:
    """
    Run FULL comprehensive intelligence research using all Phase 1 + Phase 2 connectors.

    This produces a complete intelligence package similar to the NVIDIA Intelligence Report,
    including:
    - All Phase 1 data (personnel, contracts, political, institutional)
    - SEC financial data (10-K/10-Q, XBRL, insider transactions)
    - Entity network mapping (family networks, cross-firm connections)
    - Proxy statement analysis (compensation, governance)
    - Litigation tracking (federal cases, SEC enforcement)
    - Event timeline
    - DCF valuation with scenarios
    - Comprehensive risk register

    Args:
        entity_name: Company or person name
        ticker: Stock ticker (for public companies)
        entity_type: "org" or "person"
        competitors: List of competitor tickers
        known_executives: List of executive names to research
        related_entities: List of related entities
        years: Years of history to analyze

    Returns:
        Comprehensive intelligence payload.
    """
    start_time = time.time()
    competitors = competitors or []
    known_executives = known_executives or []
    related_entities = related_entities or []

    # Start with Phase 1 research
    result = run_deep_intelligence(
        entity_name=entity_name,
        ticker=ticker,
        entity_type=entity_type,
        competitors=competitors,
        known_executives=known_executives,
        related_entities=related_entities,
    )

    # Expand research_scope to include Phase 2 and Phase 3
    result["research_scope"].update({
        "sec_edgar": SEC_EDGAR_AVAILABLE and bool(ticker),
        "entity_network": ENTITY_NETWORK_AVAILABLE,
        "proxy_analysis": PROXY_AVAILABLE and bool(ticker),
        "litigation": LITIGATION_AVAILABLE,
        "timeline": TIMELINE_AVAILABLE and bool(ticker),
        "valuation": VALUATION_AVAILABLE and bool(ticker),
        "risk_register": RISK_REGISTER_AVAILABLE,
        # Phase 3 - Deep Intelligence
        "founder_track_record": FOUNDER_TRACK_RECORD_AVAILABLE,
        "rumors_analysis": RUMORS_ANALYSIS_AVAILABLE,
        "contract_probability": CONTRACT_PROBABILITY_AVAILABLE,
        "deep_comparative": DEEP_COMPARATIVE_AVAILABLE and bool(competitors),
        "family_network": FAMILY_NETWORK_AVAILABLE,
    })

    # Initialize Phase 2 and Phase 3 result fields
    result.update({
        # Phase 2
        "financial_intelligence": {},
        "insider_transactions": {},
        "institutional_holdings": {},
        "entity_network": {},
        "proxy_intelligence": {},
        "litigation_intelligence": {},
        "event_timeline": {},
        "valuation_analysis": {},
        "filing_notes": {},
        "beneficial_ownership": {},
        "board_interlocks": {},
        "price_history": {},
        "risk_register": {},
        # Phase 3 - Deep Intelligence
        "founder_track_record": {},
        "rumors_analysis": {},
        "contract_probability": {},
        "deep_comparative": {},
        "family_network": {},
    })

    futures = {}

    with ThreadPoolExecutor(max_workers=8) as executor:
        # 1. SEC EDGAR Financial Data
        if result["research_scope"]["sec_edgar"]:
            logger.info("Starting SEC EDGAR financial analysis for %s", ticker)
            futures["sec_edgar"] = executor.submit(
                get_full_financial_profile,
                ticker,
            )

        # 2. Insider Transactions and institutional ownership
        if result["research_scope"]["sec_edgar"]:
            logger.info("Starting insider transaction analysis for %s", ticker)
            cik = get_filer_cik(ticker)
            if cik:
                futures["insider"] = executor.submit(get_insider_transactions, cik)
                futures["filing_notes"] = executor.submit(get_filing_notes, cik)
                # Share count and price let the 13F layer express positions as a
                # percentage of shares outstanding and resolve the units each
                # manager reported values in.
                quote = {}
                try:
                    from app.connectors.market_data_connector import (
                        get_quote, get_price_history,
                    )
                    quote = get_quote(ticker) or {}
                except Exception as e:
                    logger.warning("Quote unavailable for %s: %s", ticker, e)
                try:
                    from app.connectors.market_data_connector import get_price_history
                    futures["price_history"] = executor.submit(
                        get_price_history, ticker, 400)
                except Exception as e:
                    logger.warning("Price history unavailable for %s: %s", ticker, e)
                futures["institutional"] = executor.submit(
                    get_institutional_holders, entity_name, ticker,
                    quote.get("shares_outstanding"), quote.get("price"))
                futures["beneficial_owners"] = executor.submit(
                    get_beneficial_owners, cik)
            else:
                logger.warning("No CIK for %s; skipping insider and 13F analysis",
                               ticker)

        # 3. Entity Network (for CEO/key executives)
        if result["research_scope"]["entity_network"] and entity_type == "org":
            # Get key executive for network analysis
            exec_dossiers = result.get("personnel_intelligence", {}).get("executive_dossiers", [])
            ceo_name = None
            for dossier in exec_dossiers:
                title = dossier.get("title", "").lower()
                if "ceo" in title or "chief executive" in title:
                    ceo_name = dossier.get("name")
                    break

            if ceo_name:
                logger.info("Starting entity network analysis for %s", ceo_name)
                futures["entity_network"] = executor.submit(
                    discover_family_network,
                    ceo_name,
                    [entity_name],  # Known associations
                )

        # 4. Proxy Statement Analysis
        if result["research_scope"]["proxy_analysis"]:
            logger.info("Starting proxy statement analysis for %s", ticker)
            futures["proxy"] = executor.submit(
                get_proxy_intelligence,
                ticker,
                years=min(years, 3),  # Proxy analysis limited to 3 years
            )

        # 5. Litigation Tracking
        if result["research_scope"]["litigation"]:
            logger.info("Starting litigation analysis for %s", entity_name)
            futures["litigation"] = executor.submit(
                get_litigation_intelligence,
                entity_name,
                ticker,
                years,
            )

        # 6. Event Timeline
        if result["research_scope"]["timeline"]:
            logger.info("Starting timeline generation for %s", ticker)
            futures["timeline"] = executor.submit(
                generate_entity_timeline,
                ticker,
                years=min(years, 2),  # Timeline limited to 2 years
            )

        # 7. Valuation Analysis
        if result["research_scope"]["valuation"]:
            logger.info("Starting valuation analysis for %s", ticker)
            futures["valuation"] = executor.submit(
                full_valuation_report,
                ticker,
            )

        # ── Phase 3 Research Tasks ──────────────────────────────────────────

        # 8. Founder Track Record (books, interviews, prior ventures)
        if result["research_scope"]["founder_track_record"]:
            # Get executives from personnel intelligence or proxy
            exec_dossiers = result.get("personnel_intelligence", {}).get("executive_dossiers", [])
            if exec_dossiers:
                logger.info("Starting founder track record research for %s", entity_name)
                futures["founder_track_record"] = executor.submit(
                    get_founder_track_record,
                    exec_dossiers,
                    entity_name,
                    ticker,
                    True,  # deep_search
                )

        # 9. Rumors and Next Steps Analysis
        if result["research_scope"]["rumors_analysis"]:
            logger.info("Starting rumors analysis for %s", ticker or entity_name)
            futures["rumors_analysis"] = executor.submit(
                analyze_rumors_and_next_steps,
                entity_name,
                ticker,
                30,  # days_back
                True,  # include_social
            )

        # 10. Contract Probability Analysis
        if result["research_scope"]["contract_probability"]:
            logger.info("Starting contract probability analysis for %s", entity_name)
            futures["contract_probability"] = executor.submit(
                analyze_contract_probability,
                entity_name,
                ticker,
                None,  # naics_codes
                None,  # keywords
                None,  # total_revenue
            )

        # 11. Deep Comparative Analysis
        if result["research_scope"]["deep_comparative"] and competitors:
            logger.info("Starting deep comparative analysis for %s vs %s", ticker, competitors)
            futures["deep_comparative"] = executor.submit(
                run_deep_comparative_analysis,
                ticker,
                competitors,
                None,  # target_cik
            )

        # 12. Family Network Analysis
        if result["research_scope"]["family_network"]:
            logger.info("Starting family network analysis for %s", entity_name)
            futures["family_network"] = executor.submit(
                research_family_network,
                entity_name,
                ticker,
            )

        # Collect Phase 2 and Phase 3 results
        for key, future in futures.items():
            try:
                data = future.result(timeout=180)
                if data:
                    if key == "sec_edgar":
                        result["financial_intelligence"] = data
                        result["data_quality"]["sources_successful"] += 1
                    elif key == "insider":
                        result["insider_transactions"] = data
                        result["data_quality"]["sources_successful"] += 1
                    elif key == "institutional":
                        result["institutional_holdings"] = data
                        result["data_quality"]["sources_successful"] += 1
                    elif key == "entity_network":
                        result["entity_network"] = data
                        result["data_quality"]["sources_successful"] += 1
                    elif key == "proxy":
                        result["proxy_intelligence"] = data
                        result["data_quality"]["sources_successful"] += 1
                    elif key == "litigation":
                        result["litigation_intelligence"] = data
                        result["data_quality"]["sources_successful"] += 1
                    elif key == "timeline":
                        result["event_timeline"] = data
                        result["data_quality"]["sources_successful"] += 1
                    elif key == "valuation":
                        result["valuation_analysis"] = data
                        result["data_quality"]["sources_successful"] += 1
                    elif key == "filing_notes":
                        result["filing_notes"] = data
                        result["data_quality"]["sources_successful"] += 1
                    elif key == "beneficial_owners":
                        result["beneficial_ownership"] = data
                        result["data_quality"]["sources_successful"] += 1
                    elif key == "price_history":
                        result["price_history"] = data
                        result["data_quality"]["sources_successful"] += 1
                    # Phase 3 results
                    elif key == "founder_track_record":
                        result["founder_track_record"] = data
                        result["data_quality"]["sources_successful"] += 1
                    elif key == "rumors_analysis":
                        result["rumors_analysis"] = data
                        result["data_quality"]["sources_successful"] += 1
                    elif key == "contract_probability":
                        result["contract_probability"] = data
                        result["data_quality"]["sources_successful"] += 1
                    elif key == "deep_comparative":
                        result["deep_comparative"] = data
                        result["data_quality"]["sources_successful"] += 1
                    elif key == "family_network":
                        result["family_network"] = data
                        result["data_quality"]["sources_successful"] += 1
                else:
                    result["data_quality"]["sources_failed"] += 1
            except Exception as e:
                logger.warning("Research task %s failed: %s", key, e)
                result["data_quality"]["sources_failed"] += 1

    # Board interlocks run after the Form 4 sweep rather than beside it: the
    # reporting owner's CIK comes out of those filings, and it is the key that
    # locates each person's other issuers.
    if BOARD_INTERLOCK_AVAILABLE and result.get("insider_transactions"):
        cik = get_filer_cik(ticker) if ticker else None
        if cik:
            logger.info("Starting board interlock analysis for %s", ticker)
            try:
                result["board_interlocks"] = get_board_interlocks(
                    result["insider_transactions"].get("transactions", []),
                    cik, entity_name)
                result["data_quality"]["sources_successful"] += 1
            except Exception as e:
                logger.warning("Board interlock analysis failed: %s", e)
                result["data_quality"]["sources_failed"] += 1

    # 8. Generate Risk Register (requires all other data)
    if result["research_scope"]["risk_register"]:
        logger.info("Generating risk register for %s", entity_name)
        try:
            result["risk_register"] = generate_risk_register(
                entity_name=entity_name,
                ticker=ticker,
                all_data={
                    "financial_data": result.get("financial_intelligence", {}),
                    "personnel_intelligence": result.get("personnel_intelligence", {}),
                    "contract_intelligence": result.get("contract_intelligence", {}),
                    "political_intelligence": result.get("political_intelligence", {}),
                    "proxy_intelligence": result.get("proxy_intelligence", {}),
                    "litigation_intelligence": result.get("litigation_intelligence", {}),
                    "valuation_data": result.get("valuation_analysis", {}).get("dcf", {}),
                },
            )
            result["data_quality"]["sources_successful"] += 1
        except Exception as e:
            logger.warning("Risk register generation failed: %s", e)
            result["data_quality"]["sources_failed"] += 1

    # Update total research duration
    result["research_duration_seconds"] = round(time.time() - start_time, 2)

    # Add research version
    result["research_version"] = "3.0"
    result["phase"] = "comprehensive_deep_intelligence"

    return result


def get_comprehensive_summary(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate executive summary of comprehensive intelligence findings.
    """
    basic_summary = get_deep_intelligence_summary(data)

    # Add Phase 2 summary data
    financial = data.get("financial_intelligence", {})
    proxy = data.get("proxy_intelligence", {})
    litigation = data.get("litigation_intelligence", {})
    valuation = data.get("valuation_analysis", {})
    risk_register = data.get("risk_register", {})

    basic_summary["phase2_findings"] = {
        # Financial
        "revenue_ttm": financial.get("income_statement", {}).get("revenue", 0),
        "net_income_ttm": financial.get("income_statement", {}).get("net_income", 0),

        # Proxy/Governance
        "ceo_compensation": 0,  # Would be extracted from proxy
        "say_on_pay_approval": proxy.get("say_on_pay", {}).get("approval_pct", 0),
        "related_party_transactions": len(proxy.get("related_party_transactions", [])),

        # Litigation
        "total_legal_matters": litigation.get("summary", {}).get("total_matters", 0),
        "active_legal_matters": litigation.get("summary", {}).get("active_matters", 0),
        "litigation_risk": litigation.get("risk_assessment", {}).get("overall_risk", "UNKNOWN"),

        # Valuation
        "intrinsic_value": valuation.get("dcf", {}).get("intrinsic_price_per_share", 0),
        "current_price": valuation.get("dcf", {}).get("current_market_price", 0),
        "valuation_assessment": valuation.get("dcf", {}).get("assessment", "UNKNOWN"),

        # Risk
        "overall_risk_profile": risk_register.get("summary", {}).get("overall_risk_profile", "UNKNOWN"),
        "critical_risks": risk_register.get("summary", {}).get("critical_risks", 0),
        "high_risks": risk_register.get("summary", {}).get("high_risks", 0),
    }

    basic_summary["research_version"] = data.get("research_version", "1.0")
    basic_summary["phase"] = data.get("phase", "basic")

    return basic_summary


# ── Availability Check ───────────────────────────────────────────────────────

def check_connector_availability() -> Dict[str, bool]:
    """Check which deep research connectors are available."""
    return {
        # Phase 1
        "linkedin_deep": LINKEDIN_AVAILABLE,
        "fpds_contracts": FPDS_AVAILABLE,
        "opensecrets_political": OPENSECRETS_AVAILABLE,
        "institutional_overlap": OVERLAP_AVAILABLE,
        # Phase 2
        "sec_edgar": SEC_EDGAR_AVAILABLE,
        "entity_network": ENTITY_NETWORK_AVAILABLE,
        "proxy_statement": PROXY_AVAILABLE,
        "litigation": LITIGATION_AVAILABLE,
        "timeline": TIMELINE_AVAILABLE,
        "valuation": VALUATION_AVAILABLE,
        "risk_register": RISK_REGISTER_AVAILABLE,
        # Phase 3 - Deep Intelligence
        "founder_track_record": FOUNDER_TRACK_RECORD_AVAILABLE,
        "rumors_analysis": RUMORS_ANALYSIS_AVAILABLE,
        "contract_probability": CONTRACT_PROBABILITY_AVAILABLE,
        "deep_comparative": DEEP_COMPARATIVE_AVAILABLE,
        "family_network": FAMILY_NETWORK_AVAILABLE,
    }


def get_connector_status() -> Dict[str, Any]:
    """Get detailed connector status with version info."""
    availability = check_connector_availability()

    phase1_count = sum([
        availability["linkedin_deep"],
        availability["fpds_contracts"],
        availability["opensecrets_political"],
        availability["institutional_overlap"],
    ])

    phase2_count = sum([
        availability["sec_edgar"],
        availability["entity_network"],
        availability["proxy_statement"],
        availability["litigation"],
        availability["timeline"],
        availability["valuation"],
        availability["risk_register"],
    ])

    phase3_count = sum([
        availability["founder_track_record"],
        availability["rumors_analysis"],
        availability["contract_probability"],
        availability["deep_comparative"],
        availability["family_network"],
    ])

    return {
        "availability": availability,
        "phase1_connectors": phase1_count,
        "phase2_connectors": phase2_count,
        "phase3_connectors": phase3_count,
        "total_available": phase1_count + phase2_count + phase3_count,
        "comprehensive_ready": phase2_count >= 5,
        "deep_intelligence_ready": phase3_count >= 3,
        "version": "3.0",
    }
