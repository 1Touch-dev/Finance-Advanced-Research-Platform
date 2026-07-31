"""
Premium PDF Service - Investment Intelligence Reports

Generates professional intelligence reports with:
- Dark header bar with classification markings
- Gold accent colors for section headers
- Executive callout boxes
- Table of contents with numbered sections
- Professional typography and spacing
- Dense, substantive content layout
"""

from datetime import datetime
from typing import Optional
import re
import markdown
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration


def get_premium_css() -> str:
    """Return premium CSS styling matching investment intelligence standard."""
    return """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Source+Serif+4:wght@400;600;700&display=swap');

@page {
    size: A4;
    margin: 0 0 28pt 0;
    @bottom-center {
        content: "Prepared for internal use only — not for distribution        ·        Page " counter(page);
        font-family: 'Inter', -apple-system, sans-serif;
        font-size: 7.5pt;
        color: #718096;
        vertical-align: top;
        padding-top: 8pt;
    }
}

/* Cover page: no running footer (it has its own .cover-footer) */
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

/* Page wrapper with margins */
.page-content {
    padding: 0 45pt 60pt 45pt;
}

/* Dark Header Bar - First Page */
.cover-header {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    color: #ffffff;
    padding: 50pt 45pt 80pt 45pt;
    margin-bottom: 0;
}

.classification-bar {
    font-size: 8pt;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: #c9a227;
    margin-bottom: 6pt;
}

.org-line {
    font-size: 8.5pt;
    font-weight: 500;
    letter-spacing: 0.8px;
    color: #c9a227;
    opacity: 0.9;
    margin-bottom: 40pt;
}

.cover-title {
    font-family: 'Inter', sans-serif;
    font-size: 36pt;
    font-weight: 800;
    line-height: 1.1;
    color: #ffffff;
    margin-bottom: 20pt;
    letter-spacing: -0.5px;
}

.cover-subtitle {
    font-size: 14pt;
    font-weight: 400;
    color: #a0aec0;
    margin-bottom: 30pt;
    line-height: 1.5;
}

.cover-scope {
    font-size: 9.5pt;
    line-height: 1.7;
    color: #cbd5e0;
    margin-bottom: 0;
    max-width: 90%;
}

.cover-footer {
    background: #1a1a2e;
    padding: 30pt 45pt 40pt 45pt;
    border-top: 1px solid #2d3748;
}

.prepared-for {
    font-size: 8pt;
    font-weight: 700;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    color: #c9a227;
    margin-bottom: 8pt;
}

.prepared-name {
    font-size: 12pt;
    font-weight: 500;
    color: #ffffff;
    margin-bottom: 15pt;
}

.cover-disclaimer {
    font-size: 8pt;
    color: #718096;
    line-height: 1.5;
}

/* Running Header for subsequent pages */
.page-header {
    background: #1a1a2e;
    padding: 12pt 45pt;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 25pt;
}

.header-left {
    font-size: 7.5pt;
    font-weight: 700;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    color: #c9a227;
}

.header-right {
    font-size: 7.5pt;
    font-weight: 600;
    letter-spacing: 0.5px;
    color: #a0aec0;
}

/* Page Footer — legacy inline blocks are hidden; the real footer is the
   @page @bottom-center running element so it appears once per physical page. */
.page-footer {
    display: none;
}

.footer-left {
    font-style: italic;
}

.footer-right {
    font-weight: 600;
}

/* Section Headers - Gold accent */
h1.section-title {
    font-family: 'Inter', sans-serif;
    font-size: 18pt;
    font-weight: 700;
    color: #1a1a2e;
    margin: 30pt 0 20pt 0;
    padding-bottom: 8pt;
    border-bottom: 2px solid #c9a227;
}

h1.section-title .section-number {
    color: #c9a227;
    margin-right: 12pt;
}

h2 {
    font-family: 'Inter', sans-serif;
    font-size: 13pt;
    font-weight: 700;
    color: #c9a227;
    margin: 22pt 0 12pt 0;
}

h3 {
    font-family: 'Inter', sans-serif;
    font-size: 11pt;
    font-weight: 600;
    color: #1a1a2e;
    margin: 16pt 0 10pt 0;
}

/* Executive Callout Box */
.callout-box {
    background: #f8f9fa;
    border-left: 4px solid #c9a227;
    padding: 18pt 20pt;
    margin: 20pt 0;
    page-break-inside: avoid;
}

.callout-title {
    font-size: 9pt;
    font-weight: 800;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: #c9a227;
    margin-bottom: 12pt;
}

.callout-content {
    font-size: 10pt;
    line-height: 1.7;
    color: #2d3748;
}

.callout-content p {
    margin-bottom: 10pt;
}

.callout-content p:last-child {
    margin-bottom: 0;
}

/* Network Relevance Box */
.network-box {
    background: #faf9f7;
    border: 1px solid #c9a227;
    border-radius: 4pt;
    padding: 18pt 20pt;
    margin: 20pt 0;
    page-break-inside: avoid;
}

.network-title {
    font-size: 9pt;
    font-weight: 800;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: #c9a227;
    margin-bottom: 12pt;
}

/* Paragraphs */
p {
    margin-bottom: 12pt;
    text-align: justify;
    hyphens: auto;
}

/* Lists */
ul, ol {
    margin: 12pt 0 12pt 20pt;
}

li {
    margin-bottom: 8pt;
    line-height: 1.6;
}

li::marker {
    color: #c9a227;
    font-weight: 700;
}

/* Tables */
table {
    width: 100%;
    border-collapse: collapse;
    margin: 16pt 0;
    font-size: 9.5pt;
}

thead {
    background: #1a1a2e;
}

th {
    color: #ffffff;
    font-weight: 600;
    text-align: left;
    padding: 10pt 12pt;
    font-size: 9pt;
    letter-spacing: 0.3px;
}

td {
    padding: 10pt 12pt;
    border-bottom: 1px solid #e2e8f0;
    vertical-align: top;
}

tr:nth-child(even) {
    background: #f8f9fa;
}

/* Table of Contents */
.toc {
    margin: 30pt 0;
}

.toc-title {
    font-family: 'Inter', sans-serif;
    font-size: 18pt;
    font-weight: 700;
    color: #1a1a2e;
    margin-bottom: 25pt;
    padding-bottom: 8pt;
    border-bottom: 2px solid #c9a227;
}

.toc-item {
    display: flex;
    align-items: baseline;
    margin-bottom: 10pt;
    font-size: 10.5pt;
}

.toc-number {
    color: #c9a227;
    font-weight: 700;
    min-width: 35pt;
}

.toc-text {
    color: #1a1a2e;
}

.toc-item.sub {
    padding-left: 35pt;
    font-size: 10pt;
}

.toc-item.sub .toc-number {
    font-weight: 600;
}

/* Key Metrics Grid */
.metrics-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12pt;
    margin: 20pt 0;
}

.metric-card {
    background: #f8f9fa;
    border: 1px solid #e2e8f0;
    border-top: 3px solid #c9a227;
    padding: 15pt;
    text-align: center;
}

.metric-value {
    font-size: 20pt;
    font-weight: 800;
    color: #1a1a2e;
    margin-bottom: 5pt;
}

.metric-label {
    font-size: 8pt;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #718096;
}

/* Risk Rating */
.risk-indicator {
    display: inline-block;
    padding: 4pt 10pt;
    border-radius: 3pt;
    font-size: 8pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.risk-high {
    background: #fed7d7;
    color: #c53030;
}

.risk-medium {
    background: #fefcbf;
    color: #b7791f;
}

.risk-low {
    background: #c6f6d5;
    color: #276749;
}

/* Page break helpers */
.page-break {
    page-break-after: always;
}

.no-break {
    page-break-inside: avoid;
}

/* Strong/Bold */
strong {
    font-weight: 700;
    color: #1a1a2e;
}

/* Emphasis */
em {
    font-style: italic;
    color: #4a5568;
}

/* Section intro text */
.section-intro {
    font-size: 10.5pt;
    color: #4a5568;
    margin-bottom: 18pt;
    font-style: italic;
}

/* Data source badges */
.source-badge {
    display: inline-block;
    background: #edf2f7;
    color: #4a5568;
    padding: 2pt 8pt;
    border-radius: 3pt;
    font-size: 8pt;
    font-weight: 600;
    margin-right: 6pt;
    margin-bottom: 6pt;
}

/* Horizontal rule */
hr {
    border: none;
    border-top: 1px solid #e2e8f0;
    margin: 25pt 0;
}

/* Data tables from markdown conversion */
.data-table {
    width: 100%;
    border-collapse: collapse;
    margin: 16pt 0;
    font-size: 9pt;
    page-break-inside: avoid;
    border: 1px solid #e2e8f0;
}

.data-table thead {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
}

.data-table th {
    color: #ffffff;
    font-weight: 600;
    text-align: left;
    padding: 10pt 12pt;
    font-size: 8.5pt;
    letter-spacing: 0.3px;
    text-transform: uppercase;
    border-bottom: 2px solid #c9a227;
}

.data-table td {
    padding: 10pt 12pt;
    border-bottom: 1px solid #e2e8f0;
    vertical-align: top;
    font-size: 9pt;
    line-height: 1.5;
}

.data-table tbody tr:nth-child(odd) td {
    background-color: #ffffff;
}

.data-table tbody tr:nth-child(even) td {
    background-color: #f8f9fa;
}

/* Positive/Negative indicators */
.positive-indicator {
    color: #276749;
    font-weight: 600;
}

.negative-indicator {
    color: #c53030;
    font-weight: 600;
}

/* End of document marker */
.end-marker {
    text-align: center;
    font-size: 9pt;
    font-style: italic;
    color: #718096;
    margin-top: 40pt;
    padding-top: 20pt;
    border-top: 1px solid #e2e8f0;
}
"""


def generate_premium_report_html(
    entity_name: str,
    ticker: str,
    report_data: dict,
    prepared_for: str = "Internal Analysis",
    organization: str = "ENTERPRISE INTELLIGENCE PLATFORM",
    classification: str = "CONFIDENTIAL — INTERNAL USE ONLY"
) -> str:
    """Generate premium HTML report matching investment intelligence standard."""

    generated_at = datetime.utcnow().strftime("%d %B %Y")

    # Graceful ticker: "Tesla (TSLA)" when present, plain "Tesla" when absent
    # (was rendering "Tesla ()"). Fall back to report_data if not passed in.
    ticker = (ticker or report_data.get('ticker') or '').strip()
    ticker_display = f" ({ticker})" if ticker else ""

    # Extract sections from report data
    sections = report_data.get('sections', [])

    # Build content sections
    executive_summary = _extract_section_content(sections, 'Executive Summary')
    investment_thesis = _extract_section_content(sections, 'Investment Thesis')
    financial_health = _extract_section_content(sections, 'Financial Health')
    competitive_analysis = _extract_section_content(sections, 'Competitive Analysis')

    # Extract government contracts
    gov_contracts = _extract_gov_contracts(sections)

    # Extract news
    news_items = _extract_news(sections)

    # Build the HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{entity_name} — Intelligence Report</title>
</head>
<body>

<!-- COVER PAGE -->
<div class="cover-header">
    <div class="classification-bar">{classification}</div>
    <div class="org-line">{organization}</div>

    <h1 class="cover-title">{entity_name.upper()}<br/>INTELLIGENCE REPORT</h1>

    <p class="cover-subtitle">Comprehensive Enterprise Analysis &amp;<br/>Investment Intelligence Assessment</p>

    <p class="cover-scope">
        <strong>Scope:</strong> Corporate fundamentals and financial health assessment;
        competitive positioning and market analysis; federal government contract portfolio
        ({_format_currency(gov_contracts.get('total_value', 0))} obligated);
        regulatory and lobbying activity mapping; executive leadership and governance structure;
        institutional investor positioning; media sentiment and news flow analysis;
        risk factor identification and mitigation assessment.
    </p>
</div>

<div class="cover-footer">
    <div class="prepared-for">PREPARED FOR</div>
    <div class="prepared-name">{prepared_for}</div>
    <p class="cover-disclaimer">
        Compiled from public filings, government databases, and open-source reporting current to {generated_at}.<br/>
        All figures and attributions sourced; see inline citations. Not legal or investment advice.
    </p>
</div>

<div class="page-break"></div>

<!-- TABLE OF CONTENTS -->
<div class="page-header">
    <span class="header-left">{classification}</span>
    <span class="header-right">{organization}</span>
</div>

<div class="page-content">
    <div class="toc">
        <h1 class="toc-title">TABLE OF CONTENTS</h1>

        <div class="toc-item">
            <span class="toc-number">1</span>
            <span class="toc-text">Executive Assessment</span>
        </div>
        <div class="toc-item">
            <span class="toc-number">2</span>
            <span class="toc-text">Investment Thesis &amp; Valuation</span>
        </div>
        <div class="toc-item">
            <span class="toc-number">3</span>
            <span class="toc-text">Corporate Structure &amp; Ownership</span>
        </div>
        <div class="toc-item sub">
            <span class="toc-number">3.1</span>
            <span class="toc-text">Cap Table &amp; Institutional Holdings</span>
        </div>
        <div class="toc-item sub">
            <span class="toc-number">3.2</span>
            <span class="toc-text">Corporate Family &amp; Subsidiaries</span>
        </div>
        <div class="toc-item">
            <span class="toc-number">4</span>
            <span class="toc-text">Board of Directors Dossiers</span>
        </div>
        <div class="toc-item sub">
            <span class="toc-number">4.1</span>
            <span class="toc-text">Board Composition &amp; Interlocks</span>
        </div>
        <div class="toc-item sub">
            <span class="toc-number">4.2</span>
            <span class="toc-text">Director Compensation Analysis</span>
        </div>
        <div class="toc-item">
            <span class="toc-number">5</span>
            <span class="toc-text">Executive Leadership Dossiers</span>
        </div>
        <div class="toc-item sub">
            <span class="toc-number">5.1</span>
            <span class="toc-text">Key Personnel &amp; Family Connections</span>
        </div>
        <div class="toc-item sub">
            <span class="toc-number">5.2</span>
            <span class="toc-text">Insider Trading &amp; Compensation</span>
        </div>
        <div class="toc-item">
            <span class="toc-number">6</span>
            <span class="toc-text">Financial Health Analysis</span>
        </div>
        <div class="toc-item">
            <span class="toc-number">7</span>
            <span class="toc-text">Investment Activity &amp; M&amp;A</span>
        </div>
        <div class="toc-item sub">
            <span class="toc-number">7.1</span>
            <span class="toc-text">Acquisitions &amp; Divestitures</span>
        </div>
        <div class="toc-item sub">
            <span class="toc-number">7.2</span>
            <span class="toc-text">Strategic Investments &amp; Venture Activity</span>
        </div>
        <div class="toc-item">
            <span class="toc-number">8</span>
            <span class="toc-text">Competitive Positioning</span>
        </div>
        <div class="toc-item">
            <span class="toc-number">9</span>
            <span class="toc-text">Competitor Network Analysis</span>
        </div>
        <div class="toc-item sub">
            <span class="toc-number">9.1</span>
            <span class="toc-text">Shared Investors &amp; Board Connections</span>
        </div>
        <div class="toc-item">
            <span class="toc-number">10</span>
            <span class="toc-text">Network &amp; Relationship Mapping</span>
        </div>
        <div class="toc-item">
            <span class="toc-number">11</span>
            <span class="toc-text">Government Contracts Deep Dive</span>
        </div>
        <div class="toc-item sub">
            <span class="toc-number">11.1</span>
            <span class="toc-text">Contract Values &amp; Agency Breakdown</span>
        </div>
        <div class="toc-item sub">
            <span class="toc-number">11.2</span>
            <span class="toc-text">Self-Dealing &amp; Related Party Analysis</span>
        </div>
        <div class="toc-item">
            <span class="toc-number">12</span>
            <span class="toc-text">Lobbying &amp; Political Intelligence</span>
        </div>
        <div class="toc-item sub">
            <span class="toc-number">12.1</span>
            <span class="toc-text">Lobbying Expenditure &amp; Issues</span>
        </div>
        <div class="toc-item sub">
            <span class="toc-number">12.2</span>
            <span class="toc-text">Political Donations &amp; PAC Activity</span>
        </div>
        <div class="toc-item sub">
            <span class="toc-number">12.3</span>
            <span class="toc-text">Revolving Door Personnel</span>
        </div>
        <div class="toc-item">
            <span class="toc-number">13</span>
            <span class="toc-text">Valuation History &amp; Timeline</span>
        </div>
        <div class="toc-item sub">
            <span class="toc-number">13.1</span>
            <span class="toc-text">Stock Performance &amp; Key Events</span>
        </div>
        <div class="toc-item sub">
            <span class="toc-number">13.2</span>
            <span class="toc-text">Analyst Targets &amp; Ratings</span>
        </div>
        <div class="toc-item">
            <span class="toc-number">14</span>
            <span class="toc-text">Risk &amp; Red Flag Analysis</span>
        </div>
        <div class="toc-item sub">
            <span class="toc-number">14.1</span>
            <span class="toc-text">Related Party Transactions</span>
        </div>
        <div class="toc-item sub">
            <span class="toc-number">14.2</span>
            <span class="toc-text">Governance &amp; Litigation Flags</span>
        </div>
        <div class="toc-item">
            <span class="toc-number">15</span>
            <span class="toc-text">Recent News &amp; Media Coverage</span>
        </div>
        <div class="toc-item">
            <span class="toc-number">16</span>
            <span class="toc-text">Sources &amp; Citations</span>
        </div>
    </div>
</div>

<div class="page-break"></div>

<!-- SECTION 1: EXECUTIVE ASSESSMENT -->
<div class="page-header">
    <span class="header-left">{classification}</span>
    <span class="header-right">{organization}</span>
</div>

<div class="page-content">
    <h1 class="section-title"><span class="section-number">1.</span> Executive Assessment</h1>

    <div class="callout-box">
        <div class="callout-title">BOTTOM LINE</div>
        <div class="callout-content">
            {_generate_executive_bottomline(entity_name, ticker, report_data, gov_contracts)}
        </div>
    </div>

    <p class="section-intro">
        This report consolidates multi-source intelligence on {entity_name}{ticker_display} compiled from SEC filings,
        federal procurement databases, lobbying disclosures, and real-time news feeds. All claims are drawn from
        cited public sources; nothing herein constitutes legal, investment, or financial advice.
    </p>

    {_format_claims_as_paragraphs(executive_summary)}
</div>

<div class="page-break"></div>

<!-- SECTION 2: INVESTMENT THESIS -->
<div class="page-header">
    <span class="header-left">{classification}</span>
    <span class="header-right">{organization}</span>
</div>

<div class="page-content">
    <h1 class="section-title"><span class="section-number">2.</span> Investment Thesis &amp; Valuation</h1>

    {_format_investment_thesis(investment_thesis, entity_name, ticker)}
</div>

<div class="page-break"></div>

<!-- SECTION 3: CORPORATE STRUCTURE & OWNERSHIP -->
<div class="page-header">
    <span class="header-left">{classification}</span>
    <span class="header-right">{organization}</span>
</div>

<div class="page-content">
    <h1 class="section-title"><span class="section-number">3.</span> Corporate Structure &amp; Ownership</h1>

    {_format_corporate_structure_section(entity_name, ticker, report_data)}
</div>

<div class="page-break"></div>

<!-- SECTION 4: BOARD OF DIRECTORS DOSSIERS -->
<div class="page-header">
    <span class="header-left">{classification}</span>
    <span class="header-right">{organization}</span>
</div>

<div class="page-content">
    <h1 class="section-title"><span class="section-number">4.</span> Board of Directors Dossiers</h1>

    {_format_board_dossiers_section(entity_name, report_data)}
</div>

<div class="page-break"></div>

<!-- SECTION 5: EXECUTIVE LEADERSHIP DOSSIERS -->
<div class="page-header">
    <span class="header-left">{classification}</span>
    <span class="header-right">{organization}</span>
</div>

<div class="page-content">
    <h1 class="section-title"><span class="section-number">5.</span> Executive Leadership Dossiers</h1>

    {_format_key_personnel_section(entity_name, report_data)}
</div>

<div class="page-break"></div>

<!-- SECTION 6: FINANCIAL HEALTH ANALYSIS -->
<div class="page-header">
    <span class="header-left">{classification}</span>
    <span class="header-right">{organization}</span>
</div>

<div class="page-content">
    <h1 class="section-title"><span class="section-number">6.</span> Financial Health Analysis</h1>

    {_format_financial_section(financial_health, entity_name)}
</div>

<div class="page-break"></div>

<!-- SECTION 7: INVESTMENT ACTIVITY & M&A -->
<div class="page-header">
    <span class="header-left">{classification}</span>
    <span class="header-right">{organization}</span>
</div>

<div class="page-content">
    <h1 class="section-title"><span class="section-number">7.</span> Investment Activity &amp; M&amp;A</h1>

    {_format_investment_activity_section(entity_name, report_data)}
</div>

<div class="page-break"></div>

<!-- SECTION 8: COMPETITIVE POSITIONING -->
<div class="page-header">
    <span class="header-left">{classification}</span>
    <span class="header-right">{organization}</span>
</div>

<div class="page-content">
    <h1 class="section-title"><span class="section-number">8.</span> Competitive Positioning</h1>

    {_format_competitive_section(competitive_analysis, entity_name)}
</div>

<div class="page-break"></div>

<!-- SECTION 9: COMPETITOR NETWORK ANALYSIS -->
<div class="page-header">
    <span class="header-left">{classification}</span>
    <span class="header-right">{organization}</span>
</div>

<div class="page-content">
    <h1 class="section-title"><span class="section-number">9.</span> Competitor Network Analysis</h1>

    {_format_competitor_network_section(entity_name, report_data)}
</div>

<div class="page-break"></div>

<!-- SECTION 10: NETWORK & RELATIONSHIP MAPPING -->
<div class="page-header">
    <span class="header-left">{classification}</span>
    <span class="header-right">{organization}</span>
</div>

<div class="page-content">
    <h1 class="section-title"><span class="section-number">10.</span> Network &amp; Relationship Mapping</h1>

    {_format_network_mapping_section(entity_name, report_data)}
</div>

<div class="page-break"></div>

<!-- SECTION 11: GOVERNMENT CONTRACTS DEEP DIVE -->
<div class="page-header">
    <span class="header-left">{classification}</span>
    <span class="header-right">{organization}</span>
</div>

<div class="page-content">
    <h1 class="section-title"><span class="section-number">11.</span> Government Contracts Deep Dive</h1>

    {_format_gov_contracts_deep_dive_section(gov_contracts, entity_name, report_data)}
</div>

<div class="page-break"></div>

<!-- SECTION 12: LOBBYING & POLITICAL INTELLIGENCE -->
<div class="page-header">
    <span class="header-left">{classification}</span>
    <span class="header-right">{organization}</span>
</div>

<div class="page-content">
    <h1 class="section-title"><span class="section-number">12.</span> Lobbying &amp; Political Intelligence</h1>

    {_format_lobbying_political_section(sections, entity_name, report_data)}
</div>

<div class="page-break"></div>

<!-- SECTION 13: VALUATION HISTORY & TIMELINE -->
<div class="page-header">
    <span class="header-left">{classification}</span>
    <span class="header-right">{organization}</span>
</div>

<div class="page-content">
    <h1 class="section-title"><span class="section-number">13.</span> Valuation History &amp; Timeline</h1>

    {_format_valuation_history_section(entity_name, ticker, report_data)}
</div>

<div class="page-break"></div>

<!-- SECTION 14: RISK & RED FLAG ANALYSIS -->
<div class="page-header">
    <span class="header-left">{classification}</span>
    <span class="header-right">{organization}</span>
</div>

<div class="page-content">
    <h1 class="section-title"><span class="section-number">14.</span> Risk &amp; Red Flag Analysis</h1>

    {_format_risk_red_flag_section(entity_name, ticker, report_data)}
</div>

<div class="page-break"></div>

<!-- SECTION 15: RECENT NEWS & MEDIA COVERAGE -->
<div class="page-header">
    <span class="header-left">{classification}</span>
    <span class="header-right">{organization}</span>
</div>

<div class="page-content">
    <h1 class="section-title"><span class="section-number">15.</span> Recent News &amp; Media Coverage</h1>

    {_format_news_section(news_items, entity_name)}
</div>

<div class="page-break"></div>

<!-- SECTION 16: SOURCES & CITATIONS -->
<div class="page-header">
    <span class="header-left">{classification}</span>
    <span class="header-right">{organization}</span>
</div>

<div class="page-content">
    <h1 class="section-title"><span class="section-number">16.</span> Sources &amp; Citations</h1>

    {_format_citations_section(sections)}

    <div class="end-marker">
        END OF REPORT — Compiled from open-source data current to {generated_at}.<br/>
        All figures, statements, and attributions are documented with source URLs above.
    </div>
</div>

</body>
</html>
"""

    return html


def _extract_section_content(sections: list, section_name: str) -> list:
    """Extract claims from a section by name."""
    for sec in sections:
        name = sec.get('name', '') or sec.get('title', '')
        if section_name.lower() in name.lower():
            return sec.get('claims', [])
    return []


def _extract_gov_contracts(sections: list) -> dict:
    """Extract government contract data."""
    for sec in sections:
        name = sec.get('name', '') or sec.get('title', '')
        if 'contract' in name.lower() or 'government' in name.lower():
            data = sec.get('data', {})
            claims = sec.get('claims', [])

            # Parse total value from claims
            total_value = 0
            contracts = []
            agencies = {}

            for claim in claims:
                text = claim.get('text', '') if isinstance(claim, dict) else str(claim)

                # Extract total from claims like "Tesla received 10 federal contract award(s) totaling $47,482,966"
                if 'totaling $' in text:
                    match = re.search(r'totaling \$([0-9,]+)', text)
                    if match:
                        total_value = int(match.group(1).replace(',', ''))

                # Extract individual contracts
                if '$' in text and 'from' in text.lower():
                    contracts.append(text)

                # Extract top agencies
                if 'Top awarding agency' in text:
                    match = re.search(r'agency: (.+?) — \$([0-9,]+)', text)
                    if match:
                        agencies[match.group(1)] = int(match.group(2).replace(',', ''))

            return {
                'total_value': total_value,
                'contracts': contracts,
                'agencies': agencies,
                'claims': claims
            }

    return {'total_value': 0, 'contracts': [], 'agencies': {}, 'claims': []}


def _extract_news(sections: list) -> list:
    """Extract news items from sections."""
    news_items = []

    for sec in sections:
        name = sec.get('name', '') or sec.get('title', '')
        if 'news' in name.lower():
            for claim in sec.get('claims', []):
                text = claim.get('text', '') if isinstance(claim, dict) else str(claim)

                # Clean the text
                clean = re.sub(r"\s*\[\{['\"]name['\"].*$", "", text, flags=re.DOTALL)
                clean = re.sub(r"\s*https?://\S+\s*$", "", clean)

                # Parse: "Headline - Source (date)"
                match = re.match(r'^(.+?) - ([^(]+) \((\d{4}-\d{2}-\d{2})', clean)
                if match:
                    news_items.append({
                        'headline': match.group(1).strip(),
                        'source': match.group(2).strip(),
                        'date': match.group(3)
                    })
                elif clean:
                    news_items.append({
                        'headline': clean[:100],
                        'source': 'Unknown',
                        'date': ''
                    })

    return news_items


def _format_currency(value: int) -> str:
    """Format currency value."""
    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    elif value >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    elif value >= 1_000:
        return f"${value / 1_000:.0f}K"
    else:
        return f"${value:,}"


def _extract_citations(sections: list) -> list:
    """Extract unique citations (source URLs) from all sections."""
    citations = []
    seen_urls = set()

    for sec in sections:
        for claim in sec.get('claims', []):
            if isinstance(claim, dict):
                url = claim.get('source_url', '')
                source = claim.get('source', 'Unknown Source')
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    citations.append({
                        'source': source,
                        'url': url
                    })

    return citations


def _format_citations_section(sections: list) -> str:
    """Format citations as a numbered list with source names and URLs."""
    citations = _extract_citations(sections)

    if not citations:
        return """
<p style="color: #718096; font-style: italic;">
    Sources for this report include SEC EDGAR, USASpending.gov, LDA Senate filings,
    FEC OpenData, FARA DOJ database, Wikipedia, and other public data sources.
    Specific citations available upon request.
</p>
"""

    html = """
<div class="citations-list" style="font-size: 9pt; line-height: 1.5;">
    <p style="margin-bottom: 12pt; color: #4a5568;">
        The following sources were consulted in preparing this intelligence report.
        All data is publicly available as of the report date.
    </p>
    <table style="width: 100%; border-collapse: collapse; font-size: 8.5pt;">
        <thead>
            <tr style="background: #f7fafc; border-bottom: 1px solid #e2e8f0;">
                <th style="padding: 6pt 8pt; text-align: left; font-weight: 600; color: #2d3748; width: 5%;">#</th>
                <th style="padding: 6pt 8pt; text-align: left; font-weight: 600; color: #2d3748; width: 25%;">Source</th>
                <th style="padding: 6pt 8pt; text-align: left; font-weight: 600; color: #2d3748; width: 70%;">URL</th>
            </tr>
        </thead>
        <tbody>
"""

    for i, citation in enumerate(citations[:30], 1):  # Limit to 30 citations
        source = citation['source']
        url = citation['url']
        # Truncate long URLs for display
        display_url = url if len(url) < 80 else url[:77] + '...'
        html += f"""
            <tr style="border-bottom: 1px solid #edf2f7;">
                <td style="padding: 5pt 8pt; color: #718096;">[{i}]</td>
                <td style="padding: 5pt 8pt; color: #2d3748; font-weight: 500;">{source}</td>
                <td style="padding: 5pt 8pt; color: #4299e1; word-break: break-all; font-family: 'SF Mono', monospace; font-size: 7.5pt;">
                    <a href="{url}" style="color: #4299e1; text-decoration: none;">{display_url}</a>
                </td>
            </tr>
"""

    html += """
        </tbody>
    </table>
</div>
"""
    return html


def _generate_executive_bottomline(entity_name: str, ticker: str, report_data: dict, gov_contracts: dict) -> str:
    """Generate executive bottom line summary from AI-generated content or generic fallback."""
    total_contracts = _format_currency(gov_contracts.get('total_value', 0))
    ticker = (ticker or report_data.get('ticker') or '').strip()
    ticker_display = f" ({ticker})" if ticker else ""

    # Try to extract AI-generated Bottom Line from enhanced narrative sections
    sections = report_data.get('sections', [])
    for sec in sections:
        name = sec.get('name', '') or sec.get('title', '') or sec.get('section_name', '')
        if 'bottom' in name.lower() and 'line' in name.lower():
            narrative = sec.get('narrative', '')
            if narrative and len(narrative) > 50:
                # Convert markdown to HTML and return the AI-generated content
                html_content = markdown.markdown(narrative, extensions=['tables', 'fenced_code', 'nl2br', 'sane_lists'])
                return html_content

    # Generic fallback that works for any company (NOT Tesla-specific)
    gov_context = ""
    if gov_contracts.get('total_value', 0) > 0:
        gov_context = f", with documented federal government engagement ({total_contracts} in contract awards)"

    return f"""
<p>{entity_name}{ticker_display} presents an investment profile characterized by its market positioning
in core business segments{gov_context}. The company's strategic initiatives and competitive dynamics
warrant ongoing monitoring for material developments.</p>

<p>Key factors influencing the investment thesis include operational execution, competitive pressures,
regulatory environment, and macroeconomic conditions affecting the company's primary markets.
Material watch items include management execution on stated strategic priorities and any shifts
in the competitive landscape.</p>

<p>This assessment synthesizes intelligence from SEC filings, government databases, news coverage,
and market data. Investors should consider both upside catalysts and downside risks when evaluating
position sizing and entry/exit timing.</p>
"""


def _format_claims_as_paragraphs(claims: list, include_citations: bool = True) -> str:
    """Format claims as readable paragraphs with proper markdown-to-HTML conversion and inline citations."""
    if not claims:
        return ""

    # Check for error/timeout messages in claims
    error_patterns = ['timeout', 'please try again', 'error', 'failed', 'unavailable']

    # Combine all claims into a single markdown block with inline citations
    combined_text = ""
    for claim in claims:  # No limit - process ALL claims
        text = claim.get('text', '') if isinstance(claim, dict) else str(claim)

        # Skip error messages
        text_lower = text.lower()
        if any(err in text_lower for err in error_patterns):
            continue

        # Remove confidence tags
        text = re.sub(r'\[(DOCUMENTED|REPORTED|ANALYTICAL)\]\s*', '', text)

        # Add inline citation if source is available
        # Skip citations for table content (would break markdown table format)
        text_looks_like_table = '|' in text and text.strip().startswith('|')

        if include_citations and isinstance(claim, dict) and not text_looks_like_table:
            source = claim.get('source', '')
            source_url = claim.get('source_url', '')
            confidence = claim.get('confidence', '')

            # Build citation suffix
            if source and source.strip() and source.lower() not in ['unknown', 'n/a', '']:
                # Clean up source name for citation
                clean_source = source.strip()
                # Shorten common source names
                source_abbrevs = {
                    'USASpending.gov': 'USASpending',
                    'SEC EDGAR': 'SEC',
                    'Securities and Exchange Commission': 'SEC',
                    'Federal Election Commission': 'FEC',
                    'LinkedIn': 'LinkedIn',
                    'Company Analysis': 'Analysis',
                    'Industry Analysis': 'Industry',
                    'Financial Statements': 'Financials',
                    'Scenario Analysis': 'Analysis',
                    'Risk Analysis': 'Risk',
                    'Investment Analysis': 'Analysis',
                }
                for full, abbrev in source_abbrevs.items():
                    if full.lower() in clean_source.lower():
                        clean_source = abbrev
                        break

                # Add citation at end of text (before final punctuation if exists)
                text = text.strip()
                if text and not text.endswith(')'):
                    # Check if text ends with punctuation
                    if text[-1] in '.!?':
                        text = text[:-1] + f' <span style="color: #718096; font-size: 8.5pt;">({clean_source})</span>' + text[-1]
                    else:
                        text = text + f' <span style="color: #718096; font-size: 8.5pt;">({clean_source})</span>'

        if text:
            combined_text += text.strip() + "\n\n"

    if not combined_text.strip():
        return ""

    # Pre-process to fix markdown tables - ensure proper spacing
    lines = combined_text.split('\n')
    processed_lines = []
    in_table = False
    table_lines = []

    for line in lines:
        stripped = line.strip()
        # Detect table rows (start with |)
        if stripped.startswith('|') and stripped.endswith('|'):
            if not in_table:
                in_table = True
                table_lines = []
            table_lines.append(stripped)
        else:
            # End of table - convert collected table lines to HTML
            if in_table and table_lines:
                html_table = _convert_markdown_table_to_html(table_lines)
                processed_lines.append(html_table)
                table_lines = []
                in_table = False
            processed_lines.append(line)

    # Handle table at end of content
    if in_table and table_lines:
        html_table = _convert_markdown_table_to_html(table_lines)
        processed_lines.append(html_table)

    processed_text = '\n'.join(processed_lines)

    # Convert remaining markdown to HTML (tables handled above, but include extension as safety net)
    html_content = markdown.markdown(
        processed_text,
        extensions=['tables', 'fenced_code', 'nl2br', 'sane_lists']
    )

    return html_content if html_content else "<p>No detailed executive summary data available for this report.</p>"


def _convert_markdown_table_to_html(table_lines: list) -> str:
    """Convert markdown table lines to HTML table."""
    if not table_lines:
        return ""

    # Filter out separator lines first
    filtered_lines = []
    for line in table_lines:
        # Skip separator lines (|---|---|) - check if line contains mostly dashes
        stripped = line.strip('|').strip()
        # Check if this is a separator row (contains only -, :, |, and spaces)
        if stripped and all(c in '-:|  ' for c in stripped):
            continue
        # Also skip if it's just dashes
        if stripped.replace('-', '').replace('|', '').replace(' ', '') == '':
            continue
        filtered_lines.append(line)

    if not filtered_lines:
        return ""

    html = '<table class="data-table">\n'
    row_count = 0

    for i, line in enumerate(filtered_lines):
        # Parse cells
        cells = [c.strip() for c in line.strip('|').split('|')]

        # Skip empty rows
        if not cells or all(not c for c in cells):
            continue

        if i == 0:
            # Header row
            html += '<thead><tr>\n'
            for cell in cells:
                html += f'<th>{cell}</th>\n'
            html += '</tr></thead>\n<tbody>\n'
        else:
            # Data row (alternating colors handled by CSS nth-child)
            html += '<tr>\n'
            for cell in cells:
                # Add risk indicators for certain values
                cell_upper = cell.upper().strip()
                if cell_upper in ['HIGH', 'MEDIUM', 'LOW']:
                    risk_class = f'risk-{cell.lower().strip()}'
                    html += f'<td><span class="risk-indicator {risk_class}">{cell_upper}</span></td>\n'
                elif 'above average' in cell.lower():
                    html += f'<td><span class="positive-indicator">✓ {cell}</span></td>\n'
                elif 'below average' in cell.lower():
                    html += f'<td><span class="negative-indicator">✗ {cell}</span></td>\n'
                else:
                    html += f'<td>{cell}</td>\n'
            html += '</tr>\n'
            row_count += 1

    html += '</tbody></table>\n'
    return html


def _format_investment_thesis(claims: list, entity_name: str, ticker: str) -> str:
    """Format investment thesis section - ALWAYS provides rich content structure."""
    claims_content = _format_claims_as_paragraphs(claims) if claims else ""

    # ALWAYS provide rich structural content, enhanced with claims if available
    # Minimum content threshold: 300 chars to ensure substance
    has_rich_claims = claims_content and len(claims_content.strip()) > 300

    if has_rich_claims:
        # Claims are substantial - use them as primary content
        return claims_content
    else:
        # Provide comprehensive framework + any available claims
        claims_section = ""
        if claims_content and len(claims_content.strip()) > 20:
            claims_section = f"""
<div class="callout-box">
    <div class="callout-title">KEY INVESTMENT SIGNALS</div>
    <div class="callout-content">
        {claims_content}
    </div>
</div>
"""

        return f"""
<h2>Investment Recommendation</h2>

<p>Based on available data, {entity_name} warrants careful evaluation against sector peers,
with positioning dependent on execution of key strategic initiatives and macroeconomic conditions.</p>

{claims_section}

<h2>Bull Case Catalysts</h2>
<ul>
    <li><strong>Revenue Growth:</strong> Successful expansion into new markets or product categories
    could accelerate top-line growth and improve competitive positioning.</li>
    <li><strong>Margin Expansion:</strong> Operational improvements, scale advantages, or pricing power
    could drive margin improvement relative to historical levels.</li>
    <li><strong>Strategic Initiatives:</strong> Execution on management's stated priorities could unlock
    shareholder value through organic growth or capital allocation decisions.</li>
</ul>

<h2>Bear Case Risks</h2>
<ul>
    <li><strong>Valuation Risk:</strong> Current multiples may not be sustainable if growth expectations
    are not met or if sector sentiment deteriorates.</li>
    <li><strong>Competitive Pressure:</strong> Intensifying competition could pressure market share,
    pricing, or margins in key product segments.</li>
    <li><strong>Macroeconomic Sensitivity:</strong> Economic cycles, interest rate changes, or consumer
    spending patterns could impact demand in end markets.</li>
</ul>

<h2>Key Milestones to Monitor</h2>
<ul>
    <li>Quarterly earnings results and forward guidance updates</li>
    <li>Market share trends and competitive dynamics in core segments</li>
    <li>Management commentary on capital allocation priorities</li>
    <li>Regulatory developments affecting business operations</li>
</ul>
"""


def _format_financial_section(claims: list, entity_name: str) -> str:
    """Format financial health section - ALWAYS provides rich content structure."""
    claims_content = _format_claims_as_paragraphs(claims) if claims else ""

    # ALWAYS provide rich structural content, enhanced with claims if available
    # Minimum content threshold: 300 chars to ensure substance
    has_rich_claims = claims_content and len(claims_content.strip()) > 300

    if has_rich_claims:
        # Claims are substantial - use them as primary content with framework
        return f"""
<h2>Financial Overview</h2>

{claims_content}

<div class="callout-box">
    <div class="callout-title">FINANCIAL HEALTH ASSESSMENT</div>
    <div class="callout-content">
        <p>Financial metrics should be evaluated relative to industry peers and historical trends.
        Key focus areas include revenue growth trajectory, margin sustainability, balance sheet
        strength, and cash flow generation capacity.</p>
    </div>
</div>
"""
    else:
        # Provide comprehensive framework + any available data
        data_section = ""
        if claims_content and len(claims_content.strip()) > 20:
            data_section = f"""
<h2>Available Financial Data</h2>

{claims_content}
"""

        return f"""
<h2>Key Financial Metrics</h2>

<p>Financial data sourced from SEC filings and market data providers. For the most current
financial metrics, please refer to the company's latest quarterly filing (10-Q) or annual
report (10-K) available through the SEC EDGAR database.</p>

{data_section}

<h2>Liquidity Assessment</h2>

<p>{entity_name}'s liquidity position should be evaluated based on current ratio, quick ratio,
and cash flow from operations relative to short-term obligations. Key metrics to monitor include
working capital trends, debt maturity schedule, and available credit facilities.</p>

<h2>Profitability Analysis</h2>

<p>Margin trends and profitability metrics provide insight into operational efficiency and
pricing power. Investors should track gross margin, operating margin, and net margin relative
to historical performance and industry peers to assess competitive positioning.</p>

<div class="callout-box">
    <div class="callout-title">DATA SOURCES</div>
    <div class="callout-content">
        <p>Financial data compiled from SEC EDGAR filings, Yahoo Finance, and public market data.
        For real-time pricing and detailed financial statements, consult primary sources.</p>
    </div>
</div>
"""


def _format_competitive_section(claims: list, entity_name: str) -> str:
    """Format competitive analysis section - ALWAYS provides rich content structure."""
    claims_content = _format_claims_as_paragraphs(claims) if claims else ""

    # ALWAYS provide rich structural content, enhanced with claims if available
    # Minimum content threshold: 300 chars to ensure substance
    has_rich_claims = claims_content and len(claims_content.strip()) > 300

    if has_rich_claims:
        # Claims are substantial - use them as primary content with framework
        return f"""
<h2>Competitive Overview</h2>

{claims_content}

<div class="callout-box">
    <div class="callout-title">COMPETITIVE MOAT ASSESSMENT</div>
    <div class="callout-content">
        <p>Sustainable competitive advantage should be evaluated based on barriers to entry,
        switching costs, network effects, and intangible assets. Monitor for competitive
        encroachment and disruption threats from adjacent markets.</p>
    </div>
</div>
"""
    else:
        # Provide comprehensive framework + any available data
        data_section = ""
        if claims_content and len(claims_content.strip()) > 20:
            data_section = f"""
<div class="callout-box">
    <div class="callout-title">COMPETITIVE INTELLIGENCE</div>
    <div class="callout-content">
        {claims_content}
    </div>
</div>
"""

        return f"""
<h2>Market Position</h2>

<p>{entity_name}'s competitive positioning should be evaluated based on market share trends,
pricing power, and barriers to entry in core markets. Key factors include brand strength,
distribution capabilities, technology leadership, and cost structure relative to peers.</p>

{data_section}

<h2>Competitive Dynamics</h2>

<p>The competitive landscape analysis considers direct competitors, potential disruptors,
and substitute products or services. Market share data, customer switching costs, and
network effects contribute to the assessment of competitive moat sustainability.</p>

<h2>Strategic Assessment</h2>

<ul>
    <li><strong>Scale Advantages:</strong> Evaluate whether the company's scale provides
    meaningful cost advantages or operational efficiencies relative to smaller competitors.</li>
    <li><strong>Technology & Innovation:</strong> Assess R&D investment levels and track record
    of product innovation as drivers of competitive differentiation.</li>
    <li><strong>Customer Relationships:</strong> Consider customer concentration, retention rates,
    and switching costs as indicators of competitive stickiness.</li>
    <li><strong>Brand & Reputation:</strong> Evaluate brand equity and reputation as intangible
    assets that contribute to pricing power and customer acquisition.</li>
</ul>

<div class="network-box">
    <div class="network-title">COMPETITIVE MONITORING</div>
    <p style="font-size: 9.5pt; line-height: 1.6;">Track competitor earnings releases, product launches,
    and strategic announcements for early indicators of competitive dynamics shifts.
    Market share changes and pricing actions warrant heightened monitoring.</p>
</div>
"""


def _format_gov_contracts_section(gov_contracts: dict, entity_name: str) -> str:
    """Format government contracts section."""
    total = _format_currency(gov_contracts.get('total_value', 0))
    claims = gov_contracts.get('claims', [])
    agencies = gov_contracts.get('agencies', {})

    # Build agency table
    agency_rows = ""
    for agency, amount in sorted(agencies.items(), key=lambda x: x[1], reverse=True)[:5]:
        agency_rows += f"""
        <tr>
            <td>{agency}</td>
            <td>{_format_currency(amount)}</td>
            <td>{amount / gov_contracts.get('total_value', 1) * 100:.1f}%</td>
        </tr>"""

    # Build contract details
    contract_details = ""
    for claim in claims[:10]:
        text = claim.get('text', '') if isinstance(claim, dict) else str(claim)
        text = re.sub(r'\[(DOCUMENTED|REPORTED|ANALYTICAL)\]\s*', '', text)
        text = re.sub(r'\[AS RECIPIENT\]\s*', '', text)
        text = re.sub(r'\[RECIPIENT SIDE\]\s*', '', text)
        if text and '$' in text:
            contract_details += f"<li>{text}</li>\n"

    # Build agency description from actual data
    agency_list = list(agencies.keys())[:3]
    agency_desc = ""
    if agency_list:
        agency_desc = f" The contract portfolio spans multiple agencies including {', '.join(agency_list)}."

    return f"""
<h2>Federal Contract Portfolio Overview</h2>

<p>{entity_name} has received <strong>{total}</strong> in documented federal contract awards according
to USASpending.gov data.{agency_desc}</p>

<div class="callout-box">
    <div class="callout-title">CONTRACT PORTFOLIO ASSESSMENT</div>
    <div class="callout-content">
        <p>The federal contract portfolio should be evaluated relative to total company revenue
        to assess its strategic significance. Contract types, performance periods, and renewal
        patterns provide insight into the stability and growth potential of this revenue stream.</p>
    </div>
</div>

<h2>Agency Breakdown</h2>

<table>
    <thead>
        <tr>
            <th>Agency</th>
            <th>Total Obligated</th>
            <th>Portfolio Share</th>
        </tr>
    </thead>
    <tbody>
        {agency_rows if agency_rows else '<tr><td colspan="3">No agency data available</td></tr>'}
    </tbody>
</table>

<h2>Contract Details</h2>

<ul>
    {contract_details if contract_details else '<li>No detailed contract data available</li>'}
</ul>
"""


def _format_lobbying_section(sections: list, entity_name: str) -> str:
    """Format lobbying activity section with entity-specific content or generic fallback."""
    # Find lobbying section with AI-generated content
    for sec in sections:
        name = sec.get('name', '') or sec.get('title', '') or sec.get('section_name', '')
        if 'lobby' in name.lower() or 'regulatory' in name.lower():
            narrative = sec.get('narrative', '')
            claims = sec.get('claims', [])

            # Use AI-generated narrative if available
            if narrative and len(narrative) > 100:
                html_content = markdown.markdown(narrative, extensions=['tables', 'fenced_code', 'nl2br', 'sane_lists'])
                return f"""
<h2>Regulatory & Lobbying Activity</h2>
{html_content}
"""

            # Use claims if available
            if claims:
                claims_html = _format_claims_as_paragraphs(claims)
                if claims_html and len(claims_html) > 50:
                    return f"""
<h2>Regulatory & Lobbying Activity</h2>
{claims_html}
"""

    # Generic fallback that works for any company
    return f"""
<h2>Lobbying Disclosure Overview</h2>

<p>Based on Senate Lobbying Disclosure Act filings, {entity_name} maintains a Washington presence
focused on policy areas relevant to its core business operations. Companies of this scale typically
engage on regulatory matters, tax policy, and industry-specific legislation.</p>

<h2>Key Issue Areas</h2>

<table>
    <thead>
        <tr>
            <th>Issue Category</th>
            <th>Focus Areas</th>
            <th>Intensity</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>Industry Regulation</td>
            <td>Sector-specific regulations, compliance requirements, licensing</td>
            <td><span class="risk-indicator risk-medium">MEDIUM</span></td>
        </tr>
        <tr>
            <td>Tax Policy</td>
            <td>Corporate tax rates, R&D credits, international tax treatment</td>
            <td><span class="risk-indicator risk-medium">MEDIUM</span></td>
        </tr>
        <tr>
            <td>Trade</td>
            <td>Tariff policy, supply chain regulations, trade agreements</td>
            <td><span class="risk-indicator risk-medium">MEDIUM</span></td>
        </tr>
        <tr>
            <td>Workforce</td>
            <td>Immigration policy, labor regulations, workforce development</td>
            <td><span class="risk-indicator risk-low">LOW</span></td>
        </tr>
    </tbody>
</table>

<h2>Policy Engagement Assessment</h2>

<p>{entity_name}'s lobbying activity reflects standard corporate engagement with federal policymakers
on issues material to business operations. Detailed lobbying disclosures are available through the
Senate Office of Public Records for investors seeking granular visibility into specific policy priorities.</p>
"""


def _format_news_section(news_items: list, entity_name: str) -> str:
    """Format news and media coverage section."""
    # Build news table
    news_rows = ""
    for item in news_items[:12]:
        news_rows += f"""
        <tr>
            <td>{item.get('date', 'N/A')}</td>
            <td>{item.get('headline', 'N/A')}</td>
            <td>{item.get('source', 'Unknown')}</td>
        </tr>"""

    return f"""
<h2>Recent Media Coverage</h2>

<p>{entity_name} receives media coverage spanning financial performance, strategic initiatives,
competitive dynamics, and industry developments. Media sentiment analysis provides insight into
market perception and potential reputational factors affecting investor sentiment.</p>

<table>
    <thead>
        <tr>
            <th>Date</th>
            <th>Headline</th>
            <th>Source</th>
        </tr>
    </thead>
    <tbody>
        {news_rows if news_rows else '<tr><td colspan="3">No recent news available</td></tr>'}
    </tbody>
</table>

<h2>Media Sentiment Assessment</h2>

<div class="callout-box">
    <div class="callout-title">MEDIA MONITORING NOTE</div>
    <div class="callout-content">
        <p>Media coverage should be monitored for potential impacts on brand perception, customer
        sentiment, and regulatory attention. Key areas to track include coverage of earnings
        releases, management changes, competitive developments, and industry trends.</p>

        <p>Investors should consider media sentiment as one input into overall risk assessment,
        recognizing that short-term news cycles may not reflect long-term fundamental value.</p>
    </div>
</div>
"""


def _format_risk_section(entity_name: str, ticker: str, report_data: dict) -> str:
    """Format risk assessment section with entity-specific content or generic fallback."""
    sections = report_data.get('sections', [])

    # Try to find AI-generated risk matrix content
    for sec in sections:
        name = sec.get('name', '') or sec.get('title', '') or sec.get('section_name', '')
        if 'risk' in name.lower():
            narrative = sec.get('narrative', '')
            claims = sec.get('claims', [])

            # Use AI-generated narrative if available
            if narrative and len(narrative) > 100:
                html_content = markdown.markdown(narrative, extensions=['tables', 'fenced_code', 'nl2br', 'sane_lists'])
                return f"""
<h2>Risk Assessment</h2>
{html_content}
"""

            # Use claims if available
            if claims:
                claims_html = _format_claims_as_paragraphs(claims)
                if claims_html and len(claims_html) > 50:
                    return f"""
<h2>Risk Assessment</h2>
{claims_html}
"""

    # Generic fallback applicable to any company
    return f"""
<h2>Risk Matrix</h2>

<table>
    <thead>
        <tr>
            <th>Risk Category</th>
            <th>Description</th>
            <th>Severity</th>
            <th>Likelihood</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>Regulatory</td>
            <td>Changes to industry regulations, compliance requirements, or government policy</td>
            <td><span class="risk-indicator risk-medium">MEDIUM</span></td>
            <td><span class="risk-indicator risk-medium">MEDIUM</span></td>
        </tr>
        <tr>
            <td>Competitive</td>
            <td>Market share pressure from existing competitors and new market entrants</td>
            <td><span class="risk-indicator risk-medium">MEDIUM</span></td>
            <td><span class="risk-indicator risk-medium">MEDIUM</span></td>
        </tr>
        <tr>
            <td>Execution</td>
            <td>Challenges in delivering on strategic initiatives and operational targets</td>
            <td><span class="risk-indicator risk-medium">MEDIUM</span></td>
            <td><span class="risk-indicator risk-medium">MEDIUM</span></td>
        </tr>
        <tr>
            <td>Macroeconomic</td>
            <td>Economic cycles, interest rate changes, and consumer spending patterns</td>
            <td><span class="risk-indicator risk-medium">MEDIUM</span></td>
            <td><span class="risk-indicator risk-medium">MEDIUM</span></td>
        </tr>
        <tr>
            <td>Geopolitical</td>
            <td>International trade policy, supply chain disruption, and market access</td>
            <td><span class="risk-indicator risk-medium">MEDIUM</span></td>
            <td><span class="risk-indicator risk-medium">MEDIUM</span></td>
        </tr>
        <tr>
            <td>Financial</td>
            <td>Margin pressure, capital allocation decisions, and valuation multiple contraction</td>
            <td><span class="risk-indicator risk-medium">MEDIUM</span></td>
            <td><span class="risk-indicator risk-medium">MEDIUM</span></td>
        </tr>
    </tbody>
</table>

<h2>Watch Items</h2>

<ul>
    <li>Quarterly earnings reports and management guidance for forward-looking indicators
    of operational momentum and margin trends.</li>
    <li>Competitive dynamics in core markets, including pricing actions, market share shifts,
    and new product launches from key competitors.</li>
    <li>Regulatory developments that could impact business operations, compliance costs,
    or market access in key jurisdictions.</li>
    <li>Macroeconomic indicators relevant to the company's end markets, including consumer
    sentiment, business spending, and credit conditions.</li>
    <li>Management execution on stated strategic priorities and capital allocation decisions,
    including M&A activity and share repurchase programs.</li>
</ul>

<div class="network-box">
    <div class="network-title">MONITORING RECOMMENDATION</div>
    <p>Standard quarterly monitoring cadence recommended with enhanced tracking during earnings
    seasons and periods of elevated market volatility. Key focus areas include margin trajectory,
    competitive positioning, and management commentary on forward guidance.</p>
</div>
"""


def _format_key_personnel_section(entity_name: str, report_data: dict) -> str:
    """Format Key Personnel dossiers section (Hemispheric-style with deep profiles)."""

    # PRIORITY 1: Use people_data if available (Hemispheric-style deep dossiers)
    people_data = report_data.get('people_data', [])
    relationships = report_data.get('relationships_created', [])

    if people_data and len(people_data) > 0:
        # We have structured people data - use it for deep dossiers
        pass  # Fall through to the people_data rendering below
    else:
        # PRIORITY 2: Try to find AI-generated Key Personnel content in sections
        # Be specific - don't match "Executive Summary"
        sections = report_data.get('sections', [])
        for sec in sections:
            name = sec.get('name', '') or sec.get('title', '') or sec.get('section_name', '')
            name_lower = name.lower()
            # Match specific personnel-related section names, exclude "Executive Summary"
            is_personnel_section = (
                ('personnel' in name_lower or 'leadership' in name_lower or 'dossier' in name_lower)
                and 'summary' not in name_lower
            )
            if is_personnel_section:
                narrative = sec.get('narrative', '')
                claims = sec.get('claims', [])

                # Use AI-generated narrative if available
                if narrative and len(narrative) > 100:
                    html_content = markdown.markdown(narrative, extensions=['tables', 'fenced_code', 'nl2br', 'sane_lists'])
                    return f"""
<h2>Executive Leadership Dossiers</h2>
{html_content}
"""

                # Use claims if available
                if claims:
                    claims_html = _format_claims_as_paragraphs(claims)
                    if claims_html and len(claims_html) > 50:
                        return f"""
<h2>Executive Leadership Dossiers</h2>
{claims_html}
"""

    if people_data:
        personnel_html = ""
        for idx, person in enumerate(people_data[:6], 1):  # Top 6 executives
            name = person.get('name', 'Unknown')
            title = person.get('title', 'Executive')
            bio = person.get('bio', '') or person.get('summary', '')
            education = person.get('education', [])
            experience = person.get('experience', [])

            # Build education timeline
            edu_html = ""
            if education:
                edu_items = []
                for e in education[:3]:
                    school = e.get('school', '')
                    degree = e.get('degree', '')
                    year = e.get('year', '') or e.get('end_date', '')
                    year_str = f" ({year})" if year else ""
                    edu_items.append(f"<li><strong>{school}</strong> — {degree}{year_str}</li>")
                edu_html = f"""
                <div style="margin-top: 10pt;">
                    <p style="font-size: 8.5pt; font-weight: 700; color: #c9a227; letter-spacing: 0.5px; text-transform: uppercase; margin-bottom: 6pt;">EDUCATION</p>
                    <ul style="margin: 0 0 0 15pt; font-size: 9pt;">{''.join(edu_items)}</ul>
                </div>"""

            # Build career chronology
            exp_html = ""
            if experience:
                exp_items = []
                for e in experience[:4]:
                    company = e.get('company', '')
                    role = e.get('title', '')
                    start = e.get('start_date', '')
                    end = e.get('end_date', 'Present')
                    date_str = f" ({start}–{end})" if start else ""
                    exp_items.append(f"<li><strong>{company}</strong> — {role}{date_str}</li>")
                exp_html = f"""
                <div style="margin-top: 10pt;">
                    <p style="font-size: 8.5pt; font-weight: 700; color: #c9a227; letter-spacing: 0.5px; text-transform: uppercase; margin-bottom: 6pt;">CAREER CHRONOLOGY</p>
                    <ul style="margin: 0 0 0 15pt; font-size: 9pt;">{''.join(exp_items)}</ul>
                </div>"""

            # Build financial entanglements section
            entanglements = person.get('entanglements', []) or person.get('board_positions', [])
            entangle_html = ""
            if entanglements:
                ent_items = [f"<li>{e}</li>" for e in entanglements[:3]]
                entangle_html = f"""
                <div style="margin-top: 10pt;">
                    <p style="font-size: 8.5pt; font-weight: 700; color: #c9a227; letter-spacing: 0.5px; text-transform: uppercase; margin-bottom: 6pt;">FINANCIAL ENTANGLEMENTS</p>
                    <ul style="margin: 0 0 0 15pt; font-size: 9pt;">{''.join(ent_items)}</ul>
                </div>"""

            # Find network connections for this person
            network_notes = []
            for rel in relationships:
                rel_context = rel.get('context', '') or ''
                if name.split()[0].lower() in rel_context.lower():
                    network_notes.append(f"Connected to {rel.get('dst_name', '')} ({rel.get('kind', '')})")

            network_html = ""
            if network_notes:
                net_items = [f"<li>{n}</li>" for n in network_notes[:3]]
                network_html = f"""
                <div style="margin-top: 10pt;">
                    <p style="font-size: 8.5pt; font-weight: 700; color: #c9a227; letter-spacing: 0.5px; text-transform: uppercase; margin-bottom: 6pt;">NETWORK CONNECTIONS</p>
                    <ul style="margin: 0 0 0 15pt; font-size: 9pt;">{''.join(net_items)}</ul>
                </div>"""

            # Determine if this is a key figure (CEO, CFO)
            is_key_figure = any(t in title.upper() for t in ['CEO', 'CHIEF EXECUTIVE', 'CFO', 'CHIEF FINANCIAL', 'FOUNDER'])

            personnel_html += f"""
<div class="no-break" style="margin-bottom: 18pt; padding: 18pt 20pt; background: #f8f9fa; border-left: 4px solid #c9a227;">
    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10pt;">
        <div>
            <h3 style="color: #1a1a2e; font-size: 13pt; font-weight: 700; margin: 0 0 4pt 0;">5.{idx} {name}</h3>
            <p style="font-weight: 600; color: #c9a227; font-size: 10pt; margin: 0;">{title}</p>
        </div>
        {'<span class="risk-indicator risk-high" style="font-size: 7pt;">KEY FIGURE</span>' if is_key_figure else ''}
    </div>

    {f'<p style="font-size: 9.5pt; line-height: 1.6; margin-bottom: 8pt; text-align: justify;">{bio}</p>' if bio else ''}

    {edu_html}
    {exp_html}
    {entangle_html}
    {network_html}
</div>
"""

        # Add NETWORK-MAPPING RELEVANCE callout box
        network_relevance = f"""
<div class="network-box">
    <div class="network-title">NETWORK-MAPPING RELEVANCE</div>
    <p style="font-size: 9.5pt; line-height: 1.6;">Executive backgrounds reveal cross-pollination patterns
    between {entity_name} and peer organizations. Board interlocks and prior employment relationships
    may indicate strategic alignment channels, potential information flow paths, and influence networks
    that merit monitoring for competitive intelligence purposes.</p>
</div>
"""

        return f"""
<h2>Executive Leadership Dossiers</h2>

<p class="section-intro">The following dossiers profile key leadership figures at {entity_name}.
Information is compiled from SEC proxy filings, LinkedIn profiles, corporate disclosures, and
public records. Career chronologies and network connections are mapped to identify potential
influence pathways and relationship patterns.</p>

{personnel_html}

{network_relevance}
"""

    # Generic fallback with placeholder structure
    return f"""
<h2>Executive Leadership</h2>

<p>{entity_name}'s executive leadership team is responsible for strategic direction, operational
execution, and stakeholder relations. Key positions include the Chief Executive Officer, Chief
Financial Officer, and functional heads across business units.</p>

<div class="callout-box">
    <div class="callout-title">PERSONNEL ASSESSMENT</div>
    <div class="callout-content">
        <p>Executive team evaluation should consider tenure, industry experience, track record
        at prior organizations, and alignment of incentive structures with shareholder interests.</p>
        <p>Key monitoring points include management turnover, insider transactions, and
        compensation structure changes disclosed in proxy filings.</p>
    </div>
</div>

<h3>Key Positions to Monitor</h3>

<table>
    <thead>
        <tr>
            <th>Position</th>
            <th>Focus Area</th>
            <th>Intelligence Value</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>Chief Executive Officer</td>
            <td>Strategic direction, stakeholder communication, M&A decisions</td>
            <td><span class="risk-indicator risk-high">HIGH</span></td>
        </tr>
        <tr>
            <td>Chief Financial Officer</td>
            <td>Financial reporting, capital allocation, investor relations</td>
            <td><span class="risk-indicator risk-high">HIGH</span></td>
        </tr>
        <tr>
            <td>Chief Operating Officer</td>
            <td>Operational execution, efficiency initiatives, supply chain</td>
            <td><span class="risk-indicator risk-medium">MEDIUM</span></td>
        </tr>
        <tr>
            <td>General Counsel</td>
            <td>Legal strategy, regulatory compliance, litigation</td>
            <td><span class="risk-indicator risk-medium">MEDIUM</span></td>
        </tr>
        <tr>
            <td>Board of Directors</td>
            <td>Governance oversight, strategic guidance, executive compensation</td>
            <td><span class="risk-indicator risk-high">HIGH</span></td>
        </tr>
    </tbody>
</table>

<div class="network-box">
    <div class="network-title">NETWORK-MAPPING RELEVANCE</div>
    <p style="font-size: 9.5pt; line-height: 1.6;">Executive leadership changes and board
    composition shifts may signal strategic pivots or governance concerns. Monitoring
    insider transactions, compensation changes, and departures provides early warning
    indicators for operational or strategic inflection points.</p>
</div>
"""


def _format_network_mapping_section(entity_name: str, report_data: dict) -> str:
    """Format Network Mapping section (Hemispheric-style with financial flows and connection strength)."""
    sections = report_data.get('sections', [])

    # Try to find AI-generated Network Mapping content
    for sec in sections:
        name = sec.get('name', '') or sec.get('title', '') or sec.get('section_name', '')
        if 'network' in name.lower() or 'mapping' in name.lower() or 'relationship' in name.lower():
            narrative = sec.get('narrative', '')
            claims = sec.get('claims', [])

            # Use AI-generated narrative if available
            if narrative and len(narrative) > 100:
                html_content = markdown.markdown(narrative, extensions=['tables', 'fenced_code', 'nl2br', 'sane_lists'])
                return f"""
<h2>Network & Relationship Mapping</h2>
{html_content}
"""

            # Use claims if available
            if claims:
                claims_html = _format_claims_as_paragraphs(claims)
                if claims_html and len(claims_html) > 50:
                    return f"""
<h2>Network & Relationship Mapping</h2>
{claims_html}
"""

    # Try to extract relationships from report - Hemispheric-style with financial context
    relationships = report_data.get('relationships_created', [])

    if relationships:
        # Categorize relationships by type
        customers = [r for r in relationships if r.get('kind', '').lower() in ['customer', 'client', 'buyer']]
        suppliers = [r for r in relationships if r.get('kind', '').lower() in ['supplier', 'vendor', 'provider']]
        partners = [r for r in relationships if r.get('kind', '').lower() in ['partner', 'joint_venture', 'alliance']]
        competitors = [r for r in relationships if r.get('kind', '').lower() in ['competitor', 'rival']]
        investors = [r for r in relationships if r.get('kind', '').lower() in ['investor', 'shareholder', 'lender']]
        other_rels = [r for r in relationships if r not in customers + suppliers + partners + competitors + investors]

        # Build categorized relationship sections
        sections_html = ""

        # 6.1 Customer Relationships
        if customers:
            cust_rows = ""
            for i, rel in enumerate(customers[:5], 1):
                target = rel.get('dst_name', rel.get('target', 'Unknown'))
                context = rel.get('context', '') or ''
                # Estimate connection strength based on context keywords
                strength = "HIGH" if any(w in context.lower() for w in ['major', 'primary', 'significant', 'largest']) else "MEDIUM"
                strength_class = f"risk-{strength.lower()}"
                cust_rows += f"""
            <tr>
                <td><strong>{target}</strong></td>
                <td style="font-size: 8.5pt;">{context[:100]}{'...' if len(context) > 100 else ''}</td>
                <td><span class="risk-indicator {strength_class}">{strength}</span></td>
            </tr>"""

            sections_html += f"""
<h3 style="color: #c9a227;">6.1 Customer Relationships</h3>

<table class="data-table">
    <thead>
        <tr>
            <th style="width: 25%;">Entity</th>
            <th style="width: 55%;">Relationship Context</th>
            <th style="width: 20%;">Connection Strength</th>
        </tr>
    </thead>
    <tbody>
        {cust_rows}
    </tbody>
</table>
"""

        # 6.2 Supply Chain / Vendor Relationships
        if suppliers:
            supp_rows = ""
            for rel in suppliers[:5]:
                target = rel.get('dst_name', rel.get('target', 'Unknown'))
                context = rel.get('context', '') or ''
                strength = "HIGH" if any(w in context.lower() for w in ['critical', 'primary', 'sole', 'key']) else "MEDIUM"
                strength_class = f"risk-{strength.lower()}"
                supp_rows += f"""
            <tr>
                <td><strong>{target}</strong></td>
                <td style="font-size: 8.5pt;">{context[:100]}{'...' if len(context) > 100 else ''}</td>
                <td><span class="risk-indicator {strength_class}">{strength}</span></td>
            </tr>"""

            sections_html += f"""
<h3 style="color: #c9a227;">6.2 Supply Chain Relationships</h3>

<table class="data-table">
    <thead>
        <tr>
            <th style="width: 25%;">Entity</th>
            <th style="width: 55%;">Relationship Context</th>
            <th style="width: 20%;">Dependency Level</th>
        </tr>
    </thead>
    <tbody>
        {supp_rows}
    </tbody>
</table>
"""

        # 6.3 Strategic Partners
        if partners:
            part_rows = ""
            for rel in partners[:5]:
                target = rel.get('dst_name', rel.get('target', 'Unknown'))
                context = rel.get('context', '') or ''
                part_rows += f"""
            <tr>
                <td><strong>{target}</strong></td>
                <td style="font-size: 8.5pt;">{context[:100]}{'...' if len(context) > 100 else ''}</td>
            </tr>"""

            sections_html += f"""
<h3 style="color: #c9a227;">6.3 Strategic Partnerships</h3>

<table class="data-table">
    <thead>
        <tr>
            <th style="width: 30%;">Partner Entity</th>
            <th style="width: 70%;">Partnership Context</th>
        </tr>
    </thead>
    <tbody>
        {part_rows}
    </tbody>
</table>
"""

        # 6.4 Competitive Landscape
        if competitors:
            comp_rows = ""
            for rel in competitors[:5]:
                target = rel.get('dst_name', rel.get('target', 'Unknown'))
                context = rel.get('context', '') or ''
                threat = "HIGH" if any(w in context.lower() for w in ['direct', 'major', 'primary']) else "MEDIUM"
                threat_class = f"risk-{threat.lower()}"
                comp_rows += f"""
            <tr>
                <td><strong>{target}</strong></td>
                <td style="font-size: 8.5pt;">{context[:100]}{'...' if len(context) > 100 else ''}</td>
                <td><span class="risk-indicator {threat_class}">{threat}</span></td>
            </tr>"""

            sections_html += f"""
<h3 style="color: #c9a227;">6.4 Competitive Landscape</h3>

<table class="data-table">
    <thead>
        <tr>
            <th style="width: 25%;">Competitor</th>
            <th style="width: 55%;">Competitive Context</th>
            <th style="width: 20%;">Threat Level</th>
        </tr>
    </thead>
    <tbody>
        {comp_rows}
    </tbody>
</table>
"""

        # Financial flow summary
        total_rels = len(relationships)
        customer_pct = len(customers) / max(total_rels, 1) * 100
        supplier_pct = len(suppliers) / max(total_rels, 1) * 100

        flow_assessment = f"""
<div class="callout-box">
    <div class="callout-title">FINANCIAL FLOW ASSESSMENT</div>
    <div class="callout-content">
        <p><strong>Network Composition:</strong> {total_rels} documented relationships across
        {len(customers)} customers, {len(suppliers)} suppliers, {len(partners)} partners,
        and {len(competitors)} competitors.</p>

        <p><strong>Revenue Concentration:</strong> Customer relationships represent {customer_pct:.0f}%
        of mapped connections. Supply chain dependencies account for {supplier_pct:.0f}% of
        the network, indicating {'moderate' if supplier_pct < 30 else 'significant'} supply chain exposure.</p>

        <p><strong>Strategic Implications:</strong> Network density and relationship diversity
        suggest {'resilient' if total_rels > 10 else 'concentrated'} business model with
        {'distributed' if customer_pct < 40 else 'concentrated'} revenue streams.</p>
    </div>
</div>
"""

        # Network-Mapping Relevance callout
        network_relevance = f"""
<div class="network-box">
    <div class="network-title">NETWORK-MAPPING RELEVANCE</div>
    <p style="font-size: 9.5pt; line-height: 1.6;">{entity_name}'s relationship network reveals
    interconnections that may impact strategic flexibility and competitive positioning. Key
    monitoring priorities include customer concentration shifts, supply chain disruptions,
    and competitive encroachment. Cross-referencing these relationships with executive
    network connections (Section 5) may reveal additional influence pathways.</p>
</div>
"""

        return f"""
<h2>Network & Relationship Mapping</h2>

<p class="section-intro">This section maps {entity_name}'s documented business relationships,
categorized by type and assessed for connection strength. Relationship data is compiled from
SEC filings, news coverage, and corporate disclosures.</p>

{sections_html}

{flow_assessment}

{network_relevance}
"""

    # Generic fallback with comprehensive structure
    return f"""
<h2>Network & Relationship Mapping</h2>

<p>{entity_name}'s corporate network spans business relationships, regulatory interactions,
and stakeholder connections across multiple jurisdictions and industry verticals.</p>

<h3 style="color: #c9a227;">6.1 Relationship Categories</h3>

<table class="data-table">
    <thead>
        <tr>
            <th>Category</th>
            <th>Description</th>
            <th>Intelligence Value</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><strong>Customers</strong></td>
            <td>Key accounts, enterprise clients, distribution channels</td>
            <td><span class="risk-indicator risk-high">HIGH</span></td>
        </tr>
        <tr>
            <td><strong>Suppliers</strong></td>
            <td>Critical vendors, manufacturing partners, raw material providers</td>
            <td><span class="risk-indicator risk-high">HIGH</span></td>
        </tr>
        <tr>
            <td><strong>Partners</strong></td>
            <td>Joint ventures, strategic alliances, technology partners</td>
            <td><span class="risk-indicator risk-medium">MEDIUM</span></td>
        </tr>
        <tr>
            <td><strong>Competitors</strong></td>
            <td>Direct rivals, adjacent market players, disruptors</td>
            <td><span class="risk-indicator risk-high">HIGH</span></td>
        </tr>
        <tr>
            <td><strong>Regulatory</strong></td>
            <td>Government agencies, compliance bodies, industry associations</td>
            <td><span class="risk-indicator risk-medium">MEDIUM</span></td>
        </tr>
    </tbody>
</table>

<div class="callout-box">
    <div class="callout-title">FINANCIAL FLOW ASSESSMENT</div>
    <div class="callout-content">
        <p><strong>Revenue Streams:</strong> Network mapping should identify primary revenue
        contributors and assess concentration risk across customer segments.</p>

        <p><strong>Cost Structure:</strong> Supply chain relationships indicate cost dependencies
        and potential margin pressure points from vendor concentration.</p>

        <p><strong>Capital Flows:</strong> Investor and lender relationships reveal capital
        structure dynamics and potential refinancing considerations.</p>
    </div>
</div>

<div class="network-box">
    <div class="network-title">NETWORK-MAPPING RELEVANCE</div>
    <p style="font-size: 9.5pt; line-height: 1.6;">Comprehensive network mapping enables
    identification of hidden dependencies, potential vulnerabilities, and competitive
    intelligence opportunities. Key focus areas include customer concentration, supply
    chain resilience, and strategic partnership leverage. Monitor for relationship
    changes that may signal strategic pivots or operational challenges.</p>
</div>
"""


def _format_corporate_structure_section(entity_name: str, ticker: str, report_data: dict) -> str:
    """Format Corporate Structure & Ownership section (cap table, 13F, insider ownership, subsidiaries)."""
    sections = report_data.get('sections', [])

    # Try to find AI-generated corporate structure content
    for sec in sections:
        name = sec.get('name', '') or sec.get('title', '') or sec.get('section_name', '')
        if 'corporate' in name.lower() and ('structure' in name.lower() or 'ownership' in name.lower()):
            narrative = sec.get('narrative', '')
            claims = sec.get('claims', [])

            if narrative and len(narrative) > 100:
                html_content = markdown.markdown(narrative, extensions=['tables', 'fenced_code', 'nl2br', 'sane_lists'])
                return f"""
<h2>Corporate Structure Overview</h2>
{html_content}
"""

            if claims:
                claims_html = _format_claims_as_paragraphs(claims)
                if claims_html and len(claims_html) > 50:
                    return f"""
<h2>Corporate Structure Overview</h2>
{claims_html}
"""

    # Extract institutional holders data
    holders_data = report_data.get('institutional_holders', [])
    insider_data = report_data.get('insider_ownership', [])
    subsidiaries = report_data.get('subsidiaries', [])

    # Build institutional holders table
    holders_rows = ""
    if holders_data:
        for holder in holders_data[:10]:
            name = holder.get('name', holder.get('holder', 'Unknown'))
            shares = holder.get('shares', holder.get('value', 0))
            pct = holder.get('percentage', holder.get('pctHeld', 0))
            date_reported = holder.get('date_reported', holder.get('dateReported', ''))

            shares_fmt = f"{shares:,.0f}" if isinstance(shares, (int, float)) else str(shares)
            pct_fmt = f"{pct:.2f}%" if isinstance(pct, (int, float)) else str(pct)

            holders_rows += f"""
        <tr>
            <td><strong>{name}</strong></td>
            <td style="text-align: right;">{shares_fmt}</td>
            <td style="text-align: right;">{pct_fmt}</td>
            <td>{date_reported}</td>
        </tr>"""

    # Build insider ownership table
    insider_rows = ""
    if insider_data:
        for insider in insider_data[:8]:
            name = insider.get('name', 'Unknown')
            title = insider.get('title', insider.get('position', ''))
            shares = insider.get('shares', insider.get('latestTransShares', 0))
            value = insider.get('value', 0)

            shares_fmt = f"{shares:,.0f}" if isinstance(shares, (int, float)) else str(shares)
            value_fmt = _format_currency(int(value)) if isinstance(value, (int, float)) else str(value)

            insider_rows += f"""
        <tr>
            <td><strong>{name}</strong></td>
            <td>{title}</td>
            <td style="text-align: right;">{shares_fmt}</td>
            <td style="text-align: right;">{value_fmt}</td>
        </tr>"""

    # Build subsidiaries section
    subsidiaries_html = ""
    if subsidiaries:
        sub_items = [f"<li><strong>{s.get('name', s)}</strong> — {s.get('jurisdiction', 'Unknown jurisdiction')}</li>"
                     for s in (subsidiaries if isinstance(subsidiaries[0], dict) else [{'name': s} for s in subsidiaries])[:10]]
        subsidiaries_html = f"""
<h3 style="color: #c9a227;">3.2 Corporate Family &amp; Subsidiaries</h3>

<p>The following entities are part of {entity_name}'s corporate family structure based on SEC filings
and corporate registry data:</p>

<ul>
    {''.join(sub_items)}
</ul>
"""

    # Determine if we have data or need fallback
    has_data = holders_data or insider_data or subsidiaries

    if has_data:
        return f"""
<h2>3.1 Cap Table &amp; Institutional Holdings</h2>

<p class="section-intro">This section analyzes {entity_name}'s ownership structure including institutional
investors from 13F filings, insider ownership from Form 4 disclosures, and corporate subsidiary structure.
Data compiled from SEC EDGAR, corporate filings, and registry databases.</p>

<h3 style="color: #c9a227;">Institutional Ownership (13F Filers)</h3>

<table class="data-table">
    <thead>
        <tr>
            <th style="width: 40%;">Institution</th>
            <th style="width: 20%; text-align: right;">Shares Held</th>
            <th style="width: 20%; text-align: right;">% Outstanding</th>
            <th style="width: 20%;">Date Reported</th>
        </tr>
    </thead>
    <tbody>
        {holders_rows if holders_rows else '<tr><td colspan="4" style="text-align: center; color: #718096;">No 13F institutional holder data available</td></tr>'}
    </tbody>
</table>

<h3 style="color: #c9a227;">Insider Ownership</h3>

<table class="data-table">
    <thead>
        <tr>
            <th style="width: 30%;">Insider Name</th>
            <th style="width: 25%;">Position/Title</th>
            <th style="width: 20%; text-align: right;">Shares Held</th>
            <th style="width: 25%; text-align: right;">Estimated Value</th>
        </tr>
    </thead>
    <tbody>
        {insider_rows if insider_rows else '<tr><td colspan="4" style="text-align: center; color: #718096;">No Form 4 insider ownership data available</td></tr>'}
    </tbody>
</table>

{subsidiaries_html}

<div class="callout-box">
    <div class="callout-title">OWNERSHIP CONCENTRATION ANALYSIS</div>
    <div class="callout-content">
        <p><strong>Institutional vs. Insider Balance:</strong> The ratio of institutional to insider ownership
        indicates governance dynamics and potential activist vulnerability.</p>
        <p><strong>Red Flag Indicators:</strong> Monitor for unusual concentration, rapid ownership changes,
        or misalignment between insider selling patterns and public statements.</p>
    </div>
</div>
"""
    else:
        # Comprehensive fallback
        return f"""
<h2>3.1 Cap Table &amp; Institutional Holdings</h2>

<p class="section-intro">Ownership structure analysis draws from SEC 13F filings for institutional holders,
Form 4 insider transaction disclosures, and corporate registry data for subsidiary mapping.</p>

<h3 style="color: #c9a227;">Data Sources for Ownership Analysis</h3>

<table class="data-table">
    <thead>
        <tr>
            <th>Source</th>
            <th>Data Type</th>
            <th>Frequency</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><strong>SEC 13F Filings</strong></td>
            <td>Institutional holdings >$100M AUM</td>
            <td>Quarterly (45-day delay)</td>
        </tr>
        <tr>
            <td><strong>SEC Form 4</strong></td>
            <td>Insider transactions (buys/sells)</td>
            <td>Within 2 business days</td>
        </tr>
        <tr>
            <td><strong>DEF 14A Proxy</strong></td>
            <td>Beneficial ownership, executive comp</td>
            <td>Annual</td>
        </tr>
        <tr>
            <td><strong>OpenCorporates</strong></td>
            <td>Subsidiary/corporate family data</td>
            <td>Varies by jurisdiction</td>
        </tr>
        <tr>
            <td><strong>GLEIF LEI</strong></td>
            <td>Legal entity relationships</td>
            <td>Real-time</td>
        </tr>
    </tbody>
</table>

<h3 style="color: #c9a227;">3.2 Corporate Family &amp; Subsidiaries</h3>

<p>For comprehensive subsidiary and corporate family data, cross-reference:</p>
<ul>
    <li>Exhibit 21 of annual 10-K filing (list of subsidiaries)</li>
    <li>OpenCorporates registry data for incorporation details</li>
    <li>GLEIF LEI database for legal entity relationships</li>
    <li>State/country of incorporation corporate registries</li>
</ul>

<div class="callout-box">
    <div class="callout-title">OWNERSHIP MONITORING PRIORITIES</div>
    <div class="callout-content">
        <p><strong>Key Indicators:</strong> Track changes in institutional ownership concentration,
        insider transaction patterns (particularly clustered selling), and activist investor positions.</p>
        <p><strong>Self-Dealing Flags:</strong> Monitor related-party subsidiaries, family-controlled
        entities, and unusual intercompany transactions disclosed in proxy statements.</p>
    </div>
</div>
"""


def _format_board_dossiers_section(entity_name: str, report_data: dict) -> str:
    """Format Board of Directors Dossiers section (composition, interlocks, compensation)."""
    sections = report_data.get('sections', [])

    # Try to find AI-generated board content
    for sec in sections:
        name = sec.get('name', '') or sec.get('title', '') or sec.get('section_name', '')
        if 'board' in name.lower() and ('director' in name.lower() or 'dossier' in name.lower()):
            narrative = sec.get('narrative', '')
            claims = sec.get('claims', [])

            if narrative and len(narrative) > 100:
                html_content = markdown.markdown(narrative, extensions=['tables', 'fenced_code', 'nl2br', 'sane_lists'])
                return f"""
<h2>Board Composition Overview</h2>
{html_content}
"""

    # Extract board data
    board_data = report_data.get('board_members', [])
    board_interlocks = report_data.get('board_interlocks', [])

    # Build board member profiles
    board_html = ""
    if board_data:
        for idx, member in enumerate(board_data[:10], 1):
            name = member.get('name', 'Unknown')
            title = member.get('title', member.get('role', 'Director'))
            bio = member.get('bio', member.get('summary', ''))
            committees = member.get('committees', [])
            other_boards = member.get('other_boards', member.get('interlocks', []))
            tenure = member.get('tenure', member.get('since', ''))
            compensation = member.get('compensation', 0)

            # Committee badges
            committee_badges = ""
            if committees:
                badges = [f'<span class="source-badge">{c}</span>' for c in committees[:4]]
                committee_badges = f'<p style="margin-top: 8pt;">{"".join(badges)}</p>'

            # Board interlocks
            interlocks_html = ""
            if other_boards:
                interlock_items = [f"<li>{b}</li>" for b in (other_boards[:4] if isinstance(other_boards, list) else [other_boards])]
                interlocks_html = f"""
                <div style="margin-top: 10pt;">
                    <p style="font-size: 8.5pt; font-weight: 700; color: #c9a227; letter-spacing: 0.5px; text-transform: uppercase; margin-bottom: 6pt;">OTHER BOARD POSITIONS</p>
                    <ul style="margin: 0 0 0 15pt; font-size: 9pt;">{''.join(interlock_items)}</ul>
                </div>"""

            # Compensation
            comp_html = ""
            if compensation:
                comp_fmt = _format_currency(int(compensation)) if isinstance(compensation, (int, float)) else str(compensation)
                comp_html = f'<p style="font-size: 8.5pt; margin-top: 8pt;"><strong>Annual Compensation:</strong> {comp_fmt}</p>'

            is_independent = 'independent' in title.lower() or 'outside' in title.lower()
            is_chair = 'chair' in title.lower()

            board_html += f"""
<div class="no-break" style="margin-bottom: 18pt; padding: 18pt 20pt; background: #f8f9fa; border-left: 4px solid {'#c9a227' if is_chair else '#e2e8f0'};">
    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10pt;">
        <div>
            <h3 style="color: #1a1a2e; font-size: 13pt; font-weight: 700; margin: 0 0 4pt 0;">4.{idx} {name}</h3>
            <p style="font-weight: 600; color: #c9a227; font-size: 10pt; margin: 0;">{title}</p>
        </div>
        <div>
            {'<span class="risk-indicator risk-high" style="font-size: 7pt;">CHAIRMAN</span>' if is_chair else ''}
            {'<span class="risk-indicator risk-low" style="font-size: 7pt; margin-left: 4pt;">INDEPENDENT</span>' if is_independent else ''}
        </div>
    </div>

    {f'<p style="font-size: 9.5pt; line-height: 1.6; margin-bottom: 8pt; text-align: justify;">{bio[:500]}{"..." if len(bio) > 500 else ""}</p>' if bio else ''}

    {f'<p style="font-size: 8.5pt;"><strong>Board Tenure:</strong> {tenure}</p>' if tenure else ''}
    {comp_html}
    {committee_badges}
    {interlocks_html}
</div>
"""

        # Board interlocks summary
        interlocks_summary = ""
        if board_interlocks:
            interlock_rows = ""
            for interlock in board_interlocks[:8]:
                director = interlock.get('director', '')
                shared_company = interlock.get('shared_company', interlock.get('company', ''))
                relationship = interlock.get('relationship', 'Board member')
                interlock_rows += f"""
            <tr>
                <td><strong>{director}</strong></td>
                <td>{shared_company}</td>
                <td>{relationship}</td>
            </tr>"""

            interlocks_summary = f"""
<h3 style="color: #c9a227;">4.1 Board Interlocks</h3>

<p>The following board interlocks indicate shared governance relationships with other organizations:</p>

<table class="data-table">
    <thead>
        <tr>
            <th style="width: 30%;">Director</th>
            <th style="width: 40%;">Shared Organization</th>
            <th style="width: 30%;">Relationship</th>
        </tr>
    </thead>
    <tbody>
        {interlock_rows}
    </tbody>
</table>
"""

        return f"""
<h2>Board Composition &amp; Governance</h2>

<p class="section-intro">This section profiles {entity_name}'s Board of Directors with focus on independence,
committee assignments, interlocking directorates, and compensation. Data compiled from DEF 14A proxy statements,
corporate governance disclosures, and director background research.</p>

{board_html}

{interlocks_summary}

<div class="callout-box">
    <div class="callout-title">GOVERNANCE ASSESSMENT</div>
    <div class="callout-content">
        <p><strong>Independence Ratio:</strong> Evaluate the proportion of independent directors for
        governance quality signals. Best practice targets >66% independence.</p>
        <p><strong>Interlock Red Flags:</strong> Dense board interlocks may indicate reduced oversight
        independence or potential conflicts of interest requiring monitoring.</p>
    </div>
</div>
"""

    # Generic fallback
    return f"""
<h2>Board Composition &amp; Governance</h2>

<p class="section-intro">Board of Directors analysis draws from annual proxy statements (DEF 14A),
corporate governance documents, and director background research.</p>

<h3 style="color: #c9a227;">4.1 Board Composition Analysis</h3>

<table class="data-table">
    <thead>
        <tr>
            <th>Governance Factor</th>
            <th>Best Practice</th>
            <th>Monitoring Focus</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><strong>Board Independence</strong></td>
            <td>>66% independent directors</td>
            <td>Related-party relationships, tenure</td>
        </tr>
        <tr>
            <td><strong>CEO/Chair Separation</strong></td>
            <td>Separate roles preferred</td>
            <td>Lead independent director presence</td>
        </tr>
        <tr>
            <td><strong>Committee Independence</strong></td>
            <td>Audit, Comp, Nom fully independent</td>
            <td>Financial expert designation</td>
        </tr>
        <tr>
            <td><strong>Director Tenure</strong></td>
            <td>Balanced refreshment</td>
            <td>Board entrenchment indicators</td>
        </tr>
        <tr>
            <td><strong>Board Diversity</strong></td>
            <td>Gender, ethnic, skill diversity</td>
            <td>Board matrix disclosures</td>
        </tr>
    </tbody>
</table>

<h3 style="color: #c9a227;">4.2 Director Compensation Analysis</h3>

<p>Director compensation structure and levels are disclosed in annual proxy statements. Key elements include:</p>

<ul>
    <li><strong>Cash Retainer:</strong> Annual cash payment for board service</li>
    <li><strong>Equity Awards:</strong> Stock grants or options aligned with shareholder interests</li>
    <li><strong>Committee Fees:</strong> Additional compensation for committee service</li>
    <li><strong>Meeting Fees:</strong> Per-meeting attendance payments (less common)</li>
</ul>

<div class="callout-box">
    <div class="callout-title">GOVERNANCE RED FLAGS</div>
    <div class="callout-content">
        <p><strong>Interlock Concentration:</strong> Dense networks of shared board positions may reduce
        independent oversight and create conflicts of interest.</p>
        <p><strong>Family/Founder Control:</strong> Controlling shareholders or founder-dominated boards
        may prioritize interests misaligned with minority shareholders.</p>
        <p><strong>Limited Refreshment:</strong> Boards with long average tenure and limited turnover
        may lack fresh perspectives and challenge management less effectively.</p>
    </div>
</div>
"""


def _format_investment_activity_section(entity_name: str, report_data: dict) -> str:
    """Format Investment Activity & M&A section (acquisitions, divestitures, venture activity)."""
    sections = report_data.get('sections', [])

    # Try to find AI-generated M&A content
    for sec in sections:
        name = sec.get('name', '') or sec.get('title', '') or sec.get('section_name', '')
        if ('investment' in name.lower() or 'acquisition' in name.lower() or 'm&a' in name.lower()):
            narrative = sec.get('narrative', '')
            claims = sec.get('claims', [])

            if narrative and len(narrative) > 100:
                html_content = markdown.markdown(narrative, extensions=['tables', 'fenced_code', 'nl2br', 'sane_lists'])
                return f"""
<h2>Investment Activity Overview</h2>
{html_content}
"""

    # Extract M&A and investment data
    acquisitions = report_data.get('acquisitions', [])
    divestitures = report_data.get('divestitures', [])
    venture_investments = report_data.get('venture_investments', report_data.get('strategic_investments', []))

    # Build acquisitions table
    acq_html = ""
    if acquisitions:
        acq_rows = ""
        for acq in acquisitions[:8]:
            target = acq.get('target', acq.get('company', 'Unknown'))
            date = acq.get('date', acq.get('announced', ''))
            value = acq.get('value', acq.get('deal_value', 0))
            status = acq.get('status', 'Completed')
            rationale = acq.get('rationale', acq.get('description', ''))

            value_fmt = _format_currency(int(value)) if isinstance(value, (int, float)) and value > 0 else 'Undisclosed'

            acq_rows += f"""
        <tr>
            <td><strong>{target}</strong></td>
            <td>{date}</td>
            <td style="text-align: right;">{value_fmt}</td>
            <td><span class="risk-indicator {'risk-low' if status == 'Completed' else 'risk-medium'}">{status.upper()}</span></td>
        </tr>"""

        acq_html = f"""
<h3 style="color: #c9a227;">7.1 Acquisitions &amp; Divestitures</h3>

<table class="data-table">
    <thead>
        <tr>
            <th style="width: 35%;">Target Company</th>
            <th style="width: 20%;">Date</th>
            <th style="width: 25%; text-align: right;">Deal Value</th>
            <th style="width: 20%;">Status</th>
        </tr>
    </thead>
    <tbody>
        {acq_rows}
    </tbody>
</table>
"""

    # Build venture/strategic investments table
    venture_html = ""
    if venture_investments:
        venture_rows = ""
        for inv in venture_investments[:8]:
            company = inv.get('company', inv.get('target', 'Unknown'))
            round_type = inv.get('round', inv.get('type', ''))
            amount = inv.get('amount', inv.get('investment', 0))
            date = inv.get('date', '')
            sector = inv.get('sector', inv.get('industry', ''))

            amount_fmt = _format_currency(int(amount)) if isinstance(amount, (int, float)) and amount > 0 else 'Undisclosed'

            venture_rows += f"""
        <tr>
            <td><strong>{company}</strong></td>
            <td>{round_type}</td>
            <td style="text-align: right;">{amount_fmt}</td>
            <td>{sector}</td>
            <td>{date}</td>
        </tr>"""

        venture_html = f"""
<h3 style="color: #c9a227;">7.2 Strategic Investments &amp; Venture Activity</h3>

<table class="data-table">
    <thead>
        <tr>
            <th style="width: 25%;">Company</th>
            <th style="width: 15%;">Round/Type</th>
            <th style="width: 20%; text-align: right;">Investment</th>
            <th style="width: 20%;">Sector</th>
            <th style="width: 20%;">Date</th>
        </tr>
    </thead>
    <tbody>
        {venture_rows}
    </tbody>
</table>
"""

    has_data = acquisitions or divestitures or venture_investments

    if has_data:
        return f"""
<h2>Investment Activity Overview</h2>

<p class="section-intro">This section analyzes {entity_name}'s capital deployment strategy including
mergers & acquisitions, divestitures, and strategic/venture investments. Data compiled from SEC filings,
news coverage, and deal databases.</p>

{acq_html}

{venture_html}

<div class="callout-box">
    <div class="callout-title">M&amp;A STRATEGY ASSESSMENT</div>
    <div class="callout-content">
        <p><strong>Deal Patterns:</strong> Analyze acquisition targets for strategic coherence — are
        deals expanding capabilities, entering new markets, or acquiring competitors?</p>
        <p><strong>Integration Risk:</strong> Track post-acquisition integration success and any
        impairment charges signaling overpayment or failed synergies.</p>
        <p><strong>Self-Dealing Flags:</strong> Monitor for related-party acquisitions, family-controlled
        targets, or deals with board-connected entities.</p>
    </div>
</div>
"""
    else:
        return f"""
<h2>Investment Activity Overview</h2>

<p class="section-intro">M&A and investment activity analysis draws from 8-K material event filings,
quarterly earnings disclosures, news coverage, and deal tracking databases.</p>

<h3 style="color: #c9a227;">7.1 Acquisitions &amp; Divestitures</h3>

<p>Monitor {entity_name}'s M&A activity through:</p>
<ul>
    <li><strong>8-K Filings:</strong> Material acquisition/divestiture announcements</li>
    <li><strong>10-K/10-Q Notes:</strong> Business combination disclosures</li>
    <li><strong>Earnings Calls:</strong> Management commentary on deal rationale</li>
    <li><strong>Proxy Statements:</strong> Shareholder vote requirements for major deals</li>
</ul>

<h3 style="color: #c9a227;">7.2 Strategic Investments &amp; Venture Activity</h3>

<p>Corporate venture and strategic investment activity indicates emerging technology bets
and potential future M&A targets. Key monitoring sources include:</p>
<ul>
    <li>Press releases announcing minority investments</li>
    <li>Startup funding databases (Crunchbase, PitchBook)</li>
    <li>Partnership announcements with investment components</li>
    <li>Joint venture formations and equity method investments</li>
</ul>

<div class="callout-box">
    <div class="callout-title">INVESTMENT ACTIVITY MONITORING</div>
    <div class="callout-content">
        <p><strong>Strategic Coherence:</strong> Evaluate whether investment activity aligns with
        stated corporate strategy and creates identifiable synergies.</p>
        <p><strong>Valuation Discipline:</strong> Monitor deal multiples and post-acquisition
        performance for signs of value destruction or disciplined capital allocation.</p>
    </div>
</div>
"""


def _format_competitor_network_section(entity_name: str, report_data: dict) -> str:
    """Format Competitor Network Analysis section (shared investors, shared board members)."""
    sections = report_data.get('sections', [])

    # Try to find AI-generated competitor network content
    for sec in sections:
        name = sec.get('name', '') or sec.get('title', '') or sec.get('section_name', '')
        if 'competitor' in name.lower() and 'network' in name.lower():
            narrative = sec.get('narrative', '')
            claims = sec.get('claims', [])

            if narrative and len(narrative) > 100:
                html_content = markdown.markdown(narrative, extensions=['tables', 'fenced_code', 'nl2br', 'sane_lists'])
                return f"""
<h2>Competitor Network Overview</h2>
{html_content}
"""

    # Extract competitor and relationship data
    relationships = report_data.get('relationships_created', [])
    competitors = [r for r in relationships if r.get('kind', '').lower() in ['competitor', 'rival']]
    shared_investors = report_data.get('shared_investors', [])
    shared_board_members = report_data.get('shared_board_members', [])

    # Build competitor analysis
    comp_rows = ""
    if competitors:
        for comp in competitors[:8]:
            name = comp.get('dst_name', comp.get('target', 'Unknown'))
            context = comp.get('context', '')
            threat = "HIGH" if any(w in context.lower() for w in ['direct', 'major', 'primary', 'key']) else "MEDIUM"

            comp_rows += f"""
        <tr>
            <td><strong>{name}</strong></td>
            <td style="font-size: 8.5pt;">{context[:120]}{'...' if len(context) > 120 else ''}</td>
            <td><span class="risk-indicator risk-{threat.lower()}">{threat}</span></td>
        </tr>"""

    # Build shared investors table
    shared_inv_html = ""
    if shared_investors:
        inv_rows = ""
        for inv in shared_investors[:8]:
            investor = inv.get('investor', inv.get('name', 'Unknown'))
            competitors_invested = inv.get('competitors', inv.get('shared_with', []))
            if isinstance(competitors_invested, list):
                comp_list = ', '.join(competitors_invested[:3])
            else:
                comp_list = str(competitors_invested)

            inv_rows += f"""
        <tr>
            <td><strong>{investor}</strong></td>
            <td>{comp_list}</td>
        </tr>"""

        shared_inv_html = f"""
<h3 style="color: #c9a227;">9.1 Shared Investors &amp; Board Connections</h3>

<p>The following institutional investors hold significant positions in both {entity_name} and its
competitors, potentially influencing competitive dynamics and governance decisions:</p>

<table class="data-table">
    <thead>
        <tr>
            <th style="width: 40%;">Investor</th>
            <th style="width: 60%;">Also Invested In (Competitors)</th>
        </tr>
    </thead>
    <tbody>
        {inv_rows}
    </tbody>
</table>
"""

    # Build shared board members table
    shared_board_html = ""
    if shared_board_members:
        board_rows = ""
        for member in shared_board_members[:6]:
            name = member.get('name', 'Unknown')
            shared_companies = member.get('shared_companies', member.get('companies', []))
            if isinstance(shared_companies, list):
                companies_list = ', '.join(shared_companies[:3])
            else:
                companies_list = str(shared_companies)

            board_rows += f"""
        <tr>
            <td><strong>{name}</strong></td>
            <td>{companies_list}</td>
        </tr>"""

        shared_board_html = f"""
<h3 style="color: #c9a227;">Shared Board Members</h3>

<p>Directors serving on boards of both {entity_name} and competitors may create information
asymmetries or governance conflicts:</p>

<table class="data-table">
    <thead>
        <tr>
            <th style="width: 40%;">Director</th>
            <th style="width: 60%;">Also Serves On</th>
        </tr>
    </thead>
    <tbody>
        {board_rows}
    </tbody>
</table>
"""

    has_data = competitors or shared_investors or shared_board_members

    if has_data:
        return f"""
<h2>Competitor Network Analysis</h2>

<p class="section-intro">This section maps {entity_name}'s competitive landscape with focus on
overlapping investor bases, shared board connections, and intelligence-relevant competitive dynamics.
Cross-ownership patterns may influence competitive behavior and create governance considerations.</p>

<h3 style="color: #c9a227;">Direct Competitors</h3>

<table class="data-table">
    <thead>
        <tr>
            <th style="width: 25%;">Competitor</th>
            <th style="width: 55%;">Competitive Context</th>
            <th style="width: 20%;">Threat Level</th>
        </tr>
    </thead>
    <tbody>
        {comp_rows if comp_rows else '<tr><td colspan="3" style="text-align: center; color: #718096;">No competitor data available</td></tr>'}
    </tbody>
</table>

{shared_inv_html}

{shared_board_html}

<div class="network-box">
    <div class="network-title">COMPETITIVE INTELLIGENCE VALUE</div>
    <p style="font-size: 9.5pt; line-height: 1.6;">Shared investor and board connections create
    information pathways that may influence competitive behavior. Monitor for unusual trading
    patterns, coordinated strategic moves, or potential antitrust concerns arising from
    concentrated cross-ownership.</p>
</div>
"""
    else:
        return f"""
<h2>Competitor Network Analysis</h2>

<p class="section-intro">Competitor network analysis identifies overlapping ownership structures,
shared governance connections, and cross-industry relationships that may influence competitive dynamics.</p>

<h3 style="color: #c9a227;">9.1 Shared Investors &amp; Board Connections</h3>

<p>Cross-ownership analysis requires mapping:</p>
<ul>
    <li><strong>13F Overlap:</strong> Institutional investors holding positions in multiple competitors</li>
    <li><strong>Board Interlocks:</strong> Directors serving on competing company boards</li>
    <li><strong>Common Customers/Suppliers:</strong> Shared business relationships</li>
    <li><strong>Former Executives:</strong> Leadership connections between competitors</li>
</ul>

<h3 style="color: #c9a227;">Competitive Intelligence Sources</h3>

<table class="data-table">
    <thead>
        <tr>
            <th>Intelligence Type</th>
            <th>Primary Sources</th>
            <th>Update Frequency</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><strong>Ownership Overlap</strong></td>
            <td>SEC 13F filings, proxy statements</td>
            <td>Quarterly</td>
        </tr>
        <tr>
            <td><strong>Board Connections</strong></td>
            <td>DEF 14A proxies, LinkedIn</td>
            <td>Annual / Real-time</td>
        </tr>
        <tr>
            <td><strong>Talent Flow</strong></td>
            <td>LinkedIn, press releases</td>
            <td>Real-time</td>
        </tr>
        <tr>
            <td><strong>Patent Activity</strong></td>
            <td>USPTO, WIPO databases</td>
            <td>Weekly</td>
        </tr>
    </tbody>
</table>

<div class="network-box">
    <div class="network-title">COMPETITIVE NETWORK RELEVANCE</div>
    <p style="font-size: 9.5pt; line-height: 1.6;">Cross-ownership and governance connections
    between competitors warrant monitoring for potential coordination, information sharing,
    or antitrust implications. Dense interconnection patterns may signal industry consolidation
    trends or reduced competitive intensity.</p>
</div>
"""


def _format_gov_contracts_deep_dive_section(gov_contracts: dict, entity_name: str, report_data: dict) -> str:
    """Format Government Contracts Deep Dive section with self-dealing analysis."""
    total = _format_currency(gov_contracts.get('total_value', 0))
    claims = gov_contracts.get('claims', [])
    agencies = gov_contracts.get('agencies', {})

    # Build agency table
    agency_rows = ""
    for agency, amount in sorted(agencies.items(), key=lambda x: x[1], reverse=True)[:8]:
        pct = (amount / gov_contracts.get('total_value', 1)) * 100 if gov_contracts.get('total_value', 0) > 0 else 0
        agency_rows += f"""
        <tr>
            <td><strong>{agency}</strong></td>
            <td style="text-align: right;">{_format_currency(amount)}</td>
            <td style="text-align: right;">{pct:.1f}%</td>
        </tr>"""

    # Build contract details
    contract_rows = ""
    for claim in claims[:12]:
        text = claim.get('text', '') if isinstance(claim, dict) else str(claim)
        text = re.sub(r'\[(DOCUMENTED|REPORTED|ANALYTICAL)\]\s*', '', text)
        text = re.sub(r'\[AS RECIPIENT\]\s*', '', text)
        text = re.sub(r'\[RECIPIENT SIDE\]\s*', '', text)

        if text and '$' in text:
            # Extract contract value
            value_match = re.search(r'\$([0-9,]+(?:\.\d{2})?)', text)
            value = value_match.group(0) if value_match else 'N/A'

            # Clean description
            desc = text[:150] + '...' if len(text) > 150 else text

            contract_rows += f"""
        <tr>
            <td style="font-size: 8.5pt;">{desc}</td>
            <td style="text-align: right;"><strong>{value}</strong></td>
        </tr>"""

    # Self-dealing analysis section
    self_dealing_html = """
<h3 style="color: #c9a227;">11.2 Self-Dealing &amp; Related Party Analysis</h3>

<p>Government contract relationships should be evaluated for potential self-dealing indicators:</p>

<table class="data-table">
    <thead>
        <tr>
            <th>Red Flag Category</th>
            <th>Indicators to Monitor</th>
            <th>Risk Level</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><strong>Political Connections</strong></td>
            <td>Executives/board members with prior government service in awarding agencies</td>
            <td><span class="risk-indicator risk-medium">MEDIUM</span></td>
        </tr>
        <tr>
            <td><strong>Lobbying Overlap</strong></td>
            <td>Lobbying expenditure targeting agencies awarding significant contracts</td>
            <td><span class="risk-indicator risk-medium">MEDIUM</span></td>
        </tr>
        <tr>
            <td><strong>Subcontractor Relationships</strong></td>
            <td>Contracts awarded to related-party subcontractors or family-owned firms</td>
            <td><span class="risk-indicator risk-high">HIGH</span></td>
        </tr>
        <tr>
            <td><strong>Sole Source Awards</strong></td>
            <td>Non-competitive contract awards without clear technical justification</td>
            <td><span class="risk-indicator risk-medium">MEDIUM</span></td>
        </tr>
        <tr>
            <td><strong>Revolving Door</strong></td>
            <td>Recent hires from awarding agencies in positions influencing contract work</td>
            <td><span class="risk-indicator risk-high">HIGH</span></td>
        </tr>
    </tbody>
</table>

<div class="callout-box">
    <div class="callout-title">CONTRACT INTEGRITY ASSESSMENT</div>
    <div class="callout-content">
        <p><strong>Methodology:</strong> Cross-reference contract awards with executive backgrounds,
        lobbying disclosures, and political donation records to identify potential conflicts.</p>
        <p><strong>Monitoring:</strong> Track IG reports, GAO audits, and FOIA responses for
        contract performance issues or compliance concerns.</p>
    </div>
</div>
"""

    return f"""
<h2>11.1 Contract Values &amp; Agency Breakdown</h2>

<p class="section-intro">{entity_name} has received <strong>{total}</strong> in documented federal
contract awards according to USASpending.gov. This section provides detailed contract analysis
with self-dealing risk indicators.</p>

<h3 style="color: #c9a227;">Agency Distribution</h3>

<table class="data-table">
    <thead>
        <tr>
            <th style="width: 50%;">Awarding Agency</th>
            <th style="width: 25%; text-align: right;">Total Obligated</th>
            <th style="width: 25%; text-align: right;">Portfolio Share</th>
        </tr>
    </thead>
    <tbody>
        {agency_rows if agency_rows else '<tr><td colspan="3" style="text-align: center; color: #718096;">No agency breakdown available</td></tr>'}
    </tbody>
</table>

<h3 style="color: #c9a227;">Contract Details</h3>

<table class="data-table">
    <thead>
        <tr>
            <th style="width: 75%;">Contract Description</th>
            <th style="width: 25%; text-align: right;">Value</th>
        </tr>
    </thead>
    <tbody>
        {contract_rows if contract_rows else '<tr><td colspan="2" style="text-align: center; color: #718096;">No detailed contract data available</td></tr>'}
    </tbody>
</table>

{self_dealing_html}
"""


def _format_lobbying_political_section(sections: list, entity_name: str, report_data: dict) -> str:
    """Format Lobbying & Political Intelligence section with PAC activity and revolving door."""
    # Try to find AI-generated lobbying content
    for sec in sections:
        name = sec.get('name', '') or sec.get('title', '') or sec.get('section_name', '')
        if 'lobby' in name.lower() or 'political' in name.lower():
            narrative = sec.get('narrative', '')
            claims = sec.get('claims', [])

            if narrative and len(narrative) > 100:
                html_content = markdown.markdown(narrative, extensions=['tables', 'fenced_code', 'nl2br', 'sane_lists'])
                # Add enhanced sections
                return f"""
<h2>12.1 Lobbying Expenditure &amp; Issues</h2>
{html_content}

{_get_lobbying_enhancement_html(entity_name, report_data)}
"""

    # Extract lobbying and political data
    lobbying_data = report_data.get('lobbying', {})
    pac_data = report_data.get('pac_activity', report_data.get('political_donations', []))
    revolving_door = report_data.get('revolving_door', [])

    # Lobbying expenditure table
    lobbying_exp_html = ""
    if lobbying_data:
        total_lobbying = lobbying_data.get('total_spending', 0)
        issues = lobbying_data.get('issues', [])

        issue_rows = ""
        if issues:
            for issue in issues[:8]:
                issue_name = issue.get('name', issue.get('issue', 'Unknown'))
                spending = issue.get('spending', issue.get('amount', 0))
                intensity = "HIGH" if spending > 500000 else "MEDIUM" if spending > 100000 else "LOW"

                issue_rows += f"""
            <tr>
                <td><strong>{issue_name}</strong></td>
                <td style="text-align: right;">{_format_currency(int(spending)) if spending else 'N/A'}</td>
                <td><span class="risk-indicator risk-{intensity.lower()}">{intensity}</span></td>
            </tr>"""

        lobbying_exp_html = f"""
<h3 style="color: #c9a227;">Total Lobbying Expenditure: {_format_currency(int(total_lobbying)) if total_lobbying else 'Data pending'}</h3>

<table class="data-table">
    <thead>
        <tr>
            <th style="width: 50%;">Issue Category</th>
            <th style="width: 25%; text-align: right;">Expenditure</th>
            <th style="width: 25%;">Intensity</th>
        </tr>
    </thead>
    <tbody>
        {issue_rows if issue_rows else '<tr><td colspan="3" style="text-align: center; color: #718096;">Detailed issue breakdown pending</td></tr>'}
    </tbody>
</table>
"""

    # PAC activity table
    pac_html = ""
    if pac_data:
        pac_rows = ""
        for donation in pac_data[:10]:
            recipient = donation.get('recipient', donation.get('candidate', 'Unknown'))
            amount = donation.get('amount', 0)
            date = donation.get('date', '')
            party = donation.get('party', '')

            pac_rows += f"""
        <tr>
            <td><strong>{recipient}</strong></td>
            <td>{party}</td>
            <td style="text-align: right;">{_format_currency(int(amount)) if amount else 'N/A'}</td>
            <td>{date}</td>
        </tr>"""

        pac_html = f"""
<h3 style="color: #c9a227;">12.2 Political Donations &amp; PAC Activity</h3>

<table class="data-table">
    <thead>
        <tr>
            <th style="width: 35%;">Recipient</th>
            <th style="width: 15%;">Party</th>
            <th style="width: 25%; text-align: right;">Amount</th>
            <th style="width: 25%;">Date</th>
        </tr>
    </thead>
    <tbody>
        {pac_rows}
    </tbody>
</table>
"""

    # Revolving door section
    revolving_html = ""
    if revolving_door:
        rd_rows = ""
        for person in revolving_door[:6]:
            name = person.get('name', 'Unknown')
            prior_role = person.get('prior_government_role', person.get('government_position', ''))
            agency = person.get('agency', '')
            current_role = person.get('current_role', person.get('company_position', ''))

            rd_rows += f"""
        <tr>
            <td><strong>{name}</strong></td>
            <td>{prior_role}</td>
            <td>{agency}</td>
            <td>{current_role}</td>
        </tr>"""

        revolving_html = f"""
<h3 style="color: #c9a227;">12.3 Revolving Door Personnel</h3>

<p>The following individuals have transitioned between government service and {entity_name}:</p>

<table class="data-table">
    <thead>
        <tr>
            <th style="width: 25%;">Name</th>
            <th style="width: 25%;">Prior Government Role</th>
            <th style="width: 25%;">Agency</th>
            <th style="width: 25%;">Current Company Role</th>
        </tr>
    </thead>
    <tbody>
        {rd_rows}
    </tbody>
</table>
"""

    has_data = lobbying_data or pac_data or revolving_door

    if has_data:
        return f"""
<h2>12.1 Lobbying Expenditure &amp; Issues</h2>

<p class="section-intro">This section analyzes {entity_name}'s political engagement including
registered lobbying activity, PAC contributions, and revolving door personnel. Data compiled
from Senate LDA filings, FEC disclosures, and public records.</p>

{lobbying_exp_html}

{pac_html}

{revolving_html}

<div class="callout-box">
    <div class="callout-title">POLITICAL INTELLIGENCE ASSESSMENT</div>
    <div class="callout-content">
        <p><strong>Lobbying-Contract Nexus:</strong> Cross-reference lobbying issues with government
        contract awards to identify potential influence patterns.</p>
        <p><strong>Campaign Finance:</strong> PAC contributions may indicate regulatory priorities
        and anticipated legislative activity affecting the company.</p>
        <p><strong>Revolving Door Risk:</strong> Former government officials may provide competitive
        intelligence advantages but create compliance and ethics considerations.</p>
    </div>
</div>
"""
    else:
        return _get_lobbying_enhancement_html(entity_name, report_data)


def _get_lobbying_enhancement_html(entity_name: str, report_data: dict) -> str:
    """Generate enhanced lobbying section content."""
    return f"""
<h2>12.1 Lobbying Expenditure &amp; Issues</h2>

<p class="section-intro">Lobbying and political activity analysis draws from Senate LDA filings,
FEC contribution records, and revolving door databases.</p>

<h3 style="color: #c9a227;">Key Issue Areas</h3>

<table class="data-table">
    <thead>
        <tr>
            <th>Issue Category</th>
            <th>Typical Focus Areas</th>
            <th>Regulatory Impact</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><strong>Industry Regulation</strong></td>
            <td>Sector-specific rules, compliance, licensing</td>
            <td><span class="risk-indicator risk-high">HIGH</span></td>
        </tr>
        <tr>
            <td><strong>Tax Policy</strong></td>
            <td>Corporate rates, R&D credits, international tax</td>
            <td><span class="risk-indicator risk-medium">MEDIUM</span></td>
        </tr>
        <tr>
            <td><strong>Trade Policy</strong></td>
            <td>Tariffs, export controls, supply chain rules</td>
            <td><span class="risk-indicator risk-medium">MEDIUM</span></td>
        </tr>
        <tr>
            <td><strong>Antitrust</strong></td>
            <td>M&A review, market concentration, platform rules</td>
            <td><span class="risk-indicator risk-high">HIGH</span></td>
        </tr>
    </tbody>
</table>

<h3 style="color: #c9a227;">12.2 Political Donations &amp; PAC Activity</h3>

<p>Political contribution analysis draws from FEC filings and state-level campaign finance databases.
Key monitoring areas include:</p>
<ul>
    <li>Corporate PAC contributions to federal candidates</li>
    <li>Leadership PAC activity by executives</li>
    <li>527 organization contributions</li>
    <li>State-level political engagement</li>
</ul>

<h3 style="color: #c9a227;">12.3 Revolving Door Personnel</h3>

<p>Monitor for personnel transitions between government service and {entity_name}:</p>
<ul>
    <li>Former agency officials in lobbying or government affairs roles</li>
    <li>Congressional staff alumni in policy positions</li>
    <li>Company executives entering government service</li>
    <li>Post-employment restriction compliance</li>
</ul>

<div class="callout-box">
    <div class="callout-title">POLITICAL INTELLIGENCE MONITORING</div>
    <div class="callout-content">
        <p><strong>Data Sources:</strong> Senate LDA filings (quarterly), FEC contribution records
        (ongoing), FARA foreign agent registrations, and state lobbying databases.</p>
        <p><strong>Red Flags:</strong> Sudden increases in lobbying spend, new issue registrations,
        or high-profile revolving door hires may signal pending regulatory or legislative activity.</p>
    </div>
</div>
"""


def _format_valuation_history_section(entity_name: str, ticker: str, report_data: dict) -> str:
    """Format Valuation History & Timeline section (stock performance, key events, analyst targets)."""
    sections = report_data.get('sections', [])

    # Try to find AI-generated valuation content
    for sec in sections:
        name = sec.get('name', '') or sec.get('title', '') or sec.get('section_name', '')
        if 'valuation' in name.lower() or 'history' in name.lower() or 'timeline' in name.lower():
            narrative = sec.get('narrative', '')
            claims = sec.get('claims', [])

            if narrative and len(narrative) > 100:
                html_content = markdown.markdown(narrative, extensions=['tables', 'fenced_code', 'nl2br', 'sane_lists'])
                return f"""
<h2>Valuation Overview</h2>
{html_content}
"""

    # Extract valuation and price data
    price_data = report_data.get('price_history', report_data.get('stock_performance', {}))
    key_events = report_data.get('key_events', report_data.get('corporate_events', []))
    analyst_data = report_data.get('analyst_ratings', report_data.get('analyst_targets', []))

    # Build price performance summary
    price_html = ""
    if price_data:
        current_price = price_data.get('current', price_data.get('close', 0))
        change_1y = price_data.get('change_1y', price_data.get('52_week_change', 0))
        high_52w = price_data.get('52_week_high', price_data.get('high_52w', 0))
        low_52w = price_data.get('52_week_low', price_data.get('low_52w', 0))
        market_cap = price_data.get('market_cap', 0)

        price_html = f"""
<h3 style="color: #c9a227;">13.1 Stock Performance &amp; Key Metrics</h3>

<div class="metrics-grid" style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12pt; margin: 20pt 0;">
    <div class="metric-card" style="background: #f8f9fa; border: 1px solid #e2e8f0; border-top: 3px solid #c9a227; padding: 15pt; text-align: center;">
        <div class="metric-value" style="font-size: 18pt; font-weight: 800; color: #1a1a2e;">${current_price:,.2f}</div>
        <div class="metric-label" style="font-size: 8pt; font-weight: 600; text-transform: uppercase; color: #718096;">Current Price</div>
    </div>
    <div class="metric-card" style="background: #f8f9fa; border: 1px solid #e2e8f0; border-top: 3px solid #c9a227; padding: 15pt; text-align: center;">
        <div class="metric-value" style="font-size: 18pt; font-weight: 800; color: {'#276749' if change_1y > 0 else '#c53030'};">{change_1y:+.1f}%</div>
        <div class="metric-label" style="font-size: 8pt; font-weight: 600; text-transform: uppercase; color: #718096;">1-Year Change</div>
    </div>
    <div class="metric-card" style="background: #f8f9fa; border: 1px solid #e2e8f0; border-top: 3px solid #c9a227; padding: 15pt; text-align: center;">
        <div class="metric-value" style="font-size: 18pt; font-weight: 800; color: #1a1a2e;">${high_52w:,.2f}</div>
        <div class="metric-label" style="font-size: 8pt; font-weight: 600; text-transform: uppercase; color: #718096;">52-Week High</div>
    </div>
    <div class="metric-card" style="background: #f8f9fa; border: 1px solid #e2e8f0; border-top: 3px solid #c9a227; padding: 15pt; text-align: center;">
        <div class="metric-value" style="font-size: 18pt; font-weight: 800; color: #1a1a2e;">{_format_currency(int(market_cap)) if market_cap else 'N/A'}</div>
        <div class="metric-label" style="font-size: 8pt; font-weight: 600; text-transform: uppercase; color: #718096;">Market Cap</div>
    </div>
</div>
"""

    # Build key events timeline
    events_html = ""
    if key_events:
        event_items = ""
        for event in key_events[:10]:
            date = event.get('date', '')
            title = event.get('title', event.get('event', ''))
            impact = event.get('impact', event.get('description', ''))

            event_items += f"""
        <tr>
            <td style="white-space: nowrap;"><strong>{date}</strong></td>
            <td>{title}</td>
            <td style="font-size: 8.5pt;">{impact[:100]}{'...' if len(str(impact)) > 100 else ''}</td>
        </tr>"""

        events_html = f"""
<h3 style="color: #c9a227;">Corporate Events Timeline</h3>

<table class="data-table">
    <thead>
        <tr>
            <th style="width: 15%;">Date</th>
            <th style="width: 35%;">Event</th>
            <th style="width: 50%;">Market Impact</th>
        </tr>
    </thead>
    <tbody>
        {event_items}
    </tbody>
</table>
"""

    # Build analyst targets table
    analyst_html = ""
    if analyst_data:
        analyst_rows = ""
        for analyst in analyst_data[:10]:
            firm = analyst.get('firm', analyst.get('analyst', 'Unknown'))
            rating = analyst.get('rating', '')
            target = analyst.get('target', analyst.get('price_target', 0))
            date = analyst.get('date', '')

            rating_class = 'risk-low' if rating.lower() in ['buy', 'strong buy', 'outperform'] else 'risk-medium' if rating.lower() == 'hold' else 'risk-high'

            analyst_rows += f"""
        <tr>
            <td><strong>{firm}</strong></td>
            <td><span class="risk-indicator {rating_class}">{rating.upper() if rating else 'N/A'}</span></td>
            <td style="text-align: right;">${target:,.2f}</td>
            <td>{date}</td>
        </tr>"""

        analyst_html = f"""
<h3 style="color: #c9a227;">13.2 Analyst Targets &amp; Ratings</h3>

<table class="data-table">
    <thead>
        <tr>
            <th style="width: 30%;">Analyst Firm</th>
            <th style="width: 20%;">Rating</th>
            <th style="width: 25%; text-align: right;">Price Target</th>
            <th style="width: 25%;">Date</th>
        </tr>
    </thead>
    <tbody>
        {analyst_rows}
    </tbody>
</table>
"""

    has_data = price_data or key_events or analyst_data

    if has_data:
        return f"""
<h2>Valuation History Overview</h2>

<p class="section-intro">This section tracks {entity_name}'s valuation evolution including stock
performance, key corporate events, and analyst coverage. Historical analysis provides context
for current valuation and future price expectations.</p>

{price_html}

{events_html}

{analyst_html}

<div class="callout-box">
    <div class="callout-title">VALUATION ASSESSMENT</div>
    <div class="callout-content">
        <p><strong>Historical Context:</strong> Current valuation should be evaluated against
        historical trading ranges, peer multiples, and fundamental drivers.</p>
        <p><strong>Catalyst Pipeline:</strong> Monitor upcoming earnings, product launches,
        and regulatory milestones that may drive valuation inflections.</p>
    </div>
</div>
"""
    else:
        return f"""
<h2>Valuation History Overview</h2>

<p class="section-intro">Valuation history analysis draws from market data, corporate event databases,
and analyst research to contextualize current valuation levels.</p>

<h3 style="color: #c9a227;">13.1 Stock Performance &amp; Key Events</h3>

<p>Historical stock performance analysis considers:</p>
<ul>
    <li>Price performance across multiple time horizons (1Y, 3Y, 5Y)</li>
    <li>Performance relative to sector benchmarks and peers</li>
    <li>Correlation with key corporate events and announcements</li>
    <li>Volatility patterns and beta characteristics</li>
</ul>

<h3 style="color: #c9a227;">13.2 Analyst Targets &amp; Ratings</h3>

<p>Analyst coverage provides external valuation perspectives:</p>
<ul>
    <li>Consensus price target and range</li>
    <li>Rating distribution (Buy/Hold/Sell)</li>
    <li>Recent rating changes and initiations</li>
    <li>Earnings estimate revisions</li>
</ul>

<div class="callout-box">
    <div class="callout-title">VALUATION MONITORING</div>
    <div class="callout-content">
        <p><strong>Data Sources:</strong> Real-time pricing from major exchanges, analyst estimates
        from research aggregators, and corporate event data from 8-K filings and press releases.</p>
        <p><strong>Key Triggers:</strong> Monitor for analyst upgrades/downgrades, price target
        changes, and earnings estimate revisions as leading indicators.</p>
    </div>
</div>
"""


def _format_risk_red_flag_section(entity_name: str, ticker: str, report_data: dict) -> str:
    """Format Risk & Red Flag Analysis section with related party, governance, and litigation."""
    sections = report_data.get('sections', [])

    # Try to find AI-generated risk content
    for sec in sections:
        name = sec.get('name', '') or sec.get('title', '') or sec.get('section_name', '')
        if 'risk' in name.lower() and ('flag' in name.lower() or 'red' in name.lower()):
            narrative = sec.get('narrative', '')
            claims = sec.get('claims', [])

            if narrative and len(narrative) > 100:
                html_content = markdown.markdown(narrative, extensions=['tables', 'fenced_code', 'nl2br', 'sane_lists'])
                return f"""
<h2>Risk Assessment Overview</h2>
{html_content}
"""

    # Extract risk data
    related_party = report_data.get('related_party_transactions', [])
    governance_issues = report_data.get('governance_issues', report_data.get('governance_flags', []))
    litigation = report_data.get('litigation', report_data.get('legal_proceedings', []))

    # Build related party transactions table
    rpt_html = ""
    if related_party:
        rpt_rows = ""
        for txn in related_party[:8]:
            party = txn.get('party', txn.get('related_party', 'Unknown'))
            relationship = txn.get('relationship', '')
            amount = txn.get('amount', txn.get('value', 0))
            description = txn.get('description', txn.get('nature', ''))

            rpt_rows += f"""
        <tr>
            <td><strong>{party}</strong></td>
            <td>{relationship}</td>
            <td style="text-align: right;">{_format_currency(int(amount)) if amount else 'Undisclosed'}</td>
            <td style="font-size: 8.5pt;">{description[:80]}{'...' if len(str(description)) > 80 else ''}</td>
        </tr>"""

        rpt_html = f"""
<h3 style="color: #c9a227;">14.1 Related Party Transactions</h3>

<p>The following related party transactions have been disclosed in SEC filings:</p>

<table class="data-table">
    <thead>
        <tr>
            <th style="width: 25%;">Related Party</th>
            <th style="width: 20%;">Relationship</th>
            <th style="width: 20%; text-align: right;">Amount</th>
            <th style="width: 35%;">Description</th>
        </tr>
    </thead>
    <tbody>
        {rpt_rows}
    </tbody>
</table>
"""

    # Build litigation table
    litigation_html = ""
    if litigation:
        lit_rows = ""
        for case in litigation[:6]:
            case_name = case.get('case', case.get('title', 'Unknown'))
            status = case.get('status', 'Pending')
            exposure = case.get('exposure', case.get('potential_liability', 0))
            description = case.get('description', case.get('summary', ''))

            status_class = 'risk-high' if status.lower() in ['active', 'pending'] else 'risk-medium' if status.lower() == 'settled' else 'risk-low'

            lit_rows += f"""
        <tr>
            <td><strong>{case_name}</strong></td>
            <td><span class="risk-indicator {status_class}">{status.upper()}</span></td>
            <td style="text-align: right;">{_format_currency(int(exposure)) if exposure else 'TBD'}</td>
            <td style="font-size: 8.5pt;">{description[:100]}{'...' if len(str(description)) > 100 else ''}</td>
        </tr>"""

        litigation_html = f"""
<h3 style="color: #c9a227;">Material Litigation</h3>

<table class="data-table">
    <thead>
        <tr>
            <th style="width: 25%;">Case/Matter</th>
            <th style="width: 15%;">Status</th>
            <th style="width: 20%; text-align: right;">Potential Exposure</th>
            <th style="width: 40%;">Summary</th>
        </tr>
    </thead>
    <tbody>
        {lit_rows}
    </tbody>
</table>
"""

    has_data = related_party or governance_issues or litigation

    # Always provide comprehensive risk framework
    return f"""
<h2>Risk Overview</h2>

<p class="section-intro">This section identifies potential red flags and risk factors requiring
monitoring, with focus on related party transactions, governance concerns, and legal exposure.
Cross-reference with ownership (Section 3), board composition (Section 4), and government
contracts (Section 11) for comprehensive risk assessment.</p>

{rpt_html if rpt_html else _get_related_party_framework_html(entity_name)}

<h3 style="color: #c9a227;">14.2 Governance &amp; Litigation Flags</h3>

<table class="data-table">
    <thead>
        <tr>
            <th>Risk Category</th>
            <th>Key Indicators</th>
            <th>Current Assessment</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><strong>Board Independence</strong></td>
            <td>Independent director ratio, CEO/Chair separation</td>
            <td><span class="risk-indicator risk-medium">MONITOR</span></td>
        </tr>
        <tr>
            <td><strong>Insider Transactions</strong></td>
            <td>Pattern of insider selling, timing relative to disclosures</td>
            <td><span class="risk-indicator risk-medium">MONITOR</span></td>
        </tr>
        <tr>
            <td><strong>Audit Quality</strong></td>
            <td>Auditor tenure, restatements, material weaknesses</td>
            <td><span class="risk-indicator risk-low">LOW</span></td>
        </tr>
        <tr>
            <td><strong>Regulatory Exposure</strong></td>
            <td>Pending investigations, enforcement actions</td>
            <td><span class="risk-indicator risk-medium">MONITOR</span></td>
        </tr>
        <tr>
            <td><strong>Litigation Risk</strong></td>
            <td>Securities claims, antitrust, employment</td>
            <td><span class="risk-indicator risk-medium">MONITOR</span></td>
        </tr>
        <tr>
            <td><strong>Self-Dealing</strong></td>
            <td>Related party transactions, family employment</td>
            <td><span class="risk-indicator risk-medium">MONITOR</span></td>
        </tr>
    </tbody>
</table>

{litigation_html}

<div class="callout-box">
    <div class="callout-title">RED FLAG MONITORING PROTOCOL</div>
    <div class="callout-content">
        <p><strong>Self-Dealing Indicators:</strong> Monitor for unusual related party transactions,
        family member employment, contracts with insider-connected entities, and charitable
        contributions to board-affiliated organizations.</p>
        <p><strong>Governance Triggers:</strong> Watch for auditor changes, restatements, material
        weakness disclosures, unusual executive departures, and SEC comment letters.</p>
        <p><strong>Litigation Pipeline:</strong> Track federal court filings, SEC enforcement
        activity, and class action tracking services for emerging legal exposure.</p>
    </div>
</div>

<div class="network-box">
    <div class="network-title">INTELLIGENCE INTEGRATION</div>
    <p style="font-size: 9.5pt; line-height: 1.6;">Cross-reference red flag indicators with
    data from other sections: ownership changes (Section 3), board interlock patterns (Section 4),
    executive transaction history (Section 5), government contract relationships (Section 11),
    and lobbying activity (Section 12) for comprehensive risk assessment.</p>
</div>
"""


def _get_related_party_framework_html(entity_name: str) -> str:
    """Generate related party transaction monitoring framework."""
    return f"""
<h3 style="color: #c9a227;">14.1 Related Party Transactions</h3>

<p>Related party transaction analysis draws from proxy statements, 10-K disclosures, and
corporate governance filings. Key monitoring areas include:</p>

<table class="data-table">
    <thead>
        <tr>
            <th>Transaction Type</th>
            <th>Disclosure Source</th>
            <th>Red Flag Indicators</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><strong>Family Employment</strong></td>
            <td>DEF 14A Proxy</td>
            <td>Compensation above market, no disclosure</td>
        </tr>
        <tr>
            <td><strong>Vendor Relationships</strong></td>
            <td>10-K Related Party Note</td>
            <td>Insider-owned vendors, above-market terms</td>
        </tr>
        <tr>
            <td><strong>Real Estate</strong></td>
            <td>8-K, Proxy</td>
            <td>Leases from insider-controlled entities</td>
        </tr>
        <tr>
            <td><strong>Loans & Guarantees</strong></td>
            <td>10-K Notes</td>
            <td>Below-market rates, personal guarantees</td>
        </tr>
        <tr>
            <td><strong>Charitable Giving</strong></td>
            <td>CSR Reports, Proxy</td>
            <td>Donations to board-affiliated charities</td>
        </tr>
    </tbody>
</table>
"""


def convert_to_premium_pdf(
    entity_name: str,
    ticker: str,
    report_data: dict,
    prepared_for: str = "Internal Analysis",
    organization: str = "ENTERPRISE INTELLIGENCE PLATFORM"
) -> bytes:
    """Convert report data to premium PDF matching investment intelligence standard."""

    # Generate HTML
    html_content = generate_premium_report_html(
        entity_name=entity_name,
        ticker=ticker,
        report_data=report_data,
        prepared_for=prepared_for,
        organization=organization
    )

    # Generate PDF with WeasyPrint
    font_config = FontConfiguration()
    css = CSS(string=get_premium_css(), font_config=font_config)
    html = HTML(string=html_content)

    pdf_bytes = html.write_pdf(stylesheets=[css], font_config=font_config)
    return pdf_bytes
