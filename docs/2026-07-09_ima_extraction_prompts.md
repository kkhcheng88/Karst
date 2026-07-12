# IMA 知識庫 agent 抽取管道 —— prompt-driven(取代人手上載 PDF)【2026-07-09】

> 起因:用戶有 Tencent IMA 知識庫訂閱,擁有者持續上載投行研報(含 flow report)。IMA 內建 agent
> (DeepSeek / GLM)可對池做 Q&A;GitHub 有 repo 可接 IMA copilot。
> 改架構:唔再人手逐份上載 PDF + 派 subagent 讀;改為**寫精準抽取 prompt**,IMA agent 做讀,回結構化數據。
> IMA agent = single-shot(冇長 harness)→ 按主題**拆多條獨立 prompt**。

## Pilot 結論(2026-07-09,Prompt A 三 model 對打)

主力 model = **DeepSeek v4 Pro**。排名 **DeepSeek > GLM 5.2(甲)> Hunyuan Hy3(乙)**。
- **DeepSeek**:忠實保留來源板塊桶 + 註明非 GICS;Z-score 全對(獨立驗證);雙口徑並列;
  net leverage 老實「未找到」;獨立「數據缺口說明」表。零杜撰。
- **GLM(甲)**:有交 Z-score,但**硬套 GICS-11 格 → 漏 Infrastructure(Z+2.11)+ 杜撰「非必需 −412」**
  (GS 只有 Consumer Goods +412 一條)。→ 犯「禁止估算」。次選,須靠 prompt 補救硬套傾向。
- **Hy3(乙)**:最保守,板塊 Z-score 全標「未找到」(有源都唔攞)→ 漏最值錢欄。
- **教訓入 prompt**:v1「11 個 GICS 板塊」係甲出錯根因 → v2 改為「以來源自身分類為準,勿硬套 GICS」。
  「忠於來源結構 vs 硬套假 schema」= 質素分水嶺,硬套會為填格而丟數/老作。

## 兩個硬設計原則(缺一即中伏)

1. **強制原文 + 出處**:每個數字後附【逐字原文引句 + 報告名 + 日期】。RAG agent 易 summarise-drift 甚至
   老作;原文係唯一驗證線,日期判新鮮度。
2. **強制「未找到」**:池中無嘅欄位寫「未找到」,禁止估算。DeepSeek/GLM 會自信老作,必加此句。

## 對應 Karst 4-原型(見 magnifier §3k)

| Prompt | 原型 | slot | 頻率 |
|---|---|---|---|
| ① 資金流/持倉 | A | (b)擁擠 +(d)大市 | 週 |
| ② 記憶體供需(主題模板) | B | (a)供給早訊 | 週/月 |
| ③ ★ 供給約束語言全市場掃描 | 跨型(早期 edge + discovery) | (a)供給早訊 | 週 |
| ④ 板塊 house view/共識 | C | (c)priced-in 參照 | 週 |

③ 最核心:把研報池變全市場供給約束掃描器,與 transcript 掃描器兩條腿(研報 channel check 有時早過電話會)。

---

## 共用參數(所有 prompt 適用;每次跑前設定;用戶 2026-07-09 三點 + 2026-07-12 一點)

0. **★ 輸出格式(2026-07-12 新增,四model對打後嘅硬要求)**:IMA 網頁版冇inline copy功能,滑鼠選取時準時唔準,每條prompt結尾必須加返以下呢句:
   > 「請將以上完整輸出匯出/導出為一個 .md(Markdown)檔案俾我下載,唔好淨係喺對話框內顯示。」
   落成.md file先貼俾Karst,唔好手動copy-paste(會斷格式/漏內容)。

1. **範圍 Scope**:目標只用機構研報(投行/大型券商:大摩/高盛/花旗/UBS/美銀/摩通/杰富瑞/
   伯恩斯坦 + 中金/中信/國信/華泰/中泰/華創 等,**含中英文機構**);排除散戶快訊/解讀/紀要/炒股類
   (風口研報/電報解讀/金牌紀要庫/紅寶書/九點特供/強勢股 等)。**區分準則 = 機構 vs 散戶,唔係中英文。**
   ★ IMA 資料夾名(用戶 2026-07-09 確認):機構外資研報 = **「外資研報🥇」** —— prompt 內【範圍】
   直接寫呢個資料夾名(Copilot 模式下 DeepSeek 跑 ③ 已成功限定此夾,出全機構乾淨結果 ~9.5/10)。
   若 flow/記憶體另有子資料夾,按實際名調整。仍保留「⑥來源分層」欄作雙保險。
2. **時間窗 Time window**:
   - 建基線(一次性):不限日期,但**優先深掃 2026-05 及之後**(語料主體集中於此),較早報告當補充。
     ★ GLM ③b 失敗教訓(2026-07-09):唔加優先,RAG 會卡喺一個舊 cluster,只撈到 3–4 月幾篇、
     漏晒 5 月後主體(6 條 vs DeepSeek 70+)。
   - 生產(週度增量):只取「報告日期或上載日期在最近 N 天」(如 7–14 天),只掃新料,避免重覆
     surface 已 priced-in 舊訊號。每次明確寫出窗口,例:「只用 2026-07-02 至 2026-07-09 的報告」。
3. **語言 Language**:報告以英文機構報告為主 + 部分中文券商報告。關鍵詞須**中英雙語** —— 英文報告
   用英文詞命中、中文報告用中文詞命中,**勿只用中文詞(會漏英文報告)**。

---

## Prompt ① 資金流 / 持倉 —— v2(2026-07-09,piloted 兩 agent 後修訂)

> v1→v2 修正(甲乙兩份 pilot 的教訓):①Z-score 須跨報告抽,勿因單報告缺欄就標未找到;
> ②加來源新鮮度警示;③加多口徑並列;④槓桿須 pin 死來源、勿合併不同投行。
> v2→v3(2026-07-12,四model對打:DeepSeek/MiniMax-M3×2/mimo-v2.5-pro):**主力model確認為
> DeepSeek**(逐項質素最高:citation最實、槓桿口徑拆得最清楚、唯一坦白披露「資料夾名係自己歸類非
> 逐字路徑」)。新增資料夾citation要求 + 匯出.md檔要求。已知殘留問題:「B&B前值」呢類冷門單一
> 數字,四個model都試過老作/錯配citation,拎到手都要人手覆核先好採納,唔可以見到有quote格式就照信。

```
你是投行研報數據抽取助手。請在知識庫中檢索「最新一期」的資金流向與持倉報告
(BofA The Flow Show、Goldman Sachs Weekly Fund Flows、GS US Equities Weekly Rundown、
JPM/大摩 定位/資金流週報,以及任何含資金流或槓桿的報告),抽取下列欄位。

【硬性要求】
1. 每個數字後面必附:①原文引句(逐字)②報告名稱 ③報告日期 ④所在資料夾名稱。
2. 知識庫找不到的欄位寫「未找到」,嚴禁估算或用常識填補。
3. 「有就填」的欄位須「跨全知識庫」找,勿因「某一份報告沒有」就標未找到 —— 例如板塊 Z-score
   若 BofA Flow Show 沒有,務必改從 Goldman Sachs Weekly Fund Flows 抽(該報告有 sector
   4-week-sum Z-score),以獨立「GS」欄並列。
4. 新鮮度警示:每個數據區塊,若其來源報告距今 >2 週,在該區塊開頭標「⚠ 來源 N 週前,較舊」。
5. 多口徑:同一指標若出現多個口徑(如全基金頭條 vs 純股票 Table 3;含/不含 options),
   兩個都列出,並註明本表採用哪一個、為何。
6. 最後列出你實際引用了哪幾份報告、各自日期、以及各自所在資料夾(判斷新鮮度+來源)。

【要抽的欄位】
A 大市層:BofA Bull&Bear Indicator(數值/訊號 Buy-Neutral-Sell/區間);
         本週各資產淨流向(股/債/現金/黃金/加密,金額)。
B 板塊層(逐個板塊):本週淨流向(金額)、%AUM、4 週流向 Z-score。
         ★ 以來源報告自身的板塊分類為準(GS 用 Commodities/Materials、Consumer Goods、
         Infrastructure、Telecom 等非標準 GICS 桶);若與 GICS 不同,保留原分類並註明對應,
         切勿硬套 GICS-11 格而丟失板塊(如 Infrastructure)或杜撰不存在的拆分。
         Z-score/%AUM 優先取 GS Weekly Fund Flows,與 BofA 金額並列成獨立欄。
C 持倉:對沖基金 gross / net leverage 及百分位;私人客戶 股/債/現金 配置%。
         ★ 槓桿須逐個 pin 死來源:註明每個數字來自哪份報告、哪個 desk、as-of 哪日、
         哪個資料夾;不同投行的槓桿口徑不可比,切勿合併成一個數;若多來源,優先取最新並標其日期。

【輸出】三個表(A/B/C),每格 = 數字(原文引句;報告名;日期;資料夾)。末尾列引用報告清單+日期+資料夾。

請將以上完整輸出匯出/導出為一個 .md(Markdown)檔案俾我下載,唔好淨係喺對話框內顯示。
```

<details><summary>v1(存檔備查)</summary>

```
你是投行研報數據抽取助手。請在知識庫中檢索「最新一期」的資金流向與持倉報告
(BofA The Flow Show、Goldman Sachs Weekly Fund Flows、GS US Equities Weekly Rundown、
以及任何含資金流的週報),抽取下列欄位。
【硬性要求】1. 每個數字後面必附:①原文引句(逐字)②報告名稱 ③報告日期。
2. 知識庫找不到的欄位寫「未找到」,嚴禁估算或用常識填補。3. 最後列出引用報告+日期。
【欄位】A 大市層:B&B(數值/訊號/區間);各資產淨流向(股/債/現金/黃金/加密)。
B 板塊層(11 GICS):本週淨流向、%AUM、4週 Z-score(有就填)。
C 持倉:HF gross/net leverage 及百分位;私人客戶 股/債/現金%。
【輸出】三表,每格=數字(原文引句;報告名;日期)。末尾列引用報告+日期。
```
</details>

## Prompt ② 記憶體供需(主題模板,換主題可複製)

```
你是半導體記憶體供需數據抽取助手。請在知識庫「外資研報🥇」資料夾內,檢索最新的記憶體/半導體研報
(UBS Memory Semis Monthly、BofA Global Memory Tech Weekly、高盛/大摩/摩通/野村 記憶體報告,
及任何含 DRAM/NAND/HBM 者),抽取:

【範圍】只用「外資研報🥇」資料夾(機構外資)。【時間】優先 2026 年 5 月及之後,較早補充。
【硬性要求】每個數字附原文引句+報告名+日期;找不到寫「未找到」,禁止估算;末尾列引用報告+日期。

【欄位】
1. 合約價 ASP:DRAM/NAND/HBM 之 QoQ 預測(本次 vs 上次,以看修訂方向)
2. 現貨價:DDR5/DDR4/NAND wafer 之 WoW/QoQ/YoY
3. 供需緊張:sufficiency ratio 或供需缺口(哪一年、多少%)
4. LTA 長約鎖量%(哪家、目標比例)
5. 庫存週數;6. Wafer starts / capex 紀律評論;7. 韓國半導體出口($bn, MoM/YoY)
8. ★約束語言:報告中「缺貨/缺口/交期拉長/on allocation/供不應求/漲價/sold out」等原文語句,逐句+對應公司
9. 事件/channel check 要點(Samsung 業績、CXMT 風險、日本行程回饋等)

【輸出】表格逐項;第 8 項單獨一節「約束語言原文清單」。末尾列引用報告+日期。
```

## Prompt ③ ★ 供給約束語言 全市場掃描(Karst 最核心)

```
【範圍/時間/語言】依上方「共用參數」設定(機構資料夾 / 時間窗 / 中英雙語)。

你是「供給約束訊號」掃描助手。在指定範圍研報中,找出被描述為供給約束/緊張的公司或子行業 ——
不限半導體,涵蓋全市場(電力電網、光通訊、先進封裝、銅鋁、變壓器、液冷、鈾核電、航太、藥品原料等)。

【關鍵詞 · 中英雙語(英文報告務必用英文詞命中,中文報告用中文詞)】
EN: "sold out" / "on allocation" / "allocated" / "lead time(s) extending / exceeding N months" /
    "supply constrained" / "supply constraint" / "tight supply" / "supply tightness" / "shortage" /
    "undersupply" / "supply deficit" / "demand exceeds supply" / "cannot meet demand" /
    "at capacity" / "fully utilized" / "utilization ~100%" / "capacity ceiling" /
    "backlog through [year]" / "booked out" / "sold ahead" / "long-term agreement" / "LTA" /
    "take-or-pay" / "prepayment" / "capacity reservation" / "price hike" / "price increase" /
    "pricing power" / "bottleneck" / "rationing"
CN: 缺貨 / 供不應求 / 供需缺口 / 結構性短缺 / 交期拉長 / 產能吃緊 / 滿產滿載 / 產能觸頂 /
    供給剛性 / 漲價提價 / 長協 / 鎖量 / 鎖價 / 預付款 / 瓶頸 / 停報停簽

【硬性要求】每條必附:①原文引句(逐字,**須完整句子**,不可只貼表格碎片/數字串)②公司/子行業
③報告名 ④日期 ⑤需求 or 供給驅動 ⑥來源分層(機構/散戶)⑦**美股標的**:該子行業的美股上市 ticker
或相關 ETF;若只有海外/私人公司,列最相關的美股受益者,或註「無直接美股標的」。
找不到就說明未見此類語言,禁止臆造。

【輸出】一張表:子行業 | 約束語句(原文完整句) | 需求/供給 | 來源分層 | 美股標的/ETF | 報告名 | 日期。
按語言強度由強到弱排(sold out / on allocation 最強;交期拉長次之;一般漲價最弱)。
另設一段「事件驅動/地緣供給衝擊」(戰爭/制裁/天災引起,如中東、霍爾木茲)與結構性超級週期分開列。
```

## Prompt ③b —— GLM 平行變體(long-tail tilt + 來源分層;與 DeepSeek ③ 求 union)

> 用途:③ 係 recall/掃描任務(DeepSeek 22868 篇只精讀 21 篇),多 model 平行掃不同報告增覆蓋。
> 此變體叫 GLM 偏 non-memory 以最大化 NEW 命中,並加來源分層。Karst 收到後與 DeepSeek ③ 去重取 union。

```
【範圍/時間/語言】依「共用參數」設定;關鍵詞用 ③ 之中英雙語表(英文報告務必用英文詞命中)。

你是「供給約束訊號」掃描助手。在指定範圍研報中,找出被描述為供給約束/緊張的公司或子行業。

★ 本次請「刻意偏向」記憶體/DRAM/半導體以外的領域(該區已另有掃描):優先深挖
電力/電網/變壓器/燃氣輪機/開關櫃、金屬與礦(銅鋁鎳鋰鈷鈾鎢鉬錫稀土)、材料化工、
工業設備、能源、醫藥原料藥、消費供應鏈、航太軍工、液冷/數據中心實體瓶頸等。

【硬性要求】每條必附:①原文引句(逐字)②公司/子行業 ③報告名 ④日期
⑤需求 or 供給驅動 ⑥★來源分層:標「機構」(投行/大型券商研報)或「散戶聚合」
(炒股快訊/紀要庫/解讀類,如風口研報/電報解讀/金牌紀要庫/紅寶書/九點特供等)。
找不到就說明未見此類語言,禁止臆造。

【輸出】一張表:子行業 | 約束語句(原文) | 需求/供給 | 來源分層 | 報告名 | 日期。
按語言強度由強到弱排(sold out/on allocation 最強;交期拉長次之;一般漲價最弱)。
```

## Prompt ④ 板塊 house view / 共識

```
你是賣方板塊觀點抽取助手。請在知識庫「外資研報🥇」資料夾內,檢索最新股票策略週報/展望
(Morgan Stanley Weekly Warmup、MS Global Exposure Guide、高盛/摩通/花旗 strategy、各行 outlook),
抽取賣方「當前共識立場」。

【範圍】只用「外資研報🥇」資料夾。【時間】優先最近 2-4 週。
【硬性要求】原文引句+報告名+日期;找不到寫「未找到」;末尾列引用清單。

【欄位】1. 11 板塊 OW/EW/UW 評級(逐個);2. 主要輪動 call(誰進誰出);
3. 指數目標 bull/base/bear(點位+P/E);4. 被點名「已擁擠/已是共識/crowded」的交易或板塊。

【輸出】表格。用途 = 量「街上已信到幾多」= priced-in 參照,非買入訊號。
```

---

## 跑法 / workflow

1. **先跑 ① 校準**:輸出貼返 Karst 主對話 → 驗 4 點(下)→ 微調格式。
2. **DeepSeek vs GLM 各跑 ① 一次**,比對抽數準確度 + 對「原文/未找到」指令服從度 → 定主力 model。
3. 格式 OK 後排程:①③每週、②每主題、④每週。
4. **終局**:GitHub↔IMA connector 把 prompt 排程自動跑 → 自動餵 Karst(人手 pull 升級為自動 push feed)。
   **先人手驗 2-3 轮確認唔老作,先接自動**,否則靜靜餵錯數。
5. **2026-07-12 確認**:主力 model = **DeepSeek**(四model對打:DeepSeek/MiniMax-M3(兩次)/
   mimo-v2.5-pro,DeepSeek全項最紮實)。**呢個係人手週度任務,agent(Claude/Karst)做唔到——
   IMA嘅wiki OpenAPI(officialskill用緊嗰個)測試證實攞唔到全文,得IMA自己個chat介面(消費端)先做
   到RAG,而呢個要用戶自己login IMA手動問**。用戶要每週開IMA、揀DeepSeek、貼Prompt①、匯出.md、
   貼返俾Karst。Prompt②③④按主題/需要唔定期跑,同樣要人手做。**已入`STATUS.md`「人手週度」表**,
   新session開波會睇到提醒。

## 貼返嚟時的驗證清單(Karst 主對話做)

- [ ] 每個數字有冇齊【原文引句 + 報告名 + 日期 + 資料夾】?
- [ ] 有冇老實標「未找到」(全部有數字反而可疑 = 可能老作)?
- [ ] 數字內部一致?(如板塊流向加總 vs 大市總流向;ASP 修訂方向 vs 現貨價方向)
- [ ] 出處報告名係真 franchise?日期夠新?
- [ ] ★ 單一冷門數字(例如「前值XX」呢類冇被主表交叉印證嘅孤證)——就算有quote格式都要额外
      核實嗰句quote嘅內容係咪真係支持嗰個數字,唔可以見到citation格式就照收(2026-07-12 四model
      對打教訓:呢類field穩定性噉老作/錯配citation)。
- [ ] 跨兩個或以上report嘅同一數字(如GS板塊flow)一致 = 高信心;單一來源孤證 = 標低信心。
- 通過先入 slot;可疑就叫 agent 重跑該項或附更多原文。

## 邊界

- IMA 管道 = 研報層(A/B/C/D 原型);**唔取代** transcript DB(defeatbeta 一手管理層原話)。兩者都餵
  早期 edge slot,互補:研報 = 分析師綜合 channel check(有時早過電話會);transcript = 管理層原話。
- 數字/目標價照舊 reject(§4 pro-cyclical);IMA 抽返嚟嘅係「事實數據 + 約束語言 + 共識立場」,唔係採納分析師 call。
