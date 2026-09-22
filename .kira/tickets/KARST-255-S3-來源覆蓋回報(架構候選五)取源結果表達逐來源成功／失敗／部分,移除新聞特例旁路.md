---
id: KARST-255
title: S3 來源覆蓋回報(架構候選五):取源結果表達逐來源成功／失敗／部分,移除新聞特例旁路
type: task
createdAt: 2026-09-23
risk: medium
model: opus
fits: 一程:fetch port 的回報形狀、news adapter、service 與 daily 的覆蓋判斷
dependsOn: []
claimedBy: null
epic: 根基重整
deliverable: KARST-D12
---

## 工作內容

依執行計劃 §三 3 及架構評審候選五。現況 LandedRecord 表達不到部分 feed 成功,新聞覆蓋靠 coverage.json 側檔,service 內有 if adapter == 'news_rss' 特例,daily 由四個欄位拼出取源是否完整。改為每個 adapter 回報逐來源覆蓋(ok／failed／partial 及原因),service 與 daily 只讀這一份覆蓋回報判斷完整性。不改證據內容與指紋。程式只住 karst/。

## 驗收條件

- [ ] service 內沒有按 adapter 名稱的特例分支
- [ ] daily 的「取源是否完整」只由覆蓋回報一處決定
- [ ] 兩個 RSS 其中一個失敗時,回報為 partial 並列出失敗來源;全部失敗不得當作無新聞
- [ ] 既有 fetch／daily／service 測試通過,新增部分成功的定向測試

## 結果

## 留言
