#!/usr/bin/env python3
"""
Generate Intelligence Report for a Ticker
==========================================
Creates a comprehensive 100+ page intelligence report including:
- JSON data file (all raw data)
- Markdown report (formatted narrative)
- PDF report (professional print-ready)

Usage:
    cd apps/api
    python scripts/generate_intelligence_report.py --ticker NVDA
    python scripts/generate_intelligence_report.py --ticker MSFT --peers "AAPL,GOOGL"

Environment:
    DATABASE_URL - PostgreSQL connection string
    OPENAI_API_KEY - For narrative generation
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Reports output directory
REPORTS_DIR = Path(__file__).parent.parent.parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


def resolve_entity_name(ticker: str) -> str:
    """Resolve ticker to full entity name using SEC EDGAR or fallback mapping."""
    # Common ticker -> name mappings for fast lookup
    TICKER_MAP = {
        "AAPL": "Apple Inc",
        "MSFT": "Microsoft Corporation",
        "GOOGL": "Alphabet Inc",
        "AMZN": "Amazon.com Inc",
        "META": "Meta Platforms Inc",
        "NVDA": "NVIDIA Corporation",
        "TSLA": "Tesla Inc",
        "JPM": "JPMorgan Chase & Co",
        "JNJ": "Johnson & Johnson",
        "V": "Visa Inc",
        "PG": "Procter & Gamble Co",
        "UNH": "UnitedHealth Group Inc",
        "HD": "Home Depot Inc",
        "MA": "Mastercard Inc",
        "DIS": "Walt Disney Co",
        "BAC": "Bank of America Corp",
        "ADBE": "Adobe Inc",
        "CRM": "Salesforce Inc",
        "NFLX": "Netflix Inc",
        "COST": "Costco Wholesale Corp",
        "PEP": "PepsiCo Inc",
        "TMO": "Thermo Fisher Scientific Inc",
        "CSCO": "Cisco Systems Inc",
        "AVGO": "Broadcom Inc",
        "ACN": "Accenture PLC",
        "ABT": "Abbott Laboratories",
        "MRK": "Merck & Co Inc",
        "WMT": "Walmart Inc",
        "LLY": "Eli Lilly and Co",
        "AMD": "Advanced Micro Devices Inc",
        "INTC": "Intel Corporation",
        "ORCL": "Oracle Corporation",
        "IBM": "International Business Machines Corp",
        "QCOM": "Qualcomm Inc",
        "TXN": "Texas Instruments Inc",
        "NOW": "ServiceNow Inc",
        "INTU": "Intuit Inc",
        "AMAT": "Applied Materials Inc",
        "LRCX": "Lam Research Corp",
        "MU": "Micron Technology Inc",
        "SNPS": "Synopsys Inc",
        "CDNS": "Cadence Design Systems Inc",
        "KLAC": "KLA Corporation",
        "MRVL": "Marvell Technology Inc",
        "ADI": "Analog Devices Inc",
        "NXPI": "NXP Semiconductors NV",
        "ON": "ON Semiconductor Corp",
        "MCHP": "Microchip Technology Inc",
        "GS": "Goldman Sachs Group Inc",
        "MS": "Morgan Stanley",
        "C": "Citigroup Inc",
        "WFC": "Wells Fargo & Co",
        "AXP": "American Express Co",
        "BLK": "BlackRock Inc",
        "SCHW": "Charles Schwab Corp",
        "CME": "CME Group Inc",
        "ICE": "Intercontinental Exchange Inc",
        "COF": "Capital One Financial Corp",
        "USB": "U.S. Bancorp",
        "PNC": "PNC Financial Services Group Inc",
        "TFC": "Truist Financial Corp",
        "BK": "Bank of New York Mellon Corp",
        "STT": "State Street Corp",
        "AIG": "American International Group Inc",
        "MET": "MetLife Inc",
        "PRU": "Prudential Financial Inc",
        "ALL": "Allstate Corp",
        "TRV": "Travelers Companies Inc",
        "CB": "Chubb Ltd",
        "PFE": "Pfizer Inc",
        "ABBV": "AbbVie Inc",
        "BMY": "Bristol-Myers Squibb Co",
        "AMGN": "Amgen Inc",
        "GILD": "Gilead Sciences Inc",
        "BIIB": "Biogen Inc",
        "REGN": "Regeneron Pharmaceuticals Inc",
        "VRTX": "Vertex Pharmaceuticals Inc",
        "MRNA": "Moderna Inc",
        "ZTS": "Zoetis Inc",
        "DHR": "Danaher Corp",
        "SYK": "Stryker Corp",
        "ISRG": "Intuitive Surgical Inc",
        "MDT": "Medtronic PLC",
        "BSX": "Boston Scientific Corp",
        "EW": "Edwards Lifesciences Corp",
        "BDX": "Becton Dickinson and Co",
        "IDXX": "IDEXX Laboratories Inc",
        "A": "Agilent Technologies Inc",
        "IQV": "IQVIA Holdings Inc",
        "LMT": "Lockheed Martin Corp",
        "RTX": "RTX Corporation",
        "BA": "Boeing Co",
        "NOC": "Northrop Grumman Corp",
        "GD": "General Dynamics Corp",
        "LHX": "L3Harris Technologies Inc",
        "HII": "Huntington Ingalls Industries Inc",
        "GE": "General Electric Co",
        "HON": "Honeywell International Inc",
        "CAT": "Caterpillar Inc",
        "DE": "Deere & Co",
        "MMM": "3M Co",
        "EMR": "Emerson Electric Co",
        "ETN": "Eaton Corp PLC",
        "ROK": "Rockwell Automation Inc",
        "CMI": "Cummins Inc",
        "PH": "Parker-Hannifin Corp",
        "ITW": "Illinois Tool Works Inc",
        "AME": "AMETEK Inc",
        "XOM": "Exxon Mobil Corp",
        "CVX": "Chevron Corp",
        "COP": "ConocoPhillips",
        "EOG": "EOG Resources Inc",
        "SLB": "Schlumberger Ltd",
        "OXY": "Occidental Petroleum Corp",
        "PSX": "Phillips 66",
        "MPC": "Marathon Petroleum Corp",
        "VLO": "Valero Energy Corp",
        "KMI": "Kinder Morgan Inc",
        "WMB": "Williams Companies Inc",
        "NEE": "NextEra Energy Inc",
        "DUK": "Duke Energy Corp",
        "SO": "Southern Co",
        "D": "Dominion Energy Inc",
        "AEP": "American Electric Power Co Inc",
        "EXC": "Exelon Corp",
        "SRE": "Sempra",
        "XEL": "Xcel Energy Inc",
        "PEG": "Public Service Enterprise Group Inc",
        "ED": "Consolidated Edison Inc",
        "WEC": "WEC Energy Group Inc",
        "ES": "Eversource Energy",
        "AWK": "American Water Works Co Inc",
        "AMT": "American Tower Corp",
        "CCI": "Crown Castle Inc",
        "PLD": "Prologis Inc",
        "EQIX": "Equinix Inc",
        "PSA": "Public Storage",
        "SPG": "Simon Property Group Inc",
        "O": "Realty Income Corp",
        "WELL": "Welltower Inc",
        "DLR": "Digital Realty Trust Inc",
        "AVB": "AvalonBay Communities Inc",
        "EQR": "Equity Residential",
        "VTR": "Ventas Inc",
        "ARE": "Alexandria Real Estate Equities Inc",
        "MAA": "Mid-America Apartment Communities Inc",
        "UDR": "UDR Inc",
        "ESS": "Essex Property Trust Inc",
        "CPT": "Camden Property Trust",
        "T": "AT&T Inc",
        "VZ": "Verizon Communications Inc",
        "TMUS": "T-Mobile US Inc",
        "CHTR": "Charter Communications Inc",
        "CMCSA": "Comcast Corp",
        "TSM": "Taiwan Semiconductor Manufacturing Co Ltd",
        "ASML": "ASML Holding NV",
        "SAP": "SAP SE",
        "TM": "Toyota Motor Corp",
        "SONY": "Sony Group Corp",
        "NVO": "Novo Nordisk A/S",
        "AZN": "AstraZeneca PLC",
        "SHEL": "Shell PLC",
        "BP": "BP PLC",
        "RIO": "Rio Tinto PLC",
        "BHP": "BHP Group Ltd",
        "SHOP": "Shopify Inc",
        "UBER": "Uber Technologies Inc",
        "ABNB": "Airbnb Inc",
        "SQ": "Block Inc",
        "PYPL": "PayPal Holdings Inc",
        "COIN": "Coinbase Global Inc",
        "HOOD": "Robinhood Markets Inc",
        "DKNG": "DraftKings Inc",
        "RBLX": "Roblox Corp",
        "SNAP": "Snap Inc",
        "PINS": "Pinterest Inc",
        "ZM": "Zoom Video Communications Inc",
        "DOCU": "DocuSign Inc",
        "OKTA": "Okta Inc",
        "CRWD": "CrowdStrike Holdings Inc",
        "ZS": "Zscaler Inc",
        "PANW": "Palo Alto Networks Inc",
        "FTNT": "Fortinet Inc",
        "NET": "Cloudflare Inc",
        "DDOG": "Datadog Inc",
        "MDB": "MongoDB Inc",
        "SNOW": "Snowflake Inc",
        "PLTR": "Palantir Technologies Inc",
        "PATH": "UiPath Inc",
        "AI": "C3.ai Inc",
        "SMCI": "Super Micro Computer Inc",
    }

    if ticker.upper() in TICKER_MAP:
        return TICKER_MAP[ticker.upper()]

    # Try to resolve via SEC EDGAR
    try:
        from app.connectors.sec_connector import search_company
        results = search_company(ticker)
        if results and len(results) > 0:
            return results[0].get("name", ticker.upper())
    except Exception as e:
        logger.warning(f"SEC lookup failed for {ticker}: {e}")

    # Fallback to ticker as entity name
    return ticker.upper()


def generate_report(ticker: str, peers: str = "") -> dict:
    """Generate intelligence report for a ticker."""
    from app.db.session import SessionLocal
    from app.services.intelligence_service import generate_intelligence_report

    # Try to import enhanced narrative functions
    try:
        from app.services.enhanced_narrative_service import (
            generate_executive_summary,
            generate_investment_thesis,
            generate_swot_analysis,
            generate_risk_matrix,
            generate_bottom_line,
        )
        ENHANCED_AVAILABLE = True
    except ImportError:
        ENHANCED_AVAILABLE = False
        logger.warning("Enhanced narrative service not available")

    entity_name = resolve_entity_name(ticker)
    logger.info(f"Generating report for {entity_name} (ticker: {ticker})")

    # Create database session
    db = SessionLocal()

    try:
        # Generate base intelligence report
        report_data = generate_intelligence_report(
            db=db,
            entity_name=entity_name,
            entity_type="org",
            ticker=ticker.upper()
        )

        # Add ticker to report
        report_data["ticker"] = ticker.upper()

        # Generate enhanced narratives (Investment Thesis, SWOT, Risk Matrix, etc.)
        if ENHANCED_AVAILABLE:
            try:
                enhanced_sections = []

                # Generate each enhanced section
                try:
                    exec_summary = generate_executive_summary(report_data)
                    if exec_summary:
                        enhanced_sections.append({
                            "name": "Executive Summary",
                            "narrative": exec_summary,
                        })
                except Exception as e:
                    logger.warning(f"Executive summary generation failed: {e}")

                try:
                    thesis = generate_investment_thesis(report_data)
                    if thesis:
                        enhanced_sections.append({
                            "name": "Investment Thesis",
                            "narrative": thesis,
                        })
                except Exception as e:
                    logger.warning(f"Investment thesis generation failed: {e}")

                try:
                    swot = generate_swot_analysis(report_data)
                    if swot:
                        enhanced_sections.append({
                            "name": "SWOT Analysis",
                            "narrative": swot,
                        })
                except Exception as e:
                    logger.warning(f"SWOT analysis generation failed: {e}")

                try:
                    risk = generate_risk_matrix(report_data)
                    if risk:
                        enhanced_sections.append({
                            "name": "Risk Matrix",
                            "narrative": risk,
                        })
                except Exception as e:
                    logger.warning(f"Risk matrix generation failed: {e}")

                try:
                    bottom = generate_bottom_line(report_data)
                    if bottom:
                        enhanced_sections.append({
                            "name": "Bottom Line",
                            "narrative": bottom,
                        })
                except Exception as e:
                    logger.warning(f"Bottom line generation failed: {e}")

                # Merge enhanced sections into report
                existing_names = {s["name"] for s in report_data.get("sections", [])}
                for section in enhanced_sections:
                    if section["name"] not in existing_names:
                        report_data.setdefault("sections", []).append(section)

            except Exception as e:
                logger.warning(f"Enhanced narrative generation failed: {e}")

        return report_data

    finally:
        db.close()


def save_report(report_data: dict, ticker: str, output_dir: Path = None) -> dict:
    """Save report to JSON, Markdown, and PDF files."""
    if output_dir is None:
        output_dir = REPORTS_DIR

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    entity_name = report_data.get("entity_name", ticker).upper().replace(" ", "_").replace(",", "")
    base_name = f"{entity_name}_Intelligence"

    output_files = {}

    # Save JSON data file
    json_path = output_dir / f"{base_name}_Data_{timestamp}.json"
    with open(json_path, "w") as f:
        json.dump(report_data, f, indent=2, default=str)
    output_files["json"] = str(json_path)
    logger.info(f"Saved JSON: {json_path}")

    # Generate and save Markdown
    try:
        md_content = generate_markdown(report_data)
        md_path = output_dir / f"{base_name}_Report_{timestamp}.md"
        with open(md_path, "w") as f:
            f.write(md_content)
        output_files["markdown"] = str(md_path)
        logger.info(f"Saved Markdown: {md_path}")
    except Exception as e:
        logger.warning(f"Markdown generation failed: {e}")

    # Generate and save PDF
    try:
        from app.services.premium_pdf_service import convert_to_premium_pdf

        pdf_bytes = convert_to_premium_pdf(
            entity_name=report_data.get("entity_name", ticker),
            ticker=ticker.upper(),
            report_data=report_data,
            prepared_for="Intelligence Analysis",
            organization="ENTERPRISE INTELLIGENCE PLATFORM"
        )

        pdf_path = output_dir / f"{base_name}_Report_{timestamp}.pdf"
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)
        output_files["pdf"] = str(pdf_path)
        logger.info(f"Saved PDF: {pdf_path} ({len(pdf_bytes):,} bytes)")

    except ImportError:
        logger.warning("Premium PDF service not available, skipping PDF generation")
    except Exception as e:
        logger.warning(f"PDF generation failed: {e}")

    return output_files


def generate_markdown(report_data: dict) -> str:
    """Generate Markdown report from report data."""
    lines = []

    entity_name = report_data.get("entity_name", "Unknown Entity")
    ticker = report_data.get("ticker", "")

    lines.append(f"# Intelligence Report: {entity_name}")
    if ticker:
        lines.append(f"**Ticker:** {ticker}")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Table of Contents
    lines.append("## Table of Contents")
    for i, section in enumerate(report_data.get("sections", []), 1):
        name = section.get("name", f"Section {i}")
        anchor = name.lower().replace(" ", "-").replace("&", "and")
        lines.append(f"{i}. [{name}](#{anchor})")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Sections
    for section in report_data.get("sections", []):
        name = section.get("name", "Unnamed Section")
        lines.append(f"## {name}")
        lines.append("")

        # If section has narrative
        if section.get("narrative"):
            lines.append(section["narrative"])
            lines.append("")

        # If section has claims
        for claim in section.get("claims", []):
            text = claim.get("text", "")
            source = claim.get("source", "")
            confidence = claim.get("confidence", "")
            source_url = claim.get("source_url", "")

            if text:
                lines.append(f"- {text}")
                if source:
                    if source_url:
                        lines.append(f"  - *Source: [{source}]({source_url})* [{confidence}]")
                    else:
                        lines.append(f"  - *Source: {source}* [{confidence}]")
                lines.append("")

        lines.append("---")
        lines.append("")

    # Relationships
    if report_data.get("relationships_created"):
        lines.append("## Relationships")
        lines.append("")
        for rel in report_data["relationships_created"]:
            kind = rel.get("kind", "related")
            entity = rel.get("entity", "Unknown")
            context = rel.get("context", "")
            lines.append(f"- **{kind}**: {entity}")
            if context:
                lines.append(f"  - {context}")
        lines.append("")

    # Data Sources
    if report_data.get("data_sources"):
        lines.append("## Data Sources")
        lines.append("")
        for source, available in report_data["data_sources"].items():
            status = "✅" if available else "❌"
            lines.append(f"- {status} {source}")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate Intelligence Report for a Ticker")
    parser.add_argument("--ticker", required=True, help="Stock ticker symbol (e.g., NVDA)")
    parser.add_argument("--peers", default="", help="Comma-separated peer tickers for comparison")
    parser.add_argument("--output-dir", type=Path, default=None, help="Output directory")
    args = parser.parse_args()

    # Use provided output dir or default
    output_dir = args.output_dir if args.output_dir else REPORTS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    ticker = args.ticker.upper()

    logger.info("=" * 60)
    logger.info(f"Generating Intelligence Report for {ticker}")
    logger.info("=" * 60)

    try:
        # Generate report
        report_data = generate_report(ticker, args.peers)

        # Save report files
        output_files = save_report(report_data, ticker, output_dir)

        logger.info("=" * 60)
        logger.info("Report Generation Complete!")
        logger.info(f"Output files: {json.dumps(output_files, indent=2)}")
        logger.info("=" * 60)

        # Print output files for caller to parse
        print(json.dumps(output_files))
        return 0

    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
