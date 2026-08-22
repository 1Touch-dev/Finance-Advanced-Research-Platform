# Source Depth Register — 48 Sources

**Owner:** Dev-1 · **Status:** template + triage complete, per-source audit runs in S1 (25 Aug → 7 Sep)
**Answers:** James, 18 Aug — *"Fred api and all of the ones we have integrated you are using. There is a lot of data there. You really need to research each source."*

Audit spec: [A1](04-VERIFICATION-AUDIT-PLAYBOOK.md#a1--source-depth-audit).

---

## 1. The distinction this document exists to make

```
   WHAT WE TOLD JAMES              WHAT HE ASKED BACK
   ──────────────────              ──────────────────────────────
   "48 APIs integrated"            "you really need to research
    (5 Aug, numbered list)          each source"        (18 Aug)

   INTEGRATED  =  we can call it, a page renders
   RESEARCHED  =  we know every field it returns, which we use,
                  which we ignore, what it costs, what it's licensed
                  for, and what edges it can produce for the graph

   The 48 are integrated. Roughly zero are researched.
```

Breadth was the wrong axis. A source called for 3 fields out of 60 is not an integration, it is a
demo. This register replaces the count with a measurement.

---

## 2. Per-source template

Every source gets exactly this block. 14 fields, from [A1](04-VERIFICATION-AUDIT-PLAYBOOK.md#a1--source-depth-audit).

```markdown
### [Source name]
| Field | Value |
|---|---|
| Connector file | `apps/api/app/connectors/x.py` |
| Auth / key | env var, status |
| Endpoints available | N |
| Endpoints we call | M  → **M/N** |
| Fields available | N |
| Fields we extract | M  → **M/N ← the number that matters** |
| History available | e.g. 1913–present |
| History ingested | e.g. 5y |
| Update frequency | real-time / daily / quarterly |
| Rate limit vs. our burn | e.g. 120/min vs. ~8/min |
| Cost | $/mo |
| ToS / redistribution | ✅ allowed / ⚠️ restricted / ❌ prohibited |
| Entity IDs emitted | CIK, LEI, ticker, FEC ID, Bioguide… |
| Known quality issues | free text |
| Failure behaviour | `no_data` / exception / **fabricated value ← defect** |
| Fallback source | which source, or none |
| Consumed by | pages/reports |
| **Edge types producible** | `person–officer_of–org`, … |
| **Depth gap score** | 0–5 |
| Priority action | one line |
```

**Depth gap score:** `0` fully exploited · `1` minor fields unused · `2` useful fields unused ·
`3` major endpoints unused · `4` mostly unexploited · `5` connector exists but barely calls anything.

---

## 3. Triage — all 48, pre-audit

Scores are my estimates from reading the connectors; S1's job is to replace them with counts.
Ordered by **intelligence value × gap**, which is the order Dev-1 works them.

### 3.1 Tier 1 — highest leverage (audit + close in S1)

These ten carry the graph. Each is free or already paid for, and each is badly under-extracted.

| # | Source | Connector | Gap | Unused capability | Edges it unlocks |
|:--:|---|---|:--:|---|---|
| 1 | **SEC EDGAR** | `sec_edgar_connector.py` (1,960 ln) | **4** | All exhibits, full XBRL fact set, **SC 13D/G**, S-1, 8-K item codes | `officer_of`, `activist_stake_in`, `subsidiary_of` |
| 2 | **SEC-API.io** | `sec_api_connector.py` | **4** | **Form D full investor lists**, 13D/G, S-1 | `invested_in` ← richest private-money edge we already pay for |
| 3 | **DEF 14A proxy** | `proxy_statement_connector.py` | **5** | Director bios, other-board seats, comp, **Item 404 related-party transactions** | `director_of`, **`related_party_of`** ★ |
| 4 | **FRED** | via market/econ services | **4** | Category tree, releases, **ALFRED vintages** | — but delivers [A4](04-VERIFICATION-AUDIT-PLAYBOOK.md#a4) point-in-time nearly free |
| 5 | **FEC** | `packages/connectors/us/fec/` | **4** | Contributions by **employer + occupation** | `employed_by` at national scale, free |
| 6 | **Senate LDA** | `packages/connectors/us/lda/` | **4** | Issue codes, **named lobbyists**, covered officials | `lobbied_for`, `revolving_door_from` |
| 7 | **USASpending** | `packages/connectors/us/usaspending/` | **3** | **Sub-awards**, recipient parent hierarchy | `awarded`, `subcontracted_to` |
| 8 | **CourtListener** | `litigation_connector.py` | **4** | **Docket entries**, parties, RECAP docs | `party_to`, docket velocity (L5) |
| 9 | **Congress.gov** | `packages/connectors/us/congress/` | **3** | Bills → sponsors → committees → votes | `sponsored`, `voted_on` — the insider-timing thesis |
| 10 | **OpenSecrets** | `opensecrets_connector.py` | **3** | Revolving door, personal financial disclosures | `revolving_door_from`, officials' own holdings |

★ **Row 3 is the single highest-value fix in the register.** James has asked about family entities,
wives, kids, trusts and holding companies on 30 Jul, 31 Jul, 2 Aug and 4 Aug. SEC rules *require*
public companies to disclose related-party transactions in DEF 14A Item 404. We parse proxies for
board names and skip the section that literally answers him. One parser closes a four-times-repeated
request.

### 3.2 Tier 2 — real value, second pass (S1–S2)

| # | Source | Connector | Gap | Note |
|:--:|---|---|:--:|---|
| 11 | GovInfo | `us/govinfo/` | 3 | Congressional reports, hearings — founder/exec testimony |
| 12 | SAM.gov | `us/sam/` | 3 | Entity registrations, exclusions list |
| 13 | FPDS | `fpds_connector.py` | 2 | Contract modifications, competition type |
| 14 | Regulations.gov | `us/regulations/` | 3 | Comment submitters = corporate influence, unused |
| 15 | GLEIF | `us/gleif/` | 2 | **Parent/child hierarchy** — direct `subsidiary_of` edges |
| 16 | OpenCorporates | `us/opencorporates/` | 3 | Officers, ownership structure |
| 17 | OFAC | `us/ofac/` | 1 | Screening works; add event-study hooks (L4) |
| 18 | FARA | `us/fara/` | **4** | Foreign-agent registrations — **not consumed anywhere**, high signal |
| 19 | IRS 990 | `us/irs990/` | **4** | Foundation grants + trustees — **family/philanthropy vehicles**, unused |
| 20 | State registry | `us/state_registry/` | 3 | 50-state registry; Delaware COI per target |
| 21 | Federal Register | `us/federal_register/` | 2 | Rule-making timeline |
| 22 | eCFR / reginfo OIRA | `us/ecfr/`, `us/reginfo_oira/` | 2 | Regulatory pipeline |
| 23 | BEA | `us/bea/` | 3 | Industry-level economics |
| 24 | FMP | `fmp_ipo_connector.py` + | 2 | IPO calendar live; financials/valuation endpoints underused |
| 25 | Finnhub | `finnhub_earnings_connector.py` | 2 | Earnings live; ownership + insider endpoints unused |
| 26 | FINRA | `finra_short_interest_connector.py` | 1 | New. Verify live before claiming done. |
| 27 | Alpha Vantage | market services | 2 | Fallback role |
| 28 | yfinance | `yfinance_connector.py` | 1 | James: *"no need. But maybe validator or fall back"* — correct as-is |
| 29 | Apollo.io | `apollo_connector.py` | 3 | Paid. Person↔company enrichment underused. |
| 30 | Apify | `apify_connector.py` | 3 | James's own suggestion: VC portfolio pages, company pages |
| 31 | UK Companies House | — | **5** | On the 5 Aug list; **no connector found**. Free, literal cap structure. |
| 32 | Aleph (OCCRP) | — | **5** | Key pending; OSINT/investigative corpus |
| 33 | California SOS / Cobalt | `us/state_registry/` | 4 | Key pending |

### 3.3 Tier 3 — news & sentiment (verify, don't extend)

| # | Source | Connector | Gap | Note |
|:--:|---|---|:--:|---|
| 34–37 | NewsAPI, Guardian, NYT, Google News RSS | `financial_news_connector.py` | 2 | Works. Needs entity linking into the graph. |
| 38 | Reddit | `news_intelligence_connector.py` | 2 | SPECULATIVE tier only, permanently |
| 39 | RSS (50+ feeds) | `rss_worker.py` | 1 | Working, `rss-poller` online |
| 40 | LinkedIn | `linkedin_deep_connector.py` | — | **ToS-blocked.** Replace with People Data Labs — see [D2](06-DECISION-LOG.md#d2) |

### 3.4 Tier 4 — infrastructure, not intelligence sources

Listing these as "integrated APIs" to James inflated the 48 and is part of why the number misled.

| # | Source | Role | Action |
|:--:|---|---|---|
| 41–42 | Anthropic, OpenAI | LLM inference | Not data sources — reclassify |
| 43–44 | Stripe, Mercado Pago | Payments | Reclassify |
| 45–46 | SendGrid, Twilio | Delivery | Reclassify |
| 47 | Didit | KYC | Reclassify |
| 48 | Twenty CRM | CRM | Reclassify |
| — | OpenSearch, S3/MinIO, Google OIDC | Infra | Reclassify |
| — | NFe.io, Focus NFe | Brazilian invoicing | Unrelated to finance intelligence |

### 3.5 Deprioritised by James

| Source | Status |
|---|---|
| CoinGecko, CoinCap, Etherscan, Blockchain.info, CoinTelegraph | *"not focused on crypto at all; it is the least of my priorities"* (18 Aug). Maintain, never extend. |

---

## 4. What the recount actually says

| Category | Count | Reality |
|---|:--:|---|
| **Intelligence data sources** | **~33** | The real number |
| Infrastructure / SaaS misfiled as sources | 8 | Payments, email, SMS, KYC, CRM, LLMs |
| Deprioritised (crypto) | 5 | CEO-declined |
| **On the list but no connector found** | **2** | UK Companies House, Aleph |
| ToS-blocked | 1 | LinkedIn |
| Nominal total | 48 | |

**The honest headline for James:** *"We said 48. It is really ~33 intelligence sources, of which 10
carry most of the value and all 10 are extracting under a third of what they offer. Here is the
measured gap, and here is the sequence to close it."*

That is a stronger message than 48, not a weaker one — it demonstrates exactly the research he asked
for, and it is the kind of self-correcting count the 72-feature register itself recommends treating
as a good sign rather than a planning failure.

---

## 5. Free edges we are not collecting

Consolidated view of §3 — every one of these is **free or already paid for**, and each is a direct
answer to a specific thing James asked for.

| Edge type | Source | Cost | His ask it answers |
|---|---|---|---|
| `person–related_party_of–entity` | DEF 14A Item 404 | free | *"families use their wives, kids… holding companies"* |
| `investor–invested_in–org` | Form D investor lists | paid ✅ | *"all investment done by them"* |
| `person–employed_by–org` | FEC employer/occupation | free | *"analyze employees deeply"* |
| `firm–lobbied_for–org` + named lobbyists | Senate LDA | free | *"Lobbying activity needs all details"* |
| `holder–activist_stake_in–org` | SC 13D/G | free | *"Investors and cap table need all details"* |
| `person–revolving_door_from–agency` | OpenSecrets + LDA | free | Excel sheet 6, revolving door |
| `foundation–granted_to–org` + trustees | IRS 990 | free | family/philanthropy vehicles |
| `person–foreign_agent_for–principal` | FARA | free | not requested; high-signal bonus |
| `org–subsidiary_of–org` | GLEIF hierarchy | free | corporate structure |
| `agency–awarded–vendor` → sub-awards | USASpending | free | *"contracts they have"* |
| `person–sponsored–bill` | Congress.gov | free | legislation-to-trade timing |
| `entity–party_to–case` + docket velocity | CourtListener | free | L-series timing edge |

Twelve edge types. Zero incremental spend. This is the S1-B + S2-C work, and it is the strongest
available argument that the private-market budget in [D2](06-DECISION-LOG.md#d2) is a *second* step,
not the first one.

---

## 6. Output of the S1 audit

1. This register, completed — 33 blocks with counted fields.
2. `docs/program/SOURCE-DEPTH-SCORECARD.md` — auto-generated table, gap score + extraction %.
3. Ranked gap list feeding S1-B.
4. Edge-type inventory feeding S2-C.
5. `GET /health/data` — per-source last success, extraction %, staleness.
6. One CEO-facing page: the 10 sources, the gap, the plan, the cost ($0).
