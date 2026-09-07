# Karst 後端架構摩擦點審視(2026-08-30)

> 唯讀分析,未改動任何程式碼。目的:找出淺模組與可加深的機會,供用戶揀方向。
> 只描述問題、方向、好處,不提新介面設計。
> 詞彙照 `CONTEXT.md`;架構詞用模組/介面/實作/深度/接縫/適配器/槓桿/局部性。
> HTML 版:`%TEMP%\claude\C--projects-Karst\d2e5d32d-.../scratchpad/architecture-review-2026-08-30.html`

範圍:`karst/` 後端 30,287 行、71 個檔(跳過 `karst/web/static/` 與 `prototype/`)。
熱點檔(2026-08-26 起改動次數):`store.py` 11、`schema.py` 10、`gateway/service.py` 10、
`web/data.py` 9、`web/api_strategy.py` 9、`gateway/cli.py` 9、`data/__init__.py` 9。

---

## 量度:每學一分介面能驅動多少行實作

深度 = 實作行數 ÷ 對外名數(粗略指標)。

| 模組 | 介面(對外名數) | 實作(行) | 深度 | |
|---|---:|---:|---:|---|
| `karst/schema.py` | 1(`connect`) | 1,113 | 1,113 | 深 |
| `karst/web/data.py` · `RunReader` | 8 | 815 | 102 | 深 |
| `karst/factors` | 9 | 814 | 90 | 深 |
| `karst/sweep` | 52 | 3,692 | 71 | 介面過闊 |
| `karst/data` | 98 | 4,742 | 48 | 介面過闊 |
| `karst/engine` | 71 | 2,889 | 41 | 介面過闊 |
| `DefinitionStore` | 59 個公開方法 | 2,082 | 35 | 介面過闊 |

`karst/strategies` 刻意不列:行數大半是三條策略互抄,靠重覆撐起的厚度不是深度。

---

## 候選一:把策略收在一個策略合約之後 —— 強烈建議

**涉及檔案**
`karst/strategies/trend_swing.py`(981)、`factor_mix.py`(706)、`factor_rotation.py`(1,516)、
`karst/sweep/factor_mix.py`(359)、`karst/sweep/factor_rotation.py`(696)

**問題**
策略層根本沒有介面——沒有策略協定、沒有基類、沒有註冊表。結果每條策略把同一段編舞逐字重抄:

- 登記編舞 80 行 × 2 份(`trend_swing.py:470-552` ‖ `factor_mix.py:376-460`),連註釋一字不差。
- 落痕 `record_*_run` 三份,同一個 11 參數簽名(`trend_swing.py:552`、`factor_mix.py:671`、`factor_rotation.py:1482`)。
- 跑一次回測有四段逐字相同(面板守門連錯誤字串、參數組裝連註釋、遲到 import、結果打包)。
- 掃描底下每條策略再一個專屬適配檔,兩者 90–110 行近乎逐字重覆。
- 純量參數驗證五套並存;笛卡兒積三處各自砌。

新增第四、五條策略(D-015 Minervini、D-018 錯殺)= 再抄六格。

**方向**
策略只交自己獨有那一件(訊號 / 敞口 / 驅動器),登記、跑、落痕、掃描由一個合約驅動。

**好處**
槓桿:一個介面驅動五條策略;局部性:登記缺陷只在一處;新策略由六格抄寫收成一件;
測試只經合約打,不必三份 fixture;掃描適配檔連帶消失。

**刪除測試**
把三份 `record_*_run` 刪走,複雜度不消失——它在三個呼叫者身上重現,即是它在賺錢,值得收成介面。

**與裁決**:無衝突。D-013 分層與 D-016 試練場定位都假設策略可一條條加上去,合約正是缺的那件。

---

## 候選二:把治理收到唯一入口門內 —— 強烈建議

**涉及檔案**
`karst/gateway/cli.py`(981)、`service.py`(791)、`ledger.py`(275)、`karst/store.py`、
`karst/data/pipeline.py:426`、`karst/data/macro.py:1597`、`karst/batches.py:51`

**問題**
寫入者簽章住在唯一入口(`gateway/ledger.py`),定義庫完全不知它存在。所以繞過入口直呼定義庫
就是無簽章寫入,而三處凍結快照的碼正是這樣做。治理清單 `GOVERNED_TABLES` 現時 12 張表,
**收了 `data_snapshot_retraction`(除名)但沒有 `data_snapshot`(登記)**——除名要簽章、凍結不用,
兩者其實同一種定義級動作。另有 `gateway/service.py:394` 繞過定義庫直查 `gateway_write` 表。

同時門面比門後厚:`cli.py` 981 行中約 640 行是命令處理,內含代號→CIK 解析(`:677-689`)、
因子預測力四步管線(`:410-465`)等業務;`service.py` 大量方法只是定義庫呼叫加簽章的薄轉發,
而 `_sign_once` 要呼叫者自補(同檔出現 5 次)。

**方向**
簽章由呼叫者自補改為門內自動蓋;治理清單補上數據快照;命令列退回只解析參數。

**好處**
局部性:治理只在一個模組;繞不過去,不靠自律;`karst verify` 覆蓋得到快照;
命令列由 981 行收薄;測試打一道門即測到治理。

**刪除測試**
`_sign_once` 在同一個檔出現五次——它不是過手,是每個呼叫者都要記住的不變量,正該收進門內。

**與裁決**:D-020 寫明「任何人或 agent 都不可繞過直接寫庫」。這是執行上的缺口,不是重開裁決。

---

## 候選三:快照凍結收成一份正本 —— 強烈建議

**涉及檔案**
`karst/data/macro.py`(1,736)、`snapshots.py`(410)、`manifest.py`(235)、`pipeline.py`(467)

**問題**
凍結一份數據快照這件事在三個檔各出現一次半。宏觀線把價格線整套抄了一份:

| 價格版 | 宏觀版 |
|---|---|
| `canonical_prices`(snapshots.py:48) | `canonical_macro`(macro.py:773) |
| `snapshot_digest`(:73) | `macro_digest`(:842) |
| `snapshot_core`(manifest.py:201) | `macro_core`(:817) |
| `write_snapshot_dir`(:98) | `write_macro_dir`(:1278) |
| `find_equivalent_snapshot`(:173) | 同名同構(:1325) |
| `read_*` × 5(:262-325) | `read_macro_*` × 5(:1646-1716) |

程式自己的註釋已寫明「與價格快照同一個做法」「與 `snapshots.canonical_prices` 同一個用途」。
另外來源適配器有兩條互不相干的協定:`sources.py:31` 的 `PriceSource`、`macro.py:377` 的 `MacroSource`;
SEC EDGAR 抓取(`ticker_history.py:805-846`、`cik.py:49-69`)兩處各自用 urllib,不在任何協定之後。

**方向**
凍結是一個模組,收「一批序列」出「一個快照編號」;價格與宏觀只是它的兩個適配器。

**好處**
等價重用的規矩只有一份;局部性:雜湊口徑不會兩邊飄;`macro.py` 由 1,736 行大幅收薄;
第三類數據(財報)直接插得上;測試只覆蓋一套凍結行為。

**接縫是真的**:宏觀線已經行使過它——VIX 由 yfinance 換去 Cboe 官方檔而不動凍結邏輯(KARST-058)。
兩個適配器 = 真接縫,不是假想接縫。

**與裁決**:D-041 已裁基本面主幹改用 SEC EDGAR。那條線遲早要凍第三種快照;現在不收就會抄第三份。

---

## 候選四:一次掃描收成一個介面 —— 強烈建議

**涉及檔案**
`karst/sweep/__init__.py`(52 個對外名)、`runner.py`(485)、`grid.py`(702)、`report.py`(697)、
`verdict.py`(591)、`karst/web/api_jobs.py:836-880`、`karst/web/api_sweep.py`(959)

**問題**
跑一次掃描要呼叫者自己記住十步次序(讀價格面板 → 開唯一入口 → 備風控設定 → 開運行庫 → 砌格 →
造 Job → `run_sweep` → `judge` → 畫投影 → 寫報告)與三個無預設判讀門檻。這段編舞在實驗腳本
與網頁重掃路徑(`api_jobs.py:836-880`)各抄一次。掃描格構造甚至住在 `api_jobs.py`,不在 `karst/sweep/`。
同一份掃描結果整形兩次:`sweep/report.py` 寫 CSV,`web/api_sweep.py` 再由 CSV 反推一次,
欄名常數手抄,`_choice_axes_from_layer` 甚至把層標籤字串反解回選擇軸名。

**方向**
一個介面收「一個批次」:入面砌格、跑、判讀、落檔,出來是批次編號與判讀。

**好處**
槓桿:十步收成一步;掃描格構造搬回掃描模組;局部性:判讀門檻只設一次;
網頁重掃與腳本走同一條路;測試打一個介面即覆蓋全程。

**好的對照**:`sweep/verdict.py` 的 `judge` 是純函數,不開庫不跑引擎——全套件最乾淨那層,不用動。

**與裁決**:D-042 已把策略詳情改為批次層畫面,「批次」正式成為第一等概念,
但程式裡現時沒有一個叫批次的模組。這是補上的最好時機。

---

## 候選五:因子取值只留一條路 —— 強烈建議

**涉及檔案**
`karst/store.py`(`factor_value` 表:`write_factor_values:835`、`read_factor_values:916`、
`latest_known_values:950`、`value_for:987`)、`karst/factorstore.py`(449)、
`karst/engine/factorvalues.py`(249)、`karst/engine/selection.py:51`、`karst/gateway/cli.py:419`

**問題**
「取一個因子的最新已知值」有三份實作:定義庫的 sqlite 路徑、因子值批次的 Parquet 路徑,
加 `FactorValueSource` 把兩者合流的第三份——其 `:94` 註明簽名與 `DefinitionStore.latest_known_values`
「一字不差」。生產取值三種寫法並存(合流讀 / 只讀批次 / 直讀表),而 `store.value_for`
在 `karst/` 內只剩一個呼叫,其餘全在測試。`factorstore.py` 449 行只有一處測試提及。

**方向**
取值只有一個介面;sqlite 那條路退役,只留讀舊庫用。

**好處**
局部性:前視缺陷只可能在一處;兩份取值口徑不會再分岔;定義庫少一大群方法;
`factorstore.py` 補得回測試。

**與裁決**:D-032 已裁因子值改存 Parquet、定義庫只留登記。sqlite 那條取值路是裁決之前的遺留,
收掉它是執行裁決,不是重開。

---

## 候選六:網頁取數層停止自己算數 —— 值得探索

**涉及檔案**
`karst/web/api_strategy.py`(981)、`api_overview.py`(376)、`api_sweep.py`(959)、
`api_jobs.py`(1,080)、`data.py`(815)

**問題**
網頁取數層本應只讀不算(詞彙表「薄 REST 層」:只讀不寫、不自己算數),實情是:

- `api_strategy.py:366 _row_metrics` 為速度在網頁層另寫一套指標口徑(docstring 自認)。
- `api_sweep.py:727 _projection` 手寫二維聚合。
- `api_strategy.py:645 picks` 近 200 行:交易日回退、漏斗各層集合運算、因子敞口配對。
- `api_jobs.py` 1,080 行中只有約 200 行是工作佇列,其餘 880 行是業務(重跑版本比對、重掃砌格)。
- 整形小工具 `_f`/`_pct`/`_day` 三份逐字抄本;`_bench_annual_returns`、`_run_perf` 各兩份;
  指標 dict 三處各打包一次;`runId` 在五個檔各自打包。
- `api_sweep.py:240` 直接 `pd.read_csv` 掃實驗目錄——全站唯一真正繞過定義庫的地方,而且 959 行零測試。

`web/data.py` 本身反而是深模組(815 行 / 8 個公開方法),只是被繞過。

**方向**
把算與整形收進已經夠深的運行檢視模組,`api_*.py` 只剩序列化。

**好處**
一個指標一個口徑;局部性:數字對不上只查一處;測試不必起真庫才打得中;
掃描結果由庫讀,不由檔案反推。

**與裁決**:D-042 已裁策略詳情要重做(批次層、密度熱帶)。這批碼本來就要動,順手收深成本最低。

---

## 候選七:定義庫的介面幾乎與實作一樣闊 —— 值得探索

**涉及檔案**
`karst/store.py`(`DefinitionStore`,`:430-2511`,2,082 行 / 59 個公開方法)、`karst/runs/registry.py`(895)

**問題**
一個 2,082 行的類別攤出 59 個公開方法(另 25 個私有),內部十三群幾乎不互相呼叫,只共用一條連線:
實體與代號 192 行、因子定義與版本鏈 183、因子值 sqlite 178、因子值批次登記 126、快照登記 75、
策略定義 195、參數集 155、唯一落點查詢 58、**回測運行留痕 407(最大)**、現役設定 162、
風控規則 122、快照抓取登記 193。
沒有交易介面,18 處 `with self._conn` 各自為政,呼叫者不能把幾個寫入包成一個交易。
`close_ticker`、`has_active_setup`、`get_risk_rule` 全倉零呼叫;另有 7 個方法只有測試在用。
`RunStore` 的 `get_run`/`list_runs`/`stale_reasons`/`is_stale` 是純轉發,無新增行為。
測試繞介面:約 10 個測試檔用 `store._conn.execute` 或 `store.connection` 直接寫讀 SQL。

**方向**
按它自己已有的註釋分段切開,每群一個窄介面;死方法刪走。

**好處**
呼叫者只學自己那一群;局部性:改一群不驚動全庫;純轉發方法可以消失;測試不必再直插私有連線。

**留意**
切割本身不等於加深。值得做的是「回測運行留痕」那 407 行——最大一群、最少與其他群往來,
而且外面四個純轉發方法正等著被吸收。

**好的對照**:`schema.py` 1,113 行藏在一個 `connect()` 之後,是全倉最深的模組,不用動。

**與裁決**:D-027 護欄二「任何模組不得直接開 sqlite 連線,一律經定義庫」。切開後護欄照守,
只是門由一道變幾道窄門。

---

## 候選八:共用風控層交定義,也交算術 —— 推測

**涉及檔案**
`karst/risk/layer.py`(290)、`karst/engine/rules.py`(763)、`karst/engine/vectorbt_engine.py:213,324`

**問題**
共用風控層現時只交定義(名稱、參數名、值域:`risk/layer.py:97-131`)。值域檢查在
`engine/rules.py` 另有一套(`_fraction`/`_positive`,與 `RiskRule.check:81-95` 是兩套)。
真正的算術散在引擎適配層:賠率閘 `rules.py:493-506`、熔斷 `vectorbt_engine.py:308`、
**注碼在 `:213`(訂單函式臂)與 `:324`(訊號臂)兩份實作**。

**方向**
風控層連算術一併交出;引擎只問「今日可否入場、注碼幾多」。

**好處**
單一正本名副其實;注碼算術不會兩邊分岔;風控可獨立測不必起引擎;值域檢查由兩套收成一套。

**為何標推測**
兩條引擎路徑要看見的東西不同(訊號矩陣看不見現金與權益,規格 6.2 明文),
收在一起會不會反而多一層轉譯,未查證。

**與裁決**:D-013 明文「共用風控層定義單一正本」。定義確實單一,算術不是。
建議先量一量兩份注碼實作有沒有真的分岔過,再決定要不要動。

---

## 順帶記下的觀察(不成候選)

- **引擎適配層是真接縫**:全倉只有 `karst/engine/vectorbt_engine.py:23` 一個 `import vectorbt`,
  `strategies/`、`metrics/`、`risk/`、`sweep/`、`web/` 一處都無,還有 `tests/test_engine_rules.py:307-314`
  正則掃全倉把關。D-007 第 3 條守住了。
  唯一的形狀滲漏:`factor_mix.py:640-646` 註釋自認「適配層欠一個與排名無關的組合參數型別」,
  兩條策略被迫用 `top_n=len(exposures), direction="high"` 填空格。
  但 `karst/engine/__init__.py` 的 `__all__` 有 71 個名(32 常數、26 型別、13 函式),
  而真正的接縫協定只有 `PortfolioEngine` 與 `RuleEngine` 兩個——介面闊過需要。
- **測試形狀**:43 個檔、15,473 行、約 350 個測試函式,**沒有 `conftest.py`**;
  126 個 fixture 散在各檔、跨檔零共用;只有 6 個檔(約 43 個測試、13%)經 HTTP 打,
  而且那批打本機真庫,庫或運行不在就 skip——CI 上基本全跳。
  另有一批測試靠 `ast.parse` 斷言原始碼文本(`test_trend_swing.py:655`、`test_factor_mix.py:676`),
  兩檔幾乎逐字重覆。
- **零測試覆蓋的模組**:`karst/data/normalise.py`(141)、`karst/metrics/inventory.py`(136)、
  `karst/web/api_sweep.py`(959)、`karst/web/__main__.py`、`karst/gateway/__main__.py`。
  `api_sweep.py` 是最大一個缺口。
- **全倉最深的三個模組**(不用動,可作對照):`schema.py`(1,113 行藏在 `connect()` 之後)、
  `factors/alpha158.py`(781 行只有 2 個公開函式)、`web/data.py`(815 行 / 8 個公開方法)。

---

## 首選

**先做候選一(策略合約)。**

v1 規劃五套策略,現時寫了三套,每套都把同一段登記與落痕編舞抄一次,加掃描底下再一個適配檔。
第四、五套(Minervini、錯殺)未動手——現在收一個合約,那兩套由「抄六格」變成「交一件」,
而且候選四的掃描適配檔會跟住消失。這是全份報告裡槓桿最高、而且愈遲做愈貴的一個。

**另外建議順手單獨修候選二那一格缺口:治理清單補上數據快照。**
它很細、與其他候選無關,但它令「凍一份快照」現時繞得過寫入者簽章——
那是 D-020 想守住的東西上的一個真實破口,不修的話 `karst verify` 報的清白是打了折的。

**次序建議**
候選一 → 候選二(缺口) → 候選四(趁 D-042 重做批次層) → 候選三 → 候選五 → 候選六 → 候選七 → 候選八。
