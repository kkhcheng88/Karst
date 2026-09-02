# 知情時點規則(KARST-146 帳目面板)

本檔在任何面板數字產生**之前**獨立 commit。跑數腳本照這裡寫的做;兩者不符,以本檔為準,
腳本要改。

背景:KARST-140 與 KARST-145 兩次都踩同一個坑——用「期末日在月底之前」當作「當時知道」,
結果把公司幾個月後才公布的數字放進當月的決策裡,憑空多賺。本檔就是為了把那個坑封死。

---

## 一、核心規則:只准用「當日已經申報」的數字

面板的每一格是一個(公司,月底)的組合。

> **月底 m 的面板值 = 所有 `filed` ≤ m 的申報之中,期末日最近的那一期。**

`filed` 是證監會收到申報的日期,也就是公眾第一次看得到那個數字的日期。
`end` 是會計期末日。

**絕對不准**用 `end ≤ m` 當條件。2015 年 12 月 31 日那一刻,2015 全年業績還沒有申報
(通常要等到 2016 年 2 月),用 `end ≤ 2015-12-31` 等於偷看未來三個月。

實務上這代表面板有意做出「數字舊」的效果:三月底看到的多數還是去年第三季的數字,
因為第四季/全年還沒申報完。這不是缺陷,這正是當時投資者的處境。

## 二、首版優先,修訂版另存

同一期(同一個 `end`、同一個標籤)的數字,經常被後來的申報改寫——重述、會計政策變更、
或者只是後一份申報把去年那欄一併重貼。

- 面板主欄用**當時看得到的第一版**:在 `filed` ≤ m 的候選之中,同一期取 `filed` 最早那一個。
- 同一期最新一版的數字另存 `<欄名>_restated`,並附 `<欄名>_restated_filed`。
- `<欄名>_was_restated` 記錄該期後來有沒有被改過(布林)。

理由:回測要重演當時的決策,當時看到的是第一版。修訂版留住,是為了日後量度
「修訂幅度」本身(四件套的「修訂延續」那一格要用),不是拿來當主值。

補充:帶 `/A` 的修訂申報(10-K/A、10-Q/A)一律當修訂版,不會成為首版。

## 三、接受哪些申報

- 表格:`10-K`、`10-Q`、`20-F`、`40-F`,以及它們的 `/A` 修訂版(只作修訂版用)。
- 單位:金額只收 `USD`,股數只收 `shares`。其他計價貨幣一律不收——混幣種比缺數更危險。
- 分類體系:`us-gaap` 與 `ifrs-full`。公司自訂體系(`<公司名>` 命名空間)**不收**,
  但要數出來:某公司某欄若只在自訂體系有數,覆蓋率報告記為「只有自訂標籤」那一格。

## 四、標籤回退表(固定,不准為湊覆蓋率放寬)

沿用 `experiments/2026-09-02-tenbagger-casecontrol/fetch_fundamentals.py` 已跑通的十一欄
與其回退次序。回退次序是**優先次序**,不是「哪個有數用哪個」:

| 欄位 | 類型 | 標籤(按優先次序) |
|---|---|---|
| revenue | 流量 | Revenues / RevenueFromContractWithCustomerExcludingAssessedTax / RevenueFromContractWithCustomerIncludingAssessedTax / SalesRevenueNet / SalesRevenueGoodsNet / Revenue / RevenueFromContractsWithCustomers / RealEstateRevenueNet |
| gross_profit | 流量 | GrossProfit |
| net_income | 流量 | NetIncomeLoss / ProfitLoss / ProfitLossAttributableToOwnersOfParent |
| diluted_shares | 流量(股數) | WeightedAverageNumberOfDilutedSharesOutstanding / …BasicAndDiluted / WeightedAverageNumberOfSharesOutstandingBasic / WeightedAverageNumberOfShareOutstandingBasicAndDiluted / AdjustedWeightedAverageShares / WeightedAverageShares |
| cfo | 流量 | NetCashProvidedByUsedInOperatingActivities / …ContinuingOperations / CashFlowsFromUsedInOperatingActivities |
| capex | 流量 | PaymentsToAcquirePropertyPlantAndEquipment / PaymentsToAcquireProductiveAssets |
| assets | 存量 | Assets |
| liabilities | 存量 | Liabilities |
| equity | 存量 | StockholdersEquity / …IncludingPortionAttributableToNoncontrollingInterest / Equity |
| cash | 存量 | CashAndCashEquivalentsAtCarryingValue / CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents / CashAndCashEquivalents |
| lt_debt | 存量 | LongTermDebtNoncurrent / LongTermDebt / NoncurrentPortionOfBorrowings |

一家公司會中途換標籤(例如 2018 年會計準則改版,`SalesRevenueNet` 換成
`RevenueFromContractWithCustomer…`)。所以選標籤不是「拿第一個有數的」——那樣會拿到一條
早就停止更新的舊序列。做法:**在 `filed` ≤ m 的範圍內,選期末日最近的那條標籤序列**;
同期末日則取優先次序較前者。每一格記低實際用了哪個標籤(`<欄名>_tag`)。

## 五、存量欄(assets / liabilities / equity / cash / lt_debt)

資產負債表項目是「某一日的結餘」,證監會資料裡沒有 `start`,只有 `end`。
規則:`filed` ≤ m 的候選之中,`end` 最近的那一個;同 `end` 取 `filed` 最早(首版優先)。

## 六、流量欄(revenue / gross_profit / net_income / diluted_shares / cfo / capex)

流量項目有 `start` 與 `end`,跨度決定它是一季還是一年:

- **季度**:跨度 80–100 日
- **半年**:跨度 170–190 日(20-F/40-F 申報者常見,單獨標記,不混入季度)
- **年度**:跨度 330–400 日
- 其餘跨度(例如年初至今的九個月累計)一律**丟棄**——把累計數當季度數是另一種造假。

面板為每個流量欄同時提供三個值:

1. `<欄名>`:最近一期的原值,連同 `<欄名>_period`(`Q` / `H` / `FY`)。期別要看得見,
   因為 500 億的一季和 500 億的一年是兩回事。
   **同一個期末日撞期時,取跨度最短那一個**(`Q` 先於 `H`,`H` 先於 `FY`)。
   原因:一份 10-Q 同時印「本季」與「年初至今」兩欄,兩欄的期末日一模一樣。
   取長的那一欄等於把年初至今的累計數當成一季,同一家公司的 `revenue` 會在
   第一季(三個月)與第二季(六個月)之間跳,比較起來全錯。跨度最短的那一個
   才是離散的當期數。
2. `<欄名>_ttm`:最近四季滾動和。
3. `<欄名>_ttm_basis`:這個滾動和是怎麼砌出來的(見下)。

### 最近四季滾動和的砌法(季度化規則)

按以下次序,取第一個砌得成的:

- `four_quarters` —— 有四段連續、互不重疊、合共跨度 350–380 日的季度數,直接相加。
  這是最乾淨的一種。
- `fy_minus_three` —— 只有全年數與同一財政年度的頭三季(美國申報者的常態:
  10-K 只印全年,不印第四季)。第四季 = 全年 − 頭三季之和,再與後面幾季拼夠四季。
  用這條的前提是全年數與那三季**全部** `filed` ≤ m。
- `annual_only` —— 只有全年數。直接把全年數當作滾動和,並在 `_ttm_basis` 標明。
  這個值比實際落後最多一年,用的時候要知道。
- `insufficient` —— 砌不成,`<欄名>_ttm` 留空。**不准用少於四季的和去湊**,
  也不准把三季乘 4/3。

`gross_profit` 與 `capex` 常常只在年報出現,所以它們的 `_ttm_basis` 大多會是 `annual_only`;
這是事實,不是 bug,報告要照講。

`diluted_shares` 是加權平均股數,不是結餘。滾動和沒有意義,所以它**不做**四季和,
只取最近一期,並記低期別。

## 七、面板格式

- 一行 = (ticker, 月底日期)。月底 = 該月最後一個日曆日。
- 期間:2009-01-31 至 2026-08-31。2009 年之前證監會沒有結構化帳目,建了也是空的。
- 只在該公司**已經有至少一份申報**之後才出行;之後一路出到最後一份申報那個月為止
  (公司消失了就停,不會拖一條長長的空白尾)。
- 每行附:
  - `in_index`:該月底該公司是否標普 500 成分(用歷史成分名單的加入/剔除日判斷)。
  - `<欄名>_end`:這一格用的那一期的期末日。
  - `<欄名>_filed`:這一格用的那一版的申報日。
  - `<欄名>_age_days` = 月底 − `filed`。數字有多舊,一眼看得到。
    **不設上限剔除**——舊數字照留,要不要嫌它舊是策略層的事,不是數據層的事。

## 八、明確不做的事(本票範圍)

- 不做任何選股、排序、回測、訊號、比率排名。
- 不碰四件套過濾器的定義與參數。
- 不改倉根生產庫 `karst.sqlite`(全程只讀)。
- 不為了提高覆蓋率而加標籤、放寬跨度、或接受自訂體系。

## 九、已知會令面板偏樂觀的兩件事(誠實聲明)

1. **除牌公司的帳目補得回,股價補不回。** 證監會有它們的申報,免費行情源沒有它們的
   歷史價格。所以面板上會有一批「有帳目、無價格」的公司——它們在回測裡仍然不可交易。
   本票要把這批公司數出來,不負責補價格。
2. **拉不到 CIK 的成分股連帳目都沒有。** 歷史成分名單有 1,209 個代號,其中大部分已剔除的
   代號沒有留下公司名,對照不到證監會編號。逐個列在 `out/cik_missing.csv`。
   這一批在面板上完全缺席,倖存者偏差因此只修了一部分。

---

# v2 變更紀錄(KARST-158,2026-09-02)

**下游一律改讀 v2:`experiments/2026-09-02-panel-scale-fix/out/panel_monthly_v2.parquet`。
v1(`out/panel_monthly.parquet`)一個位元都沒有改,只留作追溯。**

## 為什麼要有 v2

第三節寫住「股數只收 `shares`」。這句話成立,但它保護不到本來想保護的東西:**部分公司
根本就把以千、以百萬為單位的數字,貼上了 `shares` 這個單位標籤去申報。** 原檔的 `unit`
欄照樣寫 `shares`,面板照單全收,於是同一欄裡混住了三種尺。KARST-156 順手撞到,入了
假設冊 A-041;本節是修補。

實例:MCD 有 31 格是 `732.3`(以百萬為單位)、COP 有 100 格是 `1,495,700`(以千為單位)、
GRMN 有 54 格是 `196,457`(以千為單位)、L 有 31 格是 `435.63`(以百萬為單位)、
FTI 有 4 格是 `1.0`(純垃圾)。

後果不是「數字醜一點」:凡是把面板股數乘價格當市值的做法,在那些格會錯三至六個量級,
而市值在分母,錯的方向一律是**把那隻股變成全市場最便宜**——它必然被價值類排名揀中。

## v2 改了哪一欄

只改 `diluted_shares` 與 `diluted_shares_restated` 兩欄的**數值**。行數、其他欄、
知情時點規則(第一至七節)一律不動。v2 另加兩欄留底:
`diluted_shares_v1_raw`、`diluted_shares_restated_v1_raw`(v1 原值,原封不動)。

## 校正規則(寫死,只用 10 的整數次方)

**偵測**照搬 KARST-156 `CRITERIA.md` 訂正一第 3.3′ 條,常數一字不改
(`0.7 / 1.5 / 6 / 0.35 / 100 / [1e5, 1e11]`)。在拆股對齊之後施行,逐家公司以自身
全樣本 `log10` 中位數為量級錨。

**裁決**多加一條線,這是 v2 相對 156 的唯一分別,理由在下面:

| 情況 | 做法 |
|---|---|
| 原值 < 100 股 | 判垃圾,設缺值 |
| 偏離錨 ≥ 30 倍、且落在某個整數 `k` 的 ±0.35 之內、**且封面頁股數(`dei:EntityCommonStockSharesOutstanding`)獨立指向同一個 `k`** | 除以 `10^k` |
| 偏離錨,但封面頁顯示原值本身已經對(相差五倍以內) | **不動** |
| 其餘(包括同期沒有封面頁數可對) | **設缺值,不猜** |
| 偏離錨 ≥ 5 倍但不落在任何 10 的整數次方上 | **保留**(3.3′ 第六條:那是真實公司行動,或者事件表欠缺的拆股) |
| 保留值換算到今日拆股基準後不在 `[1e5, 1e11]` 股之內、或者不是正數 | 設缺值 |

**為什麼一定要第二條線。** 單靠量級錨會把對的改壞。CPWR 是活證:它的原值 2,230 萬股
與封面頁相差不足 3%,本身完全正確;但拆股事件表裡有一宗 1:115 的反向拆股,是**後來
另一家公司用同一個代號**申報的,拆股對齊之後它的序列出現三個量級的斷層,錨會判它
「以千為單位」而乘一千。加了封面頁這條線之後,CPWR 這 49 格原封不動。

## 實測數字(`out/meta_v2.json` 為正本)

`diluted_shares` 欄,123,754 格之中:

| 項目 | 格數 |
|---|---:|
| 觸發偵測的候選格 | 2,199 |
| **判定為錯格** | **1,361** |
| ├ 校正(除以 10 的整數次方,封面頁印證) | 1,008 |
| ├ 垃圾值設缺值(< 100 股) | 22 |
| ├ 判不出倍數設缺值(兩條線不合或無封面頁可對) | 104 |
| ├ 換算後不在合理區間設缺值 | 113 |
| └ 非正數設缺值 | 114 |
| 候選但判定**沒有錯**、原值保留 | 838 |
| 非空格數 v1 → v2 | 120,302 → 119,949 |

`diluted_shares_restated`:校正 751、設缺值 409、保留 936。

第三條旁證(股價 × 股數 = 市值)同向:市值落在 `[1e7, 2e13]` 美元之外的格,
由 v1 的 540 格減到 v2 的 7 格。

## 三項誠實聲明

1. **校正依據是規則推斷加封面頁對照,不是逐格翻回原始申報正文核對。** 1,008 格全部有
   封面頁獨立印證同一個倍數,但封面頁本身也是機讀資料,不是人手核實。
2. **設缺值 353 格是真的沒有了,不是補了個估值。** 判不出就不猜,是刻意的取捨:
   缺一格,下游少一個觀測;猜錯一格,下游多一個假的極端值。
3. **封面頁股數(在外股數)與攤薄股數(加權平均)口徑不同,不可互替。** 本節只把它
   當刻度尺用——問「這個數字差了幾多個 10 倍」,不問「這兩個數字應不應該相等」。

## v2 修不到的一件事(留給下一張票)

拆股事件表(`fourpiece-test/data/splits.parquet`)按**代號**索引,代號會被重用。
CPWR、EP、PARA 的拆股因子被後來的使用者污染(0.0087 / 0.021 / 0.005),令這幾家的
市值在 KARST-148 的算法下細到荒謬(7 格,見 `out/scale_flags_mcap.csv`)。這是拆股
基準那一層的缺陷,不是股數刻度那一層,v2 沒有動它,亦不應該由 v2 動。
