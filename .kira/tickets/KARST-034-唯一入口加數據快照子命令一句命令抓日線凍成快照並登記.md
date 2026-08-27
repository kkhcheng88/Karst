---
id: KARST-034
title: 唯一入口加數據快照子命令:一句命令抓日線凍成快照並登記
type: task
createdAt: 2026-08-28
risk: low
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-027, KARST-022]
claimedBy: null
epic: V1 建置
deliverable: KARST-D02
---

## 工作內容

數據快照自此經唯一入口產生:一句 karst data snapshot 命令指定宇宙與窗口,即抓日線、凍成快照、登記編號並印出來。KARST-027 收檔時快照只能寫 Python 呼叫程式產生,不符 D-020「人手、本地 agent、日後內嵌 agent 同一道門」。範圍只是把既有管線接上命令列,不改管線本身;抓取時間(fetched_at)要在登記表查得到。

## 驗收條件

- [ ] karst data snapshot 一句命令完成抓取、凍結、登記,並印出快照編號(真實抓取,離線自動略過)
- [ ] 登記表直接查得到該快照的抓取時間與來源
- [ ] karst data list 列得出庫內全部快照(編號、窗口、實體數、抓取時間)
- [ ] 不繞過 karst/store.py 開連線(D-027)

## 結果

## 留言
