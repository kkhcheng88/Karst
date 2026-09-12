---
id: KARST-225
title: ②第一次考試 票 A′(KARST-222 按執行口徑 v1.1 重跑)——成交額門檻改 1,000 萬美元後,由宇宙起重算逐年第 90 百分位、入口池、分年分桶抽 84 主 + 44 後備並鎖定於 A2/picks_before_results.md、建 84 個 T1 遮蔽取證包與對照預測 C1–C3;沿用 A/ 的腳本與快取,不動 A/
type: research
createdAt: 2026-09-13
risk: low
model: opus
fits: 用戶 2026-09-13 原話「Make it 1000萬美元」(決策簿新條);執行口徑 v1.1 修訂頁;KARST-222 收檔留言與執行紀錄——A.md;D-175 機械工作交 DeepSeek
dependsOn: []
claimedBy: exam2-A2-ds2
epic: 方法論期(D-166)
deliverable: KARST-D06
closed: 2026-09-13
---

## 工作內容

沿用 research/2026-09-methodology/2026-09-12-②第一次考試/A/ 的 s1–s13、pxlib.py、finlib.py、buckets.py 與 cache/(events_raw、xbrl_metrics、price_metrics、merger_days、guidance.jsonl、edgar_cache/),只改宇宙門檻一項:公布前 60 個交易日日均成交額(算術平均)≥ 1,000 萬美元(同時記中位數欄);逐年第 90/95/80 百分位門檻必須在新宇宙的事件上重算;入口池、分層比例、抽樣(種子 20260912、同 buckets.py、同 s7 規則)全部重做;新宇宙的強勢反應子集若有事件未抓過 EX-99.1 文本則補抓(單線程),已抓的不重抓;取證包沿用 s9 體例,與 A/packets/ 同 event(同 accessionNumber)且規格相同者可複製並記錄,其餘新建;controls_operating.csv 另檔重算。全部輸出到 A2/(population.csv、entry_pool.csv、thresholds.md、picks_before_results.md、packets/、controls_operating.csv、執行紀錄——A2.md);A/ 一個檔都不改。執行紀錄要多寫:v1 與 v1.1 的宇宙內事件數、入口池數、逐年門檻值的差;v1 主清單 84 個之中有多少個仍在新宇宙、多少個出現在 v1.1 主清單(重疊數);抽樣純機械、無手動換名的聲明。硬規矩同 KARST-222:含中文檔案只用 Read/Write/Edit;PYTHONUTF8=1;申報原文不入庫;不 commit;不改 strategy/ 與既有輸出;記憶體逐檔處理、單線程。

## 驗收條件

- [x] A2/thresholds.md 逐年門檻在新宇宙上重算;反例:任何一年的宇宙內事件數等於 A/thresholds.md 同年數字(即沒有重算),即不合格
- [x] A2/population.csv 含 turnover_mean_60d 與 turnover_median_60d 兩欄,宇宙門檻用平均值 ≥ 1,000 萬;反例:任何一列 turnover_mean_60d < 10,000,000 而 in_universe 為真,即不合格
- [x] A2/picks_before_results.md 主 84 + 後備 44、種子 20260912、每年每桶數、SHA-256;落檔時間早於 A2/packets/ 與 A2/controls_operating.csv 任何檔;執行紀錄寫明與 v1 主清單的重疊數
- [x] A2/packets/ 84 包,任何一包含 T1 之後日期的資料即整批不合格;複製自 A/packets/ 的包逐個記錄並核 accessionNumber 相同
- [x] A2/controls_operating.csv 每事件一行 C1/C2/C3,不出現於任何包;A/ 目錄 git status 乾淨;不 commit

## 結果

· 2026-09-13 00:29 由宇宙起重跑完成,輸出全部在 `A2/`;`A/` 一個檔未改。
- 宇宙內事件 68,468 → **50,935**(逐年無一年相同);入口池 4,008 → **3,025**。
- 鎖定檔 2026-09-13 00:19:19 落檔,SHA-256 `4a3c5ffc…`;84 主 + 44 後備,補位 3 個(全部同年同桶)。
- `packets/` 84 包全新建、0 包越界、0 包缺 EX-99.1;`controls_operating.csv` 128 行。
- 與 v1 主清單重疊 **2 / 84**;v1 主清單 47 / 84 仍在新宇宙。
· 2026-09-13 00:29 票面一句須更正:v1 用的是**平均**(`np.nanmean`),不是中位數;用 300 萬重算可得回 v1 的 68,468。詳見 `A2/執行紀錄——A2.md` 第四節。

## 留言

### agent:exam2-A2-ds2 · 2026-09-13 00:30
\## 做了什麼

- 按執行口徑 v1.1,由宇宙起重跑一次(不是舊清單過濾):成交額門檻 300 萬 → 1,000 萬美元(60 個交易日算術平均)。全部輸出在 `research/2026-09-methodology/2026-09-12-②第一次考試/A2/`;**`A/` 一個檔未改**。
- 工序:`s2_turnover.py`(逐檔掃描重算成交額平均與中位)→ `s4_assemble.py`(重算宇宙與逐年門檻)→ `s5/s6`(補抓 EX-99.1、判 improvement_type)→ `s7_sample_lock.py`(抽樣並鎖定)→ `s8_controls.py` → `s9_packets.py` → `s10_export.py` → `s11/s12/s13`(覆核與驗收自查)。

\## 證據與關鍵數字

- 宇宙內事件 **68,468 → 50,935**(11 年逐年無一年相同,反例條件成立);入口池 **4,008 → 3,025**。
- 逐年第 90 百分位門檻全部下降(2015 0.0750→0.0663、2020 0.0804→0.0767、2024 0.1066→0.1010),v1 對照欄已加在 `A2/thresholds.md`。
- 鎖定檔 `A2/picks_before_results.md` **2026-09-13 00:19:19** 落檔,SHA-256 `4a3c5ffcf501378e2f7e28326b2cf96451cafec627aa4bb4c523458ab6577142`;早於 `controls_operating.csv`(00:19:50)31 秒、早於最早一包(00:26:14)414.7 秒;由檔內清單逐行重算的雜湊與鎖定時相同。
- 主 84 + 後備 44(後備每年 4 個、2025 亦 4 個,檔內文字與清單已一致);補位 3 個(B011/B029/B034),**全部同年同桶**。與 v1 主清單重疊 **2 / 84**;v1 主清單 47 / 84 仍在新宇宙。
- `A2/packets/` **84 包,0 包越界、0 包缺 EX-99.1**、每包 8 季財務數列;`A2/controls_operating.csv` 128 行、逐事件一行、C1 有值 18 / C2 117 / C3 121,不出現於任何包。
- 三列覆核(種子 20260912,由入口池抽,OII / TSLA / REZI):反應日、T1 收市、反應報酬、相對 SPY、g0、**成交額平均與中位**全部相符。
- 驗收 5 條逐條反例自查:`A2/cache/acceptance_checks.json`(宇宙內 50,935 宗之中平均 < 1,000 萬者 0 宗;11 年門檻無一年等於 v1)。
- 補抓:子集 5,093 宗需重判,其中 411 宗補抓(成功 388、23 宗該申報無 EX-99 附件);建包另抓 386 份文件。單線程、3 請求/秒。
- **票面一句要更正**:v1 用的是**平均**(`A/s2_price_metrics.py` 第 162 行 `np.nanmean`),不是中位數;證據是用「平均 ≥ 300 萬」重算得 68,468,與 v1 實報完全相同。所以 v1.1 的實際改動只是門檻值 300 萬 → 1,000 萬。

\## 未做與原因

- **未從 `A/packets/` 複製任何包(複製 0 個、新建 84 個)。** 兩份清單只有 2 宗同 accessionNumber,而 s9 本來就要為其餘 82 宗跑一次;全部新建可保證 84 包同一體例與時間戳規則。該 2 宗已逐個記錄、核 accessionNumber 相同,並逐節比對**五個資料節與 `masking_check` 0 處不同**。
- `A/` 未改:git 追蹤檔全部乾淨(`git status --porcelain -- …/A` 無輸出);`A/edgar_cache/` 只**新增** 1,130 檔(票面許可沿用該快取),未改動任何既有檔。未 commit。
- 鎖定檔標題仍寫「票 A」(非「票 A′」)——該檔落檔後不得改動,故不改;檔內規則文字已寫明 v1.1 門檻。
- 六桶對應表仍是 v1 留下的自訂表(執行口徑只寫「SIC 兩位數合成六桶」沒給表),原樣沿用未改。

\## 舉手

無,不需要人裁。要睇細節請讀 `research/2026-09-methodology/2026-09-12-②第一次考試/A2/執行紀錄——A2.md`(六步數字、v1 對 v1.1 的差、包的新建與比對、驗收逐條、時間戳)。
