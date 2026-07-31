"""
Entity name normalisation and matching.

The cases here are drawn from real false positives observed in generated
reports: an Apple report whose federal contract ledger listed "TOWN OF APPLE
VALLEY" and "BIG APPLE SIGN CORP", and a Target report whose litigation table
listed "United States v. Lopez".
"""
import pytest

from app.connectors.entity_naming import (
    clean_legal_name,
    entity_in_caption,
    entity_search_term,
    matches_entity,
)


@pytest.mark.parametrize("legal_name,expected", [
    ("NVIDIA Corporation", "NVIDIA"),
    ("Apple Inc.", "Apple"),
    ("The Coca-Cola Company", "Coca-Cola"),
    ("Bank of America Corporation", "Bank of America"),
    ("JPMorgan Chase & Co.", "JPMorgan"),
    ("Advanced Micro Devices, Inc.", "Advanced Micro"),
    ("Target Corporation", "Target"),
    ("3M Company", "3M"),
])
def test_search_term_is_distinctive(legal_name, expected):
    assert entity_search_term(legal_name) == expected


def test_clean_legal_name_drops_dangling_ampersand():
    assert clean_legal_name("JPMorgan Chase & Co.") == "JPMorgan Chase"


@pytest.mark.parametrize("recipient", [
    "APPLE INC",
    "Apple Inc.",
])
def test_recipient_accepts_the_company(recipient):
    assert matches_entity(recipient, "Apple Inc.")


@pytest.mark.parametrize("recipient", [
    "TOWN OF APPLE VALLEY",
    "CITY OF APPLE VALLEY",
    "BIG APPLE SIGN CORP.",
    "WASHINGTON APPLE COMMISSION",
    "APPLE BUS COMPANY",
    "MAYER BROS. APPLE PRODUCTS INC.",
    "KEYSTONE APPLE INC",
    "APPLE 1 ENTERPRISES, INC.",
    "APPLE CONSTRUCTION COMPANY",
])
def test_recipient_rejects_unrelated_names_sharing_a_common_word(recipient):
    assert not matches_entity(recipient, "Apple Inc.")


@pytest.mark.parametrize("recipient,expected", [
    ("NVIDIA CORPORATION", True),
    # A divisional qualifier does not make it a different organisation.
    ("NVIDIA PUBLIC SECTOR CORPORATION", True),
    ("ENVIDIA FLOORS", False),
    ("INVIDIA SALON AND SPA", False),
])
def test_recipient_matching_handles_substring_collisions(recipient, expected):
    assert matches_entity(recipient, "NVIDIA Corporation") is expected


def test_chartered_bank_subsidiary_matches_parent():
    assert matches_entity("JPMORGAN CHASE BANK, NATIONAL ASSOCIATION",
                          "JPMORGAN CHASE & CO")


def test_unrelated_bank_sharing_a_word_is_rejected():
    assert not matches_entity("APPLE BANK FOR SAVINGS", "Apple Inc.")


def test_subsidiary_matches_only_when_declared():
    subsidiary = "The Portland Group Incorporated"
    assert not matches_entity(subsidiary, "NVIDIA Corporation")
    assert matches_entity(subsidiary, "NVIDIA Corporation", [subsidiary])


@pytest.mark.parametrize("caption,expected", [
    ("Castillo de Ramirez v. TARGET CORPORATION", True),
    ("Intel Corp v. Nvidia Corp", False),
    ("United States v. Lopez", False),
    ("Jason Franco v. Chobani, LLC", False),
])
def test_caption_identifies_named_parties_only(caption, expected):
    assert entity_in_caption(caption, "Target Corp") is expected


def test_caption_handles_consolidated_actions():
    assert entity_in_caption("In re Apple Inc. Securities Litigation", "Apple Inc.")
