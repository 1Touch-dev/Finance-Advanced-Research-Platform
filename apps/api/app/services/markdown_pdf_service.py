"""
Markdown to PDF converter with beautiful styling.

Uses WeasyPrint to convert markdown to beautifully formatted PDF reports
with professional styling suitable for enterprise intelligence reports.
"""
import io
import markdown
from datetime import datetime
from typing import Optional

try:
    from weasyprint import HTML, CSS
    from weasyprint.text.fonts import FontConfiguration
    WEASYPRINT_OK = True
except ImportError:
    WEASYPRINT_OK = False

# Professional CSS styling for intelligence reports
REPORT_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

:root {
    --primary: #6366f1;
    --primary-dark: #4f46e5;
    --bg-dark: #0f172a;
    --bg-card: #1e293b;
    --text-primary: #f8fafc;
    --text-secondary: #94a3b8;
    --text-muted: #64748b;
    --border: #334155;
    --success: #22c55e;
    --warning: #f59e0b;
    --danger: #ef4444;
    --info: #3b82f6;
}

@page {
    size: letter;
    margin: 1.5cm 1.8cm;
    @top-left {
        content: "ENTERPRISE INTELLIGENCE PLATFORM";
        font-size: 8pt;
        color: #6366f1;
        font-family: 'Inter', sans-serif;
    }
    @top-right {
        content: "CONFIDENTIAL";
        font-size: 8pt;
        color: #94a3b8;
        font-family: 'Inter', sans-serif;
    }
    @bottom-center {
        content: "Page " counter(page) " of " counter(pages);
        font-size: 8pt;
        color: #64748b;
        font-family: 'Inter', sans-serif;
    }
}

@page:first {
    @top-left { content: none; }
    @top-right { content: none; }
}

* {
    box-sizing: border-box;
}

body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    font-size: 10pt;
    line-height: 1.6;
    color: #1e293b;
    background: white;
    margin: 0;
    padding: 0;
}

/* Typography */
h1 {
    font-size: 24pt;
    font-weight: 700;
    color: #0f172a;
    border-bottom: 3px solid #6366f1;
    padding-bottom: 12px;
    margin-top: 30px;
    margin-bottom: 20px;
    page-break-after: avoid;
}

h1:first-of-type {
    font-size: 28pt;
    text-align: center;
    border-bottom: none;
    margin-top: 60px;
    color: #1e293b;
}

h2 {
    font-size: 16pt;
    font-weight: 600;
    color: #334155;
    margin-top: 24px;
    margin-bottom: 12px;
    page-break-after: avoid;
}

h3 {
    font-size: 13pt;
    font-weight: 600;
    color: #475569;
    margin-top: 18px;
    margin-bottom: 10px;
    page-break-after: avoid;
}

h4 {
    font-size: 11pt;
    font-weight: 600;
    color: #6366f1;
    margin-top: 14px;
    margin-bottom: 8px;
    page-break-after: avoid;
}

p {
    margin-bottom: 10px;
    text-align: justify;
    orphans: 3;
    widows: 3;
}

/* Lists */
ul, ol {
    margin-left: 0;
    padding-left: 24px;
    margin-bottom: 12px;
}

li {
    margin-bottom: 6px;
    line-height: 1.5;
}

li > ul, li > ol {
    margin-top: 6px;
    margin-bottom: 6px;
}

/* Tables */
table {
    width: 100%;
    border-collapse: collapse;
    margin: 16px 0 24px 0;
    font-size: 9pt;
    page-break-inside: avoid;
}

thead {
    background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
}

th {
    padding: 12px 10px;
    text-align: left;
    font-weight: 600;
    color: white;
    font-size: 9pt;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border: none;
}

td {
    padding: 10px;
    border-bottom: 1px solid #e2e8f0;
    vertical-align: top;
}

tr:nth-child(even) {
    background-color: #f8fafc;
}

tr:hover {
    background-color: #f1f5f9;
}

/* Strong/Bold for key metrics */
strong {
    font-weight: 600;
    color: #1e293b;
}

/* Code blocks for data */
code {
    background: #f1f5f9;
    padding: 2px 6px;
    border-radius: 4px;
    font-family: 'SF Mono', 'Fira Code', monospace;
    font-size: 9pt;
    color: #6366f1;
}

pre {
    background: #1e293b;
    color: #e2e8f0;
    padding: 16px;
    border-radius: 8px;
    overflow-x: auto;
    font-size: 9pt;
    line-height: 1.5;
    margin: 16px 0;
}

pre code {
    background: transparent;
    color: inherit;
    padding: 0;
}

/* Horizontal rules */
hr {
    border: none;
    border-top: 2px solid #e2e8f0;
    margin: 30px 0;
    page-break-after: avoid;
}

/* Blockquotes for highlights */
blockquote {
    border-left: 4px solid #6366f1;
    background: linear-gradient(90deg, #f8fafc 0%, white 100%);
    margin: 16px 0;
    padding: 16px 20px;
    font-style: italic;
    color: #475569;
}

/* Special styling for key sections */
.executive-dashboard {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    color: white;
    padding: 24px;
    border-radius: 12px;
    margin: 24px 0;
}

/* Recommendation badges */
.recommendation-buy {
    background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
    color: white;
    padding: 8px 20px;
    border-radius: 20px;
    font-weight: 700;
    display: inline-block;
}

.recommendation-hold {
    background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
    color: white;
    padding: 8px 20px;
    border-radius: 20px;
    font-weight: 700;
    display: inline-block;
}

.recommendation-sell {
    background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
    color: white;
    padding: 8px 20px;
    border-radius: 20px;
    font-weight: 700;
    display: inline-block;
}

/* Grade badges */
.grade-a { color: #22c55e; font-weight: 700; font-size: 18pt; }
.grade-b { color: #3b82f6; font-weight: 700; font-size: 18pt; }
.grade-c { color: #f59e0b; font-weight: 700; font-size: 18pt; }
.grade-d { color: #f97316; font-weight: 700; font-size: 18pt; }
.grade-f { color: #ef4444; font-weight: 700; font-size: 18pt; }

/* Risk colors */
.risk-critical { color: #ef4444; font-weight: 600; }
.risk-high { color: #f97316; font-weight: 600; }
.risk-medium { color: #f59e0b; font-weight: 600; }
.risk-low { color: #22c55e; font-weight: 600; }

/* SWOT Grid styling */
.swot-strength { color: #22c55e; }
.swot-weakness { color: #ef4444; }
.swot-opportunity { color: #3b82f6; }
.swot-threat { color: #f59e0b; }

/* Cover page styling */
.cover-meta {
    text-align: center;
    color: #64748b;
    font-size: 10pt;
    margin-top: 20px;
}

.cover-badge {
    text-align: center;
    margin: 40px 0;
}

/* Footer styling */
.footer {
    margin-top: 40px;
    padding-top: 20px;
    border-top: 2px solid #e2e8f0;
    text-align: center;
    color: #64748b;
    font-size: 9pt;
}

/* Print optimizations */
@media print {
    body {
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
    }

    h1, h2, h3, h4 {
        page-break-after: avoid;
    }

    table, figure, img {
        page-break-inside: avoid;
    }

    p {
        orphans: 3;
        widows: 3;
    }
}

/* Confidence tag styling */
em {
    font-style: normal;
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 8pt;
    font-weight: 500;
}

/* Data source tags */
.source-documented {
    background: #dcfce7;
    color: #166534;
}

.source-reported {
    background: #fef3c7;
    color: #92400e;
}

.source-analytical {
    background: #dbeafe;
    color: #1e40af;
}
"""


def convert_markdown_to_pdf(
    markdown_content: str,
    output_path: Optional[str] = None,
    title: str = "Intelligence Report"
) -> bytes:
    """
    Convert markdown content to a beautifully formatted PDF.

    Args:
        markdown_content: The markdown text to convert
        output_path: Optional path to save the PDF file
        title: Document title for metadata

    Returns:
        PDF bytes
    """
    if not WEASYPRINT_OK:
        raise RuntimeError("WeasyPrint is not installed. Run: pip install weasyprint")

    # Convert markdown to HTML
    md = markdown.Markdown(
        extensions=[
            'tables',
            'fenced_code',
            'codehilite',
            'toc',
            'attr_list',
            'md_in_html',
        ]
    )
    html_content = md.convert(markdown_content)

    # Wrap in full HTML document
    full_html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """

    # Configure fonts
    font_config = FontConfiguration()

    # Create PDF
    html = HTML(string=full_html)
    css = CSS(string=REPORT_CSS, font_config=font_config)

    if output_path:
        html.write_pdf(output_path, stylesheets=[css], font_config=font_config)
        with open(output_path, 'rb') as f:
            return f.read()
    else:
        pdf_bytes = html.write_pdf(stylesheets=[css], font_config=font_config)
        return pdf_bytes


def _clean_news_text(text: str) -> str:
    """Clean news text by removing JSON metadata and URLs."""
    import re
    if not text:
        return ''
    # Remove JSON array/dict at the end (e.g., [{'name': 'Mashable', ...}])
    clean = re.sub(r"\s*\[\{['\"]name['\"].*$", "", text, flags=re.DOTALL)
    # Remove trailing URLs
    clean = re.sub(r"\s*https?://\S+\s*$", "", clean)
    # Remove [DOCUMENTED] etc tags
    clean = re.sub(r"\[(DOCUMENTED|REPORTED|ANALYTICAL)\]\s*", "", clean)
    return clean.strip()


def _parse_news_headline(text: str) -> tuple:
    """Parse news headline, source, and date from text."""
    import re
    if not text:
        return '', 'Unknown', ''

    # First clean the text of JSON metadata and trailing URLs
    clean_text = _clean_news_text(text)

    # Pattern 1: "Headline - Source (ISO datetime)" e.g., "Title - CNN (2026-07-19T22:40:14.000Z)"
    match = re.match(r'^(.+?) - ([^(]+) \((\d{4}-\d{2}-\d{2})(?:T[\d:.]+Z?)?\)', clean_text)
    if match:
        headline = match.group(1).strip()
        source = match.group(2).strip()
        date = match.group(3)  # Just the YYYY-MM-DD part
        return headline, source, date

    # Pattern 2: "Headline - Source (simple date)" e.g., "Title - CNN (2026-07-19)"
    match = re.match(r'^(.+?) - ([^(]+) \((\d{4}-\d{2}-\d{2})\)', clean_text)
    if match:
        return match.group(1).strip(), match.group(2).strip(), match.group(3)

    # Pattern 3: Just "Headline - Source" without date
    match = re.match(r'^(.+?) - (.+)$', clean_text)
    if match:
        return match.group(1).strip(), match.group(2).strip(), ''

    # Fallback: return cleaned text as headline
    return clean_text[:100] if clean_text else text[:100], 'Unknown', ''


def generate_enhanced_markdown_report(report_data: dict) -> str:
    """
    Generate a comprehensive markdown report from enhanced intelligence data.

    Args:
        report_data: The enhanced report dictionary

    Returns:
        Markdown formatted string
    """
    import re
    md = []

    # Use `or` (not dict.get's default arg) — these keys are often present
    # with an explicit None value (e.g. non-enhanced reports, older reports),
    # and .get(key, default) only falls back when the key is MISSING entirely.
    entity_name = report_data.get('entity_name') or 'Unknown Entity'
    ticker = report_data.get('ticker') or ''
    report_id = report_data.get('report_id') or ''
    gen_at = report_data.get('generated_at') or datetime.utcnow().isoformat()

    # Title
    ticker_str = f" ({ticker})" if ticker else ""
    md.append(f"# {entity_name}{ticker_str} — Enhanced Intelligence Report")
    md.append("")
    md.append(f"**Generated:** {gen_at[:19].replace('T', ' ')} UTC")
    md.append(f"**Report ID:** {report_id}")
    md.append(f"**Classification:** CONFIDENTIAL — Enterprise Intelligence Platform")
    md.append("")
    md.append("---")
    md.append("")

    # Executive Dashboard
    summary = report_data.get('summary') or {}
    investment_thesis = report_data.get('investment_thesis') or {}
    risk_matrix = report_data.get('risk_matrix') or {}
    financial_health = report_data.get('financial_health') or {}

    md.append("## Executive Dashboard")
    md.append("")
    md.append("| Metric | Value |")
    md.append("|--------|-------|")

    if investment_thesis:
        rec = investment_thesis.get('recommendation', 'N/A')
        conv = investment_thesis.get('conviction', 'N/A')
        md.append(f"| **Investment Recommendation** | **{rec}** ({conv} conviction) |")

    if financial_health:
        grade = financial_health.get('grade', 'N/A')
        md.append(f"| **Financial Health Grade** | **{grade}** |")

    if risk_matrix:
        score = risk_matrix.get('overall_score', 'N/A')
        md.append(f"| **Overall Risk Score** | **{score}/100** |")

    md.append(f"| SEC Filings Analyzed | {summary.get('sec_filings', 0)} |")
    md.append(f"| Government Contracts | {summary.get('contracts_found', 0)} (${summary.get('total_obligated_usd', 0):,.0f}) |")
    md.append(f"| Lobbying Filings | {summary.get('lobbying_filings', 0)} |")
    md.append(f"| News Articles | {summary.get('news_articles', 0)} |")
    md.append("")
    md.append("---")
    md.append("")

    # Process sections
    sections = report_data.get('sections') or []

    # Extract key sections
    section_map = {sec.get('name', ''): sec for sec in sections}

    # Investment Thesis
    if 'Investment Thesis' in section_map:
        sec = section_map['Investment Thesis']
        text = sec.get('claims', [{}])[0].get('text', '')
        if text:
            md.append("## Investment Thesis")
            md.append("")
            md.append(text)
            md.append("")
            md.append("---")
            md.append("")

    # Executive Summary
    if 'Executive Summary' in section_map:
        sec = section_map['Executive Summary']
        text = sec.get('claims', [{}])[0].get('text', '')
        if text:
            md.append("## Executive Summary")
            md.append("")
            md.append(text)
            md.append("")
            md.append("---")
            md.append("")

    # SWOT Analysis
    swot = report_data.get('swot_analysis') or {}
    if swot:
        md.append("## SWOT Analysis")
        md.append("")

        md.append("### Strengths")
        md.append("")
        for i, s in enumerate(swot.get('strengths', [])[:7], 1):
            if isinstance(s, dict):
                desc = s.get('description', '')
                if desc:
                    md.append(f"{i}. **{desc}**")
                    if s.get('evidence'):
                        md.append(f"   - Evidence: {s['evidence'][:150]}...")
                    if s.get('impact'):
                        md.append(f"   - Impact: {s['impact']}/5")
                    md.append("")

        md.append("### Weaknesses")
        md.append("")
        for i, w in enumerate(swot.get('weaknesses', [])[:7], 1):
            if isinstance(w, dict) and w.get('description'):
                md.append(f"{i}. **{w['description']}**")
                md.append("")

        md.append("### Opportunities")
        md.append("")
        for i, o in enumerate(swot.get('opportunities', [])[:7], 1):
            if isinstance(o, dict) and o.get('description'):
                md.append(f"{i}. **{o['description']}**")
                md.append("")

        md.append("### Threats")
        md.append("")
        for i, t in enumerate(swot.get('threats', [])[:7], 1):
            if isinstance(t, dict) and t.get('description'):
                md.append(f"{i}. **{t['description']}**")
                md.append("")

        if swot.get('synthesis'):
            md.append("### Strategic Synthesis")
            md.append("")
            md.append(swot['synthesis'])
            md.append("")

        md.append("---")
        md.append("")

    # Risk Matrix
    if risk_matrix:
        md.append("## Risk Assessment Matrix")
        md.append("")
        md.append(f"**Overall Risk Score:** {risk_matrix.get('overall_score', 0)}/100")
        md.append("")
        md.append("### Risk Distribution")
        md.append("")
        md.append(f"- **Critical Risks:** {len(risk_matrix.get('critical_risks', []))}")
        md.append(f"- **High Risks:** {len(risk_matrix.get('high_risks', []))}")
        md.append(f"- **Medium Risks:** {len(risk_matrix.get('medium_risks', []))}")
        md.append(f"- **Low Risks:** {len(risk_matrix.get('low_risks', []))}")
        md.append("")

        top_risks = risk_matrix.get('top_priority_risks', [])
        if top_risks:
            md.append("### Top Priority Risks")
            md.append("")
            md.append("| ID | Risk | Category | Severity | Likelihood | Score |")
            md.append("|:--:|------|----------|:--------:|:----------:|:-----:|")
            for risk in top_risks[:5]:
                desc = risk.get('description', '')[:60]
                md.append(f"| {risk.get('id', '-')} | {desc}... | {risk.get('category', '')} | {risk.get('severity', '')}/5 | {risk.get('likelihood', '')}/5 | **{risk.get('score', '')}** |")
            md.append("")

        md.append("---")
        md.append("")

    # Financial Health
    if 'Financial Health Summary' in section_map:
        sec = section_map['Financial Health Summary']
        text = sec.get('claims', [{}])[0].get('text', '')
        if text:
            md.append("## Financial Health Summary")
            md.append("")
            if financial_health:
                md.append(f"### Overall Grade: {financial_health.get('grade', 'N/A')}")
                md.append("")
            md.append(text)
            md.append("")
            md.append("---")
            md.append("")

    # Competitive Analysis
    if 'Competitive Analysis' in section_map:
        sec = section_map['Competitive Analysis']
        text = sec.get('claims', [{}])[0].get('text', '')
        if text:
            md.append("## Competitive Analysis")
            md.append("")
            md.append(text)
            md.append("")
            md.append("---")
            md.append("")

    # Government Contracts
    for sec in sections:
        if 'Government Contracts' in sec.get('name', ''):
            data = sec.get('data', {})
            claims = sec.get('claims', [])

            md.append("## Government Contracts & Procurement")
            md.append("")
            md.append(f"**Total Obligated:** ${data.get('total_obligated_usd', 0):,.0f}")
            md.append(f"**Award Count:** {data.get('award_count', 0)}")
            md.append("")
            md.append("### Contract Details")
            md.append("")

            for claim in claims[:12]:
                text = claim.get('text', '')
                if text:
                    md.append(f"- {text[:200]}")
            md.append("")
            md.append("---")
            md.append("")
            break

    # Lobbying Activity
    for sec in sections:
        if 'Lobbying' in sec.get('name', ''):
            data = sec.get('data', {})

            md.append("## Lobbying Activity")
            md.append("")
            md.append(f"**Total Filings:** {data.get('total_lobbying_filings', 0)}")
            md.append(f"**As Registrant:** {data.get('as_registrant_count', 0)}")
            md.append("")
            md.append("### Issue Areas")
            md.append("")
            for area in data.get('issue_areas', [])[:10]:
                md.append(f"- {area}")
            md.append("")
            md.append("---")
            md.append("")
            break

    # News - with clean formatting
    for sec in sections:
        if 'News' in sec.get('name', ''):
            claims = sec.get('claims', [])
            if claims:
                md.append("## Recent News & Media Coverage")
                md.append("")
                md.append("| Date | Headline | Source |")
                md.append("|------|----------|--------|")
                for claim in claims[:12]:
                    text = claim.get('text', '')
                    if text:
                        headline, source, date = _parse_news_headline(text)
                        if headline:
                            md.append(f"| {date} | {headline[:70]}... | {source} |")
                md.append("")
                md.append("---")
                md.append("")
            break

    # Social Media
    for sec in sections:
        if 'Social Media' in sec.get('name', ''):
            data = sec.get('data', {})
            twitter = data.get('twitter', {})
            instagram = data.get('instagram', {})
            youtube = data.get('youtube', {})

            md.append("## Social Media Footprint")
            md.append("")
            md.append("| Platform | Handle | Followers | Posts/Videos |")
            md.append("|----------|--------|----------:|-------------:|")
            if twitter:
                md.append(f"| Twitter/X | @{twitter.get('username', 'N/A')} | {twitter.get('followers', 0):,} | {twitter.get('tweets_count', 'N/A')} |")
            if instagram:
                md.append(f"| Instagram | @{instagram.get('username', 'N/A')} | {instagram.get('followers', 0):,} | {instagram.get('posts_count', 'N/A')} |")
            if youtube:
                md.append(f"| YouTube | {youtube.get('channel_name', 'N/A')} | {youtube.get('subscribers', 0):,} | {youtube.get('video_count', 'N/A')} |")
            md.append("")
            md.append("---")
            md.append("")
            break

    # Data Sources
    ds = report_data.get('data_sources') or {}
    md.append("## Data Sources & Methodology")
    md.append("")
    md.append("This report was generated using the following data sources:")
    md.append("")

    sources = []
    if ds.get('wikipedia'): sources.append("Wikipedia REST API")
    if ds.get('sec_investors'): sources.append(f"SEC EDGAR ({ds.get('sec_investors', 0)} investor filings)")
    if ds.get('yfinance'): sources.append("Yahoo Finance (fundamentals)")
    if ds.get('valuation'): sources.append("DCF Valuation Model")
    if ds.get('technicals'): sources.append("Technical Analysis Indicators")
    if ds.get('apify_news'): sources.append(f"Google News via Apify ({ds.get('apify_news', 0)} articles)")
    if ds.get('enhanced_narrative'): sources.append("GPT-4o-mini (AI analysis)")

    for src in sources:
        md.append(f"- {src}")
    md.append("")

    # Footer
    md.append("---")
    md.append("")
    md.append("## Classification & Disclaimer")
    md.append("")
    md.append("**CONFIDENTIAL** — This document contains proprietary intelligence analysis.")
    md.append("")
    md.append("*Generated by Enterprise Intelligence Platform*")
    md.append(f"*Report ID: {report_id} | Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}*")

    return '\n'.join(md)
