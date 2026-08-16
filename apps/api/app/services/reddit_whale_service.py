"""
Reddit & Whale Improvements Service (James J4)
Enhanced social sentiment and whale tracking
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import random


@dataclass
class RedditPost:
    """Reddit post with sentiment"""
    post_id: str
    subreddit: str
    title: str
    content: str
    author: str
    score: int
    comments: int
    created_at: str
    sentiment: str  # bullish, bearish, neutral
    sentiment_score: float
    tickers_mentioned: List[str] = field(default_factory=list)
    url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "post_id": self.post_id,
            "subreddit": self.subreddit,
            "title": self.title,
            "content": self.content,
            "author": self.author,
            "score": self.score,
            "comments": self.comments,
            "created_at": self.created_at,
            "sentiment": self.sentiment,
            "sentiment_score": self.sentiment_score,
            "tickers_mentioned": self.tickers_mentioned,
            "url": self.url,
        }


@dataclass
class WhaleTransaction:
    """Large transaction by whale"""
    tx_id: str
    ticker: str
    transaction_type: str  # buy, sell, option_exercise
    shares: int
    value: float
    price_per_share: float
    whale_name: str
    whale_type: str  # institution, insider, fund
    date: str
    form_type: Optional[str] = None  # Form 4, 13F, etc.

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tx_id": self.tx_id,
            "ticker": self.ticker,
            "transaction_type": self.transaction_type,
            "shares": self.shares,
            "value": self.value,
            "price_per_share": self.price_per_share,
            "whale_name": self.whale_name,
            "whale_type": self.whale_type,
            "date": self.date,
            "form_type": self.form_type,
        }


# Mock Reddit posts
MOCK_POSTS = [
    RedditPost(
        "r001", "wallstreetbets", "NVDA to the moon! 🚀",
        "Just loaded up on NVDA calls. AI is the future and Jensen is leading the way.",
        "diamond_hands_42", 1523, 287, "2024-08-16T14:30:00Z",
        "bullish", 0.85, ["NVDA"]
    ),
    RedditPost(
        "r002", "stocks", "Is AAPL fairly valued at these levels?",
        "Looking at the fundamentals, AAPL seems expensive. P/E is high but growth is slowing.",
        "value_investor", 342, 156, "2024-08-16T12:15:00Z",
        "neutral", 0.45, ["AAPL"]
    ),
    RedditPost(
        "r003", "investing", "TSLA deliveries disappoint - time to sell?",
        "Q3 deliveries came in below expectations. Competition heating up in EV market.",
        "bearish_bob", 876, 423, "2024-08-15T18:00:00Z",
        "bearish", 0.25, ["TSLA"]
    ),
    RedditPost(
        "r004", "wallstreetbets", "AMD calls printing! Semis on fire 🔥",
        "AMD crushing it with new GPU lineup. Lisa Su never misses. Bought more calls.",
        "yolo_trader", 2341, 512, "2024-08-15T16:45:00Z",
        "bullish", 0.92, ["AMD", "NVDA"]
    ),
    RedditPost(
        "r005", "stocks", "META undervalued compared to peers",
        "META trades at discount to GOOGL despite better growth. Reality Labs losses priced in.",
        "tech_analyst", 567, 198, "2024-08-15T10:30:00Z",
        "bullish", 0.72, ["META", "GOOGL"]
    ),
]

# Mock whale transactions
MOCK_WHALE_TXS = [
    WhaleTransaction(
        "W001", "NVDA", "buy", 500000, 62500000, 125.00,
        "Vanguard Group", "institution", "2024-08-15", "13F"
    ),
    WhaleTransaction(
        "W002", "AAPL", "sell", 200000, 35600000, 178.00,
        "Warren Buffett", "fund", "2024-08-14", "13F"
    ),
    WhaleTransaction(
        "W003", "TSLA", "buy", 100000, 24530000, 245.30,
        "Cathie Wood", "fund", "2024-08-14", "Form 4"
    ),
    WhaleTransaction(
        "W004", "MSFT", "option_exercise", 50000, 21000000, 420.00,
        "Satya Nadella", "insider", "2024-08-13", "Form 4"
    ),
    WhaleTransaction(
        "W005", "GOOGL", "buy", 300000, 52590000, 175.30,
        "BlackRock", "institution", "2024-08-13", "13F"
    ),
    WhaleTransaction(
        "W006", "AMZN", "sell", 150000, 27750000, 185.00,
        "Jeff Bezos", "insider", "2024-08-12", "Form 4"
    ),
]


def get_reddit_sentiment(
    ticker: Optional[str] = None,
    subreddit: Optional[str] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """Get Reddit sentiment for ticker or subreddit"""
    posts = MOCK_POSTS.copy()

    if ticker:
        posts = [p for p in posts if ticker.upper() in p.tickers_mentioned]
    if subreddit:
        posts = [p for p in posts if p.subreddit == subreddit]

    posts = posts[:limit]

    # Calculate aggregate sentiment
    if posts:
        avg_sentiment = sum(p.sentiment_score for p in posts) / len(posts)
        bullish_count = sum(1 for p in posts if p.sentiment == "bullish")
        bearish_count = sum(1 for p in posts if p.sentiment == "bearish")
    else:
        avg_sentiment = 0.5
        bullish_count = 0
        bearish_count = 0

    return {
        "posts": [p.to_dict() for p in posts],
        "count": len(posts),
        "sentiment_summary": {
            "average_score": round(avg_sentiment, 2),
            "signal": "bullish" if avg_sentiment > 0.6 else "bearish" if avg_sentiment < 0.4 else "neutral",
            "bullish_posts": bullish_count,
            "bearish_posts": bearish_count,
            "neutral_posts": len(posts) - bullish_count - bearish_count,
        },
    }


def get_reddit_trending(limit: int = 10) -> Dict[str, Any]:
    """Get trending tickers on Reddit"""
    trending = [
        {"ticker": "NVDA", "mentions": 1523, "sentiment": "bullish", "change_24h": 45},
        {"ticker": "TSLA", "mentions": 987, "sentiment": "bearish", "change_24h": -12},
        {"ticker": "AMD", "mentions": 756, "sentiment": "bullish", "change_24h": 89},
        {"ticker": "AAPL", "mentions": 654, "sentiment": "neutral", "change_24h": 5},
        {"ticker": "GME", "mentions": 543, "sentiment": "bullish", "change_24h": 234},
        {"ticker": "META", "mentions": 432, "sentiment": "bullish", "change_24h": 28},
        {"ticker": "GOOGL", "mentions": 321, "sentiment": "neutral", "change_24h": -8},
        {"ticker": "AMZN", "mentions": 298, "sentiment": "neutral", "change_24h": 15},
        {"ticker": "MSFT", "mentions": 276, "sentiment": "bullish", "change_24h": 12},
        {"ticker": "SPY", "mentions": 254, "sentiment": "neutral", "change_24h": -3},
    ]

    return {
        "trending": trending[:limit],
        "updated_at": datetime.now().isoformat() + "Z",
        "total_posts_analyzed": 15234,
    }


def get_subreddit_activity(subreddit: str) -> Dict[str, Any]:
    """Get activity metrics for a subreddit"""
    metrics = {
        "wallstreetbets": {
            "subscribers": 15200000,
            "active_users": 45230,
            "posts_24h": 1234,
            "comments_24h": 89543,
            "sentiment": "bullish",
            "top_tickers": ["NVDA", "AMD", "TSLA", "GME", "SPY"],
        },
        "stocks": {
            "subscribers": 5800000,
            "active_users": 12340,
            "posts_24h": 567,
            "comments_24h": 23456,
            "sentiment": "neutral",
            "top_tickers": ["AAPL", "MSFT", "GOOGL", "AMZN", "META"],
        },
        "investing": {
            "subscribers": 2300000,
            "active_users": 5670,
            "posts_24h": 234,
            "comments_24h": 8765,
            "sentiment": "neutral",
            "top_tickers": ["VTI", "VOO", "SCHD", "AAPL", "BRK.B"],
        },
    }

    data = metrics.get(subreddit, {
        "subscribers": 100000,
        "active_users": 1000,
        "posts_24h": 50,
        "comments_24h": 500,
        "sentiment": "neutral",
        "top_tickers": [],
    })

    return {
        "subreddit": subreddit,
        **data,
    }


def get_sentiment_history(
    ticker: str,
    days: int = 30,
) -> Dict[str, Any]:
    """Get sentiment history over time"""
    history = []
    base_date = datetime.now() - timedelta(days=days)

    for i in range(days):
        date = base_date + timedelta(days=i)
        # Generate varying sentiment
        sentiment = 0.5 + random.uniform(-0.3, 0.3)
        mentions = random.randint(50, 500)

        history.append({
            "date": date.strftime("%Y-%m-%d"),
            "sentiment_score": round(sentiment, 2),
            "mentions": mentions,
            "posts": random.randint(10, 100),
        })

    return {
        "ticker": ticker.upper(),
        "history": history,
        "trend": "improving" if history[-1]["sentiment_score"] > history[0]["sentiment_score"] else "declining",
    }


def get_whale_transactions(
    ticker: Optional[str] = None,
    whale_type: Optional[str] = None,
    transaction_type: Optional[str] = None,
    min_value: float = 0,
    limit: int = 20,
) -> Dict[str, Any]:
    """Get whale transactions with filters"""
    txs = MOCK_WHALE_TXS.copy()

    if ticker:
        txs = [t for t in txs if t.ticker == ticker.upper()]
    if whale_type:
        txs = [t for t in txs if t.whale_type == whale_type]
    if transaction_type:
        txs = [t for t in txs if t.transaction_type == transaction_type]
    if min_value > 0:
        txs = [t for t in txs if t.value >= min_value]

    txs = txs[:limit]

    # Calculate totals
    total_buy_value = sum(t.value for t in txs if t.transaction_type == "buy")
    total_sell_value = sum(t.value for t in txs if t.transaction_type == "sell")

    return {
        "transactions": [t.to_dict() for t in txs],
        "count": len(txs),
        "summary": {
            "total_buy_value": total_buy_value,
            "total_sell_value": total_sell_value,
            "net_flow": total_buy_value - total_sell_value,
            "signal": "bullish" if total_buy_value > total_sell_value else "bearish",
        },
    }


def get_whale_flow(ticker: str, days: int = 30) -> Dict[str, Any]:
    """Get whale money flow over time"""
    history = []
    base_date = datetime.now() - timedelta(days=days)

    cumulative_flow = 0
    for i in range(days):
        date = base_date + timedelta(days=i)
        # Random daily flow
        daily_buy = random.randint(0, 50000000)
        daily_sell = random.randint(0, 40000000)
        daily_flow = daily_buy - daily_sell
        cumulative_flow += daily_flow

        history.append({
            "date": date.strftime("%Y-%m-%d"),
            "buy_volume": daily_buy,
            "sell_volume": daily_sell,
            "net_flow": daily_flow,
            "cumulative_flow": cumulative_flow,
        })

    return {
        "ticker": ticker.upper(),
        "history": history,
        "total_net_flow": cumulative_flow,
        "signal": "accumulation" if cumulative_flow > 0 else "distribution",
    }


def get_top_whales(
    ticker: Optional[str] = None,
    whale_type: Optional[str] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Get top whales by transaction volume"""
    whales = [
        {
            "name": "Vanguard Group",
            "type": "institution",
            "total_value": 2500000000,
            "holdings": 15,
            "recent_activity": "buying",
        },
        {
            "name": "BlackRock",
            "type": "institution",
            "total_value": 2100000000,
            "holdings": 18,
            "recent_activity": "buying",
        },
        {
            "name": "Cathie Wood",
            "type": "fund",
            "total_value": 450000000,
            "holdings": 8,
            "recent_activity": "mixed",
        },
        {
            "name": "Warren Buffett",
            "type": "fund",
            "total_value": 380000000,
            "holdings": 5,
            "recent_activity": "selling",
        },
        {
            "name": "State Street",
            "type": "institution",
            "total_value": 1800000000,
            "holdings": 20,
            "recent_activity": "holding",
        },
    ]

    if whale_type:
        whales = [w for w in whales if w["type"] == whale_type]

    return whales[:limit]


def get_institutional_ownership(ticker: str) -> Dict[str, Any]:
    """Get institutional ownership breakdown"""
    return {
        "ticker": ticker.upper(),
        "total_institutional": 78.5,
        "top_holders": [
            {"name": "Vanguard Group", "shares": 150000000, "percent": 8.2, "change": 500000},
            {"name": "BlackRock", "shares": 130000000, "percent": 7.1, "change": -200000},
            {"name": "State Street", "shares": 85000000, "percent": 4.6, "change": 100000},
            {"name": "Fidelity", "shares": 72000000, "percent": 3.9, "change": 300000},
            {"name": "Capital Group", "shares": 65000000, "percent": 3.5, "change": -150000},
        ],
        "ownership_trend": "increasing",
        "qoq_change": 1.2,
    }


def get_insider_sentiment(ticker: str, days: int = 90) -> Dict[str, Any]:
    """Get insider buying/selling sentiment"""
    buys = random.randint(5, 20)
    sells = random.randint(3, 15)

    return {
        "ticker": ticker.upper(),
        "period_days": days,
        "insider_buys": buys,
        "insider_sells": sells,
        "buy_value": random.randint(1000000, 10000000),
        "sell_value": random.randint(500000, 8000000),
        "net_sentiment": "bullish" if buys > sells else "bearish" if sells > buys else "neutral",
        "notable_transactions": [
            {
                "name": "CEO",
                "type": "buy",
                "shares": 10000,
                "value": 1250000,
                "date": "2024-08-10",
            },
            {
                "name": "CFO",
                "type": "sell",
                "shares": 5000,
                "value": 625000,
                "date": "2024-08-05",
            },
        ],
    }


def get_social_momentum(ticker: str) -> Dict[str, Any]:
    """Get combined social momentum score"""
    reddit_score = random.uniform(30, 90)
    twitter_score = random.uniform(30, 90)
    stocktwits_score = random.uniform(30, 90)

    overall = (reddit_score + twitter_score + stocktwits_score) / 3

    return {
        "ticker": ticker.upper(),
        "overall_score": round(overall, 1),
        "reddit": {
            "score": round(reddit_score, 1),
            "mentions_24h": random.randint(100, 1000),
            "sentiment": "bullish" if reddit_score > 60 else "bearish" if reddit_score < 40 else "neutral",
        },
        "twitter": {
            "score": round(twitter_score, 1),
            "mentions_24h": random.randint(500, 5000),
            "sentiment": "bullish" if twitter_score > 60 else "bearish" if twitter_score < 40 else "neutral",
        },
        "stocktwits": {
            "score": round(stocktwits_score, 1),
            "mentions_24h": random.randint(50, 500),
            "sentiment": "bullish" if stocktwits_score > 60 else "bearish" if stocktwits_score < 40 else "neutral",
        },
        "momentum_trend": "accelerating" if overall > 70 else "decelerating" if overall < 40 else "stable",
    }
