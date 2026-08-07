"""
Implied Volatility Surface Service (Band B #27)

Features:
- Implied volatility surface (delayed EOD)
- IV term structure
- Skew analysis
- Historical IV comparison
- No OPRA license needed (uses delayed/EOD data)
"""

import math
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import random


# ── Data Models ──────────────────────────────────────────────────────────────

@dataclass
class VolatilitySurface:
    """Implied volatility surface for an underlying."""
    ticker: str
    underlying_price: float
    as_of_date: str
    as_of_time: str
    data_delay_minutes: int  # Transparency: how delayed is this data
    surface: List[Dict[str, Any]]  # List of {strike, expiry, iv, delta, option_type}
    term_structure: List[Dict[str, Any]]  # ATM IV by expiry
    skew: Dict[str, Any]  # Skew metrics

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class VolatilitySnapshot:
    """Current IV snapshot for quick view."""
    ticker: str
    current_price: float
    iv_30d: float
    iv_60d: float
    iv_90d: float
    iv_rank: float  # 0-100, current IV vs 1Y range
    iv_percentile: float  # 0-100, % of days below current IV
    hv_30d: float  # Historical volatility for comparison
    iv_hv_spread: float  # IV - HV
    put_call_skew: float  # 25-delta put IV - 25-delta call IV
    term_slope: float  # Slope of term structure

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class VolatilityHistory:
    """Historical IV data."""
    ticker: str
    period_days: int
    iv_history: List[Dict[str, Any]]  # [{date, iv_30d, iv_60d, hv_30d, ...}]
    iv_high_52w: float
    iv_low_52w: float
    current_iv_rank: float

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class SkewAnalysis:
    """Detailed skew analysis."""
    ticker: str
    expiry: str
    underlying_price: float
    atm_iv: float
    skew_25d: float  # 25-delta put - 25-delta call
    skew_10d: float  # 10-delta put - 10-delta call
    skew_by_strike: List[Dict[str, Any]]  # [{strike, iv, moneyness}]
    skew_percentile: float  # Current skew vs history
    interpretation: str

    def to_dict(self) -> Dict:
        return asdict(self)


# ── Service Implementation ───────────────────────────────────────────────────

class VolatilityService:
    """Implied volatility surface and analysis service."""

    # Standard expiry months
    EXPIRY_MONTHS = [1, 2, 3, 6, 9, 12]

    def __init__(self):
        self._cache = {}
        self._history_cache = {}

    def _generate_iv_surface(
        self,
        ticker: str,
        base_price: float,
        base_iv: float
    ) -> List[Dict]:
        """Generate mock IV surface data."""
        surface = []
        today = datetime.now()

        for months in self.EXPIRY_MONTHS:
            expiry = today + timedelta(days=months * 30)
            expiry_str = expiry.strftime('%Y-%m-%d')

            # Time-to-expiry IV adjustment (term structure)
            time_adjustment = math.sqrt(months / 12) * 0.1

            # Generate strikes around ATM
            for pct in [-20, -15, -10, -5, -2, 0, 2, 5, 10, 15, 20]:
                strike = round(base_price * (1 + pct / 100), 2)
                moneyness = strike / base_price

                # Skew: OTM puts have higher IV
                skew_adjustment = 0
                if pct < 0:  # OTM puts
                    skew_adjustment = abs(pct) * 0.002  # 0.2% IV per 1% OTM
                elif pct > 0:  # OTM calls
                    skew_adjustment = -pct * 0.001  # Slight decline for OTM calls

                # Calculate IV with smile
                iv = base_iv + time_adjustment + skew_adjustment
                iv += random.uniform(-0.01, 0.01)  # Small noise
                iv = max(0.05, min(2.0, iv))  # Bound IV

                # Delta approximation (simplified)
                if pct <= 0:
                    delta_put = -0.5 + pct * 0.02
                    delta_call = delta_put + 1
                else:
                    delta_call = 0.5 - pct * 0.02
                    delta_put = delta_call - 1

                surface.append({
                    'strike': strike,
                    'expiry': expiry_str,
                    'expiry_months': months,
                    'moneyness': round(moneyness, 3),
                    'iv': round(iv, 4),
                    'delta_call': round(delta_call, 3),
                    'delta_put': round(delta_put, 3),
                    'option_type': 'both',
                })

        return surface

    def _calculate_term_structure(
        self,
        surface: List[Dict],
        base_price: float
    ) -> List[Dict]:
        """Extract ATM term structure from surface."""
        term_structure = []

        # Group by expiry
        by_expiry = {}
        for point in surface:
            exp = point['expiry']
            if exp not in by_expiry:
                by_expiry[exp] = []
            by_expiry[exp].append(point)

        for expiry, points in sorted(by_expiry.items()):
            # Find closest to ATM
            atm_point = min(points, key=lambda p: abs(p['strike'] - base_price))
            term_structure.append({
                'expiry': expiry,
                'expiry_months': atm_point['expiry_months'],
                'atm_iv': atm_point['iv'],
                'atm_strike': atm_point['strike'],
            })

        return term_structure

    def _calculate_skew(
        self,
        surface: List[Dict],
        base_price: float
    ) -> Dict:
        """Calculate skew metrics from surface."""
        # Group by expiry, focus on nearest
        front_month = [p for p in surface if p['expiry_months'] == 1]

        if not front_month:
            return {'skew_25d': 0, 'skew_10d': 0}

        # Find approximate 25-delta strikes
        put_25d = None
        call_25d = None
        for p in front_month:
            if -0.30 <= p['delta_put'] <= -0.20:
                put_25d = p
            if 0.20 <= p['delta_call'] <= 0.30:
                call_25d = p

        skew_25d = 0
        if put_25d and call_25d:
            skew_25d = put_25d['iv'] - call_25d['iv']

        return {
            'skew_25d': round(skew_25d, 4),
            'skew_10d': round(skew_25d * 1.5, 4),  # Approximation
            'put_25d_iv': put_25d['iv'] if put_25d else None,
            'call_25d_iv': call_25d['iv'] if call_25d else None,
            'put_25d_strike': put_25d['strike'] if put_25d else None,
            'call_25d_strike': call_25d['strike'] if call_25d else None,
        }

    def get_volatility_surface(self, ticker: str) -> VolatilitySurface:
        """Get full IV surface for a ticker."""
        # Mock underlying data
        base_prices = {
            'NVDA': 875.50,
            'AAPL': 185.25,
            'TSLA': 245.80,
            'MSFT': 415.30,
            'META': 505.20,
            'AMD': 165.40,
            'AMZN': 185.75,
            'GOOGL': 175.60,
        }
        base_ivs = {
            'NVDA': 0.48,
            'AAPL': 0.22,
            'TSLA': 0.55,
            'MSFT': 0.20,
            'META': 0.35,
            'AMD': 0.45,
            'AMZN': 0.28,
            'GOOGL': 0.25,
        }

        price = base_prices.get(ticker, random.uniform(50, 500))
        base_iv = base_ivs.get(ticker, random.uniform(0.2, 0.6))

        surface = self._generate_iv_surface(ticker, price, base_iv)
        term_structure = self._calculate_term_structure(surface, price)
        skew = self._calculate_skew(surface, price)

        now = datetime.now()

        return VolatilitySurface(
            ticker=ticker,
            underlying_price=round(price, 2),
            as_of_date=now.strftime('%Y-%m-%d'),
            as_of_time=(now - timedelta(minutes=15)).strftime('%H:%M:%S'),
            data_delay_minutes=15,
            surface=surface,
            term_structure=term_structure,
            skew=skew,
        )

    def get_volatility_snapshot(self, ticker: str) -> VolatilitySnapshot:
        """Get quick IV snapshot for a ticker."""
        surface = self.get_volatility_surface(ticker)

        # Extract key metrics
        term = surface.term_structure
        iv_30d = term[0]['atm_iv'] if len(term) > 0 else 0.3
        iv_60d = term[1]['atm_iv'] if len(term) > 1 else iv_30d * 1.02
        iv_90d = term[2]['atm_iv'] if len(term) > 2 else iv_30d * 1.04

        # Mock historical volatility (typically lower than IV)
        hv_30d = iv_30d * random.uniform(0.7, 0.95)

        # IV rank and percentile (mock)
        iv_rank = random.uniform(20, 80)
        iv_percentile = random.uniform(20, 80)

        # Term slope
        term_slope = (iv_90d - iv_30d) / 60 * 30  # Per 30 days

        return VolatilitySnapshot(
            ticker=ticker,
            current_price=surface.underlying_price,
            iv_30d=round(iv_30d, 4),
            iv_60d=round(iv_60d, 4),
            iv_90d=round(iv_90d, 4),
            iv_rank=round(iv_rank, 1),
            iv_percentile=round(iv_percentile, 1),
            hv_30d=round(hv_30d, 4),
            iv_hv_spread=round(iv_30d - hv_30d, 4),
            put_call_skew=round(surface.skew.get('skew_25d', 0), 4),
            term_slope=round(term_slope, 4),
        )

    def get_volatility_history(
        self,
        ticker: str,
        days: int = 252
    ) -> VolatilityHistory:
        """Get historical IV data."""
        cache_key = f"{ticker}_{days}"
        if cache_key in self._history_cache:
            return self._history_cache[cache_key]

        # Generate mock history
        base_iv = random.uniform(0.2, 0.5)
        history = []
        today = datetime.now()

        iv_high = 0
        iv_low = 1

        for i in range(days):
            date = today - timedelta(days=days - i)

            # Random walk with mean reversion
            iv_30d = base_iv + random.gauss(0, 0.02)
            iv_30d = max(0.1, min(1.5, iv_30d))
            base_iv = base_iv * 0.95 + iv_30d * 0.05  # Mean reversion

            iv_high = max(iv_high, iv_30d)
            iv_low = min(iv_low, iv_30d)

            hv_30d = iv_30d * random.uniform(0.6, 0.95)

            history.append({
                'date': date.strftime('%Y-%m-%d'),
                'iv_30d': round(iv_30d, 4),
                'iv_60d': round(iv_30d * 1.02, 4),
                'hv_30d': round(hv_30d, 4),
                'iv_hv_spread': round(iv_30d - hv_30d, 4),
            })

        # Current IV rank
        current_iv = history[-1]['iv_30d'] if history else 0.3
        iv_rank = ((current_iv - iv_low) / (iv_high - iv_low)) * 100 if iv_high > iv_low else 50

        result = VolatilityHistory(
            ticker=ticker,
            period_days=days,
            iv_history=history,
            iv_high_52w=round(iv_high, 4),
            iv_low_52w=round(iv_low, 4),
            current_iv_rank=round(iv_rank, 1),
        )

        self._history_cache[cache_key] = result
        return result

    def get_skew_analysis(
        self,
        ticker: str,
        expiry: Optional[str] = None
    ) -> SkewAnalysis:
        """Get detailed skew analysis."""
        surface = self.get_volatility_surface(ticker)

        # Filter by expiry if specified, else use front month
        if expiry:
            points = [p for p in surface.surface if p['expiry'] == expiry]
        else:
            points = [p for p in surface.surface if p['expiry_months'] == 1]
            expiry = points[0]['expiry'] if points else datetime.now().strftime('%Y-%m-%d')

        if not points:
            return SkewAnalysis(
                ticker=ticker,
                expiry=expiry,
                underlying_price=surface.underlying_price,
                atm_iv=0,
                skew_25d=0,
                skew_10d=0,
                skew_by_strike=[],
                skew_percentile=50,
                interpretation='No data available',
            )

        # Find ATM IV
        atm_point = min(points, key=lambda p: abs(p['moneyness'] - 1))

        # Build skew by strike
        skew_by_strike = [
            {
                'strike': p['strike'],
                'iv': p['iv'],
                'moneyness': p['moneyness'],
                'iv_diff_from_atm': round(p['iv'] - atm_point['iv'], 4),
            }
            for p in sorted(points, key=lambda x: x['strike'])
        ]

        # Interpretation
        skew_25d = surface.skew.get('skew_25d', 0)
        if skew_25d > 0.05:
            interpretation = 'Elevated put skew - market pricing downside risk'
        elif skew_25d > 0.02:
            interpretation = 'Moderate put skew - normal protective put demand'
        elif skew_25d < -0.02:
            interpretation = 'Call skew - unusual upside demand (squeeze potential?)'
        else:
            interpretation = 'Flat skew - balanced market expectations'

        return SkewAnalysis(
            ticker=ticker,
            expiry=expiry,
            underlying_price=surface.underlying_price,
            atm_iv=atm_point['iv'],
            skew_25d=surface.skew.get('skew_25d', 0),
            skew_10d=surface.skew.get('skew_10d', 0),
            skew_by_strike=skew_by_strike,
            skew_percentile=random.uniform(30, 70),
            interpretation=interpretation,
        )

    def screen_volatility(
        self,
        min_iv_rank: float = 0,
        max_iv_rank: float = 100,
        min_iv_hv_spread: float = -1,
        tickers: Optional[List[str]] = None
    ) -> List[Dict]:
        """Screen stocks by volatility criteria."""
        default_tickers = ['NVDA', 'AAPL', 'TSLA', 'MSFT', 'META', 'AMD', 'AMZN', 'GOOGL',
                          'NFLX', 'CRM', 'ORCL', 'INTC', 'QCOM', 'AVGO', 'MU']

        tickers = tickers or default_tickers
        results = []

        for ticker in tickers:
            snapshot = self.get_volatility_snapshot(ticker)

            if min_iv_rank <= snapshot.iv_rank <= max_iv_rank:
                if snapshot.iv_hv_spread >= min_iv_hv_spread:
                    results.append(snapshot.to_dict())

        # Sort by IV rank descending
        results.sort(key=lambda x: x['iv_rank'], reverse=True)
        return results


# ── Module-level instance ────────────────────────────────────────────────────

_service_instance = None

def get_volatility_service() -> VolatilityService:
    """Get singleton service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = VolatilityService()
    return _service_instance
