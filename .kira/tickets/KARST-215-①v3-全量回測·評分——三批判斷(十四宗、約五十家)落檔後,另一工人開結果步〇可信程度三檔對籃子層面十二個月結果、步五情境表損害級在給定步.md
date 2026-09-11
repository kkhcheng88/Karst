---
id: KARST-215
title: ①v3 全量回測·評分——三批判斷(十四宗、約五十家)落檔後,另一工人開結果:步〇可信程度三檔對籃子層面十二個月結果、步五情境表損害級在給定步〇之下對個股相對籃子中位結果、步六至七判詞與必要前提對結果;與 v1(204)、v2.1(210)同家對比;答「v3 的殺的條件評估分不分得開、哪一步分得開、要改什麼」
type: research
createdAt: 2026-09-11
risk: low
model: opus
fits: 用戶 2026-09-11 原話「I need backtest」;執行口徑第四節;KARST-212/213/214 前置
dependsOn: [KARST-212, KARST-213, KARST-214]
claimedBy: null
epic: 方法論期(D-166)
deliverable: KARST-D05
---

## 工作內容

前置三批全部收檔。只讀三批的 判-E*.csv、步〇-E*.md、卡-E*.md(可讀判詞)與 199 的 out/basket_members.csv 結果欄;照執行口徑第四節出五張表(步〇 × 籃子結果、步五 × 個股相對籃中位分兩組、q1_verdict × 結果、必要前提 × 結果、與 204/210 同家對比),秩相關與方向為主,n 小不作定論;抽查每批兩家引用回原文。結論業務語言:v3 的「殺的條件」評估分不分得開;哪一步分得開、哪一步分不開;v1→v2.1→v3 方向變化;要改什麼。落檔 評分/(評分表.md/.csv、score.py、總覽——①v3全量回測.md 整體)。含中文檔案只用 Read/Write/Edit;Python 一律 PYTHONUTF8=1;不改三批與既有輸出;不 commit。

## 驗收條件

- [ ] 五張評分表落檔,秩相關與方向為主;抽查引用結果落檔
- [ ] 業務語言結論:哪一步分得開、哪一步分不開、v1→v2.1→v3 方向、要改什麼
- [ ] 不改三批與既有輸出、karst/ strategy/ library/;含中文檔案只用 Read/Write/Edit;Python 一律 PYTHONUTF8=1;不 commit

## 結果

## 留言
