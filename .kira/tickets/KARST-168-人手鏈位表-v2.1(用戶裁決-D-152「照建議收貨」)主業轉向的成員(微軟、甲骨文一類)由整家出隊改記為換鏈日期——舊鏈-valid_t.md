---
id: KARST-168
title: 人手鏈位表 v2.1(用戶裁決 D-152「照建議收貨」):主業轉向的成員(微軟、甲骨文一類)由整家出隊改記為換鏈日期——舊鏈 valid_to、新鏈 valid_from 各填轉向日並附年報或公告佐證,令切片日期前的樣本仍可用;逐一覆核 removed_v2.csv 的 23 行哪些屬「主業轉向」哪些屬真出隊;其餘 v2 內容一字不改;交主 agent 收貨後作 v3 量度的正本
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

背景:KARST-161 交付 v2(experiments/2026-09-02-chain-layers/chain_membership_v2.csv、chain_stories_v2.md、removed_v2.csv),用戶已裁照建議收貨(D-152),其中一項建議是主業轉向不整家出隊、改記換鏈日期(D-151 ③)。先讀 D-147、D-151、D-152,chain_stories_v2.md 的誠實聲明與出隊規則,removed_v2.csv 全部 23 行。做法:①逐行判 23 行出隊理由:規則 d「主業已轉向」的(至少 MSFT、ORCL,可能還有其他)改為兩行——舊鏈一行 valid_to=轉向日、新鏈一行 valid_from=同日,轉向日以年報或公告可查的事件為準(例如微軟 2023 年 1 月宣布 OpenAI 追加投資、甲骨文 2023 年 9 月 OCI 收入首次單獨披露),查不到填近似並標記;②其他規則(位置不同、單一資產主導、無可比公司)維持出隊;③v2 檔不改,另出 chain_membership_v2_1.csv、chain_stories_v2_1.md(只加一節「v2.1 變更」列每一行改動與佐證)、removed_v2_1.csv;④年報佐證從 data/sec/10k_text 快取讀,缺才抓(每秒 ≤10、User-Agent `Casy Limited kaho.career@gmail.com`、抓前查 manifest,fetchedBy 填票號);⑤誠實聲明沿用 v2 四項;⑥收工在票上 comment 結果並 close,不需用戶審(用戶已裁方向)。

## 驗收條件

- [ ] chain_membership_v2_1.csv:主業轉向成員以換鏈日期呈現(舊鏈 valid_to + 新鏈 valid_from 同日),每行附佐證來源;v2 檔一字不改
- [ ] chain_stories_v2_1.md 有「v2.1 變更」一節逐行列改動;removed_v2_1.csv 只剩真出隊
- [ ] 新抓年報只入單一快取連 manifest;生產庫只讀,SHA256 首 16 位維持 b168e9f45b578cf9
- [ ] commit 用 git commit --only -F <訊息檔> -- <自己的檔>;票上 comment 後 close

## 結果

## 留言
