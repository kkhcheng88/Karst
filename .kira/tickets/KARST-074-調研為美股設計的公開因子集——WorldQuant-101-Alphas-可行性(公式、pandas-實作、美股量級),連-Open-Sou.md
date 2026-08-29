---
id: KARST-074
title: 調研:為美股設計的公開因子集——WorldQuant 101 Alphas 可行性(公式、pandas 實作、美股量級),連 Open Source Asset Pricing / JKP 月度因子庫的取用方式
type: research
createdAt: 2026-08-29
risk: low
model: opus
fits: 一程
approvalRequired: false
dependsOn: []
claimedBy: null
epic: V1 建置
deliverable: KARST-D03
---

## 工作內容

用戶 2026-08-29 問(原話「whether anyone made the quant factor set which is good for US Stock? if not Qlib?」),主 agent 口頭答 WorldQuant 101、Open Source Asset Pricing、JKP、Fama-French,建議先加 WorldQuant 101。本票核實:(1) WorldQuant 101 Alphas(Kakushadze 2016, arXiv 1601.00991):101 條公式是否全部只需日線 OHLCV(哪些要 VWAP、行業分類 indneutralize、市值),原文報的美股持有期與表現量級;(2) GitHub 上不依賴 qlib 的 pandas/numpy 實作(搜 alpha101、worldquant 101 pandas),星數、授權、最後更新、公式正確性口碑,可否借用;(3) 算力估計(101 條 × 625 實體 × 2,900 日)與現有因子值批次存法是否直接可用;(4) Open Source Asset Pricing(openassetpricing.com)與 JKP 因子庫(jkpfactors.com):授權、下載方式、美股覆蓋、哪些訊號只需價量、對 Karst 的用法(對照基準 vs 自算);(5) 結語:建議路徑一句可裁 + 建置票拆法(每張一程),以及在實測前要向用戶交代的「預期量級」一句。輸出 research/2026-08-29-us-factor-sets.md,每條 URL/DOI。不動程式、不動庫。

## 驗收條件

- [ ] 研究檔落檔,五問各有答案與出處
- [ ] 建議路徑一句可裁,附建置票拆法與實測前預期量級
- [ ] 不動程式、不動庫

## 結果

## 留言
