# CEO Operating Manual — James Deller

**Internal. Do not send to James.** For Anshuman + leads only.
Derived from ~60 messages, 21 Jul → 18 Aug 2026 (`JAMES_ASKS.txt`).

This is not a personality profile for its own sake. It is a decoding table: his messages are short,
frequent and look unrelated, and misreading them costs sprints. Every claim below is anchored to
something he actually wrote.

---

## 1. The one-line model

> **He is not asking for features. He is asking for a machine that finds what nobody else has found,
> and he judges it by whether he can look at a picture and see something he didn't already know.**

Read every message through that. It resolves almost all of the apparent contradictions.

---

## 2. What he actually values, ranked

Ranked by frequency × intensity across the corpus.

| Rank | Value | His words | What it means operationally |
|:--:|---|---|---|
| 1 | **Depth over breadth** | *"Go as deep research as possible"* · *"going further and further in always"* · *"This needs to be ridiculously well researched"* | One entity explored 5 levels beats 50 entities at level 1. He will never be impressed by a count. |
| 2 | **Relationships over entities** | *"find associates of each of these people"* · *"people related to each one of them"* | The edge is the product, not the node. A list of people is worthless to him; a link between two people is the whole thing. |
| 3 | **Non-obvious correlations** | *"that will help you find correlations"* · *"What patterns emerge that aren't obvious from any single database?"* | If one API answers it, he considers it commodity. Value = requires joining ≥ 2 sources. |
| 4 | **Following the money** | *"Please maintain the idea of following the money"* | His recurring organising metaphor. When lost, ask "does this trace a dollar or a relationship?" |
| 5 | **Visual comprehension** | *"maybe a timeline would be great… Adding tables graphs visualization"* + the WSJ + bubble-chart links | He thinks visually. A picture is how he verifies. |
| 6 | **Simplicity of surface** | *"as simple clean as possible"* · *"Dark blue would be more finance"* | Complex intelligence, simple presentation. He does not want a cockpit. |
| 7 | **Cost discipline** | *"Look for an alternative if possible…"* then researched 15 cheap APIs himself | He will fund data, but he wants the cheap path found first. |

### 2.1 What he explicitly does not value

Write these down so they never consume a sprint again.

| Deprioritised | Evidence | Action |
|---|---|---|
| **Crypto** | *"not focused on crypto at all; it is the least of my priorities"* (18 Aug) | Maintain, never extend. Any crypto work is a misread. |
| **yfinance-style basics** | *"ok so no need. But maybe validator or fall back"* | Keep as fallback only. |
| **Buy/sell recommendations** | *"Point is not whether to invest or not. **point is deep intelligence**"* | **This is the most misread message in the corpus.** See §3.1. |
| Trading execution | Platform scoped as data/analysis | Out of scope. |

---

## 3. The four decode rules

### 3.1 "Deep intelligence" ≠ investment advice

On 4 Aug I described a report as *"an investment decision kind of report — whether to invest in NVIDIA
or not"*. He replied within 23 seconds, twice:

> *"Point is not wether to invest or not"*
> *"point is deep inteligence"*

Two messages, that fast, is correction not conversation. **He is not building a robo-advisor. He is
building an intelligence product.** The output is *understanding of a network*, not a verdict on a
security. Every time a feature is framed as "should you buy X", it is off-thesis.

Convenient side effect: it is also the framing with the least regulatory exposure. Intelligence
about disclosed facts is a very different compliance object from a recommendation.

### 3.2 A named example is a request for a capability

He says "PayPal Mafia". He does not mean *produce a PayPal Mafia report*. Proof — after I delivered
an 86-page PayPal-Mafia-and-Palantir report and he replied *"Amazing this is awesome"*, he then said:

> *"paypal mafia, needs to expand to research across all investments, recent investments, board
> members, advisors, employees they continuously hire, etc."*
> *"not nvidia focused"*

The report was accepted and immediately treated as insufficient — because the report was never the
ask. **PayPal Mafia is his test fixture for a general recursive intelligence engine.** Same for
NVIDIA, same for Palantir, same for the Trump-family WSJ link.

**Rule: when he names an entity, build the engine and demo it on that entity.** Building the
one-off report is the trap, and I have already fallen into it once at a cost of roughly a week.

### 3.3 "Amazing!" is not signoff

His enthusiasm is genuine, immediate, and carries zero information about completeness.

```
   4 Aug  9:53pm   "Amazing this is awesome"        ← re: 86-page report
   4 Aug  7:42pm   "needs to expand to research     ← same artifact, same evening
                    across all investments..."
```

Praise and expansion arrive together. **Never treat "amazing" as done.** Treat it as: the direction
is right, now go deeper. Ask explicitly — *"is this closed, or is this the new baseline?"* — because
he will not volunteer the distinction.

### 3.4 A link is a specification

He sends links instead of writing requirements. Each one is a spec in compressed form.

| Link | Date | What he is specifying |
|---|---|---|
| WSJ Trump family business visualized | 30 Jul | **This is the target output format.** Entity-flow visual. → S4-B |
| leoniewharton.com/bubble-chart | 31 Jul | Network bubble visualisation → S2-E |
| qz.com "all investments by PayPal mafia since 1995" | 31 Jul | Investment-history completeness bar |
| rolodexmedia / Scribd / Medium PayPal Mafia pieces | 31 Jul | The narrative depth expected |
| 10 Claude finance skills + 7 agent frameworks | 6 Aug | *"No finance / Intelligence"* — for the product, not internal tooling |
| 15 private-market APIs with prices | 2 Aug | He has done the procurement research. Decide, don't re-research. |

**Rule: every link he sends gets logged as a requirement with an ID, or it gets lost.** Historically
they have been lost. That is a process failure on my side, and §6 fixes it.

---

## 4. How he validates

He does not read code, test counts, or architecture diagrams. There is no evidence in the entire
corpus of him engaging with any internal metric. He validates by **clicking and looking**.

```
   HOW I HAVE BEEN REPORTING          HOW HE ACTUALLY EVALUATES
   ─────────────────────────────      ────────────────────────────────
   "1183 tests, 99.6% passing"        opens the link
   "78 of 72 features done"           clicks around
   "F1 = 0.895"                       "nothing on link is working at all"
   "40+ connectors"                   "I didn't look great"
   "+8.5% ranking accuracy"           looks at a picture
                                      "Amazing this is awesome"
```

Left column: zero reactions in 60 messages. Right column: every reaction he has ever given.

**Consequence for planning:** the Friday artifact ship in [plan §8](02-PROGRAM-PLAN.md#8-cadence) is
not a nicety. It is the only channel through which he can perceive progress. Architecture weeks with
no visible artifact read to him as stalled weeks, and stalled weeks are when unplanned scope arrives.

---

## 5. The anxiety he has told you about, once

> *"Anshuman nothing on link is working at all"*
> *"**I didn't look great.**"* — 5 Aug, 4:26am

The second sentence is the most useful thing he has said. He was showing the platform to someone
else and it broke. His exposure is **reputational**, not technical.

Two implications, both load-bearing:

1. **Demo reliability outranks every feature.** This is the entire justification for S0 and for the
   permanent 15-minute smoke gate. A broken link does not cost us a bug ticket; it costs him standing
   in front of a third party.
2. **He needs forwardable artifacts.** He is not the end consumer — he is a distributor. Everything
   shipped should survive being sent to someone with no context. That is why Report v2 leads with an
   Executive Intelligence Summary and why the confidence tiers must be legible to a stranger.

Also note the timestamp: **4:26am**. His messages cluster 6:26am–9:12pm across many timezones. He is
engaged at all hours and expects fast acknowledgement. Acknowledge within hours; deliver on schedule.
Those are separate commitments and conflating them is what produces overpromising.

---

## 6. The triage protocol

**The problem:** he sends unplanned research 2–3× per week — Claude skills, API lists, frameworks,
articles. Historically each one either derailed a sprint or silently vanished. Both are bad, and the
second is worse because it looks fine until he asks about it six weeks later.

**The fix — every inbound gets a written verdict within 24 hours, in one of four buckets:**

| Bucket | Meaning | Reply pattern | SLA |
|---|---|---|---|
| **ADOPT** | Goes into the current or next sprint | "Adding as `S3-x`, lands *date*" | 24h |
| **BACKLOG** | Real value, wrong sequence | "Logged as `Bx`. Blocked on *thing*. Revisit *date*." | 24h |
| **EVALUATE** | Needs a timeboxed spike | "Spiking 4h on *date*, verdict after" | 24h + spike |
| **DECLINE** | Off-thesis or dominated | "Not doing this because *specific reason*" | 24h |

Three rules that make this work:

- **Never silently ignore.** He remembers. The PayPal Mafia list from 4 Aug resurfaced on 18 Aug.
- **Always state the trade.** *"I can add X, it moves Y by a week"* — he is a CEO, he trades. What he
  cannot do is evaluate a request he thinks is free.
- **Declining is allowed and it builds credibility.** He declined crypto himself, unprompted. He
  respects a reasoned no far more than a silent yes that never ships.

### 6.1 The backlog he thinks is still live

Send this in the next weekly note. These are logged asks with no status — the silent-drop risk.

| Ask | Date | Real status | Bucket |
|---|---|---|---|
| Claude finance skills (10 repos) | 6 Aug | Not evaluated | EVALUATE, 4h spike |
| Multi-agent frameworks (TradingAgents, FinRL, FinRobot) | 6 Aug | Not evaluated | EVALUATE — but note we already have `multi_agent_intelligence.py` |
| Cheap private-market APIs (15 options, priced) | 2 Aug | Not decided | **Needs his budget call — [D2](06-DECISION-LOG.md#d2)** |
| "Analyse founder articles, books, interviews" | 21 Jul | Partial (`founder_track_record_connector`) | BACKLOG → S3 Report v2 §7 |
| "Rumours of potential next steps" | 21 Jul | `rumors_analysis_connector` exists, unverified | BACKLOG → S3 verify |
| "Employee, personal, and company news" | 21 Jul | Partial | BACKLOG → S3 Report v2 §9 |
| "Contracts they have; probability of delivery" | 21 Jul | `contract_probability_service` exists, unverified | BACKLOG → S3 verify |
| "Market share for publicly traded, all data" | 21 Jul | Not built | BACKLOG → S3 Report v2 §4 |
| "Kimi swarm for every entity discovered" | 30 Jul | Superseded by recursion engine | DECLINE — explain the substitute |
| Government officials Excel (637 rows) | 18 Aug | **In progress S0-D** | ADOPT ✅ |
| bloomberg-terminal-free evaluation | 18 Aug | Evaluated, correctly declined | Closed ✅ |

Eleven items. Two resolved. **Nine have been sitting unacknowledged** — that is the actual
relationship risk in this project, not the delivery schedule.

---

## 7. The weekly note

Friday. Short. Same shape every week so he learns where to look.

```markdown
**Week of [dates] — Finance Intelligence Platform**

SHIPPED (click these)
· [artifact] — [one line on what is new] — [link]

THE TWO NUMBERS
· Real-data endpoints: 72% → 78%
· Field extraction depth, top 10 sources: 31% → 44%

FOUND THIS WEEK  ← he cares about this section most
· [a non-obvious correlation the engine surfaced, with its confidence tier]

YOUR ASKS, STATUS
· [ask] → ADOPT / BACKLOG / EVALUATE / DECLINE + date

NEEDS YOU
· [decision] — blocking [what] — needed by [date]

NEXT WEEK
· [3 bullets max]
```

Why this shape:

- **"Click these" first** — matches §4. He evaluates by looking, so lead with the thing to look at.
- **Two numbers only** — the two that answer his 18 Aug instruction. Not test counts, not feature
  counts. Never report a feature count to him again.
- **"Found this week" is the retention hook.** One genuine non-obvious finding per week is worth more
  than any status table. It is the product demonstrating its own thesis.
- **"Your asks, status"** — closes the §6.1 gap permanently.
- **"Needs you" with a date** — decisions do not arrive unless they have a deadline attached and a
  named consequence.

---

## 8. Mistakes I have made, so they are not repeated

Written plainly because the pattern matters more than the ego.

| # | Mistake | Cost | Rule now |
|:--:|---|---|---|
| 1 | Built the PayPal Mafia **report** instead of the **engine** | ~1 week | Named entity = capability request (§3.2) |
| 2 | Reported feature counts and test counts | Trust when 108% met "nothing works" | Report real-data % and extraction depth (§7) |
| 3 | Let mock data reach a CEO-visible surface | The 5 Aug incident | Mock ban, HTTP 503 with a reason (S0-C) |
| 4 | Framed reports as invest/don't-invest | Direct correction ×2 in 23 seconds | Intelligence, never advice (§3.1) |
| 5 | Left 9 asks unacknowledged | Latent, will surface | 24h triage on everything (§6) |
| 6 | Chased breadth — 44 connectors, shallow | Prompted *"research each source"* | Depth before breadth (S1) |
| 7 | Treated his links as reading material | Lost requirements | Every link → logged requirement ID (§3.4) |

---

## 9. Pocket card

```
   ┌───────────────────────────────────────────────────────────────┐
   │  BEFORE STARTING ANY TASK, ASK:                               │
   │                                                               │
   │  1. Does this trace money or a relationship?      no → stop   │
   │  2. Could a single API answer it?                yes → weak   │
   │  3. Will every claim carry evidence + a tier?     no → stop   │
   │  4. Is there a picture at the end of it?          no → weak   │
   │  5. Am I building the engine, or the example?  example → stop │
   │                                                               │
   │  HE WANTS:  depth · relationships · non-obvious · money ·     │
   │             visual · simple surface · cheap data              │
   │  HE DOESN'T: crypto · recommendations · feature counts ·      │
   │             breadth · one-off reports                         │
   └───────────────────────────────────────────────────────────────┘
```
