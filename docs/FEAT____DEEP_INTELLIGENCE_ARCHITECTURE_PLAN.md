
# Deep Intelligence Report Architecture Plan

---

## 🔴 0. TOPMOST PRIORITY — THE GAP AGAINST JAMES'S BRIEF (2026-07-31)

**This section outranks everything below it.** Sections 1–5 track parity with
the reference PDF and the free-source backlog. That work is now largely done.
What follows is the distance between the current 45-page output and what James
has actually asked for across the 14–31 July messages, stated plainly.

### 0.1 Where we stand

**Roughly half of the brief is built.** The half that rests on **filings a
company is legally compelled to make** is strong, automated and ticker-agnostic.
The half that rests on **news, the open web and people** has barely started.

We have built the **spine** — everything a company is forced to disclose,
pulled and cross-checked automatically for any ticker. That is the hard,
reliable part and it is done. What is missing is the **flesh** — news, people
histories, and the web research that turns "here are the facts" into "here is
what is really going on."

### 0.2 Shipped against the brief

| # | James asked for | Where it lands in the report |
|---|-----------------|------------------------------|
| 1 | Data visualisation, graphs, tables | 12 figures embedded; was zero |
| 2 | Every public contract broken down, checked for self-dealing | §11 prime award ledger + award integrity screens |
| 3 | Lobbying, all details | §12 — every dollar, registrant, issue code, PAC |
| 4 | Board members' other companies | §8.6 interlocks, from their own Section 16 filings |
| 5 | Family entities, related-party dealing | §8.5 Item 404, including family employment |
| 6 | Investors who also hold the competitors | §10.2 common ownership + allocation skew |
| 7 | Subsidiaries and holding structures | §5.1 Exhibit 21, incl. offshore jurisdictions |
| 8 | Insider behaviour against price | §9 + V-11 overlay on daily bars |
| 9 | Timeline of events | §14 — 317 filing-derived events |
| 10 | Valuation and what the market implies | §7 DCF, sensitivity grid, reverse-DCF |

### 0.3 NOT built — ordered by what unblocks the most

| # | Gap | Nature | Cost |
|---|-----|--------|------|
| **G-01** | **News — zero.** No articles, interviews, rumours, Reddit, whale tracking | Build — the single largest hole; James has asked for it four separate times | Free/cheap feeds exist |
| **G-02** | **Employees.** Only board and named officers; no staff career histories | Build + source decision | LinkedIn/Apify ~$0.05/profile |
| **G-03** | **"PayPal mafia" analysis.** Schools, who met whom, what they built together | Build on top of G-02 | Depends on G-02 |
| **G-04** | **Family networks.** Wives/children/holding entities caught only when a filing names them; no active hunting | Build | Free — state registries, Form 3/4 addresses |
| **G-05** | **Private-round co-investors.** Who else was in the round | **Blocked — no free path** | PitchBook/Crunchbase $6–20K/yr |
| **G-06** | **Statistical correlations.** "Insiders sell before bad news" — price bars now exist, the maths does not | Build — event-study code | Free (D-01 shipped) |
| **G-07** | **Multi-company comparison.** Four competitors, ownership only; not deep | Build | Free — peer financials partly held |
| **G-08** | **Interactive reports.** Static PDF; cannot click, search or drill in | Build — product decision on format | Free |
| **G-09** | **LinkedIn deep research.** Connector exists (461 lines), switched off | Wire + settle ToS position | ~$0.05/profile |
| **G-10** | **Data-health alerts.** Nobody is notified when a source breaks | Build — ops, explicitly requested | Free |

**Two of the ten need money** (G-05 outright, G-02/G-09 marginally). The other
eight are engineering time against sources we already reach.

### 0.4 Fix before this goes to a client

**The lobbying section reports +3711% spend growth 2022→2026.** That is almost
certainly sparse early-year data rather than a real trajectory. A number that
large will be the first thing a reader challenges, and it undermines the exact
totals sitting beside it. Verify the early-year LDA pagination before the
report is shown externally.

---

## Executive Summary

**Current State**: 2-page NVIDIA report with placeholder data, ~5% data populated
**Target State**: Match the reference report (42 pages, 16 sections, 95%+ data density) using **free sources only**
**Gap (corrected diagnosis 2026-07-30)**: The connectors mostly EXIST and are substantial (SEC EDGAR 633 lines, proxy parser 734 lines, litigation 813 lines). The failure is in **pipeline wiring and report assembly**: connector output never reaches the markdown template, and the missing stock price zeroes the entire DCF. Evidence: the generated report's Base FCF of $102.72B exactly matches the reference's FY2026 operating cash flow ($102,718M) — SEC XBRL **is** flowing; the $0.00 values are downstream.

**Reference Benchmark**: `/reports/NVIDIA Corporation — Intelligence Report.pdf` (42 pages, 16 sections, 95%+ data density)

**Scope Correction (v3.0)**: The reference report is built almost entirely from free sources — SEC EDGAR (XBRL companyfacts, 10-K R-file exhibits, DEF 14A, 163 raw Form 4 XMLs), USASpending filtered by UEI, Senate LDA API, and Perplexity Finance for market/consensus data. It contains NO LinkedIn enrichment, family trees, board interlock graphs, 13F competitor overlap, patent data, or paid sources (Crunchbase/PitchBook/BoardEx). Therefore:
- **Phase 1 (now)** = match the reference PDF with free sources only
- **Phase 3+ (later)** = James's expanded "Hemispheric" vision (Layers 2–8, LinkedIn, correlation engine, 80–120 pages)

**Scope amendment (v3.1, 2026-07-31 — James).** The Phase 1 / Phase 3+ split
above was drawn along "in the reference report / not in the reference report".
That line is now redrawn along **source cost**, because it was deferring work
that is free and reachable today. The reference report is a floor, not a
ceiling: matching it is no longer the whole of Phase 1.

- **P0 now** = free public sources, including the network intelligence the
  reference does not contain — board interlocks, 13F competitor overlap,
  related-party transactions, subsidiary trees, 5%+ holders, and the issuer's
  own venture portfolio (§4C.3 P-series, §4C.4 N-series)
- **Phase 3+** = paid vendors only — LinkedIn, PitchBook, Crunchbase, BoardEx,
  RelSci. The single capability this defers is identifying **co-investors in a
  funding round**, which no free source discloses (see P-10)

---

## 🔄 PHASE 1 IMPLEMENTATION STATUS TRACKER

### ✅ RESOLVED IN THIS PASS (2026-07-31) — root causes, not workarounds

Six defects were fixed. Five were single-line or single-parameter errors that
each silently emptied a whole report section; none required new parsers.

| # | Defect | Root cause | Effect of fix |
|---|--------|------------|---------------|
| R1 | **Ticker→CIK resolution failing intermittently** | Four divergent implementations. `sec_edgar_connector` requested `company_tickers.json` from `data.sec.gov` (404 — the file only exists on `www.sec.gov`). `company_deep_connector` first called `cgi-bin/browse-edgar` and *discarded* the response; its timeout aborted the lookup before the working request ran. `proxy_statement_connector` and `timeline_connector` scraped the same rate-limited endpoint. | Consolidated onto one cached resolver with retry. Unblocked financials, proxy, insider and timeline data simultaneously — this was the single largest cause of empty sections. |
| R2 | **Revenue absent; all margins 0.0%** | `get_concept_values` returned the first concept name that *existed*, and NVIDIA abandoned `RevenueFromContractWithCustomerExcludingAssessedTax` after FY2022. Four-year-stale periods never aligned with current rows. | Candidate concepts are merged by period. Revenue, margins, CapEx and FCF now match the reference exactly. |
| R3 | **Federal awards understated 918x ($50K vs $46M)** | USASpending rejects `award_type_codes` spanning multiple groups, so only the `contracts` group was queried. NVIDIA's DARPA and DOE awards sit in the `other` group. | All award-type groups queried separately and combined; name-collision recipients (ENVIDIA/INVIDIA) excluded by alias validation. |
| R4 | **Lobbying showing a phantom $100K** | Filter parameter was `filing_client_name`; the correct name is `client_name`. The API ignored the unknown parameter and returned all 54,307 filings in the register — the connector summed the first page of unrelated organisations. | Correct parameter, multi-year pagination, in-house vs outside-firm split. Totals $14.0M, matching the reference. |
| R5 | **Litigation section empty** | CourtListener API v3 was retired and returns HTTP 403; the token was also read from `COURTLISTENER_API_KEY` while `.env` defines `COURTLISTENER_API_TOKEN`. | Moved to v4 with the correct variable. Cases where the company is a *party* are now counted separately from cases that merely cite it. |
| R6 | **DCF output $0.00** | Beta, shares, price, market cap, debt and cash were read from yfinance inside one `try` block, so a single failure zeroed all six. | New `market_data_connector.py` with a Finnhub → FMP → Alpha Vantage chain, plus SEC XBRL for balance-sheet items. Each field resolves independently. |

**Additional corrections:** Q4 is derived as full-year minus Q1–Q3 and
explicitly flagged `DERIVED`; FTC results were counting page navigation links
("Press Release", "Cases and Proceedings") as legal matters.

**Result:** report grew from 106 lines / 391 words to 359 lines / 2,744 words
across 12 populated sections, with a pre-render quality gate that fails the
build on placeholder values.

### ✅ RESOLVED: MARKET-WIDE APPLICABILITY (2026-07-31)

The six fixes above were validated only against NVIDIA. Auditing the pipeline
across a basket chosen to stress different fiscal calendars, sectors and naming
conventions (`scripts/audit_cross_ticker.py`) exposed seven further defects that
NVIDIA's characteristics happened to hide. All are now fixed.

| # | Defect | Root cause | Effect of fix |
|---|--------|------------|---------------|
| G1 | **Fiscal years mislabelled for 52/53-week retail calendars** | The previous fix derived the label from the period end year. Retailers name a fiscal year for the year it *starts*: Target's year ending 2026-01-31 is FY2025, not FY2026. | The label is taken from the earliest filing that reported the period, which is the issuer's own label. Correct for both conventions without special-casing either. |
| G2 | **Companies reorganised under a holding company returned no financials at all** | SEC maps XOM to "ExxonMobil Holdings Corp" (zero XBRL concepts); the 438-concept history remains under "EXXON MOBIL CORP". | New `get_filer_cik` verifies the mapped CIK reports XBRL facts and falls back to EDGAR full-text search for the CIK that filed the 10-Ks. |
| G3 | **No revenue line for any bank or insurer** | Banks stop tagging `Revenues` and report `RevenuesNetOfInterestExpense`; JPMorgan's last `Revenues` fact is from 2014. | Financial-sector concepts added to the candidate list. JPM now yields quarterly revenue and TTM where it previously had none. |
| G4 | **TTM understated for issuers on a 52/53-week calendar** | A row at the fiscal year end holding non-income facts made the interim-quarter count four instead of three, suppressing the derived Q4. Target's TTM summed only three quarters of the year. | Interim quarters are those ending strictly inside the year; a row at the year end is enriched rather than duplicated. Target's TTM corrected from $99.8B to $106.4B. |
| G5 | **Federal contract ledgers filled with unrelated recipients** | Word-boundary name matching. An Apple report listed "TOWN OF APPLE VALLEY", "BIG APPLE SIGN CORP" and "WASHINGTON APPLE COMMISSION" as its federal awards. | New `entity_naming` module requires the recipient to *begin* with the entity name, with only divisional qualifiers trailing. Apple's ledger reduced to genuine "APPLE INC" awards. |
| G6 | **Litigation tables listing unrelated cases** | CourtListener was queried with an unquoted common word, matching any opinion using it. A Target report listed "United States v. Lopez" and "Intel Corp v. Nvidia Corp". | The query is phrase-quoted and captions are matched party-wise; only matters naming the company are rendered. |
| G7 | **Another company's ticker in the output** | The price line was hardcoded to `NVDA`, so every report showed that label beside its own (correct) figures. | Rendered from the payload, and the quality gate now fails a report that names a ticker other than its subject. |

**Also generalised:** the report generator takes `--ticker` and resolves the
registrant name, exchange and peer set from it; output files are named after the
resolved registrant; market cap is formatted at a scale suited to its magnitude
(a fixed trillions scale rendered every sub-$10B company as `$0.00T`); the
hardcoded NVIDIA subsidiary map became a caller-supplied argument; and 160 lines
of fabricated NVIDIA sample data were deleted from the generator.

**Validation:** `scripts/audit_cross_ticker.py` covers ten issuers spanning
September, June, December and February fiscal year ends, banks, energy, REITs
and hyphenated share-class tickers. `tests/test_entity_naming.py` holds 32
regression cases drawn from the false positives above. Reports generated end to
end for AAPL, TGT, XOM, JPM, NVDA and PLAB all pass the quality gate.

### ✅ RESOLVED: PERSONNEL, OWNERSHIP AND VALUATION (2026-07-31, third pass)

The four items left open above are now closed. As before, most were defects in
existing code rather than absent capability, and three of them were suppressing
data for *every* issuer rather than only for edge cases.

| # | Defect | Root cause | Effect of fix |
|---|--------|------------|---------------|
| H1 | **Form 4 filings found but zero transactions parsed** | The submissions index gives the *rendered* document path, `xslF345X06/wk-form4_….xml`, which serves an HTML page produced from the XML by an XSL transform. The parser fetched that page and every `<rptOwnerName>` regex failed. It also used `re.search`, capturing at most one row per filing, and read 10b5-1 status from `transactionTimeliness` instead of the `aff10b5One` checkbox. | Raw XML is fetched by stripping the transform directory; all `nonDerivativeTransaction` and `derivativeTransaction` rows are parsed. NVIDIA yields 203 transactions from 59 filings, $900.2M of open-market sales split into plan-based and discretionary. |
| H2 | **Any high-volume filer returned no Form 4, 8-K or 10-K at all** | `get_company_submissions` truncated to the first 100 filings before any form filter was applied. JPMorgan files roughly a hundred 424B2 structured-note prospectuses *in a single day*, so its entire window held nothing else. | Filtering happens across the whole submission index. JPMorgan went from 0 to 133 Form 4 filings. This affected every bank and structured-note issuer. |
| H3 | **Fabricated HIGH-severity governance red flag on every company** | `_extract_say_on_pay` initialised `approval_pct` to `0.0`, and the flag test was `latest_sop.get("approval_pct", 100) < 70`. The fallback never applied because the key always existed, so a failed parse was indistinguishable from total shareholder revolt and raised "Say-on-pay approval only 0.0%". | Unretrieved values are `None` and no flag is raised without a figure. Results are additionally sought from 8-K Item 5.07, which is the authoritative vote record. |
| H4 | **Board roster always empty** | `_get_recent_proxies` took the most recently filed proxies. DEFA14A is *additional soliciting material* — a vote-reminder letter with no tables — and because it is filed after the proxy it sorts first. The parser was reading letters. Its roster extraction also regex-matched any two adjacent capitalised words in the document text. | Definitive DEF 14A filings are preferred, and the roster is read from the Director Compensation table, which lists the full board one director per row. NVIDIA returns 10 directors with fees and committee membership. |
| H5 | **Institutional ownership unavailable** | The connector depended on yfinance, which is not installed. Every commercial substitute is paywalled on the current tiers: Finnhub fund-ownership returns 403, FMP ownership endpoints 404. | New `institutional_holdings_connector.py` reads SEC Form 13F-HR information tables from the largest managers directly — the same public filings the vendors resell. NVIDIA 30.6% of shares outstanding across 9 managers, JPMorgan 28.6%, Target 37.7%. |
| H6 | **No issuer with an ampersand in its name was ever found in a 13F** | Issuer names arrive XML-escaped as `JPMORGAN CHASE &amp; CO.` and were matched raw. | Entities are unescaped before matching. Affected JPMorgan, Procter & Gamble, Johnson & Johnson and every similar name. |
| H7 | **A manager's two-year-old position shown beside current ones** | BlackRock's polled CIK stopped filing in Aug 2024 after the group reorganised — the same holdco pattern as G2. Its stale August 2024 holding sat in a table of May 2026 positions. | Live CIK adopted, plus a general staleness guard that excludes and reports any manager whose latest 13F predates the last 400 days. |
| H8 | **13F position values wrong by 1000x between adjacent rows** | The SEC dropped the "report in thousands" convention for periods from 2023 but adoption is uneven, so one table mixes Vanguard reporting dollars with T. Rowe Price reporting thousands. | Filed values are compared against shares times market price to determine the scale actually used. |
| H9 | **FEC contributions always zero** | Callers passed the company name where an FEC committee ID was expected, and the parser read Schedule A's `contribution_receipt_amount` from Schedule B, where the field is `disbursement_amount`. | Company names resolve to sponsored PACs, validated against the company name with PAC-naming words stripped so "OVER THE TARGET PAC" is not attributed to Target. Target $1.2M and JPMorgan $1.9M across three cycles; NVIDIA correctly reports no registered PAC. |
| H10 | **Free cash flow overstated by the entire capital programme** | The same tag-migration failure as R2, in a second place: capex tried `PaymentsToAcquirePropertyPlantAndEquipment` and fell back only if it was absent. NVIDIA still has that tag but stopped using it, so only stale years returned and every recent period matched no capex — silently zero. Periods were also matched on the XBRL `fy` field, which labels the filing rather than the period. | Candidate capex concepts are merged and matched on period end date. NVIDIA capex $6.0B and FCF $96.7B now match the reference. |

**DCF alignment.** The model was 5 years at a flat growth rate discounted on raw
beta. It now runs a 10-year horizon with growth fading linearly to the terminal
rate, and discounts on a Blume-adjusted beta — raw regression beta is a noisy
estimate that reverts towards the market, and NVIDIA's raw 2.25 drove WACC to
16.9%. The adjustment is applied uniformly rather than tuned per issuer, taking
NVIDIA's beta to 1.83 and WACC to 14.7%. The base case moved from $69.58 to
$77.12. This remains below the reference's $142.16: the reference sustains high
growth for its full horizon where this model fades it, which is a deliberately
conservative choice rather than an unreconciled difference.

**Still open:** say-on-pay is retrieved for some issuers and honestly reported
as absent for the rest; XLSX appendix (P0-13) and the precedent library (P0-12)
are not started.

### ✅ RESOLVED: NARRATIVE RENDERING (2026-07-31, fourth pass)

The report held the right facts but presented all of them as tables, which is
why it ran to 2,691 words against the reference's 19,257. The reference states
the same data as sourced prose. This pass closed that gap for the three largest
sections and fixed the defects the change exposed.

| # | Defect | Root cause | Effect |
|---|--------|-----------|--------|
| N1 | Insider sample truncated to 60 of 195 Form 4 filings | `max_filings` default capped the newest-first scan | Disposals understated four-fold: 203 transactions / $900M became 1,011 / $3.54B, against the reference's 801 / $2.83B over a shorter window |
| N2 | Every 8-K rendered as "Material Event" | The submissions index does not carry an 8-K's subject, and the Item numbers were never read from the filing | Chronology could not distinguish an earnings release from an executive departure; all 21 8-Ks now carry their reported Items |
| N3 | Director profiles carried no age, tenure, independence, committees or biography | The roster came from the Director Compensation table, which holds none of those; the nominee summary table and per-director cards were never parsed | Key Personnel was 421 words against the reference's 4,075; now 3,900 |
| N4 | Litigation rendered as a four-column table | Docket, court, cause of action, nature of suit and judge were all retrieved but discarded at render | Legal was 134 words describing 5 matters that the docket already described fully |
| N5 | Form 4 records never matched their director | EDGAR files reporting owners surname-first ("STEVENS MARK A") while the proxy writes "Mark A. Stevens"; matching on the last token yielded "a" | Every profile silently omitted its dealing history |
| N6 | A four-digit year was read as a director's age | Column positions drift between issuers and the read was unguarded | AAPL reported an age of 2024; ages and years are now range-checked |
| N7 | Name cells unmatched for issuers using layout padding | Cells held zero-width spaces, honorifics and footnote markers ("Mr. Quincey*") | Rosters were short or empty for affected issuers |
| N8 | Ticker→CIK resolution drew HTTP 429 and emptied whole reports | SEC's ticker map is the first request every run makes and was refetched per process with no on-disk cache | A throttled map takes every downstream section with it; now cached for 7 days |

**Verified across issuers** rather than on NVIDIA alone, since the extractors
key off proxy layout, which varies. Directors with a biography: NVDA 11/13,
JPM 8/11, TGT 7/10, AAPL 5/9, PLAB 4/8. Ages: JPM 0→11, TGT 0→6, AAPL 2→7.

**Known limits, stated rather than hidden:** KO's roster does not resolve (its
director compensation table is not matched by the current heuristics) and XOM
returns no proxy. JPM and KO do not disclose director ages at all, so a blank
there is the filing's silence, not a parser miss.

### ✅ RESOLVED: RISK REGISTER AND EXECUTIVE PAY (2026-07-31, fifth pass)

| # | Defect | Root cause | Effect |
|---|--------|-----------|--------|
| N9 | Risk Register absent from every report | Regression from the N3/H3 say-on-pay fix: defaulting `approval_pct` to `None` made `if approval_pct < 80` raise `TypeError`, and the orchestrator's broad `except` swallowed it into a silent `sources_failed` increment | An entire section was lost on a guard that was meant to *prevent* a false finding. The comparison now skips an unretrieved value instead of treating absence as a low vote |
| N10 | "Compensation" listed the board at identical $278,809 | The extractor matched any table containing "Stock Awards"; the Director Compensation table has that column and appears first, so director retainers were rendered as executive pay | Reported NEO compensation was wrong for every issuer. Now keyed on the Summary Compensation Table's salary column: Huang $6.0M total (matches reference), Cook $74.3M, Cornell $21.8M |
| N11 | Job titles rendered as executives | Principal positions run onto the name with no whitespace ("Tim CookChief Executive Officer") and also arrive as separate rows repeating the same figures | Phantom executives named "Executive Vice President"; names now split from titles and title-only rows rejected |
| N12 | Each executive listed three times | Summary Compensation Tables report three fiscal years per person | Only the most recent year is shown |

**Result:** 12/12 sources succeed with zero failures for the first time;
13 sections, 6,771 words.

### ✅ RESOLVED: THE PDF WAS NEVER RENDERING THE REPORT (2026-07-31, sixth pass)

The report looked thin because most of it never reached the page. The PDF and
the markdown were produced by two different renderers, and only the markdown
received any of the work of passes one through five.

| # | Defect | Root cause | Effect |
|---|--------|-----------|--------|
| N13 | PDF carried 1 of 13 sections and 3,296 of 6,771 words | `main()` built the PDF through `_convert_to_legacy_format()` into `premium_pdf_service.generate_premium_report_html()`, a 4,000-line renderer written against an older schema. Every section added since was absent from that schema, so it emitted nothing for them | The document under review had no Executive Summary, Valuation, Legal, Chronology, Risk Register or Methodology, and no director biography, docket or 8-K item. The markdown beside it was complete. Density was 122 words/page against the reference's 466. The PDF is now rendered from the markdown via `markdown_pdf_service.convert_markdown_to_pdf`, so the two cannot diverge again |
| N14 | Valuation, institutional ownership and board data empty for every ticker except NVDA | Two CIK resolvers existed. `company_deep_connector.get_cik_for_ticker` kept an in-process cache and refetched `company_tickers.json` on every run; under SEC throttling it returned `None` and the three connectors that resolve through it reported "CIK not found" | Silent and total: a whole valuation section absent, presented as though the company had no retrievable financials. Now delegates to the disk-cached resolver in `sec_edgar_connector` |
| N15 | Throttled runs were indistinguishable from empty ones | Each SEC-backed connector carried its own rate limiter or none, so a single run drove six of them past the shared ten-per-second ceiling. No caller retried on 429, and a throttled fetch returned an error page that parsed to nothing | Sections silently emptied. `sec_http.py` now provides one process-wide limiter with Retry-After-aware backoff, counts abandoned requests, and the Methodology section states the count so a thin run says why it is thin |
| N16 | A departed director counted in the sitting board, with 359 words of proxy front matter as his biography | The text-fallback bio extractor bounded its window only at the next director's name. A director named solely in a farewell passage has no such boundary, so the window ran into the notice of meeting and address block. Separately, anyone drawing fees in the reported year was counted as currently serving | Board reported as 13 rather than 12, and a third of a page of meeting logistics rendered as biography. Bio windows now also stop at proxy furniture, and former directors are detected and reported separately |
| N17 | `None` rendered into tables as a value | 24 call sites used `dict.get(key, "—")` on fields that exist but are frequently null; the default never fires for an explicit `None` | Reached the quality gate as a placeholder failure on JPM. Converted to `dict.get(key) or "—"` for string fields, leaving numeric fields alone so a real zero is not shown as missing |
| N18 | JPM's federal section ran to 6,344 words | Every one of 139 awards was narrated in full | Longest section in the report, adding nothing after the first dozen. Now narrates the 15 largest and tabulates the remainder, with totals reconciling |

**Sections rewritten from data already retrieved but under-rendered:**

| Section | Before | After | What was added |
|---------|--------|-------|----------------|
| Valuation | absent | 933 words | FCF base derivation, discount-rate walk, 10-year forecast with discount factors, EV-to-equity bridge, a WACC × terminal-growth sensitivity grid, and a reverse-DCF stating the growth the traded price implies (52.9% against the model's 25.0%). The grid reproduces the published figure exactly at base assumptions |
| Event Chronology | 684 | 1,353 | Per-event significance derived from the filing's own metadata, earnings 8-Ks tied to the quarter's reported revenue, a filing-mix table explaining what each form reports, and the 131 Form 144 notices that were previously invisible |
| Legal | 287 | 670 | Category rollup with open/resolved split, venue concentration, statutory bases, and explicit reporting of the five regulatory registers that returned nothing — a negative finding rather than a silence |
| Federal Contracting | 132 | 677 | Agency shares (`agency_share_pct` was null upstream, so the table had never rendered), the research-agreement versus procurement split, verbatim award purposes, and the integrity screens |
| Executive Summary | 64 | 298 | A findings engine that ranks conclusions by materiality across every populated section, each carrying its own figures |
| Methodology | 141 | 518 | The four quality gates, per-run source health including throttled-request count, and six stated limitations |

**Result:** NVDA 30 pages / 8,753 words in the PDF at 292 words/page, all 14
sections present, against 27 pages / 3,296 words / 1 section before. Validated
across NVDA, JPM, KO, PLAB and XOM: all pass the quality gate with no
placeholder or sentinel values. Every computed claim reconciles — the
sensitivity replication matches the connector's own output to the cent, the
implied growth rate reprices to the market price exactly, and the legal and
agency totals sum.

### ✅ RESOLVED: DISAGGREGATION, BALANCE SHEET AND PAGE DESIGN (2026-07-31, seventh pass)

**N19 — The three financial statements were collected but only one was published.**
`get_financials` merged the income statement, balance sheet and cash flow into a
single row per period, then appended that row to `income_statement` alone.
`financial_statements["balance_sheet"]` and `["cash_flow"]` were returned as
empty lists on every run for every issuer. The data had been retrieved and
discarded. The rows are now projected onto all three statements, and the
concept map was widened with current assets and liabilities, the investment
tiers, payables, deferred revenue, lease liabilities, purchase obligations,
buyback authorisation and the investing/financing cash flow totals.

**N20 — Cross-concept precedence let a stale tag outrank the issuer's primary
one.** `get_concept_values` preferred the earliest-filed fact for a period, to
stop later comparatives from mislabelling fiscal years. Applied across concept
names, a low-priority tag that happened to be filed earlier beat the tag the
issuer actually uses, so one year of a series could come from a different
concept than the next: NVIDIA's purchase commitments read as a 199% increase
when the two years were tagged differently. The preference now holds only
within a concept, and each figure records which tag supplied it so callers can
refuse to difference across a switch.

**N21 — `get_segment_data` was a stub with no possible data source.** It listed
concept names, did nothing with them, and returned an empty result. It read
companyfacts, which publishes only undimensioned facts, so segment, geographic
and customer data could never have come out of it. Disaggregation now comes
from the rendered statement exhibits (`R*.htm`) attached to the 10-K, which are
what the SEC's own viewer displays and do carry the dimensional breakdowns.

  Report titles vary too much between issuers for name matching alone —
  Apple files everything under "Segment Information and Geographic Data",
  JPMorgan under "Business Segments & Corporate", Exxon under "Disclosures
  about Segments and Related Information". Rather than tune patterns
  indefinitely, each revenue breakdown must reconcile to consolidated revenue
  within 5% before it is published. That rejects Exxon's schedule, which
  combines segment and geography in one table and so sums to twice revenue,
  and it generalises to issuers not yet seen. Where a breakdown cannot be
  reconciled the section is withheld and the Methodology section says so.

**N22 — The PDF was styled as a web dashboard.** Violet gradient table headers,
12mm row padding, left-aligned figures, no cover, no contents, no section
numbering. With little data this read as clean; with 11,000 words it read as
unfinished. The stylesheet was rewritten for print: a dark cover built from the
report's own front matter, a contents page whose page numbers resolve at layout
time through `target-counter`, numbered sections, running heads carrying the
current section via `string-set`, Charter for prose and Helvetica Neue for
data, and hairline-ruled tables at 8.2pt with tabular figures. Figure columns
are detected at build time and right-aligned, total rows are picked out, and
accession and docket numbers are set in monospace so they read as citations.

### ✅ WHAT ACTUALLY EXISTS (Verified against `apps/api/app/connectors/` 2026-07-30)

> ⚠️ The previous version of this table listed `sec_xbrl_connector.py`, `sec_filings_connector.py`, `lda_lobbying_connector.py`, `usaspending_connector.py`, and `fec_connector.py` — **none of those files exist**. The table below is reconciled against the real codebase.

| File | Lines | Key Functions (verified) | Output Reaching Report? |
|------|-------|--------------------------|------------------------|
| `sec_edgar_connector.py` | 633 | `get_company_facts`, `get_insider_transactions` (Form 4), `get_institutional_holders`, `get_investment_portfolio`, `get_full_financial_profile` | ⚠️ Partial — FCF flows ($102.72B matches reference), financial tables do NOT render |
| `proxy_statement_connector.py` | 734 | `extract_executive_compensation`, `get_board_composition`, `_extract_related_party_transactions`, `_extract_beneficial_ownership`, `_extract_say_on_pay` | ❌ Personnel section renders empty despite parser existing |
| `valuation_connector.py` | 768 | `build_dcf_valuation`, `full_valuation_report`, `generate_scenario_analysis`, `get_filing_analysis` (MD&A extraction) | ❌ DCF computes but price=$0 zeroes all outputs |
| `litigation_connector.py` | 813 | `search_federal_cases` (CourtListener), `track_sec_enforcement`, `_search_ftc_proceedings`, `_search_doj_antitrust`, `_search_ptab`, `_search_itc` | ⚠️ Count renders ("20 matters") but no detail |
| `timeline_connector.py` | ~750 | `generate_event_chronology`, `_fetch_8k_events`, `_fetch_insider_transactions` | ⚠️ 10 SEC events render; no news events |
| `risk_register_connector.py` | ~760 | `generate_risk_register`, strategic/operational/financial/legal/ESG extractors | ⚠️ 5 generic risks render, no evidence column |
| `institutional_overlap_connector.py` | ~470 | `get_institutional_overlap`, `compare_competitor_ownership` — depends on yfinance (unavailable) | **P0 as of v3.1** (P-02). Not superseded: `institutional_holdings_connector.py` covers one issuer, this covers overlap across peers. Its yfinance dependency must be repointed at the working 13F-HR path |
| `institutional_holdings_connector.py` | ~200 | `get_institutional_holders`, `find_company_pacs` — 13F-HR information tables from 14 verified major filers | ✅ Renders; 30.6% of NVDA s/o across 9 managers |
| `fpds_connector.py` | 466 | `fetch_fpds_atom`, `fetch_usaspending_full`, `fetch_subcontracts`, `detect_self_dealing` | ❌ Name-based search returns 5 contracts/$50K — needs UEI resolution |
| `opensecrets_connector.py` | 594 | `fetch_fec_contributions`, `fetch_lobbying_summary`, `detect_revolving_door` | ❌ Template data ($100K lobbying) |
| `linkedin_deep_connector.py` | ~460 | Apify-based executive profiles, `detect_family_connections`, `research_board_interlocks` | Phase 3+ — paid source (P-06) |
| `entity_network_connector.py` | ~850 | `discover_family_network`, `build_entity_network`, `analyze_board_interlocks` | **P0 as of v3.1** — free source, unwired and untested (P-01) |
| `deep_research_orchestrator.py` | 817 | `run_deep_intelligence`, `run_comprehensive_intelligence`, `check_connector_availability` | ⚠️ Runs (10.3s, "11 active connectors") but assembly drops most data |
| `premium_pdf_service.py` | — | WeasyPrint PDF generation | ✅ Working (109 KB output) |
| `generate_nvidia_report.py` | — | Report script; None-handling fixed (`dict.get(k) or 0`) | ✅ Runs without crashing |

### ❌ PENDING (Critical Issues — corrected diagnoses)

> Diagnosis correction: most issues are **wiring/rendering bugs**, not missing parsers. Audit each existing connector with a direct test call before writing new code.

> Status reconciled 2026-07-31 (third pass). The table below previously listed
> every row as NOT STARTED; that was stale. Rows are marked against verified
> pipeline output, not intent.

| ID | Issue | Resolution | Priority | Status |
|----|-------|------------|----------|--------|
| P1-01 | Financial tables empty in report | Cause was R2 (XBRL tag migration), not assembly. Income statement, balance sheet, cash flow and TTM all render. | P0 | ✅ DONE |
| P1-02 | No stock price source | `market_data_connector.py`: Finnhub → FMP `/stable` → Alpha Vantage, per-field source URLs. | P0 | ✅ DONE |
| P1-03 | Insider transactions absent | H1/H2. 10b5-1 read from `aff10b5One` plus per-transaction footnote attribution; rendered with a transaction-code breakdown and most-active-seller table. | P0 | ✅ DONE |
| P1-04 | Personnel section empty | H3/H4. Compensation, board roster with fees, committee membership and say-on-pay all render; unretrieved values are stated as such. | P0 | ✅ DONE |
| P1-05 | Federal contracts show $50K | R3. Cause was the award-type group restriction, not UEI. UEI and name searches return identical results — verified. | P1 | ✅ DONE |
| P1-06 | Lobbying shows template $100K | R4. $14.0M with in-house / outside-firm split and named registrants. | P1 | ✅ DONE |
| P1-07 | DCF all zeros | R6, plus H10 (capex silently zero) and the 10-year fade with Blume-adjusted beta. | P0 | ✅ DONE |
| P1-08 | Missing major report sections | 12 sections populate for every ticker tested. Remaining gaps are P1-09 and P1-12. | P0 | ⚠️ PARTIAL |
| P1-09 | 10-K note parsing | `filing_notes_connector.py`. Narrative notes read from the rendered exhibits via `MenuCategory == "Notes"`; yields commitments, contingencies-note legal matters and acquisition terms. | P0 | ✅ DONE |
| P1-10 | Fiscal-basis + derived Q4 | Q4 derived and flagged `DERIVED`; G1/G4 corrected 52/53-week retail calendars. | P0 | ✅ DONE |
| P1-11 | Per-claim source URLs | Carried by market data, 13F holdings, Form 4 rows and lobbying. Not yet universal across every rendered figure. | P0 | ⚠️ PARTIAL |
| P1-12 | 13-sheet xlsx appendix | Requires an openpyxl generator fed from the same data model. | P1 | ❌ NOT STARTED |
| P1-13 | Institutional ownership | H5–H8. 13F-HR information tables from the largest managers, CUSIP-matched, staleness-guarded, value-scale normalised. | P0 | ✅ DONE |
| P1-14 | FEC contributions | H9. Company name → sponsored PAC resolution with validation; Schedule B field names corrected. | P1 | ✅ DONE |

---

### N23 — Commitments understated fivefold by reading the tag alone ✅ RESOLVED

The balance sheet reported NVIDIA's purchase commitments as $22,700M, taken
from `UnrecordedUnconditionalPurchaseObligationBalanceSheetAmount`, and
described that figure as "the clearest quantitative statement of how much
volume management expects to sell". The commitments note puts manufacturing and
supply at $95.2bn, cloud services at $27bn, investment commitments at $11.4bn
and other at $3.4bn — $137,000M against the $22,700M shown. The tag was
correctly reported and materially misleading as the only measure.

`filing_notes_connector.py` reads the narrative notes and the renderer prefers
them, quoting the filed sentence and stating the shortfall against the tag.
Where no note figure is parsed the tag is used and Methodology says so.

### N24 — A holding-company reorganisation emptied an entire report ✅ RESOLVED

Exxon's ticker resolves to CIK 2115436, "ExxonMobil Holdings Corp", created in
a holding-company reorganisation and carrying 26 filings, none of them a 10-K.
Two independent faults compounded it: `get_segment_data` read only the inline
`filings.recent` block, which for a heavy filer need not contain the annual
report at all, and it used the ticker CIK rather than the filer CIK.

`find_latest_filing()` now pages through the `filings.files` overflow, and both
the segment and note parsers take the filer CIK. XOM went from producing
nothing to a passing 12-section report.

### N25 — Contingencies-note matters are a different population from the docket ✅ RESOLVED

Docket search returned 5 matters where NVIDIA is captioned as a party. The
contingencies note describes 5 matters plus management's accrual judgement,
and the two sets are not the same: the note includes regulatory inquiries that
reach no court, and carries the ASC 450 assessment — that liabilities are
reasonably possible but not probable, so nothing is accrued — which no external
source has. §10 now leads with the note and treats the docket as corroboration.

### ✅ RESOLVED: THE P0 NETWORK LAYER (2026-07-31, ninth pass)

All six free-source network capabilities now reach the PDF. Two were broken
connectors, four were not built. Findings below are from live runs, not
fixtures.

**P-02 institutional overlap** read holders through yfinance, which is not
installed, so a complete comparison engine returned zeros for every input. It
also emitted a HIGH-severity flag reading "very high institutional overlap
(100%) — selling pressure may cascade". That 100% is an artifact of polling a
curated list of the largest 13F filers, all of whom hold every large-cap by
construction; the connector was reporting our sampling method as a market
observation, the same defect class as the fabricated say-on-pay flag. Replaced
with allocation skew, which the same filings genuinely support. The validation
is that index trackers cluster at 1.15–1.27x while active managers scatter:
Wellington 21.5x toward AVGO over INTC, Fidelity 4.4x toward NVDA over AMD.

**P-04 related-party** emitted bare dollar amounts captioned "Related party
transaction disclosed in proxy". Rewritten, it finds Huang's daughter and son
at $1,232,000 and $1,320,000, the Huang Foundation's $108.3M GPU compute
agreement with CoreWeave, Walmart's $48.1M to a company owned by McMillon's
brother-in-law, and JPMorgan's $25.6M of Aladdin payments to BlackRock.
Rendering groups by the insider named rather than listing each passage: a proxy
restates the prior two years, so 13 passages for NVIDIA are 3 standing
arrangements, and the grouped view shows the escalation from $370K to $1.23M
that a flat list hides.

**P-01 board interlocks** — built, but not as this plan specified. See the
implementation note in §4C.3: the peer-roster comparison the plan called for
cannot work, because the Clayton Act prohibits the interlock it searches for.

**P-05 beneficial ownership**, **P-07 Exhibit 21** and **P-09 the venture
portfolio** were built from scratch. P-09 reads the ASC 321 rollforward rather
than prose, which is where the disclosure actually lives: NVIDIA's private
holdings went from $3,387M to $22,251M on $17,444M of net additions, so 78% of
the closing balance is capital deployed during the year rather than revaluation.

Three faults caught only by running the basket. Splitting sentences on any full
stop cut "the son of Dr. Shah was approximately $265,000" in half and dropped
every figure. Taking the last heading match ran Walmart and Coca-Cola into the
compensation tables, reporting TSR modifiers as related-party transactions. And
the policy boilerplate restating the rule's own $120,000 threshold reads exactly
like a transaction — that one would have shipped a fake finding to every issuer.

Coverage is honest rather than uniform: Photronics files no Exhibit 21, and
JPMorgan and Walmart disclose no non-marketable rollforward. Those sections are
omitted with the reason stated instead of padded.

**Rendering caught a defect the connectors could not see.** EDGAR stores an
individual reporting owner surname-first and in capitals, so the section
initially read "COXE TENCH", "SEAWELL A BROOKE". The proxy writes the same
people correctly, so names are now matched against the board roster and the
compensation table and the proxy's spelling is preferred; failing a match the
name is title-cased and the leading surname moved to the end. Corporate filers
are excluded from the reordering, since a ten percent owner is often a firm and
"BLACKROCK INC" must not become "Inc Blackrock".

**Verified state after the ninth pass.** NVDA 14,539 words / 17 sections / 37
PDF pages, 15 of 15 sources, zero failures. The new material occupies §5
Corporate Structure, §6.2 Private company holdings, §8.5 Related-party
transactions, §8.6 Board interlocks, §10.1 Five percent holders and §10.2
Common ownership. All six appear in the table of contents with correct section
numbering and page references.

---

## 📊 GAP ANALYSIS: Current Output vs Reference Report

### Generated Report (2026-07-31, eighth pass)
- **File**: `/apps/reports/NVIDIA_CORP_Intelligence_Report_20260731_060022.pdf`
- **Length**: 12,728 words of markdown across 16 sections, rendering to 33 PDF
  pages at 386 words/page
- **Source health**: 13 of 13 succeed, zero failures
- **Cross-ticker**: XOM now passes at 5,861 / 12 having previously produced
  nothing — see N24. AAPL, JPM, WMT and KO pass with no placeholder values
- **Disaggregation coverage**: NVDA, AAPL, WMT and KO reconcile and publish;
  JPM, XOM, PLAB and MSFT do not reconcile and are withheld with the reason
  stated in Methodology. Coverage is the honest number, not the optimistic one
- **Accuracy**: all seven headline financials, NEO compensation, federal awards
  and lobbying totals match the reference exactly; insider coverage exceeds it.
  The valuation's sensitivity grid reproduces the connector's own intrinsic
  value to the cent, and the implied-growth inversion reprices to the traded
  price exactly

### Reference Report (Target)
- **File**: `/reports/NVIDIA Corporation — Intelligence Report.pdf`
- **Length**: 42 pages
- **Data Density**: 95%+
- **Sections**: 16 fully populated

### Section-by-Section Comparison

Measured 2026-07-31 (eighth pass) on the NVDA run, word counts per section,
against the reference's 19,591 words across 16 sections. Ours: 12,728 words,
16 sections.

| Reference section | Ref words | Ours | Status |
|---|---|---|---|
| 4. Segment, Geographic, Customer | 427 | 613 | ✅ Exceeds — revenue by segment, market and region, long-lived assets by region, concentration disclosures, each reconciled to consolidated revenue |
| 3. Financial Performance | 550 | 324 | ✅ At parity on substance — all seven headline figures match the reference exactly |
| 5. Key Personnel | 4,075 | 3,364 | ✅ At parity — per-director dossiers with age, tenure, committees, biography and that person's Form 4 record |
| 6. Balance Sheet and Capital Allocation | 1,338 | 1,318 | ✅ At parity — liquidity, leverage against the note-sourced $137,000M commitment position, working-capital cycle, five-year capital allocation, returns on capital, and the Groq asset acquisition |
| 2. Investment View + 11. Valuation | 1,406 | 1,066 | ✅ Near parity — full derivation, sensitivity grid, and a reverse-DCF the reference does not attempt |
| 7. Federal Contracting | 882 | 677 | ✅ Near parity — $46.0M matches the reference exactly |
| 10. Legal and Regulatory | 2,413 | 1,989 | ✅ Near parity — 5 docket party matters plus the 5 described in the contingencies note, with management's ASC 450 assessment |
| 0/14. Scope and Methodology | 1,202 | 568 | ⚠️ Partial — gates, source health, throttle count and limitations all stated |
| 9. Event Chronology | 2,698 | 1,433 | ⚠️ Partial — each event carries derived significance; the reference adds media-sourced events we do not retrieve |
| 1. Executive Summary | 659 | 298 | ⚠️ Partial — ranked findings engine, not yet drawing on every populated section |
| 13. Risk Register | 477 | 283 | ⚠️ Partial — renders, but risks are not yet evidence-linked to filings |
| 8. Lobbying and Political | 631 | 200 | ⚠️ Partial — $14.0M matches the reference exactly |
| 12. Government Action Precedent Library | 2,312 | 0 | ❌ Missing — research synthesis, no data feed |
| 15. Appendix Index | 187 | 0 | ❌ Missing — XLSX workbook (P1-12) |
| — | — | 297 | ➕ Insider Activity — beyond the reference: 1,011 transactions vs its 801 |
| — | — | 171 | ➕ Institutional Ownership — 13F-HR information tables |
| — | — | 31 | ➕ Cross-Reference Findings |

The remaining gap is roughly 4,800 words, of which 2,312 is §12 and has no data
feed behind it. Excluding §12, 2,526 words separate the report from the
reference, spread across six sections rather than concentrated in any one.

§12 Government Action Precedent Library (-2,312) was attempted through
peer-name docket search and the results were unusable: searching AMD returned
`Amgen Inc v. Celltrion USA`, `State v. Bivings` and `In re: Zantac`, none
involving the company. The section is omitted, and Methodology states why,
rather than filling it with weak matches. It needs a curated enforcement feed
keyed to industry — SEC administrative proceedings and litigation releases, DOJ
and FTC actions — which is a data acquisition problem, not a rendering one.

§9 Event Chronology (-1,265) has a genuine ceiling. We hold 317 filing-derived
events; the reference quotes congressional testimony and press reporting that
appears in no filing. Closing it needs a news or transcript feed.

§1 Executive Summary (-361), §14 Methodology (-130) and §13 Risk Register
(-194) need no new data and are the cheapest remaining work.

§4, §6 and §10 are closed. §6 and §10 needed the note parser (P1-09, N23, N25);
§4 turned out to need no new source at all, coming from the rendered exhibits
the filing already carries (N21).

### Critical Data Sources Not Flowing (corrected)

| Data Point | Expected Source | Actual State (verified) | Fix Required |
|------------|-----------------|------------------------|--------------|
| Stock Price | Perplexity Finance / Alpha Vantage / Finnhub | yfinance unavailable, no fallback | Add alternative API — unblocks DCF |
| Revenue/Earnings | SEC XBRL companyfacts | **Retrieved but dropped** — FCF ($102.72B) matches reference exactly, tables never render | Debug orchestrator→template assembly |
| Executive Bios | DEF 14A proxy statements | Parser EXISTS (`proxy_statement_connector.py`, 734 lines) | Verify output + wire to template |
| Form 4 Transactions | SEC EDGAR Form 4 XML | `get_insider_transactions` EXISTS in `sec_edgar_connector.py` | Verify output, confirm 10b5-1 detection, wire to template |
| Insider 10b5-1 Plans | Form 4 `aff10b5One` checkbox | Unverified whether existing parser reads it | Confirm/add in existing parser |
| Federal Contracts | USASpending.gov | Name-based search → 5 contracts/$50K | Resolve UEIs via recipient endpoint, filter by UEI, add subawards |
| Lobbying Details | Senate LDA API | Returns template $100K | Debug API call in `opensecrets_connector.py` |
| Litigation Detail | CourtListener + SEC 10-K | Connector EXISTS (813 lines), only a count renders | Wire full docket to template |
| Segment / geographic / customer revenue | 10-K R-file exhibits | ✅ **Resolved (N21)** — parsed from rendered exhibits, reconciled to consolidated revenue before publishing | — |
| Balance sheet and capital allocation | SEC XBRL companyfacts | ✅ **Resolved (N19)** — was retrieved then discarded; now published with derived liquidity, leverage and working-capital measures | — |
| Purchase commitments | `UnrecordedUnconditionalPurchaseObligationBalanceSheetAmount` | ✅ **Resolved** — $22.7B for NVIDIA, off balance sheet | — |
| Legal contingencies (10-K Note 21) | 10-K R-file exhibits (notes) | **No parser exists** — the remaining half of the §9/§10 gap | Extend the R-file parser to the contingencies note |
| Government enforcement precedent | Curated SEC/DOJ/FTC feed | **No usable source** — peer docket search returns unrelated matters | Acquire an enforcement feed keyed to SIC |
| Consensus / Analyst Targets | Perplexity Finance or similar | No source | Add for §2/§11 (22 analysts, targets) |

---

## 🎯 JAMES'S COMPLETE REQUIREMENTS

### Must-Have Features (From Discussions)

1. **Deep Personnel Research**
   - Full executive and board member dossiers
   - Career timelines with key events
   - Family member business connections
   - Other board seats and potential conflicts
   - Insider trading patterns (10b5-1 plan detection)

2. **Complete Financial Picture**
   - DCF valuation with Bear/Base/Bull scenarios
   - Full income statement, balance sheet, cash flow
   - Key ratios and trend analysis
   - Comparison to industry benchmarks

3. **Government/Political Intelligence**
   - ALL federal contracts (not just summary)
   - Lobbying spend by quarter with firm breakdown
   - Political donations (PAC + individual)
   - Revolving door personnel tracking
   - Contract-to-lobbying temporal correlation

4. **Relationship Mapping**
   - Board interlock network graphs
   - Shared investor analysis (13F overlap)
   - Supply chain dependencies
   - Customer concentration risk
   - Competitor shared investors

5. **Risk & Red Flags**
   - Self-dealing detection engine
   - Related party transaction flagging
   - Litigation pipeline with exposure estimates
   - Regulatory investigation tracking
   - Government action precedent library

6. **Report Quality Standards**
   - 80-120 pages minimum
   - 95%+ data density (no placeholder text)
   - Full source citations for every claim
   - 13-sheet appendix workbook
   - Professional PDF formatting

---

## 1. CURRENT STATE ANALYSIS (Updated 2026-07-30)

### What the Current Report HAS (Working)

| Section | Status | Data Source | Quality | Notes |
|---------|--------|-------------|---------|-------|
| Report Structure | ✅ Working | Markdown template | A | Generates without crashing |
| PDF Generation | ✅ Working | WeasyPrint | B+ | 109 KB PDF output |
| Event Chronology | ⚠️ Partial | SEC 8-K filings | C | Has 10 events listed |
| Risk Register | ⚠️ Partial | Template + inference | D | Shows 5 risks, no evidence |
| Executive Summary | ❌ Broken | No data flowing | F | Shows "0 data sources" |
| Investment View | ❌ Broken | SEC XBRL | F | All $0.00 values |
| Financial Performance | ❌ Empty | SEC XBRL | F | No data populated |
| Key Personnel | ❌ Empty | DEF 14A (not parsed) | F | Section completely empty |
| Institutional Ownership | ❌ Empty | 13F (not implemented) | F | Section empty |
| Government Contracts | ⚠️ Broken | USASpending.gov | D | Only $50K (should be millions) |
| Lobbying Activity | ⚠️ Broken | LDA API | D | Template data, $100K shown |
| Legal & Regulatory | ⚠️ Partial | Template | D | "20 matters" but no detail |

### What the Current Report is MISSING (James's Requirements)

| Requirement | Current State | Gap Level |
|-------------|---------------|-----------|
| Family member analysis | None | CRITICAL |
| Employee deep research | AI placeholders only | CRITICAL |
| Board member other investments | None | CRITICAL |
| Advisor networks | None | HIGH |
| Cap table with ALL investors | Basic institutional only | CRITICAL |
| Competitor shared investors | None | CRITICAL |
| All government contracts (full values) | Only 5 contracts, $50K | HIGH |
| Self-dealing detection | Framework only, no data | CRITICAL |
| Valuation timeline with events | Template only | HIGH |
| M&A and venture activity | None | HIGH |
| LinkedIn automation | Not implemented | CRITICAL |
| Political connections (Trump-style mapping) | None | CRITICAL |
| Cross-API correlation engine | None | CRITICAL |

---

## 2. TARGET STATE: JAMES'S VISION

### The "Deep Intelligence Report" Must Include:

```
┌─────────────────────────────────────────────────────────────────┐
│                    DEEP INTELLIGENCE DOSSIER                     │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 1: ENTITY CORE                                            │
│  ├── Corporate Profile (financials, structure, history)         │
│  ├── Complete Cap Table (all investors, % ownership, vehicles)  │
│  └── Subsidiary Tree (all entities, jurisdictions)              │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 2: PEOPLE INTELLIGENCE                                    │
│  ├── Executive Dossiers (career, education, family, net worth)  │
│  ├── Board Member Deep Dive (other boards, investments)         │
│  ├── Key Employee Profiles (LinkedIn enrichment)                │
│  ├── Advisor Networks (formal + informal relationships)         │
│  └── Family Connections (spouses, children, business ties)      │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 3: MONEY FLOWS                                            │
│  ├── All Government Contracts (full breakdown, values)          │
│  ├── Lobbying Expenditure Timeline                              │
│  ├── Political Donations (PAC, individual, bundling)            │
│  ├── M&A Activity (acquirer + target, all deals)                │
│  ├── Venture/Strategic Investments                              │
│  └── Self-Dealing Analysis (related party transactions)         │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 4: NETWORK INTELLIGENCE                                   │
│  ├── Investor Overlap with Competitors                          │
│  ├── Board Interlock Network (visual + analysis)                │
│  ├── Supply Chain Mapping                                       │
│  ├── Customer Concentration                                     │
│  └── Hidden Relationship Detection                              │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 5: COMPETITIVE INTELLIGENCE                               │
│  ├── Competitor Deep Profiles                                   │
│  ├── Shared Investor Analysis                                   │
│  ├── Market Share Comparison                                    │
│  ├── Infrastructure Comparison                                  │
│  └── Patent/IP Landscape                                        │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 6: POLITICAL/REGULATORY                                   │
│  ├── Revolving Door Personnel                                   │
│  ├── Policy Influence Mapping                                   │
│  ├── Regulatory Risk Assessment                                 │
│  ├── Foreign Agent Registrations (FARA)                         │
│  └── Sanctions/Export Control Exposure                          │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 7: RISK & RED FLAGS                                       │
│  ├── Self-Dealing Indicators                                    │
│  ├── Governance Red Flags                                       │
│  ├── Litigation Pipeline                                        │
│  ├── Regulatory Investigations                                  │
│  └── Reputational Risk Score                                    │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 8: CORRELATION ENGINE                                     │
│  ├── Cross-Entity Relationship Graph                            │
│  ├── Temporal Event Correlation                                 │
│  ├── Anomaly Detection                                          │
│  └── Predictive Intelligence Signals                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. ARCHITECTURE: DEEP RESEARCH AGENT SYSTEM

### 3.1 Multi-Agent Research Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                      ORCHESTRATION LAYER                              │
│                   (Deep Intelligence Coordinator)                     │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────────┐
        │                       │                           │
        ▼                       ▼                           ▼
┌───────────────┐       ┌───────────────┐       ┌───────────────────┐
│  ENTITY       │       │  PEOPLE       │       │  MONEY FLOW       │
│  RESEARCH     │       │  RESEARCH     │       │  RESEARCH         │
│  AGENT        │       │  AGENT        │       │  AGENT            │
├───────────────┤       ├───────────────┤       ├───────────────────┤
│ • SEC EDGAR   │       │ • LinkedIn    │       │ • USASpending     │
│ • OpenCorp    │       │ • Apollo.io   │       │ • FPDS            │
│ • GLEIF       │       │ • Pipl/Clearbit│      │ • FEC             │
│ • State Regs  │       │ • BoardEx     │       │ • LDA             │
│ • Crunchbase  │       │ • RelSci      │       │ • CapIQ/PitchBook │
└───────────────┘       └───────────────┘       └───────────────────┘
        │                       │                           │
        └───────────────────────┼───────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────────┐
        │                       │                           │
        ▼                       ▼                           ▼
┌───────────────┐       ┌───────────────┐       ┌───────────────────┐
│  NETWORK      │       │  COMPETITIVE  │       │  POLITICAL        │
│  MAPPING      │       │  INTEL        │       │  INTEL            │
│  AGENT        │       │  AGENT        │       │  AGENT            │
├───────────────┤       ├───────────────┤       ├───────────────────┤
│ • 13F overlap │       │ • Competitor  │       │ • FEC             │
│ • Board links │       │   profiles    │       │ • OpenSecrets     │
│ • Family maps │       │ • Patent data │       │ • FARA            │
│ • Co-invest   │       │ • Market data │       │ • Revolving Door  │
│ • Supply chain│       │ • Infra comp  │       │ • Policy tracking │
└───────────────┘       └───────────────┘       └───────────────────┘
                                │
                                ▼
                ┌───────────────────────────────┐
                │      CORRELATION ENGINE       │
                ├───────────────────────────────┤
                │ • Cross-reference all data    │
                │ • Detect hidden relationships │
                │ • Flag anomalies & red flags  │
                │ • Build relationship graph    │
                │ • Generate intelligence brief │
                └───────────────────────────────┘
                                │
                                ▼
                ┌───────────────────────────────┐
                │    DEEP INTELLIGENCE PDF      │
                │    (50-100+ pages)            │
                └───────────────────────────────┘
```

### 3.2 New Data Connectors Required

> **Priority corrected 2026-07-31.** This table previously marked LinkedIn,
> PitchBook and Crunchbase as P0 while §5.1 marked the same sources Phase 3+
> and "must not block reference parity". Both could not be true. The rule now
> is a single one: **a connector is P0 if its source is free and public.**
> Paid vendors are Phase 3+ regardless of how valuable the data is.

| Connector | Purpose | Data Type | Cost | Priority |
|-----------|---------|-----------|------|----------|
| `entity_network_connector.py` | Board interlocks, family and entity networks | Director networks across peer CIKs | Free — DEF 14A | **P0** |
| `institutional_overlap_connector.py` | Managers holding this issuer and its peers | Cross-company 13F holdings | Free — 13F-HR | **P0** |
| `exhibit21_parser` (in `filing_notes_connector.py`) | Subsidiary and affiliate tree | Entity names + jurisdictions | Free — 10-K Ex. 21 | **P0** |
| Item 404 renderer (parser exists) | Related-party transactions | Self-dealing, insider agreements | Free — DEF 14A | **P0** |
| `beneficial_ownership_connector.py` | Holders above 5%, activist stakes | SC 13D/G | Free — EDGAR | **P0** |
| `opensecrets_connector.py` | Political money tracking | Donations, bundling, PACs | Free | P0 |
| `fpds_connector.py` | Federal contracts (full) | All contract data, modifications | Free | P0 |
| `patent_connector.py` | USPTO/WIPO | Patent filings, citations | Free | P1 |
| `supply_chain_connector.py` | Supplier/customer mapping | Supply chain relationships | Free — 10-K | P1 |
| `linkedin_connector.py` | Personnel research via Apify | Profiles, connections, career history | ~$0.05/profile | Phase 3+ |
| `pitchbook_connector.py` | VC/PE deals, valuations | Funding rounds, **co-investors** | $20K+/yr | Phase 3+ |
| `crunchbase_connector.py` | Startup/investment data | Funding, acquisitions, people | $6K/yr | Phase 3+ |
| `boardex_connector.py` | Board interlocks | Director networks, compensation | $50K+/yr | Phase 3+ |
| `relsci_connector.py` | Relationship intelligence | Family, education, affiliations | $25K+/yr | Phase 3+ |

### 3.3 New Research Agents

```python
# agents/deep_research/
├── entity_research_agent.py      # Corporate structure deep dive
├── people_research_agent.py      # LinkedIn + Apollo + family research
├── money_flow_agent.py           # Contracts, investments, donations
├── network_mapping_agent.py      # Relationship graphs, interlocks
├── competitive_intel_agent.py    # Competitor analysis + overlap
├── political_intel_agent.py      # Political connections, lobbying
├── correlation_engine.py         # Cross-reference + anomaly detection
└── deep_intelligence_orchestrator.py  # Master coordinator
```

---

## 4. NEW REPORT SECTIONS TO ADD

### 4.1 Enhanced Sections (Layer 2: People Intelligence)

```markdown
## 5. Executive Leadership Deep Dossiers

### JENSEN HUANG — CEO & Co-Founder

#### Professional Profile
- **Current Role**: CEO & Co-Founder, NVIDIA Corporation (1993-Present)
- **Previous**: Director of Microprocessor Division, AMD (1985-1993)
- **Education**: M.S. Electrical Engineering, Stanford (1992); B.S. Oregon State (1984)

#### Career Timeline
| Year | Event | Significance |
|------|-------|--------------|
| 1993 | Co-founded NVIDIA | With Chris Malachowsky & Curtis Priem |
| 1999 | IPO | NVIDIA goes public on NASDAQ |
| 2006 | CUDA Launch | Pivoted company to parallel computing |
| 2020 | ARM Acquisition Announced | $40B deal (later collapsed) |
| 2023 | AI Boom | Company valuation exceeds $1T |

#### Board Seats & Affiliations
| Organization | Role | Since | Other Connections |
|--------------|------|-------|-------------------|
| TSMC | Board Member | 20XX | Supplier relationship conflict? |
| Stanford HAI | Advisory Board | 20XX | Academic/research ties |
| MIT Media Lab | Board Member | 20XX | Innovation network |

#### Family Connections
- **Spouse**: Lori Huang (née Mills)
- **Children**: [Names], [Business involvement if any]
- **Extended Family Business Ties**: [Any documented business relationships]

#### Financial Entanglements
| Type | Details | Red Flag Level |
|------|---------|----------------|
| Stock Ownership | X% of NVDA (~$XX billion) | LOW - Founder expected |
| TSMC Board | Manufacturing dependency | MEDIUM - Conflict of interest |
| 10b5-1 Plans | Scheduled selling activity | MONITOR |

#### Other Investments & Vehicles
| Entity | Relationship | Investment Size |
|--------|--------------|-----------------|
| [VC Fund X] | LP | $XXM |
| [Startup Y] | Angel Investor | $XXM |
| [Family Office] | Beneficial Owner | N/A |

#### Network Graph
[Visual: Force-directed graph showing Huang's connections to other executives,
board members, investors, and political figures]
```

### 4.2 Enhanced Sections (Layer 3: Money Flows)

```markdown
## 11. Government Contracts Deep Dive

### 11.1 Complete Contract Portfolio

**Total Federal Obligations**: $XXX,XXX,XXX (FY2015-2026)

#### Contract Distribution by Agency

| Agency | Total Value | # Contracts | % of Portfolio | Trend |
|--------|-------------|-------------|----------------|-------|
| Department of Defense | $XXX M | XX | XX% | ↑ Growing |
| Department of Energy | $XX M | XX | XX% | → Stable |
| NASA | $XX M | XX | XX% | ↑ Growing |
| HHS/NIH | $XX M | XX | XX% | → Stable |
| Commerce | $XX K | X | <1% | → Stable |

#### Top 10 Contracts by Value

| Contract ID | Agency | Description | Value | Period | Type |
|-------------|--------|-------------|-------|--------|------|
| XXXX-XX-X-XXXX | DoD | AI/ML computing systems | $XX M | 2024-2029 | IDIQ |
| XXXX-XX-X-XXXX | DOE | HPC infrastructure | $XX M | 2023-2028 | FFP |
| ... | ... | ... | ... | ... | ... |

### 11.2 Self-Dealing & Related Party Analysis

#### Red Flag Detection Matrix

| Indicator | Finding | Risk Level | Evidence |
|-----------|---------|------------|----------|
| Subcontractor to insider entity | None detected | LOW | Reviewed all sub-K data |
| Contract officer connections | [Person X] previously at NVDA | MEDIUM | Revolving door hire |
| Lobbying ↔ Award timing | Q2 2024 lobbying spike → Q3 award | INVESTIGATE | Temporal correlation |
| Family-owned vendor | None detected | LOW | Cross-referenced ownership |
| Non-competitive awards | 2 sole-source contracts | MEDIUM | Review justification |

#### Contract-Lobbying Correlation Timeline

[Visual: Timeline showing lobbying spend by quarter overlaid with contract award dates]

#### Contracting Officer Network
[Visual: Graph showing government personnel who have awarded contracts to NVIDIA
and their career movements]
```

### 4.3 Enhanced Sections (Layer 4: Network Intelligence)

```markdown
## 9. Competitor Network Analysis

### 9.1 Shared Investor Overlap

**Methodology**: Cross-referenced Q2 2026 13F filings for top 50 institutional holders

| Investor | NVDA Position | AMD Position | INTC Position | QCOM Position |
|----------|--------------|--------------|---------------|---------------|
| Vanguard | $XX B (X%) | $X B (X%) | $X B (X%) | $X B (X%) |
| BlackRock | $XX B (X%) | $X B (X%) | $X B (X%) | $X B (X%) |
| State Street | $XX B (X%) | $X B (X%) | $X B (X%) | $X B (X%) |
| Fidelity | $XX B (X%) | $X B (X%) | $X B (X%) | $X B (X%) |
| ... | ... | ... | ... | ... |

**Overlap Score**: 87% (highly correlated institutional ownership)

**Implication**: High overlap means selling pressure in one company may cascade to peers

### 9.2 Board Interlock Network

| Director | NVDA Role | Other Boards | Potential Conflicts |
|----------|-----------|--------------|---------------------|
| [Name] | Independent | Apple, Microsoft | Customer/partner |
| [Name] | Independent | ARM Holdings | Former acq. target |
| [Name] | Audit Chair | Goldman Sachs | Banking relationship |

[Visual: Force-directed graph showing board connections across semiconductor industry]

### 9.3 Shared Venture Investments

| Portfolio Company | NVDA Investment | Competitor Investor | Investment Round |
|-------------------|-----------------|---------------------|------------------|
| [AI Startup X] | $XX M | AMD, Intel | Series B |
| [Chip Design Y] | $XX M | Qualcomm | Series A |
| ... | ... | ... | ... |

**Implication**: Co-investment patterns may indicate sector trends or future M&A targets
```

### 4.4 Enhanced Sections (Layer 6: Political Intelligence)

```markdown
## 12. Political & Regulatory Intelligence

### 12.1 Political Donation Mapping (FEC + OpenSecrets)

#### Corporate PAC Activity

| Cycle | Total Raised | Total Spent | D % | R % | Top Recipients |
|-------|--------------|-------------|-----|-----|----------------|
| 2024 | $X.X M | $X.X M | XX% | XX% | [Names] |
| 2022 | $X.X M | $X.X M | XX% | XX% | [Names] |
| 2020 | $X.X M | $X.X M | XX% | XX% | [Names] |

#### Executive Individual Contributions

| Executive | Total (2020-2026) | Top Recipients | Party Split |
|-----------|-------------------|----------------|-------------|
| Jensen Huang | $XXX,XXX | [Names] | XX% D / XX% R |
| [CFO] | $XXX,XXX | [Names] | XX% D / XX% R |
| [Other] | $XXX,XXX | [Names] | XX% D / XX% R |

### 12.2 Lobbying Deep Dive

#### Quarterly Lobbying Spend (2020-2026)

[Visual: Bar chart showing lobbying spend by quarter with annotations for key events]

#### Lobbying Firm Network

| Firm | Engagement Period | Total Spend | Key Issues | Former Gov Officials |
|------|-------------------|-------------|------------|----------------------|
| Tiber Creek Group | 2020-Present | $X.X M | AI regulation, export controls | [Names] |
| The Nickles Group | 2021-Present | $XXX K | Tax policy | [Names] |
| [Other firms] | ... | ... | ... | ... |

#### Issue-Specific Lobbying

| Issue | Spend (2024-26) | Bills Targeted | Agency Contacts |
|-------|-----------------|----------------|-----------------|
| AI/ML Regulation | $XXX K | HR XXXX, S.XXXX | Commerce, OSTP |
| Export Controls (China) | $XXX K | EAR amendments | BIS, Commerce |
| R&D Tax Credit | $XXX K | Tax reform | Treasury, Ways & Means |
| Antitrust | $XXX K | Big Tech bills | DOJ, FTC |

### 12.3 Revolving Door Personnel

| Person | NVIDIA Role | Previous Gov Role | Hiring Date | Concern Level |
|--------|-------------|-------------------|-------------|---------------|
| [Name] | VP Gov Affairs | Commerce Dept., Deputy Asst Sec | 2023 | HIGH |
| [Name] | Lobbyist (contract) | Senate Commerce staffer | 2022 | MEDIUM |
| [Name] | Policy Director | USTR, Trade Rep staff | 2024 | HIGH |

### 12.4 Regulatory Risk Matrix

| Regulatory Area | Current Exposure | Trend | Key Triggers |
|-----------------|------------------|-------|--------------|
| Export Controls (China) | HIGH | ↑ Increasing | New chip restrictions expected |
| Antitrust | MEDIUM | → Stable | CUDA lock-in scrutiny |
| AI Safety Regulation | MEDIUM | ↑ Increasing | EU AI Act, potential US rules |
| Securities/Disclosure | LOW | → Stable | Standard public company |
```

---

---

## 4A. WHAT REMAINS — CONSOLIDATED VIEW (after the eleventh pass)

Every free-source P0 item is shipped. Charts, the full N-series scaffold,
D-01 price history, and the cheap text-parity thickenings are in the PDF.
What is left is correlations (event-study code), B-06 XLSX, and blocked
sourcing decisions.

**1. Charts — ✅ shipped.** `chart_service.py` draws every V-series figure
the data supports (PNG at 200 dpi). NVDA embeds 12 figures / ~44 pages /
~900 KB including V-11 (insider disposals on Yahoo daily bars). Missing
series omit the figure; base64 SVG is never used (WeasyPrint blank-page bug).

**2. N-series — ✅ scaffold shipped (N-01..N-07).** `_network_trends` runs
all seven comparisons; empty legs are omitted. On NVDA, N-02 (allocation
skew) and N-06 (Israel/Singapore vs disclosed revenue geos) populate;
N-01/N-03/N-04/N-05/N-07 correctly return empty because the filings do not
support a match. Named ASC 321 holdings would unlock N-03/N-04 further.

**3. Text parity — B-01/B-02/B-03/B-04/B-05 thickened; B-06 remains.**
Methodology now states chart provenance, price-history source, network
rules and the n<12 correlation suppression. Chronology adds filing-intensity
and mix analysis. B-06 (13-sheet XLSX appendix) is still open.

**4. Genuinely blocked / next engineering.** D-01 is built (Finnhub → Alpha
Vantage → Yahoo). V-11 is live. Correlations still need the event-study
code itself (and D-02 for C-03/C-04):

| Blocked item | Blocked on | Nature |
|--------------|-----------|--------|
| C-01, C-02, C-05 | Event-study code (bars available via D-01) | Engineering |
| C-03, C-04 | D-02 quarterly XBRL from 10-Q facts | Takes financial n from 5 to 20+ |
| B-07, P-10 | Curated enforcement feed; paid VC database | Purchasing decision |

---

## 4B. OPEN BACKLOG — REFERENCE PARITY (tracked)

Measured against the eighth pass. Ordered cheapest first. Items here need no
decision, only work.

| ID | Item | Gap | Needs new data? | Priority | Status |
|----|------|-----|-----------------|----------|--------|
| B-01 | §1 Executive Summary — findings engine does not draw on every populated section | −361 words | No | P1 | ✅ Shipped — related-party, interlocks, venture, skew, N-01/N-05/N-06/N-07 all feed findings |
| B-02 | §13 Risk Register — entries not evidence-linked to the filing that raises them | −194 words | No | P1 | ✅ Shipped — evidence-linked entries lead; boilerplate demoted to "General assessments" |
| B-03 | §14 Methodology — quality gates and per-domain provenance stated, prose thin | −130 words | No | P2 | ✅ Shipped — chart provenance, price-history source, network rules, n<12 suppression |
| B-04 | §8 Lobbying — totals exact ($14.0M / 54 filings), surrounding analysis absent | −431 words | No | P2 | ✅ Shipped — trajectory, in-house/outside split, registrant concentration, issue-code caveats |
| B-05 | §9 Event Chronology — 317 filing-derived events; reference cites testimony and press | −1,265 words | Yes — news/transcript feed | P2 | ◐ Partial — filing-intensity, form mix and highlights added; news/transcript feed still absent |
| B-06 | §15 Appendix — 13-sheet XLSX workbook (P1-12) | −187 words | No — openpyxl off the same data model | P2 | ☐ Open |
| B-07 | §12 Government Action Precedent Library | −2,312 words | Yes — curated enforcement feed | P3 | ☐ Blocked — purchasing decision |

Five of the seven are closed and B-05 is partially closed from filing-derived
data alone. B-06 is the only remaining item needing no new source. B-07 has no
path from any source currently reachable: peer-name docket search for AMD
returned `Amgen Inc v. Celltrion USA`, `State v. Bivings` and `In re: Zantac`.
It stays omitted with the reason stated in Methodology.

---

## 4C. JAMES'S PHASE 2 REQUIREMENTS (2026-07-31)

Three additions requested beyond reference parity: **data visualisation**,
**deep analysis and correlations**, and **private-investigator-style research**.
Reference parity is a text target; these are not in the reference report at all,
so they extend past it rather than closing a gap.

The specifications below are written against what the pipeline actually holds
today. Where an analysis is not statistically defensible on current data, the
data collection needed to make it defensible is named rather than the analysis
being specified anyway.

### 4C.1 Data visualisation (V-series)

**Status as of the tenth pass: shipped.** Eleven V-series charts render into
the PDF for NVDA (composition, commitments, venture rollforward, capital
allocation, DCF heatmap, interlock network, insider disposals, institutional
concentration, federal obligations, filing cadence, revenue/margin). Figures
are numbered, kept with their captions, and omitted when the data will not
support them. V-11 and V-12 appear when D-01 bars / a large enough Exhibit 21
are present.

**Rendering path — verified 2026-07-31.** WeasyPrint 68.1 renders a matplotlib
PNG embedded as a `data:` URI. It renders `data:image/svg+xml;utf8,` as well.
It silently produces a blank page for base64-encoded SVG — a chart pipeline
built that way emits no error and no chart, so PNG at 300 dpi is the specified
path and any SVG work must use the utf8 form.

matplotlib 3.10.9, numpy 2.4.6, scipy 1.16.1, pandas 2.2.3 and networkx 3.5 are
all installed. No new dependency is required.

Charts must inherit the report's existing palette — navy `#1a2b47`, ink, muted
grey, amber accent — and Helvetica Neue at the tabular-figure sizes already set
in `REPORT_CSS`. A chart that does not match the surrounding typography reads as
imported clip art and undoes the work of N22.

| ID | Chart | Section | Data held today? |
|----|-------|---------|------------------|
| V-01 | Revenue and margin trend, 5 fiscal years, dual axis | §3 | Yes |
| V-02 | Capital allocation waterfall — OCF → capex → FCF → buybacks → dividends → retained | §5 | Yes |
| V-03 | Segment and geographic composition, stacked horizontal bar | §4 | Yes |
| V-04 | DCF sensitivity heatmap, WACC × terminal growth | §6 | Yes — computed grid |
| V-05 | Commitment maturity ladder by fiscal year | §5 | Yes — from the notes parser |
| V-06 | Insider disposal volume by month, 10b5-1 versus discretionary | §8 | Yes — 1,011 dated transactions |
| V-07 | Filing cadence over time by form type | §13 | Yes — 317 dated events |
| V-08 | Institutional position concentration | §9 | Yes — 9 managers |
| V-09 | Federal obligations by agency and year | §10 | Partial — awards carry no action date; needs the date field added |
| V-10 | Board interlock network graph | §8 | **Yes as of the ninth pass** — P-01 supplies the edges |
| V-11 | Insider transactions overlaid on price history | §9 | No — needs D-01 |
| V-12 | Subsidiary count by jurisdiction | §5 | **Yes as of the ninth pass** — P-07 |
| V-13 | Private-portfolio rollforward waterfall | §6 | **Yes as of the ninth pass** — P-09 |

Every chart must also be reachable as a table. A figure that cannot be read as
numbers fails the same provenance standard the rest of the report is held to.

### 4C.2 Deep analysis and correlations (C-series)

**The binding constraint is sample size, not capability.** The pipeline holds 5
annual periods, 0 quarterly periods, 7 federal awards, 9 institutional managers
and a single 13F snapshot. A Pearson correlation on n=5 is not evidence, and an
engine that emits one will manufacture findings — the precise failure mode this
project has spent eight passes removing. Two data additions change that, and
they are prerequisites rather than nice-to-haves.

| ID | Prerequisite | Effect |
|----|--------------|--------|
| D-01 | Daily or weekly price history (Finnhub / Alpha Vantage candles) | Unlocks C-01, C-02, C-05 and V-11. Single highest-value addition |
| D-02 | Quarterly XBRL series from 10-Q facts | Takes financial n from 5 to 20+, making C-03 and C-04 defensible |

| ID | Analysis | Method | Blocked on |
|----|----------|--------|------------|
| C-01 | Insider sale timing against subsequent price | Event study, ±30 trading days, discretionary sales only, 10b5-1 as control | D-01 |
| C-02 | 8-K event abnormal return | Market-adjusted return around each Item, grouped by Item number | D-01 |
| C-03 | Lobbying spend against federal obligations, with lag | Cross-correlation at 0–8 quarter lags | D-02 + award dates |
| C-04 | Margin against segment mix | Attribution across quarters | D-02 |
| C-05 | 13F entry and exit levels | Position deltas priced against the quarter's range | D-01 + multi-quarter 13F |
| C-06 | Working-capital cycle versus peers | Already computed; needs peer DSO/DIO/DPO | Peer financials, partly held |

Rules the correlation engine must obey, without exception:

1. State n alongside every coefficient. Suppress the finding entirely where
   n < 12 rather than printing a caveat.
2. Report the confidence interval, not the point estimate alone.
3. Never describe a correlation as causal. §11's contract-to-lobbying reading
   is the one most likely to be misread that way.
4. Correct for multiple comparisons. Testing 20 pairs at p<0.05 yields one
   false positive by construction.
5. Publish the negative results. "No relationship between lobbying quarters and
   award timing at any lag tested" is a finding and belongs in the report.

### 4C.3 Private-investigator-style research (P-series)

Three connectors for this already exist and none is wired into the
orchestrator: `entity_network_connector.py` (859 lines — `discover_family_network`,
`build_entity_network`, `analyze_board_interlocks`), `institutional_overlap_connector.py`
(469 lines) and `linkedin_deep_connector.py` (461 lines). The audit lesson from
STEP 0 applies directly: test what these return before writing anything new.
Four of the six issues in the first pass were single-parameter bugs in parsers
that already existed.

**Priority set 2026-07-31 (James).** The free-source network work is promoted
to **P0 and runs alongside the remaining B-series parity items**, not after
them. Paid VC data stays Phase 3+. The governing rule is source cost, not
perceived value.

| ID | Capability | Source | Cost | Priority | State |
|----|------------|--------|------|----------|-------|
| P-04 | Related-party transactions | DEF 14A Item 404 | Free | **P0** | ✅ **Shipped v3.2** — parser rewritten, rendered under Key Personnel |
| P-07 | Subsidiary and affiliate map | 10-K Exhibit 21 | Free | **P0** | ✅ **Shipped v3.2** — `filing_notes_connector.get_subsidiaries`, own report section |
| P-02 | Institutional overlap — managers holding this issuer and its peers | 13F-HR, already parsed | Free | **P0** | ✅ **Shipped v3.2** — repointed at 13F, allocation skew replaces the artifact flag |
| P-01 | Board interlocks — shared directorships across issuers | Form 3 across each insider's own CIK | Free | **P0** | ✅ **Shipped v3.2** — `board_interlock_connector.get_board_interlocks` |
| P-05 | Beneficial ownership above 5%, activist stakes | SC 13D/G | Free | **P0** | ✅ **Shipped v3.2** — `board_interlock_connector.get_beneficial_owners`, both directions |
| P-09 | Company's own venture and strategic investments | 10-K non-marketable equity securities note | Free | **P0** | ✅ **Shipped v3.2** — ASC 321 rollforward parsed and rendered |
| P-08 | Auditor, counsel and banker relationships | 10-K, DEF 14A, 8-K | Free | P1 | Not built |
| P-03 | Revolving door — officials moving between agency and issuer | Federal directories + proxy bios | Free | P1 | Not built |
| P-06 | Executive career histories | LinkedIn via Apify | ~$0.05/profile | Phase 3+ | Exists, unwired; ToS position must be settled before use |
| P-10 | **Co-investors in a given funding round** | PitchBook / Crunchbase | $6–20K/yr | Phase 3+ | **No free path — see below** |

**Implementation note on P-01, added after building it.** The plan specified
board interlocks as a comparison of DEF 14A rosters across peer CIKs. That
approach is close to worthless and the reason is legal, not technical: section
8 of the Clayton Act prohibits one person from serving as a director of two
competing corporations, so a peer-restricted interlock search is designed to
return nothing. The route actually used inverts it. A person keeps one CIK for
life across every issuer where they report under Section 16, and Form 3 is
filed once per issuer relationship — so the issuers named in an individual's
Form 3 filings are exactly the public companies where they have served, in any
industry. This is both cheaper (one request per relationship, not per peer
proxy) and complete. Nothing in Section 16 records a departure, so a seat
counts as current only where the person has filed at that issuer within two
years; that window spans an annual grant cycle.

**P-05 runs in both directions.** EDGAR indexes a Schedule 13 under both the
subject company and the filer, so an issuer's own submissions contain the
schedules others filed about it *and* the schedules it filed about its five
percent stakes in other public companies. The second set was not anticipated in
this plan and is a finding in its own right — it places corporate positions on
the public record that would otherwise be invisible. Walmart's Schedule 13G
naming Ibotta is what surfaced the distinction.

**P-10 is the one capability with no free substitute, and it should not be
promised.** The 10-K non-marketable equity securities note discloses *what* an
issuer has invested in, so P-09 gives us the portfolio. It does not disclose
who else participated in the round. Form D is the obvious candidate and does
not solve it either: Form D names the issuer's own executive officers,
directors and promoters plus the offering size, never the investor list. Every
route to co-investor identity runs through a paid vendor. Any trend analysis
across investors, founders and board seats is therefore bounded to the
relationships that appear in public filings until that budget exists.

### 4C.4 Network trend analysis (N-series) — depends on the P-series

**All five P-series prerequisites shipped in v3.2; N-01..N-07 analysis shipped
in the eleventh pass.** These are the "trends between investors, founders,
employees and board seats" in concrete terms. Empty comparisons are omitted
rather than padded. Correlation-style n≥12 suppression still applies to the
C-series, not to these register comparisons.

| ID | Question the analysis answers | Inputs | Status |
|----|-------------------------------|--------|--------|
| N-01 | Which directors sit on boards of the issuer's suppliers, customers or competitors? | P-01 | ✅ Wired — empty when no peer/counterparty seat match |
| N-02 | Which institutions hold the issuer and its direct competitors simultaneously, and at what relative weight? | P-02 | ✅ Wired — allocation-skew findings |
| N-03 | Do the issuer's venture investments cluster in the same sub-sector as its acquisitions? | P-09 + notes parser | ✅ Wired — needs named ASC 321 holdings |
| N-04 | Do executives and directors move between the issuer and the entities it invests in or acquires? | P-01 + P-09 + Form 4 | ✅ Wired — empty without named investee/acquiree seats |
| N-05 | Does a 5%+ holder appear on the register before or after a strategic announcement? | P-05 + timeline | ✅ Wired — ±90d adjacency, no causation |
| N-06 | Which subsidiaries are registered in jurisdictions inconsistent with disclosed operations? | P-07 | ✅ Wired — geo revenue vs Exhibit 21 |
| N-07 | Do related-party counterparties overlap with subsidiaries, investees or director affiliations? | P-04 + P-07 + P-09 | ✅ Wired — omit when empty |

All seven run under `### Network analysis` in the PDF. Empty legs are omitted.
N-07 remains the highest-value item when it fires; on NVDA it correctly does not.

**Standing constraint.** Every P-series finding names a natural person or a
private relationship. The provenance rule that governs the rest of the report
applies with more force here, not less: a claim about an individual carries a
source URL and a filed document behind it, or it does not appear. Inference
presented as fact is what the old `NVIDIA_Intelligence.pdf` did, and it is the
failure this architecture exists to prevent.

## 5. NEW DATA SOURCES TO INTEGRATE

> **Scope correction (v3.0)**: The reference report needs ONLY the free tier below plus a market-data source. Everything paid or LinkedIn-based is Phase 3+ and must not block reference parity.

### 5.0 Priority 0 — Reference Parity (all free, Phase 1)

| Source | API/Method | Data Type | Status |
|--------|------------|-----------|--------|
| **SEC XBRL companyfacts** | data.sec.gov | Annual/quarterly financials | Working, output dropped downstream |
| **10-K R-file exhibits** | SEC EDGAR filing index | Investment portfolio, Groq deal, commitments, warranty, segment/geo/customer concentration | **No parser — build** |
| **DEF 14A** | SEC EDGAR | Personnel dossiers, compensation, ownership | Parser exists, unwired |
| **Form 4 raw XML** | EDGAR submissions API | Insider transactions + 10b5-1 flag | Parser exists, unwired |
| **USASpending API v2** | spending_by_award, filtered by UEI | Federal prime awards + subawards | Needs UEI resolution fix |
| **Senate LDA API** | lda.senate.gov | All lobbying filings | Returns template — debug |
| **Market/consensus data** | Perplexity Finance / Alpha Vantage / Finnhub | Price, market cap, analyst targets | **Missing — highest-leverage fix** |
| **CourtListener** | Free API | Litigation docket | Connector exists, only count renders |

### 5.1 Phase 3+ (Expanded Vision — NOT needed for reference parity)

| Source | API/Method | Data Type | Cost |
|--------|------------|-----------|------|
| **LinkedIn via Apify** | Apify actors | Personnel, career, connections | ~$0.05/profile |
| **PitchBook** | API or scraping | VC/PE deals, valuations, investors | $20K+/year or scrape |
| **Crunchbase** | API | Funding, M&A, people | $6K/year (Pro) |
| **OpenSecrets** | API (free) | Political donations, lobbying | Free |
| **FPDS.gov** | API (free) | Full federal contract database | Free |
| **13F Filings Parser** | SEC EDGAR | Institutional ownership overlap | Free (build parser) |
| **Clearbit/Apollo** | API | Company enrichment, contacts | Variable |

### 5.2 Priority 1 (High - Should Have)

| Source | API/Method | Data Type | Cost |
|--------|------------|-----------|------|
| **BoardEx** | API | Director networks, compensation | $50K+/year |
| **RelSci** | API | Relationship intelligence, family | $25K+/year |
| **FactSet** | API | Financial data, ownership | Enterprise |
| **S&P Capital IQ** | API | Financials, M&A, ownership | Enterprise |
| **USPTO** | API (free) | Patent filings | Free |
| **Dun & Bradstreet** | API | Corporate family trees | Enterprise |

### 5.3 Priority 2 (Nice to Have)

| Source | API/Method | Data Type | Cost |
|--------|------------|-----------|------|
| **LexisNexis** | API | News, litigation, public records | Enterprise |
| **PACER/CourtListener** | API | Federal litigation | $0.10/page or free |
| **Refinitiv/LSEG** | API | Full financial data suite | Enterprise |
| **AlphaSense** | API | Document search, earnings transcripts | $25K+/year |
| **Similarweb** | API | Web traffic, digital footprint | Variable |

---

## 6. IMPLEMENTATION ROADMAP (Expanded Vision — Phase 3+)

> **v3.0 note**: The five phases below describe the EXPANDED vision (LinkedIn, 13F overlap, correlation engine). They come AFTER reference parity. The actual immediate roadmap is §10 (Step 0 audit + P0-1…P0-14). Phase numbering below is kept for historical continuity.

### Phase 1: Foundation (Week 1-2)
```
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 1: FOUNDATION                                             │
├─────────────────────────────────────────────────────────────────┤
│  1. LinkedIn Connector (Apify)                                   │
│     - Build linkedin_connector.py                                │
│     - Integrate with Apify LinkedIn Profile Scraper              │
│     - Add to people_research_agent.py                            │
│                                                                  │
│  2. Enhanced 13F Parser                                          │
│     - Build institutional_overlap_connector.py                   │
│     - Cross-reference holdings across competitors                │
│     - Generate shared investor reports                           │
│                                                                  │
│  3. FPDS.gov Full Integration                                    │
│     - Build fpds_connector.py                                    │
│     - Pull ALL federal contracts (not just USASpending summary)  │
│     - Include modifications, options, subcontracts               │
│                                                                  │
│  4. OpenSecrets Integration                                      │
│     - Build opensecrets_connector.py                             │
│     - PAC contributions, individual donations                    │
│     - Lobbying firm details                                      │
└─────────────────────────────────────────────────────────────────┘
```

### Phase 2: People Intelligence (Week 3-4)
```
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 2: PEOPLE INTELLIGENCE                                    │
├─────────────────────────────────────────────────────────────────┤
│  1. Deep Personnel Research Agent                                │
│     - Orchestrate LinkedIn + Apollo + SEC filings                │
│     - Build career timelines automatically                       │
│     - Extract education, certifications                          │
│                                                                  │
│  2. Family Connection Research                                   │
│     - Cross-reference Form 4 with LinkedIn                       │
│     - Identify family members in business                        │
│     - Flag related party employment                              │
│                                                                  │
│  3. Board Interlock Mapping                                      │
│     - Parse all DEF 14A proxies for board seats                  │
│     - Build cross-company board graph                            │
│     - Identify potential conflicts                               │
│                                                                  │
│  4. Advisor Network Detection                                    │
│     - Identify disclosed advisors                                │
│     - LinkedIn connection analysis                               │
│     - Investment/consulting relationships                        │
└─────────────────────────────────────────────────────────────────┘
```

### Phase 3: Money Flows & Investments (Week 5-6)
```
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 3: MONEY FLOWS                                            │
├─────────────────────────────────────────────────────────────────┤
│  1. Crunchbase/PitchBook Integration                             │
│     - All funding rounds for subject + portfolio companies       │
│     - M&A history (acquirer and target)                          │
│     - Valuation timeline                                         │
│                                                                  │
│  2. Investment Activity Tracking                                 │
│     - Corporate venture arm investments                          │
│     - Strategic minority stakes                                  │
│     - Partnership announcements                                  │
│                                                                  │
│  3. Self-Dealing Detection Engine                                │
│     - Cross-reference contracts with insider ownership           │
│     - Subcontractor entity matching                              │
│     - Temporal correlation analysis                              │
│                                                                  │
│  4. Valuation History Builder                                    │
│     - Stock price timeline with event annotations                │
│     - Private valuation marks (from funding rounds)              │
│     - Analyst target history                                     │
└─────────────────────────────────────────────────────────────────┘
```

### Phase 4: Competitive & Network Intelligence (Week 7-8)
```
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 4: COMPETITIVE & NETWORK                                  │
├─────────────────────────────────────────────────────────────────┤
│  1. Competitor Deep Profiles                                     │
│     - Auto-generate profiles for top 5-10 competitors           │
│     - Side-by-side comparison tables                             │
│     - Infrastructure/capability assessment                       │
│                                                                  │
│  2. Shared Investor Analysis                                     │
│     - 13F overlap visualization                                  │
│     - Correlation scoring                                        │
│     - Flow-through risk assessment                               │
│                                                                  │
│  3. Supply Chain Mapping                                         │
│     - Identify key suppliers (TSMC, etc.)                        │
│     - Customer concentration                                     │
│     - Geographic risk assessment                                 │
│                                                                  │
│  4. Patent/IP Landscape                                          │
│     - USPTO integration                                          │
│     - Citation network                                           │
│     - Competitive IP positioning                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Phase 5: Correlation Engine & Final Assembly (Week 9-10)
```
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 5: CORRELATION ENGINE                                     │
├─────────────────────────────────────────────────────────────────┤
│  1. Cross-Reference Engine                                       │
│     - Entity resolution across all data sources                  │
│     - Relationship graph construction                            │
│     - Hidden connection detection                                │
│                                                                  │
│  2. Anomaly Detection                                            │
│     - Unusual transaction patterns                               │
│     - Timing correlations (lobbying → contracts)                 │
│     - Insider trading pattern detection                          │
│                                                                  │
│  3. Intelligence Brief Generator                                 │
│     - Auto-generate key findings                                 │
│     - Prioritize red flags                                       │
│     - Executive summary synthesis                                │
│                                                                  │
│  4. Deep Intelligence PDF                                        │
│     - 50-100+ page comprehensive dossier                         │
│     - Interactive relationship graphs                            │
│     - Full source citations                                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. NEW FILE STRUCTURE

```
apps/api/app/
├── connectors/
│   ├── linkedin_connector.py          # NEW - Apify LinkedIn
│   ├── pitchbook_connector.py         # NEW - VC/PE data
│   ├── crunchbase_connector.py        # NEW - Funding/M&A
│   ├── opensecrets_connector.py       # NEW - Political money
│   ├── fpds_connector.py              # NEW - Full fed contracts
│   ├── boardex_connector.py           # NEW - Board networks
│   ├── institutional_overlap.py       # NEW - 13F overlap
│   └── patent_connector.py            # NEW - USPTO
│
├── agents/
│   └── deep_research/
│       ├── __init__.py
│       ├── entity_research_agent.py   # NEW
│       ├── people_research_agent.py   # NEW
│       ├── money_flow_agent.py        # NEW
│       ├── network_mapping_agent.py   # NEW
│       ├── competitive_intel_agent.py # NEW
│       ├── political_intel_agent.py   # NEW
│       ├── correlation_engine.py      # NEW
│       └── orchestrator.py            # NEW - Master coordinator
│
├── services/
│   ├── deep_intelligence_service.py   # NEW - Main entry point
│   ├── self_dealing_detector.py       # NEW - Red flag engine
│   └── relationship_graph_service.py  # NEW - Graph construction
│
└── templates/
    └── deep_report_prompts.py         # NEW - Enhanced prompts
```

---

## 8. EXAMPLE: NVIDIA DEEP INTELLIGENCE (TARGET OUTPUT)

### Current Report: 2 pages, ~5% data density (verified 2026-07-30)
### Phase 1 Target: 42 pages, ~95% data density (reference parity, free sources)
### Phase 3+ Target: 80-120 pages (expanded vision)

**New Sections to Add:**

1. **Complete Cap Table** (all 50+ institutional holders with % ownership)
2. **Executive Family Trees** (documented business relationships)
3. **Full Contract Portfolio** ($XXX million, not just $50K)
4. **Self-Dealing Analysis** (with specific findings, not templates)
5. **Competitor Investor Overlap** (13F cross-reference)
6. **Board Interlock Network** (visual graph + analysis)
7. **Political Money Flow** (PAC + individual + bundling)
8. **Revolving Door Tracking** (specific hires with dates)
9. **Valuation Timeline** (with annotated events)
10. **M&A & Venture Activity** (all documented deals)
11. **Supply Chain Risk** (TSMC dependency, geographic exposure)
12. **Correlation Analysis** (cross-entity pattern detection)

---

## 9. SUCCESS METRICS

| Metric | Current (verified) | Phase 1 Target (reference parity) | Phase 3+ Target |
|--------|--------------------|-----------------------------------|-----------------|
| Report pages | 2 | 42 | 80-120 |
| Data density (% fields populated) | ~5% | 95% | 95%+ |
| Unique data sources used | ~4 flowing | 8 free sources, all flowing | 20+ |
| Personnel profiles (deep) | 0 rendered | 15 (5 NEOs + 10 directors, per DEF 14A) | 20+ |
| Insider transactions | 0 rendered | All Form 4s parsed w/ 10b5-1 split | + pattern detection |
| Government contracts | 5 ($50K) | All UEI-resolved prime awards + subawards | + FPDS full history |
| Lobbying filings | Template | All LDA filings w/ registrant breakdown | + revolving door |
| Source citations | 0 | Deep URL on every numeric claim | Same |
| Appendix workbook | None | 13-sheet xlsx | Same |
| Quality gates passing | 0 | All 10 (see §10) | Same |

---

## 10. IMMEDIATE NEXT STEPS

### 🔴 STEP 0: AUDIT BEFORE BUILDING (do this first)

Run a direct test call against each existing connector and record what it actually returns for NVDA. Most "NOT STARTED" items were parsers that already exist. Do not write a new parser until the audit proves the existing one is broken:

```bash
# Example audit calls (from apps/api)
python -c "from app.connectors.sec_edgar_connector import get_full_financial_profile; import json; print(json.dumps(get_full_financial_profile('NVDA'), default=str)[:3000])"
python -c "from app.connectors.proxy_statement_connector import get_proxy_intelligence; ..."
python -c "from app.connectors.sec_edgar_connector import get_insider_transactions; ..."
```

### 🔴 PHASE 1 FIXES (reference parity, free sources only)

| Priority | Task | Corrected Description | Estimated Effort |
|----------|------|----------------------|------------------|
| P0-1 | **Fix report assembly for financials** | XBRL data IS retrieved (FCF matches reference) — find where orchestrator output is dropped before the markdown template and wire annual/quarterly/TTM tables through | 3-5 hours |
| P0-2 | **Add Stock Price + Consensus Source** | Alpha Vantage / Finnhub / Perplexity Finance for price, market cap, analyst targets. Unblocks the entire DCF (P0-3). Highest-leverage single fix. | 2-3 hours |
| P0-3 | **Wire DCF + add reverse DCF, sensitivity, comps** | `build_dcf_valuation` exists; after P0-2, add reverse DCF (implied CAGR), WACC×terminal sensitivity grid, peer comparables table | 4-6 hours |
| P0-4 | **Verify + wire Form 4 parser** | `get_insider_transactions` exists in `sec_edgar_connector.py`. Verify output, confirm `aff10b5One` (10b5-1) detection, compute discretionary-vs-planned split, wire to template | 3-5 hours |
| P0-5 | **Verify + wire DEF 14A parser** | `proxy_statement_connector.py` (734 lines) exists. Verify against NVDA DEF 14A, produce 15 dossiers (5 NEOs + 10 directors), wire to template | 3-5 hours |
| P0-6 | **Fix USASpending via UEI resolution** | Resolve canonical UEIs through the recipient endpoint FIRST (NVIDIA Corp: ESRLMLGWDNM3; NVIDIA Public Sector: DGCXHYTC7AD5), then filter awards by UEI. Name-based search both misses subsidiaries and returns false positives. Include subawards. | 3-4 hours |
| P0-7 | **Fix Senate LDA integration** | Debug `fetch_lobbying_summary` to return all real filings with registrant/firm breakdown | 2-3 hours |
| P0-8 | **Build 10-K note parser (NEW)** | Parse R-file exhibits for: investment portfolio ($72.5B book), business combinations (Groq terms), purchase commitments, warranty accruals, segment/geographic/customer concentration. XBRL companyfacts cannot produce these. | 8-12 hours |
| P0-9 | **Fiscal-basis + derived-Q4 logic (NEW)** | Handle NVIDIA's late-January FY end; derive Q4 as FY−(Q1+Q2+Q3) and flag DERIVED; tag every figure with FY/Q label | 3-4 hours |
| P0-10 | **Per-claim source-URL data model (NEW)** | Every numeric value carries its deep source URL through connector → orchestrator → template. Rule: an unretrieved figure is never estimated — declare gaps instead. | 6-10 hours |
| P0-11 | **Wire litigation docket + missing sections** | Litigation connector exists — render full docket by category. Add customer concentration, geographic exposure, capital allocation sections (fed by P0-8) | 4-6 hours |
| P0-12 | **Government Action Precedent Library (NEW)** | 15 researched case studies (Arm/FTC, CHIPS clawbacks, Entity List, Section 232, AT&T, etc.). This is LLM-research synthesis work, not an API connector — budget accordingly | 6-10 hours |
| P0-13 | **13-sheet xlsx appendix generator (NEW)** | openpyxl workbook fed from the same data model: A1/A2 financials, A3 valuation, A4 sensitivity, A5 comps, B/B2 awards, C lobbying, D/D2 insiders, H/H2 litigation & export controls | 6-8 hours |
| P0-14 | **Full quality-gate battery** | See gate list below. This — not more data — is what separates the reference from a template. | 8-12 hours |

**Realistic Phase 1 total: ~60-95 hours** (prior estimate of ~20-28 hours excluded note parsing, the workbook, the precedent library, and real quality gates).

### Quality Gates (match the reference's §14.2 — P0-14)

| Gate | Threshold |
|------|-----------|
| Citation coverage of numeric blocks | ≥0.95, hard fail below 0.90 |
| Arithmetic reconciliation | ±0.5% — segment sums, geo sums, cash-flow bridges, award ledger, insider totals must tie |
| Duplicate-paragraph detection | Jaccard >0.85 fails |
| News staleness | Newest item ≤90 days; window ≤24 months |
| Directionality lint | Lower-is-better set (D/E, DSO, days inventory) never marked "below average" |
| Placeholder scan | Reject "TBD", "N/A", "$0.00", "UNKNOWN", "should be evaluated" |
| Fiscal-basis lint | Every figure carries FY/Q label and GAAP tag |
| Landing-page citation ban | Deep document URLs only |
| Named-person accuracy | ≥2 independent sources per person |
| Sensitive-claim review | Documented facts only; no asserted motive |

### 🟡 PHASE 3+ FEATURES (expanded vision — after reference parity)

1. **Build LinkedIn Connector** (Apify integration) — `linkedin_deep_connector.py` already scaffolded
2. **Build FPDS Full Connector** (complete federal contracts)
3. **Build OpenSecrets Connector** (political money)
4. **Build 13F Overlap Analyzer** (competitor shared investors)
5. **Create People Research Agent** (orchestrate personnel data)
6. **Create Self-Dealing Detector** (automated red flag engine)
7. **Enhance PDF Template** (support 80+ page reports)
8. **Build Correlation Engine** (cross-reference all data)

---

## 11. ACCEPTANCE CRITERIA

### Milestone A — Pipeline Fixed (data flows end-to-end):

- [ ] NVIDIA report generates with real financial data (not $0.00) — annual, quarterly (derived Q4 flagged), TTM
- [ ] DCF valuation shows 3 scenarios with calculated intrinsic values, plus reverse DCF and sensitivity grid
- [ ] Personnel section has 15 dossiers (5 NEOs + 10 directors from DEF 14A)
- [ ] Insider transactions show all Form 4 data with discretionary vs 10b5-1 split
- [ ] Government contracts UEI-resolved, prime awards + subawards (reference found $46M/10 awards, not $50K)
- [ ] Lobbying section shows all real LDA filings with registrant breakdown
- [ ] No empty sections, no $0.00, no "UNKNOWN" in final PDF

### Milestone B — Reference Parity Achieved:

- [ ] Report matches or exceeds `/reports/NVIDIA Corporation — Intelligence Report.pdf`
- [ ] 42+ pages with 95%+ data density
- [ ] All 16 sections fully populated, including 10-K note-derived content (investment portfolio, commitments, customer concentration)
- [ ] 13-sheet appendix workbook (xlsx) generated
- [ ] Deep source URL on every numeric claim; unretrieved figures declared as gaps, never estimated
- [ ] All 10 quality gates pass (see §10)
- [ ] Government Action Precedent Library present with sourced case studies
- [ ] Built from free sources only (SEC EDGAR, USASpending, Senate LDA, one market-data API)

---

*Document Version: 3.0*
*Created: 2026-07-30*
*Last Updated: 2026-07-30 (v3.0 — status tracker reconciled against actual codebase; diagnosis corrected from "connectors missing" to "wiring/rendering broken"; Phase 1 re-scoped to reference parity with free sources; added 10-K note parsing, fiscal-basis/derived-Q4, source-URL data model, xlsx appendix, precedent library, and full quality-gate tasks)*
*Status: PHASE 1 IN PROGRESS — R1–R6 resolved 2026-07-31 (see status tracker). Remaining: Form 4 value parsing, board roster, institutional overlap, P0-12 precedent library, P0-13 XLSX appendix, P0-14 full gate battery.*
