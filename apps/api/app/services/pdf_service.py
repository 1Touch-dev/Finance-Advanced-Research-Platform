"""
PDF export service — generates a polished intelligence report PDF using ReportLab.

Produces a multi-section PDF with:
  - Cover page with entity name, report ID, generated date
  - KPI summary page
  - All report sections with claims
  - Data sources appendix
"""
import io
import os
import logging
from datetime import datetime
from typing import Dict, Any, List

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
