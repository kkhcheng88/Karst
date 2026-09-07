# 因子輪動·相對強弱對 SPY(最大回撤)

產出於 2026-08-28 23:29。

## 這次掃的是哪一套設定

- 來歷:策略「因子輪動(ETF 版)」第 2 版 × 期間 2015-01-02 至 2026-08-26 × 數據快照 2026-08-28-000b4820a23a × 引擎 vectorbt 0.1.0
- 掃描格:笛卡兒積格 lookback_months(5) × fallback(2) × cadence(2),共 20 格;相鄰 = 每條連續軸最多移一步且不可全部不動,選擇軸釘死不動(1 條連續軸;選擇軸 fallback、cadence 切出 4 層,每層各出一份判讀);軸型:lookback_months(連續)、fallback(選擇)、cadence(選擇);鄰域只沿連續軸取,選擇軸(fallback、cadence)逐層分開判
- 跑法:共 20 格,其中 20 格今次真的動過引擎、0 格是讀回已有的運行(同一格不重跑);耗時 5.3 秒
- 無風險利率 4.00%(Sortino 用);基準 QQQ、SPY
- 逐格的運行編號在 `掃描表.csv` 的 `run_id` 欄,一格一個。

## 判讀門檻

- 目標指標 max_drawdown(越大越好);無效格門檻 = 成交少於 30 筆;孤峰門檻 = 高出鄰域平均 0.005 以上;平原高地 = 目標值排前 10%(分位 0.90,即 -0.334801 以上)
- 軸型:lookback_months(連續)、fallback(選擇)、cadence(選擇);鄰域只沿連續軸取,選擇軸(fallback、cadence)逐層分開判(切出 4 層);**山脊** = 沿連續軸自己與鄰域平均都在高地,但同一組連續軸取值換去另一層即跌穿高地門檻
- 鄰域平均**包含自己那一格**,而且**只沿連續軸取**——選擇軸不入鄰域(KARST-047)。不含自己的那個數在判讀表的 `neighbour_mean` 欄;換一層的代價在 `weakest_sibling_mean` 與 `layer_drop` 兩欄。

## 結果

- 共 20 格:孤峰 2 格、普通 18 格
- **單點最優**:lookback_months=6、fallback=cash、cadence=monthly;max_drawdown = -0.2114,鄰域平均 -0.2953(落差 0.0839,孤峰),成交 275 筆,運行編號 run-08bcf7fb56c6981c
- **鄰域平均最高**:lookback_months=9、fallback=cash、cadence=monthly;鄰域平均 -0.2951,本格 -0.3391(普通),運行編號 run-7048c00120dc9126
- 單點最優與鄰域平均最高**不是同一格**——這正是規格 6.5 要人看住的那件事:單點最高不等於穩健。

### 頭 5 格(按 max_drawdown,只計有效格)

| # | 參數 | max_drawdown | 鄰域平均 | 落差 | 裁決 | 成交筆數 | 運行編號 |
|---|---|---|---|---|---|---|---|
| 1 | lookback_months=6、fallback=cash、cadence=monthly | -0.2114 | -0.2953 | 0.0839 | 孤峰 | 275 | run-08bcf7fb56c6981c |
| 2 | lookback_months=12、fallback=cash、cadence=monthly | -0.3348 | -0.3370 | 0.0022 | 普通 | 263 | run-a19324e9b1672bfd |
| 3 | lookback_months=12、fallback=equal、cadence=monthly | -0.3348 | -0.3370 | 0.0022 | 普通 | 283 | run-41a46091aee89c0a |
| 4 | lookback_months=3、fallback=equal、cadence=monthly | -0.3353 | -0.3420 | 0.0067 | 孤峰 | 353 | run-a2af4be50b3e14c3 |
| 5 | lookback_months=3、fallback=cash、cadence=monthly | -0.3353 | -0.2958 | -0.0395 | 普通 | 316 | run-b9cd36b0f209114b |

### 分層判讀(選擇軸 fallback、cadence 切出 4 層)

選擇軸換一個取值即換一套做法,不是微調——所以它不入鄰域,而是逐層各出一份判讀。同一條連續軸在哪一層站得住、在哪一層沒有,就在這張表上。

| 層 | 格數 | 有效格 | 高地格數 | 平原 | 山脊 | 孤峰 | 最優 | 層平均 |
|---|---|---|---|---|---|---|---|---|
| fallback=cash、cadence=monthly | 5 | 5 | 2 | 0 | 0 | 1 | -0.2114 | -0.3123 |
| fallback=cash、cadence=quarterly | 5 | 5 | 0 | 0 | 0 | 0 | -0.3406 | -0.3621 |
| fallback=equal、cadence=monthly | 5 | 5 | 1 | 0 | 0 | 1 | -0.3348 | -0.3400 |
| fallback=equal、cadence=quarterly | 5 | 5 | 0 | 0 | 0 | 0 | -0.3406 | -0.3621 |

逐層的完整數字在 `分層判讀表.csv`。

### 孤峰(判為擬合噪音,D-016 第 3 條)

- lookback_months=6、fallback=cash、cadence=monthly:-0.2114,鄰域平均 -0.2953,高出 0.0839
- lookback_months=3、fallback=equal、cadence=monthly:-0.3353,鄰域平均 -0.3420,高出 0.0067

## 圖

![drawdown-lookback-months-fallback.png](drawdown-lookback-months-fallback.png)

![drawdown-lookback-months-cadence.png](drawdown-lookback-months-cadence.png)

![drawdown-fallback-cadence.png](drawdown-fallback-cadence.png)

## 備註

最大回撤以**負數**表示,所以判讀那句「越大越好」在這裡就是「跌得越少越好」。與年化超額那一份**用的是同一批運行**,只換一個目標指標重判一次,一格都沒有重跑。

## 檔

- `掃描表.csv`:逐格八項指標、成交筆數、運行編號
- `判讀表.csv`:逐格裁決、鄰域平均、落差、所在層、換層代價
- `分層判讀表.csv`:逐層的裁決分佈、最優格、層平均

本報告只交表與判讀,**不裁定哪一組參數該用**——那是用戶的領域(D-008)。
