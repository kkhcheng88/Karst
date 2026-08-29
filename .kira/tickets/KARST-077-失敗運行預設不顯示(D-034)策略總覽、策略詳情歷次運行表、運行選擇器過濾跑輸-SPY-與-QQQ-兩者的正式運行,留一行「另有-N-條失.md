---
id: KARST-077
title: 失敗運行預設不顯示(D-034):策略總覽、策略詳情歷次運行表、運行選擇器過濾跑輸 SPY 與 QQQ 兩者的正式運行,留一行「另有 N 條失敗運行」可展開
type: task
createdAt: 2026-08-29
risk: low
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-070]
claimedBy: null
epic: V1 建置
deliverable: KARST-D03
closed: 2026-08-29
---

## 工作內容

依 D-034(用戶 2026-08-29 裁決)。範圍:(1) 後端一個判定函數:正式運行在其期間的年化回報同時低於 SPY 與 QQQ 買入持有(同期間、同快照日曆)即失敗運行;基準序列缺其一則不判定(照列);(2) 總覽 API、策略頁 API、運行選擇器 API 加旗標與計數,預設過濾,查詢參數可要求全列;(3) 三處畫面預設不列失敗運行,底下一行「另有 N 條失敗運行」點開即展開列出並標示「失敗」;(4) 掃描格運行不受影響。用現有真數據核對:哪幾條正式運行被判失敗,落 experiments/2026-08-29-failed-runs/README.md。不加參數預設值(門檻就是「兩者皆低於」,不是可調參數);只跑所涉測試檔。

## 驗收條件

- [x] 判定函數有測試(三情形:跑贏其一、跑輸兩者、基準缺失)
- [x] ~~三處畫面預設不列失敗運行,展開行可見~~(D-040 改:不做展開行、不顯示計數;全部運行皆失敗的策略該行仍列出,成績留空、對基準一格顯示「N 條運行全部失敗」);真數據核對結果落檔
- [x] 掃描頁不受影響;只跑所涉測試檔

## 結果

依 D-034 定義失敗運行(年化回報同時低於 SPY 與 QQQ 買入持有,任一基準缺值不判),
`karst/web/data.py` 加 `is_failed_run` 純函數,`/api/overview`、`/api/strategy`、
`/api/strategy/runs` 三個端點都加上這個判定,失敗運行預設不列(不設展開行、不顯示
計數;`?all=1` 供核對用全列)。依 D-040 補充:一套策略若正式運行**全部**失敗,
總覽與策略詳情頁該策略/該運行表仍然列出——名稱、類型照顯示,成績留空,顯示
「N 條運行全部失敗(年化回報同時低於 SPY 與 QQQ 買入持有)。」

真實本機定義庫核對(`experiments/2026-08-29-failed-runs/README.md`):9 條可判
正式運行(另 2 條序列缺失、不判),8 條判定失敗——趨勢波段 7/7、因子混合
(ETF 版)1/1;因子輪動(ETF 版)1/1 不是失敗運行。三個觸及端點的測試檔全部
針對本機真實庫跑通(16 個測試,`test_web_data.py`/`test_web_overview.py`/
`test_web_strategy.py`)。掃描格運行(`SWEEP_RUN`)不受影響,判定與過濾只作用
於正式運行(`FORMAL_RUN`)。

## 留言

### agent:KARST-077-implementer · 2026-08-29 23:16
依 D-040(.kira/decisions.md 已記)改動本票第 (3) 項與驗收條件第 2 條:失敗運行在總覽、策略詳情、運行選擇器三處預設不列,**不做「另有 N 條失敗運行」展開行,亦不在正常情況顯示計數**——原驗收條件第 2 條「展開行可見」視為取消。後端判定函數(is_failed_run)、isFailed 旗標、?all= 查詢參數(可要求全列供核對)照票面保留。

同日 D-040 再補一句,修正上面那句「策略總覽若一條策略所有正式運行皆失敗,該策略整行不列」:改為該行**仍要列出**——名稱、類型照顯示,成績欄留空,對基準一格顯示「N 條運行全部失敗」;策略詳情頁的運行表在這情況下同樣空白、只顯示該計數。失敗運行本身仍不列、不可展開;失敗計數(failedCount)因此要保留並送到前端,只是不做展開行。

實作細節:api_overview.py 的 _pick_run 回三元組(record, is_active, all_failed),全失敗時 _strategy_row 略過 _fill_results、只填 note="N 條運行全部失敗(年化回報同時低於 SPY 與 QQQ 買入持有)。";api_strategy.py 的 /api/strategy/runs 端點回 failedCount,strategy.js 的 noFormalRunsRow() 依 S.failedCount 顯示同一句。真實庫核對見 experiments/2026-08-29-failed-runs/README.md:趨勢波段 7/7 可用運行判定失敗、因子混合(ETF 版) 1/1 可用運行判定失敗,因子輪動(ETF 版)不失敗。
