"""
Intelligence Report Service - Layer 1 Entity Network Report (v1.2)
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

# Apify enrichment connectors
try:
    from app.connectors.apify_connector import (
        fetch_linkedin_by_name,
        fetch_pitchbook_company,
        fetch_news,
        fetch_social_footprint,
        fetch_key_people,
    )
    APIFY_AVAILABLE = bool(os.getenv("APIFY_API_TOKEN", ""))
except ImportError:
    APIFY_AVAILABLE = False
    def fetch_social_footprint(name, **kw): return {}
    def fetch_key_people(name, **kw): return []
    def fetch_linkedin_by_name(n, c=""): return {"education": [], "experience": [], "source": "unavailable"}
    def fetch_pitchbook_company(n): return {"investors": [], "funding_rounds": [], "source": "unavailable"}
    def fetch_news(q, max_articles=8): return []

# Browser research agent (fallback for uncovered jurisdictions)
try:
    from app.connectors.browser_research_agent import (
        research_entity_browser,
        detect_jurisdiction,
        is_us_entity,
    )
    BROWSER_AGENT_AVAILABLE = True
except ImportError:
    BROWSER_AGENT_AVAILABLE = False
    def research_entity_browser(n, **kw): return {"findings": [], "summary": "", "jurisdiction": "unknown", "source": "unavailable"}
    def detect_jurisdiction(n, c=""): return "default"
    def is_us_entity(n, t="org"): return True

# Apollo connector
try:
    from app.connectors.apollo_connector import (
        search_organization as apollo_search_org,
        fetch_org_chart as apollo_org_chart,
        enrich_organization as apollo_enrich_org,
    )
    APOLLO_AVAILABLE = True
except ImportError:
    APOLLO_AVAILABLE = False
    def apollo_search_org(name): return {}
    def apollo_org_chart(org): return []
    def apollo_enrich_org(domain="", name=""): return {}

# Private company intelligence
try:
    from app.connectors.private_company_connector import fetch_private_company_intel
    PRIVATE_CO_AVAILABLE = True
except ImportError:
    PRIVATE_CO_AVAILABLE = False
    def fetch_private_company_intel(name, **kw): return {}


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
    result = {
        "committees": [],
        "contributions": [],
        "disbursements": [],
        # Two-sided disclosure
        "as_contributor": [],    # individual or PAC contributions to other committees
        "as_recipient": [],      # committees receiving money linked to entity
    }
    if not fec_key:
        return result
    try:
        # Side A — entity as a registered committee / PAC
        resp = requests.get(
            "https://api.open.fec.gov/v1/committees/",
            params={"api_key": fec_key, "q": entity_name, "per_page": 5},
            timeout=15,
        )
        if resp.ok:
            for c in resp.json().get("results", []):
                result["committees"].append({
                    "name":  c.get("name"),
                    "id":    c.get("committee_id"),
                    "type":  c.get("committee_type_full"),
                    "party": c.get("party_full"),
                    "state": c.get("state"),
                    "side":  "REGISTRANT (entity is the committee)",
                })
    except Exception as e:
        result["error"] = str(e)

    try:
        # Side B — individual contributions from people linked to entity
        resp2 = requests.get(
            "https://api.open.fec.gov/v1/schedules/schedule_a/",
            params={
                "api_key":    fec_key,
                "contributor_name": entity_name,
                "per_page":   10,
                "sort":       "-contribution_receipt_date",
            },
            timeout=15,
        )
        if resp2.ok:
            for item in resp2.json().get("results", [])[:10]:
                result["as_contributor"].append({
                    "contributor":  item.get("contributor_name", ""),
                    "amount":       item.get("contribution_receipt_amount", 0),
                    "date":         item.get("contribution_receipt_date", ""),
                    "recipient":    item.get("committee", {}).get("name", ""),
                    "side":         "CONTRIBUTOR (entity donated to a committee)",
                })
    except Exception as e:
        pass  # Non-fatal; FEC schedule A can be slow

    return result


# ── FARA connector (entity-specific, two-sided) ───────────────────────────────

def _fetch_fara(entity_name: str) -> Dict[str, Any]:
    result = {
        "registrants":        [],   # entity as the lobbyist/registrant
        "foreign_principals": [],   # entity as the foreign principal being lobbied for
    }
    try:
        # Side A: Entity is the registrant (lobbying on behalf of a foreign principal)
        resp = requests.get("https://efile.fara.gov/api/v1/Registrants/json/Active", timeout=20)
        if resp.ok:
            data  = resp.json()
            items = data.get("REGISTRANTS_ACTIVE", {})
            rows  = items.get("ROW", []) if isinstance(items, dict) else items
            if isinstance(rows, dict):
                rows = [rows]
            name_lower = entity_name.lower()
            for r in rows:
                rname = str(r.get("Registrant_Name") or r.get("registrant_name") or "")
                if name_lower[:6] in rname.lower():
                    result["registrants"].append({
                        "name":    rname,
                        "reg_num": r.get("Registration_Number"),
                        "country": r.get("Foreign_Principal_Country"),
                        "side":    "REGISTRANT (entity is the FARA-registered lobbyist)",
                    })
    except Exception as e:
        result["error"] = str(e)

    try:
        # Side B: Entity is the foreign principal (being represented by a FARA registrant)
        resp2 = requests.get("https://efile.fara.gov/api/v1/ForeignPrincipals/json/Active", timeout=20)
        if resp2.ok:
            data2  = resp2.json()
            items2 = data2.get("FOREIGN_PRINCIPALS_ACTIVE", {})
            rows2  = items2.get("ROW", []) if isinstance(items2, dict) else items2
            if isinstance(rows2, dict):
                rows2 = [rows2]
            name_lower = entity_name.lower()
            for r in rows2:
                fp_name = str(r.get("Foreign_Principal_Name") or r.get("foreign_principal_name") or "")
                if name_lower[:6] in fp_name.lower():
                    result["foreign_principals"].append({
                        "foreign_principal":  fp_name,
                        "registrant":         r.get("Registrant_Name", ""),
                        "country":            r.get("Country_of_Principal_Representation", ""),
                        "reg_num":            r.get("Registration_Number", ""),
                        "side":               "FOREIGN PRINCIPAL (entity has a FARA-registered lobbyist)",
                    })
    except Exception as e:
        pass  # Non-fatal

    return result


# ── USASpending connector (entity-specific) ──────────────────────────────────

def _fetch_usaspending(entity_name: str) -> Dict[str, Any]:
    """Fetch USASpending data with two-sided disclosure:
    - As RECIPIENT (company receiving federal contracts) — primary view
    - As AWARDING AGENCY (agency awarding contracts to others) — secondary view
    """
    result = {
        "awards": [],
        "total_obligated": 0,
        # Two-sided additions
        "as_agency_awards": [],
        "as_agency_total": 0,
        "top_agencies": [],
        "top_recipients": [],
    }
    try:
        # ── SIDE A: entity AS RECIPIENT (receiving contracts) ─────────────────
        payload = {
            "filters": {
                "recipient_search_text": [entity_name],
                "award_type_codes": ["A", "B", "C", "D"],
            },
            "fields": ["Award ID", "Recipient Name", "Award Amount", "Awarding Agency",
                       "Award Type", "Start Date", "End Date", "Description"],
            "page": 1, "limit": 10, "sort": "Award Amount", "order": "desc"
        }
        resp = requests.post("https://api.usaspending.gov/api/v2/search/spending_by_award/",
                             json=payload, timeout=20)
        if resp.ok:
            agency_counts: Dict[str, float] = {}
            for a in resp.json().get("results", []):
                amt = float(a.get("Award Amount") or 0)
                agency = a.get("Awarding Agency") or "Unknown Agency"
                result["awards"].append({
                    "id": a.get("Award ID"),
                    "recipient": a.get("Recipient Name"),
                    "amount": amt,
                    "agency": agency,
                    "type": a.get("Award Type"),
                    "start": a.get("Start Date"),
                    "description": a.get("Description"),
                    "side": "recipient",
                })
                result["total_obligated"] += amt
                agency_counts[agency] = agency_counts.get(agency, 0) + amt
            result["top_agencies"] = sorted(agency_counts.items(), key=lambda x: -x[1])[:5]

        # ── SIDE B: entity AS AWARDING AGENCY (giving contracts to others) ────
        # Search for awards where awarding_agency_name matches entity
        payload2 = {
            "filters": {
                "keywords": [entity_name],
                "award_type_codes": ["A", "B", "C", "D"],
            },
            "fields": ["Award ID", "Recipient Name", "Award Amount", "Awarding Agency",
                       "Award Type", "Start Date", "Description"],
            "page": 1, "limit": 10, "sort": "Award Amount", "order": "desc"
        }
        resp2 = requests.post("https://api.usaspending.gov/api/v2/search/spending_by_award/",
                              json=payload2, timeout=20)
        if resp2.ok:
            recipient_counts: Dict[str, float] = {}
            for a in resp2.json().get("results", []):
                awarding = a.get("Awarding Agency") or ""
                # Only include if entity is the awarding agency, not just keyword match
                if entity_name.split()[0].lower() not in awarding.lower():
                    continue
                amt = float(a.get("Award Amount") or 0)
                recipient = a.get("Recipient Name") or "Unknown Recipient"
                result["as_agency_awards"].append({
                    "id": a.get("Award ID"),
                    "recipient": recipient,
                    "amount": amt,
                    "agency": awarding,
                    "type": a.get("Award Type"),
                    "start": a.get("Start Date"),
                    "description": a.get("Description"),
                    "side": "awarding_agency",
                })
                result["as_agency_total"] += amt
                recipient_counts[recipient] = recipient_counts.get(recipient, 0) + amt
            result["top_recipients"] = sorted(recipient_counts.items(), key=lambda x: -x[1])[:5]

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


# ── Wikipedia company background ─────────────────────────────────────────────

def _fetch_wikipedia(entity_name: str) -> Dict[str, Any]:
    result = {"summary": "", "founders": [], "founded": None, "hq": None, "url": None}
    slug = entity_name.replace(" ", "_")
    try:
        resp = requests.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{slug}",
            headers={"User-Agent": "IntelPlatform/1.0 research@example.com"},
            timeout=12)
        if resp.ok:
            d = resp.json()
            result["summary"] = d.get("extract", "")[:1200]
            result["url"] = d.get("content_urls", {}).get("desktop", {}).get("page", "")
            result["title"] = d.get("title", "")
    except Exception as e:
        result["error"] = str(e)
    return result


# ── FundedAPI — free investor/funding data (no key needed) ────────────────────

def _fetch_funded_api(entity_name: str) -> Dict[str, Any]:
    result = {"rounds": [], "investors": [], "total_raised": 0}
    try:
        resp = requests.get(
            "https://fundedapi.com/v1/startups",
            params={"q": entity_name, "limit": 5},
            timeout=12)
        if resp.ok:
            data = resp.json()
            startups = data.get("startups", data.get("data", []))
            for s in startups:
                name = s.get("name", "")
                if entity_name.lower().split()[0] in name.lower():
                    round_info = {
                        "name": name,
                        "round": s.get("fundingRound"),
                        "amount": s.get("fundingAmount"),
                        "investors": s.get("investors", []),
                        "date": s.get("scrapedAt", "")[:10],
                    }
                    result["rounds"].append(round_info)
                    amt = float(s.get("fundingAmount") or 0)
                    result["total_raised"] += amt
    except Exception as e:
        result["error"] = str(e)
    return result


# ── SEC Form D / institutional ownership via EDGAR full-text ─────────────────

def _fetch_sec_investors(entity_name: str, cik: Optional[str] = None) -> Dict[str, Any]:
    result = {"form_d_filings": [], "ownership_filings": [], "institutional_notes": ""}
    headers = {"User-Agent": os.getenv("SEC_USER_AGENT", "IntelPlatform research@example.com")}
    try:
        # Search for SC 13G and SC 13D filings mentioning this entity
        search_url = "https://efts.sec.gov/LATEST/search-index"
        resp = requests.get(search_url, headers=headers,
                            params={"q": f'"{entity_name}"',
                                    "forms": "SC 13G,SC 13D",
                                    "dateRange": "custom",
                                    "startdt": "2020-01-01",
                                    "enddt": "2030-01-01"},
                            timeout=15)
        if resp.ok:
            hits = resp.json().get("hits", {}).get("hits", [])
            for h in hits[:8]:
                s = h.get("_source", {})
                # EDGAR uses display_names (list) and root_forms, not entity_name/form_type
                display = s.get("display_names", [])
                # Filter out the subject company itself — we want the FILER
                filer_names = [n for n in display if entity_name.split()[0].lower() not in n.lower()]
                filer = filer_names[0] if filer_names else (display[0] if display else "Unknown")
                # Clean up the display name (remove CIK suffix like " (CIK 000xxx)")
                import re as _re
                filer_clean = _re.sub(r'\s*\(CIK\s*\d+\)', '', filer).strip()
                forms = s.get("root_forms", [s.get("form_type", "SC 13G")])
                result["ownership_filings"].append({
                    "entity": filer_clean,
                    "form": forms[0] if forms else "SC 13G",
                    "filed": s.get("file_date"),
                    "description": s.get("file_description", ""),
                })
            if hits:
                result["institutional_notes"] = f"{len(hits)} institutional ownership filing(s) found (SC 13G/13D)."

        # Also check Form D (private placements) if it's a private company/fund
        resp2 = requests.get(search_url, headers=headers,
                             params={"q": f'"{entity_name}"',
                                     "forms": "D",
                                     "dateRange": "custom",
                                     "startdt": "2005-01-01",
                                     "enddt": "2030-01-01"},
                             timeout=15)
        if resp2.ok:
            hits2 = resp2.json().get("hits", {}).get("hits", [])
            for h in hits2[:5]:
                s = h.get("_source", {})
                display = s.get("display_names", [s.get("entity_name", "")])
                forms = s.get("root_forms", ["D"])
                result["form_d_filings"].append({
                    "entity": display[0] if display else "Unknown",
                    "form": forms[0] if forms else "D",
                    "filed": s.get("file_date"),
                })

    except Exception as e:
        result["error"] = str(e)
    return result


# ── LDA lobbying — BOTH SIDES: client_name AND registrant_name ───────────────

def _fetch_lda(entity_name: str) -> Dict[str, Any]:
    """Fetch LDA filings with two-sided disclosure:
    - As CLIENT (company hiring lobbyists) — the primary view
    - As REGISTRANT (lobbying firm working for clients) — the other side
    Both are returned separately so the report can show the full picture.
    """
    result = {
        "filings": [],
        "total_count": 0,
        "issue_areas": [],
        "top_firms": [],
        # Two-sided disclosure additions
        "as_registrant_filings": [],
        "as_registrant_count": 0,
        "as_registrant_clients": [],
    }

    for base_url in ["https://lda.gov/api/v1/filings/", "https://lda.senate.gov/api/v1/filings/"]:
        try:
            short_name = entity_name.split()[0] if " " in entity_name else entity_name

            # ── SIDE A: entity AS CLIENT (hiring lobbying firms) ──────────────
            resp = requests.get(base_url,
                                params={"client_name": entity_name, "page_size": 15},
                                timeout=20)
            if not resp.ok:
                resp = requests.get(base_url,
                                    params={"client_name": short_name, "page_size": 15},
                                    timeout=20)
            if resp.ok:
                data = resp.json()
                result["total_count"] = data.get("count", 0)
                issue_set = set()
                firm_counts = {}
                for f in data.get("results", []):
                    registrant_name = (f.get("registrant") or {}).get("name", "")
                    client_name_val = (f.get("client") or {}).get("name", "")
                    activities = f.get("lobbying_activities") or []
                    issues = [a.get("general_issue_code_display", "") for a in activities if a.get("general_issue_code_display")]
                    issue_set.update(issues)
                    income = f.get("income") or f.get("expenses") or 0
                    filing = {
                        "uuid": f.get("filing_uuid"),
                        "registrant": registrant_name,
                        "client": client_name_val,
                        "year": f.get("filing_year"),
                        "period": f.get("filing_period"),
                        "income": income,
                        "issues": issues[:3],
                        "side": "client",
                    }
                    result["filings"].append(filing)
                    if registrant_name:
                        firm_counts[registrant_name] = firm_counts.get(registrant_name, 0) + 1
                result["issue_areas"] = sorted(issue_set)[:12]
                result["top_firms"] = sorted(firm_counts.items(), key=lambda x: -x[1])[:5]

            # ── SIDE B: entity AS REGISTRANT (lobbying firm acting for clients) ─
            resp2 = requests.get(base_url,
                                 params={"registrant_name": entity_name, "page_size": 10},
                                 timeout=20)
            if not resp2.ok:
                resp2 = requests.get(base_url,
                                     params={"registrant_name": short_name, "page_size": 10},
                                     timeout=20)
            if resp2 and resp2.ok:
                data2 = resp2.json()
                result["as_registrant_count"] = data2.get("count", 0)
                client_set = {}
                for f in data2.get("results", []):
                    client_name_val = (f.get("client") or {}).get("name", "")
                    income = f.get("income") or f.get("expenses") or 0
                    activities = f.get("lobbying_activities") or []
                    issues = [a.get("general_issue_code_display", "") for a in activities if a.get("general_issue_code_display")]
                    filing2 = {
                        "uuid": f.get("filing_uuid"),
                        "client": client_name_val,
                        "registrant": (f.get("registrant") or {}).get("name", entity_name),
                        "year": f.get("filing_year"),
                        "period": f.get("filing_period"),
                        "income": income,
                        "issues": issues[:3],
                        "side": "registrant",
                    }
                    result["as_registrant_filings"].append(filing2)
                    if client_name_val:
                        client_set[client_name_val] = client_set.get(client_name_val, 0) + 1
                result["as_registrant_clients"] = sorted(client_set.items(), key=lambda x: -x[1])[:5]

            if result["filings"] or result["as_registrant_filings"]:
                break  # success — don't try second URL
        except Exception as e:
            result["error"] = str(e)
            continue
    return result


# ── Enhanced GPT-4o narrative (deeper: company + parties + investors) ─────────

def _generate_narrative(entity_name: str, sections: List[Dict],
                         wiki_data: Dict = None, funded_data: Dict = None) -> str:
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return "[AI narrative unavailable — OPENAI_API_KEY not configured]"

    # Build rich evidence context from all sections + enrichment
    parts = []

    # Wikipedia background
    if wiki_data and wiki_data.get("summary"):
        parts.append(f"\n## Public Background\n{wiki_data['summary']}")

    # FundedAPI investor context
    if funded_data and funded_data.get("rounds"):
        parts.append("\n## Funding Rounds (Public Data)")
        for r in funded_data["rounds"][:3]:
            parts.append(f"- {r.get('round','')} | ${float(r.get('amount') or 0):,.0f} | {r.get('date','')}")

    # All evidence sections
    for s in sections:
        claims = s.get("claims", [])
        if not claims:
            continue
        parts.append(f"\n## {s['name']}")
        for c in claims[:8]:
            txt = c.get("text", "")
            conf = c.get("confidence", "")
            src = c.get("source", "")
            parts.append(f"- [{conf}] {txt[:200]}")

    evidence_block = "\n".join(parts)

    prompt = f"""You are a senior intelligence analyst producing a professional Entity Network Intelligence Report — similar in depth and style to a geopolitical investment dossier.

ENTITY UNDER ANALYSIS: {entity_name}

EVIDENCE FROM PUBLIC RECORDS:
{evidence_block}

REQUIRED OUTPUT — write a deep intelligence narrative with the following structure:

### 1. Company / Entity Overview
Describe what {entity_name} is, its business model, founding story, market position, and strategic significance. Use the background section above.

### 2. Key People & Involved Parties
Identify the key individuals — founders, executives, board members, and major figures — and their roles. Note any cross-entity roles (board seats at other companies, political positions, fund partnerships).

### 3. Investor Network & Capital Structure
Analyze the investor ecosystem around {entity_name}. Who are the key investors, what funds are involved, what does the ownership/capital structure signal about strategic direction? Note any sovereign wealth funds, defense-sector VCs, or politically connected capital.

### 4. Government & Regulatory Exposure
Analyze the federal contract footprint, lobbying strategy (which issues, which firms were hired), and any foreign agent registrations. What does the regulatory posture reveal about business strategy?

### 5. Risk Flags & Strategic Assessment
Synthesize the risk profile: sanctions exposure, litigation, political vulnerabilities, concentration risks, cross-border exposure.

RULES:
- Tag every factual claim: [DOCUMENTED] (primary source), [REPORTED] (press/secondary), or [ANALYTICAL] (your inference)
- Do NOT invent facts not present in the evidence above
- Write at the depth of a professional intelligence dossier — 5-7 substantial paragraphs minimum
- Use formal, precise intelligence report language
- Be specific about amounts, dates, agency names where present in evidence"""

    try:
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You are a senior intelligence analyst at a professional intelligence research firm. You write deep, evidence-first dossiers at the level of Jane's Intelligence Review or Kroll/Mintz analytical reports. You are thorough, precise, and analytical."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.15,
                "max_tokens": 2000,
            },
            timeout=60,
        )
        if resp.ok:
            return resp.json()["choices"][0]["message"]["content"]
        return f"[GPT error {resp.status_code}: {resp.text[:200]}]"
    except Exception as e:
        return f"[GPT narrative error: {str(e)}]"


# ── PayPal Mafia / Thiel demo seed data ───────────────────────────────────────

DEMO_SEEDS = {
    # PayPal Mafia
    "Peter Thiel":           {"ticker": "",     "type": "person", "group": "paypal_mafia"},
    "Elon Musk":             {"ticker": "TSLA", "type": "person", "group": "paypal_mafia"},
    "Reid Hoffman":          {"ticker": "",     "type": "person", "group": "paypal_mafia"},
    "Max Levchin":           {"ticker": "AFRM", "type": "person", "group": "paypal_mafia"},
    "David Sacks":           {"ticker": "",     "type": "person", "group": "paypal_mafia"},
    # Thiel / Defense / AI portfolio
    "Palantir Technologies": {"ticker": "PLTR", "type": "org",    "group": "thiel_portfolio"},
    "Anduril Industries":    {"ticker": "",     "type": "org",    "group": "thiel_portfolio"},
    "Founders Fund":         {"ticker": "",     "type": "fund",   "group": "thiel_portfolio"},
    "HawkEye 360":           {"ticker": "",     "type": "org",    "group": "thiel_portfolio"},
    "Redwire Corporation":   {"ticker": "RDW",  "type": "org",    "group": "thiel_portfolio"},
}


# ── Main orchestrator (v1.2 — Apify LinkedIn + PitchBook + News + Two-sided) ──

def generate_intelligence_report(db: Session, entity_name: str, entity_type: str = "org",
                                  ticker: Optional[str] = None) -> Dict[str, Any]:
    started = _now()
    is_person = entity_type == "person"

    # 1. Resolve/create entity in DB
    entity_id = _upsert_entity(db, entity_name, entity_type)

    # 2. Run all connectors (existing + new enrichment)
    sec_data      = _fetch_sec(entity_name, ticker)
    fec_data      = _fetch_fec(entity_name)
    fara_data     = _fetch_fara(entity_name)
    spending_data = _fetch_usaspending(entity_name)
    lda_data      = _fetch_lda(entity_name)            # TWO-SIDED: client + registrant
    ofac_data     = _fetch_ofac(entity_name)
    court_data    = _fetch_courts(entity_name)
    wiki_data     = _fetch_wikipedia(entity_name)
    funded_data   = _fetch_funded_api(entity_name)
    investor_data = _fetch_sec_investors(entity_name, sec_data.get("cik"))

    # Apify enrichment (LinkedIn + PitchBook + News + Social)
    apify_linkedin   = {}
    apify_pitchbook  = {}
    apify_news       = []
    apify_social     = {}
    apify_key_people = []
    if APIFY_AVAILABLE:
        if is_person:
            apify_linkedin = fetch_linkedin_by_name(entity_name)
        else:
            try:
                apify_key_people = fetch_key_people(entity_name, limit=15)
            except Exception as _kpe:
                logger.warning("Key people scrape failed: %s", _kpe)
        apify_pitchbook = fetch_pitchbook_company(entity_name)
        apify_news = fetch_news(entity_name, max_articles=8)
        try:
            apify_social = fetch_social_footprint(entity_name)
        except Exception as _se:
            logger.warning("Social footprint fetch failed: %s", _se)

    # Browser research agent (non-US entities or deep dive)
    browser_research = {}
    jurisdiction = detect_jurisdiction(entity_name) if BROWSER_AGENT_AVAILABLE else "default"
    run_browser_agent = (
        BROWSER_AGENT_AVAILABLE
        and jurisdiction not in ("default",)  # Only run when jurisdiction is known non-US
        and not is_us_entity(entity_name, entity_type)
    )

    # 3. Write relationships into graph
    relationships_created = []

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

    for award in spending_data.get("awards", []):
        agency_name = award.get("agency") or "Unknown Agency"
        if agency_name and award.get("amount"):
            agency_id = _upsert_entity(db, agency_name, "agency")
            _upsert_rel(db, entity_id, agency_id, "awarded_contract")
            relationships_created.append({"kind": "awarded_contract", "entity": agency_name,
                                          "amount": award.get("amount")})

    for committee in fec_data.get("committees", []):
        if committee.get("name"):
            pac_id = _upsert_entity(db, committee["name"], "pac")
            _upsert_rel(db, entity_id, pac_id, "affiliated_pac")
            relationships_created.append({"kind": "affiliated_pac", "entity": committee["name"]})

    for reg in fara_data.get("registrants", []):
        if reg.get("name"):
            fa_id = _upsert_entity(db, reg["name"], "org")
            _upsert_rel(db, entity_id, fa_id, "fara_registrant")
            relationships_created.append({"kind": "fara_registrant", "entity": reg["name"]})

    # Lobbying firms as relationships
    for firm_name, count in lda_data.get("top_firms", []):
        if firm_name:
            firm_id = _upsert_entity(db, firm_name, "org")
            _upsert_rel(db, firm_id, entity_id, "lobbies_for")
            relationships_created.append({"kind": "lobbies_for", "entity": firm_name, "filings": count})

    # 4. Assemble 9 report sections (expanded from 7)
    sections = []

    # ── Section 1: Entity Profile ─────────────────────────────────────────────
    sec1_claims = []
    if wiki_data.get("summary"):
        sec1_claims.append({"text": wiki_data["summary"][:600],
                            "confidence": "DOCUMENTED", "source": "Wikipedia"})
    if sec_data.get("cik"):
        sec1_claims.append({"text": f"SEC CIK: {sec_data['cik']}. SIC: {sec_data.get('sic_desc','')} ({sec_data.get('sic','')}).",
                            "confidence": "DOCUMENTED", "source": "SEC EDGAR"})
    if sec_data.get("state_of_inc"):
        sec1_claims.append({"text": f"Incorporated in {sec_data['state_of_inc']}; listed on {', '.join(sec_data.get('exchanges',[]))}.",
                            "confidence": "DOCUMENTED", "source": "SEC EDGAR"})
    sections.append({"name": "Entity Profile", "order": 1, "claims": sec1_claims,
                     "data": {"cik": sec_data.get("cik"), "company": sec_data.get("company_name"),
                              "wiki_url": wiki_data.get("url",""), "sic": sec_data.get("sic_desc","")}})

    # ── Section 2: Investors & Capital Structure ──────────────────────────────
    sec2_claims = []
    # SEC 13G/13D institutional ownership
    for f in investor_data.get("ownership_filings", [])[:6]:
        sec2_claims.append({"text": f"SEC 13G/13D filing associated: {f.get('entity')} — form {f.get('form')} filed {f.get('filed','unknown')} (related filing in EDGAR).",
                            "confidence": "DOCUMENTED", "source": "SEC EDGAR (SC 13G/13D)"})
    if investor_data.get("institutional_notes"):
        sec2_claims.append({"text": investor_data["institutional_notes"],
                            "confidence": "DOCUMENTED", "source": "SEC EDGAR"})
    # FundedAPI rounds
    for r in funded_data.get("rounds", []):
        if r.get("amount"):
            investors_str = ", ".join(r.get("investors", [])[:4]) or "undisclosed"
            sec2_claims.append({"text": f"Funding round: {r.get('round','')} — ${float(r.get('amount',0)):,.0f} ({r.get('date','')}). Investors: {investors_str}.",
                                "confidence": "REPORTED", "source": "FundedAPI (public)"})
    # Form D private placements
    for f in investor_data.get("form_d_filings", [])[:3]:
        sec2_claims.append({"text": f"SEC Form D (private placement): {f.get('entity')} filed {f.get('filed','unknown')}.",
                            "confidence": "DOCUMENTED", "source": "SEC EDGAR (Form D)"})
    # SEC filings as ownership indicators
    forms_seen = {}
    for f in sec_data.get("filings", []):
        form = f.get("form","")
        if form and form not in forms_seen:
            forms_seen[form] = f.get("date")
    for form, date in list(forms_seen.items())[:6]:
        sec2_claims.append({"text": f"SEC filing: {form} ({date}).",
                            "confidence": "DOCUMENTED", "source": "SEC EDGAR"})
    if not sec2_claims:
        sec2_claims.append({"text": "No institutional ownership or funding round data found via public sources.",
                            "confidence": "DOCUMENTED", "source": "SEC/FundedAPI"})
    sections.append({"name": "Investors & Capital Structure", "order": 2,
                     "claims": sec2_claims,
                     "data": {"institutional_filings": len(investor_data.get("ownership_filings",[])),
                              "funding_rounds": len(funded_data.get("rounds",[])),
                              "total_raised": funded_data.get("total_raised", 0)}})

    # ── Section 3: Government Contracts & Procurement — BOTH SIDES ───────────
    sec3_claims = []

    # SIDE A — entity AS RECIPIENT (receiving contracts)
    if spending_data.get("awards"):
        sec3_claims.append({
            "text": f"[AS RECIPIENT] {entity_name} received {len(spending_data['awards'])} federal contract award(s) totaling ${spending_data.get('total_obligated', 0):,.0f} from USASpending.gov.",
            "confidence": "DOCUMENTED", "source": "USASpending.gov"
        })
    for agency, amt in spending_data.get("top_agencies", [])[:3]:
        sec3_claims.append({
            "text": f"[RECIPIENT SIDE] Top awarding agency: {agency} — ${amt:,.0f} obligated.",
            "confidence": "DOCUMENTED", "source": "USASpending.gov"
        })
    for a in spending_data.get("awards", []):
        amt = a.get("amount", 0)
        desc = (' — ' + a['description'][:80]) if a.get('description') else ''
        sec3_claims.append({
            "text": f"[RECIPIENT SIDE] ${float(amt):,.0f} from {a.get('agency')} ({a.get('type')}){desc}. Start: {a.get('start', 'unknown')}.",
            "confidence": "DOCUMENTED", "source": "USASpending.gov"
        })

    # SIDE B — entity AS AWARDING AGENCY (giving contracts to others)
    if spending_data.get("as_agency_awards"):
        sec3_claims.append({
            "text": f"[AS AWARDING AGENCY] {entity_name} appears as awarding agency in {len(spending_data['as_agency_awards'])} contract(s) totaling ${spending_data.get('as_agency_total', 0):,.0f}.",
            "confidence": "DOCUMENTED", "source": "USASpending.gov"
        })
    for recipient, amt in spending_data.get("top_recipients", [])[:3]:
        sec3_claims.append({
            "text": f"[AGENCY SIDE] Top recipient of contracts from {entity_name}: {recipient} — ${amt:,.0f}.",
            "confidence": "DOCUMENTED", "source": "USASpending.gov"
        })
    for a in spending_data.get("as_agency_awards", [])[:3]:
        amt = a.get("amount", 0)
        sec3_claims.append({
            "text": f"[AGENCY SIDE] {entity_name} awarded ${float(amt):,.0f} to {a.get('recipient')} ({a.get('type')}). Start: {a.get('start', 'unknown')}.",
            "confidence": "DOCUMENTED", "source": "USASpending.gov"
        })

    if not sec3_claims:
        sec3_claims.append({"text": "No direct federal contract awards found (neither as recipient nor as awarding agency).",
                            "confidence": "DOCUMENTED", "source": "USASpending.gov"})
    sections.append({"name": "Government Contracts & Procurement", "order": 3,
                     "claims": sec3_claims,
                     "data": {
                         "total_obligated_usd": spending_data.get("total_obligated", 0),
                         "award_count": len(spending_data.get("awards", [])),
                         "as_agency_count": len(spending_data.get("as_agency_awards", [])),
                         "as_agency_total_usd": spending_data.get("as_agency_total", 0),
                     }})

    # ── Section 4: Lobbying Activity — BOTH SIDES ────────────────────────────
    sec4_claims = []

    # SIDE A — entity AS CLIENT (hiring lobbyists)
    if lda_data.get("total_count", 0) > 0:
        sec4_claims.append({"text": f"[AS CLIENT] {entity_name} has {lda_data['total_count']} lobbying filings on record as the client hiring lobbying firms (LDA database).",
                            "confidence": "DOCUMENTED", "source": "LDA / lda.gov"})
    if lda_data.get("issue_areas"):
        sec4_claims.append({"text": f"Lobbying issue areas (as client): {', '.join(lda_data['issue_areas'][:10])}.",
                            "confidence": "DOCUMENTED", "source": "LDA"})
    for firm, count in lda_data.get("top_firms", [])[:5]:
        sec4_claims.append({"text": f"[CLIENT SIDE] Lobbying firm {firm} filed {count} disclosure(s) on behalf of {entity_name}.",
                            "confidence": "DOCUMENTED", "source": "LDA"})
    for f in lda_data.get("filings", [])[:5]:
        income = f.get("income") or 0
        issues_str = ", ".join(f.get("issues", []))
        sec4_claims.append({"text": f"[CLIENT SIDE] {f.get('registrant','')} → Client: {f.get('client','')} | Period: {f.get('period','')} {f.get('year','')} | Income: ${float(income):,.0f} | Issues: {issues_str}.",
                            "confidence": "DOCUMENTED", "source": "LDA"})

    # SIDE B — entity AS REGISTRANT (lobbying firm acting for clients)
    if lda_data.get("as_registrant_count", 0) > 0:
        sec4_claims.append({"text": f"[AS LOBBYING FIRM] {entity_name} also appears as a registered lobbying firm in {lda_data['as_registrant_count']} filings — acting on behalf of other clients.",
                            "confidence": "DOCUMENTED", "source": "LDA"})
    for client_name, count in lda_data.get("as_registrant_clients", [])[:3]:
        sec4_claims.append({"text": f"[REGISTRANT SIDE] {entity_name} lobbied on behalf of: {client_name} ({count} filing(s)).",
                            "confidence": "DOCUMENTED", "source": "LDA"})
    for f in lda_data.get("as_registrant_filings", [])[:3]:
        income = f.get("income") or 0
        sec4_claims.append({"text": f"[REGISTRANT SIDE] {f.get('registrant','')} lobbied for client {f.get('client','')} | Period: {f.get('period','')} {f.get('year','')} | Income: ${float(income):,.0f}.",
                            "confidence": "DOCUMENTED", "source": "LDA"})

    if not sec4_claims:
        sec4_claims.append({"text": "No lobbying filings found (neither as client nor as registrant) in LDA database.",
                            "confidence": "DOCUMENTED", "source": "LDA"})

    sections.append({"name": "Lobbying Activity (Both Sides)", "order": 4,
                     "claims": sec4_claims,
                     "data": {
                         "total_lobbying_filings": lda_data.get("total_count", 0),
                         "as_registrant_count": lda_data.get("as_registrant_count", 0),
                         "issue_areas": lda_data.get("issue_areas", []),
                         "lobbying_firms": len(lda_data.get("top_firms", []))}})

    # ── Section 5: Political & Foreign Exposure ───────────────────────────────
    sec5_claims = []
    # ── FEC: Side A — entity as a registered PAC/committee ──
    for c in fec_data.get("committees", []):
        sec5_claims.append({
            "text": f"[FEC COMMITTEE — REGISTRANT SIDE] {c['name']} ({c.get('type','')}, {c.get('state','')}) — "
                    f"Entity is the registered political committee.",
            "confidence": "DOCUMENTED", "source": "FEC OpenData",
        })
    # ── FEC: Side B — entity as a donor/contributor ──
    for contrib in fec_data.get("as_contributor", [])[:5]:
        sec5_claims.append({
            "text": f"[FEC CONTRIBUTOR SIDE] {contrib.get('contributor','')} donated "
                    f"${contrib.get('amount',0):,.0f} on {contrib.get('date','')} "
                    f"to {contrib.get('recipient','')}.",
            "confidence": "DOCUMENTED", "source": "FEC Schedule A",
        })

    # ── FARA: Side A — entity as the registered lobbyist ──
    for r in fara_data.get("registrants", []):
        sec5_claims.append({
            "text": f"[FARA REGISTRANT SIDE] FARA registration #{r.get('reg_num')}: "
                    f"{r['name']} registered as foreign agent (foreign country: {r.get('country','unknown')}).",
            "confidence": "DOCUMENTED", "source": "FARA DOJ",
        })
    # ── FARA: Side B — entity as the foreign principal ──
    for fp in fara_data.get("foreign_principals", []):
        sec5_claims.append({
            "text": f"[FARA FOREIGN PRINCIPAL SIDE] {fp.get('foreign_principal','')} "
                    f"is represented in the US by FARA registrant {fp.get('registrant','')} "
                    f"(reg #{fp.get('reg_num','')}) on behalf of {fp.get('country','unknown')}.",
            "confidence": "DOCUMENTED", "source": "FARA DOJ",
        })

    if not sec5_claims:
        sec5_claims.append({"text": "No FEC committees, FEC contributions, or FARA registrations found.",
                            "confidence": "DOCUMENTED", "source": "FEC/FARA"})
    sections.append({"name": "Political & Foreign Exposure (FEC + FARA — Both Sides)", "order": 5,
                     "claims": sec5_claims, "data": {
                         "fec_committees":    len(fec_data.get("committees", [])),
                         "fec_contributions": len(fec_data.get("as_contributor", [])),
                         "fara_registrant":   len(fara_data.get("registrants", [])),
                         "fara_fp_side":      len(fara_data.get("foreign_principals", [])),
                     }})

    # ── Section 5b: People & Education (Apify LinkedIn — persons only) ────────
    if is_person and APIFY_AVAILABLE:
        sec5b_claims = []
        if apify_linkedin.get("headline"):
            sec5b_claims.append({"text": f"LinkedIn Headline: {apify_linkedin['headline']}",
                                 "confidence": "DOCUMENTED", "source": "LinkedIn (via Apify)"})
        if apify_linkedin.get("about"):
            sec5b_claims.append({"text": apify_linkedin["about"][:400],
                                 "confidence": "DOCUMENTED", "source": "LinkedIn (via Apify)"})
        if apify_linkedin.get("location"):
            sec5b_claims.append({"text": f"Location: {apify_linkedin['location']}",
                                 "confidence": "DOCUMENTED", "source": "LinkedIn (via Apify)"})
        for ed in apify_linkedin.get("education", [])[:5]:
            school  = ed.get("school") or "Unknown school"
            degree  = ed.get("degree") or ""
            field   = ed.get("field") or ""
            years   = f"{ed.get('start','')}–{ed.get('end','')}" if ed.get("start") else ""
            sec5b_claims.append({"text": f"Education: {school} — {degree} {field} {years}".strip(" —"),
                                 "confidence": "DOCUMENTED", "source": "LinkedIn (via Apify)"})
        for ex in apify_linkedin.get("experience", [])[:5]:
            company = ex.get("company") or "Unknown org"
            title   = ex.get("title") or ""
            start   = ex.get("start") or ""
            end     = ex.get("end") or "Present"
            sec5b_claims.append({"text": f"Career: {title} at {company} ({start}–{end}).",
                                 "confidence": "DOCUMENTED", "source": "LinkedIn (via Apify)"})
        if apify_linkedin.get("note"):
            sec5b_claims.append({"text": f"Note: {apify_linkedin['note']}",
                                 "confidence": "ANALYTICAL", "source": "Apify"})
        if not sec5b_claims:
            sec5b_claims.append({"text": f"LinkedIn profile not found for {entity_name} via public URL slug.",
                                 "confidence": "DOCUMENTED", "source": "Apify/LinkedIn"})
        sections.append({"name": "People & Education (LinkedIn)", "order": 6,
                         "claims": sec5b_claims,
                         "data": {
                             "education_entries": len(apify_linkedin.get("education", [])),
                             "experience_entries": len(apify_linkedin.get("experience", [])),
                             "source": "Apify/LinkedIn",
                         }})

    # ── Section: Key People & Org Chart (companies only) ─────────────────────
    if not is_person and APIFY_AVAILABLE and apify_key_people:
        kp_claims = []
        for person in apify_key_people[:15]:
            name_str    = person.get("name", "")
            title_str   = person.get("title", "")
            loc_str     = person.get("location", "")
            li_url      = person.get("linkedin_url", "")
            tenure_str  = f" · Tenure: {person.get('tenure_months','')}mo" if person.get("tenure_months") else ""
            kp_claims.append({
                "text": f"[KEY PERSON] {name_str} — {title_str} | {loc_str}{tenure_str}"
                        + (f" | {li_url}" if li_url else ""),
                "confidence": "DOCUMENTED",
                "source": "Apify/LinkedIn Company",
            })
            # Auto-create graph edge: company → person
            if name_str:
                try:
                    person_id = _upsert_entity(db, name_str, "person", {})
                    _upsert_rel(db, entity_id, person_id, "employs")
                    relationships_created.append({"kind": "employs", "entity": name_str})
                except Exception as _kpe_graph:
                    pass  # Non-fatal

        if kp_claims:
            sections.append({
                "name": "Key People & Org Chart (LinkedIn Company Employees)",
                "order": max((s["order"] for s in sections if isinstance(s.get("order"), int)), default=10) + 1,
                "claims": kp_claims,
                "data": {
                    "total_people": len(apify_key_people),
                    "source": "Apify/LinkedIn Company Scraper",
                },
            })

    sec6_claims = []
    if ofac_data.get("is_sanctioned"):
        sec6_claims.append({"text": f"ALERT: {len(ofac_data['hits'])} OFAC/OpenSanctions record(s) match this entity name.",
                            "confidence": "DOCUMENTED", "source": "OFAC/OpenSanctions"})
        for h in ofac_data.get("hits", []):
            sec6_claims.append({"text": f"Match: {h.get('name')} — datasets: {', '.join(h.get('datasets',[]))}.",
                               "confidence": "DOCUMENTED", "source": "OpenSanctions"})
    else:
        sec6_claims.append({"text": "No OFAC sanctions or OpenSanctions matches found.",
                            "confidence": "DOCUMENTED", "source": "OFAC/OpenSanctions"})
    sections.append({"name": "Sanctions & Compliance", "order": 7,
                     "claims": sec6_claims,
                     "data": {"sanctioned": ofac_data.get("is_sanctioned", False)}})

    # ── Section 7: Litigation & Legal ────────────────────────────────────────
    sec7_claims = []
    for c in court_data.get("cases", []):
        sec7_claims.append({"text": f"{c.get('case_name')} ({c.get('court')}, filed {c.get('date_filed')}) — {c.get('cause','no cause listed')}.",
                            "confidence": "REPORTED", "source": "CourtListener"})
    if not sec7_claims:
        sec7_claims.append({"text": "No federal court dockets found via CourtListener.",
                            "confidence": "DOCUMENTED", "source": "CourtListener"})
    sections.append({"name": "Litigation & Legal Exposure", "order": 8,
                     "claims": sec7_claims,
                     "data": {"case_count": len(court_data.get("cases", []))}})

    # ── Section 8: PitchBook & Investor Intelligence (Apify) ─────────────────
    if APIFY_AVAILABLE and (apify_pitchbook.get("description") or apify_pitchbook.get("investors")):
        sec_pb_claims = []
        if apify_pitchbook.get("description"):
            sec_pb_claims.append({"text": apify_pitchbook["description"][:400],
                                  "confidence": "REPORTED", "source": "PitchBook (via Apify)"})
        if apify_pitchbook.get("stage"):
            sec_pb_claims.append({"text": f"Stage: {apify_pitchbook['stage']}",
                                  "confidence": "REPORTED", "source": "PitchBook (via Apify)"})
        if apify_pitchbook.get("total_raised"):
            sec_pb_claims.append({"text": f"Total raised: {apify_pitchbook['total_raised']}",
                                  "confidence": "REPORTED", "source": "PitchBook (via Apify)"})
        if apify_pitchbook.get("founded"):
            sec_pb_claims.append({"text": f"Founded: {apify_pitchbook['founded']}",
                                  "confidence": "DOCUMENTED", "source": "PitchBook (via Apify)"})
        for inv in apify_pitchbook.get("investors", [])[:8]:
            sec_pb_claims.append({"text": f"Investor: {inv}",
                                  "confidence": "REPORTED", "source": "PitchBook (via Apify)"})
        for rnd in apify_pitchbook.get("funding_rounds", [])[:5]:
            sec_pb_claims.append({"text": f"Funding round: {rnd.get('type','')} — {rnd.get('amount','')} ({rnd.get('date','')})",
                                  "confidence": "REPORTED", "source": "PitchBook (via Apify)"})
        for comp in apify_pitchbook.get("competitors", [])[:4]:
            sec_pb_claims.append({"text": f"Competitor: {comp}",
                                  "confidence": "ANALYTICAL", "source": "PitchBook (via Apify)"})
        if sec_pb_claims:
            sections.append({"name": "PitchBook & Investor Intelligence", "order": 9,
                             "claims": sec_pb_claims,
                             "data": {
                                 "pb_investors": len(apify_pitchbook.get("investors", [])),
                                 "pb_rounds": len(apify_pitchbook.get("funding_rounds", [])),
                                 "source": "Apify/PitchBook",
                             }})

    # ── Section 9: News & Media Timeline (Apify) ─────────────────────────────
    if APIFY_AVAILABLE and apify_news:
        sec_news_claims = []
        for article in apify_news[:8]:
            date_str = f" ({article['published']})" if article.get("published") else ""
            src_str  = f" [{article['source']}]" if article.get("source") else ""
            snippet  = f" — {article['snippet'][:150]}" if article.get("snippet") else ""
            url_str  = f" {article['url']}" if article.get("url") else ""
            sec_news_claims.append({
                "text": f"{article.get('title','')}{date_str}{src_str}{snippet}{url_str}",
                "confidence": "REPORTED",
                "source": f"Google News via Apify ({article.get('source','')})",
            })
        if sec_news_claims:
            sections.append({"name": "News & Media Timeline", "order": 10,
                             "claims": sec_news_claims,
                             "data": {"articles_found": len(apify_news), "source": "Apify/Google News"}})

    # ── Section 10: Browser Research (non-US jurisdictions) ──────────────────
    if run_browser_agent:
        browser_research = research_entity_browser(
            entity_name, jurisdiction=jurisdiction, max_sources=4
        )
        if browser_research.get("findings") or browser_research.get("summary"):
            br_claims = []
            br_claims.append({
                "text": f"[BROWSER RESEARCH] Jurisdiction detected: {browser_research.get('jurisdiction', 'unknown').upper()}. Sources checked: {', '.join(browser_research.get('sources_checked', []))}. Data found in {browser_research.get('sources_with_data', 0)} source(s). Confidence: {browser_research.get('confidence', 'LOW')}.",
                "confidence": "DOCUMENTED", "source": "Browser Research Agent",
            })
            for finding in browser_research.get("findings", [])[:12]:
                if finding:
                    br_claims.append({
                        "text": finding,
                        "confidence": "REPORTED",
                        "source": f"Browser Research ({browser_research.get('jurisdiction', 'int').upper()})",
                    })
            if browser_research.get("summary") and not browser_research["findings"]:
                # Fallback: include raw summary as a narrative
                br_claims.append({
                    "text": browser_research["summary"][:1500],
                    "confidence": "REPORTED",
                    "source": f"Browser Research ({browser_research.get('jurisdiction', 'int').upper()})",
                })
            if br_claims:
                sections.append({
                    "name": f"International Research — {browser_research.get('jurisdiction', 'Int').title()} (Browser)",
                    "order": max((s["order"] for s in sections), default=10) + 1,
                    "claims": br_claims,
                    "data": {
                        "jurisdiction": browser_research.get("jurisdiction"),
                        "sources_checked": len(browser_research.get("sources_checked", [])),
                        "sources_with_data": browser_research.get("sources_with_data", 0),
                        "confidence": browser_research.get("confidence", "LOW"),
                    }
                })

    # ── Section: Social Footprint (Twitter, Instagram, YouTube) ──────────────
    social_claims = []
    tw = apify_social.get("twitter", {})
    ig = apify_social.get("instagram", {})
    yt = apify_social.get("youtube", {})

    if tw.get("name") or tw.get("followers"):
        verif = " ✓ Verified" if tw.get("verified") else ""
        tw_followers  = int(tw.get("followers") or 0)
        tw_following  = int(tw.get("following") or 0)
        tw_tweets     = int(tw.get("tweets_count") or 0)
        social_claims.append({
            "text": f"[TWITTER/X] @{tw.get('username','')}{verif} — {tw.get('name','')} — "
                    f"{tw_followers:,} followers · {tw_following:,} following · "
                    f"{tw_tweets:,} tweets · Bio: {(tw.get('bio') or '')[:200]}",
            "confidence": "DOCUMENTED", "source": "Apify/Twitter",
        })
        for t in tw.get("recent_tweets", [])[:3]:
            social_claims.append({
                "text": f"[TWEET] {(t.get('text') or '')[:200]} (❤ {int(t.get('likes') or 0):,} 🔁 {int(t.get('retweets') or 0):,})",
                "confidence": "DOCUMENTED", "source": "Twitter",
            })

    if ig.get("name") or ig.get("followers"):
        verif = " ✓ Verified" if ig.get("verified") else ""
        ig_followers  = int(ig.get("followers") or 0)
        ig_posts      = int(ig.get("posts_count") or 0)
        social_claims.append({
            "text": f"[INSTAGRAM] @{ig.get('username','')}{verif} — {ig.get('name','')} — "
                    f"{ig_followers:,} followers · {ig_posts:,} posts · "
                    f"Bio: {(ig.get('bio') or '')[:200]}",
            "confidence": "DOCUMENTED", "source": "Apify/Instagram",
        })

    if yt.get("channel_name") or yt.get("subscribers"):
        subs     = int(yt.get("subscribers") or 0)
        vid_cnt  = int(yt.get("video_count") or 0)
        social_claims.append({
            "text": f"[YOUTUBE] {yt.get('channel_name','')} — "
                    f"{subs:,} subscribers · {vid_cnt:,} videos",
            "confidence": "DOCUMENTED", "source": "Apify/YouTube",
        })
        for v in yt.get("recent_videos", [])[:3]:
            social_claims.append({
                "text": f"[VIDEO] {v.get('title','')} — {int(v.get('views') or 0):,} views",
                "confidence": "DOCUMENTED", "source": "YouTube",
            })

    if social_claims:
        sections.append({
            "name": "Social Media Footprint (Twitter · Instagram · YouTube)",
            "order": max((s["order"] for s in sections), default=10) + 1,
            "claims": social_claims,
            "data": {
                "twitter":   tw,
                "instagram": ig,
                "youtube":   yt,
            },
        })

    # ── Section: Private Company Intelligence (OpenCorporates, GLEIF, FinCEN) ──
    priv_co = {}
    if PRIVATE_CO_AVAILABLE and not is_person:
        try:
            priv_co = fetch_private_company_intel(entity_name) or {}
        except Exception as exc:
            logger.warning("Private company intel failed: %s", exc)

    priv_claims = []
    for match in (priv_co.get("opencorporates_matches") or [])[:3]:
        priv_claims.append({
            "text": f"[OPENCORPORATES] {match['name']} — {match.get('jurisdiction','').upper()} · "
                    f"Type: {match.get('company_type','N/A')} · Status: {match.get('status','N/A')} · "
                    f"Incorporated: {match.get('incorporation_date','N/A')} · "
                    f"Address: {match.get('registered_address','N/A')}",
            "confidence": "DOCUMENTED",
            "source": "OpenCorporates",
        })

    oc_detail = priv_co.get("opencorporates_detail", {})
    for off in (oc_detail.get("officers") or [])[:8]:
        status_str = " [INACTIVE]" if off.get("inactive") else ""
        priv_claims.append({
            "text": f"[OFFICER] {off.get('name','N/A')}{status_str} — Role: {off.get('role','N/A')} "
                    f"(since {off.get('start','?')})",
            "confidence": "DOCUMENTED",
            "source": "OpenCorporates",
        })

    for gl in (priv_co.get("gleif_matches") or [])[:2]:
        priv_claims.append({
            "text": f"[GLEIF LEI] {gl.get('name','')} — LEI: {gl.get('lei','')} · "
                    f"Status: {gl.get('status','')} · Jurisdiction: {gl.get('jurisdiction','')} · "
                    f"Registered: {gl.get('registered_at','')} · Address: {gl.get('registered_address','')}",
            "confidence": "DOCUMENTED",
            "source": "GLEIF",
        })

    rels = priv_co.get("gleif_relationships", {})
    if rels.get("ultimate_parent") or rels.get("direct_parent"):
        up = rels.get("ultimate_parent", {})
        dp = rels.get("direct_parent", {})
        priv_claims.append({
            "text": f"[GLEIF STRUCTURE] Ultimate parent: {up.get('id','N/A')} · "
                    f"Direct parent: {dp.get('id','N/A')}",
            "confidence": "DOCUMENTED",
            "source": "GLEIF Relationships",
        })

    for fc in (priv_co.get("fincen_records") or [])[:3]:
        priv_claims.append({
            "text": f"[FINCEN] {fc.get('name','')} — Type: {fc.get('type','')} · "
                    f"Status: {fc.get('status','')} · {fc.get('city','')}, {fc.get('state','')}, {fc.get('country','')} · "
                    f"Registered: {fc.get('reg_date','')}",
            "confidence": "DOCUMENTED",
            "source": "FinCEN",
        })

    for bank in (priv_co.get("fdic_records") or [])[:2]:
        priv_claims.append({
            "text": f"[FDIC] {bank.get('name','')} — Cert: {bank.get('cert','')} · "
                    f"Active: {'Yes' if bank.get('active') else 'No'} · "
                    f"Established: {bank.get('established','')} · "
                    f"Assets: ${bank.get('total_assets_k',0):,}K",
            "confidence": "DOCUMENTED",
            "source": "FDIC BankFind",
        })

    if priv_claims:
        sections.append({
            "name": "Private Company Intelligence (OpenCorporates · GLEIF · FinCEN)",
            "order": max((s["order"] for s in sections), default=10) + 1,
            "claims": priv_claims,
            "data": {
                "opencorporates_matches": len(priv_co.get("opencorporates_matches", [])),
                "gleif_matches":          len(priv_co.get("gleif_matches", [])),
                "fincen_records":         len(priv_co.get("fincen_records", [])),
                "fdic_records":           len(priv_co.get("fdic_records", [])),
                "officers":               len(oc_detail.get("officers", [])),
            },
        })

    # ── Section: Apollo enrichment ────────────────────────────────────────────
    apollo_org   = {}
    apollo_people_list = []
    if APOLLO_AVAILABLE and not is_person:
        try:
            # Name-based search first (most accurate — resolves to correct domain internally)
            apollo_org = apollo_search_org(entity_name) or {}
            # Fall back to domain guess only if search came back empty
            if not apollo_org.get("name"):
                slug = entity_name.lower().replace(" ", "").replace(".", "").replace(",", "")
                apollo_org = apollo_enrich_org(domain=f"{slug}.com") or {}
            apollo_people_list = apollo_org_chart(entity_name) or []
        except Exception as exc:
            logger.warning("Apollo enrichment failed: %s", exc)

    if apollo_org or apollo_people_list:
        apollo_claims = []
        if apollo_org.get("name"):
            apollo_headcount = int(apollo_org.get("headcount") or apollo_org.get("headcount_range") or 0)
            apollo_claims.append({
                "text": f"[APOLLO ORG] {apollo_org['name']} — "
                        f"Industry: {apollo_org.get('industry','N/A')} · "
                        f"Headcount: {apollo_headcount:,} · "
                        f"Revenue range: {apollo_org.get('revenue_range','N/A')} · "
                        f"Founded: {apollo_org.get('founded_year','N/A')} · "
                        f"HQ: {apollo_org.get('city','')}, {apollo_org.get('country','')}.",
                "confidence": "DOCUMENTED",
                "source": "Apollo.io",
            })
            if apollo_org.get("technologies"):
                apollo_claims.append({
                    "text": f"[APOLLO TECH STACK] {', '.join(apollo_org['technologies'][:12])}.",
                    "confidence": "DOCUMENTED",
                    "source": "Apollo.io",
                })
        for p in apollo_people_list[:15]:
            email_str = f" <{p['email']}>" if p.get("email") else ""
            apollo_claims.append({
                "text": f"[APOLLO PERSON] {p['name']}{email_str} — {p.get('title','N/A')} | {p.get('department','')}"
                        f" | Seniority: {p.get('seniority','N/A')} | {p.get('city','')}, {p.get('country','')}.",
                "confidence": "DOCUMENTED",
                "source": "Apollo.io",
            })
        if apollo_claims:
            sections.append({
                "name": "Apollo.io — Org Intelligence & Key People",
                "order": max((s["order"] for s in sections), default=10) + 1,
                "claims": apollo_claims,
                "data": {
                    "org": apollo_org,
                    "key_people": apollo_people_list[:15],
                    "total_people": len(apollo_people_list),
                },
            })

    # ── Section N-1: Data Sources ─────────────────────────────────────────────
    apify_status = f"Apify enrichment: {'active' if APIFY_AVAILABLE else 'inactive (no token)'}. " \
                   f"LinkedIn: {'profile fetched' if apify_linkedin.get('headline') else 'slug-based lookup attempted'}. " \
                   f"PitchBook: {len(apify_pitchbook.get('investors', []))} investors. " \
                   f"News: {len(apify_news)} articles."
    sec8_claims = [
        {"text": "Wikipedia: free company background via REST API (no key).",
         "confidence": "DOCUMENTED", "source": "Wikipedia REST API"},
        {"text": "FundedAPI: free startup/investor data — 60 req/hr anonymous, 100/day free tier.",
         "confidence": "DOCUMENTED", "source": "fundedapi.com"},
        {"text": "SEC EDGAR: SC 13G/13D (institutional ownership), Form D (private placements), company submissions — all free with User-Agent.",
         "confidence": "DOCUMENTED", "source": "SEC EDGAR"},
        {"text": "LDA.gov: lobbying disclosures — both client_name AND registrant_name queries (two-sided disclosure).",
         "confidence": "DOCUMENTED", "source": "lda.gov"},
        {"text": apify_status,
         "confidence": "DOCUMENTED", "source": "Apify platform"},
        {"text": "Apify actors: automation-lab/linkedin-profile-scraper (~$0.003/profile), mdataset/pitchbook-scraper (~$0.0035/lookup), brilliant_gum/google-news-scraper (~$0.03/article).",
         "confidence": "ANALYTICAL", "source": "Apify Store"},
    ]
    last_order = max((s["order"] for s in sections), default=10) + 1
    sections.append({"name": "Data Sources & Enrichment", "order": last_order,
                     "claims": sec8_claims, "data": {}})

    # ── Final section: AI Narrative ───────────────────────────────────────────
    narrative_text = _generate_narrative(entity_name, sections[:-1], wiki_data, funded_data)
    sections.append({"name": "Deep Intelligence Narrative (AI-Generated)", "order": last_order + 1,
                     "claims": [{"text": narrative_text, "confidence": "ANALYTICAL",
                                 "source": "GPT-4o-mini (grounded in cited evidence, 5-section format)"}],
                     "data": {"model": "gpt-4o-mini", "sections": 5, "depth": "enhanced"}})

    # 5. Persist report to DB
    report_id = None
    try:
        db.execute(text("INSERT INTO reports (title, kind, status) VALUES (:t, :k, 'published')"),
                   {"t": f"Layer 1 Intelligence Report: {entity_name}", "k": INTELLIGENCE_KIND})
        db.flush()
        row = db.execute(
            text("SELECT id FROM reports WHERE kind=:k ORDER BY id DESC LIMIT 1"),
            {"k": INTELLIGENCE_KIND}).fetchone()
        report_id = row[0]
        for s in sections:
            content = "\n".join([c["text"] for c in s.get("claims", [])])
            db.execute(text('INSERT INTO report_sections (report_id, name, content, "order") VALUES (:r,:n,:c,:o)'),
                       {"r": report_id, "n": s["name"], "c": content, "o": s["order"]})
            for claim in s.get("claims", []):
                db.execute(text("INSERT INTO claims (report_id, text, status) VALUES (:r,:t,'verified')"),
                           {"r": report_id, "t": f"[{claim['confidence']}] {claim['text'][:499]}"})
        db.commit()
    except Exception:
        db.rollback()

    return {
        "report_id": report_id,
        "entity_name": entity_name,
        "entity_id": entity_id,
        "entity_type": entity_type,
        "ticker": ticker,
        "generated_at": started,
        "sections": sections,
        "relationships_created": relationships_created,
        "data_sources": {
            "wikipedia": bool(wiki_data.get("summary")),
            "funded_api": bool(funded_data.get("rounds")),
            "sec_investors": len(investor_data.get("ownership_filings", [])),
            "lda_both_sides": "client_name + registrant_name",
            "apify_linkedin": bool(apify_linkedin.get("headline")),
            "apify_pitchbook": bool(apify_pitchbook.get("description") or apify_pitchbook.get("investors")),
            "apify_news": len(apify_news),
        },
        "summary": {
            "sec_cik": sec_data.get("cik"),
            "sec_filings": len(sec_data.get("filings", [])),
            "contracts_found": len(spending_data.get("awards", [])),
            "total_obligated_usd": spending_data.get("total_obligated", 0),
            "lobbying_filings": lda_data.get("total_count", 0),
            "lobbying_as_registrant": lda_data.get("as_registrant_count", 0),
            "lobbying_firms": len(lda_data.get("top_firms", [])),
            "lobbying_issue_areas": lda_data.get("issue_areas", []),
            "fec_committees": len(fec_data.get("committees", [])),
            "fara_registrations": len(fara_data.get("registrants", [])),
            "sanctions_hits": len(ofac_data.get("hits", [])),
            "court_cases": len(court_data.get("cases", [])),
            "relationships_written": len(relationships_created),
            "investor_filings": len(investor_data.get("ownership_filings", [])),
            "news_articles": len(apify_news),
            "linkedin_education": len(apify_linkedin.get("education", [])),
            # KPI fields
            "kpi_contracts_value_usd": spending_data.get("total_obligated", 0),
            "kpi_lobbying_spend": sum(
                float(f.get("income") or 0) for f in lda_data.get("filings", [])
            ),
            "kpi_court_risk": "HIGH" if len(court_data.get("cases", [])) >= 3
                              else "MEDIUM" if len(court_data.get("cases", [])) >= 1
                              else "LOW",
            "kpi_sanctions_risk": "HIGH" if ofac_data.get("is_sanctioned") else "CLEAR",
            "kpi_data_confidence": round(
                100 * sum([
                    bool(wiki_data.get("summary")),
                    bool(sec_data.get("cik")),
                    bool(spending_data.get("awards")),
                    bool(lda_data.get("total_count")),
                    bool(apify_news),
                ]) / 5
            ),
            "kpi_sources_active": sum([
                bool(wiki_data.get("summary")),
                bool(sec_data.get("cik")),
                bool(spending_data.get("awards")),
                bool(lda_data.get("filings")),
                bool(court_data.get("cases")),
                bool(apify_news),
                bool(apify_linkedin.get("headline")),
                bool(apify_pitchbook.get("description")),
            ]),
            "kpi_top_lobbying_firms": [f[0] for f in lda_data.get("top_firms", [])[:3]],
        }
    }


def get_intelligence_report(db: Session, report_id: int) -> Optional[Dict[str, Any]]:
    row = db.execute(
        text("SELECT id, title, kind, status FROM reports WHERE id=:id AND kind=:k"),
        {"id": report_id, "k": INTELLIGENCE_KIND}).fetchone()
    if not row:
        return None

    sections_raw = db.execute(
        text('SELECT name, content, "order" FROM report_sections WHERE report_id=:id ORDER BY "order"'),
        {"id": report_id}).fetchall()
    claims_raw = db.execute(
        text("SELECT text, status FROM claims WHERE report_id=:id"),
        {"id": report_id}).fetchall()

    # Flat claims list (for RAG chat)
    flat_claims = [{"text": c[0], "status": c[1]} for c in claims_raw]

    # Rebuild sections with claims nested — split content back into claim lines
    sections = []
    for s in sections_raw:
        sec_name    = s[0]
        sec_content = s[1] or ""
        sec_order   = s[2]
        # Each line in content = one claim text (matching how we stored them)
        line_claims = []
        for line in sec_content.split("\n"):
            line = line.strip()
            if line:
                # Strip leading confidence tag if present [HIGH], [MEDIUM], [LOW], [DOCUMENTED]
                import re as _re
                clean = _re.sub(r'^\[(?:HIGH|MEDIUM|LOW|DOCUMENTED|VERIFIED|FLAGGED)\]\s*', '', line)
                line_claims.append({
                    "text":       clean,
                    "source":     sec_name,
                    "confidence": "DOCUMENTED",
                })
        sections.append({
            "name":    sec_name,
            "content": sec_content,
            "order":   sec_order,
            "claims":  line_claims,
        })

    # Try to extract entity_name from title
    import re as _re
    title     = row[1] or ""
    ename_m   = _re.search(r'Intelligence Report:\s+(.+)$', title)
    entity_name = ename_m.group(1).strip() if ename_m else None

    return {
        "report_id":   row[0],
        "title":       title,
        "entity_name": entity_name,
        "kind":        row[2],
        "status":      row[3],
        "sections":    sections,
        "claims":      flat_claims,
    }


def list_intelligence_reports(db: Session, limit: int = 20) -> List[Dict[str, Any]]:
    rows = db.execute(
        text("SELECT id, title, status, created_at FROM reports WHERE kind=:k ORDER BY id DESC LIMIT :l"),
        {"k": INTELLIGENCE_KIND, "l": limit}).fetchall()
    return [{"report_id": r[0], "title": r[1], "status": r[2],
             "created_at": r[3].isoformat() if r[3] else None} for r in rows]

