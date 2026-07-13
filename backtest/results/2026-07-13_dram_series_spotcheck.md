# DRAM 合約價序列 spot-check —— 雷達 D 第一條驗證【2026-07-13】

> 承接 `docs/2026-07-12_new_sleeve_candidates.md` 候選 D(第三方產業數據做 magnifier 入場升級)+
> `docs/2026-07-12_opportunity_ladder.md` §1 表格對 D 嘅要求:「唔係一個大 backtest,係逐條數據
> 序列驗過先信……DRAM 合約價喺 MU 2016/2023 兩輪嘅拐點位對返股價」。呢份係第一條驗證,過唔過關
> 決定雷達 D 接唔接呢條序列。方法/產物依 Fable 交接書 P1-9 要求執行。

## 0. 驗證標準(先讀候選 D 原文 + 已有校準文件)

`new_sleeve_candidates.md` 候選 D 段原文:「MU 2016 嗰課……5/5 features 全亮,係因為供給確認
來自 TrendForce 產業數據(合約價兩個月 +20%、渠道庫存跌穿常態),唔使等公司自己開口;而 MU 2023
嗰次靠公司電話會語言,足足遲咗財務底四個月、股價已彈 38-60%」。即候選 D 想驗嘅係:第三方數據
拐點,能否比「等公司自己喺 transcript 度確認」更早/唔滯後。`docs/2026-07-12_magnifier_scorecard_rubric.md`
§3b/§4/§7 已經用 2023 case 精確量化咗「公司語言 vs 財務底」呢一段(落後 4 個月),但**冇拿住合約
價序列本身去對股價**——呢個正正係本次 spot-check 要補嘅缺口,亦係「逐條序列驗」嘅第一條。

## 1. 數據可得性評估(先講結論:免費完整數值序列攞唔到,只有免費文字新聞稿)

| 數據源 | 試過嘅方法 | 結果 |
|---|---|---|
| TrendForce 官方合約價數值下載(DRAM Contract Price 月報) | WebFetch `trendforce.com/research/download/...` 系列頁面 | **要 Gold+ Membership**——研究頁本身列明落地下載係付費會員功能,免費用戶只見標題/摘要 |
| DRAMeXchange Historical Price Download Center | WebFetch `dramexchange.com/intelligence/historical_price` | 頁面有 Member Center 登入入口,「download/print extracts……for personal non-commercial use」字眼曖昧——**未能確認完全免費**,傾向係要login(見§5未解項) |
| TrendForce 新聞稿(presscenter) | WebFetch `trendforce.com/presscenter/news/20231013-11880.html`(2023-10-13 篇)| **確認免費、唔使 login 就讀到全文**——但呢啲係文字新聞稿(方向性 %QoQ 敘述),**唔係連續數值時間序列**,發布頻率唔定期(2023 年一整年淨係搵到呢一篇明確轉向報導,2025-26 反而密咗、幾乎逐月一篇——反映呢個源嘅可用性隨產業熱度波動,唔係穩定 cadence) |
| Stanford DAM Memory Prices project(`dam.stanford.edu/memory-prices.html`) | WebFetch | **免費、月度 CSV 可下載**,但係**零售/spot 價**(DRAM/NAND 部分嚟自 Keepa 亞馬遜價格追蹤),**唔係 B2B 合約價**——性質唔同,只能做 proxy,未經校對(見§5) |
| repo 現有 corpus/transcript FTS(`thesis/corpus.py`)| 檢視 MU/SNDK transcript 索引 | 有,但呢條係「管理層開口」路徑——**正正係候選 D 想繞開嘅舊機制**,唔可以當第三方獨立序列用 |
| yfinance 股價 | 用於股價底核對(下面§2) | **只用作 MU 股價本身嘅參照,唔用嚟冒充合約價**——嚴守驗收條件 4 |
| 對照組:TWSE 月度營收(`thesis/altdata_twse.py`)| 讀現有接線 | **官方 OpenAPI,免費、無需 key、結構化 JSON**,已經正式接線做 WS4 altdata 输入——呢個係「乾淨」第三方序列嘅範本,DRAM 合約價**冇對應嘅官方免費 API**,兩者唔同級 |

**小結**:DRAM 合約價「序列」層面攞唔到免費、可重複下載嘅逐月數值——呢個係本 spot-check 嘅
答案之一。可攞到嘅係 TrendForce 免費新聞稿入面嘅**方向性文字**(升/跌、約 X-Y% QoQ 範圍),
要人手/agent 定期讀 + 解讀,唔係一條乾淨時間序列。

## 2. 兩輪拐點校對(月份粒度)

### 2016 輪

| 事件 | 日期 | 數字 | 出處 |
|---|---|---|---|
| MU 股價絕對底 | **2016-05-13** | 收盤 $9.56 | yfinance 一手核實(本次拉取,`Close.idxmin()` 於 2015-06~2016-12 窗),與案例庫既有 $9.56 完全吻合 |
| TrendForce/DRAMeXchange 合約價轉向訊號 | **2016-09~10**(兩個月窗) | 4GB PC DRAM 模組合約價 $14.5→$17.5(**+20%**);渠道存貨跌至 3-4 週(正常 8 週) | `backtest/results/2026-07-09_magnifier_case_library.md` 週期 7a(原案例庫記載)+ WebSearch 二次核實(DRAMeXchange/TrendForce 原文經 TechPowerUp 轉載,數字一致) |
| 公司 transcript 語言轉向確認 | 未有精確日期 | — | constraint-language 追蹤機制要到 2023 案例先起(`magnifier_scorecard_rubric.md`),2016 呢輪冇同等量化記錄,只有質性講法「唔使等管理層開口」 |

**Lag(合約價訊號 相對 MU 股價絕對底)**:2016-05-13 → 2016-09/10 中點(約 09-30)≈ **4.5 個月,滯後**。

### 2023 輪

| 事件 | 日期 | 數字 | 出處 |
|---|---|---|---|
| MU 股價絕對底(全個下行段,2022-06~2023-12 窗內搜尋) | **2022-09-26** | 收盤 $48.88 | yfinance 一手核實(本次拉取) |
| 「真.財務底」(FQ4 FY23 收入/毛利率谷底) | **2023-08** | 收入 $4.0B、毛利率 −10.8%(vs FY22 常態 ~46.7%/$8.6B) | `docs/2026-07-12_magnifier_scorecard_rubric.md` §3a(已有一手 defeatbeta 核實) |
| TrendForce 合約價轉正首度預告(連續多季下跌後首次) | **2023-10-13** | Q4 2023 DRAM/NAND **全線 +3-8% QoQ**(PC DDR5 3-8%、Server DDR5 3-8%、Mobile LPDDR5(X) 5-10%、Graphics 3-8%) | `trendforce.com/presscenter/news/20231013-11880.html`(本次 WebFetch 核實免費可讀、日期、數字) |
| 公司 transcript constraint-language 轉正 | **2023-12-20** | 全 2023 年 constraint-language ≈0/負,直到呢日先首次轉正 | `docs/2026-07-12_magnifier_scorecard_rubric.md` §3b/§4(已核實) |
| 對照:MU 股價喺各節點 | 2022-09 $48.88(底)→2023-08 ~$70→2023-10 ~$67-70→2023-12 $85.34 | — | yfinance 月度收盤(本次拉取) |

**三組 lag/lead(合約價訊號 2023-10-13 為錨點)**:
- 相對 **MU 股價絕對底**(2022-09-26):**滯後約 12.5 個月**——股價喺合約價訊號出現前已經彈咗
  35-43%,呢個滯後幅度遠大過 2016 輪
- 相對 **真.財務底**(2023-08):**滯後約 1.5 個月**——方向合理,幾乎同步
- 相對 **公司 transcript 確認**(2023-12-20):**領先約 2 個月**——即係候選 D 原本想證嘅嗰種
  「快過等管理層開口」效果,呢部分**確實成立**

## 3. 結論:**PARTIAL**

一句理由:合約價序列冇免費可重複嘅數值下載(只有唔定期嘅免費新聞稿文字)、而且相對 MU 股價
自身嘅底係**滯後**(2016 滯後 4.5 個月,2023 滯後 12.5 個月)——所以佢**唔係「領先股價」嘅入場
工具**;但相對現行「等公司自己喺 transcript 開口」機制,佢確實**領先約 2 個月**(2023 案例量化),
方向同財務底幾乎同步——即係話佢對現有 pipeline 有邊際價值,但唔夠格做獨立/搶先觸發源,亦唔應該
定位做「早過股價」。

拆解三個判準:
1. **數據可得性**:免費、但唔完整、唔規律——不夠「PASS」門檻(門檻要求可重複攞到序列),又
   未至於完全攞唔到(有免費新聞稿可讀)——不是「FAIL」
2. **訊號方向性**:相對股價底,兩輪都滯後(4.5 個月 / 12.5 個月),同候選 D「呢個 sleeve 令
   magnifier 買得早過而家成個流程」嘅字面期望(「早過股價」)有落差;但相對現行「靠 transcript
   確認」機制,確實提早(~2 個月)——呢個先係候選 D 應該量度嘅正確 baseline(唔係股價底,係
   現行機制)
3. **操作成本**:要人手/agent 定期讀新聞稿、解讀方向性語言,唔係掛一個 API 就有數——中等成本,
   同 TWSE 那種「掛咗就唔使諗」嘅乾淨 API 唔同級

三選一唔可以騎牆:因為第 3 點(操作成本非零、要人手更新)+ 第 2 點(唔係「早過股價」,係「早過
transcript」而已)已經令佢唔夠 PASS 資格,但佢真係有量化嘅邊際價值(2 個月領先 transcript)、
唔應該 FAIL 掉——故判 **PARTIAL**。

## 4. 如果接:點接入建議

- **檔案格式**:唔起「downloadable numeric series」幻想,改用「新聞稿監控」模式,仿現有
  `thesis/altdata_twse.py` 嘅結構起 `thesis/altdata_dram_price_watch.py`——WebFetch/WebSearch
  `trendforce.com/presscenter` 分類頁,擷取合約價方向性語句(升/跌、%QoQ 範圍、產品分類),
  append 一行到 `thesis/.raw/altdata_dram_price_history.jsonl`(欄位:date/segment/direction/
  pct_range/source_url),同 TWSE 果份一樣 dedup、gitignored
- **更新頻率**:建議**雙週**檢查一次(唔係 TWSE 嗰種週檢查即可,因為呢個源發布唔定期——
  2023 年成年淨一篇明確轉向報導,2025-26 反而密咗)。雙週 cadence 夠應付「有就讀,冇就 no-op」
  嘅 pattern,唔使日日掃
- **邊個 job 讀**:唔應該做獨立 trigger,應該掛喺現有 `thesis/theme_signal.py` /
  `thesis/discovery_radar.py`(讀 constraint-language 嗰條管道)**平行**做多一個輸入欄位——
  定位係「confirm layer 之一」,同 constraint-language 一齊睇,兩個都 fire 先加分。**唔應該單獨
  做 sole trigger**,尤其唔應該用嚟「catch 底部」——兩輪校對都顯示底部由宏觀/市場情緒主導,行先
  過任何基本面或產業數據好多個月,冇一種現有方法(財務、transcript、第三方數據)追得到絕對底
- **定位修正**:候選 D 原文「令 magnifier 買得早過而家成個流程」嘅講法要收窄——收窄做「早過
  等 transcript 確認嗰 ~2 個月」,唔係「早過股價底」。呢個修正同 rubric 已有嘅
  §3b/§4「股價比 constraint-language 更早」發現係同一條邏輯線嘅延伸:股價行先呢個現象唔止
  影響公司自己嘅語言,連第三方產業數據都跑輸市場——市場定價快過任何非市場訊號源,呢個係跨
  訊號源都成立嘅通則,值得寫入 rubric 做補充註腳

## [未解 / 風險]

1. 2016 輪「公司語言確認日期」冇精確記錄——constraint-language 追蹤機制起源於 2023 案例分析,
   2016 嗰輪淨係定性講法「唔使等管理層開口」,冇對應嘅量化 lag/lead 數字可對比,令 2016 輪嘅
   「領先 transcript」結論比 2023 輪弱(2023 有精確 2 個月數字,2016 冇)
2. DRAMeXchange Historical Price Download Center 嘅真實付費門檻未 100% 確認——WebFetch 攞到嘅
   頁面文字曖昧(有 login 入口但冇明確「must pay」字句),值得日後想認真接入前再核實一次
3. Stanford DAM 嘅零售/spot 價 proxy 未做校對——冇攞嚟同 2016/2023 MU 拐點對比,如果將來想用
   佢做免費補充 proxy,要另外驗證 spot 價相對真.合約價嘅 lead/lag 關係(業界一般認為現貨價
   領先合約價 1-2 季,因合約價係季度議價、較黏,但呢個假設本次未驗證)
