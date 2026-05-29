from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.base import Base
from app.models.models import Organization, Workspace, User, Project, Case
from app.models.entities import (
    Entity,
    EntityAlias,
    EntityIdentifier,
    Relationship,
    RelationshipEvidence,
)
from app.models.evidence import RawDocument, EvidenceRef
from app.models.reports import Report, ReportSection, EvidenceBundle, Claim, ClaimEvidence
from app.models.monitor import (
    Watchlist,
    WatchlistItem,
    Portfolio,
    Position,
    AlertRule,
    DeliveryChannel,
)

router = APIRouter(prefix="/demo")


def _first_or_create(db: Session, model, defaults=None, **filters):
    row = db.query(model).filter_by(**filters).first()
    if row:
        return row
    payload = dict(filters)
    if defaults:
        payload.update(defaults)
    row = model(**payload)
    db.add(row)
    db.flush()
    return row


@router.post("/seed")
def seed_demo(db: Session = Depends(get_db)):
    """Seed a realistic demo dataset for local UI testing.

    Idempotent: calling multiple times will reuse known records by natural keys.
    """
    Base.metadata.create_all(bind=db.get_bind())

    org = _first_or_create(db, Organization, name="Demo Capital")
    ws = _first_or_create(db, Workspace, org_id=org.id, name="Equity Intelligence")
    user = _first_or_create(
        db,
        User,
        email="analyst@democapital.test",
        defaults={"name": "Demo Analyst", "password_hash": "demo-seeded"},
    )
    proj = _first_or_create(db, Project, workspace_id=ws.id, name="AAPL Intelligence Case")
    case = _first_or_create(
        db, Case, workspace_id=ws.id, title="Government exposure and catalyst review"
    )

    aapl = _first_or_create(
        db,
        Entity,
        kind="org",
        name="Apple Inc.",
        defaults={"meta": {"ticker": "AAPL", "sector": "Technology"}},
    )
    msft = _first_or_create(
        db,
        Entity,
        kind="org",
        name="Microsoft Corporation",
        defaults={"meta": {"ticker": "MSFT", "sector": "Technology"}},
    )
    dod = _first_or_create(db, Entity, kind="agency", name="U.S. Department of Defense")
    tim = _first_or_create(db, Entity, kind="person", name="Tim Cook")
    blacklist = _first_or_create(
        db, Entity, kind="case", name="OFAC Screening Watch Event"
    )

    _first_or_create(db, EntityAlias, entity_id=aapl.id, alias="Apple")
    _first_or_create(db, EntityAlias, entity_id=msft.id, alias="Microsoft")
    _first_or_create(db, EntityIdentifier, entity_id=aapl.id, scheme="CIK", value="0000320193")
    _first_or_create(db, EntityIdentifier, entity_id=msft.id, scheme="CIK", value="0000789019")
    _first_or_create(db, EntityIdentifier, entity_id=dod.id, scheme="AGENCY", value="DOD")

    rel_officer = _first_or_create(
        db, Relationship, src_entity_id=tim.id, dst_entity_id=aapl.id, kind="officer_of"
    )
    rel_peer = _first_or_create(
        db, Relationship, src_entity_id=aapl.id, dst_entity_id=msft.id, kind="peer_company"
    )
    rel_contract = _first_or_create(
        db, Relationship, src_entity_id=dod.id, dst_entity_id=aapl.id, kind="awarded_to"
    )
    rel_risk = _first_or_create(
        db, Relationship, src_entity_id=aapl.id, dst_entity_id=blacklist.id, kind="mentioned_in"
    )

    raw_sec = _first_or_create(
        db,
        RawDocument,
        sha256="demo-sec-aapl-10k",
        defaults={
            "content_type": "application/json",
            "size_bytes": 1024,
            "storage_path": "demo://sec/aapl-10k-2023.json",
            "source_url": "https://www.sec.gov/ixviewer/ix.html",
            "source_native_id": "0000320193-23-000105",
            "uploader_user_id": user.id,
            "meta": {"source": "sec", "form": "10-K"},
        },
    )
    raw_award = _first_or_create(
        db,
        RawDocument,
        sha256="demo-usaspending-aapl-award",
        defaults={
            "content_type": "application/json",
            "size_bytes": 840,
            "storage_path": "demo://usaspending/aapl-award.json",
            "source_url": "https://api.usaspending.gov/",
            "source_native_id": "AWD-DEMO-1001",
            "uploader_user_id": user.id,
            "meta": {"source": "usaspending"},
        },
    )

    ref_sec = _first_or_create(
        db,
        EvidenceRef,
        raw_document_id=raw_sec.id,
        excerpt="Apple reported revenue growth with services expansion in FY2023.",
        defaults={"workspace_id": ws.id, "project_id": proj.id, "case_id": case.id},
    )
    ref_award = _first_or_create(
        db,
        EvidenceRef,
        raw_document_id=raw_award.id,
        excerpt="Award record shows recurring procurement relationship with a federal buyer.",
        defaults={"workspace_id": ws.id, "project_id": proj.id, "case_id": case.id},
    )

    _first_or_create(db, RelationshipEvidence, relationship_id=rel_contract.id, evidence_ref_id=ref_award.id)
    _first_or_create(db, RelationshipEvidence, relationship_id=rel_peer.id, evidence_ref_id=ref_sec.id)

    report = _first_or_create(
        db,
        Report,
        title="Apple Intelligence Snapshot (Demo)",
        kind="stock_analysis",
        defaults={"status": "in_review"},
    )
    sec_overview = _first_or_create(
        db,
        ReportSection,
        report_id=report.id,
        name="Executive Summary",
        defaults={
            "order": 1,
            "content": (
                "Apple remains financially strong, with evidence-backed signals across "
                "market, filings, and government exposure."
            ),
        },
    )
    _first_or_create(
        db,
        ReportSection,
        report_id=report.id,
        name="Government Exposure",
        defaults={
            "order": 2,
            "content": "Federal procurement references indicate measurable public-sector exposure.",
        },
    )
    bundle = _first_or_create(
        db,
        EvidenceBundle,
        report_id=report.id,
        name="Demo Bundle A",
        defaults={"items": [ref_sec.id, ref_award.id]},
    )
    claim = _first_or_create(
        db,
        Claim,
        report_id=report.id,
        text="Apple has trackable government procurement exposure based on public award records.",
        defaults={"status": "verified"},
    )
    _first_or_create(
        db,
        ClaimEvidence,
        claim_id=claim.id,
        evidence_ref_id=ref_award.id,
        defaults={"weight": 2},
    )

    watch = _first_or_create(db, Watchlist, name="MegaCap + Policy Watch")
    _first_or_create(
        db,
        WatchlistItem,
        watchlist_id=watch.id,
        ticker="AAPL",
        defaults={"entity_id": aapl.id, "notes": "Track filings + procurement + sanctions mentions"},
    )
    _first_or_create(
        db,
        WatchlistItem,
        watchlist_id=watch.id,
        ticker="MSFT",
        defaults={"entity_id": msft.id},
    )

    portfolio = _first_or_create(
        db, Portfolio, name="Demo Growth Portfolio", defaults={"base_ccy": "USD"}
    )
    _first_or_create(
        db,
        Position,
        portfolio_id=portfolio.id,
        ticker="AAPL",
        defaults={"entity_id": aapl.id, "qty": 120, "cost_basis": 182.5},
    )
    _first_or_create(
        db,
        Position,
        portfolio_id=portfolio.id,
        ticker="MSFT",
        defaults={"entity_id": msft.id, "qty": 85, "cost_basis": 410.0},
    )

    rule = _first_or_create(
        db,
        AlertRule,
        name="AAPL demo price move",
        kind="price_move",
        defaults={"params": {"ticker": "AAPL", "pct": 4}, "watchlist_id": watch.id},
    )
    _first_or_create(
        db,
        DeliveryChannel,
        rule_id=rule.id,
        kind="inapp",
        defaults={"target": "demo-inapp"},
    )

    db.commit()
    return {
        "ok": True,
        "message": "Demo data seeded",
        "ids": {
            "workspace_id": ws.id,
            "project_id": proj.id,
            "case_id": case.id,
            "entity_ids": {
                "apple": aapl.id,
                "microsoft": msft.id,
                "dod": dod.id,
                "tim_cook": tim.id,
            },
            "watchlist_id": watch.id,
            "portfolio_id": portfolio.id,
            "report_id": report.id,
            "bundle_id": bundle.id,
            "section_id": sec_overview.id,
        },
        "quick_checks": {
            "search": f"/search?q=apple",
            "entity_profile": f"/search/entities/{aapl.id}",
            "graph_export": f"/graph/export?entity_id={aapl.id}&depth=2",
            "portfolio_exposure": f"/monitor/portfolios/{portfolio.id}/exposure",
            "report": f"/reports/{report.id}",
        },
    }

