---
id: KARST-058
title: VIX 三個月指數換來源:免費來源自 2026-07-17 停更,改由 Cboe 官方歷史檔取數
type: task
createdAt: 2026-08-28
risk: low
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-057]
claimedBy: null
epic: V1 建置
deliverable: KARST-D03
---

## 工作內容

VIX 期限結構開關自此每個交易日都有訊號。KARST-040 發現 yfinance 的 ^VIX3M 自 2026-07-17 起無數據(指數本身 Cboe 每日照發布),^VXV 已消失;用戶 2026-08-28 追問(原話「VIX should have index which everyday is moving? Why only update to Jul. This is weird」)。範圍:宏觀來源適配器為 ^VIX3M(及 ^VIX 作對照)加第二個來源——Cboe 官方免費歷史 CSV,序列代號不變只換來源代號;兩來源重疊期逐日對數,差異列表;宏觀快照重抓後 2026-07-17 之後有數。若 Cboe 檔亦要鑰匙或不可得,在票上舉手並列替代(VIX 期貨 VX 連續合約)。

## 驗收條件

- [ ] ^VIX3M 序列 2026-07-18 至最近交易日有數,來源代號記明 Cboe
- [ ] 兩來源重疊期逐日對照表落檔,差異在合理範圍(寫明取值理由)
- [ ] 宏觀快照經唯一入口重新登記,VIX 期限結構驅動器重跑一次示例,既有測試全過

## 結果

## 留言
