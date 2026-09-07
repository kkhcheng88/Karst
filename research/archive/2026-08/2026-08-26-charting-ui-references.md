# UI 外殼與圖表庫參考調研

- 票號:KARST-014
- 日期:2026-08-26
- 交付品:KARST-D01「Karst v1 規格」
- 依據:D-002(應用程式+蠟燭圖出入場,核心引擎矩陣式性能)、D-005(先查現成框架、用戶裁決)、D-007(自用先行、SaaS 留門、引擎可換件)、D-010(虛擬籃子第一等公民,要畫自己的合成蠟燭圖/淨值曲線)、D-011(v1 回測核心用 vectorbt,Python)
- 前作:[KARST-010 指定倉調研](2026-08-25-named-repos.md)(QuantDinger 前端授權已在該篇核實)

---

## 零、一頁總結

| 候選 | 一句定位 | 授權 | 蠟燭圖+標記+疊加+多面板 | 接駁 Python 後端形態 | 虛擬籃子自繪蠟燭圖 | 可借判斷 |
|---|---|---|---|---|---|---|
| [TradingView lightweight-charts](https://github.com/tradingview/lightweight-charts) | TradingView 官方維護的輕量開源前端圖表庫,專為金融圖表而生 | Apache-2.0(須保留品牌標示) | 齊全:原生 Candlestick 系列、`createSeriesMarkers` 進出場標記、多 pane、多系列疊加 | 純前端 JS 庫,不綁定任何後端;後端(Python/vectorbt)只需吐 JSON 陣列(`{time, open, high, low, close}`)經 REST/WebSocket 餵給前端 `setData()` | **可行**:餵什麼陣列畫什麼,合成 OHLC 與交易所報價對它而言沒有分別 | **整件借(前端圖表層)** |
| [TradingView Charting Library / Advanced Charts](https://www.tradingview.com/advanced-charts/)(閉源) | TradingView 官方的完整版圖表庫(帶技術指標庫、畫線工具、多圖表版面),原始碼經審批後才交付 | 「Advanced Charts Free License」——**明文禁止私人/內部用途**,只批「公開網頁專案/應用」;須經申請批准取得 GitHub 私倉邀請,須保留 TradingView 品牌 | 功能最完整(逾百技術指標、畫線工具、多圖表版面),但條款不容許自用場景 | 經 UDF(Universal Data Feed)協定或自訂 Datafeed 介面接任何後端 | 技術上可行(自訂 Datafeed 一樣可餵合成序列),但授權先過不了 | **不可借**:D-007「自用先行」與這份授權的「非私人用途」條款直接衝突,連試用資格都沒有 |
| [Apache ECharts](https://github.com/apache/echarts) | 通用型資料視覺化庫,金融圖表是其中一類,Vibe-Trading(KARST-010 已查)前端正正用它 | Apache-2.0,無附加條款 | 有 Candlestick 系列、`markPoint`/`markLine`(單根蠟燭一個 marker,多重標記要疊加額外 series 變通)、`grid` 可疊多組座標系做多面板 | 純前端 JS;Python 側可用 `pyecharts` 產生同一份 option JSON,或後端直接吐 JSON 由前端組裝 | **可行**,道理與 lightweight-charts 相同 | **整件借(若介面同時要因子分佈/歸因瀑布/相關矩陣等非金融圖表,一套通吃較省事)** |
| [Plotly.py](https://github.com/plotly/plotly.py) / [Dash](https://github.com/plotly/dash) | Python 原生繪圖庫(`plotly.py`,MIT)+ 用它建 Web 應用的框架(`Dash`,MIT);OpenBB 的圖表層正建基於此 | 兩者皆 **MIT**;付費的是配套雲端服務 **Dash Enterprise**(月費由數千至逾萬美元起,只是託管/部署/認證服務,不影響開源核心的授權) | Candlestick trace、`add_annotation`/`add_shape` 做進出場標記、`make_subplots` 做多面板;互動性弱於前兩者(非為高頻更新設計) | Python 原生:不用另起前後端分家,一個 Python 進程直接產生圖表物件並用 Dash 起 Web 應用 | **可行**,`go.Candlestick` 吃的是任意陣列,合成序列一樣畫 | **整件借(若想要 Python 一條龍、不想自己管前後端資料協定,此為最快落地路徑;代價是互動流暢度不如原生 JS 庫)** |
| [OpenBB](https://github.com/OpenBB-finance/OpenBB) | 開源金融資料與分析平台,原「OpenBB Terminal」;圖表層是獨立擴充套件 `openbb-charting`,底層用 Plotly + PyWry | **AGPLv3**(2026 年由 MIT 轉為 AGPL,另設商業授權選項) | 有(建基於 Plotly,能力同上一列);但它是一整套資料平台外殼,不是單純圖表元件 | REST API 或 Python Client,圖表以 figure 物件經 PyWry 顯示於獨立視窗 | 技術上可行(接自訂資料源即可),但要先接受它整套資料平台的架構 | **只借思路(擴充套件分層、資料供應商抽象層設計)**;AGPL 對照 D-007——若抽用其程式碼併入自家倉並對外提供服務,須揭露對應原始碼或另購商業授權,比起自用階段隨手引用要多一層合規功夫,不建議整件借 |
| [OpenByteInc/QuantDinger 前端](https://github.com/OpenByteInc/QuantDinger-Vue)(KARST-010 已核實) | 幣圈為主的自托管交易平台之 Vue 前端 | Source-available,**非商業實體免費、商業用途須另購授權**,禁改品牌水印 | 有蠟燭圖與策略回測視覺化 | 對接自家 Flask 後端 API | 未查(授權已判定不可整件借,無需再查功能細節) | **不可借**(重申 KARST-010 結論):介面禁商用,直接踩 D-007「SaaS 留門」 |
| [vnpy](https://github.com/vnpy/vnpy) | 內地最活躍的開源量化交易框架,自帶 PySide6 桌面 UI 與高效能圖表元件(`vnpy_evo.chart`/`ChartWidget`) | **MIT**,`Copyright (c) 2015-present, Xiaoyou Chen`,無附加條款 | 有:K 線圖表元件原生支援串流更新(逐 tick/逐根即時畫),配合事件驅動架構;疊加指標與多面板由其圖表元件的 item 系統支援 | Python 原生,事件驅動引擎(`EventEngine`)把行情/成交事件推給圖表元件,元件吃的是自家 `BarData` 物件,不限資料來源 | **可行**:`BarData` 只是一組 OHLCV 欄位,合成籃子的每日淨值一樣可以包成 `BarData` 序列餵進去 | **借思路+可能抽零件**:桌面 Qt 圖表元件是 Python 原生、事件驅動、MIT 授權的少數先例,若 Karst 考慮桌面殼(而非純 Web),`ChartWidget` 值得抽出來讀一次;若走 Web 殼則思路(事件驅動餵圖表)仍可借 |

---

## 一、TradingView lightweight-charts

### 1.1 定位一句
TradingView 官方維護、開源、專為金融時序圖表而生的輕量前端 JavaScript 庫,不含任何伺服端或資料源假設。

### 1.2 授權
Apache License 2.0(<https://github.com/tradingview/lightweight-charts/blob/master/LICENSE>)。附帶條款:含入微軟 `tslib` 部分程式碼採 BSD Zero Clause License;使用者須在 NOTICE 檔的 attribution notice 之上加連結至 `https://www.tradingview.com/`。對照 D-007:純 Apache-2.0(不是 QuantDinger 那種 source-available),自用與日後商用均無阻,唯一硬性要求是保留品牌標示連結。

### 1.3 蠟燭圖、標記、疊加指標、多面板能力
- **Candlestick 系列**是原生內建的七種 series 類型之一(另有 Area、Bar、Baseline、Histogram、Line,以及自訂 series 外掛)。
- **進出場標記**:v5 起 API 為 `createSeriesMarkers(series, markers)`,回傳一個 markers primitive,以 `.setMarkers()`/`.markers()` 管理——這正是「回測結果在蠟燭圖上標出入場點」(D-002)要的功能。舊版 `series.setMarkers()` 已於 v5 廢棄(<https://tradingview.github.io/lightweight-charts/docs/migrations/from-v4-to-v5>)。
- **多面板**:內建 `Panes` 概念,預設單一面板,可加多個 pane 分開顯示不同 series(例如價格面板+成交量面板+指標面板各自一格),提供 `IPaneApi` 管理新增/搬移/調高度/移除(<https://tradingview.github.io/lightweight-charts/docs/panes>)。
- **疊加指標**:同一 pane 內可疊加多條 series(例如均線疊在蠟燭圖上)。

### 1.4 與 Python 後端接駁形態
純前端庫,不對後端語言或協定有任何假設。典型做法:Python 側(vectorbt 跑完回測)把結果序列化成 JSON 陣列 `[{time, open, high, low, close}, ...]`,經 REST 端點或 WebSocket 推給前端,前端呼叫 `series.setData()`(全量)或 `series.update()`(增量)。這與 D-002「單一定義資料層」相容——圖表庫不強加任何儲存格式,資料形狀完全由 Karst 自己的資料層定義。

### 1.5 虛擬籃子自繪蠟燭圖(D-010)可行性
**可行,而且是這個庫最自然的用法。**它不知道、也不關心資料是不是來自交易所——只要 Karst 把「虛擬籃子」的合成淨值序列算成 OHLC 四個數字餵進 `setData()`,畫出來的圖與畫一支真實股票沒有分別。

### 1.6 可借判斷
**整件借,建議作為前端圖表層的預設選擇。**KARST-001 原有的「lightweight-charts 自建前端」結論在本次調研中再獲確認,標記 API(v5 `createSeriesMarkers`)與多面板(`Panes`)兩項功能點齊全,直接對應 D-002 與 D-006 的介面需求。

---

## 二、TradingView Charting Library / Advanced Charts(閉源版)

### 2.1 定位一句
TradingView 官方的完整版圖表庫,內建逾百技術指標與畫線工具、多圖表版面(multi-chart layouts),原始碼不公開於 npm/公開倉,須經申請審批才取得存取權。

### 2.2 授權——這是本節唯一要緊的發現
官方文件明言(<https://www.tradingview.com/charting-library-docs/latest/getting_started/Frequently-Asked-Questions/>、<https://s3.amazonaws.com/tradingview/charting_library_license_agreement.pdf>):

> Advanced Charts 免費授權「is intended for Implementations as a public access service (as a free offering only, and whether account registration is required or not), and not for private, personal or internal uses.」

即:**免費版明文排除私人、個人、內部用途**,只批「公開網頁專案/應用」;而且必須先在官網提交存取申請表,審批通過後才會收到私有 GitHub 倉的邀請,取得原始碼。使用時須保留 TradingView 品牌標示,不可移除。

**對照 D-007「自用先行」——這一格是硬牆,不是可以繞過的軟限制。**Karst v1 的定位正正是「自用工具」,而這份授權條文明文把「私人/內部用途」排除在免費範圍之外。換言之,連申請試用的資格都不齊。

### 2.3 蠟燭圖、標記、疊加指標、多面板能力
功能上是三個候選中最完整的一個(逾百內建指標、畫線工具箱、多圖表版面同時對比),接駁後端經 UDF(Universal Data Feed)協定或自訂 `Datafeed` 介面對接任意後端。若授權允許,技術能力完全能滿足 D-002 與 D-010。

### 2.4 虛擬籃子自繪蠟燭圖可行性
技術上可行(自訂 Datafeed 一樣可以回應任何合成序列),但授權先過不了,此項判斷純屬紙上談兵。

### 2.5 可借判斷
**不可借。**不是「功能不夠」,是「連申請資格都不符」——D-007 定的自用先行前提,直接撞正這份授權明文排除的那一類用途。若 Karst 日後真的走向公開網頁產品(不是純自用工具),屆時可以重新申請,但那已經是另一個問題域,交由 D-005 用戶裁決時另議。

---

## 三、Apache ECharts

### 3.1 定位一句
通用型資料視覺化庫(不止金融),但金融圖表是官方支援的一等公民場景;KARST-010 已查明 Vibe-Trading 的 React 前端正正用它(ECharts 6.1)。

### 3.2 授權
Apache License 2.0(<https://github.com/apache/echarts>),無附加條款,對照 D-007 與 lightweight-charts 同級乾淨。

### 3.3 蠟燭圖、標記、疊加指標、多面板能力
- **Candlestick 系列**是官方原生圖表類型。
- **進出場標記**:`markPoint`(點狀標記)與 `markLine`(線狀標記)皆支援用於 candlestick 系列;但要留意一個限制——官方 issue 討論指出**同一根蠟燭原生只能掛一個 marker**,若要在同一根 K 線上同時標「加倉」與「減倉」等多重事件,需另外疊加一個 scatter/自訂 series 變通(<https://github.com/apache/echarts/issues/9833> 相關討論)。
- **多面板**:`grid` 選項可以在同一張圖裡定義多組座標系(每組自己的 xAxis/yAxis),典型用法是價格面板+成交量面板+指標面板各自一個 grid,是 ECharts 做金融多面板圖的標準做法。
- **疊加指標**:同一 grid 內可疊加多條 line/bar 系列做均線、布林帶等。

### 3.4 與 Python 後端接駁形態
兩條路:(1)純前端,後端只吐一份 ECharts option 形狀的 JSON;(2)用 `pyecharts` 這個 Python 包裝庫,在 Python 側直接組出 option 物件再序列化,省去前端另寫組裝邏輯(常見於 Streamlit 一類場景,如 `streamlit-echarts`)。兩條路都與 D-002「單一定義資料層」相容。

### 3.5 虛擬籃子自繪蠟燭圖可行性
**可行**,道理與 lightweight-charts 相同——`candlestick` series 吃的是任意 `[open, close, low, high]` 陣列。

### 3.6 可借判斷
**整件借,列為 lightweight-charts 的等重候選。**兩者授權同級乾淨,金融圖表核心能力(蠟燭圖+標記+多面板)大致相當,lightweight-charts 標記系統更貼近「單根出入場點」的語意、bundle 更輕、是 TradingView 官方出品,方向感最貼近 D-002 原話「像 TradingView 或 Futu」;ECharts 的優勢在於**一套通吃**——若 Karst 介面除了蠟燭圖之外還要因子分佈直方圖、歸因瀑布圖、相關矩陣熱力圖等非金融圖表(這類需求在因子分析場景下大機率會出現),用同一套庫比維護兩套前端圖表庫的心智負擔更低。此項留待 KARST-007 拍板介面形態時,由用戶在「圖表庫是否要一套通吃」這一點上裁決。

---

## 四、Plotly.py / Dash

### 4.1 定位一句
`plotly.py` 是 Python 原生的互動繪圖庫,`Dash` 是用它搭 Web 應用的框架——兩者搭配可以讓 Python 一個進程完成「算圖+起 Web 應用」,不必另起一套前端專案。

### 4.2 授權
`plotly.py` 與 `Dash` 皆 **MIT**(<https://github.com/plotly/plotly.py>、<https://github.com/plotly/dash>)。付費的是配套雲端服務 **Dash Enterprise**(託管、部署、單一登入一類企業服務,報價區間據市場調查落在每月數千至逾萬美元),**不影響開源核心的授權範圍**——自架自用完全免費,不必碰 Enterprise 那一層。對照 D-007,MIT 與 lightweight-charts、ECharts 同級乾淨。

### 4.3 蠟燭圖、標記、疊加指標、多面板能力
- `go.Candlestick` trace 原生內建。
- 進出場標記用 `add_annotation`/`add_shape` 疊加箭嘴或圖形於指定座標。
- `make_subplots` 做多面板(價格+成交量+指標各自一個 subplot,共用 x 軸)。
- 互動性(拖曳縮放、逐 tick 即時更新的流暢度)不如原生為金融場景而生的 lightweight-charts 或 ECharts——Plotly 的強項是「靜態分析圖表的美觀與易用」,不是「高頻互動的金融看盤介面」。

### 4.4 與 Python 後端接駁形態
**Python 原生,不用分前後端。**vectorbt 回測跑完直接在同一個 Python 進程用 `plotly.graph_objects` 組圖,再用 Dash 包成 Web 應用對外展示——不必像 lightweight-charts/ECharts 那樣另建一層「後端吐 JSON、前端 JS 組裝」的協定。這是三個純圖表庫候選裡唯一不需要維護前後端資料契約的一個。

### 4.5 虛擬籃子自繪蠟燭圖可行性
**可行**,`go.Candlestick` 同樣吃任意陣列,合成序列與真實報價無分別。

### 4.6 可借判斷
**整件借,列為「最快落地」候選。**若 Karst v1 想先用最少的工程把「回測結果畫出蠟燭圖+標記」這件事做出來、不想額外維護一層前後端資料協定,Plotly/Dash 是最短路徑——用戶已用 Python(vectorbt)做核心引擎,Plotly 是同一語言生態內的原生選擇。代價是互動流暢度與「像 TradingView 那種絲滑體驗」(D-002 原話)有落差,若日後要打磨看盤介面的手感,大概率要換到 lightweight-charts 或 ECharts 那一層。此為速度與體驗的取捨,同樣留待用戶裁決。

---

## 五、開源交易終端/回測 UI 外殼先例

### 5.1 OpenBB

**定位一句**:開源金融資料與分析平台(前身「OpenBB Terminal」),圖表層是獨立擴充套件 `openbb-charting`,底層建基於 Plotly + PyWry(用獨立視窗顯示互動圖表)。

**授權——這是本節最關鍵的發現**:2026 年由 MIT 轉為 **AGPLv3**,另設商業授權選項(<https://openbb.co/blog/license-change-openbb-platform-goes-agpl/>、<https://github.com/OpenBB-finance/OpenBB/blob/develop/LICENSE>)。官方 FAQ 明言:對大多數「本地研究使用」的用戶沒有影響,但**修改程式碼並將之分發或作為 SaaS 對外提供服務者,須揭露對應原始碼,否則須另購商業授權**(<https://docs.openbb.co/platform/faqs/license>)。

對照 D-007:純自用階段(不對外提供服務)引用不受影響,但這與 D-007 第 3 點「引擎/介面隔離,日後商品化只換一件」的原則有摩擦——AGPL 的「網路服務條款」(network use clause)比 GPL 更嚴,一旦 Karst 日後真的把借用 OpenBB 程式碼的部分接成 SaaS 對外服務,揭露原始碼的義務會擴散到整個提供服務的程式,不是換一個模組就能了事。

**蠟燭圖+標記+疊加+多面板**:能力同 Plotly 一節(底層同一套)。

**接駁形態**:REST API 或 Python Client,圖表以 figure 物件顯示。

**虛擬籃子自繪蠟燭圖**:技術上可行,但要先接受它整套資料供應商抽象層的架構。

**可借判斷**:**只借思路**——它的「擴充套件(extension)分層」與「資料供應商 provider 抽象層」設計,對 Karst 「引擎可換件」(D-007)的介面設計有參考價值;程式碼本身因 AGPL 的網路服務條款,不建議整件抽入。

### 5.2 QuantDinger 前端(KARST-010 已核實,此處重申結論)

Source-available,非商業實體免費,**商業用途須另購授權**,禁止移除品牌水印。對照 D-007「SaaS 留門」,這是現成的反面教材:後端開源、介面鎖死在禁商用授權後面。**不可借**,判斷與 KARST-010 一致,不重複查證細節。

### 5.3 vnpy(本票新增)

**定位一句**:內地最活躍的開源量化交易框架之一,自帶 PySide6 桌面 GUI 與一個原生 Python、事件驅動的高效能圖表元件(`vnpy_evo.chart` / `ChartWidget`)。

**授權**:**MIT**(`Copyright (c) 2015-present, Xiaoyou Chen`,<https://github.com/vnpy/vnpy/blob/master/LICENSE>),無附加條款,對照 D-007 全無阻礙。

**蠟燭圖+標記+疊加+多面板**:圖表元件原生支援串流即時更新(逐 tick/逐根畫),搭配其事件驅動引擎(`EventEngine`)把行情/成交事件即時推給圖表;疊加指標與多面板由其圖表元件的 item 系統支援。

**接駁形態**:**這是本節裡唯一一個「Python 原生桌面殼」的先例**——不是 Web 前端接 JS 圖表庫,而是 Qt 桌面元件直接吃 Python 物件(`BarData`)。若 Karst 考慮「像 Futu 桌面版那樣一個原生應用」而非純 Web 應用,這是目前查到的唯一同構先例。

**虛擬籃子自繪蠟燭圖**:可行,`BarData` 只是一組 OHLCV 欄位的資料類別,合成籃子的每日淨值一樣可以包成 `BarData` 序列餵進去。

**可借判斷**:**借思路,視 Karst 選 Web 殼或桌面殼而定**。若最終定案是 Web 應用(較符合「日後 SaaS 留門」的 D-007 第 2 點,Web 部署天然比桌面應用更接近服務化),vnpy 的圖表元件本身不會被整件抽用,但它「事件驅動餵圖表」的思路仍可借;若日後真的評估桌面殼路線,`ChartWidget` 值得整段細讀。

---

## 六、建議組合

**建議:前端圖表層採 TradingView lightweight-charts 為主(整件借),Python 側(vectorbt 回測產出)經一層薄 REST API 把結果序列化成 JSON 餵給它;若介面日後需要大量非金融統計圖表(因子分佈、歸因瀑布、相關矩陣),再評估是否整體換成或搭配 ECharts 一套通吃。TradingView Charting Library(閉源版)因授權明文排除私人/內部用途,連候選資格都不具備,排除。若想以最少工程先做出「回測結果畫蠟燭圖+標記」的第一個可用版本,Plotly/Dash(Python 原生、無需另起前後端協定)是一條更快但互動體驗較弱的替代路徑,兩者可視 KARST-007 對「先求快或先求體驗」的裁決而定。開源交易終端外殼(OpenBB、QuantDinger 前端、vnpy)沒有一個整件適合當地基,但各自在「引擎隔離分層」(OpenBB)、「授權反面教材」(QuantDinger)、「Python 原生事件驅動圖表」(vnpy)三點上留下可借的思路。**

**這只是本票的建議。最終前端圖表庫、是否雙庫並行、Web 殼或桌面殼,一律由用戶裁決(D-005)。**

---

## 七、未解與風險

| 項目 | 說明 |
|---|---|
| lightweight-charts 與 ECharts 的實際互動流暢度未實測 | 兩者官方文件與 demo 都聲稱高效能,但「串流即時更新 + 多面板同時開幾十支標的」這種 Karst 實際場景下的流暢度沒有做過對比測試 |
| ECharts 的 markPoint 單根蠟燭一個標記的限制 | 若 Karst 需要在同一根 K 線同時標示「加倉」與「觸發停損」等多重事件,ECharts 原生 API 需要用疊加 series 變通,未實測變通後的視覺與效能表現 |
| Plotly 的高頻更新效能未實測 | 官方定位偏向靜態/互動分析圖,而非為逐 tick 高頻更新設計;若 Karst 日後要做近即時的紙上交易看盤,這條路是否夠快沒有查證 |
| OpenBB AGPL 對「只借思路,不抽程式碼」是否完全免責 | 只借設計思路(分層架構)不涉及程式碼複製,一般認為不觸發 AGPL 義務,但本票未就此徵詢法律意見,若日後真的貼近抄其架構到程式碼層級,建議另外覆核 |
| vnpy 圖表元件的實際效能與可讀性未細查 | 只查證了授權與存在性,未讀 `ChartWidget` 原始碼細節,若日後真的評估桌面殼路線,需要另開查證 |

---

## 出處一覽

**圖表庫**
- TradingView lightweight-charts — <https://github.com/tradingview/lightweight-charts>
- lightweight-charts LICENSE(Apache-2.0)— <https://github.com/tradingview/lightweight-charts/blob/master/LICENSE>
- lightweight-charts v4→v5 遷移文件(`createSeriesMarkers`)— <https://tradingview.github.io/lightweight-charts/docs/migrations/from-v4-to-v5>
- lightweight-charts Panes 文件 — <https://tradingview.github.io/lightweight-charts/docs/panes>
- TradingView Advanced Charts(閉源版)產品頁 — <https://www.tradingview.com/advanced-charts/>
- Advanced Charts FAQ(「not for private, personal or internal uses」條文所在)— <https://www.tradingview.com/charting-library-docs/latest/getting_started/Frequently-Asked-Questions/>
- Advanced Charts 免費授權協議全文 PDF — <https://s3.amazonaws.com/tradingview/charting_library_license_agreement.pdf>
- Apache ECharts — <https://github.com/apache/echarts>
- ECharts markPoint 單根一標記限制討論 — <https://github.com/apache/echarts/issues/9833>(前身倉 incubator-echarts)
- Plotly.py — <https://github.com/plotly/plotly.py>
- Dash — <https://github.com/plotly/dash>

**開源交易終端/UI 外殼**
- OpenBB — <https://github.com/OpenBB-finance/OpenBB>
- OpenBB 授權由 MIT 轉 AGPL 公告 — <https://openbb.co/blog/license-change-openbb-platform-goes-agpl/>
- OpenBB LICENSE — <https://github.com/OpenBB-finance/OpenBB/blob/develop/LICENSE>
- OpenBB 授權 FAQ — <https://docs.openbb.co/platform/faqs/license>
- OpenBB 圖表擴充套件文件 — <https://docs.openbb.co/odp/python/extensions/infrastructure/openbb-charting>
- QuantDinger-Vue LICENSE(source-available,已在 KARST-010 核實)— <https://github.com/OpenByteInc/QuantDinger-Vue/blob/main/LICENSE>
- vnpy — <https://github.com/vnpy/vnpy>
- vnpy LICENSE(MIT)— <https://github.com/vnpy/vnpy/blob/master/LICENSE>

**背景**
- KARST-010 指定倉調研(Vibe-Trading 用 ECharts 6.1、QuantDinger 前端授權已核實)— [research/2026-08-25-named-repos.md](2026-08-25-named-repos.md)
