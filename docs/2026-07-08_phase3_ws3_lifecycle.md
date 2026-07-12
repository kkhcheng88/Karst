# Phase-3 WS3 規格 —— 主題增量機制(發現→收編→退場)【設計定稿,待執行】

> 設計:Fable(2026-07-08)。原則:**發現可以濫,收編必須嚴,退場必須有** —— 主題數目增加係
> 好事(IC 裁判橫截面愈闊校準愈快),但每個入場者過同一道閘、每個在場者隨時可以被除牌。

## 1. themes.yaml schema 擴充(每主題新增欄)

```yaml
sources: [{id: gooptions-trend-core, tier: 2}, ...]   # 獨立來源清單(同一間舖 N 篇 = 1 個來源)
meta_factors: [ai-capex]                               # 共同因子標籤(≥1 必填;canonical 清單見
                                                       #  thesis/themes.yaml 檔頭註冊表,§1a 詳述)
admitted: 2026-07-01                                   # 收編日
last_evidence: 2026-07-08                              # 最後一次有 cited 新證據
status: active                                         # active | watch | delisted
```
`single_source` 唔另設欄 —— lint 由 `len(sources)<2` 推導。

## 1a. meta_factor 概念正式化(2026-07-12 補寫;原文只係一句話帶過,未成形)

**係咩**:`meta_factor` 標籤嘅唔係 theme 嘅 sector/ticker,而係支撐佢 thesis 嘅**底層宏觀驅動力**。
兩個 sector 唔同、ticker 唔同嘅 theme,可以係同一注宏觀注碼(例如 memory-supercycle 同
ai-power-grid 睇落唔同行業,但兩者都係「AI capex 持續」呢個假設嘅表達)——`meta_factor` 存在
就係要捉呢種**偽分散**,`concentration.py` 讀呢個標籤計集中度。

**點解需要正式化**:原設計(§1 上面)得一句「清單:ai-capex/china-supply/rates-duration/
energy-macro/policy-defense/consumer/其他按需擴」,冇註冊表、冇命名規則、冇「幾時要開 hub
concept page」嘅規則。結果 07-11 discovery radar 一次過加 6 個新 theme 時,`euv-lithography-
monopoly` 標咗 `ai-capex` 但冇人記得接返 `ai-capex-macro-risk.md` 呢頁(隔咗一日,07-12 先由
用戶提出先發現、先補)。正式化嘅目的就係防止呢類遺漏再發生。

**canonical 註冊表**:見 `thesis/themes.yaml` 檔頭「META_FACTOR TAXONOMY REGISTRY」——單一事實
來源,唔喺呢份 spec 度重複維護(避免兩處各自過時、對唔上)。

**三條硬規則**:
1. **命名**:kebab-case,新值一定要喺 admission 嗰一個 commit 同步加入 `themes.yaml` 嘅註冊表,
   唔准自由打字(`thesis/lint.py` 會 warn 唔喺註冊表入面嘅值)。
2. **Hub page 規則**:一個 meta_factor 一旦有 **≥2 個 theme** 掛住,就必須有一頁跨主題 concept
   wiki page(格式跟 `thesis/wiki/ai-capex-macro-risk.md`:唔入 themes.yaml/thesis_quality、
   用 wiki-link 交叉連結所有掛住嘅 theme、列共同監察指標),並且每個成員 theme 嘅 kill_condition
   附近要有一句反向連結。單一 theme 掛住嘅 meta_factor 未需要(冇「偽分散」風險)。
3. **新增 theme 時嘅義務**:如果新 theme 標咗一個已有 ≥1 theme 掛住嘅 meta_factor,同一個
   session 就要檢查/更新對應 hub page(如果存在)嘅交叉連結;如果因為呢個新 theme 令個
   meta_factor 首次達到 ≥2,就要開新 hub page(可以排入 backlog,但要喺註冊表註明「hub:
   MISSING」,唔准靜默漏咗)。

**2026-07-12 掃描發現(已落 `thesis/themes.yaml` 註冊表)**:`energy-macro`(oil-gas-energy /
us-solar-manufacturing / gas-compression-equipment,共 3 個 theme、17.7% 集中度)符合規則 2
嘅門檻,但**冇 hub page**——`ai-capex` 係目前唯一有 hub page 嘅 meta_factor。列為 backlog,唔喺
呢次順手整理範圍內(需要新嘅 domain 研究去寫呢頁,唔係淨係接連結)。

## 2. Admission 閘(新主題入 registry 嘅唯一通道)

**機器 lint(`thesis/lint.py` 擴充,缺一 = 入唔到)**:
kill_condition 非空且含觸發動詞;tickers 全部 `data.py` load 得到(或明文標「掛牌後補」);
cycle_stage ∈ {early,mid,late,event-driven};confidence ∈ (0,0.6];wiki 頁存在且 frontmatter 合法;
sources ≥1;meta_factors ≥1;admitted/last_evidence 日期合法。

**人工判斷(唔扮自動,checklist 落 wiki 頁)**:
4-KPI 逐項 cited 打分;priced-in/週期閘(估值分位 + 供給回應 + 擁擠);可交易表達草案
(ETF 優先,見 WS5)。

**2026-07-11 新增兩項 checklist(嚟自 Mauboussin/Chancellor 書蒸餾 + backtest 驗證,詳見
docs/2026-07-11_magnifier_book_expectations_investing.md、backtest/results/2026-07-11_
sizing_formula_validation.md、backtest/results/2026-07-11_buyback_capital_allocation_signal.md)——
兩項都係 checklist 提示,唔係機械硬閘,唔改 lint.py**:

- **Solvency gate(margin-of-safety 前置檢查)**:對任何「估值睇落好平/跌得好殘」嘅週期股候選,
  入場前必須先過一個基本財務健康篩(利息覆蓋率/淨負債佔EBITDA/流動性跑道),先好將個「平」讀成
  「機會」。理由:backtest 用案例庫驗證「折讓越大回報越好」呢個方向有一定支持(2年期 partial
  correlation p=0.0029),但 WOLF(Wolfspeed)案例證明純折讓%完全分唔開「平常被低估」同「即將
  破產」——WOLF 2021年高位跌70-80%,睇落極吸引,2025年6月申請Chapter 11,舊股東實質全損。
  折讓本身唔係買入理由,一定要先confirm間公司捱得過落去。
- **Buyback/net issuance 訊號要分市值層讀,唔可以直覺套用**:回購多/發股少嘅公司通常表現較好,
  但呢個訊號**喺Phase-3典型嘅細/中價股候選(Materials/Energy板塊)方向可能反晒**——大價股(>$10B)
  訊號方向啱且顯著,但細/中價股($300M-10B)喺126日/252日horizon顯著反方向(t值1.7-3.5),
  Financials嘅回購反映監管資本強度而非供給紀律。**唔好將呢個當通用正面訊號用**,尤其評估
  Materials/Energy嘅細中價股thesis嗰陣。

**硬規則**:
- **單源封頂**:`len(sources)<2` → confidence 上限 **0.30**(早期捕獲天生單源 —— 冇問題,
  細注入場,加源解鎖)。
- **即日入戰績簿**:admission 當日起 `log_predictions` 覆蓋佢(裁判由第一日計分)。

## 3. 退場(三途,全部機器可檢)

| 途徑 | 條件 | 動作 |
|---|---|---|
| Kill 觸發 | kill 條件事實成立(夜班/日間 session 判)| status→delisted,confidence→0,戰績簿記 kill_fired;**留檔唔刪**(負面結果係證據)|
| 證據過期 | `today - last_evidence > 120d` | confidence ×0.8、status→watch;再 120d → delisted |
| Beta 化 | 主題籃(EW)對最近似板塊 ETF 126d rolling corr > 0.9 持續 6 個月,且對該 ETF 超額 ≈ 0 | delisted(「呢個主題已經冇獨立內容」)|

## 4. 集中度預算(拆 6/9 掛 AI 嗰個炸彈)

- **同一 meta_factor 嘅主題,合計部署唔准超過衛星資金 50%**(sizing 層執行,WS5)。
- 發現配額:每季 sweep(任務 8)候選名單 ≥50% 係非 ai-capex meta_factor。
- `ai-capex-macro-risk.md` 五盞燈 = ai-capex meta_factor 嘅共同 kill 前哨:任何一盞轉紅,
  該 meta_factor 全部主題自動 status→watch(唔係即除牌,係逼 session 覆核)。

## 5. 競爭上崗(注碼面,接 WS5)

衛星預算固定 → 主題按 confidence 排名分配;新主題 admission 唔會加大預算,只會擠佔:
預算滿額時,confidence 最低嘅在場者被削到 watch 級注碼。**多主題 = 多選擇,唔係多曝險。**

## 6. Self-Review(反駁過乜)

| 挑戰 | 裁定 |
|---|---|
| 「來源數會被 game(同一舖十篇文當十源)」| 已封:source id 按機構計,N 篇 = 1 源 |
| 「單源封頂 0.30 會唔會扼殺早期捕獲?」| 特登嘅:早 + 單源 = 正確姿勢係細注,唔係大注;加源(insider 訊號/一手財報確認)即解鎖 —— 呢個機制本身就係「求證推動加倉」|
| 「meta_factor 標籤主觀」| 成立但可控:admission 時打、季度 sweep 覆核;寧願粗標籤都要有預算閘,好過冇 |
| 「120d 過期線會殺慢主題(太空呢種幾年戲)」| 過期只係降級+watch,唔係除牌;真・慢主題自然有季度財報做新證據 |
| 「beta 化測試會唔會誤殺(主題同板塊短期共振)」| 6 個月持續 + 超額≈0 兩條件齊先殺;誤殺成本低(除牌可以重新 admission)|

## 7. 執行 backlog

| # | 項 | 驗收 |
|---|---|---|
| 1 | themes.yaml 9 主題補新欄(sources/meta_factors/admitted/last_evidence/status)| lint 0 error;ai-capex 標籤覆蓋 6 個主題 |
| 2 | lint.py 擴充 admission 規則 + 過期/單源檢查 | 人工整一個壞 fixture 主題,lint 捉到晒 |
| 3 | 集中度報表:`python thesis/concentration.py`(meta_factor × 部署額)| 輸出表 + 超額警告 |
| 4 | Beta 化檢測 job(月度夠)| 對現有 9 主題出首份報告 |

**時間盒:≤ 1 個執行 session(同 WS1 可並一批)。**
