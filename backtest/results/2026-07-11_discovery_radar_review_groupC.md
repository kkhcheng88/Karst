# Discovery Radar Manual Review — Group C (Energy/Materials)

> Reviewer pass on 2026-07-11. Source: `backtest/results/2026-07-10_discovery_radar.md` candidate list, cluster
> "能源/原材料". Method: pulled 6-9 constraint-phrase matches per ticker from `thesis/corpus.db`
> (`docs_fts_en` FTS5 MATCH over `CONSTRAINT_PHRASES`), spread across the full available time range (not just
> recent quarters), read wide context (±250 chars) around each match, checked `thesis/themes.yaml` for
> conceptual overlap. Working pull script: `backtest/experiments/exp_groupC_radar_pull.py`; raw context dump:
> `backtest/experiments/exp_groupC_radar_pull_output.txt`.
>
> **Standing caution applied throughout** (per today's "trough" false-positive experiment): every match was read
> in full sentence/paragraph context before being counted as signal. Generic business vocabulary ("constrained,"
> "at capacity," "take or pay," "pricing power" used in an analyst *question* rather than a company *claim*) was
> discounted. Energy-sector-specific caution: oilfield-services "lead time / tight supply" commentary was
> checked against the price cycle (do the claims appear only in up-cycles and vanish in downturns — i.e.
> cyclical — or do they persist independent of price — i.e. structural).

---

## USAC (USA Compression Partners) — natural gas compression services

**Ticker overlap with themes.yaml**: none. `oil-gas-energy` tickers = XOM/CVX/COP/EQT/LNG/SEI (upstream + LNG +
gas-power); `ai-power-grid` tickers = GEV/BE/VRT/ETN/PWR/MPWR/VICR/NVTS/WOLF/ON/TXN (AI-power hardware). Neither
covers gas-compression equipment/services. No overlap.

**Quotes** (compressor/engine equipment lead times, spanning 2013→2026):
- 2013-02-26: "the lead times right now, if we were to not have equipment already in queue with our fabricators,
  we'd be somewhere in the four to six month range."
- 2018-11-06 (CFO/CEO): "we're effectively sold out of the larger horsepower assets... Lead times for the large
  horsepower equipment... are still right around a year... Midstream infrastructure activity levels and the
  tight supply demand dynamics for both new and used large horsepower equipment are positive for both
  utilization and pricing."
- 2022-08-02 (analyst Q, exec answers on pricing power): "utilization continues to tick higher, you're going to
  get more and more pricing power... it really sort of kicks-in in that low 90%, high-80s"; separately, exec
  states directly: "our compression services business does not have direct commodity price exposure" — i.e.
  management itself frames this as *not* an oil/gas-price cyclical story.
- 2026-05-05 (most recent, CEO/CFO on Q1'26 call): "Certain new engine lead times have recently tripled from
  50 weeks to approximately 150 weeks... we have already placed orders for engines and packaged components for
  2027 and engines for 2028 and a portion of 2029." Also: "the relationships we've built with our suppliers,
  combined with our manufacturing capabilities, gives us a real advantage in an environment where equipment
  lead times remain extended. We intend to use that advantage."

**Judgment**: This is the strongest file in the batch. Three features distinguish it from the oilfield-services
false positives below: (1) the constraint is on the **engine/compressor manufacturing supply chain**
(Caterpillar/Ariel-type OEMs), not on oil/gas drilling activity — management explicitly disclaims direct
commodity-price exposure; (2) the lead-time escalation is **dramatic and monotonic across a full commodity
cycle** (4-6 months in 2013 → ~1 year in 2018 → 150 weeks/~3 years by 2026), i.e. it does not shrink back in
downturns the way HAL/PTEN/NOV lead times do; (3) USAC explicitly frames itself as the **beneficiary** — tight
new-equipment supply raises the value/pricing power of its large existing owned fleet, and its 2026 J-W Power
acquisition gives it in-house manufacturing capability to jump the queue, an moat-widening angle. The demand
driver (gas gathering/compression volume growth tied to LNG exports + Permian associated gas + AI gas-power
pull) is a multi-year secular story, not a single price spike.

**Verdict: STRONG.** New thesis candidate — "gas compression equipment scarcity," beneficiary = large owned-fleet
operators with OEM ties (USAC). No overlap with existing themes.

---

## NOV (National Oilwell Varco) — capital equipment for drilling (offshore rigs, downhole tools)

**Ticker overlap**: none directly, but conceptually adjacent to `oil-gas-energy`'s oil-macro leg (XOM/CVX/COP) if
promoted as an oil-services/capex name.

**Quotes** (spanning 2007→2026):
- 2026-04-28 (most recent): "we're taking in orders, we're looking at lead times that are already extending into
  2028 for some projects." Context: tied explicitly to a Middle East conflict disrupting logistics that quarter
  ("the conflict escalated during the quarter... movement of goods, access to customer sites, and overall
  logistics became increasingly constrained") plus a "renewed focus on energy security" reinvestment narrative,
  and a claim that "for much of the past decade, the industry has operated with constrained investment."
- 2021-10-27 (COVID supply-chain crunch): "Lead times for forgings have extended out from 6 weeks to 18 weeks"
  — resins/epoxy/fiberglass "remain critically low," steel/plate prices up 240% YoY. This is NOV as a **victim**
  of input shortages, not a beneficiary — margins were squeezed, not expanded.
- 2023-07-27: "supplier reliability and lead times are broadly improving" — i.e. the 2021-22 crunch was already
  normalizing by mid-2023.
- 2013-07-30: "I know you guys have reduced your lead times significantly" (analyst, describing a period of
  *improving*, not extending, lead times).
- 2020-02-07 (downturn): no tight-supply language; discussion is about order deferrals, not equipment scarcity.

**Judgment**: NOV's lead-time commentary tracks the oil capex cycle closely — tight in booms (2007, 2026),
improving/absent in downturns (2013, 2020), and in 2021-23 the "extending lead times" episode was explicitly a
COVID input-shortage story that NOV described as a headwind, not a pricing-power tailwind, and one that resolved
within 18 months. The 2026 datapoint is real but is bundled with a geopolitical logistics disruption (temporary)
and a decade-of-underinvestment narrative that, on its own history, has not proven durable — NOV's own quotes
show lead times compressing again whenever capex slows. This is the cyclical pattern the brief specifically
flagged to watch for in HAL/PTEN/NOV.

**Verdict: WEAK.** Real language, but tracks the oil/gas capex cycle rather than a persistent structural
bottleneck; NOV has been both victim (COVID input shortages) and beneficiary (order backlog) depending on the
phase of the cycle, which is inconsistent with a durable pricing-power thesis.

---

## TNRSF / TS (Tenaris) — OCTG (oil country tubular goods) / seamless & welded pipe

**IMPORTANT DATA NOTE**: TNRSF and TS are **the same company** (Tenaris S.A.). TS is the NYSE ADR; TNRSF is the
OTC/pink-sheet ticker for the ordinary shares. Every transcript slug, publish date, and quote text pulled for
the two tickers is identical (verified: `transcript-TNRSF-2026-02-19` and `transcript-TS-2026-02-19` are
word-for-word the same document). Treating as one company, one verdict.

**Ticker overlap**: none directly in themes.yaml; oil-gas-energy covers upstream/downstream+LNG+gas-power, not
pipe/tubular manufacturing.

**Quotes** (spanning 2007→2026, only representative found):
- 2026-02-19: "we continue to consolidate our presence with the award of a long-term agreement for the supply
  of OCTG to the Northwest field development in Qatar... We have, in many cases, long-term agreements that have
  some formulas related to raw materials... the majority of our backlog and our business in international
  market are driven by stability in the pricing."
- 2024-04-26: "our long-term agreement with QatarEnergy LNG has also been extended for 3 years" — a contract
  *extension*, i.e. steady-state customer relationship renewal, not a new scarcity signal.
- 2018-11-01 (analyst asks directly about pricing power): "whether you're actually seeing any pricing power with
  your customers outside of North America" → Tenaris's own answer: "the pricing in the international market
  remains challenging. The competitive environment continues to be challenging" — **company explicitly denies**
  having broad pricing power.
- 2015-08-08: "on allocation of material in the different regions" — this is a false-positive match; it refers
  to internal capital/cost allocation across regions, unrelated to product scarcity.
- No "sold out" match found anywhere in the corpus for this ticker across 19 years of transcripts sampled.

**Judgment**: The overwhelming majority of matches are "long-term agreement," which for Tenaris describes
standard OCTG supply-contract relationships with national oil companies (Qatar, Saudi, ADNOC) renewed on
multi-year cycles — this is how Tenaris has always sold pipe to these customers, not a new "supply is tight"
signal. "Lead time" hits refer to Tenaris's own internal steel-procurement planning lead time (an operational
detail), not customer-facing scarcity. Where the transcript addresses pricing power directly, management denies
having it outside a narrow premium segment. No structural-bottleneck claim by the company anywhere in the
sample.

**Verdict: WEAK** (applies to both TNRSF and TS — same company, same verdict). Thin, dominated by generic
contract-renewal language; the one place pricing power is asked about directly, the company denies it.

---

## HAL (Halliburton) — oilfield services (pressure pumping / completions)

**Ticker overlap**: none directly; adjacent to `oil-gas-energy` if promoted as an oilfield-services capex play.

**Quotes** (spanning 2006→2026):
- 2026-04-21 (most recent, exec Shannon Slocum): "the supply side of the equation... is a lot tighter than
  people think, and it would take just a little bit of demand coming back for pricing power to come back...
  we're getting calls. I think we're within a handful of fleets, of sort of premium fleets, dual fuel-type
  fleets of being absolutely sold out as an industry."
- 2022-07-19 (CEO Jeff Miller, repeated 5x across one call): "This market remains strong, steadily growing and
  all of it sold out... Halliburton remains sold out. As for the overall market, I believe it will be all but
  sold out for the second half of the year due to service company discipline, long lead times for new fleets
  and supply chain bottlenecks for consumables."
- 2017-10-23: "Our fleet is sold out for the remainder of the year and into 2018."
- 2020-07-20 (downturn): no "sold out"/pricing power language; instead: "we talked about projects being
  deferred but not necessarily cancelled."
- 2014-07-19 → 2009 → 2006: mild/absent tightness language outside up-cycle peaks.

**Judgment**: This is the textbook cyclical pattern flagged in the brief. "Sold out"/pricing-power claims from
HAL's own executives appear at every North American land-completions up-cycle peak (2017, 2022, 2026 — all
periods of rising rig count / completions activity) and disappear entirely during downturns (2020 COVID crash,
2014 late-cycle slowdown). This is oilfield-services cyclicality by definition — HAL's fortunes track
completions activity, itself a function of E&P capex which follows oil/gas prices. The 2026 language is real
and current, but the same words appeared in 2017 right before the 2018-2020 downturn erased them.

**Verdict: WEAK.** Real, current, company-sourced "sold out"/pricing-power language, but it is a recurring
cyclical up-cycle phenomenon, not a structural bottleneck independent of the commodity cycle — exactly the
pattern the brief asked to screen out.

---

## EPD (Enterprise Products Partners) — NGL/petrochemical midstream MLP

**Ticker overlap**: none directly; adjacent to `oil-gas-energy` gas-power leg conceptually.

**Quotes**:
- 2026-04-28 (most recent): "anywhere from 12 MMbpd to 15 MMbpd of crude oil, refined products, LPG, and
  petrochemical supplies are constrained" — this is EPD management discussing the **macro/global** supply
  impact of a Strait of Hormuz closure (a geopolitical event affecting world oil markets), not EPD's own
  business being supply-constrained. Off-topic for this review's purpose.
- 2022-11-01: "on the downstream side, I would say there's probably about 90% of our business that's take or
  pay type contracts." Per the brief's explicit caution, take-or-pay is EPD's baseline MLP revenue model
  (de-risking mechanism), not a scarcity signal.
- 2015-04-30: "we're sold out through 2017 and we're probably 80% in 2018... We're essentially sold out of
  everything" — referring to export-dock/terminal throughput capacity. Context makes clear this reflects EPD's
  standard project-finance model: large capex terminal projects are pre-sold under long-term contracts before
  or at completion, not a surprise demand shock. This is how EPD always builds infrastructure.
- 2019-01-31 (analyst): "I thought that you were on allocation so the Seminole couldn't happen until after Shin
  Oak" — internal capacity-sequencing question, not a structural-scarcity claim.

**Judgment**: Matches are dominated by exactly the pitfall the brief called out for EPD/KMI — take-or-pay and
long-term-agreement language that describes EPD's normal MLP business model, not an emergent supply-tight /
pricing-power narrative. The one quantitatively strongest "sold out" language (2012, 2015) describes routine
pre-contracted terminal capacity, and the most recent (2026) "constrained" hit is about global oil-market macro
(Hormuz), unrelated to EPD's own operations.

**Verdict: WEAK.** Business-model boilerplate contamination as anticipated; no genuine emergent structural
bottleneck claim found.

---

## PTEN (Patterson-UTI Energy) — land drilling & pressure pumping

**Ticker overlap**: none directly; adjacent to `oil-gas-energy` if promoted as oilfield-services capex play.

**Quotes**:
- 2026-04-23 (most recent, CEO Andy Hendricks): "the frack industry has seen consolidation and bifurcation of
  equipment quality and efficiency. Lower-tier pricing has constrained cash generation for smaller peers,
  limiting their access to capital and slowing investment in new technology. This dynamic continues to widen
  the gap between industry leaders and the broader peer group." Also: "we're essentially sold out of everything
  that can burn natural gas" and "a number of our competitors are near sold out too."
- 2024-05-02: "Our natural gas-powered equipment continues to be sold out with high demand and a widening
  operating cost savings compared to diesel equipment."
- 2018-04-26 (up-cycle, analyst Q): "demand outstripping supply for the super-specs" (premium rigs).
- 2011-07-28 (up-cycle): "We are sold out of new rigs through the end of the year."
- 2016-04-28, 2014-02-06, 2007-08-02: no sold-out claims; mid/down-cycle periods show only routine lead-time
  color, no scarcity claims.

**Judgment**: This is a genuinely harder call than HAL. Like HAL, PTEN's "sold out" language recurs at up-cycle
peaks and is absent in between (2011, 2018, 2024, 2026 vs. silence in 2014-16) — the classic cyclical pattern.
*However*, unlike HAL's generic "market is sold out," PTEN's most recent two data points (2024 **and** 2026 —
two non-adjacent report periods, not just one price spike) specifically and consistently describe a **narrower,
structural sub-segment**: dual-fuel/natural-gas-burning fleets specifically, tied to an industry consolidation
narrative where weaker, undercapitalized peers structurally lose the ability to invest in new equipment
(permanent capital-access gap, not just a temporary price effect). That consolidation argument is a genuinely
structural claim (industry structure changed permanently post-2020 shale bust) layered on top of the ordinary
cyclical tightness. It is not as clean as USAC (PTEN's core business is still fully levered to the land-drilling
capex cycle), but it is not pure noise either.

**Verdict: UNCLEAR.** Real, twice-repeated (2024 + 2026), narrower-than-HAL claim about structural fleet
consolidation + dual-fuel equipment scarcity, but the underlying business remains highly cyclical to land
drilling capex. Recommend re-checking in 2-3 quarters to see whether the "sold out" language survives a
2026-27 activity pullback (which would validate the structural-consolidation read) or vanishes with it (which
would confirm ordinary cyclicality, same as HAL).

---

## BTU (Peabody Energy) — thermal & metallurgical coal

**Ticker overlap**: none.

**Quotes**:
- 2026-05-05 (most recent): "Two major forces emerged that both increased demand and constrained supply. The
  Iran conflict in late February caused a sharp rerating of thermal coal demand and prices moved upward."
- 2023-07-27: "supply remains constrained across major supply regions" (industry-wide seaborne thermal coal
  commentary) and "Metallurgical coal supply has remained constrained primarily due to residual impacts of wet
  weather events in Queensland" (a weather event, explicitly temporary — "the rate of exports... remains below
  historical rates").
- 2018-04-25, 2021-07-29: "take or pay" hits refer to contract renegotiation/elimination of onerous legacy
  contracts and a domestic customer agreement — routine contract administration, not scarcity signals.

**Judgment**: Every match found is either (a) BTU management giving **market/industry-wide** commentary on
global seaborne coal supply-demand balance for analysts' benefit (not a claim about BTU's own production being
constrained or BTU having pricing power from its own bottleneck), or (b) explicitly attributed to one-off events
(Iran conflict, Queensland weather) that are acknowledged as temporary. No "sold out," no "pricing power," no
company self-description as a structurally advantaged supplier anywhere in the sample. This is squarely the
generic-industry-vocabulary pitfall flagged by today's "trough" experiment — coal-market color, not BTU-specific
structural signal.

**Verdict: WEAK.** Thin and generic; no company-specific structural bottleneck claim.

---

## KMI (Kinder Morgan) — natural gas pipelines/midstream

**Ticker overlap**: none directly; conceptually adjacent to `oil-gas-energy`'s gas-power leg (EQT/LNG/SEI —
natural gas demand growth story) and to LNG feedgas-pull dynamics already referenced in that theme's notes.

**Quotes**:
- 2023-10-18 (the strongest single datapoint): discussing gathering/processing systems — "Bakken constrained,
  Eagle Ford approaching full processing capacity. And in the Haynesville, we're trying to keep up... So on the
  Haynesville being constrained, that means there's going to be opportunities for new projects... being at
  capacity on processing in the Eagle Ford. There may be **opportunities to charge incremental rate** there."
  This is a genuine capacity-tight → pricing-power claim, tied explicitly to LNG-export-driven feedgas demand
  growth ("as we see these LNG facilities come on").
- 2026-04-22 (most recent): "we're operating pretty much at our capabilities, at capacity" (KinderHawk gathering
  system) — a continuation of the same theme, though this snippet doesn't restate the pricing-power angle.
- 2026-04-22 (same call, x3): "take or pay" hits describing tank storage and LNG-export gas contracts — routine
  KMI business model language (per the brief's specific caution on KMI).
- 2021-07-21: "constrained from an infrastructure standpoint" (Stagecoach assets, positioning commentary) and
  "tight supply-demand balance" (macro commodity commentary, not KMI-specific).

**Judgment**: Most matches are ordinary take-or-pay/long-term-contract boilerplate, exactly as the brief warned.
But there is one genuine, explicit data point (2023-10-18) where KMI management directly links specific gathering
systems reaching physical capacity to an ability to raise rates — a real structural-tightness-to-pricing-power
claim, tied to the multi-year LNG-export buildout rather than a short commodity price swing. This is thinner and
less frequently repeated than USAC's evidence, but it is not pure noise, and it is conceptually a natural
extension of the gas-demand-pull narrative that `oil-gas-energy` already houses (LNG is already a ticker in that
theme; the theme's own notes acknowledge "gas leg has no clean ETF... single name or skip").

**Verdict: FOLD → oil-gas-energy (gas leg).** Evidence is real but too thin/infrequent to justify a standalone
new thesis; the underlying story (LNG feedgas pull tightening midstream gathering/processing capacity) is a
natural extension of the gas-demand-pull leg already present in `oil-gas-energy`, not a distinct new bottleneck
narrative.

---

## ALB (Albemarle) — lithium

**Ticker overlap**: `rare-earth-materials` theme note already evaluated and explicitly rejected ALB: "ALB(雅保,
鋰非稀土/銦鎵)契合度牽強,未納入basket" (2026-07-10). No theme currently covers lithium/battery-materials.

**Quotes** (checked specifically for recency given lithium price crash context):
- **2026-05-07 (most recent — the critical datapoint)**: only ONE constraint-phrase match in the entire most
  recent transcript, and it is generic: a question about brownfield project restart *timeline* ("what the lead
  time would be") for a hypothetical future capacity expansion — not a claim of current tight supply, sold-out
  conditions, or pricing power. **Zero "sold out," "pricing power," or "tight supply" language in the current
  (2026) transcript.**
- 2024-02-15 (during the lithium price crash, prices already well off 2022 highs): "at capacity" refers to one
  specific brine-processing train (La Negra) being brine-feed-limited pending a separate expansion project
  coming online — an operational bottleneck on ONE input stream, not an industry-wide "can't meet demand" claim,
  and management pairs it with news that Kings Mountain / Richburg growth **projects are being delayed/paused**
  because "the economics aren't there for those projects" at current (low) prices.
- 2021-11-04 (during the 2021-22 lithium price **boom**): "Our bromine volumes remain constrained due to
  sold-out conditions" — note this is the **bromine** business, not lithium, and "long-term agreement" hits
  describe fixed-price contract lag, a genuine pricing mechanic, but from the boom era.
- 2019-11-07 / 2018-02-28 (2018-19 up-cycle): "sold out... everything we make, we can sell" — genuine lithium
  tightness claims, but again from a prior up-cycle, 6-7 years stale.
- 2007-2013: "sold out" hits refer to legacy specialty-chemicals/HPC-catalyst businesses, unrelated to lithium.

**Judgment**: This confirms the brief's own hypothesis precisely. The genuine "sold out"/pricing-power lithium
claims are concentrated in the 2018-19 and 2021-22 up-cycles — both periods when lithium prices were rising or
elevated. Since the lithium price crash (2023 onward), ALB's own transcripts show **no current constraint
language** — instead, management describes delaying/pausing new project construction because economics don't
support it at current prices, the opposite of a supply-squeeze/pricing-power story. The discovery radar's
"49 quarters flagged" count for ALB is dominated by this stale boom-era language plus unrelated legacy-business
noise; it is not a live 2025-2026 signal.

**Verdict: WEAK.** Confirmed stale/legacy language — no genuine current (2024-2026) structural constraint
evidence; directly contradicted by ALB's own 2024-2026 commentary about delaying capacity projects due to weak
pricing.

---

## Summary table

| ticker | verdict | one-line reason |
|---|---|---|
| USAC | STRONG | Engine/compressor lead times escalating for 13 years (4-6mo→150wk), explicitly non-commodity-price-linked per mgmt; no theme overlap. |
| NOV | WEAK | Lead-time commentary tracks oil capex cycle (tight in booms, compresses in downturns); 2026 tightness bundled with a temporary geopolitical logistics disruption. |
| TNRSF | WEAK | Same company as TS (Tenaris ADR vs OTC ticker) — see TS. |
| TS | WEAK | Matches are mostly routine long-term OCTG supply-contract renewals; company itself denies broad pricing power when asked directly. |
| HAL | WEAK | "Sold out"/pricing-power language recurs at every NA completions up-cycle peak (2017/2022/2026) and vanishes in downturns — textbook oilfield-services cyclicality. |
| EPD | WEAK | Dominated by take-or-pay/long-term-agreement business-model boilerplate; "sold out" terminal capacity is routine pre-contracted project finance, not a scarcity shock. |
| PTEN | UNCLEAR | Cyclical like HAL, but 2024+2026 both show a narrower dual-fuel-fleet + industry-consolidation structural argument worth re-checking through a 2026-27 pullback. |
| BTU | WEAK | All matches are market-wide coal commentary or one-off events (Iran conflict, Queensland weather); no BTU-specific structural claim. |
| KMI | FOLD | One genuine capacity→pricing-power datapoint (2023, LNG feedgas pull on Bakken/Eagle Ford/Haynesville), but thin; natural home is oil-gas-energy's existing gas-demand-pull leg, not a new thesis. |
| ALB | WEAK | Genuine "sold out" language is stale (2018-19, 2021-22 up-cycles only); zero current (2024-2026) constraint language, consistent with the post-crash lithium bear market. |
