---
id: KARST-029
title: 參數掃描與穩健平原報告
type: task
createdAt: 2026-08-27
risk: low
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-026, KARST-030, KARST-031]
claimedBy: KARST-029-sweep
epic: V1 建置
deliverable: KARST-D02
---

## 工作內容

掃一格參數自此交得出一份判得出真假的報告:熱力圖畫得出,平原與孤峰分得開,成交太少的格判無效。判準是參數穩健平原(parameter robustness plateau)——最優參數的鄰域表現皆佳才算穩健,孤峰視為擬合噪音(D-016 第 3 條、規格 6.5)。範圍是掃描的執行與報告產出;KARST-013 已實跑過一次 144 組示範(單點最優夏普 1.61 但 3×3 鄰域平均只有 1.16,按此判為孤峰),本票是把那次一次性的示範做成可重複使用的能力。本票不裁定哪組參數該用,那是用戶的領域(D-008)。

## 驗收條件

- [ ] 一次掃描交得出熱力圖,而且單點最優與其 3×3 鄰域平均兩個數同時列出(規格 6.5)
- [ ] 峰值明顯高於鄰域平均的格被明文標為孤峰、判為擬合噪音(D-016 第 3 條)
- [ ] 成交筆數低於門檻的格判為無效並在圖上區分得到,門檻值寫得出(規格 6.5)
- [ ] 報告指得回它掃的是哪一次運行設定:策略版本 × 期間 × 數據快照(規格 7.4)

## 結果

## 留言

· 2026-08-28 fable-main 前置改為 KARST-026/030/031,不再等趨勢波段(028):用戶 2026-08-28 明令首個掃描對象是因子混合策略的權重矩陣,原話「I think 因子混合策略 is not just 25% each ... with matrix-like of running, I would like to know what is the best driver to move between 4 to get the best portfolio just with the 4 ... I don't mind overfitting at first」。本票做通用掃描能力並以四隻因子 ETF 的權重格(單純形格,步長由參數指定)為首個實跑;趨勢波段掃描待 028 落地後由同一套能力跑。「驅動器」(按訊號在四者之間動態移權)另開票 KARST-036。
