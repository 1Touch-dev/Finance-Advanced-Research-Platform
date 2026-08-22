"""
Person Timeline Service (James J1)
───────────────────────────────────
Real implementation aggregating person events from:
  - SEC EDGAR Form 4 (insider transactions)
  - Government Trading Connector (congressional trades)
  - Politician Leaderboard Service (rankings & search)
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def _safe_import_sec():
    try:
        from app.connectors.sec_edgar_connector import (
            get_insider_transactions,
            get_cik_from_ticker,
            get_company_submissions,
        )
        return get_insider_transactions, get_cik_from_ticker, get_company_submissions
    except ImportError:
        return None, None, None


def _safe_import_gov():
    try:
        from app.connectors.gov_trading_connector import (
            get_trades_by_member,
            get_senate_trades_by_member,
            get_politician_profile,
            get_trades_by_ticker,
            TRACKED_POLITICIANS,
        )
        return get_trades_by_member, get_senate_trades_by_member, get_politician_profile, get_trades_by_ticker, TRACKED_POLITICIANS
    except ImportError:
        return None, None, None, None, {}


def _safe_import_leaderboard():
    try:
        from app.services.politician_leaderboard_service import (
            search_politician,
            get_all_politicians,
        )
        return search_politician, get_all_politicians
    except ImportError:
        return None, None


def _resolve_person(person_id: str) -> Dict[str, Any]:
    """
    Resolve a person_id (name or slug) to identify whether they're
    a politician (congressional) or corporate insider (SEC filer).
    """
    name = person_id.replace("_", " ").strip()

    # Check politician leaderboard
    search_fn, _ = _safe_import_leaderboard()
    if search_fn:
        result = search_fn(name)
        if result.get("found"):
            return {"type": "politician", "name": name, "data": result}

    # Check tracked politicians in gov connector
    _, _, _, _, tracked = _safe_import_gov()
    if tracked:
        slug = person_id.lower().replace(" ", "_")
        if slug in tracked:
            info = tracked[slug]
            return {"type": "politician", "name": info["name"], "data": info}
        for pid, pinfo in tracked.items():
            if name.lower() in pinfo["name"].lower() or pinfo["name"].lower() in name.lower():
                return {"type": "politician", "name": pinfo["name"], "data": pinfo}

    # Assume corporate insider if not found as politician
    return {"type": "insider", "name": name, "data": {}}


def search_persons(query: str) -> List[Dict[str, Any]]:
    """Search for persons by name — checks politicians and corporate insiders."""
    results = []
    query_lower = query.lower().strip()

    # Search politician leaderboard
    search_fn, get_all_fn = _safe_import_leaderboard()
    if get_all_fn:
        try:
            all_politicians = get_all_fn(limit=100)
            for p in all_politicians:
                name = (p.get("name") or "").lower()
                if query_lower in name or name in query_lower:
                    results.append({
                        "person_id": p.get("name", "").replace(" ", "_").lower(),
                        "name": p.get("name"),
                        "type": "politician",
                        "chamber": p.get("chamber", ""),
                        "party": p.get("party", ""),
                        "state": p.get("state", ""),
                        "trade_count": p.get("trade_count", 0),
                    })
        except Exception as e:
            logger.warning("Politician search error: %s", e)

    # Search tracked politicians in gov connector
    _, _, _, _, tracked = _safe_import_gov()
    if tracked:
        seen_names = {r["name"].lower() for r in results}
        for pid, pinfo in tracked.items():
            if query_lower in pinfo["name"].lower() and pinfo["name"].lower() not in seen_names:
                results.append({
                    "person_id": pid,
                    "name": pinfo["name"],
                    "type": "politician",
                    "chamber": pinfo.get("chamber", ""),
                    "party": pinfo.get("party", ""),
                    "state": pinfo.get("state", ""),
                })

    if not results:
        results.append({
            "person_id": query.replace(" ", "_").lower(),
            "name": query,
            "type": "unknown",
            "note": "Person not found in politician database. May be a corporate insider — use ticker-based lookup.",
        })

    return results


def get_person(person_id: str) -> Optional[Dict[str, Any]]:
    """Get person details — profile from politician leaderboard or gov connector."""
    resolved = _resolve_person(person_id)

    if resolved["type"] == "politician":
        _, _, get_profile, _, _ = _safe_import_gov()
        if get_profile:
            try:
                profile = get_profile(resolved["name"])
                if not profile.get("error"):
                    return {
                        "person_id": person_id,
                        "name": resolved["name"],
                        "type": "politician",
                        "profile": profile.get("politician", {}),
                        "ptr_filings_count": profile.get("ptr_filings_count", 0),
                        "disclosure_activity": profile.get("disclosure_activity", {}),
                        "note": profile.get("note", ""),
                    }
            except Exception as e:
                logger.warning("Gov profile fetch error for %s: %s", person_id, e)

        # Fallback to leaderboard data
        search_fn, _ = _safe_import_leaderboard()
        if search_fn:
            result = search_fn(resolved["name"])
            if result.get("found"):
                return {
                    "person_id": person_id,
                    "name": resolved["name"],
                    "type": "politician",
                    "rankings": result.get("rankings", {}),
                    "notable_cases": result.get("notable_cases", []),
                }

    return {
        "person_id": person_id,
        "name": resolved["name"],
        "type": resolved["type"],
        "note": "Limited profile data available. Use timeline endpoint for trade activity.",
    }


def get_person_timeline(person_id: str, start_date: Optional[str] = None,
                        end_date: Optional[str] = None,
                        event_types: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Aggregate events (trades, filings) into a chronological timeline.
    Combines congressional PTR filings and SEC insider data.
    """
    resolved = _resolve_person(person_id)
    name = resolved["name"]
    events = []

    days = 365
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            days = (datetime.now() - start_dt).days
        except ValueError:
            pass

    # Congressional trades
    if resolved["type"] == "politician":
        get_house, get_senate, _, _, tracked = _safe_import_gov()

        slug = person_id.lower().replace(" ", "_")
        info = tracked.get(slug, {}) if tracked else {}
        chamber = info.get("chamber", "")

        if get_senate and chamber == "senate":
            try:
                trades = get_senate(name, days=days)
                for t in trades:
                    event_date = t.get("date") or t.get("filing_date", "")
                    if end_date and event_date > end_date:
                        continue
                    events.append({
                        "date": event_date,
                        "type": "trade",
                        "subtype": "congressional_ptr",
                        "ticker": t.get("ticker", ""),
                        "transaction": t.get("transaction", ""),
                        "amount": t.get("amount", ""),
                        "source": t.get("source", "Senate eFD"),
                        "detail": t.get("asset_description", ""),
                    })
            except Exception as e:
                logger.warning("Senate trades error for %s: %s", name, e)

        if get_house and chamber == "house":
            try:
                filings = get_house(name, years=max(1, days // 365))
                for f in filings:
                    event_date = f.get("filing_date", "")
                    events.append({
                        "date": event_date,
                        "type": "filing",
                        "subtype": "house_ptr",
                        "doc_id": f.get("doc_id", ""),
                        "filing_type": f.get("filing_type", "P"),
                        "source": "House Clerk FD",
                    })
            except Exception as e:
                logger.warning("House trades error for %s: %s", name, e)

    # Filter by event_types if specified
    if event_types:
        events = [e for e in events if e.get("type") in event_types or e.get("subtype") in event_types]

    events.sort(key=lambda e: e.get("date", ""), reverse=True)

    return {
        "person_id": person_id,
        "name": name,
        "type": resolved["type"],
        "period": {"start": start_date, "end": end_date, "days": days},
        "total_events": len(events),
        "events": events,
    }


def get_timeline_with_prices(person_id: str, days: int = 365) -> Dict[str, Any]:
    """Timeline with stock price context (best-effort)."""
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    timeline = get_person_timeline(person_id, start_date=start_date)

    tickers_traded = list({
        e.get("ticker") for e in timeline.get("events", [])
        if e.get("ticker")
    })

    return {
        **timeline,
        "tickers_traded": tickers_traded,
        "price_overlay": "Price data available via separate ticker endpoints",
    }


def get_person_news(person_id: str, limit: int = 20) -> Dict[str, Any]:
    """News about a person — returns their recent filings as news-like items."""
    resolved = _resolve_person(person_id)
    timeline = get_person_timeline(person_id)
    events = timeline.get("events", [])[:limit]

    news_items = []
    for event in events:
        news_items.append({
            "date": event.get("date", ""),
            "headline": f"{resolved['name']}: {event.get('subtype', event.get('type', ''))} - {event.get('ticker', '')} {event.get('transaction', '')}".strip(" -"),
            "source": event.get("source", ""),
            "type": event.get("type", ""),
        })

    return {
        "person_id": person_id,
        "name": resolved["name"],
        "news": news_items,
        "total": len(news_items),
    }


def get_person_trades(person_id: str, days: int = 365) -> Dict[str, Any]:
    """Stock trades by person — combines congressional PTRs and SEC Form 4."""
    resolved = _resolve_person(person_id)
    name = resolved["name"]
    trades = []

    if resolved["type"] == "politician":
        get_house, get_senate, _, _, tracked = _safe_import_gov()
        slug = person_id.lower().replace(" ", "_")
        info = tracked.get(slug, {}) if tracked else {}
        chamber = info.get("chamber", "")

        if get_senate and chamber == "senate":
            try:
                raw = get_senate(name, days=days)
                for t in raw:
                    trades.append({
                        "date": t.get("date") or t.get("filing_date", ""),
                        "ticker": t.get("ticker", ""),
                        "transaction": t.get("transaction", ""),
                        "amount": t.get("amount", ""),
                        "asset": t.get("asset_description", ""),
                        "source": t.get("source", ""),
                    })
            except Exception as e:
                logger.warning("Senate trades fetch error: %s", e)

        if get_house and chamber == "house":
            try:
                raw = get_house(name, years=max(1, days // 365))
                for f in raw:
                    trades.append({
                        "date": f.get("filing_date", ""),
                        "ticker": "",
                        "transaction": "PTR Filing",
                        "amount": "",
                        "asset": f.get("doc_id", ""),
                        "source": "House Clerk FD",
                    })
            except Exception as e:
                logger.warning("House trades fetch error: %s", e)

    trades.sort(key=lambda t: t.get("date", ""), reverse=True)

    return {
        "person_id": person_id,
        "name": name,
        "type": resolved["type"],
        "days": days,
        "total_trades": len(trades),
        "trades": trades,
    }


def get_person_filings(person_id: str) -> Dict[str, Any]:
    """SEC filings involving person — Form 4 for insiders, PTRs for politicians."""
    resolved = _resolve_person(person_id)
    name = resolved["name"]
    filings = []

    if resolved["type"] == "politician":
        _, _, get_profile, _, _ = _safe_import_gov()
        if get_profile:
            try:
                profile = get_profile(name)
                for f in profile.get("recent_ptr_filings", []):
                    filings.append({
                        "date": f.get("filing_date") or f.get("date", ""),
                        "type": "PTR",
                        "ticker": f.get("ticker", ""),
                        "detail": f.get("asset_description", "") or f.get("doc_id", ""),
                        "source": f.get("source", "STOCK Act"),
                    })
            except Exception as e:
                logger.warning("Profile filings error: %s", e)

    return {
        "person_id": person_id,
        "name": name,
        "type": resolved["type"],
        "total_filings": len(filings),
        "filings": filings,
    }


def compare_persons(person_ids: List[str]) -> Dict[str, Any]:
    """Compare timelines of multiple persons."""
    comparisons = []
    for pid in person_ids:
        trades = get_person_trades(pid, days=365)
        comparisons.append({
            "person_id": pid,
            "name": trades.get("name", pid),
            "type": trades.get("type", "unknown"),
            "total_trades": trades.get("total_trades", 0),
            "recent_trades": trades.get("trades", [])[:5],
        })

    return {
        "persons": comparisons,
        "comparison_period_days": 365,
    }
