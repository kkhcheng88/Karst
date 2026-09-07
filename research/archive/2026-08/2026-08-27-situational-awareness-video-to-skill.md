# Video to Skill:Leopold Aschenbrenner(Situational Awareness)投資論點抽取

> 用途:Karst v1 KARST-011(Video to Skill 材料管線)第三條驗收——用一個新對象跑通「搜尋→候選(用戶剔選)→字幕抽取→代理抽取→筆記落檔」全流程。
> 對應決策:D-014(Video to Skill 管線成立)、D-017(名家組合跟隨入 v1,SA 為其中一個虛擬籃子的原型)。
> **邊界(D-008):本筆記只抽「性質」,不評價策略優劣,不代用戶判斷應否採用。**
> **本次用戶要學的是他的投資風格與論點,不是他的爆倉教訓——按用戶指示,倉位/風險一節只記他自述的原則,不評爆倉;基金近況只列在最後「事實核查待辦」一節,不下結論。**

## 一、對象與材料清單

對象:Leopold Aschenbrenner,前 OpenAI 對齊研究員,2024 年發表 165 頁文章《Situational Awareness: The Decade Ahead》,其後創立同名對沖基金 Situational Awareness LP。

候選清單(search.py 出,33 條):`research/_candidates/Situational Awareness/candidates.md`。用戶剔選結果如下。

### 已抽字幕(captions.py,語言優先 en > zh-Hant > zh-HK > yue > zh-Hans,全部命中 en)

| 影片 ID | 標題 | 性質 | 時長 | 純文字檔 |
|---|---|---|---|---|
| zdbVtZIn9IM | Leopold Aschenbrenner — 2027 AGI, China/US super-intelligence race, & the return of history(Dwarkesh Patel) | 第一身,4.5 小時全集 | 16327 秒 | `research/_captions/Situational Awareness/zdbVtZIn9IM.txt`(66166 字) |
| LT--MRXr4HE | Leopold Aschenbrenner chats with Ben Yeoh on existential risk, growth and valedictorian efficiency | 第一身,訪談 | 6478 秒 | `.../LT--MRXr4HE.txt`(118017 字) |
| J6VWnjC1xD4 | Situational Awareness: The Decade Ahead(Books in Bytes Podcast) | 第三方,論文導讀 | 1376 秒 | `.../J6VWnjC1xD4.txt`(24014 字) |
| BnZhkJuD6kU | Situational Awareness — Distilled in 9 min(NotebookLM AI Podcast) | 第三方,九分鐘摘要 | 531 秒 | `.../BnZhkJuD6kU.txt`(8840 字) |
| 04Kutj1vAiw | Forget NVIDIA — This 24-Year-Old's $4.5B Bet on AI's Real Problem(Limitless Podcast) | 第三方,講策略/13F 拆解 | 1277 秒 | `.../04Kutj1vAiw.txt`(23194 字) |
| p6Fd7ePiQqc | Situational Awareness Comes Roaring Back With Big Bet(Bloomberg Television) | 第三方,新聞片段 | 267 秒 | `.../p6Fd7ePiQqc.txt`(3820 字) |
| 1uk8eZwOdhI | Leopold Aschenbrenner says "No More Stocks!"(Limitless Podcast) | 第三方,講策略/13F 拆解 | 1648 秒 | `.../1uk8eZwOdhI.txt`(30893 字) |

7 條全部有英文自動字幕,0 條跳過(見 `research/_captions/Situational Awareness/skipped.md`,本次為空)。

### 用戶剔選時已跳過(不抽字幕)

- Dwarkesh Patel 頻道的三條節錄片(`667IffkMDmU`、`ghluOfM-Xik`、`K0Pa5oudUp4`)——內容已包含在全集 `zdbVtZIn9IM` 之內,不重複抽。
- `-tF_5ng3f5w`(論文全文朗讀,4.2 小時)——論文本身有公開全文,見下方「論文原文」一項,不必經語音轉文字。
- 所有爆倉/清算/Citadel/Texas hedge 類第三方片(例:`mJhGRim2MWY`、`CARL-MKcy3c`、`sDlH8OwFqgU`、`mlF-EENdLnA`、`loWsFH1f56E`、`AR9mx5CH3aA`、`O0pWKBZ707Y`、`RJdgh9eEZvw`、`EA9xQT2cPhE`、`UqoE1RIY91I`、`oln5SktcX9E`、`7JSog18EvJ8`、`vBM8FgHDL1A`、`zlH_HkUSGlY`、`_OwLiHmH2iw`、`x6QZoizvnwM`)——用戶明言要學的是投資論點,不要爆倉教訓,故本輪不抽。
- 中文轉述頻道(`三立財經iNEWS`、`Nick 美股咖啡館`、`DayDreamCapital`)——非第一手材料,跳過。

### 論文原文(非影片,補充材料)

`situational-awareness.ai` 有公開全文,原定用 WebFetch 直取全文摘要;實測該站對 WebFetch 一律回 403(根頁與分章節頁皆然),改用 WebSearch 取多篇對該文的第三方摘要與逐段引用互相印證。**本筆記第二節「論文原文」相關內容一律轉引自搜尋結果的第三方摘要,不是原文直讀,關鍵數字已與影片材料(尤其 zdbVtZIn9IM 逐字稿)交叉核對一致,但仍建議日後有機會時直接讀原文覆核。**

---

## 二、投資論點:算力 / 能源 / AI 供應鏈,以及時間軸判斷

### 2.1 時間軸判斷(第一身,zdbVtZIn9IM;第三方覆述,J6VWnjC1xD4、BnZhkJuD6kU)

- 核心預測:AGI 可能在 **2027 年**出現(他自己標明是「plausible」,非確定)。
- 由 AGI 到超級智能(superintelligence)的「智能爆炸」(intelligence explosion)可能發生在人類水平到遠超人類水平之間**不足一年**的時間內(J6VWnjC1xD4 轉述)。
- 這個時間軸判斷是他整套投資佈局的前提:他自述「I can see the cluster it's trained on」(zdbVtZIn9IM,行 233)——即他把算力叢集規模的推演,當成判斷 AGI 時點的主要依據,不是單純的技術直覺。

### 2.2 算力擴張論點(第一身為主,zdbVtZIn9IM 逐字稿)

他把過去約十年最大 AI 系統的訓練算力增長,按叢集規模與能耗畫出一條時間線(引自逐字稿,行 40–51、行 422):

| 年份 | 叢集規模 | 換算能耗 | 備註 |
|---|---|---|---|
| 2022 | 約 25,000 顆 A100,約 5 億美元 | 約 10 MW | GPT-4 據信完成預訓練那一批 |
| 2024 | 約 10 萬顆等級 | 約 100 MW | |
| 2026(推算) | — | **1 GW**(相當於一座大型核電廠/胡佛水壩的發電量) | |
| 2028(推算) | — | **10 GW**(比美國多數州的用電量還大) | |
| 2030(推算) | 「一萬億美元叢集」(trillion-dollar cluster) | **100 GW**,超過美國目前電力總產出的 20% | 相當於 1 億個 H100 等效算力,且只計訓練叢集,不含推理 |

他明言 2027 年前整體 AI 投資將達到約 **1 萬億美元**的量級(行 66–67)。

**與 WebSearch 取得的第三方摘要交叉核對:** 多篇轉引原文的第三方文章(ForkLog、AI Wiki 等)給出的數字與上表一致(2026 年 1 GW、2028 年 10 GW、2030 年 100 GW/約 1 萬億美元叢集),可視為互相印證,無矛盾。

### 2.3 能源是硬約束(第一身,zdbVtZIn9IM 行 55–56、289–329、415–511)

- 他明確指出:到 1 GW(2026)、尤其 10 GW(2028)規模時,**電力已經是綁死的約束**,不是算力晶片本身——現成的備用電力不夠,且電力合約多數是長期鎖定的,不能臨時加購。
- 他提出兩條路線:燒天然氣(自述美國天然氣蘊藏足以支撐多個「萬億美元級」數據中心,他點名西德州、賓夕凡尼亞西南部 Marcellus Shale 頁岩氣區)與綠能(建太陽能/風電場連傳輸線)。**他傾向兩條路線都做,但態度上更強調天然氣的現實可行性**,理由是綠能建設速度追不上算力擴張的速度。
- 「叢集要建在美國境內」是他反覆強調的立場(行 424–511):中東資金雖然充裕、也在爭取把叢集建在當地,但他認為這帶來不可逆的國安風險(見下節)。

### 2.4 AI 供應鏈主題:從「鏟子」到「能源」的輪動(第三方,04Kutj1vAiw、1uk8eZwOdhI 對他 13F 持倉變化的拆解;可信度標註見第七節)

這是本筆記最具體、最可核對的一段——三條第三方影片(04Kutj1vAiw、1uk8eZwOdhI,以及 p6Fd7ePiQqc 的新聞背景)都在拆解他公開的 13F 持倉申報,描述同一個輪動邏輯,彼此互相印證:

1. **第一階段(基金早期):「鏟子」(picks and shovels)** ——買晶片/算力基建本身,例如輝達(Nvidia)、博通(Broadcom)、台積電(TSMC)、美光(Micron)一類。
2. **第二階段(2025 下半年起,依 13F 揭露的變化):由「鏟子」轉向「能源」** ——他自述(經第三方轉述)判斷市場已經把 GPU 供應這一層的價值定價完,下一個還沒被定價的瓶頸是**電力/能源基建**,因此清倉/放空晶片股,轉為重倉電力與資料中心相關股份。
3. **第三階段(更新的 13F,依 1uk8eZwOdhI 轉述):由「鏟子」轉向「礦本身」** ——除了電力,他也直接持有 AI 實驗室的私募股權(Anthropic),邏輯被轉述為「不買鏟子,直接買礦」。

具體持倉(以下數字全部出自第三方對其 13F 申報的拆解,**屬公開監管申報的轉述,不是他本人口述,一律標「第三方轉述,待回 13F 原始申報核對」**):

- **多頭最大倉位:Bloom Energy(固態氧化物燃料電池,可繞開電網直接在數據中心現場發電)**——04Kutj1vAiw 轉述金額約 8.55–8.79 億美元,佔基金約 20%。
- 其他多頭:CoreWeave(GPU 雲/neo-cloud)、Core Scientific(CoreWeave 的能源基建供應商,私募約 10% 股權)、IREN/「Iron」(比特幣礦企轉型數據中心)、SK Hynix、SanDisk(記憶體)、光纖/光通訊相關股(轉述提及 Coherent、Lumentum 一類「optical」股,原字幕拼音有誤,**待核對確切代號**)。
- 空頭(以買入期權/put 部位為主,非直接放空股票):輝達(Nvidia)、ASML、Oracle、Infosys(IT 外包,理由是他判斷 AI coding 工具將取代低階 IT 外包業務)。
- 私募:Anthropic 股權,轉述佔基金總 AUM 約 20% 上下,由 2025 年初的較低估值(約 600 億美元)一路持有到後續多輪較高估值。

**這一整段供應鏈輪動論點的性質:是他透過公開監管文件(13F)揭露的持倉變化,由多個第三方頻道解讀出來的敘事,不是他自己在受訪時逐條講出的規則。** 引用時必須註明「經第三方轉述」,且金額、佔比、確切標的代號在落引擎前都要回 13F 原始申報核對。

### 2.5 地緣政治論點(第一身,zdbVtZIn9IM 行 346–701;第三方覆述,J6VWnjC1xD4)

- 核心立場:超級智能將帶來決定性的經濟與軍事優勢,美中兩國的算力/AI 競賽,他形容為關乎「自由世界能否勝出」的國安層級議題,不只是產業競爭。
- 他預期到 2027–2028 年左右,會出現某種形式的政府主導 AI 項目(他反覆用「Manhattan Project」類比),不一定是字面上的國有化,而更接近國防部與波音/洛克希德一類承包商的關係——由 Congress 撥款、頂尖實驗室「自願」併入同一個國家項目架構之下。
- 他反對把算力叢集建在中東:理由是一旦叢集建在地緣政治上不完全可控的地方,模型權重與算法秘密外洩到中國的風險不可逆轉(行 424–453)。

---

## 三、選股邏輯:揀什麼類型公司、為什麼

以下歸納自 2.4 節的持倉輪動論點,只記邏輯結構,具體標的與金額仍以第三方轉述、待核對為前提:

1. **沿著「AI 需要什麼」這條物理供應鏈找瓶頸,而不是買最熱門的名字。** 他的論點結構是:算力晶片 → 電力/能源 → 記憶體/儲存 → 資料中心實體(土地、機房)→ 網路連接(光纖)→ 最上游的模型公司本身(私募股權)。每個階段的邏輯是「這一層的價值有沒有被市場定價完」,定價完就轉去下一層還沒被定價的瓶頸。
2. **偏好「不性感」、非市場焦點的實體基建股,而非人盡皆知的龍頭股。** 04Kutj1vAiw 明確引述他放棄輝達(市場最熱門的名字)轉去 Bloom Energy(轉述前三個月前市場幾乎沒人聽過)的例子,論點是「簡單但有效的想法,正正因為簡單,才少人跟」。
3. **買「有牌照/有稀缺資產」的公司,而非單純買技術。** 比特幣礦企轉型數據中心的邏輯(1uk8eZwOdhI):這些公司本身的核心資產是電網接入權與土地,而電網接入權通常要數年才能拿到——買下這些公司等於直接買到稀缺的接入權,跳過申請流程。
4. **傾向直接持有終端受益者的股權(私募),不止於中游供應商。** Anthropic 私募倉位的邏輯:與其只買「鏟子」(基建供應商),不如直接買「礦」(能直接受益於 AGI 本身商業化的公司)。
5. **放空邏輯與多頭邏輯同一條主軸:判斷哪一層的敘事已經過度擁擠、要被下一層取代。** 放空輝達/ASML/Oracle 的論點被轉述為「晶片基建這條交易已經太擁擠,錢要輪動到下一層」;放空 Infosys 則是另一條獨立論點(AI coding 工具取代低階 IT 外包)。

---

## 四、倉位與風險取態(只記他自述的原則,不評爆倉)

本節按用戶指示,只記錄他自述或被轉述、關於自己倉位/風險原則的部分,不評論後續是否爆倉、不下任何結論。

- **集中度取向:高度集中,單一倉位可佔基金約五分之一。** 04Kutj1vAiw 轉述 Bloom Energy 一個倉位就佔基金約 20%,轉述者形容為「extremely concentrated, high risk, high conviction」。
- **長線持有取態,不常換手。** 1uk8eZwOdhI 中被引述(轉述,非他本人逐字):「他投資的時間框架很長,不常交易」("When I invest, it's on a very long time frame. I don't really like to trade much"——**此句出自轉述者口中,他是否認同這句話代表自己的原則需回片核對**)。
- **放空以期權部位為主,而非直接放空股票。** 1uk8eZwOdhI 明確轉述:他對輝達的空頭部位是透過 put option 構成,不是直接放空正股,轉述者形容「that is through options, that is through some leverage, it's not a direct one-to-one short」。
- **私募與公開市場持倉分開處理的取態。** p6Fd7ePiQqc(Bloomberg 新聞片段)轉述他在公開市場部位出現壓力時,「保留私募市場的持倉,退出公開市場的持倉」("he undersold all the public market investments and kept the private market investments")——這是他當時應對市場壓力時被觀察到的行為模式,不代表事先聲明的規則,**性質標「事後觀察,非自述原則」**。
- **論點與資金部署直接掛鉤,持倉變化即論點變化的訊號。** 04Kutj1vAiw 的轉述者明言:「可以把他的 13F 申報,當成即時追蹤他認為 AI 這條供應鏈瓶頸在哪裡的訊號」——這是外部觀察者對他行為模式的歸納,不是他自己講的規則。

---

## 五、可機械化的規則候選

判斷標準與 Eric 筆記、Minervini 筆記一致:一條規則能否寫成不需人為判斷、輸入相同就輸出相同的機械程序,並在歷史數據上跑得動。

**本節的性質提醒:與 Eric、Minervini 兩份筆記不同,Aschenbrenner 沒有公開講過一套完整的進出場規則或倉位管理公式——他公開的是一套「論點」(算力/能源/地緣政治的敘事)與「持倉變化」(13F 申報),不是一套明文的交易系統。所以本節的 A 級規則遠少於前兩份筆記,大部分只能到 B/C 級。**

### A. 完全可形式化——可直接寫成引擎規則或量化因子

| # | 規則 | 形式化形態 | 出處 |
|---|---|---|---|
| A1 | 13F 持倉揭露的板塊分類(算力晶片/電力能源/記憶體/資料中心/光纖網路/私募股權)按季追蹤 | 標準的「名家組合跟隨」入選因子(0/1),與 D-017 已裁的 SA/Pelosi 虛擬籃子同構——SA 本身的持倉變化就可以做成一個可回測的板塊輪動事件因子 | 04Kutj1vAiw、1uk8eZwOdhI(轉述其 13F 申報) |
| A2 | 「披露時滯規則」適用:13F 申報有法定延遲(美國通常季度結束後 45 日內申報),入庫必須用披露可得之日,不能用實際交易之日 | 直接沿用 D-017 已裁的知情時間/事件時間雙時間戳規則,SA 本身也是 D-017 條款的一個適用案例,不是新規則 | D-017(決策簿) |

### B. 部分可形式化——要補一層定義或額外數據才落得了引擎

| # | 規則 | 缺什麼 | 出處 |
|---|---|---|---|
| B1 | 算力叢集規模時間表(1GW/2026、10GW/2028、100GW/2030)作為判斷「AI 資本開支週期處於哪個階段」的宏觀因子 | 這是他個人對未來的推演,不是可驗證的既定規則;要形式化必須先把「叢集規模」轉成可觀測的公開數據(例如 Big Tech 資本開支公告、電力採購協議公告),再定義「超前/落後於他的時間表」的量化門檻 | zdbVtZIn9IM |
| B2 | 「供應鏈瓶頸輪動」邏輯(晶片→電力→記憶體→資料中心→網路→模型公司本身) | 邏輯結構清楚,但「這一層的價值有沒有被定價完」沒有客觀門檻(原始材料裡也只是轉述者的主觀判讀,不是他本人給出的量化訊號),要形式化需要自行定義每層的估值/擁擠度代理指標 | 04Kutj1vAiw、1uk8eZwOdhI(轉述) |
| B3 | 「電力是硬約束」作為篩選 AI 基建股的邏輯(優先揀能繞開電網瓶頸的公司,例如現場發電、已有電網接入權的公司) | 概念可轉成因子(例:是否持有電網接入許可、是否用現場發電技術),但需要額外的非財報數據源(電網接入許可紀錄、電力採購合約公告),自動化成本高 | zdbVtZIn9IM、1uk8eZwOdhI |
| B4 | 「AGI 時間軸(2027)作為宏觀計時器」影響資產配置節奏的假設 | 這是他個人對技術路徑的判斷,本質上是不可驗證的前瞻假設,不是可回測的技術規則;可以做成一個情境分析的輸入參數,但不應該當作既定會發生的訊號 | zdbVtZIn9IM、J6VWnjC1xD4 |

### C. 難以形式化——主觀裁量

| # | 內容 | 為什麼形式化不了 |
|---|---|---|
| C1 | 「哪一層供應鏈還沒被定價完」的判斷本身 | 這是他(或轉述者代他歸納)的主觀市場判讀,沒有給出量化的估值門檻或訊號,本質上是選股邏輯的最後一步人為判斷,與 Minervini 筆記 C1(最終人手排序)、Eric 筆記 C3(機會吸不吸引的最後一手篩選)同一性質 |
| C2 | 地緣政治/國安論點(美中 AI 競賽走向、政府是否會成立「The Project」) | 純敘事性質的宏觀判斷,沒有任何可執行的機械規則,頂多可以當成情境分析的背景假設 |
| C3 | 「這家公司有沒有稀缺資產/牌照」的具體判斷(例如比特幣礦企是否真的能轉型成有價值的數據中心資產) | 需要逐家公司做盡職審查式的資產評估,非結構化、非規則化 |

---

## 六、業績聲稱(一律「自述,未核實」)

以下全部出自第三方報導/轉述,均未經 Karst 自行核對原始監管文件或第一手財務數據,一律標「自述,未核實」或「第三方轉述,未核實」:

| 聲稱 | 出處 |
|---|---|
| 基金由 2024 年底約 2.55 億美元,6 個月內跑贏標普 500 指數約 8 倍,增長到約 20 億美元 | 04Kutj1vAiw(轉述其早期表現) |
| 一年內由約 10 億美元增長到約 55 億美元(2025→2026) | 04Kutj1vAiw |
| 進一步增長到「notional position 超過 200 億美元」,含約 137 億美元公開持倉(13F)加約 70 億美元 Anthropic 私募股權估值 | 1uk8eZwOdhI |
| 基金因 2026 年 7–8 月的 AI 股回撤觸發追加保證金,一度接近崩盤,其後把公開市場持倉全數轉移予 Citadel、僅保留私募持倉 | p6Fd7ePiQqc(Bloomberg 新聞轉述)——**此項屬「事實核查待辦」範圍,見第八節,不在此下結論** |
| 他 2027 年 AGI 的預測「目前為止都命中」(1GW/2026、10GW/2028 的算力時間表) | 04Kutj1vAiw(轉述者主觀評價,非客觀驗證) |

---

## 七、字幕質素與轉述可信度分級(引用前必須回片核對)

本次全部材料為英文自動字幕轉純文字,質素整體優於中文自動字幕(無需處理粵語辨識問題),但仍有以下已知問題:

| 位置 | 問題 |
|---|---|
| 全部 7 條檔案 | 自動字幕沒有標點與段落,人名、公司代號、專有名詞偶有拼寫變體(例如 "IREN" 轉出來是 "Iron";光纖股名稱片段模糊) |
| 04Kutj1vAiw、1uk8eZwOdhI 的具體金額與佔比 | 全部出自主持人口述對 13F 申報的解讀,不是申報文件本身;任何要入引擎的金額/佔比/持倉名稱,落引擎前必須回 SEC 13F 原始申報核對,不能只憑這兩條 podcast 的口述數字 |
| 第二節「論文原文」相關內容 | WebFetch 對 `situational-awareness.ai` 全站回 403,本筆記改用 WebSearch 取第三方摘要轉引,不是原文直讀;雖已與影片逐字稿交叉核對一致,仍建議日後直接讀原文覆核 |
| J6VWnjC1xD4、BnZhkJuD6kU | 屬第三方對論文的二次轉述/摘要,已與 WebSearch 取得的其他獨立摘要互相印證數字一致(1GW/2026、10GW/2028、100GW·1萬億美元/2030),可信度較高,但仍是轉述,不是原文 |

---

## 八、事實核查待辦(未核實)

按用戶指示:候選片標題顯示基金近期或有巨虧/清算/Citadel 卸倉,本節只列標題來源,**不下結論**;此事關乎 D-017(SA 跟隨策略,SA 為 Karst v1 名家組合之一),善後與是否影響 SA 入選因子的定義,交主線處理。

以下候選清單中出現過、但本輪按用戶指示未抽字幕的第三方標題(僅列出處,不評真偽,不代表 Karst 立場):

- 「Leopold Aschenbrenner Turned $100M Into $45B Betting on AI — Then It Almost Blew Up」(LA Times Studios,`mJhGRim2MWY`)
- 「Leopold Aschenbrenner - Inside The $45B AI Bet That Unravelled」(Valuetainment,`CARL-MKcy3c`)
- 「Situational Awareness: How a 25-Year-Old's Hedge Fund Exposed the Entire AI Bubble」(UNFTR Media,`sDlH8OwFqgU`)
- 「Leopold Was Actually Right (Citadel vs Situational Awareness)」(Limitless Podcast,`mlF-EENdLnA`)
- 「He just got LIQUIDATED ON AI - Situational Awareness Blows Up」(TechLead,`loWsFH1f56E`)
- 「How Leopold Aschenbrenner Lost $45 Billion in 3 Days」(Alex Temiz,`AR9mx5CH3aA`)
- 「Situational Awareness Leopold Aschenbrenner LIQUIDATED」(The Last Print,`O0pWKBZ707Y`)
- 「Martin Shkreli Breaks Down the Collapse of Situational Awareness」(TBPN,`RJdgh9eEZvw`)
- 「Aschenbrenner bet everything on AI — and lost」(Pivot to AI,`EA9xQT2cPhE`)
- 「The AI Hedge Fund That Blew Up」(AmplifyME,`UqoE1RIY91I`)
- 「The Biggest Trading Loss In History Just Happened」(Hamish Hodder,`oln5SktcX9E`)
- 「How He Lost $45 Billion in 3 Days?」(FinnovationZ,`7JSog18EvJ8`)
- 「How a 'Texas Hedge' Amplified the Losses at Situational Awareness」(WSJ News,`vBM8FgHDL1A`)
- 「Citadel Offloads Risk From Situational Awareness」(Bloomberg Television,`zlH_HkUSGlY`)
- 「KEN GRIFFIN'S CITADEL SELLS 80% OF SITUATIONAL AWARENESS 4X LEVERAGED BETS」(Ox Talks,`_OwLiHmH2iw`)
- 「Leopold Aschenbrenner's Situational Awareness Hit by AI Selloff」(Bloomberg Podcasts,`x6QZoizvnwM`)

另外,已抽字幕的 `p6Fd7ePiQqc`(Bloomberg Television)本身就是一則關於「基金經歷追加保證金壓力後重新部署 4 億美元私募投資」的新聞片段,內容間接印證上述標題群並非空穴來風,但本筆記按用戶指示不對「是否爆倉」「損失多少」做任何結論性描述。

**建議:** 若日後要處理 D-017 下的 SA 入選因子與跟隨策略,應該另開一輪材料抽取,針對性處理這批「危機/清算」類標題,並嘗試找 SA 基金本身或監管申報的一手資料核實,而不是繼續依賴第三方頻道的標題敘事。
