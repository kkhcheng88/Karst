# 決策簿 — Karst

> 鐵律:本簿永遠只寫「現在的真相」;歷史由 git 保存。

## D-001 目的地:鎖定 v1 規格再開工,Epic「V1 藍圖」承載
- 類型：決策
- 狀態：有效
- 日期：2026-08-25

- 出處：用戶 2026-08-25 勾選裁決(選項「鎖定規格再開工」)

- 背景：承接 KarstETF 停案裁決(該倉 D-015):MD 為骨幹的研究項目難管理難擴展,Karst 要以 SDLC 角度重建,治理行先。

- 決策：
  1. 本次 wayfinder 的目的地=Karst v1 規格定案:全部關鍵裁決落簿、匯成規格文件、經用戶核准後才拆建置票開工。
  2. 以 Epic「V1 藍圖」承載這批決策票;交付品 KARST-D01「Karst v1 規格」。
  3. 用戶勾選開票:回測框架調研、因子基建調研、因子合約、非結構化轉因子定義、樽頸策略嚴格定義、策略與基準概念模型、應用與評估形態,加收尾規格匯整票;治理工作流、v1 界外清單、資料模型原型三張用戶勾選不開,日後需要再議。

- 考慮過的替代方案：
  1. 先建骨架邊建邊定——用戶未揀,規格滾動與舊項目文件漂移病同源。
  2. 只做決策收斂不建新系統——範圍太窄,答不到「proper backtest engine」的訴求。

- 影響：第一批票(KARST-001 至 KARST-008)全部掛 Epic「V1 藍圖」與交付品 KARST-D01。

## D-002 產品形態:應用程式連蠟燭圖出入場;核心引擎要矩陣式/蒙地卡羅級性能
- 類型：決策
- 狀態：有效
- 日期：2026-08-25

- 出處：用戶 2026-08-25 原話(見引文)

- 決策：
  1. Karst 是一個應用程式,不是 chat 加文件。
  2. 回測結果要在蠟燭圖上看得到出入場點,體驗對標 TradingView / Futu。
  3. 核心引擎要嚴謹成程式(properly a programme):矩陣式(向量化)或蒙地卡羅式,一秒可模擬大量交易。
  4. 資料庫所有定義單一正本、無第二影像;支援多策略。

- **用戶原話（原文照錄）**

  > I want to establish a proper backtesting and paper trading running tool to evaluate the performance as well. All database should have only 1 definition, no second image, then we have a proper definition of backtesting. It should be able to support multiple strategy.

  > I want to have solid rules and control so it is properly a programme instead of agentic chat based project already.

  > To be honest, I want something like a Trading View or Futu, for backtest I can really see the CandleStick chart, with the entry and exit. And the product should be an application, but not just a chat and document

  > And I think the core engine should be very well scripted, even like matrix based or monte carlo based with can simulate lot of trade in a sec

- 影響：回測框架調研票(KARST-001)的評估準則必須包含向量化性能、蒙地卡羅支援與圖表 UI;應用與評估形態票(KARST-007)以蠟燭圖出入場為核心場景。

## D-003 核心概念初裁:一切信號歸一為量化因子;SA 是策略、QQQ 是基準;節奏是策略參數
- 類型：決策
- 狀態：有效
- 日期：2026-08-25

- 出處：用戶 2026-08-25 原話(見引文)

- 決策：
  1. 一切信號歸一為量化因子:觸發可以來自量化(非結構化信號)或質化(技術面),入引擎前統一為因子。
  2. 非結構化材料(逐字稿、分析員報告、agent 研究)轉成信號是通用能力,不是單一策略專屬管線;該轉換必須有清晰嚴格的定義。
  3. 「跟隨 SA」本身是一個策略;QQQ 是基準,不是策略。
  4. 換倉節奏是策略參數,不是平台常數;揀節奏的原則是配合策略基本面擺動、防過擬合。
  5. 生產中系統出信號,用戶只揀買或不買;平台服侍的是挑戰策略設計,不是週期性人手拍板流程。

- **用戶原話（原文照錄）**

  > The trigger can be quantitive (Unstructured Signal) or qualitative (Technical). To you honest, if each type of signal can be a quant factor, you can start unstructured signal can be a quant factor as well

  > Actually I am more to challenge the design of strategy. In production I should have nothing to 拍, system give me the signal. I just choose to buy or not buy.

  > I think if you taking SA is a strategy (to follow SA), then QQQ is just a benchmark.

  > The key is that we can convert unstructured data into signal in general

- 影響：CONTEXT.md 詞彙表據此定義因子/信號/策略/基準/換倉節奏五詞;因子合約票(KARST-003)與非結構化轉因子票(KARST-004)以本條為前提。

## D-004 首個策略:樽頸(供需故事),承繼「主題→鏈位→敘事」框架,定義要比舊項目嚴格
- 類型：決策
- 狀態：有效
- 日期：2026-08-25

- 出處：用戶 2026-08-25 原話(見引文)

- 決策：
  1. Karst 首個正式策略是樽頸策略(Bottleneck / Demand Supply Story),以非結構化材料為主要輸入。
  2. 承繼 KarstETF 的「主題→鏈位→敘事」框架;承繼的具體範圍(鏈位登記表、過閘全買平均分等)由樽頸策略嚴格定義票拍板。
  3. 這個非結構化因子必須以清晰定義成形,嚴格程度高於舊項目。

- **用戶原話（原文照錄）**

  > The 1st strategy is on Bottleneck (Demand Supply Story) based on unstructured data (Transcript, Analyst Report or Agent research)

  > I think yes it is needed? And then this time we need to be more 嚴格, this unstructure factor need to form with a clear definition

- 影響：樽頸策略嚴格定義票(KARST-005)以本條為範圍;舊倉鏈位登記表與逐字稿庫列為候選承繼資產。

## D-005 工作方式:業務需求先行;技術選型先查 GitHub 現成框架,不預設自建;舊項目研究欠帳押後
- 類型：決策
- 狀態：有效
- 日期：2026-08-25

- 出處：用戶 2026-08-25 原話(見引文)

- 決策：
  1. 與用戶對談只談業務層;技術與架構決定押後於業務定義。
  2. 不預設由零自建:現成回測框架先在 GitHub 調研,借用/自建/混合由調研結果連同用戶裁決。
  3. KarstETF 兩筆研究欠帳(四單可信度稽核、開頭行運檢驗)押後處置,先定義新 Karst;引用舊績效數字(+459.5% 一類)時一律當未驗證。

- **用戶原話（原文照錄）**

  > Can we focus on the business requirement first? As technical or architecture to be honest I think we may not neccessary to build from scratch and we need research in Github

  > We define the new Karst first.

- 影響：回測框架調研票(KARST-001)是架構決定的前置;任何規格文件引用舊績效須附「未驗證」註記。

## D-006 策略定位:選股與評估為主體,優化在組合層;不做日內、不做單股入場優化
- 類型：決策
- 狀態：有效
- 日期：2026-08-25

- 出處：用戶 2026-08-25 原話(見引文)

- 決策：
  1. Karst 服侍的策略形態是選股(stock selection)與評估,不是單一股票的擇時。
  2. 不做日內交易、不做剝頭皮;應用不是單股入場優化工具。
  3. 優化(optimisation)落在組合層(portfolio level),不在單股入場層。

- **用戶原話（原文照錄）**

  > and the strategy is always more on 選股 but not timing on 1 stock. In our strategy, we are not doing day trading or scraping, so the application is not for single stock entry optimatization. It is about stock selection and evaluation, and optimatization is on portfolio leval

- 影響：回測框架調研票(KARST-001)評估準則加入橫斷面選股/組合層回測,主打 tick 級執行的方案降權;策略與基準概念模型票(KARST-006)及應用與評估形態票(KARST-007)以組合層為主視角。

## D-007 選型約束:自用先行,SaaS 留門;核心引擎須隔離在自家介面後,可整件換走
- 類型：決策
- 狀態：有效
- 日期：2026-08-25

- 出處：用戶 2026-08-25 原話(見引文)

- 決策：
  1. 第一優先是支援用戶自己的交易;純自用,選型可自由採用帶 Commons Clause 一類禁售條款的方案(vectorbt、PyBroker 在候選之列)。
  2. SaaS 是產品成熟後的興趣,不是 v1 目標;v1 不為 SaaS 做任何多餘工程。
  3. 唯一為 SaaS 預留的一步:核心回測引擎必須隔離在自家介面之後——因子合約、策略註冊、資料層只依賴 Karst 自己的定義,不直接依賴第三方引擎的型別;引擎是可換件。
  4. 日後商品化之前必做授權覆審,屆時受限核心換走即可,不用重寫語意層。

- 為何選這個：禁售條款只綁引擎本體;把引擎收在介面後,自用期享受最好的現成件,商品化期只換一件,兩頭不吃虧。

- **用戶原話（原文照錄）**

  > 自用 first as we can freely use what we can use. First Priority is to support my own trader. But I am interest to form SaaS if the product is mature

- 影響：試跑對決票(KARST-009)按此開;規格匯整票(KARST-008)必須載明引擎隔離原則。

## D-008 策略討論的定位:只為摸清策略性質以支撐架構,不是替用戶分析策略
- 類型：決策
- 狀態：有效
- 日期：2026-08-25

- 出處：用戶 2026-08-25 原話(見引文)

- 決策：
  1. 與用戶談策略的目的是抽取策略的性質(落注單位、因子形態、材料、節奏、組合操作),據此推導平台要支援的能力。
  2. 策略本身的內容與參數取值是用戶的領域;agent 不裁定、不優化策略內部數值。
  3. 平台對策略內部數值(門檻、閘值一類)的責任形態是:做成可掃描的參數,支援用戶自己實驗。
  4. 開源參考調研收口:引擎與因子層已飽和,不再加;應用外殼/圖表、材料取得管線兩張研究票分別等 KARST-007 與材料範圍定案後才開。

- **用戶原話（原文照錄）**

  > For strategy, my intention is that only for our to know more about the naturee of strategy I would like to play. As such the technical architecture can be supported. It is not really for you to analysis the strategy itself

- 影響：KARST-005 的談法照此收窄:八條問題的答案只用於推導平台能力,策略數值一律參數化。

## D-009 樽頸策略 v1 性質裁決(KARST-005 兩輪追問所得)
- 類型：決策
- 狀態：有效
- 日期：2026-08-25

- 出處：用戶 2026-08-25 於 KARST-005 追問兩輪的回答(原話見引文)

- 決策：
  1. 「閘中藏 alpha、過閘全買」只當起點不當教條:用戶視舊測試為初步結論,基本面上有些股應優於其他;現實中一個鏈位成員可遠多於兩三隻,不可能隨機揀亦不可能全買。v1 先以鏈位(板塊)層證明 alpha,選股因子日後可加。
  2. 落注單位兩層都要:鏈位與個股同入資料模型;v1 以鏈位先行。
  3. 鏈位登記表重建、不遷移:舊項目資料仍可取用,但登記表按因子合約式規範重寫,以求更可治理、更可擴展。
  4. 因子形態以「連續分數+參數閘」為目標;用戶警示非結構化材料未必可線性刻度,故因子值的語意(序數還是基數)須在因子合約(KARST-003)正式裁決。
  5. 非結構化材料以逐字稿先行,其他材料(分析員報告、agent 研究)後補。
  6. 樽頸強度一旦成為量化因子,即可與其他因子組合使用——平台必須支援多因子組合。
  7. 換倉節奏:一旦逐字稿可量化成因子,頻率是選擇不是設計——日度亦應行得通,現實月度合理,回測可用季度做更嚴苛考驗。引擎必須節奏無關;不設任何預設值,每次執行由用戶指定(用戶反問「Why we need a default?」)。

- **用戶原話（原文照錄）**

  > But start with sector make us easier to proof the alpha on this strategy

  > if we can explore a better way - especially to normalizing it like a quant factor contract as you mentioned - could make the engine this time more scalable and govenedd

  > unstructured data could be hard to linear scaling the effect

  > if the bottleneck strength become a quant factor. Then it can be be fixing with other factor to use?

  > rebalance frequency is a choice but not an design as daily should workable as well

  > Why we need a default?

- 影響：KARST-003 須裁因子值語意(序數/基數);KARST-004 材料範圍以逐字稿先行;引擎與資料模型不得寫死節奏或內置預設節奏;組合構成走通用多因子組合路線。

## D-010 平台原語:虛擬籃子第一等公民、SA 入選可為 0/1 因子、v1 仍要第二個正式策略
- 類型：決策
- 狀態：有效
- 日期：2026-08-25

- 出處：用戶 2026-08-25 於 KARST-005 追問第二、三輪的回答(原話見引文)

- 決策：
  1. 虛擬籃子升格為第一等公民:平台可定義「籃子」(一組成員+權重規則,成員名單有版本、有生效期),引擎把它當一個可投資對象——有自己合成的價格/淨值序列,畫得出自己的蠟燭圖,回測與紙上交易直接落注到它。概念類同 Futu 一類券商的虛擬產品(virtual ETF)。鏈位籃子、SA 組合都是它的實例。
  2. SA 入選本身可建模為一個 0/1 量化因子,供任何策略取用;「跟隨 SA」不必是獨立策略形態的唯一寫法。
  3. v1 仍需第二個正式策略上紙上交易長期跟蹤,以證明多策略——單靠架構與測試案例不足夠。第二個策略選哪個,留待策略與基準概念模型(KARST-006)裁決。
  4. QQQ 與 SPY 同類,皆為基準。

- **用戶原話（原文照錄）**

  > We can form a virtual product in which FUTU or else usually does. It is just a sort of virtual ETF concept.

  > Or you can event say SA selection can become a quant factor of itself? (1 or 0)?

  > QQQ is benchmark like SPY

- 影響：資料模型加「籃子」實體(成員版本化、權重規則、合成淨值);圖表層支援籃子蠟燭圖;引擎落注對象由「股票」推廣為「可投資對象」;KARST-006 承接「第二個正式策略選哪個」;策略/基準/因子三分法照 D-003 但補上「成員名單可降維為 0/1 因子」一途。

## D-011 v1 回測核心採用 vectorbt(用戶拍板)
- 類型：決策
- 狀態：有效
- 日期：2026-08-25

- 出處：用戶 2026-08-25 於原生選項介面揀選「vectorbt (Recommended)」

- 決策：
  1. v1 回測核心採用 vectorbt(免費版),依據為 KARST-009 同機同數據實測:結果與對照引擎幾乎一致、單次回測快約 40 倍、一千組參數掃描快約 20 倍。
  2. 授權界線:vectorbt 免費版不准出售軟件本身;自用(D-007 自用先行)完全合規。日後商業化前須重審授權,引擎隔離在自家介面之後、可整件換走(D-007)。

- **用戶原話（原文照錄）**

  > vectorbt (Recommended)

- 影響：引擎適配層工作可以開展;A-001 已核實成立;若日後商業化,換引擎的出口保留在自家介面。

## D-012 v1 第二個正式策略:因子混合(質素/價值/動能/低波),ETF 版先行
- 類型：決策
- 狀態：有效
- 日期：2026-08-26

- 出處：用戶 2026-08-26 於原生選項介面裁決;策略內容出自用戶指定影片(YouTube zRvKJYVIeis)的性質抽取

- 決策：
  1. v1 第二個正式策略定為因子混合策略:以標普四隻風格指數(高質 Quality、平靚 Enhanced Value、動能 Momentum、低波 Low Volatility)對應的因子敞口混合成一個組合,上紙上交易長期跟蹤,與樽頸策略並列證明多策略。
  2. 落注形態分兩階段:v1 直接買現成因子 ETF(如 SPMO、QUAL)混權重,引擎只需把 ETF 當可投資對象;日後平台引入選股因子(行情/財務數據管線+因子計算層)後,可轉為自算因子分數選股(用戶原話見引文)。
  3. 此策略全部訊號來自結構化數據,與樽頸策略(非結構化因子)形成光譜兩端,兩者同歸一個因子合約——正是平台通用性的驗證案例。

- **用戶原話（原文照錄）**

  > Later when we introduction stock selection factor then can be choose ourselves before than we just use ETF

- 影響：KARST-006 的「第二個正式策略選哪個」一格已定;引擎 v1 必須支援 ETF 做可投資對象(與 D-010 虛擬籃子並列);因子計算層(自算分數)列為日後版本,不入 v1 規格主體;策略清單仍未數完,KARST-006 繼續開著收集。

## D-013 策略分層模型與兩種合約:選股漏斗四層、因子與進出場規則分家、共用風控層
- 類型：決策
- 狀態：有效
- 日期：2026-08-26

- 出處：用戶 2026-08-26 於 KARST-006 追問的回答(原話見引文);「兩種合約」與「共用風控層」屬用戶採納本 agent 建議

- 決策：
  1. 策略分層模型:一個策略的選股漏斗由至多四層組成——1) 非結構化量化/基本面 2) 技術量化 3) 圖形 4) 技術分析理論。「>」為優先/漏斗關係:逐層篩選,上一層的輸出是下一層的宇宙(用戶:「選擇大於努力,so filtering make sense」)。每個策略自選其中一至多層組合,多數只用一兩層——簡單勝複雜(用戶明令 simple wins complex always)。
  2. 圖形與 TA 的界線改為「機械化得到與機械化不到」:圖形形態若寫得成機械規則(VCP、趨勢線支持阻力一類),即屬 TA 的一部分(用戶原話);機械化不到的主觀裁量部分,v1 明確排除在引擎外,Video to Skill 抽取時照實標明留人手。
  3. 兩種合約:機械化訊號分兩類各立合約——選股類(因子:每日每股一數值,可排名可組合,四層漏斗屬此)與進出場類(規則:止蝕、目標、倉位、熔斷,事件式)。D-003「一切訊號歸一因子」的適用範圍收窄為選股訊號;進出場規則另立一等公民。用戶採納的條件:所有定義與規則必須單一正本,治理為要(原話見引文)。
  4. 共用風控層:單筆風險上限、月度虧損熔斷、風險回報比門檻一類風控規則,抽成平台層面所有策略共用的一層;每個策略可用可不用、參數自設,定義只有一個正本。

- **用戶原話（原文照錄）**

  > I think it is really priority or 漏斗:逐層篩選, as I believe 選擇大於努力. So filtering make sense. But again each strategy can have its combination of these layer.

  > And most of the time should have 1 or 2 layer as simple wins complex always.

  > Graph I am wondering if you can't effectively build a mechanical way for pattern? But if you can, actually Graph is part of the TA to me. For example, say if you can identify VCP, or the trendline support or resistant

  > 採納 as long as the definition and rules should be single golden source. Govenance is the key

- 影響：KARST-003 因子合約的範圍定為選股類;新增「進出場規則合約」須在規格內成文(歸 KARST-006/008);共用風控層入 v1 規格;引擎輸入型別為因子面板+事件規則兩種(vectorbt 兩者皆承載,KARST-009 已證);單一正本原則(D-002)延伸覆蓋規則類定義。

## D-014 Video to Skill 管線成立;Eric 策略入泊車位待補執行細節
- 類型：決策
- 狀態：有效
- 日期：2026-08-26

- 出處：用戶 2026-08-26 指示與追問回答(原話見引文)

- 決策：
  1. Video to Skill 為 Karst 正式管線概念:KOL 交易員影片→字幕抽取→形式化成策略規則(可機械化部分)→回測驗證其方法是否成立。用途有二:學習(把 KOL 方法變成看得清的規則)與驗證(聲稱放落歷史數據檢驗)。此為「非結構化材料→因子」路線的延伸:材料不止變因子,亦可變成套策略規則。
  2. 第一個對象 Eric(劉栢言,投資先要溫功課)已完成三片抽取(research/2026-08-26-trader-eric-video-to-skill.md):可機械化程度高,14 條規則可直接入引擎;但其十套策略只公開四類,現時骨幹版僅為均線+突破+嚴格風控。
  3. Eric 策略定位:泊車位——不列 v1 正式策略、暫不回測,待用戶補充其執行細節(會員內容、書單一類)再議升格。

- **用戶原話（原文照錄）**

  > I want to copy strategy from the KOL trader. It is more like a Video to Skill concept to form a strategy. Then I can learn from the KOL, and also to evaluate whether their approach make sense

  > Parking lot as I think we need more information on the execution details of his steps?

- 影響：v1 正式策略維持兩個(樽頸、因子混合);Video to Skill 抽取管線列入平台能力(與逐字稿管線同族);Eric 筆記存 research/ 待補料;業績聲稱(5 戰 5 冠、36 個月零負回報)一律標自述未核實。
