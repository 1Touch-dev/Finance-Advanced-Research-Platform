"""
Entity Name Normalisation
─────────────────────────────────────────────────────────────────────────────
Shared helpers for turning a company's legal name into search terms and for
deciding whether an arbitrary record refers to that company.

Several connectors previously used ``name.split()[0]``, which yields a useless
token for a large share of the market: "Bank of America" -> "BANK",
"The Coca-Cola Company" -> "THE", "International Business Machines" -> "INTERNATIONAL".
Matching on those tokens both misses real records and admits unrelated ones.
"""
import re
from typing import List, Optional

# Corporate form suffixes, stripped from the tail of a legal name.
LEGAL_SUFFIXES = [
    "incorporated", "corporation", "company", "holdings", "holding",
    "group", "limited", "partners", "trust", "plc", "corp", "inc", "co",
    "ltd", "llc", "lp", "llp", "nv", "sa", "ag", "se", "spa", "ab", "as",
    "class a", "class b", "class c",
]

# Leading articles carry no identifying information.
LEADING_ARTICLES = {"the", "a", "an"}

# Words too generic to identify a company on their own. A name reducing to only
# these keeps more of its words so the search term stays distinctive.
GENERIC_TOKENS = {
    "bank", "national", "international", "american", "america", "united",
    "states", "general", "standard", "first", "global", "world", "new",
    "north", "south", "east", "west", "central", "federal", "public",
    "financial", "capital", "industries", "industrial", "technologies",
    "technology", "systems", "solutions", "services", "enterprises",
    "resources", "energy", "motors", "communications", "pharmaceuticals",
    "laboratories", "products", "brands", "stores", "of", "and", "for",
    # Common qualifying adjectives. Without these, "Advanced Micro Devices"
    # reduces to "Advanced", which also matches "Advanced Energy Industries".
    "advanced", "applied", "allied", "premier", "superior", "dynamic",
    "integrated", "universal", "consolidated", "continental", "pacific",
    "atlantic", "modern", "precision", "quality", "select", "summit",
}


def clean_legal_name(name: str) -> str:
    """Strip punctuation, leading articles and trailing corporate suffixes."""
    if not name:
        return ""

    cleaned = re.sub(r"[.,]", " ", name)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    words = cleaned.split()
    while words and words[0].lower() in LEADING_ARTICLES:
        words.pop(0)

    # Remove suffixes from the tail, longest phrases first.
    changed = True
    while changed and words:
        changed = False
        for suffix in sorted(LEGAL_SUFFIXES, key=lambda s: -len(s.split())):
            parts = suffix.split()
            n = len(parts)
            if len(words) > n and [w.lower().strip("&") for w in words[-n:]] == parts:
                del words[-n:]
                changed = True
                break

    # A dangling ampersand left by a stripped suffix ("JPMorgan Chase & Co."
    # reduces to "JPMorgan Chase &") would never match a real record.
    while words and words[-1] in {"&", "-", "and"}:
        words.pop()

    return " ".join(words).strip()


def entity_search_term(name: str) -> str:
    """
    The shortest distinctive form of a company name, for use as a query.

    Keeps adding words until the term is no longer purely generic, so
    "Bank of America Corporation" yields "Bank of America" rather than "Bank",
    while "NVIDIA Corporation" still reduces to "NVIDIA".
    """
    cleaned = clean_legal_name(name)
    if not cleaned:
        return (name or "").strip()

    words = cleaned.split()
    for count in range(1, len(words) + 1):
        candidate = words[:count]
        if any(w.lower() not in GENERIC_TOKENS for w in candidate):
            # Do not end on a connective such as "of" or "and".
            while candidate and candidate[-1].lower() in {"of", "and", "for", "&"}:
                if count < len(words):
                    count += 1
                    candidate = words[:count]
                else:
                    candidate.pop()
            return " ".join(candidate)
    return cleaned


def entity_match_patterns(name: str, extra_aliases: Optional[List[str]] = None) -> List[str]:
    """Uppercase fragments that identify the entity in a third-party record."""
    patterns = {entity_search_term(name).upper(), clean_legal_name(name).upper()}
    patterns.discard("")
    for alias in extra_aliases or []:
        if alias:
            patterns.add(alias.upper())
    return sorted(patterns, key=len, reverse=True)


# Words that may trail a company name in a subsidiary or division without
# making it a different organisation.
DIVISION_TOKENS = {
    "sector", "division", "subsidiary", "usa", "us", "uk", "canada", "america",
    "americas", "international", "global", "worldwide", "public", "government",
    "federal", "technologies", "technology", "solutions", "services", "systems",
    "research", "development", "operations", "manufacturing", "sales",
    # Chartered banking subsidiaries take the parent's name plus a form of
    # charter: federal awards are booked to "JPMORGAN CHASE BANK, NATIONAL
    # ASSOCIATION" rather than to the holding company.
    "bank", "na", "n.a.", "national", "association", "trust", "savings",
}


def matches_entity(candidate: str, name: str,
                   extra_aliases: Optional[List[str]] = None) -> bool:
    """
    Whether ``candidate`` names this entity, as opposed to merely containing
    its name.

    A word-boundary search is far too permissive for companies named after an
    everyday word: searching federal awards for "Apple" that way returns
    "TOWN OF APPLE VALLEY", "BIG APPLE SIGN CORP" and "WASHINGTON APPLE
    COMMISSION". The candidate must therefore *begin* with the entity name once
    corporate suffixes are stripped, and anything left over must be a
    divisional qualifier — so "NVIDIA PUBLIC SECTOR CORPORATION" still matches
    while "APPLE BUS COMPANY" does not.

    An explicit alias in ``extra_aliases`` (a known subsidiary's full legal
    name) matches on its own terms.
    """
    text = clean_legal_name((candidate or "").upper())
    if not text:
        return False

    for alias in extra_aliases or []:
        if text == clean_legal_name(alias.upper()):
            return True

    words = text.split()
    for pattern in entity_match_patterns(name):
        target = pattern.split()
        if words[:len(target)] != target:
            continue
        remainder = words[len(target):]
        if all(w.lower() in DIVISION_TOKENS for w in remainder):
            return True
    return False


def entity_in_caption(caption: str, name: str,
                      extra_aliases: Optional[List[str]] = None) -> bool:
    """
    Whether the entity is a named party in a case caption.

    Captions carry two or more parties, so each side is tested separately
    rather than matching against the whole string.
    """
    text = (caption or "").strip()
    if not text:
        return False

    # Consolidated actions are captioned "In re <Company> Securities Litigation"
    # rather than as adversary proceedings, so peel off the wrapper first.
    text = re.sub(r"^in\s+re:?\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(
        r"\s+(securities|derivative|antitrust|patent|consumer|products?\s+liability)?"
        r"\s*litigation$", "", text, flags=re.IGNORECASE)

    parties = re.split(r"\s+v\.?s?\.?\s+|\s*,\s*et al\.?", text, flags=re.IGNORECASE)
    return any(matches_entity(p, name, extra_aliases) for p in parties if p.strip())
