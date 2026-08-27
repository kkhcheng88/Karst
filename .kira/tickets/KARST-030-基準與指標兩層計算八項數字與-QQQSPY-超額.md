---
id: KARST-030
title: 基準與指標兩層計算:八項數字與 QQQ/SPY 超額
type: task
createdAt: 2026-08-27
risk: medium
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-026]
claimedBy: null
epic: V1 建置
deliverable: KARST-D02
closed: 2026-08-28
---

## 工作內容

一次運行自此算得出策略卡四項與運行詳情四項共八項指標,並對 QQQ 與 SPY 各出一個超額數。範圍是指標計算這一層,取數只取已保存的逐日淨值與持倉序列,不重跑引擎;基準是純對照尺、不是策略(詞彙表 benchmark)。門面數字一律只取現役設定(active setup)那次運行,歷史最佳只可標明身份另列、視覺降級,不得冒充門面——目的是防參數擬合美化(D-020 第 8 條、規格 7.5)。

## 驗收條件

- [x] 由一次運行算得出策略卡四項與運行詳情四項,八個數字齊(D-020 第 8 條、規格 7.5)
- [x] 對 QQQ 與 SPY 各出一個超額數,基準走買入持有、不經策略路徑(規格 7.5、詞彙表 benchmark)
- [x] 門面數字取的是現役設定那次運行;換一個現役設定,門面八個數隨之更換(規格 7.5)
- [x] 八項指標由已保存的逐日序列算出,計算過程不觸發引擎重跑(規格 8.5)

## 結果

· 2026-08-28 00:24 落地 `karst/metrics/`:基準層(買入持有)與指標層(八項數字)分開兩層,兩層都只讀已保存的東西。

**八項指標與定義來源。**取的是規格 8.3〈指標兩層制〉列的八項(同 D-020 第 8 條;規格 7.5 只講門面紀律,不列指標),與原型 `prototype/strategy.html`、`prototype/run.html` 顯示的數字對得上:

| 層 | 指標 | 程式名 | 定義 |
|---|---|---|---|
| 策略卡 | 累計回報對基準 | `total_return` + `benchmarks` | 段尾淨值 ÷ 段首 − 1,連同兩條基準同段的同一個數 |
| 策略卡 | 年化回報 | `annual_return` | (1+累計回報)^(252 ÷ (交易日數−1)) − 1 |
| 策略卡 | 最大回撤 | `max_drawdown` | 段內由高位計的最深跌幅,負數 |
| 策略卡 | 勝率盈虧比 | `win_rate` / `profit_loss_ratio` | 賺錢來回 ÷ 已平倉來回;平均每筆賺 ÷ 平均每筆蝕 |
| 運行詳情 | 年化超額 | `annual_excess` | 策略年化 − 基準年化,QQQ 與 SPY 各一個(原型 `run.html`:「策略減 QQQ」) |
| 運行詳情 | Sortino | `sortino` | (年化回報 − 無風險利率) ÷ 年化下行波幅 |
| 運行詳情 | 平均持倉日數 | `average_holding_days` | 各來回持倉交易日數的平均 |
| 運行詳情 | 換手 | `turnover` | 期內買賣雙邊成交金額 ÷ 2 ÷ 平均淨值 ÷ 年數;1.0 = 一年換足一轉 |

**年化一律 252 個交易日**,與 KARST-026 同一個常數(`karst.runs.window.TRADING_DAYS_PER_YEAR`):同一次運行的年化回報與 Sortino 不可以兩個分母,否則同一張卡上兩個數字對不上。

**算不出就講算不出。**勝率、盈虧比、平均持倉日數、Sortino 四個回 `None` 而不是 0:一筆都未平倉沒有勝率、一次都未蝕過沒有盈虧比、一日都未跌穿目標沒有 Sortino——填 0 會被讀成「輸清」或者「零風險」,與因子值缺失不填 0 同制(D-021 第 4 條)。

**參數無預設值。**`risk_free_rate` 必填:當它是 0 還是 4%,同一條淨值線可以差出一倍的 Sortino,不由計算層代決定。基準相反,預設寫死 QQQ 與 SPY——那不是可調參數,是 D-010 第 4 條裁死的兩隻,寫死正是要令各處都比同一把尺。

**現役設定有地方存了。**KARST-026 代理指出的缺口:新增 `active_setup` 表(schema 第 4 版落,現已隨 KARST-025 到第 5 版),連兩個不可改 trigger。它是**只加不改的指定登記**——換一個現役設定 = 加一列新指定,舊指定一字不變,故此換過什麼、由哪一刻起全部查得回。指的是 `param_set_id`(參數集某一版)不是參數集名:同名會出新版,不釘死一版的話,參數集一出新版門面數字就會悄悄換口徑。`DefinitionStore` 加四個方法(`set_active_setup` / `get_active_setup` / `has_active_setup` / `active_setup_history`),既有簽名與既有表欄一律未動。

**未指定現役設定就沒有門面數字。**`facade_metrics` 當場拋錯,不會隨手挑一次成績好的頂上——那正是規格 7.5 要防的那件事。

**護欄兩條照守(D-027 第 4 條)**:新表不用 AUTOINCREMENT、不用 sqlite 專有語法(主鍵是 `(strategy_id, seq_no)`,序號在 Python 算,與參數集版本號同制);`karst/metrics/` 一個 sqlite 連線都沒有開,全部經 `karst/store.py`。

**驗收逐條:**

- **八個數字齊** —— `tests/test_metrics.py::test_eight_metrics_come_out_of_one_run`。逐筆交易砌成兩贏兩輸的四個來回,勝率 0.5、盈虧比 2.0、平均持倉 80 個交易日三個數各有唯一答案,逐個對得上;累計回報、年化、最大回撤、Sortino、換手、兩個超額數同時出齊。
- **QQQ 與 SPY 各一個超額數** —— `test_excess_against_qqq_and_spy_from_buy_and_hold`。基準由快照收市價直接算,對得上閉式解;超額 = 策略年化減基準年化,兩條基準各自一個數。另在真實快照 `2026-08-27-61e284eaa998` 實測 2015-01-05~2026-08-26:QQQ 年化 19.13%、最大回撤 −35.12%,SPY 年化 14.04%、最大回撤 −33.72%——與這十一年的市場走勢對得上。
- **門面隨現役設定換** —— `test_facade_follows_the_active_setup`。同一策略兩個參數集各跑一次;未指定現役設定時取不到門面數字;指定第一個,門面八個數是它那次;改指第二個,八個數全部隨之更換,舊那次運行本身一字不變、且不再自稱門面。
- **不觸發引擎** —— `test_metrics_read_saved_series_and_never_rerun_the_engine`。算完之後三條序列與落痕那一刻的雜湊一字不差;另揀一段檢視視窗重算,八項按那一段出、運行不變;並靜態核對 `karst/metrics/` 全部檔案一個 engine 都不 import。

全倉 44 個測試通過(`pytest tests/`,含另外兩位代理同期落地的部分)。

**一件要人裁的事(未自行改):現役設定應該經唯一入口設定。**現時 `set_active_setup` 只有 Python API,而唯一入口是治理的第一等公民(D-020 第 4 條)。建議加子命令 `karst params activate --strategy <名稱> --name <參數集> [--note <一句>]`,並把 `active_setup` 加入 `karst/gateway/ledger.py` 的 `GOVERNED_TABLES`(主鍵 `("strategy_id", "seq_no")`),令每次指定都有寫入者簽章、`karst verify` 掃得到。**未改 `karst/gateway/`**——分工不在本票。

**新詞一個(未改 CONTEXT.md,留待裁決):來回(round trip)** —— 同一實體一買一賣配成的一筆已平倉交易;勝率、盈虧比、平均持倉日數三項的單位。配法用先入先出,寫死一種、不設選項(換一種配法算出來的勝率會不同)。

## 留言
