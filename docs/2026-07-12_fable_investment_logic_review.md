# Karst 投資邏輯總審查【Fable 5,2026-07-12】

> **任務**:以複合投資人身份(value / swing / magnifier)審 Karst 整套投資邏輯 + KPI,唔係技術審查。
> 任務書 = `docs/2026-07-12_fable_investment_strategy_brief.md`。
> **證據鏈(本審查期間新產出,全部有 script 可重跑)**:
> `backtest/results/2026-07-12_sizing_two_axis_decision_analysis.md`(四注碼方案 Monte Carlo)
> `backtest/results/2026-07-12_capex_da_supply_response_probe.md`(供給紀律逆轉機械化探測)
> `backtest/results/2026-07-12_analyst_attendance_crowding_probe.md`(analyst 出席數擁擠 proxy)
> `backtest/results/2026-07-12_satellite_option_expression_probe.md`(衛星期權表達可行性)
> 姊妹檔:`docs/2026-07-12_dashboard_design_v3.md`(交付物 5)。

---

## 0. 一頁總評(TL;DR)

**大方向係啱嘅,而且誠實得罕見。** 20+ 回測釘死「價量無選股 alpha」、負面結果照落檔、
裁判未 PASS 注碼有鎖、kill condition 寫死——呢啲紀律喺散戶級系統入面幾乎見唔到,係真資產。
Core v2(SPY+LEAP)嘅 alpha 機制(槓桿工具先令擇時變 outperformance)邏輯企得住,唔使掂。

**但系統而家有一個核心自相矛盾:整套 Phase-3 係為「獵 5-10x 非線性放大」而設計,
而注碼數學令「中咗都唔會改變組合」。** 實跑 `sizing.py`(2026-07-12):

- 15 個主題經三重 cap 之後,總部署 $20,500;最高信念主題 memory-supercycle(conf 0.38)
  最終注碼 **$1,184**;佢入面嘅 10x 細價倉上限(≤1/3)= **~$395**。
- 更嚴重:雙重削減令**注碼排名同信念排名倒轉**——conf 第 1 嘅 memory 注碼排第 7,
  conf 並列第 4 嘅 us-solar 反而攞最大注($2,509)。個 sizing 管道喺主動反排序自己嘅信念。
- Monte Carlo 決策分析(50,000 paths,假設倍數表見結果檔):現行方案喺自己假設下
  E[PnL] ≈ **$234**(部署額嘅 1.1%);如果 confidence 集體高估 20%,直接轉負(−$1,911)。
  即係話:冷啟動組合唔係「細但正 EV」,係「細、而且可能 ≈零 EV」,因為佢照揸住 fully-priced 嗰條尾。

**三個最高 EV 嘅「一扭」**(詳 §3):
1. **Sizing 接 magnitude 軸 + 集中化**(P0):同一個 $20.5k 風險封套,由 15 注碎銀改做
   top-5 有意義注碼,E[PnL] 喺同一套假設下升一個數量級。唔使等裁判 PASS,因為裁判計分
   靠 prediction log(免費、全 15 個主題照 log),唔靠真金白銀——**分散持倉對校準迴路零貢獻**。
2. **裁判加第二把尺(milestone Brier)**(P0):63 日 IC 量緊 1-3 年 thesis,錯配;
   而且有效橫截面闊度係「主題數」唔係「ticker 數」(同主題 ticker 共用 confidence)。
3. **Crypto 治理**(P0,Phase-3 以外):61% 資產無 kill 無階梯,architecture 自己都認咗
   係 Top-1 缺陷——修佢嘅 EV 大過本檔所有 Phase-3 微調加埋。一個鐘寫得完,一直冇做。

---

## 1. 邏輯層(§5-A 四問)

### 1.1 Core(70%)/ Phase-3(30%)切法啱唔啱?70/30 有冇證據?

**切法本身:啱。** 「已證明嘅機械引擎」同「未證明嘅質性 alpha」分開管、俾後者封頂,
係正統 core-satellite,亦同 barbell 邏輯一致。冇理由推倒。

**70/30 呢個數:冇證據,而且而家係名不副實。** 三個事實:
- 佢係用戶風險偏好拍板(`.agents/KARS_MEMORY.md` user-risk-appetite),冇獨立回測——
  呢樣**唔係罪**:資產配置比例本來就係偏好參數,唔係可以「回測出嚟」嘅嘢,唔好扮可以。
- 但實際上而家根本唔係 70/30:衛星預算 $41k 對 $500k-1M 組合 = **4-8%**,再俾 PRELIMINARY
  50% cap 壓到實際部署 $20.5k = **2-4%**。真實配置係「70 core / ~4 satellite / 26 現金雜項
  + 框架外嘅 crypto(61% 總資產)」。討論 70/30 之前,個 30 根本未存在。
- Core 保守 α +6.5pp × 70% ≈ 組合級 +4.6pp/年。衛星如果最終真係去到 30% 權重,佢條 sleeve
  要做到 **+15pp/年**先可以令組合 alpha 翻倍。呢條數應該貼喺牆度:Phase-3 唔係「有就好」,
  係要交呢個數先對得住佢嘅複雜度。

**建議:將 70/30 由「靜態比例」改做「賺返嚟嘅目的地」(earn-in schedule)**——
PRELIMINARY:衛星 ≤10% 可投資資產;PASS:20%;PASS 後連續兩季 realized capital efficiency
為正:30%。咁樣 70/30 唔使假裝有回測撐,又唔會喺未驗證階段郁大錢,仲令「裁判 PASS」
呢件事有真.財務後果(而家 PASS 淨係解鎖 $41k 入面嘅另一半,誘因太細)。

### 1.2 4-KPI 同 magnifier 5-feature 有冇重疊/矛盾/漏?

**冇矛盾,有重疊,最大問題係「三隻腳得兩隻」。** 對照表:

| 4-KPI(admission) | magnifier 5F+2P(magnitude/timing) | 重疊? |
|---|---|---|
| 供需樽頸 | F4 樽頸位置 + F2 定價權 + P1 護城河獨立於商品 | 重疊(theme 級 vs 公司級,可接受)|
| 資本配置 ROIC | P2 供給紀律逆轉(反面) | 重疊 |
| 估值期望值 | F3 距底部 | **兩邊都冇工具**(見 1.3)|
| 成長耐久 | —(magnifier 天生 cycle-bound)| 唔重疊,正常 |
| — | F1 營運槓桿 | 4-KPI 完全冇呢個維度 |
| — | F5 情緒/擁擠 | 4-KPI 冇;priced-in 閘算半個 |

三個判斷:
1. **分工要寫明,唔好留喺隱含層**:4-KPI 答「收唔收編」,magnifier 答「收咗之後,邊個 node
   幾大倍數、幾時入」。而家兩套 rubric 都係人手打,同一份證據(例如「樽頸係真」)可以喺兩邊
   各計一次分——**同源證據重複計分會靜靜雞谷高 conviction**。修法:每個 theme 一頁合併
   scorecard(admission 分 + per-node magnitude 分同一頁),證據引用同一個 citation pool。
2. **漏咗嘅維度:「點解呢個 edge 會存在/邊個係對手盤」**。兩套 rubric 都冇迫你寫低
   「我點解會早過市場」。建議 admission 加一行 edge-source 分類:早期資訊(constraint
   language)/ 結構性冷落(analyst 出席數低)/ 行為偏誤(「死週期股」敘事)。一行字,
   但迫個 thesis 講清楚自己食緊邊種錢——寫唔出嚟嗰啲,多數係 beta 扮 alpha。
3. F1(營運槓桿)應該升格入 admission 參考——MU 校準證咗佢係 ex-ante 最早可讀嘅 feature
   (財報一出就有,唔使等管理層開口),但 admission 4-KPI 完全唔睇佢。

### 1.3 安全邊際體現咗未?

**體現咗一半,而且擺錯位。** 有嘅:priced-in 閘(ttm PE 分位)、solvency gate(WOLF 教訓)、
「don't chase」紀律、單源 confidence 封頂、kill 寫死、discovery 偏好平嘢(USAC 2nd pctile)。
呢啲全部係「風險意識」,唔係「安全邊際」。

冇嘅:**成個系統冇任何一度計過「呢樣嘢值幾多」。** WIKI/ARCHITECTURE 全文搵唔到
intrinsic value / expectations 框架;4-KPI 嘅「估值期望值」冇工具支撐(`thesis_valuation.py`
07-06 已列 P0 修項,一直未起);themes.yaml 用 PE 分位做晒估值判斷。PE 分位答「貴唔貴過自己
歷史」,唔答「而家個價 embed 咗咩預期」。後果好具體:aerospace-alloys / EUV 兩個 theme 以
98th percentile PE 收編(conf 0.22-0.24)——「真.結構 + fully priced」呢種嘢,upside 已經
喺價入面、downside 冇喺價入面,係**負偏態**注碼,而家靠注碼細嚟頂住,即係用倉位管理代替
估值紀律。

**修法(具體、NHITL 相容、唔係叫你轉行做 Graham 深值)**:起 `thesis_valuation.py` 極簡版
= **expectations-gap 模組**(你哋自己蒸餾咗 Mauboussin 而冇接線):每個 theme 頭兩個表達,
用 normalized mid-cycle 盈利力(magnifier F3 本來就要計)倒推「現價隱含幾多年幾快嘅增長」,
同 thesis 自己聲稱嘅供需路徑對照,出一個三值判斷:**gap 正(市場未 price)/ 中 / 負(市場
已 price 多過 thesis 講)**。Admission checklist 加一行;gap 負嘅 theme 無論 confidence 幾高,
注碼鎖 watch 級。呢個係將「安全邊際」翻譯成 supercycle 語言:唔係買平,係**買「預期落差」**。
(同 KARS_MEMORY「school mismatch」決策一致——衛星 lens 係成長/護城河,唔係深值;
expectations gap 正正係嗰個 lens 嘅估值紀律。)

### 1.4 邊啲假設係啱、邊啲可能係錯覺?

**企得住嘅**(審完唔郁):價量=風控唔係 alpha;LEAP 槓桿=core alpha 唯一結構解;
constraint-language 主管道 + 窄 thesis 粒度(板塊層兩路都判死,交叉驗證企硬);
右側入場全系統一致;China caveat;negative-result 落檔文化。

**要留神嘅錯覺風險**:
1. **「confidence」呢個字本身**——佢而家係「紀律化嘅相對強度 × 週期溫度」(themes.yaml 檔頭
   自己都咁講),唔係機率。但 sizing 公式當佢係機率咁乘錢。喺校準前,呢個字每次出現喺公式度
   都應該讀成「未經校準嘅排名分」。§2.2 詳講。
2. **確認機器**:12 個排程 job 入面,monitoring 層係「掃已收編名嘅 constraint 語言」——
   結構上係搵確認證據。Kill condition 係唯一結構化反面,但佢係事件觸發,唔係主動搜尋。
   建議季度加一個 adversarial sweep:每季對 top-3 注碼主題,派 agent 由同一個 corpus 度
   砌「最強 bear case」落 wiki(供給端自己講嘅 demand 風險、客戶端 transcript 嘅反面語言)。
   平、NHITL、直接對沖敘事累積偏誤。
3. **股價行先問題**(rubric §3b 自己發現咗,好誠實):MU 案例入面股價早過 constraint-language
   轉正 38-60%。已經修正做「F1/F3/F4 做早篩、constraint 做確認」——啱。但要提防下一步錯覺:
   「早篩」都唔等於「股價未行」;F3(距底部)本身要對照**股價**唔係淨係財務,建議 F3 打分時
   同時記「股價距 52 週/週期低位 %」,防止喺已彈 60% 嘅位置俾「財務仲殘」呃咗。

---

## 2. KPI/量度層(§5-B 兩問)

### 2.1 Capital-efficiency 系量度齊唔齊?

轉向本身**啱**(Jensen alpha 對 exposure<β 策略嘅結構拖累已數學分解證實,唔重推)。
現有:IC / PnL÷曝險 / conditional Sharpe / DD+正交性。**漏咗五樣,全部平**:

| # | 漏咗 | 點解重要 | 點做 |
|---|---|---|---|
| 1 | **Realized IRR / 資金佔用時間** | 2x-in-6mo 同 2x-in-3y 係兩單完全唔同嘅生意;multiple 睇唔到 duration | ledger 每倉記 entry/exit,報 IRR 唔淨報倍數 |
| 2 | **Idle-cash drag 明細行** | PRELIMINARY 期 50% 現金係「買紀律」嘅保費——保費幾貴要見得到 | 每季報:(部署回報 − T-bill)× 閒置額;令 earn-in 辯論有數得計 |
| 3 | **Hit-rate × slugging 分解 + top-1 貢獻佔比** | Bessembinder 邏輯:衛星 P&L 應該由 1-2 個大贏家帶——如果 P&L 係好多細贏加埋,即係你買咗 beta 唔係 magnifier | 季度分解;「集中」係健康訊號唔係病 |
| 4 | **Kill-scenario 壓力數(meta-factor VaR)** | 「ai-capex 佔幾多 %」唔係決策語言;「ai-capex kill 齊 fire 衛星蝕幾多」先係 | 用 sizing MC 同一張 downside 表計,週度出一個 $ 數 |
| 5 | **衛星 benchmark = 同額 SPY** | 衛星唔部署嘅錢有機會成本;alpha 要對「呢舊錢擺咗入 SPY」計 | ledger 平行記一條 shadow SPY leg |

### 2.2 校準未熟窗口期,sizing/admission 係咪過度自信?

**Sizing 唔係過度自信——佢係「保守得嚟揀錯咗保守嘅形狀」。** 三重 cap + conf≤0.40 紀律
+ PASS 先解鎖,呢啲全部係預先設好嘅 guardrail,誠實。真正嘅問題係:

1. **Cap 嘅形狀錯**:per-theme cap + 無限闊度 = 強迫碎片化。15 注碎銀嘅風險封套同 5 注
   有意義注碼一樣($20.5k),但前者(MC 實測)EV 貼零、暗藏反排序、連期權表達都買唔起
   (MU 一張最平 $9.1k)。**部署闊度唔應該鏡射 registry 闊度**——registry 闊係裁判嘅著數
   (橫截面愈闊校準愈快),但裁判食 prediction log,唔食倉位;15 個主題照 log,錢集中
   top-5,兩全其美。
2. **裁判自己都要俾人審**(呢個係任務書問題 4 嘅正面回答):
   - **橫截面幻覺**:週度 Spearman 用 59 個 ticker 計,但同主題 ticker 共用同一個
     confidence——有效闊度係 9-15(主題數)。IC 嘅標準誤按 √N 計,N 由 59 縮到 12,
     PASS 門檻(mean≥0.05, IR≥0.5)嘅統計含金量要打折讀。
   - **Horizon 錯配雙向風險**:63d IC 判 1-3 年 thesis——thesis 啱但 63 日內冇郁 = 假 FAIL;
     late/crowded 主題俾動能推高 63d 相對回報 = 假 PASS(最擠嗰批 theme 啱啱就係會咁)。
   - 修法唔係改 IC(佢係市場驗證,有用),係**加第二把尺**:§3 P0-2 milestone Brier。
3. **窗口期唔係免費**:校準要十個月,但 USAC(2nd pctile)/FSLR(22nd)呢類「真.平.未被
   發現」候選唔會等你十個月。而家嘅設計令系統喺自己證據最新鮮嗰陣注碼最細。Earn-in +
   集中化係喺唔加總風險下對呢個時間成本嘅回應。
4. **Admission 反而唔算過度自信**——15 個主題、conf 全部 ≤0.38、新批 6 個標明「未做深度
   研究」。唯一要執:6 個新 theme(07-11 收編)要確認已入 `log_predictions` 覆蓋
   (track_record 而家得舊 9 個主題嘅名,07-10 為止)。

---

## 3. 具體改進清單(§5-C + §6,排優先序)

> 每項:判斷 + 建議 + 驗證方式。P0 = 本月做;P1 = 裁判首讀數前(~10 月)做;P2 = 之後。

### P0-1|Sizing v2:接 magnitude 軸 + 集中化(§6-2、問題 6/8)

**判斷**:現行「linear confidence、無限闊度」係全系統而家最傷 EV 嘅單一設計。MC 四方案
(結果檔詳):D Kelly-lite E[PnL] $5,248 > C Top-5 $4,033 > B conf×mag $2,547 > A 現行 $234;
排名喺 confidence 八折情境下不變。但 C 方案暴露陷阱:magnitude 軸冇 confidence 門檻,
event-binary 主題(space/rare-earth)食咗 51.7% 部署——**magnitude 係指數差距,冇閘會輾壓一切**。

**建議規格(揉合 B/C/D 嘅贏面)**:
- score = conf × log₂(magnitude 中位);**conf < 0.25 唔食 magnitude 加成**(binary 閘)
- 只部署 top-K(K=5-7)且**每注 ≥ $4k**(否則 $0,留 watch)——$4k 係「一張平價 LEAP /
  一注有意義正股」嘅門檻
- event-binary 名維持 option/event framing:固定微注(≤$1k),唔入 score 排名
- 總部署 cap 照舊 50%(唔加風險);集中度 cut 改喺**選倉之後**先套用(修反排序 bug);
  順手修 WS5 §8 已知口徑問題(mf cap 基數用實際部署上限)
- magnitude 輸入 = per-node magnitude_tier(P2-1 推廣去其餘主題)

**驗證**:唔郁真錢住——ledger 開 shadow A/B(現行 vs v2 兩套目標倉平行記帳)兩季,
用 §2.1 嘅 capital-efficiency 量度做裁判。呢個係 self-contained、可證偽。

### P0-2|裁判加第二把尺:milestone Brier(§6-4)

**判斷**:63d IC 保留(市場驗證),但佢唔可以獨力承擔「成套 confidence 邏輯嘅可信度」。
**建議**:每個 theme wiki 加 2-4 條**具名、有期限、可判 Y/N 嘅里程碑預測**,連機率
(例:「2026Q4 前 MU LTA 簽約量唔會停滯,P=0.7」「USAC lead time 2027Q2 前唔會壓返
<52 週,P=0.75」)。夜班/週度 job 自動 check 可判項,計 Brier score。好處:
(a) horizon 同 thesis 匹配;(b) 樣本量唔靠 63d 價格窗,每季幾十個判定;(c) 直接校準
「agent 講 0.7 中唔中 70%」——D4 校準映射本來就要呢種數,而家嘅 IC 迴路俾唔到佢。
**驗證**:kill_condition 本身已經係呢種預測嘅反面版,機制現成(夜班 guard + queue),
增量工作 = wiki 加預測行 + 一個 30 行 scorer。

### P0-3|Crypto 治理(§5-A 問題 1 附帶,Phase-3 以外)

Architecture §5 Top-3 缺陷 #1 自己寫咗:紀律只管 39% 資金,ETH 一個 −30% 月 = −$62k,
遠大過 core 全年 alpha +$9k。修法佢都寫埋(recovery ladder 實數 + 下行/時間出口 + 裝錶,
一個鐘)。**本審查唯一要講嘅係優先序:呢項排喺所有 Phase-3 微調之前。** 唔做呢項而去
調衛星 sizing,係喺甲板執豆而唔理船身個窿。

### P1-1|Expectations-gap 估值模組(§5-A 1.3 詳)

`thesis_valuation.py` 極簡版;admission 加一行;gap 負 → watch 級注碼。
**驗證**:先對 15 個現有 theme 回填一次 gap 判斷,睇同 PE 分位判斷有幾多分歧——
分歧位(例:PE 平但 gap 負,或者 PE 貴但 gap 正)就係呢個模組嘅增量價值所在。

### P1-2|Feature 5 擁擠複合讀數(§6-3)

**判斷**:turnover 判死正確,唔翻案。但「維持純質性」放棄得太早——今次探測證咗
**analyst 出席數**(由自家 corpus 免費抽)方向成立:MU 谷底期出席跌到 20 年並列最低
(4 人),擁擠期 12 人;橫截面 AVGO 13.5 > NVDA 11.6 > MU 10.8 > FSLR 9.1 > WST 5.1 >
USAC 3.6,同「邊個未被發現」直覺完全一致(USAC 全場最低)。幅度溫和(底 vs 頂 +11%),
所以**做輸入唔做判官**。
**建議**:F5 改為「三輸入 + 人手判斷」:①analyst 出席數 own-history percentile(季度,
自家 corpus)②GS sector flow Z-score(週度,IMA 已收緊)③報告 bull-ratio(已有)。
Rubric 仍然人手打分——量化嘅係輸入,唔係判斷,同 §11 拍板一致。
**執行前**:修 NVDA 2025 parser 失敗(正正係最想知嘅時點)。
**驗證**:回填測試——對 15 個 theme + 4 隻 WATCH 票計三輸入複合讀數,對照 rubric 已有嘅
人手 F5 判斷(MU 2023/2016、FSLR/STP 校準點 + themes.yaml crowding notes),報一致率,
分歧個案人手裁決邊個啱;接線後每季 forward-log 複合讀數 vs 下季 theme 超額回報方向。

### P1-3|Capex/D&A 月度雷達(§5-C 新增,magnifier P2 機械化)

**判斷**:探測結果支持「機械化觸發、唔機械化判斷」:MU 兩個週期頂年度比率驚人一致
(1.679x / 1.696x),紀律谷底 0.990x,而家 TTM 2.803x——pattern 真;但 AVGO(fabless
讀數近零)/RKLB(年輕公司虛高)兩個反例證明「揀邊隻 ticker 代表 theme 嘅資本節點」
呢步機械化唔到。**唔做自動 kill trigger,做月度 watchlist**(比率/YoY 顯著上升 → 入
review queue)。
**即刻行動**:探測新發現 **MP 兩軸齊響(2.192x / 2.540x)**——rare-earth-materials 呢個
theme 嘅供給端可能開始行緊 P2 死亡劇本(頂前狂擴產),之前完全冇人標記。**排入人手覆核
queue,本週睇。** AMKR YoY 2.811x(全表最高)都值得記一筆。

### P1-4|70/30 earn-in schedule(§6-6,§1.1 詳)

PRELIMINARY ≤10% → PASS 20% → PASS+兩季正 efficiency 30%。同時 PASS 嘅財務後果
變得真實,裁判唔再係得個榮譽狀態。
**驗證**:schedule 係規則唔係預測,驗證 = 紀律審計 + 成本核算兩條:①每季覆盤有冇跳級
(升級之前對應閘門證據要齊,落 STATUS 紀錄);②idle-cash drag 明細行(§2.1 #2)令每一級
嘅「保費」有實數,兩季後用真數檢討級距係咪定得啱。

### P2-1|Per-node schema 推廣優先序(問題 9)

按「theme 內 stage/magnitude 分散度 × 部署相關性」排:
1. **photonics-optical**(9 隻:COHR/LITE 護城河 vs SIVE/LWLG 無盈利泡沫 vs GLW/FN——
   note 自己已經寫住三類人,節點結構現成)
2. **advanced-packaging**(13 隻四種動物:arms-dealer/設備/INTC event/存儲;AMKR capex
   警號令分節更逼切)
3. **memory-supercycle**(DRAM vs NAND vs HBM 純度差成個 tier;SKHY 晚期擁擠訊號 note 已記)
4. **space-satellite**(RKLB/ASTS binary vs HEI/LOAR roll-up,分散度最大,binary 名要
   option framing)
5. **oil-gas-energy 例外處理**:唔好 node 化——佢 verdict 自己都話 thin-split-watch,
   兩條腿死因唔同,**直接拆做兩個 thesis**(oil-macro watch / gas-power),node 化只會
   將一個應該拆嘅嘢焗埋一齊。
   單 ticker theme(USAC/FSLR/ASML/WST/LPX/AEHR)唔使 node。
**驗證(資訊增益驗收)**:每個新 node 化嘅 theme,必須出現 ≥2 個 tier/stage 唔同嘅 node
——如果 node 化完全部 node 同一個判斷,即係白做,回滾;sizing v2 落地後再核:node 級
magnitude 有冇真係改變注碼分配(改變唔到 = 呢個 theme 嘅 node 化冇部署價值,純記錄用)。

### P2-2|Hub page 兩個缺口(§6-5)

**重要性:中,但 china-supply 嗰個升緊級**——rare-earth-materials + us-solar(碲)+
MP capex 警號 + AXTI 生產地曝險,四條線匯聚緊同一個機制(中國出口牌照做地緣槓桿),
呢個 hub 唔係文書債,係一個成形中嘅單一賭注需要一頁紙講清楚共同觸發器。先寫佢。
energy-macro 嗰個:因果句測試本來就 borderline(spec 自己認),**考慮唔寫 hub、
直接拆標籤**(oil-price vs LNG-buildout 根本兩個 driver)。
**驗證**:機械驗收 = 寫成後 `lint.py` hub-MISSING warning 清零 + 每個成員 theme
kill_condition 有反向連結 + 頁內有共同監察指標清單(出口牌照事件 log);價值驗證係事後
質性覆盤——下次中國出口管制事件發生時,對照 hub 頁有冇令判斷快過 2025-02 碲管制嗰次。

### P2-3|需求端反向驗證掃描(新建議)

Constraint scan 而家淨係聽**供給方自述**(「we are sold out」)——管理層口徑可以吹。
corpus.db 有全市場 transcript:同一句樽頸,**去買家嗰邊搵**(hyperscaler 講「power
constrained」、車廠講「chip allocation」)。供給方講 + 需求方呻 = 雙式記帳,先係
真樽頸;淨係供給方講 = 打個折。FTS5 現成,每主題加一個 buyer-side 關鍵詞集,
週度掃描疊入 theme_signal。

### P2-4|獲利回收紀律(生命週期補窿)

三條退場路(kill/過期/beta化)全部係「thesis 死咗」先走——**冇一條係「thesis 贏咗」嘅
出口**。Magnifier 自己教材(MU 2016-18:6.5x 之後 −55%)講明呢類贏家會回吐一半。
建議:當 theme 嘅擁擠複合讀數(P1-2)入 top decile **且** 倉位 ≥2x 成本,機械 trim 1/3,
回收資金入 early-stage 主題——同 core R4(LEAP 盈利掃返底倉)同 M2(F&G>75 唔加倉)
一脈相承,唔係 TA 擇時,係擁擠紀律。Ledger 起咗之後 paper 驗證一季先接。

### P2-5|衛星凸性表達 pilot(§5-D 延伸,有現實約束)

探測結果:10/12 主題名有真 LEAP 鏈;乾淨可行 = MU/FSLR/AVGO/TSM;LPX/USAC 冇 LEAP。
**但一張 MU 最平 $9.1k——冇 P0-1 集中化,呢條路根本開唔到閘**(而家 $1.2k 注碼連一張
都買唔起)。仲有一個重要交互:**IV 就係擁擠嘅價錢**(COHR 96.7%、MU 90.1%)——
擠嘅主題,期權市場已經收咗你擁擠溢價,凸性表達只應該用喺 early/平 IV 嘅主題。
**次序**:P0-1 落地 → 揀 1-2 個 top-K 且 IV 合理嘅名 → 股票 book vs 期權 book 平行
paper 記帳一季 → 先決定接唔接。呢個唔係挑戰 two-tier scope 決定,係一個受控 pilot 提案。

### 快手項(順手做)

- 確認 6 個新 theme 已入 `log_predictions` 覆蓋(track_record 07-10 為止得舊 9 個)
- WS5 §8 mf-cap 口徑修正(P0-1 一齊做)
- SIVE 冇價源:39 條 prediction 判唔到,decide 換 proxy 定除名

---

## 4. 創新層(§5-D)——上面未涵蓋嘅一個大方向

P0-2(milestone Brier)、P1-1(expectations gap)、P1-2(analyst 出席數)、P2-3(需求端
反向驗證)、P2-4(獲利回收)其實已經係創新項。呢度補最後一個,最大膽但講得清驗證方法:

**「衛星層都要有自己嘅 T1/T2 分解」。** Core 嗰邊你哋做過最有價值嘅一件事,係將回報
分解做「擇時技巧 T1」同「結構拖累 T2」,先發現現貨擇時贏唔到而槓桿先係出口。衛星層
而家冇呢種分解:一個 theme 賺錢,你唔知係(a)thesis 對咗(供需真係緊)、(b)入場
擁擠度低買得平、定(c)純粹 AI beta 潮水。建議 ledger 起咗之後,每個平倉主題做三因子
歸因:**vs SPY(市場)、vs 最近似板塊 ETF(板塊 beta)、剩餘(thesis 特有)**——
beta_check.py 已經有「最近似 ETF」嘅基建,呢個只係將佢由風控用途延伸做歸因用途。
一年後你會有一張表:15 個主題嘅「thesis 特有回報」分佈——嗰張表先係「Phase-3 有冇
alpha」嘅終審證據,IC 同 Brier 都只係佢嘅先行指標。

---

## 5. 冇改嘅嘢(審過,企得住)

- Core v2 全套(200SMA 閘、月度 top-up、Δ0.50 旗艦、b15%)——唔掂
- 裁判 PASS/FAIL 門檻數字本身(0.05/IR 0.5/60/150)——保留,加尺唔改尺
- 單源封頂 0.30、admission lint、kill T+1 紀律、China caveat——保留
- 發現配額 ≥50% 非 ai-capex——保留(佢係管 pipeline 偏誤嘅正確槓桿,注碼 cap 管唔到呢樣)
- 50% meta-factor **部署** cap——保留做硬錢規則;但「belief-weight 54.9%>50%」唔應該
  讀做違規:54.9% 係 concentration.py 量 confidence 權重,sizing.py 實際部署 ai-capex
  只佔 39.2%(2026-07-12 實跑),錢冇爆錶。**你唔可以立法規定證據喺邊度聚集**;
  belief 集中係診斷讀數,錢集中先係規則,kill-scenario VaR(§2.1 #4)先係決策語言。
  三樣嘢而家撈埋一齊講,係 §6-1 呢條張力遲遲冇人「跟進」嘅真正原因——因為冇嘢需要跟進,
  需要嘅係把尺換名。

---

## 6. 證據 & 可重跑索引

| 主張 | 證據 |
|---|---|
| 注碼反排序 / memory $1,184 | `python thesis/sizing.py` 2026-07-12 實跑(本檔 §0)|
| 四方案 MC(A $234 → D $5,248)| `backtest/results/2026-07-12_sizing_two_axis_decision_analysis.md` + `experiments/exp_sizing_two_axis.py` |
| MU capex/D&A 兩頂一致、MP 警號 | `backtest/results/2026-07-12_capex_da_supply_response_probe.md` |
| MU 谷底 analyst 出席 20 年低、USAC 全場最低 | `backtest/results/2026-07-12_analyst_attendance_crowding_probe.md` |
| MU 一張 LEAP $9.1k、IV=擁擠價錢 | `backtest/results/2026-07-12_satellite_option_expression_probe.md` |
| 裁判規格/439 預測/matured 0 | `thesis/forward_ic.py` + `thesis/track_record.jsonl`(07-12 統計)|
| 估值框架缺席 | WIKI/ARCHITECTURE 全文掃描(無 DCF/intrinsic/安全邊際字眼)|

> **誠實聲明**:MC 嘅 magnitude/downside 全部係人工假設(逐項列喺結果檔),佢證明嘅係
> 「喺任何合理假設族下,方案排名穩定」呢個結構性結論,唔係邊個方案賺幾多錢嘅點估計。
> 本檔所有 P0-P2 建議入面,唯一建議即刻郁真錢嘅係 P0-3(crypto 治理);其餘全部行
> shadow/paper 驗證先。
