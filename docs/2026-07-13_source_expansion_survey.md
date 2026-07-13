# 2026-07-13 — 研究/分析報告來源擴闊調研(source expansion survey)

> **動機**:現有輸入源 = gooptions.cc(日抓)、Backtest-Everything transcripts、defeatbeta 法說 corpus
> (9.9k ticker)、SEC EDGAR insider(Form 3/4/5)、IMA(人手週度)。深度夠、闊度唔夠——全部係「事後」
> (公司自己講)或「人手」(IMA),缺「第一手供給/定價數據」同「即日事件披露」兩類。本檔調研可新增
> 嘅來源,逐個實測,出 top 5 建議 + 接入路徑。
>
> **方法**:全部候選用 `WebFetch` 或 `curl`(bash)親自試,唔靠訓練記憶。部分網站對 `WebFetch` 工具
> 本身有 bot 防護(Cloudflare/Akamai),再用 `curl` + 瀏覽器 User-Agent 覆核,兩種結果都記錄。

---

## 1. 篩選標準(缺一即剔)

1. **免費層有實質內容**(或一次性平價;唔考慮貴訂閱)
2. **可程式化抓取**(RSS/API/穩定 HTML;唔使 login,或 login 後有 RSS)
3. **對供給約束/資本週期類 thesis 有訊號密度**(產能/交期/定價/capex 呢啲軸,唔係大市評論)
4. **可帶引用落檔**(有 URL、日期、作者)

---

## 2. 逐候選評估表(13 個候選,全部實測)

| # | 候選 | 實測方法 | 實測結果 | 免費?| 可程式化?| 訊號密度 | 判定 |
|---|---|---|---|---|---|---|---|
| 1 | **SEC EDGAR 全文檢索 API**(`efts.sec.gov`) | curl(SEC UA)關鍵詞 `"capacity constrained"` + `forms=8-K` | HTTP 200;真.命中(Civeo Corp 8-K,2026-07-02) | ✅ | ✅ JSON API | 極高(市場全域 constraint 語言) | **入選 #1** |
| 2 | **TrendForce Press Center** | WebFetch 網頁 | 100% 免費全文,7月13日更新(SLC NAND 漲價 120-170%、Server DRAM Q3 漲 13-18% 等) | ✅ | 部分(無RSS,穩定HTML) | 極高(第一手定價/產能數字) | **入選 #2** |
| 3 | **Utility Dive RSS** | WebFetch RSS | 有效 RSS2.0,7月13日 5條(含「transfer capacity」「transmission bottlenecks」) | ✅ | ✅ 標準RSS | 高(直中 ai-power-grid) | **入選 #3** |
| 4 | **DIGITIMES daily RSS** | WebFetch RSS(`/rss/daily.xml`;首試 `latestnews.xml` 404) | 有效 RSS2.0,實時(HBM/glass interposer/foundry capacity) | ✅ | ✅ 標準RSS | 高(台灣供應鏈廣度) | **入選 #4** |
| 5 | **SIA 全球半導體月度銷售** | WebFetch 403(Cloudflare擋工具)→ curl(瀏覽器UA)200,確認全文 388 字、`articleSection: Press Release`、可信 datePublished | ✅ 真.免費全文 | ✅(listing page 可 regex 揾新連結,無RSS) | 中(量化銷售數,非直接constraint,但係唯一數字時間序列候選之一) | **入選 #5** |
| 6 | SEC EDGAR 逐 ticker submissions JSON(`data.sec.gov`) | WebFetch 403(UA問題)→ curl(SEC UA)200,Micron 8-K/10-Q 列表確認 | ✅ | ✅ JSON | 高 | 通過但同 #1 大幅重疊,唔獨立佔名額(併入 #1 實作) |
| 7 | 公司 IR PR feed(Q4平台pattern,以 MP Materials 為例) | curl,`investors.mpmaterials.com/rss/pressrelease.aspx` | 200,真實 6 條(日期到 2026-06-16) | ✅ | ✅ 但逐間公司URL/平台唔同 | 中(同 SEC 8-K 內容大量重疊) | 剔:同 #1 邊際重疊,唔統一(逐 ticker 要各自搵IR網址,唔符合 user-agnostic 系統設計) |
| 8 | Fabricated Knowledge(Substack,半導體) | WebFetch RSS `/feed` | 有效RSS、全文免費(15,000+字),但近期文章主題飄向 robotics/經濟學(Unitree/Engels' Pause) | ✅ | ✅ RSS | 中低(主題飄移,唔夠純供給約束) | 剔:訊號密度不足(criterion 3 邊緣未過),留做人手精讀候選 |
| 9 | SemiAnalysis | WebFetch RSS `/feed` | RSS有效,但條目混合 —— 部分全文、部分俾 `wp-block-passport-restricted-content` 擋(login/subscribe wall) | 🟡 不穩定 | ✅ RSS(內容不完整) | 極高(但拎唔到) | 剔:免費層唔穩定(criterion 1 邊緣未過) |
| 10 | Doomberg(Substack,能源/地緣) | WebFetch `/feed` → 301 到 `newsletter.doomberg.com`,只攞到 landing page,冇拎到 post 列表 | 無法驗證免費比例 | ❓ | ❓ | 高(如果真係免費) | 剔:實測攞唔到證據,已知模式係大部分收費 |
| 11 | Baker Hughes rig count | WebFetch timeout → curl(瀏覽器UA)`403 Access Denied`(Akamai edgesuite) | 兩次都俾 bot 防護擋死 | ❓(頁面講係免費,但攞唔到) | ❌ | 中(鑽井數,油氣供給側,但 Karst 已剔 oil-gas 追加宏觀序列) | 剔:criterion 2 唔過;另外 2026-07-12 用戶已決定唔再追加 EIA/rig-count 類宏觀序列(見 STATUS.md) |
| 12 | 工商時報 CTEE(`ctee.com.tw`) | curl(瀏覽器UA)`/feed`、`/wp-json/...` | Cloudflare JS challenge(「Just a moment...」),兩條路都擋 | ❓ | ❌(要 headless browser) | 高(如果攞到) | 剔:criterion 2 唔過,效益唔抵額外 headless browser 工程 |
| 13 | SEMI.org(半導體設備 book-to-bill) | WebFetch 403 → curl(瀏覽器UA)404(`/news-media-center/press-releases` 唔存在) | 預算內揾唔到正確 URL | ❓ | ❓ | 高(equipment book-to-bill 係 semicap-equipment 領先指標) | 未解,列入「未解/風險」,下次可用 WebSearch 先確認正確路徑 |

**備註**:SIA / SEC(submissions JSON)兩個 WebFetch 工具本身 403,但 `curl` + 瀏覽器 UA 一試就 200 —— 呢個
係 WebFetch 工具嘅 UA 指紋俾網站擋,唔係網站本身要 login;正式接入時用 Python `requests` + 合理 UA
(SEC 仲要求 descriptive UA + ≤10 req/s,見 `thesis/insider_edgar.py:29` 已有 pattern)一樣會通。
Baker Hughes / CTEE 兩個就係真.企業級 bot 防護(Akamai / Cloudflare JS challenge),兩種攔截唔可以混為一談。

---

## 3. Top 5 排名 + 理由

| 排名 | 來源 | 一句理由 |
|---|---|---|
| 1 | **SEC EDGAR 全文檢索 API**(`efts.sec.gov`) | 市場全域關鍵詞掃 8-K/10-Q/10-K,將現有「constraint-language = 主管道」由 defeatbeta 法說擴到**即日一手披露**(比下季 earnings call 更早),直接命中 Phase-3「夠早/priced-in」需求;免費、官方、`insider_edgar.py` 已有 UA/節流 pattern 可複用 |
| 2 | **TrendForce Press Center** | 唯一一個「數字係產能/定價本身」而非評論嘅來源(DRAM/NAND 合約價%、book-to-bill),直餵 memory-supercycle/semicap-equipment/advanced-packaging 三個現有 theme,100% 免費全文已證 |
| 3 | **Utility Dive RSS** | 填一個真.缺口 —— ai-power-grid 係現有 live theme(已有 per-node schema)但**而家零專門媒體監控**,淨靠 transcript 語言;免費RSS、更新量大、標題已經有「transmission bottlenecks」呢類 constraint 詞 |
| 4 | **DIGITIMES daily RSS** | 同 TrendForce 互補(封裝/HBM/foundry capacity/車用晶片,範圍更闊),免費RSS已證,對 advanced-packaging/photonics-optical/semicap-equipment 有價值 |
| 5 | **SIA 全球半導體月度銷售** | 現有信號全部係質性/文字(除咗 TWSE 一條),SIA 係第一條可加嘅**量化數字時間序列**候選,官方、月度、免費全文已證 |

---

## 4. 每個 Top 5 嘅具體接入步驟

### 4.1 SEC EDGAR 全文檢索 API
- Endpoint:`https://efts.sec.gov/LATEST/search-index?q="<詞彙>"&forms=8-K,10-Q,10-K&startdt=YYYY-MM-DD&enddt=YYYY-MM-DD`
- 複用 `thesis/insider_edgar.py` 現有 `_UA = {"User-Agent": "Karst-research/1.0 (contact ...)"}` + ≤10 req/s 節流。
- 建供給約束詞彙表(移植 `thesis/constraint_scan.py` 現有 keyword set:capacity constrained / sold out /
  lead time extended / allocation / backlog 等),逐詞查、逐 theme 對應 ticker 過濾。
- 命中後用回傳嘅 `_id`(`accession:filename`)組 filing URL
  (`https://www.sec.gov/Archives/edgar/data/<cik>/<accession-no-dashes>/<filename>`)再攞全文引用。
- 落 thesis wiki source node:仿 `thesis/build_source_nodes.py` 現有 pattern,`tier: 1`(一手 filing,
  高過 gooptions 嘅 `tier: 2`)。
- 排程:日度或週度均可(建議摺入 05:55 `Karst-nightly-analysis` 第 4 個 guard,同 gooptions/transcript
  inbox 同一批處理)。
- 工作量:**中**(詞彙表設計 + dedup + rate-limit 節流;access pattern 已有先例)。

### 4.2 TrendForce Press Center
- URL:`https://www.trendforce.com/presscenter`(HTML,無 RSS)。
- 寫輕量 scraper(`requests` + regex/BeautifulSoup)攞 title/date/summary/link,存 manifest json,
  仿 `thesis/download_gooptions.py` 嘅 resumable-manifest pattern。
- Dedup key = title+date。存落 `thesis/.raw/trendforce/`。
- 排程:日度(可掛喺 05:35 `Karst-gooptions-daily` 同一個 slot 加一條新 job)。
- 工作量:**細**(單頁、無分頁、有現成 pattern 可抄)。

### 4.3 Utility Dive RSS
- URL:`https://www.utilitydive.com/feeds/news/`(標準 RSS 2.0)。
- Python `feedparser` 直接 parse;keyword-filter 揀 grid/transmission/capacity/data-center 相關,
  剔除 `/spons/`(贊助內容)路徑嘅項目。
- 掛落 `thesis/wiki/ai-power-grid.md` source node。
- 工作量:**細**(標準 RSS parse,幾行 code)。

### 4.4 DIGITIMES daily RSS
- URL:`https://www.digitimes.com/rss/daily.xml`。
- 同 4.3 做法一樣:標準 RSS parse,用 `<category>` 欄位(Semiconductors/Servers 等)做初篩,
  再用供給約束詞彙表(同 4.1 共用)二篩。
- 工作量:**細**。

### 4.5 SIA 全球半導體月度銷售
- Listing page:`https://www.semiconductors.org/news-events/latest-news/`(免用 WebFetch 工具,改用
  `requests` + 瀏覽器 UA,已證可過)。
- 月度 scrape:regex 揾 `global-semiconductor-sales-*` slug 連結 → fetch 該頁 → 抽數字
  (JSON-LD `datePublished` + 內文 % 變化,已證頁面帶 schema.org metadata 方便解析)。
- 存做 jsonl 時間序列,做「量化供需佐證欄」,同而家質性 confidence 分數並列顯示(唔取代)。
- 工作量:**細-中**(月度單次,URL discovery 邏輯要寫一次,pattern 已驗證穩定)。

---

## 5. 被剔候選(連剔因)

- **公司 IR RSS(Q4平台,MP Materials 為例)**:實測通過(免費、200、真實日期),但同 SEC EDGAR 8-K
  內容大量重疊,而且逐間公司要各自搵 IR 網址/平台(Q4/PRNewswire/BusinessWire 唔統一)——違反「系統
  層要 user-agnostic、唔逐票手工配線」嘅設計原則。SEC EDGAR 全文檢索一條 API 已經蓋晒。
- **Fabricated Knowledge(Substack)**:免費全文確認,但近期文章主題飄向 robotics/總體經濟(非純半導體
  供給鏈),訊號密度對「供給約束」呢個窄軸唔夠純,criterion 3 邊緣未過。可留做人手精讀候選,唔做自動
  ingest 首選。
- **SemiAnalysis**:RSS 有效但條目混合——部分全文、部分俾 `subscribe wall` 擋,免費層唔穩定
  (criterion 1 邊緣未過)。如果用戶自己有訂閱,可以另外再評估(唔喺今次「免費層」範圍內)。
- **Doomberg**:`/feed` 301 導到 `newsletter.doomberg.com`,只攞到 landing page,拎唔到 post 列表核實
  免費比例。已知商業模式係大部分內容收費、少量免費 teaser,criterion 1 冇實證支持。
- **Baker Hughes rig count**:WebFetch timeout + curl(瀏覽器UA)雙雙俾 Akamai `Access Denied` 擋死,
  criterion 2 唔過。另外,用戶 2026-07-12 已明確決定唔再追加油氣類宏觀序列(EIA-930/crack spread/
  ISM/Cass Freight/AAR 同批剔除,見 STATUS.md),呢個屬同一類判斷。
- **工商時報 CTEE**(`ctee.com.tw`):`/feed`同 `/wp-json/` 兩條路都俾 Cloudflare JS challenge
  (「Just a moment...」)擋,要 headless browser 先過,criterion 2 唔過、效益唔抵額外工程。DIGITIMES
  已覆蓋台灣半導體供應鏈呢一塊,功能上可替代。
- **SEMI.org(equipment book-to-bill)**:兩個測試 URL(`/news-media-center/press-releases`、
  `/en/news-media-center`)都 404,預算內揾唔到正確路徑。**唔係剔除,係未解**——見下節。

---

## 6. 未解 / 風險

- **SEMI.org book-to-bill 正確 URL 未搵到**:semicap-equipment theme 而家冇量化領先指標(現有訊號全靠
  transcript 語言),SEMI 月度 book-to-bill ratio 係業界標準嘅設備訂單領先指標,值得下次用 WebSearch
  先定位正確路徑(而唔係靠猜 URL)再重測,可以做 SIA 之後嘅候補第 6 名。
- **WebFetch 工具本身嘅 bot 防護盲點**:SIA / SEC submissions JSON 兩個都係「WebFetch 403、curl 200」
  ——即工具本身嘅請求指紋俾部分網站擋,但實際生產環境用 `requests` library 可以通。呢個唔係網站唔
  免費,調研時要留意唔可以單憑 WebFetch 403 就判死一個候選(本次已用 curl 覆核修正)。
- **TrendForce / DIGITIMES 深度報告仍然收費**:今次驗證嘅係「新聞/press center」淺層(免費),兩間
  都各自有「Research」/「DIGITIMES Research」深度報告要俾錢——呢個唔喺推薦範圍內,接入時要注意淨係
  scrape 免費新聞層,唔好誤觸付費報告頁面。
- **SEC 全文檢索嘅 rate limit / 詞彙表品質未驗證實跑**:本次只做單一詞彙(`"capacity constrained"`)
  單次 hit 驗證 API 通,未測試大規模多詞彙、多 theme 掃描嘅實際雜訊率(false positive 比例、跟現有
  transcript-based constraint_scan.py 嘅重疊度)——建議接入後first pass 對比兩個管道嘅 hit 品質。
