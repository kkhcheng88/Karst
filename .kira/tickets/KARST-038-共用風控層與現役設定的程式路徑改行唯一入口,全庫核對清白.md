---
id: KARST-038
title: 共用風控層與現役設定的程式路徑改行唯一入口,全庫核對清白
type: task
createdAt: 2026-08-28
risk: low
model: opus
fits: 一程
approvalRequired: false
dependsOn: [KARST-035, KARST-028]
claimedBy: null
closed: 2026-08-28
epic: V1 建置
deliverable: KARST-D02
---

## 工作內容

策略程式登記風控規則、引用風控規則、指定現役設定,自此全部經唯一入口的服務層而非直接呼叫庫層 API,令真實策略跑完後 karst verify 報全庫清白。KARST-035 把三張表納入簽章核對後,KARST-028 趨勢波段跑完即報 6 條未簽章列,全部來自共用風控層直接寫庫;karst/risk/registry.py、karst/metrics 說明例子與 tests/test_risk_layer.py 亦屬同類路徑。範圍只是改呼叫路徑,不改表結構、不改規則定義、不改任何取值。

## 驗收條件

- [x] 趨勢波段與因子混合策略各重跑一次示例運行後 karst verify 報全庫清白,運行編號與成績不變
- [x] karst/ 內查不到繞過入口直接寫 active_setup、risk_rule、strategy_risk_ref 三表的程式路徑(測試除外須經入口)
- [x] 既有測試全部照過

## 結果

· 2026-08-28 08:17 —— 共用風控層自此一列都不寫庫,三張表全部改由唯一入口落筆,`karst verify` 由 6 條未簽章列變成全庫清白。

**改了什麼** —— 風控層與入口的分工調轉了方向。原本 `karst/risk/registry.py` 自己拿住 `store` 寫 `risk_rule` 與 `strategy_risk_ref` 兩張表,策略層再直接呼叫它;現在風控層只交出一份「登記單」(`risk_rule_definitions()`,三條規則叫什麼、管什麼、取值住哪個參數名),由 `Gateway.register_risk_rules()` 照單入庫並蓋寫入者簽章。引用登記同理:策略層改為呼叫 `Gateway.attach_risk_rules()`,把「哪幾條有給取值」交給入口寫。`register_risk_layer` 與 `reference_risk_rules` 兩個直接寫庫的函式一併除名。方向因此只有一條——入口 import 風控層,風控層永不反過來 import 入口,不會繞成一圈。

策略層 `karst/strategies/trend_swing.py` 只換了呼叫路徑,`register_trend_swing` 的公開簽名一格未動(KARST-036 照舊 import 得到)。因子混合本來就沒有碰過風控層,一個字都不用改。`karst/metrics/__init__.py` 的說明例子由 `store.set_active_setup(...)` 改成 `gateway.designate_active_setup(...)`,順帶指出命令列同一道門是 `karst params activate`——說明文字亦是一條會被人照抄的路徑。

**驗收條件 1(重跑兩個示例運行)** —— 成立,兩次都是對住真實日線的完整重跑,`karst verify` 事後報全庫清白。

- 趨勢波段:`python experiments/2026-08-28-trend-swing-real/run_backtest.py`。運行編號仍是 `run-728a01087531258f`,累計回報 249.83%、年化 11.38%、最大回撤 −20.84%、勝率 44.21%、盈虧比 2.132、Sortino 0.775、平均持倉 49.67 日、換手 3.6577,與 KARST-037 收檔那次逐個相同;三條序列核對全對。
- 因子混合(ETF 版):運行編號仍是 `run-f4c162e5aac34347`,累計回報 +321.86%、年化 13.19%、最大回撤 −34.93%、期內換倉 47 次、成交 188 筆,與 KARST-031 記低那次相同。
- 重跑之前 `karst verify` 報 6 條未簽章列(`risk_rule` 三條、`strategy_risk_ref` 三條),正是票上講的那 6 條;趨勢波段重跑一次即全部補上簽章,兩次重跑之後核對都是「全庫清白」。測試:`tests/test_trend_swing.py::test_a_full_run_leaves_the_whole_store_clean`(玩具場走完整條登記路徑後 `gateway.verify() == []`,並證明重跑同一次登記回同一個策略版本與參數集版本,運行編號因此不變)。

**驗收條件 2(查不到繞過入口的程式路徑)** —— 成立。測試 `tests/test_risk_layer.py::test_no_module_outside_the_gateway_writes_the_three_tables` 掃 `karst/` 每一個 `.py`:入口以外一個檔都不准呼叫 `store.set_active_setup()` / `store.register_risk_rules()` / `store.attach_risk_rules()`,亦不准自己寫這三張表的 SQL。例外只有三個,而且都是結構上必然的:`karst/schema.py`(建表與不可改 trigger 的正本)、`karst/store.py`(庫層,SQL 正本)、`karst/gateway/`(唯一入口本身,它就是那條合法通道)。另加 `test_the_risk_layer_never_imports_the_gateway` 釘住方向,免得日後有人把依賴繞成一圈。測試那一邊亦已改行入口:`tests/test_risk_layer.py` 與 `tests/test_metrics.py` 的治具換成 `Gateway`,登記與指定現役設定全部經它走(`tests/test_gateway_governance.py` 那句 `store.set_active_setup` 是刻意留下的反例,證明繞過入口一掃即現形,不動)。

**驗收條件 3(既有測試全部照過)** —— 成立。全倉 `PYTHONUTF8=1 python -m pytest -q` **89 passed**,無紅燈。`ruff check` 在本票改過的七個檔全部過關(倉內尚餘一條 `tests/test_sweep.py:18` 未用 import,不是本票碰過的檔)。

**產物** —— `karst/risk/registry.py`、`karst/risk/__init__.py`、`karst/gateway/service.py`、`karst/strategies/trend_swing.py`、`karst/metrics/__init__.py`(只改說明文字)、`tests/test_risk_layer.py`、`tests/test_trend_swing.py`、`tests/test_metrics.py`。表結構、規則定義、任何一個取值都沒有動過。未 commit。

## 留言

· 2026-08-28 KARST-038-govern2 —— **接手前一位代理的半成品,決定沿用。** 他已經把 `karst/risk/registry.py` 改成只交登記單(方向與本票一致),但只刪了函式未改呼叫端,當時 `import karst.risk` 直接拋 ImportError、`Gateway.register_risk_rules()` 亦 import 一個不存在的名。還原重做要把那一格對的判斷再想一次,沿用只欠補完呼叫端,所以沿用。

· 2026-08-28 KARST-038-govern2 —— **交低一件給下一手:因子混合那次示例運行,倉內沒有腳本重造得到。** KARST-031 當初的驅動檔沒有入 git,所以今次是照票上記低那組取值(快照 `2026-08-27-91a5d51339d9`、四格各 25%、季度換倉、本金 100,000、費用 0)在暫存區重造一個驅動檔跑的,跑完編號與成績都對得上,但那個檔沒有留在倉內。趨勢波段有 `experiments/2026-08-28-trend-swing-real/run_backtest.py`,因子混合沒有對應的一份——下次要重跑或者要查它憑什麼是這個成績,又要重造一次。

· 2026-08-28 KARST-038-govern2 —— **順帶查到一件不屬本票的事:`register_factor_mix` 每次都會為參數集出一個新版。** 它無條件呼叫 `gateway.register_param_set()`,不像 `register_trend_swing` 會先查有沒有同名同值的舊版沿用。後果是同一組取值重登記一次就換出另一個運行編號,把同一次回測記成兩次(D-021 第 9 條)。今次重跑因此刻意不呼叫它,改為由庫內已登記那一版參數集讀回取值再跑,編號才對得回 `run-f4c162e5aac34347`。`karst/strategies/factor_mix.py` 由 KARST-036 認領中,本票明文不改它,故此只在這裡記低。
