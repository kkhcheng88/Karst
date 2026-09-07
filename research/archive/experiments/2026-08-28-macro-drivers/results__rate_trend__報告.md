# 宏觀驅動器·10 年息率趨勢(對 SPY 年化超額,連成本)

產出於 2026-08-28 23:33。

## 這次掃的是哪一套設定

- 來歷:策略「因子輪動(ETF 版)」第 2 版 × 期間 2015-01-02 至 2026-08-26 × 數據快照 2026-08-28-000b4820a23a × 引擎 vectorbt 0.1.0
- 掃描格:笛卡兒積格 lookback_days(5) × tilt(3) × cadence(2),共 30 格;相鄰 = 每條連續軸最多移一步且不可全部不動,選擇軸釘死不動(2 條連續軸;選擇軸 cadence 切出 2 層,每層各出一份判讀);軸型:lookback_days(連續)、tilt(連續)、cadence(選擇);鄰域只沿連續軸取,選擇軸(cadence)逐層分開判
- 跑法:共 30 格,其中 30 格今次真的動過引擎、0 格是讀回已有的運行(同一格不重跑);耗時 7.7 秒
- 無風險利率 4.00%(Sortino 用);基準 QQQ、SPY
- 逐格的運行編號在 `掃描表.csv` 的 `run_id` 欄,一格一個。

## 判讀門檻

- 目標指標 annual_excess:SPY(越大越好);無效格門檻 = 成交少於 30 筆;孤峰門檻 = 高出鄰域平均 0.005 以上;平原高地 = 目標值排前 10%(分位 0.90,即 0.00622813 以上)
- 軸型:lookback_days(連續)、tilt(連續)、cadence(選擇);鄰域只沿連續軸取,選擇軸(cadence)逐層分開判(切出 2 層);**山脊** = 沿連續軸自己與鄰域平均都在高地,但同一組連續軸取值換去另一層即跌穿高地門檻
- 鄰域平均**包含自己那一格**,而且**只沿連續軸取**——選擇軸不入鄰域(KARST-047)。不含自己的那個數在判讀表的 `neighbour_mean` 欄;換一層的代價在 `weakest_sibling_mean` 與 `layer_drop` 兩欄。

## 結果

- 共 30 格:山脊 1 格、孤峰 4 格、普通 25 格
- **單點最優**:lookback_days=20、tilt=1、cadence=monthly;annual_excess:SPY = 0.0307,鄰域平均 0.0068(落差 0.0239,孤峰),成交 186 筆,運行編號 run-980b7e2f35d4fce3
- **鄰域平均最高**:lookback_days=10、tilt=1、cadence=monthly;鄰域平均 0.0154,本格 0.0085(山脊),運行編號 run-607ebbbd61e8659b
- 單點最優與鄰域平均最高**不是同一格**——這正是規格 6.5 要人看住的那件事:單點最高不等於穩健。

### 頭 5 格(按 annual_excess:SPY,只計有效格)

| # | 參數 | annual_excess:SPY | 鄰域平均 | 落差 | 裁決 | 成交筆數 | 運行編號 |
|---|---|---|---|---|---|---|---|
| 1 | lookback_days=20、tilt=1、cadence=monthly | 0.0307 | 0.0068 | 0.0239 | 孤峰 | 186 | run-980b7e2f35d4fce3 |
| 2 | lookback_days=20、tilt=0.75、cadence=monthly | 0.0186 | 0.0042 | 0.0144 | 普通 | 560 | run-e043edadd5768b8d |
| 3 | lookback_days=10、tilt=1、cadence=monthly | 0.0085 | 0.0154 | -0.0069 | 山脊 | 178 | run-607ebbbd61e8659b |
| 4 | lookback_days=20、tilt=0.5、cadence=monthly | 0.0060 | 0.0016 | 0.0043 | 普通 | 560 | run-4a0e465ee0981767 |
| 5 | lookback_days=10、tilt=0.75、cadence=monthly | 0.0039 | 0.0111 | -0.0072 | 普通 | 560 | run-5eb8c6ca171125d2 |

### 分層判讀(選擇軸 cadence 切出 2 層)

選擇軸換一個取值即換一套做法,不是微調——所以它不入鄰域,而是逐層各出一份判讀。同一條連續軸在哪一層站得住、在哪一層沒有,就在這張表上。

| 層 | 格數 | 有效格 | 高地格數 | 平原 | 山脊 | 孤峰 | 最優 | 層平均 |
|---|---|---|---|---|---|---|---|---|
| cadence=monthly | 15 | 15 | 3 | 0 | 1 | 2 | 0.0307 | 0.0007 |
| cadence=quarterly | 15 | 15 | 0 | 0 | 0 | 2 | -0.0077 | -0.0172 |

逐層的完整數字在 `分層判讀表.csv`。

### 山脊(沿連續軸平順,換一層即掉;KARST-047)

這幾格自己與連續軸鄰域平均都在高地,但同一組連續軸取值換去另一層之後,那一層的鄰域平均跌穿高地門檻。**不是平原**(換一套做法就沒有了),**亦不是孤峰**(連續軸上揀錯一兩格不要緊)。

- lookback_days=10、tilt=1、cadence=monthly:0.0085,連續軸鄰域平均 0.0154;換去最差那一層只有 -0.0184(跌 0.0339)

### 孤峰(判為擬合噪音,D-016 第 3 條)

- lookback_days=20、tilt=1、cadence=monthly:0.0307,鄰域平均 0.0068,高出 0.0239
- lookback_days=60、tilt=1、cadence=monthly:0.0033,鄰域平均 -0.0061,高出 0.0094
- lookback_days=20、tilt=0.5、cadence=quarterly:-0.0077,鄰域平均 -0.0140,高出 0.0064
- lookback_days=60、tilt=0.5、cadence=quarterly:-0.0098,鄰域平均 -0.0149,高出 0.0051

## 圖

![projection-lookback-days-tilt.png](projection-lookback-days-tilt.png)

![projection-lookback-days-cadence.png](projection-lookback-days-cadence.png)

![projection-tilt-cadence.png](projection-tilt-cadence.png)

## 備註

- 數據快照:`2026-08-28-000b4820a23a`
- 期間:2015-01-02 至 2026-08-26
- 交易成本:零(手續費與滑點皆為 0)
- 運行編號(30 個):`run-d9b1585567b628ff`、`run-8943537d60e0b5fd`、`run-5eb8c6ca171125d2`、`run-9af008bf35d530f4`、`run-607ebbbd61e8659b`、`run-3ce971df3f2f8ffd`、`run-4a0e465ee0981767`、`run-e5c444e52e277d9b`,另有 22 個
- 宏觀快照:`2026-08-28-810facb50382`(序列 UST_10Y;知情時間=收市後可得;宏觀序列不是可投資對象,只影響四格怎樣分)

## 檔

- `掃描表.csv`:逐格八項指標、成交筆數、運行編號
- `判讀表.csv`:逐格裁決、鄰域平均、落差、所在層、換層代價
- `分層判讀表.csv`:逐層的裁決分佈、最優格、層平均

本報告只交表與判讀,**不裁定哪一組參數該用**——那是用戶的領域(D-008)。
