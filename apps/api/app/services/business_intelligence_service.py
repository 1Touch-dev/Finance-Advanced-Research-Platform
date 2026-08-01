"""
Business Intelligence Service
────────────────────────────────────────────────────────────────────────────
Extracts business model, revenue structure, brand portfolio, and industry
outlook from SEC filings without requiring external API keys.

Sections provided:
  1. Business Model - Core business description from 10-K Item 1
  2. Revenue Structure - Segment breakdown with growth trends
  3. Brand Portfolio - Products/services/brands identified from filings
  4. Industry Outlook - SIC-based industry analysis and market positioning

Uses only SEC EDGAR data (free, no API key required).
"""

import logging
import re
from typing import Dict, Any, List, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False


# ── SEC HTTP Layer ────────────────────────────────────────────────────────────

try:
    from app.connectors.sec_http import sec_get_json, sec_get_text
    from app.connectors.sec_edgar_connector import (
        get_filer_cik,
        find_latest_filing,
        get_segment_data,
    )
    SEC_AVAILABLE = True
except ImportError:
    SEC_AVAILABLE = False
    def sec_get_json(*args, **kwargs): return {}
    def sec_get_text(*args, **kwargs): return ""
    def get_filer_cik(*args, **kwargs): return None
    def find_latest_filing(*args, **kwargs): return None
    def get_segment_data(*args, **kwargs): return {}


SEC_DATA = "https://data.sec.gov"
SEC_WWW = "https://www.sec.gov"


# ── SIC Code Industry Mapping ─────────────────────────────────────────────────

# Major industry classifications from SEC SIC codes
SIC_INDUSTRIES = {
    # Technology
    "7370": ("Software & Programming", "Technology", "High"),
    "7371": ("Computer Programming Services", "Technology", "High"),
    "7372": ("Prepackaged Software", "Technology", "High"),
    "7373": ("Computer Integrated Systems Design", "Technology", "High"),
    "7374": ("Computer Processing & Data Preparation", "Technology", "High"),
    "3674": ("Semiconductors & Related Devices", "Technology", "High"),
    "3571": ("Electronic Computers", "Technology", "Moderate"),
    "3572": ("Computer Storage Devices", "Technology", "Moderate"),
    "3661": ("Telephone & Telegraph Apparatus", "Technology", "Moderate"),
    "3663": ("Radio & TV Broadcasting Equipment", "Technology", "Moderate"),
    "3679": ("Electronic Components", "Technology", "Moderate"),
    # Internet & Digital
    "7375": ("Information Retrieval Services", "Internet", "High"),
    "4813": ("Telephone Communications", "Telecom", "Moderate"),
    "4812": ("Radiotelephone Communications", "Telecom", "Moderate"),
    # Finance
    "6021": ("National Commercial Banks", "Finance", "Low"),
    "6022": ("State Commercial Banks", "Finance", "Low"),
    "6211": ("Security Brokers & Dealers", "Finance", "Moderate"),
    "6282": ("Investment Advice", "Finance", "Moderate"),
    "6311": ("Life Insurance", "Insurance", "Low"),
    "6331": ("Fire, Marine & Casualty Insurance", "Insurance", "Low"),
    # Healthcare
    "2834": ("Pharmaceutical Preparations", "Healthcare", "High"),
    "3841": ("Surgical & Medical Instruments", "Healthcare", "High"),
    "3845": ("Electromedical Equipment", "Healthcare", "High"),
    "8011": ("Offices & Clinics of Doctors", "Healthcare", "Low"),
    "8062": ("General Medical & Surgical Hospitals", "Healthcare", "Low"),
    # Retail
    "5311": ("Department Stores", "Retail", "Low"),
    "5331": ("Variety Stores", "Retail", "Low"),
    "5411": ("Grocery Stores", "Retail", "Low"),
    "5912": ("Drug Stores", "Retail", "Low"),
    "5961": ("Catalog & Mail-Order Houses", "Retail", "Moderate"),
    # Manufacturing
    "3711": ("Motor Vehicles & Passenger Car Bodies", "Manufacturing", "Low"),
    "3714": ("Motor Vehicle Parts", "Manufacturing", "Low"),
    "3721": ("Aircraft", "Aerospace", "Moderate"),
    # Energy
    "1311": ("Crude Petroleum & Natural Gas", "Energy", "Moderate"),
    "2911": ("Petroleum Refining", "Energy", "Low"),
    "4911": ("Electric Services", "Utilities", "Low"),
    "4931": ("Electric & Other Services Combined", "Utilities", "Low"),
    # Consumer
    "2080": ("Beverages", "Consumer Goods", "Low"),
    "2111": ("Cigarettes", "Consumer Goods", "Low"),
    "2844": ("Perfumes, Cosmetics & Toilet Preparations", "Consumer Goods", "Moderate"),
    "3942": ("Dolls & Stuffed Toys", "Consumer Goods", "Moderate"),
}

# Default industry info for unknown SIC codes
DEFAULT_INDUSTRY = ("General Business", "Diversified", "Moderate")


def _get_sic_info(cik: str) -> Dict[str, Any]:
    """Get SIC code and industry classification for a company."""
    if not SEC_AVAILABLE:
        return {}

    try:
        # Company submissions contain SIC code
        submissions = sec_get_json(f"{SEC_DATA}/submissions/CIK{cik.zfill(10)}.json")
        if not submissions:
            return {}

        sic = submissions.get("sic", "")
        sic_description = submissions.get("sicDescription", "")
        category = submissions.get("category", "")

        industry_info = SIC_INDUSTRIES.get(sic, DEFAULT_INDUSTRY)

        return {
            "sic_code": sic,
            "sic_description": sic_description,
            "industry": industry_info[0],
            "sector": industry_info[1],
            "growth_profile": industry_info[2],
            "sec_category": category,
        }
    except Exception as e:
        logger.warning("Failed to get SIC info: %s", e)
        return {}


# ── Business Model Extraction ─────────────────────────────────────────────────

# Patterns to find business description start - in priority order
# GENERAL is common in tech company 10-Ks (Microsoft, etc.)
_ITEM1_PATTERNS = [
    re.compile(r"\bGENERAL\b(?=\s+[A-Z][a-z])", re.M),  # "GENERAL Microsoft is..."
    re.compile(r"item\s*1[.\s:]+business\b", re.I),
    re.compile(r"item\s*1[.\s:]+description of business", re.I),
    re.compile(r"overview of (?:our )?business", re.I),
    re.compile(r"(?:^|\n)business\s*\n", re.I | re.M),
]

_ITEM1A_BOUNDARY = re.compile(r"item\s*1a[.\s:–—-]+risk\s*factors", re.I)
_ITEM2_BOUNDARY = re.compile(r"item\s*2[.\s:–—-]+properties", re.I)
# Additional boundaries that might appear before Item 1A
_SECTION_BOUNDARIES = [
    re.compile(r"\bPART\s+I+\s*Item\s*1A\b", re.I),
    re.compile(r"\bRISK\s+FACTORS\b"),  # All caps section header
    re.compile(r"\bInformation about our Executive Officers\b", re.I),
]

# Clean extracted text
_BOILERPLATE = re.compile(
    r"table of contents|click here|page \d+|^\s*\d+\s*$|"
    r"forward.?looking|cautionary|statement regarding|"
    r"^\s*index\s*$|^\s*\d+\s+PART", re.I)

# Detect TOC entries (short lines with page numbers)
_TOC_LINE = re.compile(r"^.{10,80}\s+\d{1,3}\s*$", re.M)


def _extract_business_description(html: str, max_paragraphs: int = 15) -> Dict[str, Any]:
    """Extract business description from 10-K Item 1."""
    if not BS4_AVAILABLE:
        return {"paragraphs": [], "products_services": [], "markets": []}

    soup = BeautifulSoup(html, "html.parser")
    full_text = soup.get_text(" ", strip=True)

    result = {
        "paragraphs": [],
        "products_services": [],
        "markets": [],
        "key_customers": [],
        "competitive_position": [],
    }

    # Find Item 1 / Business description start
    item1_start = None
    for pattern in _ITEM1_PATTERNS:
        for match in pattern.finditer(full_text):
            # Skip TOC entries - check if followed by actual content (50+ chars before next section)
            after_match = full_text[match.end():match.end()+200]
            # TOC entries have page numbers shortly after
            if re.match(r"^\s*\d{1,3}\s", after_match):
                continue
            # Good match - actual content follows
            item1_start = match.start()
            break
        if item1_start is not None:
            break

    if item1_start is None:
        return result

    # Find section boundary (Item 1A, Risk Factors, etc.)
    item1_end = len(full_text)
    for boundary in [_ITEM1A_BOUNDARY, _ITEM2_BOUNDARY] + _SECTION_BOUNDARIES:
        match = boundary.search(full_text, item1_start + 500)  # Skip at least 500 chars
        if match:
            item1_end = min(item1_end, match.start())

    # Extract text
    business_text = full_text[item1_start:item1_end]

    # Split into paragraphs
    paragraphs = []
    for block in re.split(r'\n\s*\n|\.\s+(?=[A-Z])', business_text):
        text = " ".join(block.split())
        if len(text) > 100 and not _BOILERPLATE.search(text):
            paragraphs.append(text[:1000])  # Cap at 1000 chars
            if len(paragraphs) >= max_paragraphs:
                break

    result["paragraphs"] = paragraphs

    # Extract products/services mentions
    products_pattern = re.compile(
        r"\b(?:products?|services?|solutions?|platforms?|offerings?)\s+(?:include|such as|including)\s+([^.]+)",
        re.I)
    for match in products_pattern.finditer(business_text[:15000]):
        items = match.group(1).split(",")
        result["products_services"].extend([i.strip()[:100] for i in items[:10]])

    # Extract market mentions
    market_pattern = re.compile(
        r"\b(?:markets?|segments?|verticals?|industries?)\s+(?:we serve|include|such as)\s+([^.]+)",
        re.I)
    for match in market_pattern.finditer(business_text[:15000]):
        items = match.group(1).split(",")
        result["markets"].extend([i.strip()[:100] for i in items[:10]])

    # Extract customer mentions
    customer_pattern = re.compile(
        r"\b(?:customers?|clients?)\s+(?:include|such as|including)\s+([^.]+)", re.I)
    for match in customer_pattern.finditer(business_text[:15000]):
        items = match.group(1).split(",")
        result["key_customers"].extend([i.strip()[:100] for i in items[:5]])

    # Extract competitive positioning
    compete_pattern = re.compile(
        r"\b(?:compet(?:e|ition|itive)|market (?:position|share|leader))[^.]*\.", re.I)
    for match in compete_pattern.finditer(business_text[:20000]):
        text = match.group(0).strip()
        if len(text) > 50:
            result["competitive_position"].append(text[:500])
            if len(result["competitive_position"]) >= 3:
                break

    return result


def get_business_model(
    ticker: str,
    entity_name: str = "",
) -> Dict[str, Any]:
    """
    Extract business model description from SEC filings.

    Returns:
        Business model data including description, products, markets.
    """
    result = {
        "ticker": ticker,
        "company_name": entity_name,
        "business_description": {},
        "industry_classification": {},
        "key_metrics": {},
        "source": "SEC 10-K Item 1",
    }

    if not SEC_AVAILABLE:
        result["error"] = "SEC connector not available"
        return result

    cik = get_filer_cik(ticker)
    if not cik:
        result["error"] = f"No CIK found for {ticker}"
        return result

    # Get industry classification
    result["industry_classification"] = _get_sic_info(cik)

    # Find latest 10-K
    filing = find_latest_filing(cik, "10-K")
    if not filing:
        result["error"] = "No 10-K filing found"
        return result

    result["filing_date"] = filing.get("filing_date")
    result["fiscal_period_end"] = filing.get("report_date")

    # Get full filing document
    base = filing["base_url"]

    # Try to get the primary document
    primary_doc = filing.get("primary_document", "")
    if primary_doc:
        html = sec_get_text(f"{base}/{primary_doc}")
        if html:
            result["business_description"] = _extract_business_description(html)

    return result


# ── Revenue Structure Analysis ────────────────────────────────────────────────

def analyze_revenue_structure(
    ticker: str,
    segment_data: Optional[Dict[str, Any]] = None,
    financial_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Analyze revenue structure from segment data.

    Args:
        ticker: Stock ticker
        segment_data: Pre-fetched segment data (optional)
        financial_data: Pre-fetched financial data (optional)

    Returns:
        Revenue structure analysis.
    """
    result = {
        "ticker": ticker,
        "segments": [],
        "geographic": [],
        "customer_concentration": [],
        "diversification_score": 0,
        "growth_leaders": [],
        "declining_segments": [],
        "summary": {},
    }

    if not SEC_AVAILABLE:
        return result

    cik = get_filer_cik(ticker)
    if not cik:
        return result

    # Get segment data if not provided
    if not segment_data:
        # Get total revenue for reconciliation
        total_revenue = None
        if financial_data:
            total_revenue = financial_data.get("income_statement", {}).get("revenue")
        segment_data = get_segment_data(cik, total_revenue=total_revenue)

    if not segment_data:
        return result

    # Process segment revenue
    segments = segment_data.get("segments", [])
    for seg in segments:
        entry = {
            "name": seg.get("name"),
            "revenue": seg.get("current"),
            "share_pct": seg.get("share_pct"),
            "growth_pct": seg.get("growth_pct"),
            "prior_revenue": seg.get("prior"),
            "trend": _determine_trend(seg.get("growth_pct")),
        }
        result["segments"].append(entry)

        # Track growth leaders and decliners
        growth = seg.get("growth_pct")
        if growth is not None:
            if growth >= 10:
                result["growth_leaders"].append({
                    "name": seg.get("name"),
                    "growth_pct": growth
                })
            elif growth <= -5:
                result["declining_segments"].append({
                    "name": seg.get("name"),
                    "growth_pct": growth
                })

    # Process geographic breakdown
    for geo in segment_data.get("geographic", []):
        result["geographic"].append({
            "region": geo.get("name"),
            "revenue": geo.get("current"),
            "share_pct": geo.get("share_pct"),
            "growth_pct": geo.get("growth_pct"),
        })

    # Customer concentration
    result["customer_concentration"] = segment_data.get("customer_concentration", [])[:5]

    # Calculate diversification score (0-100)
    # Based on Herfindahl-Hirschman Index
    shares = [s.get("share_pct", 0) for s in result["segments"] if s.get("share_pct")]
    if shares:
        hhi = sum(s ** 2 for s in shares) / 100
        # HHI of 10000 = monopoly (score 0), HHI of 1000 = diversified (score 100)
        result["diversification_score"] = max(0, min(100, int(100 - (hhi - 1000) / 90)))

    # Summary
    total_segments = len(result["segments"])
    total_regions = len(result["geographic"])

    result["summary"] = {
        "total_segments": total_segments,
        "total_regions": total_regions,
        "largest_segment": result["segments"][0]["name"] if result["segments"] else None,
        "largest_segment_share": result["segments"][0]["share_pct"] if result["segments"] else None,
        "fastest_growing": result["growth_leaders"][0]["name"] if result["growth_leaders"] else None,
        "concentration_risk": "High" if result["diversification_score"] < 40 else "Low",
    }

    result["periods"] = segment_data.get("periods", [])
    result["source_url"] = segment_data.get("source_url")

    return result


def _determine_trend(growth_pct: Optional[float]) -> str:
    """Determine trend label from growth percentage."""
    if growth_pct is None:
        return "Unknown"
    if growth_pct >= 20:
        return "Strong Growth"
    elif growth_pct >= 5:
        return "Growing"
    elif growth_pct >= -5:
        return "Stable"
    elif growth_pct >= -15:
        return "Declining"
    else:
        return "Sharp Decline"


# ── Brand Portfolio Analysis ──────────────────────────────────────────────────

_BRAND_PATTERNS = [
    re.compile(r"\b(?:brand|trademark|product line|product family)\s*[:\s]+([A-Z][A-Za-z0-9 ]+)", re.M),
    re.compile(r"(?:our|the)\s+([A-Z][A-Za-z0-9]+(?:\s+[A-Z][a-z]+)?)\s+(?:brand|product|platform|service)", re.I),
    re.compile(r"(?:launched|introduced|released)\s+(?:the\s+)?([A-Z][A-Za-z0-9 ]+)(?:\s+in\s+\d{4})?", re.I),
]

_NOT_A_BRAND = re.compile(
    r"^(?:the|our|this|these|that|their|its|we|item|part|note|section|table|"
    r"fiscal|annual|quarterly|year|month|period|form|report|statement|"
    r"company|corporation|inc|llc|ltd|management|board|director|officer|"
    r"united states|america|europe|asia|china|japan|india)$", re.I)


def identify_brand_portfolio(
    ticker: str,
    business_model: Optional[Dict[str, Any]] = None,
    entity_name: str = "",
) -> Dict[str, Any]:
    """
    Identify brand portfolio from SEC filings.

    Returns:
        Brand portfolio analysis.
    """
    result = {
        "ticker": ticker,
        "company_name": entity_name,
        "brands": [],
        "products": [],
        "services": [],
        "platforms": [],
        "brand_mentions": {},
        "portfolio_summary": {},
    }

    if not SEC_AVAILABLE:
        return result

    cik = get_filer_cik(ticker)
    if not cik:
        return result

    # Get business model data if not provided
    if not business_model:
        business_model = get_business_model(ticker, entity_name)

    desc = business_model.get("business_description", {})

    # Extract products and services from business description
    result["products"] = desc.get("products_services", [])[:15]

    # Find latest 10-K for brand extraction
    filing = find_latest_filing(cik, "10-K")
    if filing:
        base = filing["base_url"]
        primary_doc = filing.get("primary_document", "")
        if primary_doc:
            html = sec_get_text(f"{base}/{primary_doc}")
            if html and BS4_AVAILABLE:
                soup = BeautifulSoup(html, "html.parser")
                text = soup.get_text(" ", strip=True)

                # Extract brand mentions
                brand_counts = defaultdict(int)
                for pattern in _BRAND_PATTERNS:
                    for match in pattern.finditer(text[:100000]):
                        brand = match.group(1).strip()
                        if len(brand) > 2 and len(brand) < 50 and not _NOT_A_BRAND.match(brand):
                            brand_counts[brand] += 1

                # Sort by frequency
                sorted_brands = sorted(brand_counts.items(), key=lambda x: x[1], reverse=True)

                # Filter out company name variations
                company_words = set(entity_name.lower().split())
                for brand, count in sorted_brands[:20]:
                    brand_words = set(brand.lower().split())
                    if not brand_words.issubset(company_words):
                        result["brands"].append({
                            "name": brand,
                            "mention_count": count,
                        })

                result["brand_mentions"] = dict(sorted_brands[:30])

    # Categorize
    result["portfolio_summary"] = {
        "total_brands_identified": len(result["brands"]),
        "total_products_services": len(result["products"]),
        "primary_brand": result["brands"][0]["name"] if result["brands"] else entity_name,
    }

    return result


# ── Industry Outlook ──────────────────────────────────────────────────────────

# Industry growth rates and trends (simplified estimates)
INDUSTRY_OUTLOOK = {
    "Technology": {
        "growth_rate": 8.5,
        "trend": "Strong",
        "key_drivers": ["AI/ML adoption", "Cloud migration", "Digital transformation"],
        "challenges": ["Talent shortage", "Regulation", "Competition"],
        "outlook": "Positive",
    },
    "Internet": {
        "growth_rate": 12.0,
        "trend": "Strong",
        "key_drivers": ["E-commerce growth", "Digital advertising", "Subscription economy"],
        "challenges": ["Privacy regulations", "Market saturation", "Competition"],
        "outlook": "Positive",
    },
    "Finance": {
        "growth_rate": 3.5,
        "trend": "Moderate",
        "key_drivers": ["Fintech innovation", "Wealth management", "Commercial lending"],
        "challenges": ["Interest rate sensitivity", "Regulation", "Credit risk"],
        "outlook": "Neutral",
    },
    "Healthcare": {
        "growth_rate": 6.0,
        "trend": "Strong",
        "key_drivers": ["Aging population", "Biotech innovation", "Telemedicine"],
        "challenges": ["Pricing pressure", "Regulation", "R&D costs"],
        "outlook": "Positive",
    },
    "Retail": {
        "growth_rate": 2.5,
        "trend": "Moderate",
        "key_drivers": ["E-commerce shift", "Omnichannel", "Personalization"],
        "challenges": ["Margin pressure", "Competition", "Supply chain"],
        "outlook": "Neutral",
    },
    "Manufacturing": {
        "growth_rate": 2.0,
        "trend": "Stable",
        "key_drivers": ["Automation", "Reshoring", "EV transition"],
        "challenges": ["Labor costs", "Supply chain", "Energy costs"],
        "outlook": "Neutral",
    },
    "Energy": {
        "growth_rate": 1.5,
        "trend": "Transitioning",
        "key_drivers": ["Energy transition", "LNG demand", "Infrastructure"],
        "challenges": ["ESG pressure", "Volatility", "Regulation"],
        "outlook": "Mixed",
    },
    "Insurance": {
        "growth_rate": 3.0,
        "trend": "Moderate",
        "key_drivers": ["Insurtech", "Climate risk products", "Life/health demand"],
        "challenges": ["Climate losses", "Low yields", "Competition"],
        "outlook": "Neutral",
    },
    "Aerospace": {
        "growth_rate": 5.0,
        "trend": "Recovering",
        "key_drivers": ["Travel recovery", "Defense spending", "Space economy"],
        "challenges": ["Supply chain", "Labor", "Certification delays"],
        "outlook": "Positive",
    },
    "Telecom": {
        "growth_rate": 2.5,
        "trend": "Moderate",
        "key_drivers": ["5G rollout", "Fiber expansion", "IoT"],
        "challenges": ["Capex burden", "Price competition", "Cord cutting"],
        "outlook": "Neutral",
    },
    "Utilities": {
        "growth_rate": 2.0,
        "trend": "Stable",
        "key_drivers": ["Grid modernization", "Renewables", "EV infrastructure"],
        "challenges": ["Regulation", "Rate cases", "Climate risk"],
        "outlook": "Stable",
    },
    "Consumer Goods": {
        "growth_rate": 3.0,
        "trend": "Moderate",
        "key_drivers": ["Premiumization", "Health/wellness", "Sustainability"],
        "challenges": ["Input costs", "Private label", "Channel shift"],
        "outlook": "Neutral",
    },
}

DEFAULT_OUTLOOK = {
    "growth_rate": 3.0,
    "trend": "Moderate",
    "key_drivers": ["Economic growth", "Innovation", "Market expansion"],
    "challenges": ["Competition", "Regulation", "Economic cycles"],
    "outlook": "Neutral",
}


def get_industry_outlook(
    ticker: str,
    industry_classification: Optional[Dict[str, Any]] = None,
    entity_name: str = "",
) -> Dict[str, Any]:
    """
    Generate industry outlook analysis.

    Returns:
        Industry outlook data.
    """
    result = {
        "ticker": ticker,
        "company_name": entity_name,
        "industry": {},
        "sector_outlook": {},
        "competitive_landscape": {},
        "market_position": {},
        "growth_drivers": [],
        "industry_challenges": [],
        "regulatory_environment": {},
    }

    # Get industry classification if not provided
    if not industry_classification:
        cik = get_filer_cik(ticker) if SEC_AVAILABLE else None
        if cik:
            industry_classification = _get_sic_info(cik)

    if not industry_classification:
        result["error"] = "No industry classification available"
        return result

    result["industry"] = industry_classification

    # Get sector outlook
    sector = industry_classification.get("sector", "Diversified")
    outlook = INDUSTRY_OUTLOOK.get(sector, DEFAULT_OUTLOOK)

    result["sector_outlook"] = {
        "sector": sector,
        "industry": industry_classification.get("industry"),
        "growth_rate_estimate": outlook["growth_rate"],
        "trend": outlook["trend"],
        "outlook": outlook["outlook"],
    }

    result["growth_drivers"] = outlook["key_drivers"]
    result["industry_challenges"] = outlook["challenges"]

    # Competitive landscape (general by sector)
    result["competitive_landscape"] = {
        "intensity": "High" if sector in ["Technology", "Retail", "Internet"] else "Moderate",
        "barriers_to_entry": "High" if sector in ["Aerospace", "Healthcare", "Finance"] else "Moderate",
        "market_structure": _get_market_structure(sector),
    }

    # Regulatory environment
    result["regulatory_environment"] = {
        "regulatory_intensity": _get_regulatory_intensity(sector),
        "key_regulators": _get_key_regulators(sector),
    }

    return result


def _get_market_structure(sector: str) -> str:
    """Determine market structure by sector."""
    concentrated = ["Aerospace", "Telecom", "Utilities", "Finance"]
    fragmented = ["Retail", "Consumer Goods", "Manufacturing"]

    if sector in concentrated:
        return "Concentrated oligopoly"
    elif sector in fragmented:
        return "Fragmented / competitive"
    else:
        return "Moderately concentrated"


def _get_regulatory_intensity(sector: str) -> str:
    """Determine regulatory intensity by sector."""
    high = ["Finance", "Healthcare", "Insurance", "Utilities", "Aerospace"]
    moderate = ["Technology", "Energy", "Telecom"]

    if sector in high:
        return "High"
    elif sector in moderate:
        return "Moderate"
    else:
        return "Low"


def _get_key_regulators(sector: str) -> List[str]:
    """Get key regulators by sector."""
    regulators = {
        "Finance": ["Federal Reserve", "SEC", "OCC", "FDIC"],
        "Healthcare": ["FDA", "CMS", "HHS"],
        "Insurance": ["State Insurance Commissioners", "NAIC"],
        "Technology": ["FTC", "DOJ", "EU Commission"],
        "Internet": ["FTC", "FCC", "State AGs"],
        "Aerospace": ["FAA", "DoD", "NASA"],
        "Energy": ["FERC", "EPA", "DOE"],
        "Telecom": ["FCC", "DOJ", "State PUCs"],
        "Utilities": ["FERC", "State PUCs", "EPA"],
    }
    return regulators.get(sector, ["FTC", "SEC"])


# ── Main Export Function ──────────────────────────────────────────────────────

def get_business_intelligence(
    ticker: str,
    entity_name: str = "",
    financial_data: Optional[Dict[str, Any]] = None,
    segment_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Comprehensive business intelligence from SEC filings.

    Combines:
    - Business model description
    - Revenue structure analysis
    - Brand portfolio identification
    - Industry outlook

    Args:
        ticker: Stock ticker
        entity_name: Company name
        financial_data: Pre-fetched financial data
        segment_data: Pre-fetched segment data

    Returns:
        Complete business intelligence payload.
    """
    result = {
        "ticker": ticker,
        "company_name": entity_name,
        "business_model": {},
        "revenue_structure": {},
        "brand_portfolio": {},
        "industry_outlook": {},
        "source": "SEC EDGAR",
    }

    # Business Model
    result["business_model"] = get_business_model(ticker, entity_name)

    # Revenue Structure
    result["revenue_structure"] = analyze_revenue_structure(
        ticker, segment_data=segment_data, financial_data=financial_data)

    # Brand Portfolio (uses business model data)
    result["brand_portfolio"] = identify_brand_portfolio(
        ticker, business_model=result["business_model"], entity_name=entity_name)

    # Industry Outlook
    industry_class = result["business_model"].get("industry_classification", {})
    result["industry_outlook"] = get_industry_outlook(
        ticker, industry_classification=industry_class, entity_name=entity_name)

    return result


# ── Markdown Renderers ────────────────────────────────────────────────────────

def render_business_model_markdown(data: Dict[str, Any]) -> List[str]:
    """Render business model section as markdown."""
    lines = ["## Business Model", ""]

    bm = data.get("business_model", {})
    desc = bm.get("business_description", {})
    industry = bm.get("industry_classification", {})

    if not desc.get("paragraphs") and not industry:
        # Return empty - don't show "not available" message
        return []

    # Industry classification
    if industry:
        lines.append(f"**Industry:** {industry.get('industry', 'N/A')} ({industry.get('sector', 'N/A')} sector)")
        lines.append(f"**SIC Code:** {industry.get('sic_code', 'N/A')} — {industry.get('sic_description', '')}")
        lines.append(f"**Growth Profile:** {industry.get('growth_profile', 'N/A')}")
        lines.append("")

    # Business description
    paragraphs = desc.get("paragraphs", [])
    if paragraphs:
        lines.append("### Business Description")
        lines.append("")
        for para in paragraphs[:5]:
            lines.append(para)
            lines.append("")

    # Products and services
    products = desc.get("products_services", [])
    if products:
        lines.append("### Products and Services")
        lines.append("")
        for p in products[:10]:
            lines.append(f"- {p}")
        lines.append("")

    # Markets served
    markets = desc.get("markets", [])
    if markets:
        lines.append("### Markets Served")
        lines.append("")
        for m in markets[:8]:
            lines.append(f"- {m}")
        lines.append("")

    # Competitive position
    comp = desc.get("competitive_position", [])
    if comp:
        lines.append("### Competitive Position")
        lines.append("")
        for c in comp[:3]:
            lines.append(f"> {c}")
            lines.append("")

    lines.append(f"*Source: SEC 10-K filing dated {bm.get('filing_date', 'N/A')}*")
    lines.append("")

    return lines


def render_revenue_structure_markdown(data: Dict[str, Any]) -> List[str]:
    """Render revenue structure section as markdown."""
    lines = ["## Revenue Structure by Segment", ""]

    rs = data.get("revenue_structure", {})
    segments = rs.get("segments", [])
    geographic = rs.get("geographic", [])
    summary = rs.get("summary", {})

    if not segments and not geographic:
        # Return empty - don't show "not available" message
        return []

    # Summary metrics
    if summary:
        lines.append(f"**Reporting Segments:** {summary.get('total_segments', 0)}")
        lines.append(f"**Geographic Regions:** {summary.get('total_regions', 0)}")
        lines.append(f"**Diversification Score:** {rs.get('diversification_score', 'N/A')}/100")
        lines.append(f"**Concentration Risk:** {summary.get('concentration_risk', 'N/A')}")
        lines.append("")

    # Segment breakdown
    if segments:
        lines.append("### Revenue by Segment")
        lines.append("")
        lines.append("| Segment | Revenue | Share | YoY Growth | Trend |")
        lines.append("|---------|---------|-------|------------|-------|")
        for seg in segments[:10]:
            revenue = seg.get("revenue")
            rev_str = f"${revenue:,.0f}M" if revenue else "N/A"
            share = seg.get("share_pct")
            share_str = f"{share:.1f}%" if share is not None else "N/A"
            growth = seg.get("growth_pct")
            growth_str = f"{growth:+.1f}%" if growth is not None else "N/A"
            trend = seg.get("trend", "")
            lines.append(f"| {seg.get('name', 'Unknown')} | {rev_str} | {share_str} | {growth_str} | {trend} |")
        lines.append("")

    # Geographic breakdown
    if geographic:
        lines.append("### Revenue by Geography")
        lines.append("")
        lines.append("| Region | Revenue | Share | YoY Growth |")
        lines.append("|--------|---------|-------|------------|")
        for geo in geographic[:8]:
            revenue = geo.get("revenue")
            rev_str = f"${revenue:,.0f}M" if revenue else "N/A"
            share = geo.get("share_pct")
            share_str = f"{share:.1f}%" if share is not None else "N/A"
            growth = geo.get("growth_pct")
            growth_str = f"{growth:+.1f}%" if growth is not None else "N/A"
            lines.append(f"| {geo.get('region', 'Unknown')} | {rev_str} | {share_str} | {growth_str} |")
        lines.append("")

    # Customer concentration
    concentration = rs.get("customer_concentration", [])
    if concentration:
        lines.append("### Customer Concentration")
        lines.append("")
        for cust in concentration[:5]:
            lines.append(f"- **{cust.get('counterparty', 'Customer')}**: {cust.get('pct', 0):.1f}% of revenue")
        lines.append("")

    # Growth analysis
    leaders = rs.get("growth_leaders", [])
    decliners = rs.get("declining_segments", [])

    if leaders or decliners:
        lines.append("### Growth Analysis")
        lines.append("")
        if leaders:
            lines.append("**Growth Leaders:**")
            for l in leaders[:3]:
                lines.append(f"- {l['name']}: +{l['growth_pct']:.1f}%")
        if decliners:
            lines.append("")
            lines.append("**Declining Segments:**")
            for d in decliners[:3]:
                lines.append(f"- {d['name']}: {d['growth_pct']:.1f}%")
        lines.append("")

    if rs.get("source_url"):
        lines.append(f"*Source: [SEC Filing]({rs['source_url']})*")
        lines.append("")

    return lines


def render_brand_portfolio_markdown(data: Dict[str, Any]) -> List[str]:
    """Render brand portfolio section as markdown."""
    lines = ["## Brand Portfolio", ""]

    bp = data.get("brand_portfolio", {})
    brands = bp.get("brands", [])
    products = bp.get("products", [])
    summary = bp.get("portfolio_summary", {})

    if not brands and not products:
        # Return empty - don't show "not available" message
        return []

    # Summary
    if summary:
        lines.append(f"**Primary Brand:** {summary.get('primary_brand', 'N/A')}")
        lines.append(f"**Brands Identified:** {summary.get('total_brands_identified', 0)}")
        lines.append(f"**Products/Services:** {summary.get('total_products_services', 0)}")
        lines.append("")

    # Key brands
    if brands:
        lines.append("### Key Brands and Products")
        lines.append("")
        for brand in brands[:15]:
            lines.append(f"- **{brand['name']}** ({brand.get('mention_count', 0)} mentions)")
        lines.append("")

    # Products and services
    if products:
        lines.append("### Products and Services")
        lines.append("")
        for p in products[:12]:
            lines.append(f"- {p}")
        lines.append("")

    lines.append("*Source: SEC 10-K filing analysis*")
    lines.append("")

    return lines


def render_industry_outlook_markdown(data: Dict[str, Any]) -> List[str]:
    """Render industry outlook section as markdown."""
    lines = ["## Industry Outlook", ""]

    io = data.get("industry_outlook", {})
    industry = io.get("industry", {})
    sector_outlook = io.get("sector_outlook", {})
    competitive = io.get("competitive_landscape", {})
    regulatory = io.get("regulatory_environment", {})

    if not sector_outlook:
        # Return empty - don't show "not available" message
        return []

    # Industry classification
    lines.append(f"**Sector:** {sector_outlook.get('sector', 'N/A')}")
    lines.append(f"**Industry:** {sector_outlook.get('industry', 'N/A')}")
    lines.append(f"**Industry Growth Rate:** {sector_outlook.get('growth_rate_estimate', 0):.1f}%")
    lines.append(f"**Trend:** {sector_outlook.get('trend', 'N/A')}")
    lines.append(f"**Overall Outlook:** {sector_outlook.get('outlook', 'N/A')}")
    lines.append("")

    # Growth drivers
    drivers = io.get("growth_drivers", [])
    if drivers:
        lines.append("### Key Growth Drivers")
        lines.append("")
        for d in drivers:
            lines.append(f"- {d}")
        lines.append("")

    # Challenges
    challenges = io.get("industry_challenges", [])
    if challenges:
        lines.append("### Industry Challenges")
        lines.append("")
        for c in challenges:
            lines.append(f"- {c}")
        lines.append("")

    # Competitive landscape
    if competitive:
        lines.append("### Competitive Landscape")
        lines.append("")
        lines.append(f"- **Competition Intensity:** {competitive.get('intensity', 'N/A')}")
        lines.append(f"- **Barriers to Entry:** {competitive.get('barriers_to_entry', 'N/A')}")
        lines.append(f"- **Market Structure:** {competitive.get('market_structure', 'N/A')}")
        lines.append("")

    # Regulatory environment
    if regulatory:
        lines.append("### Regulatory Environment")
        lines.append("")
        lines.append(f"**Regulatory Intensity:** {regulatory.get('regulatory_intensity', 'N/A')}")
        regulators = regulatory.get("key_regulators", [])
        if regulators:
            lines.append(f"**Key Regulators:** {', '.join(regulators)}")
        lines.append("")

    lines.append("*Industry outlook based on SIC classification and sector analysis*")
    lines.append("")

    return lines


def render_all_business_intelligence_markdown(data: Dict[str, Any]) -> List[str]:
    """Render all business intelligence sections as markdown."""
    lines = []
    lines.extend(render_business_model_markdown(data))
    lines.extend(render_revenue_structure_markdown(data))
    lines.extend(render_brand_portfolio_markdown(data))
    lines.extend(render_industry_outlook_markdown(data))
    return lines
