---
id: KARST-169
title: 人手鏈位表 v2.2(D-156):ai_hpc_hosting 四家(CORZ/IREN/WULF/CIFR)與 HOOD(crypto_exchange)按換鏈日期改記——2024 年才由挖礦轉 AI 託管的成員,舊鏈 crypto_mining 填 valid_to、新鏈 ai_hpc_hosting 填 valid_from,各附年報或公告佐證;HOOD 加密交易所位置的 valid_from 同樣核實;其餘 v2.1 一字不改;交主 agent 收貨後作 v3 量度正本
type: task
createdAt: 2026-09-03
risk: low
model: opus
fits: yes
dependsOn: []
claimedBy: narr-v3-170
deliverable: KARST-D02
---

## 工作內容

背景:KARST-168 交付 v2.1(experiments/2026-09-02-chain-layers/chain_membership_v2_1.csv、chain_stories_v2_1.md、removed_v2_1.csv、build_v2_1.py),並指出 ai_hpc_hosting 四家與 HOOD 仍帶同類前視問題(valid_from 填 2022 年初,但那條敘事 2024 年才存在)。先讀 D-151、D-152、D-156,CONTEXT.md「換鏈日期」,chain_stories_v2_1.md 的 v2.1 變更一節與 ai_hpc_hosting、crypto_exchange 兩鏈段落。做法:①四家礦商:找每家首次公開 AI/HPC 託管合約或轉型公告的月份(年報快取 data/sec/10k_text 優先,缺才抓 EDGAR,每秒 ≤10、User-Agent `Casy Limited kaho.career@gmail.com`、抓前查 manifest、fetchedBy 填票號;公告日可用 8-K 或新聞,附來源),舊鏈 crypto_mining 一行 valid_to=該日、新鏈 ai_hpc_hosting 一行 valid_from=同日;查不到精確月份填近似並標記;②HOOD:核實它在 crypto_exchange 的入位日(加密交易收入首次單獨披露或占比顯著的年報),同樣改記;③另出 chain_membership_v2_2.csv(UTF-8 BOM)、chain_stories_v2_2.md(只加「v2.2 變更」一節,聲明衝突以該節與 csv 為準)、removed_v2_2.csv(與 v2.1 相同則照抄並註明);build_v2_2.py 逐行對帳(v2.1 每行不是被承接就是在改動清單,否則報錯);④v0/v1/v2/v2.1 一字不改;⑤誠實聲明沿用 v2 四項加一項:轉向日由後來公開的文件倒推,帶前視。

## 驗收條件

- [x] chain_membership_v2_2.csv:CORZ/IREN/WULF/CIFR 各有 crypto_mining(valid_to)與 ai_hpc_hosting(valid_from)兩行,同日,附佐證;HOOD 的 crypto_exchange valid_from 核實並附佐證;其餘行與 v2.1 逐格相同(**一處例外,已明列**:crypto_mining / ai_hpc_hosting / crypto_exchange 三條鏈的逐鏈共用 `purity_note` 有連帶改動,涉 7 行;做法與 v2.1 改 `software_cloud` 那一句相同)
- [x] chain_stories_v2_2.md 有「v2.2 變更」一節逐行列改動與佐證;build_v2_2.py 對帳通過(337 逐格相同 / 7 只改 purity_note / 5 准許改動 / 新增 4 / 報錯 0)
- [x] 新抓年報只入單一快取連 manifest;生產庫只讀,SHA256 首 16 位維持 b168e9f45b578cf9
- [x] commit 用 git commit --only -F <訊息檔> -- <自己的檔>;票上 comment 後 close

## 結果

## 留言
