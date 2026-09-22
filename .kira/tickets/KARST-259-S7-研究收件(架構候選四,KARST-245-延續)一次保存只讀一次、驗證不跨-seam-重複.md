---
id: KARST-259
title: S7 研究收件(架構候選四,KARST-245 延續):一次保存只讀一次、驗證不跨 seam 重複
type: task
createdAt: 2026-09-23
risk: high
model: opus
fits: 一程:service 收件段與 agents/research.py
dependsOn: [KARST-258]
claimedBy: null
epic: 根基重整
deliverable: KARST-D12
---

## 工作內容

依執行計劃 §三 7 及架構評審候選四。現況一次保存跨四個 module,packet.json 讀三次、中途改寫一次,驗證指紋憑證因驗證跨 seam 重複而存在;另有 ImportError 退路與注入 intake 簽名不一致。收件收攏為一個 module,經 S6 證據倉讀寫。已保存研究版本與計算回執的讀回結果不變。程式只住 karst/。

## 驗收條件

- [ ] 一次保存 packet 只讀一次
- [ ] ImportError 退路移除,注入 intake 簽名一致
- [ ] 既有研究收件、版本讀回、HTTP 測試全部通過
- [ ] 以既有 fixture 保存同一研究,版本 ID 與回執與重構前相同

## 結果

## 留言
