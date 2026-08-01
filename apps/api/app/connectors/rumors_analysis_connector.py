"""
Rumors and Next Steps Analysis Connector (G-10)
────────────────────────────────────────────────────────────────────────────
Analyzes news, social media, and analyst reports to identify:
  - M&A rumors and speculation
  - Product/service launch announcements
  - Partnership/JV discussions
  - Management change rumors
  - Strategic direction hints
  - Analyst predictions and price targets

Uses Apify web scraping and news APIs to gather intelligence.
"""

import os
import re
import time
import logging
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

APIFY_TOKEN = os.getenv("APIFY_API_TOKEN", "")
APIFY_BASE = "https://api.apify.com/v2"

# News API (newsapi.org - free tier available)
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
NEWS_API_URL = "https://newsapi.org/v2/everything"

# Alpha Vantage for news sentiment (free tier)
ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY", "")
ALPHA_VANTAGE_NEWS = "https://www.alphavantage.co/query"


def _run_apify_actor(actor_id: str, input_data: dict, wait_secs: int = 120) -> List[dict]:
    """Run an Apify actor and return results."""
    if not APIFY_TOKEN:
        logger.warning("APIFY_API_TOKEN not set — skipping web scraping")
        return []

    actor_id_url = actor_id.replace("/", "~")

    try:
        run_resp = requests.post(
            f"{APIFY_BASE}/acts/{actor_id_url}/runs",
            params={"token": APIFY_TOKEN, "waitForFinish": 60},
            json=input_data,
            timeout=90,
        )
        if not run_resp.ok:
            logger.warning("Apify run failed (%s): %s", run_resp.status_code, run_resp.text[:300])
            return []

        run_data = run_resp.json().get("data", run_resp.json())
        dataset_id = run_data.get("defaultDatasetId")
        run_id = run_data.get("id")

        if not dataset_id:
            return []

        # Poll until done
        status = run_data.get("status", "")
        elapsed = 60
        poll_interval = 10
        while status not in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT") and elapsed < wait_secs and run_id:
            time.sleep(poll_interval)
            elapsed += poll_interval
            poll_resp = requests.get(
                f"{APIFY_BASE}/actor-runs/{run_id}",
                params={"token": APIFY_TOKEN},
                timeout=15,
            )
            if poll_resp.ok:
                status = poll_resp.json().get("data", {}).get("status", status)

        if status not in ("SUCCEEDED", "READY"):
            logger.warning("Apify run ended with status %s", status)
            if status in ("FAILED", "ABORTED", "TIMED-OUT"):
                return []

        items_resp = requests.get(
            f"{APIFY_BASE}/datasets/{dataset_id}/items",
            params={"token": APIFY_TOKEN, "clean": "true", "format": "json"},
            timeout=30,
        )
        if not items_resp.ok:
            return []

        items = items_resp.json()
        return items if isinstance(items, list) else []

    except Exception as exc:
        logger.warning("Apify connector error: %s", exc)
        return []


# Rumor categories and keywords
RUMOR_CATEGORIES = {
    "ma_acquisition": {
        "keywords": [
            "acquire", "acquisition", "merger", "takeover", "buyout",
            "deal talks", "in talks to buy", "exploring acquisition",
            "strategic buyer", "private equity", "LBO"
        ],
        "weight": 1.5,
        "label": "M&A / Acquisition"
    },
    "ma_target": {
        "keywords": [
            "acquisition target", "takeover target", "being acquired",
            "approached by", "suitor", "bidding war", "sale process"
        ],
        "weight": 1.5,
        "label": "Acquisition Target"
    },
    "product_launch": {
        "keywords": [
            "launch", "unveil", "announce", "release", "debut",
            "new product", "next generation", "upcoming", "preview"
        ],
        "weight": 1.0,
        "label": "Product Launch"
    },
    "partnership": {
        "keywords": [
            "partnership", "joint venture", "collaborate", "alliance",
            "team up", "strategic partnership", "licensing deal"
        ],
        "weight": 1.0,
        "label": "Partnership / JV"
    },
    "management_change": {
        "keywords": [
            "CEO", "stepping down", "resign", "succession", "new CEO",
            "leadership change", "executive departure", "board shakeup"
        ],
        "weight": 1.3,
        "label": "Management Change"
    },
    "restructuring": {
        "keywords": [
            "restructuring", "layoffs", "cost cutting", "reorganization",
            "spin-off", "divest", "sell off", "streamline"
        ],
        "weight": 1.2,
        "label": "Restructuring"
    },
    "regulatory": {
        "keywords": [
            "antitrust", "DOJ", "FTC", "investigation", "regulatory",
            "approval", "lawsuit", "settlement", "fine"
        ],
        "weight": 1.3,
        "label": "Regulatory / Legal"
    },
    "financial": {
        "keywords": [
            "earnings", "guidance", "forecast", "upgrade", "downgrade",
            "price target", "analyst", "rating", "beat", "miss"
        ],
        "weight": 1.0,
        "label": "Financial / Analyst"
    },
    "expansion": {
        "keywords": [
            "expand", "expansion", "new market", "international",
            "enter", "growth", "scaling", "geographic"
        ],
        "weight": 1.0,
        "label": "Market Expansion"
    },
    "technology": {
        "keywords": [
            "AI", "artificial intelligence", "machine learning", "cloud",
            "patent", "innovation", "breakthrough", "R&D"
        ],
        "weight": 1.1,
        "label": "Technology / Innovation"
    }
}


def _categorize_article(title: str, description: str) -> List[Dict[str, Any]]:
    """Categorize an article based on rumor keywords."""
    text = f"{title} {description}".lower()
    matches = []

    for category, config in RUMOR_CATEGORIES.items():
        keywords = config["keywords"]
        matched_keywords = [kw for kw in keywords if kw.lower() in text]

        if matched_keywords:
            matches.append({
                "category": category,
                "label": config["label"],
                "matched_keywords": matched_keywords,
                "relevance_score": len(matched_keywords) * config["weight"]
            })

    return sorted(matches, key=lambda x: x["relevance_score"], reverse=True)


def _extract_entities(text: str, company_name: str) -> List[str]:
    """Extract company/person names mentioned alongside target company."""
    entities = []

    # Common patterns for entity extraction
    patterns = [
        r'(?:with|and|by|from)\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)',
        r'([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)\s+(?:and|or)\s+' + re.escape(company_name.split()[0]),
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            # Filter out common words
            if match.lower() not in ["the", "a", "an", "this", "that", "and", "or", "but"]:
                entities.append(match)

    return list(set(entities))[:5]


def search_news_rumors(
    company_name: str,
    ticker: str = "",
    days_back: int = 30,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Search news sources for rumors and speculation.
    Uses NewsAPI if available, otherwise falls back to web scraping.
    """
    articles = []

    # Try NewsAPI first
    if NEWS_API_KEY:
        try:
            params = {
                "apiKey": NEWS_API_KEY,
                "q": f'"{company_name}" OR "{ticker}"',
                "from": (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d"),
                "sortBy": "relevancy",
                "language": "en",
                "pageSize": limit,
            }

            resp = requests.get(NEWS_API_URL, params=params, timeout=20)
            if resp.ok:
                data = resp.json()
                for article in data.get("articles", []):
                    categories = _categorize_article(
                        article.get("title", ""),
                        article.get("description", "")
                    )

                    if categories:  # Only include categorized articles
                        articles.append({
                            "title": article.get("title"),
                            "description": article.get("description"),
                            "source": article.get("source", {}).get("name"),
                            "url": article.get("url"),
                            "published_at": article.get("publishedAt"),
                            "categories": categories,
                            "primary_category": categories[0]["label"] if categories else None,
                            "relevance_score": sum(c["relevance_score"] for c in categories),
                        })
        except Exception as e:
            logger.warning("NewsAPI search failed: %s", e)

    # Use Apify Google News scraper as backup
    if not articles and APIFY_TOKEN:
        search_queries = [
            f'"{company_name}" rumors',
            f'"{company_name}" acquisition',
            f'"{ticker}" analyst upgrade downgrade',
        ]

        for query in search_queries[:2]:
            results = _run_apify_actor(
                "apify/google-search-scraper",
                {
                    "queries": query,
                    "maxPagesPerQuery": 1,
                    "resultsPerPage": 15,
                    "mobileResults": False,
                },
                wait_secs=60,
            )

            for result in results:
                for item in result.get("organicResults", []):
                    title = item.get("title", "")
                    description = item.get("description", "")
                    categories = _categorize_article(title, description)

                    if categories:
                        articles.append({
                            "title": title,
                            "description": description,
                            "source": item.get("displayedUrl", "").split("/")[0] if item.get("displayedUrl") else "web",
                            "url": item.get("url"),
                            "published_at": item.get("date"),
                            "categories": categories,
                            "primary_category": categories[0]["label"] if categories else None,
                            "relevance_score": sum(c["relevance_score"] for c in categories),
                        })

            time.sleep(1)

    # Sort by relevance and deduplicate
    seen_urls = set()
    unique_articles = []
    for article in sorted(articles, key=lambda x: x.get("relevance_score", 0), reverse=True):
        url = article.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_articles.append(article)

    return unique_articles[:limit]


def search_analyst_opinions(
    company_name: str,
    ticker: str = "",
    limit: int = 20
) -> List[Dict[str, Any]]:
    """Search for analyst ratings and price target changes."""
    opinions = []

    # Try Alpha Vantage news sentiment
    if ALPHA_VANTAGE_KEY and ticker:
        try:
            resp = requests.get(
                ALPHA_VANTAGE_NEWS,
                params={
                    "function": "NEWS_SENTIMENT",
                    "tickers": ticker,
                    "apikey": ALPHA_VANTAGE_KEY,
                    "limit": limit,
                },
                timeout=20,
            )
            if resp.ok:
                data = resp.json()
                for item in data.get("feed", []):
                    # Find ticker sentiment
                    ticker_sentiment = None
                    for ts in item.get("ticker_sentiment", []):
                        if ts.get("ticker") == ticker:
                            ticker_sentiment = ts
                            break

                    opinions.append({
                        "title": item.get("title"),
                        "source": item.get("source"),
                        "url": item.get("url"),
                        "published_at": item.get("time_published"),
                        "overall_sentiment": item.get("overall_sentiment_label"),
                        "sentiment_score": float(item.get("overall_sentiment_score", 0)),
                        "ticker_relevance": float(ticker_sentiment.get("relevance_score", 0)) if ticker_sentiment else 0,
                        "ticker_sentiment": ticker_sentiment.get("ticker_sentiment_label") if ticker_sentiment else None,
                    })
        except Exception as e:
            logger.warning("Alpha Vantage news sentiment failed: %s", e)

    # Supplement with web search for analyst opinions
    if APIFY_TOKEN:
        results = _run_apify_actor(
            "apify/google-search-scraper",
            {
                "queries": f'"{ticker}" OR "{company_name}" analyst rating price target site:seekingalpha.com OR site:tipranks.com OR site:marketwatch.com',
                "maxPagesPerQuery": 1,
                "resultsPerPage": 10,
            },
            wait_secs=60,
        )

        for result in results:
            for item in result.get("organicResults", []):
                title = item.get("title", "")

                # Extract price target if mentioned
                price_match = re.search(r'\$(\d+(?:\.\d+)?)', title)
                price_target = float(price_match.group(1)) if price_match else None

                # Extract rating action
                rating_action = None
                title_lower = title.lower()
                if "upgrade" in title_lower:
                    rating_action = "Upgrade"
                elif "downgrade" in title_lower:
                    rating_action = "Downgrade"
                elif "initiate" in title_lower or "initiates" in title_lower:
                    rating_action = "Initiate"
                elif "reiterate" in title_lower or "maintains" in title_lower:
                    rating_action = "Reiterate"

                opinions.append({
                    "title": title,
                    "source": item.get("displayedUrl", "").split("/")[0] if item.get("displayedUrl") else "web",
                    "url": item.get("url"),
                    "published_at": item.get("date"),
                    "rating_action": rating_action,
                    "price_target": price_target,
                    "overall_sentiment": None,
                })

    return opinions[:limit]


def search_social_buzz(
    company_name: str,
    ticker: str = "",
    limit: int = 30
) -> List[Dict[str, Any]]:
    """Search social media for company mentions and sentiment."""
    buzz = []

    if not APIFY_TOKEN:
        return buzz

    # Twitter/X search (via Apify)
    try:
        results = _run_apify_actor(
            "apify/twitter-scraper",
            {
                "searchTerms": [f"${ticker}", company_name],
                "maxTweets": limit,
                "sort": "Top",
            },
            wait_secs=90,
        )

        for tweet in results:
            text = tweet.get("full_text") or tweet.get("text", "")
            categories = _categorize_article(text, "")

            buzz.append({
                "platform": "Twitter/X",
                "text": text[:500],
                "author": tweet.get("user", {}).get("screen_name"),
                "followers": tweet.get("user", {}).get("followers_count", 0),
                "engagement": (
                    (tweet.get("retweet_count") or 0) +
                    (tweet.get("favorite_count") or 0)
                ),
                "created_at": tweet.get("created_at"),
                "url": tweet.get("url"),
                "categories": categories,
            })
    except Exception as e:
        logger.warning("Twitter scraping failed: %s", e)

    # Sort by engagement
    return sorted(buzz, key=lambda x: x.get("engagement", 0), reverse=True)[:limit]


def analyze_rumors_and_next_steps(
    company_name: str,
    ticker: str = "",
    days_back: int = 30,
    include_social: bool = True,
) -> Dict[str, Any]:
    """
    Comprehensive rumors and next steps analysis.

    Args:
        company_name: Company name
        ticker: Stock ticker
        days_back: Number of days to look back
        include_social: Whether to include social media analysis

    Returns:
        Complete rumors analysis with categorized findings
    """
    logger.info("Starting rumors analysis for %s (%s)", company_name, ticker)

    # Gather data in parallel
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(search_news_rumors, company_name, ticker, days_back, 50): "news",
            executor.submit(search_analyst_opinions, company_name, ticker, 20): "analyst",
        }

        if include_social:
            futures[executor.submit(search_social_buzz, company_name, ticker, 30)] = "social"

        results = {}
        for future in as_completed(futures):
            key = futures[future]
            try:
                results[key] = future.result(timeout=120)
            except Exception as e:
                logger.warning("Rumors search failed for %s: %s", key, e)
                results[key] = []

    news_articles = results.get("news", [])
    analyst_opinions = results.get("analyst", [])
    social_buzz = results.get("social", [])

    # Aggregate by category
    category_summary = defaultdict(lambda: {"count": 0, "articles": [], "total_relevance": 0})

    for article in news_articles:
        primary = article.get("primary_category")
        if primary:
            category_summary[primary]["count"] += 1
            category_summary[primary]["total_relevance"] += article.get("relevance_score", 0)
            category_summary[primary]["articles"].append(article)

    # Identify emerging themes
    emerging_themes = []
    for category, data in sorted(
        category_summary.items(),
        key=lambda x: x[1]["total_relevance"],
        reverse=True
    ):
        if data["count"] >= 2:  # At least 2 articles to be a theme
            emerging_themes.append({
                "theme": category,
                "article_count": data["count"],
                "relevance_score": data["total_relevance"],
                "sample_articles": data["articles"][:3],
            })

    # Calculate overall sentiment from analyst opinions
    sentiment_scores = [
        op.get("sentiment_score", 0)
        for op in analyst_opinions
        if op.get("sentiment_score") is not None
    ]
    avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0

    # Price target aggregation
    price_targets = [
        op.get("price_target")
        for op in analyst_opinions
        if op.get("price_target") is not None
    ]

    # Generate next steps/predictions
    next_steps = _generate_next_steps(
        emerging_themes,
        analyst_opinions,
        social_buzz,
        company_name
    )

    return {
        "company": company_name,
        "ticker": ticker,
        "analysis_date": datetime.utcnow().isoformat() + "Z",
        "lookback_days": days_back,

        "summary": {
            "total_news_articles": len(news_articles),
            "total_analyst_opinions": len(analyst_opinions),
            "total_social_mentions": len(social_buzz),
            "emerging_theme_count": len(emerging_themes),
            "average_sentiment": round(avg_sentiment, 3),
            "sentiment_label": _sentiment_label(avg_sentiment),
        },

        "emerging_themes": emerging_themes[:5],

        "price_targets": {
            "count": len(price_targets),
            "average": round(sum(price_targets) / len(price_targets), 2) if price_targets else None,
            "high": max(price_targets) if price_targets else None,
            "low": min(price_targets) if price_targets else None,
        },

        "top_news": news_articles[:10],
        "analyst_opinions": analyst_opinions[:10],
        "social_highlights": social_buzz[:10],

        "next_steps_predictions": next_steps,

        "data_sources": {
            "news_api": bool(NEWS_API_KEY),
            "apify_scraping": bool(APIFY_TOKEN),
            "alpha_vantage": bool(ALPHA_VANTAGE_KEY),
        }
    }


def _sentiment_label(score: float) -> str:
    """Convert sentiment score to label."""
    if score > 0.15:
        return "Bullish"
    elif score > 0.05:
        return "Somewhat Bullish"
    elif score < -0.15:
        return "Bearish"
    elif score < -0.05:
        return "Somewhat Bearish"
    else:
        return "Neutral"


def _generate_next_steps(
    themes: List[Dict[str, Any]],
    analyst_opinions: List[Dict[str, Any]],
    social_buzz: List[Dict[str, Any]],
    company_name: str
) -> List[Dict[str, Any]]:
    """Generate predictions for next steps based on analysis."""
    predictions = []

    # Theme-based predictions
    theme_labels = [t["theme"] for t in themes]

    if "M&A / Acquisition" in theme_labels or "Acquisition Target" in theme_labels:
        predictions.append({
            "category": "M&A Activity",
            "prediction": f"M&A activity appears likely based on recent news coverage. Monitor for official announcements.",
            "confidence": "Medium",
            "timeframe": "1-6 months",
            "supporting_evidence": len([t for t in themes if "M&A" in t["theme"] or "Acquisition" in t["theme"]]),
        })

    if "Management Change" in theme_labels:
        predictions.append({
            "category": "Leadership Transition",
            "prediction": "Leadership changes may be imminent. Watch for succession announcements.",
            "confidence": "Medium",
            "timeframe": "1-3 months",
            "supporting_evidence": len([t for t in themes if t["theme"] == "Management Change"]),
        })

    if "Product Launch" in theme_labels:
        predictions.append({
            "category": "Product Announcement",
            "prediction": "New product or service announcement expected based on media coverage patterns.",
            "confidence": "Medium",
            "timeframe": "1-3 months",
            "supporting_evidence": len([t for t in themes if t["theme"] == "Product Launch"]),
        })

    if "Restructuring" in theme_labels:
        predictions.append({
            "category": "Corporate Restructuring",
            "prediction": "Cost-cutting or reorganization measures may be announced.",
            "confidence": "Medium",
            "timeframe": "0-3 months",
            "supporting_evidence": len([t for t in themes if t["theme"] == "Restructuring"]),
        })

    if "Regulatory / Legal" in theme_labels:
        predictions.append({
            "category": "Regulatory Development",
            "prediction": "Regulatory action or settlement may be forthcoming.",
            "confidence": "Low-Medium",
            "timeframe": "1-12 months",
            "supporting_evidence": len([t for t in themes if t["theme"] == "Regulatory / Legal"]),
        })

    # Analyst-based predictions
    upgrades = len([op for op in analyst_opinions if op.get("rating_action") == "Upgrade"])
    downgrades = len([op for op in analyst_opinions if op.get("rating_action") == "Downgrade"])

    if upgrades > downgrades and upgrades >= 2:
        predictions.append({
            "category": "Analyst Sentiment Shift",
            "prediction": f"Positive analyst momentum with {upgrades} recent upgrades. Price appreciation likely.",
            "confidence": "Medium",
            "timeframe": "1-6 months",
            "supporting_evidence": upgrades,
        })
    elif downgrades > upgrades and downgrades >= 2:
        predictions.append({
            "category": "Analyst Sentiment Shift",
            "prediction": f"Negative analyst momentum with {downgrades} recent downgrades. Caution warranted.",
            "confidence": "Medium",
            "timeframe": "1-6 months",
            "supporting_evidence": downgrades,
        })

    # If no specific predictions, add general outlook
    if not predictions:
        predictions.append({
            "category": "General Outlook",
            "prediction": "No significant catalysts identified in recent news. Business as usual expected.",
            "confidence": "Low",
            "timeframe": "Ongoing",
            "supporting_evidence": 0,
        })

    return predictions


def render_rumors_analysis_markdown(analysis: Dict[str, Any]) -> List[str]:
    """Render rumors analysis as markdown."""
    lines = ["## Rumors and Next Steps Analysis", ""]

    summary = analysis.get("summary", {})
    themes = analysis.get("emerging_themes", [])
    predictions = analysis.get("next_steps_predictions", [])
    price_targets = analysis.get("price_targets", {})
    top_news = analysis.get("top_news", [])

    # Overview
    lines.append("### Intelligence Summary")
    lines.append("")
    lines.append(
        f"Analysis of **{summary.get('total_news_articles', 0)} news articles**, "
        f"**{summary.get('total_analyst_opinions', 0)} analyst opinions**, and "
        f"**{summary.get('total_social_mentions', 0)} social mentions** over the past "
        f"{analysis.get('lookback_days', 30)} days."
    )
    lines.append("")

    sentiment = summary.get("sentiment_label", "Neutral")
    sentiment_icon = {
        "Bullish": "📈", "Somewhat Bullish": "📊",
        "Bearish": "📉", "Somewhat Bearish": "📊",
        "Neutral": "➡️"
    }.get(sentiment, "➡️")

    lines.append(f"**Overall Market Sentiment:** {sentiment_icon} {sentiment}")
    lines.append("")

    # Price Targets
    if price_targets.get("count"):
        lines.append("### Analyst Price Targets")
        lines.append("")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Average Target | ${price_targets.get('average', 'N/A')} |")
        lines.append(f"| High Target | ${price_targets.get('high', 'N/A')} |")
        lines.append(f"| Low Target | ${price_targets.get('low', 'N/A')} |")
        lines.append(f"| # of Targets | {price_targets.get('count', 0)} |")
        lines.append("")

    # Emerging Themes
    if themes:
        lines.append("### Emerging Themes")
        lines.append("")

        for theme in themes[:5]:
            theme_name = theme.get("theme", "Unknown")
            count = theme.get("article_count", 0)
            relevance = theme.get("relevance_score", 0)

            lines.append(f"#### {theme_name}")
            lines.append(f"*{count} articles | Relevance score: {relevance:.1f}*")
            lines.append("")

            for article in theme.get("sample_articles", [])[:2]:
                title = article.get("title", "")[:80]
                source = article.get("source", "Unknown")
                url = article.get("url", "")
                if url:
                    lines.append(f"- [{title}]({url}) — {source}")
                else:
                    lines.append(f"- {title} — {source}")
            lines.append("")

    # Next Steps / Predictions
    if predictions:
        lines.append("### Predicted Next Steps")
        lines.append("")

        for pred in predictions:
            category = pred.get("category", "General")
            prediction = pred.get("prediction", "")
            confidence = pred.get("confidence", "Low")
            timeframe = pred.get("timeframe", "Unknown")

            confidence_icon = {"High": "🟢", "Medium": "🟡", "Low": "🟠", "Low-Medium": "🟠"}.get(confidence, "⚪")

            lines.append(f"**{category}** {confidence_icon}")
            lines.append(f"> {prediction}")
            lines.append(f"*Confidence: {confidence} | Timeframe: {timeframe}*")
            lines.append("")

    # Top News Items
    if top_news:
        lines.append("### Key News Coverage")
        lines.append("")

        for article in top_news[:7]:
            title = article.get("title", "")[:70]
            source = article.get("source", "Unknown")
            url = article.get("url", "")
            category = article.get("primary_category", "General")
            pub_date = article.get("published_at", "")[:10] if article.get("published_at") else ""

            if url:
                lines.append(f"- [{title}]({url})")
            else:
                lines.append(f"- {title}")
            lines.append(f"  *{source} | {pub_date} | {category}*")
        lines.append("")

    lines.append("*Sources: NewsAPI, Google News, Alpha Vantage, Twitter/X via Apify*")
    lines.append("")

    return lines
