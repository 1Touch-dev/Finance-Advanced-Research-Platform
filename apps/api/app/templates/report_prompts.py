"""
Centralized AI Prompts for Enhanced Intelligence Reports.

This module contains all prompts used for generating enhanced narrative sections
including Investment Thesis, SWOT Analysis, Risk Matrix, Executive Summary,
and Financial Health Summary.

All prompts follow the confidence tagging convention:
- [DOCUMENTED] - Primary source data (SEC filings, official records)
- [REPORTED] - Secondary sources (news, press releases)
- [ANALYTICAL] - AI-generated inferences and recommendations
"""

from typing import Dict, Any, Optional


# Shared guardrail: forces every figure-heavy section to use ONLY the live data
# we injected (yfinance/SEC/etc.) instead of the model's stale training memory.
# Prevents artifacts like "Revenue $81.46B (2022)" appearing on a 2026 report.
DATA_DISCIPLINE = """
DATA DISCIPLINE (STRICT):
- Use ONLY numbers present in the DATA blocks above. Do NOT recall figures from memory.
- If a metric is not provided, write "n/a" — never estimate, guess, or backfill from training data.
- Do not attach historical years (e.g. "(2022)") to figures unless that year appears in the provided data.
- When you cite a figure, it must be traceable to a line in the DATA blocks.
"""


def get_executive_summary_prompt(
    entity_name: str,
    entity_type: str,
    report_data: Dict[str, Any],
    financial_data: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate prompt for executive summary (1-page brief)."""

    context = _build_context_block(report_data, financial_data)

    return f"""You are a senior intelligence analyst at a top-tier research firm.
Generate a comprehensive 1-page Executive Summary for {entity_name}.

CONTEXT DATA:
{context}

INSTRUCTIONS:
1. Write a professional executive summary suitable for C-suite executives
2. Structure as follows:
   - **Overview**: 2-3 sentences describing the entity, sector, and primary business
   - **Key Metrics**: Top 5-7 critical metrics (market cap, revenue, employees, etc.)
   - **Top 3 Opportunities**: Growth catalysts, market expansion, competitive advantages
   - **Top 3 Risks**: Material risks that could impact valuation or operations
   - **Recent Developments**: Key events from the last 90 days
   - **Bottom Line**: 2-3 sentence synthesis with actionable insight

3. Tag EVERY factual claim:
   - [DOCUMENTED] - Data from SEC filings, official records
   - [REPORTED] - News, press releases, secondary sources
   - [ANALYTICAL] - Your inferences and recommendations

4. Use precise numbers where available (cite sources)
5. Keep total length under 500 words
6. Use bullet points for readability
{DATA_DISCIPLINE}
OUTPUT FORMAT:
Return structured markdown with clear section headers.
"""


def get_investment_thesis_prompt(
    entity_name: str,
    ticker: Optional[str],
    report_data: Dict[str, Any],
    financial_data: Optional[Dict[str, Any]] = None,
    valuation_data: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate prompt for investment thesis with Buy/Hold/Sell recommendation."""

    context = _build_context_block(report_data, financial_data)
    valuation_context = _build_valuation_context(valuation_data) if valuation_data else "No valuation data available."

    return f"""You are a senior equity research analyst at Goldman Sachs.
Generate a rigorous Investment Thesis for {entity_name} (Ticker: {ticker or 'N/A'}).

INTELLIGENCE DATA:
{context}

VALUATION DATA:
{valuation_context}

INSTRUCTIONS:
Generate a professional investment thesis with:

1. **RECOMMENDATION**: Clear Buy / Hold / Sell rating
   - Provide conviction level (High/Medium/Low)
   - State recommended position size (Overweight/Equal-weight/Underweight)

2. **INVESTMENT SUMMARY**: 3-4 sentence thesis statement

3. **BULL CASE** (3 catalysts):
   - Catalyst 1: [Description with potential upside %]
   - Catalyst 2: [Description with potential upside %]
   - Catalyst 3: [Description with potential upside %]
   - Bull case price target with rationale

4. **BEAR CASE** (3 risks):
   - Risk 1: [Description with potential downside %]
   - Risk 2: [Description with potential downside %]
   - Risk 3: [Description with potential downside %]
   - Bear case price target with rationale

5. **FAIR VALUE ESTIMATE**:
   - Intrinsic value per share (DCF-based if available)
   - Current price vs fair value (% upside/downside)
   - Valuation methodology used

6. **KEY MILESTONES TO MONITOR**:
   - Next earnings date and expectations
   - Regulatory decisions pending
   - Product launches or expansions
   - M&A activity potential

7. **POSITION SIZING GUIDANCE**:
   - Recommended entry points
   - Stop-loss levels
   - Target exit price

Tag all claims appropriately:
- [DOCUMENTED] for data from SEC filings
- [REPORTED] for news-based information
- [ANALYTICAL] for your recommendations and inferences

Be specific with numbers. If data is unavailable, state "Data not available" rather than guessing.
{DATA_DISCIPLINE}
"""


def get_swot_analysis_prompt(
    entity_name: str,
    entity_type: str,
    report_data: Dict[str, Any],
    financial_data: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate prompt for SWOT analysis with evidence citations."""

    context = _build_context_block(report_data, financial_data)

    return f"""You are a strategic consultant at McKinsey & Company.
Generate a comprehensive SWOT Analysis for {entity_name}.

CONTEXT DATA:
{context}

INSTRUCTIONS:
Generate a detailed SWOT analysis with 5-7 items per quadrant.

For EACH item, provide:
1. Clear statement of the factor
2. Evidence citation (source document or data point)
3. Impact rating (1-5, where 5 = highest impact)

FORMAT:

## STRENGTHS (Internal Positive Factors)
| # | Strength | Evidence | Impact |
|---|----------|----------|--------|
| 1 | [Strength description] | [Source: specific document/filing] [DOCUMENTED/REPORTED] | 5 |
... (5-7 items)

## WEAKNESSES (Internal Negative Factors)
| # | Weakness | Evidence | Impact |
|---|----------|----------|--------|
| 1 | [Weakness description] | [Source: specific document/filing] [DOCUMENTED/REPORTED] | 4 |
... (5-7 items)

## OPPORTUNITIES (External Positive Factors)
| # | Opportunity | Evidence | Impact |
|---|-------------|----------|--------|
| 1 | [Opportunity description] | [Source: specific document/filing] [REPORTED/ANALYTICAL] | 5 |
... (5-7 items)

## THREATS (External Negative Factors)
| # | Threat | Evidence | Impact |
|---|--------|----------|--------|
| 1 | [Threat description] | [Source: specific document/filing] [REPORTED/ANALYTICAL] | 4 |
... (5-7 items)

## STRATEGIC SYNTHESIS
Write 3-4 sentences synthesizing the overall strategic position:
- Net assessment of competitive position
- Key strategic priorities recommended
- Critical success factors going forward

Tag all claims appropriately with [DOCUMENTED], [REPORTED], or [ANALYTICAL].
Be specific and cite actual data points from the context.
"""


def get_risk_matrix_prompt(
    entity_name: str,
    entity_type: str,
    report_data: Dict[str, Any],
) -> str:
    """Generate prompt for risk matrix with severity/likelihood ratings."""

    context = _build_context_block(report_data)

    return f"""You are a Chief Risk Officer conducting enterprise risk assessment.
Generate a comprehensive Risk Matrix for {entity_name}.

CONTEXT DATA:
{context}

INSTRUCTIONS:
Identify and categorize all material risks across these categories:
1. REGULATORY - Compliance, licensing, government action
2. FINANCIAL - Liquidity, credit, market, currency
3. OPERATIONAL - Supply chain, technology, execution
4. REPUTATIONAL - Brand, ESG, public perception
5. GEOPOLITICAL - International exposure, sanctions, trade

For EACH risk, provide:
- Risk description (1-2 sentences)
- Category (from list above)
- Severity (1-5): 1=Minor, 2=Moderate, 3=Significant, 4=Major, 5=Critical
- Likelihood (1-5): 1=Rare, 2=Unlikely, 3=Possible, 4=Likely, 5=Almost Certain
- Risk Score = Severity × Likelihood (1-25)
- Mitigation status: Mitigated / Partially Mitigated / Unmitigated
- Evidence source

FORMAT:

## RISK REGISTER

| ID | Risk | Category | Severity | Likelihood | Score | Mitigation | Evidence |
|----|------|----------|----------|------------|-------|------------|----------|
| R1 | [Description] | Regulatory | 4 | 3 | 12 | Partial | [Source] [DOCUMENTED] |
| R2 | [Description] | Financial | 5 | 2 | 10 | Mitigated | [Source] [REPORTED] |
... (identify ALL material risks, minimum 10)

## RISK HEATMAP DATA
```json
{{
  "critical_risks": ["R1", "R3"],  // Score >= 20
  "high_risks": ["R2", "R5"],       // Score 15-19
  "medium_risks": ["R4", "R6"],     // Score 8-14
  "low_risks": ["R7", "R8"]         // Score 1-7
}}
```

## OVERALL RISK SCORE
Calculate aggregate risk score (1-100 scale):
- Formula: Sum of all risk scores / (Number of risks × 25) × 100
- Interpretation: <30 Low Risk, 30-50 Moderate, 50-70 High, >70 Critical

## TOP 3 PRIORITY RISKS
For each of the top 3 risks by score:
1. **[Risk Name]** (Score: X)
   - Impact if realized: [Description]
   - Recommended mitigation: [Specific action]
   - Monitoring indicator: [KPI to track]

Tag all claims with [DOCUMENTED], [REPORTED], or [ANALYTICAL].
"""


def get_financial_health_prompt(
    entity_name: str,
    ticker: Optional[str],
    financial_data: Dict[str, Any],
    technicals_data: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate prompt for financial health summary."""

    financial_context = _build_financial_context(financial_data)
    technicals_context = _build_technicals_context(technicals_data) if technicals_data else ""

    return f"""You are a senior financial analyst at Moody's Analytics.
Generate a Financial Health Summary for {entity_name} (Ticker: {ticker or 'N/A'}).

FINANCIAL DATA:
{financial_context}

TECHNICAL INDICATORS:
{technicals_context}

INSTRUCTIONS:
Generate a comprehensive financial health assessment covering:

## 1. KEY FINANCIAL METRICS
| Metric | Value | Industry Avg | Assessment |
|--------|-------|--------------|------------|
| P/E Ratio | X | Y | Above/Below Average |
| P/B Ratio | X | Y | ... |
| EV/EBITDA | X | Y | ... |
| Gross Margin | X% | Y% | ... |
| Operating Margin | X% | Y% | ... |
| Net Margin | X% | Y% | ... |
| ROE | X% | Y% | ... |
| ROA | X% | Y% | ... |
| Current Ratio | X | Y | ... |
| Debt/Equity | X | Y | ... |

## 2. PROFITABILITY ASSESSMENT
- Margin trends (improving/stable/declining)
- Return on capital efficiency
- Earnings quality indicators

## 3. LIQUIDITY & SOLVENCY
- Short-term liquidity position
- Debt coverage capability
- Credit risk indicators

## 4. GROWTH METRICS
- Revenue growth (YoY, 3-year CAGR)
- EPS growth trajectory
- Market share trends

## 5. TECHNICAL POSITION (if data available)
- Current price vs moving averages
- RSI reading and interpretation
- MACD signal
- Support/resistance levels

## 6. FINANCIAL HEALTH GRADE
Assign overall grade: A+ to F
- A+/A/A-: Excellent financial health
- B+/B/B-: Good financial health
- C+/C/C-: Adequate financial health
- D+/D/D-: Weak financial health
- F: Critical financial distress

Provide 2-3 sentence rationale for grade.

Tag all data points:
- [DOCUMENTED] for audited financials
- [REPORTED] for estimates/projections
- [ANALYTICAL] for assessments
{DATA_DISCIPLINE}
"""


def get_competitive_analysis_prompt(
    entity_name: str,
    sector: Optional[str],
    report_data: Dict[str, Any],
) -> str:
    """Generate prompt for competitive analysis."""

    context = _build_context_block(report_data)

    return f"""You are a competitive intelligence analyst at Bain & Company.
Generate a Competitive Analysis for {entity_name} in the {sector or 'unknown'} sector.

CONTEXT DATA:
{context}

INSTRUCTIONS:
Generate a professional competitive analysis covering:

## 1. MARKET POSITION
- Current market share (estimate if not available)
- Position in competitive landscape (leader/challenger/follower/niche)
- Geographic footprint and concentration

## 2. KEY COMPETITORS
| Competitor | Market Share | Key Strength | Primary Threat |
|------------|--------------|--------------|----------------|
| [Name] | X% | [Strength] | [How they threaten {entity_name}] |
... (top 5-7 competitors)

## 3. COMPETITIVE MOATS
Assess each potential moat (Strong/Moderate/Weak/None):
- **Network Effects**: [Assessment and evidence]
- **Switching Costs**: [Assessment and evidence]
- **Cost Advantages**: [Assessment and evidence]
- **Intangible Assets**: [Patents, brands, licenses - assessment]
- **Efficient Scale**: [Assessment and evidence]

## 4. COMPETITIVE DYNAMICS
- Industry concentration (HHI estimate)
- Barriers to entry (High/Medium/Low)
- Threat of substitutes
- Supplier/buyer power

## 5. STRATEGIC POSITIONING
- Current strategy characterization
- Differentiation factors
- Vulnerabilities to competitive action

## 6. COMPETITIVE OUTLOOK
- 12-month competitive trajectory
- Key competitive battles to watch
- Potential disruptors

Tag claims: [DOCUMENTED], [REPORTED], or [ANALYTICAL]
"""


# ============================================================================
# HELPER FUNCTIONS FOR CONTEXT BUILDING
# ============================================================================

def _build_context_block(
    report_data: Dict[str, Any],
    financial_data: Optional[Dict[str, Any]] = None,
) -> str:
    """Build context block from report sections."""

    context_parts = []

    # Extract sections from report
    sections = report_data.get("sections", [])
    for section in sections:
        section_name = section.get("name", "Unknown Section")
        claims = section.get("claims", [])

        if claims:
            context_parts.append(f"\n### {section_name}")
            for claim in claims[:10]:  # Limit to top 10 claims per section
                text = claim.get("text", "")
                confidence = claim.get("confidence", "UNKNOWN")
                context_parts.append(f"- {text} [{confidence}]")

    # Add KPIs if available
    kpis = report_data.get("kpis", {})
    if kpis:
        context_parts.append("\n### KEY PERFORMANCE INDICATORS")
        for key, value in kpis.items():
            context_parts.append(f"- {key}: {value}")

    # Add financial data if available
    if financial_data:
        context_parts.append("\n### FINANCIAL DATA")
        fundamentals = financial_data.get("fundamentals", {})
        for key, value in fundamentals.items():
            if value is not None:
                context_parts.append(f"- {key}: {value}")

    return "\n".join(context_parts) if context_parts else "No context data available."


def _build_valuation_context(valuation_data: Dict[str, Any]) -> str:
    """Build valuation context from DCF data."""

    if not valuation_data:
        return "No valuation data available."

    parts = []

    # DCF results
    dcf = valuation_data.get("dcf", {})
    if dcf:
        parts.append("### DCF VALUATION")
        parts.append(f"- Enterprise Value: ${dcf.get('enterprise_value', 'N/A'):,.0f}" if isinstance(dcf.get('enterprise_value'), (int, float)) else f"- Enterprise Value: {dcf.get('enterprise_value', 'N/A')}")
        parts.append(f"- Equity Value: ${dcf.get('equity_value', 'N/A'):,.0f}" if isinstance(dcf.get('equity_value'), (int, float)) else f"- Equity Value: {dcf.get('equity_value', 'N/A')}")
        parts.append(f"- Intrinsic Price: ${dcf.get('intrinsic_price', 'N/A'):.2f}" if isinstance(dcf.get('intrinsic_price'), (int, float)) else f"- Intrinsic Price: {dcf.get('intrinsic_price', 'N/A')}")
        parts.append(f"- Current Price: ${dcf.get('current_price', 'N/A'):.2f}" if isinstance(dcf.get('current_price'), (int, float)) else f"- Current Price: {dcf.get('current_price', 'N/A')}")
        parts.append(f"- Upside/Downside: {dcf.get('upside_pct', 'N/A'):.1f}%" if isinstance(dcf.get('upside_pct'), (int, float)) else f"- Upside/Downside: {dcf.get('upside_pct', 'N/A')}")

    # Scenarios
    scenarios = valuation_data.get("scenarios", {})
    if scenarios:
        parts.append("\n### SCENARIO ANALYSIS")
        for name, data in scenarios.items():
            price = data.get("price", "N/A")
            parts.append(f"- {name.title()}: ${price:.2f}" if isinstance(price, (int, float)) else f"- {name.title()}: {price}")

    return "\n".join(parts)


def _build_financial_context(financial_data: Dict[str, Any]) -> str:
    """Build financial context from yfinance data."""

    if not financial_data:
        return "No financial data available."

    parts = []

    fundamentals = financial_data.get("fundamentals", {})
    if fundamentals:
        parts.append("### FUNDAMENTALS")
        key_metrics = [
            "pe_ratio", "pb_ratio", "ev_ebitda", "gross_margin",
            "operating_margin", "net_margin", "roe", "roa",
            "current_ratio", "debt_equity", "revenue", "net_income"
        ]
        for metric in key_metrics:
            value = fundamentals.get(metric)
            if value is not None:
                parts.append(f"- {metric.replace('_', ' ').title()}: {value}")

    company_info = financial_data.get("company_info", {})
    if company_info:
        parts.append("\n### COMPANY INFO")
        parts.append(f"- Sector: {company_info.get('sector', 'N/A')}")
        parts.append(f"- Industry: {company_info.get('industry', 'N/A')}")
        parts.append(f"- Employees: {company_info.get('employees', 'N/A'):,}" if isinstance(company_info.get('employees'), (int, float)) else f"- Employees: {company_info.get('employees', 'N/A')}")
        parts.append(f"- Market Cap: ${company_info.get('market_cap', 'N/A'):,.0f}" if isinstance(company_info.get('market_cap'), (int, float)) else f"- Market Cap: {company_info.get('market_cap', 'N/A')}")

    return "\n".join(parts)


def _build_technicals_context(technicals_data: Dict[str, Any]) -> str:
    """Build technicals context from indicators."""

    if not technicals_data:
        return "No technical data available."

    parts = []
    summary = technicals_data.get("summary", {})

    if summary:
        parts.append("### TECHNICAL SUMMARY")
        parts.append(f"- RSI(14): {summary.get('rsi', 'N/A'):.1f}" if isinstance(summary.get('rsi'), (int, float)) else f"- RSI(14): {summary.get('rsi', 'N/A')}")
        parts.append(f"- MACD Signal: {summary.get('macd_signal', 'N/A')}")
        parts.append(f"- 50-day SMA: ${summary.get('sma_50', 'N/A'):.2f}" if isinstance(summary.get('sma_50'), (int, float)) else f"- 50-day SMA: {summary.get('sma_50', 'N/A')}")
        parts.append(f"- 200-day SMA: ${summary.get('sma_200', 'N/A'):.2f}" if isinstance(summary.get('sma_200'), (int, float)) else f"- 200-day SMA: {summary.get('sma_200', 'N/A')}")
        parts.append(f"- Support: ${summary.get('support', 'N/A'):.2f}" if isinstance(summary.get('support'), (int, float)) else f"- Support: {summary.get('support', 'N/A')}")
        parts.append(f"- Resistance: ${summary.get('resistance', 'N/A'):.2f}" if isinstance(summary.get('resistance'), (int, float)) else f"- Resistance: {summary.get('resistance', 'N/A')}")

    return "\n".join(parts)


# ============================================================================
# PROMPT RETRIEVAL INTERFACE
# ============================================================================

def get_bottom_line_prompt(
    entity_name: str,
    ticker: Optional[str],
    report_data: Dict[str, Any],
    financial_data: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate prompt for BOTTOM LINE executive callout (Hemispheric-style)."""

    context = _build_context_block(report_data, financial_data)

    return f"""You are a senior intelligence analyst writing a BOTTOM LINE assessment.
Generate a crisp, actionable BOTTOM LINE callout for {entity_name} ({ticker or 'N/A'}).

CONTEXT DATA:
{context}

INSTRUCTIONS:
Write a 3-4 paragraph BOTTOM LINE executive assessment that:

1. **First paragraph**: State the core investment/intelligence thesis in 2-3 sentences. What is the single most important thing a decision-maker needs to know? Be direct and assertive.

2. **Second paragraph**: Identify the primary tension or conflict. What competing forces, risks, or uncertainties define the current situation? Name specific actors, events, or structural factors.

3. **Third paragraph**: Highlight network/relationship factors that matter. Who are the key players, what are their entanglements, and why does this matter for the investment/intelligence case?

4. **Fourth paragraph (optional)**: Forward-looking watch items. What should be monitored? What events would change the thesis?

STYLE REQUIREMENTS:
- Write in intelligence-briefing style: dense, specific, assertive
- Use specific names, dates, dollar amounts, and percentages
- Avoid hedging language ("may", "might", "could potentially")
- Each sentence should contain actionable information
- Tag claims: [DOCUMENTED], [REPORTED], or [ANALYTICAL]

{DATA_DISCIPLINE}
OUTPUT: Return ONLY the BOTTOM LINE text (no headers, no markdown formatting).
"""


def get_key_personnel_prompt(
    entity_name: str,
    entity_type: str,
    report_data: Dict[str, Any],
    people_data: Optional[list] = None,
) -> str:
    """Generate prompt for Key Personnel dossiers (Hemispheric-style)."""

    context = _build_context_block(report_data)
    people_context = ""
    if people_data:
        people_context = "\n### KNOWN PERSONNEL\n"
        for p in people_data[:15]:
            if isinstance(p, dict):
                name = p.get('name', p.get('full_name', 'Unknown'))
                title = p.get('title', p.get('headline', ''))
                people_context += f"- {name}: {title}\n"

    return f"""You are an intelligence analyst compiling personnel dossiers.
Generate detailed Key Personnel profiles for {entity_name}.

CONTEXT DATA:
{context}
{people_context}

INSTRUCTIONS:
For each key person (CEO, CFO, key executives, board members), provide:

## [PERSON NAME] — [Title]

**Current Role**: [Description of responsibilities and tenure]

**Career History**:
- [Most recent prior role] — [Company], [Years]
- [Earlier role] — [Company], [Years]
- [Foundational experience] — [Company], [Years]

**Education**:
- [Degree], [Institution], [Year if known]
- [Additional credentials]

**Board Seats & Affiliations**:
- [Current board positions]
- [Advisory roles]
- [Nonprofit/institutional affiliations]

**Financial Entanglements** (if any):
- [Stock ownership, options, recent transactions]
- [Investments in related entities]
- [Potential conflicts of interest]

**Network Notes**:
- [Connections to other key figures in this report]
- [Co-employment or co-education links]
- [Investment/business relationship overlaps]

REQUIREMENTS:
- Profile at minimum: CEO, CFO, and 2-3 other key executives
- Be specific with dates, institutions, dollar amounts
- Flag any documented Russia/China/sanctioned-entity exposure
- Note any regulatory or legal history
- Tag all claims: [DOCUMENTED], [REPORTED], or [ANALYTICAL]

{DATA_DISCIPLINE}
"""


def get_network_mapping_prompt(
    entity_name: str,
    report_data: Dict[str, Any],
    relationships: Optional[list] = None,
) -> str:
    """Generate prompt for network/relationship mapping (Hemispheric-style)."""

    context = _build_context_block(report_data)
    rel_context = ""
    if relationships:
        rel_context = "\n### KNOWN RELATIONSHIPS\n"
        for r in relationships[:20]:
            if isinstance(r, dict):
                src = r.get('source', r.get('src_entity', ''))
                dst = r.get('target', r.get('dst_entity', ''))
                kind = r.get('kind', r.get('relationship_type', ''))
                rel_context += f"- {src} → {dst} ({kind})\n"

    return f"""You are a network intelligence analyst mapping financial/political relationships.
Generate a Network Mapping analysis for {entity_name}.

CONTEXT DATA:
{context}
{rel_context}

INSTRUCTIONS:
Map the key relationship networks around this entity:

## 1. OWNERSHIP & CONTROL NETWORK
- Major shareholders (>5% ownership)
- Subsidiary relationships
- Joint ventures and partnerships
- Voting control vs economic interest gaps

## 2. BOARD & EXECUTIVE INTERLOCKS
| Person | Role at {entity_name} | Other Boards/Roles | Network Significance |
|--------|----------------------|-------------------|---------------------|
| [Name] | [Role] | [Other positions] | [Why this matters] |

## 3. INVESTOR/CAPITAL NETWORK
- Key institutional investors
- Sovereign wealth fund exposure
- Private equity/VC relationships
- Family office connections

## 4. POLITICAL/REGULATORY NETWORK
- Government contracts and relationships
- Lobbying relationships (as client AND as target)
- Regulatory body connections
- Political donation patterns

## 5. CO-INVESTMENT PATTERNS
Identify entities that share investors with {entity_name}:
| Shared Investor | Other Portfolio Companies | Investment Thesis Link |
|-----------------|--------------------------|----------------------|

## 6. EDUCATIONAL/PROFESSIONAL LINEAGE
- "Mafia" networks (PayPal mafia, Goldman alumni, etc.)
- Shared educational backgrounds (Stanford MBA cohorts, etc.)
- Prior employer alumni networks

## 7. NETWORK RISKS & WATCH ITEMS
- Sanctions exposure through network connections
- Reputational contagion risks
- Regulatory scrutiny on network members

Tag all claims: [DOCUMENTED], [REPORTED], or [ANALYTICAL]
Be specific with names, dates, and dollar amounts.
"""


def get_watch_items_prompt(
    entity_name: str,
    report_data: Dict[str, Any],
    financial_data: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate prompt for Watch Items / Outlook section (Hemispheric-style)."""

    context = _build_context_block(report_data, financial_data)

    return f"""You are a senior intelligence analyst writing forward-looking watch items.
Generate an Outlook & Watch Items section for {entity_name}.

CONTEXT DATA:
{context}

INSTRUCTIONS:
Generate 8-12 specific, actionable watch items organized by timeframe:

## NEAR-TERM (30-90 days)
For each item:
- **[Watch Item]**: [Why this matters] — [Trigger event or date to monitor]

Examples of what to include:
- Earnings releases and guidance
- Regulatory decisions pending
- Product launches
- Executive changes
- Litigation milestones

## MEDIUM-TERM (3-12 months)
- Strategic initiatives and their milestones
- Competitive dynamics to monitor
- Macroeconomic factors affecting the entity
- Political/regulatory calendar events

## STRUCTURAL / LONG-TERM
- Industry transformation factors
- Technology disruption vectors
- Demographic or market shifts
- Geopolitical realignment impacts

## SCENARIO TRIGGERS
Identify specific events that would materially change the investment thesis:

| Scenario | Trigger Event | Impact on Thesis |
|----------|---------------|-----------------|
| Bull Case Acceleration | [Specific event] | [How thesis improves] |
| Bear Case Activation | [Specific event] | [How thesis deteriorates] |
| Thesis Invalidation | [Specific event] | [Why position should be exited] |

## MONITORING INDICATORS
Key metrics to track on an ongoing basis:
- [KPI 1]: Current value, threshold levels
- [KPI 2]: Current value, threshold levels
- [KPI 3]: Current value, threshold levels

REQUIREMENTS:
- Be specific with dates, names, and numbers
- Each watch item should be actionable
- Prioritize by materiality to investment thesis
- Tag all claims: [DOCUMENTED], [REPORTED], or [ANALYTICAL]

{DATA_DISCIPLINE}
"""


def get_government_exposure_prompt(
    entity_name: str,
    report_data: Dict[str, Any],
) -> str:
    """Generate prompt for Government Contracts & Exposure analysis."""

    context = _build_context_block(report_data)

    return f"""You are an analyst specializing in government contracting and political exposure.
Generate a Government Exposure analysis for {entity_name}.

CONTEXT DATA:
{context}

INSTRUCTIONS:
Analyze government relationships across all dimensions:

## 1. FEDERAL CONTRACTING PROFILE
| Agency | Contract Type | Value | Period | Status |
|--------|--------------|-------|--------|--------|
| [Agency] | [Type] | [$Amount] | [Years] | [Active/Complete] |

Summary metrics:
- Total contract value (lifetime): $X
- Active contract value: $X
- Top 3 agencies by spend
- Contract concentration risk

## 2. LOBBYING ACTIVITY (AS CLIENT)
| Lobbying Firm | Issues | Annual Spend | Key Lobbyists |
|---------------|--------|--------------|---------------|

- Total lobbying spend (annual): $X
- Primary legislative targets
- Regulatory agencies targeted

## 3. LOBBYING EXPOSURE (AS TARGET)
Which industries/entities lobby AGAINST this entity?
- Competitive lobbying efforts
- Regulatory opposition campaigns

## 4. POLITICAL DONATIONS
- PAC contributions by party/candidate
- Executive personal contributions
- 501(c)(4) dark money exposure (if known)

## 5. REGULATORY RELATIONSHIP
- Key regulatory bodies with jurisdiction
- Recent enforcement actions
- Pending investigations or inquiries
- Compliance infrastructure assessment

## 6. GEOPOLITICAL EXPOSURE
- Foreign government relationships
- CFIUS/national security considerations
- Sanctions compliance status
- Export control exposure

## 7. GOVERNMENT RISK ASSESSMENT
| Risk Factor | Severity | Likelihood | Mitigation Status |
|-------------|----------|------------|-------------------|

Tag all claims: [DOCUMENTED], [REPORTED], or [ANALYTICAL]
"""


PROMPT_REGISTRY = {
    "executive_summary": get_executive_summary_prompt,
    "investment_thesis": get_investment_thesis_prompt,
    "swot_analysis": get_swot_analysis_prompt,
    "risk_matrix": get_risk_matrix_prompt,
    "financial_health": get_financial_health_prompt,
    "competitive_analysis": get_competitive_analysis_prompt,
    "bottom_line": get_bottom_line_prompt,
    "key_personnel": get_key_personnel_prompt,
    "network_mapping": get_network_mapping_prompt,
    "watch_items": get_watch_items_prompt,
    "government_exposure": get_government_exposure_prompt,
}


def get_prompt(
    prompt_type: str,
    entity_name: str,
    **kwargs,
) -> str:
    """
    Get a prompt by type with provided parameters.

    Args:
        prompt_type: One of executive_summary, investment_thesis, swot_analysis,
                    risk_matrix, financial_health, competitive_analysis
        entity_name: Name of the entity being analyzed
        **kwargs: Additional parameters specific to each prompt type

    Returns:
        Formatted prompt string

    Raises:
        ValueError: If prompt_type is not recognized
    """
    if prompt_type not in PROMPT_REGISTRY:
        raise ValueError(
            f"Unknown prompt type: {prompt_type}. "
            f"Available: {list(PROMPT_REGISTRY.keys())}"
        )

    return PROMPT_REGISTRY[prompt_type](entity_name=entity_name, **kwargs)


def list_available_prompts() -> list:
    """Return list of available prompt types."""
    return list(PROMPT_REGISTRY.keys())
