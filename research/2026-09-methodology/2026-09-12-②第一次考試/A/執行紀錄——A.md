# 執行紀錄 —— ②第一次考試 · 票 A

> 規格正本:`../執行口徑——②第一次考試-v1.md`(一字不改);取證包七項:
> `strategy/specs/提示詞——改善驅動可持續性判斷-v1.md` 第二節。
> 本紀錄只報告工序與數字,不做任何判斷(判斷屬票 B/C)。

## 零、續做說明(上一工人中止點與接手範圍)

- 上一工人 exam2-A-ds 於 **2026-09-12 15:37(本地時間)被系統以記憶體不足中止**。
  中止時已落檔:母體與入口快取(`cache/*.parquet`、`thresholds.json`)、強勢反應子集
  5,867 宗的 EX-99.1 文本與指引正則(`cache/guidance.jsonl`、`edgar_cache/`)、以及
  **抽樣鎖定檔 `picks_before_results.md`(15:37:28 落檔)**。
- 中止時未完成:s8 對照預測、s9 取證包(`packets/` 當時是空的)、s10 匯出、s11 核對、
  s12 統計、本紀錄。
- 本工人 exam2-A2-ds 於 **15:39 接手**,範圍:跑完 s8–s13、修好三處跑不通的缺陷、
  落本紀錄。**沒有重抓 EX-99.1、沒有重抽樣、沒有改動鎖定檔**——鎖定檔的清單雜湊由
  檔內文重算 = `cbaae361fd74ca12d51a4366f7d319dd3aa3ce662fb1a72d04a31fe204d411e9`,
  與鎖定時寫入的相同(核對見第四節第 3 條)。
- 記憶體中止的成因已查明並處理:原 s9/s10 會把 16 個價格檔(2,065 萬列)一次讀入後才
  groupby / rank。`part_*.parquet` 已核實**按 entity 分檔、無 entity 跨檔**(5,260 家、
  跨檔重複 0),故改寫成逐檔掃描的 `pxlib.py`,峰值記憶體由「全部面板」降到「一個檔」。
  改寫後與手工切片逐項比對,16 個數值全等(`check_pxlib.py`,見第四節)。

## 一、腳本清單(全部在 `A/`)

| 腳本 | 做什麼 | 狀態 |
|---|---|---|
| `s1_scan_events.py` | 掃 8-K Item 2.02 業績事件 → `cache/events_raw.parquet` | 上一工人 |
| `s2_price_metrics.py` | 事件窗價格指標(反應日、相對 SPY、相對同業、成交額) | 上一工人 |
| `s3_xbrl.py` | 由 companyfacts 取單季與累計財務數(首報值) | 上一工人 |
| `s4_assemble.py`／`s4b_merger_days.py` | 併母體、宇宙四道閘、合併(Item 1.01)判定 | 上一工人 |
| `s5_fetch_text.py` | 抓強勢反應子集的 EX-99.1 全文(先縮集再抓) | 上一工人 |
| `s6_guidance.py` | 指引上調正則 → `improvement_type` | 上一工人 |
| `s7_sample_lock.py` | 分年分桶抽 84 主 + 44 後備並鎖定 | 上一工人 |
| `s8_controls.py` | 經營對照預測 C1/C2/C3 → `controls_operating.csv` | **本工人跑** |
| `s9_packets.py` | 逐事件建 T1 遮蔽取證包 → `packets/*.json` | **本工人修 + 跑** |
| `s10_export.py` | `population.csv`、`entry_pool.csv`、`thresholds.md` | **本工人修 + 跑** |
| `s11_verify3.py` | 隨機三列人手覆核(T0→反應日、g0 由原件重推) | **本工人修 + 跑** |
| `s12_stats.py` | 全案統計 `cache/stats_summary.json` | **本工人跑** |
| `s13_checks.py` | 驗收條件逐條自查 → `cache/acceptance_checks.json` | 本工人新寫 |
| `pxlib.py` | 逐檔掃描價格面板(取代一次讀入全部) | 本工人新寫 |
| `check_pxlib.py`／`diag_px_size.py`／`diag_part2.py`／`diag_subs.py` | 核對與診斷,非交付品 | 本工人新寫 |
| `finlib.py`／`buckets.py` | 共用:XBRL 數列、六桶對應表 | 上一工人 |

## 二、資料來源路徑

- 申報索引:`data/sec/submissions/CIK*.json`(本地快取 8,121 檔);XBRL:`data/sec/companyfacts/CIK*.json.gz`
- 日線:`data/prices/daily/part_*.parquet`(只取 `series_role == primary`,2013-06 起);SPY:`data/prices/spy_daily.csv`
- 公司與行業:`data/universe/entities.parquet`;代號:`data/universe/ticker_periods.parquet`
- 申報原文(EX-99.1、8-K 本體、10-K/10-Q、對手 10-K):`A/edgar_cache/`(已 gitignore,不入庫)

## 三、六步數字

1. **宇宙公司數**:價格面板 5,260 家(有 primary 日線);母體事件涉及 4,039 家。
2. **母體事件數**:8-K Item 2.02 業績事件 **119,319 宗**(2015-01-05 至 2025-06-30),
   其中過宇宙四道閘 **68,468 宗**。
3. **入口數(三版)**（該年宇宙內事件 `rel_spy ≥ 門檻` 且 `rel_sic2 > 0`）:
   第 95 版 **3,425**、**第 90 版 6,839**、第 80 版 **13,674**。
   **入口池**(第 90 版再加 `improvement_type ≠ 無`)= **4,008 宗**;
   其中六桶內 3,952 宗、「其他」桶 56 宗(不入抽樣層)。逐年門檻值見 `thresholds.md`。
4. **排除分佈**(母體 119,319 宗,可重疊):60 日中位成交額不足 300 萬 47,443;
   上市未滿 12 個月 12,484;無日線 8,172;同日 8-K 有 Item 1.01 2,630;SPAC 3。
   宇宙外合計 50,851 宗。持續經營疑慮:有 34、無 6,777、未核 112,508(未核者不剔)。
5. **每年每桶數**:66 行完整表在鎖定檔 `picks_before_results.md` §每年每桶數量。
   主清單逐年:2015–2024 各 8、2025 年 4,合 84;後備逐年各 4,合 44。
6. **抽樣與補位**:入口池六桶 3,952 宗,按年按桶以最大餘數法分層、桶內以種子 20260912 洗牌
   取前若干。**8 個主清單事件建不成包**,原因全部是「無 XBRL 財務數列」(該宗改善只由
   指引文本判出,沒有可用的單季財務數列);按後備清單補上 8 個,其中 **4 個同年同桶**、
   4 個跨年跨桶(後備清單內已無更接近的可用者)。後備另有 3 個不可建(同一原因),
   其餘 33 個可用而未用。逐條補位紀錄:`cache/packets_substitutions.json`。

### 指引文本抓取(先縮集、後抓文本;次序照執行口徑第二節)

先以價格門檻(當年第 90 百分位、相對 SPY 為正且相對同業為正)縮到**強勢反應子集 5,867 宗**,
只對這個子集抓文本;母體其餘列的指引欄標「未評」。每宗最多兩個請求(申報索引頁 + 全文),
索引頁解析不到 EX-99.1 才多要一個 `index.json`。三次執行(s5)共 **5,867 宗,成功 5,839 宗,
28 宗該申報無 EX-99 附件**。s6 以正則(raise/increase/increasing 配 guidance/outlook 並附數字)
判出 `improvement_type`。入口池 4,008 宗的組成:指引 1,483、加速 1,433、兩者 1,092;
全母體 119,319 宗之中 112,508 宗標「未評」(不在強勢反應子集內,沒有抓文本)、2,789 宗為「無」。

本工人接手後 s9 另行抓取 **427 份**文件(8-K 本體、最近 10-K/20-F、最近兩份 10-Q/6-K、
對手 10-K),單線程、3 請求/秒,分三段(120 + 150 + 157)跑完。`edgar_cache/` 現有 19,995 檔。

### 取證包與對照

- `packets/`:84 包(反應日 2015-02-03 至 2025-05-07),每包八節照提示詞 v1 第二節,
  含 EX-99.1 全文、同日 8-K 項目、截止前文件(只留本地路徑與 EDGAR 網址)、
  截止前八季財務數列、同業名單與兩個最大同業的年報資本開支摘錄、T1 價格狀態、
  共識一律「查不到」、`masking_check`。**84 包 EX-99.1 全文全部有值、0 包遮罩不合。**
- `controls_operating.csv`:128 行(主 84 + 後備 44,逐事件一行),C1 指引隱含餘下季度
  增速有值 12、C2 前四季平均有值 111、C3(=g0)有值 114;**不入任何取證包**。
  C1 抓不到的主因:指引窗內抓不到「財年收入指引中值」(90 宗)、無 EX-99.1 文本(11 宗)、
  指引中值不高於已報累計收入(10 宗)、去年餘下期間收入非正(4 宗)、無去年同季期末(1 宗)。

## 四、驗收條件逐條核(以反例核;機器輸出 `cache/acceptance_checks.json`)

1. **population.csv** 存在:**119,319 列 × 56 欄** ≥ 入口池 4,008 列;識別欄(accessionNumber、
   cik、ticker、sic2、fiscal_quarter、cluster_id、repeat_company_flag、adr_flag、covid_window、
   improvement_type、reaction_date、t2_date)與 `exclusion_reason` 全部在,無缺欄。
   隨機三列覆核(種子 20260912 由入口池抽,`cache/verify3.md`):
   DY 2016-05-25、DVN 2022-05-03、SBRA 2022-05-05 —— **反應日、T1 還原收市、反應報酬、
   相對 SPY、g0 五項全部相符**(g0 例如 DY 0.349909 對 0.349909)。
2. **entry_pool.csv**:4,008 列,`rel_spy` 低於當年第 90 百分位者 **0 列**、
   `improvement_type` 為「無」者 **0 列**、`rel_spy` 缺值 **0 列**。
3. **鎖定檔未被改動**:檔內清單逐行重算的雜湊 = `cbaae361…`(與鎖定時相同;84 + 44 列),
   全檔 SHA-256 `dd84d0fa…`。落檔時間 **15:37:28**,早於 `controls_operating.csv`(15:39:25)
   與 `packets/` 最早一檔(15:47:53),早 625 秒。
4. **包內無 T1 之後資料**:84 包 `masking_check.verified` 全為真,包內最晚資料日期最大值
   2025-05-07。逐包掃描全文的 ISO 日期,反應日之後只出現兩種:(a) `T2_可成交`(反應日後
   首個交易日開市,屬規格內欄位,只有日期、不含 T2 價格);(b) 一宗假命中 —— E043 內
   `0000882095-20-000006` 是對手年報的申報編號,不是日期。**無其他越界。**
   觸發 EX-99.1 全文缺者 **0 包**;資料不足名單因此為空(主清單 8 宗缺 XBRL 者已由後備補位)。
5. **controls_operating.csv** 128 行、逐事件一行(無重複),含 C1/C2/C3 三欄;
   84 個取證包全文掃描,**無任何包含對照預測欄或該檔內容**。
6. **本紀錄**含六步數字與續做說明;`strategy/`、`karst/`、`library/`、`tools/` 與既有
   research 輸出**未改**;未 commit。`s12_stats.py` 記下執行時的 git HEAD = `1a47df2`,
   以及 `strategy/`、`karst/`、`library/`、`tools/` 四個目錄的 git status =「(乾淨)」。

## 五、跑不通或規格不清之處與處理

1. **s9 `m["accessionNumber"]` 取不到**(`set_index` 把該欄收走)→ 補回該欄。此錯令 s9
   從未成功跑過,`packets/` 之前一直是空的。
2. **s11 `g["date"].dt` 報錯**(讀 parquet 後未轉日期型別)→ 改為由 `pxlib` 取價。
   此錯同樣令 s11 從未成功跑過。
3. **s9 補位未按鎖定檔的「同年同桶優先」**(原碼按後備清單全表次序補,亦會靜默消耗不可建
   的後備而不留紀錄)→ 改為同年同桶優先、逐個記原因。實際結果:8 個補位中 4 個同年同桶。
4. **記憶體**(上一工人的死因)→ 新增 `pxlib.py`,逐檔掃描;`s9` 與 `s10` 均已改用它。
5. **規格不清,留待票 B/C 或裁決**:
   - 鎖定檔內文寫「後備同規則每年 4 個(**2025 兩個**),合共 44」,但同檔的後備清單與
     實際抽出都是 2025 年 4 個、合共 44 個(10×4+4)。**文字與清單不一致**,清單為準
     (票面亦寫 44)。鎖定檔不得改動,故只在這裡記明。
   - `buckets.py` 的六桶對應表是上一工人自訂(執行口徑只寫「SIC 兩位數合成六桶」,
     沒有給表)。其中 SIC 28(化學品)歸入「醫療」桶,實務上可議;表已原樣抄進鎖定檔,
     本工人沒有改。
   - 主清單 84 宗之中有 8 宗(9.5%)沒有可用的單季財務數列,入口是靠指引文本判出的。
     照票面「建不成 → 由後備補」處理,但這意味**入口池本身有相當比例的事件沒有 XBRL 數列**;
     票 B/C 若要報「母體」數字,需知悉這一點。

## 六、時間戳(驗收條件第 3 條)

| 檔 | 落檔時間(本地) | 備註 |
|---|---|---|
| `picks_before_results.md` | 2026-09-12 15:37:28 | 鎖定檔;SHA-256 `dd84d0fa…` |
| `controls_operating.csv` | 2026-09-12 15:39:25 | 晚 117 秒 |
| `packets/` 最早一檔 | 2026-09-12 15:47:53 | 晚 625 秒 |
| `packets/` 最後一檔 | 2026-09-12 15:47:53 | 84 包同一次寫入 |
| `population.csv`／`entry_pool.csv`／`thresholds.md` | 2026-09-12 15:48 | |

## 七、本輪產物

- 交付品:`population.csv`、`entry_pool.csv`、`thresholds.md`、`controls_operating.csv`、
  `packets/*.json`(84)、`執行紀錄——A.md`。
- 附帶檔:`cache/verify3.md`、`cache/packets_log.csv`、`cache/packets_substitutions.json`、
  `cache/acceptance_checks.json`、`cache/stats_summary.json`、`pxlib.py`、
  `s13_checks.py`、`check_pxlib.py`、`diag_*.py`。
