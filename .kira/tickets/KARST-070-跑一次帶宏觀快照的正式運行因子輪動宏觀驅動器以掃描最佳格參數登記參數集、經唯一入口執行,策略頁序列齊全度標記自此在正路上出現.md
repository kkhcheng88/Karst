---
id: KARST-070
title: 跑一次帶宏觀快照的正式運行:因子輪動宏觀驅動器以掃描最佳格參數登記參數集、經唯一入口執行,策略頁序列齊全度標記自此在正路上出現
type: task
createdAt: 2026-08-29
risk: low
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-067]
claimedBy: null
closed: 2026-08-29
epic: V1 建置
deliverable: KARST-D03
---

## 工作內容

KARST-067 指出庫內沒有一次帶宏觀快照的正式運行(只有掃描格),策略頁新加的「序列齊全度」標記在正路上見不到。範圍:從 experiments/2026-08-28-macro-rejudge/ 的最佳格取一組宏觀驅動器參數,經唯一入口登記為參數集(名稱註明示例與來源掃描編號)、以現役宏觀快照 2026-08-28-dc2d9f1a1778 執行一次正式運行(來歷 FORMAL_RUN);把運行編號與參數集版本一併寫入 experiments/2026-08-28-macro-drivers/README.md 與 D02 摘要示例運行一行(A-009 教訓:編號要連參數集版本)。瀏覽器實開策略頁核對標記出現。不改引擎、不改策略、不加參數預設值;只跑所涉測試檔。

## 驗收條件

- [x] 一次因子輪動宏觀驅動器正式運行入庫,運行編號與參數集版本落檔
- [x] 策略頁在該策略正路上顯示序列齊全度標記(截圖或文字核對落檔)
- [x] karst verify 清白;只跑所涉測試檔

## 結果

取 `experiments/2026-08-28-macro-rejudge/` 按軸型重判之後最高、且鄰域真站得住的一格
(曲線斜度變化方向,`lookback_days=20、tilt=1、cadence=monthly`,來源掃描編號
`experiments/2026-08-28-macro-drivers/mac-curve_trend`),經唯一入口
(`gateway.register_param_set`)登記參數集**「示例正式-KARST-070-來源mac-curve_trend」
第 1 版**,以現役宏觀快照 `2026-08-28-dc2d9f1a1778` 執行一次正式運行(來歷
`FORMAL_RUN`,不經掃描跑法)。**運行編號 `run-924a54eb843f0988`**(策略「因子輪動
(ETF 版)」第 2 版 × 上述參數集 × 2015-01-02~2026-08-26 × 價格快照
`2026-08-28-000b4820a23a` × 引擎 vectorbt 0.1.0;逐日序列核對「全對」)。成績對 SPY
年化超額 +5.3712%,與來源掃描格逐位相同(同一組取值理應撞出同一個數,差別只在
來歷從 `sweep` 換成 `formal`)。此前「因子輪動(ETF 版)」策略正式運行數為 0
(KARST-067 已指出),現為 1。

以 `python -m karst.web --port 8767` 開臨時伺服器核對(過程中曾誤撞用戶已開在
8765 那個埠,已即時停掉自己那一個,確認未動用戶那邊):`/api/overview` 該策略
`runCount` 由 0 變 1;`/api/strategy?id=3` 的 `defaultRunId` 就是這次運行,策略正路
(不帶 `?run=`)已看得到,不用再靠 KARST-067 那條「只帶 `?run=`」的網址催;
`/api/runs/run-924a54eb843f0988` 的 `paramValues.macro_snapshot` 帶住現役宏觀快照
編號;`/api/macro/completeness?snapshot=2026-08-28-dc2d9f1a1778` 回 14 條序列、
`worstStaleDays: 0`——即策略頁會顯示「序列齊全度 14 條・尾段貼齊主日曆」。核對
完即關閉臨時伺服器。文字核對落
`experiments/2026-08-28-macro-drivers/formal-run-2026-08-29.md`。

`karst verify` 全庫清白。本票未改任何引擎、策略或掃描碼(只加一支跑法腳本
`run_formal_run.py`,呼叫既有的 `run_factor_rotation`/`record_factor_rotation_run`),
無新增測試,未跑測試檔。

運行編號與參數集版本已寫入 `experiments/2026-08-28-macro-drivers/README.md`(新增
7.1 節)與 `.kira/deliverables/KARST-D02.md` 示例運行一行(A-009 教訓:編號連參數
集版本一併寫明)。

## 留言
