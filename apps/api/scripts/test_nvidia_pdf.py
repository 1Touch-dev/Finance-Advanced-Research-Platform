#!/usr/bin/env python3
"""
Test NVIDIA Premium PDF Generation
==================================
Generates a Hemispheric-quality PDF using mock data (no database/API required).

Usage:
    cd apps/api
    python scripts/test_nvidia_pdf.py
"""

import os
import sys
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.premium_pdf_service import convert_to_premium_pdf

# Configuration
ENTITY_NAME = "NVIDIA Corporation"
TICKER = "NVDA"


def main():
    print("=" * 60)
    print("NVIDIA Premium PDF Test")
    print("=" * 60)

    # Create comprehensive mock data matching Hemispheric quality
    report_data = {
        "entity_name": ENTITY_NAME,
        "ticker": TICKER,
        "report_type": "enhanced",
        "sections": [
            {
                "name": "Executive Summary",
                "claims": [
                    {
                        "text": "NVIDIA Corporation is the world's leading designer of graphics processing units (GPUs) and has become the dominant force in AI computing infrastructure. The company has successfully transformed from a gaming graphics company into the preeminent supplier of artificial intelligence training and inference hardware.",
                        "source": "Company Analysis",
                        "confidence": "DOCUMENTED"
                    },
                    {
                        "text": "The company's data center segment has grown to represent over 80% of total revenue, driven by unprecedented demand for AI training and inference hardware from hyperscalers, enterprises, and sovereign nations.",
                        "source": "SEC Filings",
                        "confidence": "DOCUMENTED"
                    },
                    {
                        "text": "NVIDIA maintains a commanding market share in the AI accelerator market, with estimates ranging from 70-90% depending on the specific segment. This dominance is supported by the company's CUDA software ecosystem, which creates significant switching costs for customers.",
                        "source": "Industry Analysis",
                        "confidence": "REPORTED"
                    },
                    {
                        "text": "Recent product launches including the Blackwell architecture demonstrate continued innovation leadership. The company's full-stack approach combining hardware, software, and systems integration positions it uniquely in the market.",
                        "source": "Product Analysis",
                        "confidence": "DOCUMENTED"
                    }
                ]
            },
            {
                "name": "Bottom Line",
                "section_name": "Bottom Line",
                "narrative": """
NVIDIA Corporation represents a generational investment opportunity at the nexus of artificial intelligence infrastructure buildout. The company's dominant market position in AI accelerators (70-90% share), combined with its proprietary CUDA software ecosystem and full-stack systems integration capability, creates durable competitive advantages that are difficult for competitors to replicate.

**Key Assessment Points:**
- **Market Leadership:** Unrivaled position in AI training infrastructure with expanding presence in inference
- **Financial Profile:** Best-in-class margins (74%+ gross margin) with demonstrated operating leverage
- **Strategic Moat:** CUDA ecosystem creates high switching costs; 15+ years of developer investment
- **Growth Trajectory:** Data center revenue growth exceeding 100% YoY; secular AI tailwind duration unknown but measured in years
- **Risk Factors:** Customer concentration (hyperscalers), geopolitical exposure (China restrictions), competitive dynamics (AMD, custom silicon)

**Intelligence Assessment:** NVIDIA's current trajectory suggests continued market dominance through at least the next hardware cycle (Blackwell → successor). The company's ability to capture value across the AI stack—from chips to systems to software—provides multiple revenue expansion vectors. Primary monitoring focus should be on customer diversification metrics and competitive response timelines.
"""
            },
            {
                "name": "Investment Thesis",
                "claims": [
                    {
                        "text": "**Recommendation: BUY (High Conviction)**\n\nNVIDIA represents a unique opportunity to invest in the infrastructure layer of the AI revolution. The company's dominant market position, proprietary software ecosystem, and continuous innovation create a compelling investment case despite elevated valuations.",
                        "source": "Investment Analysis",
                        "confidence": "ANALYTICAL"
                    },
                    {
                        "text": "## Bull Case Catalysts\n\n- **Hyperscaler Capex Cycle:** Microsoft, Google, Amazon, Meta are in early stages of AI infrastructure buildout with multi-year spending commitments\n- **Enterprise AI Adoption:** Corporate AI adoption is accelerating with NVIDIA positioned as the standard platform\n- **Inference Market Expansion:** As AI models deploy to production, inference compute demand will multiply\n- **Software/Platform Revenue:** CUDA ecosystem and AI Enterprise software create recurring revenue streams\n- **Sovereign AI:** Nations are building domestic AI compute capacity, creating new customer category",
                        "source": "Scenario Analysis",
                        "confidence": "ANALYTICAL"
                    },
                    {
                        "text": "## Bear Case Risks\n\n- **Competition Intensifies:** AMD MI300X gaining traction; Intel Gaudi3 launching; Hyperscaler custom silicon (Google TPU, Amazon Trainium, Microsoft Maia)\n- **Customer Concentration:** Top 4 customers represent significant revenue share\n- **Geopolitical Headwinds:** China export restrictions limit TAM; Taiwan semiconductor risk\n- **Valuation Risk:** Premium multiple vulnerable to growth deceleration\n- **Supply Chain:** TSMC concentration; CoWoS packaging constraints",
                        "source": "Risk Analysis",
                        "confidence": "ANALYTICAL"
                    },
                    {
                        "text": "## Key Milestones to Monitor\n\n1. Blackwell production ramp and yield metrics (H2 2024)\n2. Hyperscaler capex guidance on quarterly earnings calls\n3. Competitive product launches (AMD MI350, Intel Falcon Shores)\n4. China export policy developments\n5. Enterprise AI adoption metrics from customer surveys",
                        "source": "Monitoring Framework",
                        "confidence": "ANALYTICAL"
                    }
                ]
            },
            {
                "name": "Financial Health",
                "claims": [
                    {
                        "text": "## Financial Performance Summary\n\n| Metric | TTM Value | vs. Sector |\n|--------|-----------|------------|\n| Revenue | $96.3B | Above Average |\n| Revenue Growth (YoY) | 122% | Above Average |\n| Gross Margin | 74.5% | Above Average |\n| Operating Margin | 62.3% | Above Average |\n| Net Margin | 55.2% | Above Average |\n| ROE | 91.4% | Above Average |\n| ROA | 55.8% | Above Average |\n| Debt/Equity | 0.41 | Below Average |",
                        "source": "SEC Filings (10-K/10-Q)",
                        "source_url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001045810",
                        "confidence": "DOCUMENTED"
                    },
                    {
                        "text": "## Liquidity Analysis\n\nNVIDIA maintains a fortress balance sheet with $26.0B in cash and short-term investments against only $8.5B in total debt. Current ratio of 4.2x and quick ratio of 3.8x indicate exceptional short-term liquidity. Free cash flow generation of $27.0B TTM provides ample capital for R&D investment, strategic acquisitions, and shareholder returns.",
                        "source": "Balance Sheet Analysis",
                        "confidence": "DOCUMENTED"
                    },
                    {
                        "text": "## Profitability Assessment\n\nGross margins have expanded from 65% to 75% over two years as data center revenue mix increased. Operating margins at 62% reflect scale advantages and pricing power. The company's ability to maintain premium pricing while scaling volume demonstrates exceptional competitive positioning.",
                        "source": "Margin Analysis",
                        "confidence": "DOCUMENTED"
                    }
                ]
            },
            {
                "name": "Competitive Analysis",
                "claims": [
                    {
                        "text": "## Market Position\n\nNVIDIA commands 70-90% market share in AI training accelerators, a position built over a decade of investment in both hardware and software. The CUDA ecosystem, with over 4 million developers and 15 years of library development, creates substantial switching costs.",
                        "source": "Market Analysis",
                        "confidence": "DOCUMENTED"
                    },
                    {
                        "text": "## Competitive Landscape\n\n| Competitor | Product | Threat Level | Timeline |\n|------------|---------|--------------|----------|\n| AMD | MI300X/MI350 | MEDIUM | Current/2025 |\n| Intel | Gaudi3/Falcon Shores | LOW | 2024/2025 |\n| Google | TPU v5/v6 | MEDIUM | Internal use |\n| Amazon | Trainium2 | LOW | Internal use |\n| Microsoft | Maia 100 | LOW | Internal use |\n| Cerebras | Wafer-Scale | LOW | Niche |\n| Groq | LPU | LOW | Inference only |",
                        "source": "Competitive Intelligence",
                        "confidence": "ANALYTICAL"
                    },
                    {
                        "text": "## Competitive Moat Analysis\n\n**Sources of Competitive Advantage:**\n\n1. **CUDA Ecosystem:** 15+ years of software development creates lock-in\n2. **Full-Stack Integration:** Hardware + software + networking + systems\n3. **Scale Economics:** Manufacturing volume enables cost advantages\n4. **Innovation Velocity:** 2-year architecture cadence, continuous improvement\n5. **Network Effects:** Developer ecosystem attracts more developers\n\n**Moat Durability Assessment:** HIGH - Multi-year effort required for competitors to match ecosystem breadth",
                        "source": "Strategic Analysis",
                        "confidence": "ANALYTICAL"
                    }
                ]
            },
            {
                "name": "Key Personnel",
                "section_name": "Key Personnel",
                "narrative": """
## Executive Leadership Dossiers

### Jensen Huang — Founder, President & Chief Executive Officer

**Background:** Jensen Huang co-founded NVIDIA in 1993 and has served as President and CEO since inception. Under his leadership, NVIDIA transformed from a graphics company into the world's leading AI computing platform. His strategic vision anticipated the AI revolution years before mainstream recognition.

**Education:**
- BS Electrical Engineering, Oregon State University
- MS Electrical Engineering, Stanford University

**Prior Experience:**
- Director of CoreWare, LSI Logic (1985-1993)
- Design Engineer, AMD (1983-1985)

**Board Positions:** Member of the Board of Directors at Nordstrom, Inc.

**Assessment:** Huang's technical background, strategic vision, and operational execution have been consistently exceptional. His ability to identify and invest in AI computing before the market recognized its importance demonstrates rare foresight.

---

### Colette Kress — Executive Vice President & Chief Financial Officer

**Background:** Colette Kress joined NVIDIA as CFO in 2013, bringing extensive experience in semiconductor finance. She has overseen NVIDIA's financial transformation from a $4B to $96B+ revenue company.

**Education:**
- MBA, Duke University Fuqua School of Business
- BS Business Administration, University of Arizona

**Prior Experience:**
- SVP, Business Technology and Finance, Cisco Systems (2010-2013)
- CFO, Server and Tools Business, Microsoft (1998-2010)

**Assessment:** Kress has demonstrated strong capital allocation discipline and effective investor communication during NVIDIA's hypergrowth phase.

---

### Debora Shoquist — Executive Vice President, Operations

**Background:** Debora Shoquist oversees NVIDIA's global operations including manufacturing, quality, supply chain, and workplace services. Her operational leadership has been critical during supply-constrained periods.

**Education:**
- BS Engineering, University of Kansas

**Prior Experience:**
- SVP Operations, JDS Uniphase
- VP Manufacturing, Coherent, Inc.

**Assessment:** Shoquist's operations leadership has been tested during unprecedented demand surge and supply chain challenges, with generally strong execution.
"""
            },
            {
                "name": "Network Mapping",
                "section_name": "Network Mapping",
                "narrative": """
## Corporate Network Analysis

NVIDIA's corporate network spans technology partnerships, customer relationships, supply chain dependencies, and competitive dynamics across the global AI ecosystem.

### Key Relationship Categories

| Category | Entity | Relationship Type | Strategic Importance |
|----------|--------|-------------------|---------------------|
| Customer | Microsoft | Revenue Partner | HIGH |
| Customer | Meta Platforms | Revenue Partner | HIGH |
| Customer | Amazon Web Services | Revenue Partner | HIGH |
| Customer | Google Cloud | Revenue Partner | HIGH |
| Supplier | TSMC | Manufacturing | CRITICAL |
| Supplier | Samsung | Memory/Packaging | HIGH |
| Supplier | SK Hynix | HBM Memory | HIGH |
| Partner | OpenAI | AI Research | MEDIUM |
| Partner | NVIDIA Research | Internal R&D | HIGH |
| Competitor | AMD | Direct Competition | HIGH |
| Competitor | Intel | Direct Competition | MEDIUM |
| Regulatory | US Commerce Dept | Export Controls | HIGH |

### Network Risk Assessment

**Critical Dependencies:**
1. **TSMC** — Single-source for advanced node manufacturing (3nm, 4nm)
2. **HBM Suppliers** — SK Hynix, Samsung, Micron control memory supply
3. **CoWoS Packaging** — TSMC advanced packaging capacity constraints

**Network Opportunities:**
1. **Hyperscaler Relationships** — Deep integration enables preferential allocation
2. **Startup Ecosystem** — NVIDIA Inception program creates early customer relationships
3. **Research Partnerships** — Academic collaborations maintain innovation leadership
"""
            },
            {
                "name": "Government Contracts",
                "claims": [
                    {
                        "text": "NVIDIA received 23 federal contract award(s) totaling $187,500,000 in documented obligations according to USASpending.gov data.",
                        "source": "USASpending.gov",
                        "source_url": "https://www.usaspending.gov",
                        "confidence": "DOCUMENTED"
                    },
                    {
                        "text": "Top awarding agency: Department of Energy — $95,000,000 for AI and HPC computing systems at national laboratories.",
                        "source": "USASpending.gov",
                        "source_url": "https://www.usaspending.gov",
                        "confidence": "DOCUMENTED"
                    },
                    {
                        "text": "Department of Defense contracts: $52,000,000 for advanced computing and simulation systems.",
                        "source": "USASpending.gov",
                        "source_url": "https://www.usaspending.gov",
                        "confidence": "DOCUMENTED"
                    },
                    {
                        "text": "National Science Foundation: $25,000,000 for research computing infrastructure.",
                        "source": "USASpending.gov",
                        "source_url": "https://www.usaspending.gov",
                        "confidence": "DOCUMENTED"
                    }
                ]
            },
            {
                "name": "Lobbying & Regulatory",
                "section_name": "Regulatory",
                "narrative": """
## Lobbying & Regulatory Activity

NVIDIA maintains an active Washington presence focused on technology policy, export controls, and semiconductor industry support.

### Lobbying Expenditure

| Year | Total Spending | Key Issues |
|------|---------------|------------|
| 2024 YTD | $2.8M | Export controls, CHIPS Act, AI policy |
| 2023 | $4.2M | China restrictions, semiconductor subsidies |
| 2022 | $2.9M | Supply chain, trade policy |

### Priority Policy Areas

1. **Export Controls:** Advocating for narrowly tailored restrictions that balance national security with commercial interests
2. **CHIPS Act Implementation:** Engaging on R&D funding allocation and manufacturing incentives
3. **AI Policy:** Participating in AI safety and governance discussions
4. **Immigration:** Supporting H-1B visa and skilled worker immigration policies

### Regulatory Risk Assessment

**Key Regulatory Exposures:**
- China export restrictions limit ~$5B annual revenue opportunity
- Potential additional export controls on advanced AI chips
- Antitrust scrutiny of market position and acquisition activity
- AI regulation could impact product capabilities

**Assessment:** Regulatory environment presents meaningful risk but NVIDIA's government engagement is sophisticated. Company has generally navigated export control changes effectively.
"""
            },
            {
                "name": "News",
                "claims": [
                    {
                        "text": "NVIDIA Surpasses $3 Trillion Market Cap on AI Demand - Reuters (2024-06-05)",
                        "source": "Reuters",
                        "confidence": "DOCUMENTED"
                    },
                    {
                        "text": "Blackwell GPU Architecture Sets New AI Performance Records - NVIDIA Newsroom (2024-03-18)",
                        "source": "NVIDIA",
                        "confidence": "DOCUMENTED"
                    },
                    {
                        "text": "NVIDIA Reports Record Quarterly Revenue of $26 Billion - SEC Filing (2024-05-22)",
                        "source": "SEC EDGAR",
                        "confidence": "DOCUMENTED"
                    },
                    {
                        "text": "China Export Restrictions Impact NVIDIA Revenue Guidance - Financial Times (2024-04-15)",
                        "source": "Financial Times",
                        "confidence": "DOCUMENTED"
                    },
                    {
                        "text": "Microsoft Increases AI Infrastructure Spending, NVIDIA Primary Beneficiary - Bloomberg (2024-06-01)",
                        "source": "Bloomberg",
                        "confidence": "DOCUMENTED"
                    }
                ]
            },
            {
                "name": "Risk Matrix",
                "section_name": "Risk Matrix",
                "narrative": """
## Risk Assessment Matrix

| Risk Category | Description | Severity | Likelihood | Priority |
|---------------|-------------|----------|------------|----------|
| Competitive | AMD/Intel/Custom silicon market share gains | MEDIUM | MEDIUM | 2 |
| Geopolitical | China export restrictions expansion | HIGH | MEDIUM | 1 |
| Supply Chain | TSMC capacity/Taiwan geopolitical risk | HIGH | LOW | 2 |
| Valuation | Multiple compression on growth deceleration | MEDIUM | MEDIUM | 2 |
| Customer | Hyperscaler internal silicon development | MEDIUM | HIGH | 1 |
| Regulatory | Antitrust action on market position | LOW | LOW | 4 |
| Technology | Architectural disruption (new paradigms) | LOW | LOW | 4 |
| Execution | Blackwell production ramp issues | MEDIUM | LOW | 3 |

### Critical Watch Items

1. **Hyperscaler Custom Silicon Progress:** Monitor TPU, Trainium, Maia deployment metrics and performance claims
2. **China Policy Evolution:** Track Commerce Department announcements and customer workarounds
3. **AMD MI300X Adoption:** Watch hyperscaler announcements and benchmark publications
4. **Supply Chain Constraints:** Monitor TSMC CoWoS capacity additions and HBM availability

### Risk Mitigation Assessment

NVIDIA has demonstrated effective risk management through:
- Diversified customer base reducing concentration
- Long-term supply agreements securing capacity
- Continuous innovation maintaining technology leadership
- Software ecosystem creating switching costs
"""
            }
        ],
        "relationships_created": [
            {"kind": "customer", "dst_name": "Microsoft Corporation", "context": "Major cloud computing customer for AI GPUs"},
            {"kind": "customer", "dst_name": "Amazon Web Services", "context": "Data center GPU customer"},
            {"kind": "customer", "dst_name": "Google Cloud", "context": "Cloud infrastructure partner"},
            {"kind": "customer", "dst_name": "Meta Platforms", "context": "AI infrastructure customer"},
            {"kind": "competitor", "dst_name": "AMD", "context": "GPU and AI accelerator competitor"},
            {"kind": "competitor", "dst_name": "Intel Corporation", "context": "Data center and AI chip competitor"},
            {"kind": "supplier", "dst_name": "TSMC", "context": "Primary semiconductor foundry partner"},
            {"kind": "supplier", "dst_name": "SK Hynix", "context": "HBM memory supplier"},
            {"kind": "supplier", "dst_name": "Samsung Electronics", "context": "Memory and packaging supplier"},
            {"kind": "partner", "dst_name": "OpenAI", "context": "AI research and deployment partner"},
        ],
        "people_data": [
            {
                "name": "Jensen Huang",
                "title": "Founder, President & CEO",
                "bio": "Jensen Huang co-founded NVIDIA in 1993 and has served as President and CEO since inception. Under his leadership, NVIDIA transformed from a graphics company into the world's leading AI computing platform.",
                "education": [
                    {"school": "Oregon State University", "degree": "BS Electrical Engineering"},
                    {"school": "Stanford University", "degree": "MS Electrical Engineering"}
                ],
                "experience": [
                    {"company": "LSI Logic", "title": "Director of CoreWare"},
                    {"company": "AMD", "title": "Design Engineer"}
                ]
            },
            {
                "name": "Colette Kress",
                "title": "Executive Vice President & CFO",
                "bio": "Colette Kress joined NVIDIA as CFO in 2013, bringing extensive experience in semiconductor finance from Cisco and Microsoft.",
                "education": [
                    {"school": "Duke University", "degree": "MBA"},
                    {"school": "University of Arizona", "degree": "BS Business Administration"}
                ],
                "experience": [
                    {"company": "Cisco Systems", "title": "SVP, Business Technology"},
                    {"company": "Microsoft", "title": "CFO, Server and Tools"}
                ]
            },
            {
                "name": "Debora Shoquist",
                "title": "Executive Vice President, Operations",
                "bio": "Debora Shoquist oversees NVIDIA's global operations including manufacturing, quality, and supply chain management.",
                "education": [
                    {"school": "University of Kansas", "degree": "BS Engineering"}
                ],
                "experience": [
                    {"company": "JDS Uniphase", "title": "SVP Operations"},
                    {"company": "Coherent", "title": "VP Manufacturing"}
                ]
            }
        ],
        "summary": {
            "total_claims": 25,
            "total_sections": 11,
            "relationships_count": 10,
            "investment_recommendation": "BUY",
            "financial_grade": "A",
            "multi_agent_recommendation": "BUY",
            "multi_agent_composite_score": 82.5,
            "key_personnel_count": 3
        },
        "data_sources": {
            "sec_edgar": True,
            "usaspending": True,
            "fec": True,
            "yfinance": True,
            "multi_agent": True,
            "apollo_people": True
        }
    }

    # Generate PDF
    print("\nGenerating premium PDF...")

    try:
        pdf_bytes = convert_to_premium_pdf(
            entity_name=ENTITY_NAME,
            ticker=TICKER,
            report_data=report_data,
            prepared_for="Investment Committee",
            organization="ENTERPRISE INTELLIGENCE PLATFORM"
        )
        print(f"PDF size: {len(pdf_bytes):,} bytes")
    except Exception as e:
        print(f"ERROR: PDF generation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Save PDF
    output_filename = f"NVIDIA_Intelligence_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    output_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "reports",
        output_filename
    )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "wb") as f:
        f.write(pdf_bytes)

    print(f"\nSaved to: {output_path}")
    print(f"File size: {os.path.getsize(output_path):,} bytes")

    print("\n" + "=" * 60)
    print("SUCCESS!")
    print("=" * 60)
    print(f"\nOpen report: open '{output_path}'")

    return 0


if __name__ == "__main__":
    sys.exit(main())
