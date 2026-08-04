"""
SEC-API Report Rendering Service
────────────────────────────────────────────────────────────────────────────
Transforms structured SEC-API data into rich markdown sections for the
intelligence report. Each section adds depth that the basic SEC EDGAR
connector cannot provide.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime


def render_form_d_markdown(data: Dict[str, Any]) -> List[str]:
    """Render Form D (Private Placements) section."""
    lines = []
    filings = data.get("filings", [])
    if not filings and not data.get("error"):
        return []

    lines.append("### Private Placements (Form D)")
    lines.append("")

    if data.get("error"):
        lines.append(f"*Data unavailable: {data['error']}*")
        lines.append("")
        return lines

    if not filings:
        lines.append("No Form D private placement filings found for this entity.")
        lines.append("")
        return lines

    total = data.get("total_raised", 0)
    lines.append(f"**{len(filings)} Form D filings identified**"
                 + (f" | Total capital raised: ${total:,.0f}" if total else ""))
    lines.append("")

    # Exemptions used
    exemptions = data.get("exemptions_used", [])
    if exemptions:
        lines.append(f"**Exemptions used:** {', '.join(str(e) for e in exemptions)}")
        lines.append("")

    # Filings table
    lines.append("| Filed | Issuer | Amount Sold | Offering Size | Exemption |")
    lines.append("|-------|--------|------------|---------------|-----------|")
    for f in filings[:15]:
        filed = (f.get("filed_at") or "")[:10]
        issuer = f.get("issuer_name") or f.get("company") or "—"
        sold = f"${f['total_amount_sold']:,.0f}" if f.get("total_amount_sold") else "—"
        offering = f"${f['total_offering_amount']:,.0f}" if f.get("total_offering_amount") else "—"
        exemption = f.get("exemption") or "—"
        lines.append(f"| {filed} | {issuer[:40]} | {sold} | {offering} | {exemption} |")
    lines.append("")

    # Investors identified
    investors = data.get("investors_identified", [])
    if investors:
        lines.append(f"**Related Persons / Promoters Identified ({len(investors)}):**")
        lines.append("")
        for inv in investors[:20]:
            name = inv.get("name", "Unknown")
            rel = inv.get("relationship", "")
            loc = f"{inv.get('city', '')}, {inv.get('state', '')}".strip(", ")
            lines.append(f"- **{name}** — {rel}" + (f" ({loc})" if loc else ""))
        lines.append("")

    return lines


def render_nport_markdown(data: Dict[str, Any]) -> List[str]:
    """Render N-PORT (Fund Holdings) section."""
    lines = []
    holdings = data.get("holdings", [])
    if not holdings and not data.get("error"):
        return []

    lines.append("### Fund Holdings & Implied Valuation (N-PORT)")
    lines.append("")

    if data.get("error"):
        lines.append(f"*Data unavailable: {data['error']}*")
        lines.append("")
        return lines

    if not holdings:
        lines.append("No N-PORT fund holding data found.")
        lines.append("")
        return lines

    total_value = data.get("total_value_held", 0)
    lines.append(f"**{data.get('funds_holding', 0)} funds hold positions** "
                 f"| Aggregate reported value: ${total_value:,.0f}")
    lines.append("")

    # Holdings table
    lines.append("| Fund | Value (USD) | Shares | % of Fund | Asset Type |")
    lines.append("|------|------------|--------|-----------|------------|")
    for h in sorted(holdings, key=lambda x: x.get("value_usd", 0), reverse=True)[:20]:
        fund = (h.get("fund_name") or "—")[:35]
        value = f"${h['value_usd']:,.0f}" if h.get("value_usd") else "—"
        shares = f"{h['shares']:,.0f}" if h.get("shares") else "—"
        pct = f"{h['pct_of_fund']:.2f}%" if h.get("pct_of_fund") else "—"
        atype = h.get("asset_type") or "—"
        lines.append(f"| {fund} | {value} | {shares} | {pct} | {atype} |")
    lines.append("")

    # Implied prices
    implied = data.get("implied_prices", [])
    if implied:
        lines.append("**Implied Price Per Share (from fund marks):**")
        lines.append("")
        lines.append("| Fund | Implied Price | Report Date |")
        lines.append("|------|--------------|-------------|")
        for ip in implied[:10]:
            lines.append(f"| {(ip.get('fund') or '—')[:35]} "
                         f"| ${ip.get('implied_price_per_share', 0):,.4f} "
                         f"| {(ip.get('date') or '—')[:10]} |")
        lines.append("")
        prices = [ip["implied_price_per_share"] for ip in implied
                  if ip.get("implied_price_per_share")]
        if prices:
            avg = sum(prices) / len(prices)
            lines.append(f"*Average implied price across {len(prices)} fund marks: "
                         f"${avg:,.2f}*")
            lines.append("")

    return lines


def render_subsidiaries_markdown(data: Dict[str, Any]) -> List[str]:
    """Render Company Subsidiaries section."""
    lines = []
    subs = data.get("subsidiaries", [])
    if not subs and not data.get("error"):
        return []

    lines.append("### Corporate Subsidiaries")
    lines.append("")

    if data.get("error"):
        lines.append(f"*Data unavailable: {data['error']}*")
        lines.append("")
        return lines

    if not subs:
        lines.append("No subsidiary data available.")
        lines.append("")
        return lines

    total = data.get("total_count", 0)
    jurisdictions = data.get("jurisdictions", {})
    lines.append(f"**{total} subsidiaries** across "
                 f"{len(jurisdictions)} jurisdictions")
    lines.append("")

    # Top jurisdictions
    if jurisdictions:
        sorted_j = sorted(jurisdictions.items(), key=lambda x: x[1], reverse=True)
        lines.append("**Jurisdiction distribution:**")
        lines.append("")
        for j, count in sorted_j[:10]:
            lines.append(f"- {j}: {count} entities")
        lines.append("")

    # Subsidiaries table
    lines.append("| Subsidiary | Jurisdiction | Ownership |")
    lines.append("|-----------|-------------|-----------|")
    for s in subs[:50]:
        name = (s.get("name") or "—")[:50]
        j = s.get("jurisdiction") or "—"
        own = f"{s['ownership_pct']}%" if s.get("ownership_pct") else "100%"
        lines.append(f"| {name} | {j} | {own} |")
    if total > 50:
        lines.append(f"| *... and {total - 50} more* | | |")
    lines.append("")

    return lines


def render_executive_comp_markdown(data: Dict[str, Any]) -> List[str]:
    """Render Executive Compensation section (from SEC-API)."""
    lines = []
    execs = data.get("executives", [])
    if not execs and not data.get("error"):
        return []

    lines.append("### Executive Compensation (Structured)")
    lines.append("")

    if data.get("error"):
        lines.append(f"*Data unavailable: {data['error']}*")
        lines.append("")
        return lines

    if not execs:
        lines.append("No structured compensation data available.")
        lines.append("")
        return lines

    ceo_comp = data.get("total_ceo_comp", 0)
    median = data.get("median_employee_pay", 0)
    ratio = data.get("ceo_pay_ratio")

    if ceo_comp:
        lines.append(f"**CEO Total Compensation:** ${ceo_comp:,.0f}")
    if median:
        lines.append(f"**Median Employee Pay:** ${median:,.0f}")
    if ratio:
        lines.append(f"**CEO Pay Ratio:** {ratio}:1")
    lines.append("")

    # Compensation table
    lines.append("| Executive | Title | Salary | Bonus | Stock Awards | Options | Total |")
    lines.append("|-----------|-------|--------|-------|-------------|---------|-------|")
    for ex in sorted(execs, key=lambda x: x.get("total", 0), reverse=True)[:10]:
        name = (ex.get("name") or "—")[:25]
        title = (ex.get("title") or "—")[:20]
        salary = f"${ex['salary']:,.0f}" if ex.get("salary") else "—"
        bonus = f"${ex['bonus']:,.0f}" if ex.get("bonus") else "—"
        stock = f"${ex['stock_awards']:,.0f}" if ex.get("stock_awards") else "—"
        options = f"${ex['option_awards']:,.0f}" if ex.get("option_awards") else "—"
        total = f"${ex['total']:,.0f}" if ex.get("total") else "—"
        lines.append(f"| {name} | {title} | {salary} | {bonus} | {stock} | {options} | {total} |")
    lines.append("")

    return lines


def render_beneficial_ownership_markdown(data: Dict[str, Any]) -> List[str]:
    """Render 13D/13G Beneficial Ownership section."""
    lines = []
    filings = data.get("filings", [])
    if not filings and not data.get("error"):
        return []

    lines.append("### Beneficial Ownership & Activist Positions (13D/13G)")
    lines.append("")

    if data.get("error"):
        lines.append(f"*Data unavailable: {data['error']}*")
        lines.append("")
        return lines

    if not filings:
        lines.append("No 13D/13G beneficial ownership filings found.")
        lines.append("")
        return lines

    activists = data.get("activists_identified", [])
    if activists:
        lines.append(f"**⚠️ {len(activists)} activist position(s) identified (13D filings):**")
        lines.append("")
        for a in activists:
            lines.append(f"- {a}")
        lines.append("")

    lines.append("| Filer | Form | Filed | Activist? |")
    lines.append("|-------|------|-------|-----------|")
    for f in filings[:15]:
        # The actual filer is the holder, not the subject company
        filer = (f.get("reporting_owner") or f.get("filer") or "—")[:40]
        form = f.get("form_type") or "—"
        filed = (f.get("filed_at") or "")[:10]
        activist = "✅ Yes" if f.get("is_activist") else "No"
        # Skip rows where filer is the company itself (not useful)
        if filer.upper().startswith(("NVIDIA", "—")) and not f.get("reporting_owner"):
            continue
        lines.append(f"| {filer} | {form} | {filed} | {activist} |")
    lines.append("")

    return lines


def render_enforcement_markdown(data: Dict[str, Any]) -> List[str]:
    """Render SEC Enforcement Actions section."""
    lines = []
    actions = data.get("actions", [])
    if not actions and not data.get("error"):
        return []

    lines.append("### SEC Enforcement Actions")
    lines.append("")

    if data.get("error"):
        lines.append(f"*Data unavailable: {data['error']}*")
        lines.append("")
        return lines

    if not actions:
        lines.append("No SEC enforcement actions found for this entity.")
        lines.append("")
        return lines

    lines.append(f"**{len(actions)} enforcement action(s) found:**")
    lines.append("")

    for a in actions:
        date = (a.get("date") or "")[:10]
        title = a.get("title") or "Untitled"
        atype = a.get("type") or ""
        lines.append(f"**{date}** — {title}")
        if atype:
            lines.append(f"*Type: {atype}*")
        desc = a.get("description", "")
        if desc:
            lines.append(f"> {desc[:300]}")
        lines.append("")

    return lines


def render_insider_structured_markdown(data: Dict[str, Any]) -> List[str]:
    """Render structured insider trading from SEC-API."""
    lines = []
    txns = data.get("transactions", [])
    if not txns and not data.get("error"):
        return []

    # Filter out transactions with no meaningful data (just holdings "H" with no price/value)
    meaningful_txns = [
        tx for tx in txns
        if (tx.get("price") or tx.get("value") or tx.get("shares"))
        and tx.get("transaction_type") not in ("H", None, "")
    ]

    # If we only have holdings with no price data, skip the section entirely
    buys = data.get("total_buys", 0)
    sells = data.get("total_sells", 0)
    net_val = data.get("net_value", 0)

    if not meaningful_txns and buys == 0 and sells == 0 and net_val == 0:
        return []  # Nothing useful to show

    lines.append("### Insider Trading Detail (Structured)")
    lines.append("")

    if data.get("error"):
        lines.append(f"*Data unavailable: {data['error']}*")
        lines.append("")
        return lines

    lines.append(f"**{len(meaningful_txns)} transactions** — {buys} buys, {sells} sells "
                 f"| Net value: ${net_val:,.0f}")
    lines.append("")

    # Top sellers
    sellers = data.get("top_sellers", [])
    if sellers:
        lines.append("**Top Sellers:**")
        for s in sellers[:5]:
            lines.append(f"- {s['name']}: ${s['net_value']:,.0f}")
        lines.append("")

    # Top buyers
    buyers = data.get("top_buyers", [])
    if buyers:
        lines.append("**Top Buyers:**")
        for b in buyers[:5]:
            lines.append(f"- {b['name']}: ${b['net_value']:,.0f}")
        lines.append("")

    # Recent transactions (only show ones with actual data)
    if meaningful_txns:
        lines.append("| Date | Insider | Title | Type | Shares | Price | Value | 10b5-1? |")
        lines.append("|------|---------|-------|------|--------|-------|-------|---------|")
        for tx in meaningful_txns[:25]:
            date = (tx.get("transaction_date") or "")[:10]
            name = (tx.get("name") or "—")[:20]
            title = (tx.get("title") or "—")[:15]
            ttype = tx.get("transaction_type") or "—"
            shares = f"{tx['shares']:,.0f}" if tx.get("shares") else "—"
            price = f"${tx['price']:,.2f}" if tx.get("price") else "—"
            value = f"${tx['value']:,.0f}" if tx.get("value") else "—"
            plan = "✅" if tx.get("is_10b5_1") else ""
            lines.append(f"| {date} | {name} | {title} | {ttype} | {shares} | {price} | {value} | {plan} |")
    lines.append("")

    return lines


def render_all_sec_api_markdown(sec_api_data: Dict[str, Any]) -> List[str]:
    """Render all SEC-API data as a unified report section."""
    if not sec_api_data or not sec_api_data.get("available"):
        return []

    lines = []
    lines.append("## SEC Structured Data Intelligence")
    lines.append("")
    lines.append(f"*Source: sec-api.io | Fetched: {sec_api_data.get('fetch_timestamp', 'N/A')[:19]} "
                 f"| API calls used: {sec_api_data.get('api_calls_used', 0)}*")
    lines.append("")

    # Directors (structured)
    directors_data = sec_api_data.get("directors", {})
    if directors_data.get("directors"):
        lines.append("### Board Composition (Structured)")
        lines.append("")
        total = directors_data.get("total_directors", 0)
        ind = directors_data.get("independent_count", 0)
        lines.append(f"**{total} directors** | {ind} independent "
                     f"({ind*100//total if total else 0}%) | "
                     f"Filing: {directors_data.get('filing_date', 'N/A')}")
        lines.append("")
        committees = directors_data.get("committees", {})
        if committees:
            lines.append("**Committees:** " + ", ".join(
                f"{k} ({len(v)})" for k, v in committees.items()))
            lines.append("")
        lines.append("| Director | Age | Class | Since | Independent | Committees |")
        lines.append("|----------|-----|-------|-------|-------------|------------|")
        for d in directors_data["directors"]:
            name = d.get("name", "—")
            age = d.get("age") or "—"
            cls = d.get("director_class") or "—"
            since = d.get("since") or "—"
            ind_flag = "✅" if d.get("is_independent") else "❌"
            comms = ", ".join(d.get("committees", []))
            lines.append(f"| {name} | {age} | {cls} | {since} | {ind_flag} | {comms} |")
        lines.append("")
        # Qualifications summary
        for d in directors_data["directors"][:5]:
            quals = d.get("qualifications", [])
            if quals:
                lines.append(f"**{d['name']}:** {'; '.join(quals[:3])}")
        if any(d.get("qualifications") for d in directors_data["directors"]):
            lines.append("")

    # Form D
    if sec_api_data.get("form_d"):
        lines.extend(render_form_d_markdown(sec_api_data["form_d"]))

    # N-PORT
    if sec_api_data.get("nport"):
        lines.extend(render_nport_markdown(sec_api_data["nport"]))

    # Subsidiaries
    if sec_api_data.get("subsidiaries"):
        lines.extend(render_subsidiaries_markdown(sec_api_data["subsidiaries"]))

    # Executive Compensation
    if sec_api_data.get("executive_compensation"):
        lines.extend(render_executive_comp_markdown(sec_api_data["executive_compensation"]))

    # Beneficial Ownership
    if sec_api_data.get("beneficial_ownership"):
        lines.extend(render_beneficial_ownership_markdown(sec_api_data["beneficial_ownership"]))

    # Insider Trading Structured
    if sec_api_data.get("insider_trading_structured"):
        lines.extend(render_insider_structured_markdown(sec_api_data["insider_trading_structured"]))

    # Enforcement
    if sec_api_data.get("enforcement"):
        lines.extend(render_enforcement_markdown(sec_api_data["enforcement"]))

    return lines
