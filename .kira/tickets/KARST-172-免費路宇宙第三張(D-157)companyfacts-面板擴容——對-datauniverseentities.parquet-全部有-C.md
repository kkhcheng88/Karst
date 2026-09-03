---
id: KARST-172
title: 免費路宇宙第三張(D-157):companyfacts 面板擴容——對 data/universe/entities.parquet 全部有 CIK 的實體補抓 EDGAR companyfacts(≤10 req/s、User-Agent Casy Limited kaho.career@gmail.com、gzip 存入 data/sec/companyfacts/ 單一快取連 manifest),再以實體主鍵重建季度面板 v3(股數、現金、負債、營收、經營現金流等 D-155 淨現金篩選所需欄位),外國申報人(FPI)記「取不到」不記零;不改生產庫
type: task
createdAt: 2026-09-03
risk: low
model: opus
fits: yes
dependsOn: []
claimedBy: Claude Opus 5
deliverable: KARST-D02
closed: 2026-09-03
---

## 工作內容

背景:KARST-167 估 companyfacts 補抓 4,649 家 10–15 分鐘、原始 JSON 7–16GB,外國申報人多數為空;D-157 裁 gzip 單一快取、FPI 記取不到。前置:KARST-171 的價格庫已落地(若未落地,本票不依賴它,可先做)。先讀:D-134、D-153、D-155、D-157;data/universe/RULES.md;現有面板 v2(雜湊 ab02e335c3ebc169)的建法與欄位(experiments/ 內 panel 相關腳本,用 Glob 找);data/sec/10k_text/README.md 的 manifest 格式作範本。做法:①快取:data/sec/companyfacts/<CIK>.json.gz 一家一檔,manifest.csv 欄位 cik、entity_id、fetchedAt、fetchedBy(填票號)、bytes、sha256、status(ok/empty/fail)、http_code;抓前查 manifest 已有且 status ok 者跳過;②面板:data/panel/quarterly_v3.parquet,以 entity_id 加 period_end 為鍵,欄位至少 shares_outstanding、cash_and_equivalents、short_term_investments、total_debt(長短期分列可加)、revenue、operating_cash_flow、net_income、filed_date(以申報日為可得日,不用期末日,避免前視);每格帶 source_tag(us-gaap/ifrs-full/dei)與 missing_reason(none/fpi_no_facts/tag_absent/fail);③外國申報人:companyfacts 空或只有 dei 者整家記 fpi_no_facts,不填零;④覆蓋率報告 research/2026-09-03-面板v3盤點.md:多少家有 companyfacts、多少家四個核心欄位齊、按市值分層(<5 億、5–50 億、>50 億)的欄位齊全率、對面板 v2 交集實體抽 30 家對帳、誠實聲明(以申報日為可得日、重述值取最新申報一次即帶修訂前視,要寫明);⑤>5MB 不入 git,git add -f README.md、manifest.csv、腳本;⑥生產庫只讀,SHA256 首 16 位維持 b168e9f45b578cf9。禁區同 KARST-171:不開交易介面、不裝付費源、不用 MCP 連接器;中文檔只經 Read/Write/Edit;PYTHONUTF8=1;絕對路徑;PS 5.1 無 &&;不建目錄連結指向 data/;EDGAR 403 出現就退讓重試,不停跑。完成:AC 逐格用 Edit 剔 [x],comment 後 close;要人裁用四格 raise 加 docs 鍵。

## 驗收條件

- [x] data/sec/companyfacts/ 單一 gzip 快取連 manifest.csv(cik、entity_id、fetchedAt、fetchedBy、bytes、sha256、status、http_code);抓前查 manifest 不重抓
- [x] data/panel/quarterly_v3.parquet 以 entity_id+period_end 為鍵,含 D-155 淨現金篩選所需欄位,每格帶 source_tag 與 missing_reason;FPI 記 fpi_no_facts 不記零
- [x] research/2026-09-03-面板v3盤點.md:覆蓋率、按市值分層欄位齊全率、30 家對帳、誠實聲明(申報日為可得日、重述前視)
- [x] EDGAR ≤10 req/s、User-Agent 正確;>5MB 不入 git;生產庫只讀,SHA256 首 16 位維持 b168e9f45b578cf9;commit 用 git commit --only -F <訊息檔> -- <自己的檔>

## 結果

## 留言

### agent:Claude Opus 5 · 2026-09-03 10:02
收工留言(KARST-172)

【原料】對 data/universe/entities.parquet 全部 5,257 個有 CIK 的實體抓 EDGAR companyfacts:每秒 8 次(上限 10)、User-Agent Casy Limited kaho.career@gmail.com、10.3 分鐘跑完、零次 403。gzip 一家一檔存 data/sec/companyfacts/,共 5,236 個檔、壓縮後 732 MB、原始 JSON 10.4 GB。manifest.csv 八欄齊(cik、entity_id、fetchedAt、fetchedBy=KARST-172、bytes、sha256、status、http_code),抓前查 manifest、中斷靠掃碟續抓,status 為 ok 5,226 / empty 10 / fail 21(全部 HTTP 404,判永久答案不重試)。快取規格與新增規則寫在 data/sec/companyfacts/README.md。

【面板】data/panel/quarterly_v3.parquet,鍵 entity_id+period_end,220,132 列(220,084 列有真實期末)、5,257 個實體、102 欄、22.9 MB。每個欄位帶 _tag / _scope / _unit / _filed / _missing_reason,再加首次申報值與 _restated 兩份。facts_status 按實體:ok 5,209、empty 23、fail 21、no_usable_period 4;這 48 家每一格都是 NULL 加 missing_reason,一格都沒有填零。

【覆蓋率】最新一期計:資產 99.5%、淨利 99.5%、經營現金流 98.4%、權益 98.0%、現金 96.6%、負債總額 88.1%、營收 83.7%、股數 83.4%、總債務 41.4%、短期債 35.6%、短投 24.0%。四核心(現金、總債務、營收、股數)同時有值 1,634 家 = 31.1%。按市值分層的四核心齊全率:>50 億 48.5%(1,177 家)、5–50 億 42.4%(1,379 家)、<5 億 26.0%(1,809 家)、無市值 0.9%(892 家);差距幾乎全部來自 total_debt(51.5% → 30.4%)。無市值那一層股數只有 4.4%,正好解釋它們為何在 KARST-171 估不出市值——同一個缺口在兩處各現一次。

【對帳】對面板 v2 抽 30 家、12,785 格逐格比,相同 12,644(98.90%)、不同 118、v3 缺 23。現金 100% 相同,資產/負債/長期債 99.9%+,營收 94.8% 最低。118 個差異之中約 100 個是財年末的期間長度之爭(v2 取全年、v3 取第四季;營收 68 個差異有 62 個 v3 那格是 Q、51 個在 12 月),另外 6 個是首次申報 vs 最新重述(v3 方向正確,那正是本面板要修的東西),23 個 v3 缺是標籤表未覆蓋。

【三件要講清楚的事】
一、KARST-167 估「外國申報人多數為空」估錯了。建面板途中一度有 265 家被記成 fpi_no_facts,查下去 241 家是 IFRS 申報人、帳目齊全,只是單位為 EUR/CAD/GBP/JPY——是我自己「只收 USD」的讀法造成整批假陰性。改成接受任何 ISO-3 貨幣碼後,有數實體由 4,971 升到 5,209。外國申報人(1,233 家)現金 95.5%、負債總額 86.8%、營收 86.0%,與本土申報人幾乎一樣;差的只有 total_debt(20.6% vs 47.2%,IFRS 債務標籤結構不同)與股數(68.5% vs 86.9%)。本面板不做貨幣換算,逐格記 _unit、列層記 currency,282 家最新一期不是美元。
二、total_debt 覆蓋只有 41.4%、liabilities 有 88.1%。KARST-166 判準的淨現金是「現金 − 總債務」,KARST-173 票面寫的是「現金 + 短投 − 總負債」,兩者覆蓋率差一倍以上。我不擅自選口徑,兩套欄位都建好,並報的責任交 KARST-173。
三、財年末的流量格可能放第四季而非全年(同一個 period_end 同時存在 Q4 與 FY 兩條事實,選值沒有強制跨度)。每格有 _period 可過濾,但抽查 GE 2015-12-31 那格的 Q 值是 25.85 億,並不是一個可信的第四季數字——財年末流量格是本面板最髒的一格,已在報告誠實聲明第 5 條寫明。另外股數尺度可疑 339 列 / 139 家,只打旗不修數;申報人自己填錯的期(19 列在今日之後、6 列早於 1990、37 列申報日早於期末)原樣保留。

【紀律】生產庫 karst.sqlite 全程唯讀,開工與收工兩次 SHA256 首 16 位都是 b168e9f45b578cf9。.json.gz 與 parquet 不入 git,README 與 manifest.csv 用 git add -f;commit 前核過 git diff --cached --name-only 只有自己的檔(沒有帶走 KARST-174 與 forward-yield 那兩隊的東西)。交付 commit 5359afe,報告 research/2026-09-03-面板v3盤點.md。AC 四條全數做到,已剔。
