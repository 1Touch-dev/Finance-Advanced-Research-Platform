"""
Chart utilities for ReportLab PDF generation.

Provides chart components for enhanced intelligence reports:
- KPI gauges/meters
- SWOT 2x2 grid
- Risk heatmap (5x5 severity/likelihood)
- Financial trend charts
- Investment thesis badge
"""

import io
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    from reportlab.lib import colors
    from reportlab.lib.colors import HexColor, Color
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib.units import mm, cm, inch
    from reportlab.platypus import (
        Table, TableStyle, Paragraph, Spacer, Flowable,
        KeepTogether,
    )
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.graphics.shapes import Drawing, Rect, String, Circle, Line, Polygon
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.charts.linecharts import HorizontalLineChart
    from reportlab.graphics.charts.piecharts import Pie
    from reportlab.graphics import renderPDF
    REPORTLAB_OK = True
except ImportError:
    REPORTLAB_OK = False
    logger.warning("reportlab not installed — chart utilities unavailable")

# ── Color palette (matches pdf_service.py theme) ─────────────────────────────
C_BG = HexColor('#0f172a') if REPORTLAB_OK else None
C_ACCENT = HexColor('#818cf8') if REPORTLAB_OK else None
C_TEXT = HexColor('#e2e8f0') if REPORTLAB_OK else None
C_MUTED = HexColor('#64748b') if REPORTLAB_OK else None
C_GREEN = HexColor('#4ade80') if REPORTLAB_OK else None
C_RED = HexColor('#f87171') if REPORTLAB_OK else None
C_AMBER = HexColor('#fbbf24') if REPORTLAB_OK else None
C_BORDER = HexColor('#1e293b') if REPORTLAB_OK else None
C_WHITE = colors.white if REPORTLAB_OK else None
C_BLACK = colors.black if REPORTLAB_OK else None

# SWOT colors
C_STRENGTH = HexColor('#22c55e') if REPORTLAB_OK else None  # Green
C_WEAKNESS = HexColor('#ef4444') if REPORTLAB_OK else None  # Red
C_OPPORTUNITY = HexColor('#3b82f6') if REPORTLAB_OK else None  # Blue
C_THREAT = HexColor('#f59e0b') if REPORTLAB_OK else None  # Amber

# Risk heatmap colors (low to critical)
RISK_COLORS = [
    HexColor('#22c55e'),  # Low - Green
    HexColor('#84cc16'),  # Low-Medium - Lime
    HexColor('#fbbf24'),  # Medium - Amber
    HexColor('#f97316'),  # High - Orange
    HexColor('#ef4444'),  # Critical - Red
] if REPORTLAB_OK else []


# ============================================================================
# INVESTMENT THESIS BADGE
# ============================================================================

class RecommendationBadge(Flowable):
    """
    A visual badge showing Buy/Hold/Sell recommendation.
    """

    def __init__(
        self,
        recommendation: str,
        conviction: str = "MEDIUM",
        width: float = 120,
        height: float = 50,
    ):
        Flowable.__init__(self)
        self.recommendation = recommendation.upper()
        self.conviction = conviction.upper()
        self.width = width
        self.height = height

    def draw(self):
        # Determine color based on recommendation
        if self.recommendation == "BUY":
            bg_color = C_GREEN
            text_color = C_BLACK
        elif self.recommendation == "SELL":
            bg_color = C_RED
            text_color = C_WHITE
        else:  # HOLD
            bg_color = C_AMBER
            text_color = C_BLACK

        # Draw rounded rectangle background
        self.canv.setFillColor(bg_color)
        self.canv.roundRect(0, 0, self.width, self.height, 8, fill=1, stroke=0)

        # Draw recommendation text
        self.canv.setFillColor(text_color)
        self.canv.setFont("Helvetica-Bold", 18)
        self.canv.drawCentredString(self.width / 2, self.height / 2 + 5, self.recommendation)

        # Draw conviction level
        self.canv.setFont("Helvetica", 9)
        self.canv.drawCentredString(self.width / 2, self.height / 2 - 12, f"Conviction: {self.conviction}")


def create_recommendation_badge(
    recommendation: str,
    conviction: str = "MEDIUM",
    width: float = 120,
    height: float = 50,
) -> Flowable:
    """Create a recommendation badge flowable."""
    if not REPORTLAB_OK:
        return Spacer(1, 1)
    return RecommendationBadge(recommendation, conviction, width, height)


# ============================================================================
# SWOT 2x2 GRID
# ============================================================================

def create_swot_grid(
    strengths: List[str],
    weaknesses: List[str],
    opportunities: List[str],
    threats: List[str],
    styles: Dict[str, ParagraphStyle],
    width: float = 500,
) -> Table:
    """
    Create a 2x2 SWOT analysis grid.

    Args:
        strengths: List of strength items
        weaknesses: List of weakness items
        opportunities: List of opportunity items
        threats: List of threat items
        styles: Dictionary of paragraph styles
        width: Total width of the grid

    Returns:
        ReportLab Table with SWOT grid
    """
    if not REPORTLAB_OK:
        return Table([[""]])

    cell_width = width / 2 - 10

    def format_items(items: List[str], max_items: int = 5) -> str:
        """Format list items as bullet points."""
        formatted = []
        for item in items[:max_items]:
            # Truncate long items
            if len(item) > 100:
                item = item[:97] + "..."
            formatted.append(f"• {item}")
        return "<br/>".join(formatted) if formatted else "No items identified"

    # Create header style
    header_style = ParagraphStyle(
        'SwotHeader',
        fontSize=11,
        textColor=C_WHITE,
        fontName='Helvetica-Bold',
        alignment=TA_CENTER,
        spaceAfter=4,
    )

    # Create content style
    content_style = ParagraphStyle(
        'SwotContent',
        fontSize=8,
        textColor=C_TEXT,
        fontName='Helvetica',
        leading=11,
        leftIndent=4,
    )

    # Build grid data
    data = [
        # Headers row
        [
            Paragraph("<b>STRENGTHS</b>", header_style),
            Paragraph("<b>WEAKNESSES</b>", header_style),
        ],
        # Content row 1
        [
            Paragraph(format_items(strengths), content_style),
            Paragraph(format_items(weaknesses), content_style),
        ],
        # Headers row 2
        [
            Paragraph("<b>OPPORTUNITIES</b>", header_style),
            Paragraph("<b>THREATS</b>", header_style),
        ],
        # Content row 2
        [
            Paragraph(format_items(opportunities), content_style),
            Paragraph(format_items(threats), content_style),
        ],
    ]

    table = Table(data, colWidths=[cell_width, cell_width])

    # Apply styling
    table.setStyle(TableStyle([
        # Strengths header (green)
        ('BACKGROUND', (0, 0), (0, 0), C_STRENGTH),
        ('BACKGROUND', (0, 1), (0, 1), HexColor('#14532d')),  # Dark green

        # Weaknesses header (red)
        ('BACKGROUND', (1, 0), (1, 0), C_WEAKNESS),
        ('BACKGROUND', (1, 1), (1, 1), HexColor('#7f1d1d')),  # Dark red

        # Opportunities header (blue)
        ('BACKGROUND', (0, 2), (0, 2), C_OPPORTUNITY),
        ('BACKGROUND', (0, 3), (0, 3), HexColor('#1e3a5f')),  # Dark blue

        # Threats header (amber)
        ('BACKGROUND', (1, 2), (1, 2), C_THREAT),
        ('BACKGROUND', (1, 3), (1, 3), HexColor('#78350f')),  # Dark amber

        # Borders
        ('GRID', (0, 0), (-1, -1), 1, C_BORDER),
        ('BOX', (0, 0), (-1, -1), 2, C_ACCENT),

        # Padding
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),

        # Alignment
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    return table


# ============================================================================
# RISK HEATMAP (5x5 Matrix)
# ============================================================================

class RiskHeatmap(Flowable):
    """
    A 5x5 risk heatmap showing severity vs likelihood.
    """

    def __init__(
        self,
        risks: List[Dict[str, Any]],
        width: float = 300,
        height: float = 250,
    ):
        Flowable.__init__(self)
        self.risks = risks
        self.width = width
        self.height = height
        self.cell_size = min(width, height - 50) / 5  # Reserve space for labels

    def draw(self):
        # Grid starting position
        grid_x = 40  # Space for Y-axis labels
        grid_y = 30  # Space for X-axis labels
        grid_size = self.cell_size * 5

        # Draw grid cells with color gradient
        for row in range(5):
            for col in range(5):
                # Calculate risk score for this cell (severity * likelihood)
                severity = row + 1  # 1-5 from bottom
                likelihood = col + 1  # 1-5 from left
                score = severity * likelihood

                # Determine color based on score
                if score <= 4:
                    color = RISK_COLORS[0]  # Green
                elif score <= 8:
                    color = RISK_COLORS[1]  # Lime
                elif score <= 12:
                    color = RISK_COLORS[2]  # Amber
                elif score <= 16:
                    color = RISK_COLORS[3]  # Orange
                else:
                    color = RISK_COLORS[4]  # Red

                x = grid_x + col * self.cell_size
                y = grid_y + row * self.cell_size

                self.canv.setFillColor(color)
                self.canv.setStrokeColor(C_BORDER)
                self.canv.rect(x, y, self.cell_size, self.cell_size, fill=1, stroke=1)

        # Plot risk points
        for risk in self.risks:
            severity = risk.get('severity', 3)
            likelihood = risk.get('likelihood', 3)
            risk_id = risk.get('id', 'R')

            # Calculate position (center of cell)
            x = grid_x + (likelihood - 0.5) * self.cell_size
            y = grid_y + (severity - 0.5) * self.cell_size

            # Draw risk marker
            self.canv.setFillColor(C_WHITE)
            self.canv.setStrokeColor(C_BLACK)
            self.canv.circle(x, y, 10, fill=1, stroke=1)

            # Draw risk ID
            self.canv.setFillColor(C_BLACK)
            self.canv.setFont("Helvetica-Bold", 7)
            self.canv.drawCentredString(x, y - 3, str(risk_id)[:3])

        # Draw axis labels
        self.canv.setFillColor(C_TEXT)
        self.canv.setFont("Helvetica", 8)

        # Y-axis (Severity)
        self.canv.saveState()
        self.canv.translate(15, grid_y + grid_size / 2)
        self.canv.rotate(90)
        self.canv.drawCentredString(0, 0, "SEVERITY")
        self.canv.restoreState()

        # Y-axis numbers
        for i in range(5):
            y = grid_y + (i + 0.5) * self.cell_size
            self.canv.drawCentredString(grid_x - 10, y - 3, str(i + 1))

        # X-axis (Likelihood)
        self.canv.drawCentredString(grid_x + grid_size / 2, 10, "LIKELIHOOD")

        # X-axis numbers
        for i in range(5):
            x = grid_x + (i + 0.5) * self.cell_size
            self.canv.drawCentredString(x, grid_y - 10, str(i + 1))

        # Title
        self.canv.setFont("Helvetica-Bold", 10)
        self.canv.drawCentredString(self.width / 2, self.height - 10, "Risk Assessment Matrix")


def create_risk_heatmap(
    risks: List[Dict[str, Any]],
    width: float = 300,
    height: float = 250,
) -> Flowable:
    """Create a risk heatmap flowable."""
    if not REPORTLAB_OK:
        return Spacer(1, 1)
    return RiskHeatmap(risks, width, height)


# ============================================================================
# KPI GAUGE / METER
# ============================================================================

class KPIGauge(Flowable):
    """
    A semi-circular gauge showing a KPI value.
    """

    def __init__(
        self,
        value: float,
        max_value: float = 100,
        label: str = "",
        width: float = 80,
        height: float = 60,
    ):
        Flowable.__init__(self)
        self.value = min(max(value, 0), max_value)
        self.max_value = max_value
        self.label = label
        self.width = width
        self.height = height

    def draw(self):
        import math

        center_x = self.width / 2
        center_y = 20
        radius = min(self.width / 2 - 5, self.height - 25)

        # Draw background arc
        self.canv.setStrokeColor(C_BORDER)
        self.canv.setLineWidth(8)

        # Draw arc segments
        segments = 20
        for i in range(segments):
            start_angle = 180 - (i * 180 / segments)
            end_angle = 180 - ((i + 1) * 180 / segments)

            # Determine color based on segment position
            segment_value = (i / segments) * 100
            if segment_value < 30:
                color = C_GREEN
            elif segment_value < 70:
                color = C_AMBER
            else:
                color = C_RED

            # Only draw filled segments up to current value
            if (i / segments) * self.max_value <= self.value:
                self.canv.setStrokeColor(color)
            else:
                self.canv.setStrokeColor(C_BORDER)

            # Draw arc segment
            self.canv.arc(
                center_x - radius, center_y - radius,
                center_x + radius, center_y + radius,
                start_angle, (end_angle - start_angle)
            )

        # Draw value text
        self.canv.setFillColor(C_TEXT)
        self.canv.setFont("Helvetica-Bold", 14)
        value_text = f"{self.value:.0f}" if self.value == int(self.value) else f"{self.value:.1f}"
        self.canv.drawCentredString(center_x, center_y - 5, value_text)

        # Draw label
        self.canv.setFont("Helvetica", 7)
        self.canv.setFillColor(C_MUTED)
        self.canv.drawCentredString(center_x, self.height - 5, self.label[:15])


def create_kpi_gauge(
    value: float,
    max_value: float = 100,
    label: str = "",
    width: float = 80,
    height: float = 60,
) -> Flowable:
    """Create a KPI gauge flowable."""
    if not REPORTLAB_OK:
        return Spacer(1, 1)
    return KPIGauge(value, max_value, label, width, height)


# ============================================================================
# FINANCIAL METRICS TABLE
# ============================================================================

def create_financial_metrics_table(
    metrics: Dict[str, Any],
    styles: Dict[str, ParagraphStyle],
    width: float = 500,
) -> Table:
    """
    Create a styled financial metrics table.

    Args:
        metrics: Dictionary of metric name -> value
        styles: Dictionary of paragraph styles
        width: Table width

    Returns:
        ReportLab Table with financial metrics
    """
    if not REPORTLAB_OK:
        return Table([[""]])

    # Define metric display names and formatting
    metric_config = {
        'pe_ratio': ('P/E Ratio', lambda x: f"{x:.2f}" if x else "N/A"),
        'pb_ratio': ('P/B Ratio', lambda x: f"{x:.2f}" if x else "N/A"),
        'ev_ebitda': ('EV/EBITDA', lambda x: f"{x:.2f}" if x else "N/A"),
        'gross_margin': ('Gross Margin', lambda x: f"{x*100:.1f}%" if x else "N/A"),
        'operating_margin': ('Operating Margin', lambda x: f"{x*100:.1f}%" if x else "N/A"),
        'net_margin': ('Net Margin', lambda x: f"{x*100:.1f}%" if x else "N/A"),
        'roe': ('ROE', lambda x: f"{x*100:.1f}%" if x else "N/A"),
        'roa': ('ROA', lambda x: f"{x*100:.1f}%" if x else "N/A"),
        'current_ratio': ('Current Ratio', lambda x: f"{x:.2f}" if x else "N/A"),
        'debt_equity': ('Debt/Equity', lambda x: f"{x:.2f}" if x else "N/A"),
        'revenue': ('Revenue', lambda x: f"${x/1e9:.2f}B" if x and x >= 1e9 else f"${x/1e6:.1f}M" if x else "N/A"),
        'market_cap': ('Market Cap', lambda x: f"${x/1e9:.2f}B" if x and x >= 1e9 else f"${x/1e6:.1f}M" if x else "N/A"),
    }

    header_style = ParagraphStyle(
        'MetricHeader',
        fontSize=9,
        textColor=C_ACCENT,
        fontName='Helvetica-Bold',
    )

    value_style = ParagraphStyle(
        'MetricValue',
        fontSize=9,
        textColor=C_TEXT,
        fontName='Helvetica',
    )

    # Build table data
    data = [[Paragraph("Metric", header_style), Paragraph("Value", header_style)]]

    for key, (display_name, formatter) in metric_config.items():
        value = metrics.get(key)
        if value is not None:
            formatted_value = formatter(value)
            data.append([
                Paragraph(display_name, value_style),
                Paragraph(formatted_value, value_style),
            ])

    if len(data) == 1:
        data.append([Paragraph("No financial data available", value_style), Paragraph("", value_style)])

    table = Table(data, colWidths=[width * 0.5, width * 0.5])

    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), C_BORDER),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [C_BG, HexColor('#1a1f2e')]),
        ('GRID', (0, 0), (-1, -1), 0.5, C_BORDER),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))

    return table


# ============================================================================
# RISK SCORE BADGE
# ============================================================================

def create_risk_score_badge(
    score: float,
    label: str = "Overall Risk Score",
    width: float = 150,
) -> Table:
    """
    Create a risk score badge with color-coded background.

    Args:
        score: Risk score (0-100)
        label: Label text
        width: Badge width

    Returns:
        ReportLab Table styled as a badge
    """
    if not REPORTLAB_OK:
        return Table([[""]])

    # Determine color based on score
    if score < 30:
        bg_color = C_GREEN
        text_color = C_BLACK
        risk_level = "LOW RISK"
    elif score < 50:
        bg_color = C_AMBER
        text_color = C_BLACK
        risk_level = "MODERATE RISK"
    elif score < 70:
        bg_color = HexColor('#f97316')  # Orange
        text_color = C_WHITE
        risk_level = "HIGH RISK"
    else:
        bg_color = C_RED
        text_color = C_WHITE
        risk_level = "CRITICAL RISK"

    score_style = ParagraphStyle(
        'RiskScore',
        fontSize=24,
        textColor=text_color,
        fontName='Helvetica-Bold',
        alignment=TA_CENTER,
    )

    label_style = ParagraphStyle(
        'RiskLabel',
        fontSize=8,
        textColor=text_color,
        fontName='Helvetica',
        alignment=TA_CENTER,
    )

    data = [
        [Paragraph(f"{score:.0f}", score_style)],
        [Paragraph(risk_level, label_style)],
    ]

    table = Table(data, colWidths=[width])

    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg_color),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROUNDEDCORNERS', [8]),
    ]))

    return table


# ============================================================================
# FINANCIAL HEALTH GRADE BADGE
# ============================================================================

def create_grade_badge(
    grade: str,
    width: float = 80,
) -> Table:
    """
    Create a financial health grade badge (A+ to F).

    Args:
        grade: Letter grade (A+, A, A-, B+, B, B-, C+, C, C-, D+, D, D-, F)
        width: Badge width

    Returns:
        ReportLab Table styled as a grade badge
    """
    if not REPORTLAB_OK:
        return Table([[""]])

    grade = grade.upper().strip()

    # Determine color based on grade
    if grade.startswith('A'):
        bg_color = C_GREEN
        text_color = C_BLACK
    elif grade.startswith('B'):
        bg_color = HexColor('#84cc16')  # Lime
        text_color = C_BLACK
    elif grade.startswith('C'):
        bg_color = C_AMBER
        text_color = C_BLACK
    elif grade.startswith('D'):
        bg_color = HexColor('#f97316')  # Orange
        text_color = C_WHITE
    else:  # F
        bg_color = C_RED
        text_color = C_WHITE

    grade_style = ParagraphStyle(
        'GradeLetter',
        fontSize=28,
        textColor=text_color,
        fontName='Helvetica-Bold',
        alignment=TA_CENTER,
    )

    label_style = ParagraphStyle(
        'GradeLabel',
        fontSize=7,
        textColor=text_color,
        fontName='Helvetica',
        alignment=TA_CENTER,
    )

    data = [
        [Paragraph(grade, grade_style)],
        [Paragraph("Financial Health", label_style)],
    ]

    table = Table(data, colWidths=[width])

    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg_color),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROUNDEDCORNERS', [8]),
    ]))

    return table


# ============================================================================
# PRIORITY RISKS TABLE
# ============================================================================

def create_priority_risks_table(
    risks: List[Dict[str, Any]],
    styles: Dict[str, ParagraphStyle],
    width: float = 500,
) -> Table:
    """
    Create a table of top priority risks.

    Args:
        risks: List of risk dicts with id, description, score, category
        styles: Dictionary of paragraph styles
        width: Table width

    Returns:
        ReportLab Table with priority risks
    """
    if not REPORTLAB_OK:
        return Table([[""]])

    header_style = ParagraphStyle(
        'RiskHeader',
        fontSize=9,
        textColor=C_ACCENT,
        fontName='Helvetica-Bold',
    )

    cell_style = ParagraphStyle(
        'RiskCell',
        fontSize=8,
        textColor=C_TEXT,
        fontName='Helvetica',
        leading=11,
    )

    # Header row
    data = [[
        Paragraph("ID", header_style),
        Paragraph("Risk Description", header_style),
        Paragraph("Category", header_style),
        Paragraph("Score", header_style),
    ]]

    # Risk rows
    for risk in risks[:5]:  # Top 5 risks
        score = risk.get('score', 0)

        # Color-code score
        if score >= 20:
            score_color = C_RED
        elif score >= 15:
            score_color = HexColor('#f97316')
        elif score >= 8:
            score_color = C_AMBER
        else:
            score_color = C_GREEN

        score_style = ParagraphStyle(
            'ScoreStyle',
            fontSize=9,
            textColor=score_color,
            fontName='Helvetica-Bold',
        )

        data.append([
            Paragraph(str(risk.get('id', 'R?')), cell_style),
            Paragraph(str(risk.get('description', ''))[:100], cell_style),
            Paragraph(str(risk.get('category', 'Other')), cell_style),
            Paragraph(str(score), score_style),
        ])

    if len(data) == 1:
        data.append([
            Paragraph("-", cell_style),
            Paragraph("No risks identified", cell_style),
            Paragraph("-", cell_style),
            Paragraph("-", cell_style),
        ])

    col_widths = [width * 0.08, width * 0.55, width * 0.22, width * 0.15]
    table = Table(data, colWidths=col_widths)

    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), C_BORDER),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [C_BG, HexColor('#1a1f2e')]),
        ('GRID', (0, 0), (-1, -1), 0.5, C_BORDER),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    return table
