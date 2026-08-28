---
id: KARST-046
title: 「同名同值沿用舊版」收歸唯一入口一處,策略層兩份相同實作刪走
type: task
createdAt: 2026-08-28
risk: low
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-041]
claimedBy: null
closed: 2026-08-28
epic: V1 建置
deliverable: KARST-D02
---

## 工作內容

參數集「同名、同節奏、同取值即沿用舊版」這條規則自此全倉只有一份,住在唯一入口的登記服務;任何策略登記參數集都自動得到這個行為。KARST-041 指出趨勢波段與因子混合各抄了一份逐字相同的實作,違反單一定義;KARST-041 亦指出 karst/sweep/factor_mix.py 那道「先查一句」已多餘。範圍只是搬位與刪重複,不改行為。

## 驗收條件

- [x] 唯一入口登記參數集時自動沿用同名同節奏同取值的舊版,策略層查不到第二份同樣邏輯
- [x] karst/sweep/factor_mix.py 多餘的先查步驟刪走
- [x] 既有測試全過,兩個示例運行編號不變

## 結果

· 2026-08-28 09:43 「同名、同節奏、同取值即沿用舊版」搬入 `Gateway.register_param_set`
(`karst/gateway/service.py`),策略層兩份逐字相同的 `_existing_param_set` 刪走。純粹
搬位與刪重複,公開簽名一個字不變。

逐項對驗收條件:

- **入口自動沿用,策略層無第二份** —— 入口先查同名參數集,節奏與取值(一律按庫層
  寫法收成文字再比)全中就回舊那一列,**一個字都不寫**。因為沒有寫,亦不蓋新簽章:
  收據回的是那一列本來就有的簽章,所以繞過入口寫入的列不會被沿用這一步補一個簽章
  把痕跡蓋走,`verify` 照樣揪得到。`karst/strategies/trend_swing.py` 與
  `karst/strategies/factor_mix.py` 的 `_existing_param_set` 連同已無用的 `NotFound`
  匯入一併刪走,兩處改為直接叫入口。
  測試:`tests/test_gateway.py::test_the_gateway_itself_reuses_the_same_name_cadence_and_values`
  (同一組登記兩次回同一列、`created_at` 不變、簽章不變、取值寫數字一樣認得;節奏
  不同或取值不同照樣出新版)與 `::test_the_strategy_layer_keeps_no_second_copy_of_the_reuse_rule`
  (三個模組都查不到 `_existing_param_set`,連比對那兩句都不再出現)。
- **掃描層多餘的先查刪走** —— 兩處:`ensure_factor_mix_setup` 開頭那道「先查參數集
  在不在」,以及 `FactorMixJob._param_set` 裡同一套先查。順帶執正一件事:舊那道先查
  只認**名**,同名而權重不同一樣早走,於是改了權重的設定參數集寫不入去;現在照直交
  去入口,取值不同就照樣出新版。`param_sets_written` 要繼續數得準,所以 `WriteReceipt`
  加一格 `reused`(有預設值,不影響既有呼叫),掃描按它決定加不加一。
  測試:`tests/test_engine_costs.py::test_the_sweep_registers_straight_through_the_gateway`。
- **既有測試全過,示例運行編號不變** —— `test_factor_mix.py` 原有的 KARST-041 沿用測試
  全部照過(現在走的是入口那條路)。兩個示例運行重跑:`run-f4c162e5aac34347` 與
  `run-728a01087531258f` 編號不變,腳本自己核對「一字不差」,兩個 `summary.json` 經
  git 核對逐位相同。

## 留言

· 2026-08-28 09:43 `karst/sweep/factor_rotation.py` 裡有第三份同樣的先查(`_param_set`
第 258 行起)。本票沒有動它——KARST-040 正在改那個檔。入口那條路已經令它變成多餘
(留住亦不會出錯,只是白查一句),KARST-040 收工之後可以順手刪走。
