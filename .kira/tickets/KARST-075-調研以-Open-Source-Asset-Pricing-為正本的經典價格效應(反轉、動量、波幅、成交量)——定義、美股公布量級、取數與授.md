---
id: KARST-075
title: 調研:以 Open Source Asset Pricing 為正本的經典價格效應(反轉、動量、波幅、成交量)——定義、美股公布量級、取數與授權、Karst 要補什麼
type: research
createdAt: 2026-08-29
risk: low
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-074]
claimedBy: agent:KARST-075-research
epic: V1 建置
deliverable: KARST-D03
---

## 工作內容

用戶 2026-08-29 裁決(原話「2. 學術界的美股因子庫 … I am more interested in this. I think most Quant is not working is actually meaning the pure price related TA is not able to predict the future?」並重申對周度反轉、月度成交量/波幅異常、3–12 個月動量四類效應「still very interested」)。本票答:(1) OSAP(openassetpricing.com):數據授權(官網條款原文)、三種取數方式實跑一次(pip openassetpricing 或直接下載)、提供什麼——訊號層(firm-level characteristics,是否要 CRSP permno、免費部分有多少)與組合回報層(long-short portfolio returns);(2) 四類效應在 OSAP 的準確訊號名與定義(例如 Mom12m、Mom6m、STreversal、IdioVol3F、IdioRisk、VolumeTrend、High52、MaxRet、RealizedVol、DolVol 等),逐條列:公式、只需價量還是要財務數據、OSAP 公布的美股多空組合年化回報與 t 值、樣本期;(3) 補 JKP 同名因子作第二對照(注意 CC BY-NC);(4) Karst 要補什麼:月度節奏(engine.contracts.CADENCES 現有哪些)、橫斷面分組多空組合回報這種量法(與現有逐日 IC 的分別)、因子表能否直接承載月度因子(雙時間戳照舊)、宇宙(標普 500 歷史成分 625 隻夠不夠,文獻多用全市場);(5) 結語:建議先算哪 6–10 條純價量經典訊號、以 OSAP 公布回報作核對的做法、建置票拆法(每張一程)、實測前向用戶交代的預期量級(逐條給數字與出處)。輸出 research/2026-08-29-osap-classic-anomalies.md。不動程式、不動庫。

## 驗收條件

- [ ] 研究檔落檔,五問各有答案與出處;OSAP 取數實跑一次並記錄
- [ ] 四類效應逐條有定義、只需價量與否、公布量級與樣本期
- [ ] 建議路徑與建置票拆法;不動程式、不動庫

## 結果

## 留言
