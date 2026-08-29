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
closed: 2026-08-29
epic: V1 建置
deliverable: KARST-D03
---

## 工作內容

用戶 2026-08-29 問(原話「whether anyone made the quant factor set which is good for US Stock? if not Qlib?」),主 agent 口頭答 WorldQuant 101、Open Source Asset Pricing、JKP、Fama-French,建議先加 WorldQuant 101。本票核實:(1) WorldQuant 101 Alphas(Kakushadze 2016, arXiv 1601.00991):101 條公式是否全部只需日線 OHLCV(哪些要 VWAP、行業分類 indneutralize、市值),原文報的美股持有期與表現量級;(2) GitHub 上不依賴 qlib 的 pandas/numpy 實作(搜 alpha101、worldquant 101 pandas),星數、授權、最後更新、公式正確性口碑,可否借用;(3) 算力估計(101 條 × 625 實體 × 2,900 日)與現有因子值批次存法是否直接可用;(4) Open Source Asset Pricing(openassetpricing.com)與 JKP 因子庫(jkpfactors.com):授權、下載方式、美股覆蓋、哪些訊號只需價量、對 Karst 的用法(對照基準 vs 自算);(5) 結語:建議路徑一句可裁 + 建置票拆法(每張一程),以及在實測前要向用戶交代的「預期量級」一句。輸出 research/2026-08-29-us-factor-sets.md,每條 URL/DOI。不動程式、不動庫。

## 驗收條件

- [x] 研究檔落檔,五問各有答案與出處
- [x] 建議路徑一句可裁,附建置票拆法與實測前預期量級
- [x] 不動程式、不動庫

## 結果

1. WorldQuant 101 Alphas 不是純 OHLCV 因子集:101 條裡 26 條要行業中性化(indneutralize)、逾 12 條要 VWAP,論文報平均持有期 0.6–6.4 天、平均兩兩相關性 15.9%,逐條 Sharpe 數字未能從公開來源取得。
2. GitHub 現成 pandas 實作沒有一個「星數高、授權清楚、近年仍維護」三樣齊全(862 星那個無授權聲明、5 年多沒更新;MIT 授權的兩個裡星數低或同樣多年沒更新),結論與 Alpha158 調研一致:照抄公式自寫,不依賴任何一個現成套件。
3. 算力量級比 Alpha158 更輕:101 條 × 625 隻 × 約 2,900 日 ≈ 1.83 億格(Alpha158 是 2.37 億格),沿用 D-032 的 parquet 落地方式,預期落在 Alpha158 實測時間的七至八成。
4. Open Source Asset Pricing(MIT 授權、逾 200 個月度特徵)與 JKP(數據 CC BY-NC 4.0 非商用、153 個月度特徵)都覆蓋美股,但頻率是月度、多數特徵要財務報表,只適合當對照基準庫,不適合取代日線量價因子生產線。
5. 建議路徑:101 Alphas 排在 Alpha158 建置線之後,待有餘力再開;沒有查到 101 Alphas 本身在美股大盤股上的公開 IC 數字,實測前只能類比 Karst 自家 Alpha158 標普 500 實測(158 條沒有一條 |IC 均值| 達 0.02)設定「多數條目訊號薄弱」的心理預期,並標明這是類比推論非直接出處。

## 留言
