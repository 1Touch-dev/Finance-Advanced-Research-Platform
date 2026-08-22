# Decision Log & Risk Register

**Owner:** Anshuman · **Review:** every sprint close
Decisions James owns are marked **CEO**. Each has a *needed-by* date and a named consequence of delay.

---

## Part 1 — Open decisions

Six open. Four are blocking. A decision without a deadline never arrives, so every row has one, and
every row states what slips if it does not.

| ID | Decision | Owner | Needed by | Blocks | Cost of delay |
|---|---|---|---|---|---|
| [D1](#d1) | Advisor / team segment: yes or no? | **CEO** | 13 Oct | Band D (11 features), schema | Item 61 schema gets expensive after S3 |
| [D2](#d2) | Private-market data budget | **CEO** | 6 Oct | W7, S5-A | S5 becomes catch-up; cap-table gap persists |
| [D3](#d3) | Recursion depth = cost. Approve depth 3 + monthly cap? | **CEO** | 1 Sep | S2-B | Cannot size the graph run |
| [D4](#d4) | LinkedIn: kill it, or accept ToS risk? | **CEO** | 1 Sep | Person↔company enrichment | Dead connector stays in the codebase |
| [D5](#d5) | Retire the feature-count metric | TL | **done** | reporting | — |
| [D6](#d6) | Formally decline crypto depth, native app, offline, biometrics, widgets, UGC | TL + CEO ack | 1 Sep | scope hygiene | Re-litigated later |

---

### D1 · Advisor / team segment {#d1}

**CEO decision. Needed 13 Oct.**

Eleven Band D features are worth either a large multiple of individual subscription revenue, or
exactly zero. Nothing in between, and nothing partial.

| If YES | If NO |
|---|---|
| Build items 57–67 (factor exposure, rebalancing, model portfolios, client reporting, households, branded export) | Build none of them |
| **Item 61 — multi-account households — is a data-model change.** Must be decided before S3 fixes the schema | Save ~150h; redirect to depth |
| Compliance surface expands materially (rebalancing especially) | No added compliance surface |

**Recommendation: NO for now, revisit after first paying customers.** Rationale — we have no
validated buyer in that segment, the register's own guidance is *"do not build speculatively"*, and
the honest read of the last six weeks is that we do not need eleven more features, we need the ones
we have to be true. **But item 61's schema shape must be reserved in S3 regardless**, because
retrofitting households after the schema sets is the expensive version of this decision.

---

### D2 · Private-market data budget {#d2}

**CEO decision. Needed 6 Oct.** James researched these himself on 2 Aug and priced them, then said
*"Look for an alternative if possible…"* — so this is a decision he has already half-made.

| Option | Cost | What it gives | Verdict |
|---|---|---|---|
| **Do nothing more** | $0 | The 12 free edge types in [register §5](05-SOURCE-DEPTH-REGISTER.md#5-free-edges-we-are-not-collecting) | **Do this first regardless** |
| Fundable | $20–100/mo | Funding rounds + 135k investor profiles, self-serve API + MCP | ✅ Recommended |
| People Data Labs | ~$98/mo | Person↔company linkage — **the legal replacement for LinkedIn scraping** | ✅ Recommended, resolves [D4](#d4) |
| Coresignal | $49–499/mo | Firmographics, funding, headcount history, 75M companies | Alternative to PDL |
| PrivCo | $99–167/mo | US private company financials | Later |
| Caplight | quote | Round-by-round amounts + valuations with citations, MCP server | **Closest match to the cap-table ask** — get a quote |
| Crunchbase / PitchBook | $6–20K/yr | The obvious answer | ❌ Dominated by the above |

**Recommendation: $150–250/mo — Fundable + PDL — starting S5, but only after the $0 free-edge work
lands in S1–S2.** Sequencing matters: buying data before extracting what we already have would repeat
exactly the breadth mistake that prompted the 18 Aug message.

Also worth saying plainly to James: his own research already found the right answer. The recommendation
is his list, filtered, with a sequence attached.

---

### D3 · Recursion depth budget {#d3}

**CEO decision. Needed 1 Sep.** This is where *"go as deep research as possible"* meets arithmetic.

```
   Cost per PayPal-Mafia-style run, 23 seed entities, branching ≈ 12

   depth 1 →       23 entities   ~$0.50      trivial
   depth 2 →      276 entities   ~$8         fine
   depth 3 →    3,312 entities   ~$95        ← recommended cap
   depth 4 →   39,744 entities   ~$1,150     per run
   depth 5 →  476,928 entities   ~$13,800    per run

   Rough: API calls + LLM extraction. S1's rate-limit audit sharpens these.
```

**Recommendation: depth 3 default, depth 4 by explicit request on a single seed, $500/mo ceiling
enforced in `cost_controls.py`.**

The framing for James — and this is the productive version of the conversation — is that **depth is a
budget line, not an ambition**. He can have depth 4; it costs ~$1,150 a run. Show him the curve and
let him buy the depth he wants, rather than arguing about the principle of going deeper. He is
cost-conscious (§2 of the [manual](03-CEO-OPERATING-MANUAL.md)), so he will pick sensibly once the
number is visible.

---

### D4 · LinkedIn {#d4}

**CEO decision. Needed 1 Sep.** `linkedin_deep_connector.py` exists and is ToS-blocked.

| Option | Assessment |
|---|---|
| Keep scraping | Legal + platform risk, breaks constantly, unusable in a product sold on trustworthiness |
| **Delete + adopt People Data Labs** (~$98/mo) | ✅ Recommended. Licensed person↔company linkage, same capability, no risk |
| Delete, no replacement | Loses employee-history edges James explicitly asked for (*"analyze employees deeply"*) |

**Recommendation: delete the connector, adopt PDL as part of [D2](#d2).** Note the connection — one
$98/mo line item removes a legal risk *and* fills a capability gap. Cheapest decision on this page.

---

### D5 · Retire the feature-count metric {#d5}

**TL decision. Made 19 Aug.**

Reporting "78 of 72 features done (108%)" while 40 of 89 services contain fabricated data paths is
how a project arrives at a CEO saying *"nothing on link is working at all"* three days after a
green status report. The metric caused the behaviour.

**Replaced by:** real-data endpoint %, field extraction depth, evidence coverage, graph size, demo
uptime, causation violations. See [plan §7](02-PROGRAM-PLAN.md#7-metrics--retire-feature-count-adopt-these).

`MASTER_TASK_STATUS.md` gets a correction banner at the top rather than a quiet edit — the corrected
count is a finding, and hiding the correction would repeat the original error.

---

### D6 · Formal declines {#d6}

**TL proposes, CEO acknowledges. Needed 1 Sep.** Recorded so nobody re-adds them by accident.

| Declined | Reason |
|---|---|
| Crypto depth | James: *"least of my priorities"* (18 Aug) |
| Native mobile app | PWA covers alerts; native is a whole maintenance track |
| Offline caching | Financial data users are online. Already built (E2) — sunk, do not extend |
| Biometric login | Already built (E3) — sunk. SSO matters more |
| Home-screen widgets | Requires native app |
| User-generated screen sharing | Already built (E5) — moderation + liability, tension with support commitment |
| Real-time options flow | OPRA licence-gated; delayed EOD substitute already chosen |
| Expert-call networks, broker research, licensed VOC, group chat | Licensing / moat |
| "Kimi swarm" per entity | Superseded by the recursion engine — same outcome, cost-capped |
| PitchBook / Crunchbase | Dominated by [D2](#d2) options at 1–2% of cost |

Note E2/E3/E5 — three Band E features, the lowest-value band in the register, were built on 17 Aug.
That is a scope-discipline failure worth naming once and then not relitigating.

---

## Part 2 — Risk register

| ID | Risk | P | Impact | Mitigation | Owner |
|---|---|:--:|:--:|---|---|
| [R1](#r1) | CEO trust erosion from mock data | **High** | **Critical** | S0 truth ledger + mock ban + smoke gate | TL |
| [R2](#r2) | Defamation / false-relationship claim | Med | **Critical** | A3 precision ≥ 0.95, A5 evidence 100%, A6 zero causation | TL |
| [R3](#r3) | Unbounded recursion cost | Med | High | Depth 3 cap + $ ceiling in `cost_controls.py` ([D3](#d3)) | TL |
| [R4](#r4) | Scope arriving mid-sprint | **High** | Med | 24h triage protocol + 18h/sprint reserve | TL |
| [R5](#r5) | Graph rebuild if entity resolution is wrong | Med | High | A3 gate before S2-C bulk extraction | TL |
| [R6](#r6) | Single-point key dependency | Med | Med | Fallback per source (A1 field 11) | Dev-1 |
| [R7](#r7) | 2 devs + 1 TL cannot cover 8 workstreams | Med | Med | Lane ownership; declared cut lines per sprint | TL |
| [R8](#r8) | Look-ahead bias invalidates historical output | Med | High | A4, ALFRED vintages, synthetic probe | TL |
| [R9](#r9) | ToS violation in redistribution | Low | High | A1 field 7 blocking; A8 | Dev-1 |
| [R10](#r10) | Key-person concentration on TL | **High** | High | ADRs in `docs/architecture/decisions.md`; pair on graph schema | TL |

### R1 · CEO trust erosion {#r1}
The live risk, not a hypothetical. Sequence already happened once: green status report → James clicks
→ nothing works → *"I didn't look great."* Each recurrence costs more than the last because it
discredits the reporting channel, not just the feature. **S0 exists for this and nothing else.**

### R2 · Defamation {#r2}
The product's purpose is asserting relationships between named, often powerful, private individuals.
A false-merge in entity resolution plus an inferred edge rendered as fact is the failure mode. Three
independent controls: A3 precision, A5 mandatory evidence, A6 zero-causation. **Any one of them
failing is a release blocker.** Cheap now, unfixable after publication.

### R3 · Unbounded recursion cost {#r3}
*"Go as deep research as possible"* is unbounded and $13.8k/run at depth 5. Mitigated by hard caps,
made non-contentious by showing the cost curve rather than debating the principle ([D3](#d3)).

### R4 · Mid-sprint scope {#r4}
2–3 unplanned research inbounds/week, historically absorbed silently or dropped silently. The 24h
triage protocol plus a budgeted 18h/sprint reserve converts an interruption into a planned input.

### R5 · Graph rebuild {#r5}
If A3 fails after S2-C has extracted at volume, every edge is suspect and the graph is rebuilt.
Ordering mitigates it: golden set and precision gate *before* bulk extraction, not after.

### R7 · Team capacity {#r7}
Eight workstreams, 90 coding h/week. Managed by strict lane ownership and by stating the cut line in
every sprint before it starts rather than discovering it at the end. Cut lines are already written
into [plan §6](02-PROGRAM-PLAN.md#6-sprint-detail).

### R10 · Key-person concentration {#r10}
Entity resolution, graph schema, recursion engine, evidence contract, all eight audits and CEO comms
all sit with one person. This is the most under-managed risk in the register. Mitigation: write
architecture decisions down as they are made, and pair Dev-1 on the graph schema in S2 so the design
is not single-sourced.

---

## Part 3 — Decisions already made

| Date | Decision | Rationale |
|---|---|---|
| 18 Aug | Decline bloomberg-terminal-free as a data solution | TUI wrapper; no short interest, earnings or IPO data |
| 18 Aug | Crypto deprioritised | CEO explicit |
| 18 Aug | Free APIs for short interest / earnings / IPO — FINRA, Finnhub, FMP | $0 vs. paid alternatives |
| 17 Aug | Replace FactSet/Refinitiv with in-house fact scoring | Cost |
| 17 Aug | Decline Plaid brokerage sync ($500/mo) | CSV/PDF upload already exists |
| 19 Aug | **Retire feature-count metric** ([D5](#d5)) | Caused the trust failure |
| 19 Aug | **Depth before breadth** | CEO's 18 Aug instruction |
| 19 Aug | **Evidence-mandatory edge store** | Enforced as DB constraint, not convention |
| 19 Aug | **Intelligence, never investment advice** | CEO corrected this twice in 23 seconds |
