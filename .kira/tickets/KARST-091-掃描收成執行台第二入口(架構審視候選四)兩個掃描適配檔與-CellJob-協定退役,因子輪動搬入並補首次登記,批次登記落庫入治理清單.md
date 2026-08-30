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
---

## 工作內容

源自架構審視候選四與 D-042(D-043)。完成後:(1) Executor 加 sweep 入口,一次掃描即一個批次;逐格走與 run 同一條落格路徑,分別只在來歷(掃描格加掃描編號,KARST-054)、不收選股痕跡、參數由掃描格逐格展開三處;判讀沿用 sweep/verdict.py 的 judge(純函數,一個字不動);四個判讀門檻無預設。(2) 一格拋錯不中斷整個批次,失敗格記入結果當無效格處理。(3) sweep/factor_mix.py 的 FactorMixJob(:218)與 ensure_factor_mix_setup(:184)、sweep/factor_rotation.py 的 FactorRotationJob(:225)與 ensure_factor_rotation_setup(:196)四件刪走;sweep/runner.py 的 CellJob(:101)協定與 run_sweep(:290)退役,CellPlan(:64)保留改由執行台按參數規格自動砌。(4) weight_grid(:41)、reference_point(:76)、rotation_grid(:123)留作掃描格構造;CostedEngine(sweep/factor_mix.py:154)搬去 karst/engine/ 與 VectorbtEngine 並列(它是 PortfolioEngine 的第二個實作,不是掃描的事);ScoreEntry、scoreboard、segment_excess、CostPair、cost_comparison、provenance_note 搬去 sweep/report.py。(5) karst/sweep/__init__.py 那 52 個對外名順手收窄,並補上輪動那半邊本來一個都沒導出的不一致。(6) 因子輪動搬入:刪 record_factor_rotation_run(:1482)與 run_factor_rotation(:1378)的引擎樣板;run_factor_rotation 改名 plan;:1417-1437 的大市代號解析與「大市不可以同時是持倉」核對改由 needs_entities 宣告加執行台解析;_prepare_macro(:1332)保留為策略內部守門,macro_series_needed(:975)變 needs_entities 的一格;RotationDriver(:366)與十個驅動器不動。輪動現時沒有登記函式、策略型別直接等於因子混合、沒掛 strategies/__init__.py 的 __all__、沒有選股痕跡——搬入要補一次首次登記,會生成新的策略版本,舊運行依 D-021 第 9 條標過時不改,不得倒推;新版本編號與被標過時的運行清單在票上留言。(7) sweep 收尾經唯一入口寫一列批次登記:掃描編號、策略名與版本、期間、數據快照、引擎與版本、總格數、達標格數、隱藏的失敗運行條數、中位年化、中位 Sortino、中位最大回撤、判讀目標與三個門檻、最佳格、代表格、批內最佳單次的運行編號、報告落點與內容雜湊;批次登記入治理清單,karst verify 核得到。舊掃描可以事後補登記,既有運行一個位都不動。失敗判定呼叫 web/data.py is_failed_run 同一份正本,不另寫第二套(D-034/D-040)。(8) web/api_jobs.py 的 _rescan(:836,約 110 行)收成一句 executor.sweep;RESCAN_FAMILIES(:778-781)整張刪走。要刪的測試:test_sweep.py:145 的手砌 _Job、test_factor_rotation.py 的登記與落痕編排斷言。要留的測試:test_sweep.py 的判讀與格、test_macro_drivers.py 的驅動器計分板。驗證方式:既有掃描逐格以執行台重跑,運行編號逐位相同、判讀結果逐格相同;12 條正式運行仍然一條都不變號。行號以 2026-08-30 為準,按內容找。動庫前備份到 C:\Users\Kaho\.claude\backups\karst.sqlite.2026-08-30-091.bak。不加參數預設值;只跑所涉測試檔;含中文檔案只用 Read/Write/Edit;不建目錄連結指向 data/;不碰 karst/web/static/ 與 prototype/;不 commit。

## 驗收條件

- [ ] CellJob 協定與兩個掃描適配檔的 Job 已退役,既有掃描逐格重跑後運行編號與判讀結果逐格相同,12 條正式運行不變號(測試:逐格比對舊 fingerprint 與舊 verdict)
- [ ] 批次登記經唯一入口落庫並入治理清單,karst verify 分列且清白;達標與失敗判定只有 is_failed_run 一份正本(測試:直接寫庫的批次登記被 verify 點名)
- [ ] 因子輪動經執行台跑得通,首次登記所生成的新策略版本已記錄、舊運行只標過時;只跑所涉測試檔;備份已做

## 結果

## 留言

### agent:main · 2026-08-30 11:14
用戶裁決(2026-08-30,選項介面,原話「接受」):因子輪動搬入時補一次正式登記,生成新策略版本,舊運行標過時不刪不改;新版本編號與被標過時的運行清單要在本票留言。已記 D-044。
