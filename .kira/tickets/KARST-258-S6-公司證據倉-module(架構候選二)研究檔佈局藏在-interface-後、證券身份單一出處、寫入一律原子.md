---
id: KARST-258
title: S6 公司證據倉 module(架構候選二):研究檔佈局藏在 interface 後、證券身份單一出處、寫入一律原子
type: task
createdAt: 2026-09-23
risk: high
model: opus
fits: 一程(大):證據倉 interface 及八個以上呼叫模組改接;超出則按讀／寫拆
dependsOn: [KARST-254]
claimedBy: Opus-S6
epic: 根基重整
deliverable: KARST-D12
closed: 2026-09-23
---

## 工作內容

依執行計劃 §三 6 及架構評審候選二。現況八個以上 module 直接讀寫 packet.json／evidence.json,evidence.json 退路寫四次另兩處漏寫;證券身份存於 packet.json 與 store entity 兩處,render_charts 從 title 字串切出 exchange;packet.json 有非原子寫入。建立證據倉 module,呼叫方不再知道檔案佈局;證券身份單一出處;所有寫入原子。既有雲端 /data 內容須原樣可讀,不做資料遷移或只做可回退的遷移。程式只住 karst/。

## 驗收條件

- [x] karst/ 內除證據倉 module 外沒有直接開 packet.json／evidence.json 的程式
- [x] exchange 不再從 title 字串推出
- [x] 所有寫入經原子寫入
- [x] 以現有雲端資料格式的 fixture 驗證讀取不變;既有全套測試通過

## 結果

新 module `karst/company_bundle.py`(`CompanyBundle`):interface 只答四件事——`security()`／`claim()`(證券身份)、`records()`／`register()`／`observations()`(目前可用資料與取得紀錄)、`packet()`／`working()`／`save_working()`(目前取證包)——另有 `research()`／`save_research()`／`save_frozen()`／`checked()` 供舊式 research.json 與發布包 inputs。檔名、「無登記冊則讀 evidence.json」退路只在 module 內;所有寫入經 `fetch.registry.atomic_write`(temp + fsync + os.replace,與登記冊同一實作)。

改接:service(refresh_sources、prepare_research、plan_update、get_research_context、render_charts、_register_requests、save_research、publish_research、read_evidence、ingest_source、ensure_company)、daily、workflow、bars、agents.research、agents.review、agents.assemble、pipeline、publish、run;`packet.load_bundle` 移入為 `CompanyBundle.checked()`。daily_bench 計時包裝改接 `CompanyBundle.register/records` 與 `bars.series_for`(主 agent 追加要求)。

證券身份:單一出處是證據倉內的 `security.json`,由 `ensure_company`／`prepare_research`／pipeline packet 認領(欄位合併,另一證券拒絕);SQLite entity 列改由它抄出。舊 bundle 無此檔時讀 working packet 的 security,首次認領只新增該檔、其餘檔逐 bytes 不變。render_charts 的交易所鐘只由身份決定,title 只作圖名。

雲端相容:不做資料遷移。`test_company_bundle.py` 以現行格式(登記冊＋objects＋observations＋packet.json＋evidence.json,無 security.json)構造 fixture,驗證身份、資料、取證包、context、搜尋、出圖讀取正確且不改寫任何檔;另驗首次認領只加檔、異證券拒絕、寫入失敗不留半檔。全套 451 通過、1 跳過,唯一失敗為已知 test_reader symlink(WinError 1314)。研究版本 ID、計算回執、證據指紋及發布讀回相關測試全部通過。

## 留言

### agent:Opus-S6 · 2026-09-23 03:30

一程完成,未拆票。給 KARST-256:日更快照可在 `CompanyBundle` 加一個具名讀寫方法(同樣經 `_write` 原子替換,檔名留在 module 內),呼叫方只講「存／讀本證券日更快照」;批次登記可在 `register` 旁加整批版本,一次讀寫 manifest 與 observations,interface 不需改動既有呼叫方。未處理:`publish_research` 寫公司索引頁 `index.html` 仍是 `write_text`(不在證據倉內,屬發布目錄)。
