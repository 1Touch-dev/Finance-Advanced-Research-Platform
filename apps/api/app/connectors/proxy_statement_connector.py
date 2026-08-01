"""
Proxy Statement (DEF 14A) Intelligence Connector
────────────────────────────────────────────────────────────────────────────
Deep analysis of SEC DEF 14A proxy statements for governance intelligence:
  - Executive compensation (Summary Compensation Table)
  - Named Executive Officers (NEOs)
  - Board composition and committees
  - Director compensation
  - Related party transactions
  - Say-on-pay voting results
  - Beneficial ownership disclosure
  - Stock ownership guidelines

These filings are CRITICAL for understanding:
  - How much executives are paid (and structure)
  - Who sits on the board and their independence
  - Related party dealings and conflicts
  - Shareholder voting outcomes

Usage:
    from app.connectors.proxy_statement_connector import (
        get_proxy_intelligence,
        extract_executive_compensation,
        get_board_composition,
    )
    proxy = get_proxy_intelligence("NVDA")
"""
import os
import re
import time
import logging
import requests
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from bs4 import BeautifulSoup, NavigableString
import xml.etree.ElementTree as ET

from app.connectors.sec_http import sec_get

logger = logging.getLogger(__name__)

# SEC EDGAR headers
SEC_HEADERS = {"User-Agent": os.getenv("SEC_USER_AGENT", "FinanceIntelPlatform/1.0 research@example.com")}
EDGAR_BASE = "https://www.sec.gov"
EDGAR_DATA = "https://data.sec.gov"


def _get_cik_from_ticker(ticker: str) -> Optional[str]:
    """
    Resolve stock ticker to SEC CIK.

    Delegates to the shared cached resolver rather than scraping
    cgi-bin/browse-edgar, which is rate-limited and was failing often enough to
    empty this connector's output entirely.
    """
    from app.connectors.sec_edgar_connector import get_cik_from_ticker
    return get_cik_from_ticker(ticker)


def _neg_date(date_str: str) -> str:
    """Sort key placing later dates first."""
    return "".join(chr(255 - ord(c)) for c in (date_str or ""))


def _get_recent_proxies(cik: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Recent proxy filings for a CIK, definitive statements first.

    DEFA14A is *additional* soliciting material — typically a one-page letter or
    a vote reminder carrying no compensation or director tables. Because it is
    filed after the proxy it sorts first by date, so taking the most recent
    filings yielded supplements and left the board roster empty.
    """
    proxies = []
    try:
        url = f"{EDGAR_DATA}/submissions/CIK{cik}.json"
        resp = sec_get(url, timeout=15)

        if resp is not None and resp.ok:
            data = resp.json()
            filings = data.get("filings", {}).get("recent", {})

            forms = filings.get("form", [])
            accessions = filings.get("accessionNumber", [])
            dates = filings.get("filingDate", [])
            docs = filings.get("primaryDocument", [])

            for i, form in enumerate(forms):
                if form in ("DEF 14A", "DEFA14A", "DEFM14A"):
                    proxies.append({
                        "form_type": form,
                        "accession_number": accessions[i].replace("-", ""),
                        "filing_date": dates[i],
                        "primary_document": docs[i] if i < len(docs) else "",
                    })

            definitive = {"DEF 14A", "DEFM14A"}
            proxies.sort(key=lambda p: (p["form_type"] not in definitive,
                                        _neg_date(p["filing_date"])))
            proxies = proxies[:limit]

    except Exception as e:
        logger.warning("Error fetching proxy list for CIK %s: %s", cik, e)

    return proxies


def _fetch_proxy_document(cik: str, accession: str, doc_name: str = "") -> str:
    """Fetch proxy document HTML content."""
    try:
        # Build filing URL
        base_url = f"{EDGAR_BASE}/Archives/edgar/data/{int(cik)}/{accession}"

        if doc_name:
            url = f"{base_url}/{doc_name}"
        else:
            # Get filing index to find main document
            index_url = f"{base_url}/index.json"
            resp = sec_get(index_url, timeout=15)
            if resp is not None and resp.ok:
                index_data = resp.json()
                for item in index_data.get("directory", {}).get("item", []):
                    name = item.get("name", "")
                    if name.endswith(".htm") and "def14a" in name.lower():
                        url = f"{base_url}/{name}"
                        break
                else:
                    # Fallback to first HTML file
                    for item in index_data.get("directory", {}).get("item", []):
                        if item.get("name", "").endswith(".htm"):
                            url = f"{base_url}/{item['name']}"
                            break
                    else:
                        return ""
            else:
                return ""

        resp = sec_get(url, timeout=30)
        if resp is not None and resp.ok:
            return resp.text

    except Exception as e:
        logger.warning("Error fetching proxy document: %s", e)

    return ""


def _parse_money(text: str) -> float:
    """Parse monetary value from text."""
    if not text:
        return 0.0
    # Remove common formatting
    cleaned = re.sub(r'[,$\s\(\)]', '', str(text))
    cleaned = cleaned.replace('—', '0').replace('–', '0').replace('-', '0')
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


# A principal position set immediately below the name on the same table cell
# arrives with no separating whitespace: "Tim CookChief Executive Officer".
_TITLE_START_RE = re.compile(
    r"(?<=[a-z])(?=(?:Co-)?(?:Chief|President|Executive|Senior|Vice|Chair|"
    r"General|Managing|Group|Global|Head|Director|Founder|Treasurer|"
    r"Secretary|Interim|Former|EVP|SVP|CEO|CFO|COO|CTO|CAO|CLO)\b)")


# Words that only ever appear in a job title. A cell built solely from these is
# the principal-position line, not a person.
_TITLE_WORDS = {
    "chief", "executive", "officer", "president", "senior", "vice", "chair",
    "chairman", "chairperson", "general", "counsel", "managing", "director",
    "group", "global", "head", "founder", "treasurer", "secretary", "interim",
    "former", "and", "of", "the", "co", "evp", "svp", "ceo", "cfo", "coo",
    "cto", "cao", "clo", "principal", "financial", "operating", "technology",
    "accounting", "legal", "administrative", "marketing", "business",
}


def _is_title_only(value: str) -> bool:
    """Whether a cell holds a job title rather than a person's name."""
    words = re.findall(r"[A-Za-z]+", value or "")
    return bool(words) and all(w.lower() in _TITLE_WORDS for w in words)


def _split_name_and_title(value: str) -> tuple:
    """
    Separate an executive's name from a principal position run onto it.

    Split only where the following word begins a job title, so ordinary
    intercapped surnames such as McDonald or DeSantis are left alone.
    """
    text = " ".join((value or "").split())
    parts = _TITLE_START_RE.split(text, maxsplit=1)
    if len(parts) == 2:
        return parts[0].strip(" ,;-"), parts[1].strip()
    return text, ""


def _extract_compensation_table(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """
    Extract Summary Compensation Table from proxy statement.

    The Summary Compensation Table is required in all proxies and shows:
    - Name and Principal Position
    - Year
    - Salary
    - Bonus
    - Stock Awards
    - Option Awards
    - Non-Equity Incentive
    - Change in Pension/Deferred Comp
    - All Other Compensation
    - Total
    """
    compensation = []

    # Find tables that look like compensation tables
    tables = soup.find_all("table")

    for table in tables:
        # Look for header rows with compensation keywords
        header_text = " ".join(table.get_text()[:500].lower().split())

        if not any(kw in header_text for kw in ["salary", "stock awards", "total compensation", "summary compensation"]):
            continue

        # The Director Compensation table also carries a "Stock Awards" column
        # and appears earlier in most proxies, so matching on that alone
        # returned the board's retainers as though they were executive pay.
        # Only the Summary Compensation Table reports a salary; only the
        # director table reports fees.
        if "fees earned" in header_text and "salary" not in header_text:
            continue

        rows = table.find_all("tr")
        headers = []

        for row in rows:
            cells = row.find_all(["td", "th"])
            cell_texts = [c.get_text(strip=True) for c in cells]

            # Detect header row
            if any("salary" in c.lower() for c in cell_texts) or any("stock" in c.lower() for c in cell_texts):
                headers = cell_texts
                continue

            if not headers or len(cells) < 3:
                continue

            # Parse data row
            # First cell usually contains name and position
            name_cell = cell_texts[0] if cell_texts else ""

            # Extract name (usually first line or before any year)
            name_match = re.match(r'^([A-Za-z\.\s\-]+)', name_cell)
            name = name_match.group(1).strip() if name_match else name_cell
            name, title = _split_name_and_title(name)

            # Skip non-name rows
            if not name or name.lower() in ["name", "total", "(1)", "(2)", "year"]:
                continue
            if len(name) < 3 or name.isdigit():
                continue
            # The principal position is set on its own line beneath the name and
            # arrives as a separate row carrying the same figures, which would
            # otherwise double every executive.
            if _is_title_only(name) or not _looks_like_person(name):
                continue

            # Try to extract compensation values
            entry = {
                "name": name,
                "title": title,
                "year": "",
                "salary": 0,
                "bonus": 0,
                "stock_awards": 0,
                "option_awards": 0,
                "non_equity_incentive": 0,
                "other_compensation": 0,
                "total": 0,
            }

            # Map cells to headers
            for i, cell_text in enumerate(cell_texts[1:], 1):
                if i >= len(headers):
                    break

                header = headers[i].lower() if i < len(headers) else ""
                value = _parse_money(cell_text)

                # Detect year (usually 4-digit number)
                if re.match(r'20\d{2}', cell_text.strip()):
                    entry["year"] = cell_text.strip()[:4]
                elif "year" in header:
                    entry["year"] = cell_text.strip()[:4]
                elif "salary" in header:
                    entry["salary"] = value
                elif "bonus" in header:
                    entry["bonus"] = value
                elif "stock" in header:
                    entry["stock_awards"] = value
                elif "option" in header:
                    entry["option_awards"] = value
                elif "non-equity" in header or "incentive" in header:
                    entry["non_equity_incentive"] = value
                elif "other" in header:
                    entry["other_compensation"] = value
                elif "total" in header:
                    entry["total"] = value

            # Only add if we got meaningful data
            if entry["total"] > 0 or entry["salary"] > 0:
                compensation.append(entry)

    # Deduplicate by name+year
    seen = set()
    unique = []
    for entry in compensation:
        key = f"{entry['name']}_{entry['year']}"
        if key not in seen:
            seen.add(key)
            unique.append(entry)

    return unique


# Rows that look like people but are not directors.
_NON_DIRECTOR_TERMS = (
    "total", "company", "committee", "stock", "shares", "compensation",
    "aggregate", "average", "director compensation", "name", "all other",
    "executive officer", "nominee for", "beneficial owner",
    # Section headings and contents-page entries. A proxy's navigation
    # furniture is title-cased exactly like a name, so "Board Performance
    # Assessment" satisfies the name pattern and enters the roster as a
    # director unless the heading vocabulary is excluded outright.
    "board", "governance", "leadership", "attendance", "performance",
    "assessment", "biographies", "biography", "information", "structure",
    "overview", "summary", "proposal", "election", "voting", "vote",
    "meeting", "independence", "qualifications", "skills", "matrix",
    "report of", "letter", "table of", "contents", "appendix", "annex",
    "policy", "policies", "guidelines", "oversight", "engagement",
    "highlights", "practices", "responsibilities", "frequently",
    # Additional section headers commonly parsed as names
    "director nominees", "nominees", "ceo pay", "pay ratio", "pay versus",
    "executive compensation", "stockholder", "shareholder", "fiscal year",
    "annual meeting", "corporate responsibility", "sustainability",
    "environmental", "social", "esg", "diversity", "inclusion",
    "risk management", "cybersecurity", "audit", "nominating",
)

# Matched on word boundaries rather than as substrings: "Boardman" and
# "Letterman" are surnames that contain heading words, and a substring test
# would drop the director to exclude the heading.
_NON_DIRECTOR_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(t) for t in _NON_DIRECTOR_TERMS) + r")\b",
    re.I)

_NAME_RE = re.compile(r"^[A-Z][A-Za-z.'\-]+(?:\s+(?:[A-Z]\.|[A-Z][A-Za-z.'\-]+|van|von|de|di|del|la))*"
                      r"(?:,?\s+(?:Jr|Sr|II|III|IV|Ph\.?D|M\.?D)\.?)?$")


# Table cells carry footnote markers against the name, and some filers write
# the name with an honorific throughout ("Mr. Quincey*").
_FOOTNOTE_RE = re.compile(r"\s*(?:[*†‡§¶]+|\(\d+\)|\d)\s*$")
_HONORIFIC_RE = re.compile(r"^(?:Mr|Mrs|Ms|Miss|Dr|Prof|Sir|Hon)\.?\s+", re.I)


def _clean_person_cell(value: str) -> str:
    """A name cell with layout padding, footnote markers and honorifics removed."""
    text = " ".join(_INVISIBLE_RE.sub(" ", value or "").split())
    text = _FOOTNOTE_RE.sub("", text)
    return _HONORIFIC_RE.sub("", text).strip()


def _looks_like_person(value: str) -> bool:
    """Whether a table cell holds a person's name."""
    text = _clean_person_cell(value)
    if not (4 <= len(text) <= 48) or len(text.split()) < 2:
        return False
    if _NON_DIRECTOR_RE.search(text):
        return False
    return bool(_NAME_RE.match(text))


# Filers pad table cells with zero-width and non-breaking spaces for layout.
# They survive whitespace normalisation and leave cells that look populated but
# hold nothing, which shifts every column read by position.
_INVISIBLE_RE = re.compile(r"[\u200b\u200c\u200d\u2060\ufeff\xa0]")


def _table_rows(table) -> List[List[str]]:
    """Table as a list of trimmed cell-text rows."""
    rows = []
    for tr in table.find_all("tr"):
        cells = [" ".join(_INVISIBLE_RE.sub(" ", td.get_text()).split())
                 for td in tr.find_all(["td", "th"])]
        cells = [c for c in cells if c not in ("", "$", "—", "-")]
        if cells:
            rows.append(cells)
    return rows


def _extract_directors_from_comp_table(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """
    Director roster from the Director Compensation table.

    Every proxy carries this table under Item 402(k) and it lists the full
    board, one director per row, which makes it a far more reliable roster than
    prose in the election-of-directors narrative.
    """
    directors = []
    for table in soup.find_all("table"):
        header = " ".join(table.get_text()[:400].lower().split())
        if "fees earned" not in header and "director compensation" not in header:
            continue

        for cells in _table_rows(table):
            if not _looks_like_person(cells[0]):
                continue
            fees = None
            for cell in cells[1:]:
                digits = re.sub(r"[^\d.]", "", cell)
                if digits and re.match(r"^[\d,.$ ]+$", cell):
                    try:
                        fees = float(digits)
                    except ValueError:
                        pass
                    break
            directors.append({
                "name": _clean_person_cell(cells[0]),
                "fees_earned": fees,
                "source": "Director Compensation table",
            })
        if directors:
            break
    return directors


def _name_key(name: str) -> str:
    """Match a director across tables that disagree on case and punctuation."""
    return re.sub(r"[^a-z ]", "", (name or "").lower()).strip()


def _valid_age(value: Any) -> Optional[int]:
    """
    An age, or None.

    Column positions drift between issuers, so an unguarded read lands a
    four-digit year in the age field. Directors are adults and not yet
    centenarians, which separates the two unambiguously.
    """
    try:
        age = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return age if 25 <= age <= 100 else None


def _valid_year(value: Any) -> Optional[int]:
    """A year of first election, or None."""
    try:
        year = int(str(value).strip()[:4])
    except (TypeError, ValueError):
        return None
    return year if 1900 <= year <= datetime.now().year else None


# Independence and financial-expert columns are marked with a tick, which
# survives text extraction as a wingdings letter rather than a checkbox.
_TICK_CHARS = {"ü", "✓", "✔", "x", "X", "•", "yes", "Yes", "YES"}


def _extract_nominee_summary(soup: BeautifulSoup) -> Dict[str, Dict[str, Any]]:
    """
    Director attributes from the nominee summary table.

    Proxies carry a single table summarising the slate — one row per nominee,
    with age, year first elected, independence and committee seats as columns.
    It is the only place those attributes appear in structured form; the
    compensation table used for the roster carries none of them.
    """
    profiles: Dict[str, Dict[str, Any]] = {}

    for table in soup.find_all("table"):
        rows = _table_rows(table)
        header = next((r for r in rows if any(c.strip().lower() == "age" for c in r)), None)
        if not header or not any(re.search(r"director\s+since|^since$", c, re.I)
                                 for c in header):
            continue

        index = {}
        for position, cell in enumerate(header):
            label = cell.strip().lower()
            if label == "name":
                index["name"] = position
            elif label == "age":
                index["age"] = position
            elif re.search(r"director\s+since|^since$", label):
                index["since"] = position
            elif label.startswith("occupation") or "principal position" in label:
                index["occupation"] = position
            elif label.startswith("independent"):
                index["independent"] = position
            elif "financial expert" in label:
                index["financial_expert"] = position
            elif "committee" in label:
                index["committees"] = position
        if "age" not in index or "since" not in index:
            continue

        for cells in rows:
            if cells is header or not cells:
                continue
            name = cells[index.get("name", 0)] if index.get("name", 0) < len(cells) else ""
            if not _looks_like_person(name):
                continue

            def cell_at(key):
                position = index.get(key)
                if position is None or position >= len(cells):
                    return None
                return cells[position].strip() or None

            # Tick columns collapse when a director is not marked, shifting
            # later cells left. Age and tenure are read positionally because
            # they are always populated; the ticks are detected by content.
            profile = profiles.setdefault(_name_key(name), {"name": name})
            if _valid_age(cell_at("age")) is not None:
                profile["age"] = _valid_age(cell_at("age"))
            if _valid_year(cell_at("since")) is not None:
                profile["since"] = _valid_year(cell_at("since"))
            if cell_at("occupation"):
                profile["occupation"] = cell_at("occupation")
            if any(c.strip() in _TICK_CHARS for c in cells[index.get("age", 0) + 1:]):
                profile["is_independent"] = True
            committees = cell_at("committees")
            if committees and not re.fullmatch(r"[üx✓✔\d\s]*", committees, re.I):
                profile["committees"] = [c.strip() for c in committees.split(",") if c.strip()]

    return profiles


# A bio card states these as labelled fields before the narrative paragraph.
_BIO_LABELS = ("Age", "Director Since", "Committees", "Committee Membership",
               "Other Current Public Company Boards", "Other Public Company Boards")
_BIO_LABEL_RE = re.compile(
    r"(" + "|".join(_BIO_LABELS) + r")\s*:\s*(.*?)(?=\s*(?:" +
    "|".join(_BIO_LABELS) + r")\s*:|$)", re.I | re.S)

# Badges printed between the labelled fields and the biography.
_BOARD_STOP_RE = re.compile(
    r"\s*(?:Independent Director|Financial Expert|Lead Director|Chairperson|"
    r"Board Chair)\b", re.I)


def _extract_director_bios(soup: BeautifulSoup) -> Dict[str, Dict[str, Any]]:
    """
    Narrative biographies from the per-director cards in the proxy.

    Each nominee is presented in a card holding the name, current occupation,
    labelled attributes and a prose career history. The prose is what turns a
    roster into a dossier, and it exists nowhere else in the filing.
    """
    bios: Dict[str, Dict[str, Any]] = {}

    for table in soup.find_all("table"):
        rows = _table_rows(table)
        if not rows or not rows[0]:
            continue
        heading = rows[0][0].strip()
        # The card leads with the name alone, set in capitals.
        if not (heading.isupper() and 4 < len(heading) < 60
                and _looks_like_person(heading.title())):
            continue

        flat = " ".join(" ".join(c for c in r) for r in rows)
        entry: Dict[str, Any] = {"name": heading.title()}

        for label, value in _BIO_LABEL_RE.findall(flat):
            value = " ".join(value.split()).strip(" .;")
            label = label.lower()
            if label == "age" and _valid_age(value[:3]) is not None:
                entry["age"] = _valid_age(value[:3])
            elif label == "director since" and _valid_year(value) is not None:
                entry["since"] = _valid_year(value)
            elif label.startswith("committee") and value.lower() != "none":
                entry["committees"] = [c.strip() for c in value.split(",") if c.strip()]
            elif label.startswith("other"):
                # This is the last labelled field on the card, so the capture
                # runs on into the biography. Cut at the badges that separate
                # the two, and treat anything still overlong as unparsed.
                value = _BOARD_STOP_RE.split(value, maxsplit=1)[0].strip(" .;,")
                if value and value.lower() != "none" and len(value) < 160:
                    entry["other_boards"] = value

        if len(rows) > 1 and rows[1]:
            entry["occupation"] = rows[1][0]
        if "Independent Director" in flat:
            entry["is_independent"] = True
        if "Lead Director" in flat:
            entry["is_lead_director"] = True
        if "Financial Expert" in flat:
            entry["is_financial_expert"] = True

        # Section headings are also set in capitals and read as plausible
        # names ("Performance Goals", "In Memoriam"). A card always states at
        # least one labelled attribute; a heading never does.
        if not any(field in entry for field in ("age", "since", "committees",
                                                "other_boards")):
            continue

        # The biography is the longest run of prose in the card: labelled
        # fields and headings are short, the career history is not.
        sentences = max((c for r in rows for c in r), key=len, default="")
        if len(sentences) > 120:
            # Adjacent block elements concatenate without whitespace, running
            # the last word of one paragraph into the first of the next.
            entry["biography"] = re.sub(r"(?<=[a-z.])\.(?=[A-Z])", ". ",
                                        " ".join(sentences.split()))

        bios[_name_key(heading)] = entry

    return bios


# A biography narrates a career, so it contains these constructions. Boilerplate
# and vote instructions surrounding the roster do not.
_BIO_MARKERS = re.compile(
    r"\b(?:has served|has been|served as|serves as|is the|was the|joined|"
    r"prior to joining|previously|retired|founded|co-founded|holds a|"
    r"received (?:a|his|her)|earned (?:a|his|her)|graduated)\b", re.I)


# Structural furniture of a proxy statement. A biography that runs into any of
# these has overrun its subject and is picking up the document around it.
_BIO_BOILERPLATE = re.compile(
    r"Table\s*of\s*Contents|PROXY\s+STATEMENT|ANNUAL\s+MEETING\s+OF\s+STOCKHOLDERS"
    r"|Your\s+proxy\s+is\s+being\s+solicited|Notice\s+of\s+Annual\s+Meeting"
    r"|record\s+date|virtualshareholdermeeting|Information\s+About\s+the"
    r"|VOTE\s+BY|Beneficial\s+Owner|Board\s+Recommends",
    re.I,
)

# Language marking someone as no longer serving. Such a person can still appear
# in the Director Compensation table for fees paid during the year, and would
# otherwise inflate the current roster.
_FORMER_DIRECTOR = re.compile(
    r"served\s+as\s+[^.]{0,60}member\s+of\s+(?:our|the)\s+Board\s+from\s+\d{4}\s+to\s+\d{4}"
    r"|did\s+not\s+stand\s+for\s+re-?election"
    r"|will\s+not\s+stand\s+for\s+re-?election"
    r"|retired\s+from\s+(?:our|the)\s+Board"
    r"|stepped\s+down\s+from\s+(?:our|the)\s+Board"
    r"|until\s+(?:his|her|their)\s+retirement",
    re.I,
)


def is_former_director(text: str) -> bool:
    """Whether a passage describes someone who has left the board."""
    return bool(_FORMER_DIRECTOR.search(text or ""))


def _extract_bio_from_text(name: str, text: str, others: List[str]) -> Optional[str]:
    """
    A director's biography from the running text of the proxy.

    Most issuers set biographies as prose under a name heading rather than in
    the per-director card NVIDIA uses, and the card parser finds nothing in
    those filings. Here the text following each occurrence of the name is taken
    up to the point another director is introduced.
    """
    best = None
    for match in re.finditer(re.escape(name), text):
        window = text[match.end():match.end() + 2500]

        # Stop where the next director's entry begins, so one biography is not
        # concatenated with the following one. The subject's own name recurring
        # marks the start of their summary sidebar, which repeats the same
        # facts without spacing and reads as noise.
        cut = len(window)
        for other in list(others) + [name]:
            position = window.find(other)
            if 0 <= position < cut:
                cut = position

        # Also stop at the document's own furniture. A departed director is
        # named in a farewell passage that no other director's name follows,
        # so without this the window runs on into the notice of meeting and
        # the address block and reports them as biography.
        boilerplate = _BIO_BOILERPLATE.search(window)
        if boilerplate and boilerplate.start() < cut:
            cut = boilerplate.start()
        window = window[:cut].strip(" ,;:—-")

        if len(window) < 200 or not _BIO_MARKERS.search(window[:400]):
            continue
        # End on a sentence boundary rather than mid-clause.
        last_stop = window.rfind(". ")
        if last_stop > 200:
            window = window[:last_stop + 1]
        if best is None or len(window) > len(best):
            best = window

    if best:
        # The capture begins after the name, so the biography opens on its
        # verb: "is the former Chairman of UPS". Restoring the subject makes
        # it a sentence.
        if best[0].islower():
            best = f"{name} {best}"
        best = re.sub(r"(?<=[a-z.])\.(?=[A-Z])", ". ", best)
    return best


def _extract_board_composition(soup: BeautifulSoup) -> Dict[str, Any]:
    """
    Board of directors: roster, ages, tenure, independence and committees.

    The roster is taken from the Director Compensation table rather than by
    pattern-matching capitalised words in the document text. The previous
    approach matched any two adjacent capitalised words, so it caught headings
    and firm names as readily as directors.
    """
    board = {
        "directors": [],
        "committees": {"audit": [], "compensation": [], "nominating": [], "other": []},
        "independence_ratio": 0.0,
        "avg_tenure_years": 0.0,
    }

    board["directors"] = _extract_directors_from_comp_table(soup)
    text = " ".join(soup.get_text().split())

    # Attributes and biographies come from the nominee summary table and the
    # per-director cards. The card is preferred where both carry a field: it
    # states each value against an explicit label, whereas the summary table
    # relies on column position and drifts when a tick column is blank.
    summary = _extract_nominee_summary(soup)
    bios = _extract_director_bios(soup)

    # Directors who left during the year appear in the compensation table but
    # not on the slate; nominees appointed since appear only on the slate.
    # The compensation-table path filters its rows through _looks_like_person;
    # these two do not, and a contents page read as a nominee summary put five
    # section headings on Lockheed's board. The same test is applied here so a
    # heading cannot reach the roster by the side door.
    for key, profile in {**summary, **bios}.items():
        if not _looks_like_person(profile.get("name") or ""):
            continue
        if not any(_name_key(d["name"]) == key for d in board["directors"]):
            board["directors"].append({"name": profile["name"], "fees_earned": None,
                                       "source": "Director nominee disclosure"})

    for director in board["directors"]:
        key = _name_key(director["name"])
        for field, value in {**summary.get(key, {}), **bios.get(key, {})}.items():
            if field != "name" and value is not None:
                director.setdefault(field, value)

    # Issuers that do not use per-director cards yield no biography above.
    roster = [d["name"] for d in board["directors"]]
    for director in board["directors"]:
        if director.get("biography"):
            continue
        others = [n for n in roster if n != director["name"]]
        biography = _extract_bio_from_text(director["name"], text, others)
        if biography:
            director["biography"] = biography

    # Someone paid director fees during the year may have left the board before
    # the proxy was filed. They belong in the compensation record but not in the
    # current roster, and counting them overstates the board.
    for director in board["directors"]:
        context = " ".join(
            text[m.start():m.start() + 300]
            for m in re.finditer(re.escape(director["name"]), text)
        )
        if is_former_director(context):
            director["is_former"] = True

    # Enrich each director with age, tenure and independence stated near their
    # name elsewhere in the proxy.
    current_year = datetime.now().year
    for director in board["directors"]:
        surname = director["name"].split()[-1]
        for match in re.finditer(re.escape(director["name"]), text):
            window = text[match.start():match.start() + 400]
            # Summary sidebars run their labels together with the preceding
            # word ("David P. AbneyAge 70Director since 2021"), so the label
            # cannot be required to start on a word boundary.
            if director.get("age") is None:
                age = re.search(r"Age[:\s]*(\d{2})(?!\d)", window, re.IGNORECASE)
                if age and _valid_age(age.group(1)) is not None:
                    director["age"] = _valid_age(age.group(1))
            if director.get("since") is None:
                since = re.search(r"Director since[:\s]*((?:19|20)\d{2})",
                                  window, re.IGNORECASE)
                if since and _valid_year(since.group(1)) is not None:
                    director["since"] = _valid_year(since.group(1))
            if director.get("is_independent") is None and "independent" in window.lower():
                director["is_independent"] = True
            if director.get("age") and director.get("since"):
                break
        director.setdefault("age", None)
        director.setdefault("since", None)
        director.setdefault("is_independent", None)

        # Committee seats stated on the director's own card are authoritative;
        # the abbreviations used there vary by issuer, so they are matched on
        # the initial letter of the committee name.
        for seat in director.get("committees") or []:
            initials = re.sub(r"[^A-Z]", "", seat)
            for committee, letter in (("audit", "A"), ("compensation", "C"),
                                      ("nominating", "N")):
                if (initials.startswith(letter) or committee in seat.lower()) and \
                        director["name"] not in board["committees"][committee]:
                    board["committees"][committee].append(director["name"])
                    break

        # Committee membership, read from the committee roster tables.
        for committee in ("audit", "compensation", "nominating"):
            pattern = re.compile(
                rf"{committee}[^.]{{0,80}}committee[^.]{{0,600}}", re.IGNORECASE)
            for block in pattern.finditer(text):
                if surname in block.group(0):
                    if director["name"] not in board["committees"][committee]:
                        board["committees"][committee].append(director["name"])
                    break

    tenures = [current_year - d["since"] for d in board["directors"] if d.get("since")]
    if tenures:
        board["avg_tenure_years"] = round(sum(tenures) / len(tenures), 1)

    if board["directors"]:
        independent = sum(1 for d in board["directors"] if d.get("is_independent"))
        board["independence_ratio"] = round(independent / len(board["directors"]), 2)

    return board



# Item 404 of Regulation S-K requires an issuer to describe transactions with
# directors, officers, 5% holders and their immediate families. The disclosure
# is prose, so each statement is classified rather than pattern-matched to a
# table.
_RPT_HEADING = re.compile(
    r"(transactions?\s+with\s+related\s+persons?|"
    r"certain\s+relationships\s+and\s+related\s+(?:person\s+)?transactions?|"
    # Apple titles the section "Related Party Policy and Transactions", so the
    # two words cannot be required to be adjacent.
    r"related\s+(?:party|person)\s+(?:policy\s+and\s+)?transactions?)", re.I)

# Where the section ends. Item 404 is short and always followed by another
# proxy heading; without a stop the read runs into compensation tables.
_RPT_END = re.compile(
    r"(security\s+ownership|equity\s+compensation\s+plan|audit\s+committee\s+report|"
    r"proposal\s+\d|principal\s+account(?:ant|ing)\s+fees|delinquent\s+section\s+16|"
    r"report\s+of\s+the\s+compensation|stockholder\s+proposals?\s+for|"
    r"compensation\s+discussion\s+and\s+analysis|summary\s+compensation\s+table|"
    r"director\s+compensation|pay\s+(?:versus|ratio)|outstanding\s+equity\s+awards|"
    r"deferred\s+compensation|potential\s+payments\s+upon|"
    r"questions?\s+and\s+answers|general\s+information\s+about)", re.I)

# Vocabulary that only appears in an Item 404 disclosure. Used to choose
# between candidate headings, since the phrase also appears in the contents
# page and in the governance policy that describes how such transactions are
# reviewed — neither of which is the disclosure itself.
_RPT_BODY_SIGNAL = re.compile(
    r"(immediate family|related person|beneficial owner of (?:more than )?5|"
    r"5% (?:stock)?holder|is employed by|entered into an agreement with|"
    r"indemnity agreement|arm'?s.length|no charge|"
    r"contracts with entities|has a (?:direct or indirect )?material interest|"
    r"there has not been.{0,40}any transaction|paid .{0,30}approximately \$)", re.I)

# Compensation vocabulary. A candidate section dense in this is the executive
# compensation discussion, not Item 404 — that misread put Walmart's deferred
# salary elections and Coca-Cola's TSR modifiers into the related-party list.
_COMP_SIGNAL = re.compile(
    r"(PSUs?\b|RSUs? granted|TSR|vesting|performance period|"
    r"annual incentive|base salary of|target bonus|payout|"
    r"audit fees|tax fees|grant date fair value)", re.I)

_FAMILY = re.compile(
    r"\b(daughter|son|child|children|spouse|wife|husband|brother|sister|"
    r"father|mother|parent|sibling|in-law|nephew|niece|cousin|"
    r"immediate family member|family member|relative)\b", re.I)

_ENTITY = re.compile(
    r"\b([A-Z][\w.&'-]*(?:\s+[A-Z][\w.&'’-]*){0,4}\s*,?\s*"
    r"(?:Inc\.?|LLC|L\.L\.C\.|Corp\.?|Corporation|Company|Foundation|"
    r"Trust|Partners|L\.P\.|LP|Ltd\.?|Holdings|Ventures|Capital))\b")

_AMOUNT = re.compile(r"\$\s?([\d,]+(?:\.\d+)?)\s*(billion|million|thousand)?", re.I)
_SCALE = {"billion": 1e9, "million": 1e6, "thousand": 1e3, None: 1.0}

# Indemnity agreements and director equity grants appear in every proxy and
# describe no specific counterparty relationship. They are recorded so the
# section is complete, but marked routine so the renderer can rank them last
# rather than presenting them as findings.
_ROUTINE = re.compile(
    r"(indemnity agreement|indemnification agreement|"
    r"granted RSUs to our non-employee directors|"
    r"fullest extent permitted under)", re.I)

# Every Item 404 section opens by describing the review policy and restating
# the $120,000 reporting threshold the rule itself sets. Those sentences
# contain a relationship word and a dollar figure and read exactly like a
# transaction, but disclose none.
_POLICY = re.compile(
    r"(has adopted a written policy|for purposes of this policy|"
    r"policy for the review|subject to certain exceptions|"
    r"we will refer to these transactions|may not participate in the "
    r"(?:discussion|approval)|no director may participate|"
    r"reviews? and (?:approves?|ratifies)|"
    r"amount involved exceeds|in which .{0,40}has a (?:direct or indirect )?"
    r"material interest)", re.I)

# Splitting on any full stop cuts "the son of Dr. Shah was approximately
# $265,000" in half and drops the figure, so honorifics and the common
# corporate abbreviations are excluded from the sentence boundary.
_RPT_SENTENCE = re.compile(
    r"(?<!\bMr\.)(?<!\bMrs\.)(?<!\bMs\.)(?<!\bDr\.)(?<!\bProf\.)(?<!\bJr\.)"
    r"(?<!\bSr\.)(?<!\bInc\.)(?<!\bCorp\.)(?<!\bCo\.)(?<!\bLtd\.)(?<!\bNo\.)"
    r"(?<!\bSt\.)(?<!\bU\.S\.)"
    r"(?<=[.])\s+(?=[A-Z])")


def _extract_related_party_transactions(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """Item 404 related-person transactions, as described in the proxy.

    This is the disclosure that names conflicts an issuer is obliged to admit
    to: family members on payroll, entities a director controls trading with
    the company, foundations buying from counterparties the company also deals
    with. It is prose rather than tabular, so each statement is returned with
    the sentence that supports it and a category, and nothing is inferred
    beyond what the filing states.
    """
    text = " ".join(soup.get_text(" ").split())

    # The heading appears in the contents page, in the governance policy that
    # describes how such transactions are reviewed, and at the disclosure
    # itself. Each candidate is scored on whether what follows reads like the
    # disclosure, because taking either the first or the last occurrence picks
    # the wrong one on different issuers.
    # Ties are broken toward the later candidate. An issuer states the review
    # policy first and the transactions themselves afterwards, so among equally
    # scoring candidates the last is the disclosure — Photronics carries three
    # and only the third, 120,000 characters in, holds the transactions.
    best_section, best_score = "", -1
    for heading in _RPT_HEADING.finditer(text):
        start = heading.start()
        end_match = _RPT_END.search(text, start + 80)
        end = min(end_match.start() if end_match else len(text), start + 5000)
        candidate = text[start:end]
        if len(candidate.split()) < 25:
            continue
        score = (len(_RPT_BODY_SIGNAL.findall(candidate))
                 - len(_COMP_SIGNAL.findall(candidate)))
        if score >= best_score:
            best_section, best_score = candidate, score

    # A section that scores no positive signal is not the disclosure. Returning
    # nothing is correct: many issuers genuinely report no related-person
    # transaction, and Apple is one of them.
    if not best_section:
        return []
    section = best_section

    transactions: List[Dict[str, Any]] = []
    for sentence in _RPT_SENTENCE.split(section):
        sentence = sentence.strip()
        if len(sentence.split()) < 8:
            continue

        family = _FAMILY.search(sentence)
        entities = [e for e in _ENTITY.findall(sentence)
                    if not re.fullmatch(r"(The\s+)?Company", e, re.I)]
        amounts = [float(n.replace(",", "")) * _SCALE[(u or "").lower() or None]
                   for n, u in _AMOUNT.findall(sentence)]

        if _POLICY.search(sentence):
            category = "policy"
        elif _ROUTINE.search(sentence):
            category = "routine"
        elif family:
            category = "family employment" if re.search(
                r"employ|compensation|salary", sentence, re.I) else "family relationship"
        elif entities and amounts:
            category = "entity transaction"
        elif amounts:
            category = "other"
        else:
            continue

        transactions.append({
            "category": category,
            "relationship": family.group(1).lower() if family else None,
            "counterparties": entities[:3],
            "amounts": amounts,
            "largest_amount": max(amounts) if amounts else None,
            "is_routine": category in ("routine", "policy"),
            "text": sentence,
        })

    return transactions


def _extract_say_on_pay(soup: BeautifulSoup) -> Dict[str, Any]:
    """
    Say-on-pay voting results from a proxy statement.

    Counts are left as None when nothing could be parsed. Zero is a meaningful
    vote total, so defaulting to it made a failed parse indistinguishable from
    universal shareholder opposition — which is how every company acquired a
    "say-on-pay approval only 0.0%" red flag.
    """
    result = {
        "votes_for": None,
        "votes_against": None,
        "abstain": None,
        "approval_pct": None,
        "year": None,
        "source": None,
    }

    text = soup.get_text()

    # Look for say-on-pay section
    sop_patterns = [
        r'advisory\s+vote\s+on\s+(?:executive\s+)?compensation',
        r'say.on.pay',
        r'approval\s+of\s+executive\s+compensation',
    ]

    for pattern in sop_patterns:
        match = re.search(pattern, text.lower())
        if match:
            # Look for voting results nearby
            section = text[match.start():match.start() + 2000]

            # Extract percentages
            pct_match = re.search(r'(\d+\.?\d*)\s*%\s*(?:approval|for|in favor)', section.lower())
            if pct_match:
                result["approval_pct"] = float(pct_match.group(1))

            # Extract vote counts
            for_match = re.search(r'for[:\s]+(\d[\d,]+)', section.lower())
            against_match = re.search(r'against[:\s]+(\d[\d,]+)', section.lower())

            if for_match:
                result["votes_for"] = int(for_match.group(1).replace(',', ''))
            if against_match:
                result["votes_against"] = int(against_match.group(1).replace(',', ''))

            if result["votes_for"] and result["votes_against"] is not None:
                total = result["votes_for"] + result["votes_against"] + (result["abstain"] or 0)
                if total:
                    result["approval_pct"] = round(result["votes_for"] / total * 100, 1)
            if any(result[k] is not None for k in ("votes_for", "approval_pct")):
                result["source"] = "DEF 14A"
            break

    return result


def _extract_say_on_pay_from_8k(cik: str) -> Dict[str, Any]:
    """
    Say-on-pay results from an 8-K Item 5.07.

    Annual meeting vote tallies are reported under Item 5.07 within four
    business days of the meeting. That is the authoritative record; a proxy
    statement solicits the vote and so usually predates its outcome.
    """
    empty = {"votes_for": None, "votes_against": None, "abstain": None,
             "approval_pct": None, "year": None, "source": None}

    try:
        from app.connectors.sec_edgar_connector import (
            get_company_submissions, SEC_HEADERS, SEC_WWW_BASE)
    except Exception:
        return empty

    subs = get_company_submissions(cik, forms=["8-K"], limit=40)
    for filing in subs.get("filings", []):
        accession = (filing.get("accession") or "").replace("-", "")
        document = filing.get("document") or ""
        if not accession or not document:
            continue
        url = (f"{SEC_WWW_BASE}/Archives/edgar/data/{cik.lstrip('0')}/"
               f"{accession}/{document}")
        try:
            resp = sec_get(url, timeout=20)
            if resp is None or not resp.ok:
                continue
            text = " ".join(BeautifulSoup(resp.text, "html.parser").get_text().split())
        except Exception:
            continue

        if "5.07" not in text or "compensation" not in text.lower():
            continue

        # Locate the advisory compensation proposal, then the first three vote
        # columns following it (for / against / abstain).
        match = re.search(
            r"(advisory[^.]{0,120}compensation|say[- ]on[- ]pay)", text, re.IGNORECASE)
        if not match:
            continue
        window = text[match.start():match.start() + 600]
        numbers = re.findall(r"\b(\d{1,3}(?:,\d{3}){2,})\b", window)
        if len(numbers) < 3:
            continue

        votes = [int(n.replace(",", "")) for n in numbers[:3]]
        total = sum(votes)
        if not total:
            continue
        return {
            "votes_for": votes[0],
            "votes_against": votes[1],
            "abstain": votes[2],
            "approval_pct": round(votes[0] / total * 100, 1),
            "year": (filing.get("filing_date") or "")[:4],
            "source": f"8-K Item 5.07 ({filing.get('filing_date')})",
            "source_url": url,
        }

    return empty


def _extract_beneficial_ownership(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """Extract beneficial ownership table from proxy."""
    ownership = []

    # Find ownership tables
    tables = soup.find_all("table")

    for table in tables:
        header_text = " ".join(table.get_text()[:300].lower().split())

        if not any(kw in header_text for kw in ["beneficial", "ownership", "percent of class", "shares owned"]):
            continue

        rows = table.find_all("tr")

        for row in rows:
            cells = row.find_all(["td", "th"])
            if len(cells) < 2:
                continue

            cell_texts = [c.get_text(strip=True) for c in cells]
            name = cell_texts[0]

            # Skip header/non-name rows
            if not name or any(kw in name.lower() for kw in ["name", "owner", "5%", "beneficial"]):
                continue
            if len(name) < 3:
                continue

            entry = {
                "owner": name,
                "shares": 0,
                "percent": 0.0,
            }

            # Parse remaining cells for shares and percentage
            for cell in cell_texts[1:]:
                # Percentage
                pct_match = re.search(r'(\d+\.?\d*)\s*%', cell)
                if pct_match:
                    entry["percent"] = float(pct_match.group(1))
                    continue

                # Share count
                shares = _parse_money(cell)
                if shares > entry["shares"]:
                    entry["shares"] = int(shares)

            if entry["shares"] > 0 or entry["percent"] > 0:
                ownership.append(entry)

    return ownership[:20]  # Limit results


def extract_executive_compensation(
    ticker: str,
    years: int = 3,
) -> Dict[str, Any]:
    """
    Extract executive compensation data from recent proxy statements.

    Args:
        ticker: Stock ticker symbol
        years: Number of years of proxy filings to analyze

    Returns:
        Executive compensation analysis.
    """
    result = {
        "ticker": ticker,
        "compensation_by_year": {},
        "named_executive_officers": [],
        "total_neo_compensation": 0,
        "ceo_compensation": {},
        "pay_ratio": None,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }

    cik = _get_cik_from_ticker(ticker)
    if not cik:
        result["error"] = f"Could not resolve CIK for {ticker}"
        return result

    proxies = _get_recent_proxies(cik, limit=years)
    if not proxies:
        result["error"] = "No DEF 14A filings found"
        return result

    for proxy in proxies:
        html = _fetch_proxy_document(
            cik,
            proxy["accession_number"],
            proxy.get("primary_document", ""),
        )

        if not html:
            continue

        soup = BeautifulSoup(html, "html.parser")
        compensation = _extract_compensation_table(soup)

        if compensation:
            year = proxy["filing_date"][:4]
            result["compensation_by_year"][year] = compensation

            # Track NEOs and total
            for entry in compensation:
                name = entry["name"]
                if name not in [neo["name"] for neo in result["named_executive_officers"]]:
                    result["named_executive_officers"].append({
                        "name": name,
                        "latest_total": entry["total"],
                    })
                result["total_neo_compensation"] += entry["total"]

            # Identify CEO (usually highest paid or first listed)
            if compensation:
                ceo_entry = max(compensation, key=lambda x: x["total"])
                if not result["ceo_compensation"]:
                    result["ceo_compensation"] = ceo_entry

        # Rate limit
        time.sleep(0.1)

    return result


def get_board_composition(ticker: str) -> Dict[str, Any]:
    """
    Get board of directors composition from latest proxy.

    Args:
        ticker: Stock ticker symbol

    Returns:
        Board composition analysis.
    """
    result = {
        "ticker": ticker,
        "board": {},
        "filing_date": "",
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }

    cik = _get_cik_from_ticker(ticker)
    if not cik:
        result["error"] = f"Could not resolve CIK for {ticker}"
        return result

    proxies = _get_recent_proxies(cik, limit=1)
    if not proxies:
        result["error"] = "No DEF 14A filings found"
        return result

    proxy = proxies[0]
    html = _fetch_proxy_document(
        cik,
        proxy["accession_number"],
        proxy.get("primary_document", ""),
    )

    if html:
        soup = BeautifulSoup(html, "html.parser")
        result["board"] = _extract_board_composition(soup)
        result["filing_date"] = proxy["filing_date"]

    return result


def get_proxy_intelligence(
    ticker: str,
    years: int = 3,
) -> Dict[str, Any]:
    """
    Comprehensive proxy statement intelligence for a company.

    Extracts:
    - Executive compensation (all NEOs)
    - Board composition
    - Related party transactions
    - Say-on-pay results
    - Beneficial ownership

    Args:
        ticker: Stock ticker symbol
        years: Number of years to analyze

    Returns:
        Complete proxy intelligence payload.
    """
    result = {
        "ticker": ticker,
        "executive_compensation": {},
        "board_composition": {},
        "related_party_transactions": [],
        "say_on_pay": {},
        "beneficial_ownership": [],
        "proxy_filings_analyzed": [],
        "flags": [],
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }

    cik = _get_cik_from_ticker(ticker)
    if not cik:
        result["error"] = f"Could not resolve CIK for {ticker}"
        return result

    result["cik"] = cik

    proxies = _get_recent_proxies(cik, limit=years)
    if not proxies:
        result["error"] = "No DEF 14A filings found"
        return result

    all_compensation = []
    latest_board = None
    all_rpt = []
    latest_sop = None
    latest_ownership = []

    for i, proxy in enumerate(proxies):
        result["proxy_filings_analyzed"].append({
            "filing_date": proxy["filing_date"],
            "form_type": proxy["form_type"],
            "accession": proxy["accession_number"],
        })

        html = _fetch_proxy_document(
            cik,
            proxy["accession_number"],
            proxy.get("primary_document", ""),
        )

        if not html:
            continue

        soup = BeautifulSoup(html, "html.parser")

        # Executive compensation
        compensation = _extract_compensation_table(soup)
        for entry in compensation:
            entry["filing_date"] = proxy["filing_date"]
            all_compensation.append(entry)

        # Board (latest only)
        if i == 0:
            latest_board = _extract_board_composition(soup)
            latest_sop = _extract_say_on_pay(soup)
            if latest_sop.get("approval_pct") is None:
                latest_sop = _extract_say_on_pay_from_8k(cik) or latest_sop
            latest_ownership = _extract_beneficial_ownership(soup)

        # Related party transactions (all years)
        rpt = _extract_related_party_transactions(soup)
        for entry in rpt:
            entry["filing_date"] = proxy["filing_date"]
            all_rpt.append(entry)

        # Rate limit
        time.sleep(0.1)

    # Compile results
    result["executive_compensation"] = {
        "all_entries": all_compensation,
        "neo_count": len(set(e["name"] for e in all_compensation)),
        "total_compensation": sum(e["total"] for e in all_compensation),
    }

    result["board_composition"] = latest_board or {}
    result["related_party_transactions"] = all_rpt
    result["say_on_pay"] = latest_sop or {}
    result["beneficial_ownership"] = latest_ownership

    # Generate flags
    # High CEO pay
    ceo_comp = [e for e in all_compensation if e.get("total", 0) > 50_000_000]
    for entry in ceo_comp:
        result["flags"].append({
            "type": "high_executive_compensation",
            "severity": "MEDIUM",
            "detail": f"{entry['name']} total compensation ${entry['total']:,.0f}",
            "year": entry.get("year", ""),
        })

    # Related party transactions
    if all_rpt:
        result["flags"].append({
            "type": "related_party_transactions",
            "severity": "HIGH" if len(all_rpt) > 3 else "MEDIUM",
            "detail": f"{len(all_rpt)} related party transactions disclosed",
        })

    # Low say-on-pay approval. Only raised on a figure that was actually
    # retrieved — an unparsed result is not evidence of shareholder dissent.
    approval = (latest_sop or {}).get("approval_pct")
    if approval is not None and approval < 70:
        result["flags"].append({
            "type": "low_say_on_pay",
            "severity": "HIGH",
            "detail": f"Say-on-pay approval only {approval}%"
                      f" ({latest_sop.get('source', 'source unrecorded')})",
        })

    return result


# ── Convenience Exports ──────────────────────────────────────────────────────

def get_compensation(ticker: str, years: int = 3) -> Dict[str, Any]:
    """Get executive compensation data."""
    return extract_executive_compensation(ticker, years)


def get_board(ticker: str) -> Dict[str, Any]:
    """Get board composition."""
    return get_board_composition(ticker)


def get_full_proxy(ticker: str, years: int = 3) -> Dict[str, Any]:
    """Get comprehensive proxy intelligence."""
    return get_proxy_intelligence(ticker, years)
