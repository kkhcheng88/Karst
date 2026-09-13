# 決策簿 — Karst

> 鐵律:本簿永遠只寫「現在的真相」;歷史由 git 保存。
>
> **2026-09-14 重寫(D-177)**:根基重整時只保留現行有效的條目;V1 引擎期(D-001 至 D-126)與①研究期的其餘條目全部移出,全文在 git 歷史與 tag `pre-reset-2026-09-13`(備份亦在 `~/.claude/backups/decisions.md.2026-09-14.bak`)。條目次序按編號;新條目照舊格式接在末尾。

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

## D-165 用戶裁:開發暫停,先做一輪「最新可用資源」研究;券商接口 Longbridge 與 Futu 兩者並用(Longbridge 已接入,美股即時報價含盤前盤後夜盤;Futu 主力路線須本機常駐 OpenD)。比較報告落 scratchpad longbridge-vs-futu.md(非項目檔)
- 類型：決策
- 狀態：有效
- 日期：2026-09-05

- 出處：用戶 2026-09-05 原話:「So I think I will use both. Actually I want to stop a bit on the development. And do some research on the latest resources that we can have first」

- 背景：主 agent 立場(D-110):①暫停開發是對的時機——資料層剛換代,三個舊結論剛重量,鏈層與淨現金兩條路都停在「要不要再投」的位,這時多看外面有什麼比多開一張票值錢。②「資源」要先定義範圍,否則研究會散:我建議四類——數據源(尤其退市歷史、業績電話會議、事件時鐘)、現成回測與因子框架、學術與公開策略紀錄、AI 接口(MCP/CLI)工具;每類先出一頁清單再深挖。③研究票由 sonnet 做搜集、opus 做評估(D-160 派工規則)。

- 決策：
  1. Karst 開發線暫停;KARST-170、175 舉手維持待裁,不開新實作票
  2. 券商接口:Longbridge 與 Futu 並用;Longbridge 作無人值守報價與美股基本面原料,Futu 作港股深度與期權異動掃描
  3. 開一輪資源研究,範圍待用戶確認四類分法

- **用戶原話（原文照錄）**

  > So I think I will use both. Actually I want to stop a bit on the development. And do some research on the latest resources that we can have first

- 影響：路線圖由「重量舊結論」轉入「資源研究」階段;討論議程四項(鏈層去向、淨現金取捨、停手線、三件善後)押後。

## D-166 用戶裁項目總方向:不做即日/剝頭皮,押基本面或波段;投資核心是基本面與敘事,技術分析只在關鍵事件披露之間(最長一個業績週期約三個月)讀價格行為;四類注按風險回報遞增——①錯殺注(基本面強、被拋棄,10–20%)②趨勢注(基本面好、敘事已知、已高但仍上調)③熱敘事注(敘事已知、基本面差、已高)④未共識敘事注(我們認為敘事好、市場爭論中、基本面差、未高,500–1000%+);敘事三件=護城河、經濟學(供需/技術商業化)、財務(債務/破產風險);注碼跨注分散、注內集中(一類押一兩隻不押五至十隻);四類都值得探索。全文正本 research/2026-09-06-用戶投資框架四類注.md
- 類型：決策
- 狀態：有效
- 日期：2026-09-06

- 出處：用戶 2026-09-06 原話(全文見研究檔第一節),節錄:「I want we won't be scapling or day trader […] So I will bet on the fundementals or swing trade」「The core of investment is still on the fundmentals, the business or the Narrtive itself」「Technical Analysis is still useful between the disclosure of key events […] within the result period (like every 3 month at most as a cycle)」「Please mark this down in the overall idea of the repo and project, and you should always in your mind to achieve this with me」。同一訊息用戶駁回主 agent「時間是免費的數據源」一句:「I can't accept 時間是免費的數據源 this way […] This is very crazy」

- 背景：主 agent 立場(D-110,詳見研究檔第三節):①三前提同意,與本週實測(價格上無長期訊號)一致;技術線收窄到事件窗價格行為後可重開,題目換成「業績間的價量形態有沒有資訊」。②「時間是免費數據源」收回作為方法:等數據不是策略;論點卡留作成績表用,方向由框架定不由數據浮現。③四類注是一條「基本面好壞 × 市場已否共識」的光譜,同一公司會沿光譜移動;平台要做一套分類器加按類治理,不是四套引擎,換類本身是最重要事件。④四類死法不同:價值陷阱/估值頂/純資金推動(與 D-147 GME 類邊界要寫死)/敘事不成立加燒錢破產(KARST-166 量到燒錢是十倍股反向篩,四類注只能用不欠債篩)。⑤10–20% 與 500–1000% 是贏注回報不是期望值,四類命中率可能一兩成,四數(D-148)照報。⑥現有資產全部有掛處:十倍股研究=四類起步剖面、鏈層=敘事共識度量器、錯殺策略(D-018)=一類、樽頸=二類/四類供需版。⑦不同意一點:市值加權指數 ETF 是趨勢注不是錯殺注,等權/價值型才近似一類,影響一類基準選擇。

- 決策：
  1. 項目總方向以研究檔 research/2026-09-06-用戶投資框架四類注.md 為正本;HANDOFF.md 第零節、CONTEXT.md 四類注詞條同步;任何策略票開工前先讀
  2. 策略範圍:不做即日與剝頭皮;持有期數週至數季;技術分析只用於關鍵事件披露之間的價格行為,不作長期訊號
  3. 四類注①錯殺注②趨勢注③熱敘事注④未共識敘事注全部列入探索範圍;每類先出一頁文獻結論(D-129)再開存在性測試;三類與 D-147 純資金推動股的邊界須先寫死
  4. 暫停期(D-165)第一件落地改為:四類注分類器與論點卡規格(類別、基本面證據、敘事證據、市場共識度量、定價位置、推翻條件、時限、注碼理由;機械紅線;只追加不改寫)
  5. 「時間是免費的數據源」不再作為方法主張;向前記錄只作成績表

- **用戶原話（原文照錄）**

  > I want we won't be scapling or day trader as our infrastuture, capital or execution will not be as fast or as resourceful as the institution or fund house. So I will bet on the fundementals or swing trade. […] 1) The core of investment is still on the fundmentals, the business or the Narrtive itself. 2) Technical Analysis is still useful between the disclosure of key events […] I think for each of them it is worth to explore. Please mark this down in the overall idea of the repo and project, and you should always in your mind to achieve this with me

- 影響：D-165 的資源研究範圍由「四類資源」改為「四類注各自要什麼資源」;技術線由 D-147 後的擱置轉為收窄重開;十倍股/鏈層/錯殺/樽頸四條舊線改掛到四類注下;KARST-170、175 舉手維持。

## D-167 用戶裁:專家心得全部可作參考,但一律要加權;參考組以散戶起家有對帳單的交易者與小型集中基金為主,大資本人物只借框架不借戰術;Cathie Wood 不做。落地為倉內知識庫 knowledge/(來源層+結論層)、來源權重四格(時代/持有期/親身做過/資本規模)、擴充待蒸餾名單 reference-list.md
- 類型：決策
- 狀態：有效
- 日期：2026-09-07

- 出處：用戶 2026-09-07 原話:「It is ok, all voice can be a good reference it is only a matter of how we manage ourselves, but all the expert voice should be weighted」「Here I use Trader is because we are not having the capital as soros or buffett. We have retail trader」「Yes, I think she is just betting on a believe, I don't see a key insight especially her timing is too bad」「please expand the list with your suggestion. Properly manage these distilled knowledge in our repo to be reusable」

- 背景：主 agent 立場(D-110):①加權四格由我提出,用戶「should be weighted」一句推出,四格內容(era/horizon/practised/capital)是主 agent 定案,資本規模一格由用戶「we have retail trader」一句推出。②散戶真正有的邊四條:結構邊(機構不能持有的那格)、行為邊(無基準無季考)、資訊邊(利基)、分析邊(agent 讀全宇宙申報,我們獨有);參考對象要能證明自己用過其中一條。③第一輪書庫蒸餾(七隊)已浮現三個對 D-166 框架的真挑戰:Porter/Aschenbrenner「對的敘事錢落在瓶頸不落在主角,可用②押」;Lynch「明文拒收③④」;Tharp/宏觀派「四類注一年三五注,期望總值不利,宏觀派用九成底倉一成機會注繞開」;加 Market Wizards 十四位「生死線在注碼與離場,框架未寫這一半」。這些不砍四類注,轉為論點卡必填格與 insights/conflicts-with-framework.md,待總合成後給用戶完整立場。

- 決策：
  1. 倉內建 knowledge/ 知識庫:來源層(books/ traders/ communities/ social/)與結論層(insights/ 按四類注問題分檔);策略票只引結論層;原件不入倉(留 C:\projects\Investment\)
  2. 每個來源檔頭部必填來源權重四格(時代/持有期/親身做過/資本規模,各高中低+一句理由);四格皆低者只作背景不入結論句;大資本來源框架不折減、戰術折減
  3. 待蒸餾名單照 knowledge/reference-list.md 五組(主參考散戶交易者/小型集中基金信函/大資本框架與案例/反面教材紅線/社群與本地),第二輪次序 Kullamägi、Stine、Nomad 先行;材料搜集 sonnet、對照 opus
  4. Cathie Wood / ARK 不蒸餾(用戶裁);X 上無往績網紅、量化論文、Hougaard 方法論不做
  5. 第一輪蒸餾對框架的挑戰不砍四類注,改為四類注論點卡必填格:(a) 敘事若成真錢落在主角還是瓶頸環節;(b) 不欠債篩加時間止損兜底;(c) 注碼與離場規則(集中必須配快走條件,四類注無逃生條件則注碼降級)

- **用戶原話（原文照錄）**

  > all voice can be a good reference it is only a matter of how we manage ourselves, but all the expert voice should be weighted […] we are not having the capital as soros or buffett. We have retail trader […] Properly manage these distilled knowledge in our repo to be reusable

- 影響：D-165 資源研究線由「找數據源」正式轉為「蒸餾人的心得並加權」;D-166 框架將補「注碼與離場」一半與「錢落在哪裡」一格(待總合成後修訂研究檔);CONTEXT.md 新增「來源權重四格」「知識庫」兩詞條。

## D-168 歷史資料的用途只剩三件:基準率、治理校準、分類器時點考核;不再做訊號搜尋。資料層只留原料級(EDGAR 申報文本與財務事實、日線價格),衍生表全刪;引擎回測模組角色由因子掃描改為事件研究加分類器考核;實際操作用當下非結構化資料由模型判讀
- 類型：決策
- 狀態：有效
- 日期：2026-09-07

- 出處：用戶 2026-09-07 原話:「I think most of the history data is serving the backtest only? As I think in our new findings, it seems most of unstructured data transformation with LLM + "Current" financial data to assess?」;主 agent 答一半同意一半不同意並提出三用途,用戶答「yes please do this」

- 背景：背景:八月七輪回測全部輸指數(D-112/D-125/D-122–129),證明在歷史數字裡找訊號這條路不通;D-166 四類注是判斷型框架,分類、共識階段、被迫賣、持貨結構全由當下申報、電話會、持股披露等非結構化文字判讀。主 agent 立場(D-110):用戶對的一半是操作只需當下資料;不同意的一半是歷史有三件事非它不可——(1) 基準率:Tharp 期望值必須寫得出,錯殺後 30/60/90 日回報、業績跳空後漂移、指數剔除後見底時間,只能由歷史事件量出,是事件研究不是因子格;(2) 治理校準:止蝕幅度、時間閘只能在歷史價格路徑上量(Freeman-Shor 三萬筆交易的用法),只需日線;(3) 分類器考核:模型讀歷史年報與電話會能否在當時分對類、判對共識階段,要用歷史申報文本做時點測試,並提防模型記得結局(用知識截止後時段或遮公司名)。同日用戶已裁刪除實驗中間產物 4.2 GB 與 Alpha158 因子表 5.7 GB(原話「①實驗目錄 4.2 GB,併入 99 家後刪; OK」「② Delete」),699 家原始 companyfacts 中 99 家不在快取者先併入 data/sec 再刪。

- 決策：
  1. 歷史資料的合法用途只有三件:基準率(事件研究)、治理規則校準(止蝕、時間閘、注碼)、分類器時點考核(模型讀歷史申報能否當時分對類);不再開任何「歷史數字找訊號」的票
  2. 資料層只留原料級:data/sec(EDGAR 申報文本、companyfacts、submissions,D-134 唯一快取)、data/prices 日線、universe、面板;衍生表(因子、運行輸出、掃描矩陣)一律不保留,要用時由原料重算
  3. 引擎回測模組角色改為事件研究加分類器考核;因子掃描與參數格掃描功能凍結不刪(D-165 引擎凍結不變)
  4. 每張類別規格書(KARST-178/179 起)的每個手法必列:需要哪些基準率、來自哪段歷史、樣本大約多少事件;以及實際操作時要讀哪些當下非結構化資料
  5. 分類器考核必須防模型事後知識:用模型知識截止後的時段,或遮住公司名與日期;考核設計寫進規格書待測節

- **用戶原話（原文照錄）**

  > I think most of the history data is serving the backtest only? As I think in our new findings, it seems most of unstructured data transformation with LLM + "Current" financial data to assess? […] yes please do this

- 影響：data/ 由約 10 GB 減至約 4 GB;實驗目錄與因子表已刪(2026-09-07 倉重整);研究方向由「回測找優勢」轉為「量基準率、校準治理、考核判讀」;CONTEXT.md 新增「基準率」「分類器時點考核」兩詞條。

## D-169 ①錯殺注研究立項(工作版本):機制改為「股價已反映過度悲觀預期、一年內有可核反證、隨證據逐步投入」;兩層漏斗(等級初篩、三個數決定)但護城河等級不得降低壓力情境;行業殺錯作候選來源並加替代程度證據要求;計算器分長期價值與一年回報;四層對照即刻紙上交易;資金配置待實作證據
- 類型：決策
- 狀態：有效
- 日期：2026-09-08

- 出處：兩日講解段(2026-09-07 至 08,①材料八節)後,用戶對主 agent「用這個方案加兩處調整作①的工作版本,可以嗎」答「ok」;外部評論(GPT)三輪,最終意見「同意把這個方向定為①的研究工作版本,開始規格票、計算器及候選池;但護城河與壓力情境的接線,需要先改」;五項必改由主 agent 依 D-072 接受。用戶另有兩句直接形成本決定:「my perference is actually on 1 month to 1 year」「Can the still have the 「有、弱、無」… Seems with some grades or level will be easier」

- 背景：背景:D-166 四類注;D-168 歷史資料只作基準率/治理校準/時點考核。①講解段對齊出的共用層(候選池兩道閘加可證偽故事、定位卡三相位、兩個鐘、進場三格分開量、一個池三個觸發)全部保留為定義;外部評論第一輪指出報告把假說寫成判斷(確認進場=高命中率低賠率、一個月至一季按定義是②、①與②相關性低等),已重分為定義/假說/預登記規則;第二輪以基金經理位置提出改造方案,主 agent 採用並作兩處調整;第三輪通過立項並列五項必改。主 agent 立場:方案好過自己原版,因為把「護城河還在不在」的是非題改成「現價要求多壞才合理」的三個數,模型任務由投票改為估損害幅度與時間,可核可考;代價是研究量增、頻率降、形狀接近 Lauer 六道閘與預期投資,優勢主張(模型讀非結構化資料的速度、持有能力)全部降為待驗證假說。

- 決策：
  1. ①機制一句:尋找股價已反映過度悲觀預期、未來一年內有機會出現可核查反證的公司,隨證據改善逐步投入資金;容許「市場方向對、幅度過頭」,不要求證明護城河無損
  2. 兩層漏斗:第一層定位卡全用等級(護城河四項有/弱/無加有效期、故事仍在/受損未破/已破、三相位、負債閘),另設「資料不足」一格;只作淘汰與排序。第二層對過篩者答三個數(現價隱含要壞到什麼程度、合理結果與根據、只是沒那麼壞還有多少回報)加證據日曆。護城河等級只用來指出要查證的指標,不得直接降低壓力情境跌幅;壓力情境必須納入「原先認為的護城河失效」;倉位除估計跌幅外另設單股及共同風險上限
  3. 第一版篩:財務透明、流動性足夠、已有現金流、壓力下不依賴短期再融資。行業殺錯(含技術替代型)作候選來源不降觀察名單,但每筆論點收窄到單一產品或客群,並須至少有一項持有期內可觀察、能區分「替代尚未反映」與「實際替代有限」、且對整體估值有實質影響的證據;無此證據者留候選不升可交易。「護城河全無、故事已破」排除於第一版是能力範圍限制,不寫成普遍投資規律。被迫賣作小型支線(每月掃描為候選來源);高槓桿重組與困境普通股不納入
  4. 以「下一項能改變估值的證據」選股再定進場;按證據狀態分觀察池/小額初始/加倉/價已反映則不買;加倉每次重新成立,價跌不自動加。倉位≈組合損失預算÷壓力情境跌幅,同一故事共用預算並查共同因素
  5. 退出三問:關鍵預測被推翻?剩餘回報值不值?預定證據按期出現?−33% 只作警報加強制覆核,不是自動退出;一年為硬上限並納入估值(估一年內市場可能承認多少價值),到期未兌現按規則退出
  6. 隱含預期計算器最低可行版本:固定部分假設逐組反推、展示敏感度;三組假設不可省(經營路徑、現金流轉換含股權薪酬與稀釋、長期估值含終值佔比);分開輸出長期價值範圍與一年持有回報情境
  7. 研究與紙上交易即刻開始:四層對照(單純大跌→加估值財務→加模型→加確認執行),同一候選同一截止日先鎖定不含模型的判斷再記錄模型改變了什麼;入選與被拒候選一併記錄;前瞻記錄分開研究效率、預測能力(預登記預測,對照上期延續/簡單趨勢/指引,Brier 或適當評分規則,校準與區間集中度一起看)、投資結果三類
  8. 「比多數基金多一至三季的耐性」降為待驗證持有能力假說;「模型沒有增量」與「①沒有投資價值」分開判;①的實際資金配置等待實作證據,不為湊齊四類注保留席位
  9. 先用少量真實候選(含至少一個被拒個案)把完整流程走通,再擴充框架;②材料對齊同步開始

- **用戶原話（原文照錄）**

  > ok, can we make the respons to GPT for me to paste for his final comment? […] I follow you expertise.

- 影響：KARST-178 ①規格書按本決定重寫(原「甲已知賣家/乙未知賣家」兩手法作廢);新開隱含預期計算器原型、①候選池第一版兩張票;基準率表設計納入評論修正(確認訊號當時可辨、由可成交時點計、未成熟樣本標記、非獨立樣本、保留驗證資料);共用層寫入 strategy/framework.md 待後續票;CONTEXT.md 待加「定位卡」「隱含預期」「證據日曆」三詞條。

## D-170 注碼三數(單筆損失預算、單股上限、同一故事共用上限)延後至四類注全部成形後,按組合層一起定;KARST-184 所用組合 2% 只是示例值,不是現役參數
- 類型：決策
- 狀態：有效
- 日期：2026-09-09

- 出處：用戶 2026-09-09 對主 agent「三個注碼數字未經你批核」的回應。原話:「I don't know. Can we review the balance of betting after all 4 strategy is formed, as the percentage of each could impact?」

- 背景：KARST-184 ①候選池走通時,倉位公式(組合損失預算÷壓力情境跌幅)需要一個損失預算才算得出數,隊伍用了組合 2% 作示例並標明未經對齊。主 agent 提請用戶批核三個數;用戶指出四類注各佔多少會影響每一注的注碼,應在四類齊備後一併看。主 agent 立場:同意。注碼是組合層決定,單獨為①定數等於預先分配了①的席位,與 D-169「①的實際資金配置等待實作證據,不為湊齊四類注保留席位」同一方向。

- 決策：
  1. 單筆損失預算、單股上限、同一故事共用上限三個數,待②③④規格成形後在組合層一次過定,同時考慮四類注各佔比例
  2. 在此之前,①的候選卡與計算器輸出繼續以組合 2% 作示例損失預算,所有輸出必須標明「示例值,未經用戶對齊」;不得用作真實下注
  3. 四類注的注碼平衡另開一張組合層票,依賴②③④規格票

- **用戶原話（原文照錄）**

  > I don't know. Can we review the balance of betting after all 4 strategy is formed, as the percentage of each could impact?

- 影響：KARST-178 ①規格書的倉位一節寫成「公式已定、參數待組合層」;KARST-184 舉手第一項(損失預算 2% 未對齊)以本決定結案;組合層注碼票待②③④規格票開出後再開。

## D-171 ①錯殺注不留固定資金席位,降為「有機會才做」的研究線;不設研究到期日——四類注全部研究完才作任何確認;「負期望」措詞收回,歷史表結論改為「多數輸、少數大贏、平均略正、可靠性未核」
- 類型：決策
- 狀態：有效
- 日期：2026-09-09

- 出處：第二輪外部評論(GPT,2026-09-09,原文在 research/2026-09-methodology/2026-09-09-①第二輪外部評論(原文).md)建議「暫不保留固定資金席位,保留為低頻、需要明確證據的機會型研究;但不要以已證明負期望為理由判它失敗」;主 agent 逐條評估後向用戶提三件待裁。用戶 2026-09-09 原話:第一件「OK」;第二件(到期日)「Please don't worry on this, we still reseearching the 1st strategy only.... 3 more to go to confirm anything」;第三件(無大跌觸發的新版本)用戶要求「Give more details on this」,未裁。

- 背景：KARST-187 基準率表第一版:相對大市六十日跌逾 25% 且過負債閘與現金流閘的情境,十二個月勝率 45%、中位輸大市 2.5–10%、賠率(贏家中位/輸家中位)約 1.0;主 agent 對用戶稱之為「負期望」。外部評論指出同表平均超額為正(A2 全期 +2.2%、A 版 +5.2%,驗證年份約零或略負),中位負而平均正是右偏分佈,不能稱負期望;主 agent 核實賠率欄確為中位對中位(make_tables.py:147),接受更正。外部評論另指出 LULU「隱含五年路徑與一年指引重疊」是期限錯配,主 agent 接受,該判斷改為未判。用戶對到期日的回應意思是:①仍在研究階段,②③④未研究完之前不對任何策略作確認或設限,到期日無意義。

- 決策：
  1. ①錯殺注不保留固定資金席位;定位為低頻、需要明確證據的機會型研究線
  2. 不為①設研究到期日或工時上限;任何策略的確認、降級或資金配置,待四類注全部研究完後在組合層一併裁(與 D-170 同一方向)
  3. 對外與對內措詞:①歷史情境表的結論由「負期望」改為「多數事件輸、少數大贏、平均略正、可靠性與可實現程度未核」;「篩選層零貢獻」一句收回,待與不加閘的大跌對照後再講
  4. LULU「市場沒有比管理層更悲觀」的判斷作廢(期限錯配),待以三類機制標籤重判
  5. 在此期間①只做前瞻登記、紙上配置與資料修正(KARST-188/192/193),不擴建交易功能

- **用戶原話（原文照錄）**

  > OK / Please don't worry on this, we still reseearching the 1st strategy only.... 3 more to go to confirm anything

- 影響：KARST-178 規格書第九節排序提案與第三節倉位保持「提案/參數待組合層」;②③④講解按原次序進行;第二輪外部評論其餘接受項(反推所需成功率、四情境退出估值、三類機制標籤、前瞻預測含被拒者、規則版本號綁定候選卡)於下一份回覆檔逐項落位後,再視乎用戶對第三件(無大跌觸發版本)的裁決開票。

## D-174 ①三件定案:壓力跌幅改為證偽出場價;①定義加「價格已跌破 200 日線」,線之上的深跌歸②回調;KARST-197 收貨後凍結①工具建設轉②講解
- 類型：決策
- 狀態：有效
- 日期：2026-09-10

- 出處：用戶 2026-09-10 原話:「按第一性原則,分母應該是證偽出場價 << Yes」;「我建議排序重出那隊收貨後,①工具建設凍結,轉去②講解。 << Yes」;200 日線一項由用戶問句推出:「If kill should have 200MA broken already? Otherwise should be counted as 回調?」——主 agent 同意並記為定義,不是技術面否決。賣家理由軸一項用戶反駁(原話:「But then 1 year has almost no case and this is only 1 of the 錯殺? I think we have discussed earlier already」),主 agent 收回「最值得補」的講法,被迫賣掃描只留作次要候選來源。

- 背景：第一性自查(①對齊紀錄第 26 條)後用戶逐條回應。證偽出場價:KARST-188 六十家有五十六家壓力公式失效,因入池條件已跌兩成半;改由判斷層按預登記預測失效點定出場價,計算器只答「現價假設了什麼」。200 日線:基準率表線之上格十二個月成績最差(勝率約 35%),用戶提出「殺過的股價應已跌穿 200 日線,否則是回調」,把它由技術面否決改為①定義的一部分,同時解決 D-166「技術面只在事件窗內」的合規疑問,亦答了 2026-09-09 用戶問 BE/AXTI/NBIS 深回調去向——歸②。賣家理由:①三種機制(被迫賣、情緒恐慌、敘事重估)中被迫賣一年幾乎無個案,用戶主線是行業殺錯(對齊紀錄第 1 條),行業殺/個別殺軸已在基準率表。

- 決策：
  1. ①賠率分母改為證偽出場價:每家由判斷層按預登記預測失效點寫出場價,計算器的壓力跌幅公式降為參考欄不再作分母;KARST-197 若已用舊分母,排序表加一欄標明分母口徑待換
  2. ①定義加一條:觸發時價格須已在 200 日線之下;線之上的深跌不入①池,歸②趨勢注的回調入口。此為定義,不是技術面否決;排序表「被否決(形態)」欄相應改為「不入池(線上)」並照列供對照
  3. KARST-197 收貨後凍結①工具建設(計算器、基準率表、池篩選腳本不再開修改票),①只做前瞻登記與季度對照;主線轉②講解
  4. 被迫賣申報掃描留作①次要候選來源,不立為優先工作

- **用戶原話（原文照錄）**

  > Yes / But then 1 year has almost no case and this is only 1 of the 錯殺? I think we have discussed earlier already / Yes / If kill should have 200MA broken already? Otherwise should be counted as 回調?

- 影響：KARST-178 規格書第一節(定義)、第二節(三個數)、第九節(排序)相應改寫;KARST-197 在跑,主 agent 以留言追加兩項口徑;②講解由第二節起。

## D-175 Karst 派工分層(研究項目,非軟件開發):需判斷的工作至少用 Opus(high);策略思考與探索由 Fable 親自執行;回測與大批量評估股票用 DeepSeek
- 類型：決策
- 狀態：有效
- 日期：2026-09-12

- 出處：用戶 2026-09-12 原話:「I think this project is a research project but not a SDLC project. So i think if anything need judgement, you should use at least high OPUS, and if it need thinking and exploration of trading strategy. Probably need you Fable to execute. But if it is for backtest or mass evaluate of stock. Then Deepseek is ok」。背景:用戶問「you are using Deepseek on this?」,主 agent 報 205–218 十四張票全部 DeepSeek Flash high,並自陳工人品質參差、關鍵判斷結論來自 GPT 對照與主 agent 而非工人。

- 背景：全域守則 2026-09-10 D-231/D-232 定「開關開着時所有委派一律 DeepSeek,effort 預設 high;Anthropic Opus 只用於獨立覆核」,以及 2026-08-04「Fable 只做主腦永不落場執行」。兩條都是為軟件開發型項目定的。Karst 現階段是方法論研究:判斷層(能力卡、模組規格、對外報告、對評論的逐條評估)的品質直接決定結論,工人在這一層曾令主 agent 多次回頭修(驗收條件重貼、票號寫反、報表用詞錯、收益分解錯誤)。本決策是 Karst 專案層對全域守則的例外,不改全域守則本身。

- 決策：
  1. 需要判斷的工作(能力卡與模組規格撰寫、對外評論報告、卡片判詞覆核、事件與籃子界定、任何要下結論的分析)至少派 Anthropic Opus,effort high;risk high 者仍照全域四層覆核
  2. 策略層面的思考與探索(四類注定位、主流程結構、模組要多問的問題、與用戶討論後的立場)由 Fable 主腦親自執行,不派工;此為 2026-08-04「Fable 不落場」在 Karst 的例外
  3. 回測、大批量填卡、取數、對照表、腳本重跑、格式整理等大量而規則明確的工作照用 DeepSeek Flash(effort high,純機械 low)
  4. 一張票同時含判斷與量產兩部分時拆票:判斷部分 Opus 或 Fable,量產部分 DeepSeek;DeepSeek 產出之中的判斷成分(例如卡上的判詞)交貨後由 Opus 或 Fable 抽查,抽查結果記票

- **用戶原話（原文照錄）**

  > I think this project is a research project but not a SDLC project. So i think if anything need judgement, you should use at least high OPUS, and if it need thinking and exploration of trading strategy. Probably need you Fable to execute. But if it is for backtest or mass evaluate of stock. Then Deepseek is ok

- 影響：Karst 倉根 CLAUDE.md 加派工分層一節;自動記憶 dispatch-model-by-judgement 更新;進行中的 KARST-218(能力卡與提示詞凍結 + 樣本外測 + 經營結果核)由 DeepSeek 跑到尾,交貨後能力卡與提示詞(判斷部分)由 Fable 親自覆核改定稿才算凍結;②③④模組撰寫由 Fable 執行;全域守則 10-dispatch §8 不改,加一句「研究型項目可在專案 CLAUDE.md 立例外」由主 agent 另行處理。

## D-176 ②第一次考試的可成交門檻改為公布前 60 個交易日日均成交額 ≥ 1,000 萬美元(取代執行口徑 v1 的 300 萬);v1 抽樣鎖定作廢並按 v1.1 重建
- 類型：決策
- 狀態：有效
- 日期：2026-09-13

- 出處：用戶 2026-09-13 原話

- 背景：主 agent 報告票 A 的入口四道門時,用戶即改可成交門檻。改動發生在判斷層(票 B)派出之前、任何結果之前,所以不構成事後選樣;但主 agent 已見過 v1 鎖定清單的 84 個公司名,故重抽必須純機械(同種子同規則),不得手動換名,並在執行紀錄寫明 v1 與 v1.1 主清單的重疊數。

- 決策：
  1. ②第一次考試宇宙門檻:公布前 60 個交易日日均(算術平均)成交額 ≥ 1,000 萬美元;其餘預設值不變。執行口徑由 v1 改 v1.1(修訂頁另檔,只改這一列)。
  2. KARST-222 交回的 v1 抽樣鎖定(2026-09-12 15:37:28,主 84 + 後備 44)作廢——作廢時未開任何判斷、未開任何 T1 後結果;檔案保留作紀錄,標「已取代」。
  3. 按 v1.1 重建:宇宙 → 逐年第 90 百分位門檻(在新宇宙上重算)→ 入口池 → 抽樣鎖定(同種子 20260912、同分層規則)→ 取證包 → 對照預測;新輸出另置 A2/,不動 A/。
  4. D-173 的 300 萬成交額線只管①,不變。

- 考慮過的替代方案：
  1. 保留 300 萬:用戶已否。
  2. 兩檔(300 萬與 1,000 萬)分開抽分開報:樣本與 Opus 成本加倍,第一場探索性考試不做;若第一場成立,第二場可加回小型股帶作敏感度。

- 為何選這個：1,000 萬美元是零售帳戶實際可成交而不推價的線;決定在任何結果之前作出。代價:剔走小型股,而業績後漂移文獻顯示小型股的反應不足較強,判斷層的潛在優勢可能一併被剔走——這是用戶知情下的取捨,評分時不另報 300 萬檔。

- **用戶原話（原文照錄）**

  > 日均成交額不少於三百萬美元。 <<< Make it 1000萬美元

- 影響：執行口徑 v1.1 修訂頁;能力卡 v1 依賴表(證據與權限紀錄檔);KARST-225 重跑票 A;票 B/C 改讀 A2/;地圖②行;②對帳單 §十二 第 6 條

## D-177 用戶裁根基重整(2026-09-13 至 14):項目以 Kira 重置,Epic「根基重整」聚焦資料與策略;只保留四類注定義與情境、能力卡 v1、②第一次考試結果與資料層(含圖書館);① 研究產物、封存區、鏈層、已取代規格與大部分舊決策一律刪除(硬刪,tag pre-reset-2026-09-13 保底);決策簿重寫為只含現行有效條目;之後從頭探索「對我們關鍵的元素」
- 類型:決策
- 狀態:有效
- 日期:2026-09-14

- 出處:用戶 2026-09-13 原話(重置指示):「I would like to reset this project with Kira. And startover with only the 4 category and scenarios, and the card in V1, and the result in V2 so far. And for the data, I would like to start to stocktake the data we have as well」;對四步方案的修訂:「OK, but i think Epic「根基重整」 will be focusing on the data and strategy, for most of the archive or even the decision.md is no longer valid from time to time, I really want to delete and hard result, and Library is part of the data yes we need to keep. Then we will start over, and explore what is the key elements for us」;2026-09-14 原話:「Pleas have a look on this conversation, you will know my latest ideas and the comment from GPT about the run. And then you can start cleaning the repo and prepare for the new move」。同日用戶另指出主 agent 的角色偏移:「I think you are started to become a listener or lead worker. You are no longer acting as my lead advisor in this research project」。

- 背景:方法論期(D-166)一星期內①做了十六張票、九輪外評,最後降為研究輔助;②第一次考試是本項目第一次量到判斷層對機械基準有穩健增量。主 agent 在此期間忘記倉內已有 Longbridge、Futu、DefeatBeta 三個資料接口,錯稱「逐字稿拿不到」,用戶由此判斷項目根基已散。主 agent 立場(D-110):同意重置;同意刪硬結果(①十六張票的產物沒有一件成為現役能力);不同意刪②考試的中間產物——第五輪外評指出 84 宗應固定為回歸測試集,主 agent 接受,推翻原定「只留摘要」;決策簿舊條目多數為 V1 引擎期與①期,與現行無關,重寫為只含現行有效的十六條加本條與 D-178。用戶對新形態的想法(agent team、觀察名單、機械掃描、論點作核心物件、TradingAgents 介面參考、資料層優先)全部登記在 ② 對帳單 §十二 第 17 條,不在本條裁定形態。

- 決策:
  1. Kira 新 Epic「根基重整」,四件交付品:D09 資料來源盤點與取數層(正本 `strategy/資料來源.md`);D10 策略正本重整(四類注定義與情境、原則、候選表、能力卡與提示詞);D11 ②第一次考試收尾與回歸測試集(報告更正、缺陷清單分級、84 宗整個目錄固定不動);D12 關鍵元素探索(論點物件、主流程、觀察名單、系統骨架選型;先用一宗真實事件跑通)。Epic「方法論期(D-166)」之下未關的票全部關檔並記原因,不再開票。
  2. 刪除(已執行,2026-09-14):`research/archive/`、`research/2026-09-methodology/` 之下全部①產物與①外評原文、`strategy/chains/`(V1 鏈層)、`strategy/cards/`、`strategy/tools/`(①計算器)、`strategy/specs/` 之下 v0 草稿、論點卡清單 v1/v2、①前瞻方案。保留:framework/principles/candidates 三份正本、能力卡 v1 兩張及其證據與權限紀錄、①提示詞 v1、②提示詞 v1/v1.1、論點卡清單 v3、②模組 v0、②③④三份對帳單、②考試整個目錄與五輪外評原文、圖書館、data/(vintage 併入 data/)。
  3. `.kira/decisions.md` 重寫為只含現行有效條目(D-127、128、134、147、148、149、165、166、167、168、169、170、171、174、175、176 加本條與 D-178);舊簿全文在 tag `pre-reset-2026-09-13` 與 git 歷史。
  4. 主 agent 角色回到顧問位:策略與形態由 Fable 親自思考並帶立場(D-175 第 2 條),量產與取數派工;每輪收線前更新地圖。

- **用戶原話(原文照錄)**

  > I would like to reset this project with Kira. And startover with only the 4 category and scenarios, and the card in V1, and the result in V2 so far. […] Epic「根基重整」 will be focusing on the data and strategy, for most of the archive or even the decision.md is no longer valid from time to time, I really want to delete and hard result, and Library is part of the data yes we need to keep. Then we will start over, and explore what is the key elements for us

- 影響:CLAUDE.md 開場匯入改為地圖加資料來源正本;HANDOFF/README/地圖全部改寫;方法論期十二張未關票關檔;自動記憶 roadmap 條目更新。

## D-178 ②第一次考試收尾(主 agent 定案,依第五輪外評 2026-09-14):84 宗固定為回歸測試集,整個考試目錄不動;能力假說措詞收窄為「開發樣本提供初步支持;對趨勢延續基準較一致,對假設不變基準的增量依賴事件類型;比指引準、投資價值、乾淨三件未證」;報告五處更正;三件補考(基數與口徑修正後的簡單基準、區間寬度評分、指引下修標籤替代版)與資料管線必修清單開票在 D11 之下,不在本輪做;2025-07 起事件只作時間留出,真正前瞻待方法凍結後登記新事件
- 類型:決策
- 狀態:有效
- 日期:2026-09-14

- 出處:第五輪外評(GPT,2026-09-13 至 14,原文 `research/2026-09-methodology/2026-09-13-②第五輪外部評論與新架構討論(原文).md` 末段對八問的回應);用戶未逐條裁,只指示「have a look … and then you can start cleaning the repo and prepare for the new move」。本條是主 agent 依 D-072 接棒的定案。

- 背景:主 agent 原定重整時只留②考試摘要;外評第八問答「不同意只保留四類定義、能力卡、結果摘要與資料盤點,那會丟掉這次工作最難重建的部分……這 84 宗最值得保留成一套固定的回歸測試資料」。主 agent 核對:考試查出的年份錯位、事後重述值、指引解析錯誤,全部只因原始取證包與修正紀錄在手才查得清;日後換資料來源或抽取程式,沒有這 84 包就無法檢查有沒有再次引入洩漏。接受。報告四處數字問題經核對:漏斗漏寫入口條件一步;「12 年」是訊號季年份 2014–2025;尺度違規 DeepSeek 臂 2 宗、Opus 臂 1 宗;九包修正之中五宗只改訊號季行未重判,剔走後兩臂中位 5.3 / 4.9 對 C2 11.0、C3 7.4,結論不變。

- 決策:
  1. `research/2026-09-methodology/2026-09-12-②第一次考試/` 整個目錄(母體、名單、種子、取證包、兩臂原始輸出含作廢、提示詞、執行紀錄、真值、基準、評分程式、修正紀錄)固定為回歸測試集,只准追加不准改寫;日後任何資料管線或抽取程式改動,須對這 84 包重跑越界、錯位、引用三項檢查
  2. 能力假說措詞照外評收窄;「一半優勢來自極端基數」改為「移除門檻決定型事件後,對假設不變基準的優勢明顯縮小」
  3. 補考三件與資料管線必修清單(季度/年份錯位、截止後數值、首報與重述混用、單位正負號、分拆/終止經營口徑、影響入口的指引解析、下修標籤、輸入版本與重跑規則、同業錯配若影響入池)在 D11 開票;可只作標籤的(缺逐字稿、缺歷史共識、商品/併購/負基數特徵、改善類型)不修
  4. 兩臂處置(點值 DeepSeek、區間與核資料 Opus)降為待驗證配置,補區間寬度與成本後再定

- 影響:地圖②格、能力卡 v1 證據與權限紀錄檔、報告第八節。

## D-179 用戶定義產品(2026-09-14):第一版是可日常使用的投研工作台,不是研究品——以最強前沿模型、最新資料(不在訓練資料內)與強制紀律,對市場、價值鏈、基本面、然後技術面作完整分析,並按本人投資原則與大師知識所定的時間框架給出投資建議;能力考試只作系統品質改善,不作功能交付的前提;「已量度 / 未量度」逐格標籤否決
- 類型:決策
- 狀態:有效
- 日期:2026-09-14

- 出處:用戶 2026-09-14 原話(與 GPT 對話,原文 `research/2026-09-methodology/2026-09-13-②第五輪外部評論與新架構討論(原文).md`;三段原話見 quote 欄)。主 agent 兩次提案(「先跑一宗真實事件」、「每格標已量度/未量度」)均被用戶否決,本條記用戶裁決。

- 背景:主 agent 於根基重整後提出第一版只做「資料來源正本、取證包管線、論點卡、一宗真實事件跑通」,並要求每格判斷標「已量度 / 未量度」。用戶指出:項目是投資項目不是學術研究,第一天起產物就要能被本人消費;「跑通一宗事件」不切實際(市場每日演變,鎖不住);TradingAgents 一類系統都是一套通用 agent team 適用於任何股票;逐格標籤只是把責任推回投資者,而且過去量度不代表未來。主 agent 立場(D-110):兩點都認錯——「一宗事件」把產品又寫成研究品;標籤是品管工具放錯了位置,正確形式是每格寫依據、關鍵假設、最強反證、缺哪項資料及其影響,品管紀錄留後台。補一句:②考試證明紀律與資料比模型更決定質素(兩模型點值只差 0.5 點,取證包錯位卻可翻轉結論),所以本定義的落點在資料層與版本控制,不在框架。

- 決策:
  1. 第一版交付通用的投資分析與追蹤工作台:三個入口(股票分析 / 觀察名單與持倉追蹤 / 今日市場),股票頁首屏六行(目前建議、主要理由、關鍵假設、最強反證、改變行動的條件、與上次相比),另含技術結構與動能、內在價值正向與反向及計算依據、前瞻投資計劃與風險回報
  2. 分析紀律固定六層並有因果連結:市場與宏觀 → 產業與價值鏈 → 公司基本面 → 估值與預期 → 技術與市場行為 → 投資綜合;時間框架按本人原則作共同約束;各角色開工前讀同一份投資委託(目的與期限、偏好與風險、持倉與資金、買賣原則)
  3. 負責關鍵判斷的強模型直接閱讀原始證據、自行補查、可挑戰上游摘要;便宜模型與程式只做去重、格式、計算(與 D-175 一致)
  4. 資料按來源與維度分組,帶時間戳與差異,只重評受影響部分;產業與價值鏈層研究共用並傳到公司(用戶原話「the key architecture concept is actually on the version control of the stock related information and industry level information」);資料模型第一天設計
  5. ②第一次考試與 84 宗回歸集只作系統品質改善與日後成效評估,不作逐格信任標籤,不作交付前提;實際使用中的每張卡連資料截止時間留存
  6. 主 agent 附加立場(非用戶裁):引擎用 SQLite、同一套表結構日後可換;技術面只在進出場與風險回報層;WeKnora 與 TencentDB Agent Memory 第一版不接,待大量產業 PDF 需語義檢索時再評

- **用戶原話(原文照錄)**

  > but you know what, at the end of the day it is an investment oriented project but not a research for academic project. So I think from day 1 it should need to be leading to the objective is that the result can be easily consumed by me.
  >
  > I think if the agent state whatever 已量度 or not is stupid. As we are all investing on our latest recognition or knowledge to the market. […] it is only spining the responsibility to me and I always do accept as it is real money. And even if it is 已量度, it is the past and doesn't really mean the future right?
  >
  > The whole model or application, perhaps is not try to invention a way or a workflow that is guranteed can beat the market in the future. But at the least it can leverage the best capability of the latest front-tier LLM model with the highest intelligence, with the latest information (as it is not inside your training data) and forcing the disipline to provide the best investment advise which is not limited to the easier of data source which is Price, but also a complete analyssis of Not only from K Chart, but Market, Value-Chain, Fundmentals, then TA. And taking the correct timeframe which match with the investment principle of myself and the knowledge from the masters.

- 影響:D12 改名「投研工作台 v1」;票序 資料與版本模型 → 投資委託與分析紀律 → 股票頁 → 觀察名單 → 今日市場;①估值計算器與價值鏈人手表由 tag 還原作種子;地圖 D12 格、② 對帳單 §十二 第 18–20 條。
