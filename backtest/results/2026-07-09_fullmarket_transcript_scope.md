# Result — Transcript prefetch 擴展至全市場宇宙(unknown-unknowns discovery)

**Date:** 2026-07-09
**Script:** `thesis/prefetch_transcripts.py`(新增 `--universe full` / `--sample-n` / cursor-resumable 全市場模式)
**Tag:** infra/scope 擴展 — 非訊號回測;為 Phase-3 早期偵測(未知超級週期)鋪 raw material

> 現有 `thesis/prefetch_transcripts.py` 只抓 63 個主題監察 ticker 嘅 earnings-call transcript。
> Phase-3 嘅早期偵測目標係全市場掃描(搵**未知**嘅新興超級週期,唔係監察已知主題),所以呢次
> 將 prefetch 嘅宇宙由 63 隻擴到 defeatbeta 有 transcript 覆蓋嘅全部股。本檔記錄:宇宙來源揀選、
> 規模估算方法同結果、實際跑咗嘅進度、續跑指示。

## 1. 宇宙來源揀選

三個候選,按 spec 指定優先次序試:

1. **defeatbeta 自己嘅 ticker 清單 API**(最終採用)—— `defeatbeta_api.data.company_meta.
   CompanyMeta.get_all_tickers()` / `get_all_companies_info()`,底層係 huggingface 託管嘅
   `company_tickers.json`(defeatbeta 自家 SEC ticker/CIK 映射,加一小撮 no-CIK ETF 補充)。
   呢個先前冇被留意到 —— repo 入面冇任何腳本用過 `company_meta.py`,`Tickers`(複數)class 都要求
   預先俾定 ticker list,唔提供 discovery。翻查 package 原始碼(`defeatbeta_api/data/tickers.py`,
   `company_meta.py`)先揾到 `get_all_tickers()`。
2. `backtest/.insider_data/px_defeatbeta.pkl`(6,769 隻,insider-Form4-active 廣度宇宙,
   `exp_magnifier_case_library.py` 提過)—— 冇用到,因為 (1) 已經夠、仲要更闊。
3. NASDAQ/NYSE symbol directory(WebFetch)—— 冇用到,因為 (1) 已經係 defeatbeta 自己嘅 index,
   保證同 transcript 資料庫同源,唔會出現「有 ticker 但 defeatbeta 完全唔識」嘅落差。

**驗證**:defeatbeta 全清單原始 10,417 隻,現有 66 隻預設(thesis.yaml 主題 + EXTRA_WATCHLIST)
之中只有 `DRAM`(ETF)、`SIVE`(新股)呢兩隻唔喺 defeatbeta 清單入面 —— 同現有 docstring 講嘅
「ETFs like DRAM / new listings like SKHY/SIVE fail gracefully」完全對得上,確認呢個係正確、
最闊嘅來源。

### Filter(去重、隔走明顯 ETF/非個股)

由 10,417 隻原始清單過濾走:

| 類別 | 判斷方法 | 數量 |
|---|---|---|
| No-CIK ETF 補充包 | `cik is None`(defeatbeta 自己加落去嘅純 ETF,如 IVV/IJR/MTUM/QUAL/USMV/IWM/VTV/TLT/JNK) | 10 |
| SPAC warrant/unit/rights | regex `-(WT\|WS\|UN\|RT\|U\|R)$`(如 KCAC-UN、GRAF-WT、OXY-WT、GME-WT) | 115 |
| 優先股 | regex `-P[A-Z]?$`(如 JPM-PC、BAC-PB、USB-PA、WFC-PY) | 387 |

**刻意保留**:雙股權普通股(BRK-B、BF-A、MOG-A、BH-A 等)—— 呢啲係獨立上市、有自己 earnings
call 嘅普通股,唔係 ETF/優先股/warrant,唔應該隔走。REIT/Trust/Fund 命名(DLR「Digital Realty
TRUST」、VNO「VORNADO REALTY TRUST」等)一樣保留 —— 用 name regex 隔嗰批會誤殺大量正常上市
REIT,所以冇用呢個做法。

過濾後 **9,905** 隻,加返安全網(union 現有 66-ticker 預設宇宙入面缺咗嘅 2 隻,DRAM/SIVE 本身
唔喺過濾後清單,但都會保留喺 union 入面等佢自然 fail-gracefully)—— 最終 `--universe full`
宇宙 = **9,907 隻**。

**排序**:defeatbeta 原生 idx 順序(NVDA=0、AAPL=1、GOOGL=2、MSFT=3... 大致按市值/知名度排),
唔係字母序。呢個排序對 cursor-resumable 嘅分段跑好有利 —— 時間跑唔切嘅話,partial run 自然
優先蓋到最多人識、最大機會有 transcript 嘅名(較高 hit-rate/單位時間),留返 OTC/micro-cap 尾
巴俾之後續跑。

## 2. 規模估算方法

`--universe full --sample-n 200 --seed 42`:由過濾後 9,907 隻用固定 seed 隨機抽 200 隻(唔係
淨揀最前 200 隻,避免用 idx 排序嘅頭部大 cap 去外推成個宇宙會嚴重高估——大 cap 密集覆蓋、
transcript 又多又長,同尾段 OTC/micro-cap 分布完全唔同)。抽樣結果**真係落地**(檔案寫入
`thesis/.raw/transcripts/<TICKER>/`),對最終覆蓋有貢獻,唔係拋棄嘅 throwaway 測試。

量度:每隻 ticker 嘅 fetch wall time(`elapsed_s`)、新存檔案數(`n_saved`)、新存 bytes
(`n_bytes_saved`,`out_path.stat().st_size` 實測,唔係估)。外推:`avg × 9,907`。

## 3. 規模估算結果

200 隻樣本(`seed=42`,sleep 0.4s,`thesis/.raw/transcripts/_sample_benchmark.json`)實測:

| 指標 | 樣本值(n=200) | 每隻平均 | 外推 × 9,907 |
|---|---|---|---|
| 有 transcript(hit) | 107(**53.5%**) | — | ≈5,300 隻 |
| 空(0 listed:ETF/新股/OTC/defeatbeta 未收) | 93(**46.5%**) | — | ≈4,600 隻 |
| list 失敗(crash) | **0** | — | ≈0 |
| 新存 transcript **JSON** 檔數 | 3,616 | 18.1 檔/隻 | **≈179,000 檔** |
| 新存 **JSON** disk | 175.8 MB | 0.86 MB/隻 | **≈8.7 GB** |
| Fetch wall time | 749 s(單線程) | 3.34 s/隻(+0.4s sleep) | **≈10.3 小時**(單線程) |

- 平均值用**成 200 隻**(含 46.5% 空隻)計,對外推正確 —— 全宇宙一樣有咁上下比例嘅空隻。
- 分布極右偏:median 新存檔 = **1**,hit 到嘅大 cap 有 34-81 檔(最多 XELLL=81)。idx≈市值序,
  所以 partial run 優先蓋覆蓋最深嘅大 cap,尾巴 OTC 多為空隻。
- 0 隻 `failed_list`:per-ticker try/except gracefully skip 生效,冇一單 crash。

### ⚠ 但 JSON 大細唔係 binding constraint —— HuggingFace parquet cache 先係

**呢個係我最初估算漏咗、之後 disk 實測揭穿嘅關鍵。** 上表「≈8.7 GB」淨計 defeatbeta 吐返嚟嘅
**JSON 輸出**;但 defeatbeta 底層係由 HuggingFace 拉 parquet dataset shard 落本地 cache
(`~/.cache/huggingface`)先 query。掃得越多唔同 ticker,佢就拉越多 shard。實測:200-sample +
被中止嘅 full run 之後——

| 位置 | 現時大細 |
|---|---|
| `thesis/.raw/transcripts/`(JSON 輸出,gitignored) | 469 MB |
| **`~/.cache/huggingface`(defeatbeta parquet backing cache)** | **11 GB** |
| `C:/Users/Kaho/AppData/Local/Temp/defeatbeta`(duckdb temp) | 799 MB |
| `thesis/corpus.db`(FTS index) | 697 MB |

即係話:抽 200 隻 + 少少 full-run 已經令 HF cache 谷到 11 GB。掃全 9,907 隻會拉落大部分
defeatbeta transcript parquet 全集,呢嚿(唔係 JSON、唔係 corpus.db)先係真正食幾十 GB 嘅嘢。
所以「JSON 8.7 GB fits」係**錯判**——真實 footprint 由 HF cache 主導,遠大過 JSON。詳見 §4 裁定。

## 4. 磁碟空間檢查

執行前 `Get-PSDrive C`:**Free = 34.6 GB**(C: 總用量 476 GB/511 GB)。已抓 63-ticker 監察宇宙
現時佔 197 MB(64 個有 transcript 嘅 ticker 目錄)。

### ✅ DISK VERDICT 修正(2026-07-09 晚,用戶質疑後實測):原裁定基於錯誤前提,已翻轉

**原「disk-blocked」裁定錯咗。** 用戶質疑「parquet 冇可能淨係 transcript」→ 實測 `~/.cache/huggingface`
11GB **根本唔係 defeatbeta**,而係無關 ML 模型(GLM-ASR 4.3G / faster-whisper 2.9G / Florence 1.5G /
twhin-bert 1.1G / docling 等,全部 `hub/models--*`,其他 project 遺留)。defeatbeta 真正 cache =
`AppData/Local/Temp/defeatbeta` = **799MB**(144 ticker)。HF hub 冇任何 defeatbeta/datasets 目錄。

**修正後全市場估算**:JSON ~8.7GB + defeatbeta cache ~幾GB(799MB→擴,未定會唔會脹)+
corpus.db(**word tokenizer** ~12GB / trigram ~26GB)= working set **~20-25GB**。現有 free 31.6GB →
**塞得落(緊)**;刪/搬 11GB 無用 ML 模型 → free 42GB 舒服。**唔使買大 drive。**

行動:①corpus 換 word tokenizer(實測慳 2.2x:143→64 KB/doc,≈Casy 56KB parity,兩者都存原文);
②partial run(~1000 隻)睇實 defeatbeta Temp cache 會唔會脹到失控(唯一剩低 unknown);
③可選清無用 ML 模型。原文以下段落為**已作廢**嘅錯誤裁定,留檔記錄誤判(HF cache misattribution)。

### ⛔ [已作廢,誤判留檔] DISK VERDICT(2026-07-09,主腦裁定):全市場 marathon PAUSED — disk-blocked

- 200-sample 跑到 144 ticker / 6195 檔 / **330 MB** 後,C: free 由 34.6 → **31.6 GB**。
- 外推:9,907 隻全宇宙 raw transcripts ~10-31 GB(視乎 transcript hit-rate)+ corpus.db FTS
  全市場索引(現 3623 doc=696 MB → 全市場 ~50 萬 doc 可達 50-100 GB)= **合計遠超 31.6 GB free**。
- **不可 launch**:會填爆 C: 令系統失效。呢個係實體限制,唔係流程問題。
- **已安全落地嘅**:theme 監察宇宙(63)+ 200 sample = 144 ticker/6195 檔/330 MB,corpus.db 已 index。
  呢批夠開始 magnifier/scanner 工作。

**用戶要決定(先解 disk 先能建 full-market discovery)**:
1. 清 C: 空間 / 加外置或第二個 drive,搬三樣去大 drive:
   **(a) `~/.cache/huggingface`(真.空間殺手,掃全市場會谷到幾十 GB —— 用環境變數 `HF_HOME=D:\...`
   重定向,唔使搬 code);(b) `thesis/.raw/transcripts/`(JSON 輸出);(c) `thesis/corpus.db`(FTS)。**
   三者全 gitignored / 可重生,改 path 就得。**⚠ 只搬 (b)+(c) 唔夠 —— HF parquet cache (a) 先係主要 footprint。**
2. 或做**分段 partial**:defeatbeta idx 順序(大 cap 優先)只跑頭 N 隻塞得落嘅,尾巴 OTC/micro 留待;
3. 或**index 後刪 raw**(corpus.db FTS 已存全文,raw .json 索引後可刪 → 慳一半),但 DB 本身
   全市場級都可能超 31.6 GB。
- **weekly_corpus.cmd 現時 stay `--universe default`(theme 監察)係正確**(唔會填爆 disk);
  disk 解決後先切 `--universe full`。

## 5. 實作改動(`thesis/prefetch_transcripts.py`)

- `build_full_universe()`:讀 `CompanyMeta().get_all_companies_info()`,過濾走上面三類非個股,
  同預設宇宙 union 做安全網,回傳 defeatbeta 原生 idx 順序嘅 list。
- `fetch_ticker(tk, verbose=True)`:加 `verbose` 開關(全市場模式關咗佢,淨留 progress-line,
  唔會逐份 transcript 都 print,避免洗爆 log);加 `n_bytes_saved`(逐檔 `stat().st_size` 累加)
  俾規模估算用。per-ticker try/except 同原本一樣,失敗/空清單 gracefully skip、記錄落
  summary,唔會 crash 成個 run。
- Cursor-resumable:`_full_universe_cursor.json` 記低 `last_idx`(下次由邊度續)同
  `universe_size`;`_coverage_summary_full.json` 逐 ticker 累積(唔止最後一次 run 嘅結果),
  每 `--progress-every`(預設 50)隻 flush 一次落磁碟,中途斷咗都唔會蝕晒呢一段進度
  (loop 包咗 `try/finally`,再加 periodic flush 做雙重保險)。
- `--universe {default,full}`(預設 `default`,行為同以前完全一樣,唔影響現有 63-ticker
  日常 sync);`--limit N`(呢次 invocation 最多行幾多隻,配合 cursor 分段跑);`--sample-n N`
  + `--seed`(抽樣估算模式,唔碰 cursor);`--sleep`(override 每隻之間嘅 politeness delay,
  全市場模式預設 0.4s,原本 63-ticker 模式維持 0.7s 唔變)。
- `.gitignore` 第 22 行 `thesis/.raw/transcripts/` 本身已經蓋晒成個目錄(包括全市場新加嘅
  ticker 目錄),唔使加新規則。

## 6. 進度 + 續跑指示

**已落地(landed）**:63 theme 監察宇宙 + 200 隻隨機樣本(seed 42),即約 144 個有 transcript 嘅
ticker 目錄 / 469 MB JSON。呢批已對最終覆蓋有貢獻,續跑時 sequential walk 行到佢哋會 `already_had` skip。

**Full sequential run 狀態:PAUSED(disk-blocked,見 §4 主腦裁定)。** 我曾 launch
`--universe full --limit 1000`,但喺 §4 disk 實測揭穿(HF cache 已 11 GB)後**主動中止**——
繼續會填爆 C:。中止喺首個 50-隻 checkpoint 之前,冇寫 cursor,冇 partial state 污染。

**disk 解決後點續(cursor-resumable,冪等)**:
```
# 分段(推薦,大 cap 優先):每次一段,cursor 自動記住行到邊
PYTHONUTF8=1 python thesis/prefetch_transcripts.py --universe full --limit 500
# 再 run 同一句 → 由 cursor last_idx 續下一個 500;直到行完 9,907
# 或一次過(需先確保 disk 夠 + HF cache 位):
PYTHONUTF8=1 python thesis/prefetch_transcripts.py --universe full
```
cursor 檔:`thesis/.raw/transcripts/_full_universe_cursor.json`;逐 ticker 累積覆蓋:
`_coverage_summary_full.json`。兩者都喺 gitignored 目錄內。

