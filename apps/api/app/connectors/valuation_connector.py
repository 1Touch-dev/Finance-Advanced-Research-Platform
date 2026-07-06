"""
Financial Valuation Connector
─────────────────────────────────────────────────────────────────────────────
Deep DCF (Discounted Cash Flow) valuation engine using:
  - SEC EDGAR XBRL for historical FCF and financial metrics
  - SEC EDGAR 10-K/10-Q text for MD&A, guidance, and risk factors
  - FRED API for risk-free rate (10-year Treasury)
  - yfinance for beta and market data
  - Pure-Python DCF with WACC, terminal value, intrinsic value calculation
"""
import os
import re
import html
import time
import logging
import requests
from typing import Optional

log = logging.getLogger(__name__)

EDGAR_BASE = "https://data.sec.gov"
SEC_HEADERS = {"User-Agent": "Finance-Platform/1.0 abhishekk@kyma.world"}
FRED_KEY = os.getenv("FRED_API_KEY", "")


def _get(url, params=None, timeout=15) -> dict:
    try:
        r = requests.get(url, params=params, headers=SEC_HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.warning("Valuation fetch %s: %s", url, e)
        return {}


def _get_text(url, timeout=20) -> str:
    try:
        r = requests.get(url, headers=SEC_HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.text
    except Exception as e:
        log.warning("Text fetch %s: %s", url, e)
        return ""


# ─── FRED: Risk-Free Rate ─────────────────────────────────────────────────────

def get_risk_free_rate() -> float:
    """10-year US Treasury yield from FRED (percent)."""
    if not FRED_KEY:
        return 4.5  # default fallback
    try:
        r = requests.get(
            "https://api.stlouisfed.org/fred/series/observations",
            params={"series_id": "DGS10", "api_key": FRED_KEY, "limit": 1,
                    "sort_order": "desc", "file_type": "json"},
            timeout=8
        )
        obs = r.json().get("observations", [])
        if obs:
            return float(obs[0]["value"])
    except Exception as e:
        log.warning("FRED rate error: %s", e)
    return 4.5


# ─── 10-K/10-Q Text Extraction ───────────────────────────────────────────────

def _clean_filing_text(raw_html: str) -> str:
    """Strip HTML from an SEC filing, returning clean readable text."""
    raw_html = re.sub(r'<script[^>]*>.*?</script>', ' ', raw_html, flags=re.DOTALL | re.IGNORECASE)
    raw_html = re.sub(r'<style[^>]*>.*?</style>', ' ', raw_html, flags=re.DOTALL | re.IGNORECASE)
    clean = re.sub(r'<[^>]+>', ' ', raw_html)
    clean = html.unescape(clean)
    clean = re.sub(r'[ \t]+', ' ', clean)
    clean = re.sub(r'\n\s*\n+', '\n', clean)
    return clean.strip()


def _extract_mda_text(clean_text: str, max_chars: int = 8000) -> str:
    """
    Extract MD&A (Management's Discussion and Analysis) section from cleaned filing text.
    Returns the most relevant portion.
    """
    # Find all "Item 2" occurrences and take the 3rd one (body, not TOC)
    occurrences = [m.start() for m in re.finditer(r'Item\s+2\.?\s*Management', clean_text, re.IGNORECASE)]
    if not occurrences:
        occurrences = [m.start() for m in re.finditer(r'Item\s+2\b', clean_text, re.IGNORECASE)]

    if len(occurrences) >= 2:
        start = occurrences[-1]  # Last occurrence is likely the actual body
    elif occurrences:
        start = occurrences[0]
    else:
        return ""

    # Find Item 3 to end the MD&A
    end_patterns = [
        re.search(r'Item\s+3\b', clean_text[start + 100:], re.IGNORECASE),
        re.search(r'QUANTITATIVE AND QUALITATIVE', clean_text[start + 100:], re.IGNORECASE),
    ]
    end = None
    for ep in end_patterns:
        if ep:
            end = start + 100 + ep.start()
            break

    snippet = clean_text[start:end or start + max_chars]
    return snippet[:max_chars]


def _extract_forward_guidance(mda_text: str) -> list:
    """Extract forward-looking statements and guidance from MD&A."""
    guidance = []

    # Revenue/sales guidance
    rev_patterns = [
        r'(?:expect|anticipate|project|forecast|guide|guidance).{0,100}(?:revenue|sales|net sales).{0,100}(?:\$[\d,\.]+|\d+%|billion|million)',
        r'(?:revenue|net sales).{0,50}(?:expect|anticipate|project).{0,100}(?:\$[\d,\.]+|\d+%)',
        r'(?:next quarter|Q\d|fiscal \d{4}).{0,100}(?:\$[\d,\.]+|\d+%)',
    ]
    for pattern in rev_patterns:
        matches = re.findall(pattern, mda_text, re.IGNORECASE | re.DOTALL)
        for m in matches[:3]:
            clean_m = re.sub(r'\s+', ' ', m).strip()
            if len(clean_m) > 20:
                guidance.append({"type": "revenue_guidance", "text": clean_m[:300]})

    # Margin guidance
    margin_patterns = [
        r'(?:gross margin|operating margin).{0,100}(?:expect|anticipate|approximately).{0,100}(?:\d+%)',
    ]
    for pattern in margin_patterns:
        matches = re.findall(pattern, mda_text, re.IGNORECASE | re.DOTALL)
        for m in matches[:2]:
            clean_m = re.sub(r'\s+', ' ', m).strip()
            if len(clean_m) > 20:
                guidance.append({"type": "margin_guidance", "text": clean_m[:300]})

    return guidance[:8]


def _extract_key_metrics_from_text(mda_text: str) -> dict:
    """Extract specific financial figures mentioned in MD&A narrative."""
    metrics = {}

    # Revenue mentions
    rev_match = re.search(
        r'(?:net sales|revenue)[^\.]*?\$\s*([\d,\.]+)\s*(billion|million)?',
        mda_text, re.IGNORECASE
    )
    if rev_match:
        val = float(rev_match.group(1).replace(',', ''))
        multiplier = 1e9 if rev_match.group(2) and 'billion' in rev_match.group(2).lower() else \
                     1e6 if rev_match.group(2) and 'million' in rev_match.group(2).lower() else 1
        metrics["mda_revenue_mention"] = val * multiplier

    # Growth mentions
    growth = re.findall(r'(?:increased|decreased|grew|declined)[^\.]*?(\d+)%', mda_text, re.IGNORECASE)
    if growth:
        metrics["growth_mentions_pct"] = [int(g) for g in growth[:5]]

    return metrics


def get_filing_analysis(ticker: str, cik: str = None) -> dict:
    """
    Download and analyze the most recent 10-Q and 10-K filings.
    Returns MD&A text, forward guidance, and extracted metrics.
    """
    from app.connectors.company_deep_connector import get_cik_for_ticker, get_recent_filings

    if not cik:
        cik = get_cik_for_ticker(ticker)
    if not cik:
        return {"ticker": ticker, "error": "CIK not found"}

    filings = get_recent_filings(ticker, ["10-Q", "10-K"], limit=4)
    results = []

    for filing in filings[:3]:
        doc_url = filing.get("document_url", "")
        if not doc_url or not doc_url.endswith(".htm"):
            continue
        try:
            raw = _get_text(doc_url, timeout=20)
            if not raw or len(raw) < 5000:
                continue
            clean = _clean_filing_text(raw)
            mda = _extract_mda_text(clean)
            if not mda:
                continue
            guidance = _extract_forward_guidance(mda)
            metrics = _extract_key_metrics_from_text(mda)

            # Extract risk factors
            risk_start = clean.find("Risk Factors")
            risk_text = clean[risk_start:risk_start + 2000] if risk_start > 0 else ""
            risks = re.findall(r'[A-Z][^.]{30,200}\.', risk_text)[:5]

            results.append({
                "form_type": filing["form_type"],
                "filing_date": filing["filing_date"],
                "mda_excerpt": mda[:3000],
                "forward_guidance": guidance,
                "extracted_metrics": metrics,
                "key_risks": risks[:5],
                "doc_url": doc_url,
            })

            if len(results) >= 2:
                break
        except Exception as e:
            log.warning("Filing analysis error %s: %s", doc_url, e)
            continue

    return {
        "ticker": ticker,
        "cik": cik,
        "filings_analyzed": len(results),
        "analyses": results,
    }


# ─── DCF Valuation Engine ─────────────────────────────────────────────────────

def _get_xbrl_series(cik: str, concept: str, unit: str = "USD") -> list:
    """Get a financial time series from SEC EDGAR XBRL."""
    data = _get(f"{EDGAR_BASE}/api/xbrl/companyfacts/CIK{cik}.json")
    if not data:
        return []
    us_gaap = data.get("facts", {}).get("us-gaap", {})
    items = us_gaap.get(concept, {}).get("units", {}).get(unit, [])
    annual = [x for x in items if x.get("form") == "10-K" and x.get("val") is not None]
    annual.sort(key=lambda x: x.get("end", ""), reverse=True)
    return annual[:5]


def build_dcf_valuation(ticker: str) -> dict:
    """
    Full DCF valuation:
    1. Extract historical FCF (5 years from XBRL)
    2. Calculate FCF growth rate
    3. Get WACC (FRED risk-free + ERP * beta from yfinance)
    4. Project FCF for 5 years
    5. Calculate terminal value
    6. Sum PV of cash flows + terminal value = intrinsic enterprise value
    7. Subtract net debt → equity value
    8. Divide by shares outstanding → intrinsic price per share
    """
    import math
    from app.connectors.company_deep_connector import get_cik_for_ticker

    cik = get_cik_for_ticker(ticker)
    if not cik:
        return {"ticker": ticker, "error": "CIK not found"}

    # ── Step 1: Get historical Free Cash Flow ──────────────────────────────
    # FCF = Operating Cash Flow - Capital Expenditures
    ocf_series = (
        _get_xbrl_series(cik, "NetCashProvidedByUsedInOperatingActivities") or
        _get_xbrl_series(cik, "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations")
    )
    capex_series = (
        _get_xbrl_series(cik, "PaymentsToAcquirePropertyPlantAndEquipment") or
        _get_xbrl_series(cik, "CapitalExpenditureDiscontinuedOperations")
    )

    # Match OCF and CapEx by fiscal year
    fcf_history = []
    for ocf in ocf_series[:5]:
        fy = ocf.get("fy")
        end = ocf.get("end", "")
        if not fy:
            continue
        capex_val = 0
        for cx in capex_series:
            if cx.get("fy") == fy:
                capex_val = abs(cx.get("val", 0) or 0)
                break
        fcf = (ocf.get("val", 0) or 0) - capex_val
        fcf_history.append({"fy": fy, "period_end": end, "ocf": ocf.get("val", 0), "capex": capex_val, "fcf": fcf})

    if not fcf_history:
        return {"ticker": ticker, "cik": cik, "error": "No FCF data available from XBRL"}

    # ── Step 2: Calculate FCF growth rate ─────────────────────────────────
    fcf_values = [x["fcf"] for x in fcf_history if x["fcf"] > 0]
    if len(fcf_values) >= 2:
        # CAGR from oldest to most recent
        oldest = fcf_values[-1]
        newest = fcf_values[0]
        n_years = len(fcf_values) - 1
        if oldest > 0 and newest > 0:
            historical_cagr = (newest / oldest) ** (1 / n_years) - 1
        else:
            historical_cagr = 0.05
    else:
        historical_cagr = 0.05  # 5% default

    # Cap growth rate: use lower of historical CAGR or 25%
    fcf_growth_5y = min(max(historical_cagr, 0.02), 0.25)
    terminal_growth = 0.025  # long-run terminal growth = 2.5%

    # ── Step 3: Calculate WACC ─────────────────────────────────────────────
    rf_rate = get_risk_free_rate() / 100  # convert from percent
    erp = 0.055  # Damodaran equity risk premium ~5.5%
    beta = 1.0
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info or {}
        beta = info.get("beta") or 1.0
        shares_out = info.get("sharesOutstanding") or 0
        current_price = info.get("currentPrice") or info.get("regularMarketPrice") or 0
        market_cap = info.get("marketCap") or (shares_out * current_price)
        total_debt = info.get("totalDebt") or 0
        cash = info.get("totalCash") or info.get("cashAndCashEquivalentsAtCarryingValue") or 0
        tax_rate = info.get("effectiveTaxRate") or 0.21
    except Exception:
        shares_out = 0
        current_price = 0
        market_cap = 0
        total_debt = 0
        cash = 0
        tax_rate = 0.21

    # Cost of equity (CAPM)
    cost_of_equity = rf_rate + beta * erp

    # Cost of debt (simplified: rf + 1.5% spread)
    cost_of_debt_pretax = rf_rate + 0.015
    cost_of_debt_aftertax = cost_of_debt_pretax * (1 - tax_rate)

    # Capital structure weights
    equity_val = market_cap or 1
    debt_val = total_debt or 0
    total_capital = equity_val + debt_val
    w_equity = equity_val / total_capital if total_capital > 0 else 0.9
    w_debt = debt_val / total_capital if total_capital > 0 else 0.1

    wacc = w_equity * cost_of_equity + w_debt * cost_of_debt_aftertax
    wacc = max(wacc, 0.05)  # floor at 5%

    # ── Step 4: Project FCF ────────────────────────────────────────────────
    base_fcf = fcf_values[0] if fcf_values else 0
    projected_fcfs = []
    for yr in range(1, 6):
        proj = base_fcf * ((1 + fcf_growth_5y) ** yr)
        pv = proj / ((1 + wacc) ** yr)
        projected_fcfs.append({"year": yr, "projected_fcf": round(proj), "present_value": round(pv)})

    # ── Step 5: Terminal Value ─────────────────────────────────────────────
    if wacc <= terminal_growth:
        terminal_growth = wacc - 0.01
    fcf_year5 = base_fcf * ((1 + fcf_growth_5y) ** 5)
    terminal_value = fcf_year5 * (1 + terminal_growth) / (wacc - terminal_growth)
    pv_terminal = terminal_value / ((1 + wacc) ** 5)

    # ── Step 6: Enterprise Value ──────────────────────────────────────────
    pv_fcfs = sum(x["present_value"] for x in projected_fcfs)
    enterprise_value = pv_fcfs + pv_terminal
    net_debt = total_debt - cash
    equity_value = max(enterprise_value - net_debt, 0)

    # ── Step 7: Intrinsic Price Per Share ─────────────────────────────────
    intrinsic_price = (equity_value / shares_out) if shares_out > 0 else None

    # ── Valuation Assessment ──────────────────────────────────────────────
    upside_pct = None
    assessment = "UNKNOWN"
    if intrinsic_price and current_price:
        upside_pct = (intrinsic_price - current_price) / current_price * 100
        if upside_pct > 30:
            assessment = "SIGNIFICANTLY UNDERVALUED"
        elif upside_pct > 10:
            assessment = "MODERATELY UNDERVALUED"
        elif upside_pct > -10:
            assessment = "FAIRLY VALUED"
        elif upside_pct > -30:
            assessment = "MODERATELY OVERVALUED"
        else:
            assessment = "SIGNIFICANTLY OVERVALUED"

    # ── Bear / Bull Scenarios ─────────────────────────────────────────────
    def _scenario(growth_adj, wacc_adj):
        g = min(max(fcf_growth_5y + growth_adj, 0.01), 0.35)
        w = max(wacc + wacc_adj, 0.04)
        pv = sum(base_fcf * ((1+g)**yr) / ((1+w)**yr) for yr in range(1,6))
        fcf5 = base_fcf * ((1+g)**5)
        tg = min(terminal_growth, w - 0.01)
        tv = fcf5 * (1 + tg) / (w - tg)
        ev = pv + tv / ((1+w)**5)
        eq = max(ev - net_debt, 0)
        return round(eq / shares_out, 2) if shares_out > 0 else None

    return {
        "ticker": ticker,
        "cik": cik,
        # Inputs
        "inputs": {
            "base_fcf": base_fcf,
            "fcf_growth_5y_assumed": round(fcf_growth_5y * 100, 2),
            "historical_cagr_pct": round(historical_cagr * 100, 2),
            "terminal_growth_pct": round(terminal_growth * 100, 2),
            "wacc_pct": round(wacc * 100, 2),
            "cost_of_equity_pct": round(cost_of_equity * 100, 2),
            "cost_of_debt_aftertax_pct": round(cost_of_debt_aftertax * 100, 2),
            "beta": round(beta, 2),
            "risk_free_rate_pct": round(rf_rate * 100, 2),
            "equity_weight": round(w_equity, 3),
            "debt_weight": round(w_debt, 3),
        },
        # FCF History
        "fcf_history": fcf_history[:5],
        # Projections
        "projected_fcfs": projected_fcfs,
        # Valuation
        "pv_projected_fcfs": round(pv_fcfs),
        "terminal_value": round(terminal_value),
        "pv_terminal_value": round(pv_terminal),
        "enterprise_value": round(enterprise_value),
        "net_debt": round(net_debt),
        "equity_value": round(equity_value),
        "intrinsic_price_per_share": round(intrinsic_price, 2) if intrinsic_price else None,
        "current_market_price": round(current_price, 2) if current_price else None,
        "market_cap": market_cap,
        "upside_downside_pct": round(upside_pct, 2) if upside_pct is not None else None,
        "assessment": assessment,
        # Scenarios
        "scenarios": {
            "bull": {
                "description": "Higher growth (+5%), lower WACC (-1%)",
                "intrinsic_price": _scenario(+0.05, -0.01),
            },
            "base": {
                "description": "Base case",
                "intrinsic_price": round(intrinsic_price, 2) if intrinsic_price else None,
            },
            "bear": {
                "description": "Lower growth (-5%), higher WACC (+1%)",
                "intrinsic_price": _scenario(-0.05, +0.01),
            },
        },
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


# ─── Combined Valuation Report ────────────────────────────────────────────────

def full_valuation_report(ticker: str) -> dict:
    """
    Comprehensive valuation report:
    - DCF intrinsic value
    - 10-K/10-Q MD&A analysis and forward guidance
    - Key risks extracted from filings
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    tasks = {
        "dcf": lambda: build_dcf_valuation(ticker),
        "filing_analysis": lambda: get_filing_analysis(ticker),
    }
    results = {}
    with ThreadPoolExecutor(max_workers=2) as ex:
        fut_map = {ex.submit(fn): name for name, fn in tasks.items()}
        for fut in as_completed(fut_map):
            name = fut_map[fut]
            try:
                results[name] = fut.result(timeout=60)
            except Exception as e:
                results[name] = {"error": str(e)}
                log.warning("Valuation task %s failed: %s", name, e)

    # Synthesis narrative
    dcf = results.get("dcf", {})
    fa = results.get("filing_analysis", {})
    assessment = dcf.get("assessment", "")
    intrinsic = dcf.get("intrinsic_price_per_share")
    current = dcf.get("current_market_price")
    upside = dcf.get("upside_downside_pct")
    growth = dcf.get("inputs", {}).get("fcf_growth_5y_assumed")
    wacc = dcf.get("inputs", {}).get("wacc_pct")

    narrative_parts = []
    if intrinsic and current:
        direction = "undervalued" if intrinsic > current else "overvalued"
        narrative_parts.append(
            f"Based on our DCF model, {ticker} appears {direction} at the current price of "
            f"${current:.2f}. Our intrinsic value estimate is ${intrinsic:.2f} per share, "
            f"implying {'+' if upside and upside > 0 else ''}{upside:.1f}% {'upside' if upside and upside > 0 else 'downside'}."
        )
    if growth:
        narrative_parts.append(
            f"The model assumes {growth:.1f}% FCF growth over 5 years (based on historical CAGR), "
            f"discounted at a WACC of {wacc:.1f}%."
        )

    guidance_count = sum(len(a.get("forward_guidance", [])) for a in fa.get("analyses", []))
    if guidance_count > 0:
        narrative_parts.append(
            f"Management's Discussion ({fa.get('filings_analyzed', 0)} filing(s) analyzed) "
            f"contains {guidance_count} forward-looking statements."
        )

    results["synthesis"] = {
        "assessment": assessment,
        "narrative": " ".join(narrative_parts),
        "key_takeaway": (
            f"DCF Target: ${intrinsic:.2f} | Market: ${current:.2f} | {assessment}"
            if intrinsic and current else "Insufficient data for valuation"
        ),
    }
    results["ticker"] = ticker
    results["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return results
