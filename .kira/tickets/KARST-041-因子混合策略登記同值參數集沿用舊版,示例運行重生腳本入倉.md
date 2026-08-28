---
id: KARST-041
title: 因子混合策略登記同值參數集沿用舊版,示例運行重生腳本入倉
type: task
createdAt: 2026-08-28
risk: low
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-031, KARST-036]
claimedBy: null
epic: V1 建置
deliverable: KARST-D02
closed: 2026-08-28
---

## 工作內容

因子混合策略自此重登記同一組取值不會多出一個參數集版本,同一次回測亦不會記成兩次運行;而且示例運行 run-f4c162e5aac34347 有一份入倉的重生腳本,任何人一句命令重跑得回同一編號同一成績。KARST-038 收檔時指出:因子混合的登記每次無條件開新版參數集(趨勢波段會先查同名同值沿用),而 KARST-031 當初的驅動檔從未入 git,重跑要在暫存區重造。範圍只是登記路徑與腳本入倉,不改策略定義與取值。

## 驗收條件

- [x] 同一組取值重登記兩次,參數集版本數不變,運行編號相同
- [x] experiments/ 內有因子混合示例運行的重生腳本,執行後編號 run-f4c162e5aac34347 與成績(累計 +321.86%、最大回撤 −34.93%)不變
- [x] 既有測試全部照過

## 結果

· 2026-08-28 08:45 —— 因子混合策略重登記同一組取值,不再多出一個參數集版本;示例運行 `run-f4c162e5aac34347` 亦有了一份入倉的重生腳本,一句命令重跑得回同一個編號同一份成績。

改動只有兩處。`karst/strategies/factor_mix.py` 的 `register_factor_mix` 在登記參數集之前先查一句「這個策略版本上有沒有一個同名、同節奏、同取值的參數集」——有就沿用舊版,一列都不寫;名一樣而取值或節奏不同,照舊出新版。做法照趨勢波段那條現成路(`trend_swing._existing_param_set`),沒有另發明一套。另外新增 `experiments/2026-08-28-factor-mix-real/run_backtest.py` 與它跑出來的 `summary.json`。**策略定義與取值一個字都沒有改**,公開接口簽名亦原封不動(KARST-042、KARST-043 兩票正在 import 它)。

**逐項剔驗收條件**

1. **同一組取值重登記兩次,參數集版本數不變,運行編號相同** —— 離線凍一個真快照(靜態來源重放同一條管線,D-026 第 7 條),同一組取值連登記三次:參數集版本數由頭到尾是 1、`param_set_id` 與落庫時間都是同一列,證明回的真是舊那一列而不是新寫的;權重寫成數字 `0.25` 還是文字 `"0.25"` 一樣認得是同一組(庫層一律把取值收成文字,本檔照它那個收法比對)。落痕兩次得回同一個運行編號、同一個身份文字、同一筆舊留痕,`backtest_run` 表由頭到尾只有一列——同一次回測不會記成兩次。測試:`test_registering_the_same_values_twice_keeps_one_version_and_one_run_id`。

2. **experiments/ 內有重生腳本,執行後編號與成績不變** —— `experiments/2026-08-28-factor-mix-real/run_backtest.py` 一句跑完五件事(砌面板 → 登記 → 跑回測 → 落痕 → 算指標),取值全部明寫在檔頭。實跑核對:運行編號 `run-f4c162e5aac34347`、2,929 個交易日、換倉 47 次(首次執行日 2015-01-05)、成交 188 筆、累計回報 3.2186(+321.86%)、年化 0.1319(13.19%)、最大回撤 −0.3493(−34.93%),與 KARST-031 及 KARST-038 記低那次一字不差;三條序列核對「全對」。腳本自己帶一道核對閘,對不上即當場拋錯——交不出同一份成績就不算重生。跑完之後查庫:參數集總數 3,626 個、運行 3,624 次,與跑之前一模一樣,一列都沒有多寫。快照 `2026-08-27-91a5d51339d9` 不入 git,腳本檔頭寫明重抓那一句(要帶 `--taken-on 2026-08-27`,因為快照日期是編號的前綴)。測試:`test_the_sample_run_script_rebuilds_the_same_run_id_and_figures`(複製一份庫來跑,不動倉裡那個;倉內沒有那個快照即 skip 並講明怎樣重抓)。

3. **既有測試全部照過** —— 本票 `tests/test_factor_mix.py` 7 passed(KARST-031 原有 4 條全綠,含真實抓取那條;KARST-041 新增 3 條)。另加一條回歸守門:沿用不可以過頭(取值不同、節奏不同一律照舊出新版),加 `register_factor_mix` 的公開簽名逐格核對,免得日後有人為了「沿用」而把接口改走。測試:`test_reuse_does_not_overreach_and_the_public_signature_is_unchanged`。**全倉 `python -m pytest -q` 104 個測試,103 passed、1 failed**;紅的那條是 `tests/test_engine_rules.py::test_rule_contracts_stay_behind_our_own_interface`(`NameError: TradingCosts`),來自另一位代理正在改動中的 `karst/engine/`(工作區未收檔),與本票無關——本票分工三個檔以外一個字都沒有碰,而那條紅燈在本票開工之前已經在。

**產物** —— `karst/strategies/factor_mix.py`(改)、`tests/test_factor_mix.py`(改)、`experiments/2026-08-28-factor-mix-real/run_backtest.py` 與 `summary.json`(新增)。

· 2026-08-28 08:50 更正上一條:驗收條件 3 那句「那條紅燈在本票開工之前已經在」是我沒有查過就寫的——開工時未跑過全倉,講不出它幾時開始紅。查得實的只有一件:`tests/test_engine_rules.py` 由頭到尾不 import 因子混合任何一件,所以那條紅燈牽連不到本票的改動。

## 留言

· 2026-08-28 KARST-041-fmreg —— **兩件交低給下一手,本票內按分工繞過,沒有改別人的檔。**

1. **「同名同值即沿用舊版」現時有兩份實作。** 趨勢波段一份(`trend_swing._existing_param_set`)、因子混合一份(本票加的),兩份逐字相同。這條規則本身與策略無關——它是「參數集怎樣才算同一組取值」的規約,應該住在唯一入口(`gateway.register_param_set`)或者庫層,由它一次過認住,策略層一份都不用抄。本票的檔案分工只批得到 `factor_mix.py`,所以照抄了一份,並在碼上註明出處。建議下一張票把它收歸一處,兩邊改為呼叫——現在多一份影像,就多一個日後會走樣的地方(D-002 第 4 條)。

2. **`karst/sweep/factor_mix.py` 的 `ensure_factor_mix_setup` 那道「先查一句」現在是多餘的。** 它的說明文字明寫存在理由是「`register_factor_mix` 每次都會登記一個參數集,重跑一次掃描就會白白多一個版本」——那件事本票已經在源頭修好。那個函式現在仍然行得通(它只是提早回頭,不會出錯),但它的理由沒有了。掃描那一層不是本票地盤,留待日後清理。
