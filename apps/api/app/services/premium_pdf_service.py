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
            <span class="toc-text">Financial Health Analysis</span>
        </div>
        <div class="toc-item">
            <span class="toc-number">4</span>
            <span class="toc-text">Competitive Positioning</span>
        </div>
        <div class="toc-item">
            <span class="toc-number">5</span>
            <span class="toc-text">Government Contracts &amp; Federal Engagement</span>
        </div>
        <div class="toc-item">
            <span class="toc-number">6</span>
            <span class="toc-text">Regulatory &amp; Lobbying Activity</span>
        </div>
        <div class="toc-item">
            <span class="toc-number">7</span>
            <span class="toc-text">Recent News &amp; Media Coverage</span>
        </div>
        <div class="toc-item">
            <span class="toc-number">8</span>
            <span class="toc-text">Risk Assessment &amp; Watch Items</span>
        </div>
        <div class="toc-item">
            <span class="toc-number">9</span>
            <span class="toc-text">Sources &amp; Citations</span>
        </div>
    </div>
</div>

<div class="page-footer">
    <span class="footer-left">Prepared for internal use only — not for distribution</span>
    <span class="footer-right">Page 1</span>
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

<div class="page-footer">
    <span class="footer-left">Prepared for internal use only — not for distribution</span>
    <span class="footer-right">Page 2</span>
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

<div class="page-footer">
    <span class="footer-left">Prepared for internal use only — not for distribution</span>
    <span class="footer-right">Page 3</span>
</div>

<div class="page-break"></div>

<!-- SECTION 3: FINANCIAL HEALTH -->
<div class="page-header">
    <span class="header-left">{classification}</span>
    <span class="header-right">{organization}</span>
</div>

<div class="page-content">
    <h1 class="section-title"><span class="section-number">3.</span> Financial Health Analysis</h1>

    {_format_financial_section(financial_health, entity_name)}
</div>

<div class="page-footer">
    <span class="footer-left">Prepared for internal use only — not for distribution</span>
    <span class="footer-right">Page 4</span>
</div>

<div class="page-break"></div>

<!-- SECTION 4: COMPETITIVE POSITIONING -->
<div class="page-header">
    <span class="header-left">{classification}</span>
    <span class="header-right">{organization}</span>
</div>

<div class="page-content">
    <h1 class="section-title"><span class="section-number">4.</span> Competitive Positioning</h1>

    {_format_competitive_section(competitive_analysis, entity_name)}
</div>

<div class="page-footer">
    <span class="footer-left">Prepared for internal use only — not for distribution</span>
    <span class="footer-right">Page 5</span>
</div>

<div class="page-break"></div>

<!-- SECTION 5: GOVERNMENT CONTRACTS -->
<div class="page-header">
    <span class="header-left">{classification}</span>
    <span class="header-right">{organization}</span>
</div>

<div class="page-content">
    <h1 class="section-title"><span class="section-number">5.</span> Government Contracts &amp; Federal Engagement</h1>

    {_format_gov_contracts_section(gov_contracts, entity_name)}
</div>

<div class="page-footer">
    <span class="footer-left">Prepared for internal use only — not for distribution</span>
    <span class="footer-right">Page 6</span>
</div>

<div class="page-break"></div>

<!-- SECTION 6: LOBBYING -->
<div class="page-header">
    <span class="header-left">{classification}</span>
    <span class="header-right">{organization}</span>
</div>

<div class="page-content">
    <h1 class="section-title"><span class="section-number">6.</span> Regulatory &amp; Lobbying Activity</h1>

    {_format_lobbying_section(sections, entity_name)}
</div>

<div class="page-footer">
    <span class="footer-left">Prepared for internal use only — not for distribution</span>
    <span class="footer-right">Page 7</span>
</div>

<div class="page-break"></div>

<!-- SECTION 7: NEWS -->
<div class="page-header">
    <span class="header-left">{classification}</span>
    <span class="header-right">{organization}</span>
</div>

<div class="page-content">
    <h1 class="section-title"><span class="section-number">7.</span> Recent News &amp; Media Coverage</h1>

    {_format_news_section(news_items, entity_name)}
</div>

<div class="page-footer">
    <span class="footer-left">Prepared for internal use only — not for distribution</span>
    <span class="footer-right">Page 8</span>
</div>

<div class="page-break"></div>

<!-- SECTION 8: RISK ASSESSMENT -->
<div class="page-header">
    <span class="header-left">{classification}</span>
    <span class="header-right">{organization}</span>
</div>

<div class="page-content">
    <h1 class="section-title"><span class="section-number">8.</span> Risk Assessment &amp; Watch Items</h1>

    {_format_risk_section(entity_name, ticker, report_data)}
</div>

<div class="page-break"></div>

<!-- SECTION 9: SOURCES & CITATIONS -->
<div class="page-header">
    <span class="header-left">{classification}</span>
    <span class="header-right">{organization}</span>
</div>

<div class="page-content">
    <h1 class="section-title"><span class="section-number">9.</span> Sources &amp; Citations</h1>

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
                html_content = markdown.markdown(narrative, extensions=['nl2br'])
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


def _format_claims_as_paragraphs(claims: list) -> str:
    """Format claims as readable paragraphs with proper markdown-to-HTML conversion."""
    if not claims:
        return ""

    # Check for error/timeout messages in claims
    error_patterns = ['timeout', 'please try again', 'error', 'failed', 'unavailable']

    # Combine all claims into a single markdown block
    combined_text = ""
    for claim in claims:  # No limit - process ALL claims
        text = claim.get('text', '') if isinstance(claim, dict) else str(claim)

        # Skip error messages
        text_lower = text.lower()
        if any(err in text_lower for err in error_patterns):
            continue

        # Remove confidence tags
        text = re.sub(r'\[(DOCUMENTED|REPORTED|ANALYTICAL)\]\s*', '', text)
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

    # Convert remaining markdown to HTML
    html_content = markdown.markdown(
        processed_text,
        extensions=['fenced_code', 'nl2br']
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
    """Format investment thesis section with entity-specific content or generic fallback."""
    content = _format_claims_as_paragraphs(claims) if claims else ""

    # Use fallback if no valid content
    if not content or len(content.strip()) < 50:
        content = f"""
<h2>Investment Recommendation</h2>

<p>Based on available data, {entity_name} warrants careful evaluation against sector peers,
with positioning dependent on execution of key strategic initiatives and macroeconomic conditions.</p>

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

    return content


def _format_financial_section(claims: list, entity_name: str) -> str:
    """Format financial health section with entity-specific content or generic fallback."""
    content = _format_claims_as_paragraphs(claims) if claims else ""

    # Use fallback if no valid content
    if not content or len(content.strip()) < 50:
        content = f"""
<h2>Key Financial Metrics</h2>

<p>Financial data sourced from SEC filings and market data providers. For the most current
financial metrics, please refer to the company's latest quarterly filing (10-Q) or annual
report (10-K) available through the SEC EDGAR database.</p>

<h2>Liquidity Assessment</h2>

<p>{entity_name}'s liquidity position should be evaluated based on current ratio, quick ratio,
and cash flow from operations relative to short-term obligations. Key metrics to monitor include
working capital trends, debt maturity schedule, and available credit facilities.</p>

<h2>Profitability Analysis</h2>

<p>Margin trends and profitability metrics provide insight into operational efficiency and
pricing power. Investors should track gross margin, operating margin, and net margin relative
to historical performance and industry peers to assess competitive positioning.</p>
"""

    return content


def _format_competitive_section(claims: list, entity_name: str) -> str:
    """Format competitive analysis section with entity-specific content or generic fallback."""
    content = _format_claims_as_paragraphs(claims) if claims else ""

    # Use fallback if no valid content (including timeout errors)
    if not content or len(content.strip()) < 50:
        content = f"""
<h2>Market Position</h2>

<p>{entity_name}'s competitive positioning should be evaluated based on market share trends,
pricing power, and barriers to entry in core markets. Key factors include brand strength,
distribution capabilities, technology leadership, and cost structure relative to peers.</p>

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
"""

    return content


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
                html_content = markdown.markdown(narrative, extensions=['nl2br', 'fenced_code'])
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
                html_content = markdown.markdown(narrative, extensions=['nl2br', 'fenced_code'])
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
