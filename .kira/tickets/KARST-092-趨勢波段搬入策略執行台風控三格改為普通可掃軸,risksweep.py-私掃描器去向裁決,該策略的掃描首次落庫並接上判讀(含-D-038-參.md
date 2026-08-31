---
id: KARST-092
title: 趨勢波段搬入策略執行台:風控三格改為普通可掃軸,risk/sweep.py 私掃描器去向裁決,該策略的掃描首次落庫並接上判讀(含 D-038 參數對齊)
type: task
createdAt: 2026-08-30
risk: medium
model: opus
fits: 一程
approvalRequired: true
dependsOn: [KARST-091]
claimedBy: main-agent
epic: V1 建置
deliverable: KARST-D02
closed: 2026-08-31
cancelReason: 趨勢波段已封存(D-068),搬入執行台的前提消失;risk/sweep.py 去向一問隨之擱置,日後有現役策略需要風控掃描時另開票引本票(D-082)
---

## 工作內容

源自架構審視候選一(D-043),並收拾兩份設計都沒有完整處理的一件:趨勢波段的掃描其實不走通用掃描器。完成後:(1) 開工第一步是與用戶對齊參數(D-038 明令每條策略建置期必有此步):哪幾個旋鈕、每個掃描範圍、判讀目標與三個門檻、代表格如何揀;現有示例取值(突破回望 59 日、單筆風險 2%、月度熔斷 6%、賠率門檻 1.5、單一持倉上限 25%)未經對齊,不視為現役設定,對齊結果落在本票。(2) 趨勢波段搬入:刪 register_trend_swing(trend_swing.py:470)、record_trend_swing_run(:552)、sweep_trend_swing(:932)、TrendSwingSweepCell(:868)、TrendSwingSweepResult(:909)、run_trend_swing(:449-457)那三段 isinstance 守門;run_trend_swing(:436)改名 plan,回 RulePlan;params_grid(:829)搬去掃描格構造一族;build_bar_panel(:296)搬去執行台的組面板段;to_param_values(:218)、from_param_set(:233)收成 param_spec 宣告;留 TrendSwingParams 的 entry/stop/rule_params(:188-216)與案例那一整段(EntryCase:620、entry_cases:665、cases_frame:727、CaseStats:753、case_stats:791,經旁產物交出,不入合約);factor_specs 承接 :507-515 按快照換因子版本那段動態。(3) 裁決 karst/risk/sweep.py(213 行)的去向:風控三格既已收進參數規格成為普通可掃軸,sweep_risk_settings(:163)不再是趨勢波段的掃描路徑;它另有 risk/__init__.py 的再導出與 tests/test_risk_layer.py:317,342 兩處依賴,而 trend_swing.py:941 的註釋稱它為共用風控層的正本掃描器,故不得默默刪走——按用戶對「退役還是降級」的裁決執行(待用戶裁決,未裁不得動),並在 CONTEXT.md 與 decisions.md 留下痕跡。(4) 趨勢波段的掃描自此第一次落運行庫、接上運行編號查重與判讀,並在 D-042 的批次表上第一次出現;代價是每格寫一條運行,先量一次寫入量與耗時再決定要不要分批。(5) 要刪的測試:test_trend_swing.py 的登記與落痕編排斷言、:655 _code_symbols 配 :681 _value_defaults 那份 ast.parse 文本斷言(改為參數規格斷言);要留的測試:test_trend_swing.py:431-435 守「策略層碰不到風控型別」那批、案例計算那批、test_risk_layer.py 七個(風控掃描相關兩個按裁決調整)。驗證方式:趨勢波段既有正式運行重跑後成績逐位相同;12 條正式運行全部不變號;三條策略自此在同一個批次表上比得到。行號以 2026-08-30 為準,按內容找。動庫前備份到 C:\Users\Kaho\.claude\backups\karst.sqlite.2026-08-30-092.bak。不加參數預設值;只跑所涉測試檔;含中文檔案只用 Read/Write/Edit;不建目錄連結指向 data/;不碰 karst/web/static/ 與 prototype/;不 commit。

## 驗收條件

- [ ] 參數對齊一節已與用戶完成並落在本票,示例取值與現役設定在參數集上分得出(D-038)
- [ ] 趨勢波段經執行台跑得通,風控三格是普通可掃軸,該策略的掃描首次落運行庫並出判讀;12 條正式運行重跑後成績逐位相同(測試:逐條比對舊 fingerprint)
- [ ] risk/sweep.py 的去向已按裁決執行並留痕,test_risk_layer.py 相應調整;只跑所涉測試檔;備份已做

## 結果

## 留言

### agent:main · 2026-08-30 11:14
用戶裁決(2026-08-30,選項介面,原話「整檔退役」):karst/risk/sweep.py 整檔退役,風控掃描自此只走執行台一條路;tests/test_risk_layer.py 依賴它的兩個測試改打執行台。第 (3) 項按此執行,已記 D-044。第 (1) 項參數對齊仍須開工時與用戶對齊,approvalRequired 不變。

### agent:main-agent · 2026-08-30 23:57
依 D-058/D-056:本票前提已失效——票寫趨勢波段是一條策略要搬上執行台,決策已裁它是進出場治理不是策略(D-056)。處置=**候改寫**:治理規則庫排期時把本票改寫為「規則零件改編為進出場治理規則庫」,因本票 approvalRequired: true,改寫後須重新過審批;此前不派工。
