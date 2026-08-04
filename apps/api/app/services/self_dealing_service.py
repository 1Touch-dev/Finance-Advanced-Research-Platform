"""
Self-Dealing Cross-Reference Service
────────────────────────────────────────────────────────────────────────────
Cross-references the conflict disclosures an issuer is obliged to make against
the other registers the report already reads, and scores what corroborates
what.

Every input here is already in the report. Item 404 names the related-person
transactions; Section 16 names the insiders and, through their Form 3 filings,
the other boards they sit on; USASpending names the federal counterparties. Each
was presented separately, so a proxy that discloses a $108m transaction with an
entity a sitting director also governs read as two unremarkable facts on
different pages.

What this adds is the join. A disclosed transaction is not itself a finding — the
issuer disclosed it — but a disclosed transaction whose counterparty turns up in
the insider register, on a director's other board, or on the federal award ledger
is a different proposition, and that is what is scored below.

Nothing is inferred about intent. A finding states which registers named the same
party and leaves the reader to judge it.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Sequence, Set

from app.services.person_disambiguation import (
    company_core_name,
    is_same_company,
    normalize_person_name,
    person_name_parts,
)

logger = logging.getLogger(__name__)

# Weights are ordinal, not probabilistic: they order findings for a reader
# rather than estimating a likelihood of wrongdoing.
_WEIGHT_BOARD_SEAT = 40
_WEIGHT_FEDERAL_COUNTERPARTY = 30
_WEIGHT_INSIDER_SURNAME = 25
_WEIGHT_FAMILY_EMPLOYMENT = 20
_WEIGHT_INSTITUTIONAL_HOLDER = 10

# Magnitude bands for the disclosed amount. A related-party transaction of a few
# thousand dollars and one of a hundred million are not the same disclosure.
_AMOUNT_BANDS = ((100_000_000, 25), (10_000_000, 15), (1_000_000, 8))

# Words that make a candidate a description rather than a party.
_NON_PARTY = re.compile(
    r"^(the\s+)?(company|issuer|board|committee|corporation|registrant|"
    r"compensation|audit|nominating|governance)\b", re.IGNORECASE)

# Entities whose names are built from a person's surname. A foundation, trust or
# family office carrying an insider's surname is the vehicle Item 404 exists to
# surface, and matching on the surname is how it is found.
_EPONYMOUS_MARKERS = re.compile(
    r"\b(foundation|trust|family|estate|holdings?|partners?|ventures?|capital|"
    r"lp|llc|llp|fund|office)\b", re.IGNORECASE)


def _clean_party(name: str) -> Optional[str]:
    """A counterparty name worth cross-referencing, or None."""
    text = " ".join((name or "").split()).strip(" .,;:")
    if len(text) < 3 or _NON_PARTY.match(text):
        return None
    return text


def _insider_names(insider_transactions: Dict[str, Any]) -> List[Dict[str, Any]]:
    """One entry per distinct Section 16 filer, with the roles they report."""
    people: Dict[str, Dict[str, Any]] = {}
    for row in (insider_transactions or {}).get("transactions", []) or []:
        name = row.get("insider") or row.get("owner_name") or ""
        if not name:
            continue
        key = normalize_person_name(name)
        if not key:
            continue
        entry = people.setdefault(key, {
            "name": name, "roles": set(),
            # Section 16 indexes surname first without a comma, so "COXE TENCH"
            # is Mr Coxe and not Mr Tench. Which token is the surname cannot be
            # known from the string, so both ends are kept as candidates and a
            # match on either is a match — the alternative was a family
            # foundation carrying a director's surname going unmatched against
            # that director's own insider filings.
            "surnames": set(),
        })
        entry["roles"].update(row.get("roles") or [])
        first, _, last = person_name_parts(name)
        entry["surnames"].update(s for s in (first, last) if s)
    return [
        {"name": p["name"], "roles": sorted(p["roles"]),
         "surnames": sorted(p["surnames"])}
        for p in people.values()
    ]


def _interlock_seats(board_interlocks: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Every outside issuer an insider is recorded as sitting at."""
    seats: List[Dict[str, Any]] = []
    for person in (board_interlocks or {}).get("people", []) or []:
        for seat in person.get("other_seats") or []:
            issuer = _clean_party(seat.get("issuer") or "")
            if not issuer:
                continue
            seats.append({
                "person": person.get("name", ""),
                "roles_at_issuer": person.get("roles_at_issuer") or [],
                "issuer": issuer,
                "current": seat.get("current"),
                "last_filed": seat.get("last_filed"),
                "source_url": seat.get("source_url"),
            })
    return seats


def _award_counterparties(contract_intelligence: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Recipients and sub-recipients on the federal award ledger."""
    parties: Dict[str, Dict[str, Any]] = {}

    def record(name: str, amount: Any, kind: str) -> None:
        cleaned = _clean_party(name)
        if not cleaned:
            return
        key = company_core_name(cleaned) or cleaned.lower()
        entry = parties.setdefault(key, {
            "name": cleaned, "amount": 0.0, "kind": kind, "count": 0,
        })
        try:
            entry["amount"] += float(amount or 0)
        except (TypeError, ValueError):
            pass
        entry["count"] += 1

    contracts = contract_intelligence or {}
    for sub in contracts.get("subcontracts") or []:
        record(sub.get("sub_awardee") or sub.get("sub_awardee_or_recipient_legal")
               or sub.get("recipient"), sub.get("amount"), "sub-award")
    for award in contracts.get("contracts") or []:
        record(award.get("recipient"), award.get("amount"), "prime award")

    return sorted(parties.values(), key=lambda p: -p["amount"])


def _amount_score(amount: Optional[float]) -> int:
    """Score contribution from the size of the disclosed transaction."""
    if not amount:
        return 0
    for threshold, points in _AMOUNT_BANDS:
        if amount >= threshold:
            return points
    return 0


def _entity_is_eponymous(party: str, person_surname: str) -> bool:
    """Whether an entity name is built on a person's surname.

    "Huang Family Foundation" and an insider named Huang are the relationship
    Item 404 is written to disclose. A bare surname collision inside an ordinary
    company name is not, so a vehicle marker is required as well.
    """
    if not person_surname or len(person_surname) < 3:
        return False
    if not re.search(rf"\b{re.escape(person_surname)}\b", party, re.IGNORECASE):
        return False
    return bool(_EPONYMOUS_MARKERS.search(party))


def cross_reference_self_dealing(
    related_party_transactions: Sequence[Dict[str, Any]],
    insider_transactions: Optional[Dict[str, Any]] = None,
    board_interlocks: Optional[Dict[str, Any]] = None,
    contract_intelligence: Optional[Dict[str, Any]] = None,
    family_network: Optional[Dict[str, Any]] = None,
    institutional_holders: Optional[Sequence[Dict[str, Any]]] = None,
    entity_name: str = "",
) -> Dict[str, Any]:
    """Score each disclosed related-party transaction against the other registers.

    Returns findings ordered by how much corroboration they carry, each naming
    the registers that independently mention the same party.
    """
    result: Dict[str, Any] = {
        "entity_name": entity_name,
        "findings": [],
        "unmatched": [],
        "summary": {
            "transactions_examined": 0,
            "transactions_corroborated": 0,
            "board_seat_matches": 0,
            "federal_counterparty_matches": 0,
            "insider_surname_matches": 0,
            "largest_corroborated_amount": None,
            "risk_level": "NONE",
        },
        "inputs_available": {
            "item_404": bool(related_party_transactions),
            "insider_register": bool((insider_transactions or {}).get("transactions")),
            "board_interlocks": bool((board_interlocks or {}).get("people")),
            "federal_awards": bool((contract_intelligence or {}).get("contracts")),
            "family_network": bool(family_network),
        },
    }

    insiders = _insider_names(insider_transactions or {})
    seats = _interlock_seats(board_interlocks or {})
    awards = _award_counterparties(contract_intelligence or {})
    holders = [
        _clean_party(h.get("manager") or h.get("name") or "")
        for h in (institutional_holders or [])
    ]
    holders = [h for h in holders if h]

    family_people = [
        member.get("name", "")
        for member in (family_network or {}).get("family_members", []) or []
        if member.get("name")
    ]

    for transaction in related_party_transactions or []:
        # Policy language and boilerplate indemnities describe no counterparty
        # and are excluded rather than scored as unmatched.
        if transaction.get("is_routine"):
            continue

        result["summary"]["transactions_examined"] += 1
        parties = [p for p in (
            _clean_party(c) for c in transaction.get("counterparties") or []
        ) if p]
        amount = transaction.get("largest_amount")

        evidence: List[Dict[str, Any]] = []
        score = _amount_score(amount)

        for party in parties:
            # 1. The counterparty is a company one of this issuer's insiders
            #    also governs.
            for seat in seats:
                if is_same_company(party, seat["issuer"]):
                    score += _WEIGHT_BOARD_SEAT
                    evidence.append({
                        "type": "board_seat",
                        "detail": (f"{seat['person']}, "
                                   f"{', '.join(seat['roles_at_issuer']) or 'an insider'} "
                                   f"at {entity_name or 'the issuer'}, is recorded "
                                   f"at {seat['issuer']} in Section 16"),
                        "party": party,
                        "person": seat["person"],
                        "current": seat.get("current"),
                        "source_url": seat.get("source_url"),
                    })

            # 2. The counterparty also appears on the federal award ledger, so
            #    public money and a disclosed conflict meet at one party.
            for award in awards:
                if is_same_company(party, award["name"]):
                    score += _WEIGHT_FEDERAL_COUNTERPARTY
                    evidence.append({
                        "type": "federal_counterparty",
                        "detail": (f"{award['name']} appears on the federal award "
                                   f"ledger as a {award['kind']} totalling "
                                   f"${award['amount']:,.0f} across "
                                   f"{award['count']} record"
                                   f"{'' if award['count'] == 1 else 's'}"),
                        "party": party,
                        "amount": award["amount"],
                    })

            # 3. The counterparty is a vehicle carrying an insider's surname.
            for insider in insiders:
                if any(_entity_is_eponymous(party, s)
                       for s in insider["surnames"]):
                    score += _WEIGHT_INSIDER_SURNAME
                    evidence.append({
                        "type": "insider_surname",
                        "detail": (f"{party} carries the surname of "
                                   f"{insider['name']}, who files under Section 16"
                                   + (f" as {', '.join(insider['roles'])}"
                                      if insider["roles"] else "")),
                        "party": party,
                        "person": insider["name"],
                    })

            # 4. The counterparty is also a reported institutional holder, so the
            #    same party is on both sides of the register.
            for holder in holders:
                if is_same_company(party, holder):
                    score += _WEIGHT_INSTITUTIONAL_HOLDER
                    evidence.append({
                        "type": "institutional_holder",
                        "detail": f"{holder} is also a reported 13F holder",
                        "party": party,
                    })

        # 5. A family-employment disclosure corroborated by a Section 16 filer or
        #    a mapped relative of the same surname.
        if transaction.get("relationship"):
            related_surnames: Set[str] = set()
            for relative in family_people:
                first, _, last = person_name_parts(relative)
                related_surnames.update(s for s in (first, last) if s)
            for insider in insiders:
                if set(insider["surnames"]) & related_surnames:
                    score += _WEIGHT_FAMILY_EMPLOYMENT
                    evidence.append({
                        "type": "family_employment",
                        "detail": (f"the disclosure names a "
                                   f"{transaction['relationship']} and "
                                   f"{insider['name']} files under Section 16 "
                                   f"with the same surname"),
                        "person": insider["name"],
                    })
                    break

        entry = {
            "category": transaction.get("category"),
            "relationship": transaction.get("relationship"),
            "counterparties": parties,
            "amount": amount,
            "score": score,
            "evidence": evidence,
            "text": transaction.get("text"),
        }

        if evidence:
            result["findings"].append(entry)
            result["summary"]["transactions_corroborated"] += 1
            for item in evidence:
                key = {
                    "board_seat": "board_seat_matches",
                    "federal_counterparty": "federal_counterparty_matches",
                    "insider_surname": "insider_surname_matches",
                }.get(item["type"])
                if key:
                    result["summary"][key] += 1
            if amount:
                largest = result["summary"]["largest_corroborated_amount"]
                if largest is None or amount > largest:
                    result["summary"]["largest_corroborated_amount"] = amount
        else:
            result["unmatched"].append(entry)

    result["findings"].sort(key=lambda f: (-f["score"], -(f["amount"] or 0)))

    # The level describes how much independent corroboration exists, not a
    # judgement about the issuer.
    top = result["findings"][0]["score"] if result["findings"] else 0
    if top >= 65:
        result["summary"]["risk_level"] = "HIGH"
    elif top >= 40:
        result["summary"]["risk_level"] = "ELEVATED"
    elif top > 0:
        result["summary"]["risk_level"] = "LOW"

    return result


def render_self_dealing_markdown(analysis: Dict[str, Any]) -> List[str]:
    """Render the cross-reference as markdown for the report."""
    summary = analysis.get("summary", {}) or {}
    examined = summary.get("transactions_examined", 0)
    if not examined:
        return []

    entity = analysis.get("entity_name") or "the issuer"
    lines = ["## Related-Party Cross-Reference", ""]

    corroborated = summary.get("transactions_corroborated", 0)
    lines.append(
        f"Each of the {examined} non-routine related-person transactions "
        f"{entity} disclosed under Item 404 was checked against the Section 16 "
        f"insider register, the outside board seats those insiders report on "
        f"Form 3, the federal award ledger and the reported institutional "
        f"holders. {corroborated} of them name a party that at least one of "
        f"those registers names as well."
    )
    lines.append("")

    if not analysis.get("findings"):
        lines.append(
            "No disclosed counterparty could be tied to an insider's other "
            "board seat, to a federal award recipient or to an entity carrying "
            "an insider's surname. A disclosure that no other register "
            "corroborates is the ordinary case, and is reported as such rather "
            "than left to look like an unexamined risk."
        )
        lines.append("")
        return lines

    lines.append(f"**Corroboration level:** {summary.get('risk_level', 'NONE')}")
    lines.append("")

    for finding in analysis["findings"][:10]:
        parties = ", ".join(finding["counterparties"]) or "an unnamed party"
        amount = finding.get("amount")
        heading = f"### {parties}"
        lines.append(heading)
        detail = [f"Category: {finding.get('category') or 'unclassified'}"]
        if finding.get("relationship"):
            detail.append(f"relationship disclosed as {finding['relationship']}")
        if amount:
            detail.append(f"largest disclosed amount ${amount:,.0f}")
        lines.append("; ".join(detail).capitalize() + ".")
        lines.append("")
        for item in finding["evidence"]:
            lines.append(f"- {item['detail']}.")
        lines.append("")
        if finding.get("text"):
            lines.append(f"> {finding['text'][:400]}")
            lines.append("")

    unmatched = analysis.get("unmatched") or []
    if unmatched:
        lines.append(
            f"A further {len(unmatched)} disclosed transaction"
            f"{'' if len(unmatched) == 1 else 's'} named no party that appears "
            f"in another register."
        )
        lines.append("")

    absent = [name for name, present
              in (analysis.get("inputs_available") or {}).items() if not present]
    if absent:
        lines.append(
            f"*Registers unavailable for this run: {', '.join(sorted(absent))}. "
            f"A cross-reference can only find what both sides supply, so an "
            f"absent register narrows the check rather than clearing the "
            f"issuer.*"
        )
        lines.append("")

    return lines
