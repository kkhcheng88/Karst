---
id: KARST-254
title: S2 證券價格序列 module(架構候選一):身份核對、口徑、交易時段、歷史門檻與增量接駁單一入口
type: task
createdAt: 2026-09-23
risk: high
model: opus
fits: 一程:bars 模組加深及六個呼叫點改接,測試改經新 interface
dependsOn: []
claimedBy: null
epic: 根基重整
deliverable: KARST-D12
---

## 工作內容

依執行計劃 §三 2 及 2026-09-23 架構評審候選一。現況:service.plan_update／render_charts／_publication_bars、daily 兩處、workflow 各自拼裝日曆與口徑,並讀取私有 bars._basis;身份過濾只在 workflow;歷史門檻三套(daily 200 根、出圖 2 根、發布 0.9)。把這些收進 bars 模組的一個入口,呼叫方只問「給我某證券截至某時的序列及其是否足夠某用途」。門檻按用途命名、單一出處。不改現有序列數值與完成狀態語義(KARST-250 規則保持)。程式只住 karst/,不寫一次性腳本。

## 驗收條件

- [ ] karst/ 內不再有 bars 模組以外的地方呼叫 _basis 或自行拼裝交易時段
- [ ] 證券身份核對由序列入口統一執行,六個呼叫點全部經它
- [ ] 歷史足夠門檻按用途命名並只有一處定義
- [ ] 既有 bars／charts／daily／publish 測試全部通過,新 interface 有定向測試覆蓋身份不符、歷史不足、增量接駁
- [ ] 已發布研究重建序列的數值與重構前逐值相同(以既有 fixture 驗)

## 結果

## 留言
