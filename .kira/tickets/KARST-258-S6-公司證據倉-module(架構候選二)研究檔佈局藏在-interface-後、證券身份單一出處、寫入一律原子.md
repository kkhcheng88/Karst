---
id: KARST-258
title: S6 公司證據倉 module(架構候選二):研究檔佈局藏在 interface 後、證券身份單一出處、寫入一律原子
type: task
createdAt: 2026-09-23
risk: high
model: opus
fits: 一程(大):證據倉 interface 及八個以上呼叫模組改接;超出則按讀／寫拆
dependsOn: [KARST-254]
claimedBy: null
epic: 根基重整
deliverable: KARST-D12
---

## 工作內容

依執行計劃 §三 6 及架構評審候選二。現況八個以上 module 直接讀寫 packet.json／evidence.json,evidence.json 退路寫四次另兩處漏寫;證券身份存於 packet.json 與 store entity 兩處,render_charts 從 title 字串切出 exchange;packet.json 有非原子寫入。建立證據倉 module,呼叫方不再知道檔案佈局;證券身份單一出處;所有寫入原子。既有雲端 /data 內容須原樣可讀,不做資料遷移或只做可回退的遷移。程式只住 karst/。

## 驗收條件

- [ ] karst/ 內除證據倉 module 外沒有直接開 packet.json／evidence.json 的程式
- [ ] exchange 不再從 title 字串推出
- [ ] 所有寫入經原子寫入
- [ ] 以現有雲端資料格式的 fixture 驗證讀取不變;既有全套測試通過

## 結果

## 留言
