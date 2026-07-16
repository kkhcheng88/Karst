---
slug: mag7-hyperscaler
type: B
cycle_stage: late
confidence: 0.30
verdict: real-capex-cycle-but-earnings-compounding-unproven-monitor-only
updated: 2026-07-16
tickers: [MSFT, GOOGL, AMZN, META]
---

<!-- frontmatter = valid-YAML scalars only。wiki-links 放 body 內、逐條 cite。
     frontmatter 內絕不放 [[ ]](破 parser)。 -->

# Mag7 / Hyperscaler(B 型)— core-monitor:為 tier-1 核心裝 AI-capex 週期早警,唔係衛星進攻

> 綜合頁。★ **ROLE = core-monitor(用戶已定案定位)**。Karst tier-1 核心 = SPY 底倉 + QQQ/SPY LEAP
> (core strategy v2),而 [[QQQ]] ~半係 Mag7 —— 呢個 theme **唔係叫你另開衛星倉買 Mag7 攻擊**,而係
> 為呢個既有核心裝一個 **AI-capex 週期監察鏡**:hyperscaler(MSFT/GOOGL/AMZN/META)嘅 capex 能唔能夠
> 兌現為盈利複合(AI 收入歸屬、cloud 增長、capex ROI)。confidence 轉壞 = 對 tier-1 QQQ sleeve 嘅減
> 曝險/收 LEAP 早警。載具 ETF-only(MAGS/QQQ);個股只做監察指標,唔做買入對象。INITIAL/uncalibrated。

## 一句話(核心張力 = thesis 本身)
「AI capex 一定兌現為盈利複合」係**共識敘事**,但**未被財報清晰證實**:四大 hyperscaler 一年燒
$4,000 億+ capex(折舊 3-6 年)去買 AI 產能,而可歸屬嘅 AI 收入仍只係 capex 嘅一小截。承重問題唔係
「需求真唔真」(真),而係 **「capex → 盈利複合」呢條腿幾時、能唔能兌現**——AI 收入兌現、cloud 增長
耐久、capex ROI,呢三樣就係 kill 軸本身。**因為 Mag7 = 資訊最充分定價、覆蓋最密嘅名,佢做「進攻
edge」唔得**(見下 §與 2026-07-14 not-admit 紀錄嘅關係),**但做「核心風險早警」啱**——監察軸落喺
forward 兌現訊號(capex guidance / cloud 增速 / RPO cash-backing / AI run-rate),唔係買平嘅估值 edge。

## 與 2026-07-14 not-admit 紀錄嘅關係(唔係推翻,係唔同角色)
themes.yaml 尾部有一條 2026-07-14 紀錄:評估 AAPL / Mag7 做 **Type-B 進攻供應鏈籃** → 不 admit(理由:
單一 megacap、無可交易供應鏈籃、megacap 屬 demand-anchor 慣例排除、最高覆蓋度 = 純 crowding 訊號,唔係
information-not-in-price 嘅早期 edge)。**本 theme 唔係推翻嗰個判斷——嗰個判斷成立**:Mag7 做「買平搏
超額」嘅衛星攻擊確實唔得。本 theme 係一個**結構上唔同嘅角色**:唔係「買 Mag7 攻擊」,而係「為既有
tier-1 核心裝 AI-capex 週期監察鏡」。正因為 megacap 最擁擠 + 已 priced,佢當進攻 edge 唔得(07-14
成立),但當核心早警啱(監察 forward 兌現訊號)。載具 ETF-only、magnitude<2x、crowding 照食,全部
反映呢個「監察唔進攻」定位。

## 實證地基(2026-07-16 三個實驗——釘死本 theme 係 monitor 唔係 alpha)
內部一手量化分析(single 獨立證據鏈,Tier-1),三個實驗一致指向「呢啲估值/板塊訊號唔係可接入
sizing 嘅 alpha,只可做 monitor 參考」:
- **`exp_mag7_valuation_throttle`**(backtest/results/2026-07-16_mag7_valuation_throttle.md):QQQ 估值
  月度 timing(節流/加速)**無增量**(門檻喺 2016+ 幾乎從未觸發);S&P100 全宇宙「巨頭平咗買」3y 命中率
  **49%(擲毫子)/ median excess −0.34%** = 打和;Mag7 六隻 54% / +3.14% 嘅表面優勢**主要係事後贏家
  survivorship**(+5pp 唔夠推翻全宇宙打和,同 La Porta 1996 戰術估值 timing 文獻一致)→ 估值 timing
  **唔夠格接入 sizing**。
- **`exp_sector_flow_claims`**(2026-07-16_sector_flow_claims.md):半導體 vs 軟件/大科技輪動**長期規律
  好弱**(平均接近零),現時負相關讀數主要係最近一個月嘅短期現象;XLF「業績週修復」規律(110 季)
  **不成立**。
- **`exp_residual_seesaw`**(2026-07-16_residual_seesaw.md):硬件 vs 軟件「殘差蹺蹺板」**完全喺記帳恆等式
  (兩者同屬 QQQ 成份)可解釋範圍之內、甚至比純算術更溫和** → 唔支持當獨立資金輪動訊號;真蹺蹺板證據
  反而喺能源 vs 科技(XLE-XLK)。

→ 三者一致:呢批訊號**唔係 alpha**。呢個實證正正**印證 core-monitor 定位**——本 theme 唔係搵 Mag7
alpha,而係監察 hyperscaler capex 週期會唔會轉壞,替既有 QQQ 核心裝早警。

## 監察指標(tickers,唔係買入對象)
| ticker | hyperscaler 角色 | 監察軸 | 表達 |
|---|---|---|---|
| [[MSFT]] | Azure + M365 Copilot;AI run-rate 披露最透明 | commercial RPO cash-backing、AI run-rate YoY、Azure 增速 | 監察指標 |
| [[GOOGL]] | GCP + 搜尋/廣告;antitrust 尾部 | GCP 增速、capex guidance、廣告 vs AI 蠶食 | 監察指標 |
| [[AMZN]] | AWS(雲龍頭)+ 零售 | AWS 增速(cloud 引擎)、capex guidance | 監察指標 |
| [[META]] | 無對外雲,但 AI capex 最激進、FCF 願轉負 | AI 對廣告改善可歸屬證據、capex guidance | 監察指標 |
| NVDA / AAPL / TSLA | —— | —— | **唔入**:NVDA=供應側(慣例排除,見 [[ai-power-grid]] note);AAPL=非 hyperscaler(2026-07-14 not-admit);TSLA=非 hyperscaler |

可交易表達 = **MAGS**(Roundhill 等權七大,ETF-only 主表達)+ **QQQ**(tier-1 核心本體,本 theme 為佢裝早警)。

## 4-KPI(每條 cited;§4a rubric 錨點,core-monitor 定位)

### 1. moat / bottleneck — 中(1/2)
- Mag7 hyperscaler 有**真.franchise 護城河**:cloud 寡頭(AWS/Azure/GCP 合共市佔 ~6 成)、廣告雙寡頭
  ([[GOOGL]]/[[META]])——但**呢個唔係供給樽頸 thesis**:hyperscaler 係 AI capex 嘅**需求側**(佢哋係
  掃貨嗰個),唔係持有咽喉嗰個。真正咽喉喺上游(HBM/InP/封裝/電力,見 [[memory-supercycle]]/
  [[photonics-optical]]/[[advanced-packaging]]/[[ai-power-grid]])。
- 承重「capex → 租金複合」腿嘅護城河(AI 產能能唔能轉成耐久定價權)**未證** → 依 §4a rubric「樽頸真但
  護城河被非核心/未證段稀釋」= **1/2**(且 moat=2 需承重 claim 經 red-team 生還,本腿係 red-team 判「未證」,
  故封頂 <1.5)。

### 2. 資本配置 / ROIC — 中(1/2)
- **教科書「混合」**:核心 cloud/廣告 ROIC 極高(現金牛),但 AI capex 放量($4,000 億+/年合計,折舊
  3-6 年)**回報未證**;伺服器折舊年限爭議(過去延長年限美化盈利,一旦 GPU 加速淘汰而縮短年限 → D&A
  追上侵蝕盈利)。呢個正正係 DESIGN §4 KPI 2 點名嘅「Mag7 CAPEX 恐慌 / 軍備競賽」例。
- 依 §4a rubric「核心 ROIC 好但被燒錢業務拖累;capex 放量但回報未證」= **1/2**。(具體 capex/RPO 數字見
  kill_metrics + kill_condition;current 讀數逐條落 themes.yaml kill_metrics 欄。)

### 3. 估值 / priced-in — 中(1/2)
- `exp_mag7_valuation_throttle`(2026-07-16,Tier-1 內部):QQQ 估值代理喺 2016+ 生效期 trailing-PE
  分位範圍 10.7–75.9%,**現值中段、非 ≥90 極端亦非 <50 便宜**;個股層 Mag7 混合([[MSFT]]/NVDA 抬高,
  [[GOOGL]]/[[META]] 近期曾入自身歷史低分位 episode,見實驗 Part 2)。
- 依 §4a rubric「pe_pctile 50–90」= **1/2**(非夢想定價、亦非便宜 tilt)。

### 4. 成長耐久 / TAM — 中(1/2)
- **Cloud 係真.耐久 secular**(算力長期外移已兌現);但 **AI 收入兌現(additive 機制)係未證嘅下一階段**
  ——[[MSFT]] AI run-rate、[[META]] AI 對廣告改善嘅**可歸屬性**仍未喺財報清晰現形(呢個正正係 kill 軸)。
- 依 §4a rubric「機制真但兌現中 / 部分靠未證嘅下一階段」= **1/2**(AI 收入未清晰交付 → 唔可以 2/2)。

## cycle_stage = LATE
| 訊號 | 現況 |
|---|---|
| 估值 🟡 | QQQ 代理中段(10.7–75.9% 生效期範圍)、個股混合;非極端但抬高 |
| 擁擠(敘事)🔴 | Mag7 = 公認最擁擠交易(narrative);但**機械 crowding proxy 讀低**,見下推導 ⚠ |
| ROI 兌現 🟡 | capex 仍放量、AI 收入未清晰兌現 → 承重腿未證,週期「late-但-未 topping」|
| meta_factor | `ai-capex`(同 [[ai-power-grid]]/[[photonics-optical]]/[[advanced-packaging]] 同源;見 [[ai-capex-macro-risk]] hub)|

## confidence 推導(可追溯)
```
KPI: moat 1/2(franchise 真但非供給咽喉、承重 capex→租金腿未證 red-team)
     · capital 1/2(核心 ROIC 高但 AI capex 放量回報未證、D&A 週期風險 = 軍備競賽例)
     · valuation 1/2(QQQ 代理中段 10.7–75.9% 生效期、個股混合;50–90 帶,exp_mag7_valuation_throttle)
     · growth 1/2(cloud secular 真但 AI 收入兌現係未證下一階段 = kill 軸本身)
     = 4.0/8 = 0.5 base
penalty(DESIGN §4a 表:crowding 23.9 → <40 帶 × late)                     × 0.75  → raw 0.375
single_source cap 0.30:**適用、綁住**(n_sources=1;內部實驗係謹慎/證偽性質,支持 monitor 定位,
     唔算獨立 Tier-1 擊中「承重 bull claim」→ 依 §4a 定義唔脫 cap;§4c 分岔通道 2)
uncalibrated cap 0.40:亦適用但唔係最緊(STATUS.md:256;forward_ic matured=0)
→ confidence = min(0.375, 0.30, 0.40) = **0.30**  (INITIAL, uncalibrated;binding = single_source)
```
**⚠ 機械 crowding 23.9(低)嘅誠實處理(唔夾數)**:crowding_composite.py 對 mag7-hyperscaler 讀
composite **23.9**(attendance 22.9 + bull_ratio 25.0(1/4))= <40「冷」帶。**呢個同「Mag7 = 最擁擠交易」
嘅敘事矛盾,原因係 attendance proxy 用嘅係 own-history 百分位**——MSFT/GOOGL/AMZN/META **永遠滿覆蓋**,
所以「相對自己歷史異常高」讀唔到極端(proxy 對永遠最高覆蓋 mega-cap 有已知盲點,量嘅係「新增擁擠」唔係
「絕對擁擠」);bull_ratio 1/4 亦因為 gooptions 語料偏 photonics/power、Mag7-primary 報告得 4 篇(薄)。
**處理原則(§4c):confidence 數字 = 公式輸出,唔准為咗「令 penalty 咬」而酌情上調 crowding**(酌情正正
係 P2/§4c 要消滅嘅嘢)。真正結果:**single_source cap 0.30 先係綁緊嗰個,唔係 crowding penalty**——即使
crowding 讀低令 penalty 溫和(0.75),raw 0.375 照樣被 single-source cap 壓返 0.30。qualitative「Mag7 擠」
嘅現實記喺下面 red_team narrative-risk,**唔 fabricate 入 crowding 數字**。

**讀法:真 capex 週期(需求真)但「兌現為盈利複合」承重腿未證 + 單一內部證據鏈 → 0.30 single-source
floor。方向 = 唔當進攻;做 core-monitor,confidence 轉壞先係對 tier-1 QQQ 核心嘅早警。**

## kill_condition(可證偽)— 本 theme 主要交付物
> **任一觸發 → confidence 歸零 + 向 tier-1 core 發「AI-capex 週期轉壞」早期減曝險訊號**(數值/日期閾值
> + 出處逐條落 themes.yaml `kill_metrics` 欄):
> 1. 四大 hyperscaler 合計 **capex guidance YoY 轉負**(capex 週期見頂、軍備競賽退潮);
> 2. 三大雲(Azure/AWS/GCP)任一 **YoY 增速失速跌穿 15%**(cloud 增長引擎熄火);
> 3. **cash-backed backlog 刀法** —— [[MSFT]] commercial RPO 增長停滯,或 RPO 當中已收現金(current
>    deferred revenue)佔比持續萎縮(宣稱 AI backlog 唔係真金白銀坐喺表上,[[memory-supercycle]] RPO
>    中彈嘅鏡像;對照 [[ai-power-grid]] GEV 現金預付 = cash-backed 補強嗰邊);
> 4. **AI 收入兌現失速**:[[MSFT]] AI run-rate YoY 增速大幅減速,或 [[META]] AI 對廣告改善嘅可歸屬證據轉弱;
> 5. **半導體→軟件資金流結構性逆轉**(SOXX/SMH 相對 IGV 由領先轉持續落後 = capex-beneficiary 見頂,
>    2026-07-16 residual_seesaw/sector_flow 建立嘅追蹤軸)。

## red_team(Level-2,2026-07-16;§4b 四式;§4c 判決 = 分岔 → 通道 3)
本 theme 天然攻擊面(mandate 點名):capex 無限膨脹但 ROI 未證、depreciation 週期縮短侵蝕盈利、circular
revenue(互相投資對方當收入)、監管/反壟斷。逐式:

- **(a) 反面事實狩獵(omitted-fact hunt)**:①**折舊週期反轉**——hyperscaler 過去幾年**延長**伺服器折舊
  年限(美化 EPS);AI GPU 加速淘汰(每 1-2 代)令「延長」假設變脆,一旦被迫**縮短**年限,D&A 追上、
  報告盈利壓縮,即使收入企穩。②**circular revenue**——NVDA↔OpenAI/CoreWeave、MSFT↔OpenAI、Oracle↔OpenAI
  等互相投資 + 承購,部分「AI 需求」係生態圈內部循環資金,capex 兌現度被高估嘅風險。③**監管/反壟斷**——
  [[GOOGL]] 搜尋反壟斷 remedy、[[META]] FTC、AI 監管,係盈利複合嘅尾部風險。
- **(b) Steelman 反方(非文章自供,獨立)**:**「AI capex = 經典 capex 超級週期,必然過度建設 → ROIC 崩」**
  ——電信 2000「暗光纖」類比:一年 $4,000 億+ 買 3-6 年折舊資產,而可歸屬 AI 收入仍係 capex 一小截;
  當 **capex/D&A 比率反轉**(D&A 追上),即使收入企穩,報告盈利都會硬壓縮。事實錨:capex 絕對量 vs
  當前 AI 收入級距 + 折舊年限。**呢個係最重一擊**——佢直接打「capex 兌現為盈利複合」呢條**承重腿**,
  而且有硬數據錨(capex/D&A/AI-run-rate),唔係純敘事風險。
- **(c) 平庸解釋測試**:「Mag7 一定持續複合」呢個觀感,可唔可以用悶故事解釋?**可以,而且已被 2026-07-16
  實驗證實**——全宇宙 S&P100「巨頭平咗買」3y 命中率 49%(擲毫子),Mag7 嘅 +5pp 主要係**事後贏家
  survivorship + mega-cap 動能**,唔係「巨頭必複合」嘅規律。**平庸解釋通過** → thesis **唔可以宣稱 alpha**,
  只可以宣稱 monitor 價值(呢個正正係 core-monitor 定位嘅由來,唔係事後補鑊)。
- **(d) 當下 kill 距離**:ingest 時 capex 仍放量、cloud 仍增長、RPO 仍增長 → **未近 kill**;但估值/擁擠
  敘事抬高,**最薄嗰條腿 = AI 收入兌現(kill 軸 3+4)**。逐條數值距離見 `python thesis/kill_metrics.py --report`。

**判決 = 分岔(fork,§4c)**:已-priced / 市場已知嗰部分(Mag7 franchise 強、cloud 增長真)**證實**;但
thesis 真正押注嘅**承重「capex→盈利複合」magnitude 腿未證**(AI 收入兌現未喺財報清晰現形)。三通道應用:
- **通道 1(subscore)**:未證腿已反映喺 moat 1 / growth 1(保守,唔為交貨砌額外 downgrade,亦唔為敘事
  砌額外加分——§4b 校準紀律)。
- **通道 2(cap 資格,binary)**:**唔脫 single-source cap**——內部實驗證實嘅係「megacap 跑贏 = survivorship」
  (周邊 / 已-priced),**唔係**獨立 Tier-1 擊中「capex 兌現複合」呢條承重 bull claim → 依 §4a 定義,
  分岔情況唔脫 cap,confidence 受 single-source cap 綁 0.30。
- **通道 3(magnitude,sizing 層)**:未證 magnitude 腿 → node `hyperscaler-capex-earnings-compounding`
  標 `magnitude_unconfirmed: true`,sizing v2 damp 到 2.0x 中性。但本 node magnitude_tier 已係 **2x**
  (core-monitor、無 uplift,用戶指定 <2x)→ **damp 唔 bind(damped=0)**,同 [[specialty-siding-pricing-power]]
  一致(flag 咗但 tier 本身 2x,冇 uplift 可收,唔假報)。**呢個先係 red-team 殺傷力落腳點**:唔喺
  confidence 數字(公式定 0.30),而喺「搏 capex 複合嗰部分未證 → 唔俾佢憑潛在倍數加碼」——而本 theme
  本來就係 monitor、冇 magnitude uplift,所以殺傷力已內建喺定位。

## Agent 追蹤(定日可證偽預測 → track_record)
- **2026-07-16**:mag7-hyperscaler = **真 AI-capex 週期,但「capex→盈利複合」承重腿未證**;定位 core-monitor
  (為 tier-1 QQQ 核心裝早警,非衛星進攻)。confidence 0.30(single-source floor)、cycle late、magnitude
  2x-unconfirmed。方向:**唔當進攻注碼**;監察 5 條 kill 軸(capex guidance / cloud 增速 / RPO cash-backing /
  AI run-rate / semis→software flow),任一轉壞 = 對 QQQ 核心嘅早期減曝險訊號。
- forward-IC 評估器 N 天後回填 → 呢條預測嘅 forward IC 先係「有冇 edge」嘅裁判(matured=0,現 uncalibrated)。

## 待補(降「未確認」扣分)
- [ ] kill_metrics current 讀數逐條核實 + 落 themes.yaml(capex guidance YoY / 三雲增速 / MSFT RPO +
      current deferred revenue 佔比 / MSFT AI run-rate / META AI-ad 歸屬)。
- [ ] 接前瞻追蹤:hyperscaler 逐季 capex guidance + cloud 增速 + RPO 自動更新 cycle/confidence。
- [ ] 抽 [[MSFT]]/[[GOOGL]]/[[AMZN]]/[[META]] transcript 管理層「AI 收入 / capex 紀律 / 折舊年限」語言。

## 來源
Tier-1(內部一手量化):`exp_mag7_valuation_throttle` / `exp_sector_flow_claims` / `exp_residual_seesaw`
(全部 2026-07-16,backtest/results/)—— 單一獨立證據鏈(謹慎/證偽性質,支持 monitor 定位,唔脫
single-source cap)。crowding:thesis/.raw/crowding_composite.json(2026-07-16 重算,composite 23.9)。
kill_metrics current 讀數:見 themes.yaml `kill_metrics` 欄(逐條出處 + as_of)。
