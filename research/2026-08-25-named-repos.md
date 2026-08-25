# 指定倉調研:Vibe-Trading、myhhub/stock、QuantDinger、tradingview-mcp

- 票號:KARST-010
- 日期:2026-08-25(所有 GitHub 數字以此日經 GitHub API 讀取為準)
- 交付品:KARST-D01「Karst v1 規格」
- 依據:D-002(產品形態)、D-003(非結構化轉因子)、D-005(先查 GitHub、用戶裁決)、D-006(選股不擇時、組合層)、D-007(自用先行、SaaS 留門、引擎可換件)
- 前作:[KARST-001 回測框架調研](2026-08-25-backtest-frameworks.md)

---

## 零、一頁總結

| 倉 | 一句定位 | 授權 | 近一年 commit | 對 Karst 的處置 |
|---|---|---|---|---|
| [HKUDS/Vibe-Trading](https://github.com/HKUDS/Vibe-Trading) | AI 交易 agent 平台,自帶多市場組合回測引擎、因子庫、組合優化器與網頁介面 | MIT | **1,762** | **抽零件**(因子契約、因子庫、優化器)+ 借思路 |
| [myhhub/stock](https://github.com/myhhub/stock) | A 股日線選股與形態識別系統,自帶網頁介面 | Apache-2.0 | **29** | **只借思路**(選股條件表達、形態庫、批次編排) |
| [OpenByteInc/QuantDinger](https://github.com/OpenByteInc/QuantDinger) | 幣圈為主的自托管量化交易平台,後端開源、介面禁商用 | 後端 Apache-2.0 / 前端 source-available | **492** | **只借思路**(策略合約分層);不當地基 |
| [atilaahmettaner/tradingview-mcp](https://github.com/atilaahmettaner/tradingview-mcp) | 把 TradingView 篩選器與技術指標包成 MCP 工具給 AI 客戶端呼叫 | MIT | **122** | **抽一個零件**(美股篩選取數)+ 借思路;回測部分無可借 |

**對 KARST-001 的裁定:核心建議維持,補充三項,修訂一項。**四個倉沒有一個提供向量化引擎,所以「引擎借 vectorbt 或 PyBroker」的結論站得住。要修訂的是 KARST-001 對 QuantDinger 的其中一條指控——「回測引擎未披露」**經查不成立,須撤回**(詳見第五節)。

---

## 一、HKUDS/Vibe-Trading

### 1.1 定位一句

一個以 LLM 多 agent 為外殼、內裡藏著一套自研多市場組合回測引擎與因子庫的個人交易 agent 平台;研究、回測、組合優化、實盤落單一條龍。

### 1.2 架構與核心零件

倉頂層有 `agent/`、`frontend/`、`desktop/`、`wiki/` 四塊([倉根目錄](https://github.com/HKUDS/Vibe-Trading))。真正值錢的在 `agent/`:

| 位置 | 內容 |
|---|---|
| `agent/backtest/engines/` | `base.py`(約 2,000 行自研引擎)+ 分市場引擎:`global_equity.py`(**美股**)、`china_a.py`、`crypto.py`、`forex.py`、`india_equity.py`、`korea_equity.py`、`vietnam_equity.py`、`options_portfolio.py`、`composite.py`(跨市場) |
| `agent/backtest/loaders/` | 30 多個數據源接駁(Yahoo、Binance、CCXT、Tushare、AkShare、MT5 等) |
| `agent/backtest/optimizers/` | `mean_variance.py`、`risk_parity.py`、`equal_volatility.py`、`max_diversification.py`、`turnover_aware.py` |
| `agent/src/factors/` | `registry.py` + `base.py` + `zoo/`,zoo 分五格:`alpha101`、`gtja191`、`qlib158`、`academic`、`fundamental` |
| `frontend/` | React 19.2 + Vite + Tailwind,圖表用 **ECharts 6.1**([package.json](https://github.com/HKUDS/Vibe-Trading/blob/main/frontend/package.json)) |
| `desktop/` | Electron 桌面殼 |

**引擎性質(關鍵)**:`agent/backtest/engines/base.py` 是**逐根 K 線的 Python 迴圈**(核心是 `for i, ts in enumerate(dates)`),**不是向量化**。全部自己寫,沒有包 vectorbt / zipline / backtrader 任何一個。

**組合層做得到**:`agent/backtest/runner.py`(約 1,460 行)的設定檔明寫 `position_adjustment: Literal["hold", "rebalance"]` 與 `rebalance_tolerance`——「Under 'rebalance', a resize executes only once the held weight has drifted further than this fraction of its target」。引擎持有 `positions: Dict[str, Position]`,每根 K 線算一次目標權重矩陣並歸一化至 `abs(weights) ≤ 1.0`。多市場則轉交 `CompositeEngine`。

**策略契約**:用戶寫一個名為 `SignalEngine` 的 Python 類,實作
`def generate(self, data_map: Dict[str, pd.DataFrame]) -> Dict[str, pd.Series]`
——收「代號 → OHLCV 表」,回「代號 → 信號序列」。runner 用 AST 檢查把用戶代碼過濾一次才執行。

**因子契約(對 Karst 最有價值的一件)**:`agent/src/factors/base.py` 用的是結構協定,不是繼承:

```python
@runtime_checkable
class AlphaCompute(Protocol):
    def __call__(self, panel: dict[str, pd.DataFrame]) -> pd.DataFrame: ...
```

輸入是 `index=trading_date`、`columns=instrument_code` 的寬表字典,輸出同形狀的因子分數表。註冊表強制三條紀律:NaN 必須傳遞不准 `fillna(0)`、禁止 `±inf`、**禁止前視(delta 的 lag 必須 ≥ 1)**。

**防偏差**:引擎用 `shift(1)` 做次根開盤成交語意,並有 `historical_base_price()` 拒收未來收盤價。有佣金(`calc_commission`)與滑點(`apply_slippage`)。**未見**企業行動調整、存活者偏差過濾、成交量約束——這三格要自己補。

### 1.3 授權

**MIT**(`Copyright (c) 2026 Vibe-Trading Contributors`,[LICENSE](https://github.com/HKUDS/Vibe-Trading/blob/main/LICENSE)),全文標準,無 Commons Clause、無非商業限制。

對照 D-007:這是四個倉裡最乾淨的一個。自用無阻,日後商品化亦無阻。

### 1.4 活躍度(2026-08-25 GitHub API)

| 項目 | 數值 |
|---|---|
| 星 | 31,683 |
| Fork | 5,151 |
| 未結 issue | **26** |
| 建立日 | 2026-04-01 |
| 最後推送 | 2026-08-25(當日) |
| 近一年 commit | **1,762** |
| 主要貢獻者 | warren618(909)、santhreal(176)、shadowinlife(85),另有 60+ 名尾巴 |

**可信度要打的折扣,要如實講。**HKUDS 這個實驗室是一部高星倉機器:同一個組織下 `CLI-Anything` 48,182 星、`nanobot` 47,378 星、`OpenHarness` 15,528 星、`OpenSpace` 7,457 星——**全部都是 2026 年內建立的**([HKUDS 倉列表](https://github.com/orgs/HKUDS/repositories))。換言之,31,683 星反映的是這個實驗室的發行力,**不是這個項目的生產成熟度**,不應該當作品質證據。

另外兩個要留意的形態:README 有 **248 KB**(另有五個語言版本,阿拉伯文版 318 KB),長度遠超一般說明文件;最近 20 條 issue 與 PR 幾乎全部零留言、同日開同日合併,並且問題與修補成對出現——這是 agent 驅動開發的形態,不是人手審查的形態。

代碼本身是紮實的(型別註記齊、docstring 齊、有 `tests/`),但「有沒有人真金白銀跑過」這一點,star 數答不到。

### 1.5 與 Karst 的契合度

| 準則 | 判斷 |
|---|---|
| D-002 矩陣式性能 | **✕** 逐根迴圈,不是向量化。跑千組參數掃描會慢 |
| D-002 蠟燭圖出入場 | **◐** 有 React 前端與 ECharts,但是綁死在它自己的 agent 世界觀裡 |
| D-002 單一定義資料層 | **◐** 引擎吃 `Dict[str, pd.DataFrame]`,不強加儲存格式(這點好);但整套 agent 有自己的 artifact store |
| D-003 非結構化轉因子 | **✕** 因子層只吃價量與基本面寬表。有新聞、研報、13F、本地文本情緒評分等 agent 工具,但**那些不入因子層**,兩者沒有接通 |
| D-006 美股選股 | **✅** `global_equity.py` 專門處理美股,S&P 500 為基準 |
| D-006 組合層 | **✅** 五個組合優化器 + 權重再平衡 + 容忍帶 |
| D-006 不做日內 | **✅** 日線導向,不是 tick 級 |
| D-007 授權 | **✅** MIT |

### 1.6 可借清單

| 處置 | 項目 | 理由 |
|---|---|---|
| **抽零件** | **因子契約的形狀**——`dict[str, pd.DataFrame] → pd.DataFrame`(日期 × 標的)加上「禁前視、禁 inf、NaN 必須傳遞」三條註冊表紀律 | 這正正是 KARST-003 因子合約票要定的東西,而且已經有人把邊界情況想過一遍。**建議直接當藍本讀。** |
| **抽零件** | `factors/zoo/` 的 alpha101、gtja191、qlib158、academic(Fama-French、Carhart 動量、BAB)、fundamental 五套因子定義 | MIT 授權,現成的橫斷面因子庫。Karst 的樽頸因子要對照的基準因子,這裡有齊 |
| **抽零件** | `backtest/optimizers/` 五個優化器 | 可以與 KARST-001 建議的 Riskfolio-Lib 對照,揀較合用的一套 |
| **借思路** | 引擎按市場分家(`global_equity` / `china_a` / `crypto` 各一個),共用一個 `base` | 若 Karst 日後不只做美股,這個分層值得抄 |
| **借思路** | 用戶策略代碼過 AST 檢查才執行 | Karst 若容許用戶自寫策略,這是現成的安全模式 |
| **不整件借** | 引擎本體、agent 層、前端 | 引擎非向量化(踩 D-002 最硬那一格);agent 層是 Karst 明文不要的「chat 加文件」形態(D-002);前端綁死它自己的資料模型 |

---

## 二、myhhub/stock(InStock)

### 2.1 定位一句

一套 A 股日線的選股與形態識別系統:每日抓東方財富數據、算 32 種技術指標、認 61 種 K 線形態、跑 11 條選股策略、統計命中率,全部呈現在自建網頁介面上。

### 2.2 架構與核心零件

- 後端 Python 3.11 + talib + pandas;資料庫 MySQL / MariaDB(自動建表);網頁介面在 `localhost:9988`;有 Docker 部署。
- 目錄:`instock/core/strategy/`(11 條策略)、`instock/core/backtest/`、`instock/job/`(每日批次)、`instock/trade/robot/`(自動交易)、`cron/`、`docker/`、`supervisor/`。
- 選股條件超過 200 項,橫跨股票池、基本面、技術面、情緒面(股吧人氣)、資金流(滬港通)。
- 內建策略十一條:放量上漲、均線多頭、停機坪、回踩年線、突破平台、無大幅回撤、海龜交易法則、高而窄的旗形、放量跌停、低 ATR 成長,以及一條基本面篩選(市盈率 ≤ 20、市淨率 ≤ 10、ROE ≥ 15%)。
- 籌碼分佈(chip distribution)以 210 個交易日為預設窗口計算成本分佈,自稱與東方財富專業終端對得上。
- 自動交易只在 Windows 行,靠 tesseract OCR 認同花順交易軟件的驗證碼。
- 全日流程(抓數 → 算指標 → 認形態 → 選股 → 統計)自述約四分鐘跑完。

### 2.3 「回測」的真身——這一點要講清楚

**它沒有回測引擎。**`instock/core/backtest/rate_stats.py` 全文約 45 行,核心是一句
`100 * (data['close'].values - close1) / close1`
——即由選中當日的收盤價起計,往後每日的累計漲跌百分比,預設看 101 個交易日。`instock/job/backtest_data_daily_job.py` 把這串數字寫回策略表。

**沒有現金、沒有持倉、沒有倉位大小、沒有交易成本、沒有基準對照。**這是「選股後 N 日漲了多少」的命中率統計,不是組合模擬。名字叫「回測」,實質是前向報酬統計。

這一點對 Karst 是決定性的:D-002 要求的是嚴謹成程式的引擎,這裡沒有可借的引擎。

### 2.4 授權

**Apache-2.0**(倉根有 11,357 bytes 的 LICENSE 檔,GitHub API 亦標示 `Apache-2.0`)。

README 自附免責:「股市有風險投資需謹慎,本系統只能用於學習、股票分析,投資盈虧概不負責」。另外有第三方表格控件以評估授權(evaluation licence)引入,只供測試與學習——**若 Karst 抽用它的前端代碼,這一格會踩地雷**;抽後端邏輯則不受影響。

對照 D-007:Apache-2.0 本身無阻 SaaS,但第三方控件的評估授權是一個要繞開的暗格。

### 2.5 活躍度(2026-08-25 GitHub API)

| 項目 | 數值 |
|---|---|
| 星 | 14,128 |
| Fork | 2,917 |
| 未結 issue | 10 |
| 建立日 | 2023-03-21 |
| 最後推送 | **2026-04-02(近五個月無更新)** |
| 近一年 commit | **29** |

近一年的 29 次提交內容多數是「更新依賴庫」「更新說明」,還有連續四次「誤刪除,回滾」。唯一一次功能性升級是 2026-01-16「注入 cookie 解決限制高頻率獲取數據」——即繞開東方財富的取數限制。

**判斷:維持可用,不是繼續開發。**與 KARST-001 對 zipline-reloaded 的判斷同一級數。

### 2.6 與 Karst 的契合度——先講最重要那層錯配

**用戶交易美股。這個倉是純 A 股工具,而且是綁死那一種。**

不是「改一改就能跑美股」的關係,三層都綁死了:

1. **數據源**:東方財富(需 Cookie)、騰訊財經——只有滬深 A 股與 ETF,連港股都沒有。
2. **概念**:籌碼分佈、龍虎榜、股吧人氣、漲停跌停、滬港通資金流——這些是 A 股市場結構的產物。美股沒有漲跌停板,沒有龍虎榜,籌碼分佈這個概念在美股的資料環境下算不出來(缺逐日成本分佈的公開數據)。
3. **落單**:靠 OCR 認同花順的驗證碼——美股世界是 Alpaca / IBKR 的 API,兩者無關。

要把它改成美股工具,等於把數據層、指標層以外的東西全部重寫。**改造成本高於自建。**

| 準則 | 判斷 |
|---|---|
| D-002 矩陣式性能 | **✕** 沒有引擎 |
| D-002 蠟燭圖出入場 | **◐** 有網頁蠟燭圖,但沒有回測出入場點可標(因為沒有回測) |
| D-002 單一定義資料層 | **✕** 強制自己的 MySQL schema |
| D-003 非結構化轉因子 | **✕** 完全沒有 |
| D-006 美股 | **✕** 見上 |
| D-006 組合層 | **✕** 沒有組合概念 |
| D-007 授權 | **◐** Apache-2.0 可以,但前端第三方控件是評估授權 |

### 2.7 可借清單

| 處置 | 項目 | 理由 |
|---|---|---|
| **借思路** | 200 多項選股條件的**表達方式與歸類**(股票池 / 基本面 / 技術面 / 情緒面 / 資金流五格) | Karst 要設計選股條件的資料模型時,這是一份現成的、經過真實使用打磨的欄位清單。**借的是分類法,不是代碼** |
| **借思路** | 61 種 K 線形態的輸出約定:負值 = 賣出信號 / 0 = 無形態 / 正值 = 買入信號 | 這是「質化技術面歸一為因子」的一個極簡範例,正好對應 D-003「一切信號歸一為量化因子」。實作可直接用 talib(它自己也是用 talib) |
| **借思路** | 每日批次編排:抓數 → 算指標 → 認形態 → 選股 → 統計,四分鐘跑完一日 | Karst 的紙上交易排程(KARST-001 §十列為必須自建的一格)需要同樣的作業鏈,這是一個可運行的參考骨架 |
| **明寫無可借** | 回測 | 它沒有引擎,只有前向報酬統計 |
| **明寫無可借** | 數據層、自動交易、籌碼分佈 | 全部綁死 A 股市場結構與 A 股券商軟件,對美股零適用 |
| **不抽零件** | 全部代碼 | 綁 A 股數據源與 MySQL schema,抽出來要改的比重寫多 |

---

## 三、OpenByteInc/QuantDinger——KARST-001 標記的重查

這一節是本票的重點:KARST-001 §六對 QuantDinger 下了兩條指控,票上要求證實或推翻。**一條證實,一條推翻。**

### 3.1 指控一:「前端與流動版並非開源」——**證實**

Open Byte Inc 名下四個倉([組織倉列表](https://github.com/orgs/OpenByteInc/repositories)):

| 倉 | 內容 | 授權 | 星 |
|---|---|---|---|
| QuantDinger | Python 後端 | **Apache-2.0** | 11,079 |
| QuantDinger-Vue | 網頁前端 | **Other**(source-available) | 144 |
| QuantDinger-Mobile | 流動版與輕量網頁客戶端 | **Other**(source-available) | 129 |

前端授權是「QuantDinger Frontend Source-Available License v1.0」,非 OSI 認可的開源授權。關鍵條文([QuantDinger-Vue LICENSE](https://github.com/OpenByteInc/QuantDinger-Vue/blob/main/LICENSE)):

> 「Any Commercial Use of the Software by any individual or organization that is not a Qualified Non-Profit Entity requires a separate commercial license」

> 「You may not remove, obscure, alter, or misrepresent such branding, watermark, or attribution without prior written permission」

即:非商業自用免費;**任何商業用途須另行取得 Open Byte Inc 的書面授權;不准移除它的品牌與水印**。

**同時要更正一個細節**:KARST-001 寫「即『Apache-2.0』只覆蓋後端」——這句是對的,但要補一句,後端那份 [LICENSE](https://github.com/OpenByteInc/QuantDinger/blob/main/LICENSE) 經逐字核對是**純正 Apache-2.0 全文,沒有任何附加條款,沒有 Commons Clause**。後端本身是乾淨的。

**對照 D-007**:這一格才是 QuantDinger 對 Karst 的真正殺著。D-007 第 2、4 點要求「SaaS 留門」——而 QuantDinger 的介面那一半明文禁止商業使用。若 Karst 借它的介面,SaaS 那道門當場關上。這比「回測引擎是什麼」重要得多。

### 3.2 指控二:「回測引擎未披露」——**推翻**

**引擎在開源後端裡面,而且披露得相當完整。**位置:

`backend_api_python/app/services/strategy_v2/runtime.py` — **111,314 bytes**

證據逐條:

- **有真實的模擬迴圈**:`StrategyV2BacktestRunner.run()` 內
  ```python
  for timestamp in timestamps:
      self.context.current_dt = pd.Timestamp(timestamp)
      # 執行掛單、處理保護、呼叫處理器
      self.broker.record_equity(self.portal, timestamp)
  ```
- **多標的組合**:`positions: dict[str, Position]`;`_record_rebalance()` 逐根計算 `target_weights` 與 `actual_weights`;`_position_key(symbol, position_side)` 支援多空兩腳。
- **成本模型**:佣金 `notional * self.commission`;滑點 `fill_price = open_price * (1.0 ± slippage)`;限價單按當根高低價判成交。
- **績效指標**:夏普比率、最大回撤、勝率、獲利因子、年化報酬。
- **策略定義**:用戶 Python 代碼,經 `compile_strategy_v2(code)` 編譯,回調為 `before_trading_start` / `handle_data` / `after_trading_end` / `on_rebalance`——即 zipline 那一派的寫法。
- **不包第三方回測庫**:沒有 vectorbt、backtrader、zipline、bt,只用 pandas 與(可選的)talib。

同目錄下配套齊全:`contract.py`(34 KB,策略合約)、`data.py`、`deployment.py`、`factor_research.py`、`protection.py`(風險保護)、`storage.py`、`service.py`。

**KARST-001 為何會判斷失準——已查明。**倉內另有一個名字很像的檔案 `app/services/backtest_execution.py`,只有 **1,027 bytes**,內容是手續費與滑點參數的正規化小工具(唯一的 import 是 `from typing import Any`)。從檔名清單看去,最像引擎的就是它,但它不是。真身在 `strategy_v2/runtime.py`。

### 3.3 三條 KARST-001 未發現的新事實

1. **日線回測最長只能跑三年。**`app/services/backtest_limits.py` 硬編碼上限:`"1H"/"4H"/"1D"/"1W": 1095 days`(三年);`"5m": 180 days`;`"1m"/"3m": 30 days`;而**美股分鐘線只有 7 日**(註明理由為「US stock intraday data provider limit」)。日線那條註明是「engine workload limit」——即引擎自己的負荷限制,不是數據源的。對 Karst 要跑十年日線的場景,這是硬牆。

2. **開源後端內含 SaaS 計費管道。**`billing_service.py` 有 31 KB;`routes/backtest_center.py` 的 `/run` 端點在執行回測前會先扣 credit。自托管者會連這套一併繼承。(能否關掉未查證——見第七節。)

3. **引擎同樣不是向量化。**與 Vibe-Trading 一樣是逐根事件驅動迴圈。D-002 那一格照樣不合格。

### 3.4 定位、活躍度、市場

- **定位一句**:以幣圈為主、股票與外匯為輔的自托管 AI 量化交易平台,後端開源、介面禁商用。
- **技術棧**:Flask + Gunicorn(API)、PostgreSQL(狀態)、Redis(快取與任務隊列)、Celery(非同步作業),另有交易 worker 與排程 worker;前端 Vue(另一個倉)。
- **市場與接駁**:幣圈交易所 Binance / OKX / Bitget / Bybit / Gate / HTX;傳統券商 IBKR 與 Alpaca;AI 供應商 OpenRouter / OpenAI 相容 / Google / DeepSeek / Grok / MiniMax。**股票是配菜,不是主菜。**
- **活躍度(2026-08-25)**:11,079 星 / 2,327 fork / 64 未結 issue / 建於 2025-12-28 / 最後推送 2026-08-24 / **近一年 492 commit**。八個月的項目,開發節奏是真的。
- 附帶 MCP server,可供 Cursor / Claude Code / Codex 呼叫其工具。

### 3.5 與 Karst 的契合度

| 準則 | 判斷 |
|---|---|
| D-002 矩陣式性能 | **✕** 逐根事件驅動 |
| D-002 蠟燭圖出入場 | **◐** 有,但在禁商用的前端倉 |
| D-002 單一定義資料層 | **✕** 綁 PostgreSQL schema + Redis + Celery 一整套 |
| D-003 非結構化轉因子 | **✕** 有 AI 研究工具,但不入因子層 |
| D-006 美股選股 | **◐** 股票經 IBKR / Alpaca 支援,但幣圈才是主場;日線三年上限 |
| D-006 組合層 | **✅** 有真實的多標的權重再平衡 |
| D-007 授權 | **✕** 介面禁商用,直接踩「SaaS 留門」 |

### 3.6 可借清單

| 處置 | 項目 | 理由 |
|---|---|---|
| **借思路** | `strategy_v2/` 的分檔法:`contract.py`(合約)/ `runtime.py`(執行)/ `deployment.py`(上線)/ `protection.py`(風控)/ `storage.py`(存取)分家 | Karst 要把引擎隔離在自家介面後(D-007 第 3 點),這份分層是一個可讀的參考:合約與執行分開,正是「引擎可換件」的落地形態 |
| **借思路** | `before_trading_start` / `handle_data` / `on_rebalance` 的回調契約 | 換倉節奏是策略參數(D-003 第 4 點),`on_rebalance` 是一個把節奏具體化的介面設計 |
| **借思路** | `factor_research.py` 的因子研究流程 | 與 Vibe-Trading 的因子層對照著看 |
| **不抽零件** | 引擎與其他代碼 | 綁 Flask + PostgreSQL + Redis + Celery 整套;綁計費;引擎非向量化;日線三年上限 |
| **不整件借** | 全部 | 介面那一半是禁商用的 source-available,踩 D-007 |

**KARST-001「不應該成為 Karst 的地基」的結論維持不變,但理由要換。**不是因為「引擎未披露」(該條已推翻),而是因為:授權踩 D-007、引擎非向量化踩 D-002、日線三年上限、以及一整套綁死的基建。

---

## 四、atilaahmettaner/tradingview-mcp

### 4.1 定位一句

一個 MCP server:把 TradingView 的篩選器與技術指標、Yahoo 報價、RSS 新聞、Reddit 情緒,包成 37 個工具,讓 Claude / ChatGPT / Cursor 一類 AI 客戶端直接呼叫。

### 4.2 架構與核心零件

倉很細,全倉 147 個檔案(未截斷)。核心在 `src/tradingview_mcp/core/services/`:

| 檔案 | 大小 |
|---|---|
| `screener_service.py` | 47,731 bytes |
| `backtest_service.py` | 33,382 bytes |
| `screener_provider.py` | 28,722 bytes |
| `scanner_service.py` | 16,390 bytes |

依賴([pyproject.toml](https://github.com/atilaahmettaner/tradingview-mcp/blob/main/pyproject.toml)):`tradingview-ta>=3.3.0`、`tradingview-screener==3.0.0`(明文釘死版本以防幣圈/期貨掃描失效)、`feedparser`、`requests`、`httpx`。版本 0.8.1。

工具分類:回測 3 個、報價 2 個、選股篩選 2 個、情緒與新聞 3 個、技術分析 8 個、地區市場 8 個、專用掃描器 11 個。

### 4.3 「回測」的真身

`backtest_service.py` 全文:

- **純 Python,無 numpy**。只 import `json`、`math`、`statistics`、`urllib.request`、`datetime` 加自家 `indicators_calc`。數據經 HTTP 取自 Yahoo Finance。
- **逐根迴圈**:
  ```python
  for i in range(1, len(candles)):
      if rsi[i] is None:
          continue
      price, date = candles[i]["close"], candles[i]["date"]
      if position is None and rsi[i] < oversold:
          position = {"entry_date": date, "entry_price": price...
  ```
- **單標的**:公開 API 只收一個 `symbol`,無組合聚合。
- **九個寫死的策略**:RSI、布林、MACD、EMA 交叉、Supertrend、Donchian、RSI 回調、Keltner 突破、三重 EMA,以 `_STRATEGY_MAP` 對照。
- **不能自定因子或信號**:要加策略必須改代碼。
- **無倉位管理、無組合配置**:每筆交易假設全額投入,沒有動態倉位、凱利、風險配置或多倉權重。
- 有值得一提的一格:walk-forward 驗證會輸出過擬合判語 ROBUST / MODERATE / WEAK / OVERFITTED。

**這正正是 D-006 明文排除的形態**:單股擇時、指標參數優化。用戶原話「the application is not for single stock entry optimatization」——這個倉的回測就是單股入場優化本身。

### 4.4 授權與數據來源風險

- **MIT**,自稱「free forever (MIT)」。對照 D-007 完全無阻。
- **但數據來源有一層風險要講清楚。**它依賴 `tradingview-screener`,那是包住 TradingView `/screener` 端點的第三方庫([shner-elmo/TradingView-Screener](https://github.com/shner-elmo/TradingView-Screener),MIT)。該庫自述「retrieves data directly from TradingView without the need for web scraping or HTML parsing」,但同時承認自己是「a (low-level) wrapper around TradingView's `/screener` API endpoint」——即一個**未公開文檔、非為公眾用途發佈**的端點,並提醒使用者留意「server load and potential bans」。
- 倉方自己把責任推回使用者:「You are responsible for ensuring your own use complies with the terms of any data source you point it at」。
- 明文與 TradingView 無關聯:「not affiliated with, endorsed by, or associated with TradingView Inc.」。

**判斷**:自用階段可接受(封 IP 是唯一後果)。但若 Karst 日後商品化,把一個未公開端點放進收費產品的數據路徑,是法律與可用性雙重風險。**這一格與授權無關,是條款風險,要另計。**

### 4.5 活躍度與治理

| 項目 | 數值 |
|---|---|
| 星 | 4,223 |
| Fork | 907 |
| 未結 issue | 11 |
| 建立日 | 2025-08-08 |
| 最後推送 | 2026-08-24 |
| 近一年 commit | **122** |

**巴士因子 = 1**:atilaahmettaner 96 次提交,第二名 elsahafy 只有 8 次,其後全部是個位數。

**利益關係要講明**:作者同時經營收費托管版(pro.cryptosieve.com,月費 9 / 29 美元,附 3 日試用),開源版是引流入口。這不是問題,但意味著開源版的功能邊界由商業考量決定。

### 4.6 與 Karst 的契合度

| 準則 | 判斷 |
|---|---|
| D-002 矩陣式性能 | **✕** 純 Python 迴圈,連 numpy 都沒有 |
| D-002 蠟燭圖出入場 | **◐** 托管版可在對話內畫互動蠟燭圖(MCP Apps),但那是聊天內的圖,不是 Karst 要的應用介面 |
| D-002 單一定義資料層 | **✅** 無狀態,不強加任何儲存 |
| D-003 非結構化轉因子 | **◐** 有新聞與 Reddit 情緒工具,但輸出是給 LLM 讀的文字,不是因子 |
| D-006 美股選股 | **◐** 支援 NASDAQ / NYSE 篩選,但篩選器是即時快照,不是歷史時序,做不到回測 |
| D-006 不做日內 | **✕** 主打 1d / 1h,方向是短線指標 |
| D-007 授權 | **✅** MIT(但數據來源條款風險另計) |

### 4.7 可借清單

| 處置 | 項目 | 理由 |
|---|---|---|
| **抽零件** | `screener_provider.py` / `screener_service.py` 的美股篩選取數路徑,連同它的重試 + 60 秒 TTL 快取 | Karst 的選股宇宙(universe)需要一個「今日哪些美股符合條件」的來源。這是一條現成、MIT、不需 TradingView 帳號的路。**但要自己承擔上述條款風險,並且只宜當候選之一,不宜當唯一來源** |
| **借思路** | walk-forward 加過擬合判語(ROBUST / MODERATE / WEAK / OVERFITTED) | Karst 的策略體檢報告可以加一個同樣的欄位。D-003 第 4 點明寫揀節奏要「防過擬合」——這是一個把防過擬合變成可見輸出的簡單做法 |
| **借思路** | 把量化能力包成 MCP 工具給 AI 客戶端呼叫 | Karst 日後若要讓 agent 讀自己的回測結果,MCP 是現成的介面形態。**注意這與 D-002「不要 chat 加文件」不衝突**:MCP 是附加介面,不是主形態 |
| **明寫無可借** | 回測引擎 | 單標的、寫死九個指標策略、無自定因子、無倉位管理、純 Python 迴圈。D-002 與 D-006 兩頭都不合 |

---

## 五、與 KARST-001 建議的關係:維持、補充、修訂

KARST-001 的建議是:**混合路線 = vectorbt 或 PyBroker 作向量化核心 + 自建語意層 + lightweight-charts 自建蠟燭圖介面。**

### 5.1 維持(三項)

1. **「引擎借用」的核心結論站得住,而且被這四個倉加強了。**四個倉沒有一個提供向量化引擎:Vibe-Trading 與 QuantDinger 都是逐根事件驅動迴圈,tradingview-mcp 是連 numpy 都沒有的純 Python 迴圈,myhhub 根本沒有引擎。D-002 用戶原話「matrix based … can simulate lot of trade in a sec」這一格,**vectorbt 與 PyBroker 仍然是唯二答案**。

2. **「沒有任何一個現成方案可以整套搬過來」維持。**四個倉沒有一個推翻這句。最接近的 Vibe-Trading 敗在引擎性能與 agent 層形態;QuantDinger 敗在授權與三年上限;另外兩個不在同一個問題域。

3. **D-007 引擎隔離原則維持,而且 QuantDinger 是現成的反面教材。**它把後端開源、介面鎖在禁商用授權後面——恰恰示範了「若不把可換件與正本分清楚,將來想商品化時被卡住的是哪一格」。KARST-008 規格匯整票寫這一段時,可以直接引這個例子。

### 5.2 補充(三項,建議寫入規格)

1. **Vibe-Trading 是 KARST-001 漏掉的一個真候選,亦是四個倉中唯一值得抽零件的。**MIT、近一年 1,762 次提交、自研多市場組合引擎、五個組合優化器、alpha101 / gtja191 / qlib158 / academic / fundamental 五套因子庫。**最有價值的一件是它的因子契約**:`dict[str, pd.DataFrame] → pd.DataFrame`(日期 × 標的),配三條註冊表紀律(禁前視 lag ≥ 1、禁 ±inf、NaN 必須傳遞)。**建議 KARST-003 因子合約票直接把它當藍本讀過一次再落定義。**

2. **圖表件多一個有真實案例的替代。**Vibe-Trading 的 React 19 前端用 **ECharts 6.1**,不是 lightweight-charts。KARST-001「直接用 lightweight-charts 的 JavaScript 原生 API 自建前端」的結論**不需要改**(lightweight-charts 仍是 TradingView 官方維護、專為金融圖表而生),但規格裡應該記一筆:ECharts 是有實際落地案例的替代,若 Karst 的介面同時需要大量非金融圖表(因子分佈、歸因瀑布、相關矩陣),ECharts 一套通吃可能省事。這一格由 KARST-007 拍板介面形態時一併考慮。

3. **D-003 的差異化再獲一次證實。**四個倉沒有一個做「非結構化材料 → 因子」。Vibe-Trading 最接近(有新聞、研報、13F、本地文本情緒評分等工具),但那些全部住在 agent 工具層,**與因子層沒有接通**——它的因子契約明文只吃價量與基本面寬表。**結論:這一格 Karst 必須自建,而且它是 Karst 最不可被現成框架取代的部分。**KARST-004 非結構化轉因子票的價值因此更清晰。

### 5.3 需修訂(一項)

**KARST-001 §六對 QuantDinger 列的四個警號,第 (3) 條須撤回。**

原文:「README 沒有任何關於組合層回測抑或單標的回測的說明,**回測引擎是什麼亦未披露**」。

**經查不成立。**引擎在開源後端內,`backend_api_python/app/services/strategy_v2/runtime.py`,111,314 bytes,含完整的逐根模擬迴圈、多標的持倉、權重再平衡、佣金滑點、資金曲線與績效指標,策略以 zipline 式回調定義,不包任何第三方回測庫。而且組合層回測**是**做得到的(`_record_rebalance()` 逐根算目標與實際權重)。KARST-001 誤判的成因已查明:同倉另有一個 1,027 bytes 的 `backtest_execution.py`,只是手續費正規化小工具,從檔名清單看去最像引擎。

**其餘三個警號維持**(倉太新、前端非開源、幣圈為主),並補上兩條 KARST-001 未見的:

- 日線回測硬上限 1,095 日(三年),美股分鐘線 7 日(`backtest_limits.py`);
- 開源後端內含 SaaS 計費管道(`billing_service.py` 31 KB;回測路由執行前扣 credit)。

**QuantDinger 的最終判斷不變——仍然不建議當 Karst 的地基。**只是理由要換成準確的那幾條:授權踩 D-007、引擎非向量化踩 D-002、三年上限、基建綁死。**指控要準,結論才站得住。**

### 5.4 不需修訂的

KARST-001 §十的借用/自建分工表、§八的配件清單(Riskfolio-Lib、quantstats、alphalens-reloaded)、§十二待驗證前提(vectorbt 分組共用現金能否流暢表達每月排名選股)、§十三的商業問題,**四個倉全部沒有觸及,原樣有效**。

---

## 六、最終裁決由用戶(D-005)

本報告只提供建議。四個指定倉**沒有一個改變「借用 / 自建 / 混合」的路線分岔**,亦沒有一個推翻 KARST-001 §十三那條先決問題:

> **Karst 將來有沒有可能變成賣出去的產品或收費服務?**

要用戶拍板的仍然是這一條。本票額外送上兩個小決定,同樣由用戶裁決:

1. **要不要把 Vibe-Trading 的因子契約與因子庫抽進 Karst?**(MIT,無授權障礙;代價是要讀一份約 13 KB 的協定定義加五個因子目錄,並自行判斷其品質。)
2. **選股宇宙要不要接 tradingview-screener 那條路?**(MIT,免帳號;代價是未公開端點的條款與封鎖風險。)

---

## 七、未解與風險

| 項目 | 說明 |
|---|---|
| **Vibe-Trading 引擎速度未實測** | 它是逐根 Python 迴圈,理論上遠慢於 vectorbt 的向量化。但「慢多少」沒有實測。若在數百股 × 十年日線的規模上其實夠快,則「引擎必須借向量化框架」的前提會鬆動,KARST-009 試跑對決票應考慮加它做第三條對照臂 |
| **Vibe-Trading 的品質未經獨立驗證** | 代碼形態紮實(型別、docstring、tests 齊),但 star 數來自 HKUDS 的發行力而非生產驗證;issue/PR 的零留言同日開關形態指向 agent 驅動開發。抽零件前建議先讀一遍它的因子測試 |
| **QuantDinger 的 credit 扣減能否在自托管下關閉** | 未查證。若不能關,自托管的可用性要打折。但因為已判定不當地基,此項不影響結論 |
| **tradingview-screener 的端點穩定性與條款** | 未公開端點,TradingView 隨時可改可封。倉方明文把合規責任推回使用者 |
| **myhhub 的第三方表格控件評估授權** | 若日後有人想抽它的前端代碼,這一格是地雷。已在本報告點明,無需再查 |

---

## 出處一覽

**GitHub 倉庫(數據經 GitHub API 於 2026-08-25 讀取)**
- HKUDS/Vibe-Trading — <https://github.com/HKUDS/Vibe-Trading>
- HKUDS 組織倉列表 — <https://github.com/orgs/HKUDS/repositories>
- myhhub/stock — <https://github.com/myhhub/stock>
- OpenByteInc/QuantDinger — <https://github.com/OpenByteInc/QuantDinger>
- OpenByteInc/QuantDinger-Vue — <https://github.com/OpenByteInc/QuantDinger-Vue>
- OpenByteInc/QuantDinger-Mobile — <https://github.com/OpenByteInc/QuantDinger-Mobile>
- atilaahmettaner/tradingview-mcp — <https://github.com/atilaahmettaner/tradingview-mcp>
- shner-elmo/TradingView-Screener — <https://github.com/shner-elmo/TradingView-Screener>

**授權檔**
- Vibe-Trading LICENSE(MIT)— <https://github.com/HKUDS/Vibe-Trading/blob/main/LICENSE>
- QuantDinger LICENSE(純 Apache-2.0,無附加條款)— <https://github.com/OpenByteInc/QuantDinger/blob/main/LICENSE>
- QuantDinger Frontend Source-Available License v1.0 — <https://github.com/OpenByteInc/QuantDinger-Vue/blob/main/LICENSE>

**核對過的關鍵代碼檔**
- Vibe-Trading 引擎本體 — `agent/backtest/engines/base.py`
- Vibe-Trading 回測入口與設定 — `agent/backtest/runner.py`
- Vibe-Trading 因子契約 — `agent/src/factors/base.py`
- Vibe-Trading 因子庫 — `agent/src/factors/zoo/{alpha101,gtja191,qlib158,academic,fundamental}`
- Vibe-Trading 前端依賴 — `frontend/package.json`
- QuantDinger 引擎本體 — `backend_api_python/app/services/strategy_v2/runtime.py`(111,314 bytes)
- QuantDinger 回測路由 — `backend_api_python/app/routes/backtest_center.py`
- QuantDinger 手續費正規化(KARST-001 誤認為引擎者)— `backend_api_python/app/services/backtest_execution.py`(1,027 bytes)
- QuantDinger 回測範圍上限 — `backend_api_python/app/services/backtest_limits.py`
- myhhub「回測」實質 — `instock/core/backtest/rate_stats.py`、`instock/job/backtest_data_daily_job.py`
- tradingview-mcp 回測 — `src/tradingview_mcp/core/services/backtest_service.py`
- tradingview-mcp 依賴 — `pyproject.toml`

**其他**
- QuantDinger 官方文件 — <https://www.quantdinger.com/docs.html>
- Vibe-Trading 官方 wiki — <https://vibetrading.wiki/>
- tradingview-mcp 收費托管版 — <https://pro.cryptosieve.com>
