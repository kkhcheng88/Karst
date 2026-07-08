# Dashboard 設計:core 策略每朝讀數(2026-07-06)

> 承接 `2026-07-03_dashboard_decision_experience.md`(下稱「舊檔」)——舊檔嘅逐面板規格/信任機制/
> 不要做清單全部有效,**不重做**。本檔只加舊檔冇答嘅新問題:`2026-07-06_core_strategy.md`
> 嘅 2D 象限 + 9-scenario playbook 點樣變成每朝一句話。目標讀者:非技術個人投資者,5 分鐘睇完
> 知做唔做嘢。**Read-only、日更、無 real-time、手機可睇**——呢個係唯一目標,舊檔五、本檔五都重申。

---

## 1. 首屏「今日一句」—— scenario 表 → 一句 action

**訊號 → 句子映射**(直接搬 core_strategy §6 個 9 格,唔加唔減唔重新演繹):

| # | 讀數組合(T 日收市判定) | 今日一句(印喺最頂,大字) | 呢句嚟自邊個 code 讀數 |
|---|---|---|---|
| 1 | 牛(>200SMA)+ VIX 平靜(<18~20 帶)+ RSI-2 中性 | **今日:乜都唔使做** | `mc.spy_above_200sma` + `mc.vix` + `et.rsi2` 中性帶 |
| 2 | 牛 + RSI-2<10(5 日內首次)+ 未滿 LEAP premium 目標 | **今日:可以開 LEAP 倉**(買 SPY 1年 0.80Δ call,加到 premium 目標) | `et.rsi2 < 10` + `mc.spy_above_200sma` + LEAP 倉位狀態(**未接線**,見 §2②) |
| 3 | 有 LEAP 在倉 + 剩 63 個交易日 | **今日:LEAP 要 roll**(賣舊買新 1 年 0.80Δ;超額盈利部分掃返底倉) | LEAP 到期日狀態(**未接線**) |
| 4 | RSI-2>90 + 冇短 call 在倉 | **今日:可以賣 call**(21DTE 0.30Δ,名義 ≤25% 底倉) | `et.rsi2 > 90` + 短 call 倉位狀態(**未接線**) |
| 5 | 牛 + VIX>28(恐慌窗,一輪一次) | **今日:恐慌部署窗開咗**(10pp 買 SPY 或賣 20Δ CSP,擇一,做過一次就唔再做) | `mc.vix > 28` + `mc.spy_above_200sma` + 部署狀態機(**未接線**,見 §2②) |
| 6 | 已有恐慌倉 + VIX<18 | **今日:退恐慌倉**(沽返恐慌加碼嗰批 / 等 CSP 到期唔續) | `mc.vix < 18` + 部署狀態機(**未接線**) |
| 7 | 收市 <200SMA×0.98 連續 5 日(轉熊) | **今日:LEAP 全沽**(底倉不動,停開新 LEAP/CSP) | `mc.spy_dist` 連續 5 日狀態(**未接線**,C5) |
| 8 | F&G>75(貪婪出場側) | **今日:停止賣 put**(唔加倉;call 嗰邊照舊) | F&G fetch(**未接線**,見舊檔③ + 本檔已知缺口) |
| 9 | 每年首個交易日 | **今日:年度再平衡**(底倉/LEAP premium 調返目標 %) | 日曆判斷(**可即刻做**,唔靠任何未接線數據) |

- **顯眼原則**:句 1(乜都唔使做)係最常見輸出(§2 quadrant①牛+平靜佔 74% 日子),**唔可以因為
  「太平凡」而細字處理**——用同一級大字體 + 沉靜色(唔用警示紅/橙),避免用戶誤讀「靜」為
  「壞消息」或養成「冇警示先安心」嘅錯覺。句 2-8 用觸發色(§4 統一色碼)。
- **邊句都印唔到點做**:任何一句嘅前提數據未接線(見上表右欄),首屏改印
  「**今日:數據未夠,冇法判斷 X**」(X = 邊個訊號缺),**唔准靜默 fallback 去句 1**——
  句 1 係「檢查咗、確認冇嘢做」,唔係「唔知道」,兩者對用戶意義完全唔同,混埋 = 隱藏風險。
- **本頁不重算 gate 邏輯**:一句直接讀 §2 quadrant 面板嘅輸出(單一 source of truth),
  唔喺 render 層重新判斷 9 格邊格中——避免兩處邏輯不同步。

---

## 2. Panel 層級(晨讀 5 分鐘路徑)

### ① 大市閘 —— 2D 象限圖(新,取代舊檔③嘅「過渡兩軸」為 core 版本主視覺)

| 項 | 內容 |
|---|---|
| 畫面 | 2×2 格仔圖:X 軸=趨勢(200SMA 遲滯狀態)、Y 軸=VIX zone(<18 平靜/18-28 中/>28 恐慌,3 檔非 2 檔——沿用 `context._risk_appetite` 4 段但恐慌閾值對齊 core_strategy);今日一點亮起所在格,格內印 `core_strategy §2` 嗰四格文字(底倉/LEAP/短call/現金動作) |
| 遲滯狀態徽章 | 「跌破 3/5 日」/「已達 5/5 日 → 轉熊」/「站上即時確認」—— 對應 T1(連續 5 日 <0.98×200SMA)/T2(即時 >200SMA)。呢個係 core 策略嘅核心機制,必須顯眼 |
| 數據源 | `mc.spy_above_200sma` / `mc.spy_dist`(`context.py:39-44,65-66`)+ `mc.vix`(`context.py:62`)已喺 payload;**但四格 quadrant 判斷邏輯 + 遲滯狀態機唔存在**——`context.py` 淨係將 trend/vix/breadth/momentum 分開開關做 OR 邏輯合成 `fragile`(`context.py:83-88`),冇 2D interaction、冇連續日計數 |
| 接線狀態 | 🟡 **需 C5 wiring**(`gap_conflict_register.md` §2 C5:「PARTIAL:input 有、quadrant 邏輯無」)。研究版邏輯喺 `exp_trend_vix_axis.py` / `exp_market_regime_2d.py`,未入 spine |
| 更新頻率 | 每日一次(隨 `run_scan.py` cron) |
| Fallback(未接線時顯示)| 唔畫格仔圖;顯示文字版「趨勢:{above/below} 200SMA({dist}%)· VIX:{值}({zone})」+ 黃字「2D 象限邏輯未接線,以下為獨立讀數,交叉判斷需人手對照 core_strategy §2 表」,連結去 core_strategy.md §2 俾用戶自己對表 |

### ② Core 執行面板(新,全站最大缺口——目前完全冇「用戶實際持倉狀態」呢層)

> **重要發現**:全庫搜尋確認 —— **repo 裡面冇任何模組追蹤用戶實際持倉**(LEAP 買咗未、
> 幾時到期、短 call 有冇喺倉)。`backtest/spine/holdings.py` 係 ETF 成份股組成(唔相關);
> `thesis/log_predictions.py`/`forward_ic.py` 係 thesis 校準 ledger(唔係持倉)。
> 呢個唔係 C5/C9 果類「邏輯未接線」,而係**冇資料源**——read-only dashboard 讀唔到用戶
> 手動落嘅單。呢層要嘛(a)用戶手動輸入持倉狀態(輕量表單,唔違反 read-only「唔落單」原則,
> 但要諗清楚點存/邊個寫入),要嘛(b)保持顯示「靠人手對帳」嘅 fallback。設計上列為 **P2**。

| 子項 | 顯示 | 數據源 | 接線狀態 | Fallback |
|---|---|---|---|---|
| LEAP 倉位 | 「有倉:1年 0.80Δ,開倉日 X,剩 N 個交易日」/「未開倉」 | 無現成模組——需新建輕量持倉紀錄(手動輸入或獨立 JSON) | 🔴 **P2 新模組**(非 C5/C9,係全新缺口) | 顯示「持倉狀態未接線 —— 對照 core_strategy §6 playbook 自行判斷開倉/roll」 |
| roll 倒數 | 「剩 63td → roll」進度條 | 同上(LEAP 開倉日 + 交易日曆) | 🔴 P2 | 同上 |
| RSI-2 讀數 | 數值 + DIP/中性/OB 標籤(已有樣式,舊檔沿用) | `timing.entry_timing()`(`backtest/spine/timing.py:15-28`)→ payload `cards[].entry_timing` | ✅ **live**(SPY 卡已有) | — |
| 短 call 狀態 | 「在倉:0.30Δ,到期 X」/「未賣」 | 同 LEAP,新模組 | 🔴 P2 | 「未接線 —— RSI-2>90 且冇短call在倉先符合賣call條件,自行核對」 |
| 恐慌部署狀態 | 「待命」/「觸發中(本輪已用)」/「冷卻」狀態機(舊檔④乾火藥計時器嘅 core 版) | VIX>28 觸發條件已有(`mc.vix`);「本輪用咗未」= 部署狀態,同 LEAP 一樣冇持倉層 | 🟡 觸發判斷可 P0 做(讀 VIX);「用咗未」🔴 P2(需持倉層) | 只顯示觸發條件是否成立,唔顯示「用咗未」;文字提示「今個恐慌窗用咗未請自行記錄」 |
| 年度再平衡倒數 | 「距離下個交易年首日:N 個交易日」 | 純日曆計算,唔靠任何未接線數據 | ✅ **P0 可即刻做** | — |

**設計取態**:呢個面板寧可老實顯示「未接線」都唔好靜默假設用戶冇持倉——假設錯咗會令用戶漏咗
roll/減倉動作。P2 新模組建議做法(留俾實作階段):`web/data/positions.json`,用戶手動維護
(開倉日/delta/到期),dashboard 讀取顯示但唔寫入(維持 read-only + NHITL)。

### ③ tier-2 卡片(舊檔已有規格,原樣繼承——唔重複)

沿用舊檔§三⑦:渲染 `kill_condition`、逐卡 `caveats`、action 優先排序。**本檔不重複**。

### ④ Phase-3 衛星(新)

| 子項 | 顯示 | 數據源 | 接線狀態 | Fallback |
|---|---|---|---|---|
| confidence 變化 | 逐 thesis 今日 vs 上次 confidence(`unit`)差,箭嘴 ▲▼ | `ThesisVerdict.unit`(`schemas.py:88`)已喺逐卡 payload;**差量比對**靠舊檔②嘅前日快照載入機制(`_load_previous_payload`,同一套) | 🟡 **需前日快照 wiring**(舊檔②已規格,未實作) | 只顯示今日 confidence 數值,唔顯示 Δ;註明「差量比對未接線」 |
| forward-IC 追蹤 | 每主題 forward IC 數值 + 是否過 0.05 門檻(PASS/FAIL 徽章) | `thesis/forward_ic.py` 已計 IC(`:168,176`)但**冇 enforce**(C3:「算到、冇 enforce」,prose target 非 PASS/FAIL 程式判斷) | 🔴 **需 C3 wiring**(接 enforce 邏輯 + 兩個唔一致 logger 先統一,見 C2) | 顯示原始 IC 數值(如有),唔顯示 PASS/FAIL 徽章;註明「門檻判斷未程式化,人手對比 0.05」 |
| 衛星資金占比 | 「Phase-3 衛星 ~20% NAV(core ~80%)」靜態文字,唔係即時算出嘅倉位百分比 | 靜態(core_strategy 頭一句) | ✅ 文字層可即刻做(非計算) | — |

### ⑤ 系統健康(新,承舊檔四之3「新鮮度 banner」擴展做專屬面板)

| 子項 | 顯示 | 數據源 | 接線狀態 | Fallback |
|---|---|---|---|---|
| 數據新鮮度 | `asof` vs 今日日曆日落差;>1 交易日變黃、>2 變紅;標注資料源(defeatbeta/yfinance) | `mc.asof` + `payload.generated_at` 已在 payload;`df.attrs["source"]` 穿透(舊檔已規格為小改) | 🟡 asof 比對 **P0 可做**;source 穿透 **P1 小改** | 只顯示 asof 日期,唔顯示新鮮度顏色判斷 |
| 兩個 logger 衝突 warning | 「⚠️ 校準紀錄用緊兩套唔一致 schema 寫同一檔——forward-IC 數字可能唔準,修復前僅供參考」 | C2 發現:`forward_ic.py:62-81` vs `log_predictions.py:39-73` 寫同一 `track_record.jsonl` 但 schema 唔同(`gap_conflict_register.md` §2 C2) | ✅ **靜態文字警告,P0 可即刻加**(唔需要程式判斷,寫死喺 render 直到 C2 修復先拎走) | — |
| scan.py 執行狀態 | 「最後一次成功掃描:{asof}」+ 若 cron 跳日「vs {asof}(上次成功掃描,非嚴格昨日)」 | `run_scan.py` 寫 `latest.json`;沙盒失敗(`defeatbeta_api` 缺 package)本機正常——健康面板應顯示「上次成功執行」時間戳,唔係「今日冇跑就報錯」 | ✅ **P0**(`app.py:_load_payload` 已有 file-missing/corrupt 判斷,擴展顯示執行時間戳即可) | 若 `latest.json` 完全缺:沿用現有 `render_error`(app.py:88-90 已有) |

---

## 3. Action-first 原則(貫穿全站)

- **每個讀數右側/下方直接印一句 action**,唔淨係印數值——例:VIX 27.8 唔淨係印數字,
  要印「VIX 27.8(<28 未觸發恐慌部署)」;RSI-2 8.2 要印「RSI-2 8.2(<10 = 開 LEAP 訊號,
  但要睇未滿倉先算數)」。
- **「今日:乜都唔使做」係最常見輸出,要顯眼咁講**(§1 已述,呼應)——用中性但清晰嘅視覺
  權重(唔係細字灰色帶過),避免用戶因為畫面太靜而覺得系統冇運作。
- 未接線嘅讀數一律印「數據未接線,人手核對 X」,唔印空白或假分數。

---

## 4. 唔好過度設計(read-only 邊界重申)

- 每日一 build(`run_scan.py` cron),**無 real-time / 無盤中報價**——同舊檔五第二點一致。
- 手機可睇:2D 象限圖用簡單格仔 SVG(4-6 格,非複雜互動圖表),核對舊檔 CSS 已有
  `@media(max-width:900px)` 響應式規則(`render.py:419-420`),沿用同一斷點。
- **P2 持倉模組唔等於「落單功能」**——如果做,只做「讀取用戶已手動記錄嘅持倉狀態並顯示」,
  唔做「喺 dashboard 度落單/連券商 API」,維持 NHITL + read-only 精神。
- 唔喺呢層重新驗證策略本身(core_strategy §7 已有可信度分層,dashboard 只負責顯示,唔重新judge)。

---

## 5. 實施優先次序

| 優先 | 內容 | 前提 |
|---|---|---|
| **P0**(code 已有數據,即刻出到) | 首屏句 1/9(乜都唔使做/年度再平衡,純日曆)、RSI-2 讀數面板、系統健康之 asof 新鮮度 + 兩個 logger warning + scan 執行時間戳、Phase-3 衛星資金占比靜態文字、tier-2 卡(舊檔規格搬字過紙) | 無 |
| **P1**(要 C5/C9 接線,見 gap_conflict_register §2) | 2D 象限圖 + 遲滯狀態徽章(C5)、首屏句 2-7(開LEAP/roll/賣call/恐慌窗/退恐慌/轉熊,依賴 quadrant + 連續日計數)、data source 穿透 asof 顏色判斷 | C5(2D quadrant 邏輯入 spine)+ 連續 5 日狀態機 |
| **P2**(要 Phase-2 tilt 接線 / 新持倉模組) | Core 執行面板全部持倉狀態(LEAP倉/roll倒數/短call/恐慌部署「用咗未」)、句 8(F&G 貪婪出場,需 F&G fetch 進 run_scan)、forward-IC PASS/FAIL 徽章(需 C3 enforce + C2 統一 logger)、confidence Δ(需前日快照 wiring) | 新持倉紀錄模組(非 C5/C9)+ F&G fetch(舊檔已標)+ C2/C3 + 前日快照(舊檔②) |

---

**與舊檔分工**:舊檔答「點樣顯示信任/差異/證據連結」(通用決策體驗機制,任何策略都適用);
本檔答「core_strategy 呢條特定策略樹,邊個訊號映射邊句 action、邊層完全冇資料源」。
兩檔合讀 = 完整 dashboard spec。
