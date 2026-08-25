---
id: KARST-014
title: UI 外殼與圖表庫參考調研
type: research
createdAt: 2026-08-26
risk: low
model: opus
fits: 一程
approvalRequired: false
dependsOn: []
claimedBy: KARST-014-research
epic: V1 藍圖
deliverable: KARST-D01
closed: 2026-08-26
---

## 工作內容

要答的事實問題:做一個 TradingView/Futu 式的自用交易應用(D-002:蠟燭圖+進出場標記;D-010:虛擬籃子要畫到自己的蠟燭圖/淨值曲線;D-006:組合層檢視),開源世界有什麼現成件可借——圖表庫(lightweight-charts、TradingView charting library、ECharts、Plotly 一類)各自的授權(對照 D-007 自用先行、SaaS 門常開)、蠟燭圖+標記+疊加指標+多面板的能力、與 Python 後端接駁的形態;以及有沒有整個開源交易終端/回測 UI 外殼(OpenBB、QuantDinger 前端一類先例)值得整件借或只借思路。這條問題現正阻住 KARST-007(應用形態討論)——攞住實貨傾先具體。

## 驗收條件

- [x] 每個候選有:定位一句、授權、蠟燭圖與標記能力、接駁形態、可借判斷(整件/零件/思路/不可借連理由)
- [x] 對「虛擬籃子畫自己蠟燭圖」呢個自家需求逐個候選標可行性
- [x] 有一個明寫的建議組合,並明寫最終由用戶裁決(D-005)
- [x] 報告落檔 research/ 並在票的結果引用路徑

## 結果

· 2026-08-26 12:00 查了七個候選(TradingView lightweight-charts、TradingView Charting Library 閉源版、Apache ECharts、Plotly/Dash、OpenBB、QuantDinger 前端、vnpy),逐個核對授權原文、蠟燭圖與標記能力、接駁 Python 後端形態,以及對「虛擬籃子自繪合成蠟燭圖」(D-010)的可行性。建議組合:前端圖表層以 TradingView lightweight-charts 為主(Apache-2.0、原生 Candlestick+`createSeriesMarkers`標記+多 pane,授權最乾淨),Python 側(vectorbt)經薄 REST 層餵 JSON;若介面日後需要大量非金融統計圖表,評估搭配或換成 Apache ECharts(同級乾淨授權,一套通吃);TradingView Charting Library 閉源版因授權明文排除私人/內部用途,連候選資格都不具備,已排除;Plotly/Dash(MIT)是「Python 原生、免前後端協定」的更快替代路徑,代價是互動流暢度較弱;OpenBB、QuantDinger 前端、vnpy 三個開源終端外殼均不整件借,只借思路(OpenBB 已轉 AGPL,只借其分層設計;QuantDinger 前端禁商用,重申 KARST-010 結論;vnpy 為 MIT、Python 原生桌面圖表元件先例,留待 Web 殼或桌面殼裁決時參考)。最終選型由用戶裁決(D-005)。報告:[research/2026-08-26-charting-ui-references.md](../../research/2026-08-26-charting-ui-references.md)

## 留言
