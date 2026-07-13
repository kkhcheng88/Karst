# 裁決建議 — MP Materials(MP)capex/D&A 雙警號對抗式人手級覆核

**Date:** 2026-07-13
**Type:** decision-support(NHITL)——**最終裁決權在用戶,本文是覆核 + 建議,不是自動落 kill**
**動機:** Fable 交接書 P2-16「兩軸齊響 2.192x/2.540x,P2 死亡劇本前兆,未有人跟」。稀土 theme 現處 KILL-WATCH,錯得像對的代價高,故正反雙方都寫足。
**覆核材料:** `backtest/results/2026-07-12_capex_da_supply_response_probe.md`(警號出處)、`docs/2026-07-09_magnifier_model_plan.md` §3c(P2 定義)、`backtest/results/2026-07-09_magnifier_case_library.md`(9 週期爆煲庫)、`thesis/wiki/rare-earth-materials.md` + `thesis/themes.yaml`(kill_condition/confidence/中國依賴 audit)、`thesis/wiki/sources/078`(#078 全文)、`corpus.py` transcript-MP-2026-05-07(最新法說)。

---

## 前置:一個貫穿全文的關鍵發現

**probe 從來冇計過 MP 自己的歷史 capex/D&A 分佈。** probe 的兩週期歷史分佈分析(percentile、教科書「紀律谷底→再加速」路徑)**全部只做咗 MU**(probe 第 61-122 行),MP 只出現喺「15-theme 今日單點快照表」(probe 第 136 行)一次。所以「2.192x/2.540x 有幾極端」呢個問題,喺 probe 裏面**冇 MP 自身基準可比**——只有跨 15 個 theme 的橫切排名。呢個事實直接影響下面每一條的答案,尤其係紅藍對抗。

---

## 問題 1:兩個警號軸實際量度緊乜?2.192x/2.540x 有幾極端?

**兩軸定義(probe 第 32-38 行,明確拆開兩個唔同指標):**

| 軸 | MP 讀數 | 定義 | 意義 |
|---|---|---|---|
| **capex/D&A(TTM 水平比率)** | **2.192x** | capex ÷ 同期 D&A(TTM) | >1 = 淨產能擴張超過折舊替換;標準 capital-cycle 指標 |
| **capex YoY(增長倍數)** | **2.540x** | 最新季 capex vs 4 季前 | 加速度;量度「而家擴張得幾快」 |

出處:probe 第 136 行(MP 行:`rare-earth-materials | MP | 2.192x | 2.540x`)。

**「有幾極端」——三個層次的誠實答案:**

1. **橫切排名(唯一有做的比較):** 15 個 theme 中,水平軸 MP 排第 3(RKLB 3.080 > MU 2.803 > **MP 2.192**;probe 第 132-148 行);YoY 軸 MP 排第 4(AMKR 2.811 > MU 2.664 > COHR 2.591 > **MP 2.540**)。MP 是**除 MU 外唯一一個「兩軸都過門檻 + 敘事吻合」**的 theme,故 probe 把佢列為第 2 警號 theme,並明寫「之前冇被特別標記過,呢個 probe 先發現,值得盡快人手覆核」(probe 第 156-159 行)。**本文就是回應呢句。**

2. **門檻本身無統計基礎(probe 自己的 caveat):** flag 規則(水平>2.0x 或 YoY>1.5x)是 probe「粗略錨定 MU 自己而家嘅讀數」倒推的 loosely-anchored 門檻,**唔係外部驗證的 cutoff**(probe 第 150、224-225 行)。probe 更明寫:n=2 週期樣本太細、唔可以宣稱呢個門檻有預測力(第 228-229 行);而支持呢類指標的文獻(Cooper 2008 asset-growth、Titman 2004 capex)驗證的是**跨股票排名 factor、~1 年遠期回報**,**唔是**「單一具名股票穿過某門檻 = 週期頂」呢個用法——mirror 錯配(probe 第 198-202 行)。

3. **MP 自身極端度 = 未知。** 因為 probe 冇 MP 歷史時序,「2.192x 對 MP 自己嚟講算唔算高」**冇答案**。而且 MP 水平軸(2.192x)**低過 probe 自己標為結構性誤報的 RKLB(3.080x)**——RKLB 被 probe 判為「年輕公司、折舊基數細 → 結構性高比率,唔係週期頂」(probe 第 164-166 行)。MP 2020 年先 IPO、正喺由零起建整條磁材供應鏈,折舊基數同樣細——**MP 的高比率有可能屬 RKLB 型 base-rate 假象,唔係 MU 型週期頂**。呢點是藍方的核心。

> **問題 1 小結:** 兩軸量度的是「產能擴張相對折舊」(水平)同「擴張加速度」(YoY)。就橫切嚟講 MP 確實是除 MU 外最響的一個;但「極端」呢個字冇 MP 自身基準支撐,而門檻本身按 probe 自己講係無統計基礎、mirror 錯配的 loosely-anchored 值。

---

## 問題 2:供給紀律崩壞(P2)定政府訂單帶動的被動擴產?——**本次覆核核心**

### P2 死亡劇本的精確定義(唔可以含糊)

`docs/2026-07-09_magnifier_model_plan.md` §3c 第 75-77 行:死亡 marker =「**供給紀律逆轉**」——「公司**由紀律轉狂擴** capex/借錢/併購 = 頂訊號」,與 memory-supercycle 現行 kill「LTA 停滯 OR HBM 產能 ramp AHEAD of 需求(glut)」同源。錨定案例 = MU(§ 第 20-24 行)。

case library 跨 9 週期收斂出的死亡三特徵(第 377-388 行):
- **(1a)** 週期頂附近做**債務融資**的槓桿式產能/併購(Global Crossing/DryShips/VeraSun/LDK);
- **(1b)** 護城河**是否真獨立於樽頸商品價格本身**(FSLR CdTe 唔使多晶矽 vs 純晶矽 play);
- **(1c)** 有冇**多元化/低成本分位**緩衝(ADM vs VeraSun;純 play 幾乎全滅)。

**P2 的定義要件是「reversal」——一間本來有紀律的公司,喺需求敘事高位突然轉去債務融資超建。**

### MP 對照 P2 三特徵:結構上**唔係** P2 型,更接近 MU 的 LTA 反敘事

| P2 要件 | MP 實況 | 出處 |
|---|---|---|
| **(1a) 債務融資的槓桿式超建** | ❌ 擴產由 **DoD 15% 股權注資**(equity,非 MP 獨力舉債)+ **10 年 $110/kg NdPr 保底**(現金流地板)+ **Apple $72M 預付**(下游需求鎖定)+ **Project Vault $12B**(政府戰略儲備背書)撐住。最新法說:剛 broke ground on 10X,「**full Department of War support**」,構建加速 | 源 #078 dek/stats;wiki 第 53、66 行;transcript-MP-2026-05-07 |
| **(1b) 護城河獨立於商品價?** | ✅ 部分成立:$110/kg **保底把現金流從商品週期解耦**——正正是 case library 講純 play 死於「commodity-price exposure 反轉」的**相反**;呢個 floor 比 MU 的 LTA/take-or-pay **更強**(是政府定價地板,不只長約) | wiki 第 74 行;themes.yaml 第 424-425 行 |
| **(1c) 多元化緩衝?** | ❌ MP 是純 play(單一 Mountain Pass 礦 + 磁廠),無多元化——**呢個是 MP 真正的結構弱點**(下見紅方) | case library 第 196 行 |
| **「由紀律轉狂擴」的 reversal?** | ❌ MP 從來冇經歷過「紀律期」再逆轉——佢正處**戰略資產的初次建置期**(2020 IPO 後由零起建磁材鏈),唔是晚週期對超建的投降。管理層框架:「we continue to **scale and execute with discipline**」「ramping core processes with precision」 | transcript-MP-2026-05-07 |

**需求性質的根本差異:** P2 的需求是**商品週期需求**(會反轉);MP 的擴產驅動是**國安級 onshoring 政策 mandate**(把稀土磁材鏈搬離中國)+ 三重合約綁定(DoD/Apple/Vault)。case library 亦有 MP 自己的 row:**cyclical-supercycle + event-driven,confidence 0.28,未清晰命中 5x 門檻**(第 196 行)——即 case 庫本身冇把 MP 當成典型爆煲樣本。

> **問題 2 小結:** 就定義嚴格對照,MP 的 capex 加速**唔符合 P2「供給紀律逆轉」的核心要件**(無債務融資超建、無 discipline→狂擴的 reversal、有政府保底解耦商品價)。佢更接近「政府/國防合約帶動 + 保底護底的政策性被動擴產」,結構上近 MU 的 LTA 反敘事、遠 P2 死亡劇本。**唯一真對得上 P2 的是 (1c) 純 play 無緩衝**——呢點紅方會用盡。

---

## 問題 3:同 2026-11 event kill 條件點互動?警號會唔會只係 event 前噪音?

**event 定義:** `thesis/themes.yaml` 第 398-404 行 kill_condition ——**2026-11 中美正式協議全面解除銦/鎵/重稀土出口管制** → 咽喉論述基礎瓦解,confidence 歸零,回歸商品週期 mean-revert。同月撞美國期中選舉(源 #078:川普政治不能輸 → 北京議價籌碼放大)。現況:管制機制原封不動,釔/鏑/鋱對美出口只剩管制前約 5%/41%/49%(源 #078)。

**capex 警號同 event 的互動 = 條件相依,唔是獨立訊號:**

- **base case(咽喉延續、管制不解除):** MP 的 capex 對得住已鎖定需求(DoD/Apple/Vault),floor 護現金流 → capex **唔是**危險訊號,是政策性合理擴產。
- **kill case(2026-11 管制解除):** 稀缺溢價崩,MP 手上一堆新建低回報產能 → **呢個時候先變成 P2**,而且正正係 case library 最尖銳教材 **LDK Solar「反向整合入新增產能、追供給訊號追到訊號剛好反轉」**(第 274 行)的翻版。
- **關鍵:** 即使 kill case 觸發,**$110/kg 保底仍護住 MP 的現金流地板**(雖然護唔住政策溢價估值)——所以連 kill case 都唔是乾淨的 P2 歸零。

**所以:capex 警號不是獨立的「供給紀律崩壞」訊號,而是一個 event-conditional risk multiplier。** 佢只喺 kill case 場景先兌現成 P2;喺 base case 是噪音。**呢個 event 二元性正正是把佢當「獨立死亡前兆」會誤導的原因。** 真正要盯的單點是 2026-11,唔是 capex 比率本身。

---

## 問題 4:對抗式(紅藍雙方,各自成立,唔准稻草人)

### 🔴 最強紅方(即刻 trim/kill 的最好論證)

1. **政府背書從來救唔到爆煲——case library 有硬證。** 太陽能組:**Solyndra 有 $535M DOE 貸款、且技術上專為「唔使多晶矽」而設計(表面上避開咗樽頸),照樣破產**(第 280 行);VeraSun 有 RFS 強制配額的政府擔保需求底,照樣 2 年破產(第 123 行)。**「DoD/Apple 合約 + $110/kg 保底」正正是呢類「政府需求敘事」——歷史上呢個唔是免死金牌。** MP 的 DoD/Vault 背書在論證結構上同 Solyndra 的 DOE 貸款是同一類東西。
2. **MP 是純 play,無 (1c) 緩衝。** case library 跨 9 週期最乾淨的分野:純 play 幾乎全滅,多元化/低成本分位存活(第 315-318 行)。MP 單礦單鏈,冇任何多元化。
3. **capex 是對「咽喉延續」的槓桿式押注,而 timing 貼近 binary 事件解決點。** 一路狂建產能到 2026-11——若管制解除,就是 LDK 型「追訊號追到反轉」。擴產動作本身喺當時已公開可見(10X 動工),完全符合 case library 講的「死亡 marker 喺當時已係公開 SEC/新聞」(第 381 行)。
4. **估值已重度入政策溢價:ttm_pe 119.6 = 自身史 92 分位**(wiki 第 53 行、themes.yaml 第 425 行)。下行不對稱:base case 已 price-in,kill case 崩。wiki 自己結論就係「**別追高**」。
5. **中國依賴仍有過渡期缺口:** MP 歷史上 >90% 營收靠賣精礦俾 Shenghe 喺中國分離;DoD $400M 夥伴切走營收依賴,但**重稀土(鏑/鋱)本土分離要等 2026 中新線先投產**——即擴產期正撞產能依賴未完全脫鈎的窗口,加中國反向把 MP 列設備/技術進口黑名單(themes.yaml 第 428-436 行)。capex 建緊的正是呢條未驗證的新線。

### 🔵 最強藍方(警號誤報的最好論證)

1. **警號的門檻同 mirror,probe 自己已經 disown。** 門檻無統計基礎、n=2、mirror 錯配(cross-sectional factor ≠ single-name peak-timing)——**呢啲唔是我嘅辯護,是 probe 自己白紙黑字的反對理由**(probe 第 198-202、224-229 行)。用一個自己都話「唔可以宣稱有預測力」的門檻去推「死亡前兆」,舉證責任未達。
2. **MP 冇自身歷史分佈,而佢水平軸(2.192x)低過 probe 自己判為誤報的 RKLB(3.080x)。** RKLB 被判「年輕公司、折舊基數細 → 結構性高比率、唔係頂」(probe 第 164-166 行)。MP 2020 IPO、由零起建磁材鏈、D&A 基數細——**高比率極可能是 RKLB 型 build-out 假象,唔是 MU 型週期頂**。冇 MP 自身時序,「極端」講法冇底。
3. **$110/kg 政府保底把現金流從商品價解耦——這是 case library 判「存活」的那一側,不是「爆煲」那一側。** 純晶矽 play 死於 commodity-price exposure 反轉;MP 的 floor 正正移除咗呢個 exposure。probe 亦把 MU 的 LTA/RPO 列為「純比率指標睇唔到、會對有鎖定需求的名產生假陽性死亡訊號」的頭號反例(probe 第 230-232 行)——MP 的政府 floor 是**比 LTA 更硬**的同類反例。
4. **P2 定義要件係「reversal」,MP 冇 reversal 可言。** MP 唔是「有紀律 → 突然狂擴」的晚週期投降,而是戰略資產的初次建置。管理層框架是需求拉動(customer validation、DoW support、Apple offtake)、非供給推動的投機。硬套 P2 = 類比錯配。
5. **需求是結構性 onshoring mandate,唔是商品週期需求。** 咽喉是 USGS 官方硬數據(銦 70%、鎵 98-99%、重稀土對美約 5%),需求鎖死國防(F-35/神盾/潛艇)+ EV + AI 電源——真、additive、非一次性(wiki 第 84-86 行)。呢類需求唔會像記憶體/航運咁週期反轉。

### 對抗結論(唔偏幫)

紅方最硬的一點是 **(1) 政府需求救唔到 Solyndra/VeraSun** 加 **(2) 純 play 無緩衝** 加 **(4) 92 分位估值**——呢三點**真、獨立成立**。藍方最硬的一點是 **警號本身(門檻/mirror/MP 無自身分佈/RKLB 型假象)在方法上未達舉證門檻**,加 **政府 floor 是「存活側」特徵而非「爆煲側」**。

**兩邊其實喺講唔同的命題:** 藍方贏「capex 兩軸 = P2 死亡前兆」呢個**具體 claim**(即 Fable 交接書那句);紅方贏「MP 整體有值得 trim 的獨立風險」呢個**更闊的命題**(估值 + binary event + 純 play + 過渡期依賴)。**capex 警號本身唔成立為 P2 訊號,但 MP 確有非 capex 的獨立風險。**

---

## 問題 5:最終建議 + confidence + 需用戶拍板

### 建議:**維持觀察(hold / watch),不 kill、不因 capex 警號加倉;對 capex「死亡前兆」claim 判定為大致誤報。**

- **對 Fable 交接書那句「兩軸齊響 = P2 死亡劇本前兆」:駁回(rebut)。** capex/D&A 2.192x + YoY 2.540x **唔構成** P2「供給紀律逆轉」訊號——理由見問題 2/4 藍方:門檻無統計基礎、MP 無自身分佈且低過 RKLB 誤報線、政府 floor 解耦商品價、無 discipline→狂擴的 reversal。
- **但唔等於 MP 無風險。** 若用戶現有持倉是喺 92 分位政策溢價價位入的,一個**小幅 trim 是可辯護的**——但呢個 trim 的理據是**估值(ttm_pe 92 分位、wiki 已叫「別追高」)+ 2026-11 binary event + 純 play 集中**,**唔是** capex「死亡訊號」。兩者要分清:唔好用一個誤報的訊號去正當化一個(基於其他理由)本身合理的動作。
- **與現有 thesis 一致:** wiki/themes.yaml 現行判斷已是 confidence 0.28(全批最低)、event-driven、「別追高、小注、分層、盯 2026-11」。本覆核**唔改變 thesis 方向**,只是把「capex 兩軸 = P2 前兆」呢個新提法澄清為誤報,並補上具體監察條件。

### 具體監察條件(用嚟區分「P2 真兌現」vs「持續誤報」)

1. **capex 融資結構是否轉債務型:** 若 MP 開始在 DoD 股權 + floor 結構以外**大額舉債/發可轉債**去建產能 → 呢個先是真正的 P2 槓桿 marker(現時是 equity/政府背書型)。
2. **$110/kg 保底 / Project Vault 撥款狀態**(已在 kill_condition):任一生變 → 現金流護墊消失,capex **即刻**變 P2 危險。
3. **2026-11 事件解決方向:** 管制解除 → capex 反轉成過剩產能(LDK 型);管制延續 → capex 合理。這是主單點。
4. **產能是否 ramp AHEAD of 已鎖定需求**(MU kill_condition 的 glut 類比):MP 建的產能若超出 DoD/Apple/Vault 已鎖量 → glut 風險。
5. **補計 MP 自身 capex/D&A 歷史時序**(probe 從未做):若 2.192x 對 MP build-out 期屬正常 → 警號確認為 base-rate 假象。**呢條是最低成本、最快能證偽/確認的一步,建議優先補。**

### confidence:**中**

- 對「capex 兩軸唔是 P2 死亡訊號」呢個核心判定:**中偏高信心**(多條獨立理由,且大半來自 probe 自己的 caveat)。
- 對「MP 整體該點做」:**中信心**——因為 binary event + 92 分位估值的殘餘風險是真的,而事件本身不可預測(二元地緣)。
- 拉低信心的因素:證據薄(thesis 僅 2 篇 Tier-2)、MP 無自身歷史分佈、2026-11 純二元事件無法 front-run、transcript 只取到 formal remarks(無 CFO capex guidance / Q&A)。

### 🚩 需用戶拍板

本文是 decision-support。**「維持觀察、駁回 capex-P2 前兆說、trim 與否取決於用戶對 92 分位估值 + 2026-11 二元事件的風險胃納」——最終 buy/hold/trim 由用戶決定。** 若用戶要即時降險,建議的動作是「不加倉 + 視乎持倉成本小幅 trim(理據 = 估值/事件,非 capex)」,而非 kill(kill 應留待 kill_condition 任一觸發)。

---

## 出處清單(file + 行/段)

- 兩軸數字 2.192x/2.540x:`backtest/results/2026-07-12_capex_da_supply_response_probe.md` 第 136 行;定義第 32-38 行;flag 規則第 150 行;MP 列第 2 警號 + 「先發現、值得人手覆核」第 156-159 行;門檻 loosely-anchored/無統計基礎/n=2 第 224-229 行;mirror 錯配第 198-202 行;RKLB 誤報第 164-166 行;LTA 假陽性反例第 230-232 行;MU-only 歷史分佈第 61-122 行。
- P2 定義「供給紀律逆轉」:`docs/2026-07-09_magnifier_model_plan.md` §3c 第 75-77 行;MU 錨定案例第 20-24 行。
- 爆煲三特徵 / 純 play 全滅 / LDK / Solyndra:`backtest/results/2026-07-09_magnifier_case_library.md` 第 377-388、315-318、274、280、123 行;MP 自己 row 第 196 行。
- kill_condition / confidence 0.28 / ttm_pe 92 分位 / 中國依賴 audit:`thesis/themes.yaml` 第 398-436 行;`thesis/wiki/rare-earth-materials.md` 第 53、66、74、84-86、116-119 行。
- DoD 15% / $110/kg / Apple $72M / Project Vault $12B / 2026-11 雙撞點 / 對美出口 5%:`thesis/wiki/sources/078-trend-core-research-mp-china-rare-earth-midterm-tri-collision.md` + corpus 全文 `#078`。
- 管理層框架(scale with discipline / 10X 動工 / DoW support / Apple 回收線 / PPA 保底收入 / 重稀土分離線 Q2 commissioning):`corpus.py get transcript-MP-2026-05-07`(FY2026Q1 法說,formal remarks;無 CFO capex guidance / Q&A 段)。

## 已知限制 / 未解

- ~~MP 自身 capex/D&A 歷史時序未計(probe 從未做)——「2.192x 對 MP 自己算唔算高」仍未有底,屬監察條件 #5,建議優先補。~~
  **【2026-07-13 同日已補】** 見 `2026-07-13_mp_capex_da_history.md`:MP 2.192x 喺自身歷史係
  季度 55.6 百分位 / 年度 16.7 百分位(FY2022 建置高峰 17.792x),且係 2025Q3 谷底(1.747x)後
  第 2 季溫和反彈——**確認 build-out 假象判讀,監察條件 #5 判 confirm**。對照 RKLB/MU 均處自身
  100 百分位新高,形態同 MP 完全唔同類。本文「駁回 P2 前兆」結論獲硬數據二次支持。
- transcript-MP-2026-05-07 只索引到 formal remarks(CEO/IR),**無 CFO Corbett 的 capex 金額 guidance 同 Q&A**——「MP 全年 capex 規模 vs 已鎖定需求」呢個 glut 判斷(監察條件 #4)未有一手數字支撐。
- thesis 證據薄(僅 2 篇 Tier-2:#078/#105);DoD $110/kg 保底 + Project Vault 撥款仍是 Tier-2 轉引,未一手核實 SEC/DoD 文件。
- 2026-11 為純二元地緣事件,無法 front-run;本建議的殘餘風險主要壓在呢個單點。
- `china-supply` meta_factor hub page 仍 MISSING(themes.yaml 第 43-46 行),跨 theme 相關性(rare-earth + us-solar)未成文。
</content>
</invoke>
