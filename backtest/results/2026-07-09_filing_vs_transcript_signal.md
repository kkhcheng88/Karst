# 財報全文(10-K/10-Q)vs 電話會 transcript——constraint-language 訊號加唔加值(2026-07-09)

**Date:** 2026-07-09  **Script:** `backtest/experiments/exp_filing_signal.py`
**原始資料:** `backtest/experiments/_filing_signal_data.json`(6 case,filing+transcript 逐筆分數 + diff)
**對照基線:** `backtest/experiments/exp_constraint_language.py` / `2026-07-08_constraint_language_probe.md`(MU transcript 早 17 個月嗰個發現)

> **標籤:可行性 + 增量探測,非交易訊號回測。** 答三條問題:財報受限訊號早唔早過 transcript?
> 財報有冇 transcript 冇嘅獨有語言(增量)?財報「呢份 vs 上一份」嘅新增受限語言(Lazy-Prices
> 文字改動)早唔早?**6 個 case**:5 個真.供需超級週期(記憶體/pharma/電力/鈾/光通訊上游)
> + 1 個刻意 negative control(量子,敘事/里程碑驅動、非供需)。

## 0. 方法

- **mirror**:同一套 pre-registered 雙向詞表(`exp_constraint_language.py` 嘅
  `CONSTRAINED_PHRASES`/`LOOSENING_PHRASES`,直接 import,唔重複貼,避免兩份漂移),同一條
  `score_per_1000w = 1000×(受限命中−鬆動命中)/字數` 公式,分別套用喺(a)transcript 全文、
  (b)filing 嘅 **MD&A + Risk Factors** 段(兩段 concat 做 combined score)。
- **increment**:逐 filing 記錄邊啲受限/鬆動 pattern 有命中(bool array),同全案例掃描比較邊啲
  pattern **喺任何 filing 都冇出現過**(vs transcript 詞表全數用開)。
- **Lazy-Prices 文字改動**:逐 filing 同「同系列上一份」(10-K vs 上一份 10-K;10-Q vs 上一份
  10-Q;CCJ 嘅 40-F vs 上一份 40-F、季度 6-K vs 上一份季度 6-K)比較邊啲 pattern 新增/消失
  (`diff` 欄),而唔淨係睇絕對水平。
- **EDGAR 全文攞法**:唔用 WebFetch(LLM 摘要工具,對逐字 regex 計分唔精準),改用
  `urllib.request` 直打 EDGAR(同 `thesis/insider_edgar.py` 一致嘅 SEC-compliant User-Agent
  模式),抓 `index.json` 揀主文件 → 去 HTML tag → 抽 MD&A/Risk Factors 段。**呢個抽段步驟
  本身係本探測最大嘅工程風險**(見 §5 caveat),已用 7 個獨立 filing 樣本(3 種大小寫慣例、
  4 種 item-number 分隔符慣例)交叉驗證至穩定。
- **transcript**:直接用 `defeatbeta_api`(唔讀 `thesis/.raw/transcripts/` 本地 cache),
  script 自足可重現。

## 1. 6 個 case 定義

| Ticker | 類型 | filing 窗(filing_date) | 敘事「應該」喺窗外先成形 |
|---|---|---|---|
| **MU** | 記憶體,cyclical-commodity | 2021-07~2024-12 | gooptions 記憶體叢 ~2025-2026 先大量出現 |
| **LLY** | GLP-1 需求超級週期,pharma | 2021-01~2023-06 | Zepbound 2023-11 批;mania 敘事 2023H2+ |
| **VST** | AI-datacenter 電力,IPP | 2022-01~2024-03 | AI-電力敘事 ~2024 先成形 |
| **CCJ** | 鈾供給缺口,加拿大 FPI | 2021-01~2023-06 | 鈾/核復興敘事 ~2023H2 先firm |
| **AXTI** | InP/GaAs 基板,光通訊上游 | 2022-01~2024-06 | AXTI 過去一年 ~$2→$140(窗外) |
| **RGTI** | 量子計算——**negative control** | 2023-01~2024-09 | Google Willow 2024-12 爆升(窗外) |

CCJ 係加拿大 MJDS filer:EDGAR 冇 10-K/10-Q(`sec_filing()` 核實 form_type 得
40-F/6-K/144/3/4/5/13G),季度 MD&A 收埋喺 6-K 附件、年度 MD&A+Risk(標題唔係「Risk
Factors」而係「**Risks that can affect our business**」)收埋喺 40-F 附件——呢個本身係
第一個發現(見 §5)。

## 2. 逐 case 時間線(headline)

### MU(記憶體)

| 來源 | 首次明顯轉正 | 峰值 |
|---|---|---|
| Transcript | **FY2024Q1(2023-12-20)score=1.005** | FY2024Q2 1.741 |
| Filing(10-Q/10-K,MD&A+Risk) | **全窗(2021-07~2024-12)未曾轉正**,score 恆在 −0.05~−0.35 | 最高 −0.051(2022-03) |

同一季(10-Q filed 2023-12-21,transcript 早 1 日):filing c=1 l=4(score −0.177)vs
transcript c=8 l=0(score 1.005)——transcript 峰值季度,filing 仍然淨負。

### LLY(GLP-1)

| 來源 | 首次明顯轉正 | 峰值 |
|---|---|---|
| Transcript | FY2021Q4(2022-02-03)score=0.089,其後持續正到 FY2023Q3(2023-11-02)0.095 | FY2022Q3 0.200(全期最高,幅度細——分散型 pharma 淡化單一藥物訊號) |
| Filing | **全窗未曾轉正**,score −0.59~−1.98(全 6 case 最負) | — |

### VST(AI 電力)

| 來源 | 首次明顯轉正 | 峰值 |
|---|---|---|
| Transcript | 窗前已持續正(FY2021Q3 2021-11-05 已 1.156);窗內全程正 | FY2023Q4 1.129 |
| Filing | **10-Q(Risk 段只係短 stub~292字)同期都跟到正**(0.62~0.80,方向啱);**10-K(Risk 段全文 138-140K字)一落地跌返近零**(0.000/0.077/−0.029) | 10-Q 2022-05 0.795 |

VST 全部 filing 同對應 transcript **gap=0 日**(同日申報),結構上唔可能「早」。

### CCJ(鈾)

| 來源 | 首次明顯轉正 | 峰值 |
|---|---|---|
| Transcript | **FY2021Q4(2022-02-09)score=0.420**,比「敘事 2023H2 firm」早 ≈18 個月 | FY2022Q1 0.561 |
| Filing(季度 6-K MD&A) | **全窗未曾轉正**,但同季(2022-02-09)raw hits c=6 完全同 transcript 一致——差別在filing 同時帶 l=8(transcript l=0),寫成文字時兩面都講,net 拉平 | — |

### AXTI(光通訊上游 InP)——**兩邊都弱,窗選早咗**

Transcript 全窗最高 0.384(FY2021Q4);filing 全窗 −0.38~−0.56。thesis wiki
(`thesis/wiki/photonics-optical.md`)引用嘅實證(COHR 預付 $22.285M 鎖 3 年 InP 產能)
係 **2026-06-25** 嘅 8-K——遠喺呢個窗(2022-2024)之後。**呢個窗兩邊都搵唔到早期訊號,
唔係框架否證,而係窗本身可能揀早咗**(AXTI 嘅真轉折可能發生喺 2025-2026,唔喺呢次覆蓄範圍)。

### RGTI(量子,negative control)

Transcript **11 季有 10 季 score=0.000**(唯一例外 FY2024Q2 0.163)。Filing 都貼近零
(0.0~0.2)。**但 RGTI filing fire 嘅 pattern 同真.供需 case 完全同一批**(`\ballocation\b`、
`capacity constraints?`、`prepay(?:ment)?s?` / `discount(?:ing)?`、`excess inventory`)
——證明呢啲係**任何公司 filing 都會出現嘅通用商業樣板語言**,唔係供需訊號本身。

## 3. 三個比對問題(核心判定)

### (a) 時機:filing 早唔早過 transcript?

**唔早,結構上唔可能早,實測全部持平或差。** 5 個可判斷 case(AXTI 兩邊都弱、唔計入)入面:

- MU/LLY/CCJ:filing **全窗未曾轉正**,transcript 明顯轉正嘅季度,filing 淨係持平或更負——
  唔淨止「唔早」,係「見唔到」。
- VST:filing 喺 Risk 段係短 stub 嗰幾季**方向跟到**(非「早」,係「同步」——filing_date 同
  transcript report_date **gap 恆 = 0 日**,同日申報),Risk 段變長就跌返。

**跨 4 個可判斷 case 一致結論:transcript 冇一個 case 輸畀 filing 嘅時機;filing 最好情況
係同步,typical 情況係見唔到訊號或倒跟(net 負)。**

### (b) 增量:filing 有冇 transcript 冇嘅獨有受限語言?

**冇。** 掃描 16 條受限 pattern 喺全部 6 case、全部 filing 入面邊啲曾經命中:

| Fire 過嘅受限 pattern | Case |
|---|---|
| `capacity constraints?` | MU、RGTI |
| `prepay(?:ment)?s?` | MU、VST、RGTI |
| `supply shortage` | MU、LLY、VST、AXTI |
| `\ballocation\b` | VST、CCJ、RGTI |
| `take-or-pay` | VST |
| `demand outstripping supply` | AXTI |

**16 條受限 pattern 入面,10 條全 6 case、全部 filing 都從未命中過**——包括最「口語化」嗰批:
`lead times extending`、`on allocation`、`sold out`、`capacity constrained`(單數)、
`cannot/unable to meet demand`、`supply tight(ness)`、`tight supply`、`price increases
sticking`、`undersupply`。**呢批正正係 transcript 探針(2026-07-08)搵到 MU/VST 轉正嘅
主力詞**("lead times extending"、"allocation"、"sold out" 呢類詞係管理層電話會口語,SEC
書面披露幾乎唔用)。反而 9 條鬆動 pattern 入面 **6 條喺 filing 廣泛命中**(`discount(?:ing)?`、
`excess inventory`、`oversupply`、`pricing pressure`、`inventory correction`、
`soft(?:ening)? demand`)——呢啲正正係 SEC Risk Factors 段慣常引用嘅**假設性風險場景**
(「competitors may discount」「we may face oversupply」),同公司實際供需狀況無關,
逐年 copy-paste 都會出現。

**結論:方向反轉——filing 唔係「transcript 冇講、filing 講咗」,而係「transcript 有嘅熱詞
filing 幾乎唔用,filing 反而穩定帶入一批通用鬆動樣板」。**呢個對 LLY 尤其傷:`pricing
pressure` 喺 pharma 語境通常指 PBM/保險/學名藥壓價(同供需完全無關嘅常規風險),但被詞表
當鬆動訊號計,直接解釋 LLY filing score 全 6 case 最負(−0.59~−1.98)。

### (c) Lazy-Prices:呢份 vs 上一份新增嘅受限語言,早唔早?

逐 filing 同「同系列上一份」比較(見 script `diff_series()`)。MU 最貼近轉折點嗰次:

> `10-Q 2023-12-21`(同 transcript 轉正嗰季同日+1):`+C['prepay(?:ment)?s?']`——但**同一份
> 亦 `+L['discount(?:ing)?']`**,net 拉平。`prepay(?:ment)?s?` 之後喺 2024-12-19 又被
> dropped、翻年再上——**反覆進出,唔係單調爬升嘅早期警號,係雜訊**。

VST 全窗只得 1 次 diff 事件(10-K 2024-02-29 dropped `supply shortage`);CCJ/LLY/AXTI/RGTI
嘅 diff 事件都係零散嘅單一 pattern 進出,冇一個案例顯出「連續 ≥2 期同方向新增」嘅乾淨遞增
訊號。**Lazy-Prices 角度冇搵到早過絕對水平嘅額外資訊。**

## 4. 儲存代價(值唔值得儲)

| Ticker | transcript 平均字數 | filing(MD&A+Risk)平均字數 | 倍數 |
|---|---|---|---|
| MU | 8,093 | 18,302 | 2.3x |
| LLY | 12,918 | 11,394(Risk 段常係短 stub) | 0.9x |
| VST | 8,287 | 21,046 | 2.5x |
| CCJ | 11,349 | 26,621 | 2.3x |
| AXTI | 6,105 | 30,960 | 5.1x |
| RGTI | 5,561 | 19,194 | 3.5x |

**中位數 ≈2.4x 儲存代價**(LLY 因 Risk 段短例外),換嚟嘅係「同步或見唔到」嘅訊號、加一批
會拖低分數嘅通用樣板詞。

## 5. 判定

**三選一:redundant/加值/劣過 transcript——本探測結論係「劣過 transcript」,唔係中性
「redundant」。**

1. **時機**:4 個可判斷案例(MU/LLY/VST/CCJ)全部 filing 唔早於 transcript——最好(VST)
   係同步,其餘(MU/LLY/CCJ)filing 全窗未曾轉正,transcript 明顯轉正嘅季度 filing 反而
   淨負。
2. **增量**:方向同用戶假設相反——filing 唔係帶嚟 transcript 冇嘅受限訊號,而係穩定帶入一批
   通用「鬆動」樣板語言(Risk Factors 段結構性偏鬆動),拖低淨分數;transcript 嘅熱詞
   (lead times/allocation/sold out 等)喺 filing 幾乎唔出現。
3. **Lazy-Prices**:文字改動訊號雜訊大,冇一個案例顯出乾淨嘅提前遞增訊號。
4. **儲存代價**:中位數 ~2.4x transcript 大小。
5. **Negative control(RGTI)確認框架射程**:量子(敘事/里程碑驅動,非供需超級週期)喺
   transcript 同 filing 兩邊都讀近零——**但 filing 側嘅「近零」係靠同一批通用樣板詞拖平
   出嚟,唔係乾淨嘅「訊號 vs 無訊號」對照**,同真.供需案例(MU/VST/CCJ)嘅 filing 側都被
   同一批樣板詞拖到接近零/負係同一個機制。呢個反而加強咗「filing 側 constraint-language
   訊噪比太低,唔分得出真假 supercycle」嘅判斷,而唔止係「框架射程窄」。

**建議:唔將 10-K/10-Q 全文納入 Phase-3 常規語料掃描。** transcript 掃描(`exp_constraint_
language.py`,已有 MU/VST 兩個真早期訊號證據)維持做早期偵測嘅主管道;如果將來要用
filing,只用 **MD&A 段(剔除 Risk Factors)** 或許能減少鬆動樣板污染,但呢次冇任何案例
證實 MD&A-only 會贏 transcript 時機(VST 嘅「跟到」都係同步、非早),不足以支持額外開發。

## 未解/風險

1. **單一詞表版本(v0)**——本探測用同一套 transcript 校準嘅詞表套落 filing,結論可能部分
   反映「詞表冇為 filing 書面語域重新校準」,而非「filing 文本本身冇早期訊號」。未試過針對
   filing 語域重新 pre-register 一套詞(例如書面常見講法「we intend to allocate available
   capacity to...」「our lead time commitments have lengthened」)。
2. **EDGAR 段落抽取係工程風險最高嘅一環**——7 個獨立 filer 樣本入面搵到至少 5 類獨立失敗模式
   (大小寫慣例、item-number 與標題之間句號/破折號分隔符、HTML tag 令詞中間插入雜訊空格、
   引用句 vs 真標題嘅消歧),已逐一修正並用真實文本交叉驗證,但**冇對全部 70 份 filing 逐份
   人手核對**——不能排除仍有個別 filing 抽段唔精準(尤其 CCJ 嘅 40-F/6-K,附件 content-sniffing
   本質上比 SEC 標準化 iXBRL item 編號脆弱)。
3. **CCJ 嘅 MD&A/AIF 文本被硬截斷喺 220,000 字元**(冇像 US-regime 咁精準搵 END 邊界)——
   CCJ 季度/年度分數可能因此輕微低估(截走文件後段),但截斷發生喺全部年份一致,唔會扭曲
   跨年比較方向。
4. **AXTI 窗選早咗嘅可能性**——thesis wiki 引用嘅實證日期喺窗外,呢個 case 嘅「兩邊都弱」
   結論唔應該被讀成「AXTI 唔係真瓶頸」,只係「呢個窗搵唔到」。
5. **單一詞表 run(non-repeated)**——冇做多次獨立 pre-registration/多分析師覆現,詞表 fire
   統計(§3b 表)基於一次掃描,唔排除個別 regex 邊界情況(如 `\ballocation\b` 喺 RGTI/VST
   可能部分命中「capital allocation」呢類同供需無關嘅財務用語,未逐句人手抽查確認)。
