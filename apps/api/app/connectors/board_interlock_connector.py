"""
Board interlocks and beneficial ownership, from Section 16 and Schedule 13
filings.

Two capabilities that commercial directories charge for, both derivable from
free SEC data:

  Interlocks (P-01). A person keeps one CIK for life, across every issuer they
  report at. So the issuers named in an individual's Form 3 filings are exactly
  the public companies where they have been an officer, director or 10% owner.
  Reading them back gives a director's other board seats without a directory
  subscription, and unlike a scraped biography it is the director's own sworn
  filing.

  Beneficial ownership (P-05). Schedule 13D and 13G disclose every holder above
  five percent. Unlike a 13F this includes strategic and insider blocks, and 13D
  specifically signals an intent to influence control, which 13G disclaims.

Note on the interlock question: Clayton Act section 8 prohibits a person from
sitting on the boards of two competitors, so an interlock search restricted to
an issuer's peer group is close to guaranteed to return nothing. The useful
search is across all of a director's seats, whatever the industry, which is
what this module does.
"""

import logging
import re
from collections import defaultdict
from datetime import date, timedelta
from html import unescape
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

from app.connectors.sec_http import sec_get_json, sec_get_text

logger = logging.getLogger(__name__)

# Section 16 filings are indexed under the XSL-rendered path. The raw XML sits
# beside it, one directory up, and is what carries the issuer identifiers.
_XSL_PREFIX = re.compile(r"^xsl[^/]*/")

_ISSUER_CIK = re.compile(r"<issuerCik>\s*([^<\s]+)", re.I)
_ISSUER_NAME = re.compile(r"<issuerName>\s*([^<]+)", re.I)
_ISSUER_SYMBOL = re.compile(r"<issuerTradingSymbol>\s*([^<]+)", re.I)
_IS_DIRECTOR = re.compile(r"<isDirector>\s*(1|true)", re.I)
_IS_OFFICER = re.compile(r"<isOfficer>\s*(1|true)", re.I)
_IS_TEN_PERCENT = re.compile(r"<isTenPercentOwner>\s*(1|true)", re.I)
_OFFICER_TITLE = re.compile(r"<officerTitle>\s*([^<]+)", re.I)

# Form 3 is filed once per issuer relationship, so it is the cheapest complete
# index of where a person has served. Form 5 catches the rare late filer.
_APPOINTMENT_FORMS = ("3", "5")


def _person_appointments(person_cik: str, max_filings: int = 30) -> Dict[str, Any]:
    """Every issuer where this person has filed an initial ownership statement."""
    padded = str(person_cik).lstrip("0").zfill(10)
    submissions = sec_get_json(
        f"https://data.sec.gov/submissions/CIK{padded}.json") or {}
    recent = submissions.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    if not forms:
        return {"name": submissions.get("name", ""), "seats": []}

    accessions = recent.get("accessionNumber", [])
    documents = recent.get("primaryDocument", [])
    dates = recent.get("filingDate", [])
    file_numbers = recent.get("fileNumber", [])

    # A Section 16 file number belongs to the issuer, so the latest filing
    # carrying it is the last time this person reported at that issuer. Form 3
    # records when a relationship began and nothing records when it ended, so
    # this is the only free indication of whether a seat is still held.
    last_seen: Dict[str, str] = {}
    for i, filed in enumerate(dates):
        key = file_numbers[i] if i < len(file_numbers) else ""
        if key and filed > last_seen.get(key, ""):
            last_seen[key] = filed

    # One filing per issuer file number. A person who has filed both a Form 3
    # and a late Form 5 at the same issuer only needs to be read once.
    candidates = []
    seen_files = set()
    for i, form in enumerate(forms):
        if form not in _APPOINTMENT_FORMS or i >= len(documents):
            continue
        key = file_numbers[i] if i < len(file_numbers) else accessions[i]
        if key and key in seen_files:
            continue
        seen_files.add(key)
        candidates.append((accessions[i], documents[i],
                           dates[i] if i < len(dates) else "",
                           last_seen.get(key, "")))
        if len(candidates) >= max_filings:
            break

    numeric_cik = str(int(person_cik))
    seats = []
    for accession, document, filed, last_filed in candidates:
        document = _XSL_PREFIX.sub("", document or "")
        if not document.endswith(".xml"):
            continue
        body = sec_get_text(
            f"https://www.sec.gov/Archives/edgar/data/{numeric_cik}/"
            f"{accession.replace('-', '')}/{document}")
        if not body:
            continue
        name = _ISSUER_NAME.search(body)
        if not name:
            continue
        roles = []
        if _IS_DIRECTOR.search(body):
            roles.append("Director")
        if _IS_OFFICER.search(body):
            roles.append("Officer")
        if _IS_TEN_PERCENT.search(body):
            roles.append("10% owner")
        title = _OFFICER_TITLE.search(body)
        issuer_cik = _ISSUER_CIK.search(body)
        symbol = _ISSUER_SYMBOL.search(body)
        ticker = unescape(symbol.group(1)).strip().upper() if symbol else ""
        seats.append({
            "issuer": unescape(name.group(1)).strip(),
            "issuer_cik": (issuer_cik.group(1).strip().lstrip("0")
                           if issuer_cik else ""),
            "ticker": ticker.strip("()") if ticker not in ("", "NONE") else "",
            "roles": roles,
            "title": unescape(title.group(1)).strip() if title else "",
            "first_filed": filed,
            "last_filed": last_filed or filed,
            "source_url": (f"https://www.sec.gov/Archives/edgar/data/"
                           f"{numeric_cik}/{accession.replace('-', '')}/{document}"),
        })

    return {"name": submissions.get("name", ""), "seats": seats}


def get_board_interlocks(
    insiders: List[Dict[str, Any]],
    issuer_cik: str,
    issuer_name: str = "",
    max_people: int = 16,
) -> Dict[str, Any]:
    """Other public-company seats held by this issuer's directors and officers.

    Args:
        insiders: Form 4 rows, which carry the reporting owner's own CIK.
        issuer_cik: The subject company, excluded from each person's seat list.
    """
    result: Dict[str, Any] = {
        "people": [],
        "interlocked_issuers": {},
        "shared_boards": [],
        "summary": {
            "people_checked": 0,
            "people_with_other_seats": 0,
            "distinct_other_issuers": 0,
            "max_seats_per_person": 0,
            "current_since": "",
        },
        "method": ("Issuers named in each person's Form 3 filings, which are "
                   "filed once per issuer relationship. Nothing in Section 16 "
                   "records a departure, so a seat is treated as current only "
                   "where the person has filed at that issuer within two years."),
    }

    # Two years spans an annual equity grant cycle, so a sitting director will
    # normally have filed at least once inside it.
    cutoff = (date.today() - timedelta(days=730)).isoformat()
    result["summary"]["current_since"] = cutoff

    # A person appears on many Form 4 rows; collapse to one entry each, keeping
    # the roles seen at this issuer.
    people: Dict[str, Dict[str, Any]] = {}
    for row in insiders or []:
        person_cik = str(row.get("insider_cik") or "").lstrip("0")
        if not person_cik:
            continue
        entry = people.setdefault(person_cik, {
            "name": row.get("insider", ""), "roles_here": set(), "rows": 0})
        entry["roles_here"].update(row.get("roles") or [])
        entry["rows"] += 1

    if not people:
        return result

    # Directors first: an interlock is a governance fact about a board, and a
    # non-director officer's outside seat is a weaker signal.
    ranked = sorted(
        people.items(),
        key=lambda kv: ("Director" not in kv[1]["roles_here"], -kv[1]["rows"]),
    )[:max_people]

    target = str(issuer_cik).lstrip("0")
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(_person_appointments, cik): (cik, meta)
                   for cik, meta in ranked}
        for future in as_completed(futures):
            person_cik, meta = futures[future]
            try:
                appointments = future.result()
            except Exception as error:
                logger.warning("Interlock lookup failed for %s: %s",
                               meta["name"], error)
                continue

            elsewhere = [s for s in appointments["seats"]
                         if s["issuer_cik"] != target
                         and s["issuer"].lower() != (issuer_name or "").lower()]
            result["summary"]["people_checked"] += 1
            if not elsewhere:
                continue
            for seat in elsewhere:
                seat["current"] = seat["last_filed"] >= cutoff
            result["people"].append({
                "name": appointments["name"] or meta["name"],
                "cik": person_cik,
                "roles_at_issuer": sorted(meta["roles_here"]),
                "other_seats": sorted(elsewhere,
                                      key=lambda s: s["last_filed"], reverse=True),
                "other_seat_count": len(elsewhere),
                "current_seat_count": sum(1 for s in elsewhere if s["current"]),
                "profile_url": (f"https://www.sec.gov/cgi-bin/browse-edgar?"
                                f"action=getcompany&CIK={person_cik}&type=3"),
            })

    result["people"].sort(
        key=lambda p: (p["current_seat_count"], p["other_seat_count"]), reverse=True)

    # An interlock is a live relationship. A seat the person last reported at in
    # 2007 says something about their history, not about this board's reach.
    by_issuer: Dict[str, List[str]] = defaultdict(list)
    for person in result["people"]:
        for seat in person["other_seats"]:
            if seat["current"]:
                by_issuer[seat["issuer"]].append(person["name"])

    # An issuer reached by two or more of this board is a shared board — the
    # interlock proper, rather than one director's unrelated outside seat.
    result["shared_boards"] = sorted(
        ({"issuer": issuer, "directors": sorted(set(names)),
          "director_count": len(set(names))}
         for issuer, names in by_issuer.items() if len(set(names)) >= 2),
        key=lambda s: s["director_count"], reverse=True)

    result["interlocked_issuers"] = {k: sorted(set(v)) for k, v in by_issuer.items()}
    result["summary"]["people_with_other_seats"] = len(result["people"])
    result["summary"]["distinct_other_issuers"] = len(by_issuer)
    result["summary"]["max_seats_per_person"] = max(
        (p["other_seat_count"] for p in result["people"]), default=0)
    return result


# ---------------------------------------------------------------------------
# P-05  Beneficial ownership above five percent
# ---------------------------------------------------------------------------

# Schedule 13 has no machine-readable form. Filers use one of three cover-page
# conventions: the numbered EDGAR shorthand, the printed cover page, or the
# Item 2 narrative. All three appear among the holders of any large issuer.
_HOLDER_PATTERNS = (
    re.compile(r"Item\s*2\(a\)[.:]?\s*Name of Person Filing[.:]?\s*(.{3,80}?)"
               r"\s*(?:Item|Address)", re.I | re.S),
    re.compile(r"Item\s*1:\s*Reporting Person\s*[-–]\s*(.{3,80}?)\s*Item", re.I | re.S),
    re.compile(r"NAMES?\s+OF\s+REPORTING\s+PERSONS?\s*[.:]?\s*(.{3,140}?)"
               r"\s*\(?\s*2\s*[.)]?\s*CHECK", re.I | re.S),
)

# The printed cover page interleaves the name with the filer's tax number, and
# the two are not separated by any markup once the tags are stripped.
_IRS_LABEL = re.compile(
    r"(?:I\.?R\.?S\.?\s*)?(?:or\s+)?(?:S\.?S\.?\s*)?(?:Employer\s*)?"
    r"Identification\s*(?:Nos?\.?|Numbers?)?\s*(?:of\s+above\s+persons?)?"
    r"\s*(?:\(entities\s+only\))?\s*[.:]?", re.I)
_IRS_NUMBER = re.compile(r"\b\d{2}-\d{7}\b")
# Whatever remains of the tax-number cell once the label and the number itself
# are gone: an empty placeholder, or the abbreviations either side of it.
_IRS_RESIDUE = re.compile(
    r"\((?:tax\s*id|ein|irs)[^)]*\)|^\s*(?:I\.?R\.?S\.?|S\.?S\.?|or)\s+", re.I)


def _clean_holder(name: str) -> str:
    name = _IRS_LABEL.sub(" ", name)
    name = _IRS_NUMBER.sub(" ", name)
    name = _IRS_RESIDUE.sub(" ", name)
    name = _IRS_RESIDUE.sub(" ", name)
    name = re.sub(r"^\W+", " ", name)
    name = re.sub(r"\s*\(?\d\)?(\([a-z]\))?\s*$", " ", name)
    name = re.sub(r"\s+", " ", name).strip(" .:,-–—")
    # What survives must read as a name, not as a leftover form label.
    if len(name) < 4 or not re.search(r"[A-Za-z]{3}", name):
        return ""
    if re.match(r"^(check|see|item|not applicable|n/?a)\b", name, re.I):
        return ""
    return name
_PERCENT_PATTERNS = (
    re.compile(r"Item\s*11:\s*(\d{1,2}(?:\.\d{1,3})?)\s*%", re.I),
    re.compile(r"PERCENT\s+OF\s+CLASS\s+REPRESENTED\s+BY\s+AMOUNT\s+IN\s+ROW"
               r"[^%\d]{0,40}(\d{1,2}(?:\.\d{1,3})?)\s*%", re.I | re.S),
    re.compile(r"percent(?:age)? of class[^%\d]{0,40}(\d{1,2}(?:\.\d{1,3})?)\s*%",
               re.I | re.S),
)
_SHARES_PATTERNS = (
    re.compile(r"Item\s*9:\s*([\d,]{4,})", re.I),
    re.compile(r"AGGREGATE\s+AMOUNT\s+BENEFICIALLY\s+OWNED\s+BY\s+EACH"
               r"\s+REPORTING\s+PERSON[^\d]{0,80}([\d,]{4,})", re.I | re.S),
)
_PURPOSE = re.compile(
    r"Item\s*4[.:]?\s*Purpose of (?:the )?Transaction[.:]?\s*(.{40,900})",
    re.I | re.S)
_TAG = re.compile(r"<[^>]+>")

# EDGAR indexes a Schedule 13 under both parties, so an issuer's submissions
# contain the schedules others filed about it and the schedules it filed about
# its own holdings in other public companies. Only the subject company line
# distinguishes them, and the second set is a finding in its own right.
_SUBJECT_PATTERNS = (
    re.compile(r"Item\s*1\(a\)[.:]?\s*Name of Issuer[.:]?\s*(.{3,80}?)"
               r"\s*Item\s*1\(b\)", re.I | re.S),
    # The cover page reads "(Amendment No. 10) ISSUER NAME (Name of Issuer)",
    # so the capture must not reach back across the preceding bracket.
    re.compile(r"([^()]{3,80}?)\s*\(\s*Name of Issuer\s*\)", re.I | re.S),
)


def _same_entity(left: str, right: str) -> bool:
    """Whether two rendered company names refer to the same registrant."""
    def key(value: str) -> str:
        value = re.sub(r"[^a-z0-9 ]", " ", value.lower())
        value = re.sub(r"\b(the|inc|corp|corporation|company|co|plc|ltd|"
                       r"limited|llc|lp|holdings?|group|class|common|stock)\b",
                       " ", value)
        return " ".join(value.split())

    a, b = key(left), key(right)
    return bool(a and b and (a == b or a.startswith(b) or b.startswith(a)))


def _first_match(patterns, text: str) -> Optional[str]:
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return match.group(1).strip()
    return None


def get_beneficial_owners(cik: str, lookback_filings: int = 40) -> Dict[str, Any]:
    """Holders above five percent, from Schedules 13D and 13G.

    A 13F shows what an investment manager reported holding at quarter end.
    Schedule 13 is a different disclosure: it is triggered by crossing five
    percent, it captures strategic and insider blocks a 13F never sees, and the
    D-versus-G distinction states whether the holder intends to influence
    control.
    """
    result: Dict[str, Any] = {
        "holders": [],
        "stakes_in_others": [],
        "activist_filings": 0,
        "passive_filings": 0,
        "source_url": None,
    }

    padded = str(cik).lstrip("0").zfill(10)
    submissions = sec_get_json(
        f"https://data.sec.gov/submissions/CIK{padded}.json") or {}
    recent = submissions.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    if not forms:
        return result
    registrant = submissions.get("name", "")

    result["source_url"] = (
        f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany"
        f"&CIK={padded}&type=SC+13")

    def collect(index: Dict[str, Any], into: List[Any]) -> None:
        rows = index.get("form", [])
        accessions = index.get("accessionNumber", [])
        documents = index.get("primaryDocument", [])
        dates = index.get("filingDate", [])
        for i, form in enumerate(rows):
            if not form.startswith("SC 13") or i >= len(documents):
                continue
            into.append((form, accessions[i], documents[i],
                         dates[i] if i < len(dates) else ""))
            if len(into) >= lookback_filings:
                return

    candidates: List[Any] = []
    collect(recent, candidates)

    # A bank files hundreds of structured-note prospectuses a week, so its
    # thousand most recent filings can contain no Schedule 13 at all while the
    # overflow index holds every one of them.
    if not candidates:
        for overflow in submissions.get("filings", {}).get("files", [])[:4]:
            page = sec_get_json(
                f"https://data.sec.gov/submissions/{overflow.get('name')}") or {}
            collect(page, candidates)
            if len(candidates) >= lookback_filings:
                break
    if not candidates:
        return result

    numeric_cik = str(int(cik))

    def read(entry):
        form, accession, document, filed = entry
        url = (f"https://www.sec.gov/Archives/edgar/data/{numeric_cik}/"
               f"{accession.replace('-', '')}/{document}")
        body = sec_get_text(url)
        if not body:
            return None
        # Entities have to be decoded before whitespace is normalised: filers
        # pad the cover page with runs of &#160;, which survive a split() as
        # non-breaking spaces and break every fixed-distance match.
        text = " ".join(unescape(_TAG.sub(" ", body)).split())

        holder = _clean_holder(_first_match(_HOLDER_PATTERNS, text) or "")
        subject = _clean_holder(_first_match(_SUBJECT_PATTERNS, text) or "")
        percent = _first_match(_PERCENT_PATTERNS, text)
        shares = _first_match(_SHARES_PATTERNS, text)
        purpose = _PURPOSE.search(text) if form.startswith("SC 13D") else None
        if not holder:
            return None
        return {
            "form": form,
            "filed": filed,
            "percent_of_class": float(percent) if percent else None,
            "shares": int(shares.replace(",", "")) if shares else None,
            "intent": ("influence control" if form.startswith("SC 13D")
                       else "passive"),
            "purpose": " ".join(purpose.group(1).split())[:400] if purpose else "",
            "holder": holder,
            "subject": subject,
            "inbound": not subject or _same_entity(subject, registrant),
            "source_url": url,
        }

    rows = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        for future in as_completed([executor.submit(read, c) for c in candidates]):
            try:
                row = future.result()
            except Exception:
                continue
            if row:
                rows.append(row)

    inbound = [r for r in rows if r["inbound"]]
    outbound = [r for r in rows if not r["inbound"]]

    for row in inbound:
        if row["form"].startswith("SC 13D"):
            result["activist_filings"] += 1
        else:
            result["passive_filings"] += 1

    # A holder amends its schedule annually, so the same name recurs. Only the
    # most recent statement describes the position as it now stands.
    def latest_by(key, entries):
        seen: Dict[str, Dict[str, Any]] = {}
        for row in sorted(entries, key=lambda r: r["filed"]):
            if row["percent_of_class"]:
                seen[(row[key] or "").lower()] = row
        return sorted(seen.values(),
                      key=lambda r: r["percent_of_class"], reverse=True)

    result["holders"] = latest_by("holder", inbound)
    result["stakes_in_others"] = latest_by("subject", outbound)
    return result
