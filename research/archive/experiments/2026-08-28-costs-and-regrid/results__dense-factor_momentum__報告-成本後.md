# 因子輪動·因子動量排名·加密重掃(成本後)

產出於 2026-08-28 23:31。

## 這次掃的是哪一套設定

- 來歷:策略「因子輪動(ETF 版)」第 2 版 × 期間 2015-01-02 至 2026-08-26 × 數據快照 2026-08-28-000b4820a23a × 引擎 vectorbt 0.1.0
- 掃描格:笛卡兒積格 lookback_months(15) × mode(2) × cadence(2),共 60 格;相鄰 = 每條連續軸最多移一步且不可全部不動,選擇軸釘死不動(1 條連續軸;選擇軸 mode、cadence 切出 4 層,每層各出一份判讀);軸型:lookback_months(連續)、mode(選擇)、cadence(選擇);鄰域只沿連續軸取,選擇軸(mode、cadence)逐層分開判
- 跑法:共 60 格,其中 59 格今次真的動過引擎、1 格是讀回已有的運行(同一格不重跑);耗時 12.8 秒
- 無風險利率 4.00%(Sortino 用);基準 QQQ、SPY
- 逐格的運行編號在 `掃描表.csv` 的 `run_id` 欄,一格一個。

## 判讀門檻

- 目標指標 annual_excess:SPY(越大越好);無效格門檻 = 成交少於 30 筆;孤峰門檻 = 高出鄰域平均 0.005 以上;平原高地 = 目標值排前 10%(分位 0.90,即 0.0193651 以上)
- 軸型:lookback_months(連續)、mode(選擇)、cadence(選擇);鄰域只沿連續軸取,選擇軸(mode、cadence)逐層分開判(切出 4 層);**山脊** = 沿連續軸自己與鄰域平均都在高地,但同一組連續軸取值換去另一層即跌穿高地門檻
- 鄰域平均**包含自己那一格**,而且**只沿連續軸取**——選擇軸不入鄰域(KARST-047)。不含自己的那個數在判讀表的 `neighbour_mean` 欄;換一層的代價在 `weakest_sibling_mean` 與 `layer_drop` 兩欄。

## 結果

- 共 60 格:山脊 3 格、孤峰 7 格、普通 50 格
- **單點最優**:lookback_months=8、mode=winner、cadence=monthly;annual_excess:SPY = 0.0332,鄰域平均 0.0245(落差 0.0087,孤峰),成交 98 筆,運行編號 run-35c3f7e9979fe553
- **鄰域平均最高**:lookback_months=4、mode=winner、cadence=monthly;鄰域平均 0.0256,本格 0.0235(山脊),運行編號 run-3205dd16a0a4a1d1
- 單點最優與鄰域平均最高**不是同一格**——這正是規格 6.5 要人看住的那件事:單點最高不等於穩健。

### 頭 5 格(按 annual_excess:SPY,只計有效格)

| # | 參數 | annual_excess:SPY | 鄰域平均 | 落差 | 裁決 | 成交筆數 | 運行編號 |
|---|---|---|---|---|---|---|---|
| 1 | lookback_months=8、mode=winner、cadence=monthly | 0.0332 | 0.0245 | 0.0087 | 孤峰 | 98 | run-35c3f7e9979fe553 |
| 2 | lookback_months=9、mode=winner、cadence=monthly | 0.0278 | 0.0246 | 0.0031 | 山脊 | 96 | run-4cf5506c7c64efeb |
| 3 | lookback_months=3、mode=winner、cadence=monthly | 0.0273 | 0.0141 | 0.0132 | 孤峰 | 144 | run-e284632da504c890 |
| 4 | lookback_months=5、mode=winner、cadence=monthly | 0.0260 | 0.0217 | 0.0043 | 山脊 | 118 | run-6c48d4b9ef346c89 |
| 5 | lookback_months=15、mode=winner、cadence=monthly | 0.0257 | 0.0203 | 0.0054 | 孤峰 | 104 | run-c5259c0a8877f21c |

### 分層判讀(選擇軸 mode、cadence 切出 4 層)

選擇軸換一個取值即換一套做法,不是微調——所以它不入鄰域,而是逐層各出一份判讀。同一條連續軸在哪一層站得住、在哪一層沒有,就在這張表上。

| 層 | 格數 | 有效格 | 高地格數 | 平原 | 山脊 | 孤峰 | 最優 | 層平均 |
|---|---|---|---|---|---|---|---|---|
| mode=winner、cadence=monthly | 15 | 15 | 6 | 0 | 3 | 4 | 0.0332 | 0.0160 |
| mode=winner、cadence=quarterly | 15 | 15 | 0 | 0 | 0 | 3 | 0.0166 | -0.0014 |
| mode=rank、cadence=monthly | 15 | 15 | 0 | 0 | 0 | 0 | 0.0028 | -0.0014 |
| mode=rank、cadence=quarterly | 15 | 15 | 0 | 0 | 0 | 0 | -0.0003 | -0.0053 |

逐層的完整數字在 `分層判讀表.csv`。

### 山脊(沿連續軸平順,換一層即掉;KARST-047)

這幾格自己與連續軸鄰域平均都在高地,但同一組連續軸取值換去另一層之後,那一層的鄰域平均跌穿高地門檻。**不是平原**(換一套做法就沒有了),**亦不是孤峰**(連續軸上揀錯一兩格不要緊)。

- lookback_months=9、mode=winner、cadence=monthly:0.0278,連續軸鄰域平均 0.0246;換去最差那一層只有 -0.0036(跌 0.0283)
- lookback_months=5、mode=winner、cadence=monthly:0.0260,連續軸鄰域平均 0.0217;換去最差那一層只有 -0.0053(跌 0.0270)
- lookback_months=4、mode=winner、cadence=monthly:0.0235,連續軸鄰域平均 0.0256;換去最差那一層只有 -0.0042(跌 0.0298)

### 孤峰(判為擬合噪音,D-016 第 3 條)

- lookback_months=8、mode=winner、cadence=monthly:0.0332,鄰域平均 0.0245,高出 0.0087
- lookback_months=3、mode=winner、cadence=monthly:0.0273,鄰域平均 0.0141,高出 0.0132
- lookback_months=15、mode=winner、cadence=monthly:0.0257,鄰域平均 0.0203,高出 0.0054
- lookback_months=12、mode=winner、cadence=monthly:0.0189,鄰域平均 0.0137,高出 0.0052
- lookback_months=5、mode=winner、cadence=quarterly:0.0159,鄰域平均 0.0037,高出 0.0123
- lookback_months=3、mode=winner、cadence=quarterly:0.0141,鄰域平均 0.0038,高出 0.0103
- lookback_months=8、mode=winner、cadence=quarterly:0.0063,鄰域平均 -0.0012,高出 0.0075

## 圖

![projection-after-lookback-months-mode.png](projection-after-lookback-months-mode.png)

![projection-after-lookback-months-cadence.png](projection-after-lookback-months-cadence.png)

![projection-after-mode-cadence.png](projection-after-mode-cadence.png)

## 備註

- 數據快照:`2026-08-28-000b4820a23a`
- 期間:2015-01-02 至 2026-08-26
- 交易成本:手續費 每股 US$0.005(型別 `per_share`)、滑點 5 個基點(佔成交價比例)
- 運行編號(60 個):`run-89c9bc036c87b624`、`run-078800ab95528f19`、`run-dfa769c8129a1ce6`、`run-8135b9442ffa74e1`、`run-5053757985311967`、`run-53607a430bade45b`、`run-7f14ca07bc335fcf`、`run-42fc0c63888b5735`,另有 52 個
- 掃描格:回望期逐月 1 至 15 個月 × monthly/quarterly 兩個節奏,共 60 格(KARST-036 原本只有 20 格)

回望期由「1/3/6/9/12」改成**逐月**之後,「一步之遙」由三個月變成一個月——鄰域的定義本身變了,所以本份判讀的平原/孤峰**不可以與 KARST-036 那次直接比較**。

熱身期 252 根 K 線,期間四格各佔 25%;訊號一律只用決策日收工前的數據,成交在下一根 K 線的開價(D-021 第 3 條)。

## 檔

- `掃描表.csv`:逐格八項指標、成交筆數、運行編號
- `判讀表.csv`:逐格裁決、鄰域平均、落差、所在層、換層代價
- `分層判讀表.csv`:逐層的裁決分佈、最優格、層平均

本報告只交表與判讀,**不裁定哪一組參數該用**——那是用戶的領域(D-008)。
