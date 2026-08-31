---
id: KARST-125
title: 補充勘察:逐季「公布前共識」做季度 PIT 前瞻分母——Futu 業績頁與 defeatbeta/yfinance 有冇貨(用戶指路)
type: research
createdAt: 2026-08-31
risk: low
model: opus
fits: yes
dependsOn: []
claimedBy: null
deliverable: KARST-D02
---

## 工作內容

要答的事實問題(現正擋住倍數情緒儀的分母設計,KARST-121 勘察的補充):美股逐季業績「公布前夕的分析員共識」(estimate vs actual 嗰個 estimate)有邊個免費源攞得到、攞到幾深歷史?攞得到即係一種季度頻率的 point-in-time 前瞻分母——比每日存檔粗,但歷史深、免費,係 KARST-121 冇掘到嘅一格。三條線索逐條核實:(1) Futu 業績預測頁(例 https://www.futunn.com/hk/stock/AXTI-US/earnings,欄目有營收/淨利潤/每股收益/息稅前利潤)——已公布季度顯示嘅「預測」值係咪公布前夕共識快照?定係而家先倒填?歷史顯示到幾多季/幾多年?覆蓋美股幾廣?公開 HTML 定要登入/app 先睇到?服務條款可唔可以程式化抓取(唔可以就明寫,唔好蠱惑抓)?(2) defeatbeta-api(倉內 KARST-020 已接嘅免費源,數據住喺 Hugging Face)——有冇 earnings estimate 類表?實際裝嚟攞一兩隻股樣本驗證欄位與深度。(3) yfinance 嘅 earnings_history(epsEstimate vs epsActual)與 earnings_estimate/analyst 端點——每隻股顯示幾多季歷史?estimate 係當時值定事後修訂值(關鍵判項,搵證據唔好靠估)?每源照 KARST-121 格式記:覆蓋層級、指標、頻率、起始深度、point-in-time 與否、費用、取數方式、條款風險。收尾一句明判:「季度 PIT 前瞻分母做唔做得成、用邊個源、歷史幾深」。樣本數據與驗證腳本落 experiments/2026-08-31-quarterly-consensus/,大檔不入 git。純數據勘察,不落策略結論、不改策略碼。

## 驗收條件

- [ ] 三條線索(Futu 頁、defeatbeta、yfinance)逐條有明判:估值係咪公布前夕快照(附證據,唔准靠估)、歷史深度、覆蓋、取數方式、條款風險
- [ ] 至少一源有實際樣本數據驗證過欄位,腳本與樣本落 experiments/2026-08-31-quarterly-consensus/
- [ ] 收尾一句明判:季度 PIT 前瞻分母做唔做得成、用邊個源、歷史幾深;做唔成都要寫明點解
- [ ] 結論落檔 research/2026-08-31-季度共識來源勘察.md

## 結果

## 留言
