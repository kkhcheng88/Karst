---
id: KARST-195
title: 隱含預期計算器取數六缺陷統一修復——稀釋股數當流量按季拆、債務標籤漏信貸額度/可轉債/有抵押債、現金與投資標籤過窄且不核申報日、合計標籤同時入流動與非流動兩桶、現金標籤前綴未涵蓋、融資租賃整筆漏計;另加報表新鮮度核對(對 EDGAR 申報清單,落後即拒絕輸出)與收市價核對(最後一根日線未收市則退回上一交易日);修後對六十家機械重跑出前後差異
type: task
createdAt: 2026-09-09
risk: low
model: opus
fits: KARST-188 舉手第 5、6、7 項;假設冊 A-049、A-053、A-054、A-055、A-056、A-059;第二輪外部評論「先做一次有限的資料修復,再開下一個策略版本」
dependsOn: []
claimedBy: null
deliverable: KARST-D04
---

## 工作內容

對象 strategy/tools/implied_expectations.py 與 README.md。必須建基於 KARST-193 之後的版本(折現率已改逐家 WACC 配 FCFF、_meta、四情境表),不得倒退。六處缺陷的一手證據與本地修法全在 research/2026-09-methodology/2026-09-09-①候選池全量/(run_60_full.py 內的本地覆寫、check_finance_lease.py、check_bs_staleness.py、finance_lease_gap.csv、bs_staleness.csv、facts-*.md、B-RMBS 與 B-CRNC 卡片),先讀這些再改工具,把本地修法搬進共用工具而不是重新發明。逐項:(一)稀釋股數用 instant 取最近一期,不按季拆流量;(二)債務標籤有序清單加 LineOfCredit、ConvertibleNotesPayable、SecuredDebt、LongTermDebtAndCapitalLeaseObligations 等(以 188 的 facts-*.md 核出的實際標籤為準),並印出每家用了哪個標籤;(三)現金與投資標籤加前綴變體並核申報日在價格日前 200 日內,否則標「過期」並印警告;(四)合計標籤與分項標籤互斥——若已取 total 就不再加流動/非流動分項,反之亦然;(五)融資租賃負債(FinanceLeaseLiability 流動+非流動,或合計)計入有息負債,經營租賃照舊分開列;(六)報表新鮮度:由 SEC submissions 端點或 data/sec 索引取該公司最近 10-Q/10-K 申報日,若 companyfacts 最新資產負債表期末日早於最近申報所涵蓋期末,標「資料落後」並在輸出拒絕給基準值(只給警告),README 寫明;(七)收市價核對:yfinance 最後一根日線若日期為今日且美股仍在交易時段(按美東時間判),退回上一交易日收市,並在 _meta 記價格日與「是否收市價」。修後對 KARST-188 的六十家(screen60_full.csv 名單)機械重跑三個數,出前後差異表(淨負債、基準每股值、隱含增速、賠率、過不過負債閘、過不過底線)並標結論翻轉的家數與名單;不改十四張卡的文字。README 末更正紀錄;假設冊 A-049/053/054/055/056/059 按結果改狀態附證據。

## 驗收條件

- [ ] 六處缺陷各有修法與單元級驗證(以 188 卡片核出的個案為測試:ORCL 債務、RMBS 雙計、CRNC 現金、DOCN 融資租賃、CLVT 淨負債、稀釋股數一例),修後數字與一手 10-Q 對得上
- [ ] 報表新鮮度與收市價兩項核對加入,_meta 記錄;落後或未收市時的行為在 README 寫明
- [ ] 六十家前後差異表落檔,標結論翻轉家數與名單;假設冊六條狀態更新附證據
- [ ] 建基於 KARST-193 版本、JSON 只加欄不刪欄、舊呼叫方式仍可跑;不改 karst/、library/、候選卡文字;含中文檔案只用 Read/Write/Edit;Python 一律 PYTHONUTF8=1;不 commit

## 結果

## 留言
