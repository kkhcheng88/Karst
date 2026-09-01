---
id: KARST-146
title: 帳目數據線建置(用戶裁決 D-123 第 1 條):美國證監會 companyfacts 全宇宙下載(標普 500 歷史成分 1,209 家,含已除牌)→ 逐月知情時點面板(每個月底只用該日之前已申報的數字,零偷看)→ 十一個核心欄位覆蓋率報告;只建數據不做任何選股測試,四件套實測另開下一張票
type: task
createdAt: 2026-09-02
risk: low
model: opus
fits: yes
dependsOn: []
claimedBy: null
deliverable: KARST-D02
---

## 工作內容

要做的事:把「公司成績表」數據砌成可以放心回測的面板,令四件套過濾器(盈利能力、投資紀律、行內價值、修訂延續)第一次有機會被實測。①**宇宙**:標普 500 歷史成分 1,209 家(名單與 ticker↔CIK 對照表在 experiments/2026-09-01-stock-oracle-curve/ 與 experiments/2026-09-02-tenbagger-casecontrol/ 已有,先 Glob 找,不重砌);已除牌公司照下載,拉不到 CIK 的逐家列出。②**來源**:data.sec.gov/api/xbrl/companyfacts/CIK##########.json,每秒最多 10 個請求,必帶 User-Agent(公司名+電郵 kaho.career@gmail.com),失敗重試上限寫死;原始 JSON 落 experiments/2026-09-02-fundamentals-panel/data/secfacts/(預估約 2GB,整個 data/ 目錄 .gitignore 擋住)。③**抽取**:沿用 experiments/2026-09-02-tenbagger-casecontrol/fetch_fundamentals.py 已跑通的十一個欄位(revenue, gross_profit, net_income, diluted_shares, cfo, capex, assets, liabilities, equity, cash, lt_debt)與其標籤回退表;740 家的自訂標籤變化是本票最大未知——每個欄位每年報「有數 / 無數 / 只有自訂標籤」三格覆蓋率,不准為湊覆蓋率而放寬回退規則。④**知情時點規則(本票核心,寫在跑數前並獨立 commit)**:每個數字帶 filed(申報日)與 end(期末日);月底 m 的面板值 = filed ≤ m 的最新一期數字,絕不用 end ≤ m(那是偷看,KARST-140/145 兩次踩過)。同一期被後來申報修訂的數字,面板用「當時看到的第一版」,修訂版另存一欄;流量欄(revenue/net_income/cfo/capex)同時提供最近四季滾動和;年報季報混報時季度化規則寫明。⑤**輸出**:experiments/2026-09-02-fundamentals-panel/out/panel_monthly.parquet(大檔不入 git)+ meta.json(覆蓋期、家數、每欄覆蓋率)+ coverage_by_year.csv;建置報告 research/2026-09-02-帳目面板建置.md,結論首段用白話答三件事:面板覆蓋幾多家幾多年、哪些欄位靠得住哪些靠不住、已除牌公司補回幾多家。⑥**誠實聲明必寫**:證監會檔案庫只補回已除牌公司的**帳目**,它們的**股價**仍然沒有(免費來源查過的照列),所以倖存者缺口只修了一半——四件套實測時已除牌公司仍然只能用「當時存在但無法交易」的方式處理,或另開價格來源票;本票不解這一格,但要把「已除牌且有帳目但無價格」的家數數出來。⑦不做任何選股、排序、回測、訊號;不碰四件套定義(參數對齊留給下一張票)。

## 驗收條件

- [ ] 知情時點規則(filed ≤ 月底、首版優先、季度化規則)寫成 RULES.md 並在任何面板數字產生前獨立 commit;下載覆蓋家數、CIK 缺失名單、失敗重試紀錄寫入 meta.json
- [ ] 十一個欄位逐年覆蓋率報告(有數/無數/只有自訂標籤)落 coverage_by_year.csv,並在報告用白話指出哪些欄位靠得住;無為湊覆蓋率放寬回退
- [ ] 已除牌公司補回家數、以及「有帳目無價格」家數,兩個數寫入報告首段;免費價格來源查過的逐一列出
- [ ] 面板 parquet 與原始 JSON 全部由 .gitignore 擋住不入 git;生產庫(倉根 C:\projects\Karst\karst.sqlite)全程只讀,SHA256 首 16 位維持 b168e9f45b578cf9;報告落 research/2026-09-02-帳目面板建置.md

## 結果

## 留言
