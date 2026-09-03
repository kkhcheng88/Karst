---
id: KARST-172
title: 免費路宇宙第三張(D-157):companyfacts 面板擴容——對 data/universe/entities.parquet 全部有 CIK 的實體補抓 EDGAR companyfacts(≤10 req/s、User-Agent Casy Limited kaho.career@gmail.com、gzip 存入 data/sec/companyfacts/ 單一快取連 manifest),再以實體主鍵重建季度面板 v3(股數、現金、負債、營收、經營現金流等 D-155 淨現金篩選所需欄位),外國申報人(FPI)記「取不到」不記零;不改生產庫
type: task
createdAt: 2026-09-03
risk: low
model: opus
fits: yes
dependsOn: []
claimedBy: null
deliverable: KARST-D02
---

## 工作內容

背景:KARST-167 估 companyfacts 補抓 4,649 家 10–15 分鐘、原始 JSON 7–16GB,外國申報人多數為空;D-157 裁 gzip 單一快取、FPI 記取不到。前置:KARST-171 的價格庫已落地(若未落地,本票不依賴它,可先做)。先讀:D-134、D-153、D-155、D-157;data/universe/RULES.md;現有面板 v2(雜湊 ab02e335c3ebc169)的建法與欄位(experiments/ 內 panel 相關腳本,用 Glob 找);data/sec/10k_text/README.md 的 manifest 格式作範本。做法:①快取:data/sec/companyfacts/<CIK>.json.gz 一家一檔,manifest.csv 欄位 cik、entity_id、fetchedAt、fetchedBy(填票號)、bytes、sha256、status(ok/empty/fail)、http_code;抓前查 manifest 已有且 status ok 者跳過;②面板:data/panel/quarterly_v3.parquet,以 entity_id 加 period_end 為鍵,欄位至少 shares_outstanding、cash_and_equivalents、short_term_investments、total_debt(長短期分列可加)、revenue、operating_cash_flow、net_income、filed_date(以申報日為可得日,不用期末日,避免前視);每格帶 source_tag(us-gaap/ifrs-full/dei)與 missing_reason(none/fpi_no_facts/tag_absent/fail);③外國申報人:companyfacts 空或只有 dei 者整家記 fpi_no_facts,不填零;④覆蓋率報告 research/2026-09-03-面板v3盤點.md:多少家有 companyfacts、多少家四個核心欄位齊、按市值分層(<5 億、5–50 億、>50 億)的欄位齊全率、對面板 v2 交集實體抽 30 家對帳、誠實聲明(以申報日為可得日、重述值取最新申報一次即帶修訂前視,要寫明);⑤>5MB 不入 git,git add -f README.md、manifest.csv、腳本;⑥生產庫只讀,SHA256 首 16 位維持 b168e9f45b578cf9。禁區同 KARST-171:不開交易介面、不裝付費源、不用 MCP 連接器;中文檔只經 Read/Write/Edit;PYTHONUTF8=1;絕對路徑;PS 5.1 無 &&;不建目錄連結指向 data/;EDGAR 403 出現就退讓重試,不停跑。完成:AC 逐格用 Edit 剔 [x],comment 後 close;要人裁用四格 raise 加 docs 鍵。

## 驗收條件

- [ ] data/sec/companyfacts/ 單一 gzip 快取連 manifest.csv(cik、entity_id、fetchedAt、fetchedBy、bytes、sha256、status、http_code);抓前查 manifest 不重抓
- [ ] data/panel/quarterly_v3.parquet 以 entity_id+period_end 為鍵,含 D-155 淨現金篩選所需欄位,每格帶 source_tag 與 missing_reason;FPI 記 fpi_no_facts 不記零
- [ ] research/2026-09-03-面板v3盤點.md:覆蓋率、按市值分層欄位齊全率、30 家對帳、誠實聲明(申報日為可得日、重述前視)
- [ ] EDGAR ≤10 req/s、User-Agent 正確;>5MB 不入 git;生產庫只讀,SHA256 首 16 位維持 b168e9f45b578cf9;commit 用 git commit --only -F <訊息檔> -- <自己的檔>

## 結果

## 留言
