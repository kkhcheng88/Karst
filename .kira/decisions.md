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
- 狀態：部分已取代（見 D-028、D-041）
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
- 狀態：部分已取代（見 D-042）
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
- 狀態：部分已取代（見 D-040）
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
- 狀態：已取代（見 D-042）
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
- 狀態：已取代（見 D-042）
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
- 狀態：部分已取代（見 D-042）
- 日期：2026-08-29

- 出處：用戶 2026-08-29

- 背景：用戶指出策略詳情是該策略的總覽、歷次運行是逐次;引入自建量化因子後運行會數以千計,必須有排名;快照與參數在表上不需要;「因子分布」實際應是股票分布,並與歷次運行配對;隨後補充要顯示各股在該次運行內的累計報酬。再補充:策略頁的「檢視中」區塊(該次運行的參數清單、運行編號、快照、視窗)不必顯示(原話「Is not need to show in the strategy page」),這些資料只在運行詳情顯示。

- 決策：策略詳情頁的歷次運行表:(1) 欄位為運行編號、版本、年化、Sortino、最大回撤、勝率(旁附交易次數),四個成績欄可點欄頭排序,預設按年化由高至低;快照、參數兩欄拿走(在運行詳情才看);(2) 幾千條時只列前 50,底下「載入更多」;失敗運行照 D-034 預設隱藏。「因子分布」一段改為「持股分布」:與歷次運行配對,點運行表某一行即換成該次運行的持股分布——最常持有的前十隻股票、每隻在該次運行內的累計報酬、行業佔比;因子敞口與因子版本搬到運行詳情頁。策略頁次序因此為:門面成績 → 熱力圖帶 → 歷次運行(排名)+ 持股分布 → 選股漏斗(補充 D-036)。

- 考慮過的替代方案：預設按 Sortino 排序(未選);勝率換成交易次數一欄(未選);持股分布與因子分布並列(未選);持股分布不含行業佔比(未選)。

- 為何選這個：用戶原話:「when we are getting thousands of run later … you need to have ranking on the run for 年化, Sortino, 最大回撤, 勝率」「快照, 參數 is not needed」「因子分布 is actually the Stock 分布 but not 因子 … can be paired up with the 歷次運行」「should the 累計報酬 of the Stock in the run as well」;勝率附交易次數、前 50 分頁、因子搬去運行詳情是主 agent 提出、用戶選「照這樣做」。

- **用戶原話（原文照錄）**

  > you need to have ranking on the run for 年化, Sortino, 最大回撤, 勝率?? / 快照, 參數 is not needed. And I think 因子分布 is actually thhe Stock 分布 but not 因子??? This can be paired up with the 歷次運行 / 因子分布 for the Stock can should the 累計報酬 of the Stock in the run as well

- 影響：策略頁運行表與持股分布段重做、運行詳情頁加因子段(KARST-080,接 KARST-079);後端要有每次運行的持股彙總與每股累計報酬 API。

## D-038 策略參數取值逐條策略在建置期與用戶對齊;現有「示例」參數集(如示例-KARST-028)只是通鏈用的示例值,未經用戶對齊,不視為現役設定
- 類型：決策
- 狀態：有效
- 日期：2026-08-29

- 出處：用戶 2026-08-29

- 背景：用戶見策略頁列出示例-KARST-028 的參數清單,指出「most of these parameter you havn't aligned with me yet」並問是否 vectorbt 的結果;主 agent 說明 vectorbt 只是引擎、取值是代理揀的示例值,提出現在對齊或留到建置期兩個選項,用戶選「留到建置期」。

- 決策：每條策略(波段 1–5、基本面 6–8)開工建置時,固定有一步與用戶對齊參數:哪幾個旋鈕、每個掃描範圍、代表格如何揀;對齊結果落在該策略的建置票。趨勢波段現有示例值(突破回望 59 日、單筆風險 2%、月度熔斷 6%、賠率門檻 1.5、單一持倉上限 25% 等)留到建置期才對齊,現在不另開對齊票。示例參數集不是現役設定,畫面與紀錄須能分辨。

- 考慮過的替代方案：現在開一張趨勢波段參數對齊討論票(未選)。

- 為何選這個：用戶原話:「留到建置期」。

- **用戶原話（原文照錄）**

  > but most of these parameter you havn't aligned with me yet. And actually I think these are the result of vectorbt? / 留到建置期

- 影響：日後每張策略建置票的工作內容必含「參數對齊」一節;示例運行的成績只證明鏈通,不代表策略優劣。

## D-039 策略總覽的欄位與策略詳情運行排名表對齊(年化、Sortino、最大回撤、勝率附交易次數),每行數字即該策略在策略詳情預設顯示的那次運行;拿走迷你走勢欄;所有頁面底部說明列拿走
- 類型：決策
- 狀態：部分已取代（見 D-042）
- 日期：2026-08-29

- 出處：用戶 2026-08-29

- 背景：用戶在 D-037 之後指出策略總覽也要跟著改:欄位與策略詳情對齊,迷你走勢不需要,底部說明列不需要。

- 決策：策略總覽表欄位為:名稱、類型、對基準、年化、Sortino、最大回撤、勝率(附交易次數)、開啟;迷你走勢欄拿走。每行代表的運行與策略詳情頁預設顯示的那次相同(有現役設定用現役,否則用排名第一的非失敗正式運行),兩頁數字必須一致。全部策略的正式運行都是失敗運行時,該策略不列於主表,收進一行「另有 N 條策略無達標運行」可展開(依 D-034 的做法推出)。所有頁面底部那條說明列(數據期間、數據快照、「數字全部由本機庫內…」、圖表庫版本)整個拿走。

- 考慮過的替代方案：總覽保留盈虧比欄(未選,與運行表對齊為準);總覽保留迷你走勢(未選)。

- 為何選這個：用戶原話:「策略總覽 need to be updated as well? As the column 1) should match with the 策略詳情 page? the column and the chart. 迷你走勢 in the table I think is not needed」及「the bottom bar is not needed」;每行對應策略頁預設那次運行、全失敗策略收進展開行,是主 agent 依 D-034/D-037 推出。

- **用戶原話（原文照錄）**

  > 策略總覽 need to be updated as well? As the column 1) should match with the 策略詳情 page? the column and the chart. 迷你走勢 in the table I think is not needed. … the bottom bar is not needed

- 影響：策略總覽表與 API 改欄位(KARST-081,接 KARST-080);頁腳元件移除;design-system.md 更新。

## D-040 失敗運行在畫面上完全不顯示,連「另有 N 條失敗運行」展開行也不要;全部正式運行皆失敗的策略在策略總覽仍列一行,只顯示失敗數(部分取代 D-034 的展開行)
- 類型：決策
- 狀態：有效
- 日期：2026-08-29

- 出處：用戶 2026-08-29

- 背景：主 agent 在 D-039 提出全失敗策略收進展開行,用戶答「No need. Actually they are no need to show up and should be excluded from the strategy page at all」。

- 決策：失敗運行(年化同時低於 SPY 與 QQQ 買入持有的正式運行)在策略總覽、策略詳情、運行排名表、持股分布都不出現,不留展開行、不留計數;登記、留痕、直連網址照舊。全部正式運行皆失敗的策略在策略總覽仍列一行,成績欄留空,只顯示「N 條運行全部失敗」的計數,令該策略仍然可見、可點入;策略詳情頁的運行表則空白,同樣只顯示該計數。D-034 的「另有 N 條失敗運行」展開行取消。(同日補充:主 agent 講明「全失敗策略不列」會令策略隱形,用戶答「if all are failed. You can just leave a failed count. Then the strategy will be visible as well」,決策文字據此修訂。)

- 考慮過的替代方案：保留展開行(未選)。

- 為何選這個：用戶原話:「No need. Actually they are no need to show up and should be excluded from the strategy page at all I think」。

- **用戶原話（原文照錄）**

  > No need. Actually they are no need to show up and should be excluded from the strategy page at all I think

- 影響：KARST-077 改為只隱藏、不做展開行;KARST-081 第 (3) 項改為全失敗策略不列;失敗運行詞條修訂。

## D-041 基本面財報數據主幹改為 SEC EDGAR XBRL(2009 財年起,按申報日期還原知情時點,保留除牌公司);DefeatBeta 與 yfinance 降為補充與核對(部分取代 D-026 的 defeatbeta 管基本面分工)
- 類型：決策
- 狀態：有效
- 日期：2026-08-29

- 出處：用戶 2026-08-29

- 背景：KARST-076 實測:DefeatBeta 年報只由 2019 年起、典型每家 7 期、44 隻已除牌成分股無一有歷史;yfinance 硬上限 4 年度 5 季度、除牌股連價格都無;EDGAR 2009 財年起齊全、保留除牌公司、可還原申報時點(蘋果 2008 年總資產申報時 395.72 億 vs 重述後 361.71 億)。主 agent 提選項,用戶首答「維持 DefeatBeta 主幹」並留言「OK, just I afraid the scraping will be an issue」;主 agent 澄清 EDGAR 不是網頁抓取而是官方機讀接口後再問,用戶改選「改用 SEC EDGAR 主幹」。

- 決策：基本面線(D-033 第 6–8 類與估值模型目錄首批 13 條)的財報數據主幹是 SEC EDGAR 的機讀申報數據(companyfacts 壓縮包 / 逐公司 JSON,官方免費、不需鑰匙、附聯絡電郵、每秒不超過十次請求);每個事實以申報日期作知情時間,不用重述後數字回測。誠實回測範圍為 2009–2026。DefeatBeta 與 yfinance 只作補充(近期季度、價格)與交叉核對,不作主幹。EDGAR 來源適配器待第一條基本面策略開工時連同建置票一併開,不在基建期插隊。

- 考慮過的替代方案：維持 DefeatBeta 主幹(用戶首答,澄清後放棄);暫不裁等揀第一條策略(未選)。

- 為何選這個：用戶原話:「OK, just I afraid the scraping will be an issue」;澄清後選「改用 SEC EDGAR 主幹 (Recommended)」。

- **用戶原話（原文照錄）**

  > 即是基本面線的數據主幹很可能要改為 EDGAR <<< OK, just I afraid the scraping will be an issue / 改用 SEC EDGAR 主幹

- 影響：D-026 中「defeatbeta 管基本面」的分工部分取代;基本面線所有建置票以 EDGAR 適配器為前置;A-012 已按此記為崩塌。

## D-042 策略詳情改為「批次層」畫面:批次=一次參數掃描;淨值圖畫成密度熱帶(疊最佳單次、SPY、QQQ);門面=最佳批次整體+該批最佳單次;掃描批次表可切換;點運行行=在批內選一次運行作篩選,整頁轉為該次;取消運行詳情頁與參數格熱力圖頁(取代 D-036、D-037 的頁面結構,取代 D-029、D-035;先出原型再實作)
- 類型：決策
- 狀態：部分已取代（見 D-045）
- 日期：2026-08-30

- 出處：用戶 2026-08-30

- 背景：用戶看過 079–081 的成品後指出主 agent 把「熱力圖帶」理解錯:不是參數掃描的格仔圖,而是淨值圖上把一批運行疊成的帶。經一輪八問(批次定義、批次排名、門面組成、熱帶畫法、失敗運行處理、批次切換、運行詳情頁去留、批次層持股分布、參數格頁去留),用戶逐題裁定。

- 決策：(1) 批次 = 一次參數掃描跑出來的那批運行;策略詳情頁以批次為單位顯示。(2) 最佳批次 = 達標運行的中位數年化最高(旁列達標比率與批內最佳單次);頁面預設顯示最佳批次。(3) 門面成績:左半=最佳批次整體(N 條達標/M 條、中位年化、中位 Sortino、中位最大回撤),右半=該批最佳單次並明標「最佳單次」;若有現役設定另加一格顯示,不冒充門面(D-031 精神保留)。(4) 淨值走勢改為密度熱帶:批內每條淨值曲線疊上去,同一格經過的曲線越多越紅;疊三條線——該批最佳單次(實線)、SPY、QQQ(虛線);熱帶只計達標運行,門面標明隱藏了幾多條失敗運行(D-040)。(5) 掃描批次表:名稱、日期、格數、達標比率、中位年化,按 (2) 排名,點一行整頁切換到該批。(6) 歷次運行表列該批的達標運行,四成績欄可排序(現時排序壞了,一併修);點一行 = 在批內選一次運行作篩選,整頁轉為該次:淨值圖變該次一條線(熱帶淡化為底)、持股分布變該次、並在下方出現該次的選股快照與選股漏斗(漏斗緊貼快照,是它的篩選器)、參數與因子資料摺疊區;再點一次或點「回到批次」還原。直連網址 ?id=&sweep=&run= 保留。(7) 持股分布批次層:每隻股票被幾多條達標運行持有(頻率)、平均持有日數、平均累計報酬,按頻率排前十;選了單次運行即轉為該次(持有日數、累計報酬)。(8) 運行詳情頁取消(D-035 取代);參數格熱力圖頁取消(D-029 取代),參數空間視角日後另裁。(9) 頂層導覽維持兩頁:策略總覽、策略詳情;總覽每行數字改為對齊批次門面(最佳批次中位數),欄位細節由原型定。(10) 先出原型(假數據、lightweight-charts)等用戶過目,認可後才實作。

- 考慮過的替代方案：批次=同策略全部正式運行(未選);最佳批次按最佳單次排(未選);門面只顯示最佳單次(未選);熱帶計入失敗運行(未選);保留運行詳情頁作下鑽層(未選);保留參數格熱力圖作下鑽層(未選)。

- 為何選這個：用戶原話:「By means of Heatband, I think it is in the chart 淨值走勢 that instead of just 1 line, as 1 batch can have many success run. Then I want to see the band in chart which mean the distribution of this batch for all the run」「一次參數掃描跑出來的那一批 << This」「I think it is the frequency as the heatmap concept? more overlap will be more red?」「Prelim I want to see the best batch, and the best run of the best batch」「The gap is just to select 1 run in the batch. Then the chart, and the stock selection and distribution will be run level, it is kind of a filter of the batch」「Prototype first before implement to confirm」;Q1–Q8 答案:甲甲甲甲甲乙甲乙。

- **用戶原話（原文照錄）**

  > Q1甲 Q2甲 Q3甲 Q4甲 Q5甲 Q6乙 <<< I have mentioned already. The gap is just to select 1 run in the batch. Then the chart, and the stock selection and distribution will be run level, it is kind of a filter of the batch. Q7甲 <<< And then can be run level Q8乙 Prototype first before implement to confirm

- 影響：D-036、D-037 的頁面結構被取代;D-029、D-035 全部取代;D-039 總覽欄位的「代表運行」改為「最佳批次中位數」,細節待原型;KARST-079/080/081 已建的策略頁與運行詳情頁大部分要重做;開原型票(KARST-086),認可後開實作票。

## D-043 後端架構審視八個候選全部推進;順序按「靜默錯數風險」先於「建置成本」
- 類型：決策
- 狀態：有效
- 日期：2026-08-30

- 出處：依用戶 2026-08-30 一句推出

- 背景：2026-08-30 後端架構審視(research/2026-08-30-architecture-review-backend.md)列出八個深化候選。主腦判斷:候選二(治理漏快照登記)、五(三份「最新已知值」實作可能靜默分歧)、六(網頁層自己算指標)、八(風控算術重複)帶有「數字錯了沒有人知道」的信任風險;候選一(策略合約)、三(凍結單一正本)、四(掃描單一介面)、七(定義庫介面過闊)屬建置成本與速度,不改變任何結果數字。

- 決策：
  1. 八個候選全部做。
  2. 順序:二(KARST-087)→ 五(KARST-088)→ 一+四合併設計(設計兩次後開票)→ 三(087 之後開票)→ 六(併入策略頁批次層實作票)→ 八(先開查證票確認是否真重複)→ 七(延後,首條策略落地後重審)。
  3. 087 與 088 同觸 store.py,必須先後不可並行。

- 為何選這個：帶靜默錯數風險的先做,因為它們影響對盤數的信任;純成本的候選在第一條新策略建置前做完即可,候選七面積大且不影響結果,延後不設期限。

- **用戶原話（原文照錄）**

  > any of them has business implication? If all are technically I think we should do that?

- 影響：開票 KARST-087/088;候選一/四設計兩次後開實作票;候選三/八另開票;候選六併入策略頁批次層實作票;候選七不開票,首條策略落地後重審。

## D-044 趨勢波段專用風控掃描器整檔退役;因子輪動搬入執行台時補正式登記、舊運行標過時
- 類型：決策
- 狀態：有效
- 日期：2026-08-30

- 出處：用戶 2026-08-30 於選項介面裁決

- 背景：策略層深化(KARST-090/091/092,設計評審 research/2026-08-30-strategy-layer-design/design-judge.md 第六節)留下兩個要用戶拍板的未決點:(1) 風控三格收進參數規格成為普通可掃軸之後,karst/risk/sweep.py 的私掃描器是退役還是降級;(2) 因子輪動從未正式登記(借用因子混合身份),搬入必須補登記,會生成新策略版本。

- 決策：
  1. karst/risk/sweep.py 整檔退役;風控掃描自此只走策略執行台一條路;tests/test_risk_layer.py 依賴它的兩個測試改打執行台。
  2. 因子輪動搬入時補一次正式登記,生成新策略版本;舊運行依 D-021 第 9 條標過時,不刪不改;新版本編號與被標過時的運行清單記在 KARST-091 票上。因子混合與趨勢波段的運行編號不變。

- 為何選這個：同一件事留兩個掃描器正是這次架構整理要治的病;輪動舊運行只是未經對齊的示例運行,標過時的代價低於維持一個從未登記的身份。

- **用戶原話（原文照錄）**

  > 整檔退役

  > 接受

- 影響：KARST-092 第 (3) 項按「退役」執行;KARST-091 第 (6) 項按「接受」執行;CONTEXT.md 共用風控層詞條不用改(掃描器不是詞條)。

## D-045 策略詳情單次運行層改為「時點檢視」:淨值圖標進出場並與時點卡併排,選股快照撐滿下方;歷次運行預設頭 10 名;批次層佈局認可
- 類型：決策
- 狀態：部分已取代（見 D-046）
- 日期：2026-08-30

- 出處：用戶 2026-08-30 原話與選項介面裁決

- 背景：KARST-086 原型改版稿(兩組併排、去現役設定卡、密度疊線預設)給用戶過目。用戶認可批次層佈局,指出兩個表的表頭壞了、歷次運行只需頭 10 名,並否決主腦「選股快照卡撐滿整行」的提議:單次層要看到某一時點的持倉與成交,圖上要見進出場訊號。

- 決策：
  1. 批次層佈局照現稿:密度熱帶淨值圖與持股分布併排;掃描批次表與歷次運行表併排;表頭修好。
  2. 歷次運行表預設只列按當時排序的頭 10 名,下設「展開全部 N 條」;整批資訊由密度熱帶與批次門面交代。
  3. 選了一次運行後進入「時點檢視」:淨值圖在左,淨值線上標進場▲出場▼(同日多筆合成一個標記,懸停見股票與方向),點任何一日或一個標記即定「時點」,預設時點為該次運行最後一日;右邊「時點卡」分頁籤:持倉(該時點持什麼、成本、浮動盈虧)、成交(該日買賣)、全期持股分布(該次運行整段期間的頻率/平均持有日數/平均累計報酬)。
  4. 選股快照撐滿整行放在圖與時點卡之下,顯示時點當日全宇宙逐隻分數與去留,選股漏斗貼在旁邊當篩選器;三處(時點卡、快照、漏斗)隨時點同步。
  5. 以上先改原型再給用戶過目,認可後才開實作票。

- 為何選這個：批次層答「這批整體去了哪裡」,單次層答「這一次在哪一日做了什麼、為什麼揀這些」;時點由圖驅動,三處同步,不用另開頁。頭 10 名是因為人不會逐行讀千條運行。

- **用戶原話（原文照錄）**

  > I think the layout is ok.

  > Header of 掃描批次 and 歷次運行 seems broken, 歷次運行 default I think show only top 10 after sorting is ok, click to expand but I think I won't really will look at them as Human can't read thousand of run

  > When clicked in 1 run. The 該次運行・選股快照 should actually merged with 持股分布. I think it should be a flag on that card.

  > Not ok any better option. As In I even want to see the transaction and holder of that point in time as well. Also the chart when run is choicen I want to see the in and out ssignal

  > 圖與時點卡左右併排

  > 淨值線上,點標記展開該日成交

- 影響：KARST-086 原型再改一輪;D-042 第 (6)(7) 項的單次層描述由本決策細化(部分已取代);CONTEXT.md 加「時點檢視」;實作票待原型認可後開。全期持股分布放進時點卡第三個頁籤是主腦按用戶選項推出的擺位,用戶未明講。

## D-046 單次運行層改為整頁換成該次:淨值圖(40–50%)帶進出場標記在左、選股快照在右;成交列全部不限時點;時點線要準
- 類型：決策
- 狀態：有效
- 日期：2026-08-30

- 出處：用戶 2026-08-30 原話

- 背景：KARST-086 第三輪原型把時點檢視接在批次層之下、時點卡放在圖右、選股快照撐滿下方、成交只列時點當日。用戶過目後否決這幾點。

- 決策：
  1. 選了一次運行後整頁換成該次(批次層的門面、熱帶、批次表、運行表全部收起),頂部留「回到批次」與該次身份。
  2. 淨值圖就是批次層那張淨值圖轉為單次:寬 40–50%,該次淨值實線,線上標進場▲出場▼,不另設「時點檢視」區塊;點任何一日或標記定時點,時點垂直線必須落在所點那一日(第三輪畫錯位,要修)。
  3. 淨值圖右邊即是選股快照表(代號、名稱、行業、各層因子分數、綜合、基本面、技術、狀態),隨時點更新;選股漏斗貼在快照上方當篩選器。
  4. 成交列該次運行全部成交,不限時點;點一行成交即把時點定到該日。持倉(該時點)與全期持股分布放在下方。
  5. 先改原型再過目;認可後才開實作票。

- 為何選這個：用戶要選了一次運行後專注看該次,不要批次層留在上方;選股快照是單次層最重要的表,要在圖旁一眼看到;成交要全期看節奏。

- **用戶原話（原文照錄）**

  > But 批次層 still got changed? I want to see the prototype of 「整頁換成該次」 actually.

  > Especially the table 代號 名稱 行業 質素 動量 超賣 綜合 基本面 技術 狀態 <<< Should be the right card of the 淨值圖. I think 淨值圖 can be smaller like 40% or 50% width.

  > 淨值與進出場 that concept should go backk to 淨值圖, but now the blue dotted line has bug. it is not accurate. Also 成交 just show all 成交 it is not needed to show only point in time.

- 影響：D-045 第 3、4 條被本決策取代(部分已取代);KARST-086 原型第四輪;CONTEXT.md「時點檢視」詞條意思收窄為單次層本身而非附加區塊。成交與持倉在下方的左右擺位由主腦按用戶原話推出,用戶未明講。

## D-047 畫面一期定稿並凍結迭代;工作重心轉入策略期,策略測試以對話+命令列先行,畫面實作押後至首條策略有真批次
- 類型：決策
- 狀態：有效
- 日期：2026-08-30

- 出處：用戶 2026-08-30 原話

- 背景：KARST-086 原型第四輪(D-046 佈局)給用戶過目。用戶裁定一期收貨、停止畫面細節迭代,並確認策略測試以對話進行、畫面只是窗口;數據與引擎已各剩一套(S&P500 凍結快照+宏觀;vectorbt 經適配層;唯一入口)。

- 決策：
  1. KARST-086 第四輪稿即畫面一期定稿(批次層 D-042/D-044、單次層 D-046);此後不再開畫面變體、不再迭代細節,除非壞掉或用戶主動再提。
  2. 策略詳情頁實作票開而不派,排在首條策略產出真批次之後;架構候選六(網頁取數層停止自己算數)併入該票一次過做。
  3. 進入策略期:參數對齊、掃描、判讀、報數全部在對話+命令列完成;報數用業務語言(達標率、中位年化、回撤、穩健平原)。
  4. 策略期數據前設:價格與宏觀已就緒;基本面策略須先建 SEC EDGAR 數據線(D-041)才排得上。

- **用戶原話（原文照錄）**

  > I think the current design is just acceptable for phase 1. But I don't want to drill to detail in the screen already. As for an investment strategy, the key is the strategy but not the UI as it is still only for my personal use for now.

  > Meanwhile, I pressumed by now, you should only rely on 1 single dataset, single backtest framework. Then actual if I just talk to you here without the UI. You will still able to perform the strategy testing properly? If that's the case. We will move on to the next phase on Strategy

- 影響：KARST-086 關檔;開策略頁實作票(不派);KARST-092/094/096 照常收尾;下一步由用戶揀首條策略。

## D-048 策略先行:因子庫由「發現策略」降為「支援已有策略前提」;因子三種用途(選股、時機確認、逆向解讀);全市場評估只作校準;假設與收窄規則必須在看數據之前寫低
- 類型：決策
- 狀態：有效
- 日期：2026-08-30

- 出處：用戶 2026-08-30 原話

- 背景：主 agent 提出三層模型(第零層因子庫中性、第一層全市場統一評估、第二層才有策略),用戶否定其因果方向。用戶論據:一條因子在全市場多空排序得出的是一個平均數,若訊號只在少數股票上有效,平均即趨零;能通過全市場檢驗的按定義是幾乎對所有股票都成立的東西,亦即最擁擠、最平凡的東西。故全市場評估對「集中而有條件的優勢」結構性盲。同一輪主 agent 誤稱財報與業績發布會逐字稿「完全沒有來源」,用戶當場更正:來源早已定案並驗證過(D-041 SEC EDGAR 為財報主幹;DefeatBeta 提供逐字稿與損益表,舊項目 KarstETF 已實際取用約 6,530 份逐字稿 / 98 隻代表股,語料今日仍在機器上,四個快取目錄共 173 檔約 162MB),欠的只是接進 Karst 的管線。此誤述是主 agent 上兩輪把主線推向純價格因子的直接原因。

- 決策：
  1. 因果方向定為策略先行:先有一個可證偽的策略前提(例如供應鏈樽頸、錯殺),由它收窄宇宙,再用因子在收窄後的宇宙裡找時機與做確認。因子庫的定位由「用來發現策略」降為「用來支援已有前提」。
  2. 因子有三種用途,驗證要求各不相同:(甲)選股——按排名揀,屬預測用途;(乙)入場時機與確認——屬預測用途;(丙)逆向解讀——用因子描述一批既有持股(如某投資者或國會議員披露持倉)背後的揀股邏輯,屬描述用途,結論只可當假設來源,不可當結論,須另在別的宇宙或期間驗證。
  3. 全市場跑只保留一個用途:校準——拿有公開答案的訊號跑一次,證明本平台算得對。它是驗機器,不是搵策略;跑一次即止,不作發現用途。
  4. 假設與收窄規則兩者都必須在看數據之前寫低。禁止的做法是:先揀定一批股票,再去因子庫問哪幾條與之最夾——那量到的是自己那條揀股規則,不是未來回報,屬循環論證。合規的做法是:條件寫在前面,量的是條件成立之後的回報。
  5. 收窄那一步本身是一個賭注,同樣要驗證(那批股票其後有沒有跑贏);不能靠把篩選做得更聰明來免除量度。
  6. 因子混合取互相獨立的:因子與其後回報的關係是要找的東西;因子與因子之間高度重複則拿走一條(用戶 2026-08-30 確認)。

- **用戶原話（原文照錄）**

  > 所以其實一定係策略先行囉全部嘢都係而唔係,即係我求其random比一堆嘢嚟,然之後就話咁佢邊隻呢50隻股邊啲因子同佢夾

  > 如果你用全個美股市場嚟驗證過因子負,然之後先可以制定策略嘅話,咁你咪即係其實你好like係個甄子符其實係未必有用或者係你真係搵到一個Marco Economic即係大環境上都可能有用嘅即係你就搵唔到啲?即係比較個別適用嘅

  > 即係其實佢揀咗啲咩股票我就係到返轉頭想用個因子去或者係同你去討論吓啦究竟其實佢哋咁樣揀呢啲股票背後嘅邏輯係咩?即係個因子都變咗可以係俾我哋去了解得到,其實佢哋個孫古邏輯囉

  > 另外你又話我啲財報啊,啲業績發佈會捉沒有?唔係囉我哋有㗎啦

- 影響：取代主 agent 同日提出的三層模型之因果方向。上一輪『首輪先跑十條價格因子』的計劃降為校準用途,不再是主線。評估台的宇宙改為由假設指定的輸入,不再固定為全美股。開兩張與首條假設無關、無論走哪條路都要的票:測試協議、分組多空回報計算件。首條策略前提待用戶指定;樽頸策略(D-004,以逐字稿為主要輸入)是現成候選。財報與逐字稿數據線由『未有來源』更正為『來源已驗證、欠接線』。

## D-049 四個價格系市況開關一族退役;防守格不得再由股票充當;訊號準繩度測試升格為開跑前的篩選關卡
- 類型：決策
- 狀態：有效
- 日期：2026-08-30

- 出處：主 agent 依 KARST-103 實測結果裁決。用戶未就此事發言,不記為用戶裁決;用戶本人只表達過『短期最有興趣做四隻因子 ETF 的配置,並要一個判斷此刻應進攻、防守還是避險的訊號』這個目標,本決策是對達成該目標的手段作出的技術裁決,方向本身未變。

- 背景：KARST-102 查出四個判市況的驅動器(大市趨勢開關、恐慌指數水平、恐慌指數期限結構、信用利差方向)在三次跌市的得益全為負。當時有兩個互相排斥的解釋且後續行動完全相反:(甲)訊號本身判錯;(乙)訊號判對但月度換倉令成交遲到。KARST-103 用日線逐個開關、逐次跌市重算訊號首次轉守日、對照實際成交日、並在只改成交時點不改訊號的前提下重算,以判定是哪一個。不判定就會在一個訊號本身無效的方向上繼續投入。

- 決策：
  1. 四個價格系市況開關(大市趨勢、恐慌指數水平、恐慌指數期限結構、信用利差方向)判定為訊號本身判錯,一族退役,不再在其上投入調參或加變體;信用利差方向兼有換倉太慢成分,但以訊號錯為主,同樣退役
  2. 防守格不得再由股票資產充當:在四隻因子 ETF 的宇宙內,即使一個事後完美的開關在急跌市也只護得住約半個百分點,因為四隻同屬股票;要做跌市保本,防守格必須是股票以外的資產(現金、債券或其他),此事需用戶裁定是否擴闊宇宙,在裁定之前不得自行擴闊
  3. 訊號準繩度測試升格為開跑前的篩選關卡:任何市況開關類訊號在跑參數掃描之前,必須先通過『轉守之後防守那邊是否真的跑贏』這項只需幾行運算、不用回測的檢驗;不通過即不准進入掃描
  4. 換倉節奏收緊仍然是有效方向,但必須配一個已通過上條篩選關卡的訊號;單靠改節奏救不返一個判錯的訊號

- 考慮過的替代方案：
  1. 只改換倉節奏、保留四個開關 —— 不揀:實測顯示改成即時成交後零個由負轉正,四個之中三個更差,唯一改善那個仍是負數;節奏不是病因
  2. 保留恐慌指數期限結構單獨再試 —— 不揀:它是四個之中訊號質素最差的一個,十五格零格翻身;主 agent 開跑前的預測正正估錯這一項,反而更應退役
  3. 整條因子輪動線一併放棄 —— 不揀:七套方法之中『相對強弱』一套中位數勝過等權基準且是唯一勝過大市那套,而『沒有因子跑贏大市就全數轉現金』一條在 2022 年省了 7.5 個百分點;退役的是判市況那一族,不是整條線

- 為何選這個：兩個最要命的證據不是『遲到』能解釋的:一,十九個設定全部出現『叫轉守之後防守那邊反而跑輸』,而該項檢驗由訊號當日起計、完全沒有成交延遲在內;二,2020 年有一半設定、2022 年有六成設定在跌市開始之前已經身處防守、零遲到,照樣蝕。遲到中位數 16 個交易日、空窗期大市中位跌 2.06% 看似昂貴,但同期防守那邊一樣在跌,兩邊只差零點幾個百分點,而且 33 個空窗之中有 7 個期間大市反彈、遲到反而慳返。至於升格篩選關卡,理由是成本不對稱:這項檢驗只需幾行運算,而這四個開關本來可以在跑 494 組參數之前就被篩走。

- 影響：karst/strategies/factor_rotation.py 的 TrendSwitchDriver、VixLevelDriver、VixTermDriver、CreditTrendDriver 四個驅動器歸入退役類,不再開新票調參或加變體。因子輪動(ETF 版)的防守上限須在相關報告中明寫為約半個百分點,擴闊宇宙至股票以外資產列為待用戶裁決,未裁決前不得開實作票。新增訊號準繩度篩選關卡一件,須在參數掃描入口之前生效,KARST-103 的判準與運算方式為其規格來源。任何以收緊換倉節奏為賣點的新票,工作內容必須寫明所配訊號已通過該關卡,否則不予開票;CONTEXT.md 加『訊號準繩度測試』與『防守格』兩個詞條。

## D-050 退化神諭曲線列為每條策略線的起點:未量出打和準繩度之前,不得進入建置
- 類型：決策
- 狀態：有效
- 日期：2026-08-30

- 出處：用戶 2026-08-30 裁決。原話見 quote 一欄。起因是主 agent 在 KARST-107 設計中提出這個做法,用戶讀後表示應該立為通則並寫低。

- 背景：KARST-102 與 KARST-103 的教訓是:我們在一個獎品尺寸未量過的方向上,跑了 494 組參數、七套方法、兩張票,最後查出四個市況開關連事後完美執行都只護得住約半個百分點——即是說那個方向的天花板本身就低,無論訊號多準都贏不到。同樣的浪費會在下一條策略線重演,除非在投入之前先量獎品。用戶今日定下四隻因子 ETF 的策略前提時,自己提出要先知道『事後全知可以跑贏幾多』,主 agent 在此之上加了退化那一節;用戶讀後裁定這個做法應該通用於每條策略線。

- 決策：
  1. 每條新策略線在進入建置之前,必須先跑退化神諭曲線:先算事後全知的上限,再逐級退化準繩度(由全中一路退到隨機),每級用足夠抽樣給出分布而非單一路徑,量出超額回報跌至零的那個準繩度,此數稱為打和準繩度
  2. 打和準繩度必須對『同期最強的單一被動選擇』報,不可只對大市報:若事後全知的輪動只比單獨持有最好那一隻好少許,則輪動本身不值得做,直接持有一隻即可
  3. 打和準繩度過高(即要求極高準繩度才贏得到)的策略線判為不值得走,不進入建置;上限本身高但打和準繩度苛刻,同樣判為不值得走
  4. 此曲線是起點不是終點:它答得到『值不值得有一個訊號』,答不到『有沒有一個訊號』;通過此關只代表該線可以繼續,不代表該線成立,結論一律仍按 D-048 定性為探索性

- 考慮過的替代方案：
  1. 只算事後全知上限、不做退化 —— 不揀:上限本身只是入場券,一個很高的上限若果需要九成準繩度才拿得到一半,這條路一樣是死的;不做退化就分不出這兩種情況
  2. 在建置之後才回頭量獎品 —— 不揀:那正是 KARST-102 與 KARST-103 已經發生過的浪費,兩張票加 494 組參數之後才知道天花板只有半個百分點
  3. 只對大市報打和準繩度 —— 不揀:大市不一定是最難的對手,若單獨持有某一隻已經跑贏大市,那才是真正的門檻,對大市報會令一條實際上輸給被動持有的線通過關卡

- 為何選這個：成本不對稱。這條曲線只需要價格數據與抽樣,不用建任何訊號、不用跑參數掃描,幾個鐘之內出得到;而走錯一條策略線的代價是數以週計的建置加上一個看似有數據支持的錯誤結論。而且它答的問題是其他測試答不到的:所有回測都在問『這個訊號幾好』,只有它在問『這件事本身值不值得做』。

- **用戶原話（原文照錄）**

  > 都合理嘅，我覺得用退化神與曲線呢個講法作為我哋每個stage嘅起點其實都幾有幫助嘅我覺得呢個可以寫低

- 影響：每張策略建置票的工作內容必須先指出該線的退化神諭曲線在哪一份報告、打和準繩度是多少;未量過的線不予開建置票。KARST-107 為此做法的首個實例與規格來源,其計算方式(全知上限、三個變體、逐級退化抽樣、打和點)為後續各線的樣板。KARST-106 那個訊號準繩度關卡與本條分工不同,前者篩單一訊號、後者篩整條策略線,兩者都要過,不得互相取代。CONTEXT.md 加『退化神諭曲線』與『打和準繩度』兩個詞條。

## D-051 可交易宇宙限於市面現成的因子 ETF:不自建個股層面的因子籃,理由是交易成本與戶口規模
- 類型：決策
- 狀態：有效
- 日期：2026-08-30

- 出處：用戶 2026-08-30 裁決。原話見 quote 一欄。

- 背景：Pacer 那份文件的核心觀點是用八個因子(每個因子的高低兩邊都用),而我們現有四隻 ETF 只是傳統那一邊,即只有半張棋盤;文件引 1994–2024 數據指非傳統那一邊在 43.59%–54.70% 的季度跑贏傳統那一邊。主 agent 因此指出兩條路:買 PALC(規則不公開的黑箱),或落到個股層面自己砌另外四個因子籃。用戶即時否決了後者,理由是交易成本與戶口規模。這條約束會反過來決定日後每一條策略線可以用什麼工具,所以必須在建置之前定死。

- 決策：
  1. 可交易宇宙限於市面上已經存在、可以直接買賣的因子類 ETF;不自建需要逐隻股票買入並定期再平衡的因子籃,理由是手續費與戶口規模令這種做法在實務上不成立
  2. 非傳統那一邊(低價值、低動能、低質素、高波動)因為沒有現成 ETF,在自建路線被否決之後只剩兩個處理方式:買現成的多因子輪動產品(例如 PALC),或者接受我們的棋盤只有一半並在報告中明寫這個限制;兩者皆未拍板
  3. 個股層面的因子研究仍然可以做,但定位改為「解釋與校準」而不是「可執行策略」:任何以個股籃為落注單位的結論,必須另外指出用什麼現成工具才落得到注,指不出即不得列為可執行
  4. 日後任何策略票在寫工作內容時,必須指明落注工具是哪一隻或哪幾隻現成 ETF;寫不出即該策略線在本平台不可執行,不予開建置票

- 考慮過的替代方案：
  1. 自建個股層面因子籃 —— 用戶否決:手續費與戶口規模令逐隻買、逐次再平衡在實務上蝕住做,這是資金規模決定的硬約束,不是技術問題,做得幾好都改變不到
  2. 只做四隻傳統因子 ETF、當另一半不存在 —— 未否決但要明寫代價:我們自己量到四隻剝走大市後只剩 0.03 的關係、空間很細,而那正是只拿半張棋盤的後果;所以這個選擇等於接受一個已知偏低的天花板
  3. 改用個股但降低換手以壓成本 —— 不揀:降低換手會令因子曝露走樣,而且用戶的約束是每筆手續費相對戶口規模,不是換手頻率本身

- 為何選這個：這是資金規模帶來的硬約束,不是可以靠做得好一點繞過的東西。早一日定死,就早一日不會再開一張「理論上很好、但這個戶口根本執行不到」的票——KARST-102 與 KARST-103 已經示範過在一個天花板本身就低的方向上投入的代價,而執行不到比天花板低更徹底。

- **用戶原話（原文照錄）**

  > 我就唔覺得呢要自己組成嗰啲Tiet㗎啦因為呢一方面就係交易成本問題啦，即係如果我要砌嗰啲ETF即係我要逐隻買逐隻買逐個re balance咁我錢又唔係話真係好多咁我扣埋手續費啊都好金喎其實咁所以其實就好難㗎啦咁所以其實我諗我可以動用嘅就真係市面上面現成可以有嘅因子類嘅S&P 500 ETF

- 影響：所有涉及個股層面選股的既有票與研究,結論一節必須加一句「用什麼現成工具落注」,指不出的降為解釋用途。八因子路線只餘買現成產品一途,PALC 因此由「參考對照組」升為「可能的落注工具」,KARST-107 量 PALC 的那一項連帶提高重要性。研究跑仍可用個股與學術指數作校準,但不得因為校準跑的結果好而推論該做法可執行。CONTEXT.md 加『可交易宇宙』詞條。

## D-052 現金正式入防守格,並升格為所有策略的常設選項;擇時線的報信人搜尋轉向持倉與資金流維度
- 類型：決策
- 狀態：有效
- 日期：2026-08-30

- 出處：用戶 2026-08-30 裁決,原話見 quote 一欄。第一句批的是主 agent 提出的『防守格加現金』,第二句是用戶自己擴闊:現金不限於這條線,是所有策略的常設選項。

- 背景：D-049 已判防守格全是股票時,急跌市保護上限只有約半個百分點,並把『擴闊宇宙至股票以外資產』列為待用戶裁決。其後 KARST-107/110 量出:四選一加現金那格,月度多 13.05 個百分點一年、最大回撤由三成四壓至一成二,週度更把回撤壓至 7.5%;KARST-102 的『無因子贏大市就全數轉現金』一條在 2022 年慳 7.5 個百分點;KARST-103 量出事後完美的股票內開關三次跌市只值 +7.65 個百分點。全部證據指向同一件事:防守的價值幾乎全部住在『離開股票』那一步。用戶據此拍板。

- 決策：
  1. 現金正式加入因子輪動線的防守格;四隻因子 ETF 的宇宙由四選一擴為五選一(四隻加現金)
  2. 現金升格為所有策略的常設選項:任何策略的可投資宇宙一律容許現金為其中一格,引擎須把現金當一等可投資對象處理;現金以什麼形式落實(純現金、短期國債 ETF 代理一類)未裁,屬實作票要先對齊的參數
  3. 擇時線的報信人搜尋正式轉向持倉與資金流維度(期貨持倉、基金資金流、貨幣市場基金資產、內部人買賣),價格衍生一族依 D-049 維持退役;新維度的任何候選一樣要過訊號準繩度檢驗與打和線,不因維度新而豁免

- 考慮過的替代方案：
  1. 防守格用債券 ETF 而非現金 —— 未否決但未裁:債券在 2022 年與股票同跌,不是萬能避風港;現金先行,債券留待日後按數據另議
  2. 維持四隻純股票宇宙 —— 不揀:三份獨立測量(103/107/110)一致顯示股票內防守的天花板只有每年零點幾個百分點,而加現金那格是全部測量中唯一同時提高回報與壓低回撤的動作

- 為何選這個：證據一面倒,而且用戶原話把它由一條線的設定升為平台原則:防守要有效,必須有一格真正離開股票;現金是最簡單、成本最低、任何策略都用得到的那一格。

- **用戶原話（原文照錄）**

  > (1) 拍板俾現金入防守格 <<< This is ok. And infact Cash can always be a option of our strategies

  > (2) 開票接持倉/資金流數據 <<< Where?

- 影響：引擎與策略合約要支援現金作可投資格(實作票另開,現金形式先對齊);因子輪動線的基準表自此要加『四隻加現金的事後全知』一欄;持倉與資金流數據接口的勘察票即開(CFTC 期貨持倉、ICI 資金流與貨幣基金資產,內部人申報歸已定的 EDGAR 線);CONTEXT.md 的防守格詞條更新為已裁。

## D-053 防守階梯:板塊輪動行先,現金只作最後一著——「無一個板塊安全」先落現金
- 類型：決策
- 狀態：有效
- 日期：2026-08-30

- 出處：用戶 2026-08-30 裁決,原話見 quote 一欄。承接同日 D-052(現金入防守格)與「兩種熊市」的討論(輪動熊裡低波動勝現金、全面熊裡現金勝一切股票)。

- 背景：D-052 批了現金入防守格之後,下一個設計問題是現金幾時用。兩級認錯成本不同:市場內輪動(換去防守性板塊)認錯平——訊號誤報只是少賺;轉現金認錯貴——誤報就錯過成段升幅。而我們已知自己的訊號誤報率高(價格系報信人全滅)。用戶據此定出階梯:平嗰級行先,貴嗰級做最後一著。

- 決策：
  1. 防守採兩級階梯:第一級在市場之內輪動(板塊層面,含公用、必需消費一類天然防守板塊);第二級才是現金,觸發條件是「無一個板塊安全」
  2. 板塊輪動線成為下一條要量的策略線;依 D-050,先量獎品上限與打和準繩度,未過關不進入建置
  3. 「全部板塊都不安全→轉現金」屬市況開關類:依 D-049 先過訊號準繩度檢驗,「安全」的判準必須在看數據之前寫死
  4. 因子輪動(ETF 版)一線定位不變:訊號試驗場與被動預設(持有動能),不作主力建置

- 考慮過的替代方案：
  1. 直接做「大市開關→現金」不經板塊 —— 不揀:現金認錯貴而我們的訊號誤報率高,把最貴的一級放最前等於保費最大化;且 KARST-103 已證價格系大市開關指錯方向
  2. 用四隻因子 ETF 做第一級 —— 不揀:四隻全部是全市場股票,無天然防守格(D-049 已證天花板約半個百分點);板塊宇宙有真防守格(公用、必需消費),而且板塊 ETF 歷史由 1998 年起,2000 與 2008 兩次熊市首次入到樣本
  3. 以債券 ETF 做中間級 —— 未裁:2022 年債與股同跌,是否加入留待板塊線量完再議

- 為何選這個：階梯把「認錯成本」由平到貴排序,與用戶早前「有防守意識、唔使下下中」的立場一致;而板塊層面第一次令防守可以留在市場之內完成(輪動熊食得到 2000 年低波動那種 +25%),現金只留給全面熊。

- **用戶原話（原文照錄）**

  > i see. So yes I think Cash is the last resort. In our theory, 板塊輪動should be first considered. Only when all sector is not safe then we move to cash

- 影響：開 KARST-113 量板塊線的退化神諭曲線(獎品、打和線、階梯規則在歷次熊市會不會響);板塊 ETF 價格數據不在現有快照的話,研究用途可在 scratchpad 探索性取數,生產級要另開接數票;日後板塊線的任何建置票必須指明它的退化神諭曲線報告與打和準繩度。

## D-054 平台重心:由上而下三層(市況→板塊→個股),基礎版本全程 ETF 落注;個股層保留為正式一層,但永遠在板塊之後
- 類型：決策
- 狀態：有效
- 日期：2026-08-30

- 出處：用戶 2026-08-30 裁決,原話見 quote。主 agent 原提案把個股層降為「板塊計分材料+錯殺加強」,用戶修訂:個股層仍然重要,但一律跟從由上而下次序。

- 背景：用戶自省平台是否過度複雜(『I doubt if I am setting the engine overcomplicated』),自認不是即市炒家、信念在選股、揀板塊、基本面、板塊輪動。討論中查實 gooptions 的搵目標流程是個股先行且無理由交代,而其自報成績跑輸『什麼都不做』;而我們自己量得到錢的位置(防守階梯、整段進出)都在板塊層,個股與因子層的訊號搜尋十八個候選全軍覆沒。加上 D-051(只用市面現成 ETF 落注)已令 ETF 層必然是執行地基。

- 決策：
  1. 平台重心定為由上而下三層:市況(防守階梯,D-053)→板塊→個股;任何策略按此次序收窄,不准跳層由個股起步
  2. 基礎版本全程用市面現成 ETF 落注(承 D-051):板塊層本身要可以獨立成軍,個股層做得再好都是加強項,不是地基
  3. 個股層保留為正式一層(用戶修訂,非降級),用途三個:錯殺、在已揀板塊之內押強者、基本面加強;另兼板塊計分材料(由成員股向上加總出板塊層基本面);個股層任何策略要獨立通過驗證,永遠在板塊層之後執行
  4. gooptions 式個股先行不採用:其流程經查證無板塊步、無理由交代,自報成績低於無為基準

- 考慮過的替代方案：
  1. 個股層降為純材料與附屬加強(主 agent 原提案)—— 用戶修訂不揀:個股仍然 very considerated,只是次序上永遠在板塊之後
  2. 個股先行(gooptions 式)—— 不揀:見 decision 第 4 條
  3. 板塊層用自建籃 —— 不揀:D-051 已裁只用市面現成 ETF

- 為何選這個：把搜尋空間由六百個選擇收窄到十一個再落到已揀魚塘之內,統計上誠實、執行上落得到注,同用戶的信念清單(揀板塊、基本面、錯殺、板塊輪動)一一對應;個股層保留正式地位,但以次序紀律防止回到最易自欺的層面起步。

- **用戶原話（原文照錄）**

  > :平台重心記做「由上而下三層:市況(防守階梯)→板塊→個股;基礎版本全程用 ETF 落注;個股層降為板塊計分材料+日後經驗證的錯殺加強 & 基本面加強 <<< I think individual is still very considerated. but always follow top-down approach. Both 錯殺, and betting the strong performance among sector.

- 影響：KARST-113 量緊的正是第一、二層的獎品上限,回來即知此架構的錢有幾大;日後錯殺策略票要寫明板塊版先行、個股版在已揀板塊之內做;財務報表數據線(EDGAR)的用途排序隨之調整——先服務板塊計分與錯殺,後服務全市場選股;因子混合、趨勢波段、影片轉技能三條線是否降級封存,用戶未裁,另行請示。

## D-055 因子混合、影片轉技能兩線降級封存;趨勢波段去向未裁(用戶問是否 VCP,主 agent 建議改編制為個股層進出場規則庫)
- 類型：決策
- 狀態：有效
- 日期：2026-08-30

- 出處：用戶 2026-08-30 裁決,原話見 quote。承 D-054(平台重心由上而下三層)後的線別清點。

- 背景：D-054 落實後,主 agent 請示三條不在用戶信念清單上的線如何處置。用戶裁兩條封存,第三條(趨勢波段)反問它是否 VCP——顯示用戶對這族強勢股突破打法仍有興趣,只是想確認它的身份。

- 決策：
  1. 因子混合策略線降級封存:不刪、不再投入,留返日後;其已產出的基建(掃描、批次登記一類)屬引擎資產照用,封存的是『以因子 ETF 混權重作為正式策略』這條線本身
  2. 影片轉技能管線降級封存:不刪、不再投入
  3. 趨勢波段未裁:用戶問『This is VCP?』——主 agent 答不是但同族(記錄裡是 Eric 一般化:突破 N 日新高、波段低位/均線成本線止蝕、三元素計劃、賠率門檻;VCP 另要求突破前波動收縮形態),並建議不封存、改編制為 D-054 個股層『板塊內押強者』的進出場規則庫,VCP 可作日後入場變體;待用戶覆

- 考慮過的替代方案：
  1. 三線齊封存 —— 用戶不揀:趨勢波段被點名再議
  2. 照舊全部保留 —— 不揀:與 D-054 收窄重心相違

- 為何選這個：把投入集中在用戶信念清單(揀板塊、基本面、錯殺、板塊輪動)對應的線上;封存不是否定,是排隊。

- **用戶原話（原文照錄）**

  > 因子混合、影片轉技能 can 降級封存. But what about 趨勢波段? This is VCP?

- 影響：開放票清點:屬因子混合與影片轉技能兩線的未派工票不再派工,標明封存緣由;趨勢波段相關票凍結至用戶裁去向;策略頁與文件中兩線標示封存狀態的整理留待架構整理一步一併做。

## D-056 趨勢波段改編制為進出場治理(不是策略);止蝕/賠率/跌後加注屬按策略信念類型配置的治理選項,配置必須在入場之前寫死
- 類型：決策
- 狀態：有效
- 日期：2026-08-30

- 出處：用戶 2026-08-30 裁決,原話見 quote。承 D-055(趨勢波段去向未裁)——用戶自己給出定性:它是策略的治理,不是策略本身。

- 背景：用戶指出三件事:(1) Eric 那套(突破入場、止蝕、賠率門檻)其實是治理一個策略的規矩,本身不是策略;(2) 止蝕與賠率門檻未必人人適用——對板塊沒有信念的注(例如反轉)需要,對有論點的注(例如樽頸)可能不需要;(3) 第一注入場後下跌,應該溝貨還是離場,必須在落注之前就有答案。並問學術界有沒有研究講這件事。

- 決策：
  1. 趨勢波段不再是策略線,改編制為進出場治理規則庫(歸進出場規則合約族,D-003/D-013):突破入場、止蝕擺位、賠率門檻、注碼規則是治理選項,供個股層與板塊層的策略按類型取用;VCP 一類形態日後可作這族的入場變體
  2. 治理配置(有沒有止蝕、賠率門檻要不要、跌後加注還是離場、加注上限)必須在入場之前按策略類型寫死,是策略合約的一部分,不准臨場決定
  3. 哪類策略配哪套治理,先過文獻關再定案:開研究票查學術證據(止蝕幾時有用幾時有害、溝貨對斬倉、賠率門檻的實證),回來才落設計決定

- 考慮過的替代方案：
  1. 趨勢波段維持獨立策略線 —— 不揀:用戶定性它是治理不是策略,且與 D-054 重心清單不對應
  2. 一刀切全部策略都設止蝕 —— 不揀:用戶明確質疑,且與「論點型的注價格下跌不等於論點死亡」相違;留待文獻票回來定案

- 為何選這個：把「幾時走、走定加」由風格之爭變成按策略信念類型配置的合約欄位,而且逼它在入場前寫死——同 D-048(前提先寫死)同一條紀律,只是用在離場那一邊。

- **用戶原話（原文照錄）**

  > 趨勢波段 <<< If it is Eric approach, I think it is actually some governance of a strategy. but itself is not a strategy as well. ... for those sector in faith (i.e. you bet is bottleneck), then actually 賠率 or 止蝕 may not needed? ... Whether you should be 均注 to buy in the 2nd entry level, or you should exit. I think this is something important to know at first before the trade is executed.

- 影響：開 KARST-114 文獻研究票;進出場規則合約日後加「治理配置」一節(策略合約必填);D-055 的趨勢波段懸案就此了結——相關票由凍結轉為按新編制改寫;錯殺與樽頸的策略票日後必須寫明自己的離場治理屬哪一族。

## D-057 轉向落地次序:引擎優先對齊新重心,介面押後;不重開新倉,以 tag、文件轉向聲明與逐模組審視防止新 session 走回舊方向
- 類型：決策
- 狀態：有效
- 日期：2026-08-30

- 出處：用戶 2026-08-30 裁決,原話見 quote。承 D-054–056 轉向後,用戶問資料庫與介面是否還適用、應否重開新倉;主 agent 建議「不重開、打 tag、逐模組審視」,用戶接納並加兩點:介面可後補、引擎必須先行反映最新決策以防日後 session 失焦。

- 背景：用戶的核心憂慮是漂移:轉向只住在對話與決策簿裡的話,下一個接手的 agent 會照舊規格與舊代碼的重心行事,把他帶回已否決的方向。Karst 本身是 KarstETF 的重開,教訓是重開保得住文件、保不住行得通的護欄,所以這次以「標記+聲明+審視」代替重開。

- 決策：
  1. 不重開新倉;已打 git tag `pre-pivot-2026-08-30` 作轉向前標記,git 歷史即存檔,倉內不放 ZIP
  2. 介面修改降為後補優先(儀錶板一類新畫面留待引擎對齊之後)
  3. 引擎優先對齊 D-052–056:現金作一等可投資對象、宇宙以市面 ETF 為基礎、三層次序、離場治理欄位入策略合約;開審視票逐模組判「留用/改編制/封存」,封存以搬走或刪除落實(git 留底),不留誤導性重心
  4. 防漂移三件:v1 規格文件已加轉向聲明(牴觸處以決策簿為準);規格正式修訂隨審視結果開票;現存開放票逐張覆核是否已因轉向失效

- 考慮過的替代方案：
  1. 重開新倉只帶文件 —— 用戶接納不重開:重開會失去經測試的護欄(實體編號、知情時間、唯一入口、快照治理),而這些正是新方向最需要的
  2. 只寫文件不動代碼 —— 不揀:用戶明言怕引擎唔對焦令新 session 失焦;誤導性代碼與文件一樣會帶錯方向

- 為何選這個：把「轉向」由對話記憶變成倉內三層護欄:tag 保舊貌、聲明擋誤讀、審視清誤導;引擎先行是因為引擎是所有 session 實際打交道的東西,它的形狀就是最有力的方向指示。

- **用戶原話（原文照錄）**

  > ok, I take your approach. But I want to make sure 1) UI can be lower priority to fix later. But the engine should be better reflecting the latest decision as I am afraid if the engine is not focusing on this setup. Later when a new agent take up the session, it will lose the focus and bring me back to the wrong decision.

- 影響：開 KARST-115 引擎對齊審視票(研究型,出候選清單交用戶裁);規格修訂票與各項改編/封存建置票候審視結果再開;專案自動記憶的路線圖同步改寫。

## D-058 引擎對齊全單照審視執行;現金以短期國債 ETF 代理落實(依用戶委託推出);錯殺離場治理未裁候白話解釋;「今日仲買唔買」重新核准原則收入詞彙表
- 類型：決策
- 狀態：有效
- 日期：2026-08-30

- 出處：用戶 2026-08-30 裁決與委託,原話見 quote。承 KARST-115 審視與 KARST-114 文獻兩份報告。

- 背景：審視報告列出模組、票務、規格三份清單;文獻報告交出四類注離場治理對應表。用戶對第一項答 Yes(全單照做),第二項委託技術判斷並問零息現金是否最易,第三項要求先用白話解釋再裁。同一訊息用戶另交出一條原則:持倉去留的真測試是「以最新價格你仲會唔會買入」。

- 決策：
  1. 引擎對齊照 KARST-115 建議全單執行(用戶:Yes):策略合約加兩格必填(屬三層哪一層、離場治理屬延續型注/回歸型注/規則型);封存以登記狀態格(現役/封存)落實——定義庫按設計不可刪,D-057 的「搬走或刪除」修正為:代碼可搬走,登記用狀態格,經唯一入口留痕;票務處置照審視:KARST-012/017 取消轉封存、066 量度半收檔畫面半取消、092 前提失效候改寫(改寫後重新過審批)、085 降優先、079/097 押後、100/106 升最高優先
  2. 現金形式:短期國債 ETF 代理(依用戶「I think it is easy for you」委託技術判斷推出,非逐字裁決)。理由:零息現金並非更易——引擎留白不落注已經是零息現金,顯式現金格的成本在「可持有對象」的管道而不在利息;而且零息會令現金格在量度中被系統性低估(2000–02 現金優勢 +9.6% 基本上全是利息)。代理 ETF 上市之前的歷史,由數據層以官方短期國債利率合成價格序列填補,引擎不改
  3. 錯殺一格(破產閘代價格止蝕)未裁:候用戶看過白話解釋再拍板
  4. 「持倉無記憶」原則收入詞彙表:每期換倉以「今日仲會唔會用呢個價買入」重新核准每格持倉,買入成本價不是任何訊號的輸入;引擎逐期重選本來如此,此原則同時是防處置效應的人手版(依用戶同日原話推出)

- 考慮過的替代方案：
  1. 零息現金 —— 不揀,理由見 decision 第 2 條
  2. 純現金連息 —— 不揀:要起合成對象、逐日持倉多一行、自己計息,工程量大一個量級而量度結果與代理相同

- 為何選這個：全單細或中量級、無一件大工程,而最重要那件(合約兩格必填)是全倉唯一「唔答就跑唔到」的防漂移閘——正對用戶怕新 session 走回舊方向的憂慮。

- **用戶原話（原文照錄）**

  > 1. 我建議照單全做。 <<< Yes

  > 2. 國債 ETF 代理 actually I don't know too much, but I think it is easy for you. But what about if Cash = Cash with no dividend at all? Then it is the easiest?

  > Actually I think the key I heard from some KOL or video, they said the key test is whether you will be still willing to buy the ticker at the latest price.

- 影響：開三張票:策略合約兩格必填(KARST-116)、登記狀態格與因子混合標封存(KARST-117)、規格修訂十九點(KARST-118);012/017/066 收檔或取消、092/085/079/097 留言標明處置;100/106 排隊優先派工;現金代理的具體代號與合成序列口徑在 KARST-116 之後的實作票對齊(D-038 參數對齊照舊)。

## D-059 錯殺離場治理定案(破產閘代價格止蝕);論點型注一律事件錨定——入場當日有理由、當日按該理由寫死論點死亡清單;非結構化數據按論點記錄形態處理
- 類型：決策
- 狀態：有效
- 日期：2026-08-31

- 出處：用戶 2026-08-31 裁決,原話見 quote。承 D-058 待裁一項(錯殺離場治理),用戶看過白話解釋後答 Fair,並自行擴充事件錨定一層。

- 背景：KARST-114 文獻查明:回歸型注設價格止蝕必定賣在底,但「又平又跌」的股票整體成績差(真殘風險是實的)。化解方案=破產閘。用戶接納之餘指出關鍵一環:錯殺當日必有一個理由(行業消息、業績發佈一類),論點死亡清單要在當日按那個理由定出;並點明樽頸的供需論點同款,這決定了非結構化數據該怎樣研究與處理。

- 決策：
  1. 錯殺(以及一切回歸型/論點型注)的離場治理照 KARST-114 建議落實:不設價格止蝕,設破產閘=注碼硬上限+時間閘(論點講明 N 個月內回,到期未回即走)+論點死亡清單(事實出現即走,不理價格);價格永遠不是離場理由(用戶:Fair)
  2. 事件錨定:論點型注入場當日必須有明文理由(業績發佈、行業層面消息一類事件),論點死亡清單在當日按該理由推出——不是通用範本;理由與清單同日寫死,同 D-048(前提先寫死)一條紀律(用戶:This is important for us)
  3. 樽頸同款:供需論點一樣要事件錨定+可證偽死亡條件
  4. 非結構化數據的處理形態隨之定向:不是全市場連續打分,而是圍繞每單論點開一個論點記錄(入場理由、誤會分類、死亡清單、時間閘),其後的新聞/逐字稿/財報以清單為問題去監察;落實用 D-024 已有的材料庫+判準書機制——判準書問什麼,由死亡清單決定
  5. 具體規格留待錯殺/樽頸策略票(板塊版先行,D-054)

- 考慮過的替代方案：
  1. 價格止蝕 —— 不揀:文獻證回歸型設價格止蝕必定減少預期回報(賣在底)
  2. 通用死亡清單範本 —— 不揀:用戶明令清單要按當日理由推出,理由不同清單不同

- 為何選這個：把「防真殘」由價格層搬到事實層:注碼上限保本、時間閘防論點無限期拖延、死亡清單令離場有據可依;事件錨定令每單注可覆盤,亦令非結構化管線有了清晰的問題形態——讀材料是為咗答清單,不是為讀而讀。

- **用戶原話（原文照錄）**

  > Fair and here introduced 論點死亡清單. And I think 錯殺 should have a reason on that day? Like is a industry level news, or a result release. Then we need to , at that day to determine the 論點死亡清單. This is important for us, and this also means the same for demand supply bottleneck on how should we research or handle unstructured data?

- 影響：KARST-114 對應表的錯殺格由「建議」轉「已裁」;錯殺與樽頸的策略票必含論點記錄一節(理由、分類、死亡清單、時間閘為必填欄);判準書機制的用法示範以此為首個場景;逐單覆盤成為可能(論點與死亡條件皆有落檔,事後可對答案)。

## D-060 現金形式定案:Cash == USD,以 USD 為代號、定價恆為 1、零利息;取代 D-058 的國債 ETF 代理;量度自此一律以零息現金計
- 類型：決策
- 狀態：有效
- 日期：2026-08-31

- 出處：用戶 2026-08-31 裁決,原話見 quote。用戶看過 D-058 國債 ETF 代理方案與「齋揸美元會比帳面少收利息」的提醒後,自行揀定 USD。

- 背景：D-058 依技術委託選了國債 ETF 代理,理由之一是零息會令現金格在量度中被低估。用戶知情後仍揀 USD——這其實換來一個更乾淨的性質:他實盤本來就打算齋揸美元,帳面用 USD 就令回測假設與實際執行完全一致,不再有「帳面收息、實盤冇收」的落差。

- 決策：
  1. 現金格以 USD 為代號落實:一個合成實體,價格序列恆為 1(美元計),零利息;引擎視之為普通可投資對象,不用任何特殊處理
  2. 取代 D-058 第 2 條的國債 ETF 代理;「以官方利率合成歷史序列」一併不用做
  3. 量度紀律:自此所有含現金格的量度一律以零息計,令帳面與實盤一致;既有研究報告(KARST-113 一類)的現金格數字含國債利息(例 2000–02 現金 +9.6% 基本上是利息,零息下為 0%),引用時要知道新口徑下數值會縮——已核對:三次全面熊中最好板塊皆為負數,零息現金照樣是贏家,結論次序不變,只是幅度縮
  4. 日後若用戶改為願意買短期國債 ETF 收息,只是宇宙多一隻代號,隨時加回,不用改引擎

- 考慮過的替代方案：
  1. 國債 ETF 代理(D-058 原案)—— 用戶知情後不揀;保留為日後可隨時加回的選項
  2. 純現金連息 —— 不揀,同 D-058

- 為何選這個：用戶實盤就是齋揸美元;帳面照樣計息只會令回測靚過現實。Cash==USD 令假設與執行零落差,而工程上是最細的一種(恆一序列)。

- **用戶原話（原文照錄）**

  > OK, I think then you just use USD as the ticker. So Caassh == USD.

- 影響：現金格實作隨 KARST-116/117 之後的實作票落地(USD 合成實體+恆一價格序列);KARST-113 等報告的現金格數字日後引用時註明舊口徑含息;防守格詞條更新為已裁。

## D-061 論點記錄的錨定放寬為二型:事件錨定(錯殺——當日發生咗咩事)與情景錨定(樽頸——入場時的情況快照,可在市場仍平靜時落注);死亡清單與時間閘兩型照舊必填
- 類型：決策
- 狀態：有效
- 日期：2026-08-31

- 出處：用戶 2026-08-31 修訂 D-059,原話見 quote。

- 背景：D-059 把論點型注定為事件錨定(入場當日必有明文理由)。用戶指出樽頸未必有「嗰日發生咗咩事」——樽頸的最佳入場時機可以是市場仍然平靜、或者啱啱開始轉熱之時,錨定的不是一件事,而是當下情況的一個快照。論點分類、死亡清單、時間閘三格則兩型通用。

- 決策：
  1. 論點記錄第一格由「當日事件」放寬為「入場錨定」,分二型:事件錨定(錯殺——業績、行業消息一類當日事件)/情景錨定(樽頸——入場時的情況快照:當時見到的供需缺口證據,逐項指回材料庫的材料,時間戳照蓋)
  2. 死亡清單的推法兩型一致:由錨定內容推出——事件錨定推自那件事(誤會被證實是真),情景錨定推自快照(快照裡哪幾件情況改變=論點死:新產能上線、需求轉弱、價差回落一類)
  3. 時間閘對情景錨定的注更重要,不是更不重要:沒有事件逼市場重新定價,論點對都可以等不切——早=錯;N 個月市場仍未回應即走
  4. 錯殺照 D-059 事件錨定不變;情景快照可以順帶記低入場時市場的冷熱(仍平靜/開始轉熱),供日後覆盤分辨時機模式,不作必填

- 考慮過的替代方案：樽頸都強制事件錨定 —— 不揀:會逼策略等一件未必出現的事件,錯過「市場仍平靜」的最佳入場窗

- 為何選這個：錯殺是對一件事的反應,樽頸是對一個狀態的判斷;錨定形式跟注的本質走,但「證據事前落檔、事後對得到答案」這條紀律兩型一樣咬得實。

- **用戶原話（原文照錄）**

  > 樽頸同款 may not have 嗰日發生咗咩事. But 論點分類、死亡清單 and 時間閘 could be. I think as 樽頸 we could buy at the time the market is still calm or a just the right timing it start to be warm (the best timing). so it may or may not be 嗰日發生咗咩事 But the current situation or a snapshot of situation?

- 影響：詞彙表論點記錄詞條更新為二型錨定;樽頸策略票的論點記錄一節按情景錨定寫;覆盤的三分法(論點錯/時機錯/執行錯)兩型照用。

## D-062 論點記錄的載體定形:骨架結構化落庫(經唯一入口)、日誌自由 MD 追加、格式逼出驗證;明文否決純 MD 檔做骨幹
- 類型：決策
- 狀態：有效
- 日期：2026-08-31

- 出處：用戶 2026-08-31 核准主 agent 方案(原話 ok);起因是用戶提出每單錯殺/樽頸敘事值得當一個「假設+日誌」項目管理,問好的做法。

- 背景：用戶要保證「情景內的邏輯不會漏、永遠被驗證」。主 agent 指出純 MD 項目正是舊倉 KarstETF 的死法(D-001 立項理由:MD 為骨幹難管理難擴展——沒有東西逼人回去覆核,死亡清單埋在文中三個月後無人記得);好的形是 Kira 票的形:一單論點=一張票。

- 決策：
  1. 每單論點型注一個論點記錄,兩層落實:骨架結構化落庫,經唯一入口、有版本有時間戳——錨定(事件/情景快照,D-061)、論點分類、死亡清單逐項一格各有狀態(未觸發/觸發/已覆核)、時間閘到期日、注碼上限、記錄狀態(進行中/論點死/到期/完場)
  2. 日誌自由文追加(內容格式 MD 無妨):一條條有日期、引材料庫材料;每條日誌三格必答——死亡清單各項今日狀態、有無新證據、時間閘剩餘;不答不收貨,驗證由格式逼出,不靠自律
  3. 機器守閘:時間閘到期要響、死亡清單未覆核格一眼可見、進行中論點一列可得
  4. 完場必覆盤:結果+三分法歸因(論點錯/時機錯/執行錯),積累自家命中率與錯法分佈
  5. 日後 agent 輔助:換倉日 agent 掃新材料草擬各論點死亡清單狀態、人手確認;用 D-024 材料庫+判準書機制,判準書問題=死亡清單
  6. 明文否決純 MD 檔做骨幹(重蹈 D-001 舊倉死因);MD 做內容,庫做脊骨,格式做紀律

- 考慮過的替代方案：
  1. 純 MD 項目(一單敘事一個資料夾)—— 否決:舊倉已死過一次,無機制逼覆核,正是用戶怕的 logic missed 的成因
  2. 全結構化無自由文 —— 不揀:敘事的血肉要寫得出先留得低,自由文放日誌層

- 為何選這個：用戶日日在用的 Kira 票證明了這個形行得通:假設=開票、死亡清單=驗收條件、日誌=留言、離場=關檔;把同一套紀律搬到落注,覆盤數據(命中率、錯法分佈)就是無人有的私家資產。

- **用戶原話（原文照錄）**

  > I think actually for these 錯殺 or 樽頸 as in a stock or a specific narrative. The evidence and the founding is every important. So actually every narrative of such is worth setting up like a project or a hypothesis + dairy and it is like a MD based or else. To make sure the logic within the scenarios is not missed and always validated. ... ok

- 影響：錯殺與樽頸策略票必含論點記錄一節並照此形實作;論點記錄的庫表與唯一入口支援屬該實作票範圍;介面(論點記錄檢視)照 D-057 押後。

## D-063 選股(含敘事)是唯一的策略形態;擇時從來不是策略,只是時機與訊號——否決 KARST-118 修訂版對「服侍選股,不是擇時」的重新解讀
- 類型：決策
- 狀態：有效
- 日期：2026-08-31

- 出處：用戶 2026-08-31 裁決,原話見 quote。回應 KARST-118 舉手:修訂版把 D-006 原句解讀為「排除單股擇時、組合層市況判斷升為第一層」,用戶指出這個框架本身錯了。

- 背景：KARST-118 修訂 v1 規格時,把三層架構與「Karst 服侍選股,不是擇時」的表面衝突,調和為「市況擇時已是正式的第一層」。用戶否決這個寫法:擇時由頭到尾都不是策略,無所謂「升為一層策略」;策略一律是選股(含錯殺、樽頸一類敘事),擇時只是服侍策略的時機與訊號。

- 決策：
  1. 策略(strategy)一詞收窄:只有選股/選板塊(含敘事型:錯殺、樽頸)才是策略;alpha 來自揀對對象,不來自捉市場時機
  2. 擇時(market timing)定性:時機與訊號,是服侍策略的治理層——市況層與防守階梯決定幾時可以入、幾時要退守,本身不是策略、不產生 alpha 主張
  3. D-006 原句「Karst 服侍選股,不是擇時」照字面完全成立,不需重新解讀;三層架構與它無衝突——第一層(市況)是訊號開關,不是一條策略線
  4. 規格 1.2 第 2 點按此改寫;「擇時線」一詞日後指訊號線(報信人一族),不指策略線

- 考慮過的替代方案：維持修訂版解讀(市況擇時=正式第一層策略)—— 否決:把訊號層講成策略層,正是用戶怕新 agent 走歪的那種讀法

- 為何選這個：分清「策略」與「訊號」是這個平台的骨:策略票量的是揀對幾多,訊號票量的是報信準繩度(D-049);兩者混為一談,防守階梯就會被誤建成一條擇時策略去追優化。

- **用戶原話（原文照錄）**

  > This is wrong, as I think our strategy is by stock selection (includig narratives), 擇時 is never our strategy of all, it is the timing or signal.

- 影響：v1 規格 1.2 第 2 點改寫、0.6 補一句定性;詞彙表新增擇時詞條;KARST-118 舉手就此了結。

## D-064 「無一個板塊安全」判準:持倉/資金流族與趨勢線族兩條判準齊寫死(連參數)、同一張量度票同場考五次熊市,考完只留及格那條;廣度族不入首輪
- 類型：決策
- 狀態：有效
- 日期：2026-08-31

- 出處：用戶 2026-08-31 經選項介面揀定建議項「兩族齊寫死一齊量」;三族(持倉/趨勢/廣度)已向用戶以白話解釋後才問。

- 背景：D-053 第 3 條要求「安全」判準在看數據之前寫死(10.13 缺口)。三族候選各有短板:持倉/資金流族合現行方向(D-052)但 CFTC 詳細版 2006 年起、走漏 2000–02 熊;趨勢線族文獻證據最強(KARST-114 階梯證據)且覆蓋 1999 年起五次熊全齊,但價格衍生一族在因子線已依 D-049 退役;廣度族自計但極端讀數樣本薄。

- 決策：
  1. 持倉/資金流族與趨勢線族兩條「安全」判準都先白紙黑字寫死(連具體參數),寫死動作必須在量度開跑、看結果之前完成——判準文本屬量度票第一節
  2. 同一張量度票同場比併五次熊市(2000–02、2008、2018Q4、2020、2022),考完只留及格那條入建置
  3. 價格衍生一族在板塊層重開一次,只為攞證據、不為建置——過不到訊號準繩度關(D-049)照樣淘汰,不視為推翻 D-049 在因子線的退役
  4. 廣度族不入首輪(樣本薄、多數量不出結論);日後有需要另裁

- 考慮過的替代方案：
  1. 只寫持倉/資金流族 —— 不揀:三次全面熊只得兩件樣本
  2. 只寫趨勢線族 —— 不揀:等於裁定 D-049 退役不延伸板塊層而無對照
  3. 三族全寫 —— 不揀:廣度族樣本薄,工夫多一截而多數無結論

- 為何選這個：兩條探熱針都先寫低刻度同場考一次,成本低(兩邊數據都已勘察好),趨勢線正好補住持倉族 2006 年前的盲區;「先寫死後看數」的紀律兩族一樣守住。

- **用戶原話（原文照錄）**

  > (用戶於選項介面揀)兩族齊寫死一齊量 (Recommended)

- 影響：10.13 缺口由「未裁族別」收窄為「族別已裁,判準文本待量度票開跑前寫死」;板塊線量度票即可開,判準文本一節先行。

## D-065 債券不先入防守階梯:階梯維持兩級(板塊→USD);「加債券中間級會點」在安全判準量度票順手同場量,量完有數再裁入不入
- 類型：決策
- 狀態：有效
- 日期：2026-08-31

- 出處：用戶 2026-08-31 經選項介面揀定建議項「掋住兩級,量度票順手一齊量」;用戶先問明債券風險(利率:加息跌、減息升;2022 股債齊跌之因)後才答。

- 背景：D-052 替代方案 1 與 D-053 替代方案 3 兩次記債券「未裁」(10.12 缺口)。債券做中間級實質是賭「下次熊市聯儲局會減息」:過去五次熊四次啱(2008、2020 債升股跌)、一次大錯(2022 暴力加息股債齊跌,長債 ETF 年跌三成幾)。年期長短決定利率敏感度:短債近乎有息現金,長債近乎另一隻高波動資產。

- 決策：
  1. 防守階梯現形維持兩級:板塊輪動→現金(USD),不先加級
  2. 安全判準量度票(D-064)入面順手加一隻債券 ETF 同場量:五次熊逐次睇「加了中間級好幾多、衰幾多」——數據同一批,成本極低
  3. 量完有數,先裁債券入不入階梯做中間級

- 考慮過的替代方案：
  1. 而家即刻加入中間級 —— 不揀:2022 那類加息熊未有數據支撐就入制度,違反先量後建紀律
  2. 永不加入 —— 不揀:白白放棄一個多數熊市有用的工具

- 為何選這個：未量先定形違反先量後建;但唔量就摺埋又嘥咗一件多數時候有用的工具——順手同場量是零額外成本的中間路。

- **用戶原話（原文照錄）**

  > (用戶於選項介面揀)掋住兩級,量度票順手一齊量 (Recommended)

- 影響：10.12 缺口由「未裁」轉為「先量後裁,掛在安全判準量度票」;階梯定義暫不改。

## D-066 因子棋盤接受只有傳統半邊:不買現成多因子產品補全,引用因子輪動結果時明寫「只測了傳統四風格」;D-051 該條舊數就此了結
- 類型：決策
- 狀態：有效
- 日期：2026-08-31

- 出處：用戶 2026-08-31 裁定,原話「I think ok」;之前已向用戶以白話解釋半邊棋盤何意(反面風格無現成 ETF、2020–21 反面領先時無棋可出)並建議認命了結。

- 背景：D-051 記低兩條出路未拍板:買現成多因子輪動產品(PALC 一類)補另一半,或接受半邊並明寫限制(10.11 缺口)。當日因子輪動是主力線;D-053 第 4 條已把它降級做訊號試驗場與被動預設,不作主力建置——為一張試驗枱買產品補棋盤不值。

- 決策：
  1. 接受棋盤只有傳統半邊(價值/動能/質素/低波四風格);不買現成多因子產品
  2. 日後引用因子輪動任何結果,一句明寫「只測了傳統四風格,反面風格無工具、不在樣本」
  3. D-051 該條「兩者皆未拍板」就此了結

- 考慮過的替代方案：
  1. 買現成多因子輪動產品 —— 不揀:為已降級的試驗場加新產品、新數據、新追蹤工夫,回報不對等
  2. 押後再議 —— 不揀:單純拖後,重提時要重傾一次

- 為何選這個：因子線已不是主力,試驗場用途半邊棋盤足夠;零成本零新風險。

- **用戶原話（原文照錄）**

  > I think ok

- 影響：10.11 缺口關閉;規格該節改記已裁。

## D-067 延續型與規則型的離場治理細目:文獻建議表(KARST-114)收做「預設待驗」,實際數值留到每張策略建置票的參數對齊一節逐個裁——形而家定,數開工先傾
- 類型：決策
- 狀態：有效
- 日期：2026-08-31

- 出處：用戶 2026-08-31 經選項介面揀定建議項「形而家定,數開工先傾」。

- 背景：D-056 第 3 條裁「哪類策略配哪套治理,先過文獻關再定案」;文獻票 KARST-114 已交四類注×六行治理欄位建議表,明文未經用戶裁決(10.14 缺口)。回歸型那格已裁(D-059 破產閘)。

- 決策：
  1. KARST-114 建議表收做延續型與規則型的治理預設,身份是「預設待驗」——不是已核准參數
  2. 止蝕擺位、賠率門檻、加注上限一類實際數值,留到每張策略建置票的參數對齊一節(D-038)逐個同用戶裁
  3. 10.14 缺口由「未裁」轉為「形已定、數掛建置票」

- 考慮過的替代方案：
  1. 而家逐格傾掂 —— 不揀:未有實盤票在手,磨出的數字到開工時多數要重傾
  2. 全部押後 —— 不揀:日後開策略票時又要回頭重傾一次文獻結論

- 為何選這個：與 D-038 一致:參數建置期先對齊;今日鎖形不鎖數,避免空對空磨數字。

- **用戶原話（原文照錄）**

  > (用戶於選項介面揀)形而家定,數開工先傾 (Recommended)

- 影響：規格 1.5.1 治理表可引建議表做預設待驗;各策略建置票必含治理數值對齊一節。

## D-068 趨勢波段與因子輪動(ETF 版)兩條線的舊登記一併封存:狀態旗照 KARST-117 機制、歷史留底不刪;因子輪動試驗場定位(D-053)不變,日後要用另開新登記
- 類型：決策
- 狀態：有效
- 日期：2026-08-31

- 出處：用戶 2026-08-31 裁定,原話見 quote。原題只問趨勢波段舊登記點標,用戶加碼把因子輪動(四隻因子 ETF)的過往運行一併封存。

- 背景：D-056 把趨勢波段改編制做離場治理規則庫,引擎內仍有它以策略身份留低的登記、13 組參數與歷次運行;因子輪動(ETF 版)依 D-053 為訊號試驗場、不作主力建置,但登記仍掛現役。定義庫不可刪(D-058),用戶原話「removed or you can say archived」以封存落實。

- 決策：
  1. 趨勢波段舊登記蓋封存旗,依據 D-056 改編制;13 組參數與歷次運行原封留底照查;離場規則庫日後另立新身份,不同舊帳撈亂
  2. 因子輪動(ETF 版)舊登記一併蓋封存旗;D-053 第 4 條試驗場定位不變——日後要做訊號試驗時另開新登記新運行,唔翻舊帳
  3. 已執行:2026-08-31 經唯一入口 set-status 落旗(strategy_status 簽章第 2、3 筆),全清單三條線(連因子混合)已全封存,日常清單只剩現役

- 考慮過的替代方案：
  1. 留低現狀等規則庫票一次過處理 —— 不揀:期間清單仍當趨勢波段係現役策略,同新編制對唔齊,正是用戶怕新 agent 走歪的狀態
  2. 刪除舊運行 —— 做唔到:定義庫按設計不可刪(D-058),封存已達到用戶「唔想再見到」的目的且留得低帳

- 為何選這個：帳目乾淨:清單所見即現行路線,舊帳查得返但唔阻眼。

- **用戶原話（原文照錄）**

  > To be honest, the past run on this and the 4 factor ETF should be removed or you can say archived.

- 影響：引擎/CLI 預設清單自此不見三條舊線;10.15 趨勢波段處置一格關閉;現役策略清單暫時清零,下一條現役線由板塊輪動建置票補上。

## D-069 被動預設改為揸 SPY:取代 D-053 第 4 條的「持有動能」;因子輪動(ETF 版)只餘紙上試驗場身份,四隻因子 ETF 全部無需維護
- 類型：決策
- 狀態：有效
- 日期：2026-08-31

- 出處：用戶 2026-08-31 裁定,原話「Yes」——回應主 agent 建議「後備條款改做 SPY」;起因是用戶連番質疑:動能喺全板塊冧市一樣冧(正確,文獻同向)、退路一隻就夠唔使四隻、點解唔係 SPY 更簡單。

- 背景：D-053 第 4 條留了一句後備:若全套訊號系統考試肥佬,被動揸動能。呢句係因子線年代寫低;「認命被動揸」的本意就係揸住成個市場、唔好再扮識揀,SPY 一隻嘢、無額外管理費差、無動能深冧風險。動能後備與防守階梯係兩件事:動能從不在階梯之內,熊市避難所唔關佢事。

- 決策：
  1. 被動預設(所有訊號線考試肥佬時的認命持倉)改為:被動揸 SPY
  2. D-053 第 4 條「持有動能」一句由此取代;因子輪動(ETF 版)只餘紙上訊號試驗場身份,無被動預設角色
  3. 四隻因子 ETF(價值/動能/質素/低波)自此全部無需維護、無任何現役角色;舊帳已封存(D-068)

- 考慮過的替代方案：
  1. 保留持有動能 —— 不揀:動能喺全面熊一樣冧且冧得傷,後備的本意係認命揸市場,SPY 先係自然答案
  2. 唔寫後備條款 —— 不揀:留一句寫死的認命方案,免得系統肥佬時臨場亂揀

- 為何選這個：後備的目的係「唔玩訊號時揸咩」——最簡單、最似「成個市場」的一隻就係 SPY;同時清走最後一隻要記住的因子 ETF,概念數目再減一。

- **用戶原話（原文照錄）**

  > 「被動揸 SPY」 <<< Yes

- 影響：規格 0.6 第 5 點與第 5 節因子輪動一欄改寫;用戶注意力聚焦板塊輪動與錯殺/樽頸兩條線。

## D-070 轉現金的觸發定性為資產類別層面的退守(asset-level risk-off):正形是「價格/趨勢訊號+資金流確認」雙腳制,不只是板塊輪動訊號;KARST-119 判準設計照此改形,單腳版本只作對照
- 類型：決策
- 狀態：有效
- 日期：2026-08-31

- 出處：用戶 2026-08-31 裁定,原話見 quote。回應主 agent「幾時返 USD=無一個板塊安全訊號響」的講法,用戶收窄:呢個係資產層面的 risk-off 判斷,通常要資金流一併確認。

- 背景：D-064 裁了兩族判準(持倉/資金流族、趨勢線族)齊寫死同場量,當時兩族係並列考生。用戶今次定了判準的形:全撤 USD 唔係「九個板塊逐個唔安全」加總出嚟,而係對整個股票資產類別的一次退守判斷;而呢類判斷通常要資金流(fund flow)做確認腳,唔可以齋靠板塊/價格訊號自己。

- 決策：
  1. 「無一個板塊安全→全撤 USD」的觸發屬資產類別層面的 risk-off 判斷,不是板塊層訊號的簡單加總
  2. 判準正形為雙腳制:價格/趨勢訊號一腳+資金流/持倉確認一腳,兩腳齊響先觸發;單腳版本照樣寫死照樣量,但身份係對照,唔係正選
  3. KARST-119 的判準設計一節照此改形;D-064 兩族「二揀一」的講法收窄為「雙腳合體為正形、單腳為對照」,其餘(先寫死後看數、五次熊同場考、債券順手量)不變
  4. 資金流確認腳的候選數據照 KARST-112 勘察:CFTC 資產管理人持倉、基金資金流、貨幣市場基金資產一族;覆蓋年期限制照 D-064 明寫

- 考慮過的替代方案：維持兩族二揀一 —— 用戶否決:齋靠板塊輪動/價格訊號自己去裁全撤,唔係佢心目中呢個判斷的性質

- 為何選這個：全撤現金係成個帳戶最貴的一個掣,按錯的代價係坐喺場外錯過成段升幅;要兩條互相獨立的證據鏈齊響先准撳,係同認錯成本相稱的門檻。

- **用戶原話（原文照錄）**

  > I think it should be asset level risk off. Usually need to confirm with the Fund Flow as well but not just sector rotation

- 影響：KARST-119 票面補一條裁決留言;規格 0.6 防守階梯第二級與 10.13 補寫雙腳正形;詞彙表新增資產層退守。

## D-071 持倉三態狀態機定形:風險開+有及格訊號→揸揀中對象;風險開+無及格訊號或賠率唔吸引→揸 SPY(日常預設地板);資產層退守雙腳齊響→全撤 USD。SPY 由 D-069 認命方案擴展為風險開預設
- 類型：決策
- 狀態：有效
- 日期：2026-08-31

- 出處：用戶 2026-08-31 提出並問主 agent 意見,主 agent 認同並加一條收緊(切換判準要寫死);原話見 quote。**收緊那一條(決策第 4 項)其後由用戶明確確認**(2026-08-31 原話「Yes」),自此屬用戶裁決,不再只是 agent 建議。

- 背景：用戶把幾日裁決串成完整狀態機:板塊輪動的本質係市場仍在、錢由一處搬另一處(熱板塊獲利了結但敘事仍在),唔係 risk-off,所以唔觸發撤退;真正撤去現金係資產類別層面的退守(D-070 雙腳制);而市場風險開但自家訊號無一個及格/賠率唔吸引時,應該揸 SPY 而唔係坐現金。三次轉態的認錯成本啱啱好遞增(搬板塊最平→退 SPY 中價→全撤最貴),同 D-053 防守階梯排序一致。

- 決策：
  1. 持倉狀態機三態定形:一、風險開+有及格訊號→揸揀中的板塊/個股;二、風險開+無及格訊號或賠率唔吸引→揸 SPY;三、資產層退守(D-070 雙腳齊響)→全撤 USD
  2. SPY 角色由 D-069 的「系統肥佬認命方案」擴展為「風險開之內的日常預設地板」——唔識揀就揸大市,現金只留畀資產層退守嗰格
  3. 板塊輪動確認定性:風險開之內的資金搬倉(獲利了結、敘事仍在),唔係 risk-off,唔觸發任何撤退動作——與 D-070 分層一致
  4. 「無及格訊號/賠率唔吸引」的切換判準必須白紙黑字寫死,唔准靠感覺(D-049/D-063 紀律:擇時係訊號,訊號要考試);具體數值留到板塊線建置票參數對齊(D-038)

- 考慮過的替代方案：
  1. 無及格訊號時坐現金等機會 —— 不揀:風險開之內坐現金會錯過大市慢升,認錯成本高過揸 SPY
  2. 切換掣留人手判斷 —— 不揀:會變成憑感覺擇時的後門

- 為何選這個：三態各有一個明確持倉,冇曖昧地帶;成本階梯遞增同防守階梯同構,成套制度一個邏輯講得晒。

- **用戶原話（原文照錄）**

  > so i think the whole idea of sector rotation means the market is still on going, it is only that the money moved from one thing to the other. It is usually profit take but not entire risk off. ... If the asset level wanted to risk off on stock, then we fall back to cash. Last question then when should we switch to SPY. I thinnk it is when no signal is good or the R&R is not attractive but the market is still risk on?

- 影響：規格 0.6 補三態狀態機;詞彙表新增風險開預設;板塊線建置票必含「SPY 地板切換判準」一節;KARST-119 不受影響(佢量的是第三態嗰個掣)。

## D-072 營運模式轉換:agent 主導策略成形(排程、開票、量度、實作不逐步請示);用戶轉任贊助人兼討論夥伴,保留三個把關位——判準/參數批核、每條線入紙上交易前放行、定期成績覆核;真錢落注永遠是用戶在券商的人手決定
- 類型：決策
- 狀態：有效
- 日期：2026-08-31

- 出處：用戶 2026-08-31 提出交棒,原話見 quote;主 agent 接受並加兩條護欄(大量試錯只用於參數穩健性、訊號必行先寫後看+樣本外),用戶提出時已同意 proven by backtesting 為底線。

- 背景：用戶看過 vibe-coded 產品後反思自己深度答題但感覺無進展,提出由 agent 主導策略成形、自己做 sponsor/discussion。此時作戰守則已齊(D-053/D-054/D-056/D-059–D-071 三態狀態機收官),agent 已無方向性問題要問,交棒條件成熟。

- 決策：
  1. agent 主導:排程、開票、派工、量度、引擎實作自行推進,不逐步請示;方向性新問題出現時仍先問後行
  2. 用戶三個把關位:一、判準與參數批核(agent 提案連依據,用戶一句准否——D-038/D-049 的對齊步不取消,改為 agent 主動遞案);二、每條策略線入紙上交易前的放行;三、定期成績覆核(agent 主動交數)
  3. 護欄一:大量試錯(VectorBT 一類)只用於參數穩健性掃描與既定假設的量度;禁止無假設撈訊號揀「歷史最佳形態」——訊號一律先有理由、先寫死判準、後看數據,樣本外考試先算數(D-049 紀律不因交棒鬆綁)
  4. 護欄二:所有結論以回測與打和線白紙黑字呈報,期望值講實話;回測證明的是紀律,不是保證
  5. 真金白銀落注不在本平台範圍:永遠是用戶自己在券商執行的人手決定

- 考慮過的替代方案：
  1. 維持逐步請示 —— 用戶主動放棄:密集答題期已完,樽頸在執行不在方向
  2. 全自動連判準都不批 —— 不揀:判準批核是防自欺的最後一重人手閘,保留

- 為何選這個：守則已寫齊,剩下的是執行量;agent 快在迭代,用戶貴在判斷——把判斷集中在三個真正要人的位,其餘交機器,正是整個平台的設計初衷。

- **用戶原話（原文照錄）**

  > Can I handover to you to take the lead? You can explore the way we should be doing in order to get the best strategy to earn the living of both of us. And for sure it should be proven by backtesting ... I guess it could be easier that I am the discussion and sponsor of you, but you take the lead on this stratgy forming?

- 影響：自此 agent 不再等「開工」口令,照現行路線推進(首件:KARST-119 即場派工);用戶可隨時叫停或收回主導權;決策簿照舊逐條入帳供覆核。

## D-073 估值錨成為論點記錄必填格(錯殺與樽頸兩型通用):公允區間+算法+背後假設,假設直接餵入死亡清單;不另開「均值回歸/內在價值」第三條個股線,純估值篩選歸個股層基本面加強計分材料
- 類型：決策
- 狀態：有效
- 日期：2026-08-31

- 出處：用戶 2026-08-31 提出「錯殺背後其實係內在價值,市場應有公認估值指標、公允價應有合理區間」並問是否 overfitting;主 agent 判斷為補漏非過擬,建議照此落地;用戶授權照主 agent 建議辦(原話見 quote),並明言風險自負。

- 背景：用戶指出:華爾街殺錯一隻股票、或我們認為殺錯而值得買,前提是心目中有一個公司估值。主 agent 認同:錯殺注的完整句子是「事件→大跌→市價明顯低過心目中公允價→值得買」,無估值錨講不成;用戶自己「今日這個價仲肯唔肯買」的原則(持倉無記憶)本質就是公允價測試。但文獻潑冷水:價值溢價長期存在而可連續十年跑輸;個股層「淨係因為平」就買是價值陷阱地帶(揸住的輸家平均跑輸、壞消息在跌緊的股票傳得最慢,KARST-114);公允區間閒閒哋闊三至五成,而估值假設正正是錯殺事件當日被質疑的東西——所以公允區間做不到自動買賣訊號,做得到必填紀律格。

- 決策：
  1. 論點記錄的結構化骨架(D-062)加一個必填格「估值錨」:公允區間、用什麼方法算(倍數/現金流折現/同業比較一類)、建基於哪幾個關鍵假設
  2. 估值錨的關鍵假設直接餵入死亡清單:某假設崩=公允價冧=論點死,逐項一格照 D-062 有狀態可覆核
  3. 不另開「均值回歸/內在價值」第三條個股策略線:純粹低過公允價就買=接落刀,拆走破產閘護欄,否決
  4. 純估值篩選(全市場搵平貨)歸位:個股層「基本面加強」計分材料(D-054 已有位置),不是獨立注型
  5. 「今日這個價仲肯唔肯買」測試自此有操作化定義:市價對照論點記錄內的估值錨區間

- 考慮過的替代方案：
  1. 開第三條均值回歸線 —— 否決:文獻上個股層無事件無論點的「平就買」正是價值陷阱,且與 D-059 破產閘設計相沖
  2. 估值錨做選填 —— 不揀:選填等於無;無估值錨的錯殺論點根本不成立,必填先逼得出紀律

- 為何選這個：把「憑估值買」的直覺保留,同時逼它寫出假設、接受覆核——直覺變成可證偽的紀律,正是全平台的形。

- **用戶原話（原文照錄）**

  > I think you investment knowledge is more than me, while I will for sure own my risk on trading. Given that, I want to know your advice

- 影響：詞彙表新增估值錨、論點記錄詞條更新;規格論點記錄相關段落補必填格;錯殺/樽頸策略票的論點記錄實作(10.15)按此加欄。

## D-074 倍數拆解入制度:價格變動拆成盈利變動×倍數變動;錯殺的操作化偵測=倍數壓縮對盈利下修的比較(倍數無郁=不是錯殺不要接);行業倍數趨勢列為板塊層計分材料候選,照舊要過訊號考試;forward 盈利預測滯後入知情滯後處理
- 類型：決策
- 狀態：有效
- 日期：2026-08-31

- 出處：用戶 2026-08-31 提出方向問題(公允價之外應否計入市場情緒/承認趨勢,industry PE 或 forward P/E 趨勢是否比 K 線更值得看);主 agent 依 D-072 主導權採納並定位,原話見 quote。

- 背景：價格=盈利×倍數:股價跌只有兩個來源——盈利(預期)跌,或市場肯畀的倍數跌;後者才是情緒。K 線把兩者混在一起,倍數趨勢把它們拆開。對錯殺注:事件後跌幅遠大於盈利預期下修幅度=倍數壓縮=過度反應,錯殺候選;跌幅與下修幅度相稱=市場照事實計數,不是錯殺。冷水三盤:分析員預測出名慢手(與壞消息傳播慢同源),事件初期 forward P/E 分母失真;倍數趨勢有慣性但作為訊號無特權,一樣先寫判準後看數據過打和線;行業層 forward P/E 歷史序列免費來源有限,要先勘察。

- 決策：
  1. 錯殺論點記錄的操作化偵測寫死:比較「股價跌幅」對「盈利預期下修幅度」,差額=倍數壓縮;倍數無壓縮的下跌不是錯殺,不接——此測試與估值錨(D-073)扣連,屬錯殺策略票實作範圍
  2. 行業倍數趨勢(P/E、forward P/E 的時間序列)列為板塊層計分材料候選;板塊計分設計時與其他候選同場考,無免試特權(D-049 紀律)
  3. forward 盈利預測的更新滯後照知情滯後處理:事件後初期的 forward P/E 失真要在任何用它的判準內明文處理
  4. K 線不棄用:K 線答幾時(執行層),倍數答點解(論點層),互補不取代
  5. 行業層倍數歷史數據來源勘察列入待辦(免費來源有限,先勘察後承諾)

- 考慮過的替代方案：
  1. 以倍數趨勢取代 K 線做主要視角 —— 不揀:兩者答不同問題,且倍數數據頻率低、分母滯後,執行層仍需價格
  2. 倍數趨勢即時入板塊訊號 —— 不揀:未考試,照 D-049 排隊

- 為何選這個：把「市場情緒」由一個講法變成一條可以量的數(倍數),令錯殺的「殺錯」二字第一次有得客觀檢驗;同時唔俾一個啱聽的概念繞過考試制度。

- **用戶原話（原文照錄）**

  > should we actually factor in the market "emo" on this fair value and admit that there is a trend? What I mean is that instead of looking at the K chat for the stock or the industry, we should be more interested to PE or Forward P/E trend of the industry?

- 影響：錯殺策略票的論點記錄實作加此偵測;板塊計分材料候選清單記此一項;數據勘察待辦一項;詞彙表新增倍數拆解。

## D-075 KARST-119 結果收案:三條「無板塊安全」判準全部不及格,全撤現金掣不入建置(D-049 紀律);三態機第三態暫無自動掣,報信人狀態只顯示不落閘;債券原則入階梯須帶自身趨勢濾網、落實押後,現行兩級不變
- 類型：決策
- 狀態：有效
- 日期：2026-08-31

- 出處：量度結果 KARST-119(research/2026-08-31-板塊安全判準與債券中間級.md);主 agent 依 D-072 主導權定案。用戶未逐字覆「照辦」,但隨即提出以貪恐框架取代失敗判準的新方向(D-076),即接受舊判準不建;債券押後無異議。**其後用戶已追認**(2026-08-31 原話「Yes I think it is ok.」,見 D-078 第 4 項)。

- 背景：三判準(趨勢單腳/持倉單腳/雙腳正形)五熊同場考:精確度 40.0%/22.7%/20.0%,對打和精確度 46.0% 全部不及格;響後大市平均 +1.84%/+2.04%/+5.89%——量的都是「已經冧咗幾多」,響時已近底部。雙腳制把 44 次噪音壓到 5 次但兩腳一齊遲到。債券:2008 +20.5%、2022 −15.1%;無濾網三級 2022 多蝕 5.87 個百分點;用十個月線做債券自身濾網,2008 全放行、2022 全拒絕,兩次都判啱。

- 決策：
  1. 三條判準一條不入建置;10.13 缺口由「待量」轉「已量、量不出」
  2. 三態機第三態(全撤 USD)暫無自動掣:平台顯示報信人狀態,不自動落閘;日後新候選判準另開票先寫後考
  3. 債券:原則入階梯、必須帶自身趨勢濾網;落實押後至有及格總開關;D-065 兩級現形不變
  4. 持倉族只考了「機構在撤」方向;相反方向(擁擠即危險)未考,屬 D-076 貪恐框架範圍,判準另行事前寫死

- 考慮過的替代方案：調鬆判準令其及格 —— 否決:考試制度存在的意義正是擋這一步

- 為何選這個：不及格不建是 D-049 立下的鐵律;這次它第一次在真金白銀的掣上發揮作用——三條判準若建成,歷史上會反覆在底部叫人離場。

- **用戶原話（原文照錄）**

  > (用戶未直接批示;其後原話)Actually this also applies, all I want to say is about the fear and greek concept here?

- 影響：規格 10.13 改記結果;KARST-119 已關;接任方向見 D-076。

## D-076 貪恐對稱框架立為總開關接任方向:退守時機=FOMO 蔓延(領漲板塊+一定比例板塊同時過熱),撈底時機=恐慌極端(領漲板塊急縮/全市場恐懼);貪恐兩半分開評分,退守目的地 SPY 與 USD 兩變體都量;日/週尺度考,判準先寫死
- 類型：決策
- 狀態：有效
- 日期：2026-08-31

- 出處：用戶 2026-08-31 提出,原話見 quote;主 agent 認同方向並加三條收緊(兩半分開評分——文獻上買恐懼強過賣貪婪;RSI2 一族屬日級尺度,照反應型訊號原則在短周期考;判準文本照舊先寫死先接觸數據)。**其後用戶已追認**(2026-08-31 原話「Yes I think it is ok.」,見 D-078 第 4 項)。

- 背景：KARST-119 三判準敗因是「量已發生的損毀」,響時近底;用戶隨即把方向反轉——不等冧完先走,而是在過熱時走、恐慌時買,結構上由滯後改領先,正是量度報告點名未考的「擁擠即危險」方向。文獻提醒:貪的一半歷史上最弱(過熱可以持續數月,見貪即走會提早離場成年計),恐的一半較強(恐慌極端短而尖),所以必須分開評分,可以一半及格一半不及格。

- 決策：
  1. 貪半判準形:動能/領漲板塊帶頭,以短窗擺盪指標(RSI2/RSI5 一族)偵測 FOMO;FOMO 蔓延至一定比例板塊=退守訊號;退守目的地 SPY 與 USD 兩個變體都量
  2. 恐半判準形:領漲板塊急速重估(如倍數/價格 RSI2 極低)=個別撈底候選;全市場恐懼=黃金撈底候選
  3. 尺度:日/週(反應型訊號原則——恐慌極端衰減快,月度看不見);與月度板塊輪動線分層並行,不互相取代
  4. 貪恐兩半獨立評分,各對打和精確度型基準;判準連參數先寫死先 commit 先接觸結果數據
  5. 倍數版本(以倍數代價格做擺盪指標輸入)候補:待倍數數據勘察(D-077)有結果後補考;首輪用價格版

- 考慮過的替代方案：繼續在「損毀量度」族內找新判準 —— 不揀:敗因是結構性滯後,同族再考大概率同病

- 為何選這個：把開關由「事後確認冧市」改為「事前偵測過熱與恐慌」,方向上正面回應了 KARST-119 的失敗機制;但領先型訊號誤報天生多,考試門檻一分不減。

- **用戶原話（原文照錄）**

  > the timing to 全撤現金 should actually be majority of the market sector is under fomo, and the timing to buy should be the market sector is under fear? ... if all the momentum + the related sector (or a certain percentage of sector are under fomo, actually we should be leaving or change back to more defensive like SPY holding. Later when the momentum sector is revaluation sharply, like if the multiple is under RSI2 < 5. We can consider to dip buy again. And if the whole market is fear, then we should golden dip buy?

- 影響：開考試票並派工;及格的一半先入建置,不及格照樣落檔。

## D-077 倍數情緒儀立為正式策略假設:以倍數(按分母階梯指定)代替價格做情緒量度——剝走事實淨計情緒、以歷史倍數區間做錨;每個投資對象必須指定「市場實際用緊的分母」(前瞻市盈率/市銷率/滲透數學);命門是 point-in-time 預測數據,先勘察後承諾
- 類型：決策
- 狀態：有效
- 日期：2026-08-31

- 出處：用戶 2026-08-31 連番討論收斂(倍數圖=市場情緒、TA 可施於倍數、分母階梯要應用),主 agent 依 D-072 採納定形;用戶原話見 quote。**其後用戶已追認**(2026-08-31 原話「Yes I think it is ok.」,見 D-078 第 4 項)。

- 背景：價格圖=事實+情緒混合;倍數圖=剝走事實的淨情緒,回歸目標是「市場歷史上肯畀的倍數區間」而非舊價格——價格版均值回歸接落刀的死因(盈利真冧)倍數版天生免疫。三個限制:分母滯後(事件初期錨最不準,要疊證據流);錨會結構性漂移(公司成熟令合理倍數搬家,不是情緒);短窗兩圖等價(倍數優勢在中長窗)。分母階梯:有穩定盈利用前瞻市盈率、未有盈利用市銷率、營收未成形用滲透數學;用錯級數的倍數圖無意義。

- 決策：
  1. 倍數情緒儀立為正式假設:對指定分母的倍數序列施以區間錨+擺盪指標,量情緒偏離;與倍數拆解(D-074)扣連分辨盈利冧/情緒冧
  2. 分母階梯入制度:每個投資對象(個股/板塊)指定其定價分母,為估值錨與倍數圖層的必答格
  3. 先決條件:point-in-time 預測數據勘察(冇當時知道的預測,只有事後修正版,回測即前視)——勘察票先行,結果決定倍數層做到幾深幾遠
  4. 一切倍數基規則照舊過考試先入建置;首階段倍數層做貪恐框架(D-076)的候補輸入與錯殺偵測(D-074)的落地件

- 考慮過的替代方案：直接用事後修正版預測數據起倍數層 —— 否決:前視,回測會講大話

- 為何選這個：有機制故事的假設(情緒有錨、可分解、可證偽)天生及格率高過無機制的圖形;但數據誠實是它的地基,先查地基後起樓。

- **用戶原話（原文照錄）**

  > I think we will need to apply this consideration? And all in all, do you think in this way we might finnd a better trading strategy based on mulitple based TA?

- 影響：開倍數數據勘察票並派工;詞彙表新增分母階梯;板塊計分與離場治理設計把倍數基候選列入同考名單。

## D-078 分母指定邏輯由 agent 制定(市場用低級只因高級用不到,規則可推);級數轉換接駁位容忍細微不連續——產品是連續圖,重點是趨勢不是絕對水平,板塊層尤其;倍數圖 TA 候選庫立案(SMC/RSI/均線形態)留待數據勘察後開考
- 類型：決策
- 狀態：有效
- 日期：2026-08-31

- 出處：用戶 2026-08-31 裁決,原話見 quote;同一訊息追認 D-075/D-076/D-077 落地與兩張在途票(「Yes I think it is ok.」)。

- 背景：D-077 立分母階梯後,剩一個執行問題:每隻股/每個板塊用邊個分母,係咪要逐個問用戶。用戶裁明唔使——市場用低級數只係因為高級數用唔到(無盈利先用市銷率),所以指定規則可以機械推出;而級數轉換(如公司轉盈由市銷率升級做前瞻市盈率)的接駁位有細微不連續唔緊要,因為倍數圖的用途係睇趨勢,唔係睇絕對水平,板塊層更加係。

- 決策：
  1. 分母指定規則由 agent 依階梯機械制定:有穩定盈利→前瞻市盈率;無盈利但營收成形→EV/Sales;營收未成形→滲透數學;唔使逐個對象問用戶
  2. 級數轉換接駁位容忍細微不連續;倍數圖一切用法以趨勢為主,絕對水平不作跨級比較
  3. 倍數圖 TA 候選庫立案:SMC(Smart Money Concepts)、RSI 一族、均線形態(多頭排列、金叉死叉)——用戶明示有興趣測倍數圖上的均值回歸/趨勢 TA;留待倍數數據勘察(KARST-121)有結果後另開考試票,照舊判準先寫死、過打和線先入建置
  4. 追認:D-075(KARST-119 收案)、D-076(貪恐對稱)、D-077(倍數情緒儀)及 KARST-120/121 派工,用戶批示照辦

- 考慮過的替代方案：逐個對象問用戶指定分母 —— 否決:規則可推,問=浪費把關位

- 為何選這個：把關位要留給判準與成績,不是留給機械可推的指定;候選庫先立案後開考,防止勘察回報後散失方向。

- **用戶原話（原文照錄）**

  > I think this is not something difficult for you. As you mentioned, the market use the lower tier is only because the higher is not applicable. So actually I think you can fform the logic of which stock should use which. And minor stitch is not actually matter as the product should be a continuous plot, the key is always the trend, especially when it is a sector level consideration ... I am actually interest to test the multiple chart with mean reveral/trend TA. I think the result can be interesting. potential is SMC, RSI, and Moving Average pattern (e.g. 多頭排列, or 金叉死叉). But yes we can check later. ... Yes I think it is ok.

- 影響：分母指定規則寫入日後倍數層實作票;候選庫在勘察票回報後轉考試票;三項決定的署名升級為用戶裁決。

## D-079 KARST-120 收案:貪恐對稱開關價格版兩半皆不及格——貪半帶反向資訊整族收檔;恐半有料但不過值博線不入建置;恐慌極端重新定位為「風險開之內加注時機」候選另開考試;退守目的地一問已答(現金每格最差,D-069 SPY 預設不改)
- 類型：決策
- 狀態：有效
- 日期：2026-08-31

- 出處：量度結果 KARST-120(research/2026-08-31-貪恐對稱開關.md);主 agent 依 D-072 主導權定案,成績留用戶覆核。判準先寫死 commit 5944006 早於結果 commit fd6a230,時序可證。

- 背景：27 年日線,響後 21 個交易日評分,打和精確度 46.2%、跌月基礎率 35.2%。貪半(FOMO 蔓延退守):主副兩組響 207/129 次,精確度 29.0%/27.1% 低過基礎率——報「危險」之後大市平均反而升 0.90%/0.94%,85% 訊號響在熊市外;2020-03-26 見底後三日響一次,之後 +14.91%。三目的地:繼續持有 +0.97% > 轉 SPY +0.90% > 轉現金 0.00%。恐半(恐慌極端撈底):個別撈底/黃金撈底響 103/80 次,響後 +1.16%/+1.45%,精確度過基礎率,但超額 +0.53/+0.65 點不足事前寫死的 1.00 點值博線;一季窗超額 +1.22/+1.78 點過得到,但主窗事前寫死 21 日,事後改窗=作弊,無做。關鍵發現:恐半熊外(+2.00%)賺多過熊內,2008 個別撈底 8 次平均蝕 4.77%(領漲板塊已換防守股,撈=接刀);2020 黃金撈底門檻寫死 5.0、極端讀數最低 6.38,差 1.38 點一次未響。

- 決策：
  1. 貪半(FOMO 蔓延退守)整族收檔,不入建置,不開變體票——精確度低過基礎率即帶反向資訊,唔係參數問題係方向問題
  2. 恐半不入建置——過賺錢關與有資訊關,倒在事前寫死的值博線;窗長不事後改,考試紀律優先
  3. 恐慌極端重新定位:總開關係擺錯位,正位係「風險開之內的加注/入場時機」(熊外賺多過熊內、熊內撈底=接刀、錯誤成本在風險開內最平);另開票重考,判準事前寫死,百分位門檻與一季窗兩個選擇受本輪結果知情要明寫、證據力打折、值博線相應從嚴
  4. D-076 遺留一問(退守目的地 SPY 定 USD)以數據答畢:現金每格最差,D-069 被動預設 SPY 不變
  5. 總開關(全撤 USD)維持 D-075 現狀:無自動掣,平台只顯示報信人狀態

- 考慮過的替代方案：改用一季窗令恐半及格 —— 否決:事後改窗=作弊,考試制度存在的意義正是擋這一步

- 為何選這個：兩半分開評分(D-076)正是為了容許一半死一半留;貪半死於方向、恐半死於幅度,前者收檔後者換位重考,各得其所。

- **用戶原話（原文照錄）**

  > (用戶未批示,成績覆核待用戶;文獻預期「貪半最弱」已於派工前向用戶預告)

- 影響：開恐慌重定位考試票並派工;貪半方向自此不再立票;規格 0.6 開關一節按此補記(留待與 KARST-121 結果一併改)。

## D-080 自建 ETF 倍數用頭十大持倉加總近似即可;ETF 候選池擴闊範圍,入池門檻兩條:長期向上(月/年線視角)+成交額門檻,具體數值留參數對齊
- 類型：決策
- 狀態：有效
- 日期：2026-08-31

- 出處：用戶 2026-08-31 裁決,原話見 quote。

- 背景：細分主題 ETF(DRAM、MAGS 一類)現成倍數序列不存在,要自建——逐隻成份股計倍數按持倉加總。用戶裁定唔使全持倉,頭十大已足夠;並定下 ETF 候選池的方向:範圍要分散,入池兩條門檻。細分主題注的定位維持 D-079 前一輪討論所講:個股/敘事層,逐主題寫論點記錄、指定分母、掛估值錨與死亡清單,倍數圖做入場時機與監察工具,不做向後回測計分池(今日贏家主題向後砌圖=倖存者偏差)。

- 決策：
  1. 自建 ETF 倍數:頭十大持倉加總近似即可;加總數學照「成籃市值 ÷ 成籃盈利」,唔係逐隻市盈率求平均;報告須同場記低頭十大佔淨值覆蓋率,覆蓋率明顯偏低的 ETF 要註明近似誤差(此句為 agent 補充的執行細則)
  2. ETF 候選池:範圍擴闊、分散主題;入池門檻兩條——(1) 長期向上:月/年線視角整體向上;(2) 成交額門檻:流動性不足不入池
  3. 兩條門檻的具體數值(幾多期月線、成交額幾多)未裁,留策略建置票的參數對齊一節(D-038 慣例)逐個裁
  4. 門檻用途是前瞻性入池篩選(紙上交易起計),不得用作向後回測的池——向後套用「長期向上」即內嵌倖存者偏差,舊數據上考訊號照用固定基準池

- 考慮過的替代方案：全持倉加總 —— 用戶裁定唔使:主題 ETF 持倉集中,頭十大已覆蓋大部分權重,邊際精度不值邊際成本

- 為何選這個：近似制換取覆蓋面,配覆蓋率註記守住誠實;入池門檻前瞻用、不回測用,一條線把倖存者偏差擋在池外。

- **用戶原話（原文照錄）**

  > Yes, I think in any event, if we need to form the multiple ourselves, use top10 holdings should be good enough ... I think we will try to diverse the scope of ETF. As long as the ETF overall is 長期向上 from month or year pov. And the ETF should have a threshold of 成交額 as well is my plan

- 影響：個股層倍數工具的實作票須含頭十大加總件;候選池門檻數值入日後參數對齊清單。

## D-081 修訂 D-080:「長期向上」剔出 ETF 入池門檻,入池門檻剩成交額一條;趨勢判斷歸訊號層,不在池門口重複
- 類型：決策
- 狀態：有效
- 日期：2026-08-31

- 出處：用戶 2026-08-31 裁決,原話見 quote(回應 agent 指出「長期向上」門檻向後套用即內嵌倖存者偏差)。

- 背景：D-080 原定入池兩條門檻(長期向上+成交額)。agent 提出向後回測不得用「長期向上」篩池(攞今日仲向上的 ETF 砌返轉頭=倖存者偏差),用戶隨即裁定整條剔除——不只回測不用,前瞻入池都不用。效果:池只管流動性,夠唔夠買得順手;一隻 ETF 而家升定跌、值唔值得入,由訊號層(輪動線、倍數圖、論點記錄)話事,池門口不重複判斷。

- 決策：
  1. ETF 入池門檻剩一條:成交額(流動性),具體數值照舊留參數對齊(D-038 慣例)
  2. 「長期向上」不作入池門檻,前瞻與回測一律不用;D-080 第 2、4 項中該門檻相應失效,其餘不變(頭十大加總、覆蓋率註記、前瞻/回測池分界照舊)

- 考慮過的替代方案：只限回測不用、前瞻照用 —— 用戶裁定整條剔除,趨勢判斷不屬池門口

- 為何選這個：池答「買唔買得順手」,訊號答「而家買唔買」——兩個問題分開答,門檻先唔會同訊號打架。

- **用戶原話（原文照錄）**

  > yes, remove 「長期向上」

- 影響：候選池定義簡化;參數對齊清單剩成交額一項。

## D-082 票冊清理:未關 13 張逐張覆核——7 張依轉向廢票(012/017/066/092/100/101/106)、1 張孤兒收成關檔(079)、3 張留開(085/097/099)、2 張在途(121/122);V1 藍圖 Epic 隨之完結;前路寫入 HANDOFF.md 供新 session 起手
- 類型：決策
- 狀態：有效
- 日期：2026-08-31

- 出處：用戶 2026-08-31 指令,原話見 quote;逐張裁廢由主 agent 依 D-072 執行,每張的依據寫在該票結果一節。

- 背景：轉向(D-052–057 三層路線、D-063 選股唯一策略形態、D-068 三舊策略封存、介面押後)之後,票冊仍留 13 張未關,其中大半前提已消失,對新 session 構成誤導。廢票用 Cancelled 形(closed + cancelReason),驗收條件不剔,構想未推翻的明寫重啟時另開新票;做完未關的孤兒票(079,驗收全剔、舉手已答)照收成關檔。

- 決策：
  1. 廢票 7 張:012 名家組合倒推(藍圖期構想不在 v1)、017 人物判官(敘事改由論點記錄承載)、066 因子 IC 面板(計算件已交,畫面依因子線封存+介面押後)、092 趨勢波段搬執行台(策略已封存 D-068)、100 因子測試協議(因子矩陣路線封存,紀律改由考試票慣例承載,通用版另開 KARST-123)、101 組合回報尺(源自已封存路線,尺通用、重啟另開)、106 訊號準繩度關卡(已由考試票紀律取代)
  2. 收成關檔 1 張:079 策略詳情一頁四段(2026-08-29 做完,驗收全剔,agent 已消失,孤兒認領照關)
  3. 留開 3 張:085 代號切段取價(個股層數據地基,backlog)、097 策略詳情頁實作(設計已定稿,押後至首條現役策略有真批次)、099 快照說明檔判定(backlog)
  4. V1 藍圖 Epic 全部票已關,Epic 完結;現行工作全歸 V1 建置
  5. 前路交接寫入倉根 HANDOFF.md:現況、在途、下一步隊列、用戶把關位;新 session 起手先讀它與規格開頭轉向聲明

- 考慮過的替代方案：全部留開等日後逐張處理 —— 否決:前提已消失的票留喺度就係誤導,正是用戶叫清理的原因

- 為何選這個：票冊要反映而家真實的工作面;廢票不刪檔、寫明依據與重啟路徑,歷史照查得到。

- **用戶原話（原文照錄）**

  > from now. It seems we are moving into a better way. Please help to review the epic and ticket of the repo. Remove the invaid. And plan forward on the task as such next agent wont lost

- 影響：未關票由 13 張收到 5 張(3 留開+2 在途);HANDOFF.md 成為新 session 起手正本之一。

## D-083 KARST-122 收案:恐慌極端「風險開之內加注」兩組皆不及格且超額為負,定位一併收檔;情緒族(貪恐)三連敗後暫停開票;兩條紀律入帳——情緒族日後考試須事前寫死樣本外對象(SPDR 日線已四票重用),濾網關之內撈底線索記入候選庫不即開
- 類型：決策
- 狀態：有效
- 日期：2026-08-31

- 出處：量度結果 KARST-122(research/2026-08-31-恐慌極端重定位.md);主 agent 依 D-072 定案,成績留用戶覆核。判準 commit ef4fc5d 早於結果 commit e4176c6,判準零修訂。

- 背景：主成績(十個月線濾網開、五熊窗外,4,699 個交易日,一季窗):全市場恐慌買 SPY 31 次,響後 +2.85% 對基礎率 +3.19%,超額 −0.35 點;領漲板塊恐慌買該板塊 25 次,+2.88% 對 +3.15%,超額 −0.28 點。兩組在有資訊關已失守(精確度低過基礎率),值博線不用動用。機制解讀:十個月線濾網本身已經賺走恐慌反彈嗰筆錢——濾網開之內的恐慌係淺坑,冇額外著數。副窗 21 日更差。2008 濾網關時撈底一季平均 −10.06%(接刀再確認);2020 年 3 月黃金撈底照舊零次響。A-020(恐慌極端正位在風險開之內)已記 overturned。殘餘線索:濾網關之內主組 9 次一季超額 +9.10 點(約 2.5 倍標準誤)——即熊市之內的極端恐慌撈底;惟樣本極細、屬事後發現、且同一批數據已被 KARST-119/120/122 及日線價格快照多票重用,量度 agent 明文不當它及格。

- 決策：
  1. 恐慌極端「風險開之內加注時機」定位收檔,不入建置——超額為負係方向問題,唔係參數問題
  2. 情緒族(貪恐框架)三連敗(KARST-119 損毀型、KARST-120 對稱開關、KARST-122 重定位)後暫停:不再開同族考試票,除非新票帶全新樣本外對象
  3. 紀律一:日後情緒/擇時類考試票,判準一節除參數外必須事前寫死樣本外對象(另一市場/另一資產/另一時段),同一批 SPDR 日線唔准再做唯一考場
  4. 紀律二:「濾網關之內極端恐慌撈底」記入候選庫,不即開票;若日後重啟,必須事前寫死並以樣本外對象為主考場,本輪 +9.10 點只可當方向提示、不可當證據
  5. 下一步重心照路線圖轉去板塊計分設計(風險開之內揸邊個板塊),唔再喺開關族打轉

- 考慮過的替代方案：即開「濾網關內撈底」考試票 —— 否決:事後發現+樣本 9 次+數據重用,而家開票等於用同一份數據考自己出嘅題

- 為何選這個：三張考試三次擋住劣品,制度運作正常;但同一批數據反覆考落去,遲早考出一個假及格——暫停與樣本外紀律係對制度本身嘅保養。

- **用戶原話（原文照錄）**

  > (用戶未批示,成績覆核待用戶)

- 影響：KARST-122 已關;A-020 overturned;考試協議正本(KARST-123)須收錄樣本外對象紀律;HANDOFF.md 記情緒族暫停。

## D-084 KARST-121 收案:倍數層數據路線裁定——免費三步走(即日起每日存檔 SPDR 前瞻市盈率、EDGAR 自砌行業後顧倍數 2009 年起、網頁存檔+Estimize 補前瞻);收費選項留用戶裁;誠實回測邊界入帳:板塊倍數最遠 2009 年,考不到 2008 與 2000 兩隻熊
- 類型：決策
- 狀態：有效
- 日期：2026-08-31

- 出處：量度結果 KARST-121(research/2026-08-31-倍數數據勘察.md,27 個來源逐源明判 point-in-time);主 agent 依 D-072 定案;涉及畀錢與開帳戶的項明確留用戶。

- 背景：勘察答齊三問:(一) 板塊層後顧倍數用 SEC EDGAR 自砌(申報自帶日期=真 point-in-time,全免費)最遠誠實回測到 2009 年;前瞻倍數群眾共識到 2012、賣方共識存檔只有 2015 年起且斷纜。(二) 個股層 0 元自砌 2009 年起,或 Sharadar 39 美元/月買到 1998 年起逐日、含約 12,000 隻已除牌;前瞻要 Estimize(免費索取)或賣方共識 1,250 美元/月。(三) 標普官方行業盈利試算表經實測 4,486 格零差異可當 point-in-time,但 2026 年 1 月已停刊,只剩網頁存檔。一個坑:Polygon 一類「來自 SEC 申報」的來源,重述會覆蓋原件並冠較後申報日期,「來自申報」不等於 as-reported。

- 決策：
  1. 即日起建每日存檔件:每日抓九隻 SPDR + SPY 的前瞻市盈率落 append-only 存檔,記抓取時間戳——唯一一條不畀錢就會隨時間變成資產的路,遲一日蝕一日;開票即派
  2. 板塊層後顧倍數走 EDGAR 自砌路線,以標普/Yardeni 網頁存檔雙重驗證;建置票待板塊計分設計定案後開(免得砌完先發現計分唔用)
  3. 誠實回測邊界入帳:倍數基判準的考試最遠 2009 年,五熊只覆蓋 2018Q4/2020/2022 三隻,2008 與 2000 考不到——一切倍數基考試結論永遠帶此腳註,不得外推到未考過的熊形
  4. 收費項留用戶裁:Sharadar 39 美元/月(個股層 1998 年起)建議暫緩至個股層倍數工程實際開工先決定;Estimize 帳戶屬開帳戶行為,必須用戶親手辦,暫不急
  5. 重述覆蓋原件的來源(Polygon 一型)禁用於倍數 vintage 用途,列入報告內名單

- 考慮過的替代方案：等板塊計分定案先開始存檔 —— 否決:存檔件成本極低而數據唔等人,計分用唔用倍數都唔蝕

- 為何選這個：免費路線已足夠開展板塊層;錢留到證明咗價值先畀,符合用戶做 sponsor 的分工。

- **用戶原話（原文照錄）**

  > (用戶未批示;收費兩項待用戶,見 decision 第 4 項)

- 影響：開每日存檔件票並派工;EDGAR 建置票入 HANDOFF 隊列;KARST-121 已關;詞彙表已新增「數據版本存檔/vintage」(勘察 agent 落檔)。
