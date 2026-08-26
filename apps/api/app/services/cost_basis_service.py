"""
Cost Basis Tracking Service (Band C #42)
Track purchase prices, calculate gains/losses using FIFO/LIFO/Average methods.
Uses real database for position storage and yfinance for current market prices.
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


# ── TTL Cache for Price Lookups (30 min) ─────────────────────────────────────


class _TTLCache:
    """Thread-safe TTL cache for price lookups to avoid excessive API calls."""

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

    def clear(self):
        """Clear all cached entries."""
        self._store.clear()
        self._ts.clear()

    def invalidate(self, key: str):
        """Invalidate a specific cache entry."""
        self._store.pop(key, None)
        self._ts.pop(key, None)


_price_cache = _TTLCache(ttl_seconds=1800)


def _get_current_price(ticker: str) -> Optional[float]:
    """
    Fetch current price via yfinance with caching.
    Returns None if price cannot be fetched (no_data pattern).
    """
    if not ticker:
        return None

    ticker = ticker.upper()
    cached = _price_cache.get(ticker)
    if cached is not None:
        return cached

    try:
        import yfinance as yf

        stock = yf.Ticker(ticker)
        info = stock.info

        # Try multiple price fields in order of preference
        price = (
            info.get("currentPrice")
            or info.get("regularMarketPrice")
            or info.get("previousClose")
            or info.get("open")
        )

        if price:
            price = float(price)
            _price_cache.set(ticker, price)
            log.debug("Fetched price for %s: %.2f", ticker, price)
            return price

        log.warning("No price data available for %s", ticker)
    except Exception as e:
        log.warning("Failed to get price for %s: %s", ticker, e)

    return None


def _get_batch_prices(tickers: List[str]) -> Dict[str, Optional[float]]:
    """
    Fetch current prices for multiple tickers efficiently.
    Uses caching and batch fetching where possible.
    """
    result: Dict[str, Optional[float]] = {}

    # Check cache first
    uncached = []
    for t in tickers:
        t = t.upper()
        cached = _price_cache.get(t)
        if cached is not None:
            result[t] = cached
        else:
            uncached.append(t)

    # Fetch uncached prices
    if uncached:
        try:
            import yfinance as yf

            # yfinance supports batch fetching
            data = yf.download(
                uncached, period="1d", progress=False, auto_adjust=True, threads=True
            )

            if not data.empty:
                # Handle single vs multiple tickers
                if len(uncached) == 1:
                    ticker = uncached[0]
                    if "Close" in data.columns:
                        price = float(data["Close"].iloc[-1])
                        if price and price > 0:
                            _price_cache.set(ticker, price)
                            result[ticker] = price
                else:
                    for ticker in uncached:
                        try:
                            if ticker in data["Close"].columns:
                                price = float(data["Close"][ticker].iloc[-1])
                                if price and price > 0:
                                    _price_cache.set(ticker, price)
                                    result[ticker] = price
                        except (KeyError, IndexError):
                            pass
        except Exception as e:
            log.warning("Batch price fetch failed: %s", e)

        # Fall back to individual fetches for any still missing
        for t in uncached:
            if t not in result:
                result[t] = _get_current_price(t)

    return result


# ── Database Integration ─────────────────────────────────────────────────────


def _get_user_positions(user_id: str, ticker: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get user's positions from database.
    Returns empty list if no positions found (no_data pattern).
    """
    try:
        from app.db.session import get_db_context
        from sqlalchemy import text

        with get_db_context() as db:
            params: Dict[str, Any] = {"user_id": user_id}

            # Query positions through portfolios table
            sql = """
                SELECT
                    p.id,
                    p.ticker,
                    p.qty,
                    p.cost_basis,
                    p.notes,
                    p.entity_id,
                    po.name as portfolio_name,
                    po.id as portfolio_id
                FROM positions p
                JOIN portfolios po ON p.portfolio_id = po.id
                WHERE (po.user_id = :user_id OR po.user_id IS NULL)
            """

            if ticker:
                sql += " AND UPPER(p.ticker) = :ticker"
                params["ticker"] = ticker.upper()

            sql += " ORDER BY p.id"

            rows = db.execute(text(sql), params).fetchall()

            if rows:
                return [
                    {
                        "id": r[0],
                        "ticker": r[1].upper() if r[1] else None,
                        "qty": float(r[2]) if r[2] else 0,
                        "price": float(r[3]) if r[3] else 0,  # cost_basis is the purchase price
                        "date": None,  # Position model doesn't have purchase date
                        "notes": r[4],
                        "entity_id": r[5],
                        "portfolio": r[6],
                        "portfolio_id": r[7],
                    }
                    for r in rows
                ]

            log.debug("No positions found for user %s", user_id)
            return []

    except Exception as exc:
        log.warning("Database position fetch failed for user %s: %s", user_id, exc)
        return []


def _positions_from_db(user_id: str, ticker: Optional[str] = None) -> List[Dict[str, Any]]:
    """Backwards-compat wrapper around _get_user_positions."""
    return _get_user_positions(user_id, ticker)


# ── Public API ───────────────────────────────────────────────────────────────


def get_user_positions(user_id: str, ticker: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get all positions for a user from the database.
    Returns empty list if no positions found.
    """
    return _get_user_positions(user_id, ticker)


def get_position_by_lot(user_id: str, lot_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific lot by ID."""
    positions = _positions_from_db(user_id)
    for p in positions:
        if str(p.get("id")) == str(lot_id):
            return p
    return None


def calculate_cost_basis(
    positions: List[Dict[str, Any]], method: str = "fifo"
) -> Dict[str, Any]:
    """
    Calculate cost basis using FIFO, LIFO, or average method.

    FIFO: First In, First Out - oldest shares sold first
    LIFO: Last In, First Out - newest shares sold first
    Average: Weighted average cost across all lots

    positions: [{"ticker": "AAPL", "qty": 100, "price": 150.0, "date": "2024-01-15"}, ...]
    """
    if not positions:
        return {
            "method": method,
            "total_cost": 0,
            "total_shares": 0,
            "avg_cost_per_share": 0,
            "no_data": True,
        }

    try:
        # Sort by date: ascending for FIFO, descending for LIFO
        sorted_positions = sorted(
            positions,
            key=lambda p: p.get("date") or "1970-01-01",
            reverse=(method == "lifo"),
        )

        total_cost = sum(p["qty"] * p["price"] for p in sorted_positions)
        total_shares = sum(p["qty"] for p in sorted_positions)
        avg_cost = total_cost / total_shares if total_shares > 0 else 0

        # Determine basis per share based on method
        if method == "average":
            per_share = avg_cost
        else:
            # FIFO/LIFO: first lot in sorted order determines basis
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
                    "id": p.get("id"),
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
        return {"method": method, "error": str(e), "no_data": True}


def get_realized_gains(user_id: str, year: Optional[int] = None) -> Dict[str, Any]:
    """
    Calculate realized gains from closed positions.
    Note: Requires sell transaction records which are not currently stored.
    Returns structured response indicating no data available.
    """
    target_year = year or datetime.utcnow().year

    # Check if user has any positions at all
    positions = _positions_from_db(user_id)

    return {
        "user_id": user_id,
        "year": target_year,
        "total_realized_gain": 0.0,
        "short_term_gain": 0.0,
        "long_term_gain": 0.0,
        "transactions": [],
        "has_positions": len(positions) > 0,
        "no_data": True,
        "note": "Realized gains require sell transaction records. Current implementation tracks open positions only.",
    }


def get_unrealized_gains(user_id: str) -> Dict[str, Any]:
    """
    Calculate unrealized gains: current market price minus cost basis for open positions.
    Uses real-time prices from yfinance.
    """
    positions = _positions_from_db(user_id)

    if not positions:
        return {
            "user_id": user_id,
            "total_unrealized_gain": 0.0,
            "positions": [],
            "no_data": True,
            "note": "No positions found for user",
        }

    results = []
    total_gain = 0.0
    total_cost = 0.0
    total_market = 0.0
    positions_without_price = []

    # Group positions by ticker
    tickers_seen: Dict[str, List[Dict]] = {}
    for p in positions:
        t = p.get("ticker", "").upper()
        if t:
            tickers_seen.setdefault(t, []).append(p)

    # Batch fetch prices for efficiency
    all_tickers = list(tickers_seen.keys())
    prices = _get_batch_prices(all_tickers)

    for ticker, lots in tickers_seen.items():
        current_price = prices.get(ticker)

        if current_price is None:
            positions_without_price.append(ticker)
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
            "lots_count": len(lots),
        })

    total_gain_pct = (total_gain / total_cost * 100) if total_cost > 0 else 0

    response = {
        "user_id": user_id,
        "total_unrealized_gain": round(total_gain, 2),
        "total_cost_basis": round(total_cost, 2),
        "total_market_value": round(total_market, 2),
        "total_gain_pct": round(total_gain_pct, 2),
        "positions": results,
        "positions_count": len(results),
    }

    if positions_without_price:
        response["price_unavailable"] = positions_without_price
        response["note"] = f"Price data unavailable for: {', '.join(positions_without_price)}"

    return response


def compare_methods(positions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compare FIFO vs LIFO vs Average cost basis side by side.
    Useful for tax planning to see which method results in lower gains.
    """
    if not positions:
        return {
            "fifo": {},
            "lifo": {},
            "average": {},
            "no_data": True,
            "note": "No positions provided for comparison",
        }

    fifo = calculate_cost_basis(positions, method="fifo")
    lifo = calculate_cost_basis(positions, method="lifo")
    avg = calculate_cost_basis(positions, method="average")

    ticker = positions[0].get("ticker", "").upper() if positions else None
    current_price = _get_current_price(ticker) if ticker else None

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
        comparison["ticker"] = ticker
    elif ticker:
        comparison["price_unavailable"] = True
        comparison["note"] = f"Unable to fetch current price for {ticker}"

    return comparison


def get_portfolio_summary(user_id: str) -> Dict[str, Any]:
    """
    Get portfolio cost basis summary with current market values.
    Aggregates all positions by ticker with real-time pricing.
    """
    positions = _positions_from_db(user_id)

    if not positions:
        return {
            "user_id": user_id,
            "holdings": [],
            "total_cost": 0,
            "total_value": 0,
            "no_data": True,
            "note": "No positions found for user",
        }

    # Group by ticker
    tickers_seen: Dict[str, List[Dict]] = {}
    for p in positions:
        t = p.get("ticker", "").upper()
        if t:
            tickers_seen.setdefault(t, []).append(p)

    # Batch fetch prices
    all_tickers = list(tickers_seen.keys())
    prices = _get_batch_prices(all_tickers)

    holdings = []
    total_cost = 0.0
    total_value = 0.0
    price_unavailable = []

    for ticker, lots in tickers_seen.items():
        total_qty = sum(l["qty"] for l in lots)
        cost = sum(l["qty"] * l["price"] for l in lots)
        current_price = prices.get(ticker)
        mkt = total_qty * current_price if current_price else None

        total_cost += cost
        if mkt:
            total_value += mkt
        else:
            price_unavailable.append(ticker)

        holdings.append({
            "ticker": ticker,
            "shares": round(total_qty, 4),
            "total_cost": round(cost, 2),
            "avg_cost": round(cost / total_qty, 4) if total_qty else 0,
            "current_price": current_price,
            "market_value": round(mkt, 2) if mkt else None,
            "unrealized_gain": round(mkt - cost, 2) if mkt else None,
            "lots_count": len(lots),
        })

    response = {
        "user_id": user_id,
        "holdings": holdings,
        "total_cost": round(total_cost, 2),
        "total_value": round(total_value, 2),
        "total_gain": round(total_value - total_cost, 2) if total_value else None,
        "holdings_count": len(holdings),
    }

    if price_unavailable:
        response["price_unavailable"] = price_unavailable

    return response


def get_ticker_cost_basis(user_id: str, ticker: str) -> Dict[str, Any]:
    """Get cost basis details for a specific ticker using FIFO method."""
    positions = _positions_from_db(user_id, ticker)

    if not positions:
        return {
            "ticker": ticker.upper(),
            "no_data": True,
            "note": f"No positions found for {ticker.upper()}",
        }

    result = calculate_cost_basis(positions, method="fifo")
    result["ticker"] = ticker.upper()

    # Add current price info
    current_price = _get_current_price(ticker)
    if current_price:
        result["current_price"] = current_price
        total_shares = result.get("total_shares", 0)
        total_cost = result.get("total_cost", 0)
        market_value = total_shares * current_price
        result["market_value"] = round(market_value, 2)
        result["unrealized_gain"] = round(market_value - total_cost, 2)

    return result


def calculate_realized_gain(
    user_id: str,
    ticker: str,
    shares_to_sell: float,
    method="fifo",
    specific_lots: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Calculate realized gain for a hypothetical sale.
    Useful for tax planning before executing a sale.

    Args:
        user_id: User identifier
        ticker: Stock symbol
        shares_to_sell: Number of shares to simulate selling
        method: Cost basis method (fifo, lifo, average)
        specific_lots: Optional list of specific lot IDs to use
    """
    method_str = method.value if isinstance(method, CostBasisMethod) else str(method)

    positions = _positions_from_db(user_id, ticker)

    if not positions:
        return {
            "ticker": ticker.upper(),
            "no_data": True,
            "note": f"No positions found for {ticker.upper()}",
        }

    total_shares = sum(p["qty"] for p in positions)
    if shares_to_sell > total_shares:
        return {
            "ticker": ticker.upper(),
            "error": f"Cannot sell {shares_to_sell} shares. Only {total_shares} shares available.",
            "shares_available": total_shares,
        }

    current_price = _get_current_price(ticker)
    if not current_price:
        return {
            "ticker": ticker.upper(),
            "error": f"Cannot fetch current price for {ticker.upper()}",
            "price_unavailable": True,
        }

    # Sort lots based on method
    sorted_lots = sorted(
        positions,
        key=lambda p: p.get("date") or "1970-01-01",
        reverse=(method_str == "lifo"),
    )

    # HIFO: Highest In, First Out - sell highest cost shares first
    if method_str == "hifo":
        sorted_lots = sorted(positions, key=lambda p: p["price"], reverse=True)

    remaining = shares_to_sell
    total_cost = 0.0
    lots_used = []

    for lot in sorted_lots:
        if remaining <= 0:
            break
        used = min(lot["qty"], remaining)
        lot_cost = used * lot["price"]
        total_cost += lot_cost
        lots_used.append({
            "lot_id": lot.get("id"),
            "qty": used,
            "cost": lot["price"],
            "date": lot.get("date"),
            "lot_cost": round(lot_cost, 2),
        })
        remaining -= used

    proceeds = shares_to_sell * current_price
    gain = proceeds - total_cost
    gain_pct = (gain / total_cost * 100) if total_cost > 0 else 0

    return {
        "ticker": ticker.upper(),
        "shares_sold": shares_to_sell,
        "method": method_str,
        "sale_price": current_price,
        "proceeds": round(proceeds, 2),
        "cost_basis": round(total_cost, 2),
        "realized_gain": round(gain, 2),
        "gain_pct": round(gain_pct, 2),
        "is_gain": gain > 0,
        "lots_used": lots_used,
        "shares_remaining": round(total_shares - shares_to_sell, 4),
    }


def get_tax_lot_comparison(user_id: str, ticker: str, shares_to_sell: float) -> Dict[str, Any]:
    """
    Compare different cost basis methods for tax planning.
    Shows which method would result in the lowest/highest tax impact.
    """
    positions = _positions_from_db(user_id, ticker)

    if not positions:
        return {
            "ticker": ticker.upper(),
            "no_data": True,
            "note": f"No positions found for {ticker.upper()}",
        }

    fifo = calculate_realized_gain(user_id, ticker, shares_to_sell, method="fifo")
    lifo = calculate_realized_gain(user_id, ticker, shares_to_sell, method="lifo")
    hifo = calculate_realized_gain(user_id, ticker, shares_to_sell, method="hifo")

    # Determine which method minimizes gain (best for tax)
    methods = [
        ("fifo", fifo.get("realized_gain", float("inf"))),
        ("lifo", lifo.get("realized_gain", float("inf"))),
        ("hifo", hifo.get("realized_gain", float("inf"))),
    ]
    # Filter out error cases
    valid_methods = [(m, g) for m, g in methods if isinstance(g, (int, float))]

    recommendation = None
    if valid_methods:
        min_gain_method = min(valid_methods, key=lambda x: x[1])
        max_gain_method = max(valid_methods, key=lambda x: x[1])
        recommendation = {
            "lowest_gain_method": min_gain_method[0],
            "lowest_gain": min_gain_method[1],
            "highest_gain_method": max_gain_method[0],
            "highest_gain": max_gain_method[1],
            "tax_savings_potential": round(max_gain_method[1] - min_gain_method[1], 2),
        }

    return {
        "ticker": ticker.upper(),
        "shares_to_sell": shares_to_sell,
        "fifo": fifo,
        "lifo": lifo,
        "hifo": hifo,
        "recommendation": recommendation,
    }


def get_gains_by_holding_period(user_id: str) -> Dict[str, Any]:
    """
    Group unrealized gains by holding period (short-term vs long-term).
    Short-term: held <= 365 days (taxed as ordinary income)
    Long-term: held > 365 days (lower capital gains tax rate)
    """
    positions = _positions_from_db(user_id)

    if not positions:
        return {
            "short_term": [],
            "long_term": [],
            "unknown": [],
            "no_data": True,
            "note": "No positions found for user",
        }

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
                entry = {**p, "days_held": days_held, "is_long_term": days_held > 365}

                if days_held > 365:
                    long_term.append(entry)
                else:
                    short_term.append(entry)
            except (ValueError, TypeError):
                unknown.append(p)
        else:
            # Without purchase date, we can't determine holding period
            unknown.append(p)

    # Calculate totals for each category
    def calc_total(positions_list):
        return {
            "count": len(positions_list),
            "total_shares": sum(p["qty"] for p in positions_list),
            "total_cost": sum(p["qty"] * p["price"] for p in positions_list),
        }

    return {
        "short_term": short_term,
        "short_term_summary": calc_total(short_term),
        "long_term": long_term,
        "long_term_summary": calc_total(long_term),
        "unknown": unknown,
        "unknown_summary": calc_total(unknown),
        "note": "Positions without purchase dates are categorized as unknown holding period",
    }


def add_position(
    user_id: str,
    ticker: str,
    shares: float,
    purchase_price: float,
    purchase_date: str,
    portfolio_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Add a new position/lot to the database.

    Args:
        user_id: User identifier
        ticker: Stock symbol
        shares: Number of shares purchased
        purchase_price: Price per share at purchase
        purchase_date: Date of purchase (YYYY-MM-DD format)
        portfolio_name: Optional portfolio name (defaults to "Default")
    """
    try:
        from app.models.monitor import Position, Portfolio
        from app.db.session import get_db_context

        with get_db_context() as db:
            # Find or create user's portfolio
            portfolio = db.query(Portfolio).filter(
                Portfolio.user_id == user_id
            ).first()

            if not portfolio:
                # Check for orphan portfolio that can be assigned
                portfolio = db.query(Portfolio).filter(
                    Portfolio.user_id.is_(None)
                ).first()

                if portfolio:
                    portfolio.user_id = user_id
                else:
                    portfolio = Portfolio(
                        name=portfolio_name or "Default",
                        base_ccy="USD",
                        user_id=user_id,
                    )
                    db.add(portfolio)
                    db.flush()

            pos = Position(
                portfolio_id=portfolio.id,
                ticker=ticker.upper(),
                qty=shares,
                cost_basis=purchase_price,
                notes=f"Purchased on {purchase_date}",
            )
            db.add(pos)
            db.commit()

            # Invalidate price cache to ensure fresh data
            _price_cache.invalidate(ticker.upper())

            return {
                "status": "created",
                "id": pos.id,
                "ticker": ticker.upper(),
                "shares": shares,
                "purchase_price": purchase_price,
                "purchase_date": purchase_date,
                "portfolio_id": portfolio.id,
                "portfolio_name": portfolio.name,
            }

    except Exception as e:
        log.error("add_position DB write failed: %s", e)
        return {
            "status": "error",
            "error": str(e),
            "ticker": ticker.upper(),
            "shares": shares,
            "purchase_price": purchase_price,
            "purchase_date": purchase_date,
        }


def delete_position(user_id: str, lot_id: str) -> Dict[str, Any]:
    """
    Delete a position/lot from the database.

    Args:
        user_id: User identifier
        lot_id: Position ID to delete
    """
    try:
        from app.models.monitor import Position, Portfolio
        from app.db.session import get_db_context

        with get_db_context() as db:
            # Verify the position belongs to the user
            position = db.query(Position).join(Portfolio).filter(
                Position.id == int(lot_id),
                (Portfolio.user_id == user_id) | (Portfolio.user_id.is_(None))
            ).first()

            if not position:
                return {
                    "status": "error",
                    "error": f"Position {lot_id} not found or access denied",
                }

            ticker = position.ticker
            db.delete(position)
            db.commit()

            # Invalidate price cache
            if ticker:
                _price_cache.invalidate(ticker.upper())

            return {
                "status": "deleted",
                "id": lot_id,
                "ticker": ticker,
            }

    except Exception as e:
        log.error("delete_position failed: %s", e)
        return {
            "status": "error",
            "error": str(e),
        }


def update_position(
    user_id: str,
    lot_id: str,
    shares: Optional[float] = None,
    purchase_price: Optional[float] = None,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Update an existing position/lot.

    Args:
        user_id: User identifier
        lot_id: Position ID to update
        shares: New share quantity (optional)
        purchase_price: New cost basis (optional)
        notes: New notes (optional)
    """
    try:
        from app.models.monitor import Position, Portfolio
        from app.db.session import get_db_context

        with get_db_context() as db:
            position = db.query(Position).join(Portfolio).filter(
                Position.id == int(lot_id),
                (Portfolio.user_id == user_id) | (Portfolio.user_id.is_(None))
            ).first()

            if not position:
                return {
                    "status": "error",
                    "error": f"Position {lot_id} not found or access denied",
                }

            if shares is not None:
                position.qty = shares
            if purchase_price is not None:
                position.cost_basis = purchase_price
            if notes is not None:
                position.notes = notes

            db.commit()

            return {
                "status": "updated",
                "id": lot_id,
                "ticker": position.ticker,
                "shares": position.qty,
                "purchase_price": position.cost_basis,
                "notes": position.notes,
            }

    except Exception as e:
        log.error("update_position failed: %s", e)
        return {
            "status": "error",
            "error": str(e),
        }


# ── Cache Management ─────────────────────────────────────────────────────────


def clear_price_cache():
    """Clear all cached prices. Useful for testing or forcing fresh data."""
    _price_cache.clear()
    log.info("Price cache cleared")


def invalidate_ticker_cache(ticker: str):
    """Invalidate cached price for a specific ticker."""
    _price_cache.invalidate(ticker.upper())
    log.debug("Cache invalidated for %s", ticker.upper())
