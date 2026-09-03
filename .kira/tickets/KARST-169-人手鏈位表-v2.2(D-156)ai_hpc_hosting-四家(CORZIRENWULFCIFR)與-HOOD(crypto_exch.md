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
closed: 2026-09-03
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

### agent:narr-v3-170 · 2026-09-03 08:24
v2.2 交付。353 行、65 條鏈、343 家;v0 / v1 / v2 / v2.1 一字不改。commit ef4f012。

**轉向日判準(查證之前寫死)**:取首次公開宣佈 AI/HPC 客戶合約的當日。只宣佈買 GPU、只宣佈策略、只講「potential HPC tenants」而未有客戶合約的,不算。這條判準令四個日期全部**精確到日而且事前可得**——公佈當日 8-K / 6-K 連新聞稿一齊出,不需要等年報倒推。這一點與 v2.1 的 ORCL 不同(那個是由 2024 年才公開的年報倒推)。

| 公司 | 轉向日 | 那一日公佈了什麼 | 出處 |
|---|---|---|---|
| IREN | 2024-02-08 | 與 poolside AI 的 GPU 雲服務合約正式開始(248 顆 H100) | 6-K 0001140361-24-006216 |
| CORZ | 2024-03-06 | 與 CoreWeave 多年期合約,供應最多 16MW 機位 | 8-K 0001628280-24-009396(Item 7.01)連新聞稿 |
| WULF | 2024-12-23 | 與 Core42(G42 旗下)長期資料中心租約,逾 70MW | 8-K 0000950142-24-002980(Item 8.01) |
| CIFR | 2025-09-25 | 子公司與 Fluidstack 十年期資料中心租約,Google 作後盾 | 8-K 0000950103-25-012168(Item 1.01) |

四家各補回 `crypto_mining` 一行(valid_to = 轉向日),`ai_hpc_hosting` 那一行的 valid_from 改為同日。三個被判為「不算轉向」的邊界個案,判詞連原文都寫在 `v22_switch_basis` 欄:IREN 2023-08-29 買 H100 那份新聞稿自己寫「Core business remains Bitcoin mining」;WULF FY2023 10-K 自己寫「the Company only operated bitcoin mining facilities」;CIFR FY2024 10-K 講 HPC 講了 73 次但全部是「potential HPC tenants」。

**HOOD:日期核實過,不改;但查到 v2 一句判詞是錯的。** `crypto_exchange` 的 valid_from 維持 2022-01-01——走廊起點之前它已在做加密交易,而且由第一份年報(FY2021)起就把加密交易收入單獨列一行,所以這不是前視日期,是走廊起點本身。但 v2 / v2.1 的 purity 欄寫住「2024 年起加密交易佔交易收入主體」,年報數字不支持:

| | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---:|---:|---:|---:|---:|
| 加密交易占總淨收入 | 23% | 15% | 7% | 21% | 20% |
| 期權 | 38% | 36% | 27% | 26% | 25% |

**每一年期權都比加密大**,加密從來沒有做過主體;而且它由 23% 跌到 7% 再升回 21%,是隨幣市週期上落,不是一次轉向。那一句已改寫。順帶記低一件本票沒有做的事:這其實在問「HOOD 究竟是不是 crypto_exchange 這一層的乾淨成員」,本票按票面只核實日期、沒有按四條出隊規則重判。反正 `crypto_exchange` 名冊只有兩家,本來已在「名冊不足五家」那 16 條鏈之內。

**連帶改動**:三條鏈的逐鏈共用 `purity_note`(`crypto_mining`、`ai_hpc_hosting`、`crypto_exchange`)在 v2.2 已不成立,已改寫,涉 7 行。做法與 v2.1 改 `software_cloud` 那一句相同,已在文件與驗收條件明列。

**逐行對帳**(`build_v2_2.py` 內建,不過就報錯):v2.1 的 349 行之中 337 行逐格相同、7 行只改了 purity_note、5 行在准許改動清單上;新增 4 行;**報錯 0**。

**資料衛生**:新抓年報 10 份(CORZ 3、WULF 3、CIFR 3、IREN 1),只入 `data/sec/10k_text` 共用快取連 manifest,`fetchedBy: KARST-169`,EDGAR ≤8 req/s。公告類申報(8-K / 6-K / 20-F)不是年報,按該快取 README「現時全部是 10-K」沒有入快取,只在 `out_v2_2/evidence_index.json` 留 URL 索引,原文中間物不入 git。沒有碰 `data/sec/submissions/` 與 `data/universe/`(KARST-167 隊在寫)。生產庫只讀,SHA256 首 16 位維持 `b168e9f45b578cf9`。

**未做,留給後續**:①`ai_hpc_hosting` 的 APLD 仍是 2022-01-01,同一類前視問題,票面沒有點名;②HOOD 的成員資格未按四條出隊規則重判;③`chain_membership` 由 v2 起就有一組重複鍵(`WDC` 在 `memory` 出現兩行),本票不動,但用表的人要知道。
