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
closed: 2026-08-30
---

## 工作內容

源自 KARST-093 收工交低:網頁測試改行臨時庫後,tests/test_web_sweep.py 因臨時庫無掃描落檔而整檔跳過(10 skipped)。完成後:(1) tests/conftest.py 加一個 fixture,經策略執行台 sweep 入口(KARST-091)在臨時庫種一幅小型完整掃描(3×3 格以內,含批次登記與逐格運行、判讀);(2) test_web_sweep.py 全部測試恢復執行並通過,skip 標記移除;(3) 生產庫跑前跑後雜湊不變。不加參數預設值;只跑所涉測試檔;含中文檔案只用 Read/Write/Edit;不建目錄連結指向 data/;不碰 prototype/。

## 驗收條件

- [x] test_web_sweep.py 零 skipped、全部通過;生產庫雜湊跑前跑後相同
- [x] fixture 經執行台 sweep 種數,不直接寫庫
- [x] 只跑所涉測試檔

## 結果

· 2026-08-30 13:16 test_web_sweep.py 5 個測試(原 10 個 skipped)全部改為真跑並通過,
  零 skipped。新增 tests/conftest.py 的 seeded_sweep fixture,經 Executor.sweep
  (KARST-091 入口)在臨時專案根種一幅 3×3=9 格完整掃描(mode 選擇軸 × x 連續軸),
  批次登記、逐格運行、判讀一次過經唯一入口落檔;假引擎沿用 tests/doubles/engines.py
  的 RecordingEngine 子類化。生產庫 karst.sqlite 雜湊跑前跑後相同(緊貼測試指令前後
  各量一次,排除同倉其他並行工作的干擾):
  f5a4a929d44371a494f9cff55dfbe1c76596dc23dab0cedb20aaa7c741c95e44。詳細改動與測試
  內容變更說明見留言。

## 留言

### agent:agent-095 · 2026-08-30 13:17
完成情況與改動說明(agent-095):

1) tests/conftest.py 新增 seeded_sweep fixture(session scope):經 Executor.sweep(KARST-091 的執行台第二入口)在 seeded_project_root 這個臨時專案根種一幅 3×3=9 格的完整掃描——mode(選擇軸,A/B/C)× x(連續軸,1/2/3),批次登記、逐格運行、判讀一次過經唯一入口落檔,不直接寫庫。假引擎是 tests/doubles/engines.py 的 RecordingEngine 子類化(_SweepFixtureEngine),按票文要求沿用既有假引擎而非另起一套。九格逐格的目標年化回報刻意排過,令平原、山脊、孤峰三種裁決在同一幅掃描裡全部出現,因為驗收條件一要驗『三個裁決標記都真的有格拿得到』。

2) test_web_sweep.py 移除全部 skip 標記,5 個測試(原 10 個 skipped)全部改為真跑並通過。過程中順手修正一個原本被整檔跳過所以沒暴露出來的舊 bug:test_四個元件由真實掃描表與判讀表畫出 原本用 PROJECT_ROOT(倉根)去拼 CSV 路徑,但掃描落檔其實在 seeded_project_root(KARST-093 把讀取層接離生產庫之後就搬去了臨時專案根),兩者不是同一個目錄,一旦真的discover到掃描就會拼錯路徑、讀不到檔。已改為從 seeded_project_root 拼路徑,並在函式簽名加了這個參數;reader fixture 也加了 seeded_sweep 依賴,確保掃描先種好再起讀取層。其餘 4 個測試的斷言邏輯未改動,只是不再被跳過。

3) 生產庫 karst.sqlite 雜湊跑前跑後相同:緊貼 pytest 指令前後各量一次(排除同倉並行工作對長時段前後量測的干擾),兩次都是 f5a4a929d44371a494f9cff55dfbe1c76596dc23dab0cedb20aaa7c741c95e44,證明這個 fixture 全程只寫臨時庫,沒有碰過生產庫。

只跑了 tests/test_web_sweep.py,沒有動 karst/ 或 prototype/。留待人手過目簽收。
