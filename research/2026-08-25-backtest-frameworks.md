# 回測框架調研:借用、自建,定混合

- 票號:KARST-001
- 日期:2026-08-25(所有 GitHub 數字以此日經 GitHub API 讀取為準)
- 交付品:KARST-D01「Karst v1 規格」
- 依據:D-002(產品形態)、D-005(先查 GitHub、不預設自建)、D-006(選股與組合層為主場景)

---

## 一、一句話結論

**建議走「混合」:引擎借用,語意層與介面自建。**首選是以 [vectorbt](https://github.com/polakowo/vectorbt) 或 [PyBroker](https://github.com/edtechre/pybroker) 其中一個作向量化組合模擬核心(兩者先做一次短期併行試跑再定),因子合約與單一定義資料層自建,蠟燭圖介面用 [TradingView lightweight-charts](https://github.com/tradingview/lightweight-charts) 自建。

**沒有任何一個現成方案可以整套搬過來。**理由不是它們不好,而是三件事同時成立:(1) 主場景是橫斷面選股與組合層回測,而市面上大部分成熟框架的重心在單一標的擇時或 tick 級執行;(2) D-002 要求資料庫單一定義,而每個現成框架都會強加自己的資料模型;(3) 帶完整介面的開源交易平台幾乎全部是加密貨幣機器人,沒有一個服侍股票組合回測。

---

## 二、評估準則與評分方式

八項準則直接取自本票工作內容(來源為 D-002、D-003、D-006):

| 代號 | 準則 |
|---|---|
| C1 | 多策略共存 |
| C2 | 自定量化因子(含由非結構化材料轉成的因子)接得入 |
| C3 | 換倉節奏由策略自訂 |
| C4 | 單一定義資料層親和度(不迫你養第二份資料影像) |
| C5 | 紙上交易 / 排程運行 |
| C6 | 矩陣式(向量化)性能與蒙地卡羅模擬 |
| C7 | 蠟燭圖 UI 連出入場標記,或可嵌入自家應用 |
| C8 | 橫斷面選股與組合層回測是主場景(主打 tick 級執行者按 D-006 降權) |

評分:**✅ 合用** / **◐ 要自行改造才合用** / **✕ 不合用或方向相反**

---

## 三、主評估表

| 方案 | C1 多策略 | C2 自定因子 | C3 節奏 | C4 資料層 | C5 紙上交易 | C6 矩陣/蒙地卡羅 | C7 蠟燭圖 UI | C8 橫斷面組合 | 總評 |
|---|---|---|---|---|---|---|---|---|---|
| **vectorbt** | ✅ | ✅ | ✅ | ✅ | ◐ | ✅ | ◐ | ◐ | **核心候選** |
| **PyBroker** | ✅ | ✅ | ✅ | ✅ | ◐ | ✅ | ✕ | ✅ | **核心候選** |
| **qlib** | ✅ | ✅ | ◐ | ◐ | ◐ | ◐ | ✕ | ✅ | 次選 |
| **QuantConnect Lean** | ✅ | ✅ | ✅ | ✕ | ✅ | ✕ | ◐ | ✅ | 次選(重) |
| **zipline-reloaded** | ◐ | ✅ | ✅ | ✕ | ✕ | ✕ | ✕ | ✅ | 不建議(維護停滯) |
| **bt** | ✅ | ✅ | ✅ | ✅ | ✕ | ✕ | ✕ | ✅ | 配件級 |
| **backtrader** | ✅ | ✅ | ✅ | ◐ | ◐ | ✕ | ◐ | ◐ | 不建議(已停更) |
| **backtesting.py** | ✕ | ◐ | ◐ | ✅ | ✕ | ✕ | ◐ | ✕ | 不合用 |
| **NautilusTrader** | ✅ | ◐ | ✅ | ✕ | ✅ | ✕ | ✕ | ◐ | 不合用(方向相反) |
| **Freqtrade** | ◐ | ◐ | ◐ | ✕ | ✅ | ✕ | ✅ | ✕ | 不合用(加密貨幣) |
| **QuantDinger** | ◐ | ◐ | ◐ | ✕ | ✅ | ✕ | ✅ | ◐ | 不建議(見 §六) |
| **StockSharp / Jesse / OctoBot / Hummingbot** | — | — | — | — | — | — | — | ✕ | 不合用(見 §六) |

---

## 四、逐個方案的判斷與出處

### 4.1 vectorbt — 唯一真正「矩陣式」的候選

- Repo:<https://github.com/polakowo/vectorbt> ・ 文件:<https://vectorbt.dev>
- **C6 向量化(✅)**:官方自述「packs thousands of configurations into NumPy arrays, accelerates the hot path with Numba and Rust」——把成千上萬組參數打包成 NumPy 陣列一次過算。這正正對應 D-002 用戶原話「matrix based … can simulate lot of trade in a sec」。蒙地卡羅方面,套件提供 `Portfolio.from_random_signals()` 與隨機信號產生器,可以做隨機對照與穩健性檢驗([討論串](https://github.com/polakowo/vectorbt/discussions/674))。
- **C8 組合層(◐)**:官方 Portfolio 文件明寫支援分組與共用現金——「Groups can be formed to share capital between columns (make sure to pass `cash_sharing=True`)」,並示範把組合分成幾個共用同一筆現金的組別([Portfolio API](https://vectorbt.dev/api/portfolio/base/))。換言之組合層是做得到的,但**橫斷面排名與選股不是一等公民**:要自己先把排名算成權重向量,再經 `from_order_func` 逐個換倉日下單。社群討論明確指出這條路要自己寫「每月選股 + 再平衡」的函式([Discussion #237](https://github.com/polakowo/vectorbt/discussions/237))。這是要付出的工程量,不是缺陷。
- **C7 圖表(◐)**:內建 Plotly 互動圖與出入場標記,但那是分析用圖表,不是可嵌入自家應用的蠟燭圖介面。要達到 D-002 的 TradingView / Futu 體驗,仍要自建前端。
- **C4 資料層(✅)**:吃 pandas DataFrame,不強加自家儲存格式——這一點對「單一定義」極重要。
- **C5 紙上交易(◐)**:沒有內建的持續運行 / 排程 / 落單模組,要自己接。

### 4.2 PyBroker — 橫斷面排名是一等公民

- Repo:<https://github.com/edtechre/pybroker> ・ 文件:<https://www.pybroker.com/>
- **C8(✅)**:官方文件列明支援跨多個標的執行規則,並有專章「Ranking Long and Short Signals」——排名選股是內建功能,不用自己砌。這是它相對 vectorbt 最大的優勢。
- **C6(✅)**:自述「a super-fast backtesting engine built in NumPy and accelerated with Numba」,並內建 walkforward 分析與 **randomized bootstrapping** 的績效指標——後者就是蒙地卡羅式穩健性檢驗的標準做法。
- **C7(✕)**:沒有圖表介面。
- 維護:2026-08-24 有推送,只有 5 條未結 issue——維護紀律相當好。

### 4.3 qlib — 概念上最貼近,但節奏在放慢

- Repo:<https://github.com/microsoft/qlib> ・ 文件:<https://qlib.readthedocs.io/>
- **C2、C8(✅)**:內建運算式引擎,用 `'$close'`、`'Ref($close, 1)'`、`'Mean($close, 3)'` 這類寫法定義因子,並附 Alpha158 / Alpha360 因子集;回測本身就是橫斷面選股加組合分析(累計報酬、資訊系數、風險指標)。整個平台的世界觀就是 Karst 的世界觀。
- **授權最乾淨**:MIT。若 Karst 日後要商品化,這一點是決定性優勢(見 §五)。
- **C4(◐)**:qlib 有自己的 `.bin` 壓縮資料格式與 DataServer,等於要養第二份資料影像——與 D-002「no second image」正面衝突,需要改造。
- **維護風險**:過去一年只有 **29 次 commit**,而未結 issue 有 **469 條**。星數(47,928)與實際開發節奏嚴重脫節。這不是死項目,但不是一個你想把地基押上去的活躍度。

### 4.4 QuantConnect Lean — 框架概念與 Karst 一一對應,但太重

- Repo:<https://github.com/QuantConnect/Lean> ・ 文件:<https://www.quantconnect.com/docs/v2/>
- **概念對位極好**:Lean 的 Algorithm Framework 分五層——Universe Selection(選標的)→ Alpha(出信號)→ Portfolio Construction(轉成持倉目標)→ Risk Management → Execution。官方文件明寫它擅長「portfolio rebalancing, ranking, and multi-factor style strategies」。這幾乎就是 Karst 的因子→信號→組合的分層。
- **C5(✅)**:紙上交易與實盤接駁是內建能力。
- **C6(✕)**:事件驅動逐 tick 推進,不是向量化。大規模參數掃描與蒙地卡羅會很慢——與 D-002 的性能訴求相反。
- **C4(✕)**:強制使用 Lean 自家的資料格式與目錄結構。
- **成本風險**:官方 Lean CLI 文件寫明「To use the CLI, you must be a member in an organization on a paid tier」——即本機回測要經 CLI 就要付費組織席位([Tier Features](https://www.quantconnect.com/docs/v2/cloud-platform/organizations/tier-features))。引擎本體是 Apache-2.0,理論上可繞過 CLI 自行編譯運行,但那條路未經本次調研實測,列為待驗證。
- **C7(◐)**:漂亮的蠟燭圖與回測報表在 QuantConnect 雲端平台,本機執行沒有介面。

### 4.5 zipline-reloaded — 概念最正統,但實質已停滯

- Repo:<https://github.com/stefan-jansen/zipline-reloaded>
- **Pipeline API 是橫斷面回測的原型設計**:官方 API 參考文件載有 `Factor.rank()`、`top()`、`bottom()`、`quantiles()`、`zscore()` 等橫斷面運算,加上 `CustomFactor` 自定因子與 `schedule_function` / `date_rules` 排程換倉。單看設計,這是所有候選中最貼合 Karst 的一個。
- **但是**:過去一年只有 **4 次 commit,全部是 dependabot 自動升級依賴**(2025-11-13,訊息為「Bump actions/checkout from 4 to 5」一類)。獨立評估服務 Snyk 把它的維護狀態列為 **Inactive**。作者 Stefan Jansen 的自述亦只是「trying to keep the library up to date」——維持可用,不是繼續開發。
- 結論:可以參考它的 Pipeline 設計來自建 Karst 的因子層,**但不應該把它當地基**。

### 4.6 backtrader — 已停更近兩年

- Repo:<https://github.com/mementum/backtrader>
- 22,959 星,但**最後一次推送是 2024-08-19,過去一年 commit 數為 0**。社群接手的 fork [backtrader2/backtrader](https://github.com/backtrader2/backtrader) 只有 268 星,而且最後推送是 2024-03-24——連 fork 也停了。
- 就算功能合用,把一個停更兩年的 GPL-3.0 專案當地基,是把 Karst 的未來押在一個沒有人維護的引擎上。**不建議。**

### 4.7 backtesting.py — 結構上做不到 Karst 的主場景

- Repo:<https://github.com/kernc/backtesting.py>
- 維護正常(2026-07-22 發 0.6.6),但**單標的**是它的結構前提。官方定位是「supports any financial instrument with OHLC(V) candlestick data」——是「任何一個」,不是「同時多個」。社群多年來的多標的支援 PR([#639](https://github.com/kernc/backtesting.py/pull/639)、[#641](https://github.com/kernc/backtesting.py/pull/641))至今仍是 WIP,議題 [#196「Are there plans to support multi-asset portfolio rebalancing?」](https://github.com/kernc/backtesting.py/issues/196) 與 [#1120](https://github.com/kernc/backtesting.py/issues/1120) 長期未解。
- 它正正是 D-006 明文排除的那種工具:單股入場時機優化。**不合用。**
- 附註:授權為 AGPL-3.0,是本次調研中傳染性最強的授權。

### 4.8 NautilusTrader — 工程質素最高,但方向與 D-006 相反

- Repo:<https://github.com/nautechsystems/nautilus_trader>
- 過去一年 **5,178 次 commit**,是全部候選中最活躍的。Rust 核心、確定性事件驅動、回測與實盤共用同一套執行語意。
- 但它的自述是「quote tick, trade tick, bar, order book, and custom data with **nanosecond resolution**」——**納秒級 tick 執行細節正是它的賣點**,而 D-006 明令 Karst「不做日內交易、不做剝頭皮」。按票上規則,這類方案要降權。
- 官方文件亦明寫 **「UI dashboards」屬於 out of scope**——不會有介面。
- 授權 LGPL-3.0,靜態連結時有額外義務要留意。

### 4.9 bt — 換倉邏輯寫得最漂亮,適合做配件

- Repo:<https://github.com/pmorissette/bt> ・ 文件:<http://pmorissette.github.io/bt>
- Algo 堆疊設計(`RunMonthly()` → `SelectAll()` → `WeighEqually()` → `Rebalance()`)把「換倉節奏是策略參數」這件事表達得極清楚,值得 Karst 的策略 DSL 直接借鑑。
- 但官方文件自己承認性能是取捨:「usability will always be the priority」,速度改善仍在 roadmap 上。**做不到 D-002 的矩陣式性能要求**,只宜當基準策略與組合規則的參考或配件。

---

## 五、授權(licence):本次調研最重要的一個發現

**兩個性能最合用的候選,都帶 Commons Clause。**

| 方案 | 授權 | 對 Karst 的意義 |
|---|---|---|
| vectorbt | Apache-2.0 **+ Commons Clause** | 內部自用可以;**不可以**售賣主要價值來自它的產品或服務 |
| PyBroker | Apache-2.0 **+ Commons Clause** | 同上 |
| qlib | MIT | 無限制 |
| QuantConnect Lean | Apache-2.0 | 無限制 |
| zipline-reloaded | Apache-2.0 | 無限制 |
| bt / Jesse / PyPortfolioOpt | MIT | 無限制 |
| backtesting.py | AGPL-3.0 | 傳染性最強;經網絡提供服務亦須開源 |
| backtrader / Freqtrade / OctoBot | GPL-3.0 | 傳染性強 |
| NautilusTrader | LGPL-3.0 | 動態連結可,靜態連結有義務 |

Commons Clause 原文:「the grant of rights under the License will not include … the right to **Sell** the Software」,而「Sell」定義為「to provide to third parties, for a fee or other consideration … a product or service whose value derives, entirely or substantially, from the functionality of the Software」(來源:[vectorbt 授權頁](https://vectorbt.dev/terms/license/))。

**判斷:** 若 Karst 永遠只是用戶自用的內部工具,Commons Clause 不構成障礙。若 Karst 有可能變成賣出去的產品或收費服務,vectorbt 與 PyBroker 兩條路就要重新考慮,屆時 qlib(MIT)與 Lean(Apache-2.0)的優先次序會反轉。**這是一個需要用戶自己回答的商業問題,不是技術問題。**

---

## 六、帶完整 UI 的開源交易平台:為何全部不合用

票上要求查「任何帶完整 UI 的開源交易平台」。查完的結論是:**這一類平台存在,而且做得很好,但幾乎全部服侍加密貨幣的單標的機器人,沒有一個服侍股票的橫斷面組合回測。**

| 平台 | 星數 | 介面 | 為何不合用 |
|---|---|---|---|
| [Freqtrade](https://github.com/freqtrade/freqtrade) | 53,622 | FreqUI:網頁應用,有蠟燭圖、指標設定器、可在介面內跑回測並比較歷史回測結果 | 官方文件明寫**只支援加密貨幣**,沒有股票功能。介面做得好,值得當 Karst 介面的參考標竿 |
| [Hummingbot](https://github.com/hummingbot/hummingbot) | 19,600 | 有 | 做市與高頻導向,加密貨幣 |
| [Jesse](https://github.com/jesse-ai/jesse) | 8,374 | 有 GUI | 加密貨幣 |
| [OctoBot](https://github.com/Drakkar-Software/OctoBot) | 6,462 | 有 | 加密貨幣 |
| [StockSharp](https://github.com/StockSharp/StockSharp) | 10,636 | Designer GUI(.NET / Windows) | 覆蓋股票與期權,但是 C#/.NET Windows 桌面棧,與 Python 因子生態脫節;授權非標準 SPDX |
| [QuantDinger](https://github.com/OpenByteInc/QuantDinger) | 11,079 | Vue 網頁,自稱自托管的 TradingView / QuantConnect 替代 | **不建議**,見下 |

**QuantDinger 要特別留意。**表面上最貼合:自托管、有回測、有網頁蠟燭圖、接 Interactive Brokers 與 Alpaca、Apache-2.0。但四個警號:(1) repo 建於 **2025-12-28**,八個月內累積 11,079 星與 2,327 fork,fork 對星比例異常地高;(2) **前端與流動版並非開源**,README 註明使用「separate source-available licenses」,並提供商業授權——即「Apache-2.0」只覆蓋後端;(3) README 沒有任何關於組合層回測抑或單標的回測的說明,回測引擎是什麼亦未披露;(4) 定位是加密貨幣為主,股票為輔。**一個八個月大、核心介面不開源、回測能力未披露的專案,不應該成為 Karst 的地基。**

---

## 七、圖表件

D-002 要求蠟燭圖上看到出入場點,對標 TradingView / Futu。這一格反而最清晰:

- **[TradingView lightweight-charts](https://github.com/tradingview/lightweight-charts)**(17,059 星,Apache-2.0,2026-08-21 有推送)是業界事實標準。TradingView 官方維護、體積小、Canvas 繪製、支援標記(markers),正是出入場標記所需。**建議直接採用。**
- Python 端封裝要小心:[louisnw01/lightweight-charts-python](https://github.com/louisnw01/lightweight-charts-python)(2,114 星)**最後推送是 2024-09-28,已近兩年無人維護**,不建議依賴。
- Streamlit 生態的封裝多數是個人小專案(最大的 [freyastreamlit/streamlit-lightweight-charts](https://github.com/freyastreamlit/streamlit-lightweight-charts) 225 星,2023 年後無更新),同樣不宜依賴。
- **結論:直接用 lightweight-charts 的 JavaScript 原生 API 自建前端,不經第三方封裝。**

---

## 八、可以直接借用的配件(這幾格不用自建)

| 用途 | 方案 | 星數 | 授權 | 狀態 |
|---|---|---|---|---|
| 因子有效性檢定(IC、分層報酬) | [alphalens-reloaded](https://github.com/stefan-jansen/alphalens-reloaded) | 634 | Apache-2.0 | 2025-12-15 推送,慢但可用 |
| 績效報表(夏普、回撤、對基準比較) | [quantstats](https://github.com/ranaroussi/quantstats) | 7,586 | Apache-2.0 | 2026-07-20 推送,活躍 |
| 組合層優化(D-006 的 optimisation) | [Riskfolio-Lib](https://github.com/dcajasn/Riskfolio-Lib) | 4,456 | BSD-3 | 2026-08-18 推送,6 條未結 issue,最健康 |
| 組合層優化(替代) | [PyPortfolioOpt](https://github.com/PyPortfolio/PyPortfolioOpt) | 5,981 | MIT | 2026-07-07 推送 |
| 蠟燭圖 | [lightweight-charts](https://github.com/tradingview/lightweight-charts) | 17,059 | Apache-2.0 | 活躍 |

D-006 明寫「optimisation is on portfolio level」——Riskfolio-Lib 與 PyPortfolioOpt 正是這一格的成熟答案,**這部分完全不需要自建。**

---

## 九、維護活躍度記錄(2026-08-25 經 GitHub API 讀取)

「近一年 commit」= GitHub Search Commits API,條件 `committer-date:>2025-08-25`。

| Repo | 星 | Fork | 未結 Issue | 最後推送 | 近一年 commit | 判斷 |
|---|---|---|---|---|---|---|
| nautechsystems/nautilus_trader | 27,756 | 3,582 | 115 | 2026-08-25 | **5,178** | 極活躍 |
| QuantConnect/Lean | 21,347 | 5,191 | 267 | 2026-08-25 | **416** | 很活躍 |
| polakowo/vectorbt | 8,826 | 1,134 | 137 | 2026-08-02 | **147** | 活躍 |
| pmorissette/bt | 2,964 | 493 | 85 | 2026-08-07 | **75** | 穩定維護 |
| kernc/backtesting.py | 8,881 | 1,519 | 67 | 2026-08-05 | **33** | 穩定維護 |
| microsoft/qlib | 47,928 | 7,599 | **469** | 2026-07-23 | **29** | 明顯放慢 |
| stefan-jansen/zipline-reloaded | 1,927 | 328 | 44 | 2026-01-06 | **4**(全 dependabot) | **停滯** |
| mementum/backtrader | 22,959 | 5,246 | 63 | **2024-08-19** | **0** | **已停更** |
| edtechre/pybroker | 3,515 | 452 | **5** | 2026-08-24 | 未查 | 活躍、issue 紀律好 |
| freqtrade/freqtrade | 53,622 | 11,148 | 31 | 2026-08-25 | 未查 | 極活躍 |
| tradingview/lightweight-charts | 17,059 | 2,578 | 126 | 2026-08-21 | 未查 | 活躍(官方維護) |
| OpenByteInc/QuantDinger | 11,079 | 2,327 | 64 | 2026-08-24 | 未查 | 活躍但**建於 2025-12-28**,太新 |
| louisnw01/lightweight-charts-python | 2,114 | 431 | 123 | **2024-09-28** | 未查 | **已停更** |

**額外一項重要更新:**vectorbt 開源版並非坊間傳說中的「已被 PRO 版取代而放棄」。PyPI 紀錄顯示它在 **2026-04-22 發布 1.0.0、2026-07-05 發布 1.1.0**,是一次實質的大版本推進。不過官方仍自述開源版是 PRO 版的「community edition」,PRO 為付費閉源(約每月 20 美元),兩者的功能差距長期存在——這是採用時要接受的前提。

---

## 十、建議:混合(borrow the engine, build the meaning)

### 借用

| 層 | 採用 | 理由 |
|---|---|---|
| 向量化模擬核心 | vectorbt 或 PyBroker(二擇一,先試跑) | 唯二同時滿足 C6 矩陣式性能與 C8 組合層的方案 |
| 組合層優化 | Riskfolio-Lib(主)/ PyPortfolioOpt(備) | D-006 的 optimisation 一格,成熟且授權乾淨 |
| 因子檢定 | alphalens-reloaded | 因子有效性的標準工具 |
| 績效報表 | quantstats | 與基準對照的標準報表 |
| 蠟燭圖 | lightweight-charts(JS 原生 API) | 業界標準,官方維護,支援出入場標記 |

### 自建

| 層 | 為何必須自建 |
|---|---|
| **因子合約與單一定義資料層** | D-002 明令「All database should have only 1 definition, no second image」。每一個現成框架都會強加自己的資料模型(qlib 的 `.bin`、Lean 的目錄結構、zipline 的 bundle)。這一層是 Karst 的正本,不能外判。KARST-003 因子合約票正是這一格。 |
| **非結構化材料轉因子的管線** | D-003 明令這是通用能力,不是單一策略專屬。市面上沒有任何回測框架提供這一格——這是 Karst 的差異化所在,亦是它最不像一個現成框架能覆蓋的部分。 |
| **策略註冊與多租戶** | 「策略是引擎的租戶,各有自己的換倉節奏參數」(CONTEXT.md)。所有框架都能跑多策略,但沒有一個提供 Karst 需要的策略登記與比較語意。 |
| **應用介面** | §六已證:沒有一個開源平台提供股票組合回測的介面。 |
| **紙上交易的排程運行** | vectorbt 與 PyBroker 都沒有這一格,要自己接排程器與行情更新。 |

### 為何不是「全借」

Lean 是唯一一個「全借」有機會成立的方案(框架分層、紙上交易、實盤都齊)。但它在 D-002 最硬的兩格上不合格:**不是向量化**(事件驅動逐 tick,大規模參數掃描與蒙地卡羅會慢),而且**強制自己的資料格式**(直接違反單一定義)。加上 CLI 的付費組織席位要求,把它當地基的代價高於收益。

### 為何不是「全自建」

自建一個正確的組合層回測引擎,難的不是撮合邏輯,是**前視偏差(look-ahead bias)、存活者偏差、企業行動調整、成交量約束**這幾樣——每一樣都是需要數年打磨的陷阱,而 vectorbt / PyBroker / Lean 已經替你踩過。D-005 明令不預設自建,調研結果支持這個判斷:**引擎這一格,借用是對的。**

---

## 十一、風險

| 風險 | 嚴重度 | 說明與緩解 |
|---|---|---|
| **Commons Clause 商業化封鎖** | 高(如有商業化打算) | vectorbt 與 PyBroker 都不容許售賣主要價值源自它的產品或服務。緩解:把引擎放在一個薄的轉接層(port)之後,令日後可換成 qlib(MIT)或 Lean(Apache-2.0)而不動上層 |
| **vectorbt 的橫斷面選股要自己砌** | 中 | `from_order_func` 加共用現金分組寫起來不直觀,學習曲線陡。緩解:這正是要先試跑再定的原因 |
| **開源版與 PRO 版的功能差距** | 中 | vectorbt 開源版落後 PRO 版,且差距由作者控制。緩解:同上,轉接層 |
| **配件維護不均** | 低至中 | alphalens-reloaded 只有 634 星、更新緩慢。緩解:它的計算不複雜,必要時可自行接手 |
| **自建介面的工作量被低估** | 中 | 「用 lightweight-charts 自建」一句寫得容易,實際是一個完整的前端項目。緩解:介面形態由 KARST-007 拍板時要一併估工 |
| **單一定義與框架資料模型的張力** | 中 | 就算選了 vectorbt(吃 pandas,最寬鬆),回測期間仍會產生中間態資料。緩解:在 KARST-003 因子合約中明確界定「什麼是正本、什麼是可重算的派生物」 |

---

## 十二、待驗證的前提(建議下一步)

本報告的首選建議建基於一個**尚未實測**的前提:

> **vectorbt 的分組共用現金機制(`group_by` + `cash_sharing=True`)配 `from_order_func`,足以流暢表達「每月按因子排名選 N 隻股票並再平衡」這個 Karst 的主場景,而且在數百隻股票、十年日線的規模上維持秒級。**

這一條由官方文件與社群討論支持,但**沒有實跑驗證**。若它為假,引擎選型要改投 PyBroker 或 qlib,而基於 vectorbt 寫的所有適配層工作會白做。

**建議下一步(另開票):** 用同一個玩具策略(例:100 隻股票、10 年日線、每月按單一因子排名取前 10 名等權重),在 **vectorbt 與 PyBroker 上各實作一次**,比較三件事:(1) 表達這個策略要寫多少行、直不直觀;(2) 一次回測與 1,000 組參數掃描各要多久;(3) 接自家資料層有多順。用實測數字定案,不用文件宣稱定案。

---

## 十三、最終裁決

**本報告只提供建議,最終走「借用 / 自建 / 混合」哪一條路,由用戶裁決。**

需要用戶回答的,其實只有一個先決問題:

> **Karst 將來有沒有可能變成賣出去的產品或收費服務?**

- **沒有(純自用)** → 建議如 §十:vectorbt 或 PyBroker 為核心,混合路線。
- **有可能** → Commons Clause 成為障礙,建議改以 **qlib(MIT)** 為核心候選,並接受它維護節奏放慢的風險;或以 **Lean(Apache-2.0)** 為核心而放棄向量化性能。

這是一個商業問題,不是技術問題,所以本票不代答。

---

## 出處一覽

**GitHub 倉庫(數據經 GitHub API 於 2026-08-25 讀取)**
- vectorbt — <https://github.com/polakowo/vectorbt>
- PyBroker — <https://github.com/edtechre/pybroker>
- qlib — <https://github.com/microsoft/qlib>
- QuantConnect Lean — <https://github.com/QuantConnect/Lean>
- zipline-reloaded — <https://github.com/stefan-jansen/zipline-reloaded>
- backtrader — <https://github.com/mementum/backtrader> ・ fork:<https://github.com/backtrader2/backtrader>
- backtesting.py — <https://github.com/kernc/backtesting.py>
- NautilusTrader — <https://github.com/nautechsystems/nautilus_trader>
- bt — <https://github.com/pmorissette/bt>
- Freqtrade — <https://github.com/freqtrade/freqtrade>
- Hummingbot — <https://github.com/hummingbot/hummingbot>
- Jesse — <https://github.com/jesse-ai/jesse>
- OctoBot — <https://github.com/Drakkar-Software/OctoBot>
- StockSharp — <https://github.com/StockSharp/StockSharp>
- QuantDinger — <https://github.com/OpenByteInc/QuantDinger>
- lightweight-charts — <https://github.com/tradingview/lightweight-charts>
- lightweight-charts-python — <https://github.com/louisnw01/lightweight-charts-python>
- alphalens-reloaded — <https://github.com/stefan-jansen/alphalens-reloaded>
- quantstats — <https://github.com/ranaroussi/quantstats>
- Riskfolio-Lib — <https://github.com/dcajasn/Riskfolio-Lib>
- PyPortfolioOpt — <https://github.com/PyPortfolio/PyPortfolioOpt>

**官方文件**
- vectorbt Portfolio API(分組與共用現金)— <https://vectorbt.dev/api/portfolio/base/>
- vectorbt 授權條款(Commons Clause)— <https://vectorbt.dev/terms/license/>
- PyBroker 文件(多標的、排名、bootstrap)— <https://www.pybroker.com/>
- qlib 文件 — <https://qlib.readthedocs.io/en/latest/introduction/introduction.html>
- Lean Algorithm Framework — <https://www.quantconnect.com/docs/v2/writing-algorithms/algorithm-framework/overview>
- Lean CLI 付費層要求 — <https://www.quantconnect.com/docs/v2/cloud-platform/organizations/tier-features>
- zipline-reloaded API 參考(Pipeline / Factor.rank)— <https://github.com/stefan-jansen/zipline-reloaded/blob/main/docs/source/api-reference.rst>
- NautilusTrader 文件 — <https://nautilustrader.io/docs/latest/>
- FreqUI 文件 — <https://www.freqtrade.io/en/stable/freq-ui/>
- Freqtrade 文件 — <https://www.freqtrade.io/en/stable/>
- bt 文件 — <http://pmorissette.github.io/bt>

**社群討論與議題**
- backtesting.py 多資產議題 — <https://github.com/kernc/backtesting.py/issues/196> ・ <https://github.com/kernc/backtesting.py/issues/1120> ・ PR <https://github.com/kernc/backtesting.py/pull/639> ・ PR <https://github.com/kernc/backtesting.py/pull/641>
- vectorbt 組合再平衡討論 — <https://github.com/polakowo/vectorbt/discussions/674> ・ <https://github.com/polakowo/vectorbt/discussions/237>
- zipline-reloaded 維護狀態評估 — <https://snyk.io/advisor/python/zipline-reloaded>

**發行紀錄(PyPI)**
- vectorbt 1.1.0(2026-07-05)、1.0.0(2026-04-22)— <https://pypi.org/project/vectorbt/>
- zipline-reloaded 3.1.1 — <https://pypi.org/project/zipline-reloaded/>
- backtesting 0.6.6(2026-07-22)— <https://pypi.org/project/backtesting/>
- pyqlib 0.9.7 — <https://pypi.org/project/pyqlib/>
