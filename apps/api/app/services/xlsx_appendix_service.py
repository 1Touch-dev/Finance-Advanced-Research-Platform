"""
XLSX Appendix Workbook Generator
────────────────────────────────────────────────────────────────────────────────
Generates a 13-sheet Excel workbook from the deep research data model, providing
raw data export for the intelligence report.

Sheets:
  A1. Annual Financials       - 5-year income statement and key metrics
  A2. Quarterly Financials    - Last 8 quarters with TTM
  A3. Valuation Model         - DCF assumptions and calculation
  A4. Sensitivity Grid        - WACC × terminal growth matrix
  A5. Peer Comparables        - Valuation multiples vs competitors
  B1. Federal Contracts       - Prime awards detail
  B2. Contract Subawards      - Subcontracting breakdown
  C.  Lobbying Activity       - LDA filings and registrant breakdown
  D1. Insider Transactions    - Form 4 transactions
  D2. Insider Summary         - Net insider position by person
  H1. Litigation Matters      - Active and resolved cases
  H2. Export Controls         - Entity List, OFAC, BIS status

Usage:
    from app.services.xlsx_appendix_service import generate_xlsx_appendix
    path = generate_xlsx_appendix(deep_research_data, output_dir="/path/to/output")
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from io import BytesIO

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
    from openpyxl.utils import get_column_letter
    OPENPYXL_AVAILABLE = True
except ImportError:
    Workbook = Any  # type: ignore[assignment]
    OPENPYXL_AVAILABLE = False

logger = logging.getLogger(__name__)

# ── Styling Constants ─────────────────────────────────────────────────────────

if OPENPYXL_AVAILABLE:
    HEADER_FONT = Font(bold=True, color="FFFFFF")
    HEADER_FILL = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    HEADER_ALIGN = Alignment(horizontal="center", vertical="center", wrap_text=True)

    NUMBER_FONT = Font(name="Calibri", size=10)
    NUMBER_ALIGN = Alignment(horizontal="right")

    THIN_BORDER = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )
else:
    HEADER_FONT = None
    HEADER_FILL = None
    HEADER_ALIGN = None
    NUMBER_FONT = None
    NUMBER_ALIGN = None
    THIN_BORDER = None

CURRENCY_FORMAT = '#,##0.00'
PERCENT_FORMAT = '0.00%'
INTEGER_FORMAT = '#,##0'
DATE_FORMAT = 'YYYY-MM-DD'


def _apply_header_style(ws, row: int, cols: int):
    """Apply header styling to a row."""
    for col in range(1, cols + 1):
        cell = ws.cell(row=row, column=col)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = HEADER_ALIGN
        cell.border = THIN_BORDER


def _auto_column_width(ws, min_width: int = 10, max_width: int = 50):
    """Auto-fit column widths based on content."""
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            except:
                pass
        adjusted_width = min(max(max_length + 2, min_width), max_width)
        ws.column_dimensions[column].width = adjusted_width


def _write_table(ws, headers: List[str], data: List[List], start_row: int = 1):
    """Write a table with headers and data."""
    # Write headers
    for col, header in enumerate(headers, 1):
        ws.cell(row=start_row, column=col, value=header)
    _apply_header_style(ws, start_row, len(headers))

    # Write data
    for row_idx, row_data in enumerate(data, start_row + 1):
        for col_idx, value in enumerate(row_data, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.border = THIN_BORDER
            if isinstance(value, (int, float)):
                cell.alignment = NUMBER_ALIGN


# ── Sheet Generators ──────────────────────────────────────────────────────────

def _sheet_a1_annual_financials(wb: Workbook, data: Dict[str, Any]):
    """A1: Annual financial statements (5 years)."""
    ws = wb.create_sheet("A1. Annual Financials")

    # Get financial data
    fin_data = data.get("financial_intelligence", {})
    facts = fin_data.get("facts", {})

    # Metrics to include
    metrics = [
        ("Revenue", "Revenues", CURRENCY_FORMAT),
        ("Cost of Revenue", "CostOfRevenue", CURRENCY_FORMAT),
        ("Gross Profit", "GrossProfit", CURRENCY_FORMAT),
        ("Operating Income", "OperatingIncomeLoss", CURRENCY_FORMAT),
        ("Net Income", "NetIncomeLoss", CURRENCY_FORMAT),
        ("EPS (Diluted)", "EarningsPerShareDiluted", "#0.00"),
        ("Total Assets", "Assets", CURRENCY_FORMAT),
        ("Total Liabilities", "Liabilities", CURRENCY_FORMAT),
        ("Stockholders Equity", "StockholdersEquity", CURRENCY_FORMAT),
        ("Cash & Equivalents", "CashAndCashEquivalentsAtCarryingValue", CURRENCY_FORMAT),
        ("Operating Cash Flow", "NetCashProvidedByUsedInOperatingActivities", CURRENCY_FORMAT),
        ("Capital Expenditures", "PaymentsToAcquirePropertyPlantAndEquipment", CURRENCY_FORMAT),
        ("Free Cash Flow", "FreeCashFlow", CURRENCY_FORMAT),
        ("R&D Expense", "ResearchAndDevelopmentExpense", CURRENCY_FORMAT),
    ]

    # Collect fiscal years
    fiscal_years = set()
    for metric_name, concept, _ in metrics:
        if concept in facts:
            for item in facts[concept].get("units", {}).get("USD", []):
                if item.get("form") in ("10-K", "20-F") and item.get("fy"):
                    fiscal_years.add(item["fy"])

    fiscal_years = sorted(fiscal_years, reverse=True)[:5]  # Last 5 years

    if not fiscal_years:
        ws.cell(row=1, column=1, value="No annual financial data available")
        return

    # Headers
    headers = ["Metric ($ millions)"] + [f"FY{fy}" for fy in fiscal_years]
    _write_table(ws, headers, [])

    # Data rows
    row = 2
    for metric_name, concept, fmt in metrics:
        values = [metric_name]
        concept_data = facts.get(concept, {}).get("units", {}).get("USD", [])

        for fy in fiscal_years:
            # Find annual value for this fiscal year
            fy_values = [
                item for item in concept_data
                if item.get("fy") == fy and item.get("form") in ("10-K", "20-F")
            ]
            if fy_values:
                # Take the most recent filing's value
                value = fy_values[-1].get("val", 0)
                # Convert to millions
                values.append(value / 1_000_000 if abs(value) > 1000 else value)
            else:
                values.append("")

        for col, val in enumerate(values, 1):
            cell = ws.cell(row=row, column=col, value=val)
            cell.border = THIN_BORDER
            if col > 1 and isinstance(val, (int, float)):
                cell.number_format = '#,##0.0'
        row += 1

    _auto_column_width(ws)


def _sheet_a2_quarterly_financials(wb: Workbook, data: Dict[str, Any]):
    """A2: Quarterly financial statements."""
    ws = wb.create_sheet("A2. Quarterly Financials")

    fin_data = data.get("financial_intelligence", {})
    facts = fin_data.get("facts", {})

    metrics = [
        ("Revenue", "Revenues"),
        ("Gross Profit", "GrossProfit"),
        ("Operating Income", "OperatingIncomeLoss"),
        ("Net Income", "NetIncomeLoss"),
        ("EPS (Diluted)", "EarningsPerShareDiluted"),
    ]

    # Collect quarters
    quarters = set()
    for metric_name, concept in metrics:
        if concept in facts:
            for item in facts[concept].get("units", {}).get("USD", []):
                if item.get("form") in ("10-Q",) and item.get("fy") and item.get("fp"):
                    quarters.add((item["fy"], item["fp"]))

    quarters = sorted(quarters, reverse=True)[:8]  # Last 8 quarters

    if not quarters:
        ws.cell(row=1, column=1, value="No quarterly financial data available")
        return

    headers = ["Metric ($ millions)"] + [f"{q[1]} FY{q[0]}" for q in quarters]
    _write_table(ws, headers, [])

    row = 2
    for metric_name, concept in metrics:
        values = [metric_name]
        concept_data = facts.get(concept, {}).get("units", {}).get("USD", [])

        for fy, fp in quarters:
            q_values = [
                item for item in concept_data
                if item.get("fy") == fy and item.get("fp") == fp and item.get("form") == "10-Q"
            ]
            if q_values:
                value = q_values[-1].get("val", 0)
                values.append(value / 1_000_000 if abs(value) > 1000 else value)
            else:
                values.append("")

        for col, val in enumerate(values, 1):
            cell = ws.cell(row=row, column=col, value=val)
            cell.border = THIN_BORDER
            if col > 1 and isinstance(val, (int, float)):
                cell.number_format = '#,##0.0'
        row += 1

    _auto_column_width(ws)


def _sheet_a3_valuation(wb: Workbook, data: Dict[str, Any]):
    """A3: DCF valuation model."""
    ws = wb.create_sheet("A3. Valuation Model")

    val_data = data.get("valuation_analysis", {})
    dcf = val_data.get("dcf_valuation", {})

    if not dcf:
        ws.cell(row=1, column=1, value="No valuation data available")
        return

    # Assumptions section
    ws.cell(row=1, column=1, value="DCF Valuation Model")
    ws.cell(row=1, column=1).font = Font(bold=True, size=14)

    ws.cell(row=3, column=1, value="Assumptions")
    ws.cell(row=3, column=1).font = Font(bold=True)

    assumptions = [
        ("Risk-Free Rate", dcf.get("risk_free_rate"), PERCENT_FORMAT),
        ("Equity Risk Premium", dcf.get("equity_risk_premium"), PERCENT_FORMAT),
        ("Beta", dcf.get("beta"), "0.00"),
        ("Cost of Equity", dcf.get("cost_of_equity"), PERCENT_FORMAT),
        ("Cost of Debt (after-tax)", dcf.get("cost_of_debt"), PERCENT_FORMAT),
        ("Debt Weight", dcf.get("debt_weight"), PERCENT_FORMAT),
        ("Equity Weight", dcf.get("equity_weight"), PERCENT_FORMAT),
        ("WACC", dcf.get("wacc"), PERCENT_FORMAT),
        ("Terminal Growth Rate", dcf.get("terminal_growth_rate"), PERCENT_FORMAT),
        ("Forecast Period (years)", dcf.get("forecast_years"), "#0"),
    ]

    row = 4
    for label, value, fmt in assumptions:
        ws.cell(row=row, column=1, value=label)
        cell = ws.cell(row=row, column=2, value=value)
        if value is not None:
            cell.number_format = fmt
        row += 1

    # Valuation output
    row += 1
    ws.cell(row=row, column=1, value="Valuation Output")
    ws.cell(row=row, column=1).font = Font(bold=True)
    row += 1

    outputs = [
        ("Present Value of FCFs", dcf.get("pv_fcf"), CURRENCY_FORMAT),
        ("Terminal Value", dcf.get("terminal_value"), CURRENCY_FORMAT),
        ("PV of Terminal Value", dcf.get("pv_terminal_value"), CURRENCY_FORMAT),
        ("Enterprise Value", dcf.get("enterprise_value"), CURRENCY_FORMAT),
        ("Less: Net Debt", dcf.get("net_debt"), CURRENCY_FORMAT),
        ("Equity Value", dcf.get("equity_value"), CURRENCY_FORMAT),
        ("Shares Outstanding", dcf.get("shares_outstanding"), INTEGER_FORMAT),
        ("Intrinsic Value per Share", dcf.get("intrinsic_value_per_share"), '$#,##0.00'),
        ("Current Price", dcf.get("current_price"), '$#,##0.00'),
        ("Upside/Downside", dcf.get("upside_pct"), PERCENT_FORMAT),
    ]

    for label, value, fmt in outputs:
        ws.cell(row=row, column=1, value=label)
        cell = ws.cell(row=row, column=2, value=value)
        if value is not None:
            cell.number_format = fmt
        row += 1

    _auto_column_width(ws)


def _sheet_a4_sensitivity(wb: Workbook, data: Dict[str, Any]):
    """A4: Sensitivity grid (WACC × terminal growth)."""
    ws = wb.create_sheet("A4. Sensitivity Grid")

    val_data = data.get("valuation_analysis", {})
    sensitivity = val_data.get("sensitivity_analysis", {})
    grid = sensitivity.get("sensitivity_grid", [])

    if not grid:
        ws.cell(row=1, column=1, value="No sensitivity data available")
        return

    ws.cell(row=1, column=1, value="Intrinsic Value Sensitivity (WACC × Terminal Growth)")
    ws.cell(row=1, column=1).font = Font(bold=True, size=12)

    # Get unique WACC and growth values
    wacc_values = sorted(set(row.get("wacc", 0) for row in grid))
    growth_values = sorted(set(row.get("terminal_growth", 0) for row in grid))

    # Create grid
    headers = ["WACC \\ Growth"] + [f"{g:.1%}" for g in growth_values]
    start_row = 3
    for col, header in enumerate(headers, 1):
        ws.cell(row=start_row, column=col, value=header)
    _apply_header_style(ws, start_row, len(headers))

    # Fill grid
    for row_idx, wacc in enumerate(wacc_values, start_row + 1):
        ws.cell(row=row_idx, column=1, value=f"{wacc:.1%}")
        for col_idx, growth in enumerate(growth_values, 2):
            # Find the value for this WACC/growth combination
            for row in grid:
                if abs(row.get("wacc", 0) - wacc) < 0.001 and abs(row.get("terminal_growth", 0) - growth) < 0.001:
                    cell = ws.cell(row=row_idx, column=col_idx, value=row.get("intrinsic_value"))
                    cell.number_format = '$#,##0.00'
                    cell.border = THIN_BORDER
                    break

    _auto_column_width(ws)


def _sheet_a5_comps(wb: Workbook, data: Dict[str, Any]):
    """A5: Peer comparables."""
    ws = wb.create_sheet("A5. Peer Comparables")

    comp_data = data.get("deep_comparative", {}) or data.get("peer_comparison", {})
    peers = comp_data.get("peers", []) or comp_data.get("comparables", [])

    if not peers:
        ws.cell(row=1, column=1, value="No peer comparison data available")
        return

    headers = [
        "Company", "Ticker", "Market Cap ($B)", "Revenue ($B)", "P/E",
        "EV/EBITDA", "EV/Revenue", "Gross Margin", "Net Margin", "ROE"
    ]

    rows = []
    for peer in peers:
        rows.append([
            peer.get("name", ""),
            peer.get("ticker", ""),
            peer.get("market_cap", 0) / 1e9 if peer.get("market_cap") else "",
            peer.get("revenue", 0) / 1e9 if peer.get("revenue") else "",
            peer.get("pe_ratio", ""),
            peer.get("ev_ebitda", ""),
            peer.get("ev_revenue", ""),
            peer.get("gross_margin", ""),
            peer.get("net_margin", ""),
            peer.get("roe", ""),
        ])

    _write_table(ws, headers, rows)
    _auto_column_width(ws)


def _sheet_b1_contracts(wb: Workbook, data: Dict[str, Any]):
    """B1: Federal contracts."""
    ws = wb.create_sheet("B1. Federal Contracts")

    contract_data = data.get("contract_intelligence", {})
    contracts = contract_data.get("contracts", [])

    if not contracts:
        ws.cell(row=1, column=1, value="No federal contract data available")
        return

    headers = [
        "Award ID", "Agency", "Description", "Award Date",
        "Obligated Amount", "Contract Type", "NAICS", "Place of Performance"
    ]

    rows = []
    for c in contracts[:500]:  # Limit to 500 rows
        rows.append([
            c.get("award_id", ""),
            c.get("awarding_agency", ""),
            c.get("description", "")[:100],
            c.get("start_date", ""),
            c.get("obligated_amount", 0),
            c.get("contract_type", ""),
            c.get("naics_code", ""),
            c.get("place_of_performance", ""),
        ])

    _write_table(ws, headers, rows)

    # Format currency column
    for row in range(2, len(rows) + 2):
        ws.cell(row=row, column=5).number_format = CURRENCY_FORMAT

    _auto_column_width(ws)


def _sheet_b2_subawards(wb: Workbook, data: Dict[str, Any]):
    """B2: Contract subawards."""
    ws = wb.create_sheet("B2. Contract Subawards")

    contract_data = data.get("contract_intelligence", {})
    subawards = contract_data.get("subawards", [])

    if not subawards:
        ws.cell(row=1, column=1, value="No subaward data available")
        return

    headers = [
        "Prime Award ID", "Subaward Number", "Subrecipient",
        "Subaward Amount", "Award Date", "Description"
    ]

    rows = []
    for s in subawards[:500]:
        rows.append([
            s.get("prime_award_id", ""),
            s.get("subaward_number", ""),
            s.get("subrecipient_name", ""),
            s.get("subaward_amount", 0),
            s.get("award_date", ""),
            s.get("description", "")[:100],
        ])

    _write_table(ws, headers, rows)
    _auto_column_width(ws)


def _sheet_c_lobbying(wb: Workbook, data: Dict[str, Any]):
    """C: Lobbying activity."""
    ws = wb.create_sheet("C. Lobbying Activity")

    pol_data = data.get("political_intelligence", {})
    lobbying = pol_data.get("lobbying", {})
    filings = lobbying.get("filings", [])

    if not filings:
        ws.cell(row=1, column=1, value="No lobbying data available")
        return

    headers = [
        "Filing ID", "Year", "Quarter", "Registrant", "Client",
        "Amount", "Issues", "Lobbyists"
    ]

    rows = []
    for f in filings[:500]:
        rows.append([
            f.get("filing_id", ""),
            f.get("year", ""),
            f.get("quarter", ""),
            f.get("registrant", ""),
            f.get("client", ""),
            f.get("income", 0) or f.get("amount", 0),
            ", ".join(f.get("issues", []))[:100] if isinstance(f.get("issues"), list) else str(f.get("issues", ""))[:100],
            ", ".join(f.get("lobbyists", []))[:100] if isinstance(f.get("lobbyists"), list) else str(f.get("lobbyists", ""))[:100],
        ])

    _write_table(ws, headers, rows)

    for row in range(2, len(rows) + 2):
        ws.cell(row=row, column=6).number_format = CURRENCY_FORMAT

    _auto_column_width(ws)


def _sheet_d1_insider_transactions(wb: Workbook, data: Dict[str, Any]):
    """D1: Insider transactions (Form 4)."""
    ws = wb.create_sheet("D1. Insider Transactions")

    insider_data = data.get("insider_transactions", {})
    transactions = insider_data.get("transactions", [])

    if not transactions:
        ws.cell(row=1, column=1, value="No insider transaction data available")
        return

    headers = [
        "Filing Date", "Name", "Title", "Transaction Type",
        "Shares", "Price", "Value", "Direct/Indirect", "10b5-1 Plan"
    ]

    rows = []
    for t in transactions[:1000]:  # Limit to 1000 rows
        rows.append([
            t.get("filing_date", ""),
            t.get("owner_name", ""),
            t.get("owner_title", ""),
            t.get("transaction_code", ""),
            t.get("shares", 0),
            t.get("price", 0),
            t.get("value", 0),
            "Direct" if t.get("is_direct") else "Indirect",
            "Yes" if t.get("is_10b5_1") else "No",
        ])

    _write_table(ws, headers, rows)

    for row in range(2, len(rows) + 2):
        ws.cell(row=row, column=5).number_format = INTEGER_FORMAT
        ws.cell(row=row, column=6).number_format = '$#,##0.00'
        ws.cell(row=row, column=7).number_format = CURRENCY_FORMAT

    _auto_column_width(ws)


def _sheet_d2_insider_summary(wb: Workbook, data: Dict[str, Any]):
    """D2: Insider summary by person."""
    ws = wb.create_sheet("D2. Insider Summary")

    insider_data = data.get("insider_transactions", {})
    transactions = insider_data.get("transactions", [])

    if not transactions:
        ws.cell(row=1, column=1, value="No insider transaction data available")
        return

    # Aggregate by person
    summary = {}
    for t in transactions:
        name = t.get("owner_name", "Unknown")
        if name not in summary:
            summary[name] = {
                "name": name,
                "title": t.get("owner_title", ""),
                "total_acquired": 0,
                "total_disposed": 0,
                "transactions": 0,
            }

        shares = t.get("shares", 0) or 0
        code = t.get("transaction_code", "")

        if code in ("P", "A", "M"):  # Purchase, Award, Conversion
            summary[name]["total_acquired"] += shares
        elif code in ("S", "D", "F"):  # Sale, Disposition, Tax
            summary[name]["total_disposed"] += shares

        summary[name]["transactions"] += 1

    headers = ["Name", "Title", "Total Acquired", "Total Disposed", "Net Position", "Transactions"]

    rows = []
    for person in sorted(summary.values(), key=lambda x: x["transactions"], reverse=True):
        net = person["total_acquired"] - person["total_disposed"]
        rows.append([
            person["name"],
            person["title"],
            person["total_acquired"],
            person["total_disposed"],
            net,
            person["transactions"],
        ])

    _write_table(ws, headers, rows)

    for row in range(2, len(rows) + 2):
        for col in range(3, 7):
            ws.cell(row=row, column=col).number_format = INTEGER_FORMAT

    _auto_column_width(ws)


def _sheet_h1_litigation(wb: Workbook, data: Dict[str, Any]):
    """H1: Litigation matters."""
    ws = wb.create_sheet("H1. Litigation Matters")

    lit_data = data.get("litigation_intelligence", {})
    cases = lit_data.get("federal_cases", {}).get("cases", [])

    if not cases:
        ws.cell(row=1, column=1, value="No litigation data available")
        return

    headers = [
        "Case Name", "Court", "Case Number", "Filed Date",
        "Status", "Category", "Exposure ($)", "Source URL"
    ]

    rows = []
    for c in cases[:200]:
        rows.append([
            c.get("case_name", ""),
            c.get("court", ""),
            c.get("docket_number", ""),
            c.get("date_filed", ""),
            c.get("status", ""),
            c.get("category", ""),
            c.get("exposure", ""),
            c.get("url", ""),
        ])

    _write_table(ws, headers, rows)
    _auto_column_width(ws)


def _sheet_h2_export_controls(wb: Workbook, data: Dict[str, Any]):
    """H2: Export controls and sanctions."""
    ws = wb.create_sheet("H2. Export Controls")

    lit_data = data.get("litigation_intelligence", {})
    export_controls = lit_data.get("export_controls", {})

    # Add precedent library if available
    precedent = data.get("government_precedent_library", {})

    ws.cell(row=1, column=1, value="Export Control & Sanctions Status")
    ws.cell(row=1, column=1).font = Font(bold=True, size=12)

    row = 3
    checks = [
        ("Entity List (BIS)", export_controls.get("entity_list_status", "Not Listed")),
        ("OFAC SDN List", export_controls.get("ofac_status", "Not Listed")),
        ("ITAR Restrictions", export_controls.get("itar_status", "None")),
        ("EAR Classification", export_controls.get("ear_classification", "N/A")),
    ]

    for label, status in checks:
        ws.cell(row=row, column=1, value=label)
        ws.cell(row=row, column=2, value=status)
        row += 1

    # Add industry precedents if available
    if precedent.get("curated_precedents"):
        row += 2
        ws.cell(row=row, column=1, value="Industry Regulatory Precedents")
        ws.cell(row=row, column=1).font = Font(bold=True)
        row += 1

        for p in precedent.get("curated_precedents", [])[:10]:
            ws.cell(row=row, column=1, value=p.get("case", ""))
            ws.cell(row=row, column=2, value=p.get("relevance", ""))
            ws.cell(row=row, column=3, value=p.get("year", ""))
            row += 1

    _auto_column_width(ws)


# ── Main Generator ────────────────────────────────────────────────────────────

def generate_xlsx_appendix(
    data: Dict[str, Any],
    output_dir: Optional[str] = None,
    filename: Optional[str] = None,
) -> str:
    """
    Generate the 13-sheet XLSX appendix workbook.

    Args:
        data: Deep research data dictionary
        output_dir: Output directory path (defaults to current directory)
        filename: Output filename (defaults to "{entity}_appendix_{date}.xlsx")

    Returns:
        Path to the generated XLSX file.
    """
    if not OPENPYXL_AVAILABLE:
        raise RuntimeError("openpyxl is required for XLSX generation")

    entity_name = data.get("entity_name", "Company")
    ticker = data.get("ticker", "")

    # Create workbook
    wb = Workbook()

    # Remove default sheet
    if "Sheet" in wb.sheetnames:
        del wb["Sheet"]

    # Generate all sheets
    logger.info("Generating A1: Annual Financials")
    _sheet_a1_annual_financials(wb, data)

    logger.info("Generating A2: Quarterly Financials")
    _sheet_a2_quarterly_financials(wb, data)

    logger.info("Generating A3: Valuation Model")
    _sheet_a3_valuation(wb, data)

    logger.info("Generating A4: Sensitivity Grid")
    _sheet_a4_sensitivity(wb, data)

    logger.info("Generating A5: Peer Comparables")
    _sheet_a5_comps(wb, data)

    logger.info("Generating B1: Federal Contracts")
    _sheet_b1_contracts(wb, data)

    logger.info("Generating B2: Contract Subawards")
    _sheet_b2_subawards(wb, data)

    logger.info("Generating C: Lobbying Activity")
    _sheet_c_lobbying(wb, data)

    logger.info("Generating D1: Insider Transactions")
    _sheet_d1_insider_transactions(wb, data)

    logger.info("Generating D2: Insider Summary")
    _sheet_d2_insider_summary(wb, data)

    logger.info("Generating H1: Litigation Matters")
    _sheet_h1_litigation(wb, data)

    logger.info("Generating H2: Export Controls")
    _sheet_h2_export_controls(wb, data)

    # Determine output path
    if output_dir:
        output_path = Path(output_dir)
    else:
        output_path = Path.cwd()

    output_path.mkdir(parents=True, exist_ok=True)

    if filename:
        output_file = output_path / filename
    else:
        date_str = datetime.now().strftime("%Y%m%d")
        safe_name = "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in entity_name)
        output_file = output_path / f"{safe_name}_{ticker}_appendix_{date_str}.xlsx"

    # Save workbook
    wb.save(str(output_file))
    logger.info("XLSX appendix saved to %s", output_file)

    return str(output_file)


def generate_xlsx_bytes(data: Dict[str, Any]) -> bytes:
    """
    Generate the XLSX appendix as bytes (for API responses).

    Args:
        data: Deep research data dictionary

    Returns:
        XLSX file contents as bytes.
    """
    if not OPENPYXL_AVAILABLE:
        raise RuntimeError("openpyxl is required for XLSX generation")

    # Create workbook
    wb = Workbook()

    if "Sheet" in wb.sheetnames:
        del wb["Sheet"]

    # Generate all sheets
    _sheet_a1_annual_financials(wb, data)
    _sheet_a2_quarterly_financials(wb, data)
    _sheet_a3_valuation(wb, data)
    _sheet_a4_sensitivity(wb, data)
    _sheet_a5_comps(wb, data)
    _sheet_b1_contracts(wb, data)
    _sheet_b2_subawards(wb, data)
    _sheet_c_lobbying(wb, data)
    _sheet_d1_insider_transactions(wb, data)
    _sheet_d2_insider_summary(wb, data)
    _sheet_h1_litigation(wb, data)
    _sheet_h2_export_controls(wb, data)

    # Save to bytes
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output.read()
