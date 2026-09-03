---
id: KARST-171
title: 免費路宇宙第二張(D-157):日線 OHLCV 單一價格庫——對 data/universe/ticker_periods.parquet 全部 5,952 代號時段抓 yfinance 日線(40 個一批、1.2–2 秒退讓),以實體主鍵(entity_id=CIK)加代號時段為 join 鍵存入 data/prices/daily/ 單一價格庫,連 manifest 與失敗清單;順帶收入 154 家已抓收市價與 6 個未登記價格檔(D-153),並出 universe_smallcap_v1(剔 SIC 6221 信託型 ETP)
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

背景:KARST-167 交付實體表 5,257 家、代號時段表 5,952 段(data/universe/、RULES.md 第八節記跑數後兩條規則修正);報告 research/2026-09-03-小型股宇宙v0盤點.md 估價格抓取 45–90 分鐘、300–600MB、1–3% 失敗,並實測 yfinance 200 個一批不退讓成功率只有 32%,40 個一批加 1.2–2 秒退讓 99.3%。先讀:D-134、D-152、D-153、D-157;data/universe/RULES.md;experiments/2026-09-03-price-registry-study/價格登記路線盤點.md(154 家收市價位置 experiments/2026-09-02-narrative-layers-v2/data/new_close.parquet、六個未登記價格檔清單);karst/data/freeze.py 的 ensure_entities/_ensure_ticker_period/resolve_entity_ids(生產線已有實體主鍵做法,只讀參考,不改生產碼)。做法:①先出 data/universe/universe_smallcap_v1.csv:v0 剔 SIC 6221 信託型 ETP,RULES.md 加一節記 v1 規則,其餘不動;②價格庫格式:data/prices/daily/<entity_id>.parquet 或單一分區 parquet(自選,寫進 README),欄位至少 entity_id、ticker、date、open、high、low、close、adj_close、volume、source、fetchedAt;每段只抓該代號時段 valid_from 至 valid_to 之間(缺 valid_to 抓到今日);同一實體多段代號合併成一條時間序列;③manifest.csv 每代號時段一行:entity_id、ticker、valid_from、valid_to、rows、first_date、last_date、status(ok/partial/fail)、error;失敗清單另出 failed.csv,連續失敗者重試一次後放棄,不無限重試;④154 家新增收市價與 6 個未登記檔:先查其代號時段登記,已登記者 yfinance 重抓全 OHLCV 後舊檔留原位不刪(只在 README 標為已被單一價格庫取代);未登記者列出報主 agent,不擅自補登記;⑤全庫 >5MB 不入 git(data/ 已 gitignore),只 git add -f README.md、manifest.csv、failed.csv、腳本;⑥生產庫 karst.sqlite 只讀,SHA256 首 16 位維持 b168e9f45b578cf9;⑦報告 research/2026-09-03-單一價格庫盤點.md:覆蓋率(多少段 ok/partial/fail)、日期範圍分佈、與生產庫重疊代號抽 20 個對帳收市價差異、誠實聲明(yfinance 無退市股、除權調整口徑、倖存者口徑)。禁區:不開任何交易介面、不裝付費數據源、不用 MCP 連接器;Chinese 檔案只經 Read/Write/Edit;PYTHONUTF8=1;絕對路徑;PS 5.1 無 &&;不建目錄連結指向 data/。完成:AC 逐格用 Edit 剔 [x],comment 後 close;要人裁的用四格 raise 加 docs 鍵。

## 驗收條件

- [ ] data/universe/universe_smallcap_v1.csv 出,RULES.md 加 v1 規則一節(剔 SIC 6221)
- [ ] data/prices/daily/ 單一價格庫落地,以 entity_id 加代號時段為鍵;README.md、manifest.csv、failed.csv 用 git add -f 入庫;>5MB 檔不入 git
- [ ] 5,952 代號時段抓取完成率 ≥97%(ok+partial),40 個一批加退讓;失敗者重試一次後列 failed.csv
- [ ] 154 家新增價與 6 個未登記檔處理結果寫進報告;research/2026-09-03-單一價格庫盤點.md 含覆蓋率、20 個對帳樣本、誠實聲明
- [ ] 生產庫只讀,SHA256 首 16 位維持 b168e9f45b578cf9;commit 用 git commit --only -F <訊息檔> -- <自己的檔>

## 結果

## 留言
