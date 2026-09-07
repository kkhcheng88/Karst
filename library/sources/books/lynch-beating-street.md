---
name: lynch-beating-street
type: book
title: Beating the Street
source_path: "C:\projects\Investment\ebooks\Fundamental Value & Growth\Peter Lynch\Beating the Street.pdf"
era: 1993 年出版,樣本集中 1992 年前後,與《One Up On Wall Street》同一世代,早於未盈利敘事股主導的年代
market: US
weights: {era: 低, horizon: 低, practised: 高, capital: 低}
weights_note: 樣本集中 1992 年前後,且明言③④類敘事股(「長線莫名其妙的小型股」)不宜提早進場,與現時未盈利敘事股主導的市場結構脫節(era 低);五隻法則假設持有到十倍兌現、以年計,持有期遠長於用戶數週至數季的框架(horizon 低);富達麥哲倫基金經理,書中逐隻股票示範實際操作紀錄(practised 高);富達麥哲倫基金規模達機構級,戰術受折減,但六類分類器與換類邏輯本身不受折減。
categories: [category-transitions, pricing-position, forced-selling, event-window-price-action]
verified_record: 審計(富達麥哲倫基金公開審計淨值紀錄)
status: distilled
distilled_on: 2026-09-07
distilled_by: Claude Opus 5
---

# 《Beating the Street》蒸餾(對照四類注框架)

> 來源檔:`lynch-beating-street.txt`(英文原版,295 頁)。頁碼依檔內 `=== PAGE n ===`。引號內為英文原文,其餘為本檔轉述。此書是《One Up》的實作版:同一套六類分法,但改為逐隻股票示範「怎樣由一個念頭做到落注」。

## 一、一句核心主張

選股是一門要靠腳走出來的手藝——由被市場冷落的行業入手,逐家翻開資產負債表與擴張計劃,每半年重新核一次故事;能不能贏,取決於做了多少功課與有沒有胃口捱住跌,不取決於預測經濟。

## 二、心得逐條

1. **翻石頭的命中率**(PAGE 136):「if you turn over 10 rocks you'll likely find one grub; if you turn over 20 rocks you'll find two」。25 條金律版本(PAGE 291):「If you study 10 companies, you'll find 1 for which the story is better than expected. If you study 50, you'll find 5.」→ 全部類;歸類:**命中率的基準線——一成**,可直接作④注的期望值計算輸入,也是 agent 原生方法(大量翻申報)唯一的量化依據。
2. **五隻法則**(PAGE 136):「The smallest investor can follow the Rule of Five... If just one of those is a 10-bagger and the other four combined go nowhere, you've still tripled your money.」→ 全組合;歸類:**與用戶「跨注分散、注內集中」數學上同一件事,可作注碼上限的參照(單一敘事一至兩隻、全倉五隻)**。
3. **價格線 vs 盈利線**(PAGE 142):「Buy shares when the stock price is at or below the earnings line, and not when the price line diverges into the danger zone, way above the earnings line.」後記(PAGE 292)補上:默克、沃爾瑪 1991–92 年正是價格線遠離盈利線,之後兩年橫行。→ ②的「定價到哪裡」;歸類:**己族「反向折現定價位置」的極簡機械版,成本近零,可先考這一個**。
4. **他自己承認的用圖方式只此一種**(PAGE 135-136):他明言不用工作站、不畫技術圖、「Trust me, Warren Buffett doesn't use this stuff」。唯一用圖的地方就是上一條的長期價格/盈利線。→ 歸類:**與用戶「TA 只在事件窗」不衝突但不重疊**——林奇用的是多年期的圖,用戶用的是季內的圖。
5. **貴市場比殘市場更難做**(PAGE 137):「I'm always more depressed by an overpriced market... the devoted stockpicker is happier when the market drops 300 points than when it rises the same amount.」→ ①;歸類:**與「被迫賣出事件庫」同向:跌市是①的原料供應**。
6. **稅務賣壓與一月效應**(PAGE 142):小型股在一月平均升 6.86%,全市場只升 1.6%;他每年秋末做功課,就是去執十一、十二月的低位名單。→ ①(季節性);歸類:**丙族「年底稅務賣出」候選,林奇給了一個具體量級與可考的窗口**。
7. **舊注優先於新注**(Principle #11,PAGE 123):「The best stock to buy may be the one you already own.」配合半年覆核(PAGE 269-270):每半年只問兩條——相對盈利是否仍便宜?公司裡有什麼令盈利上升?答案三選一:加碼/減碼/不變。→ 全組合治理;歸類:**論點卡的覆核節奏(半年)與三選一動作,直接可抄**。
8. **爛行業裡的好公司**(Principle #16,PAGE 173-176):「In business, competition is never as healthy as total domination.」共同特徵:**單位成本最低、高層慳家、避免舉債、員工有股份、找到大公司看不上的利基**。西南航空、Crown Cork & Seal、Golden West 都是。判斷慳家的土辦法:看總部(Principle #7,PAGE 80-81:辦公室愈豪華,管理層愈不肯回報股東;Principle #17,PAGE 180:年報彩色相片愈少愈好)。→ ①②;歸類:**《One Up》第 8 章的實證版,可與「零增長行業低成本領導者」候選合併**。
9. **連分析員都覺得悶就是買點**(Principle #18,PAGE 189):儲貸(S&L)行業,全國幾千家、華爾街只跟幾十家,他逐本 Thrift Digest 揭,1992 年推七隻全部升,1993 年再推八隻。他要的三件事:低於帳面值、盈利在增長、遲早被大行收購。→ ①;歸類:**「無人覆蓋 + 低於帳面值 + 併購接盤」三件套,是①最可機械化的一條劇本**。
10. **週期股的市盈率是倒轉的**(PAGE 220-221):「When the p/e ratios of cyclical companies are very low, it's usually a sign that they are at the end of a prosperous interlude.」反之高市盈率往往是週期底。→ ②;歸類:**用戶把半導體/DRAM 放進②,這條規則會令②的估值訊號完全做反,必須補週期軸**。
11. **週期股要看的是實物指標,不是價格**(PAGE 221-228):銅——他去問水喉匠銅管價;汽車——二手車價回升、以及 Chrysler 刊物裡的「units of pent-up demand」(實際銷量與趨勢線之差,1980–83 累積欠 700 萬架,之後 1984–89 超出趨勢 780 萬架)。「The most important question to ask about a cyclical is whether the company's balance sheet is strong enough to survive the next downturn.」→ ②;歸類:**可入表:被壓抑需求指標**。
12. **分部加總的隨手估值**(PAGE 223-225):把各分部盈利乘一個通用市盈率(週期股正常盈利 8–10 倍、高峰盈利 3–4 倍),常見結果是「the parts are worth more than the whole」。→ ①(隱蔽資產);歸類:**低成本、可自動化(分部盈利在 10-K 有),適合 agent 全宇宙跑一次**。
13. **零售與餐飲的可複製性跑道**(PAGE 265-266):連鎖店「has 15–20 years of fast growth ahead of it as it expands」,而且天然免受外國競爭;成敗分野是**擴張節奏**——Fuddrucker's 一年開逾 100 間垮掉,Chili's 一年 30–35 間成功。「When a company tries to open more than 100 new units a year, it's likely to run into problems.」→ ②④;歸類:**②的「增長是否仍在上調」有一個可數的物理版本:單位數增速與同店銷售**。
14. **內部人買入有例外**(Principle #15,PAGE 162):「When insiders are buying, it's a good sign—unless they happen to be New England bankers.」(該地區銀行家一路買一路破產。)→ ④①;歸類:**甲族「內部人群體買入」要加一條:行業本身面臨系統性危機時,內部人訊號失效**。
15. **不要在奏送葬曲時押翻身**(Principle #13,PAGE 133):Texas Air 蝕 3300 萬美元、New England 銀行由 40 蚊跌到 20 蚊開始止蝕、15 蚊清倉。→ ④;歸類:**時間止損以外,要有「資產負債表惡化即走」的硬止損**。
16. **週末憂慮症**(第二章,PAGE 36-41):Barron's 圓桌每年都在憂慮宏觀,1987 年最樂觀那年跌了 1000 點,1988 年最悲觀那年之後大升。Principle #4:「You can't see the future through a rearview mirror.」金律版(PAGE 291):「Nobody can predict interest rates, the future direction of the economy, or the stock market. Dismiss all such forecasts.」→ 歸類:**與用戶「不預測宏觀、押基本面」完全一致**。
17. **理髮師買認沽 = 底部**(PAGE 40):他把散戶行為當反向情緒指標。→ ③;歸類:**乙族「零售注意力」候選的另一半:注意力方向(睇好/睇淡)比注意力量級更有用**。
18. **時間與期權**(PAGE 291):「Time is on your side when you own shares of superior companies... Time is against you when you own options.」→ 庚族「④當成期權式小注」這個比喻要小心:林奇的意思是真期權會被時間殺死,而好公司的股票不會;④注若用真期權表達,時間止損與期權到期日會互相打架。
19. **賣出的唯一正當理由**(PAGE 290):「Sell a stock because the company's fundamentals deteriorate, not because the sky is falling.」以及(PAGE 289):「Often, there is no correlation between the success of a company's operations and the success of its stock over a few months or even a few years. In the long term, there is a 100 percent correlation.」→ 歸類:**第二句是對戊族全族最嚴厲的一句話:數月至數年的股價與經營無關,正是本倉想在事件窗裡撈訊號的那個尺度**。
20. **後記裡的一次自我打臉**(PAGE 292-295):1993 年他一口氣推薦週期股(鋼、能源、汽車)＋八隻儲貸,理由不是宏觀判斷,而是「the biggest bargains were in cyclicals, and that's where earnings were on the move」。→ 歸類:**方向由估值與盈利動能決定、不由宏觀劇本決定;這正是本倉「先定問題再找候選」的做法**。

## 三、與用戶框架衝突處

1. **「數月至數年,股價與經營無關」**(PAGE 289)。用戶的波段口徑(數週至數季)與 D-166 技術線題目(業績日之間的價格行為)正好落在林奇說「無關」的那一段。這不是說戊族不用做,而是說**戊族的假說必須明確聲明:它找的不是經營資訊,是持貨結構資訊**——否則林奇這句話就是對整族的先驗否定。
2. **③④仍然是拒收的。** 本書沒有推翻《One Up》的立場,反而加碼:「Long shots almost always miss the mark」、「With small companies, you're better off to wait until they turn a profit before you invest」(PAGE 290)。**用戶④的整個進場時點主張,與這句直接相反。**
3. **週期軸。** 同上一本:②裡的半導體/DRAM 若按週期股治理,低市盈率是賣訊。本書把這條講得更死,而且給出實物先行指標。
4. **持有期與注碼。** 五隻法則假設持有到十倍兌現(以年計)。用戶跨注分散＋注內集中在數學上同構,但收割窗口短得多;同一套注碼規則在短窗口下,命中率會被截斷(未及兌現就離場)。這一點要在四數(D-148)裡明寫。
5. **不衝突但要記一筆:** 林奇對宏觀、對預測、對「不做即日」的立場與用戶完全一致,甚至更極端(他連衰退都不預測)。用戶框架在這一格上有最硬的外部支持。

## 四、可入候選登記表的項目(五格齊)

| 候選 | ①聲稱 | ②服務/答哪條問題 | ③文獻 | ④延遲/成本 | ⑤證偽條件 |
|---|---|---|---|---|---|
| 價格線/盈利線背離 | 股價線遠離盈利線的成長股,其後 12 個月橫行或下跌,直至估值回到盈利線 | ②「定價到哪裡」;③頂部標記 | **中**(等同盈利收益率/估值均值回歸文獻,方向一致但幅度分歧) | 即日;免費(面板 v3 已有盈利與價格) | 背離幅度最高十分位的股票,其後 12 個月回報與最低十分位無差異 |
| 無人覆蓋 × 低於帳面值 × 併購標的 | 行業內公司數遠多於分析員覆蓋數的行業(儲貸型),其中低於帳面值而盈利增長的公司有顯著超額回報,並常被溢價收購 | ①(最機械的一條劇本) | **中至強**(低市帳率與被收購機率文獻強;「覆蓋密度」作篩的用法少) | 季度;免費(申報＋覆蓋數) | 三條件齊備的子集,24 個月回報與同市值低市帳率組無差異 |
| 被壓抑需求指標 | 實際銷量長期低於趨勢線所累積的缺口,領先該週期行業的復甦 | ②(週期軸)、④(下游需求) | **中**(耐用品替換週期文獻有;作選股訊號的少) | 季度;免費(行業銷量統計＋10-K) | 缺口最大的行業,其後 2 年銷量與股價回報與缺口最小的行業無差異 |
| 擴張節奏紅線 | 連鎖型公司年開店數超過既有店數的某比例(林奇:>100 間/年)後,同店銷售與盈利質素轉差 | ②④(增長是否仍在上調) | **弱至中**(零售擴張過度的個案文獻多,門檻值未見統一) | 季度;免費(10-Q 門店數) | 高速擴張組與穩健擴張組,其後 8 季同店銷售與回報無差異 |
| 分部加總折讓 | 各分部盈利乘通用市盈率之和顯著高於市值的公司,其後被收購或重估 | ①(隱蔽資產) | **中**(集團折讓文獻穩定存在,能否賺到錢分歧) | 年度;免費(10-K 分部披露) | 折讓最深十分位 24 個月回報與最淺十分位無差異 |
| 內部人訊號的行業失效條件 | 當行業本身面臨系統性危機時,內部人買入不再預示超額回報(林奇的新英格蘭銀行家) | ①④(甲族候選的必要修正) | **中**(內部人買入文獻強,行業條件調節的研究少) | 兩日;免費(Form 4) | 危機行業與正常行業的內部人買入組,後續 12 個月超額回報無差異(即修正沒有必要) |

## 五、值不值得深讀

**只值得抽讀五段,不值得通讀。** 第七章(方法與價格/盈利線)、第十一章(爛行業好公司)、第十三章(儲貸:無人覆蓋劇本)、第十五章(週期股與實物指標)、第二十一章＋25 條金律(半年覆核與注碼紀律)——這五段是本倉直接拿得走的。其餘一半篇幅是 1992 年 Barron's 二十一隻個股的逐隻紀錄與基金業導覽,個案已過時,通則已在上述五段講完。
