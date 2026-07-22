"""
PDF export service — generates polished intelligence report PDFs using ReportLab.

Produces a multi-section PDF with:
  - Cover page with entity name, report ID, generated date
  - KPI summary page
  - All report sections with claims
  - Data sources appendix

Enhanced reports additionally include:
  - Investment thesis badge (Buy/Hold/Sell)
  - SWOT 2x2 grid visualization
  - Risk heatmap (5x5 severity/likelihood)
  - Financial metrics table
  - Financial health grade badge
"""
import io
import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

try:
    from reportlab.lib             import colors
    from reportlab.lib.enums       import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib.pagesizes   import A4, letter
    from reportlab.lib.styles      import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units       import mm, cm
    from reportlab.platypus        import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, PageBreak, KeepTogether,
    )
    from reportlab.lib.colors      import HexColor
    REPORTLAB_OK = True
except ImportError:
    REPORTLAB_OK = False
    logger.warning("reportlab not installed — PDF export unavailable")

# Chart utilities for enhanced reports
try:
    from app.utils.chart_utils import (
        create_recommendation_badge,
        create_swot_grid,
        create_risk_heatmap,
        create_risk_score_badge,
        create_grade_badge,
        create_financial_metrics_table,
        create_priority_risks_table,
    )
    CHARTS_OK = True
except ImportError:
    CHARTS_OK = False
    logger.warning("chart_utils not available — enhanced visualizations disabled")

# ── Color palette (dark-intelligence theme adapted for print) ─────────────────
C_BG        = HexColor('#0f172a') if REPORTLAB_OK else None
C_ACCENT    = HexColor('#818cf8') if REPORTLAB_OK else None
C_TEXT      = HexColor('#e2e8f0') if REPORTLAB_OK else None
C_MUTED     = HexColor('#64748b') if REPORTLAB_OK else None
C_GREEN     = HexColor('#4ade80') if REPORTLAB_OK else None
C_RED       = HexColor('#f87171') if REPORTLAB_OK else None
C_AMBER     = HexColor('#fbbf24') if REPORTLAB_OK else None
C_BORDER    = HexColor('#1e293b') if REPORTLAB_OK else None
C_WHITE     = colors.white        if REPORTLAB_OK else None
C_BLACK     = colors.black        if REPORTLAB_OK else None

PAGE_WIDTH, PAGE_HEIGHT = letter


def _styles():
    base = getSampleStyleSheet()

    heading1 = ParagraphStyle(
        'IntelH1',
        parent=base['Heading1'],
        fontSize=22,
        textColor=C_WHITE,
        spaceAfter=6,
        fontName='Helvetica-Bold',
        leading=28,
    )
    heading2 = ParagraphStyle(
        'IntelH2',
        parent=base['Heading2'],
        fontSize=14,
        textColor=C_ACCENT,
        spaceAfter=4,
        spaceBefore=10,
        fontName='Helvetica-Bold',
        leading=18,
    )
    body = ParagraphStyle(
        'IntelBody',
        parent=base['Normal'],
        fontSize=9,
        textColor=C_TEXT,
        leading=13,
        spaceAfter=3,
        fontName='Helvetica',
    )
    claim = ParagraphStyle(
        'IntelClaim',
        parent=body,
        leftIndent=10,
        bulletIndent=0,
        spaceBefore=1,
        spaceAfter=2,
        fontSize=8.5,
    )
    small = ParagraphStyle(
        'IntelSmall',
        parent=body,
        fontSize=7.5,
        textColor=C_MUTED,
    )
    cover_title = ParagraphStyle(
        'CoverTitle',
        parent=heading1,
        fontSize=28,
        leading=34,
        alignment=TA_CENTER,
    )
    cover_sub = ParagraphStyle(
        'CoverSub',
        parent=body,
        fontSize=12,
        textColor=C_MUTED,
        alignment=TA_CENTER,
    )
    kpi_val = ParagraphStyle(
        'KpiVal',
        parent=heading2,
        fontSize=18,
        alignment=TA_CENTER,
        spaceAfter=0,
        spaceBefore=0,
    )
    kpi_label = ParagraphStyle(
        'KpiLabel',
        parent=small,
        alignment=TA_CENTER,
        spaceAfter=0,
        fontSize=7,
    )

    return {
        'h1': heading1, 'h2': heading2, 'body': body,
        'claim': claim, 'small': small,
        'cover_title': cover_title, 'cover_sub': cover_sub,
        'kpi_val': kpi_val, 'kpi_label': kpi_label,
    }


def _header_footer(canvas, doc, entity_name: str, report_id):
    canvas.saveState()
    canvas.setFillColor(C_ACCENT)
    canvas.setFont('Helvetica-Bold', 7)
    canvas.drawString(22, PAGE_HEIGHT - 14, f'ENTERPRISE INTELLIGENCE PLATFORM   ·   CONFIDENTIAL')
    canvas.drawRightString(PAGE_WIDTH - 22, PAGE_HEIGHT - 14,
                           f'Report #{report_id}  ·  {entity_name.upper()}')
    canvas.setFillColor(C_MUTED)
    canvas.setFont('Helvetica', 7)
    canvas.drawString(22, 12, f'Generated {datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}')
    canvas.drawRightString(PAGE_WIDTH - 22, 12, f'Page {doc.page}')
    canvas.setStrokeColor(C_BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(22, 18, PAGE_WIDTH - 22, 18)
    canvas.restoreState()


def _confidence_color(text: str):
    if '[DOCUMENTED]' in text:   return C_GREEN
    if '[REPORTED]' in text:     return C_AMBER
    if '[ANALYTICAL]' in text:   return C_ACCENT
    return C_TEXT


def generate_report_pdf(report: Dict[str, Any]) -> bytes:
    """
    Generate a PDF for an intelligence report dict and return raw bytes.
    """
    if not REPORTLAB_OK:
        raise RuntimeError("reportlab is not installed. Run: pip install reportlab")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=22*mm, rightMargin=22*mm,
        topMargin=20*mm,  bottomMargin=18*mm,
        title=f"Intelligence Report — {report.get('entity_name','Unknown')}",
        author="Enterprise Intelligence Platform",
    )

    entity_name = report.get('entity_name') or report.get('title') or 'Unknown Entity'
    report_id   = report.get('report_id', '')
    gen_at      = report.get('generated_at') or datetime.utcnow().isoformat()
    summary     = report.get('summary') or {}
    sections    = report.get('sections') or []

    S = _styles()
    story = []

    # ── Cover page ────────────────────────────────────────────────────────────
    story.append(Spacer(1, 40*mm))
    story.append(Paragraph('INTELLIGENCE REPORT', S['cover_sub']))
    story.append(Spacer(1, 6*mm))
    story.append(Paragraph(entity_name, S['cover_title']))
    story.append(Spacer(1, 8*mm))
    if report.get('ticker'):
        story.append(Paragraph(f'Ticker: {report["ticker"]}', S['cover_sub']))
    story.append(Paragraph(f'Report ID: {report_id}', S['cover_sub']))
    story.append(Paragraph(
        f'Generated: {gen_at[:19].replace("T"," ")} UTC',
        S['cover_sub']
    ))
    story.append(Spacer(1, 10*mm))
    story.append(HRFlowable(width='100%', thickness=1, color=C_ACCENT))
    story.append(Spacer(1, 6*mm))

    # Data source badges
    ds = report.get('data_sources') or {}
    badges = []
    for src in ['SEC', 'FEC', 'FARA', 'LDA', 'USASpending', 'OFAC', 'CourtListener']:
        badges.append(src)
    if ds.get('apify_linkedin'): badges.append('LinkedIn')
    if ds.get('apify_pitchbook'): badges.append('PitchBook')
    if ds.get('apify_news', 0) > 0: badges.append('Google News')
    story.append(Paragraph('Data sources: ' + ' · '.join(badges), S['cover_sub']))
    story.append(PageBreak())

    # ── KPI Summary page ──────────────────────────────────────────────────────
    story.append(Paragraph('Key Performance Indicators', S['h1']))
    story.append(Spacer(1, 4*mm))

    kpi_items = [
        ('Contracts Obligated', f"${summary.get('total_obligated_usd',0)/1e6:.1f}M"),
        ('Lobbying Spend',      f"${summary.get('kpi_lobbying_spend',0)/1e3:.0f}K"),
        ('Court Risk',          summary.get('kpi_court_risk','LOW')),
        ('Sanctions',           summary.get('kpi_sanctions_risk','CLEAR')),
        ('Data Confidence',     f"{summary.get('kpi_data_confidence',0)}%"),
        ('Sources Active',      f"{summary.get('kpi_sources_active',0)}/8"),
    ]

    kpi_data = [
        [Paragraph(val, S['kpi_val']) for _, val in kpi_items],
        [Paragraph(lbl, S['kpi_label']) for lbl, _ in kpi_items],
    ]
    kpi_table = Table(kpi_data, colWidths=[doc.width / len(kpi_items)] * len(kpi_items))
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND',   (0,0), (-1,-1), C_BORDER),
        ('GRID',         (0,0), (-1,-1), 0.5, C_BG),
        ('ROUNDEDCORNERS', [4]),
        ('TOPPADDING',   (0,0), (-1,-1), 8),
        ('BOTTOMPADDING',(0,0), (-1,-1), 8),
        ('ALIGN',        (0,0), (-1,-1), 'CENTER'),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 6*mm))

    # Summary stats table
    stats = [
        ['SEC Filings',       str(summary.get('sec_filings',0))],
        ['FEC Committees',    str(summary.get('fec_committees',0))],
        ['FARA Registrations',str(summary.get('fara_registrations',0))],
        ['Lobbying Filings',  str(summary.get('lobbying_filings',0))],
        ['Court Cases',       str(summary.get('court_cases',0))],
        ['Relationships',     str(summary.get('relationships_written',0))],
        ['News Articles',     str(summary.get('news_articles',0))],
    ]
    stats_table = Table(
        [[Paragraph(k, S['small']), Paragraph(v, S['body'])] for k, v in stats],
        colWidths=[80*mm, doc.width - 80*mm],
    )
    stats_table.setStyle(TableStyle([
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [C_BG, C_BORDER]),
        ('TOPPADDING',    (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING',   (0,0), (-1,-1), 6),
    ]))
    story.append(stats_table)
    story.append(PageBreak())

    # ── Report sections ───────────────────────────────────────────────────────
    story.append(Paragraph('Intelligence Report', S['h1']))
    story.append(Spacer(1, 3*mm))

    for sec in sections:
        name   = sec.get('name') or sec.get('title') or 'Section'
        claims = sec.get('claims') or []

        sec_els = []
        sec_els.append(Spacer(1, 2*mm))
        sec_els.append(HRFlowable(width='100%', thickness=0.5, color=C_BORDER))
        sec_els.append(Paragraph(name, S['h2']))

        if not claims:
            sec_els.append(Paragraph('No data found for this section.', S['small']))
        else:
            for claim in claims:
                raw = claim.get('text') or str(claim) or ''
                # Strip confidence tag for display
                display = raw.replace('[DOCUMENTED]', '').replace('[REPORTED]', '').replace('[ANALYTICAL]', '').strip()
                if not display:
                    continue
                conf  = claim.get('confidence', '')
                src   = claim.get('source', '')
                color = _confidence_color(raw)

                text_para = Paragraph(display[:600], S['claim'])
                if src or conf:
                    src_para = Paragraph(
                        f'<font color="#{"%02x%02x%02x" % (int(C_MUTED.red*255), int(C_MUTED.green*255), int(C_MUTED.blue*255))}">'
                        f'{conf}{"  ·  " if conf and src else ""}{src}</font>',
                        S['small']
                    )
                    sec_els.append(text_para)
                    sec_els.append(src_para)
                else:
                    sec_els.append(text_para)
                sec_els.append(Spacer(1, 1*mm))

        story.append(KeepTogether(sec_els[:5]))
        for el in sec_els[5:]:
            story.append(el)

    # ── Footer page ───────────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Spacer(1, 40*mm))
    story.append(Paragraph('ENTERPRISE INTELLIGENCE PLATFORM', S['cover_sub']))
    story.append(Paragraph('This document is CONFIDENTIAL.', S['cover_sub']))
    story.append(Paragraph(
        'Generated by automated connectors: SEC EDGAR, FEC, FARA, USASpending, LDA, '
        'OFAC/OpenSanctions, CourtListener, Wikipedia, Apify LinkedIn, Apify PitchBook, '
        'Google News, Apollo.io, OpenCorporates, GLEIF.',
        S['small']
    ))

    doc.build(
        story,
        onFirstPage  = lambda c, d: _header_footer(c, d, entity_name, report_id),
        onLaterPages = lambda c, d: _header_footer(c, d, entity_name, report_id),
    )
    return buf.getvalue()


def _get_section_text(sections: List[Dict], section_name: str) -> str:
    """Extract narrative text from a named section."""
    for sec in sections:
        if sec.get('name') == section_name:
            claims = sec.get('claims', [])
            if claims and len(claims) > 0:
                return claims[0].get('text', '')
    return ''


def _clean_markdown(text: str) -> str:
    """Convert markdown to clean text for PDF, preserving key formatting."""
    if not text:
        return ''
    # Remove markdown headers but keep the text
    import re
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # Remove bold/italic markers
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    # Remove markdown links but keep text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    return text.strip()


def generate_enhanced_report_pdf(report: Dict[str, Any]) -> bytes:
    """
    Generate a professional PDF for an enhanced intelligence report.

    This includes all standard report sections plus:
    - Investment thesis with Buy/Hold/Sell badge
    - SWOT 2x2 grid visualization
    - Risk heatmap (5x5 severity/likelihood matrix)
    - Financial metrics table
    - Financial health grade badge
    - Full narrative content for each section
    """
    if not REPORTLAB_OK:
        raise RuntimeError("reportlab is not installed. Run: pip install reportlab")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=18*mm, rightMargin=18*mm,
        topMargin=18*mm, bottomMargin=16*mm,
        title=f"Enhanced Intelligence Report — {report.get('entity_name', 'Unknown')}",
        author="Enterprise Intelligence Platform",
    )

    entity_name = report.get('entity_name') or report.get('title') or 'Unknown Entity'
    report_id = report.get('report_id', '')
    gen_at = report.get('generated_at') or datetime.utcnow().isoformat()
    ticker = report.get('ticker')
    summary = report.get('summary') or {}
    sections = report.get('sections') or []

    # Enhanced data
    investment_thesis = report.get('investment_thesis')
    swot_analysis = report.get('swot_analysis')
    risk_matrix = report.get('risk_matrix')
    financial_health = report.get('financial_health')
    financial_data = report.get('financial_data', {})

    S = _styles()
    story = []

    # ── Cover page with Executive Summary ─────────────────────────────────────
    story.append(Spacer(1, 20*mm))
    story.append(Paragraph('ENHANCED INTELLIGENCE REPORT', S['cover_sub']))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph(entity_name, S['cover_title']))
    story.append(Spacer(1, 4*mm))

    if ticker:
        story.append(Paragraph(f'Ticker: {ticker}', S['cover_sub']))
    story.append(Paragraph(f'Report ID: {report_id}', S['cover_sub']))
    story.append(Paragraph(
        f'Generated: {gen_at[:19].replace("T", " ")} UTC',
        S['cover_sub']
    ))
    story.append(Spacer(1, 6*mm))

    # Investment recommendation badge on cover
    if investment_thesis and CHARTS_OK:
        recommendation = investment_thesis.get('recommendation', 'NOT_RATED')
        conviction = investment_thesis.get('conviction', 'MEDIUM')
        if recommendation and recommendation != 'NOT_RATED':
            badge = create_recommendation_badge(recommendation, conviction, width=150, height=60)
            badge_table = Table([[badge]], colWidths=[doc.width])
            badge_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ]))
            story.append(badge_table)
            story.append(Spacer(1, 4*mm))

    story.append(HRFlowable(width='100%', thickness=1, color=C_ACCENT))
    story.append(Spacer(1, 4*mm))

    # Executive Dashboard on cover
    story.append(Paragraph('Executive Dashboard', S['h2']))
    story.append(Spacer(1, 2*mm))

    # Create metrics table
    cover_metrics = [
        ['Recommendation', investment_thesis.get('recommendation', 'N/A') if investment_thesis else 'N/A'],
        ['Conviction', investment_thesis.get('conviction', 'N/A') if investment_thesis else 'N/A'],
        ['Financial Grade', financial_health.get('grade', 'N/A') if financial_health else 'N/A'],
        ['Risk Score', f"{risk_matrix.get('overall_score', 0):.1f}/100" if risk_matrix else 'N/A'],
        ['SEC Filings', str(summary.get('sec_filings', 0))],
        ['Gov Contracts', f"${summary.get('total_obligated_usd', 0)/1e6:.2f}M"],
        ['Lobbying Filings', str(summary.get('lobbying_filings', 0))],
        ['News Articles', str(summary.get('news_articles', 0))],
    ]

    # 2 column layout for metrics
    left_metrics = cover_metrics[:4]
    right_metrics = cover_metrics[4:]

    combined_data = []
    for i in range(len(left_metrics)):
        left = left_metrics[i] if i < len(left_metrics) else ['', '']
        right = right_metrics[i] if i < len(right_metrics) else ['', '']
        combined_data.append([
            Paragraph(left[0], S['small']),
            Paragraph(str(left[1]), S['body']),
            Paragraph(right[0], S['small']),
            Paragraph(str(right[1]), S['body']),
        ])

    metrics_table = Table(combined_data, colWidths=[50*mm, 40*mm, 50*mm, 40*mm])
    metrics_table.setStyle(TableStyle([
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [C_BG, C_BORDER]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, C_BORDER),
    ]))
    story.append(metrics_table)
    story.append(Spacer(1, 4*mm))

    # Data source badges
    ds = report.get('data_sources') or {}
    badges = ['SEC', 'FEC', 'FARA', 'LDA', 'USASpending', 'OFAC', 'CourtListener']
    if ds.get('apify_linkedin'):
        badges.append('LinkedIn')
    if ds.get('apify_pitchbook'):
        badges.append('PitchBook')
    if ds.get('apify_news', 0) > 0:
        badges.append('Google News')
    if ds.get('yfinance'):
        badges.append('YFinance')
    if ds.get('valuation'):
        badges.append('DCF Valuation')
    if ds.get('technicals'):
        badges.append('Technical Analysis')
    story.append(Paragraph('Data sources: ' + ' · '.join(badges), S['small']))
    story.append(PageBreak())

    # ── Executive Summary Page ─────────────────────────────────────────────────
    story.append(Paragraph('Executive Summary', S['h1']))
    story.append(Spacer(1, 4*mm))

    # Get executive summary text from sections
    exec_summary_text = _get_section_text(sections, 'Executive Summary')
    if exec_summary_text:
        # Clean and render the text
        clean_text = _clean_markdown(exec_summary_text)
        # Split into paragraphs for better rendering
        paragraphs = clean_text.split('\n\n')
        for para in paragraphs[:15]:  # Limit to prevent overflow
            para = para.strip()
            if para and len(para) > 10:
                story.append(Paragraph(para[:800], S['body']))
                story.append(Spacer(1, 2*mm))
    else:
        story.append(Paragraph('Executive summary analysis in progress.', S['body']))

    story.append(PageBreak())

    # ── Investment Thesis Page ────────────────────────────────────────────────
    story.append(Paragraph('Investment Thesis', S['h1']))
    story.append(Spacer(1, 4*mm))

    # Investment metrics row
    if investment_thesis:
        inv_metrics = [
            ('Rating', investment_thesis.get('recommendation', 'N/A')),
            ('Conviction', investment_thesis.get('conviction', 'N/A')),
        ]
        if investment_thesis.get('fair_value'):
            inv_metrics.append(('Fair Value', f"${investment_thesis['fair_value']:.2f}"))
        if investment_thesis.get('upside_pct'):
            inv_metrics.append(('Upside', f"{investment_thesis['upside_pct']:.1f}%"))

        inv_data = [
            [Paragraph(val, S['kpi_val']) for _, val in inv_metrics],
            [Paragraph(lbl, S['kpi_label']) for lbl, _ in inv_metrics],
        ]
        inv_table = Table(inv_data, colWidths=[doc.width / len(inv_metrics)] * len(inv_metrics))
        inv_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), C_BORDER),
            ('GRID', (0, 0), (-1, -1), 0.5, C_BG),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        story.append(inv_table)
        story.append(Spacer(1, 4*mm))

    # Get investment thesis narrative
    thesis_text = _get_section_text(sections, 'Investment Thesis')
    if thesis_text:
        clean_text = _clean_markdown(thesis_text)
        paragraphs = clean_text.split('\n\n')
        for para in paragraphs[:20]:
            para = para.strip()
            if para and len(para) > 10:
                # Check if it's a subheading
                if para.upper() == para and len(para) < 50:
                    story.append(Paragraph(para, S['h2']))
                else:
                    story.append(Paragraph(para[:1000], S['body']))
                story.append(Spacer(1, 1.5*mm))

    story.append(PageBreak())

    # ── SWOT Analysis Page ────────────────────────────────────────────────────
    if swot_analysis and CHARTS_OK:
        story.append(Paragraph('SWOT Analysis', S['h1']))
        story.append(Spacer(1, 6*mm))

        strengths = [s.get('description', str(s)) if isinstance(s, dict) else str(s)
                     for s in swot_analysis.get('strengths', [])]
        weaknesses = [w.get('description', str(w)) if isinstance(w, dict) else str(w)
                      for w in swot_analysis.get('weaknesses', [])]
        opportunities = [o.get('description', str(o)) if isinstance(o, dict) else str(o)
                         for o in swot_analysis.get('opportunities', [])]
        threats = [t.get('description', str(t)) if isinstance(t, dict) else str(t)
                   for t in swot_analysis.get('threats', [])]

        swot_grid = create_swot_grid(
            strengths=strengths,
            weaknesses=weaknesses,
            opportunities=opportunities,
            threats=threats,
            styles=S,
            width=doc.width,
        )
        story.append(swot_grid)

        if swot_analysis.get('synthesis'):
            story.append(Spacer(1, 4*mm))
            story.append(Paragraph('Strategic Synthesis', S['h2']))
            story.append(Paragraph(swot_analysis['synthesis'][:1000], S['body']))

        story.append(PageBreak())

    # ── Risk Matrix Page ──────────────────────────────────────────────────────
    if risk_matrix and CHARTS_OK:
        story.append(Paragraph('Risk Assessment', S['h1']))
        story.append(Spacer(1, 6*mm))

        # Risk score badge and heatmap side by side
        risk_score = risk_matrix.get('overall_score', 50)
        score_badge = create_risk_score_badge(risk_score, width=120)

        risks = risk_matrix.get('risks', [])
        heatmap = create_risk_heatmap(risks, width=280, height=230)

        risk_row = Table([[score_badge, heatmap]], colWidths=[130, 300])
        risk_row.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ]))
        story.append(risk_row)
        story.append(Spacer(1, 6*mm))

        # Priority risks table
        top_risks = risk_matrix.get('top_priority_risks', [])
        if top_risks:
            story.append(Paragraph('Top Priority Risks', S['h2']))
            story.append(Spacer(1, 3*mm))
            priority_table = create_priority_risks_table(top_risks, S, width=doc.width)
            story.append(priority_table)

        story.append(PageBreak())

    # ── Financial Health Page ─────────────────────────────────────────────────
    if financial_health and CHARTS_OK:
        story.append(Paragraph('Financial Health Summary', S['h1']))
        story.append(Spacer(1, 4*mm))

        # Grade badge
        grade = financial_health.get('grade', 'C')
        grade_badge = create_grade_badge(grade, width=100)
        grade_table = Table([[grade_badge]], colWidths=[doc.width])
        grade_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        story.append(grade_table)
        story.append(Spacer(1, 4*mm))

        # Financial metrics
        metrics = financial_health.get('metrics', {})
        if not metrics and financial_data:
            metrics = financial_data.get('fundamentals', {})

        if metrics:
            metrics_table = create_financial_metrics_table(metrics, S, width=doc.width * 0.7)
            metrics_wrapper = Table([[metrics_table]], colWidths=[doc.width])
            metrics_wrapper.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ]))
            story.append(metrics_wrapper)
            story.append(Spacer(1, 4*mm))

        # Financial health narrative
        fh_text = _get_section_text(sections, 'Financial Health Summary')
        if fh_text:
            clean_text = _clean_markdown(fh_text)
            paragraphs = clean_text.split('\n\n')
            for para in paragraphs[:12]:
                para = para.strip()
                if para and len(para) > 10:
                    story.append(Paragraph(para[:800], S['body']))
                    story.append(Spacer(1, 1.5*mm))

        story.append(PageBreak())

    # ── Competitive Analysis Page ─────────────────────────────────────────────
    comp_text = _get_section_text(sections, 'Competitive Analysis')
    if comp_text:
        story.append(Paragraph('Competitive Analysis', S['h1']))
        story.append(Spacer(1, 4*mm))

        clean_text = _clean_markdown(comp_text)
        paragraphs = clean_text.split('\n\n')
        for para in paragraphs[:18]:
            para = para.strip()
            if para and len(para) > 10:
                # Check if it looks like a heading
                if len(para) < 60 and para.endswith(':'):
                    story.append(Paragraph(para, S['h2']))
                else:
                    story.append(Paragraph(para[:1000], S['body']))
                story.append(Spacer(1, 1.5*mm))

        story.append(PageBreak())

    # ── Standard Report Sections ──────────────────────────────────────────────
    story.append(Paragraph('Detailed Intelligence Data', S['h1']))
    story.append(Spacer(1, 3*mm))

    # Sections to skip (already rendered with full narrative)
    skip_sections = [
        'Executive Summary', 'Investment Thesis', 'SWOT Analysis',
        'Risk Matrix', 'Financial Health Summary', 'Competitive Analysis',
        'Deep Intelligence Narrative'
    ]

    for sec in sections:
        name = sec.get('name') or sec.get('title') or 'Section'
        claims = sec.get('claims') or []

        # Skip enhanced sections already rendered
        if any(x in name for x in skip_sections):
            continue

        sec_els = []
        sec_els.append(Spacer(1, 2*mm))
        sec_els.append(HRFlowable(width='100%', thickness=0.5, color=C_BORDER))
        sec_els.append(Paragraph(name, S['h2']))

        if not claims:
            sec_els.append(Paragraph('No data found for this section.', S['small']))
        else:
            for claim in claims:
                raw = claim.get('text') or str(claim) or ''
                display = raw.replace('[DOCUMENTED]', '').replace('[REPORTED]', '').replace('[ANALYTICAL]', '').strip()
                if not display:
                    continue
                conf = claim.get('confidence', '')
                src = claim.get('source', '')
                color = _confidence_color(raw)

                # Truncate long claims
                text_para = Paragraph(display[:800], S['claim'])
                if src or conf:
                    src_para = Paragraph(
                        f'<font color="#{"%02x%02x%02x" % (int(C_MUTED.red * 255), int(C_MUTED.green * 255), int(C_MUTED.blue * 255))}">'
                        f'{conf}{"  ·  " if conf and src else ""}{src}</font>',
                        S['small']
                    )
                    sec_els.append(text_para)
                    sec_els.append(src_para)
                else:
                    sec_els.append(text_para)
                sec_els.append(Spacer(1, 1*mm))

        story.append(KeepTogether(sec_els[:5]))
        for el in sec_els[5:]:
            story.append(el)

    # ── Footer page ───────────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Spacer(1, 40*mm))
    story.append(Paragraph('ENTERPRISE INTELLIGENCE PLATFORM', S['cover_sub']))
    story.append(Paragraph('ENHANCED INTELLIGENCE REPORT', S['cover_sub']))
    story.append(Paragraph('This document is CONFIDENTIAL.', S['cover_sub']))
    story.append(Spacer(1, 6*mm))
    story.append(Paragraph(
        'Generated by automated connectors: SEC EDGAR, FEC, FARA, USASpending, LDA, '
        'OFAC/OpenSanctions, CourtListener, Wikipedia, Apify LinkedIn, Apify PitchBook, '
        'Google News, Apollo.io, OpenCorporates, GLEIF, YFinance, DCF Valuation, Technical Analysis.',
        S['small']
    ))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph(
        'Enhanced analysis powered by GPT-4o-mini: Investment Thesis, SWOT Analysis, '
        'Risk Matrix, Financial Health Summary, Competitive Analysis.',
        S['small']
    ))

    doc.build(
        story,
        onFirstPage=lambda c, d: _header_footer(c, d, entity_name, report_id),
        onLaterPages=lambda c, d: _header_footer(c, d, entity_name, report_id),
    )
    return buf.getvalue()
