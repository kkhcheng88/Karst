---
id: KARST-185
title: 知識庫補收 Minervini 第一至三冊(縱橫天下股市的奧秘、像冠軍一樣思考和交易、趨勢交易圓桌訪談)——抽原文、按體例蒸餾、把②治理規則(趨勢模板、VCP、止蝕、注碼公式)逐條核到書內頁碼
type: task
createdAt: 2026-09-08
risk: low
model: opus
fits: D-167 知識庫;②對帳單第 27、32c、32d 條指出②治理規則書內零出處——查明是因為第一至三冊從未入庫,只入了第四冊(純心理);用戶 2026-09-08 問「the 4 books … Doesn't have any formula?」
dependsOn: []
claimedBy: minervini185-opus
deliverable: KARST-D04
---

## 工作內容

來源 PDF 在 C:\projects\Investment\ebooks\Discretionary Momentum\The Modern Snipers\Mark Minervini\(三冊:股票魔法師:縱橫天下股市的奧秘 / 股票魔法師II:像冠軍一樣思考和交易 / 股票魔法師III:趨勢交易圓桌訪談;第四冊已入庫)。照 library/raw/books/minervini-4-winner-rules.md 與 library/sources/books/minervini-4-winner-rules.md 的體例:每冊一份 raw(=== PAGE n === 標記)+ 一份 sources 蒸餾(frontmatter 含 era/horizon/practised/capital 權重、categories、verified_record)。蒸餾重點是②對帳單點名「書內零出處」的規則,逐條找出原句與頁碼:趨勢模板(價格對 150/200 日線、200 日線上升、50>150>200、距 52 週低高位置、相對強度排名)、VCP 收縮形態、止蝕(平均蝕幅、上限)、注碼公式(每注風險佔權益比例、由止蝕幅度反推倉位)、業績前後處理、賣強不賣弱、四階段(核實是價格四階段還是承諾四階段,並註 Weinstein 出處)。找不到的明寫「三冊皆無」。第三冊圓桌訪談另抽 Zanger、Ryan 的注碼與離場說法。完成後更新 library/INDEX.md、catalog.md,並在 research/2026-09-methodology/2026-09-08-②趨勢注材料全盤梳理.md 檔尾加「補記」節(不改原條文):逐條寫第 27/32c/32d 及第 20 條「大贏家回調是大市幾倍」在三冊有沒有出處、頁碼、原句。另核一件事:②對帳單頭註寫「社交原始貼文已不在倉內」是錯的,library/raw/social/markminervini/ 有 41 個月檔;補記要更正,並把社交提煉檔 markminervini.md 引用的注碼公式、5–6% 蝕幅、VCP、50 日線離場四條各找一則原貼(日期+原句)核實。

## 驗收條件

- [x] 三冊各有 raw 與 sources 兩檔,體例與第四冊一致,frontmatter 齊(另加 Zanger 訪談一組,共四組八檔)
- [x] ②對帳單檔尾補記逐條答第 20/27/32c/32d 條:有出處給頁碼與原句,無則明寫三冊皆無(第 20 條=三冊皆無,並列出書中意思相反的那兩句)
- [x] 四階段的性質核清(價格相位還是承諾階段)並註 Weinstein 是否被書引用(**兩套都存在**;價格四階段在第一冊 p.103–118,同頁明文歸功 Stan Weinstein 1988,中譯音譯作「斯坦·威斯特恩」)
- [x] 社交四條規則各有一則原貼日期與原句;對帳單頭註「貼文不在倉內」更正(41 個月檔在 `library/raw/social/markminervini/`;另更正提煉檔的 `source_path` 舊路徑,那正是誤判根源)
- [x] INDEX.md 與 catalog.md 更新;不改對帳單原條文;不 commit;含中文檔案只用 Read/Write/Edit(PDF 抽字用 Python,PYTHONUTF8=1)

## 結果

· 2026-09-08 21:40 minervini185-opus 四冊全部入庫(三冊 Minervini + 加收 Dan Zanger 2003 訪談),②對帳單點名「書內零出處」的四條規則**全部找到書內頁碼與原句**。

**新增檔案(8 個):**

| raw | 頁數 | sources |
|---|---|---|
| `library/raw/books/minervini-1-stock-market-wizard.md` | 382 | `library/sources/books/minervini-1-stock-market-wizard.md` |
| `library/raw/books/minervini-2-think-trade-like-champion.md` | 267 | `library/sources/books/minervini-2-think-trade-like-champion.md` |
| `library/raw/books/minervini-3-trading-roundtable.md` | 159(12 頁純圖表無文字層) | `library/sources/books/minervini-3-trading-roundtable.md` |
| `library/raw/books/zanger-traders-interview-2003.md` | 6 | `library/sources/books/zanger-traders-interview-2003.md` |

三冊**皆為簡體中譯**(票內寫「繁體中譯」是誤),PDF 文字層完整、無掃描圖頁、無亂碼。第二、三冊原 PDF 每頁帶盜版網站浮水印,抽字後為亂碼並黏進行尾,已程式刪去(第二冊約 3.5 萬字元),正文一字未改,已在兩檔檔頭載明。

**逐條答對帳單。第 20 條(大贏家回調是大市幾倍)——三冊皆無,而且書中最接近的一句意思相反。** 第一冊 p.265「一般的,我们应该对下跌幅度超过市场跌幅2到3倍的股票敬而远之」;第二冊 p.169「在大多数情况下,应该避免买入跌幅超过整体市场跌幅2.5倍或3倍的股票」(GoPro 個案)。這是**排除**規則不是大贏家特徵——那句話很可能是把它記反了,操作後果剛好相反。

**第 27 條(注碼公式書內零出處)——作廢,三個獨立出處。** 第二冊 **p.203**(章前引言「你的最大风险应该不超过整体股票或单笔交易的1.25%～2.5%」)、**p.204**(完整算式:25% 倉 × 10% 止蝕 = 2.5% 上限;收緊到 5% 止蝕 = 1.25%)、第三冊 **p.38、p.94**(他本人再講一次,例子數字相同)。另六條同段點名的規則亦全部有出處:5–6% 蝕幅(第一冊 p.376、第二冊 p.79,**但書內是「弱市才收緊到」不是常態**)、不向下加碼(第一冊 p.372)、VCP(第一冊 p.252–254、p.279–281)、50 日線離場(第二冊 p.230、第三冊 p.129)、業績前減倉(第二冊 p.138、第三冊 p.132,**條件是有無利潤緩衝,「減半」書內沒有**)。

**第 32c 條——前半成立,後半作廢。** 「10% 是研究用封頂值」與第一冊 p.363「止损不能超过平均收益的一半」口徑一致,更站得住;但「他全章沒有給倉位上限或持股隻數」只對 Schwager 那一章成立:第一冊 p.377(4–6 隻、上限 20 隻、最優 25%)、第三冊 p.36/p.39 都有。

**第 32d 條——Weinstein 那半作廢,CANSLIM 那半仍成立。** 第一冊 **p.103** 明文歸功 Stan Weinstein 與《在牛市和熊市中赚钱的秘密》(McGraw-Hill 1988)。

**四階段的性質:兩套都存在,不是同一件事。** ②「定位卡」要用的**價格四階段**在第一冊 p.103–118(忽略/突圍/到頂/衰敗,源頭 Weinstein);第四冊 PAGE 79–82 的是**承諾階段**(參與/學習/競爭/獲勝),心理訓練內容。第三冊全書無 Weinstein 任何譯名。

**社交四條各核一則原貼(對帳單頭註「貼文不在倉內」是事實錯誤):** `library/raw/social/markminervini/` 有 **41 個月檔**。注碼公式 **2023-06-26**(「1.25-2.50 of total equity risk. Example: 25% position size x 5% stop = 1.25% of total equity.」——他自己指着第二冊);5–6% **2026-02-15**;VCP **2023-06-29**;50 日線 **2023-06-14 / 06-16**(06-16 他自己補限定:「something I do rarely, but would adhere to for the best stocks, generally at the beginning of a new bull market」——**提煉檔把它當常規離場規則,口徑錯了**)。

**更新的檔:** `library/INDEX.md`(32→36 份,四行新增 + markminervini 一句結論更正 + 更正紀錄一條)、`library/catalog.md`(Minervini/Zanger 兩行改 done;新增 Weinstein 1988 一行,優先次序 1、pending)、`library/raw/README.md`(25→29,加浮水印說明)、`library/sources/social/markminervini.md`(`source_path` 的 scratchpad 舊路徑改為倉內實際路徑——**那個舊路徑就是誤判的根源**;另加「四之二」節列三處要改的口徑)、`research/2026-09-methodology/2026-09-08-②趨勢注材料全盤梳理.md`(檔尾加「補記」六節,**原條文一字未改**)、`CONTEXT.md`(加「價格四階段 / price stage analysis」詞條,寫明它與「承諾四階段」同名不同物)。

**沒有改變的結論:** 對帳單第 44 條「上表沒有一條是②的基準率」收了三冊 808 頁之後**仍然成立**——找到出處只證明他確實這樣講,不證明有效。三冊零基準率、零樣本定義;第一冊 p.119 的 99%/96% 與 O'Neil 的 CANSLIM 數字是同一類先驗機率陳述,應併入第 14 號舉手項處理。

## 留言

· 2026-09-08 21:42 minervini185-opus 加收一項(派工中途追加,ac 未改):同層 `Dan Zanger\Dan Zanger Trading Method.pdf`(TRADERS' 2003 年 11/12 月號,6 頁英文,有文字層)此前 catalog 只寫「引用前人」、倉內從無正本,已抽成 raw + sources 並更新 INDEX/catalog。最值錢的兩句是**「I've yet to audit up until April 2000, so you'll just have to believe me on that one.」**(那個 164,000% 有一半未經審計,他自己講)與**2000 年 10 月單日蝕 32%、熊市累計回撤約 75%**(p.6)——這正好補上對帳單第 49 條所缺的失敗數據那一半。另做了他 2003 vs 第三冊 2018 的十五年立場對照:零指標、零目標價、零追蹤止蝕三格不變,注碼與持股隻數兩格他改過(由「按資金分級」改為「按市況調節」)。

· 2026-09-08 21:44 minervini185-opus **一個查核方法上的教訓,值得記低。** 我派了兩隊 sonnet 分冊讀,兩隊都獨立報「全書無 Stan Weinstein」,理由是搜過「Weinstein / Stan / 溫斯坦」全部零命中。**兩份都是假陰性**——中譯把姓氏音譯成「**斯坦·威斯特恩**」,書名譯《在牛市和熊市中赚钱的秘密》,英文原名一次都不會出現。由我逐字核第一冊 p.103 才查出。同一隊還報「第二冊全書搜唔到 1.25%–2.5%」,而那句就在 p.203 的章前引言。**日後查中譯本的人名與術語,一律要連音譯變體一齊搜;子代理的否定結論(「全書無」)不可直接採信,要自己抽核。** 本次每冊抽核不少於五處,全部原句與頁碼由我親自對過。

· 2026-09-08 21:46 minervini185-opus **舉手一項,待用戶裁。** 補記己節列出對帳單有五處要改、兩處不改。我**只在檔尾加補記,沒有動原條文**(照 ac)。但頭註第 (b)(c) 兩項與第 27、32c、32d 四處現時是「原文寫零出處、檔尾寫有出處」並存,任何人由頭讀落去會先讀到已作廢的版本。要不要把原條文就地改掉(並在旁註明原文與改期),還是維持現時「原文 + 補記」兩層?**這關乎那份對帳單是「當日快照」還是「現行正本」,由用戶定。**

· 2026-09-08 21:47 minervini185-opus 未 commit,主 agent 收。`.kira/assumptions.jsonl` 未加條目——本次更正的是一份研究文件的事實陳述,不是冊上已登記的假設,寫不出「它若是假,哪樣東西會白做」。
