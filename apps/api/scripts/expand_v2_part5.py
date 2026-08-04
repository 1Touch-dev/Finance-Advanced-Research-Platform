
# ============ COMPANY DOSSIER GENERATOR ============

def generate_company_dossier(ticker: str, data: Dict) -> List[str]:
    """Generate full company intelligence dossier."""
    md = []
    info = COMPANIES_FULL.get(ticker, data.get("info", {}))
    name = info.get("name", ticker)
    financials = data.get("financials", {})
    insiders = data.get("insiders", {})
    lobbying_data = data.get("lobbying", {})
    contracts = data.get("contracts", {})
    institutional = data.get("institutional", {})
    mafia = data.get("info", {}).get("mafia", [])

    md.append(f"### {name} ({ticker})")
    md.append("")
    md.append(f"**Sector:** {info.get('sector', 'N/A')} | **Founded:** {info.get('founded', 'N/A')} | **IPO:** {info.get('ipo', 'N/A')}")
    md.append("")
    if mafia:
        md.append(f"**PayPal Mafia Members:** {', '.join(mafia)}")
        md.append("")

    # Market Data
    price = financials.get("price")
    if price:
        md.append("#### Financial Profile")
        md.append("")
        md.append("| Metric | Value |")
        md.append("|--------|-------|")
        md.append(f"| Share Price | ${price:.2f} |")
        mc = financials.get("market_cap", 0)
        md.append(f"| Market Capitalization | {fmt_money(mc)} |")
        md.append(f"| P/E Ratio (TTM) | {financials.get('pe_ttm', 'N/A')} |")
        md.append(f"| P/S Ratio (TTM) | {financials.get('ps_ttm', 'N/A')} |")
        md.append(f"| Beta (Volatility) | {financials.get('beta', 'N/A')} |")
        md.append(f"| 52-Week High | ${financials.get('week_52_high', 0):.2f} |")
        md.append(f"| 52-Week Low | ${financials.get('week_52_low', 0):.2f} |")
        md.append(f"| 50-Day Moving Avg | ${financials.get('price_avg_50', 0):.2f} |")
        md.append(f"| 200-Day Moving Avg | ${financials.get('price_avg_200', 0):.2f} |")
        pct = financials.get("pct_below_52w_high")
        if pct:
            md.append(f"| Distance from 52W High | {pct:.1f}% |")
        md.append("")

        # Analyst consensus
        consensus = financials.get("consensus", {})
        if consensus.get("target_consensus"):
            md.append("#### Analyst Consensus")
            md.append("")
            md.append("| Metric | Value |")
            md.append("|--------|-------|")
            md.append(f"| Target Price (Mean) | ${consensus['target_consensus']:.2f} |")
            md.append(f"| Target Price (Median) | ${consensus.get('target_median', 0):.2f} |")
            md.append(f"| Target High | ${consensus.get('target_high', 0):.2f} |")
            md.append(f"| Target Low | ${consensus.get('target_low', 0):.2f} |")
            ratings = consensus.get("ratings", {})
            md.append(f"| Strong Buy | {ratings.get('strongBuy', 0)} |")
            md.append(f"| Buy | {ratings.get('buy', 0)} |")
            md.append(f"| Hold | {ratings.get('hold', 0)} |")
            md.append(f"| Sell | {ratings.get('sell', 0)} |")
            md.append(f"| Strong Sell | {ratings.get('strongSell', 0)} |")
            bp = consensus.get("bullish_pct")
            if bp:
                md.append(f"| Bullish Consensus | {bp:.1f}% |")
            upside = ((consensus["target_consensus"] - price) / price) * 100
            md.append(f"| Implied Upside/Downside | {upside:+.1f}% |")
            md.append("")

    # Insider Transactions
    if insiders and isinstance(insiders, dict):
        txns = insiders.get("transactions", [])
        if txns:
            md.append(f"#### Insider Trading Activity ({len(txns)} transactions)")
            md.append("")
            md.append("| Date | Insider | Transaction | Shares | Value |")
            md.append("|------|---------|-------------|--------|-------|")
            for t in txns[:20]:
                val = fmt_money(t.get("value")) if t.get("value") else ""
                shares = t.get("shares", 0)
                sh_str = f"{int(shares):,}" if shares else ""
                md.append(f"| {t.get('date', '')} | {t.get('name', '')} | {t.get('type', '')} | {sh_str} | {val} |")
            md.append("")

    # Lobbying
    if lobbying_data and isinstance(lobbying_data, dict):
        spend = lobbying_data.get("spend_by_year") or lobbying_data.get("total_spend")
        if spend:
            md.append("#### Lobbying & Political Activity")
            md.append("")
            if isinstance(spend, dict) and spend:
                md.append("| Year | Lobbying Expenditure |")
                md.append("|------|---------------------|")
                for year, amount in sorted(spend.items(), reverse=True)[:8]:
                    md.append(f"| {year} | {fmt_money(amount)} |")
                total_lobby = sum(float(v) for v in spend.values())
                md.append(f"| **Total** | **{fmt_money(total_lobby)}** |")
                md.append("")
            issues = lobbying_data.get("issues") or lobbying_data.get("issues_lobbied", [])
            if issues:
                md.append(f"**Key Issues Lobbied:** {', '.join(str(i) for i in issues[:10])}")
                md.append("")

    # Government Contracts
    if contracts and isinstance(contracts, dict):
        total = contracts.get("total_obligations") or contracts.get("total_value", 0)
        awards = contracts.get("awards") or contracts.get("results", [])
        if total or awards:
            md.append("#### Government Contracts & Federal Awards")
            md.append("")
            if total:
                md.append(f"**Total Federal Obligations:** {fmt_money(total)}")
                md.append("")
            uei = contracts.get("recipient_uei") or contracts.get("uei")
            if uei:
                md.append(f"**UEI:** {uei}")
                md.append("")
            if isinstance(awards, list) and awards:
                md.append("| Agency | Description | Obligation | Period |")
                md.append("|--------|-------------|-----------|--------|")
                for a in awards[:15]:
                    agency = str(a.get("agency") or a.get("awarding_agency_name", ""))[:30]
                    desc = str(a.get("description") or a.get("award_description", ""))[:50]
                    val = a.get("value") or a.get("total_obligation", 0)
                    period = str(a.get("period_of_performance_start_date", ""))[:10]
                    md.append(f"| {agency} | {desc} | {fmt_money(val)} | {period} |")
                md.append("")

    # Institutional Holders
    if institutional and isinstance(institutional, dict):
        holders = institutional.get("holders") or institutional.get("top_holders", [])
        if isinstance(holders, list) and holders:
            md.append("#### Institutional Ownership")
            md.append("")
            md.append("| Institution | Shares Held | Value | % Outstanding |")
            md.append("|-------------|-------------|-------|--------------|")
            for h in holders[:12]:
                nm = h.get("name") or h.get("holder", "")
                sh = h.get("shares", 0)
                val = h.get("value", 0)
                pct = h.get("pct_outstanding", "")
                pct_str = f"{pct:.2f}%" if isinstance(pct, (int, float)) else ""
                md.append(f"| {nm} | {int(sh):,} | {fmt_money(val)} | {pct_str} |")
            md.append("")

    md.append("")
    return md
