"""
Multi-Agent Financial Intelligence Engine — Phase 5th-July
===========================================================
Inspired by: TradingAgents, ai-hedge-fund, FinRobot patterns

Four specialist agents work in parallel, then a synthesis agent produces
a final investment intelligence report.

Agents:
  1. FundamentalsAgent  — income/balance/cash flow + financial health scores
  2. TechnicalAgent     — trend, momentum, volatility, support/resistance
  3. SentimentAgent     — RSS news + analyst sentiment + social signals
  4. RiskAgent          — Beneish M-score, Altman Z-score, debt metrics, beta
  5. SynthesisAgent     — combines all into final thesis + recommendation

Each agent returns a structured dict with:
  - analysis: dict of raw data/metrics
  - narrative: 1-3 sentence plain-English summary
  - score: 0–100 (higher = more bullish / healthier)
  - signals: list of key findings

No LLM required for structured output — LLM can be used for narrative
generation if OPENAI_API_KEY is present (gracefully degrades to rule-based).
"""

import os
import logging
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

log = logging.getLogger(__name__)

_OPENAI_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _safe(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        log.warning("Agent call error %s: %s", fn.__name__, e)
        return None


def _llm_narrative(system_prompt: str, user_content: str) -> Optional[str]:
    """Generate a narrative using OpenAI if key available, else return None."""
    if not _OPENAI_KEY:
        return None
    try:
        import openai
        client = openai.OpenAI(api_key=_OPENAI_KEY)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_content[:3000]},
            ],
            max_tokens=300,
            temperature=0.3,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        log.warning("LLM narrative error: %s", e)
        return None


# ─── Agent 1: Fundamentals ───────────────────────────────────────────────────

def fundamentals_agent(ticker: str) -> dict:
    """Analyze financial statements + yfinance fundamentals."""
    from app.connectors.yfinance_connector import yf_fundamentals, yf_company_info
    from app.connectors.financial_news_connector import (
        fmp_income_statement, fmp_key_metrics
    )

    fund = _safe(yf_fundamentals, ticker) or {}
    info = _safe(yf_company_info, ticker) or {}
    income = _safe(fmp_income_statement, ticker, 5) or []
    metrics = _safe(fmp_key_metrics, ticker) or {}

    pe   = fund.get("trailingPE")
    pb   = fund.get("priceToBook")
    ps   = fund.get("priceToSalesTrailing12Months")
    ev_e = fund.get("enterpriseToEbitda")
    margins = {
        "gross":     fund.get("grossMargins"),
        "operating": fund.get("operatingMargins"),
        "net":       fund.get("profitMargins"),
    }
    roe = fund.get("returnOnEquity")
    roa = fund.get("returnOnAssets")

    # Revenue trend
    rev_trend = [r.get("revenue") for r in income if r.get("revenue")]

    signals = []
    score = 50

    if pe:
        if pe < 15:
            signals.append(f"Low P/E ({pe:.1f}) — potentially undervalued")
            score += 8
        elif pe > 40:
            signals.append(f"High P/E ({pe:.1f}) — growth premium or overvalued")
            score -= 5
    if margins.get("net") and margins["net"] > 0.15:
        signals.append(f"Strong net margin ({margins['net']*100:.1f}%)")
        score += 7
    if roe and roe > 0.15:
        signals.append(f"Excellent ROE ({roe*100:.1f}%)")
        score += 8
    if len(rev_trend) >= 2 and rev_trend[0] and rev_trend[-1] and rev_trend[0] > rev_trend[-1]:
        signals.append("Revenue growing YoY")
        score += 6

    narrative = _llm_narrative(
        "You are a fundamental analyst. In 2 sentences, assess this company's fundamentals.",
        f"{info.get('name', ticker)} - PE:{pe} PB:{pb} NetMargin:{margins.get('net')} ROE:{roe} Sector:{info.get('sector')}"
    ) or _rule_fundamentals_narrative(ticker, pe, margins, roe, score)

    return {
        "agent": "FundamentalsAgent",
        "score": min(max(score, 0), 100),
        "analysis": {"pe": pe, "pb": pb, "ev_ebitda": ev_e, "margins": margins, "roe": roe, "roa": roa},
        "signals": signals,
        "narrative": narrative,
    }


def _rule_fundamentals_narrative(ticker, pe, margins, roe, score) -> str:
    parts = []
    if pe:
        parts.append(f"P/E of {pe:.1f} suggests {'attractive' if pe < 20 else 'premium'} valuation.")
    if margins.get("net"):
        m = margins["net"] * 100
        parts.append(f"Net margin of {m:.1f}% is {'strong' if m > 15 else 'modest'}.")
    if roe:
        parts.append(f"ROE of {roe*100:.1f}% indicates {'excellent' if roe > 0.15 else 'adequate'} capital efficiency.")
    return " ".join(parts) or f"{ticker} fundamentals analysis complete."


# ─── Agent 2: Technical ──────────────────────────────────────────────────────

def technical_agent(ticker: str) -> dict:
    """Analyze price action, trend, momentum, and volatility."""
    from app.connectors.technicals_connector import compute_technicals

    data = _safe(compute_technicals, ticker, "1y") or {}
    if data.get("error"):
        return {"agent": "TechnicalAgent", "score": 50, "analysis": {}, "signals": [], "narrative": "Insufficient price data."}

    summ = data.get("summary", {})
    price   = summ.get("current_price")
    sma50   = summ.get("sma_50")
    sma200  = summ.get("sma_200")
    rsi     = summ.get("rsi")
    macd_h  = summ.get("macd_histogram")
    support = summ.get("support")
    resist  = summ.get("resistance")
    signals_raw = summ.get("signals", [])

    signals = [s["label"] for s in signals_raw]
    score = 50

    # Trend
    if price and sma50 and price > sma50:
        signals.append("Price above 50-day SMA (uptrend)")
        score += 8
    elif price and sma50 and price < sma50:
        signals.append("Price below 50-day SMA (downtrend)")
        score -= 8

    if sma50 and sma200 and sma50 > sma200:
        signals.append("50-SMA above 200-SMA (bullish structure)")
        score += 7
    elif sma50 and sma200 and sma50 < sma200:
        signals.append("50-SMA below 200-SMA (bearish structure)")
        score -= 7

    # RSI
    if rsi:
        if rsi > 70:
            signals.append(f"RSI overbought ({rsi:.1f})")
            score -= 5
        elif rsi < 30:
            signals.append(f"RSI oversold ({rsi:.1f})")
            score += 5

    # MACD
    if macd_h and macd_h > 0:
        signals.append("MACD histogram positive (bullish momentum)")
        score += 5
    elif macd_h and macd_h < 0:
        signals.append("MACD histogram negative (bearish momentum)")
        score -= 5

    # Support proximity
    if price and support and abs(price - support) / price < 0.03:
        signals.append(f"Near support level ({support:.2f})")

    trend = "uptrend" if score > 55 else ("downtrend" if score < 45 else "sideways")
    sma50_str = f"{sma50:.2f}" if sma50 is not None else "N/A"
    narrative = (
        f"Price is in a {trend} at {price:.2f}, "
        f"{'above' if price and sma50 and price > sma50 else 'below'} its 50-day SMA ({sma50_str}). "
        f"RSI at {rsi:.1f} indicates {'overbought conditions' if rsi and rsi > 70 else 'oversold conditions' if rsi and rsi < 30 else 'neutral momentum'}. "
        f"Key support at {support:.2f}, resistance at {resist:.2f}."
    ) if price and sma50 and rsi else f"{ticker} technical analysis complete."

    return {
        "agent": "TechnicalAgent",
        "score": min(max(score, 0), 100),
        "analysis": {"price": price, "sma50": sma50, "sma200": sma200, "rsi": rsi, "macd_histogram": macd_h, "support": support, "resistance": resist},
        "signals": signals,
        "narrative": narrative,
    }


# ─── Agent 3: Sentiment ──────────────────────────────────────────────────────

def sentiment_agent(ticker: str, company_name: str = "") -> dict:
    """Analyze news sentiment from RSS articles + traditional news APIs."""
    from app.connectors.financial_news_connector import aggregate_news
    import os
    from sqlalchemy import create_engine, text as sqlt

    query = company_name or ticker

    # Get articles from traditional APIs
    news_data = _safe(aggregate_news, query, 15) or {}
    api_articles = news_data.get("articles", []) if isinstance(news_data, dict) else []

    # Also get articles from RSS DB (entity-matched)
    rss_articles = []
    bare_name = (company_name or ticker).split()[0]  # e.g. "Apple" from "Apple Inc."
    try:
        db_url = os.getenv("DATABASE_URL", "postgresql+psycopg://user:password@127.0.0.1:5433/mydb")
        engine = create_engine(db_url)
        with engine.connect() as conn:
            rows = conn.execute(sqlt("""
                SELECT title, summary FROM rss_articles
                WHERE :entity = ANY(matched_entities)
                ORDER BY published_at DESC NULLS LAST LIMIT 20
            """), {"entity": bare_name}).fetchall()
            rss_articles = [{"title": r.title, "summary": r.summary or ""} for r in rows]
    except Exception as e:
        log.debug("RSS sentiment lookup error: %s", e)

    all_articles = api_articles + rss_articles

    # Simple keyword-based sentiment scoring
    BULLISH_WORDS = {"surge", "jump", "gain", "rally", "beat", "record", "growth", "profit", "strong", "upgrade", "buy", "bullish", "positive", "rise", "soar", "boost", "outperform", "exceed", "better"}
    BEARISH_WORDS = {"drop", "fall", "decline", "loss", "miss", "cut", "downgrade", "sell", "bearish", "negative", "concern", "risk", "warn", "crash", "plunge", "debt", "weak", "disappoint", "underperform", "worse"}

    bullish_count = 0
    bearish_count = 0
    neutral_count = 0

    for art in all_articles:
        title = (art.get("title") or "").lower()
        words = set(title.split())
        b = len(words & BULLISH_WORDS)
        br = len(words & BEARISH_WORDS)
        if b > br:
            bullish_count += 1
        elif br > b:
            bearish_count += 1
        else:
            neutral_count += 1

    total = max(bullish_count + bearish_count + neutral_count, 1)
    sentiment_ratio = (bullish_count - bearish_count) / total
    score = int(50 + sentiment_ratio * 30)

    signals = []
    if bullish_count > bearish_count:
        signals.append(f"News sentiment predominantly bullish ({bullish_count}/{total} articles)")
    elif bearish_count > bullish_count:
        signals.append(f"News sentiment predominantly bearish ({bearish_count}/{total} articles)")
    else:
        signals.append(f"News sentiment mixed/neutral ({total} articles analyzed)")

    narrative = (
        f"Analyzed {total} articles (API + RSS). "
        f"{bullish_count} bullish-leaning, {bearish_count} bearish-leaning. "
        f"Overall sentiment is {'positive' if sentiment_ratio > 0.1 else 'negative' if sentiment_ratio < -0.1 else 'neutral'}."
    )

    return {
        "agent": "SentimentAgent",
        "score": min(max(score, 0), 100),
        "analysis": {
            "articles_analyzed": total,
            "bullish": bullish_count,
            "bearish": bearish_count,
            "neutral": neutral_count,
            "sentiment_ratio": round(sentiment_ratio, 3),
        },
        "signals": signals,
        "narrative": narrative,
    }


# ─── Agent 4: Risk ───────────────────────────────────────────────────────────

def risk_agent(ticker: str) -> dict:
    """Compute risk metrics: Beneish M-score, Altman Z-score, debt, beta."""
    from app.connectors.financial_news_connector import compute_beneish_mscore, compute_altman_zscore
    from app.connectors.yfinance_connector import yf_fundamentals

    beneish = _safe(compute_beneish_mscore, ticker) or {}
    altman  = _safe(compute_altman_zscore, ticker) or {}
    fund    = _safe(yf_fundamentals, ticker) or {}

    m_score   = beneish.get("mscore")
    z_score   = altman.get("zscore")
    debt_eq   = fund.get("debtToEquity")
    beta      = fund.get("beta")
    short_pct = fund.get("shortPercentOfFloat")

    signals = []
    score = 60  # start with moderate

    if m_score is not None:
        if m_score > -2.22:
            signals.append(f"Beneish M-Score {m_score:.2f} — EARNINGS MANIPULATION FLAG (> -2.22)")
            score -= 25
        else:
            signals.append(f"Beneish M-Score {m_score:.2f} — no manipulation signal")
            score += 5

    if z_score is not None:
        if z_score < 1.81:
            signals.append(f"Altman Z-Score {z_score:.2f} — DISTRESS ZONE (< 1.81)")
            score -= 20
        elif z_score < 2.99:
            signals.append(f"Altman Z-Score {z_score:.2f} — grey zone")
        else:
            signals.append(f"Altman Z-Score {z_score:.2f} — safe zone (> 2.99)")
            score += 10

    if debt_eq:
        if debt_eq > 200:
            signals.append(f"High debt/equity ratio ({debt_eq:.0f}%)")
            score -= 10
        elif debt_eq < 50:
            signals.append(f"Low debt/equity ({debt_eq:.0f}%) — conservative leverage")
            score += 5

    if beta:
        if beta > 1.5:
            signals.append(f"High beta ({beta:.2f}) — volatile, high market risk")
        elif beta < 0.5:
            signals.append(f"Low beta ({beta:.2f}) — defensive, low market correlation")

    if short_pct and short_pct > 0.15:
        signals.append(f"High short interest ({short_pct*100:.1f}% of float)")
        score -= 8

    narrative = (
        f"Risk assessment: M-Score {f'{m_score:.2f}' if m_score is not None else 'N/A'} "
        f"({'flags manipulation' if m_score is not None and m_score > -2.22 else 'clean'}), "
        f"Z-Score {f'{z_score:.2f}' if z_score is not None else 'N/A'} "
        f"({'distress' if z_score is not None and z_score < 1.81 else 'safe'}). "
        f"Beta of {f'{beta:.2f}' if beta is not None else 'N/A'} with D/E ratio of {f'{debt_eq:.0f}' if debt_eq is not None else 'N/A'}%."
    )

    return {
        "agent": "RiskAgent",
        "score": min(max(score, 0), 100),
        "analysis": {
            "beneish_mscore": m_score,
            "altman_zscore":  z_score,
            "debt_to_equity": debt_eq,
            "beta":           beta,
            "short_interest": short_pct,
        },
        "signals": signals,
        "narrative": narrative,
    }


# ─── Synthesis Agent ─────────────────────────────────────────────────────────

def synthesis_agent(ticker: str, agent_results: dict) -> dict:
    """Combine all agent outputs into a final investment thesis."""
    fund_r  = agent_results.get("fundamentals", {})
    tech_r  = agent_results.get("technical", {})
    sent_r  = agent_results.get("sentiment", {})
    risk_r  = agent_results.get("risk", {})

    scores = {k: v.get("score", 50) for k, v in {
        "fundamentals": fund_r,
        "technical":    tech_r,
        "sentiment":    sent_r,
        "risk":         risk_r,
    }.items() if v}

    composite = sum(scores.values()) / len(scores) if scores else 50

    # Recommendation thresholds
    if composite >= 70:
        recommendation = "BUY"
        conviction = "HIGH" if composite >= 80 else "MEDIUM"
    elif composite >= 55:
        recommendation = "HOLD"
        conviction = "MEDIUM"
    elif composite >= 40:
        recommendation = "HOLD/REDUCE"
        conviction = "LOW"
    else:
        recommendation = "SELL"
        conviction = "HIGH" if composite <= 30 else "MEDIUM"

    all_signals = []
    for agent in [fund_r, tech_r, sent_r, risk_r]:
        all_signals.extend(agent.get("signals", []))

    # LLM synthesis narrative if available
    agent_summaries = "\n".join([
        f"Fundamentals: {fund_r.get('narrative', '')}",
        f"Technical: {tech_r.get('narrative', '')}",
        f"Sentiment: {sent_r.get('narrative', '')}",
        f"Risk: {risk_r.get('narrative', '')}",
    ])
    llm_thesis = _llm_narrative(
        "You are a hedge fund portfolio manager. Synthesize this multi-agent analysis into a 3-sentence investment thesis with a clear recommendation (BUY/HOLD/SELL) and key conviction drivers.",
        f"Ticker: {ticker}\nComposite score: {composite:.1f}/100\n{agent_summaries}"
    )

    rule_thesis = (
        f"Multi-agent composite score: {composite:.1f}/100 → {recommendation} ({conviction} conviction). "
        f"Key drivers: {'; '.join(all_signals[:3]) if all_signals else 'see individual agent reports'}."
    )

    return {
        "ticker":         ticker,
        "composite_score": round(composite, 1),
        "recommendation": recommendation,
        "conviction":     conviction,
        "scores":         scores,
        "top_signals":    all_signals[:8],
        "thesis":         llm_thesis or rule_thesis,
        "agent_results":  agent_results,
    }


# ─── Main Entry — run all agents ─────────────────────────────────────────────

def run_investment_intelligence(ticker: str, company_name: str = "") -> dict:
    """
    Run all 4 specialist agents in parallel, then synthesize.
    Returns full multi-agent intelligence report.
    """
    tasks = {
        "fundamentals": (fundamentals_agent, [ticker]),
        "technical":    (technical_agent,    [ticker]),
        "sentiment":    (sentiment_agent,    [ticker, company_name]),
        "risk":         (risk_agent,         [ticker]),
    }

    results = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(fn, *args): name for name, (fn, args) in tasks.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result(timeout=30)
            except Exception as e:
                log.warning("Agent %s failed: %s", name, e)
                results[name] = {"agent": name, "score": 50, "signals": [], "narrative": f"Agent unavailable: {e}"}

    return synthesis_agent(ticker, results)
