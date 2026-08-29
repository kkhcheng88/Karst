---
id: KARST-073
title: 行業 ETF 宇宙:SPDR 十一隻行業 ETF(XLK 一族)登記宇宙名單、凍結十二年日線快照並入 Alpha158 因子值批次;因子 ETF 快照亦入批次
type: task
createdAt: 2026-08-29
risk: low
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-068]
claimedBy: null
epic: V1 建置
deliverable: KARST-D03
---

## 工作內容

用戶 2026-08-29 裁決要測「XLK and related series of industrial ETF, and the 4 S&P factor ETF」。本票只做數據準備,不做實測(實測票等 KARST-072 文獻結論向用戶交代後才開)。範圍:(1) 宇宙名單登記新增「SPDR 行業 ETF」:XLK、XLF、XLE、XLV、XLI、XLY、XLP、XLU、XLB、XLRE(2015-10 起)、XLC(2018-06 起),連 SPY 作主日曆錨,成立日期照登記;(2) 經唯一入口凍結 2015 年起日線快照,較遲成立的兩隻照 D-026 標示起始缺口;(3) 以 karst factor ingest-alpha158 把該快照與既有因子 ETF 快照 2026-08-28-000b4820a23a(SPY、QQQ、QUAL、VLUE、MTUM、USMV)各入一批 Alpha158 因子值;(4) experiments/snapshot_ids.py 加編號;結果落 experiments/2026-08-29-sector-etf-universe/(README、行數、缺值比例)。karst verify 清白。不加參數預設值;只跑所涉測試檔。

## 驗收條件

- [ ] 宇宙名單登記有「SPDR 行業 ETF」,唯一入口列得出;快照凍結,兩隻較遲成立的起始缺口照 D-026 標示
- [ ] 行業 ETF 快照與因子 ETF 快照各有 Alpha158 因子值批次,行數與缺值比例落檔;karst verify 清白
- [ ] snapshot_ids.py 已加編號;只跑所涉測試檔

## 結果

## 留言
