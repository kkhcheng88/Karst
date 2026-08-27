---
id: KARST-020
title: 數據架構:defeatbeta+yfinance 免費源接入、儲存形態(duckdb 與否)、數據快照版本化
type: grilling
createdAt: 2026-08-27
risk: medium
model: opus
fits: 一程
approvalRequired: false
dependsOn: []
claimedBy: null
epic: V1 建置
deliverable: KARST-D02
closed: 2026-08-27
---

## 工作內容

要人拍板的問題:v1 數據層怎樣搭——(一)defeatbeta 與 yfinance 各負責哪些數據(價格/除權除息/基本面/逐字稿/財報日曆),兩者重疊時以誰為準;(二)儲存形態:沿用 defeatbeta 自帶的 duckdb、還是抽出成自家 parquet/sqlite 一類,單一定義庫與數據快照放同一庫還是分開;(三)數據快照如何版本化(D-021 第 8 條要求可追):整批快照定期凍結、還是按來源增量加版本;(四)退市股與存活者偏差:免費源覆蓋不到時,回測報告怎樣標明;(五)日後加其他免費來源的接口形態。為什麼自己答不到:用戶明言(D-025 原話)要先看 KarstETF 舊倉用法再談架構,儲存與版本化的取捨牽涉他日後維護與擴展的意願。前置事實:research/2026-08-27-karstetf-data-layer-facts.md(KarstETF 數據層用法)與 research/2026-08-27-us-daily-data-providers.md(供應商現況)。

## 驗收條件

- [x] 五項各有裁決,構成持久決定的部分已落決策簿
- [x] 行情數據接入票(建置第一批第 7 張)的範圍據此定稿
- [x] 新詞入 CONTEXT.md

## 結果

· 2026-08-27 23:40 一輪追問四題,落 D-026:parquet 存數據快照、sqlite 存定義與登記(用戶交由按性能與擴展性建議);實體編號主鍵連代號歷史映射(回應 GOLD 事故);每次拉數一個快照編號;照舊倉只存已調整價(後果明記);分工 yfinance 價格、defeatbeta 基本面與逐字稿,單一管線單一快取根;存活者偏差前向累積宇宙歷史並在報告標明;新來源以適配器接入。KARST-027 範圍據此定稿可開工。詞彙表加實體編號、數據快照。事實依據:research/2026-08-27-karstetf-data-layer-facts.md、research/2026-08-27-us-daily-data-providers.md。

## 留言
