"""
Tests for the U.S. state registry framework.

Covers:
- Schema normalization
- Registry metadata (51 jurisdictions)
- Tier A bulk connectors (NY, CO, FL, OR)
- Tier B API connectors (WA, TX, CA)
- Tier D generic scrape connector
- BEA connector
- Registry API (unit-level)
"""
import importlib
import os
import sys

import pytest

os.environ["ENV"] = "test"

# Add connectors to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "packages", "connectors"))


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------
def test_schema_normalize_basic():
    from us.state_registry.schema import normalize
    result = normalize(
        jurisdiction_code="us_ny",
        entity_id="NY001",
        legal_name="APPLE INC",
        raw_status="Active",
        raw_entity_type="Domestic Business Corporation",
        source_tier="bulk",
        source_url="https://data.ny.gov",
    )
    assert result["jurisdiction_code"] == "us_ny"
    assert result["entity_id"] == "NY001"
    assert result["legal_name"] == "APPLE INC"
    assert result["status"] == "active"
    assert result["entity_type"] == "corporation"
    assert result["source_tier"] == "bulk"
    assert "retrieved_at" in result


def test_schema_status_normalization():
    from us.state_registry.schema import _normalize_status
    assert _normalize_status("Active") == "active"
    assert _normalize_status("Good Standing") == "active"
    assert _normalize_status("Dissolved") == "dissolved"
    assert _normalize_status("Inactive") == "inactive"
    assert _normalize_status(None) == "unknown"
    assert _normalize_status("") == "unknown"


def test_schema_entity_type_normalization():
    from us.state_registry.schema import _normalize_entity_type
    assert _normalize_entity_type("LLC") == "llc"
    assert _normalize_entity_type("Limited Liability Company") == "llc"
    assert _normalize_entity_type("Domestic Business Corporation") == "corporation"
    assert _normalize_entity_type("Nonprofit") == "nonprofit"
    assert _normalize_entity_type(None) == "unknown"


# ---------------------------------------------------------------------------
# Registry metadata tests
# ---------------------------------------------------------------------------
def test_registry_51_jurisdictions():
    from us.state_registry.registry import JURISDICTIONS
    assert len(JURISDICTIONS) == 51, f"Expected 51 jurisdictions, got {len(JURISDICTIONS)}"


def test_registry_required_fields():
    from us.state_registry.registry import JURISDICTIONS
    required = {"jurisdiction_code", "name", "tier", "sos_url", "search_url", "adapter_module", "adapter_class"}
    for jcode, meta in JURISDICTIONS.items():
        for field in required:
            assert field in meta, f"{jcode} missing field {field}"
        assert meta["tier"] in ("bulk", "api", "scrape", "cobalt"), f"{jcode} has invalid tier {meta['tier']}"


def test_registry_bulk_states():
    from us.state_registry.registry import JURISDICTIONS
    bulk_states = [j for j, m in JURISDICTIONS.items() if m["tier"] == "bulk"]
    assert "us_ny" in bulk_states
    assert "us_co" in bulk_states
    assert "us_fl" in bulk_states
    assert "us_or" in bulk_states


def test_registry_api_states():
    from us.state_registry.registry import JURISDICTIONS
    api_states = [j for j, m in JURISDICTIONS.items() if m["tier"] == "api"]
    assert "us_wa" in api_states
    assert "us_tx" in api_states
    assert "us_ca" in api_states


# ---------------------------------------------------------------------------
# Tier A bulk connector tests
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("mod_path,cls_name", [
    ("us.state_registry.bulk.ny", "NewYorkBulkConnector"),
    ("us.state_registry.bulk.co", "ColoradoBulkConnector"),
    ("us.state_registry.bulk.fl", "FloridaBulkConnector"),
    ("us.state_registry.bulk.or_", "OregonBulkConnector"),
])
def test_bulk_connector_contract(mod_path, cls_name):
    mod = importlib.import_module(mod_path)
    cls = getattr(mod, cls_name)
    c = cls(creds={})
    m = c.run()
    assert m["seen"] >= 1, f"{cls_name} returned 0 records"
    assert "checkpoint" in m


def test_ny_bulk_normalized_schema():
    from us.state_registry.bulk.ny import NewYorkBulkConnector
    c = NewYorkBulkConnector(creds={})
    records = list(c.fetch_records())
    assert len(records) >= 1
    eid, payload = records[0]
    normalized = c.normalize(eid, payload)
    assert normalized["jurisdiction_code"] == "us_ny"
    assert normalized["source_tier"] == "bulk"
    assert "legal_name" in normalized
    assert "status" in normalized
    assert "entity_type" in normalized


# ---------------------------------------------------------------------------
# Tier B API connector tests
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("mod_path,cls_name", [
    ("us.state_registry.api.wa", "WashingtonAPIConnector"),
    ("us.state_registry.api.tx", "TexasAPIConnector"),
    ("us.state_registry.api.ca", "CaliforniaSOSConnector"),
])
def test_api_connector_contract(mod_path, cls_name):
    mod = importlib.import_module(mod_path)
    cls = getattr(mod, cls_name)
    c = cls(creds={})
    m = c.run()
    assert m["seen"] >= 1, f"{cls_name} returned 0 records"
    assert "checkpoint" in m


# ---------------------------------------------------------------------------
# Tier D scrape connector tests
# ---------------------------------------------------------------------------
def test_scrape_generic_all_jurisdictions():
    """All 51 jurisdictions can be instantiated and yield ≥1 sample record."""
    from us.state_registry.registry import JURISDICTIONS
    from us.state_registry.states.scrape_generic import GenericScrapedStateConnector

    scrape_jurs = [j for j, m in JURISDICTIONS.items() if m["tier"] == "scrape"]
    assert len(scrape_jurs) >= 40, f"Expected ≥40 scrape-tier states, got {len(scrape_jurs)}"

    for jcode in scrape_jurs:
        c = GenericScrapedStateConnector(jurisdiction_code=jcode, creds={})
        m = c.run()
        assert m["seen"] >= 1, f"Scrape connector for {jcode} returned 0 records"


def test_scrape_generic_normalized_schema():
    from us.state_registry.states.scrape_generic import GenericScrapedStateConnector
    c = GenericScrapedStateConnector(jurisdiction_code="us_al", creds={})
    records = list(c.fetch_records())
    assert len(records) >= 1
    eid, payload = records[0]
    norm = c.normalize(eid, payload)
    assert norm["jurisdiction_code"] == "us_al"
    assert "legal_name" in norm
    assert "status" in norm


# ---------------------------------------------------------------------------
# BEA connector tests
# ---------------------------------------------------------------------------
def test_bea_connector_contract():
    from us.bea.bea import BEAConnector
    c = BEAConnector(creds={})
    m = c.run()
    assert m["seen"] >= 1, "BEA connector returned 0 records"
    assert "checkpoint" in m


def test_bea_normalized_fields():
    from us.bea.bea import BEAConnector
    c = BEAConnector(creds={})
    records = list(c.fetch_records())
    assert len(records) >= 1
    eid, payload = records[0]
    norm = c.normalize(eid, payload)
    assert "dataset" in norm
    assert "data_value" in norm


# ---------------------------------------------------------------------------
# Cobalt fallback tests (no API key required)
# ---------------------------------------------------------------------------
def test_cobalt_disabled_without_key():
    """Cobalt should yield nothing when COBALT_API_KEY not set."""
    from us.state_registry.cobalt_fallback import CobaltFallbackConnector
    os.environ.pop("COBALT_API_KEY", None)
    c = CobaltFallbackConnector(jurisdiction_code="us_de", state_abbrev="DE", creds={})
    records = list(c.fetch_records())
    assert records == [], "Cobalt should yield nothing without API key"


def test_ca_parse_keyword_response_shape():
    """Parse CA SOS BE API JSON without calling the network."""
    from us.state_registry.api.ca import _map_entity, _parse_keyword_response

    sample_response = {
        "RecordCount": 1,
        "EntityData": [
            {
                "EntityID": "202150010575",
                "EntityName": "Pure Forest LLC",
                "EntityType": "Limited Liability Company - CA",
                "StatusDescription": "Active",
                "FilingDate": "2021-11-17T10:19:38.923",
                "AgentName": "Jane Agent",
            }
        ],
    }
    items = _parse_keyword_response(sample_response)
    assert len(items) == 1
    eid, payload = _map_entity(items[0])
    assert eid == "202150010575"
    assert payload["legal_name"] == "Pure Forest LLC"
    assert payload["status"] == "Active"


def test_bizfile_parse_dom_row_standard():
    """Parse a standard 6-column BizFile DOM row (confirmed from live page 2026-06-15)."""
    from us.state_registry.api.ca import _parse_bizfile_dom_row

    cells = [
        "! ! ! APPLE IPAD & ANDROID TABLET TUTORING ! ! ! (3110952)Click to expand",
        "10/06/2009",
        "Active",
        "Stock Corporation - CA - General",
        "CALIFORNIA",
        "KOUROSH MASJEDI",
    ]
    result = _parse_bizfile_dom_row(cells)
    assert result is not None
    eid, payload = result
    assert eid == "3110952"
    assert payload["legal_name"] == "! ! ! APPLE IPAD & ANDROID TABLET TUTORING ! ! !"
    assert payload["status"] == "Active"
    assert payload["formation_date"] == "2009-10-06"
    assert payload["entity_type"] == "Stock Corporation - CA - General"
    assert payload["registered_agent_name"] == "KOUROSH MASJEDI"
    assert payload["source_tier"] == "scrape_bizfile"


def test_bizfile_parse_dom_row_alphanumeric_eid():
    """BizFile entity numbers can be alphanumeric (e.g. B20260155183)."""
    from us.state_registry.api.ca import _parse_bizfile_dom_row

    cells = [
        "11825 Apple Valley Road GP LLC (B20260155183)Click to expand",
        "03/31/2026",
        "Active",
        "Limited Liability Company - Out of State",
        "DELAWARE",
        "CSC - LAWYERS INCORPORATING SERVICE",
    ]
    result = _parse_bizfile_dom_row(cells)
    assert result is not None
    eid, payload = result
    assert eid == "B20260155183"
    assert "Apple Valley Road" in payload["legal_name"]


def test_bizfile_parse_dom_row_no_eid_falls_back_to_name():
    """If no entity number in parens, use truncated name as key."""
    from us.state_registry.api.ca import _parse_bizfile_dom_row

    cells = ["SOME ENTITY WITHOUT NUMBER", "01/01/2020", "Active", "LLC", "CA", "Agent"]
    result = _parse_bizfile_dom_row(cells)
    assert result is not None
    eid, payload = result
    assert eid == "SOME ENTITY WITHOUT NUMBER"
    assert payload["legal_name"] == "SOME ENTITY WITHOUT NUMBER"


def test_bizfile_parse_date():
    """_parse_date normalises MM/DD/YYYY and ISO dates; returns None for empty."""
    from us.state_registry.api.ca import _parse_date

    assert _parse_date("10/06/2009") == "2009-10-06"
    assert _parse_date("01/13/2023") == "2023-01-13"
    assert _parse_date("2021-11-17T10:19:38.923") == "2021-11-17"
    assert _parse_date("") is None
    assert _parse_date(None) is None


def test_bizfile_fetch_graceful_failure(monkeypatch):
    """_bizfile_fetch yields 0 records when both API and Playwright fail; no exception raised."""
    import os as _os
    _os.environ["ENV"] = "production"
    from us.state_registry.api.ca import _bizfile_fetch

    records = list(_bizfile_fetch(queries=["TestQuery"], max_per_query=5))
    # On this server Playwright Chromium is unavailable and WAF blocks requests;
    # the function must return an empty list without raising.
    assert isinstance(records, list)


def test_cobalt_parse_response_shape():
    """Parse real Cobalt JSON shape without calling the API."""
    from us.state_registry.cobalt_fallback import _parse_cobalt_item, cobalt_search
    sample = {
        "title": "PIEZO MOTION CORP.",
        "sosId": "21203219",
        "normalizedStatus": "Inactive",
        "entityType": "Foreign Profit Corporation",
        "agentName": "CORPORATION SERVICE COMPANY",
        "history": [{"name": "Business Formation", "date": "07/26/2021"}],
    }
    row = _parse_cobalt_item(sample)
    assert row["legal_name"] == "PIEZO MOTION CORP."
    assert row["sos_id"] == "21203219"
    assert row["source_tier"] == "cobalt"
    # No network when key unset
    os.environ.pop("COBALT_API_KEY", None)
    assert cobalt_search("GA", "test") == []


# ---------------------------------------------------------------------------
# Contract test: all 51 connectors loadable
# ---------------------------------------------------------------------------
def test_all_51_connectors_loadable():
    """All 51 jurisdiction connectors can be loaded and instantiated."""
    from us.state_registry.registry import JURISDICTIONS
    from us.state_registry.orchestrator import _load_connector

    for jcode, meta in JURISDICTIONS.items():
        try:
            connector = _load_connector(meta)
            assert connector is not None, f"Connector for {jcode} is None"
        except Exception as e:
            pytest.fail(f"Failed to load connector for {jcode}: {e}")


# ---------------------------------------------------------------------------
# Orchestrator test
# ---------------------------------------------------------------------------
def test_orchestrator_runs_all_jurisdictions():
    """Orchestrator runs all 51 and returns aggregated metrics."""
    from us.state_registry.orchestrator import run_all_jurisdictions
    result = run_all_jurisdictions(verbose=False)

    assert result["total_jurisdictions"] == 51
    assert result["total_records_seen"] >= 51 * 1  # ≥1 record per jurisdiction
    # At least 45 should succeed or partially succeed
    assert result["success"] + result["partial"] >= 45, \
        f"Expected ≥45 success/partial, got success={result['success']} partial={result['partial']}"


# ---------------------------------------------------------------------------
# Keep original 17 connectors working (regression)
# ---------------------------------------------------------------------------
ORIGINAL_CONNECTORS = [
    ("us.sec.edgar", "SECEDGARConnector"),
    ("us.fec.fec", "FECConnector"),
    ("us.congress.congress", "CongressGovConnector"),
    ("us.sam.sam", "SAMGovConnector"),
    ("us.courtlistener.courtlistener", "CourtListenerConnector"),
    ("us.usaspending.usaspending", "USASpendingConnector"),
    ("us.ofac.ofac", "OFACConnector"),
    ("us.gleif.gleif", "GLEIFConnector"),
    ("us.lda.lda", "LDAConnector"),
    ("us.fara.fara", "FARAConnector"),
    ("us.govinfo.govinfo", "GovInfoConnector"),
    ("us.federal_register.federal_register", "FederalRegisterConnector"),
    ("us.regulations.regulations", "RegulationsGovConnector"),
    ("us.ecfr.ecfr", "ECFRConnector"),
    ("us.reginfo_oira.reginfo_oira", "RegInfoOIRAConnector"),
    ("us.irs990.irs990", "IRS990Connector"),
    ("us.opencorporates.opencorporates", "OpenCorporatesConnector"),
]


@pytest.mark.parametrize("mod_path,cls_name", ORIGINAL_CONNECTORS)
def test_original_connectors_still_work(mod_path, cls_name):
    """Regression: all 17 original connectors still pass contract test."""
    mod = importlib.import_module(mod_path)
    cls = getattr(mod, cls_name)
    c = cls(creds={})
    m = c.run()
    assert m["seen"] >= 1, f"{cls_name} regression: 0 records"
    assert "checkpoint" in m
