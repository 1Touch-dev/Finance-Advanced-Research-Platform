"""
OpenSecrets Political Money Connector
────────────────────────────────────────────────────────────────────────────
Comprehensive political intelligence using OpenSecrets.org data:
  - Corporate PAC contributions
  - Individual executive donations
  - Lobbying expenditure details
  - Revolving door personnel
  - Industry political giving patterns
  - Political donation recipients

Uses OpenSecrets API (free tier available) + FEC data fallback.
API Key: Get free key at https://www.opensecrets.org/api/admin/index.php?function=signup
"""
import os
import re
import time
import logging
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import defaultdict

from app.connectors.entity_naming import entity_search_term, matches_entity

logger = logging.getLogger(__name__)

# OpenSecrets API
OPENSECRETS_API_KEY = os.getenv("OPENSECRETS_API_KEY", "")
OPENSECRETS_BASE = "https://www.opensecrets.org/api"

# FEC API (free, no key required but rate limited)
FEC_BASE = "https://api.open.fec.gov/v1"
FEC_API_KEY = os.getenv("FEC_API_KEY", "DEMO_KEY")

HEADERS = {"User-Agent": "FinanceIntelPlatform/1.0 research@example.com"}


def _safe_float(val) -> float:
    """Safely convert value to float."""
    if val is None:
        return 0.0
    try:
        return float(str(val).replace(",", "").replace("$", ""))
    except (ValueError, TypeError):
        return 0.0


# ── OpenSecrets API Functions ────────────────────────────────────────────────

def search_opensecrets_org(org_name: str) -> Dict[str, Any]:
    """
    Search OpenSecrets for organization data.
    Returns organization profile if found.
    """
    result = {
        "org_name": org_name,
        "org_id": None,
        "industry": None,
        "sector": None,
        "pac_total": 0,
        "lobbying_total": 0,
    }

    if not OPENSECRETS_API_KEY:
        logger.info("OPENSECRETS_API_KEY not set - using FEC fallback only")
        return result

    try:
        # GetOrgs API - search for organization
        params = {
            "apikey": OPENSECRETS_API_KEY,
            "org": org_name,
            "output": "json",
        }
        resp = requests.get(f"{OPENSECRETS_BASE}/", params={**params, "method": "getOrgs"}, timeout=15)

        if resp.ok:
            data = resp.json()
            orgs = data.get("response", {}).get("organization", [])
            if orgs:
                org = orgs[0] if isinstance(orgs, list) else orgs
                result["org_id"] = org.get("@attributes", {}).get("orgid")
                result["org_name"] = org.get("@attributes", {}).get("orgname")

    except Exception as e:
        logger.warning("OpenSecrets org search error: %s", e)

    return result


def fetch_opensecrets_pac(org_id: str, cycle: str = "2024") -> Dict[str, Any]:
    """
    Fetch PAC contribution data from OpenSecrets.
    """
    result = {
        "cycle": cycle,
        "total_contributions": 0,
        "dem_pct": 0,
        "rep_pct": 0,
        "recipients": [],
    }

    if not OPENSECRETS_API_KEY or not org_id:
        return result

    try:
        params = {
            "apikey": OPENSECRETS_API_KEY,
            "id": org_id,
            "cycle": cycle,
            "output": "json",
            "method": "orgSummary",
        }
        resp = requests.get(f"{OPENSECRETS_BASE}/", params=params, timeout=15)

        if resp.ok:
            data = resp.json()
            summary = data.get("response", {}).get("organization", {}).get("@attributes", {})
            result["total_contributions"] = _safe_float(summary.get("total"))
            result["dem_pct"] = _safe_float(summary.get("dems", "0").replace("%", ""))
            result["rep_pct"] = _safe_float(summary.get("repubs", "0").replace("%", ""))

    except Exception as e:
        logger.warning("OpenSecrets PAC fetch error: %s", e)

    return result


# ── FEC API Functions (Primary Data Source) ──────────────────────────────────

def search_fec_committee(org_name: str) -> List[Dict[str, Any]]:
    """
    Search FEC for PAC/committee by organization name.
    Returns list of matching committees.
    """
    committees = []

    try:
        params = {
            "api_key": FEC_API_KEY,
            "q": org_name,
            "per_page": 20,
        }
        resp = requests.get(f"{FEC_BASE}/names/committees/", params=params, headers=HEADERS, timeout=15)

        if resp.ok:
            for result in resp.json().get("results", []):
                committees.append({
                    "committee_id": result.get("id"),
                    "name": result.get("name"),
                })

    except Exception as e:
        logger.warning("FEC committee search error: %s", e)

    return committees


def fetch_fec_committee_details(committee_id: str) -> Dict[str, Any]:
    """
    Fetch detailed committee information from FEC.
    """
    result = {
        "committee_id": committee_id,
        "name": None,
        "designation": None,
        "organization_type": None,
        "party": None,
        "treasurer": None,
        "total_receipts": 0,
        "total_disbursements": 0,
        "cash_on_hand": 0,
        "cycles_active": [],
    }

    try:
        params = {"api_key": FEC_API_KEY}
        resp = requests.get(f"{FEC_BASE}/committee/{committee_id}/", params=params, headers=HEADERS, timeout=15)

        if resp.ok:
            data = resp.json().get("results", [{}])[0]
            result["name"] = data.get("name")
            result["designation"] = data.get("designation_full")
            result["organization_type"] = data.get("organization_type_full")
            result["party"] = data.get("party_full")
            result["treasurer"] = data.get("treasurer_name")
            result["cycles_active"] = data.get("cycles", [])

    except Exception as e:
        logger.warning("FEC committee details error: %s", e)

    return result


# Words appended to a sponsor's name to form its PAC name. Stripped before
# matching so "TARGET CORPORATION CITIZENS POLITICAL FORUM" resolves to Target
# while "OVER THE TARGET PAC" does not.
PAC_NAME_TOKENS = {
    "pac", "political", "action", "committee", "fund", "forum", "citizens",
    "federal", "employees", "employee", "good", "government", "affairs",
    "civic", "association", "voluntary", "nonpartisan", "inc", "of", "the",
    "for", "and", "&",
}


def find_company_pacs(entity_name: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Corporate PACs sponsored by a company.

    FEC search is a loose text match, so each candidate is confirmed against the
    company name with the PAC-naming words removed. Many companies sponsor no
    PAC at all, which is a finding rather than a failure.
    """
    if not FEC_API_KEY:
        return []

    try:
        resp = requests.get(
            f"{FEC_BASE}/committees/",
            params={"api_key": FEC_API_KEY, "q": entity_search_term(entity_name),
                    "per_page": 20, "sort": "-last_file_date"},
            headers=HEADERS, timeout=20)
        if not resp.ok:
            return []
    except Exception as e:
        logger.warning("FEC committee search failed for %s: %s", entity_name, e)
        return []

    committees = []
    for c in resp.json().get("results", []):
        name = c.get("name") or ""
        # PAC names often carry a parenthetical short form, as in "TARGET
        # CORPORATION CITIZENS POLITICAL FORUM (TARGETCITIZENS POLITICAL
        # FORUM)". Left in place, the closing bracket stops the suffix strip.
        stem = re.sub(r"\([^)]*\)", " ", name)
        words = re.sub(r"[,.]", " ", stem).split()
        while words and words[-1].lower() in PAC_NAME_TOKENS:
            words.pop()
        if not matches_entity(" ".join(words), entity_name):
            continue
        committees.append({
            "committee_id": c.get("committee_id"),
            "name": name,
            "type": c.get("committee_type_full"),
            "cycles": c.get("cycles") or [],
            "source_url": f"https://www.fec.gov/data/committee/{c.get('committee_id')}/",
        })
        if len(committees) >= limit:
            break
    return committees


def fetch_fec_contributions(committee_id: str, cycle: int = 2024) -> Dict[str, Any]:
    """
    Fetch PAC contributions to candidates from FEC.

    Accepts either an FEC committee ID or a company name; a name is resolved to
    the company's sponsored PACs first. Callers previously passed the entity
    name straight through as a committee ID, which the API silently ignored.
    """
    if not re.fullmatch(r"C\d{8}", (committee_id or "").strip().upper()):
        pacs = find_company_pacs(committee_id)
        if not pacs:
            return {
                "committee_id": None,
                "entity_name": committee_id,
                "cycle": cycle,
                "contributions": [],
                "total_amount": 0,
                "by_party": {"DEM": 0, "REP": 0, "OTHER": 0},
                "top_recipients": [],
                "committees_found": [],
                "note": "No corporate PAC registered with the FEC under this name.",
            }
        committee_id = pacs[0]["committee_id"]

    result = {
        "committee_id": committee_id,
        "cycle": cycle,
        "contributions": [],
        "total_amount": 0,
        "by_party": {"DEM": 0, "REP": 0, "OTHER": 0},
        "top_recipients": [],
    }

    try:
        params = {
            "api_key": FEC_API_KEY,
            "committee_id": committee_id,
            "two_year_transaction_period": cycle,
            "per_page": 100,
            "sort": "-disbursement_amount",
        }
        resp = requests.get(f"{FEC_BASE}/schedules/schedule_b/", params=params, headers=HEADERS, timeout=20)

        if resp.ok:
            recipient_totals = defaultdict(float)
            for contrib in resp.json().get("results", []):
                # Schedule B reports money paid out, keyed on disbursement_*.
                # The contribution_receipt_* fields belong to Schedule A
                # (money received), so reading them here yielded zero for every
                # committee regardless of activity.
                amount = _safe_float(contrib.get("disbursement_amount"))
                committee = contrib.get("recipient_committee") or {}
                recipient = (contrib.get("recipient_name")
                             or committee.get("name") or "Unknown")
                party = committee.get("party") or "OTHER"

                result["contributions"].append({
                    "recipient": recipient,
                    "amount": amount,
                    "date": contrib.get("disbursement_date"),
                    "party": party,
                    "purpose": contrib.get("disbursement_description", ""),
                })

                result["total_amount"] += amount
                recipient_totals[recipient] += amount

                # Party breakdown
                if party in ["DEM", "Democratic"]:
                    result["by_party"]["DEM"] += amount
                elif party in ["REP", "Republican"]:
                    result["by_party"]["REP"] += amount
                else:
                    result["by_party"]["OTHER"] += amount

            # Top recipients
            result["top_recipients"] = sorted(
                [{"recipient": k, "amount": v} for k, v in recipient_totals.items()],
                key=lambda x: x["amount"],
                reverse=True,
            )[:20]

    except Exception as e:
        logger.warning("FEC contributions fetch error: %s", e)

    return result


def fetch_individual_contributions(person_name: str, employer: str = "", cycle: int = 2024) -> Dict[str, Any]:
    """
    Fetch individual political contributions from FEC.
    Used for executive donation tracking.
    """
    result = {
        "person_name": person_name,
        "employer_filter": employer,
        "cycle": cycle,
        "contributions": [],
        "total_amount": 0,
        "by_party": {"DEM": 0, "REP": 0, "OTHER": 0},
        "recipients": [],
    }

    try:
        params = {
            "api_key": FEC_API_KEY,
            "contributor_name": person_name,
            "two_year_transaction_period": cycle,
            "per_page": 100,
            "sort": "-contribution_receipt_amount",
        }
        if employer:
            params["contributor_employer"] = employer

        resp = requests.get(f"{FEC_BASE}/schedules/schedule_a/", params=params, headers=HEADERS, timeout=20)

        if resp.ok:
            recipient_totals = defaultdict(float)
            for contrib in resp.json().get("results", []):
                amount = _safe_float(contrib.get("contribution_receipt_amount"))
                recipient = contrib.get("committee", {}).get("name", "Unknown")

                result["contributions"].append({
                    "recipient": recipient,
                    "amount": amount,
                    "date": contrib.get("contribution_receipt_date"),
                    "employer": contrib.get("contributor_employer"),
                    "occupation": contrib.get("contributor_occupation"),
                })

                result["total_amount"] += amount
                recipient_totals[recipient] += amount

            result["recipients"] = sorted(
                [{"recipient": k, "amount": v} for k, v in recipient_totals.items()],
                key=lambda x: x["amount"],
                reverse=True,
            )[:10]

    except Exception as e:
        logger.warning("FEC individual contributions error: %s", e)

    return result


# ── Lobbying Data ────────────────────────────────────────────────────────────

LDA_BASE = "https://lda.senate.gov/api/v1"


# Once the register refuses a caller it refuses every subsequent request from
# the same address, so retrying each of the seven yearly queries turns a dead
# source into seven minutes of backoff. The first exhausted retry trips this
# and the rest of the run skips the register and reports why.
_LDA_STATE: Dict[str, Any] = {"blocked": False, "reason": ""}


def reset_lda_circuit() -> None:
    """Clear the breaker. For tests and for long-lived processes."""
    _LDA_STATE.update(blocked=False, reason="")


def _lda_headers() -> Dict[str, str]:
    """Request headers for the Senate register, with a key when one is set.

    Anonymous callers are throttled by IP and then refused outright with a 403
    — which is how Lockheed's $131.2M and 410 filings became a silent zero
    between two runs fifteen minutes apart. A key is free from
    lda.senate.gov/api and raises the ceiling by roughly two orders of
    magnitude, so it is read from the environment when present.
    """
    headers = dict(HEADERS)
    key = os.getenv("LDA_API_KEY") or os.getenv("SENATE_LDA_API_KEY")
    if key:
        headers["Authorization"] = f"Token {key}"
    return headers


def _fetch_lda_page(params: Dict[str, Any], attempts: int = 4) -> Dict[str, Any]:
    """One page of LDA filings, retried on throttling and transient faults.

    403 is retried alongside the usual transient codes because the register
    uses it for throttling as well as for genuine refusal, and the two are
    indistinguishable from the response body.
    """
    if _LDA_STATE["blocked"]:
        return {}

    for attempt in range(attempts):
        try:
            resp = requests.get(f"{LDA_BASE}/filings/", params=params,
                                headers=_lda_headers(), timeout=30)
            if resp.ok:
                return resp.json()
            if resp.status_code in (403, 429, 500, 502, 503, 504):
                # An IP throttle needs longer than a transient server fault.
                base = 8 if resp.status_code in (403, 429) else 2
                wait = float(resp.headers.get("Retry-After") or 0) or base * (2 ** attempt)
                if attempt < attempts - 1:
                    logger.warning("LDA HTTP %s — retrying in %.0fs (%d/%d)",
                                   resp.status_code, wait, attempt + 1, attempts)
                    time.sleep(min(wait, 60))
                    continue
                if resp.status_code in (403, 429):
                    keyed = bool(os.getenv("LDA_API_KEY")
                                 or os.getenv("SENATE_LDA_API_KEY"))
                    _LDA_STATE.update(
                        blocked=True,
                        reason=(f"the Senate LDA register refused {attempts} "
                                f"requests with HTTP {resp.status_code}"
                                + ("" if keyed else
                                   " and no LDA_API_KEY is set — the key is "
                                   "free from lda.senate.gov/api and raises "
                                   "the anonymous rate ceiling")))
                    logger.warning("LDA circuit open: %s", _LDA_STATE["reason"])
                    return {}
            logger.warning("LDA HTTP %s: %s", resp.status_code, resp.text[:200])
            return {}
        except Exception as e:
            if attempt < attempts - 1:
                time.sleep(2 ** attempt)
                continue
            logger.warning("LDA fetch error: %s", e)
    return {}


def fetch_lobbying_summary(org_name: str, years: int = 7) -> Dict[str, Any]:
    """
    Fetch lobbying disclosures for a client from the Senate LDA register.

    The filter parameter is ``client_name``. A prior version passed
    ``filing_client_name``, which the API ignores — it silently returned the
    entire 54,000-filing database and the connector summed the first page of
    unrelated organisations, producing a fabricated total.

    Results are split into in-house spend (the company registering for itself)
    and outside firms retained on its behalf, mirroring the reference report's
    lobbying section. No API key is required.
    """
    result = {
        "org_name": org_name,
        "total_spend": 0.0,
        "in_house_spend": 0.0,
        "outside_firm_spend": 0.0,
        "filing_count": 0,
        "filings": [],
        "top_issues": [],
        "top_firms": [],
        "year_breakdown": {},
        "source_url": f"{LDA_BASE}/filings/?client_name={entity_search_term(org_name)}",
    }

    issue_counts = defaultdict(int)
    firm_totals = defaultdict(float)
    year_totals = defaultdict(float)
    # Filings and distinct reporting periods per year. LDA is filed quarterly
    # per registrant, so a year carrying one filing is a year we have partial
    # coverage of, not a year the client barely lobbied. Without this the
    # first year in the window anchors a growth rate that is an artefact.
    year_filings = defaultdict(int)
    year_periods = defaultdict(set)
    # Search on the distinctive short form: LDA matches client names literally,
    # so "NVIDIA Corporation" misses filings registered as plain "NVIDIA".
    search_name = entity_search_term(org_name)

    current_year = datetime.now().year
    for year in range(current_year - years + 1, current_year + 1):
        page = 1
        while page <= 10:  # LDA pages at 25; 250 filings/year is ample headroom
            data = _fetch_lda_page({
                "client_name": search_name,
                "filing_year": year,
                "page": page,
            })
            filings = data.get("results") or []
            if not filings:
                break

            for filing in filings:
                client = (filing.get("client") or {}).get("name", "") or ""
                # Guard against loose server-side matching on the client name.
                if not matches_entity(client, org_name):
                    continue

                amount = _safe_float(filing.get("income") or filing.get("expenses"))
                registrant = (filing.get("registrant") or {}).get("name", "Unknown")
                issues = [
                    li.get("general_issue_code_display")
                    for li in (filing.get("lobbying_activities") or [])
                ]
                # A registrant matching the client is in-house lobbying;
                # anything else is an outside firm retained by the company.
                is_in_house = matches_entity(registrant, org_name)

                result["filings"].append({
                    "registrant": registrant,
                    "client": client,
                    "amount": amount,
                    "year": str(year),
                    "period": filing.get("filing_period_display") or filing.get("filing_period"),
                    "filing_type": filing.get("filing_type_display"),
                    "in_house": is_in_house,
                    "issues": issues,
                    "url": filing.get("filing_document_url"),
                })

                result["total_spend"] += amount
                result["filing_count"] += 1
                year_totals[str(year)] += amount
                year_filings[str(year)] += 1
                period = (filing.get("filing_period_display")
                          or filing.get("filing_period"))
                if period:
                    year_periods[str(year)].add(str(period))
                firm_totals[registrant] += amount
                if is_in_house:
                    result["in_house_spend"] += amount
                else:
                    result["outside_firm_spend"] += amount

                for issue in issues:
                    if issue:
                        issue_counts[issue] += 1

            if not data.get("next"):
                break
            page += 1

    result["top_issues"] = sorted(issue_counts.items(), key=lambda x: -x[1])[:10]
    result["top_firms"] = sorted(
        [{"firm": k, "amount": v, "in_house": matches_entity(k, org_name)}
         for k, v in firm_totals.items()],
        key=lambda x: x["amount"],
        reverse=True,
    )[:10]
    result["year_breakdown"] = dict(sorted(year_totals.items()))
    result["year_filings"] = dict(sorted(year_filings.items()))
    result["year_periods"] = {y: len(p) for y, p in sorted(year_periods.items())}
    # A year is comparable when all four quarterly periods are present and it
    # is not the year currently in progress. Anything else is a coverage
    # artefact and must not anchor a growth rate.
    result["complete_years"] = sorted(
        y for y, periods in year_periods.items()
        if len(periods) >= 4 and int(y) < current_year)
    result["partial_years"] = sorted(
        y for y in year_totals
        if y not in set(
            y2 for y2, p in year_periods.items()
            if len(p) >= 4 and int(y2) < current_year))
    result["filings"].sort(key=lambda f: (f["year"], f["registrant"]), reverse=True)

    # A refusal and a genuine absence of lobbying produce the same empty
    # result, and only one of them is a fact about the issuer. Say which.
    if _LDA_STATE["blocked"] and not result["filing_count"]:
        result["error"] = _LDA_STATE["reason"]

    return result


# ── Revolving Door ───────────────────────────────────────────────────────────

def detect_revolving_door(company_name: str, executives: List[Dict] = None) -> List[Dict[str, Any]]:
    """
    Detect potential revolving door hires by analyzing executive backgrounds
    for prior government service.

    Checks career history for keywords indicating government roles.
    """
    revolving_door = []

    gov_keywords = [
        "department of", "secretary", "deputy secretary", "assistant secretary",
        "federal", "congress", "senate", "house of representatives", "staffer",
        "white house", "executive office", "agency", "bureau", "commission",
        "fcc", "ftc", "sec", "fda", "epa", "doj", "dod", "state department",
        "treasury", "commerce", "defense", "homeland", "va ", "hud", "usda",
        "ambassador", "appointed", "administration", "military", "army",
        "navy", "air force", "marine", "pentagon", "capitol hill",
    ]

    if not executives:
        return revolving_door

    for exec in executives:
        career = exec.get("career_history", []) or exec.get("experience", [])
        name = exec.get("name", "Unknown")

        for role in career:
            company = str(role.get("company", "")).lower()
            title = str(role.get("title", "")).lower()
            combined = f"{company} {title}"

            for keyword in gov_keywords:
                if keyword in combined:
                    # Check if this was before current role
                    end = role.get("end", "")
                    if end and end != "Present":
                        revolving_door.append({
                            "person": name,
                            "government_role": role.get("title"),
                            "government_entity": role.get("company"),
                            "dates": f"{role.get('start', 'Unknown')} - {end}",
                            "current_role": exec.get("current_role") or exec.get("title"),
                            "keyword_matched": keyword,
                            "concern_level": "HIGH" if any(
                                kw in combined for kw in ["secretary", "director", "commissioner", "appointed"]
                            ) else "MEDIUM",
                        })
                    break

    return revolving_door


# ── Main Intelligence Function ───────────────────────────────────────────────

def get_political_intelligence(company_name: str,
                                executives: List[Dict] = None,
                                cycles: List[int] = None) -> Dict[str, Any]:
    """
    Comprehensive political intelligence gathering.

    Returns:
    - PAC activity and contributions
    - Individual executive donations
    - Lobbying expenditure summary
    - Revolving door detection
    - Party split analysis
    """
    # FEC cycles are two-year periods labelled by the even year they end in.
    # A fixed list silently goes stale, so the current and two prior cycles are
    # derived from today's date.
    if not cycles:
        latest = datetime.utcnow().year
        latest += latest % 2
        cycles = [latest, latest - 2, latest - 4]

    result = {
        "company_name": company_name,
        "pac_activity": {
            "committee_found": False,
            "committee_id": None,
            "committee_name": None,
            "contributions_by_cycle": {},
            "total_all_cycles": 0,
            "party_split": {"DEM": 0, "REP": 0, "OTHER": 0},
            "top_recipients_all_time": [],
        },
        "executive_donations": [],
        "lobbying_summary": {},
        "revolving_door": [],
        "political_risk_assessment": {
            "partisan_lean": "NEUTRAL",
            "lobbying_intensity": "LOW",
            "revolving_door_count": 0,
            "overall_risk": "LOW",
        },
        "source": "FEC + LDA Senate",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    # Step 1: Find the sponsoring company's PAC. The validated resolver is used
    # rather than a raw name search, which returns any committee whose name
    # merely contains the word — "OVER THE TARGET PAC" for Target Corp.
    logger.info("Searching for PAC: %s", company_name)
    committees = find_company_pacs(company_name)

    if committees:
        committee_id = committees[0].get("committee_id")
        result["pac_activity"]["committee_found"] = True
        result["pac_activity"]["committee_id"] = committee_id
        result["pac_activity"]["committee_name"] = committees[0].get("name")

        # Fetch contributions for each cycle
        all_recipients = defaultdict(float)
        for cycle in cycles:
            contribs = fetch_fec_contributions(committee_id, cycle)
            result["pac_activity"]["contributions_by_cycle"][cycle] = {
                "total": contribs.get("total_amount", 0),
                "by_party": contribs.get("by_party", {}),
                "top_recipients": contribs.get("top_recipients", [])[:5],
            }

            result["pac_activity"]["total_all_cycles"] += contribs.get("total_amount", 0)
            result["pac_activity"]["party_split"]["DEM"] += contribs.get("by_party", {}).get("DEM", 0)
            result["pac_activity"]["party_split"]["REP"] += contribs.get("by_party", {}).get("REP", 0)
            result["pac_activity"]["party_split"]["OTHER"] += contribs.get("by_party", {}).get("OTHER", 0)

            for recip in contribs.get("top_recipients", []):
                all_recipients[recip["recipient"]] += recip["amount"]

        result["pac_activity"]["top_recipients_all_time"] = sorted(
            [{"recipient": k, "amount": v} for k, v in all_recipients.items()],
            key=lambda x: x["amount"],
            reverse=True,
        )[:20]

    # Step 2: Executive individual donations
    if executives:
        for exec in executives[:10]:
            name = exec.get("name", "")
            if name:
                exec_donations = fetch_individual_contributions(name, employer=company_name, cycle=2024)
                if exec_donations.get("total_amount", 0) > 0:
                    result["executive_donations"].append({
                        "executive": name,
                        "title": exec.get("title") or exec.get("current_role"),
                        "total_donated": exec_donations.get("total_amount", 0),
                        "recipients": exec_donations.get("recipients", [])[:5],
                    })

    # Step 3: Lobbying summary
    result["lobbying_summary"] = fetch_lobbying_summary(company_name)

    # Step 4: Revolving door detection
    if executives:
        result["revolving_door"] = detect_revolving_door(company_name, executives)

    # Step 5: Political risk assessment
    pac_total = result["pac_activity"]["total_all_cycles"]
    dem_total = result["pac_activity"]["party_split"]["DEM"]
    rep_total = result["pac_activity"]["party_split"]["REP"]
    total_partisan = dem_total + rep_total

    if total_partisan > 0:
        dem_pct = dem_total / total_partisan * 100
        rep_pct = rep_total / total_partisan * 100
        if dem_pct > 65:
            result["political_risk_assessment"]["partisan_lean"] = "STRONG_DEM"
        elif dem_pct > 55:
            result["political_risk_assessment"]["partisan_lean"] = "LEAN_DEM"
        elif rep_pct > 65:
            result["political_risk_assessment"]["partisan_lean"] = "STRONG_REP"
        elif rep_pct > 55:
            result["political_risk_assessment"]["partisan_lean"] = "LEAN_REP"
        else:
            result["political_risk_assessment"]["partisan_lean"] = "BALANCED"

    lobbying_total = result["lobbying_summary"].get("total_spend", 0)
    if lobbying_total > 10_000_000:
        result["political_risk_assessment"]["lobbying_intensity"] = "HIGH"
    elif lobbying_total > 1_000_000:
        result["political_risk_assessment"]["lobbying_intensity"] = "MEDIUM"

    result["political_risk_assessment"]["revolving_door_count"] = len(result["revolving_door"])

    # Overall risk
    risk_score = 0
    if result["political_risk_assessment"]["lobbying_intensity"] == "HIGH":
        risk_score += 30
    if len(result["revolving_door"]) >= 3:
        risk_score += 30
    if result["political_risk_assessment"]["partisan_lean"] in ["STRONG_DEM", "STRONG_REP"]:
        risk_score += 20

    result["political_risk_assessment"]["overall_risk"] = (
        "HIGH" if risk_score >= 50 else "MEDIUM" if risk_score >= 25 else "LOW"
    )

    return result


# ── Convenience exports ───────────────────────────────────────────────────────

def get_pac_contributions(company_name: str, cycle: int = 2024) -> Dict[str, Any]:
    """Simple PAC contribution lookup."""
    committees = search_fec_committee(f"{company_name} PAC")
    if committees:
        return fetch_fec_contributions(committees[0].get("committee_id"), cycle)
    return {"error": "No PAC found"}


def get_executive_donations(person_name: str, employer: str = "") -> Dict[str, Any]:
    """Individual donation lookup."""
    return fetch_individual_contributions(person_name, employer)


def get_lobbying(company_name: str) -> Dict[str, Any]:
    """Lobbying summary lookup."""
    return fetch_lobbying_summary(company_name)
