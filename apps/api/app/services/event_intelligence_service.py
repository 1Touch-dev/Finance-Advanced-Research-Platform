"""
Event intelligence enrichment — F-08 RSS Phase 2, steps 2-4
(§4.2 fact extraction, §4.3 contradiction detection, §4.4 perspective labeling).

Orchestrates, per clustered event (app.connectors.event_clustering):
  1. Full-text fetch per article via Crawl4AI (falls back to the RSS summary
     alone if Crawl4AI is unavailable or the fetch fails/times out — an RSS
     summary is thinner but still workable, per the design doc's degrade
     posture).
  2. GPT-4o structured extraction: confirmed facts, unconfirmed claims, key
     quotes, per source.
  3. GPT-4o cross-source comparison: contradictions between claims when 2+
     sources cover the same event.
  4. GPT-4o per-article framing/perspective label.

Single-source events skip steps 2-4's cross-source pieces (nothing to
contradict or compare) but still get fact extraction — see
`enrich_event_candidate()`.

Every step is wrapped so a failure anywhere (OpenAI down, bad JSON, Crawl4AI
timeout) degrades to a partial result rather than raising — this must never
take down the existing /market/rss/* endpoints or the RSS poller.
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

_TIMEOUT = 45
_MODEL = "gpt-4o-mini"  # same cost-conscious model already used in intelligence_service.py


def _openai_key() -> str:
    return os.getenv("OPENAI_API_KEY", "")


def _chat_json(system: str, user: str, max_tokens: int = 900) -> Optional[Dict[str, Any]]:
    """One GPT-4o-mini call, asked to return strict JSON. Returns None on any
    failure (no key, HTTP error, unparseable JSON) rather than raising."""
    api_key = _openai_key()
    if not api_key:
        return None
    try:
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": _MODEL,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.1,
                "max_tokens": max_tokens,
                "response_format": {"type": "json_object"},
            },
            timeout=_TIMEOUT,
        )
        if not resp.ok:
            logger.info("event enrichment: OpenAI call failed %s: %s", resp.status_code, resp.text[:200])
            return None
        content = resp.json()["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception as e:
        logger.info("event enrichment: OpenAI call error: %s", e)
        return None


# ── Full-text fetch (Crawl4AI, §5 of the design doc) ──────────────────────────

def _full_text_for(article: Dict[str, Any], max_chars: int = 3000) -> str:
    """Best-effort full article text. Falls back to the RSS summary (already
    on the article dict) if Crawl4AI is unavailable/fails/times out — this
    function never raises."""
    url = article.get("url")
    summary = (article.get("summary") or "")[:max_chars]
    if not url:
        return summary
    try:
        from app.connectors.crawl4ai_connector import crawl_url
        markdown = crawl_url(url)
        if markdown:
            return markdown[:max_chars]
    except Exception as e:
        logger.debug("event enrichment: crawl_url fallback to summary for %s (%s)", url, e)
    return summary


# ── Step 2: Fact extraction (§4.2) ────────────────────────────────────────────

_FACTS_SYSTEM = (
    "You are a financial news analyst extracting discrete factual claims from "
    "articles for a research platform. Be precise, conservative, and cite the "
    "source name for every claim. Only extract what the text actually states — "
    "never infer or add outside knowledge. Respond with strict JSON only."
)


def extract_facts(article: Dict[str, Any]) -> Dict[str, Any]:
    """
    Per-article fact extraction. Returns:
        {"facts": [str], "claims": [str], "quotes": [{"quote","attributed_to"}]}
    Empty lists (not an error) if OpenAI is unavailable — callers treat that as
    "nothing extracted" rather than a hard failure.
    """
    source = article.get("source_name", "Unknown")
    text = _full_text_for(article)
    if not text.strip():
        return {"facts": [], "claims": [], "quotes": []}

    user = (
        f"Source: {source}\nHeadline: {article.get('title','')}\n\n"
        f"Article text:\n{text}\n\n"
        "Extract, as JSON with keys \"facts\", \"claims\", \"quotes\":\n"
        "- facts: array of strings — discrete, verifiable statements this article makes "
        "as established fact (numbers, dates, named actions).\n"
        "- claims: array of strings — statements presented as someone's assertion or "
        "opinion rather than a settled fact (allegations, predictions, unconfirmed reports).\n"
        "- quotes: array of {\"quote\": str, \"attributed_to\": str} — direct quotes with speaker.\n"
        "Keep each list to at most 5 items, most important first."
    )
    result = _chat_json(_FACTS_SYSTEM, user)
    if not result:
        return {"facts": [], "claims": [], "quotes": []}
    return {
        "facts": result.get("facts") or [],
        "claims": result.get("claims") or [],
        "quotes": result.get("quotes") or [],
    }


# ── Step 3: Contradiction detection (§4.3) ────────────────────────────────────

_CONTRADICTION_SYSTEM = (
    "You compare factual claims about the same news event from different "
    "sources and flag genuine contradictions — conflicting numbers, dates, "
    "attributions, or outcomes. Do not flag differences in tone or emphasis as "
    "contradictions; only flag them when the sources assert incompatible facts. "
    "Respond with strict JSON only."
)


def detect_contradictions(per_source_facts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    per_source_facts: [{"source": str, "facts": [str], "claims": [str]}, ...]
    Returns: [{"claim_a","source_a","claim_b","source_b","note"}]
    Only meaningful with 2+ sources — callers should skip this for
    single-source events (nothing to compare).
    """
    if len(per_source_facts) < 2:
        return []
    blocks = []
    for row in per_source_facts:
        items = (row.get("facts") or []) + (row.get("claims") or [])
        if not items:
            continue
        blocks.append(f"### {row['source']}\n" + "\n".join(f"- {i}" for i in items[:8]))
    if len(blocks) < 2:
        return []

    user = (
        "Below are factual claims from different sources, all about the same news event.\n\n"
        + "\n\n".join(blocks)
        + "\n\nIdentify genuine contradictions between sources (conflicting numbers, dates, "
        "outcomes, attributions). Respond with JSON: "
        "{\"conflicts\": [{\"claim_a\": str, \"source_a\": str, \"claim_b\": str, "
        "\"source_b\": str, \"note\": str}]}. If there are no real contradictions, "
        "return {\"conflicts\": []}. Do not invent conflicts that aren't there."
    )
    result = _chat_json(_CONTRADICTION_SYSTEM, user, max_tokens=700)
    if not result:
        return []
    return result.get("conflicts") or []


# ── Step 4: Perspective labeling (§4.4) ───────────────────────────────────────

_PERSPECTIVE_SYSTEM = (
    "You label the apparent framing of a single news article — not the outlet "
    "in general, just this article. This is a judgment call about tone and "
    "emphasis, not a factual claim about bias. Respond with strict JSON only."
)


def label_perspective(article: Dict[str, Any]) -> Dict[str, Any]:
    """
    Returns: {"framing": "bullish"|"bearish"|"neutral", "lean": str|None, "notes": str}
    `lean` is a short free-text note (e.g. "reads as market-optimistic", or
    "frames the policy critically") rather than a hard left/right label — see
    design doc §9 risk #3 on overstating certainty from an LLM's judgment call.
    """
    text = _full_text_for(article, max_chars=1500)
    if not text.strip():
        return {"framing": "neutral", "lean": None, "notes": ""}

    user = (
        f"Source: {article.get('source_name','Unknown')}\n"
        f"Headline: {article.get('title','')}\n\n"
        f"Article text:\n{text}\n\n"
        "Respond with JSON: {\"framing\": \"bullish\"|\"bearish\"|\"neutral\", "
        "\"lean\": short phrase describing any apparent political/regional/ideological "
        "framing (or null if none apparent), \"notes\": one-sentence justification}."
    )
    result = _chat_json(_PERSPECTIVE_SYSTEM, user, max_tokens=250)
    if not result:
        return {"framing": "neutral", "lean": None, "notes": ""}
    framing = result.get("framing") if result.get("framing") in ("bullish", "bearish", "neutral") else "neutral"
    return {"framing": framing, "lean": result.get("lean"), "notes": result.get("notes", "")}


# ── Orchestration: one event candidate → full enrichment ─────────────────────

def enrich_event_candidate(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """
    Takes one candidate from event_clustering.build_event_candidates() and
    returns the fields ready to persist onto an RssEvent row. Never raises —
    on any internal failure, returns as much as was computed with
    enrichment_status="failed" and enrichment_error set, so the caller can
    still save a partial row rather than losing the whole event.
    """
    articles = candidate.get("articles") or []
    out: Dict[str, Any] = {
        "headline": candidate.get("headline", ""),
        "topic_entity": candidate.get("topic_entity"),
        "article_ids": candidate.get("article_ids") or [],
        "source_count": candidate.get("source_count", len(articles)),
        "sources": [
            {"source_name": a.get("source_name"), "title": a.get("title"),
             "url": a.get("url"), "published_at": str(a.get("published_at"))}
            for a in articles
        ],
        "confirmed_facts": [],
        "unconfirmed_claims": [],
        "conflicts": [],
        "perspectives": [],
        "key_quotes": [],
        "market_impact": None,
        "enrichment_status": "pending",
        "enrichment_error": None,
    }

    if not articles:
        out["enrichment_status"] = "skipped_single_source"
        return out

    try:
        per_source_facts = []
        for article in articles:
            extracted = extract_facts(article)
            source = article.get("source_name", "Unknown")
            per_source_facts.append({"source": source, **extracted})
            for fact in extracted["facts"]:
                out["confirmed_facts"].append({"fact": fact, "sources": [source]})
            for claim in extracted["claims"]:
                out["unconfirmed_claims"].append({"claim": claim, "source": source})
            for quote in extracted["quotes"]:
                out["key_quotes"].append({**quote, "source": source})

            perspective = label_perspective(article)
            out["perspectives"].append({"source": source, "url": article.get("url"), **perspective})

        if len(articles) > 1:
            out["conflicts"] = detect_contradictions(per_source_facts)
        out["enrichment_status"] = "enriched" if any(
            out[k] for k in ("confirmed_facts", "unconfirmed_claims", "conflicts", "perspectives")
        ) else "failed"
    except Exception as e:
        logger.warning("enrich_event_candidate failed for %r: %s", out.get("headline"), e)
        out["enrichment_status"] = "failed"
        out["enrichment_error"] = str(e)

    return out


# ── Top-level job: cluster + enrich + persist ─────────────────────────────────

def run_event_intelligence_job(db, hours: int = 48, max_events: int = 15,
                                min_sources_for_enrichment: int = 1,
                                categories: Optional[List[str]] = None,
                                regions: Optional[List[str]] = None,
                                us_finance_only: bool = True) -> Dict[str, Any]:
    """
    Full Phase-2 pipeline: fetch recent rss_articles → cluster into events →
    enrich each cluster with facts/contradictions/perspectives → upsert into
    rss_events. Designed to be run from a background task (it can take
    minutes if OpenAI/Crawl4AI are slow) — see api/market.py's job-polling
    endpoints, which follow the exact pattern already used for the tracking
    digest job (apps/api/app/api/tracking.py).

    us_finance_only=True (default) scopes clustering to US-stock-market-
    relevant articles only (finance/macro/government categories, US/global
    sources, plus a stock-keyword content check) — this is a US finance
    research platform, not a general news reader. Set False to widen scope.

    Never raises: any per-event failure is caught and recorded on that row;
    a total failure (e.g. DB unreachable) is caught and returned as a
    dict with "error" rather than propagating, so a bad run can never take
    down the calling background task thread.
    """
    from app.connectors.event_clustering import build_event_candidates
    from app.models.base import Base
    from app.models.news_events import RssEvent

    try:
        Base.metadata.create_all(bind=db.get_bind())
    except Exception as e:
        return {"error": f"could not prepare rss_events table: {e}", "events_created": 0}

    try:
        candidates = build_event_candidates(
            hours=hours, max_events=max_events,
            categories=categories, regions=regions, us_finance_only=us_finance_only,
        )
    except Exception as e:
        return {"error": f"clustering failed: {e}", "events_created": 0}

    if not candidates:
        return {"events_created": 0, "events_updated": 0, "note": "no recent RSS articles to cluster"}

    created, updated, skipped_enrichment = 0, 0, 0
    for candidate in candidates:
        try:
            if candidate.get("source_count", 1) < min_sources_for_enrichment:
                enriched = {
                    "headline": candidate.get("headline", ""),
                    "topic_entity": candidate.get("topic_entity"),
                    "article_ids": candidate.get("article_ids") or [],
                    "source_count": candidate.get("source_count", 1),
                    "sources": [
                        {"source_name": a.get("source_name"), "title": a.get("title"),
                         "url": a.get("url"), "published_at": str(a.get("published_at"))}
                        for a in candidate.get("articles") or []
                    ],
                    "confirmed_facts": [], "unconfirmed_claims": [], "conflicts": [],
                    "perspectives": [], "key_quotes": [], "market_impact": None,
                    "enrichment_status": "skipped_single_source", "enrichment_error": None,
                }
                skipped_enrichment += 1
            else:
                enriched = enrich_event_candidate(candidate)

            existing = None
            new_ids = set(enriched["article_ids"])
            if new_ids:
                # Match by article-id overlap rather than exact headline text:
                # a cluster's "headline" is just its most-recent article's
                # title, so as new articles join the same real-world story
                # across runs, the chosen headline can shift entirely (e.g.
                # once an outlet updates its title) — an exact-text match
                # would then never find the prior row and create a duplicate
                # event for the same story instead of updating it.
                candidate_rows = db.query(RssEvent).filter(
                    RssEvent.updated_at.isnot(None)
                ).order_by(RssEvent.id.desc()).limit(200).all()
                best_overlap = 0
                for row in candidate_rows:
                    row_ids = set(row.article_ids or [])
                    if not row_ids:
                        continue
                    overlap = len(row_ids & new_ids)
                    if overlap > best_overlap and overlap / len(row_ids | new_ids) >= 0.3:
                        best_overlap = overlap
                        existing = row

            if existing:
                for field in ("headline", "article_ids", "sources", "source_count", "confirmed_facts",
                              "unconfirmed_claims", "conflicts", "perspectives", "key_quotes",
                              "market_impact", "enrichment_status", "enrichment_error", "topic_entity"):
                    setattr(existing, field, enriched.get(field))
                updated += 1
            else:
                db.add(RssEvent(**enriched))
                created += 1
            db.commit()
        except Exception as e:
            db.rollback()
            logger.warning("run_event_intelligence_job: failed to persist candidate: %s", e)
            continue

    return {
        "events_created": created,
        "events_updated": updated,
        "events_skipped_enrichment": skipped_enrichment,
        "candidates_seen": len(candidates),
    }
