---
id: KARST-051
title: 參數掃描頁(真數據):熱力圖、小倍數、切片、鄰域與分層判讀
type: task
createdAt: 2026-08-28
risk: low
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-048]
claimedBy: null
epic: V1 建置
deliverable: KARST-D03
---

## 工作內容

用戶自此可以在畫面上看掃描結果,而不是開 CSV:照原型第十版 prototype/sweep.html 實作熱力圖、小倍數、切片、鄰域;數據經薄 REST 層讀真實掃描表與判讀表(含 KARST-047/048 的軸型、分層、山脊與孤峰標記)。選擇軸以分層切換呈現,連續軸畫熱力圖。畫面三態照原型。不含從畫面發起重掃(另票)。不改設計決定。

## 驗收條件

- [ ] 參數掃描頁四個元件由真實掃描表與判讀表畫出,孤峰/山脊/平原標記可見
- [ ] 選擇軸可切層,熱力圖只沿連續軸畫
- [ ] 載入中/空/錯誤三態齊全
- [ ] 既有頁面行為不變,既有測試全過

## 結果

## 留言
