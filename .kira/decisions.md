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

## D-015 v1 第三個正式策略:Minervini SEPA/VCP(用戶拍板)
- 類型：決策
- 狀態：有效
- 日期：2026-08-26

- 出處：用戶 2026-08-26 於原生選項介面揀選「列第三個正式策略」

- 決策：
  1. Minervini SEPA/VCP 列為 v1 第三個正式策略:趨勢模板八條準則做選股閘,VCP 結構定義做進場形態,止損百分比與風險回報比按書中條文參數化。規則來源為四本《股票魔法師》中文版的抽取(research/2026-08-26-minervini-sepa.md),具體數字引用前按筆記標註核對。
  2. v1 正式策略清單至此:① 樽頸(非結構化因子)② 因子混合(結構化因子,ETF 先行)③ Minervini SEPA/VCP(技術規則+進出場規則)。三套恰好各自考驗平台三種輸入形態:非結構化轉因子、多因子組合、選股閘+事件式進出場規則(D-013 兩種合約)。
  3. Eric 維持泊車:缺的不是無字幕影片(用戶明言不需要),而是佢十套策略的內容本身(公開材料只披露四類)與週期階段規則的數值門檻;升格條件是用戶日後提供 Patreon 一類非公開材料。

- **用戶原話（原文照錄）**

  > What is missing? video without transcript is not needed

- 影響：KARST-008 規格匯整以三個正式策略為準;引擎驗收案例應覆蓋三種輸入形態各一;Eric 筆記維持 research/ 存檔,不入回測隊列。

## D-016 v1 第四個正式策略:趨勢波段(由 Eric 骨幹一般化),兼任引擎試練場
- 類型：決策
- 狀態：有效
- 日期：2026-08-26

- 出處：用戶 2026-08-26 裁決(原話見引文),agent 建議獲用戶採納的部分已註明

- 決策：
  1. Eric 系統一般化為「趨勢波段」(Trend Swing)策略,列 v1 第四個正式策略——v1 只做這一套純技術波段,日後隨用戶知識檢驗逐步改良。用已抽齊的零件組成:突破 N 日新高入場、前波段低位與均線成本線做支持阻力、三元素交易計劃(入場/止蝕/目標)、風險回報比門檻、共用風控層(2% 單筆風險、月度熔斷)。純風險回報驅動,與基本面無關,天花板由賠率定義(用戶語)。
  2. 此策略兼任回測引擎的試練場:純價格數據即可運行,全程操練 D-013 進出場規則合約與共用風控層,並以大規模參數掃描(N 日、賠率門檻、止蝕擺位、節奏)測試引擎。
  3. 防過擬合規矩(agent 建議,依用戶一貫防過擬合立場):參數掃描的評估準則是穩健平原而非單點最優——最優參數鄰域表現皆佳才算穩健,孤峰視為擬合噪音;配合已收錄的「一條規則須在約 500 個歷史案例驗證」驗收要求。
  4. 供求事件(IPO 流通量、指數納入被動買盤一類)不鎖死於單一策略,做成可共用的供求事件因子——與樽頸策略(供需故事)同思路不同材料,兩邊皆可取用(用戶明示此交匯點重要)。
  5. Eric 本人的完整系統維持泊車(D-015 條款不變);本策略是一般化產物,不冠名、不聲稱等同其系統。

- **用戶原話（原文照錄）**

  > I think such kind of pure technical swing trade is really non-fundmental related and the ceiling is defined, ppurely risk-reward.

  > As for now, we will just do 1 pure technical Swing Trade which will be this. We can improve and improve when my knowledge we have examinated.

  > I think this is a good arena to test our backtest engine especially this mean a lot of parameter testing

- 影響：v1 正式策略共四套:樽頸、因子混合、Minervini SEPA/VCP、趨勢波段;四套覆蓋非結構化因子、多因子組合、選股閘+形態、純進出場規則四種形態。引擎第一個實跑案例定為趨勢波段;規格(KARST-008)須含參數穩健性報告要求;供求事件因子列入因子清單,歸 KARST-003/004 承接。

## D-017 名家組合:跟隨入 v1(SA、Pelosi 虛擬籃子+入選因子);倒推成知識立票後行
- 類型：決策
- 狀態：部分已取代（見 D-022）
- 日期：2026-08-26

- 出處：用戶 2026-08-26 提出並於原生選項介面裁決(原話見引文)

- 決策：
  1. 名家組合跟隨入 v1:SA 組合與 Pelosi 組合各建一個虛擬籃子(成員名單有版本有生效期,D-010),並各出一個 0/1 入選因子供任何策略取用(SA 一途 D-010 已裁,Pelosi 同構)。
  2. 披露時滯規則:名家組合的成員變動一律以「知情時間」(披露可得之日)入庫,不以事件時間(實際買賣之日)——Pelosi 一類國會申報可遲至 45 日,用事件時間回測會得出假成績。此為因子合約兩條時間戳的第一個強制案例。
  3. 組合倒推成知識(Portfolio to Skill)為 Video to Skill 同族管線:由持倉時序倒推背後概念(共同特徵、板塊傾斜、動能一類假設),假設寫成因子或規則,回測驗證其是否解釋該組合行為;產出是可檢驗的概念,不是複製。立票後行,排在引擎跑起之後。

- **用戶原話（原文照錄）**

  > SA is 1 portfolio, And Pelosi is another porfolio I woould like to follow. Somehoow I even want to reverse engine this porfollio they hold into knowledge and skill. To deduce their concept behind, and then we can backtest as well

- 影響：v1 規格加兩個虛擬籃子實例與兩個入選因子;因子合約(KARST-003)必須含事件時間/知情時間雙時間戳;新開票承接倒推管線;數據面新增披露類來源(SA 名單、國會申報),取得方式屬材料管線範圍。

## D-018 v1 第五套正式策略:錯殺(事件錨定的質優超賣)
- 類型：決策
- 狀態：有效
- 日期：2026-08-26

- 出處：用戶 2026-08-26 提出並於原生選項介面裁決(原話見引文)

- 決策：
  1. 「錯殺」列 v1 第五套正式策略:基本面良好但被市場超賣的股票,成員由規則篩選產生(非外部名單),自動入籃、回測、紙上交易長期跟蹤。
  2. 觸發形態為事件錨定:必須有一個「不確定性落地」事件(業績、指引、訴訟結果一類)後仍大跌,才入候選——候選少而精。用戶例子:BE 好業績剛公布仍大跌。
  3. 分層構成(照 D-013 漏斗):基本面/質素閘 → 超賣度(技術量化)→ 事件錨。質素閘與超賣度的具體門檻一律參數化(D-008),留用戶實驗。
  4. 此策略與趨勢波段互為鏡像(一追強勢、一執錯殺),兩者共用進出場規則合約與共用風控層。

- **用戶原話（原文照錄）**

  > This is usually about the stock which the fundmental is good but the market still oversold. Especially when the uncertainty is clear but still oversold (e.g. Very good result just released but still dropping a lot. like recently for BE)

- 影響：v1 正式策略共五套;數據面需要業績/事件日曆與基本面數據(用戶提過基本面有外部參考材料,後補討論);事件錨定義歸因子合約的事件時間/知情時間體系;KARST-008 規格照五套匯整。

## D-019 圖表庫選型:lightweight-charts(用戶拍板)
- 類型：決策
- 狀態：有效
- 日期：2026-08-26

- 出處：用戶 2026-08-26 於原生選項介面揀選「lightweight-charts (Recommended)」

- 決策：
  1. 應用圖表層採用 TradingView lightweight-charts(Apache-2.0):蠟燭圖+進出場標記+多面板原生支援,虛擬籃子合成序列照畫;授權自用與日後 SaaS 皆無障礙(D-007)。依據 KARST-014 調研(research/2026-08-26-charting-ui-references.md)。
  2. 閉源 TradingView Charting Library 因授權明文禁止私人/內部用途,永久出局;Plotly/Dash(MIT)列為求快後備。
  3. 原型(KARST-015)以 lightweight-charts 為基砌。

- **用戶原話（原文照錄）**

  > lightweight-charts (Recommended)

- 影響：KARST-015 原型技術基座已定;KARST-007 討論應用載體時前端已有錨點;設計系統的圖表元件一格由此起。

## D-020 應用形態:研發主軸、本機網頁、唯一入口治理、紙上全自動、五畫面兩層指標
- 類型：決策
- 狀態：部分已取代（見 D-025）
- 日期：2026-08-26

- 出處：KARST-007 grilling,用戶 2026-08-26 三輪原生選項介面裁決

- 決策：
  1. 旅程主軸=策略研發;首頁以策略為中心(五套策略+SA/Pelosi 各一張卡)。日常巡查與紙上交易退居第二層。
  2. 應用載體=本機網頁(瀏覽器開本地網址;重計算在後端 Python,前端只畫圖;日後 SaaS 同一條路)。
  3. 回測由腳本發起,介面只睇結果,不設跑回測按鍵。
  4. 治理住在唯一入口,不住在對話:所有策略定義、參數、回測運行一律經同一套命令入庫,由它查合約、蓋版本時間戳、留血統;任何人或 agent 都不可繞過直接寫庫。(依用戶原話推出:「All I care is the governance and ensure the same kit applies for all strategy and backtesting」)
  5. Agent 對話 v1 用現有環境(Claude Code),不內嵌;後端接口明文預留 agent 內嵌位,日後 SaaS 加門面不重建。用戶問及 HKUDS VibeTrader 內嵌路線,經解釋後採此案。
  6. 紙上交易全自動照訊號入帳,終態無人手介入(用戶原話:「All should auto follow… The system should be no human involvement at the end」)。
  7. 畫面定案五個:策略總覽、策略詳情、運行詳情(組合層結果:淨值對基準/持倉變化/逐筆交易;頁頂帶留痕摘要)、個股蠟燭圖連因子檢視(逐日因子分數與入選狀態;擺位留原型驗證)、參數掃描(穩健平原熱力圖)。運行留痕不設獨立畫面,但每次運行照蓋版本×參數×期間×數據快照(KARST-006 結果不變)。
  8. 指標兩層制:策略卡精簡四項(累計回報對基準、年化回報、最大回撤、勝率盈虧比);運行詳情加年化超額、Sortino、平均持倉日數、換手。基準照 D-010 用 QQQ 與 SPY。

- **用戶原話（原文照錄）**

  > All I care is the governance and ensure the same kit applies for all strategy and backtesting. Then what is the approach?

  > I think all should auto follow. As my decision is not needed to capture in this system. The system should be no human involvement at the end

  > 運行留痕 is not needed seems

  > I think 年化 is the key. Alpha, Sortino are needed as well? Average holding period?

  > Can have prototype to validate?

- 影響：KARST-007 收檔;KARST-015 原型即可開工(五畫面砌核心三個+因子檢視兩變體);KARST-008 規格照此成文;唯一入口是日後建置 Epic 的第一等公民。

## D-021 因子合約:形態、刻度、時點、缺失、有效期、產生程序、中性化、追溯、版本
- 類型：決策
- 狀態：有效
- 日期：2026-08-26

- 出處：KARST-003 grilling,用戶 2026-08-26 三輪原生選項介面裁決,末條「ok go with your suggestion」

- 決策：
  1. 形態:一個因子=一張「日期 × 股票 → 一個數值」的表(業界共識,KARST-002),配同形狀的未來回報表作評估;只管選股訊號(D-013)。
  2. 刻度:每個因子登記自己的刻度型(基數/序數/是非 0-1);多因子合成時一律先轉當日橫斷面百分位排名再加權(市場標準:Barra/AQR/qlib/alphalens 的橫斷面標準化)。
  3. 時點:每個值帶兩個時間戳——事件時間與知情時間(D-017);一切查詢以知情時間為閘。可執行時點寫死於合約、策略不得繞過:「知情時點之後的下一根可交易 K 線的開價」——綁 K 線不綁時鐘(用戶提出美股 2026-12 起近 23 小時交易);v1 只當常規時段 K 線可交易,延長時段待數據含入才自動延伸。
  4. 缺失值=該股該日不參與該因子的篩選與排名;不填補、不當零。
  5. 稀疏與混頻:因子值永久有效直至被同因子的新值取代,不設有效期(用戶揀此案,明知兩年前判斷會一直生效——由策略層自理);每個交易日按知情時間取最新已知值對齊日曆。
  6. 公式派與數值派一份合約:兩者同落一張表,合約多一格「產生程序」——公式因子填公式+輸入數據版本,數值因子填材料+判官版本。
  7. 中性化(剔行業/市值)是合成時的參數,庫存原值;無預設。
  8. 追溯深度:公式因子記到批次(因子版本 × 數據快照 × 產生程序版本,可一字不差重算);由文字材料判出的因子逐筆指回材料段落與判官理由。
  9. 版本:因子定義一經落庫不可改、只可出新版,每版有父版本(git 式,與策略版本同制,用戶 2026-08-26 於原型階段裁「版本 is key…trail like git」);運行記錄蓋齊所用因子版本,舊運行永不自動更新,只標過時(D-020 補充)。
  10. 與 KARST-002 調研的採納/偏離:採納「日期×股票」形態、雙時間戳、橫斷面標準化、Vibe-Trading AlphaCompute 的三條紀律(NaN 必須傳遞、禁 ±inf、禁前視);偏離:不設有效期(feature store 慣例有 TTL)、版本與產生程序掛在因子本身而非實驗(qlib Recorder/MLflow 掛實驗,D-002 單一定義不容)。

- **用戶原話（原文照錄）**

  > What is the market standard?

  > So to me, there are no effective or cutoff date

  > Want to discuss further. As US Stock Market in Dec this year will have 23 hours of trading

  > ok go with your suggestion

- 影響：KARST-003 收檔;KARST-004 解鎖(轉換合約輸出對齊本合約);KARST-008 規格照此成文;唯一入口(D-020)負責執行本合約的登記與驗證。

## D-022 技能三層次與人物判官:複製判斷而非機制;可量化者先量化;SA 改為答案紙
- 類型：決策
- 狀態：有效
- 日期：2026-08-27

- 出處：用戶 2026-08-27 兩則訊息:整理「to Skill」終點,並確認框架

- 決策：
  1. 「技能」分三層:A 機械規則(直接入引擎)、B 半機械(缺門檻,掃描補或降級)、C 判斷(投資者的思考方式本身)。Video/Portfolio to Skill 的終點是 C 層——複製投資者的判斷,不是抄機制;能量化的部分一律先量化(用戶原話:「if quantifiable then quant it」)。
  2. C 層由「人物判官」承載:由該投資者的材料筆記建成人設的 agent,輸入為知情時間把關下某時點之前的公開資訊,輸出為對範圍內股票的判斷(0/1 或分數)。人物判官是因子合約(D-021)數值派因子的一種,產生程序=材料+人設版本;登記、版本、追溯、合成全部照合約,不另立制度。
  3. 判官的學習=對照答案紙:以該投資者實際持倉歷史(13F 一類)為對照,判官逐期出決定→比對真實持倉→修人設→出新版本。組合倒推(KARST-012)與人物判官是同一件事的兩面。
  4. 成本控制原則:量化因子先粗篩、判官只細判剩餘候選;判斷按材料事件觸發而非按日重算(值永久有效直至被取代,D-021);同一(材料版本×人設版本)結果快取;判官結果反過來用作標籤,尋找可複製其決定的廉價代理因子,達標即以代理取代判官(B→A 升級)。
  5. SA(Situational Awareness)定位改寫:其公開倉位 2026-07-30 售予 Citadel(KARST-016),不再是可現場跟隨的組合;改為人物判官的答案紙(2025–2026H1 持倉歷史)與訓練樣本,SA 判官日後可替其繼續出決定。Pelosi 照舊為現場跟隨籃子。D-017 相應修訂。
  6. 人物判官令 A-002(LLM 訓練截止日污染)由「留意」升為「必須先解」:回測期須用截止日早於該期的模型或只做前向驗證;此為人物判官合約票(KARST-017)必答項。

- **用戶原話（原文照錄）**

  > Actually I would like to mimic the investment decision (not exactly mechanism as always these approach iis not mechanical...) so it should be kind of a bot which can be learning the investment approach

  > Yes, and if quantifiable then quant it.

  > whether this skill judge result can be a quant factor? But this will be expensive?

- 影響：開 KARST-017 人物判官合約(grilling,依賴 KARST-004);D-017 SA 一項修訂;KARST-012 與 017 合流;KARST-008 規格加技能三層次一節。

## D-023 畫面不再是阻塞項:原型第十版定為 v1 基線,日後可改;優先次序轉向策略表現
- 類型：決策
- 狀態：部分已取代（見 D-035）
- 日期：2026-08-27

- 出處：用戶 2026-08-27 原話

- 決策：
  1. 應用畫面以 KARST-015 原型第十版為 v1 基線(策略總覽、策略詳情、運行詳情、參數掃描四頁),未裁的小項(漏斗篩選語意、圖下留白)按現狀落檔,不再逐項等用戶拍板;任何畫面決定日後皆可重開,不算推翻。
  2. 投資項目的核心是策略表現。往後的地圖次序以「引擎跑起、策略出成績」為先,畫面打磨排在其後;需要用戶在場的時間優先用於需求裁決(材料轉因子、人物判官合約)而非畫面細節。
  3. 設計系統文件由原型第十版抽出成正本(design-system.md),作為實作依據;原型本身封存於 prototype/。

- **用戶原話（原文照錄）**

  > actually if i don't frustrate on the screen decide, we can always revisit later? I think an investment project the key is performance?

- 影響：KARST-015 以第十版收版關檔;design-system.md 誕生;KARST-008 規格整理只剩 KARST-004 一項前置;地圖後續排序以引擎與策略成績為先。

## D-024 材料轉因子通用合約:公開可得時間、入庫值即正本、三族共用登記時點追溯、兩道強制防禦、判準書五步流程、規則不受時點限制、逐份存原層策略層合併
- 類型：決策
- 狀態：有效
- 日期：2026-08-27

- 出處：用戶 2026-08-27 於 KARST-004 追問三輪的原生選項回答(原話見引文)

- 決策：
  1. 材料知情時間=公開可得時間(影片上載日、13F 申報日、書籍出版日),不用內容所指時間,不由材料逐份自報。
  2. 可重現性:入庫值即正本,不重判;同一材料同一判準同一模型再判屬新版本因子;另以抽樣重判量度穩定度,只作判準質素指標,不作改值依據。
  3. 轉換合約三族(影片字幕、書籍、持倉披露)通用的是登記凍結、知情時間、追溯三條;判準書與判官只適用於文字材料,持倉披露直接以公式產生因子。
  4. 兩道防禦列為唯一入口強制閘:(一)每個分數必須指回材料內逐字存在的段落,機器核對,對不上=缺失;(二)每版判準附固定樣本集,判準或模型一改即重評,偏離超門檻擋住不准入庫。舊項目兩宗事故(判官標準漂移、外判捏造證據)由此逐條回應。
  5. 判準書必須成文並有版本;生效流程五步:agent 草擬 → 子 agent 試判 → agent 覆核並附表現測試 → 用戶批准 → 鎖版生效。判官鎖版:每個分數記錄模型、判準版本、提示版本,任何一項變即新版本因子,不覆蓋舊值。
  6. 由材料抽出的規則(技能 A/B 層)不受知情時間限制,只有材料內關於個股的事實與見解受限;規則在出版前區間的回測成績報告須標明「事後看」。
  7. 材料不可變:修正(字幕錯字、更佳逐字稿、上載者改片)=同一材料新版本,知情時間不變,舊分數保留可追。
  8. 同日多份材料對同一股票各自出分:逐份分數連來源存原層;合併法(平均/最新/最高/計數一類)是策略取用因子時的必填參數,不設預設,可掃描——與中性化同屬合成參數。
  9. 來源等級(第一身/官方/第三方)不列入本合約通用欄位:逐字稿與分析員報告來源已清楚;KOL 影片與第三方轉述的分級歸人物判官合約(KARST-017)處理。模型已知結局(A-002)的取捨同歸 KARST-017(D-022)。

- **用戶原話（原文照錄）**

  > Agent 草擬, subagent testing, agent review with performance test, me approve

  > I don't know, need more scenarios from you to consider

  > This question is about Video to Skill?

- 影響：KARST-004 關檔;KARST-008 規格整理前置全部完成;KARST-017 加收來源等級與 A-002 取捨兩項;詞彙表加判準書、材料庫、合併法。

## D-025 v1 規格核准開工;建置次序引擎先行、趨勢波段首出成績;數據免費源先行(defeatbeta+yfinance)另議架構;畫面以四頁為準、個股頁屬額外
- 類型：決策
- 狀態：有效
- 日期：2026-08-27

- 出處：用戶 2026-08-27 於原生選項介面四題回答(原話見引文)

- 決策：
  1. docs/karst-v1-spec.md 核准為開工依據;缺口清單照列不補裁,逐項在建置期補。地圖「V1 藍圖」到達目的地(D-001)。
  2. 第一批建置次序照規格第 11 節草案:引擎(單一定義庫、唯一入口、適配層 A/B、共用風控層、運行留痕)→ 接真實行情 → 趨勢波段策略首先出成績 → 參數掃描 → 因子混合 ETF 版 → 本機網頁殼。樽頸策略排第二批(先要材料庫與判準書)。
  3. 行情與基本面數據以免費來源先行:defeatbeta(基本面、逐字稿、價格)+ yfinance;日後可加其他免費來源。儲存與整合方式(是否沿用 defeatbeta 的 duckdb、快照如何版本化)另開需求票討論,先查 KarstETF 舊倉的用法。付費含退市股來源不在 v1 起步範圍;回測成績報告須標明存活者偏差風險。
  4. 應用畫面以四頁為準(策略總覽、策略詳情、運行詳情、參數掃描),個股蠟燭圖連因子檢視住在運行詳情頁;獨立個股頁屬額外資訊查看功能,不在回測主線,日後有餘力再加。D-020 第 7 條「五個畫面」據此修訂。

- **用戶原話（原文照錄）**

  > I think defeatbeta + yfinance for the fundmentals, transcripts, stock prices or those candal sticks? You can check the KarstETF. And Actually I would like to introduce other free sourcee later consider what we should do. I mean even defeatbeta, we may not use duckdb. Seems we may need a discussion on the architecture when you have a look on this?

  > I think have individual page is ok for information checking as well. But it is not really for backtesting. Bouns only

- 影響：開建置交付品與第一批實作票;開數據架構需求票(前置:KarstETF defeatbeta 用法事實);D-020 狀態改部分已取代;規格 10.7 缺口關閉。

## D-026 數據架構:parquet 快照+sqlite 登記、實體編號主鍵連代號歷史映射、每次拉數一個快照編號、只存已調整價、單一管線單一快取根
- 類型：決策
- 狀態：部分已取代（見 D-028）
- 日期：2026-08-27

- 出處：用戶 2026-08-27 於 KARST-020 原生選項回答(原話見引文);儲存形態與主鍵兩項用戶交由按性能與擴展性建議,採本條建議

- 決策：
  1. 儲存形態:行情、基本面、逐字稿等數據照批次存 parquet(欄式、可分區、不可變、pandas/vectorbt 直接讀);因子定義、策略、運行登記、實體代號映射存單一 sqlite 檔(單一定義庫)。日後查詢量大再加 duckdb 作 parquet 的讀層,不改存法。理由:parquet 是單機可擴展到億級列的標準欄式格式,sqlite 零伺服器、備份=複製檔;兩者皆不鎖死於任何一個數據源套件。用戶原話:「What is the best approach in terms of performance and scalability?」——按此推出。
  2. 實體主鍵:每個可投資對象一個不變的內部實體編號(上市公司以 SEC CIK 為錨,ETF 與籃子另編),交易代號只是有生效期的屬性,以映射表(實體編號、代號、生效起訖)維護;價格、因子、逐字稿全部掛在實體編號上,入庫時按日期把代號解析成實體。回應 KarstETF GOLD 代號回收事故(舊倉交接書明文要求)。用戶原話:「內部編號 need a mapping with ticket then?」——是,映射表即此。
  3. 數據快照:每次拉數=一個新快照編號(日期+內容雜湊),舊快照不動;運行引用快照編號,同一編號重算一字不差。清理規則日後再定。
  4. 價格形態:照舊倉只存 yfinance 已調整價(auto_adjust),不自建除權除息表。後果明記:每次派息後整條歷史會變,故不同快照之間價格不可直接比較,一律靠快照編號;蠟燭圖顯示的是調整價不是當日真實成交價。
  5. 分工:價格與日曆由 yfinance;基本面與業績電話會逐字稿由 defeatbeta;兩者重疊時價格以 yfinance 為準、財務以 defeatbeta 為準。全倉只有一條抓取管線、一個快取根目錄,同一實體同一數據只有一份(單一定義),寫入原子化——杜絕舊倉五套管線五個快取「先撞先贏」的第二影像。
  6. 存活者偏差:免費來源不含退市股。自即日起每次快照連同當時的宇宙名單一併凍結,前向累積自家的宇宙歷史;在此之前的回測期一律在成績報告標明「未含退市股」。付費含退市股來源留待日後。
  7. 日後加其他免費來源:每個來源一個適配器,輸出同一套 parquet 欄位與實體編號,經同一條管線入快照;來源名記在快照內。

- **用戶原話（原文照錄）**

  > What is the best approach in terms of performance and scalability?

  > I don't know. 內部編號 need a mapping with ticket then?

  > 照舊倉只存已調整價

- 影響：KARST-020 關檔;KARST-027 行情數據接入票範圍據此定稿(可開工);KARST-021 單一定義庫要加實體代號映射表;詞彙表加實體編號、數據快照。

## D-027 數據庫本機先行(sqlite+parquet);雲端與否於紙上交易上線時一併決定;兩條護欄守住換庫成本
- 類型：決策
- 狀態：有效
- 日期：2026-08-27

- 出處：用戶 2026-08-27 提問「should I use Online DB from dayone? or you think it can be just later?」,並於我建議後答「Ok」

- 決策：
  1. v1 建置期數據庫留在本機:sqlite 存定義與登記、parquet 存數據快照(D-026)。不在第一日上雲數據庫。
  2. 「在互聯網上看到」由網頁殼加安全隧道(Tailscale / Cloudflare Tunnel 一類)解決,不需改庫;雲數據庫要解決的是多機寫入或引擎在雲上跑,v1 無此需要。
  3. 換庫時機=紙上交易上線:全自動入帳需要一部長開的機,屆時一次過決定長開機是本地還是雲上;若雲上,sqlite 換 Postgres、parquet 換對象儲存、網頁殼同時上網,一次決定不分兩次。
  4. 兩條護欄自即日起為驗收條件:(一)只用 sqlite 與 Postgres 皆通用的 SQL(trigger、外鍵、索引通用;不用 sqlite 專有語法);(二)任何模組不得直接開 sqlite 連線,一律經單一定義庫 API(karst/store.py)。

- **用戶原話（原文照錄）**

  > Actually if we use SQLite then actually for the update I won't be able to see from the internet? I mean should I use Online DB from dayone? or you think it can be just later?

  > Ok

- 影響：KARST-021/022 已落地部分要覆核護欄(一);後續建置票驗收加護欄兩條;紙上交易排程票開票時必答長開機去向。

## D-028 數據快照去重:凍結前歸一化到 7 位有效數字,並以等價重用取代「每次拉數=新編號」
- 類型：決策
- 狀態：有效
- 日期：2026-08-28

- 出處：用戶 2026-08-28 裁決,原話「yes normalize it. no duplicated copy」;KARST-033 查證

- 決策：
  1. 凍結快照前,價格一律捨入到 7 位有效數字(來源已調整價本身只有 float32 精度,第 8 位起每次抓回都不同);規則寫入快照說明檔,是數據定義的一部分。
  2. 單靠捨入吸收不了飄移(要捨到 3 位才吸收得到,數據即廢),故加第二層「等價重用」:凍結前先查快取根有沒有同窗口、同宇宙、同規矩而價格相對差不過 1e-5 的已凍結快照,有就沿用原編號原檔案,不另存副本。
  3. D-026 第 3 條「每次拉數一個新快照編號」據此修訂為「每次拉數得一個編號;與既有快照等價則沿用原編號」。副作用明記:沿用時抓取日仍是原本那日。
  4. 容差寧緊莫鬆:小過該股價 0.001% 的真更動會被當作噪音維持舊快照;這是刻意取捨。

- **用戶原話（原文照錄）**

  > yes normalize it. no duplicated copy

- 影響：KARST-027 既有快照 61e284eaa998 原封不動仍驗得過;KARST-034 快照命令列沿用兩層做法。

## D-029 掃描的呈現三層(清單→熱力圖→單格)與因子混合策略的參數是驅動器設定
- 類型：決策
- 狀態：有效
- 日期：2026-08-28

- 出處：用戶 2026-08-28 對運行詳情頁與掃描的追問

- 背景：用戶見運行選單列出掃描格運行的編號,追問三千多格是否蒙地卡羅、是否只該顯示最佳結果;並重申因子混合不是固定比例。

- 決策：(1) 一次掃描當一件事,畫面分三層:掃描清單(一次一行:策略、幾格、裁決、代表格成績)→ 點進去預設顯示熱力圖,標出最佳格與代表格兩個標記 → 點格才開該格單次運行的曲線;掃描格運行不入運行清單。不可只顯示最佳格。(2) 因子混合策略的參數是驅動器設定(訊號、回望期、換倉節奏、退路),四隻 ETF 的比例是每個換倉日由驅動器算出的輸出,不是參數;固定比例掃描只作對照,在掃描清單標明「對照」。

- 考慮過的替代方案：每格一張圖(用戶否定:「non-sense to breakdown to 3000+ chart」);只顯示最佳格(否定:孤峰誤導);點進去先見代表格曲線(用戶未選)。

- 為何選這個：掃描的意義是地形不是個別結果;只看最佳格等於看 3,542 分之 1 的幸運兒。比例由訊號決定是用戶一貫裁定(見因子輪動相關裁決)。

- **用戶原話（原文照錄）**

  > But then it is non-sense to breakdown to 3000+ chart for every 1 run then. … the parameter here shouldn't be the fixed % of the 4 etf. It should be the parameter of the strategy to decide the proportion of the 4 etf? as it is not a fixed portion?

- 影響：KARST-049/050/051/053 據此實作;參數掃描頁、策略詳情頁的參數區、運行清單三處。

## D-030 成績口徑:基準情境不計交易成本;存活者偏差暫不處理;成交時點沿 D-021 第 3 條
- 類型：決策
- 狀態：有效
- 日期：2026-08-28

- 出處：用戶 2026-08-28 過目 KARST-D02 交付摘要「假設」一節

- 背景：用戶指自己不是日內交易者,月度/季度換倉的成本不足以左右結論;存活者偏差留待日後。

- 決策：(1) 成績的基準情境不計交易成本(手續費與滑點皆為零);既有的成本敏感度掃描保留作對照,不作主報。(2) 存活者偏差暫不量化、暫不列為簽核阻礙。(3) 成交時點與價格照 D-021 第 3 條:訊號在收市成形,下一根可交易 K 線的開價成交;交付摘要假設一節要明寫此條。

- 考慮過的替代方案：維持估計成本(每股 US$0.005 + 5 個基點)作主報——用戶否決;按券商校準成本——未選。

- 為何選這個：用戶按自身交易形態裁定;成本情境仍保留,日後要校準只是換一格參數。

- **用戶原話（原文照錄）**

  > 交易成本是估計值(每股 US$0.005 + 5 個基點滑點) <<< Can actually assume no as I am not day trader;存活者偏差那條 <<< Can ignore for now;成交時點與價格……這條要寫明用的是哪一種 OK

- 影響：KARST-D02 交付摘要假設一節改寫;KARST-057 重建時主報數字用零成本情境;成本情境降為對照。

## D-031 ETF 流動性只看日均成交金額;因子 ETF 維持 MSCI 套(MTUM 等),SPMO 不加對照
- 類型：決策
- 狀態：有效
- 日期：2026-08-28

- 出處：用戶 2026-08-28

- 背景：用戶追問 MTUM 與 SPMO 近五年流動性;查回成交金額 MTUM 一直較高但差距急速收窄。

- 決策：揀 ETF 時流動性判準只用日均成交金額(收市價 × 成交量),不看資產規模、不看組合換手率。按此 MTUM 成交金額仍高於 SPMO,因子 ETF 維持 MSCI 四隻;SPMO 暫不加作對照臂。

- 考慮過的替代方案：兼看資產規模(未選);加 SPMO 作對照臂重掃(未選)。

- 為何選這個：用戶按實盤進出考慮,成交金額直接決定滑點與可成交量。

- **用戶原話（原文照錄）**

  > I see. I think can just based on 成交金額.

- 影響：日後任何 ETF 候選(含 KARST-058 以後的宇宙擴充)以成交金額排序;研究檔 research/2026-08-28-mtum-spmo-aum-volume-5y.md 為依據。

## D-032 因子值改存壓縮檔案(Parquet,按快照 × 因子版本一批一檔),定義庫只留登記與雜湊;不再逐值入 sqlite
- 類型：決策
- 狀態：有效
- 日期：2026-08-29

- 出處：用戶 2026-08-29

- 背景：KARST-064 以十二隻入庫 Alpha158 後定義庫由 40 MB 漲到 1.6 GB(每值近 300 字節),標普 500 外推約 65 GB,備份、核對與網頁殼讀取都不可用。

- 決策：因子值(factor_value)不再逐行存入定義庫;改為按「數據快照 × 因子版本(或因子庫批次)」一批一個 Parquet 檔,放運行/快照同一套數據目錄,定義庫的因子表只保留登記(因子、因子版本、產生程序版本、快照編號、檔案路徑、內容雜湊、行數),全庫核對照管雜湊。D-021 的三個時點與 D-022 的表結構語義不變,只是承載體由表改為檔。

- 考慮過的替代方案：留在 sqlite 壓縮欄位(約 9 GB,未選);暫不擴容只在十二隻上用(未選);先放下 Alpha158(未選)。

- 為何選這個：值本身只需 4–8 字節,逐行帶時點入表是十倍以上的膨脹;運行淨值與選股痕跡已用檔案加雜湊的做法,核對機制現成。

- **用戶原話（原文照錄）**

  > Oh my god. it is not ok seems. What is your advise to me? … 照建議:還原庫、開票改存壓縮檔案

- 影響：KARST-064 的入庫路徑要改寫(KARST-068);KARST-066 預測力面板按檔案形狀讀取;A-010 由此取代。現有 1.6 GB 庫內的 Alpha158 值遷出後庫回到約 40 MB。

## D-033 因子線只保留八類:反轉、反轉減弱、成交量與波幅異常、動量、相對強弱、月度基本面量化、行業量化、估值模型(DCF 一類)量化;日線技術統計單條訊號(Alpha158/101 Alphas)不再追
- 類型：決策
- 狀態：有效
- 日期：2026-08-29

- 出處：用戶 2026-08-29

- 背景：Alpha158 在標普 500 實測 158 條無一達 |IC| 0.02;用戶判斷純價格技術統計預測不到未來,但對學術界有機構級證據的經典效應與基本面 / 行業 / 估值量化仍感興趣。

- 決策：Karst 因子線的範圍收窄為八類,以此排工:(1) 短期反轉(周度);(2) 反轉減弱(月度轉折);(3) 成交量異常與波幅異常(月度);(4) 動量(3–12 個月);(5) 相對強弱;(6) 月度基本面量化因子;(7) 行業量化(行業層面的訊號與輪動);(8) 估值模型(DCF 一類定價模型)量化。前五類純價量、現有數據可算;後三類要財務報表 / 行業分類 / 估值輸入數據線。Alpha158 已算好的批次保留作原料與過濾器,不再逐條追單因子訊號;WorldQuant 101 Alphas 不排。

- 考慮過的替代方案：續加 101 Alphas(未選);先做小型股 / ETF 實測(擱置);多因子合成層(未裁)。

- 為何選這個：用戶要的是有幾十年機構級證據、月度節奏、橫斷面組合的效應,以及基本面與估值驅動的量化,不是逐日技術統計。

- **用戶原話（原文照錄）**

  > So in short 1. 反轉 2. 反轉減弱 3. 成交量異常與波幅異常接手 4. 動量 5. Relative Strength 6. 月度訊號 Fundamentals based Quant 7. Industry based Quant. 8. DCF or related Pricing Model based Quant are what I am interested <<< I just want to keep these

- 影響：KARST-075(OSAP 調研)以前五類為先算清單;基本面、行業分類、估值數據源各要另開調研票;小型股 / 行業 ETF / 因子 ETF 實測按八類需要再排;預測力面板首輪窗口改為月度為主(21、63、126 日)連原有 1、5 日。

## D-034 跑輸 SPY 與 QQQ 兩者的運行視為失敗運行,畫面預設不顯示;運行本身照留庫、照核對
- 類型：決策
- 狀態：有效
- 日期：2026-08-29

- 出處：用戶 2026-08-29

- 背景：用戶看策略頁時指出跑輸兩個基準的運行沒有價值,不應佔畫面。

- 決策：一次正式運行若在同一期間的年化回報同時低於 SPY 買入持有與 QQQ 買入持有,即為「失敗運行」:策略總覽、策略詳情的歷次運行表、運行選擇器預設不列出;只留一行「另有 N 條失敗運行」可展開。運行登記、留痕、全庫核對照舊,不刪不改。掃描格運行不在此限(掃描頁本來就要看全部格)。

- 考慮過的替代方案：只跑輸其一即隱藏(未選);以夏普或超額判定(未選,見假設);全部照列加標記(未選)。

- 為何選這個：用戶原話:「for run in which the performance is not better than both SPY and QQQ. it is not need to show in the screen as they are failed.」判準用年化回報是主 agent 依這句推出(畫面門面成績本來就以年化回報為首),用戶未指明指標;若用戶日後改以超額或風險調整判定,只換判準函數。

- **用戶原話（原文照錄）**

  > for run in which the performance is not better than both SPY and QQQ. it is not need to show in the screen as they are failed.

- 影響：網頁殼三處清單加過濾與展開行(KARST-077);「失敗運行」入詞彙表;示例運行若跑輸兩者會從門面消失,D02 摘要仍引用它們(摘要是歷史記錄,不改)。

## D-035 運行詳情不是頂層頁面,是策略詳情的鑽取層;頂層導覽改為策略總覽 / 策略詳情 / 參數掃描三頁(部分取代 D-023 的四頁基線)
- 類型：決策
- 狀態：部分已取代（見 D-036）
- 日期：2026-08-29

- 出處：用戶 2026-08-29

- 背景：用戶指出運行詳情本質是策略詳情的下鑽,不應與策略並列。

- 決策：運行詳情由頂層導覽移除,只能從策略詳情的歷次運行表(或運行選擇器)點入;運行詳情頁頂顯示「策略詳情 › 運行」麵包屑可回上層,網址保留 ?id=&run= 以便直連。頂層導覽為策略總覽、策略詳情、參數掃描三頁;日後新增頂層頁(例如因子預測力)另裁。

- 考慮過的替代方案：運行詳情嵌入策略詳情頁同一畫面展開(未選,主圖與右欄三分頁擠不下);維持四頁(未選)。

- 為何選這個：用戶原話:「運行詳情 is not a sepearate page actually. It should be the drill down of the 策略詳情」;鑽取層用獨立網址 + 麵包屑是主 agent 依這句推出的最小改動,不重排運行頁內部。

- **用戶原話（原文照錄）**

  > 運行詳情 is not a sepearate page actually. It should be the drill down of the 策略詳情

- 影響：網頁殼導覽與運行頁頂改動(KARST-078);D-023 四頁基線部分取代;KARST-066 面板版式問題的前提改變(變體 B 的「第五頁」變「第四頁」)。

## D-036 策略詳情改為一頁四段(門面成績 → 熱力圖帶 → 正式運行表 → 選股漏斗);參數掃描降為熱力圖的下鑽層;頂層導覽只剩策略總覽與策略詳情兩頁(部分取代 D-035)
- 類型：決策
- 狀態：有效
- 日期：2026-08-29

- 出處：用戶 2026-08-29

- 背景：用戶問策略詳情為何仍是逐行而非熱力圖帶,並指出運行選擇器在幾千個運行下無用;主 agent 說明 D-029 把熱力圖建在參數掃描頁,提出改法,用戶選「是,照這個改」。

- 決策：策略詳情頁結構定為四段:(1) 門面成績與參數區;(2) 熱力圖帶——該策略每個掃描一條帶,標最佳格與代表格(D-029 三層照舊,只是第二層搬到策略頁);(3) 正式運行表(照 D-034 隱藏失敗運行);(4) 選股漏斗。點熱力圖某格下鑽到單格曲線(現參數掃描頁的第三層),點運行表某行下鑽到運行詳情(D-035)。頂層導覽只剩策略總覽、策略詳情;參數掃描與運行詳情都是下鑽層,保留直連網址。運行詳情頁的運行選擇器移除。

- 考慮過的替代方案：熱力圖帶加入策略詳情但參數掃描保留頂層(未選);維持現狀(未選)。

- 為何選這個：用戶原話:「I remember you said the 策略詳情 should be a heatmap band? Why it is still line by line?」及「檢視運行 bar is not useful again if I have thousands of run for this strategy」;一頁四段與兩頁導覽是主 agent 依這兩句提出、用戶選定。

- **用戶原話（原文照錄）**

  > Also I remember you said the 策略詳情 should be a heatmap band? Why it is still line by line? / 是,照這個改

- 影響：網頁殼策略頁重組、導覽改兩項(KARST-079,接 KARST-078 之後做);D-035 的「三頁」部分取代;KARST-066 面板版式問題前提再變(頂層只有兩頁)。

## D-037 歷次運行表改為排名表(年化、Sortino、最大回撤、勝率可排序,拿走快照與參數兩欄);「因子分布」改為「持股分布」(點運行行即換,列最常持有前十股票、各股在該次運行內的累計報酬、行業佔比);因子敞口搬去運行詳情
- 類型：決策
- 狀態：有效
- 日期：2026-08-29

- 出處：用戶 2026-08-29

- 背景：用戶指出策略詳情是該策略的總覽、歷次運行是逐次;引入自建量化因子後運行會數以千計,必須有排名;快照與參數在表上不需要;「因子分布」實際應是股票分布,並與歷次運行配對;隨後補充要顯示各股在該次運行內的累計報酬。再補充:策略頁的「檢視中」區塊(該次運行的參數清單、運行編號、快照、視窗)不必顯示(原話「Is not need to show in the strategy page」),這些資料只在運行詳情顯示。

- 決策：策略詳情頁的歷次運行表:(1) 欄位為運行編號、版本、年化、Sortino、最大回撤、勝率(旁附交易次數),四個成績欄可點欄頭排序,預設按年化由高至低;快照、參數兩欄拿走(在運行詳情才看);(2) 幾千條時只列前 50,底下「載入更多」;失敗運行照 D-034 預設隱藏。「因子分布」一段改為「持股分布」:與歷次運行配對,點運行表某一行即換成該次運行的持股分布——最常持有的前十隻股票、每隻在該次運行內的累計報酬、行業佔比;因子敞口與因子版本搬到運行詳情頁。策略頁次序因此為:門面成績 → 熱力圖帶 → 歷次運行(排名)+ 持股分布 → 選股漏斗(補充 D-036)。

- 考慮過的替代方案：預設按 Sortino 排序(未選);勝率換成交易次數一欄(未選);持股分布與因子分布並列(未選);持股分布不含行業佔比(未選)。

- 為何選這個：用戶原話:「when we are getting thousands of run later … you need to have ranking on the run for 年化, Sortino, 最大回撤, 勝率」「快照, 參數 is not needed」「因子分布 is actually the Stock 分布 but not 因子 … can be paired up with the 歷次運行」「should the 累計報酬 of the Stock in the run as well」;勝率附交易次數、前 50 分頁、因子搬去運行詳情是主 agent 提出、用戶選「照這樣做」。

- **用戶原話（原文照錄）**

  > you need to have ranking on the run for 年化, Sortino, 最大回撤, 勝率?? / 快照, 參數 is not needed. And I think 因子分布 is actually thhe Stock 分布 but not 因子??? This can be paired up with the 歷次運行 / 因子分布 for the Stock can should the 累計報酬 of the Stock in the run as well

- 影響：策略頁運行表與持股分布段重做、運行詳情頁加因子段(KARST-080,接 KARST-079);後端要有每次運行的持股彙總與每股累計報酬 API。
