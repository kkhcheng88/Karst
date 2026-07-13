# 需求端反向驗證掃描 -- 2026-07-13

Fable 交接書 P2-14。thesis/constraint_scan.py 聽**賣家**(themes.yaml 追蹤 tickers 自己)講自己供給緊;呢個掃描聽**買家**(唔喺該 theme tickers 名單入面嘅下游客戶)講「買唔夠/交期長」反向驗證。買家冇動機吹噓供應商緊張,理論上係更乾淨嘅確認訊號。

**方法**:thesis/demand_side_scan.py。每個 theme 3-5 條買家視角 (product, tension) 詞組(如 memory→'DRAM cost'/'memory prices'/'HBM allocation'),用 FTS5 `NEAR(a b, 8)` 近接查詢(非硬性連續片語——已驗證 2026-07-13:完全一致片語 'transformer lead time' 喺呢個 corpus 得 0 命中,NEAR 版本(視窗 8 tokens)得 64 命中,因為真實 earnings call 講法通常有插入字"we procured long lead time components such as turbines and transformers")。掃描視窗:最近 4 個日曆季(cutoff >= 2025-10-01)、僅英文 transcript 語料(docs_fts_en)。

**買家身份檢查**:SQL 層 `primary_ticker NOT IN (<該 theme 自己嘅 themes.yaml tickers>)`——逐 theme 分開排除,只排除嗰個 theme 自己嘅供應商,唔係全局排除(例如 GLW 同時喺 photonics-optical/advanced-packaging 兩個 theme,兩邊各自排除自己嗰份)。呢個過濾喺下面每個 theme 表格前已註明採用嘅排除清單。

**兩個實測發現嘅雜訊來源,已喺 script 修正**(唔係隱藏,寫低俾覆核):(1) porter stemmer 詞根碰撞——首輪跑出嚟 'generator' 匹配到 'generally/generation'、'transformer' 匹配到 'transformation'、'siding' 匹配到極常見嘅 'side'(單一呢個碰撞就製造咗 specialty-siding-pricing-power theme 55/57 條假命中!)、'forging' 匹配到專有名詞 'Forge'(如數據中心項目名'Polaris Forge One')——已加 LITERAL_GUARDS,要求 snippet 入面literal 字面字串(唔止靠詞根)先算數,唔係就直接棄用嗰條命中。(2) corpus 有部分 transcript 俾多個 primary_ticker 標籤(OTC/ADR 雙重上市如 SONY/SNEJF、NOK/NOKBF;公用事業優先股系列如 AEE 底下~15 個關聯 ticker)——同一份 transcript 逐字重複,已加內容排重(同季度+前150字元完全相同視為同一個買家聲音,只計一次)。方法仍係 v1 啟發式,唔係 100% 乾淨(例如 'packaging'/'module' 呢類多義詞喺部分 theme 仍可能有殘餘雜訊——逐條引句已保留俾人手/LLM 覆核)。

**方向判定**(v1 啟發式,非 LLM):snippet 內見 EASE_MARKERS(要求 eased/improved/normalized/resolved/caught up 呢類字直接掛住 supply/availability/lead time/capacity/shortage/pricing 呢類供給名詞先算,唔係淨係見到隻字就算——首輪跑出嚟兩條假 `reverse`(NVMI「further IMPROVING our manufacturing PROCESS」、ONTO「backlog VISIBILITY has IMPROVED」,兩條都同「供給鬆咗」冇關,已用呢個收緊修正)→ 見到就算 `reverse`(買家話鬆咗);否則喺每個命中片語前 ~8 個 token 檢查否定詞(沿用 constraint_scan.py 嘅 NEGATIONS 清單)——全部命中都被否定先算 `negated-no-signal`,否則 `confirm`。呢個係 snippet 層面(唔係全文)嘅啟發式,同 constraint_scan.py 一樣嘅務實取捨——每條命中嘅原句都保留喺表入面,人手/LLM 可以覆核。

**未覆蓋 theme**(有記錄理由,唔係靜靜跳過):

- **space-satellite**:早週期需求/執行敘事(發射、頻譜、月球任務),唔係「買家買唔到實物」型供給樽頸——冇自然嘅下游買家投訴語言可測,強行造 probe 只會製造假訊號。

- **oil-gas-energy**:thesis 本身標記 thin-split-watch(油價 macro 腿 + gas-power watch 腿混合,非單一商品/零件供給樽頸故事),唔屬於呢個掃描方法適用嘅「單一實物瓶頸」型 thesis。


## 摘要:每 theme 買家側確認數 vs 反向數 vs 賣家側最新讀數

| theme | 賣家側最新密度(季) | 買家確認 | 買家反向(鬆咗) | 買家無訊號(被否定) | 對照結論 |
|---|---|---|---|---|---|
| memory-supercycle | 1.00 (2026Q2) | 90 | 0 | 2 | 雙重確認(最強) |
| photonics-optical | 0.88 (2026Q2) | 6 | 0 | 0 | 雙重確認(最強) |
| advanced-packaging | 0.92 (2026Q2) | 23 | 0 | 0 | 雙重確認(最強) |
| ai-power-grid | 0.71 (2026Q2) | 20 | 0 | 0 | 雙重確認(最強) |
| rare-earth-materials | 0.00 (2026Q2) | 16 | 0 | 0 | 賣家已轉鬆,買家仍確認緊張(落後訊號?) |
| gas-compression-equipment | 1.00 (2026Q2) | 2 | 0 | 0 | 雙重確認(最強) |
| tpu-custom-silicon | 1.00 (2026Q2) | 8 | 0 | 0 | 雙重確認(最強) |
| semicap-equipment | 0.00 (2026Q2) | 2 | 0 | 0 | 賣家已轉鬆,買家仍確認緊張(落後訊號?) |
| aerospace-specialty-alloys | 1.00 (2026Q2) | 2 | 0 | 0 | 雙重確認(最強) |
| euv-lithography-monopoly | 1.00 (2026Q2) | 0 | 0 | 0 | 賣家話緊,買家靜(要小心) |
| us-solar-manufacturing | 1.00 (2026Q2) | 1 | 0 | 0 | 雙重確認(最強) |
| specialty-siding-pricing-power | 1.00 (2026Q2) | 0 | 0 | 0 | 賣家話緊,買家靜(要小心) |
| glp1-biologics-packaging | 1.00 (2026Q2) | 0 | 0 | 0 | 賣家話緊,買家靜(要小心) |

### 賣家話緊、買家又話緊(最強confirmation)

- **memory-supercycle**:賣家密度 1.00、買家確認 90 條、反向 0 條
- **tpu-custom-silicon**:賣家密度 1.00、買家確認 8 條、反向 0 條
- **gas-compression-equipment**:賣家密度 1.00、買家確認 2 條、反向 0 條
- **aerospace-specialty-alloys**:賣家密度 1.00、買家確認 2 條、反向 0 條
- **us-solar-manufacturing**:賣家密度 1.00、買家確認 1 條、反向 0 條
- **advanced-packaging**:賣家密度 0.92、買家確認 23 條、反向 0 條
- **photonics-optical**:賣家密度 0.88、買家確認 6 條、反向 0 條
- **ai-power-grid**:賣家密度 0.71、買家確認 20 條、反向 0 條

### 賣家話緊、但買家靜晒(要小心——可能係單方面供應商敘事)

- **euv-lithography-monopoly**:賣家密度 1.00、買家確認 0 條、反向 0 條
- **specialty-siding-pricing-power**:賣家密度 1.00、買家確認 0 條、反向 0 條
- **glp1-biologics-packaging**:賣家密度 1.00、買家確認 0 條、反向 0 條

### 賣家籃子太薄、讀數唔穩,但買家側(全市場)反而強確認(額外發現,唔係任務原定兩類)

呢類 theme 嘅賣家側 constraint_scan.py 追蹤 tickers 得 1-2 隻(rare-earth-materials 得 MP/USAR 兩隻;semicap-equipment 得 AEHR 一隻),單一 ticker 轉態就令密度喺 0/0.5/1.0 之間跳(睇 backtest/results/2026-07-12_constraint_scan_production.md 嘅歷史列:rare-earth-materials 6 季讀數 1.00→0.00→1.00→0.50→1.00→0.00,noise 主導,唔可靠)。但買家側掃描係跨全市場(~5,370 tickers)搵,唔受單一供應商籃子太細影響——呢個先真係「反向驗證」原本要做嘅嘢:賣家讀數唔穩定嗰陣,買家側可以充當更穩健嘅獨立確認。

- **rare-earth-materials**:賣家最新密度 0.00(籃子太細唔可靠)、買家確認 **16 條**(跨多間唔同公司,見下逐 theme 明細)

## 逐 theme 命中明細

### memory-supercycle

probe 組:DRAM/cost; memory/prices; HBM/allocation; memory/pricing; NAND/pricing
排除嘅該 theme 自己 tickers(唔當買家):MU, SKHY, SNDK, WDC

| 買家 ticker | 季度 | 方向 | probe | 引句(≤2句,已截) |
|---|---|---|---|---|
| AEHR | 2025Q4 | confirm | DRAM / cost | ...This innovation is said to offer eight to 16 times the capacity of HBM [DRAM] at a similar [cost], delivering comparable bandwidth to dramatically accelerate AI inference and process larger... |
| SIMO | 2025Q4 | confirm | NAND / pricing | ...Despite the challenges inherent with the [NAND] [price] increases, we believe our business will remain robust. Our module maker customers have been building [NAND] inventory ahead of anticipated [price] increases... |
| ACLS | 2025Q4 | confirm | NAND / pricing | ...However, we are encouraged with some initial signs of improvement in the [NAND] bit demand and [pricing], and we are ready to service market once customers resume capacity additions. On... |
| MKSI | 2025Q4 | confirm | NAND / pricing | ...But then I think overlay on top of that, the industry discussion of [NAND] [pricing] that I think Melissa asked earlier, that's just a tailwind. The discussion by many... |
| CRNT | 2025Q4 | confirm | DRAM / cost | ...Any comments on supply chain as it relates to availability of parts and costs and any new concerns that we've heard other hardware vendors about, [DRAM] [costs], ratcheting up... |
| SNEJF | 2025Q4 | confirm | NAND / pricing | ...And then also -- and the [NAND] flash [price] is increasing, and then that might have the negative impact on the PS5, the hardware profitability. So what's your plan for... |
| HPQ | 2025Q4 | confirm | memory / prices | ...Guess to start, your free cash flow guide for next year is flat year on year despite the margin pressures you alluded to from increased [memory] [pricing]. What are some... |
| DELL | 2025Q4 | confirm | NAND / pricing | ...at as sort of evidence of how you're thinking about where DRAM and [NAND] [prices] could be? And I think last quarter, you exited the queue north of $5... |
| NTNX | 2025Q4 | confirm | NAND / pricing | ...renewal for the customer versus, you know, the the full hardware refresh with the [NAND] [pricing] going up as much as it is. So that I guess that's that... |
| HPE | 2025Q4 | confirm | DRAM / cost | ...We expect [DRAM] and NAND [costs] to continue to increase in 2026, the majority of which we expect to pass to the market while monitoring demand. Hybrid cloud revenue grew... |
| SNX | 2026Q1 | confirm | DRAM / cost | ...How are you handicapping any end market demand destruction from higher component [costs] like [DRAM] and NAND And one for David, can you just update us on the CapEx spend... |
| TSM | 2026Q1 | confirm | memory / prices | ...As for PC or the smartphone, to tell the truth, we expect higher [memory] [price]. So we expect the unit growth will be very minimal. But for TSMC, we did... |
| GM | 2026Q1 | confirm | DRAM / cost | ...by recent trends in aluminum, copper, and other key commodities as well as higher [DRAM] [costs] and unfavorable foreign exchange movements. Turning to our regions, we expect both China and... |
| LOGI | 2026Q1 | confirm | memory / prices | ...But as you've seen, we're really good at mitigating cost impacts through cost reductions and through targeted [pricing] if needed. So that's on [memory]. On PCs, you... |
| STX | 2026Q1 | confirm | NAND / pricing | ...Just curious, do you think there's an opportunity here for more significant [price] increases in [NAND] flash. We're hearing things like 40% to 100% up Q-on-Q... |
| MSFT | 2026Q1 | confirm | memory / prices | ...We mentioned the potential impact on Windows OEM and on-premises server markets, from increased [memory] [pricing] earlier. In addition, rising [memory] [prices] would impact capital expenditures, though the impact... |
| EXTR | 2026Q1 | confirm | memory / prices | ...In addition, we have the flexibility to further increase [prices] to offset any increases in [memory] or other components. We are confident in our ability to meet customer demand and... |
| KLAC | 2026Q1 | confirm | DRAM / cost | ...This guidance also includes the incremental impact of the rapidly escalating [cost] of [DRAM] shifts used in the company's image processing computers that ship with our systems, creating a... |
| XRX | 2026Q1 | confirm | DRAM / cost | ...What does give us pause is the recent spike in [DRAM] prices, as they began to impact [costs] across storage, servers, endpoints, and networking equipment. Having the greatest effect on... |
| AAPL | 2026Q1 | confirm | memory / prices | ...Just a lot of discussion on [memory] [pricing]. Given that the [memory] constraint or commodities scarcities both the smartphone and the PC markets, and Apple arguably having more purchasing power... |
| DLB | 2026Q1 | confirm | memory / prices | ...The reference to [memory] [pricing], in particular, obviously, that's a hot topic. I would say -- that was some -- like I said, it wasn't a significant adjustment, and we... |
| GNTX | 2026Q1 | confirm | DRAM / cost | ...back from a customer perspective, just like the tariffs in go some of these [DRAM] [cost] points are multiples of where they used to be from a pricing. So they... |
| SIMO | 2026Q1 | confirm | DRAM / cost | ...While the overall smartphone market is expected to decline this year due to higher [DRAM] and NAND component [cost], we expect the continuing shift from NAND flash maker to module... |
| QCOM | 2026Q1 | confirm | memory / prices | ...In the coming quarters, the handset industry will be constrained by the availability and [pricing] of [memory], particularly DRAM. As [memory] suppliers redirect manufacturing capacity to HBM to meet AI... |
| CDW | 2026Q1 | confirm | memory / prices | ...At the end of the quarter, our teams helped customers navigate [memory]-related [price] increases and announced future increases. Client devices showed continued growth of high single digits. Growth reflected... |
| ARM | 2026Q1 | confirm | memory / prices | ...I'll take the second part first, and then Jason will take the first part on [memory]. Question was regarding CSS [pricing] impacting bill of materials. No. We're not... |
| KLIC | 2026Q1 | confirm | DRAM / cost | ...While AI-related workloads are driving capacity tightness across the memory market, they are also driving new packaging solutions for [cost]-effective stacked [DRAM], in addition to emerging requirements for... |
| NSIT | 2026Q1 | confirm | memory / prices | ...And those [prices] will also go up significantly given the [memory] constraints and the [memory] [price] hikes. We think there's a little bit less elasticity there. And -- because, again... |
| SNEJF | 2026Q1 | confirm | memory / prices | ...So with the surging [memory] [price], so you have secured the supply until the next year-end campaign. So you maybe have secured supply, but will there be impact of... |
| ICHR | 2026Q1 | confirm | NAND / pricing | ...And then, going back on the broader industry demand, DRAM and [NAND] [prices] seem to be surging. Are you looking at this as mostly driven by capacity shifts toward AI... |
| ENTG | 2026Q1 | confirm | NAND / pricing | ...In fact, you started to see [pricing] kind of firm for [NAND] in the 2025, you saw the [pricing] continue to perform well throughout the latter half then of '25... |
| RIVN | 2026Q1 | confirm | DRAM / cost | ...And then as you look forward, clearly, you just alluded to some of the supply chain challenges around [DRAM] and other input [costs] that are embedded into your guidance. But... |
| CHKP | 2026Q1 | confirm | memory / prices | ...When I'm looking ahead into 2026, we all know the [memory] [price] increase, the recent [memory] [price] increase that we have in the market over the past few months... |
| ZBRA | 2026Q1 | confirm | memory / prices | ...We are currently facing industry-wide [price] increases for [memory] components beginning in Q2. Our full year guide reflects us fully mitigating this approximately two-point headwind and driving profitable... |
| NVMI | 2026Q1 | confirm | memory / prices | ...Is [memory] [price] creating any pressure on your gross margin? Gabriel Waisman: Not sure I fully understood the question. But overall, we don't see a correlation between [memory] [pricing]... |
| IRM | 2026Q1 | confirm | memory / prices | ...I mentioned that [memory] [pricing] in particular, and I think that is what you are specifically speaking about because that is where the industry has seen some [pricing] trends, that... |
| HIMX | 2026Q1 | confirm | memory / prices | ...Recent shocks, [price] increases in [memory] further weighed on the market sentiment for electronic products. However, compared with consumer products, the automotive segment, which accounts for over half of Himax... |
| MGA | 2026Q1 | confirm | DRAM / cost | ...And any color on what you are assuming for [DRAM] and raw material [costs]? I think your ADAS business is around $3,000,000,000. That is probably the one... |
| CEVA | 2026Q1 | confirm | memory / prices | ...While we do not have the control on the precise timing of royalty growth and continue to monitor factors such as [memory] [pricing] and broader market condition, the underlying trajectory... |
| CRNT | 2026Q1 | confirm | memory / prices | ...This effort also includes a plan to overcome the recent spike in the [price] of [memory] components in the market. All in all, we expect our non-GAAP operating margin... |
| ACLS | 2026Q1 | confirm | NAND / pricing | ...That said, recent improvements in [NAND] bit demand and [pricing] are encouraging, and we believe we are well positioned once our customers resume wafer capacity additions, which we expect is... |
| ESI | 2026Q1 | confirm | memory / prices | ...That's a real risk that [memory] [prices] will rise and correspondingly, consumer electronics [prices] will rise and that will have an impact on demand. But that's really looking... |
| ALRM | 2026Q1 | confirm | DRAM / cost | ...Related to other manufacturing [costs], we've been watching the [DRAM] market, obviously, that impacts us to some degree. We haven't really seen any cost increases come through related... |
| HLIT | 2026Q1 | confirm | memory / prices | ...With our 2026 guidance, we're taking a prudent and measured approach on both revenue and margins, considering factors such as the current [memory] chip [pricing] and supply dynamics. Built... |
| ADEA | 2026Q1 | confirm | NAND / pricing | ...If I could just quickly follow-up on a clarification on the [NAND] front. Just want to clarify in terms of [pricing]. You guys -- as I understand it, right, you... |
| HPQ | 2026Q1 | confirm | DRAM / cost | ...Like others, we are seeing increased input [costs] driven primarily by the rising prices of [DRAM] and NAND. We expect this volatility to remain throughout fiscal '26 and likely into... |
| ALLT | 2026Q1 | confirm | DRAM / cost | ...And sorry, I'm running on here, but one more question just on the [cost] side. Liat mentioned the [DRAM] shortages impacting margins, which I think is no surprise for... |
| P | 2026Q1 | confirm | NAND / pricing | ...Strong component demand, driven by tech titan AI build-outs, has outstripped supply across the industry, dramatically increasing [NAND], memory, and CPU [pricing]. We expect that the industry, including Everpure... |
| AMBA | 2026Q1 | confirm | DRAM / cost | ...And then are you seeing any impact on the overall demand environment from component [cost] inflation? Fermi Wang: You are talking about [DRAM]. First of all, there is obviously no... |
| VISN | 2026Q1 | confirm | memory / prices | ...As you are aware, supply of DDR4 [memory] has tightened, and we are experiencing availability and [pricing] impacts. Vistance Networks, Inc. already has significant seasonality and variability in our quarterly... |
| NTAP | 2026Q1 | confirm | memory / prices | ...Before I wrap up, I'd like to address how we are managing through the unprecedented inflation in [memory] [prices] currently affecting the global market. First, we have raised our... |
| NLST | 2026Q1 | confirm | memory / prices | ...Rapid growth in AI has created a supply-demand imbalance leading to a global [memory] chip shortage and sharp [price] increases across all product categories. These industry dynamics are expected... |
| GPRO | 2026Q1 | confirm | memory / prices | ...Our outlook is prefaced by highlighted uncertainty that exists due to volatility in tariff rates, [memory] [pricing], [memory] availability, consumer confidence, competition, component supply chain and global economic uncertainty. To... |
| HPE | 2026Q1 | confirm | DRAM / cost | ...The IT market is facing a sharp acceleration in supply tightness and increasing component [costs], most notably in [DRAM] and NAND. We expect elevated prices to persist well into 2027... |
| RERE | 2026Q1 | confirm | memory / prices | ...Recently, the continued rise in [memory] [prices] is directly pushing up new device [prices], and this trend is creating new opportunities for the pre-owned industry. We see this playing... |
| HRZRF | 2026Q1 | confirm | memory / prices | ...Regarding this year's [memory] [price] impact, it is true that the impact is very profound. As one of the largest intelligent and assisted driving solution shipment companies in the... |
| LRCX | 2026Q2 | confirm | HBM / allocation | ...in that area, partly as customers made choices about clean room [allocation] and obviously, some other devices like [HBM] were so hot during that period. Also going back to what... |
| MBLY | 2026Q2 | confirm | DRAM / cost | ...I think you talked about higher [DRAM] [costs] for this year. Maybe you could help quantify that. Is that something you can pass along via price adjustments? Amnon Shashua: The... |
| VC | 2026Q2 | confirm | DRAM / cost | ...the OEMs, would those essentially allow ongoing passthrough even into next year if the [DRAM] [costs] keep rising? Sachin Lawande: Yeah. Let me take that, Emmanuel. On the first topic... |
| GM | 2026Q2 | confirm | DRAM / cost | ...As a result of these changes, we are increasing our full-year guidance for year-over-year commodity inflation, including logistics and higher [DRAM] [costs], to $1.5 billion-$2... |
| CVLT | 2026Q2 | confirm | memory / prices | ...I'm going to start with the last on the macro and the [memory] [pricing]. We kind of look at them as a combined. We're managing that in our... |
| FFIV | 2026Q2 | confirm | memory / prices | ...We've also been closely monitoring what's been going on with [memory] and SSD [pricing], which has just been accelerating through the year and really kind of had a... |
| SIMO | 2026Q2 | confirm | DRAM / cost | ...a significant component hurdle for our customer at a time when [DRAM] availability is constrained and the [costs] are elevated. Wallace Kou: We have our NAND flash maker customer for... |
| KLAC | 2026Q2 | confirm | DRAM / cost | ...As discussed last quarter, the guidance also includes the persistent impact of elevated [DRAM] chip [costs] for the company's image processing computers that ship with our systems, creating a... |
| AVT | 2026Q2 | confirm | memory / prices | ...During the March quarter, we have seen price increases across a few suppliers and technologies, most predominantly related to [memory]. We expect to see additional [price] increases over the next... |
| DBD | 2026Q2 | confirm | DRAM / cost | ...We also saw some impact from higher [DRAM] and memory [costs], but are taking appropriate pricing actions and adjusting our quoting cadence. This does not change our confidence in our... |
| ROKU | 2026Q2 | confirm | memory / prices | ...Just overall, like, no one knows what will happen to [memory] [prices] beyond this year. We really don't know how the market will react to higher [memory] [prices]. Dan... |
| DLB | 2026Q2 | confirm | memory / prices | ...Of course, we're watching that very closely, as we are all the macro factors, [memory] [pricing], volatility in oil [prices] and how that might affect supply chain, consumer sentiment... |
| XRXDW | 2026Q2 | confirm | memory / prices | ...Memory lead times have extended, and in certain cases, higher [memory] [prices] have compressed margins as we prioritize establishing new relationships and expanding wallet share. We are also investing in... |
| ONTO | 2026Q2 | confirm | DRAM / cost | ...You know, you talked about, you know, some of the headwinds like [DRAM] [cost]. You know, there's also some components up like maybe specifically, are there any supply chain... |
| AMD | 2026Q2 | confirm | memory / prices | ...In that market, it's more impacted by, you know, some of the [memory] [pricing] and the component [price] increases. Lisa Su: You know, when we look at the full... |
| AOSL | 2026Q2 | confirm | memory / prices | ...As is broadly reported, [memory] supply constraints and [price] pressures represent growing headwinds for the second half of calendar 2026. Stephen Chang: Against this backdrop, we're using three primary... |
| DGII | 2026Q2 | confirm | memory / prices | ...Inside of there is the impact of the current [pricing] related to [memory]. That [pricing] is being somewhat offset by other positive pricing impacts that we're seeing elsewhere inside... |
| CDW | 2026Q2 | confirm | memory / prices | ...Customers also navigated [memory] supply and [pricing] constraints, which reshaped budget priorities in this quarter. Teams responded quickly by leveraging our partner relationships, full stack capabilities, and balance sheet strength... |
| KLIC | 2026Q2 | confirm | DRAM / cost | ...We also announced the ProMEM suite of memory features and highlighted our growing portfolio of [DRAM] solutions, supporting both [cost]-sensitive and high-bandwidth memory applications. Additionally, we have a... |
| ARLO | 2026Q2 | confirm | DRAM / cost | ...quarter, memory is a pretty small percentage of your guys' BOM [cost]. You use kind of lower-level [DRAM], maybe not as much of the constrained stuff in your products... |
| CRSR | 2026Q2 | confirm | memory / prices | ...We are in a non-GPU upgrade cycle, compounded by challenging [memory] [pricing] dynamics. Semiconductor supply constraints have added further headwinds on both availability and consumer demand. These are industry... |
| HIMX | 2026Q2 | confirm | memory / prices | ...In our display IC business for automotive, we remain confident in our long-term growth prospects, as automotive is an area relatively insulated from [memory] [price] impact compared to consumer... |
| RDWR | 2026Q2 | confirm | memory / prices | ...While this had a modest impact on gross margin, we are actively managing these dynamics through [pricing] and procurement. Looking ahead, we expect [memory]-related cost pressure to persist in... |
| AMVIF | 2026Q2 | confirm | memory / prices | ...Phasing of headwinds from raw materials in Q1, obviously there has been some headwind mainly on the raw material and [memory] [price] to a lower extent. Jutta Dönges: As we... |
| SNEJF | 2026Q2 | confirm | memory / prices | ...The [memory] [prices], looking at the current circumstances, the [memory] [prices], is expected to be very high, also in FY 2027, because there will still be a shortage in supply... |
| CEVA | 2026Q2 | confirm | memory / prices | ...You mentioned [memory] [pricing] and, you know, overall, you know, sort of macro, you know, sort of dynamics going on. Ruben Roy: Either Amir or Yaniv, can you maybe just... |
| PRSO | 2026Q2 | confirm | memory / prices | ...Although a combination of current market dynamics, including the shortage and related increase of [pricing] of [memory] chips, are contributing to subdued near-term demand and purchase order activity from... |
| ZBRA | 2026Q2 | confirm | memory / prices | ...What are your [memory] [price] assumptions baked into the rest of the year in terms of the [memory] [price] spiking? Bill Burns: Andrew, maybe I'll start and then hand... |
| UCL | 2026Q2 | confirm | memory / prices | ...This result come despite significant external headwinds, including macroeconomic volatility, weak travel demand, rising energy [prices], [memory] chipset cost increase, and the conflict-related supply chain disruption. More importantly, our... |
| P | 2026Q2 | confirm | NAND / pricing | ...[Pricing] in both memory as well as [NAND] is up just an incredible amount. The demand is so high, it's still able to be sold at that level as... |
| PLAB | 2026Q2 | confirm | memory / prices | ...The recent surge in [memory] [prices] and related supply constraints have contributed to delays in the launch of several new consumer electronic products as OEMs have worked to secure memory... |
| NTAP | 2026Q2 | confirm | NAND / pricing | ...Do you think this is simply just wanting to find other ways to deal with higher [NAND] [pricing], or is this more durable than just a pricing or payment mechanism... |
| HPE | 2026Q2 | confirm | DRAM / cost | ...Sequentially, revenue grew 15%, reflecting higher average selling prices within our server business, driven by ongoing [DRAM] and NAND inflationary [costs] and supply constraints. We continue to work with our... |
| PENG | 2026Q3 | confirm | memory / prices | ...These factors were partially offset by AI-driven demand, which supported favorable [pricing] in our Integrated [Memory] business during the quarter. Non-GAAP operating expenses for the third quarter were... |
| QRVO | 2026Q1 | negated-no-signal | memory / prices | ...Qorvo enjoys broad participation across smartphone OEMs and we are not seeing signs of [memory] [pricing], or [memory] availability impacting the flagship and premium tiers. Our largest customer is expected... |
| DELL | 2026Q1 | negated-no-signal | memory / prices | ...Clearly, given the demand backdrop, it seems like you are not really seeing any, you know, [memory] [price] impacts on that business. But I am curious, as the business scales... |

### photonics-optical

probe 組:optics/lead time; transceiver/shortage; optical component/shortage; laser/lead time; transceiver/lead time
排除嘅該 theme 自己 tickers(唔當買家):AAOI, AXTI, COHR, FN, GLW, LITE, LWLG, MRVL, SIVE

| 買家 ticker | 季度 | 方向 | probe | 引句(≤2句,已截) |
|---|---|---|---|---|
| SITM | 2025Q4 | confirm | optical component / shortage | ...We do hear rumors of some of the [optical] [components] that are in [shortage]. But I don't think that anybody is holding back because we see quite a significant... |
| KLAC | 2026Q1 | confirm | optics / lead time | ...Well, Joe, the biggest long [lead] [time] aspect of our build of materials and [optical] components. So to my earlier point about the lead time for that tends to be... |
| NVMI | 2026Q1 | confirm | optics / lead time | ...And is the [optical] component a driver of that [lead] [time] pressure? Gabriel Waisman: No. I think that the lead time pressure is coming from the customers that they have... |
| ONTO | 2026Q1 | confirm | optics / lead time | ...on some of our suppliers, especially in the area of precision [optics] and things like this, where [lead] [times] are relatively fixed. So we're working very closely with our... |
| CCOI | 2026Q1 | confirm | optics / lead time | ...I think the other thing that is a constraint today is actually pluggable [optics] [lead] [times] have become more challenging just because of, yeah, the pressures that some of the... |
| NOKBF | 2026Q2 | confirm | optics / lead time | ...I guess, so you mentioned that the [lead] [times] in [optical], and I think IP are 12-18 months currently, but you also significantly increased your growth assumptions for this... |

### advanced-packaging

probe 組:advanced packaging/capacity; substrate/shortage; advanced packaging/allocation; chip packaging/lead time; CoWoS/capacity
排除嘅該 theme 自己 tickers(唔當買家):AMKR, ASX, FORM, GLW, INTC, KLAC, KLIC, LRCX, MKSI, STX, TER, TTMI, WDC

| 買家 ticker | 季度 | 方向 | probe | 引句(≤2句,已截) |
|---|---|---|---|---|
| TSM | 2025Q4 | confirm | advanced packaging / capacity | ...She wants to understand also on the CoWoS [capacity] and specifically, I guess, [advanced] [packaging] in Arizona and how do we work with our OSAT partners. C.C. Wei: Okay... |
| SIMO | 2025Q4 | confirm | substrate / shortage | ...May we know the reason behind? Is it due to the inventory preparation for the BT [substrate] [shortage]? And I have a follow-up. Jason Tsai: Yes. So inventory did... |
| NVMI | 2025Q4 | confirm | advanced packaging / capacity | ...This advanced clean room, which extends our existing site, enables us to triple our production [capacity] for [advanced] [packaging] optical metrology solutions while further improving our manufacturing process and quality... |
| SITM | 2025Q4 | confirm | substrate / shortage | ...We've also, of course, heard of [substrate] [shortages], but I think that's sort of fairly common knowledge. Nothing that's very particular to timing. Quinn Bolton: And then... |
| INDI | 2025Q4 | confirm | substrate / shortage | ...Specifically, there are [shortages] in the supply of packaged [substrates], which will impact our ability to deliver the full demand for Q4. In spite of that, we expect to continue... |
| TSM | 2026Q1 | confirm | advanced packaging / capacity | ...He knows a local news has been reporting that TSMC is exiting 8-inch and 12-inch businesses and converting the [capacity] to [advanced] [packaging]. So he wants to know... |
| UMC | 2026Q1 | confirm | advanced packaging / capacity | ...So my first question will be besides the Interposer, what else we might have, some engagement for [advanced] [packaging]? And for Interposer, what's the [capacity] expansion plan for 2026... |
| NVMI | 2026Q1 | confirm | advanced packaging / capacity | ...On DRAM and high-bandwidth memory, we see a healthy recovery in DRAM and continued build-out of HBM [capacity]. In [advanced] [packaging], we see growing contribution from hybrid bonding... |
| ONTO | 2026Q1 | confirm | advanced packaging / capacity | ...As evidenced by our backlog doubling over the last 3 months, visibility for 2026 has dramatically improved as customers plan for sustained investments in [advanced] nodes and [advanced] [packaging] [capacity]... |
| INDI | 2026Q1 | confirm | substrate / shortage | ...Recall on our previous call, we highlighted the [shortage] of package [substrates] prevalent in the industry caused by ever-increasing demand for AI chips. We are pleased to report we... |
| ADEA | 2026Q1 | confirm | advanced packaging / capacity | ...Micron, Samsung, and SK hynix are all making significant multibillion dollar investments in [advanced] [packaging] [capacity] that support their hybrid bonding strategies for HBM and NAND. Semiconductor equipment toolmakers involved... |
| VECO | 2026Q1 | confirm | advanced packaging / capacity | ...We are seeing accelerating demand for our LSA tools at advanced nodes, along with growth in wet processing applications for [advanced] [packaging] as customers scale [capacity] driven by AI and... |
| Q | 2026Q1 | confirm | advanced packaging / capacity | ...Obviously, a lot of our customers and folks throughout the industry are making significant investments to expand the [capacity] for both [advanced] [packaging] as well as kind of the place... |
| TSMWF | 2026Q2 | confirm | advanced packaging / capacity | ...How do we work with the customers to plan the [advanced] [packaging] [capacity]? Is what she would like to understand, and also in the context of working with our OSAT... |
| ADTTF | 2026Q2 | confirm | CoWoS / capacity | ...Yeah, I would just add one other simple comment, which is, um, unit volume is gonna continue to grow, you know, as wafer starts and things like [CoWoS] [capacity], new... |
| UMC | 2026Q2 | confirm | advanced packaging / capacity | ...your advanced packaging, right? Can management talk about your future plan for those [advanced] [packaging] [capacity] expansion and also potential revenue contribution in the coming two years? Chitung Liu: These... |
| VECO | 2026Q2 | confirm | advanced packaging / capacity | ...William did, you know, sort of mention earlier in prepared remarks that we are increasing, you know, our [capacity] for [advanced] [packaging]. We see opportunities, you know, for that to... |
| LITE | 2026Q2 | confirm | substrate / shortage | ...Some of these, for example, [substrate] [shortages] that's been reported out, you know, I think you know our story better than most, and that is that we've executed... |
| CAMT | 2026Q2 | confirm | advanced packaging / capacity | ...We see a compelling opportunity in the OSAT domain, which is currently undergoing a significant wave of investment in [advanced] [packaging], particularly for AI-related [capacity] expansion. As the leading... |
| Q | 2026Q2 | confirm | advanced packaging / capacity | ...We're investing in line with our customers to meet their capacity as they put more [capacity] in the ground, especially for things like [advanced] [packaging], and they continue to... |
| ALMU | 2026Q2 | confirm | substrate / shortage | ...Last, there is a major [shortage] of indium phosphide [substrates] of all sizes. Suppliers are sold out for years with only limited increase in capacity expected in the near term... |
| DINRF | 2026Q2 | confirm | advanced packaging / allocation | ...The surplus production capacity of FT will have to be [allocated] to the [advanced] [package] business so that we can support the growth of the sales of advanced package, which... |
| NVMI | 2026Q2 | confirm | advanced packaging / capacity | ...This is accelerating [capacity] expansion across logic, memory, and [advanced] [packaging], while also introducing greater manufacturing complexity and yield challenges, driving higher process control and metrology intensity. These dynamics reinforce... |

### ai-power-grid

probe 組:transformer/lead time; turbine/backlog; switchgear/lead time; power equipment/shortage; generator/lead time
排除嘅該 theme 自己 tickers(唔當買家):BE, CAT, ETN, GEV, GNRC, MPWR, NVTS, ON, PWR, SPXC, TXN, VICR, VRT, WOLF

| 買家 ticker | 季度 | 方向 | probe | 引句(≤2句,已截) |
|---|---|---|---|---|
| APLD | 2025Q4 | confirm | transformer / lead time | ...So what are you seeing in the supply chain for long lead equipment, such as the [transformers], generators, and have [lead] [times] or pricing shifted materially in the past six... |
| CECO | 2025Q4 | confirm | turbine / backlog | ...And if you dig into the large OEM, gas [turbine] OEM [backlog] information, you'll see that they are also suggesting that the international demand is every bit as exciting... |
| CIFR | 2025Q4 | confirm | transformer / lead time | ...In the third quarter, we continued development of the substation for the site and secured long [lead] [time] items, including [transformers] and high-voltage breakers. The site is on track... |
| AEE | 2025Q4 | confirm | transformer / lead time | ...We have procured long [lead] [time] components such as turbines and [transformers] for our planned energy centers with expected in-service dates through 2029. And we have secured production slots... |
| AA | 2026Q1 | confirm | transformer / lead time | ...And depending on the availability of key [lead] [time] on key production items, for instance, [transformers] and things like that, it could take up to a couple of years to... |
| POWL | 2026Q1 | confirm | switchgear / lead time | ...And then just as a follow-up, how should we think about the [lead] [times] on specific components like [switchgear], for example, obviously, you have a significant backlog at this... |
| NI | 2026Q1 | confirm | transformer / lead time | ...to do, we are facilitating that pipeline through investment in long [lead] [time] equipment, turbine reservations, breakers, [transformers], etcetera. To help make sure that we can meet counterparty demand in... |
| SMEGF | 2026Q1 | confirm | turbine / backlog | ...The 83 units that you've had on the industrial [turbines] and the color around the order [backlog] exposure to hyperscalers. I wondered if you could just talk a little... |
| AEE | 2026Q1 | confirm | transformer / lead time | ...We have procured long [lead] [time] components such as turbines and [transformers] for our planned near term energy centers and we have executed gas supply contracts and awarded labor contracts... |
| EQT | 2026Q1 | confirm | turbine / backlog | ...Together, [turbine] [backlogs] and data center construction activity reinforce the structural demand growth that is building across the power sector. Given the location of this load and the depth of... |
| BLHWF | 2026Q1 | confirm | transformer / lead time | ...Of course, the energy but also the supply chain overall, there are some components from some manufacturers that have [lead] [times] until 2030, [transformers] and things like this. And so... |
| BLMOY | 2026Q1 | confirm | transformer / lead time | ...There are some components from some manufacturers that have [lead] [times] until 2030, [transformers] and things like this. That will be, we'll find out what can be really then... |
| PEG | 2026Q1 | confirm | turbine / backlog | ...RFP? And how do we, like, work through things like air permits and [turbine] queue [backlogs]? I guess, how do you think about this whole process around this for some... |
| RIOT | 2026Q1 | confirm | transformer / lead time | ...As industry analysts have noted, [transformer] and switchgear [lead] [times] have quietly become one of the defining constraints in modern data center development. These are the hidden bottlenecks shaping 2026... |
| FPS | 2026Q1 | confirm | transformer / lead time | ...We're only beginning to fully leverage two key advantages, our expanding manufacturing depth and our strength in longer [lead] [time] products like medium voltage switchgear and [transformers]. As our... |
| SEI | 2026Q2 | confirm | turbine / backlog | ...of what I'll call speculators in the queue of [turbine] [backlogs] that thought they could just kinda buy [turbines] and be a mini SEI. They're now realizing that... |
| WCC | 2026Q2 | confirm | switchgear / lead time | ...With switchgear components stretching well over one year and medium voltage [switchgear] sometimes staying 40, 60 week [lead] [times], you're clearly navigating any shortages in the market out there... |
| AEP | 2026Q2 | confirm | transformer / lead time | ...This includes already securing extra high voltage, long [lead] [time] equipment like [transformers], breakers, and lattice steel. As we also said on past calls, we have secured more than 10... |
| SMEGF | 2026Q2 | confirm | turbine / backlog | ...date? Whether or not you're also seeing continuing momentum in that [backlog] margin for the [turbine] business. You've also been clear that you expect a slowing order intake... |
| WYFI | 2026Q2 | confirm | generator / lead time | ...You know, stuff that's site agnostic, [generators], UPSs, stuff that does have longer [lead] [time]. Pre-planning and having all that prepared to integrate into our project timelines is... |

### rare-earth-materials

probe 組:rare earth/shortage; magnet/supply; gallium/shortage; indium/shortage; rare earth/allocation
排除嘅該 theme 自己 tickers(唔當買家):MP, USAR

| 買家 ticker | 季度 | 方向 | probe | 引句(≤2句,已截) |
|---|---|---|---|---|
| GM | 2025Q4 | confirm | rare earth / shortage | ...chain resiliency after we lived through COVID and the semiconductor [shortage]. And so from a battery raw materials, [rare] [earths], Paul has led the activity to really work to source... |
| RRX | 2025Q4 | confirm | magnet / supply | ...With all of this said, the majority of our guidance changes due to margin headwinds caused by newly introduced and increased tariffs, along with additional rare earth [magnet] [supply] chain... |
| ALGM | 2025Q4 | confirm | magnet / supply | ...It's more related to the conversations we're having with our customers about the transition over to [magnetic] current sensors in the power [supplies] being a general trend and... |
| LCID | 2025Q4 | confirm | magnet / supply | ...Over the last 6 months, we have contended with 3 consecutive industry-wide [supply] chain crisis, [magnets], aluminum and chips. These are crisis that set even far bigger competitors on... |
| SVYSF | 2025Q4 | confirm | magnet / supply | ...Additionally, and beyond permanent [magnet], we're considering also [supplying] other essential rare earths like gadolinium or yttrium, which are critical for aeronautics, medical and other high-end applications. To... |
| HYLN | 2025Q4 | confirm | magnet / supply | ...That said, the broader [supply] environment for these [magnets] remains uncertain, and we're continuing to monitor it closely to mitigate any potential impact on our production schedule. To wrap... |
| CNR | 2026Q1 | confirm | rare earth / allocation | ...Fourth, we will continue to advance our efforts in the growth areas of [rare] [earth] and critical materials with a prudent capital [allocation] strategy. Last but not least, our employees... |
| HYLN | 2026Q1 | confirm | magnet / supply | ...On our last earnings call, we discussed the potential risk related to [magnet] [supply], particularly given the export constraints from China. We are pleased to share that we have made... |
| ALNT | 2026Q1 | confirm | magnet / supply | ...On the main issue for you on the [supply] chain side is rare earth around [magnets]. Everyone has that problem. I have to believe that your government is well aware... |
| CODI | 2026Q2 | confirm | magnet / supply | ...Demand for geopolitically secure rare earth [magnet] [supply] continues to build as customers increasingly prioritize reliable, non-China sources. Arnold's Thailand facility is ramping up, adding capacity and supply... |
| RRX | 2026Q2 | confirm | magnet / supply | ...You know, I think this is the, you know, maybe four quarters now that we've had rare earth [magnet] [supply] issues. That certainly has weighed on margins within the... |
| AAOI | 2026Q2 | confirm | indium / shortage | ...Taran, we see a [shortage] of [indium] phosphide laser manufacturing capacity across the industry right now, and we think that's gonna persist and even get more acute with the... |
| FEAM | 2026Q2 | confirm | magnet / supply | ...Global [magnet] [supply] chains remain highly concentrated. Recent export controls and geopolitical friction are forcing customers to focus on resilient U.S. domestic [magnet] [supply] chains as an alternative to... |
| HYLN | 2026Q2 | confirm | magnet / supply | ...On [supply] chain, we noted last quarter that [magnet] [supply] was a potential risk given export constraints from China. I'm pleased to share that during the 1st quarter, we... |
| ALMU | 2026Q2 | confirm | indium / shortage | ...Last, there is a major [shortage] of [indium] phosphide substrates of all sizes. Suppliers are sold out for years with only limited increase in capacity expected in the near term... |
| IQEPF | 2026Q2 | confirm | indium / shortage | ...There have been reports of [indium] phosphide [shortages]. Are you seeing this, and could this impact the company in the second half of the year? Jutta Meier: Indium phosphide is... |

### gas-compression-equipment

probe 組:compressor/lead time; compression equipment/shortage; compressor/backlog; compression equipment/capacity
排除嘅該 theme 自己 tickers(唔當買家):USAC

| 買家 ticker | 季度 | 方向 | probe | 引句(≤2句,已截) |
|---|---|---|---|---|
| EFXT | 2025Q4 | confirm | compressor / lead time | ...And [lead] [times] for the engines and [compressors], where we think we're at there. Jeffrey Fetterly: Tim, it's Jeff. It's obviously been fairly widely publicized the increases... |
| CF | 2025Q4 | confirm | compressor / lead time | ...The products that we -- or the equipment that we ordered as long [lead] [time] is like your boilers, your [compressors], different equipment like that. The modular equipment, which is going... |

### tpu-custom-silicon

probe 組:ASIC/capacity; custom silicon/lead time; TPU/allocation; foundry capacity/constrained
排除嘅該 theme 自己 tickers(唔當買家):AVGO, CLS, TSM

| 買家 ticker | 季度 | 方向 | probe | 引句(≤2句,已截) |
|---|---|---|---|---|
| CDNS | 2025Q4 | confirm | ASIC / capacity | ...At TSMC's OIP conference, Broadcom highlighted Integrity 3D-IC full flow deployment success for hyperscaler high-[capacity] [ASICs]. Our IP business maintained strong momentum in Q3, driven by global... |
| HUT | 2025Q4 | confirm | ASIC / capacity | ...Revenue generation commenced under an ASIC colocation agreement with BITMAIN, supporting nearly 15 exahash of [capacity] delivered by the next-generation [ASIC] machines we co-developed with the manufacturer. In... |
| ASTS | 2025Q4 | confirm | ASIC / capacity | ...Kevin from Vancouver asked, what is the difference in processing [capacity] between Block 2 FPGA satellites and Block 2 [ASICs]? Abel Avellan: Hi, Kevin. That's a great question. Listen... |
| AEHR | 2026Q1 | confirm | ASIC / capacity | ...In addition, in the last month, we received a very large forecast from our lead Sonoma production customer for AI [ASIC] production [capacity]. This forecast is expected to drive very... |
| KLAC | 2026Q1 | confirm | foundry capacity / constrained | ...ship tools to? And, any areas where potentially you could be [constrained], and would need more [capacity] once, [foundry] and logic takes off, more in in, calendar year '27. Richard... |
| ABTC | 2026Q1 | confirm | ASIC / capacity | ...We have access to additional [capacity] and to next-generation [ASICs] technology. We will deploy when we believe the investment returns more Bitcoin over its useful life than it costs... |
| IBIDF | 2026Q2 | confirm | ASIC / capacity | ...Is it right to say that you will be able to do more than that? Your [capacity] is limited, which means that [ASIC], GPU, perhaps within Ibiden, you're fighting... |
| LMFA | 2026Q2 | confirm | ASIC / capacity | ...Leading semiconductor foundries are allocating an increased share of advanced manufacturing [capacity] to AI chip production, extending [ASIC] lead times and compressing efficiency improvements across the Bitcoin supply chain. The... |

### semicap-equipment

probe 組:burn-in/capacity; test capacity/constrained; package test/capacity
排除嘅該 theme 自己 tickers(唔當買家):AEHR

| 買家 ticker | 季度 | 方向 | probe | 引句(≤2句,已截) |
|---|---|---|---|---|
| AMKR | 2026Q1 | confirm | package test / capacity | ...About 30% to 35% is projected for HDFO [test] and other advanced [packaging] [capacity]. The remaining spend is projected for R&D and quality programs. In closing, our fourth quarter... |
| AMKR | 2026Q2 | confirm | package test / capacity | ...About 30% to 35% is projected for HDFO, [test] and other advanced [packaging] [capacity]. The remaining spend is projected for R&D and quality programs. We anticipate elevated CapEx spend... |

### aerospace-specialty-alloys

probe 組:titanium/shortage; nickel alloy/shortage; specialty alloy/lead time; forging/capacity; alloy/allocation
排除嘅該 theme 自己 tickers(唔當買家):ATI, CRS

| 買家 ticker | 季度 | 方向 | probe | 引句(≤2句,已截) |
|---|---|---|---|---|
| KRMN | 2025Q4 | confirm | forging / capacity | ...One example is the investment we are making in our Albany, Oregon facility that will double our [forging] [capacity] for specialty payload production. These investments increase throughput, enhance quality and... |
| RTX | 2026Q1 | confirm | forging / capacity | ...And Pratt will continue to invest in [capacity] across multiple sites including Columbus, Georgia to increase [forging] production and Asheville to establish a foundry to produce turbine airflow castings. We... |

### euv-lithography-monopoly

probe 組:EUV/lead time; lithography tool/allocation; EUV tool/backlog; lithography/capacity constrained
排除嘅該 theme 自己 tickers(唔當買家):ASML

_無命中(全部 probe 喺呢個視窗 0 hits,或全部命中都嚟自被排除嘅自己 tickers)。_

### us-solar-manufacturing

probe 組:solar module/shortage; panel/allocation; solar module/lead time; solar module/supply
排除嘅該 theme 自己 tickers(唔當買家):FSLR

| 買家 ticker | 季度 | 方向 | probe | 引句(≤2句,已截) |
|---|---|---|---|---|
| TE | 2025Q4 | confirm | solar module / supply | ...Our top operational priority for the next year is to source a meaningful [supply] of non-FEOC [solar] cells to feed [module] production at G1 prior to the expected start... |

### specialty-siding-pricing-power

probe 組:siding/allocation; siding/lead time; siding/cost increase
排除嘅該 theme 自己 tickers(唔當買家):LPX

_無命中(全部 probe 喺呢個視窗 0 hits,或全部命中都嚟自被排除嘅自己 tickers)。_

### glp1-biologics-packaging

probe 組:vial/shortage; stopper/shortage; elastomer/shortage
排除嘅該 theme 自己 tickers(唔當買家):WST

_無命中(全部 probe 喺呢個視窗 0 hits,或全部命中都嚟自被排除嘅自己 tickers)。_

