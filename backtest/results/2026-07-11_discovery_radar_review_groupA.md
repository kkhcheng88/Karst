# Discovery Radar Manual Review — Group A (航太特種合金 / 工業重型設備 cluster)

> 2026-07-11. Manual verbatim review of 11 candidates from `backtest/results/2026-07-10_discovery_radar.md`
> (all n_quarters_flagged ≥45). Method: FTS5 query on `thesis/corpus.db` `docs_fts_en` for the standard
> constraint-phrase list, stratified sample of 6-8 transcripts spread across each ticker's full history
> (not just recent quarters), ±260-char context pulled around each phrase hit and read in full sentence/
> paragraph context. Same skeptical bar as the "trough" false-positive experiment earlier today: a phrase
> hit only counts if the company is describing **its own** structural bottleneck as a **beneficiary**
> (pricing power / backlog leverage), not generic market color, a one-off, or a victim-role mention
> (its own supplier/input is constrained, hurting it).
>
> Query script: `backtest/experiments/exp_groupA_radar_review.py` (per-ticker match counts) +
> `backtest/experiments/exp_groupA_radar_review2.py` (stratified quotes with wide context, dumped to
> `backtest/experiments/_groupA_context_quotes.txt`).
>
> **Headline finding**: 3 of the 11 (GNRC, CAT, SPXC) carry strong, current (2025-2026), *quantified*
> structural-bottleneck evidence — but it is the **same AI-data-center-power/cooling story the
> `ai-power-grid` theme already tracks** (which holds GEV/BE/VRT/ETN/PWR/MPWR/VICR/NVTS/WOLF/ON/TXN).
> These are FOLD candidates, not new theses. 2 of the 11 (ATI, CRS) carry strong, sustained,
> first-person structural evidence in a sub-industry (aerospace jet-engine specialty alloys) that has
> **no existing theme** — genuine STRONG candidates, likely as a paired new theme. The remaining 6
> (ARW, RS, STLD, KALU, TEX, OSK) are WEAK/UNCLEAR: mostly distributor/service-center commentary on
> *someone else's* lead times, victim-role supply-chain-hurts-us language, or generic commodity-cycle
> color that happens to contain the same keywords.

---

## ATI (ATI Inc — specialty metals: titanium, nickel superalloys; aerospace/defense/energy)

**Quotes (spanning 2007-2026, 7 of the sampled transcripts):**

- 2007-07-25: *"Titanium and Nickel alloy shipments under long-term agreements have grown and are
  expected to continue to grow with robust Aerospace build rates."*
- 2010-04-28: *"overall order receipts were up significantly causing lead times to extend by an
  additional two to eight weeks for high performance metals... Based on these continued market
  conditions, we believe there may be opportunities for improving base prices."*
- 2013-01-23 / 2015-07-21: multiple, consistent references to LTAs "in hand and more being negotiated,"
  powder capacity expansion tied to "existing long-term agreements with jet engine OEMs that run well
  into the next decade."
- 2023-08-02: *"We're converting near-term demand into long-term agreements. In June, we announced
  that we've secured over $1.2 billion in new commitments... 70% is incremental to our announced 2025
  targets."*
- **2026-04-30 (most recent):** *"lead times are extending for our most differentiated products, super
  alloy nickels, premium quality titanium, isothermal forgings and exotic alloys. This is a key point.
  This is not short-cycle demand. It is tied to long-term contracts, production schedules..."* and, same
  call: *"We supply 6 of the 7 most advanced jet engine nickel alloys. This remains a capacity-constrained
  market where our differentiated capabilities allow us to capture both share and value."*

**Judgment:** This is exactly the profile the "trough" experiment warns against checking for —
and it clears the bar cleanly. Nineteen years of consistent, first-person, structural language:
specific product differentiation (named alloy classes, "6 of 7 most advanced" — a real moat claim),
explicit multi-year LTA structure (not spot/one-off), and management explicitly distinguishing this
from "short-cycle demand." Beneficiary framing throughout (pricing/share capture), never victim.

**themes.yaml overlap check:** No existing theme covers aerospace jet-engine specialty
materials/superalloys. `space-satellite` is launch/satellite hardware, not engine metallurgy.
No overlap.

**VERDICT: STRONG**

---

## CRS (Carpenter Technology — specialty alloys, premium aerospace materials)

**Quotes:**

- 2011-04-26: *"a significant part of our existing capacity is booked under long-term agreements for
  the next four years... All our existing key customers, with whom we have LTAs, are pressing [for more]."*
- 2018-10-24: *"Our customers recognize the urgency to qualify additional capacity, given increasing
  lead times and the projected airframe and engine build rates."* — customers must formally
  re-qualify CRS's capacity, a real switching-cost moat.
- **2023-10-26: *"Lead times remain at record levels and could be even longer as we are actively
  managing incoming orders and customers continue to tell us their primary concern is surety of
  supply, asking when they can book more with us."*** Same call: raised prices 7-12% on transactional
  business.
- **2026-04-29 (most recent): *"customers are prioritizing security of supply, and we are continuing
  to realize pricing that reflects the value we deliver... While no long-term agreements were completed
  in the quarter, several are currently in negotiation. These long-term agreements support attractive
  economics for us while providing our customers with the supply chain certainty they need."*** Same
  call, on output: *"you know you guys are kind of 24/7 full out."*

**Judgment:** Same sub-industry and same structural pattern as ATI — customer-side qualification
lock-in, explicit pricing capture tied to scarcity, sustained across 15 years of transcripts, current
quarter confirms the story is still live ("24/7 full out," pricing "reflects the value we deliver").
No victim-role language found in the sample.

**themes.yaml overlap check:** Same conclusion as ATI — no existing theme. ATI and CRS are close
enough in mechanism (aerospace specialty-alloy LTA/qualification moat, jet-engine OEM customers,
capacity-constrained pricing) that they read as two names for the **same** candidate new theme, not
two separate theses.

**VERDICT: STRONG** (paired with ATI — recommend evaluating together as one new
"aerospace-specialty-alloys" theme candidate, not two)

---

## GNRC (Generac — generators; home standby + C&I/data-center gensets)

**Quotes:**

- 2012, 2014, 2018, 2021: recurring cycle of home-standby-generator lead times extending during
  storm/outage-driven demand surges, then normalizing — genuinely cyclical (weather-driven), not
  structural.
- 2022-11-02: *"growth in our dealer base was constrained in prior quarters by our extended production
  lead times"* — mild victim-adjacent framing (own bottleneck limiting own channel growth, not
  obviously converting to pricing power in this snippet).
- 2024-07-31: *"reduced product lead times"* — lead times **normalizing/shrinking**, the opposite
  direction of a persistent bottleneck.
- **2026-02-11 (supplementary "data center" query): *"we are making progress with other data center
  co-locators and developers as our existing backlog has increased to approximately $400 million...
  providing a path to doubling our C&I product sales."***
- **2026-04-29 (most recent, supplementary query): *"we have also realized significant order activity
  from both new and existing data center customers, increasing our current backlog to more than $700
  million... an increase of approximately $300 million since our fourth quarter update... backlog
  growth provides visibility through 2027."***

**Judgment:** The legacy home-standby business is cyclical/weather-driven, not a structural
bottleneck story (WEAK on its own). But the current, fast-growing C&I large-megawatt-genset /
data-center-backup business is a genuine, quantified, current structural story: backlog +$300M in one
quarter to $700M, explicitly tied to hyperscaler/data-center vendor-qualification wins. This is real
and current — but it is the same "AI infrastructure needs backup power capacity that can't be built
fast enough" story the `ai-power-grid` theme already tracks via GEV (gas turbines) and BE (fuel
cells). GNRC's diesel/gas large-genset line is a direct sibling product to what GEV sells at grid
scale, serving the same data-center customers referenced by the same demand driver.

**themes.yaml overlap check:** `ai-power-grid` tickers = GEV, BE, VRT, ETN, PWR, MPWR, VICR, NVTS,
WOLF, ON, TXN. Not present — but the theme's own kill_condition already watches "turbine majors'
orders confirm a 2026 peak (GEV CEO order-pace cracks)" — GNRC's large-genset backlog data would be a
direct, relevant data point for that exact tracked risk. Clear conceptual fit.

**VERDICT: FOLD → ai-power-grid** (specifically as the diesel/gas large-genset leg alongside GEV's
turbines; legacy home-standby business is cyclical noise, exclude that segment's language from the
thesis evidence)

---

## CAT (Caterpillar — heavy equipment; Power & Energy segment gensets/turbines for data centers)

**Quotes:**

- 2010, 2012, 2016, 2018, 2021, 2023: mostly generic "lead times extended/improved" market commentary
  across CAT's very broad equipment lines (mining trucks, machinery) — largely cyclical, tracks the
  general industrial cycle, not a specific moat.
- **2026-04-30 (most recent): *"Obviously where we're capacity constrained, we're able to do a little
  bit more [on pricing]... a large part of that business is industrial and smaller power generation,
  marine."*** Same call: *"the 3x and way we've said 2x capacity now going to 3x, that's sort of
  factory output... we estimate this will give us another 15 gigawatts of capacity annually when we're
  done with this installation."*
- **2026-04-30 (supplementary "data center" query): *"Power generation grew 48%, driven by strong
  demand for large gensets and turbines used in data center applications with an increasing mix
  towards prime power."*** Also 2025-08-05: *"Power generation grew by 19%, primarily due to demand
  for reciprocating engine for data center applications."*

**Judgment:** Same pattern as GNRC but for CAT's Power & Energy segment specifically: current-quarter,
first-person, explicit capacity-constrained-with-pricing-power language ("where we're capacity
constrained, we're able to do a little bit more"), directly and explicitly tied to data-center genset/
turbine demand, with a hard, quantified capacity build number (going from 2x to 3x factory output,
+15 GW/year). The rest of CAT's business (mining, construction machinery) is generic industrial-cycle
noise and should NOT be read as part of this evidence — only the Power & Energy / data-center leg
qualifies.

**themes.yaml overlap check:** Same conclusion as GNRC — this is CAT's version of the exact
GEV-turbine / BE-fuel-cell data-center-backup-power story already inside `ai-power-grid`.

**VERDICT: FOLD → ai-power-grid** (Power & Energy / data-center genset-turbine leg only; CAT's other
segments are not part of this evidence and should not be dragged in)

---

## SPXC (SPX Technologies — HVAC/cooling towers, Detection & Measurement)

**Quotes:**

- 2015, 2018: legacy power-transformer business showed long lead times (40-55 weeks) tied to industry
  capacity consolidation — but note 2023-08-02: *"The businesses that we did not feel we had pricing
  power we divested... really the transformer business"* — SPXC explicitly divested that leg; not
  relevant to current SPXC.
- 2023-08-02 (current-portfolio businesses): *"we do believe we have pricing power in our HVAC and our
  Detection & Measurement [segments]."*
- **2026-04-30 (most recent), analyst framing confirmed by management: *"it feels like you're more
  capacity-constrained than customers seem like they'll take anything you can give them"*** — and in
  the same exchange: *"You raised the data center growth from 50% to 70%... when you ramp up this
  capacity, Tennessee, Mirabel, Madison, et cetera, how much more revenue you think you can unlock?"*
  Management confirms: *"Olathe should be at full capacity as we get into mid-2027. The Tennessee
  facility... we expect that to be at full capacity in 2027."*

**Judgment:** Strong, current, quantified evidence (data-center revenue-mix guidance raised from 50%
to 70% of a segment; multiple named facilities running flat-out into 2027) that SPXC's HVAC/cooling
business (Marley-brand cooling towers, an industry-known data-center-cooling supplier) is capacity-
constrained by AI-data-center demand specifically. This is not generic HVAC replacement-cycle color —
it is explicitly the data-center leg.

**themes.yaml overlap check:** `ai-power-grid` already holds VRT (Vertiv), which sells combined
power-and-thermal-management infrastructure to the same hyperscaler data-center customers. SPXC's
cooling-tower business serves the identical end-market/demand driver (AI-capex-driven data-center
buildout) with a directly adjacent product category (cooling infrastructure vs. Vertiv's power+cooling
systems).

**VERDICT: FOLD → ai-power-grid** (HVAC/data-center-cooling leg only; Detection & Measurement segment
not covered by this evidence)

---

## ARW (Arrow Electronics — electronic components distributor)

**Quotes:**

- Nearly every hit across 2007-2026 is standard distributor color-commentary tracking **industry-wide**
  component lead times as a demand indicator, not ARW's own capacity: *"lead times are still within
  normal ranges"* (2007), *"lead times remained at the high end of normal ranges"* (2010), *"lead
  times haven't changed either"* (2013), *"lead times and cancelation rates continue to track within
  normal ranges"* (2016).
- 2018-08-02: *"We still have a fairly constrained supply situation on MLCC. There's more product
  actually coming through... but the demand is outstripping that."* — describes a **supplier-side**
  (MLCC manufacturer) constraint that ARW as distributor is managing around, not ARW's own bottleneck.
- **2026-05-07 (most recent): *"We have also seen lead times extend. They remain significantly lower
  than a pervasive shortage environment."*** and *"as pockets of supply became constrained for
  technologies around AI investments, hardware sales saw strong momentum in the first quarter."*

**Judgment:** ARW is a distributor/middleman. Every quote describes conditions in the components it
buys and resells, not ARW's own product/capacity being scarce. Even the most favorable framing
("hardware sales saw strong momentum" when suppliers were tight) describes ARW benefiting from
*someone else's* scarcity via its position in the value chain — a different economic mechanism from
"our own product is the bottleneck, so we have pricing power." This is the ARW pattern the earlier
CIEN/ARM eliminations warned about: present in the language, but not the right role.

**themes.yaml overlap check:** N/A (verdict is WEAK regardless).

**VERDICT: WEAK**

---

## RS (Reliance Steel & Aluminum — metals service center / distributor)

**Quotes:**

- Recurring pattern across 2012-2018: reporting **mill** (supplier) lead times as a market indicator
  — *"mill lead times at 16 to 18 weeks"* (2012), *"Lead times... 8 to 12 weeks and mills are busy"*
  (2014) — this is RS describing its suppliers' conditions, not its own.
- 2021-07-22: *"our business model... is particularly effective during periods of tight supply and
  volatile pricing. In addition, despite metal supply constraints, our strong, long-standing
  relationships with the domestic mills... allowed us to source the metal we needed."* — RS profits
  from arbitraging *mills'* tightness via relationship/scale advantage, a distributor-arbitrage moat,
  not a "my own product is scarce" moat.
- **2026-04-23 (most recent): *"extending lead times at our mill suppliers also bode well for a
  continued strong pricing environment where access to metal becomes a strategic advantage."***

**Judgment:** Same structural pattern as ARW — RS is explicit that the *mills* (its suppliers) are the
ones with extending lead times/tight supply; RS's edge is relationship-based access, not its own
capacity being the chokepoint. Real business advantage, but not the "self as beneficiary of own
supply constraint" mechanism the objective is looking for.

**themes.yaml overlap check:** N/A (verdict is WEAK).

**VERDICT: WEAK**

---

## STLD (Steel Dynamics — EAF steel producer)

**Quotes:**

- 2008-01-29: *"a structural supply shortage creating a gap that's not being filled by imports"* —
  macro/industry-wide commentary, not STLD-specific differentiation.
- 2010, 2013, 2022: *"running at capacity"* for specific divisions during cyclical upswings; capacity
  expansion narrative ("steelmaking capacity expanded to 7.4 million tons, and we've yet to fully
  realize the benefit").
- 2017-10-19: *"mill lead times are pretty healthy... could create a tight market and lead to
  significant price appreciation"* — cyclical (imports declining, trade-case driven), not a
  differentiated-product moat.
- **2026-04-21 (most recent): *"conditions continue to improve, supported by strong demand and lower
  imports. Lead times remain elevated and customers remain optimistic about the outlook... improving
  value-added spreads returning with the impact of the core trade cases that we won in 2025."*** Same
  call, Q&A: *"Beams, I hear, are sold out."* (analyst statement, not directly confirmed/quantified by
  management in this snippet).

**Judgment:** STLD is a genuine producer (unlike ARW/RS) so the lead-time language is about its own
order book — but the driver throughout is the commodity steel cycle plus trade protection
(Section 232/anti-dumping cases), not a structural, differentiated-product bottleneck. This reads as
standard steel-earnings-call boilerplate that would apply to most US steel producers, not a company-
specific moat comparable to ATI/CRS's named, qualification-locked specialty alloys.

**themes.yaml overlap check:** N/A (verdict is WEAK).

**VERDICT: WEAK**

---

## KALU (Kaiser Aluminum — aluminum products, aerospace plate)

**Quotes:**

- 2007-11-14: *"we're very confident that we will run at capacity next year... about 95% of capacity...
  we expect we'll sell every pound that we can produce through our heat treat operations."* — strong,
  specific.
- 2012-04-26: *"we think there's continued good pricing power in [aerospace] products."* — decent but
  tied to a cyclical recovery, not asserted as durable.
- 2016-10-20: *"our lead times for heat treat plate are down to six weeks and we have indications that
  the aerospace supply chain will experience destocking in 2017"* — lead times **shrinking**, explicit
  destocking warning, i.e. the opposite of persistent constraint.
- **2022-04-21: *"Our main supplier, US Mag, declared force majeure in September of 2021 and we have
  been on allocation below our contracted volumes since that time."*** — this is KALU as the
  **victim** of a supplier's constraint (the exact trap flagged in the task brief: "on allocation" here
  means KALU can't get enough magnesium, not that KALU's own product is allocated to customers).
- **2026-04-23 (most recent): *"lead times across the industry are beginning to stretch, and pricing
  continues to firm across many of our products... As lead times extended and pricing firmed, the
  environment has increasingly rewarded reliability and service."***

**Judgment:** Genuinely mixed record. Two bookend positive quotes (2007, 2026) suggest real periods of
capacity-driven pricing power, but the 15 years between them show cyclical lead-time compression
("down to six weeks," "destocking" warning) and one explicit victim-role episode (2022 magnesium force
majeure — KALU on the wrong side of an allocation, not the right side). Unlike ATI/CRS, there's no
consistent LTA-anchored structural narrative running through the whole sample — it looks more like
ordinary aluminum-cycle behavior with the most recent quarter happening to be in an up-phase.

**themes.yaml overlap check:** No aluminum theme exists currently; N/A given verdict.

**VERDICT: UNCLEAR** — recommend a follow-up pass reading only the last 4-6 quarters (2025-2026) in
full to see if the 2026-04-23 tone (pricing firming, lead times stretching) is becoming a sustained
new regime or is just normal cyclical upswing language like 2007's was before the multi-year
cyclical/destocking swings that followed.

---

## TEX (Terex — construction/aerial equipment; segments include Aerials, Utilities, Materials
Processing, Environmental Solutions/Transport per the 2026 transcripts)

**Quotes:**

- 2009-10-22, 2011-10-28: routine "long lead times, lumpy" business-characteristic descriptions, not
  constraint episodes.
- 2018-11-02: TEX describes *entering into* long-term agreements **with its own suppliers** ("entering
  into long-term agreements with suppliers so that... we're able to ensure continuity of supply") —
  TEX as buyer/procurement side, not the scarce-capacity seller.
- **2022-02-11: *"we're facing shortages and cost pressures for materials, logistics, freight and
  labor. These headwinds have constrained our growth in the short term."*** — explicit victim-role
  language: supply constraints are hurting TEX, not creating pricing power for it.
- 2024-02-09: *"continue to be constrained by body and chassis shortages"* — victim role again
  (third-party component shortage limiting TEX's own output).
- **2026-05-01 (most recent): *"increasing capacity by 35% at our Ocala, Florida plant... Both
  investments will help to reduce lead times, and with the S-180 pumper, provide our customers with a
  lower cost alternative."*** — TEX is investing specifically to **shrink** its own lead times and cut
  costs for customers, the opposite framing of a scarcity/pricing-power moat.

**Judgment:** Every "beneficiary-shaped" reading in the sample is undercut by TEX's own framing:
constraint language here is either about TEX-as-procurement-victim (2018, 2022, 2024) or TEX actively
working to eliminate its own bottlenecks to compete on price/delivery (2026), not to defend a scarcity
premium. No first-person pricing-power claim tied to constrained capacity was found.

**themes.yaml overlap check:** N/A (verdict is WEAK).

**VERDICT: WEAK**

---

## OSK (Oshkosh Corp — access equipment/JLG, defense, fire & emergency, refuse/vocational)

**Quotes:**

- **2008-02-01: *"the very large booms 120 feet and up demand is very strong. It's, we're in sold out
  kind of condition."*** — genuine, specific, beneficiary-framed (JLG large aerial booms).
- 2014-04-29: *"Product and business complexity and long lead times prevent quick fixes."* — OSK
  describing its own lead times as an operational **problem** it's struggling to solve, not a moat.
- 2016-07-31: procuring "a limited amount of longer lead time materials" for defense M-ATV vehicles —
  procurement/victim-side framing.
- 2019-10-30: *"lead times have come down, and our customers are comfortable now ordering within that
  quarter"* — describes conditions **easing**, the opposite of sustained constraint.
- 2022-07-28: *"availability remains constrained... we have been impacted by several other components
  that have further limited our ability to produce."* — explicit victim-role (component shortages
  limiting OSK's own output).
- **2024-04-25: *"pretty well sold out... big backlogs and such, therefore, longer lead times"*** for
  Access equipment — genuine beneficiary framing again.
- **2026-05-08 (most recent): *"focused on modernizing and improving production flow and removing
  bottlenecks to improve lead times"*** and *"we reduce lead times"* (Transport segment) — again OSK
  framing its own lead times as a problem to fix, though the same call notes *"jetway backlog now
  extends beyond 12 months"* (Transport segment) as a genuine strength.

**Judgment:** Real mixed signal. JLG (Access segment) shows two clean, dated, beneficiary-framed
sold-out/backlog episodes (2008, 2024) — a legitimate periodic capacity-tightness pattern for large
aerial booms specifically. But across the rest of the 18-year sample and across OSK's other segments
(defense, vocational/fire, transport), the dominant framing is OSK **struggling with** and actively
**working to reduce** lead times/bottlenecks as an operational headwind, not defending a pricing-power
moat. The signal is real but concentrated in one specific product line (JLG large booms) rather than
company-wide.

**themes.yaml overlap check:** No overlap found — OSK's businesses (access equipment, defense
vehicles, fire apparatus, refuse trucks) don't connect to the AI-power/data-center story that
GNRC/CAT/SPXC do.

**VERDICT: WEAK** (company-wide); if pursued further, narrow strictly to the JLG Access-equipment
large-boom sub-line rather than OSK as a whole — but on the current sample this doesn't clear the bar
for a standalone thesis.

---

## Summary table

| ticker | verdict | one-line reason |
|---|---|---|
| ARW | WEAK | Distributor commentary on *suppliers'* component lead times, not ARW's own bottleneck |
| ATI | **STRONG** | 19yrs consistent first-person LTA/capacity-constrained language, named-product moat, no theme overlap |
| CRS | **STRONG** | Same pattern as ATI (customer-qualification lock-in, pricing capture); pair with ATI as one new theme |
| RS | WEAK | Reports *mill* (supplier) lead times; profits from distributor-relationship arbitrage, not own capacity |
| STLD | WEAK | Commodity steel-cycle/trade-case boilerplate, not a differentiated structural moat |
| KALU | UNCLEAR | Mixed: 2007/2026 bookends look real, but 15yrs between show cyclicality + a 2022 victim-role (supplier force majeure) episode |
| TEX | WEAK | Constraint language is victim-role (own growth hurt by shortages) or TEX actively shrinking its own lead times to compete on price |
| OSK | WEAK | Dominant framing = OSK struggling with/reducing its own bottlenecks; genuine beneficiary episodes exist but confined to JLG large-boom sub-line only |
| GNRC | **FOLD → ai-power-grid** | Current, quantified ($700M data-center genset backlog, +$300M in one quarter) — same AI-backup-power story as GEV/BE |
| SPXC | **FOLD → ai-power-grid** | Capacity-constrained HVAC/cooling-tower leg, data-center revenue mix guided 50%→70%, facilities full through 2027 — same story as VRT |
| CAT | **FOLD → ai-power-grid** | Power & Energy segment: "capacity constrained... able to do a little bit more [pricing]", 2x→3x factory output, +15GW/yr, explicitly data-center-driven |
