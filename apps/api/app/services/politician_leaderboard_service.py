"""
Politician Trading Leaderboard Service
───────────────────────────────────────
Provides ranked government official trading data from parsed Excel.
Data sources: Capitol Markets, Capitol Trades, Kapitol.ai, Open Cabinet (2013-2026)

Endpoints:
- Top by Trades (357 officials)
- Top by Volume (241 officials)
- Top by Returns (72 officials)
- Executive Branch (50 officials)
- Notable Cases (20 cases)
- Politician Search/Lookup
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

log = logging.getLogger(__name__)

# Data directory
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "gov_trading"


def _load_data() -> Dict[str, Any]:
    """Load cached leaderboard data from JSON."""
    combined_path = DATA_DIR / "gov_trading_rankings.json"
    if combined_path.exists():
        try:
            with open(combined_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            log.error(f"Failed to load gov trading data: {e}")
    return {}


def _safe_float(val) -> float:
    """Safely convert to float, handling NaN values."""
    import math
    if val is None:
        return 0.0
    try:
        if isinstance(val, str):
            val = val.replace(",", "").replace("$", "").replace("%", "").replace("—", "0").strip()
            # Handle empty strings and dash-only strings
            if not val or val == "-" or val.lower() == "nan" or val.lower() == "n/a":
                return 0.0
            if "M" in val:
                val = val.replace("M", "")
                result = float(val) * 1_000_000
            elif "K" in val:
                val = val.replace("K", "")
                result = float(val) * 1_000
            else:
                result = float(val)
        else:
            result = float(val)
        # Check for NaN and infinity
        if math.isnan(result) or math.isinf(result):
            return 0.0
        return result
    except (ValueError, TypeError):
        return 0.0


def _safe_str(val) -> str:
    """Safely convert to string, handling NaN values."""
    import math
    if val is None:
        return ""
    if isinstance(val, float):
        if math.isnan(val) or math.isinf(val):
            return ""
    s = str(val).strip()
    if s.lower() in ("nan", "none", "n/a", "null"):
        return ""
    return s


def _safe_int(val) -> int:
    """Safely convert to int."""
    import math
    if val is None:
        return 0
    try:
        if isinstance(val, float):
            if math.isnan(val) or math.isinf(val):
                return 0
        if isinstance(val, str):
            val = val.replace(",", "").replace("$", "").replace("—", "0").replace("-", "0").strip()
            if not val or val.lower() in ("nan", "n/a"):
                return 0
        return int(float(val))
    except (ValueError, TypeError):
        return 0


def get_leaderboard_by_trades(limit: int = 50) -> List[Dict]:
    """Get politicians ranked by number of trades."""
    data = _load_data()
    records = data.get("top_by_trades", [])

    return [
        {
            "rank": _safe_int(r.get("rank", i + 1)),
            "name": _safe_str(r.get("official") or r.get("name")) or "Unknown",
            "party": _safe_str(r.get("party")),
            "chamber": _safe_str(r.get("chamber_role") or r.get("chamber")),
            "state": _safe_str(r.get("state")),
            "trade_count": _safe_int(r.get("trades") or r.get("trade_count")),
            "trade_source": _safe_str(r.get("trade_source")) or "Capitol Trades",
            "volume_usd": _safe_float(r.get("volume_m") or r.get("volume")) * (1_000_000 if "m" in str(r.get("volume_m", "")).lower() else 1),
            "return_pct": _safe_float(r.get("return_pct") or r.get("return")),
            "net_profit_usd": _safe_float(r.get("net_profit_m") or r.get("net_profit")) * 1_000_000,
        }
        for i, r in enumerate(records[:limit])
    ]


def get_leaderboard_by_volume(limit: int = 50) -> List[Dict]:
    """Get politicians ranked by dollar volume of trades."""
    data = _load_data()
    records = data.get("top_by_volume", [])

    return [
        {
            "rank": _safe_int(r.get("rank", i + 1)),
            "name": _safe_str(r.get("official") or r.get("name")) or "Unknown",
            "party": _safe_str(r.get("party")),
            "chamber": _safe_str(r.get("chamber_role") or r.get("chamber")),
            "state": _safe_str(r.get("state")),
            "volume_usd": _safe_float(r.get("volume_m") or r.get("volume")) * 1_000_000,
            "volume_source": _safe_str(r.get("volume_source")) or "Capitol Trades",
            "trade_count": _safe_int(r.get("trades") or r.get("trade_count")),
            "return_pct": _safe_float(r.get("return_pct") or r.get("return")),
            "net_profit_usd": _safe_float(r.get("net_profit_m") or r.get("net_profit")) * 1_000_000,
        }
        for i, r in enumerate(records[:limit])
    ]


def get_leaderboard_by_returns(limit: int = 50) -> List[Dict]:
    """Get politicians ranked by investment returns vs S&P 500."""
    data = _load_data()
    records = data.get("top_by_returns", [])

    return [
        {
            "rank": _safe_int(r.get("rank", i + 1)),
            "name": _safe_str(r.get("official") or r.get("name")) or "Unknown",
            "party": _safe_str(r.get("party")),
            "chamber": _safe_str(r.get("chamber_role") or r.get("chamber")),
            "state": _safe_str(r.get("state")),
            "return_pct": _safe_float(r.get("est._return_pct") or r.get("return_pct") or r.get("return")),
            "vs_sp500": _safe_float(r.get("vs._s&p_500") or r.get("vs_sp500")),
            "trade_count": _safe_int(r.get("trades") or r.get("trade_count")),
            "est_profit_usd": _safe_float(r.get("est._profit_m") or r.get("profit")) * 1_000_000,
            "measurement_period": _safe_str(r.get("measurement_window") or r.get("period")),
        }
        for i, r in enumerate(records[:limit])
    ]


def get_executive_branch(limit: int = 50) -> List[Dict]:
    """Get Executive Branch officials trading data."""
    data = _load_data()
    records = data.get("executive_branch", [])

    return [
        {
            "rank": _safe_int(r.get("rank", i + 1)),
            "name": _safe_str(r.get("official") or r.get("name")) or "Unknown",
            "role": _safe_str(r.get("role") or r.get("position")),
            "department": _safe_str(r.get("department")),
            "trades_2025": _safe_int(r.get("trades_2025+") or r.get("trades")),
            "sales": _safe_int(r.get("sales")),
            "purchases": _safe_int(r.get("purchases")),
            "late_filing_pct": _safe_float(r.get("late_pct") or r.get("late_filing")),
            "filings_since": _safe_str(r.get("filings_since")),
            "source": _safe_str(r.get("source")) or "STOCK Act / Open Cabinet",
        }
        for i, r in enumerate(records[:limit])
    ]


def get_notable_cases(limit: int = 20) -> List[Dict]:
    """Get notable insider trading cases."""
    data = _load_data()
    records = data.get("notable_cases", [])

    return [
        {
            "case": _safe_str(r.get("case")),
            "year": _safe_str(r.get("year")),
            "official": _safe_str(r.get("official") or r.get("name")),
            "party": _safe_str(r.get("party")),
            "position": _safe_str(r.get("position")),
            "trades_amount": _safe_str(r.get("trades___amount") or r.get("amount")),
            "details": _safe_str(r.get("details")),
            "outcome": _safe_str(r.get("outcome")),
        }
        for r in records[:limit]
    ]


def get_all_politicians(limit: int = 100) -> List[Dict]:
    """Get all unique politicians from flat combined list."""
    data = _load_data()
    records = data.get("flat_combined", [])

    return [
        {
            "rank": _safe_int(r.get("rank", i + 1)),
            "name": _safe_str(r.get("official") or r.get("name")) or "Unknown",
            "party": _safe_str(r.get("party")),
            "chamber": _safe_str(r.get("chamber_role") or r.get("chamber")),
            "state": _safe_str(r.get("state")),
            "trade_count": _safe_int(r.get("best_trades") or r.get("trades")),
            "volume_usd": _safe_float(r.get("best_volume_m") or r.get("volume")) * 1_000_000,
            "return_pct": _safe_float(r.get("best_return_pct") or r.get("return")),
        }
        for i, r in enumerate(records[:limit])
    ]


def search_politician(name: str) -> Dict:
    """Search for a politician across all rankings."""
    data = _load_data()
    name_lower = name.lower().strip()

    results = {
        "query": name,
        "found": False,
        "rankings": {},
        "notable_cases": [],
    }

    # Search in each leaderboard
    for category in ["top_by_trades", "top_by_volume", "top_by_returns", "executive_branch"]:
        records = data.get(category, [])
        for i, r in enumerate(records):
            official = (r.get("official") or r.get("name") or "").lower()
            if name_lower in official or official in name_lower:
                results["found"] = True
                results["rankings"][category] = {
                    "rank": _safe_int(r.get("rank", i + 1)),
                    "total_in_category": len(records),
                    "data": r,
                }
                break

    # Search in notable cases
    for case in data.get("notable_cases", []):
        official = (case.get("official") or "").lower()
        if name_lower in official or official in name_lower:
            results["notable_cases"].append(case)

    return results


def get_politician_rank(name: str) -> Dict:
    """Get a specific politician's ranking across all categories."""
    search_result = search_politician(name)

    if not search_result["found"]:
        return {
            "name": name,
            "found": False,
            "message": f"Politician '{name}' not found in rankings",
        }

    # Extract best rankings
    best_by_trades = search_result["rankings"].get("top_by_trades", {})
    best_by_volume = search_result["rankings"].get("top_by_volume", {})
    best_by_returns = search_result["rankings"].get("top_by_returns", {})
    executive = search_result["rankings"].get("executive_branch", {})

    return {
        "name": name,
        "found": True,
        "rank_by_trades": best_by_trades.get("rank"),
        "rank_by_volume": best_by_volume.get("rank"),
        "rank_by_returns": best_by_returns.get("rank"),
        "is_executive_branch": bool(executive),
        "notable_cases_count": len(search_result["notable_cases"]),
        "notable_cases": search_result["notable_cases"],
        "details": {
            "by_trades": best_by_trades.get("data"),
            "by_volume": best_by_volume.get("data"),
            "by_returns": best_by_returns.get("data"),
            "executive": executive.get("data"),
        },
    }


def get_statistics() -> Dict:
    """Get overall statistics about the leaderboard data."""
    data = _load_data()

    return {
        "total_politicians": len(data.get("flat_combined", [])),
        "top_by_trades_count": len(data.get("top_by_trades", [])),
        "top_by_volume_count": len(data.get("top_by_volume", [])),
        "top_by_returns_count": len(data.get("top_by_returns", [])),
        "executive_branch_count": len(data.get("executive_branch", [])),
        "notable_cases_count": len(data.get("notable_cases", [])),
        "data_sources": [
            "Capitol Markets",
            "Capitol Trades",
            "Kapitol.ai",
            "Open Cabinet",
            "STOCK Act disclosures",
        ],
        "coverage_period": "2013-2026",
        "last_updated": data.get("metadata", {}).get("parsed_at"),
    }


def get_top_performers_summary() -> Dict:
    """Get summary of top performers across all categories."""
    trades = get_leaderboard_by_trades(limit=5)
    volume = get_leaderboard_by_volume(limit=5)
    returns = get_leaderboard_by_returns(limit=5)
    executive = get_executive_branch(limit=5)
    notable = get_notable_cases(limit=5)

    return {
        "top_by_trades": {
            "leader": trades[0] if trades else None,
            "top_5": trades,
        },
        "top_by_volume": {
            "leader": volume[0] if volume else None,
            "top_5": volume,
        },
        "top_by_returns": {
            "leader": returns[0] if returns else None,
            "top_5": returns,
        },
        "executive_branch": {
            "leader": executive[0] if executive else None,
            "top_5": executive,
        },
        "recent_notable_cases": notable,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }
