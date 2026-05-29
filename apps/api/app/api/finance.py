from fastapi import APIRouter
from typing import List, Dict
from finance.market import StaticProvider
from finance.fundamentals import statements_from_inputs
from finance.dcf import dcf, reverse_dcf
from finance.comps import multiples
from finance.technicals import sma, rsi

router = APIRouter(prefix="/finance")

@router.get('/analyze_stock')
def analyze_stock(ticker: str, wacc: float = 0.1, terminal_growth: float = 0.02):
    md = StaticProvider()
    q = md.quote(ticker)
    candles = md.candles(ticker)
    closes = [c["close"] for c in candles]
    tech = {
        "sma_50": sma(closes, 50)[-1],
        "sma_200": sma(closes, 200)[-1],
        "rsi_14": rsi(closes, 14)[-1],
    }
    fcf = [q.get("price",100.0)*x for x in [0.05,0.055,0.06,0.065,0.07]]
    d = dcf(fcf, wacc, terminal_growth)
    return {"ticker": ticker.upper(), "quote": q, "technicals": tech, "dcf": d}

@router.post('/dcf')
def run_dcf(fcf: List[float], wacc: float, terminal_growth: float):
    return dcf(fcf, wacc, terminal_growth)

@router.post('/reverse_dcf')
def run_reverse_dcf(price_per_share: float, shares_out: float, wacc: float, years: int = 5):
    return {"implied_terminal_growth": reverse_dcf(price_per_share, shares_out, wacc, years)}

@router.post('/comps')
def run_comps(peer: List[Dict[str, float]]):
    return multiples(peer)

@router.post('/fundamentals')
def fundamentals(revenue: float, op_margin: float, tax_rate: float, capex: float, wc_delta: float):
    return statements_from_inputs(revenue, op_margin, tax_rate, capex, wc_delta)
