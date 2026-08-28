---
id: KARST-063
title: Alpha158 因子計算:照公開公式自寫 pandas 版本(不裝 qlib),在起步宇宙 12 隻上算出全部 158 條並對照官方數值抽查
type: task
createdAt: 2026-08-29
risk: low
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-062]
claimedBy: null
epic: V1 建置
deliverable: KARST-D03
---

## 工作內容

依 research/2026-08-29-alpha158-feasibility.md 第一、二節與用戶 2026-08-29 裁決(四張票同時開)。範圍:新模組(建議 karst/factors/alpha158.py)以 pandas 實作 Alpha158 全部表達式——K 線形態組、價格組、成交量組、滾動窗口組(28 種運算子 × 5/10/20/30/60 日);輸入是現有 K 線面板(日線開高低收量),輸出是「日期 × 實體 × 因子名」長表,只算不入庫。第一步先跑一次 qlib 的 get_feature_config() 核實 158 條逐組確切條數並記入模組說明。牽涉成交均價的幾條用近似值並在模組說明列明。測試:小樣本(兩三隻股票、短窗)對照公開的 qlib 官方公式抽查至少十條因子數值;只跑自己新增的測試檔。不裝 qlib 為運行依賴(核實條數可用臨時環境)。不加參數預設值。

## 驗收條件

- [ ] 158 條因子在起步宇宙 12 隻上全部算得出,逐組條數與 qlib 官方核實一致並寫入模組說明
- [ ] 至少十條因子小樣本數值與公開定義對照一致(測試檔),近似處理的條目列明
- [ ] 只新增模組與測試,不動因子表、不動唯一入口、不跑全庫測試

## 結果

## 留言
