"""
Person and Entity Disambiguation
────────────────────────────────────────────────────────────────────────────
Shared resolution helpers for the people sections of an intelligence report.

Free biographical sources match on strings, not on people. Searching Google
Books for a director named Tench Coxe returns *The Federalist* (1796), because
the eighteenth-century political economist of that name is the more published
holder of it; searching Open Library for "Stephen C. Neal" returns science
fiction anthologies edited by an unrelated Neal; and reading prior employers out
of search snippets produced "Biden" and "Jensen" as companies. Each of those
reached a published report as a fact about a sitting NVIDIA director.

Nothing here fetches anything. These are the gates a candidate has to pass
before a retrieved string is allowed to become a claim about a named person:

  - a surname match is necessary but not sufficient; given names must agree
  - a person cannot have written a book before they were born
  - a company name must look like a company and not like a person or a verb
  - an institution must resolve to a canonical name before two people can be
    said to have attended the same one
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# Honorifics and post-nominals carry no identity and break naive comparison.
_TITLES = {
    "mr", "mrs", "ms", "miss", "dr", "prof", "professor", "sir", "dame",
    "hon", "rev", "mx",
}
_SUFFIXES = {
    "jr", "sr", "ii", "iii", "iv", "v", "phd", "md", "jd", "mba", "cpa",
    "esq", "cfa", "llm", "dds", "rn",
}

# A candidate "company" that is really a person, a government, a role or a
# sentence fragment. Extracting employers from prose produces all four.
_NON_COMPANY_TOKENS = {
    "the", "a", "an", "and", "or", "of", "in", "at", "for", "from", "with",
    "he", "she", "they", "his", "her", "their", "who", "which", "that",
    "board", "director", "chairman", "chairperson", "president", "ceo", "cfo",
    "coo", "cto", "officer", "executive", "member", "partner", "trustee",
    "committee", "university", "college", "school", "degree", "bachelor",
    "master", "doctorate", "since", "until", "prior", "previously", "currently",
    "company", "corporation", "firm", "business", "career", "role", "position",
}

# Business functions read out of a title clause. "He was Director of Marketing
# and MIS at Digital Communication Associates" names one company, and a regex
# that stops at the first preposition returns "Marketing" as the employer.
_BUSINESS_FUNCTIONS = {
    "marketing", "sales", "operations", "finance", "engineering", "research",
    "development", "administration", "manufacturing", "procurement", "legal",
    "compliance", "communications", "human resources", "strategy", "technology",
    "information technology", "product", "design", "quality", "logistics",
    "accounting", "audit", "tax", "treasury", "investor relations",
}


def company_core_name(name: str) -> str:
    """A company name stripped to its distinctive core, for deduplication.

    "Tensilica", "Tensilica Inc" and "Tensilica, Inc." are one employer, and a
    list that prints all three reads as three jobs.
    """
    try:
        from app.connectors.entity_naming import clean_legal_name
        cleaned = clean_legal_name((name or "").upper())
        if cleaned:
            return " ".join(cleaned.lower().split())
    except ImportError as e:
        import logging
        logging.getLogger(__name__).debug("entity_naming module not available for company_core_name: %s", e)
    words = [
        w for w in re.sub(r"[^\w\s]", " ", (name or "").lower()).split()
        if w not in _CORPORATE_SUFFIXES
    ]
    return " ".join(words)

# Heads of state, agencies and other proper nouns that a snippet scraper reads
# as employers. "Joe Biden has announced the appointment of John O. Dabiri"
# yielded "Biden" as a prior company in a published report.
_POLITICAL_NOISE = {
    "biden", "trump", "obama", "bush", "clinton", "reagan", "carter", "harris",
    "congress", "senate", "house", "white house", "pentagon", "government",
}

_CORPORATE_SUFFIXES = {
    "inc", "inc.", "corp", "corp.", "corporation", "co", "co.", "company",
    "llc", "l.l.c.", "ltd", "ltd.", "limited", "plc", "lp", "l.p.", "llp",
    "gmbh", "ag", "sa", "s.a.", "nv", "n.v.", "ab", "as", "oy", "spa",
    "holdings", "group", "partners", "ventures", "capital", "technologies",
    "systems", "labs", "laboratories", "industries", "enterprises",
    "associates", "international", "solutions", "networks", "semiconductor",
    "pharmaceuticals", "bank", "trust",
}

# Canonical institution names, keyed by the fragments that appear in proxy
# biographies. A degree from Harvard Business School and a degree from Harvard
# University are the same affiliation for the purpose of asking whether two
# directors overlapped, so both resolve to one name.
INSTITUTION_ALIASES: Dict[str, Tuple[str, ...]] = {
    "Stanford University": ("stanford",),
    "Harvard University": ("harvard",),
    "Massachusetts Institute of Technology": (
        "massachusetts institute of technology", "mit sloan", " mit ",
    ),
    "Yale University": ("yale",),
    "Princeton University": ("princeton",),
    "University of Pennsylvania": ("wharton", "university of pennsylvania"),
    "Columbia University": ("columbia",),
    "University of California, Berkeley": (
        "uc berkeley", "berkeley", "university of california, berkeley",
    ),
    "California Institute of Technology": (
        "california institute of technology", "caltech",
    ),
    "University of Chicago": ("university of chicago", "booth school"),
    "Northwestern University": ("northwestern", "kellogg school"),
    "Dartmouth College": ("dartmouth", "tuck school"),
    "Cornell University": ("cornell",),
    "Brown University": ("brown university",),
    "Duke University": ("duke university", "fuqua school"),
    "Georgetown University": ("georgetown",),
    "Carnegie Mellon University": ("carnegie mellon",),
    "Johns Hopkins University": ("johns hopkins",),
    "New York University": ("new york university", "nyu stern", "stern school"),
    "University of Michigan": ("university of michigan", "ross school"),
    "University of Virginia": ("university of virginia", "darden school"),
    "University of Texas": ("university of texas",),
    "University of Southern California": (
        "university of southern california", "marshall school",
    ),
    "University of California, Los Angeles": ("ucla", "anderson school"),
    "University of Oxford": ("oxford",),
    "University of Cambridge": ("cambridge",),
    "London School of Economics": ("london school of economics",),
    "INSEAD": ("insead",),
    "Indian Institute of Technology": ("indian institute of technology", "iit "),
}

# Institutions whose alumni networks are the ones the report is asked about.
# Membership here changes emphasis, never whether an overlap is reported.
ELITE_INSTITUTIONS = frozenset({
    "Stanford University", "Harvard University",
    "Massachusetts Institute of Technology", "Yale University",
    "Princeton University", "University of Pennsylvania",
    "Columbia University", "University of California, Berkeley",
    "California Institute of Technology", "University of Chicago",
    "Dartmouth College", "Cornell University", "Brown University",
    "University of Oxford", "University of Cambridge", "INSEAD",
})

# Degree tokens as they appear in proxy prose.
_DEGREE_PATTERN = re.compile(
    r"\b(Ph\.?D|M\.?B\.?A|M\.?S\.?c?|M\.?A\.?|M\.?Eng|LL\.?M|LL\.?B|J\.?D|M\.?D|"
    r"B\.?S\.?E?|B\.?A\.?|A\.?B\.?|B\.?Eng|D\.?Phil|Sc\.?D|Ed\.?D)\b",
    re.IGNORECASE,
)

# A proper-noun phrase ending in an educational-institution head noun. The
# phrase is bounded by a lowercase word so that "from Dartmouth College and an
# MBA degree from Harvard" yields two institutions rather than one run-on.
_INSTITUTION_PATTERN = re.compile(
    r"\b((?:[A-Z][A-Za-z&.'’-]*\s+){0,4}?"
    r"(?:University|College|Institute|Institute\s+of\s+Technology|Academy|"
    r"Polytechnic|Conservatory)"
    r"(?:\s+of\s+(?:[A-Z][A-Za-z&.'’-]*(?:\s+[A-Z][A-Za-z&.'’-]*){0,3}))?)"
)

_SCHOOL_PATTERN = re.compile(
    r"\b((?:[A-Z][A-Za-z&.'’-]*\s+){1,4}"
    r"(?:Business\s+School|Law\s+School|Medical\s+School|School\s+of\s+"
    r"(?:Business|Law|Medicine|Management|Engineering|Government|"
    r"Public\s+Health)))"
)


# ── Names ────────────────────────────────────────────────────────────────────

def _tokens(name: str) -> List[str]:
    """Lowercased name words, with titles and post-nominals removed."""
    cleaned = re.sub(r"[^\w\s'’-]", " ", (name or "").lower())
    words = [w for w in cleaned.split() if w]
    return [
        w for w in words
        if w.strip(".") not in _TITLES and w.strip(".") not in _SUFFIXES
    ]


def normalize_person_name(name: str) -> str:
    """A person's name reduced to comparable form."""
    return " ".join(_tokens(name))


def person_name_parts(name: str) -> Tuple[str, List[str], str]:
    """Given name, middle tokens and surname.

    Filing indexes invert names — Form 4 reports "HUANG JEN HSUN" while a proxy
    prints "Jen-Hsun Huang" — so callers that need to compare across sources
    should compare surnames and given names rather than whole strings.
    """
    parts = _tokens(name)
    if not parts:
        return "", [], ""
    if len(parts) == 1:
        return "", [], parts[0]
    return parts[0], parts[1:-1], parts[-1]


def surname(name: str) -> str:
    """Surname alone, for family-tie and vehicle-name comparisons."""
    return person_name_parts(name)[2]


def _given_names_agree(left: str, right: str) -> bool:
    """Whether two given names can belong to the same person.

    An initial is allowed to stand for a full name, so "J. Huang" and
    "Jen-Hsun Huang" agree, while "Dawn" and "David" do not.
    """
    if not left or not right:
        return False
    left, right = left.strip("."), right.strip(".")
    if left == right:
        return True
    if len(left) == 1 or len(right) == 1:
        return left[0] == right[0]
    # Hyphenated and compressed forms of the same name: "jen-hsun" / "jenhsun".
    return left.replace("-", "") == right.replace("-", "")


def _invert(name: str) -> str:
    """A filing-index name rewritten given-name-first.

    Section 16 indexes surname first without a comma — "HUANG JEN HSUN" — while
    proxies print "Jen-Hsun Huang". Comparing the two without this returns no
    match, which matters because the insider register and the proxy are the two
    sources a conflict has to be found across.
    """
    parts = _tokens(name)
    if len(parts) < 2:
        return name
    return " ".join(parts[1:] + parts[:1])


def same_person(left: str, right: str) -> bool:
    """Whether two name strings plausibly denote one person.

    Requires the surname to match and the given names to be compatible. A shared
    surname alone is not enough: it is what let books by an unrelated Hudson be
    attributed to a director named Hudson.
    """
    if _same_person_ordered(left, right):
        return True
    # One side may be a filing index entry in surname-first order.
    return (_same_person_ordered(_invert(left), right)
            or _same_person_ordered(left, _invert(right)))


def _same_person_ordered(left: str, right: str) -> bool:
    """Name comparison assuming both sides are given-name-first."""
    l_first, l_middle, l_last = person_name_parts(left)
    r_first, r_middle, r_last = person_name_parts(right)
    if not l_last or l_last != r_last:
        return False
    if not l_first or not r_first:
        # One side is a bare surname. Too weak to assert, so it is refused.
        return False

    # A compound given name may be written as one hyphenated token or as two:
    # "Jen-Hsun Huang" and "Jen Hsun Huang" are one person.
    l_joined = (l_first + "".join(l_middle)).replace("-", "")
    r_joined = (r_first + "".join(r_middle)).replace("-", "")
    if l_joined == r_joined:
        return True

    if not _given_names_agree(l_first, r_first):
        return False
    # Where both sides state a middle initial, they must not contradict.
    l_initials = [m[0] for m in l_middle if m]
    r_initials = [m[0] for m in r_middle if m]
    if l_initials and r_initials and l_initials[0] != r_initials[0]:
        return False

    # A spelled-out middle name on one side and none on the other is a
    # different person, not an abbreviation: "Dawn Bennett Hudson" wrote the
    # novels that were attributed to the director Dawn Hudson. An initial is
    # still allowed to be dropped, as proxies and filings do so routinely.
    l_full = [m for m in l_middle if len(m) > 1]
    r_full = [m for m in r_middle if len(m) > 1]
    if bool(l_full) != bool(r_full):
        return False
    return True


def author_matches_person(authors: List[str], person: str) -> bool:
    """Whether a credited author list contains this person."""
    return any(same_person(author, person) for author in authors or [])


# ── Lifespan gates ───────────────────────────────────────────────────────────

MINIMUM_AUTHORSHIP_AGE = 16


def birth_year_from_age(age: Any,
                        as_of: Optional[int] = None) -> Optional[int]:
    """Approximate birth year from a proxy-disclosed age.

    Proxies state age rather than date of birth, so this is accurate to a year.
    That is ample for the only question asked of it: whether a person was alive
    when a document was published.
    """
    try:
        age_int = int(age)
    except (TypeError, ValueError):
        return None
    if not 18 <= age_int <= 110:
        return None
    return (as_of or datetime.utcnow().year) - age_int


def publication_year(value: Any) -> Optional[int]:
    """First four-digit year in a publication date field."""
    match = re.search(r"(1[0-9]{3}|20[0-9]{2})", str(value or ""))
    return int(match.group(1)) if match else None


def plausible_authorship(year: Optional[int],
                         birth_year: Optional[int]) -> bool:
    """Whether a person of this age could have written something that year.

    With no birth year the check cannot be made, and the candidate is allowed
    through to be judged on the other gates — except for works old enough that
    no living executive could have written them, which is how an eighteenth
    century namesake was credited to a sitting director.
    """
    if year is None:
        return True
    if birth_year is None:
        return year >= datetime.utcnow().year - 110
    return year >= birth_year + MINIMUM_AUTHORSHIP_AGE


# ── Company names ────────────────────────────────────────────────────────────

def looks_like_person_name(candidate: str,
                           known_people: Optional[List[str]] = None) -> bool:
    """Whether a candidate company name is really a person's name.

    Snippet extraction produces the subject of the sentence as often as the
    employer: "Jensen", "Dawn Hudson" and "Biden" were all published as prior
    companies of NVIDIA directors.
    """
    text = (candidate or "").strip()
    if not text:
        return False
    lowered = text.lower()
    if lowered in _POLITICAL_NOISE:
        return True

    # A single-word company name is common and legitimate — Pepsi, Synopsys,
    # Tensilica — so the test is not "does this look like a name" in the
    # abstract, but "is this one of the people already in this document".
    if any(w.lower().strip(".,&") in _CORPORATE_SUFFIXES for w in text.split()):
        return False

    for person in known_people or []:
        if same_person(text, person):
            return True
        if normalize_person_name(text) == normalize_person_name(person):
            return True
        first, _, last = person_name_parts(person)
        if lowered in {first, last} and lowered:
            return True
    return False


def clean_company_name(raw: str) -> Optional[str]:
    """A company name trimmed out of prose, or None if it is not one.

    Rejects the fragments that regex extraction over biographies and search
    snippets reliably produces: trailing dates ("Nvidia in 1993"), clauses
    ("Dawn Hudson Speaks at the U"), role words and bare connectives.
    """
    text = " ".join((raw or "").split())
    if not text:
        return None

    # Drop a trailing subordinate clause or date qualifier.
    text = re.split(r"\s+(?:in|from|since|until|during|where|which|who|and)\s+",
                    text)[0]
    text = re.sub(r"[,;:.]+$", "", text).strip()
    text = re.sub(r"\s+\b(19|20)\d{2}\b$", "", text).strip()
    if not text or len(text) < 2:
        return None

    words = text.split()
    if len(words) > 8:
        return None

    lowered = [w.lower().strip(".,&") for w in words]
    if lowered[0] in _NON_COMPANY_TOKENS:
        return None
    # A phrase made only of generic words names no company.
    if all(w in _NON_COMPANY_TOKENS or not w for w in lowered):
        return None
    # A business function on its own is a department, not an employer.
    if text.lower() in _BUSINESS_FUNCTIONS:
        return None
    if all(w in _BUSINESS_FUNCTIONS or w in {"and", "of", "the"} for w in lowered):
        return None
    # An extraction that swallowed a verb is a sentence, not a name.
    if re.search(r"\b(?:is|was|are|were|has|have|had|said|says|announced|"
                 r"joined|serves|served|speaks|discusses|leads|led)\b",
                 text, re.IGNORECASE):
        return None
    # Must contain a capitalised word: a company name is a proper noun.
    if not any(w[:1].isupper() for w in words):
        return None
    return text


def is_same_company(left: str, right: str) -> bool:
    """Whether two strings name the same company.

    Defers to the entity resolver used by the federal and litigation
    connectors, so "NVIDIA" and "NVIDIA CORP" are one company here exactly as
    they are there.
    """
    if not left or not right:
        return False
    try:
        from app.connectors.entity_naming import matches_entity
        if matches_entity(left, right) or matches_entity(right, left):
            return True
    except ImportError as e:
        import logging
        logging.getLogger(__name__).debug("entity_naming module not available for is_same_company: %s", e)
    return normalize_person_name(left) == normalize_person_name(right)


def is_valid_company_name(raw: str,
                          known_people: Optional[List[str]] = None,
                          current_company: str = "") -> bool:
    """Whether an extracted string may be published as a company name."""
    cleaned = clean_company_name(raw)
    if not cleaned:
        return False
    if looks_like_person_name(cleaned, known_people):
        return False
    if current_company and is_same_company(cleaned, current_company):
        return False
    return True


# ── Institutions ─────────────────────────────────────────────────────────────

def normalize_institution(raw: str) -> Optional[str]:
    """Canonical name for an educational institution, or None.

    Two directors can only be said to have attended the same institution once
    the strings naming it agree. "Harvard Business School" and "Harvard
    University" are one affiliation here; without this, the overlap between two
    Dartmouth graduates was reported as no connection at all.
    """
    text = " ".join((raw or "").split())
    if not text:
        return None
    padded = f" {text.lower()} "
    for canonical, fragments in INSTITUTION_ALIASES.items():
        for fragment in fragments:
            if fragment.startswith(" ") or fragment.endswith(" "):
                if fragment in padded:
                    return canonical
            elif fragment in padded:
                return canonical

    # Unknown but well-formed institution names are kept under their own name so
    # that overlaps outside the alias table are still detected.
    if re.search(r"\b(University|College|Institute|Academy|Polytechnic|"
                 r"Business School|Law School|School of)\b", text, re.IGNORECASE):
        return re.sub(r"^(?:the)\s+", "", text, flags=re.IGNORECASE).strip()
    return None


# ── Employment history in filed biographies ──────────────────────────────────

# Prior roles as a proxy states them. These read the issuer's own filed
# biography, where the sentence structure is consistent and the subject is
# always the person being described — unlike a search snippet, where the subject
# is whoever the query surfaced.
_BIO_ROLE_PATTERNS = (
    # "Director of Marketing and MIS at Digital Communication Associates" — the
    # employer follows "at", and stopping at the first preposition instead
    # returns the department.
    re.compile(
        r"(?:was|is|served|serves)\s+(?:as\s+)?(?:the\s+)?"
        r"(?P<role>[A-Za-z\s&]{3,60}?)\s+at\s+"
        r"(?P<company>[A-Z][A-Za-z0-9&.,'’\s-]{2,60}?)"
        r"(?=,\s(?:a|an|the)\s|\s+from\s|\s+since\s|\s+until\s|\.|,|;)"),
    re.compile(
        r"(?:served|serves|was|is|has\s+been|had\s+been)\s+(?:as\s+)?(?:the\s+)?"
        r"(?P<role>[A-Za-z\s]{3,60}?)\s+(?:of|at|for)\s+"
        r"(?P<company>[A-Z][A-Za-z0-9&.,'’\s-]{2,60}?)"
        r"(?=,\s(?:a|an|the)\s|\s+from\s|\s+since\s|\s+until\s|\.|,|;)"),
    re.compile(
        r"(?:co-)?founded\s+(?P<company>[A-Z][A-Za-z0-9&.,'’\s-]{2,60}?)"
        r"(?=,\s(?:a|an|the)\s|\s+in\s+\d{4}|\.|,|;)"),
    re.compile(
        r"(?:joined|worked\s+at|led|ran|headed)\s+"
        r"(?P<company>[A-Z][A-Za-z0-9&.,'’\s-]{2,60}?)"
        r"(?=,\s(?:a|an|the)\s|\s+in\s+\d{4}|\.|,|;)"),
    re.compile(
        r"board\s+of\s+directors\s+of\s+"
        r"(?P<company>[A-Z][A-Za-z0-9&.,'’\s-]{2,60}?)"
        r"(?=,\s(?:a|an|the)\s|\s+from\s|\s+since\s|\.|,|;)"),
)


def extract_bio_companies(
    biography: str,
    current_company: str = "",
    known_people: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Companies named as employers or board seats in a filed biography."""
    if not biography:
        return []

    flat = " ".join(str(biography).split())
    found: List[Dict[str, Any]] = []
    seen: set = set()

    for pattern in _BIO_ROLE_PATTERNS:
        for match in pattern.finditer(flat):
            raw = match.groupdict().get("company") or ""
            cleaned = clean_company_name(raw)
            if not cleaned:
                continue
            if not is_valid_company_name(cleaned, known_people, current_company):
                continue
            key = company_core_name(cleaned) or cleaned.lower()
            if key in seen:
                continue
            seen.add(key)

            role = (match.groupdict().get("role") or "").strip() or None
            year_match = re.search(r"\b(19|20)\d{2}\b",
                                   flat[match.end():match.end() + 30])
            found.append({
                "company": cleaned,
                "role": role,
                "year": int(year_match.group(0)) if year_match else None,
                "is_founder": "found" in match.group(0).lower(),
            })

    return found


def extract_institutions(text: str) -> List[Dict[str, Any]]:
    """Institutions named in a biography, with the degree each is attached to.

    Scanning for institutions and then attaching the nearest preceding degree is
    what makes multiple degrees in one sentence separable. Capturing outward from
    the degree instead — the previous approach — ran the match past the
    institution and into the next clause, yielding "Economics from Dartmouth
    College and an MBA degree" as the name of a school.
    """
    if not text:
        return []

    flat = " ".join(str(text).split())
    found: List[Dict[str, Any]] = []
    seen: set = set()

    for pattern in (_SCHOOL_PATTERN, _INSTITUTION_PATTERN):
        for match in pattern.finditer(flat):
            raw = match.group(1).strip()
            canonical = normalize_institution(raw)
            if not canonical or canonical in seen:
                continue

            # The degree governing this institution is the last one mentioned
            # before it, within the same clause.
            preceding = flat[max(0, match.start() - 120):match.start()]
            degrees = _DEGREE_PATTERN.findall(preceding)
            degree = degrees[-1].upper().replace(".", "") if degrees else None

            field = None
            field_match = re.search(
                r"\b(?:in|of)\s+([A-Z][A-Za-z\s&]{2,40}?)\s+(?:from|at)\s*$",
                preceding)
            if field_match:
                field = field_match.group(1).strip()

            year_match = re.search(r"\b(19|20)\d{2}\b",
                                   flat[match.end():match.end() + 40])

            seen.add(canonical)
            found.append({
                "institution": raw,
                "normalized_institution": canonical,
                "degree": degree,
                "field": field,
                "year": int(year_match.group(0)) if year_match else None,
                "is_elite": canonical in ELITE_INSTITUTIONS,
            })

    return found
