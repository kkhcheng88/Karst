# KRMN(Karman Holdings Inc.)事實查證

- 查證人:子任務 agent(KARST-188 資料蒐集)
- 查證日期:2026-09-09
- 資料截止:2026-09-09 之後公開的資料一律不用;價格截止 2026-09-08
- 本檔只負責找事實,不下投資結論

## 【資料品質警示——先講這一條】

背景資料寫「淨現金約 3000 萬美元」。經查最近一季 10-Q(季結 2026-06-30,附件一)及 8 月底的 8-K(附件二),KRMN **不是淨現金,是淨負債超過 7 億美元**,而且負債在查證窗口內又再擴大:

- 2026-06-30 資產負債表:現金及約當現金 5,174.1 萬美元;定期貸款(term note)long-term 部分 7.513 億美元 + 流動部分 561.0 萬美元 = **總定期貸款約 7.569 億美元**。(10-Q,accession 0002040127-26-000024,2026-08-11 申報)
- 2026-08-26 簽第六號信貸協議修訂,定期貸款本金再加 1 億美元,總本金增至 **8.63961 億美元**,用途是支付 Walker Precision Engineering 收購款及相關費用。(8-K,accession 0001193125-26-374378,2026-08-28 申報)
- yfinance 抓到的 totalDebt 為 8.75265 億美元、totalCash 5,174.1 萬美元(抓取日 2026-09-09)。

三個來源互相印證:KRMN 現時淨負債落在 **7 億至 8.1 億美元**這個區間(視乎抓取時點在不在 Walker 收購前後),不是淨現金 3000 萬美元。背景資料那個「淨現金」數字明顯有誤(可能是抓錯欄位或抓到舊口徑),排序候選池時要用這裡查到的數字更正,不要用原背景數字。

營運現金流 TTM 586 萬美元一項,背景數字準確(yfinance 抓到 operatingCashflow 586.1 萬美元,與 TTM 口徑相符)——但細節見第 8 項,H1 2026 單獨計其實是**負**現金流。

---

## 1. 為什麼跌——2026-06-01 至 2026-09-08 逐項事件表

窗口內收盤 40.72(9/8,與背景 40.81 略有差異,大約是資料源之間的收盤價尾差,不影響結論)。窗口報酬率以 2026-06-01 收盤 53.65 起算至 9/8 收盤 40.72,約 **-24.1%**(背景給的 -23.9% 是用不同基準日算,同一量級)。

| 日期 | 事件 | 當日/翌日股價反應 | 分類 | 出處 |
|---|---|---|---|---|
| 2026-05-28(週四) | 8-K 揭露:啟動 1,350 萬股(另有 202.5 萬股超額配售選擇權)公司股東二次發售(non-primary,公司不賣股、不收錢);公司同意 90 天內不再發新股(自 5/28 起計) | 5/28 當日 +3.68%(65.86);**5/29 翌日 -12.69%(57.50)** | 大股東/股權事件 | 8-K accession 0001193125-26-251791(2026-06-01 申報);EX-99.1/99.3 |
| 2026-05-29(週五) | 定價:1,400 萬股,發售價 $61.00/股,予售股股東的毛額約 $854,000,000;KRMN 本身不收取任何款項 | 併入上一列的翌日反應 | 大股東/股權事件 | 同上 EX-99.3;Investing.com 2026-05-29 10:01「shares fell over 8% on Friday」 |
| 2026-06-01(週一) | 發售交割完成(closing) | 當日 -6.70%(53.65) | 大股東/股權事件 | 8-K accession 0001193125-26-251791 |
| 2026-06-03 至 06-05 | 無單一 8-K 對應;06-05 當日大盤(SPY)亦跌 -2.58%,KRMN -9.10%、KTOS -7.70%、MRCY -5.56%,同業同步重跌,顯示部分為板塊/宏觀共振 | 06-03 -5.14%,06-05 -9.10% | 估值壓縮(部分同業共振) | yfinance 逐日核對(見附表) |
| 2026-06-10(週三,8-K 揭露的事件日) | 更換簽證會計師:解任 Baker Tilly US, LLP,委任 PricewaterhouseCoopers LLP,無意見分歧,附帶提及先前已披露的內控重大缺失(非新增) | 6/10 當日 -5.17%(在 8-K 申報前一日,可能是巧合非因果);**6/11 申報日反而 +8.09%** | 治理事件(市場未讀作負面) | 8-K accession 0001193125-26-267832(2026-06-11 申報);EX-16.1 |
| 2026-06-11 至 08-05 | 無重大 8-K;股價在 $44–$62 區間反覆(見附表逐日數字),07-13(-9.76%)、07-29(-7.97%)兩日跌幅最大。07-29 對應當日美股大盤本身重挫(道指 -2.19%,標普 -1.52%,因 Fed 按兵不動、市場憂慮通脹),KTOS(-9.79%)、MRCY(-9.27%)同日同步重跌,屬高 beta 成長股對宏觀消息的放大反應,非 KRMN 個股消息。07-13 未查到對應的個股或同業消息 | 見上 | 估值壓縮/宏觀(07-29 有macro 佐證,07-13 查不到) | yfinance;CNBC 2026-07-29 市場報導(綜合搜尋結果轉述,非直接引用全文) |
| 2026-07-14 | KRMN 納入標普中型股 400 指數(取代 Chart Industries) | 07-14 +1.55%,07-15 +6.44%(正面事件,非跌因) | 指數事件(利好) | WebSearch 綜合結果(來源含 SqueezeReport、MarketBeat 系列快訊,未逐一核對原文,信度中等) |
| 2026-08-06(週四收市後) | Q2 2026 業績:收入 $182.06M(+58.2% 總增速,+24.4% 有機),經調整 EBITDA $54.58M(+54.7%),**全年指引上調**(收入 $730–745M,經調整 EBITDA $215.0–222.5M);CEO 提到在談判三項合計潛在價值逾 $1B 的新長約 | 8/6 當日 +0.04%,**8/7 翌日 +5.60%,續兩日再 +6.75%(8/10)**——業績本身是利多,股價當週先漲 | 業績/指引(利多) | 8-K accession 0002040127-26-000018;EX-99.1 |
| 2026-08-07(翌日) | 三間分析行同步**調低**目標價但維持買入評級:Needham $125→$80、Evercore ISI $100→$80(以上為 8/7);Truist $118→$85(8/14)。搜尋結果未見任何一份報告明確寫出調低理由的原文,只能從時間點與後續 J Capital 報告的估值論述推斷是「估值太貴,即使業績超預期也追不上原目標價的隱含倍數」 | 目標價下調與股價次週(8/11 起)轉弱同步,但非單一因可完全解釋(股價 8/6–8/14 其實仍在高位 $55–62) | 分析員動作 | WebSearch 綜合結果(MarketBeat/TipRanks the-fly 快訊式標題,未取得完整報告全文,信度中等) |
| 2026-08-18 至 08-25 | 無對應 8-K;連續陰跌(-3.80%、-2.07%、-6.60%、-1.77%、-3.80%、-4.22%),08-20 當日 KTOS -7.23%、MRCY -6.93% 同步重跌,同業共振明顯;08-18 MRCY 單日 -7.37% 但 KRMN 只 -3.80%、KTOS 更只 -2.05%,顯示 08-18 主要是 MRCY 個股事件,非板塊 | 見上 | 估值壓縮(同業共振為主) | yfinance |
| 2026-08-26 | 簽第六號信貸協議修訂,定期貸款加碼 $100M 至總本金 $863,961,000,用於資助 Walker Precision Engineering 收購 | 併入 08-27/08-28 反應 | 併購/融資事件 | 8-K accession 0001193125-26-374378 |
| 2026-08-27(週四) | CFO 交接公告:Mike Willis 卸任、Chris Boynton(前 Battelle EVP/CFO、前 Raytheon 飛彈與防務部門 CFO)接任,生效日 2026-09-14 | 8/27 當日 -1.98%,**8/28 -3.90%,08/31 再重挫 -9.04%(收 $41.45,52 週新低)** | 管理層變動 | 8-K accession 0001193125-26-369561;Seeking Alpha 2026-08-31 快訊「declines 9% to new 52-week low」;Motley Fool 2026-08-28/09-04 兩篇週報 |
| 2026-08-28(週五) | 完成收購 Walker Precision Engineering,代價約 $95M(£70M),同日申報前述信貸修訂 8-K | 見上 | 併購事件 | 8-K accession 0001193125-26-374378 |
| 2026-09-02(週三,約下午 3:58 ET 發佈) | 放空機構 **J Capital Research**(Substack「The Equity Dispatch」)發表看空報告,核心論點:(a)營收與帳面盈利增長但「不產生正營運現金流」;(b)前瞻 P/E 約 70 倍、EV/經調整 EBITDA 約 28 倍,較標普 500 溢價 70%、較航太國防同業溢價 50%;(c)合約資產(contract assets)快速膨脹造成「負現金拖累」,令經調整 EBITDA「不是現金流的好代理指標」;(d)頻繁舉債併購,且屢次披露為「不重大」但金額不小;(e)內控仍然薄弱,對國防產品的會計複雜度增添疑慮 | 9/2 當日 -1.63%(Investing.com 標題稱 "falls 2.1%",與收盤跌幅小幅不一致,可能是報告發佈後盤中反應與收盤價差異);**當週(9/1–9/4)累計跌 11%** | 估值/會計質疑(放空報告) | jcapitalresearch.substack.com/p/karman-holdings-inc-krmn(2026-09-02);Investing.com「Karman Holdings stock falls after short-seller questions cash flow」(2026-09-02 15:58);Motley Fool「why-karman-holdings-stock-wilting」(2026-09-04) |
| 2026-09-08 | 收 $40.72(本檔口徑,背景給 $40.81,兩者差異在容許誤差內) | — | — | yfinance |

**小結判斷(僅陳述已查證的事實,不下投資結論)**:窗口內至少三個獨立、可歸因的個股/公司事件——(1)5/29–6/1 的 $854M 大股東二次發售、(2)8/27–8/31 的 CFO 交接、(3)9/2 的 J Capital 看空報告——每一個發生後股價都有明顯跌幅;另外有多個交易日(06-05、07-29、08-20、08-24)KTOS/MRCY 同步重跌,顯示同一批「高估值、高 beta」中小型國防成長股存在共同的板塊/宏觀壓縮力道。07-13、08-18、08-25 等個別交易日的下跌原因查不到對應消息。篩選腳本標「混合」殺法與這裡查到的證據吻合:既有板塊共振,亦有個股獨有的三個負面事件疊加。

---

## 2. 最近兩季業績要點

| 項目 | Q1 2026(季結 2026-03-31) | Q2 2026(季結 2026-06-30) |
|---|---|---|
| 業績發佈日 | 2026-05-12(8-K,accession 0001193125-26-219495) | 2026-08-06(8-K,accession 0002040127-26-000018) |
| 10-Q 申報日 | 2026-05-14(accession 0001193125-26-222116) | 2026-08-11(accession 0002040127-26-000024) |
| 收入 | $151.2M | $182.063M |
| 收入按年增速(總) | +51.0%(去年同期 $100.1M) | +58.2%(去年同期 $115.097M) |
| 有機增長 | **公司未單獨披露**(新聞稿全文搜尋「organic」一字,零命中) | +24.4%(公司明確披露) |
| 毛利率 | 42.2%($63.9M/$151.2M) | 42.9%($78.234M/$182.063M),去年同期 40.8% |
| 營業利潤/利潤率 | $21.5M/14.2% | $34.829M/19.1% |
| 淨利潤 | $7.8M(去年同期 -$4.8M) | $14.032M(去年同期 $6.807M,+106.1%) |
| 經調整 EBITDA/利潤率 | $44.8M/29.6%(+47.7% 按年) | $54.580M/30.0%(+54.7% 按年) |
| 全年指引(當次發佈時) | 收入 $720–735M;經調整 EBITDA $208.5–219.5M(較之前上調) | 收入 $730–745M;經調整 EBITDA $215.0–222.5M(**再度上調**) |
| 併購對增長的貢獻 | 2026 年 1 月完成收購 Seemann Composites 及 MSC,新設 Maritime Defense Systems 分部,該分部 Q1 貢獻收入 $26.4M(佔當季總收入 $151.2M 的 17.5%);若簡單扣除此新分部,增速降至約 25%(**此為本檔用披露數字反推的估算,非公司官方「有機增長」數字**,公司 Q1 未給出官方口徑) | 公司明確表示總增速 58.2% 中「有機增長 24.4%」,差額主要來自 Seemann 併購(Maritime Defense Systems 分部) |
| 管理層評論 | CEO Jon Rambeau:「achieved another quarter of record financial results」,積壓訂單逾 $10 億,按年增逾 60% | CEO Jon Rambeau:「Our record $1.3 billion backlog provides exceptionally strong visibility」,並提到正洽談三項合計潛在價值逾 $1B 的新長約 |

**核實結論**:兩季收入增速有相當部分來自併購(Q1 尤其明顯,新分部佔約六分之一收入;Q2 官方明確拆出有機 24.4% vs 總 58.2%,即約 34 個百分點來自併購/新分部),背景資料提醒「留意併購拉動增長」屬實,而且兩季指引都是**上調**,非下調或維持。

---

## 3. 同業有沒有一齊跌(yfinance 實測,2026-06-01 收盤至 2026-09-08 收盤)

| 代號 | 公司 | 窗口報酬率 |
|---|---|---|
| KRMN | Karman Holdings | -24.1% |
| KTOS | Kratos Defense | -23.4% |
| MRCY | Mercury Systems | -23.6% |
| MOG-A | Moog Inc | **+1.4%** |
| TDG | TransDigm | -7.5% |
| HEI | Heico | -4.5% |
| LOAR | Loar Holdings(近期 IPO 利基航太零件,可比性最高) | **+9.5%** |
| SPY | 大盤 | +1.4% |
| ITA | 航太國防 ETF | -2.2% |
| XAR | 航太國防 ETF(另一隻) | -9.1% |

**核實結論**:不是整個航太國防板塊一齊跌——大盤 ETF(ITA、XAR)只跌 2–9%,大型多元化同業(MOG-A 反升、TDG/HEI 只跌個位數)表現相對穩定。真正跟 KRMN 同步重跌(-23% 至 -24%)的,是另外兩隻同屬「高估值、高成長敘事」的中小型國防股 KTOS 和 MRCY——這三隻在多個交易日(06-05、07-29、08-20)同日同步大跌,顯示存在一個共同的「高倍數國防成長股」板塊壓縮因子。但 KRMN 最直接的可比同業 LOAR(同樣是近年 IPO 的利基零件供應商)在同一窗口反而**上升 9.5%**,與 KRMN 明顯背馳——這說明 KRMN 的跌幅不能完全用「同類股票一齊跌」解釋,個股層面(二次發售、CFO 變動、放空報告)的疊加是跌幅特別深的部分原因。

---

## 4. 護城河四項證據(只列證據,不評級)

出處:FY2025 10-K(accession 0002040127-26-000014,2026-04-03 申報,krmn-20251231.htm)

- **無形資產/專利**:「As of December 31, 2025, we own 23 issued patents, which will expire between July 2027 and June 2044」,另有 7 項專利申請待審。公司自述擁有三類 IP:設計 IP、專利化的 proprietary IP(energetics/safe-and-arm 相關組件)、製程 IP。
- **客戶集中度**:「Our three largest customers accounted for approximately 51.5% of revenue during the year ended December 31, 2025.」單一客戶佔比未單獨披露。同時披露「no single program out of the more than 130 active programs...accounted for more than 12% of our revenue, on average」——即個別客戶集中度高,但個別合約/計劃集中度分散。「A material portion of our revenue is derived from direct and indirect defense contracts with the U.S. military」(具體百分比查不到)。
- **單一/唯一供應商地位(轉換成本相關)**:「We often occupy a single or sole source position on key strategic missile and space programs.」10-K 風險因子亦寫:「the lengthy and expensive OEM certification processes associated with our products could prevent efficient replacement of a supplier」,以及「it is unlikely that a customer would pursue re-qualification, given its typically lengthy and costly nature」。
- **認證壁壘**:10-K 提到 OEM 認證流程「lengthy and expensive」構成轉換障礙,但**沒有**具體點名 AS9100、ITAR 等特定認證名稱(可能在其他章節,本次未查到)。
- **合約年期**:「The life of these programs can often exceed 20 years with lengthy production lifecycles」;「Fostering enduring partnerships of more than 15 years, in many cases」。具體最短合約年期條款查不到。
- **毛利率相對同業**:KRMN 經調整 EBITDA 利潤率 FY2025 為 30.8%,Q2 2026 毛利率 42.9%。與同業(KTOS、MRCY、LOAR 等)逐一比較毛利率——**本次未查**,時間所限,留待日後補查。
- **成本優勢/市佔率**:10-K 自述行業「characterized by a large, fragmented supplier base of piece part and subsystems providers, with few integrated system providers」,即 KRMN 定位為少數「整合系統供應商」之一,但沒有給出具體市佔率數字——**查不到**具體市佔率百分比。

---

## 5. 市場現在最擔心哪一項

1. **現金流轉換率/會計質量**(最主要):J Capital Research,2026-09-02,Substack「The Equity Dispatch」,標題文章即為 KRMN 專題。核心引句:「books high revenue growth and consistent, albeit modest, profitability without generating positive operating cash flows」;「Ongoing weak internal controls at Karman, given difficult accounting challenges for defense products, increase our concern. If we were investors, we would want to make sure acquisitions and contract payments had been audited with strong internal controls.」
2. **估值過高**:同一份 J Capital 報告——前瞻 P/E 約 70 倍(2026 年共識預測),EV/經調整 EBITDA 約 28 倍(以指引上限 $218.8M 經調整 EBITDA 計),較標普 500 溢價 70%、較航太國防板塊溢價 50%。分析員雖然多數維持買入評級,但 8/7–8/14 期間 Needham、Evercore ISI、Truist 三間都調低目標價(分別 $125→$80、$100→$80、$118→$85),時間點正好在業績超預期公佈之後,方向與「估值太貴」的論述一致(報告原文未查到,推斷基礎見第 1 項事件表)。
3. **管理層/治理變動**:CFO Mike Willis 於 2026-08-27 公告卸任(生效 2026-09-14),市場當週股價明顯走弱,媒體(Motley Fool、Seeking Alpha)均將此列為股價轉弱的直接催化劑之一。
4. **併購頻繁且屢次披露為「不重大」**:J Capital 報告明確質疑此點,認為屢次舉債收購但個別交易常被歸類為「not material」,削弱資訊透明度。

未查到具體提及「lock-up 解禁拋壓」或「客戶/計劃集中度」作為市場主要擔憂的公開評論——已查證的二次發售(6/1)本身不附帶新的個人鎖定期解禁(見第 6、9 項),因此「lock-up 解禁」這個角度目前沒有找到直接證據支持是近期股價擔憂點。

---

## 6. 下一項能改變估值的證據

| 項目 | 預期日期 | 出處 |
|---|---|---|
| 下次業績日(Q3 2026) | 2026-11-05(盤後,yfinance earnings_dates)或 2026-11-06(yfinance calendar 兩個口徑略有差異,均指向 11 月首週) | yfinance `get_earnings_dates()` / `.calendar`,抓取日 2026-09-09 |
| Walker Precision Engineering 收購整合成效首度反映 | 收購已於 2026-08-28 完成,預期在 Q3/Q4 2026 業績中首次完整反映其收入貢獻 | 8-K accession 0001193125-26-374378 |
| CEO 提及在談的三項長約(合計潛在價值逾 $1B) | 未有明確日期,Q2 業績會提及「negotiations」,屬未定時程的潛在催化劑 | 8-K accession 0002040127-26-000018 EX-99.1 |
| CFO 交接完成 | 2026-09-14(Chris Boynton 正式接任生效日) | 8-K accession 0001193125-26-369561 |
| 公司層面 90 天禁售期(不得增發新股) | 已於 2026-08-26 前後屆滿(自 2026-05-28 起計 90 天) | 8-K accession 0001193125-26-251791 EX-1.1;本檔已查:此條款只約束公司本身增發,**沒有查到**另有一條專門約束售股股東(包括高管/Trive Capital)個人持股的鎖定期條款,故無法標示「個人持股鎖定期解禁日」 |
| 政府財政年度/預算相關 | 美國聯邦 2027 財政年度於 2026-10-01 開始,持續撥款決議(CR)/政府停擺風險屬每年例行的宏觀不確定因素,對國防承包商有潛在影響——**具體 2026 年這次的撥款進度查不到**(本次查證未觸及國會撥款時間表) | 未查(僅屬常識性宏觀日期,非個別新聞來源) |

---

## 7. 資本週期(同業資本是否在退出)

**資料不足,只能提供片段證據,不能給出全面判斷:**

- KRMN 自身 10-K 沒有揭露具體 2026 年資本開支計劃或新廠公告,只有概括語句:「We continue to evaluate opportunities to support anticipated growth and add flexible and dedicated capacity to support emerging and mature production programs.」(FY2025 10-K)
- 電子元件/半導體供應仍然緊張,10-K 風險因子寫:「The market for electronic components has been and currently still is experiencing increased demand and a global shortage of semiconductors, creating substantial uncertainty regarding our suppliers' ongoing timely delivery.」——顯示上游供應鏈(而非 KRMN 直接同業)仍處於產能偏緊狀態。
- 搜尋中找到一則相關但非直接同業的參考:Howmet Aerospace(航太零件供應商,非 KRMN 直接同業但同屬航太精密零件供應鏈)2026 年財報提及正考慮因應國防需求增長而加開產能(路透社報導,具體日期在本次搜尋結果中顯示不完整,信度中等,建議日後另行核實原文日期)。
- KRMN 本身持續透過收購擴張(Seemann/MSC 2026 年 1 月、Walker Precision Engineering 2026 年 8 月),屬於「以併購代替自建產能」的資本配置模式,但這是 KRMN 自己的行為,不能代表「同業資本在退出」。
- **同業(KTOS、MRCY、Moog、TransDigm、Heico、LOAR)各自的資本開支方向、新產能公告、有沒有破產或退出案例——本次完全沒有查,屬於明顯缺口**,如需要應另開查證。

---

## 8. 負債與現金(交叉核對 10-Q/8-K,不只用 yfinance TTM)

**現金**(2026-06-30,10-Q accession 0002040127-26-000024):
- 現金及約當現金:$51,741 千(即 $51.741M)

**有息負債**:
- 2026-06-30 資產負債表:定期貸款(term note)long-term 淨額 $751,327 千 + 流動部分 $5,610 千 = **$756,937 千**(約 $756.9M,10-Q 數字)
- 2026-08-26 簽第六號信貸協議修訂(Citibank, N.A. 為 Administrative Agent/Collateral Agent):定期貸款本金增加 $100,000,000,**總原始本金增至 $863,961,000**,用途明確為資助 Walker Precision Engineering 收購及相關費用(8-K accession 0001193125-26-374378)
- yfinance 抓到的 totalDebt(抓取日 2026-09-09):$875,265,024——與上面兩個 SEC 來源同一量級,細微差額可能來自融資租賃或其他小額負債項目未在本次查證中逐項拆解

**租賃負債**(2026-06-30,10-Q):
- 流動部分營運租賃負債:$2,464 千
- 非流動部分營運租賃負債:$13,725 千
- 合計約 $16.189M

**近四季營運現金流(交叉核對)**:
- H1 2026(六個月至 2026-06-30):**淨現金流出(使用)$2,975 千**(即 -$2.975M)
- H1 2025(同期比較):淨現金流出 $30,955 千(即 -$30.955M)——按年已大幅改善但仍是負數
- 主要現金消耗項目(H1 2026):應收帳款增加 $25,455 千、合約資產增加 $24,851 千、存貨增加 $4,651 千,三項合計消耗約 $54.96M 營運資金
- yfinance operatingCashflow(TTM,抓取日 2026-09-09):$5,861 千——與背景給的 $586 萬一致。將 H1 2026 的 -$2.975M 與 TTM +$5.861M 對照,可反推 H2 2025(即 2025-07-01 至 2025-12-31)營運現金流約為正 $8.8M 左右(本檔推算,非公司直接披露的分季數字)。**即 KRMN 的營運現金流有明顯季節性/成長期特徵:上半年因應收帳款與合約資產隨收入增長而擴大,現金流轉負;下半年隨收款週期改善而回正**——這與 J Capital 報告質疑「經調整 EBITDA 不是現金流的好代理指標」的論點方向一致,但本檔查到的是「週期性現金消耗」而非會計舞弊證據,兩者要分清楚。

**結論**:KRMN 現時是淨負債公司(淨負債落在約 $7 億至 $8.1 億美元的區間,視乎以哪個時點的數字計算),不是背景資料所講的「淨現金約 3000 萬美元」。這一點請採用本檔數字更正候選池排序用的背景數字。

---

## 9. 內部人買賣(2026-03-09 至 2026-09-09)

透過 SEC EDGAR Form 4 清單(CIK 0002040127)查證,窗口內(含窗口前追溯至 2026-03-09)**唯一一批 Form 4 是 2026-05-26 申報的 11 份**,涵蓋以下報告人(職務見括號):

- Jon Rambeau(CEO)、Michael Willis(CFO,即後來 8/27 公告卸任者)、Stephanie Sawhill、Mary D Petryszyn、John Hamilton、David Stinnett、Matthew Alty、Brian Raduenz 等

**逐一核實交易性質**:抽查其中 Jon Rambeau 及 Michael Willis 兩份的 ownership.xml,交易代碼均為 **"A"(Award,即股份獎勵/歸屬授予)**,價格 $0(RSU 授予,非公開市場買賣),事件日期 2026-05-21,屬公司長期激勵計劃例行 RSU 授予,**不是**公開市場買入,也不是賣出。

**核心結論**:
- 2026-03-09 至 2026-09-09 這半年窗口內,**沒有查到任何內部人在公開市場買入**(不計期權行使/稅務代扣)的 Form 4 紀錄。
- **也沒有查到任何內部人透過 Form 4 在公開市場賣出**的紀錄(2026-05-26 之後至查證日為止,EDGAR 未見新的 Form 4 申報)。
- 2026-06-01 完成的 $854,000,000 二次發售(第 1 項已述),SEC 文件只稱「Selling Stockholders」/「certain of Karman's existing stockholders」,**沒有在本次可讀取到的 8-K 正文、新聞稿(EX-99.1/99.2/99.3)中點名賣方身份**,Schedule II(理應列明賣方名單)本次未能透過 WebFetch 取得完整內容。
- 用 EDGAR 公司名稱搜尋「Trive」,找到多個 Trive Capital 系基金實體(如 Trive Capital Fund IV LP、Fund V LP 等,CIK 分別列出),但**沒有找到任何一個 Trive 系實體對 KRMN 申報過 Form 4、SC 13D 或 SC 13G**(EDGAR 搜尋 CIK 0002040127 底下的 SC 13 類型申報,結果是空的)。這代表本次查證**未能用 SEC 一手文件直接證實** Trive Capital 是這次 6/1 二次發售的賣方——只有新聞/公開資料(PE Professional 網站「Trive Soars to Exit with IPO of Karman」、Trive Capital 官網自述為 Karman 的 2021 年創辦股東、R.W. Baird 交易紀錄頁列出 IPO/2025 年 7 月 $1.2B follow-on/2026 年 6 月本次發售等一系列「follow-on offering」)間接指向 Trive 是持續減持的主要股東,**但不是 SEC 一手申報文件直接證實**,查證信度中等,務必註明來源限制。
- 另查到 KRMN 過去一年至少有三次同類型「existing stockholders」二次發售:IPO(2025-02)、follow-on(2025-07,$1.2B,21.1M+3.15M股 @ $49/股)、以及本次(2026-06,$854M,14M股 @ $61/股),顯示賣方(無論是否為 Trive)持續透過公開市場減持,屬於一個重複模式,但**個別身份查不到**。

---

## 10. 有沒有「技術替代」爭議

**不適用。** 本次查證(FY2025 10-K 風險因子全文搜尋 + 一般搜尋)沒有找到任何關於「可重複使用火箭降低消耗性零件需求」「積層製造(3D 打印)取代傳統精密機械加工」或其他技術替代/過時風險的具體爭議或分析員評論。10-K 唯一相關語句只涉及公司自身要適應 AI 技術以維持營運效率,不是外部技術替代對其業務模式的威脅論述。J Capital 的看空論點集中在會計/現金流/估值,不涉及技術替代。若日後市場出現這類爭議,建議另開查證追蹤。

---

## 附:窗口內 KRMN 逐日收盤與按日報酬率(yfinance, 2026-05-20 至 2026-09-08)

已用於第 1、3 項的計算依據,原始數據存於子任務暫存目錄的 `yf_krmn2.py`/`yf_krmn3.py` 輸出(未落入本倉,如需重跑可用相同腳本,資料源 yfinance)。重大單日跌幅(≤-5%)日期:05-26(-5.37%)、05-29(-12.69%)、06-01(-6.70%)、06-03(-5.14%)、06-05(-9.10%)、06-10(-5.17%)、06-22(-5.30%)、07-06(-5.34%)、07-13(-9.76%)、07-29(-7.97%)、08-20(-6.60%)、08-31(-9.04%)。
