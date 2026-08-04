"""
Regression tests for the people and peer-comparison fixes.

Every case here corresponds to something a delivered report got wrong. All of
them failed silently — an empty section, a blank column, a confident sentence
about the wrong person — so each is pinned rather than left to be noticed again
in a client's hands.
"""

import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.connectors import opensecrets_connector as oc
from app.services.data_health_service import _payload_error
from app.services.deep_comparative_service import (
    _calculate_percentile_rank,
    _metrics_from_sec_facts,
    _xbrl_annual_series,
)
from app.services.founder_correlations_service import (
    build_founder_correlation_graph,
    extract_educational_background,
)
from app.services.person_disambiguation import (
    birth_year_from_age,
    clean_company_name,
    extract_bio_companies,
    is_valid_company_name,
    plausible_authorship,
    same_person,
)
from app.services.self_dealing_service import cross_reference_self_dealing


# ── Person identity ──────────────────────────────────────────────────────────

def test_shared_surname_is_not_the_same_person():
    """Books by an unrelated Hudson were attributed to the director Hudson."""
    assert not same_person("Dawn Bennett Hudson", "Dawn Hudson")
    assert not same_person("David Hudson", "Dawn Hudson")


def test_dropped_middle_initial_is_still_the_same_person():
    assert same_person("Harvey C. Jones", "Harvey Jones")


def test_section_16_surname_first_names_resolve():
    """Form 4 indexes surname first; the proxy does not."""
    assert same_person("HUANG JEN HSUN", "Jen-Hsun Huang")
    assert same_person("COLETTE KRESS", "Colette M. Kress")


def test_publication_predating_birth_is_rejected():
    born = birth_year_from_age(68, as_of=2026)
    assert not plausible_authorship(1796, born)   # the 18th-century namesake
    assert plausible_authorship(2015, born)


def test_no_birth_year_still_rejects_centuries_old_works():
    assert not plausible_authorship(1796, None)


# ── Company names out of prose ───────────────────────────────────────────────

def test_person_and_clause_fragments_are_not_companies():
    people = ["John O. Dabiri", "Dawn Hudson"]
    assert not is_valid_company_name("Biden", people)
    assert not is_valid_company_name("Dawn Hudson Speaks at the U", people)
    assert not is_valid_company_name("Marketing", people)


def test_real_companies_survive():
    assert is_valid_company_name("Tensilica Inc", [])
    assert is_valid_company_name("Synopsys", [])
    assert clean_company_name("Nvidia in 1993") == "Nvidia"


def test_current_employer_is_excluded():
    assert not is_valid_company_name("NVIDIA", [], current_company="NVIDIA CORP")


def test_employer_follows_at_not_the_first_preposition():
    bio = ("He was Director of Marketing and MIS at Digital Communication "
           "Associates, a company.")
    names = [c["company"] for c in extract_bio_companies(bio)]
    assert "Digital Communication Associates" in names
    assert "Marketing" not in names


# ── Education overlaps ───────────────────────────────────────────────────────

def test_institution_is_extracted_without_trailing_clause():
    bio = ("Mr. Coxe holds a BA degree in Economics from Dartmouth College and "
           "an MBA degree from Harvard Business School.")
    found = {e["normalized_institution"] for e in extract_educational_background(bio)}
    assert found == {"Dartmouth College", "Harvard University"}


def test_two_alumni_of_one_school_are_a_connection():
    """This board reported zero educational links while sharing two schools."""
    people = [
        {"name": "Tench Coxe", "biography":
            "Mr. Coxe holds a BA degree from Dartmouth College and an MBA "
            "degree from Harvard Business School."},
        {"name": "Dawn Hudson", "biography":
            "Ms. Hudson holds a BA degree in English from Dartmouth College."},
        {"name": "Stephen C. Neal", "biography":
            "Mr. Neal holds an AB degree from Harvard University."},
    ]
    graph = build_founder_correlation_graph(people, "NVIDIA CORP")
    assert graph["network_stats"]["education_connections"] == 2
    institutions = {o["institution"] for o in graph["education_overlaps"]["overlaps"]}
    assert institutions == {"Dartmouth College", "Harvard University"}


def test_ticker_substring_does_not_create_a_network_membership():
    """"SQ" made Square Wave Ventures a PayPal-network company."""
    people = [
        {"name": "Harvey C. Jones", "biography":
            "Harvey C. Jones has been the Managing Partner of Square Wave "
            "Ventures since 2004."},
        {"name": "Other Person", "biography":
            "She has been a partner of Square Wave Ventures since 2010."},
    ]
    graph = build_founder_correlation_graph(people, "NVIDIA CORP")
    assert graph["company_overlaps"]["notable_network_connections"] == []


# ── Peer comparison ──────────────────────────────────────────────────────────

def _facts(concept_values):
    return {"facts": {"us-gaap": {
        concept: {"units": {"USD": [
            {"form": "10-K", "fp": "FY", "start": f"{year}-01-01",
             "end": f"{year}-12-31", "val": value, "filed": f"{year + 1}-02-01"}
            for year, value in years.items()
        ]}} for concept, years in concept_values.items()
    }}}


def test_series_prefers_the_currently_used_tag():
    """NVIDIA moved from one revenue tag to another and the stale one won,
    dividing a current gross profit by a four-year-old revenue."""
    facts = _facts({
        "RevenueFromContractWithCustomerExcludingAssessedTax": {2020: 100, 2021: 200},
        "Revenues": {2022: 400, 2023: 800},
    })
    series = _xbrl_annual_series(facts, [
        "RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"])
    assert series[0] == 800
    # Older periods are back-filled from the retired tag so growth stays computable.
    assert series == [800, 400, 200, 100]


def test_quarterly_comparatives_are_not_read_as_annual():
    facts = {"facts": {"us-gaap": {"Revenues": {"units": {"USD": [
        {"form": "10-K", "fp": "FY", "start": "2025-10-01", "end": "2025-12-31",
         "val": 25, "filed": "2026-02-01"},
        {"form": "10-K", "fp": "FY", "start": "2025-01-01", "end": "2025-12-31",
         "val": 100, "filed": "2026-02-01"},
    ]}}}}}
    assert _xbrl_annual_series(facts, ["Revenues"]) == [100]


def test_metrics_come_from_filings_without_any_vendor_key():
    """Peers rendered N/A whenever a vendor quota ran out mid-set."""
    facts = _facts({
        "Revenues": {2023: 1000, 2024: 1200},
        "GrossProfit": {2024: 700},
        "OperatingIncomeLoss": {2024: 500},
        "NetIncomeLoss": {2024: 400},
        "Assets": {2024: 2000},
        "StockholdersEquity": {2024: 1600},
    })
    metrics = _metrics_from_sec_facts(facts)
    assert round(metrics["gross_margin"], 4) == 0.5833
    assert round(metrics["net_margin"], 4) == 0.3333
    assert round(metrics["roe"], 4) == 0.25
    assert round(metrics["revenue_growth_yoy"], 4) == 0.2


def test_percentile_needs_a_distribution():
    """A 65.6% operating margin was published as the 0th percentile because it
    was the only value that resolved."""
    assert _calculate_percentile_rank(0.656, [0.656]) is None
    assert _calculate_percentile_rank(0.9, [0.1, 0.5, 0.9]) == 66


# ── Lobbying register ────────────────────────────────────────────────────────

class _Response:
    def __init__(self, status_code, payload=None, headers=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.headers = headers or {}
        self.text = ""

    @property
    def ok(self):
        return 200 <= self.status_code < 300

    @property
    def is_redirect(self):
        return self.status_code in (301, 302, 307, 308)

    def json(self):
        return self._payload


_FILING_PAGE = {"results": [{
    "client": {"name": "NVIDIA Corporation"},
    "registrant": {"name": "Akin Gump"},
    "income": "1200000",
    "filing_period_display": "Q1",
    "lobbying_activities": [{"general_issue_code_display": "Taxation"}],
}], "next": None}


def _reset_lda(base):
    oc.reset_lda_circuit()
    oc._LDA_STATE["base"] = base
    oc._LDA_STATE["tried"] = set()


def test_host_move_redirect_is_not_followed_to_a_bare_root():
    """The register's 301 drops the path; following it reads as a clean zero."""
    def fake_get(url, **kwargs):
        if "lda.senate.gov" in url:
            return _Response(301, headers={"Location": "https://lda.gov/"})
        return _Response(200, _FILING_PAGE)

    _reset_lda("https://lda.senate.gov/api/v1")
    with mock.patch.object(oc.requests, "get", side_effect=fake_get):
        summary = oc.fetch_lobbying_summary("NVIDIA Corporation", years=1)

    assert summary["filing_count"] == 1
    assert summary["total_spend"] == 1_200_000
    assert not summary.get("error")


def test_unreachable_register_records_a_reason_the_health_check_can_see():
    _reset_lda("https://lda.gov/api/v1")
    with mock.patch.object(oc.requests, "get", return_value=_Response(403)), \
            mock.patch.object(oc.time, "sleep", lambda *a: None):
        summary = oc.fetch_lobbying_summary("NVIDIA Corporation", years=1)

    assert summary["filing_count"] == 0
    assert summary["error"]
    # The probe reads the wrapper, not the summary nested inside it.
    assert _payload_error({"lobbying_summary": summary})


def test_a_genuine_zero_stays_a_zero():
    _reset_lda("https://lda.gov/api/v1")
    with mock.patch.object(oc.requests, "get",
                           return_value=_Response(200, {"results": [], "next": None})):
        summary = oc.fetch_lobbying_summary("Tiny Private Co", years=1)

    assert summary["filing_count"] == 0
    assert not summary.get("error")


# ── Self-dealing cross-reference ─────────────────────────────────────────────

def test_counterparty_on_a_directors_other_board_is_surfaced():
    analysis = cross_reference_self_dealing(
        [{"category": "entity transaction",
          "counterparties": ["Arm Holdings plc"],
          "largest_amount": 108_300_000.0,
          "is_routine": False,
          "text": "We purchased licenses from Arm Holdings plc."}],
        insider_transactions={"transactions": [
            {"insider": "COXE TENCH", "roles": ["Director"]}]},
        board_interlocks={"people": [{
            "name": "Tench Coxe",
            "roles_at_issuer": ["Director"],
            "other_seats": [{"issuer": "ARM HOLDINGS PLC", "current": True,
                             "last_filed": "2026-05-01"}],
        }]},
        entity_name="NVIDIA CORP",
    )
    assert analysis["summary"]["board_seat_matches"] == 1
    assert analysis["summary"]["risk_level"] == "HIGH"


def test_vehicle_carrying_an_insider_surname_is_surfaced():
    analysis = cross_reference_self_dealing(
        [{"category": "entity transaction",
          "counterparties": ["Coxe Family Foundation"],
          "largest_amount": 1_500_000.0,
          "is_routine": False,
          "text": "Contribution to the Coxe Family Foundation."}],
        insider_transactions={"transactions": [
            {"insider": "COXE TENCH", "roles": ["Director"]}]},
        entity_name="NVIDIA CORP",
    )
    assert analysis["summary"]["insider_surname_matches"] == 1


def test_boilerplate_and_unrelated_parties_are_not_findings():
    analysis = cross_reference_self_dealing(
        [{"category": "routine", "counterparties": ["The Company"],
          "is_routine": True, "text": "Indemnity agreements with directors."},
         {"category": "entity transaction", "counterparties": ["Acme Widget Supply"],
          "largest_amount": 50_000.0, "is_routine": False,
          "text": "We bought widgets from Acme Widget Supply."}],
        insider_transactions={"transactions": [
            {"insider": "COXE TENCH", "roles": ["Director"]}]},
        entity_name="NVIDIA CORP",
    )
    assert analysis["summary"]["transactions_examined"] == 1
    assert analysis["findings"] == []
    assert len(analysis["unmatched"]) == 1
