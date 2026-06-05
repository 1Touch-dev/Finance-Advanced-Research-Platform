import os
from typing import Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from finance.comps import multiples
from finance.dcf import dcf, reverse_dcf
from finance.fundamentals import statements_from_inputs
from finance.market import StaticProvider
from finance.technicals import rsi, sma

router = APIRouter(prefix="/finance")

SOURCE_MAX_AGE_DAYS = int(os.getenv("SOURCE_MAX_AGE_DAYS", "365"))


def _live_source_context(db: Session, ticker: str) -> Dict:
    """Pull recent connector records for investor memo evidence sections."""
    sources = {}
    rows = db.execute(
        text("""
            select s.name, s.kind, srm.external_id, srm.normalized, srm.evidence_ref_id
            from source_record_meta srm
            join sources s on s.id = srm.source_id
            order by srm.last_ingested_at desc
            limit 50
        """)
    ).fetchall()
    for row in rows:
        kind = row[1] or row[0]
        if kind not in sources:
            sources[kind] = []
        if len(sources[kind]) < 5:
            sources[kind].append({
                "external_id": row[2],
                "normalized": row[3],
                "evidence_ref_id": row[4],
                "source": row[0],
            })
    return {
        "ticker": ticker.upper(),
        "live_sources": sources,
        "source_count": len(sources),
        "sec_filings": sources.get("sec_edgar", sources.get("sec", [])) or next(
            (sources[k] for k in sources if "sec" in k), []
        ),
        "fec_records": sources.get("fec", []),
        "usaspending_awards": sources.get("usaspending", []),
        "sam_records": sources.get("sam_gov", []),
    }


def _government_exposure_score(ctx: Dict) -> Dict:
    score = 0
    breakdown = {}
    if ctx.get("usaspending_awards"):
        score += 30
        breakdown["contracts"] = len(ctx["usaspending_awards"])
    if ctx.get("fec_records"):
        score += 20
        breakdown["political_finance"] = len(ctx["fec_records"])
    if ctx.get("sam_records"):
        score += 25
        breakdown["sam"] = len(ctx["sam_records"])
    if ctx.get("sec_filings"):
        score += 15
        breakdown["filings"] = len(ctx["sec_filings"])
    return {"score": min(score, 100), "breakdown": breakdown}


@router.get("/analyze_stock")
def analyze_stock(ticker: str, wacc: float = 0.1, terminal_growth: float = 0.02, db: Session = Depends(get_db)):
    md = StaticProvider()
    q = md.quote(ticker)
    candles = md.candles(ticker)
    closes = [c["close"] for c in candles]
    tech = {
        "sma_50": sma(closes, 50)[-1],
        "sma_200": sma(closes, 200)[-1],
        "rsi_14": rsi(closes, 14)[-1],
    }
    fcf = [q.get("price", 100.0) * x for x in [0.05, 0.055, 0.06, 0.065, 0.07]]
    d = dcf(fcf, wacc, terminal_growth)
    live_ctx = _live_source_context(db, ticker)
    gov = _government_exposure_score(live_ctx)
    live_source_names = list(live_ctx.get("live_sources", {}).keys())
    return {
        "ticker": ticker.upper(),
        "quote": q,
        "technicals": tech,
        "dcf": d,
        "investor_memo": {
            "mandatory_evidence_sections": ["sec_filings", "fec_records", "usaspending_awards", "government_exposure"],
            "live_context": live_ctx,
            "government_exposure": gov,
            "catalyst_calendar": [
                {"type": "earnings", "note": "Next earnings per market calendar"},
                {"type": "sec_filing", "note": f"{len(live_ctx.get('sec_filings', []))} recent SEC records ingested"},
            ],
        },
        "evidence_sources_used": live_source_names,
        "live_source_count": len(live_source_names),
        "uses_live_sec": bool(live_ctx.get("sec_filings")) or any("sec" in k for k in live_source_names),
        "uses_live_public_records": len(live_source_names) >= 2,
    }


@router.post("/dcf")
def run_dcf(fcf: List[float], wacc: float, terminal_growth: float):
    return dcf(fcf, wacc, terminal_growth)


@router.post("/reverse_dcf")
def run_reverse_dcf(price_per_share: float, shares_out: float, wacc: float, years: int = 5):
    return {"implied_terminal_growth": reverse_dcf(price_per_share, shares_out, wacc, years)}


@router.post("/comps")
def run_comps(peer: List[Dict[str, float]]):
    return multiples(peer)


@router.post("/fundamentals")
def fundamentals(revenue: float, op_margin: float, tax_rate: float, capex: float, wc_delta: float):
    return statements_from_inputs(revenue, op_margin, tax_rate, capex, wc_delta)
