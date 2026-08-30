---
id: KARST-091
title: 掃描收成執行台第二入口(架構審視候選四):兩個掃描適配檔與 CellJob 協定退役,因子輪動搬入並補首次登記,批次登記落庫入治理清單
type: task
createdAt: 2026-08-30
risk: medium
model: opus
fits: 多程
approvalRequired: false
dependsOn: [KARST-090]
claimedBy: agent-091
epic: V1 建置
deliverable: KARST-D02
closed: 2026-08-30
---

## 工作內容

源自架構審視候選四與 D-042(D-043)。完成後:(1) Executor 加 sweep 入口,一次掃描即一個批次;逐格走與 run 同一條落格路徑,分別只在來歷(掃描格加掃描編號,KARST-054)、不收選股痕跡、參數由掃描格逐格展開三處;判讀沿用 sweep/verdict.py 的 judge(純函數,一個字不動);四個判讀門檻無預設。(2) 一格拋錯不中斷整個批次,失敗格記入結果當無效格處理。(3) sweep/factor_mix.py 的 FactorMixJob(:218)與 ensure_factor_mix_setup(:184)、sweep/factor_rotation.py 的 FactorRotationJob(:225)與 ensure_factor_rotation_setup(:196)四件刪走;sweep/runner.py 的 CellJob(:101)協定與 run_sweep(:290)退役,CellPlan(:64)保留改由執行台按參數規格自動砌。(4) weight_grid(:41)、reference_point(:76)、rotation_grid(:123)留作掃描格構造;CostedEngine(sweep/factor_mix.py:154)搬去 karst/engine/ 與 VectorbtEngine 並列(它是 PortfolioEngine 的第二個實作,不是掃描的事);ScoreEntry、scoreboard、segment_excess、CostPair、cost_comparison、provenance_note 搬去 sweep/report.py。(5) karst/sweep/__init__.py 那 52 個對外名順手收窄,並補上輪動那半邊本來一個都沒導出的不一致。(6) 因子輪動搬入:刪 record_factor_rotation_run(:1482)與 run_factor_rotation(:1378)的引擎樣板;run_factor_rotation 改名 plan;:1417-1437 的大市代號解析與「大市不可以同時是持倉」核對改由 needs_entities 宣告加執行台解析;_prepare_macro(:1332)保留為策略內部守門,macro_series_needed(:975)變 needs_entities 的一格;RotationDriver(:366)與十個驅動器不動。輪動現時沒有登記函式、策略型別直接等於因子混合、沒掛 strategies/__init__.py 的 __all__、沒有選股痕跡——搬入要補一次首次登記,會生成新的策略版本,舊運行依 D-021 第 9 條標過時不改,不得倒推;新版本編號與被標過時的運行清單在票上留言。(7) sweep 收尾經唯一入口寫一列批次登記:掃描編號、策略名與版本、期間、數據快照、引擎與版本、總格數、達標格數、隱藏的失敗運行條數、中位年化、中位 Sortino、中位最大回撤、判讀目標與三個門檻、最佳格、代表格、批內最佳單次的運行編號、報告落點與內容雜湊;批次登記入治理清單,karst verify 核得到。舊掃描可以事後補登記,既有運行一個位都不動。失敗判定呼叫 web/data.py is_failed_run 同一份正本,不另寫第二套(D-034/D-040)。(8) web/api_jobs.py 的 _rescan(:836,約 110 行)收成一句 executor.sweep;RESCAN_FAMILIES(:778-781)整張刪走。要刪的測試:test_sweep.py:145 的手砌 _Job、test_factor_rotation.py 的登記與落痕編排斷言。要留的測試:test_sweep.py 的判讀與格、test_macro_drivers.py 的驅動器計分板。驗證方式:既有掃描逐格以執行台重跑,運行編號逐位相同、判讀結果逐格相同;12 條正式運行仍然一條都不變號。行號以 2026-08-30 為準,按內容找。動庫前備份到 C:\Users\Kaho\.claude\backups\karst.sqlite.2026-08-30-091.bak。不加參數預設值;只跑所涉測試檔;含中文檔案只用 Read/Write/Edit;不建目錄連結指向 data/;不碰 karst/web/static/ 與 prototype/;不 commit。

## 驗收條件

- [x] CellJob 協定與兩個掃描適配檔的 Job 已退役,既有掃描逐格重跑後運行編號與判讀結果逐格相同,12 條正式運行不變號(測試:逐格比對舊 fingerprint 與舊 verdict)
- [x] 批次登記經唯一入口落庫並入治理清單,karst verify 分列且清白;達標與失敗判定只有 is_failed_run 一份正本(測試:直接寫庫的批次登記被 verify 點名)
- [x] 因子輪動經執行台跑得通,首次登記所生成的新策略版本已記錄、舊運行只標過時;只跑所涉測試檔;備份已做

## 結果

· 2026-08-30 12:49 掃描已收成執行台第二入口。`CellJob` 協定、`run_sweep`、四件適配檔的 Job 與 ensure 函式全部退役;`CostedEngine` 搬去 `karst/engine/costed.py`,六個報告函式搬去 `sweep/report.py`,`karst/sweep/__init__.py` 的對外名收窄並補回輪動那半邊。因子輪動改為策略合約(`FactorRotationContract`),`run_factor_rotation` 與 `record_factor_rotation_run` 兩段引擎樣板刪走,大市代號解析改由 `needs_entities` 宣告。收尾經唯一入口寫一列 `sweep_batch` 批次登記,入治理清單的「定義」類。

· 2026-08-30 12:49 重跑核對:22 幅已落檔的掃描、4708 格,運行編號、參數集名、參數集參數值**逐格逐位相同**;12 條正式運行前後不變。另挑一幅 20 格的輪動掃描整幅真跑一次執行台:逐格編號、逐格指標、逐格裁決全部對得上,全部讀回舊運行、一次引擎都沒有碰。腳本與結果落 `experiments/2026-08-30-sweep-verify/`。

· 2026-08-30 12:49 測試:`test_sweep.py`、`test_gateway_governance.py`、`test_cadence_weekly.py`、`test_factor_rotation.py`、`test_engine_costs.py`、`test_macro_drivers.py` 六個檔一齊跑,40 條全綠。只跑了這六個所涉檔。庫的備份已做,全程在複本上跑,正本未動。

## 留言

### agent:main · 2026-08-30 11:14
用戶裁決(2026-08-30,選項介面,原話「接受」):因子輪動搬入時補一次正式登記,生成新策略版本,舊運行標過時不刪不改;新版本編號與被標過時的運行清單要在本票留言。已記 D-044。

### agent:agent-091 · 2026-08-30 12:51
**進度:主體做完並驗過,第三條驗收剔不到——原因寫在下面,同時已在票上舉手。**

\## 一、做了什麼

掃描不再自己一套跑法,收成 `Executor.sweep` 這個第二入口,與 `run` 共用同一條落格路徑(`_execute_cell`)。分別只在三處:來歷加掃描編號、不收選股痕跡、參數由掃描格逐格展開。判讀仍然叫 `sweep/verdict.py` 的 `judge`,那個純函數一個字都沒有動,四個門檻無預設。

一格拋錯不會中斷整個批次:錯的格記入 `BatchOutcome.failures`,再以 `CellScore(value=None, trades=0)` 餵入判讀,順理成章當**無效格**。

退役的:`CellJob` 協定、`run_sweep`、`FactorMixJob` / `ensure_factor_mix_setup` / `FactorRotationJob` / `ensure_factor_rotation_setup`。`CellPlan` 保留,改由執行台按參數規格自動砌。搬家的:`CostedEngine` → `karst/engine/costed.py`(與 VectorbtEngine 並列);`ScoreEntry`、`scoreboard`、`segment_excess`、`CostPair`、`cost_comparison`、`provenance_note` → `sweep/report.py`。`karst/sweep/__init__.py` 的對外名收窄,並補回輪動那半邊本來一個都沒導出的不一致。

因子輪動搬入:`run_factor_rotation` 與 `record_factor_rotation_run` 兩段引擎樣板刪走,策略只剩參數規格、因子規格、要哪些實體,加一個純函數 `plan()`。大市代號解析與「大市不可以同時是持倉」那條核對改由 `needs_entities` 宣告、執行台解析;`_prepare_macro` 留作策略內部守門。

批次登記:收尾經唯一入口寫一列 `sweep_batch`,入治理清單的「定義」類,`karst verify` 分得出、核得到。達標與失敗判定只呼叫 `web/data.py` 的 `is_failed_run` 一份正本,沒有另寫第二套。

\## 二、重跑核對的結果(報告落 `experiments/2026-08-30-sweep-verify/報告.md`)

**全倉重算**:22 幅已落檔的掃描、4708 格,運行編號、參數集名、參數集參數值**逐格逐位相同**,一格例外都沒有。12 條正式運行前後都是 12,一條都沒有變號。

**真跑一次**:挑那幅 20 格的 `factor_momentum` 輪動掃描,整幅走一次 `Executor.sweep`。因為編號一位不變,執行台逐格查得回舊運行——20 格全部讀回,**一次引擎都沒有碰**。逐格運行編號、逐格指標(年化、最大回撤、對 SPY / QQQ 超額,容差 1e-9)、逐格裁決,全部與落檔那兩張表相同。批次登記寫得出、`verify` 見它清白;之後直接寫庫塞一列進 `sweep_batch`,`verify` 即刻點名「未經唯一入口寫入」。

**中途一個岔子要講清楚**(免得下一手重踩):第一輪對裁決有 5 格對不上,查下去**不是程式有問題,是我對錯了表**。那幅掃描當日判讀了兩次(一次主目標、一次最大回撤),而落檔那張 `判讀表.csv` 是**最大回撤**那次——核實方法是它的 `value` 欄逐格等於 `掃描表.csv` 的 `max_drawdown` 欄。用回同一個目標之後 20 格全中。另外單獨驗了一次:把落檔那張掃描表**自己的數字**餵回判讀,同一幅格同一組門檻,重現出來的裁決與落檔那張 20/20 完全相同,即是判讀那一層本身一位都沒有飄。順帶:那幅掃描的門檻在 `results/summary.json`,孤峰是 0.005 不是 0.01。

\## 三、順手修了一個新寫出來的毛病

批次登記把報告的 sha256 當內容指紋,而批次登記**只加不改**。但報告正文本來寫住產出時刻、耗時、幾多格今次真的動過引擎——三樣逐次都不同的東西。於是重掃同一個掃描編號,指紋必然不同,必然撞「內容不同」被拒收,`reused_batch` 那條重用路線**永遠走不到**。

改法:報告不再寫這三樣(`karst/sweep/report.py`)。資料一件都沒有丟——登記時刻在批次登記的 `created_at`,逐格是讀回抑或真跑、用了幾多秒,在同一個資料夾 `掃描表.csv` 的 `reused`、`seconds` 兩欄。改完之後重掃同一幅格,報告逐位相同、批次登記照重用(已在冒煙驗到:`rescan_reuses_batch = true`)。

畫面那個重掃按鈕本來就每次派一個新掃描編號,所以它從來沒有壞過;壞的只是同編號重掃這條路。

\## 四、與票文不同的一處,請裁決

**`RESCAN_FAMILIES` 我沒有整張刪走。** 票上寫要刪,但那張表其實孭住兩件事:一半是「彈窗開放改哪幾格」(`_rotation_form` / `_mix_form`,各約 26 行),一半是「怎樣砌新格」。`_rescan` 那 110 行確實已經收成 `setup_from` 加一句 `executor.sweep`,但**彈窗那一半刪了畫面就砌不出控制項**,而砌新格那一半仍然逐個策略不同。要真的刪得走,方向是由合約的 `param_spec()` 自動生成彈窗控制項,再留一張「策略名 → 合約」的對照表——那還是同一張表換個形狀,而且會動到畫面的接口,不是這張票的範圍。所以我留低了它,在這裡講明,聽裁決。

\## 五、沒有做的

- `rejudge` 收批次編號:那是 KARST-090 的未了項,不是本票驗收條件,沒有碰。
- `experiments/` 之下 5 個舊日期的腳本仍然 import 已退役的名。它們是歷史紀錄不是現役程式碼,按之前講法當已知欠帳留低。

\## 六、測試

`test_sweep.py`、`test_gateway_governance.py`、`test_cadence_weekly.py`、`test_factor_rotation.py`、`test_engine_costs.py`、`test_macro_drivers.py` 六個檔一齊跑,**40 條全綠**。只跑了這六個所涉檔。`test_gateway_governance.py` 新增一條:直接寫庫的批次登記被 `verify` 點名。庫備份已做(`karst.sqlite.2026-08-30-091.bak`),全程在複本上跑,正本未動;未 commit。

### agent:agent-091 · 2026-08-30 12:51
**問題**：因子輪動補正式登記,實際上不會生成新策略版本、亦沒有運行需要標過時——D-044 的前提不成立。要照實收貨,還是要人為逼出一個新版本?

**前文後理**：D-044(2026-08-30,用戶原話「接受」)講明:因子輪動搬入時補一次正式登記,會生成新策略版本,舊運行標過時不刪不改,新版本編號與過時運行清單要在本票留言。實際做出來:補登記的內容與庫裡現有那一版**逐字相同**,唯一入口見內容無異就不開新版本。前後對照——策略版本號 2 → 2(沒有新版本);四條因子引用登記前後完全相同,全部 @2;過時運行 30 條 → 30 條,新增 0 條。掛在舊版本上的 675 條運行因此一條都不用標過時。即是說,票上要求留言的「新版本編號」與「被標過時的運行清單」兩樣都沒有東西可以填——不是漏做,是那件事不會發生。所以第三條驗收我沒有剔。我亦刻意沒有為了讓它發生而寫一個門面用的參數集入正本庫:那會在帳上造一件沒有真正發生過的事。

**建議**：照實收貨。這其實是好消息:它證明搬入策略合約之後,輪動這條策略的登記內容與從前逐字一致,即是搬家沒有偷偷改動策略的身份。新版本本來就不是目的,目的是「舊運行不被改動」——那一點已經達到,而且達得更徹底(一條都不用標過時)。如果為了對齊 D-044 的字面而人為造一個新版本,反而會把 675 條完全有效的運行無端標成過時,令治理清單上多 675 條假的雜訊。

**選項**：
- 甲（建議）：照實收貨:登記維持第 2 版,不造新版本,675 條運行照舊有效;D-044 補一句「內容相同則不開新版本」作修訂 —— 帳目與事實一致,舊運行不受無謂牽連;D-044 想保護的東西(舊運行不改)已經達到
- 乙：人為改動登記內容(例如加一個標記欄)以逼出第 3 版,再依 D-021 第 9 條把 675 條運行標過時 —— 字面上對齊 D-044,但代價是造一件沒有真正發生過的版本變更,並令 675 條有效運行變成過時
- 丙：先擱住第三條驗收,等日後輪動真的有內容改動時才順帶開新版本 —— 不作任何裁決,但這張票會一直剔不齊、關不到檔

**要睇邊份稿**：
- experiments/2026-08-30-sweep-verify/報告.md

### agent:main · 2026-08-30 12:52
**裁決**：因子輪動補登記查實與庫內現有版本逐字相同,不生成新版本、無運行變過時——照實收貨,不為湊合 D-044 而寫假登記。第三條驗收以「已核實無新版本(2→2)、無新增過時(30→30)」為證據剔格;D-044 第 2 項的後果句(新版本、標過時)視為未觸發,決策本身不改。

**出處**：主腦(main)決定;依 D-044(用戶「接受」的是搬入補登記這件事,不是一定要有新版本)推出
