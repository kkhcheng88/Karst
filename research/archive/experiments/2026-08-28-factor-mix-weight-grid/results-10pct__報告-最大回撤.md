# 因子混合權重掃描·最大回撤(步長 10%)

產出於 2026-08-28 23:12。

## 這次掃的是哪一套設定

- 來歷:策略「因子混合(ETF 版)」第 2 版 × 期間 2015-01-02 至 2026-08-26 × 數據快照 2026-08-28-000b4820a23a × 引擎 vectorbt 0.1.0
- 掃描格:拼合格(2 個成分格,共 572 格)——相鄰 = 每個成分格各自移一步或者不動,但不可全部不動;軸型:weight_quality(連續)、weight_value(連續)、weight_momentum(連續)、weight_low_vol(連續)、cadence(選擇);鄰域只沿連續軸取,選擇軸(cadence)逐層分開判。成分格:權重單純形格:4 個權重(weight_quality、weight_value、weight_momentum、weight_low_vol),步長 10%,加總 100%,共 286 格;相鄰 = 把一步的權重由其中一格移去另一格(一個 +一步、一個 −一步,其餘不動);笛卡兒積格 cadence(2),共 2 格;相鄰 = 每條連續軸最多移一步且不可全部不動,選擇軸釘死不動(0 條連續軸;選擇軸 cadence 切出 2 層,每層各出一份判讀);軸型:cadence(選擇);鄰域只沿連續軸取,選擇軸(cadence)逐層分開判
- 跑法:共 572 格,其中 572 格今次真的動過引擎、0 格是讀回已有的運行(同一格不重跑);耗時 171.0 秒
- 無風險利率 4.00%(Sortino 用);基準 QQQ、SPY
- 逐格的運行編號在 `掃描表.csv` 的 `run_id` 欄,一格一個。

## 判讀門檻

- 目標指標 max_drawdown(越大越好);無效格門檻 = 成交少於 30 筆;孤峰門檻 = 高出鄰域平均 0.005 以上;平原高地 = 目標值排前 10%(分位 0.90,即 -0.337331 以上)
- 軸型:weight_quality(連續)、weight_value(連續)、weight_momentum(連續)、weight_low_vol(連續)、cadence(選擇);鄰域只沿連續軸取,選擇軸(cadence)逐層分開判(切出 2 層);**山脊** = 沿連續軸自己與鄰域平均都在高地,但同一組連續軸取值換去另一層即跌穿高地門檻
- 鄰域平均**包含自己那一格**,而且**只沿連續軸取**——選擇軸不入鄰域(KARST-047)。不含自己的那個數在判讀表的 `neighbour_mean` 欄;換一層的代價在 `weakest_sibling_mean` 與 `layer_drop` 兩欄。

## 結果

- 共 572 格:平原 43 格、普通 521 格、無效 8 格
- **單點最優**:weight_quality=0、weight_value=0、weight_momentum=0.1、weight_low_vol=0.9、cadence=monthly;max_drawdown = -0.3319,鄰域平均 -0.3340(落差 0.0021,平原),成交 280 筆,運行編號 run-cb38c8ae01a7a191
- **鄰域平均最高**:weight_quality=0、weight_value=0、weight_momentum=0.1、weight_low_vol=0.9、cadence=quarterly;鄰域平均 -0.3339,本格 -0.3319(平原),運行編號 run-23dfe254c3a28464
- 單點最優與鄰域平均最高**不是同一格**——這正是規格 6.5 要人看住的那件事:單點最高不等於穩健。

### 頭 5 格(按 max_drawdown,只計有效格)

| # | 參數 | max_drawdown | 鄰域平均 | 落差 | 裁決 | 成交筆數 | 運行編號 |
|---|---|---|---|---|---|---|---|
| 1 | weight_quality=0、weight_value=0、weight_momentum=0.1、weight_low_vol=0.9、cadence=monthly | -0.3319 | -0.3340 | 0.0021 | 平原 | 280 | run-cb38c8ae01a7a191 |
| 2 | weight_quality=0.1、weight_value=0、weight_momentum=0、weight_low_vol=0.9、cadence=quarterly | -0.3319 | -0.3339 | 0.0020 | 平原 | 94 | run-920577ee905c42c9 |
| 3 | weight_quality=0、weight_value=0、weight_momentum=0.1、weight_low_vol=0.9、cadence=quarterly | -0.3319 | -0.3339 | 0.0020 | 平原 | 94 | run-23dfe254c3a28464 |
| 4 | weight_quality=0.1、weight_value=0、weight_momentum=0、weight_low_vol=0.9、cadence=monthly | -0.3319 | -0.3340 | 0.0021 | 平原 | 280 | run-ab5d31814436922f |
| 5 | weight_quality=0、weight_value=0、weight_momentum=0.2、weight_low_vol=0.8、cadence=monthly | -0.3328 | -0.3344 | 0.0017 | 平原 | 280 | run-04f46ca28406ae27 |

### 對照格

| 參數 | max_drawdown | 全格排名 | 運行編號 |
|---|---|---|---|
| weight_quality=0.25、weight_value=0.25、weight_momentum=0.25、weight_low_vol=0.25、cadence=monthly | -0.3499 | 不在這個格上 | run-e1ecd16be7d794ab |
| weight_quality=0.25、weight_value=0.25、weight_momentum=0.25、weight_low_vol=0.25、cadence=quarterly | -0.3493 | 不在這個格上 | run-9177d17490f49dc4 |

### 分層判讀(選擇軸 cadence 切出 2 層)

選擇軸換一個取值即換一套做法,不是微調——所以它不入鄰域,而是逐層各出一份判讀。同一條連續軸在哪一層站得住、在哪一層沒有,就在這張表上。

| 層 | 格數 | 有效格 | 高地格數 | 平原 | 山脊 | 孤峰 | 最優 | 層平均 |
|---|---|---|---|---|---|---|---|---|
| cadence=monthly | 286 | 282 | 28 | 21 | 0 | 0 | -0.3319 | -0.3506 |
| cadence=quarterly | 286 | 282 | 29 | 22 | 0 | 0 | -0.3319 | -0.3501 |

逐層的完整數字在 `分層判讀表.csv`。

### 無效格(成交太少,數字講的是運氣不是參數)

- 共 8 格成交少於 30 筆;它們不入最優,亦不入任何一格的鄰域平均。
  - weight_quality=0、weight_value=0、weight_momentum=0、weight_low_vol=1、cadence=monthly:成交 1 筆
  - weight_quality=0、weight_value=0、weight_momentum=0、weight_low_vol=1、cadence=quarterly:成交 1 筆
  - weight_quality=0、weight_value=0、weight_momentum=1、weight_low_vol=0、cadence=monthly:成交 1 筆
  - weight_quality=0、weight_value=0、weight_momentum=1、weight_low_vol=0、cadence=quarterly:成交 1 筆
  - weight_quality=0、weight_value=1、weight_momentum=0、weight_low_vol=0、cadence=monthly:成交 1 筆
  - weight_quality=0、weight_value=1、weight_momentum=0、weight_low_vol=0、cadence=quarterly:成交 1 筆
  - weight_quality=1、weight_value=0、weight_momentum=0、weight_low_vol=0、cadence=monthly:成交 1 筆
  - weight_quality=1、weight_value=0、weight_momentum=0、weight_low_vol=0、cadence=quarterly:成交 1 筆

## 圖

![drawdown-monthly-weight-quality-weight-value.png](drawdown-monthly-weight-quality-weight-value.png)

![drawdown-monthly-weight-quality-weight-momentum.png](drawdown-monthly-weight-quality-weight-momentum.png)

![drawdown-monthly-weight-quality-weight-low-vol.png](drawdown-monthly-weight-quality-weight-low-vol.png)

![drawdown-monthly-weight-value-weight-momentum.png](drawdown-monthly-weight-value-weight-momentum.png)

![drawdown-monthly-weight-value-weight-low-vol.png](drawdown-monthly-weight-value-weight-low-vol.png)

![drawdown-monthly-weight-momentum-weight-low-vol.png](drawdown-monthly-weight-momentum-weight-low-vol.png)

![drawdown-quarterly-weight-quality-weight-value.png](drawdown-quarterly-weight-quality-weight-value.png)

![drawdown-quarterly-weight-quality-weight-momentum.png](drawdown-quarterly-weight-quality-weight-momentum.png)

![drawdown-quarterly-weight-quality-weight-low-vol.png](drawdown-quarterly-weight-quality-weight-low-vol.png)

![drawdown-quarterly-weight-value-weight-momentum.png](drawdown-quarterly-weight-value-weight-momentum.png)

![drawdown-quarterly-weight-value-weight-low-vol.png](drawdown-quarterly-weight-value-weight-low-vol.png)

![drawdown-quarterly-weight-momentum-weight-low-vol.png](drawdown-quarterly-weight-momentum-weight-low-vol.png)

## 備註

最大回撤以**負數**表示(−0.34 即由高位跌 34%),所以判讀那句「越大越好」在這裡剛好就是「跌得越少越好」,方向不用另設參數。

這一份與年化超額那一份**用的是同一批運行**——同一個格、同一批運行編號,只是換一個目標指標重判一次,一格都沒有重跑。

## 檔

- `掃描表.csv`:逐格八項指標、成交筆數、運行編號
- `判讀表.csv`:逐格裁決、鄰域平均、落差、所在層、換層代價
- `分層判讀表.csv`:逐層的裁決分佈、最優格、層平均

本報告只交表與判讀,**不裁定哪一組參數該用**——那是用戶的領域(D-008)。
