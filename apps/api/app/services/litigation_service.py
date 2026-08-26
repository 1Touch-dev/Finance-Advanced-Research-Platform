"""
Litigation Intelligence Service (Band C #52-56)
────────────────────────────────────────────────────────────────────────────────
Provides:
- #52 Enforcement action event studies (SEC/DOJ/OFAC)
- #53 Docket velocity indicator (new filings before disclosure)
- #54 Exposure normalized (litigation/revenue ratio)
- #55 Point-in-time litigation panel
- #56 Litigation fields for screener + alerts
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class EnforcementType(Enum):
    """Types of enforcement actions."""
    SEC = "sec"
    DOJ = "doj"
    FTC = "ftc"
    OFAC = "ofac"
    EPA = "epa"
    OSHA = "osha"
    OTHER = "other"


class RiskLevel(Enum):
    """Litigation risk levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    MINIMAL = "minimal"


@dataclass
class EnforcementEvent:
    """An enforcement action event for event studies."""
    event_id: str
    event_type: EnforcementType
    event_date: str
    entity_name: str
    ticker: Optional[str]
    description: str
    amount: Optional[float] = None
    source_url: Optional[str] = None
    agency: Optional[str] = None
    resolution: Optional[str] = None  # pending, settled, dismissed

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "event_date": self.event_date,
            "entity_name": self.entity_name,
            "ticker": self.ticker,
            "description": self.description,
            "amount": self.amount,
            "source_url": self.source_url,
            "agency": self.agency,
            "resolution": self.resolution,
        }


@dataclass
class EventStudyResult:
    """Result of an enforcement event study."""
    event: EnforcementEvent
    pre_event_return: Optional[float] = None  # Return before event
    event_day_return: Optional[float] = None  # Return on event day
    post_event_return: Optional[float] = None  # Return after event
    cumulative_abnormal_return: Optional[float] = None  # CAR
    market_reaction: Optional[str] = None  # negative, neutral, positive
    volume_spike: Optional[float] = None  # Volume vs average

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event": self.event.to_dict(),
            "pre_event_return": self.pre_event_return,
            "event_day_return": self.event_day_return,
            "post_event_return": self.post_event_return,
            "cumulative_abnormal_return": self.cumulative_abnormal_return,
            "market_reaction": self.market_reaction,
            "volume_spike": self.volume_spike,
        }


@dataclass
class DocketVelocity:
    """Docket velocity indicator - new filings before disclosure (#53)."""
    ticker: str
    company_name: str
    period_days: int
    new_filings: int
    avg_filings_per_period: float
    velocity_ratio: float  # current / average
    undisclosed_count: int
    days_to_disclosure_avg: Optional[float]
    alert_level: RiskLevel
    recent_cases: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "company_name": self.company_name,
            "period_days": self.period_days,
            "new_filings": self.new_filings,
            "avg_filings_per_period": self.avg_filings_per_period,
            "velocity_ratio": self.velocity_ratio,
            "undisclosed_count": self.undisclosed_count,
            "days_to_disclosure_avg": self.days_to_disclosure_avg,
            "alert_level": self.alert_level.value,
            "recent_cases": self.recent_cases,
        }


@dataclass
class NormalizedExposure:
    """Litigation exposure normalized to financials (#54)."""
    ticker: str
    company_name: str
    total_litigation_exposure: float  # Total $ at risk
    # Normalized ratios
    exposure_to_revenue: Optional[float] = None  # % of annual revenue
    exposure_to_equity: Optional[float] = None  # % of book equity
    exposure_to_cash: Optional[float] = None  # % of cash position
    exposure_to_market_cap: Optional[float] = None  # % of market cap
    exposure_to_assets: Optional[float] = None  # % of total assets
    # Comparison
    industry_avg_exposure: Optional[float] = None
    percentile_rank: Optional[float] = None  # 0-100
    # Risk classification
    risk_level: RiskLevel = RiskLevel.MEDIUM
    # Underlying data
    case_count: int = 0
    active_cases: int = 0
    securities_cases: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "company_name": self.company_name,
            "total_litigation_exposure": self.total_litigation_exposure,
            "exposure_to_revenue": self.exposure_to_revenue,
            "exposure_to_equity": self.exposure_to_equity,
            "exposure_to_cash": self.exposure_to_cash,
            "exposure_to_market_cap": self.exposure_to_market_cap,
            "exposure_to_assets": self.exposure_to_assets,
            "industry_avg_exposure": self.industry_avg_exposure,
            "percentile_rank": self.percentile_rank,
            "risk_level": self.risk_level.value,
            "case_count": self.case_count,
            "active_cases": self.active_cases,
            "securities_cases": self.securities_cases,
        }


@dataclass
class LitigationSnapshot:
    """Point-in-time litigation snapshot (#55)."""
    ticker: str
    as_of_date: str
    total_cases: int
    active_cases: int
    total_exposure: float
    disclosed_exposure: float
    undisclosed_exposure: float
    by_type: Dict[str, int] = field(default_factory=dict)
    by_status: Dict[str, int] = field(default_factory=dict)
    risk_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "as_of_date": self.as_of_date,
            "total_cases": self.total_cases,
            "active_cases": self.active_cases,
            "total_exposure": self.total_exposure,
            "disclosed_exposure": self.disclosed_exposure,
            "undisclosed_exposure": self.undisclosed_exposure,
            "by_type": self.by_type,
            "by_status": self.by_status,
            "risk_score": self.risk_score,
        }


@dataclass
class LitigationTimeSeries:
    """Point-in-time litigation panel data (#55)."""
    ticker: str
    company_name: str
    start_date: str
    end_date: str
    frequency: str  # daily, weekly, monthly, quarterly
    snapshots: List[LitigationSnapshot] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "company_name": self.company_name,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "frequency": self.frequency,
            "snapshots": [s.to_dict() for s in self.snapshots],
        }


@dataclass
class LitigationScreenerFields:
    """Litigation fields for screener (#56)."""
    ticker: str
    company_name: str
    # Core metrics
    total_cases: int = 0
    active_cases: int = 0
    total_exposure_usd: float = 0.0
    # Normalized metrics
    exposure_pct_revenue: Optional[float] = None
    exposure_pct_market_cap: Optional[float] = None
    # Velocity
    new_cases_30d: int = 0
    new_cases_90d: int = 0
    # Risk
    risk_score: float = 0.0
    risk_level: RiskLevel = RiskLevel.LOW
    # Specific types
    securities_cases: int = 0
    antitrust_cases: int = 0
    patent_cases: int = 0
    regulatory_cases: int = 0
    # Flags
    has_sec_enforcement: bool = False
    has_class_action: bool = False
    has_undisclosed: bool = False
    # Alert triggers
    velocity_alert: bool = False
    exposure_alert: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "company_name": self.company_name,
            "total_cases": self.total_cases,
            "active_cases": self.active_cases,
            "total_exposure_usd": self.total_exposure_usd,
            "exposure_pct_revenue": self.exposure_pct_revenue,
            "exposure_pct_market_cap": self.exposure_pct_market_cap,
            "new_cases_30d": self.new_cases_30d,
            "new_cases_90d": self.new_cases_90d,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level.value,
            "securities_cases": self.securities_cases,
            "antitrust_cases": self.antitrust_cases,
            "patent_cases": self.patent_cases,
            "regulatory_cases": self.regulatory_cases,
            "has_sec_enforcement": self.has_sec_enforcement,
            "has_class_action": self.has_class_action,
            "has_undisclosed": self.has_undisclosed,
            "velocity_alert": self.velocity_alert,
            "exposure_alert": self.exposure_alert,
        }


# ── #52: Enforcement Event Studies ────────────────────────────────────────────


def get_enforcement_events(
    ticker: str,
    entity_name: str,
    years: int = 5,
    event_types: Optional[List[EnforcementType]] = None,
) -> List[EnforcementEvent]:
    """
    Fetch enforcement action events for event study analysis.

    Args:
        ticker: Stock ticker
        entity_name: Company name
        years: Lookback period
        event_types: Filter by event type

    Returns:
        List of enforcement events.
    """
    events = []
    event_id = 0

    try:
        from app.connectors.litigation_connector import (
            track_sec_enforcement,
            _search_ftc_proceedings,
            _search_doj_antitrust,
        )

        # SEC enforcement
        sec_data = track_sec_enforcement(entity_name, years)
        for action in sec_data.get("enforcement_actions", []):
            event_id += 1
            events.append(EnforcementEvent(
                event_id=f"ENF{event_id:04d}",
                event_type=EnforcementType.SEC,
                event_date=action.get("filing_date", ""),
                entity_name=entity_name,
                ticker=ticker,
                description=action.get("title", "")[:200],
                source_url=action.get("url", ""),
                agency="SEC",
                resolution="pending",
            ))

        for lr in sec_data.get("litigation_releases", []):
            event_id += 1
            events.append(EnforcementEvent(
                event_id=f"ENF{event_id:04d}",
                event_type=EnforcementType.SEC,
                event_date=lr.get("filing_date", ""),
                entity_name=entity_name,
                ticker=ticker,
                description=lr.get("title", "")[:200],
                source_url=lr.get("url", ""),
                agency="SEC",
                resolution="pending",
            ))

        # FTC proceedings
        ftc_data = _search_ftc_proceedings(entity_name)
        for proc in ftc_data:
            event_id += 1
            events.append(EnforcementEvent(
                event_id=f"ENF{event_id:04d}",
                event_type=EnforcementType.FTC,
                event_date=proc.get("date", ""),
                entity_name=entity_name,
                ticker=ticker,
                description=proc.get("title", "")[:200],
                source_url=proc.get("url", ""),
                agency="FTC",
                resolution="pending",
            ))

        # DOJ Antitrust
        doj_data = _search_doj_antitrust(entity_name)
        for case in doj_data:
            event_id += 1
            events.append(EnforcementEvent(
                event_id=f"ENF{event_id:04d}",
                event_type=EnforcementType.DOJ,
                event_date="",  # DOJ doesn't provide date in scrape
                entity_name=entity_name,
                ticker=ticker,
                description=case.get("title", "")[:200],
                source_url=case.get("url", ""),
                agency="DOJ Antitrust",
                resolution="pending",
            ))

    except Exception as e:
        logger.warning(f"Error fetching enforcement events for {ticker}: {e}")

    # Filter by event type if specified
    if event_types:
        events = [e for e in events if e.event_type in event_types]

    return events


def run_enforcement_event_study(
    ticker: str,
    entity_name: str,
    event_window: int = 5,
) -> List[EventStudyResult]:
    """
    Run event study on enforcement actions (#52).

    Calculates abnormal returns around enforcement events using
    a simple market model.

    Args:
        ticker: Stock ticker
        entity_name: Company name
        event_window: Days before/after event to analyze

    Returns:
        Event study results for each enforcement event.
    """
    results = []

    # Get enforcement events
    events = get_enforcement_events(ticker, entity_name)

    for event in events:
        if not event.event_date:
            continue

        # Calculate event study metrics
        # In production, this would use actual price data
        result = EventStudyResult(
            event=event,
            pre_event_return=None,  # Would be calculated from price data
            event_day_return=None,
            post_event_return=None,
            cumulative_abnormal_return=None,
            market_reaction="unknown",
            volume_spike=None,
        )

        try:
            # Try to get price data for event study
            from app.connectors.market_data_connector import get_historical_prices

            event_dt = datetime.strptime(event.event_date, "%Y-%m-%d")
            start_dt = event_dt - timedelta(days=event_window + 30)
            end_dt = event_dt + timedelta(days=event_window)

            prices = get_historical_prices(
                ticker,
                start_dt.strftime("%Y-%m-%d"),
                end_dt.strftime("%Y-%m-%d"),
            )

            if prices and len(prices) > event_window * 2:
                # Simple event study calculation
                # Pre-event: average return before event
                pre_returns = []
                event_returns = []
                post_returns = []

                for i, p in enumerate(prices):
                    p_date = p.get("date", "")
                    if p_date < event.event_date:
                        if i > 0:
                            prev = prices[i-1].get("close", 0)
                            curr = p.get("close", 0)
                            if prev > 0:
                                pre_returns.append((curr - prev) / prev)
                    elif p_date == event.event_date:
                        if i > 0:
                            prev = prices[i-1].get("close", 0)
                            curr = p.get("close", 0)
                            if prev > 0:
                                result.event_day_return = (curr - prev) / prev
                    else:
                        if i > 0:
                            prev = prices[i-1].get("close", 0)
                            curr = p.get("close", 0)
                            if prev > 0:
                                post_returns.append((curr - prev) / prev)

                if pre_returns:
                    result.pre_event_return = sum(pre_returns) / len(pre_returns)
                if post_returns:
                    result.post_event_return = sum(post_returns) / len(post_returns)

                # Calculate CAR (simple version)
                if result.event_day_return is not None:
                    car = result.event_day_return
                    if post_returns:
                        car += sum(post_returns[:event_window])
                    result.cumulative_abnormal_return = car

                    # Classify market reaction
                    if car < -0.05:
                        result.market_reaction = "strongly_negative"
                    elif car < -0.01:
                        result.market_reaction = "negative"
                    elif car > 0.05:
                        result.market_reaction = "strongly_positive"
                    elif car > 0.01:
                        result.market_reaction = "positive"
                    else:
                        result.market_reaction = "neutral"

        except Exception as e:
            logger.debug(f"Could not calculate event study for {event.event_id}: {e}")

        results.append(result)

    return results


# ── #53: Docket Velocity Indicator ────────────────────────────────────────────


def calculate_docket_velocity(
    ticker: str,
    entity_name: str,
    period_days: int = 90,
) -> DocketVelocity:
    """
    Calculate docket velocity indicator (#53).

    Measures rate of new court filings to detect acceleration
    in litigation activity before it appears in disclosures.

    Args:
        ticker: Stock ticker
        entity_name: Company name
        period_days: Period to measure velocity over

    Returns:
        DocketVelocity with filing rate metrics.
    """
    new_filings = 0
    recent_cases = []
    undisclosed_count = 0
    days_to_disclosure_list = []

    try:
        from app.connectors.litigation_connector import search_federal_cases
        from app.services.docket_disclosure_service import reconcile_litigation

        # Get recent cases
        result = search_federal_cases(entity_name, years=2)
        cases = result.get("cases", [])

        cutoff = datetime.now() - timedelta(days=period_days)
        historical_cutoff = datetime.now() - timedelta(days=365)

        period_cases = []
        historical_cases = []

        for case in cases:
            filed_date = case.get("date_filed", "")
            if not filed_date:
                continue

            try:
                filed_dt = datetime.strptime(filed_date, "%Y-%m-%d")
                if filed_dt >= cutoff:
                    period_cases.append(case)
                    recent_cases.append({
                        "case_name": case.get("case_name", "")[:100],
                        "court": case.get("court", ""),
                        "filed_date": filed_date,
                        "nature_of_suit": case.get("nature_of_suit", ""),
                    })
                elif filed_dt >= historical_cutoff:
                    historical_cases.append(case)
            except ValueError:
                continue

        new_filings = len(period_cases)

        # Calculate average (annualized)
        historical_count = len(historical_cases) + len(period_cases)
        avg_filings = historical_count / (365 / period_days) if historical_count else 1

        # Velocity ratio
        velocity_ratio = new_filings / avg_filings if avg_filings > 0 else 0

        # Get reconciliation to find undisclosed
        try:
            recon = reconcile_litigation(ticker)
            undisclosed_count = recon.summary.get("undisclosed_count", 0)
        except Exception as e:
            logger.debug("Failed to reconcile litigation for %s: %s", ticker, e)

        # Determine alert level
        if velocity_ratio > 3.0 or undisclosed_count > 5:
            alert_level = RiskLevel.CRITICAL
        elif velocity_ratio > 2.0 or undisclosed_count > 2:
            alert_level = RiskLevel.HIGH
        elif velocity_ratio > 1.5 or undisclosed_count > 0:
            alert_level = RiskLevel.MEDIUM
        elif velocity_ratio > 1.0:
            alert_level = RiskLevel.LOW
        else:
            alert_level = RiskLevel.MINIMAL

    except Exception as e:
        logger.warning(f"Error calculating docket velocity for {ticker}: {e}")
        alert_level = RiskLevel.LOW

    return DocketVelocity(
        ticker=ticker,
        company_name=entity_name,
        period_days=period_days,
        new_filings=new_filings,
        avg_filings_per_period=avg_filings if 'avg_filings' in dir() else 0,
        velocity_ratio=velocity_ratio if 'velocity_ratio' in dir() else 0,
        undisclosed_count=undisclosed_count,
        days_to_disclosure_avg=None,  # Would need disclosure dates to calculate
        alert_level=alert_level,
        recent_cases=recent_cases[:10],
    )


# ── #54: Normalized Exposure ──────────────────────────────────────────────────


def calculate_normalized_exposure(
    ticker: str,
    entity_name: str,
) -> NormalizedExposure:
    """
    Calculate litigation exposure normalized to financials (#54).

    Normalizes total litigation exposure against:
    - Annual revenue
    - Book equity
    - Cash position
    - Market cap
    - Total assets

    Args:
        ticker: Stock ticker
        entity_name: Company name

    Returns:
        NormalizedExposure with all normalized metrics.
    """
    total_exposure = 0.0
    case_count = 0
    active_cases = 0
    securities_cases = 0

    try:
        from app.connectors.litigation_connector import get_litigation_intelligence

        # Get litigation data
        lit_data = get_litigation_intelligence(entity_name, ticker)
        federal_cases = lit_data.get("federal_cases", {}).get("cases", [])

        for case in federal_cases:
            case_count += 1
            amount = case.get("amount_claimed") or 0
            total_exposure += amount

            status = case.get("status", "").lower()
            if status not in ["dismissed", "closed", "settled"]:
                active_cases += 1

            case_type = case.get("case_type", "").lower()
            if "securities" in case_type:
                securities_cases += 1

    except Exception as e:
        logger.warning(f"Error getting litigation data for {ticker}: {e}")

    # Get financial data for normalization
    revenue = None
    equity = None
    cash = None
    market_cap = None
    assets = None

    try:
        from app.connectors.market_data_connector import get_company_fundamentals

        fundamentals = get_company_fundamentals(ticker)
        if fundamentals:
            revenue = fundamentals.get("revenue")
            equity = fundamentals.get("total_equity") or fundamentals.get("book_value")
            cash = fundamentals.get("cash") or fundamentals.get("cash_and_equivalents")
            market_cap = fundamentals.get("market_cap")
            assets = fundamentals.get("total_assets")
    except Exception as e:
        logger.debug(f"Could not get fundamentals for {ticker}: {e}")

    # Calculate normalized ratios
    exposure_to_revenue = (total_exposure / revenue * 100) if revenue and revenue > 0 else None
    exposure_to_equity = (total_exposure / equity * 100) if equity and equity > 0 else None
    exposure_to_cash = (total_exposure / cash * 100) if cash and cash > 0 else None
    exposure_to_market_cap = (total_exposure / market_cap * 100) if market_cap and market_cap > 0 else None
    exposure_to_assets = (total_exposure / assets * 100) if assets and assets > 0 else None

    # Determine risk level based on exposure
    risk_level = RiskLevel.MINIMAL
    if exposure_to_market_cap is not None:
        if exposure_to_market_cap > 10:
            risk_level = RiskLevel.CRITICAL
        elif exposure_to_market_cap > 5:
            risk_level = RiskLevel.HIGH
        elif exposure_to_market_cap > 2:
            risk_level = RiskLevel.MEDIUM
        elif exposure_to_market_cap > 0.5:
            risk_level = RiskLevel.LOW
    elif exposure_to_revenue is not None:
        if exposure_to_revenue > 50:
            risk_level = RiskLevel.CRITICAL
        elif exposure_to_revenue > 20:
            risk_level = RiskLevel.HIGH
        elif exposure_to_revenue > 10:
            risk_level = RiskLevel.MEDIUM
        elif exposure_to_revenue > 2:
            risk_level = RiskLevel.LOW

    return NormalizedExposure(
        ticker=ticker,
        company_name=entity_name,
        total_litigation_exposure=total_exposure,
        exposure_to_revenue=exposure_to_revenue,
        exposure_to_equity=exposure_to_equity,
        exposure_to_cash=exposure_to_cash,
        exposure_to_market_cap=exposure_to_market_cap,
        exposure_to_assets=exposure_to_assets,
        industry_avg_exposure=None,  # Would require industry data
        percentile_rank=None,  # Would require peer comparison
        risk_level=risk_level,
        case_count=case_count,
        active_cases=active_cases,
        securities_cases=securities_cases,
    )


# ── #55: Point-in-Time Litigation Panel ───────────────────────────────────────


def get_litigation_snapshot(
    ticker: str,
    entity_name: str,
    as_of_date: Optional[str] = None,
) -> LitigationSnapshot:
    """
    Get point-in-time litigation snapshot (#55).

    Args:
        ticker: Stock ticker
        entity_name: Company name
        as_of_date: Date for snapshot (defaults to today)

    Returns:
        LitigationSnapshot as of the specified date.
    """
    if as_of_date is None:
        as_of_date = datetime.now().strftime("%Y-%m-%d")

    total_cases = 0
    active_cases = 0
    total_exposure = 0.0
    disclosed_exposure = 0.0
    undisclosed_exposure = 0.0
    by_type: Dict[str, int] = defaultdict(int)
    by_status: Dict[str, int] = defaultdict(int)
    risk_score = 0.0

    try:
        from app.services.docket_disclosure_service import reconcile_litigation

        report = reconcile_litigation(ticker)

        # Filter cases by as_of_date
        as_of_dt = datetime.strptime(as_of_date, "%Y-%m-%d")

        for case in report.docket_cases:
            filed_date = case.filed_date
            if not filed_date:
                continue

            try:
                filed_dt = datetime.strptime(filed_date, "%Y-%m-%d")
                if filed_dt <= as_of_dt:
                    total_cases += 1
                    by_type[case.nature_of_suit or "other"] += 1
                    by_status[case.status or "unknown"] += 1

                    if case.amount_claimed:
                        total_exposure += case.amount_claimed

                    if case.status and case.status.lower() not in ["dismissed", "closed", "settled"]:
                        active_cases += 1
            except ValueError:
                continue

        # Calculate disclosed vs undisclosed
        for finding in report.findings:
            if finding.disclosure_status.value == "undisclosed":
                if finding.docket_case and finding.docket_case.amount_claimed:
                    undisclosed_exposure += finding.docket_case.amount_claimed

        disclosed_exposure = total_exposure - undisclosed_exposure
        risk_score = report.risk_score

    except Exception as e:
        logger.warning(f"Error getting litigation snapshot for {ticker}: {e}")

    return LitigationSnapshot(
        ticker=ticker,
        as_of_date=as_of_date,
        total_cases=total_cases,
        active_cases=active_cases,
        total_exposure=total_exposure,
        disclosed_exposure=disclosed_exposure,
        undisclosed_exposure=undisclosed_exposure,
        by_type=dict(by_type),
        by_status=dict(by_status),
        risk_score=risk_score,
    )


def get_litigation_time_series(
    ticker: str,
    entity_name: str,
    start_date: str,
    end_date: Optional[str] = None,
    frequency: str = "quarterly",
) -> LitigationTimeSeries:
    """
    Get point-in-time litigation panel data (#55).

    Generates a time series of litigation snapshots for
    historical analysis and trend detection.

    Args:
        ticker: Stock ticker
        entity_name: Company name
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (defaults to today)
        frequency: Snapshot frequency (daily, weekly, monthly, quarterly)

    Returns:
        LitigationTimeSeries with historical snapshots.
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    snapshots = []

    # Determine date intervals
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    if frequency == "daily":
        delta = timedelta(days=1)
    elif frequency == "weekly":
        delta = timedelta(weeks=1)
    elif frequency == "monthly":
        delta = timedelta(days=30)
    else:  # quarterly
        delta = timedelta(days=91)

    current_dt = start_dt
    while current_dt <= end_dt:
        snapshot = get_litigation_snapshot(
            ticker,
            entity_name,
            current_dt.strftime("%Y-%m-%d"),
        )
        snapshots.append(snapshot)
        current_dt += delta

    return LitigationTimeSeries(
        ticker=ticker,
        company_name=entity_name,
        start_date=start_date,
        end_date=end_date,
        frequency=frequency,
        snapshots=snapshots,
    )


# ── #56: Litigation Screener Fields ───────────────────────────────────────────


def get_screener_fields(
    ticker: str,
    entity_name: str,
) -> LitigationScreenerFields:
    """
    Get litigation fields for screener (#56).

    Consolidates all litigation metrics into fields suitable
    for screening and filtering companies by litigation risk.

    Args:
        ticker: Stock ticker
        entity_name: Company name

    Returns:
        LitigationScreenerFields with all screenable metrics.
    """
    fields = LitigationScreenerFields(
        ticker=ticker,
        company_name=entity_name,
    )

    try:
        # Get velocity data
        velocity = calculate_docket_velocity(ticker, entity_name)
        fields.new_cases_30d = sum(1 for c in velocity.recent_cases
                                    if _within_days(c.get("filed_date", ""), 30))
        fields.new_cases_90d = velocity.new_filings
        fields.velocity_alert = velocity.alert_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]

        # Get normalized exposure
        exposure = calculate_normalized_exposure(ticker, entity_name)
        fields.total_cases = exposure.case_count
        fields.active_cases = exposure.active_cases
        fields.total_exposure_usd = exposure.total_litigation_exposure
        fields.exposure_pct_revenue = exposure.exposure_to_revenue
        fields.exposure_pct_market_cap = exposure.exposure_to_market_cap
        fields.securities_cases = exposure.securities_cases
        fields.risk_level = exposure.risk_level
        fields.exposure_alert = exposure.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]

        # Get litigation intelligence for additional fields
        from app.connectors.litigation_connector import get_litigation_intelligence
        lit_data = get_litigation_intelligence(entity_name, ticker)

        # Count case types
        by_type = lit_data.get("federal_cases", {}).get("by_type", {})
        fields.antitrust_cases = len(by_type.get("antitrust", []))
        fields.patent_cases = len(by_type.get("patent", []))
        fields.regulatory_cases = len(by_type.get("regulatory", []))

        # Check for specific flags
        sec_count = lit_data.get("sec_enforcement", {}).get("summary", {}).get("total_actions", 0)
        fields.has_sec_enforcement = sec_count > 0

        # Check for class actions
        federal_cases = lit_data.get("federal_cases", {}).get("cases", [])
        for case in federal_cases:
            nos = case.get("nature_of_suit", "").lower()
            if "class" in nos or "class action" in case.get("case_name", "").lower():
                fields.has_class_action = True
                break

        # Check for undisclosed
        fields.has_undisclosed = velocity.undisclosed_count > 0

        # Calculate overall risk score
        fields.risk_score = _calculate_screener_risk_score(fields)

    except Exception as e:
        logger.warning(f"Error getting screener fields for {ticker}: {e}")

    return fields


def _within_days(date_str: str, days: int) -> bool:
    """Check if date is within N days of today."""
    if not date_str:
        return False
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return (datetime.now() - dt).days <= days
    except ValueError:
        return False


def _calculate_screener_risk_score(fields: LitigationScreenerFields) -> float:
    """Calculate overall risk score for screener."""
    score = 0.0

    # Case count factor
    if fields.total_cases > 20:
        score += 25
    elif fields.total_cases > 10:
        score += 15
    elif fields.total_cases > 5:
        score += 10

    # Active cases factor
    if fields.active_cases > 10:
        score += 20
    elif fields.active_cases > 5:
        score += 10

    # Exposure factor
    if fields.exposure_pct_market_cap is not None:
        if fields.exposure_pct_market_cap > 10:
            score += 30
        elif fields.exposure_pct_market_cap > 5:
            score += 20
        elif fields.exposure_pct_market_cap > 2:
            score += 10

    # Velocity factor
    if fields.new_cases_30d > 3:
        score += 15
    elif fields.new_cases_30d > 1:
        score += 10

    # Flag factors
    if fields.has_sec_enforcement:
        score += 15
    if fields.has_class_action:
        score += 10
    if fields.has_undisclosed:
        score += 10

    return min(100, score)


def screen_companies(
    tickers: List[str],
    min_risk_score: Optional[float] = None,
    max_risk_score: Optional[float] = None,
    has_sec_enforcement: Optional[bool] = None,
    has_class_action: Optional[bool] = None,
    has_undisclosed: Optional[bool] = None,
    min_exposure_pct: Optional[float] = None,
    max_exposure_pct: Optional[float] = None,
    risk_levels: Optional[List[RiskLevel]] = None,
) -> List[LitigationScreenerFields]:
    """
    Screen companies by litigation criteria (#56).

    Args:
        tickers: List of tickers to screen
        min_risk_score: Minimum risk score filter
        max_risk_score: Maximum risk score filter
        has_sec_enforcement: Filter for SEC enforcement
        has_class_action: Filter for class actions
        has_undisclosed: Filter for undisclosed litigation
        min_exposure_pct: Minimum exposure as % of market cap
        max_exposure_pct: Maximum exposure as % of market cap
        risk_levels: Filter by risk level

    Returns:
        List of companies matching criteria.
    """
    results = []

    for ticker in tickers:
        try:
            # Get entity name (simplified - would use entity resolution)
            entity_name = ticker  # Would normally resolve to company name

            fields = get_screener_fields(ticker, entity_name)

            # Apply filters
            if min_risk_score is not None and fields.risk_score < min_risk_score:
                continue
            if max_risk_score is not None and fields.risk_score > max_risk_score:
                continue
            if has_sec_enforcement is not None and fields.has_sec_enforcement != has_sec_enforcement:
                continue
            if has_class_action is not None and fields.has_class_action != has_class_action:
                continue
            if has_undisclosed is not None and fields.has_undisclosed != has_undisclosed:
                continue
            if min_exposure_pct is not None:
                if fields.exposure_pct_market_cap is None or fields.exposure_pct_market_cap < min_exposure_pct:
                    continue
            if max_exposure_pct is not None:
                if fields.exposure_pct_market_cap is not None and fields.exposure_pct_market_cap > max_exposure_pct:
                    continue
            if risk_levels is not None and fields.risk_level not in risk_levels:
                continue

            results.append(fields)

        except Exception as e:
            logger.debug(f"Error screening {ticker}: {e}")
            continue

    return results
