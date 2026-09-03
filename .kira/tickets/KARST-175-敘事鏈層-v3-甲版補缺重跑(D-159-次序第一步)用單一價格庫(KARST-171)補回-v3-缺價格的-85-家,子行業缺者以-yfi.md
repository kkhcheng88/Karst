---
id: KARST-175
title: 敘事鏈層 v3 甲版補缺重跑(D-159 次序第一步):用單一價格庫(KARST-171)補回 v3 缺價格的 85 家,子行業缺者以 yfinance industry 補(只抓缺的),判準、切片、配對、運氣帶、bootstrap 一字照 KARST-170 CRITERIA.md,只重跑甲版(事後表);判詞規則寫死:2023-06-30 切片 cluster bootstrap 95% 置信區間下限 >0 = 甲版存在(進入 D-159 第二步),否則量不出(鏈層降為研究用途);乙版不重跑
type: task
createdAt: 2026-09-03
risk: low
model: opus
fits: yes
dependsOn: []
claimedBy: Claude Opus 5
deliverable: KARST-D02
---

## 工作內容

背景:KARST-170(research/2026-09-03-敘事鏈層存在性v3.md、experiments/2026-09-03-narrative-layers-v3/)甲版 2023 切片解析度倍數 2.82、隨機重貼標籤第 100 百分位,但 cluster bootstrap 95% 置信區間 [−0.001, +0.231] 含 0,差 0.0014;343 家中 85 家無價無子行業(從未進 728 家宇宙,含 META、TTD、S、CORZ、APLD),ai_hpc_hosting 鏈近乎缺席。D-159 裁:價格庫落地後零成本補缺重跑甲版,過線才開乙版新資訊源票。先讀:D-156、D-158、D-159;KARST-170 的 CRITERIA.md、腳本、out/;data/prices/daily/README.md(用 close 加自算調整因子,不直接用 adj_close,D-160);experiments/2026-09-02-chain-layers/chain_membership_v2_2.csv。做法:①CRITERIA_rerun.md 獨立 commit 在任何數字之前:寫明「判準照 v3 一字不改,只換價格來源與補子行業」,並寫死判詞規則(2023 切片置信區間下限 >0 = 存在;否則量不出;2025 切片只作附錄);②價格:全部 343 家改由單一價格庫取(不再混用生產庫與 new_close.parquet),自算調整因子(拆股與股息)並記版本;③子行業:只對缺的公司抓 yfinance info 的 industry(≤85 家,退讓 1.2–2 秒),存 out/industry_fill.csv 附抓取日;④重跑甲版全部四數(解析度倍數、等效獨立層數、可配對數、運氣帶)加 bootstrap 置信區間,兩個切片;⑤與 v3 原數逐項並列(舊、新、差、原因);⑥誠實聲明沿用 v3 六項,加一項:價格來源換了,舊新不完全可比;⑦報告 research/2026-09-03-敘事鏈層v3甲版補缺重跑.md;A-038 若本票足以判,經 Edit 更新 status,否則不動;⑧不重跑乙版,不動 A-042;KARST-170 票不動(留 raised 待用戶)。禁區:不開交易介面、不裝付費源、不用 MCP 連接器;中文檔只經 Read/Write/Edit;PYTHONUTF8=1;絕對路徑;PS 5.1 無 &&;不建目錄連結指向 data/;>5MB 不入 git;生產庫只讀 SHA256 首 16 位維持 b168e9f45b578cf9。完成:AC 逐格用 Edit 剔 [x],comment 後 close;要人裁用四格 raise 加 docs 鍵。

## 驗收條件

- [ ] CRITERIA_rerun.md 凍結並獨立 commit 在任何數字之前;判詞規則寫死
- [ ] 343 家全部改由單一價格庫取價(自算調整因子並記版本);缺子行業者補齊並存 out/industry_fill.csv;可配對數報出
- [ ] 報告:誠實聲明首段、兩切片四數加 bootstrap 置信區間、與 v3 原數逐項並列、判詞只用存在/不存在/量不出
- [ ] 生產庫只讀,SHA256 首 16 位維持 b168e9f45b578cf9;commit 用 git commit --only -F <訊息檔> -- <自己的檔>

## 結果

## 留言
