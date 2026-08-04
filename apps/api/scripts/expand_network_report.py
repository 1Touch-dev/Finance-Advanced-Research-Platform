"""
Expand PayPal Mafia report: add company financials, lobbying, contracts for each company.
"""
import sys, os, json, time, logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("expand")

KEY_COMPANIES = {
    "PLTR": {"name": "Palantir Technologies", "mafia": ["Peter Thiel", "Joe Lonsdale", "Stephen Cohen"]},
    "TSLA": {"name": "Tesla Inc", "mafia": ["Elon Musk"]},
    "AFRM": {"name": "Affirm Holdings", "mafia": ["Max Levchin"]},
    "YELP": {"name": "Yelp Inc", "mafia": ["Jeremy Stoppelman", "Russel Simmons", "Keith Rabois", "Max Levchin"]},
    "SQ": {"name": "Block Inc (Square)", "mafia": ["Keith Rabois", "Roelof Botha"]},
    "META": {"name": "Meta Platforms (Facebook)", "mafia": ["Peter Thiel"]},
    "HOOD": {"name": "Robinhood Markets", "mafia": []},
    "BLK": {"name": "BlackRock Inc", "mafia": ["Stephen Cohen"]},
}


def get_company_financials(ticker: str) -> Dict:
    try:
        from app.connectors.market_data_connector import get_market_snapshot
        return get_market_snapshot(ticker)
    except Exception as e:
        logger.warning(f"Market data failed for {ticker}: {e}")
        return {}


def get_insider_data(ticker: str) -> Dict:
    try:
        from app.connectors.sec_edgar_connector import get_insider_transactions, get_cik_from_ticker
        cik = get_cik_from_ticker(ticker)
        if cik:
            return get_insider_transactions(cik, start_date="2023-01-01")
        return {}
    except Exception as e:
        logger.warning(f"Insider data failed for {ticker}: {e}")
        return {}


def get_lobbying(company_name: str) -> Dict:
    try:
        from app.connectors.opensecrets_connector import get_lobbying
        return get_lobbying(company_name)
    except Exception as e:
        logger.warning(f"Lobbying failed for {company_name}: {e}")
        return {}


def get_contracts(company_name: str) -> Dict:
    try:
        from app.connectors.fpds_connector import get_full_contract_portfolio
        return get_full_contract_portfolio(company_name)
    except Exception as e:
        logger.warning(f"Contracts failed for {company_name}: {e}")
        return {}


def get_institutional(ticker: str) -> Dict:
    try:
        from app.connectors.sec_edgar_connector import get_institutional_holders, get_cik_from_ticker
        cik = get_cik_from_ticker(ticker)
        if cik:
            return get_institutional_holders(cik)
        return {}
    except Exception as e:
        logger.warning(f"Institutional failed for {ticker}: {e}")
        return {}


def fmt_money(val):
    if not val:
        return "N/A"
    val = float(val)
    if val >= 1e12:
        return f"${val/1e12:.2f}T"
    if val >= 1e9:
        return f"${val/1e9:.1f}B"
    if val >= 1e6:
        return f"${val/1e6:.1f}M"
    return f"${val:,.0f}"


def generate_company_section(ticker, info, financials, lobbying_data, contracts, insiders, institutional):
    lines = []
    name = info["name"]
    mafia_members = info["mafia"]

    lines.append(f"\n### {name} ({ticker})")
    lines.append("")
    lines.append(f"**PayPal Mafia Connection:** {', '.join(mafia_members) if mafia_members else 'Indirect (co-investment target)'}")
    lines.append("")

    # Financials
    price = financials.get("price")
    if price:
        lines.append("#### Market Data")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Current Price | ${price:.2f} |")
        mc = financials.get("market_cap", 0)
        lines.append(f"| Market Cap | {fmt_money(mc)} |")
        pe = financials.get("pe_ttm")
        lines.append(f"| P/E (TTM) | {pe if pe else 'N/A'} |")
        ps = financials.get("ps_ttm")
        lines.append(f"| P/S (TTM) | {ps if ps else 'N/A'} |")
        beta = financials.get("beta")
        lines.append(f"| Beta | {beta if beta else 'N/A'} |")
        w52h = financials.get("week_52_high", 0)
        w52l = financials.get("week_52_low", 0)
        lines.append(f"| 52W High | ${w52h:.2f} |")
        lines.append(f"| 52W Low | ${w52l:.2f} |")

        consensus = financials.get("consensus", {})
        if consensus.get("target_consensus"):
            lines.append(f"| Analyst Target | ${consensus['target_consensus']:.2f} |")
            ratings = consensus.get("ratings", {})
            buy = ratings.get("buy", 0) + ratings.get("strongBuy", 0)
            hold = ratings.get("hold", 0)
            sell = ratings.get("sell", 0) + ratings.get("strongSell", 0)
            lines.append(f"| Analyst Buy/Hold/Sell | {buy}/{hold}/{sell} |")
        lines.append("")

    # Insider activity
    if insiders and isinstance(insiders, dict):
        txns = insiders.get("transactions", [])
        if txns:
            lines.append(f"#### Insider Transactions ({len(txns)} recent)")
            lines.append("")
            lines.append("| Date | Name | Type | Shares | Value |")
            lines.append("|------|------|------|--------|-------|")
            for t in txns[:15]:
                val = fmt_money(t.get("value")) if t.get("value") else ""
                shares = t.get("shares", 0)
                sh_str = f"{int(shares):,}" if shares else ""
                lines.append(f"| {t.get('date', '')} | {t.get('name', '')} | {t.get('type', '')} | {sh_str} | {val} |")
            lines.append("")

    # Lobbying
    if lobbying_data and isinstance(lobbying_data, dict):
        spend = lobbying_data.get("spend_by_year") or lobbying_data.get("total_spend")
        if spend:
            lines.append("#### Lobbying Activity")
            lines.append("")
            if isinstance(spend, dict):
                lines.append("| Year | Spend |")
                lines.append("|------|-------|")
                for year, amount in sorted(spend.items(), reverse=True)[:6]:
                    lines.append(f"| {year} | {fmt_money(amount)} |")
            else:
                lines.append(f"Total lobbying spend: {fmt_money(spend)}")
            lines.append("")
            issues = lobbying_data.get("issues") or lobbying_data.get("issues_lobbied", [])
            if issues:
                lines.append(f"**Issues lobbied:** {', '.join(str(i) for i in issues[:8])}")
                lines.append("")

    # Government contracts
    if contracts and isinstance(contracts, dict):
        total = contracts.get("total_obligations") or contracts.get("total_value", 0)
        awards = contracts.get("awards") or contracts.get("results", [])
        if total or awards:
            lines.append("#### Government Contracts")
            lines.append("")
            if total:
                lines.append(f"**Total obligations:** {fmt_money(total)}")
                lines.append("")
            if isinstance(awards, list) and awards:
                lines.append("| Agency | Description | Value |")
                lines.append("|--------|-------------|-------|")
                for a in awards[:12]:
                    agency = str(a.get("agency") or a.get("awarding_agency_name", ""))[:35]
                    desc = str(a.get("description") or a.get("award_description", ""))[:55]
                    val = a.get("value") or a.get("total_obligation", 0)
                    lines.append(f"| {agency} | {desc} | {fmt_money(val)} |")
                lines.append("")

    # Institutional holders
    if institutional and isinstance(institutional, dict):
        holders = institutional.get("holders") or institutional.get("top_holders", [])
        if isinstance(holders, list) and holders:
            lines.append("#### Top Institutional Holders")
            lines.append("")
            lines.append("| Institution | Shares | Value |")
            lines.append("|-------------|--------|-------|")
            for h in holders[:10]:
                nm = h.get("name") or h.get("holder", "")
                sh = h.get("shares", 0)
                val = h.get("value", 0)
                lines.append(f"| {nm} | {int(sh):,} | {fmt_money(val)} |")
            lines.append("")

    return "\n".join(lines)


def main():
    logger.info("Loading existing PayPal Mafia report...")
    report_dir = Path(__file__).resolve().parent.parent.parent.parent / "apps" / "reports"

    # Find existing markdown
    existing_files = sorted(report_dir.glob("PayPal_Mafia_Deep_Intelligence_*.md"), reverse=True)
    if existing_files:
        base_md = existing_files[0].read_text(encoding="utf-8")
        logger.info(f"Using base: {existing_files[0].name}")
    else:
        base_md = "# PayPal Mafia Deep Intelligence Report\n\n*No base found.*\n"

    # Pull data for each company
    logger.info("Pulling company intelligence...")
    company_data = {}
    for ticker, info in KEY_COMPANIES.items():
        logger.info(f"  {ticker} ({info['name']})...")
        company_data[ticker] = {
            "info": info,
            "financials": get_company_financials(ticker),
            "insiders": get_insider_data(ticker),
            "lobbying": get_lobbying(info["name"].split("(")[0].strip()),
            "contracts": get_contracts(info["name"].split("(")[0].strip()),
            "institutional": get_institutional(ticker),
        }
        time.sleep(1)

    # Generate company sections
    logger.info("Generating company deep-dive sections...")
    company_md_parts = []
    company_md_parts.append("\n---\n")
    company_md_parts.append("## Deep Company Intelligence — PayPal Mafia Portfolio")
    company_md_parts.append("")
    company_md_parts.append("Full financial, lobbying, government contract, and ownership analysis for each major company in the network.")
    company_md_parts.append("")

    for ticker, data in company_data.items():
        section = generate_company_section(
            ticker, data["info"], data["financials"],
            data["lobbying"], data["contracts"],
            data["insiders"], data["institutional"]
        )
        company_md_parts.append(section)

    # Cross-company comparison
    company_md_parts.append("\n---\n")
    company_md_parts.append("## Cross-Company Comparison")
    company_md_parts.append("")
    company_md_parts.append("| Company | Market Cap | P/E | Beta | Mafia Members |")
    company_md_parts.append("|---------|-----------|-----|------|--------------|")
    for ticker, data in company_data.items():
        fin = data["financials"]
        mc = fin.get("market_cap", 0)
        mc_str = fmt_money(mc)
        pe = fin.get("pe_ttm", "N/A")
        beta = fin.get("beta", "N/A")
        members = ", ".join(data["info"]["mafia"][:3])
        company_md_parts.append(f"| {data['info']['name']} ({ticker}) | {mc_str} | {pe} | {beta} | {members} |")

    company_md_parts.append("")
    company_md_parts.append("### Combined Network Value")
    company_md_parts.append("")
    total_mc = sum(d["financials"].get("market_cap", 0) for d in company_data.values())
    company_md_parts.append(f"**Total market capitalization of PayPal Mafia public companies: {fmt_money(total_mc)}**")
    company_md_parts.append("")
    company_md_parts.append("This represents only public companies where mafia members hold/held board or officer positions. ")
    company_md_parts.append("Private holdings (SpaceX ~$350B, Founders Fund portfolio, 8VC portfolio) likely add another $500B+.")
    company_md_parts.append("")

    # Merge into base markdown
    company_text = "\n".join(company_md_parts)
    methodology_marker = "## Methodology"
    if methodology_marker in base_md:
        parts = base_md.split(methodology_marker, 1)
        final_md = parts[0] + company_text + "\n\n" + methodology_marker + parts[1]
    else:
        final_md = base_md + "\n\n" + company_text

    # Save
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path = report_dir / f"PayPal_Mafia_EXPANDED_{ts}.md"
    pdf_path = report_dir / f"PayPal_Mafia_EXPANDED_{ts}.pdf"

    md_path.write_text(final_md, encoding="utf-8")
    words = len(final_md.split())
    logger.info(f"Markdown saved: {md_path.name} ({words:,} words)")

    # Render PDF
    try:
        import markdown as md_lib
        from weasyprint import HTML

        html_body = md_lib.markdown(final_md, extensions=["tables", "fenced_code", "toc"])
        css = """
body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 35px; font-size: 9.5px; line-height: 1.4; color: #1a1a1a; }
h1 { font-size: 20px; border-bottom: 3px solid #1e40af; padding-bottom: 8px; color: #1e3a5f; }
h2 { font-size: 14px; color: #1e40af; margin-top: 20px; border-bottom: 1px solid #dbeafe; padding-bottom: 4px; page-break-after: avoid; }
h3 { font-size: 12px; color: #374151; margin-top: 14px; page-break-after: avoid; }
h4 { font-size: 10.5px; color: #4b5563; }
table { border-collapse: collapse; width: 100%; margin: 5px 0; font-size: 8.5px; }
th { background: #1e40af; color: white; padding: 3px 5px; text-align: left; }
td { padding: 2px 5px; border: 1px solid #e5e7eb; }
tr:nth-child(even) { background: #f9fafb; }
hr { border: none; border-top: 2px solid #1e40af; margin: 16px 0; }
img { max-width: 100%; height: auto; }
@page { size: A4; margin: 1.2cm; @bottom-center { content: counter(page); font-size: 8px; } }
"""
        full_html = f"<!DOCTYPE html><html><head><style>{css}</style></head><body>{html_body}</body></html>"
        HTML(string=full_html).write_pdf(str(pdf_path))

        import fitz
        doc = fitz.open(str(pdf_path))
        logger.info(f"PDF saved: {pdf_path.name} ({doc.page_count} pages)")
    except Exception as e:
        logger.error(f"PDF render error: {e}")
        import traceback
        traceback.print_exc()

    logger.info("DONE")


if __name__ == "__main__":
    main()
