# Karst 專案守則(2026-09-10 建;每個 session 自動載入,不靠記性)

> 起因:用戶原話「how Claude is managing memory, as i am afraid the project will get lost again like the failure in all the previous Karst project」。本檔用 `@` 匯入把進度正本直接塞進每個 session 的開場 context,主 agent 不用「記得要讀」。

## 開場必讀(自動匯入,勿刪)

@strategy/四類注地圖.md

## 硬規則(本專案)

1. **地圖是唯一進度正本。** 任何「這件事做到哪」的答案以 `strategy/四類注地圖.md` 為準;每輪與用戶討論收線前必須更新對應格,否則不算收線。
2. **向用戶提「新想法 / 新形態 / 要你點頭」之前**,先搜三份正本:`strategy/framework.md`、`strategy/principles.md`、`strategy/candidates.md`,再搜 `.kira/decisions.md` 與各對帳單的對齊紀錄。文件已有的不准當新提案。
3. **開票**必掛 Epic `方法論期(D-166)` 之下五件交付品之一(D05 ①/D06 ②/D07 ③/D08 ④/D04 共用層);Kira 把關會擋掛錯的。
4. **每類收官報四數**(複合年化、最大跌幅、命中率、優勢來源;`principles.md` §三)。
5. 上文被壓縮(compaction)後,第一件事重讀地圖與 HANDOFF §零,不憑摘要行事。

其餘規矩:`HANDOFF.md`(現況與規矩)、`CONTEXT.md`(詞彙表)、`.kira/decisions.md`(已裁決的事)。
