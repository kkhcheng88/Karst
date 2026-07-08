# 供應受限語言掃描——電話會 transcript 可行性原型(2026-07-08)

標籤:**可行性原型**(feasibility probe,非生產訊號、非回測 alpha 結論)。
Script:`backtest/experiments/exp_constraint_language.py`
原始逐季分數:`backtest/results/2026-07-08_constraint_language_probe_data.json`(487 列)

## 目的

WS4(早期偵測)另一條路:財報電話會 transcript 嘅「供給受限措辭」(lead time
extending、allocation、sold out…)喺文字上現形,可能早過賣方/研究社群寫成敘事
(如 gooptions 記憶體 supercycle 系列)。本探針只答:(1) 數據有冇、(2) 詞表訊號
喺時間軸上係咪真係跑贏敘事、(3) 值唔值得落地做常規 job。唔答「呢個訊號可以交易
幾多 α」。

## 1. 數據盤點

`defeatbeta_api.data.ticker.Ticker(sym).earning_call_transcripts()` →
`Transcripts` 物件,`.get_transcripts_list()` 列出 (fiscal_year, fiscal_quarter,
report_date),`.get_transcript(fy, fq)` 攞逐段 (paragraph_number, speaker,
content) DataFrame。15 隻覆蓋(全部一次性列出,非掃描窗):

| Ticker | 季度數 | 最舊 | 最新 |
|---|---|---|---|
| MU   | 80 | 2006 FY1 (2005-12-26) | 2026 FY3 (2026-06-24, **僅 312 字元,片段/未完整收錄,已 SKIP**) |
| TSM  | 79 | 2005 FY4 (2006-01-28) | 2026 FY1 (2026-04-16) |
| ETN  | 76 | 2007 FY2 (2007-07-16) | 2026 FY1 (2026-05-05) |
| VST  | 36 | 2016 FY4 (2017-03-30) | 2026 FY1 (2026-05-07) |
| CAT  | 77 | 2007 FY1 (2007-04-20) | 2026 FY1 (2026-04-30) |
| UNP  | 74 | 2007 FY4 (2008-01-24) | 2026 FY1 (2026-04-23) |
| LLY  | 76 | 2007 FY2 (2007-07-24) | 2026 FY1 (2026-04-30) |
| XOM  | 82 | 2005 FY3 (2005-10-31) | 2026 FY1 (2026-05-01) |
| JPM  | 76 | 2007 FY2 (2007-07-18) | 2026 FY1 (2026-04-14) |
| AMAT | 80 | 2006 FY1 (2006-02-17) | 2026 FY2 (2026-05-14) |
| WDC  | 79 | 2005 FY4 (2006-01-28) | 2026 FY3 (2026-04-30) |
| STX  | 81 | 2006 FY2 (2006-01-19) | 2026 FY3 (2026-04-28) |
| NVDA | 81 | 2005 FY4 (2006-01-30) | 2027 FY1 (2026-05-20) |
| AVGO | 83 | 2005 FY4 (2006-01-31) | 2026 FY2 (2026-06-03) |
| CEG  | 30 | 2007 FY4 (2008-01-30) | 2026 FY1 (2026-05-11) |

**結論:15 隻全部有覆蓋,回溯到 2005-2008 年,無需 fallback。** VST/CEG 因分拆/上市
較遲只有 30-36 季(≈2016/2007 起)。單一 gap:MU 最新一季(2026 FY3)transcript 喺
defeatbeta 度只得片段(1 段、312 字元),疑未完整收錄,掃描時已自動偵測並 skip
(閾值 <500 字元)。

## 2. 詞表 v0(pre-registered,雙向,見 script `CONSTRAINED_PHRASES`/
`LOOSENING_PHRASES`)

- 受限方向(15 條 regex):lead times extending/stretched/stretching、on
  allocation、sold out、capacity constrained、cannot/unable to meet demand、
  supply tight(ness)、price increases sticking、take-or-pay、prepay(ment)、
  undersupply、supply shortage、demand outstripping supply
- 鬆動方向(9 條,對照/反向):inventory correction、demand softness、capacity
  coming online、pricing pressure、discounting、excess inventory、inventory
  build/glut、oversupply

分數 = 1000 × (受限命中 − 鬆動命中) / transcript 字數(逐季、逐 ticker),
scan 窗 FY2018 起(487 季度列,涵蓋驗證所需嘅 2023-2026)。

## 3. 原型掃描結果(2023 起,重點季度)

**記憶體鏈**

| Ticker | 訊號首次明顯轉正 | 分數軌跡重點 |
|---|---|---|
| MU  | **FY2024Q1(財報日 2023-12-20)score=1.005**,FY2024Q2(2024-03-20)飆到 **1.741**(全序列最高之一) | 2023 全年 ≈0 或負;2024Q1 起連續 4 季 >0.5;2025Q1 短暫回落到 0,但 FY2025Q4(2025-09-23)再衝 1.323,FY2026Q1/Q2 續高(0.96/0.78)——**兩波**:2023H2→2024 初升 + 2025H2→2026 再加速 |
| WDC | 落後 MU 約 3-4 季:FY2025Q1(2024-10-24)score=0.436 首見持續轉正,FY2025Q3(2025-04-30)0.884 | |
| STX | 落後更多:FY2025Q3(2025-04-29)score=0.411,真正明顯要到 FY2026Q3(2026-04-28)0.766 | |

**電力/電網鏈**

| Ticker | 訊號首次明顯轉正 |
|---|---|
| VST | FY2023Q2(2023-08-09)score=0.959,其後長期維持 0.5-1.1(persistent,非單季尖峰) |
| ETN | FY2023Q4(財報日 2024-02-01)score=0.919,FY2024Q1(2024-04-30)0.875 |
| CEG | 較弱、較慢:2023-2024 維持 0.1-0.4,FY2026Q1(2026-05-11)才到 0.613 |

## 4. 關鍵驗證:訊號 vs 敘事——早唔早?

Gooptions 語料(`thesis/.raw/gooptions/research/`)裡有「記憶體/DRAM/NAND/HBM/
supercycle」關鍵字嘅最早一篇:**issue #044-046(2026-05-04)**,內文提到「記憶體
炒完」(暗示敘事已提早存在但呢個語料庫入面最早出現點係度);第一篇**專題**
LTA 驗證清單係 **issue #068(2026-05-21)**;供給/超級循環正題文章 **issue #148
(2026-07-07)**。

- **MU 第一波受限訊號(FY2024Q1,2023-12-20)比 gooptions 語料最早記憶體提及
  (2026-05-04)早 ≈ 17 個月**;比專題文章(2026-05-21)早 ≈ 17 個月。
- **MU 第二波加速(FY2025Q4,2025-09-23)比 gooptions 最早提及早 ≈ 8 個月**,
  比專題文章(2026-05-21)早 ≈ 8 個月——呢一波時序上直接領先敘事轉熱。
- **電力鏈(VST/ETN)受限訊號 2023Q2-Q4 已經明顯**,比 gooptions 電力/AI infra
  系列首篇(090,2026-05-30;137,2026-07-01)早 **>2 年**。呢個落差比記憶體鏈
  仲大,但要留意電網容量緊張係公開已久嘅主題(電網互連排隊、變壓器交期喺
  2023 已見於行業新聞),唔淨止喺 gooptions 呢個語料庫先出現——所以「早幾多」
  嘅比較對電力鏈冇記憶體鏈咁乾淨(敘事可能早已喺其他管道存在,只係 gooptions
  遲寫)。

**淨結論:transcript 詞頻訊號喺呢個原型入面,對記憶體鏈同電力鏈都跑贏(早於)
gooptions 敘事——記憶體鏈兩波都提前(17 個月/8 個月),電力鏈提前幅度更大但可信
度較低(可能只係反映 gooptions 覆蓋遲,唔係訊號本身特別早)。**

## 5. 落地規格建議

- **頻率**:跟財報季走,唔係逐日/逐週——建議每季財報季後(約 4 個月一輪:
  1月、4月、7月、10月)批次重跑一次,唔需要更高頻(transcript 唔會日更)。
- **輸出**:板塊 × 季度熱力表(本探針 JSON 已經係呢個形狀,可直接餵
  dashboard/heatmap);**突變警報**=score 環比跳升超過 X 個標準差,或連續
  ≥2 季轉正(避免單季雜訊觸發)。
- **接入發現隊列**:每 ticker-quarter 一行 `{ticker, fiscal_year,
  fiscal_quarter, report_date, score_per_1000w, constrained_hits,
  loosening_hits}`,同現有 thesis/ INGEST 格式對齊(加 `source=transcript_scan`
  tag),分數本身唔係 confidence,要經 thesis 校準層先落地做 CONFIDENCE 輸入。
- **詞表紀律化擴充**:遵守 df 收割 anti-noise 原則——新詞唔可以憑單一公司/單一
  季度加入,要求(a)跨 ≥3 家唔同公司出現、(b)跨 ≥2 季持續出現、先可以升級入
  v1 正式詞表;過程留 log(邊季邊 ticker 首次見到候選詞、覆現次數),避免
  overfitting 到某一次财報嘅特定措辭。

## 未解/風險

1. 詞表 v0 未經跨行業/跨語言(電話會有非英語管理層口音轉錄)雜訊率評估——
   FALSE POSITIVE 率(例如泛用詞「allocation」都可能指資本配置而非產能分配)
   未人手抽查驗證,本探針純字面 regex match。
2. 電力鏈「早幾多」嘅結論置信度低於記憶體鏈(見 §4),因為對照組(gooptions
   語料)本身可能就遲寫電力主題,唔代表訊號本身特別早——呢點落 dashboard 前
   要標注。
3. 本探針未做「訊號→之後股價/thesis confidence 表現」嘅回測(呢個係下一步,
   如果決定落地要另開一份回測驗證 lead-lag 唔止喺敘事層面,仲要驗證能唔能夠
   轉化做可交易訊號)。
4. MU 最新一季(2026 FY3)transcript 喺 defeatbeta 未完整,後續重跑需要留意
   資料是否已補齊,否則熱力表最新一格會持續缺格。
