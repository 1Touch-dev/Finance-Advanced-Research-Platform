"""
PayPal Mafia Expanded Report v2 - 50-80 pages
Generates deep per-person profiles with full company financials, lobbying, contracts.
"""
import sys, os, json, time, logging, base64, io
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("expand_v2")

# ============ CONFIGURATION ============

PEOPLE = [
    {"name": "Peter Thiel", "role": "Co-founder, Chairman", "companies": ["PLTR", "META"], "funds": ["Founders Fund", "Mithril Capital", "Valar Ventures"], "known_for": "First outside investor in Facebook, co-founded Palantir"},
    {"name": "Elon Musk", "role": "Co-founder, CEO X.com", "companies": ["TSLA", "XPEV"], "funds": [], "known_for": "CEO Tesla, SpaceX, X (Twitter), Neuralink, The Boring Company"},
    {"name": "Reid Hoffman", "role": "COO, Board Member", "companies": ["MSFT"], "funds": ["Greylock Partners"], "known_for": "Co-founded LinkedIn, Board of Microsoft"},
    {"name": "Max Levchin", "role": "Co-founder, CTO", "companies": ["AFRM", "YELP"], "funds": [], "known_for": "Founded Affirm, early investor in Yelp"},
    {"name": "David Sacks", "role": "COO", "companies": ["PLTR"], "funds": ["Craft Ventures"], "known_for": "Founded Yammer (sold to MSFT $1.2B), Craft Ventures"},
    {"name": "Keith Rabois", "role": "Executive VP", "companies": ["SQ", "YELP", "HOOD"], "funds": ["Khosla Ventures", "Founders Fund"], "known_for": "COO Square, Board Yelp/DoorDash/Robinhood"},
    {"name": "Jeremy Stoppelman", "role": "VP Engineering", "companies": ["YELP"], "funds": [], "known_for": "Co-founded and CEO of Yelp"},
    {"name": "Chad Hurley", "role": "Designer", "companies": ["GOOG"], "funds": [], "known_for": "Co-founded YouTube (sold to Google $1.65B)"},
    {"name": "Steve Chen", "role": "Engineer", "companies": ["GOOG"], "funds": [], "known_for": "Co-founded YouTube"},
    {"name": "Jawed Karim", "role": "Engineer", "companies": ["GOOG"], "funds": ["Youniversity Ventures"], "known_for": "Co-founded YouTube, early Airbnb investor"},
    {"name": "Joe Lonsdale", "role": "Intern/Early Employee", "companies": ["PLTR"], "funds": ["8VC", "Formation 8"], "known_for": "Co-founded Palantir, 8VC, Addepar"},
    {"name": "Roelof Botha", "role": "CFO", "companies": ["SQ"], "funds": ["Sequoia Capital"], "known_for": "Managing Partner Sequoia Capital"},
    {"name": "Ken Howery", "role": "Co-founder", "companies": [], "funds": ["Founders Fund"], "known_for": "Co-founded Founders Fund, US Ambassador to Sweden"},
    {"name": "Luke Nosek", "role": "Co-founder", "companies": [], "funds": ["Founders Fund", "Gigafund"], "known_for": "Co-founded Founders Fund, Gigafund (SpaceX focused)"},
    {"name": "Premal Shah", "role": "Product Manager", "companies": [], "funds": [], "known_for": "President of Kiva.org (microfinance)"},
    {"name": "Russel Simmons", "role": "Engineer", "companies": ["YELP"], "funds": [], "known_for": "Co-founded Yelp"},
]

COMPANIES_FULL = {
    "PLTR": {"name": "Palantir Technologies", "sector": "Enterprise Software / Defense", "founded": 2003, "ipo": 2020},
    "TSLA": {"name": "Tesla Inc", "sector": "Electric Vehicles / Energy", "founded": 2003, "ipo": 2010},
    "AFRM": {"name": "Affirm Holdings", "sector": "Fintech / BNPL", "founded": 2012, "ipo": 2021},
    "YELP": {"name": "Yelp Inc", "sector": "Local Search / Reviews", "founded": 2004, "ipo": 2012},
    "SQ": {"name": "Block Inc (Square)", "sector": "Fintech / Payments", "founded": 2009, "ipo": 2015},
    "META": {"name": "Meta Platforms", "sector": "Social Media / VR", "founded": 2004, "ipo": 2012},
    "MSFT": {"name": "Microsoft Corp", "sector": "Enterprise Software / Cloud", "founded": 1975, "ipo": 1986},
    "GOOG": {"name": "Alphabet (Google)", "sector": "Search / Advertising / Cloud", "founded": 1998, "ipo": 2004},
    "HOOD": {"name": "Robinhood Markets", "sector": "Fintech / Brokerage", "founded": 2013, "ipo": 2021},
    "DASH": {"name": "DoorDash", "sector": "Food Delivery / Logistics", "founded": 2013, "ipo": 2020},
    "ABNB": {"name": "Airbnb", "sector": "Travel / Marketplace", "founded": 2008, "ipo": 2020},
    "SPOT": {"name": "Spotify", "sector": "Music Streaming", "founded": 2006, "ipo": 2018},
}


def get_company_financials(ticker: str) -> Dict:
    try:
        from app.connectors.market_data_connector import get_market_snapshot
        return get_market_snapshot(ticker)
    except Exception as e:
        logger.warning(f"Market data failed for {ticker}: {e}")
        return {}


def get_insider_data(ticker: str) -> Dict:
    try:
        from app.connectors.sec_edgar_connector import get_insider_transactions, get_cik_from_ticker
        cik = get_cik_from_ticker(ticker)
        if cik:
            return get_insider_transactions(cik, start_date="2023-01-01")
        return {}
    except Exception as e:
        logger.warning(f"Insider data failed for {ticker}: {e}")
        return {}


def get_lobbying(company_name: str) -> Dict:
    try:
        from app.connectors.opensecrets_connector import get_lobbying
        return get_lobbying(company_name)
    except Exception as e:
        logger.warning(f"Lobbying failed for {company_name}: {e}")
        return {}


def get_contracts(company_name: str) -> Dict:
    try:
        from app.connectors.fpds_connector import get_full_contract_portfolio
        return get_full_contract_portfolio(company_name)
    except Exception as e:
        logger.warning(f"Contracts failed for {company_name}: {e}")
        return {}


def get_institutional(ticker: str) -> Dict:
    try:
        from app.connectors.sec_edgar_connector import get_institutional_holders, get_cik_from_ticker
        cik = get_cik_from_ticker(ticker)
        if cik:
            return get_institutional_holders(cik)
        return {}
    except Exception as e:
        logger.warning(f"Institutional failed for {ticker}: {e}")
        return {}


def fmt_money(val):
    if not val:
        return "N/A"
    val = float(val)
    if val >= 1e12:
        return f"${val/1e12:.2f}T"
    if val >= 1e9:
        return f"${val/1e9:.1f}B"
    if val >= 1e6:
        return f"${val/1e6:.1f}M"
    if val >= 1e3:
        return f"${val/1e3:.0f}K"
    return f"${val:,.0f}"
