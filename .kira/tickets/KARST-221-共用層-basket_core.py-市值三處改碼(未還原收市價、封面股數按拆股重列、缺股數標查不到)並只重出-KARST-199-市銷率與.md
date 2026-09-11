---
id: KARST-221
title: 共用層 basket_core.py 市值三處改碼(未還原收市價、封面股數按拆股重列、缺股數標查不到)並只重出 KARST-199 市銷率與市帳率兩條事前特徵核「估值平者勝」結論是否成立;其餘舊表加一行標註不重出
type: task
createdAt: 2026-09-12
risk: low
model: sonnet
fits: KARST-219 舉手裁決(改碼 + 只重出 199 兩條);修法與驗證個案已在 research/2026-09-methodology/2026-09-12-暴露差異模組v1/fix_mcap.py 與 修復——mcap_usd.md;199 的「分得開的是估值(市銷率平者勝)」是被引到結論層的唯一市值衍生數
dependsOn: []
claimedBy: null
epic: 方法論期(D-166)
deliverable: KARST-D04
---

## 工作內容

一、改碼:找出 basket_core.py(Grep research/ 與 strategy/tools/),按 fix_mcap.py 的修法改三處——價格改用未除息還原的收市價(data/prices/daily/ 的 close 而非 adj_close)、封面股數按拆股表重列(拆股表若不在 data/ 則用 fix_mcap.py 已用的來源並寫明)、缺股數者 mcap_usd 標 NaN 並加 mcap_status 欄;改前備份;以 218/219 驗證個案(NVDA 2024-08-01、AT&T 2013-05-21 等)重跑核對誤差為零。二、重出 199:用修後市值重算 2026-09-10-①行業殺錯事件籃子/ 的市銷率(EV/S 或 P/S,照原口徑)與市帳率兩條事前特徵對十二個月結果的分組(照原腳本 feature 分析的三分位做法),另存 *_mcap修正.csv 與一頁對照(修前/修後分組中位、結論有沒有變);原檔不改。三、標註:在 204 checklist_test、210、212–214 三批、218 的總覽檔尾各加一行「市值欄(mcap_usd)含 2026-09-12 前舊值,經 KARST-219 查證不影響本檔結論;修正值見 2026-09-12-暴露差異模組v1/mcap修正/」——用 Edit 只加行不改原文。含中文檔案只用 Read/Write/Edit;Python 一律 PYTHONUTF8=1;不改 karst/ library/ strategy/tools/;不 commit。

## 驗收條件

- [ ] basket_core.py 三處改碼,備份在,驗證個案誤差為零,重跑腳本可用
- [ ] 199 兩條特徵修前修後對照落檔,結論有沒有變寫明
- [ ] 受影響檔尾標註一行各加齊;含中文檔案只用 Read/Write/Edit;Python 一律 PYTHONUTF8=1;不 commit

## 結果

## 留言
