# Dashboard 決策體驗設計(2026-07-03)

> 目標:每天早上 **5 分鐘內完成一次有校準信任度的決策**。
> 現狀錨點全部來自實碼抽取(file:line);與
> `2026-07-03_strategy_methodology_review.md`(方法論審查)配套,
> compute 端依賴標注為「依賴 P0-x」。

---

## 一、設計原則(從已驗證發現推出,不是美學偏好)

1. **決策先行,資料殿後**:tier-2 卡已有 action(BUY_DIP/WATCH/AVOID),
   大盤層卻只給分數不給動作——頂部要有「今天要不要做什麼」。
2. **兩軸誠實**:單一混合分數會掩蓋趨勢軸/風險軸背離(✅ finding:背離標記
   2018/2020 頂、2022 底)。主視覺必須是兩軸+背離徽章,混合分降為次要。
3. **恐懼與貪婪分席**:VIX=進場恐懼計、F&G=出場貪婪計,**永不混合**(✅)。
4. **每個數字帶證據**:formula foldout 已有(`render.py:154-161,191-198` 的
   `<details class="fx">` 模式),缺的是「這條規則的回測證據」連結。
5. **差異優先**:昨天到今天什麼翻轉了,比今天的絕對讀數更值得放大。
6. **新鮮度誠實**:defeatbeta 落後 ~1 交易日只寫在 README(`web/README.md:52-53`),
   UI 上完全沒有——決策工具不標資料鮮度是缺陷。

---

## 二、資訊架構重組(面板順序)

現狀(`render.py:445-448`):大盤 → 板塊輪動 → 板塊 → tier-2 做多。
目標(自上而下 = 決策順序):

```
① 決策條(新)        今天:能開新倉? | 該部署乾火藥? | 該減碼?
② 翻轉警示 banner(新) gate/action/板塊溫度 的日對日狀態變化
③ 大盤兩軸(改)       趨勢軸 | 風險軸 | 背離徽章;混合分+sparkline 降為次行
④ 乾火藥計時器(新)    待命/觸發/冷卻 + 部署期條件統計(證據連結)
⑤ 板塊輪動(保留)     + 渲染 drivers/caveats(現在算了沒顯示)
⑥ 板塊溫度(保留)
⑦ tier-2 做多(強化)  + kill_condition、逐卡 caveats(現在算了沒顯示)
```

---

## 三、逐面板規格(含實作錨點)

### ① 決策條(最高價值,大部分資料已在 payload)
三開關,各附「狀態持續天數」與「什麼會翻轉它」:
- **能開新倉?** = `mc.gate` + `gate_label`(payload 已有,`schemas.py:8-26`)。
- **該部署乾火藥?** = 恐慌觸發(VIX>30 或 RSI2<10 且 VIX>25)✅。
  `mc.vix` 已在 payload(未渲染);RSI2 取 SPY 卡 `entry_timing.rsi2`。
- **該減碼?** = F&G>80 ✅。**資料依賴**:F&G 目前不在 scan 管線
  (僅 reference/ 下研究用 CSV)——需在 `run_scan.py` 加一個 F&G fetch
  (whit3rabbit github CSV,免費、headless 安全);拿不到就顯示「無資料」,
  **不用替代指標假裝**(RSI2>90 是 trade-exit,不是市場減碼訊號 ✅,別混用)。
- 實作:`render.py` 新增 `_panel_decision_bar(ms, mc, cards)`,插在
  `render()` 組裝最前(`render.py:445` 之前);重用 `_gauge/_meter/_dchip`
  (`render.py:54-118`)。狀態持續天數依賴前日快照(見②)。

### ② 翻轉警示 + 差異面板
- 現狀:**全站沒有任何日對日比對邏輯**(唯一的 Δ 是 market_score 自身趨勢,
  `market_score.py:125-138`);原料已存在:每日快照 `scan-YYYY-MM-DD.json`
  (`run_scan.py:60-69`)。
- 實作(agent 已定位):`app.py` 加 `_load_previous_payload()`(仿
  `_load_payload`,`app.py:64-72`,取次新快照);`render()` 簽章加 `prev`;
  新增 `_panel_delta`:逐 ticker 比 `expression.action`、逐板塊比 `temperature`、
  比 `mc.gate`。放 `<header>` 下方當 banner(`render.py:453`)。
- 誠實細節:cron 跳日時,「昨日」實為「上一個成功掃描日」——banner 要標注
  「vs 2026-07-01(上次成功掃描)」,不要假裝是昨天。

### ③ 大盤兩軸(取代單一 gauge 為主視覺)
- **過渡版(純 render,今天就能做)**:payload 裡 11 個從未渲染的 MarketContext
  因子(`spy_above_200sma / momentum_on / iwm_above_200sma / vix_iv_rank /
  vix_term / breadth_divergence …`)已足夠拼出粗版兩軸:
  趨勢軸 = trend+momentum+breadth;風險軸 = vol+term。
- **完整版(依賴 P0-2)**:compute 端加 credit(HYG/LQD)進風險軸 +
  `trend_risk_divergence` 欄位;market_score 拆成兩個子分數。
- 背離徽章:兩軸不同號時顯示「⚠ 背離(歷史上標記頂/底)」+ 證據連結。
  混合分 gauge 與 90d sparkline 縮為次行(向後相容,不刪)。

### ④ 乾火藥部署計時器
- 狀態機:`待命`(無觸發)→ `觸發中`(恐慌條件成立)→ `冷卻`(觸發後
  RSI2>90 或 F&G>80 出場訊號)✅ 對應 `exp_mr_roundtrip.py` 規則。
- 顯示部署期統計(靜態證據文字):「部署期 conditional Sharpe 1.0–1.7 vs B&H
  0.86–0.99;deployed-cap 年化 24–74%」+ 連到
  `backtest/results/2026-07-03_topdays_exposure.md`。
- 誠實標注:「這是資本部署計時器,不是 SPY 替代品(日曆 CAGR 落後 B&H)」✅。

### ⑤⑥ 板塊面板(小改)
- 渲染現在被丟棄的 `rotation.drivers/caveats`(agent 確認無渲染出口)、
  `rows[].rs21`(輪動加速度,KARS_MEMORY 讀數靠它)。

### ⑦ tier-2 卡(強化可證偽性可見度)
- **渲染 `thesis.kill_condition`**(算了沒顯示)——可證偽性是 Phase 3 的靈魂,
  必須看得見;hover 或 foldout 皆可。
- 渲染逐卡 `caveats`;insider 區塊補 `net_value/note` tooltip。
- 排序預設 action 優先(BUY_DIP 置頂),現有表頭排序 JS(`render.py:423-437`)保留。

---

## 四、信任機制(把「校準的信任」做進 UI)

1. **證據連結**:兩個既有 fx foldout(`render.py:156-161,196-198`)內加
   「回測證據 →」連結;新增 `/evidence/<name>` 唯讀路由(token 保護,
   服務 `backtest/results/*.md` 渲染)——`_FACTOR_FORMULA` 字典
   (`render.py:37-43`)是逐因子連結的集中維護點。
2. **驗證標記**:每個規則帶 repo 紀律的 ✅/📄/⚠️ 標(如 credit 軸上線初期標 ⚠️
   直到面板重現三個歷史背離事件)。
3. **新鮮度 banner**:`asof` vs 今日的落差 >1 交易日就變黃;標注資料源
   (`df.attrs["source"]` 需從 data 層穿透到 payload——小改)。
4. **系統戰績條(依賴 Phase B ledger)**:近 30/90d 系統呼叫 vs SPY 的
   反事實對比——防自欺的終極機制,ledger 建成後第一個要接的 UI。

---

## 五、不要做的(防決策體驗劣化)

- **不要**把兩軸再合成一個「更聰明的」單一分數當主視覺——回到 finding #1 的坑。
- **不要**加盤中即時報價——資料節奏是日線,假即時感會誘發過度操作。
- **不要**在 UI 上把 F&G 缺資料時用其他指標補位假裝——寧可顯示「無資料」。
- **不要**破壞 read-only + token 架構(compute/serve 分離是部署穩定性的地基)。
- 欄位取捨原則:**渲染它,或從 payload 刪它**——殭屍欄位讓 schema 越長越難信。

## 六、實作順序建議

| 步 | 內容 | 依賴 |
|---|---|---|
| 1 | 決策條(gate+乾火藥開關)+ 新鮮度 banner | 無(資料已在 payload) |
| 2 | 前日快照載入 + 翻轉警示/差異 banner | 無 |
| 3 | 兩軸過渡版(用未渲染欄位拼)+ kill_condition/caveats 渲染 | 無 |
| 4 | F&G fetch 進 run_scan → 減碼開關 + 乾火藥計時器完整版 | 小 compute 改 |
| 5 | 兩軸完整版(credit 進風險軸)+ 證據連結路由 | P0-2 |
| 6 | 系統戰績條 | Phase B ledger |
