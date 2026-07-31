"""
Narrative notes to the financial statements, read from a 10-K.

XBRL companyfacts publishes tagged figures without the disclosure around them,
so anything an issuer states in prose is invisible to it. That covered a large
share of what a reference-quality report says: the size and horizon of supply
commitments, what an acquisition actually bought, and which legal matters
management considers material enough to describe.

The gap it leaves is not only missing detail, it is wrong detail. NVIDIA tags
`UnrecordedUnconditionalPurchaseObligationBalanceSheetAmount` at $22.7bn, and a
report built from tags alone presents that as the company's commitment
position. The note puts manufacturing and supply commitments at $95.2bn,
cloud services at $27bn and investment commitments at $11.4bn. The tag is a
narrower measure, correctly reported, and materially misleading if it is the
only one shown.

The notes are read from the rendered exhibits attached to the filing, which
FilingSummary.xml labels with MenuCategory "Notes". That is a structural key
rather than a naming convention, so it holds across issuers.
"""

import logging
import re
from typing import Any, Dict, List, Optional

from app.connectors.sec_http import sec_get_json, sec_get_text

logger = logging.getLogger(__name__)

SEC_DATA = "https://data.sec.gov"
SEC_WWW = "https://www.sec.gov"

# Every rendered note ends with the XBRL element documentation the viewer
# appends. It is longer than most notes and would swamp anything read from them.
_BOILERPLATE = re.compile(
    r"asc\.fasb\.org|Namespace Prefix|No definition available|"
    r"Data Type: xbrli|Publisher FASB|^X - (Definition|References)|"
    r"xbrl\.org/2003/role", re.I)

_AMOUNT = re.compile(
    r"\$\s?([\d,]+(?:\.\d+)?)\s*(billion|million|thousand)?\b", re.I)

_SCALE = {"billion": 1e9, "million": 1e6, "thousand": 1e3, None: 1.0}

_COMMITMENT_SENTENCE = re.compile(
    r"\b(commitment|obligation|committed|purchase order|minimum payment)", re.I)

# A settlement or judgment amount also sits in the contingencies note and also
# reads as an amount the company has agreed to pay. It is not a commitment, and
# Walmart's opioid settlement was being reported as one.
_NOT_A_COMMITMENT = re.compile(
    r"\b(settlement|judgment|damages|penalt|fine|verdict|restitution|"
    r"risk participation|net of|allowance for)", re.I)

# Words that mark a sentence as describing an amount owed under an agreement
# rather than, say, a balance already recognised.
_COMMITMENT_KIND = (
    ("Manufacturing and supply", re.compile(
        r"(manufactur|supply|supplier|capacity|inventor|vendor|"
        r"purchase of goods or services)", re.I)),
    ("Cloud services", re.compile(r"cloud", re.I)),
    ("Investment", re.compile(r"invest", re.I)),
    ("Lease", re.compile(r"lease", re.I)),
    ("Data centre and property", re.compile(r"(data ?cent|property|construction|facilit)", re.I)),
    ("Other", re.compile(r".", re.I)),
)

_LEGAL_SIGNAL = re.compile(
    r"(court|plaintiff|defendant|complaint|lawsuit|class action|"
    r"subpoena|investigation|inquiry|antitrust|securities litigation|"
    r"district of|circuit|arbitration|settlement|derivative action|"
    r"attorney general|commission staff|grand jury|indictment)", re.I)

_ACQUISITION_SIGNAL = re.compile(
    r"(we (acquired|recorded|entered into)|acquisition of|business combination|"
    r"purchase price|goodwill of|license agreement)", re.I)


def _clean_paragraphs(html_text: str) -> List[str]:
    """Readable paragraphs from a rendered note, boilerplate removed.

    The viewer emits each note twice — once as a single element holding the
    whole note and again broken into paragraphs — so any block that contains
    another block is dropped in favour of its parts.
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return []

    soup = BeautifulSoup(html_text, "html.parser")
    blocks, seen = [], set()
    for element in soup.find_all(["p", "div", "td", "span"]):
        text = " ".join(element.get_text(" ", strip=True).split())
        if len(text.split()) < 12 or text in seen:
            continue
        if _BOILERPLATE.search(text):
            continue
        seen.add(text)
        blocks.append(text)

    return [block for block in blocks
            if not any(other != block and other in block for other in blocks)]


def _to_usd(number: str, unit: Optional[str]) -> float:
    return float(number.replace(",", "")) * _SCALE.get((unit or "").lower() or None, 1.0)


_TABLE_SCALE = re.compile(r"\$?\s*in\s+(billions|millions|thousands)", re.I)

# A maturity schedule: successive fiscal years against amounts, closing with a
# total. Apple states its purchase obligations this way and never names a
# figure in prose, so a sentence-level read finds nothing.
_MATURITY_SCHEDULE = re.compile(
    r"(?:20\d\d\s+\$?\s*[\d,]+(?:\.\d+)?\s+){2,}.*?"
    r"Total\s*\$?\s*([\d,]+(?:\.\d+)?)", re.I | re.S)


def _detect_scale(html_text: str) -> float:
    """The unit a rendered table reports in, from its header."""
    match = _TABLE_SCALE.search(html_text[:20000])
    if not match:
        return 1.0
    return {"billions": 1e9, "millions": 1e6, "thousands": 1e3}[match.group(1).lower()]


def _sentences(paragraph: str) -> List[str]:
    return [s.strip() for s in re.split(r"(?<=[.;])\s+(?=[A-Z(])", paragraph) if s.strip()]


def _extract_commitments(paragraphs: List[str],
                         table_scale: float = 1.0) -> List[Dict[str, Any]]:
    """Contractual amounts the issuer states, in prose or as a maturity schedule."""
    found: List[Dict[str, Any]] = []
    for position, paragraph in enumerate(paragraphs):
        schedule = _MATURITY_SCHEDULE.search(paragraph)
        if schedule and table_scale > 1.0:
            # A bare schedule carries no label, so it takes the one from the
            # prose that introduces it.
            context = next((paragraphs[i] for i in range(position - 1, -1, -1)
                            if _COMMITMENT_SENTENCE.search(paragraphs[i])), "")
            if context:
                kind = next(label for label, pattern in _COMMITMENT_KIND
                            if pattern.search(context))
                years = re.findall(r"\b(20\d\d)\b", paragraph)
                found.append({
                    "kind": kind,
                    "amount": _to_usd(schedule.group(1), None) * table_scale,
                    "through_fiscal_year": max(years) if years else None,
                    "sentence": context,
                })
            continue

        for sentence in _sentences(paragraph):
            if not _COMMITMENT_SENTENCE.search(sentence):
                continue
            if _NOT_A_COMMITMENT.search(sentence) or _LEGAL_SIGNAL.search(sentence):
                continue
            match = _AMOUNT.search(sentence)
            if not match:
                continue
            # The figure has to belong to the commitment rather than merely
            # share a sentence with it. JPMorgan's note qualifies a lending
            # exposure with "net of risk participations… of $200 million" in a
            # sentence that mentions commitments 200 characters earlier.
            window = sentence[max(0, match.start() - 90):match.end() + 90]
            if not _COMMITMENT_SENTENCE.search(window):
                continue
            amount = _to_usd(match.group(1), match.group(2))
            # Below a billion these are usually incidental references rather
            # than the headline commitment figure.
            if amount < 1e8:
                continue
            # An issuer commonly names the commitment in one sentence and
            # quantifies it in the next — "we enter into agreements with our
            # supply vendors… As of January 25, 2026, these commitments were
            # $95.2 billion" — so the paragraph supplies the label when the
            # sentence carrying the figure does not.
            kind = next(label for label, pattern in _COMMITMENT_KIND
                        if pattern.search(sentence))
            if kind == "Other":
                kind = next(label for label, pattern in _COMMITMENT_KIND
                            if pattern.search(paragraph))
            horizon = re.search(r"through fiscal year (\d{4})", sentence, re.I)
            found.append({
                "kind": kind,
                "amount": amount,
                "through_fiscal_year": horizon.group(1) if horizon else None,
                "sentence": sentence,
            })

    # The same commitment is often restated; keep the largest per kind.
    best: Dict[str, Dict[str, Any]] = {}
    for item in found:
        current = best.get(item["kind"])
        if current is None or item["amount"] > current["amount"]:
            best[item["kind"]] = item
    return sorted(best.values(), key=lambda c: c["amount"], reverse=True)


def _extract_legal_matters(paragraphs: List[str]) -> List[Dict[str, Any]]:
    """Matters the issuer describes in the contingencies note.

    These are not the same population as a docket search. An issuer describes
    what it considers material, including regulatory inquiries that never reach
    a court and so appear on no docket at all.
    """
    matters = []
    for paragraph in paragraphs:
        if not _LEGAL_SIGNAL.search(paragraph) or len(paragraph.split()) < 30:
            continue
        # The concluding assessment paragraph is management's overall view, not
        # a matter; it is captured separately.
        assessment = bool(re.search(
            r"(ultimate outcome|reasonably possible|cannot be reasonably estimated|"
            r"not have a material adverse effect)", paragraph, re.I))
        venue = re.search(
            r"((?:U\.S\.\s+)?District Court[^.,;]{0,60}|"
            r"Court of Appeals[^.,;]{0,40}|Delaware Court of Chancery)",
            paragraph)
        filed = re.search(r"\b(in|on)\s+((?:January|February|March|April|May|June|July|"
                          r"August|September|October|November|December)\s+\d{1,2},?\s+\d{4}|"
                          r"\d{4})", paragraph)
        matters.append({
            "text": paragraph,
            "words": len(paragraph.split()),
            "venue": venue.group(1).strip() if venue else None,
            "first_date": filed.group(2) if filed else None,
            "is_assessment": assessment,
        })
    return matters


def _extract_acquisitions(paragraphs: List[str]) -> List[Dict[str, Any]]:
    """Transactions described in a business combination or asset acquisition note."""
    deals = []
    for paragraph in paragraphs:
        if not _ACQUISITION_SIGNAL.search(paragraph):
            continue
        goodwill = re.search(
            r"\$\s?([\d,.]+)\s*(billion|million)?\s+(?:of\s+)?goodwill", paragraph, re.I)
        intangible = re.search(
            r"\$\s?([\d,.]+)\s*(billion|million)?\s+develop(?:ed)?[- ]technology",
            paragraph, re.I)
        if not (goodwill or intangible):
            continue
        consideration = _AMOUNT.search(paragraph)
        counterparty = re.search(
            r"\bwith\s+([A-Z][\w.&'-]*(?:\s+[A-Z][\w.&'-]*){0,3}),?\s+Inc\b|"
            r"\bacquisition of\s+([A-Z][\w.&'-]*(?:\s+[A-Z][\w.&'-]*){0,3})",
            paragraph)
        deals.append({
            "counterparty": next((g for g in (counterparty.groups() if counterparty else [])
                                  if g), None),
            "goodwill": _to_usd(goodwill.group(1), goodwill.group(2)) if goodwill else None,
            "developed_technology": (_to_usd(intangible.group(1), intangible.group(2))
                                     if intangible else None),
            "consideration": (_to_usd(consideration.group(1), consideration.group(2))
                              if consideration else None),
            "text": paragraph,
        })
    return deals


# Which note answers which question, matched against its title.
_NOTE_TOPICS = (
    ("commitments", re.compile(r"commitment|contingenc|purchase obligation", re.I)),
    ("acquisitions", re.compile(r"business combination|acquisition", re.I)),
    ("investments", re.compile(r"marketable securities|non-?marketable|investments", re.I)),
    ("debt", re.compile(r"^debt$|borrowings|notes payable", re.I)),
    ("leases", re.compile(r"^leases?$", re.I)),
)


def get_filing_notes(cik: str) -> Dict[str, Any]:
    """Narrative notes from the latest 10-K, with the figures stated in them."""
    result: Dict[str, Any] = {
        "notes": [],
        "commitments": [],
        "legal_matters": [],
        "acquisitions": [],
        "source_url": None,
        "fiscal_period_end": None,
    }

    from app.connectors.sec_edgar_connector import find_latest_filing

    filing = find_latest_filing(cik, "10-K")
    if not filing:
        return result

    base = filing["base_url"]
    result["source_url"] = f"{base}/"
    result["accession"] = filing["accession"]
    result["fiscal_period_end"] = filing["report_date"]

    summary = sec_get_text(f"{base}/FilingSummary.xml")
    if not summary:
        return result

    # MenuCategory is how the viewer itself separates the narrative notes from
    # the statements and the tagged detail tables. Matching on it rather than on
    # the note's title avoids depending on what an issuer calls things — NVIDIA
    # titles its business combination note simply "Groq".
    for block in re.findall(r"<Report[^>]*>(.*?)</Report>", summary, re.S):
        category = re.search(r"<MenuCategory>(.*?)</MenuCategory>", block)
        name = re.search(r"<ShortName>(.*?)</ShortName>", block)
        filename = re.search(r"<HtmlFileName>(.*?)</HtmlFileName>", block)
        if not (category and name and filename) or category.group(1) != "Notes":
            continue

        import html as html_module
        title = html_module.unescape(name.group(1))
        if any(suffix in title for suffix in ("(Tables)", "(Details)", "(Policies)")):
            continue

        body = sec_get_text(f"{base}/{filename.group(1)}")
        paragraphs = _clean_paragraphs(body)
        if not paragraphs:
            continue
        scale = _detect_scale(body)

        topics = [key for key, pattern in _NOTE_TOPICS if pattern.search(title)]
        result["notes"].append({
            "title": title,
            "topics": topics,
            "paragraphs": paragraphs,
            "words": sum(len(p.split()) for p in paragraphs),
            "url": f"{base}/{filename.group(1)}",
        })

        if "commitments" in topics:
            result["commitments"].extend(_extract_commitments(paragraphs, scale))
            result["legal_matters"].extend(_extract_legal_matters(paragraphs))
        # An acquisition may be described in a note named after the target, so
        # the content decides rather than the title.
        result["acquisitions"].extend(_extract_acquisitions(paragraphs))

    # Deduplicate across notes.
    by_kind: Dict[str, Dict[str, Any]] = {}
    for item in result["commitments"]:
        current = by_kind.get(item["kind"])
        if current is None or item["amount"] > current["amount"]:
            by_kind[item["kind"]] = item
    result["commitments"] = sorted(by_kind.values(),
                                   key=lambda c: c["amount"], reverse=True)
    result["total_commitments"] = sum(c["amount"] for c in result["commitments"])

    unique_deals: Dict[str, Dict[str, Any]] = {}
    for deal in result["acquisitions"]:
        unique_deals.setdefault(deal["text"][:120], deal)
    result["acquisitions"] = list(unique_deals.values())

    unique_matters: Dict[str, Dict[str, Any]] = {}
    for matter in result["legal_matters"]:
        unique_matters.setdefault(matter["text"][:120], matter)
    result["legal_matters"] = list(unique_matters.values())

    return result
