# Per-node magnifier 評估 — Batch 2(memory-supercycle + space-satellite)【草稿,待大腦逐 node 覆核】

**Date:** 2026-07-13
**任務:** Fable 交接書 P2-12 推廣次序第 3、4 個 theme(memory-supercycle、space-satellite),各起 `nodes:` 塊
(per-node magnifier tier),照 ai-power-grid / photonics-optical / advanced-packaging 現有 nodes schema。
**方法:** magnifier 五特徵框架(`docs/2026-07-09_magnifier_model_plan.md` §1 + `docs/2026-07-12_
magnifier_scorecard_rubric.md` §1),校準錨 = MU 2023 / MU 2016-18(**呢兩個錨正正就係 memory theme 自己嘅
歷史,用到盡**)+ FSLR-vs-STP。**唔係估值篩**——tier 反映「呢個 node 被供需超級週期非線性放大嘅潛在倍數
檔 + 性質(durable / binary)」。**打分維持人手/agent 質性判斷**(rubric §11 拍板,唔起自動 scoring script)。
confidence 逐 node 故意 OMIT。

## Tier 語意(照 ai-power-grid 五個現有 node + batch-1 校準)
- `2x` = 成熟/已 priced/大型稀釋,倍數有限(對應 ai-power-grid ipp-utilities / batch-1 GLW)
- `2-3x` = late/priced-ahead 但有真護城河(對應 grid-hardware / power-semis-mature / batch-1 osat/laser-idm)
- `3-5x-durable` = mid-cycle 但耐久(供給結構性慢,對應 uranium-fuel)——**本 batch 兩 theme 都冇乾淨可交易嘅呢一檔**(理由見下)
- `5-10x-binary` = 高 magnitude 但 binary(pre-profit / event / turnaround;對應 pre-earnings-optionality /
  batch-1 inp-substrate / cpo-speculative;WOLF 已 ex-post 破產驗證「binary」標籤真)

## 跨兩 theme 的結構發現(重要,已寫入 themes.yaml node comment)

**呢兩個 theme 同 batch-1 兩個(photonics/advanced-packaging)嘅「冇乾淨 3-5x-durable」原因唔同,要分開講:**

- **memory-supercycle = 全條鏈一致 LATE,冇 tier dispersion。** ai-power-grid 跨 early(pre-earnings 5-10x-binary)
  →late(grid-hardware 2-3x)→mid(uranium 3-5x-durable),有闊 dispersion,因為佢價值鏈各節點週期位置差一個
  數量級。memory **唔係**——四個可交易 node(MU/SNDK/WDC/SKHY)全部處於同一個晚週期位置(capex 頂訊號、
  peak-earnings、破紀錄 IPO 擁擠),所以四個 node 一律 `2-3x`,**冇 dispersion 唔係打分偷懶,係主題本質:
  記憶體而家成條鏈都喺「頂」,唔似電力鏈有真.早腿(SMR/pre-earnings)可以俾高檔。** 3-5x-durable 缺席,
  因為 durable 檔要「mid-cycle + 供給結構性慢」,但 memory 而家 capex/D&A 2.803x = 供給正在**加速回應**
  (durable 嘅反面)。
- **space-satellite = 主題早,但可乾淨買嘅表達幾乎全部 pre-profit 執行賭注或站頂鏟子。** 冇 3-5x-durable,
  因為唯一耐久深護城河(SpaceX/Starlink)**不可乾淨買**(同 batch-1 InP/T-glass 咽喉本體非美股同構——真咽喉
  買唔到);可交易嘅係 binary 執行賭注(RKLB/ASTS/小型 operators)或太空非主業嘅稀釋防守腿(HEI/LOAR)。

## ★ binary 檔紀律(任務明示,最重要嘅打分約束)
任務明確:「唔係全部 pre-profit 都自動 5-10x-binary,要按樽頸位置/護城河分」。space 10 隻大部分 pre-profit,
但本 batch **刻意用三層分開**,唔一律 binary:
- **(a) justified event-binary**(有真位置/護城河 + 定日催化):RKLB(發射#2 位置 + $2.2B backlog + Neutron
  定日首飛)、ASTS(FCC 授權 + 頻譜 + 98.9Mbps 實測 = 真監管咽喉)。呢兩隻 `5-10x-binary` 係「真位置 + binary
  催化」,同 batch-1 inp-substrate(AXTI 真咽喉 + China/CPO binary)同構——**唔係彩票,係有 anchor 嘅 option。**
- **(b) 純彩票 binary**(無護城河、pre-revenue):RDW/LUNR/PL/BKSY 合成一個 `preprofit-smallcap-lottery` node,
  `5-10x-binary` 但明標「magnitude 本質不可量(option/彩票端,MAX effect 平均輸)」——空間版 batch-1
  cpo-speculative(SIVE/LWLG)。
- **(c) 拉出 binary 檔**:HEI/LOAR(profitable、真護城河、但太空非主業)= `2x`;KTOS(有營收、政策期權、但
  薄利潤率+無咽喉)= `2-3x`;GSAT(併購套利、上檔封頂)= `2x`。**懶惰打法會把呢四隻都丟落 binary(因為
  「太空/投機」),本 batch 明確唔咁做——呢個就係任務要嘅紀律。**

---

# THEME 1 — memory-supercycle(4 nodes;theme-level: late / confidence 0.38 / real-but-late-cushioned)

價值鏈分層依 `thesis/wiki/memory-supercycle.md` mermaid(HBM★瓶頸 / DRAM / NAND-CMX 三支柱 → 三寡頭供給 →
LTA 去週期化 → MU[美]/SK Hynix[非美]/Samsung[非美];NAND → SNDK[美]/WDC[美])。theme 4 隻 ticker 全部覆蓋,
無遺漏(MU/SNDK/WDC/SKHY)。

## ★ 校準錨(用到盡:MU 自己兩個歷史週期 = memory theme 自身歷史)
`docs/2026-07-12_magnifier_scorecard_rubric.md` §3/§7 + `results/2026-07-09_memory_supply_demand.md` +
`results/2026-07-12_capex_da_supply_response_probe.md`:

| 時點 | MU 狀態(ex-ante) | 五特徵讀法 | tier(若當時打) |
|---|---|---|---|
| **MU 2023 谷底**(FQ4 2023,2023-08 財報) | 毛利率 **−10.8%**、蝕 $1.43B、「死週期股」情緒、capex/D&A **年度 0.990x**(資本紀律谷底,capex 低過折舊) | F1 高 / F3 **遠底(好)** / F4 高 / F5 中低(好)= 4-5/5 favourable | **5-10x-binary→durable**(真.trough magnifier)|
| **MU 2016 谷底**(FY16) | 收入退 24%、營業利潤率 1.4%、股價由 2014 高位 −70% 至 <$10 | 5/5 favourable(供給確認來自 TrendForce 第三方,唔使等管理層) | **5-10x**(其後兌現 6.5x 2016→2018)|
| **MU 今日**(2026,本 batch 打分時點) | capex/D&A **TTM 2.803x / 單季 3.310x = 供給回應頂**、ttm_pe 26(67%,peak-earnings 偽裝)、SKHY 破紀錄 $294 億 IPO 擁擠 | F1 高(不變)/ F3 **近頂(差,反轉讀)** / F4 高(不變)/ F5 已擁擠 = magnitude 被晚期封 | **2-3x** |

**核心教材(直接寫俾大腦)**:**同一隻 MU、同一套五特徵框架,喺 2023/2016 谷底會打 5-10x,喺今日 2026 頂
只值 2-3x。** 差別純粹係 F3(距底部)——2023 遠底(好)vs 今日近頂(差)。案例庫已兌現嘅 realized 倍數
(MU **23.1x**、SNDK **78.8x**[本庫單一最極端]、WDC **26.78x**,全部 2022-12 trough→2026-06 top)**正正係
「由谷底計」嘅放大,證明框架 work、放大係真**;但**今日入場 = 由頂計,唔會再有嗰 23-78x,只有晚週期
2-3x 或 downside。** LTA/RPO(MU $100B、SNDK $41.6B、照付不議)墊高**下跌地板**(減 downside),但**唔加
upside magnitude**——所以 tier(講 upside 放大)照壓 2-3x,LTA 嘅價值反映喺「跌得冇以前深」唔係「升得
更多」。

## Node 1 — dram-hbm-integrated-leader:[MU] · late · **2-3x**(band 頂)
- **F1 營運槓桿 = 高**:DRAM/HBM/NAND fab 高固定成本;rubric §3a MU 毛利率一年半擺動 57 個百分點
  (46.7%→−10.8%)= 教科書營運槓桿。今日反方向:盈利已爆(ttm_pe 26 睇似唔貴 = peak-earnings 偽裝)。
- **F2 定價權捱擺動 = 高(最乾淨 path a)**:三寡頭 + HBM 瓶頸 + WF6 上游材料咽喉(中國掐鎢);#150 逐字
  MU RPO ~$1,000 億 / 16 份 take-or-pay 照付不議、涵蓋約兩成 DRAM 出貨 = 定價權由週期性移向結構性。
  HBM4 溢價 40-50%(#144)。**呢個係全 thesis 最強 F2。**
- **F3 距底部 = 近頂(差,反轉讀)**:capex/D&A TTM **2.803x**、單季 **3.310x**、年度 FY25 1.899x(對比 FY23
  谷底 0.990x)——**供給回應頂訊號已確認**(probe 2026-07-12);ttm_pe 26 係 peak-earnings 偽裝非便宜。
  **呢個 feature 就係 MU 由 5-10x(2023)跌落 2-3x(今日)嘅唯一原因。**
- **F4 樽頸位置 = 高**:DRAM/NAND fab 資本密度($10B+/世代)+ 全球得 3 個玩家,結構性跨週期不變(rubric §3c)。
- **F5 情緒/擁擠 = 已擁擠(差)**:gooptions 記憶體叢僅 3/22 bull(敘事層仲低)**但** SK 海力士破紀錄 IPO +
  三星 Q2 天量營業利益當日股價跌 6-9%(peak-earnings 行為)+ 雲端 capex 三成投記憶體(2024 僅 8%)= 資金
  已擠。
- **判 2-3x(band 頂)**:全 thesis 最深整合護城河 + anchor case 本尊(F1/F2/F4 全高),但 F3 近頂 + F5 擁擠
  把 magnitude 由 trough 嘅 5-10x 壓返 2-3x。對應 batch-1 laser-idm-moat(深護城河但已 run = 2-3x)。**明寫:
  呢個係晚週期 READ,唔係永久護城河評分;2023 谷底同一隻 MU 會係 5-10x。** late。

## Node 2 — nand-flash-shortage:[SNDK] · late · **2-3x**
- **F1 營運槓桿 = 中高(眼前爆發)**:NAND 2Q **+53~60% QoQ**(首次超過 DRAM、高盛稱 15 年來最嚴重短缺,
  #148/研報②)——短缺定價直落盈利底,眼前營運槓桿正在兌現。
- **F2 定價權捱擺動 = 中(打折)**:RPO **$41.6B** LTA book(去週期化證據,path a 一部分);但 NAND 歷史上
  **比 DRAM/HBM 更商品化、寡頭紀律更弱**(#128),定價權捱週期能力次於 MU。
- **F3 距底部 = 近頂(差)**:ttm_pe **79(97 分位,但 n=94 史短不可靠)**;案例庫 SNDK **78.8x 生涯**
  (2025-04 分拆起 14 個月)= **本 case 庫單一最極端**——但呢個係由分拆谷底計嘅已兌現放大,而家喺頂。
- **F4 樽頸位置 = 中**:NAND-CMX 純押,但 **capex ~0.04B = 輕資產**(供給回應風險低,同時少咗重資產壁壘)
  → 樽頸位置弱過 MU(重 fab)。NAND-CMX(推論 KV-cache)係真.新增 TAM(#135)俾少少加持。
- **F5 情緒/擁擠 = 中高**:97 分位估值 + NAND 首超 DRAM 敘事熱。
- **判 2-3x**:眼前真短缺定價權(F1/F2 眼前強)撐住 2-3x,但輕資產 + 更商品化 + 短史 + 晚期 → **唔升
  5-10x**(78.8x 係谷底計,唔係 forward)。對應 batch-1 pcb-substrate(收費站但更商品化 = 2-3x)。late。

## Node 3 — hdd-nearline-storage:[WDC] · mid-late · **2-3x**
- **F1 營運槓桿 = 高**:HDD 高固定成本,完售 + 漲價~50% 環境大幅落盈利底(#083/#085)。
- **F2 定價權捱擺動 = 高(當下)**:HDD nearline 完售 + Hoya HDD 玻璃碟 **100% 上游壟斷**封住供給
  (oligopoly STX/WDC/Toshiba)= 真.供給受限定價力時刻。
- **F3 距底部 = 中(已 run)**:ttm_pe 38(82%),capex 平;案例庫 WDC **26.78x realized**(2022-12→2026-06,
  谷底計);HDD 曾被當「結構性衰退」死股,現靠 AI-儲存 inflect。
- **F4 樽頸位置 = 中高**:oligopoly HDD 受惠 Hoya 100% 玻璃碟壟斷封供給;但大型股 + NAND/HDD 鄰接、
  次於 MU。
- **F5 情緒/擁擠 = 較低**:HDD 曾 under-loved,現 inflect。
- **判 2-3x + 跨 theme 一致性錨**:**WDC 亦係 advanced-packaging 嘅 hdd-storage-hoya-downstream node
  (batch-1 判 2-3x)。同一隻股、同一 HDD-Hoya 商業本質,兩 theme 必須同檔**——同 batch-1 GLW 兩 theme
  都 2x 一致嘅原則一樣。批 1 已標三重折扣(Tier-2 完售/50%-漲價未一手驗 + 儲存週期 late + 大型稀釋)
  壓返 2-3x;升級路徑同批 1:若完售/漲價/Hoya-鎖耐久一手驗證成立可升 3-5x-durable。mid-late。

## Node 4 — hbm4-oligopoly-leader-unbuyable:[SKHY] · late · **2-3x**(notional;⚠最薄/不可買)
- **F1 營運槓桿 = 高(理論)**:HBM4 龍頭,fab 高固定成本;但**冇乾淨可拉嘅一手財務(ADR 剛掛牌)**。
- **F2 定價權捱擺動 = 全鏈最高(理論)**:**HBM4 份額 60-70%、MR-MUF 一次灌注良率 75-80%**(填充散熱良率
  分水嶺 = 龍頭護城河根源,#150)、三星堆疊良率落後約一年——結構上係**全記憶體鏈最深咽喉**。
- **F3 距底部 = 近頂(差)+ 破紀錄 IPO 擁擠**:**~$294 億 IPO(2026-07-10,史上最大外企美股上市)本身 =
  教科書頂部擁擠訊號**(wiki 逐字:同 DRAM-ETF 上市訊號同款讀法);SK 海力士/美光目前約 6.2-7 倍 PE =
  peak-earnings 倍數,非便宜錨(#148)。
- **F4 樽頸位置 = 最高(理論)**:HBM4 MR-MUF 良率咽喉,結構上係 memory 版嘅「最深護城河本體」——**但同
  batch-1 InP 基板本體(非美股)/ SpaceX(不可乾淨買)同構:真咽喉,買唔到。**
- **F5 情緒/擁擠 = 頂(破紀錄 IPO)**。
- **判 2-3x notional + 三重旗**:(1)**2026-07-13 已無價格數據(可能退市/data feed 未 populate)→ 不可乾淨買/
  唔入 scan**(現階段亦唔入 universe.yaml,見 themes.yaml note);(2)破紀錄 IPO = 頂訊號;(3)結構上係最深
  咽喉但不可交易。**tier `2-3x` 係 notional 記錄用**——結構護城河當得起更高,但(a)不可買令實際 magnitude
  對 Karst 係 moot,(b)晚週期 + 破紀錄 IPO 擁擠壓檔。**呢個係 memory 版 SpaceX(deepest moat, unbuyable)。**
  **SKHY 處理方式 = 「標明」(任務二選一):保留喺 node 維持全 ticker 覆蓋,但明旗不可買 + notional。** late。

**Memory 最薄證據 node = hbm4-oligopoly-leader-unbuyable (SKHY)**(無價格數據、無一手財務、不可交易,
tier 純 notional);次薄 = nand-flash-shortage(ttm_pe 97 分位但 n=94 史短不可靠,magnifier 特定證據
偏眼前短缺而非結構耐久)。**注意:memory 四 node 全 2-3x = 一致晚週期,冇一個係 trough magnifier
(對比 MU 2023/2016 谷底錨),即係「主題真但入場時機已過 trough」——呢個先係 tier 冇 dispersion 嘅
真因,唔係打分懶。**

---

# THEME 2 — space-satellite(6 nodes;theme-level: early / confidence 0.28 / real-early-but-froth-priced)

價值鏈分層依 `thesis/wiki/space-satellite.md` mermaid(Morgan Stanley Space 60 第 5-7 層:⑤ 零組件/子系統
→⑥ 航天器/發射→⑦ 衛星營運/服務;+ Golden Dome 國防分食)。theme 10 隻 ticker 全部覆蓋,無遺漏
(MP 唔喺 themes.yaml space tickers——佢喺 rare-earth-materials,wiki frontmatter 列 MP 係多元化非純玩家、
已「排除於核心表達」,故本 batch 依 themes.yaml 10 隻打)。

## ★ theme-level 風險疊加:early 但 KILL-WATCH(趨勢已跌穿 200SMA,2026-07-13)
本 theme 主題週期 early(VC 單季 $36B 史上最大、Golden Dome 未撥款),但**兩層錯位**:股價 LATE-PRICED
(ASTS 377x/RKLB 94x P/S 夢想定價)。**再疊加:趨勢已跌穿 200SMA = KILL-WATCH。** 呢個係 **theme-level
風險疊加,唔改各 node 嘅 magnitude 性質,但硬壓 sizing/urgency**——所有 binary node 應以 option/事件
框架、極細注表達,KILL-WATCH 期間尤其唔加碼。(magnitude_tier 講「若催化兌現嘅放大潛力」,KILL-WATCH
講「而家唔應該重注」,兩者唔矛盾,分開記。)

## Node 1 — profitable-aero-space-diluted:[HEI, LOAR] · mid-late · **2x**
- **F1 營運槓桿 = 低中**:HEI 大型多元化航太售後(FY25 $4.485B);LOAR 輕資產併購飛輪(capex ~$3-6M)——
  太空 capex 週期對佢哋盈利底嘅槓桿細(太空非主業)。
- **F2 定價權捱擺動 = 中高但太空外**:HEI 「不押單一衛星商、誰中標零件都在裡面」鏟子護城河(#111);
  LOAR 迷你 TransDigm「買低倍數利基件、整合後享 LOAR 溢價」飛輪(#041,唯一 bull)——**護城河真,但係
  航太售後嘅護城河,唔係太空超級週期嘅。**
- **F3 距底部 = 近頂(差)**:HEI ttm_pe **63.6(87 分位,n=7146 深史→頂區)**;LOAR 113.7(29 分位但 n=546
  短史 + GAAP 被併購攤提壓)。
- **F4 樽頸位置 = 中(但太空曝險薄)**:HEI 鏟子護城河真但太空只係 ETG 一段;LOAR 空曝險最薄(售後
  50-55%、國防<25%)。
- **F5 情緒/擁擠 = 中**:HEI 站頂;LOAR 內部人 cluster 買 $11.3M(唯一 bull)。
- **判 2x**:唯二有盈利 + 真護城河,**但太空非主業 → 太空超級週期非線性放大唔到佢哋**(放大要落喺太空
  本業);耐久-但-被稀釋防守腿,對應 batch-1 GLW / ai-power-grid ipp-utilities(2x)。**呢個係把「profitable
  + 有護城河」自動當高檔嘅陷阱嘅反例——太空非主業就係封頂原因。** mid-late。

## Node 2 — launch-execution-bet:[RKLB] · event-driven · **5-10x-binary**
- **F1 營運槓桿 = N/A(pre-profit)**:會計仍虧損,理論槓桿大但未兌現;capex $22M→$50M→$27M(Neutron 建置)。
- **F2 定價權捱擺動 = 中(未證)**:發射純玩家、SpaceX 外最活躍,backlog **$2.2B(+108%)**、Q1 營收
  $200.3M(+63.5%)= 有真訂單簿(非純概念);但要**同 SpaceX 競爭**,定價權未證。
- **F3 距底部 = 冇法用盈利量**:pre-profit,P/S 94x = 押未來非 trough 便宜。
- **F4 樽頸位置 = 中(且瓶頸正崩)**:發射曾係 THE 樽頸,**但發射成本正崩塌($54,500→$2,720/kg,-95%)=
  主題引擎,亦即發射本身唔再係耐久稀缺**;RKLB 係#2 發射位置(真位置,非純彩票)。
- **F5 情緒/擁擠 = 中高**:發射層核心表達,市場關注度高。
- **判 5-10x-binary(justified,非彩票)**:有真發射#2位置 + 真 backlog + **定日 binary 催化(Neutron 2026Q4
  首飛)**——同 batch-1 inp-substrate(真咽喉 + binary)同構,係「有 anchor 嘅 option」唔係純彩票。但
  pre-profit + 首飛執行 binary + 發射瓶頸正崩 → 用 option/事件框架、極細注、盯 Neutron。event-driven。

## Node 3 — d2d-spectrum-optionality:[ASTS] · event-driven · **5-10x-binary**
- **F1 營運槓桿 = N/A(pre-revenue)**:capex 爆發 **$82M→$424M(5x,建星系)**= 早週期建置,理論槓桿巨大
  但未兌現。
- **F2 定價權捱擺動 = 中高(真監管咽喉)**:**FCC 授權 + 頻譜 + 實測 98.9 Mbps + backlog $12 億**——D2D
  手機直連衛星,**FCC/頻譜係真.監管咽喉**(唔係人人做得到),呢個係 ASTS 同純彩票嘅分野。
- **F3 距底部 = 冇法用盈利量**:P/S **377x(全叢最高,近 590x 2025 營收)= 夢想定價**,押未來。
- **F4 樽頸位置 = 中高(監管型)**:頻譜 + FCC 授權 = 監管型咽喉(非物理製造咽喉);2026H2 衛星能否準時
  足量上天係執行 binary。
- **F5 情緒/擁擠 = froth 端**:空單 18.4%、377x P/S = 最曝險。
- **判 5-10x-binary(justified by moat,非 blanket froth)**:有 FCC/頻譜護城河 → 唔係「因為 pre-profit
  就 binary」而係「有真監管咽喉 + binary 執行催化」;但夢想定價 + pre-revenue + 執行 binary → 極細注/
  option 框架。**同 Node 4 純彩票分開,就係 binary 紀律嘅體現。** event-driven。

## Node 4 — preprofit-smallcap-lottery:[RDW, LUNR, PL, BKSY] · early · **5-10x-binary**(⚠最薄,magnitude 不可量)
- **F1 營運槓桿 = N/A**:全部 pre-revenue / 虧損(RDW/PL/BKSY ttm_pe 無;LUNR 9.6 合約 lumpy 失真)。
- **F2 定價權 = 未證**:衛星製造(RDW)/月球基建(LUNR)/對地觀測(PL)/訊號情報(BKSY)——**無一個握清晰
  咽喉**,執行賭注。
- **F3 距底部 = 冇法用盈利量**:P/S 8-33x,押未來。
- **F4 樽頸位置 = 低/未證**:小型、燒錢、無護城河證明。
- **F5 情緒/擁擠 = froth**:小型二元投機端。
- **判 5-10x-binary(彩票端,magnitude 本質不可量)**:同 batch-1 cpo-speculative(SIVE/LWLG「純選擇權/
  純投機」)同構——pre-revenue 無護城河 = magnifier_model_plan §3f/§4 警告嘅彩票/option profile(MAX effect、
  平均輸)。**tier `5-10x-binary` 正確 flag 做 option/彩票、極細注**;magnitude 數字本質不可量但「彩票性質」
  證據強。**本 theme 最薄 magnifier 證據。合成一個 node = 避免俾四隻無護城河小型股各自扮有 magnitude。**
  early(pre-profit)。

## Node 5 — golden-dome-policy-option:[KTOS] · event-driven · **2-3x**(唔升 binary 檔)
- **F1 營運槓桿 = 低(薄利潤率封頂)**:2025 營收 $1.347B(+18.5%)**但 Op 利潤率僅 2.9%**(ttm_pe 294.9 失真)
  ——薄利潤率**限制**營運槓桿放大空間。
- **F2 定價權捱擺動 = 中低**:國防太空,但「**2,400+ 家入池 = 門票非合約**」(mermaid)= 得標唔保證;
  無耐久咽喉。
- **F3 距底部 = 中**:有營收(**非 pre-profit**),PE 因薄利潤率失真;溢價追有修正風險。
- **F4 樽頸位置 = 中(相對 torque 真但無咽喉)**:Golden Dome 相對衝擊最大(**一張 $446.8M ≈ 年營收 33%**)
  = 真.相對 torque(小基數 + 大相對合約);但門票非合約 + 無結構咽喉封住 magnitude 上限。
- **F5 情緒/擁擠 = 中(政策事件)**:Golden Dome CBO $1.2T 願景、**已到位僅 $250B**(政策二元)。
- **判 2-3x(刻意唔升 binary)**:**已有營收(非 pre-profit)+ 相對 torque** 值 2-3x,**但**薄利潤率 + 無咽喉 +
  門票非合約 + 溢價 → 政策期權封頂。**呢個係 binary 紀律嘅關鍵示範:KTOS 睇落「太空 + 政策投機」好易被
  懶惰打成 5-10x-binary,但佢有營收 + 無咽喉 + 薄利潤率 = 應該 2-3x event-driven,唔升 binary 檔。** 對應
  batch-1 emib-optionality 嘅反面(INTC 近零盈利/turnaround → binary;KTOS 有實在營收 → 唔 binary)。event-driven。

## Node 6 — merger-arb-special-sit:[GSAT] · event-driven · **2x**(⚠框架最不適配)
- **F1-F4 = 框架不適用**:GSAT = Globalstar,Amazon **$11.57B 收購中**(S 波段頻譜、待 FCC、約 2027 關);
  ttm_pe 19.2(4 分位)**但係併購套利估值、非營運**。
- **F5 = 事件(過會)**:催化 = FCC 批 deal;風險 = 破局。
- **判 2x(schema 完整 + 全 ticker 覆蓋用,明旗最不適配)**:**併購套利 = 上檔封頂(收購價)+ binary on
  過會,根本唔係供需 magnifier**——magnitude 天生封頂(套利價差),唔屬任何一檔乾淨。用 `2x`(parseable
  最低有意義檔)+ **明旗:GSAT 係 special-situation merger-arb,唔應該用 magnifier 框架評,tier 純為
  schema 完整 + 全 ticker 覆蓋**。**呢個係全 batch 框架最不適配嘅 node**(GSAT 甚至比純彩票更唔啱框架:
  彩票至少係供需驅動嘅 option,套利連供需都唔係)。event-driven。

**Space 最薄/最不適配**:(1)框架最不適配 = merger-arb-special-sit (GSAT,連供需 magnifier 都唔係);
(2)最薄 magnifier 證據 = preprofit-smallcap-lottery (RDW/LUNR/PL/BKSY,magnitude 不可量);
(3)theme-level KILL-WATCH(200SMA 破)令所有 binary node 都應極細注/暫緩加碼。

---

## 校準對照(確保唔係亂標)
- **對 MU 2023/2016 谷底錨(rubric §3/§7,memory theme 自身歷史)**:兩個谷底錨 F1 高 + F3 遠底 + F4 高 →
  真 5-10x magnifier。**memory 今日四 node 冇一個 F3 遠底**(全部 capex 頂訊號/近頂)→ 冇亂標高檔,一律 2-3x
  = 誠實反映「入場時機已過 trough」。呢個係「用到盡」歷史錨嘅意思:唔係攞嚟撐高分,係攞嚟證明今日**唔應該**
  俾高分(同一框架、同一隻股、trough 5-10x vs top 2-3x)。
- **對 FSLR-vs-STP(rubric §6):F4(樽頸位置)+ P1(護城河獨立於商品)最有分辨力。** space 用 F4 拉開:
  HEI/LOAR 護城河真但太空外(F4 太空曝險低→2x);RKLB/ASTS 有真位置/監管咽喉(F4 中高 + binary→5-10x-binary);
  RDW/PL/BKSY/LUNR 無咽喉(F4 低→彩票);KTOS 相對 torque 真但無咽喉(F4 中→2-3x 唔升 binary);GSAT 唔適用。
- **對 batch-1 六 node semantics 一致**:2x = 大型稀釋/耐久-但-被稀釋(GLW ↔ HEI/LOAR);2-3x = 深護城河但
  已 priced / late(laser-idm ↔ MU/SNDK,pcb-substrate 更商品化 ↔ nand);5-10x-binary 兩種——有真咽喉+binary
  (inp-substrate ↔ RKLB/ASTS)vs 純彩票 option(cpo-speculative ↔ RDW/LUNR/PL/BKSY);WDC 跨 theme 同檔
  (2-3x,同 GLW 跨 theme 同檔原則)。
- **對 ai-power-grid 五 node dispersion**:ai-power-grid 有闊 tier dispersion(2x~5-10x-binary,因價值鏈跨
  early→late);memory **冇 dispersion**(全 2-3x,因全鏈一致 late)是誠實的結構差異,唔係打分懶;space
  **有 dispersion**(2x/2-3x/5-10x-binary,因主題早但表達品質參差)。

## 已知風險 / 待大腦覆核
- **sizing v2-shadow 交互**:`theme_magnitude_mid` ticker-count-weighted → memory 2.50、**space 5.35**
  (6/10 ticker 係 5-10x-binary,4-隻彩票 node 加權拉高)。space 5.35 高 magnitude + confidence 0.28
  (>V2_MAGNITUDE_CONF_GATE 0.25,啱啱過閘)→ v2-shadow 可能把 space 排高。**但(a)v2 純 shadow ledger 非
  operative;(b)`is_event_binary()` 讀 theme-level cycle_stage=="event-driven",space theme 級係 "early"
  → space 唔會被當 theme-level event-binary micro-position(sizing.py 自己 comment 已知呢個 narrower 限制)。**
  ★ 建議大腦留意:本 batch 令 space「6/10 binary」變 explicit,同 sizing.py 現時「space 唔當 event-binary」
  嘅取捨形成張力——加上 KILL-WATCH,值得覆核 space 喺 v2-shadow 嘅排名係咪需要 theme-level binary 處理。
- **SKHY**:無價格數據處理方式已選「標明」(保留 node + 明旗 notional/unbuyable)。若大腦傾向「唔分組並
  解釋」,可移除 SKHY node、喺 comment 解釋——但會失去全 ticker 覆蓋。現版選擇維持覆蓋 + 明旗。
- **KILL-WATCH(200SMA 破)** 係任務提供嘅 2026-07-13 context,非 wiki(wiki 為 2026-07-01/07-08)。node
  magnitude 性質不受影響,但 sizing/urgency 要反映。
