---
id: KARST-177
title: 申報索引正本補全(D-161;KARST-174 舉手答甲):把 experiments/2026-09-02-silent-revisions/data/submissions/ 保留的 1,051 個歷史分頁檔與 99 份宇宙外公司收編入 data/sec/submissions/(整檔位元搬移、逐檔 sha256 入 manifest),再向 EDGAR 補抓餘下 1,765 個歷史分頁(≤10 req/s、User-Agent Casy Limited kaho.career@gmail.com、fetchedBy 填票號),正本改為每家「主檔加全部分頁」結構並寫 README;重算 KARST-167 首次申報年分佈並在 research/2026-09-03-小型股宇宙v0盤點.md 加更正節;A-046 依結果更新
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

背景:KARST-174(commit 1ccdead、76d7bf0;data/sec/submissions/README.md 第二節)查出證監會 submissions 索引每家只載最近約 1,000 份申報,正本 8,012 份之中 2,066 份(25.8%)被截短,欠 2,736 個歷史分頁(filings.files[] 內 name 指向的 CIK##########-submissions-NNN.json),其中 971 個現存於 silent-revisions 目錄(227MB),餘 1,765 個未抓;另有 99 份正本沒有的宇宙外公司。D-161 裁收編加補抓。先讀:D-134、D-157、D-161;data/sec/submissions/README.md 與 manifest.csv、manifest.jsonl;KARST-174 票上留言;experiments/2026-09-02-silent-revisions/fetch_8k402.py(它的寫入路徑現時仍指向實驗目錄,本票收編後改指正本)。做法:①正本結構:data/sec/submissions/<CIK>.json 主檔不動,分頁存 data/sec/submissions/pages/<CIK>-submissions-NNN.json,manifest.jsonl 每個分頁一行(cik、page、fetchedAt、fetchedBy、bytes、sha256、source=moved/fetched);②收編:Move-Item 整檔搬移(不解碼),搬後逐檔 sha256 與搬前相同才記入 manifest,搬不成者留原位列出;99 份宇宙外公司主檔同樣搬入並在 manifest 標 outside_universe_v0;③補抓 1,765 個分頁:抓前查 manifest,403 退讓重試不停跑,失敗者列 failed.csv;④完整性核對:每家主檔 filings.files[] 列出的分頁全部在 pages/ 才記 complete,否則 partial,manifest.csv 加 completeness 欄,報告列 complete 家數與比率;⑤fetch_8k402.py 寫入路徑改指正本 pages/(只改路徑常數);⑥重算首次申報年分佈(每家取主檔加全部分頁的最早 filingDate),在 research/2026-09-03-小型股宇宙v0盤點.md 加「更正:首次申報年」一節,舊新並列;⑦A-046 經 Edit 更新(補全後仍被截短的家數為證據;全部補齊記 overturned 維持並註明已修復,否則寫明餘缺);⑧>5MB 不入 git,README/manifest/failed.csv/腳本用 git add -f;生產庫只讀 SHA256 首 16 位維持 b168e9f45b578cf9;不動 10-K 文本快取、companyfacts、價格庫。禁區:中文檔只經 Read/Write/Edit;絕對路徑;PS 5.1 無 &&;不建目錄連結指向 data/;不用 MCP 連接器、不裝付費源。本機另有兩隊在做 KARST-175(鏈層重跑)與 176(淨現金重驗),不要 add 它們的檔。完成:AC 逐格用 Edit 剔 [x],comment 後 close;要人裁用四格 raise 加 docs 鍵。

## 驗收條件

- [ ] 1,051 個歷史分頁與 99 份宇宙外公司收編入 data/sec/submissions/(pages/ 結構),逐檔 sha256 入 manifest.jsonl,搬不成者列出
- [ ] 餘下 1,765 個分頁補抓,失敗者列 failed.csv;manifest.csv 加 completeness 欄,報告列 complete 家數與比率
- [ ] 首次申報年分佈重算並在 research/2026-09-03-小型股宇宙v0盤點.md 加更正節(舊新並列);A-046 經 Edit 更新附證據;fetch_8k402.py 寫入路徑改指正本
- [ ] EDGAR ≤10 req/s、User-Agent 正確;>5MB 不入 git;生產庫只讀,SHA256 首 16 位維持 b168e9f45b578cf9;commit 用 git commit --only -F <訊息檔> -- <自己的檔>

## 結果

## 留言
