# Finance Intelligence Platform — Plan to 2 November

**For:** James Deller · **From:** Anshuman · **19 August 2026**

---

## What you asked for, in one line

> A system that follows the money, goes deeper into every entity it finds, surfaces connections
> nobody else has spotted — and shows it as a picture you can forward.

That is what your messages since 21 July add up to. This plan builds that, in that order.

---

## Where we actually are

We have 44 data connectors, 75 pages and 89 services. That is real work, and it is the wrong shape.

**Your 18 August message was the correct diagnosis:** *"There is a lot of data there. You really need
to research each source."*

Here is what we found when we checked:

| | |
|---|---|
| Data sources connected | ~33 real intelligence sources (the "48" included Stripe, SendGrid, Twilio and similar — those are plumbing, not data) |
| **Of the 10 most valuable sources, how much of their data we actually extract** | **under one third** |
| Entity relationship graph — the thing that makes recursion possible | **does not exist yet** |
| Endpoints returning verified live data | ~60% |

The gap is not features. It is **depth and proof.**

Concrete example, and it is the one that stung: you have asked four times about families, wives,
holding companies and trusts. Public companies are **legally required** to disclose exactly that in
their annual proxy statement. We parse those proxies for board names and skip the section that
answers your question. That is a one-week fix to a six-week-old request, and it is representative of
what the next two weeks are for.

---

## The plan — six sprints

Every sprint ends with one thing you can click or forward.

| | Dates | What we build | **What you get** |
|:--:|---|---|---|
| **1** | 19–24 Aug | Fix trust: every link works or honestly says "no data" | **Government trading leaderboards live** — your 637-official spreadsheet, ranked by trades, volume, ROI vs S&P |
| **2** | 25 Aug – 7 Sep | Research all 33 sources properly. Extract what we are leaving behind | **Source depth report** + deeper extraction demo |
| **3** | 8–21 Sep | Build the relationship graph and the recursion engine | **PayPal Mafia network, 3 levels deep, ~500 entities — every single connection citing its source document** |
| **4** | 22 Sep – 5 Oct | Find non-obvious correlations. Prove every claim | **NVIDIA intelligence report v2 — 25 sections, every fact tagged Confirmed / Reported / Inferred / Speculative** |
| **5** | 6–19 Oct | Make it look like a finance product | **Dark blue UI + money-flow visualization** in the style of that WSJ Trump-family piece you sent |
| **6** | 20 Oct – 2 Nov | Private-market data, final audits | **Cap-table and funding-round data layer** |

Three people, three parallel tracks throughout: one making the data deeper, one making it visible,
one making it provable.

---

## One change I am making to how I report to you

I have been telling you things like *"78 of 72 features complete, 1183 tests passing."* Those numbers
were true and they were useless — three days after one of those reports you opened the site and
nothing worked.

**I am retiring the feature count.** From now on you get two numbers:

| | Today | Target 2 Nov |
|---|:--:|:--:|
| **Endpoints serving verified live data** | ~60% | **95%** |
| **How much of each source's data we extract** (top 10) | ~25% | **85%** |

Those two numbers are the direct answer to the thing you asked for. They can only go up by doing the
research you asked for, and they cannot be gamed by shipping more features.

---

## The one thing I want to add that you have not asked for

Every relationship the system asserts will carry its evidence: which document, what date, how
confident, and if two sources disagree we show you both instead of silently picking one.

Two reasons this is worth the time:

1. **It is the moat.** Anyone can join public datasets and draw a network diagram. Almost nobody will
   do the work to say how confident they are. Accuracy is the #1 buying criterion in this market at
   87%, ahead of price.
2. **It is the difference between an intelligence product and a lawsuit.** We are asserting
   relationships between named, powerful private individuals. "Thiel invested in X, whose employee
   worked at Y" must never render as "Thiel is connected to Y" without evidence attached. Cheap to
   build now, impossible to fix after publication.

---

## Four decisions I need from you

Dates attached because each one blocks something specific.

| | Decision | Needed by | My recommendation |
|:--:|---|:--:|---|
| **1** | **Recursion depth budget.** Going deeper costs money: depth 3 ≈ $95 per run, depth 4 ≈ $1,150, depth 5 ≈ $13,800. | **1 Sep** | Depth 3 default, $500/mo ceiling. You can buy more depth any time — I just need a number I am allowed to spend. |
| **2** | **LinkedIn.** Our connector violates their terms and breaks constantly. People Data Labs does the same job legally for ~$98/mo. | **1 Sep** | Delete ours, buy theirs. Removes a legal risk and fills a gap in one line item. |
| **3** | **Private-market data.** From your own list: Fundable + People Data Labs ≈ $150–250/mo. Caplight for cap tables, quote-based. | **6 Oct** | Yes, but from sprint 6 — after we have extracted the free data we are already sitting on. Your instinct on 2 Aug was right; I have just put a sequence on it. |
| **4** | **Advisors and research teams — target segment or not?** 11 features worth either a lot or exactly zero. One of them changes the database schema, so it gets expensive if decided late. | **13 Oct** | Not yet. Revisit after first paying customers. I will reserve the schema shape so saying yes later stays cheap. |

---

## What I got wrong

Worth saying directly, because the corrections are already in the plan.

- I built the **PayPal Mafia report** when you were asking for the **engine** that produces reports
  like it, for any group. Cost about a week. Sprint 3 builds the engine.
- I reported feature counts instead of whether things actually worked. Fixed above.
- Mock data reached a page you clicked. Sprint 1 makes that structurally impossible — an endpoint
  with no real data now returns a visible "no data" state, never a number.
- Nine things you sent me have no status from me. They are all triaged now, and from this week
  everything you send gets a written yes / no / when within 24 hours.

---

## Friday

Government trading leaderboards, live, on your own data. 30 minutes to walk you through it.

*Detail behind this summary: [program plan](02-PROGRAM-PLAN.md) · [source register](05-SOURCE-DEPTH-REGISTER.md) · [audit playbook](04-VERIFICATION-AUDIT-PLAYBOOK.md) · [decision log](06-DECISION-LOG.md)*
