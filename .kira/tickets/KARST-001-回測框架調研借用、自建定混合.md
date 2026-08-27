---
id: KARST-001
title: 回測框架調研:借用、自建定混合
type: research
createdAt: 2026-08-25
risk: low
model: opus
fits: 一程
approvalRequired: false
dependsOn: []
claimedBy: KARST-001-researcher
epic: V1 藍圖
deliverable: KARST-D01
closed: 2026-08-25
---

## 工作內容

要答的事實問題:GitHub 上現成的回測/紙上交易方案(至少覆蓋 vectorbt、backtrader、zipline-reloaded、NautilusTrader、QuantConnect Lean、qlib、backtesting.py,及任何帶完整 UI 的開源交易平台)各自對 Karst 的核心需求覆蓋到什麼程度——(1) 多策略共存;(2) 自定量化因子(含由非結構化材料轉成的因子)接得入;(3) 換倉節奏由策略自訂;(4) 單一定義資料層親和度;(5) 紙上交易/排程運行;(6) 矩陣式(向量化)性能與蒙地卡羅模擬,一秒可模擬大量交易(D-002);(7) 蠟燭圖 UI 連出入場標記,或可嵌入自家應用(如 TradingView lightweight-charts 一類圖表件)(D-002);(8) 橫斷面選股與組合層回測/優化是主場景——不是單股入場時機優化,不做日內(D-006),主打 tick 級執行細節的方案要按此降權。這條問題現正擋住「Karst 借用現成框架、自建、定混合」的架構決定(D-005 明令先查 GitHub、不預設自建)。

## 驗收條件

- [x] 每個候選方案有逐項對照上述七項需求的評估表,附 repo 連結與文件出處
- [x] 維護活躍度(近一年 commit、star、issue 回應)有記錄
- [x] 有明確建議(借用/自建/混合)連理由與風險,但明寫最終由用戶裁決
- [x] 報告落檔於倉內 research/ 目錄並在票的結果引用路徑

## 結果

調研 21 個開源方案後,建議走**混合**路線:引擎借用、語意層與介面自建。首選以 vectorbt 或 PyBroker 作向量化組合模擬核心(兩者需先短期併行試跑再定案),組合層優化借 Riskfolio-Lib、因子檢定借 alphalens-reloaded、蠟燭圖借 TradingView lightweight-charts;因子合約與單一定義資料層、非結構化轉因子管線、策略註冊、應用介面則必須自建。沒有任何現成方案可以整套搬過來:帶完整 UI 的開源平台幾乎全部是加密貨幣機器人,而 zipline-reloaded(近一年僅 4 次 dependabot commit)與 backtrader(2024-08 後零 commit)已不宜作地基。最重要的一項發現是授權:vectorbt 與 PyBroker 兩個性能最合用的候選都帶 Commons Clause,不容許售賣主要價值源自它的產品或服務——因此「Karst 將來會否商品化」這個商業問題,決定了引擎選型是走 vectorbt/PyBroker 抑或改投 qlib(MIT)/ Lean(Apache-2.0)。**最終由用戶裁決。**

報告:`research/2026-08-25-backtest-frameworks.md`

## 留言

### human:Kaho · 2026-08-27 23:09
交付品「Karst v1 規格」（KARST-D01）已簽收。

**簽收人留言**：用戶 2026-08-27 於原生多選介面勾選簽收
