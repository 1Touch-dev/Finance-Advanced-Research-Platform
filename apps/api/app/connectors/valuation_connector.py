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

# Explicit-forecast horizon before the terminal value takes over.
PROJECTION_YEARS = 10

# Blume weighting on raw beta; the remainder is pulled towards the market beta
# of 1.0. Applied uniformly so no issuer receives a hand-tuned discount rate.
BLUME_WEIGHT = 2.0 / 3.0


def _faded_growth(initial: float, terminal: float, year: int, horizon: int) -> float:
    """Growth rate in a given year, gliding linearly from initial to terminal."""
    if horizon <= 1:
        return terminal
    return initial + (terminal - initial) * (year - 1) / (horizon - 1)


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


def _get_xbrl_latest(cik: str, concepts: list, unit: str = "USD") -> Optional[float]:
    """First non-empty value across a list of candidate XBRL concept names."""
    for concept in concepts:
        series = _get_xbrl_series(cik, concept, unit)
        if series:
            val = series[0].get("val")
            if val is not None:
                return float(val)
    return None


def _get_market_inputs(ticker: str, cik: str) -> dict:
    """
    Market and balance-sheet inputs for the DCF, resolved through three tiers:

      1. yfinance, when the package is importable
      2. Finnhub / FMP / Alpha Vantage via market_data_connector
      3. SEC XBRL for balance-sheet items no price API carries (debt, cash)

    Previously a single yfinance failure zeroed price, shares, debt and cash
    simultaneously, which collapsed the entire valuation to $0.00. Each field is
    now resolved independently so one missing input cannot cascade.
    """
    inputs = {
        "beta": None, "shares_out": None, "current_price": None,
        "market_cap": None, "total_debt": None, "cash": None,
        "tax_rate": None, "sources": {}, "provider": None,
    }

    # ── Tier 1: yfinance ──────────────────────────────────────────────────
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info or {}
        if info.get("currentPrice") or info.get("regularMarketPrice"):
            inputs.update({
                "beta": info.get("beta"),
                "shares_out": info.get("sharesOutstanding"),
                "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
                "market_cap": info.get("marketCap"),
                "total_debt": info.get("totalDebt"),
                "cash": info.get("totalCash"),
                "tax_rate": info.get("effectiveTaxRate"),
                "provider": "yfinance",
            })
    except Exception as e:
        log.info("yfinance unavailable for %s (%s); using market data APIs", ticker, e)

    # ── Tier 2: market data APIs ──────────────────────────────────────────
    if not inputs["current_price"]:
        try:
            from app.connectors.market_data_connector import get_market_snapshot
            snap = get_market_snapshot(ticker)
            snap_sources = snap.get("sources", {})
            for field, key in (("current_price", "price"), ("beta", "beta"),
                               ("shares_out", "shares_outstanding"),
                               ("market_cap", "market_cap")):
                if not inputs[field] and snap.get(key) is not None:
                    inputs[field] = snap[key]
                    if key in snap_sources:
                        inputs["sources"][field] = snap_sources[key]
            if snap.get("data_available"):
                inputs["provider"] = ",".join(snap.get("providers_used", [])) or "market_data"
                inputs["market_snapshot"] = snap
        except Exception as e:
            log.warning("Market data fallback failed for %s: %s", ticker, e)

    # ── Tier 3: SEC XBRL for balance-sheet items ──────────────────────────
    if cik:
        xbrl_url = f"{EDGAR_BASE}/api/xbrl/companyfacts/CIK{cik}.json"
        if inputs["total_debt"] is None:
            long_term = _get_xbrl_latest(cik, [
                "LongTermDebtNoncurrent", "LongTermDebt",
                "DebtLongtermAndShorttermCombinedAmount",
            ]) or 0
            short_term = _get_xbrl_latest(cik, [
                "LongTermDebtCurrent", "ShortTermBorrowings",
            ]) or 0
            if long_term or short_term:
                inputs["total_debt"] = long_term + short_term
                inputs["sources"]["total_debt"] = xbrl_url

        if inputs["cash"] is None:
            cash_val = _get_xbrl_latest(cik, [
                "CashAndCashEquivalentsAtCarryingValue",
                "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
            ]) or 0
            investments = _get_xbrl_latest(cik, [
                "MarketableSecuritiesCurrent", "ShortTermInvestments",
                "AvailableForSaleSecuritiesDebtSecuritiesCurrent",
            ]) or 0
            if cash_val or investments:
                inputs["cash"] = cash_val + investments
                inputs["sources"]["cash"] = xbrl_url

        if inputs["shares_out"] is None:
            shares = _get_xbrl_latest(cik, [
                "CommonStockSharesOutstanding", "CommonStockSharesIssued",
            ], unit="shares")
            if shares:
                inputs["shares_out"] = shares
                inputs["sources"]["shares_out"] = xbrl_url

    # Derive market cap when only price and share count are known.
    if not inputs["market_cap"] and inputs["current_price"] and inputs["shares_out"]:
        inputs["market_cap"] = inputs["current_price"] * inputs["shares_out"]

    # Defaults only for modelling assumptions, never for retrievable facts.
    if not inputs["beta"]:
        inputs["beta"] = 1.0
    if not inputs["tax_rate"]:
        inputs["tax_rate"] = 0.21
    inputs["total_debt"] = inputs["total_debt"] or 0
    inputs["cash"] = inputs["cash"] or 0

    return inputs


def build_dcf_valuation(ticker: str) -> dict:
    """
    Full DCF valuation:
    1. Extract historical FCF (5 years from XBRL)
    2. Calculate FCF growth rate
    3. Get WACC (FRED risk-free + ERP * beta from yfinance)
    4. Project FCF for 5 years
    5. Calculate terminal value
    6. Sum PV of cash flows + terminal value = intrinsic enterprise value

    The horizon is ten years with growth fading to the terminal rate, matching
    how sell-side models treat a company that cannot compound above the economy
    indefinitely.
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
    # Issuers migrate between capex tags: NVIDIA reports
    # PaymentsToAcquireProductiveAssets while others use
    # PaymentsToAcquirePropertyPlantAndEquipment. Taking the first tag that
    # exists returns whichever the company used to file under, leaving recent
    # years unmatched and capex silently zero — which overstates free cash flow
    # by the whole capital programme. All candidates are merged instead.
    capex_by_period: Dict[str, float] = {}
    for concept in ("PaymentsToAcquirePropertyPlantAndEquipment",
                    "PaymentsToAcquireProductiveAssets",
                    "PaymentsToAcquirePropertyPlantAndEquipmentAndIntangibleAssets",
                    "CapitalExpenditureDiscontinuedOperations"):
        for entry in _get_xbrl_series(cik, concept):
            end = (entry.get("end") or "")[:10]
            value = abs(entry.get("val", 0) or 0)
            if end and value:
                capex_by_period[end] = max(capex_by_period.get(end, 0), value)

    # Periods are matched on end date; the XBRL "fy" field labels the filing,
    # not the period it reports.
    # A period restated in a later filing appears more than once in the fact
    # series; the first occurrence is the most recent filing of it.
    fcf_history = []
    seen_periods = set()
    for ocf in ocf_series:
        end = (ocf.get("end") or "")[:10]
        if not end or end in seen_periods:
            continue
        seen_periods.add(end)
        if len(fcf_history) >= 5:
            break
        capex_val = capex_by_period.get(end, 0)
        ocf_val = ocf.get("val", 0) or 0
        fcf_history.append({
            "fy": ocf.get("fy"),
            "period_end": end,
            "ocf": ocf_val,
            "capex": capex_val,
            "capex_retrieved": end in capex_by_period,
            "fcf": ocf_val - capex_val,
        })

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
    market = _get_market_inputs(ticker, cik)
    beta = market["beta"]
    shares_out = market["shares_out"] or 0
    current_price = market["current_price"] or 0
    market_cap = market["market_cap"] or 0
    total_debt = market["total_debt"]
    cash = market["cash"]
    tax_rate = market["tax_rate"]

    # Cost of equity (CAPM) on a Blume-adjusted beta. Raw regression beta is a
    # noisy estimate that reverts towards the market over time; NVIDIA's raw
    # 2.25 drove WACC to 16.9% and discounted the company to a third of any
    # sell-side estimate. The two-thirds/one-third weighting is the standard
    # adjustment and is applied to every issuer rather than tuned per name.
    adjusted_beta = round(BLUME_WEIGHT * beta + (1 - BLUME_WEIGHT) * 1.0, 3)
    cost_of_equity = rf_rate + adjusted_beta * erp

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
    # Growth fades linearly from the historical rate to the terminal rate over
    # the horizon. Holding the initial rate flat then dropping to terminal in a
    # single step implies a company still compounding at 25% in year ten, which
    # loads almost all the value into the terminal jump.
    if wacc <= terminal_growth:
        terminal_growth = wacc - 0.01

    base_fcf = fcf_values[0] if fcf_values else 0
    projected_fcfs = []
    fcf = base_fcf
    for yr in range(1, PROJECTION_YEARS + 1):
        growth = _faded_growth(fcf_growth_5y, terminal_growth, yr, PROJECTION_YEARS)
        fcf *= (1 + growth)
        pv = fcf / ((1 + wacc) ** yr)
        projected_fcfs.append({
            "year": yr,
            "growth_rate_pct": round(growth * 100, 2),
            "projected_fcf": round(fcf),
            "present_value": round(pv),
        })

    # ── Step 5: Terminal Value ─────────────────────────────────────────────
    fcf_terminal = fcf
    terminal_value = fcf_terminal * (1 + terminal_growth) / (wacc - terminal_growth)
    pv_terminal = terminal_value / ((1 + wacc) ** PROJECTION_YEARS)

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
    def _price_at(g, w, tg):
        """Re-run the model at one point in the assumption space."""
        g = min(max(g, 0.01), 0.35)
        w = max(w, 0.04)
        tg = min(tg, w - 0.01)

        pv = 0.0
        cash_flow = base_fcf
        for yr in range(1, PROJECTION_YEARS + 1):
            cash_flow *= (1 + _faded_growth(g, tg, yr, PROJECTION_YEARS))
            pv += cash_flow / ((1 + w) ** yr)

        tv = cash_flow * (1 + tg) / (w - tg)
        ev = pv + tv / ((1 + w) ** PROJECTION_YEARS)
        eq = max(ev - net_debt, 0)
        return round(eq / shares_out, 2) if shares_out > 0 else None

    def _scenario(growth_adj, wacc_adj):
        return _price_at(fcf_growth_5y + growth_adj, wacc + wacc_adj,
                         terminal_growth)

    return {
        "ticker": ticker,
        "cik": cik,
        # Inputs
        "inputs": {
            "base_fcf": base_fcf,
            "projection_years": PROJECTION_YEARS,
            "fcf_growth_initial_pct": round(fcf_growth_5y * 100, 2),
            "fcf_growth_5y_assumed": round(fcf_growth_5y * 100, 2),
            "growth_fade": "linear to terminal growth over the horizon",
            "historical_cagr_pct": round(historical_cagr * 100, 2),
            "terminal_growth_pct": round(terminal_growth * 100, 2),
            "wacc_pct": round(wacc * 100, 2),
            "cost_of_equity_pct": round(cost_of_equity * 100, 2),
            "cost_of_debt_aftertax_pct": round(cost_of_debt_aftertax * 100, 2),
            "beta_raw": round(beta, 2),
            "beta_adjusted": adjusted_beta,
            "beta": adjusted_beta,
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
        # Provenance
        "market_data_provider": market.get("provider"),
        "sources": market.get("sources", {}),
        "market_snapshot": market.get("market_snapshot", {}),
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


# ─── Enhanced Scenario & Sensitivity Analysis ─────────────────────────────────

def generate_scenario_analysis(ticker: str) -> dict:
    """
    Generate Bear/Base/Bull scenario analysis with different assumptions.

    Returns three DCF scenarios with varying growth and WACC assumptions.
    """
    base_dcf = build_dcf_valuation(ticker)

    if "error" in base_dcf:
        return {"ticker": ticker, "error": base_dcf.get("error")}

    # Get base parameters
    base_fcf = base_dcf.get("inputs", {}).get("base_fcf", 0)
    base_growth = base_dcf.get("inputs", {}).get("fcf_growth_5y_assumed", 10) / 100
    base_wacc = base_dcf.get("inputs", {}).get("wacc_pct", 10) / 100
    terminal_growth = base_dcf.get("inputs", {}).get("terminal_growth_pct", 2.5) / 100
    net_debt = base_dcf.get("net_debt", 0)
    shares_out = base_dcf.get("market_cap", 0) / base_dcf.get("current_market_price", 1) if base_dcf.get("current_market_price") else 0

    def run_scenario(growth_rate, wacc_rate):
        """Run DCF with specific growth and WACC assumptions."""
        projected_pv = 0
        for yr in range(1, 6):
            fcf = base_fcf * ((1 + growth_rate) ** yr)
            pv = fcf / ((1 + wacc_rate) ** yr)
            projected_pv += pv

        fcf_year5 = base_fcf * ((1 + growth_rate) ** 5)
        tg = min(terminal_growth, wacc_rate - 0.01)
        terminal_value = fcf_year5 * (1 + tg) / (wacc_rate - tg)
        pv_terminal = terminal_value / ((1 + wacc_rate) ** 5)

        enterprise_value = projected_pv + pv_terminal
        equity_value = max(enterprise_value - net_debt, 0)
        intrinsic = equity_value / shares_out if shares_out > 0 else 0

        return {
            "growth_rate": growth_rate,
            "wacc": wacc_rate,
            "enterprise_value": round(enterprise_value),
            "equity_value": round(equity_value),
            "intrinsic_price": round(intrinsic, 2),
        }

    scenarios = {
        "bear": {
            "description": "Conservative: Lower growth (-5%), higher WACC (+2%)",
            "growth_assumption": max(base_growth - 0.05, 0.02),
            "wacc_assumption": base_wacc + 0.02,
        },
        "base": {
            "description": "Base case using historical trends",
            "growth_assumption": base_growth,
            "wacc_assumption": base_wacc,
        },
        "bull": {
            "description": "Optimistic: Higher growth (+5%), lower WACC (-1%)",
            "growth_assumption": min(base_growth + 0.05, 0.30),
            "wacc_assumption": max(base_wacc - 0.01, 0.06),
        },
    }

    for scenario_name, params in scenarios.items():
        result = run_scenario(params["growth_assumption"], params["wacc_assumption"])
        scenarios[scenario_name].update(result)

    # Calculate probability-weighted value (25/50/25 weights)
    weighted_price = (
        0.25 * scenarios["bear"]["intrinsic_price"] +
        0.50 * scenarios["base"]["intrinsic_price"] +
        0.25 * scenarios["bull"]["intrinsic_price"]
    )

    current_price = base_dcf.get("current_market_price", 0)
    weighted_upside = ((weighted_price - current_price) / current_price * 100) if current_price else 0

    return {
        "ticker": ticker,
        "scenarios": scenarios,
        "probability_weighted": {
            "weights": {"bear": 0.25, "base": 0.50, "bull": 0.25},
            "weighted_intrinsic_price": round(weighted_price, 2),
            "current_price": current_price,
            "weighted_upside_pct": round(weighted_upside, 1),
        },
        "base_dcf": base_dcf,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def generate_sensitivity_analysis(
    ticker: str,
    wacc_range: tuple = (0.06, 0.14),
    growth_range: tuple = (0.02, 0.10),
    steps: int = 5,
) -> dict:
    """
    Generate sensitivity grid for WACC vs Growth Rate.

    Args:
        ticker: Stock ticker
        wacc_range: (min, max) WACC values
        growth_range: (min, max) growth rate values
        steps: Number of steps in each dimension

    Returns:
        Sensitivity grid with intrinsic values.
    """
    base_dcf = build_dcf_valuation(ticker)

    if "error" in base_dcf:
        return {"ticker": ticker, "error": base_dcf.get("error")}

    # Get parameters
    base_fcf = base_dcf.get("inputs", {}).get("base_fcf", 0)
    terminal_growth = base_dcf.get("inputs", {}).get("terminal_growth_pct", 2.5) / 100
    net_debt = base_dcf.get("net_debt", 0)
    current_price = base_dcf.get("current_market_price", 0)
    shares_out = base_dcf.get("market_cap", 0) / current_price if current_price else 0

    # Generate ranges
    wacc_step = (wacc_range[1] - wacc_range[0]) / (steps - 1)
    growth_step = (growth_range[1] - growth_range[0]) / (steps - 1)

    wacc_values = [round(wacc_range[0] + i * wacc_step, 3) for i in range(steps)]
    growth_values = [round(growth_range[0] + i * growth_step, 3) for i in range(steps)]

    def calc_intrinsic(growth_rate, wacc_rate):
        if wacc_rate <= terminal_growth:
            return None
        projected_pv = sum(
            (base_fcf * ((1 + growth_rate) ** yr)) / ((1 + wacc_rate) ** yr)
            for yr in range(1, 6)
        )
        fcf5 = base_fcf * ((1 + growth_rate) ** 5)
        tg = min(terminal_growth, wacc_rate - 0.01)
        tv = fcf5 * (1 + tg) / (wacc_rate - tg)
        pv_tv = tv / ((1 + wacc_rate) ** 5)
        ev = projected_pv + pv_tv
        eq = max(ev - net_debt, 0)
        return round(eq / shares_out, 2) if shares_out > 0 else None

    # Build grid
    grid = []
    for wacc in wacc_values:
        row = []
        for growth in growth_values:
            intrinsic = calc_intrinsic(growth, wacc)
            row.append(intrinsic)
        grid.append(row)

    return {
        "ticker": ticker,
        "current_price": current_price,
        "wacc_values": [f"{w*100:.1f}%" for w in wacc_values],
        "growth_values": [f"{g*100:.1f}%" for g in growth_values],
        "sensitivity_grid": grid,
        "base_case": {
            "wacc": f"{base_dcf.get('inputs', {}).get('wacc_pct', 0):.1f}%",
            "growth": f"{base_dcf.get('inputs', {}).get('fcf_growth_5y_assumed', 0):.1f}%",
            "intrinsic_price": base_dcf.get("intrinsic_price_per_share"),
        },
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def generate_valuation_markdown(ticker: str) -> str:
    """
    Generate markdown-formatted valuation report.

    Returns a complete valuation section for intelligence reports.
    """
    scenario = generate_scenario_analysis(ticker)
    if "error" in scenario:
        return f"## Valuation Analysis\n\nError: {scenario.get('error')}"

    lines = []
    lines.append(f"## Valuation Analysis: {ticker}")
    lines.append("")

    dcf = scenario.get("base_dcf", {})
    current = dcf.get("current_market_price", 0)
    assessment = dcf.get("assessment", "UNKNOWN")

    lines.append(f"**Current Price:** ${current:,.2f}")
    lines.append(f"**Assessment:** {assessment}")
    lines.append("")

    # Scenario table
    lines.append("### DCF Scenario Analysis")
    lines.append("")
    lines.append("| Scenario | Growth | WACC | Intrinsic Value | vs Current |")
    lines.append("|----------|--------|------|-----------------|------------|")

    for name in ["bear", "base", "bull"]:
        s = scenario["scenarios"].get(name, {})
        intrinsic = s.get("intrinsic_price", 0)
        growth = s.get("growth_assumption", 0) * 100
        wacc = s.get("wacc_assumption", 0) * 100
        vs_current = ((intrinsic - current) / current * 100) if current else 0
        lines.append(f"| {name.title()} | {growth:.1f}% | {wacc:.1f}% | ${intrinsic:,.2f} | {vs_current:+.1f}% |")

    lines.append("")

    # Probability-weighted
    pw = scenario.get("probability_weighted", {})
    lines.append(f"**Probability-Weighted Value:** ${pw.get('weighted_intrinsic_price', 0):,.2f}")
    lines.append(f"**Expected Return:** {pw.get('weighted_upside_pct', 0):+.1f}%")
    lines.append("")

    # Key assumptions
    inputs = dcf.get("inputs", {})
    lines.append("### Key Assumptions")
    lines.append("")
    lines.append(f"- **Base FCF:** ${inputs.get('base_fcf', 0):,.0f}")
    lines.append(f"- **5Y FCF Growth:** {inputs.get('fcf_growth_5y_assumed', 0):.1f}%")
    lines.append(f"- **WACC:** {inputs.get('wacc_pct', 0):.1f}%")
    lines.append(f"- **Terminal Growth:** {inputs.get('terminal_growth_pct', 0):.1f}%")
    lines.append(f"- **Beta:** {inputs.get('beta', 1.0):.2f}")
    lines.append("")

    return "\n".join(lines)


# ─── Convenience Exports ──────────────────────────────────────────────────────

def get_dcf(ticker: str) -> dict:
    """Get DCF valuation."""
    return build_dcf_valuation(ticker)


def get_scenarios(ticker: str) -> dict:
    """Get Bear/Base/Bull scenario analysis."""
    return generate_scenario_analysis(ticker)


def get_sensitivity(ticker: str) -> dict:
    """Get sensitivity grid."""
    return generate_sensitivity_analysis(ticker)


def get_valuation_report(ticker: str) -> dict:
    """Get full valuation report."""
    return full_valuation_report(ticker)


def valuation_to_markdown(ticker: str) -> str:
    """Get markdown valuation report."""
    return generate_valuation_markdown(ticker)
