---
id: KARST-262
title: S10 增量範圍控制:更新任務帶明確重評範圍,保存時系統沿用範圍外各層、擋未聲明的越界修改、範圍內每層須有已審證明,並記層級變更來源
type: task
createdAt: 2026-09-23
risk: high
model: opus
fits: 一程(大):更新範圍物件、收件閘、沿用與審閱證明、過期強制入範圍;超出則按收件閘／過期規則拆
dependsOn: [KARST-256, KARST-257, KARST-259]
claimedBy: null
epic: 根基重整
deliverable: KARST-D12
---

## 工作內容

依執行計劃 §二「增量建置」。用戶 2026-09-23 問:「this also introduced that whether the daily incremental process can really have the scope and update control?」。現況:updates.plan 的 affected_layers 只是建議(karst/README 明寫「是分流範圍……均不是投資結論」);更新保存時模型交整份研究,可改任何一層;唯一機制是某層與前版逐字相同就保留 assessed_at(agents/research.py 約 222 行);跨 packet 沿用證明只有設計(strategy/specs/補查與增量重評路由-v1.md),未實作(agents/README.md 約 115 行)。要交:(1) 更新範圍物件:每個更新任務帶前版 version_id、允許改動的層、觸發來源(價格事件／來源 ID／日更快照 ID);(2) 範圍外各層由系統從前版原樣沿用(含 assessed_at、read_evidence_ids),模型不重交,亦節省 token;(3) 模型改範圍外的層須聲明擴大範圍及理由(保留「任何舊分析錯誤均可修訂」),否則收件拒絕;(4) 範圍內每層須是「已改」或「已審未改」並列出本次讀過的證據,不接受無聲照抄;(5) 每個研究版本記層級變更來源表:層 → 觸發 → 前版;(6) 沿用層有最長年齡或事件失效條件(例如下次業績日已過仍沿用 L3),到期強制納入範圍;(7) 閱讀頁及 get_research_context 顯示各層評估日期與是否沿用。經 KARST-259 收件 module 實作。程式只住 karst/,代號與日期由參數傳入,不寫一次性腳本(D-180)。

## 驗收條件

- [ ] 純價格事件更新只准改 L4 現價部分、L5、L6;模型改 L3 而未聲明擴大範圍時收件拒絕,聲明後接受並記理由
- [ ] 範圍外各層由系統沿用,與前版逐欄相同(含 assessed_at 與證據 ID),有定向測試
- [ ] 範圍內某層無改動亦無已審證明時收件拒絕
- [ ] 研究版本讀回可見層級變更來源表
- [ ] 沿用層超過年齡或事件失效時,下一次更新任務自動把該層納入範圍
- [ ] 既有研究版本讀回、HTTP 及收件測試全部通過;既有已發布研究不變

## 結果

## 留言
