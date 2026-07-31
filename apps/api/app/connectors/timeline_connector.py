"""
Event Timeline & Chronology Generator
────────────────────────────────────────────────────────────────────────────
Generate comprehensive timelines aggregating events from all sources:
  - SEC filings (10-K, 10-Q, 8-K, Form 4, DEF 14A)
  - News and press releases
  - Stock price movements
  - Insider transactions
  - Legal/regulatory events
  - Executive changes
  - M&A activity
  - Earnings announcements
  - Product launches

This connector fulfills James's request:
  "a timeline would be great on news, valuations, etc."

Usage:
    from app.connectors.timeline_connector import (
        generate_entity_timeline,
        generate_event_chronology,
    )
    timeline = generate_entity_timeline("NVDA", years=2)
"""
import os
import re
import time
import logging
import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.connectors.sec_http import sec_get

logger = logging.getLogger(__name__)

# SEC EDGAR headers
SEC_HEADERS = {"User-Agent": os.getenv("SEC_USER_AGENT", "FinanceIntelPlatform/1.0 research@example.com")}

# Event type categories
EVENT_CATEGORIES = {
    "financial": ["earnings", "10-K", "10-Q", "revenue", "guidance"],
    "governance": ["board", "ceo", "cfo", "executive", "director", "proxy"],
    "legal": ["lawsuit", "litigation", "settlement", "sec", "enforcement"],
    "strategic": ["acquisition", "merger", "divestiture", "partnership", "deal"],
    "operational": ["product", "launch", "expansion", "restructuring", "layoff"],
    "market": ["stock", "price", "analyst", "upgrade", "downgrade", "target"],
    "regulatory": ["fda", "ftc", "doj", "investigation", "approval", "clearance"],
    "insider": ["form 4", "insider", "10b5-1", "stock sale", "stock purchase"],
}

# Priority scoring for event significance
EVENT_PRIORITY = {
    "8-K": 8,
    "10-K": 9,
    "10-Q": 7,
    "Form 4": 5,
    "DEF 14A": 6,
    "SC 13D": 8,
    "SC 13G": 4,
    "acquisition": 10,
    "merger": 10,
    "ceo_change": 10,
    "earnings": 8,
    "guidance": 7,
    "lawsuit_filed": 7,
    "settlement": 8,
    "sec_action": 9,
    "product_launch": 6,
    "layoff": 7,
    "stock_split": 6,
    "dividend": 5,
}


def _get_cik_from_ticker(ticker: str) -> Optional[str]:
    """
    Resolve stock ticker to SEC CIK.

    Delegates to the shared cached resolver rather than scraping
    cgi-bin/browse-edgar, which is rate-limited and fails intermittently.
    """
    from app.connectors.sec_edgar_connector import get_cik_from_ticker
    return get_cik_from_ticker(ticker)


def _fetch_sec_filings(cik: str, years: int = 2) -> List[Dict[str, Any]]:
    """
    Fetch SEC filing history for timeline generation.

    Retrieves all filings and extracts key events.
    """
    events = []

    try:
        url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        resp = sec_get(url, timeout=15)

        if resp is None or not resp.ok:
            return events

        data = resp.json()
        company_name = data.get("name", "")
        filings = data.get("filings", {}).get("recent", {})

        forms = filings.get("form", [])
        dates = filings.get("filingDate", [])
        accessions = filings.get("accessionNumber", [])
        descriptions = filings.get("primaryDocDescription", [])
        documents = filings.get("primaryDocument", [])

        cutoff = datetime.now() - timedelta(days=years*365)

        for i, form in enumerate(forms):
            if i >= len(dates):
                break

            filing_date = dates[i]
            if datetime.strptime(filing_date, "%Y-%m-%d") < cutoff:
                continue

            # Map form type to event
            event = {
                "date": filing_date,
                "event_type": "sec_filing",
                "form_type": form,
                "title": f"{form} Filed",
                "description": descriptions[i] if i < len(descriptions) else "",
                "accession": accessions[i] if i < len(accessions) else "",
                "document": documents[i] if i < len(documents) else "",
                "entity": company_name,
                "source": "SEC EDGAR",
                "priority": EVENT_PRIORITY.get(form, 3),
                "category": _categorize_event(form, descriptions[i] if i < len(descriptions) else ""),
            }

            # Add context for specific filings
            if form == "8-K":
                event["title"] = "Material Event (8-K)"
                event["priority"] = 8
            elif form == "10-K":
                event["title"] = "Annual Report Filed"
                event["priority"] = 9
            elif form == "10-Q":
                event["title"] = "Quarterly Report Filed"
            elif form == "4":
                event["title"] = "Insider Transaction (Form 4)"
                event["event_type"] = "insider_transaction"
            elif form == "DEF 14A":
                event["title"] = "Proxy Statement Filed"
            elif form == "SC 13D":
                event["title"] = "Activist Stake Disclosed (13D)"
                event["priority"] = 8
            elif form == "SC 13G":
                event["title"] = "Institutional Stake Disclosed (13G)"

            events.append(event)

    except Exception as e:
        logger.warning("Error fetching SEC filings for CIK %s: %s", cik, e)

    return events


# Form 8-K reportable events, per the SEC's General Instruction B.
FORM_8K_ITEMS = {
    "1.01": "Entry into a material definitive agreement",
    "1.02": "Termination of a material definitive agreement",
    "1.03": "Bankruptcy or receivership",
    "1.05": "Material cybersecurity incident",
    "2.01": "Completion of an acquisition or disposition of assets",
    "2.02": "Results of operations and financial condition",
    "2.03": "Creation of a direct financial obligation",
    "2.04": "Triggering event accelerating a direct financial obligation",
    "2.05": "Costs associated with exit or disposal activities",
    "2.06": "Material impairment",
    "3.01": "Notice of delisting or failure to satisfy a listing rule",
    "3.02": "Unregistered sale of equity securities",
    "3.03": "Material modification to rights of security holders",
    "4.01": "Change in the registrant's certifying accountant",
    "4.02": "Non-reliance on previously issued financial statements",
    "5.01": "Change in control of the registrant",
    "5.02": "Departure or appointment of directors or principal officers",
    "5.03": "Amendment to articles or bylaws; change in fiscal year",
    "5.04": "Temporary suspension of trading under employee benefit plans",
    "5.05": "Amendment to the code of ethics",
    "5.07": "Submission of matters to a vote of security holders",
    "5.08": "Shareholder director nominations",
    "7.01": "Regulation FD disclosure",
    "8.01": "Other events",
    "9.01": "Financial statements and exhibits",
}

# Items that carry no information on their own: 9.01 merely lists exhibits and
# accompanies nearly every 8-K, and 7.01 is a disclosure channel rather than a
# subject. They are kept but never used as the headline item.
_LOW_SIGNAL_ITEMS = {"9.01", "7.01"}


def enrich_8k_items(cik: str, events: List[Dict[str, Any]],
                    max_filings: int = 40) -> List[Dict[str, Any]]:
    """
    Label each 8-K with the reportable events it discloses.

    The submissions index gives no indication of an 8-K's subject, so every
    filing renders identically as "Material Event". Reading the Item numbers off
    the filing itself distinguishes an earnings release from an executive
    departure or a material agreement.
    """
    processed = 0
    for event in events:
        if event.get("form_type") != "8-K" or processed >= max_filings:
            continue
        accession = (event.get("accession") or "").replace("-", "")
        document = event.get("document") or ""
        if not accession or not document:
            continue

        url = (f"https://www.sec.gov/Archives/edgar/data/{cik.lstrip('0')}/"
               f"{accession}/{document}")
        try:
            resp = sec_get(url, timeout=15)
            if resp is None or not resp.ok:
                continue
            text = " ".join(BeautifulSoup(resp.text, "html.parser").get_text().split())
        except Exception as e:
            logger.debug("8-K item parse failed for %s: %s", url, e)
            continue
        processed += 1

        found = []
        for code in sorted(set(re.findall(r"Item\s+(\d\.\d{2})", text))):
            if code in FORM_8K_ITEMS and code not in found:
                found.append(code)
        if not found:
            continue

        event["items"] = [{"code": c, "title": FORM_8K_ITEMS[c]} for c in found]
        event["source_url"] = url
        headline = next((c for c in found if c not in _LOW_SIGNAL_ITEMS), found[0])
        event["title"] = FORM_8K_ITEMS[headline]
        event["description"] = "; ".join(
            f"Item {c} — {FORM_8K_ITEMS[c]}" for c in found)

    return events


def _categorize_event(form_type: str, description: str = "") -> str:
    """Categorize an event based on form type and description."""
    text = f"{form_type} {description}".lower()

    for category, keywords in EVENT_CATEGORIES.items():
        for keyword in keywords:
            if keyword in text:
                return category

    # Default categorization by form type
    if form_type in ("10-K", "10-Q", "8-K"):
        return "financial"
    elif form_type in ("4", "Form 4"):
        return "insider"
    elif form_type in ("DEF 14A", "DEFA14A"):
        return "governance"
    elif form_type in ("SC 13D", "SC 13G"):
        return "market"

    return "other"


def _fetch_stock_events(ticker: str, years: int = 2) -> List[Dict[str, Any]]:
    """
    Fetch significant stock price events using yfinance.

    Detects:
    - Stock splits
    - Dividends
    - Major price movements (>10% in a day)
    """
    events = []

    try:
        import yfinance as yf

        stock = yf.Ticker(ticker)

        # Get splits
        splits = stock.splits
        if splits is not None and len(splits) > 0:
            cutoff = datetime.now() - timedelta(days=years*365)

            for date, ratio in splits.items():
                if date.to_pydatetime() >= cutoff:
                    events.append({
                        "date": date.strftime("%Y-%m-%d"),
                        "event_type": "stock_split",
                        "title": f"Stock Split ({ratio:.0f}:1)",
                        "description": f"Stock split ratio: {ratio}",
                        "entity": ticker,
                        "source": "Market Data",
                        "priority": 6,
                        "category": "market",
                    })

        # Get dividends
        dividends = stock.dividends
        if dividends is not None and len(dividends) > 0:
            cutoff = datetime.now() - timedelta(days=years*365)

            for date, amount in dividends.items():
                if date.to_pydatetime() >= cutoff and amount > 0:
                    events.append({
                        "date": date.strftime("%Y-%m-%d"),
                        "event_type": "dividend",
                        "title": f"Dividend: ${amount:.2f}/share",
                        "description": f"Cash dividend of ${amount:.2f} per share",
                        "entity": ticker,
                        "source": "Market Data",
                        "priority": 5,
                        "category": "financial",
                    })

        # Get major price movements
        history = stock.history(period=f"{years}y")
        if history is not None and len(history) > 0:
            history["Daily_Return"] = history["Close"].pct_change()

            # Find days with >10% move
            big_moves = history[abs(history["Daily_Return"]) > 0.10]

            for date, row in big_moves.iterrows():
                pct = row["Daily_Return"] * 100
                direction = "up" if pct > 0 else "down"

                events.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "event_type": "price_movement",
                    "title": f"Stock {direction.capitalize()} {abs(pct):.1f}%",
                    "description": f"Closed at ${row['Close']:.2f}",
                    "price": row["Close"],
                    "change_pct": pct,
                    "entity": ticker,
                    "source": "Market Data",
                    "priority": 7 if abs(pct) > 15 else 5,
                    "category": "market",
                })

    except ImportError:
        logger.warning("yfinance not available for stock events")
    except Exception as e:
        logger.warning("Error fetching stock events for %s: %s", ticker, e)

    return events


def _fetch_insider_transactions(cik: str, years: int = 2) -> List[Dict[str, Any]]:
    """
    Fetch insider transaction summary for timeline.

    Groups Form 4 filings into meaningful events.
    """
    events = []

    try:
        # Search EFTS for Form 4 filings
        params = {
            "q": f"cik:{cik}",
            "forms": "4",
            "dateRange": "custom",
            "startdt": (datetime.now() - timedelta(days=years*365)).strftime("%Y-%m-%d"),
            "enddt": datetime.now().strftime("%Y-%m-%d"),
        }

        resp = requests.get(
            "https://efts.sec.gov/LATEST/search-index",
            params=params,
            headers=SEC_HEADERS,
            timeout=20,
        )

        if resp.ok:
            data = resp.json()
            hits = data.get("hits", {}).get("hits", [])

            # Group by filing date and reporter
            filings_by_date = defaultdict(list)
            for hit in hits:
                src = hit.get("_source", {})
                date = src.get("file_date", "")
                names = src.get("display_names", [])
                reporter = names[0] if names else "Unknown"

                filings_by_date[date].append(reporter)

            # Create events for significant filing clusters
            for date, reporters in filings_by_date.items():
                if len(reporters) >= 3:
                    events.append({
                        "date": date,
                        "event_type": "insider_cluster",
                        "title": f"Multiple Insider Transactions ({len(reporters)} filings)",
                        "description": f"Insiders filing: {', '.join(reporters[:3])}{'...' if len(reporters) > 3 else ''}",
                        "insider_count": len(reporters),
                        "source": "SEC Form 4",
                        "priority": 6,
                        "category": "insider",
                    })

    except Exception as e:
        logger.warning("Error fetching insider transactions for CIK %s: %s", cik, e)

    return events


def _fetch_8k_events(cik: str, years: int = 2) -> List[Dict[str, Any]]:
    """
    Parse 8-K filings for specific material events.

    8-K item numbers indicate event types:
    1.01 - Entry into Material Agreement
    1.02 - Termination of Material Agreement
    2.01 - Acquisition or Disposition
    2.02 - Results of Operations
    3.01 - Delisting
    5.02 - Executive Officer Changes
    5.03 - Amendment to Articles
    7.01 - Regulation FD Disclosure
    8.01 - Other Events
    """
    events = []

    try:
        url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        resp = sec_get(url, timeout=15)

        if resp is None or not resp.ok:
            return events

        data = resp.json()
        filings = data.get("filings", {}).get("recent", {})

        forms = filings.get("form", [])
        dates = filings.get("filingDate", [])
        items = filings.get("items", [])

        cutoff = datetime.now() - timedelta(days=years*365)

        for i, form in enumerate(forms):
            if form != "8-K":
                continue
            if i >= len(dates):
                continue

            filing_date = dates[i]
            if datetime.strptime(filing_date, "%Y-%m-%d") < cutoff:
                continue

            item_str = items[i] if i < len(items) else ""

            # Parse item codes for specific events
            if "5.02" in item_str:
                events.append({
                    "date": filing_date,
                    "event_type": "executive_change",
                    "title": "Executive Change Announced (8-K 5.02)",
                    "item_code": "5.02",
                    "source": "SEC 8-K",
                    "priority": 8,
                    "category": "governance",
                })
            elif "2.01" in item_str:
                events.append({
                    "date": filing_date,
                    "event_type": "acquisition_disposition",
                    "title": "Acquisition/Disposition (8-K 2.01)",
                    "item_code": "2.01",
                    "source": "SEC 8-K",
                    "priority": 9,
                    "category": "strategic",
                })
            elif "1.01" in item_str:
                events.append({
                    "date": filing_date,
                    "event_type": "material_agreement",
                    "title": "Material Agreement (8-K 1.01)",
                    "item_code": "1.01",
                    "source": "SEC 8-K",
                    "priority": 7,
                    "category": "strategic",
                })
            elif "2.02" in item_str:
                events.append({
                    "date": filing_date,
                    "event_type": "earnings_release",
                    "title": "Earnings Release (8-K 2.02)",
                    "item_code": "2.02",
                    "source": "SEC 8-K",
                    "priority": 8,
                    "category": "financial",
                })

    except Exception as e:
        logger.warning("Error parsing 8-K events for CIK %s: %s", cik, e)

    return events


def generate_entity_timeline(
    ticker: str,
    years: int = 2,
    include_price: bool = True,
    include_insider: bool = True,
    categories: List[str] = None,
) -> Dict[str, Any]:
    """
    Generate comprehensive timeline for an entity.

    Aggregates events from:
    - SEC filings
    - Stock price movements
    - Insider transactions
    - Material 8-K events

    Args:
        ticker: Stock ticker symbol
        years: Years of history to include
        include_price: Include price movement events
        include_insider: Include insider transaction events
        categories: Filter to specific categories

    Returns:
        Complete event timeline with statistics.
    """
    result = {
        "ticker": ticker,
        "period_years": years,
        "events": [],
        "by_category": defaultdict(list),
        "by_month": defaultdict(list),
        "statistics": {
            "total_events": 0,
            "high_priority_events": 0,
            "events_by_category": {},
            "busiest_month": "",
            "avg_events_per_month": 0,
        },
        "highlights": [],
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }

    cik = _get_cik_from_ticker(ticker)
    if not cik:
        result["error"] = f"Could not resolve CIK for {ticker}"
        return result

    all_events = []

    # Fetch events from all sources in parallel
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(_fetch_sec_filings, cik, years): "sec_filings",
            executor.submit(_fetch_8k_events, cik, years): "8k_events",
        }

        if include_price:
            futures[executor.submit(_fetch_stock_events, ticker, years)] = "stock_events"

        if include_insider:
            futures[executor.submit(_fetch_insider_transactions, cik, years)] = "insider_events"

        for future in as_completed(futures):
            source = futures[future]
            try:
                events = future.result()
                all_events.extend(events)
            except Exception as e:
                logger.warning("Error fetching %s: %s", source, e)

    # Filter by categories if specified
    if categories:
        all_events = [e for e in all_events if e.get("category") in categories]

    # Sort by date descending, then priority
    all_events.sort(key=lambda x: (x.get("date", ""), x.get("priority", 0)), reverse=True)

    # Resolve what each 8-K actually reported. Done after sorting so the most
    # recent filings are the ones enriched when the cap binds.
    if cik:
        try:
            all_events = enrich_8k_items(cik, all_events)
        except Exception as e:
            logger.warning("8-K item enrichment failed for %s: %s", ticker, e)

    # Deduplicate similar events on same day
    seen = set()
    unique_events = []
    for event in all_events:
        key = f"{event.get('date')}_{event.get('event_type')}_{event.get('title', '')[:30]}"
        if key not in seen:
            seen.add(key)
            unique_events.append(event)

    result["events"] = unique_events

    # Organize by category and month
    for event in unique_events:
        category = event.get("category", "other")
        result["by_category"][category].append(event)

        month = event.get("date", "")[:7]  # YYYY-MM
        result["by_month"][month].append(event)

    # Calculate statistics
    result["statistics"]["total_events"] = len(unique_events)
    result["statistics"]["high_priority_events"] = len([
        e for e in unique_events if e.get("priority", 0) >= 7
    ])

    for category, events in result["by_category"].items():
        result["statistics"]["events_by_category"][category] = len(events)

    if result["by_month"]:
        busiest_month = max(result["by_month"].items(), key=lambda x: len(x[1]))
        result["statistics"]["busiest_month"] = busiest_month[0]
        result["statistics"]["avg_events_per_month"] = round(
            len(unique_events) / len(result["by_month"]), 1
        )

    # Generate highlights (highest priority events)
    result["highlights"] = sorted(
        unique_events,
        key=lambda x: x.get("priority", 0),
        reverse=True,
    )[:10]

    return result


def generate_event_chronology(
    ticker: str,
    start_date: str = "",
    end_date: str = "",
    event_types: List[str] = None,
) -> Dict[str, Any]:
    """
    Generate focused chronology for a specific time period.

    Args:
        ticker: Stock ticker symbol
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        event_types: Filter to specific event types

    Returns:
        Chronological event listing.
    """
    # Calculate years needed
    if start_date and end_date:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        years = max(1, (end - start).days // 365 + 1)
    else:
        years = 2
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=730)).strftime("%Y-%m-%d")

    timeline = generate_entity_timeline(ticker, years=years)

    # Filter to date range
    events = []
    for event in timeline.get("events", []):
        event_date = event.get("date", "")
        if event_date and start_date <= event_date <= end_date:
            if event_types is None or event.get("event_type") in event_types:
                events.append(event)

    return {
        "ticker": ticker,
        "start_date": start_date,
        "end_date": end_date,
        "events": events,
        "total_events": len(events),
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


def compare_entity_timelines(
    tickers: List[str],
    years: int = 2,
) -> Dict[str, Any]:
    """
    Compare timelines across multiple entities.

    Useful for identifying correlated events across competitors.

    Args:
        tickers: List of stock tickers
        years: Years of history

    Returns:
        Comparative timeline analysis.
    """
    result = {
        "tickers": tickers,
        "period_years": years,
        "timelines": {},
        "correlated_events": [],
        "summary": {
            "events_by_ticker": {},
            "total_events": 0,
        },
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }

    # Fetch all timelines
    with ThreadPoolExecutor(max_workers=len(tickers)) as executor:
        futures = {
            executor.submit(generate_entity_timeline, ticker, years): ticker
            for ticker in tickers
        }

        for future in as_completed(futures):
            ticker = futures[future]
            try:
                timeline = future.result()
                result["timelines"][ticker] = timeline
                result["summary"]["events_by_ticker"][ticker] = timeline.get(
                    "statistics", {}
                ).get("total_events", 0)
                result["summary"]["total_events"] += result["summary"]["events_by_ticker"][ticker]
            except Exception as e:
                logger.warning("Error fetching timeline for %s: %s", ticker, e)

    # Find correlated events (same day, similar type)
    events_by_date: Dict[str, List[Tuple[str, Dict]]] = defaultdict(list)

    for ticker, timeline in result["timelines"].items():
        for event in timeline.get("events", []):
            date = event.get("date", "")
            if date:
                events_by_date[date].append((ticker, event))

    for date, ticker_events in events_by_date.items():
        if len(ticker_events) >= 2:
            # Multiple companies have events on same day
            result["correlated_events"].append({
                "date": date,
                "events": [
                    {"ticker": ticker, "event": event}
                    for ticker, event in ticker_events
                ],
            })

    # Sort correlated events by date
    result["correlated_events"].sort(key=lambda x: x["date"], reverse=True)

    return result


def generate_timeline_markdown(timeline: Dict[str, Any]) -> str:
    """
    Generate markdown-formatted timeline for reports.

    Args:
        timeline: Output from generate_entity_timeline

    Returns:
        Markdown string for inclusion in reports.
    """
    lines = []
    ticker = timeline.get("ticker", "")

    lines.append(f"## Event Chronology: {ticker}")
    lines.append("")

    # Highlights section
    highlights = timeline.get("highlights", [])[:5]
    if highlights:
        lines.append("### Key Events")
        lines.append("")
        for event in highlights:
            date = event.get("date", "")
            title = event.get("title", "")
            category = event.get("category", "").title()
            lines.append(f"- **{date}** | {category} | {title}")
        lines.append("")

    # Full chronology by month
    by_month = timeline.get("by_month", {})
    if by_month:
        lines.append("### Monthly Chronology")
        lines.append("")

        for month in sorted(by_month.keys(), reverse=True):
            events = by_month[month]
            lines.append(f"#### {month}")
            lines.append("")

            for event in sorted(events, key=lambda x: x.get("date", ""), reverse=True):
                date = event.get("date", "")
                title = event.get("title", "")
                source = event.get("source", "")
                lines.append(f"- {date}: {title} _{source}_")

            lines.append("")

    # Statistics
    stats = timeline.get("statistics", {})
    if stats:
        lines.append("### Statistics")
        lines.append("")
        lines.append(f"- Total Events: {stats.get('total_events', 0)}")
        lines.append(f"- High Priority Events: {stats.get('high_priority_events', 0)}")
        lines.append(f"- Busiest Month: {stats.get('busiest_month', 'N/A')}")
        lines.append(f"- Average Events/Month: {stats.get('avg_events_per_month', 0)}")
        lines.append("")

        if stats.get("events_by_category"):
            lines.append("**By Category:**")
            for category, count in stats["events_by_category"].items():
                lines.append(f"- {category.title()}: {count}")
            lines.append("")

    return "\n".join(lines)


# ── Convenience Exports ──────────────────────────────────────────────────────

def get_timeline(ticker: str, years: int = 2) -> Dict[str, Any]:
    """Generate entity timeline."""
    return generate_entity_timeline(ticker, years)


def get_chronology(ticker: str, start: str = "", end: str = "") -> Dict[str, Any]:
    """Generate focused chronology."""
    return generate_event_chronology(ticker, start, end)


def compare_timelines(tickers: List[str], years: int = 2) -> Dict[str, Any]:
    """Compare multiple entity timelines."""
    return compare_entity_timelines(tickers, years)


def timeline_to_markdown(timeline: Dict[str, Any]) -> str:
    """Convert timeline to markdown."""
    return generate_timeline_markdown(timeline)
