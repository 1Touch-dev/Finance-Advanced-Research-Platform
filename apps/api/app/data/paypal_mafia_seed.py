"""
PayPal Mafia Seed Data
══════════════════════════════════════════════════════════════════════════════

The 23 core members of the PayPal Mafia and their key relationships.
This is the seed data for James's "Follow the Money" demonstration.

Source: Public records, SEC filings, company announcements, news archives.
"""

from datetime import datetime
from typing import Dict, List, Any

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PAYPAL MAFIA MEMBERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PAYPAL_MAFIA_MEMBERS: List[Dict[str, Any]] = [
    {
        "id": "person:peter-thiel",
        "kind": "person",
        "name": "Peter Thiel",
        "identifiers": {
            "FEC": "C00575373",  # Thiel's PAC
        },
        "aliases": ["Peter Andreas Thiel"],
        "meta": {
            "role_at_paypal": "Co-founder, CEO",
            "paypal_equity": "~$55M from eBay sale",
            "current_net_worth": "~$9.4B (2024)",
        },
    },
    {
        "id": "person:elon-musk",
        "kind": "person",
        "name": "Elon Musk",
        "identifiers": {
            "CIK": "0001494730",  # SEC CIK
        },
        "aliases": ["Elon Reeve Musk"],
        "meta": {
            "role_at_paypal": "Co-founder (X.com merged with PayPal)",
            "paypal_equity": "~$165M from eBay sale",
            "current_net_worth": "~$200B+ (2024)",
        },
    },
    {
        "id": "person:reid-hoffman",
        "kind": "person",
        "name": "Reid Hoffman",
        "aliases": ["Reid Garrett Hoffman"],
        "meta": {
            "role_at_paypal": "COO, EVP",
            "paypal_equity": "Undisclosed",
        },
    },
    {
        "id": "person:max-levchin",
        "kind": "person",
        "name": "Max Levchin",
        "aliases": ["Max Rafael Levchin"],
        "meta": {
            "role_at_paypal": "Co-founder, CTO",
            "paypal_equity": "~$34M from eBay sale",
        },
    },
    {
        "id": "person:david-sacks",
        "kind": "person",
        "name": "David Sacks",
        "aliases": ["David Oliver Sacks"],
        "meta": {
            "role_at_paypal": "COO",
        },
    },
    {
        "id": "person:roelof-botha",
        "kind": "person",
        "name": "Roelof Botha",
        "aliases": ["Roelof Frederik Botha"],
        "meta": {
            "role_at_paypal": "CFO",
        },
    },
    {
        "id": "person:keith-rabois",
        "kind": "person",
        "name": "Keith Rabois",
        "aliases": [],
        "meta": {
            "role_at_paypal": "EVP Business Development",
        },
    },
    {
        "id": "person:steve-chen",
        "kind": "person",
        "name": "Steve Chen",
        "aliases": ["Steve Shih Chen"],
        "meta": {
            "role_at_paypal": "Engineer",
        },
    },
    {
        "id": "person:chad-hurley",
        "kind": "person",
        "name": "Chad Hurley",
        "aliases": ["Chad Meredith Hurley"],
        "meta": {
            "role_at_paypal": "Designer",
        },
    },
    {
        "id": "person:jawed-karim",
        "kind": "person",
        "name": "Jawed Karim",
        "aliases": [],
        "meta": {
            "role_at_paypal": "Engineer",
        },
    },
    {
        "id": "person:jeremy-stoppelman",
        "kind": "person",
        "name": "Jeremy Stoppelman",
        "aliases": [],
        "meta": {
            "role_at_paypal": "VP Engineering",
        },
    },
    {
        "id": "person:russel-simmons",
        "kind": "person",
        "name": "Russel Simmons",
        "aliases": [],
        "meta": {
            "role_at_paypal": "Engineer",
            "note": "Not the hip-hop mogul",
        },
    },
    {
        "id": "person:ken-howery",
        "kind": "person",
        "name": "Ken Howery",
        "aliases": ["Kenneth Howery"],
        "meta": {
            "role_at_paypal": "CFO",
        },
    },
    {
        "id": "person:luke-nosek",
        "kind": "person",
        "name": "Luke Nosek",
        "aliases": [],
        "meta": {
            "role_at_paypal": "Co-founder, VP Marketing",
        },
    },
    {
        "id": "person:joe-lonsdale",
        "kind": "person",
        "name": "Joe Lonsdale",
        "aliases": ["Joseph Lonsdale"],
        "meta": {
            "role_at_paypal": "Intern/Associate",
        },
    },
    {
        "id": "person:dave-mcclure",
        "kind": "person",
        "name": "Dave McClure",
        "aliases": ["David McClure"],
        "meta": {
            "role_at_paypal": "Director of Marketing",
        },
    },
    {
        "id": "person:premal-shah",
        "kind": "person",
        "name": "Premal Shah",
        "aliases": [],
        "meta": {
            "role_at_paypal": "Product Manager",
        },
    },
    {
        "id": "person:yishan-wong",
        "kind": "person",
        "name": "Yishan Wong",
        "aliases": [],
        "meta": {
            "role_at_paypal": "Engineering Manager",
        },
    },
    {
        "id": "person:jack-selby",
        "kind": "person",
        "name": "Jack Selby",
        "aliases": [],
        "meta": {
            "role_at_paypal": "Executive",
        },
    },
    {
        "id": "person:andrew-mccormack",
        "kind": "person",
        "name": "Andrew McCormack",
        "aliases": [],
        "meta": {
            "role_at_paypal": "Executive",
        },
    },
    {
        "id": "person:eric-jackson",
        "kind": "person",
        "name": "Eric M. Jackson",
        "aliases": ["Eric Jackson"],
        "meta": {
            "role_at_paypal": "Marketing",
            "note": "Author of 'The PayPal Wars'",
        },
    },
]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# KEY COMPANIES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

COMPANIES: List[Dict[str, Any]] = [
    # PayPal
    {
        "id": "org:paypal",
        "kind": "org",
        "name": "PayPal Holdings, Inc.",
        "identifiers": {
            "CIK": "0001633917",
            "ticker": "PYPL",
        },
        "meta": {"founded": "1998", "ipo": "2002", "acquired_by_ebay": "2002"},
    },
    # Thiel Companies
    {
        "id": "org:palantir",
        "kind": "org",
        "name": "Palantir Technologies Inc.",
        "identifiers": {
            "CIK": "0001321655",
            "ticker": "PLTR",
        },
        "meta": {"founded": "2003", "ipo": "2020"},
    },
    {
        "id": "fund:founders-fund",
        "kind": "fund",
        "name": "Founders Fund",
        "meta": {"founded": "2005", "aum": "~$11B"},
    },
    # Musk Companies
    {
        "id": "org:tesla",
        "kind": "org",
        "name": "Tesla, Inc.",
        "identifiers": {
            "CIK": "0001318605",
            "ticker": "TSLA",
        },
        "meta": {"founded": "2003", "ipo": "2010"},
    },
    {
        "id": "org:spacex",
        "kind": "org",
        "name": "Space Exploration Technologies Corp.",
        "identifiers": {},
        "aliases": ["SpaceX"],
        "meta": {"founded": "2002", "valuation": "~$180B"},
    },
    {
        "id": "org:boring-company",
        "kind": "org",
        "name": "The Boring Company",
        "meta": {"founded": "2016"},
    },
    {
        "id": "org:neuralink",
        "kind": "org",
        "name": "Neuralink Corp.",
        "meta": {"founded": "2016"},
    },
    {
        "id": "org:x-corp",
        "kind": "org",
        "name": "X Corp.",
        "aliases": ["Twitter"],
        "meta": {"acquired": "2022"},
    },
    # Hoffman Companies
    {
        "id": "org:linkedin",
        "kind": "org",
        "name": "LinkedIn Corporation",
        "identifiers": {
            "CIK": "0001271024",
        },
        "meta": {"founded": "2002", "acquired_by_microsoft": "2016"},
    },
    {
        "id": "fund:greylock",
        "kind": "fund",
        "name": "Greylock Partners",
        "meta": {"founded": "1965"},
    },
    # Levchin Companies
    {
        "id": "org:affirm",
        "kind": "org",
        "name": "Affirm Holdings, Inc.",
        "identifiers": {
            "CIK": "0001820953",
            "ticker": "AFRM",
        },
        "meta": {"founded": "2012", "ipo": "2021"},
    },
    {
        "id": "org:slide",
        "kind": "org",
        "name": "Slide, Inc.",
        "meta": {"founded": "2005", "acquired_by_google": "2010"},
    },
    # YouTube (Chen, Hurley, Karim)
    {
        "id": "org:youtube",
        "kind": "org",
        "name": "YouTube, LLC",
        "meta": {"founded": "2005", "acquired_by_google": "2006"},
    },
    # Yelp (Stoppelman, Simmons)
    {
        "id": "org:yelp",
        "kind": "org",
        "name": "Yelp Inc.",
        "identifiers": {
            "CIK": "0001345016",
            "ticker": "YELP",
        },
        "meta": {"founded": "2004", "ipo": "2012"},
    },
    # Sacks Companies
    {
        "id": "org:yammer",
        "kind": "org",
        "name": "Yammer, Inc.",
        "meta": {"founded": "2008", "acquired_by_microsoft": "2012"},
    },
    {
        "id": "fund:craft-ventures",
        "kind": "fund",
        "name": "Craft Ventures",
        "meta": {"founded": "2017"},
    },
    # Botha / Sequoia
    {
        "id": "fund:sequoia",
        "kind": "fund",
        "name": "Sequoia Capital",
        "meta": {"founded": "1972"},
    },
    # Rabois Companies
    {
        "id": "org:square",
        "kind": "org",
        "name": "Block, Inc.",
        "identifiers": {
            "CIK": "0001512673",
            "ticker": "SQ",
        },
        "aliases": ["Square"],
        "meta": {"founded": "2009", "ipo": "2015"},
    },
    {
        "id": "org:opendoor",
        "kind": "org",
        "name": "Opendoor Technologies Inc.",
        "identifiers": {
            "CIK": "0001801169",
            "ticker": "OPEN",
        },
        "meta": {"founded": "2014", "spac": "2020"},
    },
    {
        "id": "fund:khosla-ventures",
        "kind": "fund",
        "name": "Khosla Ventures",
        "meta": {"founded": "2004"},
    },
    # Lonsdale Companies
    {
        "id": "fund:8vc",
        "kind": "fund",
        "name": "8VC",
        "meta": {"founded": "2015"},
    },
    # McClure
    {
        "id": "fund:500-startups",
        "kind": "fund",
        "name": "500 Startups",
        "aliases": ["500 Global"],
        "meta": {"founded": "2010"},
    },
    # Shah / Kiva
    {
        "id": "org:kiva",
        "kind": "org",
        "name": "Kiva Microfunds",
        "meta": {"founded": "2005", "type": "nonprofit"},
    },
    # Wong / Reddit
    {
        "id": "org:reddit",
        "kind": "org",
        "name": "Reddit, Inc.",
        "identifiers": {
            "ticker": "RDDT",
        },
        "meta": {"founded": "2005", "ipo": "2024"},
    },
]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RELATIONSHIPS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RELATIONSHIPS: List[Dict[str, Any]] = [
    # ── PayPal Founders ─────────────────────────────────────────────────────
    {
        "id": "edge:thiel-paypal-founder",
        "src": "person:peter-thiel",
        "dst": "org:paypal",
        "type": "founder_of",
        "confidence": "CONFIRMED",
        "as_of": "1998-12-01",
        "valid_to": "2002-10-03",
        "evidence": {
            "document_id": "sec-edgar-paypal-s1-2002",
            "source_name": "SEC EDGAR",
            "source_url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001633917",
            "excerpt": "Peter Thiel, Co-founder and Chairman",
        },
    },
    {
        "id": "edge:musk-paypal-founder",
        "src": "person:elon-musk",
        "dst": "org:paypal",
        "type": "founder_of",
        "confidence": "CONFIRMED",
        "as_of": "2000-03-01",
        "valid_to": "2002-10-03",
        "evidence": {
            "document_id": "sec-edgar-paypal-s1-2002",
            "source_name": "SEC EDGAR",
            "excerpt": "X.com merged with Confinity to form PayPal",
        },
    },
    {
        "id": "edge:levchin-paypal-founder",
        "src": "person:max-levchin",
        "dst": "org:paypal",
        "type": "founder_of",
        "confidence": "CONFIRMED",
        "as_of": "1998-12-01",
        "valid_to": "2002-10-03",
        "evidence": {
            "document_id": "sec-edgar-paypal-s1-2002",
            "source_name": "SEC EDGAR",
            "excerpt": "Max Levchin, Co-founder and CTO",
        },
    },
    {
        "id": "edge:nosek-paypal-founder",
        "src": "person:luke-nosek",
        "dst": "org:paypal",
        "type": "founder_of",
        "confidence": "CONFIRMED",
        "as_of": "1998-12-01",
        "evidence": {
            "document_id": "sec-edgar-paypal-s1-2002",
            "source_name": "SEC EDGAR",
        },
    },

    # ── PayPal Employees ────────────────────────────────────────────────────
    {
        "id": "edge:hoffman-paypal",
        "src": "person:reid-hoffman",
        "dst": "org:paypal",
        "type": "employed_at",
        "confidence": "CONFIRMED",
        "as_of": "2000-01-01",
        "valid_to": "2002-10-03",
        "evidence": {
            "document_id": "linkedin-profile-hoffman",
            "source_name": "LinkedIn",
            "excerpt": "COO at PayPal",
        },
    },
    {
        "id": "edge:sacks-paypal",
        "src": "person:david-sacks",
        "dst": "org:paypal",
        "type": "employed_at",
        "confidence": "CONFIRMED",
        "as_of": "1999-01-01",
        "valid_to": "2002-10-03",
        "evidence": {
            "document_id": "sec-edgar-paypal-s1-2002",
            "source_name": "SEC EDGAR",
        },
    },
    {
        "id": "edge:botha-paypal",
        "src": "person:roelof-botha",
        "dst": "org:paypal",
        "type": "employed_at",
        "confidence": "CONFIRMED",
        "as_of": "2000-01-01",
        "valid_to": "2003-01-01",
        "evidence": {
            "document_id": "sec-edgar-paypal-s1-2002",
            "source_name": "SEC EDGAR",
            "excerpt": "CFO",
        },
    },
    {
        "id": "edge:rabois-paypal",
        "src": "person:keith-rabois",
        "dst": "org:paypal",
        "type": "employed_at",
        "confidence": "CONFIRMED",
        "as_of": "2000-01-01",
        "valid_to": "2002-10-03",
        "evidence": {
            "document_id": "sec-edgar-paypal-s1-2002",
            "source_name": "SEC EDGAR",
        },
    },
    {
        "id": "edge:chen-paypal",
        "src": "person:steve-chen",
        "dst": "org:paypal",
        "type": "employed_at",
        "confidence": "CONFIRMED",
        "as_of": "1999-01-01",
        "valid_to": "2005-01-01",
        "evidence": {
            "document_id": "youtube-founders-bio",
            "source_name": "Company records",
        },
    },
    {
        "id": "edge:hurley-paypal",
        "src": "person:chad-hurley",
        "dst": "org:paypal",
        "type": "employed_at",
        "confidence": "CONFIRMED",
        "as_of": "1999-01-01",
        "valid_to": "2005-01-01",
        "evidence": {
            "document_id": "youtube-founders-bio",
            "source_name": "Company records",
        },
    },
    {
        "id": "edge:karim-paypal",
        "src": "person:jawed-karim",
        "dst": "org:paypal",
        "type": "employed_at",
        "confidence": "CONFIRMED",
        "as_of": "2000-01-01",
        "valid_to": "2005-01-01",
        "evidence": {
            "document_id": "youtube-founders-bio",
            "source_name": "Company records",
        },
    },
    {
        "id": "edge:stoppelman-paypal",
        "src": "person:jeremy-stoppelman",
        "dst": "org:paypal",
        "type": "employed_at",
        "confidence": "CONFIRMED",
        "as_of": "2000-01-01",
        "valid_to": "2004-01-01",
        "evidence": {
            "document_id": "yelp-s1",
            "source_name": "SEC EDGAR",
        },
    },
    {
        "id": "edge:simmons-paypal",
        "src": "person:russel-simmons",
        "dst": "org:paypal",
        "type": "employed_at",
        "confidence": "CONFIRMED",
        "as_of": "2000-01-01",
        "valid_to": "2004-01-01",
        "evidence": {
            "document_id": "yelp-s1",
            "source_name": "SEC EDGAR",
        },
    },
    {
        "id": "edge:howery-paypal",
        "src": "person:ken-howery",
        "dst": "org:paypal",
        "type": "employed_at",
        "confidence": "CONFIRMED",
        "as_of": "1999-01-01",
        "valid_to": "2002-10-03",
        "evidence": {
            "document_id": "sec-edgar-paypal-s1-2002",
            "source_name": "SEC EDGAR",
        },
    },
    {
        "id": "edge:lonsdale-paypal",
        "src": "person:joe-lonsdale",
        "dst": "org:paypal",
        "type": "employed_at",
        "confidence": "REPORTED",
        "as_of": "2000-01-01",
        "valid_to": "2002-01-01",
        "evidence": {
            "document_id": "lonsdale-bio",
            "source_name": "Company bio",
            "excerpt": "Intern at PayPal while at Stanford",
        },
    },
    {
        "id": "edge:mcclure-paypal",
        "src": "person:dave-mcclure",
        "dst": "org:paypal",
        "type": "employed_at",
        "confidence": "CONFIRMED",
        "as_of": "2001-01-01",
        "valid_to": "2004-01-01",
        "evidence": {
            "document_id": "mcclure-linkedin",
            "source_name": "LinkedIn",
        },
    },
    {
        "id": "edge:shah-paypal",
        "src": "person:premal-shah",
        "dst": "org:paypal",
        "type": "employed_at",
        "confidence": "CONFIRMED",
        "as_of": "2001-01-01",
        "valid_to": "2004-01-01",
        "evidence": {
            "document_id": "kiva-founder-bio",
            "source_name": "Kiva website",
        },
    },
    {
        "id": "edge:wong-paypal",
        "src": "person:yishan-wong",
        "dst": "org:paypal",
        "type": "employed_at",
        "confidence": "CONFIRMED",
        "as_of": "2001-01-01",
        "valid_to": "2005-01-01",
        "evidence": {
            "document_id": "wong-linkedin",
            "source_name": "LinkedIn",
        },
    },

    # ── Post-PayPal Ventures: Thiel ─────────────────────────────────────────
    {
        "id": "edge:thiel-palantir-founder",
        "src": "person:peter-thiel",
        "dst": "org:palantir",
        "type": "founder_of",
        "confidence": "CONFIRMED",
        "as_of": "2003-05-01",
        "evidence": {
            "document_id": "palantir-s1-2020",
            "source_name": "SEC EDGAR",
            "source_url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001321655",
            "excerpt": "Peter Thiel, Co-Founder and Chairman",
        },
    },
    {
        "id": "edge:thiel-founders-fund",
        "src": "person:peter-thiel",
        "dst": "fund:founders-fund",
        "type": "founder_of",
        "confidence": "CONFIRMED",
        "as_of": "2005-01-01",
        "evidence": {
            "document_id": "founders-fund-about",
            "source_name": "Founders Fund website",
        },
    },
    {
        "id": "edge:howery-founders-fund",
        "src": "person:ken-howery",
        "dst": "fund:founders-fund",
        "type": "founder_of",
        "confidence": "CONFIRMED",
        "as_of": "2005-01-01",
        "evidence": {
            "document_id": "founders-fund-about",
            "source_name": "Founders Fund website",
        },
    },
    {
        "id": "edge:nosek-founders-fund",
        "src": "person:luke-nosek",
        "dst": "fund:founders-fund",
        "type": "founder_of",
        "confidence": "CONFIRMED",
        "as_of": "2005-01-01",
        "evidence": {
            "document_id": "founders-fund-about",
            "source_name": "Founders Fund website",
        },
    },

    # ── Post-PayPal Ventures: Musk ──────────────────────────────────────────
    {
        "id": "edge:musk-spacex-founder",
        "src": "person:elon-musk",
        "dst": "org:spacex",
        "type": "founder_of",
        "confidence": "CONFIRMED",
        "as_of": "2002-05-06",
        "evidence": {
            "document_id": "spacex-company-info",
            "source_name": "SpaceX website",
        },
    },
    {
        "id": "edge:musk-tesla",
        "src": "person:elon-musk",
        "dst": "org:tesla",
        "type": "board_member",
        "confidence": "CONFIRMED",
        "as_of": "2004-02-01",
        "evidence": {
            "document_id": "tesla-s1-2010",
            "source_name": "SEC EDGAR",
            "excerpt": "Elon Musk joined Tesla's board in February 2004",
        },
    },
    {
        "id": "edge:musk-boring",
        "src": "person:elon-musk",
        "dst": "org:boring-company",
        "type": "founder_of",
        "confidence": "CONFIRMED",
        "as_of": "2016-12-01",
        "evidence": {
            "document_id": "boring-company-about",
            "source_name": "The Boring Company website",
        },
    },
    {
        "id": "edge:musk-neuralink",
        "src": "person:elon-musk",
        "dst": "org:neuralink",
        "type": "founder_of",
        "confidence": "CONFIRMED",
        "as_of": "2016-07-01",
        "evidence": {
            "document_id": "neuralink-about",
            "source_name": "Neuralink website",
        },
    },
    {
        "id": "edge:musk-x-corp",
        "src": "person:elon-musk",
        "dst": "org:x-corp",
        "type": "owns",
        "confidence": "CONFIRMED",
        "as_of": "2022-10-27",
        "evidence": {
            "document_id": "sec-13d-twitter-2022",
            "source_name": "SEC EDGAR",
            "excerpt": "Elon Musk completed acquisition of Twitter",
        },
    },

    # ── Post-PayPal Ventures: Hoffman ───────────────────────────────────────
    {
        "id": "edge:hoffman-linkedin-founder",
        "src": "person:reid-hoffman",
        "dst": "org:linkedin",
        "type": "founder_of",
        "confidence": "CONFIRMED",
        "as_of": "2002-12-01",
        "evidence": {
            "document_id": "linkedin-s1-2011",
            "source_name": "SEC EDGAR",
            "source_url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001271024",
        },
    },
    {
        "id": "edge:hoffman-greylock",
        "src": "person:reid-hoffman",
        "dst": "fund:greylock",
        "type": "employed_at",
        "confidence": "CONFIRMED",
        "as_of": "2009-01-01",
        "evidence": {
            "document_id": "greylock-team",
            "source_name": "Greylock website",
        },
    },

    # ── Post-PayPal Ventures: Levchin ───────────────────────────────────────
    {
        "id": "edge:levchin-slide-founder",
        "src": "person:max-levchin",
        "dst": "org:slide",
        "type": "founder_of",
        "confidence": "CONFIRMED",
        "as_of": "2005-01-01",
        "valid_to": "2010-08-01",
        "evidence": {
            "document_id": "slide-acquisition-announcement",
            "source_name": "Google Press Release",
        },
    },
    {
        "id": "edge:levchin-affirm-founder",
        "src": "person:max-levchin",
        "dst": "org:affirm",
        "type": "founder_of",
        "confidence": "CONFIRMED",
        "as_of": "2012-01-01",
        "evidence": {
            "document_id": "affirm-s1-2021",
            "source_name": "SEC EDGAR",
            "source_url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001820953",
        },
    },
    {
        "id": "edge:levchin-yelp-investor",
        "src": "person:max-levchin",
        "dst": "org:yelp",
        "type": "invested_in",
        "confidence": "CONFIRMED",
        "as_of": "2004-01-01",
        "evidence": {
            "document_id": "yelp-s1-2012",
            "source_name": "SEC EDGAR",
            "excerpt": "Angel investment from Max Levchin",
        },
    },

    # ── YouTube Founders ────────────────────────────────────────────────────
    {
        "id": "edge:chen-youtube-founder",
        "src": "person:steve-chen",
        "dst": "org:youtube",
        "type": "founder_of",
        "confidence": "CONFIRMED",
        "as_of": "2005-02-14",
        "evidence": {
            "document_id": "youtube-google-acquisition",
            "source_name": "Google Press Release",
        },
    },
    {
        "id": "edge:hurley-youtube-founder",
        "src": "person:chad-hurley",
        "dst": "org:youtube",
        "type": "founder_of",
        "confidence": "CONFIRMED",
        "as_of": "2005-02-14",
        "evidence": {
            "document_id": "youtube-google-acquisition",
            "source_name": "Google Press Release",
        },
    },
    {
        "id": "edge:karim-youtube-founder",
        "src": "person:jawed-karim",
        "dst": "org:youtube",
        "type": "founder_of",
        "confidence": "CONFIRMED",
        "as_of": "2005-02-14",
        "evidence": {
            "document_id": "youtube-google-acquisition",
            "source_name": "Google Press Release",
        },
    },

    # ── Yelp Founders ───────────────────────────────────────────────────────
    {
        "id": "edge:stoppelman-yelp-founder",
        "src": "person:jeremy-stoppelman",
        "dst": "org:yelp",
        "type": "founder_of",
        "confidence": "CONFIRMED",
        "as_of": "2004-07-01",
        "evidence": {
            "document_id": "yelp-s1-2012",
            "source_name": "SEC EDGAR",
            "source_url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001345016",
        },
    },
    {
        "id": "edge:simmons-yelp-founder",
        "src": "person:russel-simmons",
        "dst": "org:yelp",
        "type": "founder_of",
        "confidence": "CONFIRMED",
        "as_of": "2004-07-01",
        "evidence": {
            "document_id": "yelp-s1-2012",
            "source_name": "SEC EDGAR",
        },
    },

    # ── Sacks Ventures ──────────────────────────────────────────────────────
    {
        "id": "edge:sacks-yammer-founder",
        "src": "person:david-sacks",
        "dst": "org:yammer",
        "type": "founder_of",
        "confidence": "CONFIRMED",
        "as_of": "2008-09-01",
        "valid_to": "2012-07-01",
        "evidence": {
            "document_id": "yammer-microsoft-acquisition",
            "source_name": "Microsoft Press Release",
            "excerpt": "Microsoft acquires Yammer for $1.2B",
        },
    },
    {
        "id": "edge:sacks-craft-founder",
        "src": "person:david-sacks",
        "dst": "fund:craft-ventures",
        "type": "founder_of",
        "confidence": "CONFIRMED",
        "as_of": "2017-01-01",
        "evidence": {
            "document_id": "craft-ventures-about",
            "source_name": "Craft Ventures website",
        },
    },

    # ── Botha / Sequoia ─────────────────────────────────────────────────────
    {
        "id": "edge:botha-sequoia",
        "src": "person:roelof-botha",
        "dst": "fund:sequoia",
        "type": "employed_at",
        "confidence": "CONFIRMED",
        "as_of": "2003-01-01",
        "evidence": {
            "document_id": "sequoia-team",
            "source_name": "Sequoia Capital website",
        },
    },
    {
        "id": "edge:sequoia-youtube",
        "src": "fund:sequoia",
        "dst": "org:youtube",
        "type": "invested_in",
        "confidence": "CONFIRMED",
        "as_of": "2005-11-01",
        "evidence": {
            "document_id": "sequoia-portfolio",
            "source_name": "Sequoia Capital",
            "excerpt": "$11.5M Series A investment",
        },
    },

    # ── Rabois Ventures ─────────────────────────────────────────────────────
    {
        "id": "edge:rabois-square",
        "src": "person:keith-rabois",
        "dst": "org:square",
        "type": "employed_at",
        "confidence": "CONFIRMED",
        "as_of": "2010-01-01",
        "valid_to": "2013-01-01",
        "evidence": {
            "document_id": "square-s1-2015",
            "source_name": "SEC EDGAR",
            "excerpt": "Keith Rabois, COO",
        },
    },
    {
        "id": "edge:rabois-opendoor-founder",
        "src": "person:keith-rabois",
        "dst": "org:opendoor",
        "type": "founder_of",
        "confidence": "CONFIRMED",
        "as_of": "2014-01-01",
        "evidence": {
            "document_id": "opendoor-s1-2020",
            "source_name": "SEC EDGAR",
            "source_url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001801169",
        },
    },
    {
        "id": "edge:rabois-khosla",
        "src": "person:keith-rabois",
        "dst": "fund:khosla-ventures",
        "type": "employed_at",
        "confidence": "CONFIRMED",
        "as_of": "2013-01-01",
        "valid_to": "2019-01-01",
        "evidence": {
            "document_id": "khosla-team-archive",
            "source_name": "Khosla Ventures",
        },
    },

    # ── Lonsdale / Palantir / 8VC ───────────────────────────────────────────
    {
        "id": "edge:lonsdale-palantir-founder",
        "src": "person:joe-lonsdale",
        "dst": "org:palantir",
        "type": "founder_of",
        "confidence": "CONFIRMED",
        "as_of": "2003-05-01",
        "evidence": {
            "document_id": "palantir-s1-2020",
            "source_name": "SEC EDGAR",
            "excerpt": "Joe Lonsdale, Co-Founder",
        },
    },
    {
        "id": "edge:lonsdale-8vc-founder",
        "src": "person:joe-lonsdale",
        "dst": "fund:8vc",
        "type": "founder_of",
        "confidence": "CONFIRMED",
        "as_of": "2015-01-01",
        "evidence": {
            "document_id": "8vc-about",
            "source_name": "8VC website",
        },
    },

    # ── McClure / 500 Startups ──────────────────────────────────────────────
    {
        "id": "edge:mcclure-500-founder",
        "src": "person:dave-mcclure",
        "dst": "fund:500-startups",
        "type": "founder_of",
        "confidence": "CONFIRMED",
        "as_of": "2010-01-01",
        "evidence": {
            "document_id": "500-startups-about",
            "source_name": "500 Startups website",
        },
    },

    # ── Shah / Kiva ─────────────────────────────────────────────────────────
    {
        "id": "edge:shah-kiva-founder",
        "src": "person:premal-shah",
        "dst": "org:kiva",
        "type": "founder_of",
        "confidence": "CONFIRMED",
        "as_of": "2005-10-01",
        "evidence": {
            "document_id": "kiva-about",
            "source_name": "Kiva website",
        },
    },

    # ── Wong / Reddit ───────────────────────────────────────────────────────
    {
        "id": "edge:wong-reddit-ceo",
        "src": "person:yishan-wong",
        "dst": "org:reddit",
        "type": "employed_at",
        "confidence": "CONFIRMED",
        "as_of": "2012-03-01",
        "valid_to": "2014-11-01",
        "evidence": {
            "document_id": "reddit-blog-ceo",
            "source_name": "Reddit Blog",
            "excerpt": "Yishan Wong appointed as CEO",
        },
    },

    # ── Cross-Investment / Co-Investment ────────────────────────────────────
    {
        "id": "edge:founders-fund-spacex",
        "src": "fund:founders-fund",
        "dst": "org:spacex",
        "type": "invested_in",
        "confidence": "CONFIRMED",
        "as_of": "2008-01-01",
        "evidence": {
            "document_id": "founders-fund-portfolio",
            "source_name": "Founders Fund",
            "excerpt": "Early investor in SpaceX",
        },
    },
    {
        "id": "edge:founders-fund-affirm",
        "src": "fund:founders-fund",
        "dst": "org:affirm",
        "type": "invested_in",
        "confidence": "CONFIRMED",
        "as_of": "2012-01-01",
        "evidence": {
            "document_id": "affirm-s1-2021",
            "source_name": "SEC EDGAR",
        },
    },
    {
        "id": "edge:founders-fund-palantir",
        "src": "fund:founders-fund",
        "dst": "org:palantir",
        "type": "invested_in",
        "confidence": "CONFIRMED",
        "as_of": "2005-01-01",
        "evidence": {
            "document_id": "palantir-s1-2020",
            "source_name": "SEC EDGAR",
        },
    },
    {
        "id": "edge:sequoia-affirm",
        "src": "fund:sequoia",
        "dst": "org:affirm",
        "type": "invested_in",
        "confidence": "CONFIRMED",
        "as_of": "2012-01-01",
        "evidence": {
            "document_id": "affirm-s1-2021",
            "source_name": "SEC EDGAR",
        },
    },
    {
        "id": "edge:greylock-linkedin",
        "src": "fund:greylock",
        "dst": "org:linkedin",
        "type": "invested_in",
        "confidence": "CONFIRMED",
        "as_of": "2004-01-01",
        "evidence": {
            "document_id": "linkedin-s1-2011",
            "source_name": "SEC EDGAR",
        },
    },
    {
        "id": "edge:khosla-square",
        "src": "fund:khosla-ventures",
        "dst": "org:square",
        "type": "invested_in",
        "confidence": "CONFIRMED",
        "as_of": "2009-01-01",
        "evidence": {
            "document_id": "square-s1-2015",
            "source_name": "SEC EDGAR",
        },
    },

    # ── Board Relationships ─────────────────────────────────────────────────
    {
        "id": "edge:thiel-facebook-board",
        "src": "person:peter-thiel",
        "dst": "org:facebook",
        "type": "board_member",
        "confidence": "CONFIRMED",
        "as_of": "2005-04-01",
        "valid_to": "2022-02-01",
        "evidence": {
            "document_id": "meta-proxy-2022",
            "source_name": "SEC EDGAR",
        },
    },
    {
        "id": "edge:hoffman-airbnb-board",
        "src": "person:reid-hoffman",
        "dst": "org:airbnb",
        "type": "board_member",
        "confidence": "CONFIRMED",
        "as_of": "2015-01-01",
        "evidence": {
            "document_id": "airbnb-s1-2020",
            "source_name": "SEC EDGAR",
        },
    },
]


# Additional company needed for board relationships
ADDITIONAL_COMPANIES: List[Dict[str, Any]] = [
    {
        "id": "org:facebook",
        "kind": "org",
        "name": "Meta Platforms, Inc.",
        "identifiers": {
            "CIK": "0001326801",
            "ticker": "META",
        },
        "aliases": ["Facebook"],
        "meta": {"founded": "2004", "ipo": "2012"},
    },
    {
        "id": "org:airbnb",
        "kind": "org",
        "name": "Airbnb, Inc.",
        "identifiers": {
            "CIK": "0001559720",
            "ticker": "ABNB",
        },
        "meta": {"founded": "2008", "ipo": "2020"},
    },
]

# Merge additional companies
COMPANIES.extend(ADDITIONAL_COMPANIES)


def get_all_entities() -> List[Dict[str, Any]]:
    """Get all entities (people + companies + funds)."""
    return PAYPAL_MAFIA_MEMBERS + COMPANIES


def get_all_relationships() -> List[Dict[str, Any]]:
    """Get all relationships."""
    return RELATIONSHIPS


def get_seed_stats() -> Dict[str, Any]:
    """Get statistics about the seed data."""
    return {
        "paypal_mafia_members": len(PAYPAL_MAFIA_MEMBERS),
        "companies_and_funds": len(COMPANIES),
        "total_entities": len(get_all_entities()),
        "relationships": len(RELATIONSHIPS),
        "relationship_types": list(set(r["type"] for r in RELATIONSHIPS)),
    }
