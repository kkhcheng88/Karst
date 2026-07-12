# Phase-3 Supercycle Magnifier 模型 —— 建構計畫【進行中,2026-07-09】

> 起因:用戶 2026-07-09 指出 agent 把「細價股 value 篩」錯當「supercycle magnifier」——
> 兩者完全唔同。Phase-3 唔係細價 value(嗰個應該掃 IWM/meme);係「識別供需超級週期,
> 然後揀邊隻股會被非線性放大 5-10x」。呢個 paradigm 錯誤要用正經模型 + case study 修正。

## 0. Paradigm 校正(唔好再犯)

| | 細價 value 篩(錯用) | Supercycle magnifier(對) |
|---|---|---|
| 搵乜 | 平而穩 | 會被週期非線性放大 |
| 買入時機 | 平嗰陣 | **睇落最差嗰陣**(trough,蝕錢/無 PE)|
| 估值 metric | PE percentile | **PE 倒轉**(trough 高 PE=買 / peak 低 PE=賣);normalized earnings / P/S / 距底部 |
| 適用 | IWM/meme ETF | Phase-3 主題股 |

## 1. Magnifier 機制(工作假設,待 case study 驗證)

**10x = 營運槓桿 × 需求超級週期 × 供給受限/定價權 × 情緒 re-rating(trough→supercycle)**

Anchor case anatomy — **MU 記憶體**(現行主題,最乾淨教材):
- Trough(2023):DRAM 過剩、蝕幾十億、PE 負/無意義、「死週期股」情緒 ← 10x 起點
- 放大:①三寡頭供給紀律 ②巨大營運槓桿(fab 固定成本)③新需求向量(HBM/AI,供給受限高毛利)
  ④對手過剩期砍 capex → 供給收緊
- 早期訊號:LTA 簽約 + 電話會 constraint-language(證咗早敘事 17 個月)
- 放大結果:EPS 負→$12+,同時 multiple re-rate → 5x+
- ★ 反直覺:PE 無意義/最高(蝕/微利)時買;PE 最低(peak earnings)時賣

ex-ante 可偵測 features(要 encode 成 scorecard,取代 naive PE):
1. 營運槓桿(毛利軌跡/固定資產密度/收入基數細)
2. 供給受限+定價權(產業結構/對手 capex 紀律/交期)
3. 距底部幾遠(normalized/mid-cycle earnings,唔用 trailing PE)
4. 樽頸位置(arms-dealer vs commodity player)
5. 情緒/擁擠(低=早=好)

## 2. 建構步驟(次序重要)

| # | 步 | 狀態 |
|---|---|---|
| A | **case 庫**:歷史 5x/10x 超級週期贏家+輸家(避 survivorship)| ✅ 完成(9 週期~90 名 + 883 價格篩命中,`results/2026-07-09_magnifier_case_library.md`)|
| B | **學術論文**:回報偏態(Bessembinder)/資本週期/營運槓桿/週期估值/彩票警告 | ✅ 完成(21篇已核實,`docs/2026-07-09_magnifier_literature.md`)|
| C | **書**(用戶任務,返屋企 gather → ingest):Capital Returns(Chancellor)★ / Expectations Investing(Mauboussin)/ One Up on Wall Street(Lynch)| ⏳ 用戶 |
| D | **逆向工程 case study**:由 A 抽共通 ex-ante features(MU 先行,最乾淨)| 待 A |
| E | **magnifier scorecard**:encode features,replace theme_signal 對超級週期名嘅 PE 邏輯 | 待 D+C |
| F | **constraint scanner 生產化**:defeatbeta 電話會 constraint-language 每季掃全宇宙 → 早期訊號隊列 | 待 E(先定模型,自動搵料先唔白做)|

## 3. Constraint scanner 現狀(誠實)

- ✅ 概念驗證(`exp_constraint_language.py`,MU 早敘事 17 個月)
- ✅ 數據源 = defeatbeta `earning_call_transcripts`(76-83 季;1 週延遲對月級訊號 OK)
- ❌ **未 production**:一次過 probe,冇每季自動跑/擴全宇宙/入隊列;冇排程
- → 步 F;但排喺模型(E)之後,因為 scanner 搵「邊個週期起」、magnifier 揀「邊隻放大」,要先定模型。

## 3b. 硬要求:cycle_stage 要 per-node,唔係 per-theme(用戶 2026-07-09 AI-power case)

用戶洞見:「AI 用電被電力供給樽頸,而電力唔可一日建成」= 資本週期 setup(需求耐久+供給結構性慢
=長短缺+持久定價權)。但套用力度**沿價值鏈遞增**:
- 電網設備(ETN/GEV,GRID ETF)= **LATE/priced**(近期贏家已跑;供給幾年擴到,你個「慢」邏輯最弱)
- IPP(VST/CEG,UTES ETF)= MID
- 鈾/核燃料(URA/CCJ)= **MID 但耐久**(礦幾年)
- SMR/次世代核(OKLO/NNE/SMR)= **EARLY,pre-revenue,最大 magnitude(10x option)但 binary**

→ **同一主題,各 node 嘅 stage 同 magnitude 差一個數量級。** 現行 theme_signal 單一 stage 標籤壓平咗。
**magnifier 模型必須 per-value-chain-node 標 stage + magnitude**;10x「早+高倍數」通常住喺上游樽頸/
供給最慢嗰端,唔喺已跑嘅下游設備端。case 庫預期會喺每個歷史週期重複見到呢個「上游 vs 下游」stage 差。
對用戶 URA+GRID+UTES 籃嘅意思:URA=耐久早腿、GRID=late froth 腿、UTES=mid;10x option 喺籃外嘅 SMR 端。

## 3c. Case 庫抽出嘅兩個跨 9 週期 pattern(2026-07-09,step A 產出 —— 直接 encode)

**呢兩個喺全部 9 個超級週期一致重現,係 magnifier 模型最強嘅實證 feature:**

1. **★ 贏家嘅護城河獨立於商品價格本身**(FSLR vs 幾乎全太陽能同業 = 最乾淨單一實驗)。
   → 洗牌:magnifier ≠ 「騎商品上升」(嗰個係純週期 beta,商品回落即死);magnifier = 「擁有一樣
   喺商品回落後仍生存嘅結構性護城河/定價權」。**refine feature #2/#4**:唔淨問「有冇樽頸」,問
   「呢個護城河喺週期下行時仲存唔存在」。
2. **★ 輸家喺週期頂前做槓桿式產能擴張 / 併購**(9 週期一致)。→ 呢個係**死亡 marker = 新 kill feature**:
   「供給紀律逆轉」——公司由紀律轉狂擴 capex/借錢/併購 = 頂訊號。同 memory-supercycle 現行 kill
   「LTA 停滯 OR HBM 產能 ramp AHEAD of 需求」同源。

**Ex-ante 效力驗證(重要)**:SMCI(會計醜聞)、WOLF(Wolfspeed 破產)兩個爆煲案例,**repo thesis wiki
已預先寫低嘅 kill_condition 事前捉到** → 框架有 ex-ante 力,唔止事後解釋。

**誠實 caveat**:pre-2010 週期數字多來自 WebSearch(標「約/unverified」),未經 Bloomberg/CRSP 二核;
部分 ticker 有 reuse/反向合股污染。→ **magnitude approximate,pattern(質性)先係產出**;要做嚴謹統計
驗證(尤其 feature #3 週期 PE 倒轉,文獻地基薄)要用付費歷史數據另核。

## 3d. Discovery 層 reframe(用戶 2026-07-09 —— 全市場 DB,唔係監察已知主題)

**關鍵分野**:Phase-3 早期偵測 = **全市場 unknown-unknowns 發現**,唔係監察 themes.yaml 已有嘅名。
只掃已知主題永遠發現唔到下一個 supercycle(佢喺變敘事前唔喺 watchlist)。
- **DB 範圍**:defeatbeta 有 transcript 嘅**全部股**(~6000-7000 隻),唔係 63 監察名。
  (`thesis/.raw/transcripts/` full-market;`corpus.db` FTS5 增量;全 gitignored/regenerable。)
- **cadence**:**週度**(唔係季度)—— transcript 逐步落 + constraint-language 係 trend,週度 re-index+scan
  捉得最快。`thesis/weekly_corpus.cmd`(prefetch --universe full → build --incremental)。
- **兩層清晰**:discovery(全市場掃新興 constraint cluster → 冒出新主題候選)vs monitoring
  (themes.yaml 已知名 → theme_signal 每日 verdict)。scanner 生產化(步 F)= discovery 層。
- 現狀:核心 DB 已成形(3623 docs,transcript 檢索 work);full-market prefetch 進行中(marathon,
  規模估算 → `results/2026-07-09_fullmarket_transcript_scope.md`)。

## 3e. Smart-money / 13F 做 discovery 輸入(用戶問「monitor Bessembinder holdings」)

**釐清**:Hendrik Bessembinder = 學者(ASU),冇基金/13F holdings,冇嘢可 monitor —— 佢貢獻係研究
(4% 股票創造全部財富)。**底層 idea 啱**:追蹤有捉 multi-bagger 往績嘅集中投資者嘅 13F。
- caveat:13F 延遲 45 日 + 季度 + 只 long = **滯後**(對「早期」發現係硬傷);copycat 學術證據 mixed。
- 定位:discovery 層 **probe 級候選**(唔係 commitment),同 constraint-language(更早更強)並列;
  同 insider-cluster(已陰性,公司內部人)唔同 —— 呢個係外部技術型 allocator。證據查緊
  (`docs/2026-07-09_text_and_smartmoney_methodology.md`)。

## 3f. 框架射程邊界(用戶 2026-07-09 quantum 洞見)—— 重要 scope 結論

**magnifier + constraint-language 框架只捉「供需驅動」超級週期,唔捉「敘事/里程碑驅動」主題。**
- 供需型(框架射程內):記憶體/pharma/電力/鈾/光通訊上游 —— 有真樽頸、營運槓桿、供給受限、
  定價權;scanner 捉「on allocation / lead time / sold out」供給受限語言。
- 敘事/里程碑型(框架射程外):**量子(RGTI/IONQ/QBTS)、部分 AI-software** —— 由 hype/催化劑
  (Google Willow 2024-12)/政府撥款驅動,**無規模產品、無供給約束、無 allocation 語言**。
  scanner 對佢哋應該**靜晒**(= 框架正確講「唔係我嗰種獵物」)。
- 學術:敘事/里程碑型接近**彩票股(MAX effect,平均輸,Bali-Cakici-Whitelaw)** → **唔應該做
  Phase-3 magnifier 目標**;想玩 = 另一個投機 sleeve、另一套規則(里程碑、極細注、option 式)。
- 驗證中:6-case 實驗(`results/2026-07-09_filing_vs_transcript_signal.md`)含 RGTI 做 negative
  control —— scanner 對 RGTI 靜 vs 對 MU/AXTI 有 hit,confirm 邊界。

## 3g. Phase-3 文字語料定案(2026-07-09,6-case 實測後)

**defeatbeta 三個文字源,實測後定案:**
- **earning_call_transcripts = 主管道**(全文 2005+,constraint-language 早敘事 17mo,已證)。
- **10-K/10-Q 全文 = 拒絕**(`results/2026-07-09_filing_vs_transcript_signal.md`,6-case:MU/LLY/VST/CCJ/
  AXTI + RGTI 對照)。實測**劣過** transcript,唔止 redundant:時機冇一個贏 transcript(財報全窗未
  轉正 vs transcript MU 1.741/CCJ 早 18mo);財報書面語帶通用鬆板詞拖低淨分(LLY「pricing pressure」=
  PBM 壓價 false signal);Lazy-Prices 逐份新增語言雜訊太大。**唔納入,慳 EDGAR 抓取管線 + ~2.4x 儲存。**
- **news = 淨標題無全文** → 最多做輕量事件/注意力層(Tier-3),可有可無。
- **SC 13D/13G(sec_filing 索引免費列)= smart-money 累積 probe 候選**(同 13F 問題,見 3e)。
- 8-K = 事件層,同供需價值鏈分開,唔納入 constraint 用途(用戶指出)。

**RGTI 負面對照結果**:量子兩邊近零 → confirm 框架只捉供需型,唔捉敘事/里程碑主題(見 3f)。
caveat:詞表為口語 transcript 校準(未為財報重調);AXTI 窗可能早咗(勿讀成 AXTI 非真樽頸)。

## 3h. Queued 實驗:板塊層 constraint-language → 年度板塊輪動(用戶 2026-07-09「revisit sector rotation」)

**動機**:oracle 逆向工程 —— 真.可捕捉獎 = 完美「年度」板塊揀 ~2× SPY(週頻 155% 係頻率幻象);
量化板塊輪動已判死(0/28 價量因子);oracle 親口:年度 regime = 質性宏觀敘事,唔喺價格圖。
**未測過嘅橋**:constraint-language(供需文字,已證個股層 MU 早 17mo)**aggregate 到板塊層** →
睇某板塊公司集體講供給緊,lead 唔 lead 板塊年度回報?**呢個唔係死咗嘅量價因子,係 oracle 講「唯一
有希望」嗰種價格外供需資訊嘅系統化。**
**設計**:板塊 = GICS 11;訊號 = 成員 transcript 淨受限密度(季);裁判 = 板塊 forward IC(年度非重疊);
bar = IC≥0.05(凸獎勵→贏 SPY);對比 oracle 上限 + 0/28 baseline。**誠實風險**:可能板塊層一樣 IC≈0。
**Gate**:需板塊平衡 transcript 覆蓋 → 排喺全市場 marathon 之後(現 144 名偏 AI/科技,唔夠)。
**若成立**:板塊輪動由「core 判死」→ 變「Phase-3 質性訊號嘅一個新 sleeve」(仍係衛星,唔入 core 機械層)。

**★ 結果(2026-07-10,marathon 完成後跑,`exp_sector_constraint_language.py`,
`results/2026-07-10_sector_constraint_language.md`)—— 判死,同量價因子(0/28)同一命運**:

用戶指定 unsupervised 探索先(唔即刻計正式 supervised IC pass/fail)。全量 908 個板塊-季度、
84 季(2005Q4-2026Q3)、每季中位數 158 隻公司/板塊(真.平衡樣本,唔似細測試得 1-5 隻):
- Pooled correlation(density vs fwd_3/6/12m 相對回報):**-0.009 / -0.010 / -0.008 ≈ 0**
- 動量變體(density YoY delta,對應用戶「word trend」提議):**同樣 ≈ 0**(+0.025 12m)
- 逐板塊拆開:11 個入面 **8 個負相關**(XLB/XLK/XLY/XLRE/XLF/XLI/XLV/XLE),得 3 個正——
  方向唔一致 = 噪音特徵,唔係真訊號嘅樣。高密度板塊-季度之後一年相對回報平均仲**係負**(-2.2%),
  同假設方向相反。

**判斷**:唔係做錯,係**粒度太粗**——MU 嘅 17 個月早期訊號成立喺「記憶體」呢個好窄嘅子行業,
但溝入 GICS 11 大板塊(如 Technology 158 隻公司入面得幾隻相關)後,窄訊號畀噪音溝晒。
**同量價因子(0/28)拼埋睇:兩條完全唔同嘅路(價量、文字)都做唔到廣板塊輪動** ——
反過嚟**加強咗信心**:你哋而家用緊嘅窄 thesis 粒度(memory-supercycle/ai-power-grid 呢類)
先係真.有效嘅表達層,唔係廣板塊。**§3h 呢條 queued item 就此判死,唔再追。**
未跑正式 supervised IC/placebo/LM 對照(探索已經冇 pattern,升級只會更精確咁確認「冇嘢」)。

## 3i. 知識層待補輸入(用戶 2026-07-09)—— 擺啱層先有用

統一原則:transcript constraint-language = 早期 edge(primary,早 17mo);analyst/iBank 報告 =
滯後共識,擺**擁擠/priced-in 閘** + 4-KPI context,唔係早期層。

| 輸入 | 正確 slot | 機制 | caveat |
|---|---|---|---|
| **Analyst / expert 報告** | 4-KPI 佐證 + crowding(越多睇好=越 late,priced-in 扣分)| thesis INGEST workflow 已有;要自動化須用戶俾來源 feed | consensus/lagging |
| **iBank 資金流報告**(BofA Flow Show / GS / JPM)| **擁擠閘**(填現時質性 gap)+ 板塊輪動嘅「遲/擁擠」端(vs constraint-language 嘅「早/供給」端)| 多數付費→用戶 access;免費 proxy = CFTC COT / ETF issuer flows / ICI | 付費 + 週度滯後 |

**板塊輪動接口**:供給緊(constraint-language 早)+ 錢未湧入(flow 未擠)= 買點;錢湧晒 = 賣點。

**★ 三層架構(用戶 2026-07-09 釐清:資金流 = 市場/板塊層「現狀評估」,唔係個股早期)**:
```
大市層 : VIX/趨勢/DIX + 資金流 positioning  -> risk-on/off + 擁擠現狀(Phase 0/2)
板塊層 : constraint-language(早) + 板塊 flow(擠) -> 板塊輪動(3h 條橋;板塊 flow 係真 gap)
個股層 : transcript constraint + magnifier       -> 超級週期名(Phase 3)
```
誠實 nuance:資金流 = descriptive「現狀/positioning」(入 dashboard + priced-in 閘,啱);但「現狀」≠
自動有預測力 —— flow 多同步/滯後 + smart(DIX,IC 0.11-0.14 已證)vs dumb(散戶頂部湧入=逆向)方向相反。
→ 用法:①現狀 context(直接用);②另測預測力(同 DIX 咁測,預期 modest,分 smart/dumb)。
免費源:ICI / ETF 板塊 flows / CFTC COT / DIX(已有);iBank(BofA/GS)= premium,用戶 access 先。
**Magnifier 書(定版,待用戶攞→ingest)**:①Capital Returns(Chancellor)★ ②Expectations Investing
(Mauboussin)③One Up on Wall Street(Lynch)。文字掃描部分唔使多書(LM 詞典已標準)。

## 3j. iBank/broker 報告實測評估(用戶 2026-07-09 上載 5 份,派 5 subagent 逐份抽)

結論:冇一份垃圾,但價值差好遠;最高價值嗰份係供給端(UBS Memory),唔係資金流。稀缺 = 供給
(theme-specific 供需月報,冇第二處攞);泛濫 = flow/positioning(3 份重疊,揀一份夠)。

| 報告 | 主 slot | 獨有價值 | ingest 難度 | 判 |
|---|---|---|---|---|
| **UBS Memory Semis Monthly** | (a)供給早訊 | sufficiency ratio + ASP 前瞻 + LTA 鎖量%(=on-allocation 代理)+ 庫存週 + wafer starts,全 vendor chain 逐月,前瞻到 2027E | 難(多欄表,pdftotext 亂→需 layout-aware/OCR)| ★最高·必留(月)|
| **GS Weekly Fund Flows** | (b)板塊擁擠 | 每板塊/國家 4週 flow 嘅 **Z-score**(現成極值),純表回溯 2019;EPFR 全市場 | 易(純表)| ★最高·必留(週)|
| **BofA The Flow Show** | (d)大市擁擠 | **Bull&Bear Indicator**(0-10 contrarian 綜合,公開 backtest,今期 9.5=Sell)+ 私人客戶配置 | 中(取 B&B block)| 留·淨取 B&B(週)|
| **GS Prime Rundown** | (b)聰明錢 | HF gross/net 槓桿 percentile + 衍生/funding microstructure + 槓桿 ETF 結構 | 中 | 留·淨取槓桿+vol(週)|
| **MS Weekly Warmup** | (c)板塊 house view | 11 板塊 OW/EW/UW grid + SPX 情境目標 | 難(多圖需 digitize)| 留·淨取2表·**首個可棄**(週)|

**三個判斷**:
1. **稀缺 vs 泛濫方向唔好搞反** —— flow 報告 3 份大量重疊,只需①一份板塊 flow(GS Fund Flows 贏)②一份
   大市 contrarian(BofA B&B 贏);多一份 = 邊際遞減。**值得再搜集嘅係 theme-specific 供需月報**(像 UBS
   Memory:記憶體✅ / 待補電力·光通訊·封裝),唔係更多 flow。
2. **Smart vs dumb 補實**:聰明錢 = DIX(暗盤,已有)+ **GS Prime HF 槓桿**(呢片令 GS Prime 唔係純
   redundant);散戶/泛總 = GS Fund Flows(EPFR)+ BofA 私人客戶(滯後,做 fade/context);contrarian
   綜合 = BofA B&B。
3. **MS Warmup = consensus 閘唔係 alpha**:sell-side 已 OW = 開始變共識 = priced-in;做 priced-in 參照,
   最接近可棄。

實務 flag:PDF 表格自動化要 layout-aware 解析或頁面 OCR(subagent 今次用 PyMuPDF render 成圖先讀到;
環境冇 poppler/pdftoppm)。唔使即整,記低。

**★ Push vs Pull 原則(用戶 2026-07-09:「週期報告我搵到,但 sector/stock analyst report 係 ad hoc,
唔知有冇用」)**:

| | Push(週期可預測) | Pull(ad hoc 不可預測)|
|---|---|---|
| 例 | Flow Show / Fund Flows / UBS Memory | 板塊 deep-dive、個股 analyst |
| 價值 | 喺時間序列(Z-score/趨勢),單期唔重要 | 喺單次答一條具體問題,唔累積成序列 |
| 做法 | 建常設 feed | 被自己訊號**觸發**先 pull,用完即棄 |

- 核心:usefulness 唔係報告屬性,係「你有冇具體問題」屬性。**事前判唔到有冇用 = 唔可入系統層。**
  冇觸發嘅 ad hoc report 預設當 noise。
- Ad hoc report 三個真用途(全 pull + 有觸發):①共識/priced-in 基線(觸發=隻名 fire)②bootstrap 新主題
  價值鏈地圖(觸發=新主題入 radar,即 3h/「on-radar fan-out」機制嘅輸入;**唯一高價值格**,一次性 onboarding)
  ③反面壓力測試(觸發=已有 thesis)。
- 個股層再誠實:多數內容 Karst 已有更一手源(數字→reject;敘事→transcript 早;供需→theme 月報)。analyst
  淨補:共識基線 + 新主題地圖 + 異見,全 pull-only 低邊際。
- 姿態:週期報告 commit 搵(常設);ad hoc **唔主動獵**,淨兩觸發下攞完即棄,唔入常設。
  一句:**週期報告買「序列」,ad hoc 買「答案」;錯誤 = 當 ad hoc 都好似週期咁去收集監察。**

## 3k. 報告 4 大原型分類法(用戶 2026-07-09 上載 11 份後收斂,self-service)

關鍵細化 push/pull:**「定期」≠「push feed」**。要**高頻 + 有重複數字序列**兩樣齊先算 feed;
年度/半年展望雖定期但係 reference。

| 原型 | 頻率 | 內容 | 例 | slot | 做法 |
|---|---|---|---|---|---|
| **A 資金/持倉** | 週 | flow/positioning 數列 | GS Fund Flows★ / BofA Flow Show★ / GS Prime | (b)擁擠+(d)大市 | PUSH·砌 series,留 1-2 |
| **B 主題供需** | 月+週 | ASP/spot/channel check | UBS Memory 月★ / BofA Memory 週★ | (a)供給早訊 | PUSH·每活躍主題留 |
| **C 策略/展望參照** | 年/半年 | 敘事+曝險地圖 | MS Exposure Guide / JPM Outlook | (c)籃 map+共識基線 | REFERENCE·讀一次,唔砌 series |
| **D ad hoc 深研** | 不定 | 個股/板塊一次性 | sector/stock 深研 | priced-in 檢+主題 bootstrap | PULL·訊號觸發先攞 |

**自我分類兩問**:①高頻定期(週/月)? ②有重複數字序列(唔淨係文字)? 兩 YES→A/B push;
定期但低頻/文字為主→C reference;不定期→D pull。
(邊界:MS Weekly Warmup = 週頻但共識內容 → 當低優先週報,只採 OW/EW/UW grid 做共識讀數。)

**逐份定案(11 份累計)**:
- A:GS Fund Flows(板塊 Z-score,最強)、BofA Flow Show(B&B 指標)、GS Prime(HF 槓桿=聰明錢)
- B:UBS Memory 月(結構模型 = model-of-record)、**BofA Memory 週(spot tape+channel check+謠言拆解,
  同月報互補唔重疊,兩份都留)**
- C:MS Exposure Guide(年度 ticker→地區曝險 map,採一次)、JPM Outlook(65pp ~90%敘事,滯後共識,**跳過
  standing ingest**,頂多 pull sanity check)、MS Warmup(週但共識,低優先)
- 重複確認:UBS 7/3 dccb1957 = 已評版逐數字對得上,無需重評

**B&B series 實證(push 價值活教材)**:6/11=8.8 → 6/19=9.2 → 7/02=9.5(全 Sell,極貪區),
單調爬升+資金同步加速;單期睇唔到,series 先見。直接餵 core 貪婪/減磅閘 + 對上 BofA backtest
(17 次 Sell→2-3 個月平均跌 2-3%)。

## 3l. IMA agent 抽取管道(用戶 2026-07-09:改用 Tencent IMA 知識庫 prompt,取代人手上載)

用戶有 IMA 知識庫(擁有者持續上載投行研報含 flow;內建 DeepSeek/GLM agent 可 Q&A;GitHub 可接 copilot)。
→ 改架構:唔再逐份上載 PDF,改為寫精準抽取 prompt 俾 IMA agent 讀,回結構化數據入 slot。
**細節/4 條 prompt/驗證清單/workflow 全檔:`docs/2026-07-09_ima_extraction_prompts.md`。**
兩硬原則:①強制原文引句+報告名+日期(防 RAG drift/老作)②強制「未找到」禁估算。
IMA 池經濟學改變咗「只留 1-2 份」邏輯(邊際查詢成本近零)→ 約束由「揀邊份收集」變「問邊條精準問題」。
先人手驗 2-3 轮再接 GitHub 自動化。IMA = 研報層,唔取代 transcript 一手管道。

## 4. 唔好犯(用戶已點名)

- 唔好用 analyst 目標價做錨(Tier-2 順週期意見,pro-cyclical)
- 唔好用主觀浪型(主升浪/回撤浪 = 敘事 TA,無 backtested edge;驗證版係機械 momentum,且選股 IC≈0)
- 唔好用 trailing PE 評週期/pre-profit 名(倒轉陷阱)
- 唔好把 secular-growth(NVDA 型)/turnaround(INTC 型)/meme 同 cyclical-supercycle 混做一類
- **唔好將中國本地/國企關聯名嘅「供給紀律回歸」當同西方案例庫同等可信**(2026-07-11 用戶確認,
  Chancellor Capital Returns ch.6 蒸餾)——債務豁免機制令產能退出訊號失效,IPO窗口/carve-out/
  政府定價干預可以模擬假嘅kill-feature反轉。範圍:淨係China本地/國企關聯名,唔係「有中國業務
  依賴」嘅西方公司(後者正常用)。詳見 `thesis/themes.yaml` header comment。
