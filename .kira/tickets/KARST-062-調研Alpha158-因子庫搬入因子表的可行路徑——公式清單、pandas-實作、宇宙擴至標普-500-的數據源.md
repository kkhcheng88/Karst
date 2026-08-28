---
id: KARST-062
title: 調研:Alpha158 因子庫搬入因子表的可行路徑——公式清單、pandas 實作、宇宙擴至標普 500 的數據源
type: research
createdAt: 2026-08-29
risk: low
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-056]
claimedBy: null
closed: 2026-08-29
epic: V1 建置
deliverable: KARST-D03
---

## 工作內容

用戶 2026-08-29 提出(原話「I think we have consider to add Alpha 158 or 360 into the DB calculation first? … Quant Factor is worth to scan … Then TA?」);主 agent 建議先 158(360 是原始輸入非解釋性因子)。調研要答:(1) Alpha158 的 158 條表達式完整清單與分組(K 線形態、滾動統計、量價相關),每條在日線 OHLCV 上是否算得出;(2) 不安裝 qlib 的前提下,有沒有現成、授權可用的 pandas/numpy 實作可借(GitHub 查,依 business-first 原則),或表達式求值器要自寫多少;(3) 逐日算 158 因子 × 500 隻 × 12 年的算力與儲存估計,配現有因子表(日期×實體×因子版本);(4) 宇宙擴至標普 500 成分:免費日線來源(yfinance)覆蓋與成分歷史(避免存活者偏差的來源);(5) 因子檢視(逐因子 IC、分時期)在 Karst 現有 factor 檢視機制上要補什麼。輸出 research/2026-08-29-alpha158-feasibility.md,結論含建議路徑與建置票拆法。

## 驗收條件

- [x] 研究檔落檔,五問各有答案與出處
- [x] 建議路徑一句話可裁,附建置票拆法(每張一程)
- [x] 不動程式、不動庫

## 結果

研究檔:`research/2026-08-29-alpha158-feasibility.md`。五問結論:(1) Alpha158 共 158 條表達式,分 K 線形態(9 條)、價格、成交量、滾動窗口(28 種運算子 × 5 個窗口)四組,絕大部分只需日線 OHLCV,只有 VWAP 相關少數幾條需另補一項近似計算;(2) 沒有現成、授權清楚、脫離 qlib 的 pandas 套件可直接借用,但公式本身公開,務實做法是照抄公式定義自寫約 20–25 個滾動運算子函數,不裝整個 qlib;(3) 158 因子 × 500 實體 × 3,000 日 ≈ 2.4 億格,parquet 儲存估計數百 MB,pandas 向量化計算估計數分鐘至十餘分鐘,單機可承受;(4) 標普 500 成分歷史有免費維護中的 GitHub 數據集,但 yfinance 對退市代號覆蓋不穩定,擴容後退市股缺口依然存在,須依 D-026 標示;(5) 現有因子檢視畫面缺逐因子 IC 面板,建議自寫薄層直接對接因子表雙時間戳(knowledge_time 為軸),不整套引入 alphalens(其輸入形狀假設單一時間戳)。建議路徑與建置票拆法(四張,每張一程)已寫入研究檔第六節。

## 留言
