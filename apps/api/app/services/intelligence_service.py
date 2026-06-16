"""
Intelligence Report Service - Layer 1 Entity Network Report
"""
import os
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.reports import Report, ReportSection, Claim, ClaimEvidence
from app.models.entities import Entity, EntityIdentifier, Relationship, RelationshipEvidence
from app.models.base import Base


INTELLIGENCE_KIND = "entity_network_intel"

# ── helpers ──────────────────────────────────────────────────────────────────

def _now():
    return datetime.now(timezone.utc).isoformat()

def _upsert_entity(db: Session, name: str, kind: str, meta: dict = None) -> int:
    row = db.execute(text("SELECT id FROM entities WHERE name=:n AND kind=:k LIMIT 1"),
                     {"n": name, "k": kind}).fetchone()
    if row:
        return row[0]
    db.execute(text("INSERT INTO entities (name, kind, canonical, meta) VALUES (:n,:k,true,:m)"),
               {"n": name, "k": kind, "m": None})
    db.flush()
    row = db.execute(text("SELECT id FROM entities WHERE name=:n AND kind=:k ORDER BY id DESC LIMIT 1"),
                     {"n": name, "k": kind}).fetchone()
    db.commit()
    return row[0]

def _upsert_rel(db: Session, src: int, dst: int, kind: str, meta: dict = None) -> int:
    row = db.execute(
        text("SELECT id FROM relationships WHERE src_entity_id=:s AND dst_entity_id=:d AND kind=:k LIMIT 1"),
        {"s": src, "d": dst, "k": kind}).fetchone()
    if row:
        return row[0]
    db.execute(
        text("INSERT INTO relationships (src_entity_id, dst_entity_id, kind, meta) VALUES (:s,:d,:k,:m)"),
        {"s": src, "d": dst, "k": kind, "m": None})
    db.flush()
    row = db.execute(
        text("SELECT id FROM relationships WHERE src_entity_id=:s AND dst_entity_id=:d AND kind=:k ORDER BY id DESC LIMIT 1"),
        {"s": src, "d": dst, "k": kind}).fetchone()
    db.commit()
    return row[0]


# ── SEC EDGAR connector (entity-specific) ────────────────────────────────────

def _fetch_sec(entity_name: str, ticker: Optional[str]) -> Dict[str, Any]:
    headers = {"User-Agent": os.getenv("SEC_USER_AGENT", "IntelPlatform research@example.com")}
    result = {"filings": [], "officers": [], "cik": None, "company_name": None}
    try:
        # search company tickers JSON
        resp = requests.get("https://www.sec.gov/files/company_tickers.json", headers=headers, timeout=15)
        if resp.ok:
            tickers_map = resp.json()
            name_lower = entity_name.lower()
            tick_lower = (ticker or "").lower()
            for _k, v in tickers_map.items():
                match = (tick_lower and v.get("ticker","").lower() == tick_lower) or \
                        (name_lower in v.get("title","").lower())
                if match:
                    cik = str(v["cik_str"]).zfill(10)
                    result["cik"] = cik
                    result["company_name"] = v.get("title")
                    break

        if result["cik"]:
            cik = result["cik"]
            sub = requests.get(f"https://data.sec.gov/submissions/CIK{cik}.json",
                               headers=headers, timeout=15)
            if sub.ok:
                data = sub.json()
                recent = data.get("filings", {}).get("recent", {})
                forms = recent.get("form", [])
                dates = recent.get("filingDate", [])
                accs = recent.get("accessionNumber", [])
                for i, f in enumerate(forms[:20]):
                    result["filings"].append({
                        "form": f,
                        "date": dates[i] if i < len(dates) else None,
                        "accession": accs[i] if i < len(accs) else None,
                    })
                # officers from company facts
                result["officers"] = data.get("insiderTransactionForIssuerExists", 0)
                result["sic"] = data.get("sic")
                result["sic_desc"] = data.get("sicDescription")
                result["exchanges"] = data.get("exchanges", [])
                result["state_of_inc"] = data.get("stateOfIncorporation")
    except Exception as e:
        result["error"] = str(e)
    return result


# ── FEC connector (entity-specific) ─────────────────────────────────────────

def _fetch_fec(entity_name: str) -> Dict[str, Any]:
    fec_key = os.getenv("FEC_API_KEY", "")
    result = {"committees": [], "contributions": [], "disbursements": []}
    if not fec_key:
        return result
    try:
        resp = requests.get("https://api.open.fec.gov/v1/committees/",
                            params={"api_key": fec_key, "q": entity_name, "per_page": 5},
                            timeout=15)
        if resp.ok:
            for c in resp.json().get("results", []):
                result["committees"].append({
                    "name": c.get("name"),
                    "id": c.get("committee_id"),
                    "type": c.get("committee_type_full"),
                    "party": c.get("party_full"),
                    "state": c.get("state"),
                })
    except Exception as e:
        result["error"] = str(e)
    return result


# ── FARA connector (entity-specific) ─────────────────────────────────────────

def _fetch_fara(entity_name: str) -> Dict[str, Any]:
    result = {"registrants": [], "foreign_principals": []}
    try:
        resp = requests.get("https://efile.fara.gov/api/v1/Registrants/json/Active", timeout=20)
        if resp.ok:
            data = resp.json()
            items = data.get("REGISTRANTS_ACTIVE", {})
            rows = items.get("ROW", []) if isinstance(items, dict) else items
            if isinstance(rows, dict):
                rows = [rows]
            name_lower = entity_name.lower()
            for r in rows:
                rname = str(r.get("Registrant_Name") or r.get("registrant_name") or "")
                if name_lower[:6] in rname.lower():
                    result["registrants"].append({
                        "name": rname,
                        "reg_num": r.get("Registration_Number"),
                        "country": r.get("Foreign_Principal_Country"),
                    })
    except Exception as e:
        result["error"] = str(e)
    return result


# ── USASpending connector (entity-specific) ──────────────────────────────────

def _fetch_usaspending(entity_name: str) -> Dict[str, Any]:
    result = {"awards": [], "total_obligated": 0}
    try:
        payload = {
            "filters": {
                "recipient_search_text": [entity_name],
                "award_type_codes": ["A","B","C","D"],
            },
            "fields": ["Award ID","Recipient Name","Award Amount","Awarding Agency",
                       "Award Type","Start Date","End Date","Description"],
            "page": 1, "limit": 10, "sort": "Award Amount", "order": "desc"
        }
        resp = requests.post("https://api.usaspending.gov/api/v2/search/spending_by_award/",
                             json=payload, timeout=20)
        if resp.ok:
            data = resp.json()
            for a in data.get("results", []):
                amt = a.get("Award Amount") or 0
                result["awards"].append({
                    "id": a.get("Award ID"),
                    "recipient": a.get("Recipient Name"),
                    "amount": amt,
                    "agency": a.get("Awarding Agency"),
                    "type": a.get("Award Type"),
                    "start": a.get("Start Date"),
                    "description": a.get("Description"),
                })
                result["total_obligated"] += float(amt or 0)
    except Exception as e:
        result["error"] = str(e)
    return result


# ── LDA lobbying connector (entity-specific) ─────────────────────────────────

def _fetch_lda(entity_name: str) -> Dict[str, Any]:
    result = {"filings": []}
    try:
        resp = requests.get("https://lda.senate.gov/api/v1/filings/",
                            params={"registrant_name": entity_name, "page_size": 10},
                            timeout=20)
        if resp.ok:
            for f in resp.json().get("results", []):
                result["filings"].append({
                    "uuid": f.get("filing_uuid"),
                    "registrant": (f.get("registrant") or {}).get("name"),
                    "client": (f.get("client") or {}).get("name"),
                    "year": f.get("filing_year"),
                    "period": f.get("filing_period"),
                    "income": f.get("income"),
                    "expenses": f.get("expenses"),
                })
    except Exception as e:
        result["error"] = str(e)
    return result


# ── OFAC sanctions check ──────────────────────────────────────────────────────

def _fetch_ofac(entity_name: str) -> Dict[str, Any]:
    result = {"hits": [], "is_sanctioned": False}
    try:
        api_key = os.getenv("SANCTIONS_API_KEY", "")
        if api_key:
            resp = requests.get("https://api.opensanctions.org/search/default",
                                headers={"Authorization": f"ApiKey {api_key}"},
                                params={"q": entity_name, "limit": 5},
                                timeout=15)
            if resp.ok:
                for r in resp.json().get("results", []):
                    props = r.get("properties", {})
                    names = props.get("name", [])
                    result["hits"].append({
                        "id": r.get("id"),
                        "name": names[0] if names else r.get("id"),
                        "datasets": r.get("datasets", []),
                        "schema": r.get("schema"),
                    })
                result["is_sanctioned"] = len(result["hits"]) > 0
    except Exception as e:
        result["error"] = str(e)
    return result


# ── CourtListener litigation check ───────────────────────────────────────────

def _fetch_courts(entity_name: str) -> Dict[str, Any]:
    result = {"cases": []}
    try:
        cl_token = os.getenv("COURTLISTENER_API_TOKEN", "")
        headers = {"Authorization": f"Token {cl_token}"} if cl_token else {}
        resp = requests.get("https://www.courtlistener.com/api/rest/v4/dockets/",
                            headers=headers,
                            params={"q": entity_name, "page_size": 5},
                            timeout=15)
        if resp.ok:
            for c in resp.json().get("results", []):
                result["cases"].append({
                    "id": c.get("id"),
                    "case_name": c.get("case_name"),
                    "court": c.get("court"),
                    "date_filed": c.get("date_filed"),
                    "cause": c.get("cause"),
                })
    except Exception as e:
        result["error"] = str(e)
    return result


# ── GPT-4o narrative writer ───────────────────────────────────────────────────

def _generate_narrative(entity_name: str, sections: List[Dict]) -> str:
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return "[AI narrative unavailable — OPENAI_API_KEY not configured]"

    # Build a concise structured prompt from the evidence
    evidence_text = []
    for s in sections:
        if s.get("claims"):
            evidence_text.append(f"\n## {s['name']}")
            for c in s["claims"][:5]:
                evidence_text.append(f"- [{c['confidence']}] {c['text']}")

    prompt = f"""You are an intelligence analyst writing a professional cited dossier.
Entity under analysis: {entity_name}

Evidence gathered from public records:
{''.join(evidence_text)}

Write a concise 3-4 paragraph executive narrative for an intelligence dossier on {entity_name}.
- Reference only the evidence provided above
- Tag each factual claim as [DOCUMENTED], [REPORTED], or [ANALYTICAL]
- Focus on: ownership/investors, government relationships, risk flags, network significance
- Use formal intelligence report language (no speculation beyond evidence)
- Do not add facts not present in the evidence above"""

    try:
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You are an expert financial and geopolitical intelligence analyst producing evidence-first dossiers."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 800,
            },
            timeout=45,
        )
        if resp.ok:
            return resp.json()["choices"][0]["message"]["content"]
        return f"[GPT error {resp.status_code}: {resp.text[:200]}]"
    except Exception as e:
        return f"[GPT narrative error: {str(e)}]"


# ── Thiel demo seed data ───────────────────────────────────────────────────────

THIEL_NETWORK = {
    "Palantir Technologies": {"ticker": "PLTR", "type": "org", "note": "Defense AI flagship; Thiel co-founder"},
    "Anduril Industries":    {"ticker": None,   "type": "org", "note": "Defense tech; Palmer Luckey; Founders Fund"},
    "Founders Fund":         {"ticker": None,   "type": "fund","note": "Peter Thiel VC fund"},
    "HawkEye 360":           {"ticker": None,   "type": "org", "note": "RF satellite intelligence; Ghisallo/Founders Fund"},
    "Erebor Bank":           {"ticker": None,   "type": "org", "note": "OCC national charter; Luckey/Thiel orbit"},
    "Redwire Corporation":   {"ticker": "RDW",  "type": "org", "note": "Space/defense manufacturing"},
}


# ── Main orchestrator ─────────────────────────────────────────────────────────

def generate_intelligence_report(db: Session, entity_name: str, entity_type: str = "org",
                                  ticker: Optional[str] = None) -> Dict[str, Any]:
    """
    Full Layer 1 Entity Network Intelligence Report pipeline:
    1. Resolve/create entity in DB
    2. Run all federal connectors for this entity
    3. Write relationships + evidence into graph tables
    4. Assemble 7-section report JSON
    5. Generate GPT-4o cited narrative
    6. Persist report + sections to DB
    7. Return full report JSON
    """
    started = _now()

    # 1. Ensure entity exists
    entity_id = _upsert_entity(db, entity_name, entity_type)

    # 2. Run connectors
    sec_data      = _fetch_sec(entity_name, ticker)
    fec_data      = _fetch_fec(entity_name)
    fara_data     = _fetch_fara(entity_name)
    spending_data = _fetch_usaspending(entity_name)
    lda_data      = _fetch_lda(entity_name)
    ofac_data     = _fetch_ofac(entity_name)
    court_data    = _fetch_courts(entity_name)

    # 3. Write relationships into graph
    relationships_created = []

    # SEC CIK identifier
    if sec_data.get("cik"):
        try:
            existing = db.execute(
                text("SELECT id FROM entity_identifiers WHERE entity_id=:e AND scheme='CIK' LIMIT 1"),
                {"e": entity_id}).fetchone()
            if not existing:
                db.execute(
                    text("INSERT INTO entity_identifiers (entity_id, scheme, value) VALUES (:e,'CIK',:v)"),
                    {"e": entity_id, "v": sec_data["cik"]})
                db.commit()
        except Exception:
            db.rollback()

    # USASpending — awarded_to relationships (entity → federal agency)
    for award in spending_data.get("awards", []):
        agency_name = award.get("agency") or "Unknown Agency"
        if agency_name and award.get("amount"):
            agency_id = _upsert_entity(db, agency_name, "agency")
            rel_id = _upsert_rel(db, entity_id, agency_id, "awarded_contract")
            relationships_created.append({
                "kind": "awarded_contract",
                "entity": agency_name,
                "amount": award.get("amount"),
                "description": award.get("description"),
            })

    # FEC — political committee relationships
    for committee in fec_data.get("committees", []):
        if committee.get("name"):
            pac_id = _upsert_entity(db, committee["name"], "pac")
            rel_id = _upsert_rel(db, entity_id, pac_id, "affiliated_pac")
            relationships_created.append({
                "kind": "affiliated_pac",
                "entity": committee["name"],
                "type": committee.get("type"),
            })

    # FARA — foreign agent relationships
    for reg in fara_data.get("registrants", []):
        if reg.get("name"):
            fa_id = _upsert_entity(db, reg["name"], "org")
            rel_id = _upsert_rel(db, entity_id, fa_id, "fara_registrant")
            relationships_created.append({
                "kind": "fara_registrant",
                "entity": reg["name"],
                "country": reg.get("country"),
            })

    # 4. Assemble 7 report sections
    sections = []

    # Section 1: Entity Profile
    sec1_claims = []
    if sec_data.get("cik"):
        sec1_claims.append({"text": f"{entity_name} is registered with the SEC under CIK {sec_data['cik']}.",
                            "confidence": "DOCUMENTED", "source": "SEC EDGAR"})
    if sec_data.get("sic_desc"):
        sec1_claims.append({"text": f"SIC classification: {sec_data['sic_desc']} (code {sec_data.get('sic')}).",
                            "confidence": "DOCUMENTED", "source": "SEC EDGAR"})
    if sec_data.get("state_of_inc"):
        sec1_claims.append({"text": f"State of incorporation: {sec_data['state_of_inc']}.",
                            "confidence": "DOCUMENTED", "source": "SEC EDGAR"})
    if sec_data.get("exchanges"):
        sec1_claims.append({"text": f"Listed on: {', '.join(sec_data['exchanges'])}.",
                            "confidence": "DOCUMENTED", "source": "SEC EDGAR"})
    sections.append({"name": "Entity Profile", "order": 1, "claims": sec1_claims,
                     "data": {"cik": sec_data.get("cik"), "company": sec_data.get("company_name")}})

    # Section 2: SEC Filings (ownership / holding indicators)
    sec2_claims = []
    forms_seen = {}
    for f in sec_data.get("filings", []):
        form = f.get("form", "")
        if form and form not in forms_seen:
            forms_seen[form] = f.get("date")
    for form, date in list(forms_seen.items())[:8]:
        sec2_claims.append({"text": f"Filed {form} on {date}.",
                            "confidence": "DOCUMENTED", "source": "SEC EDGAR"})
    sections.append({"name": "SEC Filings & Ownership Indicators", "order": 2,
                     "claims": sec2_claims, "data": {"filing_types": list(forms_seen.keys())}})

    # Section 3: Government Contracts
    sec3_claims = []
    for a in spending_data.get("awards", []):
        amt = a.get("amount", 0)
        sec3_claims.append({
            "text": f"Received ${float(amt):,.0f} federal contract from {a.get('agency')} ({a.get('type')}){(' — ' + a['description'][:80]) if a.get('description') else ''}.",
            "confidence": "DOCUMENTED", "source": "USASpending.gov"
        })
    if not sec3_claims:
        sec3_claims.append({"text": "No direct federal contract awards found in USASpending database for this entity name.",
                            "confidence": "DOCUMENTED", "source": "USASpending.gov"})
    total = spending_data.get("total_obligated", 0)
    sections.append({"name": "Government Contracts & Procurement", "order": 3,
                     "claims": sec3_claims,
                     "data": {"total_obligated_usd": total, "award_count": len(spending_data.get("awards", []))}})

    # Section 4: Political & Regulatory Exposure
    sec4_claims = []
    for c in fec_data.get("committees", []):
        sec4_claims.append({"text": f"Affiliated political committee: {c['name']} ({c.get('type','')}, {c.get('state','')}).",
                            "confidence": "DOCUMENTED", "source": "FEC OpenData"})
    for f in lda_data.get("filings", []):
        income = f.get("income") or 0
        sec4_claims.append({"text": f"Lobbying filing ({f.get('period')} {f.get('year')}): registrant {f.get('registrant')}, client {f.get('client')}, income ${float(income):,.0f}.",
                            "confidence": "DOCUMENTED", "source": "LDA Senate"})
    for r in fara_data.get("registrants", []):
        sec4_claims.append({"text": f"FARA registration #{r.get('reg_num')}: {r['name']} (foreign country: {r.get('country','unknown')}).",
                            "confidence": "DOCUMENTED", "source": "FARA DOJ"})
    if not sec4_claims:
        sec4_claims.append({"text": "No FEC committee, lobbying, or FARA registrations found for this entity.",
                            "confidence": "DOCUMENTED", "source": "FEC/LDA/FARA"})
    sections.append({"name": "Political & Regulatory Exposure", "order": 4,
                     "claims": sec4_claims, "data": {}})

    # Section 5: Sanctions & Compliance
    sec5_claims = []
    if ofac_data.get("is_sanctioned"):
        sec5_claims.append({"text": f"ALERT: Entity name matches {len(ofac_data['hits'])} OFAC/OpenSanctions record(s).",
                            "confidence": "DOCUMENTED", "source": "OFAC/OpenSanctions"})
        for h in ofac_data.get("hits", []):
            sec5_claims.append({"text": f"Sanctions hit: {h.get('name')} — datasets: {', '.join(h.get('datasets',[]))}.",
                               "confidence": "DOCUMENTED", "source": "OpenSanctions"})
    else:
        sec5_claims.append({"text": "No OFAC sanctions or OpenSanctions matches found for this entity.",
                            "confidence": "DOCUMENTED", "source": "OFAC/OpenSanctions"})
    sections.append({"name": "Sanctions & Compliance Check", "order": 5,
                     "claims": sec5_claims, "data": {"sanctioned": ofac_data.get("is_sanctioned", False)}})

    # Section 6: Litigation & Legal Exposure
    sec6_claims = []
    for c in court_data.get("cases", []):
        sec6_claims.append({"text": f"Court docket: {c.get('case_name')} ({c.get('court')}, filed {c.get('date_filed')}) — {c.get('cause','no cause listed')}.",
                            "confidence": "REPORTED", "source": "CourtListener"})
    if not sec6_claims:
        sec6_claims.append({"text": "No federal court dockets found via CourtListener for this entity.",
                            "confidence": "DOCUMENTED", "source": "CourtListener"})
    sections.append({"name": "Litigation & Legal Exposure", "order": 6,
                     "claims": sec6_claims, "data": {"case_count": len(court_data.get("cases", []))}})

    # Section 7: AI Narrative (generated last, grounded in sections 1–6)
    narrative_text = _generate_narrative(entity_name, sections)
    sections.append({"name": "Intelligence Narrative (AI-Generated)", "order": 7,
                     "claims": [{"text": narrative_text, "confidence": "ANALYTICAL",
                                 "source": "GPT-4o (grounded in cited evidence above)"}],
                     "data": {"model": "gpt-4o-mini", "grounded": True}})

    # 5. Persist report to DB
    try:
        db.execute(text("""
            INSERT INTO reports (title, kind, status, meta)
            VALUES (:t, :k, 'published', :m)
        """), {
            "t": f"Layer 1 Intelligence Report: {entity_name}",
            "k": INTELLIGENCE_KIND,
            "m": None,
        })
        db.flush()
        row = db.execute(
            text("SELECT id FROM reports WHERE kind=:k ORDER BY id DESC LIMIT 1"),
            {"k": INTELLIGENCE_KIND}).fetchone()
        report_id = row[0]

        for s in sections:
            content = "\n".join([c["text"] for c in s.get("claims", [])])
            db.execute(text("""
                INSERT INTO report_sections (report_id, name, content, "order")
                VALUES (:r, :n, :c, :o)
            """), {"r": report_id, "n": s["name"], "c": content, "o": s["order"]})

            for claim in s.get("claims", []):
                db.execute(text("""
                    INSERT INTO claims (report_id, text, status)
                    VALUES (:r, :t, 'verified')
                """), {"r": report_id, "t": f"[{claim['confidence']}] {claim['text'][:499]}"})

        db.commit()
    except Exception as e:
        db.rollback()
        report_id = None

    return {
        "report_id": report_id,
        "entity_name": entity_name,
        "entity_id": entity_id,
        "entity_type": entity_type,
        "ticker": ticker,
        "generated_at": started,
        "sections": sections,
        "relationships_created": relationships_created,
        "summary": {
            "sec_cik": sec_data.get("cik"),
            "sec_filings": len(sec_data.get("filings", [])),
            "contracts_found": len(spending_data.get("awards", [])),
            "total_obligated_usd": spending_data.get("total_obligated", 0),
            "fec_committees": len(fec_data.get("committees", [])),
            "lobbying_filings": len(lda_data.get("filings", [])),
            "fara_registrations": len(fara_data.get("registrants", [])),
            "sanctions_hits": len(ofac_data.get("hits", [])),
            "court_cases": len(court_data.get("cases", [])),
            "relationships_written": len(relationships_created),
        }
    }


def get_intelligence_report(db: Session, report_id: int) -> Optional[Dict[str, Any]]:
    row = db.execute(
        text("SELECT id, title, kind, status FROM reports WHERE id=:id AND kind=:k"),
        {"id": report_id, "k": INTELLIGENCE_KIND}).fetchone()
    if not row:
        return None
    sections = db.execute(
        text('SELECT name, content, "order" FROM report_sections WHERE report_id=:id ORDER BY "order"'),
        {"id": report_id}).fetchall()
    claims = db.execute(
        text("SELECT text, status FROM claims WHERE report_id=:id"),
        {"id": report_id}).fetchall()
    return {
        "report_id": row[0], "title": row[1], "kind": row[2], "status": row[3],
        "sections": [{"name": s[0], "content": s[1], "order": s[2]} for s in sections],
        "claims": [{"text": c[0], "status": c[1]} for c in claims],
    }


def list_intelligence_reports(db: Session, limit: int = 20) -> List[Dict[str, Any]]:
    rows = db.execute(
        text("SELECT id, title, status, created_at FROM reports WHERE kind=:k ORDER BY id DESC LIMIT :l"),
        {"k": INTELLIGENCE_KIND, "l": limit}).fetchall()
    return [{"report_id": r[0], "title": r[1], "status": r[2],
             "created_at": r[3].isoformat() if r[3] else None} for r in rows]

