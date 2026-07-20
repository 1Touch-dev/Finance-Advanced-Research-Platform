"""
Stock Expert Analysis & Sentiment Tracker
────────────────────────────────────────────────────────────────────────────
Aggregates analyst reports, expert opinions, and news sentiment for a stock:
  - Multi-source news aggregation (NewsAPI, Guardian, NYT, RSS)
  - Analyst upgrade/downgrade timeline from yfinance
  - Sentiment scoring over time (weekly/monthly buckets)
  - Key themes extraction from article titles/summaries
  - Expert opinion clustering (bullish/bearish/neutral)
"""
import os
import re
import time
import logging
import requests
from datetime import datetime, timedelta
from collections import defaultdict

log = logging.getLogger(__name__)

BULLISH_WORDS = {
    "surge", "jump", "gain", "rally", "beat", "record", "growth", "profit", "strong",
    "upgrade", "buy", "bullish", "positive", "rise", "soar", "boost", "outperform",
    "exceed", "better", "upside", "attractive", "opportunity", "momentum", "breakout",
    "undervalued", "cheap", "value", "accumulate", "overweight", "target raise",
    "raised target", "price target raised", "initiates", "initiating coverage",
    "strong buy", "outperform", "conviction", "top pick", "best idea",
}

BEARISH_WORDS = {
    "drop", "fall", "decline", "loss", "miss", "cut", "downgrade", "sell", "bearish",
    "negative", "concern", "risk", "warn", "crash", "plunge", "debt", "weak",
    "disappoint", "underperform", "worse", "overvalued", "expensive", "bubble",
    "short", "reduce", "underweight", "target cut", "price target cut",
    "missed expectations", "below expectations", "disappointing", "challenges",
    "headwinds", "competition", "regulatory", "lawsuit",
}

ANALYST_SIGNAL_WORDS = {
    "initiates", "upgrades", "downgrades", "raises target", "cuts target",
    "reiterates", "maintains", "price target", "outperform", "underperform",
    "buy rating", "sell rating", "analyst", "wall street", "consensus",
    "research note", "research report", "investment thesis",
}


def _safe_score(text: str) -> dict:
    """Score a piece of text for sentiment."""
    text_lower = text.lower()
    b = sum(1 for w in BULLISH_WORDS if w in text_lower)
    be = sum(1 for w in BEARISH_WORDS if w in text_lower)
    a = sum(1 for w in ANALYST_SIGNAL_WORDS if w in text_lower)
    return {"bullish": b, "bearish": be, "analyst_signal": a > 0}


def get_expert_news(ticker: str, company_name: str = "", days: int = 90) -> list:
    """Gather all analyst and expert news articles for a ticker."""
    articles = []
    query = company_name or ticker

    # Source 1: Traditional news APIs
    try:
        from app.connectors.financial_news_connector import aggregate_news
        data = aggregate_news(query, 30) or {}
        raw = data.get("articles", []) if isinstance(data, dict) else []
        for a in raw:
            articles.append({
                "title": a.get("title", ""),
                "summary": a.get("description", a.get("summary", "")),
                "source": a.get("source", {}).get("name", "") if isinstance(a.get("source"), dict) else str(a.get("source", "")),
                "url": a.get("url", ""),
                "published": a.get("publishedAt", a.get("published_at", "")),
                "origin": "news_api",
            })
    except Exception as e:
        log.warning("Expert news API error: %s", e)

    # Source 2: RSS articles from database
    try:
        import os
        from sqlalchemy import create_engine, text as sqlt
        bare_name = (company_name or ticker).split()[0]
        db_url = os.getenv("DATABASE_URL", "postgresql+psycopg://user:password@127.0.0.1:5433/mydb")
        engine = create_engine(db_url)
        with engine.connect() as conn:
            rows = conn.execute(sqlt("""
                SELECT title, summary, source_name, link, published_at
                FROM rss_articles
                WHERE :entity = ANY(matched_entities)
                ORDER BY published_at DESC NULLS LAST LIMIT 40
            """), {"entity": bare_name}).fetchall()
        for r in rows:
            articles.append({
                "title": r.title or "",
                "summary": r.summary or "",
                "source": r.source_name or "RSS",
                "url": r.link or "",
                "published": str(r.published_at or ""),
                "origin": "rss",
            })
    except Exception as e:
        log.debug("RSS expert news error: %s", e)

    # Source 3: Finnhub company news (FINNHUB_API_KEY is available; NewsAPI/
    # Guardian/NYT keys usually are not, so this is the primary live source).
    try:
        import os
        finnhub_key = os.getenv("FINNHUB_API_KEY", "").strip()
        if finnhub_key and ticker:
            to_dt = datetime.utcnow().date()
            from_dt = to_dt - timedelta(days=days)
            resp = requests.get(
                "https://finnhub.io/api/v1/company-news",
                params={"symbol": ticker.upper(), "from": str(from_dt),
                        "to": str(to_dt), "token": finnhub_key},
                timeout=15,
            )
            if resp.ok:
                for a in resp.json()[:60]:
                    dt = a.get("datetime")
                    published = ""
                    if dt:
                        try:
                            published = datetime.utcfromtimestamp(int(dt)).isoformat()
                        except Exception:
                            published = ""
                    articles.append({
                        "title": a.get("headline", ""),
                        "summary": a.get("summary", ""),
                        "source": a.get("source", "Finnhub"),
                        "url": a.get("url", ""),
                        "published": published,
                        "origin": "finnhub",
                    })
    except Exception as e:
        log.warning("Finnhub expert news error: %s", e)

    # Deduplicate by title
    seen = set()
    deduped = []
    for a in articles:
        key = (a["title"] or "")[:80].lower()
        if key and key not in seen:
            seen.add(key)
            deduped.append(a)

    return deduped


def score_articles(articles: list, ticker: str) -> list:
    """Score each article for sentiment and analyst signal."""
    scored = []
    ticker_upper = ticker.upper()
    for a in articles:
        full_text = (a.get("title", "") + " " + (a.get("summary", "") or "")).strip()
        score = _safe_score(full_text)
        is_analyst = score["analyst_signal"] or any(
            w in full_text.lower() for w in ["analyst", "target", "rating", "upgrade", "downgrade"]
        )
        sentiment = (
            "bullish" if score["bullish"] > score["bearish"]
            else "bearish" if score["bearish"] > score["bullish"]
            else "neutral"
        )
        scored.append({
            **a,
            "sentiment": sentiment,
            "bullish_score": score["bullish"],
            "bearish_score": score["bearish"],
            "is_analyst_report": is_analyst,
        })
    return scored


def aggregate_sentiment_over_time(scored_articles: list) -> list:
    """Aggregate sentiment into weekly buckets."""
    weekly = defaultdict(lambda: {"bullish": 0, "bearish": 0, "neutral": 0, "total": 0, "analyst": 0})

    for a in scored_articles:
        pub = a.get("published", "")
        try:
            dt = datetime.fromisoformat(str(pub)[:10])
            week_key = dt.strftime("%Y-W%V")
        except Exception:
            week_key = "unknown"

        weekly[week_key][a["sentiment"]] += 1
        weekly[week_key]["total"] += 1
        if a.get("is_analyst_report"):
            weekly[week_key]["analyst"] += 1

    result = []
    for week, counts in sorted(weekly.items(), reverse=True)[:16]:
        total = max(counts["total"], 1)
        net_sentiment = (counts["bullish"] - counts["bearish"]) / total
        result.append({
            "week": week,
            "total_articles": counts["total"],
            "bullish": counts["bullish"],
            "bearish": counts["bearish"],
            "neutral": counts["neutral"],
            "analyst_reports": counts["analyst"],
            "net_sentiment_score": round(net_sentiment, 3),
            "sentiment": "bullish" if net_sentiment > 0.1 else "bearish" if net_sentiment < -0.1 else "neutral",
        })
    return result


def extract_key_themes(articles: list, top_n: int = 15) -> list:
    """Extract most frequently mentioned themes/topics from article titles."""
    # Common financial keywords to track
    THEME_KEYWORDS = {
        "earnings": ["earnings", "quarterly results", "q1", "q2", "q3", "q4", "fiscal"],
        "revenue": ["revenue", "sales", "net sales", "top line"],
        "guidance": ["guidance", "outlook", "forecast", "project", "expect"],
        "AI": ["ai", "artificial intelligence", "machine learning", "chatgpt", "llm"],
        "product launch": ["launch", "new product", "unveiled", "announces", "release"],
        "acquisition": ["acquires", "acquisition", "buyout", "merger", "deal"],
        "partnership": ["partnership", "collaborate", "joint venture", "agreement"],
        "layoffs": ["layoffs", "job cuts", "restructuring", "headcount"],
        "regulatory": ["regulation", "antitrust", "sec", "ftc", "lawsuit", "legal"],
        "competition": ["competition", "competitor", "market share", "rival"],
        "buyback": ["buyback", "repurchase", "share buyback"],
        "dividend": ["dividend", "payout", "yield"],
        "debt": ["debt", "borrowing", "credit facility", "bonds"],
        "growth": ["growth", "expansion", "scale", "international"],
        "profit": ["profit", "margin", "profitability", "income"],
    }

    theme_counts = defaultdict(int)
    all_text = " ".join((a.get("title", "") + " " + (a.get("summary", "") or "")) for a in articles).lower()

    for theme, keywords in THEME_KEYWORDS.items():
        for kw in keywords:
            count = all_text.count(kw)
            theme_counts[theme] += count

    return sorted(
        [{"theme": k, "mentions": v} for k, v in theme_counts.items() if v > 0],
        key=lambda x: x["mentions"],
        reverse=True
    )[:top_n]


def get_analyst_timeline(ticker: str, months: int = 12) -> list:
    """Get analyst upgrade/downgrade timeline from yfinance."""
    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)
        df = stock.upgrades_downgrades
        if df is None or df.empty:
            return []
        df = df.reset_index()
        cutoff = datetime.now() - timedelta(days=months * 30)
        events = []
        for _, row in df.iterrows():
            date_val = row.get("GradeDate", row.get("Date", ""))
            try:
                dt = datetime.fromisoformat(str(date_val)[:10])
                if dt < cutoff:
                    continue
            except Exception:
                pass
            to_grade = str(row.get("ToGrade", ""))
            from_grade = str(row.get("FromGrade", ""))
            action = str(row.get("Action", ""))
            sentiment = (
                "bullish" if any(w in to_grade.lower() for w in ["buy", "outperform", "overweight", "strong"])
                else "bearish" if any(w in to_grade.lower() for w in ["sell", "underperform", "underweight", "reduce"])
                else "neutral"
            )
            events.append({
                "date": str(date_val)[:10],
                "firm": str(row.get("Firm", "")),
                "action": action,
                "from_grade": from_grade,
                "to_grade": to_grade,
                "sentiment": sentiment,
            })
        return sorted(events, key=lambda x: x["date"], reverse=True)[:50]
    except Exception as e:
        log.error("Analyst timeline error for %s: %s", ticker, e)
        return []


def expert_analysis_report(ticker: str, company_name: str = "") -> dict:
    """
    Full expert analysis report:
    - All articles scored for sentiment
    - Weekly sentiment trend
    - Key themes
    - Analyst rating timeline
    - Summary stats
    """
    log.info("Building expert analysis for %s", ticker)

    # Resolve the real company name when the caller only gave a ticker. This
    # fixes the "wrong-entity"/ticker-as-name display and improves news matching
    # (name-based sources searched the bare ticker, e.g. "C" for Citigroup).
    if not company_name:
        try:
            import yfinance as yf
            info = yf.Ticker(ticker).info or {}
            company_name = info.get("longName") or info.get("shortName") or ticker
        except Exception:
            company_name = ticker

    articles = get_expert_news(ticker, company_name)
    scored = score_articles(articles, ticker)
    weekly_trend = aggregate_sentiment_over_time(scored)
    themes = extract_key_themes(scored)
    analyst_timeline = get_analyst_timeline(ticker)

    # Analyst-only articles
    analyst_articles = [a for a in scored if a.get("is_analyst_report")]

    # Overall stats
    total = len(scored)
    bullish_count = sum(1 for a in scored if a["sentiment"] == "bullish")
    bearish_count = sum(1 for a in scored if a["sentiment"] == "bearish")
    neutral_count = total - bullish_count - bearish_count
    net_score = (bullish_count - bearish_count) / max(total, 1)
    overall_sentiment = "BULLISH" if net_score > 0.1 else "BEARISH" if net_score < -0.1 else "NEUTRAL"

    # Recent trend (last 30 days vs previous 30 days)
    recent = [a for a in scored if a.get("published", "") > (datetime.now() - timedelta(days=30)).isoformat()[:10]]
    recent_net = (sum(1 for a in recent if a["sentiment"] == "bullish") -
                  sum(1 for a in recent if a["sentiment"] == "bearish")) / max(len(recent), 1)
    trend_direction = "IMPROVING" if recent_net > net_score else "DETERIORATING" if recent_net < net_score else "STABLE"

    return {
        "ticker": ticker,
        "company_name": company_name or ticker,
        "summary": {
            "total_articles": total,
            "bullish": bullish_count,
            "bearish": bearish_count,
            "neutral": neutral_count,
            "analyst_reports": len(analyst_articles),
            "overall_sentiment": overall_sentiment,
            "net_sentiment_score": round(net_score, 3),
            "recent_trend": trend_direction,
        },
        "weekly_sentiment_trend": weekly_trend,
        "key_themes": themes,
        "analyst_timeline": analyst_timeline[:20],
        "top_analyst_articles": analyst_articles[:8],
        "recent_articles": sorted(scored, key=lambda x: x.get("published", ""), reverse=True)[:15],
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
