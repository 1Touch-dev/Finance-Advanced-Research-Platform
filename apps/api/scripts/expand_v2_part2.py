
# ============ CHART GENERATION ============

def generate_charts(company_data: Dict, people: List) -> Dict[str, str]:
    """Generate matplotlib charts as base64 PNGs."""
    charts = {}
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        logger.warning("matplotlib not available")
        return charts

    # Chart 1: Market Cap comparison
    fig, ax = plt.subplots(figsize=(10, 5))
    tickers = []
    caps = []
    for t, d in company_data.items():
        mc = d.get("financials", {}).get("market_cap", 0)
        if mc:
            tickers.append(t)
            caps.append(mc / 1e9)
    if tickers:
        bars = ax.bar(tickers, caps, color=["#1e40af", "#2563eb", "#3b82f6", "#60a5fa", "#93c5fd", "#bfdbfe", "#dbeafe", "#eff6ff"][:len(tickers)])
        ax.set_ylabel("Market Cap ($B)")
        ax.set_title("PayPal Mafia Portfolio — Market Capitalization")
        ax.bar_label(bars, fmt="$%.0fB", fontsize=8)
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=150)
        charts["market_cap"] = base64.b64encode(buf.getvalue()).decode()
        plt.close()

    # Chart 2: P/E Ratios
    fig, ax = plt.subplots(figsize=(9, 4))
    pe_tickers = []
    pe_vals = []
    for t, d in company_data.items():
        pe = d.get("financials", {}).get("pe_ttm")
        if pe and isinstance(pe, (int, float)) and pe > 0:
            pe_tickers.append(t)
            pe_vals.append(pe)
    if pe_tickers:
        colors = ["#dc2626" if p > 50 else "#f59e0b" if p > 25 else "#16a34a" for p in pe_vals]
        ax.barh(pe_tickers, pe_vals, color=colors)
        ax.set_xlabel("P/E Ratio (TTM)")
        ax.set_title("Valuation Comparison — P/E Ratios")
        ax.axvline(x=25, color="gray", linestyle="--", alpha=0.5)
        ax.text(25.5, -0.5, "S&P 500 avg", fontsize=7, color="gray")
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=150)
        charts["pe_ratio"] = base64.b64encode(buf.getvalue()).decode()
        plt.close()

    # Chart 3: Government contracts comparison
    fig, ax = plt.subplots(figsize=(9, 4))
    contract_tickers = []
    contract_vals = []
    for t, d in company_data.items():
        c = d.get("contracts", {})
        total = c.get("total_obligations") or c.get("total_value", 0)
        if total and float(total) > 0:
            contract_tickers.append(t)
            contract_vals.append(float(total) / 1e6)
    if contract_tickers:
        ax.bar(contract_tickers, contract_vals, color="#059669")
        ax.set_ylabel("Total Obligations ($M)")
        ax.set_title("Government Contract Awards — PayPal Mafia Companies")
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=150)
        charts["contracts"] = base64.b64encode(buf.getvalue()).decode()
        plt.close()

    # Chart 4: Network connections per person
    fig, ax = plt.subplots(figsize=(10, 5))
    names = [p["name"].split()[-1] for p in people]
    connections = [len(p.get("companies", [])) + len(p.get("funds", [])) for p in people]
    ax.barh(names, connections, color="#7c3aed")
    ax.set_xlabel("Number of Companies/Funds")
    ax.set_title("Network Density — Connections Per Person")
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150)
    charts["network_density"] = base64.b64encode(buf.getvalue()).decode()
    plt.close()

    # Chart 5: Sector distribution pie
    fig, ax = plt.subplots(figsize=(7, 7))
    sectors = defaultdict(int)
    for t, info in COMPANIES_FULL.items():
        if t in company_data:
            mc = company_data[t].get("financials", {}).get("market_cap", 0)
            if mc:
                sector = info.get("sector", "Other").split("/")[0].strip()
                sectors[sector] += mc
    if sectors:
        labels = list(sectors.keys())
        sizes = [v/1e9 for v in sectors.values()]
        colors_pie = plt.cm.Set3(range(len(labels)))
        ax.pie(sizes, labels=labels, autopct="%1.1f%%", colors=colors_pie, startangle=90)
        ax.set_title("Portfolio Sector Distribution (by Market Cap)")
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=150)
        charts["sector_pie"] = base64.b64encode(buf.getvalue()).decode()
        plt.close()

    # Chart 6: Beta risk profile
    fig, ax = plt.subplots(figsize=(8, 4))
    beta_tickers = []
    beta_vals = []
    for t, d in company_data.items():
        b = d.get("financials", {}).get("beta")
        if b and isinstance(b, (int, float)):
            beta_tickers.append(t)
            beta_vals.append(b)
    if beta_tickers:
        colors = ["#dc2626" if b > 1.5 else "#f59e0b" if b > 1 else "#16a34a" for b in beta_vals]
        ax.bar(beta_tickers, beta_vals, color=colors)
        ax.axhline(y=1.0, color="gray", linestyle="--", alpha=0.7)
        ax.set_ylabel("Beta")
        ax.set_title("Risk Profile — Portfolio Beta Values")
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=150)
        charts["beta"] = base64.b64encode(buf.getvalue()).decode()
        plt.close()

    logger.info(f"Generated {len(charts)} charts")
    return charts
