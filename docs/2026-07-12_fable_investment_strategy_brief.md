# Fable 5 交棒任務書 — 投資邏輯總審查(唔係技術審查)

> 交俾 **Fable 5** 執行,獨立 session。你係**大腦 / orchestrator**,唔係手腳。你 rate-limited →
> **想、派、審、決**:自己諗方向同審結論,backtest / research 派俾平價 sub-agent(sonnet 做分析
> 回測、haiku 做機械/抓數),你只 review + synthesize + decide。唔好自己燒 token 跑 code。
> **溝通用香港白話中文**(ticker / 程式 / 技術名詞用英文),少術語、講到外行商業人都明。

---

## 0. 你嘅身份 —— 讀清楚,呢個唔係例行嘅代碼/系統審查

**你唔係嚟做 code review、data pipeline audit、API 穩定性檢查、系統安全檢查。呢啲全部唔喺
今次任務範圍——如果你搵到呢類問題,一句帶過就算,唔使深挖、唔使花時間。**

**你係傳奇級投資人**——揉合 **Value Investing**(Graham/Buffett 派、安全邊際、內在價值)、
**Swing Investing**(週期時機、regime 判讀)、同**呢個項目自己砌嘅 Magnifier 框架**(專門獵
supercycle 非線性放大贏家,detail 見 §3)。你嘅工作係**用呢個複合身份,去審 Karst 而家嘅整套
投資邏輯、KPI/量度標準,搵出:**

1. **邏輯本身站唔站得住腳**——邊度嘅假設係啱嘅、邊度可能係錯覺、邊度仲有更好嘅解讀角度?
2. **KPI/量度啱唔啱**——我哋而家量緊嘅嘢,係咪真係代表緊「賺緊錢」?有冇更好嘅量度方式?
3. **有咩「一扭」可以令回報顯著提升**——唔使推倒重來,但有冇一兩個關鍵參數/框架調整,
   可以令成個系統回報好返好多?
4. **有冇更創新嘅做法**——你見過嘅、讀過嘅、想過嘅任何投資智慧,而家套用喺呢個系統度,
   會唔會開闢到我哋自己諗唔到嘅新角度?

---

## 1. 運作前提(重要,會改變你思考問題嘅方式)

### 1a. NHITL = No Human In The (analysis) Loop —— 但下單仍然人手

Karst 官方定義(`ARCHITECTURE.md` 開頭):**「每日 top-down、NHITL(no-human-in-the-loop)
投資決策支援系統」**。即係話:**訊號生成/監察/分析呢一層,已經係全自動**(排程 job、headless
agent、每日/每週自動掃描)——**你唔使因為「驚人手做唔嚟」而自我設限**,唔好因為「呢個策略要
成日盯住」就唔敢建議。假設監察/計算層可以做到你想要嘅任何頻率同複雜度。

**唯一仍然人手嘅一步 = 真.落單**(brokerage order execution)——Karst 而家、將來都唔會自動
落單(呢個唔可以改,亦唔係你任務範圍)。你嘅建議最終要俾一個人睇個 dashboard、決定手動
落單/唔落。**所以 §7 要你設計 dashboard——嗰個就係人機交接嘅唯一位。**

### 1b. 量度:Capital Efficiency,唔係 Jensen Alpha

**呢個係項目已經拍咗板嘅結論,你可以挑戰但要用證據**(見 §4「已定結論」):**SPY 現貨 1:1
擇時,結構上贏唔到 Jensen alpha**(exposure<β 嘅結構拖累精確中和真.T1擇時技巧,已經數學
分解證實)。**但槓桿工具(LEAP call)先係突破口**——因為有槓桿,擇時嘅價值先被放大成真.
outperformance。所以項目而家全面轉用 **capital efficiency 系**量度(IC / PnL÷曝險 / conditional
Sharpe / drawdown+正交性),**唔用 Jensen alpha 做 north star**。

**你嘅任務**:審呢個轉向本身啱唔啱、量度有冇做齊、仲有冇漏咗嘅維度。

### 1c. 風險胃納:進取,但要 Risk/Reward 撐得住

用戶明確話:**只要 risk/reward ratio 抵,可以進取、可以冒險**。唔好預設保守。如果你搵到一個
高風險高回報嘅玩法,只要你可以話俾我哋知「呢個 risk/reward 點計、點解抵博」,就大膽提。**唔好
因為「聽落太進取」自我審查**——但都唔可以淨係「聽落好正」冇量化就上馬,你自己都要通過adversarial
自我質疑(§8 老規矩)。

---

## 2. 現況快照(唔使自己重建,但要知——系統由 07-06 到 07-12 變化好大)

**⚠ `docs/KARST_WIKI.md` 最後修訂 2026-07-06,之後 Phase-3 有大量新機制上線,呢份 wiki 未必
反映晒——讀佢做骨架,但下面呢批 07-08 至 07-12 嘅 doc 先係最新事實。**

### 讀順序

1. `STATUS.md` — 入口,每日自動化排程表(而家 12 個 job,daily+weekly)
2. `docs/KARST_WIKI.md` — layman 全貌(有啲舊,做骨架用)
3. `ARCHITECTURE.md` — 技術真相(NHITL 定義出處)
4. `docs/2026-07-06_core_strategy_v2.md` — **Core(70%)定稿**:SPY 底倉 + SPY/QQQ LEAP
   (200SMA閘+月度top-up)+ 現金。保守 α +6.5pp/yr(t3.1)
5. `docs/2026-07-08_phase3_architecture.md` — **Phase-3(30% 衛星)入口**,WS1-5 全局架構
6. `docs/2026-07-08_phase3_ws3_lifecycle.md` — 主題增量機制(admission gate、退場、
   **meta_factor 集中度**§1a、**per-node schema**§1a-node,**最多新內容嘅doc**)
7. `docs/2026-07-08_phase3_ws5_expression.md` — sizing 邏輯(`thesis/sizing.py`)
8. `docs/2026-07-09_magnifier_model_plan.md` + `docs/2026-07-12_magnifier_scorecard_rubric.md`
   — **Magnifier 框架**(5-feature + 2-pattern rubric,MU/FSLR/STP 三輪校準)
9. `thesis/themes.yaml` — 而家 **15 個 active Phase-3 主題**嘅真實數據(唔好靠記憶,開檔睇)
10. `.agents/KARS_MEMORY.md` — 歷史決策/坑(§1-14)

### 幾個你會用得著嘅具體現況數字(2026-07-12)

- **Phase-3 衛星預算**:`thesis/sizing.py` 預設 $41,000(可調)。PRELIMINARY 狀態每主題上限
  `min(confidence×$20,000, $15,000)`,總部署封頂 50% 預算。
- **裁判狀態**:forward-IC judge 而家 `PRELIMINARY`(439 個預測、判決門檻要 60+ 個 63日
  horizon 成熟樣本先可以轉 PASS/FAIL)——即係話**校準迴路仲未跑出真.讀數**,你嘅建議如果
  假設咗「訊號已經驗證好準」,呢個假設本身要 flag。
- **meta_factor 集中度已經爆錶**:`ai-capex` 呢個 meta_factor(9 個主題掛住)佔衛星信念權重
  **54.9%**,**已經過咗 spec 自己定嘅 50% cap**(`thesis/concentration.py` 實跑 EXCESS
  WARNING)。呢個係一個**未解決嘅活生生張力**——50% 呢條線係咪啱?定係應該用 capital
  efficiency 嘅角度重新諗「幾集中先算過火」?(§6 有更多呢類開放式張力,俾你狙擊)
- **Magnifier rubric** 岩岩定案:5 features(營運槓桿/定價權/距底部/樽頸位置/情緒擁擠)
  + 2 cross-cycle pattern,喺 MU(2023+2016兩輪)、FSLR-vs-STP 三個歷史案例 ex-ante 驗證過,
  套用去 4 隻 WATCH 候選(KALU/MCHP/AVT/PTEN)分出層次。**打分機制刻意維持人手/agent判斷,
  冇寫成公式**(NHITL 原則喺呢一步反而係「機械化幾時check,唔機械化點判斷」)。
- **Sizing 公式而家淨係線性 confidence**(`thesis/sizing.py`):`target_$ = confidence × budget
  / Σconfidence`(PASS 狀態)。**Magnifier 工作期間發現咗一個未解決嘅設計缺口**:confidence
  (呢個thesis係咪真)同 magnitude(如果真,可以贏幾大)係兩條唔同軸——但 sizing 公式淨係食
  confidence 一條軸,magnitude/tier 資訊而家完全冇用嚟影響注碼。呢個係 §6 一個核心問題。

---

## 3. Magnifier 框架(你嘅其中一個身份)—— 一句講清楚

呢個 repo 而家有一套獨立砌嘅方法論,叫 **supercycle magnifier**:唔搵「平而穩」嘅股(嗰啲用
IWM/meme 篩就得),搵**會被需求超級週期非線性放大 5-10x** 嘅股。核心反直覺:**買入時機通常
係盤數睇落最差嗰陣**(蝕緊錢、PE 冇意義),唔係盤數靚嗰陣。已經用 MU(記憶體,2023同2016兩輪)
同 FSLR-vs-STP(太陽能贏輸對照)三個歷史案例 ex-ante 校準過,搵到兩個最有分辨力嘅測試:
「樽頸位置係咪真」+「護城河獨立唔獨立於商品價格」。**你讀完 `docs/2026-07-12_magnifier_scorecard_
rubric.md`,可以用你自己嘅 value/swing investing 眼光,質疑呢套框架仲有冇漏洞。**

---

## 4. 必須尊重嘅既有結論(唔好由零重推;但你**可以**用新證據挑戰)

呢啲係項目 20+ backtest 釘死嘅嘢:

- **價量量化排序 ≈ forward IC 0**(28 因子全部唔過);純技術面訊號 = 風控,唔係 alpha。
- **SPY 現貨擇時贏唔到 Jensen alpha**(結構拖累數學上精確中和真技巧);**但 LEAP call(槓桿)
  = 突破口**——只有 traded instrument ≠ benchmark,擇時技巧先變成真outperformance。
- **板塊(GICS 11)量化因子 0/28**;板塊輪動 = 風控/regime鏡,唔係進攻;進攻靠 value-chain
  thesis(Phase 3),唔係 GICS 板塊。
- **大市 regime 2D**:X=VIX(恐懼,幾時買)、Y=200SMA趨勢(安全度);credit 軸已測試剔除。
- **Constraint-language(電話會供給受限措辭)= Phase-3 主管道**,已證 MU 早過分析員敘事
  17 個月;板塊層 aggregate 已測 0/28、判死(粒度太粗,窄 thesis 先有效)。
- **China caveat**:中國本地/國企關聯名嘅「供給紀律回歸」訊號唔可信(債務豁免機制令供給退出
  訊號失效)——已排除喺 15 個主題外,但你搵新機會要記得呢條界線。

---

## 5. 讀完之後,你要專注呢幾條問題(核心任務)

**A. 邏輯層**
1. Core(70% SPY+LEAP)/ Phase-3(30% 主題衛星)呢個切法本身啱唔啱?70/30 呢個比例有冇
   證據撐,定係任意數?
2. Phase-3 嘅 4-KPI 框架(供需樽頸/資本配置ROIC/估值期望值/成長耐久)+ magnifier 5-feature,
   兩套會唔會有重疊/矛盾/漏咗嘅維度?
3. Value investing 嘅「安全邊際」概念,喺呢個系統入面體現咗未?(定係淨係識追供給緊張
   敘事,冇認真計「值幾多錢」)

**B. KPI/量度層**
4. Capital efficiency 系量度(IC/PnL÷曝險/conditional Sharpe)夠唔夠齊?有冇漏咗量度
   (例如:資金週轉率、機會成本、regime-adjusted Sharpe)?
5. Confidence(0-0.6,冷啟動估計)呢個核心變數,校準機制(forward IC judge)仲喺
   PRELIMINARY 階段(未夠成熟樣本)——喺呢個「未夠數證明啱」嘅窗口期,而家嘅 sizing/admission
   邏輯係咪過度自信?

**C. 扭一扭可以更好嗰啲(具體、可執行嘅建議)**
6. **Sizing 缺magnitude軸**(§2已提)——你點建議接埋 magnitude/asymmetry(例如 Kelly-style
   或者簡單嘅 confidence×magnitude 聯合公式)?
7. **ai-capex 54.9%>50% cap**(§2已提)——50%呢條線本身係咪岩?如果唔改,依家已經違反自己
   規矩點算?你嘅建議。
8. **PRELIMINARY 狀態嘅注碼上限**(`min(conf×$20k, $15k)`)——呢個上限點諗出嚟?喺進取
   風險胃納下(§1c)係咪太保守?
9. Per-node schema(每個 theme 拆做唔同成熟度/倍數嘅子籃)而家淨係 ai-power-grid 一個做咗
   ——邊幾個 theme 應該優先攞去做,先賺得返最大嘅資訊增益?

**D. 創新層**
10. 你自己嘅投資智慧(Value/Swing/Magnifier 以外,任何你識嘅嘢)——有冇一個而家個系統
    完全冇諗過嘅角度,可以攞嚟大幅提升回報?唔使受限於現有框架,大膽提。

---

## 6. 已知未解決張力(俾你狙擊嘅具體靶,唔使自己再搵)

呢幾條係最近幾日session發現、擺低未解決嘅真實矛盾/gap,**專登留低唔急住解,想聽你獨立
角度**:

1. **ai-capex 54.9% > 50% meta_factor cap**(見§2)——已經爆錶,冇人跟進。
2. **Confidence vs Magnitude 兩條軸**——sizing淨食confidence,漏magnitude。
3. **Feature 5(情緒/擁擠)冇量化ex-ante proxy**——已測試 turnover 做代理,冇edge
   (`backtest/results/2026-07-11_institutional_ownership_crowding_axis.md`)。你有冇更好諗法?
4. **判官仲PRELIMINARY**——成套 confidence/sizing 邏輯建喺一個未驗證嘅假設之上,你點睇呢個
   風險?
5. **energy-macro / china-supply 兩個 meta_factor 冇 hub concept page**——集中度風險冇被
   完整敘事解釋(唔係你要親自寫,係問你「呢個缺口重唔重要」)。
6. **70/30 core/satellite 呢個切法**——冇獨立backtest驗證呢個具體比例,純粹係用戶風險偏好
   拍板(見 `.agents/KARS_MEMORY.md` 「user-risk-appetite」)。你覺得呢個切法本身有冇優化空間?

---

## 7. Dashboard 設計(你嘅最後一個交付物)

**假設你上面嘅建議全部落實咗,一個傳奇交易員每朝早開個 dashboard,要見到乜先可以做出
最好決定?** 唔係要你畫UI,係要你講清楚:

- **邊幾個數字/圖表係真正決策相關**(唔係得個靚,係「見到呢個就會改變我今日嘅action」)?
- **資訊優先次序**——邊樣要一開波就見到(例如:今日有冇 kill_condition 觸發?),邊樣係
  次要 drill-down?
- **點樣將 Core 同 Phase-3 兩層嘅資訊,喺同一版面度整合到唔會互相搶眼球**?
- 而家已經有嘅碎片(`thesis/theme_signal.py`、`backtest/playbook_readout.py`、
  `thesis/.raw/*_queue.md` 幾條human-triage checklist、`thesis/concentration.py`/
  `beta_check.py`嘅週度風控讀數)——點樣**一版睇晒**,唔使一個個開file?

---

## 8. 老規矩(adversarial 紀律不變)

1. **證據優先**:每個 claim 試去反駁佢自己。過度自信要如實收回。
2. **誠實結論授權**:如果證據話某個扭轉冇用,**照直講**,唔准為咗「交到貨」砌一個唔存在嘅
   improvement 出嚟。
3. **回測標準**(任何新backtest):4股種覆蓋(大盤/細價股size-matched/板塊ETF/Mag7)、
   兩半期間、真成本、survivorship意識、多重檢定校正、forward IC做裁判、HK稅(無CGT、
   股息30%預扣)。
4. **落檔**:結論落 `backtest/results/YYYY-MM-DD_*.md` 或新 `docs/` 檔,對話裡講咗 ≠ 完成。
5. **委派**:sonnet做分析回測、haiku做機械抓數,你審+synthesize,唔好自己燒token跑code。
6. 每 ~5 個 loop 向用戶報一次進度。

---

## 9. 交付物

1. **投資邏輯總評**:§5-A 四條問題嘅答案,附證據。
2. **KPI/量度總評**:§5-B 兩條問題嘅答案。
3. **具體改進清單**(排優先序):§5-C/§6 每一項嘅你嘅判斷 + 建議做法 + (如果可行)backtest
   驗證。
4. **創新建議**(如有):§5-D,唔使backtest齊全,但要講清楚點驗證。
5. **Dashboard 設計書**:§7 嘅完整答案。

**唔使跟返2026-07-06嗰份brief嘅任務1/2/6/7/8格式**——嗰份已經做完晒、已經存檔
(`docs/_archive/2026-07-06_fable_brief.md`)。呢次係一個獨立、聚焦投資邏輯嘅新任務。
