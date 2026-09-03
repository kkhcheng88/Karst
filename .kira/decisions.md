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

## D-085 KARST-123 收案:docs/考試協議.md 立為考試正本(六節,159 行);三份先例十三處做法不一逐處裁定;訊噪倍數由固定 2.0 改為隨同族已測組數上升的 k(M) 公式(HLZ 一路,情緒族 M=9 → k≈2.77,重現 D-083 對殘餘線索的否決)
- 類型：決策
- 狀態：有效
- 日期：2026-08-31

- 出處：KARST-123 交付(docs/考試協議.md,commit fe7b98e);主 agent 依 D-072 收案。裁定細節與新規/先例對照表在文件附錄。

- 背景：三張考試票之間本身有十三處做法不一,最要緊四處已裁:基礎率母體照 KARST-122(收窄到與訊號同一母體,否則熊市混入令超額失真);打和精確度立為及格關(照 KARST-120);第三關一律用雙重值博線(幅度+訊噪),不再拿策略成績當報信準繩度及格關;樣本外紀律(第五節)係新規,三票一票都未做過。多重測試門檻選 Harvey/Liu/Zhu(門檻隨已測數目上升),否決縮減夏普因輸入交不出(考試票不畫淨值、每族限兩組估不出變異數);縮減夏普留給參數穩健性掃描票。

- 決策：
  1. docs/考試協議.md 為一切訊號/判準類考試的正本;日後考試票派工指令引它,不再逐張重抄紀律
  2. 訊噪值博線改用 k(M) = clamp(Φ⁻¹(1−0.05/(2M)), 2.0, 3.0),M 為同族歷來參與判定的判準組總數——同一族考得愈多,門檻自動愈高
  3. 情緒族現時 M=9,k≈2.77;此公式套 KARST-122 殘餘線索(2.5 倍標準誤)不過關,與 D-083 收案一致——公式重現先例裁決,不是另立新線
  4. 協議引用的兩篇文獻(HLZ、Bailey-LdP)本輪未能連線核對,文件只錄 DOI/SSRN 編號與核心結論、無未核實數字;日後首次有人引用其表格數字前須先核對原文

- 考慮過的替代方案：維持每票各自為政 —— 否決:十三處不一已證同一制度三票走樣,冇正本遲早考出假及格

- 為何選這個：制度成文先鎖得住;門檻隨測試次數自動收緊,係對「同一批數據反覆考」呢個結構風險的機械防線,唔靠自律。

- **用戶原話（原文照錄）**

  > (用戶未批示;協議屬 D-072 授權內的內部品管正本,成績覆核照舊留用戶)

- 影響：KARST-123 已關;考試協議入 CONTEXT.md 詞彙表;HANDOFF 開工規矩一節指向協議正本。

## D-086 KARST-124 收案:板塊倍數每日存檔件上線,「每日一跑」自此係營運日課;抓取範圍係十二隻超集(SPY+十一隻 SPDR,多咗 XLRE/XLC——漏抄補不回而多抄成本為零);回測對齊用發行商自報截數日不是抓取日
- 類型：決策
- 狀態：有效
- 日期：2026-08-31

- 出處：KARST-124 交付(commit 31e10ae/dba9ff3);主 agent 依 D-072 收案。

- 背景：首次實抓 2026-08-31 零失敗:十二隻 ETF 各八格估值欄位(前瞻市盈率 FY1、後顧市盈率、市現率、市帳率、盈利增長預估等)落 append-only 存檔 vintage/sector-multiples/readings.csv(入 git);同日重跑冪等驗過;發行商自報截數日 2026-08-28,知情滯後 T+1。首批前瞻市盈率讀數:XLK 26.03、XLI 25.37、XLY 23.42、SPY 21.36、XLV 20.41、XLP 20.16、XLB 18.29、XLU 17.74、XLF 16.21、XLC 12.88、XLE 12.53(XLRE 36.05 屬房託口徑另計)。假設 A-021 已記:發行商 FY1 口徑不會靜靜改;若為假,自儲序列會有查不出的斷點。

- 決策：
  1. 每日一跑成為營運日課,命令:PYTHONUTF8=1 之下 python -m karst.gateway multiples capture(在倉根跑);同日重跑安全
  2. 抓取範圍定為十二隻超集,不收窄——多儲兩隻板塊成本零,日後要用補不回
  3. 存檔序列的時間軸一律用發行商截數日,不用抓取日;斷纜響亮失敗、不寫空值(已有測試)
  4. 排程自動化未做:現階段靠 session 日課人手跑;日後接排程另開票

- 考慮過的替代方案：只抓票面點名十隻 —— 交付 agent 已裁超集並在票面講明,收案照准

- 為何選這個：前瞻分母推導不到、只能實時累積(D-084);儲多兩隻的成本係零,漏儲的代價係永久。

- **用戶原話（原文照錄）**

  > (用戶未批示;屬 D-084 第 1 項的落實收案)

- 影響：KARST-124 已關;HANDOFF 日課一句更新;自家前瞻倍數 vintage 自此逐日累積。

## D-087 板塊層優先次序補裁:先做行業 ETF 線(現行主線不變);富途 262 板塊「自砌倍數回測」立為後續候選線,先決條件係 API 攞唔攞到歷史基本面(勘察緊)
- 類型：決策
- 狀態：有效
- 日期：2026-08-31

- 出處：用戶裁決(2026-08-31,見原話)。

- 背景：OpenD 接通後實抓富途美股板塊全清單:行業板塊 145 個(分類穩定、估值介面支援)、概念/主題板塊 117 個(人手策展、無時點版本,只可前瞻用)——已落檔 research/2026-08-31-富途美股板塊清單.md。用戶見清單後表示想喺呢批板塊上自砌倍數做回測,但確認行業 ETF 線先行。

- 決策：
  1. 優先次序不變:行業 ETF 線(SPDR 每日存檔+EDGAR 自砌後顧倍數)先行,照 HANDOFF 隊列——板塊計分設計係下一站
  2. 富途板塊自砌倍數回測立為候選線:按板塊成分股自下而上砌板塊倍數(砌法照 D-080 加總原則),回測宇宙優先用行業板塊(分類穩定);概念板塊因成分無時點版本,回測用途受限
  3. 呢條線的先決條件:富途 API 有冇歷史基本面/共識數據砌得返以前的倍數——正是 KARST-125 勘察緊的問題,勘察返齊先知做唔做得成
  4. 開票時機:勘察收案+板塊計分設計定案之後;暫不開票,記入 HANDOFF 隊列

- 考慮過的替代方案：即刻開票做富途板塊回測 —— 唔啱:API 歷史深度未核實,開咗都係空票

- 為何選這個：用戶明確定序;而自砌倍數回測做唔做得成完全取決於歷史數據攞唔攞到,先勘察後開票係 D-084 同一紀律。

- **用戶原話（原文照錄）**

  > actually if API support, I would like to backtest on these list by forming the multiple ourselves. But yes, do the industry ETF first

- 影響：HANDOFF 隊列第 2 項補一句;板塊層數據材料由 SPDR 十二隻擴闊到富途 145 個行業板塊(粒度細一個層級)的可能性入了路線圖。

## D-088 ETF 範圍暫不擴闊(用戶裁決):驗證倍數假設期間,宇宙維持十二隻超集(SPY+十一隻 SPDR);iShares 細分行業 ETF 與富途板塊線全部押後,先證假設再擴器皿
- 類型：決策
- 狀態：有效
- 日期：2026-08-31

- 出處：用戶裁決(2026-08-31,見原話)。

- 背景：同日先後傾過 iShares 行業 ETF(SOXX 一類,只公開後顧倍數,定位入池材料)與富途 262 板塊(D-087 後續候選線)。用戶裁定暫時唔加 ETF 範圍,集中證明倍數情緒儀假設本身。

- 決策：
  1. 板塊層驗證宇宙鎖定現有十二隻(SPY+十一隻 SPDR)——每日存檔件、板塊計分設計、EDGAR 自砌全部以此為範圍
  2. iShares 細分行業 ETF、富途板塊自砌倍數回測(D-087)一律押後:假設證得成先講擴闊
  3. D-087 的先決條件不變,只是排序更後

- 考慮過的替代方案：同步擴 iShares/富途細分層 —— 用戶否決:未證假設先擴範圍係本末倒置

- 為何選這個：先用最平、數據最齊嘅十一個板塊證明「倍數講唔講到板塊層嘅嘢」;證得成,擴到細分層先有意義。

- **用戶原話（原文照錄）**

  > ok. I think I rather not adding the scope of ETF for now. So to proof our hypothesis.

- 影響：板塊計分設計票範圍收窄、更快可以開;HANDOFF 隊列次序不變。

## D-089 板塊倍數路線定案:一律自砌(主 agent 依 D-072 定案;用戶表態傾向自砌後交棒)——聚合口徑自控(離群值處理、加權、負盈利成員點算),富途官方 plate_value 降格為對照線,不入判準;自砌原料用邊條線(富途成分股日頻/EDGAR 申報)與深歷史點處理,留 KARST-126 方案稿出選項候批
- 類型：決策
- 狀態：有效
- 日期：2026-09-01

- 出處：主 agent 依 D-072 定案;用戶先表態傾向自砌、隨即講明交主 agent 決定(2026-09-01,兩句原話見 quote)。承 A-022 成立、A-023 推翻(KARST-125 查證)。

- 背景：查證證實富途官方行業均值無倖存者偏差但聚合口徑失真(負盈利成員整隻剔走、無離群值控制,困境期讀數失真)。主 agent 匯報後用戶表態傾向自砌並交棒,主 agent 採納自砌——與 A-023 善後方向一致。

- 決策：
  1. 板塊層倍數一律自行由成分股聚合,口徑自控自文檔;官方 plate_value 只准做對照與抽查,不准直接入判準
  2. 自砌口徑細節(加權法、離群值處理、負盈利成員點算)屬 KARST-126 方案稿的設計位,出選項連建議候批
  3. 深歷史張力照三線並列交裁:富途成分股自砌(日頻但除牌股查唔到)、EDGAR 自砌(2009 起含除牌股)、官方線只作方向對照

- 考慮過的替代方案：直接用官方 plate_value 水平 —— 已由 A-023 推翻;用官方線淨睇趨勢方向 —— 降為對照用途,不入判準

- 為何選這個：自砌先控制得住口徑;管理成本反而低——出事時知道係邊個環節,官方黑盒斷估。

- **用戶原話（原文照錄）**

  > great. actually I think we form it ourselves could be easier to manage / but I think up to you. You leading

- 影響：KARST-126 數據材料一節改以自砌為正路;A-023 善後方向由建議升格為裁定。

## D-090 板塊計分 gate-1 批核第一批:動能雙窗口(主 12-1、副 12-7 兩組齊考)與持倉闊度(三隻等權)用戶已批;族別歸屬新立「板塊輪動族」(主 agent 定案);資金流處置押後,待實測富途有冇 ETF 申贖流原料(用戶反問觸發)
- 類型：決策
- 狀態：有效
- 日期：2026-09-01

- 出處：用戶經選項介面批核兩項(2026-09-01,原話見 quote);族別屬考試記帳方法,主 agent 依 D-072 定案;方案正本 research/2026-08-31-板塊計分設計方案.md(KARST-126)。

- 背景：方案書呈交後用戶先追問三件:係咪已經在組策略(答:未,係先寫死判準、考試證有冇 edge 嘅題目紙,與用戶「先證明有 edge」的要求同一方向);RSI/MA/SMC 去咗邊(答:候選庫照在,第一輪先考最樸素嘅相對強度);「族」係咪第二隻策略(答:唔係,係考試防作弊嘅記帳分組,三層一套策略不變)。釐清後逐項批核。

- 決策：
  1. 動能窗口:主組「過去 12 個月跳最近 1 個月」、副組「第 12 至第 7 個月」,兩組齊考,用盡每族主+副配額,禁止事後加組(用戶批)
  2. 持倉闊度:被考規則定為「每月月底重算,揸最強三隻等權;收不到貨整注退 SPY(D-071 地板)」(用戶批)
  3. 族別:新立「板塊輪動族」,唔併入趨勢族——考的對象(板塊橫向比較)與趨勢族(大市擇時)唔同,誠實分類,非為門檻低(主 agent 定案)
  4. 資金流:未裁。用戶反問富途 OpenAPI 是否有原料(印象中只見 AUM/市值),已派實測:富途做唔做到 ETF 申贖流歷史;實測結果返嚟先裁「唔入計分但儲原料/搵到歷史即刻考/完全唔要」三選一
  5. 方案其餘建議(倍數只做極端否決閘、月度重算、門檻閘合成)用戶未逐項表態,未算已批;連同資金流一併在下一輪收尾

- 考慮過的替代方案：持倉闊度主+副兩個都考 —— 配額已被窗口用盡,同族唔准第三組

- 為何選這個：gate-1 逐項落鎖先開得考試票;族別分類影響及格門檻,誠實分類要留痕。

- **用戶原話（原文照錄）**

  > 主 12-1、副 12-7 兩組齊考 (Recommended) / 三隻等權 (Recommended) / I think you are forming the strategy already? But should we first prove if the approach like RSI or MA or SMC has edge first / But it is 2 layer from top to bottom? But not 2 strategy? / FUTU OPENAPI don't have??? it seems AUM or Marketcap only?

- 影響：考試票的參數形狀鎖了兩個位;資金流一問變成實測任務;KARST-126 方案書進入逐項批核中。

## D-091 板塊計分 gate-1 收案:判準定稿。資金流入考(用戶批——動能考完隨即開資金流考試票,數據路用 A-024 反推線);其餘設計位照方案定案(主 agent 依 D-072):倍數只做極端否決閘(材料照 D-089 自砌,EDGAR 建成先考)、月度重算、門檻閘合成、揸三隻等權收不到貨退 SPY;考試次序:動能→資金流→倍數閘
- 類型：決策
- 狀態：有效
- 日期：2026-09-01

- 出處：用戶經選項介面批核資金流入考(2026-09-01,原話見 quote);其餘未逐項表態的設計位由主 agent 依 D-072 照 KARST-126 方案建議定案。方案正本 research/2026-08-31-板塊計分設計方案.md;批核紀錄承 D-090。

- 背景：資金流原先因免費歷史缺貨而擬押後;實測(A-024,已查證成立)證明富途可反推 ETF 申贖流二十年月頻歷史,限制消失,用戶隨即批入考。

- 決策：
  1. 板塊計分判準至此定稿:動能主菜(主 12-1、副 12-7)+ 倍數極端否決閘 + 月度重算 + 最強三隻等權 + 收不到貨整注退 SPY(D-071 地板)
  2. 考試次序鎖定:第一考動能(即開票);第二考資金流(動能收案後隨即開,月頻申贖流,反向方向,數據路=前復權成交量÷換手率);第三考倍數否決閘(等 EDGAR 自砌件建成)
  3. 三張考各自判準先寫死先 commit,照 docs/考試協議.md 正本;族別同記板塊輪動族,門檻隨已測組數自動遞升
  4. SSGA 每日自儲在外股數暫不加抓——申贖流歷史已有富途反推線,自儲只餘日頻精度與即日性兩個窄用途,月度節奏用不着;日後真要日頻先補

- 考慮過的替代方案：資金流押後(原方案建議)—— 已被 A-024 實測推翻前提,用戶改批入考

- 為何選這個：判準齊備而數據路全通,不開考就係拖;次序動能先行係因為佢係主菜、數據最熟。

- **用戶原話（原文照錄）**

  > 入考:動能考完隨即開資金流考試票 (Recommended)

- 影響：KARST-126 方案全數落鎖;動能考試票隨本決策開出;HANDOFF 隊列第 1 項改寫。

## D-092 KARST-127 收案:板塊動能主副兩組齊不及格——年化超額僅 +0.75pp(主 12-1)/+1.83pp(副 12-7),訊噪 0.17/0.40 遠低門檻 k(2)=2.24,死因係幅度本身不夠而非多重測試門檻;結構發現:超額全住 2000-2012 與熊窗,2013 後歸零倒輸;板塊輪動族 M=2 入帳,資金流考照 D-091 次序即開
- 類型：決策
- 狀態：有效
- 日期：2026-09-01

- 出處：KARST-127 交付(判準 commit 153c6a0 早於結果 commit 47dbca7 七分鐘,時序證據成立);主 agent 依 D-072 收案。

- 背景：量度範圍 2000-01 至 2026-07 共 319 個完整持有月,九隻 SPDR(無 XLRE/XLC 面板)對揸 SPY 含息基線,扣 10 個基點成本。主組過方向/資訊/次數三關,幅度與訊噪不過;副組幅度過,訊噪不過(月均超額 0.142pp 對門檻要求 0.81pp;配對 t 值 1.12,連協議下限 k=2.0 都不過)。

- 決策：
  1. 板塊動能計分(主副兩組)不及格,照協議落檔;KARST-126 方案的主菜落榜
  2. 副組(12-7)每一格都勝主組(12-1)——與方案建議相反、與 Novy-Marx 同向;照協議只作方向提示,不作及格
  3. 「動能超額全住熊窗」(2022 熊窗贏 15.76pp,熊窗以外 258 個月年化輸 1.83pp)入候選庫不開票:防守職能已有十月線在做,與 D-083 對恐慌線的結論同型——貴價防守掣,唔係選板塊線
  4. 板塊輪動族已測組數 M=2 入帳,下次同族兩組考試門檻 k(4)≈2.50,照協議自動遞升
  5. 三個判準缺口記於報告未核實清單:面板無 XLRE/XLC、樣本外只做到時段切割、三隻等權打和準繩度未計
  6. 資金流考(文獻量級最實)照 D-091 鎖定次序隨即開票;若資金流亦不及格,板塊層計分設計回爐並重上 gate-1

- 考慮過的替代方案：放寬窗口或加組再考 —— 協議禁止事後加組;幅度本身不夠,加組救不了

- 為何選這個：文獻早已預告呢個可能(行業動能的賺錢機制住在行業內部,ETF 買不到);誠實預期寫明「考出嚟係零係完全可能」,而家兌現咗——制度擋住劣品係正常運作。

- **用戶原話（原文照錄）**

  > (用戶未批示;屬 D-072 授權內收案,成績覆核照舊留用戶)

- 影響：KARST-127 已關;板塊層第一條主菜證僞;計分設計的最終形態取決於資金流考結果。

## D-093 KARST-125 收案:季度「公布前共識」做得成——yfinance get_earnings_dates 定為季度 PIT 前瞻分母來源,誠實深度至 2002 年(每股最多 100 季),Wayback 逐格對數改寫率 2.8%;富途業績頁質素最高但任一刻只見約 9 個月且條款禁程式化抓取;defeatbeta 無預測表兼屬 Yahoo 轉包剔出候選
- 類型：決策
- 狀態：有效
- 日期：2026-09-01

- 出處：KARST-125 三線勘察交付(富途業績頁跨公布日對照、defeatbeta 實裝實跑、yfinance 三組證據互證含 Wayback 142 格對數與當時新聞 4 格吻合);主 agent 依 D-072 收案。

- 背景：倍數情緒儀(D-077/D-084)後顧分母 EDGAR 自砌只到 2009 年;本勘察補的係季度頻率 point-in-time 前瞻分母一格——比每日存檔粗但歷史深且免費。

- 決策：
  1. 季度 PIT 前瞻分母定源 yfinance get_earnings_dates:2002 年起、約九成七乾淨而非保證乾淨(唯一乾淨反例 CROX 2021Q4);拆股重的股票舊季度精度已毀(NVDA 2017 預測今日存為 0.03);ETF 一格都無——板塊層要成分股逐隻夾
  2. 富途業績網頁不做程式化抓取(用戶協議明文禁止,勘察已停手);其質素(標普共識、公布即凍結)只作方法論對照
  3. 富途 OpenAPI plate-stocks 的 forward_value(授權接口、即日快照、無日期參數)列為每日存檔件的個股/細分行業級擴充候選,開唔開工等倍數儀設計定案先裁;主題板塊明文 no_data
  4. defeatbeta 剔出共識源候選:17 張表零預測欄,且資料集係 yahoo-finance-data 轉包,不能用來與 yfinance 互相對數
  5. 日後凡用 yfinance 估計數,必按報告兩個陷阱核對:欄位次序造成的假改寫(標籤與值錯開一季)、拆股造成的假差異(比預測/實際兩個比率先分得出單位變動)

- 考慮過的替代方案：買 Sharadar/Estimize 先有 PIT 保證 —— 收費兩問已擺低等用戶裁,免費線先行

- 為何選這個：三線逐條實證有明判,收尾一句answered「做得成、用邊個源、歷史幾深」,達票面驗收;2.8% 改寫率與精度陷阱已量化,可帶腳註使用。

- **用戶原話（原文照錄）**

  > (用戶未批示;屬 D-072 授權內收案,成績覆核照舊留用戶)

- 影響：倍數情緒儀分母設計多一條 2002 年起的季度前瞻線,神諭版上限考(HANDOFF 隊列 2)與 EDGAR 自砌票規格可直接引用;D-087 富途板塊自砌線的歷史基本面判項亦有據——valuation/detail 三十年序列係今日數回頭重算、非版本存檔,該線開票時要照此定位。

## D-094 KARST-128 收案:板塊申贖流反向計分主副兩組齊不及格(主 1 個月流年化 −1.27pp;副 3 個月流 +2.30pp 但訊噪 0.36 遠低門檻 2.50)——深層死因係數據:富途反推線 2020-01 之前係凍結分母,真流歷史只六年半,本線判「量不出」而非「冇用」;D-091 不加 SSGA 自儲的前提被推翻,即開每日在外股數存檔件;動能+資金流齊落榜,板塊計分設計回爐重上 gate-1
- 類型：決策
- 狀態：有效
- 日期：2026-09-01

- 出處：KARST-128 交付(判準 commit 6ef494c 01:20:52 早於首次取數 01:21:54,結果 commit f36e2ee,判準自提交後無修訂);主 agent 依 D-072 收案。

- 背景：評分期 171 個月(判準機械規則定出),九隻 SPDR 對揸 SPY 含息,扣 10bp,k(4)=2.50。副組方向/資訊/幅度三關過,訊噪不過;樣本外段同樣不過。順向臂對照:追資金流入年化輸大市 2.8–5.4pp,反向方向本身成立。

- 決策：
  1. 申贖流反向計分主副兩組不及格,照協議落檔;連同 KARST-127,板塊計分方案兩道主菜齊落榜
  2. 深層死因係數據不係假設:富途換手率 2020-01 之前用固定股數(九隻 ETF 反推在外單位數六至八年紋絲不動),評分期頭八年排名由捨入塵埃驅動;剔走該段只剩 78 個月,不夠 120 個月次數關——本線判「量不出」,長歷史(自儲累積或收費源)到位先可再考
  3. A-025(富途反推線全期可用)判 overturned、A-024 補年代邊界,考官已寫入假設冊
  4. D-091「唔加 SSGA 在外股數自儲」嘅前提(富途後門存在)被今次硬證據推翻——即開 KARST-130 每日在外股數存檔件,與 D-086 倍數存檔同型,遲一日蝕一日
  5. 板塊輪動族已測組數 M=4 入帳,下次同族兩組考試門檻 k(6)≈2.64,照協議遞升
  6. 候選庫備註不開票:反向組合喺跌市明顯抗跌(2022 主組 −0.44% 對 SPY −12.43%)、升市跟唔上——性質似防守持倉多過資訊訊號,與動能考「超額全住熊窗」同型;月 K 對日 K 口徑差留畀日後票,判準已寫死唔准掉轉
  7. 兌現 D-092 承諾:板塊層計分設計回爐——等 KARST-129 死因診斷(含窗口全掃敏感度圖)返嚟,連同兩份成績單一次過重上 gate-1 畀用戶裁

- 考慮過的替代方案：用 2020-02 起真流段照判 —— 只 78 個月不夠次數關,考官已試,結論不變且不及格

- 為何選這個：判準先行時序證據成立;唔及格照落檔係制度正常運作;「量不出」與「冇用」分開記,免日後錯殺一條文獻最實嘅線。

- **用戶原話（原文照錄）**

  > (用戶未批示;屬 D-072 授權內收案,成績覆核照舊留用戶)

- 影響：KARST-128 已關;板塊層兩條免費材料線(動能、資金流)證僞或量不出,計分設計最終形態待診斷結果與用戶 gate-1;KARST-130 開站後,在外股數歷史由 2026-09 起逐日累積。

## D-095 全組合掃描升格為探索期常規工具(用戶裁決):指定用 vectorBT 跑齊參數組合出全景圖,判讀標準係「平原定孤峰」——孤峰當運氣棄,鄰域穩健嘅平原先入候選;掃描結果仍係提示唔係成績,正式及格照考試協議另考
- 類型：決策
- 狀態：有效
- 日期：2026-09-01

- 出處：用戶對「一直不跑齊全組合係刻意」嘅回應;主 agent 按裁決落實。

- 背景：動能(D-092)同資金流(D-094)兩考齊落榜,計分設計回爐中;用戶定調:而家仲係 trial and error 階段,唔輕易放棄一條線,提示係好起點。

- 決策：
  1. 全組合掃描由「只准診斷用」升格為探索期常規工具:每條線回爐或起新線之前,先用向量化全掃出全景圖攞提示
  2. 判讀標準寫死:孤峰(鄰域參數一改就冧)當運氣,唔入候選;平原(相鄰一片組合都企得住)先算真提示,入候選庫
  3. 工具指定 vectorBT(用戶點名;機上已裝 1.1.0)
  4. 界線不變:掃描出嚟係提示與候選,唔係成績;要成成績必須照考試協議另開考試票,預先寫死判準,族內門檻照 M 遞升——呢條協議正本冇被推翻
  5. 即時應用:KARST-129 窗口掃描改用 vectorBT 實作,月粒度全掃之外加週粒度形成窗,報告必答「平原定孤峰」

- 考慮過的替代方案：維持只考預先寫死兩組、唔做全掃 —— 用戶明言唔想咁保守,試錯期要提示

- 為何選這個：用戶指出重點:怕嘅係孤峰,唔係掃描本身;答案若係一片平原,全掃正正係最有效攞提示嘅方法。

- **用戶原話（原文照錄）**

  > But I think if the answer is not a 孤峰 but it is actually very helpful as if we are still just trial and error for now only. As if we won't giveup easily. Having hints are the good starting point actually. So I want you to use VectorBT

- 影響：探索速度快好多(一個腳本一次過睇齊全景),而假發現風險由「孤峰唔入候選+考試協議把關」兩重閘接住;KARST-129 派工即時更新。

## D-096 判生死改制(用戶裁決):預選兩組落榜只等於「嗰兩點唔得」,不准再判「成條線死」;線嘅生死由 vectorBT 全景圖判——搵到非孤峰、道理講得通嘅平原,嗰度大概就係答案;次序倒轉為「先全景圖攞提示、後喺未見過嘅時段/場地正式驗證」;D-092/D-094 判詞相應收窄;考試協議加第七節正本更新
- 類型：決策
- 狀態：有效
- 日期：2026-09-01

- 出處：用戶對兩考齊落榜嘅回應(承 D-095);主 agent 按裁決修訂協議並落實。

- 背景：舊制:每考預先寫死主副兩組,落榜即當一條線證僞。用戶指出:兩點覆蓋唔到成個參數面,喺佢眼中同隨機揀無異;逐次重考又浪費時間 token。KARST-127/128 兩張落榜判詞受影響。

- 決策：
  1. 廢除「兩點定生死」:兩組考試落榜嘅判詞只可以講「嗰兩組參數唔得」,唔准講「條線死」;線嘅死刑要全景圖顯示無任何講得通嘅平原先判得出
  2. 生死判據三件套:非孤峰(鄰域一片組合企得住嘅平原)+ 道理講得通(有經濟/行為解釋,唔係純數字靚)+ 喺佢未見過嘅時段或場地企得住
  3. 次序倒轉:新線或回爐線一律先跑 vectorBT 全景圖(探索票)攞提示,先至定正式判準;正式考試嘅主判場改為全景圖未見過嘅時段/市場/資產——因為平原係喺見過嘅數據搵出嚟,同一批數據自己讚自己唔算數
  4. 全景圖唔逐格計入 4.3 嘅 M(否則門檻爆表,制度自廢);代價改由兩樣嘢承擔:考試必帶知情聲明,且樣本外主判唔可以豁免
  5. D-092 判詞收窄:動能線只證咗 12-1 同 12-7 兩點唔得,線嘅生死等 KARST-129 全景圖;D-094 判詞收窄:資金流線只證咗 1 個月/3 個月兩點唔得,兼且數據唔夠,等自儲數據夠量再判
  6. 唔靠逐次人手叫重考:一張探索票一次過掃齊成個參數面,唔好擠牙膏
  7. docs/考試協議.md 加第七節(全景圖探索閘)作正本更新,引 D-095/D-096

- 考慮過的替代方案：維持兩點定生死 —— 用戶明言不能接受;統計上亦確實只證得嗰兩點

- 為何選這個：誠實記低一句:嗰兩組唔係隨機——12-1 係經典動能、12-7 係 Novy-Marx、1/3 個月流係文獻常用窗;但用戶重點成立:兩點覆蓋唔到成個參數面,判唔到成條線嘅生死。新制用「平原+道理+未見過場地」三件套換走「兩點」,假發現風險冇放鬆,判詞反而更準確。

- **用戶原話（原文照錄）**

  > yes. as to be honest, if we do in the way like choosing only 2 option, ffailed and then saying it is failed I can't accept. as if the 2 option you choose is random at first to me. If 2 random parameter failed = strategy failed then I can't accept. And then if I ask for retry and rerun actually is wasting time and token, and also it is just trial and error. But if vectorBT can find out the answer which is not a 孤峰. And if the reasoning making sense, then it is properly the answer

- 影響：探索流程由「文獻揀兩點→考→落榜即死」改為「全景圖→平原+道理→未見過場地驗證」;KARST-129 已照新制執行中;兩張已收案判詞讀法即時收窄,決策簿以本條為準,原文不改。

## D-097 KARST-129 收案+按 D-096 新制判板塊動能線:vectorBT 122 格全景圖有真平原(形成窗約十一個月,跨月/週兩種粒度、兩種跳空互證)但高度唔夠——平原平均 +0.76pp、最高 t 僅 1.81,低過 122 格純噪音應有嘅最高水位,離 k(4)≈2.50 更遠;呢個規則形狀(月底調倉、揸三隻等權、SPDR ETF)下動能線判死,死因判詞係「結構存在但太細」而唔係「無結構」;用戶假設前半成立(相對單邊中位 8.8 個月確實短過 12 個月窗)、後半方向相反(買入時已掉頭嗰批之後一個月反而較好);月度板塊相對走勢係回吐唔係延續,「短窗反轉」方向入候選庫
- 類型：決策
- 狀態：有效
- 日期：2026-09-01

- 出處：KARST-129 交付(結果 commit b9979c2、關檔 956484e;五項驗收由關檔閘獨立核過;vectorBT 與手寫向量化對數最大差 0.009pp、m12-1 格逐位重現 KARST-127 主組,機器可信;生產庫雜湊不變)。主 agent 依 D-072 收案,並依 D-096 補判線嘅生死——診斷報告按舊制寫成,本條係新制判詞正本。

- 背景：D-096 定明:線嘅死刑要全景圖顯示先判得出。今次 122 格(月粒度 1–12×跳空 0/1;週粒度 2–52×跳空 0/4;調倉維持月底)係板塊輪動族第一張全景圖;唯一 |t|≥2 嘅格係 w8-4 嘅 −2.41,即全表最似訊號嗰格係一個虧損。

- 決策：
  1. KARST-129 收案關檔;票面五項驗收齊,加項(全掃)照 D-095 用 vectorBT 完成
  2. 按 D-096 三件套判:平原有(非孤峰✓)、道理有(經典動能✓)、但高度唔夠用——板塊動能線喺「月底調倉、揸三隻等權、SPDR ETF」呢個規則形狀下死刑成立,判詞係「結構存在但太細,唔夠付成本同噪音」;呢個死刑有全景圖撐,唔再係兩點推論
  3. 用戶假設判詞記低:前半成立(15% 門檻下相對單邊中位 8.8 個月,短過 12 個月窗;板塊之間差七倍),後半方向相反(六格對照全同向:買入時短窗已向下嗰批之後一個月反而較好)——「已掉頭先買」唔係死因,月度尺度嘅板塊相對走勢係回吐唔係延續,呢個亦解釋咗 12-7 每格勝 12-1
  4. 「約十一個月形成窗」平原入候選庫存檔,不得宣稱及格;佢嘅意義係話俾人聽考過嗰兩點已經係全景最高處,唔存在「揀錯點屈死條線」
  5. 「短窗反轉」(w8-4 反面)入候選庫做新方向提示;開探索票前必須先過文獻關(板塊/行業層短期反轉文獻結論與量級,照 2026-08-29 用戶明令),而且要記低 Moskowitz-Grinblatt 行業動能喺一個月窗係正嘅——同我哋 ETF 面板相反,呢個矛盾本身就係探索票要答嘅嘢
  6. 板塊計分設計正式回爐:兩道主菜判詞齊(動能=結構太細判死;資金流=數據唔夠判量不出),下一步方向以 gate-1 問用戶

- 考慮過的替代方案：照舊制維持 D-092 判詞唔補判 —— D-096 已改制,有全景圖而唔用佢判生死係自相矛盾

- 為何選這個：全景圖令死刑判詞由「兩點唔得」升級為「成個參數面最高嘅平原都唔夠高」,正係 D-096 要求嘅證據形狀;診斷同時產出兩個候選(十一個月平原、短窗反轉)示範咗「落榜都有收穫」。

- **用戶原話（原文照錄）**

  > (用戶未批示;屬 D-072 授權內收案;D-096 新制係用戶裁決,判詞係按該裁決執行)

- 影響：板塊輪動族現況:動能死(全景圖級判詞)、資金流等自儲數據(KARST-130 開站中)、倍數閘等 EDGAR 自砌;板塊層下一步方向留用戶裁。

## D-098 板塊層下一步(用戶裁決+一句推出):短窗反轉探索開票;技術指標候選庫(RSI/SMC/均線,D-078)一併入板塊層探索隊列——RSI/均線用新制全景圖並行掃,SMC 因無機械定義暫不入掃描;均線擇時格已由市況層十月線佔住,板塊層只考橫截面揀板塊用法
- 類型：決策
- 狀態：有效
- 日期：2026-09-01

- 出處：gate-1 回爐選項問答:用戶揀「短窗反轉探索(建議)」並問「But we still have those RSI, SMC and MA those signal aren't we?」;後半屬依用戶一句推出,不是明文指令。

- 背景：動能線全景圖判死(D-097)、資金流判量不出等自儲(D-094)之後,板塊層要新材料;技術指標候選庫係 D-078 早已記低嘅存貨,一直未考。

- 決策：
  1. 開 KARST-131 短窗反轉全景圖探索票:文獻先行(必須正面處理 Moskowitz-Grinblatt 行業動能一個月窗係正、與我哋 ETF 面板相反嘅矛盾),再照協議第七節用 vectorBT 一次過掃齊反向短窗參數面
  2. 開 KARST-132 RSI/均線橫截面全景圖探索票:文獻先行,再掃 RSI 回望×門檻、均線組合×價格對均線距離等橫截面排名用法,動能讀法同反轉讀法兩個方向都掃
  3. SMC 暫不入掃描:佢冇公認機械定義,掃唔到亦冇文獻量級可先行交代;RSI/均線有平原先值得開定義票處理 SMC,原因寫入票面
  4. 界線:均線做開關/擇時嗰格已由市況層十月線佔住(D-071),板塊層票唔准重考同一樣嘢,只考「邊個板塊」嘅橫截面用法
  5. 兩張並行,同用現有 SPDR 面板;數據重用次數照協議第五節記入報告;探索票唔產生及格,一切入候選庫

- 考慮過的替代方案：淨做短窗反轉一張 —— 用戶主動問起技術指標存貨,一併掃成本低而且答咗佢條問題

- 為何選這個：用戶問嗰句係提醒:候選庫有存貨未清;新制全掃啱啱好係清呢批存貨最平嘅方法。

- **用戶原話（原文照錄）**

  > 短窗反轉探索(建議), But we still have those RSI, SMC and MA those signal aren't we?

- 影響：板塊層探索隊列由一條變三條材料線(反轉、RSI、均線),全部行新制「全景圖→平原+道理→未見過場地驗證」;倍數線同個股層次序不變。

## D-099 板塊層主線定位覆正(用戶點出):核心假設係倍數(D-077 正式假設——以倍數代價格量情緒),價格類線(動能/反轉/RSI 均線)只係「數據先就緒」嘅先頭部隊,唔係主菜;神諭版上限考即開——神諭分母明文唔需要時點數據,今日重建版盈利即刻用得,唔使等 EDGAR 自砌;EDGAR 建置與收費數據兩問等神諭結果先裁;恐半全景圖排隊喺兩張跑緊掃描之後
- 類型：決策
- 狀態：有效
- 日期：2026-09-01

- 出處：用戶 2026-09-01 兩句:糾正板塊層定位(原話一),及要求恐半掃描計劃(原話二);主 agent 依 D-072 落實。

- 背景：板塊計分價格類材料連敗(動能判死 D-097、資金流量不出 D-094、反轉/RSI 均線掃緊),用戶提醒本策略核心假設係倍數;而神諭版上限考(2026-08-31 用戶方向,HANDOFF 隊列 2)有一個一直未用嘅便利:神諭版用事後真實盈利做完美分母,明文唔需要 point-in-time 數據,所以今日已有嘅重建版盈利源(defeatbeta ttm_eps 1993 年起、yfinance 實際 EPS 2002 年起)即刻用得,唔使等 EDGAR 自砌件。

- 決策：
  1. 板塊層主線覆正為倍數線;價格類掃描照跑(成本已付、結果照收),但定位係外圍材料
  2. 即開 KARST-133 板塊倍數神諭版上限考(探索票,照協議第七節):上限都冇平原=成條倍數線收檔,Sharadar/Estimize 一蚊都唔使買;上限有料先裁 EDGAR 建置與收費數據
  3. 神諭票必須誠實處理倖存者偏差(板塊盈利用邊批成分砌)——方向明判或做敏感度
  4. 恐半(恐慌買入)全景圖:計劃已向用戶交代,預設排隊喺 KARST-131/132 回來之後開;情緒族若由候選轉正,必守 D-083 全新樣本外對象紀律
  5. 貪半(FOMO 走)維持收檔唔重掃——死於方向唔係參數,全景圖救唔到方向

- 考慮過的替代方案：等 EDGAR 自砌完先考倍數 —— 唔使:神諭版唔需要時點數據,而家就考到上限,仲慳咗可能白起嘅工程

- 為何選這個：用戶提醒得啱:一路掃價格線唔係因為佢係主菜,係因為佢數據就手;神諭上限考正好用最平方式答「主菜值唔值得起數據工程」。

- **用戶原話（原文照錄）**

  > But first of all, you based on price? I think our approach is now based on multiple?(另:i don't even know the parameter for vectorBT. What is the plan?)

- 影響：板塊層隊形:倍數神諭(主線,即開)+ 反轉/RSI 均線(跑緊)+ 恐半(排隊)+ 資金流(等自儲);EDGAR 同收費數據兩個錢袋決定押後到神諭出結果。

## D-100 日課收縮(用戶裁決):未證明有料嘅線唔加日常任務——在外股數每日存檔(KARST-130)即日由日課除名,碼與測試保留,資金流線證明值得先重開,空窗係接受咗嘅代價;板塊倍數每日存檔(D-086)暫留,綁定神諭上限考結果——神諭冇料一齊停
- 類型：決策
- 狀態：有效
- 日期：2026-09-01

- 出處：用戶 2026-09-01 對在外股數存檔開站報告嘅回應,原話見 quote;主 agent 照裁決落實。

- 背景：KARST-130 啱啱建成每日在外股數存檔並寫入日課(兩句);用戶裁定方向倒轉:數據存檔任務唔應該行先過證明——證明咗條線有料,先值得日日餵佢數據。

- 決策：
  1. 在外股數每日存檔由日課除名,即日生效;karst.gateway shares capture 命令、測試、已回填嗰十二列全部保留唔剷
  2. 重開條件:資金流線證明值得(例如神諭式上限有料、或用戶明令);重開嗰日之前嘅數據空窗係呢個裁決接受咗嘅代價,唔另開票補救
  3. 板塊倍數每日存檔(D-086)暫時保留——佢係主線(倍數)嘅正本材料;但一樣受本裁決約束:神諭上限考(KARST-133)判倍數線冇料,佢即日一齊停
  4. 通則入帳:日後任何「每日/定期」任務,開站之前要有一條已證明或者擋住緊決定嘅線做依據,唔准以「儲咗先」為理由自動開站——D-086 嗰句「漏一日蝕一日」由通則降為個案理由
  5. HANDOFF 第三節日課句已照此改寫

- 考慮過的替代方案：照跑兩句(每日成本十幾秒) —— 用戶裁明唔係成本問題,係次序問題:證明行先,儲數行後

- 為何選這個：用戶條原則同考試制度同一個底:唔准未證先建。存檔件都係一種建置,一樣要排喺證明後面。

- **用戶原話（原文照錄）**

  > I think no need until we have proven. Dont make so many cron before something significant is well proven

- 影響：日課由兩句縮返一句;KARST-130 交付物轉為「備用件」;將來重考資金流,自儲序列由重開日起計。

## D-101 KARST-133 主軸修正(用戶裁決):考嘅唔係「倍數平貴水平排名」——係「倍數序列上嘅均值回歸/技術指標」:將板塊倍數序列當價格用,喺佢上面掃 RSI/超買超賣/對自身歷史回歸/趨勢一族;平貴水平排名降為對照基線;神諭分母嘅角色只係「令今日就砌得出幾十年倍數序列」嘅手段,唔係考點本身;價格層 TA 已證冇預測力,出路睇倍數層——正正係 D-076 第 5 項一直候補嘅「倍數版擺盪指標」
- 類型：決策
- 狀態：有效
- 日期：2026-09-01

- 出處：用戶 2026-09-01 對神諭票框架嘅糾正,原話見 quote;主 agent 即時修正派工。

- 背景：神諭票原框架偏重「完美盈利分母之下買平賣貴最多賺幾多」;用戶指出咁樣考極其量係考緊價格對基本面嘅比率水平,而價格層量化(動能/反轉/TA)已經證實冇答案;佢要嘅係將 TA 同均值回歸嘅整套武器搬去倍數序列上面用——即 D-076 第 5 項「以倍數代價格做擺盪指標輸入」嗰條候補線,依家轉正做主軸。

- 決策：
  1. KARST-133 掃描主軸改為「倍數序列上嘅訊號」四族:對自身歷史嘅均值回歸(百分位/標準差距離)、倍數序列 RSI/擺盪指標(超買超賣)、倍數趨勢/動量(D-074 嘅行業倍數趨勢)、倍數對大市比值嘅同類變形;平/貴水平排名只留一族做對照基線
  2. 神諭分母(事後真實盈利)嘅角色講清楚:佢係手段唔係考點——令我哋今日唔使任何存檔數據都砌得出幾十年板塊倍數序列;序列砌好之後,考點全部喺序列形狀上
  3. 對齊要兩版都跑:神諭版(盈利即知,理論上限)同現實版(盈利要等公布日先入序列,滯後對齊)——兩版差距本身就係「預測數據值幾多錢」嘅直接讀數
  4. 判讀照協議第七節不變:平原定孤峰、候選庫、唔產生及格
  5. 價格層 TA 量化嘅總結判詞照用戶講法入帳:jackpot 高但價格層冇預測力,出路睇倍數層

- 考慮過的替代方案：照原框架淨考平貴水平 —— 用戶明言唔係嗰回事;水平排名留做基線就夠

- 為何選這個：用戶指正嘅係考點錯位:D-077 個假設從來係「倍數係更乾淨嘅情緒溫度計」,考溫度計就要考佢嘅擺動(回歸/超買超賣),唔係淨考佢嘅絕對讀數。

- **用戶原話（原文照錄）**

  > Actually this is not the case, as the oracle is still on the price, but we have run a lot of quant that it seems although the jackpot of the high, but price level TA quant has no answer for the prediction. So we would like to see if multiple with Mean Reversal or TA on Multiple is the way out

- 影響：KARST-133 派工已即時補充指令;呢張票由「值唔值得買數據」升級為「倍數情緒儀(D-077)嘅第一次正面實測」。

## D-102 KARST-132 收案:RSI/均線橫截面揀板塊全景圖——兩族皆無平原,線級判死(D-096 證據形狀足):RSI 族 16 格 15 負連形狀都冇;均線族唯一正區係山脊唔係平原(沿長腳軸一換即冧),高度全住 2013 年之前,且三族與已判死嘅 12-1 動能逐月相關中位 +0.80——唔係第二條訊號,係死咗嘅動能換三種寫法;44 主格無一格 |t|≥2;SMC 開票前置條件未滿足繼續掛帳
- 類型：決策
- 狀態：有效
- 日期：2026-09-01

- 出處：KARST-132 交付(文獻關 commit a325d6d 先行、掃描收成 4603259、收檔 a99f3b1;關票把關驗過驗收四條;生產庫雜湊 B168E9F4…5FA8 不變)。主 agent 依 D-072 收案。

- 背景：文獻關事前寫死兩個預言,雙雙命中:(1) 均線喺指數層嘅正面證據已被後續文獻推翻或削至邊際,RSI 喺指數/ETF 層零可信學術基礎;(2) 價格對均線距離數學上係加權動能,所以掃描面預先擺低 12-1 動能參照格逐格算相關——結果相關中位 +0.80。

- 決策：
  1. 「價格層技術指標橫截面揀板塊」線級判死——本票自身就係全景圖,證據形狀符合 D-096(唔係兩點推論):44 主格 t 全域 −1.48 至 +1.39,最高格 +1.88pp 連單次檢驗都唔過
  2. RSI 族、均線族零格入候選庫;唯一山脊(短長均線差反轉、長腳 100 日)明文唔入——山脊唔係平原,高度全住 2013 前,且係動能嘅換裝
  3. SMC 繼續掛帳唔開票:D-098 第 3 條前置條件(RSI/均線有平原)未滿足,加上零同儕評審文獻、無可重現機械定義兩個自身死因
  4. 界線守住入帳:本票冇碰擇時/開關用法(市況層十月線佔住嗰格),價格層 TA 喺板塊層嘅結論唔倒推市況層十月線——嗰條係另一族、有自己嘅考試史
  5. 詞彙表補咗「全景圖/panorama」容器詞條(agent 已入 CONTEXT.md)

- 考慮過的替代方案：將山脊三格入候選庫 —— 否決:同動能相關 +0.80,入咗都係重複落注同一件已判死嘅嘢

- 為何選這個：文獻預言與實測逐格對得上,係本套「文獻先行+全景圖」流程第一次完整走通;判死判得快而平,正係制度想要嘅樣。

- **用戶原話（原文照錄）**

  > (用戶未批示;屬 D-072 授權內收案,成績覆核照舊留用戶)

- 影響：板塊層價格類材料至此:動能死(D-097)、TA 死(本條)、短窗反轉掃緊(KARST-131)、恐慌買入掃緊(KARST-134);主線係倍數序列訊號(KARST-133,D-101)。用戶「價格層量化冇答案」嘅判斷(D-101 quote)再添一張實證。

## D-103 神諭上限框架撤銷(用戶裁決):9 隻揀 3 逐月攞事後贏家,上限必然遠高於 SPY,不證自明、冇行動含義,唔使考;KARST-133 收窄做一件事——用公布滯後對齊嘅真實盈利砌「當時睇到」嘅板塊倍數序列,喺序列上掃入場/離場訊號(照 D-101 四族);判準永遠只有一條:搵唔搵到入場/離場訊號
- 類型：決策
- 狀態：有效
- 日期：2026-09-01

- 出處：用戶 2026-09-01 原話見 quote,承 D-099/D-101 兩輪修正;主 agent 即時改派工。

- 背景：D-099 開神諭票原意係用上限答「值唔值得起數據工程」;用戶兩步糾正到位:D-101 指出考點係倍數序列上嘅訊號,本條再指出上限本身冇資訊量——選項愈多上限機械上愈高,證極都係廢話,錢同注意力應全部擺喺訊號度。

- 決策：
  1. 神諭版(盈利即知)對齊撤銷唔跑;「神諭 vs 現實差距=預測數據價值」嗰個讀數一併撤銷
  2. KARST-133 收窄:單一序列——真實盈利按公布日滯後入帳砌逐月板塊倍數(即當年當時真係睇得到嘅後顧倍數),分子當時價格;喺呢條序列上照 D-101 四族掃訊號(對自身歷史均值回歸/序列 RSI 擺盪/倍數趨勢/對大市比值變形),平貴水平留一族基線
  3. 報告唯一主問題:四族有冇平原;有=入候選庫並裁下一步(樣本外對象、數據工程),冇=倍數序列訊號喺呢個宇宙判死
  4. 重建版盈利嘅誠實腳註照落:事後重述/追溯改寫風險要明寫(數據源係今日重建,唔係當年存檔)
  5. 橫截面分散度讀數(上一補項)保留——佢服務嘅係「換更細宇宙時嘅比例尺」,同上限撤銷唔衝突

- 考慮過的替代方案：照跑神諭版做參考格 —— 用戶明言 not practical,跑咗都係一個必然好睇嘅數,徒增誤讀風險

- 為何選這個：用戶把把關位用得準:上限高係選擇效應嘅數學必然,唔係策略資訊;考試資源應該全數擺喺「訊號搵唔搵到」呢條真問題。

- **用戶原話（原文照錄）**

  > yes, so I think it is not practical on oracle or now. As in just 9 sector ETF, for monthly rebalance, the oracle is definitely very high againt SPY already. Doesn't need to mention when going to further smaller ETF section. The key is always whether we have a way to find out the entry or exit signal

- 影響：KARST-133 派工已再修正;決策鏈 D-099→D-101→本條記錄咗成個收窄過程:由「上限值唔值」到「序列訊號」到「唯一問題係訊號」。

## D-104 價格類配菜兩隊即停(用戶裁決):唔 fit 整體策略(倍數情緒儀)嘅材料,就算可能有小利都唔要——KARST-134 恐慌買入取消(未接觸數據,腳本棄);KARST-131 反轉停機時已交齊卷,結果照收並依 D-096 補判死刑(唯一平原坐喺機制對唔上嘅位置且矮過盲揀三隻);KARST-129 候選庫「短期反轉方向」劃走;板塊層價格類材料全部清場,現役只剩倍數序列一條主線(KARST-133)
- 類型：決策
- 狀態：有效
- 日期：2026-09-01

- 出處：用戶 2026-09-01 原話見 quote;主 agent 即時執行:TaskStop 兩隊、KARST-131 代行關票、KARST-134 取消。

- 背景：用戶盤點四隊在跑嘅 agent 後裁定:恐慌買入(含 RSI2 on SPY 嗰格)同短窗反轉兩條係價格層材料,同核心假設(D-077 倍數情緒儀)無關,停。停機時反轉隊啱啱交齊卷(文獻關 386a5c2、結果 e9b482d),恐慌隊未接觸數據。

- 決策：
  1. KARST-134 取消:未開跑,experiments 草稿腳本唔入倉照棄;cancelReason 記重啟路徑——情緒族恐半重啟另開新票引本票及 D-083/D-096,QQQ/SOXX 做全新樣本外對象嘅備案一併記低;RSI2 喺 SPY 得唔得呢條問題隨之擱置未答,係本裁決接受咗嘅
  2. KARST-131 結果照收:172 格掃齊,零格正向 |t|≥2;唯一平原(6–13 週反動能)有平原無道理,且矮過盲揀三隻嘅運氣帶;順勢臂輸錢無等額變成反轉賺錢(兩臂同正 1/43)——依 D-096 三件套補判:短窗反轉線死刑成立
  3. KARST-129 候選庫「短期反轉方向」一條劃走——開票嗰條線索(追強者輸推反買贏)已被本票證明推唔成立
  4. 通則入帳:材料線立項要同核心假設(倍數情緒儀)接得上;「可能有小利」唔係立項理由
  5. 板塊層現役線清單:KARST-133 倍數序列訊號一條;資金流等自儲重開條件(D-100)、倍數閘等 KARST-133 結果

- 考慮過的替代方案：俾恐慌隊跑埋先停(佢答緊用戶自己問嘅 RSI2) —— 用戶裁明唔值,fit 唔 fit 行先過有冇小利

- 為何選這個：用戶把關位用喺正確層次:資源同注意力對齊核心假設,唔係逐條線問「賺唔賺」;證僞紀錄已經齊,清場成本低。

- **用戶原話（原文照錄）**

  > 兩隊配菜即刻停 I think. It is not worth as even it has some profit. But it  doesn't fit our overall strategy at all

- 影響：四隊縮一隊;板塊層價格類材料(動能/TA 橫截面/反轉/恐慌買入)全部清場或擱置,證僞紀錄齊備;下一個裁決點=KARST-133 四族有冇平原。

## D-105 KARST-133 收案:板塊倍數序列訊號四族全景圖 116 格無一格 |t|≥2(最好一格 +0.67pp/t 0.34;唯三統計分得清嘅格全部係輸),命中率 33.81% 對亂揀 33.33%——冇平原,倍數揀板塊喺呢個宇宙判死;錢袋三件(Sharadar/Estimize/EDGAR 行業倍數件)全部唔使做;依 D-100 每日倍數存檔即日停,日課歸零;板塊層至此冇任何現役線,下一步方向上 gate-1
- 類型：決策
- 狀態：有效
- 日期：2026-09-01

- 出處：KARST-133 交付(文獻關 commit a8909db 先行並早於一切數據下載、收檔 b53844d、關檔 891f3bd;vectorBT 同獨立手寫向量化對數中位差 0.075pp;生產庫雜湊 b168e9f45b578cf9 不變;票已關)。主 agent 依 D-072 收案。

- 背景：文獻關發現本身就係答案嘅一半:「行業之間用估值揀行業」兩輪檢索搵唔到一篇同儕評審論文,最接近嘅市場層證據共識偏負面(Goyal-Welch 樣本外冇一個變數幫到投資者;Asness 評因子擇時「歷史上非常弱」),事前預期接近零——實測命中。唯一形狀合格嘅高地(均值回歸·對大市比值·買平·36–84 個月窗)換基準即消失:對等權九隻贏 +0.6~1.6pp,對 SPY 得 −0.45~+0.54pp——贏嘅其實係「等權九隻本身輸 SPY」。

- 決策：
  1. 板塊倍數序列訊號線(四族:自身歷史均值回歸/序列擺盪/倍數趨勢/對大市比值,連平貴水平基線)喺「九隻 SPDR、月調倉、揸三隻」呢個宇宙判死——D-096 證據形狀足:成個參數面掃齊,冇平原
  2. 判死範圍講清楚,唔准讀多:否定嘅只係「用倍數揀邊個行業」;行業內用估值揀公司(個股層估值錨 D-073)不受影響;倍數做極端否決閘未考、隨板塊計分一併擱置
  3. 錢袋三件全部唔開:Sharadar(39 美元/月)、Estimize 開戶、EDGAR 行業倍數自砌件——問題唔係分母準唔準,係條序列本身排唔出板塊次序,買靚數據都救唔返
  4. 依 D-100 條款執行:每日板塊倍數存檔(D-086)即日停,日課歸零;HANDOFF 已改;capture 命令與已存 vintage 保留唔剷,重啟條件=有任何一條用得上佢嘅現役線
  5. 未核實三條照錄,判死受此限:評分期 2008-12 至 2026-07(2008/2000 兩隻大熊唔喺樣本,成因係暖身窗);公布滯後 60 日係近似+盈利係今日重述版;SPDR 面板第七次重用
  6. 板塊層總結算:動能死(D-097)、TA 橫截面死(D-102)、短窗反轉死(D-104)、資金流量不出(D-094)、倍數死(本條)——板塊層冇任何現役線;「風險開之內揀板塊」暫時冇證得住嘅方法,下一步方向(住 SPY 轉個股層/換宇宙/其他)上 gate-1 由用戶裁

- 考慮過的替代方案：繼續喺同一宇宙試新材料 —— 五類材料已清場,冇候選;要試要換宇宙或換層,嗰個係 gate-1 級方向

- 為何選這個：文獻預期、全景圖、基準拆解三者互相印證,判死判得乾淨;「贏等權唔等於贏 SPY」呢一格正係基準紀律(協議第三節)嘅價值所在。

- **用戶原話（原文照錄）**

  > (用戶未批示;屬 D-072 授權內收案,成績覆核照舊留用戶)

- 影響：D-052–057 三層路線嘅第二層暫時以「風險開=揸 SPY(D-071 地板)」運作;日課歸零;板塊層七張考試/掃描證僞紀錄齊備,係 v1 引擎交付品嘅一部分成績。

## D-106 倍數線唔收檔住(用戶覆核裁示):D-105 判死屬 agent 收案判詞,用戶行使成績覆核把關位裁示「想再探索」——三層補齊票暫唔開,判詞維持「後顧盈利層、呢個宇宙」範圍不擴大不落最終幕;主 agent 出九板塊倍數序列互動觀察頁交用戶親自睇圖,探索方向等用戶睇完再定
- 類型：決策
- 狀態：有效
- 日期：2026-09-01

- 出處：用戶 2026-09-01 對 KARST-133 收案報告嘅覆核回應,原話見 quote;主 agent 照裁示執行。

- 背景：KARST-133 砌成 1998 至今 335 個月、657 間公司真實盈利夾嘅板塊後顧倍數序列(experiments/2026-09-02-multiples-oracle-scan/sector_multiples.csv);四族訊號喺呢條序列上無平原(D-105)。用戶唔接受就此收場,想親自喺條圖上再探索。

- 決策：
  1. 三層補齊(P/S 層補掃+前瞻天花板讀數)暫唔開票——用戶明言 no need
  2. D-105 判死判詞維持但唔落最終幕:佢係 agent 收案判詞,覆核位喺用戶,用戶裁示再探索,倍數線維持「開放待探索」狀態
  3. 主 agent 出互動觀察頁(九板塊+大市,倍數水平/對大市比值兩個視圖,熊窗標示)交用戶親自睇;數據正本就係考試嗰條序列,唔另砌
  4. 下一步探索方向等用戶睇圖後指路,唔預設

- 考慮過的替代方案：照 agent 判詞直接收檔 —— 覆核位係用戶嘅,佢話未完就未完

- 為何選這個：成績覆核本來就係 D-072 留畀用戶嘅三個把關位之一;而條序列係新造出嚟嘅資產,用戶未親眼摸過就落最終幕,確實早咗。

- **用戶原話（原文照錄）**

  > Actually no need. I would like to explore further on this

- 影響：板塊層狀態由「冇現役線」改記「倍數線開放待探索」;錢袋三件照舊唔使(探索唔使買數據);日課維持歸零。

## D-107 用戶明令開 RSI2 多頻全景探索(倍數線探索第一步):RSI 窗固定 2 bar,bar 尺寸掃 1D/3D/1W/1M/3M 五檔,喺板塊倍數序列上跑,9 隻 SPDR 橫截面;日/週頻倍數序列冇現成正本,用月度自砌序列做錨、ETF 日價逐月重錨內插近似,並必須帶價格對照臂量化「日頻倍數 RSI2 ≈ 價格 RSI2」等價程度;照協議第七節,探索不產生及格
- 類型：決策
- 狀態：有效
- 日期：2026-09-01

- 出處：用戶 2026-09-01 原話裁示(quote 欄);主 agent 依 D-072 落場執行,開 KARST-135。

- 背景：主 agent answer 話日/週頻倍數圖不存在、月頻 RSI2 鄰域(3–24 個月窗)全死;用戶唔接受淨係鄰域推論,明令直接試 RSI2 五檔 bar 尺寸。分母每季先更新一次,兩次公布之間日頻倍數變動全來自價格,呢個結構性事實唔會因為跑咗個掃而消失——所以對照臂係本票誠實度嘅一半。

- 決策：
  1. 開探索票 KARST-135:RSI2(2-bar)× bar 尺寸 1D/3D/1W/1M/3M × 訊號用法(橫截面買最超賣 / 門檻式)× 持有窗,九隻 SPDR,倍數序列為主場
  2. 日/週頻倍數序列用「月度正本做錨+ETF 日價逐月重錨」近似砌出,砌法同限制寫入報告;1M/3M 用真序列
  3. 必帶價格對照臂:同一掃描喺價格序列上照跑一次,報兩者訊號相關同成績差,答「呢啲格贏嘅係倍數定其實係價格」
  4. 文獻關先行照 2026-08-29 用戶明令;RSI2 文獻全部喺價格日線(Connors 一系,2011 年後衰減),倍數序列上零文獻,預期可信度低,開跑前已向用戶交代
  5. 探索票照第七節:唔產生及格,平原+道理先入候選,轉正必守 D-083 全新樣本外對象

- 考慮過的替代方案：淨用月頻真序列補 RSI2 嗰格 —— 用戶明令五檔 bar 尺寸齊掃,唔剪佢單

- 為何選這個：用戶行使方向把關位直接落指令;鄰域推論唔等於實測,佢要見實數。對照臂令呢張票無論結果如何都有淨得着:一係搵到倍數獨有訊號,一係實證「高頻倍數=價格」呢句從此有數行。

- **用戶原話（原文照錄）**

  > I don't agree with 3/6/9/12/14/18/24 個月窗 I want to testing with Daily, Weekly and monthly RSI2. If vectorDB. Then can you try 1D, 3D, 1W, 1M, 3M.

- 影響：倍數線「開放待探索」狀態(D-106)下嘅第一張探索票;日課照舊歸零;唔使買任何數據。

## D-108 KARST-135 收案:RSI2 五檔 bar 尺寸 5,644 格全掃——日/三日/週三檔無平原且兩臂等價(重合率 0.83–0.95,兩邊皆負,日頻成本一年食 4–6 個百分點);月/季兩檔倍數臂勝價格臂(94–100% 格,中位差 +2.4 至 +4.3pp),最強格月頻橫截面 +5.19pp t=2.16;但真倍數口徑下縮至 +1.82pp t=1.29(過半優勢來自票面砌法),且 24 族無一族 2013 年後中位超額為正——不產生及格,入候選庫 C-135-A 帶三條扣分
- 類型：決策
- 狀態：有效
- 日期：2026-09-01

- 出處：KARST-135 交付(文獻關 commit d16cb29 先於一切掃描;生產庫雜湊 b168e9f45b578cf9 不變;vectorBT 對照 117 格最大差 0.0105pp;票已關)。主 agent 依 D-072 收案。

- 背景：用戶明令(D-107)五檔 bar 尺寸齊掃,並帶價格對照臂。結果答齊兩條問題:(1) 高頻倍數 RSI2 是否只是價格翻版——係,1D/3D/1W 兩臂持倉重合 0.83–0.95、讀數相關 0.81–0.92,且兩邊都輸;(2) 慢頻有冇倍數獨有訊號——有形狀:月/季倍數臂在 94–100% 格贏價格臂,價格臂月/季為負數族。

- 決策：
  1. 日/三日/週三檔判死:無平原,兩臂等價皆負,日頻年換手 42–58 倍單成本已足以解釋
  2. 月/季倍數臂訊號入候選庫 C-135-A(月頻橫截面買 RSI2 最低一隻持兩月,+5.19pp t=2.16,鄰域最低 +3.59),帶三條扣分:①真月底倍數口徑下縮至 +1.82pp t=1.29,過半優勢來自票面砌法(月 bar 重錨序列混入回報動量成分)而非倍數本身;②時間對半切,24 族無一族 2013 年後中位超額為正,與 RSI2 文獻 2011 後失效逐格對上——換估值序列救唔返近期失效;③同批 SPDR 日線第十次重用
  3. 不產生任何及格(協議第七節);轉正必守 D-083 全新樣本外對象,主 agent 判斷:未指定全新市場(歐洲/日本板塊 ETF 一類)之前,唔值得為 C-135-A 另開考試票
  4. 本票新知識一句:慢頻上倍數確實載有價格冇嘅資訊(方向啱),但幅度細、近十三年唔出糧——「倍數揀板塊」由 D-105 嘅『排唔出次序』修正做『排到少少但唔夠俾成本同年代衰減』

- 考慮過的替代方案：直接為 C-135-A 開新市場考試票 —— 三條扣分未解,先等用戶睇圖後裁方向

- 為何選這個：對照臂設計令本票兩個可能結果都有淨得着,實際兩個都兌現:高頻=價格翻版有數為證;慢頻倍數獨有訊號有形但站唔住,死因(砌法混訊+年代失效)寫得出嚟。

- **用戶原話（原文照錄）**

  > (用戶未批示;屬 D-072 授權內收案,成績覆核照舊留用戶)

- 影響：倍數線維持開放待探索(D-106);候選庫新增 C-135-A;日課照舊歸零;成績覆核照舊留用戶。

## D-109 用戶裁決:倍數線全面轉前瞻——序列升級唔逐樣揀,直接合併做「前瞻盈利收益率」(未來預估盈利÷市值,一個指標同時解決分母係預期+負數唔斷線);觀察台每板塊兩條線(後顧/前瞻)並排;RSI2 喺兩條月頻真口徑序列上對照重掃;前瞻分母行 KARST-125 勘察出嘅免費 PIT 路線(2002+,錯改率約 2.8%)
- 類型：決策
- 狀態：有效
- 日期：2026-09-01

- 出處：用戶 2026-09-01 對序列升級選項嘅回覆(quote 欄原話);主 agent 開 KARST-136/137 執行。

- 背景：觀察台出街後用戶裁示唔要介面鑽入功能,要升級序列本身做探索地基;我提四個改法(前瞻分母/收益率連續化/多年平均分母/市銷率層),用戶裁:市場其實只睇前瞻,收益率連續化 ok,兩者合併,每板塊兩條線,兩條都用 RSI2 測,而且「all these should use forward」。

- 決策：
  1. 開 KARST-136(建置):由 yfinance 季度 PIT 預估(D-093/KARST-125 路線)砌九板塊+大市前瞻盈利收益率月度序列 2002 年起;後顧盈利收益率由現有序列翻算;兩條同落一個 CSV
  2. 開 KARST-137(探索):RSI2 月/季頻真口徑,喺後顧與前瞻兩條收益率序列上對照掃——只用月底真序列,汲取 KARST-135 教訓(重錨近似混入動量成分),不再用近似砌法
  3. 多年平均分母、市銷率層暫唔做——用戶裁「market only look at 前瞻」,全副注碼落前瞻
  4. 觀察台升級(主 agent 自做):每板塊後顧+前瞻兩條線並排,等 KARST-136 序列交貨後更新,同一條連結

- 考慮過的替代方案：逐樣改法分開驗 —— 用戶已裁合併轉前瞻,唔剪佢單

- 為何選這個：用戶行使方向把關位;「市場出價買嘅係將來」呢個判斷同文獻一致,而免費 PIT 路線係 KARST-125 勘察已證嘅現成資產,啱好接得上。

- **用戶原話（原文照錄）**

  > Yes, I think the market only look at 前瞻分母 to be honest. 盈利收益率連續化 is ok. But may want to know how to mix and match both of them. Or maybe 2 line for 1 industry. both tested with RSI2. But I think Earning should need forecast as well. In fact I think all these should use forward

- 影響：倍數線探索地基由「後顧市盈率」升級做「前瞻盈利收益率」;免費路線,錢袋照舊唔使開;日課照舊歸零。

## D-110 用戶明令(常設):agent 同用戶平級對話——誠實批判,唔准附和;認真考慮用戶觀點但必須帶自己立場同批判評估;用戶會持續挑戰,agent 讓步必須寫得出讓喺邊、點解讓
- 類型：決策
- 狀態：有效
- 日期：2026-09-01

- 出處：用戶 2026-09-01 原話(quote 欄),緊接佢批評 agent 連續多輪只識話佢啱、冇 solid insight 之後。

- 背景：倍數線探索期間用戶連續推理(比率約價格、釘同財季量修訂),agent 逐輪確認佢啱但冇企出大局立場;用戶指出自己係 layman 都搵到 loophole 而 agent 冇貢獻判斷。agent 承認並補硬立場(板塊圖無寶藏、2013 斷層係結構性、現時實證最佳組合=揸 SPY、建議落個股層)。

- 決策：
  1. 常設規矩:每個回覆帶 agent 自己立場(信乜、押邊邊、把握幾多),唔准淨係整理用戶諗法
  2. 用戶觀點啱要講埋「放喺大局代表乜」;錯要直接講,俾理由證據
  3. 被挑戰時真思考先答;可以認錯但唔准為息事寧人讓步
  4. 此令與 D-072(agent 主導)同讀:執行主導之外,判斷都要主導

- 為何選這個：附和令用戶失去強模型嘅價值;用戶要對手盤,唔係應聲蟲。

- **用戶原話（原文照錄）**

  > OK - First, from now on, you need to be the same level as me, give honest comment. I will for sure challenging you, but you really need to think about with your best understanding, and consider my point honestly. And critical thinking to assess.

- 影響：溝通紀律,全部日後對話適用;已同步寫入專案記憶。

## D-111 KARST-136/137 收案:前瞻盈利收益率序列砌得成(2002–2025 市值覆蓋率中位 88–100%,後顧線 87 個負盈利斷格全部接返);RSI2 前瞻臂企得住形——最強格 +9.33pp t=2.82,25/32 族平原,鏡像方向(買貴)0/8 全滅——但表面優勢約三分之二來自預估凍結洩漏(低洩漏線中位 +1.28pp 對 +3.35pp),踢走精度受損成員後 2013 後族內中位剩 +0.23pp,最強格最大回撤 −58.2% 深過 SPY;「救返 2013 後」只在門檻式一半成立;探索票不產生及格,入候選庫;A-028(低洩漏線是否足以隔離洩漏)未查證,查證前前瞻臂判詞全部有條件
- 類型：決策
- 狀態：有效
- 日期：2026-09-01

- 出處：KARST-136/137 交付(兩票規格與判準均先於跑數 commit:f80a1cb/c2af380 等七個;生產庫雜湊 b168e9f45b578cf9 不變;兩票已關)。主 agent 依 D-072 收案。

- 背景：用戶裁決 D-109 全面轉前瞻後嘅實測。對照設計答咗核心問題:前瞻分母喺月/季頻確有增量(後顧臂門檻式全孤峰、前瞻臂轉平原;方向性核對乾淨),但增量嘅大部分喺剝走洩漏同精度問題後幅度細,且集中持倉回撤深。

- 決策：
  1. 收貨事實:前瞻序列係真資產——覆蓋率超門檻、斷格接返、兩條線已上觀察台(收益率視圖,實線前瞻幼虛線後顧)
  2. RSI2 前瞻格入候選庫 C-137-A,帶四條扣分:①低洩漏口徑幅度縮三分之二;②2013 後剔精度受損成員剩 +0.23pp;③最強格全押單一板塊回撤 −58.2%;④SPDR 面板重用次數再增
  3. A-028 查證係前瞻臂一切判詞嘅先決條件,列為下一件機制工作;查證前唔開任何轉正考試
  4. 主 agent 立場照 D-110 記錄:呢個係板塊層開戰以嚟最靚嘅形,但剝乾淨之後唔夠俾成本+回撤,唔改變「主力落個股層」嘅建議;前瞻/修訂數據價值上升,而佢哋正正可以直接搬落個股層用

- 考慮過的替代方案：直接為 C-137-A 開全新市場轉正考試 —— A-028 未查、幅度未企穩,言之尚早

- 為何選這個：對照臂+低洩漏線+精度拆解三重誠實檢查,令「企得住」同「企唔住」兩句都有數支撐;唔收檔唔加注係證據當前最誠實嘅位置。

- **用戶原話（原文照錄）**

  > (用戶未批示;屬 D-072 授權內收案,成績覆核照舊留用戶)

- 影響：板塊層倍數線維持開放但唔加注;觀察台已升級;下一階段方向(個股層 vs 其他)上 gate-1 等用戶裁,方向討論已喺對話展開(行內排名+月頻起跳+事件錨定骨架獲用戶推理獨立收斂)。

## D-112 用戶裁決(gate-1 方向級,經多輪平級討論收斂):主力落個股層,憲法修一條——板塊層職能由「揀贏家」改「劃賽道」(行內比較組+風險欄),市況閘不變、先揀嘢後時機不變;個股層架構四件:①過濾器=盈利能力+投資紀律+行內價值三因子加「預估未被斬」活線,行業內每行頭 N 隻出名單(用戶原話傾向 top 3 per industry,主 agent 否決「全市場頭十隻」);②排名=事件/修訂錨定,事件時鐘唔用月曆時鐘;③TA 退役做入場/離場/賠率條件,唔做選股;④波段持有(swing),明文唔炒即日;細分行業 ETF 做載具/樣本外考場/刻度三個配角,唔做超額層;樽頸論=壽命錯價,量化影子併入修訂訊號,供應紀律入因子候選,論點記錄表加「產能倒數」欄
- 類型：決策
- 狀態：有效
- 日期：2026-09-01

- 出處：用戶 2026-09-01 連串裁示與討論收斂(關鍵原話見 quote;其餘:「Our rules is not Market > Sector / Value Chain > Individual? And selection first then timing?」「should we introduce subsector after section given Market and Sector? iShare those ETF?」(主 agent 回:做三配角唔做超額層,用戶未反對)「Swing trade I think la. But not day trade at least」)。主 agent 依 D-072 落實,開設計票。

- 背景：板塊層七輪實測清場(D-097/102/104/105/108/111)後,用戶擲波問最大寶藏喺邊;多輪討論收斂:細 IC 必須闊棋盤兌現、估值訊號預測力住喺長視界、事件訊號要事件時鐘、樽頸 edge 喺壽命錯價。五因子入面近代企得穩嘅三隻(盈利能力/投資紀律/行內價值)原料喺 657 公司免費數據齊備。

- 決策：
  1. 憲法修訂:三層維持,板塊/價值鏈層之於超額回報——經七輪實測,職能由選擇改為結構(比較組+風險欄);此條入 CONTEXT/HANDOFF
  2. 個股層設計票即開:過濾器四件套、事件排名、TA 幾何、波段節奏、參數對齊一節(D-038)、考法照考試協議、樣本外考場寫死(QQQ/SOXX/細分 ETF 池)
  3. 過濾器名單制:行業內 top-N(N 對齊時定),唔用全市場 top-10;過濾器必含修訂活線防價值陷阱
  4. TA 角色明文:entry/exit/R&R 條件,唔產生選股訊號;持有期波段級,即日交易明文排除
  5. 樽頸三落點:修訂延續訊號(量化影子)、供應紀律因子(候選)、論點記錄表「產能倒數」欄

- 考慮過的替代方案：繼續板塊層挖倍數 —— 用戶同 agent 立場一致:剝乾淨後唔夠俾成本,轉場

- 為何選這個：三條獨立線索(闊度數學、文獻證據、用戶常識推理)收斂同一出口;設計票先行俾 gate-1 把關,符合判準先寫死紀律。

- **用戶原話（原文照錄）**

  > Agree. I think it could be the case where these 3 factor is not a TA by itself, but the best stock filter at the point in time. Say only look at the top 10 stocks of the market, or top 3 in each industry. Then simple TA as single as good stock gonna good. Even if buying the dip, should buy the book stock instead of the bad stock at the dip. TA should help to set the entry, exit and R&R as condition

- 影響：下一階段主力=個股層設計方案書(gate-1 審批件);板塊層倍數線維持開放但唔加注;觀察台照留;日課照舊歸零。

## D-113 KARST-138 收案:個股層設計方案書交付(research/2026-09-03-個股層設計方案.md,gate-1 審批件)——四件套精確定義(盈利能力=現金制營業利潤÷上期資產;投資紀律=總資產按年增長;行內價值=前瞻盈利收益率;修訂活線免費數據回測不到、只有「連續 N 季超預期」代用品)、兩層名單制(板塊內頭 3→約 27 隻池→持倉約 6)、事件時鐘公布後 1–5 個交易日、樣本外主考場 QQQ、27 項待對齊參數(5 項須用戶親裁);文獻關潑冷水:大型股 2014 後四件套無一有顯著獨立溢價、同類異象扣成本剩每月幾個基點;agent 建議先跑 D-050 退化神諭曲線再裁建唔建;兩件擋路事上 gate-1:①修訂活線真線要自建存檔一年後先有(且開存檔=新日課,同 D-100 衝突);②D-051(唔自建個股籃)與 D-112(主力個股層)憲法衝突,agent 建議修 D-051(零佣時代理由已變)但戶口規模係用戶事實,不代裁
- 類型：決策
- 狀態：有效
- 日期：2026-09-01

- 出處：KARST-138 交付(文獻關 8261cc1 獨立先於一切設計參數 commit;生產庫雜湊 b168e9f45b578cf9 不變;票已關,四條驗收剔齊)。主 agent 依 D-072 收案;三件裁決事項(D-051 修訂/神諭曲線先行/存檔日課)以選項介面上 gate-1。

- 背景：D-112 憲法修訂後首張設計票。方案書行業粒度建議用九板塊而非 129 細行業(細行業平均每組 5.7 隻,頭三名變三揀五,名單膨脹到 300 隻戶口買唔起);過濾除數一律用上期而非當期(明知當期歷史數靚啲,揀理論啱嗰個,已入知情聲明)。

- 決策：
  1. 方案書收貨為 gate-1 審批件;任何實測票等用戶批方案書+裁三件事先開
  2. 主 agent 立場:同意 agent 嘅「神諭曲線先行」建議——幾個鐘換「呢條線值唔值得行」嘅判詞,平過幾個星期起完先發現唔值;文獻關嘅冷水照擺枱面唔沖淡
  3. D-051 衝突唔代裁:修訂理據(當年理由=佣金,今日美股佣金近零)成立,但戶口規模可行性係用戶事實
  4. 修訂活線存檔如開=新日常任務,觸 D-100「未證明有料嘅線唔加日課」,一併上 gate-1

- 考慮過的替代方案：跳過神諭曲線直接開建置 —— 文獻關已預警溢價可能係零,先量獎品上限先合 D-050 慣例

- **用戶原話（原文照錄）**

  > (用戶未批示;屬 D-072 授權內收案,gate-1 裁決留用戶)

- 影響：個股層進入 gate-1 審批;三件裁決事項擋住後續;板塊層/觀察台/候選庫狀態不變。

## D-114 個股層 gate-1 三裁齊(用戶裁決):①開工次序=退化神諭曲線先行,幾個鐘量個股層獎品上限,上限唔吸引即收檔;②正式修訂 D-051——「唔自建個股籃」一格取消,六隻個股每隻一注屬用戶戶口可行範圍(用戶親自確認),零佣時代原理由已失效;ETF-only 執行地基改為「ETF 為載具/樣本外考場/刻度三配角,個股籃為主力落注形式」與 D-112 對齊;③修訂預估每日存檔唔即刻開,等上限曲線結果——曲線話條線值得行先開存檔,唔值就慳埋,同 D-100「未證明有料嘅線唔加日課」精神一致
- 類型：決策
- 狀態：有效
- 日期：2026-09-01

- 出處：用戶 2026-09-01 gate-1 選項介面三答:「上限曲線先行(建議)」「修例:六隻壹注可行(建議)」「等上限曲線先(建議)」。三條全部揀建議項。

- 背景：KARST-138 方案書(D-113 收案)交付後嘅三件擋路裁決。D-051 修訂令 D-112 憲法衝突正式解除;存檔日課裁決同時解咗 D-100 衝突(以「等證據先開」方式)。

- 決策：
  1. 開 KARST-139 退化神諭曲線探索票:個股層架構約束下(九板塊×頭3、持倉約6、事件時鐘、波段)事後全知揀股嘅年化上限、打和倍數,對 SPY 含息;幾個鐘交貨
  2. D-051 修訂即時生效:個股籃唔再被禁,戶口規模一格由用戶確認可行
  3. 修訂預估存檔日課押後,綁定 KARST-139 結果再裁;過渡期修訂活線繼續用「連續超預期」代用品設計

- 考慮過的替代方案：跳過上限曲線直接開建 —— 用戶已裁唔行,文獻冷水在前,先量獎品係平價殺主意老規矩

- **用戶原話（原文照錄）**

  > 用戶三選:「上限曲線先行(建議)」/「修例:六隻壹注可行(建議)」/「等上限曲線先(建議)」(2026-09-01 選項介面)

- 影響：個股層由審批狀態轉入探索狀態;KARST-139 結果係下一個裁決點(值得行→開建置+裁存檔;唔值→成條線收檔返論點線/LLM掃描)。

## D-115 KARST-139 收案:個股層退化神諭曲線交付,agent 建議照方案書架構收檔——事後全知上限年化 1,190%(27.7 年零蝕月,板塊版 105.7% 的十一倍),但打和準繩度對大市/最強單一板塊(XLK)/事後最強單一股(AAPL)分別為擲骰的 1.39/1.71/4.72 倍,板塊版通則 1.34 倍在個股線不成立;兩條事先寫死的笨規則(上月頭六名、12-1 動能)實際準繩度達擲骰 2.50/2.58 倍、超過打和門檻一倍半,仍雙雙輸大市(6.84%/8.68% 對 SPY 8.71%、XLK 10.43%)——根因係集中度懲罰:「揸六隻、每月全換」本身先蝕 10.3 個百分點(3.7 成本+6.6 波動拖累;隨機六隻全換年化 1.27% 對同批股全揸等權 11.55%),而方案書自己預期四件套只值零至幾個百分點,填唔到個洞;十格架構(行內頭3/5×持倉6至45)無一贏 XLK;倖存者缺口明錄(1,209 家有 740 家查到分類,近四成除牌者缺席,上限偏樂觀)
- 類型：決策
- 狀態：有效
- 日期：2026-09-02

- 出處：KARST-139 交付(票已關 2026-09-02,四條驗收剔齊,生產庫雜湊 b168e9f45b578cf9 不變,大檔未入 git)。正本 research/2026-09-01-個股層神諭曲線.md、experiments/2026-09-01-stock-oracle-curve/。主 agent 依 D-072 收案。

- 背景：agent 明示自己建議嘅弱點:兩條核對規則同屬動能族(天生高波動高互相關),四件套係質素/價值族,集中度懲罰未必咬得一樣深、未量過——故對「照呢個架構唔值得建」高把握,對「整條個股線唔值得行」中等把握。連帶影響:D-114 第③項存檔日課本綁定「曲線話值得行先開」,現狀=繼續唔開,等後續小票結果。附:A-030 已登記為推翻——退化神諭曲線「揀錯係獨立隨機」假設不成立(真實策略嘅錯誤高度相關兼帶集中度懲罰),凡單靠 D-050 曲線把關嘅線都會低估真門檻;D-050 係用戶裁決,補唔補格留用戶裁。詞彙表新增「集中度懲罰 concentration penalty」。

- 決策：
  1. KARST-139 結論收貨;個股層「九板塊×頭3→27池→揀6、月度全換」呢個具體架構判死,唔開建置
  2. 主 agent 立場(D-110):認同 agent 分段建議——用一張幾個鐘小票量質素族(行內價值原料已在倉)嘅算術優勢與六隻組合波動,先答「集中度懲罰對質素族咬幾深」,再裁整條個股線嘅生死;唔跳過呢步直接判整條線死,因為判死嘅證據嚟自動能族,族唔同
  3. 開唔開小票、A-030 要唔要補 D-050 一格,兩條上用戶裁決;存檔日課維持唔開

- 考慮過的替代方案：
  1. 跳過小票即刻整條個股線收檔 —— 慳一張票,但用動能族證據判質素族死刑,族錯配;agent 自己都只有中等把握
  2. 無視集中度懲罰照開建置 —— 算術上唔成立:預期幾個百分點填 10.3 個百分點嘅洞

- **用戶原話（原文照錄）**

  > (用戶未裁;屬 D-072 授權內收案,小票與 D-050 補格兩條留用戶)

- 影響：個股層建置全面凍結;D-114 排隊嘅第3/4/5張票(EDGAR建置/全景圖/考試)全部唔開;10x 對照研究與 LLM 掃描兩張衛星票唔受本判詞直接影響(論點線唔以贏 XLK 為判準),但開票時序等用戶裁完小票一併排。

## D-116 D-050 補格(用戶裁決):日後所有退化神諭曲線必須連帶「笨規則實測」核對——至少一條事先寫死的簡單真策略在同一架構下實際行一次,對照曲線在該準繩度下的預測回報,兩者背離即在結論明報,不准單靠曲線定打和門檻。理據:A-030 推翻——曲線假設「揀錯係獨立隨機」,真實策略成批一齊錯並帶集中度懲罰,單靠曲線會低估真門檻(KARST-139 實測:兩條笨規則準繩度達擲骰 2.50/2.58 倍、超打和門檻一倍半,仍雙雙輸大市)
- 類型：決策
- 狀態：有效
- 日期：2026-09-02

- 出處：用戶 2026-09-02 選項介面裁「補一格(建議)」。原格 D-050(退化神諭曲線為每條線起點)維持不變,本條只加核對義務。

- 背景：KARST-139 個股層神諭曲線首次暴露此盲點;板塊層各線(KARST-113 等)當日無笨規則核對,其打和門檻(1.34 倍通則)可能同樣偏樂觀,但該層已清場,不回頭重跑;由本條起生效於所有新曲線票。

- 決策：
  1. 神諭曲線票的驗收條件今後必含「笨規則實測」一格:至少一條事先寫死、不准事後改的簡單策略真跑,報實際準繩度、實際回報、曲線預測回報三個數
  2. 背離(實際明顯低於曲線預測)即為集中度懲罰的量度,必須入結論首段
  3. A-030 維持推翻狀態,教訓正本在假設冊與本條

- **用戶原話（原文照錄）**

  > 用戶選「補一格(建議)」(2026-09-02 選項介面;問題文本明列 A-030 證據與兩條笨規則實測結果)

- 影響：所有未來策略線的獎品量度多一重校準;成本每票約一個鐘。

## D-117 個股層生死分段裁(用戶裁決):開小票量「揀穩陣好公司」型六隻組合嘅波動懲罰——用同一範圍(標普歷史成員查得到分類批,每月 238–439 隻)現成原料砌行內價值排名,只量穩陣六隻嘅集中度懲罰幾深;似追強者(懲罰同量級)就整條個股線收檔,懲罰明顯輕先再裁後續。用戶同時確認理解:判死原因係組合數學唔係股票範圍,換範圍(中小型股)只會令懲罰更深,唔試
- 類型：決策
- 狀態：有效
- 日期：2026-09-02

- 出處：用戶 2026-09-02 選項介面裁「開小票量穩陣族(建議)」;前一輪追問「But what is the stock scope」已答(範圍=每月 238–439 隻,缺席近四成除牌者,上限偏樂觀方向已錄 D-115)。

- 決策：
  1. 開 KARST-140:穩陣族集中度懲罰量度票,幾個鐘交貨,受 D-116 笨規則實測新規約束
  2. 判準事先寫死:穩陣六隻嘅波動拖累與動能族(6.6pp)同量級=整條個股線收檔;明顯輕(方向性判詞,數字由票面事先寫死)=返用戶裁後續
  3. 存檔日課、EDGAR 建置、全景圖、考試票全部維持凍結,等本票判詞

- **用戶原話（原文照錄）**

  > 用戶選「開小票量穩陣族(建議)」(2026-09-02 選項介面)

- 影響：個股層生死繫於 KARST-140 一張票;其餘隊列不動。

## D-118 KARST-140 收案:集中度懲罰證實為規則中性——換完全相反嘅選股風格(深度價值對動能),六隻組合嘅波動懲罰 4.07pp 對 3.81pp,相差 0.26pp,按事先寫死嘅補充判準(相差 1pp 內=同量級)讀作同量級;「一次只揸六隻」本身係每年約 4pp 嘅固定學費,同揀邊族無關。agent 建議整條個股層(系統線)收檔。三件不利自己建議嘅話照錄:①KARST-139 嘅 6.6pp 唔係常數(同式落本票日子只得 0.68),4.4 判準線底子浮;②KARST-139 成本按每月全換算重咗,實際換手 26%/37%,更正後動能族淨年化 12.23% 贏 SPY 兩個幾百分點(仍輸 XLK 13.17%);③實測揀出嚟嘅係困境股(中位前瞻 PE 約 4 倍:杜邦/通用汽車/美聯航/梅西),倉內原料量到便宜量唔到穩陣——本票證偽嘅係深度價值族,質素族一次都未測過(A-031 已登記;詞彙表新增「深度價值族」)。規劃曲線三次核對三次嚴重高估(本次預測 +9.11% 對實際 −7.90%,背離 17pp),不再可用作決策工具
- 類型：決策
- 狀態：有效
- 日期：2026-09-02

- 出處：KARST-140 交付(票已關,四條驗收剔齊,判準跑數前獨立 commit 92eea8a,生產庫雜湊 b168e9f45b578cf9 不變)。正本 research/2026-09-02-穩陣族集中度懲罰.md、experiments/2026-09-02-quality-concentration/。主 agent 依 D-072 收案。

- 背景：主 agent 立場(D-110):同意收檔系統線。理由:①4pp 學費規則中性,方案書自己預期過濾器只值零至幾 pp,算術唔成立;②「質素族未測過」係事實,但補測佢要先建 EDGAR 基本面線(幾星期),而文獻話大型股質素 t=0.7,期望值明顯負;③KARST-139 十格架構(持倉闊到 45)無一贏 XLK,放寬持倉呢條路都試過。重開觸發點寫死:日後若因其他原因建成 EDGAR 基本面線,質素族可用幾個鐘平價補測,嗰時先重談。衛星三線(論點/修訂活/LLM 掃描)唔受本判詞影響——佢哋唔係「月度排名揸六隻」嘅玩法。動能族更正後贏 SPY 兩個幾 pp 一格照錄入帳,但 D-050(用戶裁)嘅對手係最強單一被動選擇,佢輸 XLK,唔翻案。

- 決策：
  1. KARST-140 結論收貨;「行內排名揀六隻波段換馬」呢個系統線玩法判死
  2. 整條個股層系統線收唔收檔=用戶 gate 裁決,選項介面上;衛星三線與存檔日課嘅去向一併等埋 KARST-141/142 回報後排
  3. 退化神諭曲線工具降級:三次核對三次嚴重高估,今後只准做「上限刻度」,不准單獨用作開建置嘅依據(D-116 笨規則實測照行)

- **用戶原話（原文照錄）**

  > (用戶未裁;收檔裁決以選項介面上 gate)

- 影響：板塊層(D-112 已清)加個股層系統線若收檔,平台主力線歸零,現存資產=市況閘、板塊結構職能、前瞻收益率序列、三條衛星線;下一主力方向係大過一張票嘅討論,等 141/142 齊先擺枱面。

## D-119 KARST-142 收案:LLM 樽頸語言掃描原型交付,判詞「樣本太細判唔到,但押行得通」——封存尺下命中 2/6(33%)、零誤報(12 段對照全清),每份文本處理量全文約 18,500 字元(關鍵詞預篩後 790,慳 23 倍);量產成本唔係關卡(657 家每季掃一年僅 6–146 美元、網絡時間 9 分鐘),真人手成本在 MD&A 切節工程(彎引號致 12 份切錯 8 份且靜默失敗,已修;Eaton 年報無此節換 Cummins)。四段漏報拆帳:兩段係標籤本身貼錯(Powell 2024/Bloom 該期實為景氣好非供貨緊,尺判對咗)、兩段係尺缺陷(積壓/交貨期兩項部分商業模式根本唔披露);另發現積壓與加價兩項量景氣唔量樽頸(Powell 2019 對照年積壓 +61% 強過樽頸年)。下一步次序寫死:先用客觀數據(交貨期指數/積壓對營收比跳升)定義樽頸期標籤,先改尺(供貨受限為主判),後擴樣本(40–60 份、同公司跨年配對),最後正式工程化切節——標籤唔搞掂,擴掃描全部白做
- 類型：決策
- 狀態：有效
- 日期：2026-09-02

- 出處：KARST-142 交付(票已關,判別清單讀文本前寫死並獨立 commit 400f0a3,46.4MB 原始文本留本機零入 git,生產庫全程唯讀雜湊 b168e9f45b578cf9 不變)。正本 research/2026-09-02-樽頸語言掃描原型.md、experiments/2026-09-02-bottleneck-scan-prototype/。A-032(印象標籤不可靠)入假設冊;詞彙表新增「樽頸語言」「樽頸指標 vs 景氣指標」。主 agent 依 D-072 收案。

- 背景：路徑更正:派工指令寫嘅生產庫路徑 data\karst.sqlite 唔存在,實際喺倉根 C:\projects\Karst\karst.sqlite(已 Glob 核實),agent 對正確檔核雜湊。今後派工指令用倉根路徑。

- 決策：
  1. KARST-142 結論收貨;論點線入貨漏斗「行唔行得通」維持開放,但零誤報+成本近零兩格係正面證據
  2. 後續票(客觀樽頸標籤定義)唔即刻開——排入衛星線隊列,等個股層收檔裁決與 KARST-141 回報後一併排
  3. 派工守則更正:生產庫路徑=倉根 karst.sqlite

- **用戶原話（原文照錄）**

  > (用戶未裁;屬 D-072 授權內收案)

- 影響：衛星線第 4 線(LLM 漏斗)由「未知可行性」推進到「押行得通、下一步明確」;無任何投資訊號產生。

## D-120 KARST-141 收案:10x 對照研究交付——11 對贏家配輸家(6 類成因)、10 對計分,判別清單草案 12 項事前指標零統計顯著;傳統質素篩選(盈利/現金流/毛利/攤薄/規模)事前完全分唔出贏輸,最極端係盈利一項:3 對可分中 2 對反而輸家較賺錢,AMD 2015(蝕錢、淨負債 6.5 倍權益、毛利一半)四項全輸其後 55 倍——用戶「盈利轉好係結果唔係原因」(2026-09-01)喺數據上企得住;唯一有苗頭=估值相對同業便宜(9 對中 7 對,p=0.18 排除唔到運氣,且與系統線重疊非論點線獨有);基礎率:10 倍要十年(2-7%)、五年內 <0.3%、十年中位僅 2.3-3.3 倍,面板內真 10 倍股全係早已證明自己嘅龍頭。三格打折照錄:原定三隻退市輸家免費數據連價都攞唔到被迫換生還者(搵數據呢步已偏袒生還者)、配對主觀、樣本細。agent 建議:唔好靠清單落注,論點線唯一唔同系統線重疊嘅判別力(樽頸真唔真、幾時被新產能解)在文本,先行文本掃描路;注碼與持有期紀律可即刻按基礎率寫死
- 類型：決策
- 狀態：有效
- 日期：2026-09-02

- 出處：KARST-141 交付(票已關,四條驗收系統把關,生產庫雜湊 b168e9f45b578cf9 不變,62MB SEC 快取未入 git)。修掉三個會反轉結論嘅真錯誤並留檔(谷底峰值倍數法、財務標籤取舊數、拆股致市值錯五倍)。正本 research/2026-09-02-10x對照研究.md、experiments/2026-09-02-tenbagger-casecontrol/。主 agent 依 D-072 收案。

- 背景：與 KARST-142(D-119)對讀:141 話論點線嘅獨有判別力在文本,142 話文本掃描押行得通但要先搞客觀樽頸標籤——兩票指向同一下一步(客觀標籤票),互相印證而非互相依賴(兩隊平行跑,冇通過氣)。論點線操作含義:清單唔准做落注依據;注碼上限與十年持有期預期由基礎率定形。

- 決策：
  1. KARST-141 結論收貨;論點線判別清單定性為「假設清單,不准落注」
  2. 論點線下一步=客觀樽頸標籤票(141/142 共同指向),排入衛星隊列,等 KARST-143 與個股層總裁決一併排
  3. 基礎率三個數(十年 2-7%/五年 <0.3%/中位 2.3-3.3 倍)列為論點線注碼與持有期紀律嘅定形依據,寫入日後論點線制度票

- **用戶原話（原文照錄）**

  > (用戶未裁;屬 D-072 授權內收案)

- 影響：衛星三線現況:論點線(判別力在文本,清單不落注)、LLM 漏斗(押行得通,等標籤)、修訂活線(等存檔裁決);三線下一步全部匯合喺「個股層總裁決」一場。

## D-121 KARST-143 收案:平穩六隻拖累只得 0.82pp(判詞「懲罰可壓」,不足判準下限一半),但同時推翻兩條前提——①「4pp 固定學費」講法錯:拖累=持倉自己月度上落嘅半方差,五個組合逐行吻合(平穩 0.82/動能 3.80/深度價值 5.61),而基準本身都喺度交(SPY 1.24、XLK 2.72),前兩票攞絕對拖累對隱含為零嘅基準,單位錯配;動能對真對手 XLK 只多 1.1pp 唔係 4pp;②KARST-140「便宜股蝕 7.9%」係假數:實作偏離自己規格,用月底價揀股再收同月已發生升跌,帶一個月前視,正確對齊後 +20.76%(但同樣不可當前瞻預期,深度價值正是倖存者偏差咬最深嗰格;正確講法只有「−7.9% 係假,真值未知」)。壓走懲罰嘅代價貴過懲罰本身:27 池收窄到最平穩六隻一年蝕 2.19pp(8.08% 對 10.25%),甚至低過同池閉眼亂抽六隻(10.02%);扣成本淨年化 7.48%,輸 SPY 9.07% 同 XLK 11.46%,零成本假設下仍輸大市。回調笨規則(用戶玩法最簡機械版)不成立:340 次入場、平均持 3.17 個月、六格平均只填 3.5 格,淨 7.74% 輸大市,剔走 SPY 補位後自揀股每月 0.60% 對 SPY 0.80%——親手揀嘅每注平均輸乾坐 SPY 0.20pp/月,而且買 dip 令最大跌幅由 −30.1% 惡化到 −43.1%
- 類型：決策
- 狀態：有效
- 日期：2026-09-02

- 出處：KARST-143 交付(票已關,四條驗收剔齊,判準與參數跑數前獨立 commit,重跑逐位重現 KARST-140 六個數證明管線忠實,生產庫倉根 karst.sqlite 雜湊 b168e9f45b578cf9 不變)。A-034/A-035 入假設冊,善後票 KARST-144 已開。正本 research/2026-09-02-平穩六隻懲罰下限.md、experiments/2026-09-02-calm-concentration/。主 agent 依 D-072 收案。

- 背景：主 agent 立場(D-110,含自我更正):我前三次向用戶轉述嘅「揸六隻每年固定蝕 4pp」講法錯,錯在單位——基準自己都有同類拖累,應該報差額唔係絕對值;呢個錯係我轉述時放大嘅,唔止 agent 嘅事。更正後個股層收檔嘅理由書要重寫:舊理由(4pp 固定學費、便宜股蝕 7.9%)兩條全部作廢,仍立得住嘅只剩兩條——四個家族之中三個扣成本贏唔到乾坐 XLK;唯一表面贏到嗰個(深度價值 +20.76%)正正係現有數據永遠證唔到嗰個(倖存者偏差最深:1,209 家曾做成分,面板只得 585 隻,逾五成缺席)。agent 押收檔,把握中等偏高。

- 決策：
  1. KARST-143 結論收貨;「4pp 固定學費」與「便宜股蝕 7.9%」兩個講法作廢,不得再引用
  2. 個股層收檔裁決仍未落,但理由書必須重寫後先上 gate——用戶有權按更正後嘅盤數重新判
  3. 唯一值得留嘅尾巴=含已除牌公司嘅美股歷史數據源勘察票(同時解 A-033/A-035 與本票倖存者上限,三張撞同一堵牆);其餘建置票維持凍結
  4. 用戶親裁一格(生意判斷非數據判斷):平穩六隻係全線唯一做到「大市跌 8% 佢只跌 3.4%」、按每單位上落計回報最好嗰個;若帳目線目標由『贏科技板塊』改為『跌市守得住』,呢格唔係廢物——但嗰係換目標,唔係翻案

- **用戶原話（原文照錄）**

  > (用戶未裁;理由書重寫後再上 gate)

- 影響：個股層四張實測票(139/140/143)嘅盤數重排;倖存者數據源成為三張票共同樽頸,係目前唯一有價值嘅後續票候選。

## D-122 KARST-145 收案:擇時層 504 格掃完(6 入場掣 × 7 離場掣 × 6 範圍 × 2 選股代用品,2005–2026 日線,判準跑數前凍結 49b0a70)——嚴格平原(同贏 SPY 與 XLK)零格;寬鬆平原(只贏 SPY)一片 24 格但功勞不在擇時:同池零擇時 15.97% 高過平原中位 15.23%,前瞻收益率半邊 252 格只有 22 格贏得過自己的無擇時版本(中位差 −4.22pp);離場軸單調——跌出池 12.97%(年換手 1.8)→ 時間止蝕 → 止蝕 → RSI2 超買 5.44%(換手 28)→ MA20/50 死叉 −12.08%(換手 80),做得越少越好;入場軸六個掣中位全落 9.70–10.77% 無分辨力;冠軍格 20.02% 判孤峰(鄰域中位 16.18% = 其無擇時版本 16.21%,最深跌幅 −63.1%);「贏運氣帶 186/504」屬成本口徑假象,零成本對零成本掃描格中位 11.88% 反輸隨機抽 16.0–16.7%。附帶推翻 A-028:前瞻收益率的預估凍結於業績公布日而非排名日,一季洩漏憑空造出每年約 4.8pp(零洩漏 TTM 排序 11.0–11.2% 對 SPY 10.9% 無優勢;一季洩漏 15.9%;四季洩漏 22.9–25.8%,成績單調跟洩漏長度走)
- 類型：決策
- 狀態：有效
- 日期：2026-09-02

- 出處：KARST-145 交付(票已關,四條驗收剔齊;判準與 504 格參數跑數前獨立 commit 49b0a70 且一字未改;接手隊跑數前修正三處引擎缺陷——同日成交、成本重複計、隨機種子不可重現——方向全部令成績變差或可重現;生產庫倉根 karst.sqlite 只讀雜湊 b168e9f45b578cf9 不變;日線 20MB 不入 git)。正本 research/2026-09-02-擇時層全景圖.md、experiments/2026-09-02-timing-sweep/(含 leak_check.py 洩漏診斷)。A-028 已由該票改為推翻並寫入假設冊;KARST-136/137 已留言觸發後果條款(不倒推階段)。主 agent 依 D-072 收案。

- 背景：本票由用戶 2026-09-02 質疑觸發(原話:「I think you are too rushy to use 1 dimension to kill the forest」),點名 RSI2 bar size、範圍、死叉離場三個未試維度,現已全部納入掃描。主 agent 立場(D-110):用戶質疑的一半成立——一條笨規則確不足以判死擇時層;現在是四十條規則、完整地形圖,結論不變但有了地形支撐,而且結論不是靠幾格數字,是靠一條單調的離場軸,把握頗高。另一半:此票最反直覺的發現不是擇時無效,而是「擇時掣本來就在扣分」,所以此前收檔理由書若含「加了擇時掣都救不回」這條推理,該推理站不住,要換。A-028 推翻的影響超出個股層:KARST-136 前瞻序列是板塊層資產(D-109 用戶裁決全面轉前瞻),KARST-137 板塊層 RSI2 前瞻臂的候選 C-137-A 建基於「低洩漏線足以隔離」——此前提現已為假,D-111 第 3 條寫明「A-028 查證是前瞻臂一切判詞的先決條件」,先決條件反向落地。

- 決策：
  1. KARST-145 結論收貨;擇時層在日線至月線粒度、四十條規則範圍內判為「不是優勢來源」,不再開新的擇時規則試探票;寬鬆平原 24 格不入候選庫(其贏 SPY 的功勞屬選股池而非擇時掣,且該池成績本身受 A-028 洩漏污染)
  2. A-028 推翻的後果落地:D-111 第 2 條候選 C-137-A 撤出候選庫;KARST-136 前瞻盈利收益率序列保留為觀察台資料資產(兩條線照樣並排顯示),但在砌出真正按排名日定格的預估之前,禁止用作任何排序、訊號或考試輸入;KARST-137「前瞻分母救返 2013 後」判詞作廢,重審另開新票
  3. 個股層收檔理由書改寫規則追加兩條:不得寫「四件套過濾器已證無效」(從未測過);不得用「加了擇時掣都救不回」作推理(擇時掣本身在扣分);D-121 已作廢的「4pp 固定學費」「便宜股蝕 7.9%」照舊不得引用
  4. 個股層總裁決現在上 gate,連同帳目線建置(成本已由「幾星期」重估為一張票、數小時至一日,且順帶解決三張票共同撞到的倖存者牆)與 KARST-143 留給用戶的目標重設一格,一次過交用戶裁

- **用戶原話（原文照錄）**

  > (用戶未裁;屬 D-072 授權內收案。用戶 2026-09-02 質疑原話:「I think you are too rushy to use 1 dimension to kill the forest. To be honest. a lot of things to tune.」)

- 影響：個股層四張實測票(139/140/143/145)全部收案,系統線的實測結論收窄為:兩個代用品選股層乾淨量度之下無優勢、擇時掣在其上只減不加;用戶真正要的四件套仍然未測。板塊層前瞻線由「有條件候選」退回「資料資產、訊號禁用」,D-109 路線需要真正的歷史定格預估才能重啟。倖存者牆(A-033/A-035)與帳目線建置合併為同一件工作。

## D-123 用戶裁決三格(2026-09-02,個股層總裁決第一輪):①建帳目數據線(美國證監會檔案庫全宇宙公司帳目,逐月知情時點面板),測完四件套過濾器再裁個股層系統線生死——收檔裁決由「即裁」改為「待四件套實測」;②板塊層盈利收益率(倍數)線是否停止投入不即裁,用戶要求先做對抗覆核「是否真的無路可走」,覆核回報後再裁;③選股目標維持「賺得比科技板塊 ETF 多」,不改為「跌市蝕得少」,平穩六隻組合維持判死
- 類型：決策
- 狀態：有效
- 日期：2026-09-02

- 出處：用戶 2026-09-02 對主 agent 三條原生選項問題的回覆(quote 欄原話)。主 agent 先以白話重講三格背景(帳目線=公司成績表、倍數線=市盈率倒轉排板塊、平穩六隻=跌市守得住但長期跑輸)後用戶方作答。

- 背景：主 agent 立場(D-110):①同意建——一日成本換「測過」而非「猜過」,且順帶把已除牌公司的帳目補回(帳目面倖存者缺口修補;價格面缺口仍在,須在票內明寫);對四件套建成後能贏 XLK 的機會看不到一半,但令收檔理由書變真這一點把握高。②用戶不即接「停」而要求對抗覆核,合理——D-108/109/111 與 KARST-145 洩漏診斷疊起來的結論是「兩個版本都無乾淨優勢」,但未有人系統地列過未試路徑(不偷看的預測重建、評級動作史作前瞻代理、板塊數目太少等),覆核值得一張票;主 agent 押覆核結果仍是「停」,把握中等。③同意維持「賺得多」:同等防守用少揸股票多揸 SPY 更便宜,一次跌市不足以判防守力。

- 決策：
  1. 開帳目數據線建置票:美國證監會 companyfacts 全宇宙(標普 500 歷史成分 1,209 家,含已除牌)下載並整理成逐月知情時點面板(每個月底只用該日之前已申報的數字);本票只建數據與覆蓋率報告,四件套實測另開下一張票
  2. 個股層系統線收檔裁決押後至四件套實測回報;收檔理由書改寫規則(D-121/D-122)不變
  3. 開倍數線對抗覆核票(task + kira:redteam):攻擊「板塊層盈利收益率線已無路可走」這個結論,列出所有未試路徑並估量級與成本;覆核前該線維持 D-122 狀態(觀察台顯示、訊號禁用、不新投入)
  4. 選股目標維持「贏 XLK」;平穩六隻維持判死,不因防守力翻案

- **用戶原話（原文照錄）**

  > 用戶 2026-09-02 原話:「建,測完再裁個股層(建議)」;「Can I ask you to do a adversial review to try to explorer if really nothing can do further?」;「賴得多(建議)」(選項原文「賺得多」)。

- 影響：個股層由「等收檔」轉為「等四件套實測」;板塊層倍數線由「準備停」轉為「等對抗覆核」;帳目面板成為兩線共用資產。

## D-124 KARST-147 收案:倍數線對抗覆核裁決「停」站得住(把握約 85%),但主 agent 的理由書兩處錯要改——正確死因不是「測過無效」,是「量不出」:①神諭上限已為零(KARST-133 用事後真實盈利做分子掃 116 格,命中率 33.65–34.20% 貼死 33.33% 亂猜基礎率,所有「把預測砌得更準」的路一次過封死);②棋盤沒有解析度(九隻板塊月度回報兩兩平均相關 0.578,等效獨立板塊只有 1.60 隻;2013 後持三隻要 t=2 需真優勢每年 3.60pp,文獻級數只有 1.3–2.0pp,永遠量不出);③目標對不上(2013 起 SPY 14.83%、XLK 21.83%,案卷唯一乾淨正數換算約 17% 仍輸 XLK 近 5pp)。五條未試路徑全封:歷史網頁快照重建(14 隻股 57 個快照只 27 個解析得出、全落 2018-05 至 2022-11,而需要約 17 萬個定格)、分析員升降級動作史(Boni & Womack 已測:行業層無增量預測力,屬動量化身)、後顧線換口徑、板塊數目、由下而上匯總——最後一條不是倍數線的路,是個股層「行內價值」的路
- 類型：決策
- 狀態：有效
- 日期：2026-09-02

- 出處：KARST-147 交付(票已關,四條驗收剔齊,只讀未動其他票,生產庫倉根 karst.sqlite 雜湊 b168e9f45b578cf9 不變)。正本 research/2026-09-02-倍數線對抗覆核.md,commit 55425d4。用戶 2026-09-02 要求本覆核(D-123 第 3 條)。主 agent 依 D-072 收案。

- 背景：主 agent 立場(D-110):覆核推翻的是我的理由,不是我的建議——我之前對用戶講「兩個版本都測過無優勢」,其中「後顧版無優勢」講過頭(後顧季頻橫截面四族全平原、2013 後 +2.0/+2.6pp,零預估洩漏,我略去了;且與 D-108 未和解),而洩漏 5pp 是在個股層量的,板塊層從未直接量。認錯。但「量不出」比「無效」更徹底:D-099/D-100 早已寫明「神諭上限無平原=整條倍數線收檔」,KARST-133 的上限結果正是零,這條線其實在 D-101 主軸修正後就應該停,是我們用 D-109 轉前瞻把它延了兩日。覆核另指出:倍數這個念頭沒有死,死的是「用它排九隻板塊」;估值有用的地方是行業內部揀公司,即 KARST-146 正在建的「行內價值」。另記待查:KARST-136 的 3.9% 事後改寫率量在不含 VLO 的樣本上,加 VLO 多出四個被改寫財季(預估動 2–10%),方向上加強「停」。

- 決策：
  1. KARST-147 結論收貨;板塊層倍數線(後顧與前瞻兩版)收檔理由書改為「量不出」三條(神諭上限為零、九隻板塊只有 1.6 隻獨立資訊、目標對不上),不再寫「測過無效」;D-122 對該線的處置(觀察台顯示、訊號禁用、不新投入)維持,待用戶確認「停」
  2. 偵測地板入決策簿作攔路石:任何板塊層橫截面排名訊號(九隻 ETF 互排)要在 2013 後達 t=2,真優勢須每年 ≥3.6pp;開票前必先寫出該訊號的文獻量級,低於 3.6pp 的一律不開實測票,直接歸檔為「量不出」
  3. 五條未試路徑全部歸檔為不開票,理由各如 title;分析員升降級動作史(設計方案候選丁)在板塊層作廢,在個股層的去留待四件套實測票一併裁
  4. 板塊倍數每日存檔(D-086)照 D-100 第 3 條即日停止,材料保留;KARST-136/137/145 三票不補指路留言,以本條決策交叉引用代替

- **用戶原話（原文照錄）**

  > (用戶未裁「停」;用戶 2026-09-02 要求覆核原話:「Can I ask you to do a adversial review to try to explorer if really nothing can do further?」)

- 影響：板塊層估值訊號全部收檔;倍數念頭移交個股層「行內價值」一格;板塊層剩下的主線只有市況層與已入候選庫的格。偵測地板成為日後任何板塊層新訊號票的硬門檻。

## D-125 用戶確認板塊層倍數線收檔(2026-09-02,原話「確認停(建議)」,依 D-124 理由書「量不出」三條);同時 KARST-146 收案:帳目面板建成——718 家(506 家仍在指數、212 家已除牌補回)、2009-04 至 2026-08、逐月 123,754 格 × 11 欄,知情時點逐格核過違規 0 格;靠得住欄位:純利、總資產、股東權益、經營現金流、現金、攤薄股數、營業額(2012 起覆蓋 ≥95%);靠不住:毛利僅五成、總負債僅七成(銀行保險地產公用事業結構性不申報毛利,非抓漏);經營現金流與資本開支實際一年更新一次(滾動和 92%/79% 靠全年數砌,最舊落後 15 個月);有帳目無價格 84 家(81 家已除牌),倖存者缺口只修一半;2010 年前除牌的 361 家不可能補回;126 家成分股查不到 CIK;A-036 推翻(companyfacts 端點已濾走自訂標籤,「只有自訂標籤」一格恆為 0 屬端點限制)
- 類型：決策
- 狀態：有效
- 日期：2026-09-02

- 出處：用戶 2026-09-02 對原生選項問題的回覆(quote 欄);KARST-146 交付(票已關,四條驗收剔齊,規則兩次先行 commit dce6fc2/daf7294 均在面板數字產生前,收檔 commit d776d64;生產庫倉根 karst.sqlite 開工收工雜湊同為 b168e9f45b578cf9;12.1MB parquet 與 2.5GB 原始 JSON 不入 git)。正本 research/2026-09-02-帳目面板建置.md、experiments/2026-09-02-fundamentals-panel/。主 agent 依 D-072 收案。

- 背景：主 agent 立場(D-110):①面板是真資產,第一次令四件套可測;②agent 交上來三格待裁,我裁兩格留一格:總負債用「總資產減股東權益」倒算補回(會計恆等式,少數股東權益誤差可接受,加旗標欄)——裁做;126 家缺 CIK 用 SEC company_tickers.json 與全文搜尋補查,限一小時,做不到的列名單——裁做,併入下一張票的準備步;已除牌 81 家股價要否付費購買屬開支,交用戶,我建議押後:先在 718 家有價格的樣本上測四件套並報「當時存在但不可買賣」家數,四件套若無優勢則不必花錢,若有優勢才買數據做倖存者核實;③經營現金流與資本開支年更一次,直接影響下一張票設計:投資紀律一項不得按月重算,四件套實測的換倉頻率應為季度(業績季後)而非月度,擇時層已證只減不加(D-122),所以下一張票不含任何入場離場掣。

- 決策：
  1. 板塊層倍數線(後顧與前瞻)正式收檔:觀察台兩條線保留顯示,訊號禁用,不再開票;板塊倍數每日存檔照 D-100/D-124 停止
  2. KARST-146 結論收貨;帳目面板列為個股層正本資料資產;毛利與總負債兩欄標記「結構性缺失」,任何用到它們的篩選必須先報剔走的行業分佈
  3. 總負債以總資產減股東權益倒算補回並加旗標欄;126 家缺 CIK 限時一小時補查——兩項併入四件套實測票的準備步,不另開票
  4. 已除牌 81 家股價是否付費購買押後,待四件套實測結果:無優勢不買,有優勢才買作倖存者核實
  5. 四件套實測票設計約束:季度換倉、不含任何擇時掣、投資紀律用年更數據、2009-04 起研究窗;四件套具體定義須先與用戶對齊(D-038 參數建置期對齊)後才開票

- **用戶原話（原文照錄）**

  > 用戶 2026-09-02 原話:「確認停(建議)」

- 影響：板塊層估值線全部收檔;個股層由「等數據」轉為「等四件套定義對齊」;倖存者缺口的價格半邊延後至實測後裁。

## D-126 用戶對齊四件套過濾器定義(2026-09-02,依 D-038 參數建置期對齊):盈利能力=經營現金流÷總資產;投資紀律=總資產一年增長率,只剔走同行內膨脹最快兩成(不作排名);行內價值=已公布純利÷市值,同行內排名(不用預測);修訂延續=過去六個月分析員升級減降級淨次數(數據 2012 起,另測);做法=每季每板塊用前三件揀頭三隻共 27 隻等權、無任何擇時掣、每邊 15bp、對手 SPY 與 XLK;開四件套實測票
- 類型：決策
- 狀態：有效
- 日期：2026-09-02

- 出處：用戶 2026-09-02 對原生選項問題的回覆(quote 欄原話)。主 agent 先以白話表列四條量法與做法(含「ROE 可靠借錢谷高故不用」「只剔極端不誤殺增長股」「用已公布純利不用預測」三句理由)後用戶方作答。

- 背景：主 agent 立場(D-110):四件套扣成本贏 XLK 的機會看不到一半,但這是個股層系統線第一次真測,測完答案照講。設計約束來自 D-122(擇時只減不加,故無掣)與 D-125(現金流年更,故季度換倉)。實測票依考試協議第七節屬探索,不產生及格;判準跑數前凍結;要同時報三件單獨的分辨力,免得合成分數掩蓋哪一件在做功。

- 決策：
  1. 四件套定義與做法照 title 定案,寫入個股層設計方案作為現役參數;日後改動須再對齊
  2. 開 KARST-148 四件套實測票(research,探索不產生及格):前三件 2009-04 起,第四件 2012 起另測;判準與鄰域格(每板塊頭 2/3/5 × 膨脹剔除 10/20/30%)跑數前凍結;基準四條(SPY、XLK、同池等權、換倉頻率對齊的隨機 27 隻運氣帶);準備步含總負債倒算與 126 家 CIK 補查
  3. 已除牌 81 家股價維持押後(D-125)

- **用戶原話（原文照錄）**

  > 用戶 2026-09-02 原話:「照建議開票(建議)」

- 影響：個股層系統線進入第一次真實測;結果決定 D-121/D-122 押後的收檔裁決。

## D-127 用戶設定新總目標(2026-09-02):持續尋找任何可能的優勢、驗證並不斷改進策略;唯一原則是決策次序由上而下——市況(market)> 價值鏈(value-chain)> 個股(individual)> 技術觸發(TA triggers);方法論、工具、技術指標不設限,鼓勵跳出框框、大膽假設,先做初步存在性證明;之後交出找到的五個最佳策略與用戶討論
- 類型：決策
- 狀態：有效
- 日期：2026-09-02

- 出處：用戶 2026-09-02 原話(quote 欄)。主 agent 依 D-072 接棒執行,不逐步請示。

- 背景：主 agent 立場(D-110):①接受總目標,但兩點先講明——樽頸文本掃描目前只是「零誤報、樣本六份中兩份命中」的苗頭(D-119),是值得追的方向,不是已證明的優勢,我不會把它記成成功;②「由上而下」次序與 D-052–057 三層架構一致,價值鏈一層是新的中間層(介乎板塊與個股之間,用戶早前提過「行內 RS 或價值鏈內 RS」),需要在詞彙表定義;③已定案的攔路石照用:偷看零容忍、倖存者聲明、板塊層偵測地板 3.6pp(D-124)、擇時只作最後觸發不作獨立訊號(D-122)、探索票不產生及格(考試協議七.7)。執行形狀:先開一張假設長名單票(跳出框框列 ≥20 條,每條附文獻量級、倉內或免費數據可行性、偷看/倖存者風險、幾小時內做得到的存在性測試設計),再由主 agent 揀約八條並行做初步存在性測試,最後選五條交用戶討論。

- 決策：
  1. 新總目標登記為現役路線,取代「個股層收檔與否」單一議題;四件套實測(KARST-148)照跑,作為個股層第一條候選
  2. 價值鏈(value chain)登記為第二層決策單位,定義入 CONTEXT.md:同一條供應鏈或需求鏈上互相牽動的公司群,可跨 GICS 板塊;其量法由假設長名單票提出
  3. 開假設長名單票(KARST-149):四層各列大膽假設,附量級、數據可行性、風險、存在性測試設計;主 agent 由此揀約八條開初步測試票,最後五條交用戶
  4. 存在性測試的通用門檻:判準跑數前凍結、四條基準(SPY/XLK/同池等權/換倉對齊的運氣帶)、誠實三格(倖存者/偷看/多重測試)入首段、不產生及格

- **用戶原話（原文照錄）**

  > 用戶 2026-09-02 原話:「Goal set: I would like you to continue finding any possible edges and validate and keep on improving the strategy. Like the Bottleneck we have made a preliminary great success on those. I would like you to continue exploring the strategy with only 1 principle is that the decisions should be from the top (market) > value-chain > individual > TA triggers. You can use any methodology, you can use any tools or measure of TA. Think out of the box. 大膽假設 then preliminary to proof the existance first. Give me the 5 best strategy you find out later and discuss with me」

- 影響：研究路線由「逐條線收檔」轉為「廣搜優勢、快證存在」;既有攔路石全部保留,不因廣搜而放寬。

## D-128 用戶補充新總目標(2026-09-02,續 D-127):廣泛分頭研究、設實驗、由第一原理思考;目標是找到能長期跑贏標普、年化 30% 或以上級數的策略(原話「like 30% or above annualized if possible」);先探索;允許任何技能、技術與網上研究
- 類型：決策
- 狀態：有效
- 日期：2026-09-02

- 出處：用戶 2026-09-02 原話(quote 欄)。主 agent 依 D-072 接棒。

- 背景：主 agent 立場(D-110,不附和):①30% 年化持續數十年,在公開紀錄裡幾乎不存在——巴菲特約 20%(50 年)、公開因子策略 15–20% 且回撤深;文獻中超過 30% 的多屬容量極細的私人基金或短時期。所以我押「30% 持續三十年」不可能,把握高;但「30% 持續五至十年」在集中、長揸、容量細的打法(散戶結構優勢:無容量約束、無基準壓力、可揸小型與非流動、可集中)有存在空間,把握中低。②倉內神諭曲線已量出上限空間極大(個股層事後全知 1,190%/年,板塊層 105.7%/年),問題從來是準繩度不是空間;30% 目標把「所需準繩度」推得很高,所以每條新假設都要先算「達 30% 需要的命中率」再決定值不值得測。③既有攔路石全部不放寬。執行:在 KARST-149 假設長名單之外,再分兩隊——(甲)公開紀錄研究:誰真的做到 30%+、用什麼機制(集中度、持有期、槓桿、容量、時期),用來校準目標與策略形狀;(乙)第一原理推導:散戶相對機構的結構優勢在哪裡、超額回報的來源(誰被迫交易/誰在犯錯)、由此推出符合由上而下原則的策略形狀,並為每個形狀算出達 30% 所需的命中率與持有期。三隊回報後主 agent 揀約八條開存在性測試,最後五條交用戶討論。

- 決策：
  1. 目標登記為「年化 30% 或以上,跑贏標普」,但以「五至十年可持續」為工作定義,不以三十年為準;每條候選策略必報「達 30% 所需命中率/持有期/集中度」與「文獻中同類打法的實際紀錄」
  2. 開 KARST-150 公開紀錄研究票(誰做到 30%+、機制、容量、時期、失敗者名單)與 KARST-151 第一原理推導票(散戶結構優勢、超額回報來源、由上而下策略形狀與所需命中率);與 KARST-149 三票平行,互不通氣
  3. 存在性測試門檻(D-127 第 4 條)不變;30% 目標不得成為放寬偷看、倖存者或多重測試紀律的理由

- **用戶原話（原文照錄）**

  > 用戶 2026-09-02 原話:「try to fan out to research or setting experiment or thinking on first principle. And I want to get the great strategy which can beat S&P like 30% or above annualized if possible of level. Explore first. You are allowed to use any skills or technique or web research」

- 影響：研究由「找優勢」升級為「找 30% 級數的優勢」,主 agent 立場已登記:三十年不可能、五至十年有空間但把握中低;所有候選都要先過「所需命中率」這一格。

## D-129 KARST-148 收案:四件套過濾器實測(用戶對齊 D-126)——合成臂 2010-03 至 2026-08 每邊 15bp 年化 11.2%,SPY 14.5%、XLK 20.5%,輸 SPY 3.3pp、輸 XLK 9.3pp,最大跌幅 −45.4%,兩個分期都輸;三件無一做功(盈利能力 12.7%、投資紀律剔除臂 13.5% 比不剔 13.7% 更低、行內價值 10.4%),合成比單用盈利能力更差;修訂延續 2013 起 +0.9pp 仍在運氣帶內;鄰域九格 11.2–13.1% 無一格達 SPY,判「無平原」(地形平但平在輸的水平);唯一苗頭=資產增長最慢三隻 15.1% 贏 SPY 0.6pp、升穿運氣帶上緣,但超出 D-126 定義(投資紀律不作排名),只入候選庫,仍輸 XLK 5.4pp;順手拆出拆股市值陷阱(申報時股數 × 已調整價格令申報後拆股公司市值低估數倍,不修正合成臂假顯示 16.6% 贏 SPY,假優勢每年 5.2–5.4pp,已修正入詞彙表)。同時登記用戶對「價值鏈」的定義修正:價值鏈=產業鏈,鏈再分「鏈層」,同層=鏈上同位置、對市場講同一個故事、行業消息衝擊相似的一群公司
- 類型：決策
- 狀態：有效
- 日期：2026-09-02

- 出處：KARST-148 交付(票已關,四條驗收剔齊;判準凍結 commit efe5d08 一字未改,收檔 580d58b;偷看核對 22,934 格零違規;生產庫倉根 karst.sqlite 開工收工雜湊同為 b168e9f45b578cf9)。正本 research/2026-09-02-四件套實測.md、experiments/2026-09-02-fourpiece-test/。用戶 2026-09-02 價值鏈定義原話見 quote 欄。主 agent 依 D-072 收案。

- 背景：主 agent 立場(D-110):①我事前押「四件套贏 XLK 機會不到一半」,結果比預期更差——連 SPY 都輸,而且三件單獨全部不做功,這與 KARST-141(傳統質素篩選事前分不出 10× 贏輸)和文獻一致;個股層系統線(機械篩選揀股)作為優勢來源至此已測到底:價格代用品(139/140/143)、擇時掣(145)、帳目四件套(148)三路全部輸給乾坐 XLK。我押收檔,把握高;收檔理由書現在寫得真,因為四件套真的測過了。②帳目面板本身保留為資料資產——價值鏈層與論點線都會用到它。③「資產增長最慢」那個苗頭:文獻上資產增長效應(Cooper-Gulen-Schill 2008)是已知的,但在這個宇宙只贏 SPY 0.6pp 且輸 XLK 5.4pp,不足以撐一條線,列候選不追。④用戶的價值鏈定義比我先前寫的窄而可驗證(核心=同層對同一消息反應相似),已更新詞彙表並即時傳給正在跑的 KARST-149/151 兩隊;舊倉 KarstETF 的 98 個代表公司分層表正在找,找到就成為鏈層的第一版人手表。

- 決策：
  1. KARST-148 結論收貨;個股層系統線(機械篩選揀股)收檔理由書定稿引用 139/140/143/145/148 五票:價格代用品、擇時掣、帳目四件套三路皆輸 XLK;不得寫「四件套未測」——現在已測;收檔本身上 gate,與五策略討論一併交用戶確認
  2. 帳目面板(KARST-146)維持為個股層與價值鏈層共用資料資產;「資產增長最慢」入候選庫不開票
  3. 拆股市值陷阱入詞彙表與派工守則:凡用申報股數計市值,必須用申報當日未調整價格或同步調整股數;日後任何用市值的票開票必寫此條
  4. 價值鏈定義照用戶修正更新 CONTEXT.md(價值鏈=產業鏈;新增「鏈層」條目);KARST-149/151 兩隊已收到新定義;舊倉 KarstETF 分層表由 Explore 隊尋找,找到則列為鏈層第一版人手表,待用戶覆核

- **用戶原話（原文照錄）**

  > 用戶 2026-09-02 原話:「value chain to me is 產業鏈, and if you refer to KarstETF value chain can further break down into layers, it is defined as at 1 layer with companies sharing the same position with the same story or narrative in the market. So if any news or any update of the industry, the same layer will have very similar impact. So the same layer should be also the same business or position of 上下遊」(收檔一格用戶未裁)

- 影響：個股層系統線實測全部完成,結論一致為輸;研究重心正式移到價值鏈/鏈層(第二層)與論點線(樽頸文本),等 149/150/151 三隊回報後揀存在性測試。

## D-130 用戶指示(2026-09-02):鏈層的分類方法可由 agent 調整——舊倉只有字面定義、沒有更好的分類法;初步判斷 AI 時代的優勢更多在非結構化/文本資訊,價值鏈(敘事/故事視角)的分組比行業或 GICS 分組更有價值,因為 GICS 只是為過去的索引與分組而設,而今同一板塊內的玩家差異太大;敘事分組應是所有優勢的起點
- 類型：決策
- 狀態：有效
- 日期：2026-09-02

- 出處：用戶 2026-09-02 原話(quote 欄)。主 agent 依 D-072 接棒。

- 背景：主 agent 立場(D-110):同意兩點、挑戰三點。同意:①KARST-141/142 已顯示唯一乾淨的判別力在文本(D-119/D-120),與用戶方向一致;②GICS 是為指數編製服務的靜態分類,NVDA 與 INTC 同屬半導體但故事相反,用戶的觀察成立。挑戰:①敘事標籤最容易偷看——「AI 晶片鏈」這個故事是股價升完才被市場命名的,用事後的故事分組再量該組回報,等於 KARST-140 印象標籤(A-032)的翻版;所以敘事分層必須用當時的文本(10-K 業務描述、電話會議逐字稿,按申報日定格)由機器分,不用今日的認知;②同層共同波動有一部分只是共同的因子曝險(規模、動量、板塊),存在性測試必須量「扣走市場與板塊之後」的殘餘相關,否則量到的是板塊;③AI 時代人人有 LLM,「讀得快」不是優勢,散戶的真優勢是願意在一個敘事上集中、長揸幾年而機構不能——所以敘事分層是起點,但優勢要在「層級敘事轉折(如樽頸在文本出現)→ 層回報」這一步才成立。執行:即開 KARST-152 敘事鏈層存在性測試(不等 149 回報,因為這一格已由用戶定為起點):用按申報日定格的 10-K 業務描述做機器分層(先用不需 API 的 TF-IDF 聚類,再視需要升級),三個年份切片,量同層殘餘回報相關是否顯著高於同 GICS 子行業;另用舊倉 98 代表人手表直接驗「同層比同 GICS 更同步」。

- 決策：
  1. 鏈層分類方法由 agent 定義與調整,舊倉人手表降為對照組之一;任何分層必須按申報日定格(point-in-time),禁止用今日認知或事後命名的故事回頭分組
  2. 「敘事分組是所有優勢的起點」登記為現役工作假設 A-037(若假:同層殘餘相關不高於 GICS 子行業,則價值鏈層無解析度優勢,由上而下第二層要另找單位)
  3. 開 KARST-152 敘事鏈層存在性測試,判準跑數前凍結;結果與 149/150/151 一併進入五策略遴選
  4. KARST-149/151 兩隊即時收到本指示:價值鏈層提案以敘事/文本分層為主,GICS 只作對照

- **用戶原話（原文照錄）**

  > 用戶 2026-09-02 原話:「but I think you need to chain-layers definition. But at that time, although we have a liternal means of definition but we don't have any better way of classification. In case you think is needed you can adjust the layer itself. Prelimary, I think with the age of AI, maybe the edge in more on the unstructured data or the text based information. So Value-Chain which is narrative / story point of view, should be more valuable than industry or GICS point of view. as the latter is just trying to fit a classification just for indexing or grouping in the pass. But nowadays the different player within the same sector is too different. I think the grouping should be sticked with the narrative is more making sense as the starting point of all edges」

- 影響：由上而下第二層的單位由「板塊」正式改為「敘事鏈層」;文本數據線(10-K、逐字稿)升為核心原料,帳目面板與價格為配角。

## D-131 KARST-151 收案:第一原理推導——年化 30% 不是選股問題是賠率結構問題:任何策略的長期複合年化封頂於「無風險利率 + 夏普平方÷2」(最佳槓桿下的增長率),以 4% 計 30% 需夏普 ≥0.72 且要加槓桿;巴郡四十年夏普 0.76 用 1.6 倍槓桿;倉內旁證 XLK 2013–2025 夏普 0.97 兩倍槓桿零選股可到 31.3%,但 2004–2026 全段夏普 0.70 上限 26.5% 加槓桿也不夠。命中率同一條算式:季頻常見賠率(+15%/−10%)需 72.8% 命中(不可能),三年 +400%/−50% 只需 43.1%,一年 +150%/−25% 只需 35.1%——「一注講不出四至五倍目標就不是 30% 策略的一注」。五個形狀:①鏈層(先量同層是否同動、等效獨立層數是否遠高於板塊層 1.60;本身不產回報但把可偵測下限由 3.6pp 拉低到約 1.5pp;1–2 小時)②市況層注碼調節(不改選股只改注碼,需市況閘每次熊市早於 −35% 減注;1 小時,D-049 前科)③股本供給(跟管理層自己買賣自己股票,1.5–2.5pp,2–3 小時,零預估洩漏)④產能週期(一層公司一齊擴產兩至四年後該層蝕錢,1.5–3pp,半日;KARST-148 唯一苗頭在此格)⑤樽頸鏈(買鏈上短期加得到價的那一層,一年 +150%/−25% 只需 35.1% 命中,半日)
- 類型：決策
- 狀態：有效
- 日期：2026-09-02

- 出處：KARST-151 交付(票已關,四條驗收剔齊,只讀未動其他票,生產庫倉根 karst.sqlite 雜湊 b168e9f45b578cf9 不變)。正本 research/2026-09-02-第一原理策略形狀.md,commit f80ecf6。主 agent 依 D-072 收案。

- 背景：主 agent 立場(D-110):①夏普上限那條算式是 Kelly 增長率的近似,前提是可以自由加槓桿且回報接近常態——散戶用槓桿 ETF 或孖展做得到但有波動拖累與爆倉尾巴,所以「30% 的數學入口在市況注碼」這句我接受一半:它是唯一乘數級的入口,但 D-049 準繩度檢驗曾把所有開關類訊號全部篩走,我押第一步再被篩走,把握中等。②「一注講不出四至五倍目標就不是 30% 策略的一注」是本票對用戶最有用的一句,它把 30% 目標從「揀股」改寫成「賠率結構」,與 D-120 基礎率(十年 10× 機率 2–7%)接得上。③agent 三格待裁:第一格(同層相似 + 等效獨立層數 >1.60)前半已是 A-037,後半補入 KARST-152 作事後診斷(判準已凍結不改);第二格同意(人手表只量解析度不回測);第三格(日線補成交量欄)同意,併入下一張用到它的票的準備步。

- 決策：
  1. KARST-151 結論收貨;「複合年化上限 = 無風險利率 + 夏普²/2」與「命中率門檻算式」列為五策略遴選的兩把尺,每條候選必報所需夏普或所需命中率
  2. 五個形狀全部進入遴選池,與 KARST-149/150/152 回報一併排序;鏈層(①)與樽頸鏈(⑤)已有票或苗頭在跑,股本供給(③)與產能週期(④)為新形狀候選
  3. KARST-152 追加事後診斷(不改凍結判準):敘事層的等效獨立層數,對照板塊層 1.60
  4. 日線面板補成交量欄併入下一張需要它的票的準備步,不另開票;鏈層人手表只量解析度不回測

- **用戶原話（原文照錄）**

  > (用戶未裁;屬 D-072 授權內收案)

- 影響：30% 目標有了數學尺:要麼夏普 ≥0.72 加槓桿(市況注碼入口),要麼長賠率注(四至五倍目標、35–43% 命中);五策略遴選兩把尺定形。

## D-132 KARST-149 收案:優勢假設長名單 26 條落檔(市況 6、價值鏈 8、個股 6、技術觸發 6),核心診斷=過去兩週判死的十一條線全死在同一場地(九板塊 1.6 隻獨立資訊),要換場地不是換訊號;價值鏈層已照 D-130 改為文本機器分層主線、GICS 與人手表降對照;前八條:鏈層存在性(152 主體)、年報文字改動大者回報差(文獻月 188bp)、同層敘事由需求轉供給受限、分批換馬+等風險注碣(組合數學省 1.9–2.8pp/年)、股數收縮(頂刊有據)、短倉比率(樣本外 R² 13%)、非價格宏觀狀態開關、帳目靜默修訂(無人做過)。KARST-151 補充(D-130 後重寫):形狀 H「敘事層二階效應時滯」有最強文獻背書——共同分析員覆蓋網絀溢出月 alpha 1.68%、t=9.67,且吸收產業/地理/客戶/技術四種連結動量(Ali & Hirshleifer 2020),即「比 GICS 好的分組器存在」已有硬證據,缺的是免費分組器,而那正是 LLM 今日做得到的事。主 agent 由此揀第一波存在性測試
- 類型：決策
- 狀態：有效
- 日期：2026-09-02

- 出處：KARST-149 交付(票已關,四條驗收剔齊,只讀;報告 research/2026-09-02-優勢假設長名單.md,被 KARST-151 的 commit 818ffe4 一併帶入,內容無損)。KARST-151 D-130 後重寫版同一 commit。主 agent 依 D-072 收案。

- 背景：主 agent 立場(D-110):①兩隊獨立得出同一結論——場地(分組單位)比訊號重要;我接受,並把 152 的等效獨立層數定為場地是否成立的硬尺(D-131)。②第一波存在性測試揀不依賴 A-037 的三條先跑,不等 152:年報文字改動(用戶「文本是優勢所在」的最直接檢驗,文獻量級最大,免費,查不到反方)、非價格宏觀狀態開關(30% 唯一乘數級入口,D-131;D-049 準繩度檢驗是死線,過不到當場判死)、帳目靜默修訂(倉內面板已存首版與修訂版兩欄,無人做過,便宜)。股數收縮列第二波(與股本供給合併,待 Form 4 抓取評估)。分批換馬+等風險屬執行改良非優勢來源,留給紙上交易前的執行票。短倉比率待數據源核實。③A-029 便宜修法(申報檔頭當時 SIC 碑作知情時點行業)接受,寫入任何行內排名測試的準備步。④自砌具名客戶鏈判死路,不開票。⑤commit 衛生:兩隊互相帶走檔案,派工模板加「commit 前核 git diff --cached --name-only」。

- 決策：
  1. KARST-149 結論收貨;26 條假設為遴選池正本;自砌具名客戶鏈不開票
  2. 第一波存在性測試即開三票:KARST-153 年報文字改動(Lazy Prices 形)、KARST-154 非價格宏觀狀態開關(市況注碼,D-049 準繩度為死線)、KARST-155 帳目靜默修訂;三票判準跑數前凍結、四條基準、不產生及格
  3. 第二波(待 152 回報或數據源核實):股數收縮+股本供給、短倉比率、同層敘事轉折、產能週期(層級)、樽頸鏈
  4. A-029 便宜修法(申報檔頭 SIC 作知情時點行業)寫入行內排名測試的準備步;派工模板收工段加「commit 前核 git diff --cached --name-only,只帶自己的檔」

- **用戶原話（原文照錄）**

  > (用戶未裁;屬 D-072 授權內收案)

- 影響：遴選池 26+5 條定形;第一波三條存在性測試開跑,連同 152 共四條實測平行;五策略討論的原料在第一波與 152 回報後齊備。

## D-133 KARST-150 收案:公開紀錄裡持續十年淨賺 30% 的只查到一個(文藝復興 Medallion 1988–2018 扣費後約 39%,1993 對外關門、規模鎖死約 100 億美元);連存疑一併算最多五個(Druckenmiller/Soros 無可核實正本且靠大槓桿;TQQQ/UPRO 成立日全在海嘯底未歷長熊)。「集中揸幾隻、不用槓桿、持續十年 30%」公開紀錄零例——最接近的巴菲特合夥人時期 LP 十三年實收 23.8%,天花板 20% 出頭。共同點:全部有容量上限且多數主動關門;毛淨落差 5–20pp;起點在便宜年份;機制只有高頻套戥/宏觀加槓桿/事件套戥三類。倖存者偏差:基金年消亡率 8.3–10.5%,報告報酬每年虛高 3.0–4.3pp,回填偏差另加 5.7pp;頂四分一基金四年後仍在頂四分一為 0.0%。算術硬牆:五年 30%=八隻倉要 2.6 隻五年十倍(基礎率 <0.3%,約 108 倍);十年 30%=八隻全部十年十倍仍不夠。誠實的十年目標 15–22%
- 類型：決策
- 狀態：有效
- 日期：2026-09-02

- 出處：KARST-150 交付(票已關,四條驗收剔齊,只讀;報告 research/2026-09-02-三十趴公開紀錄.md,算式 2026-09-02-hit-rate-math.py/.txt;commit 26c7bc5;生產庫雜湊 b168e9f45b578cf9 不變)。主 agent 依 D-072 收案。

- 背景：主 agent 立場(D-110):①與 D-128 我的判斷一致(三十年不可能、五至十年把握中低),但公開紀錄比我講得更狠:不用槓桿的集中長揸連十年 30% 都零例,誠實的十年目標是 15–22%——這一句要原樣告訴用戶,不修飾。②與 KARST-151 對讀,兩隊獨立得出同一結論:30% 要麼靠槓桿(市況注碼入口,KARST-154 正在測死線)、要麼靠長賠率注(樽頸鏈形狀),都不是「揀對股」。③散戶唯一真正的結構優勢是不受 100 億美元容量線約束——所以值得追的優勢一定是容量細、機構做不到或不屑做的:小型/非流動、集中、長揸、文本細讀。④我不會因此把用戶的目標改寫;目標由他定,我的責任是每條候選都報「達 30% 所需命中率或夏普」,讓他看見差距。

- 決策：
  1. KARST-150 結論收貨;「誠實的十年目標 15–22%、五年 30% 屬運氣區」列為五策略討論的開場事實,原樣交用戶,不由 agent 改寫目標
  2. 五策略遴選加一把尺:容量——優先容量細、機構結構上做不到的打法(小型/非流動、集中長揸、文本細讀);容量大的打法即使量到優勢也降權
  3. 倖存者偏差量級(報告報酬每年虛高 3–4pp)寫入日後任何引用外部紀錄的票的誠實聲明

- **用戶原話（原文照錄）**

  > (用戶未裁;屬 D-072 授權內收案)

- 影響：30% 目標的公開紀錄校準完成:三隊(149/150/151)結論一致——場地比訊號重要、30% 是賠率結構與槓桿問題、散戶優勢在容量;第一波存在性測試(153/154/155)與 152 平行開跑。

## D-134 原料文本唯一快取(用戶明令):EDGAR 為正本,倉內年報/申報全文只准一份副本,住 data/sec/10k_text/ 連 manifest.jsonl;實驗票只存衍生物(切節、分層、面板)並記 accession;抓之前先查 manifest,已有不再打 EDGAR;D-002 單一正本與「等價重用」(2026-08-28 no duplicated copy)由價格快照延伸至文本原料
- 類型：決策
- 狀態：有效
- 日期：2026-09-02

- 出處：用戶 2026-09-02 原話:「Make sure we keep only single copy. Still the golden principle is governance on data」(針對 KARST-152 與 KARST-153 兩隊同時向 EDGAR 抓同一批年報)。主 agent 依 D-072 定具體規則。

- 背景：實況:KARST-152 只存 Item 1 切節(out/texts,918KB),KARST-153 正在抓 574 家 2008–2026 約一萬份 10-K,原本也只存 MD&A 與 Item 1A 切節——即倉內零份全文、兩份不同切節、下一條文本假設又要重抓一萬份。用戶那句話點中的問題不是「兩份太多」,是「沒有一份正本、每隊各抓各存」。主 agent 立場(D-110):①同意用戶,治理先於速度;不同意的地方只有一處——原始 HTML 不存,存 clean 後全文純文本:HTML 一萬份約 10–30GB,純文本 gz 約十分之一,而所有文本假設(相似度、敘事分層、轉折)都只用純文本;真要 HTML 可按 accession 從 EDGAR 重取,EDGAR 才是正本。②153 抓取途中改規則的代價是補抓已抓的約 700 份,可接受。③152 不重抓:153 的抓取範圍是 152 三個年份的超集,152 只補一句聲明。

- 決策：
  1. EDGAR 為正本;倉內年報/申報全文唯一快取住 C:\projects\Karst\data\sec\10k_text\<TICKER>_<accession>.txt.gz(clean 後純文本,gitignore 已覆蓋 data/),同目錄 manifest.jsonl 每份一行:ticker、cik、accession、form、filingDate、reportDate、url、chars、sha256、fetchedAt、fetchedBy
  2. 任何票抓 EDGAR 全文之前先查 manifest,已有就讀快取;實驗票目錄只存衍生物(切節、分層、面板)並記 accession,不存第二份全文;company_tickers 一類查表同樣只用 data/sec/ 那一份
  3. KARST-153 即改為同時寫入快取並補抓已抓的那批;KARST-152 不重抓,報告聲明文本直接取自 EDGAR、日後重跑改讀快取;派工模板數據段加一句「原料只入 data/sec 唯一快取,票內只存衍生物」
  4. D-002 單一正本與「等價重用」由價格快照延伸至文本原料;日後 8-K、Form 4、逐字稿等文本原料照同一形(data/sec/<form>_text/ + manifest)

- **用戶原話（原文照錄）**

  > Make sure we keep only single copy. Still the golden principle is governance on data

- 影響：第二波所有文本類假設(敘事轉折、8-K、產能敘事)零重抓;153 抓取多寫一份全文與補抓約 700 份,估計多一小時;152 不受影響。

## D-135 第二波數據源偵察定案:股數收縮即開(KARST-156,面板 diluted_shares 加封面頁實際股數已在倉內,零下載);短倉比率押後(交易所上市股票免費歷史只從 2021 年 6 月起,2009–2021 找不到免費來源,樣本腰斬,原 FINRA 端點已失效);產能週期(層級)押後至專項查證(只有 EIA 能源確認免費,半導體/鐵路/鑽機/卡車四項未能查證);A-029 便宜修法改為「申報檔頭 SIC」——現成端點只帶當前 SIC,知情時點 SIC 藏在每份申報原始檔頭,搭在 KARST-153 已抓的申報流程上邊際成本近零;敘事轉折走 EDGAR 全文搜尋(免費、無條款風險),逐字稿免費批量來源找不到,GDELT 只作輔助,待 KARST-152 分層結果再開
- 類型：決策
- 狀態：有效
- 日期：2026-09-02

- 出處：唯讀偵察隊交付(scratchpad 報告已複製為 research/2026-09-02-第二波數據源偵察.md;WebSearch 額度耗盡後部分改直接請求驗證,查不到的逐項標「未找到」)。主 agent 依 D-072 定案。

- 背景：主 agent 立場(D-110):①股數收縮是全名單最便宜的一條(一兩小時、零下載、頂刊有據),它答的是「面板還有沒有第五條有用的欄」;但要先剔拆股——KARST-148 的教訓是股數變化率會被拆股吃掉,這一條寫成死線。②短倉比率我原本看好(樣本外 R² 13% 是名單裡最硬的文獻),數據深度不夠就不硬做:五年樣本量不出橫截面,押後而不是判死,日後若找到付費或另一免費歷史再開。③A-029 修法不叫 153 中途再改第三次;等 153 收工後由後續票讀 manifest 的申報編號補抓檔頭,約一萬個請求二十分鐘。④敘事轉折依賴 A-037,等 152。

- 決策：
  1. 開 KARST-156 股數收縮存在性測試(第二波第一張);拆股剔除為死線;判準跑數前凍結、四基準、不產生及格
  2. 短倉比率(M2/S5)押後,理由:交易所上市股票免費歷史僅 2021 年 6 月起;寫入長名單狀態欄,不判死
  3. 產能週期(層級)押後至專項查證票;A-029 修法定為「申報檔頭 SIC」,待 KARST-153 收工後以其 manifest 補抓檔頭,另開小票
  4. 敘事轉折(層級)走 EDGAR 全文搜尋,待 KARST-152 回報 A-037 後開票;逐字稿路線放棄

- **用戶原話（原文照錄）**

  > (用戶未裁;屬 D-072 授權內定案)

- 影響：第二波第一張即開;三條押後各有明確重開條件;實測隊由四隊增至五隊平行。

## D-136 KARST-152 收案:機器讀年報自動分故事(TF-IDF 加平均連結聚類)按凍結判準決定性輸給 GICS 子行業——同層不同行業殘餘相關 0.02–0.04 對同行業不同層 0.11–0.18,九格同方向、置信區間不含零;A-037 推翻,但推翻範圍只到這一版做法。兩個但書比結論值錢:①3–25 家的細層層內同步 0.14–0.24,三個切片全高過行業基準,而且是人認得出的真故事(2019 郵輪+賭場酒店+租車+網上訂房 0.434;2023 平台化旅遊 0.206);輸在半數以上公司被掃進大雜燴層。②舊倉人手鏈位表方向在用戶那一邊:同鏈位 0.168 對同子行業 0.083(兩倍),等效獨立層數 3.08 對板塊 1.79,是唯一明顯超出板塊層的解析度;但 98 家只有 63 家在標普宇宙有日線、配對 30 對,置信區間跨零證不到。卡死點是宇宙:量子、鈾、加密礦、GLP-1 等最純主題股不在標普成份內。A-038 立(人手/語意分層的解析度,未證);開 KARST-157 第二版:先擴宇宙,再換分層方法
- 類型：決策
- 狀態：有效
- 日期：2026-09-02

- 出處：KARST-152 交付(票已關,驗收剔齊,只讀;報告 research/2026-09-02-敘事鏈層存在性.md;判準凍結 0aa236d,收檔 abcd81d;生產庫雜湊 b168e9f45b578cf9 不變;文本直接取自 EDGAR、只留切節無全文副本,合 D-134)。主 agent 依 D-072 收案。

- 背景：主 agent 立場(D-110):①這不是「敘事分層無用」,是「用數字典型辦法分故事分不出」——我同意 152 隊的判斷,而且要向用戶講清楚:他那張人手表是全票唯一明顯跑贏板塊層的分法,證不到只因為樣本被削了一半。②我押的是宇宙問題先於方法問題(把握中高):對象不在樣本裡,改幾多次演算法都無從檢驗;所以 157 先補齊 98 家日線再談分層。③要誠實的一點:人手表是用戶事後編的,曾見過價格,證得到也只證「解析度存在」不證「事前可得」(A-032 風險);事前可得那一半要靠語意模型在定格文本上重現同樣的分組——157 三臂並列就是為了把這兩件事分開量。④若 157 仍量不出,價值鏈層的角色降為「人手主題名單,用作注碼集中的候選池」,不作機器訊號層;這一步先講明,免得日後又是一條「量不出」拖着走。

- 決策：
  1. KARST-152 結論收貨;A-037 推翻(範圍限 TF-IDF 機器分層);A-038 立為價值鏈層的關鍵假設
  2. 開 KARST-157 敘事鏈層存在性第二版:先擴宇宙至標普以外(人手表 98 家補齊日線、細層成員、主題 ETF 成份只作宇宙來源),再以人手表/強制細層機器分層/語意模型分層三臂各自量,配對數門檻 100;判準跑數前凍結、不產生及格
  3. 若 157 仍量不出,價值鏈層降為人手主題候選池(注碼集中用),不作機器訊號層;此後不再開第三版存在性測試
  4. 五策略討論的價值鏈一節以 157 結果為準;157 未回前,鏈上策略只列為候選不排名

- **用戶原話（原文照錄）**

  > (用戶未裁;屬 D-072 授權內收案。人手表方向引用戶 D-130 原話立場:「the grouping should be sticked with the narrative」)

- 影響：價值鏈層由「機器自動分」改為「人手/語意分層、擴宇宙驗證」;敘事轉折等鏈上假設押後至 157;A-037 推翻不影響第一波三票(153/154/155 均不依賴分層)。

## D-137 KARST-154 收案:非價格宏觀開關(六變量多數投票,1990–2026)按字面過了 D-049 死線——窗內只有 2001 與 2008 兩次跌穿三成半,兩次都提前 6.7/10.2 個月減至 0×——但 2020 與 2022 兩次熊市完全睡過(見底後才轉守,2020 空倉四個月期間市場升 20.8%),只因為兩次剛好停在 −33.7% 與 −24.5% 死線才沒咬到。合成規則 0×/1×/2× 年化 13.81% 對買入持有 10.83%,+2.98pp 幾乎全是槓桿在贏(純開關只 +0.55pp),最大跌幅反而深 3.6pp;運氣帶 96 百分位但全靠 2008 一年 +38.2pp,2010 後每年輸 2.48pp;純開關夏普 0.61 → 最佳槓桿年化上限 21.4%,距 30% 差 8.6pp。不升格建置;唯一線索 A-039:2019 曲線倒掛那條腿 2020-01 已響,被多數投票否決——開關族病灶在合成方式不在變量
- 類型：決策
- 狀態：有效
- 日期：2026-09-02

- 出處：KARST-154 交付(票已關,四條驗收剔齊,只讀;報告 research/2026-09-02-宏觀狀態開關.md;判準凍結 8a4f064、交付 0773735、關檔 08e5a34;生產庫雜湊 b168e9f45b578cf9 不變;commit 衛生逐次核過)。主 agent 依 D-072 收案。

- 背景：主 agent 立場(D-110):①同意不升格,把握中高:有效樣本是兩次事件不是 36.6 年;它認得慢性信貸/就業週期熊市,認不得速度型熊市,而近二十年熊市愈來愈偏速度型;那 2.98pp 是槓桿的錢,誰都加得到。②這一票對我自己的一個更正:我在 D-132 把非價格宏觀開關列為「30% 唯一乘數級入口」,現在量到純開關夏普 0.61、上限 21.4%,這個入口在非價格宏觀變量這條路上關了;乘數要另找(市況注碼若要成立,只剩「或門」線索與價格類波動目標兩條,後者已在 D-075/079/083 族內測過)。③D-049 死線本身要收緊:「−35% 前減注」在這個窗只咬到兩次事件,讓一條睡過一半熊市的規則按字面過關。日後開關類測試加一條判死:窗內跌逾兩成的事件,規則錯過(見底後才轉守)達一半或以上,不論年化一律不入候選。④A-039 或門版本:值得一張便宜票,但要守 D-083 全新樣本外對象(SPY 已用掉),而且或門必然大增假警報,先量假警報代價再談;不搶在五策略討論之前開。

- 決策：
  1. KARST-154 結論收貨;非價格宏觀開關不升格建置;D-132 所稱「30% 唯一乘數級入口」更正為「此路已測、上限 21.4%」
  2. 開關類測試判死加一條(補 D-049):窗內跌逾兩成的事件,規則錯過(見底後才轉守)達一半或以上,不論年化不入候選;日後開關票的判準書必含「錯過熊市數/總熊市數」為首行
  3. A-039(或門合成)列入候選池,押後至五策略討論後決定開不開;若開,守 D-083 全新樣本外對象並先報假警報代價
  4. 五策略討論中,市況層的角色改為「注碼與風控的乘數,現時無非價格開關可用」,不把 13.81% 列為策略成績

- **用戶原話（原文照錄）**

  > (用戶未裁;屬 D-072 授權內收案)

- 影響：30% 的乘數入口由「非價格宏觀開關」改為「未找到」;第一波餘下 153/155 與第二波 156/157 不受影響;開關族判死條件收緊,適用於日後所有市況層票。

## D-138 KARST-155 收案:帳目靜默修訂不存在(擦邊)——±2% 門檻靜默向下修訂 4,314 宗(365 家、850 個板塊×月聚類),6 個月同板塊同月配對差 −0.48%(年化 −0.95pp)、聚類 t=−0.66,兩段皆負皆不顯著;可交易組合(多無修訂/空向下修訂)年化 +0.20%,對運氣帶排第 27 百分位;三條反證互相印證(持有愈久差距愈淡、門檻收緊反而更弱、向上修訂無反向效果);A-040 推翻長名單 S2。副產品更有用:向下修訂六成是營業額,而那一格完全平——因為最大一批是分拆出售後把賣走的業務由比較欄剔走(例:Agilent 2015 把 2013 財年營業額由 67.8 億改 38.9 億,因 Keysight 已分拆),不是帳目轉差;面板 _was_restated/_restated 兩欄不可當帳目質素代理
- 類型：決策
- 狀態：有效
- 日期：2026-09-02

- 出處：KARST-155 交付(票已關,四條驗收剔齊,只讀;報告 research/2026-09-02-帳目靜默修訂.md;判準凍結 f5e4334、結果 6d0e24a、收尾 631fd0f;生產庫雜湊 b168e9f45b578cf9 不變;CONTEXT.md 新增「靜默修訂」;commit 衛生逐次核過)。主 agent 依 D-072 收案。

- 背景：主 agent 立場(D-110):①收貨,把握高:事件數夠(4,314)、判準事前寫死、三條反證同方向,這不是量不出,是這個訊號在標普大型股上沒有東西。②我原本押這條「無人做過所以可能有」,錯在把「無人做過」當成「有優勢」的證據;真正原因是修訂的主體是重分類不是造假,雜訊淹沒訊號。③副產品要入帳:面板的修訂旗標不能當質素代理——KARST-148 四件套若有任何一格用過修訂旗標,要回頭核;日後任何用修訂欄的假設先把分拆/出售重列剔走。④文本線(153)與帳目線(155)是兩條不同的線,155 死不影響 153。

- 決策：
  1. KARST-155 結論收貨;帳目靜默修訂線收線,不開第二版;A-040 推翻 S2
  2. 面板 _was_restated/_restated 兩欄定為「重列旗標」不是「質素旗標」;日後任何用到它的假設須先剔除分拆/出售引起的比較欄重列;核 KARST-148 四件套是否用過修訂旗標,若有,在五策略討論附註
  3. 五策略遴選池剔除帳目靜默修訂

- **用戶原話（原文照錄）**

  > (用戶未裁;屬 D-072 授權內收案)

- 影響：第一波三票已回兩票(154 不升格、155 不存在),餘 153;第二波 156/157 在跑;遴選池由 26+5 減一。

## D-139 KARST-156 收案:股數收縮量不出(兩版訊號同判,差在門檻邊上)——A 版攤薄股數排名相關度中位 0.0141(門檻 0.015)、t 2.43(門檻 2.5);B 版封面頁股數 0.0169、t 2.18;控制規模與盈利能力後保留 65–78%,不是舊因子化身。只做多 D1(收縮最多十分位)年化 16.48%:對 SPY +2.36pp、對 XLK −3.68pp、對同池等權 +2.52pp,收足 15bp 仍排運氣帶 98.5 百分位;長短倉只 0.68%——做空發股多那邊完全收不到錢,優勢全在買入那邊;兩段 D1 絕對回報不變(16.4→16.5%),相對 XLK 由 +2.5pp 變 −8.3pp 是科技股太好不是訊號變差。順手推翻 A-041:面板 diluted_shares 約 1,100 格單位刻度錯三至六個量級(MCD 以百萬、COP/GRMN 以千、FTI 為 1.0),凡市值、每股數字、股數變化率都受影響,KARST-148 修的是拆股基準層,這層沒碰到。另:多隊共用 git index 撞了兩次(判準檔被別隊掃走、私有 index 令已入庫檔記成 deleted)
- 類型：決策
- 狀態：有效
- 日期：2026-09-02

- 出處：KARST-156 交付(票已關,四條驗收剔齊,只讀;報告 research/2026-09-02-股數收縮.md;凍結 39aba66、訂正 dbefc41(21:06:16,早於首個回報數字 21:11:13,原文未改以「訂正一」整節附加)、交付 6c67c36;生產庫雜湊 b168e9f45b578cf9 不變;兩處偏離票面已在首段攤開:拆股核對改用倉內拆股事件表)。主 agent 依 D-072 收案。

- 背景：主 agent 立場(D-110):①判詞收貨,但我對這條的看法比判詞正面:它是本輪第一條「只做多版排運氣帶 98.5 百分位、控制後留七成」的訊號,量不出是差 0.001 與 0.07 個 t;它跟 XLK 輸 3.7pp 是因為它是全市場橫截面訊號、XLK 是科技板塊——尺不對,五策略討論要用同池等權那把尺(+2.5pp)講。②它單獨不是 30% 策略(年化 16.5%),它的角色是「個股層的過濾器候選」:在鏈層/主題候選池內揀收縮者,而不是全市場排名。③A-041 是本輪最重要的數據發現:面板股數刻度錯會令 KARST-148「行內價值」那件的市值錯三至六個量級——148 的「無一件有效」結論之中,價值一件要在修好之後重跑一次才算數;開 KARST-158 修補,面板出新版本不改正本原檔。④git 共用 index 撞兩次是我的派工模板漏洞:「只 add 自己的檔」擋不住別隊已 stage 的內容被自己 commit 帶走,也擋不住私有 index 的副作用;規則改為 `git commit --only -- <自己的檔>`,禁用私有 index,寫入模板與記憶。

- 決策：
  1. KARST-156 結論收貨(量不出);股數收縮列入五策略候選池,角色為個股層過濾器(只做多版),尺用同池等權;不單獨升格
  2. A-041 收錄;開 KARST-158 面板股數刻度修補:diluted_shares 與封面頁股數逐格刻度校正(對照封面頁股數與市值合理範圍),面板出新版本(v2)保留 v1 正本與變更紀錄;修好後重跑 KARST-148 價值一件(行內價值)作核對,結果附註於 148 票留言,不重開 148
  3. 多隊平行 commit 規則改為:`git add` 只加自己的檔後,`git commit --only -- <自己的檔路徑>`;禁用 GIT_INDEX_FILE 私有 index;若 index 有別隊 stage 的檔,不動它;寫入派工模板與記憶
  4. 五策略討論中股數收縮的成績以 D1 只做多對同池等權 +2.5pp、對 SPY +2.4pp 報,並附「對 XLK −3.7pp 是尺不同」一句

- **用戶原話（原文照錄）**

  > (用戶未裁;屬 D-072 授權內收案)

- 影響：候選池加一條有量的個股層過濾器;面板 v2 修補影響 148 價值一件的結論可信度(待重跑);派工模板 commit 段改寫;第一波餘 153、第二波餘 157。

## D-140 KARST-157 收案:敘事鏈層第二版量不出——宇宙 574→728 家(人手表可入數 63→102 家,量子/鈾/加密礦/GLP-1 全部入數,價格零缺失),人手表同層不同行業殘餘相關 0.175/0.232 對同行業不同層 0.061/0.123(2023/2025 切片),等效獨立層數 3.77 對板塊 1.96、4.98 對 3.03,兩把 D-131 尺都過,敗在配對只有 61/62 對(門檻 100)、置信區間跨零;機器 v2 與語意分層六格全跨零,由上一版「決定性輸」退回「平手」,即上一版的負號相當部分是方法造成。卡死點的算式:31 條鏈位中位每條 3 家,要每條約 5 家(約 167 家成員)才過 100 對——下一步不是換演算法,是擴人手表。對假設不利的新證據:機器分層愈似 GICS 愈贏(互信息 0.61–0.65),人手表是唯一例外。宇宙是卡死點的直接證據:機器與語意同時找到 CIFR/CLSK/MARA/RIOT/WULF 加密礦層 0.698,人手表 quantum 層 0.762,上一版一家都不在宇宙內。A-038 維持 unverified 附查證紀錄
- 類型：決策
- 狀態：有效
- 日期：2026-09-02

- 出處：KARST-157 交付(票已關;報告 research/2026-09-02-敘事鏈層存在性v2.md;判準凍結 1c4a7b5、收檔 91a449e、關檔 6b06857;年報全文 202 份只入 data/sec/10k_text 逐行 append manifest;生產庫雜湊 b168e9f45b578cf9 不變)。票上兩格 raised 由主 agent 裁(見決定)。

- 背景：主 agent 立場(D-110):①兩版讀齊,我對用戶命題的看法由「懷疑」轉為「方向對、未證」:人手表兩個切片、兩把尺都在用戶那一邊,置信區間下限離零只差 0.02–0.04,這不是雜訊形狀,是樣本形狀。②但 D-136 第三條已寫明「若 v2 仍量不出,不再開第三版存在性測試,價值鏈層降為人手主題候選池」,我守這條——不是因為它不值得證,是因為下一步(擴人手表到每條鏈約五家)是人手敘事工作,由誰編、如何防事後標籤(A-032),是用戶要裁的事,放到五策略討論當一個明確選項,不由 agent 自行再開一票拖着走。③機器/語意分層兩版都證明「數字典型辦法分故事分不出」,把握高;敘事分層要成立只能靠人(或受控的模型輔助)編表——這一點要原樣告訴用戶,因為它決定價值鏈層的成本結構。④兩格 raised:(a)154 家新增日線未經生產庫登記——我裁「憑證入 coverage_meta_v2.json 已合 D-134 實質(唯一副本),正式登記另開小票,在五策略討論後與其他數據治理小票一併開」;(b)A-038 狀態——「unverified 加查證紀錄」正是第三種狀態,不改冊的欄位設計。

- 決策：
  1. KARST-157 結論收貨(量不出);依 D-136 第三條,不開第三版存在性測試;價值鏈層現階段定為「人手主題候選池」,用作注碼集中的候選來源,不作機器訊號層
  2. 「擴人手表至每條鏈約五家(約 167 家成員)再量」列為五策略討論的明確選項,由用戶裁編表方式與防事後標籤方法;agent 不自行開票
  3. raised(a):154 家新增日線暫以 out/coverage_meta_v2.json 憑證為登記,正式入生產庫登記另開小票(五策略討論後);raised(b):A-038 維持 unverified 加查證紀錄即為第三種狀態,不改假設冊欄位
  4. 「分法愈似 GICS 愈贏、人手表是唯一例外」與「加密礦層 0.698、量子層 0.762」兩項寫入五策略討論的價值鏈一節作證據

- **用戶原話（原文照錄）**

  > (用戶未裁;屬 D-072 授權內收案。用戶 D-130 原話立場「the grouping should be sticked with the narrative」在兩版實測中方向一致但未證)

- 影響：價值鏈層由「待證的機器訊號層」改為「人手主題候選池」;A-038 保留;第二波餘 158(修補)與第一波餘 153;五策略討論原料齊備度:七票中六票已回。

## D-141 KARST-153 收案:年報文字改動不存在——574 家大型股、9,666 份 10-K(覆蓋 97.7%)、210 個月、每月中位 476 家,量得出;Q1(改動最小)−Q5(改動最大)月差餘弦 −0.041%(t −0.31)、Jaccard +0.013%(t +0.10),兩把尺方向相反、兩段方向皆不一致;只做多 Q1 對 SPY +3.9/+4.8pp 是同池等權本身贏 SPY 每月 0.41% 的功勞(與 KARST-145 同一件事),對同池等權 −0.95/−0.16pp、運氣帶 14.5/49.6 百分位。有資訊的一格:管理層討論一節單獨看方向與文獻相反(月 −0.21%,t≈−1.1,兩尺一致),風險因素一節方向對不顯著,兩節互相抵銷。證偽範圍:大型股、只數改動不讀內容、按年更新;不證偽文獻、不構成對「讀得懂內容」路線的反證。附帶:9,666 份全文入 data/sec/10k_text 唯一快取,共用 manifest 兩隊欄名不一致待統一
- 類型：決策
- 狀態：有效
- 日期：2026-09-02

- 出處：KARST-153 交付(票已關,四條驗收剔齊;報告 research/2026-09-02-年報文字改動.md;判準凍結 d4b8ad2、結論 aacb72e、關檔 ec73e05;生產庫雜湊 b168e9f45b578cf9 不變;commit 衛生逐次核過)。主 agent 依 D-072 收案。

- 背景：主 agent 立場(D-110):①收貨,把握高:兩把尺相反、兩段相反,加樣本不會令相反變同向,這條在大型股上收線。②對用戶「文本是優勢所在」命題的意義要講準:本輪兩條文本線(152/157 讀內容分故事、153 數改動)合起來說的是——「數字典型辦法處理文本」(數相似度、聚類)在大型股上都沒有東西;唯一方向對的是人手讀出來的故事分層。即文本優勢若存在,存在於「讀得懂」而不是「量得出」,成本結構是人手或受控模型細讀,不是批量統計。③這與 D-133 容量尺一致:機構做得到的批量文本統計早已被做掉,散戶剩下的是細讀。④manifest 欄名統一開小票(五策略討論後,與 157 的價格登記小票一併)。

- 決策：
  1. KARST-153 結論收貨(不存在);年報文字改動線收線,不擴不重開;五策略遴選池剔除
  2. 文本線總結寫入五策略討論:批量統計文本(相似度/聚類)在大型股上無優勢;文本優勢若存在只在細讀,成本結構為人手或受控模型;與容量尺一致
  3. data/sec/10k_text 共用 manifest 欄名統一(fetchedBy/by、path、primaryDoc)開小票,與 157 價格登記小票同批,五策略討論後開
  4. 第一波三票全部回齊(154 不升格、155 不存在、153 不存在);第二波 156 量不出、157 量不出;五策略討論即開

- **用戶原話（原文照錄）**

  > (用戶未裁;屬 D-072 授權內收案)

- 影響：遴選池文本類只餘「人手鏈層」一條;年報全文快取 9,666 份可供日後細讀類假設零重抓;五策略討論原料齊(158 修補結果只影響 148 附註)。

## D-142 KARST-158 收案:面板 diluted_shares 123,754 格中判錯 1,361 格——校正 1,008 格(只除以 10 的整數次方,且須封面頁股數獨立指向同一倍數才動手)、設缺值 353 格(判不出不猜);面板 v2 出檔(雜湊 ab02e335c3ebc169,v1 一個位元未改)。KARST-148 行內價值一件 v1→v2 重跑(判準一字不改,v1 重跑與原公布數字完全對得上):年化 10.42%→9.99%、對 SPY −4.06→−4.49pp、運氣帶第 7.95→第 2.70 百分位(跌穿 p5)——結論沒變而且變硬:錯格一直在幫這一件(市值被打細的 MCD/COP/GRMN 等必然排純利收益率榜首),1,779 個持股位有 140 個因修補換人。新發現:拆股事件表按代號索引而代號會被重用,CPWR/EP/PARA 的拆股因子被後來使用同一代號的公司污染(0.0087/0.021/0.005),屬拆股基準層,本票刻意未動
- 類型：決策
- 狀態：有效
- 日期：2026-09-02

- 出處：KARST-158 交付(票已關;報告 research/2026-09-02-面板股數刻度修補.md;正檔 d1682d9、收尾 15a4309,全部 --only;148 票已留言未重開;A-041 補註維持 overturned;生產庫雜湊 b168e9f45b578cf9 不變)。主 agent 依 D-072 收案。

- 背景：主 agent 立場(D-110):①收貨;修補隊自行加嚴裁決線(要封面頁股數獨立佐證)是對的——CPWR 一例證明單靠量級錨會把對的改壞,多 104 格缺值換零宗誤修,我接受這個交換。②148 的價值一件由「與隨機無別」變「輸給九成七隨機」,D-129 判詞不用改,但要在五策略討論稿把「四件套無一件有效」這句加一個註:價值一件本來還有錯格在幫它。③代號重用污染拆股表是第三個數據治理問題(連同 manifest 欄名、154 家價格登記),三件同批開小票,不在五策略討論前開。④下游所有用面板的票自此讀 v2。

- 決策：
  1. KARST-158 結論收貨;面板 v2(ab02e335c3ebc169)為現行版本,下游一律讀 v2,v1 只留追溯;D-129 判詞不改,五策略討論稿加註「價值一件修補後更差」
  2. 拆股事件表代號重用污染(CPWR/EP/PARA 等 7 格)列入數據治理小票批次:與 data/sec manifest 欄名統一、154 家新增日線正式登記同批開,五策略討論後
  3. 面板修補的裁決線(倍數須兩個獨立欄佐證、判不出設缺值)寫入 RULES.md v2 已成,日後任何面板刻度修補沿用

- **用戶原話（原文照錄）**

  > (用戶未裁;屬 D-072 授權內收案)

- 影響：八張存在性/修補票全部收齊;帳目面板 v2 成為現行;三件數據治理小票待開;五策略討論可以定稿。

## D-143 用戶三裁(2026-09-02 晚,五策略討論第一輪):①人手鏈位表擴至每鏈約五家——可行就做,agent 主編可用網上資料,事後眼光編表的偏差接受(「Approximate may twist the performance. But the overall trend should hold」);②個股層由主菜降為配菜——接受,但另開「十倍股」線:先盤點名單,並設過濾器避開 BYND 一類迷因股;③主目標 30% 或 15–22%——用戶記得舊倉樽頸「贏 60% 以上」,待舊倉檔案核實後再裁
- 類型：決策
- 狀態：有效
- 日期：2026-09-02

- 出處：用戶 2026-09-02 原話三段(見 quote)。主 agent 依 D-072 把①②落成票,③押後至舊倉核實。

- 背景：主 agent 立場(D-110):①用戶接受事後眼光的代價,我照做,但誠實聲明照寫、而且量法要分兩版(事後表證解析度、受控表證事前可得)——這不是不信用戶,是這兩件事答的問題不同,混在一起將來紙上交易會被反噬。②「十倍股」線是用戶對「個股層降為配菜」的補充:他要的不是個股層系統規則,是「哪些股票會十倍」的名單與特徵——這與 D-131 長賠率注形狀完全一致(一注要講得出四至五倍),所以我把它定為候選一的注碼來源盤點,不是重開個股層系統線。先盤點歷史十倍股的基礎率與 t0 特徵,再設迷因過濾器;股數收縮(D-139)天然是反迷因過濾器之一(BYND 一類靠增發續命)。③樽頸 60%+ 我不憑記憶接受:要看口徑、窗口、鏈表是否事後編、成本;核實前不裁主目標。

- 決策：
  1. 開 KARST-159 人手鏈位表擴編(agent 主編、網上資料可用、每家附 valid_from 與年報佐證、每鏈附故事一句;交用戶審);量法分兩版寫入其後的 v3 票
  2. 開 KARST-160 十倍股盤點:歷史十倍股名單(倉內 728 家 + 文獻/網上)、基礎率、t0 特徵、所屬鏈位,並設計迷因過濾器(BYND 一類),以歷史十倍股回測過濾器的誤殺率
  3. 敘事鏈層 v3(擴表後重量)待 159 交表後開,D-136「不開第三版」由用戶本裁決解除
  4. 主目標裁決押後至舊倉樽頸成績核實;核實結果原樣交用戶

- **用戶原話（原文照錄）**

  > ①「I think it is ok if doable. But I think you can web research to purpose. Actually I think you should have the memory to propose?」/「This is fine. Approximate may twist the performance. But the overall trend should hold」 ②「OK, or we can still on 10x stock track. Try to stock take a list first. We may need need to set some filter as some MEME stock should be avoided like BYND」 ③「I remember Bottleneck at the time of KarstETF is winning 60+%?」

- 影響：價值鏈層由「候選池」升回「待證訊號層」(用戶授權擴表);個股層新增十倍股線作長賠率注的注碼來源;主目標未裁。

## D-144 舊倉樽頸成績核實(D-143 ③):查不到「贏 60% 以上」;舊倉所有 60%+ 都是捕捉率(揀中目標比率),且捕捉率推到六至七成時全期回報跑輸 QQQ(R0–R3 四臂 −2.4 至 −28.3pp);現行三注生產配置全期 +422% 至 +519%(2021Q4–2026Q1,三個快照口徑不一),對 QQQ 約 +420pp——但鏈籃於 2026-07 回測窗後才編(倒填 valid_from)、引擎無交易成本、讀卷模型帶事後知識;定性為「最強苗頭、非已證成績」;主目標裁決不建基於舊倉數字,改建基於本倉重驗
- 類型：決策
- 狀態：有效
- 日期：2026-09-02

- 出處：唯讀偵察回報,主 agent 改寫落 research/2026-09-02-舊倉樽頸成績核實.md(每個數字附舊倉檔案出處)。

- 背景：主 agent 立場(D-110):①用戶的記憶最可能是把「捕捉率 60%」與「贏 QQQ」溝在一起,或把 +422% 四年半折算成年化 44–50%;我要原樣講,不修飾。②這不代表那條線不值錢——它是本倉手上形狀最對(三注集中、鏈位讀卷、供需缺口=長賠率注)的苗頭;正確做法是以考試協議重驗,補三件事:鏈籃按 valid_from 定格(159 在編)、交易成本、模型事後知識對照。③主目標:我建議 15–22% 作主線量度、30% 作長賠率副線目標,直到重驗給出有成本、無事後知識的數字;不建議因舊倉數字維持 30% 為主線。

- 決策：
  1. 舊倉「60%+」定性為捕捉率或事後折算,非已證回報;本倉任何文件引用舊倉成績須附本核實檔
  2. 「樽頸引擎重驗」列為候選二的正式票(待 KARST-159 交表後開):鏈籃定格、交易成本、模型事後知識對照三件為必備判準;不重驗不引用其回報
  3. 舊倉 docs/adr/0039 §三之二 的逐鏈故事定義與 chain_audit_proposal.md 舊草稿交 KARST-159 作來源
  4. 主目標裁決再交用戶(建議 15–22% 主線、30% 長賠率副線)

- **用戶原話（原文照錄）**

  > 用戶原話:「I remember Bottleneck at the time of KarstETF is winning 60+%?」

- 影響：候選二由「舊倉初步成功」改為「待重驗的最強苗頭」;159 多兩個來源;主目標待裁。

## D-145 KARST-160 收案:十倍股盤點——728 家 2009 起,五年窗 138/689 家(20.0%)、三年窗 101/699 家(14.5%)曾達十倍;按年基礎率:任揀入場月五年中位 4.00%、只准一月入場五年 1.79%,最保守一格(一月買揸足五年)十倍 1.12%、五倍 5.62%;倖存者可量:2026 補進的 154 家主題股五年十倍率 33.1% 對原 574 家 17.1%;基礎率隨市況跳(2009/2020/2023 起點最高,2010–14 近零)。t0 最分得開三項:起點市值(十倍股中位 25 億對 120 億美元)、起點不在標普 500 內、前 12 個月股數變化——十倍股在發股(+0.92%)非十倍股在回購(−0.77%)。迷因過濾器實務版 R2(無營業額而市值高)+R5(上市未滿兩年):誤殺 19.3%、捕捉 75.8%(十反例中八);嚴格版 R2+R4 誤殺 6.1%、捕捉 59.6%;GME/AMC 任何基本面規則攔不住。文獻基礎率因網搜額度耗盡做不齊,逐項標未找到。兩格 raised:①「股數收縮天然反迷因」推論須收窄(它同時誤殺 12.9% 真十倍,方向與十倍股畫像相反);②十倍股線要先改宇宙(細、不在指數內),倉內骨幹正是標普成分股
- 類型：決策
- 狀態：有效
- 日期：2026-09-02

- 出處：KARST-160 交付(票已關;報告 research/2026-09-02-十倍股盤點.md;收檔 dc62674、收尾 07c5841;生產庫雜湊 b168e9f45b578cf9 不變;唯一新外部來源 SEC 2021 GME 幕僚報告)。主 agent 依 D-072 收案並裁兩格 raised。

- 背景：主 agent 立場(D-110):①raised ①我認錯:D-143 我寫「股數收縮天然是反迷因過濾器之一」,數據說相反——十倍股起步時在發股,回購是成熟公司的行為;股數收縮留在 KARST-156 橫截面訊號位置(15–22% 主線的零件),不作長賠率注入場條件;五策略討論稿候選三的角色改寫。②raised ②同意:十倍股的畫像是「細、不在指數內、起步時發股、上市不久」,而本倉宇宙骨幹是標普成分股(154 家主題股是例外,而它們的五年十倍率 33% 正是證據);要認真做十倍股線,先要一個小型股/非指數宇宙(例如 Russell 2000 或全美上市 <50 億美元),這是基建分母重建,成本要交用戶裁。③迷因過濾器 R2+R5 可用,但要講清楚它攔不住 GME/AMC 那種純資金驅動的狂熱,那類只能靠注碼上限與止蝕。④基礎率是本輪最重要的數字之一:最保守 1.1%/年十倍、5.6%/年五倍;D-131 說五年 30% 要八注中 2.6 注十倍,即命中率要三成——對比 1–4% 基礎率,選股要把命中率提高十至三十倍,這就是候選一鏈層+樽頸要做到的事,量化了它的難度。⑤文獻補查開小票(六至八次搜尋)。

- 決策：
  1. KARST-160 結論收貨;D-143 ②「股數收縮天然反迷因」推論撤回,股數收縮定位為橫截面訊號零件,不作十倍股入場條件
  2. 迷因過濾器實務版 R2+R5 列為十倍股線的預設守則(誤殺 19%、捕捉 76%),並明記攔不住純資金狂熱(GME/AMC),該類靠注碼上限與止蝕
  3. 十倍股線的宇宙問題交用戶裁:是否建小型股/非指數宇宙(基建分母重建),裁前十倍股線只作盤點不作訊號
  4. 十倍股基礎率(保守 1.1%/年十倍、5.6%/年五倍)寫入五策略討論稿,作候選一「所需命中率 35–43% 對基礎率 1–4%」的難度標尺;文獻基礎率補查開小票

- **用戶原話（原文照錄）**

  > (用戶未裁;屬 D-072 授權內收案;宇宙裁決待用戶)

- 影響：候選一的難度有了數字(命中率要提高十至三十倍);候選三角色改寫;十倍股線待宇宙裁決;三件小票再加一件(文獻補查)。

## D-146 KARST-159 交審:人手鏈位表 v1——52 條鏈、309 行、298 家(v0 33 鏈 143 行原樣保留、機械比對零差異;v1 新增 166 行、19 條新鏈);每鏈 ≥5 家達成 48/52;valid_from 近似 50.8%(新增成員 95% 不精確);年報佐證 88.3%(36 家為 20-F/40-F 外國申報人)。三格 raised 待用戶:①四條鏈結構性補不到五家(memory 3、solar 4、metaverse_innov 2、cannabis 1),舊倉 ADR-0039 §4.8 已逐條寫過同一理由;②三條 v0 鏈成員不在同一位置(staples 品牌廠對零售商、web3_crypto 交易所/國庫/礦工、china 只共通政策風險),按 D-129 不合格,建議 v2 拆開;③本表放寬舊倉「代表性測試」(投注代表門檻)而改用「同鏈位」門檻,三家初級銅礦商因此回表。A-042 立(「事後編的表整體趨勢仍成立」為可證偽假設);CONTEXT.md 新增「鏈位名冊 vs 投注代表」;票因 raise 未答不能關(守閘正確)
- 類型：決策
- 狀態：有效
- 日期：2026-09-02

- 出處：KARST-159 交付(票開着等用戶 answer;正本 experiments/2026-09-02-chain-layers/chain_stories_v1.md 與 chain_membership_v1.csv;commit 67c4912、94693d0;生產庫雜湊 b168e9f45b578cf9 不變)。主 agent 依 D-072 收貨,三格由用戶裁。

- 背景：主 agent 立場(D-110):①四條細鏈「補不到就是結論」我同意:它們永遠量不出顯著,只能作候選池成員,不入任何統計判準;這一點寫死免得日後又一條「量不出」。②三條不合格鏈我建議拆:D-129 定義是同位置同故事同消息衝擊,staples 品牌廠與零售商對同一則消息方向可以相反,塞在一起會把真訊號攤平;但那是用戶的表,由他裁。③名冊與投注代表分開命名是對的——量解析度用名冊(愈齊愈好),落注揀代表(愈純愈好),兩個門檻混用正是舊倉與本倉互相看不懂對方數字的原因。④valid_from 一半是近似,這會令 v3 的定格切片有誤差;v3 判準要把「近似 valid_from 的成員只入 2023 以後切片」寫死。⑤A-042 立得好:它把用戶「overall trend should hold」變成可證偽的一條,v3 若證不到,推翻的是 A-042 不是 A-038。

- 決策：
  1. KARST-159 交付收貨,票留開待用戶 answer 三格 raised;用戶答後由主 agent 或後續票 answer 並關檔
  2. 四條結構性細鏈(memory/solar/metaverse_innov/cannabis)定為「候選池成員、不入統計判準」,v3 判準寫死
  3. 主 agent 建議:v2 拆 staples/web3_crypto/china 三條;名冊門檻(同鏈位)與投注代表門檻(純度)分開命名並各自成文;均交用戶裁
  4. 敘事鏈層 v3 票待用戶審表後開;判準必含:近似 valid_from 成員只入 2023 以後切片、兩版量法(事後表證解析度、受控表證事前可得)、配對門檻 100

- **用戶原話（原文照錄）**

  > (用戶未裁;三格 raised 原文見票)

- 影響：價值鏈層有了 298 家的名冊(舊 98 家的三倍),v3 可過 100 對門檻;三條鏈拆不拆、四條細鏈處置、名冊與代表分家三件待用戶;主目標與小型股宇宙兩件仍待裁。

## D-147 用戶三裁(2026-09-03):①純資金推動的狂熱股(GME/AMC 類)一律不做——不是靠注碼上限與止蝕去管,而是整條線排除在外;②小型股宇宙要建,但先開研究專案研究這個題目,研究完再裁建法;③鏈層純度是最高優先——同一層的公司必須共享同一敘事,加多少家不設上限;staples/web3_crypto/china 三條 v0 鏈按此拆開
- 類型：決策
- 狀態：有效
- 日期：2026-09-03

- 出處：用戶原話三句:「Not doing these.」(指 GME/AMC 類純資金狂熱股);「Yes, we need to. But I want to have a study project and research on this topic first」(指小型股宇宙);「Yes, I dont care how much you add, but the purity of the layer is the highest priority. The company in the same layer should share the same narrative」(指鏈表三條不合格鏈)。

- 背景：主 agent 立場(D-110):①同意排除。D-145 寫的是「該類靠注碼上限與止蝕」,用戶改為整條線不做;代價是十倍股名單裡 GME 一類會被剔走(五年窗 138 家之中 GME 99 倍在列),接受——那不是可複製的形。迷因過濾器 R2+R5 由「注碼守則」升為「入場硬排除」。②同意先研究:小型股宇宙的分母重建最大的坑不是抓價,是倖存者偏差(退市、除牌、殼股的歷史要齊)與代號重用污染(CPWR/EP 已中招);研究專案要先答「用什麼來源才有退市歷史」,答不到就建出來的基礎率全是假的。③純度優先我照辦,而且要收回我在 D-146 ③ 的立場:我當時支持把「只講自己那個礦」的初級銅礦商收回鏈表(名冊門檻放寬),按用戶「同一層必須共享同一敘事」的原則,它們不合格——敘事是那個礦,不是銅市。名冊門檻由「同鏈位」收緊為「同鏈位且同敘事」,舊倉的代表性測試回歸。讓步在此,理由是用戶定義優先於我的解析度考量。④D-146 ①(四條細鏈作候選池不入判準)用戶未反對,維持。

- 決策：
  1. 純資金推動狂熱股整條線不做:迷因過濾器 R2+R5 升為入場硬排除,不再以注碼上限與止蝕承接;十倍股基礎率日後分開報「排除後」一欄
  2. 小型股宇宙:先開研究專案票(宇宙定義選項、有退市歷史的數據來源、倖存者偏差與代號重用處置、工作量估算),研究交付後由用戶裁建法;裁前不建
  3. 鏈層純度為最高優先:同一層必須共享同一敘事,成員數不設上限;開鏈表 v2 票拆 staples/web3_crypto/china,並對全部 52 條鏈做一次敘事純度覆核;名冊門檻收緊為「同鏈位且同敘事」,D-146 ③ 主 agent 立場撤回
  4. KARST-159 raise 以此裁決作答並關檔;敘事鏈層 v3 量度改在 v2 表上做

- **用戶原話（原文照錄）**

  > 「Not doing these.」/「Yes, we need to. But I want to have a study project and research on this topic first」/「Yes, I dont care how much you add, but the purity of the layer is the highest priority. The company in the same layer should share the same narrative」

- 影響：十倍股線多一道硬排除;小型股宇宙由「待裁」轉「研究中」;鏈表進 v2(純度版),v3 量度順延到 v2 之後;主目標(15–22% 主線加 30% 副線或維持 30%)仍待裁。

## D-148 用戶裁決:回報目標數字不作把關——「target = 30% or target = 22% doesn't matter at all」;agent 的任務是持續探索並找出最好的策略;五策略討論稿第五節第 2 問撤回;日後每條策略一律報齊四個數(年化、最大跌幅、命中率、容量),不以目標數字判生死;預設風險假設:主線可承受最大跌幅 25%、長賠率副線 50%(agent 假設,用戶未裁)
- 類型：決策
- 狀態：有效
- 日期：2026-09-03

- 出處：用戶原話:「how does it matter on the target? At the end, the goal to you is to explore and explore the best strategy for us. target = 30% or target = 22% doesn't matter at all」(2026-09-03)。

- 背景：主 agent 立場(D-110):用戶對——現階段全部票是存在性測試,存不存在與目標無關;我問主目標其實是在問資源先投哪條線,而用戶已用 D-147 三裁答了(建小型股宇宙、純度優先、十倍股線繼續)。目標仍有一處作用:比較「低回報淺跌幅」與「高回報深跌幅」的策略要一把尺;改為報齊四個數交用戶揀,不由 agent 以目標代裁。D-131 的 30% 數學(夏普上限、長賠率命中率)保留為難度標尺,不作門檻。D-137 的開關死線(漏一半熊市不算候選)是機制有效性判準,與目標無關,維持。

- 決策：
  1. 回報目標數字不作任何票的判準或死線;D-131 的 30% 數學降為難度標尺
  2. 每條策略交付一律報齊:年化、最大跌幅、命中率(長賠率注)或月勝率(橫截面)、容量;由用戶按四個數揀
  3. 預設風險假設(A-043):主線最大跌幅 25%、長賠率副線 50%;用戶一句話可改
  4. 五策略討論稿第五節第 2 問標記撤回;主目標問題不再向用戶重問

- **用戶原話（原文照錄）**

  > 「how does it matter on the target? At the end, the goal to you is to explore and explore the best strategy for us. target = 30% or target = 22% doesn't matter at all」

- 影響：少一條待裁;判準設計改為四數並報;討論稿更新。

## D-149 用戶交來十條交易原則(2026-09-03,原文照錄於 research/2026-09-03-用戶十條交易原則與評估.md)作為策略評估的判準透鏡;由此改動:①策略四數改為複合年化、最大跌幅、命中率或月勝率、優勢來源,容量降為資料欄不作排序(第五、六條);②排序的尺是複合增長率,唯一硬線是用戶的停手線(跌到多少會停整個計劃),用戶未講前沿用 A-043(第十條);③主線與副線由二選一改為資金份額問題(第七條);④第八條「下行有限、上行極大」與十倍股畫像(起步時燒錢、營業額在跌)的矛盾開 KARST-166 存在性測試
- 類型：決策
- 狀態：有效
- 日期：2026-09-03

- 出處：用戶 2026-09-03 交來十條原則並問「What do you think」;原文全文在該研究檔第一節;改動由主 agent 依十條推出,用戶未逐條裁。

- 背景：主 agent 立場(D-110):十條之中同意九條;第十條同意方向不同意字面——最大化長期總盈利在數學上等於最大化複合增長率,而複合增長率自動懲罰深跌幅,過度下注令長期總盈利下降;所以尺是「複合增長率 + 停手線」,不是「不管跌幅」。第五、六條對本倉成立(散戶規模距容量樽頸遠),但十倍股線的真正樽頸是人手讀鏈的頻寬(一次三至五條鏈),現在就在。第八條是最有生產力的一條:它與 KARST-160 畫像表面矛盾,品質過濾器已證誤殺十倍股,資產負債表式安全邊際(公司死不了)是形狀不同的過濾器,值得量。

- 決策：
  1. 策略交付四數:複合年化、最大跌幅、命中率(長賠率注)或月勝率(橫截面)、優勢來源;容量降為資料欄
  2. 排序用複合增長率;硬線只有用戶停手線,待用戶一句話定;定前沿用 A-043(主線 25%、副線 50%,很可能太緊)
  3. 主線與副線同時跑,按資金份額分;份額由用戶按四數定
  4. 開 KARST-166(十倍股安全邊際存在性測試);已開 KARST-163/164/165 三張 D-134 治理票

- **用戶原話（原文照錄）**

  > 用戶原話見 research/2026-09-03-用戶十條交易原則與評估.md 第一節(十條全文);問句「What do you think」

- 影響：日後每張策略票的判準格式改;A-043 待用戶改數;十倍股線多一條待證的入場過濾器形狀。

## D-150 KARST-162 交審:小型股宇宙研究——宇宙選項 t0 覆蓋率(138 家十倍股中 117 家算得出市值):現役骨幹 6.5%、羅素 2000 近似(3–50 億)48.6–63.8%、全美小型股(<50 億)70.3–85.5%、自定義(2–100 億)61.6–76.8%;成交額門檻未能驗證(日線無成交量欄);117 家之中 26% 起飛時市值不足 3 億。有完整退市歷史且准個人回測的來源只有三個:Norgate(25,222 隻退市、回溯 1950、含羅素成分史、報價未公開)、Sharadar(明文近乎無倖存者偏差、回溯 1990 年代、全歷史 $499/年)、Polygon($2,388/年、退市股價格是否保留未確認);免費路結構上答不到基礎率(免費基本面最早只回溯 2011;倉內 718 家有 84 家有帳目無股價,81 家已除牌)。文獻基礎率:MicroCapClub 約 1% 五年十倍(博客級)與倉內 1.12% 對得上;Bessembinder 三份、Mauboussin 兩份(約一半上市公司 10 年內除牌);「Alta Fox 十倍股研究」不存在(門檻 4.5 倍、無分母)。順帶修正 KARST-160:十倍股起點市值中位由 25 億(34 家樣本)修正為 9.8 億美元(117 家),方向不變幅度加倍。建議:全美小型股 + Sharadar $499/年 + 先做 2–3 人日覆蓋率驗證再建(約 8.5 人日)。三格 raised 待用戶:選項、預算上限、先驗證還是直接建
- 類型：決策
- 狀態：有效
- 日期：2026-09-03

- 出處：KARST-162 交付(票開着等用戶 answer;報告 research/2026-09-03-小型股宇宙研究.md;實驗 experiments/2026-09-03-smallcap-universe-study/;commit 2a93617;A-044 立;CONTEXT.md 兩個新詞條;生產庫雜湊 b168e9f45b578cf9 不變;未寫入 data/、未建宇宙)。主 agent 依 D-072 收貨,三格由用戶裁。

- 背景：主 agent 立場(D-110):①同意建議路線(全美小型股 <50 億 + Sharadar + 先驗證),理由是它是唯一「明文無倖存者偏差、個人買得起、回溯夠遠」的組合;羅素 2000 的 3 億下限會漏掉四分之一十倍股,不合十倍股畫像。②研究隊指出票上沒寫明目的是「令三十趴走得通」還是「令十倍股線的數字不再是假的」,並押前者走不通;按 D-148 用戶已裁目標數字不作把關,本倉目的是後者——分母不含退市公司,十倍股線的每一個數都是倖存者數字,這是 D-134 數據治理的延伸,非做不可。③我在票上點名的 Alta Fox 研究不存在,是我憑記憶寫錯來源,認錯。④起點市值中位由 25 億修正為 9.8 億:十倍股比我們之前講的更細一倍,「換宇宙」的必要性更高;五策略討論稿同步修正。⑤免費基本面只回溯 2011:任何 2009–2010 起點的基礎率格,免費路填不到,買數據前要接受這一段留空或另補。

- 決策：
  1. KARST-162 交付收貨,票留開待用戶 answer 三格(選項、預算上限、先驗證還是直接建);主 agent 建議:全美小型股(<50 億)+ Sharadar 全歷史($499/年)+ 先做覆蓋率驗證(2–3 人日)再建
  2. 小型股宇宙的目的定為「令十倍股線的分母含退市公司、數字不再是倖存者數字」(D-134 延伸),不是「令三十趴走得通」(D-148 目標不作把關)
  3. KARST-160 起點市值中位修正為 9.8 億美元(117 家樣本);五策略討論稿候選一同步改
  4. 任何付費數據訂閱由用戶親自下單,agent 不註冊、不付款;用戶裁後開建置票

- **用戶原話（原文照錄）**

  > (用戶未裁;三格 raised 原文見票)

- 影響：十倍股線的分母重建有了路線與價錢;待用戶三裁;十倍股畫像「更細」。

## D-151 KARST-161 交審:人手鏈位表 v2 純度版——65 條鏈/347 行/343 家(v1 52/309/298 原樣不改);票面三條拆開(staples→品牌廠/零售商;web3_crypto→交易所/持幣國庫,礦工併入 crypto_mining;china→電商/內容/教育),覆核另拆六條(uranium_power、streaming、fintech、ev、casino_resorts、ag_fertilizer),另分出 ai_hpc_hosting、auto_aftermarket,新開 aero_aftermarket;出隊 23 行(最爭議:MSFT/ORCL 主業轉向 AI 資本開支歸 hyperscalers、BHP/RIO 跟鐵礦石不跟銅、PLTR 跟自己的故事、SPOT 拆後無同位置可比;HBM/ERO/TGB 按 D-147 ③ 出隊);名冊不足五家的鏈由 4 條升到 16 條;年報佐證 88.2%,新抓 25 份入單一快取;純度判斷全屬人手、無統計背書;valid_from 六成近似。三格 raised 待用戶:①copper 縮到三家、ag_fertilizer 拆成四家與三家——純度贏了可量度性,是否接受;②GS/MS(banks)、PWR(datacenter_power)位置不同但股價跟鏈敘事走,判留,是否改拆;③審表
- 類型：決策
- 狀態：有效
- 日期：2026-09-03

- 出處：KARST-161 交付(票開着等用戶 answer;正本 experiments/2026-09-02-chain-layers/chain_membership_v2.csv、chain_stories_v2.md、removed_v2.csv;commit 41797e1、38212f5、05c12ee;生產庫雜湊 b168e9f45b578cf9 不變)。主 agent 依 D-072 收貨;CONTEXT.md「鏈位名冊 vs 投注代表」一行由主 agent 按 D-147 ③ 收窄。

- 背景：主 agent 立場(D-110):①純度與可量度性相撞時純度贏,這是用戶 D-147 ③ 的直接後果,我照辦;但要講清楚代價:16 條鏈永遠量不出統計顯著,鏈層 v3 的可配對數要重算,若 100 對門檻過不到,v3 只能證解析度方向、證不到量級。②MSFT/ORCL 出隊我同意——2023 年後它們的股價由 AI 資本開支敘事主導,留在企業軟件鏈會攤平那條鏈的訊號;但規則沒有時間維度是真問題:2022 年前它們是軟件股。v3 若按切片日期量,要用 valid_from/valid_to 承載這種轉向,不是整家出隊;建議 v2.1 把「主業轉向」改記為換鏈日期而非出隊。③GS/MS 與 PWR 判留我同意:用戶的問法是「股價跟不跟鏈敘事走」,不是「業務位置一不一樣」;位置是手段,敘事是目的。④v1 交審那四條結構性細鏈的處置(候選池不入判準)延伸到現在的 16 條。

- 決策：
  1. KARST-161 交付收貨,票留開待用戶 answer 三格;用戶答後 answer 並關檔
  2. 名冊不足五家的 16 條鏈一律作候選池成員、不入統計判準(D-146 ② 延伸);敘事鏈層 v3 判準須先重算可配對數,不足 100 對則只證方向不證量級,並在誠實聲明寫明
  3. 主 agent 建議(交用戶裁):主業轉向(MSFT/ORCL 類)在 v2.1 改記為換鏈日期(valid_to 舊鏈、valid_from 新鏈)而非整家出隊,讓按切片日期的量度用得上 2022 年前的樣本
  4. CONTEXT.md「鏈位名冊 vs 投注代表」按 D-147 ③ 收窄為同鏈位且同敘事(主 agent 已改)

- **用戶原話（原文照錄）**

  > (用戶未裁;三格 raised 原文見票)

- 影響：鏈表進入 v2;v3 量度的樣本量要重算;三件待用戶裁;主業轉向的記法待裁。

## D-152 用戶兩裁(2026-09-03,選項介面):①小型股宇宙「先走免費路試建」——不訂閱付費數據,以免費來源(證監會申報人清單、CIK 對照、yfinance 日線、companyfacts)試建全美小型股宇宙,明知分母缺退市公司、基本面只回溯 2011,基礎率仍是倖存者數字,先建了再看;②鏈表純度版「照建議收貨」——純度贏可量度性(銅鏈三家、化肥四家與三家)、高盛/摩根士丹利/Quanta 判留、主業轉向(微軟/甲骨文類)改記為換鏈日期而非整家出隊、16 條細鏈只作候選池、下一輪量度在 v2 表上跑
- 類型：決策
- 狀態：有效
- 日期：2026-09-03

- 出處：用戶 2026-09-03 選項介面答覆:問題一選「先走免費路試建」;問題二選「照建議收貨」。

- 背景：主 agent 立場(D-110):①免費路我建議過不選,理由是分母缺退市公司;用戶選了,我照辦,但把代價寫死在票上:免費路建出來的十倍股基礎率一律標「倖存者口徑」,不得與文獻比較;它買到的是覆蓋率(6.5% → 七八成)與宇宙骨架(實體主鍵、價格庫、面板擴容),日後若轉付費來源,骨架可沿用,只換價格與名單來源。②免費路試建明顯跨多張卡(約八個工作日):按 Kira 第 7 條拆為四張票——宇宙名單與實體主鍵對照、日線 OHLCV 入單一價格庫、帳目面板擴容、對 138 家十倍股的覆蓋率驗證;第一張先開,其餘按第一張報回的規模再開。③三張治理票(D-153)撞到的代號重用問題,正好由這次重建一併解決:新宇宙由頭就用 entity_id 作主鍵。

- 決策：
  1. KARST-162 raise 以「免費路試建」作答並關檔;開免費路試建第一張票(宇宙名單與實體主鍵對照),後續三張按規模再開
  2. 免費路產出的所有基礎率標「倖存者口徑」,不與文獻或付費口徑比較;骨架設計要讓日後換付費來源時只換名單與價格,不換主鍵
  3. KARST-161 raise 以「照建議收貨」作答並關檔;開 v2.1 小票(主業轉向改記換鏈日期);v2.1 落地後開敘事鏈層 v3 量度
  4. 16 條細鏈作候選池不入統計判準(D-146 ② 延伸,用戶已裁)

- **用戶原話（原文照錄）**

  > 選項介面:「先走免費路試建」/「照建議收貨」

- 影響：十倍股線分母重建開工(免費路);鏈表定版 v2 → v2.1;v3 量度排在 v2.1 之後。

## D-153 KARST-163/164/165 三張 D-134 治理票收案:①年報快取 manifest 已統一欄位(202 行改寫,9,914 行全量解壓核 sha256 零錯),唯一發現是雙重股權代號(GOOGL/GOOG、UAA/UA)同一份申報存兩份共 21 行 1.9MB——裁:保留兩份不刪,manifest 主鍵定為 ticker+accession 而非 accession,README 註明;②154 家新增日線價格住在實驗目錄(收市價寬表 2.94MB),復權口徑與生產線完全一致(五家逐日最大差 0.0001%),但只有收市價、沒有開高低量,走不進現有凍結機制,且生產快照另有 8 家真重複、6 個價格檔 26.8MB 未登記——裁:不單獨登記,併入免費路小型股宇宙重建(新單一價格庫,OHLCV 齊全,實體主鍵);③代號重用確證 3 個(CPWR/EP/PARA,面板 427 格),面板按代號 join 令今日那家公司的帳目乘上前一家公司的價格,基本面本身接錯,不是只修 7 格拆股;生產線早有 entity_id 機制(freeze.py 的 TickerRecycled),實驗線繞過了它,A-011 早已記過同一件事——裁:實驗線一律改用 entity_id 作主鍵,代號降為帶時段別名;面板 v3 隨宇宙重建以實體 join 重出;6 個嫌疑代號(SUN/COV/MEE/RAI/RTN/WRK)在重建時人手核
- 類型：決策
- 狀態：有效
- 日期：2026-09-03

- 出處：KARST-163/164/165 交付(三票 raise 留開;commit 37ba4d9/a314f3f、bb0171c/8320b4d、932a033/d388c83;生產庫雜湊 b168e9f45b578cf9 不變;164 報告 experiments/2026-09-03-price-registry-study/REPORT.md;165 清單 experiments/2026-09-03-ticker-reuse/out/)。主 agent 依 D-072 在數據治理範圍內裁三格並關檔;三票都指向同一決定(實驗線改用 entity_id),一併裁。

- 背景：主 agent 立場(D-110):①三票是同一件事的三個面——一家公司兩個代號、一家公司兩份價格、一個代號兩家公司;根源是實驗線用代號做主鍵而生產線早已用實體。A-011 在 8 月 29 日已推翻過一次而善後只做了生產線,今日在實驗線再撞一次,這是治理漏洞不是新發現;我沒有為它再開假設,對。②刪雙重股權副本沒有必要:兩個代號各自指向同一份申報是事實,存兩份是冗餘不是錯誤,1.9MB 不值得引入刪檔風險;改主鍵定義即可。③154 家價格不單獨登記的理由:現有檔缺開高低量,登記要重抓;而免費路宇宙重建本來就要抓幾千家 OHLCV,154 家順帶重抓成本近零,單獨做反而多一套流程。④面板 427 格接錯公司這一項比拆股嚴重,KARST-160 前二十名有兩格(EP、CPWR)是污染,D-145 已註明;十倍股名單在宇宙重建後要重出。

- 決策：
  1. manifest 主鍵定為 ticker+accession;雙重股權 21 行保留不刪;README 註明;KARST-163 關檔
  2. 154 家價格與 6 個未登記價格檔不單獨登記,併入免費路小型股宇宙重建的單一價格庫(OHLCV、實體主鍵);KARST-164 關檔
  3. 實驗線一律改用 entity_id 作主鍵、代號為帶時段別名;面板 v3 隨宇宙重建以實體 join 重出;CPWR/EP/PARA 三代號的 7 條拆股修補與 427 面板格在重建時處理;6 個嫌疑代號人手核;KARST-165 關檔
  4. 宇宙重建票的判準必含:主鍵 entity_id、代號時段表、拆股表按實體、面板按實體 join

- **用戶原話（原文照錄）**

  > (用戶未裁;數據治理範圍內依 D-072 與 D-134 裁決)

- 影響：三票關檔;免費路宇宙重建票的骨架規格定了(實體主鍵、OHLCV、面板實體 join);十倍股名單日後重出。

## D-154 KARST-166 收案:十倍股安全邊際——資產負債表式安全邊際是方向相反的兩件事:「不欠債」(淨現金對市值)與十倍股同向(逐年加權 AUC 0.648,市值三組全部一致,不是規模效應),作門檻不誤殺(誤殺 59.6% 對剔走 82.6%,比值 0.72);「不燒錢」(現金跑道 ≥2 年)與十倍股反向(AUC 0.346),是真誤殺(誤殺 21.9% 對剔走 6.7%,比值 3.27),而它是唯一買得到「死不了」的一條;「有形資產厚」分不開(0.556)且通過者反而死得多。最像十倍股的起步狀態是「有淨現金而且正在燒它」(十倍率 11.0% 對淨負債不燒錢 0.7%;按公司數計差距收窄到 2.3 倍,由七家撐起,含 GME)。覆蓋只及四分之一十倍格,漏掉的正是新上市與外國申報那批;728 家全活到今日,退市一格未觸發,死亡率嚴重偏低。判詞:存在(不欠債同向)/存在(不燒錢反向)/量不出(有形資產)。一格 raised 待用戶:第八條原則的「Margin of Safety」指「不欠債、輸得起」還是「盈利穩定、不燒錢」
- 類型：決策
- 狀態：有效
- 日期：2026-09-03

- 出處：KARST-166 交付(票開着等用戶 answer;報告 research/2026-09-03-十倍股安全邊際.md;判準凍結 3612c9f、結果 760ab69、票務 3e554f2;零新抓 EDGAR,用 KARST-146 的 698 份 companyfacts 快取補三欄;生產庫雜湊 b168e9f45b578cf9 不變;CONTEXT.md 加「安全邊際」一條)。主 agent 依 D-072 收案。

- 背景：主 agent 立場(D-110):①這是本輪最有用的一個結果:它把「安全邊際」拆成兩個名,而兩個名對十倍股的作用相反。用戶第八條講的是下行有限;數據說資產負債表買到的是「有本錢賭」(上行),買不到「死不了」(下行)——唯一買到下行的門檻同時殺掉五分一真十倍。②所以我押:選股層只用「淨現金為正」這一條(不誤殺、而且偏幫),下行保護搬去注碼與離場層(每注上限、止蝕),不在選股層做。這與 D-149 第十條的討論一致:跌幅由組合層管,不由選股層管。③自扣分兩項我照收:燒錢那一格與 KARST-160「經營現金流為正」是同一件事;11.0% 由七家撐起,含 D-147 ① 明令不做的 GME,剔走後結論方向不變但強度要重報。④覆蓋四分之一與零退市是免費路宇宙重建要解決的同一件事;本票結論在新宇宙上要重量一次。

- 決策：
  1. KARST-166 交付收貨,票留開待用戶 answer「Margin of Safety 指哪一種」;主 agent 建議:不欠債(淨現金為正)入選股層,不燒錢不入;下行保護由注碼上限與止蝕承擔
  2. 「安全邊際」一詞在本倉分兩個名:資產負債表緩衝(淨現金)與燒錢紀律(現金跑道),不得混用(CONTEXT.md 已立)
  3. 十倍股線入場條件現有三條可證存在的方向:鏈敘事(待 v3)、細且不在指數、淨現金為正;品質與不燒錢兩類過濾器明文不用
  4. 本票結論在免費路宇宙重建後重量(覆蓋、退市)

- **用戶原話（原文照錄）**

  > (用戶未裁;raise 原文見票)

- 影響：十倍股線的選股層多一條不誤殺的過濾器;下行保護的位置定在組合層;待用戶答一格。

## D-155 用戶裁(2026-09-03,選項介面):第八條原則的「Margin of Safety」在十倍股線選股層取「不欠債、輸得起」——選股層只用淨現金為正一條;不燒錢(現金跑道)門檻不入選股層;下行保護由注碼上限與止蝕承擔;十倍股線入場條件定為三條方向:鏈敘事(待 v3)、細且不在指數、淨現金為正
- 類型：決策
- 狀態：有效
- 日期：2026-09-03

- 出處：用戶 2026-09-03 選項介面答「不欠債、輸得起」(KARST-166 raise 的三選項之一,主 agent 建議項)。

- 背景：主 agent 立場(D-110):與我建議一致。後果要寫清楚:①這條線由此正式接受「途中跌一半」的形——D-149 第十條與 A-043 副線 50% 跌幅假設一致;②淨現金門檻在免費路宇宙建好後要重量(現在只覆蓋四分之一十倍股格,而且零退市);③GME 類純資金狂熱股按 D-147 ① 仍是硬排除,淨現金為正救不回它。

- 決策：
  1. 十倍股線選股層過濾器:淨現金為正(資產負債表緩衝);現金跑道、品質、回購三類明文不用
  2. 下行保護在組合層:每注上限與止蝕(數值待策略建置票對齊,D-038 參數對齊節)
  3. KARST-166 raise 以此作答並關檔;結論在免費路宇宙建好後重量

- **用戶原話（原文照錄）**

  > 選項介面:「不欠債、輸得起」

- 影響：十倍股線三條入場方向定了兩條(細且不在指數、淨現金為正),第三條(鏈敘事)等 v3。

## D-156 KARST-168 收案:鏈表 v2.1——主業轉向改記換鏈日期只涉兩家四行(MSFT 2023-01-23 月準確,FY2023 年報明文 OpenAI 第三階段;ORCL 2023-06-01 近似,FY2024 年報首見 OCI 訓練生成式 AI 客戶),其餘規則 d 名下四行(BHP/RIO 全期鐵礦石無轉向日、COP 轉向在 2012 早於表起點、HOOD 屬去重)維持出隊;v2.1 65 鏈/349 行/343 家、出隊 21;零新抓年報;CONTEXT.md 新詞「換鏈日期」。編表人指出同類前視問題仍在:ai_hpc_hosting 四家(CORZ/IREN/WULF/CIFR)2024 年才由挖礦轉 AI 託管而 valid_from 仍是 2022 年初,HOOD 在 crypto_exchange 同樣——裁:開 v2.2 小票修這五行,然後在 v2.2 表上開敘事鏈層 v3 量度
- 類型：決策
- 狀態：有效
- 日期：2026-09-03

- 出處：KARST-168 交付(票已關;commit efc8335、a37426e;生產庫雜湊 b168e9f45b578cf9 不變)。主 agent 依 D-072 收案並開後續兩票。

- 背景：主 agent 立場(D-110):①ORCL 的轉向日由 2024 年才公開的年報倒推,編表人自己標明帶前視,對;v3 判準要把「近似 valid_from 只入 2023 年後切片」寫死,這類就自然落在規則內。②ai_hpc_hosting 四家的 valid_from 錯法比 MSFT/ORCL 嚴重:那條鏈本身就是 2024 年才存在的敘事,四家在 2022–2023 的切片按現表會被當成「AI 託管層」量同步度,量到的其實是加密礦層——這正是 A-042 要防的那種事後眼光滲漏,v3 前必須修。③v3 的兩版量法:事後表(v2.2)證解析度;受控表(只用切片日前資訊)證事前可得,兩個數相差不遠才算答到 A-042。

- 決策：
  1. KARST-168 結論收貨;v2.1 為現行表
  2. 開 v2.2 小票:ai_hpc_hosting 四家與 HOOD 按換鏈日期改記(舊鏈 valid_to、新鏈 valid_from、佐證),其餘不動
  3. 開敘事鏈層 v3 量度票(在 v2.2 表上):兩版量法(事後表證解析度、受控表證事前可得)、配對門檻 100、近似 valid_from 成員只入 2023 年後切片、16 條細鏈不入判準、判準先凍結、四數並報;A-042 由受控版答
  4. 兩票由同一隊接連做;v3 收貨後才開樽頸引擎重驗

- **用戶原話（原文照錄）**

  > (用戶未裁;屬 D-072 授權內收案)

- 影響：鏈表 v2.1 → v2.2;v3 量度開跑;A-042 有了查證路徑。

## D-157 KARST-167 收案:免費路宇宙第一張——實體表 5,257 家(納斯達克 3,100、紐交所 2,138、CBOE 19;含 1,233 家 ADR),現役 5,255、停止申報 2(來源只列今日仍掛牌者,缺退市正本);近似市值 <50 億美元 3,188 家(剔信託型 ETP 後 3,114);有股數 83.1%、有價 99.9%;代號時段表 5,952 段零重疊,CPWR/EP/PARA/SUN 各切兩段(EP/PARA 前手仍在申報,切斷點改用成分期離場日);138 家十倍股 135 家在名單內但屬同一倖存者池,不作覆蓋率;跑數後改過兩條規則(外國私人發行人類別為 other 非 operating,不改則 ADR 全剔;信託型 ETP SIC 6221 漏出剔除規則,只標旗建議 v1 剔);A-045 立(近似市值足以劃 50 億線);CONTEXT.md 新詞「停止申報日」;餘下三票估算:OHLCV 5,947 代號 45–90 分鐘 300–600MB(yfinance 要 40 個一批加退讓,否則成功率 32%)、companyfacts 補抓 4,649 家 7–16GB、覆蓋率驗證零新抓;順帶發現申報索引在五個實驗目錄各存一份副本(一個 334MB),D-134 在這一格從未落地
- 類型：決策
- 狀態：有效
- 日期：2026-09-03

- 出處：KARST-167 交付(票已關;commit e8343bb/974b4c3/c2b64f5;產物 data/universe/(entities、ticker_periods、universe_smallcap_v0、RULES.md);報告 research/2026-09-03-小型股宇宙v0盤點.md;生產庫雜湊 b168e9f45b578cf9 不變)。主 agent 依 D-072 收案並開後續票。

- 背景：主 agent 立場(D-110):①跑數後改規則兩項,編表人自己寫進 RULES 第八節,可接受——第一項是規則寫錯(把 ADR 全剔)不是調參;第二項只標旗不改,對。②5,257 家全是今日掛牌者:免費路的倖存者口徑比我預期更徹底(停止申報只有 2 家),這條線的所有基礎率日後一律標倖存者口徑,D-152 已寫死。③companyfacts 7–16GB 屬原料庫規模,按 D-134 單一副本收入 data/sec/companyfacts/ 並 gzip;外國申報人多數為空,面板要記「取不到」不記零。④申報索引五份副本是 D-134 明文違反,開清副本票:逐檔核 sha256 與正本相同才刪,不同者留並列出。⑤價格庫由頭用實體主鍵與代號時段表 join,順帶把 154 家與 6 個未登記檔收進來(D-153)。

- 決策：
  1. KARST-167 結論收貨;universe_smallcap_v0 為現行名單;v1 剔 SIC 6221 信託型 ETP 在價格票順帶出
  2. 開三張後續票:日線 OHLCV 單一價格庫(實體主鍵、40 個一批加退讓)、companyfacts 面板擴容(gzip 單一快取、外國申報人記取不到)、覆蓋率驗證(對 138 家十倍股 t0 市值);同一隊依序做
  3. 開申報索引副本清理票:實驗目錄內與正本 sha256 相同的副本刪除,不同者留並列出
  4. 免費路全部基礎率標倖存者口徑(D-152 重申)

- **用戶原話（原文照錄）**

  > (用戶未裁;屬 D-072 授權內收案)

- 影響：宇宙線由名單進入價格與面板;D-134 多一項落地。

## D-158 KARST-169 收案:鏈表 v2.2——四家 AI 託管礦企按「首次公開宣佈 AI/HPC 客戶合約當日」換鏈(規則跑前寫死:只講策略或買 GPU 不算):CORZ 2024-03-06、IREN 2024-02-08、WULF 2024-12-23、CIFR 2025-09-25,各附 8-K/6-K/10-K 原文與 accession,並明文否決三個更早的誘人日期;HOOD 入位日 2022-01-01 不變,但查出 v2/v2.1 理由書講錯(原寫 2024 年起加密佔交易收入主體,10-K 實數加密佔總淨收入 21–23% 而期權每年更大),已改寫並保留原句;三條鏈七行 purity_note 重寫(APLD 標明未修);對帳 353 行/65 鏈/343 家,v2.1 一組重複鍵(WDC 在 memory 兩行,v2 前已存在)改用位序對帳並記 README
- 類型：決策
- 狀態：有效
- 日期：2026-09-03

- 出處：KARST-169 交付(票已關;commit ef4f012、10c0828;生產庫雜湊 b168e9f45b578cf9 不變)。主 agent 依 D-072 收案。

- 背景：主 agent 立場(D-110):①「客戶合約公告日」比「策略宣佈日」嚴,對——市場把一家礦企當 AI 託管股,是在它拿到合約那天,不是它講想做那天;這條規則日後所有換鏈日期沿用。②CIFR 的換鏈日 2025-09-25 落在 v3 兩個切片之後,即 v3 的 ai_hpc_hosting 鏈實際只有兩三家,這條鏈在 v3 判準內近乎缺席,是 v3 誠實聲明應寫的一項。③HOOD 理由書寫錯是編表人自己查出來的,價值在於證明 v2 的鏈故事有未經數字核對的段落;v2.2 之後任何鏈故事引用收入佔比一律附 10-K 數字。④WDC 重複鍵留待下一版表修,不在本票動。

- 決策：
  1. KARST-169 結論收貨;v2.2 為現行鏈位表
  2. 換鏈日期規則定為「首次公開宣佈該鏈客戶合約當日」,寫入 CONTEXT.md 換鏈日期條
  3. 鏈故事引用收入佔比必附 10-K 數字;WDC 重複鍵留下一版修

- **用戶原話（原文照錄）**

  > (用戶未裁;屬 D-072 授權內收案)

- 影響：鏈表 v2.1 → v2.2;換鏈日期有了統一規則。

## D-159 KARST-170 收案(票留舉手待用戶裁):敘事鏈層 v3——甲版(事後表)兩個切片解析度倍數 2.82(2023-06-30)與 1.46(2025-06-30),等效獨立層數 3.70/5.60 對板塊 1.96/3.03,可配對 125/127 對達標,隨機重貼標籤 2,000 次實測值排第 100 百分位(不是運氣),但 cluster bootstrap 95% 置信區間仍含 0(2023 為 [−0.001, +0.231]),判「量不出」;乙版(只用切片前年報文本重建分組)保留率 −134%/−271%,四格全負且置信區間不含 0,判「不存在」;A-042 推翻(範圍:這張表的解析度事前用年報文本重建不出來,不是這張表量不到東西;A-038 仍未核);既知不足:343 家中 85 家無價無子行業(從未進 728 家宇宙,含 META、TTD、S、CORZ、APLD)、子行業用 yfinance industry 近似、入位日約六成近似、語意模型訓練語料可能含事後知識(偏向高估事前可得)、2025 切片只 142/209 家有事前文本;乙版與子行業的分組相似度 0.29–0.52 而人手表 0.79–0.80,即年報文本重建出來的是行業不是敘事;編表人舉手四選項,押「再試一次別的事前資訊源,一張票預算,不成收線」
- 類型：決策
- 狀態：有效
- 日期：2026-09-03

- 出處：KARST-170 交付(票未關,raised 待用戶裁;commit ef08ef0 判準凍結、efef572 結果、eddbd91 收尾;A-042 status 改 overturned 的改動被 974b4c3 帶走,票上已留言更正;生產庫雜湊 b168e9f45b578cf9 不變)。主 agent 依 D-072 收案,方向問題交用戶。

- 背景：主 agent 立場(D-110):①這是今日最重要的結果:路線圖上唯一形狀對 30% 的路(人手鏈層+集中長賠率注,D-142)其前提之一剛剛缺了一角——人手表的解析度用「當年公開的年報文字」重建不出來。②但我不同意就此收線,理由兩個:第一,甲版本身還未判死——85 家缺價格是抽樣缺口不是方法缺口,而 D-157 開的單一價格庫正好把它補上,零額外成本;補上後 2023 切片的置信區間差 0.0014 過線,很可能過。第二,乙版用的資訊源是年報 Item 1,那一節講「我做什麼生意」,重建出來自然是行業;鏈位講的是「市場把誰跟誰當一個故事」,天然住在共同分析員覆蓋、供應鏈客戶名單、新聞共現,這一步未試。③我也不同意無限期再試:甲版即使過線,量級是同步度 0.16 對 0.06,能否撐起倉位是另一回事;所以要有死線。④我押的次序:先靠價格庫補缺重跑甲版(免費);甲版置信區間過線才開一張乙版新資訊源票(一張票、判準照 v3、保留率仍 ≤0 就收線);甲版不過線則鏈層只作研究用途,轉其他候選形狀。這與編表人的甲選項相同,只多了「先補缺再花錢」一步。⑤停手線與此無關,仍欠用戶一個數。

- 決策：
  1. KARST-170 結論收貨;A-042 維持 overturned(範圍限年報文本路徑);KARST-170 留 raised 待用戶裁方向
  2. 主 agent 建議次序:單一價格庫落地後零成本重跑甲版補 85 家缺口 → 甲版置信區間過線才開一張乙版新資訊源票(一張票、死線、不成收線)→ 不過線則鏈層降為研究用途
  3. 樽頸引擎重驗(D-156 第四條)押後至方向裁定後

- **用戶原話（原文照錄）**

  > (用戶未裁;方向問題以選項介面交用戶)

- 影響：鏈層路線由「唯一形狀對的路」降為「待證的路」;是否再投一張票由用戶裁。

## D-160 KARST-171/172/173 收案:免費路宇宙四張齊——①單一價格庫 data/prices/daily/ 16 片 parquet、2,065 萬列、462MB,5,952 代號時段完成率 99.95%,adj_close 非不變量(除息後整條改寫,對生產快照比值 0.9885–0.9939),定性為原料倉不是快照;小型股名單 v1 3,117 家(剔 SIC 6221);②companyfacts 5,257 家零次 403、gzip 732MB(原始 10.4GB),面板 v3 220,132 列/102 欄,48 家逐格記取不到不填零,覆蓋率資產 99.5%/現金 96.6%/總債務僅 41.4%,四核心齊全 31.1%,對 v2 抽 30 家相同率 98.9%;一度誤丟 241 家 IFRS 非美元申報人,已改收任何 ISO 貨幣碼;③覆蓋率驗證:138 家十倍股算得出 t0 市值只餘 68 家(舊 117 家之中 31 家用了 t0 後才存在的股數,前視),起步市值中位新 14.49 億/舊 9.77 億,分別全來自誰算得出,真值多數仍在 9.8 億下;淨現金為正 N1 口徑十倍股 20.6% 對宇宙 22.3% 不存在、N2 口徑 42 家量不出,D-155 未推翻但要在面板 v3 重跑 KARST-166 格級 AUC 才裁;五年窗 >50% 回撤十倍股 7.0% 對宇宙 56.7% 存在但循環不可當訊號;宇宙覆蓋率 37.7%–88.4% 量不出;倖存者口徑基礎率(2010–2021)五年十倍率 3.69%、>50% 回撤率 50.2%,2009–2011 幾乎盲;129 家十倍股新價格庫重算全部仍 ≥10 倍;A-045 holds;三件善後未開票:封面股數 599 家無標籤、「今日仍然細」不是合格歷史宇宙、退市正本仍缺
- 類型：決策
- 狀態：有效
- 日期：2026-09-03

- 出處：KARST-171(commit 5b26af8/7eeeb39)、172(5359afe/0cb4fd9/ae0efe7)、173(ec4f9b8 判準/767e5f5/906c28f)交付,三票已關;生產庫雜湊 b168e9f45b578cf9 不變。主 agent 依 D-072 收案。

- 背景：主 agent 立場(D-110):①舊起步市值 9.8 億含前視,是今日發現的最大一個舊結論缺口——之前 D-150 修正過一次,現在要再退一步:這個數目前「量不出」,只知道區間在 7.5 億至 14.5 億之間。②淨現金篩選在新宇宙量不到關係,編表人拒絕推翻 D-155 因四樣同時變,做法對;開一張票在面板 v3 上分四步隔離主因。③總債務覆蓋率只有 41.4% 意味淨現金篩選的分母一半以上算不出,這本身就可能是 N2 口徑量不出的主因,票內要先答這個。④adj_close 非不變量:所有實測以 close 加自算調整因子為準,凍結時記調整因子版本,不直接用 adj_close。⑤三件善後留待用戶討論後開,先不開票。

- 決策：
  1. KARST-171/172/173 結論收貨;價格庫、面板 v3、小型股名單 v1 為現行資料層;實測用 close 加自算調整因子,不直接用 adj_close
  2. 起步市值中位改記「量不出,區間 7.5 億至 14.5 億美元」,D-150 的 9.8 億降為區間內一個點
  3. 開一張票在面板 v3 上重跑 KARST-166 格級 AUC,四步隔離(對照組、單位、量度、樣本)後才裁 D-155 去留
  4. 三件善後(封面股數、歷史宇宙、退市正本)留用戶討論後開

- **用戶原話（原文照錄）**

  > (用戶未裁;屬 D-072 授權內收案。用戶 2026-09-03 原話:「I think can resume the remaining task. But when they are done. Wait for me for further discussion」——依此只開已講明的三張,做完停下)

- 影響：免費路宇宙四張齊,資料層換代;十倍股起步剖面與淨現金篩選兩個舊結論降級待重量。

## D-161 KARST-174 收案:申報索引清理——票面「五個實驗目錄各存一份副本」前提更正:只有兩個是真副本(fundamentals-panel 110 檔、silent-revisions 1,655 檔),其餘三個目錄名叫 submissions 但存的是切出來的年報清單衍生物(1,298 檔),D-134 准許,一個未刪;正本維持 data/sec/submissions/(8,013 檔 643MB,唯一有逐份 manifest);刪除 514 檔 89.2MB 全部逐檔 sha256 與正本一對一相同;保留 1,254 檔 256MB:1,051 個歷史分頁檔(227MB,正本完全沒有這一類)、101 份較舊子集、99 份正本沒有的宇宙外公司;兩支腳本各改一行路徑;真正發現:證監會索引檔只載每家最近約 1,000 份申報,正本 8,012 份之中 2,066 份(25.8%)被截短,欠 2,736 個歷史分頁一個未存——任何用首次申報日當上市日代理的規則(十條原則「上市未滿兩年不碰」)在這 2,066 家會把老公司當新上市,KARST-167 首次申報年分佈表同樣受影響;A-046 立並推翻;編表人舉手問歷史分頁要否收編,押收編加補抓餘下 1,765 個分頁(約 4 分鐘)
- 類型：決策
- 狀態：有效
- 日期：2026-09-03

- 出處：KARST-174 交付(commit 1ccdead/76d7bf0;票 raised;生產庫雜湊 b168e9f45b578cf9 不變)。主 agent 依 D-072 收案並答舉手。

- 背景：主 agent 立場(D-110):①編表人在刪除前核出票面前提錯了(五份之中三份是衍生物),沒有照票面刪,對——票面是我寫的,錯在我把 KARST-167 報告的描述照搬。②歷史分頁 227MB 現時掛在一張已關的票的目錄下,下次清理極易再被當副本刪走,而且正本自稱單一正本卻缺四分之一公司的早年歷史,這是結構問題不是文檔問題,收編加補抓是唯一對的答案;丙(只靠 README 警告)靠人記得讀,否決。③「首次申報日當上市日」這條代理本來就弱(老公司換 CIK、分拆、由 ADR 轉本地上市都會令它失真),補齊分頁後仍要另找上市日正本(交易所首個交易日),留用戶討論後開。④AGENTS.md 在本倉不存在,派工指令要改為 CONTEXT.md 與 HANDOFF.md。

- 決策：
  1. KARST-174 結論收貨;舉手答甲:開票把 1,051 個歷史分頁與 99 份宇宙外公司收編入 data/sec/submissions/,補抓餘下 1,765 個分頁,重算首次申報年分佈,A-046 依結果更新
  2. 首次申報日不再當上市日唯一代理;上市日正本另議(留用戶討論)
  3. 派工指令「先讀 AGENTS.md」改為 CONTEXT.md 與 HANDOFF.md

- **用戶原話（原文照錄）**

  > (用戶未裁;屬 D-072 授權內收案)

- 影響：D-134 在申報索引這一格落地;正本殘缺列為已知缺陷並開票修。

## D-162 KARST-176 收案:淨現金篩選四步重驗——第①步完全重現 KARST-166 的 AUC 0.6483;只換面板 v3 0.5996、只換宇宙為小型股 v1 0.7684、全換 0.6183,四步皆存在、無一跌穿 0.55,即 KARST-173 量到「不存在」不由換面板/宇宙/價格庫造成;附錄診斷找出真正分歧在口徑:N2(現金 − 總債務)淨現金為正比率十倍股對宇宙差 17.3pp,N1(現金 + 短投 − 負債總額)只差 4.1pp,兩口徑 AUC 相若(0.618 對 0.608)——以排序看兩者都分得開,以符號看只有 N2 分得開;總債務覆蓋 41.4% 不是主因(以短期借款補算後 51.7%,AUC 幾乎不變);租賃負債原料層無標籤補不到;CONTEXT.md 新格「淨現金口徑(N1/N2)」;代價:N2 只在約一半公司算得出,門檻誤殺約一半真十倍格(27%–65%)
- 類型：決策
- 狀態：有效
- 日期：2026-09-03

- 出處：KARST-176 交付(commit d10c3f0 判準/3e85454/21e5c99/955340f;報告 research/2026-09-03-淨現金篩選重驗.md;生產庫雜湊 b168e9f45b578cf9 不變;零新抓)。主 agent 依 D-072 答舉手並收案。

- 背景：主 agent 立場(D-110):①用戶 D-155 原話裁的是「不欠債、輸得起」,「不欠債」字面就是現金對債務,不是現金對全部負債(負債總額含應付帳款、遞延收入等營運項目,不是欠債)。所以釘 N2 不是新裁決,是把用戶那句話落地成唯一算法;KARST-173 用 N1 是實作偏離,不是用戶裁錯。②D-155 維持;但兩項代價要用戶知道:一半公司算不出(缺長期債標籤者按「取不到」處理,不當作不合格也不當作合格,選股層另設「算不出」一類),以及這條門檻誤殺約一半真十倍格——這與 D-155 當日我講的「淨現金是同向且不殺人的篩」不一致,那句話要收回:它同向,但會殺一半。③是否值得為了排序訊號承受一半誤殺,屬集中長賠率注的取捨,留用戶討論。

- 決策：
  1. KARST-176 結論收貨;舉手答乙:D-155 維持,淨現金口徑釘死為 N2(現金 − 總債務,以申報日可得值),寫入 CONTEXT.md
  2. 算不出 N2 的公司在選股層記「算不出」,不作合格亦不作不合格;租賃負債待擴標籤表後再議
  3. 收回 D-155 當日「不殺人」一句:N2 門檻誤殺約一半真十倍格,是否承受留用戶討論
  4. KARST-173 對 D-155 的「不存在」判詞作廢(口徑偏離)

- **用戶原話（原文照錄）**

  > (依用戶 2026-09-03 D-155 原話「不欠債、輸得起」推出口徑為 N2;用戶未另裁)

- 影響：D-155 由一句話變成一個算法;十倍股安全邊際結論由「同向不殺」改為「同向但殺一半」。

## D-163 KARST-175 收案(票留舉手,與 KARST-170 同待用戶裁):敘事鏈層 v3 甲版補缺重跑——補回 62 家(343 家中只 XOM/PXD/GTBIF 取不到,XOM 因代號今日指向新設控股公司被宇宙規則剔走,相對 v3 倒退一家),2023-06-30 切片 265 家/49 鏈,解析度倍數 2.37(v3 2.82),G1−G2 +0.106,bootstrap 95% 置信區間 [+0.020, +0.217] 下限過零,可配對 171/246,運氣帶第 100 百分位;2025 切片同樣過零([+0.014, +0.206]);等效獨立層數 3.50 對板塊 1.96;判詞「存在」(限事後表的解析度),A-038 改 holds(範圍限死事後表);關鍵診斷:換價格來源效果為零(限在 v3 原 204 家重量逐位相同),差別全來自補缺,機制是量度變穩(單成員層 9 條→3 條)不是效果變大;但補回的 62 家不是隨機——是最純的主題鏈(鈾礦、聯網電視廣告、中國線上內容、太陽能),按新舊拆分 G1−G2 舊×舊 +0.102、新×新 +0.170,最強證據與最重事後眼光落在同一批公司;編表人押先做一張零新數據的穩健性檢查(剔四條最純主題鏈或逐鏈留一)才開事前資訊源票
- 類型：決策
- 狀態：有效
- 日期：2026-09-03

- 出處：KARST-175 交付(commit 9a7add0 判準/a77e9e1/06a3bd0;報告 research/2026-09-03-敘事鏈層v3甲版補缺重跑.md;生產庫雜湊 b168e9f45b578cf9 不變;yfinance 只抓 85 家子行業)。主 agent 依 D-072 收案;方向連同 KARST-170 交用戶討論。

- 背景：主 agent 立場(D-110):①D-159 第一步的閘過了:甲版由「量不出」改「存在」,而且過線的原因是我押的那個(補缺令量度變穩)。②但編表人的警告比過線更重要:增量全來自事後最容易抓出來的那幾堆主題股,即「存在」有一部分可能只是「編表人記得 2023 年哪幾堆股一齊升」。逐鏈留一檢查零成本,應做,而且我預期會過(舊×舊本身已 +0.102,與 v3 原數同,只是置信區間窄一點),過了才算真正拿到開事前資訊源票的門票。③XOM 那一家暴露宇宙規則一個洞:代號被新控股公司承接時,舊實體的歷史被整段剔走;要在宇宙規則加「代號承接」處理,留用戶討論後開。④用戶 2026-09-03 已講明三隊做完停下等討論,本票不再自行開穩健性檢查票,列入討論議程第一項。

- 決策：
  1. KARST-175 結論收貨;甲版判詞由量不出改存在(限事後表解析度);A-038 holds(範圍限事後表);A-042 維持 overturned
  2. KARST-175 與 KARST-170 兩票留 raised,待用戶討論鏈層去向;主 agent 建議次序:零成本逐鏈留一穩健性檢查 → 過關才開事前資訊源票(一張票一個死線)→ 不過關鏈層降為研究用途
  3. 宇宙規則「代號承接」洞(XOM)列入討論後善後清單

- **用戶原話（原文照錄）**

  > (用戶未裁;用戶 2026-09-03 原話「Wait for me for further discussion」,故不再自行推進)

- 影響：鏈層路線由「待證」回到「事後有解析度、事前未證」;下一步等用戶。
