"""
M&A Rumor Tracking Service (Band C #39)
Aggregates M&A rumors from news sources
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import random


@dataclass
class MARumor:
    """M&A Rumor data"""
    rumor_id: str
    target_ticker: str
    target_name: str
    acquirer_ticker: Optional[str]
    acquirer_name: Optional[str]
    deal_type: str  # acquisition, merger, hostile_takeover, spinoff, divestiture
    rumor_date: str
    source: str
    headline: str
    summary: str
    estimated_value: Optional[float] = None
    premium_percent: Optional[float] = None
    probability_score: float = 0.0  # 0-100
    status: str = "rumor"  # rumor, confirmed, denied, completed, withdrawn
    sector: str = ""
    last_updated: str = ""
    related_articles: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rumor_id": self.rumor_id,
            "target_ticker": self.target_ticker,
            "target_name": self.target_name,
            "acquirer_ticker": self.acquirer_ticker,
            "acquirer_name": self.acquirer_name,
            "deal_type": self.deal_type,
            "rumor_date": self.rumor_date,
            "source": self.source,
            "headline": self.headline,
            "summary": self.summary,
            "estimated_value": self.estimated_value,
            "premium_percent": self.premium_percent,
            "probability_score": self.probability_score,
            "status": self.status,
            "sector": self.sector,
            "last_updated": self.last_updated,
            "related_articles": self.related_articles,
        }


# Mock M&A Rumor data
MOCK_RUMORS = [
    MARumor(
        rumor_id="MA001",
        target_ticker="SNAP",
        target_name="Snap Inc",
        acquirer_ticker="META",
        acquirer_name="Meta Platforms",
        deal_type="acquisition",
        rumor_date=(datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d"),
        source="Wall Street Journal",
        headline="Meta reportedly exploring acquisition of Snap",
        summary="Sources familiar with the matter suggest Meta has held preliminary discussions about acquiring Snap. Deal would face significant regulatory scrutiny.",
        estimated_value=25000000000,
        premium_percent=45.0,
        probability_score=35.0,
        status="rumor",
        sector="Technology",
        last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        related_articles=["WSJ: Meta-Snap Talks", "Reuters: Antitrust concerns"],
    ),
    MARumor(
        rumor_id="MA002",
        target_ticker="ROKU",
        target_name="Roku Inc",
        acquirer_ticker="NFLX",
        acquirer_name="Netflix Inc",
        deal_type="acquisition",
        rumor_date=(datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d"),
        source="Bloomberg",
        headline="Netflix considers Roku acquisition for hardware play",
        summary="Netflix reportedly exploring acquisition of Roku to expand into hardware and gain access to Roku's advertising platform.",
        estimated_value=18000000000,
        premium_percent=55.0,
        probability_score=25.0,
        status="rumor",
        sector="Technology",
        last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ),
    MARumor(
        rumor_id="MA003",
        target_ticker="PINS",
        target_name="Pinterest Inc",
        acquirer_ticker="MSFT",
        acquirer_name="Microsoft Corp",
        deal_type="acquisition",
        rumor_date=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
        source="Financial Times",
        headline="Microsoft in talks to acquire Pinterest",
        summary="Microsoft has approached Pinterest about a potential acquisition, sources say. Deal would boost Microsoft's advertising business.",
        estimated_value=35000000000,
        premium_percent=40.0,
        probability_score=45.0,
        status="rumor",
        sector="Technology",
        last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ),
    MARumor(
        rumor_id="MA004",
        target_ticker="BYND",
        target_name="Beyond Meat Inc",
        acquirer_ticker="PEP",
        acquirer_name="PepsiCo Inc",
        deal_type="acquisition",
        rumor_date=(datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d"),
        source="CNBC",
        headline="PepsiCo exploring Beyond Meat acquisition",
        summary="PepsiCo reportedly considering acquisition of struggling Beyond Meat to expand plant-based portfolio.",
        estimated_value=1500000000,
        premium_percent=80.0,
        probability_score=40.0,
        status="rumor",
        sector="Consumer Staples",
        last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ),
    MARumor(
        rumor_id="MA005",
        target_ticker="RIVN",
        target_name="Rivian Automotive",
        acquirer_ticker="AMZN",
        acquirer_name="Amazon.com Inc",
        deal_type="acquisition",
        rumor_date=(datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
        source="Reuters",
        headline="Amazon may increase stake in Rivian, possible full acquisition",
        summary="Amazon, already a major Rivian investor, reportedly exploring increasing stake or full acquisition of the EV maker.",
        estimated_value=20000000000,
        premium_percent=35.0,
        probability_score=50.0,
        status="rumor",
        sector="Consumer Discretionary",
        last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ),
    MARumor(
        rumor_id="MA006",
        target_ticker="DKNG",
        target_name="DraftKings Inc",
        acquirer_ticker="DIS",
        acquirer_name="Walt Disney Co",
        deal_type="acquisition",
        rumor_date=(datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d"),
        source="Sports Business Journal",
        headline="Disney exploring sports betting entry via DraftKings",
        summary="Disney reportedly in preliminary discussions about acquiring DraftKings to enter the sports betting market through ESPN.",
        estimated_value=22000000000,
        premium_percent=50.0,
        probability_score=30.0,
        status="rumor",
        sector="Consumer Discretionary",
        last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ),
    MARumor(
        rumor_id="MA007",
        target_ticker="ZM",
        target_name="Zoom Video Communications",
        acquirer_ticker="CRM",
        acquirer_name="Salesforce Inc",
        deal_type="merger",
        rumor_date=(datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d"),
        source="The Information",
        headline="Salesforce and Zoom discuss potential merger",
        summary="Enterprise software giants Salesforce and Zoom have reportedly held merger discussions to create unified collaboration platform.",
        estimated_value=30000000000,
        premium_percent=30.0,
        probability_score=20.0,
        status="denied",
        sector="Technology",
        last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ),
    MARumor(
        rumor_id="MA008",
        target_ticker="PLTR",
        target_name="Palantir Technologies",
        acquirer_ticker=None,
        acquirer_name="Private Equity Consortium",
        deal_type="acquisition",
        rumor_date=(datetime.now() - timedelta(days=4)).strftime("%Y-%m-%d"),
        source="Bloomberg",
        headline="PE firms reportedly eye Palantir take-private",
        summary="A consortium of private equity firms is reportedly exploring a take-private deal for Palantir Technologies.",
        estimated_value=45000000000,
        premium_percent=25.0,
        probability_score=15.0,
        status="rumor",
        sector="Technology",
        last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ),
    MARumor(
        rumor_id="MA009",
        target_ticker="HOOD",
        target_name="Robinhood Markets",
        acquirer_ticker="SCHW",
        acquirer_name="Charles Schwab",
        deal_type="acquisition",
        rumor_date=(datetime.now() - timedelta(days=20)).strftime("%Y-%m-%d"),
        source="Wall Street Journal",
        headline="Schwab confirms acquisition talks with Robinhood",
        summary="Charles Schwab has confirmed it is in discussions to acquire Robinhood Markets to expand its retail brokerage platform.",
        estimated_value=12000000000,
        premium_percent=60.0,
        probability_score=65.0,
        status="confirmed",
        sector="Financials",
        last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ),
    MARumor(
        rumor_id="MA010",
        target_ticker="ABNB",
        target_name="Airbnb Inc",
        acquirer_ticker="BKNG",
        acquirer_name="Booking Holdings",
        deal_type="merger",
        rumor_date=(datetime.now() - timedelta(days=8)).strftime("%Y-%m-%d"),
        source="Financial Times",
        headline="Booking Holdings, Airbnb explore merger of equals",
        summary="Travel giants Booking Holdings and Airbnb have held preliminary discussions about a potential merger of equals.",
        estimated_value=150000000000,
        premium_percent=15.0,
        probability_score=10.0,
        status="rumor",
        sector="Consumer Discretionary",
        last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ),
]


def get_active_rumors(
    days: int = 30,
    status: Optional[str] = None,
    sector: Optional[str] = None,
    min_probability: float = 0.0,
) -> List[Dict[str, Any]]:
    """Get active M&A rumors"""
    cutoff_date = datetime.now() - timedelta(days=days)

    rumors = []
    for rumor in MOCK_RUMORS:
        rumor_date = datetime.strptime(rumor.rumor_date, "%Y-%m-%d")
        if rumor_date >= cutoff_date:
            if status and rumor.status != status:
                continue
            if sector and rumor.sector.lower() != sector.lower():
                continue
            if rumor.probability_score < min_probability:
                continue
            rumors.append(rumor.to_dict())

    # Sort by date descending
    rumors.sort(key=lambda x: x["rumor_date"], reverse=True)
    return rumors


def get_rumor_by_id(rumor_id: str) -> Optional[Dict[str, Any]]:
    """Get rumor details by ID"""
    for rumor in MOCK_RUMORS:
        if rumor.rumor_id == rumor_id:
            return rumor.to_dict()
    return None


def get_rumors_by_ticker(ticker: str) -> List[Dict[str, Any]]:
    """Get all rumors involving a ticker (as target or acquirer)"""
    ticker = ticker.upper()
    rumors = []

    for rumor in MOCK_RUMORS:
        if rumor.target_ticker == ticker or rumor.acquirer_ticker == ticker:
            rumors.append(rumor.to_dict())

    rumors.sort(key=lambda x: x["rumor_date"], reverse=True)
    return rumors


def get_high_probability_rumors(min_score: float = 40.0) -> List[Dict[str, Any]]:
    """Get rumors with high probability scores"""
    rumors = []

    for rumor in MOCK_RUMORS:
        if rumor.probability_score >= min_score and rumor.status == "rumor":
            rumors.append(rumor.to_dict())

    rumors.sort(key=lambda x: x["probability_score"], reverse=True)
    return rumors


def get_confirmed_deals() -> List[Dict[str, Any]]:
    """Get confirmed M&A deals"""
    deals = []

    for rumor in MOCK_RUMORS:
        if rumor.status == "confirmed":
            deals.append(rumor.to_dict())

    deals.sort(key=lambda x: x["rumor_date"], reverse=True)
    return deals


def get_rumors_by_deal_type(deal_type: str) -> List[Dict[str, Any]]:
    """Get rumors by deal type"""
    rumors = []

    for rumor in MOCK_RUMORS:
        if rumor.deal_type == deal_type:
            rumors.append(rumor.to_dict())

    rumors.sort(key=lambda x: x["rumor_date"], reverse=True)
    return rumors


def get_largest_deals(limit: int = 10) -> List[Dict[str, Any]]:
    """Get largest rumored deals by value"""
    rumors = [r.to_dict() for r in MOCK_RUMORS if r.estimated_value]
    rumors.sort(key=lambda x: x["estimated_value"], reverse=True)
    return rumors[:limit]


def get_ma_stats() -> Dict[str, Any]:
    """Get M&A market statistics"""
    total_rumors = len(MOCK_RUMORS)
    active_rumors = len([r for r in MOCK_RUMORS if r.status == "rumor"])
    confirmed = len([r for r in MOCK_RUMORS if r.status == "confirmed"])
    denied = len([r for r in MOCK_RUMORS if r.status == "denied"])

    total_value = sum(r.estimated_value or 0 for r in MOCK_RUMORS)
    avg_premium = sum(r.premium_percent or 0 for r in MOCK_RUMORS if r.premium_percent) / max(1, len([r for r in MOCK_RUMORS if r.premium_percent]))

    # By sector
    by_sector = {}
    for rumor in MOCK_RUMORS:
        by_sector[rumor.sector] = by_sector.get(rumor.sector, 0) + 1

    # By deal type
    by_type = {}
    for rumor in MOCK_RUMORS:
        by_type[rumor.deal_type] = by_type.get(rumor.deal_type, 0) + 1

    # Hottest target (most rumors)
    target_counts = {}
    for rumor in MOCK_RUMORS:
        target_counts[rumor.target_ticker] = target_counts.get(rumor.target_ticker, 0) + 1
    hottest_target = max(target_counts.items(), key=lambda x: x[1])[0] if target_counts else None

    return {
        "total_rumors": total_rumors,
        "active_rumors": active_rumors,
        "confirmed_deals": confirmed,
        "denied_rumors": denied,
        "total_estimated_value": total_value,
        "avg_premium_percent": round(avg_premium, 2),
        "by_sector": by_sector,
        "by_deal_type": by_type,
        "hottest_target": hottest_target,
    }


def search_rumors(query: str) -> List[Dict[str, Any]]:
    """Search rumors by company name, ticker, or headline"""
    query = query.lower()
    results = []

    for rumor in MOCK_RUMORS:
        if (
            query in rumor.target_ticker.lower()
            or query in rumor.target_name.lower()
            or (rumor.acquirer_ticker and query in rumor.acquirer_ticker.lower())
            or (rumor.acquirer_name and query in rumor.acquirer_name.lower())
            or query in rumor.headline.lower()
        ):
            results.append(rumor.to_dict())

    return results


def get_recent_updates(hours: int = 24) -> List[Dict[str, Any]]:
    """Get rumors with recent updates"""
    cutoff = datetime.now() - timedelta(hours=hours)
    updates = []

    for rumor in MOCK_RUMORS:
        last_updated = datetime.strptime(rumor.last_updated, "%Y-%m-%d %H:%M:%S")
        if last_updated >= cutoff:
            updates.append(rumor.to_dict())

    updates.sort(key=lambda x: x["last_updated"], reverse=True)
    return updates
