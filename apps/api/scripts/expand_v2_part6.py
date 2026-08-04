
# ============ ANALYSIS SECTIONS ============

def generate_cross_analysis(company_data: Dict, people: List) -> List[str]:
    """Cross-portfolio analysis."""
    md = []
    md.append("### Portfolio Valuation Comparison")
    md.append("")
    md.append("| Company | Ticker | Market Cap | P/E | P/S | Beta | Mafia Connection |")
    md.append("|---------|--------|-----------|-----|-----|------|-----------------|")
    for ticker, data in company_data.items():
        fin = data.get("financials", {})
        mc = fin.get("market_cap", 0)
        info = data.get("info", {})
        name = info.get("name", COMPANIES_FULL.get(ticker, {}).get("name", ticker))
        mafia = ", ".join(info.get("mafia", [])[:2])
        md.append(f"| {name} | {ticker} | {fmt_money(mc)} | {fin.get('pe_ttm', 'N/A')} | {fin.get('ps_ttm', 'N/A')} | {fin.get('beta', 'N/A')} | {mafia} |")
    md.append("")

    total_mc = sum(d.get("financials", {}).get("market_cap", 0) for d in company_data.values())
    md.append(f"**Combined Public Market Capitalization: {fmt_money(total_mc)}**")
    md.append("")

    md.append("### Sector Allocation")
    md.append("")
    md.append("| Sector | Companies | Combined Market Cap | % of Portfolio |")
    md.append("|--------|-----------|--------------------|--------------:|")
    sectors = defaultdict(lambda: {"companies": [], "mc": 0})
    for ticker, data in company_data.items():
        info = COMPANIES_FULL.get(ticker, {})
        sector = info.get("sector", "Other").split("/")[0].strip()
        mc = data.get("financials", {}).get("market_cap", 0)
        sectors[sector]["companies"].append(ticker)
        sectors[sector]["mc"] += mc
    for sector, sdata in sorted(sectors.items(), key=lambda x: -x[1]["mc"]):
        pct = (sdata["mc"] / total_mc * 100) if total_mc else 0
        md.append(f"| {sector} | {', '.join(sdata['companies'])} | {fmt_money(sdata['mc'])} | {pct:.1f}% |")
    md.append("")

    md.append("### Performance Metrics Summary")
    md.append("")
    md.append("**Risk-Return Profile:**")
    md.append("")
    betas = [d.get("financials", {}).get("beta", 0) for d in company_data.values() if d.get("financials", {}).get("beta")]
    if betas:
        avg_beta = sum(betas) / len(betas)
        md.append(f"- Portfolio Average Beta: **{avg_beta:.2f}** (vs. market 1.0)")
        md.append(f"- Highest Risk: {max(company_data.items(), key=lambda x: x[1].get('financials', {}).get('beta', 0))[0]} (Beta {max(betas):.2f})")
        md.append(f"- Lowest Risk: {min(company_data.items(), key=lambda x: x[1].get('financials', {}).get('beta', 99) if x[1].get('financials', {}).get('beta') else 99)[0]}")
    md.append("")

    md.append("### Valuation Thesis")
    md.append("")
    md.append("The PayPal Mafia portfolio is characterized by **premium valuations** driven by:")
    md.append("")
    md.append("1. **Network Effects**: META, YELP, HOOD — all platform businesses with user-driven moats")
    md.append("2. **Government Lock-in**: PLTR's classified contracts create 10+ year switching costs")
    md.append("3. **Category Creation**: TSLA (EVs), AFRM (transparent BNPL), SQ (merchant payments)")
    md.append("4. **Data Moats**: Every company in the portfolio generates proprietary datasets")
    md.append("")
    md.append("This explains P/E ratios consistently above market averages — the market prices in ")
    md.append("durable competitive advantages and network-driven growth compounding.")
    md.append("")

    md.append("### Correlation & Co-Movement Analysis")
    md.append("")
    md.append("Companies in the PayPal Mafia portfolio exhibit moderate-to-high correlation due to:")
    md.append("- Shared investor base (Founders Fund, Sequoia cross-hold)")
    md.append("- Similar macro sensitivity (tech/growth factor)")
    md.append("- Overlapping board members creating information flow")
    md.append("- Common customer segments (tech-savvy, high-income consumers)")
    md.append("")
    md.append("**Risk Implication:** High correlation means diversification benefit is limited ")
    md.append("within the mafia portfolio. A tech/growth downturn affects all simultaneously.")
    md.append("")

    return md


def generate_political_section(company_data: Dict, people: List) -> List[str]:
    """Government and political intelligence."""
    md = []
    md.append("### Federal Contract Portfolio Summary")
    md.append("")
    total_contracts = 0
    md.append("| Company | Total Obligations | Primary Agency | UEI Resolution |")
    md.append("|---------|------------------|----------------|---------------|")
    for ticker, data in company_data.items():
        c = data.get("contracts", {})
        total = c.get("total_obligations") or c.get("total_value", 0)
        if total:
            total_contracts += float(total)
            agency = "Multiple"
            awards = c.get("awards") or c.get("results", [])
            if isinstance(awards, list) and awards:
                agency = str(awards[0].get("agency") or awards[0].get("awarding_agency_name", ""))[:25]
            uei = c.get("recipient_uei") or "Text search"
            name = data.get("info", {}).get("name", ticker)
            md.append(f"| {name} | {fmt_money(total)} | {agency} | {uei} |")
    md.append(f"| **TOTAL** | **{fmt_money(total_contracts)}** | | |")
    md.append("")

    md.append("### Defense & Intelligence Concentration")
    md.append("")
    md.append("Palantir Technologies dominates the network's government relationship:")
    md.append("")
    md.append("- **Agencies served:** CIA, NSA, DHS, Army, Navy, Air Force, Space Force, CDC, NIH, IRS")
    md.append("- **Contract types:** IDIQ (Indefinite Delivery), Cost-Plus, Firm Fixed Price")
    md.append("- **Key programs:** Project Maven (AI for DoD), Army Vantage, CDC disease surveillance")
    md.append("- **International:** UK NHS, Australian Defence, NATO allies")
    md.append("")
    md.append("This concentration creates both opportunity (recurring revenue, high margins) and risk ")
    md.append("(political dependency, security clearance requirements, ethical scrutiny).")
    md.append("")

    md.append("### Lobbying Intelligence")
    md.append("")
    md.append("| Company | Total Lobby Spend | Key Issues | Trend |")
    md.append("|---------|------------------|-----------|-------|")
    for ticker, data in company_data.items():
        lob = data.get("lobbying", {})
        if lob and isinstance(lob, dict):
            spend = lob.get("spend_by_year", {})
            if isinstance(spend, dict) and spend:
                total = sum(float(v) for v in spend.values())
                issues = lob.get("issues", lob.get("issues_lobbied", []))
                issues_str = ", ".join(str(i) for i in issues[:3]) if issues else "General"
                name = data.get("info", {}).get("name", ticker)
                md.append(f"| {name} | {fmt_money(total)} | {issues_str} | Active |")
    md.append("")

    md.append("### Political Donations & Influence")
    md.append("")
    md.append("PayPal Mafia members are among the largest political donors in tech:")
    md.append("")
    md.append("| Person | Political Leaning | Notable Donations | Influence Vector |")
    md.append("|--------|------------------|-------------------|-----------------|")
    md.append("| Peter Thiel | Libertarian/Right | $15M+ to Trump PACs, JD Vance | Direct candidate backing |")
    md.append("| Elon Musk | Independent/Right | $100M+ political (2024) | Platform ownership (X) |")
    md.append("| Reid Hoffman | Democrat/Left | $20M+ to Biden/Dem PACs | Board influence, media |")
    md.append("| David Sacks | Libertarian/Right | $5M+ to GOP | Podcast influence, advisory |")
    md.append("| Keith Rabois | Right-leaning | Multiple GOP donations | VC network |")
    md.append("")
    md.append("**Key Insight:** The PayPal Mafia spans the political spectrum but concentrates ")
    md.append("on anti-regulatory, pro-innovation policy regardless of party affiliation.")
    md.append("")

    md.append("### Ambassadorial & Government Service")
    md.append("")
    md.append("| Person | Role | Period | Significance |")
    md.append("|--------|------|--------|-------------|")
    md.append("| Ken Howery | US Ambassador to Sweden | 2019-2021 | Diplomatic access |")
    md.append("| Peter Thiel | Trump Transition Team | 2016-2017 | Policy influence |")
    md.append("| Elon Musk | DOGE (Government Efficiency) | 2025-present | Direct executive power |")
    md.append("| David Sacks | White House AI/Crypto Czar | 2025-present | Policy architect |")
    md.append("")

    return md


def generate_fund_analysis(people: List) -> List[str]:
    """Venture fund analysis."""
    md = []
    md.append("### Venture Fund Operations")
    md.append("")
    md.append("The PayPal Mafia operates or has operated the following major venture funds:")
    md.append("")
    md.append("| Fund | GP(s) | Est. AUM | Focus | Notable Investments |")
    md.append("|------|-------|---------|-------|---------------------|")
    md.append("| Founders Fund | Thiel, Nosek, Howery | $12B | Deep tech, defense | SpaceX, Palantir, Stripe, Anduril |")
    md.append("| Sequoia Capital | Botha (MP) | $85B | Full-stack tech | Apple, Google, Airbnb, Stripe |")
    md.append("| Craft Ventures | Sacks | $3B | SaaS, crypto, defense | SpaceX, Bird, ClickUp |")
    md.append("| 8VC | Lonsdale | $5B | Defense, health, RE | Anduril, Oscar Health, Joby |")
    md.append("| Greylock Partners | Hoffman | $4B | Enterprise, consumer | LinkedIn, Discord, Figma |")
    md.append("| Khosla Ventures | Rabois (former) | $15B | Clean tech, enterprise | DoorDash, Affirm |")
    md.append("| Mithril Capital | Thiel | $2B | Growth stage | Palantir, SpaceX |")
    md.append("| Valar Ventures | Thiel | $1B | International fintech | TransferWise, N26 |")
    md.append("| Gigafund | Nosek | $1B | Space, energy | SpaceX, nuclear |")
    md.append("| Youniversity Ventures | Karim | <$500M | Seed/angel | Airbnb (early) |")
    md.append("")
    md.append(f"**Combined estimated AUM: >$125 billion**")
    md.append("")

    md.append("### Fund Interconnections")
    md.append("")
    md.append("These funds frequently co-invest, creating layered exposure:")
    md.append("")
    md.append("| Target Company | Funds Investing | Round | Significance |")
    md.append("|---------------|-----------------|-------|-------------|")
    md.append("| SpaceX | Founders Fund, Craft, Gigafund, 8VC | Multiple | Highest co-investment density |")
    md.append("| Anduril | Founders Fund, 8VC | Series D+ | Defense-tech alignment |")
    md.append("| Stripe | Founders Fund, Sequoia | Series A+ | Payments heritage |")
    md.append("| Palantir | Founders Fund, Mithril | Growth | Origin company |")
    md.append("| Airbnb | Founders Fund, Greylock, Sequoia | Multiple | Platform thesis |")
    md.append("")

    md.append("### Second-Generation Mafia")
    md.append("")
    md.append("Companies funded by PayPal Mafia VCs that have produced their own talent networks:")
    md.append("")
    md.append("| Company | Funded By | Alumni Now Leading |")
    md.append("|---------|-----------|-------------------|")
    md.append("| Stripe | Sequoia, Founders Fund | Stripe alumni at Ramp, Mercury, Modern Treasury |")
    md.append("| Palantir | Founders Fund, Mithril | Palantir alumni at Anduril, Databricks, Scale AI |")
    md.append("| Square/Block | Sequoia, Khosla | Square alumni at Plaid, Marqeta, Cash App spinoffs |")
    md.append("| LinkedIn | Greylock | LinkedIn alumni at hundreds of SaaS companies |")
    md.append("")
    md.append("This 'second-generation' effect means the PayPal Mafia's influence extends far beyond ")
    md.append("direct investments into a self-perpetuating talent and capital network.")
    md.append("")

    return md


def generate_risk_section(company_data: Dict, people: List) -> List[str]:
    """Risk assessment."""
    md = []
    md.append("### Concentration Risk Analysis")
    md.append("")
    md.append("| Risk Factor | Severity | Affected Companies | Mitigation |")
    md.append("|-------------|----------|-------------------|-----------|")
    md.append("| Tech sector downturn | HIGH | All | Diversification limited within portfolio |")
    md.append("| Interest rate sensitivity | HIGH | AFRM, HOOD, growth names | Duration risk on future cash flows |")
    md.append("| Regulatory crackdown (antitrust) | MEDIUM | META, GOOG, MSFT | Scale creates regulatory target |")
    md.append("| Defense budget cuts | MEDIUM | PLTR | Revenue concentration in government |")
    md.append("| Key person risk | HIGH | TSLA (Musk), AFRM (Levchin) | Founder-dependent narratives |")
    md.append("| Political backlash | MEDIUM | All | Mafia members' public political activity |")
    md.append("| AI disruption | LOW-MED | YELP, traditional SaaS | AI could disrupt review/search businesses |")
    md.append("")

    md.append("### Insider Trading Patterns")
    md.append("")
    md.append("Analysis of insider transactions across the portfolio reveals:")
    md.append("")
    total_sell = 0
    total_buy = 0
    for ticker, data in company_data.items():
        txns = data.get("insiders", {}).get("transactions", [])
        for t in txns:
            ttype = str(t.get("type", "")).lower()
            val = t.get("value", 0) or 0
            if "sell" in ttype or "sale" in ttype:
                total_sell += float(val)
            elif "buy" in ttype or "purchase" in ttype:
                total_buy += float(val)

    md.append(f"- **Net insider selling (2023-present):** {fmt_money(total_sell)}")
    md.append(f"- **Net insider buying (2023-present):** {fmt_money(total_buy)}")
    if total_sell and total_buy:
        ratio = total_sell / max(total_buy, 1)
        md.append(f"- **Sell/Buy Ratio:** {ratio:.1f}x")
    md.append("")
    md.append("*Note: Insider selling is common for diversification and does not necessarily indicate ")
    md.append("bearish sentiment, especially for founders with concentrated holdings.*")
    md.append("")

    md.append("### Geopolitical Risk Exposure")
    md.append("")
    md.append("| Company | China Revenue | Europe Revenue | Sanction Risk | Supply Chain Risk |")
    md.append("|---------|-------------|---------------|--------------|------------------|")
    md.append("| TSLA | High (Shanghai factory) | High | Medium | High (batteries) |")
    md.append("| META | Blocked in China | High (GDPR) | Low | Low |")
    md.append("| PLTR | None (excluded) | Growing | None | Low (software) |")
    md.append("| GOOG | Blocked in China | High (DMA/GDPR) | Low | Low |")
    md.append("| MSFT | Significant | High | Medium | Medium |")
    md.append("")

    md.append("### Network Fragility Assessment")
    md.append("")
    md.append("Despite its power, the PayPal Mafia network has potential fragility points:")
    md.append("")
    md.append("1. **Political Divergence**: Hoffman (left) vs. Thiel/Musk/Sacks (right) creates internal tension")
    md.append("2. **Generational Shift**: All members now 45-55+; succession at funds is underway")
    md.append("3. **Public Scrutiny**: 'All-In Podcast' and Twitter/X have increased public awareness of the network")
    md.append("4. **Regulatory Coordination**: If regulators connect the dots on cross-board influence")
    md.append("5. **Reputation Contagion**: One member's scandal could affect others (shared brand)")
    md.append("")

    return md


# ============ MAIN EXECUTION ============

def main():
    logger.info("Starting PayPal Mafia Expanded Report v2...")

    report_dir = Path(__file__).resolve().parent.parent.parent.parent / "apps" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    # Pull company data
    logger.info("Phase 1: Pulling financial intelligence for all companies...")
    tickers_to_pull = list(KEY_COMPANIES.keys()) + ["MSFT", "GOOG", "DASH", "ABNB"]
    company_data = {}

    for ticker in tickers_to_pull:
        info = KEY_COMPANIES.get(ticker, {"name": COMPANIES_FULL.get(ticker, {}).get("name", ticker), "mafia": []})
        logger.info(f"  {ticker} ({info['name']})...")
        company_name = info["name"].split("(")[0].strip()

        company_data[ticker] = {
            "info": info,
            "financials": get_company_financials(ticker),
            "insiders": get_insider_data(ticker),
            "lobbying": get_lobbying(company_name),
            "contracts": get_contracts(company_name),
            "institutional": get_institutional(ticker),
        }
        time.sleep(1.5)

    # Generate charts
    logger.info("Phase 2: Generating charts...")
    charts = generate_charts(company_data, PEOPLE)

    # Generate report
    logger.info("Phase 3: Generating full report...")
    report_md = generate_full_report(company_data, PEOPLE, charts)

    # Save markdown
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path = report_dir / f"PayPal_Mafia_EXPANDED_v2_{ts}.md"
    pdf_path = report_dir / f"PayPal_Mafia_EXPANDED_v2_{ts}.pdf"

    md_path.write_text(report_md, encoding="utf-8")
    words = len(report_md.split())
    logger.info(f"Markdown saved: {md_path.name} ({words:,} words, {len(report_md.splitlines()):,} lines)")

    # Render PDF
    logger.info("Phase 4: Rendering PDF...")
    try:
        import markdown as md_lib
        from weasyprint import HTML

        html_body = md_lib.markdown(report_md, extensions=["tables", "fenced_code", "toc"])
        css = """
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 40px; font-size: 9.5px; line-height: 1.45; color: #1a1a1a; }
h1 { font-size: 22px; border-bottom: 3px solid #1e40af; padding-bottom: 10px; color: #1e3a5f; page-break-before: always; }
h1:first-child { page-break-before: avoid; }
h2 { font-size: 15px; color: #1e40af; margin-top: 22px; border-bottom: 1.5px solid #dbeafe; padding-bottom: 5px; page-break-after: avoid; }
h3 { font-size: 12px; color: #374151; margin-top: 16px; page-break-after: avoid; }
h4 { font-size: 10.5px; color: #4b5563; margin-top: 10px; }
table { border-collapse: collapse; width: 100%; margin: 6px 0; font-size: 8.5px; page-break-inside: auto; }
th { background: #1e40af; color: white; padding: 4px 6px; text-align: left; }
td { padding: 3px 6px; border: 1px solid #e5e7eb; }
tr:nth-child(even) { background: #f9fafb; }
tr { page-break-inside: avoid; }
hr { border: none; border-top: 2px solid #1e40af; margin: 18px 0; }
img { max-width: 100%; height: auto; margin: 8px 0; page-break-inside: avoid; }
li { margin: 2px 0; }
strong { color: #1e3a5f; }
p { margin: 4px 0; }
@page { size: A4; margin: 1.5cm; @bottom-center { content: counter(page); font-size: 8px; color: #6b7280; } }
"""
        full_html = f"<!DOCTYPE html><html><head><meta charset='utf-8'><style>{css}</style></head><body>{html_body}</body></html>"
        HTML(string=full_html).write_pdf(str(pdf_path))

        import fitz
        doc = fitz.open(str(pdf_path))
        logger.info(f"PDF saved: {pdf_path.name} ({doc.page_count} pages)")
        doc.close()
    except Exception as e:
        logger.error(f"PDF render error: {e}")
        import traceback
        traceback.print_exc()

    logger.info("DONE")


if __name__ == "__main__":
    main()
