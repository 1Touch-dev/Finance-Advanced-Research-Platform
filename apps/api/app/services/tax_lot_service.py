"""
Tax Lot Optimization Service (Band C #45)
FIFO/LIFO/specific lot selection, wash sale detection, and tax-loss harvesting.
"""
import logging
import time as time_module
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta

log = logging.getLogger(__name__)


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
        log.warning("Price fetch failed for %s: %s", ticker, e)
    return None


DEFAULT_TAX_LOTS = [
    {"lot_id": "demo-1", "ticker": "AAPL", "qty": 50, "purchase_price": 145.0, "purchase_date": "2023-06-15", "notes": None},
    {"lot_id": "demo-2", "ticker": "AAPL", "qty": 30, "purchase_price": 172.0, "purchase_date": "2024-01-10", "notes": None},
    {"lot_id": "demo-3", "ticker": "MSFT", "qty": 40, "purchase_price": 310.0, "purchase_date": "2023-08-20", "notes": None},
    {"lot_id": "demo-4", "ticker": "NVDA", "qty": 25, "purchase_price": 450.0, "purchase_date": "2024-03-05", "notes": None},
    {"lot_id": "demo-5", "ticker": "GOOGL", "qty": 35, "purchase_price": 138.0, "purchase_date": "2023-11-01", "notes": None},
]


def _get_user_positions(user_id: str, ticker: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get user's tax lots from DB, or DEFAULT_TAX_LOTS if none exist."""
    try:
        from app.db.session import get_db_context
        from sqlalchemy import text

        with get_db_context() as db:
            params: Dict[str, Any] = {}
            sql = (
                "SELECT p.id, p.ticker, p.qty, p.cost_basis, p.notes, po.name as portfolio_name "
                "FROM positions p JOIN portfolios po ON p.portfolio_id = po.id"
            )
            if ticker:
                sql += " WHERE p.ticker = :ticker"
                params["ticker"] = ticker.upper()
            sql += " ORDER BY p.id"

            rows = db.execute(text(sql), params).fetchall()
            if rows:
                return [
                    {
                        "lot_id": str(r[0]),
                        "ticker": r[1],
                        "qty": float(r[2]),
                        "purchase_price": float(r[3]),
                        "purchase_date": None,
                        "notes": r[4],
                        "portfolio": r[5],
                    }
                    for r in rows
                ]
    except Exception as exc:
        log.debug("DB tax lot fetch failed: %s", exc)

    fallback = DEFAULT_TAX_LOTS
    if ticker:
        fallback = [l for l in fallback if l["ticker"] == ticker.upper()]
    return fallback


def _load_lots_from_db(user_id: str, ticker: Optional[str] = None) -> List[Dict[str, Any]]:
    """Backwards-compat wrapper around _get_user_positions."""
    return _get_user_positions(user_id, ticker)


# ── Public API ────────────────────────────────────────────────────────────────

def get_tax_lots(user_id: str, ticker: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get all tax lots for a user, optionally filtered by ticker."""
    lots = _load_lots_from_db(user_id, ticker)
    if not lots:
        return []

    for lot in lots:
        current = _get_current_price(lot["ticker"]) if lot.get("ticker") else None
        if current:
            gain = (current - lot["purchase_price"]) * lot["qty"]
            lot["current_price"] = current
            lot["unrealized_gain"] = round(gain, 2)
            lot["gain_pct"] = round((current / lot["purchase_price"] - 1) * 100, 2)
        else:
            lot["current_price"] = None
            lot["unrealized_gain"] = None
            lot["gain_pct"] = None

    return lots


def get_lot_by_id(user_id: str, lot_id: str) -> Optional[Dict[str, Any]]:
    """Get specific tax lot."""
    lots = _load_lots_from_db(user_id)
    for lot in lots:
        if lot["lot_id"] == lot_id:
            current = _get_current_price(lot["ticker"]) if lot.get("ticker") else None
            if current:
                lot["current_price"] = current
                lot["unrealized_gain"] = round((current - lot["purchase_price"]) * lot["qty"], 2)
            return lot
    return None


def calculate_gains(
    lots: List[Dict[str, Any]], method: str = "fifo", current_price: Optional[float] = None
) -> Dict[str, Any]:
    """
    Calculate per-lot gain/loss given current price.
    lots: [{"ticker": "AAPL", "qty": 100, "purchase_price": 150, "purchase_date": "2024-01-15"}, ...]
    """
    if not lots:
        return {"method": method, "lots": [], "total_gain": 0}

    if current_price is None and lots[0].get("ticker"):
        current_price = _get_current_price(lots[0]["ticker"])
    if current_price is None:
        return {"error": "Cannot determine current price"}

    sorted_lots = sorted(
        lots,
        key=lambda l: l.get("purchase_date") or "1970-01-01",
        reverse=(method == "lifo"),
    )

    results = []
    total_gain = 0.0

    for lot in sorted_lots:
        qty = lot["qty"]
        cost = lot["purchase_price"]
        gain_per_share = current_price - cost
        lot_gain = gain_per_share * qty
        total_gain += lot_gain

        holding_days = None
        if lot.get("purchase_date"):
            try:
                pd = datetime.strptime(lot["purchase_date"], "%Y-%m-%d").date()
                holding_days = (date.today() - pd).days
            except (ValueError, TypeError) as e:
                log.debug("Failed to parse purchase_date for lot: %s", e)

        results.append({
            "lot_id": lot.get("lot_id"),
            "ticker": lot.get("ticker"),
            "qty": qty,
            "purchase_price": cost,
            "purchase_date": lot.get("purchase_date"),
            "current_price": current_price,
            "gain_per_share": round(gain_per_share, 4),
            "lot_gain": round(lot_gain, 2),
            "gain_pct": round(gain_per_share / cost * 100, 2) if cost else 0,
            "holding_days": holding_days,
            "term": "long" if (holding_days and holding_days > 365) else "short",
        })

    return {
        "method": method,
        "current_price": current_price,
        "total_gain": round(total_gain, 2),
        "lots": results,
    }


def wash_sale_check(
    lots: List[Dict[str, Any]], sell_date: str
) -> Dict[str, Any]:
    """
    Flag lots within 30-day wash sale window.
    A wash sale occurs if you buy substantially identical stock 30 days before or after a loss sale.
    """
    if not lots:
        return {"flagged_lots": [], "wash_sale_risk": False}

    try:
        sell_dt = datetime.strptime(sell_date, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return {"error": "Invalid sell_date format. Use YYYY-MM-DD"}

    window_start = sell_dt - timedelta(days=30)
    window_end = sell_dt + timedelta(days=30)

    flagged = []
    for lot in lots:
        pd_str = lot.get("purchase_date")
        if not pd_str:
            continue
        try:
            purchase_dt = datetime.strptime(pd_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue

        if window_start <= purchase_dt <= window_end and purchase_dt != sell_dt:
            days_from_sale = (purchase_dt - sell_dt).days
            flagged.append({
                **lot,
                "days_from_sale": days_from_sale,
                "wash_sale_risk": True,
                "window": "before" if days_from_sale < 0 else "after",
            })

    return {
        "sell_date": sell_date,
        "window_start": str(window_start),
        "window_end": str(window_end),
        "flagged_lots": flagged,
        "wash_sale_risk": len(flagged) > 0,
        "flagged_count": len(flagged),
    }


def harvest_opportunities(
    lots: List[Dict[str, Any]], current_prices: Optional[Dict[str, float]] = None
) -> List[Dict[str, Any]]:
    """
    Find lots with unrealized losses for tax-loss harvesting.
    current_prices: {"AAPL": 175.0, "MSFT": 420.0} — if not provided, fetches from yfinance.
    """
    if not lots:
        return []

    prices = current_prices or {}
    opportunities = []

    for lot in lots:
        ticker = lot.get("ticker", "").upper()
        if ticker and ticker not in prices:
            p = _get_current_price(ticker)
            if p:
                prices[ticker] = p

        current = prices.get(ticker)
        if current is None:
            continue

        cost = lot.get("purchase_price", 0)
        qty = lot.get("qty", 0)

        if current < cost:
            loss = (cost - current) * qty
            loss_pct = (1 - current / cost) * 100 if cost else 0

            holding_days = None
            term = "short"
            if lot.get("purchase_date"):
                try:
                    pd = datetime.strptime(lot["purchase_date"], "%Y-%m-%d").date()
                    holding_days = (date.today() - pd).days
                    term = "long" if holding_days > 365 else "short"
                except (ValueError, TypeError) as e:
                    log.debug("Failed to parse purchase_date for harvest opportunity: %s", e)

            opportunities.append({
                "lot_id": lot.get("lot_id"),
                "ticker": ticker,
                "qty": qty,
                "purchase_price": cost,
                "current_price": current,
                "unrealized_loss": round(-loss, 2),
                "loss_pct": round(-loss_pct, 2),
                "potential_tax_savings_short": round(loss * 0.37, 2),
                "potential_tax_savings_long": round(loss * 0.20, 2),
                "holding_days": holding_days,
                "term": term,
                "purchase_date": lot.get("purchase_date"),
            })

    opportunities.sort(key=lambda x: x["unrealized_loss"])
    return opportunities


def optimize_sale(
    user_id: str,
    ticker: str,
    shares_to_sell: float,
    goal: str = "minimize_tax",
) -> Dict[str, Any]:
    """Find optimal lots to sell based on tax goal."""
    lots = _load_lots_from_db(user_id, ticker)
    if not lots:
        return {}

    current_price = _get_current_price(ticker)
    if not current_price:
        return {"error": f"Cannot fetch price for {ticker}"}

    for lot in lots:
        lot["gain_per_share"] = current_price - lot["purchase_price"]
        lot["lot_gain"] = lot["gain_per_share"] * lot["qty"]

    if goal == "minimize_tax":
        sorted_lots = sorted(lots, key=lambda l: l["gain_per_share"])
    elif goal == "maximize_loss":
        sorted_lots = sorted(lots, key=lambda l: l["gain_per_share"])
    elif goal == "maximize_gain":
        sorted_lots = sorted(lots, key=lambda l: l["gain_per_share"], reverse=True)
    else:
        sorted_lots = sorted(lots, key=lambda l: l.get("purchase_date") or "1970-01-01")

    remaining = shares_to_sell
    selected = []
    total_gain = 0.0

    for lot in sorted_lots:
        if remaining <= 0:
            break
        used = min(lot["qty"], remaining)
        gain = lot["gain_per_share"] * used
        total_gain += gain
        selected.append({
            "lot_id": lot["lot_id"],
            "qty_sold": used,
            "purchase_price": lot["purchase_price"],
            "gain_per_share": round(lot["gain_per_share"], 4),
            "lot_gain": round(gain, 2),
        })
        remaining -= used

    return {
        "ticker": ticker,
        "goal": goal,
        "shares_to_sell": shares_to_sell,
        "current_price": current_price,
        "selected_lots": selected,
        "total_gain": round(total_gain, 2),
        "estimated_tax_short": round(total_gain * 0.37, 2) if total_gain > 0 else 0,
        "estimated_tax_long": round(total_gain * 0.20, 2) if total_gain > 0 else 0,
    }


def compare_methods(user_id: str, ticker: str, shares_to_sell: float) -> Dict[str, Any]:
    """Compare different tax lot selection methods."""
    lots = _load_lots_from_db(user_id, ticker)
    if not lots:
        return {}

    current_price = _get_current_price(ticker)
    if not current_price:
        return {"error": f"Cannot fetch price for {ticker}"}

    for lot in lots:
        lot["purchase_date"] = lot.get("purchase_date") or "1970-01-01"

    fifo_lots = sorted(lots, key=lambda l: l["purchase_date"])
    lifo_lots = sorted(lots, key=lambda l: l["purchase_date"], reverse=True)
    hifo_lots = sorted(lots, key=lambda l: l["purchase_price"], reverse=True)

    def _calc(ordered):
        remaining = shares_to_sell
        total_cost = 0.0
        for lot in ordered:
            if remaining <= 0:
                break
            used = min(lot["qty"], remaining)
            total_cost += used * lot["purchase_price"]
            remaining -= used
        proceeds = shares_to_sell * current_price
        return {"cost_basis": round(total_cost, 2), "proceeds": round(proceeds, 2), "gain": round(proceeds - total_cost, 2)}

    return {
        "ticker": ticker,
        "shares_to_sell": shares_to_sell,
        "current_price": current_price,
        "fifo": _calc(fifo_lots),
        "lifo": _calc(lifo_lots),
        "hifo": _calc(hifo_lots),
        "recommendation": "hifo" if current_price > fifo_lots[0]["purchase_price"] else "fifo",
    }


def get_tax_loss_harvesting_opportunities(user_id: str, min_loss: float = 500) -> List[Dict[str, Any]]:
    """Find opportunities for tax loss harvesting above min_loss threshold."""
    lots = _load_lots_from_db(user_id)
    if not lots:
        return []

    opps = harvest_opportunities(lots)
    return [o for o in opps if abs(o.get("unrealized_loss", 0)) >= min_loss]


def get_approaching_long_term(user_id: str, days_threshold: int = 30) -> List[Dict[str, Any]]:
    """Find lots approaching long-term holding status (365 days)."""
    lots = _load_lots_from_db(user_id)
    if not lots:
        return []

    today = date.today()
    approaching = []

    for lot in lots:
        pd_str = lot.get("purchase_date")
        if not pd_str:
            continue
        try:
            purchase_dt = datetime.strptime(pd_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue

        days_held = (today - purchase_dt).days
        days_to_long = 365 - days_held

        if 0 < days_to_long <= days_threshold:
            approaching.append({
                **lot,
                "days_held": days_held,
                "days_to_long_term": days_to_long,
                "long_term_date": str(purchase_dt + timedelta(days=365)),
            })

    approaching.sort(key=lambda x: x["days_to_long_term"])
    return approaching
