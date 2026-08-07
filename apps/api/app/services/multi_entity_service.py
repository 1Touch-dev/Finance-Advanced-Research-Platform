"""
Multi-Entity & Thematic Corpora Service (Band B #18)
────────────────────────────────────────────────────────────────────────────
Provides:
  - Sector-based entity grouping and queries
  - Supply chain relationship mapping
  - Cross-entity thematic analysis
  - Comparative metrics across entity groups
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from enum import Enum
from datetime import datetime, date
import re


# ── Sector & Industry Taxonomy ─────────────────────────────────────────────────

class Sector(Enum):
    """GICS-aligned sector classification."""
    TECHNOLOGY = "technology"
    HEALTHCARE = "healthcare"
    FINANCIALS = "financials"
    CONSUMER_DISCRETIONARY = "consumer_discretionary"
    CONSUMER_STAPLES = "consumer_staples"
    INDUSTRIALS = "industrials"
    ENERGY = "energy"
    MATERIALS = "materials"
    UTILITIES = "utilities"
    REAL_ESTATE = "real_estate"
    COMMUNICATION_SERVICES = "communication_services"


class Industry(Enum):
    """Detailed industry classification."""
    # Technology
    SEMICONDUCTORS = "semiconductors"
    SOFTWARE = "software"
    HARDWARE = "hardware"
    IT_SERVICES = "it_services"
    INTERNET = "internet"

    # Healthcare
    PHARMACEUTICALS = "pharmaceuticals"
    BIOTECHNOLOGY = "biotechnology"
    MEDICAL_DEVICES = "medical_devices"
    HEALTHCARE_SERVICES = "healthcare_services"

    # Financials
    BANKS = "banks"
    INSURANCE = "insurance"
    ASSET_MANAGEMENT = "asset_management"
    FINTECH = "fintech"

    # Consumer
    RETAIL = "retail"
    AUTOMOTIVE = "automotive"
    RESTAURANTS = "restaurants"
    APPAREL = "apparel"
    ECOMMERCE = "ecommerce"

    # Industrials
    AEROSPACE_DEFENSE = "aerospace_defense"
    MACHINERY = "machinery"
    TRANSPORTATION = "transportation"

    # Energy
    OIL_GAS = "oil_gas"
    RENEWABLE_ENERGY = "renewable_energy"


class RelationshipType(Enum):
    """Supply chain and business relationship types."""
    SUPPLIER = "supplier"
    CUSTOMER = "customer"
    COMPETITOR = "competitor"
    PARTNER = "partner"
    SUBSIDIARY = "subsidiary"
    PARENT = "parent"
    JOINT_VENTURE = "joint_venture"
    LICENSEE = "licensee"
    LICENSOR = "licensor"


# ── Data Classes ───────────────────────────────────────────────────────────────

@dataclass
class EntityProfile:
    """Profile for a single entity in the corpora."""
    ticker: str
    name: str
    sector: Sector
    industry: Industry
    market_cap: Optional[float] = None
    market_cap_category: Optional[str] = None  # mega, large, mid, small, micro
    region: str = "US"
    exchange: str = "NYSE"
    cik: Optional[str] = None
    sic_code: Optional[str] = None

    # Metrics for comparison
    revenue_ttm: Optional[float] = None
    net_income_ttm: Optional[float] = None
    employees: Optional[int] = None

    # Tags for thematic grouping
    themes: List[str] = field(default_factory=list)

    # Metadata
    last_updated: Optional[datetime] = None


@dataclass
class EntityRelationship:
    """Relationship between two entities."""
    source_ticker: str
    target_ticker: str
    relationship_type: RelationshipType
    confidence: float = 0.8
    revenue_exposure: Optional[float] = None  # % of revenue
    description: Optional[str] = None
    source_filing: Optional[str] = None
    effective_date: Optional[date] = None


@dataclass
class ThematicCorpus:
    """A collection of entities grouped by theme."""
    id: str
    name: str
    description: str
    theme_keywords: List[str]
    entities: List[str]  # List of tickers
    sector_focus: Optional[Sector] = None
    created_date: datetime = field(default_factory=datetime.now)

    # Analysis results
    common_risks: List[str] = field(default_factory=list)
    common_opportunities: List[str] = field(default_factory=list)
    avg_exposure_score: float = 0.0


@dataclass
class CrossEntityMetric:
    """Comparative metric across entities."""
    metric_name: str
    metric_description: str
    values: Dict[str, float]  # ticker -> value
    unit: str = ""
    higher_is_better: bool = True

    # Computed statistics
    mean: Optional[float] = None
    median: Optional[float] = None
    std_dev: Optional[float] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    leader: Optional[str] = None  # Best ticker


@dataclass
class SupplyChainNode:
    """Node in supply chain graph."""
    ticker: str
    name: str
    tier: int  # 0 = focal company, 1 = direct, 2 = indirect
    relationship_type: RelationshipType
    revenue_at_risk: Optional[float] = None
    concentration_risk: Optional[str] = None  # low, medium, high, critical


@dataclass
class SupplyChainAnalysis:
    """Full supply chain analysis for a focal company."""
    focal_ticker: str
    focal_name: str
    nodes: List[SupplyChainNode]
    total_suppliers: int
    total_customers: int
    concentration_score: float  # 0-100
    supply_chain_risk_score: float  # 0-100
    key_risks: List[str]
    geographic_exposure: Dict[str, float]  # region -> % exposure


@dataclass
class ThematicAnalysisResult:
    """Results from cross-entity thematic analysis."""
    theme: str
    theme_description: str
    entities_analyzed: List[str]

    # Exposure by entity
    exposure_scores: Dict[str, float]  # ticker -> score (0-100)
    exposure_rankings: List[str]  # tickers ranked by exposure

    # Aggregated insights
    total_mentions: int
    avg_exposure_score: float
    sentiment_by_entity: Dict[str, str]  # ticker -> positive/neutral/negative

    # Key findings
    key_excerpts: List[Dict[str, Any]]  # entity, text, source, date
    trend_direction: str  # increasing, stable, decreasing

    # Risk/opportunity flags
    risk_flags: List[str]
    opportunity_flags: List[str]


# ── Entity Database (In-Memory for Demo) ───────────────────────────────────────

# Major tech companies
ENTITY_DATABASE: Dict[str, EntityProfile] = {
    # Technology - Semiconductors
    "NVDA": EntityProfile(
        ticker="NVDA", name="NVIDIA Corporation",
        sector=Sector.TECHNOLOGY, industry=Industry.SEMICONDUCTORS,
        market_cap=3_200_000_000_000, market_cap_category="mega",
        themes=["AI", "GPU", "data center", "gaming", "autonomous vehicles"]
    ),
    "AMD": EntityProfile(
        ticker="AMD", name="Advanced Micro Devices",
        sector=Sector.TECHNOLOGY, industry=Industry.SEMICONDUCTORS,
        market_cap=280_000_000_000, market_cap_category="mega",
        themes=["AI", "CPU", "GPU", "data center", "gaming"]
    ),
    "INTC": EntityProfile(
        ticker="INTC", name="Intel Corporation",
        sector=Sector.TECHNOLOGY, industry=Industry.SEMICONDUCTORS,
        market_cap=110_000_000_000, market_cap_category="large",
        themes=["CPU", "data center", "foundry", "AI", "PC"]
    ),
    "TSM": EntityProfile(
        ticker="TSM", name="Taiwan Semiconductor",
        sector=Sector.TECHNOLOGY, industry=Industry.SEMICONDUCTORS,
        market_cap=900_000_000_000, market_cap_category="mega",
        region="Taiwan",
        themes=["foundry", "advanced nodes", "AI chips", "supply chain"]
    ),
    "ASML": EntityProfile(
        ticker="ASML", name="ASML Holding",
        sector=Sector.TECHNOLOGY, industry=Industry.SEMICONDUCTORS,
        market_cap=350_000_000_000, market_cap_category="mega",
        region="Netherlands",
        themes=["EUV", "lithography", "chip manufacturing"]
    ),
    "AVGO": EntityProfile(
        ticker="AVGO", name="Broadcom Inc.",
        sector=Sector.TECHNOLOGY, industry=Industry.SEMICONDUCTORS,
        market_cap=800_000_000_000, market_cap_category="mega",
        themes=["networking", "data center", "AI", "wireless"]
    ),
    "QCOM": EntityProfile(
        ticker="QCOM", name="Qualcomm Inc.",
        sector=Sector.TECHNOLOGY, industry=Industry.SEMICONDUCTORS,
        market_cap=200_000_000_000, market_cap_category="mega",
        themes=["5G", "mobile", "wireless", "AI", "automotive"]
    ),

    # Technology - Software
    "MSFT": EntityProfile(
        ticker="MSFT", name="Microsoft Corporation",
        sector=Sector.TECHNOLOGY, industry=Industry.SOFTWARE,
        market_cap=3_100_000_000_000, market_cap_category="mega",
        themes=["AI", "cloud", "enterprise", "gaming", "productivity"]
    ),
    "ORCL": EntityProfile(
        ticker="ORCL", name="Oracle Corporation",
        sector=Sector.TECHNOLOGY, industry=Industry.SOFTWARE,
        market_cap=400_000_000_000, market_cap_category="mega",
        themes=["cloud", "database", "enterprise", "AI"]
    ),
    "CRM": EntityProfile(
        ticker="CRM", name="Salesforce Inc.",
        sector=Sector.TECHNOLOGY, industry=Industry.SOFTWARE,
        market_cap=280_000_000_000, market_cap_category="mega",
        themes=["CRM", "cloud", "AI", "enterprise"]
    ),
    "ADBE": EntityProfile(
        ticker="ADBE", name="Adobe Inc.",
        sector=Sector.TECHNOLOGY, industry=Industry.SOFTWARE,
        market_cap=200_000_000_000, market_cap_category="mega",
        themes=["creative", "AI", "digital media", "marketing"]
    ),

    # Technology - Internet/Hardware
    "AAPL": EntityProfile(
        ticker="AAPL", name="Apple Inc.",
        sector=Sector.TECHNOLOGY, industry=Industry.HARDWARE,
        market_cap=3_400_000_000_000, market_cap_category="mega",
        themes=["consumer electronics", "services", "AI", "wearables"]
    ),
    "GOOGL": EntityProfile(
        ticker="GOOGL", name="Alphabet Inc.",
        sector=Sector.COMMUNICATION_SERVICES, industry=Industry.INTERNET,
        market_cap=2_100_000_000_000, market_cap_category="mega",
        themes=["AI", "search", "cloud", "advertising", "autonomous vehicles"]
    ),
    "META": EntityProfile(
        ticker="META", name="Meta Platforms Inc.",
        sector=Sector.COMMUNICATION_SERVICES, industry=Industry.INTERNET,
        market_cap=1_300_000_000_000, market_cap_category="mega",
        themes=["social media", "AI", "metaverse", "advertising"]
    ),
    "AMZN": EntityProfile(
        ticker="AMZN", name="Amazon.com Inc.",
        sector=Sector.CONSUMER_DISCRETIONARY, industry=Industry.ECOMMERCE,
        market_cap=2_000_000_000_000, market_cap_category="mega",
        themes=["ecommerce", "cloud", "AI", "logistics", "advertising"]
    ),

    # Financials
    "JPM": EntityProfile(
        ticker="JPM", name="JPMorgan Chase & Co.",
        sector=Sector.FINANCIALS, industry=Industry.BANKS,
        market_cap=600_000_000_000, market_cap_category="mega",
        themes=["banking", "investment banking", "consumer", "AI"]
    ),
    "GS": EntityProfile(
        ticker="GS", name="Goldman Sachs Group",
        sector=Sector.FINANCIALS, industry=Industry.BANKS,
        market_cap=170_000_000_000, market_cap_category="large",
        themes=["investment banking", "trading", "asset management"]
    ),
    "V": EntityProfile(
        ticker="V", name="Visa Inc.",
        sector=Sector.FINANCIALS, industry=Industry.FINTECH,
        market_cap=550_000_000_000, market_cap_category="mega",
        themes=["payments", "fintech", "digital payments"]
    ),

    # Healthcare
    "JNJ": EntityProfile(
        ticker="JNJ", name="Johnson & Johnson",
        sector=Sector.HEALTHCARE, industry=Industry.PHARMACEUTICALS,
        market_cap=370_000_000_000, market_cap_category="mega",
        themes=["pharmaceuticals", "medical devices", "consumer health"]
    ),
    "PFE": EntityProfile(
        ticker="PFE", name="Pfizer Inc.",
        sector=Sector.HEALTHCARE, industry=Industry.PHARMACEUTICALS,
        market_cap=160_000_000_000, market_cap_category="large",
        themes=["pharmaceuticals", "vaccines", "oncology"]
    ),
    "UNH": EntityProfile(
        ticker="UNH", name="UnitedHealth Group",
        sector=Sector.HEALTHCARE, industry=Industry.HEALTHCARE_SERVICES,
        market_cap=450_000_000_000, market_cap_category="mega",
        themes=["health insurance", "healthcare services", "pharmacy benefits"]
    ),

    # Consumer
    "TSLA": EntityProfile(
        ticker="TSLA", name="Tesla Inc.",
        sector=Sector.CONSUMER_DISCRETIONARY, industry=Industry.AUTOMOTIVE,
        market_cap=800_000_000_000, market_cap_category="mega",
        themes=["EV", "autonomous vehicles", "energy", "AI", "robotics"]
    ),
    "WMT": EntityProfile(
        ticker="WMT", name="Walmart Inc.",
        sector=Sector.CONSUMER_STAPLES, industry=Industry.RETAIL,
        market_cap=600_000_000_000, market_cap_category="mega",
        themes=["retail", "ecommerce", "grocery", "logistics"]
    ),

    # Energy
    "XOM": EntityProfile(
        ticker="XOM", name="Exxon Mobil Corporation",
        sector=Sector.ENERGY, industry=Industry.OIL_GAS,
        market_cap=450_000_000_000, market_cap_category="mega",
        themes=["oil", "natural gas", "energy transition", "refining"]
    ),
}


# ── Relationship Database ──────────────────────────────────────────────────────

RELATIONSHIP_DATABASE: List[EntityRelationship] = [
    # Apple supply chain
    EntityRelationship("AAPL", "TSM", RelationshipType.SUPPLIER, 0.95, 15.0, "Primary chip foundry"),
    EntityRelationship("AAPL", "QCOM", RelationshipType.SUPPLIER, 0.9, 5.0, "Modem chips"),
    EntityRelationship("AAPL", "AVGO", RelationshipType.SUPPLIER, 0.85, 3.0, "Wireless components"),

    # NVIDIA relationships
    EntityRelationship("NVDA", "TSM", RelationshipType.SUPPLIER, 0.95, 20.0, "Chip manufacturing"),
    EntityRelationship("NVDA", "MSFT", RelationshipType.CUSTOMER, 0.9, 15.0, "Cloud AI infrastructure"),
    EntityRelationship("NVDA", "META", RelationshipType.CUSTOMER, 0.85, 10.0, "AI training infrastructure"),
    EntityRelationship("NVDA", "GOOGL", RelationshipType.CUSTOMER, 0.85, 8.0, "AI training infrastructure"),
    EntityRelationship("NVDA", "AMD", RelationshipType.COMPETITOR, 0.95, None, "GPU competition"),
    EntityRelationship("NVDA", "INTC", RelationshipType.COMPETITOR, 0.8, None, "AI chip competition"),

    # AMD relationships
    EntityRelationship("AMD", "TSM", RelationshipType.SUPPLIER, 0.95, 25.0, "Chip manufacturing"),
    EntityRelationship("AMD", "INTC", RelationshipType.COMPETITOR, 0.95, None, "CPU competition"),
    EntityRelationship("AMD", "MSFT", RelationshipType.CUSTOMER, 0.8, 8.0, "Xbox chips, data center"),

    # Microsoft relationships
    EntityRelationship("MSFT", "NVDA", RelationshipType.PARTNER, 0.9, None, "AI partnership"),
    EntityRelationship("MSFT", "GOOGL", RelationshipType.COMPETITOR, 0.95, None, "Cloud, AI competition"),
    EntityRelationship("MSFT", "AMZN", RelationshipType.COMPETITOR, 0.95, None, "Cloud competition"),

    # TSMC relationships
    EntityRelationship("TSM", "ASML", RelationshipType.SUPPLIER, 0.95, 30.0, "EUV lithography equipment"),

    # Tesla relationships
    EntityRelationship("TSLA", "NVDA", RelationshipType.SUPPLIER, 0.7, 2.0, "AI training chips"),
]


# ── Predefined Thematic Corpora ────────────────────────────────────────────────

PREDEFINED_CORPORA: Dict[str, ThematicCorpus] = {
    "ai_leaders": ThematicCorpus(
        id="ai_leaders",
        name="AI Infrastructure Leaders",
        description="Companies leading AI infrastructure and development",
        theme_keywords=["artificial intelligence", "machine learning", "GPU", "AI chips", "LLM"],
        entities=["NVDA", "MSFT", "GOOGL", "META", "AMD", "ORCL"],
        sector_focus=Sector.TECHNOLOGY,
    ),
    "semiconductor_supply_chain": ThematicCorpus(
        id="semiconductor_supply_chain",
        name="Semiconductor Supply Chain",
        description="Critical players in semiconductor manufacturing",
        theme_keywords=["semiconductor", "foundry", "chips", "EUV", "wafer"],
        entities=["TSM", "ASML", "NVDA", "AMD", "INTC", "QCOM", "AVGO"],
        sector_focus=Sector.TECHNOLOGY,
    ),
    "cloud_hyperscalers": ThematicCorpus(
        id="cloud_hyperscalers",
        name="Cloud Hyperscalers",
        description="Major cloud infrastructure providers",
        theme_keywords=["cloud computing", "AWS", "Azure", "GCP", "data center"],
        entities=["AMZN", "MSFT", "GOOGL", "ORCL"],
        sector_focus=Sector.TECHNOLOGY,
    ),
    "ev_ecosystem": ThematicCorpus(
        id="ev_ecosystem",
        name="EV Ecosystem",
        description="Electric vehicle manufacturers and suppliers",
        theme_keywords=["electric vehicle", "EV", "battery", "charging", "autonomous"],
        entities=["TSLA"],
        sector_focus=Sector.CONSUMER_DISCRETIONARY,
    ),
    "fintech_payments": ThematicCorpus(
        id="fintech_payments",
        name="Fintech & Payments",
        description="Digital payments and fintech leaders",
        theme_keywords=["payments", "fintech", "digital wallet", "banking"],
        entities=["V", "JPM", "GS"],
        sector_focus=Sector.FINANCIALS,
    ),
}


# ── Service Functions ──────────────────────────────────────────────────────────

def get_entity(ticker: str) -> Optional[EntityProfile]:
    """Get entity profile by ticker."""
    return ENTITY_DATABASE.get(ticker.upper())


def get_entities_by_sector(sector: Sector) -> List[EntityProfile]:
    """Get all entities in a sector."""
    return [e for e in ENTITY_DATABASE.values() if e.sector == sector]


def get_entities_by_industry(industry: Industry) -> List[EntityProfile]:
    """Get all entities in an industry."""
    return [e for e in ENTITY_DATABASE.values() if e.industry == industry]


def get_entities_by_theme(theme: str) -> List[EntityProfile]:
    """Get entities matching a theme keyword."""
    theme_lower = theme.lower()
    return [
        e for e in ENTITY_DATABASE.values()
        if any(theme_lower in t.lower() for t in e.themes)
    ]


def search_entities(
    query: str,
    sectors: Optional[List[Sector]] = None,
    industries: Optional[List[Industry]] = None,
    min_market_cap: Optional[float] = None,
    themes: Optional[List[str]] = None,
) -> List[EntityProfile]:
    """Search entities with multiple filters."""
    results = list(ENTITY_DATABASE.values())

    # Filter by query (name or ticker)
    if query:
        query_lower = query.lower()
        results = [
            e for e in results
            if query_lower in e.ticker.lower() or query_lower in e.name.lower()
        ]

    # Filter by sectors
    if sectors:
        results = [e for e in results if e.sector in sectors]

    # Filter by industries
    if industries:
        results = [e for e in results if e.industry in industries]

    # Filter by market cap
    if min_market_cap:
        results = [e for e in results if e.market_cap and e.market_cap >= min_market_cap]

    # Filter by themes
    if themes:
        theme_set = {t.lower() for t in themes}
        results = [
            e for e in results
            if any(t.lower() in theme_set for t in e.themes)
        ]

    return results


def get_entity_relationships(
    ticker: str,
    relationship_types: Optional[List[RelationshipType]] = None,
) -> List[EntityRelationship]:
    """Get all relationships for an entity."""
    ticker = ticker.upper()
    relationships = [
        r for r in RELATIONSHIP_DATABASE
        if r.source_ticker == ticker or r.target_ticker == ticker
    ]

    if relationship_types:
        relationships = [r for r in relationships if r.relationship_type in relationship_types]

    return relationships


def get_supply_chain(
    ticker: str,
    max_tiers: int = 2,
) -> SupplyChainAnalysis:
    """
    Build supply chain analysis for a company.

    Identifies suppliers, customers, and calculates concentration risk.
    """
    ticker = ticker.upper()
    entity = get_entity(ticker)
    if not entity:
        raise ValueError(f"Unknown ticker: {ticker}")

    nodes: List[SupplyChainNode] = []
    suppliers = []
    customers = []

    # Get direct relationships (tier 1)
    relationships = get_entity_relationships(ticker)

    for rel in relationships:
        if rel.source_ticker == ticker:
            # Outgoing relationship
            target = get_entity(rel.target_ticker)
            if target:
                tier = 1
                node = SupplyChainNode(
                    ticker=rel.target_ticker,
                    name=target.name,
                    tier=tier,
                    relationship_type=rel.relationship_type,
                    revenue_at_risk=rel.revenue_exposure,
                    concentration_risk=_calculate_concentration_risk(rel.revenue_exposure),
                )
                nodes.append(node)

                if rel.relationship_type == RelationshipType.SUPPLIER:
                    suppliers.append(rel.target_ticker)
                elif rel.relationship_type == RelationshipType.CUSTOMER:
                    customers.append(rel.target_ticker)
        else:
            # Incoming relationship
            source = get_entity(rel.source_ticker)
            if source:
                # Reverse the relationship type perspective
                rel_type = _reverse_relationship(rel.relationship_type)
                node = SupplyChainNode(
                    ticker=rel.source_ticker,
                    name=source.name,
                    tier=1,
                    relationship_type=rel_type,
                    revenue_at_risk=rel.revenue_exposure,
                    concentration_risk=_calculate_concentration_risk(rel.revenue_exposure),
                )
                nodes.append(node)

                if rel_type == RelationshipType.SUPPLIER:
                    suppliers.append(rel.source_ticker)
                elif rel_type == RelationshipType.CUSTOMER:
                    customers.append(rel.source_ticker)

    # Calculate concentration score
    high_concentration = sum(1 for n in nodes if n.concentration_risk in ["high", "critical"])
    concentration_score = min(100, (high_concentration / max(len(nodes), 1)) * 100)

    # Calculate supply chain risk
    key_risks = []
    if len(suppliers) < 3:
        key_risks.append("Limited supplier diversification")
    if any(n.concentration_risk == "critical" for n in nodes):
        key_risks.append("Critical concentration risk with key partner")
    if any(get_entity(n.ticker).region != "US" for n in nodes if get_entity(n.ticker)):
        key_risks.append("Geographic supply chain risk (non-US exposure)")

    risk_score = min(100, len(key_risks) * 25 + concentration_score * 0.5)

    # Geographic exposure
    geo_exposure: Dict[str, float] = {}
    for node in nodes:
        node_entity = get_entity(node.ticker)
        if node_entity:
            region = node_entity.region
            geo_exposure[region] = geo_exposure.get(region, 0) + 1

    # Normalize to percentages
    total_nodes = len(nodes)
    if total_nodes > 0:
        geo_exposure = {k: (v / total_nodes) * 100 for k, v in geo_exposure.items()}

    return SupplyChainAnalysis(
        focal_ticker=ticker,
        focal_name=entity.name,
        nodes=nodes,
        total_suppliers=len(suppliers),
        total_customers=len(customers),
        concentration_score=concentration_score,
        supply_chain_risk_score=risk_score,
        key_risks=key_risks,
        geographic_exposure=geo_exposure,
    )


def _calculate_concentration_risk(exposure: Optional[float]) -> str:
    """Calculate concentration risk level from revenue exposure."""
    if exposure is None:
        return "low"
    if exposure >= 20:
        return "critical"
    elif exposure >= 10:
        return "high"
    elif exposure >= 5:
        return "medium"
    return "low"


def _reverse_relationship(rel_type: RelationshipType) -> RelationshipType:
    """Reverse relationship type for bidirectional viewing."""
    reversals = {
        RelationshipType.SUPPLIER: RelationshipType.CUSTOMER,
        RelationshipType.CUSTOMER: RelationshipType.SUPPLIER,
        RelationshipType.PARENT: RelationshipType.SUBSIDIARY,
        RelationshipType.SUBSIDIARY: RelationshipType.PARENT,
        RelationshipType.LICENSOR: RelationshipType.LICENSEE,
        RelationshipType.LICENSEE: RelationshipType.LICENSOR,
    }
    return reversals.get(rel_type, rel_type)


def get_thematic_corpus(corpus_id: str) -> Optional[ThematicCorpus]:
    """Get a predefined thematic corpus."""
    return PREDEFINED_CORPORA.get(corpus_id)


def list_thematic_corpora() -> List[ThematicCorpus]:
    """List all available thematic corpora."""
    return list(PREDEFINED_CORPORA.values())


def create_custom_corpus(
    name: str,
    description: str,
    tickers: List[str],
    keywords: Optional[List[str]] = None,
) -> ThematicCorpus:
    """Create a custom thematic corpus from a list of tickers."""
    # Validate tickers
    valid_tickers = []
    for ticker in tickers:
        if get_entity(ticker.upper()):
            valid_tickers.append(ticker.upper())

    if not valid_tickers:
        raise ValueError("No valid tickers provided")

    corpus_id = f"custom_{name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    return ThematicCorpus(
        id=corpus_id,
        name=name,
        description=description,
        theme_keywords=keywords or [],
        entities=valid_tickers,
    )


def analyze_theme_across_entities(
    theme: str,
    tickers: Optional[List[str]] = None,
    corpus_id: Optional[str] = None,
) -> ThematicAnalysisResult:
    """
    Analyze a theme across multiple entities.

    This is a simulated analysis - in production, this would:
    1. Fetch SEC filings for each entity
    2. Search for theme keywords in filings
    3. Calculate exposure scores
    4. Aggregate sentiment and trends
    """
    # Determine entities to analyze
    if corpus_id:
        corpus = get_thematic_corpus(corpus_id)
        if not corpus:
            raise ValueError(f"Unknown corpus: {corpus_id}")
        entity_tickers = corpus.entities
    elif tickers:
        entity_tickers = [t.upper() for t in tickers if get_entity(t)]
    else:
        # Default to entities with matching theme
        entities = get_entities_by_theme(theme)
        entity_tickers = [e.ticker for e in entities]

    if not entity_tickers:
        raise ValueError("No entities to analyze")

    # Simulate exposure analysis
    exposure_scores: Dict[str, float] = {}
    sentiment_by_entity: Dict[str, str] = {}
    key_excerpts: List[Dict[str, Any]] = []

    theme_lower = theme.lower()

    for ticker in entity_tickers:
        entity = get_entity(ticker)
        if not entity:
            continue

        # Calculate exposure based on theme presence in entity themes
        theme_matches = sum(1 for t in entity.themes if theme_lower in t.lower())
        base_score = theme_matches * 30

        # Adjust based on sector relevance
        if entity.sector == Sector.TECHNOLOGY and theme_lower in ["ai", "gpu", "cloud"]:
            base_score += 20

        exposure_scores[ticker] = min(100, base_score + 20)  # Base relevance

        # Simulate sentiment
        if exposure_scores[ticker] >= 70:
            sentiment_by_entity[ticker] = "positive"
        elif exposure_scores[ticker] >= 40:
            sentiment_by_entity[ticker] = "neutral"
        else:
            sentiment_by_entity[ticker] = "neutral"

        # Simulate excerpt
        key_excerpts.append({
            "entity": ticker,
            "text": f"{entity.name} continues to invest in {theme} capabilities...",
            "source": "10-K 2024",
            "date": "2024-02-15",
        })

    # Sort by exposure
    exposure_rankings = sorted(exposure_scores.keys(), key=lambda t: exposure_scores[t], reverse=True)

    # Calculate aggregates
    avg_score = sum(exposure_scores.values()) / len(exposure_scores) if exposure_scores else 0

    # Generate risk/opportunity flags
    risk_flags = []
    opportunity_flags = []

    if avg_score >= 60:
        opportunity_flags.append(f"High sector-wide exposure to {theme}")
    if len([s for s in exposure_scores.values() if s >= 70]) >= 3:
        opportunity_flags.append(f"Multiple leaders emerging in {theme} space")
    if any(sentiment_by_entity.get(t) == "negative" for t in entity_tickers):
        risk_flags.append(f"Some entities showing negative {theme} sentiment")

    return ThematicAnalysisResult(
        theme=theme,
        theme_description=f"Analysis of {theme} exposure and positioning",
        entities_analyzed=entity_tickers,
        exposure_scores=exposure_scores,
        exposure_rankings=exposure_rankings,
        total_mentions=len(key_excerpts) * 15,  # Simulated
        avg_exposure_score=avg_score,
        sentiment_by_entity=sentiment_by_entity,
        key_excerpts=key_excerpts[:5],
        trend_direction="increasing" if avg_score >= 50 else "stable",
        risk_flags=risk_flags,
        opportunity_flags=opportunity_flags,
    )


def compare_entities_metrics(
    tickers: List[str],
    metrics: Optional[List[str]] = None,
) -> List[CrossEntityMetric]:
    """
    Compare specific metrics across multiple entities.

    Available metrics: market_cap, revenue_ttm, net_income_ttm, employees
    """
    default_metrics = ["market_cap", "revenue_ttm", "employees"]
    metric_names = metrics or default_metrics

    results: List[CrossEntityMetric] = []

    for metric_name in metric_names:
        values: Dict[str, float] = {}

        for ticker in tickers:
            entity = get_entity(ticker.upper())
            if entity:
                value = getattr(entity, metric_name, None)
                if value is not None:
                    values[ticker.upper()] = float(value)

        if not values:
            continue

        # Calculate statistics
        value_list = list(values.values())
        sorted_values = sorted(value_list)

        mean_val = sum(value_list) / len(value_list)
        median_val = sorted_values[len(sorted_values) // 2]
        min_val = min(value_list)
        max_val = max(value_list)

        # Variance and std dev
        variance = sum((v - mean_val) ** 2 for v in value_list) / len(value_list)
        std_dev = variance ** 0.5

        # Find leader
        leader = max(values.keys(), key=lambda t: values[t])

        # Metric metadata
        unit = ""
        description = metric_name.replace("_", " ").title()

        if metric_name == "market_cap":
            unit = "USD"
            description = "Market Capitalization"
        elif "revenue" in metric_name:
            unit = "USD"
            description = "Trailing Twelve Month Revenue"
        elif metric_name == "employees":
            unit = "count"
            description = "Number of Employees"

        results.append(CrossEntityMetric(
            metric_name=metric_name,
            metric_description=description,
            values=values,
            unit=unit,
            higher_is_better=True,
            mean=mean_val,
            median=median_val,
            std_dev=std_dev,
            min_value=min_val,
            max_value=max_val,
            leader=leader,
        ))

    return results


# ── Serialization ──────────────────────────────────────────────────────────────

def entity_to_dict(entity: EntityProfile) -> Dict[str, Any]:
    """Convert entity to dictionary."""
    return {
        "ticker": entity.ticker,
        "name": entity.name,
        "sector": entity.sector.value,
        "industry": entity.industry.value,
        "market_cap": entity.market_cap,
        "market_cap_category": entity.market_cap_category,
        "region": entity.region,
        "exchange": entity.exchange,
        "cik": entity.cik,
        "themes": entity.themes,
    }


def relationship_to_dict(rel: EntityRelationship) -> Dict[str, Any]:
    """Convert relationship to dictionary."""
    return {
        "source_ticker": rel.source_ticker,
        "target_ticker": rel.target_ticker,
        "relationship_type": rel.relationship_type.value,
        "confidence": rel.confidence,
        "revenue_exposure": rel.revenue_exposure,
        "description": rel.description,
    }


def supply_chain_to_dict(analysis: SupplyChainAnalysis) -> Dict[str, Any]:
    """Convert supply chain analysis to dictionary."""
    return {
        "focal_ticker": analysis.focal_ticker,
        "focal_name": analysis.focal_name,
        "nodes": [
            {
                "ticker": n.ticker,
                "name": n.name,
                "tier": n.tier,
                "relationship_type": n.relationship_type.value,
                "revenue_at_risk": n.revenue_at_risk,
                "concentration_risk": n.concentration_risk,
            }
            for n in analysis.nodes
        ],
        "total_suppliers": analysis.total_suppliers,
        "total_customers": analysis.total_customers,
        "concentration_score": analysis.concentration_score,
        "supply_chain_risk_score": analysis.supply_chain_risk_score,
        "key_risks": analysis.key_risks,
        "geographic_exposure": analysis.geographic_exposure,
    }


def corpus_to_dict(corpus: ThematicCorpus) -> Dict[str, Any]:
    """Convert thematic corpus to dictionary."""
    return {
        "id": corpus.id,
        "name": corpus.name,
        "description": corpus.description,
        "theme_keywords": corpus.theme_keywords,
        "entities": corpus.entities,
        "sector_focus": corpus.sector_focus.value if corpus.sector_focus else None,
        "created_date": corpus.created_date.isoformat(),
        "common_risks": corpus.common_risks,
        "common_opportunities": corpus.common_opportunities,
    }


def thematic_result_to_dict(result: ThematicAnalysisResult) -> Dict[str, Any]:
    """Convert thematic analysis result to dictionary."""
    return {
        "theme": result.theme,
        "theme_description": result.theme_description,
        "entities_analyzed": result.entities_analyzed,
        "exposure_scores": result.exposure_scores,
        "exposure_rankings": result.exposure_rankings,
        "total_mentions": result.total_mentions,
        "avg_exposure_score": result.avg_exposure_score,
        "sentiment_by_entity": result.sentiment_by_entity,
        "key_excerpts": result.key_excerpts,
        "trend_direction": result.trend_direction,
        "risk_flags": result.risk_flags,
        "opportunity_flags": result.opportunity_flags,
    }


def metric_to_dict(metric: CrossEntityMetric) -> Dict[str, Any]:
    """Convert cross-entity metric to dictionary."""
    return {
        "metric_name": metric.metric_name,
        "metric_description": metric.metric_description,
        "values": metric.values,
        "unit": metric.unit,
        "higher_is_better": metric.higher_is_better,
        "statistics": {
            "mean": metric.mean,
            "median": metric.median,
            "std_dev": metric.std_dev,
            "min": metric.min_value,
            "max": metric.max_value,
        },
        "leader": metric.leader,
    }
