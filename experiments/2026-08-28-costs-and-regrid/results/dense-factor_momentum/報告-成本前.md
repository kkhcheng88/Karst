# 因子輪動·因子動量排名·加密重掃(成本前)

產出於 2026-08-28 23:30。

## 這次掃的是哪一套設定

- 來歷:策略「因子輪動(ETF 版)」第 2 版 × 期間 2015-01-02 至 2026-08-26 × 數據快照 2026-08-28-000b4820a23a × 引擎 vectorbt 0.1.0
- 掃描格:笛卡兒積格 lookback_months(15) × mode(2) × cadence(2),共 60 格;相鄰 = 每條連續軸最多移一步且不可全部不動,選擇軸釘死不動(1 條連續軸;選擇軸 mode、cadence 切出 4 層,每層各出一份判讀);軸型:lookback_months(連續)、mode(選擇)、cadence(選擇);鄰域只沿連續軸取,選擇軸(mode、cadence)逐層分開判
- 跑法:共 60 格,其中 40 格今次真的動過引擎、20 格是讀回已有的運行(同一格不重跑);耗時 8.8 秒
- 無風險利率 4.00%(Sortino 用);基準 QQQ、SPY
- 逐格的運行編號在 `掃描表.csv` 的 `run_id` 欄,一格一個。

## 判讀門檻

- 目標指標 annual_excess:SPY(越大越好);無效格門檻 = 成交少於 30 筆;孤峰門檻 = 高出鄰域平均 0.005 以上;平原高地 = 目標值排前 10%(分位 0.90,即 0.0216512 以上)
- 軸型:lookback_months(連續)、mode(選擇)、cadence(選擇);鄰域只沿連續軸取,選擇軸(mode、cadence)逐層分開判(切出 4 層);**山脊** = 沿連續軸自己與鄰域平均都在高地,但同一組連續軸取值換去另一層即跌穿高地門檻
- 鄰域平均**包含自己那一格**,而且**只沿連續軸取**——選擇軸不入鄰域(KARST-047)。不含自己的那個數在判讀表的 `neighbour_mean` 欄;換一層的代價在 `weakest_sibling_mean` 與 `layer_drop` 兩欄。

## 結果

- 共 60 格:山脊 3 格、孤峰 7 格、普通 50 格
- **單點最優**:lookback_months=8、mode=winner、cadence=monthly;annual_excess:SPY = 0.0357,鄰域平均 0.0272(落差 0.0085,孤峰),成交 98 筆,運行編號 run-7d49fa518874b385
- **鄰域平均最高**:lookback_months=4、mode=winner、cadence=monthly;鄰域平均 0.0300,本格 0.0280(山脊),運行編號 run-8390921e7dac4626
- 單點最優與鄰域平均最高**不是同一格**——這正是規格 6.5 要人看住的那件事:單點最高不等於穩健。

### 頭 5 格(按 annual_excess:SPY,只計有效格)

| # | 參數 | annual_excess:SPY | 鄰域平均 | 落差 | 裁決 | 成交筆數 | 運行編號 |
|---|---|---|---|---|---|---|---|
| 1 | lookback_months=8、mode=winner、cadence=monthly | 0.0357 | 0.0272 | 0.0085 | 孤峰 | 98 | run-7d49fa518874b385 |
| 2 | lookback_months=3、mode=winner、cadence=monthly | 0.0324 | 0.0194 | 0.0130 | 孤峰 | 144 | run-95118047dd866a68 |
| 3 | lookback_months=9、mode=winner、cadence=monthly | 0.0301 | 0.0269 | 0.0032 | 山脊 | 96 | run-da7b666cb00e4f94 |
| 4 | lookback_months=5、mode=winner、cadence=monthly | 0.0296 | 0.0257 | 0.0039 | 山脊 | 118 | run-f225e31d3b1b95da |
| 5 | lookback_months=4、mode=winner、cadence=monthly | 0.0280 | 0.0300 | -0.0020 | 山脊 | 132 | run-8390921e7dac4626 |

### 分層判讀(選擇軸 mode、cadence 切出 4 層)

選擇軸換一個取值即換一套做法,不是微調——所以它不入鄰域,而是逐層各出一份判讀。同一條連續軸在哪一層站得住、在哪一層沒有,就在這張表上。

| 層 | 格數 | 有效格 | 高地格數 | 平原 | 山脊 | 孤峰 | 最優 | 層平均 |
|---|---|---|---|---|---|---|---|---|
| mode=winner、cadence=monthly | 15 | 15 | 6 | 0 | 3 | 4 | 0.0357 | 0.0196 |
| mode=winner、cadence=quarterly | 15 | 15 | 0 | 0 | 0 | 3 | 0.0182 | 0.0007 |
| mode=rank、cadence=monthly | 15 | 15 | 0 | 0 | 0 | 0 | 0.0037 | 0.0000 |
| mode=rank、cadence=quarterly | 15 | 15 | 0 | 0 | 0 | 0 | 0.0002 | -0.0046 |

逐層的完整數字在 `分層判讀表.csv`。

### 山脊(沿連續軸平順,換一層即掉;KARST-047)

這幾格自己與連續軸鄰域平均都在高地,但同一組連續軸取值換去另一層之後,那一層的鄰域平均跌穿高地門檻。**不是平原**(換一套做法就沒有了),**亦不是孤峰**(連續軸上揀錯一兩格不要緊)。

- lookback_months=9、mode=winner、cadence=monthly:0.0301,連續軸鄰域平均 0.0269;換去最差那一層只有 -0.0030(跌 0.0299)
- lookback_months=5、mode=winner、cadence=monthly:0.0296,連續軸鄰域平均 0.0257;換去最差那一層只有 -0.0044(跌 0.0301)
- lookback_months=4、mode=winner、cadence=monthly:0.0280,連續軸鄰域平均 0.0300;換去最差那一層只有 -0.0033(跌 0.0333)

### 孤峰(判為擬合噪音,D-016 第 3 條)

- lookback_months=8、mode=winner、cadence=monthly:0.0357,鄰域平均 0.0272,高出 0.0085
- lookback_months=3、mode=winner、cadence=monthly:0.0324,鄰域平均 0.0194,高出 0.0130
- lookback_months=15、mode=winner、cadence=monthly:0.0279,鄰域平均 0.0224,高出 0.0055
- lookback_months=12、mode=winner、cadence=monthly:0.0210,鄰域平均 0.0155,高出 0.0054
- lookback_months=5、mode=winner、cadence=quarterly:0.0182,鄰域平均 0.0060,高出 0.0122
- lookback_months=3、mode=winner、cadence=quarterly:0.0170,鄰域平均 0.0068,高出 0.0102
- lookback_months=8、mode=winner、cadence=quarterly:0.0080,鄰域平均 0.0006,高出 0.0074

## 圖

![projection-before-lookback-months-mode.png](projection-before-lookback-months-mode.png)

![projection-before-lookback-months-cadence.png](projection-before-lookback-months-cadence.png)

![projection-before-mode-cadence.png](projection-before-mode-cadence.png)

## 備註

- 數據快照:`2026-08-28-000b4820a23a`
- 期間:2015-01-02 至 2026-08-26
- 交易成本:零(手續費與滑點皆為 0)
- 運行編號(60 個):`run-05fa63b7d280d974`、`run-95ca8120ead09df4`、`run-21781b478ae52c05`、`run-427cb859e03c97a1`、`run-ee9aaa6b50ccc6d6`、`run-854b9643cba2efdf`、`run-9f38c1af4eb33a96`、`run-862fb2f6672068da`,另有 52 個
- 掃描格:回望期逐月 1 至 15 個月 × monthly/quarterly 兩個節奏,共 60 格(KARST-036 原本只有 20 格)

回望期由「1/3/6/9/12」改成**逐月**之後,「一步之遙」由三個月變成一個月——鄰域的定義本身變了,所以本份判讀的平原/孤峰**不可以與 KARST-036 那次直接比較**。

熱身期 252 根 K 線,期間四格各佔 25%;訊號一律只用決策日收工前的數據,成交在下一根 K 線的開價(D-021 第 3 條)。

## 檔

- `掃描表.csv`:逐格八項指標、成交筆數、運行編號
- `判讀表.csv`:逐格裁決、鄰域平均、落差、所在層、換層代價
- `分層判讀表.csv`:逐層的裁決分佈、最優格、層平均

本報告只交表與判讀,**不裁定哪一組參數該用**——那是用戶的領域(D-008)。
