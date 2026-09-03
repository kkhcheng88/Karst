---
id: KARST-174
title: 申報索引副本清理(D-157;D-134 落地):EDGAR submissions/申報索引在五個實驗目錄各存一份副本(一個 334MB)——定一份正本位置(data/sec/submissions/ 或現有最完整那份),其餘逐檔核 sha256 與正本相同才刪,不同者保留並列出差異;所有引用該副本的腳本改指向正本;不動 10-K 文本快取與 companyfacts
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

背景:KARST-167 報告(research/2026-09-03-小型股宇宙v0盤點.md)發現申報索引(EDGAR submissions/bulk index)在五個實驗目錄各存一份副本,D-134 單一副本原則在這一格從未落地。先讀:D-134、D-153、D-157;data/sec/10k_text/README.md(單一快取範本);該報告列出的五個位置。做法:①盤點:列出每份副本的路徑、大小、sha256、抓取日期(檔內或 manifest)、被哪些腳本引用(Grep);②定正本:最完整或最新那份搬入 data/sec/submissions/(Move-Item 整檔位元操作,不解碼內容),寫 README.md(來源、抓取日期、格式、更新方法)與 manifest.csv;③其餘副本:sha256 與正本相同者刪除(Remove-Item),不同者保留原位並在 README 列出差異(大小、日期、行數差),不擅自合併;④引用它們的腳本改路徑指向正本(只改路徑常數,不改邏輯),每個改動列在票上留言;⑤刪除前把清單寫進票上留言(路徑、大小、sha256、與正本相同的證據),刪除後再留言確認;⑥不動 10-K 文本快取、companyfacts、價格庫;生產庫只讀,SHA256 首 16 位維持 b168e9f45b578cf9。禁區:中文檔只經 Read/Write/Edit;絕對路徑;PS 5.1 無 &&;不建目錄連結指向 data/;>5MB 不入 git(README、manifest 用 git add -f)。完成:AC 逐格用 Edit 剔 [x],comment 後 close;要人裁用四格 raise 加 docs 鍵。

## 驗收條件

- [ ] 票上留言列齊五份副本的路徑、大小、sha256、引用腳本,刪除前後各一則留言
- [ ] data/sec/submissions/ 正本連 README.md 與 manifest.csv(git add -f);與正本相同的副本已刪,不同者保留並在 README 列出差異
- [ ] 引用副本的腳本改指向正本,只改路徑常數;10-K 文本快取、companyfacts、價格庫不動
- [ ] 生產庫只讀,SHA256 首 16 位維持 b168e9f45b578cf9;commit 用 git commit --only -F <訊息檔> -- <自己的檔>

## 結果

## 留言
