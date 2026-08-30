---
id: KARST-095
title: 掃描頁測試由整檔跳過改為真跑:臨時庫種一幅完整掃描落檔(批次登記+逐格運行),test_web_sweep.py 全部測試恢復執行
type: task
createdAt: 2026-08-30
risk: low
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-091]
claimedBy: agent-095
epic: V1 建置
deliverable: KARST-D03
---

## 工作內容

源自 KARST-093 收工交低:網頁測試改行臨時庫後,tests/test_web_sweep.py 因臨時庫無掃描落檔而整檔跳過(10 skipped)。完成後:(1) tests/conftest.py 加一個 fixture,經策略執行台 sweep 入口(KARST-091)在臨時庫種一幅小型完整掃描(3×3 格以內,含批次登記與逐格運行、判讀);(2) test_web_sweep.py 全部測試恢復執行並通過,skip 標記移除;(3) 生產庫跑前跑後雜湊不變。不加參數預設值;只跑所涉測試檔;含中文檔案只用 Read/Write/Edit;不建目錄連結指向 data/;不碰 prototype/。

## 驗收條件

- [ ] test_web_sweep.py 零 skipped、全部通過;生產庫雜湊跑前跑後相同
- [ ] fixture 經執行台 sweep 種數,不直接寫庫
- [ ] 只跑所涉測試檔

## 結果

## 留言
