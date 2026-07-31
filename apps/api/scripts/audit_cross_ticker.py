"""
Cross-ticker audit: exercise the financial extraction path against a basket
spanning sectors, fiscal-calendar conventions and naming edge cases.

Run:  python3 scripts/audit_cross_ticker.py
"""
import os
import sys
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))

from app.connectors.sec_edgar_connector import get_filer_cik as get_cik_from_ticker, get_full_financial_profile  # noqa: E402

# Chosen to stress specific assumptions rather than for coverage breadth:
#   AAPL  September fiscal year end
#   MSFT  June fiscal year end
#   TGT   52/53-week retail calendar ending early February (labels FY by START year)
#   JPM   bank — no GrossProfit concept, revenue tagged differently
#   XOM   energy — different cost structure
#   KO    "The Coca-Cola Company" — leading article breaks split()[0]
#   BAC   "Bank of America" — split()[0] yields the useless token "BANK"
#   BRK-B hyphenated share-class ticker
#   PLD   REIT — FFO-based, minimal GrossProfit
BASKET = ["AAPL", "MSFT", "TGT", "JPM", "XOM", "KO", "BAC", "BRK-B", "PLD", "NVDA"]


def audit(ticker: str) -> dict:
    row = {"ticker": ticker, "cik": None, "revenue": None, "fy_labels": [],
           "quarters": 0, "derived_q4": 0, "ttm": None, "margins_ok": False,
           "error": None}
    try:
        cik = get_cik_from_ticker(ticker)
        row["cik"] = cik
        if not cik:
            row["error"] = "CIK unresolved"
            return row

        profile = get_full_financial_profile(ticker)
        fs = profile.get("financial_statements") or {}
        annual = fs.get("income_statement") or []
        quarterly = fs.get("quarterly") or []
        ttm = fs.get("ttm") or {}

        if annual:
            row["revenue"] = annual[0].get("Revenues")
            row["fy_labels"] = [
                f"{r.get('fiscal_year')}:{r.get('period_end_date')}" for r in annual[:4]
            ]
            row["margins_ok"] = annual[0].get("net_margin") not in (None, 0)
        row["quarters"] = len(quarterly)
        row["derived_q4"] = sum(1 for q in quarterly if q.get("derived"))
        row["ttm"] = ttm.get("Revenues")
    except Exception as e:
        row["error"] = f"{type(e).__name__}: {e}"
        traceback.print_exc(file=sys.stderr)
    return row


print(f"{'TICK':<7}{'CIK':<12}{'Revenue($M)':>13}{'Qtrs':>6}{'DerQ4':>7}"
      f"{'TTM($M)':>13}{'Margins':>9}  FY labels (fy:period_end)")
print("-" * 132)
for tick in BASKET:
    r = audit(tick)
    rev = f"{r['revenue'] / 1e6:,.0f}" if r["revenue"] else "—"
    ttm = f"{r['ttm'] / 1e6:,.0f}" if r["ttm"] else "—"
    flag = "ok" if r["margins_ok"] else "ZERO"
    labels = " ".join(r["fy_labels"][:4]) or (r["error"] or "no annual data")
    print(f"{r['ticker']:<7}{str(r['cik']):<12}{rev:>13}{r['quarters']:>6}"
          f"{r['derived_q4']:>7}{ttm:>13}{flag:>9}  {labels}")
