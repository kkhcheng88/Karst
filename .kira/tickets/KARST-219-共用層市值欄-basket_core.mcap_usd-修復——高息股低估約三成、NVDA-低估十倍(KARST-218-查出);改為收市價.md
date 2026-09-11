---
id: KARST-219
title: 共用層市值欄 basket_core.mcap_usd 修復——高息股低估約三成、NVDA 低估十倍(KARST-218 查出);改為收市價 × 最近申報流通股數(拆股調整),單元驗證兩類個案;列出引用過該欄的票(199/204/209/212–218)逐張標「數字要重核/不影響結論」
type: task
createdAt: 2026-09-12
risk: low
model: sonnet
fits: KARST-218 舉手第 1 件裁甲;共用層錯會擴散到每張下游票;D-172 已取消市值閘故短期無交易損失,但 209 籃子表、216/218 財務簡篩與重疊度、199 籃子成員描述都印過市值
dependsOn: []
claimedBy: null
epic: 方法論期(D-166)
deliverable: KARST-D04
---

## 工作內容

先讀 research/2026-09-methodology/2026-09-12-暴露差異模組v1/check_mcap.py 與 raise_mcap.json 看查出的個案與根因;找 basket_core.mcap_usd 的產生腳本(Grep research/ 與 strategy/tools/,可能在 2026-09-10-①行業殺錯事件籃子/build_events.py 或 199 的 basket 建置腳本),查明錯在哪(股數欄取錯標籤、未拆股調整、用了 float 而非 outstanding、或價格日錯配)。修法:市值 = 該日收市價 × 最近一份 10-Q/10-K 的流通股數(dei:EntityCommonStockSharesOutstanding,拆股按 data/ 拆股表調整),取數用 strategy/tools/implied_expectations.py 取數層(只讀);單元驗證:高息股(AT&T、ConEd、Simon 等 218 點名者)與 NVDA 修前修後對比 yfinance 同日市值,誤差寫明。回溯:Grep 全部 research/ 檔引用 mcap_usd 的地方,列表逐張票標「數字要重核」或「不影響結論」附理由(例如 D-172 後市值不作閘、財務簡篩用的是現金流與營收非市值)。落檔同目錄 修復——mcap_usd.md 與腳本;不改既有輸出檔本身(另存修正版);含中文檔案只用 Read/Write/Edit;Python 一律 PYTHONUTF8=1;不 commit。

## 驗收條件

- [ ] 根因寫明;修後市值對 yfinance 同日誤差表(含高息股與 NVDA)落檔
- [ ] 引用過 mcap_usd 的票逐張標重核/不影響附理由
- [ ] 不改既有輸出檔本身、karst/ library/;含中文檔案只用 Read/Write/Edit;Python 一律 PYTHONUTF8=1;不 commit

## 結果

## 留言
