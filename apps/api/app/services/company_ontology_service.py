"""
Company-Specific Ontology + KPI Schema Service (Band B #16)
────────────────────────────────────────────────────────────────────────────
Provides per-company semantic understanding:
  - Custom ontology extraction from filings and documents
  - KPI schema definition and tracking
  - Entity relationship mapping
  - Metric hierarchy and derivation rules
  - Industry-specific terminology mapping

Enables RAG systems to understand company-specific concepts.
"""

import os
import re
import json
import logging
import hashlib
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict, field
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of KPI metrics."""
    FINANCIAL = "financial"
    OPERATIONAL = "operational"
    STRATEGIC = "strategic"
    RISK = "risk"
    ESG = "esg"
    CUSTOM = "custom"


class AggregationType(Enum):
    """How metrics should be aggregated."""
    SUM = "sum"
    AVERAGE = "average"
    LATEST = "latest"
    CUMULATIVE = "cumulative"
    YOY_GROWTH = "yoy_growth"
    QOQ_GROWTH = "qoq_growth"


class DataFrequency(Enum):
    """Reporting frequency for metrics."""
    REALTIME = "realtime"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


@dataclass
class KPIDefinition:
    """Definition of a company-specific KPI."""
    id: str
    name: str
    description: str
    metric_type: MetricType
    unit: str
    formula: Optional[str] = None
    components: List[str] = field(default_factory=list)
    aggregation: AggregationType = AggregationType.LATEST
    frequency: DataFrequency = DataFrequency.QUARTERLY
    source_tags: List[str] = field(default_factory=list)
    xbrl_concepts: List[str] = field(default_factory=list)
    industry_benchmark: Optional[float] = None
    target_value: Optional[float] = None
    higher_is_better: bool = True
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class EntityConcept:
    """A concept/entity in the company ontology."""
    id: str
    name: str
    aliases: List[str]
    entity_type: str  # segment, product, region, customer, supplier, competitor, etc.
    parent_id: Optional[str] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    relationships: List[Dict[str, str]] = field(default_factory=list)
    source_filing: Optional[str] = None
    confidence: float = 1.0


@dataclass
class CompanyOntology:
    """Complete ontology for a company."""
    ticker: str
    company_name: str
    cik: str
    industry: str
    sic_code: str
    created_at: str
    updated_at: str

    # Core ontology components
    entities: List[EntityConcept] = field(default_factory=list)
    kpis: List[KPIDefinition] = field(default_factory=list)
    terminology: Dict[str, str] = field(default_factory=dict)  # Company-specific term -> standard term
    relationships: List[Dict[str, Any]] = field(default_factory=list)

    # Metadata
    sources_analyzed: List[str] = field(default_factory=list)
    version: str = "1.0"


# ── Industry-specific KPI templates ────────────────────────────────────────────

INDUSTRY_KPI_TEMPLATES = {
    "technology": [
        KPIDefinition(
            id="arr", name="Annual Recurring Revenue", description="Total recurring revenue annualized",
            metric_type=MetricType.FINANCIAL, unit="USD", aggregation=AggregationType.LATEST,
            frequency=DataFrequency.QUARTERLY, higher_is_better=True,
            xbrl_concepts=["RevenueFromContractWithCustomer", "RecurringRevenue"],
        ),
        KPIDefinition(
            id="dau", name="Daily Active Users", description="Unique users active per day",
            metric_type=MetricType.OPERATIONAL, unit="users", aggregation=AggregationType.AVERAGE,
            frequency=DataFrequency.DAILY, higher_is_better=True,
        ),
        KPIDefinition(
            id="nrr", name="Net Revenue Retention", description="Revenue retention including expansion",
            metric_type=MetricType.OPERATIONAL, unit="percent", aggregation=AggregationType.LATEST,
            frequency=DataFrequency.QUARTERLY, higher_is_better=True, industry_benchmark=120.0,
        ),
        KPIDefinition(
            id="cac", name="Customer Acquisition Cost", description="Cost to acquire one customer",
            metric_type=MetricType.FINANCIAL, unit="USD", aggregation=AggregationType.AVERAGE,
            frequency=DataFrequency.QUARTERLY, higher_is_better=False,
        ),
        KPIDefinition(
            id="ltv", name="Customer Lifetime Value", description="Total value from a customer relationship",
            metric_type=MetricType.FINANCIAL, unit="USD", aggregation=AggregationType.AVERAGE,
            frequency=DataFrequency.QUARTERLY, higher_is_better=True,
        ),
    ],
    "semiconductor": [
        KPIDefinition(
            id="data_center_revenue", name="Data Center Revenue", description="Revenue from data center segment",
            metric_type=MetricType.FINANCIAL, unit="USD", aggregation=AggregationType.SUM,
            frequency=DataFrequency.QUARTERLY, higher_is_better=True,
            source_tags=["segment_revenue", "data_center"],
        ),
        KPIDefinition(
            id="gaming_revenue", name="Gaming Revenue", description="Revenue from gaming segment",
            metric_type=MetricType.FINANCIAL, unit="USD", aggregation=AggregationType.SUM,
            frequency=DataFrequency.QUARTERLY, higher_is_better=True,
        ),
        KPIDefinition(
            id="gross_margin", name="Gross Margin", description="Gross profit as percentage of revenue",
            metric_type=MetricType.FINANCIAL, unit="percent", aggregation=AggregationType.LATEST,
            frequency=DataFrequency.QUARTERLY, higher_is_better=True,
            xbrl_concepts=["GrossProfit", "Revenues"],
            formula="GrossProfit / Revenues * 100",
        ),
        KPIDefinition(
            id="rd_intensity", name="R&D Intensity", description="R&D spending as percentage of revenue",
            metric_type=MetricType.STRATEGIC, unit="percent", aggregation=AggregationType.LATEST,
            frequency=DataFrequency.QUARTERLY, higher_is_better=True,
            formula="ResearchAndDevelopmentExpense / Revenues * 100",
        ),
    ],
    "retail": [
        KPIDefinition(
            id="same_store_sales", name="Same-Store Sales Growth", description="Sales growth from existing stores",
            metric_type=MetricType.OPERATIONAL, unit="percent", aggregation=AggregationType.LATEST,
            frequency=DataFrequency.QUARTERLY, higher_is_better=True,
        ),
        KPIDefinition(
            id="inventory_turnover", name="Inventory Turnover", description="How quickly inventory is sold",
            metric_type=MetricType.OPERATIONAL, unit="turns", aggregation=AggregationType.LATEST,
            frequency=DataFrequency.QUARTERLY, higher_is_better=True,
            formula="CostOfGoodsSold / AverageInventory",
        ),
        KPIDefinition(
            id="revenue_per_sqft", name="Revenue per Square Foot", description="Sales productivity measure",
            metric_type=MetricType.OPERATIONAL, unit="USD/sqft", aggregation=AggregationType.LATEST,
            frequency=DataFrequency.QUARTERLY, higher_is_better=True,
        ),
    ],
    "banking": [
        KPIDefinition(
            id="nim", name="Net Interest Margin", description="Difference between interest income and expense",
            metric_type=MetricType.FINANCIAL, unit="percent", aggregation=AggregationType.LATEST,
            frequency=DataFrequency.QUARTERLY, higher_is_better=True,
            xbrl_concepts=["InterestIncomeExpenseNet", "InterestBearingAssets"],
        ),
        KPIDefinition(
            id="efficiency_ratio", name="Efficiency Ratio", description="Operating expenses / Revenue",
            metric_type=MetricType.OPERATIONAL, unit="percent", aggregation=AggregationType.LATEST,
            frequency=DataFrequency.QUARTERLY, higher_is_better=False,
        ),
        KPIDefinition(
            id="npl_ratio", name="Non-Performing Loan Ratio", description="NPLs as percentage of total loans",
            metric_type=MetricType.RISK, unit="percent", aggregation=AggregationType.LATEST,
            frequency=DataFrequency.QUARTERLY, higher_is_better=False,
        ),
        KPIDefinition(
            id="cet1_ratio", name="CET1 Capital Ratio", description="Common Equity Tier 1 capital ratio",
            metric_type=MetricType.RISK, unit="percent", aggregation=AggregationType.LATEST,
            frequency=DataFrequency.QUARTERLY, higher_is_better=True, industry_benchmark=10.0,
        ),
    ],
}

# ── SIC code to industry mapping ────────────────────────────────────────────────

SIC_TO_INDUSTRY = {
    "3674": "semiconductor",
    "7370": "technology",
    "7372": "technology",
    "7373": "technology",
    "5331": "retail",
    "5411": "retail",
    "5912": "retail",
    "6021": "banking",
    "6022": "banking",
    "6211": "banking",
    "6282": "asset_management",
}


def get_industry_from_sic(sic_code: str) -> str:
    """Map SIC code to industry category."""
    return SIC_TO_INDUSTRY.get(sic_code, "general")


def build_company_ontology(
    ticker: str,
    include_kpis: bool = True,
    include_entities: bool = True,
    include_terminology: bool = True,
) -> CompanyOntology:
    """
    Build a complete ontology for a company.

    Args:
        ticker: Stock ticker symbol
        include_kpis: Whether to extract KPI definitions
        include_entities: Whether to extract entity concepts
        include_terminology: Whether to build terminology mapping

    Returns:
        CompanyOntology object with all extracted information
    """
    from app.connectors.sec_edgar_connector import (
        get_filer_cik,
        get_company_submissions,
        extract_financial_statements,
        get_segment_data,
    )
    from app.connectors.filing_notes_connector import get_filing_notes

    logger.info(f"Building ontology for {ticker}")

    # Resolve company info
    cik = get_filer_cik(ticker)
    if not cik:
        raise ValueError(f"Could not resolve CIK for ticker: {ticker}")

    submissions = get_company_submissions(cik)
    if not submissions:
        raise ValueError(f"Could not fetch submissions for CIK: {cik}")

    company_name = submissions.get("name", ticker)
    sic_code = submissions.get("sicDescription", "")

    # Try to extract SIC code from description or use default
    sic_match = re.search(r'\d{4}', str(submissions.get("sic", "")))
    sic_code = sic_match.group(0) if sic_match else "9999"

    industry = get_industry_from_sic(sic_code)

    now = datetime.utcnow().isoformat()
    ontology = CompanyOntology(
        ticker=ticker,
        company_name=company_name,
        cik=cik,
        industry=industry,
        sic_code=sic_code,
        created_at=now,
        updated_at=now,
    )

    # Extract KPIs
    if include_kpis:
        ontology.kpis = _extract_kpis(ticker, industry, submissions)

    # Extract entities
    if include_entities:
        ontology.entities = _extract_entities(ticker, submissions)

    # Build terminology
    if include_terminology:
        ontology.terminology = _build_terminology(ticker, company_name, industry)

    ontology.sources_analyzed = _get_analyzed_sources(submissions)

    return ontology


def _extract_kpis(
    ticker: str,
    industry: str,
    submissions: Dict[str, Any],
) -> List[KPIDefinition]:
    """Extract KPI definitions for a company."""
    kpis = []

    # Start with industry template
    if industry in INDUSTRY_KPI_TEMPLATES:
        kpis.extend(INDUSTRY_KPI_TEMPLATES[industry])

    # Add universal KPIs
    universal_kpis = [
        KPIDefinition(
            id="revenue", name="Total Revenue", description="Total company revenue",
            metric_type=MetricType.FINANCIAL, unit="USD", aggregation=AggregationType.SUM,
            frequency=DataFrequency.QUARTERLY, higher_is_better=True,
            xbrl_concepts=["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax"],
        ),
        KPIDefinition(
            id="net_income", name="Net Income", description="Bottom-line profit",
            metric_type=MetricType.FINANCIAL, unit="USD", aggregation=AggregationType.SUM,
            frequency=DataFrequency.QUARTERLY, higher_is_better=True,
            xbrl_concepts=["NetIncomeLoss"],
        ),
        KPIDefinition(
            id="operating_income", name="Operating Income", description="Income from operations",
            metric_type=MetricType.FINANCIAL, unit="USD", aggregation=AggregationType.SUM,
            frequency=DataFrequency.QUARTERLY, higher_is_better=True,
            xbrl_concepts=["OperatingIncomeLoss"],
        ),
        KPIDefinition(
            id="fcf", name="Free Cash Flow", description="Cash flow available for distribution",
            metric_type=MetricType.FINANCIAL, unit="USD", aggregation=AggregationType.SUM,
            frequency=DataFrequency.QUARTERLY, higher_is_better=True,
            formula="OperatingCashFlow - CapitalExpenditures",
        ),
        KPIDefinition(
            id="revenue_growth", name="Revenue Growth", description="Year-over-year revenue growth",
            metric_type=MetricType.FINANCIAL, unit="percent", aggregation=AggregationType.YOY_GROWTH,
            frequency=DataFrequency.QUARTERLY, higher_is_better=True,
        ),
    ]
    kpis.extend(universal_kpis)

    # Extract company-specific metrics from MD&A
    custom_kpis = _extract_custom_kpis_from_filings(ticker)
    kpis.extend(custom_kpis)

    # Deduplicate by ID
    seen = set()
    unique_kpis = []
    for kpi in kpis:
        if kpi.id not in seen:
            seen.add(kpi.id)
            unique_kpis.append(kpi)

    return unique_kpis


def _extract_custom_kpis_from_filings(ticker: str) -> List[KPIDefinition]:
    """Extract company-specific KPIs mentioned in filings."""
    custom_kpis = []

    # Common non-GAAP metrics to look for
    non_gaap_patterns = [
        (r"adjusted\s+ebitda", "adjusted_ebitda", "Adjusted EBITDA"),
        (r"non-gaap\s+operating\s+income", "non_gaap_op_income", "Non-GAAP Operating Income"),
        (r"free\s+cash\s+flow", "free_cash_flow", "Free Cash Flow"),
        (r"organic\s+revenue\s+growth", "organic_growth", "Organic Revenue Growth"),
        (r"bookings", "bookings", "Bookings"),
        (r"backlog", "backlog", "Backlog"),
        (r"deferred\s+revenue", "deferred_revenue", "Deferred Revenue"),
        (r"remaining\s+performance\s+obligations?", "rpo", "Remaining Performance Obligations"),
        (r"billings", "billings", "Billings"),
        (r"annual\s+contract\s+value", "acv", "Annual Contract Value"),
        (r"total\s+contract\s+value", "tcv", "Total Contract Value"),
    ]

    # TODO: Actually parse filings to find these
    # For now, add common ones based on ticker patterns

    if ticker.upper() in ["NVDA", "AMD", "INTC"]:
        custom_kpis.append(KPIDefinition(
            id="data_center_segment",
            name="Data Center Segment Revenue",
            description="Revenue from data center products and services",
            metric_type=MetricType.FINANCIAL,
            unit="USD",
            aggregation=AggregationType.SUM,
            frequency=DataFrequency.QUARTERLY,
            higher_is_better=True,
            source_tags=["segment", "data_center"],
        ))

    return custom_kpis


def _extract_entities(
    ticker: str,
    submissions: Dict[str, Any],
) -> List[EntityConcept]:
    """Extract entity concepts from company filings."""
    from app.connectors.sec_edgar_connector import get_segment_data

    entities = []

    # Get segment data
    try:
        segments = get_segment_data(ticker)

        # Extract business segments
        if segments.get("revenue_by_segment"):
            for seg_name, revenue in segments["revenue_by_segment"].items():
                entities.append(EntityConcept(
                    id=f"segment_{_slugify(seg_name)}",
                    name=seg_name,
                    aliases=[],
                    entity_type="segment",
                    attributes={"revenue": revenue, "segment_type": "business"},
                    confidence=0.95,
                ))

        # Extract geographic regions
        if segments.get("geographic_revenue"):
            for region_name, revenue in segments["geographic_revenue"].items():
                entities.append(EntityConcept(
                    id=f"region_{_slugify(region_name)}",
                    name=region_name,
                    aliases=[],
                    entity_type="region",
                    attributes={"revenue": revenue},
                    confidence=0.95,
                ))

        # Extract major customers
        if segments.get("customer_concentration"):
            for customer in segments.get("customer_concentration", []):
                if isinstance(customer, dict):
                    entities.append(EntityConcept(
                        id=f"customer_{_slugify(customer.get('name', 'unknown'))}",
                        name=customer.get("name", "Unknown"),
                        aliases=[],
                        entity_type="customer",
                        attributes={
                            "concentration_pct": customer.get("pct"),
                            "segment": customer.get("segment"),
                        },
                        confidence=0.9,
                    ))

    except Exception as e:
        logger.warning(f"Error extracting segments for {ticker}: {e}")

    return entities


def _build_terminology(
    ticker: str,
    company_name: str,
    industry: str,
) -> Dict[str, str]:
    """Build terminology mapping for company-specific terms."""
    terminology = {}

    # Company name variations
    name_parts = company_name.split()
    if len(name_parts) > 1:
        terminology[name_parts[0].lower()] = company_name
        terminology[ticker.lower()] = company_name

    # Industry-specific terminology
    industry_terms = {
        "semiconductor": {
            "gpu": "Graphics Processing Unit",
            "cuda": "Compute Unified Device Architecture",
            "tensor core": "Matrix multiplication unit",
            "wafer": "Silicon wafer for chip manufacturing",
            "node": "Process technology node (e.g., 7nm)",
            "fabless": "Chip designer without manufacturing",
        },
        "technology": {
            "arr": "Annual Recurring Revenue",
            "mrr": "Monthly Recurring Revenue",
            "churn": "Customer attrition rate",
            "nrr": "Net Revenue Retention",
            "dau": "Daily Active Users",
            "mau": "Monthly Active Users",
            "saas": "Software as a Service",
            "arpu": "Average Revenue Per User",
        },
        "banking": {
            "nim": "Net Interest Margin",
            "npa": "Non-Performing Assets",
            "npl": "Non-Performing Loans",
            "casa": "Current Account Savings Account ratio",
            "cet1": "Common Equity Tier 1",
            "lcr": "Liquidity Coverage Ratio",
        },
        "retail": {
            "comps": "Comparable store sales",
            "sss": "Same-store sales",
            "gmv": "Gross Merchandise Value",
            "aov": "Average Order Value",
            "sqft": "Square footage",
        },
    }

    if industry in industry_terms:
        terminology.update(industry_terms[industry])

    return terminology


def _get_analyzed_sources(submissions: Dict[str, Any]) -> List[str]:
    """Get list of sources analyzed for ontology building."""
    sources = []

    filings = submissions.get("filings", {}).get("recent", {})
    forms = filings.get("form", [])
    dates = filings.get("filingDate", [])

    # Get most recent of each form type
    seen_forms = set()
    for i, form in enumerate(forms[:50]):
        if form not in seen_forms and form in ["10-K", "10-Q", "8-K", "DEF 14A"]:
            seen_forms.add(form)
            date = dates[i] if i < len(dates) else "unknown"
            sources.append(f"{form} ({date})")

    return sources


def _slugify(text: str) -> str:
    """Convert text to slug format."""
    return re.sub(r'[^a-z0-9]+', '_', text.lower()).strip('_')


# ── KPI Calculation Engine ────────────────────────────────────────────────────

def calculate_kpi(
    kpi: KPIDefinition,
    financial_data: Dict[str, Any],
    period: str = "latest",
) -> Optional[Dict[str, Any]]:
    """
    Calculate a KPI value from financial data.

    Args:
        kpi: The KPI definition
        financial_data: Financial statements data
        period: Which period to calculate for

    Returns:
        Dict with value, formatted value, and metadata
    """
    if not kpi.formula and not kpi.xbrl_concepts:
        return None

    value = None

    # Try to get value from XBRL concepts
    if kpi.xbrl_concepts:
        for concept in kpi.xbrl_concepts:
            for section in ["income_statement", "balance_sheet", "cash_flow", "metrics"]:
                section_data = financial_data.get(section, [])
                if isinstance(section_data, list) and section_data:
                    latest = section_data[0]
                    if concept in latest:
                        value = latest[concept]
                        break
                elif isinstance(section_data, dict):
                    if concept in section_data:
                        value = section_data[concept]
                        break
            if value is not None:
                break

    # Try to calculate from formula
    if value is None and kpi.formula:
        try:
            # Build variable context
            context = {}
            for section in ["income_statement", "balance_sheet", "cash_flow"]:
                section_data = financial_data.get(section, [])
                if isinstance(section_data, list) and section_data:
                    context.update(section_data[0])
                elif isinstance(section_data, dict):
                    context.update(section_data)

            # Safe eval of formula (only allow math operations)
            allowed_names = {k: v for k, v in context.items() if isinstance(v, (int, float))}
            value = eval(kpi.formula, {"__builtins__": {}}, allowed_names)
        except Exception as e:
            logger.debug(f"Could not calculate {kpi.id}: {e}")

    if value is None:
        return None

    # Format value
    formatted = _format_kpi_value(value, kpi.unit)

    # Calculate vs benchmark/target
    vs_benchmark = None
    if kpi.industry_benchmark and isinstance(value, (int, float)):
        vs_benchmark = value - kpi.industry_benchmark

    vs_target = None
    if kpi.target_value and isinstance(value, (int, float)):
        vs_target = value - kpi.target_value

    return {
        "kpi_id": kpi.id,
        "name": kpi.name,
        "value": value,
        "formatted": formatted,
        "unit": kpi.unit,
        "vs_benchmark": vs_benchmark,
        "vs_target": vs_target,
        "higher_is_better": kpi.higher_is_better,
        "period": period,
    }


def _format_kpi_value(value: Any, unit: str) -> str:
    """Format a KPI value for display."""
    if value is None:
        return "—"

    if unit == "percent":
        return f"{value:.1f}%"
    elif unit == "USD":
        if abs(value) >= 1e9:
            return f"${value/1e9:.1f}B"
        elif abs(value) >= 1e6:
            return f"${value/1e6:.1f}M"
        elif abs(value) >= 1e3:
            return f"${value/1e3:.1f}K"
        else:
            return f"${value:.2f}"
    elif unit == "users":
        if abs(value) >= 1e6:
            return f"{value/1e6:.1f}M"
        elif abs(value) >= 1e3:
            return f"{value/1e3:.1f}K"
        else:
            return f"{value:,.0f}"
    else:
        if isinstance(value, float):
            return f"{value:.2f}"
        return str(value)


def get_kpi_dashboard(
    ticker: str,
    ontology: Optional[CompanyOntology] = None,
) -> Dict[str, Any]:
    """
    Get a complete KPI dashboard for a company.

    Args:
        ticker: Stock ticker
        ontology: Pre-built ontology (optional, will be built if not provided)

    Returns:
        Dict with all KPIs calculated and formatted
    """
    from app.connectors.sec_edgar_connector import extract_financial_statements, get_filer_cik

    if not ontology:
        ontology = build_company_ontology(ticker)

    cik = get_filer_cik(ticker)
    financial_data = extract_financial_statements(cik) if cik else {}

    kpi_results = []
    for kpi in ontology.kpis:
        result = calculate_kpi(kpi, financial_data)
        if result:
            kpi_results.append(result)

    # Group by type
    by_type = defaultdict(list)
    for result in kpi_results:
        kpi_def = next((k for k in ontology.kpis if k.id == result["kpi_id"]), None)
        if kpi_def:
            by_type[kpi_def.metric_type.value].append(result)

    return {
        "ticker": ticker,
        "company_name": ontology.company_name,
        "industry": ontology.industry,
        "kpis": kpi_results,
        "kpis_by_type": dict(by_type),
        "total_kpis": len(kpi_results),
        "generated_at": datetime.utcnow().isoformat(),
    }


# ── Serialization ────────────────────────────────────────────────────────────

def ontology_to_dict(ontology: CompanyOntology) -> Dict[str, Any]:
    """Convert ontology to JSON-serializable dict."""
    return {
        "ticker": ontology.ticker,
        "company_name": ontology.company_name,
        "cik": ontology.cik,
        "industry": ontology.industry,
        "sic_code": ontology.sic_code,
        "created_at": ontology.created_at,
        "updated_at": ontology.updated_at,
        "entities": [
            {
                "id": e.id,
                "name": e.name,
                "aliases": e.aliases,
                "entity_type": e.entity_type,
                "parent_id": e.parent_id,
                "attributes": e.attributes,
                "relationships": e.relationships,
                "confidence": e.confidence,
            }
            for e in ontology.entities
        ],
        "kpis": [
            {
                "id": k.id,
                "name": k.name,
                "description": k.description,
                "metric_type": k.metric_type.value,
                "unit": k.unit,
                "formula": k.formula,
                "components": k.components,
                "aggregation": k.aggregation.value,
                "frequency": k.frequency.value,
                "source_tags": k.source_tags,
                "xbrl_concepts": k.xbrl_concepts,
                "industry_benchmark": k.industry_benchmark,
                "target_value": k.target_value,
                "higher_is_better": k.higher_is_better,
            }
            for k in ontology.kpis
        ],
        "terminology": ontology.terminology,
        "relationships": ontology.relationships,
        "sources_analyzed": ontology.sources_analyzed,
        "version": ontology.version,
    }
