"""
Layer 1 Intelligence Report API
POST /intelligence/generate              — run connectors for an entity, build graph, generate cited dossier
POST /intelligence/generate-enhanced     — generate enhanced report with AI analysis
POST /intelligence/generate-full-report  — generate comprehensive 100+ page PDF report for a ticker
POST /intelligence/generate-network-report — generate network/group intelligence report (PayPal Mafia, etc.)
GET  /intelligence/report-job/{job_id}   — check status of a report generation job
GET  /intelligence/report-job/{job_id}/download/{file_type} — download generated report file
GET  /intelligence/available-networks    — list available network configurations
GET  /intelligence/{report_id}           — retrieve a generated intelligence report
GET  /intelligence/                      — list recent intelligence reports
GET  /intelligence/{report_id}/pdf-professional — download enhanced PDF with charts
GET  /intelligence/{report_id}/excel-detailed   — download multi-sheet Excel
GET  /intelligence/{report_id}/powerpoint-detailed — download data-rich PowerPoint
"""
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, Dict, Any, List
import io
import logging
import os
import time
from pydantic import BaseModel, Field
from app.db.session import get_db
from app.services.intelligence_service import (
    generate_intelligence_report,
    get_intelligence_report,
    list_intelligence_reports,
)
from app.services.intelligence_activation_service import (
    build_paypal_mafia_report_addendum,
    build_contract_probability_analysis,
    build_correlation_analysis,
    build_interactive_report_html,
    build_network_analysis,
    build_self_dealing_analysis,
    render_interactive_report_from_report,
)

# Enhanced report functions
try:
    from app.services.intelligence_service import (
        generate_enhanced_intelligence_report,
        get_enhanced_intelligence_report,
        list_enhanced_intelligence_reports,
    )
    _ENHANCED_AVAILABLE = True
except ImportError:
    _ENHANCED_AVAILABLE = False

try:
    from app.connectors.browser_research_agent import research_entity_browser, detect_jurisdiction
    _BROWSER_AVAILABLE = True
except ImportError:
    _BROWSER_AVAILABLE = False

try:
    from app.connectors.apollo_connector import (
        search_people, enrich_organization, fetch_org_chart, search_organization,
    )
    _APOLLO_AVAILABLE = True
except ImportError:
    _APOLLO_AVAILABLE = False

try:
    from app.connectors.private_company_connector import (
        fetch_private_company_intel,
        search_opencorporates,
        search_gleif,
        search_fincen_entities,
    )
    _PRIV_CO_AVAILABLE = True
except ImportError:
    _PRIV_CO_AVAILABLE = False

try:
    from app.services.pdf_service import generate_report_pdf
    _PDF_AVAILABLE = True
except ImportError:
    _PDF_AVAILABLE = False

try:
    from app.services.pdf_service import generate_enhanced_report_pdf
    _ENHANCED_PDF_AVAILABLE = True
except ImportError:
    _ENHANCED_PDF_AVAILABLE = False

try:
    from app.services.markdown_pdf_service import convert_markdown_to_pdf, generate_enhanced_markdown_report
    _MARKDOWN_PDF_AVAILABLE = True
except ImportError:
    _MARKDOWN_PDF_AVAILABLE = False

try:
    from app.services.premium_pdf_service import convert_to_premium_pdf
    _PREMIUM_PDF_AVAILABLE = True
except ImportError:
    _PREMIUM_PDF_AVAILABLE = False

try:
    from app.services.xlsx_appendix_service import generate_xlsx_bytes, OPENPYXL_AVAILABLE
    _XLSX_APPENDIX_AVAILABLE = OPENPYXL_AVAILABLE
except ImportError:
    _XLSX_APPENDIX_AVAILABLE = False
    def generate_xlsx_bytes(*args): return b""

try:
    from app.services.quality_gate_service import run_quality_gates, format_quality_report
    _QUALITY_GATES_AVAILABLE = True
except ImportError:
    _QUALITY_GATES_AVAILABLE = False
    def run_quality_gates(*args): return {"passed": True, "gates_passed": 0, "gates_total": 0}
    def format_quality_report(*args): return ""

try:
    from app.services.quality.decision import evaluate as _quality_evaluate
    _QUALITY_JUDGE_AVAILABLE = True
except ImportError:
    _QUALITY_JUDGE_AVAILABLE = False
    def _quality_evaluate(*args, **kwargs):
        return {"mode": "rules", "decision": "needs_review", "combined_score": None,
                "rule_result": run_quality_gates(*args), "judge_result": None}

router = APIRouter(prefix="/intelligence")
logger = logging.getLogger(__name__)


class SelfDealingRequest(BaseModel):
    entity_name: str = Field(min_length=1, max_length=200)
    ticker: str = Field(default="", max_length=20)
    related_entities: List[str] = Field(default_factory=list, max_length=25)
    include_family_network: bool = True
    include_institutional_holders: bool = True


class NetworkRequest(BaseModel):
    entity_name: str = Field(min_length=1, max_length=200)
    ticker: str = Field(default="", max_length=20)
    competitors: List[str] = Field(default_factory=list, max_length=12)
    depth: int = Field(default=1, ge=1, le=5)


class CorrelationRequest(BaseModel):
    entity_name: str = Field(min_length=1, max_length=200)
    ticker: str = Field(default="", max_length=20)
    competitors: List[str] = Field(default_factory=list, max_length=12)
    years: int = Field(default=2, ge=1, le=5)


class ContractProbabilityRequest(BaseModel):
    entity_name: str = Field(min_length=1, max_length=200)
    ticker: str = Field(default="", max_length=20)
    naics_codes: List[str] = Field(default_factory=list, max_length=20)
    keywords: List[str] = Field(default_factory=list, max_length=20)
    total_revenue: Optional[float] = None


class InteractiveReportRequest(BaseModel):
    entity_name: str = Field(min_length=1, max_length=200)
    entity_type: str = Field(default="org", pattern="^(org|person)$")
    ticker: str = Field(default="", max_length=20)


@router.post("/self-dealing")
def intelligence_self_dealing(payload: SelfDealingRequest):
    return build_self_dealing_analysis(
        entity_name=payload.entity_name,
        ticker=payload.ticker,
        related_entities=payload.related_entities,
        include_family_network=payload.include_family_network,
        include_institutional_holders=payload.include_institutional_holders,
    )


@router.post("/network")
def intelligence_network(payload: NetworkRequest):
    return build_network_analysis(
        entity_name=payload.entity_name,
        ticker=payload.ticker,
        competitors=payload.competitors,
        depth=payload.depth,
    )


@router.post("/correlation")
def intelligence_correlation(payload: CorrelationRequest):
    started = time.monotonic()
    logger.warning("route:correlation:start ticker=%s", payload.ticker)
    result = build_correlation_analysis(
        entity_name=payload.entity_name,
        ticker=payload.ticker,
        competitors=payload.competitors,
        years=payload.years,
    )
    logger.warning("route:correlation:return elapsed=%.3fs", time.monotonic() - started)
    return result


@router.post("/contract-probability")
def intelligence_contract_probability(payload: ContractProbabilityRequest):
    return build_contract_probability_analysis(
        entity_name=payload.entity_name,
        ticker=payload.ticker,
        naics_codes=payload.naics_codes,
        keywords=payload.keywords,
        total_revenue=payload.total_revenue,
    )


@router.post("/interactive-report")
def intelligence_interactive_report(
    payload: InteractiveReportRequest,
    db: Session = Depends(get_db),
):
    try:
        result = build_interactive_report_html(
            db,
            entity_name=payload.entity_name,
            entity_type=payload.entity_type,
            ticker=payload.ticker,
        )
    except RuntimeError as error:
        raise HTTPException(503, str(error))
    return HTMLResponse(content=result["html"])


@router.post("/generate")
def generate_report(
    entity_name: str,
    entity_type: str = "org",
    ticker: Optional[str] = None,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
):
    """
    Kick off a Layer 1 Entity Network Intelligence Report.
    Runs connectors (SEC, FEC, FARA, USASpending, LDA, OFAC, CourtListener),
    writes relationships + evidence, assembles report JSON, generates GPT narrative.
    Returns report_id immediately; report builds synchronously for demo.
    """
    report = generate_intelligence_report(db, entity_name=entity_name, entity_type=entity_type, ticker=ticker)
    return report


@router.post("/browser-research")
def browser_research(
    entity_name: str,
    jurisdiction: Optional[str] = None,
    context: str = "",
    deep_dive: bool = False,
):
    """
    Run browser-based research on an entity using public registries, news, and
    government sources for any jurisdiction (used as fallback for non-US entities
    or for deep dives on holding companies, vehicles, financials).

    Examples:
      POST /intelligence/browser-research?entity_name=Aeropuertos+Argentina+2000&jurisdiction=argentina
      POST /intelligence/browser-research?entity_name=Mercado+Libre&deep_dive=true
    """
    if not _BROWSER_AVAILABLE:
        raise HTTPException(503, "Browser research agent not available")
    detected_jur = jurisdiction or detect_jurisdiction(entity_name, context)
    result = research_entity_browser(
        entity_name,
        jurisdiction=detected_jur,
        context=context,
        max_sources=6 if deep_dive else 4,
        deep_dive=deep_dive,
    )
    return result


@router.get("/")
def list_reports(limit: int = 20, db: Session = Depends(get_db)):
    return list_intelligence_reports(db, limit=limit)


@router.get("/apollo/org")
def apollo_org(name: str, domain: str = ""):
    """
    Enrich an organization using Apollo.io.
    Returns headcount, revenue range, technologies, founding year, etc.

    Strategy: name-based search first (uses Apollo's internal domain resolution),
    then direct domain enrichment if domain is explicitly provided.
    """
    if not _APOLLO_AVAILABLE:
        raise HTTPException(503, "Apollo connector not available")

    result = {}
    # Explicit domain takes priority
    if domain:
        result = enrich_organization(domain=domain)
    # Name-based search is most accurate (Apollo resolves to the correct entity)
    if not result and name:
        result = search_organization(name)
    # Last resort: guess domain
    if not result and name:
        slug = name.lower().replace(" ", "").replace(".", "").replace(",", "")
        result = enrich_organization(domain=f"{slug}.com")

    return result or {"message": "No Apollo data found", "hint": "Check APOLLO_API_KEY and try adding domain= parameter"}


@router.get("/apollo/people")
def apollo_people(organization: str, limit: int = 20):
    """
    Fetch key executives and employees of an organization via Apollo.io.
    Returns up to `limit` people with name, title, email, LinkedIn URL.
    """
    if not _APOLLO_AVAILABLE:
        raise HTTPException(503, "Apollo connector not available")
    return search_people(organization=organization, limit=limit)


@router.get("/apollo/orgchart")
def apollo_orgchart(organization: str):
    """
    Fetch the C-suite + VP-level org chart for an organization via Apollo.io.
    """
    if not _APOLLO_AVAILABLE:
        raise HTTPException(503, "Apollo connector not available")
    return fetch_org_chart(organization)


@router.post("/apollo/enrich")
def apollo_enrich(
    entity_name: str,
    domain: str = "",
    include_people: bool = True,
):
    """
    Full Apollo enrichment: org profile + executives + key people search.

    Free plan: org enrichment only (by domain preferred).
    Paid plan: + people/org chart search.
    """
    if not _APOLLO_AVAILABLE:
        raise HTTPException(503, "Apollo connector not available — set APOLLO_API_KEY in .env")

    # Domain lookup first (most accurate on free tier)
    org_data = {}
    if domain:
        org_data = enrich_organization(domain=domain)
    if not org_data:
        # Try to derive domain from name
        slug = entity_name.lower().replace(" ", "").replace(".", "").replace(",", "")
        org_data = enrich_organization(domain=f"{slug}.com")
    if not org_data:
        org_data = search_organization(entity_name)

    people_data = []
    people_plan_note = ""
    if include_people:
        people_data = fetch_org_chart(entity_name)

    return {
        "entity_name":       entity_name,
        "organization":      org_data,
        "key_people":        people_data,
        "total_people":      len(people_data),
        "plan_note":         people_plan_note or None,
        "data_coverage":     {
            "org_enrichment":  bool(org_data),
            "people_search":   bool(people_data),
            "paid_plan_active": True,
        },
    }


@router.get("/apollo/health")
def apollo_health():
    """
    Verify Apollo API key is valid and account is authenticated.
    Returns account health status.
    """
    if not _APOLLO_AVAILABLE:
        return {"status": "unavailable", "reason": "APOLLO_API_KEY not set in .env"}
    try:
        import requests as req
        # Use the connector's call-time key resolver (loads .env on demand) so
        # the key is picked up even if the process started before it was added.
        from app.connectors.apollo_connector import _get_key
        key = _get_key()
        r = req.get("https://api.apollo.io/api/v1/auth/health",
                    headers={"X-Api-Key": key}, timeout=8)
        data = r.json()
        return {
            "status": "ok" if data.get("is_logged_in") else "invalid",
            "healthy": data.get("healthy"),
            "authenticated": data.get("is_logged_in"),
            "api_key_suffix": f"...{key[-6:]}" if key else "not set",
            "plan": "paid",
        }
    except Exception as e:
        return {"status": "error", "reason": str(e)}


@router.get("/private-co/search")
def private_co_search(name: str, jurisdiction: str = ""):
    """
    Full private company enrichment: OpenCorporates + GLEIF + FinCEN + FDIC.
    """
    if not _PRIV_CO_AVAILABLE:
        raise HTTPException(503, "Private company connector not available")
    return fetch_private_company_intel(name, jurisdiction=jurisdiction)


@router.get("/private-co/opencorporates")
def oc_search(name: str, jurisdiction: str = "", limit: int = 5):
    """Search OpenCorporates for company registrations globally."""
    if not _PRIV_CO_AVAILABLE:
        raise HTTPException(503, "Private company connector not available")
    return search_opencorporates(name, jurisdiction=jurisdiction, limit=limit)


@router.get("/private-co/gleif")
def gleif_search(name: str, limit: int = 3):
    """Search GLEIF for Legal Entity Identifiers."""
    if not _PRIV_CO_AVAILABLE:
        raise HTTPException(503, "Private company connector not available")
    return search_gleif(name, limit=limit)


@router.get("/private-co/fincen")
def fincen_search(name: str):
    """Search FinCEN financial institution registry."""
    if not _PRIV_CO_AVAILABLE:
        raise HTTPException(503, "Private company connector not available")
    return search_fincen_entities(name)


@router.get("/enhanced")
def list_enhanced_reports(limit: int = 20, db: Session = Depends(get_db)):
    """List recent enhanced intelligence reports.

    Defined before the catch-all /{report_id} route so "enhanced" is not
    parsed as a report id.
    """
    if not _ENHANCED_AVAILABLE:
        raise HTTPException(503, "Enhanced reports not available")
    return list_enhanced_intelligence_reports(db, limit=limit)


@router.get("/available-networks")
def list_available_networks():
    """
    List available network configurations for group reports.
    """
    return {
        "networks": [
            {
                "id": "paypal_mafia",
                "title": "The PayPal Mafia",
                "description": "Founders and early employees of PayPal who went on to shape Silicon Valley",
                "people_count": 18,
            }
        ]
    }


@router.get("/{report_id}/interactive")
def get_interactive_report(report_id: int, db: Session = Depends(get_db)):
    report = None
    if _ENHANCED_AVAILABLE:
        report = get_enhanced_intelligence_report(db, report_id)
    if not report:
        report = get_intelligence_report(db, report_id)
    if not report:
        raise HTTPException(404, "Intelligence report not found")
    try:
        result = render_interactive_report_from_report(report)
    except RuntimeError as error:
        raise HTTPException(409, str(error))
    return HTMLResponse(content=result["html"])


@router.get("/{report_id}")
def get_report(report_id: int, db: Session = Depends(get_db)):
    report = get_intelligence_report(db, report_id)
    # Fall back to the enhanced getter so enhanced reports (different kind) load
    # on historic open and return their persisted structured fields.
    if not report and _ENHANCED_AVAILABLE:
        report = get_enhanced_intelligence_report(db, report_id)
    if not report:
        raise HTTPException(404, "Intelligence report not found")
    return report


@router.get("/{report_id}/pdf")
def download_report_pdf(report_id: int, db: Session = Depends(get_db)):
    """
    Download an intelligence report as a polished PDF.
    Returns a binary PDF file suitable for direct browser download.
    """
    if not _PDF_AVAILABLE:
        raise HTTPException(503, "PDF export unavailable — install reportlab")

    report = get_intelligence_report(db, report_id)
    if not report:
        raise HTTPException(404, "Intelligence report not found")

    try:
        pdf_bytes = generate_report_pdf(report)
    except Exception as exc:
        raise HTTPException(500, f"PDF generation failed: {exc}")

    entity_slug = (report.get("entity_name") or "report").lower().replace(" ", "_")[:40]
    filename    = f"intel_{entity_slug}_{report_id}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{report_id}/word")
def download_report_word(report_id: int, db: Session = Depends(get_db)):
    """Download intelligence report as Word (.docx)."""
    try:
        from docx import Document as DocxDocument
        from docx.shared import Pt, RGBColor
    except ImportError:
        raise HTTPException(503, "python-docx not installed")

    report = get_intelligence_report(db, report_id)
    if not report:
        raise HTTPException(404, "Intelligence report not found")

    doc = DocxDocument()
    doc.add_heading(f"Intelligence Report: {report.get('entity_name', 'Unknown')}", 0)
    doc.add_paragraph(f"Generated: {report.get('created_at', '')}  |  Type: {report.get('entity_type', '')}")
    doc.add_paragraph("")

    for section in report.get("sections", []):
        doc.add_heading(section.get("title", "Section"), level=1)
        doc.add_paragraph(section.get("summary", ""))
        for claim in section.get("claims", []):
            p = doc.add_paragraph(style="List Bullet")
            p.add_run(f"[{claim.get('confidence', 'ANALYTICAL')}] ").bold = True
            p.add_run(claim.get("text", ""))
            if claim.get("source_url"):
                p.add_run(f"  ({claim['source_url']})")

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    entity_slug = (report.get("entity_name") or "report").lower().replace(" ", "_")[:40]
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="intel_{entity_slug}_{report_id}.docx"'},
    )


@router.get("/{report_id}/excel")
def download_report_excel(report_id: int, db: Session = Depends(get_db)):
    """Download intelligence report as Excel (.xlsx) — claims as rows."""
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
    except ImportError:
        raise HTTPException(503, "openpyxl not installed")

    report = get_intelligence_report(db, report_id)
    if not report:
        raise HTTPException(404, "Intelligence report not found")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Intelligence Report"

    # Header row
    headers = ["Section", "Claim", "Confidence", "Source URL"]
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="4F46E5")
        cell.alignment = Alignment(wrap_text=True)

    row = 2
    for section in report.get("sections", []):
        title = section.get("title", "")
        for claim in section.get("claims", []):
            ws.cell(row=row, column=1, value=title)
            ws.cell(row=row, column=2, value=claim.get("text", ""))
            ws.cell(row=row, column=3, value=claim.get("confidence", "ANALYTICAL"))
            ws.cell(row=row, column=4, value=claim.get("source_url", ""))
            row += 1

    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 80
    ws.column_dimensions["C"].width = 15
    ws.column_dimensions["D"].width = 50

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    entity_slug = (report.get("entity_name") or "report").lower().replace(" ", "_")[:40]
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="intel_{entity_slug}_{report_id}.xlsx"'},
    )


@router.get("/{report_id}/powerpoint")
def download_report_pptx(report_id: int, db: Session = Depends(get_db)):
    """Download intelligence report as PowerPoint (.pptx)."""
    try:
        from pptx import Presentation
        from pptx.util import Inches, Pt
        from pptx.dml.color import RGBColor as PptxRGB
    except ImportError:
        raise HTTPException(503, "python-pptx not installed")

    report = get_intelligence_report(db, report_id)
    if not report:
        raise HTTPException(404, "Intelligence report not found")

    prs = Presentation()
    blank_layout = prs.slide_layouts[1]

    # Title slide
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = f"Intelligence Report"
    slide.placeholders[1].text = f"{report.get('entity_name', 'Unknown')} — {report.get('created_at', '')[:10]}"

    # One slide per section (max 6 bullet points per slide)
    for section in report.get("sections", []):
        slide = prs.slides.add_slide(blank_layout)
        slide.shapes.title.text = section.get("title", "Section")
        body = slide.placeholders[1]
        tf = body.text_frame
        tf.word_wrap = True
        claims = section.get("claims", [])[:6]
        for i, claim in enumerate(claims):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.text = f"[{claim.get('confidence','?')}] {claim.get('text','')[:200]}"
            p.level = 0

    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    entity_slug = (report.get("entity_name") or "report").lower().replace(" ", "_")[:40]
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f'attachment; filename="intel_{entity_slug}_{report_id}.pptx"'},
    )


@router.get("/report-job/{job_id}/appendix")
def download_report_appendix(job_id: str):
    """
    Download the 13-sheet XLSX appendix for a generated report.

    The appendix workbook contains:
    - A1. Annual Financials (5-year income statement)
    - A2. Quarterly Financials (8 quarters)
    - A3. Valuation Model (DCF assumptions and output)
    - A4. Sensitivity Grid (WACC x terminal growth)
    - A5. Peer Comparables (valuation multiples)
    - B1. Federal Contracts (prime awards)
    - B2. Contract Subawards
    - C. Lobbying Activity (LDA filings)
    - D1. Insider Transactions (Form 4)
    - D2. Insider Summary (net positions)
    - H1. Litigation Matters
    - H2. Export Controls and Precedents

    Requires a completed report job with a JSON data file.
    """
    if not _XLSX_APPENDIX_AVAILABLE:
        raise HTTPException(503, "XLSX appendix generation unavailable — install openpyxl")

    job = _REPORT_JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Report job not found")

    if job["status"] != "completed":
        raise HTTPException(400, f"Report job not completed (status: {job['status']})")

    json_path = job.get("output_files", {}).get("json")
    if not json_path:
        raise HTTPException(404, "No JSON data file found for this report")

    import json
    from pathlib import Path

    json_file = Path(json_path)
    if not json_file.exists():
        raise HTTPException(404, "JSON data file not found on disk")

    try:
        with open(json_file) as f:
            data = json.load(f)
    except Exception as e:
        raise HTTPException(500, f"Failed to read JSON data: {e}")

    try:
        xlsx_bytes = generate_xlsx_bytes(data)
    except Exception as e:
        raise HTTPException(500, f"XLSX generation failed: {e}")

    ticker = job.get("ticker", "report")
    buf = io.BytesIO(xlsx_bytes)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{ticker}_appendix.xlsx"'},
    )


_QUALITY_DEFAULT_MODE = os.getenv("QUALITY_DEFAULT_MODE", "blend")


@router.get("/report-job/{job_id}/quality-gates")
def check_quality_gates(
    job_id: str,
    mode: str = Query(_QUALITY_DEFAULT_MODE, description="rules | judge | blend | ml — see docs/Quality-Judge.md"),
):
    """
    Run the quality battery on a generated report.

    Rule gates (always the compliance floor, hard-veto):
    1. Citation coverage (≥95% of numeric blocks)
    2. Arithmetic reconciliation (±0.5%)
    3. Duplicate detection (Jaccard >0.85 fails)
    4. News staleness (≤90 days; window ≤24 months)
    5. Directionality lint (lower-is-better metrics)
    6. Placeholder scan (reject TBD, N/A, $0.00, etc.)
    7. Fiscal-basis lint (FY/Q labels)
    8. Landing-page ban (deep URLs only)
    9. Named-person accuracy (≥2 sources)
    10. Sensitive-claim review (documented facts only)

    mode=rules (default): the 10 gates above, unchanged behavior.
    mode=judge: LLM-as-judge holistic read (accuracy/citations/clarity/relevance/
        neutrality) — catches subtly-bad reports that pass every rule.
    mode=blend: rules veto hard failures first (non-negotiable); otherwise
        combines the rule score with the judge score into one decision.
    mode=ml: rules veto first; otherwise the supervised classifier (trained on
        rule_features -> judge_publishable, see train_quality_classifier.py)
        substitutes for the judge — no LLM call, near-instant. Degrades to
        pure rules if no model has been trained yet.
    """
    if not _QUALITY_GATES_AVAILABLE:
        raise HTTPException(503, "Quality gate service unavailable")

    job = _REPORT_JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Report job not found")

    if job["status"] != "completed":
        raise HTTPException(400, f"Report job not completed (status: {job['status']})")

    json_path = job.get("output_files", {}).get("json")
    if not json_path:
        raise HTTPException(404, "No JSON data file found for this report")

    import json
    from pathlib import Path

    json_file = Path(json_path)
    if not json_file.exists():
        raise HTTPException(404, "JSON data file not found on disk")

    try:
        with open(json_file) as f:
            data = json.load(f)
    except Exception as e:
        raise HTTPException(500, f"Failed to read JSON data: {e}")

    if mode == "rules" or not _QUALITY_JUDGE_AVAILABLE:
        results = run_quality_gates(data)
        return {
            "job_id": job_id,
            "ticker": job.get("ticker"),
            "mode": "rules",
            "quality_gates": results,
        }

    evaluation = _quality_evaluate(data, mode=mode, report_id=job_id)
    return {
        "job_id": job_id,
        "ticker": job.get("ticker"),
        "mode": evaluation["mode"],
        "decision": evaluation["decision"],
        "combined_score": evaluation["combined_score"],
        "quality_gates": evaluation["rule_result"],
        "judge": evaluation["judge_result"],
        "ml": evaluation.get("ml_result"),
    }


# ============================================================================
# ENHANCED INTELLIGENCE REPORT ENDPOINTS
# ============================================================================

@router.post("/generate-enhanced")
def generate_enhanced_report(
    entity_name: str,
    entity_type: str = "org",
    ticker: Optional[str] = None,
    competitors: str = "",
    network_depth: int = 1,
    include_investment_thesis: bool = True,
    include_swot: bool = True,
    include_risk_matrix: bool = True,
    include_financial_health: bool = True,
    include_competitive: bool = True,
    db: Session = Depends(get_db),
):
    """
    Generate an enhanced intelligence report with AI-synthesized insights.

    This extends the standard intelligence report with:
    - Executive Summary (1-page brief with key metrics, risks, opportunities)
    - Investment Thesis (Buy/Hold/Sell with bull/bear cases)
    - SWOT Analysis (with evidence citations)
    - Risk Matrix (severity/likelihood ratings)
    - Financial Health Summary (key metrics, grade)
    - Competitive Analysis (market position, moats)

    Parameters:
        entity_name: Name of the entity to research
        entity_type: "org" or "person"
        ticker: Stock ticker (enables financial analysis)
        include_*: Flags to enable/disable specific sections
    """
    if not _ENHANCED_AVAILABLE:
        raise HTTPException(503, "Enhanced report generation not available")

    report = generate_enhanced_intelligence_report(
        db,
        entity_name=entity_name,
        entity_type=entity_type,
        ticker=ticker,
        competitors=[item.strip().upper() for item in competitors.split(",") if item.strip()],
        network_depth=network_depth,
        include_investment_thesis=include_investment_thesis,
        include_swot=include_swot,
        include_risk_matrix=include_risk_matrix,
        include_financial_health=include_financial_health,
        include_competitive=include_competitive,
    )
    return report


@router.get("/{report_id}/enhanced")
def get_enhanced_report(report_id: int, db: Session = Depends(get_db)):
    """
    Retrieve an enhanced intelligence report by ID.
    This retrieves both standard and enhanced reports.
    """
    if not _ENHANCED_AVAILABLE:
        raise HTTPException(503, "Enhanced reports not available")

    report = get_enhanced_intelligence_report(db, report_id)
    if not report:
        raise HTTPException(404, "Intelligence report not found")
    return report


@router.get("/{report_id}/pdf-professional")
def download_enhanced_pdf(report_id: int, db: Session = Depends(get_db)):
    """
    Download an enhanced intelligence report as a professional PDF.

    Includes:
    - Investment thesis badge (Buy/Hold/Sell)
    - SWOT 2x2 grid visualization
    - Risk heatmap (5x5 severity/likelihood matrix)
    - Financial metrics table
    - Financial health grade badge
    """
    if not _ENHANCED_PDF_AVAILABLE:
        raise HTTPException(503, "Enhanced PDF export unavailable — install reportlab")

    # Try enhanced report first, fall back to standard
    report = None
    if _ENHANCED_AVAILABLE:
        report = get_enhanced_intelligence_report(db, report_id)
    if not report:
        report = get_intelligence_report(db, report_id)
    if not report:
        raise HTTPException(404, "Intelligence report not found")

    try:
        pdf_bytes = generate_enhanced_report_pdf(report)
    except Exception as exc:
        raise HTTPException(500, f"PDF generation failed: {exc}")

    entity_slug = (report.get("entity_name") or "report").lower().replace(" ", "_")[:40]
    filename = f"enhanced_intel_{entity_slug}_{report_id}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{report_id}/excel-detailed")
def download_detailed_excel(report_id: int, db: Session = Depends(get_db)):
    """
    Download an enhanced intelligence report as a multi-sheet Excel workbook.

    Sheets:
    1. Executive Summary - key metrics and recommendations
    2. All Claims - detailed claims with confidence levels
    3. Financial Metrics - financial health data
    4. Risk Matrix - risk register with scores
    5. Government Contracts - procurement data
    6. Raw JSON - complete report data
    """
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        import json
    except ImportError:
        raise HTTPException(503, "openpyxl not installed")

    # Try enhanced report first
    report = None
    if _ENHANCED_AVAILABLE:
        report = get_enhanced_intelligence_report(db, report_id)
    if not report:
        report = get_intelligence_report(db, report_id)
    if not report:
        raise HTTPException(404, "Intelligence report not found")

    wb = openpyxl.Workbook()

    # Style definitions
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="4F46E5")
    alt_fill = PatternFill("solid", fgColor="F3F4F6")
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin'),
    )

    # Sheet 1: Executive Summary
    ws_summary = wb.active
    ws_summary.title = "Executive Summary"

    summary_data = [
        ["Entity Name", report.get("entity_name", "N/A")],
        ["Report ID", str(report.get("report_id", "N/A"))],
        ["Report Type", report.get("report_type", "standard")],
        ["Generated At", str(report.get("generated_at", "N/A"))[:19]],
        ["Ticker", report.get("ticker", "N/A")],
    ]

    # Add investment thesis if available
    investment_thesis = report.get("investment_thesis")
    if investment_thesis:
        summary_data.extend([
            ["", ""],
            ["INVESTMENT THESIS", ""],
            ["Recommendation", investment_thesis.get("recommendation", "N/A")],
            ["Conviction", investment_thesis.get("conviction", "N/A")],
        ])

    # Add financial health if available
    financial_health = report.get("financial_health")
    if financial_health:
        summary_data.extend([
            ["", ""],
            ["FINANCIAL HEALTH", ""],
            ["Grade", financial_health.get("grade", "N/A")],
        ])

    # Add risk score if available
    risk_matrix = report.get("risk_matrix")
    if risk_matrix:
        summary_data.extend([
            ["", ""],
            ["RISK ASSESSMENT", ""],
            ["Overall Risk Score", str(risk_matrix.get("overall_score", "N/A"))],
            ["Critical Risks", str(len(risk_matrix.get("critical_risks", [])))],
            ["High Risks", str(len(risk_matrix.get("high_risks", [])))],
        ])

    for row_idx, (key, val) in enumerate(summary_data, 1):
        ws_summary.cell(row=row_idx, column=1, value=key).font = Font(bold=True)
        ws_summary.cell(row=row_idx, column=2, value=val)

    ws_summary.column_dimensions["A"].width = 25
    ws_summary.column_dimensions["B"].width = 50

    # Sheet 2: All Claims
    ws_claims = wb.create_sheet("All Claims")
    claim_headers = ["Section", "Claim Text", "Confidence", "Source"]
    for col, h in enumerate(claim_headers, 1):
        cell = ws_claims.cell(row=1, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill

    row = 2
    for section in report.get("sections", []):
        section_name = section.get("name", section.get("title", "Section"))
        for claim in section.get("claims", []):
            ws_claims.cell(row=row, column=1, value=section_name)
            ws_claims.cell(row=row, column=2, value=str(claim.get("text", ""))[:1000])
            ws_claims.cell(row=row, column=3, value=claim.get("confidence", "ANALYTICAL"))
            ws_claims.cell(row=row, column=4, value=claim.get("source", ""))
            if row % 2 == 0:
                for col in range(1, 5):
                    ws_claims.cell(row=row, column=col).fill = alt_fill
            row += 1

    ws_claims.column_dimensions["A"].width = 30
    ws_claims.column_dimensions["B"].width = 100
    ws_claims.column_dimensions["C"].width = 15
    ws_claims.column_dimensions["D"].width = 40

    # Sheet 3: Financial Metrics
    ws_financial = wb.create_sheet("Financial Metrics")
    financial_data = report.get("financial_data", {})
    fundamentals = financial_data.get("fundamentals", {}) if financial_data else {}

    fin_headers = ["Metric", "Value"]
    for col, h in enumerate(fin_headers, 1):
        cell = ws_financial.cell(row=1, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill

    row = 2
    if fundamentals:
        for key, val in fundamentals.items():
            if val is not None:
                ws_financial.cell(row=row, column=1, value=key)
                ws_financial.cell(row=row, column=2, value=str(val))
                row += 1

    ws_financial.column_dimensions["A"].width = 30
    ws_financial.column_dimensions["B"].width = 25

    # Sheet 4: Risk Matrix
    ws_risks = wb.create_sheet("Risk Matrix")
    risk_headers = ["ID", "Description", "Category", "Severity", "Likelihood", "Score", "Mitigation"]
    for col, h in enumerate(risk_headers, 1):
        cell = ws_risks.cell(row=1, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill

    row = 2
    if risk_matrix:
        for risk in risk_matrix.get("risks", []):
            ws_risks.cell(row=row, column=1, value=risk.get("id", ""))
            ws_risks.cell(row=row, column=2, value=risk.get("description", ""))
            ws_risks.cell(row=row, column=3, value=risk.get("category", ""))
            ws_risks.cell(row=row, column=4, value=risk.get("severity", 0))
            ws_risks.cell(row=row, column=5, value=risk.get("likelihood", 0))
            ws_risks.cell(row=row, column=6, value=risk.get("score", 0))
            ws_risks.cell(row=row, column=7, value=risk.get("mitigation", ""))
            row += 1

    ws_risks.column_dimensions["A"].width = 8
    ws_risks.column_dimensions["B"].width = 60
    ws_risks.column_dimensions["C"].width = 15
    ws_risks.column_dimensions["D"].width = 10
    ws_risks.column_dimensions["E"].width = 12
    ws_risks.column_dimensions["F"].width = 8
    ws_risks.column_dimensions["G"].width = 20

    # Sheet 5: Raw JSON
    ws_json = wb.create_sheet("Raw JSON")
    ws_json.cell(row=1, column=1, value="Complete Report Data (JSON)")
    ws_json.cell(row=1, column=1).font = header_font

    # Serialize report to JSON (handling non-serializable types)
    try:
        json_str = json.dumps(report, indent=2, default=str)
        # Split into rows (max 32767 chars per cell in Excel)
        lines = json_str.split('\n')
        for row_idx, line in enumerate(lines[:10000], 2):  # Limit rows
            ws_json.cell(row=row_idx, column=1, value=line[:32767])
    except Exception:
        ws_json.cell(row=2, column=1, value="[Error serializing report data]")

    ws_json.column_dimensions["A"].width = 150

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    entity_slug = (report.get("entity_name") or "report").lower().replace(" ", "_")[:40]
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="enhanced_intel_{entity_slug}_{report_id}.xlsx"'},
    )


@router.get("/{report_id}/powerpoint-detailed")
def download_detailed_pptx(report_id: int, db: Session = Depends(get_db)):
    """
    Download an enhanced intelligence report as a data-rich PowerPoint.

    Slides:
    1. Title slide with recommendation badge
    2. Executive summary with KPIs
    3. Investment thesis (if available)
    4. SWOT analysis (if available)
    5. Risk matrix (if available)
    6. Financial health (if available)
    7+ Content sections
    """
    try:
        from pptx import Presentation
        from pptx.util import Inches, Pt
        from pptx.dml.color import RGBColor as PptxRGB
        from pptx.enum.text import PP_ALIGN
    except ImportError:
        raise HTTPException(503, "python-pptx not installed")

    # Try enhanced report first
    report = None
    if _ENHANCED_AVAILABLE:
        report = get_enhanced_intelligence_report(db, report_id)
    if not report:
        report = get_intelligence_report(db, report_id)
    if not report:
        raise HTTPException(404, "Intelligence report not found")

    prs = Presentation()
    blank_layout = prs.slide_layouts[1]
    title_only_layout = prs.slide_layouts[5]

    # Slide 1: Title slide
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = "Enhanced Intelligence Report"
    entity_name = report.get("entity_name", "Unknown")
    ticker = report.get("ticker", "")
    subtitle = f"{entity_name}"
    if ticker:
        subtitle += f" ({ticker})"
    slide.placeholders[1].text = subtitle

    # Slide 2: Executive Summary with KPIs
    slide = prs.slides.add_slide(blank_layout)
    slide.shapes.title.text = "Executive Summary"
    body = slide.placeholders[1]
    tf = body.text_frame
    tf.word_wrap = True

    summary = report.get("summary", {})
    investment_thesis = report.get("investment_thesis")
    financial_health = report.get("financial_health")
    risk_matrix = report.get("risk_matrix")

    kpis = []
    if investment_thesis:
        kpis.append(f"Recommendation: {investment_thesis.get('recommendation', 'N/A')} ({investment_thesis.get('conviction', '')} conviction)")
    if financial_health:
        kpis.append(f"Financial Health Grade: {financial_health.get('grade', 'N/A')}")
    if risk_matrix:
        kpis.append(f"Overall Risk Score: {risk_matrix.get('overall_score', 'N/A')}/100")
    kpis.append(f"Data Confidence: {summary.get('kpi_data_confidence', 'N/A')}%")
    kpis.append(f"Court Risk: {summary.get('kpi_court_risk', 'N/A')}")
    kpis.append(f"Sanctions Status: {summary.get('kpi_sanctions_risk', 'N/A')}")

    for i, kpi in enumerate(kpis[:6]):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = kpi
        p.level = 0

    # Slide 3: Investment Thesis (if available)
    if investment_thesis:
        slide = prs.slides.add_slide(blank_layout)
        slide.shapes.title.text = "Investment Thesis"
        body = slide.placeholders[1]
        tf = body.text_frame
        tf.word_wrap = True

        thesis_points = [
            f"Recommendation: {investment_thesis.get('recommendation', 'N/A')}",
            f"Conviction Level: {investment_thesis.get('conviction', 'N/A')}",
        ]

        for bc in investment_thesis.get("bull_case", [])[:3]:
            thesis_points.append(f"Bull: {bc}" if isinstance(bc, str) else f"Bull: {bc.get('description', '')}")
        for bc in investment_thesis.get("bear_case", [])[:3]:
            thesis_points.append(f"Bear: {bc}" if isinstance(bc, str) else f"Bear: {bc.get('description', '')}")

        for i, point in enumerate(thesis_points[:8]):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.text = str(point)[:150]
            p.level = 0

    # Slide 4: SWOT Analysis (if available)
    swot = report.get("swot_analysis")
    if swot:
        slide = prs.slides.add_slide(blank_layout)
        slide.shapes.title.text = "SWOT Analysis"
        body = slide.placeholders[1]
        tf = body.text_frame
        tf.word_wrap = True

        swot_points = []
        for s in swot.get("strengths", [])[:2]:
            swot_points.append(f"S: {s.get('description', str(s))[:80]}" if isinstance(s, dict) else f"S: {str(s)[:80]}")
        for w in swot.get("weaknesses", [])[:2]:
            swot_points.append(f"W: {w.get('description', str(w))[:80]}" if isinstance(w, dict) else f"W: {str(w)[:80]}")
        for o in swot.get("opportunities", [])[:2]:
            swot_points.append(f"O: {o.get('description', str(o))[:80]}" if isinstance(o, dict) else f"O: {str(o)[:80]}")
        for t in swot.get("threats", [])[:2]:
            swot_points.append(f"T: {t.get('description', str(t))[:80]}" if isinstance(t, dict) else f"T: {str(t)[:80]}")

        for i, point in enumerate(swot_points[:8]):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.text = point
            p.level = 0

    # Slide 5: Risk Matrix (if available)
    if risk_matrix:
        slide = prs.slides.add_slide(blank_layout)
        slide.shapes.title.text = "Risk Assessment"
        body = slide.placeholders[1]
        tf = body.text_frame
        tf.word_wrap = True

        risk_points = [
            f"Overall Risk Score: {risk_matrix.get('overall_score', 'N/A')}/100",
            f"Critical Risks: {len(risk_matrix.get('critical_risks', []))}",
            f"High Risks: {len(risk_matrix.get('high_risks', []))}",
        ]

        for risk in risk_matrix.get("top_priority_risks", [])[:3]:
            risk_points.append(f"Priority: {risk.get('description', '')[:60]} (Score: {risk.get('score', 0)})")

        for i, point in enumerate(risk_points[:6]):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.text = point
            p.level = 0

    # Remaining slides: Content sections
    sections = report.get("sections", [])
    for section in sections[:10]:  # Limit to 10 sections
        section_name = section.get("name", section.get("title", "Section"))

        # Skip sections already covered
        if any(x in section_name for x in ["Executive", "Investment Thesis", "SWOT", "Risk"]):
            if any([investment_thesis, swot, risk_matrix]):
                continue

        slide = prs.slides.add_slide(blank_layout)
        slide.shapes.title.text = section_name[:50]
        body = slide.placeholders[1]
        tf = body.text_frame
        tf.word_wrap = True

        claims = section.get("claims", [])[:6]
        for i, claim in enumerate(claims):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            claim_text = claim.get("text", str(claim)) if isinstance(claim, dict) else str(claim)
            p.text = f"[{claim.get('confidence', '?') if isinstance(claim, dict) else 'INFO'}] {claim_text[:180]}"
            p.level = 0

    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    entity_slug = (report.get("entity_name") or "report").lower().replace(" ", "_")[:40]
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f'attachment; filename="enhanced_intel_{entity_slug}_{report_id}.pptx"'},
    )


@router.get("/{report_id}/pdf-beautiful")
def download_beautiful_pdf(report_id: int, db: Session = Depends(get_db)):
    """
    Download an enhanced intelligence report as a beautifully formatted PDF.

    Uses WeasyPrint to convert markdown to PDF with professional styling:
    - Clean typography with Inter font
    - Colored tables and headers
    - Proper page headers/footers
    - Print-optimized layout
    """
    if not _MARKDOWN_PDF_AVAILABLE:
        raise HTTPException(503, "Beautiful PDF export unavailable — install weasyprint and markdown")

    # Try enhanced report first, fall back to standard
    report = None
    if _ENHANCED_AVAILABLE:
        report = get_enhanced_intelligence_report(db, report_id)
    if not report:
        report = get_intelligence_report(db, report_id)
    if not report:
        raise HTTPException(404, "Intelligence report not found")

    try:
        # Generate markdown from report data
        markdown_content = generate_enhanced_markdown_report(report)

        # Convert to beautiful PDF
        pdf_bytes = convert_markdown_to_pdf(
            markdown_content,
            title=f"{report.get('entity_name', 'Entity')} — Enhanced Intelligence Report"
        )
    except Exception as exc:
        raise HTTPException(500, f"PDF generation failed: {exc}")

    entity_slug = (report.get("entity_name") or "report").lower().replace(" ", "_")[:40]
    filename = f"beautiful_intel_{entity_slug}_{report_id}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{report_id}/markdown")
def download_markdown(report_id: int, db: Session = Depends(get_db)):
    """
    Download an enhanced intelligence report as a markdown file.

    Useful for:
    - Custom formatting/editing
    - Integration with other tools
    - Archival purposes
    """
    if not _MARKDOWN_PDF_AVAILABLE:
        raise HTTPException(503, "Markdown export unavailable")

    # Try enhanced report first, fall back to standard
    report = None
    if _ENHANCED_AVAILABLE:
        report = get_enhanced_intelligence_report(db, report_id)
    if not report:
        report = get_intelligence_report(db, report_id)
    if not report:
        raise HTTPException(404, "Intelligence report not found")

    try:
        markdown_content = generate_enhanced_markdown_report(report)
    except Exception as exc:
        raise HTTPException(500, f"Markdown generation failed: {exc}")

    entity_slug = (report.get("entity_name") or "report").lower().replace(" ", "_")[:40]
    filename = f"intel_{entity_slug}_{report_id}.md"

    return StreamingResponse(
        io.BytesIO(markdown_content.encode('utf-8')),
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{report_id}/pdf-premium")
def download_premium_pdf(
    report_id: int,
    prepared_for: str = "Internal Analysis",
    db: Session = Depends(get_db)
):
    """
    Download a premium intelligence report as a professional PDF.

    Generates institutional-quality reports matching investment intelligence standards:
    - Dark header bar with classification markings
    - Gold accent colors for section headers
    - Executive callout boxes with key assessments
    - Table of contents with numbered sections
    - Risk matrix and watch items
    - Professional typography and dense content layout
    """
    if not _PREMIUM_PDF_AVAILABLE:
        raise HTTPException(503, "Premium PDF export unavailable — install weasyprint")

    # Try enhanced report first, fall back to standard
    report = None
    if _ENHANCED_AVAILABLE:
        report = get_enhanced_intelligence_report(db, report_id)
    if not report:
        report = get_intelligence_report(db, report_id)
    if not report:
        raise HTTPException(404, "Intelligence report not found")

    entity_name = report.get("entity_name", "Unknown Entity")
    ticker = report.get("ticker", "")

    try:
        pdf_bytes = convert_to_premium_pdf(
            entity_name=entity_name,
            ticker=ticker,
            report_data=report,
            prepared_for=prepared_for,
            organization="ENTERPRISE INTELLIGENCE PLATFORM"
        )
    except Exception as exc:
        raise HTTPException(500, f"Premium PDF generation failed: {exc}")

    entity_slug = entity_name.lower().replace(" ", "_")[:40]
    filename = f"premium_intel_{entity_slug}_{report_id}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ============================================================================
# FULL REPORT GENERATION ENDPOINTS (using scripts)
# ============================================================================

import subprocess
import os
from pathlib import Path
import uuid
import json
from datetime import datetime

# Track running jobs
_REPORT_JOBS: Dict[str, Dict[str, Any]] = {}


def _append_grounded_network_addendum(markdown_path: Path, addendum_text: str) -> None:
    marker = "## Grounded PayPal Network Addendum"
    if not addendum_text or not markdown_path.exists():
        return
    existing = markdown_path.read_text(encoding="utf-8")
    if marker in existing:
        return
    markdown_path.write_text(
        existing.rstrip() + "\n\n" + addendum_text.strip() + "\n",
        encoding="utf-8",
    )


@router.post("/generate-full-report")
def generate_full_report(
    ticker: str,
    peers: str = "",
    background_tasks: BackgroundTasks = None,
):
    """
    Generate a comprehensive intelligence report PDF for a ticker.

    This runs the full generate_intelligence_report.py script which produces:
    - 100+ page PDF report
    - JSON data file
    - Markdown source

    Returns a job_id to poll for status.
    """
    job_id = str(uuid.uuid4())[:8]

    _REPORT_JOBS[job_id] = {
        "status": "running",
        "type": "individual",
        "ticker": ticker,
        "started_at": datetime.now().isoformat(),
        "output_files": {},
    }

    def run_report():
        try:
            script_path = Path(__file__).parent.parent.parent / "scripts" / "generate_intelligence_report.py"
            cmd = ["python3", str(script_path), "--ticker", ticker]
            if peers:
                cmd.extend(["--peers", peers])

            result = subprocess.run(
                cmd,
                cwd=str(script_path.parent.parent),
                capture_output=True,
                text=True,
                timeout=1800,  # 30 min timeout
            )

            # Find generated files — check both possible output directories
            reports_dir = script_path.parent.parent.parent.parent / "reports"
            alt_reports_dir = script_path.parent.parent.parent / "reports"
            all_matches = []
            for rdir in [reports_dir, alt_reports_dir]:
                if rdir.exists():
                    all_matches.extend(rdir.glob(f"*{ticker.upper()}*"))
            latest_files = sorted(all_matches, key=lambda x: x.stat().st_mtime, reverse=True)

            output_files = {}
            for f in latest_files[:4]:
                if f.suffix == ".pdf":
                    output_files["pdf"] = str(f)
                elif f.suffix == ".md":
                    output_files["markdown"] = str(f)
                elif f.suffix == ".json":
                    output_files["json"] = str(f)

            _REPORT_JOBS[job_id]["status"] = "completed"
            _REPORT_JOBS[job_id]["output_files"] = output_files
            _REPORT_JOBS[job_id]["completed_at"] = datetime.now().isoformat()

        except Exception as e:
            _REPORT_JOBS[job_id]["status"] = "failed"
            _REPORT_JOBS[job_id]["error"] = str(e)

    if background_tasks:
        background_tasks.add_task(run_report)

    return {"job_id": job_id, "status": "started", "ticker": ticker}


@router.post("/generate-network-report")
def generate_network_report(
    network: str = "paypal_mafia",
    expanded: bool = True,
    background_tasks: BackgroundTasks = None,
):
    """
    Generate a network/group intelligence report PDF.

    Available networks: paypal_mafia (more can be added)

    Set expanded=True for 50-80 page deep analysis including:
    - Full financial profiles per person
    - All investments traced
    - Lobbying data per company
    - Government contracts per company

    Returns a job_id to poll for status.
    """
    job_id = str(uuid.uuid4())[:8]

    _REPORT_JOBS[job_id] = {
        "status": "running",
        "type": "network",
        "network": network,
        "expanded": expanded,
        "started_at": datetime.now().isoformat(),
        "output_files": {},
    }

    def run_report():
        try:
            scripts_dir = Path(__file__).parent.parent.parent / "scripts"
            cwd = str(scripts_dir.parent)

            if expanded:
                # Run the full pipeline: expand_v2 → supplement_a → supplement_b → merge_final
                # This produces the comprehensive styled report with charts and appendices
                pipeline = [
                    scripts_dir / "expand_network_report_v2.py",
                    scripts_dir / "supplement_a.py",
                    scripts_dir / "supplement_b.py",
                    scripts_dir / "merge_final.py",
                ]
                for script in pipeline:
                    if script.exists():
                        result = subprocess.run(
                            ["python3", str(script)],
                            cwd=cwd,
                            capture_output=True,
                            text=True,
                            timeout=1800,
                        )
                        # Log but don't fail on supplements (they enhance, not block)
                        if result.returncode != 0 and script.name == "expand_network_report_v2.py":
                            raise RuntimeError(f"{script.name} failed: {result.stderr[-500:]}")
            else:
                script_path = scripts_dir / "generate_network_report.py"
                cmd = ["python3", str(script_path), "--network", network]
                subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=3600)

            # Find generated files — check both possible output directories
            reports_dir = scripts_dir.parent.parent.parent / "reports"
            alt_reports_dir = scripts_dir.parent.parent / "reports"

            # Look for PayPal Mafia reports — prefer COMPLETE > FINAL > EXPANDED
            search_pattern = "PayPal_Mafia" if network == "paypal_mafia" else network

            all_matches = []
            for rdir in [reports_dir, alt_reports_dir]:
                if rdir.exists():
                    all_matches.extend([f for f in rdir.glob(f"*{search_pattern}*") if f.is_file()])

            latest_files = sorted(
                all_matches,
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )

            output_files = {}
            for f in latest_files:
                if f.suffix == ".pdf" and "pdf" not in output_files:
                    output_files["pdf"] = str(f)
                elif f.suffix == ".md" and "markdown" not in output_files:
                    output_files["markdown"] = str(f)
                elif f.suffix == ".json" and "json" not in output_files:
                    output_files["json"] = str(f)

            if network == "paypal_mafia" and output_files.get("markdown"):
                try:
                    addendum = build_paypal_mafia_report_addendum()
                    _append_grounded_network_addendum(
                        Path(output_files["markdown"]),
                        addendum.get("markdown", ""),
                    )
                    _REPORT_JOBS[job_id]["grounded_network_analysis"] = addendum.get("analysis")
                except Exception as addendum_error:
                    _REPORT_JOBS[job_id]["grounded_network_warning"] = str(addendum_error)

            _REPORT_JOBS[job_id]["status"] = "completed"
            _REPORT_JOBS[job_id]["output_files"] = output_files
            _REPORT_JOBS[job_id]["completed_at"] = datetime.now().isoformat()

        except Exception as e:
            _REPORT_JOBS[job_id]["status"] = "failed"
            _REPORT_JOBS[job_id]["error"] = str(e)

    if background_tasks:
        background_tasks.add_task(run_report)

    return {"job_id": job_id, "status": "started", "network": network, "expanded": expanded}


@router.get("/report-job/{job_id}")
def get_report_job_status(job_id: str):
    """
    Check status of a report generation job.
    Returns status and output file paths when complete.
    """
    if job_id not in _REPORT_JOBS:
        raise HTTPException(404, f"Job {job_id} not found")

    return _REPORT_JOBS[job_id]


@router.get("/report-job/{job_id}/download/{file_type}")
def download_report_file(job_id: str, file_type: str):
    """
    Download a generated report file.
    file_type: pdf, markdown, json
    """
    if job_id not in _REPORT_JOBS:
        raise HTTPException(404, f"Job {job_id} not found")

    job = _REPORT_JOBS[job_id]
    if job["status"] != "completed":
        raise HTTPException(400, f"Job not completed. Status: {job['status']}")

    if file_type not in job["output_files"]:
        raise HTTPException(404, f"File type {file_type} not available")

    file_path = Path(job["output_files"][file_type])
    if not file_path.exists():
        raise HTTPException(404, "File not found on disk")

    media_types = {
        "pdf": "application/pdf",
        "markdown": "text/markdown",
        "json": "application/json",
    }

    return StreamingResponse(
        open(file_path, "rb"),
        media_type=media_types.get(file_type, "application/octet-stream"),
        headers={"Content-Disposition": f'attachment; filename="{file_path.name}"'},
    )


# ============================================================================
# NARRATIVE EDIT COLLECTION (for AI fine-tuning)
# ============================================================================

from datetime import datetime, timezone
from pathlib import Path as PathLib
import json as json_lib

_NARRATIVE_EDITS_PATH = PathLib(__file__).parent.parent / "exports" / "narrative_edits.jsonl"


class NarrativeEditRequest(BaseModel):
    """Request to save a human edit to a report section."""
    section: str = Field(..., description="Section name (e.g., 'executive_summary', 'investment_thesis')")
    original: str = Field(..., description="Original AI-generated text")
    edited: str = Field(..., description="Human-edited text")
    entity_name: Optional[str] = Field(None, description="Entity name for context")
    edit_reason: Optional[str] = Field(None, description="Why the edit was made")


class NarrativeEditResponse(BaseModel):
    """Response after saving an edit."""
    status: str
    edit_id: str
    message: str


@router.post("/{report_id}/edit", response_model=NarrativeEditResponse)
async def save_narrative_edit(
    report_id: str,
    edit: NarrativeEditRequest,
):
    """
    Save a human edit to a report section for AI fine-tuning.

    Human edits are gold-standard training data for narrative generation.
    They capture the "preferred" output that the fine-tuned model should produce.

    The edit is logged to exports/narrative_edits.jsonl with:
    - report_id: Which report was edited
    - section: Which section (executive_summary, swot_analysis, etc.)
    - original: The AI-generated text
    - edited: The human-corrected text
    - timestamp: When the edit was made

    This endpoint enables the "Edit & Save" feature in the report UI.
    """
    import hashlib

    # Generate unique edit ID
    edit_hash = hashlib.md5(
        f"{report_id}:{edit.section}:{datetime.now(timezone.utc).isoformat()}".encode()
    ).hexdigest()[:12]

    log_entry = {
        "edit_id": edit_hash,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "report_id": report_id,
        "section": edit.section,
        "original": edit.original[:20000],  # Truncate very long text
        "edited": edit.edited[:20000],
        "entity_name": edit.entity_name,
        "edit_reason": edit.edit_reason,
        "is_human_edit": True,
        "original_length": len(edit.original),
        "edited_length": len(edit.edited),
        "change_ratio": round(len(edit.edited) / max(len(edit.original), 1), 4),
    }

    try:
        _NARRATIVE_EDITS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_NARRATIVE_EDITS_PATH, "a") as f:
            f.write(json_lib.dumps(log_entry) + "\n")

        return NarrativeEditResponse(
            status="saved",
            edit_id=edit_hash,
            message=f"Edit logged for fine-tuning (section: {edit.section})",
        )
    except Exception as exc:
        logger.error("Failed to save narrative edit: %s", exc)
        raise HTTPException(500, f"Failed to save edit: {str(exc)}")


@router.get("/training-stats")
async def get_training_stats():
    """
    Get statistics about collected training data.

    Returns counts of:
    - embedding_triplets: For embedding fine-tuning
    - rag_training_log: From RAG queries
    - narrative_training_log: From narrative generation
    - narrative_edits: From human corrections
    """
    exports_dir = PathLib(__file__).parent.parent / "exports"

    stats = {}

    files = [
        ("embedding_triplets", "embedding_triplets.jsonl"),
        ("rag_training_log", "rag_training_log.jsonl"),
        ("narrative_training_log", "narrative_training_log.jsonl"),
        ("narrative_edits", "narrative_edits.jsonl"),
    ]

    for name, filename in files:
        path = exports_dir / filename
        if path.exists():
            try:
                with open(path) as f:
                    count = sum(1 for _ in f)
                size_kb = path.stat().st_size / 1024
                stats[name] = {
                    "exists": True,
                    "entries": count,
                    "size_kb": round(size_kb, 2),
                }
            except Exception as exc:
                stats[name] = {"exists": True, "error": str(exc)}
        else:
            stats[name] = {"exists": False, "entries": 0}

    # Add summary
    total_entries = sum(s.get("entries", 0) for s in stats.values())
    stats["_summary"] = {
        "total_entries": total_entries,
        "ready_for_phase2": stats.get("embedding_triplets", {}).get("entries", 0) >= 1000,
        "ready_for_phase4": (
            stats.get("narrative_training_log", {}).get("entries", 0) +
            stats.get("narrative_edits", {}).get("entries", 0) * 3  # Edits count 3x
        ) >= 500,
    }

    return stats
