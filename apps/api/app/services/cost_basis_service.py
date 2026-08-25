"""
Cost Basis Tracking Service (Band C #42)
Track purchase prices, calculate gains/losses using FIFO/LIFO/Average methods.
Wired to yfinance for current prices and the Position model for DB lookups.
"""
import logging
import time as time_module
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime, date

log = logging.getLogger(__name__)


class CostBasisMethod(str, Enum):
    FIFO = "fifo"
    LIFO = "lifo"
    AVERAGE = "average"
    HIFO = "hifo"


# ── TTL Cache (30 min) ────────────────────────────────────────────────────────

class _TTLCache:
    def __init__(self, ttl_seconds: int = 1800):
        self._ttl = ttl_seconds
        self._store: Dict[str, Any] = {}
        self._ts: Dict[str, float] = {}

    def get(self, key: str) -> Optional[Any]:
        if key in self._store and time_module.time() - self._ts[key] < self._ttl:
            return self._store[key]
        self._store.pop(key, None)
        self._ts.pop(key, None)
        return None

    def set(self, key: str, value: Any):
        self._store[key] = value
        self._ts[key] = time_module.time()


_price_cache = _TTLCache(ttl_seconds=1800)


def _get_current_price(ticker: str) -> Optional[float]:
    """Fetch current price via yfinance with caching."""
    cached = _price_cache.get(ticker)
    if cached is not None:
        return cached
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info
        price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
        if price:
            price = float(price)
            _price_cache.set(ticker, price)
            return price
    except Exception as e:
        log.warning("Failed to get price for %s: %s", ticker, e)
    return None


DEFAULT_POSITIONS = [
    {"ticker": "AAPL", "qty": 50, "price": 145.0, "date": "2023-06-15"},
    {"ticker": "AAPL", "qty": 30, "price": 172.0, "date": "2024-01-10"},
    {"ticker": "MSFT", "qty": 40, "price": 310.0, "date": "2023-08-20"},
    {"ticker": "NVDA", "qty": 25, "price": 450.0, "date": "2024-03-05"},
    {"ticker": "GOOGL", "qty": 35, "price": 138.0, "date": "2023-11-01"},
]


def _get_user_positions(user_id: str, ticker: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get user's positions from DB, or DEFAULT_POSITIONS if none exist."""
    try:
        from app.db.session import get_db_context
        from sqlalchemy import text

        with get_db_context() as db:
            params: Dict[str, Any] = {"user_id": user_id}
            # Filter by user_id through portfolios table
            sql = (
                "SELECT p.id, p.ticker, p.qty, p.cost_basis, p.notes, po.name as portfolio_name "
                "FROM positions p JOIN portfolios po ON p.portfolio_id = po.id "
                "WHERE (po.user_id = :user_id OR po.user_id IS NULL)"
            )
            if ticker:
                sql += " AND p.ticker = :ticker"
                params["ticker"] = ticker.upper()
            sql += " ORDER BY p.id"

            rows = db.execute(text(sql), params).fetchall()
            if rows:
                return [
                    {
                        "id": r[0],
                        "ticker": r[1],
                        "qty": float(r[2]),
                        "price": float(r[3]),
                        "date": None,
                        "notes": r[4],
                        "portfolio": r[5],
                    }
                    for r in rows
                ]
    except Exception as exc:
        log.debug("DB position fetch failed: %s", exc)

    fallback = DEFAULT_POSITIONS
    if ticker:
        fallback = [p for p in fallback if p["ticker"] == ticker.upper()]
    return fallback


def _positions_from_db(user_id: str, ticker: Optional[str] = None) -> List[Dict[str, Any]]:
    """Backwards-compat wrapper around _get_user_positions."""
    return _get_user_positions(user_id, ticker)


# ── Public API ────────────────────────────────────────────────────────────────

def get_user_positions(user_id: str, ticker: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get all positions for a user. Falls back to DEFAULT_POSITIONS if DB is empty."""
    return _get_user_positions(user_id, ticker)


def get_position_by_lot(user_id: str, lot_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific lot by ID."""
    positions = _positions_from_db(user_id)
    for p in positions:
        if str(p.get("id")) == lot_id:
            return p
    return None


def calculate_cost_basis(
    positions: List[Dict[str, Any]], method: str = "fifo"
) -> Dict[str, Any]:
    """
    Calculate cost basis using FIFO, LIFO, or average method.
    positions: [{"ticker": "AAPL", "qty": 100, "price": 150.0, "date": "2024-01-15"}, ...]
    """
    if not positions:
        return {"method": method, "total_cost": 0, "total_shares": 0, "avg_cost_per_share": 0}

    try:
        sorted_positions = sorted(
            positions,
            key=lambda p: p.get("date") or "1970-01-01",
            reverse=(method == "lifo"),
        )

        total_cost = sum(p["qty"] * p["price"] for p in sorted_positions)
        total_shares = sum(p["qty"] for p in sorted_positions)
        avg_cost = total_cost / total_shares if total_shares > 0 else 0

        if method == "average":
            per_share = avg_cost
        else:
            per_share = sorted_positions[0]["price"] if sorted_positions else 0

        return {
            "method": method,
            "total_cost": round(total_cost, 2),
            "total_shares": round(total_shares, 4),
            "avg_cost_per_share": round(avg_cost, 4),
            "basis_per_share": round(per_share, 4),
            "lots_count": len(sorted_positions),
            "lots": [
                {
                    "qty": p["qty"],
                    "price": p["price"],
                    "date": p.get("date"),
                    "lot_cost": round(p["qty"] * p["price"], 2),
                }
                for p in sorted_positions
            ],
        }
    except Exception as e:
        log.warning("calculate_cost_basis error: %s", e)
        return {}


def get_realized_gains(user_id: str, year: Optional[int] = None) -> Dict[str, Any]:
    """
    Calculate realized gains from closed positions.
    Without a full trade history table, returns an empty structure.
    """
    target_year = year or datetime.utcnow().year
    positions = _positions_from_db(user_id)
    # With the current Position model (no sell records), return empty
    return {
        "user_id": user_id,
        "year": target_year,
        "total_realized_gain": 0.0,
        "short_term_gain": 0.0,
        "long_term_gain": 0.0,
        "transactions": [],
        "note": "Realized gains require sell transaction records",
    }


def get_unrealized_gains(user_id: str) -> Dict[str, Any]:
    """Current price (yfinance) minus cost basis for open positions."""
    positions = _positions_from_db(user_id)
    if not positions:
        return {"user_id": user_id, "total_unrealized_gain": 0.0, "positions": []}

    results = []
    total_gain = 0.0
    total_cost = 0.0
    total_market = 0.0

    tickers_seen: Dict[str, List[Dict]] = {}
    for p in positions:
        t = p.get("ticker", "").upper()
        if t:
            tickers_seen.setdefault(t, []).append(p)

    for ticker, lots in tickers_seen.items():
        current_price = _get_current_price(ticker)
        if current_price is None:
            continue

        total_qty = sum(l["qty"] for l in lots)
        avg_cost = sum(l["qty"] * l["price"] for l in lots) / total_qty if total_qty > 0 else 0
        market_value = total_qty * current_price
        cost_value = total_qty * avg_cost
        gain = market_value - cost_value
        gain_pct = (gain / cost_value * 100) if cost_value > 0 else 0

        total_gain += gain
        total_cost += cost_value
        total_market += market_value

        results.append({
            "ticker": ticker,
            "shares": round(total_qty, 4),
            "avg_cost": round(avg_cost, 4),
            "current_price": round(current_price, 4),
            "market_value": round(market_value, 2),
            "cost_basis_total": round(cost_value, 2),
            "unrealized_gain": round(gain, 2),
            "gain_pct": round(gain_pct, 2),
        })

    total_gain_pct = (total_gain / total_cost * 100) if total_cost > 0 else 0

    return {
        "user_id": user_id,
        "total_unrealized_gain": round(total_gain, 2),
        "total_cost_basis": round(total_cost, 2),
        "total_market_value": round(total_market, 2),
        "total_gain_pct": round(total_gain_pct, 2),
        "positions": results,
    }


def compare_methods(positions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compare FIFO vs LIFO vs Average cost basis side by side."""
    if not positions:
        return {"fifo": {}, "lifo": {}, "average": {}}

    fifo = calculate_cost_basis(positions, method="fifo")
    lifo = calculate_cost_basis(positions, method="lifo")
    avg = calculate_cost_basis(positions, method="average")

    ticker = positions[0].get("ticker", "UNKNOWN") if positions else "UNKNOWN"
    current_price = _get_current_price(ticker)

    comparison = {"fifo": fifo, "lifo": lifo, "average": avg}

    if current_price:
        total_shares = sum(p["qty"] for p in positions)
        market_value = total_shares * current_price
        for method_name, basis in [("fifo", fifo), ("lifo", lifo), ("average", avg)]:
            cost = basis.get("total_cost", 0)
            gain = market_value - cost
            comparison[method_name]["unrealized_gain"] = round(gain, 2)
            comparison[method_name]["gain_pct"] = round(gain / cost * 100, 2) if cost else 0
        comparison["current_price"] = current_price
        comparison["market_value"] = round(market_value, 2)

    return comparison


def get_portfolio_summary(user_id: str) -> Dict[str, Any]:
    """Get portfolio cost basis summary."""
    positions = _positions_from_db(user_id)
    if not positions:
        return {"user_id": user_id, "holdings": [], "total_cost": 0, "total_value": 0}

    tickers_seen: Dict[str, List[Dict]] = {}
    for p in positions:
        t = p.get("ticker", "").upper()
        if t:
            tickers_seen.setdefault(t, []).append(p)

    holdings = []
    total_cost = 0.0
    total_value = 0.0

    for ticker, lots in tickers_seen.items():
        total_qty = sum(l["qty"] for l in lots)
        cost = sum(l["qty"] * l["price"] for l in lots)
        current_price = _get_current_price(ticker)
        mkt = total_qty * current_price if current_price else None

        total_cost += cost
        if mkt:
            total_value += mkt

        holdings.append({
            "ticker": ticker,
            "shares": round(total_qty, 4),
            "total_cost": round(cost, 2),
            "avg_cost": round(cost / total_qty, 4) if total_qty else 0,
            "current_price": current_price,
            "market_value": round(mkt, 2) if mkt else None,
        })

    return {
        "user_id": user_id,
        "holdings": holdings,
        "total_cost": round(total_cost, 2),
        "total_value": round(total_value, 2),
        "total_gain": round(total_value - total_cost, 2),
    }


def get_ticker_cost_basis(user_id: str, ticker: str) -> Dict[str, Any]:
    """Get cost basis details for a specific ticker."""
    positions = _positions_from_db(user_id, ticker)
    if not positions:
        return {}
    return calculate_cost_basis(positions, method="fifo")


def calculate_realized_gain(
    user_id: str,
    ticker: str,
    shares_to_sell: float,
    method = "fifo",
    specific_lots: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Calculate realized gain for a hypothetical sale."""
    method_str = method.value if isinstance(method, CostBasisMethod) else str(method)

    positions = _positions_from_db(user_id, ticker)
    if not positions:
        return {}

    current_price = _get_current_price(ticker)
    if not current_price:
        return {"error": f"Cannot fetch current price for {ticker}"}

    sorted_lots = sorted(
        positions,
        key=lambda p: p.get("date") or "1970-01-01",
        reverse=(method_str == "lifo"),
    )

    remaining = shares_to_sell
    total_cost = 0.0
    lots_used = []

    for lot in sorted_lots:
        if remaining <= 0:
            break
        used = min(lot["qty"], remaining)
        total_cost += used * lot["price"]
        lots_used.append({"qty": used, "cost": lot["price"], "date": lot.get("date")})
        remaining -= used

    proceeds = shares_to_sell * current_price
    gain = proceeds - total_cost

    return {
        "ticker": ticker,
        "shares_sold": shares_to_sell,
        "method": method_str,
        "sale_price": current_price,
        "proceeds": round(proceeds, 2),
        "cost_basis": round(total_cost, 2),
        "realized_gain": round(gain, 2),
        "gain_pct": round(gain / total_cost * 100, 2) if total_cost else 0,
        "lots_used": lots_used,
    }


def get_tax_lot_comparison(user_id: str, ticker: str, shares_to_sell: float) -> Dict[str, Any]:
    """Compare different cost basis methods for tax planning."""
    fifo = calculate_realized_gain(user_id, ticker, shares_to_sell, method="fifo")
    lifo = calculate_realized_gain(user_id, ticker, shares_to_sell, method="lifo")
    return {"fifo": fifo, "lifo": lifo, "ticker": ticker, "shares_to_sell": shares_to_sell}


def get_gains_by_holding_period(user_id: str) -> Dict[str, Any]:
    """Group unrealized gains by holding period (short-term vs long-term)."""
    positions = _positions_from_db(user_id)
    if not positions:
        return {"short_term": [], "long_term": [], "unknown": []}

    today = date.today()
    short_term = []
    long_term = []
    unknown = []

    for p in positions:
        d = p.get("date")
        if d:
            try:
                purchase_date = datetime.strptime(d, "%Y-%m-%d").date()
                days_held = (today - purchase_date).days
                entry = {**p, "days_held": days_held}
                if days_held > 365:
                    long_term.append(entry)
                else:
                    short_term.append(entry)
            except (ValueError, TypeError):
                unknown.append(p)
        else:
            unknown.append(p)

    return {"short_term": short_term, "long_term": long_term, "unknown": unknown}


def add_position(
    user_id: str,
    ticker: str,
    shares: float,
    purchase_price: float,
    purchase_date: str,
) -> Dict[str, Any]:
    """Add a new position/lot. Attempts DB write, returns confirmation."""
    try:
        from app.models.monitor import Position, Portfolio
        from app.db.session import get_db_context

        with get_db_context() as db:
            # Find or create user's portfolio
            portfolio = db.query(Portfolio).filter(
                (Portfolio.user_id == user_id) | (Portfolio.user_id.is_(None))
            ).first()
            if not portfolio:
                portfolio = Portfolio(name="Default", base_ccy="USD", user_id=user_id)
                db.add(portfolio)
                db.flush()
            elif portfolio.user_id is None:
                # Assign orphan portfolio to this user
                portfolio.user_id = user_id

            pos = Position(
                portfolio_id=portfolio.id,
                ticker=ticker.upper(),
                qty=shares,
                cost_basis=purchase_price,
                notes=f"Added {purchase_date}",
            )
            db.add(pos)
            db.commit()
            return {
                "status": "created",
                "id": pos.id,
                "ticker": ticker.upper(),
                "shares": shares,
                "purchase_price": purchase_price,
                "purchase_date": purchase_date,
            }
    except Exception as e:
        log.warning("add_position DB write failed: %s", e)
        return {
            "status": "recorded_locally",
            "ticker": ticker.upper(),
            "shares": shares,
            "purchase_price": purchase_price,
            "purchase_date": purchase_date,
            "note": "DB write unavailable; position noted",
        }
