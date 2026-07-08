# Phase-3 WS3 規格 —— 主題增量機制(發現→收編→退場)【設計定稿,待執行】

> 設計:Fable(2026-07-08)。原則:**發現可以濫,收編必須嚴,退場必須有** —— 主題數目增加係
> 好事(IC 裁判橫截面愈闊校準愈快),但每個入場者過同一道閘、每個在場者隨時可以被除牌。

## 1. themes.yaml schema 擴充(每主題新增欄)

```yaml
sources: [{id: gooptions-trend-core, tier: 2}, ...]   # 獨立來源清單(同一間舖 N 篇 = 1 個來源)
meta_factors: [ai-capex]                               # 共同因子標籤(≥1 必填;清單:ai-capex/
                                                       #  china-supply/rates-duration/energy-macro/
                                                       #  policy-defense/consumer/其他按需擴)
admitted: 2026-07-01                                   # 收編日
last_evidence: 2026-07-08                              # 最後一次有 cited 新證據
status: active                                         # active | watch | delisted
```
`single_source` 唔另設欄 —— lint 由 `len(sources)<2` 推導。

## 2. Admission 閘(新主題入 registry 嘅唯一通道)

**機器 lint(`thesis/lint.py` 擴充,缺一 = 入唔到)**:
kill_condition 非空且含觸發動詞;tickers 全部 `data.py` load 得到(或明文標「掛牌後補」);
cycle_stage ∈ {early,mid,late,event-driven};confidence ∈ (0,0.6];wiki 頁存在且 frontmatter 合法;
sources ≥1;meta_factors ≥1;admitted/last_evidence 日期合法。

**人工判斷(唔扮自動,checklist 落 wiki 頁)**:
4-KPI 逐項 cited 打分;priced-in/週期閘(估值分位 + 供給回應 + 擁擠);可交易表達草案
(ETF 優先,見 WS5)。

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
