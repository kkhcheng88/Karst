---
id: KARST-082
title: 代號歷史對照(A-011 善後):標普 500 歷史成分的代號→實體錨改用帶生效期的對照,已回收代號(如 BBBY)不再錨到今日的另一家公司;受影響快照重凍並列出差異
type: task
createdAt: 2026-08-29
risk: medium
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-076]
claimedBy: null
epic: V1 建置
deliverable: KARST-D03
---

## 工作內容

源自假設 A-011 崩塌(KARST-076 實測:SEC company_tickers.json 只講代號今日屬誰,BBBY 現解到 NEIGHBORHOOD INTELLIGENCE 而不是 Bed Bath & Beyond,而 BBBY 在標普 500 歷史成分範圍內)。完成後:(1) 代號→CIK 的錨定對歷史成分改用帶歷史公司名的來源(SEC cik-lookup-data.txt,1,057,117 行,保留歷史名;比對規則寫明,前綴雜訊要人手辨的代號列成清單而不是靜靜猜);(2) 對照表本身帶生效起訖日,同一代號不同時期可指向不同實體,與 D-026「交易代號只是有生效期的屬性」一致;(3) 跑一次現有標普 500 歷史成分快照 2026-08-28-493fd1df1cb9 的 625 個實體,列出錨改變了的代號(哪個、由誰改到誰),落 experiments/2026-08-29-ticker-history/README.md;(4) 錨有改變即按等價重用規矩重凍快照,新舊快照編號並列寫入同一 README,舊快照不刪;(5) A-011 條目補一句指向本票的善後結果。不改因子批次(重凍後由後續票重入)。只跑所涉測試檔;含中文檔案只用 Read/Write/Edit;不建目錄連結指向 data/;不用 8765 埠。

## 驗收條件

- [ ] 代號對照帶生效期,BBBY 在 2015–2023 期間解到 Bed Bath & Beyond(CIK 886158)
- [ ] 625 個實體逐個核對結果落檔,錨改變清單與人手待辨清單分開列
- [ ] 錨有變則新快照已凍、新舊編號並列;A-011 條目已補善後指向;只跑所涉測試檔

## 結果

## 留言
