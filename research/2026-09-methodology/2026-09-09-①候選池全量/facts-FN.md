# FN(Fabrinet)資料底稿——KARST-188

截止日 2026-09-09;價格日 2026-09-08(收盤 $426.19,窗口 2026-06-01→2026-09-08 跌 31.8%,相對 SPY 跌 32.8%)。
背景數字來源:`screen60_full.csv` FN 那一行(rev_ttm 4,641,097 千、op_margin 9.97%、rev_growth_yoy 35.7%、net_debt −871,042 千〔淨現金〕、ocf_ttm 256,725 千)。

本檔只列事實與出處,不下結論。

---

## 1. 為什麼跌——窗口內事件表

| 日期 | 事件 | 當日/翌日股價反應 | 出處 |
|---|---|---|---|
| 2026-08-12 | 無明確對應之 8-K/新聞可查(查不到當日具體事件) | 收盤 $571.88,單日 +8.75% | 自算(yfinance 收盤價) |
| 2026-08-17(收市後) | 公佈 FY2026 第四季及全年業績:Q4 收入 $1,315.8M(市場原估較低,超出公司自己 Q3 給的指引區間)、非 GAAP EPS $4.10(創新高);同日另發 8-K 披露與 Bank of Ayudhya 擴大信貸額至 THB 2.61B+$100M,並新提取 $75M 定期貸款 | 8/17 收盤 $598.58(+4.97%,盤中已部分反映業績消息);8/18 收盤 $482.59,單日 **−19.38%** | SEC 8-K 0001408710-26-000026(2026-08-17 申報,事件日 2026-08-11/08-17);自算股價 |
| 2026-08-18 | 業績會後市場消化:非 GAAP 每股盈利創新高,但自由現金流轉負(Q4 非 GAAP FCF −$36.9M,全年僅 $4.2M)、資本開支大增,Q1 FY27 GAAP EPS 指引 $3.39–3.54 低於上季實際 $3.83(隱含環比下降) | 收盤 $482.59,−19.38%(全年最大單日跌幅) | The Motley Fool "Why Fabrinet Stock Just Plummeted"(2026-08-18);Yahoo Finance "Fabrinet Shares Slide Despite Earnings Beat as Margins and Cash Flow Disappoint" |
| 2026-08-19 至 08-24 | 跌勢延續,無新催化劑,市場繼續消化估值(~69x 市盈率)與現金流問題 | 8/19 −5.81%、8/20 −2.13%、8/21 −1.84%、8/24 −3.56% | 自算(yfinance) |

備註:窗口內另有多宗 Form 4(高管 RSU 歸屬/扣稅賣出,非公開市場買賣),不構成價格事件,詳見第 9 項。

## 2. 最近兩季業績要點

| 季度 | 收入 | 按年增速 | 毛利率(GAAP) | 營業利潤率(GAAP) | 指引變動 | 業績日期 |
|---|---|---|---|---|---|---|
| FY2026 Q3(截至 2026-03-27) | $1,214.3M | +39.3%(對比去年同期 $871.8M) | 11.9% | 9.9% | — | 2026-05-04/05(8-K + 10-Q) |
| FY2026 Q4/全年(截至 2026-06-26) | Q4 $1,315.8M;全年 $4,641.1M | Q4 +44.6%(對比 $909.7M);全年 +35.7% | Q4 12.0%;全年 12.0% | Q4 10.2%;全年 10.0% | 發 Q1 FY27 指引:收入 $1.375–1.425B、GAAP EPS $3.39–3.54、非GAAP EPS $4.10–4.25 | 2026-08-17 |

出處:SEC 8-K exhibit 99.1(FN_PR_Q4FY26,accession 0001408710-26-000026);10-Q accession 0001408710-26-000016(Q3 數字)。

## 3. 同業有沒有一齊跌

窗口 2026-06-01→2026-09-08 收盤跌幅(yfinance 自算,首個交易日 6/1 對 9/8):

| 代號 | 公司 | 窗口跌幅 |
|---|---|---|
| FN | Fabrinet | −31.8% |
| AAOI | Applied Optoelectronics | −38.5% |
| CLS | Celestica | −22.0% |
| COHR | Coherent Corp | −15.1% |
| JBL | Jabil | −13.6% |
| LITE | Lumentum | **+9.7%** |
| SPY | 大盤對照 | +1.5% |

同業表現分歧:AAOI 跌幅比 FN 更深,CLS 也顯著跌,但 COHR、JBL 跌幅較淺,LITE 反而上升。不是全行業齊跌,光學零件/模組股(LITE、COHR)跌幅明顯小於代工/EMS 股(FN、CLS、AAOI)。

## 4. 護城河四項證據(只列證據,不評級)

- **無形資產/品牌**:查不到專利數量或品牌溢價的量化披露。10-K 未列專利組合規模。
- **轉換成本**:10-K 明言「We do not typically obtain firm purchase orders or commitments from our customers that extend beyond 13 weeks」——客戶承諾期只到 13 週,沒有長約鎖定。10-K 同時指出「Our current and prospective customers tend to evaluate our capabilities against the merits of their internal manufacturing... We believe the internal manufacturing capabilities of current and prospective customers are our primary competition.」——公司自己界定「客戶自行內部生產」是最大競爭對手。(出處:FN 10-K,accession 0001408710-26-000028,Item 1A)
- **客戶集中度**:FY2026(截至 2026-06-26)首四大客戶合計佔收入 57.4%——Cisco 19.9%、NVIDIA 16.3%、Nokia 10.7%、Amazon 10.5%。NVIDIA 佔比逐年下降:FY2024 35.1% → FY2025 27.6% → FY2026 16.3%(出處同上,10-K「Significant customers」表)。
- **成本優勢/規模**:TTM 毛利率 12.0%,與同業 EMS/代工股相近(CLS 12.0%、JBL 9.2%),遠低於零件廠 COHR(37.5%)、LITE(44.2%)、AAOI(28.9%)——顯示 FN 屬代工模式,毛利率結構性偏薄,非產品溢價護城河。但 TTM 營業利潤率 10.2%,高於 CLS(9.8%)、JBL(5.2%),遠高於 AAOI(−12.9%)——同屬代工股之中,FN 營運效率較高。(出處:yfinance,2026-09-09 抓取,TTM 數字)
- 列明同業競爭者(10-K 原文):Benchmark Electronics、Celestica、InnoLight Technology (Suzhou)、Jabil、Sanmina、Venture Corporation、Eoptolink Technology,以及客製光學/玻璃業務對手 CASTECH、Excelitas、Photop Technologies(Coherent 子公司)。

## 5. 市場現在最擔心哪一項

- **標題**:"Why Fabrinet Stock Just Plummeted"——The Motley Fool,2026-08-18。核心論點:業績本身超預期(收入、EPS 均創新高、按年增速 40–55%),但自由現金流轉負(Q4 非GAAP FCF −$36.9M)、資本開支大增,市場質疑鉅額再投資的長期回報,觸發拋售。
- **標題**:"Fabrinet Shares Slide Despite Earnings Beat as Margins and Cash Flow Disappoint"——Yahoo Finance,2026-08-18 前後。指出估值已達約 69 倍市盈率,「beat 已經不夠」,市場預期已經隱含高增長。
- 綜合:市場最擔心的是**現金流與資本開支的可持續性**,而非收入增長本身。

## 6. 下一項能改變估值的證據

| 事項 | 預期日期 | 出處 |
|---|---|---|
| Q1 FY2027 業績(季度截至 2026-09-25) | 官方未正式公佈;按過去年度規律推算約 **2026-11-02**(FY2026 Q1 於 2025-11-03 公佈,同一排期模式)——此為推算日期,非公司確認 | MarketBeat 頁面推算(2026-09 抓取) |
| Thailand Building 10(新產能)落成 | 目標 2027 年初,預計新增年化產能 $3.0–3.5B | BigGo Finance,"Fabrinet Data Center Revenue Tops 50% for First Time as Capacity Expansion Targets $14 Billion",2026-08-18(二手報導,轉述公司業績會內容,非直接引 10-K/8-K 原文) |
| 整體產能擴張目標 | 公司目標把年化收入產能由現時 $5.3B 擴至 $12.5–14B(2.4–2.6倍),含 Pinehurst 廠房改建(+$200–300M)、Navanakorn(+$200–250M)、Santa Clara(+$200–250M)、未來 Chonburi 兩座新廠(各 +$1.8–2.1B) | 同上出處 |
| 新定期貸款 $75M + 信貸額擴至 THB 2.61B+$100M,提取日期 2026-08-17,支持資本開支 | 已發生(非未來催化劑,但反映資本週期方向) | SEC 8-K accession 0001408710-26-000026 |

## 7. 資本週期(同業資本開支方向)

- FN 自身正大幅擴產(見第 6 項),不是收縮。
- 同業資本開支/新產能公告、破產或退出、新進入者:**查不到**系統性資料——本次未查得 Celestica、Jabil、Coherent、Lumentum 等同業在此窗口內的產能退出或新進入者公告。不排除存在,只是本次未查到,不可用印象填補。

## 8. 負債與現金

- 資產負債表(截至 2026-06-26,10-K/業績稿):現金及等價物 $346.7M;短期投資 $528.3M;合計流動性資產約 $875.1M。**資產負債表上未見任何計息負債項目**(負債主要是應付賬款 $1,005.8M、應付所得稅、經營租賃負債等非計息項目;利息支出全年僅 $84 千,屬微量)。
- 期後事項:2026-08-17 新提取定期貸款本金 THB 2.50B(約 $75.0M),並將與 Bank of Ayudhya 的信貸額擴大至 THB 2.61B(約 $78.3M)+$100.0M,提取期延長至 2044-08-20;貸款由母公司擔保,用於支持資本開支。(出處:SEC 8-K accession 0001408710-26-000026)
- 營運現金流:FY2026 全年(2025-06-28→2026-06-26)$256.7M(對比 FY2025 全年 $328.4M,按年下跌)。Q4 單季非GAAP自由現金流 −$36.9M;全年非GAAP自由現金流僅 $4.2M(對比 FY2025 全年 $207.3M)。(出處:8-K exhibit 99.1 現金流量表及非GAAP調節表)
- 融資租賃負債:僅小額經營租賃負債(流動 $1.2M+非流動 $2.8M),無融資租賃計息負債披露。

## 9. 內部人買賣(近六個月,2026-03-09 起)

檢視全部 18 宗 Form 4(SEC EDGAR):**未發現任何公開市場買入(transaction code "P")**。全部交易均為:
- Code S(賣出,主要為 RSU 歸屬後在市場出售,如 Archer 2026-09-03 賣 1,420 股 @$385.58、1,080 股 @$386.34);
- Code F(股份歸屬時代扣稅款而處置,非市場交易,如 Grady/Gill/Sverha/Archer 於 2026-08-25/08-26/08-13 多筆);
- Code A(限制性股份/業績股單位授予,非市場交易)。
- 另一宗 2026-05-22 Bahrami Homa 賣出 2,500 股 @$711.91(code S)。

結論(僅陳述事實):近六個月無管理層或董事在公開市場買入 FN 股份的記錄。

## 10. 技術替代爭議

**適用**——光模組代工是否會被客戶自製或矽光子(silicon photonics)/共封裝光學(CPO)取代。

- 10-K 原文已將「客戶自行內部生產」列為公司「主要競爭對手」("We believe the internal manufacturing capabilities of current and prospective customers are our primary competition")。(出處:FN 10-K,accession 0001408710-26-000028,Item 1A,2026-08-18 申報)
- **可觀察指標(用以區分「替代尚未反映」與「實際替代有限」)**:FN 前五大客戶收入集中度的逐年變化,尤其 NVIDIA 佔比——FY2024 35.1% → FY2025 27.6% → FY2026 16.3%(10-K 同一出處)。若此下降主因是客戶分散化/新客戶增加,支持「替代有限」;若主因是既有大客戶轉向自製或改用其他代工廠,則支持「替代已在發生」。本檔案只列數字,不做判斷,兩種解讀均需要進一步交叉核對客戶總收入絕對值(NVIDIA 絕對收入是否也下降,還是只是佔比被其他客戶稀釋)。
- 另一面向:公司透過 iPronics 夥伴合作擴大矽光子製造產能(2026-03-17 公佈擴大合作,目標 2026 年 6 月季度全面投產)——顯示 FN 正嘗試把矽光子/CPO 也納入自己的代工業務,而非純粹被取代。(來源:WebSearch 摘要,原始新聞標題 "Why Fabrinet (FN) Is Up 12.7% After Expanding iPronics Silicon Photonics Manufacturing Partnership",未能直接取得一手 SEC 文件佐證,列為二手來源。)

---

*本檔案由 KARST-188 資料隊(FN/AGX/CLVT 分組)製作,只負責事實蒐集,不含投資結論。*
