# Discovery Radar Review — Group B (2026-07-11)

Manual verbatim verification of 8 tickers flagged by the transcript discovery radar
(`backtest/results/2026-07-10_discovery_radar.md`) for constraint-language ("lead
times extending", "sold out", "capacity constrained", "pricing power", etc.)
appearing repeatedly in their **own** earnings-call transcripts, cross-checked
against `thesis/themes.yaml` for overlap with existing Phase-3 theses.

Cluster: MCHP, ASMLF, ASML, AVT, AMAT, ADI, VSH, FSLR (semiconductors / electronic
distribution / solar).

**Method**: `backtest/experiments/exp_discovery_radar_groupB_extract.py` queries
`thesis/corpus.db` (`docs_fts_en` FTS5 MATCH over the constraint-phrase list,
`primary_ticker`-scoped, `thesistype='transcript'`), then samples up to 8 matching
transcripts spread across each ticker's full available history (oldest → newest,
forcing in the 2 most recent quarters), and pulls ±220-char context windows around
every phrase hit (raw dump: `backtest/results/_scratch_groupB/<ticker>.txt`). Every
quote below was read in that wider context, not just the bare snippet, before
judging direction (structural own-voice bottleneck vs. generic/seasonal/victim-role
noise) — same discipline as the "trough" false-positive experiment from earlier
today (most "trough" matches turned out to be unrelated boilerplate like deal-cycle
or seasonality language).

**Verdict legend**: STRONG (clear, concrete, persistent structural bottleneck,
own-voice, no overlap → new thesis candidate) / FOLD (evidence real, but
conceptually belongs inside an existing theme) / WEAK (evidence thin, generic,
victim-role, or explicitly contradicted by the company's own words) / UNCLEAR
(real signal but too young / mixed / needs another data point before committing).

---

## MCHP (Microchip Technology) — UNCLEAR

**Sample quotes** (68 matching transcripts total, 2009–2026; company history shows
classic boom-bust semiconductor cyclicality, not a one-way structural story):

- 2021-05-06 (COVID chip shortage peak): *"...we're obviously not giving revenue
  guidance outside of the current quarter... As far as back end and front end, we
  have constraints in both internal and external factories... they're all
  constrained."* / *"PSP backlog is almost equal to 100% of capacity."* /
  *"...worked constructively with our supply chain partners to find creative
  solutions in a hyper constrained environment."* — genuine, but this is the
  well-known industry-wide 2021 shortage, already historical.
- 2023-08-03 (the very next up-cycle unwind, same company): *"We have been able to
  reduce average lead time from roughly 52 weeks at the start of 2023 to roughly 26
  weeks by the end of the June quarter, and we expect to continue to drive lead
  times down farther..."* — MCHP **deliberately compressed** its own lead times;
  proves the 2021 tightness was cyclical, not structural, and that MCHP does not
  hoard scarcity.
- 2026-02-05 (most recent -1): *"...lead times for our products have been four to
  eight weeks for some time, we are continuing to experience lead times bounce off
  the bottom, and we are experiencing increases on some of our products... the
  constraints are broadening even a run-of-the-mill foundry process..."* CEO Steve
  Sanghi also: *"high bandwidth memory is really constrained... NAND as well as the
  flash memory is very constrained... some of that shares capacity with our serial
  e-square business."*
- 2026-05-07 (most recent, CEO Steve Sanghi, very explicit): *"Capacity is tight...
  You're right... driven by AI, the DRAM capacity is very tight... The NOR flash got
  constrained, so some of the EEPROM manufacturers in Asia shifted their EEPROM
  capacity..."* / on pricing: *"...at least in some areas, we're starting to see
  some signs that pricing is moving higher... You know, in some cases, it's about
  the tight supply..."* / on lead times: *"lead time for our products have been 4-8
  weeks for some time, we are continuing to see lead times increase on many of our
  products. We're running into challenges on certain kinds of substrates and
  subcontracting..."* / *"...lead times are broadly expanding. I think in another
  quarter or so, there could be nothing available in 4 to 6 weeks."* / *"...probably
  70%, 80% of the process technology nodes are constrained... We are constrained on
  substrates... Is it impacting our data center business? Yes. Is it impacting our
  connectivity and networking and automotive business? Yes."*

**Judgment**: the most recent 2 quarters (Feb + May 2026) are unusually explicit,
detailed, and CEO-voiced — a real, differentiated signal (not boilerplate): legacy/
mature-node wafer capacity and substrates are getting squeezed as fabs prioritize
AI/HBM-driven advanced-node and memory output, spilling over into analog/MCU lead
times and pricing. This is corroborated by cross-checking ADI (same cluster, same
month, see below) which explicitly **denies** experiencing the same tightness —
ruling out generic industry-wide boilerplate as the explanation. But: (1) it is only
2 quarters old; (2) MCHP's own 2023 history shows it can unwind from "hyper
constrained" to actively slashing lead times within ~2 years; (3) the driver looks
like a second-order spillover from AI/HBM capacity allocation (memory-supercycle's
territory) rather than MCHP's own structural moat. Not enough of a track record yet
to call "persistent."

**themes.yaml overlap**: no existing theme covers analog/MCU (memory-supercycle =
DRAM/NAND owners MU/SNDK/WDC/SKHY; ai-power-grid = power semis ETN/MPWR/VICR/ON/TXN;
advanced-packaging = packaging materials/equipment). MCHP is genuinely a different
market segment (industrial/auto/aerospace-weighted analog+MCU, not HBM/AI-chip). No
overlap found.

**Verdict: UNCLEAR.** Real, detailed, differentiated, own-voice evidence of
renewed tightening in the last 2 quarters, but too young against a company with a
documented history of rapid cyclical reversal. Recommend re-checking after the
August 2026 print; if the tightening/pricing-power language persists a 3rd
consecutive quarter, upgrade toward STRONG (possibly as a new "legacy-node/analog
squeeze" theme, distinct from the existing AI-chip theses).

---

## ASML / ASMLF — STRONG (combined; same company, two share classes)

**Sample quotes** (72/71 matching transcripts, 2006–2026 — by far the longest and
most consistent history of the 8):

- 2010-01-20 (CEO Eric Meurice): *"...we are always constraining the business
  because our lead times are so enormous. So if you ask me... what is the natural
  need that does not constrain the real output, I think we are not far..."* — ASML
  management **explicitly stating they deliberately ration output** because their
  own lead times can't keep pace with demand — the clearest possible "we are the
  bottleneck" admission.
- 2017-01-18 (Peter Wennink, on EUV specifically): *"...we have currently, if you
  would – in 2016 we had 24-month lead time..."*
- 2019-07-17: *"...there is an order lead time which we give our customers about 18
  months... The lead time is 18 months. It was 24. We're driving it down..."*
- 2024-01-24: *"...for a number of tools, we're still supply constrained. So there
  you have to determine where is the tool going..."* + *"you're not expected to be
  capacity constrained, especially on the EUV side necessarily"* (nuanced — 2024 DUV
  softer, EUV still allocated).
- 2026-01-28 (R.J.M. Dassen, CFO): *"...what we've done, as you know, in the past
  couple of years is to put in what we call the long lead time items, which means
  that everything that takes, let's say, longer than 12, 18 months to realize is in
  place in order to get to a much higher volume."*
- 2026-04-15 (most recent): *"...creating a strong constraint in the end market from
  AI to mobile and PC. And as a result, our customers are strongly invited to create
  more capacity. So if we look at memory, what our customers tell us is that they
  are sold out for 2026 and their supply constraint will last beyond 2026."*

**Judgment**: this is the textbook case — ASML is the sole global supplier of EUV
lithography (no substitute exists), and management has used first-person
"constraining the business" / chronic 12-24-month order lead time / customer
"sold out" language consistently across 4 different industry cycles (2010 DRAM
boom, 2017 memory upcycle, 2021 chip shortage, 2024 recovery, 2026 AI-driven
memory/logic buildout) spanning 16 years. Two nuances worth flagging for the human
reviewer: (1) the 2026-04 "sold out" quote describes ASML's *customers* (memory
makers) being sold out, which is demand-pull evidence for ASML rather than ASML's
own scarcity in that specific sentence — but the surrounding 2026-01 quote shows
ASML itself pre-building "long lead time items" specifically to avoid being the
constraint, i.e., current lead times are "normal" (12-18mo) because ASML has
proactively invested ahead of demand — the moat is the chronic order-to-delivery
lead time + sole-supplier status itself, not an acute shortage; (2) pricing power is
inferred from monopoly structure + backlog, not a direct "we raised prices" quote in
the sampled set (ASML's own pricing power is well documented externally but wasn't
directly quoted here).

**themes.yaml overlap**: none of ASML/ASMLF appear in any `tickers:` list.
Conceptually distinct from advanced-packaging (post-fab packaging materials/
equipment: AMKR/ASX/TTMI/KLAC/LRCX/TER/FORM/KLIC) — ASML is front-end lithography,
a different chain link, and semicap-equipment (currently just AEHR, unrelated
burn-in-test niche). No overlap.

**Verdict: STRONG.** Clearest, longest, most consistent own-voice sole-supplier
structural bottleneck story of the batch. Recommend new thesis (or fold as the
anchor name of a new "EUV/semicap monopoly" theme) covering both ASML and ASMLF as
one ticker economically.

---

## AVT (Avnet) — UNCLEAR

**Sample quotes** (57 matching transcripts, 2007–2026):

- 2013-08-07: *"the environment of relatively short and stable lead times... has led
  to some competitive pricing pressure"* — short lead times were **bad** for AVT
  (pricing pressure), the inverse of a scarcity-benefits-me story.
- 2022-04-27 (chip-shortage era): *"Lead times remain consistently extended at this
  point in time... there's no real indication of lead times coming in."*
- 2024-05-01 (bust that followed): *"customers are facing... elevated inventory
  levels, some cash flow constraints, diminished customer visibility, and shortened
  lead times. These market conditions are among the most challenging in recent
  memory."* — AVT itself badly hurt by the destocking bust, confirming this
  business is highly cyclical/volatile, not a clean structural moat.
- 2026-01-28 (most recent -1): *"Demand signals continue to reset globally,
  resulting in lead times trending higher across most product categories. This
  trend is still largely driven by the data center, artificial intelligence, but is
  also broadening..."* / *"We're also seeing an increasing number of customer
  orders being placed within lead times, along with higher instances of deliveries
  beyond lead times. These factors are driving a mismatch... This creates
  opportunity for us..."*
- 2026-04-29 (most recent): *"You mentioned longer lead times are spreading across
  more of the portfolio. I know IP&E has had some tightness for quite some time and
  then some of the memory or storage stuff... it's mostly memory right now...
  discrete a tad, analog is about flat to up a tad... storage is going to up and
  that's going to be tied to memory..."* / *"Over the past 90 days... component
  lead time trends are increasing across many product categories. We have seen lead
  time extensions in over 50% of the product categories we track... While lead time
  extensions continue in components supporting data center and AI builds, they are
  now spreading [to] the broader set of products..."*

**Judgment**: the 2 most recent quarters are genuinely detailed and consistent —
AVT (an electronics distributor, not a component maker) is describing a real,
broadening, AI/data-center-driven lead-time extension across >50% of tracked
product categories, memory-led but spreading. This is credible evidence of an
emerging "chip shortage 2.0," and as a distributor AVT can capture margin/allocation
value during such cycles. But two things hold this back from STRONG: (1) AVT's own
history (2013, 2024 quotes above) shows the distributor's economics are volatile in
*both* directions — short lead times hurt them via pricing pressure, and the 2024
destocking bust was described as "among the most challenging in recent memory" —
this is a pass-through intermediary, not a scarcity-owner with durable pricing
power; (2) only 2 quarters of the current upswing sampled. The signal is real but
the vehicle (distributor economics) is structurally weaker/more volatile than an
owner of the scarce resource.

**themes.yaml overlap**: no existing theme covers electronic component
distribution. No direct overlap, but AVT is essentially re-observing the *same*
underlying AI-capex-driven component tightness that memory-supercycle /
ai-power-grid already capture from the producer side — AVT would be a
distribution-channel *expression* of that same macro theme rather than an
independent bottleneck.

**Verdict: UNCLEAR.** Real and current, but (a) too young (2 quarters), (b)
distributor economics are inherently more volatile/pass-through than a true
bottleneck owner, (c) may be better paired with ARW (flagged in the same radar
batch, Group A, also a distributor showing the same lead-time language) as a joint
"chip-shortage-2.0 distribution" watch item rather than a standalone thesis.
Recommend re-checking after Q3 2026 prints.

---

## AMAT (Applied Materials) — WEAK

**Sample quotes** (58 matching transcripts, 2006–2026):

- 2019-02-14: *"logic customers are buying EUV systems. And those systems have very
  long lead times... While this represents a market share headwind for Applied in
  both 2018 and 2019..."* — this is about **ASML's** EUV lead times crowding out
  AMAT's deposition/etch spend — a headwind for AMAT, not AMAT's own bottleneck.
- 2021-11-18 (chip shortage): *"we were unable to fully meet demand in our fourth
  quarter due to component shortages, and we expect to remain supply constrained
  going into fiscal 2022... Without these supply shortages, we estimate that our Q4
  revenues would have been at least $300 million higher."* — AMAT here is the
  **victim** of upstream component shortages limiting its own ability to build and
  ship tools, not a beneficiary with pricing power over customers.
- 2026-02-12 (most recent -1, Brice Hill, CFO): *"Lead times are improving as we
  qualify additional suppliers and streamline our operations."* / *"These actions
  improve resiliency, reduce lead times..."* — AMAT explicitly says its own lead
  times are **getting better/shorter**, the opposite direction from a tightening
  bottleneck story.
- 2026-05-14 (most recent): capacity/lead-time discussion is entirely about
  customer fabs' own capacity ("how full is it," "clean rooms become more
  available") and AMAT's supply-chain planning cadence with its 2,000 direct
  suppliers — not AMAT's product being scarce to its customers.

**Judgment**: across the full sample, AMAT's own constraint language is either (a)
about a competitor's product (ASML/EUV) being the scarce one, (b) AMAT being the
victim of upstream shortages limiting its own output, or (c) most recently, AMAT
explicitly stating its lead times are improving. No own-voice evidence found of AMAT
itself being a scarcity-with-pricing-power story. "Long-term agreement" hits (2019,
2021) refer to AMAT's services/subscription revenue model, unrelated to supply
constraint.

**themes.yaml overlap**: semicap equipment sector is adjacent to advanced-packaging
(KLAC/LRCX/TER/FORM are equipment names in that theme) but AMAT is not in it and the
evidence here doesn't support adding it — this is a WEAK verdict on the merits, not
an overlap-driven FOLD.

**Verdict: WEAK.** No credible own-voice evidence of AMAT itself being
supply-constrained-with-pricing-power; evidence found either describes AMAT as
victim of shortages or points to a competitor's (ASML's) constraint. Not
recommended.

---

## ADI (Analog Devices) — WEAK

*(Special note: ADI was previously evaluated and rejected from the ai-power-grid
theme because the only evidence found was in a third-party summary table, not
ADI's own transcript — see `themes.yaml` ai-power-grid note. This review used direct
FTS search of ADI's own transcripts (55 quarters / 570 raw matches per the radar)
specifically to re-test that rejection on a stronger evidentiary basis.)*

**Sample quotes** (58 matching transcripts, 2006–2026):

- 2011-08-17: *"...suppliers like ADI, who had consistently short lead times..."* /
  *"We believe we can respond rapidly if the demand pattern improves and we intend
  to keep our lead times very short as we have in the last few years."* / *"we
  really run the company around the lead times. So we're going to make sure that
  the lead times stay low..."* — ADI explicitly describes deliberately keeping lead
  times **short** as a strategic choice, the opposite of exploiting scarcity.
- 2017-05-31: *"we're delivering the vast majority of our products within our
  stated lead times of 4 to 6 weeks. That frankly hasn't changed all that much...
  I guess what I would tell you is, at ADI, we're very focused on providing the
  highest levels of customer service..."*
- 2023-02-15 (post chip-shortage unwind): *"These actions have reduced our lead
  times with half of our portfolio now shipping in under 13 weeks... the
  supply-demand imbalance is definitely getting better..."*
- 2025-11-25: *"...most of our products have lead times sub-13 weeks. So we get a
  lot of orders in quarter... short lead time orders, visibility tends to be pretty
  low right now."* — short lead times here are actually a **headwind** to forecast
  visibility, not a moat.
- 2026-05-20 (most recent, CEO): *"...around the choke points in the semiconductor
  supply chain, memory being one of those. That's, I think, having most effect on
  consumer customers... generally speaking, **our lead times are in pretty good
  shape**. Our demand book is increasing. We've a lot more capacity as well than we
  had, say, pre the COVID cycle. **We've more than doubled the internal capacity**,
  and we've a lot more optionality built in..."*

**Judgment**: this is a clean, decisive negative. ADI's own management, across 15
years and in its single most recent (2026-05) transcript, explicitly (a) names
*memory* as the sector's choke point while (b) stating ADI's own lead times are
"in pretty good shape," and (c) attributes this to having deliberately more-than-
doubled internal capacity since COVID specifically to avoid being capacity-limited.
The high raw match count (570) is confirmed here to be mostly boilerplate/routine
lead-time commentary — often in the direction of ADI *actively avoiding* a
constrained posture as a customer-service differentiator, not evidence of a
bottleneck. This is a good illustration of why match count is not a signal-strength
proxy (same lesson as today's "trough" experiment).

**themes.yaml overlap**: confirms the existing ai-power-grid note's prior rejection
of ADI ("原始逐字引句冇點名,同CIEN一樣係推論非證據"). This review, using ADI's own
verbatim transcript text (a stronger evidence bar than that prior check), finds
active, current, first-person evidence **against** the constraint thesis, not just
absence of evidence for it.

**Verdict: WEAK.** Re-confirms and strengthens the prior rejection. Not just
insufficient evidence — direct contradicting evidence from ADI's own CEO in the most
recent quarter.

---

## VSH (Vishay Intertechnology) — WEAK

**Sample quotes** (58 matching transcripts, 2007–2026):

- 2010-05-05 (post-GFC snapback, genuine): *"There are shortages of supply and
  continuously increasing lead times... extremely long lead times these days for
  MOSFET, due to broad capacity allocation limitations..."* / *"I think like
  everybody at the moment in MOSFET, all of us could sell more if we could make
  more"* — real, but explicitly framed as an industry-wide ("all of us") condition,
  not a VSH-specific moat.
- 2017-10-26: *"stretched lead times for many product lines, in particular, for
  power inductors and resistor chips... Perceived shortages of supply continue to
  drive orders..."*
- 2026-02-04 (most recent -1): *"Order intake grew because of the increased
  production of AI servers and extended component lead times across the industry. A
  number of customers are actively adding Vishay to the bill of materials in
  AI-related applications..."* — this reads as a genuine *demand/design-win* story
  (share gains) more than a supply-constrained-pricing-power story.
- 2026-05-13 (most recent, the key quote): *"Historically, at this point in the
  business upcycle, much of Vishay 2.0 capacity would have been sold out on
  allocation and with lead times longer than 1 year. **Because it took too long to
  fulfill orders, Vishay missed repeat opportunities, and we were no longer a
  reliable supplier to the customers.** Today, as the market upcy[cle continues]..."*
  / *"We have no intention of backsliding to the business approach of Vishay
  2.0."* / *"...it's about quick delivery now, who has competitive or leading lead
  times and product ready to go."*

**Judgment**: this is the most explicit anti-thesis quote in the entire batch.
VSH's own current management directly states that, historically, being "sold out on
allocation" with >1-year lead times **lost them customers** and reliability
reputation, and that their current "Vishay 3.0" strategy is explicitly designed to
avoid recreating that pattern — competing instead on being the fast, reliable,
available supplier. This is close to the inverse of the Objective-B "beneficiary of
its own scarcity" framing. There is real AI-driven demand growth (design wins in AI
servers/power management), which is a legitimate positive but is a volume-share
story, not a pricing-power-from-scarcity story.

**themes.yaml overlap**: VSH (MOSFETs/passives, some power-management exposure) is
conceptually adjacent to ai-power-grid (MPWR/VICR/ON/TXN power semis), but the
evidence here doesn't clear the bar to justify adding it even there — management's
own words argue against the constraint framing.

**Verdict: WEAK.** Real AI-driven demand growth exists, but management explicitly
disclaims the scarcity/pricing-power framing as a past mistake they are avoiding.
Not recommended, at least not on the "supply-constrained beneficiary" framing this
review is testing for.

---

## FSLR (First Solar) — STRONG

**Sample quotes** (60 matching transcripts, 2007–2026):

- 2016-04-27 (important negative control, shows this isn't a permanent given):
  CFO explicitly: *"...I wouldn't say we have pricing power but we have that
  ability to optimize."* — FSLR itself denied having pricing power in 2016 (mid
  solar downcycle / Chinese oversupply period), confirming the current tightness is
  a real regime change, not always-on marketing language.
- 2019-05-02: *"we are largely sold out through the end of 2020. With the current
  bookings now 50% of the anticipated Q1 2021 supply has been booked."* / *"We can
  be selective; we can engage with customers, we can make decisions on where to
  walk away. We're not being held by volume..."* — explicit pricing-leverage
  language (can walk away from unfavorable deals).
- 2021-07-29: *"we are largely sold out for 2021 and 2022, have 3.4 gigawatts of
  planned deliveries in 2023 and 4 and 5 gigawatts in 2024."* / *"we continue to
  book out... we are still somewhat capacity constrained even with the 2 new
  factories... we are capacity constrained from that standpoint."*
- 2023-10-31: *"Our contracted backlog extends into 2030, and excluding India, we
  are sold out through 2026."* / *"We are still supply constrained and we have a
  road map that will get us to 25 gigawatts."*
- 2026-02-24 (most recent -1, confirms the 2023 forward claim held true 2+ years
  later): *"We entered 2026 with a fully allocated position for our U.S.
  production."*
- 2026-04-30 (most recent): U.S. production still running "at full capacity
  end-to-end"; only the *international* (Malaysia/Vietnam) Series 6 capacity is
  under-utilized (~20%) and "remains constrained" **on the demand side** due to
  tariff policy — i.e., the scarcity is specifically in FSLR's tariff-protected
  U.S. manufacturing footprint, not global.

**Judgment**: the strongest, most durable, most quantified evidence in the batch.
FSLR has been progressively selling out further into the future for 7+ consecutive
years (2019: sold out through 2020 → 2021: sold out through 2022 with bookings into
2024 → 2023: sold out through 2026 with backlog to 2030 → 2026: confirms "fully
allocated" for the year, exactly as forecast 2+ years earlier). This is not a
generic component-lead-time story; it's a company that can name specific
counterparties, specific gigawatt volumes, specific years, and can walk away from
bad deals. Crucially, the bottleneck is reinforced by U.S. trade policy (Section
201/232/301 tariffs + IRA domestic-content incentives), which is a **durable, policy
moat**, distinct from a cyclical semiconductor shortage — the 2016 "no pricing
power" quote is useful evidence that FSLR's management does NOT reflexively claim
scarcity, making the 2019-2026 sold-out run more credible as a genuine regime
change rather than boilerplate.

**themes.yaml overlap**: no existing theme touches solar/PV manufacturing or U.S.
industrial/trade policy moats. Zero overlap — this is a genuinely new sector for the
thesis registry.

**Verdict: STRONG.** Longest, most quantified, most consistently-confirmed
structural bottleneck in the batch, reinforced by a durable trade-policy moat.
Recommend new thesis. Kill condition to build in: a rollback/exemption of the
Section 232/301 solar tariffs or IRA domestic-content rules would reopen FSLR's
U.S. market to Chinese/SE-Asian competition and could collapse the "sold
out"/"fully allocated" pricing power quickly (cf. the 2016 quote showing this
company has been in a no-pricing-power regime before).

---

## Summary table

| ticker | verdict | one-line reason |
|---|---|---|
| MCHP | UNCLEAR | Real, detailed, CEO-voiced tightening (foundry/substrate spillover from AI/HBM) in the last 2 quarters, corroborated by ADI's contrasting denial in the same period — but only 2 quarters old vs. a company with a documented history of fast cyclical reversal (52→26wk lead-time cut in 2023 alone). |
| ASMLF / ASML | STRONG | Sole global EUV supplier; 16 years of consistent first-person "we constrain the business" / 12-24mo order lead-time / customer-sold-out language across 4 cycles; zero thematic overlap. Combine as one write-up. |
| AVT | UNCLEAR | Detailed, current (2 most recent quarters) evidence of broadening AI-driven lead-time extension across >50% of tracked categories — but a distributor's pass-through economics are structurally more volatile than a true bottleneck-owner (own 2024 quotes show a brutal destocking bust), and it's largely re-observing the same AI-capex tightness memory-supercycle/ai-power-grid already cover. |
| AMAT | WEAK | Own constraint language found is either about a competitor's (ASML's) lead times crowding out AMAT's spend, or AMAT itself as *victim* of upstream shortages (2021); most recent (2026) quotes say AMAT's own lead times are improving. |
| ADI | WEAK | Direct contradicting evidence: 15 years of ADI explicitly choosing short lead times as a service differentiator, and its own May-2026 CEO quote names *memory* as the industry choke point while stating ADI's own lead times are "in pretty good shape" after more-than-doubling internal capacity since COVID. Reaffirms the prior themes.yaml rejection on stronger evidence. |
| VSH | WEAK | Most explicit anti-thesis quote of the batch: management says being "sold out on allocation" with >1yr lead times in the last upcycle (Vishay 2.0) *lost* them customers, and their current strategy explicitly avoids repeating that; real AI-driven demand exists but it's a share-gain story, not a scarcity/pricing-power story. |
| FSLR | STRONG | 7+ consecutive years of progressively-further-forward "sold out"/"fully allocated" language (sold out through 2020 → 2022 → 2026, backlog to 2030), reinforced by a durable U.S. tariff/IRA policy moat; a 2016 explicit "no pricing power" quote confirms this isn't reflexive language. Zero overlap — new sector for the thesis registry (solar/PV, US industrial policy). |
