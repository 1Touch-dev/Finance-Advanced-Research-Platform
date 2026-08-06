"""
Generate Professional Tutorial PDF using WeasyPrint
Matches the project's premium intelligence report design
"""

from weasyprint import HTML, CSS
from datetime import datetime
import base64
import os

DOCS_DIR = os.path.dirname(os.path.abspath(__file__))
SCREENSHOTS_DIR = os.path.join(DOCS_DIR, 'screenshots')

def get_base64_image(filename):
    """Convert image to base64 for embedding in HTML."""
    filepath = os.path.join(SCREENSHOTS_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    return None

def get_premium_css():
    """Premium CSS matching the project's intelligence report design."""
    return """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

@page {
    size: A4;
    margin: 25mm 20mm 25mm 20mm;
    @bottom-center {
        content: "Enterprise Intelligence Platform  •  Tutorial Guide  •  Page " counter(page);
        font-family: 'Inter', -apple-system, sans-serif;
        font-size: 8pt;
        color: #718096;
    }
}

@page :first {
    margin: 0;
    @bottom-center {
        content: none;
    }
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: 10pt;
    line-height: 1.6;
    color: #1a1a2e;
    background: #ffffff;
}

/* Cover Page */
.cover-page {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    min-height: 100vh;
    padding: 60pt 50pt;
    page-break-after: always;
}

.cover-badge {
    display: inline-block;
    background: rgba(201, 162, 39, 0.15);
    border: 1px solid #c9a227;
    color: #c9a227;
    font-size: 8pt;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    padding: 6pt 14pt;
    border-radius: 4pt;
    margin-bottom: 40pt;
}

.cover-title {
    font-size: 42pt;
    font-weight: 800;
    color: #ffffff;
    line-height: 1.1;
    margin-bottom: 20pt;
    letter-spacing: -0.5px;
}

.cover-subtitle {
    font-size: 16pt;
    font-weight: 400;
    color: #a0aec0;
    margin-bottom: 50pt;
    line-height: 1.5;
}

.cover-url-box {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8pt;
    padding: 20pt 25pt;
    margin-bottom: 30pt;
}

.cover-url-label {
    font-size: 8pt;
    font-weight: 700;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    color: #c9a227;
    margin-bottom: 8pt;
}

.cover-url {
    font-size: 12pt;
    color: #60a5fa;
    word-break: break-all;
}

.cover-credentials {
    background: rgba(74, 222, 128, 0.08);
    border: 1px solid rgba(74, 222, 128, 0.3);
    border-radius: 8pt;
    padding: 20pt 25pt;
    margin-bottom: 60pt;
}

.credentials-title {
    font-size: 11pt;
    font-weight: 700;
    color: #4ade80;
    margin-bottom: 8pt;
}

.credentials-text {
    font-size: 10pt;
    color: #a0aec0;
}

.cover-footer {
    margin-top: auto;
    padding-top: 40pt;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.cover-date {
    font-size: 9pt;
    color: #718096;
}

/* Page Content Wrapper */
.page-content {
    padding: 0;
}

/* Table of Contents */
.toc {
    background: #f8fafc;
    border-radius: 8pt;
    padding: 25pt 30pt;
    margin-bottom: 30pt;
    page-break-after: always;
}

.toc h2 {
    font-size: 16pt;
    font-weight: 700;
    color: #1a1a2e;
    margin-bottom: 20pt;
    padding-bottom: 10pt;
    border-bottom: 2px solid #c9a227;
}

.toc ul {
    list-style: none;
    margin: 0;
    padding: 0;
}

.toc li {
    padding: 6pt 0;
    border-bottom: 1px dotted #e2e8f0;
    font-size: 10pt;
    color: #374151;
}

.toc li ul {
    margin-left: 20pt;
    margin-top: 4pt;
}

.toc li ul li {
    font-size: 9pt;
    color: #6b7280;
    border-bottom: none;
    padding: 3pt 0;
}

/* Section Headers */
h1.section-title {
    font-size: 20pt;
    font-weight: 700;
    color: #1a1a2e;
    margin: 30pt 0 15pt 0;
    padding-bottom: 8pt;
    border-bottom: 2px solid #c9a227;
    page-break-after: avoid;
}

h1.section-title .section-number {
    color: #c9a227;
    margin-right: 10pt;
}

h2.subsection-title {
    font-size: 14pt;
    font-weight: 600;
    color: #2c5282;
    margin: 20pt 0 10pt 0;
    page-break-after: avoid;
}

h3 {
    font-size: 11pt;
    font-weight: 600;
    color: #374151;
    margin: 15pt 0 8pt 0;
}

p {
    margin-bottom: 10pt;
    text-align: justify;
}

/* Feature Box - Blue accent */
.feature-box {
    background: #f0f9ff;
    border-left: 3pt solid #3182ce;
    padding: 12pt 15pt;
    margin: 12pt 0;
    border-radius: 0 6pt 6pt 0;
    page-break-inside: avoid;
}

.feature-box h4 {
    font-size: 10pt;
    font-weight: 700;
    color: #2b6cb0;
    margin-bottom: 6pt;
}

.feature-box p, .feature-box li {
    font-size: 9.5pt;
    color: #374151;
    margin-bottom: 4pt;
}

/* Step Box - Orange accent */
.step-box {
    background: #fffbeb;
    border: 1pt solid #fbbf24;
    border-radius: 6pt;
    padding: 12pt 15pt;
    margin: 12pt 0;
    page-break-inside: avoid;
}

.step-box h4 {
    font-size: 10pt;
    font-weight: 700;
    color: #b45309;
    margin-bottom: 8pt;
}

.step-box ol {
    margin-left: 18pt;
    font-size: 9.5pt;
}

.step-box li {
    margin-bottom: 5pt;
    color: #374151;
}

/* Tip Box - Teal accent */
.tip-box {
    background: #f0fdfa;
    border: 1pt solid #14b8a6;
    border-radius: 6pt;
    padding: 10pt 15pt;
    margin: 12pt 0;
    font-size: 9.5pt;
    color: #134e4a;
    page-break-inside: avoid;
}

.tip-box::before {
    content: "💡 TIP: ";
    font-weight: 700;
}

/* Screenshot Container */
.screenshot-container {
    background: #f8fafc;
    border: 1pt solid #e2e8f0;
    border-radius: 8pt;
    padding: 12pt;
    margin: 15pt 0;
    text-align: center;
    page-break-inside: avoid;
}

.screenshot-container h4 {
    font-size: 9pt;
    font-weight: 600;
    color: #64748b;
    margin-bottom: 10pt;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.screenshot-container img {
    max-width: 100%;
    height: auto;
    border: 1pt solid #cbd5e0;
    border-radius: 6pt;
    box-shadow: 0 2pt 8pt rgba(0, 0, 0, 0.08);
}

/* Tables */
table {
    width: 100%;
    border-collapse: collapse;
    margin: 15pt 0;
    font-size: 9pt;
}

th {
    background: #1a1a2e;
    color: #ffffff;
    font-weight: 600;
    text-align: left;
    padding: 10pt 12pt;
}

td {
    border-bottom: 1pt solid #e2e8f0;
    padding: 8pt 12pt;
    color: #374151;
}

tr:nth-child(even) {
    background: #f8fafc;
}

/* Lists */
ul {
    margin-left: 18pt;
    margin-bottom: 10pt;
}

li {
    margin-bottom: 4pt;
    font-size: 9.5pt;
}

/* Quick Links */
.quick-links {
    display: flex;
    flex-wrap: wrap;
    gap: 6pt;
    margin: 10pt 0;
}

.quick-link {
    display: inline-block;
    background: #eff6ff;
    color: #2563eb;
    padding: 4pt 12pt;
    border-radius: 12pt;
    font-size: 9pt;
    font-weight: 500;
}

/* Page breaks */
.page-break {
    page-break-after: always;
}

/* Footer styling */
.doc-footer {
    margin-top: 40pt;
    padding-top: 20pt;
    border-top: 1pt solid #e2e8f0;
    text-align: center;
    color: #718096;
    font-size: 9pt;
}

/* Data Sources Grid */
.data-sources {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 8pt;
    margin: 12pt 0;
}

.data-source-item {
    background: #f8fafc;
    padding: 8pt 12pt;
    border-radius: 4pt;
    font-size: 9pt;
}

.data-source-item strong {
    color: #1a1a2e;
}
"""

def generate_html():
    """Generate the full HTML content for the tutorial."""

    # Load screenshots as base64
    screenshots = {}
    for name in ['dashboard', 'stock', 'valuation', 'company', 'intelligence',
                 'search', 'institutional', 'gov-trading', 'crypto', 'graph', 'tracking']:
        b64 = get_base64_image(f'{name}.png')
        if b64:
            screenshots[name] = f'data:image/png;base64,{b64}'
        else:
            screenshots[name] = ''

    today = datetime.now().strftime('%B %Y')

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Enterprise Intelligence Platform - Tutorial Guide</title>
</head>
<body>

<!-- COVER PAGE -->
<div class="cover-page">
    <div class="cover-badge">User Tutorial & Quick Start Guide</div>
    <h1 class="cover-title">Enterprise Intelligence Platform</h1>
    <p class="cover-subtitle">Comprehensive financial research and analytics combining market data, intelligence reporting, institutional tracking, and government trading monitoring.</p>

    <div class="cover-url-box">
        <div class="cover-url-label">Platform URL</div>
        <div class="cover-url">https://8th-july-sprint.d11ri08de55gmb.amplifyapp.com</div>
    </div>

    <div class="cover-credentials">
        <div class="credentials-title">✓ Access Credentials</div>
        <div class="credentials-text"><strong>No login required</strong> — The platform is currently open access. Simply visit the URL to get started.</div>
    </div>

    <div class="cover-footer">
        <div class="cover-date">Document Version 1.0  •  {today}</div>
    </div>
</div>

<!-- TABLE OF CONTENTS -->
<div class="toc">
    <h2>Table of Contents</h2>
    <ul>
        <li><strong>1.</strong> Platform Overview</li>
        <li><strong>2.</strong> Getting Started</li>
        <li><strong>3.</strong> Markets Section
            <ul>
                <li>3.1 Stock Analysis</li>
                <li>3.2 Valuation (DCF)</li>
                <li>3.3 Expert Analysis</li>
                <li>3.4 Company Profiles</li>
                <li>3.5 Compare Tool</li>
                <li>3.6 Economics Data</li>
            </ul>
        </li>
        <li><strong>4.</strong> Intelligence Section
            <ul>
                <li>4.1 Deep Intelligence Reports</li>
                <li>4.2 Global Search</li>
                <li>4.3 Saved Reports</li>
                <li>4.4 Timeline View</li>
            </ul>
        </li>
        <li><strong>5.</strong> Institutional Section
            <ul>
                <li>5.1 Institutional Holdings (13F)</li>
                <li>5.2 Government Trading</li>
                <li>5.3 Crypto Intelligence</li>
            </ul>
        </li>
        <li><strong>6.</strong> Tools & Utilities
            <ul>
                <li>6.1 Entity Registry</li>
                <li>6.2 Relationship Graph</li>
                <li>6.3 Tracking & Alerts</li>
            </ul>
        </li>
        <li><strong>7.</strong> Quick Reference Guide</li>
    </ul>
</div>

<div class="page-content">

<!-- SECTION 1 -->
<h1 class="section-title"><span class="section-number">1</span>Platform Overview</h1>

<p>The Enterprise Intelligence Platform is a comprehensive financial research and analytics system that combines market data, intelligence reporting, institutional tracking, and government trading monitoring into a single unified interface.</p>

<div class="screenshot-container">
    <h4>Main Dashboard</h4>
    <img src="{screenshots['dashboard']}" alt="Dashboard">
</div>

<div class="feature-box">
    <h4>Platform Statistics</h4>
    <ul>
        <li><strong>50+ Articles</strong> — Ingested from multiple sources</li>
        <li><strong>15+ RSS Sources</strong> — Live data feeds active</li>
        <li><strong>60+ Entities</strong> — Tracked and monitored</li>
        <li><strong>20+ API Endpoints</strong> — For programmatic access</li>
    </ul>
</div>

<h3>Data Sources</h3>
<p>The platform aggregates data from multiple authoritative sources:</p>

<div class="data-sources">
    <div class="data-source-item"><strong>SEC</strong> — Securities filings, 10-K, 10-Q, 13F</div>
    <div class="data-source-item"><strong>FEC</strong> — Federal Election Commission data</div>
    <div class="data-source-item"><strong>FARA</strong> — Foreign Agents Registration Act</div>
    <div class="data-source-item"><strong>USASpending</strong> — Government contracts</div>
    <div class="data-source-item"><strong>LDA</strong> — Lobbying Disclosure Act (both sides)</div>
    <div class="data-source-item"><strong>OFAC</strong> — Sanctions data</div>
    <div class="data-source-item"><strong>CourtListener</strong> — Legal cases</div>
    <div class="data-source-item"><strong>LinkedIn & PitchBook</strong> — Via Apify integrations</div>
    <div class="data-source-item"><strong>Google News</strong> — Current events coverage</div>
    <div class="data-source-item"><strong>CoinGecko</strong> — Cryptocurrency data</div>
</div>

<div class="page-break"></div>

<!-- SECTION 2 -->
<h1 class="section-title"><span class="section-number">2</span>Getting Started</h1>

<div class="step-box">
    <h4>Quick Start Steps</h4>
    <ol>
        <li>Open your web browser (Chrome, Firefox, Safari, or Edge recommended)</li>
        <li>Navigate to: <strong>https://8th-july-sprint.d11ri08de55gmb.amplifyapp.com</strong></li>
        <li>The dashboard will load automatically — no login required</li>
        <li>Use the navigation menu on the left side to access different sections</li>
    </ol>
</div>

<h3>Navigation Structure</h3>
<p>The platform is organized into these main sections accessible from the left sidebar:</p>

<table>
    <tr><th>Section</th><th>Description</th></tr>
    <tr><td><strong>Dashboard</strong></td><td>Main entry point with system status overview</td></tr>
    <tr><td><strong>Reports</strong></td><td>Generate deep intelligence dossiers on entities</td></tr>
    <tr><td><strong>Global Search</strong></td><td>Search across all articles and reports</td></tr>
    <tr><td><strong>Saved</strong></td><td>Access your archived intelligence reports</td></tr>
    <tr><td><strong>Timeline</strong></td><td>View chronological signal history</td></tr>
    <tr><td><strong>Markets</strong></td><td>Stock, Valuation, Expert Analysis, Company, Compare, Economics</td></tr>
    <tr><td><strong>Institutional</strong></td><td>13F holdings, Government Trading, Crypto</td></tr>
    <tr><td><strong>Tools</strong></td><td>Registry, Graph, Tracking, Alerts, Skills</td></tr>
</table>

<div class="page-break"></div>

<!-- SECTION 3 -->
<h1 class="section-title"><span class="section-number">3</span>Markets Section</h1>

<p>The Markets section provides comprehensive financial analysis tools for stocks, valuations, and economic data.</p>

<h2 class="subsection-title">3.1 Stock Analysis</h2>

<div class="feature-box">
    <h4>What It Does</h4>
    <p>Analyze any publicly traded stock with fundamentals, technicals, AI consensus, and analyst ratings.</p>
</div>

<div class="screenshot-container">
    <h4>Stock Analysis Interface</h4>
    <img src="{screenshots['stock']}" alt="Stock Analysis">
</div>

<div class="step-box">
    <h4>How to Use Stock Analysis</h4>
    <ol>
        <li>Click <strong>"Stock"</strong> in the Markets section of the sidebar</li>
        <li>Enter a ticker symbol in the search box (e.g., AAPL, MSFT, TSLA)</li>
        <li>Or click one of the quick-access buttons: AAPL, MSFT, TSLA, NVDA, AMZN, GOOGL, META, BRK-B</li>
        <li>View the analysis including price data, technical indicators, and AI-powered insights</li>
    </ol>
</div>

<p><strong>Supported Exchanges:</strong> NYSE, NASDAQ, and global exchange symbols</p>

<h2 class="subsection-title">3.2 Valuation (DCF Analysis)</h2>

<div class="feature-box">
    <h4>What It Does</h4>
    <p>Calculate intrinsic value using Discounted Cash Flow (DCF) analysis with SEC filing data. Compare fair value estimates against current market prices.</p>
</div>

<div class="screenshot-container">
    <h4>DCF Valuation Tool</h4>
    <img src="{screenshots['valuation']}" alt="Valuation">
</div>

<div class="step-box">
    <h4>How to Use Valuation Tool</h4>
    <ol>
        <li>Click <strong>"Valuation"</strong> in the Markets section</li>
        <li>Enter a stock ticker symbol</li>
        <li>The system automatically pulls SEC EDGAR XBRL financials</li>
        <li>View DCF intrinsic value, bull/bear scenarios, and price comparison</li>
    </ol>
</div>

<div class="tip-box">Use this tool to identify potentially undervalued or overvalued stocks by comparing calculated intrinsic value to market price.</div>

<div class="page-break"></div>

<h2 class="subsection-title">3.3 Expert Analysis</h2>

<div class="feature-box">
    <h4>What It Does</h4>
    <p>View aggregated analyst ratings and sentiment trends from Wall Street experts.</p>
</div>

<div class="step-box">
    <h4>How to Use Expert Analysis</h4>
    <ol>
        <li>Click <strong>"Expert Analysis"</strong> in the Markets section</li>
        <li>Enter a ticker symbol</li>
        <li>Review analyst recommendations (Buy/Hold/Sell)</li>
        <li>See price targets and sentiment trends over time</li>
    </ol>
</div>

<h2 class="subsection-title">3.4 Company Profiles</h2>

<div class="feature-box">
    <h4>What It Does</h4>
    <p>Deep dive into any public company with SEC filings, cap table data, earnings history, and insider trading activity.</p>
</div>

<div class="screenshot-container">
    <h4>Company Profile Interface</h4>
    <img src="{screenshots['company']}" alt="Company">
</div>

<div class="step-box">
    <h4>How to Use Company Profiles</h4>
    <ol>
        <li>Click <strong>"Company"</strong> in the Markets section</li>
        <li>Enter a stock ticker symbol</li>
        <li>Click <strong>"Deep Analyze"</strong></li>
        <li>Browse through SEC filings, financial data, cap table, and earnings history</li>
    </ol>
</div>

<p><strong>Available Information:</strong> SEC quarterly reports (10-K/10-Q), XBRL financials, cap table and ownership structure, earnings history, analyst ratings, insider trades.</p>

<h2 class="subsection-title">3.5 Compare Tool</h2>

<div class="feature-box">
    <h4>What It Does</h4>
    <p>Side-by-side comparison of multiple entities for competitive analysis.</p>
</div>

<h2 class="subsection-title">3.6 Economics Data</h2>

<div class="feature-box">
    <h4>What It Does</h4>
    <p>Access macroeconomic data including GDP, CPI, interest rates, and FRED data.</p>
</div>

<div class="page-break"></div>

<!-- SECTION 4 -->
<h1 class="section-title"><span class="section-number">4</span>Intelligence Section</h1>

<p>The Intelligence section is the core of the platform, providing deep research capabilities and comprehensive entity dossiers.</p>

<h2 class="subsection-title">4.1 Deep Intelligence Reports</h2>

<div class="feature-box">
    <h4>What It Does</h4>
    <p>Generate comprehensive 50-100+ page dossiers on any entity by aggregating data from 12+ sources including SEC, FEC, FARA, USASpending, court records, and more.</p>
</div>

<div class="screenshot-container">
    <h4>Intelligence Reports Generator</h4>
    <img src="{screenshots['intelligence']}" alt="Intelligence">
</div>

<div class="step-box">
    <h4>How to Generate a Report</h4>
    <ol>
        <li>Click <strong>"Reports"</strong> in the navigation (or go to /intelligence)</li>
        <li>Choose a search method: Pre-built Networks, Entity Search, or With Ticker</li>
        <li>Select entity type: Organization, Individual, Fund, or Government Agency</li>
        <li>Click generate and wait 30-90 seconds for processing</li>
        <li>Review the comprehensive report with clickable entity references</li>
    </ol>
</div>

<p><strong>Report Includes:</strong> Investment thesis, SWOT analysis, risk matrices, financial assessment, LinkedIn education profiles, funding histories (PitchBook), current news coverage, lobbying data, government contracts, court cases.</p>

<div class="tip-box">Click on any entity name within a report to drill down and generate a new report on that entity.</div>

<h2 class="subsection-title">4.2 Global Search</h2>

<div class="screenshot-container">
    <h4>Global Search Interface</h4>
    <img src="{screenshots['search']}" alt="Search">
</div>

<div class="step-box">
    <h4>How to Use Global Search</h4>
    <ol>
        <li>Click <strong>"Global Search"</strong> in the navigation</li>
        <li>Enter search terms: entity names, tickers, keywords, or document terms</li>
        <li>Or use quick search buttons: Apple, Palantir, SpaceX, Microsoft, Defense, BlackRock, Tesla</li>
        <li>Browse results organized by Entities, Relationships, and Evidence records</li>
    </ol>
</div>

<div class="page-break"></div>

<!-- SECTION 5 -->
<h1 class="section-title"><span class="section-number">5</span>Institutional Section</h1>

<p>Track major institutional investors, government officials' trades, and cryptocurrency markets.</p>

<h2 class="subsection-title">5.1 Institutional Holdings (13F)</h2>

<div class="feature-box">
    <h4>What It Does</h4>
    <p>Research major institutional investors' portfolios using SEC 13F filings. Track positions of hedge funds, mutual funds, and investment managers.</p>
</div>

<div class="screenshot-container">
    <h4>Institutional Holdings Interface</h4>
    <img src="{screenshots['institutional']}" alt="Institutional">
</div>

<div class="step-box">
    <h4>How to Use Institutional Holdings</h4>
    <ol>
        <li>Click <strong>"Institutional"</strong> in the sidebar</li>
        <li>Enter a ticker symbol to see who holds that stock</li>
        <li>Or select an institution from the dropdown (Berkshire, BlackRock, Vanguard, etc.)</li>
        <li>Browse through tabs: Institutional Holders, Mutual Funds, Mega Positions, 13F Filers</li>
    </ol>
</div>

<h2 class="subsection-title">5.2 Government Trading</h2>

<div class="feature-box">
    <h4>What It Does</h4>
    <p>Monitor congressional trading activity under the STOCK Act, corporate insider trades (SEC Form 4), and track individual politicians' financial dealings.</p>
</div>

<div class="screenshot-container">
    <h4>Government Trading Monitor</h4>
    <img src="{screenshots['gov-trading']}" alt="Gov Trading">
</div>

<div class="step-box">
    <h4>How to Use Government Trading</h4>
    <ol>
        <li>Click <strong>"Gov Trading"</strong> in the sidebar</li>
        <li>Browse: Congressional Summary, Corporate Insider Trades, Politician Tracker</li>
        <li>Use time filters: Last 30/60/90 days, or Last 6 months</li>
        <li>Click on any trade for details</li>
    </ol>
</div>

<div class="tip-box">Use this feature to spot potential market-moving trades by government officials or corporate insiders.</div>

<div class="page-break"></div>

<h2 class="subsection-title">5.3 Crypto Intelligence</h2>

<div class="feature-box">
    <h4>What It Does</h4>
    <p>Monitor cryptocurrency markets with live CoinGecko data, wallet tracking, and whale alerts.</p>
</div>

<div class="screenshot-container">
    <h4>Crypto Intelligence Dashboard</h4>
    <img src="{screenshots['crypto']}" alt="Crypto">
</div>

<div class="step-box">
    <h4>How to Use Crypto Intelligence</h4>
    <ol>
        <li>Click <strong>"Crypto"</strong> in the sidebar</li>
        <li>Browse tabs: Dashboard, Coin Detail, Wallet Lookup</li>
        <li>Monitor whale alerts for large transactions</li>
    </ol>
</div>

<div class="page-break"></div>

<!-- SECTION 6 -->
<h1 class="section-title"><span class="section-number">6</span>Tools & Utilities</h1>

<p>Advanced tools for entity management, relationship mapping, and automated monitoring.</p>

<h2 class="subsection-title">6.1 Entity Registry</h2>

<div class="feature-box">
    <h4>What It Does</h4>
    <p>OSINT enrichment and private intelligence repository for managing entity data.</p>
</div>

<h2 class="subsection-title">6.2 Relationship Graph</h2>

<div class="feature-box">
    <h4>What It Does</h4>
    <p>Interactive network visualization showing relationships between entities. Features expand-on-click, zoom/pan, and export capabilities.</p>
</div>

<div class="screenshot-container">
    <h4>Relationship Graph Visualization</h4>
    <img src="{screenshots['graph']}" alt="Graph">
</div>

<div class="step-box">
    <h4>How to Use the Graph</h4>
    <ol>
        <li>Click <strong>"Graph"</strong> in the Tools section</li>
        <li>Enter an entity ID and click <strong>"Expand Graph"</strong></li>
        <li>Click nodes to expand, scroll to zoom, drag to pan</li>
        <li>Export as JSON or PNG when ready</li>
    </ol>
</div>

<h2 class="subsection-title">6.3 Tracking & Alerts</h2>

<div class="feature-box">
    <h4>What It Does</h4>
    <p>Entity monitoring system (v2.0) that tracks changes in contracts, lobbying, court cases, and more. Supports automated daily digests with email and SMS alerts.</p>
</div>

<div class="screenshot-container">
    <h4>Tracking & Alerts Dashboard</h4>
    <img src="{screenshots['tracking']}" alt="Tracking">
</div>

<div class="step-box">
    <h4>How to Set Up Tracking</h4>
    <ol>
        <li>Click <strong>"Tracking"</strong> in the Tools section</li>
        <li>Add entities to your watchlist (manual entry or quick-add suggestions)</li>
        <li>Select entity type: Organization or Person</li>
        <li>View watchlist dashboard showing entities monitored and digest history</li>
    </ol>
</div>

<p><strong>Automated Alerts:</strong> The system runs automatically at 6:00 AM UTC daily, re-generating reports for all watched entities and sending notifications for any changes detected via Email (SendGrid) or SMS (Twilio).</p>

<div class="page-break"></div>

<!-- SECTION 7 -->
<h1 class="section-title"><span class="section-number">7</span>Quick Reference Guide</h1>

<h3>Navigation Shortcuts</h3>
<table>
    <tr><th>Feature</th><th>URL Path</th><th>Purpose</th></tr>
    <tr><td>Dashboard</td><td>/</td><td>Main overview</td></tr>
    <tr><td>Reports</td><td>/intelligence</td><td>Generate dossiers</td></tr>
    <tr><td>Global Search</td><td>/search</td><td>Search everything</td></tr>
    <tr><td>Stock Analysis</td><td>/stock</td><td>Analyze stocks</td></tr>
    <tr><td>Valuation</td><td>/valuation</td><td>DCF analysis</td></tr>
    <tr><td>Company</td><td>/company</td><td>Company profiles</td></tr>
    <tr><td>Institutional</td><td>/institutional</td><td>13F holdings</td></tr>
    <tr><td>Gov Trading</td><td>/gov-trading</td><td>Political trades</td></tr>
    <tr><td>Crypto</td><td>/crypto</td><td>Crypto markets</td></tr>
    <tr><td>Graph</td><td>/graph</td><td>Relationship mapping</td></tr>
    <tr><td>Tracking</td><td>/tracking</td><td>Entity monitoring</td></tr>
</table>

<h3>Quick Ticker Access</h3>
<div class="quick-links">
    <span class="quick-link">AAPL</span>
    <span class="quick-link">MSFT</span>
    <span class="quick-link">TSLA</span>
    <span class="quick-link">NVDA</span>
    <span class="quick-link">AMZN</span>
    <span class="quick-link">GOOGL</span>
    <span class="quick-link">META</span>
    <span class="quick-link">BRK-B</span>
</div>

<h3>Pre-Built Network Reports</h3>
<ul>
    <li>PayPal Mafia</li>
    <li>Thiel Network</li>
    <li>AI/Defense Networks</li>
</ul>

<h3>Major Institutions Tracked</h3>
<p>Berkshire Hathaway, BlackRock, Vanguard, State Street, Fidelity, T. Rowe Price, JP Morgan, Goldman Sachs, Morgan Stanley, Cathie Wood / ARK, Pershing Square</p>

<div class="feature-box">
    <h4>Need Help?</h4>
    <p>The platform includes API documentation for programmatic access. Look for the "API Docs" link in the navigation for detailed endpoint information.</p>
</div>

<div class="doc-footer">
    <strong>Enterprise Intelligence Platform</strong><br>
    Tutorial Document v1.0  •  {today}<br><br>
    Platform URL: https://8th-july-sprint.d11ri08de55gmb.amplifyapp.com
</div>

</div>
</body>
</html>
"""
    return html


def generate_pdf():
    """Generate the professional PDF using WeasyPrint."""
    print("Generating professional tutorial PDF...")

    html_content = generate_html()
    css = get_premium_css()

    output_path = os.path.join(DOCS_DIR, 'Enterprise-Intelligence-Platform-Tutorial.pdf')

    # Generate PDF with WeasyPrint
    html_doc = HTML(string=html_content, base_url=DOCS_DIR)
    css_doc = CSS(string=css)

    html_doc.write_pdf(output_path, stylesheets=[css_doc])

    file_size = os.path.getsize(output_path) / 1024
    print(f"✓ PDF generated: {output_path}")
    print(f"  Size: {file_size:.1f} KB")

    return output_path


if __name__ == '__main__':
    generate_pdf()
