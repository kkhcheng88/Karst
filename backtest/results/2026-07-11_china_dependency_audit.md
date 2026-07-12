# China Dependency Audit — all 15 thesis / 68 unique tickers (2026-07-11)

## 0. Why this exists

`thesis/themes.yaml` carries a 2026-07-11 "China caveat" (header comment + `docs/2026-07-09_magnifier_model_plan.md` §4)
distilled from Edward Chancellor's *Capital Returns* ch.6: China's domestic bank-debt-forgiveness mechanism disables
the normal "capacity exit → supply discipline restored" signal our constraint-language methodology assumes. That
caveat only screened for **Type A** risk — is the candidate ticker *itself* China-domiciled/state-linked? None of
the 15 registered theses are.

The user pointed out this audit was too narrow. There is a second, distinct China risk that Type-A screening
misses entirely: **Type B — a US/allied company whose own manufacturing, supply chain, or revenue base materially
depends on China**, even though the company itself is not Chinese. Type B is not a Chancellor-style "kill-feature
disabled" mechanism; it is a straightforward geopolitical-shock channel — export controls, tariffs, or an outright
breakage of production/supply can hit these names directly. We also tag the mirror case, **Type C — a company
*restricted by* China policy from selling into China** (e.g. ASML), and reverse-blacklist cases (China barring a
US company from Chinese business, e.g. KTOS, MP, USAR).

## 1. Method

Every ticker in every `tickers:` list across all 15 themes in `thesis/themes.yaml` (68 unique names after dedup —
GLW and WDC each appear in two themes) was checked against 3 questions:

1. **Manufacturing** — does the company operate production/assembly/test facilities inside mainland China?
2. **Supply chain** — does a critical processing/fabrication step run through China such that the business
   couldn't function without that link? (Different from "sells into China.")
3. **Revenue concentration** — is revenue concentrated enough in mainland China that a policy shock would be a
   *serious* hit, not just "has some China sales"?

Research was done via 6 parallel subagents (WebSearch + SEC EDGAR text pulls), covering ~57 of the 68 tickers.
**One subagent (batch 6: oil/gas + AEHR/USAC/LPX/WST) died without producing output** (confirmed: its output file
exists but is 0 bytes) — those 11 tickers (XOM, CVX, COP, EQT, LNG, SEI, KMI, AEHR, USAC, LPX, WST) were instead
researched directly via WebSearch in this session, with the same evidence-discipline rules applied.

**Verdict tags** (a ticker can carry more than one):
- `NONE` — no material China dependency found
- `TYPE_A` — company itself is China-domiciled/state-linked (screened by the existing caveat; not expected/found
  among these 68, confirmed still true)
- `TYPE_B_MANUFACTURING` — production facility inside mainland China
- `TYPE_B_SUPPLY_CHAIN` — a critical process step depends on China
- `TYPE_B_REVENUE` — revenue concentrated enough in China that policy risk is material
- `TYPE_C_EXPORT_RESTRICTED` — the reverse: restricted BY policy (US or China) from selling into/out of China

**Evidence discipline**: every dependency claim below is tagged HIGH (verbatim 10-K/company-statement source
found) / MEDIUM (credible secondary source, not independently verified against a primary filing) / LOW or
**未證實 (unverified)** (could not confirm — stated explicitly rather than guessed). Nothing below is fabricated;
where a number couldn't be pinned down, that is said outright.

---

## 2. Summary table — all 68 tickers

| Ticker | Theme(s) | Verdict | One-line evidence | Confidence |
|---|---|---|---|---|
| MU | memory-supercycle | TYPE_B_MANUFACTURING, TYPE_B_REVENUE, TYPE_C | Xi'an DRAM/NAND A&T ($600M packaging/test expansion); China+HK ≈10-12% rev; 2023 CAC critical-infra ban | HIGH |
| SNDK | memory-supercycle | TYPE_B_SUPPLY_CHAIN, TYPE_B_REVENUE | Sold Shanghai OSAT to JCET 2024 but locked into $550M/yr min. purchase; China+HK ≈45% FY25 rev | HIGH |
| WDC | memory-supercycle, advanced-packaging | TYPE_B_MANUFACTURING, TYPE_B_REVENUE | Shenzhen A&T (smallest of its sites, PP&E $87M); China+HK ≈27% FY25 rev | HIGH |
| SKHY | memory-supercycle | TYPE_B_MANUFACTURING (severe), TYPE_B_REVENUE, TYPE_C | Wuxi fab ≈40% of global DRAM output; Dalian NAND; Chongqing packaging; 2025 US export-control equipment-upgrade ceiling | HIGH |
| COHR | photonics-optical | TYPE_B_MANUFACTURING | 10-K names China among production/R&D countries; ~12% FY25 rev (stockanalysis.com breakdown) | MEDIUM |
| LITE | photonics-optical | TYPE_B_MANUFACTURING (unresolved conflict), TYPE_B_REVENUE | China-registered mfg entity found (Shenzhen/Wuhan) vs. a separate extract naming only US/Japan/Thailand/UK — **unresolved, needs primary-source check**; ~22% rev (2023, unverified) | LOW-MEDIUM |
| AXTI | photonics-optical | **TYPE_B_MANUFACTURING (HIGH), TYPE_B_SUPPLY_CHAIN (HIGH)** | 10-K verbatim: "All of our substrate products... manufactured in the PRC"; Beijing Tongmei; 1,049/1,075 employees in China; hit twice by Chinese export licensing (Ga/Ge 2023, InP 2025) | **HIGH — highest-severity ticker in the whole audit** |
| MRVL | photonics-optical, tpu-custom-silicon (n/a) | TYPE_B_REVENUE, TYPE_C | Fabless (TSMC Taiwan); China 36-43% by ship-to but 10-K itself notes much is "ship-to-China-for-global-customer," overstating true end-market exposure; declining | MEDIUM-HIGH |
| AAOI | photonics-optical | TYPE_B_MANUFACTURING | 10-K verbatim: Ningbo plant (Global Technology/Prime World) does labor-intensive transceiver assembly; 2,881/4,691 employees in China; $300M Sugar Land TX reshoring underway | HIGH |
| SIVE | photonics-optical | NONE | = Sivers Semiconductors AB (Kista, Sweden; OMXSTO:SIVE/OTC:SIVEF); InP laser fab in Glasgow, Scotland; explicitly positioned as non-China CPO alternative | MEDIUM |
| LWLG | photonics-optical | NONE | US-only (Englewood CO); pre-revenue; partners with Tower Semi's Newport Beach CA fab | HIGH |
| GLW | photonics-optical, advanced-packaging | TYPE_B_MANUFACTURING | Shanghai optical-fiber plant (CSFOC, Optical Comms segment) + Beijing/Chongqing/Hefei/Wuhan Display-glass plants (different segment); revenue % unverified (search extract had an internal contradiction, discarded) | HIGH (facilities) / unverified (rev %) |
| FN | photonics-optical | NONE (mfg) + TYPE_B_SUPPLY_CHAIN (minor) | Thailand-primary, 15-yr tax-locked; owns Casix crystal/optics fab in Fuzhou (minor input supplier, materiality unverified) | HIGH (Thailand) / LOW (Fuzhou materiality) |
| GEV | ai-power-grid | **TYPE_B_SUPPLY_CHAIN (HIGH), TYPE_C, TYPE_B_MANUFACTURING** | CEO Strazik (Reuters Dec-2025) confirmed China's yttrium export curbs threaten GEV's global H-class turbine fleet (blade coatings); NdFeB magnet dependency in Haliade-X (Arafura MoU to de-risk); Qinhuangdao JV assembly | **HIGH — sharpest supply-chain finding in the audit** |
| BE | ai-power-grid | TYPE_B_SUPPLY_CHAIN (contested, unresolved), TYPE_C (contingent) | Hunterbrook investigation (~Jul-2026) alleges China-linked scandium-oxide supply into Newark plant; Bloom's 8-K denies without naming suppliers; scandium independently confirmed under active China export license since Apr-2025 | MEDIUM (unresolved dispute) |
| VRT | ai-power-grid | TYPE_B_MANUFACTURING, TYPE_B_SUPPLY_CHAIN (shrinking) | Shenzhen mfg anchor since 2000 (~70% historical APAC volume) + Mianyang/Jiangmen/Suzhou; actively diversifying to Mexico/Malaysia | MEDIUM-HIGH |
| ETN | ai-power-grid | TYPE_B_MANUFACTURING | 50%/49% JVs (Jiangsu Huineng/Ryan Electrical) + Jining site since 1993; no chokepoint found; APAC <10% of revenue | HIGH (mfg) |
| PWR | ai-power-grid | **NONE (verified clean)** | Zero "China" mentions across full FY24 10-K text search; zero China entities among 305 subsidiaries (Ex. 21.1) | HIGH |
| MPWR | ai-power-grid | **TYPE_B_MANUFACTURING, TYPE_B_SUPPLY_CHAIN, TYPE_B_REVENUE** | Chengdu mfg+test (owned); 10-K names China supplier-concentration as a top risk verbatim; China = 55.3% FY25 rev (ship-to, rising from 51.4% FY23) | **HIGH — highest-dependency ticker in the whole audit** |
| VICR | ai-power-grid | TYPE_B_REVENUE (moderate, declining) | No mfg (Andover MA only; China = sales-support offices); China+HK = 12.6% (2024), down from 18.8% (2022); Section-301 tariff cost disclosed | HIGH |
| NVTS | ai-power-grid | **TYPE_B_REVENUE (severe)** | No mfg (fabless, Taiwan/Philippines A&T); China = 47% (2025) end-customer basis, down from 60-62% (2023-24) — still largest revenue-concentration in the audit | HIGH |
| WOLF | ai-power-grid | TYPE_B_REVENUE (moderate) | No mfg (NC/NY/AR + Malaysia A&T); company explicitly disclaimed Ga/Ge exposure (Jul-2023 statement); mainland China 9.3% FY25 ship-to (rising from 3.1% FY23), ~20-24% w/ HK | HIGH |
| ON | ai-power-grid | TYPE_B_MANUFACTURING, TYPE_B_SUPPLY_CHAIN (partial) | Leshan JV (80%, historically state-linked partner) + Shenzhen (wholly owned since 1984) + Suzhou; revenue % obscured — 10-K discloses by *billing jurisdiction* (HK/UK/Singapore/US), no China line exists; secondary "~30%" claim unverified | HIGH (mfg) / unverified (rev%) |
| TXN | ai-power-grid | TYPE_B_MANUFACTURING, TYPE_B_SUPPLY_CHAIN, TYPE_B_REVENUE | Chengdu fab+A&T+wafer-bump, Shanghai; 10-K verbatim: 21% rev by customer-HQ / ~50% by ship-to (2025); named in Sept-2025 China MOFCOM anti-dumping probe on US legacy analog chips | HIGH |
| GNRC | ai-power-grid | TYPE_B_MANUFACTURING (contained) | Foshan/Pramac owned plant (Guangdong, via 2016 acquisition); tariff-exposed, no chokepoint found; China rev bundled in 16.2% "International," not broken out | HIGH (mfg) / unverified (rev%) |
| SPXC | ai-power-grid | TYPE_B_MANUFACTURING (small) | Suzhou plant (SPX Cooling Technologies); 10-K: "not significantly dependent on any one... suppliers"; China = 3.27% FY24 rev (rising from 2.5%) | HIGH |
| CAT | ai-power-grid | **TYPE_B_MANUFACTURING (extensive), TYPE_C** | Deepest China footprint of all 68 tickers: 6 cities (Suzhou/Wujiang/Xuzhou/Qingzhou/Tianjin/Wuxi/Shanghai), 4 segments, 30-yr history; ~$2.6B 2026 tariff cost (partly China-driven); rare-earth dependency searched, not disclosed | HIGH (mfg) / MEDIUM (tariff) |
| AMKR | advanced-packaging | TYPE_B_MANUFACTURING | Shanghai plant, described as "2nd-largest factory by revenue" (secondary source); China ≈9% of PP&E vs Korea ~54%; China revenue % unverified | MEDIUM-HIGH |
| ASX | advanced-packaging | TYPE_B_MANUFACTURING, TYPE_B_REVENUE (caveat) | Kunshan/Shanghai/Weihai OSAT facilities confirmed; "60% Greater China" figure conflates Taiwan+mainland — **do not cite as mainland-only** | HIGH (facilities) / MEDIUM (rev, caveat) |
| TTMI | advanced-packaging | TYPE_B_MANUFACTURING | 4 PCB plants (Huiyang/Dongguan/Guangzhou/Zhongshan), ~9,900 China employees; already divested highest-risk consumer-mobility China unit in 2020 ($550M sale) | HIGH (facilities) / unverified (rev%) |
| INTC | advanced-packaging | TYPE_B_MANUFACTURING (partial), TYPE_B_REVENUE | Chengdu A&T (largest by shipped volume); Dalian NAND fab fully divested to SK Hynix (final Mar-2025); China+HK ≈29% FY24 rev | HIGH |
| MKSI | advanced-packaging | TYPE_B_MANUFACTURING (unconfirmed detail), TYPE_B_REVENUE, TYPE_C | 10-K names China generically among mfg countries (Israel/Mexico/Singapore/China), no facility/% pinned down; China ≈22-24% rev | LOW-MEDIUM |
| KLAC | advanced-packaging | TYPE_B_REVENUE, TYPE_C | No mfg found; China revenue 41%→33% FY24→FY25, explicitly attributed to tightened US export controls | MEDIUM-HIGH |
| STX | advanced-packaging | TYPE_B_MANUFACTURING (structurally significant) | Wuxi = 1 of only 2 remaining global Seagate mfg sites (other = Thailand; Suzhou closed 2017); revenue not broken out by China in 10-K (only Singapore/US/Netherlands/Other) | MEDIUM-HIGH |
| KLIC | advanced-packaging | **TYPE_B_MANUFACTURING, TYPE_B_REVENUE** | Suzhou die-bonder production site; 10-K verbatim: "approximately 53.5% of net revenue for fiscal 2025 was for shipments to customers headquartered in China" | **HIGH — cleanest revenue evidence in the audit** |
| TER | advanced-packaging | TYPE_B_REVENUE (modest), TYPE_C | No mfg found (US/Malaysia); China = 13% FY24 rev, tied with US — smallest of the equipment names | MEDIUM-HIGH |
| FORM | advanced-packaging | TYPE_C (shrinking TYPE_B_REVENUE) | No mfg found; China revenue 14%→7% FY24→FY25, sharpest export-control-driven drop found in the audit | HIGH |
| LRCX | advanced-packaging | TYPE_B_REVENUE, TYPE_C | No mfg found (Shanghai entities read as sales/service only); China 42%→34% FY24→FY25, still the single largest country | HIGH |
| RKLB | space-satellite | NONE | US (Long Beach/Albuquerque/Tucson/Wallops)/NZ vertically integrated; no China facility or revenue disclosed | HIGH |
| ASTS | space-satellite | NONE | Midland TX + Spain/Israel/India/Scotland engineering; no China link disclosed | HIGH |
| KTOS | space-satellite | TYPE_C_EXPORT_RESTRICTED | Apr-2025: placed on China MOFCOM "Unreliable Entity List" (Taiwan tech-cooperation allegation) — reverse risk, not a dependency | MEDIUM-HIGH |
| HEI | space-satellite | NONE (lower confidence — partial doc coverage) | No China mfg found; only a dated (2007) CASGC distribution-access relationship, likely minor/inactive | MEDIUM |
| LOAR | space-satellite | NONE | 11 US + Germany/UK/France facilities only; only China mentions are data-privacy boilerplate | HIGH |
| RDW | space-satellite | NONE | Only China mention: named as a potential future low-cost *competitor*, not a supplier/customer | HIGH |
| LUNR | space-satellite | NONE | Zero "China"/"PRC" mentions in FY25 10-K | HIGH |
| BKSY | space-satellite | NONE | In-house satellite build, Tukwila WA; no China link | HIGH |
| PL | space-satellite | NONE | Zero China mentions; mfg expansion cited is Germany | HIGH |
| GSAT | space-satellite | NONE | Satellites procured from MDA Space (Canada); no China link | HIGH |
| MP | rare-earth-materials | **TYPE_B_SUPPLY_CHAIN (historical, unwinding), TYPE_B_REVENUE (historical, ceased)** | Textbook case: concentrate shipped to Shenghe/Chinese refiners because MP lacked own separation capacity; China >90% of revenue historically → 0% since Jul-2025 DoD deal; heavy-REE (Dy/Tb) separation gap persists until mid-2026; now also blacklisted by China from importing equipment/tech | HIGH |
| USAR | rare-earth-materials | NONE (core) | Deliberately China-free design (Stillwater OK, Round Top TX); blacklisted from buying Chinese-origin equipment (minor reverse risk) | MEDIUM |
| AVGO | tpu-custom-silicon | TYPE_B_REVENUE (moderate, declining) | Fabless (TSMC Taiwan); China (incl. HK) 17% FY25 rev (down from 20% FY24); 10-K itself notes much is ship-to-for-global-customer | HIGH |
| TSM | tpu-custom-silicon | TYPE_B_MANUFACTURING (small scale) | Nanjing + Shanghai legacy-node (16/28nm) fabs; China revenue ~9% (2025), down from ~22%; **primary risk is Taiwan Strait, not mainland dependency** | MEDIUM-HIGH |
| CLS | tpu-custom-silicon | TYPE_B_MANUFACTURING | Suzhou/Dongguan/Shanghai confirmed (company site); revenue % unverified (bundled in "Asia" 75% aggregate) | HIGH (facilities) / unverified (rev%) |
| XOM | oil-gas-energy | TYPE_B_MANUFACTURING (minor) | Fujian refining/petrochemicals JV (with Aramco/Sinopec) since 2007; evaluating Huizhou/Guangdong chemical complex; revenue % unverified, likely immaterial vs. XOM's global scale | MEDIUM |
| CVX | oil-gas-energy | NONE (low confidence — absence of evidence) | No material current China JV/operations surfaced in this pass | LOW |
| COP | oil-gas-energy | NONE (low confidence — absence of evidence) | No material current China JV/operations surfaced in this pass | LOW |
| EQT | oil-gas-energy | NONE | Domestic Appalachian gas producer; no China business-model exposure | MEDIUM-HIGH |
| LNG | oil-gas-energy | TYPE_B_REVENUE (contractual, moderate) | PetroChina (1.2 mmtpa combined, 2 SPAs) + Sinochem (up to 1.8 mmtpa, 17.5-yr, 2021); ~20 China-linked US LNG SPAs industry-wide (~25 mmtpa); **but** Feb-2026 reporting: China not currently lifting US LNG cargoes (redirect/resale amid tariff tension) — contracted exposure real, current physical offtake apparently diverted; % of Cheniere's own portfolio to China unverified | MEDIUM |
| SEI | oil-gas-energy | NONE | US domestic power-gen/proppant-logistics model; no China exposure found | MEDIUM |
| KMI | oil-gas-energy | NONE | North America-only pipelines/storage; no China exposure found | HIGH |
| AEHR | semicap-equipment | TYPE_B_REVENUE (indirect, unverified %) | Extreme single-customer concentration (67-88%, understood to be onsemi, which has its own China JV exposure — indirect, not independently confirmed); FY25 Asia revenue declined citing EV/power-semi demand softness (implies real Asia/China-linked SiC-EV end-market exposure); no direct China revenue % found in 10-K | LOW-MEDIUM |
| ATI | aerospace-specialty-alloys | **TYPE_B_MANUFACTURING, TYPE_B_SUPPLY_CHAIN** | 60%-owned Shanghai STAL JV (PRS finishing, since 1995, +65% capacity 2019); 10-K verbatim: sources zirconium/hafnium/molybdenum partly from China, names China export-control risk explicitly | HIGH |
| CRS | aerospace-specialty-alloys | TYPE_B_MANUFACTURING (confirmed) | 10-K Item 2 verbatim: owns/leases mfg facilities "including... China"; Shanghai office (2009)/Suzhou warehouse (2010)/possible Changshu site — scale not fully characterized; **notably, unlike ATI, CRS's own raw-material risk language does NOT name China** | HIGH (facility exists) / MEDIUM (scale) |
| ASML | euv-lithography-monopoly | **TYPE_C_EXPORT_RESTRICTED, TYPE_B_REVENUE (historical/reversing)** | No mfg in China (Veldhoven NL); China = 33% of FY25 net system sales (was largest single market, spiked to 42% Q3 as customers front-ran restrictions), guided down to ~20% for 2026; bipartisan US "MATCH Act" pending would bar DUV exports to China entirely | HIGH |
| FSLR | us-solar-manufacturing | TYPE_C_EXPORT_RESTRICTED / TYPE_B_SUPPLY_CHAIN (input-material only) | Mfg confirmed non-China (OH/India/Vietnam/Malaysia); avoids China-dominated polysilicon chain (CdTe tech) — **but** China controls ~75-76% of global tellurium production and imposed Feb-2025 export controls on tellurium/CdTe specifically; FSLR's own 10-K discloses active mitigation (alt suppliers, license applications, recycling) | HIGH (export control) / MEDIUM (cost-share claim) |
| USAC | gas-compression-equipment | NONE | US-only compression services; lead times (120+ wks) driven by Caterpillar engine availability, not China; no China link found | HIGH |
| LPX | specialty-siding-pricing-power | NONE | 20+ North/South America mfg facilities; no China link in supply-chain sourcing found | MEDIUM-HIGH |
| WST | glp1-biologics-packaging | TYPE_B_MANUFACTURING (confirmed) | Two Qingpu, Shanghai plants (injection molding since 2009; compression molding since 2013; 250 employees) — appears to serve APAC pharma market rather than feed a global HVP bottleneck; China revenue % unverified | MEDIUM-HIGH |

---

## 3. Findings by theme, with recommended `themes.yaml` note additions

### memory-supercycle (MU, SNDK, WDC, SKHY) — **all 4 tickers carry real Type B exposure**
Every ticker in this thesis has China manufacturing and/or heavy China revenue concentration. SKHY is the most
severe (Wuxi ≈40% of global DRAM output, under a live US export-control equipment-upgrade ceiling). MU carries a
live *revenue-restriction* risk too (2023 CAC ban on critical-infrastructure sales). **Recommend**: add a note that
the whole memory-supercycle basket has structural China exposure on both the manufacturing side (Xi'an/Shenzhen/
Wuxi/Dalian/Chongqing) and the demand side (10-45% of revenue by name) — this is a supply-chain concentration risk
layered on top of the existing cyclical-top kill condition, not a reason to exit, but worth flagging as a
correlated tail risk across the whole basket (a China policy shock hits all 4 names at once, undermining the
"diversified across 4 tickers" framing).

### photonics-optical (COHR, LITE, AXTI, MRVL, AAOI, SIVE, LWLG, GLW, FN) — **AXTI is a standout case**
AXTI is not just "has China exposure" — it is effectively a China-domiciled manufacturer wearing a US ticker (100%
of substrate production is in Beijing per its own 10-K), and its revenue has already been directly throttled twice
by Chinese export licensing (Ga/Ge 2023, InP 2025). The existing wiki already flags AXTI's InP-quota exposure
(#115, "中國僅精準批次放行") as a *supply* story; this audit adds the *manufacturing-location* dimension, which is
new. AAOI and GLW also carry real China manufacturing. SIVE/LWLG/FN are clean. **Recommend**: elevate AXTI's
existing kill-condition language to explicitly name it as a dual-exposure case (production *and* export-license
risk both sit in Beijing) — a further tightening of Chinese export controls on InP could hit AXTI on both fronts
simultaneously, not just the "China batch-releases InP" framing currently in the wiki.

### ai-power-grid (14 tickers) — **the largest and most consequential cluster in this audit**
Two standout findings:
1. **GEV**: not a revenue story at all — a CEO-confirmed (Reuters) supply-chain chokepoint. China's yttrium export
   restrictions threaten GEV's H-class gas-turbine fleet (thermal barrier coatings), and GEV's Haliade-X wind
   turbine has a separate rare-earth-magnet dependency it is actively trying to de-risk (Arafura MoU). This sits
   directly inside the thesis's own bottleneck story (AI-power buildout) — a China rare-earth shock could remove
   supply of the very turbines the thesis is long.
2. **MPWR**: the single highest-dependency ticker in the *entire* 68-ticker audit — Chengdu manufacturing, an
   explicit 10-K risk-factor naming China supplier concentration, and 55.3% of revenue from China (rising). This
   is also one of the thesis's flagged "90th-pctile quality" names (89% ttm_pe).
   Also notable: **NVTS** (47-62% revenue concentration, the single largest revenue exposure found anywhere in the
   audit), **TXN** (Chengdu fab + named in a live China anti-dumping probe), **CAT** (deepest China manufacturing
   footprint of all 68 tickers — 6 cities, 4 segments), and **BE** (a genuinely unresolved scandium-supply dispute
   that the company itself is actively contesting).
   PWR is the one clean name (verified zero China exposure across the full 10-K).
**Recommend**: this thesis's kill_condition doesn't currently mention China policy risk at all. Given GEV's
turbine-coating exposure sits inside the thesis's own physical-bottleneck story, and MPWR/NVTS carry the two most
extreme revenue-concentration numbers in the whole audit, recommend adding an explicit China-policy sub-clause to
the kill_condition (e.g., "OR China tightens rare-earth/yttrium export controls further, hitting GEV turbine supply
or MPWR/NVTS/TXN China revenue directly").

### advanced-packaging (13 tickers, minus WDC/GLW already counted above)
KLIC has the cleanest, highest-confidence China-revenue disclosure in the *entire audit* (53.5% verbatim from its
own 10-K) alongside a real Suzhou production site. ASX, AMKR, TTMI, STX all have confirmed China manufacturing.
KLAC/TER/FORM/LRCX have no manufacturing exposure but carry large, *declining* China revenue shares — all four are
explicitly attributed by their own filings to tightening US export controls (this is the cluster's dominant China
story: demand being cut by US policy, not a supply dependency). **Recommend**: split the note into two distinct
China risks for this thesis — (a) manufacturing/supply exposure (ASX/AMKR/TTMI/STX/KLIC — a China-side shock risk)
vs. (b) revenue exposure being actively *reduced by US export policy* (KLAC/TER/FORM/LRCX/MKSI — a US-side policy
risk that's already playing out and shrinking these names' China revenue, which arguably de-risks rather than
threatens the packaging-equipment sub-basket going forward).

### space-satellite (10 tickers) — **confirms the thesis is genuinely walled off from China**
9 of 10 names came back clean; the one exception (KTOS) is the *reverse* case — blacklisted BY China in April 2025
over Taiwan-related tech cooperation, which if anything reinforces this cluster's ITAR/defense-insulated
positioning rather than undermining it. **Recommend**: no note change needed; this cluster is correctly understood
as China-independent, and the KTOS blacklist is worth one line as color (not a risk) — evidence that this basket's
US-defense positioning is real enough that China itself treats it as adversarial.

### rare-earth-materials (MP, USAR) — **MP is the canonical Type B case; note is now stale**
This is the single most important finding to act on. MP is the textbook illustration of exactly the risk the user
asked about: historically >90% of revenue came from selling rare-earth *concentrate* to Shenghe Resources (a
minority MP shareholder) for refining in China, because MP itself lacked separation capacity. That dependency was
deliberately and rapidly cut to zero starting July 2025 under the DoD/DoW $400M partnership — but MP still can't
separate heavy rare earths (dysprosium/terbium) domestically until its new circuit commissions mid-2026, meaning
the company is not yet fully independent of the capability China provides, only of the *revenue relationship*.
China has also since blacklisted MP from importing Chinese processing equipment/technology — a new reverse-risk
layer. **Recommend**: this is the single highest-priority themes.yaml update coming out of this audit. The current
`rare-earth-materials` note doesn't mention any of this — it should explicitly record (a) MP's *historical* China
concentrate-refining dependency as context for why the DoD deal was structurally necessary, not just a nice-to-
have, (b) the heavy-REE domestic-capability gap that persists until mid-2026 as an interim risk window, and (c) the
new China equipment-import blacklist as a fresh, current risk. USAR remains clean (deliberately anti-China design)
modulo the same minor blacklist caveat.

### tpu-custom-silicon (AVGO, TSM, CLS)
TSM's China story is categorically different from every other ticker in this audit and should not be conflated
with the others: its small Nanjing/Shanghai fabs and shrinking (~9%) mainland revenue share are minor; its
dominant "China" risk is the Taiwan Strait — a China invasion/blockade scenario threatening TSM's *home* Taiwan
production base (90% of the world's most advanced chips), which is a different risk category entirely from "TSM
depends on mainland China." AVGO's headline China revenue (17-20%) is fabless/ship-to and, per its own 10-K,
substantially inflated by shipments that end up in devices sold in the US/Europe. CLS has confirmed Suzhou/
Dongguan/Shanghai manufacturing but revenue materiality couldn't be pinned down. **Recommend**: add a one-line
clarification distinguishing "TSM Taiwan Strait risk" from "TSM mainland China dependency" if this thesis's note
is ever read as implying the latter — they are not the same risk and shouldn't be sized the same way.

### oil-gas-energy (XOM, CVX, COP, EQT, LNG, SEI, KMI) — **mostly clean, one real nuance on LNG**
Most of this cluster is genuinely China-independent (EQT, KMI, SEI domestic; CVX/COP no material China ops found in
this pass, though confidence is low rather than a hard confirmed zero). XOM has a minor, decades-old Fujian
refining JV — immaterial at XOM's scale. The one real finding worth a note: **Cheniere (LNG)** carries real
long-term contractual exposure to Chinese buyers (PetroChina + Sinochem SPAs, part of an industry-wide ~25 mmtpa
of China-linked US LNG contracts) — but as of Feb-2026 reporting, China is not currently lifting US LNG cargoes at
all (redirecting/reselling elsewhere amid tariff tension), meaning the *contracted* exposure is real but the
*current physical* offtake relationship has already been disrupted by trade tension. **Recommend**: add a note to
the oil-gas-energy thesis (gas leg) flagging LNG's China-counterparty contract book as a live, already-partially-
disrupted risk — worth watching whether China resumes lifting cargoes or the contracts get renegotiated/redirected
long-term.

### semicap-equipment (AEHR)
No direct China revenue % could be found in AEHR's own 10-K in this pass. The real signal is indirect: AEHR's
revenue is extremely customer-concentrated (67-88% one customer, understood to be onsemi), and onsemi itself has a
China JV (Leshan). AEHR's FY2025 Asia revenue also declined, explicitly attributed to EV/power-semi demand
softness — consistent with (but not proof of) a China-linked SiC-EV end-market exposure. **Recommend**: mark as
"未證實/possible indirect exposure via customer concentration" rather than a confirmed dependency — this needs a
direct primary-source follow-up (AEHR's 10-K geographic-revenue note) before it goes into the thesis note as a
settled fact.

### aerospace-specialty-alloys (ATI, CRS) — **a real, well-evidenced asymmetry between the two names**
ATI is the stronger case: a named, 60%-owned equity JV manufacturing facility in Shanghai *plus* an explicit 10-K
risk-factor naming China as a source of zirconium/hafnium/molybdenum with disclosed export-control risk — directly
on point for the thesis's own supply-chain-input framing. CRS has confirmed China manufacturing/distribution
presence in its own 10-K Item 2, but — notably — its raw-material risk disclosure does **not** name China, despite
using similar nickel/cobalt/titanium inputs to ATI. **Recommend**: since the thesis note currently treats ATI+CRS
as one merged story ("同一個航太特種合金LTA鎖客護城河"), add a line noting the two names are *not* symmetric on
China exposure — ATI has a disclosed, named critical-material China dependency; CRS's China exposure is manufacturing/
distribution-only per its own filing, with no disclosed raw-material link.

### euv-lithography-monopoly (ASML) — **note already gets the "priced-in" story right; add the China-policy angle**
ASML's China story is real, large, and actively deteriorating: China was ASML's #1 market in 2025 (33% of system
sales, spiking to 42% in Q3 as customers front-ran new rules) and is being guided down to ~20% for 2026 by policy,
with a further bill (MATCH Act) pending that would bar DUV sales to China entirely. This is TYPE_C, not TYPE_B — the
risk to the thesis is a revenue *headwind* from shrinking China sales, not an operational dependency. **Recommend**:
add a line noting ASML's China revenue is actively being cut by policy (33%→~20% guided) as a component of near-term
revenue risk, distinct from the existing kill_condition's focus on competition/capex-cycle risk.

### us-solar-manufacturing (FSLR) — **a genuine correction to the "China-free" framing**
The thesis is built on FSLR being the anti-China, tariff-protected play, and that's correct for manufacturing
location and for avoiding the China-dominated polysilicon supply chain. But it is not fully correct that FSLR has
*zero* China dependency: its CdTe technology relies on tellurium, of which China controls ~75-76% of global
production, and China imposed export-license controls on tellurium/CdTe specifically in February 2025. FSLR's own
10-K discloses active mitigation (alternate suppliers, license applications, recycling up to 95% material recovery)
— language that itself signals the company treats this as a real, not hypothetical, exposure. **Recommend**: add a
qualifying line to the us-solar-manufacturing note — FSLR's "China-free" positioning is correct for
manufacturing/final-assembly and the polysilicon chain, but not for its core CdTe raw-material input (tellurium),
which carries its own, distinct China export-control risk that the company is actively managing.

### gas-compression-equipment (USAC) & specialty-siding-pricing-power (LPX) — **both clean, no change needed**
Both verified NONE with reasonable confidence. USAC's lead-time story (120+ weeks) is driven by Caterpillar engine
availability, not China. LPX's 20+ facilities are all North/South America. No note changes recommended.

### glp1-biologics-packaging (WST) — **a real but likely immaterial-to-thesis finding**
WST operates two confirmed manufacturing plants in Qingpu, Shanghai (injection + compression molding, since 2009/
2013, 250 employees) — this is real China manufacturing, not speculation. However, this appears to be a
regionally-self-contained plant serving the APAC pharma market rather than a single point of failure feeding WST's
global HVP/GLP-1 packaging story (which the thesis is actually about — Annex-1 regulatory-lock, not China). China
revenue % couldn't be verified. **Recommend**: add a factual note (China manufacturing exists, Shanghai/Qingpu,
~250 employees) for completeness, but flag as likely low-materiality to the thesis's actual kill_condition (which
hinges on demand-outstripping-supply language and Annex-1 upgrade counts, not on this plant specifically) unless
follow-up research shows otherwise.

---

## 4. What was NOT verified (explicit gaps, don't treat as settled)

- **LITE (Lumentum)**: conflicting sources on current China manufacturing status — one source found a China-
  registered manufacturing entity (Shenzhen/Wuhan), another (search extract of the current 10-K) named only US/
  Japan/Thailand/UK as primary manufacturing countries. This needs a direct primary-10-K read before either
  claim is relied on.
- **ON (onsemi)** and **GEV/VRT**: true China revenue % is obscured by billing-jurisdiction or regional-bucket
  disclosure in their own filings — no reliable country-specific number exists in the public record as searched.
- **CAT**: no rare-earth/critical-mineral China dependency was found despite plausible relevance (heavy machinery
  uses magnets/specialty alloys) — absence of 10-K disclosure, not a confirmed clean bill of health.
- **BE (Bloom Energy)** scandium allegation: actively contested between an investigative outlet and the company's
  own denial as of report date — treat as an open question, not a resolved finding either way.
- **CVX, COP**: "NONE" verdicts here are LOW confidence (absence of evidence in this search pass, not an
  affirmative denial) — worth a follow-up pass if either name becomes decision-relevant.
- **AEHR, WST, LNG revenue %**: none of these got a verbatim 10-K geographic-revenue confirmation in this session;
  all flagged 未證實/unverified for the specific percentage, even though qualitative exposure is reasonably
  well-evidenced.
