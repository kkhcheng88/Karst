# Discovery Radar Review — Group D (Homebuilders / Real Estate / Other Industrials)

Reviewer scope: LEN, LEN-B, TOL, FSS, IIIN, LPX, MHK, EQR, AVB, ESS, WST.

Method: for each ticker, FTS5-matched `thesis/corpus.db` transcripts against the constraint-phrase
list (`sold out`, `on allocation`, `fully allocated`, `supply constrained`, `capacity constrained`,
`at capacity`, `tight supply`, `supply is tight`, `lead time(s)`, `supply shortage`, `unable to meet
demand`, `demand exceeds supply`, `outstripping supply`, `take or pay`, `long-term agreement`,
`pricing power`, `constrained`), pulled an 8-quarter time-spread sample (full date range, not just
recent quarters) with ~220-char context windows around each hit
(`backtest/experiments/exp_groupD_constraint_context.py` →
`backtest/results/_scratch_groupD/<ticker>.txt`), then for tickers with a promising thread, drilled
into 2024-2026 quarters specifically to check whether the signal is *current* (not just a legacy/
resolved episode). Cross-checked every surviving candidate against `thesis/themes.yaml` (9 existing
themes, all AI-capex/semiconductor/space/rare-earth/energy — none touch housing, building materials,
REITs, or pharma packaging, so no theme-overlap risk for this cluster a priori).

---

## LEN / LEN-B (Lennar) — WEAK

LEN and LEN-B are the same company (Class A / Class B shares); `corpus.db` stores byte-identical
transcript text under both tickers (verified: `transcript-LEN-2008-06-26` and
`transcript-LEN-B-2008-06-26` etc. are textually identical). Discussed once here for both.

Sampled 8 quarters spanning 2008-06-26 to 2026-06-12 (65 matching transcripts total, full range
2008–2026).

Representative quotes:
- 2008-06-26: *"…right now we are in what I call a price taker business **with no pricing power**."* — explicit denial.
- 2012-03-27: *"…demand still remains **constrained** or is being held back by the mortgage qualification standards…"* — demand-side macro constraint (mortgage credit), not LEN's own product/capacity.
- 2014-06-26: *"…supplies remain **constrained** to meet that demand… production deficit of both single and multifamily dwellings…"* — the generic "chronic housing underproduction" macro narrative.
- 2016-09-20 / 2019-06-25 / 2021-12-16: repeated variations of "land constrained," "labor constrained," "mortgage-constrained" — cost/input-side headwinds, not LEN's own product being the scarce good.
- 2024-03-14: *"…along with the **supply shortage**, the additional limiting factor continues to center around affordability…"* — same 15-year-old macro talking point, phrased almost identically to how it was phrased in 2014 and 2019.
- 2026-06-12 (most recent transcript in corpus): **zero** constraint-phrase hits.

Judgment: This is exactly the "supply-constrained housing" macro narrative flagged in the brief as a
decade-plus-old, well-worn storyline — LEN has been repeating some version of "chronic housing
underproduction" continuously since ~2012–2014, i.e., it is not a new discovery, it's baseline
messaging. Critically, LEN is *not* describing itself as a beneficiary with pricing power in most of
these quotes — it repeatedly describes itself as *constrained by inputs* (land, labor, mortgage
credit/rates) that hurt its own volumes, and in 2008 explicitly denies having pricing power. The most
recent transcript (2026-06-12) has no constraint-language hits at all, suggesting the narrative isn't
even currently prominent in LEN's own framing. themes.yaml overlap: none (no housing theme exists).

**Verdict: WEAK** — old macro narrative, not a fresh signal, mixed self-description (often
input-constrained/victim, not output-constrained/beneficiary), fading in latest transcript.

---

## TOL (Toll Brothers) — WEAK

Sampled 8 quarters spanning 2006-12-05 to 2026-02-18 (58 matching transcripts, full range 2006–2026).

Representative quotes:
- 2013-05-22: *"…I wouldn't say that our prices went up because of **pricing power** in last 2 years…"* — CEO explicitly disclaiming that margin gains reflect pricing power (attributes it to land appreciation instead).
- 2015-08-25: *"…We continue to have terrific **pricing power**. We manage pricing weekly…"* — genuinely bullish, but single-quarter, luxury-market-specific (peak of a local cycle).
- 2017-12-05: *"…the small number of month's supply of new home… remains **constrained**… This shortage plays to our advantage…"* — again the generic macro-shortage narrative.
- 2020-08-26 / 2022-08-24: *"tight supply"* — same macro narrative repeated through COVID cycle.
- 2026-02-18 (latest): *"…there's still **pricing power**. It's relatively limited… 30% to 40%... range of where we saw some price increases"* — soft, hedged, not a strong current claim.

Judgment: Same pattern as LEN — TOL is a luxury/move-up homebuilder riding the same well-known
"decade of housing underproduction" macro story. Pricing-power claims oscillate with the local cycle
(strong in 2015, explicitly denied in 2013, "relatively limited" in the most recent 2026 quarter).
No distinctive company-specific bottleneck beyond the generic industry narrative. themes.yaml
overlap: none.

**Verdict: WEAK** — same old macro housing-shortage narrative as LEN; current-quarter pricing power
explicitly described as "relatively limited."

---

## FSS (Federal Signal) — WEAK

Sampled 8 quarters spanning 2008-03-10 to 2026-04-29 (54 matching transcripts).

Representative quotes:
- 2008-03-10: *"Bronto is now **sold out** for 2008…"* — genuine beneficiary quote, but one-off, 18 years old.
- 2018-11-11 / 2020-07-29: *"lead times for certain product lines extended"* — demand-side strength on FSS's own vacuum-truck/fire-truck products (plausible beneficiary signal at the time).
- 2022-07-27: *"For our Vactor, Elgin, MRL businesses, we have — we're **on allocation**."* — but this is FSS **as the customer** being allocated *chassis* by third-party truck-chassis suppliers (a victim-role constraint on FSS's own production), not FSS's own product being scarce to its customers.
- 2024-04-30: *"…pent-up replacement demand as **chassis supply shortages** have weighed on demand last year…"* — again FSS describing itself as hurt by an upstream (chassis) shortage, not benefiting from one.
- 2024-04-30 / 2026-04-29 (most recent two transcripts, 41 combined hits): the dominant, repeated theme is FSS **actively reducing** its own lead times as an announced operational-execution win ("continue to focus on increasing production levels... to reduce backlog and lead times," "decreasing lead times across vacuum trucks and street sweepers... driven by our successful execution").

Judgment: FSS's own product lead times were extending 2018–2022 (plausible genuine signal at the
time), but the two most recent transcripts (2024, 2026) explicitly frame **shrinking** lead times as
good news — i.e., FSS's own capacity has caught up with demand, the opposite of a current bottleneck
claim. The other recurring theme (chassis allocation) is FSS in the *victim* role, not the
beneficiary role the brief warns against conflating. No current, self-described "we can't keep up
with demand for our own product" narrative. themes.yaml overlap: none.

**Verdict: WEAK** — mixed victim/beneficiary roles; the current (2024–2026) narrative is explicitly
about *reducing* lead times, which contradicts an active-bottleneck thesis.

---

## IIIN (Insteel Industries) — WEAK

Sampled 8 quarters spanning 2008-07-18 to 2026-04-16 (52 matching transcripts).

Representative quotes:
- 2008-07-18: *"The primary driver of the extraordinary **pricing power** possessed by **our suppliers**…"* / *"…we are clearly still **on allocation**…"* — IIIN describing itself as the victim of its wire-rod suppliers' pricing power / allocation, i.e., exactly the victim-role trap the brief warns about, not the beneficiary role.
- 2012-10-18: *"We really have not seen that [pricing power]… I'm not so sure that we were going to have a whole lot of **pricing power** in this market… Insteel operating below 50% capacity…"* — explicit denial, plus evidence of chronic *excess* capacity (the opposite of a bottleneck).
- 2015-01-15 / 2022-01-20 / 2024-04-25: repeated hedged, conditional language ("if strength continues... then we develop just a little more pricing power," "we don't have the backlog to be able to tell you that's going to happen").
- 2026-04-16 (latest): *"…we had staffed up… in anticipation of expanding operating hours, which would reduce lead times… but were unable to operate at expected levels."* — an execution/operational miss, not a demand-outstrips-supply signal.
- 2025-01-16 (recency check, not in original 8-quarter sample): *"…the **tight supply** condition right now is related to the **supply of wire rod**, it is not driven by outstanding demand for wire rod among wire products producers."* — management explicitly clarifies the tightness is in their input (wire rod, bought from suppliers), not in IIIN's own finished product; confirms the victim-role pattern seen in 2008.

Judgment: Across 18 years of sampled transcripts, IIIN never makes a clean, current, self-described
"we are supply-constrained and have pricing power" claim — the closest analogues are either explicit
denials, hedged conditionals, or IIIN describing itself as the victim of upstream supplier allocation.
This looks like a keyword false-positive: the discovery radar likely flagged IIIN because "pricing
power" appears frequently in analyst Q&A (the question is asked almost every call), not because IIIN
asserts it has pricing power. themes.yaml overlap: none.

**Verdict: WEAK** — no clean beneficiary-role evidence in 18 years of sampled transcripts; repeated
explicit denials of pricing power; "on allocation" instance is IIIN as victim, not beneficiary.

---

## LPX (Louisiana-Pacific) — STRONG

Sampled 8 quarters spanning 2007-10-29 to 2026-05-06 (49 matching transcripts), then drilled into
all 9 quarters from 2024-02-14 through 2026-05-06 to check currency of the signal.

Two distinct businesses show up in the transcripts with opposite current dynamics:

**Commodity OSB (weak/irrelevant to this thesis):** 2015–2017 and COVID-era (2020–2023) transcripts
show genuine historical capacity tightness (*"we're putting customers **on allocation**,"* 2017-05-05;
*"during COVID, being on allocation for all of two years… we were **sold out**,"* 2023-11-01), but the
**current** (2026-05-06) transcript is explicit that OSB is now oversupplied and weak: *"OSB price
softness accounted for a $66 million reduction in net sales and EBITDA… fell below EBITDA break
even for Q4 of last year and Q1 of this year."* This leg does **not** support a current bottleneck
thesis.

**Siding / SmartSide / ExpertFinish (the live signal):** Starting in 2024, LPX pivots its own framing
to a value-added, premium-priced siding franchise with a distinct and *repeated, currently-active*
pricing-power claim, tied explicitly to product differentiation and share gains versus vinyl siding
(not to the generic "housing shortage" macro story):
- 2024-05-08: *"Nearly 30% cumulative Siding revenue growth over a period [in] which the underlying market contracted clearly demonstrates **pricing power** and share gains…"*
- 2025-02-19: *"…the cost of the projects go up, but the returns stay very healthy because we've got **pricing power** for specialized products that we're producing at those mills."*
- 2025-05-06: *"…despite tariff-induced market volatility, it was a solid quarter for **pricing power**, growth, share gains, operating leverage…"*
- 2025-08-06: *"…highlights the value of Siding's consistent growth, **pricing power**, and margin expansion through operating leverage."*
- 2026-02-17: *"LP SmartSide has consistently gained share with innovative products that expand the addressable market. That growth, coupled with the **pricing power** that comes with a premium specialty product…"*
- 2026-05-06 (latest, most direct): *"The **pricing power** of SmartSide helped offset lower sales volume, moderating revenue declines"* [amid the OSB collapse].

"pricing power" appears in **7 of the last 9 quarterly transcripts** (2024-05 through 2026-05),
essentially every quarter, always attributed specifically to the Siding/SmartSide franchise's premium
positioning — a much higher hit-rate and much more specific attribution than the generic housing
commentary seen in LEN/TOL/MHK.

**The clincher — an actual, recent, named allocation event:** on the 2026-05-06 call, an analyst asks
whether flat ExpertFinish (LPX's specialty pre-finished-siding coating line) volume is a capacity
issue; management confirms: *"We are still dealing with a little bit of the ExpertFinish **allocation**
hangover… We came off allocation… in February-ish… channel inventories… are a little bit higher than
where we would like them to be, which isn't uncommon when you come off of a managed order file."*
I.e., ExpertFinish was literally on a managed-allocation order file through ~January 2026 — a genuine,
current, self-described capacity bottleneck on LPX's own differentiated product, not a
supplier-victim story and not a stale macro narrative.

Judgment: This is a real, current, structurally-differentiated (premium/proprietary product mix-shift
away from commodity OSB into higher-margin, share-gaining, recently-allocation-constrained Siding
products) signal, self-described by management in nearly every recent quarter, distinct from the
generic "housing is supply constrained" narrative that sank LEN/TOL. themes.yaml overlap: none — no
existing theme touches building products / siding.

**Verdict: STRONG** — recommend a new thesis around LPX's OSB→value-added-Siding mix shift
(SmartSide/ExpertFinish premium-product pricing power + a real, recent allocation/capacity event),
explicitly *not* the commodity-OSB or generic-housing-shortage story.

---

## MHK (Mohawk Industries) — WEAK

Sampled 8 quarters spanning 2008-04-20 to 2026-05-01 (50 matching transcripts), then checked all 10
quarters from 2024-02-09 through 2026-05-01 for currency.

- 2011–2018: recurring "our LVT sales grew significantly, but were **constrained** by internal
  production" as MHK ramped up new LVT (luxury vinyl tile) manufacturing lines — a real signal at the
  time, but explicitly a temporary ramp-up bottleneck that MHK was actively resolving with new capex
  each cycle ("Our production has been expanded to support the higher projected volume," 2015-05-08).
- 2021-10-29: supply-chain/labor/transportation constraints (COVID-era, industry-wide, not MHK-specific).
- 2024-02-09: *"constrained"* refers to macro new-home construction (demand-side, not MHK's product).
- Recency scan (2024-02-09 through 2026-05-01, 10 quarters): only 3 quarters have **any** hit at all
  (`at capacity` once in 2024-10-26; `pricing power` twice in 2025-05-02 and once in 2026-05-01), and
  the 2026-05-01 quote is explicitly non-committal: *"I'm not sure there's a dramatic difference in any
  of them [regions/products]…"*

Judgment: MHK's clearest constraint-language episodes (LVT capacity 2011–2018) are old and were
resolved by MHK's own capex each time — a recurring "we built more capacity to catch up" pattern, not
a persistent bottleneck. The current (2024–2026) signal is sparse and hedged. themes.yaml overlap:
conceptually adjacent to LEN/TOL housing-supply narrative (flooring demand tracks new construction /
remodeling) but that narrative itself is already judged WEAK.

**Verdict: WEAK** — old, resolved-by-capex episodes; thin and non-committal current signal.

---

## WST (West Pharmaceutical Services) — STRONG

**Data-quality flag first:** one transcript tagged `primary_ticker='WST'` in the corpus,
`transcript-WST-2023-11-10`, is **not** West Pharmaceutical Services — its body text is the Westrock
Coffee Company (ticker WEST) Q3 2023 earnings call ("Westrock Coffee Company's Third Quarter 2023
Earnings Conference call... Scott Ford, Co-Founder and CEO"). This produced a false "sold out" /
"100% sold out of capacity" hit in the initial sample that is about Westrock Coffee's extract/RTD
beverage manufacturing lines (Richmond, CA and Conway, AR plants), not West Pharma. I verified this is
an isolated mislabeling (checked via FTS match on "Westrock" across all 66 WST-tagged transcripts —
only this one slug matches); every other sampled WST transcript, including the adjacent
2026-04-23 one, opens with "West's first quarter earnings conference call... Eric Green [CEO]... Bob
McMahon [CFO]" — the genuine West Pharmaceutical Services executives. **Recommend a corpus hygiene
pass to re-scrape/re-tag `transcript-WST-2023-11-10`** (it should not count as WST evidence and should
probably be re-filed under a WEST/Westrock Coffee slug). This does not affect the verdict below, which
is built entirely on the confirmed-genuine West Pharma transcripts.

Sampled 8 quarters spanning 2008-02-21 to 2026-04-23 (48/66 matching in the original sample; excluding
the mislabeled doc), then pulled all of 2025-07-24 through 2026-04-23 (4 consecutive genuine quarters)
in full to check breadth/consistency.

West Pharma's "HVP" (High-Value Products) segment — proprietary elastomer/rubber components
(NovaPure, FluroTec, Westar, Daikyo Crystal Zenith) used as stoppers/seals/containment systems for
injectable biologic drugs, GLP-1s (Ozempic-class), and other parenteral drugs — is **48% of total
company sales**, and is described as capacity-constrained by demand in every one of the last 4
quarterly transcripts:

- 2025-07-24 (Q2'25): *"…one of our HVP plants in Europe has experienced certain **constraints**. We
  are proactively executing an initiative to expand capacity…"*
- 2025-10-23 (Q3'25): *"We continue to work through our **constraint** at our HVP manufacturing site in
  Germany. During the quarter, we made good progress hiring and training employees in installing new
  equipment to expand capacity."*
- 2026-02-12 (Q4'25): *"…the demand is **outstripping supply** right now, which we need to get caught
  up."* / *"…while **demand outstripped our supply**. As Eric mentioned, we continue to **ramp
  capacity**…"*
- 2026-04-23 (Q1'26, most recent transcript in corpus): *"If you recall, in Q4, we talked about
  **demand outstripping supply**. We're continuing to ramp and feel good about the team's ability to
  continue to meet that demand for the rest of the year."*

The structural driver is explicit and twofold, not just cyclical demand: (1) secular GLP-1/biologics
volume growth, and (2) "Annex 1" — an EU regulatory update forcing pharma customers to upgrade from
Standard components to HVP components for contamination-control compliance, which West frames as a
multi-year, largely irreversible mix-shift tailwind ("Annex 1 and related HVP upgrades," 370 upgrade
projects in progress as of mid-2025, up from 340 the prior quarter). Management explicitly ties this
to a **pricing/margin moat**, not just volume: HVP components carry roughly 60%+ gross margins vs.
20–30% for Standard products, and over half of HVP components are "spec-ed into an FDA or similar
regulatory process" — i.e., once a drug's regulatory filing names West's specific component, switching
suppliers requires re-filing, a genuine regulatory-lock moat reinforcing pricing power (distinct from
a pure physical-scarcity story).

Judgment: this is the cleanest hit in the entire Group D batch — current (spans at least 4 consecutive
quarters through the most recent transcript in the corpus), self-described by name (CEO/CFO both use
"demand outstripping supply" verbatim across two consecutive quarters), quantified (48% of sales, 200bp
margin contribution from mix), and backed by a distinct structural/regulatory moat (Annex 1 filing-lock)
rather than a generic macro story. No existing theme in themes.yaml touches pharma packaging /
drug-delivery components — zero overlap.

**Verdict: STRONG** — recommend a new thesis on West Pharma's HVP components (GLP-1/biologics
elastomer packaging), capacity-constrained with an Annex-1 regulatory-lock pricing moat. Also file the
corpus data-hygiene note above (one mislabeled Westrock Coffee transcript under the WST ticker).

---

## EQR (Equity Residential) — WEAK

Sampled 8 quarters spanning 2008-02-06 to 2026-04-29 (53 matching transcripts). "Pricing power" is
the dominant matched phrase (appears in nearly every sampled quarter) — but it is used as routine,
market-by-market (DC / NY / LA / SF / Denver / Seattle) rent-growth commentary that any apartment REIT
gives every quarter, oscillating freely with the local cycle rather than describing a persistent
structural advantage:
- 2015-08-03: *"Boston continues to perform as expected, with **virtually no pricing power** in the
  downtown financial district."*
- 2018-01-31 (x4 hits): alternates between "elevated new supply... had begun to impact landlords'
  pricing power" and "we believe... pricing power kind of return[s] to the landlords" — purely cyclical.
- 2022-04-27: *"we are seeing **pricing power** ahead of our expectations"* — post-COVID reopening
  demand surge, cyclical.
- 2026-04-29 (latest, 10 hits): mostly about D.C. specifically — *"such a tremendous drop-off in the
  supply... 65% less new units coming online. That will equate to some level of pricing power"* — a
  single-submarket, federal-workforce-driven new-supply pullback, not a company-wide structural
  bottleneck in EQR's own "product."

Judgment: this reads as ordinary REIT boilerplate — every quarter's earnings call walks through
market-by-market rent-growth drivers, and "pricing power" is simply the standard term of art for
"can we push rents," not a discovery-worthy structural signal. No consistent, company-specific
beneficiary narrative distinct from routine market commentary.

**Verdict: WEAK** — routine quarterly REIT rent-commentary language, not a structural discovery.

---

## AVB (AvalonBay Communities) — WEAK

Sampled 8 quarters spanning 2008-02-07 to 2026-04-28 (56 matching transcripts). "Supply constrained"
appears repeatedly, but describes **AVB's decades-old, explicitly stated investment strategy** of
concentrating in coastal, land-constrained metros — not a new discovery:
- 2016-07-26: *"...the region is pretty **supply-constrained**."* (Southern California)
- 2018-04-26: *"...highly **supply-constrained** where we have the ability to get entitlements, so
  those tend to be very accretive deals."* — explicitly framed as AVB's long-standing acquisition
  criterion, not a fresh structural bottleneck.
- 2021-02-04 / 2023-02-09: same pattern for Marin County / suburban Denver — "we bought assets... where
  it is more supply-constrained" as a stated portfolio-construction rule.
- 2026-04-28 (latest): *"pricing power"* discussion is generic month-to-month leasing commentary,
  nothing structurally new.

Judgment: "coastal supply-constrained markets" has been AVB's explicit, publicly stated investment
thesis for well over a decade (it's literally how AVB describes its own strategy in every 10-K) — this
is the textbook definition of an already-priced-in, well-known narrative, not a new radar discovery.

**Verdict: WEAK** — AVB's own long-stated investment strategy/tagline, not a new signal; same
old-narrative caveat as the homebuilder cluster, arguably even more so since it's explicit strategy
language repeated for 18+ years.

---

## ESS (Essex Property Trust) — WEAK

Sampled 8 quarters spanning 2008-02-07 to 2026-04-29 (47 matching transcripts). Same pattern as AVB,
West-Coast-specific:
- 2008-02-07: *"...take on more of a **supply constrained** market characteristics"* (Portland, urban
  growth boundary) — this is literally ESS explaining its regional investment thesis on its very first
  sampled call, 18 years ago.
- 2023-07-28: *"...the West Coast supply outlook is relatively muted, and a multiyear **lead time** is
  required to develop new housing in our markets."* — same long-standing West Coast entitlement-
  scarcity thesis.
- 2026-04-29 (latest): *"...the durability of our **supply-constrained** West Coast markets. There is a
  direct correlation between housing supply and the cost of housing for consumers."* — still the same
  framing verbatim, 18 years later.

Judgment: identical situation to AVB — "West Coast markets are supply constrained due to entitlement/
urban-growth-boundary friction" is ESS's original and unchanged core investment thesis since at least
2008, not a new discovery. The pricing-power quotes (2026-04-29, discussing eviction-processing
timelines and delinquency normalization pushing L.A. toward 95% occupancy) are cyclical
recovery-from-COVID-delinquency-overhang commentary, not a structural bottleneck story.

**Verdict: WEAK** — same 18-year-old West Coast supply-constraint thesis as AVB; not new.

---

## Housing-supply-shortage "two ends of one macro story" check (LEN/LEN-B/TOL ↔ EQR/AVB/ESS)

The brief flagged this pairing explicitly: homebuilders (short of housing → should have pricing power
building it) and apartment REITs (short of housing → benefit from rental pricing power) are two ends
of the same "supply-constrained housing" macro narrative. Having reviewed both ends independently, the
conclusion is the same on both sides: this is a well-known, 10-15+ year old macro narrative
(underproduction since the 2008-2012 housing bust) that is already widely priced in and explicitly
stated as each company's core strategy/messaging for well over a decade — it does not meet the bar of
a fresh, un-priced discovery-radar signal on either end. **Not recommended as a combined thesis
either.**

---

## Summary table

| Ticker | Verdict | One-line reason |
|---|---|---|
| LEN / LEN-B | WEAK | 15-yr-old "chronic housing underproduction" macro narrative; mixed/negative self-described pricing power; zero hits in latest transcript |
| TOL | WEAK | Same old housing-shortage narrative; pricing power explicitly "relatively limited" in latest quarter |
| FSS | WEAK | Mostly victim of chassis-supplier allocation; current (2024-2026) narrative is *reducing* lead times, the opposite of a bottleneck claim |
| IIIN | WEAK | Repeated explicit denials of pricing power; "on allocation" instance is IIIN as victim of wire-rod suppliers, not beneficiary |
| LPX | **STRONG** | SmartSide/ExpertFinish specialty siding: pricing power self-attributed in 7 of last 9 quarters + ExpertFinish literally on allocation through ~Feb 2026 — distinct from weak commodity-OSB leg |
| MHK | WEAK | LVT capacity constraints (2011-2018) were resolved by MHK's own capex each cycle; current signal thin/non-committal |
| EQR | WEAK | Routine quarterly REIT rent-growth boilerplate, not a structural discovery |
| AVB | WEAK | "Supply-constrained coastal markets" is AVB's own 18-year-old stated investment strategy, not new |
| ESS | WEAK | Same as AVB — 18-year-old West Coast supply-constraint thesis, unchanged messaging |
| WST | **STRONG** | HVP (GLP-1/biologics elastomer components), 48% of sales, "demand outstripping supply" self-described verbatim across 2 consecutive quarters + Annex-1 regulatory-filing-lock pricing moat; cleanest hit in the batch |

**New thesis candidates: LPX (siding/building-products mix-shift) and WST (pharma packaging/HVP
components).** Both have zero conceptual overlap with existing `themes.yaml` themes (all 9 existing
themes are AI-capex/semiconductor/space/rare-earth/energy).

**Corpus data-hygiene item to file:** `transcript-WST-2023-11-10` is mislabeled — it is Westrock
Coffee Company (ticker WEST) content tagged under `primary_ticker='WST'`. Isolated to this one slug
(verified via full-text "Westrock" match across all 66 WST-tagged transcripts).
