# 分析師出席人數(Q&A)作為 crowding/attention 代理指標 —— 可行性探測

**日期**: 2026-07-12
**腳本**: `backtest/experiments/exp_analyst_attendance.py`
**資料源**: `thesis/corpus.db`(FTS5,歷史財報電話會議全文,免費、隨季更新)+ defeatbeta `ttm_pe`(交叉驗證用)
**背景**: Magnifier rubric feature 5(sentiment/crowding)長期無量化代理 —— institutional ownership 同
analyst-coverage-count 都只係 yfinance 嘅 snapshot(冇歷史),turnover 已測試無 edge
(`backtest/results/2026-07-11_institutional_ownership_crowding_axis.md`,本次依指示不重測)。
本探測驗證:電話會議 Q&A 環節「有幾多個唔同分析師發問」呢個歷史序列,是否可以填呢個缺口。

---

## [結論]

**方向性成立、幅度溫和 —— 建議升格為「排名/own-history percentile」輸入,唔好做獨立訊號。**
橫截面上 6 隻股嘅出席人數排序(AVGO 13.5 > NVDA 11.6 > MU 10.8 > FSLR 9.1 > WST 5.1 > USAC 3.6)
完全符合「邊隻愈多人關注」嘅先驗直覺,USAC(Discovery Radar 話係 2nd percentile 未被發現)出席人數
全場最低,係好強嘅正面證據。MU 時序上,2023-09-27(「dead cyclical」谷底期)出席人數跌到全History
20年**並列最低**(4人),2024-12-18(供應緊張敘事高峰)彈返到 post-2019 並列最高(12人)——方向啱,
但底部期(6.71)vs 復甦期(7.43)嘅平均差只係 +11%,而且兩期都低於全史平均(10.77),反映 MU 有結構性
覆蓋率長期下滑,原始人數要控制呢個 secular trend 先可比較。過程中揪出並修正咗一個會令 2013-2019
整段靜默出錯(誤判做 n=1)嘅解析 bug——修正後總失敗率 1.6%(7/434 季),健康。

---

## [證據] MU 底部 vs 而家出席數 + 對照組讀數

### MU 核心問題:2022-2023 谷底 vs 2024-2025 共識期
| 期間 | 定義 | 平均出席人數 | 季數 | Range |
|---|---|---|---|---|
| 谷底(股價$49-50,「dead cyclical」) | 2022-06-01 ~ 2023-12-31 | **6.71** | 7 | 4-8 |
| 供應緊張共識期 | 2024-06-01 ~ 2025-12-31 | **7.43** | 7 | 5-12 |
| 全史(2006-2026) | — | 10.77(median 11.0) | 79 | 4-21 |

關鍵單點:
- **2023-09-27(FY23 Q4)= 4 人**,同 2006-06-28 並列全史(20年)最低紀錄 —— 谷底確實出現咗
  「多年低點」,答案係**確認性(confirmatory)**,唔係反向(冇出現「執平貨嘅人湧入」嘅反向訊號)。
- **2024-12-18(HBM/AI 供應緊張敘事高峰)= 12 人**,並列 post-2019 時代最高讀數。
- 但兩個窗口嘅平均(6.71、7.43)都低於全史平均 10.77 —— MU 由 2015 年起有結構性覆蓋人數下滑
  (2006-2014 era 常見 13-20 人;2015 後多數 6-13 人),呢個 secular trend 會稀釋單純「底 vs 頂」
  比較嘅訊號幅度,實務上應該用 own-history percentile 而非 raw count 嚟比較唔同年代。

### 對照組讀數(全期平均出席人數,排名由高至低)
| Ticker | 用途 | Mean n_analysts | Median | Max | 季數 | 失敗率 |
|---|---|---|---|---|---|---|
| AVGO | 熱門/擠迫對照 | **13.45** | 12.0 | 24 | 82 | 0.0% |
| NVDA | 熱門/擠迫對照 | **11.55** | 11.0 | 21 | 80 | 5.0%(見下方caveat) |
| MU | 本體 | 10.77 | 11.0 | 21 | 79 | 2.5% |
| FSLR | 對照 | 9.07 | 8.0 | 22 | 75 | 1.3% |
| WST | 對照 | 5.05 | 5.0 | 13 | 64 | 0.0% |
| USAC | Discovery Radar「未被發現」對照 | **3.61** | 4.0 | 8 | 54 | 0.0% |

排名完全符合先驗:AVGO/NVDA(mega-cap、AI 敘事核心)遠高於 USAC(小型 midstream MLP,thesis 話
2nd percentile 未被發現)。呢個橫截面排序本身就係對 feature-5 假設嘅正面驗證 —— 出席人數同「市場
關注度」高度相關,獨立於 ttm_pe。

### ttm_pe 交叉驗證 —— 兩個代理喺谷底「唔講同一個故事」
喺 MU 谷底期(2022-2023),ttm_pe percentile 本身就唔穩定:2022-09-29 讀 0.02,但 2023-03-28
即跳到 1.00 —— 呢個係 P/E 喺盈利崩潰嘅週期性谷底嘅典型 artefact(分母 E 趨零/負,PE 失真)。
出席人數喺同一期間反而平穩(4-8 人區間,無同類爆走)。結論:analyst attendance 喺「PE 最唔可靠」
嘅精確時點(cyclical trough)反而更穩定可解讀 —— 但正正因為 ttm_pe 喺呢段本身壞咗,兩個代理無法
乾淨地互相驗證,呢點要老實揭露,唔算「交叉驗證通過」。

---

## [產物]

- `C:\projects\Investment\Karst\backtest\experiments\exp_analyst_attendance.py` —— 解析器 + 全 pipeline
- `C:\projects\Investment\Karst\backtest\results\2026-07-12_analyst_attendance_crowding_probe.md` —— 本報告
- `C:\projects\Investment\Karst\backtest\.insider_data\analyst_attendance_series.json` —— 6 隻股完整季度序列 cache(MU/NVDA/AVGO/USAC/WST/FSLR)

---

## [未解/風險]

### 方法論(解析器)—— 誠實失敗率
| Ticker | 季數 | 失敗 | 失敗率 |
|---|---|---|---|
| MU | 79 | 2 | 2.5% |
| NVDA | 80 | 4 | 5.0% |
| AVGO | 82 | 0 | 0.0% |
| USAC | 54 | 0 | 0.0% |
| WST | 64 | 0 | 0.0% |
| FSLR | 75 | 1 | 1.3% |
| **合計** | **434** | **7** | **1.6%** |

**過程中揪出並修正嘅一個重大 bug**(誠實揭露,非事後修飾):舊版 header-block 解析器用
`\s{2,}|\n` split「Analysts:」名單,假設條目一定用雙空格或換行分隔。實際上 2013-2019
年代嘅部分文件(MU 全部核心窗口重疊季度)將名單寫成單行、單空格分隔(例如
`"Tim Luke - Lehman Brothers Shawn Webster - J.P. Morgan ..."`),舊 split 會將成句當一個條目,
`_clean_name` 再取第一個 dash 之前,靜默塌陷做「1 個分析師」——**呢個 bug 影響咗 MU 2013-2019
全部 24 季(100%),且冇被舊版「failed」bucket 揪到**(技術上「成功」返 1,唔算 parse failure,
係最危險嗰種:靜默錯數據)。已重寫做 `_extract_header_block()`,用 name-shaped-token + dash/comma
邊界嘅 regex(`HEADER_ENTRY_RE`),對單行同多行格式都穩健,修正後喺 24 季樣本全部驗證通過。

### 未解/殘留限制(已知,判斷唔值得為呢個 feasibility probe 再投入工程)
1. **NVDA 2025 年 4 季連續解析失敗**(2025-02-26 / 05-28 / 08-27 / 11-19),正正係「NVDA 而家有幾
   crowded」呢個最想知嘅時點 —— 呢個係實質缺口,升格前應該優先修。
2. **舊年代(pre-2013)header_roster_fallback 偶爾將前一條目嘅公司名尾巴漏落嚟緊接嘅名入面**
   (例:2007-10-02 出現 "Bank Gurinder Kalra"、"Brothers Tristan Gerra"),confirmed 只出現喺舊
   格式、且喺 2015+ 核心窗口冇實質出現(spot-check 2015-01-06、2016-12-21 讀數乾淨合理)。
3. **同一分析師跨季拼寫漂移**(例:C.J. Muse / CJ Muse / Christopher Muse / Christopher James Muse;
   Ambrish Srivastava / Ambrish Shrivastava)—— 唔影響單季計數本身(同一份文件內唔會撞名兩種寫法),
   但代表**未做 entity resolution**,任何想做「分析師去留/turnover」嘅後續功能都要先做名字正規化。
4. 呢個係 attention/coverage 代理,**唔等於**真正嘅機構持倉 crowding(sell-side 覆蓋 ≠ buy-side
   positioning)—— 相關但非同一件事,要喺 rubric 文檔明確標註呢個代理嘅性質。
5. Survivorship bias 唔適用(單一股票時序,唔係跨股票宇宙篩選)——如指示確認。

### 建議後續步驟(如果要升格做 feature 5 quantified input)
1. 修 NVDA 2025 年解析缺口(4季)。
2. 用 own-history rolling percentile(仿 ttm_pe 嘅 756-day/252-min-period rank 做法)代替 raw
   count,控制 secular coverage 下滑趨勢,先至有跨年代可比性。
3. 擴大去多幾隻已有 corpus.db 覆蓋嘅股票做統計顯著性測試(本次只 6 隻,屬 feasibility spot-check,
   唔係正式 backtest)。
4. 如果要做「分析師去留」類功能,先做輕量 entity resolution(name normalization)。
