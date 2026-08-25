---
id: KARST-009
title: 回測核心試跑對決:vectorbt 對 PyBroker
type: task
createdAt: 2026-08-25
risk: low
model: opus
fits: 一程
approvalRequired: false
dependsOn: []
claimedBy: KARST-009-bakeoff
epic: V1 藍圖
deliverable: KARST-D01
closed: 2026-08-25
---

## 工作內容

完成之後有什麼是之前做不到的:「借用哪個回測核心」這個決定有實測數據支撐,不再只憑文件。考題(照 D-006 的主場景設):同一個玩具選股策略——按一個模擬因子橫斷面排名、每月選 N 隻、平均分再平衡——在 vectorbt 與 PyBroker 各實作一次,規模數百股乘約十年日線,並做一輪約一千組參數掃描。比較三樣:表達直觀度(選股邏輯寫出來扭不扭曲)、耗時(單次回測與掃描)、接自家資料層的順暢度。同時判定假設 A-001 的真假。結論寫建議但明寫最終由用戶裁決(D-005)。

## 驗收條件

- [x] 兩邊實作代碼落倉並可重跑,環境依賴有記錄
- [x] 耗時數據表落檔(單次回測與參數掃描,同機同數據)
- [x] 表達力與接駁順暢度有逐項對比與建議,明寫由用戶裁決
- [x] A-001 在假設冊更新狀態(holds 或 overturned),附一句證據

## 結果

**兩個引擎都做得到這條策略,結果幾乎一模一樣;但 vectorbt 快 20 至 40 倍,而 PyBroker 寫得順手得多。建議以 vectorbt 為 v1 回測核心——最終裁決由用戶作出(D-005)。**

### 考題與環境

500 隻股票 × 2,608 個交易日(2016-01-04 至 2025-12-31),合成數據固定種子 20260825,不依賴任何外部 API。策略:每 interval 個月的第一個交易日按平滑後的因子橫斷面排名選頭 N 隻、平均分,訊號日的下一個交易日以收市價成交。掃描網格 N(40) × 換倉月距(5) × 平滑窗(5)= 1,000 組。機器 AMD Ryzen 7 7840HS / 16 核 / 23.8 GB。兩邊共用同一套 numpy 2.4.6、pandas 3.0.5、numba 0.67.0,計時基礎公平;各用一個獨立 venv(vectorbt 1.1.0 / lib-pybroker 2.0.0)。

### 耗時(同機同數據,詳見 results/timings.csv)

| 項目 | vectorbt | PyBroker | 倍數 |
|---|---:|---:|---:|
| 單次回測(熱身後) | 0.332 秒 | 13.49 秒 | 40.6 |
| 單次回測(全新環境首次) | 10.02 秒 | 15.08 秒 | 1.5 |
| 1,000 組掃描 | 677 秒(實跑) | 13,573 秒 = 3 小時 46 分(外推) | 20.0 |

PyBroker 的 1,000 組是外推,不是實跑:實測橫跨網格的 20 組,每組 12.75 至 14.24 秒,離散度極低。差距的成因是結構性的——PyBroker 每根 bar 每隻股票呼叫一次 Python 函式,一次回測 130 萬次;vectorbt 把整個矩陣交給 numba 核心,掃描時還可以把多組參數橫向拼成一個更寬的矩陣。兩邊本次都是單一進程;多核並行兩邊都做得到,所以「每核心約 20 倍」才是穩健的結論。

### 表達直觀度與接駁順暢度(逐項)

| 項目 | vectorbt | PyBroker | 勝方 |
|---|---|---|---|
| 選股邏輯 | 排名要自己在 numpy 砌(argsort 套 argsort、目標權重矩陣),27 行 | `ctx.long_score` 加 `enable_rotation`,排名是一等公民,18 行 | PyBroker |
| 掃描機制 | 要自己寫批次堆疊,20 行,並要管記憶體 | 普通 for 迴圈,0 行 | PyBroker |
| 接自家資料層 | 每個欄位 pivot 成寬表,5 行 | `register_columns` 一句,直接吃長格式,2 行 | PyBroker |
| 交易機制真實度 | 目標權重,較抽象 | 買賣延遲、成交價型別、滑點模型、碎股 | PyBroker |
| 蒙地卡羅 / 穩健性 | `from_random_signals` | 內建 bootstrap 與 walkforward | PyBroker |
| 單次回測與掃描速度 | 見上表 | 見上表 | vectorbt(大勝) |
| 授權 | Apache-2.0 + Commons Clause | 同左 | 平手 |

兩邊都不強加自家儲存格式,所以 D-002「單一定義、無第二影像」在兩邊都守得住。心智負擔方面各有一個「不寫就默默錯」的陷阱:vectorbt 漏了 `call_seq="auto"`,共用現金時買單會因現金未到位而被部分拒絕;PyBroker 的 `enable_rotation` 語意是「跌出名次就換走、空位由頭名補上」,不是每次換倉把全部持倉拉回平均分,要嚴格等權需另寫 sizer。

### 兩邊是否在跑同一條策略(否則「誰快」沒有意義)

20 組橫跨網格的組合對照:相關系數 **0.9996**,差距中位數 0.78%,最大 4.18%(出現在 N=1 這種最集中的組合)。基準組(N=10、每月換倉)vectorbt 總報酬 5.5649、PyBroker 5.5714,**差 0.1%**。速度差距是真的,不是誰偷工減料。殘餘差距來源已查明:目標權重每次全部拉回 1/N 對 rotation 只換跌出名次者;以及 PyBroker 買賣各有一根 bar 延遲。

### 建議(最終由用戶裁決 — D-005)

計分是 PyBroker 贏得多,**但它輸掉的兩格正是 D-002 明文寫死的硬要求**。建議選 vectorbt,三個理由:一、用戶原話要求核心引擎「matrix based … can simulate lot of trade in a sec」,vectorbt 0.332 秒達標,PyBroker 13.49 秒不達標且是結構性的;二、11 分鐘與 3 小時 46 分的分別,是「一杯咖啡試完一輪想法」與「今晚掛住、明早看結果」的分別,會直接改變用戶怎樣用這件工具;三、vectorbt 的表達劣勢是一次性的——那段排名邏輯按 D-007 本來就要寫在 Karst 自家介面之後,寫一次之後每條新策略只是換一個因子。**換句話說 PyBroker 的表達優勢主要在第一天體現,vectorbt 的速度優勢每一天都體現。**

選 PyBroker 亦站得住:排名語意內建,寫錯策略而不自知的機會低很多(這個代價可以大過慢);交易機制貼近真實券商,日後接紙上交易時回測與生產可共用同一套語意;內建 bootstrap 對應 D-002 的蒙地卡羅要求。另有一個未實測的折衷:兩個都接,互動與掃描走 vectorbt、落地驗證走 PyBroker,互相對帳(本次已證兩邊會收斂到同一答案),代價是維護兩套適配層。

### A-001 判定:成立(holds)

「維持秒級」成立且有餘裕(0.332 秒,是次秒級)。「足以流暢表達」成立(27 行,不算扭曲)。**但「配 from_order_func」一句要更正:全程沒有動用 from_order_func**——`from_orders` 配 `size_type="targetpercent"`、`cash_sharing=True`、`call_seq="auto"` 就表達得到,即實際比假設所預期更淺,不是更差。後果條款(基於 vectorbt 的適配層工作會白做)不觸發,故記 holds,原文不改。

### 未解與風險

PyBroker 的 1,000 組是外推;多核並行兩邊都未實測;合成數據沒有停牌、除權除息、成交量約束與存活者偏差,**引擎正確性本次完全沒有考到**;費用與滑點設為零以求公平,開啟後兩邊會分歧;vectorbt 掃描的批次大小要自己管(25 組約 0.5 GB,1,000 組一次過需約 20 GB,這部機頂不住)。

### 產物(全部在 experiments/2026-08-bakeoff/)

代碼 `karst_spec.py`(共用考題規格)、`gen_data.py`(種子 20260825)、`vbt_bakeoff.py`、`pb_bakeoff.py`、`compare.py`、`count_lines.py`;依賴 `requirements-vbt.txt`(59 個套件)、`requirements-pb.txt`(52 個套件);數據 `results/timings.csv`(耗時數據表)、`results/agreement.csv` 與 `agreement.json`(兩邊一致性)、`results/vbt_sweep_returns.csv`(1,000 組)、`results/pb_sweep_returns.csv`(20 組)、`results/linecounts.json`、`results/vbt_single.json`、`results/pb_single.json`、`data/panel.parquet`。重跑指令見各腳本的 `--mode single` / `--mode sweep`。

**一項要交低的事:**本票原定把敘述版對比報告寫成 `experiments/2026-08-bakeoff/REPORT.md`,但執行這張票的子 agent 被工具層規則擋住,不准建立報告類 .md 檔(連試兩次,確定性否決)。所以逐項對比與建議改為完整寫在本節(在倉內,符合「結論必須落檔」),敘述長版已交回主 session。**REPORT.md 目前不存在,不要引用該路徑。**

## 留言
