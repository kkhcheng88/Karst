# -*- coding: utf-8 -*-
"""把第二批核證回來的事件併入 events_spec.json(一次性,保留作追溯)。"""
import json
import pathlib

p = pathlib.Path(__file__).resolve().parent / "events_spec.json"
s = json.loads(p.read_text(encoding="utf-8"))

new = [
{
 "event_id": "E09", "name": "2014-11 石油輸出國組織不減產殺頁岩油與油服",
 "narrative": "石油輸出國組織決定維持產量、沙特刻意放棄護價要打爆美國頁岩,市場怕油價無底,高槓桿的開採商與被斬資本開支的油服一齊完蛋。",
 "shock_start": "2014-11-26", "news_shock_end": "2015-01-30", "end_date_sourced": False,
 "basket_definition": "當時報導點名的頁岩開採商與油服",
 "basket_source": "Business Insider / CNBC-Reuters / USA Today / CSM 2014-11-28 逐隻點名",
 "tickers": ["XOM", "CVX", "COP", "MRO", "OXY", "APC", "LINE", "WLL", "OAS", "KOG", "RIG", "HAL"],
 "tickers_headline_only": ["DNR"],
 "sic2_basket": ["13"],
 "sources": [
  {"outlet": "Business Insider", "date": "2014-11-28", "url": "https://www.businessinsider.com/oil-company-stocks-tumble-november-28-2014-11"},
  {"outlet": "CNBC / Reuters", "date": "2014-11-28", "url": "https://www.cnbc.com/2014/11/28/oil-stocks-and-oil-related-currencies-slammed-by-opec-move.html"},
  {"outlet": "USA Today", "date": "2014-11-28", "url": "https://www.usatoday.com/story/money/markets/2014/11/28/stocks-friday/19608677/"},
  {"outlet": "Christian Science Monitor / Reuters", "date": "2014-11-28", "url": "https://www.csmonitor.com/Environment/Latest-News-Wires/2014/1128/Crude-falls-below-68-oil-sector-stocks-plunge"}],
 "in_main_sample": True,
 "notes": "會議在感恩節 11-27(美股休市),起日取對上一個收市 11-26。結束日無出處,是推斷(油價要到 2015 年 1 月中才見底),故本宗的「衝擊結束日」口徑不可信,只看「衝擊低點」口徑。油服只核到 HAL、RIG 兩隻,SLB/BHI 當日報導未點名故不入。APC/LINE/WLL/KOG 其後被收購或破產,是本宗倖存者缺口。"
},
{
 "event_id": "E10", "name": "2016-11 特朗普當選殺太陽能與醫院",
 "narrative": "特朗普意外當選,市場怕太陽能的三成聯邦投資稅務抵免被砍,同時怕平價醫療法案被廢除令醫院失去投保病人、壞帳回升。",
 "shock_start": "2016-11-08", "news_shock_end": "2016-12-09", "end_date_sourced": False,
 "basket_definition": "當時報導點名的太陽能與醫院/管理式醫療",
 "basket_source": "Motley Fool / IBD / Business Insider / ThinkAdvisor 2016-11-09 至 11-10 逐隻點名",
 "tickers": ["FSLR", "SPWR", "CSIQ", "SEDG", "RUN", "THC", "CYH", "HCA", "LPNT", "UHS", "CNC", "MOH", "WCG", "SCTY"],
 "tickers_headline_only": [],
 "sic2_basket": ["36", "80"],
 "sources": [
  {"outlet": "Motley Fool", "date": "2016-11-09", "url": "https://www.fool.com/investing/2016/11/09/why-solar-stocks-plunged-today.aspx"},
  {"outlet": "Investors Business Daily", "date": "2016-11-09", "url": "https://www.investors.com/news/technology/solar-stocks-plunge-on-coal-champion-trumps-surprise-win/"},
  {"outlet": "Business Insider", "date": "2016-11-09", "url": "https://www.businessinsider.com/obamacare-stocks-slammed-donald-trump-election-2016-11"},
  {"outlet": "ThinkAdvisor", "date": "2016-11-10", "url": "https://www.thinkadvisor.com/2016/11/10/the-elections-dramatic-effect-on-insurance-stocks-2/"}],
 "in_main_sample": True,
 "notes": "一個事件兩個子籃(太陽能、醫院),敘事其實是兩條(稅務抵免、平價醫療法案),對照 SIC 因此要同時取 36 與 80,較混雜。結束日無出處,是推斷。SCTY(2016 年底被特斯拉收購)、LPNT(2018 私有化)、WCG(2020 被收購)是本宗倖存者缺口。"
},
{
 "event_id": "E11", "name": "2018-03 劍橋分析私隱風暴殺社交平台",
 "narrative": "Facebook 五千萬用戶資料被政治顧問公司挪用曝光,市場怕大西洋兩岸監管會逼平台改動數據與廣告定向,而那正是社交平台收入的根基。",
 "shock_start": "2018-03-16", "news_shock_end": "2018-03-27",
 "basket_definition": "當時報導點名的社交平台",
 "basket_source": "Reuters / Investing.com 2018-03-19、CBS News 2018-05-10",
 "tickers": ["META", "SNAP"],
 "tickers_headline_only": ["TWTR"],
 "sic2_basket": ["73"],
 "sources": [
  {"outlet": "Reuters(經 Investing.com)", "date": "2018-03-19", "url": "https://www.investing.com/news/stock-market-news/facebook-shares-slide-after-reports-of-data-misuse-1347789"},
  {"outlet": "Investing.com", "date": "2018-03-19", "url": "https://www.investing.com/news/stock-market-news/stocks-facebook-data-leak-political-uncertainty-weighs-on-markets-1348064"},
  {"outlet": "CBS News", "date": "2018-05-10", "url": "https://www.cbsnews.com/news/facebook-stock-price-recovers-all-134-billion-lost-in-after-cambridge-analytica-datascandal/"}],
 "in_main_sample": True,
 "notes": "本宗籃子太細,分散度不可用,只作清單登記。核證查出兩件事:(一)當日同場下跌的 AMZN/NFLX/TSLA/INTC/AMD/ORCL 不是本敘事的受害者,是同日大市走勢,故剔出籃外;(二)廣告科技純股(CRTO/TTD/RUBI/QUOT)一隻都找不到當時被點名的出處,所以這個敘事最應該打中的那一批反而無名單。FB 已改名 META,用今日代號解析;TWTR 2022 年私有化,是倖存者缺口。"
},
{
 "event_id": "E12", "name": "2019-05 華為實體清單殺半導體",
 "narrative": "華為被列入實體清單、美國供應商相繼斷供,市場怕多間晶片商前五大客戶的下半年收入直接消失,還要面對中方報復。",
 "shock_start": "2019-05-17", "news_shock_end": "2019-05-21",
 "basket_definition": "當時報導點名的半導體",
 "basket_source": "Reuters / Investing.com 2019-05-20 逐隻點名;實體清單以聯邦公報為一手",
 "tickers": ["QCOM", "XLNX", "MU", "AVGO", "SWKS", "AMD", "LITE", "QRVO", "INTC"],
 "tickers_headline_only": [],
 "sic2_basket": ["36"],
 "sources": [
  {"outlet": "Reuters(經 Investing.com)", "date": "2019-05-20", "url": "https://www.investing.com/news/stock-market-news/chips-are-down-huawei-us-blacklisting-knocks-eu-semiconductor-stocks-1873020"},
  {"outlet": "Investing.com", "date": "2019-05-20", "url": "https://www.investing.com/news/stock-market-news/stocks--sp-stumbles-as-huawei-ban-sends-chip-stocks-spiraling-lower-1873753"},
  {"outlet": "Federal Register(一手)", "date": "2019-05-21", "url": "https://www.federalregister.gov/documents/2019/05/21/2019-10616/addition-of-entities-to-the-entity-list"}],
 "in_main_sample": True,
 "notes": "2018-19 貿易戰有多個節點(2018-07、2018-11-19、2019-05-16、2019-08-05),選華為這一節是因為它是唯一逐間公司點名、機制指向半導體那一個;但「它最急」這一判斷沒有跨事件排名的出處,屬本票的判斷不是核出來的事實。急性期只有兩日(05-21 已發九十日臨時許可證),窗口極短。XLNX 2022 年被 AMD 收購,是本宗倖存者缺口。"
},
{
 "event_id": "E13", "name": "2022-01 利率衝擊殺未獲利軟件股",
 "narrative": "聯儲局會議紀要顯示除加息外還會提早縮表,市場怕長年期現金流的貼現率一升,最傷的就是利潤還未出現的軟件股。",
 "shock_start": "2022-01-03", "news_shock_end": "2022-01-24",
 "basket_definition": "當時報導點名的高倍數/未獲利軟件股",
 "basket_source": "CNBC / AP-LA Times / Motley Fool 2022-01-03 至 01-07 逐隻點名",
 "tickers": ["ZM", "DOCU", "SHOP", "ASAN", "TWLO", "CRWD", "DDOG", "HUBS", "MDB", "CRM", "ADBE", "MSFT", "NET", "BILL"],
 "tickers_headline_only": [],
 "sic2_basket": ["73"],
 "sources": [
  {"outlet": "CNBC", "date": "2022-01-07", "url": "https://www.cnbc.com/2022/01/07/cloud-stocks-plunge-as-investors-sour-on-pandemics-top-performers.html"},
  {"outlet": "AP / LA Times", "date": "2022-01-05", "url": "https://www.latimes.com/business/story/2022-01-05/tech-stocks-slide-bonds-fall-after-fed-flags-rate-hikes"},
  {"outlet": "Motley Fool(經 Nasdaq)", "date": "2022-01-03", "url": "https://www.nasdaq.com/articles/why-crowdstrike-datadog-hubspot-and-mongodb-fell-today"},
  {"outlet": "CNBC", "date": "2022-01-24", "url": "https://www.cnbc.com/2022/01/24/stocks-staged-a-remarkable-turnaround-but-the-selling-is-not-over-.html"}],
 "in_main_sample": True,
 "notes": "2021-11 起已在去泡沫,2022-05 亦有一腿;選 2022-01 這一段是因為它是唯一「有日期的利率事件 → 未獲利軟件集中跌」。SNOW 與 U 只有搜尋摘要無正文,不入籃。"
},
{
 "event_id": "E14", "name": "2023-05 生成式 AI 殺教育科技",
 "narrative": "Chegg 在業績電話會議明講 ChatGPT 正在搶走它的新客,市場怕免費通用聊天機械人直接打掉賣功課輔導與參考內容的付費訂閱。",
 "shock_start": "2023-05-01", "news_shock_end": "2023-05-03",
 "basket_definition": "當時報導點名的教育科技",
 "basket_source": "CNBC 2023-05-02 / Motley Fool 2023-05-03 / Ummid 2023-05-03",
 "tickers": ["CHGG", "DUOL", "UDMY"],
 "tickers_headline_only": [],
 "sic2_basket": ["82"],
 "sources": [
  {"outlet": "CNBC", "date": "2023-05-02", "url": "https://www.cnbc.com/2023/05/02/chegg-drops-more-than-40percent-after-saying-chatgpt-is-killing-its-business.html"},
  {"outlet": "Motley Fool", "date": "2023-05-03", "url": "https://www.fool.com/investing/2023/05/03/why-chegg-and-pearson-just-popped-duolingo-dropped/"},
  {"outlet": "Ummid", "date": "2023-05-03", "url": "https://ummid.com/news/2023/may/03.05.2023/mayhem-in-global-edtech-sector-after-cheggs-warning-over-chatgpt.html"}],
 "in_main_sample": True,
 "notes": "本宗籃子只有三家,分散度不可用,只作清單登記。這正是「一個敘事打一個籃子」的極端例:敘事非常清楚,但當時被點名的同類上市公司就只有三家(Pearson 是存託憑證,按只計美國普通股的規矩剔除)。急性期實際只有一個交易日加翌日反彈。"
},
{
 "event_id": "E15", "name": "2026-02 AI 代理殺應用軟件(SaaSpocalypse)",
 "narrative": "Anthropic 開源 Claude 外掛、法律外掛推出,市場怕通用 AI 代理可以直接執行企業工作流,SaaS 賣的那件產品本身變成 AI 的一個功能,受威脅的是收入不只是毛利。",
 "shock_start": "2026-02-02", "news_shock_end": "2026-02-24",
 "basket_definition": "當時報導點名的應用軟件與法律/數據科技",
 "basket_source": "CNBC / TechStartups / Forbes / Reuters 2026-02-04 至 02-24 逐隻點名",
 "tickers": ["CRM", "NOW", "ADBE", "WDAY", "INTU", "LZ", "LAW", "ASAN", "DOCU", "HUBS", "TEAM", "SHOP", "SNOW", "OWL"],
 "tickers_headline_only": ["NET", "CRWD", "PLTR", "IBM", "DDOG", "OKTA", "MNDY", "FRSH", "ORCL", "AGYS"],
 "sic2_basket": ["73"],
 "sources": [
  {"outlet": "CNBC", "date": "2026-02-06", "url": "https://www.cnbc.com/2026/02/06/ai-anthropic-tools-saas-software-stocks-selloff.html"},
  {"outlet": "TechStartups", "date": "2026-02-05", "url": "https://techstartups.com/2026/02/05/anthropics-claude-plugins-spark-285-billion-software-stock-selloff-as-ai-targets-entire-saas-workflows/"},
  {"outlet": "Forbes", "date": "2026-02-04", "url": "https://www.forbes.com/sites/donmuir/2026/02/04/300-billion-evaporated-the-saaspocalypse-has-begun/"}],
 "in_main_sample": True,
 "notes": "票面寫「2026 年初 AI 取代 SaaS」,核證後日期要改:觸發者是 Anthropic 的 Claude Cowork 與外掛,主震公布日 2026-02-02、首個完整交易日反應 2026-02-03。本宗有兩段獨立衝擊(2026-02 與 2026-04 業績段),窗口只取 2 月那一段。十二個月未到期(價格庫止於 2026-09-02),只有三個月與六個月數得出,故本宗不參與事前特徵的十二個月對照——它是 KARST-198 前瞻登記的對象,不是歷史樣本。TRI 是加拿大公司,按只計美國普通股的規矩剔除。"
},
{
 "event_id": "E16", "name": "2020-03 疫情加油價戰殺旅遊休閒與能源(另列,不入主樣本)",
 "narrative": "疫情令收入蒸發,同時撞正沙特與俄羅斯增產戰壓垮油價,市場怕郵輪、航空、酒店、博彩與高槓桿油企的資產負債表撐不過幾季停擺。",
 "shock_start": "2020-03-06", "news_shock_end": "2020-03-23",
 "basket_definition": "當時報導點名的能源、郵輪、航空、酒店、博彩",
 "basket_source": "AP / Cruise Industry News / CNBC / Fox Business 2020-03-09 及同一急性窗內報導",
 "tickers": ["OXY", "APA", "MRO", "FANG", "XOM", "CVX", "HAL", "SLB", "CCL", "RCL", "NCLH", "LIND",
             "UAL", "DAL", "AAL", "LUV", "JBLU", "HA", "MAR", "HLT", "H", "LVS", "MGM", "WYNN",
             "PENN", "CZR", "ERI"],
 "tickers_headline_only": [],
 "sic2_basket": ["13", "45", "70", "79"],
 "sources": [
  {"outlet": "AP / Denver Post", "date": "2020-03-09", "url": "https://www.denverpost.com/2020/03/09/dow-stock-market-plunge-coronavirus-monday/"},
  {"outlet": "Cruise Industry News", "date": "2020-03-09", "url": "https://cruiseindustrynews.com/cruise-news/2020/03/black-monday-for-cruise-line-stocks/"},
  {"outlet": "CNBC", "date": "2020-03-09", "url": "https://www.cnbc.com/2020/03/09/stock-market-today-live.html"},
  {"outlet": "Fox Business", "date": "2020-03-09", "url": "https://www.foxbusiness.com/markets/us-markets-march-9-2020"}],
 "in_main_sample": False,
 "notes": "票面明文另列不入主樣本。理由不只是它大:它是全市場崩跌加上聯儲局無限量買債救市,籃子之後的回報主要由大市反彈與流動性決定,不是由「敘事對這一家適不適用」決定。基準率表早已量到①池的優勢一半來自 2020 年 3 月,本表刻意不讓它再做一次同樣的事。"
},
]

have = {e["event_id"] for e in s["events"]}
s["events"].extend([e for e in new if e["event_id"] not in have])
p.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
print("events:", len(s["events"]))
