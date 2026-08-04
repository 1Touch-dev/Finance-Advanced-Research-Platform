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


# ============ EXTENDED PERSON NARRATIVES ============

EXTENDED_NARRATIVES = {
    "Peter Thiel": """
Peter Andreas Thiel represents one of the most consequential figures in Silicon Valley's transformation from a technology hub into a center of ideological and political power. Born in Frankfurt, Germany in 1967, Thiel immigrated to the United States as a child and was raised in Foster City, California. His academic journey through Stanford University—both undergraduate (philosophy) and law school—established the intellectual foundations that would later inform his contrarian investment philosophy.

**Early Career and PayPal Foundation**

Thiel's pre-PayPal career included a stint at Sullivan & Cromwell practicing securities law, followed by derivatives trading at Credit Suisse. These experiences in traditional finance would prove invaluable when he co-founded Confinity with Max Levchin in December 1998. The company's initial focus on cryptographic security for handheld devices pivoted to digital payments, eventually becoming PayPal after merging with Elon Musk's X.com in 2000.

As PayPal's CEO through the turbulent dot-com bust, Thiel demonstrated the crisis management skills that would become his hallmark. The company went public in February 2002—one of the first successful tech IPOs after the crash—and was acquired by eBay for $1.5 billion just months later. Thiel's stake yielded approximately $55 million, providing the capital for his next ventures.

**The Facebook Investment and Contrarian Philosophy**

In August 2004, Thiel made what would become the defining investment of his career: a $500,000 angel investment in a college social network called TheFacebook, founded by Harvard dropout Mark Zuckerberg. This investment, made when Facebook had fewer than 1 million users, would eventually be worth over $1 billion—a 2,000x return that established Thiel's reputation as one of the most successful angel investors in history.

The Facebook investment exemplified Thiel's contrarian approach: while most investors were fleeing consumer internet after the dot-com bust, Thiel recognized that network effects could create winner-take-all dynamics in social platforms. This philosophy—investing in monopolies, not competition—would become the central thesis of his 2014 book "Zero to One."

**Palantir and the Government-Technology Nexus**

In 2003, Thiel co-founded Palantir Technologies with Joe Lonsdale, Stephen Cohen, and Nathan Gettings. Initially funded by the CIA's venture arm In-Q-Tel, Palantir developed data integration and analytics software for intelligence agencies. The company's name, drawn from Tolkien's seeing-stones, reflected its mission of providing visibility into complex data landscapes.

Palantir's journey from a $32 million In-Q-Tel investment to its 2020 direct listing at a $21 billion valuation represents the most successful government-technology company of the 21st century. As of 2026, the company's market capitalization exceeds $300 billion, driven by its Gotham (government) and Foundry (commercial) platforms.

**Founders Fund and Venture Philosophy**

Launched in 2005 with Ken Howery and Luke Nosek, Founders Fund embodies Thiel's belief that technology has stagnated relative to mid-20th century expectations. The firm's provocative motto—"We wanted flying cars, instead we got 140 characters"—captures Thiel's frustration with incremental innovation.

Founders Fund's portfolio includes transformative companies across multiple sectors: SpaceX (aerospace), Stripe (payments), Airbnb (hospitality), Palantir (enterprise software), and Anduril (defense). The fund's AUM has grown to approximately $12 billion, making it one of the most influential venture capital firms in Silicon Valley.

**Political Influence and Controversies**

Thiel's political involvement has been extensive and often controversial. His 2016 endorsement and financial support of Donald Trump made him an outlier in Democratic-leaning Silicon Valley. His funding of the Hulk Hogan lawsuit that bankrupted Gawker Media raised questions about the intersection of wealth and press freedom.

More recently, Thiel has supported political candidates aligned with his worldview, including J.D. Vance and Blake Masters. His 2022 resignation from Meta's board was widely interpreted as reflecting his growing distance from mainstream tech culture.

**Investment Style and Key Positions**

| Company | Investment Type | Approximate Value | Strategic Rationale |
|---------|----------------|-------------------|---------------------|
| Palantir | Co-founder | ~$8-10B | Government-tech infrastructure |
| SpaceX | Founders Fund | ~$15B+ | Space access monopoly |
| Stripe | Founders Fund | ~$5B+ | Global payments infrastructure |
| Anduril | Founders Fund | ~$2B+ | Defense technology |
| Facebook/Meta | Angel | Exited | Network effects platform |

Thiel's current net worth is estimated at $10-12 billion, making him one of the wealthiest individuals to emerge from the PayPal generation. His influence extends far beyond his financial holdings, however—his network of proteges, investment partners, and political allies has reshaped multiple industries.
""",

    "Elon Musk": """
Elon Reeve Musk has become the most valuable entrepreneur in human history, with a personal net worth exceeding $300 billion at various points—a figure unprecedented in the annals of capitalism. Born in Pretoria, South Africa in 1971, Musk's path to PayPal began with his first company, Zip2, a city guide software company sold to Compaq for $307 million in 1999.

**X.com and the PayPal Merger**

With proceeds from Zip2, Musk founded X.com in 1999 as an online financial services company. X.com's merger with Confinity in 2000 created PayPal, though Musk's tenure as CEO was brief—he was replaced by Peter Thiel in September 2000 after disagreements over technical architecture. Despite the leadership change, Musk emerged from PayPal's eBay sale with approximately $180 million, which he immediately deployed into his next ventures.

**Tesla: The Electric Vehicle Revolution**

Musk's $6.5 million Series A investment in Tesla Motors in 2004 made him chairman of a company that would eventually transform the global automotive industry. Taking over as CEO in 2008 during the financial crisis, Musk navigated Tesla through near-bankruptcy multiple times, including a 2008 episode where the company had fewer than 24 hours of cash remaining.

Tesla's trajectory from niche electric sports car maker to the world's most valuable automotive company represents one of the most successful corporate turnarounds in history. Key milestones include:

- 2012: Model S launch establishes Tesla as a luxury EV manufacturer
- 2017: Model 3 begins mass-market production
- 2020: Tesla joins the S&P 500 with $600B+ market cap
- 2024: Global vehicle deliveries exceed 2 million annually

As of 2026, Tesla's market capitalization exceeds $800 billion, with Musk holding approximately 13% of shares outstanding. The company has expanded beyond vehicles into energy storage (Powerwall, Megapack), solar (Solar Roof), and AI (Dojo, Optimus robot).

**SpaceX: Making Life Multiplanetary**

Founded in 2002 with $100 million of Musk's PayPal proceeds, SpaceX has revolutionized the space industry through its reusable rocket technology. After three failed launches of the Falcon 1 nearly bankrupted the company, SpaceX achieved orbit in September 2008—and has since dominated the commercial launch market.

Critical achievements include:
- First private company to dock with the International Space Station (2012)
- First orbital-class rocket landing (2015)
- Starlink satellite constellation (6,000+ satellites as of 2026)
- Starship development for Mars colonization

SpaceX's private market valuation has reached approximately $350 billion, making it the most valuable private company in history. Musk's ~42% equity stake represents approximately $147 billion in value—more than his Tesla holdings.

**The Twitter/X Acquisition**

Musk's $44 billion acquisition of Twitter in October 2022 represented the largest leveraged buyout of a technology company. Rebranding the platform as X, Musk has pursued aggressive cost-cutting (reducing headcount by 80%) while attempting to transform the service into an "everything app" modeled on China's WeChat.

The acquisition has proven controversial, with advertisers initially fleeing the platform over content moderation concerns. However, Musk's vision for X includes payments, banking, and AI integration—potentially recreating the original X.com vision abandoned during the PayPal merger.

**xAI and the Artificial Intelligence Race**

Launched in 2023, xAI represents Musk's entry into the artificial intelligence race. The company's Grok chatbot, integrated into X, competes directly with OpenAI (which Musk co-founded and later departed) and Google's AI offerings. xAI has raised billions in funding at a valuation exceeding $20 billion.

**Wealth Analysis and Holdings**

| Asset | Ownership | Est. Value | Notes |
|-------|-----------|------------|-------|
| Tesla (TSLA) | ~13% | $100B+ | Declined from 20%+ due to Twitter financing |
| SpaceX | ~42% | $147B | Includes Starlink stake |
| X Corp | ~78% | $15-20B | Acquired 2022, valuation contested |
| xAI | Majority | $20B+ | Growing rapidly |
| The Boring Company | 90% | $5B+ | Tunnel infrastructure |
| Neuralink | Majority | $2B+ | Brain-computer interface |

Musk's management style—characterized by aggressive timelines, public feuds, and unconventional communication via social media—has made him a polarizing figure. However, his track record of executing on seemingly impossible goals (reusable rockets, mass-market EVs, global satellite internet) has earned him credibility that few other entrepreneurs possess.
""",

    "Reid Hoffman": """
Reid Garrett Hoffman represents the PayPal Mafia's most successful pivot into venture capital and corporate board influence. Born in Palo Alto in 1967, Hoffman's career spans the earliest days of the commercial internet through the current AI revolution.

**Academic Foundation and Early Career**

Hoffman's intellectual foundation includes a B.S. in Symbolic Systems from Stanford (1990) and a master's degree from Oxford as a Marshall Scholar. His early career at Apple and Fujitsu provided exposure to both consumer technology and enterprise software—a dual perspective that would inform his later investments.

**PayPal and the Social Networking Vision**

At PayPal, Hoffman served as Executive Vice President and was responsible for external relations—a role that positioned him to observe the emerging power of networked platforms. Even while at PayPal, Hoffman was formulating his vision for a professional social network.

**LinkedIn: The Professional Graph**

Founded in December 2002, just months after PayPal's sale, LinkedIn represented Hoffman's thesis that professional relationships—not just social connections—could benefit from digital networking. The company's growth was deliberately slower than Facebook's, prioritizing "professional" over "viral."

Key LinkedIn milestones:
- 2003: Launch with Hoffman's personal network as seed users
- 2011: IPO at $45/share, valuing company at $9 billion
- 2016: Sale to Microsoft for $26.2 billion (largest acquisition in MSFT history)

Hoffman served as CEO through 2009, then chairman through the Microsoft acquisition. The deal made him a billionaire several times over and established his reputation as someone who could both found and scale a major platform company.

**Greylock and the VC Evolution**

Since 2009, Hoffman has been a partner at Greylock Partners, one of Silicon Valley's oldest venture capital firms. His investments reflect his network-focused thesis:

| Investment | Status | Notes |
|------------|--------|-------|
| Airbnb | IPO 2020 | Board member |
| Convoy | Shut down 2023 | Trucking marketplace |
| Aurora | SPAC 2021 | Autonomous vehicles |
| Coda | Private | Collaborative docs |
| Inflection AI | Acquired 2024 | AI assistant |

**Microsoft Board and Big Tech Influence**

Hoffman's Microsoft board seat (2017-present) gives him influence over a $3 trillion company. His role includes advising on AI strategy, particularly given Microsoft's massive investment in OpenAI. This positioning makes Hoffman a bridge between venture capital and the largest technology incumbents.

**Media and Thought Leadership**

Unlike some PayPal colleagues who maintain lower profiles, Hoffman has cultivated a substantial media presence:
- "Masters of Scale" podcast: Interviews with top founders
- Books: "The Alliance," "Blitzscaling"
- Regular appearances on CNBC, Bloomberg
- Active LinkedIn publishing (fitting, given his platform)

This visibility has made Hoffman a sought-after advisor and board member, multiplying his influence beyond his direct investments.

**Political Activity**

Hoffman has been one of the most politically active PayPal Mafia members, primarily supporting Democratic candidates and causes. His donations and political organizing reflect views often at odds with Thiel's conservative activism—illustrating that PayPal's legacy extends across the political spectrum.

**Current Portfolio and Net Worth**

Hoffman's net worth is estimated at $2.5-3 billion, derived primarily from:
- Microsoft stock (from LinkedIn acquisition)
- Greylock carried interest
- Personal angel investments (Airbnb, others)
- Ongoing advisory and board compensation

His influence, however, extends far beyond his financial holdings—Hoffman's network includes founders, executives, and policymakers across the technology ecosystem.
""",

    "Max Levchin": """
Max Rafael Levchin is the technical architect of PayPal and the embodiment of the immigrant founder success story. Born in Kyiv, Ukraine (then Soviet Union) in 1975, Levchin's family emigrated to the United States in 1991, settling in Chicago. His journey from refugee to billionaire entrepreneur illustrates both the opportunities of the American technology industry and the distinctive culture of Silicon Valley.

**Technical Foundations**

Levchin studied computer science at the University of Illinois at Urbana-Champaign, where he developed expertise in cryptography and security—skills that would prove essential for PayPal's success. While still a student, he founded or co-founded four companies, displaying the serial entrepreneurship that would characterize his career.

**PayPal: The Technical Vision**

As PayPal's CTO and co-founder, Levchin built the security infrastructure that made online payments viable. His innovations included the CAPTCHA system to prevent fraud (later spun off as reCAPTCHA and acquired by Google) and the risk assessment algorithms that reduced PayPal's fraud rate below credit card industry standards.

The technical culture Levchin established at PayPal—a blend of mathematical rigor and pragmatic engineering—became a template for subsequent Silicon Valley companies. Many PayPal engineers went on to senior technical roles at Google, Facebook, and other major platforms.

**Post-PayPal Ventures**

After PayPal's sale, Levchin pursued multiple ventures:

| Venture | Period | Outcome | Notes |
|---------|--------|---------|-------|
| Slide | 2004-2010 | Sold to Google ~$228M | Social gaming widgets |
| Yelp | 2004 | IPO 2012, ~$2.5B | Co-founder/investor |
| Glow | 2013 | Private | Fertility tracking app |
| Affirm | 2012-present | IPO 2021, ~$15B | BNPL leader |

**Affirm: Rebuilding Consumer Credit**

Affirm represents Levchin's most ambitious post-PayPal venture—an attempt to rebuild consumer credit from first principles. The company's thesis: traditional credit products (credit cards, layaway) hide true costs through complex fee structures, creating financial traps for consumers.

Affirm's model:
- Point-of-sale lending with transparent, fixed payments
- No hidden fees, late fees, or deferred interest
- Integration with major retailers (Amazon, Walmart, Target)
- Simple monthly payments displayed at checkout

Since its January 2021 IPO, Affirm has become the leading "buy now, pay later" (BNPL) provider in North America. Key partnerships include Amazon (2021), Shopify, and Apple Pay Later (integration).

**Technical Philosophy**

Levchin's approach combines mathematical rigor with practical application. His investments and advisory roles reflect this focus on technically defensible businesses:

- Hard science: He's invested in companies applying machine learning to healthcare, fertility, and finance
- Infrastructure: Preference for platform plays over applications
- Security: Ongoing advisory role at Affirm focuses on fraud prevention

**Current Holdings and Net Worth**

| Asset | Est. Value | Notes |
|-------|------------|-------|
| Affirm (AFRM) | ~$2B+ | Founder stake |
| Yelp (YELP) | ~$200M+ | Early equity |
| Personal investments | ~$500M | Angel portfolio |

Levchin's net worth is estimated at $2.5-3 billion, primarily derived from Affirm and Yelp. He remains actively involved in both companies and continues to make angel investments in early-stage startups.

**Philanthropy and Causes**

As an immigrant founder, Levchin has been particularly supportive of organizations helping immigrants and refugees in technology. He's donated to STEM education initiatives and has spoken publicly about the importance of immigration to American innovation.
""",

    "David Sacks": """
David Oliver Sacks represents the PayPal Mafia's most visible evolution into media influence and political commentary. Born in Cape Town, South Africa in 1972, Sacks immigrated to the United States as a child, attending Stanford for both undergraduate and law degrees.

**PayPal: The Operational Foundation**

As PayPal's COO, Sacks was responsible for the company's core operations during its most critical growth phase. His role included:
- Scaling customer service from startup to millions of users
- Managing the fraud prevention organization
- Overseeing business development partnerships
- Corporate development (acquisitions and strategic initiatives)

The operational experience at PayPal—scaling a company from chaos to IPO in 3.5 years—became the template for Sacks's subsequent ventures.

**Yammer: Enterprise Social**

Founded in 2008, Yammer applied social networking patterns to enterprise communication. The company pioneered the "freemium" model for enterprise software, allowing individuals to sign up with their corporate email and invite colleagues.

Key milestones:
- 2010: $25M Series B led by Emergence Capital
- 2011: 100,000 companies using the platform
- 2012: Acquired by Microsoft for $1.2 billion

The Yammer exit demonstrated that PayPal veterans could succeed outside consumer payments—in enterprise software, a space requiring different skills than consumer internet.

**Craft Ventures: The VC Evolution**

Since 2017, Sacks has led Craft Ventures, a venture capital fund focused on early-stage technology companies. The fund's portfolio reflects Sacks's operational background—a preference for companies with clear paths to revenue and defensible market positions.

Selected Craft portfolio companies:

| Company | Sector | Stage | Status |
|---------|--------|-------|--------|
| SpaceX | Aerospace | Growth | Private $350B |
| Bird | Mobility | Series C | Public (delisted) |
| ClickUp | Productivity | Series C | Private |
| Sourcegraph | Dev Tools | Series D | Private |
| Relativity Space | Aerospace | Series E | Private |
| Hopin | Events | Series C | Acquired |

Craft's AUM has grown to approximately $3 billion across multiple funds.

**All-In Podcast: Media Influence**

Since 2020, Sacks has co-hosted the "All-In" podcast with fellow PayPal Mafia member Chamath Palihapitiya and investors Jason Calacanis and David Friedberg. The podcast has become one of the most influential voices in technology and politics, with episodes regularly reaching #1 on Apple Podcasts.

The podcast's influence extends beyond technology:
- Political commentary on fiscal policy, foreign policy, elections
- Real-time reactions to market events
- Investments discussed on the show often see price movements

**Political Evolution**

Sacks has become increasingly involved in politics, supporting candidates across the political spectrum but trending conservative/libertarian in recent years. His commentary on:
- Immigration: Support for skilled immigration, criticism of border policy
- Technology regulation: Opposition to antitrust enforcement against Big Tech
- Foreign policy: Skepticism of interventionism
- Economic policy: Criticism of Federal Reserve, inflation concerns

This political engagement has made Sacks a polarizing figure in Silicon Valley, where many peers hold different views.

**Net Worth and Holdings**

| Asset | Est. Value | Notes |
|-------|------------|-------|
| Craft Ventures | ~$500M | GP stake and carry |
| SpaceX (via Craft) | ~$500M | Fund holdings |
| Personal investments | ~$200M | Direct positions |
| Yammer proceeds | N/A | Deployed into ventures |

Sacks's net worth is estimated at $1.5-2 billion, though precise figures are difficult given the private nature of venture capital returns.
""",

    "Keith Rabois": """
Keith Rabois stands as the PayPal Mafia's most prolific board member, having served on the boards of more successful technology companies than perhaps any other individual in Silicon Valley. Born in 1969, Rabois attended Stanford for both undergraduate and law degrees, where he was a contemporary of Peter Thiel.

**Early Career and PayPal**

Before PayPal, Rabois worked at several law firms and as an executive at various startups. At PayPal, he served as Executive Vice President of Business Development, responsible for merchant partnerships and strategic relationships.

**Post-PayPal Operating Roles**

Unlike many PayPal colleagues who moved directly into venture capital, Rabois spent years in operational roles:

| Company | Role | Period | Outcome |
|---------|------|--------|---------|
| LinkedIn | VP Business Development | 2002-2004 | IPO 2011, sold to MSFT |
| Square | COO | 2010-2013 | IPO 2015, $50B+ market cap |
| Opendoor | CEO (interim) | 2015-2017 | SPAC 2020, ~$4B |

These operating experiences—especially the Square COO role—provided Rabois with direct experience scaling companies from early stage to IPO.

**Venture Capital Career**

Rabois has held partner roles at three major venture firms:

| Firm | Period | Notable Investments |
|------|--------|---------------------|
| Khosla Ventures | 2013-2019 | DoorDash, Stripe, Affirm |
| Founders Fund | 2019-2023 | Various |
| Khosla Ventures | 2023-present | Return |

**Board Positions: An Unprecedented Record**

Rabois's board portfolio spans multiple successful companies:

| Company | Role | IPO/Exit |
|---------|------|----------|
| Yelp | Board Director | IPO 2012 |
| Square/Block | Board Director | IPO 2015 |
| DoorDash | Board Director | IPO 2020 |
| Robinhood | Board Director | IPO 2021 |
| Opendoor | Board Director | SPAC 2020 |

This concentration of board seats across major platform companies is unusual even by Silicon Valley standards.

**Investment Philosophy**

Rabois's investment approach emphasizes:
- Operational efficiency: Companies should be "default alive" quickly
- Market timing: Investing in categories at inflection points
- Founder caliber: Strong preference for repeat founders
- Capital efficiency: Skepticism of excessive fundraising

His investments in DoorDash, Stripe, and Affirm have generated some of the best returns of the past decade.

**Miami Advocacy**

Since 2020, Rabois has been a prominent advocate for Miami as a technology hub, relocating there and investing in local companies. His move represented one of the highest-profile defections from San Francisco during the COVID-era technology migration.

**Current Holdings**

| Asset | Est. Value | Notes |
|-------|------------|-------|
| DoorDash | ~$500M+ | Board seat |
| Square/Block | ~$300M+ | Board seat |
| Stripe | ~$200M+ | Via Khosla |
| Other positions | ~$200M+ | Portfolio |

Rabois's net worth is estimated at $1.5-2 billion, primarily derived from board positions and VC carry.
""",

    "Chad Hurley": """
Chad Meredith Hurley co-founded YouTube, which became the most successful media platform acquisition in history. His journey from PayPal designer to billionaire illustrates the accidental nature of many Silicon Valley success stories.

**Background and PayPal**

Born in 1977 in Reading, Pennsylvania, Hurley studied fine arts at Indiana University of Pennsylvania—an unusual background for a technology entrepreneur. At PayPal, he worked as a designer, creating the company's original logo and interface designs.

**YouTube: The Accidental Billion-Dollar Company**

In early 2005, Hurley, along with PayPal colleagues Steve Chen and Jawed Karim, began working on a video-sharing concept. The original idea reportedly involved a video dating service before pivoting to general video sharing.

Key YouTube milestones:
- February 2005: Domain registered
- April 2005: First video uploaded ("Me at the zoo" by Karim)
- December 2005: Official launch
- October 2006: Acquired by Google for $1.65 billion

The speed of YouTube's success—from founding to billion-dollar exit in 21 months—remains one of the fastest unicorn trajectories in Silicon Valley history.

**The Google Acquisition**

At the time of acquisition, YouTube was:
- Serving 100 million video views per day
- Operating at a significant loss due to bandwidth costs
- Facing potential copyright litigation from media companies

Google's $1.65 billion purchase (in stock) provided:
- Hurley: Estimated ~$345 million
- Chen: Estimated ~$326 million
- Karim: Estimated ~$65 million (smaller stake due to earlier departure)

**Post-YouTube Ventures**

After serving as YouTube CEO until 2010, Hurley pursued several ventures:

| Venture | Period | Status | Notes |
|---------|--------|--------|-------|
| AVOS Systems | 2011-2016 | Shut down | Acquired Delicious, Zeen |
| MixBit | 2013 | Shut down | Video editing app |
| GreenPark Sports | 2018-present | Active | Metaverse sports |

None of these ventures achieved YouTube's success, illustrating the difficulty of replicating lightning-strike outcomes.

**Investment Activity**

Hurley has made numerous angel investments, including:
- Virgin Hyperloop (transportation)
- Formlabs (3D printing)
- Various cryptocurrency projects

**Current Status**

Hurley maintains a lower profile than some PayPal colleagues, focusing on private investments and lifestyle pursuits (he's an avid race car driver). His net worth is estimated at $400-500 million, primarily from the YouTube exit proceeds and subsequent investments.

The YouTube story—three PayPal designers creating a billion-dollar platform in under two years—remains one of the most compelling illustrations of the PayPal Mafia's impact on the technology industry.
""",
}

# Add shorter narratives for other members (will generate dynamically)
def get_extended_narrative(name: str) -> str:
    """Get extended narrative for a person, or generate a shorter version."""
    if name in EXTENDED_NARRATIVES:
        return EXTENDED_NARRATIVES[name]

    # Default shorter narrative template for members without full profiles
    return f"""
{name}'s journey from PayPal to their current ventures exemplifies the network effects that have made the PayPal Mafia so influential. Their role in PayPal's early days provided both capital and connections that would prove essential for subsequent ventures.

The PayPal experience instilled a particular approach to company-building: move fast, embrace risk, and maintain strong relationships with co-investors and fellow founders. This approach has been evident throughout their career trajectory.

Their investment and operational activities continue to influence the broader technology ecosystem, with connections spanning venture capital, operating companies, and board positions across multiple sectors.
"""


# ============ CHART GENERATION ============

def generate_charts(company_data: Dict, people: List) -> Dict[str, str]:
    """Generate matplotlib charts as base64 PNGs."""
    charts = {}
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        logger.warning("matplotlib not available")
        return charts

    # Chart 1: Market Cap comparison
    fig, ax = plt.subplots(figsize=(10, 5))
    tickers = []
    caps = []
    for t, d in company_data.items():
        mc = d.get("financials", {}).get("market_cap", 0)
        if mc:
            tickers.append(t)
            caps.append(mc / 1e9)
    if tickers:
        bars = ax.bar(tickers, caps, color=["#1e40af", "#2563eb", "#3b82f6", "#60a5fa", "#93c5fd", "#bfdbfe", "#dbeafe", "#eff6ff"][:len(tickers)])
        ax.set_ylabel("Market Cap ($B)")
        ax.set_title("PayPal Mafia Portfolio — Market Capitalization")
        ax.bar_label(bars, fmt="$%.0fB", fontsize=8)
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=150)
        charts["market_cap"] = base64.b64encode(buf.getvalue()).decode()
        plt.close()

    # Chart 2: P/E Ratios
    fig, ax = plt.subplots(figsize=(9, 4))
    pe_tickers = []
    pe_vals = []
    for t, d in company_data.items():
        pe = d.get("financials", {}).get("pe_ttm")
        if pe and isinstance(pe, (int, float)) and pe > 0:
            pe_tickers.append(t)
            pe_vals.append(pe)
    if pe_tickers:
        colors = ["#dc2626" if p > 50 else "#f59e0b" if p > 25 else "#16a34a" for p in pe_vals]
        ax.barh(pe_tickers, pe_vals, color=colors)
        ax.set_xlabel("P/E Ratio (TTM)")
        ax.set_title("Valuation Comparison — P/E Ratios")
        ax.axvline(x=25, color="gray", linestyle="--", alpha=0.5)
        ax.text(25.5, -0.5, "S&P 500 avg", fontsize=7, color="gray")
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=150)
        charts["pe_ratio"] = base64.b64encode(buf.getvalue()).decode()
        plt.close()

    # Chart 3: Government contracts comparison
    fig, ax = plt.subplots(figsize=(9, 4))
    contract_tickers = []
    contract_vals = []
    for t, d in company_data.items():
        c = d.get("contracts", {})
        total = c.get("total_obligations") or c.get("total_value", 0)
        if total and float(total) > 0:
            contract_tickers.append(t)
            contract_vals.append(float(total) / 1e6)
    if contract_tickers:
        ax.bar(contract_tickers, contract_vals, color="#059669")
        ax.set_ylabel("Total Obligations ($M)")
        ax.set_title("Government Contract Awards — PayPal Mafia Companies")
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=150)
        charts["contracts"] = base64.b64encode(buf.getvalue()).decode()
        plt.close()

    # Chart 4: Network connections per person
    fig, ax = plt.subplots(figsize=(10, 5))
    names = [p["name"].split()[-1] for p in people]
    connections = [len(p.get("companies", [])) + len(p.get("funds", [])) for p in people]
    ax.barh(names, connections, color="#7c3aed")
    ax.set_xlabel("Number of Companies/Funds")
    ax.set_title("Network Density — Connections Per Person")
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150)
    charts["network_density"] = base64.b64encode(buf.getvalue()).decode()
    plt.close()

    # Chart 5: Sector distribution pie
    fig, ax = plt.subplots(figsize=(7, 7))
    sectors = defaultdict(int)
    for t, info in COMPANIES_FULL.items():
        if t in company_data:
            mc = company_data[t].get("financials", {}).get("market_cap", 0)
            if mc:
                sector = info.get("sector", "Other").split("/")[0].strip()
                sectors[sector] += mc
    if sectors:
        labels = list(sectors.keys())
        sizes = [v/1e9 for v in sectors.values()]
        colors_pie = plt.cm.Set3(range(len(labels)))
        ax.pie(sizes, labels=labels, autopct="%1.1f%%", colors=colors_pie, startangle=90)
        ax.set_title("Portfolio Sector Distribution (by Market Cap)")
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=150)
        charts["sector_pie"] = base64.b64encode(buf.getvalue()).decode()
        plt.close()

    # Chart 6: Beta risk profile
    fig, ax = plt.subplots(figsize=(8, 4))
    beta_tickers = []
    beta_vals = []
    for t, d in company_data.items():
        b = d.get("financials", {}).get("beta")
        if b and isinstance(b, (int, float)):
            beta_tickers.append(t)
            beta_vals.append(b)
    if beta_tickers:
        colors = ["#dc2626" if b > 1.5 else "#f59e0b" if b > 1 else "#16a34a" for b in beta_vals]
        ax.bar(beta_tickers, beta_vals, color=colors)
        ax.axhline(y=1.0, color="gray", linestyle="--", alpha=0.7)
        ax.set_ylabel("Beta")
        ax.set_title("Risk Profile — Portfolio Beta Values")
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=150)
        charts["beta"] = base64.b64encode(buf.getvalue()).decode()
        plt.close()

    logger.info(f"Generated {len(charts)} charts")
    return charts

# ============ REPORT GENERATION ============

def generate_full_report(company_data: Dict, people: List, charts: Dict) -> str:
    """Generate 50-80 page markdown report."""
    md = []

    # TITLE PAGE
    md.append("# PayPal Mafia — Deep Intelligence Network Report")
    md.append("")
    md.append(f"**Generated:** {datetime.now().strftime('%B %d, %Y')}")
    md.append("")
    md.append("**Classification:** CONFIDENTIAL — For Internal Research Only")
    md.append("")
    md.append("---")
    md.append("")

    # TABLE OF CONTENTS
    md.append("## Table of Contents")
    md.append("")
    md.append("1. Executive Summary")
    md.append("2. Network Overview & Key Findings")
    md.append("3. Individual Deep Profiles")
    md.append("4. Company Intelligence Dossiers")
    md.append("5. Cross-Portfolio Analysis")
    md.append("6. Government & Political Intelligence")
    md.append("7. Investment Network & Fund Analysis")
    md.append("8. Risk Assessment & Correlations")
    md.append("9. Network Visualizations")
    md.append("10. Methodology & Data Sources")
    md.append("")
    md.append("---")
    md.append("")

    # EXECUTIVE SUMMARY
    md.append("## 1. Executive Summary")
    md.append("")
    total_mc = sum(d.get("financials", {}).get("market_cap", 0) for d in company_data.values())
    md.append(f"The PayPal Mafia represents one of the most consequential networks in modern capitalism. ")
    md.append(f"This report traces **{len(people)} core members** across **{len(company_data)} public companies** ")
    md.append(f"with a combined market capitalization of **{fmt_money(total_mc)}**.")
    md.append("")
    md.append("### Key Network Statistics")
    md.append("")
    md.append("| Metric | Value |")
    md.append("|--------|-------|")
    md.append(f"| Core Members Analyzed | {len(people)} |")
    md.append(f"| Public Companies Tracked | {len(company_data)} |")
    md.append(f"| Combined Public Market Cap | {fmt_money(total_mc)} |")
    md.append(f"| Est. Private Portfolio Value | $500B+ (SpaceX, Stripe, etc.) |")
    md.append(f"| Venture Funds Operated | {sum(len(p.get('funds', [])) for p in people)} |")
    md.append(f"| Sectors Dominated | Technology, Fintech, Defense, Social, Energy |")
    md.append(f"| Government Contract Value | ${sum(float(d.get('contracts', {}).get('total_obligations', 0) or 0) for d in company_data.values())/1e9:.1f}B+ |")
    md.append("")
    md.append("### Critical Findings")
    md.append("")
    md.append("1. **Concentration of Power**: A single PayPal cohort of ~16 people controls or influences companies worth >$5 trillion")
    md.append("2. **Defense-Tech Nexus**: Palantir (Thiel/Lonsdale) has become a primary intelligence platform for US/Allied governments")
    md.append("3. **Financial Infrastructure**: Block, Affirm, Robinhood — mafia members rebuilt payments from scratch post-PayPal")
    md.append("4. **Political Influence**: Through lobbying ($100M+), donations, ambassadorships, and advisory roles")
    md.append("5. **Venture Multiplication**: Founders Fund, Sequoia, 8VC, Craft Ventures fund the next generation of mafia-adjacent companies")
    md.append("")
    md.append("---")
    md.append("")

    # NETWORK OVERVIEW
    md.append("## 2. Network Overview & Key Findings")
    md.append("")
    md.append("### The PayPal Origin (1998-2002)")
    md.append("")
    md.append("PayPal was founded in December 1998 as Confinity by Peter Thiel, Max Levchin, and Luke Nosek. ")
    md.append("It merged with Elon Musk's X.com in 2000. The company went public in February 2002 and was ")
    md.append("acquired by eBay for $1.5 billion in October 2002. This relatively brief period created a ")
    md.append("network of entrepreneurs who would go on to found, fund, or lead companies worth trillions.")
    md.append("")
    md.append("### Network Formation Patterns")
    md.append("")
    md.append("The PayPal Mafia exhibits three distinct patterns of network propagation:")
    md.append("")
    md.append("**Pattern 1: Serial Founding**")
    md.append("Members who left PayPal to found entirely new companies:")
    md.append("- Elon Musk → Tesla, SpaceX, Neuralink, The Boring Company, xAI")
    md.append("- Max Levchin → Slide (sold to Google), Affirm")
    md.append("- Jeremy Stoppelman + Russel Simmons → Yelp")
    md.append("- Chad Hurley + Steve Chen + Jawed Karim → YouTube")
    md.append("- David Sacks → Yammer (sold to Microsoft), Craft Ventures")
    md.append("- Joe Lonsdale → Palantir, Addepar, 8VC")
    md.append("")
    md.append("**Pattern 2: Venture Capital Multiplication**")
    md.append("Members who became VCs, funding hundreds of subsequent companies:")
    md.append("- Peter Thiel → Founders Fund (AUM ~$12B), Mithril Capital, Valar Ventures")
    md.append("- Roelof Botha → Sequoia Capital (AUM ~$85B)")
    md.append("- Keith Rabois → Khosla Ventures → Founders Fund")
    md.append("- Luke Nosek + Ken Howery → Founders Fund, Gigafund")
    md.append("- David Sacks → Craft Ventures (AUM ~$3B)")
    md.append("- Joe Lonsdale → 8VC (AUM ~$5B)")
    md.append("")
    md.append("**Pattern 3: Board Interlocking**")
    md.append("Members serving on each other's boards and co-investing:")
    md.append("- Peter Thiel: Board of Facebook/Meta, Palantir, Founders Fund portfolio companies")
    md.append("- Keith Rabois: Board of Square, Yelp, DoorDash, Robinhood")
    md.append("- Reid Hoffman: Board of Microsoft, Airbnb, Aurora")
    md.append("")
    md.append("### Educational Background Correlation")
    md.append("")
    md.append("| University | Members | Post-PayPal Impact |")
    md.append("|-----------|---------|-------------------|")
    md.append("| Stanford University | Thiel, Sacks, Rabois, Lonsdale, Stoppelman | Dominant in VC formation |")
    md.append("| University of Illinois | Levchin, Chen | Technical founders |")
    md.append("| Indiana University (Penn) | Hurley | Creative/design leadership |")
    md.append("| Stanford Law | Thiel, Howery | Legal/strategic focus |")
    md.append("")
    md.append("---")
    md.append("")

    # INDIVIDUAL DEEP PROFILES
    md.append("## 3. Individual Deep Profiles")
    md.append("")
    md.append("Comprehensive intelligence on each PayPal Mafia member: their ventures, investments, ")
    md.append("board positions, political activities, and financial footprint.")
    md.append("")

    for person in people:
        md.extend(generate_person_profile(person, company_data))

    md.append("---")
    md.append("")

    # COMPANY INTELLIGENCE DOSSIERS
    md.append("## 4. Company Intelligence Dossiers")
    md.append("")
    md.append("Full financial, lobbying, government contract, and institutional ownership analysis ")
    md.append("for each major public company in the PayPal Mafia portfolio.")
    md.append("")

    for ticker, data in company_data.items():
        md.extend(generate_company_dossier(ticker, data))

    md.append("---")
    md.append("")

    # CROSS-PORTFOLIO ANALYSIS
    md.append("## 5. Cross-Portfolio Analysis")
    md.append("")
    md.extend(generate_cross_analysis(company_data, people))
    md.append("")
    md.append("---")
    md.append("")

    # GOVERNMENT & POLITICAL
    md.append("## 6. Government & Political Intelligence")
    md.append("")
    md.extend(generate_political_section(company_data, people))
    md.append("")
    md.append("---")
    md.append("")

    # INVESTMENT NETWORK
    md.append("## 7. Investment Network & Fund Analysis")
    md.append("")
    md.extend(generate_fund_analysis(people))
    md.append("")
    md.append("---")
    md.append("")

    # RISK ASSESSMENT
    md.append("## 8. Risk Assessment & Correlations")
    md.append("")
    md.extend(generate_risk_section(company_data, people))
    md.append("")
    md.append("---")
    md.append("")

    # CHARTS
    md.append("## 9. Network Visualizations")
    md.append("")
    for chart_name, chart_b64 in charts.items():
        title = chart_name.replace("_", " ").title()
        md.append(f"### {title}")
        md.append("")
        md.append(f"![{title}](data:image/png;base64,{chart_b64})")
        md.append("")

    md.append("---")
    md.append("")

    # METHODOLOGY
    md.append("## 10. Methodology & Data Sources")
    md.append("")
    md.append("| Source | Data Type | Coverage |")
    md.append("|--------|-----------|----------|")
    md.append("| SEC EDGAR | Insider transactions, 13F filings, Form D | All public companies |")
    md.append("| SEC EFTS | Full-text search for person CIKs, filings | Historical |")
    md.append("| Finnhub | Real-time market data, analyst ratings | Live |")
    md.append("| Financial Modeling Prep | Financials, targets, quotes | Current + historical |")
    md.append("| USASpending.gov | Federal contract awards | FY2008-present |")
    md.append("| OpenSecrets/FEC | Lobbying spend, PAC contributions | 2010-present |")
    md.append("| Senate LDA | Lobbying disclosure registrations | Current |")
    md.append("| NewsAPI | Recent news coverage | 30 days |")
    md.append("")
    md.append("**Limitations:**")
    md.append("- Private company valuations (SpaceX, Stripe) are estimates from secondary markets")
    md.append("- Venture fund returns are not publicly disclosed")
    md.append("- Some international lobbying may not be captured by US-focused sources")
    md.append("- LinkedIn data not included due to ToS restrictions")
    md.append("")

    return "\n".join(md)

# ============ PERSON PROFILE GENERATOR ============

def generate_person_profile(person: Dict, company_data: Dict) -> List[str]:
    """Generate 4-6 page profile for each person with extended narrative."""
    md = []
    name = person["name"]
    md.append(f"### {name}")
    md.append("")
    md.append(f"**PayPal Role:** {person['role']}")
    md.append("")
    md.append(f"**Known For:** {person['known_for']}")
    md.append("")

    # Extended narrative biography (if available)
    extended = get_extended_narrative(name)
    if extended.strip():
        md.append("#### Profile Overview")
        md.append("")
        md.append(extended.strip())
        md.append("")

    # Career trajectory
    md.append("#### Career Trajectory")
    md.append("")
    if name == "Peter Thiel":
        md.append("| Period | Role | Organization | Outcome |")
        md.append("|--------|------|--------------|---------|")
        md.append("| 1998-2002 | Co-founder, CEO | PayPal | Sold to eBay $1.5B |")
        md.append("| 2003-present | Co-founder, Chairman | Palantir Technologies | Market cap $300B+ |")
        md.append("| 2004 | First outside investor | Facebook/Meta | $500K → $1B+ return |")
        md.append("| 2005-present | Managing Partner | Founders Fund | AUM ~$12B |")
        md.append("| 2005-present | Managing Partner | Mithril Capital | Growth-stage fund |")
        md.append("| 2014-present | Managing Partner | Valar Ventures | International fintech |")
        md.append("| 2016-2022 | Board Member | Meta Platforms | Resigned 2022 |")
        md.append("")
        md.append("#### Investment Philosophy")
        md.append("")
        md.append("Thiel's investment thesis centers on 'definite optimism' — backing founders with specific, ")
        md.append("contrarian visions of the future. Key principles:")
        md.append("- Monopoly over competition (prefer market-defining companies)")
        md.append("- 'Zero to One' thinking — creating genuinely new things")
        md.append("- Long time horizons with concentrated bets")
        md.append("- Defense/intelligence as inevitable tech frontier")
        md.append("")
        md.append("#### Notable Investments & Returns")
        md.append("")
        md.append("| Investment | Entry | Outcome | Est. Return |")
        md.append("|-----------|-------|---------|-------------|")
        md.append("| Facebook | 2004 ($500K) | IPO 2012 | ~2000x |")
        md.append("| Palantir | 2003 (co-founder) | IPO 2020 | ~1000x+ |")
        md.append("| SpaceX | Early investor | Private ($350B) | ~100x+ |")
        md.append("| Stripe | Founders Fund | Private ($50B+) | ~50x |")
        md.append("| Airbnb | Founders Fund | IPO 2020 | ~100x |")
        md.append("| LinkedIn | Angel | Sold to MSFT $26.2B | ~500x |")
        md.append("")
    elif name == "Elon Musk":
        md.append("| Period | Role | Organization | Outcome |")
        md.append("|--------|------|--------------|---------|")
        md.append("| 1999-2002 | Founder, CEO | X.com/PayPal | Merged, sold to eBay $1.5B |")
        md.append("| 2002-present | CEO, Chief Engineer | SpaceX | Private, ~$350B valuation |")
        md.append("| 2004-present | CEO, Product Architect | Tesla | Market cap ~$800B |")
        md.append("| 2016-present | Co-founder | Neuralink | Brain-computer interface |")
        md.append("| 2016-present | Founder | The Boring Company | Tunneling infrastructure |")
        md.append("| 2022-present | Owner, CTO | X (Twitter) | Acquired $44B |")
        md.append("| 2023-present | Founder | xAI | AI research company |")
        md.append("")
        md.append("#### Wealth & Holdings")
        md.append("")
        md.append("| Asset | Est. Value | % of Net Worth |")
        md.append("|-------|-----------|----------------|")
        md.append("| Tesla equity (~13%) | ~$100B | 35% |")
        md.append("| SpaceX equity (~42%) | ~$147B | 50% |")
        md.append("| X (Twitter) | ~$15B | 5% |")
        md.append("| xAI | ~$20B | 7% |")
        md.append("| Other (Neuralink, Boring Co) | ~$10B | 3% |")
        md.append("")
    elif name == "Reid Hoffman":
        md.append("| Period | Role | Organization | Outcome |")
        md.append("|--------|------|--------------|---------|")
        md.append("| 2000-2002 | COO | PayPal | Sold to eBay |")
        md.append("| 2002-2009 | Co-founder, CEO | LinkedIn | Sold to MSFT $26.2B |")
        md.append("| 2009-present | Partner | Greylock Partners | VC fund |")
        md.append("| 2017-present | Board Member | Microsoft | After LinkedIn acquisition |")
        md.append("| 2023-present | Co-founder | Inflection AI | AI safety company |")
        md.append("")
        md.append("#### Board Positions & Influence")
        md.append("")
        md.append("| Company | Role | Period | Market Cap |")
        md.append("|---------|------|--------|-----------|")
        md.append("| Microsoft | Board Director | 2017-present | ~$3.0T |")
        md.append("| Airbnb | Board Director | 2011-2020 | ~$80B |")
        md.append("| Aurora Innovation | Board Director | 2021-present | ~$5B |")
        md.append("| Blockstream | Investor | 2014-present | Private |")
        md.append("")
    elif name == "Max Levchin":
        md.append("| Period | Role | Organization | Outcome |")
        md.append("|--------|------|--------------|---------|")
        md.append("| 1998-2002 | Co-founder, CTO | PayPal | $1.5B exit |")
        md.append("| 2004 | Co-founder, investor | Yelp | IPO 2012, ~$2.5B |")
        md.append("| 2005-2010 | Founder, CEO | Slide | Sold to Google ~$228M |")
        md.append("| 2012-present | Founder, CEO | Affirm | IPO 2021, ~$15B |")
        md.append("| 2016 | Co-founder | Glow (fertility) | Health tech |")
        md.append("")
        md.append("#### Affirm Business Intelligence")
        md.append("")
        md.append("Affirm (AFRM) represents Levchin's thesis that consumer credit should be transparent. ")
        md.append("The company provides point-of-sale lending with no hidden fees.")
        md.append("")
    elif name == "David Sacks":
        md.append("| Period | Role | Organization | Outcome |")
        md.append("|--------|------|--------------|---------|")
        md.append("| 1999-2002 | COO | PayPal | $1.5B exit |")
        md.append("| 2008-2012 | Founder, CEO | Yammer | Sold to Microsoft $1.2B |")
        md.append("| 2017-present | GP | Craft Ventures | AUM ~$3B |")
        md.append("| 2022-present | Host | All-In Podcast | Political influence |")
        md.append("")
        md.append("#### Craft Ventures Portfolio (Selected)")
        md.append("")
        md.append("| Company | Sector | Stage | Status |")
        md.append("|---------|--------|-------|--------|")
        md.append("| SpaceX | Aerospace | Growth | Private $350B |")
        md.append("| Bird | Mobility | Series C | Public (delisted) |")
        md.append("| ClickUp | Productivity | Series C | Private |")
        md.append("| Sourcegraph | Dev Tools | Series D | Private |")
        md.append("| Relativity Space | Aerospace | Series E | Private |")
        md.append("")
    elif name == "Keith Rabois":
        md.append("| Period | Role | Organization | Outcome |")
        md.append("|--------|------|--------------|---------|")
        md.append("| 2000-2002 | EVP | PayPal | $1.5B exit |")
        md.append("| 2010-2013 | COO | Square (Block) | IPO 2015 |")
        md.append("| 2013-2019 | Partner | Khosla Ventures | VC |")
        md.append("| 2019-present | Managing Director | Founders Fund | VC |")
        md.append("")
        md.append("#### Board Seats (Active & Former)")
        md.append("")
        md.append("| Company | Ticker | Role | Period |")
        md.append("|---------|--------|------|--------|")
        md.append("| Yelp | YELP | Board Director | 2004-present |")
        md.append("| DoorDash | DASH | Board Director | 2016-present |")
        md.append("| Robinhood | HOOD | Board Director | 2020-present |")
        md.append("| Affirm | AFRM | Investor/Advisor | 2012-2018 |")
        md.append("")
    elif name == "Joe Lonsdale":
        md.append("| Period | Role | Organization | Outcome |")
        md.append("|--------|------|--------------|---------|")
        md.append("| 2002-2003 | Intern | PayPal (via Clarium) | Thiel mentee |")
        md.append("| 2003-present | Co-founder | Palantir Technologies | IPO 2020, $300B+ |")
        md.append("| 2009-present | Founder, GP | 8VC (Formation 8) | AUM ~$5B |")
        md.append("| 2009-present | Founder | Addepar | Wealth management platform |")
        md.append("| 2021-present | Founder | Epirus | Directed energy defense |")
        md.append("")
        md.append("#### 8VC Portfolio Focus")
        md.append("")
        md.append("8VC focuses on 'industries of the future': defense tech, biotech, real estate tech, logistics.")
        md.append("")
        md.append("| Company | Sector | Notable |")
        md.append("|---------|--------|---------|")
        md.append("| Anduril | Defense | Autonomous defense systems |")
        md.append("| Epirus | Defense | Directed energy weapons |")
        md.append("| Joby Aviation | Air mobility | eVTOL aircraft |")
        md.append("| Oscar Health | Healthcare | Health insurance tech |")
        md.append("| Opendoor | Real estate | iBuying platform |")
        md.append("")
    elif name == "Roelof Botha":
        md.append("| Period | Role | Organization | Outcome |")
        md.append("|--------|------|--------------|---------|")
        md.append("| 2000-2003 | CFO | PayPal | $1.5B exit |")
        md.append("| 2003-present | Partner → Managing Partner | Sequoia Capital | AUM ~$85B |")
        md.append("")
        md.append("#### Sequoia Investments (Botha-led)")
        md.append("")
        md.append("| Company | Entry Stage | Outcome | Sector |")
        md.append("|---------|-----------|---------|--------|")
        md.append("| YouTube | Series A | Sold to Google $1.65B | Video |")
        md.append("| Square/Block | Series A | IPO, ~$40B | Fintech |")
        md.append("| MongoDB | Series B | IPO, ~$25B | Database |")
        md.append("| Unity | Growth | IPO, ~$15B | Gaming |")
        md.append("| Instagram | Early | Sold to Meta $1B | Social |")
        md.append("| Eventbrite | Series A | IPO | Events |")
        md.append("")
    else:
        md.append(f"*Career details being researched for {name}.*")
        md.append("")

    # Show their companies' current data
    person_tickers = person.get("companies", [])
    if person_tickers:
        md.append(f"#### Portfolio Companies — Live Financial Data")
        md.append("")
        for ticker in person_tickers:
            if ticker in company_data:
                fin = company_data[ticker].get("financials", {})
                price = fin.get("price")
                if price:
                    mc = fin.get("market_cap", 0)
                    info = COMPANIES_FULL.get(ticker, {})
                    md.append(f"**{info.get('name', ticker)} ({ticker})**")
                    md.append("")
                    md.append(f"- Price: ${price:.2f} | Market Cap: {fmt_money(mc)}")
                    md.append(f"- P/E: {fin.get('pe_ttm', 'N/A')} | P/S: {fin.get('ps_ttm', 'N/A')} | Beta: {fin.get('beta', 'N/A')}")
                    consensus = fin.get("consensus", {})
                    if consensus.get("target_consensus"):
                        md.append(f"- Analyst Target: ${consensus['target_consensus']:.2f} | Bullish: {consensus.get('bullish_pct', 'N/A')}%")
                    md.append("")

    # Funds
    if person.get("funds"):
        md.append("#### Fund Operations")
        md.append("")
        for fund in person["funds"]:
            md.append(f"- **{fund}**")
        md.append("")

    md.append("")
    return md

# ============ COMPANY DOSSIER GENERATOR ============

def generate_company_dossier(ticker: str, data: Dict) -> List[str]:
    """Generate full company intelligence dossier."""
    md = []
    info = COMPANIES_FULL.get(ticker, data.get("info", {}))
    name = info.get("name", ticker)
    financials = data.get("financials", {})
    insiders = data.get("insiders", {})
    lobbying_data = data.get("lobbying", {})
    contracts = data.get("contracts", {})
    institutional = data.get("institutional", {})
    mafia = data.get("info", {}).get("mafia", [])

    md.append(f"### {name} ({ticker})")
    md.append("")
    md.append(f"**Sector:** {info.get('sector', 'N/A')} | **Founded:** {info.get('founded', 'N/A')} | **IPO:** {info.get('ipo', 'N/A')}")
    md.append("")
    if mafia:
        md.append(f"**PayPal Mafia Members:** {', '.join(mafia)}")
        md.append("")

    # Market Data
    price = financials.get("price")
    if price:
        md.append("#### Financial Profile")
        md.append("")
        md.append("| Metric | Value |")
        md.append("|--------|-------|")
        md.append(f"| Share Price | ${price:.2f} |")
        mc = financials.get("market_cap", 0)
        md.append(f"| Market Capitalization | {fmt_money(mc)} |")
        md.append(f"| P/E Ratio (TTM) | {financials.get('pe_ttm', 'N/A')} |")
        md.append(f"| P/S Ratio (TTM) | {financials.get('ps_ttm', 'N/A')} |")
        md.append(f"| Beta (Volatility) | {financials.get('beta', 'N/A')} |")
        md.append(f"| 52-Week High | ${financials.get('week_52_high', 0):.2f} |")
        md.append(f"| 52-Week Low | ${financials.get('week_52_low', 0):.2f} |")
        md.append(f"| 50-Day Moving Avg | ${financials.get('price_avg_50', 0):.2f} |")
        md.append(f"| 200-Day Moving Avg | ${financials.get('price_avg_200', 0):.2f} |")
        pct = financials.get("pct_below_52w_high")
        if pct:
            md.append(f"| Distance from 52W High | {pct:.1f}% |")
        md.append("")

        # Analyst consensus
        consensus = financials.get("consensus", {})
        if consensus.get("target_consensus"):
            md.append("#### Analyst Consensus")
            md.append("")
            md.append("| Metric | Value |")
            md.append("|--------|-------|")
            md.append(f"| Target Price (Mean) | ${consensus['target_consensus']:.2f} |")
            md.append(f"| Target Price (Median) | ${consensus.get('target_median', 0):.2f} |")
            md.append(f"| Target High | ${consensus.get('target_high', 0):.2f} |")
            md.append(f"| Target Low | ${consensus.get('target_low', 0):.2f} |")
            ratings = consensus.get("ratings", {})
            md.append(f"| Strong Buy | {ratings.get('strongBuy', 0)} |")
            md.append(f"| Buy | {ratings.get('buy', 0)} |")
            md.append(f"| Hold | {ratings.get('hold', 0)} |")
            md.append(f"| Sell | {ratings.get('sell', 0)} |")
            md.append(f"| Strong Sell | {ratings.get('strongSell', 0)} |")
            bp = consensus.get("bullish_pct")
            if bp:
                md.append(f"| Bullish Consensus | {bp:.1f}% |")
            upside = ((consensus["target_consensus"] - price) / price) * 100
            md.append(f"| Implied Upside/Downside | {upside:+.1f}% |")
            md.append("")

    # Insider Transactions
    if insiders and isinstance(insiders, dict):
        txns = insiders.get("transactions", [])
        if txns:
            md.append(f"#### Insider Trading Activity ({len(txns)} transactions)")
            md.append("")
            md.append("| Date | Insider | Transaction | Shares | Value |")
            md.append("|------|---------|-------------|--------|-------|")
            for t in txns[:20]:
                val = fmt_money(t.get("value")) if t.get("value") else ""
                shares = t.get("shares", 0)
                sh_str = f"{int(shares):,}" if shares else ""
                md.append(f"| {t.get('date', '')} | {t.get('name', '')} | {t.get('type', '')} | {sh_str} | {val} |")
            md.append("")

    # Lobbying
    if lobbying_data and isinstance(lobbying_data, dict):
        spend = lobbying_data.get("spend_by_year") or lobbying_data.get("total_spend")
        if spend:
            md.append("#### Lobbying & Political Activity")
            md.append("")
            if isinstance(spend, dict) and spend:
                md.append("| Year | Lobbying Expenditure |")
                md.append("|------|---------------------|")
                for year, amount in sorted(spend.items(), reverse=True)[:8]:
                    md.append(f"| {year} | {fmt_money(amount)} |")
                total_lobby = sum(float(v) for v in spend.values())
                md.append(f"| **Total** | **{fmt_money(total_lobby)}** |")
                md.append("")
            issues = lobbying_data.get("issues") or lobbying_data.get("issues_lobbied", [])
            if issues:
                md.append(f"**Key Issues Lobbied:** {', '.join(str(i) for i in issues[:10])}")
                md.append("")

    # Government Contracts
    if contracts and isinstance(contracts, dict):
        total = contracts.get("total_obligations") or contracts.get("total_value", 0)
        awards = contracts.get("awards") or contracts.get("results", [])
        if total or awards:
            md.append("#### Government Contracts & Federal Awards")
            md.append("")
            if total:
                md.append(f"**Total Federal Obligations:** {fmt_money(total)}")
                md.append("")
            uei = contracts.get("recipient_uei") or contracts.get("uei")
            if uei:
                md.append(f"**UEI:** {uei}")
                md.append("")
            if isinstance(awards, list) and awards:
                md.append("| Agency | Description | Obligation | Period |")
                md.append("|--------|-------------|-----------|--------|")
                for a in awards[:15]:
                    agency = str(a.get("agency") or a.get("awarding_agency_name", ""))[:30]
                    desc = str(a.get("description") or a.get("award_description", ""))[:50]
                    val = a.get("value") or a.get("total_obligation", 0)
                    period = str(a.get("period_of_performance_start_date", ""))[:10]
                    md.append(f"| {agency} | {desc} | {fmt_money(val)} | {period} |")
                md.append("")

    # Institutional Holders
    if institutional and isinstance(institutional, dict):
        holders = institutional.get("holders") or institutional.get("top_holders", [])
        if isinstance(holders, list) and holders:
            md.append("#### Institutional Ownership")
            md.append("")
            md.append("| Institution | Shares Held | Value | % Outstanding |")
            md.append("|-------------|-------------|-------|--------------|")
            for h in holders[:12]:
                nm = h.get("name") or h.get("holder", "")
                sh = h.get("shares", 0)
                val = h.get("value", 0)
                pct = h.get("pct_outstanding", "")
                pct_str = f"{pct:.2f}%" if isinstance(pct, (int, float)) else ""
                md.append(f"| {nm} | {int(sh):,} | {fmt_money(val)} | {pct_str} |")
            md.append("")

    md.append("")
    return md

# ============ ANALYSIS SECTIONS ============

def generate_cross_analysis(company_data: Dict, people: List) -> List[str]:
    """Cross-portfolio analysis."""
    md = []
    md.append("### Portfolio Valuation Comparison")
    md.append("")
    md.append("| Company | Ticker | Market Cap | P/E | P/S | Beta | Mafia Connection |")
    md.append("|---------|--------|-----------|-----|-----|------|-----------------|")
    for ticker, data in company_data.items():
        fin = data.get("financials", {})
        mc = fin.get("market_cap", 0)
        info = data.get("info", {})
        name = info.get("name", COMPANIES_FULL.get(ticker, {}).get("name", ticker))
        mafia = ", ".join(info.get("mafia", [])[:2])
        md.append(f"| {name} | {ticker} | {fmt_money(mc)} | {fin.get('pe_ttm', 'N/A')} | {fin.get('ps_ttm', 'N/A')} | {fin.get('beta', 'N/A')} | {mafia} |")
    md.append("")

    total_mc = sum(d.get("financials", {}).get("market_cap", 0) for d in company_data.values())
    md.append(f"**Combined Public Market Capitalization: {fmt_money(total_mc)}**")
    md.append("")

    md.append("### Sector Allocation")
    md.append("")
    md.append("| Sector | Companies | Combined Market Cap | % of Portfolio |")
    md.append("|--------|-----------|--------------------|--------------:|")
    sectors = defaultdict(lambda: {"companies": [], "mc": 0})
    for ticker, data in company_data.items():
        info = COMPANIES_FULL.get(ticker, {})
        sector = info.get("sector", "Other").split("/")[0].strip()
        mc = data.get("financials", {}).get("market_cap", 0)
        sectors[sector]["companies"].append(ticker)
        sectors[sector]["mc"] += mc
    for sector, sdata in sorted(sectors.items(), key=lambda x: -x[1]["mc"]):
        pct = (sdata["mc"] / total_mc * 100) if total_mc else 0
        md.append(f"| {sector} | {', '.join(sdata['companies'])} | {fmt_money(sdata['mc'])} | {pct:.1f}% |")
    md.append("")

    md.append("### Performance Metrics Summary")
    md.append("")
    md.append("**Risk-Return Profile:**")
    md.append("")
    betas = [d.get("financials", {}).get("beta", 0) for d in company_data.values() if d.get("financials", {}).get("beta")]
    if betas:
        avg_beta = sum(betas) / len(betas)
        md.append(f"- Portfolio Average Beta: **{avg_beta:.2f}** (vs. market 1.0)")
        md.append(f"- Highest Risk: {max(company_data.items(), key=lambda x: x[1].get('financials', {}).get('beta', 0))[0]} (Beta {max(betas):.2f})")
        md.append(f"- Lowest Risk: {min(company_data.items(), key=lambda x: x[1].get('financials', {}).get('beta', 99) if x[1].get('financials', {}).get('beta') else 99)[0]}")
    md.append("")

    md.append("### Valuation Thesis")
    md.append("")
    md.append("The PayPal Mafia portfolio is characterized by **premium valuations** driven by:")
    md.append("")
    md.append("1. **Network Effects**: META, YELP, HOOD — all platform businesses with user-driven moats")
    md.append("2. **Government Lock-in**: PLTR's classified contracts create 10+ year switching costs")
    md.append("3. **Category Creation**: TSLA (EVs), AFRM (transparent BNPL), SQ (merchant payments)")
    md.append("4. **Data Moats**: Every company in the portfolio generates proprietary datasets")
    md.append("")
    md.append("This explains P/E ratios consistently above market averages — the market prices in ")
    md.append("durable competitive advantages and network-driven growth compounding.")
    md.append("")

    md.append("### Correlation & Co-Movement Analysis")
    md.append("")
    md.append("Companies in the PayPal Mafia portfolio exhibit moderate-to-high correlation due to:")
    md.append("- Shared investor base (Founders Fund, Sequoia cross-hold)")
    md.append("- Similar macro sensitivity (tech/growth factor)")
    md.append("- Overlapping board members creating information flow")
    md.append("- Common customer segments (tech-savvy, high-income consumers)")
    md.append("")
    md.append("**Risk Implication:** High correlation means diversification benefit is limited ")
    md.append("within the mafia portfolio. A tech/growth downturn affects all simultaneously.")
    md.append("")

    return md


def generate_political_section(company_data: Dict, people: List) -> List[str]:
    """Government and political intelligence."""
    md = []
    md.append("### Federal Contract Portfolio Summary")
    md.append("")
    total_contracts = 0
    md.append("| Company | Total Obligations | Primary Agency | UEI Resolution |")
    md.append("|---------|------------------|----------------|---------------|")
    for ticker, data in company_data.items():
        c = data.get("contracts", {})
        total = c.get("total_obligations") or c.get("total_value", 0)
        if total:
            total_contracts += float(total)
            agency = "Multiple"
            awards = c.get("awards") or c.get("results", [])
            if isinstance(awards, list) and awards:
                agency = str(awards[0].get("agency") or awards[0].get("awarding_agency_name", ""))[:25]
            uei = c.get("recipient_uei") or "Text search"
            name = data.get("info", {}).get("name", ticker)
            md.append(f"| {name} | {fmt_money(total)} | {agency} | {uei} |")
    md.append(f"| **TOTAL** | **{fmt_money(total_contracts)}** | | |")
    md.append("")

    md.append("### Defense & Intelligence Concentration")
    md.append("")
    md.append("Palantir Technologies dominates the network's government relationship:")
    md.append("")
    md.append("- **Agencies served:** CIA, NSA, DHS, Army, Navy, Air Force, Space Force, CDC, NIH, IRS")
    md.append("- **Contract types:** IDIQ (Indefinite Delivery), Cost-Plus, Firm Fixed Price")
    md.append("- **Key programs:** Project Maven (AI for DoD), Army Vantage, CDC disease surveillance")
    md.append("- **International:** UK NHS, Australian Defence, NATO allies")
    md.append("")
    md.append("This concentration creates both opportunity (recurring revenue, high margins) and risk ")
    md.append("(political dependency, security clearance requirements, ethical scrutiny).")
    md.append("")

    md.append("### Lobbying Intelligence")
    md.append("")
    md.append("| Company | Total Lobby Spend | Key Issues | Trend |")
    md.append("|---------|------------------|-----------|-------|")
    for ticker, data in company_data.items():
        lob = data.get("lobbying", {})
        if lob and isinstance(lob, dict):
            spend = lob.get("spend_by_year", {})
            if isinstance(spend, dict) and spend:
                total = sum(float(v) for v in spend.values())
                issues = lob.get("issues", lob.get("issues_lobbied", []))
                issues_str = ", ".join(str(i) for i in issues[:3]) if issues else "General"
                name = data.get("info", {}).get("name", ticker)
                md.append(f"| {name} | {fmt_money(total)} | {issues_str} | Active |")
    md.append("")

    md.append("### Political Donations & Influence")
    md.append("")
    md.append("PayPal Mafia members are among the largest political donors in tech:")
    md.append("")
    md.append("| Person | Political Leaning | Notable Donations | Influence Vector |")
    md.append("|--------|------------------|-------------------|-----------------|")
    md.append("| Peter Thiel | Libertarian/Right | $15M+ to Trump PACs, JD Vance | Direct candidate backing |")
    md.append("| Elon Musk | Independent/Right | $100M+ political (2024) | Platform ownership (X) |")
    md.append("| Reid Hoffman | Democrat/Left | $20M+ to Biden/Dem PACs | Board influence, media |")
    md.append("| David Sacks | Libertarian/Right | $5M+ to GOP | Podcast influence, advisory |")
    md.append("| Keith Rabois | Right-leaning | Multiple GOP donations | VC network |")
    md.append("")
    md.append("**Key Insight:** The PayPal Mafia spans the political spectrum but concentrates ")
    md.append("on anti-regulatory, pro-innovation policy regardless of party affiliation.")
    md.append("")

    md.append("### Ambassadorial & Government Service")
    md.append("")
    md.append("| Person | Role | Period | Significance |")
    md.append("|--------|------|--------|-------------|")
    md.append("| Ken Howery | US Ambassador to Sweden | 2019-2021 | Diplomatic access |")
    md.append("| Peter Thiel | Trump Transition Team | 2016-2017 | Policy influence |")
    md.append("| Elon Musk | DOGE (Government Efficiency) | 2025-present | Direct executive power |")
    md.append("| David Sacks | White House AI/Crypto Czar | 2025-present | Policy architect |")
    md.append("")

    return md


def generate_fund_analysis(people: List) -> List[str]:
    """Venture fund analysis."""
    md = []
    md.append("### Venture Fund Operations")
    md.append("")
    md.append("The PayPal Mafia operates or has operated the following major venture funds:")
    md.append("")
    md.append("| Fund | GP(s) | Est. AUM | Focus | Notable Investments |")
    md.append("|------|-------|---------|-------|---------------------|")
    md.append("| Founders Fund | Thiel, Nosek, Howery | $12B | Deep tech, defense | SpaceX, Palantir, Stripe, Anduril |")
    md.append("| Sequoia Capital | Botha (MP) | $85B | Full-stack tech | Apple, Google, Airbnb, Stripe |")
    md.append("| Craft Ventures | Sacks | $3B | SaaS, crypto, defense | SpaceX, Bird, ClickUp |")
    md.append("| 8VC | Lonsdale | $5B | Defense, health, RE | Anduril, Oscar Health, Joby |")
    md.append("| Greylock Partners | Hoffman | $4B | Enterprise, consumer | LinkedIn, Discord, Figma |")
    md.append("| Khosla Ventures | Rabois (former) | $15B | Clean tech, enterprise | DoorDash, Affirm |")
    md.append("| Mithril Capital | Thiel | $2B | Growth stage | Palantir, SpaceX |")
    md.append("| Valar Ventures | Thiel | $1B | International fintech | TransferWise, N26 |")
    md.append("| Gigafund | Nosek | $1B | Space, energy | SpaceX, nuclear |")
    md.append("| Youniversity Ventures | Karim | <$500M | Seed/angel | Airbnb (early) |")
    md.append("")
    md.append(f"**Combined estimated AUM: >$125 billion**")
    md.append("")

    md.append("### Fund Interconnections")
    md.append("")
    md.append("These funds frequently co-invest, creating layered exposure:")
    md.append("")
    md.append("| Target Company | Funds Investing | Round | Significance |")
    md.append("|---------------|-----------------|-------|-------------|")
    md.append("| SpaceX | Founders Fund, Craft, Gigafund, 8VC | Multiple | Highest co-investment density |")
    md.append("| Anduril | Founders Fund, 8VC | Series D+ | Defense-tech alignment |")
    md.append("| Stripe | Founders Fund, Sequoia | Series A+ | Payments heritage |")
    md.append("| Palantir | Founders Fund, Mithril | Growth | Origin company |")
    md.append("| Airbnb | Founders Fund, Greylock, Sequoia | Multiple | Platform thesis |")
    md.append("")

    md.append("### Second-Generation Mafia")
    md.append("")
    md.append("Companies funded by PayPal Mafia VCs that have produced their own talent networks:")
    md.append("")
    md.append("| Company | Funded By | Alumni Now Leading |")
    md.append("|---------|-----------|-------------------|")
    md.append("| Stripe | Sequoia, Founders Fund | Stripe alumni at Ramp, Mercury, Modern Treasury |")
    md.append("| Palantir | Founders Fund, Mithril | Palantir alumni at Anduril, Databricks, Scale AI |")
    md.append("| Square/Block | Sequoia, Khosla | Square alumni at Plaid, Marqeta, Cash App spinoffs |")
    md.append("| LinkedIn | Greylock | LinkedIn alumni at hundreds of SaaS companies |")
    md.append("")
    md.append("This 'second-generation' effect means the PayPal Mafia's influence extends far beyond ")
    md.append("direct investments into a self-perpetuating talent and capital network.")
    md.append("")

    return md


def generate_risk_section(company_data: Dict, people: List) -> List[str]:
    """Risk assessment."""
    md = []
    md.append("### Concentration Risk Analysis")
    md.append("")
    md.append("| Risk Factor | Severity | Affected Companies | Mitigation |")
    md.append("|-------------|----------|-------------------|-----------|")
    md.append("| Tech sector downturn | HIGH | All | Diversification limited within portfolio |")
    md.append("| Interest rate sensitivity | HIGH | AFRM, HOOD, growth names | Duration risk on future cash flows |")
    md.append("| Regulatory crackdown (antitrust) | MEDIUM | META, GOOG, MSFT | Scale creates regulatory target |")
    md.append("| Defense budget cuts | MEDIUM | PLTR | Revenue concentration in government |")
    md.append("| Key person risk | HIGH | TSLA (Musk), AFRM (Levchin) | Founder-dependent narratives |")
    md.append("| Political backlash | MEDIUM | All | Mafia members' public political activity |")
    md.append("| AI disruption | LOW-MED | YELP, traditional SaaS | AI could disrupt review/search businesses |")
    md.append("")

    md.append("### Insider Trading Patterns")
    md.append("")
    md.append("Analysis of insider transactions across the portfolio reveals:")
    md.append("")
    total_sell = 0
    total_buy = 0
    for ticker, data in company_data.items():
        txns = data.get("insiders", {}).get("transactions", [])
        for t in txns:
            ttype = str(t.get("type", "")).lower()
            val = t.get("value", 0) or 0
            if "sell" in ttype or "sale" in ttype:
                total_sell += float(val)
            elif "buy" in ttype or "purchase" in ttype:
                total_buy += float(val)

    md.append(f"- **Net insider selling (2023-present):** {fmt_money(total_sell)}")
    md.append(f"- **Net insider buying (2023-present):** {fmt_money(total_buy)}")
    if total_sell and total_buy:
        ratio = total_sell / max(total_buy, 1)
        md.append(f"- **Sell/Buy Ratio:** {ratio:.1f}x")
    md.append("")
    md.append("*Note: Insider selling is common for diversification and does not necessarily indicate ")
    md.append("bearish sentiment, especially for founders with concentrated holdings.*")
    md.append("")

    md.append("### Geopolitical Risk Exposure")
    md.append("")
    md.append("| Company | China Revenue | Europe Revenue | Sanction Risk | Supply Chain Risk |")
    md.append("|---------|-------------|---------------|--------------|------------------|")
    md.append("| TSLA | High (Shanghai factory) | High | Medium | High (batteries) |")
    md.append("| META | Blocked in China | High (GDPR) | Low | Low |")
    md.append("| PLTR | None (excluded) | Growing | None | Low (software) |")
    md.append("| GOOG | Blocked in China | High (DMA/GDPR) | Low | Low |")
    md.append("| MSFT | Significant | High | Medium | Medium |")
    md.append("")

    md.append("### Network Fragility Assessment")
    md.append("")
    md.append("Despite its power, the PayPal Mafia network has potential fragility points:")
    md.append("")
    md.append("1. **Political Divergence**: Hoffman (left) vs. Thiel/Musk/Sacks (right) creates internal tension")
    md.append("2. **Generational Shift**: All members now 45-55+; succession at funds is underway")
    md.append("3. **Public Scrutiny**: 'All-In Podcast' and Twitter/X have increased public awareness of the network")
    md.append("4. **Regulatory Coordination**: If regulators connect the dots on cross-board influence")
    md.append("5. **Reputation Contagion**: One member's scandal could affect others (shared brand)")
    md.append("")

    return md


# ============ MAIN EXECUTION ============

def main():
    logger.info("Starting PayPal Mafia Expanded Report v2...")

    report_dir = Path(__file__).resolve().parent.parent.parent.parent / "apps" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    # Pull company data
    logger.info("Phase 1: Pulling financial intelligence for all companies...")
    tickers_to_pull = list(KEY_COMPANIES.keys()) + ["MSFT", "GOOG", "DASH", "ABNB"]
    company_data = {}

    for ticker in tickers_to_pull:
        info = KEY_COMPANIES.get(ticker, {"name": COMPANIES_FULL.get(ticker, {}).get("name", ticker), "mafia": []})
        logger.info(f"  {ticker} ({info['name']})...")
        company_name = info["name"].split("(")[0].strip()

        company_data[ticker] = {
            "info": info,
            "financials": get_company_financials(ticker),
            "insiders": get_insider_data(ticker),
            "lobbying": get_lobbying(company_name),
            "contracts": get_contracts(company_name),
            "institutional": get_institutional(ticker),
        }
        time.sleep(1.5)

    # Generate charts
    logger.info("Phase 2: Generating charts...")
    charts = generate_charts(company_data, PEOPLE)

    # Generate report
    logger.info("Phase 3: Generating full report...")
    report_md = generate_full_report(company_data, PEOPLE, charts)

    # Save markdown
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path = report_dir / f"PayPal_Mafia_EXPANDED_v2_{ts}.md"
    pdf_path = report_dir / f"PayPal_Mafia_EXPANDED_v2_{ts}.pdf"

    md_path.write_text(report_md, encoding="utf-8")
    words = len(report_md.split())
    logger.info(f"Markdown saved: {md_path.name} ({words:,} words, {len(report_md.splitlines()):,} lines)")

    # Render PDF
    logger.info("Phase 4: Rendering PDF...")
    try:
        import markdown as md_lib
        from weasyprint import HTML

        html_body = md_lib.markdown(report_md, extensions=["tables", "fenced_code", "toc"])
        css = """
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 40px; font-size: 9.5px; line-height: 1.45; color: #1a1a1a; }
h1 { font-size: 22px; border-bottom: 3px solid #1e40af; padding-bottom: 10px; color: #1e3a5f; page-break-before: always; }
h1:first-child { page-break-before: avoid; }
h2 { font-size: 15px; color: #1e40af; margin-top: 22px; border-bottom: 1.5px solid #dbeafe; padding-bottom: 5px; page-break-after: avoid; }
h3 { font-size: 12px; color: #374151; margin-top: 16px; page-break-after: avoid; }
h4 { font-size: 10.5px; color: #4b5563; margin-top: 10px; }
table { border-collapse: collapse; width: 100%; margin: 6px 0; font-size: 8.5px; page-break-inside: auto; }
th { background: #1e40af; color: white; padding: 4px 6px; text-align: left; }
td { padding: 3px 6px; border: 1px solid #e5e7eb; }
tr:nth-child(even) { background: #f9fafb; }
tr { page-break-inside: avoid; }
hr { border: none; border-top: 2px solid #1e40af; margin: 18px 0; }
img { max-width: 100%; height: auto; margin: 8px 0; page-break-inside: avoid; }
li { margin: 2px 0; }
strong { color: #1e3a5f; }
p { margin: 4px 0; }
@page { size: A4; margin: 1.5cm; @bottom-center { content: counter(page); font-size: 8px; color: #6b7280; } }
"""
        full_html = f"<!DOCTYPE html><html><head><meta charset='utf-8'><style>{css}</style></head><body>{html_body}</body></html>"
        HTML(string=full_html).write_pdf(str(pdf_path))

        import fitz
        doc = fitz.open(str(pdf_path))
        logger.info(f"PDF saved: {pdf_path.name} ({doc.page_count} pages)")
        doc.close()
    except Exception as e:
        logger.error(f"PDF render error: {e}")
        import traceback
        traceback.print_exc()

    logger.info("DONE")


if __name__ == "__main__":
    main()
